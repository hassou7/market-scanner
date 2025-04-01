#!/bin/bash
# Setup script for Market Scanner Service on AWS
set -e

echo "Setting up Market Scanner Service..."

# Get the absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Check if Python 3.8+ is installed
python3 --version
if [ $? -ne 0 ]; then
    echo "Python 3 is not installed. Installing..."
    sudo yum update -y
    sudo yum install -y python3 python3-pip python3-devel
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating Python virtual environment..."
    cd "$PROJECT_ROOT"
    python3 -m venv venv
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install python-telegram-bot pandas aiohttp tqdm asyncio numpy

# Set up the systemd service
echo "Setting up systemd service..."
sudo cp "$SCRIPT_DIR/market-scanner.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable market-scanner.service

# Create log rotation config
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/market-scanner > /dev/null << EOF
$SCRIPT_DIR/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 ec2-user ec2-user
}
EOF

echo "Setup complete!"
echo "To start the service, run: sudo systemctl start market-scanner.service"
echo "To check service status: sudo systemctl status market-scanner.service"
echo "To view logs: tail -f $SCRIPT_DIR/logs/scanner_service.log"