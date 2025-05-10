# strategies/loaded_bar.py
def get_params():
    return {
        # Basic indicators
        'lookback': 50, 
        'direction_opt': "None",
        'bar_type_opt': "None",
        'spread_opt': "Narrow",
        'spread_std': 0.5,
        'spread_abnormal_std': 2.0,
        'momentum_opt': "None",
        'momentum_std': 0.5,
        'volume_opt': "Abnormal",
        'volume_std': 2.0,
        'volume_abnormal_std': 3.0,
        'close_opt': "Off Lows",
        
        # Macro parameters
        'macro_opt': "None",
        'macro_method': "Count Based (V2)",
        
        # V1 (Price Based) parameters
        'v1_macro_short_lookback': 7,
        'v1_macro_medium_lookback': 23,
        'v1_macro_long_lookback': 50,
        'v1_macro_percentile': 10.0,
        
        # V2 (Count Based) parameters
        'v2_macro_short_lookback': 8,
        'v2_macro_medium_lookback': 28,
        'v2_macro_long_lookback': 48,
        'v2_macro_percentile': 25.0,
        
        # Breakout Close parameters
        'use_breakout_close': False,
        'breakout_close_percent': 30.0,

        # New Arctangent Ratio condition
        'use_arctangent_ratio': False,  # Optional
        'arctangent_ratio_threshold': 1.0,
        
        # High Breakout parameters
        'use_high_breakout': False,  # Enable high breakout detection for breakout_bar strategy
        'high_breakout_lookback': 10,
        'high_breakout_count_percent': 10
    }