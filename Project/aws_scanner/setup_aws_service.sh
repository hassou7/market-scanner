#!/bin/bash
# Setup script for Optimized Market Scanner Service on AWS
# Updated to support native/composed strategy prioritization and efficient data fetching

set -e

echo "=== Setting up Optimized Market Scanner Service ==="

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
    pip install psycopg2-binary>=2.9.0  # For database integration
    pip install sqlalchemy>=2.0.0       # For database models
fi

# Verify installations
echo "Verifying installations..."
python -c "import pandas, aiohttp, tqdm, numpy; print('✓ All dependencies installed successfully')"

# Set up the systemd service with optimized configuration
echo "Setting up optimized systemd service..."
sudo tee /etc/systemd/system/market-scanner.service > /dev/null << EOF
[Unit]
Description=Optimized Cryptocurrency Market Scanner Service
After=network.target
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PROJECT_ROOT/venv/bin/python $SCRIPT_DIR/aws_scanner_service.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=market-scanner

# Environment variables for optimization
Environment=PYTHONPATH=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
Environment=FAST_MAX_EXCHANGES=4
Environment=SLOW_MAX_EXCHANGES=2
Environment=EXCHANGE_STAGGER_MS=250

# Resource limits
MemoryMax=2G
CPUQuota=80%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$SCRIPT_DIR/logs
PrivateTmp=true
PrivateNetwork=false

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable market-scanner.service
echo "✓ Optimized systemd service configured with virtual environment"

# Create enhanced log rotation config
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/market-scanner > /dev/null << EOF
$SCRIPT_DIR/logs/*.log {
    daily
    rotate 30
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
echo "✓ Log rotation configured (30 days retention)"

# Set proper permissions
echo "Setting permissions..."
chmod +x "$SCRIPT_DIR/aws_scanner_service.py"
chmod 755 "$SCRIPT_DIR/logs"
chown -R ec2-user:ec2-user "$SCRIPT_DIR/logs"
echo "✓ Permissions set"

# Create enhanced status script with optimization info
cat > "$SCRIPT_DIR/status.sh" << 'EOF'
#!/bin/bash
echo "=== Optimized Market Scanner Service Status ==="
sudo systemctl status market-scanner.service --no-pager -l

echo -e "\n=== Recent Performance Logs ==="
tail -30 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | grep -E "(Priority|signals found|Session complete|Starting prioritized)"

echo -e "\n=== Cache and Session Management ==="
tail -10 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | grep -E "(cache|Cache|session|Session)"

echo -e "\n=== Service Commands ==="
echo "Start:   sudo systemctl start market-scanner.service"
echo "Stop:    sudo systemctl stop market-scanner.service"
echo "Restart: sudo systemctl restart market-scanner.service"
echo "Logs:    tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "Status:  ~/market-scanner/Project/aws_scanner/status.sh"
EOF

chmod +x "$SCRIPT_DIR/status.sh"
echo "✓ Enhanced status script created at $SCRIPT_DIR/status.sh"

echo ""
echo "=== Optimized Setup Complete! ==="
echo ""
echo "Key Optimizations Active:"
echo "• Native/Composed Strategy Prioritization:"
echo "  - Priority 1: Fast Native Strategies (confluence, consolidation_breakout, etc.)"
echo "  - Priority 2: Fast Composed Strategies (hbs_breakout, vs_wakeup)"
echo "  - Priority 3: Fast Futures-Only Strategies (reversal_bar, pin_down)"
echo "  - Priority 4: Slow Native Strategies"
echo "  - Priority 5: Slow Composed Strategies"
echo ""
echo "• Efficient Data Fetching:"
echo "  - Single 1d fetch for aggregated timeframes (2d, 3d, 4d)"
echo "  - Smart cache management between sessions"
echo "  - Optimized API usage to prevent rate limiting"
echo ""
echo "• Exchange Classification:"
echo "  - Fast: Binance, Bybit, Gate.io (spot & futures)"
echo "  - Slow: KuCoin, MEXC (with careful rate limiting)"
echo ""
echo "Strategy Coverage:"
echo "• Native Strategies (all timeframes): confluence, consolidation_breakout,"
echo "  channel_breakout, loaded_bar, trend_breakout, pin_up, sma50_breakout"
echo "• Composed Strategies (all timeframes): hbs_breakout, vs_wakeup"
echo "• Futures-Only (all timeframes): reversal_bar, pin_down"
echo ""
echo "Timeframes: 1d, 2d, 3d, 4d, 1w (all strategies on all timeframes)"
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
echo "Daily Execution Schedule (00:01 UTC):"
echo "1. Fast Native Strategies (fastest DB population)"
echo "2. Fast Composed Strategies (derived analysis)"  
echo "3. Fast Futures-Only Strategies (specialized patterns)"
echo "4. Slow Native Strategies (comprehensive coverage)"
echo "5. Slow Composed Strategies (complete analysis)"
echo ""
echo "Environment Variables:"
echo "• FAST_MAX_EXCHANGES=4 (concurrent fast exchanges)"
echo "• SLOW_MAX_EXCHANGES=2 (concurrent slow exchanges)"
echo "• EXCHANGE_STAGGER_MS=250 (stagger timing)"
echo ""
echo "Resource Management:"
echo "• Memory limit: 2GB"
echo "• CPU quota: 80%"
echo "• Log retention: 30 days with daily rotation"
echo "• Automatic cache clearing for aggregated timeframes"