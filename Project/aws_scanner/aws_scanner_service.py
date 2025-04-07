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
        "strategies": ["reversal_bar", "volume_surge"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1d",
        "strategies": ["reversal_bar", "volume_surge"],
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
        "strategies": ["breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1d",
        "strategies": ["breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "2d",
        "strategies": ["start_bar", "breakout_bar", "volume_surge"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None
    },
    {
        "timeframe": "1w",
        "strategies": ["start_bar", "breakout_bar", "volume_surge"],
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
    """
    Run all scans based on a pre-computed schedule with optimized wait times
    """
    # Group configs by timeframe
    timeframe_configs = {}
    for config in all_scan_configs:
        timeframe = config['timeframe']
        if timeframe not in timeframe_configs:
            timeframe_configs[timeframe] = []
        timeframe_configs[timeframe].append(config)
    
    # Track last execution time for each timeframe
    last_execution = {tf: None for tf in timeframe_configs.keys()}
    
    # Initialize the scan schedule
    scan_schedule = []
    
    while True:
        try:
            now = datetime.utcnow()
            logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # If schedule is empty or we need to refresh it, compute the next 24 hours of scans
            if not scan_schedule:
                logger.info("Computing scan schedule for the next 24 hours")
                scan_schedule = compute_scan_schedule(24)  # Next 24 hours
                logger.info(f"Scheduled scans: {len(scan_schedule)}")
                for scheduled_time, timeframes in scan_schedule:
                    logger.info(f"  {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} UTC: {', '.join(timeframes)}")
            
            # Check if there are scans to run now
            if scan_schedule and now >= scan_schedule[0][0]:
                scheduled_time, timeframes_to_run = scan_schedule.pop(0)
                logger.info(f"Running scheduled scan for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                # Run each timeframe in order
                for tf in timeframes_to_run:
                    if tf == "2d":
                        # Check if today is a 2d start day
                        reference_date = pd.Timestamp('2025-03-20').normalize()
                        today = pd.Timestamp(now.date())
                        days_diff = (today - reference_date).days
                        is_2d_start_day = days_diff % 2 == 0
                        
                        if not is_2d_start_day:
                            logger.info(f"Skipping 2d scan as today is not a 2d start day")
                            continue
                    
                    if tf == "1w":
                        # Check if today is Monday
                        is_monday = now.weekday() == 0
                        
                        if not is_monday:
                            logger.info(f"Skipping 1w scan as today is not Monday")
                            continue
                    
                    logger.info(f"Starting {tf} timeframe scan")
                    
                    # Clear cache before each scan
                    from scanner.main import kline_cache
                    kline_cache.clear()
                    logger.info(f"Cache cleared before processing {tf} timeframe")
                    
                    # Run all configs for this timeframe
                    configs = timeframe_configs[tf]
                    total_signals = 0
                    
                    try:
                        for config in configs:
                            signals = await run_scan(config)
                            total_signals += signals
                        
                        # Update last execution time
                        last_execution[tf] = datetime.utcnow()
                        logger.info(f"Completed {tf} scan. Total signals found: {total_signals}")
                    except Exception as e:
                        logger.error(f"Error executing {tf} scan: {str(e)}")
                    
                    # Small delay between timeframes
                    await asyncio.sleep(10)
                
                # After running all timeframes for this scheduled time, check if we need to refresh the schedule
                if not scan_schedule:
                    continue  # Will refresh the schedule at the top of the loop
            
            # No immediate scans to run, calculate optimized wait time
            time_to_next_scan = (scan_schedule[0][0] - now).total_seconds()
            
            # Use longer sleep times for far-future scans to optimize resource usage
            # Wake up at least 15 seconds before the scheduled time
            if time_to_next_scan > 4 * 3600:  # More than 4 hours away
                # Sleep for up to 2 hours as requested
                max_sleep = 2 * 3600  # 2 hours
            elif time_to_next_scan > 1 * 3600:  # More than 1 hour away
                max_sleep = 1800  # 30 minutes
            else:
                # For imminent scans (less than 1 hour away), check more frequently
                max_sleep = 300  # 5 minutes
            
            # Calculate final wait time: min(time to next scan - 15 seconds, max allowed sleep)
            wait_time = max(10, min(time_to_next_scan - 15, max_sleep))
            
            logger.info(f"Next scan at {scan_schedule[0][0].strftime('%Y-%m-%d %H:%M:%S')} UTC (waiting {wait_time/60:.1f} minutes)")
            await asyncio.sleep(wait_time)
        
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            logger.info("Waiting 2 minutes before retrying...")
            await asyncio.sleep(120)


def compute_scan_schedule(hours_ahead):
    """
    Compute a schedule of scans for the next X hours
    
    Args:
        hours_ahead (int): How many hours to schedule ahead
        
    Returns:
        list: List of (datetime, [timeframes]) tuples in chronological order
    """
    now = datetime.utcnow()
    end_time = now + timedelta(hours=hours_ahead)
    
    # Define 4h boundaries
    hours_4h = [0, 4, 8, 12, 16, 20]
    
    # Create the schedule
    schedule = []
    
    # Schedule all 4h boundaries
    current = now.replace(minute=0, second=0, microsecond=0)
    while current <= end_time:
        # For each day
        for hour in hours_4h:
            scan_time = current.replace(hour=hour, minute=1)
            
            # Skip times in the past
            if scan_time < now:
                continue
                
            # At 00:01, we run 4h->1d->2d->1w in sequence
            if hour == 0:
                schedule.append((scan_time, ["4h", "1d", "2d", "1w"]))
            else:
                # At other 4h boundaries, we only run 4h
                schedule.append((scan_time, ["4h"]))
        
        # Move to next day
        current += timedelta(days=1)
    
    # Sort the schedule by time (should already be in order, but just to be safe)
    schedule.sort(key=lambda x: x[0])
    
    return schedule

def main():
    """Main entry point of the scanner service"""
    logger.info("Market Scanner Service starting up")
    logger.info(f"Project root directory: {project_root}")
    
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