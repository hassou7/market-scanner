# breakout_vsa/helpers.py

import pandas as pd
import numpy as np
import logging

def calculate_basic_indicators(df, params):
    """
    Calculate basic bar characteristics, spread, volume, momentum and bar type indicators
    """
    # Initialize result DataFrame
    result = pd.DataFrame(index=df.index)
    
    # Extract params
    lookback = params['lookback']
    spread_std = params['spread_std']
    spread_abnormal_std = params['spread_abnormal_std']
    momentum_std = params['momentum_std']
    volume_std = params['volume_std']
    volume_abnormal_std = params['volume_abnormal_std']
    
    # Spread Calculations
    result['spread'] = df['high'] - df['low']
    result['mean_spread'] = result['spread'].rolling(lookback).mean()
    result['std_spread'] = result['spread'].rolling(lookback).std()
    result['is_narrow_spread'] = result['spread'] < (result['mean_spread'] - spread_std * result['std_spread'])
    result['is_wide_spread'] = (result['spread'] > (result['mean_spread'] + spread_std * result['std_spread'])) & \
                               (result['spread'] <= (result['mean_spread'] + spread_abnormal_std * result['std_spread']))
    result['is_abnormal_spread'] = result['spread'] > (result['mean_spread'] + spread_abnormal_std * result['std_spread'])
    
    # Volume Calculations
    result['sma20_volume'] = df['volume'].rolling(lookback).mean()
    result['std_volume'] = df['volume'].rolling(lookback).std()
    result['is_low_volume'] = df['volume'] < (result['sma20_volume'] - volume_std * result['std_volume'])
    result['is_high_volume'] = (df['volume'] >= (result['sma20_volume'] - volume_std * result['std_volume'])) & \
                               (df['volume'] <= (result['sma20_volume'] + volume_abnormal_std * result['std_volume']))
    result['is_abnormal_volume'] = df['volume'] > (result['sma20_volume'] + volume_abnormal_std * result['std_volume'])
    
    # Close Position Calculations
    result['bar_range'] = df['high'] - df['low']
    result['close_position'] = np.where(
        result['bar_range'] != 0, 
        (df['close'] - df['low']) / result['bar_range'], 
        0
    )
    result['is_in_highs'] = result['close_position'] > 0.75
    result['is_off_highs'] = result['close_position'] <= 0.5
    result['is_in_lows'] = result['close_position'] < 0.25
    result['is_off_lows'] = result['close_position'] >= 0.5
    
    # Momentum Calculations
    result['momentum'] = df['close'] - df['close'].shift(1)
    result['abs_momentum'] = result['momentum'].abs()
    result['mean_momentum'] = result['abs_momentum'].rolling(lookback).mean()
    result['std_momentum'] = result['abs_momentum'].rolling(lookback).std()
    result['is_narrow_momentum'] = result['abs_momentum'] < (result['mean_momentum'] - momentum_std * result['std_momentum'])
    result['is_wide_momentum'] = result['abs_momentum'] > (result['mean_momentum'] + momentum_std * result['std_momentum'])
    
    # Bar Direction Calculations
    result['is_up_bar'] = df['close'] > df['close'].shift(1)
    result['is_down_bar'] = df['close'] < df['close'].shift(1)
    
    # Bar Type Calculations
    result['is_new_high'] = (df['high'] > df['high'].shift(1)) & (df['low'] >= df['low'].shift(1))
    result['is_new_low'] = (df['low'] < df['low'].shift(1)) & (df['high'] <= df['high'].shift(1))
    result['is_outside_bar'] = (df['high'] > df['high'].shift(1)) & (df['low'] < df['low'].shift(1))
    result['is_inside_bar'] = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    
    # Breakout Close Detection
    v1_macro_short_lookback = params['v1_macro_short_lookback']
    breakout_close_percent = params['breakout_close_percent']
    
    result['highest_close_short'] = df['close'].rolling(v1_macro_short_lookback).max()
    result['lowest_close_short'] = df['close'].rolling(v1_macro_short_lookback).min()
    result['close_range'] = result['highest_close_short'] - result['lowest_close_short']
    result['breakout_threshold'] = result['highest_close_short'] - (result['close_range'] * (breakout_close_percent / 100))
    result['is_breakout_close'] = df['close'] >= result['breakout_threshold']
    
    return result

