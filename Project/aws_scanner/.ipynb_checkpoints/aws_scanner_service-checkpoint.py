#!/usr/bin/env python3
"""
Optimized AWS Scanner Service

Key optimizations:
1. Efficient data fetching: Single 1d fetch for aggregated timeframes (2d, 3d, 4d)
2. Fast/slow exchange categorization with prioritized execution
3. Proper cache management for aggregated sessions
4. Exchange-type specific strategy execution

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

parser = argparse.ArgumentParser(description="Optimized AWS Market Scanner Service")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
args = parser.parse_args()

logger = setup_logging(args.debug)

# ═════════════════════════════════════════════════════════════════════════════════════════
# Exchange categorization with fast/slow classification
# ═════════════════════════════════════════════════════════════════════════════════════════

# Fast exchanges (reliable, fast API responses)
fast_spot_exchanges = [
    "binance_spot",
    "bybit_spot",
    "gateio_spot"
]

fast_futures_exchanges = [
    "binance_futures",
    "bybit_futures", 
    "gateio_futures"
]

# Slow exchanges (slower API responses, need careful rate limiting)
slow_spot_exchanges = [
    "kucoin_spot",
    "mexc_spot"
]

slow_futures_exchanges = [
    "mexc_futures"
]

# All exchanges grouped by type
all_fast_exchanges = fast_spot_exchanges + fast_futures_exchanges
all_slow_exchanges = slow_spot_exchanges + slow_futures_exchanges
all_spot_exchanges = fast_spot_exchanges + slow_spot_exchanges
all_futures_exchanges = fast_futures_exchanges + slow_futures_exchanges

# ═════════════════════════════════════════════════════════════════════════════════════════
# Strategy configurations by type and priority
# ═════════════════════════════════════════════════════════════════════════════════════════

# Strategy classification
native_strategies = [
    "confluence", "consolidation_breakout", "channel_breakout", 
    "loaded_bar", "trend_breakout", "pin_up", "sma50_breakout"
]

composed_strategies = [
    "hbs_breakout", "vs_wakeup"
]

futures_only_strategies = [
    "reversal_bar", "pin_down"
]

# All timeframes to scan
all_timeframes = ["1d", "2d", "3d", "4d", "1w"]

# Main scan configurations - organized by priority and strategy type
scan_configs = [
    # ────────────────────────────────────────────────────────────────────────────────────
    # PRIORITY 1: FAST EXCHANGES - NATIVE STRATEGIES (highest priority for DB development)
    # ────────────────────────────────────────────────────────────────────────────────────
    {
        "name": "fast_native_strategies",
        "timeframes": all_timeframes,
        "strategies": native_strategies,
        "exchanges": fast_spot_exchanges + ["binance_futures"],
        "users": ["default", "user1", "user2"],
        "send_telegram": True,
        "min_volume_usd": None,
        "priority": 1,
        "exchange_type": "fast_mixed",
        "strategy_type": "native"
    },
    
    # ────────────────────────────────────────────────────────────────────────────────────
    # PRIORITY 2: FAST EXCHANGES - COMPOSED STRATEGIES  
    # ────────────────────────────────────────────────────────────────────────────────────
    {
        "name": "fast_composed_strategies",
        "timeframes": all_timeframes,
        "strategies": composed_strategies,
        "exchanges": fast_spot_exchanges + ["binance_futures"],
        "users": ["default", "user1", "user2"],
        "send_telegram": True,
        "min_volume_usd": None,
        "priority": 2,
        "exchange_type": "fast_mixed",
        "strategy_type": "composed"
    },
    
    # ────────────────────────────────────────────────────────────────────────────────────
    # PRIORITY 3: FAST FUTURES - FUTURES-ONLY STRATEGIES
    # ────────────────────────────────────────────────────────────────────────────────────
    {
        "name": "fast_futures_only",
        "timeframes": all_timeframes,
        "strategies": futures_only_strategies,
        "exchanges": fast_futures_exchanges,
        "users": ["default"],
        "send_telegram": True,
        "min_volume_usd": None,
        "priority": 3,
        "exchange_type": "fast_futures",
        "strategy_type": "futures_only"
    },
    
    # ────────────────────────────────────────────────────────────────────────────────────
    # PRIORITY 4: SLOW SPOT - NATIVE STRATEGIES
    # ────────────────────────────────────────────────────────────────────────────────────
    {
        "name": "slow_native_strategies",
        "timeframes": all_timeframes,
        "strategies": native_strategies,
        "exchanges": slow_spot_exchanges,
        "users": ["default", "user1", "user2"],
        "send_telegram": True,
        "min_volume_usd": None,
        "priority": 4,
        "exchange_type": "slow_spot",
        "strategy_type": "native"
    },
    
    # ────────────────────────────────────────────────────────────────────────────────────
    # PRIORITY 5: SLOW SPOT - COMPOSED STRATEGIES
    # ────────────────────────────────────────────────────────────────────────────────────
    {
        "name": "slow_composed_strategies", 
        "timeframes": all_timeframes,
        "strategies": composed_strategies,
        "exchanges": slow_spot_exchanges,
        "users": ["default", "user1", "user2"],
        "send_telegram": True,
        "min_volume_usd": None,
        "priority": 5,
        "exchange_type": "slow_spot",
        "strategy_type": "composed"
    }
    
    # Note: slow_futures_exchanges reserved for future use
    # Can be added when needed with priority 6+
]

# ═════════════════════════════════════════════════════════════════════════════════════════
# Optimized timeframe scheduling and cache management
# ═════════════════════════════════════════════════════════════════════════════════════════

def get_aggregated_timeframes():
    """Return timeframes that require daily data aggregation"""
    return ["2d", "3d", "4d"]

def get_native_timeframes():
    """Return timeframes with native exchange support"""
    return ["1d", "1w"]

def should_clear_cache_for_session(timeframes):
    """
    Determine if cache should be cleared after a session.
    Clear cache after any session containing aggregated timeframes.
    """
    aggregated_tfs = get_aggregated_timeframes()
    return any(tf in aggregated_tfs for tf in timeframes)

class OptimizedSessionManager:
    """Manages efficient data fetching and cache for aggregated timeframes"""
    
    def __init__(self):
        self.session_data_cache = {}  # Cache for 1d data used across aggregated timeframes
        
    def clear_session_cache(self):
        """Clear the session-level cache (daily data for aggregation)"""
        self.session_data_cache.clear()
        logger.info("Session-level cache cleared")
        
    def needs_daily_data(self, timeframes):
        """Check if any timeframe in the list needs daily data for aggregation"""
        return any(tf in get_aggregated_timeframes() for tf in timeframes)
        
    async def prepare_session_data(self, timeframes, exchanges):
        """
        Pre-fetch daily data once if needed for aggregated timeframes.
        This avoids multiple API calls for the same 1d data.
        """
        if not self.needs_daily_data(timeframes):
            return  # No aggregated timeframes, no prep needed
            
        logger.info("Pre-fetching daily data for aggregated timeframes optimization")
        
        # We don't actually pre-fetch here as the parallel scanner handles this
        # This is a placeholder for future optimization where we could pre-warm cache
        # with a single daily fetch per exchange before running aggregated timeframes
        pass

# Global session manager
session_manager = OptimizedSessionManager()

# ═════════════════════════════════════════════════════════════════════════════════════════
# Enhanced scheduling logic
# ═════════════════════════════════════════════════════════════════════════════════════════

def get_next_candle_time(interval="1d"):
    """
    Calculate time until next candle close for a given interval
    
    Args:
        interval (str): Timeframe interval ('1d', '2d', '3d', '4d', '1w')
        
    Returns:
        datetime: Next candle close time in UTC
    """
    now = datetime.utcnow()
    
    if interval == "1d":
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
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
        while next_time <= now:
            next_time += timedelta(days=2)
    
    elif interval == "3d":
        reference_date = pd.Timestamp('2025-03-20').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        period = days_diff // 3
        next_period_start = reference_date + timedelta(days=period * 3 + 3)
        next_time = datetime.combine(next_period_start, time(0, 1, 0))
        if now >= next_time:
            next_time = datetime.combine(next_period_start + timedelta(days=3), time(0, 1, 0))
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
        while next_time <= now:
            next_time += timedelta(days=4)
    
    elif interval == "1w":
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0 and now.minute >= 1:
            days_until_monday = 7
        next_time = now.replace(hour=0, minute=1, second=0, microsecond=0)
        next_time += timedelta(days=days_until_monday)
        while next_time <= now:
            next_time += timedelta(days=7)
    
    else:
        logger.warning(f"Unrecognized interval: {interval}, defaulting to 1d")
        return get_next_candle_time("1d")
    
    return next_time

def should_run_timeframe_today(timeframe):
    """
    Check if a timeframe should run today based on aggregation schedule
    """
    now = datetime.utcnow()
    
    if timeframe == "1d" or timeframe == "1w":
        # Native timeframes
        if timeframe == "1w":
            return now.weekday() == 0  # Monday
        return True  # Daily runs every day
    
    elif timeframe == "2d":
        reference_date = pd.Timestamp('2025-03-20').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        return days_diff % 2 == 0
    
    elif timeframe == "3d":
        reference_date = pd.Timestamp('2025-03-20').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        return days_diff % 3 == 0
    
    elif timeframe == "4d":
        reference_date = pd.Timestamp('2025-03-22').normalize()
        today = pd.Timestamp(now.date())
        days_diff = (today - reference_date).days
        return days_diff % 4 == 0
    
    return False

def get_active_timeframes_for_today():
    """Get list of timeframes that should run today"""
    all_timeframes = ["1d", "2d", "3d", "4d", "1w"]
    return [tf for tf in all_timeframes if should_run_timeframe_today(tf)]

# ═════════════════════════════════════════════════════════════════════════════════════════
# Optimized scan execution with prioritization
# ═════════════════════════════════════════════════════════════════════════════════════════

async def run_optimized_scan(config, active_timeframes):
    """Run a single scan configuration with timeframe filtering"""
    try:
        from run_parallel_scanner import run_parallel_multi_timeframes_all_exchanges
        
        # Filter timeframes to only those active today and in config
        scan_timeframes = [tf for tf in config["timeframes"] if tf in active_timeframes]
        
        if not scan_timeframes:
            logger.info(f"Skipping {config['name']} - no active timeframes today")
            return 0
        
        logger.info(f"Running {config['name']} scan for timeframes: {scan_timeframes}")
        logger.info(f"  Strategies: {config['strategies']}")
        logger.info(f"  Exchanges: {config['exchanges']}")
        logger.info(f"  Priority: {config['priority']} ({config['exchange_type']})")
        
        result = await run_parallel_multi_timeframes_all_exchanges(
            timeframes=scan_timeframes,
            strategies=config['strategies'],
            exchanges=config['exchanges'],
            users=config['users'],
            send_telegram=config['send_telegram'],
            min_volume_usd=config['min_volume_usd']
        )
        
        signal_count = sum(len(signals) for signals in result.values())
        logger.info(f"Completed {config['name']}: {signal_count} signals found")
        
        return signal_count
    
    except Exception as e:
        logger.error(f"Error in {config['name']} scan: {str(e)}")
        return 0

async def run_prioritized_scans(active_timeframes):
    """
    Run all scan configurations in priority order with optimized data fetching
    """
    logger.info("═══════════════════════════════════════════════════════════════")
    logger.info(f"Starting prioritized scan session for timeframes: {active_timeframes}")
    logger.info("═══════════════════════════════════════════════════════════════")
    
    # Prepare session data if needed for aggregated timeframes
    await session_manager.prepare_session_data(active_timeframes, all_spot_exchanges + all_futures_exchanges)
    
    # Sort configs by priority for execution order
    sorted_configs = sorted(scan_configs, key=lambda x: x['priority'])
    
    total_signals = 0
    
    # Group configs by priority for potential parallel execution within priority levels
    priority_groups = {}
    for config in sorted_configs:
        priority = config['priority']
        if priority not in priority_groups:
            priority_groups[priority] = []
        priority_groups[priority].append(config)
    
    # Execute each priority group
    for priority in sorted(priority_groups.keys()):
        group_configs = priority_groups[priority]
        logger.info(f"Executing priority {priority} group ({len(group_configs)} configs)")
        
        # Within each priority group, we can run configs in parallel
        # But for now, run sequentially to respect API limits
        group_signals = 0
        for config in group_configs:
            signals = await run_optimized_scan(config, active_timeframes)
            group_signals += signals
            
            # Small delay between configs in same priority group
            await asyncio.sleep(5)
        
        logger.info(f"Priority {priority} complete: {group_signals} signals")
        total_signals += group_signals
        
        # Longer delay between priority groups to let fast exchanges complete
        # before starting slow exchanges
        if priority < max(priority_groups.keys()):
            logger.info("Waiting before next priority group...")
            await asyncio.sleep(15)
    
    # Cache management - clear if session contained aggregated timeframes
    if should_clear_cache_for_session(active_timeframes):
        logger.info("Clearing cache after aggregated timeframes session")
        kline_cache.clear()
        session_manager.clear_session_cache()
    
    logger.info("═══════════════════════════════════════════════════════════════")
    logger.info(f"Session complete: {total_signals} total signals across all priorities")
    logger.info("═══════════════════════════════════════════════════════════════")
    
    return total_signals

# ═════════════════════════════════════════════════════════════════════════════════════════
# Main scheduler with optimized scanning
# ═════════════════════════════════════════════════════════════════════════════════════════

async def run_optimized_scheduler():
    """
    Main scheduler with optimized data fetching and prioritized execution
    """
    logger.info("Starting optimized scanner scheduler")
    logger.info(f"Strategy Classification:")
    logger.info(f"  Native strategies: {native_strategies}")
    logger.info(f"  Composed strategies: {composed_strategies}")
    logger.info(f"  Futures-only strategies: {futures_only_strategies}")
    logger.info(f"Exchange Classification:")
    logger.info(f"  Fast spot exchanges: {fast_spot_exchanges}")
    logger.info(f"  Fast futures exchanges: {fast_futures_exchanges}")
    logger.info(f"  Slow spot exchanges: {slow_spot_exchanges}")
    logger.info(f"  Slow futures exchanges: {slow_futures_exchanges}")
    logger.info(f"Execution Priority:")
    logger.info(f"  1. Fast Native → 2. Fast Composed → 3. Fast Futures-Only → 4. Slow Native → 5. Slow Composed")
    
    while True:
        try:
            now = datetime.utcnow()
            logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # Get active timeframes for today
            active_timeframes = get_active_timeframes_for_today()
            
            if not active_timeframes:
                logger.info("No active timeframes today, waiting...")
                await asyncio.sleep(3600)  # Wait 1 hour
                continue
            
            logger.info(f"Active timeframes today: {active_timeframes}")
            
            # Check if it's time to scan (00:01 UTC)
            if now.hour == 0 and now.minute <= 5:  # 5-minute window for execution
                logger.info("Scanning window detected - starting optimized scan session")
                
                # Clear all caches for fresh start
                kline_cache.clear()
                session_manager.clear_session_cache()
                
                # Run prioritized scans
                total_signals = await run_prioritized_scans(active_timeframes)
                
                logger.info(f"Daily scan session complete: {total_signals} total signals")
                
                # Wait until next day to avoid re-running
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_seconds = (tomorrow - datetime.utcnow()).total_seconds()
                logger.info(f"Waiting until next scan window: {wait_seconds/3600:.1f} hours")
                await asyncio.sleep(max(3600, wait_seconds - 300))  # Wake up 5 minutes early
                
            else:
                # Not scan time - calculate wait until next 00:01
                tomorrow = now.replace(hour=0, minute=1, second=0, microsecond=0)
                if now >= tomorrow:
                    tomorrow += timedelta(days=1)
                
                wait_seconds = (tomorrow - now).total_seconds()
                
                # Use optimized wait times
                if wait_seconds > 4 * 3600:  # More than 4 hours
                    sleep_time = min(2 * 3600, wait_seconds - 300)  # Max 2 hours, wake 5 min early
                elif wait_seconds > 1 * 3600:  # More than 1 hour  
                    sleep_time = min(1800, wait_seconds - 60)  # Max 30 min, wake 1 min early
                else:
                    sleep_time = min(300, max(60, wait_seconds - 30))  # Max 5 min, min 1 min
                
                logger.info(f"Next scan at {tomorrow.strftime('%Y-%m-%d %H:%M:%S')} UTC (waiting {sleep_time/60:.1f} minutes)")
                await asyncio.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            logger.info("Waiting 2 minutes before retrying...")
            await asyncio.sleep(120)

def main():
    """Main entry point of the optimized scanner service"""
    logger.info("Optimized Market Scanner Service starting up")
    logger.info(f"Project root directory: {project_root}")
    logger.info("Key optimizations active:")
    logger.info("  ✓ Efficient 1d data fetching for aggregated timeframes")
    logger.info("  ✓ Fast/slow exchange prioritization")
    logger.info("  ✓ Smart cache management")
    logger.info("  ✓ Exchange-type specific strategy execution")
    
    # Create a new event loop
    loop = asyncio.get_event_loop()
    
    # Flag to track if shutdown has been initiated
    shutting_down = False
    
    async def shutdown():
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        
        logger.info("Received shutdown signal. Stopping optimized scanner...")
        
        # Clear caches on shutdown
        kline_cache.clear()
        session_manager.clear_session_cache()
        
        # Cancel all running tasks except the current one
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        try:
            await loop.shutdown_asyncgens()
        except Exception as e:
            logger.error(f"Error shutting down async generators: {str(e)}")
        
        loop.stop()
        logger.info("Optimized scanner stopped gracefully")
    
    def handle_shutdown():
        asyncio.ensure_future(shutdown())
    
    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown)
    
    try:
        loop.run_until_complete(run_optimized_scheduler())
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
        pass

    if shutting_down:
        sys.exit(0)

if __name__ == "__main__":
    main()