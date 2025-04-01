import pandas as pd
import numpy as np

def detect_volume_surge(df, lookback_period=65, std_dev=4.0):
    """
    Detect if there was a volume surge in the previous candle
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with columns: 'open', 'high', 'low', 'close', 'volume'
    lookback_period : int
        Number of previous candles to consider for volume statistics
    std_dev : float
        Number of standard deviations above mean for volume surge detection
        
    Returns:
    bool, dict
        Boolean indicating if volume surge was detected, and dictionary with details
    """
    if df is None or len(df) < lookback_period:
        return False, {}

    # Calculate volume statistics
    volume_mean = df['volume'].rolling(lookback_period).mean()
    volume_std = df['volume'].rolling(lookback_period).std()
    volume_upper_band = volume_mean + std_dev * volume_std
    
    # Check if previous candle volume was above upper band
    surge_detected = df['volume'].iloc[-2] > volume_upper_band.iloc[-2]
    
    if not surge_detected:
        return False, {}
    
    # Calculate score and additional metrics
    prev_volume = df['volume'].iloc[-2]
    prev_close = df['close'].iloc[-2]
    volume_in_usd = prev_volume * prev_close
    
    # Calculate score
    score = calculate_score(df)
    
    # Detect price extreme
    price_extreme = detect_price_extreme(df)
    
    # Calculate volume ratio
    volume_ratio = df['volume'].iloc[-2] / df['volume'].iloc[-10:-2].mean()
    
    result = {
        'timestamp': df.index[-2],
        'volume': prev_volume,
        'volume_usd': volume_in_usd,
        'volume_ratio': volume_ratio,
        'close_price': prev_close,
        'score': score,
        'price_extreme': price_extreme
    }
    
    return surge_detected, result

def calculate_score(df):
    """Calculate score for the previous candle based on a formula"""
    current_idx = -2  # Previous candle (where we detected surge)
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

def detect_price_extreme(df, lookback=50):
    """
    Detect if previous candle made new high or low and its color
    Returns description string including price extreme and candle color
    """
    current_idx = -2  # Previous candle

    # Get the high and low of current candle
    current_high = df['high'].iloc[current_idx]
    current_low = df['low'].iloc[current_idx]
    current_close = df['close'].iloc[current_idx]
    prev_close = df['close'].iloc[current_idx-1]

    # Get the highs and lows of previous candles
    prev_high = df['high'].iloc[current_idx-lookback:current_idx].max()
    prev_low = df['low'].iloc[current_idx-lookback:current_idx].min()

    # Determine candle color
    candle_color = "White candle" if current_close > prev_close else "Black candle"

    if current_high > prev_high:
        return f"{candle_color} - new high"
    elif current_low < prev_low:
        return f"{candle_color} - new low"
    else:
        return candle_color