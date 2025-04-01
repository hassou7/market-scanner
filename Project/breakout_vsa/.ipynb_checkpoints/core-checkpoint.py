#breakout_vsa/core.py

import pandas as pd
import numpy as np
from .helpers import (
    calculate_basic_indicators,
    calculate_price_based_macro,
    calculate_count_based_macro,
    apply_condition_filters
)

def vsa_detector(df, strategy_params):
    """
    General VSA pattern detector that uses the configured strategy parameters.
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with columns: 'open', 'high', 'low', 'close', 'volume'
    strategy_params : dict
        Dictionary of parameters for the strategy
        
    Returns:
    pandas.Series
        Boolean series indicating where the pattern conditions are met
    """
    # Ensure we have all required columns
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain column: {col}")
    
    # Special case for start bar pattern
    if strategy_params.get('is_start_bar', False):
        condition = calculate_start_bar(
            df, 
            lookback=strategy_params.get('lookback', 5),
            volume_lookback=strategy_params.get('volume_lookback', 30),
            volume_percentile=strategy_params.get('volume_percentile', 50),
            low_percentile=strategy_params.get('low_percentile', 75),
            range_percentile=strategy_params.get('range_percentile', 75),
            close_off_lows_percent=strategy_params.get('close_off_lows_percent', 50),
            prev_close_range=strategy_params.get('prev_close_range', 75)
        )
        
        # Create a result DataFrame to maintain consistent return structure
        result = pd.DataFrame(index=df.index)
        
        # Add arctan ratio for consistency with other patterns
        result['arctan_ratio'] = pd.Series(np.nan, index=df.index)
        
        return condition, result
    
    # Standard VSA pattern flow for other patterns
    # Calculate all necessary indicators using helper functions
    result = calculate_basic_indicators(df, strategy_params)
    
    # Calculate price-based macro indicators (V1)
    result = calculate_price_based_macro(df, result, strategy_params)
    
    # Calculate count-based macro indicators (V2)
    result = calculate_count_based_macro(df, result, strategy_params)
    
    # Apply filters based on configured conditions
    condition = apply_condition_filters(df, result, strategy_params)
    
    return condition, result

# Functions for specific strategies - provides backward compatibility

def breakout_bar_vsa(df):
    """Detect breakout bars with the breakout bar strategy"""
    from .strategies.breakout_bar import get_params
    strategy_params = get_params()
    return vsa_detector(df, strategy_params)

def stop_bar_vsa(df):
    """Detect stop bars with the stop bar strategy"""
    from .strategies.stop_bar import get_params
    strategy_params = get_params()
    return vsa_detector(df, strategy_params)

def reversal_bar_vsa(df):
    """Detect reversal bars with the reversal bar strategy"""
    from .strategies.reversal_bar import get_params
    strategy_params = get_params()
    return vsa_detector(df, strategy_params)

def start_bar_vsa(df):
    """Detect Start Bar pattern"""
    from .strategies.start_bar import get_params
    strategy_params = get_params()
    return vsa_detector(df, strategy_params)

def calculate_start_bar(df, lookback=5, volume_lookback=30, volume_percentile=50, 
                       low_percentile=75, range_percentile=75, close_off_lows_percent=50,
                       prev_close_range=75):
    """
    Calculate the Start Bar pattern indicator based on updated conditions
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with columns: 'high', 'low', 'close', 'volume'
    """
    # Convert the input data to a DataFrame if it's not already
    df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df
    
    def percentile_rank(series, length):
        """Calculate percentile rank of current value within a rolling window"""
        def rank_in_window(window):
            current = window[-1]
            rank = sum(1.0 for x in window if x <= current)
            return (rank / len(window)) * 100
        return series.rolling(length).apply(rank_in_window, raw=True)
    
    def is_in_bottom_percent(series, length, percent):
        """Check if value is in bottom percentage of range"""
        ranks = percentile_rank(series, length)
        return ranks <= percent
    
    def is_in_top_percent(series, length, percent):
        """Check if value is in top percentage of range"""
        ranks = percentile_rank(series, length)
        return ranks >= percent
    
    # Calculate basic bar characteristics
    df['bar_range'] = df['high'] - df['low']
    df['volume_rank'] = percentile_rank(df['volume'], lookback)
    
    # Calculate rolling values using volume_lookback
    df['macro_low'] = df['low'].rolling(volume_lookback).min()
    df['macro_high'] = df['high'].rolling(volume_lookback).min()
    df['highest_high'] = df['high'].rolling(lookback).max()
    
    # Volume conditions
    df['volume_sma'] = df['volume'].rolling(volume_lookback).mean()
    df['volume_std'] = df['volume'].rolling(volume_lookback).std()
    df['excess_volume'] = df['volume'] > (df['volume_sma'] + 3.0 * df['volume_std'])
    
    # Range conditions with volume_lookback
    df['range_sma'] = df['bar_range'].rolling(volume_lookback).mean()
    df['range_std'] = df['bar_range'].rolling(volume_lookback).std()
    df['excess_range'] = df['bar_range'] > (df['range_sma'] + 3.0 * df['range_std'])
    
    # Volume conditions
    df['is_higher_volume'] = is_in_top_percent(df['volume'], lookback, volume_percentile)
    df['is_high_volume'] = (df['volume'] > 0.75 * df['volume_sma']) & (df['volume'] > df['volume'].shift(1))
    
    # Price action conditions
    df['has_higher_high'] = df['high'] > df['high'].shift(1)
    df['no_narrow_range'] = is_in_top_percent(df['bar_range'], lookback, range_percentile)
    
    # Low price condition
    df['is_in_the_lows'] = (
        (df['low'] - df['macro_low']).abs() < df['bar_range']
    ) | is_in_bottom_percent(df['low'], volume_lookback, low_percentile)
    
    # Close position conditions
    df['close_in_the_highs'] = (
        (df['close'] - df['low']) / df['bar_range']
    ) >= (close_off_lows_percent / 100)
    
    # Previous close distance condition
    df['far_prev_close'] = (
        (df['close'] - df['close'].shift(1)).abs() >=
        (df['bar_range'].shift(1) * (prev_close_range / 100))
    )
    
    # New highs condition
    df['new_highs'] = df['high'] >= 0.75 * df['highest_high']
    
    # Optional strength condition
    df['strong_close'] = df['close'] >= df['highest_high'].shift(1)
    
    # Combine all conditions for the Start Bar pattern
    start_bar_pattern = (
        df['is_high_volume'] &
        df['has_higher_high'] &
        df['no_narrow_range'] &
        df['close_in_the_highs'] &
        df['far_prev_close'] &
        ~df['excess_range'] &
        ~df['excess_volume'] &
        df['new_highs'] &
        df['is_in_the_lows']
    )
    
    # Signal only new occurrences
    start_bar = start_bar_pattern & ~start_bar_pattern.shift(1).fillna(False)
    
    return start_bar