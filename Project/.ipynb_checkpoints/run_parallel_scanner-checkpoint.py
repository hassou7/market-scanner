# run_parallel_scanner.py
"""
Parallel Market Scanner Runner (PHASED)

Runs market scans on cryptocurrency exchanges with a phased orchestrator:
- Phase 1: FAST exchanges (Binance, Bybit, Gate) with higher parallelism
- Phase 2: SLOW exchanges (KuCoin, MEXC, SF 1w) with lower parallelism

Keeps your per-exchange symbol/strategy parallelism intact, but avoids
cross-exchange burst that causes timeouts on KuCoin/MEXC.

Env overrides:
  FAST_MAX_EXCHANGES (default 4)
  SLOW_MAX_EXCHANGES (default 2)
  EXCHANGE_STAGGER_MS (default 250)
"""

import asyncio
import sys
import os
import logging
import pandas as pd
import nest_asyncio
from datetime import datetime

def filter_csv_columns(df):
    """Remove technical columns that shouldn't be in CSV exports"""
    columns_to_exclude = [
        'bars_inside',
        'min_bars_inside_req',
        'window_size',
        'entry_idx',
        'left_idx',
        'close_position_indicator',
        'color',
        'atr_ok'
    ]
    columns_to_drop = [col for col in columns_to_exclude if col in df.columns]
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)
    return df

# Check if running in Jupyter Notebook
def is_jupyter():
    try:
        from IPython import get_ipython
        return get_ipython() is not None and 'IPKernelApp' in get_ipython().config
    except (ImportError, AttributeError):
        return False

# Conditional import for IPython only in Jupyter
if is_jupyter():
    from IPython.display import display
else:
    display = lambda x: logging.info(f"DataFrame output (non-Jupyter): \n{x.to_string(index=False)}")

project_dir = os.path.join(os.getcwd(), "Project")
sys.path.insert(0, project_dir)
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(message)s')

from scanner.main import run_scanner, kline_cache
from utils.config import get_telegram_config

# ──────────────────────────────────────────────────────────────────────────────
# Exchange groups
# ──────────────────────────────────────────────────────────────────────────────

futures_exchanges = ["binance_futures", "bybit_futures", "gateio_futures", "mexc_futures"]
spot_exchanges = ["binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"]
spot_exchanges_1w = ["binance_spot", "bybit_spot", "gateio_spot"]
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]

# All available exchanges including SF
all_exchanges = futures_exchanges + spot_exchanges + sf_exchanges_1w

# Speed profiles
FAST_SET = {
    "binance_futures", "bybit_futures", "gateio_futures",
    "binance_spot", "bybit_spot", "gateio_spot",
}
SLOW_SET = {
    "kucoin_spot", "mexc_spot", "mexc_futures",
    "sf_kucoin_1w", "sf_mexc_1w",
}

def split_by_speed(exchanges):
    fast = [e for e in exchanges if e in FAST_SET]
    slow = [e for e in exchanges if e in SLOW_SET]
    other = [e for e in exchanges if e not in FAST_SET and e not in SLOW_SET]
    # Unknowns go to slow by default (safer)
    slow += other
    return fast, slow

# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_sf_exchange_timeframe(exchanges, timeframes):
    """Validate that SF exchanges are only used with compatible timeframes"""
    sf_only_1w = {"sf_kucoin_1w", "sf_mexc_1w"}
    for exchange in exchanges:
        if exchange in sf_only_1w:
            invalid_timeframes = [tf for tf in timeframes if tf != "1w"]
            if invalid_timeframes:
                raise ValueError(
                    f"SF exchange '{exchange}' only supports 1w timeframe. "
                    f"Invalid timeframes requested: {invalid_timeframes}"
                )
    return True

def print_header(text):
    logging.info(f"\n{'='*80}")
    logging.info(f"  {text}")
    logging.info(f"{'='*80}\n")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers: phased exchange execution
# ──────────────────────────────────────────────────────────────────────────────

