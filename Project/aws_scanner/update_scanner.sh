#!/bin/bash

# Market Scanner Update Script for Future Changes
# Use this script to update your deployed scanner with latest GitHub changes

set -e  # Exit on any error

echo "Market Scanner Update Process"
echo "Repository: https://github.com/hassou7/market-scanner"
echo "============================================="

# Function to check service status
check_service_status() {
    local status=$(sudo systemctl is-active market-scanner.service 2>/dev/null || echo "inactive")
    echo "$status"
}

# Function to show service info
show_service_info() {
    echo "Service Status: $(check_service_status)"
    if [ "$(check_service_status)" = "active" ]; then
        echo "Service Details:"
        sudo systemctl status market-scanner.service --no-pager -l | head -10
        echo ""
        echo "Running Process:"
        ps aux | grep -E "(scanner|market)" | grep -v grep || echo "No processes found"
    fi
}

# STEP 1: Pre-update Status Check
echo ""
echo "STEP 1: Pre-update status check..."
echo "-----------------------------------"

echo "Current service status:"
show_service_info

echo ""
echo "Current code status:"
cd ~/market-scanner
echo "Current directory: $(pwd)"
echo "Current branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
echo "Last commit: $(git log -1 --oneline 2>/dev/null || echo 'unknown')"

# Check for local changes
if git status --porcelain 2>/dev/null | grep -q .; then
    echo "WARNING: Local changes detected:"
    git status --porcelain
    echo ""
    read -p "Do you want to stash local changes? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stashing local changes..."
        git stash
        echo "Local changes stashed"
    else
        echo "Proceeding without stashing (may cause conflicts)"
    fi
fi

# STEP 2: Stop the Service
echo ""
echo "STEP 2: Stopping market scanner service..."
echo "------------------------------------------"

if [ "$(check_service_status)" = "active" ]; then
    echo "Stopping service..."
    sudo systemctl stop market-scanner.service
    
    # Wait for service to stop
    sleep 3
    
    # Verify it stopped
    if [ "$(check_service_status)" = "inactive" ]; then
        echo "Service stopped successfully"
    else
        echo "Service still running, force stopping..."
        sudo pkill -f "market-scanner" 2>/dev/null || true
        sudo pkill -f "aws_scanner" 2>/dev/null || true
        sleep 2
        echo "Force stop completed"
    fi
else
    echo "Service is not running"
fi

# Kill any remaining processes
REMAINING_PROCS=$(ps aux | grep -E "(scanner|market)" | grep -v grep || true)
if [ -n "$REMAINING_PROCS" ]; then
    echo "Killing remaining scanner processes..."
    sudo pkill -f "scanner" 2>/dev/null || true
    sudo pkill -f "market" 2>/dev/null || true
    sleep 2
fi

echo "All processes stopped"

# STEP 3: Update Code from GitHub
echo ""
echo "STEP 3: Updating code from GitHub..."
echo "-------------------------------------"

cd ~/market-scanner

# Fetch latest changes
echo "Fetching latest changes..."
git fetch origin

# Check if there are updates available
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "No updates available - code is already up to date"
    echo "Local commit: $LOCAL_COMMIT"
else
    echo "Updates available!"
    echo "Local commit:  $LOCAL_COMMIT"
    echo "Remote commit: $REMOTE_COMMIT"
    
    # Show what will be updated
    echo ""
    echo "Changes to be pulled:"
    git log --oneline HEAD..origin/main
    
    # Pull the changes
    echo ""
    echo "Pulling latest changes..."
    git pull origin main
    
    echo "Code updated successfully"
    echo "New commit: $(git rev-parse HEAD)"
fi

# STEP 4: Update Dependencies if Needed
echo ""
echo "STEP 4: Checking and updating dependencies..."
echo "----------------------------------------------"

cd ~/market-scanner/Project

# Activate virtual environment
source venv/bin/activate

# Check if requirements.txt changed
if git diff --name-only HEAD~1..HEAD 2>/dev/null | grep -q "requirements.txt"; then
    echo "requirements.txt has changed - updating dependencies..."
    
    # Show what changed in requirements
    echo "Changes in requirements.txt:"
    git diff HEAD~1..HEAD requirements.txt || echo "Cannot show diff"
    
    # Update dependencies
    echo ""
    echo "Installing/updating dependencies..."
    pip install -r requirements.txt --upgrade
    
    echo "Dependencies updated successfully"
    
    # Verify critical packages
    echo "Verifying critical packages..."
    pip show pandas aiohttp python-telegram-bot tqdm numpy > /dev/null 2>&1 && echo "Core packages verified" || echo "WARNING: Some core packages missing"
    
else
    echo "requirements.txt unchanged - skipping dependency update"
    echo "Current package count: $(pip list | wc -l)"
fi

# STEP 5: Test Updated Components
echo ""
echo "STEP 5: Testing updated components..."
echo "-------------------------------------"

cd ~/market-scanner/Project
source venv/bin/activate

echo "Testing core scanner components..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from scanner.main import UnifiedScanner
    from utils.config import TELEGRAM_TOKENS, TELEGRAM_USERS
    print('Core scanner components: OK')
except Exception as e:
    print('ERROR: Core import failed:', str(e))
    sys.exit(1)
"

echo "Testing custom strategies..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from custom_strategies import detect_confluence, detect_sma50_breakout
    print('Custom strategies: OK')
except Exception as e:
    print('ERROR: Strategy import failed:', str(e))
    sys.exit(1)
