# custom_strategies/trend_breakout.py

import pandas as pd
import numpy as np
import pandas_ta as ta

def ama(series, period=2, period_fast=2, period_slow=30, epsilon=1e-10):
    """Calculate Adaptive Moving Average"""
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
    """Calculate JSmooth moving average"""
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
    """Calculate pivot points"""
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

def detect_trend_breakout(
    df: pd.DataFrame,
    check_bar: int = -1,
    smooth: int = 13,
    power: int = 5,
    ha_ma_length: int = 15,
    atr_trend_threshold: float = 0.01
) -> tuple[bool, dict]:
    """
    Detect Trend Breakout pattern - flagUp_trend logic from hbs_indicator.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        smooth: Smoothing parameter for JSmooth calculation
        power: Power parameter for JSmooth calculation
        ha_ma_length: Moving average length for HA calculations
        atr_trend_threshold: ATR trend threshold
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    
    if df is None or len(df) < max(55, ha_ma_length + 20):
        return False, {"reason": "insufficient_data"}

    d = df.copy()
    for col in ("open", "high", "low", "close"):
        d[col] = d[col].astype(float)

    # ATR calculations
    d['atr_7'] = ta.atr(d['high'], d['low'], d['close'], 7)
    
    # Heikin-Ashi calculations
    lac = (d['open'] + d['close'])/2 + (((d['close'] - d['open'])/(d['high'] - d['low'] + 1e-6)) * np.abs((d['close'] - d['open'])/2))
    habclose = ama(lac.values, period=2, period_fast=2, period_slow=30)
    
    habopen = np.zeros(len(d))
    habopen[0] = (d['open'].iloc[0] + d['close'].iloc[0]) / 2.0
    for i in range(1, len(d)):
        habopen[i] = (habopen[i - 1] + habclose[i - 1]) / 2.0
    
    habhigh = np.maximum(d['high'], np.maximum(habopen, habclose))
    hablow = np.minimum(d['low'], np.minimum(habopen, habclose))
    
    # Smooth HA calculations - FIX: Preserve index
    jsmooth_habhigh = jsmooth(habhigh, smooth, power)
    jsmooth_hablow = jsmooth(hablow, smooth, power)
    s_habhigh = (pd.Series(jsmooth_habhigh, index=d.index).ewm(span=ha_ma_length).mean() + 
                pd.Series(jsmooth_habhigh, index=d.index).rolling(ha_ma_length).apply(lambda x: np.average(x, weights=np.arange(1, len(x)+1)), raw=True)) / 2
    
    # Moving averages for trend detection - FIX: Preserve index
    jsmooth_habclose = jsmooth(habclose, smooth, power)
    jsmooth_habopen = jsmooth(habopen, smooth, power)
    ma1 = pd.Series(jsmooth_habclose, index=d.index).ewm(span=1).mean()
    ma2 = pd.Series(jsmooth_habopen, index=d.index).ewm(span=1).mean()
    
    # Swing Pivots & Breakouts
    LBL = 2; LBR = 2
    ph = pivot(d['high'].tolist(), LBL, LBR, 'high')
    d['ph'] = pd.Series(ph, index=d.index).shift(LBR)
    d['ph_range'] = d['ph'].ffill()
    
    multiplier_val = 0.3
    d['breakup'] = d['close'] >= (d['ph_range'] + multiplier_val * d['atr_7'])
    d['upwego'] = d['breakup'] & (d['breakup'] != d['breakup'].shift(1))
    
    # ATR trend condition
    atr_trend = d['atr_7'] > atr_trend_threshold * d['close']
    
    # FlagUp trend conditions
    barCount = np.arange(len(d))
    condition_flagUp_trend = pd.Series(
        np.where(barCount < ha_ma_length, True, d['close'] > s_habhigh + 0.1 * d['atr_7']),
        index=d.index
    ).astype(bool)
    
    upwego_bool = d['upwego'].fillna(False)
    
    # FIX: Ensure all Series have same index for comparison
    ma1_values = ma1.reindex(d.index, fill_value=0)
    ma2_values = ma2.reindex(d.index, fill_value=0)
    
    # Convert numpy arrays to Series with proper index for comparison
    habclose_series = pd.Series(habclose, index=d.index)
    habopen_series = pd.Series(habopen, index=d.index)
    
    flagUp_trend = (condition_flagUp_trend & 
                   atr_trend & 
                   upwego_bool & 
                   (ma1_values > ma2_values) & 
                   (np.abs(habclose_series - habopen_series) > np.abs(habclose_series.shift(1) - habopen_series.shift(1))))
    
    # Check specified bar
    i_check = check_bar if check_bar >= 0 else len(d) + check_bar
    if i_check < 0 or i_check >= len(d):
        return False, {"reason": "bad_check_bar"}
    
    if not flagUp_trend.iloc[i_check]:
        return False, {"reason": "not_detected", "timestamp": d.index[i_check]}
    
    # Calculate volume info
    volume_usd = d['volume'].iloc[i_check] * d['close'].iloc[i_check]
    volume_mean = d['volume'].rolling(7).mean().iloc[i_check]
    volume_ratio = d['volume'].iloc[i_check] / volume_mean if volume_mean > 0 else 0
    
    # Close position indicator
    bar_range = d['high'].iloc[i_check] - d['low'].iloc[i_check]
    close_position_pct = ((d['close'].iloc[i_check] - d['low'].iloc[i_check]) / bar_range * 100) if bar_range > 0 else 50.0
    
    if close_position_pct <= 30:
        close_indicator = "●○○"
    elif close_position_pct <= 70:
        close_indicator = "○●○"
    else:
        close_indicator = "○○●"
    
    # Additional metrics - FIX: Safe array access
    ha_momentum = habclose[i_check] - habopen[i_check] if i_check < len(habclose) else 0
    prev_ha_momentum = habclose[i_check-1] - habopen[i_check-1] if i_check > 0 and i_check-1 < len(habclose) else 0
    
    result = {
        "timestamp": d.index[i_check],
        "date": d.index[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "detected": True,
        "current_bar": (i_check == len(d) - 1),
        "close": float(d['close'].iloc[i_check]),
        "volume_usd": float(volume_usd),
        "volume_ratio": float(volume_ratio),
        "close_position_indicator": close_indicator,
        "close_position_pct": float(close_position_pct),
        "breakup_trigger": bool(d['upwego'].iloc[i_check]),
        "atr_trend_active": bool(atr_trend.iloc[i_check]),
        "above_ha_high": bool(condition_flagUp_trend.iloc[i_check]),
        "ma_bullish": bool(ma1_values.iloc[i_check] > ma2_values.iloc[i_check]),
        "ha_momentum": float(ha_momentum),
        "ha_momentum_increase": bool(abs(ha_momentum) > abs(prev_ha_momentum)),
        "pivot_high_break": float(d['close'].iloc[i_check] - d['ph_range'].iloc[i_check]) if not pd.isna(d['ph_range'].iloc[i_check]) else 0,
        "direction": "Up",
        "color": "#3ACF3F"
    }
    
    return True, result