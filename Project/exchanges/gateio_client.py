import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from .base_client import BaseExchangeClient

class GateioClient(BaseExchangeClient):
    """
    Gate.io exchange API client for fetching market data
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.gateio.ws/api/v4"
        self.batch_size = 20
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Gate.io API specific intervals"""
        return {
            '1w': '7d',    # Weekly
            '2d': '1d',    # For 2d, we'll fetch daily and aggregate
            '1d': '1d',    # Daily
            '4h': '4h'     # 4-hour
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
        """Fetch all USDT spot trading pairs from Gate.io"""
        async with self.session.get(f"{self.base_url}/spot/currency_pairs") as response:
            data = await response.json()
            symbols = [pair['id'] for pair in data 
                      if pair.get('quote') == self.quote_currency and 
                      pair.get('trade_status') == 'tradable']
            return sorted(symbols)

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from Gate.io spot market"""
        url = f"{self.base_url}/spot/candlesticks"
        params = {
            'currency_pair': symbol,
            'interval': self.interval_map[self.timeframe],
            'limit': self.fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open', 'volume_quote', 'amount']
                df = pd.DataFrame(data, columns=columns)
                
                df = df.astype({
                    'timestamp': 'int64',
                    'open': 'float',
                    'high': 'float',
                    'low': 'float',
                    'close': 'float',
                    'volume': 'float'
                })
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
                # For 2d timeframe, aggregate the daily data
                if self.timeframe == "2d":
                    df = self.aggregate_to_2d(df)
                
                return df
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {str(e)}")
            return None