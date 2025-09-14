# exchanges/binance_futures_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime
from .base_client import BaseExchangeClient

class BinanceFuturesClient(BaseExchangeClient):
    """
    Binance Futures (Perpetuals) exchange API client for fetching market data
    Updated with support for 1D, 2D, 3D, 4D, 1W timeframes, and 1D_INV (inverted daily closing at 12:00 UTC)
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://fapi.binance.com"  # Futures API base URL
        self.batch_size = 20
        self.request_delay = 0.1  # Add a small delay between requests to avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Binance Futures API specific intervals"""
        return {
            '1w': '1w',    # Weekly - native support
            '4d': '1d',    # 4-day - fetch daily and aggregate
            '3d': '1d',    # 3-day - fetch daily and aggregate
            '2d': '1d',    # 2-day - fetch daily and aggregate
            '1d': '1d',    # Daily - native support
            '1d_inv': '4h', # Inverted daily - fetch 4h and aggregate to 24h periods ending at 12:00 UTC
            '4h': '4h'     # 4-hour - native support
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,      # 60 weekly candles (direct from API)
            '4d': 240,     # 220 daily → aggregate to ~55 4d candles  
            '3d': 180,     # 170 daily → aggregate to ~56 3d candles
            '2d': 120,     # 110 daily → aggregate to 55 2d candles
            '1d': 60,      # 60 daily candles (direct from API)
            '1d_inv': 366, # 61 * 6 4h candles to cover 60 inverted days with buffer
            '4h': 60       # 60 4h candles (direct from API)
        }[self.timeframe]

    def aggregate_to_2d(self, df):
        """Aggregate daily data to 2-day periods"""
        # Use UTC-aware origin to match the timezone of the data
        origin = pd.Timestamp('1970-01-01 00:00:00', tz='UTC')
        daily_2d = df.resample('2D', origin=origin, closed='right', label='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        return daily_2d

    def aggregate_to_3d(self, df):
        """Aggregate daily data to 3-day periods"""
        # Use UTC-aware origin to match the timezone of the data
        origin = pd.Timestamp('1970-01-01 00:00:00', tz='UTC')
        daily_3d = df.resample('3D', origin=origin, closed='right', label='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        return daily_3d

    def aggregate_to_4d(self, df):
        """Aggregate daily data to 4-day periods"""
        # Use UTC-aware origin to match the timezone of the data
        origin = pd.Timestamp('1970-01-01 00:00:00', tz='UTC')
        daily_4d = df.resample('4D', origin=origin, closed='right', label='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        return daily_4d

    def aggregate_to_1d_inv(self, df_4h):
        """Aggregate 4h data to inverted daily (24h periods closing at 12:00 UTC)"""
        origin = pd.Timestamp('1970-01-01 12:00:00', tz='UTC')  # Anchor for 12:00 UTC alignment
        daily = df_4h.resample('24H', origin=origin, closed='right', label='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        return daily
    
    async def get_all_spot_symbols(self):
        """Fetch all USDT perpetual futures contracts from Binance"""
        url = f"{self.base_url}/fapi/v1/exchangeInfo"
        
        try:
            async with self.session.get(url) as response:
                data = await response.json()
                if 'symbols' in data:
                    symbols = [item['symbol'] for item in data['symbols'] 
                              if item['contractType'] == 'PERPETUAL' and 
                              item['symbol'].endswith(self.quote_currency) and 
                              item['status'] == 'TRADING']
                    return sorted(symbols)
                else:
                    logging.error(f"Error fetching Binance futures symbols: {data}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching Binance futures symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str, limit=None):
        """Fetch candlestick data from Binance futures market"""
        url = f"{self.base_url}/fapi/v1/klines"
        
        # Use provided limit or fall back to default
        fetch_limit = limit if limit is not None else self.fetch_limit
        
        # Get the appropriate interval based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d, 3d, 4d timeframes, we need to fetch daily data and then aggregate
        if self.timeframe in ["2d", "3d", "4d"]:
            api_interval = "1d"
            # For aggregated timeframes, we need more daily bars to create the requested number
            if limit is not None:
                # Multiply by the aggregation factor to get enough daily bars
                aggregation_factors = {"2d": 2, "3d": 3, "4d": 4}
                fetch_limit = limit * aggregation_factors[self.timeframe]
        # For 1d_inv, fetch 4h and aggregate
        elif self.timeframe == "1d_inv":
            api_interval = "4h"
            if limit is not None:
                # Fetch extra to account for potential partial periods at the start
                fetch_limit = (limit + 2) * 6  # 6 4h per day, +2 days buffer
        
        params = {
            'symbol': symbol,
            'interval': api_interval,
            'limit': fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if isinstance(data, list):
                    # Binance futures returns same format as spot:
                    # [timestamp, open, high, low, close, volume, close_time, 
                    #  quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, 
                    #  taker_buy_quote_asset_volume, ignore]
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                              'close_time', 'quote_asset_volume', 'number_of_trades', 
                              'taker_buy_base_asset_volume', 
                              'taker_buy_quote_asset_volume', 'ignore']
                    df = pd.DataFrame(data, columns=columns)
                    
                    # Convert numeric columns
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col])
                    
                    # Binance timestamp is in milliseconds - make UTC-aware
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    df.set_index('timestamp', inplace=True)
                    
                    # Keep only OHLCV columns
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Ensure data is sorted by timestamp (oldest first)
                    df = df.sort_index()
                    
                    # Aggregate based on timeframe
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    elif self.timeframe == "3d":
                        df = self.aggregate_to_3d(df)
                    elif self.timeframe == "4d":
                        df = self.aggregate_to_4d(df)
                    elif self.timeframe == "1d_inv":
                        df = self.aggregate_to_1d_inv(df)
                    # For 1w and 1d, Binance provides native data
                    # For 4h, Binance provides native data
                    
                    # If a specific limit was requested and we have aggregated data,
                    # return only the requested number of final candles
                    if limit is not None and self.timeframe in ["2d", "3d", "4d", "1d_inv"]:
                        df = df.tail(limit)
                    
                    return df
                else:
                    # Handle error response from Binance Futures
                    if isinstance(data, dict) and 'code' in data:
                        if data['code'] == -1121:  # Invalid symbol
                            logging.warning(f"Invalid symbol {symbol} on Binance futures")
                        elif data['code'] == -1003:  # Too many requests
                            logging.warning(f"Rate limit exceeded for {symbol}, consider increasing delay")
                        else:
                            logging.error(f"Binance Futures API error for {symbol}: {data}")
                    else:
                        logging.error(f"Unexpected response format for {symbol}: {data}")
                    return None
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol}")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol}: {str(e)}")
            return None