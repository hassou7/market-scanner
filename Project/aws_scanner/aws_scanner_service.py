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
from datetime import datetime, timedelta, time
import time as time_module
import pandas as pd
from scanner.main import kline_cache
kline_cache.clear()  # Clear cache for fresh data

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level to project root
sys.path.insert(0, project_root)

# Configure logging
def setup_logging(debug_mode=False):
    level = logging.DEBUG if debug_mode else logging.INFO
    
    # Create logs directory if it doesn't exist
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
    
    # Set higher log level for telegram libraries to reduce verbosity
    logging.getLogger('telegram').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    return logging.getLogger("ScannerService")

# Parse command line arguments
parser = argparse.ArgumentParser(description="AWS Market Scanner Service")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
args = parser.parse_args()

# Set up logging
logger = setup_logging(args.debug)

# List of spot exchanges to scan
spot_exchanges = [
    "binance_spot",
    "bybit_spot", 
    "gateio_spot",
    "kucoin_spot",
    "mexc_spot"
]

# List of futures exchanges to scan
futures_exchanges = [
    "binance_futures",
    "bybit_futures",
    "gateio_futures",
    "mexc_futures"
]

# Futures exchanges scan configurations
futures_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "1d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "2d",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "1w",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    }
]

# Spot exchanges scan configurations
spot_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "1d",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "2d",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    },
    {
        "timeframe": "1w",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None  # Use value from config
    }
]

