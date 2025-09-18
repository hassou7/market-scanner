# custom_strategies/confluence.py

"""
Confluence Strategy - Custom Pattern Detection (Pine v5 aligned, bullish + bearish)

Detects confluence signals from Volume, Spread, and Momentum.
- Fixes '&' precedence errors
- Keeps all arrays as Series aligned to df.index
- Uses safe division to avoid NaNs/Inf from zero ranges
- Normalizes WMA/NaN handling across bull & bear
- Added volume breakout detection
- Added bullish confluence_breakout (as confluence_wakeup)
- Added only_wakeup parameter to detect only volume spread wakeup signals (bullish)
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average returning a Series aligned to input index."""
    s = pd.Series(series)
    if period is None or period <= 0:
        return s * np.nan
    weights = np.arange(1, period + 1, dtype=float)
    return s.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def _safe_div(num: pd.Series, den: pd.Series, fill: float = 0.0) -> pd.Series:
    out = num / den
    return out.replace([np.inf, -np.inf], np.nan).fillna(fill)

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def detect_confluence(
    df,
    doji_threshold: float = 5.0,
    ctx_len: int = 7,
    range_floor: float = 0.10,
    len_fast: int = 7,
    len_mid: int = 13,
    len_slow: int = 21,
    check_bar: int = -1,
    is_bullish: bool = True,
    only_wakeup: bool = False
):
    """
    Detect confluence signals based on Volume, Spread, and Momentum analysis.
    If only_wakeup is True, detects only bullish confluence_wakeup signals.
    Returns: (detected: bool, result: dict)
    """

    # Basic guards & normalization
    if df is None:
        return False, {}

    df = pd.DataFrame(df).copy()
    required_cols = ["open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan

    # Need enough bars for context & WMA(21)
    min_bars = max(len_slow, ctx_len, 21) + 2
    if len(df) < min_bars:
        return False, {}

    # Shorthand series (keep as Series)
    o = df["open"]
    h = df["high"]
    l = df["low"]
    c = df["close"]
    v = df["volume"]

    pc = c.shift(1)
    ph = h.shift(1)
    pl = l.shift(1)

    rng = h - l
    prng = ph - pl

    # ── VOLUME / VSA ───────────────────────────────────────────────────────────
    close_change_pct = _safe_div((c - pc).abs(), pd.concat([c, pc], axis=1).max(axis=1), 0.0) * 100.0
    is_doji_like = close_change_pct <= float(doji_threshold)

    upper_shadow = h - c
    lower_shadow = c - l
    doji_up = lower_shadow > upper_shadow
    doji_down = upper_shadow > lower_shadow

    is_up_intention = c > pc
    is_down_intention = c < pc

    close_progress     = c - pc
    potential_progress = h - pc
    normal_up = (close_progress >= 0.5 * potential_progress) & is_up_intention

    close_decline      = pc - c
    potential_decline  = pc - l
    normal_down = (close_decline >= 0.5 * potential_decline) & is_down_intention

    up_bar_vsa = pd.Series(
        np.where(is_doji_like, doji_up, normal_up),
        index=df.index, dtype=bool
    )
    down_bar_vsa = pd.Series(
        np.where(
            is_doji_like, doji_down,
            np.where(is_up_intention, ~normal_up,
                     np.where(is_down_intention, normal_down, False))
        ),
        index=df.index, dtype=bool
    )

    vol_sma7  = v.rolling(7).mean()
    vol_sma13 = v.rolling(13).mean()
    vol_sma21 = v.rolling(21).mean()
    vol_std21 = v.rolling(21).std()
    vol_stdv7 = v.rolling(7).std()

    # Volume WMAs for breakout detection
    vol_wma7  = wma(v, 7)
    vol_wma13 = wma(v, 13)
    vol_wma21 = wma(v, 21)

    # Volume breakout: above all WMAs + highest in last 7 bars
    above_all_vol_wmas = (v > vol_wma7) & (v > vol_wma13) & (v > vol_wma21)
    highest_vol_7bars = (v == v.rolling(7).max())
    volume_breakout_wma = above_all_vol_wmas & highest_vol_7bars

    # Vol exceed count for SMA-based breakout
    vol_exceed_count = (
        (v > vol_sma7).astype(int) +
        (v > vol_sma13).astype(int) +
        (v > vol_sma21).astype(int)
    )
    vol_exceed_all = vol_exceed_count >= 3
    extreme_volume = v > (vol_sma7 + 3.0 * vol_stdv7)
    volume_breakout_sma = highest_vol_7bars & vol_exceed_all & ~extreme_volume

    local_rel_high = pd.Series(False, index=df.index)
    broad_rel_high = pd.Series(False, index=df.index)
    serious_volume = pd.Series(False, index=df.index)

    for i in range(1, len(df)):
        # local relative vs same-direction previous bar
        if up_bar_vsa.iloc[i]:
            prev_up_vol = v.iloc[i-1] if up_bar_vsa.iloc[i-1] else 0
            local_rel_high.iloc[i] = v.iloc[i] > prev_up_vol
        elif down_bar_vsa.iloc[i]:
            prev_dn_vol = v.iloc[i-1] if down_bar_vsa.iloc[i-1] else 0
            local_rel_high.iloc[i] = v.iloc[i] > prev_dn_vol

        # 3-bar recent same-direction average
        if i >= 3:
            if up_bar_vsa.iloc[i]:
                recent = [v.iloc[j] for j in range(max(0, i-3), i) if up_bar_vsa.iloc[j]]
                if recent:
                    broad_rel_high.iloc[i] = v.iloc[i] > np.mean(recent)
            elif down_bar_vsa.iloc[i]:
                recent = [v.iloc[j] for j in range(max(0, i-3), i) if down_bar_vsa.iloc[j]]
                if recent:
                    broad_rel_high.iloc[i] = v.iloc[i] > np.mean(recent)

            # serious vol: current vs last opposite-direction bar
            if broad_rel_high.iloc[i]:
                if up_bar_vsa.iloc[i]:
                    for j in range(i-1, -1, -1):
                        if down_bar_vsa.iloc[j]:
                            serious_volume.iloc[i] = v.iloc[i] > v.iloc[j]
                            break
                else:
                    for j in range(i-1, -1, -1):
                        if up_bar_vsa.iloc[j]:
                            serious_volume.iloc[i] = v.iloc[i] > v.iloc[j]
                            break

    absolute_high_vol = (v > vol_sma7) & (v > vol_sma13) & (v > vol_sma21)
    high_volume = (serious_volume | absolute_high_vol | broad_rel_high | local_rel_high)  # optionally & ~extreme_volume

    # ── SPREAD ─────────────────────────────────────────────────────────────────
    tol = 0.95
    wma7_spread  = wma(rng, 7)
    wma13_spread = wma(rng, 13)
    wma21_spread = wma(rng, 21)

    above_wma7_spread  = (rng > tol * wma7_spread).fillna(True)
    above_wma13_spread = (rng > tol * wma13_spread).fillna(True)
    above_wma21_spread = (rng > tol * wma21_spread).fillna(True)
    above_all_wmas_spread = (above_wma7_spread & above_wma13_spread & above_wma21_spread)

    close_pos_bull = _safe_div((c - l), rng, 0.0)
    bull_spread_wakeup = (close_pos_bull > 0.7) & above_all_wmas_spread
    bull_spread_breakout = bull_spread_wakeup & (rng == rng.rolling(3).max())

    close_pos_bear = _safe_div((h - c), rng, 0.0)
    bear_spread_wakeup = (close_pos_bear > 0.7) & above_all_wmas_spread
    bear_spread_breakout = bear_spread_wakeup & (rng == rng.rolling(3).max())

    spread_sma13 = rng.rolling(13).mean()
    spread_std13 = rng.rolling(13).std()
    extreme_spread = rng > (spread_sma13 + 3.0 * spread_std13)

    # Range breakout for confluence_wakeup (bullish)
    range_breakout = (rng == rng.rolling(7).max()) & above_all_wmas_spread & ~extreme_spread & (close_pos_bull > 0.3)

    # ── MOMENTUM ───────────────────────────────────────────────────────────────
    # Context range anchored from the highest-range bar in the last ctx_len bars
    ctxHi = pd.Series(np.nan, index=df.index, dtype=float)
    ctxLo = pd.Series(np.nan, index=df.index, dtype=float)
    ctxRng = pd.Series(np.nan, index=df.index, dtype=float)

    for idx in range(ctx_len, len(df)):
        highest_range = 0.0
        highest_range_idx = 0
        for i in range(1, ctx_len + 1):
            rv = rng.iloc[idx - i]
            if rv > highest_range:
                highest_range = rv
                highest_range_idx = i

        ctx_hi = ph.iloc[idx - ctx_len: idx].max()
        ctx_lo = pl.iloc[idx - ctx_len: idx].min()

        if 0 < highest_range_idx <= ctx_len:
            start = max(0, idx - ctx_len + highest_range_idx - 1)
            ctx_hi = h.iloc[start: idx + 1].max()
            ctx_lo = l.iloc[start: idx + 1].min()

        ctxHi.iloc[idx] = ctx_hi
        ctxLo.iloc[idx] = ctx_lo
        ctxRng.iloc[idx] = ctx_hi - ctx_lo

    # Range factor (floored)
    range_factor = pd.Series(
        np.where(ctxRng > 0, np.maximum(_safe_div(rng, ctxRng, 0.0), float(range_floor)), float(range_floor)),
        index=df.index
    )

    # Positional terms (bull)
    pos_current_global = pd.Series(
        np.where(ctxRng > 0,
                 np.power(_safe_div(2 * (c - (ctxHi + ctxLo) / 2.0), ctxRng, 0.0), 2),
                 0.0),
        index=df.index
    )
    pos_current_local = np.power(_safe_div((c - l), rng, 0.0), 2)

    centered_prev_pos = pd.Series(
        np.where(prng > 0, _safe_div((c - (ph + pl) / 2.0), prng, 0.0), 0.0),
        index=df.index
    )
    pos_previous_local = 1 + 0.5 * np.sqrt(np.abs(centered_prev_pos)) * np.sign(centered_prev_pos)

    score = (range_factor * pos_current_global * pos_current_local * pos_previous_local).astype(float)

    # WMAs for momentum (bull)
    wma_fast = wma(score, len_fast)
    wma_mid  = wma(score, len_mid)
    wma_slow = wma(score, len_slow)

    # Normalize NaN policy: missing WMA counts as pass (like Pine warmup)
    above_wma7_mom  = (score > wma_fast) | wma_fast.isna()
    above_wma13_mom = (score > wma_mid)  | wma_mid.isna()
    above_wma21_mom = (score > wma_slow) | wma_slow.isna()
    above_all_wmas_momentum = (above_wma7_mom & above_wma13_mom & above_wma21_mom).fillna(False)

    is_orange = c > pc
    momentum_breakout = is_orange & above_all_wmas_momentum

    # Mirror for bear
    bear_pos_current_local = np.power(_safe_div((h - c), rng, 0.0), 2)
    bear_pos_previous_local = 1 - 0.5 * np.sqrt(np.abs(centered_prev_pos)) * np.sign(centered_prev_pos)
    bear_score = (range_factor * pos_current_global * bear_pos_current_local * bear_pos_previous_local).astype(float)

    bear_wma_fast = wma(bear_score, len_fast)
    bear_wma_mid  = wma(bear_score, len_mid)
    bear_wma_slow = wma(bear_score, len_slow)

    bear_above_fast = (bear_score > bear_wma_fast) | bear_wma_fast.isna()
    bear_above_mid  = (bear_score > bear_wma_mid)  | bear_wma_mid.isna()
    bear_above_slow = (bear_score > bear_wma_slow) | bear_wma_slow.isna()
    bear_above_all  = (bear_above_fast & bear_above_mid & bear_above_slow).fillna(False)

    is_red = c < pc
    bear_momentum_breakout = is_red & bear_above_all

    # ── CONFLUENCE ─────────────────────────────────────────────────────────────
    bull_confluence = (high_volume & bull_spread_breakout & momentum_breakout).fillna(False)
    bear_confluence = (high_volume & bear_spread_breakout & bear_momentum_breakout).fillna(False)

    confluence = bull_confluence if is_bullish else bear_confluence
    spread_breakout_sel = bull_spread_breakout if is_bullish else bear_spread_breakout
    momentum_breakout_sel = momentum_breakout if is_bullish else bear_momentum_breakout
    score_sel = score if is_bullish else bear_score
    direction_base = "Up" if is_bullish else "Down"

    # Bullish confluence_wakeup (breakout)
    prev_range_breakout = range_breakout.shift(1).fillna(False)
    is_confluence_wakeup = (c > pc) & volume_breakout_sma & range_breakout & ~prev_range_breakout

    # Resolve check_bar
    idx = check_bar if check_bar >= 0 else (len(df) + check_bar)
    if not (0 <= idx < len(df)):
        return False, {}

    # Determine detected based on only_wakeup
    if only_wakeup:
        if not is_bullish:
            return False, {"reason": "only_wakeup requires is_bullish=True"}
        detected = bool(is_confluence_wakeup.iloc[idx])
        direction = "Up Wakeup"
        is_engulfing_reversal = False  # Skip engulfing for wakeup
    else:
        detected = bool(confluence.iloc[idx])
        # Check for engulfing reversal
        is_engulfing_reversal = False
        if idx > 0:
            if is_bullish:
                is_engulfing_reversal = bool(bear_confluence.iloc[idx-1]) and bool(bull_confluence.iloc[idx])
            else:
                is_engulfing_reversal = bool(bull_confluence.iloc[idx-1]) and bool(bear_confluence.iloc[idx])
        direction = f"{direction_base} Reversal" if is_engulfing_reversal else direction_base

    # Metrics snapshot
    vol_mean7 = vol_sma7.iloc[idx]
    volume_ratio = (v.iloc[idx] / vol_mean7) if (pd.notna(vol_mean7) and vol_mean7) else 0.0
    volume_usd = v.iloc[idx] * c.iloc[idx]
    bar_range = rng.iloc[idx]

    if is_bullish:
        close_off_low = _safe_div(pd.Series([c.iloc[idx] - l.iloc[idx]]), pd.Series([bar_range if pd.notna(bar_range) else np.nan]), 0.0).iloc[0] * 100.0
    else:
        close_off_low = _safe_div(pd.Series([h.iloc[idx] - c.iloc[idx]]), pd.Series([bar_range if pd.notna(bar_range) else np.nan]), 0.0).iloc[0] * 100.0

    momentum_score_value = float(score_sel.iloc[idx])

    result = {
        "timestamp": df.index[idx],
        "date": df.index[idx].strftime("%Y-%m-%d %H:%M:%S") if hasattr(df.index[idx], "strftime") else str(df.index[idx]),
        "direction": direction,
        "current_bar": (check_bar == -1),
        "only_wakeup": only_wakeup,

        "close_price": float(c.iloc[idx]),
        "volume": float(v.iloc[idx]),
        "volume_usd": float(volume_usd) if pd.notna(volume_usd) else 0.0,
        "volume_ratio": float(volume_ratio),
        "bar_range": float(bar_range) if pd.notna(bar_range) else 0.0,
        "close_off_low": float(close_off_low),

        "momentum_score": momentum_score_value,
        "high_volume": bool(high_volume.iloc[idx]) if pd.notna(high_volume.iloc[idx]) else False,
        "volume_breakout": bool(volume_breakout_wma.iloc[idx]) if pd.notna(volume_breakout_wma.iloc[idx]) else False,
        "spread_breakout": bool(spread_breakout_sel.iloc[idx]) if pd.notna(spread_breakout_sel.iloc[idx]) else False,
        "momentum_breakout": bool(momentum_breakout_sel.iloc[idx]) if pd.notna(momentum_breakout_sel.iloc[idx]) else False,
        "extreme_volume": bool(extreme_volume.iloc[idx]) if pd.notna(extreme_volume.iloc[idx]) else False,
        "extreme_spread": bool(extreme_spread.iloc[idx]) if pd.notna(extreme_spread.iloc[idx]) else False,

        "is_confluence_wakeup": bool(is_confluence_wakeup.iloc[idx]) if pd.notna(is_confluence_wakeup.iloc[idx]) else False,
        "is_engulfing_reversal": is_engulfing_reversal,
    }

    if not detected:
        result["reason"] = "not_confluence" if not only_wakeup else "not_wakeup"

    return detected, result