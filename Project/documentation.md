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
9. [SF Weekly Scanning](#sf-weekly-scanning)
10. [Parallel Scanning](#parallel-scanning)
11. [Multi-User Support](#multi-user-support)
12. [Adding New Exchanges](#adding-new-exchanges)
13. [Adding New Strategies](#adding-new-strategies)
14. [Troubleshooting](#troubleshooting)

## Project Overview

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms like volume surge, weak uptrend, pin down, confluence pattern detection, consolidation breakout detection, channel breakout detection, 50SMA breakout detection, wedge breakout detection, and hybrid breakout strategies.

The scanner supports multiple exchanges including Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit. It can analyze various timeframes (1w, 3d, 2d, 1d, 4h) and send notifications via Telegram to multiple users. The system now features **parallel processing** for enhanced performance across multiple exchanges and timeframes, plus **SF (Seven Figures) integration** for enhanced KuCoin and MEXC weekly data access.

## Features

- **Multiple Exchange Support**: Scan Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit markets
- **SF Exchange Integration**: Enhanced KuCoin and MEXC weekly data via Seven Figures service
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
  - **Channel Breakout** - breakout from diagonal channel patterns
  - **50SMA Breakout** - clean moving average breakout detection
  - **Wedge Breakout** - diagonal consolidation wedge breakout detection (NEW)
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
│   ├── consolidation_breakout.py  # Consolidation breakout detection
│   ├── channel_breakout.py     # Channel breakout detection
│   ├── sma50_breakout.py       # 50SMA breakout detection
│   └── wedge_breakout.py       # NEW: Wedge breakout detection
├── exchanges/                  # Exchange API clients
│   ├── __init__.py
│   ├── base_client.py          # Base exchange client class
│   ├── binance_futures_client.py  # Binance Perpetuals client
│   ├── binance_spot_client.py  # Binance Spot client
│   ├── bybit_client.py         # Bybit client
│   ├── gateio_client.py        # Gate.io client
│   ├── kucoin_client.py        # KuCoin client
│   ├── mexc_client.py          # MEXC client
│   ├── sf_kucoin_client.py     # SF KuCoin weekly client
│   └── sf_mexc_client.py       # SF MEXC weekly client
├── scanner/                    # Market scanning logic
│   ├── __init__.py
│   └── main.py                 # Scanner main functions with parallel support
├── utils/                      # Utility functions and configuration
│   ├── __init__.py
│   └── config.py               # Configuration values
├── run_parallel_scanner.py     # Parallel scanning engine with SF support
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
    "confluence": "8066329517:AAHVr6kufZWe8UqCKPfmsRhSPleNlt_7G-g",
    "hbs_breakout": "8346095660:AAF0oUOfcMVsrbvTmklOnO-9KohlUH5JmqE"
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
    "channel_breakout": "start_trend",
    "sma50_breakout": "start_trend",
    "wedge_breakout": "start_trend",
    "hbs_breakout": "hbs_breakout"
}
```

### Volume Thresholds

Adjust volume thresholds for different timeframes in `utils/config.py`:

```python
# Volume thresholds (updated with new timeframes)
VOLUME_THRESHOLDS = {
    "1w": 500000,  # Weekly volume threshold in USD
    "4d": 300000,  # 4-day volume threshold in USD
    "3d": 200000,  # 3-day volume threshold in USD
    "2d": 150000,  # 2-day volume threshold in USD
    "1d": 75000,   # Daily volume threshold in USD
    "4h": 40000    # 4-hour volume threshold in USD
}
```

## Usage

### SF Weekly Scanning

The scanner now supports enhanced weekly data access for KuCoin and MEXC via the Seven Figures service:

#### SF Exchange Usage

```python
from run_parallel_scanner import sf_exchanges_1w

# Scan SF exchanges for weekly data
result = await run_parallel_exchanges(
    timeframe="1w",                    # Must be 1w for SF exchanges
    strategies=["wedge_breakout", "sma50_breakout", "loaded_bar", "breakout_bar"],
    exchanges=sf_exchanges_1w,         # SF KuCoin and MEXC
    users=["default"],
    send_telegram=True,
    min_volume_usd=None
)
```

#### Auto-Selection for Weekly Scans

```python
# When scanning 1w with no exchanges specified, SF exchanges are auto-selected
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1w"],              # Automatically uses sf_exchanges_1w
    strategies=["wedge_breakout", "sma50_breakout", "confluence"],
    exchanges=None,                 # Auto-selects SF exchanges
    users=["default"],
    send_telegram=True
)
```

### Parallel Scanning

The scanner supports parallel processing for maximum efficiency:

#### Single Timeframe, Multiple Exchanges

```python
from run_parallel_scanner import run_parallel_exchanges

# Run scan across all exchanges in parallel
result = await run_parallel_exchanges(
    timeframe="1d",
    strategies=["breakout_bar", "confluence", "wedge_breakout", "sma50_breakout"],
    exchanges=["binance_spot", "bybit_spot", "kucoin_spot"],
    users=["default"],
    send_telegram=True,
    min_volume_usd=None
)
```

#### Multiple Timeframes, Multiple Exchanges

```python
from run_parallel_scanner import run_parallel_multi_timeframes_all_exchanges

# Run scan across multiple timeframes and exchanges
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["3d", "4d", "1w"],
    strategies=["confluence", "consolidation_breakout", "wedge_breakout", "sma50_breakout"],
    exchanges=None,  # Use all available exchanges
    users=["default"],
    send_telegram=True,
    min_volume_usd=None
)
```

### Command Line Usage

```bash
# Run parallel scan with wedge breakout strategy
python run_parallel_scanner.py 1w "wedge_breakout,loaded_bar" "sf_kucoin_1w,sf_mexc_1w" "default" true

# Run multiple strategies including wedge breakout
python run_parallel_scanner.py 1d "wedge_breakout,confluence,consolidation_breakout" "binance_spot,bybit_spot" "default" true
```

### Traditional Jupyter Notebook Usage

Start Jupyter and open the `vsa_and_custom_scanner.ipynb` notebook:

```bash
jupyter notebook
```

#### Custom Strategy Scanning with Wedge Breakout

```python
await run_custom_scan(
    exchange='binance_futures',
    timeframe='1w',
    strategies=['wedge_breakout', 'sma50_breakout', 'consolidation_breakout', 'channel_breakout', 'hbs_breakout'],
    send_telegram=True
)
```

## VSA Strategies

[VSA strategies section remains the same as original...]

## Custom Strategies

### Wedge Breakout

A sophisticated diagonal consolidation wedge breakout detection system that identifies when price breaks out of converging trend lines, indicating potential strong directional moves.

**Detection Logic:**
1. **Wedge Formation**: Identifies converging upper and lower trend lines over a rolling 9-bar window
2. **Diagonal Convergence**: Uses Theil-Sen robust regression to fit both high and low trend lines
3. **Progressive Tightening**: Detects when wedge narrows to specific percentage levels (40%, 35%, 25%, 15%)
4. **ATR Volatility Filter**: Ensures wedge formation occurs during low volatility periods
5. **Breakout Detection**: Identifies when price breaks above upper or below lower wedge boundary

**Key Components:**
- **Rolling Window Analysis**: 9-bar rolling window for wedge detection
- **Theil-Sen Regression**: Robust statistical fitting for upper/lower bounds
- **Log Scale Option**: Optional logarithmic scaling for better percentage-based analysis
- **ATR Filter**: 14-period ATR with 7-period smoothing for volatility confirmation
- **Multi-Level Detection**: Progressive tightening thresholds for different wedge qualities

**Advanced Features:**
- **Dynamic Wedge Tracking**: Real-time wedge monitoring with age tracking
- **Breakout Direction**: Clear identification of upward or downward breakouts
- **Channel Slope Analysis**: Measures wedge direction (upward/downward/horizontal trending)
- **Minimum Bars Inside**: Configurable requirement for wedge validity (default: 9 bars)
- **Deduplication**: Prevents multiple signals from similar wedge patterns

**Signal Requirements:**
- Minimum data requirement: 23 bars (for ATR calculation)
- Rolling window size: 9 bars for wedge detection
- Minimum bars inside wedge: 9 bars for validity
- ATR period: 14 bars with 7-period smoothing
- Height percentage thresholds: 40%, 35%, 25%, 15% for quality levels

**Telegram Notifications Include:**
- Breakout direction (Up/Down) with appropriate color coding
- Wedge channel direction (Upwards/Downwards/Horizontal)
- Channel slope and percentage growth per bar
- Wedge age and formation period
- Height percentage and tightness level
- Entry and left boundary timestamps
- ATR volatility confirmation status

**Usage Recommendations:**
- Excellent for catching breakouts from tight consolidation patterns
- Best used on higher timeframes (1d, 1w) for reliable wedge formations
- Ideal for trend continuation and reversal strategies
- Suitable for automated trading systems requiring precise breakout timing
- Works well in combination with volume confirmation strategies

**Technical Implementation:**
- **Log Scale Processing**: Optional logarithmic transformation for percentage-based analysis
- **Robust Statistical Fitting**: Theil-Sen regression resistant to outliers
- **Progressive Monitoring**: Real-time wedge tracking with dynamic tightening detection
- **Memory Efficiency**: Smart channel management with automatic cleanup
- **Vectorized Calculations**: Optimized for performance across large datasets

**Parameters:**
```python
detect_wedge_breakout(
    df,
    check_bar=-1,           # Bar to analyze (-1 current, -2 last closed)
    use_log=True,           # Use logarithmic scale for fits
    width_multiplier=0.9    # Multiplier for wedge width (not used in implementation)
)
```

**Configuration Options:**
```python
# Internal parameters (customizable in implementation)
N = 9                      # Rolling window size
min_bars_inside = 9        # Minimum bars required inside wedge
pct_levels = [40.0, 35.0, 25.0, 15.0]  # Tightness thresholds
atr_len = 14               # ATR calculation period
atr_sma = 7                # ATR smoothing period
atr_k = 1.0                # ATR volatility filter multiplier
```

### 50SMA Breakout

A clean moving average breakout detection system that identifies initial breakout moments rather than continuation moves, ensuring early entry opportunities.

**Detection Logic:**
1. **Primary Condition**: Close > 50SMA and Low < 50SMA (classic breakout)
2. **Clean Filter**: Last N bars (configurable, default 7) did NOT close above 50SMA + 0.2*ATR(7)
3. **Optional Pre-breakout**: Close > 50SMA - 0.2*ATR(7) to catch early signals

**Key Components:**
- **50SMA Calculation**: Simple moving average over 50 periods
- **ATR Integration**: Uses 7-period ATR for dynamic threshold adjustment
- **Clean Breakout Filter**: Prevents late entries on extended moves
- **Volume Confirmation**: Includes volume analysis for signal validation
- **Strength Classification**: Weak/Moderate/Strong breakout categorization

**Advanced Features:**
- **Configurable Lookback**: Adjust clean filter strictness (1-10 bars)
- **Pre-breakout Mode**: Option to catch signals before full breakout
- **ATR-Based Thresholds**: Dynamic adjustment based on volatility
- **Volume Integration**: Volume ratio and USD volume analysis

**Signal Requirements:**
- Minimum data requirement: 57 bars (50 for SMA + 7 for ATR)
- Configurable clean lookback period (default: 7 bars)
- ATR period: 7 bars for volatility measurement
- ATR multiplier: 0.2 for threshold calculation

**Telegram Notifications Include:**
- Breakout type (classic or pre-breakout)
- Breakout strength classification
- Price vs SMA percentage difference
- Low vs SMA relationship
- ATR value and thresholds
- Clean lookback period used
- Volume analysis and confirmation

**Usage Recommendations:**
- Ideal for trend-following strategies requiring clean entries
- Excellent for catching initial momentum moves
- Best used on higher timeframes (1d, 1w) for reliable signals
- Suitable for automated trading systems requiring precise entry timing
- Configure clean_lookback based on market volatility (higher for volatile markets)

**Parameters:**
```python
detect_sma50_breakout(
    df,
    sma_period=50,           # SMA period (default: 50)
    atr_period=7,            # ATR period (default: 7)
    atr_multiplier=0.2,      # ATR multiplier (default: 0.2)
    use_pre_breakout=False,  # Enable pre-breakout mode
    clean_lookback=7,        # Clean filter lookback period
    check_bar=-1             # Bar to analyze (-1 current, -2 last closed)
)
```

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

A sophisticated multi-factor confirmation system that combines Volume, Spread, and Momentum analysis. It combines:

- **High Volume Component**: Volume significantly above average
- **Spread Breakout Component**: Range expansion indicating volatility
- **Momentum Breakout Component**: Strong directional movement

The confluence detector calculates:
- Individual component scores
- Combined momentum score
- Close-off-low percentage
- Volume ratio analysis

Confluence signals are triggered when multiple components align, providing higher-probability trade setups.

Now supports **bidirectional detection** with **engulfing reversal pattern recognition**.

**Enhanced Features:**
- **Bullish Confluence Detection**: Upward momentum with volume and spread confirmation
- **Bearish Confluence Detection**: Downward momentum with volume and spread confirmation
- **Engulfing Reversal Patterns**: Identifies trend reversals when opposite-direction signals occur consecutively

**Detection Components:**
1. **VSA-Based Volume Analysis**: Direction-aware volume classification with local, broad, and serious volume conditions
2. **Dual-Direction Spread Analysis**: Separate bullish (close > 70% of range) and bearish (close < 30% of range) spread breakout detection
3. **Mirrored Momentum Scoring**: Independent bullish and bearish momentum calculations with weighted moving average validation

**Engulfing Reversal Logic:**
- Detects when bearish confluence (bar N-1) is followed by bullish confluence (bar N)
- Signals potential trend reversal or momentum shift
- Labeled as "Up Reversal" or "Down Reversal" in notifications

**Signal Requirements:**
- Minimum data requirement: 21+ bars for WMA calculations
- All three components (Volume + Spread + Momentum) must align
- Context length: 7 bars for range analysis
- WMA periods: 7 (fast), 13 (mid), 21 (slow)

**Advanced Parameters:**
```python
detect_confluence(
    df,
    is_bullish=True,         # Direction to detect (True/False)
    doji_threshold=5.0,      # Doji detection threshold (%)
    ctx_len=7,              # Context length for momentum
    len_fast=7,             # Fast WMA period
    len_mid=13,             # Mid WMA period  
    len_slow=21,            # Slow WMA period
    check_bar=-1            # Bar to analyze
)
```

### Consolidation Breakout

An advanced breakout detection system that identifies when price breaks out of established consolidation patterns with channel confirmation. This strategy combines consolidation box detection with trend channel analysis to provide high-probability breakout signals.

### Channel Breakout

An advanced diagonal channel breakout detection system that identifies when price breaks out of established diagonal consolidation channels using Theil-Sen regression for robust trend fitting.

### HBS Breakout

A sophisticated hybrid strategy that combines **Consolidation Breakout**/**Channel Breakout** AND **Confluence Signal** detection for ultra-high probability trade setups. HBS stands for "Hybrid Breakout Strategy" and represents the confluence of multiple confirming factors.

## SF Weekly Scanning

The scanner now includes enhanced weekly data access through the Seven Figures (SF) service for KuCoin and MEXC exchanges.

### SF Exchange Support

#### SF Exchange Definitions
```python
# Available SF exchanges for weekly data
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]
```

#### SF-Specific Features
- **Enhanced Data Quality**: Access to Seven Figures curated market data
- **Weekly Focus**: Optimized for 1w timeframe analysis
- **TradingView Integration**: Links maintain regular exchange format (KuCoin, MEXC)
- **Volume Filtering**: Enhanced volume thresholds for weekly timeframes
- **Parallel Processing**: Full support for concurrent SF exchange scanning

### SF Usage Examples

#### Direct SF Exchange Scanning
```python
# Scan SF exchanges specifically
result = await run_parallel_exchanges(
    timeframe="1w",                    # Required for SF exchanges
    strategies=["wedge_breakout", "sma50_breakout", "loaded_bar", "breakout_bar"],
    exchanges=sf_exchanges_1w,         # SF KuCoin and MEXC
    users=["default"],
    send_telegram=True,
    min_volume_usd=300000              # Weekly volume threshold
)
```

#### Combined Exchange Scanning
```python
# Mix SF and regular exchanges for comprehensive weekly analysis
weekly_exchanges = ["binance_spot", "bybit_spot", "gateio_spot"] + sf_exchanges_1w

result = await run_parallel_exchanges(
    timeframe="1w",
    strategies=["wedge_breakout", "sma50_breakout", "confluence", "hbs_breakout"],
    exchanges=weekly_exchanges,
    users=["default"],
    send_telegram=True
)
```

#### SF Exchange Validation
The system automatically validates that SF exchanges are only used with 1w timeframe:
```python
# This will raise an error
await run_parallel_exchanges(
    timeframe="1d",                    # Invalid timeframe
    exchanges=["sf_kucoin_1w"],        # SF exchange
    strategies=["wedge_breakout"]
)
# Error: SF exchange 'sf_kucoin_1w' only supports 1w timeframe
```

### SF Exchange Integration

#### TradingView Links
SF exchanges generate TradingView links that point to regular exchanges:
- `sf_kucoin_1w` → `KUCOIN:BTCUSDT`
- `sf_mexc_1w` → `MEXC:BTCUSDT`

#### Exchange Name Mapping
```python
# In scanner/main.py UnifiedScanner._get_exchange_name()
mappings = {
    "SFKucoinClient": "KuCoin Spot",      # SF KuCoin → KuCoin Spot
    "SFMexcClient": "MEXC Spot"           # SF MEXC → MEXC Spot
}
```

## Parallel Scanning

The scanner features advanced parallel processing capabilities:

### Exchange Groups (Updated)

```python
# Regular exchanges
futures_exchanges = ["binance_futures", "bybit_futures", "mexc_futures", "gateio_futures"]
spot_exchanges = ["binance_spot", "bybit_spot", "kucoin_spot", "mexc_spot", "gateio_spot"]
spot_exchanges_1w = ["binance_spot", "bybit_spot", "gateio_spot"]

# SF exchange group for enhanced weekly data
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]

# All available exchanges
all_exchanges = futures_exchanges + spot_exchanges + sf_exchanges_1w
```

### Smart Auto-Selection

```python
# Auto-selects appropriate exchanges based on timeframe
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1w"],              # Auto-selects sf_exchanges_1w
    strategies=["wedge_breakout", "sma50_breakout"],
    exchanges=None                  # Smart selection
)
```

## Multi-User Support

The system supports sending notifications to multiple users:

```python
await run_parallel_exchanges(
    timeframe='1w',
    strategies=['wedge_breakout', 'confluence'],
    exchanges=sf_exchanges_1w,
    users=["default", "user1", "trader2"],
    send_telegram=True
)
```

## Adding New Exchanges

To add a new SF-style exchange:

1. Create a new client class inheriting from `BaseExchangeClient`
2. Implement SF service integration
3. Update exchange mapping in `scanner/main.py`
4. Add to appropriate exchange group definitions

Example SF exchange client:
```python
from .base_client import BaseExchangeClient
from exchanges.sf_pairs_service import SFPairsService

