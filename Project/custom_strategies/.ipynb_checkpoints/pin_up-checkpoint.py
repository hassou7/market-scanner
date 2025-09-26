#custom_strategies/pin_up.py

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
    out = np.full(len(condition), np.nan)
    last_true = -1
    
    for i in range(len(condition)):
        if condition.iloc[i]:
            last_true = i
            out[i] = 0
        else:
            out[i] = 0 if last_true == -1 else i - last_true
    
    return pd.Series(out, index=condition.index).astype(int)

def detect_pin_up(df, check_bar=-2):
    """
    Detect if the specified candle satisfies the pin up condition.
    
    Parameters:
    df : pandas.DataFrame
        DataFrame containing OHLC data with columns: 'open', 'high', 'low', 'close'
    check_bar : int
        Which bar to check (default -2 for last closed candle, -1 for current)
        
    Returns:
    bool, dict
        Boolean indicating if pin up was detected, and dictionary with details
    """
    if len(df) < 50:  # Need at least 50 candles for the calculation
        return False, {}
    
    # Calculate required indicators
    df = df.copy()
    
    # Calculate ATR with period 7 (matching PineScript)
    prev_close = df['close'].shift(1)
    tr = np.maximum(df['high'] - df['low'], 
                    np.maximum(np.abs(df['high'] - prev_close), 
                              np.abs(df['low'] - prev_close)))
    df['atr_7'] = tr.rolling(7).mean()
    
    # Calculate wicks and body - exact PineScript translation
    df['high_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['low_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['body_size'] = np.abs(df['open'] - df['close'])
    df['range_candle'] = df['high'] - df['low']
    
    # Wick threshold from PineScript
    wick_threshold = 0.85
    
    # Candle classification - exact PineScript logic
    df['high_upper_wick'] = (df['high_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] > df['low_wick'])
    df['high_lower_wick'] = (df['low_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] < df['low_wick'])
    
    df['bearishcandle'] = df['high_upper_wick'] | ((np.maximum(df['open'], df['close']) - df['low']) < df['high_wick'])
    df['bullishcandle'] = df['high_lower_wick'] | ((df['high'] - np.minimum(df['open'], df['close'])) < df['low_wick'])
    
    # Bullish bottom identification - exact PineScript logic
    lowest_low_50 = df['low'].rolling(window=50, min_periods=1).min()
    bullishbottom = (df['bullishcandle'] & 
                    (df['low'] == lowest_low_50) & 
                    (df['range_candle'] < df['atr_7']))
    
    # Get bullish bottom high using valuewhen equivalent
    df['bullishbottom_high'] = df['high'].where(bullishbottom).ffill()
    df['bullishbottom_high_prev'] = df['high'].shift(1).where(bullishbottom).ffill()
    
    # Pin up condition - exact PineScript logic
    pin_up = (
        (df['close'] > df['bullishbottom_high']) &
        (df['high'] > df['bullishbottom_high_prev']) &
        (df['close'] > df['high'].shift(1)) &   # <-- new condition
        (bars_since(bullishbottom.fillna(False)) < 4) &
        (~df['bearishcandle'])
    )

    
    pin_up_cond = pin_up & (pin_up != pin_up.shift(1))
    
    # Determine which bar to check
    if check_bar < 0:
        check_index = len(df) + check_bar
    else:
        check_index = check_bar
        
    # Validate check_index
    if check_index < 0 or check_index >= len(df):
        return False, {}
    
    # Check if the specified candle is a pin up
    pin_up_detected = False
    pin_up_details = {}
    
    if pin_up_cond.iloc[check_index]:
        pin_up_detected = True
        
        # Calculate volume ratio
        if check_index >= 8:  # Need at least 8 bars for volume average
            volume_ratio = df['volume'].iloc[check_index] / df['volume'].iloc[check_index-8:check_index].mean()
        else:
            volume_ratio = 1.0
        
        # Collect details about the pin up pattern
        pin_up_details = {
            'date': df.index[check_index],
            'close': df['close'].iloc[check_index],
            'high': df['high'].iloc[check_index],
            'low': df['low'].iloc[check_index],
            'volume_ratio': volume_ratio,
            'bullishbottom_dist': bars_since(bullishbottom.fillna(False)).iloc[check_index],
            'low_wick_ratio': df['low_wick'].iloc[check_index] / df['body_size'].iloc[check_index] if df['body_size'].iloc[check_index] > 0 else 0,
            'bullish_candle': df['bullishcandle'].iloc[check_index],
            'range_vs_atr': df['range_candle'].iloc[check_index] / df['atr_7'].iloc[check_index] if df['atr_7'].iloc[check_index] > 0 else 0
        }
    
    return pin_up_detected, pin_up_details