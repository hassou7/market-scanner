#!/usr/bin/env python3
"""
AWS Scanner Service

This script runs on an AWS server to scan multiple exchanges on different timeframes.
It respects the specific timing requirements for 2d and 1w candles based on exchange implementations.

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

futures_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "2d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1w",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    }
]

spot_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1d",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "2d",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1w",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    }
]

all_scan_configs = futures_scan_configs + spot_scan_configs

def get_next_candle_time(interval="4h"):
    """
    Calculate time until next candle close for a given interval
    
    Args:
        interval (str): Timeframe interval ('4h', '1d', '2d', '1w')
        
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
    
    elif interval == "1d":
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        if now.hour >= 0 and now.minute >= 1:
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
    
    elif interval == "1w":
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0 and now.minute >= 1:
            days_until_monday = 7
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        next_time += timedelta(days=days_until_monday)
    
    else:
        logger.warning(f"Unrecognized interval: {interval}, defaulting to 4h")
        return get_next_candle_time("4h")
    
    return next_time

async def run_scan(config):
    """Run a single scan configuration"""
    try:
        from run_scanner import run_all_exchanges
        from scanner.main import kline_cache
        kline_cache.clear()
        
        logger.info(f"Running scan for {config['timeframe']} timeframe with strategies: {config['strategies']} on {config['exchanges']}")
        
        result = await run_all_exchanges(
            timeframe=config['timeframe'],
            strategies=config['strategies'],
            exchanges=config['exchanges'],
            users=config['users'],
            send_telegram=config['send_telegram'],
            min_volume_usd=config['min_volume_usd']
        )
        
        signal_count = 0
        for strategy, signals in result.items():
            signal_count += len(signals)
        
        logger.info(f"Scan complete: Found {signal_count} signals for {config['timeframe']} timeframe")
        return signal_count
    
    except Exception as e:
        logger.error(f"Error running scan: {str(e)}")
        return 0

async def run_scheduled_scans():
    """Run all scans at their scheduled times with staggered execution and optimized data fetching"""
    # Group configs by timeframe
    timeframe_configs = {}
    for config in all_scan_configs:
        timeframe = config['timeframe']
        if timeframe not in timeframe_configs:
            timeframe_configs[timeframe] = []
        timeframe_configs[timeframe].append(config)
    
    # Define timeframe processing order priority
    timeframe_priority = {"4h": 0, "1d": 1, "2d": 2, "1w": 3}
    
    while True:
        try:
            # Find the soonest upcoming scan time across all timeframes
            next_times = {tf: get_next_candle_time(tf) for tf in timeframe_configs.keys()}
            
            # Log all upcoming scan times for debugging
            now = datetime.utcnow()
            for tf, next_time in sorted(next_times.items(), key=lambda x: x[1]):
                wait_seconds = (next_time - now).total_seconds()
                logger.info(f"Next {tf} scan scheduled for {next_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (in {wait_seconds/3600:.1f} hours)")
            
            # Find all timeframes that need to be scanned in the next 2 minutes
            current_time = datetime.utcnow()
            upcoming_scans = []
            
            for tf, scan_time in next_times.items():
                time_diff = (scan_time - current_time).total_seconds()
                if time_diff <= 120:  # 2 minutes in seconds
                    upcoming_scans.append((tf, scan_time))
            
            if len(upcoming_scans) > 1:
                logger.info(f"Multiple scans scheduled close together: {[tf for tf, _ in upcoming_scans]}")
                
                # Sort timeframes by priority
                upcoming_timeframes = [tf for tf, _ in upcoming_scans]
                sorted_timeframes = sorted(upcoming_timeframes, 
                                         key=lambda tf: timeframe_priority.get(tf, 99))
                
                logger.info(f"Processing timeframes in priority order: {sorted_timeframes}")
                
                # Process timeframes sequentially with a 1-minute delay between each
                for tf in sorted_timeframes:
                    logger.info(f"Starting scheduled scans for {tf} timeframe")
                    
                    # Clear the cache before starting (unless reusing data)
                    from scanner.main import kline_cache
                    if tf == "2d" or tf == "1w":
                        logger.info(f"Preserving 1d data cache for {tf} timeframe")
                    else:
                        logger.info(f"Clearing cache before processing {tf} timeframe")
                        kline_cache.clear()
                    
                    # Run all configs for this timeframe
                    configs = timeframe_configs[tf]
                    total_signals = 0
                    for config in configs:
                        signals = await run_scan(config)
                        total_signals += signals
                    
                    logger.info(f"Completed all {tf} scans. Total signals found: {total_signals}")
                    
                    # Add a 1-minute delay before the next timeframe
                    if sorted_timeframes.index(tf) < len(sorted_timeframes) - 1:
                        delay = 60  # 1 minute delay
                        logger.info(f"Waiting {delay} seconds before starting the next timeframe scan")
                        await asyncio.sleep(delay)
            else:
                # Regular case - just one scan approaching
                if upcoming_scans:
                    next_tf, next_time = upcoming_scans[0]
                else:
                    next_tf, next_time = min(next_times.items(), key=lambda x: x[1])
                
                # Calculate wait time
                now = datetime.utcnow()
                wait_seconds = (next_time - now).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"Next scan: {next_tf} at {next_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (waiting {wait_seconds/60:.1f} minutes)")
                    await asyncio.sleep(wait_seconds)
                
                # Clear cache before scanning
                from scanner.main import kline_cache
                kline_cache.clear()
                logger.info(f"Cache cleared before processing {next_tf} timeframe")
                
                # Run all configs for this timeframe
                logger.info(f"Starting scheduled scans for {next_tf} timeframe")
                configs = timeframe_configs[next_tf]
                
                total_signals = 0
                for config in configs:
                    signals = await run_scan(config)
                    total_signals += signals
                
                logger.info(f"Completed all {next_tf} scans. Total signals found: {total_signals}")
            
            # Small delay before checking next schedules
            await asyncio.sleep(30)
        
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            logger.info("Waiting 5 minutes before retrying...")
            await asyncio.sleep(300)

def main():
    """Main entry point of the scanner service"""
    logger.info("Market Scanner Service starting up")
    logger.info(f"Project root directory: {project_root}")
    
    # Set up signal handlers for SIGTERM and SIGINT
    loop = asyncio.get_event_loop()
    
    def handle_shutdown():
        logger.info("Received shutdown signal. Stopping scanner...")
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Scanner stopped gracefully")
        sys.exit(0)
    
    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown)
    
    try:
        loop.run_until_complete(run_scheduled_scans())
    except asyncio.CancelledError:
        logger.info("Scanner tasks cancelled during shutdown")
        handle_shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.info("Restarting service in 5 minutes...")
        time_module.sleep(300)
        main()

if __name__ == "__main__":
    main()