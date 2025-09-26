# trend_breakout.py — HBS‑aligned Heikin‑Ashi smoothing + pivot‑aware UpWeGo
# ---------------------------------------------------------------------------
# This version matches your HBS definitions for:
#   - habclose (AMA 2/2/30)
#   - habopen  (recursive)
#   - habhigh / hablow
#   - s_habhigh = avg( EMA(jsmooth(habhigh), 13), WMA(jsmooth(habhigh), 13) )
#   - s_hablow  = EMA(jsmooth(hablow), 13)
# and keeps:
#   - UpWeGo: pivot breakout above ph_range + 0.3*ATR7 with 2‑bar grace + pivot update awareness
#   - crossover: edge of breakout_condition (close > s_habhigh + 0.1*ATR7) on the checked bar
#   - 5 supporting conditions: ATR trend, UpWeGo, MA1>MA2, HA momentum, FlagUp
#
# Author: you, updated by assistant — 2025‑09‑17

from __future__ import annotations
import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# Tunables
# ──────────────────────────────────────────────────────────────────────────────
HA_MA_LENGTH: int = 13       # TV: HA_ma_length = 13
JS_SMOOTH: int = 13          # jsmooth Smooth
JS_POWER: int = 5            # jsmooth Pow
PIVOT_LBL: int = 2
PIVOT_LBR: int = 2

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _wma(s: pd.Series, length: int) -> pd.Series:
    """Weighted MA with weights 1..length (Pine ta.wma style)."""
    weights = np.arange(1, length + 1, dtype=float)
    return s.rolling(length, min_periods=1).apply(
        lambda x: np.dot(x, weights[-len(x):]) / weights[-len(x):].sum(),
        raw=True,
    )


def _atr_wilder(h: pd.Series, l: pd.Series, c: pd.Series, length: int = 7) -> pd.Series:
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()


def ama(series, period: int = 2, period_fast: int = 1, period_slow: int = 15, epsilon: float = 1e-10) -> pd.Series:
    """Kaufman's Adaptive Moving Average variant (as in your HBS)."""
    src = np.asarray(series, dtype=float)
    n = period + 1
    hh = pd.Series(src).rolling(window=n, min_periods=1).max().values
    ll = pd.Series(src).rolling(window=n, min_periods=1).min().values
    mltp = np.where((hh - ll) != 0, np.abs(2 * src - ll - hh) / (hh - ll + epsilon), 0.0)
    sc_fastest = 2 / (period_fast + 1)
    sc_slowest = 2 / (period_slow + 1)
    sc = (mltp * (sc_fastest - sc_slowest) + sc_slowest) ** 2
    sc = np.nan_to_num(sc, nan=0.0, posinf=0.0, neginf=0.0)
    out = np.zeros_like(src)
    out[:period] = src[:period]
    for i in range(period, len(src)):
        out[i] = out[i - 1] + sc[i] * (src[i] - out[i - 1])
    return pd.Series(out)


def jsmooth(src, smooth: int, power: int) -> pd.Series:
    """Jurik‑style smoother (as in your HBS jsmooth)."""
    s = np.asarray(src, dtype=float)
    beta = 0.45 * (smooth - 1) / (0.45 * (smooth - 1) + 2)
    alpha = beta ** power
    n = len(s)
    jma = np.zeros(n)
    e0 = np.zeros(n); e1 = np.zeros(n); e2 = np.zeros(n)
    e0[0] = s[0]; e1[0] = 0.0; e2[0] = 0.0; jma[0] = s[0]
    for i in range(1, n):
        e0[i] = (1 - alpha) * s[i] + alpha * e0[i - 1]
        e1[i] = (s[i] - e0[i]) * (1 - beta) + beta * e1[i - 1]
        e2[i] = (e0[i] - jma[i - 1]) * ((1 - alpha) ** 2) + (alpha ** 2) * e2[i - 1]
        jma[i] = jma[i - 1] + e2[i]
    return pd.Series(jma)


def _pivot_calc(osc: list[float], LBL: int = PIVOT_LBL, LBR: int = PIVOT_LBR, highlow: str = 'high') -> list[float]:
    """Robust swing‑pivot detector with LBR confirmation shift."""
    n = len(osc)
    piv = [np.nan] * n
    if n == 0:
        return piv
    for center in range(LBL + LBR, n):
        ref_index = center - LBR
        ref = osc[ref_index]
        left = ref_index - LBL
        right = ref_index + LBR
        if left < 0 or right >= n:
            continue
        is_pivot = True
        for j in range(left, right + 1):
            if j == ref_index:
                continue
            if highlow == 'high':
                if osc[j] >= ref:
                    is_pivot = False; break
            else:
                if osc[j] <= ref:
                    is_pivot = False; break
        if is_pivot:
            piv[ref_index] = ref
    return piv


