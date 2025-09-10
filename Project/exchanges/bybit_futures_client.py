# exchanges/bybit_futures_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime
from .base_client import BaseExchangeClient

class BybitFuturesClient(BaseExchangeClient):
    """
    Bybit Futures (Perpetuals) exchange API client for fetching market data
    Updated with support for 1D, 2D, 3D, 4D, and 1W timeframes
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.bybit.com"
        self.batch_size = 20
        self.request_delay = 0.1  # Add a small delay between requests to avoid rate limits
        super().__init__(timeframe)
    
    def _get_interval_map(self):
        """Map standard timeframes to Bybit Futures API specific intervals"""
        return {
            '1w': 'W',     # Weekly - Bybit native support
            '4d': 'D',     # 4-day - fetch daily and aggregate
            '3d': 'D',     # 3-day - fetch daily and aggregate
            '2d': 'D',     # 2-day - fetch daily and aggregate
            '1d': 'D',     # Daily - Bybit native support
            '4h': '240'    # 4-hour (240 minutes) - Bybit native support
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
        """Fetch all USDT perpetual futures contracts from Bybit"""
        url = f"{self.base_url}/v5/market/instruments-info"
        params = {
            'category': 'linear',  # Linear perpetual contracts
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                if data['retCode'] == 0 and 'result' in data and 'list' in data['result']:
                    symbols = [item['symbol'] for item in data['result']['list']
                              if item['contractType'] == 'LinearPerpetual' and 
                              item['symbol'].endswith(self.quote_currency) and 
                              item['status'] == 'Trading']
                    return sorted(symbols)
                else:
                    logging.error(f"Error fetching Bybit futures symbols: {data}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching Bybit futures symbols: {str(e)}")
            return []
    
    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from Bybit futures market"""
        url = f"{self.base_url}/v5/market/kline"
        
        # Get the appropriate interval based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d, 3d, 4d timeframes, we need to fetch daily data and then aggregate
        if self.timeframe in ["2d", "3d", "4d"]:
            api_interval = "D"
        
        params = {
            'category': 'linear',
            'symbol': symbol,
            'interval': api_interval,
            'limit': self.fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data['retCode'] == 0 and 'result' in data and 'list' in data['result']:
                    # Bybit returns: [timestamp, open, high, low, close, volume, turnover]
                    df = pd.DataFrame(data['result']['list'], 
                                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                    
                    # Convert types
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col])
                    
                    # Bybit timestamp is in milliseconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Keep only OHLCV columns
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Bybit returns newest first, so reverse to get oldest first
                    df = df[::-1]
                    
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
                    # Handle Bybit futures error responses
                    if data.get('retCode') == 10001:  # Invalid parameter
                        logging.warning(f"Invalid parameter for {symbol} on Bybit futures")
                    elif data.get('retCode') == 110001:  # Symbol not found
                        logging.warning(f"Symbol {symbol} not found on Bybit futures")
                    else:
                        logging.error(f"Bybit futures API error for {symbol}: {data}")
                    return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from Bybit futures")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from Bybit futures: {str(e)}")
            return None