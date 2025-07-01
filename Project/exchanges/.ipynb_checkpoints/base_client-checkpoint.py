# exchanges/base_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
from abc import ABC, abstractmethod

class BaseExchangeClient(ABC):
    """
    Base class for exchange API clients
    
    This class provides the common structure and methods that all exchange clients
    should implement, focusing only on data fetching and processing.
    """
    def __init__(self, timeframe="1d"):
        self.session = None
        self.quote_currency = 'USDT'
        self.timeframe = timeframe
        
        # Map timeframes to API-specific format
        self.interval_map = self._get_interval_map()
        
        # Set fetch limit based on timeframe
        self.fetch_limit = self._get_fetch_limit()

    async def init_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    @abstractmethod
    def _get_interval_map(self):
        """Return a dictionary mapping standard timeframes to exchange-specific intervals"""
        pass
    
    @abstractmethod
    def _get_fetch_limit(self):
        """Return the number of candles to fetch based on timeframe"""
        pass
    
    @abstractmethod
    async def get_all_spot_symbols(self):
        """Fetch all available spot trading pairs for the specified quote currency"""
        pass
    
    @abstractmethod
    async def fetch_klines(self, symbol):
        """Fetch candlestick data for the specified symbol"""
        pass
    
    def aggregate_to_2d(self, df):
        """
        Aggregate daily data to 2-day timeframe starting from specific days
        
        This method can be used by any exchange client to convert daily data
        to 2-day candles. Reference date: March 20, 2025 (Thursday).
        """
        if df is None or len(df) < 4:  # Need at least a few days to work with
            return None
            
        try:
            # Make a copy to avoid modifying the original
            df = df.copy()
            
            # Add a helper column to identify which 2-day period each row belongs to
            # Thursday March 20, 2025 was the start of a 2d candle
            reference_date = pd.Timestamp('2025-03-20').normalize()
            
            # Calculate days since reference date for each timestamp
            df['days_diff'] = (df.index.normalize() - reference_date).days
            
            # Group by 2-day periods (integer division by 2 of days difference)
            df['period'] = df['days_diff'] // 2
            
            # Aggregate by period
            agg_df = df.groupby('period').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Create proper timestamps for the aggregated data (using the first day of each period)
            # Get mapping from period to timestamp
            period_to_time = df.groupby('period').apply(lambda x: x.index[0])
            agg_df.index = period_to_time.values
            
            return agg_df
        except Exception as e:
            logging.error(f"Error aggregating to 2d: {str(e)}")
            return None
    
    def aggregate_to_3d(self, df):
        """
        Aggregate daily data to 3-day timeframe starting from specific days
        
        This method can be used by any exchange client to convert daily data
        to 3-day candles. Reference date: March 20, 2025 (Thursday).
        """
        if df is None or len(df) < 6:  # Need at least 6 days to work with
            return None
            
        try:
            # Make a copy to avoid modifying the original
            df = df.copy()
            
            # Add a helper column to identify which 3-day period each row belongs to
            # Thursday March 20, 2025 was the start of a 3d candle
            reference_date = pd.Timestamp('2025-03-20').normalize()
            
            # Calculate days since reference date for each timestamp
            df['days_diff'] = (df.index.normalize() - reference_date).days
            
            # Group by 3-day periods (integer division by 3 of days difference)
            df['period'] = df['days_diff'] // 3
            
            # Aggregate by period
            agg_df = df.groupby('period').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Create proper timestamps for the aggregated data (using the first day of each period)
            # Get mapping from period to timestamp
            period_to_time = df.groupby('period').apply(lambda x: x.index[0])
            agg_df.index = period_to_time.values
            
            return agg_df
        except Exception as e:
            logging.error(f"Error aggregating to 3d: {str(e)}")
            return None
    
    def aggregate_to_4d(self, df):
        """
        Aggregate daily data to 4-day timeframe starting from specific days
        
        This method can be used by any exchange client to convert daily data
        to 4-day candles. Reference date: March 22, 2025 (Saturday).
        """
        if df is None or len(df) < 8:  # Need at least 8 days to work with
            return None
            
        try:
            # Make a copy to avoid modifying the original
            df = df.copy()
            
            # Add a helper column to identify which 4-day period each row belongs to
            # Saturday March 22, 2025 was the start of a 4d candle
            reference_date = pd.Timestamp('2025-03-22').normalize()
            
            # Calculate days since reference date for each timestamp
            df['days_diff'] = (df.index.normalize() - reference_date).days
            
            # Group by 4-day periods (integer division by 4 of days difference)
            df['period'] = df['days_diff'] // 4
            
            # Aggregate by period
            agg_df = df.groupby('period').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Create proper timestamps for the aggregated data (using the first day of each period)
            # Get mapping from period to timestamp
            period_to_time = df.groupby('period').apply(lambda x: x.index[0])
            agg_df.index = period_to_time.values
            
            return agg_df
        except Exception as e:
            logging.error(f"Error aggregating to 4d: {str(e)}")
            return None
    
    def build_weekly_candles(self, df):
        """
        Build weekly candles starting on Monday from daily data
        
        This method can be used by any exchange client to convert daily data
        to weekly candles.
        """
        if df is None or len(df) < 7:  # Need at least a week of data
            return None
            
        try:
            # Ensure data is sorted by date (oldest first)
            df = df.sort_index()
            
            # Create a custom grouper for weeks starting on Monday
            df['week_start'] = df.index.to_series().apply(
                lambda x: (x - pd.Timedelta(days=x.dayofweek)).normalize()  # dayofweek: 0=Monday
            )
            
            # Group by week start and aggregate
            weekly_df = df.groupby('week_start').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            return weekly_df
        except Exception as e:
            logging.error(f"Error building weekly candles: {str(e)}")
            return None

    def get_aggregation_method(self, timeframe):
        """
        Get the appropriate aggregation method based on timeframe
        
        This helper method can be used by exchange clients to determine
        which aggregation method to use for custom timeframes.
        """
        aggregation_methods = {
            '2d': self.aggregate_to_2d,
            '3d': self.aggregate_to_3d,
            '4d': self.aggregate_to_4d,
            '1w': self.build_weekly_candles
        }
        return aggregation_methods.get(timeframe.lower())
    
    def get_reference_dates(self):
        """
        Get reference dates for custom timeframe aggregations
        
        Returns a dictionary with reference dates for each custom timeframe.
        """
        return {
            '2d': pd.Timestamp('2025-03-20'),  # Thursday
            '3d': pd.Timestamp('2025-03-20'),  # Thursday
            '4d': pd.Timestamp('2025-03-22'),  # Saturday
            '1w': None  # Weekly uses Monday calculation, no fixed reference date
        }
    
    def validate_aggregation_data(self, df, timeframe):
        """
        Validate that we have enough data for the requested timeframe aggregation
        
        Returns True if we have sufficient data, False otherwise.
        """
        if df is None or len(df) == 0:
            return False
        
        min_days_required = {
            '1d': 1,
            '2d': 4,
            '3d': 6,
            '4d': 8,
            '1w': 7
        }
        
        required_days = min_days_required.get(timeframe.lower(), 1)
        return len(df) >= required_days