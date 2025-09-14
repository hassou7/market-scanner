# custom_strategies/__init__.py

"""
Custom trading strategies for cryptocurrency market analysis.

This module provides various pattern detection strategies including:
- Volume surge detection
- Weak uptrend detection  
- Pin down pattern detection
- Confluence signal detection
- Consolidation pattern detection
- Consolidation breakout detection
- Channel breakout detection
- Wedge breakout detection
- 50sma breakout
- Trend breakout (from HBS indicator vX)
- Pin up pattern detection (from HBS indicator vX)
"""

# Import all strategy detection functions
from .volume_surge import detect_volume_surge
from .weak_uptrend import detect_weak_uptrend  
from .pin_down import detect_pin_down
from .confluence import detect_confluence
from .consolidation import detect_consolidation
from .channel import detect_channel
from .consolidation_breakout import detect_consolidation_breakout
from .channel_breakout import detect_channel_breakout
from .wedge_breakout import detect_wedge_breakout
from .sma50_breakout import detect_sma50_breakout
from .trend_breakout import detect_trend_breakout
from .pin_up import detect_pin_up

# Export all functions for easy import
__all__ = [
    'detect_volume_surge',
    'detect_weak_uptrend', 
    'detect_pin_down',
    'detect_confluence',
    'detect_consolidation',
    'detect_channel',
    'detect_consolidation_breakout',
    'detect_channel_breakout',
    'detect_wedge_breakout',
    'detect_sma50_breakout'
    'detect_trend_breakout',
    'detect_pin_up'
    
]