import numpy as np
import pandas as pd
import pandas_ta as ta

# -------------------------------
# Global Parameters
# -------------------------------
Pow = 5
Smooth = 13
HA_ma_length = 15
wick_threshold = 0.85
atr_trend_threshold = 0.01

# -------------------------------
# Helper Functions
# -------------------------------
def ama(series, period=2, period_fast=2, period_slow=30, epsilon=1e-10):
    n = period + 1
    src = np.asarray(series)
    hh = pd.Series(src).rolling(window=n, min_periods=1).max().values
    ll = pd.Series(src).rolling(window=n, min_periods=1).min().values
    mltp = np.where((hh - ll) != 0, np.abs(2 * src - ll - hh) / (hh - ll + epsilon), 0)
    sc_fastest = 2 / (period_fast + 1)
    sc_slowest = 2 / (period_slow + 1)
    sc = (mltp * (sc_fastest - sc_slowest) + sc_slowest) ** 2
    sc = np.nan_to_num(sc, nan=0.0, posinf=0.0, neginf=0.0)
    ama_values = np.zeros_like(src)
    ama_values[:period] = src[:period]
    for i in range(period, len(src)):
        ama_values[i] = ama_values[i - 1] + sc[i] * (src[i] - ama_values[i - 1])
    return ama_values

def jsmooth(src, smooth, power):
    src = np.asarray(src)
    beta = 0.45 * (smooth - 1) / (0.45 * (smooth - 1) + 2)
    alpha = beta ** power
    length = len(src)
    jma = np.zeros(length)
    e0 = np.zeros(length)
    e1 = np.zeros(length)
    e2 = np.zeros(length)
    e0[0] = src[0]
    e1[0] = 0
    e2[0] = 0
    jma[0] = src[0]
    for i in range(1, length):
        e0[i] = (1 - alpha) * src[i] + alpha * e0[i - 1]
        e1[i] = (src[i] - e0[i]) * (1 - beta) + beta * e1[i - 1]
        e2[i] = (e0[i] - jma[i - 1]) * ((1 - alpha) ** 2) + (alpha ** 2) * e2[i - 1]
        jma[i] = jma[i - 1] + e2[i]
    return jma

def pivot(osc, LBL, LBR, highlow):
    pivots = [0.0] * len(osc)
    for i in range(LBL + LBR, len(osc)):
        ref = osc[i - LBR]
        is_pivot = True
        for j in range(1, LBL + 1):
            idx = i - LBR - j
            if idx < 0:
                continue
            if highlow.lower() == 'high':
                if osc[idx] >= ref:
                    is_pivot = False
                    break
            elif highlow.lower() == 'low':
                if osc[idx] <= ref:
                    is_pivot = False
                    break
        if is_pivot:
            for j in range(1, LBR + 1):
                idx = i - LBR + j
                if idx >= len(osc):
                    continue
                if highlow.lower() == 'high':
                    if osc[idx] >= ref:
                        is_pivot = False
                        break
                elif highlow.lower() == 'low':
                    if osc[idx] <= ref:
                        is_pivot = False
                        break
        if is_pivot:
            pivots[i - LBR] = ref
    return pivots

def bars_since(condition):
    """
    Calculate how many bars have passed since the condition was last True.
    
    Parameters:
    condition : pandas.Series
        Boolean series where True indicates the condition occurred
        
    Returns:
    pandas.Series
        Integer series with the same index as condition, containing the number
        of bars since the condition was last True
    """
    # Create an output array of integers (not Timestamps)
    out = np.full(len(condition), np.nan)
    last_true = -1
    
    # Iterate through the condition Series
    for i in range(len(condition)):
        if condition.iloc[i]:
            last_true = i
            out[i] = 0
        else:
            out[i] = 0 if last_true == -1 else i - last_true
    
    # Return as Series with the same index but numeric values
    # This ensures it's integers being compared later, not Timestamps
    return pd.Series(out, index=condition.index).astype(int)

def percentile_rank_series(s):
    current = s.iloc[-1]
    rank = (s <= current).sum()
    return (rank / len(s)) * 100

