# exchanges/gateio_futures_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
from datetime import datetime
from .base_client import BaseExchangeClient

class GateioFuturesClient(BaseExchangeClient):
    """
    Gate.io Futures (Perpetuals) exchange API client for fetching market data
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.gateio.ws/api/v4"
        self.batch_size = 20
        self.request_delay = 0.1
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Gate.io Futures API intervals"""
        return {
            '1w': '1w',    # Weekly - Gate.io futures native support
            '4d': '1d',    # 4-day - fetch daily and aggregate
            '3d': '1d',    # 3-day - fetch daily and aggregate
            '2d': '1d',    # 2-day - fetch daily and aggregate
            '1d': '1d',    # Daily - Gate.io futures native support
            '4h': '4h'     # 4-hour - Gate.io futures native support
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
        """Fetch candlestick data from Gate.io futures market"""
        url = f"{self.base_url}/futures/usdt/candlesticks"
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d, 3d, 4d timeframes, we need to fetch daily data and then aggregate
        if self.timeframe in ["2d", "3d", "4d"]:
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
                    # Gate.io Futures returns: [t, v, c, h, l, o]
                    # t=timestamp, v=volume, c=close, h=high, l=low, o=open
                    df = pd.DataFrame(data, columns=['t', 'v', 'c', 'h', 'l', 'o'])
                    df = df.rename(columns={
                        't': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    })
                    
                    # Convert types
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    # Gate.io timestamp is in seconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    
                    # Reorder to standard OHLCV format
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Ensure data is sorted by timestamp (oldest first)
                    df = df.sort_index()
                    
                    # Process according to timeframe
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    elif self.timeframe == "3d":
                        df = self.aggregate_to_3d(df)
                    elif self.timeframe == "4d":
                        df = self.aggregate_to_4d(df)
                    # For 1w and 1d, Gate.io provides native data
                    # For 4h, Gate.io provides native data
                    
                    return df
                else:
                    # Handle Gate.io futures error responses
                    if isinstance(data, dict):
                        if data.get('label') == 'INVALID_PARAM_VALUE':  # Invalid symbol
                            logging.warning(f"Invalid symbol {symbol} on Gate.io futures")
                        else:
                            logging.error(f"Gate.io futures API error for {symbol}: {data}")
                    else:
                        logging.error(f"Unexpected response format for {symbol}: {data}")
                    return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from Gate.io futures")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from Gate.io futures: {str(e)}")
            return None