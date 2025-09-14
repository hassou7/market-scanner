v 11.09.2025

# Complete AWS Instance Deployment Guide

This guide provides safe deployment of the market scanner from your GitHub repository, ensuring no conflicting services run simultaneously.

## Prerequisites

- SSH key file: `C:\Users\hbs\.ssh\hbs_event_indicator.pem`
- AWS Instance IP: `13.60.20.56`
- GitHub Repository: `https://github.com/hassou7/market-scanner`
- Updated repository with latest changes pushed to main branch

## Step 1: Connect to Your AWS Instance

```bash
ssh -i "C:\Users\hbs\.ssh\hbs_event_indicator.pem" ec2-user@13.60.20.56
```

## Step 2: Assess Current State and Stop All Services

```bash
# Check what services are currently running
sudo systemctl list-units --type=service --state=running | grep -E "(scanner|market)"

# Check for any Python processes related to scanning
ps aux | grep -E "(scanner|market)" | grep -v grep

# Stop any market scanner services
sudo systemctl stop market-scanner.service 2>/dev/null || echo "No market-scanner service found"
sudo systemctl stop scanner.service 2>/dev/null || echo "No scanner service found"

# Kill any remaining Python scanner processes
pkill -f "scanner" 2>/dev/null || echo "No scanner processes found"
pkill -f "market" 2>/dev/null || echo "No market processes found"

# Verify nothing is running
ps aux | grep -E "(scanner|market)" | grep -v grep
echo "✓ All scanner processes stopped if no output above"
```

## Step 3: Clean Up Old Services and Files

```bash
# Disable auto-start for old services
sudo systemctl disable market-scanner.service 2>/dev/null || echo "No market-scanner service to disable"
sudo systemctl disable scanner.service 2>/dev/null || echo "No scanner service to disable"

# Remove old service files
sudo rm -f /etc/systemd/system/market-scanner.service
sudo rm -f /etc/systemd/system/scanner.service

# Remove log rotation config if exists
sudo rm -f /etc/logrotate.d/market-scanner

# Reload systemd daemon
sudo systemctl daemon-reload

# Verify services are gone
sudo systemctl list-unit-files | grep -E "(scanner|market)" || echo "✓ No scanner services remain"
```

## Step 4: Update Code from GitHub

```bash
# Navigate to your project
cd ~/market-scanner

# Check current git status
git status

# Stash local changes if any (optional)
# git stash

# Pull latest changes from your repository
git pull origin main

# Apply stashed changes if you stashed them
# git stash pop

# Verify Project directory exists with latest code
ls -la Project/
```

## Step 5: Set Up Clean Virtual Environment

```bash
# Navigate to Project directory
cd ~/market-scanner/Project

# Remove any existing virtual environment
rm -rf venv/

# Create fresh virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify you're in the virtual environment
echo "Python path: $(which python)"
echo "Pip path: $(which pip)"

# Upgrade pip to latest version
pip install --upgrade pip
```

Expected output: Python and pip paths should show the venv directory

## Step 6: Install Dependencies in Virtual Environment

```bash
# Ensure you're in Project directory with venv activated
pwd  # Should show ~/market-scanner/Project
which python  # Should show ~/market-scanner/Project/venv/bin/python

# Check requirements.txt exists
ls -la requirements.txt

# Install all dependencies
pip install -r requirements.txt

# Verify critical dependencies are installed
python -c "
import pandas
import aiohttp
import telegram
import tqdm
import numpy
import asyncio
print('✓ All critical dependencies installed successfully')
"
```

Expected output: All imports should succeed without errors

## Step 7: Test Scanner Components

```bash
# Test that the scanner can import properly
cd ~/market-scanner/Project
source venv/bin/activate

# Test basic scanner imports
python -c "
from scanner.main import UnifiedScanner
from utils.config import TELEGRAM_TOKENS, TELEGRAM_USERS
from custom_strategies import detect_confluence, detect_sma50_breakout
print('✓ Scanner components import successful')
"

# Test exchange clients import
python -c "
from exchanges import BinanceSpotClient, BybitSpotClient
print('✓ Exchange clients import successful')
"
```

