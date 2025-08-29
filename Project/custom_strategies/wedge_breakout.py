# custom_strategies/wedge_breakout.py

# min df number = 23 (for ATR etc.)

import pandas as pd
import numpy as np

def detect_wedge_breakout(
    df: pd.DataFrame,
    check_bar: int = -1,
    use_log: bool = True,
    width_multiplier: float = 1.0
) -> tuple[bool, dict]:
    """
    Detect if the specified bar is a breakout from diagonal consolidation wedge.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        use_log: Whether to use log scale for fit
        width_multiplier: Multiplier to scale wedge width (>1.0 to widen) - note: not used in wedge as width is implicit in fits
    
    Returns:
        tuple: (detect: bool, result: dict)
    """
    N = 14
    min_bars_inside = 14
    pct_levels = [40.0, 35.0, 25.0, 15.0]
    use_atr_filter = True
    atr_len = 14
    atr_sma = 7
    atr_k = 1.0  # Higher for diagonal
    dedupe_eps = 0.01

    if df is None or len(df) < max(N, atr_len + atr_sma) + 2:
        return False, {}

    d = df.copy()
    for col in ("open", "high", "low", "close"):
        d[col] = d[col].astype(float)

    h, l, c = d["high"].values, d["low"].values, d["close"].values
    idx = d.index
    n = len(d)

    def compute_fit(closes):
        len_ = len(closes)
        if len_ < 2:
            return np.nan, np.nan
        slopes = []
        for j in range(len_ - 1):
            for k in range(j + 1, len_):
                sl = (closes[k] - closes[j]) / (k - j)
                slopes.append(sl)
        median_slope = np.median(slopes) if slopes else np.nan

        intercepts = []
        for j in range(len_):
            inc = closes[j] - median_slope * j
            intercepts.append(inc)
        median_inter = np.median(intercepts) if intercepts else np.nan
        return median_slope, median_inter

    height_pct = np.full(n, np.nan)
    for i in range(n):
        if i >= N-1:
            lo_i = i - (N-1)
            wh = np.log(h[lo_i:i+1]) if use_log else h[lo_i:i+1]
            wl = np.log(l[lo_i:i+1]) if use_log else l[lo_i:i+1]
            uslope, uinter = compute_fit(wh)
            lslope, linter = compute_fit(wl)
            if not np.isnan(uslope) and not np.isnan(lslope):
                max_dev = 0
                for j in range(N):
                    u = uinter + uslope * j
                    l_ = linter + lslope * j
                    u = np.exp(u) if use_log else u
                    l_ = np.exp(l_) if use_log else l_
                    max_dev = max(max_dev, abs(h[lo_i + j] - u), abs(l[lo_i + j] - l_))
                median_p = np.median(c[lo_i:i+1])
                height_pct[i] = 100 * 2 * max_dev / median_p if median_p != 0 else np.nan

    bars_inside = np.full(n, N)  # By construction

    pc = np.roll(c, 1); pc[0] = np.nan
    tr = np.maximum.reduce([h-l, np.abs(h-pc), np.abs(l-pc)])
    atr = np.full(n, np.nan)
    if n >= atr_len:
        atr[atr_len-1] = np.nanmean(tr[0:atr_len])
        alpha = 1.0 / atr_len
        for i in range(atr_len, n):
            atr[i] = atr[i-1] + alpha * (tr[i] - atr[i-1])
    atr_slow = pd.Series(atr, index=idx).rolling(atr_sma, min_periods=atr_sma).mean().values
    atr_ok = (~np.isnan(atr)) & (~np.isnan(atr_slow)) & (atr < atr_k * atr_slow) if use_atr_filter else np.ones(n, bool)

    # Compute potential level for each bar (tightest possible)
    potential_level = np.full(n, -1)
    for i in range(n):
        if bars_inside[i] >= min_bars_inside and atr_ok[i]:
            for lvl in range(len(pct_levels)-1, -1, -1):
                if height_pct[i] <= pct_levels[lvl]:
                    potential_level[i] = lvl
                    break

    cond_now = potential_level >= 0
    cond_prev = np.roll(cond_now, 1); cond_prev[0] = False
    is_entry = cond_now & (~cond_prev)

    active = []
    channels = []

    is_breakout = np.zeros(n, dtype=bool)
    breakout_direction = np.full(n, 0)  # 1 upper, -1 lower, 0 none
    channel_slope = np.full(n, np.nan)  # Slope at breakout
    in_channel_any = np.zeros(n, dtype=bool)
    channel_age_newest = np.zeros(n, dtype=int)
    entry_idx_new = np.full(n, np.nan); left_idx_new = np.full(n, np.nan)
    current_level_newest = np.full(n, -1)

    for i in range(n):
        if is_entry[i]:
            lvl = potential_level[i]
            lo_i = i - (N-1)
            wc = np.log(c[lo_i:i+1]) if use_log else c[lo_i:i+1]
            wh = np.log(h[lo_i:i+1]) if use_log else h[lo_i:i+1]
            wl = np.log(l[lo_i:i+1]) if use_log else l[lo_i:i+1]
            mslope, minter = compute_fit(wc)
            uslope, uinter = compute_fit(wh)
            lslope, linter = compute_fit(wl)
            # Check initial closes inside
            initial_outside = False
            for j in range(N):
                upper_j = np.exp(uinter + uslope * j) if use_log else uinter + uslope * j
                lower_j = np.exp(linter + lslope * j) if use_log else linter + lslope * j
                close_j = c[lo_i + j]
                if close_j > upper_j or close_j < lower_j:
                    initial_outside = True
                    break
            if not initial_outside:
                left_idx_val = max(0, i - (N - 1))
                initial_age = min(N, i - left_idx_val + 1)
                bx_closes = list(c[left_idx_val:i+1])
                bx_highs = list(h[left_idx_val:i+1])
                bx_lows = list(l[left_idx_val:i+1])
                ch = {
                    "start_idx": i, "start_ts": idx[i],
                    "left_idx": left_idx_val,
                    "left_ts": idx[left_idx_val],
                    "end_idx": None, "end_ts": None,
                    "age": initial_age,
                    "level": lvl,
                    "closes": bx_closes,  # List of closes inside wedge
                    "highs": bx_highs,
                    "lows": bx_lows
                }
                active.append(ch)
                channels.append(ch)

        keep = []
        for ch in active:
            # Check for tightening if possible
            tighter_lvl = potential_level[i]
            if tighter_lvl > ch["level"] and i - ch["left_idx"] + 1 > N:
                # Tighten to recent N
                lo_i = i - (N-1)
                wc = np.log(c[lo_i:i+1]) if use_log else c[lo_i:i+1]
                wh = np.log(h[lo_i:i+1]) if use_log else h[lo_i:i+1]
                wl = np.log(l[lo_i:i+1]) if use_log else l[lo_i:i+1]
                mslope, minter = compute_fit(wc)
                uslope, uinter = compute_fit(wh)
                lslope, linter = compute_fit(wl)
                ch["left_idx"] = i - (N - 1)
                ch["left_ts"] = idx[ch["left_idx"]]
                ch["age"] = N
                ch["level"] = tighter_lvl
                ch["closes"] = list(c[ch["left_idx"]:i])  # Update to recent, exclude current
                ch["highs"] = list(h[ch["left_idx"]:i])
                ch["lows"] = list(l[ch["left_idx"]:i])

            # Compute current fits for projection
            prev_closes_log = np.log(ch["closes"]) if use_log else np.array(ch["closes"])
            prev_highs_log = np.log(ch["highs"]) if use_log else np.array(ch["highs"])
            prev_lows_log = np.log(ch["lows"]) if use_log else np.array(ch["lows"])
            prev_length = len(ch["closes"])
            mslope, minter = compute_fit(prev_closes_log)
            uslope, uinter = compute_fit(prev_highs_log)
            lslope, linter = compute_fit(prev_lows_log)
            if not np.isnan(uslope) and not np.isnan(lslope):
                projected_upper = np.exp(uinter + uslope * prev_length) if use_log else uinter + uslope * prev_length
                projected_lower = np.exp(linter + lslope * prev_length) if use_log else linter + lslope * prev_length
                channel_break_up = c[i] > projected_upper
                channel_break_down = c[i] < projected_lower
                channel_break = channel_break_up or channel_break_down
            else:
                channel_break = False
                channel_break_up = False
                channel_break_down = False

            if channel_break:
                # Breakout from wedge
                channel_slope[i] = mslope
                breakout_direction[i] = 1 if channel_break_up else -1
                ch["end_idx"] = i
                ch["end_ts"] = idx[i]
            else:
                keep.append(ch)
                ch["closes"].append(c[i])
                ch["highs"].append(h[i])
                ch["lows"].append(l[i])
                if i > ch["start_idx"]:
                    ch["age"] = i - ch["left_idx"] + 1

        active = keep

        if active:
            newest = active[-1]
            in_channel_any[i] = True
            channel_age_newest[i] = newest["age"]
            entry_idx_new[i] = newest["start_idx"]
            left_idx_new[i] = newest["left_idx"]
            current_level_newest[i] = newest["level"]
        else:
            in_channel_any[i] = False
            channel_age_newest[i] = 0
            entry_idx_new[i] = np.nan
            left_idx_new[i] = np.nan
            current_level_newest[i] = -1

    i_check = check_bar if check_bar < 0 else int(check_bar)
    if i_check < 0: i_check = n + i_check
    if i_check < 0 or i_check >= n:
        return False, {"reason": "bad_check_bar"}

    if breakout_direction[i_check] == 0:
        return False, {"reason": "not_breakout", "timestamp": idx[i_check]}

    # Use i_check-1 for wedge info, with safety checks
    prev_idx = max(0, i_check - 1)  # Avoid index error
    ei = int(entry_idx_new[prev_idx]) if not np.isnan(entry_idx_new[prev_idx]) else None
    li = int(left_idx_new[prev_idx]) if not np.isnan(left_idx_new[prev_idx]) else None
    channel_dir = "Upwards" if channel_slope[i_check] > 0 else "Downwards" if channel_slope[i_check] < 0 else "Horizontal"
    g = (np.exp(channel_slope[i_check]) - 1) * 100 if use_log and not np.isnan(channel_slope[i_check]) else (channel_slope[i_check] / np.median(c[li:ei+1])) * 100 if not np.isnan(channel_slope[i_check]) else 0.0

    res = {
        "timestamp": idx[i_check],
        "date": idx[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "breakout": True,
        "direction": "Up" if breakout_direction[i_check] == 1 else "Down",
        "color": "#3ACF3F" if breakout_direction[i_check] == 1 else "#FF007F",
        "current_bar": (i_check == n-1),
        "window_size": int(N),
        "entry_idx": ei, "entry_ts": idx[ei] if ei is not None else None,
        "left_idx": li, "left_ts": idx[li] if li is not None else None,
        "channel_age": int(channel_age_newest[prev_idx]),
        "channel_direction": channel_dir,
        "channel_slope": float(channel_slope[i_check]) if not np.isnan(channel_slope[i_check]) else 0.0,
        "percent_growth_per_bar": float(g),
        "bars_inside": bars_inside[i_check],
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[i_check],
        "max_height_pct_req": pct_levels[int(current_level_newest[prev_idx])] if current_level_newest[prev_idx] >= 0 else np.nan,
        "atr_ok": atr_ok[i_check]
    }
    return True, res