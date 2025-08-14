# Export the main strategy functions


"""
Custom Strategies Package

This package contains custom pattern detection strategies for the cryptocurrency scanner.
Each strategy implements a specific trading pattern or market condition detection algorithm.
"""

from .volume_surge import detect_volume_surge
from .weak_uptrend import detect_weak_uptrend
from .pin_down import detect_pin_down
from .confluence import detect_confluence
from .consolidation import detect_consolidation

__all__ = [
    'detect_volume_surge',
    'detect_weak_uptrend', 
    'detect_pin_down',
    'detect_confluence',
    'detect_consolidation'
]