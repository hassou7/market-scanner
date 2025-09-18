# custom_strategies/box_breakout.py v2

# version with channel inside. Strong breakout is a breakout from the channel and the box. Weak breakout is a breakout only from the channel or from the box occuring after a channel breakout. 

import pandas as pd
import numpy as np
import math

def detect_consolidation_breakout(
    df: pd.DataFrame,
    check_bar: int = -1,
    use_log: bool = True,
    channel_multiplier: float = 0.6,
    use_midrange: bool = True,
    channel_max_pct: float = 100.0,
    max_height_pct: float = 35.0
) -> tuple[bool, dict]:
    """
    Detect if the specified bar is a breakout from consolidation box with optional channel.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        use_log: Whether to use log scale for fit
        channel_multiplier: Multiplier to scale channel width (0.7 = tighter)
        use_midrange: If True, use (H+L)/2 for channel fit; if False, use close
        channel_max_pct: Maximum % of box height for valid channel
        max_height_pct: Maximum percentage height of the box relative to its median price
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    N = 7
    min_bars_inside = 4
    pct_levels = [max_height_pct, 25.0, 15.0]
    use_atr_filter = True
    atr_len = 14
    atr_sma = 7
    atr_k = 0.9
    channel_min_length = 6
    channel_break_buffer = 0.05
    dedupe_eps = 0.01

    if df is None or len(df) < max(N, atr_len + atr_sma) + 2:
        return False, {"reason": "insufficient_data"}

    d = df.copy()
    for col in ("open","high","low","close"):
        d[col] = d[col].astype(float)

    h, l, c = d["high"].values, d["low"].values, d["close"].values
    idx = d.index
    n = len(d)

    # Calculate midrange if needed
    midrange = (h + l) / 2.0

    # Rolling range calculations
    range_high = np.full(n, np.nan)
    range_low = np.full(n, np.nan)
    height_pct = np.full(n, np.nan)
    for i in range(n):
        if i >= N-1:
            lo_i = i - (N-1)
            rh = np.max(h[lo_i:i+1])
            rl = np.min(l[lo_i:i+1])
            range_high[i] = rh
            range_low[i] = rl
            denom = rh + rl
            height_pct[i] = np.nan if denom == 0 else 200.0 * (rh - rl) / denom

    # Inside bar detection
    inside = np.zeros(n)
    bars_inside = np.full(n, np.nan)
    for i in range(n):
        rh, rl = range_high[i], range_low[i]
        if not np.isnan(rh) and not np.isnan(rl):
            inside[i] = 1.0 if (h[i] <= rh and l[i] >= rl) else 0.0
        if i >= N-1:
            lo_i = i - (N-1)
            bars_inside[i] = np.sum(inside[lo_i:i+1])

    # ATR calculation
    pc = np.roll(c, 1)
    pc[0] = np.nan
    tr = np.maximum.reduce([h-l, np.abs(h-pc), np.abs(l-pc)])
    atr = np.full(n, np.nan)
    if n >= atr_len:
        atr[atr_len-1] = np.nanmean(tr[0:atr_len])
        alpha = 1.0 / atr_len
        for i in range(atr_len, n):
            atr[i] = atr[i-1] + alpha * (tr[i] - atr[i-1])
    atr_slow = pd.Series(atr, index=idx).rolling(atr_sma, min_periods=atr_sma).mean().values
    atr_ok = (~np.isnan(atr)) & (~np.isnan(atr_slow)) & (atr < atr_k * atr_slow) if use_atr_filter else np.ones(n, bool)

    # Compute potential level for each bar
    potential_level = np.full(n, -1)
    for i in range(n):
        if bars_inside[i] >= min_bars_inside and atr_ok[i]:
            for lvl in range(len(pct_levels)-1, -1, -1):
                if height_pct[i] <= pct_levels[lvl]:
                    potential_level[i] = lvl
                    break

    # Entry detection
    cond_now = potential_level >= 0
    cond_prev = np.roll(cond_now, 1)
    cond_prev[0] = False
    is_entry = cond_now & (~cond_prev)

    def similar_bounds(hi1, lo1, hi2, lo2):
        mid = (hi1 + lo1) / 2.0
        if mid == 0: return False
        return (abs(hi1 - hi2) / mid <= dedupe_eps) and (abs(lo1 - lo2) / mid <= dedupe_eps)

    def compute_theil_sen(values):
        """Compute Theil-Sen estimator for slope and intercept"""
        n_vals = len(values)
        if n_vals < 2:
            return np.nan, np.nan
        
        slopes = []
        for ii in range(n_vals - 1):
            for jj in range(ii + 1, n_vals):
                slope = (values[jj] - values[ii]) / (jj - ii)
                slopes.append(slope)
        median_slope = np.median(slopes) if slopes else 0.0
        
        intercepts = []
        for ii in range(n_vals):
            intercept = values[ii] - median_slope * ii
            intercepts.append(intercept)
        median_intercept = np.median(intercepts) if intercepts else 0.0
        
        return median_slope, median_intercept

    def compute_channel_params(data_points, highs, lows, box_hi, box_lo, pos_for_bound, use_log, channel_multiplier, channel_max_pct):
        """Compute channel parameters and bounds at specified relative position"""
        n = len(data_points)
        if n < 2:
            return 1.0, np.nan, False, box_hi, box_lo
        
        # Log transform if needed
        if use_log:
            data_log = np.log(np.maximum(data_points, 1e-8))
            h_log = np.log(np.maximum(highs, 1e-8))
            l_log = np.log(np.maximum(lows, 1e-8))
        else:
            data_log = np.array(data_points)
            h_log = np.array(highs)
            l_log = np.array(lows)
        
        # Theil-Sen regression
        slope, intercept = compute_theil_sen(data_log)
        if np.isnan(slope):
            return 1.0, np.nan, False, box_hi, box_lo
        
        # Max deviation
        max_dev = 0.0
        for k in range(n):
            fit_val = intercept + slope * k
            if use_log:
                p_fit = np.exp(fit_val)
                h_val = np.exp(h_log[k])
                l_val = np.exp(l_log[k])
            else:
                p_fit = fit_val
                h_val = h_log[k]
                l_val = l_log[k]
            max_dev = max(max_dev, h_val - p_fit, p_fit - l_val)
        
        channel_req = max_dev * channel_multiplier
        
        # Offset
        mid_x = (n - 1) / 2.0
        mid_fit = intercept + slope * mid_x
        center_price = np.exp(mid_fit) if use_log else mid_fit
        if use_log:
            offset = channel_req / center_price if center_price > 0 else 0.0
        else:
            offset = channel_req
        
        # Widths for avg
        widths = []
        for px in [0, mid_x, n - 1]:
            p_fit_px = intercept + slope * px
            c_price_px = np.exp(p_fit_px) if use_log else p_fit_px
            if use_log:
                w_px = c_price_px * (np.exp(offset) - np.exp(-offset))
            else:
                w_px = 2 * channel_req
            widths.append(w_px)
        avg_channel_width = np.mean(widths)
        
        box_height = box_hi - box_lo
        ratio = avg_channel_width / box_height if box_height > 0 else 1.0
        h_pct = 100 * ratio
        valid = h_pct <= channel_max_pct
        
        # Bounds at pos_for_bound (n-1 for current, n for project)
        upper_val = intercept + offset + slope * pos_for_bound
        lower_val = intercept - offset + slope * pos_for_bound
        if use_log:
            upper_pos = np.exp(upper_val)
            lower_pos = np.exp(lower_val)
        else:
            upper_pos = upper_val
            lower_pos = lower_val
        
        return ratio, avg_channel_width, valid, upper_pos, lower_pos

    # Track active boxes
    active = []
    boxes = []
    
    # Arrays for tracking
    is_breakout = np.zeros(n, dtype=bool)
    breakout_direction = np.full(n, 0)  # 1 up, -1 down
    strong_break = np.zeros(n, dtype=bool)
    box_tightness = np.full(n, 1.0)
    breakout_types = ["" for _ in range(n)]
    channel_width_newest = np.full(n, np.nan)
    in_box_any = np.zeros(n, dtype=bool)
    box_hi_newest = np.full(n, np.nan)
    box_lo_newest = np.full(n, np.nan)
    box_age_newest = np.zeros(n, dtype=int)
    entry_idx_new = np.full(n, np.nan)
    left_idx_new = np.full(n, np.nan)
    current_level_newest = np.full(n, -1)

    for i in range(n):
        # Check for new box entry
        if is_entry[i]:
            lvl = potential_level[i]
            hi, lo = range_high[i], range_low[i]
            if not np.isnan(hi) and not np.isnan(lo):
                if not any(similar_bounds(hi, lo, b["hi"], b["lo"]) for b in active):
                    left_idx_val = max(0, i - (N - 1))
                    data_pts = []
                    h_pts = []
                    l_pts = []
                    for j in range(left_idx_val, i):
                        dp = midrange[j] if use_midrange else c[j]
                        data_pts.append(dp)
                        h_pts.append(h[j])
                        l_pts.append(l[j])
                    
                    bx = {
                        "start_idx": i, "start_ts": idx[i],
                        "left_idx": left_idx_val,
                        "left_ts": idx[left_idx_val],
                        "end_idx": None, "end_ts": None,
                        "hi": float(hi), "lo": float(lo),
                        "age": len(data_pts),
                        "level": lvl,
                        "data_points": data_pts,
                        "highs": h_pts,
                        "lows": l_pts,
                        "channel_alerted": False,
                        "last_channel_break_bar": None
                    }
                    active.append(bx)
                    boxes.append(bx)

        keep = []
        for bx in active:
            # Check for tightening
            tighter_lvl = potential_level[i]
            if tighter_lvl > bx["level"]:
                left = max(0, i - (N - 1))
                hi_new = range_high[i]
                lo_new = range_low[i]
                bx["hi"] = hi_new
                bx["lo"] = lo_new
                bx["left_idx"] = left
                bx["left_ts"] = idx[left]
                bx["age"] = N - 1
                bx["level"] = tighter_lvl
                bx["channel_alerted"] = False
                bx["last_channel_break_bar"] = None
                
                data_pts = []
                h_pts = []
                l_pts = []
                for j in range(left, i):
                    dp = midrange[j] if use_midrange else c[j]
                    data_pts.append(dp)
                    h_pts.append(h[j])
                    l_pts.append(l[j])
                bx["data_points"] = data_pts
                bx["highs"] = h_pts
                bx["lows"] = l_pts
            
            # Check for box breakout
            box_break = (c[i] > bx["hi"]) or (c[i] < bx["lo"])
            buffer_i = channel_break_buffer * atr[i] if not np.isnan(atr[i]) else 0.0
            
            if box_break:
                # Compute channel for projection (pos = n)
                data_pts = bx["data_points"]
                h_pts = bx["highs"]
                l_pts = bx["lows"]
                n_data = len(data_pts)
                ratio, ch_width, valid, upper_proj, lower_proj = compute_channel_params(
                    data_pts, h_pts, l_pts, bx["hi"], bx["lo"], n_data, use_log, channel_multiplier, channel_max_pct
                )
                
                simultaneous = False
                if valid and n_data >= channel_min_length:
                    if c[i] > upper_proj + buffer_i:
                        simultaneous = True
                    elif c[i] < lower_proj - buffer_i:
                        simultaneous = True
                
                if simultaneous:
                    bx["channel_alerted"] = True
                
                has_channel = valid and ratio < 1.0 and n_data >= channel_min_length
                box_dir = 1 if c[i] > bx["hi"] else -1
                detect = True
                is_strong = False
                b_type = ""
                if not has_channel:
                    is_strong = True
                    b_type = "strong_box_only"
                else:
                    previous_bar = bx["last_channel_break_bar"] == i - 1 if bx["last_channel_break_bar"] is not None else False
                    if simultaneous or previous_bar:
                        is_strong = True
                        b_type = "strong_box_channel" if simultaneous else "strong_box_prev_channel"
                    elif bx["channel_alerted"]:
                        is_strong = False
                        b_type = "weak_box_failed_channel"
                    else:
                        detect = False
                        b_type = "no_breakout"
                
                if detect:
                    is_breakout[i] = True
                    breakout_direction[i] = box_dir
                    strong_break[i] = is_strong
                    box_tightness[i] = ratio
                    breakout_types[i] = b_type
                    channel_width_newest[i] = ch_width if has_channel else np.nan
                    box_hi_newest[i] = bx["hi"]
                    box_lo_newest[i] = bx["lo"]
                    box_age_newest[i] = bx["age"]
                    entry_idx_new[i] = bx["start_idx"]
                    left_idx_new[i] = bx["left_idx"]
                    current_level_newest[i] = bx["level"]
                
                # End box
                bx["end_idx"] = i
                bx["end_ts"] = idx[i]
            else:
                # Extend box
                dp = midrange[i] if use_midrange else c[i]
                bx["data_points"].append(dp)
                bx["highs"].append(h[i])
                bx["lows"].append(l[i])
                bx["age"] += 1
                
                # Check channel breakout inside (pos = n-1)
                n_data = len(bx["data_points"])
                ratio, ch_width, valid, upper_curr, lower_curr = compute_channel_params(
                    bx["data_points"], bx["highs"], bx["lows"], bx["hi"], bx["lo"], n_data - 1, use_log, channel_multiplier, channel_max_pct
                )
                
                channel_break_curr = False
                ch_dir = 0
                if valid and n_data >= channel_min_length and ratio < 1.0:
                    if c[i] > upper_curr + buffer_i:
                        channel_break_curr = True
                        ch_dir = 1
                    elif c[i] < lower_curr - buffer_i:
                        channel_break_curr = True
                        ch_dir = -1
                
                if channel_break_curr:
                    bx["channel_alerted"] = True
                    bx["last_channel_break_bar"] = i
                    is_breakout[i] = True
                    breakout_direction[i] = ch_dir
                    strong_break[i] = False
                    box_tightness[i] = ratio
                    breakout_types[i] = "weak_channel_only"
                    channel_width_newest[i] = ch_width
                    box_hi_newest[i] = bx["hi"]
                    box_lo_newest[i] = bx["lo"]
                    box_age_newest[i] = bx["age"]
                    entry_idx_new[i] = bx["start_idx"]
                    left_idx_new[i] = bx["left_idx"]
                    current_level_newest[i] = bx["level"]
                
                keep.append(bx)
        
        active = keep

        # Update tracking for non-breakout bars
        if active and not is_breakout[i]:
            newest = active[-1]
            in_box_any[i] = True
            box_hi_newest[i] = newest["hi"]
            box_lo_newest[i] = newest["lo"]
            box_age_newest[i] = newest["age"]
            entry_idx_new[i] = newest["start_idx"]
            left_idx_new[i] = newest["left_idx"]
            current_level_newest[i] = newest["level"]

    # Check specified bar
    i_check = check_bar if check_bar < 0 else int(check_bar)
    if i_check < 0: i_check = n + i_check
    if i_check < 0 or i_check >= n:
        return False, {"reason": "bad_check_bar"}

    if not is_breakout[i_check]:
        return False, {"reason": "not_breakout", "timestamp": idx[i_check]}

    # Prepare result
    prev_idx = max(0, i_check - 1)
    ei = int(entry_idx_new[i_check]) if not np.isnan(entry_idx_new[i_check]) else None
    li = int(left_idx_new[i_check]) if not np.isnan(left_idx_new[i_check]) else None
    
    box_h = box_hi_newest[i_check]
    box_l = box_lo_newest[i_check]
    box_height = box_h - box_l if not np.isnan(box_h) and not np.isnan(box_l) else np.nan
    ch_w = channel_width_newest[i_check]
    
    res = {
        "timestamp": idx[i_check],
        "date": idx[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "breakout": True,
        "direction": "Up" if breakout_direction[i_check] == 1 else "Down",
        "current_bar": (i_check == n-1),
        "strong": bool(strong_break[i_check]),
        "breakout_type": breakout_types[i_check],
        "channel_ratio": float(box_tightness[i_check]),
        "channel_width": float(ch_w) if not np.isnan(ch_w) else np.nan,
        "box_height": float(box_height),
        "box_age": int(box_age_newest[i_check]),
        "window_size": int(N),
        "entry_idx": ei,
        "entry_ts": idx[ei] if ei is not None else None,
        "left_idx": li,
        "left_ts": idx[li] if li is not None else None,
        "box_hi": float(box_hi_newest[i_check]),
        "box_lo": float(box_lo_newest[i_check]),
        "box_mid": float((box_hi_newest[i_check] + box_lo_newest[i_check]) / 2.0) if not np.isnan(box_hi_newest[i_check]) and not np.isnan(box_lo_newest[i_check]) else np.nan,
        "bars_inside": bars_inside[prev_idx] if prev_idx < len(bars_inside) else np.nan,
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[prev_idx] if prev_idx < len(height_pct) else np.nan,
        "max_height_pct_req": pct_levels[int(current_level_newest[i_check])] if current_level_newest[i_check] >= 0 else np.nan,
        "atr_ok": atr_ok[prev_idx] if prev_idx < len(atr_ok) else False,
        "range_high": range_high[prev_idx] if prev_idx < len(range_high) else np.nan,
        "range_low": range_low[prev_idx] if prev_idx < len(range_low) else np.nan,
        "range_mid": (range_high[prev_idx] + range_low[prev_idx]) / 2.0 if prev_idx < len(range_high) else np.nan
    }
    return True, res