# scanner/__init__.py
# Volume thresholds for different timeframes (in USD)
VOLUME_THRESHOLDS = {
    "1w": 300000,  # Weekly
    "2d": 100000,  # 2-day
    "1d": 50000,   # Daily
    "4h": 20000    # 4-hour
}

# Import after defining VOLUME_THRESHOLDS to avoid circular imports
from .main import run_scanner