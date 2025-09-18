# Cryptocurrency Market Scanner Documentation v2.10

A comprehensive market scanner for cryptocurrency exchanges that combines VSA (Volume Spread Analysis) strategies with custom pattern detection algorithms, featuring parallel processing, multi-timeframe analysis, and optimized native/composed strategy prioritization.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Strategy Classification](#strategy-classification)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [VSA Strategies](#vsa-strategies)
9. [Native Strategies](#native-strategies)
10. [Composed Strategies](#composed-strategies)
11. [Session Management Flow](#session-management-flow)
12. [Execution Flow and Priorities](#execution-flow-and-priorities)
13. [SF Weekly Scanning](#sf-weekly-scanning)
14. [Parallel Scanning](#parallel-scanning)
15. [Multi-User Support](#multi-user-support)
16. [Adding New Exchanges](#adding-new-exchanges)
17. [Adding New Strategies](#adding-new-strategies)
18. [Troubleshooting](#troubleshooting)

## Project Overview

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms, with a clear separation between native strategies (foundational patterns) and composed strategies (multi-factor combinations).

The scanner supports multiple exchanges including Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit. It can analyze various timeframes (1w, 4d, 3d, 2d, 1d, 4h) and send notifications via Telegram to multiple users. The system features **optimized parallel processing** with **native/composed strategy prioritization**, **efficient data fetching** for aggregated timeframes, and **SF (Seven Figures) integration** for enhanced KuCoin and MEXC weekly data access.

## Features

- **Optimized Strategy Prioritization**: Native strategies execute first for database population, followed by composed strategies
- **Multiple Exchange Support**: Scan Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit markets with fast/slow classification
- **SF Exchange Integration**: Enhanced KuCoin and MEXC weekly data via Seven Figures service
- **Extended Timeframes**: Analyze 1w, 4d, 3d, 2d, 1d, and 4h timeframes with efficient data aggregation
- **Parallel Processing**: Simultaneously scan multiple exchanges and timeframes for maximum efficiency
- **Smart Data Management**: Single 1d fetch for aggregated timeframes (2d, 3d, 4d) with intelligent cache management
- **VSA Strategies**: Breakout Bar, Stop Bar, Reversal Bar, Start Bar, Loaded Bar, Test Bar
- **Native Pattern Strategies**: Confluence, Consolidation Breakout, Channel Breakout, Loaded Bar, Trend Breakout, Pin Up, SMA50 Breakout
- **Composed Multi-Factor Strategies**: HBS Breakout, VS Wakeup
- **Futures-Only Strategies**: Reversal Bar, Pin Down for specialized futures analysis
- **Database Integration**: PostgreSQL support with market event tracking and deduplication
- **Telegram Integration**: Send alerts to multiple users and channels with priority-based notifications
- **Modular Architecture**: Easy to add new exchanges and strategies
- **Volume Filtering**: Focus on markets with significant trading volume
- **Jupyter Notebook Interface**: Run scans interactively and visualize results

## Project Structure

```
project/
├── breakout_vsa/               # VSA pattern detection logic
│   ├── __init__.py
│   ├── core.py
│   ├── helpers.py
│   └── strategies/
│       ├── __init__.py
│       ├── breakout_bar.py
│       ├── stop_bar.py
│       ├── reversal_bar.py
│       ├── start_bar.py
│       ├── loaded_bar.py
│       └── test_bar.py
├── custom_strategies/          # Custom pattern detection
│   ├── __init__.py
│   ├── volume_surge.py
│   ├── weak_uptrend.py
│   ├── pin_down.py
│   ├── pin_up.py               # Bullish pin pattern
│   ├── confluence.py           # Native: Multi-factor confirmation
│   ├── consolidation.py
│   ├── consolidation_breakout.py  # Native: Enhanced breakout detection
│   ├── channel.py
│   ├── channel_breakout.py     # Native: Diagonal channel breakouts
│   ├── sma50_breakout.py       # Native: Clean SMA breakouts
│   ├── trend_breakout.py       # Native: HBS-aligned trend breakout
│   └── wedge_breakout.py
├── exchanges/
│   ├── __init__.py
│   ├── base_client.py
│   ├── binance_futures_client.py
│   ├── binance_spot_client.py
│   ├── bybit_client.py
│   ├── gateio_client.py
│   ├── kucoin_client.py
│   ├── mexc_client.py
│   ├── sf_kucoin_client.py
│   └── sf_mexc_client.py
├── scanner/
│   ├── __init__.py
│   └── main.py                 # Unified orchestrator (Telegram + DB)
├── SFEvent/                    # Database model + insert helper
│   └── market_event_db_utils.py
├── aws_scanner/
│   ├── aws_scanner_service.py  # Optimized AWS service with prioritization
│   └── setup_aws_service.sh    # Enhanced setup script
├── utils/
│   ├── __init__.py
│   └── config.py
├── run_parallel_scanner.py     # Phased runner (FAST/SLOW)
└── vsa_and_custom_scanner.ipynb
```

## Strategy Classification

### Native Strategies (Priority 1 & 4)
**Foundational patterns that provide clean database population for future composed strategy development:**

- **confluence**: Multi-factor confirmation system combining volume, spread, and momentum
- **consolidation_breakout**: Breakout from horizontal consolidation patterns with strength classification
- **channel_breakout**: Breakout from diagonal channel patterns using robust statistical fitting
- **loaded_bar**: VSA-based accumulation/distribution detection
- **trend_breakout**: HBS-aligned trend breakout using Heikin-Ashi with AMA and Jurik smoothing
- **pin_up**: Bullish pin pattern (counterpart to pin_down)
- **sma50_breakout**: Clean moving average breakout detection with pre-breakout and strength analysis

### Composed Strategies (Priority 2 & 5)
**Multi-factor combinations that build upon native strategy foundations:**

- **hbs_breakout**: Hybrid Breakout Strategy combining consolidation/channel breakout + confluence signals with optional SMA50 and engulfing reversal components
- **vs_wakeup**: Volume Surge Wakeup combining consolidation pattern monitoring with confluence signal detection for anticipating breakout opportunities

### Futures-Only Strategies (Priority 3)
**Specialized patterns for futures markets:**

- **reversal_bar**: VSA-based potential trend reversal detection
- **pin_down**: Bearish continuation pattern for futures trend analysis

### Legacy/Utility Strategies
**Additional patterns for comprehensive coverage:**

- **volume_surge**: Abnormal volume spike detection
- **weak_uptrend**: Weakness pattern identification in uptrends
- **test_bar**: VSA support/resistance testing
- **wedge_breakout**: Diagonal consolidation wedge breakout detection
- **channel**: Ongoing diagonal channel monitoring
- **consolidation**: Horizontal consolidation pattern detection

## Session Management Flow

### Optimized Data Fetching Architecture
The scanner implements intelligent session management to minimize API calls and maximize efficiency:

```
Session Initialization:
├── Determine Active Timeframes for Today
├── Pre-Session Cache Assessment
├── Daily Data Requirement Analysis
└── Session-Level Cache Preparation

Data Fetching Optimization:
├── Native Timeframes (1d, 1w): Direct API fetch
├── Aggregated Timeframes (2d, 3d, 4d): Single 1d fetch + aggregation
└── Cross-Timeframe Data Reuse: Cache sharing between strategies

Cache Management:
├── Intra-Session: Preserve cache across same-session scans
├── Inter-Session: Clear cache after aggregated timeframe sessions
└── Daily Reset: Fresh cache start each trading day
```

### Cache Lifecycle Management
```python
# Cache clearing logic
def should_clear_cache_for_session(timeframes):
    aggregated_tfs = ["2d", "3d", "4d"]
    return any(tf in aggregated_tfs for tf in timeframes)

# Session flow
1. Daily 00:01 UTC: Clear all caches
2. Execute priority-based scans
3. Post-session: Clear cache if aggregated timeframes were used
4. Next day: Fresh start with clean cache
```

## Execution Flow and Priorities

### Daily Execution Schedule (00:01 UTC)
The optimized scanner follows a strict priority-based execution order designed to maximize database population speed and overall efficiency:

```
Priority 1: Fast Native Strategies
├── Exchanges: Binance, Bybit, Gate.io (spot + Binance futures)
├── Strategies: confluence, consolidation_breakout, channel_breakout, 
│              loaded_bar, trend_breakout, pin_up, sma50_breakout
├── Timeframes: 1d, 2d, 3d, 4d, 1w
├── Purpose: Rapid database population with foundational patterns
└── Result: Fastest alerts and cleanest data for composed strategy development

Priority 2: Fast Composed Strategies  
├── Exchanges: Binance, Bybit, Gate.io (spot + Binance futures)
├── Strategies: hbs_breakout, vs_wakeup
├── Timeframes: 1d, 2d, 3d, 4d, 1w
├── Purpose: Quick multi-factor analysis on fast exchanges
└── Result: High-quality composite signals with minimal latency

Priority 3: Fast Futures-Only Strategies
├── Exchanges: Binance, Bybit, Gate.io (futures only)
├── Strategies: reversal_bar, pin_down
├── Timeframes: 1d, 2d, 3d, 4d, 1w
├── Purpose: Specialized futures pattern analysis
└── Result: Futures-specific trend reversal and continuation signals

Priority 4: Slow Native Strategies
├── Exchanges: KuCoin, MEXC (spot)
├── Strategies: confluence, consolidation_breakout, channel_breakout,
│              loaded_bar, trend_breakout, pin_up, sma50_breakout  
├── Timeframes: 1d, 2d, 3d, 4d, 1w
├── Purpose: Comprehensive native pattern coverage
└── Result: Complete database population across all exchanges

Priority 5: Slow Composed Strategies
├── Exchanges: KuCoin, MEXC (spot)
├── Strategies: hbs_breakout, vs_wakeup
├── Timeframes: 1d, 2d, 3d, 4d, 1w
├── Purpose: Complete multi-factor analysis coverage
└── Result: Full strategy coverage with careful rate limiting
```

### Exchange Classification and Performance
```
Fast Exchanges (Priorities 1-3):
├── Binance (spot & futures): Highly reliable, fast API
├── Bybit (spot & futures): Excellent performance 
└── Gate.io (spot & futures): Stable and responsive

Slow Exchanges (Priorities 4-5):
├── KuCoin (spot): Requires careful rate limiting
└── MEXC (spot): Slower API responses, gentle handling

Reserved for Future:
└── MEXC (futures): Available but not actively used
```

### Timeframe Execution Logic
```
All Strategies Execute on All Timeframes:
├── 1d: Runs every day (native)
├── 2d: Runs every 2 days from Mar 20, 2025 reference (aggregated from 1d)
├── 3d: Runs every 3 days from Mar 20, 2025 reference (aggregated from 1d)  
├── 4d: Runs every 4 days from Mar 22, 2025 reference (aggregated from 1d)
└── 1w: Runs every Monday (native)

Smart Data Fetching:
├── Native timeframes: Direct exchange API calls
├── Aggregated timeframes: Single 1d fetch + mathematical aggregation
└── Cache optimization: Reuse 1d data across multiple aggregated timeframes
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
- psycopg2-binary (for database integration)
- sqlalchemy (for database models)

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
    "channel": "start_trend",
    "channel_breakout": "start_trend",
    "wedge_breakout": "start_trend",
    "sma50_breakout": "start_trend",
    "hbs_breakout": "hbs_breakout",
    "vs_wakeup": "start_trend",
    "trend_breakout": "start_trend",
    "pin_up": "start_trend"
}
```

### Database Configuration

Configure PostgreSQL integration in `utils/config.py`:

```python
DATABASE_CONFIG = {
    "enabled": True,  # Set to False to disable database integration
    "connection_string": "postgresql://username:password@host:port/database"
}
```

### Volume Thresholds

Adjust volume thresholds for different timeframes in `utils/config.py`:

```python
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

### Optimized AWS Service Deployment

The primary deployment method uses the optimized AWS service:

```bash
# Setup the service
cd aws_scanner
./setup_aws_service.sh

# Start the service
sudo systemctl start market-scanner.service

# Monitor execution
tail -f logs/scanner_service.log

# Check status with priority information
./status.sh
```

### Manual Scanning Examples

#### Native Strategy Scanning
```python
from run_parallel_scanner import run_parallel_multi_timeframes_all_exchanges

# Run native strategies for database population
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1d", "2d", "3d", "4d", "1w"],
    strategies=["confluence", "consolidation_breakout", "channel_breakout", 
               "loaded_bar", "trend_breakout", "pin_up", "sma50_breakout"],
    exchanges=["binance_spot", "bybit_spot", "gateio_spot", "binance_futures"],
    users=["default"],
    send_telegram=True
)
```

#### Composed Strategy Scanning
```python
# Run composed strategies after native strategies complete
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1d", "2d", "3d", "4d", "1w"],
    strategies=["hbs_breakout", "vs_wakeup"],
    exchanges=["binance_spot", "bybit_spot", "gateio_spot", "binance_futures"],
    users=["default", "user1", "user2"],
    send_telegram=True
)
```

## VSA Strategies

Volume Spread Analysis (VSA) is based on the relationship between volume, spread (range), and close position within the bar. The scanner implements six key VSA patterns:

### Breakout Bar
Detects bars that suggest the start of a new trend with:
- High volume (above average)
- Wide spread (large range)
- Close in upper portion of range (for bullish breakouts)

### Stop Bar
Identifies bars that suggest trend exhaustion:
- Very high volume
- Wide spread but close in opposite direction of trend
- Often marks temporary or permanent trend reversal

### Reversal Bar (Futures-Only)
Spots potential trend reversal bars:
- High volume
- Wide spread
- Close opposite to the prevailing trend direction

### Start Bar
Detects early trend initiation:
- Above average volume
- Good spread
- Close in direction of emerging trend

### Loaded Bar (Native Strategy)
Identifies accumulation/distribution:
- High volume with narrow spread
- Suggests professional money entering quietly
- Used as both VSA pattern and native strategy for database population

### Test Bar
Spots support/resistance testing:
- Low volume on revisit to previous support/resistance
- Narrow spread suggests lack of selling/buying pressure

## Native Strategies

Native strategies form the foundation of the scanning system, providing clean database population for future composed strategy development.

### Confluence (Native)
A sophisticated multi-factor confirmation system that combines Volume, Spread, and Momentum analysis:

**Detection Components:**
1. **VSA-Based Volume Analysis**: Direction-aware volume classification with local, broad, and serious volume conditions
2. **Dual-Direction Spread Analysis**: Separate bullish (close > 70% of range) and bearish (close < 30% of range) spread breakout detection
3. **Mirrored Momentum Scoring**: Independent bullish and bearish momentum calculations with weighted moving average validation

**Enhanced Features:**
- **Bidirectional Detection**: Both bullish and bearish confluence signals
- **Engulfing Reversal Recognition**: Detects trend reversals when opposite-direction signals occur consecutively
- **Multi-Timeframe Compatibility**: Runs on all timeframes (1d, 2d, 3d, 4d, 1w)

### Consolidation Breakout (Native)
An advanced breakout detection system combining horizontal consolidation boxes with diagonal channel analysis:

**Detection Logic:**
1. **Box Formation**: Identifies horizontal support/resistance levels
2. **Channel Inside Box**: Detects diagonal channels within consolidation using Theil-Sen robust regression
3. **Strength Classification**: 
   - **Strong**: Breakout clears both channel and box bounds
   - **Regular**: Breakout clears one bound or post-channel continuation
4. **ATR Filter**: Quiet market validation with height percentage checks

**Key Features:**
- Multi-level breakout validation
- Channel-inside-box detection for enhanced accuracy
- Strength labeling for trade quality assessment
- All timeframes supported with database integration

### Channel Breakout (Native)
Advanced diagonal channel breakout detection using robust statistical fitting:

**Technical Implementation:**
- **Theil-Sen Regression**: Robust statistical fitting resistant to outliers
- **Progressive Tightening**: Multi-level detection (35%, 25%, 15%)
- **ATR Volatility Filter**: Ensures breakout occurs during appropriate volatility
- **Direction Classification**: Clear upward/downward breakout identification

### SMA50 Breakout (Native)
Clean moving average breakout detection with advanced filtering:

**Types and Strength:**
- **Regular Breakout**: Close > SMA50 and Low < SMA50 with clean filter validation
- **Pre-Breakout**: Early signal when Close > SMA50 - 0.2*ATR(7)
- **Strength on Regular**: Strong if SMA50 in lower 35% of breakout bar body
- **Clean Filter**: Last N bars didn't close above SMA50 + ATR threshold

**Advanced Features:**
- Configurable lookback periods (default: 7 bars)
- ATR-based dynamic thresholds
- Volume confirmation integration
- Prevents late entries on extended moves

### Trend Breakout (Native)
HBS-aligned trend breakout using Heikin-Ashi with sophisticated smoothing:

**Technical Components:**
- **Heikin-Ashi Transformation**: Noise reduction and trend clarity
- **AMA Smoothing**: Adaptive Moving Average (2/2/30 parameters)
- **Jurik Smoothing**: JS 13/5 for additional noise reduction
- **Pivot High Detection**: ATR(7) buffer with 2-bar grace period
- **Multi-Filter System**: Momentum/MA/ATR filters to reduce false starts

### Pin Up (Native)
Bullish pin pattern detection (counterpart to pin_down):

**Detection Criteria:**
- Bullish candle formation near significant lows
- Within 3 bars, price breaks above the high of the bullish pin candle
- Pattern validation excludes outside bars
- Suggests bullish continuation after brief pullback

### Loaded Bar (Native)
VSA-based accumulation/distribution pattern:

**Identification Logic:**
- High volume with narrow spread (professional accumulation)
- Close position analysis for directional bias
- Volume ratio confirmation (significant above average)
- Multi-timeframe detection capability

## Composed Strategies

Composed strategies build upon native strategy foundations, combining multiple detection methods for higher-probability signals.

### HBS Breakout (Composed)
Hybrid Breakout Strategy combining multiple confirmation factors:

**Core Components (Required):**
- **Primary**: Either Consolidation Breakout OR Channel Breakout
- **Secondary**: Confluence Signal (Volume + Spread + Momentum alignment)

**Optional Enhancement Components:**
- **SMA50 Breakout**: Trend confirmation component
- **Engulfing Reversal**: Momentum shift confirmation
- **Volume Breakout**: Additional volume validation

**Signal Requirements:**
- Confluence signal must be present
- Either consolidation breakout OR channel breakout must occur simultaneously
- Optional components reported when detected for complete analysis

**Enhanced Telegram Notifications:**
```
Primary Context: ☰ Consolidation BO / ⧨ Channel BO / 📈 Both
Secondary Confirmations:
✅ 50SMA: Regular (Strong) - when SMA50 breakout detected
✅ Engulfing Reversal: Up - when reversal pattern present
✅ Volume breakout - when volume component strong
Strength: 💪 STRONG / 😐 REGULAR (for consolidation breakouts)
```

### VS Wakeup (Composed) 
Volume Surge Wakeup strategy combining consolidation monitoring with confluence detection:

**Strategy Logic:**
1. **Consolidation Component**: Detects ongoing horizontal consolidation patterns
2. **Confluence Component**: Identifies confluence signals with special "wakeup" mode
3. **Combined Analysis**: Reports when consolidation box shows confluence activity

**Detection Requirements:**
- Active consolidation pattern (no breakout detected)
- Confluence signal within consolidation box
- Box age tracking for pattern maturity
- All timeframes supported

**Purpose:**
- Anticipate breakout opportunities before they occur
- Monitor consolidation patterns for early breakout signs
- Provide advance warning of potential trend changes

**Telegram Notification Format:**
```
VS Wakeup Detection:
Symbol | Price | Volume
Box age: X bars
Close Position: ●○○ (percentage within current bar range)
```

## SF Weekly Scanning

The scanner includes enhanced weekly data access through the Seven Figures (SF) service for KuCoin and MEXC exchanges.

### SF Exchange Integration

#### Available SF Exchanges
```python
sf_exchanges_1w = ["sf_kucoin_1w", "sf_mexc_1w"]
```

#### Auto-Selection for Weekly Scans
The system automatically selects appropriate exchanges based on timeframes:
- **1w timeframe only**: Automatically uses SF exchanges
- **Mixed timeframes**: Uses regular exchanges
- **Validation**: SF exchanges restricted to 1w timeframe only

### SF Usage in Priority System
SF exchanges integrate seamlessly with the priority system:
```python
# Weekly-only scanning with SF exchanges
result = await run_parallel_multi_timeframes_all_exchanges(
    timeframes=["1w"],
    strategies=native_strategies + composed_strategies,
    exchanges=None,  # Auto-selects SF exchanges for 1w
    users=["default", "user1", "user2"],
    send_telegram=True
)
```

## Parallel Scanning

The parallel scanning system uses a phased approach with fast/slow exchange classification:

### Phased Execution (FAST → SLOW)
```
Environment Variables:
├── FAST_MAX_EXCHANGES=4 (concurrent fast exchanges)
├── SLOW_MAX_EXCHANGES=2 (concurrent slow exchanges)  
└── EXCHANGE_STAGGER_MS=250 (stagger timing)

Phase Execution:
├── FAST Phase: Binance, Bybit, Gate.io (higher parallelism)
└── SLOW Phase: KuCoin, MEXC, SF exchanges (lower parallelism)
```

### Multi-Layer Parallelism
```
Layer 1: Exchange-level batching (25 concurrent symbols per exchange)
Layer 2: Strategy-level parallelism (all strategies per symbol run concurrently)
Layer 3: Priority-based exchange grouping (fast before slow)
```

## Multi-User Support

The system supports sending notifications to multiple users with priority-based delivery:

```python
# Native strategies - highest priority users first
native_users = ["default", "user1", "user2"]

# Composed strategies - all users
composed_users = ["default", "user1", "user2"]

# Futures-only - primary user
futures_users = ["default"]
```

## Adding New Exchanges

To add a new exchange to the priority system:

1. **Classify Exchange Speed**:
```python
# Add to appropriate category
fast_spot_exchanges.append("new_fast_exchange")
# OR
slow_spot_exchanges.append("new_slow_exchange")
```

2. **Update Scan Configurations**:
```python
# Add to relevant priority configs
{
    "name": "fast_native_strategies",
    "exchanges": fast_spot_exchanges + ["binance_futures", "new_fast_exchange"],
    # ... other config
}
```

3. **Implement Client Class**: Create exchange client following existing patterns
4. **Test Priority Integration**: Verify proper execution order and API rate limiting

## Adding New Strategies

### Adding Native Strategies
Native strategies get highest priority for database population:

1. **Create Strategy File**: `custom_strategies/new_native_strategy.py`
2. **Add to Native List**: 
```python
native_strategies = [
    "confluence", "consolidation_breakout", "channel_breakout",
    "loaded_bar", "trend_breakout", "pin_up", "sma50_breakout",
    "new_native_strategy"  # Add here
]
```
3. **Database Integration**: Add columns to MarketEvent model for new strategy
4. **Scanner Integration**: Add detection logic to scanner/main.py

### Adding Composed Strategies
Composed strategies build on native strategy foundations:

1. **Create Strategy File**: `custom_strategies/new_composed_strategy.py`
2. **Implement Multi-Factor Logic**: Combine multiple native strategies
3. **Add to Composed List**:
```python
composed_strategies = [
    "hbs_breakout", "vs_wakeup", 
    "new_composed_strategy"  # Add here
]
```
4. **Priority Integration**: Composed strategies automatically get Priority 2 and 5

### Strategy Development Best Practices
- **Native First**: Develop fundamental patterns as native strategies
- **Database Ready**: Ensure native strategies support clean database insertion
- **Compose Later**: Build advanced strategies by combining native ones
- **Test All Timeframes**: Verify strategy works on 1d, 2d, 3d, 4d, 1w
- **Document Components**: Clearly document which native strategies are combined

## Troubleshooting

### Priority Execution Issues

1. **Native Strategies Not Executing First**:
```bash
# Check priority order in logs
tail -f logs/scanner_service.log | grep "Priority"
```

2. **Database Population Delays**:
- Verify native strategies are in Priority 1 and 4
- Check database connection and insert performance
- Monitor cache clearing between sessions

3. **Composed Strategy Dependencies**:
- Ensure all required native strategies are implemented
- Verify native strategies populate database before composed strategies run
- Check cross-strategy data dependencies

### Performance Optimization

1. **Slow Native Strategy Execution**:
```python
# Monitor per-strategy execution time
logger.info(f"Strategy {strategy} completed in {duration:.2f}s")
```

2. **Cache Management Issues**:
- Verify cache clearing logic for aggregated timeframes
- Monitor memory usage during multi-timeframe sessions
- Check session-level cache performance

3. **API Rate Limiting**:
- Adjust exchange stagger timing: `EXCHANGE_STAGGER_MS=500`
- Reduce concurrent exchanges: `FAST_MAX_EXCHANGES=2, SLOW_MAX_EXCHANGES=1`
- Monitor exchange-specific rate limit responses

### Strategy Development Debugging

1. **Native Strategy Testing**:
```python
# Test individual native strategies
from custom_strategies import detect_confluence
detected, result = detect_confluence(df, check_bar=-1)
```

2. **Composed Strategy Dependencies**:
```python
# Verify native strategy components
hbs_components = ["consolidation_breakout", "confluence"]
for component in hbs_components:
    # Test each component independently
```

3. **Database Integration Testing**:
```python
# Test database insertion for native strategies
from SFEvent.market_event_db_utils import insert_market_event
# Verify clean insertion without conflicts
```

## Recent Updates

### Version 2.10 Features (NEW)

- **Native/Composed Strategy Prioritization**: Complete reorganization with native strategies executing first for optimal database population, followed by composed strategies for advanced analysis
- **Optimized Session Management**: Single 1d data fetch for all aggregated timeframes (2d, 3d, 4d) with intelligent cache management and session-level optimization
- **Enhanced Priority System**: Five-tier priority system ensuring fastest database population and comprehensive coverage across all exchanges and timeframes
- **VS Wakeup Strategy**: New composed strategy combining consolidation monitoring with confluence detection for early breakout anticipation
- **Complete Timeframe Coverage**: All strategies now execute on all timeframes (1d, 2d, 3d, 4d, 1w) with unified configuration
- **Fast/Slow Exchange Classification**: Intelligent exchange categorization with Binance/Bybit/Gate.io as fast, KuCoin/MEXC as slow
- **Database-First Architecture**: Native strategies designed specifically for clean database population enabling future composed strategy development
- **Resource Optimization**: Memory limits, CPU quotas, and enhanced log rotation with 30-day retention
- **Enhanced AWS Service**: Complete systemd service integration with security hardening and graceful shutdown handling

### Version 2.9 Features

- **Unified Entrypoint**: `scanner/main.py` replaces legacy implementations with support for both Telegram alerts and PostgreSQL database insertion
- **Database Integration**: New `SFEvent/market_event_db_utils.py` with `MarketEvent` SQLAlchemy model and idempotent `insert_market_event()` helper
- **Parallel Orchestrator**: `run_parallel_scanner.py` with phased execution (FAST vs SLOW exchanges) and tunable environment variables
- **Trend Breakout Strategy**: New native strategy using Heikin-Ashi + AMA + Jurik smoothing with pivot-aware breakout detection
- **Pin Up Strategy**: Bullish counterpart to Pin Down for comprehensive reversal pattern coverage
- **Enhanced Consolidation Breakout**: v2 with channel-inside detection and Strong/Regular strength classification
- **Advanced SMA50 Breakout**: v2 with Regular/Pre-breakout types and Weak/Strong strength analysis plus clean filter

### Version 2.8 Features

- **Parallel Strategy Execution**: Strategies run concurrently within symbol scans using `asyncio.gather()` for maximum performance
- **ThreadPoolExecutor Integration**: CPU-intensive pandas operations moved to thread pools preventing async event loop blocking
- **Optimized Batch Processing**: Increased symbol batch size with enhanced throughput while respecting API rate limits
- **Thread-Safe Architecture**: Complete rewrite with proper import scoping and error isolation
- **VSA Parameters Caching**: Strategy parameters cached to eliminate repeated imports and function calls
- **Enhanced Error Handling**: Individual strategy failures no longer crash entire symbol scans
- **Two-Level Parallelism**: Symbol-level batching combined with strategy-level parallelism for maximum efficiency

### Version 2.7 Features

- **Enhanced HBS Breakout Strategy**: Advanced multi-component analysis with SMA50 and engulfing reversal detection
- **Component Detection**: HBS strategy reports when secondary technical components (SMA50 breakout, engulfing reversal) are present
- **Optimized API Data Fetching**: Updated fetch limits ensuring sufficient data for SMA50 calculations across all timeframes
- **Enhanced Telegram Notifications**: Visual indicators for secondary technical components in HBS breakout messages
- **Weekly Data Consistency**: Enhanced handling of MEXC and KuCoin weekly data aggregation for Sunday weekly closes
- **Multi-Factor Signal Analysis**: Comprehensive technical analysis showing which confluence factors drive breakout signals

### Version 2.6 Features

- **Channel Strategy**: Ongoing diagonal channel monitoring for consolidation patterns before breakouts occur
- **Enhanced Pattern Detection**: Real-time monitoring with progressive tightening detection (40%, 35%, 25%, 15%)
- **ATR-Based Validation**: Volatility filtering ensuring channel formation quality
- **Direction Classification**: Upward, downward, and horizontal trending channel identification
- **Complementary Strategy Design**: Works alongside Channel Breakout for complete pattern coverage

### Version 2.5 Features

- **Enhanced Confluence Strategy**: Bidirectional bullish/bearish confluence detection with VSA-based volume analysis
- **Engulfing Reversal Recognition**: Automatic detection of trend reversal patterns when opposite-direction signals occur
- **Dual Momentum Scoring**: Independent bullish and bearish momentum calculations with mirrored positioning logic
- **Improved Signal Prioritization**: Current bar and reversal pattern prioritization in scanner execution
- **Robust NaN Handling**: Improved early-bar processing with safe WMA warmup periods

### Version 2.4 Features

- **Wedge Breakout Strategy**: Advanced diagonal consolidation wedge breakout detection using Theil-Sen regression
- **Progressive Wedge Monitoring**: Real-time tracking with dynamic tightening detection at four quality levels
- **Multi-Level Detection**: Tightness thresholds at 40%, 35%, 25%, 15% for different wedge qualities
- **ATR Volatility Integration**: Wedge formation validation during low volatility periods
- **Logarithmic Scale Support**: Optional log-scale processing for percentage-based wedge analysis

### Version 2.3 Features

- **SF Exchange Integration**: Enhanced KuCoin and MEXC weekly data via Seven Figures service
- **50SMA Breakout Strategy**: Clean moving average breakout detection with configurable clean filters
- **SF Exchange Validation**: Automatic timeframe compatibility checking for SF exchanges
- **Enhanced Weekly Scanning**: Improved weekly timeframe analysis capabilities with SF data quality
- **Smart Exchange Selection**: Auto-selection of appropriate exchanges based on requested timeframes

### Version 2.2 Features

- **Channel Breakout Strategy**: Advanced diagonal channel breakout detection using Theil-Sen robust regression
- **Enhanced Channel Analysis**: Robust statistical fitting for trending channel patterns resistant to outliers
- **Multi-Level Tightness Detection**: Progressive tightening thresholds ensuring high-quality breakout signals
- **ATR Volatility Filtering**: Enhanced volatility confirmation for channel formation and breakout validation

### Version 2.1 Features

- **Consolidation Breakout Strategy**: Advanced breakout detection with channel confirmation and strength classification
- **HBS Breakout Strategy**: Hybrid strategy combining consolidation and confluence signals for high-probability setups
- **Extended Timeframe Support**: Added 3d and 4d timeframes for medium-term analysis with proper aggregation
- **Enhanced Telegram Notifications**: Direction indicators, detailed breakout metrics, and component analysis
- **Parallel Processing Engine**: Complete rewrite enabling concurrent operations across exchanges and strategies

---

This documentation reflects the complete evolution of the cryptocurrency market scanner, showcasing its progression from basic pattern detection to a sophisticated, database-driven system with optimized native/composed strategy prioritization and comprehensive multi-exchange coverage.