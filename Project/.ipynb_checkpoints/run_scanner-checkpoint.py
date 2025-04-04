#!/usr/bin/env python3
"""
Market Scanner Runner

This script provides functions to run market scans on cryptocurrency exchanges.
It supports both Jupyter Notebook interactive use and standalone execution.
"""

import asyncio
import sys
import os
import logging
import pandas as pd
import nest_asyncio

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

from scanner.main import run_scanner
from utils.config import get_telegram_config

def print_header(text):
    logging.info(f"\n{'='*80}")
    logging.info(f"  {text}")
    logging.info(f"{'='*80}\n")

async def run(exchange, timeframe, strategies, users=["default"], send_telegram=True, min_volume_usd=None):
    """Run a scan on a single exchange."""
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    print_header(f"RUNNING SCAN ON {exchange.upper()} {timeframe}")
    logging.info(f"• Exchange: {exchange.replace('_futures', ' Futures').replace('_spot', ' Spot').title()}")
    logging.info(f"• Timeframe: {timeframe}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    logging.info("\nFetching market data...")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None
    results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
    
    print_header("SCAN RESULTS")
    total_signals = sum(len(res) for res in results.values())
    logging.info(f"Total signals found: {total_signals}")
    
    for strategy, res in results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values('symbol') if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
            display(df)

async def run_all_exchanges(timeframe, strategies, exchanges=None, users=["default"], send_telegram=True, min_volume_usd=None):
    """Run scans across multiple exchanges."""
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    print_header(f"RUNNING SCAN ON ALL EXCHANGES {timeframe}")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframe: {timeframe}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    logging.info("\nFetching market data...")

    telegram_config = get_telegram_config(strategies, users) if send_telegram else None
    all_results = {}
    
    for exchange in exchanges:
        logging.info(f"Scanning {exchange}...")
        try:
            results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
            for strategy, res in results.items():
                if strategy not in all_results:
                    all_results[strategy] = []
                all_results[strategy].extend([{**r, 'exchange': exchange} for r in res])
        except Exception as e:
            logging.error(f"Error scanning {exchange}: {str(e)}")

    print_header("COMBINED SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    logging.info(f"Total signals found across all exchanges: {total_signals}")
    
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
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    print_header(f"RUNNING MULTI-TIMEFRAME SCAN ON {exchange.upper()}")
    logging.info(f"• Exchange: {exchange.replace('_futures', ' Futures').replace('_spot', ' Spot').title()}")
    logging.info(f"• Timeframes: {', '.join(timeframes)}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    
    all_timeframe_results = {}
    
    for timeframe in timeframes:
        logging.info(f"\nScanning {timeframe} timeframe...")
        telegram_config = get_telegram_config(strategies, users) if send_telegram else None
        results = await run_scanner(exchange, timeframe, strategies, telegram_config, min_volume_usd)
        
        for strategy, res_list in results.items():
            for res in res_list:
                res['timeframe'] = timeframe
            
            if strategy not in all_timeframe_results:
                all_timeframe_results[strategy] = []
            
            all_timeframe_results[strategy].extend(res_list)
    
    print_header("MULTI-TIMEFRAME SCAN RESULTS")
    total_signals = sum(len(res) for res in all_timeframe_results.values())
    logging.info(f"Total signals found across all timeframes: {total_signals}")
    
    for strategy, res in all_timeframe_results.items():
        if res:
            df = pd.DataFrame(res)
            for col in ['date', 'timestamp']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            df = df.sort_values(['timeframe', 'symbol']) if 'symbol' in df.columns else df
            logging.info(f"\n{strategy.replace('_', ' ').title()}: {len(res)} signals")
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
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "binance_futures", "bybit_futures", "gateio_futures", "mexc_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"
    ]
    exchanges = exchanges if exchanges is not None else default_exchanges
    
    print_header(f"RUNNING MULTI-TIMEFRAME SCAN ON ALL EXCHANGES")
    logging.info(f"• Exchanges: {', '.join(exchanges)}")
    logging.info(f"• Timeframes: {', '.join(timeframes)}")
    logging.info(f"• Strategies: {', '.join(strategies)}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    
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
    
    print_header("MULTI-TIMEFRAME MULTI-EXCHANGE SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    logging.info(f"Total signals found across all exchanges and timeframes: {total_signals}")
    
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
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    spot_exchanges = ["binance_spot", "bybit_spot", "gateio_spot", "mexc_spot", "kucoin_spot"]
    futures_exchanges = ["binance_futures", "bybit_futures", "gateio_futures", "mexc_futures"]
    
    all_timeframes = ["4h", "1d", "2d", "1w"]
    timeframes = timeframes if timeframes is not None else all_timeframes
    
    timeframes = [tf for tf in timeframes if tf in all_timeframes]
    if "2d" in timeframes and "1d" not in timeframes:
        timeframes.append("1d")
        logging.info("Note: Added 1d timeframe since it's required to build 2d candles")
    if "1w" in timeframes and "1d" not in timeframes:
        timeframes.append("1d")
        logging.info("Note: Added 1d timeframe since it's required to build weekly candles for some exchanges")
    
    timeframe_strategy_map = {
        "4h": {"spot": ["breakout_bar"], "futures": ["reversal_bar", "volume_surge"]},
        "1d": {"spot": ["breakout_bar"], "futures": ["reversal_bar", "volume_surge"]},
        "2d": {"spot": ["breakout_bar", "start_bar"], "futures": ["reversal_bar", "pin_down"]},
        "1w": {"spot": ["breakout_bar", "start_bar"], "futures": ["reversal_bar", "pin_down"]}
    }
    
    print_header("RUNNING OPTIMIZED STRATEGY SCANS")
    logging.info(f"• Timeframes: {', '.join(sorted(timeframes))}")
    logging.info(f"• Notifications: {'Enabled' if send_telegram else 'Disabled'}")
    logging.info(f"• Recipients: {', '.join(users)}")
    
    all_results = {}
    
    for priority_tf in ["4h", "1d", "2d", "1w"]:
        if priority_tf not in timeframes:
            continue
            
        logging.info(f"\nProcessing {priority_tf} timeframe...")
        from scanner.main import kline_cache
        kline_cache.clear()
        logging.info(f"Cache cleared before processing {priority_tf} timeframe")
        
        if priority_tf == "2d" and "1d" in timeframes:
            logging.info(f"Reusing 1d candles for building 2d candles")
        if priority_tf == "1w" and "1d" in timeframes:
            logging.info(f"Reusing 1d candles for building weekly candles where needed")
        
        if timeframe_strategy_map[priority_tf]["spot"]:
            spot_strategies = timeframe_strategy_map[priority_tf]["spot"]
            for exchange in spot_exchanges:
                try:
                    logging.info(f"Scanning {exchange} {priority_tf} for {', '.join(spot_strategies)}")
                    telegram_config = get_telegram_config(spot_strategies, users) if send_telegram else None
                    results = await run_scanner(exchange, priority_tf, spot_strategies, telegram_config, min_volume_usd)
                    
                    for strategy, res_list in results.items():
                        for res in res_list:
                            res['timeframe'] = priority_tf
                            res['exchange'] = exchange
                        if strategy not in all_results:
                            all_results[strategy] = []
                        all_results[strategy].extend(res_list)
                except Exception as e:
                    logging.error(f"Error scanning {exchange} {priority_tf}: {str(e)}")
        
        if timeframe_strategy_map[priority_tf]["futures"]:
            futures_strategies = timeframe_strategy_map[priority_tf]["futures"]
            for exchange in futures_exchanges:
                try:
                    logging.info(f"Scanning {exchange} {priority_tf} for {', '.join(futures_strategies)}")
                    telegram_config = get_telegram_config(futures_strategies, users) if send_telegram else None
                    results = await run_scanner(exchange, priority_tf, futures_strategies, telegram_config, min_volume_usd)
                    
                    for strategy, res_list in results.items():
                        for res in res_list:
                            res['timeframe'] = priority_tf
                            res['exchange'] = exchange
                        if strategy not in all_results:
                            all_results[strategy] = []
                        all_results[strategy].extend(res_list)
                except Exception as e:
                    logging.error(f"Error scanning {exchange} {priority_tf}: {str(e)}")
    
    print_header("OPTIMIZED SCAN RESULTS")
    total_signals = sum(len(res) for res in all_results.values())
    logging.info(f"Total signals found: {total_signals}")
    
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
    if len(sys.argv) < 4:
        logging.info("Usage: python run_scanner.py <exchange> <timeframe> <strategies> [users] [send_telegram]")
        sys.exit(1)
    
    exchange = sys.argv[1]
    timeframe = sys.argv[2]
    strategies = sys.argv[3].split(',')
    users = sys.argv[4].split(',') if len(sys.argv) > 4 else ["default"]
    send_telegram = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    
    asyncio.run(run(exchange, timeframe, strategies, users, send_telegram))