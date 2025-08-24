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
"""

# Import all strategy detection functions
from .volume_surge import detect_volume_surge
from .weak_uptrend import detect_weak_uptrend  
from .pin_down import detect_pin_down
from .confluence import detect_confluence
from .consolidation import detect_consolidation
from .consolidation_breakout import detect_consolidation_breakout
from .channel_breakout import detect_channel_breakout
from .sma50_breakout import detect_sma50_breakout

# Export all functions for easy import
__all__ = [
    'detect_volume_surge',
    'detect_weak_uptrend', 
    'detect_pin_down',
    'detect_confluence',
    'detect_consolidation',
    'detect_consolidation_breakout',
    'detect_channel_breakout',
    'detect_sma50_breakout'
]