class SFNewExchangeClient(BaseExchangeClient):
    def __init__(self, timeframe="1w"):
        self.exchange_name = "NewExchange"
        self.sf_service = SFPairsService()
        super().__init__(timeframe)
    
    def _get_interval_map(self):
        return {'1w': '1w'}  # SF exchanges support 1w only
    
    async def get_all_spot_symbols(self):
        # SF service integration
        pass
    
    async def fetch_klines(self, symbol):
        # SF service data fetching
        pass
```

## Adding New Strategies

### Adding the Wedge Breakout Strategy

1. **Create Strategy File**: `custom_strategies/wedge_breakout.py` (already provided)
2. **Update Imports**: Add to `custom_strategies/__init__.py`
   ```python
   from .wedge_breakout import detect_wedge_breakout
   ```
3. **Scanner Integration**: Add strategy handling in `scanner/main.py`
   ```python
   elif strategy == "wedge_breakout":
       from custom_strategies import detect_wedge_breakout
       detected, result = detect_wedge_breakout(df, check_bar=check_bar)
   ```
4. **Configuration**: Add Telegram channel mapping in `utils/config.py`
   ```python
   STRATEGY_CHANNELS = {
       # ... existing strategies ...
       "wedge_breakout": "start_trend",
   }
   ```

### Strategy Combination Examples

#### Wedge + 50SMA Breakout
```python
# Combine wedge breakout with 50SMA for complementary signals
strategies = ["wedge_breakout", "sma50_breakout"]
```

#### Multi-Strategy Confluence
```python
# Run multiple complementary strategies
strategies = ["wedge_breakout", "consolidation_breakout", "confluence"]
```

#### Advanced Pattern Recognition
```python
# Comprehensive pattern detection suite
strategies = ["wedge_breakout", "channel_breakout", "consolidation_breakout", "hbs_breakout"]
```

## Troubleshooting

### SF Exchange Issues

1. **SF Exchange Timeframe Errors**:
   - Ensure SF exchanges only used with 1w timeframe
   - Check exchange group definitions
   - Verify timeframe validation logic

2. **SF Service Connection**:
   - Verify SF service availability
   - Check network connectivity to SF endpoints
   - Monitor SF service rate limits

3. **Wedge Breakout Issues**:
   - Ensure sufficient historical data (23+ bars minimum)
   - Check rolling window configuration (9 bars default)
   - Verify ATR calculation requirements (14-period ATR + 7-period smoothing)
   - Monitor tightness level thresholds

### Strategy Combination Issues

1. **Strategy Conflicts**:
   - Some strategies may have conflicting requirements
   - Verify data requirements for all selected strategies
   - Check volume threshold compatibility
   - Monitor minimum bar requirements (wedge: 23, 50SMA: 57)

2. **Performance Impact**:
   - Multiple strategies increase processing time
   - Consider strategy prioritization for large scans
   - Monitor memory usage with complex combinations
   - Wedge breakout adds computational overhead due to rolling regression
  
3. **Confluence Direction Issues**:
   - Current scanner only processes bullish confluence signals
   - Full bearish detection requires uncommenting bearish checks in scan_market()
   - Engulfing reversals only detect bullish reversals from prior bearish signals
   - Monitor signal direction field: "Up", "Down", "Up Reversal", "Down Reversal"

### Enhanced Logging

```python
import logging

