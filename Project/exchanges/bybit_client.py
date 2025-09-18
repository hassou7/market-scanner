# exchanges/bybit_client.py

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
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.bybit.com"
        self.batch_size = 20
        self.request_delay = 0.5  # Add a small delay between requests to avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Bybit API specific intervals"""
        return {
            '1w': 'W',     # Weekly - Bybit native support
            '4d': 'D',     # 4-day - fetch daily and aggregate
            '3d': 'D',     # 3-day - fetch daily and aggregate
            '2d': 'D',     # 2-day - fetch daily and aggregate
            '1d': 'D',     # Daily - Bybit native support
            '4h': '240'    # 4-hour (in minutes) - Bybit native support
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,      # 60 weekly candles (direct from API)
            '4d': 240,     # 220 daily → aggregate to ~55 4d candles  
            '3d': 180,     # 170 daily → aggregate to ~56 3d candles
            '2d': 120,     # 110 daily → aggregate to 55 2d candles
            '1d': 60,      # 60 daily candles (direct from API)
            '4h': 60       # 60 4h candles (direct from API)
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
        
        # For 2d, 3d, 4d timeframes, we need to fetch daily data and then aggregate
        if self.timeframe in ["2d", "3d", "4d"]:
            api_interval = "D"
        
        # Calculate interval in milliseconds for start time calculation
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
                    
                    # Bybit returns: [timestamp, open, high, low, close, volume, turnover]
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                    df = pd.DataFrame(klines, columns=columns)
                    
                    # Convert types
                    df = df.astype({
                        'timestamp': 'int64',
                        'open': 'float',
                        'high': 'float',
                        'low': 'float',
                        'close': 'float',
                        'volume': 'float',
                        'turnover': 'float'
                    })
                    
                    # Bybit timestamp is in milliseconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Keep only OHLCV columns
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Process according to timeframe
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    elif self.timeframe == "3d":
                        df = self.aggregate_to_3d(df)
                    elif self.timeframe == "4d":
                        df = self.aggregate_to_4d(df)
                    # For 1w and 1d, Bybit provides native data
                    # For 4h, Bybit provides native data
                    
                    return df
                else:
                    # Handle Bybit error responses
                    if data.get('retCode') == 10001:  # Invalid parameter
                        logging.warning(f"Invalid parameter for {symbol} on Bybit spot")
                    elif data.get('retCode') == 10004:  # Invalid signature/auth
                        logging.warning(f"Authentication issue for {symbol} on Bybit spot")
                    else:
                        logging.error(f"Bybit spot API error for {symbol}: {data}")
                    return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from Bybit spot")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from Bybit spot: {str(e)}")
            return None