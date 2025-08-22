"""
Confluence Strategy - Custom Pattern Detection (Updated to match Pine Script v5)

This strategy detects confluence signals based on Volume, Spread, and Momentum analysis.
It combines three different analytical approaches to identify high-probability trading opportunities.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def wma(series, period):
    """Calculate Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def detect_confluence(df, doji_threshold=5.0, ctx_len=7, range_floor=0.10, 
                     len_fast=7, len_mid=13, len_slow=21, check_bar=-1):
    """
    Detect confluence signals based on Volume, Spread, and Momentum analysis
    Updated to match Pine Script v5 implementation exactly
    
    Parameters:
    df : pandas.DataFrame
        DataFrame with OHLCV data
    doji_threshold : float
        Doji threshold percentage (default: 5.0)
    ctx_len : int
        Context bars for range calculation (default: 7)
    range_floor : float
        Range floor value 0-1 (default: 0.10)
    len_fast : int
        WMA fast period (default: 7)
    len_mid : int
        WMA mid period (default: 13)
    len_slow : int
        WMA slow period (default: 21)
    check_bar : int
        Which bar to check (-1 for current, -2 for last closed)
    
    Returns:
    tuple: (bool, dict) - (detected, result_data)
    """
    
    if df is None or len(df) < max(len_slow, ctx_len, 21) + 2:
        return False, {}
    
    # Convert to DataFrame if needed
    df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
    
    # Ensure all required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # OHLCV DATA
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    curr_open = df['open']
    curr_high = df['high']
    curr_low = df['low']
    curr_close = df['close']
    prev_close = df['close'].shift(1)
    prev_high = df['high'].shift(1)
    prev_low = df['low'].shift(1)
    curr_volume = df['volume']
    curr_range = curr_high - curr_low
    prev_range = df['high'].shift(1) - df['low'].shift(1)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # VOLUME ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # VSA Direction Logic
    close_change_pct = np.abs(curr_close - prev_close) / np.maximum(curr_close, prev_close) * 100
    is_doji_like = close_change_pct <= doji_threshold
    
    # VSA Classification
    up_bar_vsa = pd.Series(False, index=df.index)
    down_bar_vsa = pd.Series(False, index=df.index)
    
    # For doji-like bars
    upper_shadow = curr_high - curr_close
    lower_shadow = curr_close - curr_low
    doji_up = lower_shadow > upper_shadow
    doji_down = upper_shadow > lower_shadow
    
    # For normal bars
    is_up_intention = curr_close > prev_close
    is_down_intention = curr_close < prev_close
    
    # Up intention logic
    close_progress = curr_close - prev_close
    potential_progress = curr_high - prev_close
    normal_up = (close_progress >= potential_progress * 0.5) & is_up_intention
    
    # Down intention logic
    close_decline = prev_close - curr_close
    potential_decline = prev_close - curr_low
    normal_down = (close_decline >= potential_decline * 0.5) & is_down_intention
    
    # Combine VSA logic
    up_bar_vsa = np.where(is_doji_like, doji_up, normal_up)
    down_bar_vsa = np.where(is_doji_like, doji_down, 
                           np.where(is_up_intention, ~normal_up, 
                                   np.where(is_down_intention, normal_down, False)))
    
    # Volume Moving Averages and Standard Deviation
    vol_sma7 = curr_volume.rolling(7).mean()
    vol_sma13 = curr_volume.rolling(13).mean()
    vol_sma21 = curr_volume.rolling(21).mean()
    vol_stdv21 = curr_volume.rolling(21).std()
    
    # Track volumes for same directional moves (simplified Python implementation)
    local_relative_high_vol = pd.Series(False, index=df.index)
    broader_relative_high_vol = pd.Series(False, index=df.index)
    serious_volume = pd.Series(False, index=df.index)
    
    for i in range(1, len(df)):
        # Local relative volume
        if up_bar_vsa[i] and i > 0:
            prev_up_vol = curr_volume.iloc[i-1] if up_bar_vsa[i-1] else 0
            local_relative_high_vol.iloc[i] = curr_volume.iloc[i] > prev_up_vol
        elif down_bar_vsa[i] and i > 0:
            prev_down_vol = curr_volume.iloc[i-1] if down_bar_vsa[i-1] else 0
            local_relative_high_vol.iloc[i] = curr_volume.iloc[i] > prev_down_vol
        
        # Broader relative volume (using 3-period average)
        if i >= 3:
            if up_bar_vsa[i]:
                recent_vols = [curr_volume.iloc[j] for j in range(max(0, i-3), i) if up_bar_vsa[j]]
                if recent_vols:
                    avg_vol = np.mean(recent_vols)
                    broader_relative_high_vol.iloc[i] = curr_volume.iloc[i] > avg_vol
            elif down_bar_vsa[i]:
                recent_vols = [curr_volume.iloc[j] for j in range(max(0, i-3), i) if down_bar_vsa[j]]
                if recent_vols:
                    avg_vol = np.mean(recent_vols)
                    broader_relative_high_vol.iloc[i] = curr_volume.iloc[i] > avg_vol
            
            # Serious volume logic
            if broader_relative_high_vol.iloc[i]:
                if up_bar_vsa[i]:
                    # Find last down volume
                    for j in range(i-1, -1, -1):
                        if down_bar_vsa[j]:
                            serious_volume.iloc[i] = curr_volume.iloc[i] > curr_volume.iloc[j]
                            break
                elif down_bar_vsa[i]:
                    # Find last up volume
                    for j in range(i-1, -1, -1):
                        if up_bar_vsa[j]:
                            serious_volume.iloc[i] = curr_volume.iloc[i] > curr_volume.iloc[j]
                            break
    
    # Volume Classifications
    absolute_high_vol = (curr_volume > vol_sma7) & (curr_volume > vol_sma13) & (curr_volume > vol_sma21)
    
    # Extreme volume
    extreme_volume = (curr_volume > (vol_sma21 + 3.0 * vol_stdv21)) & ((curr_volume / vol_sma21) > 3)
    
    # High volume definition
    high_volume = (serious_volume | absolute_high_vol | broader_relative_high_vol | local_relative_high_vol) #& ~extreme_volume
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # SPREAD ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    spread = curr_range
    
    # Close position in bar
    closePosition = (curr_close - curr_low) / curr_range
    isCloseInUpperhigh = closePosition > 0.7
    
    # Weighted moving averages for spread
    wma7_spread = wma(spread, 7)
    wma13_spread = wma(spread, 13)
    wma21_spread = wma(spread, 21)
    
    # Spread Breakout Logic
    tol = 0.95
    
    # Check if WMAs exist (not na) and if spread is above each existing WMA
    above_wma7_spread = spread > (tol * wma7_spread)
    above_wma13_spread = spread > (tol * wma13_spread)
    above_wma21_spread = spread > (tol * wma21_spread)
    
    # Handle NaN values (if WMA doesn't exist, consider condition as True)
    above_wma7_spread = above_wma7_spread.fillna(True)
    above_wma13_spread = above_wma13_spread.fillna(True)
    above_wma21_spread = above_wma21_spread.fillna(True)
    
    # Combine WMA conditions
    above_all_wmas_spread = above_wma7_spread & above_wma13_spread & above_wma21_spread
    
    spread_wakeup = isCloseInUpperhigh & above_all_wmas_spread
    spread_breakout = spread_wakeup & (spread == spread.rolling(3).max())
    
    # Compute extreme spread (same pattern as extreme volume)
    spread_sma21 = spread.rolling(21).mean()
    spread_stdv21 = spread.rolling(21).std()
    
    # Extreme spread - using same approach as extreme volume
    extreme_spread = (spread > (spread_sma21 + 2.0 * spread_stdv21)) & ((spread / spread_sma21) > 2)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # MOMENTUM ANALYSIS (Updated to match Pine Script exactly)
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # ❶ CONTEXT RANGE (last N bars) - Updated logic
    # Find the bar with the highest range in the lookback period
    highest_range_idx = 0
    highest_range = 0.0
    
    # Calculate context range for each bar
    ctxHi = pd.Series(index=df.index, dtype=float)
    ctxLo = pd.Series(index=df.index, dtype=float)
    ctxRng = pd.Series(index=df.index, dtype=float)
    
    for idx in range(ctx_len, len(df)):
        # Reset for each bar
        highest_range = 0.0
        highest_range_idx = 0
        
        # Find highest range in lookback period
        for i in range(1, ctx_len + 1):
            if idx - i >= 0:
                range_val = curr_range.iloc[idx - i]
                if range_val > highest_range:
                    highest_range = range_val
                    highest_range_idx = i
        
        # Initialize context range with fallback values
        ctx_hi = prev_high.iloc[idx-ctx_len:idx].max()  # Default highest high of previous ctx_len bars
        ctx_lo = prev_low.iloc[idx-ctx_len:idx].min()   # Default lowest low of previous ctx_len bars
        
        # Adjust context range starting from the highest-range bar
        if highest_range_idx > 0 and highest_range_idx <= ctx_len:
            range_start = max(0, idx - ctx_len + highest_range_idx - 1)
            ctx_hi = curr_high.iloc[range_start:idx+1].max()
            ctx_lo = curr_low.iloc[range_start:idx+1].min()
        
        ctxHi.iloc[idx] = ctx_hi
        ctxLo.iloc[idx] = ctx_lo
        ctxRng.iloc[idx] = ctx_hi - ctx_lo
    
    # ❂ RANGE COMPARISON FACTOR
    range_factor = np.where(ctxRng > 0, np.maximum(curr_range / ctxRng, range_floor), range_floor)
    
    # ❸ POSITIONAL TERMS (Updated to match Pine Script exactly)
    pos_current_global = np.where(ctxRng > 0, 
                                 np.power(2 * (curr_close - (ctxHi + ctxLo) / 2) / ctxRng, 2), 
                                 0)
    pos_current_local = np.power((curr_close - curr_low) / curr_range, 2)
    
    # New: Previous bar positional term
    centered_prev_pos = np.where(prev_range > 0, 
                                (curr_close - (prev_high + prev_low) / 2) / prev_range, 
                                0)
    pos_previous_local = 1 + 0.5 * np.sqrt(np.abs(centered_prev_pos)) * np.sign(centered_prev_pos)
    
    # ❹ FINAL SCORE (Updated formula)
    score = range_factor * pos_current_global * pos_current_local * pos_previous_local
    
    # WMA CALCULATIONS FOR MOMENTUM
    wma_fast = wma(pd.Series(score, index=df.index), len_fast)
    wma_mid = wma(pd.Series(score, index=df.index), len_mid)
    wma_slow = wma(pd.Series(score, index=df.index), len_slow)
    
    # Momentum Breakout Logic
    is_orange = curr_close > prev_close
    above_wma7_momentum = score > wma_fast
    above_wma13_momentum = score > wma_mid
    above_wma21_momentum = pd.Series(score > wma_slow).fillna(True)
    
    above_all_wmas_momentum = above_wma7_momentum & above_wma13_momentum & above_wma21_momentum
    momentum_breakout = is_orange & above_all_wmas_momentum
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # CONFLUENCE SIGNAL
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    confluence = high_volume & spread_breakout & momentum_breakout
    
    # Check the specified bar
    idx = check_bar
    if idx < 0:
        idx = len(df) + idx  # Convert negative index to positive
    if not 0 <= idx < len(df):
        return False, {}
    
    if not confluence.iloc[idx]:
        return False, {}
    
    # Calculate additional metrics for the detected bar
    bar_idx = df.index[idx]
    volume_mean = curr_volume.rolling(7).mean().iloc[idx]
    volume_ratio = curr_volume.iloc[idx] / volume_mean if volume_mean > 0 else 0
    volume_usd = curr_volume.iloc[idx] * curr_close.iloc[idx]
    bar_range = curr_range.iloc[idx]
    close_off_low = (curr_close.iloc[idx] - curr_low.iloc[idx]) / bar_range * 100 if bar_range > 0 else 0
    
    # Component analysis for detailed results
    high_vol_component = high_volume.iloc[idx]
    spread_component = spread_breakout.iloc[idx]
    momentum_component = momentum_breakout.iloc[idx]
    extreme_volume_component = bool(extreme_volume.iloc[idx]) if hasattr(extreme_volume.iloc[idx], '__bool__') else extreme_volume.iloc[idx]
    extreme_spread_component = bool(extreme_spread.iloc[idx]) if hasattr(extreme_spread.iloc[idx], '__bool__') else extreme_spread.iloc[idx]
    
    # Fix momentum score extraction to avoid FutureWarning
    if isinstance(score, pd.Series):
        momentum_score_value = score.iloc[idx]
    elif hasattr(score, '__len__'):
        momentum_score_value = score[idx]
    else:
        momentum_score_value = float(score)
    
    result = {
        'timestamp': bar_idx,
        'close_price': curr_close.iloc[idx],
        'volume': curr_volume.iloc[idx],
        'volume_usd': volume_usd,
        'volume_ratio': volume_ratio,
        'close_off_low': close_off_low,
        'bar_range': bar_range,
        'momentum_score': momentum_score_value,
        'high_volume': high_vol_component,
        'spread_breakout': spread_component,
        'momentum_breakout': momentum_component,
        'extreme_volume': extreme_volume_component,
        'extreme_spread': extreme_spread_component,
        'current_bar': check_bar == -1,
        'date': bar_idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(bar_idx, 'strftime') else str(bar_idx)
    }
    
    return True, result