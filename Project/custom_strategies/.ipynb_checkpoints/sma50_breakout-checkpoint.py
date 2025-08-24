"""
50SMA Breakout Strategy - Custom Pattern Detection

This strategy detects clean breakout signals when:
1. Close > 50SMA and Low < 50SMA (classic breakout)
2. Last N bars (configurable, default 7) did NOT close above 50SMA + 0.2*ATR(7)
3. Optional: Close > 50SMA - 0.2*ATR(7) to catch pre-breakouts

The clean breakout filter ensures we catch initial breakout moments rather than 
continuation moves, avoiding late entries on already-extended price action.

The strategy follows the same structure as other custom strategies with 
detection for both current and previous closed bars.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def atr(df, period=14):
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    # True Range calculation
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Average True Range
    return true_range.rolling(period).mean()

def detect_sma50_breakout(df, sma_period=50, atr_period=7, atr_multiplier=0.2, 
                         use_pre_breakout=False, clean_lookback=7, check_bar=-1):
    """
    Detect 50SMA breakout signals
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with OHLCV data
    sma_period : int
        Simple Moving Average period (default: 50)
    atr_period : int
        ATR period for pre-breakout detection (default: 7)
    atr_multiplier : float
        ATR multiplier for pre-breakout threshold (default: 0.2)
    use_pre_breakout : bool
        Enable pre-breakout detection (default: False)
    clean_lookback : int
        Number of previous bars to check for clean breakout (default: 7)
    check_bar : int
        Which bar to check (-1 for current, -2 for last closed)
    
    Returns:
    tuple: (bool, dict) - (detected, result_data)
    """
    
    if df is None or len(df) < max(sma_period, atr_period, clean_lookback) + 2:
        return False, {}
    
    # Convert to DataFrame if needed
    df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
    
    # Ensure all required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # CALCULATE INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # Calculate 50SMA
    sma50 = df['close'].rolling(sma_period).mean()
    
    # Calculate ATR for pre-breakout detection
    atr_values = atr(df, atr_period)
    
    # Pre-breakout threshold (50SMA - 0.2*ATR)
    pre_breakout_threshold = sma50 - (atr_multiplier * atr_values)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # BREAKOUT DETECTION LOGIC
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # Calculate upper breakout threshold (50SMA + 0.2*ATR)
    upper_breakout_threshold = sma50 + (atr_multiplier * atr_values)
    
    # Current bar conditions
    # Classic breakout: Close > 50SMA and Low < 50SMA
    classic_breakout = (df['close'] > sma50) & (df['low'] < sma50)
    
    # Pre-breakout: Close > (50SMA - 0.2*ATR) and Low < 50SMA
    pre_breakout = (df['close'] > pre_breakout_threshold) & (df['low'] < sma50)
    
    # Clean breakout filter: Last N bars should NOT have closed above 50SMA + 0.2*ATR
    # This ensures we catch initial breakouts, not continuation moves
    clean_breakout_filter = pd.Series(True, index=df.index)
    
    for i in range(clean_lookback, len(df)):
        # Check if any of the last N bars (excluding current) closed above upper threshold
        last_n_bars_above = False
        for lookback in range(1, clean_lookback + 1):  # Check bars -1, -2, ..., -N relative to current
            if i - lookback >= 0:
                if df['close'].iloc[i - lookback] > upper_breakout_threshold.iloc[i - lookback]:
                    last_n_bars_above = True
                    break
        
        clean_breakout_filter.iloc[i] = not last_n_bars_above
    
    # Choose detection method based on use_pre_breakout flag
    if use_pre_breakout:
        breakout_signal = pre_breakout & clean_breakout_filter
        breakout_type = "pre_breakout"
    else:
        breakout_signal = classic_breakout & clean_breakout_filter
        breakout_type = "classic_breakout"
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # SIGNAL VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # Check the specified bar
    idx = check_bar
    if idx < 0:
        idx = len(df) + idx  # Convert negative index to positive
    if not 0 <= idx < len(df):
        return False, {}
    
    # Check if breakout signal exists for the specified bar
    if pd.isna(breakout_signal.iloc[idx]) or not breakout_signal.iloc[idx]:
        return False, {}
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # ADDITIONAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # Calculate how far price is above/below SMA
    price_vs_sma = ((df['close'].iloc[idx] - sma50.iloc[idx]) / sma50.iloc[idx] * 100) if not pd.isna(sma50.iloc[idx]) else 0
    
    # Calculate how far low is below SMA
    low_vs_sma = ((df['low'].iloc[idx] - sma50.iloc[idx]) / sma50.iloc[idx] * 100) if not pd.isna(sma50.iloc[idx]) else 0
    
    # Volume analysis
    volume_mean = df['volume'].rolling(7).mean().iloc[idx]
    volume_ratio = df['volume'].iloc[idx] / volume_mean if volume_mean > 0 else 0
    volume_usd = df['volume'].iloc[idx] * df['close'].iloc[idx]
    
    # Bar characteristics
    bar_range = df['high'].iloc[idx] - df['low'].iloc[idx]
    close_off_low = (df['close'].iloc[idx] - df['low'].iloc[idx]) / bar_range * 100 if bar_range > 0 else 0
    
    # Calculate how far the last N bars were from upper threshold (for analysis)
    last_n_bars_distance = []
    for lookback in range(1, clean_lookback + 1):
        if idx - lookback >= 0:
            distance = df['close'].iloc[idx - lookback] - upper_breakout_threshold.iloc[idx - lookback]
            last_n_bars_distance.append(distance)
        else:
            last_n_bars_distance.append(0)
    
    # Calculate average distance of last N bars from upper threshold
    avg_last_n_distance = np.mean(last_n_bars_distance) if last_n_bars_distance else 0
    
    # ATR analysis
    current_atr = atr_values.iloc[idx] if not pd.isna(atr_values.iloc[idx]) else 0
    atr_threshold_distance = abs(df['close'].iloc[idx] - pre_breakout_threshold.iloc[idx]) if not pd.isna(pre_breakout_threshold.iloc[idx]) else 0
    upper_threshold = upper_breakout_threshold.iloc[idx] if not pd.isna(upper_breakout_threshold.iloc[idx]) else 0
    
    # Determine if this is a clean breakout
    is_clean_breakout = clean_breakout_filter.iloc[idx]
    
    # Determine breakout strength
    if use_pre_breakout:
        # For pre-breakout, measure distance from pre-breakout threshold
        breakout_strength = "Strong" if df['close'].iloc[idx] > sma50.iloc[idx] else "Pre-breakout"
    else:
        # For classic breakout, measure how far above SMA
        if price_vs_sma > 2.0:
            breakout_strength = "Strong"
        elif price_vs_sma > 0.5:
            breakout_strength = "Moderate"
        else:
            breakout_strength = "Weak"
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # BUILD RESULT
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    bar_idx = df.index[idx]
    
    result = {
        'timestamp': bar_idx,
        'close_price': df['close'].iloc[idx],
        'volume': df['volume'].iloc[idx],
        'volume_usd': volume_usd,
        'volume_ratio': volume_ratio,
        'close_off_low': close_off_low,
        'bar_range': bar_range,
        'sma50': sma50.iloc[idx],
        'atr': current_atr,
        'price_vs_sma_pct': price_vs_sma,
        'low_vs_sma_pct': low_vs_sma,
        'breakout_type': breakout_type,
        'breakout_strength': breakout_strength,
        'pre_breakout_threshold': pre_breakout_threshold.iloc[idx] if not pd.isna(pre_breakout_threshold.iloc[idx]) else 0,
        'upper_breakout_threshold': upper_threshold,
        'atr_threshold_distance': atr_threshold_distance,
        'is_clean_breakout': is_clean_breakout,
        'clean_lookback_period': clean_lookback,
        'avg_last_n_distance': avg_last_n_distance,
        'direction': 'Up',  # SMA breakout is always bullish
        'current_bar': check_bar == -1,
        'date': bar_idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(bar_idx, 'strftime') else str(bar_idx)
    }
    
    return True, result