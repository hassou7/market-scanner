import asyncio
import aiohttp
import logging
import pandas as pd
from datetime import datetime
from .base_client import BaseExchangeClient

class GateioFuturesClient(BaseExchangeClient):
    """
    Gate.io Futures (Perpetuals) exchange API client for fetching market data
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.gateio.ws/api/v4"
        self.batch_size = 20
        self.request_delay = 0.1
        super().__init__(timeframe)

    def _get_interval_map(self):
        return {
            '1w': '1w',
            '2d': '1d',
            '1d': '1d',
            '4h': '4h'
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,
            '2d': 120,
            '1d': 60,
            '4h': 200
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT perpetual futures contracts from Gate.io"""
        url = f"{self.base_url}/futures/usdt/contracts"
        try:
            async with self.session.get(url) as response:
                data = await response.json()
                if isinstance(data, list):
                    # Filter by name ending with '_USDT' since this is the USDT futures endpoint
                    symbols = [item['name'] for item in data if item['name'].endswith('_USDT')]
                    return sorted(symbols)
                else:
                    logging.error(f"Error fetching Gate.io futures symbols: {data}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching Gate.io futures symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str):
        url = f"{self.base_url}/futures/usdt/candlesticks"
        api_interval = self.interval_map[self.timeframe]
        if self.timeframe == "2d":
            api_interval = "1d"
        params = {
            'contract': symbol,
            'interval': api_interval,
            'limit': self.fetch_limit
        }
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                if isinstance(data, list):
                    df = pd.DataFrame(data, columns=['t', 'v', 'c', 'h', 'l', 'o'])
                    df = df.rename(columns={
                        't': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    })
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    return df
                else:
                    logging.error(f"Error fetching klines for {symbol}: {data}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol}: {str(e)}")
            return None