async def _stagger(ms=250):
    import random
    await asyncio.sleep(random.uniform(0, ms/1000))

async def scan_exchange(exchange, timeframe, strategies, telegram_config, min_volume_usd):
    """Run scan on a single exchange with progress logging"""
    try:
        start_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{start_time}] Starting scan on {exchange} for {timeframe} timeframe...")
        results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
        signal_count = sum(len(res) for res in results.values())
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{end_time}] ✓ Completed {exchange} scan: {signal_count} signals found")
        return exchange, results
    except Exception as e:
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.error(f"[{end_time}] ✗ Error scanning {exchange}: {str(e)}")
        return exchange, {}

async def _run_exchange_phase(exchanges, timeframe, strategies, telegram_config, min_volume_usd,
                              max_parallel_exchanges: int, label: str, stagger_ms: int):
    """Run a phase (fast or slow exchanges) with limited concurrent exchanges."""
    print_header(f"PHASE: {label} ({len(exchanges)} exchanges)")
    if not exchanges:
        logging.info("No exchanges in this phase.")
        return []

    sem = asyncio.Semaphore(max_parallel_exchanges)

    async def _guarded(exchange):
        async with sem:
            await _stagger(stagger_ms)
            return await scan_exchange(exchange, timeframe, strategies, telegram_config, min_volume_usd)

    tasks = [_guarded(ex) for ex in exchanges]
    return await asyncio.gather(*tasks)

# ──────────────────────────────────────────────────────────────────────────────
# Single-timeframe runner (phased)
# ──────────────────────────────────────────────────────────────────────────────

async def run_parallel_exchanges(timeframe, strategies, exchanges=None, users=["default"],
                                 send_telegram=True, min_volume_usd=None, save_to_csv=False):
    """
    Run scans on multiple exchanges in parallel, phased by API speed profile.
    """
    start_time = datetime.now()
    users = users if isinstance(users, (list, tuple)) else ["default"]

    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges

    # Validate SF timeframe
    validate_sf_exchange_timeframe(exchanges, [timeframe])

    # Orchestration params (env-tunable)
    FAST_MAX_EX = int(os.getenv("FAST_MAX_EXCHANGES", "4"))
    SLOW_MAX_EX = int(os.getenv("SLOW_MAX_EXCHANGES", "2"))
    STAGGER_MS  = int(os.getenv("EXCHANGE_STAGGER_MS", "250"))

    print_header(f"RUNNING PARALLEL SCANS ON ALL EXCHANGES {timeframe}")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframe: {timeframe}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    logging.info(f"• Save to CSV: {'Enabled' if save_to_csv else 'Disabled'}")
    logging.info(f"• Start time: {start_time.strftime('%H:%M:%S')}")
    logging.info("\nFetching market data...\n")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None

    # Phase split
    fast, slow = split_by_speed(exchanges)
    if fast:
        logging.info(f"Phase FAST: {', '.join(fast)}")
    if slow:
        logging.info(f"Phase SLOW: {', '.join(slow)}")

    # Run FAST exchanges first (higher parallelism)
    fast_results = await _run_exchange_phase(
        exchanges=fast, timeframe=timeframe, strategies=strategies,
        telegram_config=telegram_config, min_volume_usd=min_volume_usd,
        max_parallel_exchanges=FAST_MAX_EX, label="FAST", stagger_ms=STAGGER_MS
    )

    # Then SLOW exchanges (gentler parallelism)
    slow_results = await _run_exchange_phase(
        exchanges=slow, timeframe=timeframe, strategies=strategies,
        telegram_config=telegram_config, min_volume_usd=min_volume_usd,
        max_parallel_exchanges=SLOW_MAX_EX, label="SLOW", stagger_ms=STAGGER_MS
    )

    exchange_results = [*fast_results, *slow_results]

    # Process results
    all_results = {}
    for exchange, result in exchange_results:
        for strategy, res_list in result.items():
            if strategy not in all_results:
                all_results[strategy] = []
            for r in res_list:
                r['exchange'] = exchange
                r['timeframe'] = timeframe
            all_results[strategy].extend(res_list)

    end_time = datetime.now()
    duration = end_time - start_time

    print_header("COMBINED SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    logging.info(f"Total signals found across all exchanges: {total_signals}")
    logging.info(f"Start time: {start_time.strftime('%H:%M:%S')}")
    logging.info(f"End time: {end_time.strftime('%H:%M:%S')}")
    logging.info(f"Duration: {str(duration).split('.')[0]}")

    for strategy, res in all_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], utc=True)
            df = df.sort_values(['exchange', 'symbol']) if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)

    if save_to_csv:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for strategy, res in all_results.items():
            if res:
                df = pd.DataFrame(res)
                df = filter_csv_columns(df)
                filename = f"{strategy}_{timeframe}_{timestamp}.csv"
                df.to_csv(filename, index=False)
                logging.info(f"Saved {strategy} results to {filename}")

    return all_results

