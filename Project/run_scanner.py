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

async def run(exchange, timeframe, strategies, users=["default"], send_telegram=True):
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
    results = await run_scanner(exchange, timeframe, strategies, telegram_config)
    
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

async def run_all_exchanges(timeframe, strategies, exchanges=None, users=["default"], send_telegram=True):
    # Ensure users is a list
    users = users if isinstance(users, (list, tuple)) else ["default"]
    
    default_exchanges = [
        "mexc_futures", "gateio_futures", "binance_futures", "bybit_futures",
        "binance_spot", "bybit_spot", "gateio_spot", "kucoin_spot", "mexc_spot"
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
            results = await run_scanner(exchange, timeframe, strategies, telegram_config)
            for strategy, res in results.items():
                if strategy not in all_results:
                    all_results[strategy] = []
                all_results[strategy].extend([{**r, 'exchange': exchange} for r in res])
        except Exception as e:
            logging.error(f"Error scanning {exchange}: {str(e)}")

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