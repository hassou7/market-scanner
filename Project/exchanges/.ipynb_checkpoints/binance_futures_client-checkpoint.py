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
    
    This class handles only the API interactions and data fetching functionality,
    without any scanning or messaging logic.
    """
    def __init__(self, timeframe="1d"):
        self.base_url = "https://fapi.binance.com"
        self.batch_size = 20
        self.request_delay = 0.1  # Add a small delay between requests to avoid rate limits
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to Binance Futures API specific intervals"""
        return {
            '1w': '1w',    # Weekly
            '2d': '1d',    # For 2d, we'll fetch daily and aggregate
            '1d': '1d',    # Daily
            '4h': '4h'     # 4-hour
        }
    
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        return {
            '1w': 60,      # Weekly needs at least 40+ bars for macro lookback
            '2d': 120,     # 2d needs 120 daily bars to build enough 2d candles
            '1d': 60,      # Daily needs at least 60 days for history
            '4h': 200      # 4h needs more bars
        }[self.timeframe]

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

    async def fetch_klines(self, symbol: str):
        """Fetch candlestick data from Binance futures market"""
        url = f"{self.base_url}/fapi/v1/klines"
        
        # Get the appropriate interval based on timeframe
        api_interval = self.interval_map[self.timeframe]
        
        # For 2d timeframe, we need to fetch daily data and then aggregate
        if self.timeframe == "2d":
            api_interval = "1d"
        
        params = {
            'symbol': symbol,
            'interval': api_interval,
            'limit': self.fetch_limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if isinstance(data, list):
                    # Binance futures returns: [time, open, high, low, close, volume, ...]
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                              'close_time', 'quote_asset_volume', 'number_of_trades', 
                              'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
                    df = pd.DataFrame(data, columns=columns)
                    
                    # Convert types
                    for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col])
                    
                    # Binance timestamp is in milliseconds
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Keep only what we need
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Only need to aggregate for 2d timeframe
                    if self.timeframe == "2d":
                        df = self.aggregate_to_2d(df)
                    
                    return df
                else:
                    logging.error(f"Error fetching klines for {symbol}: {data}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol}: {str(e)}")
            return None