import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime
from .base_client import BaseExchangeClient

class BybitClient(BaseExchangeClient):
    """
    Bybit exchange API client for fetching market data
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.bybit.com"
        self.batch_size = 20
        self.request_delay = 0.1  # Add a small delay between requests to avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Bybit API specific intervals"""
        return {
            '1w': 'W',     # Weekly
            '2d': 'D',     # For 2d, we'll fetch daily and aggregate
            '1d': 'D',     # Daily
            '4h': '240'    # 4-hour (in minutes)
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 60,      # Weekly needs at least 40+ bars for macro lookback
            '2d': 120,     # 2d needs 120 daily bars to build enough 2d candles
            '1d': 60,      # Daily needs at least 60 days for history
            '4h': 200      # 4h needs more bars
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT spot trading pairs from Bybit"""
        url = f"{self.base_url}/v5/market/tickers"
        params = {
            'category': 'spot'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                    symbols = [item['symbol'] for item in data['result']['list'] 
                              if item['symbol'].endswith(self.quote_currency)]
                    return sorted(symbols)
                else:
                    logging.error(f"Error fetching Bybit spot symbols: {data}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching Bybit spot symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from Bybit spot market"""
        url = f"{self.base_url}/v5/market/kline"
        
        # Calculate start time based on timeframe and fetch limit
        end_time = int(time.time() * 1000)
        
        # Get the appropriate interval based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d timeframe, we need to fetch daily data and then aggregate
        if self.timeframe == "2d":
            api_interval = "D"
        
        interval_seconds = {
            'W': 7 * 24 * 60 * 60 * 1000,  # 1 week in milliseconds
            'D': 24 * 60 * 60 * 1000,      # 1 day in milliseconds
            '240': 4 * 60 * 60 * 1000      # 4 hours in milliseconds
        }[api_interval]
        
        # Calculate start time
        start_time = end_time - (self.fetch_limit * interval_seconds)
        
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': api_interval,
            'start': start_time,
            'end': end_time,
            'limit': self.fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                    # Bybit returns data in reverse order (newest first)
                    klines = data['result']['list']
                    klines.reverse()  # Convert to oldest first
                    
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                    df = pd.DataFrame(klines, columns=columns)
                    
                    df = df.astype({
                        'timestamp': 'int64',
                        'open': 'float',
                        'high': 'float',
                        'low': 'float',
                        'close': 'float',
                        'volume': 'float',
                        'turnover': 'float'
                    })
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Only need to aggregate for 2d timeframe
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    
                    return df
                else:
                    logging.error(f"Error fetching klines for {symbol}: {data}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol}: {str(e)}")
            return None