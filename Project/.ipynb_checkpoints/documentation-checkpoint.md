# Cryptocurrency Market Scanner Documentation

A comprehensive market scanner for cryptocurrency exchanges that combines VSA (Volume Spread Analysis) strategies with custom pattern detection algorithms, featuring parallel processing and multi-timeframe analysis.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [VSA Strategies](#vsa-strategies)
8. [Custom Strategies](#custom-strategies)
9. [Parallel Scanning](#parallel-scanning)
10. [Multi-User Support](#multi-user-support)
11. [Adding New Exchanges](#adding-new-exchanges)
12. [Adding New Strategies](#adding-new-strategies)
13. [Troubleshooting](#troubleshooting)

## Project Overview

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms like volume surge, weak uptrend, pin down, confluence pattern detection, consolidation breakout detection, and hybrid breakout strategies.

The scanner supports multiple exchanges including Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit. It can analyze various timeframes (1w, 3d, 2d, 1d, 4h) and send notifications via Telegram to multiple users. The system now features **parallel processing** for enhanced performance across multiple exchanges and timeframes.

## Features

- **Multiple Exchange Support**: Scan Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit markets
- **Extended Timeframes**: Analyze 1w, 4d, 3d, 2d, 1d, and 4h timeframes
- **Parallel Processing**: Simultaneously scan multiple exchanges and timeframes for maximum efficiency
- **VSA Strategies**:
  - Breakout Bar for trend starts
  - Stop Bar for trend reversals
  - Reversal Bar for potential reversals
  - Start Bar for trend initiation
  - Loaded Bar for accumulation detection
  - Test Bar for support/resistance testing
- **Custom Strategies**:
  - Volume Surge detection
  - Weak Uptrend detection with 5 pattern types
  - Pin Down pattern for bearish continuation
  - **Confluence Signal** - multi-factor confirmation system
  - **Consolidation Breakout** - breakout from consolidation patterns
  - **HBS Breakout** - hybrid consolidation + confluence strategy
- **Telegram Integration**: Send alerts to multiple users and channels
- **Modular Architecture**: Easy to add new exchanges and strategies
- **Batch Processing**: Efficiently scan hundreds of markets in parallel
- **Volume Filtering**: Focus on markets with significant trading volume
- **Jupyter Notebook Interface**: Run scans interactively and visualize results
- **Cache Optimization**: Smart caching system to reduce API calls

## Project Structure

```
project/
├── breakout_vsa/               # VSA pattern detection logic
│   ├── __init__.py             # Main imports
│   ├── core.py                 # Core VSA detector functions
│   ├── helpers.py              # Helper functions for indicators
│   └── strategies/             # Strategy parameter files
│       ├── __init__.py
│       ├── breakout_bar.py     # Breakout Bar strategy parameters
│       ├── stop_bar.py         # Stop Bar strategy parameters
│       ├── reversal_bar.py     # Reversal Bar strategy parameters
│       ├── start_bar.py        # Start Bar strategy parameters
│       ├── loaded_bar.py       # Loaded Bar strategy parameters
│       └── test_bar.py         # Test Bar strategy parameters
├── custom_strategies/          # Custom pattern detection
│   ├── __init__.py             # Main imports
│   ├── volume_surge.py         # Volume surge detection
│   ├── weak_uptrend.py         # Weak uptrend detection
│   ├── pin_down.py             # Pin down pattern detection
│   ├── confluence.py           # Confluence signal detection
│   ├── consolidation.py        # Ongoing Consolidation box detection
│   └── consolidation_breakout.py  # NEW: Consolidation breakout detection
├── exchanges/                  # Exchange API clients
│   ├── __init__.py
│   ├── base_client.py          # Base exchange client class
│   ├── binance_futures_client.py  # Binance Perpetuals client
│   ├── binance_spot_client.py  # Binance Spot client
│   ├── bybit_client.py         # Bybit client
│   ├── gateio_client.py        # Gate.io client
│   ├── kucoin_client.py        # KuCoin client
│   └── mexc_client.py          # MEXC client
├── scanner/                    # Market scanning logic
│   ├── __init__.py
│   └── main.py                 # Scanner main functions with parallel support
├── utils/                      # Utility functions and configuration
│   ├── __init__.py
│   └── config.py               # Configuration values
├── run_parallel_scanner.py     # NEW: Parallel scanning engine
└── vsa_and_custom_scanner.ipynb  # Jupyter notebook interface
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crypto-scanner.git
cd crypto-scanner
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Required dependencies:
- pandas
- numpy
- asyncio
- aiohttp
- python-telegram-bot
- nest_asyncio (for Jupyter)
- tqdm
- jupyter (for notebook interface)

## Configuration

### Telegram Configuration

Edit `utils/config.py` to configure your Telegram bots and users:

```python
TELEGRAM_TOKENS = {
    "volume_surge": "7553154813:AAG4KU9eAEhSpFRgIgNR5vpG05mT8at4Udw",
    "start_trend": "7501317114:AAHqd8BYNqR81zWEHAuwQhKji1fOM9HxjdQ",
    "weakening_trend": "7837067804:AAE1H2XWMlwvogCdhQ7vJpufv6VpXaBFg8Q",
    "confluence": "8066329517:AAHVr6kufZWe8UqCKPfmsRhSPleNlt_7G-g"
}

TELEGRAM_USERS = {
    "default": {"name": "Houssem", "chat_id": "375812423"},
    "user1": {"name": "Samed", "chat_id": "2008960887"},
    "user2": {"name": "Moez", "chat_id": "6511370226"}, 
}

STRATEGY_CHANNELS = {
    "breakout_bar": "start_trend",
    "stop_bar": "start_trend",
    "reversal_bar": "weakening_trend",
    "volume_surge": "volume_surge",
    "weak_uptrend": "weakening_trend",
    "pin_down": "weakening_trend",
    "confluence": "confluence",
    "start_bar": "start_trend",
    "loaded_bar": "volume_surge",
    "test_bar": "weakening_trend",
    "consolidation": "start_trend",
    "consolidation_breakout": "start_trend",
    "hbs_breakout": "confluence"
}
```

### Volume Thresholds

Adjust volume thresholds for different timeframes in `utils/config.py`:

```python
# Volume thresholds (updated with new timeframes)
VOLUME_THRESHOLDS = {
    "1w": 300000,  # Weekly volume threshold in USD
    "4d": 200000,  # NEW: 4-day volume threshold in USD
    "3d": 150000,  # NEW: 3-day volume threshold in USD
    "2d": 100000,  # 2-day volume threshold in USD
    "1d": 50000,   # Daily volume threshold in USD
    "4h": 20000    # 4-hour volume threshold in USD
}
```

## Usage

### Parallel Scanning (NEW)

The scanner now supports parallel processing for maximum efficiency:

#### Single Timeframe, Multiple Exchanges

```python
from run_parallel_scanner import run_parallel_exchanges

# Run scan across all exchanges in parallel
result = await run_parallel_exchanges(
    timeframe="1d",
    strategies=["breakout_bar", "confluence", "consolidation_breakout"],
    exchanges=["binance_spot", "bybit_spot", "kucoin_spot"],  # Optional: specify exchanges
    users=["default"],
    send_telegram=True,
    min_volume_usd=None  # Use default thresholds
)
```

#### Multiple Timeframes, Multiple Exchanges (NEW)

```python
from run_parallel_scanner import run_parallel_multi_timeframes_all_exchanges

# Run scan across multiple timeframes and exchanges
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["3d", "4d", "1w"],  # NEW: Extended timeframe support
    strategies=["confluence", "consolidation_breakout", "hbs_breakout"],
    exchanges=None,  # Use all available exchanges
    users=["default"],
    send_telegram=True,
    min_volume_usd=None
)
```

### Command Line Usage

```bash
# Run parallel scan from command line
python run_parallel_scanner.py 1d "consolidation_breakout,confluence" "binance_spot,bybit_spot" "default" true
```

### Traditional Jupyter Notebook Usage

Start Jupyter and open the `vsa_and_custom_scanner.ipynb` notebook:

```bash
jupyter notebook
```

#### VSA-Based Scanning

```python
await run_scan(
    timeframe='4h', 
    strategy='breakout_bar', 
    exchange="binance_spot", 
    send_telegram=True,
    telegram_channel="start_trend",
    user_id="default"
)
```

#### Custom Strategy Scanning

```python
await run_custom_scan(
    exchange='binance_futures',
    timeframe='3d',  # NEW: 3-day timeframe support
    strategies=['volume_surge', 'consolidation_breakout', 'hbs_breakout'],  # NEW: consolidation strategies
    send_telegram=True
)
```

## VSA Strategies

### Breakout Bar

A breakout bar is characterized by:
- Strong volume (above average)
- Close near the high of the bar
- Range (high-low) is large
- Close is higher than the previous close

This pattern is often used to identify the start of a new trend.

### Stop Bar

A stop bar is characterized by:
- Strong volume (above average)
- Close near the low of the bar
- Range (high-low) is large
- Usually occurs in an uptrend, signaling potential reversal

This pattern suggests a potential trend reversal or correction.

### Reversal Bar

A reversal bar is characterized by:
- Strong volume (above average)
- Small body (close near open)
- Long lower wick in an uptrend (selling rejected)
- Long upper wick in a downtrend (buying rejected)

This pattern indicates potential exhaustion of the current trend and possible reversal.

### Start Bar

Identifies the beginning of a new trend with:
- Strong momentum indicators
- Volume confirmation
- Price action supporting trend initiation

### Loaded Bar

Detects accumulation phases with:
- High volume but narrow spread
- Potential for explosive moves
- Professional money accumulation

### Test Bar

Identifies support/resistance testing with:
- Volume analysis at key levels
- Price rejection patterns
- Confirmation of level strength

## Custom Strategies

### Volume Surge

Detects bars with abnormally high volume (typically 4+ standard deviations above average) and calculates a score based on price action and range. Useful for identifying significant market events and potential trend changes.

### Weak Uptrend

Identifies bars showing weakness in an uptrend by detecting 5 types of weakness patterns:
- W1: Higher high with lower volume (diminishing buying pressure)
- W2: Up bar with smaller/similar spread (less conviction)
- W3: Momentum loss (mandatory) - detected in three different ways
- W4: Excess volume (potential exhaustion)
- W5: Wide range with lower close (selling pressure)

### Pin Down

Detects a bearish continuation pattern where:
1. A bearish candle forms near a significant high (bearish top)
2. Within 3 bars, price breaks below the low of the bearish top candle
3. The pattern is NOT an outside bar

This pattern suggests continuation of a downtrend after a brief pullback.

### Confluence Signal

A sophisticated multi-factor confirmation system that combines:
- **High Volume Component**: Volume significantly above average
- **Spread Breakout Component**: Range expansion indicating volatility
- **Momentum Breakout Component**: Strong directional movement

The confluence detector calculates:
- Individual component scores
- Combined momentum score
- Close-off-low percentage
- Volume ratio analysis

Confluence signals are triggered when multiple components align, providing higher-probability trade setups.

**Key Features:**
- Checks both current and last closed bars
- Calculates comprehensive momentum scores
- Provides detailed component breakdown in alerts
- Suitable for trend confirmation and entry timing

### Consolidation Pattern

A robust pattern detection system for identifying periods of low volatility and price compression, often preceding breakouts or reversals. It combines multiple filters to detect tight trading ranges:

- **Bars Inside Component**: Requires a minimum number of bars (default: 4) fully contained within the lookback window's high-low range.
- **Range Height Component**: Limits the relative height of the range (default: ≤35% of average price) to ensure compression.
- **ATR Filter Component**: Ensures low volatility by requiring current ATR below a multiple (default: 0.9x) of its SMA.

The consolidation detector calculates:
- Rolling highest/lowest over lookback (default: 7 bars)
- Height percentage and bars inside count
- ATR conditions for volatility confirmation
- Box age, bounds (high/low/mid), and maturity status

Consolidation patterns are triggered on the rising edge of conditions, with boxes latched retroactively and extended until a close-based breakout, providing reliable setup identification.

**Key Features:**
- Checks both current and last closed bars
- Retroactive box drawing from detection window start
- Provides detailed box metrics (age, range bounds, mid) and condition breakdowns in alerts
- Suitable for spotting potential breakouts or reversals in ranging markets

### Consolidation Breakout (NEW)

An advanced breakout detection system that identifies when price breaks out of established consolidation patterns with channel confirmation. This strategy combines consolidation box detection with trend channel analysis to provide high-probability breakout signals.

**Detection Logic:**
1. **Consolidation Box Formation**: Identifies tight trading ranges using the same logic as the consolidation pattern
2. **Channel Analysis**: Uses Theil-Sen regression to fit trend channels through the consolidation data
3. **Breakout Confirmation**: Requires both box breakout AND channel breakout for signal generation

**Key Components:**
- **Box Breakout**: Price closes above/below the consolidation box boundaries
- **Channel Breakout**: Price exceeds the projected upper/lower channel bounds
- **Volume Confirmation**: Enhanced volume during breakout for additional validation
- **Direction Detection**: Clear identification of breakout direction (Up/Down)

**Signal Requirements:**
- Minimum data requirement: 23 bars for proper analysis
- Consolidation box with 4+ bars inside the range
- Range height ≤35% of average price (tight consolidation)
- ATR filter for low volatility confirmation
- Channel projection breakout for trend continuation

**Telegram Notifications Include:**
- Breakout direction with color-coded emojis (🟢 Up, 🔴 Down)
- Box metrics (age, high/low bounds, compression ratio)
- Volume analysis (ratio and USD volume)
- Channel breakout confirmation details

### HBS Breakout (NEW)

A sophisticated hybrid strategy that combines **Consolidation Breakout** and **Confluence Signal** detection for ultra-high probability trade setups. HBS stands for "Hybrid Breakout Strategy" and represents the confluence of multiple confirming factors.

**Strategy Logic:**
HBS signals are generated only when BOTH conditions are met simultaneously:
1. **Consolidation Breakout**: Price breaks out of a consolidation pattern with channel confirmation
2. **Confluence Signal**: Multiple technical factors align (volume, momentum, spread)

**Multi-Factor Confirmation:**
- **Structural Component**: Consolidation breakout provides price structure analysis
- **Volume Component**: Confluence ensures sufficient market participation
- **Momentum Component**: Confluence validates directional strength
- **Timing Component**: Both signals must fire within the same analysis window

**Enhanced Reliability:**
By requiring both consolidation breakout AND confluence confirmation, HBS significantly reduces false signals while maintaining sensitivity to genuine breakout opportunities. This dual-confirmation approach filters out:
- Low-volume breakouts (likely to fail)
- Breakouts without momentum confirmation
- Structural breaks without market participation

**Signal Characteristics:**
- **Very High Probability**: Dual confirmation significantly improves success rate
- **Lower Frequency**: More selective than individual strategies
- **Clear Direction**: Strong directional bias from breakout analysis
- **Volume Validated**: Ensures market participation behind the move

**Telegram Notifications Include:**
- Combined consolidation and confluence metrics
- Breakout direction and structural analysis
- Volume ratios and momentum scores
- Component breakdown showing which factors aligned

**Usage Recommendations:**
- Ideal for swing trading and position entries
- Excellent for automated trading systems requiring high-probability setups
- Suitable for risk-averse traders seeking confluence confirmation
- Best used on higher timeframes (4h, 1d, 1w) for reduced noise

## Parallel Scanning (NEW)

The scanner now features advanced parallel processing capabilities:

### Architecture Benefits

- **Concurrent Exchange Scanning**: Multiple exchanges scanned simultaneously
- **Multi-Timeframe Processing**: Sequential timeframe processing with cache optimization
- **Batch Processing**: Efficient symbol batching for rate limit management
- **Smart Caching**: Reduces redundant API calls across strategies
- **Progress Tracking**: Real-time progress updates for all operations

### Performance Features

- **Async/Await Implementation**: Non-blocking I/O operations
- **Connection Pooling**: Efficient HTTP connection management
- **Rate Limit Handling**: Automatic throttling and retry mechanisms
- **Memory Optimization**: Strategic cache clearing between timeframes
- **Error Resilience**: Graceful handling of individual exchange failures

### Usage Examples

#### Quick Single Exchange Scan
```python
# Fast scan of single exchange
result = await run_parallel_exchanges(
    timeframe="1d",
    strategies=["consolidation_breakout"],
    exchanges=["binance_spot"],
    users=["default"],
    send_telegram=True
)
```

#### Comprehensive Multi-Everything Scan
```python
# Complete market scan across all dimensions
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["4d", "3d", "2d", "1d"],  # NEW timeframes included
    strategies=["confluence", "consolidation_breakout", "hbs_breakout"],
    exchanges=None,  # All exchanges
    users=["default", "trader1", "analyst2"],
    send_telegram=True
)
```

## Multi-User Support

The system supports sending notifications to multiple users:

1. Add users to `TELEGRAM_USERS` in `utils/config.py`
2. For parallel scans, specify multiple users:
   ```python
   await run_parallel_exchanges(
       timeframe='2d',  # NEW: 2-day timeframe
       strategies=['consolidation_breakout', 'hbs_breakout'], 
       exchanges=["binance_spot", "bybit_spot"],
       users=["default", "user1", "trader2"],  # Multiple users
       send_telegram=True
   )
   ```

3. For VSA strategies in notebooks, specify the user ID:
   ```python
   await run_scan(
       timeframe='3d',  # NEW: 3-day timeframe 
       strategy='consolidation_breakout',  # NEW: consolidation breakout strategy
       exchange="binance_spot", 
       send_telegram=True,
       user_id="user1"
   )
   ```

## Adding New Exchanges

To add a new exchange:

1. Create a new client class in `exchanges/` that inherits from `BaseExchangeClient`
2. Implement all required methods (`_get_interval_map`, `_get_fetch_limit`, `get_all_spot_symbols`, `fetch_klines`)
3. Update the exchange mapping in `scanner/main.py` to include the new exchange
4. Add support for new timeframes (3d, 4d) in the interval mapping

Example of an updated exchange client:

```python
from .base_client import BaseExchangeClient

class NewExchangeClient(BaseExchangeClient):
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.newexchange.com"
        super().__init__(timeframe)

    def _get_interval_map(self):
        return {
            '1w': '1week',
            '4d': '1day',  # Will aggregate 4 days
            '3d': '1day',  # Will aggregate 3 days  
            '2d': '1day',  # Will aggregate 2 days
            '1d': '1day',
            '4h': '4hour'
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,
            '4d': 160,   # NEW: 4-day limit
            '3d': 120,   # NEW: 3-day limit
            '2d': 120,
            '1d': 60,
            '4h': 200
        }[self.timeframe]

    async def get_all_spot_symbols(self):
        # Implementation...
        pass

    async def fetch_klines(self, symbol):
        # Implementation...
        pass
```

## Adding New Strategies

### Adding a New VSA Strategy

1. Create a new strategy file in `breakout_vsa/strategies/`
2. Define parameters in the `get_params()` function
3. Update `breakout_vsa/core.py` to include the new strategy
4. Update `STRATEGY_CHANNELS` in `utils/config.py` to map your strategy to a channel
5. Add strategy support in `scanner/main.py` vsa_detectors dictionary

### Adding a New Custom Strategy

1. Create a new strategy file in `custom_strategies/` (like `consolidation_breakout.py`)
2. Define a detection function that returns a boolean and a result dictionary
3. Update `custom_strategies/__init__.py` to expose your new function
4. Update `scanner/main.py` to support the new strategy in the scan_market method
5. Update `TELEGRAM_TOKENS` and telegram configuration for the new strategy

Example custom strategy structure:
```python
# custom_strategies/new_strategy.py
def detect_new_strategy(df, check_bar=-1):
    """
    Detect new strategy pattern
    
    Args:
        df: DataFrame with OHLCV data
        check_bar: Which bar to check (-1 for current, -2 for last closed)
    
    Returns:
        tuple: (detected: bool, result: dict)
    """
    # Strategy logic here
    detected = False
    result = {}
    
    if detected:
        result = {
            'timestamp': df.index[check_bar],
            'close_price': df['close'].iloc[check_bar],
            'volume_usd': df['volume'].iloc[check_bar] * df['close'].iloc[check_bar],
            'direction': 'Up',  # or 'Down'
            # Add strategy-specific metrics
        }
    
    return detected, result
```

## Troubleshooting

### Common Issues

1. **Circular Import Errors**:
   - Ensure imports are properly ordered in `__init__.py` files
   - Use local imports within functions where needed

2. **API Rate Limiting**:
   - Adjust `request_delay` in exchange clients
   - Reduce `batch_size` for high-traffic exchanges
   - Use parallel scanning to distribute load

3. **Telegram Bot Issues**:
   - Verify token correctness for all strategies including consolidation_breakout and hbs_breakout
   - Ensure the bot has been started by all users
   - Check permission to post in groups
   - Verify new strategies are mapped correctly in config

4. **No Results Found**:
   - Check volume thresholds for new timeframes (3d, 4d) in `config.py`
   - Verify the strategy parameters for consolidation_breakout and hbs_breakout
   - Ensure exchange API supports new timeframes
   - Check if consolidation detection logic has sufficient data (23+ bars)

5. **Parallel Scanning Issues**:
   - Verify all required exchanges are available
   - Check network connectivity for multiple concurrent connections
   - Monitor memory usage during large multi-timeframe scans
   - Ensure proper async/await usage

6. **Cache-Related Problems**:
   - Clear cache manually: `kline_cache.clear()`
   - Restart scanner if cache becomes corrupted
   - Check memory usage for large cache sizes

7. **Consolidation Strategy Issues**:
   - Ensure sufficient historical data (minimum 23 bars for consolidation_breakout)
   - Check ATR filter settings for low volatility requirements
   - Verify box formation criteria (height percentage, bars inside)
   - Monitor channel breakout confirmation logic

### Logging

Enhanced logging for parallel operations:

```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# For debugging parallel operations
logging.getLogger('scanner').setLevel(logging.DEBUG)
logging.getLogger('exchanges').setLevel(logging.DEBUG)
```

For file-based logging:

```python
handler = logging.FileHandler('parallel_scanner.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)
```

### Performance Monitoring

Monitor parallel scan performance:

```python
import time
start_time = time.time()

result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["4d", "3d", "1d"],
    strategies=["consolidation_breakout", "hbs_breakout"],
    exchanges=None
)

duration = time.time() - start_time
print(f"Scan completed in {duration:.2f} seconds")
```

---

## Recent Updates

### Version 2.1 Features (NEW)

- **Consolidation Breakout Strategy**: Advanced breakout detection with channel confirmation
- **HBS Breakout Strategy**: Hybrid strategy combining consolidation and confluence signals
- **Extended Timeframe Support**: Added 3d and 4d timeframes for medium-term analysis
- **Enhanced Telegram Notifications**: Direction indicators and detailed breakout metrics
- **Parallel Processing Engine**: Complete rewrite for concurrent operations
- **Multi-Timeframe Scanning**: Efficient scanning across multiple timeframes
- **Enhanced Caching**: Smart cache management for optimal performance
- **Improved Error Handling**: Robust error recovery in parallel operations
- **Progress Tracking**: Real-time progress updates for all operations
