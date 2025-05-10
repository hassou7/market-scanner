# Cryptocurrency Market Scanner Documentation

A comprehensive market scanner for cryptocurrency exchanges that combines VSA (Volume Spread Analysis) strategies with custom pattern detection algorithms.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [VSA Strategies](#vsa-strategies)
8. [Custom Strategies](#custom-strategies)
9. [Multi-User Support](#multi-user-support)
10. [Adding New Exchanges](#adding-new-exchanges)
11. [Adding New Strategies](#adding-new-strategies)
12. [Troubleshooting](#troubleshooting)

## Project Overview

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms like volume surge, weak uptrend, and pin down pattern detection.

The scanner supports multiple exchanges including Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit. It can analyze various timeframes (1w, 2d, 1d, 4h) and send notifications via Telegram to multiple users.

## Features

- **Multiple Exchange Support**: Scan Binance (spot and futures), Gate.io, KuCoin, MEXC, and Bybit markets
- **Multiple Timeframes**: Analyze 1w, 2d, 1d, and 4h timeframes
- **VSA Strategies**:
  - Breakout Bar for trend starts
  - Stop Bar for trend reversals
  - Reversal Bar for potential reversals
- **Custom Strategies**:
  - Volume Surge detection
  - Weak Uptrend detection with 5 pattern types
  - Pin Down pattern for bearish continuation
- **Telegram Integration**: Send alerts to multiple users and channels
- **Modular Architecture**: Easy to add new exchanges and strategies
- **Batch Processing**: Efficiently scan hundreds of markets in parallel
- **Volume Filtering**: Focus on markets with significant trading volume
- **Jupyter Notebook Interface**: Run scans interactively and visualize results

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
│       ├── start_bar.py     # Reversal Bar strategy parameters
│       ├── loaded_bar.py         # Stop Bar strategy parameters
│       └── test_bar.py     # Reversal Bar strategy parameters
├── custom_strategies/          # Custom pattern detection
│   ├── __init__.py             # Main imports
│   ├── volume_surge.py         # Volume surge detection
│   ├── weak_uptrend.py         # Weak uptrend detection
│   └── pin_down.py             # Pin down pattern detection
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
│   ├── main.py                 # Scanner main functions
│   ├── market_scanner.py       # VSA-based market scanner
│   └── custom_scanner.py       # Custom strategy scanner
├── utils/                      # Utility functions and configuration
│   ├── __init__.py
│   └── config.py               # Configuration values
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
# Telegram tokens for different channels
TELEGRAM_TOKENS = {
    "volume_surge": "YOUR_VOLUME_SURGE_TOKEN",
    "start_trend": "YOUR_START_TREND_TOKEN",
    "weakening_trend": "YOUR_WEAKENING_TREND_TOKEN"
}

# Map strategies to default channels
STRATEGY_CHANNELS = {
    "breakout_bar": "start_trend",
    "stop_bar": "weakening_trend",
    "reversal_bar": "weakening_trend"
}

# Multiple users configuration
TELEGRAM_USERS = {
    "default": {
        "chat_id": "YOUR_DEFAULT_CHAT_ID",
        "name": "Your Name"
    },
    "user1": {
        "chat_id": "USER1_CHAT_ID",
        "name": "User 1"
    },
    # Add more users as needed
}
```

### Volume Thresholds

Adjust volume thresholds for different timeframes in `utils/config.py`:

```python
# Volume thresholds
VOLUME_THRESHOLDS = {
    "1w": 300000,  # Weekly volume threshold in USD
    "2d": 100000,  # 2-day volume threshold in USD
    "1d": 50000,   # Daily volume threshold in USD
    "4h": 20000    # 4-hour volume threshold in USD
}
```

## Usage

### Running the Jupyter Notebook

Start Jupyter and open the `vsa_and_custom_scanner.ipynb` notebook:

```bash
jupyter notebook
```

### VSA-Based Scanning

Run a VSA strategy scan with:

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

### Custom Strategy Scanning

Run custom strategy scans with:

```python
await run_custom_scan(
    exchange='binance_futures',
    timeframe='4h',
    strategies=['volume_surge', 'weak_uptrend', 'pin_down'],
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

## Multi-User Support

The system supports sending notifications to multiple users:

1. Add users to `TELEGRAM_USERS` in `utils/config.py`
2. For VSA strategies, specify the user ID when running a scan:
   ```python
   await run_scan(
       timeframe='4h', 
       strategy='breakout_bar', 
       exchange="binance_spot", 
       send_telegram=True,
       user_id="user1"  # Use the user ID from TELEGRAM_USERS
   )
   ```

3. For custom strategies, add user chat IDs to the `CUSTOM_TELEGRAM_CONFIG` in the notebook:
   ```python
   CUSTOM_TELEGRAM_CONFIG['volume_surge']['chat_ids'].append(TELEGRAM_USERS["user1"]["chat_id"])
   ```

## Adding New Exchanges

To add a new exchange:

1. Create a new client class in `exchanges/` that inherits from `BaseExchangeClient`
2. Implement all required methods (`_get_interval_map`, `_get_fetch_limit`, `get_all_spot_symbols`, `fetch_klines`)
3. Update the exchange mapping in `scanner/main.py` to include the new exchange

Example of a minimal exchange client:

```python
from .base_client import BaseExchangeClient

class NewExchangeClient(BaseExchangeClient):
    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.newexchange.com"
        super().__init__(timeframe)

    def _get_interval_map(self):
        return {
            '1w': '1week',
            '2d': '1day',  # Will aggregate
            '1d': '1day',
            '4h': '4hour'
        }
    
    def _get_fetch_limit(self):
        return {
            '1w': 60,
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

### Adding a New Custom Strategy

1. Create a new strategy file in `custom_strategies/`
2. Define a detection function that returns a boolean and a result dictionary
3. Update `custom_strategies/__init__.py` to expose your new function
4. Update `scanner/custom_scanner.py` to support the new strategy
5. Update `CUSTOM_TELEGRAM_CONFIG` in the notebook to include your strategy

## Troubleshooting

### Common Issues

1. **Circular Import Errors**:
   - Ensure imports are properly ordered in `__init__.py` files
   - Use local imports within functions where needed

2. **API Rate Limiting**:
   - Adjust `request_delay` in exchange clients
   - Reduce `batch_size` for high-traffic exchanges

3. **Telegram Bot Issues**:
   - Verify token correctness
   - Ensure the bot has been started by the user
   - Check permission to post in groups

4. **No Results Found**:
   - Check volume thresholds in `config.py`
   - Verify the strategy parameters
   - Ensure exchange API is functioning correctly

### Logging

The system uses Python's logging module. To increase logging verbosity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

For file-based logging, add:

```python
handler = logging.FileHandler('scanner.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.