# exchanges/kucoin_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from .base_client import BaseExchangeClient

class KucoinClient(BaseExchangeClient):
    """
    KuCoin exchange API client for fetching market data
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.kucoin.com"
        self.batch_size = 20
        self.request_delay = 0.2  # Slightly longer delay for KuCoin
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to KuCoin API specific intervals"""
        return {
            '1w': '1week',  # Weekly - KuCoin native support
            '4d': '1day',   # 4-day - fetch daily and aggregate
            '3d': '1day',   # 3-day - fetch daily and aggregate
            '2d': '1day',   # 2-day - fetch daily and aggregate
            '1d': '1day',   # Daily - KuCoin native support
            '4h': '4hour'   # 4-hour - KuCoin native support
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 120,     # Weekly needs at least 60+ bars for macro lookback
            '4d': 200,     # 4d needs 200 daily bars to build 50+ 4d candles
            '3d': 180,     # 3d needs 180 daily bars to build 60+ 3d candles
            '2d': 150,     # 2d needs 150 daily bars to build 75+ 2d candles
            '1d': 80,      # Daily needs at least 80 days for history
            '4h': 200      # 4h needs more bars
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT spot trading pairs from KuCoin"""
        async with self.session.get(f"{self.base_url}/api/v1/symbols") as response:
            data = await response.json()
            if data.get('code') == '200000' and 'data' in data:
                symbols = [item['symbol'] for item in data['data'] 
                          if item.get('quoteCurrency') == self.quote_currency and 
                          item.get('enableTrading', False)]
                return sorted(symbols)
            else:
                logging.error(f"Error fetching KuCoin spot symbols: {data}")
                return []

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from KuCoin spot market"""
        url = f"{self.base_url}/api/v1/market/candles"
        
        # Set API parameters based on timeframe
        # For weekly data, always fetch daily data and build weekly from scratch
        # KuCoin's weekly data starts on Sunday, but we want Monday-based weeks
        if self.timeframe == '1w':
            api_interval = '1day'
        elif self.timeframe in ["2d", "3d", "4d"]:
            api_interval = '1day'
        else:
            api_interval = self.interval_map[self.timeframe]
        
        # Calculate end time (now)
        end_time = int(time.time())
        
        # Adjust fetch limit for weekly data to ensure we have enough daily candles
        fetch_limit = 500 if self.timeframe == '1w' else self.fetch_limit
        
        params = {
            'symbol': symbol,
            'type': api_interval,
            'endAt': end_time,
            'limit': fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == '200000' and 'data' in data:
                    # KuCoin returns: [time, open, close, high, low, volume, turnover]
                    # Note: KuCoin has different column order than other exchanges
                    columns = ['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover']
                    df = pd.DataFrame(data['data'], columns=columns)
                    
                    # Convert types
                    df = df.astype({
                        'timestamp': 'int64',
                        'open': 'float',
                        'high': 'float',
                        'low': 'float',
                        'close': 'float',
                        'volume': 'float'
                    })
                    
                    # KuCoin timestamp is in seconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    
                    # Reorder columns to standard OHLCV format
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # KuCoin data may come in reverse order, ensure oldest first
                    if len(df) > 1 and df.index[0] > df.index[-1]:
                        df = df.sort_index()
                    
                    # Process according to timeframe
                    if self.timeframe == '2d':
                        df = self.aggregate_to_2d(df)
                    elif self.timeframe == '3d':
                        df = self.aggregate_to_3d(df)
                    elif self.timeframe == '4d':
                        df = self.aggregate_to_4d(df)
                    elif self.timeframe == '1w':
                        # Use custom weekly aggregation for Monday-based weeks
                        df = self.build_weekly_candles(df)
                    
                    return df
                else:
                    # Handle KuCoin error responses
                    if data.get('code') == '400005':  # Invalid symbol
                        logging.warning(f"Invalid symbol {symbol} on KuCoin")
                    elif data.get('code') == '429000':  # Rate limit
                        logging.warning(f"Rate limit exceeded for {symbol} on KuCoin")
                    else:
                        logging.error(f"KuCoin API error for {symbol}: {data}")
                    return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from KuCoin")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from KuCoin: {str(e)}")
            return None