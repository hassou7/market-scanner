#!/usr/bin/env python3
"""
AWS Scanner Service

This script runs on an AWS server to scan multiple exchanges on different timeframes.
It respects the specific timing requirements for 2d, 3d, 4d and 1w candles based on exchange implementations.
Sequential scanning per exchange - no parallel scanning within same exchange.

Usage:
    python aws_scanner_service.py [--debug]

Options:
    --debug    Enable debug logging
"""

import asyncio
import sys
import os
import argparse
import logging
import signal
from datetime import datetime, timedelta, time
import time as time_module
import pandas as pd

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_dir)

from scanner.main import kline_cache
kline_cache.clear()  # Clear cache for fresh data

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level to project root
sys.path.insert(0, project_root)

# Configure logging
def setup_logging(debug_mode=False):
    level = logging.DEBUG if debug_mode else logging.INFO
    
    logs_dir = os.path.join(current_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, "scanner_service.log")
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file)
        ]
    )
    
    logging.getLogger('telegram').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    return logging.getLogger("ScannerService")

parser = argparse.ArgumentParser(description="AWS Market Scanner Service")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
args = parser.parse_args()

logger = setup_logging(args.debug)

spot_exchanges = [
    "binance_spot",
    "bybit_spot", 
    "gateio_spot",
    "kucoin_spot",
    "mexc_spot"
]

futures_exchanges = [
    "binance_futures",
    "bybit_futures",
    "gateio_futures",
    "mexc_futures"
]