Expected output: All imports should complete without errors

## Step 8: Set Up and Configure New Service

```bash
# Navigate to aws_scanner directory
cd ~/market-scanner/Project/aws_scanner/

# Check that setup script exists
ls -la setup_aws_service.sh

# Make setup script executable
chmod +x setup_aws_service.sh

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the setup script to create new service
./setup_aws_service.sh

# Verify service file was created correctly
sudo cat /etc/systemd/system/market-scanner.service
```

Expected output: Service file should be created with correct paths to your virtual environment

## Step 9: Start and Enable New Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Start the service
sudo systemctl start market-scanner.service

# Check initial status (should show active/running)
sudo systemctl status market-scanner.service

# If it started successfully, enable auto-start on boot
sudo systemctl enable market-scanner.service

# Double-check it's running and enabled
echo "Service active: $(sudo systemctl is-active market-scanner.service)"
echo "Service enabled: $(sudo systemctl is-enabled market-scanner.service)"
```

Expected output: Service should be "active" and "enabled"

## Step 10: Monitor Initial Deployment

```bash
# Watch service logs in real-time (Ctrl+C to exit)
sudo journalctl -u market-scanner.service -f

# In another terminal session, watch application logs
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Check for any errors in the first few minutes
sleep 60
echo "Recent errors (if any):"
grep -i error ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5

# Check for successful initialization
echo "Recent activity:"
tail -10 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

Expected output: Should see schedule computation and scan initialization messages

## Step 11: Verify Deployment Success

```bash
# Check comprehensive service status
cd ~/market-scanner/Project/aws_scanner/
./status.sh

# Verify no duplicate processes are running
echo "Scanner processes running:"
ps aux | grep -E "(scanner|market)" | grep -v grep

# Check that only one scanner service is enabled
echo "Scanner services:"
sudo systemctl list-unit-files | grep -E "(scanner|market)"

# View recent successful operations
echo "Recent log entries:"
tail -20 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Check for pattern detection success
echo "Recent signals found:"
grep -i "signals found\|detected for" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5
```

Expected output: Single service running, no duplicates, recent log activity showing normal operation

## Quick Reference Commands

### Service Management
```bash
# Start service
sudo systemctl start market-scanner.service

# Stop service
sudo systemctl stop market-scanner.service

# Restart service (after code updates)
sudo systemctl restart market-scanner.service

# Check service status
sudo systemctl status market-scanner.service

# View service logs
sudo journalctl -u market-scanner.service -f

# Check if service is running
sudo systemctl is-active market-scanner.service
```

### Log Monitoring
```bash
# View live application logs
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Quick status check
cd ~/market-scanner/Project/aws_scanner/ && ./status.sh

# Check for recent errors
grep -i error ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10

# Check for recent successful scans
grep -i "signals found\|scan complete" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10

# Check last 100 lines of logs
tail -100 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

### Code Updates from GitHub
```bash
# Stop service
sudo systemctl stop market-scanner.service

# Update code from GitHub
cd ~/market-scanner
git pull origin main

# Restart service with new code
sudo systemctl start market-scanner.service

# Verify restart was successful
sudo systemctl status market-scanner.service
```

### Virtual Environment Management
```bash
# Activate virtual environment
cd ~/market-scanner/Project
source venv/bin/activate

# Check installed packages
pip list

# Install new dependencies (if requirements.txt updated)
pip install -r requirements.txt

