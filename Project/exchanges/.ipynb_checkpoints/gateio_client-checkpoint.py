# exchanges/gateio_client.py

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
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    
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
            '1w': '7d',    # Weekly - Gate.io native support
            '4d': '1d',    # 4-day - fetch daily and aggregate
            '3d': '1d',    # 3-day - fetch daily and aggregate
            '2d': '1d',    # 2-day - fetch daily and aggregate
            '1d': '1d',    # Daily - Gate.io native support
            '4h': '4h'     # 4-hour - Gate.io native support
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,      # 60 weekly candles (direct from API)
            '4d': 220,     # 220 daily → aggregate to ~55 4d candles  
            '3d': 170,     # 170 daily → aggregate to ~56 3d candles
            '2d': 110,     # 110 daily → aggregate to 55 2d candles
            '1d': 60,      # 60 daily candles (direct from API)
            '4h': 60       # 60 4h candles (direct from API)
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        """Fetch all USDT spot trading pairs from Gate.io, excluding leveraged tokens"""
        async with self.session.get(f"{self.base_url}/spot/currency_pairs") as response:
            data = await response.json()
            
            # Define patterns to exclude Gate.io leveraged tokens
            excluded_patterns = [
                '3S',    # 3x Short leveraged tokens
                '3L',    # 3x Long leveraged tokens  
                '5S',    # 5x Short leveraged tokens
                '5L'     # 5x Long leveraged tokens
            ]
            
            symbols = []
            for pair in data:
                if (pair.get('quote') == self.quote_currency and 
                    pair.get('trade_status') == 'tradable'):
                    
                    symbol = pair['id']
                    base_currency = symbol.replace('_USDT', '')
                    
                    # Check if symbol contains any excluded leveraged token patterns
                    should_exclude = any(pattern in base_currency for pattern in excluded_patterns)
                    
                    if not should_exclude:
                        symbols.append(symbol)
            
            return sorted(symbols)

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from Gate.io spot market"""
        url = f"{self.base_url}/spot/candlesticks"
        
        # Get the appropriate interval based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d, 3d, 4d timeframes, we need to fetch daily data and then aggregate
        if self.timeframe in ["2d", "3d", "4d"]:
            api_interval = "1d"
        
        params = {
            'currency_pair': symbol,
            'interval': api_interval,
            'limit': self.fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                # Gate.io returns: [timestamp, volume, close, high, low, open, volume_quote, amount]
                # Note: Unique column order compared to other exchanges
                columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open', 'volume_quote', 'amount']
                df = pd.DataFrame(data, columns=columns)
                
                # Convert types
                df = df.astype({
                    'timestamp': 'int64',
                    'open': 'float',
                    'high': 'float',
                    'low': 'float',
                    'close': 'float',
                    'volume': 'float'
                })
                
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
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from Gate.io spot")
            return None
        except Exception as e:
            logging.error(f"Error fetching data for {symbol} from Gate.io spot: {str(e)}")
            return None