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
            '1w': '1week',  # Weekly (will need adjustment)
            '2d': '1day',   # For 2d, we'll fetch daily and aggregate
            '1d': '1day',   # Daily
            '4h': '4hour'   # 4-hour
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 60,      # Weekly needs at least 50+ bars for macro lookback
            '2d': 120,     # 2d needs double the daily bars to build enough 2d candles
            '1d': 60,      # Daily needs at least 50+ bars for macro lookback
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
        # For 1w timeframe, always fetch daily data and build weekly from scratch
        api_interval = '1day' if self.timeframe == '1w' else self.interval_map[self.timeframe]
        
        # Calculate end time (now)
        end_time = int(time.time())
        
        # For weekly data, we need more daily candles
        fetch_limit = 200 if self.timeframe == '1w' else self.fetch_limit
        
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
                    # Convert to our standard format
                    columns = ['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover']
                    df = pd.DataFrame(data['data'], columns=columns)
                    
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
                    
                    # Check if data is in reverse order
                    if df.index[0] > df.index[-1]:
                        # Data is in reverse order, sort it
                        df = df.sort_index()
                    
                    # Process according to timeframe
                    if self.timeframe == '2d':
                        df = self.aggregate_to_2d(df)
                    elif self.timeframe == '1w':
                        df = self.build_weekly_candles(df)
                    
                    return df
                else:
                    logging.error(f"Error fetching klines for {symbol}: {data}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol}: {str(e)}")
            return None