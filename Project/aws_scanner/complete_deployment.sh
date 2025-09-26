#!/bin/bash

# Complete AWS Market Scanner Deployment Script with All Fixes
# Repository: https://github.com/hassou7/market-scanner
# This script includes all fixes for common deployment issues

set -e  # Exit on any error

echo "Complete Market Scanner Deployment from Public GitHub"
echo "Repository: https://github.com/hassou7/market-scanner"
echo "=========================================================="

# STEP 1: Stop ALL Services and Processes
echo ""
echo "STEP 1: Stopping all scanner services and processes..."
echo "--------------------------------------------------------"

# Stop all scanner-related services
sudo systemctl stop market-scanner.service 2>/dev/null || echo "• No market-scanner service running"
sudo systemctl stop scanner.service 2>/dev/null || echo "• No scanner service running"

# Kill ALL scanner processes
sudo pkill -f "scanner" 2>/dev/null || echo "• No scanner processes"
sudo pkill -f "market" 2>/dev/null || echo "• No market processes"
sudo pkill -f "aws_scanner" 2>/dev/null || echo "• No aws_scanner processes"
sudo pkill -f "market-scanner" 2>/dev/null || echo "• No market-scanner processes"
sudo pkill -f "/home/ec2-user/market-scanner" 2>/dev/null || echo "• No project-specific processes"

# Wait for processes to terminate
sleep 5

# Force kill any remaining processes
REMAINING_PROCS=$(ps aux | grep -E "(scanner|market)" | grep -v grep || true)
if [ -z "$REMAINING_PROCS" ]; then
    echo "All scanner processes stopped successfully"
else
    echo "Force killing remaining processes..."
    sudo pkill -9 -f "scanner" 2>/dev/null || true
    sudo pkill -9 -f "market" 2>/dev/null || true
    sleep 2
    echo "Force termination completed"
fi

# STEP 2: Remove ALL Service Files and Configuration
echo ""
echo "STEP 2: Cleaning all service files and configurations..."
echo "---------------------------------------------------------"

# Disable services
sudo systemctl disable market-scanner.service 2>/dev/null || echo "• No market-scanner service to disable"
sudo systemctl disable scanner.service 2>/dev/null || echo "• No scanner service to disable"