# Combine all configurations
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
        # 4h candles close at 0, 4, 8, 12, 16, 20 UTC
        current_hour = now.hour
        next_4h = ((current_hour // 4) + 1) * 4
        if next_4h >= 24:
            next_4h = 0
            # Add a day if we roll over to the next day
            next_time = now.replace(hour=next_4h, minute=1, second=0, microsecond=0)
            if next_4h <= current_hour:
                next_time += timedelta(days=1)
        else:
            next_time = now.replace(hour=next_4h, minute=1, second=0, microsecond=0)
    
    elif interval == "1d":
        # Daily candles close at 0:00 UTC
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        if now.hour >= 0 and now.minute >= 1:  # If already past 00:01
            next_time += timedelta(days=1)
    
    elif interval == "2d":
        # 2-day candles follow a specific reference pattern
        # Thursday March 20, 2025 was the start of a 2d candle
        reference_date = pd.Timestamp('2025-03-20').normalize()
        today = pd.Timestamp(now.date())
        
        # Calculate days since reference date
        days_diff = (today - reference_date).days
        
        # Determine which 2-day period we're in
        period = days_diff // 2
        
        # Calculate the start of the next period
        next_period_start = reference_date + timedelta(days=period * 2 + 2)
        
        # Set the time to 00:01 UTC
        next_time = datetime.combine(next_period_start, time(0, 1, 0))
        
        # If we're already past this time, the calculation is correct
        # If not, the calculation gave us the start of the current period
        if now >= next_time:
            next_time = datetime.combine(next_period_start + timedelta(days=2), time(0, 1, 0))
    
    elif interval == "1w":
        # Weekly candles start on Monday and close on Sunday night/Monday morning at 00:00 UTC
        # Calculate days until next Monday
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0 and now.minute >= 1:
            days_until_monday = 7  # If it's Monday after 00:01, wait until next Monday
            
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        next_time += timedelta(days=days_until_monday)
    
    else:
        # Default to 4h if interval not recognized
        logger.warning(f"Unrecognized interval: {interval}, defaulting to 4h")
        return get_next_candle_time("4h")
    
    return next_time

async def run_scan(config):
    """Run a single scan configuration"""
    try:
        # Import the run_all_exchanges function
        from run_scanner import run_all_exchanges
        
        # Clear the kline cache before each scan
        from scanner.main import kline_cache
        kline_cache.clear()
        
        logger.info(f"Running scan for {config['timeframe']} timeframe with strategies: {config['strategies']} on {config['exchanges']}")
        
        # Run the scan using the existing function, passing the min_volume_usd parameter
        result = await run_all_exchanges(
            timeframe=config['timeframe'],
            strategies=config['strategies'],
            exchanges=config['exchanges'],
            users=config['users'],
            send_telegram=config['send_telegram'],
            min_volume_usd=config['min_volume_usd']  # Pass None to use config values
        )
        
        # Count total signals found
        signal_count = 0
        for exchange_result in result.values():
            for strategy_result in exchange_result.values():
                signal_count += len(strategy_result)
        
        logger.info(f"Scan complete: Found {signal_count} signals for {config['timeframe']} timeframe")
        return signal_count
    
    except Exception as e:
        logger.error(f"Error running scan: {str(e)}")
        return 0

async def run_scheduled_scans():
    """Run all scans at their scheduled times with staggered execution"""
    # Group configs by timeframe
    timeframe_configs = {}
    for config in all_scan_configs:
        timeframe = config['timeframe']
        if timeframe not in timeframe_configs:
            timeframe_configs[timeframe] = []
        timeframe_configs[timeframe].append(config)
    
    while True:
        try:
            # Find the soonest upcoming scan time across all timeframes
            next_times = {tf: get_next_candle_time(tf) for tf in timeframe_configs.keys()}
            
            # Log all upcoming scan times for debugging
            now = datetime.utcnow()
            for tf, next_time in sorted(next_times.items(), key=lambda x: x[1]):
                wait_seconds = (next_time - now).total_seconds()
                logger.debug(f"Next {tf} scan scheduled for {next_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (in {wait_seconds/3600:.1f} hours)")
            
            # Find all timeframes that need to be scanned in the next 2 minutes
            # This helps identify overlapping scans (like Monday 00:00 with 4h, 1d, 1w)
            current_time = datetime.utcnow()
            upcoming_scans = []
            
            for tf, scan_time in next_times.items():
                time_diff = (scan_time - current_time).total_seconds()
                # If scan is due in the next 2 minutes, add to upcoming scans
                if time_diff <= 120:  # 2 minutes in seconds
                    upcoming_scans.append((tf, scan_time))
            
            # If we have multiple scans approaching, stagger them
            if len(upcoming_scans) > 1:
                logger.info(f"Multiple scans scheduled close together: {[tf for tf, _ in upcoming_scans]}")
                # Sort by priority: 1d, 4h, 1w, 2d (most important to least)
                priority_order = {"1d": 0, "4h": 1, "1w": 2, "2d": 3}
                upcoming_scans.sort(key=lambda x: priority_order.get(x[0], 99))
                
                # Process each scan with a delay between them
                for i, (tf, scan_time) in enumerate(upcoming_scans):
                    # Wait until the scan time
                    now = datetime.utcnow()
                    wait_seconds = (scan_time - now).total_seconds()
                    if wait_seconds > 0:
                        logger.info(f"Waiting {wait_seconds/60:.1f} minutes for {tf} scan at {scan_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                        await asyncio.sleep(wait_seconds)
                    
                    # Run all configs for this timeframe
                    logger.info(f"Starting scheduled scans for {tf} timeframe")
                    configs = timeframe_configs[tf]
                    
                    total_signals = 0
                    for config in configs:
                        signals = await run_scan(config)
                        total_signals += signals
                    
                    logger.info(f"Completed all {tf} scans. Total signals found: {total_signals}")
                    
                    # Add a delay before the next timeframe to avoid API rate limits
                    # Only add delay if there are more scans to process
                    if i < len(upcoming_scans) - 1:
                        delay = 60  # 1 minute delay between timeframes
                        logger.info(f"Adding {delay} second delay before next timeframe to avoid API rate limits")
                        await asyncio.sleep(delay)
            else:
                # Regular case - just one scan approaching
                if upcoming_scans:
                    next_tf, next_time = upcoming_scans[0]
                else:
                    # Get the next timeframe to scan and its time
                    next_tf, next_time = min(next_times.items(), key=lambda x: x[1])
                
                # Calculate wait time
                now = datetime.utcnow()
                wait_seconds = (next_time - now).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"Next scan: {next_tf} at {next_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (waiting {wait_seconds/60:.1f} minutes)")
                    await asyncio.sleep(wait_seconds)
                
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
    
    try:
        # Run the continuous scanner
        asyncio.run(run_scheduled_scans())
    except KeyboardInterrupt:
        logger.info("Scanner stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.info("Restarting service in 5 minutes...")
        time_module.sleep(300)
        main()  # Restart the service

if __name__ == "__main__":
    main()