"

echo "Testing exchange clients..."
python -c "
try:
    import sys
    sys.path.insert(0, '.')
    from exchanges import BinanceSpotClient, BybitSpotClient
    print('Exchange clients: OK')
except Exception as e:
    print('ERROR: Exchange import failed:', str(e))
    sys.exit(1)
"

echo "All components tested successfully"

# STEP 6: Update Service Configuration if Needed
echo ""
echo "STEP 6: Checking service configuration..."
echo "-----------------------------------------"

# Check if service-related files changed
if git diff --name-only HEAD~1..HEAD 2>/dev/null | grep -E "(aws_scanner|setup_aws_service)" | head -1 >/dev/null; then
    echo "Service-related files changed - updating service configuration..."
    
    cd ~/market-scanner/Project/aws_scanner/
    
    # Run setup script if it exists and changed
    if [ -f "setup_aws_service.sh" ] && git diff --name-only HEAD~1..HEAD 2>/dev/null | grep -q "setup_aws_service.sh"; then
        echo "Running updated service setup script..."
        chmod +x setup_aws_service.sh
        ./setup_aws_service.sh
    fi
    
    # Reload systemd daemon to pick up any changes
    sudo systemctl daemon-reload
    echo "Service configuration updated"
    
else
    echo "No service configuration changes detected"
fi

# STEP 7: Restart the Service
echo ""
echo "STEP 7: Starting updated market scanner service..."
echo "---------------------------------------------------"

# Start the service
echo "Starting market-scanner service..."
sudo systemctl start market-scanner.service

# Wait for service to initialize
echo "Waiting for service initialization..."
sleep 8

# Check service status
SERVICE_STATUS=$(check_service_status)
echo "Service status: $SERVICE_STATUS"

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "Service started successfully!"
    
    # Show service details
    echo ""
    echo "Service details:"
    sudo systemctl status market-scanner.service --no-pager -l | head -10
    
    # Show running processes
    echo ""
    echo "Running processes:"
    ps aux | grep -E "(scanner|market)" | grep -v grep
    
    # Show recent logs
    echo ""
    echo "Recent startup logs:"
    sudo journalctl -u market-scanner.service -n 5 --no-pager -l
    
else
    echo "ERROR: Service failed to start after update"
    
    # Show detailed error information
    echo ""
    echo "Service status details:"
    sudo systemctl status market-scanner.service --no-pager -l
    
    echo ""
    echo "Recent error logs:"
    sudo journalctl -u market-scanner.service -n 10 --no-pager -l
    
    echo ""
    echo "Attempting manual test..."
    cd ~/market-scanner/Project/aws_scanner
    source ../venv/bin/activate
    timeout 10s python aws_scanner_service.py || echo "Manual execution failed"
    
    exit 1
fi

# STEP 8: Post-update Verification
echo ""
echo "STEP 8: Post-update verification..."
echo "-----------------------------------"

# Wait a bit more for full initialization
sleep 5

# Run status check
cd ~/market-scanner/Project/aws_scanner/
if [ -f "status.sh" ]; then
    echo "Running comprehensive status check..."
    ./status.sh
else
    echo "Manual status check:"
    echo "Service: $(check_service_status)"
    echo "Process count: $(ps aux | grep -E "(scanner|market)" | grep -v grep | wc -l)"
fi

# Check for any immediate errors
echo ""
echo "Checking for immediate errors..."
ERROR_COUNT=$(sudo journalctl -u market-scanner.service --since "2 minutes ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "WARNING: $ERROR_COUNT error(s) found in recent logs"
    sudo journalctl -u market-scanner.service --since "2 minutes ago" | grep -i error | tail -3
else
    echo "No immediate errors detected"
fi

# STEP 9: Update Summary
echo ""
echo "UPDATE COMPLETED SUCCESSFULLY!"
echo "==============================="

echo ""
echo "Update Summary:"
echo "• Repository: https://github.com/hassou7/market-scanner"
echo "• Current commit: $(git -C ~/market-scanner rev-parse HEAD | head -c 8)"
echo "• Service status: $(check_service_status)"
echo "• Auto-start: $(sudo systemctl is-enabled market-scanner.service)"
echo "• Process count: $(ps aux | grep -E "(scanner|market)" | grep -v grep | wc -l)"

if [ -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log ]; then
    echo "• Last log entry: $(tail -1 ~/market-scanner/Project/aws_scanner/logs/scanner_service.log 2>/dev/null | head -c 80)..."
fi

echo ""
echo "Monitoring Commands:"
echo "• Live logs: sudo journalctl -u market-scanner.service -f"
echo "• App logs: tail -f ~/market-scanner/Project/aws_scanner/logs/scanner_service.log"
echo "• Status check: cd ~/market-scanner/Project/aws_scanner && ./status.sh"
echo "• Service status: sudo systemctl status market-scanner.service"

echo ""
echo "Your Market Scanner has been updated successfully!"
echo "The service is running with the latest code from GitHub."
echo ""
echo "Monitor the logs for a few minutes to ensure everything is working correctly."

# Optional: Show what changed
echo ""
echo "What was updated in this session:"
if [ "$LOCAL_COMMIT" != "$(git -C ~/market-scanner rev-parse HEAD)" ]; then
    echo "Code changes:"
    git -C ~/market-scanner log --oneline $LOCAL_COMMIT..HEAD | head -5
else
    echo "No code changes were applied"
fi