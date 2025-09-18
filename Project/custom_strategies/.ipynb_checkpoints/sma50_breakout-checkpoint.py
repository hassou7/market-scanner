# custom_strategies/sma50_breakout.py

"""
50SMA Breakout Strategy - Custom Pattern Detection

This strategy detects clean breakout signals with **priority** and **strength** rules:

TYPES (mutually exclusive, priority enforced):
1) "regular"       : Close > SMA50 AND Low < SMA50 (classic breakout)
2) "pre_breakout"  : Close > (SMA50 - ATR*mult) AND Low < SMA50, but NOT "regular"

CLEAN FILTER:
- The last N bars (default 7), excluding the checked bar, must NOT have closed above (SMA50 + ATR*mult).
  This avoids continuation/late entries and focuses on initial breakouts.

STRENGTH (only for "regular"):
- Compute SMA50 location inside the bar as: sma_loc = (SMA50 - Low) / (High - Low)  in [0..1]
- "Strong" if sma_loc < 0.35
- "Weak"   if sma_loc >= 0.35
- "pre_breakout" carries no strength (None)

PARAMS:
- sma_period: SMA length (default 50)
- atr_period: ATR length (default 7)
- atr_multiplier: multiplier for pre/upper thresholds (default 0.2)
- use_pre_breakout: whether to allow pre-breakout detection (default True)
- clean_lookback: bars to check for the clean filter (default 7)
- check_bar: which bar to evaluate (-1 current, -2 last closed, etc.)

RETURNS:
(bool, dict):
- bool        : True if a signal is detected on the specified bar, else False
- dict        : metrics payload (see bottom of function for keys)
"""

import pandas as pd
import numpy as np
from datetime import datetime


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (simple rolling mean)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(period, min_periods=period).mean()


