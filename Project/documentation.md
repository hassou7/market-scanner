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

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms like volume surge, weak uptrend, pin down, confluence pattern detection, consolidation breakout detection, channel breakout detection, 50SMA breakout detection, and hybrid breakout strategies.

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
  - **50SMA Breakout** - clean moving average breakout detection (NEW)
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
│   └── sma50_breakout.py       # NEW: 50SMA breakout detection
├── exchanges/                  # Exchange API clients
│   ├── __init__.py
│   ├── base_client.py          # Base exchange client class
│   ├── binance_futures_client.py  # Binance Perpetuals client
│   ├── binance_spot_client.py  # Binance Spot client
│   ├── bybit_client.py         # Bybit client
│   ├── gateio_client.py        # Gate.io client
│   ├── kucoin_client.py        # KuCoin client
│   ├── mexc_client.py          # MEXC client
│   ├── sf_kucoin_client.py     # NEW: SF KuCoin weekly client
│   └── sf_mexc_client.py       # NEW: SF MEXC weekly client
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

### SF Weekly Scanning (NEW)

The scanner now supports enhanced weekly data access for KuCoin and MEXC via the Seven Figures service:

#### SF Exchange Usage

```python
from run_parallel_scanner import sf_exchanges_1w

# Scan SF exchanges for weekly data
result = await run_parallel_exchanges(
    timeframe="1w",                    # Must be 1w for SF exchanges
    strategies=["sma50_breakout", "loaded_bar", "breakout_bar"],
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
    strategies=["sma50_breakout", "confluence"],
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
    strategies=["breakout_bar", "confluence", "sma50_breakout"],  # NEW: sma50_breakout
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
    strategies=["confluence", "consolidation_breakout", "sma50_breakout"],  # NEW: sma50_breakout
    exchanges=None,  # Use all available exchanges
    users=["default"],
    send_telegram=True,
    min_volume_usd=None
)
```

### Command Line Usage

```bash
# Run parallel scan with 50SMA breakout strategy
python run_parallel_scanner.py 1w "sma50_breakout,loaded_bar" "sf_kucoin_1w,sf_mexc_1w" "default" true

# Run multiple strategies including 50SMA breakout
python run_parallel_scanner.py 1d "sma50_breakout,confluence,consolidation_breakout" "binance_spot,bybit_spot" "default" true
```

### Traditional Jupyter Notebook Usage

Start Jupyter and open the `vsa_and_custom_scanner.ipynb` notebook:

```bash
jupyter notebook
```

#### Custom Strategy Scanning with 50SMA Breakout

```python
await run_custom_scan(
    exchange='binance_futures',
    timeframe='1w',
    strategies=['sma50_breakout', 'consolidation_breakout', 'channel_breakout', 'hbs_breakout'],  # NEW: sma50_breakout
    send_telegram=True
)
```

## VSA Strategies

[VSA strategies section remains the same as original...]

## Custom Strategies

### 50SMA Breakout (NEW)

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

### Consolidation Breakout

An advanced breakout detection system that identifies when price breaks out of established consolidation patterns with channel confirmation. This strategy combines consolidation box detection with trend channel analysis to provide high-probability breakout signals.

### Channel Breakout

An advanced diagonal channel breakout detection system that identifies when price breaks out of established diagonal consolidation channels using Theil-Sen regression for robust trend fitting.

### HBS Breakout

A sophisticated hybrid strategy that combines **Consolidation Breakout**/**Channel Breakout** AND **Confluence Signal** detection for ultra-high probability trade setups. HBS stands for "Hybrid Breakout Strategy" and represents the confluence of multiple confirming factors.

## SF Weekly Scanning (NEW)

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
    strategies=["sma50_breakout", "loaded_bar", "breakout_bar"],
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
    strategies=["sma50_breakout", "confluence", "hbs_breakout"],
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
    strategies=["sma50_breakout"]
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

# NEW: SF exchange group for enhanced weekly data
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]

# All available exchanges
all_exchanges = futures_exchanges + spot_exchanges + sf_exchanges_1w
```

### Smart Auto-Selection

```python
# Auto-selects appropriate exchanges based on timeframe
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1w"],              # Auto-selects sf_exchanges_1w
    strategies=["sma50_breakout"],
    exchanges=None                  # Smart selection
)
```

## Multi-User Support

The system supports sending notifications to multiple users:

```python
await run_parallel_exchanges(
    timeframe='1w',
    strategies=['sma50_breakout', 'confluence'],  # NEW: sma50_breakout
    exchanges=sf_exchanges_1w,                    # NEW: SF exchanges
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

### Adding the 50SMA Breakout Strategy

1. **Create Strategy File**: `custom_strategies/sma50_breakout.py`
2. **Define Detection Function**: 
   ```python
   def detect_sma50_breakout(df, sma_period=50, clean_lookback=7, check_bar=-1):
       # Strategy implementation
       return detected, result
   ```
3. **Update Imports**: Add to `custom_strategies/__init__.py`
4. **Scanner Integration**: Add strategy handling in `scanner/main.py`
5. **Configuration**: Add Telegram channel mapping

### Strategy Combination Examples

#### 50SMA + HBS Breakout
```python
# Combine 50SMA breakout with HBS for high-probability signals
strategies = ["sma50_breakout", "hbs_breakout"]
```

#### Multi-Strategy Confluence
```python
# Run multiple complementary strategies
strategies = ["sma50_breakout", "consolidation_breakout", "confluence"]
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

3. **50SMA Breakout Issues**:
   - Ensure sufficient historical data (57+ bars)
   - Check clean lookback configuration
   - Verify ATR calculation requirements
   - Monitor volume threshold settings

### Strategy Combination Issues

1. **Strategy Conflicts**:
   - Some strategies may have conflicting requirements
   - Verify data requirements for all selected strategies
   - Check volume threshold compatibility

2. **Performance Impact**:
   - Multiple strategies increase processing time
   - Consider strategy prioritization for large scans
   - Monitor memory usage with complex combinations

### Enhanced Logging

```python
import logging

# Enable debug logging for SF exchanges
logging.getLogger('exchanges.sf_kucoin_client').setLevel(logging.DEBUG)
logging.getLogger('exchanges.sf_mexc_client').setLevel(logging.DEBUG)

# Enable strategy-specific logging
logging.getLogger('custom_strategies.sma50_breakout').setLevel(logging.DEBUG)
```

---

## Recent Updates

### Version 2.3 Features (NEW)

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