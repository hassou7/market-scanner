# custom_strategies/pin_up.py

import pandas as pd
import numpy as np

def percentile_rank_series(s):
    """Calculate percentile rank of current value within series"""
    current = s.iloc[-1]
    rank = (s <= current).sum()
    return (rank / len(s)) * 100

def is_in_top_percent(series, lookback, percent):
    """Check if current value is in top percentage of lookback period"""
    return series.rolling(lookback).apply(lambda x: (x <= x[-1]).sum() / len(x) * 100 >= percent, raw=True)

def bars_since(condition):
    """Calculate bars since condition was last True"""
    out = np.full(len(condition), np.nan)
    last_true = -1
    
    for i in range(len(condition)):
        if condition.iloc[i]:
            last_true = i
            out[i] = 0
        else:
            out[i] = 0 if last_true == -1 else i - last_true
    
    return pd.Series(out, index=condition.index).astype(int)

def calculate_confluence_spread(df):
    """Calculate confluence spread analysis for below_all_wmas_spread"""
    curr_range = df['high'] - df['low']
    
    # Calculate weighted moving averages for spread analysis
    def wma(series, period):
        weights = np.arange(1, period + 1)
        return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    
    wma7_spread = wma(curr_range, 7)
    wma13_spread = wma(curr_range, 13)
    wma21_spread = wma(curr_range, 21)
    
    # Spread breakout logic
    tol = 0.95
    below_wma7_spread = curr_range <= (tol * wma7_spread)
    below_wma13_spread = curr_range <= (tol * wma13_spread)
    below_wma21_spread = curr_range <= (tol * wma21_spread)
    
    below_all_wmas_spread = pd.Series(True, index=df.index)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma7_spread.notna(), below_wma7_spread, True)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma13_spread.notna(), below_wma13_spread, True)
    below_all_wmas_spread = below_all_wmas_spread & np.where(wma21_spread.notna(), below_wma21_spread, True)
    
    return below_all_wmas_spread

def detect_pin_up(
    df: pd.DataFrame,
    check_bar: int = -1,
    wick_threshold: float = 0.85
) -> tuple[bool, dict]:
    """
    Detect Pin Up pattern - similar to pin_down but for bullish pin reversal.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        wick_threshold: Threshold for wick analysis
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    
    if df is None or len(df) < 55:  # Need enough data for calculations
        return False, {"reason": "insufficient_data"}

    d = df.copy()
    for col in ("open", "high", "low", "close"):
        d[col] = d[col].astype(float)

    # ATR calculation
    prev_close = d['close'].shift(1)
    tr = np.maximum(d['high'] - d['low'], 
                    np.maximum(np.abs(d['high'] - prev_close), 
                              np.abs(d['low'] - prev_close)))
    atr_7 = tr.rolling(7).mean()
    
    # Candle calculations
    high_wick = d['high'] - np.maximum(d['open'], d['close'])
    low_wick = np.minimum(d['open'], d['close']) - d['low']
    body_size = np.abs(d['open'] - d['close'])
    
    # Inside/Outside bar detection
    inside_bar = (d['high'] < d['high'].shift(1)) & (d['low'] > d['low'].shift(1))
    outside_bar = (d['high'] > d['high'].shift(1)) & (d['low'] < d['low'].shift(1))
    
    # Bullish candle detection (high lower wick)
    high_lower_wick = (low_wick >= wick_threshold * body_size) & (high_wick < low_wick)
    bullish_candle = high_lower_wick | (low_wick > (d['high'] - np.minimum(d['open'], d['close'])))
    
    # Bullish bottom detection
    lowest_low_50 = d['low'].rolling(50).min()
    bullish_bottom = (bullish_candle & 
                     (d['low'] == lowest_low_50) & 
                     ((d['high'] - d['low']) < atr_7))
    
    # Track bullish bottom high for pin up detection
    d['bullish_bottom_high'] = d['high'].where(bullish_bottom).ffill()
    
    # Pin up logic - price breaks above bullish bottom high within 4 bars
    pin_up = ((d['close'] > d['bullish_bottom_high']) & 
             (d['close'] > d['bullish_bottom_high'].shift(1)) & 
             (bars_since(bullish_bottom.fillna(False)) < 4) & 
             (~outside_bar))
    
    # Pin up condition - new occurrence (not continuation)
    pin_up_cond = pin_up & (pin_up != pin_up.shift(1))
    
    # Calculate spread conditions
    below_all_wmas_spread = calculate_confluence_spread(d)
    
    # FlagUp Pin Logic - similar to hbs_indicator flagUp_pin
    flagup_pin = (pin_up_cond & 
                 is_in_top_percent(d['close'], 5, 80) & 
                 (d['close'] > d['high'].shift(1)) & 
                 (~below_all_wmas_spread))
    
    # Check specified bar
    i_check = check_bar if check_bar >= 0 else len(d) + check_bar
    if i_check < 0 or i_check >= len(d):
        return False, {"reason": "bad_check_bar"}
    
    if not flagup_pin.iloc[i_check]:
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
    
    # Get bars since bullish bottom
    bars_since_bottom = bars_since(bullish_bottom.fillna(False)).iloc[i_check] if i_check < len(d) else 0
    
    # Calculate percentile rank
    close_percentile = is_in_top_percent(d['close'], 5, 80).iloc[i_check] if i_check < len(d) else False
    
    # Get bullish bottom info
    bullish_bottom_high = d['bullish_bottom_high'].iloc[i_check] if not pd.isna(d['bullish_bottom_high'].iloc[i_check]) else 0
    
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
        "bars_since_bullish_bottom": int(bars_since_bottom),
        "bullish_bottom_high": float(bullish_bottom_high),
        "close_above_prev_high": bool(d['close'].iloc[i_check] > d['high'].iloc[i_check-1]) if i_check > 0 else False,
        "in_top_percentile": bool(close_percentile),
        "spread_favorable": bool(~below_all_wmas_spread.iloc[i_check]),
        "direction": "Up",
        "color": "#3ACF3F"
    }
    
    return True, result