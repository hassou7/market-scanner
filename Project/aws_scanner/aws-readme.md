# Market Scanner AWS Service

This folder contains everything you need to run your cryptocurrency market pattern scanner as a service on an AWS EC2 instance. This guide is written for beginners, with complete multi-timeframe support including the new 3d and 4d timeframes, plus confluence strategy notifications.

## Directory Structure

```
Project/
├── aws_scanner/             # AWS service components
│   ├── aws_scanner_service.py   # Main service script (UPDATED)
│   ├── market-scanner.service   # Systemd service configuration (UPDATED)
│   ├── setup_aws_service.sh     # Setup script (UPDATED)
│   ├── status.sh                # Quick status checker (NEW)
│   ├── README.md                # This file (you're reading it!)
│   └── logs/                    # Log files (created automatically)
│       ├── scanner_service.log  # Main application logs
│       ├── systemd_output.log   # Standard output logs
│       └── systemd_error.log    # Error logs
├── scanner/                 # Your existing scanner code
├── exchanges/               # Your existing exchange clients
├── breakout_vsa/            # Your existing VSA pattern detection code
├── custom_strategies/       # Your custom strategies (including confluence.py)
└── run_parallel_scanner.py # Your parallel scanner runner
```

## New Features (Version 2.0)

- **Extended Timeframes**: Now supports 3d and 4d timeframes alongside existing ones
- **Confluence Strategy**: Advanced multi-factor signal detection for spot exchanges
- **Enhanced User Management**: Multiple Telegram recipients for different strategies
- **Improved Scheduling**: Smart timing logic for all timeframes
- **Better Error Handling**: Enhanced resilience and automatic recovery
- **Status Monitoring**: Easy-to-use status checking script

## Features

- **Multi-Timeframe Scanning**: Automatically scans 4h, 1d, 2d, 3d, 4d, and 1w timeframes
- **Parallel Processing**: Scans multiple exchanges simultaneously for maximum efficiency
- **Smart Scheduling**: Optimized timing based on candle close schedules
- **Confluence Detection**: Advanced pattern recognition combining volume, spread, and momentum
- **Multi-User Notifications**: Different Telegram recipients for different strategies
- **Cache Optimization**: Reuses data efficiently across timeframes
- **Auto-Recovery**: Restarts automatically if crashes occur
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Installation on AWS

### 1. Connect to your EC2 instance

```bash
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@13.53.165.65
```

### 2. Remove Old Files (If Any)

Move to your home directory and remove the market-scanner folder and everything inside it:

```bash
cd ~
rm -rf market-scanner
```

### 3. Clone your repository or upload your code

```bash
# Option 1: If using git
git clone https://github.com/hassou7/market-scanner.git

# Option 2: Create directories for manual file uploads
mkdir -p market-scanner/Project/aws_scanner/logs
```

### 4. Install Required Tools

Update your server and install Python and Git:

```bash
sudo yum update -y
sudo yum install python3 python3-pip git gcc python3-devel -y
```

### 5. Set Up the Service

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

This sets up the service with all new features including 3d/4d timeframes and confluence strategy.

### 6. Configure Telegram Users (IMPORTANT)

Make sure your `utils/config.py` file has the correct user configuration:

```python
TELEGRAM_USERS = {
    "default": {"name": "Houssem", "chat_id": "375812423"},
    "user1": {"name": "Samed", "chat_id": "2008960887"},
    "user2": {"name": "Moez", "chat_id": "6511370226"}, 
}
```

**Note**: User2 (Moez) will receive confluence strategy notifications for 2d, 3d, 4d, and 1w timeframes.

### 7. Launch the Service

Start the scanner service:

```bash
sudo systemctl start market-scanner.service
```

Check if it's running:

```bash
sudo systemctl status market-scanner.service
```

Look for `Active: active (running)` in the output. If you see that, it's working!

### 8. Quick Status Check

Use the new status script for a quick overview:

```bash
./status.sh
```

This shows service status, recent logs, and helpful commands.

## Timeframe Schedule

### Automatic Scan Times (All times in UTC)

- **4-Hour Scans**: Every 4 hours at 00:01, 04:01, 08:01, 12:01, 16:01, 20:01
- **Daily Scans**: Every day at 00:01
- **2-Day Scans**: Every 2 days at 00:01 (starting from March 20, 2025)
- **3-Day Scans**: Every 3 days at 00:01 (starting from March 20, 2025) **NEW**
- **4-Day Scans**: Every 4 days at 00:01 (starting from March 22, 2025) **NEW**
- **Weekly Scans**: Every Monday at 00:01

### Execution Priority

When multiple timeframes trigger simultaneously (e.g., Monday 00:01 UTC), they execute in this order:
1. **4h** (most time-sensitive)
2. **1d** 
3. **2d**
4. **3d** **NEW**
5. **4d** **NEW**
6. **1w** (least time-sensitive)

Each timeframe waits 30 seconds after the previous one completes.

## Strategy Configuration

### Futures Exchanges
- **4h**: volume_surge
- **1d**: reversal_bar, volume_surge
- **2d**: reversal_bar, pin_down
- **3d**: reversal_bar, pin_down **NEW**
- **4d**: reversal_bar, pin_down **NEW**
- **1w**: reversal_bar, pin_down

