# strategies/loaded_bar.py

def get_params():
    return {
        # Basic indicators
        'lookback': 23, 
        'direction_opt': "None",
        'bar_type_opt': "New Low or Outside Bar",
        'spread_opt': "None",
        'spread_std': 0.5,
        'spread_abnormal_std': 4.0,
        'momentum_opt': "None",
        'momentum_std': 0.5,
        'volume_opt': "High",
        'volume_std': 1.5,
        'volume_abnormal_std': 4.5,
        'close_opt': "In Highs",
        
        # Macro parameters
        'macro_opt': "Macro Low",
        'macro_method': "Count Based (V2)",
        
        # V1 (Price Based) parameters
        'v1_macro_short_lookback': 7,
        'v1_macro_medium_lookback': 23,
        'v1_macro_long_lookback': 50,
        'v1_macro_percentile': 10.0,
        
        # V2 (Count Based) parameters
        'v2_macro_short_lookback': 7,
        'v2_macro_medium_lookback': 13,
        'v2_macro_long_lookback': 23,
        'v2_macro_percentile': 15.0,
        
        # Breakout Close parameters
        'use_breakout_close': False,
        'breakout_close_percent': 30.0,

        # New: Close within prev range (higher than prev low)
        'use_close_within_prev': True,  # Set to True to enable

        # New Arctangent Ratio condition
        'use_arctangent_ratio': False,  # Optional
        'arctangent_ratio_threshold': 1.0,
        
        # High Breakout parameters
        'use_high_breakout': False,  # Enable high breakout detection for breakout_bar strategy
        'high_breakout_lookback': 10,
        'high_breakout_count_percent': 10
    }