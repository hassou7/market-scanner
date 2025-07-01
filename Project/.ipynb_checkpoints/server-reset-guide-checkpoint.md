# Complete Server Reset and Fresh GitHub Project Deployment

Here's a comprehensive step-by-step guide to reset your server and set up your project from scratch using your GitHub repository:

## Step 1: Stop All Running Services

```bash
# Find all running processes related to your project
ps aux | grep aws_scanner_service.py

# Kill the process (replace PID with actual process ID)
kill -SIGTERM 837404

# Verify the process is stopped
ps aux | grep aws_scanner_service.py
```

## Step 2: Backup Any Important Data (Optional)

```bash
# Create a backup folder
mkdir -p ~/backups

# Backup any important configuration files or data
cp -r /home/ec2-user/market-scanner/Project/aws_scanner/logs ~/backups/logs
```

## Step 3: Remove Existing Project Directory

```bash
# Remove the entire project directory
rm -rf /home/ec2-user/market-scanner
```

## Step 4: Clean Up Python Environment (Optional)

```bash
# Remove the virtual environment if it exists
rm -rf /home/ec2-user/market-scanner/Project/venv

# Or if you have a global environment you want to clean
pip list | grep -v "pip" | grep -v "setuptools" | grep -v "wheel" | cut -d " " -f 1 | xargs pip uninstall -y
```

## Step 5: Clone Fresh Copy from GitHub

```bash
# Navigate to the directory where you want to clone
cd /home/ec2-user

# Clone your repository
git clone https://github.com/hassou7/market-scanner.git
cd market-scanner
```

## Step 6: Set Up Python Virtual Environment

```bash
# Navigate to the project directory
cd /home/ec2-user/market-scanner

# Create a Project directory if it doesn't exist
mkdir -p Project

# Create and activate a virtual environment
cd Project
python3 -m venv venv
source venv/bin/activate
```

## Step 7: Install Dependencies

```bash
# Make sure pip is up-to-date
pip install --upgrade pip

# Install requirements if you have a requirements.txt file
cd /home/ec2-user/market-scanner
pip install -r requirements.txt

# Or install dependencies manually
pip install pandas numpy asyncio aiohttp python-telegram-bot nest_asyncio tqdm jupyter
```

## Step 8: Create AWS Scanner Directory

```bash
# Create the aws_scanner directory structure
mkdir -p /home/ec2-user/market-scanner/Project/aws_scanner/logs
```

## Step 9: Copy Your AWS Scanner Service Script

```bash
# Copy the AWS scanner service script to the appropriate directory
cp /home/ec2-user/market-scanner/aws_scanner_service.py /home/ec2-user/market-scanner/Project/aws_scanner/
```

## Step 10: Set Up Permissions

```bash
# Make sure the script is executable
chmod +x /home/ec2-user/market-scanner/Project/aws_scanner/aws_scanner_service.py

# Set proper permissions for the logs directory
chmod 755 /home/ec2-user/market-scanner/Project/aws_scanner/logs
```

## Step 11: Start the Service

```bash
# Navigate to the aws_scanner directory
cd /home/ec2-user/market-scanner/Project/aws_scanner

# Start the service in the background
python aws_scanner_service.py --debug > scanner_output.log 2>&1 &

# Note the process ID
echo $! > scanner.pid
```

## Step 12: Verify the Service is Running

```bash
# Check process status
ps aux | grep aws_scanner_service.py

# Check for logs
cat scanner_output.log
```

## Step 13: Set Up Log Rotation (Optional)

```bash
# Create a logrotate configuration
sudo nano /etc/logrotate.d/aws_scanner

# Add the following content
# /home/ec2-user/market-scanner/Project/aws_scanner/logs/scanner_service.log {
#    daily
#    rotate 7
#    compress
#    delaycompress
#    missingok
#    notifempty
#    create 0640 ec2-user ec2-user
#    postrotate
#        kill -USR1 $(cat /home/ec2-user/market-scanner/Project/aws_scanner/scanner.pid)
#    endscript
# }
```

## Step 14: Set Up Auto-Start on Reboot (Optional)

```bash
# Create a systemd service file
sudo nano /etc/systemd/system/aws-scanner.service

# Add the following content
# [Unit]
# Description=AWS Scanner Service
# After=network.target
# 
# [Service]
# User=ec2-user
# WorkingDirectory=/home/ec2-user/market-scanner/Project/aws_scanner
# ExecStart=/home/ec2-user/market-scanner/Project/venv/bin/python aws_scanner_service.py --debug
# Restart=always
# 
# [Install]
# WantedBy=multi-user.target

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable aws-scanner
sudo systemctl start aws-scanner
```

## Step 15: Monitor the Service

```bash
# Check service status
sudo systemctl status aws-scanner

# Monitor logs
tail -f /home/ec2-user/market-scanner/Project/aws_scanner/logs/scanner_service.log
```

These steps will completely reset your server and set up your project from scratch using your GitHub repository. Adjust paths and commands as needed based on your specific project structure and requirements.