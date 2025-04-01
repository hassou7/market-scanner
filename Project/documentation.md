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
10. [AWS Service Setup](#aws-service-setup)
11. [Adding New Exchanges](#adding-new-exchanges)
12. [Adding New Strategies](#adding-new-strategies)
13. [Troubleshooting](#troubleshooting)

## Project Overview

This project is a cryptocurrency market scanner designed to detect profitable trading opportunities across multiple exchanges and timeframes. It employs both traditional Volume Spread Analysis (VSA) techniques and custom pattern detection algorithms like volume surge, weak uptrend, and pin down pattern detection.

The scanner supports multiple exchanges including Binance (spot and futures), Bybit (spot and futures), Gate.io (spot and futures), KuCoin, and MEXC (spot and futures). It can analyze various timeframes (1w, 2d, 1d, 4h) and send notifications via Telegram to multiple users.

## Features

- **Multiple Exchange Support**: Scan Binance, Bybit, Gate.io, KuCoin, and MEXC markets (both spot and futures where available)
- **Multiple Timeframes**: Analyze 1w, 2d, 1d, and 4h timeframes
- **VSA Strategies**:
  - Breakout Bar for trend starts
  - Stop Bar for trend reversals
  - Reversal Bar for potential reversals
  - Start Bar for new trend identification
- **Custom Strategies**:
  - Volume Surge detection
  - Weak Uptrend detection
  - Pin Down pattern for bearish continuation
- **Telegram Integration**: Send alerts to multiple users and channels
- **Modular Architecture**: Easy to add new exchanges and strategies
- **Batch Processing**: Efficiently scan hundreds of markets in parallel
- **Volume Filtering**: Focus on markets with significant trading volume
- **Jupyter Notebook Interface**: Run scans interactively and visualize results
- **AWS Service**: Run as a scheduled service on AWS EC2

## Project Structure

```
Project/
├── aws_scanner/               # AWS service components
│   ├── aws_scanner_service.py   # Service script
│   ├── market-scanner.service   # Systemd service configuration
│   ├── setup_aws_service.sh     # Setup script
│   └── logs/                    # Service logs
├── breakout_vsa/               # VSA pattern detection logic
│   ├── __init__.py             # Main imports
│   ├── core.py                 # Core VSA detector functions
│   ├── helpers.py              # Helper functions for indicators
│   └── strategies/             # Strategy parameter files
│       ├── __init__.py
│       ├── breakout_bar.py     # Breakout Bar strategy parameters
│       ├── stop_bar.py         # Stop Bar strategy parameters
│       ├── reversal_bar.py     # Reversal Bar strategy parameters
│       └── start_bar.py        # Start Bar strategy parameters
├── custom_strategies/          # Custom pattern detection
│   ├── __init__.py             # Main imports
│   ├── volume_surge.py         # Volume surge detection
│   ├── weak_uptrend.py         # Weak uptrend detection
│   └── pin_down.py             # Pin down pattern detection
├── exchanges/                  # Exchange API clients
│   ├── __init__.py
│   ├── base_client.py          # Base exchange client class
│   ├── binance_futures_client.py  # Binance Futures client
│   ├── binance_spot_client.py  # Binance Spot client
│   ├── bybit_client.py         # Bybit Spot client
│   ├── bybit_futures_client.py # Bybit Futures client
│   ├── gateio_client.py        # Gate.io Spot client
│   ├── gateio_futures_client.py # Gate.io Futures client
│   ├── kucoin_client.py        # KuCoin client
│   ├── mexc_client.py          # MEXC Spot client
│   └── mexc_futures_client.py  # MEXC Futures client
├── scanner/                    # Market scanning logic
│   ├── __init__.py
│   └── main.py                 # Unified scanner for VSA and custom strategies
├── utils/                      # Utility functions and configuration
│   ├── __init__.py
│   └── config.py               # Configuration values
└── run_scanner.py              # Script to run scans
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hassou7/market-scanner.git
cd market-scanner
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
- tqdm

## Configuration

### Telegram Configuration

To set up Telegram notifications, you'll need to create bot tokens and get chat IDs for each user.

1. Create Telegram bots using [@BotFather](https://t.me/BotFather)
2. Get your chat ID using [@userinfobot](https://t.me/userinfobot)
3. Configure the tokens in your code

Example configuration in a Jupyter notebook:

```python
# Telegram configuration for different strategies
TELEGRAM_CONFIG = {
    "volume_surge": {
        "token": "YOUR_VOLUME_SURGE_TOKEN",
        "chat_ids": ["YOUR_CHAT_ID"]
    },
    "start_bar": {
        "token": "YOUR_START_BAR_TOKEN",
        "chat_ids": ["YOUR_CHAT_ID"]
    },
    "reversal_bar": {
        "token": "YOUR_REVERSAL_BAR_TOKEN",
        "chat_ids": ["YOUR_CHAT_ID"]
    }
}
```

## Usage

### Running in Jupyter Notebook

To run scans from a Jupyter notebook:

```python
import asyncio
import sys
import os
project_dir = os.path.join(os.getcwd(), "Project")
sys.path.insert(0, project_dir)
print(f"✓ Added {project_dir} to sys.path")
from run_scanner import run, run_all_exchanges

# Define exchange lists
spot_exchanges = [
    "binance_spot",
    "bybit_spot", 
    "gateio_spot",
    "kucoin_spot",
    "mexc_spot"
]

futures_exchanges = [
    "binance_futures",
    "bybit_futures",
    "gateio_futures",
    "mexc_futures"
]

# Run a scan on a single exchange with a specific strategy
result1 = await run(
    exchange="binance_futures",
    timeframe="4h",
    strategies=["volume_surge"],
    users=["default"],
    send_telegram=True
)

# Run a scan on all futures exchanges with multiple strategies
result2 = await run_all_exchanges(
    timeframe="4h",
    strategies=["reversal_bar", "pin_down"],
    exchanges=futures_exchanges,
    users=["default"],
    send_telegram=True
)

# Run a scan on all spot exchanges with different strategies
result3 = await run_all_exchanges(
    timeframe="1d",
    strategies=["start_bar", "breakout_bar"],
    exchanges=spot_exchanges,
    users=["default"],
    send_telegram=True
)
```

### Running Directly from Python

You can also run the scanner directly using a Python script:

```python
import asyncio
from run_scanner import run

async def main():
    await run(
        exchange="binance_futures",
        timeframe="4h",
        strategies=["reversal_bar"],
        users=["default"],
        send_telegram=True
    )

if __name__ == "__main__":
    asyncio.run(main())
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

A start bar is characterized by:
- Higher volume than previous bars
- Higher high
- Good range (not narrow)
- Close in the upper portion of the bar
- Located near a significant low

This pattern helps identify the beginning of a new uptrend after a prolonged decline.

## Custom Strategies

### Volume Surge

Detects bars with abnormally high volume (typically 4+ standard deviations above average) and calculates a score based on price action and range. Useful for identifying significant market events and potential trend changes.

Parameters:
- `lookback_period`: Number of bars to consider for volume statistics (default: 65)
- `std_dev`: Standard deviations above mean to consider a volume surge (default: 4.0)

### Weak Uptrend

Identifies bars showing weakness in an uptrend, which could signal potential reversal or correction. This strategy detects multiple signs of weakness including divergence between price and volume.

### Pin Down

Detects a bearish continuation pattern where:
1. A bearish candle forms near a significant high (bearish top)
2. Within a few bars, price breaks below the low of the bearish top candle
3. The pattern is NOT an outside bar

This pattern suggests continuation of a downtrend after a brief pullback.

## Multi-User Support

To send notifications to multiple users:

1. Add users to your Telegram configuration:
```python
# Add another user
TELEGRAM_CONFIG["volume_surge"]["chat_ids"].append("ANOTHER_USER_CHAT_ID")
```

2. Specify multiple users when running a scan:
```python
await run(
    exchange="binance_futures",
    timeframe="4h",
    strategies=["volume_surge"],
    users=["default", "user2"],
    send_telegram=True
)
```

## AWS Service Setup

The scanner can be run as a scheduled service on an AWS EC2 instance:

1. **Upload the Code to AWS**:
```bash
# Clone your repository to AWS
git clone https://github.com/hassou7/market-scanner.git
mkdir -p ~/market-scanner/aws_scanner/logs
```

2. **Set Up the Service**:
```bash
cd ~/market-scanner/aws_scanner
chmod +x setup_aws_service.sh
./setup_aws_service.sh
```

3. **Start the Service**:
```bash
sudo systemctl start market-scanner.service
```

4. **Monitor the Service**:
```bash
# Check service status
sudo systemctl status market-scanner.service

# View logs
tail -f ~/market-scanner/aws_scanner/logs/scanner_service.log
```

The AWS service will automatically run scans at the appropriate times for different timeframes:
- 4h scans: Every 4 hours (00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC)
- 1d scans: Daily at 00:01 UTC
- 2d scans: Every other day at 00:01 UTC (based on March 20, 2025 reference)
- 1w scans: Weekly on Monday at 00:01 UTC

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

1. Create a new strategy file in `breakout_vsa/strategies/` (e.g., `new_strategy.py`)
2. Define parameters in the `get_params()` function:
   ```python
   def get_params():
       return {
           'lookback': 14,
           'direction_opt': "Up",
           # Add other parameters
       }
   ```

3. Update `breakout_vsa/core.py` to handle the new strategy
4. Import and use the strategy in your scans:
   ```python
   await run(
       exchange="binance_futures",
       timeframe="4h",
       strategies=["new_strategy"],
       users=["default"],
       send_telegram=True
   )
   ```

### Adding a New Custom Strategy

1. Create a new strategy file in `custom_strategies/` (e.g., `new_custom.py`)
2. Define a detection function that returns a boolean and a result dictionary:
   ```python
   def detect_new_pattern(df, param1=default1, param2=default2):
       # Detection logic here
       detected = some_condition
       result = {
           'timestamp': df.index[-2],
           'key1': value1,
           'key2': value2
       }
       return detected, result
   ```

3. Update `custom_strategies/__init__.py` to export your function
4. Update `scanner/main.py` to handle your new strategy
5. Use the strategy in your scans

## Troubleshooting

### Common Issues

1. **Exchange API Rate Limiting**:
   - Add delays between requests
   - Reduce batch size for scanning
   - Implement intelligent caching

2. **Telegram Bot Issues**:
   - Verify token correctness
   - Ensure the bot has been started by the user
   - Check permission to post in groups

3. **AWS Service Not Starting**:
   - Check systemd logs: `sudo journalctl -u market-scanner.service`
   - Verify Python path is correct
   - Check file permissions

4. **No Patterns Detected**:
   - Verify volume threshold settings
   - Check strategy parameters
   - Ensure market data is being fetched correctly

### Debug Mode

For more detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# For AWS service, run with debug flag
python aws_scanner/aws_scanner_service.py --debug
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
