#!/bin/bash
# Setup systemd service for ternary server
# Runs BitNet.cpp ternary model server as a system service

set -e

echo "🔧 Setting up Ternary Model Server as systemd service"
echo "====================================================="
echo ""

# Check if running with sudo
if [ "$EUID" -eq 0 ]; then
    echo "❌ Do not run this script as root/sudo"
    echo "   The script will ask for sudo when needed"
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)
INSTALL_DIR="${HOME}/ai_stack"
VENV_PATH="$INSTALL_DIR/venv"

# Verify paths exist
if [ ! -d "$INSTALL_DIR/bitnet.cpp" ]; then
    echo "❌ BitNet.cpp not found at $INSTALL_DIR/bitnet.cpp"
    echo "   Run ./scripts/install_ternary.sh first"
    exit 1
fi

if [ ! -f "$INSTALL_DIR/scripts/ternary_server.py" ]; then
    echo "❌ ternary_server.py not found"
    echo "   Expected: $INSTALL_DIR/scripts/ternary_server.py"
    exit 1
fi

# Ensure Python venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Install Flask if needed
echo "Installing Python dependencies..."
source "$VENV_PATH/bin/activate"
pip install flask requests
deactivate

echo ""
echo "Creating systemd service file..."

# Create systemd service file
sudo tee /etc/systemd/system/ternary-server.service > /dev/null << EOF
[Unit]
Description=Ternary Model Server (BitNet 1.58-bit LLMs)
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
Environment="BITNET_PATH=$INSTALL_DIR/bitnet.cpp"
Environment="MODEL_PATH=$INSTALL_DIR/models/ternary"
Environment="DEFAULT_MODEL=bitnet-2b"
ExecStart=$VENV_PATH/bin/python $INSTALL_DIR/scripts/ternary_server.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created: /etc/systemd/system/ternary-server.service"
echo ""

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "Enabling ternary-server service..."
sudo systemctl enable ternary-server.service

# Start service
echo "Starting ternary-server service..."
sudo systemctl start ternary-server.service

# Wait a moment for startup
sleep 2

# Check status
echo ""
echo "Service status:"
sudo systemctl status ternary-server.service --no-pager -l

echo ""
echo "✅ Ternary server service setup complete!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start ternary-server"
echo "  Stop:    sudo systemctl stop ternary-server"
echo "  Restart: sudo systemctl restart ternary-server"
echo "  Status:  sudo systemctl status ternary-server"
echo "  Logs:    sudo journalctl -u ternary-server -f"
echo ""
echo "Test the server:"
echo "  curl http://localhost:8003/health"
echo ""