def detect_sma50_breakout(
    df,
    sma_period: int = 50,
    atr_period: int = 7,
    atr_multiplier: float = 0.2,
    use_pre_breakout: bool = True,
    clean_lookback: int = 7,
    check_bar: int = -1,
):
    """
    Detect 50SMA breakout signals with priority (regular > pre_breakout) and strength rules.

    See module docstring for full behavior.
    """
    # Basic guards
    if df is None:
        return False, {}
    df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
    if len(df) < max(sma_period, atr_period, clean_lookback) + 2:
        return False, {}

    # Ensure required columns exist
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            df[col] = np.nan

    # ──────────────────────────────────────────────────────────────────────────
    # INDICATORS
    # ──────────────────────────────────────────────────────────────────────────
    sma50 = df["close"].rolling(sma_period, min_periods=sma_period).mean()
    atr_values = atr(df, atr_period)

    pre_breakout_threshold = sma50 - (atr_multiplier * atr_values)
    upper_breakout_threshold = sma50 + (atr_multiplier * atr_values)

    # ──────────────────────────────────────────────────────────────────────────
    # CLEAN FILTER
    # "No closes above (SMA50 + mult*ATR) in the last N bars (excluding current)"
    # Efficient vector form: check condition and use shifted rolling window.
    # above == 1 where prior bar closed above upper threshold
    above = (df["close"] > upper_breakout_threshold).astype("float32")
    # Shift by 1 to exclude current bar, then rolling sum over clean_lookback
    recent_above_sum = (
        above.shift(1)
        .rolling(clean_lookback, min_periods=1)
        .sum()
        .fillna(0)
    )
    clean_breakout_filter = (recent_above_sum == 0)

    # ──────────────────────────────────────────────────────────────────────────
    # BAR INDEX RESOLUTION
    # ──────────────────────────────────────────────────────────────────────────
    idx = len(df) + check_bar if check_bar < 0 else check_bar
    if not (0 <= idx < len(df)):
        return False, {}

    # If we don't have SMA/ATR computed at idx, exit early
    if pd.isna(sma50.iloc[idx]) or pd.isna(atr_values.iloc[idx]):
        return False, {}

    # ──────────────────────────────────────────────────────────────────────────
    # SIGNAL CONDITIONS (evaluate at idx only)
    # Priority: "regular" first; if false, then "pre_breakout" (if enabled)
    # ──────────────────────────────────────────────────────────────────────────
    is_clean = bool(clean_breakout_filter.iloc[idx])

    # Regular (classic) breakout
    high_i = df["high"].iloc[idx]
    low_i = df["low"].iloc[idx]
    close_i = df["close"].iloc[idx]
    sma_i = sma50.iloc[idx]
    pre_thr_i = pre_breakout_threshold.iloc[idx]

    regular_here = bool((close_i > sma_i) and (low_i < sma_i) and is_clean)

    pre_here = False
    if use_pre_breakout and not regular_here:
        pre_here = bool((close_i > pre_thr_i) and (low_i < sma_i) and is_clean)

    if regular_here:
        breakout_type = "regular"
    elif pre_here:
        breakout_type = "pre_breakout"
    else:
        return False, {}

    # ──────────────────────────────────────────────────────────────────────────
    # METRICS & STRENGTH
    # ──────────────────────────────────────────────────────────────────────────
    bar_range = max(float(high_i - low_i), 0.0)
    volume_i = float(df["volume"].iloc[idx]) if not pd.isna(df["volume"].iloc[idx]) else 0.0

    # Price vs SMA (pct) & low vs SMA (pct)
    price_vs_sma = ((close_i - sma_i) / sma_i * 100.0) if sma_i and not pd.isna(sma_i) else 0.0
    low_vs_sma = ((low_i - sma_i) / sma_i * 100.0) if sma_i and not pd.isna(sma_i) else 0.0

    # Volume analytics
    vol_mean_7 = df["volume"].rolling(7, min_periods=1).mean().iloc[idx]
    volume_ratio = (volume_i / vol_mean_7) if (vol_mean_7 and vol_mean_7 > 0) else 0.0
    volume_usd = volume_i * float(close_i) if not pd.isna(close_i) else 0.0

    # Bar characteristics
    close_off_low = ((close_i - low_i) / bar_range * 100.0) if bar_range > 0 else 0.0

    # Distances of previous bars from upper threshold (for diagnostics)
    last_n_bars_distance = []
    for lb in range(1, clean_lookback + 1):
        j = idx - lb
        if j >= 0 and not (pd.isna(df["close"].iloc[j]) or pd.isna(upper_breakout_threshold.iloc[j])):
            last_n_bars_distance.append(float(df["close"].iloc[j] - upper_breakout_threshold.iloc[j]))
        else:
            last_n_bars_distance.append(0.0)
    avg_last_n_distance = float(np.mean(last_n_bars_distance)) if last_n_bars_distance else 0.0

    current_atr = float(atr_values.iloc[idx]) if not pd.isna(atr_values.iloc[idx]) else 0.0
    upper_thr_i = float(upper_breakout_threshold.iloc[idx]) if not pd.isna(upper_breakout_threshold.iloc[idx]) else 0.0
    atr_threshold_distance = abs(float(close_i - pre_thr_i)) if not (pd.isna(close_i) or pd.isna(pre_thr_i)) else 0.0

    # Strength logic (only for "regular")
    if breakout_type == "regular":
        if bar_range > 0 and not pd.isna(sma_i):
            sma_loc = (sma_i - low_i) / bar_range  # 0..1 from low->high
            breakout_strength = "Strong" if sma_loc < 0.35 else "Weak"
        else:
            # Degenerate bar or missing values → default to "Weak"
            sma_loc = None
            breakout_strength = "Weak"
    else:
        sma_loc = None
        breakout_strength = None  # No strength for pre_breakout

    # Build result
    bar_idx = df.index[idx]
    result = {
        "timestamp": bar_idx,
        "close_price": float(close_i),
        "volume": volume_i,
        "volume_usd": float(volume_usd),
        "volume_ratio": float(volume_ratio),
        "close_off_low": float(close_off_low),
        "bar_range": float(bar_range),
        "sma50": float(sma_i),
        "atr": float(current_atr),
        "price_vs_sma_pct": float(price_vs_sma),
        "low_vs_sma_pct": float(low_vs_sma),
        "breakout_type": breakout_type,           # "regular" or "pre_breakout"
        "breakout_strength": breakout_strength,   # "Strong"/"Weak" or None (for pre_breakout)
        "pre_breakout_threshold": float(pre_thr_i) if not pd.isna(pre_thr_i) else 0.0,
        "upper_breakout_threshold": float(upper_thr_i),
        "atr_threshold_distance": float(atr_threshold_distance),
        "is_clean_breakout": bool(is_clean),
        "clean_lookback_period": int(clean_lookback),
        "avg_last_n_distance": float(avg_last_n_distance),
        "direction": "Up",                        # by definition of SMA50 breakout
        "current_bar": (check_bar == -1),
        "date": bar_idx.strftime("%Y-%m-%d %H:%M:%S") if hasattr(bar_idx, "strftime") else str(bar_idx),
        # Optional diagnostic (comment out if not needed downstream):
        # "sma_loc": None if sma_loc is None else float(sma_loc),
    }

    return True, result
