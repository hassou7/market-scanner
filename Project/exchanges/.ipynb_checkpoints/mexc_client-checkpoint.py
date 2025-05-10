#exchanges/mexc_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from .base_client import BaseExchangeClient

class MexcClient(BaseExchangeClient):
    """
    MEXC exchange API client for fetching market data
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.mexc.com"
        self.batch_size = 20
        self.request_delay = 0.2  # Slightly longer delay for MEXC
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to MEXC API specific intervals"""
        return {
            '1w': '1d',    # Will build weekly from daily
            '2d': '1d',    # Will build 2d from daily
            '1d': '1d',    # Daily
            '4h': '4h'     # 4-hour
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 120,     # Need at least 200 days to build good weekly data
            '2d': 120,     # Need at least 120 days for 2d candles
            '1d': 60,      # Daily needs at least 60 days for history
            '4h': 200      # 4h needs more bars
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT spot trading pairs from MEXC"""
        async with self.session.get(f"{self.base_url}/api/v3/exchangeInfo") as response:
            data = await response.json()
            if 'symbols' in data:
                # Status value is '1' for active markets in MEXC
                symbols = [symbol['symbol'] for symbol in data['symbols'] 
                          if symbol['symbol'].endswith(self.quote_currency) and 
                          symbol['status'] == '1']
                return sorted(symbols)
            else:
                logging.error(f"Error fetching MEXC spot symbols: {data}")
                return []

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from MEXC spot market"""
        url = f"{self.base_url}/api/v3/klines"
        
        # Set API parameters based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # Calculate end time (now)
        end_time = int(time.time() * 1000)  # MEXC uses milliseconds

        # For 4h, calculate start time in hours (4h * fetch_limit)
        fetch_limit = self._get_fetch_limit()  # e.g., 200 for 4h
        if self.timeframe == '4h':
            start_time = end_time - (fetch_limit * 4 * 60 * 60 * 1000)
        else:
            fetch_days = 90 if self.timeframe in ['1w', '2d'] else fetch_limit
            start_time = end_time - (fetch_days * 24 * 60 * 60 * 1000)
        
        
        params = {
            'symbol': symbol,
            'interval': api_interval,
            'startTime': start_time,
            'endTime': end_time,
            'limit': 1000  # Use maximum limit to ensure we get all data
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if isinstance(data, list):
                    # MEXC returns: [time, open, high, low, close, volume, ...]
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                              'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
                    df = pd.DataFrame(data, columns=columns[:len(data[0])] if data else columns)
                    
                    # Convert types
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col])
                    
                    # MEXC timestamp is in milliseconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Reorder columns to standard OHLCV format and keep only what we need
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Ensure data is sorted by date (oldest first)
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