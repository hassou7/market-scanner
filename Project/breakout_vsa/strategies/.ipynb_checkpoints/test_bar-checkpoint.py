# strategies/test_bar.py
def get_params():
    """
    Calculate the Test Bar pattern based on these conditions:
    - Inside bar
    - Down bar  
    - Closing off the lows (close >= 65% of spread from low)
    - Lower volume than previous bar (less than 40%)
    - Lowest volume in the last 3 bars
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