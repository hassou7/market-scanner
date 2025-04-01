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
- Implements staggered scanning to prevent exchange API rate limiting

## Installation on AWS

1. **Connect to your EC2 instance**

```bash
ssh -i "/path/to/your-key.pem" ec2-user@your-instance-ip
```

For example:
```bash
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@13.53.165.65
```

2. **Clone your repository or upload your code**

```bash
# Option 1: If using git
git clone https://github.com/yourusername/market-scanner.git

# Option 2: Create directories for manual file uploads
mkdir -p market-scanner/aws_scanner/logs
```

3. **If uploading manually, use SCP in a separate terminal window**

```bash
# Upload the main project files
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" -r /path/to/your/Project/* ec2-user@13.53.165.65:~/market-scanner/

# Upload the AWS scanner files
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" aws_scanner_service.py ec2-user@13.53.165.65:~/market-scanner/aws_scanner/
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" market-scanner.service ec2-user@13.53.165.65:~/market-scanner/aws_scanner/
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" setup_aws_service.sh ec2-user@13.53.165.65:~/market-scanner/aws_scanner/
```

4. **Run the setup script**

```bash
cd ~/market-scanner/aws_scanner
chmod +x setup_aws_service.sh
./setup_aws_service.sh
```

5. **Start the service**

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

### Staggered Scan Logic

The service implements a staggered scanning approach to prevent exchange API rate limiting:

1. **When multiple timeframes need to be scanned at the same time (like Monday 00:00 UTC when 4h, 1d, and 1w coincide):**
   - Scans are prioritized in the following order: 1d, 4h, 1w, 2d
   - A 1-minute delay is added between different timeframe scans
   - This prevents API rate limiting while keeping scans as timely as possible

2. **For normal operation (non-overlapping scans):**
   - Each timeframe is scanned at its appropriate candle close time

You can adjust the priority order in the code if needed:
```python
# Sort by priority: 1d, 4h, 1w, 2d (most important to least)
priority_order = {"1d": 0, "4h": 1, "1w": 2, "2d": 3}
```

## Special Timeframe Handling

- **4-Hour Candles**: Closes at 0, 4, 8, 12, 16, 20 UTC
- **Daily Candles**: Closes at 00:00 UTC
- **2-Day Candles**: Based on the reference date of March 20, 2025
- **Weekly Candles**: Starts on Monday and closes on Sunday night/Monday morning at 00:00 UTC

## Monitoring

### Check Service Status

```bash
sudo systemctl status market-scanner.service
```

### View Logs

```bash
# View the main application log
tail -f ~/market-scanner/aws_scanner/logs/scanner_service.log

# View systemd output logs
tail -f ~/market-scanner/aws_scanner/logs/systemd_output.log

# View systemd error logs
tail -f ~/market-scanner/aws_scanner/logs/systemd_error.log
```

### Restart the Service

```bash
sudo systemctl restart market-scanner.service
```

## Updating the Service

If you make changes to the service script:

```bash
# Edit the file
nano ~/market-scanner/aws_scanner/aws_scanner_service.py

# Restart the service
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
cd ~/market-scanner
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
