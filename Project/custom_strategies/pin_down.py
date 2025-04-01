#custom_strategies/pin_down.py

import pandas as pd
import numpy as np

def bars_since(condition):
    """
    Calculate how many bars have passed since the condition was last True.
    
    Parameters:
    condition : pandas.Series
        Boolean series where True indicates the condition occurred
        
    Returns:
    pandas.Series
        Integer series with the same index as condition, containing the number
        of bars since the condition was last True
    """
    # Create an output array of integers (not Timestamps)
    out = np.full(len(condition), np.nan)
    last_true = -1
    
    # Iterate through the condition Series
    for i in range(len(condition)):
        if condition.iloc[i]:
            last_true = i
            out[i] = 0
        else:
            out[i] = 0 if last_true == -1 else i - last_true
    
    # Return as Series with the same index but numeric values
    return pd.Series(out, index=condition.index).astype(int)

def detect_pin_down(df):
    """
    Detect if the last closed candle satisfies the pin down condition.
    
    Parameters:
    df : pandas.DataFrame
        DataFrame containing OHLC data with columns: 'open', 'high', 'low', 'close'
        
    Returns:
    bool, dict
        Boolean indicating if pin down was detected, and dictionary with details
    """
    if len(df) < 5:  # Need at least 5 candles for the calculation
        return False, {}
    
    # Calculate required indicators
    df = df.copy()
    
    # Calculate ATR with period 3
    df['atr_3'] = df['high'].rolling(3).max() - df['low'].rolling(3).min()
    
    # Calculate wicks and body
    df['high_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['low_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['body_size'] = np.abs(df['open'] - df['close'])
    df['range_candle'] = df['high'] - df['low']
    
    # Check for outsideBar
    outsideBar = (df['high'] > df['high'].shift(1)) & (df['low'] < df['low'].shift(1))
    insideBar = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    
    # Bearish candle identification with wick threshold
    wick_threshold = 0.85
    df['high_upper_wick'] = (df['high_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] > df['low_wick'])
    df['bearish_candle'] = df['high_upper_wick'] | (df['high_wick'] > (np.maximum(df['open'], df['close']) - df['low']))
    
    # Identify bearish top
    highest_close_50 = df['close'].rolling(window=50, min_periods=1).max()
    highest_high_50 = df['high'].rolling(window=50, min_periods=1).max()
    
    bearishtop = (df['bearish_candle'] & 
                 (df['high'] > highest_close_50) &
                 ((df['high'] - df['close']) < df['atr_3']) &
                 (np.abs(df['high'] - highest_high_50) < df['atr_3']) &
                 (~insideBar) &
                 ((df['high'] - df['close']) > (df['close'] - df['low'])))
    
    # Calculate pin down condition
    df['bearishtop_low'] = df['low'].where(bearishtop).ffill()
    pin_down = (df['close'] < df['bearishtop_low']) & (bars_since(bearishtop.fillna(False)) < 4) & (~outsideBar)
    pin_down_cond = pin_down & (pin_down != pin_down.shift(1))
    
    # Check if the last closed candle (the second to last in the dataframe) is a pin down
    pin_down_detected = False
    pin_down_details = {}
    
    if len(df) >= 2 and pin_down_cond.iloc[-2]:  # -2 because -1 is the current forming candle
        pin_down_detected = True
        
        # Calculate volume ratio
        volume_ratio = df['volume'].iloc[-2] / df['volume'].iloc[-10:-2].mean()
        
        # Collect details about the pin down pattern
        pin_down_details = {
            'date': df.index[-2],
            'close': df['close'].iloc[-2],
            'high': df['high'].iloc[-2],
            'low': df['low'].iloc[-2],
            'volume_ratio': volume_ratio,
            'bearishtop_dist': bars_since(bearishtop.fillna(False)).iloc[-2],
            'high_wick_ratio': df['high_wick'].iloc[-2] / df['body_size'].iloc[-2] if df['body_size'].iloc[-2] > 0 else 0,
            'bearish_candle': df['bearish_candle'].iloc[-2]
        }
    
    return pin_down_detected, pin_down_details