# Remove ALL service files
sudo rm -f /etc/systemd/system/market-scanner.service
sudo rm -f /etc/systemd/system/scanner.service
sudo rm -f /etc/systemd/system/*scanner*.service

# Remove log rotation configs
sudo rm -f /etc/logrotate.d/market-scanner
sudo rm -f /etc/logrotate.d/*scanner*

# Reload systemd daemon
sudo systemctl daemon-reload

echo "All scanner services and configs removed"

# STEP 3: Complete Project Directory Removal
echo ""
echo "STEP 3: Removing existing project directory..."
echo "------------------------------------------------"

cd ~

if [ -d "market-scanner" ]; then
    echo "• Current project directory size:"
    du -sh market-scanner/ 2>/dev/null || echo "  Cannot determine size"
    
    echo "• Removing market-scanner directory completely..."
    rm -rf market-scanner/
    
    # Verify complete removal
    if [ ! -d "market-scanner" ]; then
        echo "Project directory completely removed"
    else
        echo "Failed to remove project directory - trying with sudo..."
        sudo rm -rf market-scanner/ 2>/dev/null || true
        if [ ! -d "market-scanner" ]; then
            echo "Project directory removed with elevated permissions"
        else
            echo "ERROR: Cannot remove project directory - manual intervention needed"
            exit 1
        fi
    fi
else
    echo "No existing market-scanner directory found"
fi

# Clean any leftover files
rm -rf ~/.market-scanner* 2>/dev/null || true
rm -rf ~/market_scanner* 2>/dev/null || true

# STEP 4: Fresh Clone from Public GitHub Repository
echo ""
echo "STEP 4: Cloning fresh code from public GitHub repository..."
echo "------------------------------------------------------------"

cd ~

echo "• Cloning from: https://github.com/hassou7/market-scanner.git"
git clone https://github.com/hassou7/market-scanner.git

# Verify successful clone
if [ -d "market-scanner" ]; then
    echo "Repository cloned successfully"
    
    cd market-scanner
    
    # Check Project directory
    if [ -d "Project" ]; then
        echo "Project directory found"
        
        # Check key files
        echo "• Checking key files..."
        [ -f "Project/requirements.txt" ] && echo "  requirements.txt found" || echo "  ERROR: requirements.txt missing"
        [ -d "Project/scanner" ] && echo "  scanner directory found" || echo "  ERROR: scanner directory missing"
        [ -d "Project/aws_scanner" ] && echo "  aws_scanner directory found" || echo "  ERROR: aws_scanner directory missing"
        [ -f "Project/aws_scanner/aws_scanner_service.py" ] && echo "  main service script found" || echo "  ERROR: main service script missing"
        
    else
        echo "ERROR: Project directory not found in cloned repository"
        exit 1
    fi
else
    echo "ERROR: Failed to clone repository"
    echo "Checking network connectivity..."
    ping -c 2 github.com || echo "Network issue detected"
    exit 1
fi

# STEP 5: Create Clean Virtual Environment
echo ""
echo "STEP 5: Setting up fresh virtual environment..."
echo "------------------------------------------------"

cd ~/market-scanner/Project

# Remove any existing virtual environment remnants
rm -rf venv/ .venv/ env/ 2>/dev/null || true

# Check Python version
PYTHON_VERSION=$(python3 --version)
echo "• Using Python: $PYTHON_VERSION"

# Create new virtual environment
echo "• Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment activated"
    echo "• Virtual environment path: $VIRTUAL_ENV"
    echo "• Python executable: $(which python)"
    echo "• Pip executable: $(which pip)"
else
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip to latest version
echo "• Upgrading pip..."
python -m pip install --upgrade pip

PIP_VERSION=$(pip --version)
echo "• Pip version: $PIP_VERSION"

# STEP 6: Install All Dependencies
echo ""
echo "STEP 6: Installing project dependencies..."
echo "-------------------------------------------"

cd ~/market-scanner/Project
source venv/bin/activate

# Verify requirements file
if [ -f "requirements.txt" ]; then
    echo "• Found requirements.txt"
    
    # Install dependencies with verbose output
    echo "• Installing dependencies..."
    pip install -r requirements.txt --no-cache-dir
    
    echo "All dependencies installed successfully"
    
    # Verify key packages
    echo "• Verifying critical packages..."
    pip show pandas aiohttp python-telegram-bot tqdm numpy > /dev/null 2>&1 && echo "  Core packages verified" || echo "  WARNING: Some core packages missing"
    
else
    echo "ERROR: requirements.txt not found"
    exit 1
fi

# Show final package list summary
echo "• Total packages installed: $(pip list | wc -l)"

# STEP 7: Test All Components
echo ""
echo "STEP 7: Testing all scanner components..."
echo "------------------------------------------"

cd ~/market-scanner/Project
source venv/bin/activate

# Test Python path and imports
echo "• Python path verification:"
python -c "import sys; print('  Python executable:', sys.executable)"
python -c "import sys; print('  Python version:', sys.version.split()[0])"

# Test core scanner imports
echo "• Testing core scanner components..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from scanner.main import UnifiedScanner
    from utils.config import TELEGRAM_TOKENS, TELEGRAM_USERS
    print('  Core scanner components imported successfully')
except ImportError as e:
    print('  ERROR: Core import failed:', str(e))
    sys.exit(1)
except Exception as e:
    print('  ERROR: Unexpected error:', str(e))
    sys.exit(1)
"

# Test strategy imports
echo "• Testing custom strategies..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from custom_strategies import detect_confluence, detect_sma50_breakout
    print('  Custom strategies imported successfully')
except ImportError as e:
    print('  ERROR: Strategy import failed:', str(e))
    sys.exit(1)
except Exception as e:
    print('  ERROR: Unexpected error:', str(e))
    sys.exit(1)
"

# Test exchange clients
echo "• Testing exchange clients..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from exchanges import BinanceSpotClient, BybitSpotClient
    print('  Exchange clients imported successfully')
except ImportError as e:
    print('  ERROR: Exchange import failed:', str(e))
    sys.exit(1)
except Exception as e:
    print('  ERROR: Unexpected error:', str(e))
    sys.exit(1)
"

echo "All components tested and working correctly"

# STEP 8: Configure Service Infrastructure
echo ""
echo "STEP 8: Setting up service infrastructure..."
echo "----------------------------------------------"

cd ~/market-scanner/Project/aws_scanner/

# Check service setup script
if [ -f "setup_aws_service.sh" ]; then
    echo "• Found service setup script"
    
    # Make executable
    chmod +x setup_aws_service.sh
    
    # Create logs directory
    mkdir -p logs
    echo "• Created logs directory"
    
    # Run setup script
    echo "• Running service setup script..."
    ./setup_aws_service.sh
    
else
    echo "Service setup script not found - creating manual setup..."
    
    # Create logs directory
    mkdir -p logs
    
    # Create service file manually
    echo "• Creating service file manually..."
fi

# STEP 9: Create Fixed Service Configuration
echo ""
echo "STEP 9: Creating fixed service configuration..."
echo "----------------------------------------------"

# Always create our own corrected service file to avoid path issues
echo "• Creating corrected service file with verified paths..."

# Verify paths first
PYTHON_PATH="/home/ec2-user/market-scanner/Project/venv/bin/python"
SCRIPT_PATH="/home/ec2-user/market-scanner/Project/aws_scanner/aws_scanner_service.py"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "ERROR: Python executable not found at $PYTHON_PATH"
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: Service script not found at $SCRIPT_PATH"
    exit 1
fi

echo "• Verified paths exist"

# Create the corrected service file
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
WorkingDirectory=/home/ec2-user/market-scanner/Project/aws_scanner
ExecStart=/home/ec2-user/market-scanner/Project/venv/bin/python aws_scanner_service.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=market-scanner

# Environment variables
Environment=PYTHONPATH=/home/ec2-user/market-scanner/Project
Environment=PATH=/home/ec2-user/market-scanner/Project/venv/bin:/usr/local/bin:/usr/bin:/bin

# Resource limits
MemoryLimit=2G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created successfully"

# Test the service configuration before starting
echo "• Testing service configuration..."
cd /home/ec2-user/market-scanner/Project/aws_scanner

# Test Python works
$PYTHON_PATH --version || {
    echo "ERROR: Python executable fails to run"
    exit 1
}

# Test script imports
$PYTHON_PATH -c "
import sys
sys.path.insert(0, '/home/ec2-user/market-scanner/Project')
try:
    import aws_scanner_service
    print('  Script imports successfully')
except Exception as e:
    print('  ERROR: Script import failed:', str(e))
    sys.exit(1)
" || {
    echo "ERROR: Script has import issues"
    exit 1
}

echo "Service configuration tested successfully"

# STEP 10: Start and Enable Service
echo ""
echo "STEP 10: Starting the market scanner service..."
echo "------------------------------------------------"

# Reload systemd to recognize new/updated service
sudo systemctl daemon-reload

# Start the service
echo "• Starting market-scanner service..."
sudo systemctl start market-scanner.service

# Wait for service to initialize
echo "• Waiting for service initialization..."
sleep 10

# Check service status
SERVICE_STATUS=$(sudo systemctl is-active market-scanner.service)
echo "• Service status: $SERVICE_STATUS"

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "Service started successfully!"
    
    # Enable auto-start on boot
    sudo systemctl enable market-scanner.service
    
    ENABLED_STATUS=$(sudo systemctl is-enabled market-scanner.service)
    echo "• Auto-start enabled: $ENABLED_STATUS"
    
    # Show service details
    echo "• Service details:"
    sudo systemctl status market-scanner.service --no-pager -l | head -15
    
    # Check for running processes
    echo ""
    echo "Running processes:"
    ps aux | grep -E "(scanner|market)" | grep -v grep
    
    # Check logs
    echo ""
    echo "Recent logs:"
    sudo journalctl -u market-scanner.service -n 5 --no-pager -l
    
else
    echo "ERROR: Service failed to start"
    echo "• Detailed status:"
    sudo systemctl status market-scanner.service --no-pager -l
    
    echo "• Recent logs:"
    sudo journalctl -u market-scanner.service --no-pager -l -n 20
    
    echo "• Manual execution test:"
    cd /home/ec2-user/market-scanner/Project/aws_scanner
    timeout 10s $PYTHON_PATH aws_scanner_service.py || echo "Manual execution failed or timed out"
    
    exit 1
fi

# STEP 11: Final Verification and Setup Status Script
echo ""
echo "STEP 11: Final verification and setup..."
echo "---------------------------------------"

# Create enhanced status script if it doesn't exist
cd ~/market-scanner/Project/aws_scanner/

if [ ! -f "status.sh" ]; then
    echo "• Creating status script..."
    cat > status.sh << 'EOF'
#!/bin/bash
echo "=== Market Scanner Service Status ==="
sudo systemctl status market-scanner.service --no-pager -l | head -15
echo ""
echo "=== Running Processes ==="
ps aux | grep -E "(scanner|market)" | grep -v grep || echo "No scanner processes found"
echo ""
echo "=== Recent Logs ==="
if [ -f "/home/ec2-user/market-scanner/Project/aws_scanner/logs/scanner_service.log" ]; then
    tail -5 /home/ec2-user/market-scanner/Project/aws_scanner/logs/scanner_service.log
else
    echo "Application log not found yet"
fi
echo ""
echo "=== Service Commands ==="
echo "Start:   sudo systemctl start market-scanner.service"
echo "Stop:    sudo systemctl stop market-scanner.service"
echo "Restart: sudo systemctl restart market-scanner.service"
echo "Logs:    tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "Status:  ~/market-scanner/Project/aws_scanner/status.sh"
EOF
    chmod +x status.sh
fi

# Run final status check
echo "• Running final status check..."
./status.sh

# Final summary
echo ""
echo "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "======================================"
echo ""
echo "Deployment Summary:"
echo "• Repository: https://github.com/hassou7/market-scanner (public)"
echo "• Service Status: $(sudo systemctl is-active market-scanner.service)"
echo "• Auto-start: $(sudo systemctl is-enabled market-scanner.service)"
echo "• Python Version: $(cd ~/market-scanner/Project && source venv/bin/activate && python --version)"
echo "• Virtual Environment: ~/market-scanner/Project/venv/"
echo "• Service Script: ~/market-scanner/Project/aws_scanner/aws_scanner_service.py"
echo "• Log Directory: ~/market-scanner/Project/aws_scanner/logs/"
echo ""
echo "Management Commands:"
echo "• Service status: sudo systemctl status market-scanner.service"
echo "• Restart service: sudo systemctl restart market-scanner.service"
echo "• Stop service: sudo systemctl stop market-scanner.service"
echo "• View live logs: sudo journalctl -u market-scanner.service -f"
echo "• App logs: tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "• Quick status: cd ~/market-scanner/Project/aws_scanner && ./status.sh"
echo ""
echo "Monitoring Commands:"
echo "• Live systemd logs: sudo journalctl -u market-scanner.service -f"
echo "• Live app logs: tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "• Recent activity: tail -20 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "• Error check: grep -i error ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5"
echo "• Signal check: grep -i 'signals found' ~/market-scanner/Project/aws_scanner/logs/scanner_service.log | tail -5"
echo ""
echo "Your Market Scanner is now running with the latest code from GitHub!"
echo "The service will automatically start on boot and restart if it crashes."
echo ""
echo "Next scans will run according to your configured schedule."
echo "Monitor the logs to see trading signals and system activity."