def calculate_price_based_macro(df, result, params):
    """
    Calculate price-based macro indicators (V1 method)
    """
    # Extract params
    v1_macro_short_lookback = params['v1_macro_short_lookback']
    v1_macro_medium_lookback = params['v1_macro_medium_lookback']
    v1_macro_long_lookback = params['v1_macro_long_lookback']
    v1_macro_percentile = params['v1_macro_percentile']
    
    # Macro Lows/Highs Detection (Version 1 - based on price levels)
    result['v1_lowest_short'] = df['low'].rolling(v1_macro_short_lookback).min()
    result['v1_highest_short'] = df['high'].rolling(v1_macro_short_lookback).max()
    
    # Handle NA values in calculations
    result['v1_is_low_short'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_lowest_short'].notna()) & (df['low'].notna()) & 
         (df['low'] <= result['v1_lowest_short'] * (1 + v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_is_high_short'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_highest_short'].notna()) & (df['high'].notna()) & 
         (df['high'] >= result['v1_highest_short'] * (1 - v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_lowest_medium'] = df['low'].rolling(v1_macro_medium_lookback).min()
    result['v1_highest_medium'] = df['high'].rolling(v1_macro_medium_lookback).max()
    
    result['v1_is_low_medium'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_lowest_medium'].notna()) & (df['low'].notna()) & 
         (df['low'] <= result['v1_lowest_medium'] * (1 + v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_is_high_medium'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_highest_medium'].notna()) & (df['high'].notna()) & 
         (df['high'] >= result['v1_highest_medium'] * (1 - v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_lowest_long'] = df['low'].rolling(v1_macro_long_lookback).min()
    result['v1_highest_long'] = df['high'].rolling(v1_macro_long_lookback).max()
    
    result['v1_is_low_long'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_lowest_long'].notna()) & (df['low'].notna()) & 
         (df['low'] <= result['v1_lowest_long'] * (1 + v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_is_high_long'] = np.where(
        (v1_macro_percentile == 100.0) | 
        ((result['v1_highest_long'].notna()) & (df['high'].notna()) & 
         (df['high'] >= result['v1_highest_long'] * (1 - v1_macro_percentile / 100))),
        True, False
    )
    
    result['v1_is_macro_low'] = result['v1_is_low_short'] & result['v1_is_low_medium'] & result['v1_is_low_long']
    result['v1_is_macro_high'] = result['v1_is_high_short'] & result['v1_is_high_medium'] & result['v1_is_high_long']
    
    return result

def count_lower_lows(series, lookback_period):
    """
    Count how many previous bars have lower lows than current bar
    """
    count_series = pd.Series(index=series.index, dtype=int)
    for i in range(len(series)):
        if i < lookback_period:
            count_series.iloc[i] = 0
            continue
            
        count = 0
        current_low = series.iloc[i]
        for j in range(1, lookback_period + 1):
            if i-j >= 0 and current_low > series.iloc[i-j]:
                count += 1
        count_series.iloc[i] = count
    return count_series

def count_higher_highs(series, lookback_period):
    """
    Count how many previous bars have higher highs than current bar
    """
    count_series = pd.Series(index=series.index, dtype=int)
    for i in range(len(series)):
        if i < lookback_period:
            count_series.iloc[i] = 0
            continue
            
        count = 0
        current_high = series.iloc[i]
        for j in range(1, lookback_period + 1):
            if i-j >= 0 and current_high < series.iloc[i-j]:
                count += 1
        count_series.iloc[i] = count
    return count_series

def calculate_high_breakout(df, high_breakout_lookback=20, high_breakout_count_percent=80):
    """
    Calculates high breakout based on count of prior bars with highs below current close
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC data
        high_breakout_lookback (int): Lookback period for checking highs
        high_breakout_count_percent (float): Percentage threshold for breakout confirmation
        
    Returns:
        pd.Series: Boolean series indicating where high breakout condition is met
    """
    # Initialize result series with False values
    is_high_breakout = pd.Series(False, index=df.index)
    
    for i in range(len(df)):
        # Skip the first few bars where we don't have enough history
        if i < high_breakout_lookback + 2:
            continue
        
        # Check if current close exceeds previous 2 bars' highs
        is_above_prev_two = df['close'].iloc[i] > df['high'].iloc[i-1] and df['close'].iloc[i] > df['high'].iloc[i-2]
        
        if not is_above_prev_two:
            continue
        
        # Count how many highs in the lookback period (excluding last 2 bars) are below current close
        high_breakout_count = 0
        for j in range(3, high_breakout_lookback + 3):
            if i-j >= 0 and df['close'].iloc[i] > df['high'].iloc[i-j]:
                high_breakout_count += 1
        
        # Calculate percentage based on adjusted lookback (total lookback - 2)
        adjusted_lookback = high_breakout_lookback
        high_breakout_pct = (high_breakout_count / adjusted_lookback) * 100 if adjusted_lookback > 0 else 0
        
        # Set result based on threshold
        is_high_breakout.iloc[i] = high_breakout_pct >= high_breakout_count_percent
    
    return is_high_breakout
    
def calculate_count_based_macro(df, result, params):
    """
    Calculate count-based macro indicators (V2 method)
    """
    # Extract params
    v2_macro_short_lookback = params['v2_macro_short_lookback']
    v2_macro_medium_lookback = params['v2_macro_medium_lookback']
    v2_macro_long_lookback = params['v2_macro_long_lookback']
    v2_macro_percentile = params['v2_macro_percentile']
    
    # Short-term lookback
    result['v2_count_lower_lows_short'] = count_lower_lows(df['low'], v2_macro_short_lookback)
    result['v2_count_higher_highs_short'] = count_higher_highs(df['high'], v2_macro_short_lookback)
    
    result['v2_pct_lower_lows_short'] = result['v2_count_lower_lows_short'] / v2_macro_short_lookback * 100
    result['v2_pct_higher_highs_short'] = result['v2_count_higher_highs_short'] / v2_macro_short_lookback * 100
    
    # Medium-term lookback
    result['v2_count_lower_lows_medium'] = count_lower_lows(df['low'], v2_macro_medium_lookback)
    result['v2_count_higher_highs_medium'] = count_higher_highs(df['high'], v2_macro_medium_lookback)
    
    result['v2_pct_lower_lows_medium'] = result['v2_count_lower_lows_medium'] / v2_macro_medium_lookback * 100
    result['v2_pct_higher_highs_medium'] = result['v2_count_higher_highs_medium'] / v2_macro_medium_lookback * 100
    
    # Long-term lookback
    result['v2_count_lower_lows_long'] = count_lower_lows(df['low'], v2_macro_long_lookback)
    result['v2_count_higher_highs_long'] = count_higher_highs(df['high'], v2_macro_long_lookback)
    
    result['v2_pct_lower_lows_long'] = result['v2_count_lower_lows_long'] / v2_macro_long_lookback * 100
    result['v2_pct_higher_highs_long'] = result['v2_count_higher_highs_long'] / v2_macro_long_lookback * 100
    
    # Define macro low/high based on percentile threshold
    result['v2_is_macro_low'] = (result['v2_pct_lower_lows_short'] <= v2_macro_percentile) & \
                               (result['v2_pct_lower_lows_medium'] <= v2_macro_percentile) & \
                               (result['v2_pct_lower_lows_long'] <= v2_macro_percentile)
    
    result['v2_is_macro_high'] = (result['v2_pct_higher_highs_short'] <= v2_macro_percentile) & \
                                (result['v2_pct_higher_highs_medium'] <= v2_macro_percentile) & \
                                (result['v2_pct_higher_highs_long'] <= v2_macro_percentile)
    
    # Select the appropriate macro method
    macro_method = params['macro_method']
    if macro_method == "Price Based (V1)":
        result['is_macro_low'] = result['v1_is_macro_low']
        result['is_macro_high'] = result['v1_is_macro_high']
    elif macro_method == "Count Based (V2)":
        result['is_macro_low'] = result['v2_is_macro_low']
        result['is_macro_high'] = result['v2_is_macro_high']
    else:  # "Combined (Strict)"
        result['is_macro_low'] = result['v1_is_macro_low'] & result['v2_is_macro_low']
        result['is_macro_high'] = result['v1_is_macro_high'] & result['v2_is_macro_high']
    
    return result

def calculate_arctangent_ratio(df):
    H2 = df['high']
    H1 = df['high'].shift(1)
    L2 = df['low']
    atan_H2_H1 = np.degrees(np.arctan(H2 - H1))
    atan_H1_L2 = np.degrees(np.arctan(H1 - L2))
    
    ratio = np.where(atan_H1_L2 != 0, atan_H2_H1 / atan_H1_L2, np.nan)
    
    return pd.Series(ratio, index=df.index)
    
def apply_condition_filters(df, result, params):
    """
    Apply all condition filters based on the configured parameters, including optional arctangent ratio.
    """
    # Extract params
    spread_opt = params['spread_opt']
    momentum_opt = params['momentum_opt']
    volume_opt = params['volume_opt']
    close_opt = params['close_opt']
    direction_opt = params['direction_opt']
    bar_type_opt = params['bar_type_opt']
    macro_opt = params['macro_opt']
    use_breakout_close = params['use_breakout_close']
    use_arctangent_ratio = params.get('use_arctangent_ratio', False)
    arctangent_ratio_threshold = params.get('arctangent_ratio_threshold', 0.0)

    # Add high breakout parameters with defaults if not provided
    use_high_breakout = params.get('use_high_breakout', False)
    high_breakout_lookback = params.get('high_breakout_lookback', 10)
    high_breakout_count_percent = params.get('high_breakout_count_percent', 10)
    
    # Calculate arctangent ratio for all bars and store in result
    result['arctan_ratio'] = calculate_arctangent_ratio(df)

    # Calculate high breakout if needed
    if use_high_breakout:
        result['is_high_breakout'] = calculate_high_breakout(df, high_breakout_lookback, high_breakout_count_percent)
    
    # Initialize condition as True for all rows
    condition = pd.Series(True, index=df.index)
    
    # Spread condition
    if spread_opt == "Wide":
        condition = condition & result['is_wide_spread']
    elif spread_opt == "Narrow":
        condition = condition & result['is_narrow_spread']
    elif spread_opt == "Abnormal":
        condition = condition & result['is_abnormal_spread']
    
    # Momentum condition
    if momentum_opt == "Wide":
        condition = condition & result['is_wide_momentum']
    elif momentum_opt == "Narrow":
        condition = condition & result['is_narrow_momentum']
    
    # Volume condition
    if volume_opt == "High":
        condition = condition & result['is_high_volume']
    elif volume_opt == "Low":
        condition = condition & result['is_low_volume']
    elif volume_opt == "Abnormal":
        condition = condition & result['is_abnormal_volume']
    
    # Close location condition
    if close_opt == "In Highs":
        condition = condition & result['is_in_highs']
    elif close_opt == "Off Highs":
        condition = condition & result['is_off_highs']
    elif close_opt == "In Lows":
        condition = condition & result['is_in_lows']
    elif close_opt == "Off Lows":
        condition = condition & result['is_off_lows']
    
    # Bar direction condition
    if direction_opt == "Up":
        condition = condition & result['is_up_bar']
    elif direction_opt == "Down":
        condition = condition & result['is_down_bar']
    
    # Bar type condition
    if bar_type_opt == "New High":
        condition = condition & result['is_new_high']
    elif bar_type_opt == "New Low":
        condition = condition & result['is_new_low']
    elif bar_type_opt == "Outside Bar":
        condition = condition & result['is_outside_bar']
    elif bar_type_opt == "Not Outside Bar":
        condition = condition & ~result['is_outside_bar']
    elif bar_type_opt == "Inside Bar":
        condition = condition & result['is_inside_bar']
    elif bar_type_opt == "New High or Outside Bar":
        condition = condition & (result['is_new_high'] | result['is_outside_bar'])
    elif bar_type_opt == "New Low or Outside Bar":
        condition = condition & (result['is_new_low'] | result['is_outside_bar'])
    
    # Macro condition
    if macro_opt == "Macro Low":
        condition = condition & result['is_macro_low']
    elif macro_opt == "Macro High":
        condition = condition & result['is_macro_high'] & ~result['v1_is_low_short']
    
    # Breakout close condition
    if use_breakout_close:
        condition = condition & result['is_breakout_close']
    
    # Optional arctangent ratio condition
    if use_arctangent_ratio:
        condition = condition & (result['arctan_ratio'] >= arctangent_ratio_threshold)

    # Apply high breakout condition if enabled
    if use_high_breakout:
        condition = condition & result['is_high_breakout']
    
    return condition