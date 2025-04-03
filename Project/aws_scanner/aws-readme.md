# Market Scanner AWS Service

This folder contains everything you need to run your cryptocurrency market pattern scanner as a service on an AWS EC2 instance. This guide is written for beginners, so don't worry if you're new to this—we'll walk you through each step!

## Directory Structure

```
Project/
├── aws_scanner/             # AWS service components
│   ├── aws_scanner_service.py   # Main service script
│   ├── market-scanner.service   # Systemd service configuration
│   ├── setup_aws_service.sh     # Setup script
│   ├── README.md                # This file (you're reading it!)
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

- Runs scans automatically for different timeframes (4h, 1d, 2d, 1w)
- Optimized for Timeframes: Scans are scheduled and prioritized by timeframe (4h, 1d, 2d, 1w) with smart cache management to reuse data (e.g., 1d data for 2d and 1w scans)
- Uses your existing scanner code to find trading patterns
- Sends notifications to Telegram when patterns are detected
- Runs as a background service that restarts if it crashes
- Staggers scans to avoid overwhelming exchange APIs

## Installation on AWS

1. **Connect to your EC2 instance**

```bash
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@13.53.165.65
```

2. **Remove Old Files (If Any)**

Move to your home directory and remove the market-scanner folder and everything inside it:

```bash
rm -rf market-scanner
```

3. **Clone your repository or upload your code**

```bash
# Option 1: If using git
git clone https://github.com/hassou7/market-scanner.git

# Option 2: Create directories for manual file uploads
mkdir -p market-scanner/Project/aws_scanner/logs
```

4. **Install Required Tools**

Update your server and install Python and Git:

```bash
sudo yum update -y
sudo yum install python3 python3-pip git -y
```

Install the Python libraries the scanner needs:

```bash
pip3 install pandas numpy asyncio aiohttp python-telegram-bot tqdm
```

5. **Set Up the Service**

a. Move to the aws_scanner folder:

```bash
cd ~/market-scanner/Project/aws_scanner/
```

b. Make the setup script runnable:

```bash
chmod +x setup_aws_service.sh
```

c. Run the setup script:

```bash
./setup_aws_service.sh
```

This sets up the service so it can run in the background.

6. **Launch the Service**

Start the scanner service:

```bash
sudo systemctl start market-scanner.service
```

Look for `Active: active (running)` in the output. If you see that, it's working!

7. **Look at the Logs**

```bash
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

You'll see messages like "Next scan: 4h at [time]". Press Ctrl+C to stop watching the logs.

8. **Restarting the Service**

If you change something or it stops working:

```bash
sudo systemctl restart market-scanner.service
```

This stops and starts it again.

9. **Stopping the Service**

If you need to stop the service:

```bash
sudo systemctl stop market-scanner.service
```

It'll stop running until you start it again.

## Monitoring

### View Logs

```bash
# View the main application log
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# View systemd output logs
tail -f ~/market-scanner/Project/aws_scanner/logs/systemd_output.log

# View systemd error logs
tail -f ~/market-scanner/Project/aws_scanner/logs/systemd_error.log
```

This shows the latest updates. Use Ctrl+C to exit.

## Updating the Service

If you make changes to the service script:

```bash
# Edit the file
nano ~/market-scanner/Project/aws_scanner/aws_scanner_service.py

# Restart the service
sudo systemctl restart market-scanner.service
```

## Updating the Service Remotely

To update the AWS scanner service while it's running, you can use SCP to upload new files from your local machine:

```bash
# Upload updated aws_scanner_service.py from your local machine
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" path\to\aws_scanner_service.py ec2-user@13.53.165.65:~/market-scanner/Project/aws_scanner/

# Then SSH to the instance and restart the service
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@13.53.165.65 "sudo systemctl restart market-scanner.service"
```

You can also update multiple files at once:

```bash
# Upload multiple files
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" path\to\aws_scanner\*.py ec2-user@13.53.165.65:~/market-scanner/Project/aws_scanner/
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

## Configuration Details

### Scan Settings

```python
futures_scan_configs = [
    {
        "timeframe": "4h",
        "strategies": ["reversal_bar", "pin_down"],
        "exchanges": futures_exchanges,
        "users": ["default"],
        "send_telegram": True
    }
]
```

### Scan Timing

- **4-Hour Scans**: Every 4 hours (00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC)
- **Daily Scans**: Every day at 00:01 UTC
- **2-Day Scans**: Every other day at 00:01 UTC (based on March 20, 2025)
- **Weekly Scans**: Every Monday at 00:01 UTC

### Timeframe Optimization

- **Scans are prioritized**: 4h first (most time-sensitive), then 1d, 2d, and finally 1w
- If multiple timeframes align (e.g., Monday 00:01 UTC), they run in order with a 1-minute delay between them
- **Cache Management**: 
  - Processes 4h first with a fresh cache (time-sensitive)
  - Clears cache again before processing 1d
  - Reuses 1d data for 2d and 1w scans to save time and API calls