# ──────────────────────────────────────────────────────────────────────────────
# Multi-timeframe runner (phased each timeframe)
# ──────────────────────────────────────────────────────────────────────────────

async def run_parallel_multi_timeframes_all_exchanges(timeframes, strategies, exchanges=None,
                                                      users=["default"], send_telegram=True,
                                                      min_volume_usd=None, save_to_csv=False):
    """
    Run scans on multiple timeframes across multiple exchanges with FAST→SLOW phasing per timeframe.
    """
    os.environ["DISABLE_PROGRESS"] = "1"  # keep logs clean for multi runs

    start_time = datetime.now()
    users = users if isinstance(users, (list, tuple)) else ["default"]

    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]

    # Smart selection: if only 1w, prefer SF exchanges; else regular
    if exchanges is None:
        if timeframes == ["1w"] or all(tf == "1w" for tf in timeframes):
            exchanges = sf_exchanges_1w
        else:
            exchanges = default_exchanges

    # Validate SF timeframe
    validate_sf_exchange_timeframe(exchanges, timeframes)

    # Orchestration params (env-tunable)
    FAST_MAX_EX = int(os.getenv("FAST_MAX_EXCHANGES", "4"))
    SLOW_MAX_EX = int(os.getenv("SLOW_MAX_EXCHANGES", "2"))
    STAGGER_MS  = int(os.getenv("EXCHANGE_STAGGER_MS", "250"))

    print_header(f"RUNNING PARALLEL MULTI-TIMEFRAME SCAN ON ALL EXCHANGES")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframes: {', '.join(timeframes)}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    logging.info(f"• Save to CSV: {'Enabled' if save_to_csv else 'Disabled'}")
    logging.info(f"• Start time: {start_time.strftime('%H:%M:%S')}")
    logging.info("\nFetching market data...\n")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None

    all_results = {}
    for timeframe in timeframes:
        kline_cache.clear()  # better hit ratios per TF
        logging.info(f"Processing timeframe: {timeframe}")

        fast, slow = split_by_speed(exchanges)
        logging.info(f"{timeframe}: {len(fast)} FAST, {len(slow)} SLOW exchanges")

        fast_phase = await _run_exchange_phase(
            exchanges=fast, timeframe=timeframe, strategies=strategies,
            telegram_config=telegram_config, min_volume_usd=min_volume_usd,
            max_parallel_exchanges=FAST_MAX_EX, label=f"FAST {timeframe}", stagger_ms=STAGGER_MS
        )

        slow_phase = await _run_exchange_phase(
            exchanges=slow, timeframe=timeframe, strategies=strategies,
            telegram_config=telegram_config, min_volume_usd=min_volume_usd,
            max_parallel_exchanges=SLOW_MAX_EX, label=f"SLOW {timeframe}", stagger_ms=STAGGER_MS
        )

        exchange_results = [*fast_phase, *slow_phase]

        # Merge phase results
        for exchange, result in exchange_results:
            for strategy, res_list in result.items():
                for res in res_list:
                    res['timeframe'] = timeframe
                    res['exchange'] = exchange
                if strategy not in all_results:
                    all_results[strategy] = []
                all_results[strategy].extend(res_list)

        await asyncio.sleep(0.2)  # small breather between TFs

    end_time = datetime.now()
    duration = end_time - start_time

    print_header("PARALLEL MULTI-TIMEFRAME MULTI-EXCHANGE SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    logging.info(f"Total signals found across all exchanges and timeframes: {total_signals}")
    logging.info(f"Start time: {start_time.strftime('%H:%M:%S')}")
    logging.info(f"End time: {end_time.strftime('%H:%M:%S')}")
    logging.info(f"Duration: {str(duration).split('.')[0]}")

    for strategy, res in all_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], utc=True)
            df = df.sort_values(['exchange', 'timeframe', 'symbol']) if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)

    if save_to_csv:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for strategy, res in all_results.items():
            if res:
                df = pd.DataFrame(res)
                df = filter_csv_columns(df)
                filename = f"{strategy}_multi_{timestamp}.csv"
                df.to_csv(filename, index=False)
                logging.info(f"Saved {strategy} results to {filename}")

    return all_results

