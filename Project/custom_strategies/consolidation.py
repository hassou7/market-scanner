# custom_strategies/consolidation.py

# min df number = 23

import pandas as pd
import numpy as np

def detect_consolidation(
    df: pd.DataFrame,
    check_bar: int = -1,
) -> tuple[bool, dict]:
    """
    Detect consolidation pattern based on specified criteria.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    N = 7
    min_bars_inside = 4
    max_height_pct = 35.0
    use_atr_filter = True
    atr_len = 14
    atr_sma = 7
    atr_k = 0.9
    dedupe_eps = 0.01

    if df is None or len(df) < max(N, atr_len + atr_sma) + 2:
        return False, {}

    d = df.copy()
    for col in ("open","high","low","close"):
        d[col] = d[col].astype(float)

    h, l, c = d["high"].values, d["low"].values, d["close"].values
    idx = d.index
    n = len(d)

    range_high = np.full(n, np.nan); range_low = np.full(n, np.nan)
    height_pct = np.full(n, np.nan)
    for i in range(n):
        if i >= N-1:
            lo_i = i - (N-1)
            rh = np.max(h[lo_i:i+1]); rl = np.min(l[lo_i:i+1])
            range_high[i] = rh; range_low[i] = rl
            denom = rh + rl
            height_pct[i] = np.nan if denom == 0 else 200.0 * (rh - rl) / denom

    inside = np.zeros(n); bars_inside = np.full(n, np.nan)
    for i in range(n):
        rh, rl = range_high[i], range_low[i]
        if not np.isnan(rh) and not np.isnan(rl):
            inside[i] = 1.0 if (h[i] <= rh and l[i] >= rl) else 0.0
        if i >= N-1:
            lo_i = i - (N-1)
            bars_inside[i] = np.sum(inside[lo_i:i+1])

    pc = np.roll(c, 1); pc[0] = np.nan
    tr = np.nanmax(np.vstack([h-l, np.abs(h-pc), np.abs(l-pc)]), axis=0)
    atr = np.full(n, np.nan)
    if n >= atr_len:
        first = np.nanmean(tr[0:atr_len])
        atr[atr_len-1] = first
        alpha = 1.0 / atr_len
        for i in range(atr_len, n):
            atr[i] = atr[i-1] + alpha * (tr[i] - atr[i-1])
    atr_slow = pd.Series(atr, index=idx).rolling(atr_sma, min_periods=atr_sma).mean().values
    atr_ok = (~np.isnan(atr)) & (~np.isnan(atr_slow)) & (atr < atr_k * atr_slow) if use_atr_filter else np.ones(n, bool)

    cond_now = (bars_inside >= min_bars_inside) & (height_pct <= max_height_pct) & atr_ok
    cond_now = np.nan_to_num(cond_now, nan=False)
    cond_prev = np.roll(cond_now, 1); cond_prev[0] = False
    is_entry = cond_now & (~cond_prev)

    def similar_bounds(hi1, lo1, hi2, lo2):
        mid = (hi1 + lo1) / 2.0
        if mid == 0: return False
        return (abs(hi1 - hi2) / mid <= dedupe_eps) and (abs(lo1 - lo2) / mid <= dedupe_eps)

    active = []
    boxes = []

    in_box_any = np.zeros(n, dtype=bool)
    box_hi_newest = np.full(n, np.nan); box_lo_newest = np.full(n, np.nan)
    box_age_newest = np.zeros(n, dtype=int)
    entry_idx_new = np.full(n, np.nan); left_idx_new = np.full(n, np.nan)

    for i in range(n):
        if is_entry[i]:
            hi, lo = range_high[i], range_low[i]
            if not np.isnan(hi) and not np.isnan(lo):
                if not any(similar_bounds(hi, lo, b["hi"], b["lo"]) for b in active):
                    left_idx_val = max(0, i - (N - 1))
                    initial_age = min(N, i - left_idx_val + 1)
                    bx = {
                        "start_idx": i, "start_ts": idx[i],
                        "left_idx": left_idx_val,
                        "left_ts": idx[left_idx_val],
                        "end_idx": None, "end_ts": None,
                        "hi": float(hi), "lo": float(lo),
                        "age": initial_age
                    }
                    active.append(bx)
                    boxes.append(bx)

        keep = []
        for bx in active:
            if (c[i] > bx["hi"]) or (c[i] < bx["lo"]):
                bx["end_idx"] = i; bx["end_ts"] = idx[i]
            else:
                if i > bx["start_idx"]:
                    bx["age"] = i - bx["left_idx"] + 1
                keep.append(bx)
        active = keep

        if active:
            newest = active[-1]
            in_box_any[i] = True
            box_hi_newest[i] = newest["hi"]; box_lo_newest[i] = newest["lo"]
            box_age_newest[i] = newest["age"]
            entry_idx_new[i] = newest["start_idx"]; left_idx_new[i] = newest["left_idx"]
        else:
            in_box_any[i] = False; box_age_newest[i] = 0
            entry_idx_new[i] = np.nan; left_idx_new[i] = np.nan

    i_check = check_bar if check_bar < 0 else int(check_bar)
    if i_check < 0: i_check = n + i_check
    if i_check < 0 or i_check >= n:
        return False, {"reason": "bad_check_bar"}

    if not in_box_any[i_check]:
        return False, {"reason": "not_in_box", "timestamp": idx[i_check]}

    ei = int(entry_idx_new[i_check]) if not np.isnan(entry_idx_new[i_check]) else None
    li = int(left_idx_new[i_check]) if not np.isnan(left_idx_new[i_check]) else None
    res = {
        "timestamp": idx[i_check],
        "date": idx[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "consolidation": True,
        "current_bar": (i_check == n-1),
        "window_size": int(N),
        "entry_idx": ei, "entry_ts": (idx[ei] if ei is not None else None),
        "left_idx": li, "left_ts": (idx[li] if li is not None else None),
        "box_age": int(box_age_newest[i_check]),
        "box_hi": float(box_hi_newest[i_check]),
        "box_lo": float(box_lo_newest[i_check]),
        "box_mid": float((box_hi_newest[i_check] + box_lo_newest[i_check]) / 2.0),
        "mature": True,
        "bars_inside": bars_inside[i_check],
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[i_check],
        "max_height_pct_req": max_height_pct,
        "atr_ok": atr_ok[i_check],
        "range_high": range_high[i_check],
        "range_low": range_low[i_check],
        "range_mid": (range_high[i_check] + range_low[i_check]) / 2.0 if not np.isnan(range_high[i_check]) else np.nan
    }
    return True, res