import pandas as pd
import numpy as np

def detect_weak_uptrend(df, min_weaknesses=3):
    """
    Detects market weakness patterns on a rolling window basis.
    Weakness 3 (momentum loss) is a mandatory condition among the min_weaknesses.
    
    Parameters:
    df (pandas.DataFrame): DataFrame with columns 'open', 'high', 'low', 'close', 'volume'
    min_weaknesses (int): Minimum number of distinct weakness types required
    
    Returns:
    bool, dict: Boolean indicating if weakness was detected, and dictionary with details
    """
    if len(df) < 7:
        # Need at least 7 bars for proper analysis (6 for the window + 1 preceding bar)
        return False, {}
    
    # We'll analyze the previous candle (-2) with lookback window
    # Check for the last 7 bars of the dataframe
    window = df.iloc[-7:].copy()
    
    if len(window) < 7:
        return False, {}
    
    # Extract data for analysis
    closes = window['close'].values
    highs = window['high'].values
    lows = window['low'].values
    volumes = window['volume'].values
    spreads = highs - lows
    
    # Initialize set for weaknesses found
    found_weaknesses = set()
    has_w3 = False  # Track if W3 (mandatory pattern) was present
    weakness_details = {}
    
    # Check Weakness 1: An up bar with a new high and volume less than the previous bar's volume
    # This suggests diminishing buying strength despite higher prices
    for j in range(2, 6):  # Analyzing within window
        if closes[j] > closes[j-1] and highs[j] > highs[j-1] and volumes[j] < volumes[j-1]:
            found_weaknesses.add('W1')
            weakness_details['W1'] = True
            break
    
    # Check Weakness 2: Two conditions:
    # 1. An up bar with less spread than the previous bar, OR
    # 2. An up bar with spread within +/- 10% of the previous bar's spread
    # Both suggest less conviction in the upward move
    for j in range(2, 6):  # Analyzing within window
        if closes[j] > closes[j-1] and (
            spreads[j] < spreads[j-1] or
            (spreads[j] <= spreads[j-1] * 1.10 and spreads[j] >= spreads[j-1] * 0.90)
        ):
            found_weaknesses.add('W2')
            weakness_details['W2'] = True
            break
    
    # Check Weakness 3: Several patterns showing loss of momentum
    # Part 1: Up bar following another up bar, but with smaller close-to-close distance
    # This suggests diminishing upward momentum
    for j in range(3, 6):  # Need 3 bars, analyzing within window
        if (closes[j] > closes[j-1] and 
            closes[j-1] > closes[j-2] and 
            (closes[j] - closes[j-1]) < (closes[j-1] - closes[j-2])):
            found_weaknesses.add('W3')
            weakness_details['W3'] = True
            has_w3 = True
            break
    
    # Part 2: Down bar that made a new high, with smaller absolute close-to-close distance
    # This suggests resistance after testing higher levels
    if not has_w3:
        for j in range(3, 6):  # Need 3 bars, analyzing within window
            if (closes[j] < closes[j-1] and 
                highs[j] > highs[j-1] and 
                abs(closes[j] - closes[j-1]) < abs(closes[j-1] - closes[j-2])):
                found_weaknesses.add('W3')
                weakness_details['W3'] = True
                has_w3 = True
                break
    
    # Part 3: Up bar where close-to-close distance is <= 25% of previous bar's range
    # This suggests minimal upward progress relative to the previous price action
    if not has_w3:
        for j in range(2, 6):  # Analyzing within window
            if (closes[j] > closes[j-1] and 
                (closes[j] - closes[j-1]) <= 0.25 * spreads[j-1]):
                found_weaknesses.add('W3')
                weakness_details['W3'] = True
                has_w3 = True
                break
    
    # Compute statistics for Weakness 4 and 5 using the 5 bars of the window
    window_volumes = volumes[1:6]  # Use window
    window_spreads = spreads[1:6]  # Use window
    
    mean_volume = np.mean(window_volumes)
    stdv_volume = np.std(window_volumes, ddof=1)
    mean_spread = np.mean(window_spreads)
    stdv_spread = np.std(window_spreads, ddof=1)
    
    # Check Weakness 4: A bar with volume exceeding 2 standard deviations above the mean
    # This suggests climactic or exhaustion activity
    for j in range(1, 6):  # Analyzing within window
        if window_volumes[j-1] > mean_volume + 2 * stdv_volume:
            found_weaknesses.add('W4')
            weakness_details['W4'] = True
            break
    
    # Check Weakness 5: A bar with exceptionally wide spread, closing in the lower 75% of its range
    # This suggests selling pressure after a wide-range bar
    for j in range(1, 6):  # Analyzing within window
        if (window_spreads[j-1] > mean_spread + 2 * stdv_spread and 
            window_spreads[j-1] > 0 and 
            (closes[j] - lows[j]) / window_spreads[j-1] <= 0.75):
            found_weaknesses.add('W5')
            weakness_details['W5'] = True
            break
    
    # Final check: At least min_weaknesses patterns AND W3 is one of them (momentum loss is mandatory)
    weakness_detected = len(found_weaknesses) >= min_weaknesses and has_w3
    
    if not weakness_detected:
        return False, {}
    
    # Prepare result with all weaknesses detected
    prev_volume = df['volume'].iloc[-2]
    prev_close = df['close'].iloc[-2]
    volume_in_usd = prev_volume * prev_close

    # Calculate volume ratio
    volume_ratio = df['volume'].iloc[-2] / df['volume'].iloc[-10:-2].mean()
    
    result = {
        'date': df.index[-2],
        'close': prev_close,
        'volume_usd': volume_in_usd,
        'volume_ratio': volume_ratio,
        'total_patterns': len(found_weaknesses),
        'W1': 'W1' in found_weaknesses,
        'W2': 'W2' in found_weaknesses,
        'W3': 'W3' in found_weaknesses, 
        'W4': 'W4' in found_weaknesses,
        'W5': 'W5' in found_weaknesses
    }
    
    return weakness_detected, result