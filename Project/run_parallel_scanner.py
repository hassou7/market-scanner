#run_parallel_scanner.py
"""
Parallel Market Scanner Runner

This script provides functions to run market scans on cryptocurrency exchanges in parallel.
It supports both Jupyter Notebook interactive use and standalone execution.
Updated with SF exchange support for KuCoin and MEXC 1w data.
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
    
    # Remove columns that exist in the dataframe
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

# Define exchange groups including SF exchanges
futures_exchanges = ["binance_futures", "bybit_futures", "gateio_futures", "mexc_futures"]
spot_exchanges = ["binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"]
spot_exchanges_1w = ["binance_spot", "bybit_spot", "gateio_spot"]

# New SF exchange group for 1w data from KuCoin and MEXC
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]

# All available exchanges including SF
all_exchanges = futures_exchanges + spot_exchanges + sf_exchanges_1w

# Validation function for SF exchanges
def validate_sf_exchange_timeframe(exchanges, timeframes):
    """Validate that SF exchanges are only used with compatible timeframes"""
    sf_exchanges = ["sf_kucoin_1w", "sf_mexc_1w"]
    
    for exchange in exchanges:
        if exchange in sf_exchanges:
            # SF exchanges only support 1w
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

async def scan_exchange(exchange, timeframe, strategies, telegram_config, min_volume_usd):
    """Run scan on a single exchange with progress logging"""
    try:
        start_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{start_time}] Starting scan on {exchange} for {timeframe} timeframe...")
        
        # Run scanner
        results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
        
        # Count signals
        signal_count = sum(len(res) for res in results.values())
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{end_time}] ✓ Completed {exchange} scan: {signal_count} signals found")
        
        return exchange, results
    except Exception as e:
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.error(f"[{end_time}] ✗ Error scanning {exchange}: {str(e)}")
        return exchange, {}

async def run_parallel_exchanges(timeframe, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None, save_to_csv=False):
    """Run scans on multiple exchanges in parallel.
    
    Args:
        timeframe (str): Timeframe to scan (e.g., "1d", "4h", "1w")
        strategies (list): List of strategies to run
        exchanges (list): List of exchanges to scan (or None for all)
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        save_to_csv (bool): Whether to save results to CSV files
        
    Returns:
        dict: Combined results from all exchanges
    """
    start_time = datetime.now()
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    # Add SF exchange validation
    validate_sf_exchange_timeframe(exchanges, [timeframe])
    
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
    
    # Create tasks for all exchanges to run in parallel
    tasks = []
    for exchange in exchanges:
        tasks.append(scan_exchange(exchange, timeframe, strategies, telegram_config, min_volume_usd))
    
    # Run all tasks concurrently and collect results
    exchange_results = await asyncio.gather(*tasks)
    
    # Process results and handle any exceptions
    all_results = {}
    for exchange, result in exchange_results:
        # Add exchange name to each result entry
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

async def scan_exchange_timeframe(exchange, timeframe, strategies, telegram_config, min_volume_usd):
    """Run scan for a specific exchange and timeframe with progress logging"""
    try:
        start_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{start_time}] Starting scan on {exchange} - {timeframe} timeframe...")
        
        # Run scanner
        results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
        
        # Count signals
        signal_count = sum(len(res) for res in results.values())
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"[{end_time}] ✓ Completed {exchange} - {timeframe}: {signal_count} signals found")
        
        return exchange, timeframe, results
    except Exception as e:
        end_time = datetime.now().strftime("%H:%M:%S")
        logging.error(f"[{end_time}] ✗ Error scanning {exchange} - {timeframe}: {str(e)}")
        return exchange, timeframe, {}

async def run_parallel_multi_timeframes_all_exchanges(timeframes, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None, save_to_csv=False):
    """
    Run scans on multiple timeframes across multiple exchanges in parallel
    
    Args:
        timeframes (list): List of timeframes to scan (e.g., ["1d", "2d", "4h"])
        strategies (list): List of strategies to run
        exchanges (list): List of exchanges to scan (or None for all)
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        save_to_csv (bool): Whether to save results to CSV files
        
    Returns:
        dict: Combined results across all timeframes and exchanges
    """
    # Set environment variable to disable progress bars
    os.environ["DISABLE_PROGRESS"] = "1"
    
    start_time = datetime.now()
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    
    # Smart exchange selection based on timeframes
    if exchanges is None:
        if timeframes == ["1w"] or all(tf == "1w" for tf in timeframes):
            exchanges = sf_exchanges_1w  # Use SF exchanges for 1w-only scans
        else:
            exchanges = default_exchanges  # Use regular exchanges for other timeframes
    
    # Add SF exchange validation
    validate_sf_exchange_timeframe(exchanges, timeframes)
    
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
    
    # Process timeframes in order (to optimize cache usage)
    all_results = {}
    
    for timeframe in timeframes:
        kline_cache.clear()  # Clear cache between timeframes
        logging.info(f"Processing {timeframe} timeframe")
        
        # Create tasks for all exchanges for this timeframe
        tasks = []
        for exchange in exchanges:
            tasks.append(scan_exchange(exchange, timeframe, strategies, telegram_config, min_volume_usd))
        
        # Run all tasks concurrently 
        exchange_results = await asyncio.gather(*tasks)
        
        # Process results
        for exchange, result in exchange_results:
            for strategy, res_list in result.items():
                for res in res_list:
                    res['timeframe'] = timeframe
                    res['exchange'] = exchange
                
                if strategy not in all_results:
                    all_results[strategy] = []
                
                all_results[strategy].extend(res_list)
        
        # Small delay between timeframes
        await asyncio.sleep(2)
    
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

async def run_scan(timeframes, exchanges, strategies, min_volume_usd=None):
    results = []  # List to collect detections
    result = await run_parallel_multi_timeframes_all_exchanges(
        timeframes=timeframes,
        strategies=strategies,
        exchanges=exchanges,
        users=["default"],  # Or None if not sending Telegram
        send_telegram=False,  # Disable for dashboard
        min_volume_usd=min_volume_usd
    )
    # Assuming 'result' is a dict/list of detections; loop and append
    for detection in result:  # Adjust based on your actual result format
        results.append({
            'Symbol': detection['symbol'],
            'Exchange': detection['exchange'],
            'Timeframe': detection['timeframe'],
            'Strategy': detection['strategy'],
            'Detected': True,
            'Volume': detection['volume_usd'],
            'Scan_Price': detection['current_price'],  # Fetch price at scan time
            'Scan_Time': pd.Timestamp.now()
        })
    return pd.DataFrame(results)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_parallel_scanner.py <timeframe> <strategies> [exchanges] [users] [send_telegram] [save_to_csv]")
        print()
        print("Examples:")
        print("  python run_parallel_scanner.py 1w 'loaded_bar,breakout_bar' 'sf_kucoin_1w,sf_mexc_1w' 'default' true true")
        print("  python run_parallel_scanner.py 4h 'confluence,test_bar' 'binance_spot,bybit_spot' 'default' true false")
        print("  python run_parallel_scanner.py 1d 'consolidation_breakout,channel_breakout' 'all' 'default' true true")
        sys.exit(1)
    
    timeframe = sys.argv[1]
    strategies = sys.argv[2].split(',')
    
    # Handle exchange argument
    if len(sys.argv) > 3:
        exchange_arg = sys.argv[3]
        if exchange_arg == 'all':
            exchanges = all_exchanges
        elif exchange_arg == 'sf_1w':
            exchanges = sf_exchanges_1w
        elif exchange_arg == 'spot':
            exchanges = spot_exchanges
        elif exchange_arg == 'futures':
            exchanges = futures_exchanges
        else:
            exchanges = exchange_arg.split(',')
    else:
        exchanges = None
    
    users = sys.argv[4].split(',') if len(sys.argv) > 4 else ["default"]
    send_telegram = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    save_to_csv = sys.argv[6].lower() == 'true' if len(sys.argv) > 6 else False
    
    try:
        asyncio.run(run_parallel_exchanges(timeframe, strategies, exchanges, users, send_telegram, save_to_csv=save_to_csv))
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        sys.exit(1)