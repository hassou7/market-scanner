# hbs_indicator_vX-b.py
# 19.08.2025

import numpy as np
import pandas as pd
import pandas_ta as ta

# -------------------------------
# Global Parameters
# -------------------------------
Pow = 5
Smooth = 13
HA_ma_length = 15
wick_threshold = 0.85
atr_trend_threshold = 0.01

# Confluence parameters
doji_threshold = 5.0
ctx_len = 7
range_floor = 0.10
len_fast = 7
len_mid = 13
len_slow = 21

# Show flags (mimicking Pine Script inputs)
showConfluence = True
showPinUp = True

# -------------------------------
# Helper Functions
# -------------------------------
def wma(series, period):
    """Calculate Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def isInTopPercent(series, lookback, percent):
    """Check if current value is in top percentage of lookback period"""
    return series.rolling(lookback).apply(lambda x: (x <= x[-1]).sum() / len(x) * 100 >= percent, raw=True)

def ama(series, period=2, period_fast=2, period_slow=30, epsilon=1e-10):
    n = period + 1
    src = np.asarray(series)
    hh = pd.Series(src).rolling(window=n, min_periods=1).max().values
    ll = pd.Series(src).rolling(window=n, min_periods=1).min().values
    mltp = np.where((hh - ll) != 0, np.abs(2 * src - ll - hh) / (hh - ll + epsilon), 0)
    sc_fastest = 2 / (period_fast + 1)
    sc_slowest = 2 / (period_slow + 1)
    sc = (mltp * (sc_fastest - sc_slowest) + sc_slowest) ** 2
    sc = np.nan_to_num(sc, nan=0.0, posinf=0.0, neginf=0.0)
    ama_values = np.zeros_like(src)
    ama_values[:period] = src[:period]
    for i in range(period, len(src)):
        ama_values[i] = ama_values[i - 1] + sc[i] * (src[i] - ama_values[i - 1])
    return ama_values

def jsmooth(src, smooth, power):
    src = np.asarray(src)
    beta = 0.45 * (smooth - 1) / (0.45 * (smooth - 1) + 2)
    alpha = beta ** power
    length = len(src)
    jma = np.zeros(length)
    e0 = np.zeros(length)
    e1 = np.zeros(length)
    e2 = np.zeros(length)
    e0[0] = src[0]
    e1[0] = 0
    e2[0] = 0
    jma[0] = src[0]
    for i in range(1, length):
        e0[i] = (1 - alpha) * src[i] + alpha * e0[i - 1]
        e1[i] = (src[i] - e0[i]) * (1 - beta) + beta * e1[i - 1]
        e2[i] = (e0[i] - jma[i - 1]) * ((1 - alpha) ** 2) + (alpha ** 2) * e2[i - 1]
        jma[i] = jma[i - 1] + e2[i]
    return jma

def pivot(osc, LBL, LBR, highlow):
    pivots = [0.0] * len(osc)
    for i in range(LBL + LBR, len(osc)):
        ref = osc[i - LBR]
        is_pivot = True
        for j in range(1, LBL + 1):
            idx = i - LBR - j
            if idx < 0:
                continue
            if highlow.lower() == 'high':
                if osc[idx] >= ref:
                    is_pivot = False
                    break
            elif highlow.lower() == 'low':
                if osc[idx] <= ref:
                    is_pivot = False
                    break
        if is_pivot:
            for j in range(1, LBR + 1):
                idx = i - LBR + j
                if idx >= len(osc):
                    continue
                if highlow.lower() == 'high':
                    if osc[idx] >= ref:
                        is_pivot = False
                        break
                elif highlow.lower() == 'low':
                    if osc[idx] <= ref:
                        is_pivot = False
                        break
        if is_pivot:
            pivots[i - LBR] = ref
    return pivots

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
    # This ensures it's integers being compared later, not Timestamps
    return pd.Series(out, index=condition.index).astype(int)

def percentileRank(series, length):
    """
    Calculate percentile rank exactly as in Pine Script
    percentileRank(series, length) - compares current value (series[0]) with previous 'length' values
    """
    def calc_rank(window):
        if len(window) < length:
            return np.nan
        
        current_val = window.iloc[-1]  # series[0] in Pine Script (current bar)
        rank = 0.0
        
        # Loop through previous 'length' values (series[0] to series[length-1])
        for i in range(length):
            if i < len(window):
                if window.iloc[-(i+1)] <= current_val:  # series[i] <= series[0]
                    rank += 1.0
        
        return (rank / length) * 100
    
    return series.rolling(window=length, min_periods=length).apply(calc_rank, raw=False)
    
def percentile_rank_series(s):
    current = s.iloc[-1]
    rank = (s <= current).sum()
    return (rank / len(s)) * 100

def calculate_confluence(df):
    """
    Calculate confluence signal based on Volume, Spread, and Momentum analysis
    """
    # OHLCV Data
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
    absolute_high_vol = pd.Series(False, index=df.index)
    absolute_high_vol = np.where(vol_sma21.notna(), curr_volume > vol_sma21, False)
    
    # Extreme volume
    extreme_volume = pd.Series(False, index=df.index)
    extreme_volume = np.where(vol_sma21.notna() & vol_stdv21.notna(), 
                              (curr_volume > (vol_sma21 + 3.0 * vol_stdv21)) & ((curr_volume / vol_sma21) > 3),
                              False)
    
    # High volume definition
    high_volume = (serious_volume | absolute_high_vol | broader_relative_high_vol | local_relative_high_vol) & ~extreme_volume
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # SPREAD ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    spread = curr_range
    
    # Close position in bar
    closePosition = (curr_close - curr_low) / curr_range
    isCloseInUpperhigh = closePosition > 0.6
    
    # Weighted moving averages for spread
    wma7_spread = wma(spread, 7)
    wma13_spread = wma(spread, 13)
    wma21_spread = wma(spread, 21)
    
    # Spread Breakout Logic
    tol = 0.95
    
    # Compute the conditions without fillna
    above_wma7_spread = spread > (tol * wma7_spread)
    above_wma13_spread = spread > (tol * wma13_spread)
    above_wma21_spread = spread > (tol * wma21_spread)
    
    # For each bar, AND only if the WMA is not NaN (available)
    above_all_wmas_spread = pd.Series(True, index=df.index)
    above_all_wmas_spread = above_all_wmas_spread & np.where(wma7_spread.notna(), above_wma7_spread, True)
    above_all_wmas_spread = above_all_wmas_spread & np.where(wma13_spread.notna(), above_wma13_spread, True)
    above_all_wmas_spread = above_all_wmas_spread & np.where(wma21_spread.notna(), above_wma21_spread, True)
    
    # Also calculate below_all_wmas_spread similarly
    below_wma7_spread = spread <= (tol * wma7_spread)
    below_wma13_spread = spread <= (tol * wma13_spread)
    below_wma21_spread = spread <= (tol * wma21_spread)
    
    below_all_wmas_spread = pd.Series(True, index=df.index)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma7_spread.notna(), below_wma7_spread, True)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma13_spread.notna(), below_wma13_spread, True)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma21_spread.notna(), below_wma21_spread, True)
    
    spread_breakout = isCloseInUpperhigh & (spread == spread.rolling(3).max()) & above_all_wmas_spread
    
    # Compute extreme spread
    spread_sma21 = spread.rolling(21).mean()
    spread_stdv21 = spread.rolling(21).std()
    extreme_spread = pd.Series(False, index=df.index)
    extreme_spread = np.where(spread_sma21.notna() & spread_stdv21.notna(),
                              spread > (spread_sma21 + 2.0 * spread_stdv21),
                              False)
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # MOMENTUM ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # ❶ CONTEXT RANGE (last N bars)
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
    
    # ❷ RANGE COMPARISON FACTOR
    range_factor = np.where(ctxRng > 0, np.maximum(curr_range / ctxRng, range_floor), range_floor)
    
    # ❸ POSITIONAL TERMS
    pos_current_global = np.where(ctxRng > 0, 
                                 np.power(2 * (curr_close - (ctxHi + ctxLo) / 2) / ctxRng, 2), 
                                 0)
    pos_current_local = np.power((curr_close - curr_low) / curr_range, 2)
    pos_previous_local = np.power((curr_close - prev_low) / prev_range, 2)
    
    # ❹ FINAL SCORE
    score = range_factor * pos_current_global * pos_current_local
    
    # WMA CALCULATIONS FOR MOMENTUM
    wma_fast = wma(pd.Series(score, index=df.index), len_fast)
    wma_mid = wma(pd.Series(score, index=df.index), len_mid)
    wma_slow = wma(pd.Series(score, index=df.index), len_slow)
    
    # Momentum Breakout Logic
    is_orange = curr_close > prev_close
    above_wma7_momentum = score > wma_fast
    above_wma13_momentum = score > wma_mid
    above_wma21_momentum = score > wma_slow
    
    # Combine with availability check
    above_all_wmas_momentum = pd.Series(True, index=df.index)
    above_all_wmas_momentum = above_all_wmas_momentum & np.where(wma_fast.notna(), above_wma7_momentum, True)
    above_all_wmas_momentum = above_all_wmas_momentum & np.where(wma_mid.notna(), above_wma13_momentum, True)
    above_all_wmas_momentum = above_all_wmas_momentum & np.where(wma_slow.notna(), above_wma21_momentum, True)
    
    momentum_breakout = is_orange & above_all_wmas_momentum
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    # CONFLUENCE SIGNAL
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    confluence = high_volume & spread_breakout & momentum_breakout
    
    # Identify extreme confluence
    is_extreme = confluence & (extreme_volume | extreme_spread)
    
    # Confluence strength
    is_strong = closePosition > 0.7
    confluence_strength = np.where(confluence & is_strong, 'strong', np.where(confluence, 'weak', np.nan))
    
    return confluence, below_all_wmas_spread, high_volume, is_extreme, confluence_strength

def confirm_confluence(df):
    """
    Checks if current bar doesn't make a new 7-period low, then it must close above the last confirmed 2-period pivot high
    """
    # Check if current bar doesn't make a new 7-period low
    newMacroLow = df['low'] == df['low'].rolling(7).min()
    
    # Calculate 2-period pivot highs
    ph2 = pivot(df['high'].tolist(), 2, 2, 'high')
    ph2_series = pd.Series(ph2, index=df.index).shift(2)
    lastPivotHigh = ph2_series.ffill()
    
    # If not making new macro low, close must be above last pivot high
    confirm_confluence = np.where(~newMacroLow, df['close'] > lastPivotHigh, True)
    
    return pd.Series(confirm_confluence, index=df.index)

# -------------------------------
# get_signals – hbs_indicator_vX
# -------------------------------
def get_signals(df):
    error = ""
    if len(df.index) < (HA_ma_length + 1):
        error = f"Skipping - Insufficient data - ({len(df.index)})"
        return df, error

    # Ensure pending flag columns are boolean
    df['IsPendingBull'] = False
    df['IsPendingBear'] = False

    # ATRs
    df['atr']   = ta.atr(df['high'], df['low'], df['close'], 14)
    df['atr_3'] = ta.atr(df['high'], df['low'], df['close'], 3)
    df['atr_4'] = ta.atr(df['high'], df['low'], df['close'], 4)
    df['atr_7'] = ta.atr(df['high'], df['low'], df['close'], 7)

    # HA Candle Calculation
    df['lac'] = (df['open'] + df['close'])/2 + (((df['close'] - df['open'])/(df['high'] - df['low'] + 1e-6)) * np.abs((df['close'] - df['open'])/2))
    df['habclose'] = ama(df['lac'].values, period=2, period_fast=2, period_slow=30)
    habopen = np.zeros(len(df))
    habopen[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2.0
    for i in range(1, len(df)):
        habopen[i] = (habopen[i - 1] + df['habclose'].iloc[i - 1]) / 2.0
    df['habopen'] = habopen
    df['habhigh'] = df[['high', 'habopen']].join(pd.DataFrame(df['habclose'])).max(axis=1)
    df['hablow']  = df[['low', 'habopen']].join(pd.DataFrame(df['habclose'])).min(axis=1)
    df['lac_sym'] = (df['open'] + df['close'])/2 - (((df['close'] - df['open'])/(df['high'] - df['low'] + 1e-6)) * np.abs((df['close'] - df['open'])/2))

    # Smooth HA High/Low
    df['jsmooth_habhigh'] = jsmooth(df['habhigh'].values, Smooth, Pow)
    df['jsmooth_hablow']  = jsmooth(df['hablow'].values, Smooth, Pow)
    df['s_habhigh'] = (ta.ema(pd.Series(df['jsmooth_habhigh']), length=HA_ma_length) + ta.wma(pd.Series(df['jsmooth_habhigh']), length=HA_ma_length)) / 2
    df['s_hablow']  = ta.ema(pd.Series(df['jsmooth_hablow']), length=HA_ma_length)

    # Fast MA Crossover from JSmooth of HA close/open
    jsmooth_habclose = jsmooth(df['habclose'], Smooth, Pow)
    jsmooth_habopen  = jsmooth(df['habopen'], Smooth, Pow)
    df['MA1'] = ta.ema(pd.Series(jsmooth_habclose), length=1)
    df['MA2'] = ta.ema(pd.Series(jsmooth_habopen), length=1)
    bullishCross = (df['MA1'].shift(1) < df['MA2'].shift(1)) & (df['MA1'] > df['MA2'])
    bearishCross = (df['MA1'].shift(1) > df['MA2'].shift(1)) & (df['MA1'] < df['MA2'])
    bullishCross = bullishCross.fillna(False)
    bearishCross = bearishCross.fillna(False)

    # Swing Pivots & Breakouts
    LBL = 2; LBR = 2
    ph = pivot(df['high'].tolist(), LBL, LBR, 'high')
    pl = pivot(df['low'].tolist(), LBL, LBR, 'low')
    df['ph'] = pd.Series(ph, index=df.index).shift(LBR)
    df['pl'] = pd.Series(pl, index=df.index).shift(LBR)
    df['ph_range'] = df['ph'].ffill()
    df['pl_range'] = df['pl'].ffill()
    multiplier_val = 0.3
    df['breakup'] = df['close'] >= (df['ph_range'] + multiplier_val * df['atr']) #df['close'] >= (df['ph_range'])
    df['upwego'] = df['breakup'] & (df['breakup'] != df['breakup'].shift(1))
    df['breakdn'] = df['close'] <= (df['pl_range'])
    df['downwego'] = df['breakdn'] & (df['breakdn'] != df['breakdn'].shift(1))

    # Calculate Confluence and below_all_wmas_spread
    confluence, below_all_wmas_spread, high_volume, is_extreme, confluence_strength = calculate_confluence(df)
    
    # Calculate confirm_confluence
    confirm_confluence_signal = confirm_confluence(df)

    # At the Top / Bottom Conditions
    xh = 21
    highest_high_21 = df['high'].rolling(window=xh, min_periods=1).max()
    at_the_top = (df['high'] == highest_high_21) | (df['high'].shift(1) == highest_high_21) | (df['high'].shift(2) == highest_high_21)
    xl = 21
    lowest_low_21 = df['low'].rolling(window=xl, min_periods=1).min()
    at_the_bottom = (df['low'] == lowest_low_21) | (df['low'].shift(1) == lowest_low_21) | (df['low'].shift(2) == lowest_low_21)

    # Candle Calculations (moved up to be available for reversal bar logic)
    df['high_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['low_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['body_size'] = np.abs(df['open'] - df['close'])
    df['range_candle'] = df['high'] - df['low']
    insideBar = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    outsideBar = (df['high'] > df['high'].shift(1)) & (df['low'] < df['low'].shift(1)) #& ((df['close'] - df['low']) / (df['high']- df['low']))>0.65
    df['bear_power'] = df['high'] - df['close']
    df['bull_power'] = df['close'] - df['low']

    # ───────── REVERSAL BAR ─────────
    # VSA Fixed Parameters
    reversal_lookback = 14
    high_rank_threshold = 3
    v2_macro_short_lookback = 8
    v2_macro_medium_lookback = 28
    v2_macro_long_lookback = 48

    # Bar Type Calculations
    is_new_high_or_outside_bar = df['high'] > df['high'].shift(1)
    significant_high_breakout = (df['high'] - df['high'].shift(1)) > 0.1 * (df['high'].shift(1) - df['low'].shift(1))

    # Volume Analysis for Reversal Bar
    vol_sma21 = df['volume'].rolling(21).mean()
    vol_stdv21 = df['volume'].rolling(21).std()
    
    # Simple high volume check for reversal bar
    reversal_high_volume = df['volume'] > vol_sma21
    
    # Close position analysis
    bar_range = df['high'] - df['low']
    close_position = (df['close'] - df['low']) / bar_range
    is_in_lower_half = close_position < 0.5

    # Rank-Based Macro High Detection
    def get_high_rank(highs, lookback, threshold):
        """Get the threshold-ranked high from the lookback period"""
        result = pd.Series(index=highs.index, dtype=float)
        for i in range(lookback, len(highs)):
            window = highs.iloc[i-lookback:i]
            sorted_highs = window.sort_values(ascending=False)
            if len(sorted_highs) >= threshold:
                result.iloc[i] = sorted_highs.iloc[threshold-1]
            else:
                result.iloc[i] = sorted_highs.iloc[-1] if len(sorted_highs) > 0 else 0
        return result

    v2_high_rank_short = get_high_rank(df['high'], v2_macro_short_lookback, high_rank_threshold)
    v2_high_rank_medium = get_high_rank(df['high'], v2_macro_medium_lookback, high_rank_threshold)
    v2_high_rank_long = get_high_rank(df['high'], v2_macro_long_lookback, high_rank_threshold)

    is_macro_high = (df['high'] >= v2_high_rank_short) & (df['high'] >= v2_high_rank_medium) & (df['high'] >= v2_high_rank_long)

    # Reversal Bar Logic
    reversal_bar = (reversal_high_volume & 
                   is_in_lower_half & 
                   is_new_high_or_outside_bar & 
                   significant_high_breakout & 
                   is_macro_high & 
                   (~insideBar.shift(1).fillna(False)))

    # Reverse Trend Logic
    reverse_trend = reversal_bar.shift(1) & (df['close'] < df['low'].shift(1))

    # Continue with other candle calculations
    df['high_upper_wick'] = (df['high_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] > df['low_wick'])
    df['high_lower_wick'] = (df['low_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] < df['low_wick'])

    df['bearish_candle'] = df['high_upper_wick'] | (df['high_wick'] > (np.maximum(df['open'], df['close']) - df['low']))
    df['bullish_candle'] = df['high_lower_wick'] | (df['low_wick'] > (df['high'] - np.minimum(df['open'], df['close'])))

    highest_close_50 = df['close'].rolling(window=50, min_periods=1).max()
    highest_high_50 = df['high'].rolling(window=50, min_periods=1).max()
    # bearishtop = (df['bearish_candle'] & (df['high'] > highest_close_50) &
    #               ((df['high'] - df['close']) < df['atr_3']) &
    #               (np.abs(df['high'] - highest_high_50) < df['atr_3']) &
    #               (~insideBar) &
    #               ((df['high'] - df['close']) > (df['close'] - df['low'])))
    
    lowest_low_50 = df['low'].rolling(window=50, min_periods=1).min()
    bullishbottom = (df['bullish_candle'] & (df['low'] == lowest_low_50) & ((df['high'] - df['low']) < df['atr_7']))

    # df['bearish_top'] = bearishtop
    bearishtop = (df['bearish_candle'] & (df['high'] > highest_close_50) & ((df['high'] - df['low']) < df['atr_7']) & (abs(df['high'] - highest_close_50) < df['atr_3']) & ((~insideBar)))
    df['bullish_bottom'] = bullishbottom

    # Pin Signals
    pin_top = percentileRank(df['close'].shift(1), 4) > 80
    df['bearishtop_low'] = df['low'].where(bearishtop).ffill()
    pin_down = (df['close'] < df['bearishtop_low']) & (bars_since(bearishtop.fillna(False)) < 4) & (~outsideBar) & pin_top
    pin_down_cond = pin_down & (pin_down != pin_down.shift(1))

    df['bullishbottom_high'] = df['high'].where(bullishbottom).ffill()
    pin_up = (df['close'] > df['bullishbottom_high']) & (df['close'] > df['bullishbottom_high'].shift(1)) & (bars_since(bullishbottom.fillna(False)) < 4) & (~outsideBar)
    pin_up_cond = pin_up & (pin_up != pin_up.shift(1))

    barclosinginthehighs = ((df['high'] - df['close']) < (df['close'] - df['low'])) & (((df['close'] - df['low']) > 0.4 * (df['high'] - df['low']))) & (df['range_candle'] < df['range_candle'].rolling(window=50, min_periods=1).mean())

    atr_trend = df['atr'] > atr_trend_threshold * df['close']

    BullishEngulfing = (df['open'].shift(1) > df['close'].shift(1)) & (df['close'] > df['open']) & (df['close'] >= df['open'].shift(1)) & ((df['close'] - df['open']) > (df['open'].shift(1) - df['close'].shift(1)))
    df['BullishEngulfing'] = BullishEngulfing
    BearishEngulfing = (df['close'].shift(1) > df['open'].shift(1)) & (df['open'] > df['close']) & (df['open'] >= df['close'].shift(1)) & (df['open'].shift(1) >= df['close']) & ((df['open'] - df['close']) > (df['close'].shift(1) - df['open'].shift(1)))
    df['BearishEngulfing'] = BearishEngulfing

    sum_low_wick = df['low_wick'].shift(2) + df['low_wick'].shift(1) + df['low_wick']
    bullish_engulf_reversal = (sum_low_wick > df['atr_3']) & BullishEngulfing & (~outsideBar)
    bearish_engulf_reversal = (BearishEngulfing & (df['range_candle'] > 1.5 * df['range_candle'].shift(1)) & (df['high'].shift(1) == df['high'].rolling(window=21, min_periods=1).max())) | (outsideBar & at_the_top & (df['close'] < df['close'].shift(1)) & ((df['high'] - df['close']) > 0.25 * df['range_candle']))

    hl2 = (df['high'] + df['low']) / 2
    df['low_perc'] = df['low'].rolling(window=50, min_periods=1).apply(lambda s: percentile_rank_series(pd.Series(s)), raw=False)
    isBullishEngulfing_atlows = (BullishEngulfing &
                                 (df['high'] < df['high'].rolling(window=5, min_periods=1).max()) &
                                 (df['high'] > df['high'].shift(1)) &
                                 (df['high'] > df['high'].shift(2)) &
                                 (df['close'] > hl2.shift(2)) &
                                 (df['low'] < df['s_hablow']) &
                                 (pd.concat([df['MA1'], df['MA2']], axis=1).min(axis=1) > df['close']) &
                                 ((df['high_wick'] / (df['range_candle'] + 1e-6)) < 0.15) &
                                 (df['low_perc'] >= 30))

    barCount = np.arange(len(df))
    # Create boolean Series with proper index
    condition_flagUp_trend = pd.Series(
        np.where(barCount < HA_ma_length, True, df['close'] > df['s_habhigh'] + 0.1 * df['atr_7']),
        index=df.index
    ).astype(bool)
    
    # Convert the upwego series to boolean and handle NaN values
    upwego_bool = df['breakup'].fillna(False)
    
    # Create flagUp_trend condition with proper Series alignment
    flagUp_trend = (condition_flagUp_trend & 
                    atr_trend & 
                    upwego_bool & 
                    (df['MA1'] > df['MA2']) & 
                    (np.abs(df['habclose'].shift(1) - df['habopen'].shift(1)) < np.abs(df['habclose'] - df['habopen'])))

    # FlagUp candles condition
    flagUp_candles = (df['high'] > df['high'].shift(1)) & ((df['high'] - df['close']) < (df['close'] - df['low'])) & (~bearishtop) & (~df['BearishEngulfing'])

    # Create the specific flagUp conditions as per Pine Script
    # flagUp_conflunce = confluence and isInTopPercent(close, 5, 80) and confirm_confluence
    flagUp_confluence = confluence & isInTopPercent(df['close'], 5, 80) & confirm_confluence_signal #& ~is_extreme
    
    # flagUp_pin = pin_up_cond and isInTopPercent(close, 5, 80) and close > high[1] and not below_all_wmas_spread
    flagUp_pin = pin_up_cond & isInTopPercent(df['close'], 5, 80) & (df['close'] > df['high'].shift(1)) & (~below_all_wmas_spread)

    # Main flagUp logic - trend patterns with candle filter
    flagUp_main = (((flagUp_trend) | (bullish_engulf_reversal) |
                   (isBullishEngulfing_atlows)) & flagUp_candles)
    # flagUp_main = (((flagUp_trend) | (bullish_engulf_reversal) |
    #                (outsideBar & (df['close'] > df['open']) & (df['high'] < df['high'].rolling(window=21, min_periods=1).max()) & (df['close'] < df['close'].rolling(window=21, min_periods=1).max())) |
    #                (isBullishEngulfing_atlows)) & flagUp_candles)

    # Final flagUp logic as per Pine Script:
    # flagUp := flagUp and flagUp_candles or (showConfluence ? flagUp_conflunce : false) or (showPinUp ? flagUp_pin : false)
    flagUp = flagUp_main | (flagUp_confluence if showConfluence else False) | (flagUp_pin if showPinUp else False)

    # Properly calculate bars_since_bearish_cross as numeric Series with same index
    bearish_cross_numeric = bearishCross.fillna(False)
    bars_since_bearish_cross = pd.Series(
        np.array([0 if bearish_cross_numeric.iloc[max(0, i-5):i+1].any() else 6 
                  for i in range(len(df))]),
        index=df.index
    )
    
    # Create numeric condition_flagDn with proper index
    barCount = np.arange(len(df))
    condition_flagDn = np.where(barCount < HA_ma_length, True, (df['close'] < df['s_hablow']).values)
    condition_flagDn_series = pd.Series(condition_flagDn, index=df.index)
    
    # For safety, explicitly create Series for each condition with matching index
    ma_check = df['MA1'] < df['MA2']
    bars_check = bars_since_bearish_cross <= 5
    bullish_check = ~BullishEngulfing
    hammer_check = ~df.get('hammer', pd.Series(False, index=df.index))
    outside_check = ~outsideBar
    
    # Combine with proper Series alignment
    flagDn_trend = (condition_flagDn_series.astype(bool) & 
                   ma_check & 
                   bars_check & 
                   bullish_check & 
                   hammer_check & 
                   outside_check)

    reversal = at_the_top & ((np.abs(df['open'] - df['close']) / (df['range_candle'] + 1e-6)) > 0.6) & (df['low'] < df['low'].shift(2)) & (df['low'] < df['low'].shift(1)) & (~outsideBar) & ((df['bear_power']) > (df['bull_power']))

    # Reversal VSA Logic
    reversal_vsa = reversal_bar & confluence.shift(1).fillna(False)

    crossunder_condition = (df['close'].shift(1) >= df['s_hablow'].shift(1)) & (df['close'] < df['s_hablow'])
    stoploss = crossunder_condition & (df['close'] < df['open'].shift(1)) & (df['low'] != df['low'].rolling(window=50, min_periods=1).min())

    range_break = df['downwego'] & (df['range_candle'] > df['atr_4']) & ((df['close'] - df['high_wick']) < df['low'].shift(1)) & (df['low'] != df['low'].rolling(window=20, min_periods=1).min())

    # Add columns explicitly for confirmation_regime
    df['stoploss'] = stoploss
    df['range_break'] = range_break
    df['reversal'] = reversal
    df['reversal_bar'] = reversal_bar
    df['reversal_vsa'] = reversal_vsa
    df['reverse_trend'] = reverse_trend
    
    # Updated flagDown logic to include reversal_vsa and reverse_trend
    flagDown = (stoploss | pin_down_cond | range_break | reversal  | reverse_trend | 
               bearish_engulf_reversal | (outsideBar & at_the_top & 
               ((df['high'] - df['close']) > 0.25 * df['range_candle'])))

    # --- Prepare Output ---
    df['bearish_top'] = bearishtop
    df['bullish_bottom'] = bullishbottom

    df_datas = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df_datas['sma_50'] = df['close'].rolling(window=50, min_periods=50).mean()
    df_datas['sma_200'] = df['close'].rolling(window=200, min_periods=200).mean()
    df_datas['atr_7'] = df['atr_7']
    df_datas['hlc3'] = (df['high'] + df['low'] + df['close']) / 3

    df_datas['ha_close'] = df['habclose']
    df_datas['ha_open'] = df['habopen']
    df_datas['sm_ha_high'] = df['s_habhigh']
    df_datas['sm_ha_low'] = df['s_hablow']

    df_datas['flagUp'] = flagUp
    df_datas['flagDown'] = flagDown
    df_datas['trend_bull_signal'] = flagUp_trend
    df_datas['trend_bear_signal'] = flagDn_trend
    df_datas['pin_up_cond'] = pin_up_cond
    df_datas['pin_down_cond'] = pin_down_cond
    df_datas['bullish_engulf_reversal'] = bullish_engulf_reversal
    df_datas['bearish_engulf_reversal'] = bearish_engulf_reversal
    df_datas['isBullishEngulfing_atlows'] = isBullishEngulfing_atlows
    df_datas['confluence'] = confluence
    df_datas['outsideBar'] = outsideBar
    df_datas['at_the_top'] = at_the_top

    df_datas['bearish_top'] = df['bearish_top']
    df_datas['bullish_bottom'] = df['bullish_bottom']
    
    # Add these to df_datas for the confirmation_regime function
    df_datas['stoploss'] = stoploss
    df_datas['range_break'] = range_break
    df_datas['reversal'] = reversal
    df_datas['reversal_bar'] = reversal_bar
    df_datas['reversal_vsa'] = reversal_vsa
    df_datas['reverse_trend'] = reverse_trend

    df_datas['lac'] = df['lac']
    df_datas['lac_sym'] = df['lac_sym']

    return df_datas, error