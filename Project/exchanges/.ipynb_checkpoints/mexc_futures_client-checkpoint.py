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
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://contract.mexc.com"
        self.batch_size = 20
        self.request_delay = 0.2  # Increased to match spot client and avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to MEXC Futures API intervals"""
        return {
            '1w': 'Week1',
            '2d': 'Day1',
            '1d': 'Day1',
            '4h': 'Hour4'
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 120,
            '2d': 120,
            '1d': 60,
            '4h': 200
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
        if self.timeframe == "2d":
            api_interval = "Day1"
        params = {'interval': api_interval, 'limit': self.fetch_limit}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logging.error(f"Failed to fetch klines for {symbol}: HTTP {response.status} - {await response.text()}")
                        return None
                    
                    data = await response.json()
                    if data.get('success') and 'data' in data:
                        df = pd.DataFrame(data['data']).rename(columns={'time': 'timestamp', 'vol': 'volume'})
                        for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col])
                        df['timestamp'] = pd.to_datetime(df['timestamp'] * 1000, unit='ms')
                        df.set_index('timestamp', inplace=True)
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                        if self.timeframe == "2d":
                            df = self.aggregate_to_2d(df)
                        return df
                    else:
                        # Check for rate limit error
                        if data.get('code') == 510:  # "Request frequency too fast!"
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                                logging.warning(f"Rate limit hit for {symbol}. Retrying in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                                continue
                        logging.error(f"Error fetching klines for {symbol}: {data}")
                        return None
            except Exception as e:
                logging.error(f"Error fetching klines for {symbol}: {str(e)}")
                return None
        
        logging.error(f"Failed to fetch klines for {symbol} after {max_retries} retries")
        return None