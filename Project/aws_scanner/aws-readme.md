# Complete AWS Instance Cleanup and Setup Guide

This guide will help you completely clean your AWS instance and set up the market scanner from scratch using your GitHub repository.

## Prerequisites

- SSH key file: `C:\Users\hbs\.ssh\volume_surge.pem`
- AWS Instance IP: `16.171.41.211`
- GitHub Repository: `https://github.com/hassou7/market-scanner`

## Step 1: Connect to Your AWS Instance

```bash
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@16.171.41.211
```

## Step 2: Stop the Running Service

```bash
# Stop the market scanner service
sudo systemctl stop market-scanner.service

# Disable it from auto-starting
sudo systemctl disable market-scanner.service

# Check that it's stopped
sudo systemctl status market-scanner.service
```

Expected output: Service should show as "inactive (dead)"

## Step 3: Clean Up All Files

```bash
# Go to home directory
cd ~

# Remove all market scanner related files
rm -rf market-scanner/
rm -rf Project/

# Remove any other scanner-related directories if they exist
rm -rf crypto-scanner/
rm -rf scanner/

# Remove the systemd service file
sudo rm -f /etc/systemd/system/market-scanner.service

# Remove log rotation config
sudo rm -f /etc/logrotate.d/market-scanner

# Reload systemd to remove the deleted service
sudo systemctl daemon-reload

# Clean up any Python virtual environments
rm -rf venv/
rm -rf .local/lib/python*/site-packages/scanner*
rm -rf .local/lib/python*/site-packages/exchanges*

# Optional: Clean package cache
sudo yum clean all
```

## Step 4: Verify Clean State

```bash
# Check that no scanner processes are running
ps aux | grep scanner

# Check that the service is gone
sudo systemctl list-unit-files | grep scanner

# List current directory contents
ls -la

# Check available disk space
df -h
```

Expected output: No scanner processes, no scanner service files, clean home directory

## Step 5: Update System and Install Dependencies

```bash
# Update the system
sudo yum update -y

# Install required packages
sudo yum install -y git python3 python3-pip python3-devel gcc

# Verify Python installation
python3 --version
pip3 --version
```

Expected output: Python 3.8+ and pip should be installed

## Step 6: Clone Fresh Repository from GitHub

```bash
# Clone the repository
git clone https://github.com/hassou7/market-scanner.git

# Enter the directory
cd market-scanner

# List contents to verify
ls -la

# Check if Project directory exists
ls -la Project/
```

Expected output: Repository cloned successfully with Project directory visible

## Step 7: Set Up Python Environment

```bash
# Create virtual environment in the Project directory
cd Project
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## Step 8: Install Dependencies from requirements.txt

```bash
# Make sure you're in the Project directory with requirements.txt
ls requirements.txt

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Verify installations
python -c "import pandas, aiohttp, tqdm, numpy, telegram; print('✓ All dependencies installed successfully')"
```

Expected output: All packages should install without errors and the verification should pass

## Step 9: Set Up the AWS Scanner Service

```bash
# Go to the aws_scanner directory
cd ~/market-scanner/Project/aws_scanner/

# List files to verify aws_scanner directory exists
ls -la

# Make the setup script executable
chmod +x setup_aws_service.sh

# Run the setup script
./setup_aws_service.sh
```

Expected output: Setup script should complete successfully and configure the systemd service

## Step 10: Configure and Start the Service

```bash
# Check the service configuration
sudo systemctl status market-scanner.service

# Start the service
sudo systemctl start market-scanner.service

# Enable auto-start on boot
sudo systemctl enable market-scanner.service

# Check that it's running
sudo systemctl status market-scanner.service
```

Expected output: Service should show as "active (running)"

## Step 11: Monitor the Service

```bash
# Check the status script
cd ~/market-scanner/Project/aws_scanner/
./status.sh

# Watch live logs (press Ctrl+C to exit)
tail -f logs/scanner_service.log

# In another terminal session, check service logs
sudo journalctl -u market-scanner.service -f
```

Expected output: You should see log messages indicating the scanner is computing schedules and running scans

## Step 12: Verify Everything is Working

```bash
# Check that the service is active
sudo systemctl is-active market-scanner.service

# Check that it's enabled for auto-start
sudo systemctl is-enabled market-scanner.service

# View recent log entries
tail -20 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Check for any errors
grep -i error ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10

# Check for successful scans
grep -i "scan complete" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5
```

Expected output: Service should be active and enabled, logs should show successful scans

## Quick Commands Summary

### Service Management
```bash
# Start service
sudo systemctl start market-scanner.service

# Stop service
sudo systemctl stop market-scanner.service

# Restart service
sudo systemctl restart market-scanner.service

# Check service status
sudo systemctl status market-scanner.service

# View service logs
sudo journalctl -u market-scanner.service -f
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
grep -i "signals found" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10
```

### Code Updates
```bash
# Update code from GitHub
cd ~/market-scanner
git pull origin main

