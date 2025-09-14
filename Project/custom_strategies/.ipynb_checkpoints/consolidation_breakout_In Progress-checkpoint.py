# custom_strategies/box_breakout.py

# min df number = 23

import pandas as pd
import numpy as np

def detect_consolidation_breakout(
    df: pd.DataFrame,
    check_bar: int = -1,
    use_log: bool = True,
    channel_multiplier: float = 0.7,
    use_midrange: bool = True,
    channel_max_pct: float = 100.0
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
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    N = 7
    min_bars_inside = 4
    max_height_pct = 35.0
    pct_levels = [35.0, 25.0, 15.0]
    use_atr_filter = True
    atr_len = 14
    atr_sma = 7
    atr_k = 0.9
    channel_min_length = 6
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
        n = len(values)
        if n < 2:
            return np.nan, np.nan
        
        slopes = []
        for i in range(n - 1):
            for j in range(i + 1, n):
                slope = (values[j] - values[i]) / (j - i)
                slopes.append(slope)
        median_slope = np.median(slopes) if slopes else 0.0
        
        intercepts = []
        for i in range(n):
            intercept = values[i] - median_slope * i
            intercepts.append(intercept)
        median_intercept = np.median(intercepts) if intercepts else 0.0
        
        return median_slope, median_intercept

    def compute_channel_params(data_points, highs, lows, box_hi, box_lo):
        """Compute channel parameters within a box"""
        n = len(data_points)
        if n < 2:
            return np.nan, 1.0, False, 0, 0
        
        # Convert to log if needed
        if use_log:
            data_log = np.log(np.maximum(data_points, 1e-10))
            highs_log = np.log(np.maximum(highs, 1e-10))
            lows_log = np.log(np.maximum(lows, 1e-10))
        else:
            data_log = data_points
            highs_log = highs
            lows_log = lows
        
        # Theil-Sen regression on data points
        slope, intercept = compute_theil_sen(data_log)
        
        if np.isnan(slope):
            return np.nan, 1.0, False, 0, 0
        
        # Calculate max deviation from fit line
        max_dev = 0.0
        for i in range(n):
            fit_val = intercept + slope * i
            if use_log:
                p_fit = np.exp(fit_val)
                h_val = np.exp(highs_log[i])
                l_val = np.exp(lows_log[i])
            else:
                p_fit = fit_val
                h_val = highs_log[i]
                l_val = lows_log[i]
            
            max_dev = max(max_dev, h_val - p_fit, p_fit - l_val)
        
        # Apply channel multiplier
        channel_req = max_dev * channel_multiplier
        
        # Calculate channel offset
        mid_x = (n - 1) / 2.0
        mid_fit = intercept + slope * mid_x
        center_price = np.exp(mid_fit) if use_log else mid_fit
        
        if use_log:
            channel_offset = channel_req / center_price if center_price > 0 else 0
            channel_width = center_price * (np.exp(channel_offset) - np.exp(-channel_offset))
        else:
            channel_offset = channel_req
            channel_width = 2 * channel_req
        
        # Calculate channel ratio (tightness)
        box_height = box_hi - box_lo
        channel_ratio = channel_width / box_height if box_height > 0 else 1.0
        channel_h_pct = 100 * channel_ratio
        
        # Valid if within max percentage
        valid_channel = channel_h_pct <= channel_max_pct
        
        # Calculate channel boundaries at the end
        if valid_channel:
            upper_intercept = intercept + channel_offset
            lower_intercept = intercept - channel_offset
            upper_val = upper_intercept + slope * (n - 1)
            lower_val = lower_intercept + slope * (n - 1)
            if use_log:
                upper_bound = np.exp(upper_val)
                lower_bound = np.exp(lower_val)
            else:
                upper_bound = upper_val
                lower_bound = lower_val
        else:
            upper_bound = box_hi
            lower_bound = box_lo
        
        return channel_ratio, channel_ratio, valid_channel, upper_bound, lower_bound

    # Track active boxes
    active = []
    boxes = []
    
    # Arrays for tracking
    is_breakout = np.zeros(n, dtype=bool)
    breakout_direction = np.full(n, 0)  # 1 upper, -1 lower, 0 none
    strong_break = np.zeros(n, dtype=bool)
    box_tightness = np.full(n, 1.0)
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
                    initial_age = min(N, i - left_idx_val + 1)
                    
                    # IMPORTANT: Collect data points EXCLUDING current bar for initial box
                    # The box should be formed from the N bars BEFORE checking for breakout
                    data_pts = []
                    h_pts = []
                    l_pts = []
                    for j in range(left_idx_val, i):  # Changed from i+1 to i (exclude current)
                        dp = midrange[j] if use_midrange else c[j]
                        data_pts.append(dp)
                        h_pts.append(h[j])
                        l_pts.append(l[j])
                    
                    # Box boundaries should be from the window excluding current bar
                    actual_hi = np.max(h[left_idx_val:i])  # Exclude current bar
                    actual_lo = np.min(l[left_idx_val:i])  # Exclude current bar
                    
                    bx = {
                        "start_idx": i, "start_ts": idx[i],
                        "left_idx": left_idx_val,
                        "left_ts": idx[left_idx_val],
                        "end_idx": None, "end_ts": None,
                        "hi": float(actual_hi), "lo": float(actual_lo),  # Use actual bounds
                        "age": initial_age,
                        "level": lvl,
                        "data_points": data_pts,
                        "highs": h_pts,
                        "lows": l_pts
                    }
                    active.append(bx)
                    boxes.append(bx)

        keep = []
        for bx in active:
            # Check for tightening
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
                
                # Update data points
                bx["data_points"] = []
                bx["highs"] = []
                bx["lows"] = []
                for j in range(bx["left_idx"], i):
                    dp = midrange[j] if use_midrange else c[j]
                    bx["data_points"].append(dp)
                    bx["highs"].append(h[j])
                    bx["lows"].append(l[j])

            # Check for breakout (close-based)
            box_break = (c[i] > bx["hi"]) or (c[i] < bx["lo"])
            
            # Compute channel parameters if box length sufficient
            channel_break = False
            channel_dir = 0
            ratio = 1.0
            
            if len(bx["data_points"]) >= channel_min_length:
                ratio, _, valid_ch, upper_b, lower_b = compute_channel_params(
                    np.array(bx["data_points"]),
                    np.array(bx["highs"]),
                    np.array(bx["lows"]),
                    bx["hi"], bx["lo"]
                )
                
                if valid_ch:
                    if c[i] > upper_b:
                        channel_break = True
                        channel_dir = 1
                    elif c[i] < lower_b:
                        channel_break = True
                        channel_dir = -1
            
            if box_break:
                # Box breakout detected
                is_breakout[i] = True
                breakout_direction[i] = 1 if c[i] > bx["hi"] else -1
                strong_break[i] = channel_break  # Strong if channel also breaks
                box_tightness[i] = ratio if not np.isnan(ratio) else 1.0
                bx["end_idx"] = i
                bx["end_ts"] = idx[i]
            else:
                # Continue box
                keep.append(bx)
                dp = midrange[i] if use_midrange else c[i]
                bx["data_points"].append(dp)
                bx["highs"].append(h[i])
                bx["lows"].append(l[i])
                if i > bx["start_idx"]:
                    bx["age"] = i - bx["left_idx"] + 1
        
        active = keep

        # Update tracking arrays
        if active:
            newest = active[-1]
            in_box_any[i] = True
            box_hi_newest[i] = newest["hi"]
            box_lo_newest[i] = newest["lo"]
            box_age_newest[i] = newest["age"]
            entry_idx_new[i] = newest["start_idx"]
            left_idx_new[i] = newest["left_idx"]
            current_level_newest[i] = newest["level"]
        else:
            in_box_any[i] = False
            box_age_newest[i] = 0
            entry_idx_new[i] = np.nan
            left_idx_new[i] = np.nan
            current_level_newest[i] = -1

    # Check specified bar
    i_check = check_bar if check_bar < 0 else int(check_bar)
    if i_check < 0: i_check = n + i_check
    if i_check < 0 or i_check >= n:
        return False, {"reason": "bad_check_bar"}

    if not is_breakout[i_check]:
        return False, {"reason": "not_breakout", "timestamp": idx[i_check]}

    # Get box info from previous bar
    prev_idx = max(0, i_check - 1)
    ei = int(entry_idx_new[prev_idx]) if not np.isnan(entry_idx_new[prev_idx]) else None
    li = int(left_idx_new[prev_idx]) if not np.isnan(left_idx_new[prev_idx]) else None
    
    res = {
        "timestamp": idx[i_check],
        "date": idx[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "breakout": True,
        "direction": "Up" if breakout_direction[i_check] == 1 else "Down",
        "color": "#3ACF3F" if breakout_direction[i_check] == 1 else "#FF007F",
        "current_bar": (i_check == n-1),
        "strong": bool(strong_break[i_check]),
        "channel_ratio": float(box_tightness[i_check]),
        "window_size": int(N),
        "entry_idx": ei,
        "entry_ts": idx[ei] if ei is not None else None,
        "left_idx": li,
        "left_ts": idx[li] if li is not None else None,
        "box_age": int(box_age_newest[prev_idx]),
        "box_hi": float(box_hi_newest[prev_idx]),
        "box_lo": float(box_lo_newest[prev_idx]),
        "box_mid": float((box_hi_newest[prev_idx] + box_lo_newest[prev_idx]) / 2.0),
        "bars_inside": bars_inside[prev_idx] if prev_idx < len(bars_inside) else np.nan,
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[prev_idx] if prev_idx < len(height_pct) else np.nan,
        "max_height_pct_req": pct_levels[current_level_newest[prev_idx]] if current_level_newest[prev_idx] >= 0 else np.nan,
        "atr_ok": atr_ok[prev_idx] if prev_idx < len(atr_ok) else False,
        "range_high": range_high[prev_idx] if prev_idx < len(range_high) else np.nan,
        "range_low": range_low[prev_idx] if prev_idx < len(range_low) else np.nan,
        "range_mid": (range_high[prev_idx] + range_low[prev_idx]) / 2.0 if prev_idx < len(range_high) else np.nan
    }
    return True, res