# -------------------------------
# get_signals – hbs_indicator_v8
# -------------------------------
def get_signals(df):
    error = ""
    if len(df.index) < (HA_ma_length + 1):
        error = f"Skipping - Insufficient data - ({len(df.index)})"
        return df, error

    # Ensure pending flag columns are boolean
    df['IsPendingBull'] = False
    df['IsPendingBear'] = False

    # ATRs
    df['atr']   = ta.atr(df['high'], df['low'], df['close'], 14)
    df['atr_3'] = ta.atr(df['high'], df['low'], df['close'], 3)
    df['atr_4'] = ta.atr(df['high'], df['low'], df['close'], 4)
    df['atr_7'] = ta.atr(df['high'], df['low'], df['close'], 7)

    # HA Candle Calculation
    df['lac'] = (df['open'] + df['close'])/2 + (((df['close'] - df['open'])/(df['high'] - df['low'] + 1e-6)) * np.abs((df['close'] - df['open'])/2))
    df['habclose'] = ama(df['lac'].values, period=2, period_fast=2, period_slow=30)
    habopen = np.zeros(len(df))
    habopen[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2.0
    for i in range(1, len(df)):
        habopen[i] = (habopen[i - 1] + df['habclose'].iloc[i - 1]) / 2.0
    df['habopen'] = habopen
    df['habhigh'] = df[['high', 'habopen']].join(pd.DataFrame(df['habclose'])).max(axis=1)
    df['hablow']  = df[['low', 'habopen']].join(pd.DataFrame(df['habclose'])).min(axis=1)
    df['lac_sym'] = (df['open'] + df['close'])/2 - (((df['close'] - df['open'])/(df['high'] - df['low'] + 1e-6)) * np.abs((df['close'] - df['open'])/2))

    # Smooth HA High/Low
    df['jsmooth_habhigh'] = jsmooth(df['habhigh'].values, Smooth, Pow)
    df['jsmooth_hablow']  = jsmooth(df['hablow'].values, Smooth, Pow)
    df['s_habhigh'] = (ta.ema(pd.Series(df['jsmooth_habhigh']), length=HA_ma_length) + ta.wma(pd.Series(df['jsmooth_habhigh']), length=HA_ma_length)) / 2
    df['s_hablow']  = ta.ema(pd.Series(df['jsmooth_hablow']), length=HA_ma_length)

    # Fast MA Crossover from JSmooth of HA close/open
    jsmooth_habclose = jsmooth(df['habclose'], Smooth, Pow)
    jsmooth_habopen  = jsmooth(df['habopen'], Smooth, Pow)
    df['MA1'] = ta.ema(pd.Series(jsmooth_habclose), length=1)
    df['MA2'] = ta.ema(pd.Series(jsmooth_habopen), length=1)
    bullishCross = (df['MA1'].shift(1) < df['MA2'].shift(1)) & (df['MA1'] > df['MA2'])
    bearishCross = (df['MA1'].shift(1) > df['MA2'].shift(1)) & (df['MA1'] < df['MA2'])
    bullishCross = bullishCross.fillna(False)
    bearishCross = bearishCross.fillna(False)

    # Swing Pivots & Breakouts
    LBL = 2; LBR = 2
    ph = pivot(df['high'].tolist(), LBL, LBR, 'high')
    pl = pivot(df['low'].tolist(), LBL, LBR, 'low')
    df['ph'] = pd.Series(ph, index=df.index).shift(LBR)
    df['pl'] = pd.Series(pl, index=df.index).shift(LBR)
    df['ph_range'] = df['ph'].ffill()
    df['pl_range'] = df['pl'].ffill()
    multiplier_val = 0.3
    df['breakup'] = df['close'] >= (df['ph_range'] + multiplier_val * df['atr'])
    df['upwego'] = df['breakup'] & (df['breakup'] != df['breakup'].shift(1))
    df['breakdn'] = df['close'] <= (df['pl_range'] - multiplier_val * df['atr'])
    df['downwego'] = df['breakdn'] & (df['breakdn'] != df['breakdn'].shift(1))

    # Start Bar Pattern
    lookback = 5; volume_lookback = 30; volume_percentile = 50
    low_percentile = 75; range_percentile = 75; close_off_lows_percent = 50; prev_close_range = 75
    df['bar_range'] = df['high'] - df['low']
    df['macroLow'] = df['low'].rolling(volume_lookback, min_periods=1).min()
    df['macroHigh'] = df['high'].rolling(volume_lookback, min_periods=1).min()
    df['excessVolume'] = df['volume'] > (df['volume'].rolling(volume_lookback, min_periods=1).mean() + 3.0 * df['volume'].rolling(volume_lookback, min_periods=1).std())
    df['excessRange'] = df['bar_range'] > (df['bar_range'].rolling(volume_lookback, min_periods=1).mean() + 3.0 * df['bar_range'].rolling(volume_lookback, min_periods=1).std())
    
    # Create numeric condition_flagDn with proper index
    barCount = np.arange(len(df))
    condition_flagDn = np.where(barCount < HA_ma_length, True, (df['close'] < df['s_hablow']).values)
    condition_flagDn_series = pd.Series(condition_flagDn, index=df.index)
    
    df['volume_rank'] = df['volume'].rolling(lookback, min_periods=1).apply(lambda s: (s <= s[-1]).sum()/len(s)*100, raw=True)
    isHighVolume = (df['volume'] > 0.75 * df['volume'].rolling(volume_lookback, min_periods=1).mean()) & (df['volume'] > df['volume'].shift(1))
    hasHigherHigh = df['high'] > df['high'].shift(1)
    df['bar_range_rank'] = df['bar_range'].rolling(lookback, min_periods=1).apply(lambda s: (s <= s[-1]).sum()/len(s)*100, raw=True)
    noNarrowRange = df['bar_range_rank'] >= range_percentile
    closeintheHighs = (df['close'] - df['low']) >= ((close_off_lows_percent/100) * df['bar_range'])
    farPrevClose = (df['close'] - df['close'].shift(1)).abs() >= (df['bar_range'].shift(1) * (prev_close_range/100))
    newHighs = df['high'] >= 0.75 * df['high'].rolling(lookback, min_periods=1).max()
    isInthelows = (np.abs(df['low'] - df['macroLow']) < df['bar_range']) | (df['low'].rolling(volume_lookback, min_periods=1).apply(lambda s: (s <= s[-1]).sum()/len(s)*100, raw=True) >= low_percentile)
    # Create the base pattern condition
    start_bar_pattern = (
        isHighVolume & 
        hasHigherHigh & 
        noNarrowRange & 
        closeintheHighs & 
        farPrevClose & 
        (~df['excessRange']) & 
        (~df['excessVolume']) & 
        newHighs & 
        isInthelows
    )
    # This ensures we only get the first bar of a sequence of start bar patterns
    isStartBarPattern = start_bar_pattern & (~start_bar_pattern.shift(1).fillna(False))

    # At the Top / Bottom Conditions
    xh = 21
    highest_high_21 = df['high'].rolling(window=xh, min_periods=1).max()
    at_the_top = (df['high'] == highest_high_21) | (df['high'].shift(1) == highest_high_21) | (df['high'].shift(2) == highest_high_21)
    xl = 21
    lowest_low_21 = df['low'].rolling(window=xl, min_periods=1).min()
    at_the_bottom = (df['low'] == lowest_low_21) | (df['low'].shift(1) == lowest_low_21) | (df['low'].shift(2) == lowest_low_21)

    # Candle Calculations
    df['high_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['low_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['body_size'] = np.abs(df['open'] - df['close'])
    df['range_candle'] = df['high'] - df['low']
    insideBar = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    outsideBar = (df['high'] > df['high'].shift(1)) & (df['low'] < df['low'].shift(1))
    df['bear_power'] = df['high'] - df['close']
    df['bull_power'] = df['close'] - df['low']

    df['high_upper_wick'] = (df['high_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] > df['low_wick'])
    df['high_lower_wick'] = (df['low_wick'] >= wick_threshold * df['body_size']) & (df['high_wick'] < df['low_wick'])

    df['bearish_candle'] = df['high_upper_wick'] | (df['high_wick'] > (np.maximum(df['open'], df['close']) - df['low']))
    df['bullish_candle'] = df['high_lower_wick'] | (df['low_wick'] > (df['high'] - np.minimum(df['open'], df['close'])))

    highest_close_50 = df['close'].rolling(window=50, min_periods=1).max()
    highest_high_50 = df['high'].rolling(window=50, min_periods=1).max()
    bearishtop = (df['bearish_candle'] & (df['high'] > highest_close_50) &
                  ((df['high'] - df['close']) < df['atr_3']) &
                  (np.abs(df['high'] - highest_high_50) < df['atr_3']) &
                  (~insideBar) &
                  ((df['high'] - df['close']) > (df['close'] - df['low'])))
    
    lowest_low_50 = df['low'].rolling(window=50, min_periods=1).min()
    bullishbottom = (df['bullish_candle'] & (df['low'] == lowest_low_50) & ((df['high'] - df['low']) < df['atr_7']))

    df['bearish_top'] = bearishtop
    df['bullish_bottom'] = bullishbottom

    # Pin Signals
    df['bearishtop_low'] = df['low'].where(bearishtop).ffill()
    pin_down = (df['close'] < df['bearishtop_low']) & (bars_since(bearishtop.fillna(False)) < 4) & (~outsideBar)
    pin_down_cond = pin_down & (pin_down != pin_down.shift(1))

    df['bullishbottom_high'] = df['high'].where(bullishbottom).ffill()
    pin_up = (df['close'] > df['bullishbottom_high']) & (df['close'] > df['bullishbottom_high'].shift(1)) & (bars_since(bullishbottom.fillna(False)) < 4) & (~outsideBar)
    pin_up_cond = pin_up & (pin_up != pin_up.shift(1))

    barclosinginthehighs = ((df['high'] - df['close']) < (df['close'] - df['low'])) & (((df['close'] - df['low']) > 0.4 * (df['high'] - df['low']))) & (df['range_candle'] < df['range_candle'].rolling(window=50, min_periods=1).mean())

    atr_trend = df['atr'] > atr_trend_threshold * df['close']

    BullishEngulfing = (df['open'].shift(1) > df['close'].shift(1)) & (df['close'] > df['open']) & (df['close'] >= df['open'].shift(1)) & ((df['close'] - df['open']) > (df['open'].shift(1) - df['close'].shift(1)))
    df['BullishEngulfing'] = BullishEngulfing
    BearishEngulfing = (df['close'].shift(1) > df['open'].shift(1)) & (df['open'] > df['close']) & (df['open'] >= df['close'].shift(1)) & (df['open'].shift(1) >= df['close']) & ((df['open'] - df['close']) > (df['close'].shift(1) - df['open'].shift(1)))
    df['BearishEngulfing'] = BearishEngulfing

    sum_low_wick = df['low_wick'].shift(2) + df['low_wick'].shift(1) + df['low_wick']
    bullish_engulf_reversal = (sum_low_wick > df['atr_3']) & BullishEngulfing & (~outsideBar)
    bearish_engulf_reversal = (BearishEngulfing & (df['range_candle'] > 1.5 * df['range_candle'].shift(1)) & (df['high'].shift(1) == df['high'].rolling(window=21, min_periods=1).max())) | (outsideBar & at_the_top & (df['close'] < df['close'].shift(1)) & ((df['high'] - df['close']) > 0.25 * df['range_candle']))

    hl2 = (df['high'] + df['low']) / 2
    df['low_perc'] = df['low'].rolling(window=50, min_periods=1).apply(lambda s: percentile_rank_series(pd.Series(s)), raw=False)
    isBullishEngulfing_atlows = (BullishEngulfing &
                                 (df['high'] < df['high'].rolling(window=5, min_periods=1).max()) &
                                 (df['high'] > df['high'].shift(1)) &
                                 (df['high'] > df['high'].shift(2)) &
                                 (df['close'] > hl2.shift(2)) &
                                 (df['low'] < df['s_hablow']) &
                                 (pd.concat([df['MA1'], df['MA2']], axis=1).min(axis=1) > df['close']) &
                                 ((df['high_wick'] / (df['range_candle'] + 1e-6)) < 0.15) &
                                 (df['low_perc'] >= 30))

    barCount = np.arange(len(df))
    # Create boolean Series with proper index
    condition_flagUp_trend = pd.Series(
        np.where(barCount < HA_ma_length, True, df['close'] > df['s_habhigh'] + 0.1 * df['atr_7']),
        index=df.index
    ).astype(bool)
    
    # Convert the upwego series to boolean and handle NaN values
    upwego_bool = df['upwego'].fillna(False)
    upwego_shift1 = df['upwego'].shift(1).fillna(False)
    upwego_shift2 = df['upwego'].shift(2).fillna(False)
    upwego_shift3 = df['upwego'].shift(3).fillna(False)
    
    # Create flagUp_trend condition with proper Series alignment
    flagUp_trend = (condition_flagUp_trend & 
                    atr_trend & 
                    (upwego_bool | upwego_shift1 | upwego_shift2 | upwego_shift3) & 
                    (df['MA1'] > df['MA2']) & 
                    (np.abs(df['habclose'].shift(1) - df['habopen'].shift(1)) < np.abs(df['habclose'] - df['habopen'])))

    flagUp_candles = (df['high'] > df['high'].shift(1)) & ((df['high'] - df['close']) < (df['close'] - df['low'])) & (~bearishtop) & (~df['BearishEngulfing'])

    flagUp = (((flagUp_trend) | (pin_up_cond) | (bullish_engulf_reversal) |
              (outsideBar & (df['close'] > df['open']) & (df['high'] < df['high'].rolling(window=21, min_periods=1).max()) & (df['close'] < df['close'].rolling(window=21, min_periods=1).max())) |
              (isBullishEngulfing_atlows) | (isStartBarPattern)) & flagUp_candles)

    # Properly calculate bars_since_bearish_cross as numeric Series with same index
    bearish_cross_numeric = bearishCross.fillna(False)
    bars_since_bearish_cross = pd.Series(
        np.array([0 if bearish_cross_numeric.iloc[max(0, i-5):i+1].any() else 6 
                  for i in range(len(df))]),
        index=df.index
    )
    
    # For safety, explicitly create Series for each condition with matching index
    ma_check = df['MA1'] < df['MA2']
    bars_check = bars_since_bearish_cross <= 5
    bullish_check = ~BullishEngulfing
    hammer_check = ~df.get('hammer', pd.Series(False, index=df.index))
    outside_check = ~outsideBar
    
    # Combine with proper Series alignment
    flagDn_trend = (condition_flagDn_series.astype(bool) & 
                   ma_check & 
                   bars_check & 
                   bullish_check & 
                   hammer_check & 
                   outside_check)

    reversal = at_the_top & ((np.abs(df['open'] - df['close']) / (df['range_candle'] + 1e-6)) > 0.6) & (df['low'] < df['low'].shift(2)) & (df['low'] < df['low'].shift(1)) & (~outsideBar) & ((df['bear_power']) > (df['bull_power']))

    crossunder_condition = (df['close'].shift(1) >= df['s_hablow'].shift(1)) & (df['close'] < df['s_hablow'])
    stoploss = crossunder_condition & (df['close'] < df['open'].shift(1)) & (df['low'] != df['low'].rolling(window=50, min_periods=1).min())

    range_break = df['downwego'] & (df['range_candle'] > df['atr_4']) & ((df['close'] - df['high_wick']) < df['low'].shift(1)) & (df['low'] != df['low'].rolling(window=20, min_periods=1).min())

    # Add stoploss column explicitly for confirmation_regime
    df['stoploss'] = stoploss
    df['range_break'] = range_break
    df['reversal'] = reversal
    
    flagDown = stoploss | pin_down_cond | range_break | reversal | bearish_engulf_reversal | (outsideBar & at_the_top & (df['close'] < df['close'].shift(1)) & ((df['high'] - df['close']) > 0.25 * df['range_candle']))

    # --- Prepare Output ---
    df['bearish_top'] = bearishtop
    df['bullish_bottom'] = bullishbottom

    df_datas = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df_datas['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    df_datas['sma_200'] = df['close'].rolling(window=200, min_periods=1).mean()
    df_datas['atr_7'] = df['atr_7']
    df_datas['hlc3'] = (df['high'] + df['low'] + df['close']) / 3

    df_datas['ha_close'] = df['habclose']
    df_datas['ha_open'] = df['habopen']
    df_datas['sm_ha_high'] = df['s_habhigh']
    df_datas['sm_ha_low'] = df['s_hablow']

    df_datas['flagUp'] = flagUp
    df_datas['flagDown'] = flagDown
    df_datas['trend_bull_signal'] = flagUp_trend
    df_datas['trend_bear_signal'] = flagDn_trend
    df_datas['pin_up_cond'] = pin_up_cond
    df_datas['pin_down_cond'] = pin_down_cond
    df_datas['bullish_engulf_reversal'] = bullish_engulf_reversal
    df_datas['bearish_engulf_reversal'] = bearish_engulf_reversal
    df_datas['isBullishEngulfing_atlows'] = isBullishEngulfing_atlows
    df_datas['isStartBarPattern'] = isStartBarPattern
    df_datas['outsideBar'] = outsideBar
    df_datas['at_the_top'] = at_the_top

    df_datas['bearish_top'] = df['bearish_top']
    df_datas['bullish_bottom'] = df['bullish_bottom']
    
    # Add these to df_datas for the confirmation_regime function
    df_datas['stoploss'] = stoploss
    df_datas['range_break'] = range_break
    df_datas['reversal'] = reversal

    df_datas['lac'] = df['lac']
    df_datas['lac_sym'] = df['lac_sym']

    return df_datas, error