# Restart service to apply changes
sudo systemctl restart market-scanner.service

# Check if restart was successful
sudo systemctl status market-scanner.service
```

## Troubleshooting

### If the service fails to start:
```bash
# Check detailed error logs
sudo journalctl -u market-scanner.service --no-pager -l

# Check Python path and dependencies
cd ~/market-scanner/Project
source venv/bin/activate
python -c "import sys; print(sys.path)"
pip list
```

### If getting "module not found" errors:
```bash
# Reinstall dependencies
cd ~/market-scanner/Project
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
sudo systemctl restart market-scanner.service
```

### If the service keeps crashing:
```bash
# Run manually to see error messages
cd ~/market-scanner/Project
source venv/bin/activate
python aws_scanner/aws_scanner_service.py --debug
```

## Expected Scanner Behavior

Once running successfully, you should see:

1. **Schedule computation** messages every 24 hours
2. **Scan execution** messages at scheduled times:
   - 4h scans: Every 4 hours (00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC)
   - 1d scans: Daily at 00:01 UTC
   - 2d scans: Every 2 days at 00:01 UTC (from March 20, 2025)
   - 3d scans: Every 3 days at 00:01 UTC (from March 20, 2025)
   - 4d scans: Every 4 days at 00:01 UTC (from March 22, 2025)
   - 1w scans: Weekly on Mondays at 00:01 UTC

3. **Signal notifications** via Telegram when patterns are detected
4. **Exchange scanning** messages showing markets being processed
5. **Cache management** messages between timeframes

## Updating the Service Code

If you need to update the scanner service code without doing a full cleanup:

### Method 1: Update via GitHub (Recommended)

```bash
# Connect to your instance
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@16.171.41.211

# Stop the service
sudo systemctl stop market-scanner.service

# Navigate to repository
cd ~/market-scanner

# Pull latest changes
git pull origin main

# Restart the service
sudo systemctl start market-scanner.service

# Check status
sudo systemctl status market-scanner.service

# Monitor logs
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

### Method 2: Replace Service File Manually

```bash
# Connect to your instance
ssh -i "C:\Users\hbs\.ssh\volume_surge.pem" ec2-user@16.171.41.211

# Stop the service
sudo systemctl stop market-scanner.service

# Check that it's stopped
sudo systemctl status market-scanner.service
```

Expected output: Service should show "inactive (dead)"

```bash
# Navigate to the aws_scanner directory
cd ~/market-scanner/Project/aws_scanner/

# Backup current file (optional)
cp aws_scanner_service.py aws_scanner_service.py.backup

# Remove the current file
rm aws_scanner_service.py

# Verify it's removed
ls -la aws_scanner_service.py
```

Expected output: "No such file or directory"

```bash
# Create a new file with nano editor
nano aws_scanner_service.py
```

**Now copy and paste your new code into the editor:**
- Paste your updated code
- Press `Ctrl + X` to exit
- Press `Y` to save
- Press `Enter` to confirm the filename

```bash
# Make the file executable
chmod +x aws_scanner_service.py

# Verify the file was created correctly
ls -la aws_scanner_service.py

# Check the first few lines to make sure it was pasted correctly
head -10 aws_scanner_service.py
```

```bash
# Start the service
sudo systemctl start market-scanner.service

# Check that it started successfully
sudo systemctl status market-scanner.service
```

Expected output: Service should show "active (running)"

```bash
# Check live logs to verify new functionality
tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Look for new scan configurations in the logs
grep -i "Config.*:" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -15

# Check for new timeframes (3d and 4d)
grep -i "3d\|4d" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10

# Check for confluence strategy
grep -i "confluence" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5

# Check for user2 notifications
grep -i "user2" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5
```

### Verification Steps

After updating the service code, verify everything is working:

```bash
# Check service status
sudo systemctl is-active market-scanner.service
sudo systemctl is-enabled market-scanner.service

# View recent startup logs
tail -30 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

# Check for any errors
grep -i error ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -10

# Verify scan configurations loaded
grep -i "Configured.*scan configurations" ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -1
```

### Rollback if Issues

If the new code has issues, you can quickly rollback:

```bash
# Stop the service
sudo systemctl stop market-scanner.service

# Restore backup (if you made one)
cp aws_scanner_service.py.backup aws_scanner_service.py

# Or pull previous version from git
git checkout HEAD~1 aws_scanner/aws_scanner_service.py

# Restart service
sudo systemctl start market-scanner.service
```

## Support

If you encounter issues:
1. Check the logs first using the commands above
2. Verify all dependencies are installed correctly
3. Ensure your GitHub repository has the latest code
4. Check that your Telegram configuration is correct in `utils/config.py`

---

**Note**: This setup includes support for all timeframes (4h, 1d, 2d, 3d, 4d, 1w) and the confluence strategy with multi-user Telegram notifications.