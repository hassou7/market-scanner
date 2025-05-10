# strategies/reversal_bar.py
# A bar in the extreme highs, made a new high and closed in the lows with wide spread at high volume. Momentum is not important. It can be an up or down bar. 
def get_params():
    return {
        # Basic indicators
        'lookback': 14,
        'direction_opt': "None",
        'bar_type_opt': "New High or Outside Bar",
        'spread_opt': "Wide",
        'spread_std': 0.5,
        'spread_abnormal_std': 4.0,
        'momentum_opt': "None",
        'momentum_std': 0.5,
        'volume_opt': "High",
        'volume_std': 0.5,
        'volume_abnormal_std': 3.0,
        'close_opt': "In Lows",
        
        # Macro parameters
        'macro_opt': "Macro High",
        'macro_method': "Count Based (V2)",
        
        # V1 (Price Based) parameters
        'v1_macro_short_lookback': 14,
        'v1_macro_medium_lookback': 34,
        'v1_macro_long_lookback': 50,
        'v1_macro_percentile': 5.0,
        
        # V2 (Count Based) parameters
        'v2_macro_short_lookback': 8,
        'v2_macro_medium_lookback': 28,
        'v2_macro_long_lookback': 48,
        'v2_macro_percentile': 20.0,
        
        # Breakout Close parameters
        'use_breakout_close': False,
        'breakout_close_percent': 30.0,

        # New Arctangent Ratio condition
        'use_arctangent_ratio': False,  # Optional
        'arctangent_ratio_threshold': 1.0,

        # High Breakout parameters
        'use_high_breakout': False,  # Enable high breakout detection for breakout_bar strategy
        'high_breakout_lookback': 20,
        'high_breakout_count_percent': 80
    }