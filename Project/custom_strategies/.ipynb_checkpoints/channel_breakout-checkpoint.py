# custom_strategies/channel_breakout.py

# min df number = 23 (for ATR etc.)

import pandas as pd
import numpy as np

def detect_channel_breakout(
    df: pd.DataFrame,
    check_bar: int = -1,
    use_log: bool = True
) -> tuple[bool, dict]:
    """
    Detect if the specified bar is a breakout from diagonal consolidation channel.
    
    Args:
        df: DataFrame with OHLC data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
        use_log: Whether to use log scale for fit
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    N = 7
    min_bars_inside = 4
    pct_levels = [40.0, 35.0, 25.0, 15.0]
    use_atr_filter = True
    atr_len = 14
    atr_sma = 7
    atr_k = 1.5  # Higher for diagonal
    dedupe_eps = 0.01

    if df is None or len(df) < max(N, atr_len + atr_sma) + 2:
        return False, {}

    d = df.copy()
    for col in ("open","high","low","close"):
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
            wc = np.log(c[lo_i:i+1]) if use_log else c[lo_i:i+1]
            mslope, minter = compute_fit(wc)
            if not np.isnan(mslope):
                req = 0
                for j in range(N):
                    fit = minter + mslope * j
                    p_fit = np.exp(fit) if use_log else fit
                    req = max(req, h[lo_i + j] - p_fit, p_fit - l[lo_i + j])
                median_p = np.median(c[lo_i:i+1])
                height_pct[i] = 100 * 2 * req / median_p if median_p != 0 else np.nan

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
    channel_offset_newest = np.full(n, np.nan)
    channel_age_newest = np.zeros(n, dtype=int)
    entry_idx_new = np.full(n, np.nan); left_idx_new = np.full(n, np.nan)
    current_level_newest = np.full(n, -1)

    for i in range(n):
        if is_entry[i]:
            lvl = potential_level[i]
            lo_i = i - (N-1)
            wc = np.log(c[lo_i:i+1]) if use_log else c[lo_i:i+1]
            mslope, minter = compute_fit(wc)
            req = 0
            for j in range(N):
                fit = minter + mslope * j
                p_fit = np.exp(fit) if use_log else fit
                req = max(req, h[lo_i + j] - p_fit, p_fit - l[lo_i + j])
            if not np.isnan(req):
                left_idx_val = max(0, i - (N - 1))
                initial_age = min(N, i - left_idx_val + 1)
                bx_closes = list(c[left_idx_val:i+1])
                ch = {
                    "start_idx": i, "start_ts": idx[i],
                    "left_idx": left_idx_val,
                    "left_ts": idx[left_idx_val],
                    "end_idx": None, "end_ts": None,
                    "base_offset": float(req),
                    "age": initial_age,
                    "level": lvl,
                    "closes": bx_closes  # List of closes inside channel
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
                mslope, minter = compute_fit(wc)
                req = 0
                for j in range(N):
                    fit = minter + mslope * j
                    p_fit = np.exp(fit) if use_log else fit
                    req = max(req, h[lo_i + j] - p_fit, p_fit - l[lo_i + j])
                ch["base_offset"] = req
                ch["left_idx"] = i - (N - 1)
                ch["left_ts"] = idx[ch["left_idx"]]
                ch["age"] = N
                ch["level"] = tighter_lvl
                ch["closes"] = list(c[ch["left_idx"]:i])  # Update closes to recent, exclude current

            # Tentative append for fit
            temp_closes = ch["closes"] + [c[i]]
            temp_length = len(temp_closes)
            temp_closes_log = np.log(temp_closes) if use_log else np.array(temp_closes)
            mslope, minter = compute_fit(temp_closes_log)
            if not np.isnan(mslope):
                mid_x = (temp_length - 1) / 2.0
                mid_fit = minter + mslope * mid_x
                center_price = np.exp(mid_fit) if use_log else mid_fit
                offset = ch["base_offset"] / (center_price if use_log else 1.0)
                intercept_upper = minter + offset
                intercept_lower = minter - offset
                upper_right_y = np.exp(intercept_upper + mslope * (temp_length - 1)) if use_log else (intercept_upper + mslope * (temp_length - 1))
                lower_right_y = np.exp(intercept_lower + mslope * (temp_length - 1)) if use_log else (intercept_lower + mslope * (temp_length - 1))
                channel_break_up = c[i] > upper_right_y
                channel_break_down = c[i] < lower_right_y
                channel_break = channel_break_up or channel_break_down
            else:
                channel_break = False
                channel_break_up = False
                channel_break_down = False

            if channel_break:
                # Breakout from channel
                # Refit on previous for slope
                prev_closes_log = np.log(ch["closes"]) if use_log else np.array(ch["closes"])
                prev_slope, _ = compute_fit(prev_closes_log)
                channel_slope[i] = prev_slope
                breakout_direction[i] = 1 if channel_break_up else -1
                ch["end_idx"] = i
                ch["end_ts"] = idx[i]
            else:
                keep.append(ch)
                ch["closes"].append(c[i])
                if i > ch["start_idx"]:
                    ch["age"] = i - ch["left_idx"] + 1
        active = keep

        if active:
            newest = active[-1]
            in_channel_any[i] = True
            channel_offset_newest[i] = newest["base_offset"]
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

    # Use i_check-1 for channel info
    ei = int(entry_idx_new[i_check-1]) if not np.isnan(entry_idx_new[i_check-1]) else None
    li = int(left_idx_new[i_check-1]) if not np.isnan(left_idx_new[i_check-1]) else None
    res = {
        "timestamp": idx[i_check],
        "date": idx[i_check].strftime("%Y-%m-%d %H:%M:%S"),
        "breakout": True,
        "direction": "Up" if breakout_direction[i_check] == 1 else "Down",
        "color": "#3ACF3F" if breakout_direction[i_check] == 1 else "#FF007F",
        "current_bar": (i_check == n-1),
        "window_size": int(N),
        "entry_idx": ei, "entry_ts": (idx[ei] if ei is not None else None),
        "left_idx": li, "left_ts": (idx[li] if li is not None else None),
        "channel_age": int(channel_age_newest[i_check-1]),
        "channel_offset": float(channel_offset_newest[i_check-1]),
        "channel_direction": "Upwards" if channel_slope[i_check] > 0 else "Downwards",
        "channel_slope": float(channel_slope[i_check]),
        "bars_inside": bars_inside[i_check-1],
        "min_bars_inside_req": min_bars_inside,
        "height_pct": height_pct[i_check-1],
        "max_height_pct_req": pct_levels[int(current_level_newest[i_check-1])],
        "atr_ok": atr_ok[i_check-1]
    }
    return True, res