# ──────────────────────────────────────────────────────────────────────────────
# Convenience wrapper used by dashboards (unchanged API)
# ──────────────────────────────────────────────────────────────────────────────

async def run_scan(timeframes, exchanges, strategies, min_volume_usd=None):
    results = []
    result = await run_parallel_multi_timeframes_all_exchanges(
        timeframes=timeframes,
        strategies=strategies,
        exchanges=exchanges,
        users=["default"],
        send_telegram=False,
        min_volume_usd=min_volume_usd
    )
    # NOTE: result is a dict[strategy] -> list[dict]; flatten if needed
    for strategy, rows in result.items():
        for detection in rows:
            results.append({
                'Symbol': detection.get('symbol'),
                'Exchange': detection.get('exchange'),
                'Timeframe': detection.get('timeframe'),
                'Strategy': strategy,
                'Detected': True,
                'Volume': detection.get('volume_usd'),
                'Scan_Price': detection.get('close'),
                'Scan_Time': pd.Timestamp.now(tz='UTC')
            })
    return pd.DataFrame(results)

# # ──────────────────────────────────────────────────────────────────────────────
# # CLI
# # ──────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     if len(sys.argv) < 3:
#         print("Usage: python run_parallel_scanner.py <timeframe> <strategies> [exchanges] [users] [send_telegram] [save_to_csv]")
#         print()
#         print("Examples:")
#         print("  python run_parallel_scanner.py 1w 'loaded_bar,breakout_bar' 'sf_kucoin_1w,sf_mexc_1w' 'default' true true")
#         print("  python run_parallel_scanner.py 4h 'confluence,test_bar' 'binance_spot,bybit_spot' 'default' true false")
#         print("  python run_parallel_scanner.py 1d 'consolidation_breakout,channel_breakout' 'all' 'default' true true")
#         sys.exit(1)

#     timeframe = sys.argv[1]
#     strategies = sys.argv[2].split(',')

#     if len(sys.argv) > 3:
#         exchange_arg = sys.argv[3]
#         if exchange_arg == 'all':
#             exchanges = all_exchanges
#         elif exchange_arg == 'sf_1w':
#             exchanges = sf_exchanges_1w
#         elif exchange_arg == 'spot':
#             exchanges = spot_exchanges
#         elif exchange_arg == 'futures':
#             exchanges = futures_exchanges
#         else:
#             exchanges = exchange_arg.split(',')
#     else:
#         exchanges = None

#     users = sys.argv[4].split(',') if len(sys.argv) > 4 else ["default"]
#     send_telegram = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
#     save_to_csv = sys.argv[6].lower() == 'true' if len(sys.argv) > 6 else False

#     try:
#         asyncio.run(run_parallel_exchanges(timeframe, strategies, exchanges, users, send_telegram, save_to_csv=save_to_csv))
#     except ValueError as e:
#         logging.error(f"Configuration error: {e}")
#         sys.exit(1)
