# strategies/test_bar.py
def get_params():
    return {
        # Basic indicators
        'lookback': 14,
        'direction_opt': "Down",
        'bar_type_opt': "None",
        'spread_opt': "None",
        'spread_std': 1.0,
        'spread_abnormal_std': 99.0,
        'momentum_opt': "None",
        'momentum_std': 0.5,
        'volume_opt': "None",
        'volume_std': 1.0,
        'volume_abnormal_std': 99.0,
        'close_opt': "None",
        'use_volume_pct': True,
        'volume_pct_threshold': 0.20,
        'use_spread_pct': False,
        'spread_pct_threshold': 0.10,

        # Macro parameters
        'macro_opt': "None",
        'macro_method': "Combined (Strict)",
        'v1_macro_short_lookback': 7,
        'v1_macro_medium_lookback': 23,
        'v1_macro_long_lookback': 50,
        'v1_macro_percentile': 10.0,
        'v2_macro_short_lookback': 8,
        'v2_macro_medium_lookback': 28,
        'v2_macro_long_lookback': 48,
        'v2_macro_percentile': 25.0,

        # Breakout Close parameters
        'use_breakout_close': False,
        'breakout_close_percent': 30.0,

        # Arctangent Ratio condition
        'use_arctangent_ratio': False,
        'arctangent_ratio_threshold': 1.0,

        # High Breakout parameters
        'use_high_breakout': False,
        'high_breakout_lookback': 10,
        'high_breakout_count_percent': 10,

        # Test bar specific parameters (aligned with direct script)
        'test_bar_volume_ratio': 0.8,      # Stricter: volume < 1/2 previous
        'test_bar_spread_ratio': 0.5,      # Stricter: spread < 1/2 previous
        'test_bar_breakout_lookback': 5,   # Stricter: 5-bar breakout
        'test_bar_close_position': 0.65,   # Stricter: close in top 25%
        'is_test_bar_strategy': True,
    }