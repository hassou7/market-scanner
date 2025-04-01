# Market Scanner AWS Service

This folder contains everything needed to run your market pattern scanner as a service on AWS EC2.

## Directory Structure

```
Project/
├── aws_scanner/             # AWS service components
│   ├── aws_scanner_service.py   # Main service script
│   ├── market-scanner.service   # Systemd service configuration
│   ├── setup_aws_service.sh     # Setup script
│   ├── README.md                # This file
│   └── logs/                    # Log files (created automatically)
│       ├── scanner_service.log  # Main application logs
│       ├── systemd_output.log   # Standard output logs
│       └── systemd_error.log    # Error logs
├── scanner/                 # Your existing scanner code
├── exchanges/               # Your existing exchange clients
├── breakout_vsa/            # Your existing VSA pattern detection code
└── run_scanner.py           # Your existing scanner runner
```

## Features

- Runs scans at appropriate times for different timeframes (4h, 1d, 2d, 1w)
- Respects specific timing for 2d and 1w candles based on exchange implementations
- Uses your existing code structure and functions
- Sends Telegram notifications for detected patterns
- Runs as a systemd service with automatic restart on failure

## Installation on AWS

1. **Clone your repository to the AWS EC2 instance**

```bash
git clone https://github.com/yourusername/market-scanner.git
cd market-scanner
```

2. **Run the setup script**

```bash
cd aws_scanner
chmod +x setup_aws_service.sh
./setup_aws_service.sh
```

3. **Start the service**

```bash
sudo systemctl start market-scanner.service
```

## Configuration

The scanner is configured in the `aws_scanner_service.py` file. You can modify:

### Exchange Lists

```python
# List of spot exchanges to scan
spot_exchanges = [
    "binance_spot",
    "bybit_spot", 
    # ...
]

# List of futures exchanges to scan
futures_exchanges = [
    "binance_futures",
    "bybit_futures",
    # ...
]
```

### Scan Configurations

```python
# Futures exchanges scan configurations
futures_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True
    },
    # ...
]

# Spot exchanges scan configurations
spot_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["start_bar", "breakout_bar"],
        "exchanges": spot_exchanges,
        "users": ["default"],
        "send_telegram": True
    },
    # ...
]
```

## Monitoring

### Check Service Status

```bash
sudo systemctl status market-scanner.service
```

### View Logs

```bash
# View the main application log
tail -f aws_scanner/logs/scanner_service.log

# View systemd output logs
tail -f aws_scanner/logs/systemd_output.log

# View systemd error logs
tail -f aws_scanner/logs/systemd_error.log
```

### Restart the Service

```bash
sudo systemctl restart market-scanner.service
```

## Debugging

If you need more detailed logs, you can restart the service with debug logging:

1. Stop the service:
```bash
sudo systemctl stop market-scanner.service
```

2. Run manually with debug flag:
```bash
cd /home/ec2-user/market-scanner
source venv/bin/activate
python aws_scanner/aws_scanner_service.py --debug
```

## Stopping the Service

```bash
sudo systemctl stop market-scanner.service
```

To disable the service from starting at boot:

```bash
sudo systemctl disable market-scanner.service
```