# Enable debug logging for SF exchanges
logging.getLogger('exchanges.sf_kucoin_client').setLevel(logging.DEBUG)
logging.getLogger('exchanges.sf_mexc_client').setLevel(logging.DEBUG)

# Enable strategy-specific logging
logging.getLogger('custom_strategies.wedge_breakout').setLevel(logging.DEBUG)
logging.getLogger('custom_strategies.sma50_breakout').setLevel(logging.DEBUG)
```

---

## Recent Updates

### Version 2.5 Features (NEW)

- **Enhanced Confluence Strategy**: Bidirectional bullish/bearish confluence detection
- **Engulfing Reversal Recognition**: Automatic detection of trend reversal patterns
- **VSA-Based Volume Direction**: Direction-aware volume analysis using Volume Spread Analysis principles
- **Dual Momentum Scoring**: Independent bullish and bearish momentum calculations with mirrored positioning logic
- **Improved Signal Prioritization**: Current bar and reversal pattern prioritization in scanner
- **Enhanced Telegram Notifications**: Reversal pattern indicators with "⚡Engulfing Reversal!" alerts
- **Robust NaN Handling**: Improved early-bar processing with safe WMA warmup periods
- **Series Alignment Optimization**: Maintained proper pandas indexing throughout all calculations
  
### Version 2.4 Features

- **Wedge Breakout Strategy**: Advanced diagonal consolidation wedge breakout detection with Theil-Sen regression
- **Progressive Wedge Monitoring**: Real-time wedge tracking with dynamic tightening detection
- **Multi-Level Wedge Detection**: Four tightness levels (40%, 35%, 25%, 15%) for different quality wedges
- **Enhanced Breakout Classification**: Clear direction identification with channel slope analysis
- **ATR Volatility Integration**: Wedge formation validation during low volatility periods
- **Logarithmic Scale Support**: Optional log-scale processing for percentage-based wedge analysis
- **Memory-Efficient Implementation**: Smart channel management with automatic cleanup

### Version 2.3 Features

- **SF Exchange Integration**: Enhanced KuCoin and MEXC weekly data via Seven Figures service
- **50SMA Breakout Strategy**: Clean moving average breakout detection with configurable filters
- **SF Exchange Validation**: Automatic timeframe compatibility checking
- **Enhanced Weekly Scanning**: Improved weekly timeframe analysis capabilities
- **Smart Exchange Selection**: Auto-selection of appropriate exchanges based on timeframe
- **Strategy Combination Support**: Framework for combining multiple strategies
- **Improved TradingView Integration**: Proper exchange mapping for SF exchanges

### Version 2.2 Features

- **Channel Breakout Strategy**: Advanced diagonal channel breakout detection with Theil-Sen regression
- **Enhanced Channel Analysis**: Robust statistical fitting for trending channel patterns
- **Improved Breakout Detection**: Diagonal channel breakouts vs horizontal consolidation breakouts
- **ATR Volatility Filtering**: Enhanced volatility confirmation for channel formation
- **Multi-Level Tightness Detection**: Progressive tightening thresholds (35%, 25%, 15%)
- **Advanced Telegram Notifications**: Channel-specific metrics including slope, direction, and age

### Version 2.1 Features

- **Consolidation Breakout Strategy**: Advanced breakout detection with channel confirmation
- **HBS Breakout Strategy**: Hybrid strategy combining consolidation and confluence signals
- **Extended Timeframe Support**: Added 3d and 4d timeframes for medium-term analysis
- **Enhanced Telegram Notifications**: Direction indicators and detailed breakout metrics
- **Parallel Processing Engine**: Complete rewrite for concurrent operations
- **Multi-Timeframe Scanning**: Efficient scanning across multiple timeframes