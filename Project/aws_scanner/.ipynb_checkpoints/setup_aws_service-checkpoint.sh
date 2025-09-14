#!/bin/bash
# Setup script for Market Scanner Service on AWS
# Updated to support Version 2.7 with enhanced HBS breakout and optimized data fetching

set -e

echo "=== Setting up Market Scanner Service Version 2.7 ==="

# Get the absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"
echo "✓ Created logs directory"

# Check if Python 3.8+ is installed
echo "Checking Python installation..."
python3 --version

if [ $? -ne 0 ]; then
    echo "Python 3 is not installed. Installing..."
    sudo yum update -y
    sudo yum install -y python3 python3-pip python3-devel gcc
    echo "✓ Python 3 installed"
else
    echo "✓ Python 3 already installed"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating Python virtual environment..."
    cd "$PROJECT_ROOT"
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$PROJECT_ROOT/venv/bin/activate"

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from requirements.txt if available, otherwise install manually
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    echo "Installing required dependencies manually..."
    pip install python-telegram-bot==20.7
    pip install pandas>=2.0.0
    pip install aiohttp>=3.8.0
    pip install tqdm>=4.64.0
    pip install numpy>=1.24.0
    pip install nest-asyncio>=1.5.0
fi

# Verify installations
echo "Verifying installations..."
python -c "import pandas, aiohttp, tqdm, numpy; print('✓ All dependencies installed successfully')"

# Set up the systemd service with CORRECT virtual environment path
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/market-scanner.service > /dev/null << EOF
[Unit]
Description=Cryptocurrency Market Scanner Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PROJECT_ROOT/venv/bin/python $SCRIPT_DIR/aws_scanner_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=market-scanner

# Environment variables
Environment=PYTHONPATH=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable market-scanner.service
echo "✓ Systemd service configured with virtual environment"

# Create log rotation config
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/market-scanner > /dev/null << EOF
$SCRIPT_DIR/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    create 0640 ec2-user ec2-user
    postrotate
        # Send HUP signal to service to reopen log files
        systemctl reload-or-restart market-scanner.service > /dev/null 2>&1 || true
    endscript
}
EOF
echo "✓ Log rotation configured (14 days retention)"

# Set proper permissions
echo "Setting permissions..."
chmod +x "$SCRIPT_DIR/aws_scanner_service.py"
chmod 755 "$SCRIPT_DIR/logs"
chown -R ec2-user:ec2-user "$SCRIPT_DIR/logs"
echo "✓ Permissions set"

# Create a simple status script
cat > "$SCRIPT_DIR/status.sh" << 'EOF'
#!/bin/bash
echo "=== Market Scanner Service Status ==="
sudo systemctl status market-scanner.service --no-pager -l

echo -e "\n=== Recent Logs ==="
tail -20 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log

echo -e "\n=== Service Commands ==="
echo "Start:   sudo systemctl start market-scanner.service"
echo "Stop:    sudo systemctl stop market-scanner.service"
echo "Restart: sudo systemctl restart market-scanner.service"
echo "Logs:    tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
EOF

chmod +x "$SCRIPT_DIR/status.sh"
echo "✓ Status script created at $SCRIPT_DIR/status.sh"

echo ""
echo "=== Setup Complete! Version 2.7 Features Active ==="
echo ""
echo "Version 2.7 New Features:"
echo "• Enhanced HBS Breakout with SMA50 and Engulfing Reversal component detection"
echo "• Optimized API fetch limits ensuring sufficient data for SMA50 calculations"
echo "• New strategies: Channel, Wedge Breakout, SMA50 Breakout"
echo "• Clean date formatting in Telegram messages (YYYY-MM-DD HH:00)"
echo "• Weekly data consistency across all exchanges"
echo "• Multi-component signal analysis for HBS breakout"
echo ""
echo "To manage the service:"
echo "• Start:    sudo systemctl start market-scanner.service"
echo "• Stop:     sudo systemctl stop market-scanner.service"
echo "• Restart:  sudo systemctl restart market-scanner.service"
echo "• Status:   $SCRIPT_DIR/status.sh"
echo ""
echo "To view logs:"
echo "• Live logs: tail -f $SCRIPT_DIR/logs/scanner_service.log"
echo "• All logs:  ls -la $SCRIPT_DIR/logs/"
echo ""
echo "Timeframe Schedule:"
echo "• 4h scans: Every 4 hours (00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC)"
echo "• 1d scans: Daily at 00:01 UTC"
echo "• 2d scans: Every 2 days at 00:01 UTC (from Mar 20, 2025)"
echo "• 3d scans: Every 3 days at 00:01 UTC (from Mar 20, 2025)"
echo "• 4d scans: Every 4 days at 00:01 UTC (from Mar 22, 2025)"
echo "• 1w scans: Weekly on Mondays at 00:01 UTC"
echo ""
echo "Enhanced Strategies Active:"
echo "• HBS Breakout: Reports SMA50 and Engulfing Reversal components"
echo "• Channel: Ongoing diagonal channel monitoring"
echo "• Wedge Breakout: Diagonal consolidation wedge breakout detection"
echo "• SMA50 Breakout: Clean moving average breakout detection"
echo "• All strategies: Optimized data fetching for reliable analysis"