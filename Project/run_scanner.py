#run_scanner.py

import asyncio
import sys
import os
import logging
from IPython.display import display
import pandas as pd
import nest_asyncio

project_dir = os.path.join(os.getcwd(), "Project")
sys.path.insert(0, project_dir)
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(message)s')

from scanner.main import run_scanner
from utils.config import get_telegram_config

def print_header(text):
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")

async def run(exchange, timeframe, strategies, users=["default"], send_telegram=True, min_volume_usd=None):
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    print_header(f"RUNNING SCAN ON {exchange.upper()} {timeframe}")
    print(f"• Exchange: {exchange.replace('_futures', ' Futures').replace('_spot', ' Spot').title()}")
    print(f"• Timeframe: {timeframe}")
    print(f"• Strategies: {', '.join(strategies)}")
    print(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    print(f"• Recipients: {', '.join(users)}")
    print("\nFetching market data...")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None
    results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
    
    print_header("SCAN RESULTS")
    total_signals = sum(len(res) for res in results.values())
    print(f"Total signals found: {total_signals}")
    
    for strategy, res in results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values('symbol') if 'symbol' in df.columns else df
            print(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)

async def run_all_exchanges(timeframe, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None):
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    print_header(f"RUNNING SCAN ON ALL EXCHANGES {timeframe}")
    print(f"• Exchanges: {', '.join(exchanges)}")
    print(f"• Timeframe: {timeframe}")
    print(f"• Strategies: {', '.join(strategies)}")
    print(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    print(f"• Recipients: {', '.join(users)}")
    print("\nFetching market data...")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None
    all_results = {}
    
    for exchange in exchanges:
        logging.info(f"Scanning {exchange}...")
        try:
            # Pass the min_volume_usd parameter to run_scanner
            results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
            for strategy, res in results.items():
                if strategy not in all_results:
                    all_results[strategy] = []
                all_results[strategy].extend([{**r, 'exchange': exchange} for r in res])
        except Exception as e:
            logging.error(f"Error scanning {exchange}: {str(e)}")

    # ... rest of the function remains the same

    print_header("COMBINED SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    print(f"Total signals found across all exchanges: {total_signals}")
    
    for strategy, res in all_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['exchange', 'symbol']) if 'symbol' in df.columns else df
            print(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_scanner.py <exchange> <timeframe> <strategies> [users] [send_telegram]")
        sys.exit(1)
    
    exchange = sys.argv[1]
    timeframe = sys.argv[2]
    strategies = sys.argv[3].split(',')
    users = sys.argv[4].split(',') if len(sys.argv) > 4 else ["default"]
    send_telegram = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    
    asyncio.run(run(exchange, timeframe, strategies, users, send_telegram))

async def run_multi_timeframes(exchange, timeframes, strategies, users=["default"], send_telegram=True, min_volume_usd=None):
    """
    Run scans on multiple timeframes for the same exchange and strategies
    
    Args:
        exchange (str): Exchange to scan (e.g., "binance_futures")
        timeframes (list): List of timeframes to scan (e.g., ["1d", "2d", "4h"])
        strategies (list): List of strategies to run
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        
    Returns:
        dict: Combined results across all timeframes
    """
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    print_header(f"RUNNING MULTI-TIMEFRAME SCAN ON {exchange.upper()}")
    print(f"• Exchange: {exchange.replace('_futures', ' Futures').replace('_spot', ' Spot').title()}")
    print(f"• Timeframes: {', '.join(timeframes)}")
    print(f"• Strategies: {', '.join(strategies)}")
    print(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    print(f"• Recipients: {', '.join(users)}")
    
    # Store results from all timeframes
    all_timeframe_results = {}
    
    for timeframe in timeframes:
        print(f"\nScanning {timeframe} timeframe...")
        telegram_config = get_telegram_config(strategies, users) if send_telegram else None
        results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
        
        # Add timeframe to each result
        for strategy, res_list in results.items():
            for res in res_list:
                res['timeframe'] = timeframe
            
            # Initialize strategy in all_timeframe_results if not already there
            if strategy not in all_timeframe_results:
                all_timeframe_results[strategy] = []
            
            # Add results to combined list
            all_timeframe_results[strategy].extend(res_list)
    
    # Print combined results
    print_header("MULTI-TIMEFRAME SCAN RESULTS")
    total_signals = sum(len(res) for res in all_timeframe_results.values())
    print(f"Total signals found across all timeframes: {total_signals}")
    
    for strategy, res in all_timeframe_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['timeframe', 'symbol']) if 'symbol' in df.columns else df
            print(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)
    
    return all_timeframe_results

async def run_multi_timeframes_all_exchanges(timeframes, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None):
    """
    Run scans on multiple timeframes across multiple exchanges
    
    Args:
        timeframes (list): List of timeframes to scan (e.g., ["1d", "2d", "4h"])
        strategies (list): List of strategies to run
        exchanges (list): List of exchanges to scan (or None for all)
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        
    Returns:
        dict: Combined results across all timeframes and exchanges
    """
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    print_header(f"RUNNING MULTI-TIMEFRAME SCAN ON ALL EXCHANGES")
    print(f"• Exchanges: {', '.join(exchanges)}")
    print(f"• Timeframes: {', '.join(timeframes)}")
    print(f"• Strategies: {', '.join(strategies)}")
    print(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    print(f"• Recipients: {', '.join(users)}")
    
    # Store results from all exchanges and timeframes
    all_results = {}
    
    for exchange in exchanges:
        logging.info(f"Scanning {exchange}...")
        try:
            for timeframe in timeframes:
                logging.info(f"  - Timeframe {timeframe}...")
                
                telegram_config = get_telegram_config(strategies, users) if send_telegram else None
                results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
                
                for strategy, res_list in results.items():
                    for res in res_list:
                        res['timeframe'] = timeframe
                        res['exchange'] = exchange
                    
                    if strategy not in all_results:
                        all_results[strategy] = []
                    
                    all_results[strategy].extend(res_list)
        except Exception as e:
            logging.error(f"Error scanning {exchange}: {str(e)}")
    
    # Print combined results
    print_header("MULTI-TIMEFRAME MULTI-EXCHANGE SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    print(f"Total signals found across all exchanges and timeframes: {total_signals}")
    
    for strategy, res in all_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['exchange', 'timeframe', 'symbol']) if 'symbol' in df.columns else df
            print(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)
    
    return all_results

async def run_optimized_scans(timeframes=None, users=["default"], send_telegram=True, min_volume_usd=None):
    """
    Run scans using the optimal strategy-timeframe-exchange combinations
    with intelligent cache management for derived timeframes
    
    Args:
        timeframes (list): Timeframes to scan (default: all ["4h", "1d", "2d", "1w"])
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        
    Returns:
        dict: Combined results across all strategies, timeframes, and exchanges
    """
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    # Define exchange groups
    spot_exchanges = ["binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"]
    futures_exchanges = ["binance_futures", "bybit_futures", "gateio_futures", "mexc_futures"]
    
    # Define all possible timeframes
    all_timeframes = ["4h", "1d", "2d", "1w"]
    
    # Use provided timeframes or default to all
    if timeframes is None:
        timeframes = all_timeframes
    else:
        # Ensure timeframes list contains valid values
        timeframes = [tf for tf in timeframes if tf in all_timeframes]
        
        # If 2d is requested but 1d is not, add 1d since 2d is derived from it
        if "2d" in timeframes and "1d" not in timeframes:
            timeframes.append("1d")
            print("Note: Added 1d timeframe since it's required to build 2d candles")
            
        # If 1w is requested but 1d is not, add 1d for exchanges that build weekly from daily
        if "1w" in timeframes and "1d" not in timeframes:
            timeframes.append("1d")
            print("Note: Added 1d timeframe since it's required to build weekly candles for some exchanges")
    
    # Assign strategies to timeframes and exchange types
    timeframe_strategy_map = {
        # Format: timeframe: {exchange_type: [strategies]}
        "4h": {
            "spot": ["breakout_bar"],
            "futures": ["reversal_bar", "volume_surge"]
        },
        "1d": {
            "spot": ["breakout_bar"],
            "futures": ["reversal_bar", "volume_surge"]
        },
        "2d": {
            "spot": ["breakout_bar", "start_bar"],
            "futures": ["reversal_bar", "volume_surge", "pin_down"]
        },
        "1w": {
            "spot": ["breakout_bar", "start_bar"],
            "futures": ["reversal_bar", "volume_surge", "pin_down"]
        }
    }
    
    print_header("RUNNING OPTIMIZED STRATEGY SCANS")
    print(f"• Timeframes: {', '.join(sorted(timeframes))}")
    print(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    print(f"• Recipients: {', '.join(users)}")
    
    # Store results from all combinations
    all_results = {}
    
    # Process timeframes in order of priority: 4h -> 1d -> 2d -> 1w
    for priority_tf in ["4h", "1d", "2d", "1w"]:
        # Skip if this timeframe is not in the requested list
        if priority_tf not in timeframes:
            continue
            
        print(f"\nProcessing {priority_tf} timeframe...")
        
        # Clear cache before processing a new timeframe
        from scanner.main import kline_cache
        kline_cache.clear()
        logging.info(f"Cache cleared before processing {priority_tf} timeframe")
        
        # Handle special case: Reuse 1d candles for 2d
        if priority_tf == "2d" and "1d" in timeframes:
            logging.info(f"Reusing 1d candles for building 2d candles")
            # Note: No need to clear cache here as we want to keep the 1d data
        
        # Handle special case: Reuse 1d candles for 1w
        if priority_tf == "1w" and "1d" in timeframes:
            logging.info(f"Reusing 1d candles for building weekly candles where needed")
            # Note: No need to clear cache here as we want to keep the 1d data
        
        # Process spot exchanges for this timeframe
        if timeframe_strategy_map[priority_tf]["spot"]:
            spot_strategies = timeframe_strategy_map[priority_tf]["spot"]
            for exchange in spot_exchanges:
                try:
                    logging.info(f"Scanning {exchange} {priority_tf} for {', '.join(spot_strategies)}")
                    
                    # Prepare telegram config for these strategies
                    telegram_config = get_telegram_config(spot_strategies, users) if send_telegram else None
                    
                    # Run scanner for this exchange-timeframe combination
                    results = await run_scanner(exchange, priority_tf, spot_strategies, telegram_config, min_volume_usd)
                    
                    # Process and store results
                    for strategy, res_list in results.items():
                        for res in res_list:
                            res['timeframe'] = priority_tf
                            res['exchange'] = exchange
                        
                        if strategy not in all_results:
                            all_results[strategy] = []
                        
                        all_results[strategy].extend(res_list)
                except Exception as e:
                    logging.error(f"Error scanning {exchange} {priority_tf}: {str(e)}")
        
        # Process futures exchanges for this timeframe
        if timeframe_strategy_map[priority_tf]["futures"]:
            futures_strategies = timeframe_strategy_map[priority_tf]["futures"]
            for exchange in futures_exchanges:
                try:
                    logging.info(f"Scanning {exchange} {priority_tf} for {', '.join(futures_strategies)}")
                    
                    # Prepare telegram config for these strategies
                    telegram_config = get_telegram_config(futures_strategies, users) if send_telegram else None
                    
                    # Run scanner for this exchange-timeframe combination
                    results = await run_scanner(exchange, priority_tf, futures_strategies, telegram_config, min_volume_usd)
                    
                    # Process and store results
                    for strategy, res_list in results.items():
                        for res in res_list:
                            res['timeframe'] = priority_tf
                            res['exchange'] = exchange
                        
                        if strategy not in all_results:
                            all_results[strategy] = []
                        
                        all_results[strategy].extend(res_list)
                except Exception as e:
                    logging.error(f"Error scanning {exchange} {priority_tf}: {str(e)}")
    
    # Print combined results
    print_header("OPTIMIZED SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    print(f"Total signals found: {total_signals}")
    
    for strategy, res in all_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['exchange', 'timeframe', 'symbol']) if 'symbol' in df.columns else df
            print(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)
    
    return all_results