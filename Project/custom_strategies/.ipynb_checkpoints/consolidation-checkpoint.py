# custom_strategies/consolidation.py

# min df number = 23

import pandas as pd
import numpy as np

def detect_consolidation(
    df: pd.DataFrame,
    check_bar: int = -1,
    use_log: bool = True
) -> tuple[bool, dict]:
    """
    Detect if the specified bar is inside an ongoing consolidation box and channel.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        use_log: Whether to use log scale for fit
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    N = 7
    min_bars_inside = 4
    pct_levels = [35.0, 25.0, 15.0]
    use_atr_filter = True  # Enabled to reduce false positives in high volatility periods
    atr_len = 14
    atr_sma = 7
    atr_k = 0.9
    dedupe_eps = 0.01
    max_abs_rel_slope = 0.005  # Max absolute relative slope per bar (0.5%) to consider as consolidation

    if df is None or len(df) < max(N, atr_len + atr_sma) + 2:
        return False, {"reason": "insufficient_data"}

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

    # Compute potential level for each bar (tightest possible)
    potential_level = np.full(n, -1)
    for i in range(n):
        if i >= N-1 and bars_inside[i] >= min_bars_inside and atr_ok[i]:
            lo_i = i - (N-1)
            box_closes = c[lo_i:i+1]
            box_length = len(box_closes)
            if box_length >= 2:
                if use_log:
                    box_closes_log = np.log(box_closes)
                else:
                    box_closes_log = box_closes

                # Theil-Sen fit to check slope
                slopes = []
                for j in range(box_length - 1):
                    for k in range(j + 1, box_length):
                        sl = (box_closes_log[k] - box_closes_log[j]) / (k - j)
                        slopes.append(sl)
                median_slope = np.median(slopes) if slopes else 0.0

                # Skip if slope too steep
                if abs(median_slope) > max_abs_rel_slope:
                    continue

            for lvl in range(len(pct_levels)-1, -1, -1):
                if height_pct[i] <= pct_levels[lvl]:
                    potential_level[i] = lvl
                    break

    cond_now = potential_level >= 0
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
    current_level_newest = np.full(n, -1)

    for i in range(n):
        if is_entry[i]:
            lvl = potential_level[i]
            hi, lo = range_high[i], range_low[i]
            if not np.isnan(hi) and not np.isnan(lo):
                if not any(similar_bounds(hi, lo, b["hi"], b["lo"]) for b in active):
                    left_idx_val = max(0, i - (N - 1))
                    initial_age = min(N, i - left_idx_val + 1)
                    bx_closes = list(c[left_idx_val:i+1])
                    bx = {
                        "start_idx": i, "start_ts": idx[i],
                        "left_idx": left_idx_val,
                        "left_ts": idx[left_idx_val],
                        "end_idx": None, "end_ts": None,
                        "hi": float(hi), "lo": float(lo),
                        "age": initial_age,
                        "level": lvl,
                        "closes": bx_closes  # List of closes inside box
                    }
                    active.append(bx)
                    boxes.append(bx)

        keep = []
        for bx in active:
            # Check for tightening if possible
            tighter_lvl = potential_level[i]
            if tighter_lvl > bx["level"] and i - bx["left_idx"] + 1 > N:
                # Tighten to recent N
                recent_hi = range_high[i]
                recent_lo = range_low[i]
                bx["hi"] = recent_hi
                bx["lo"] = recent_lo
                bx["left_idx"] = i - (N - 1)
                bx["left_ts"] = idx[bx["left_idx"]]
                bx["age"] = N
                bx["level"] = tighter_lvl
                bx["closes"] = list(c[bx["left_idx"]:i])  # Update closes to recent, exclude current since append later

            # Compute channel using closes up to i-1
            box_closes = np.array(bx["closes"])
            box_length = len(box_closes)
            channel_break = False
            channel_dir = 0
            median_slope = 0.0
            if box_length >= 2:
                if use_log:
                    box_closes_log = np.log(box_closes)
                else:
                    box_closes_log = box_closes

                # Theil-Sen fit
                slopes = []
                for j in range(box_length - 1):
                    for k in range(j + 1, box_length):
                        sl = (box_closes_log[k] - box_closes_log[j]) / (k - j)
                        slopes.append(sl)
                median_slope = np.median(slopes)

                intercepts = []
                for j in range(box_length):
                    inc = box_closes_log[j] - median_slope * j
                    intercepts.append(inc)
                median_inter = np.median(intercepts)

                # Center for offset
                mid_x = (box_length - 1) / 2.0
                mid_fit = median_inter + median_slope * mid_x
                center_price = np.exp(mid_fit) if use_log else mid_fit
                box_height = bx["hi"] - bx["lo"]
                offset = box_height / 2.0 / (center_price if use_log else 1.0)
                intercept_upper = median_inter + offset
                intercept_lower = median_inter - offset

                # Extrapolate to current bar (relative index box_length)
                upper_right_y = np.exp(intercept_upper + median_slope * box_length) if use_log else (intercept_upper + median_slope * box_length)
                lower_right_y = np.exp(intercept_lower + median_slope * box_length) if use_log else (intercept_lower + median_slope * box_length)

                if c[i] > upper_right_y:
                    channel_break = True
                    channel_dir = 1
                elif c[i] < lower_right_y:
                    channel_break = True
                    channel_dir = -1

            # Also check if current slope is still flat enough
            if abs(median_slope) > max_abs_rel_slope:
                channel_break = True  # Treat steep slope as break to avoid false positives in trends

            box_break = (c[i] > bx["hi"]) or (c[i] < bx["lo"])

            # For ongoing consolidation, end if either box or channel break
            if box_break or channel_break:
                bx["end_idx"] = i; bx["end_ts"] = idx[i]
            else:
                keep.append(bx)
                bx["closes"].append(c[i])
                if i > bx["start_idx"]:
                    bx["age"] = i - bx["left_idx"] + 1
        active = keep

        if active:
            newest = active[-1]
            in_box_any[i] = True
            box_hi_newest[i] = newest["hi"]; box_lo_newest[i] = newest["lo"]
            box_age_newest[i] = newest["age"]
            entry_idx_new[i] = newest["start_idx"]; left_idx_new[i] = newest["left_idx"]
            current_level_newest[i] = newest["level"]
        else:
            in_box_any[i] = False; box_age_newest[i] = 0
            entry_idx_new[i] = np.nan; left_idx_new[i] = np.nan
            current_level_newest[i] = -1

    i_check = check_bar if check_bar < 0 else int(check_bar)
    if i_check < 0: i_check = n + i_check
    if i_check < 0 or i_check >= n:
        return False, {"reason": "bad_check_bar"}

    if not in_box_any[i_check]:
        return False, {"reason": "not_in_consolidation", "timestamp": idx[i_check]}

    # Get info from newest at i_check
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
        "bars_inside": bars_inside[i_check],
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[i_check],
        "max_height_pct_req": pct_levels[current_level_newest[i_check]],
        "atr_ok": atr_ok[i_check],
        "range_high": range_high[i_check],
        "range_low": range_low[i_check],
        "range_mid": (range_high[i_check] + range_low[i_check]) / 2.0 if not np.isnan(range_high[i_check]) else np.nan,
        "current_close": float(c[i_check]),
        "inside_range": True
    }
    return True, res