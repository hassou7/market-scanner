#custom_strategies/volume_surge.py

import pandas as pd
import numpy as np

def detect_volume_surge(df, lookback_period=65, std_dev=4.0, check_bar=-2):
    """
    Detect if there was a volume surge in the specified bar
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with columns: 'open', 'high', 'low', 'close', 'volume'
    lookback_period : int
        Number of previous candles to consider for volume statistics
    std_dev : float
        Number of standard deviations above mean for volume surge detection
    check_bar : int
        Which bar to check for volume surge (-1 for current bar, -2 for last closed bar)
        
    Returns:
    bool, dict
        Boolean indicating if volume surge was detected, and dictionary with details
    """
    if df is None or len(df) < lookback_period:
        return False, {}
    
    # Ensure check_bar is valid
    if abs(check_bar) > len(df):
        check_bar = -2  # Default to last closed bar if invalid
    
    # Calculate volume statistics
    volume_mean = df['volume'].rolling(lookback_period).mean()
    volume_std = df['volume'].rolling(lookback_period).std()
    volume_upper_band = volume_mean + std_dev * volume_std
    
    # Check if specified candle volume was above upper band
    surge_detected = df['volume'].iloc[check_bar] > volume_upper_band.iloc[check_bar]
    
    if not surge_detected:
        return False, {}
    
    # Calculate score and additional metrics
    selected_volume = df['volume'].iloc[check_bar]
    selected_close = df['close'].iloc[check_bar]
    volume_in_usd = selected_volume * selected_close
    
    # Calculate score using the bar being checked and its previous bar
    score = calculate_score(df, current_idx=check_bar)
    
    # Detect price extreme
    price_extreme = detect_price_extreme(df, lookback=50, current_idx=check_bar)
    
    # Calculate volume ratio
    if check_bar == -1:
        # For current bar, compare to previous 10 bars excluding the last closed bar
        volume_ratio = df['volume'].iloc[check_bar] / df['volume'].iloc[-12:-2].mean()
    else:
        # For last closed bar, compare to previous 10 bars
        volume_ratio = df['volume'].iloc[check_bar] / df['volume'].iloc[check_bar-10:check_bar].mean()
    
    result = {
        'timestamp': df.index[check_bar],
        'volume': selected_volume,
        'volume_usd': volume_in_usd,
        'volume_ratio': volume_ratio,
        'close_price': selected_close,
        'score': score,
        'price_extreme': price_extreme
    }
    
    return surge_detected, result

def calculate_score(df, current_idx=-2):
    """
    Calculate score for the specified candle based on a formula
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with price and volume data
    current_idx : int
        Index of the candle to calculate score for
    
    Returns:
    float
        Score value
    """
    alpha = 1.5       # Multiplier for score calculation
    
    # Get required values
    high_prev = df['high'].iloc[current_idx-1]
    low_prev = df['low'].iloc[current_idx-1]
    close_prev = df['close'].iloc[current_idx-1]
    high = df['high'].iloc[current_idx]
    low = df['low'].iloc[current_idx]
    close = df['close'].iloc[current_idx]
    
    # Calculate ranges
    range_prev = high_prev - low_prev
    range_curr = high - low
    
    # Avoid division by zero
    if range_prev == 0 or range_curr == 0:
        return 0
    
    # Calculate closeRel based on conditions
    if close < low_prev:
        closeRel = -1 + alpha * (close - low_prev) / range_prev
    elif close > high_prev:
        closeRel = 1 + alpha * (close - high_prev) / range_prev
    else:
        closeRel = (close - close_prev) / range_prev
    
    # Calculate final score
    score = (range_curr / range_prev) * (2 * (close - low) / (high - low) - 1) + closeRel
    return score

def detect_price_extreme(df, lookback=50, current_idx=-2):
    """
    Detect if specified candle made new high or low and its color
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with price and volume data
    lookback : int
        Number of bars to look back for price extremes
    current_idx : int
        Index of the candle to check
        
    Returns:
    str
        Description string including price extreme and candle color
    """
    # Get the high and low of current candle
    current_high = df['high'].iloc[current_idx]
    current_low = df['low'].iloc[current_idx]
    current_close = df['close'].iloc[current_idx]
    prev_close = df['close'].iloc[current_idx-1]
    
    # Get the highs and lows of previous candles
    start_idx = max(0, current_idx-lookback)
    prev_high = df['high'].iloc[start_idx:current_idx].max()
    prev_low = df['low'].iloc[start_idx:current_idx].min()
    
    # Determine candle color
    candle_color = "White candle" if current_close > prev_close else "Black candle"
    
    if current_high > prev_high:
        return f"{candle_color} - new high"
    elif current_low < prev_low:
        return f"{candle_color} - new low"
    else:
        return candle_color