### Spot Exchanges
- **4h**: breakout_bar
- **1d**: breakout_bar, loaded_bar, volume_surge
- **2d**: start_bar, breakout_bar, volume_surge, loaded_bar, **confluence** **NEW**
- **3d**: start_bar, breakout_bar, volume_surge, loaded_bar, **confluence** **NEW**
- **4d**: start_bar, breakout_bar, volume_surge, loaded_bar, **confluence** **NEW**
- **1w**: start_bar, breakout_bar, volume_surge, loaded_bar, **confluence** **NEW**

### Telegram Notifications

- **Default User (Houssem)**: Receives all strategy notifications
- **User2 (Moez)**: Receives confluence strategy notifications for 2d, 3d, 4d, and 1w timeframes **NEW**

## Monitoring and Management

### View Logs

```bash
# Live main application log
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Live systemd output
tail -f ~/market-scanner/Project/aws_scanner/logs/systemd_output.log

# Live systemd errors
tail -f ~/market-scanner/Project/aws_scanner/logs/systemd_error.log

# All logs at once (recent entries)
./status.sh
```

### Service Management

```bash
# Start the service
sudo systemctl start market-scanner.service

# Stop the service
sudo systemctl stop market-scanner.service

# Restart the service
sudo systemctl restart market-scanner.service

# Check service status
sudo systemctl status market-scanner.service

# Enable auto-start on boot (already done by setup)
sudo systemctl enable market-scanner.service

# Disable auto-start on boot
sudo systemctl disable market-scanner.service
```

### Debug Mode

If you need detailed debugging information:

1. Stop the service:
```bash
sudo systemctl stop market-scanner.service
```

2. Run manually with debug flag:
```bash
cd ~/market-scanner/Project
source venv/bin/activate
python aws_scanner/aws_scanner_service.py --debug
```

3. Press Ctrl+C to stop, then restart the service:
```bash
sudo systemctl start market-scanner.service
```

## Updating the Service

### Remote Updates via SCP

Upload updated files from your local machine:

```bash
# Upload updated service script
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" path\to\aws_scanner_service.py ec2-user@13.53.165.65:~/market-scanner/Project/aws_scanner/

# Upload multiple files
scp -i "C:\Users\hbs\.ssh\volume_surge.pem" path\to\aws_scanner\*.py ec2-user@13.53.165.65:~/market-scanner/Project/aws_scanner/

# Restart the service remotely
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@13.53.165.65 "sudo systemctl restart market-scanner.service"
```

### Local Updates

If you're logged into the server:

```bash
# Edit the service file
nano ~/market-scanner/Project/aws_scanner/aws_scanner_service.py

# Restart to apply changes
sudo systemctl restart market-scanner.service
```

## Understanding the Confluence Strategy

The confluence strategy combines three factors for high-probability signals:

1. **High Volume**: Volume significantly above average
2. **Spread Breakout**: Range expansion indicating volatility
3. **Momentum Breakout**: Strong directional movement

**Confluence signals are only sent to:**
- Default user (all strategies)
- User2 (confluence only, on 2d/3d/4d/1w timeframes)

## Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   # Check for errors
   sudo journalctl -u market-scanner.service -f
   
   # Check file permissions
   ls -la ~/market-scanner/Project/aws_scanner/
   ```

2. **No Telegram notifications**:
   - Verify bot tokens in `utils/config.py`
   - Check that bots are started by users
   - Confirm user chat IDs are correct

3. **Missing confluence signals**:
   - Ensure user2 is configured correctly
   - Check that confluence.py exists in custom_strategies/
   - Verify timeframes (confluence only runs on 2d/3d/4d/1w for spots)

4. **Memory issues**:
   ```bash
   # Check memory usage
   free -h
   
   # Check service memory limit
   sudo systemctl show market-scanner.service | grep Memory
   ```

### Log Analysis

Key log patterns to look for:

```bash
# Successful scan
grep "Parallel scan complete" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Confluence detections
grep "confluence detected" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Schedule information
grep "Computing scan schedule" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Error patterns
grep "Error" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

### Performance Monitoring

Monitor the service performance:

```bash
# Check CPU and memory usage
top -p $(pgrep -f aws_scanner_service.py)

# Check network connections
netstat -tulpn | grep python

# Check disk space for logs
df -h ~/market-scanner/Project/aws_scanner/logs/
```

## Log Rotation

Logs are automatically rotated daily with 14-day retention. Configuration is in `/etc/logrotate.d/market-scanner`.

## Security Features

The service runs with enhanced security:
- Non-root user execution
- Private temporary directories
- Read-only system protection
- Limited file access permissions
- Memory limits (2GB max)
- File descriptor limits (4096 max)

## Backup Recommendations

Consider backing up:
- Configuration files (`utils/config.py`)
- Log files (important detections)
- Service scripts (for easy restoration)

```bash
# Create backup
tar -czf market-scanner-backup-$(date +%Y%m%d).tar.gz ~/market-scanner/Project/aws_scanner/
```

---

## Quick Reference

### Essential Commands
```bash
# Service status and recent logs
./status.sh

# Restart service
sudo systemctl restart market-scanner.service

# Live logs
tail -f logs/scanner_service.log

# Debug mode
python aws_scanner_service.py --debug
```

### Important Files
- Service script: `aws_scanner_service.py`
- Configuration: `../utils/config.py`
- Service definition: `market-scanner.service`
- Logs: `logs/scanner_service.log`

### Key Features
- ✅ 6 timeframes (4h, 1d, 2d, 3d, 4d, 1w)
- ✅ Confluence strategy with multi-user notifications
- ✅ Parallel exchange scanning
- ✅ Smart cache management
- ✅ Automatic error recovery
- ✅ Comprehensive logging

For support or questions about the new features, check the logs or run in debug mode for detailed information.