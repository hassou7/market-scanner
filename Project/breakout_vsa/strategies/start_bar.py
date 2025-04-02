"""
Start Bar VSA Pattern Strategy Parameters

This module defines the parameters for the Start Bar VSA pattern detection.
"""

def get_params():
    """
    Get the parameters for Start Bar VSA pattern detection.
    
    Returns:
        dict: Parameters dictionary for Start Bar detection
    """
    return {
        # Basic parameters for start bar detection
        'lookback': 5,
        'volume_lookback': 30,
        'volume_percentile': 50,
        'low_percentile': 75,
        'range_percentile': 75,
        'close_off_lows_percent': 50,
        'prev_close_range': 75,
        
        # Use start bar specific detection
        'is_start_bar': True,
        
        # Dummy parameters needed by vsa_detector
        'direction_opt': "None",
        'bar_type_opt': "None",
        'spread_opt': "None",
        'momentum_opt': "None",
        'volume_opt': "None",
        'close_opt': "None",
        'macro_opt': "None",
        'macro_method': "None",
        'use_arctangent_ratio': False,
        'arctangent_ratio_threshold': 1.0,
        'use_high_breakout': True,  # Enable high breakout detection for breakout_bar strategy
        'high_breakout_lookback': 20,
        'high_breakout_count_percent': 80
    }