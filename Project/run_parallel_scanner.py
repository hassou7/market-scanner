#run_parallel_scanner.py
#!/usr/bin/env python3
"""
Parallel Market Scanner Runner

This script provides functions to run market scans on cryptocurrency exchanges in parallel.
It supports both Jupyter Notebook interactive use and standalone execution.
"""

import asyncio
import sys
import os
import logging
import pandas as pd
import nest_asyncio
from datetime import datetime

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

async def run_parallel_exchanges(timeframe, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None):
    """Run scans on multiple exchanges in parallel.
    
    Args:
        timeframe (str): Timeframe to scan (e.g., "1d", "4h", "1w")
        strategies (list): List of strategies to run
        exchanges (list): List of exchanges to scan (or None for all)
        users (list): List of users to notify
        send_telegram (bool): Whether to send Telegram notifications
        min_volume_usd (float): Minimum USD volume threshold (or None to use defaults)
        
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
    
    print_header(f"RUNNING PARALLEL SCANS ON ALL EXCHANGES {timeframe}")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframe: {timeframe}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
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
            
            all_results[strategy].extend([{**r, 'exchange': exchange} for r in res_list])
    
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
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['exchange', 'symbol']) if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)
    
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

async def run_parallel_multi_timeframes_all_exchanges(timeframes, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None):
    """
    Run scans on multiple timeframes across multiple exchanges in parallel
    
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
    # Set environment variable to disable progress bars
    os.environ["DISABLE_PROGRESS"] = "1"
    
    start_time = datetime.now()
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    print_header(f"RUNNING PARALLEL MULTI-TIMEFRAME SCAN ON ALL EXCHANGES")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframes: {', '.join(timeframes)}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
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
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['exchange', 'timeframe', 'symbol']) if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)
    
    return all_results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        logging.info("Usage: python run_parallel_scanner.py <timeframe> <strategies> [exchanges] [users] [send_telegram]")
        sys.exit(1)
    
    timeframe = sys.argv[1]
    strategies = sys.argv[2].split(',')
    exchanges = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    users = sys.argv[4].split(',') if len(sys.argv) > 4 else ["default"]
    send_telegram = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    
    asyncio.run(run_parallel_exchanges(timeframe, strategies, exchanges, users, send_telegram))