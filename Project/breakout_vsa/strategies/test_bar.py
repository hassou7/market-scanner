# strategies/test_bar.py
def get_params():
    """
    Test Bar strategy parameters.
    Note: The new test bar implementation uses hardcoded criteria and doesn't 
    use these parameters, but they are kept for consistency with the framework.
    
    The Test Bar pattern detects:
    - Inside bar
    - Down bar (close < open)
    - Close >= 35% of spread from low
    - Volume < 40% of previous bar
    - Lowest volume in last 3 bars
    - Previous bar: up + close > 75% of range
    - Previous bar volume > SMA(3) of volume
    - Previous bar NOT inside bar
    """
    return {
        # These parameters are not used by the new test bar implementation
        # but are kept for framework consistency
        'lookback': 3,  # Only used for volume SMA calculation
        'direction_opt': "None",
        'bar_type_opt': "None", 
        'spread_opt': "None",
        'momentum_opt': "None",
        'volume_opt': "None",
        'close_opt': "None",
        'macro_opt': "None",
        'use_breakout_close': False,
        'use_arctangent_ratio': False,
        'use_high_breakout': False,
    }