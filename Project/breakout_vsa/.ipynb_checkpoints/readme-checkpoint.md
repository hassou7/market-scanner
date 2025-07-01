# Breakout Bar + VSA Indicator

This package implements the Breakout Bar + VSA (Volume Spread Analysis) indicator for technical analysis of financial markets. The indicator combines bar pattern recognition with volume analysis to identify potential breakout opportunities.

project/
├── breakout_vsa/
│   ├── init.py                # Main imports
│   ├── core.py                    # Core VSA detector functions
│   ├── helpers.py                 # Helper functions for indicators
│   └── strategies/
│       ├── init.py            # Strategy imports
│       ├── breakout_bar.py        # Breakout Bar strategy parameters
│       ├── stop_bar.py            # Stop Bar strategy parameters
│       └── reversal_bar.py        # Reversal Bar strategy parameters
├── exchanges/
│   ├── init.py                # Exchange imports
│   ├── binance_spot.py            # Binance spot data fetcher
│   ├── binance_perps.py           # Binance perpetuals data fetcher
│   ├── kucoin.py                  # KuCoin data fetcher
│   └── mexc.py                    # MEXC data fetcher
├── scanner.py                     # Main scanner implementation
└── utils/
├── init.py
└── config.py                  # Configuration values


## Features

- Identifies potential breakout bars based on various configurable conditions
- Supports two different macro detection methods:
  - Price-based (V1): Using price levels relative to historical ranges
  - Count-based (V2): Using counts of lower lows/higher highs
  - Combined (Strict): Requiring both conditions to be met
- Analyzes bar characteristics: spread, volume, momentum, close position
- Works with standard OHLCV (Open, High, Low, Close, Volume) data

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/breakout_bar_vsa.git

# Navigate to the directory
cd breakout_bar_vsa

# Install the package
pip install -e .
```

## Usage

```python
import pandas as pd
from breakout_vsa import breakout_bar_vsa

# Load your OHLCV data (example)
df = pd.read_csv('your_data.csv')

# Apply the indicator
breakout_signals = breakout_bar_vsa(df)

# Show signal dates
signal_dates = df.index[breakout_signals]
print("Breakout signal dates:", signal_dates)
```

## Configuration

The indicator uses a set of fixed parameters that can be modified in the `breakout_bar_vsa` function:

- Basic parameters:
  - `lookback`: Lookback period for basic calculations
  - `direction_opt`: Bar direction requirement ("None", "Up", "Down")
  - `bar_type_opt`: Bar type requirement ("None", "New High", "New Low", "New High or Outside Bar", "New Low or Outside Bar",  etc.)
  - `spread_opt`: Spread requirement ("None", "Wide", "Narrow", "Abnormal")
  - `volume_opt`: Volume requirement ("None", "High", "Low", "Abnormal", "Not Low")
  - `close_opt`: Close position requirement ("None", "Off Lows", "In Lows", "In Middle", etc.)

- Macro detection parameters:
  - `macro_opt`: Macro condition requirement ("None", "Macro Low", "Macro High")
  - `macro_method`: Macro detection method ("Price Based (V1)", "Count Based (V2)", "Combined (Strict)")
  - V1 parameters: Short/medium/long lookbacks and percentile threshold
  - V2 parameters: Short/medium/long lookbacks and percentile threshold

- Breakout close parameters:
  - `use_breakout_close`: Whether to require close above breakout threshold
  - `breakout_close_percent`: Percentile for breakout threshold

## Structure

The code is organized into modular components:

- `core.py`: Main function that orchestrates the indicator calculation
- `helpers.py`: Helper functions for different aspects of the calculation:
  - Basic indicators (spread, volume, momentum, etc.)
  - Price-based macro detection (V1)
  - Count-based macro detection (V2)
  - Condition filtering

## Example

See `example.py` for a complete example of how to use the indicator with sample data.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original PineScript implementation by hassou7
- Converted to Python by [Your Name]