# Configuration for each scan - one scan per timeframe per exchange type
scan_configs = [
    # 4h scans
    {
        "timeframe": "4h",
        "strategies": ["volume_surge"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "4h",
        "strategies": ["breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    
    # 1d scans
    {
        "timeframe": "1d",
        "strategies": ["reversal_bar", "volume_surge"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1d",
        "strategies": ["breakout_bar", "loaded_bar", "volume_surge"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    
    # 2d scans
    {
        "timeframe": "2d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "2d",
        "strategies": ["start_bar", "breakout_bar", "volume_surge", "loaded_bar", "confluence"],
        "exchanges": spot_exchanges,
        "users": ["default", "user2"],  # Added user2 for confluence
        "send_telegram": True,
        "min_volume_usd": None
    },
    
    # 3d scans
    {
        "timeframe": "3d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "3d",
        "strategies": ["start_bar", "breakout_bar", "volume_surge", "loaded_bar", "confluence"],
        "exchanges": spot_exchanges,
        "users": ["default", "user2"],  # Added user2 for confluence
        "send_telegram": True,
        "min_volume_usd": None
    },
    
    # 4d scans
    {
        "timeframe": "4d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "4d",
        "strategies": ["start_bar", "breakout_bar", "volume_surge", "loaded_bar", "confluence"],
        "exchanges": spot_exchanges,
        "users": ["default", "user2"],  # Added user2 for confluence
        "send_telegram": True,
        "min_volume_usd": None
    },
    
    # 1w scans
    {
        "timeframe": "1w",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1w",
        "strategies": ["start_bar", "breakout_bar", "volume_surge", "loaded_bar", "confluence"],
        "exchanges": spot_exchanges,
        "users": ["default", "user2"],  # Added user2 for confluence
        "send_telegram": True,
        "min_volume_usd": None
    }
]

def get_next_candle_time(interval="4h"):
    """
    Calculate time until next candle close for a given interval
    
    Args:
        interval (str): Timeframe interval ('4h', '1d', '2d', '3d', '4d', '1w')
        
    Returns:
        datetime: Next candle close time in UTC
    """
    now = datetime.utcnow()
    
    if interval == "4h":
        current_hour = now.hour
        next_4h = ((current_hour // 4) + 1) * 4
        if next_4h >= 24:
            next_4h = 0
            next_time = now.replace(hour=next_4h, minute=1, second=0, microsecond=0)
            if next_4h <= current_hour:
                next_time += timedelta(days=1)
        else:
            next_time = now.replace(hour=next_4h, minute=1, second=0, microsecond=0)
        # Ensure the time is in the future
        while next_time <= now:
            next_time += timedelta(hours=4)
    
    elif interval == "1d":
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        # If the current time is past 00:01 today, schedule for tomorrow
        if now >= next_time:
            next_time += timedelta(days=1)
    
    elif interval == "2d":
        reference_date = pd.Timestamp('2025-03-20').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        period = days_diff // 2
        next_period_start = reference_date + timedelta(days=period * 2 + 2)
        next_time = datetime.combine(next_period_start, time(0, 1, 0))
        if now >= next_time:
            next_time = datetime.combine(next_period_start + timedelta(days=2), time(0, 1, 0))
        # Ensure the time is in the future
        while next_time <= now:
            next_time += timedelta(days=2)
    
    elif interval == "3d":
        reference_date = pd.Timestamp('2025-03-20').normalize()  # Same as 2d
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        period = days_diff // 3
        next_period_start = reference_date + timedelta(days=period * 3 + 3)
        next_time = datetime.combine(next_period_start, time(0, 1, 0))
        if now >= next_time:
            next_time = datetime.combine(next_period_start + timedelta(days=3), time(0, 1, 0))
        # Ensure the time is in the future
        while next_time <= now:
            next_time += timedelta(days=3)
    
    elif interval == "4d":
        reference_date = pd.Timestamp('2025-03-22').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        period = days_diff // 4
        next_period_start = reference_date + timedelta(days=period * 4 + 4)
        next_time = datetime.combine(next_period_start, time(0, 1, 0))
        if now >= next_time:
            next_time = datetime.combine(next_period_start + timedelta(days=4), time(0, 1, 0))
        # Ensure the time is in the future
        while next_time <= now:
            next_time += timedelta(days=4)
    
    elif interval == "1w":
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0 and now.minute >= 1:
            days_until_monday = 7
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        next_time += timedelta(days=days_until_monday)
        # Ensure the time is in the future
        while next_time <= now:
            next_time += timedelta(days=7)
    
    else:
        logger.warning(f"Unrecognized interval: {interval}, defaulting to 4h")
        return get_next_candle_time("4h")
    
    return next_time

async def run_timeframe_scans(timeframe, configs_for_timeframe):
    """
    Run all scans for a specific timeframe:
    1. Execute strategies one by one (sequential)
    2. For each strategy, scan all exchanges in parallel
    3. Reuse cached data within the timeframe
    4. Confluence strategy runs first if present
    """
    logger.info(f"Starting {timeframe} timeframe scans")
    
    # Group configs by exchange type (futures vs spot) and extract strategies
    futures_configs = [c for c in configs_for_timeframe if any(e in c['exchanges'] for e in futures_exchanges)]
    spot_configs = [c for c in configs_for_timeframe if any(e in c['exchanges'] for e in spot_exchanges)]
    
    # Extract unique strategies from each type and prioritize confluence
    def get_strategy_order(configs):
        strategies = []
        for config in configs:
            for strategy in config['strategies']:
                if strategy not in strategies:
                    strategies.append(strategy)
        
        # Move confluence to the front if present
        if 'confluence' in strategies:
            strategies.remove('confluence')
            strategies.insert(0, 'confluence')
        
        return strategies
    
    futures_strategies = get_strategy_order(futures_configs) if futures_configs else []
    spot_strategies = get_strategy_order(spot_configs) if spot_configs else []
    
    logger.info(f"{timeframe} - Futures strategies: {futures_strategies}")
    logger.info(f"{timeframe} - Spot strategies: {spot_strategies}")
    
    total_signals = 0
    
    # Run futures strategies sequentially
    if futures_strategies:
        logger.info(f"Running {len(futures_strategies)} futures strategies for {timeframe}")
        for strategy in futures_strategies:
            # Find the config that contains this strategy
            strategy_config = None
            for config in futures_configs:
                if strategy in config['strategies']:
                    strategy_config = config.copy()
                    strategy_config['strategies'] = [strategy]  # Run only this strategy
                    break
            
            if strategy_config:
                logger.info(f"Running {strategy} on futures exchanges for {timeframe}")
                signals = await run_single_strategy_scan(strategy_config)
                total_signals += signals
                logger.info(f"Completed {strategy} for {timeframe} futures: {signals} signals")
                
                # Short delay between strategies
                await asyncio.sleep(5)
    
    # Run spot strategies sequentially  
    if spot_strategies:
        logger.info(f"Running {len(spot_strategies)} spot strategies for {timeframe}")
        for strategy in spot_strategies:
            # Find the config that contains this strategy
            strategy_config = None
            for config in spot_configs:
                if strategy in config['strategies']:
                    strategy_config = config.copy()
                    strategy_config['strategies'] = [strategy]  # Run only this strategy
                    break
            
            if strategy_config:
                logger.info(f"Running {strategy} on spot exchanges for {timeframe}")
                signals = await run_single_strategy_scan(strategy_config)
                total_signals += signals
                logger.info(f"Completed {strategy} for {timeframe} spot: {signals} signals")
                
                # Short delay between strategies
                await asyncio.sleep(5)
    
    logger.info(f"Completed {timeframe} timeframe. Total signals: {total_signals}")
    return total_signals

async def run_single_strategy_scan(config):
    """Run a single strategy scan across multiple exchanges in parallel"""
    try:
        from run_parallel_scanner import run_parallel_exchanges
        
        timeframe = config['timeframe']
        strategy = config['strategies'][0]  # Should be only one strategy
        exchanges = config['exchanges']
        users = config['users']
        
        logger.info(f"Running {strategy} strategy on {len(exchanges)} exchanges for {timeframe}")
        
        result = await run_parallel_exchanges(
            timeframe=timeframe,
            strategies=[strategy],
            exchanges=exchanges,
            users=users,
            send_telegram=config['send_telegram'],
            min_volume_usd=config['min_volume_usd']
        )
        
        signal_count = sum(len(signals) for signals in result.values())
        return signal_count
        
    except Exception as e:
        logger.error(f"Error running {config['timeframe']} {config['strategies'][0]} scan: {str(e)}")
        return 0

async def run_scheduled_scans():
    """
    Run scans based on their scheduled times:
    1. Timeframes execute sequentially (4h -> 1d -> 2d -> 3d -> 4d -> 1w)
    2. Within each timeframe, strategies execute sequentially 
    3. Within each strategy, exchanges execute in parallel
    4. Cache is reused within timeframe, cleared between timeframes
    """
    while True:
        try:
            now = datetime.utcnow()
            logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # Group configs by timeframe
            timeframes_to_run = {}
            
            # Check each scan config to see if it should run now
            for config in scan_configs:
                timeframe = config['timeframe']
                next_candle_time = get_next_candle_time(timeframe)
                
                # Check if it's time to run (within 1 minute of candle close)
                time_diff = (next_candle_time - now).total_seconds()
                
                # Run scan if we're within 1 minute after the scheduled time
                if -60 <= time_diff <= 60:
                    if timeframe not in timeframes_to_run:
                        timeframes_to_run[timeframe] = []
                    timeframes_to_run[timeframe].append(config)
            
            if timeframes_to_run:
                logger.info(f"Running scans for timeframes: {list(timeframes_to_run.keys())}")
                
                # Process timeframes in order: 4h -> 1d -> 2d -> 3d -> 4d -> 1w
                timeframe_priority = ["4h", "1d", "2d", "3d", "4d", "1w"]
                
                for timeframe in timeframe_priority:
                    if timeframe in timeframes_to_run:
                        # Clear cache before each timeframe
                        kline_cache.clear()
                        logger.info(f"Cache cleared before {timeframe} timeframe")
                        
                        # Run all strategies for this timeframe
                        await run_timeframe_scans(timeframe, timeframes_to_run[timeframe])
                        
                        # Wait 30 seconds between timeframes
                        logger.info(f"Waiting 30 seconds before next timeframe")
                        await asyncio.sleep(30)
                        
                logger.info("All scheduled scans completed")
            
            # Calculate next check time
            next_scan_times = []
            for config in scan_configs:
                next_time = get_next_candle_time(config['timeframe'])
                next_scan_times.append(next_time)
            
            if next_scan_times:
                next_scan = min(next_scan_times)
                wait_time = max(30, (next_scan - datetime.utcnow()).total_seconds() - 30)  # Check 30s before
                logger.info(f"Next scan at {next_scan.strftime('%Y-%m-%d %H:%M:%S')} UTC. Waiting {wait_time/60:.1f} minutes")
                await asyncio.sleep(min(wait_time, 1800))  # Max 30 minutes sleep
            else:
                await asyncio.sleep(300)  # 5 minutes default
                
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            logger.info("Waiting 2 minutes before retrying...")
            await asyncio.sleep(120)

def main():
    """Main entry point of the scanner service"""
    logger.info("Market Scanner Service starting up")
    logger.info(f"Project root directory: {project_root}")
    logger.info(f"Configured {len(scan_configs)} scan configurations")
    
    # Print scan configurations
    for i, config in enumerate(scan_configs, 1):
        logger.info(f"Config {i}: {config['timeframe']} - {config['strategies']} - {len(config['exchanges'])} exchanges")
    
    # Create a new event loop
    loop = asyncio.get_event_loop()
    
    # Flag to track if shutdown has been initiated
    shutting_down = False
    
    async def shutdown():
        nonlocal shutting_down
        if shutting_down:
            return  # Prevent multiple shutdown attempts
        shutting_down = True
        
        logger.info("Received shutdown signal. Stopping scanner...")
        # Cancel all running tasks except the current one
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        # Wait for all tasks to complete their cancellation
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Run cleanup tasks
        try:
            await loop.shutdown_asyncgens()
        except Exception as e:
            logger.error(f"Error shutting down async generators: {str(e)}")
        
        # Stop the event loop
        loop.stop()
        logger.info("Scanner stopped gracefully")
    
    def handle_shutdown():
        # Schedule the shutdown coroutine to run in the event loop
        asyncio.ensure_future(shutdown())
    
    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown)
    
    try:
        loop.run_until_complete(run_scheduled_scans())
    except asyncio.CancelledError:
        logger.info("Scanner tasks cancelled during shutdown")
        if not shutting_down:
            loop.run_until_complete(shutdown())
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.info("Restarting service in 5 minutes...")
        time_module.sleep(300)
        main()
    except SystemExit:
        # Handle SystemExit explicitly to avoid logging it as an error
        pass

    # If shutdown was initiated, exit the process
    if shutting_down:
        sys.exit(0)

if __name__ == "__main__":
    main()