# strategies/stop_bar.py
def get_params():
    return {
        # Basic indicators
        'lookback': 50,
        'direction_opt': "Up",
        'bar_type_opt': "New Low or Outside Bar",
        'spread_opt': "None",
        'spread_std': 1.0,
        'spread_abnormal_std': 4.0,
        'momentum_opt': "None",
        'momentum_std': 0.5,
        'volume_opt': "High",
        'volume_std': 1.5,
        'volume_abnormal_std': 6.0,
        'close_opt': "in Highs",
        
        # Macro parameters
        'macro_opt': "Macro Low",
        'macro_method': "Count Based (V2)",
        
        # V1 (Price Based) parameters
        'v1_macro_short_lookback': 5,
        'v1_macro_medium_lookback': 21,
        'v1_macro_long_lookback': 21,
        'v1_macro_percentile': 10.0,
        
        # V2 (Count Based) parameters
        'v2_macro_short_lookback': 20,
        'v2_macro_medium_lookback': 20,
        'v2_macro_long_lookback': 20,
        'v2_macro_percentile': 4.0,
        
        # Breakout Close parameters
        'use_breakout_close': False,
        'breakout_close_percent': 80.0,

        # New Arctangent Ratio condition
        'use_arctangent_ratio': False,  # Optional
        'arctangent_ratio_threshold': 1.0,

        # High Breakout parameters
        'use_high_breakout': False,  # Enable high breakout detection for breakout_bar strategy
        'high_breakout_lookback': 20,
        'high_breakout_count_percent': 80
    }