def _bearish_top(data: pd.DataFrame, idx: int) -> bool:
    o = float(data['open'].iloc[idx]); h = float(data['high'].iloc[idx])
    l = float(data['low'].iloc[idx]);  c = float(data['close'].iloc[idx])
    high_wick = h - max(o, c)
    low_wick  = min(o, c) - l
    body_size = abs(o - c)
    highest_close_50 = data['close'].rolling(window=50, min_periods=1).max().iloc[idx]
    atr = data['atr_7'].iloc[idx]
    high_upper_wick = (high_wick >= 0.85 * body_size) and (high_wick > low_wick)
    bearish_candle  = high_upper_wick or (high_wick > (max(o, c) - l))
    return bearish_candle and (h > highest_close_50) and ((h - l) < atr) and (abs(h - highest_close_50) < atr)

# ──────────────────────────────────────────────────────────────────────────────
# Detector
# ──────────────────────────────────────────────────────────────────────────────

def detect_trend_breakout(
    df: pd.DataFrame,
    check_bar: int = -2,
    require_crossover: bool = True,
    require_all_conditions: bool = True,
    atr_trend_threshold: float = 0.01,
) -> tuple[bool, dict]:
    """Detect trend breakout at a specific bar (-2 for last closed).

    crossover := edge of breakout_condition = (close > s_habhigh + 0.1*ATR7).
    UpWeGo    := pivot breakout above ph_range + 0.3*ATR7 with 2‑bar grace & pivot update awareness.
    """
    if df is None or len(df) < 10:
        return False, {"error": "insufficient_data"}

    data = df.copy()

    # Resolve index (support negative, e.g., -2)
    idx = check_bar if check_bar >= 0 else len(data) + check_bar
    if idx < 2 or idx >= len(data):
        return False, {"error": f"check_bar_out_of_range: idx={idx}, len={len(data)}"}

    # ATR(7) Wilder True Range
    data['atr_7'] = _atr_wilder(data['high'], data['low'], data['close'], 7)

    # --- HBS‑aligned HA construction ---
    data['lac'] = (data['open'] + data['close'])/2 + (((data['close'] - data['open']) / (data['high'] - data['low'] + 1e-6)) * ((data['close'] - data['open']).abs()/2))
    data['habclose'] = ama(data['lac'].values, period=2, period_fast=1, period_slow=15).values

    habopen = np.zeros(len(data), dtype=float)
    habopen[0] = float((data['open'].iloc[0] + data['close'].iloc[0]) / 2.0)
    for i in range(1, len(data)):
        habopen[i] = (habopen[i - 1] + float(data['habclose'].iat[i - 1])) / 2.0
    data['habopen'] = habopen

    data['habhigh'] = pd.concat([data['high'], data['habopen'], data['habclose']], axis=1).max(axis=1)
    data['hablow']  = pd.concat([data['low'],  data['habopen'], data['habclose']], axis=1).min(axis=1)

    # jsmooth + MA mix
    data['jsmooth_habhigh'] = jsmooth(data['habhigh'].values, JS_SMOOTH, JS_POWER).values
    data['jsmooth_hablow']  = jsmooth(data['hablow'].values,  JS_SMOOTH, JS_POWER).values

    ema_high = _ema(pd.Series(data['jsmooth_habhigh'], index=data.index), span=HA_MA_LENGTH)
    wma_high = _wma(pd.Series(data['jsmooth_habhigh'], index=data.index), length=HA_MA_LENGTH)
    data['s_habhigh'] = (ema_high + wma_high) / 2
    data['s_hablow']  = _ema(pd.Series(data['jsmooth_hablow'],  index=data.index), span=HA_MA_LENGTH)

    # MA1/MA2 for stack & momentum
    data['MA1'] = _ema(pd.Series(data['habclose'], index=data.index), span=5)
    data['MA2'] = _ema(pd.Series(data['habopen'],  index=data.index), span=10)

    # Pivots (with LBR shift + ffill)
    ph = _pivot_calc(data['high'].astype(float).tolist(), PIVOT_LBL, PIVOT_LBR, 'high')
    pl = _pivot_calc(data['low'].astype(float).tolist(),  PIVOT_LBL, PIVOT_LBR, 'low')
    data['ph'] = pd.Series(ph, index=data.index).shift(PIVOT_LBR)
    data['pl'] = pd.Series(pl, index=data.index).shift(PIVOT_LBR)
    data['ph_range'] = data['ph'].ffill()
    data['pl_range'] = data['pl'].ffill()

    # Levels
    level_ph = data['ph_range'] + 0.3 * data['atr_7']           # UpWeGo level (pivot based)
    level_sh = data['s_habhigh'] + 0.1 * data['atr_7']          # breakout_condition level (crossover)

    # Booleans
    data['breakup'] = data['close'] >= level_ph
    bu1 = data['breakup'].shift(1).fillna(False)
    bu2 = data['breakup'].shift(2).fillna(False)
    pivot_updated = data['ph_range'].ne(data['ph_range'].shift(1)).fillna(False)
    fresh_cross_1 = data['breakup'] & ~bu1        # this bar
    fresh_cross_2 = bu1 & ~bu2                    # last bar
    data['upwego'] = data['breakup'] & (fresh_cross_1 | fresh_cross_2 | pivot_updated)

    breakout_condition = data['close'] > level_sh
    breakout_prev = breakout_condition.shift(1).fillna(False)
    is_crossover_series = breakout_condition & ~breakout_prev
    is_crossover = bool(is_crossover_series.iloc[idx])

    # ── Supporting conditions (5)
    atr_now = float(data['atr_7'].iloc[idx]); atr_prev = float(data['atr_7'].iloc[idx-1])
    atr_trend = (atr_now - atr_prev) >= (atr_trend_threshold * max(1e-12, atr_prev))
    upwego_val = bool(data['upwego'].iloc[idx])
    ma_bull    = bool(data['MA1'].iloc[idx] > data['MA2'].iloc[idx])
    ha_momentum= bool(data['habclose'].iloc[idx] > data['habopen'].iloc[idx])

    higher_high = bool(data['high'].iloc[idx] > data['high'].iloc[idx-1])
    close_upper_half = bool((data['high'].iloc[idx] - data['close'].iloc[idx]) < (data['close'].iloc[idx] - data['low'].iloc[idx]))
    flagup_candles = higher_high and close_upper_half and (not _bearish_top(data, idx))

    supporting = [atr_trend, upwego_val, ma_bull, ha_momentum, flagup_candles]
    conditions_met = int(sum(bool(x) for x in supporting))

    main_breakout = bool(data['breakup'].iloc[idx])

    ok = (conditions_met >= 5) if require_all_conditions else (conditions_met >= 4)
    if require_crossover:
        ok = ok and is_crossover

    result = {
        "timestamp": data.index[idx],
        "close": float(data['close'].iloc[idx]),
        "s_habhigh": float(data['s_habhigh'].iloc[idx]) if not pd.isna(data['s_habhigh'].iloc[idx]) else None,
        "s_hablow":  float(data['s_hablow'].iloc[idx])  if not pd.isna(data['s_hablow'].iloc[idx])  else None,
        "breakout_level": float(level_sh.iloc[idx]) if not pd.isna(level_sh.iloc[idx]) else None,
        "main_breakout": main_breakout,
        "is_crossover": is_crossover,
        "require_crossover": require_crossover,
        "conditions_met": conditions_met,
        "ma1": float(data['MA1'].iloc[idx]),
        "ma2": float(data['MA2'].iloc[idx]),
        "upwego": upwego_val,
        "atr_trend": atr_trend,
        "ha_momentum": ha_momentum,
        "flagup_candles": flagup_candles,
        "ph_range": float(data['ph_range'].iloc[idx]) if not pd.isna(data['ph_range'].iloc[idx]) else None,
        "supporting_conditions": supporting,
        # UpWeGo debug
        "upwego_debug": {
            "breakup_now": bool(data['breakup'].iloc[idx]),
            "breakup_prev1": bool(bu1.iloc[idx]),
            "breakup_prev2": bool(bu2.iloc[idx]),
            "pivot_updated": bool(pivot_updated.iloc[idx]),
            "level_ph": float(level_ph.iloc[idx]) if not pd.isna(level_ph.iloc[idx]) else None,
            "level_sh": float(level_sh.iloc[idx]) if not pd.isna(level_sh.iloc[idx]) else None,
            "breakout_condition": bool(breakout_condition.iloc[idx]),
            "is_crossover_series": bool(is_crossover_series.iloc[idx])
        },
    }

    if ok:
        return True, result

    result["reason"] = (
        "insufficient_supporting_conditions" if conditions_met < (5 if require_all_conditions else 4)
        else ("missing_crossover" if require_crossover and not is_crossover else "unknown")
    )
    return False, result