# Test imports after updates
python -c "from scanner.main import UnifiedScanner; print('✓ Scanner ready')"
```

## Expected Scanner Behavior

Once running successfully, you should see:

### Schedule Computation (Every 24 hours)
- **Schedule calculation** messages showing when scans will run
- **Next scan times** for each timeframe
- **UTC timezone** calculations for proper timing

### Scan Execution (At scheduled times)
- **4h scans**: Every 4 hours at 01 minutes past (00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC)
- **1d scans**: Daily at 00:01 UTC
- **2d scans**: Every 2 days at 00:01 UTC (starting from March 20, 2025)
- **3d scans**: Every 3 days at 00:01 UTC (starting from March 20, 2025)
- **4d scans**: Every 4 days at 00:01 UTC (starting from March 22, 2025)
- **1w scans**: Weekly on Mondays at 00:01 UTC

### Strategy Detection Messages
- **Exchange scanning** messages showing markets being processed
- **Pattern detection** results for each strategy
- **Telegram notifications** when signals are found
- **Cache management** between timeframes for efficiency

### Version 2.7 Features Active
- **Enhanced HBS breakout** with SMA50 and engulfing reversal component detection
- **Optimized data fetching** ensuring sufficient data for all strategies
- **Clean date formatting** in Telegram messages (YYYY-MM-DD HH:00)
- **Weekly data consistency** across all exchanges

## Troubleshooting

### If the service fails to start:
```bash
# Check detailed error logs
sudo journalctl -u market-scanner.service --no-pager -l

# Check virtual environment is working
cd ~/market-scanner/Project
source venv/bin/activate
python -c "import sys; print('Python path:', sys.executable)"
python -c "from scanner.main import UnifiedScanner; print('✓ Scanner imports OK')"
```

### If getting "module not found" errors:
```bash
# Reinstall dependencies in virtual environment
cd ~/market-scanner/Project
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Restart service
sudo systemctl restart market-scanner.service

# Check status
sudo systemctl status market-scanner.service
```

### If multiple processes are running:
```bash
# Stop all scanner processes
sudo systemctl stop market-scanner.service
pkill -f "scanner"
pkill -f "market"

# Wait a moment, then restart single service
sleep 5
sudo systemctl start market-scanner.service

# Verify only one process is running
ps aux | grep -E "(scanner|market)" | grep -v grep
```

### If the service keeps crashing:
```bash
# Run manually to see error messages
cd ~/market-scanner/Project
source venv/bin/activate
python aws_scanner/aws_scanner_service.py --debug

# Check for Python path issues
python -c "import sys; print('\\n'.join(sys.path))"

# Check for missing dependencies
pip check
```

### If Git pull fails:
```bash
# Check what local changes exist
cd ~/market-scanner
git status
git diff

# Stash local changes and pull
git stash
git pull origin main

# If you need local changes back
git stash pop
```

## Configuration Files

Key configuration files in your setup:
- `~/market-scanner/Project/utils/config.py` - Telegram and user configuration
- `~/market-scanner/Project/aws_scanner/aws_scanner_service.py` - Main service script
- `/etc/systemd/system/market-scanner.service` - Systemd service configuration
- `~/market-scanner/Project/requirements.txt` - Python dependencies

## Security and Maintenance

### Regular Maintenance
```bash
# Update system packages monthly
sudo yum update -y

# Check service health weekly
cd ~/market-scanner/Project/aws_scanner/ && ./status.sh

# Monitor log file sizes
du -h ~/market-scanner/Project/aws_scanner/logs/

# Check available disk space
df -h
```

### Log Rotation
The system automatically manages log rotation to prevent disk space issues. Logs are rotated when they exceed certain size limits.

### GitHub Updates
Update your code by pulling from GitHub and restarting the service. The virtual environment ensures dependencies remain isolated and stable.

## Support

If you encounter issues:
1. **Check logs first** using the monitoring commands above
2. **Verify virtual environment** is activated and dependencies are installed
3. **Ensure only one service** is running to avoid conflicts
4. **Check GitHub repository** has the latest code pushed
5. **Verify Telegram configuration** in `utils/config.py` is correct
6. **Test manual imports** in the virtual environment to isolate issues

---

**Note**: This deployment guide ensures safe, conflict-free deployment with virtual environment isolation, supporting all Version 2.7 features including enhanced HBS breakout strategy, optimized data fetching, and multi-component signal analysis.