# exchanges/mexc_futures_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime
from .base_client import BaseExchangeClient

class MexcFuturesClient(BaseExchangeClient):
    """
    MEXC Futures (Perpetuals) exchange API client for fetching market data
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://contract.mexc.com"
        self.batch_size = 20
        self.request_delay = 0.2  # Increased to match spot client and avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to MEXC Futures API intervals"""
        return {
            '1w': 'Day1',    # Weekly - build from daily
            '4d': 'Day1',    # 4-day - fetch daily and aggregate
            '3d': 'Day1',    # 3-day - fetch daily and aggregate
            '2d': 'Day1',    # 2-day - fetch daily and aggregate
            '1d': 'Day1',    # Daily - MEXC native support
            '4h': 'Hour4'    # 4-hour - MEXC native support
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 150,     # Weekly needs enough daily bars for proper weekly construction
            '4d': 200,     # 4d needs 200 daily bars to build 50+ 4d candles
            '3d': 180,     # 3d needs 180 daily bars to build 60+ 3d candles
            '2d': 150,     # 2d needs 150 daily bars to build 75+ 2d candles
            '1d': 80,      # Daily needs at least 80 days for history
            '4h': 200      # 4h needs more bars
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT perpetual futures contracts from MEXC"""
        url = f"{self.base_url}/api/v1/contract/detail"
        try:
            async with self.session.get(url) as response:
                data = await response.json()
                if data.get('success') and 'data' in data:
                    symbols = [item['symbol'] for item in data['data'] 
                             if item['symbol'].endswith(self.quote_currency)]
                    return sorted(symbols)
                else:
                    logging.error(f"Error fetching MEXC futures symbols: {data}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching MEXC futures symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from MEXC futures market"""
        url = f"{self.base_url}/api/v1/contract/kline/{symbol}"
        api_interval = self.interval_map[self.timeframe]
        fetch_limit = self.fetch_limit
        
        params = {'interval': api_interval, 'limit': fetch_limit}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logging.error(f"Failed to fetch klines for {symbol}: HTTP {response.status} - {await response.text()}")
                        return None
                    
                    data = await response.json()
                    if data.get('success') and 'data' in data:
                        # MEXC futures returns: {'time': timestamp, 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'vol': volume}
                        df = pd.DataFrame(data['data']).rename(columns={'time': 'timestamp', 'vol': 'volume'})
                        
                        # Convert types
                        for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col])
                        
                        # MEXC futures timestamp is in seconds (not milliseconds like spot)
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        df.set_index('timestamp', inplace=True)
                        
                        # Reorder columns to standard OHLCV format and keep only what we need
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                        
                        # Ensure data is sorted by date (oldest first)
                        df = df.sort_index()
                        
                        # Process according to timeframe
                        if self.timeframe == '2d':
                            df = self.aggregate_to_2d(df)
                        elif self.timeframe == '3d':
                            df = self.aggregate_to_3d(df)
                        elif self.timeframe == '4d':
                            df = self.aggregate_to_4d(df)
                        elif self.timeframe == '1w':
                            df = self.build_weekly_candles(df)
                        
                        return df
                    else:
                        # Check for rate limit error
                        if data.get('code') == 510:  # "Request frequency too fast!"
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                                logging.warning(f"Rate limit hit for {symbol}. Retrying in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                                continue
                        elif data.get('code') == -1121:  # Invalid symbol
                            logging.warning(f"Invalid symbol {symbol} on MEXC futures")
                        else:
                            logging.error(f"MEXC futures API error for {symbol}: {data}")
                        return None
            except asyncio.TimeoutError:
                logging.error(f"Timeout fetching klines for {symbol} from MEXC futures")
                return None
            except Exception as e:
                logging.error(f"Error fetching klines for {symbol} from MEXC futures: {str(e)}")
                return None
        
        logging.error(f"Failed to fetch klines for {symbol} after {max_retries} retries")
        return None