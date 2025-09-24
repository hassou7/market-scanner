#custom_strategies/bullish_engulfing.py

import pandas as pd
import numpy as np

def detect_bullish_engulfing(df, check_bar=-2):
    """
    Detect if the specified candle satisfies the bullish engulfing reversal condition.
    
    Parameters:
    df : pandas.DataFrame
        DataFrame containing OHLC data with columns: 'open', 'high', 'low', 'close' (and optionally 'volume')
    check_bar : int
        Which bar to check (default -2 for last closed candle, -1 for current)
        
    Returns:
    bool, dict
        Boolean indicating if bullish engulfing reversal was detected, and dictionary with details
    """
    if len(df) < 50:  # Need at least 50 candles for reliable calculations (matching example)
        return False, {}
    
    # Copy the DataFrame to avoid modifying the original
    df = df.copy()
    
    # Calculate spread and low_wick
    df['spread'] = df['high'] - df['low']
    df['low_wick'] = df['close'] - df['low']  # Direct translation from PineScript
    
    # Calculate close_position
    df['close_position'] = np.where(df['spread'] != 0, (df['close'] - df['low']) / df['spread'], np.nan)
    
    # Calculate ATR(3) using simple moving average (matching example's ATR approach)
    prev_close = df['close'].shift(1)
    tr = np.maximum(df['high'] - df['low'], 
                    np.maximum(np.abs(df['high'] - prev_close), 
                               np.abs(df['low'] - prev_close)))
    df['atr_3'] = tr.rolling(3).mean()
    
    # Calculate is_buying_power
    df['is_buying_power'] = (df['low_wick'].shift(2) + df['low_wick'].shift(1) + df['low_wick']) > df['atr_3']
    
    # Calculate hl2
    df['hl2'] = (df['high'] + df['low']) / 2
    
    # Helper function for percentrank (approximating PineScript's ta.percentrank)
    def percentrank(series, period):
        return series.rolling(period).apply(
            lambda x: (pd.Series(x).rank(pct=True).iloc[-1]) * 100 if len(x) == period else np.nan,
            raw=False
        )
    
    # Calculate percentranks
    df['pr_spread_21'] = percentrank(df['spread'], 21)
    df['pr_low_21'] = percentrank(df['low'], 21)
    df['pr_hl2_13'] = percentrank(df['hl2'], 13)
    
    # Calculate highest(high[1], 2) which is max(high[1], high[2])
    df['highest_high_prev_2'] = df['high'].shift(1).rolling(2).max()
    
    # Calculate isBullishEngulfing
    df['isBullishEngulfing'] = (
        (df['spread'] > df['spread'].shift(1)) &
        (df['spread'] > df['spread'].shift(2)) &
        (df['low'] < (df['low'].shift(1) + 0.25 * df['spread'].shift(1))) &
        (df['low'] < (df['low'].shift(2) + 0.25 * df['spread'].shift(2))) &
        (df['high'] > df['high'].shift(1)) &
        (df['high'] > df['close'].shift(2)) &
        (df['close'] > df['highest_high_prev_2']) &
        (df['pr_spread_21'] > 20)
    )
    
    # Calculate bullish_engulf_reversal
    df['bullish_engulf_reversal'] = (
        df['isBullishEngulfing'] &
        (df['close_position'] > 0.5) &
        (df['pr_low_21'] < 25) &
        (df['pr_hl2_13'] < 35) &
        df['is_buying_power']
    )
    
    # Determine which bar to check
    if check_bar < 0:
        check_index = len(df) + check_bar
    else:
        check_index = check_bar
        
    # Validate check_index
    if check_index < 0 or check_index >= len(df):
        return False, {}
    
    # Check if the specified candle is a bullish engulfing reversal
    detected = df['bullish_engulf_reversal'].iloc[check_index]
    details = {}
    
    if detected:
        # Calculate volume ratio if volume is available
        volume_ratio = 1.0
        if 'volume' in df.columns and check_index >= 8:
            volume_ratio = df['volume'].iloc[check_index] / df['volume'].iloc[check_index-8:check_index].mean()
        
        # Collect details about the pattern
        details = {
            'date': df.index[check_index],
            'close': df['close'].iloc[check_index],
            'high': df['high'].iloc[check_index],
            'low': df['low'].iloc[check_index],
            'volume_ratio': volume_ratio,
            'close_position': df['close_position'].iloc[check_index],
            'is_buying_power': df['is_buying_power'].iloc[check_index],
            'pr_low_21': df['pr_low_21'].iloc[check_index],
            'pr_hl2_13': df['pr_hl2_13'].iloc[check_index],
            'pr_spread_21': df['pr_spread_21'].iloc[check_index]
        }
    
    return detected, details