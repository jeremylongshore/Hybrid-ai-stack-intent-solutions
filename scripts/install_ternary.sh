#!/bin/bash
# Install BitNet.cpp for ternary model support
# Microsoft's 1.58-bit LLM inference framework

set -e

echo "🔬 Installing Ternary Model Runtime (BitNet.cpp)"
echo "================================================"
echo ""

# Check system requirements
echo "Checking system requirements..."
if [ $(free -g | awk '/^Mem:/{print $2}') -lt 6 ]; then
    echo "⚠️  Warning: Less than 6GB RAM detected"
    echo "   Ternary models work best with 8GB+ RAM"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Determine install location
INSTALL_DIR="${HOME}/ai_stack"
mkdir -p "$INSTALL_DIR"

echo "📦 Installing dependencies..."
# Install build dependencies
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    clang \
    llvm \
    python3 \
    python3-pip

echo ""
echo "📥 Cloning BitNet.cpp repository..."
# Clone BitNet.cpp
cd "$INSTALL_DIR"
if [ ! -d "bitnet.cpp" ]; then
    git clone --recursive https://github.com/microsoft/BitNet.git bitnet.cpp
    cd bitnet.cpp
else
    echo "BitNet.cpp already exists, pulling latest changes..."
    cd bitnet.cpp
    git pull
    git submodule update --init --recursive
fi

echo ""
echo "🔨 Building BitNet.cpp..."
# Setup Python environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Build the project
echo "Compiling with CMake..."
mkdir -p build
cd build
cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
make -j$(nproc)

echo ""
echo "✅ BitNet.cpp installation complete!"
echo ""
echo "Installation location: $INSTALL_DIR/bitnet.cpp"
echo ""
echo "Next steps:"
echo "1. Download ternary models: ./scripts/download_ternary_models.sh"
echo "2. Setup ternary server: ./scripts/setup_ternary_service.sh"
echo "3. Test: cd $INSTALL_DIR/bitnet.cpp && source venv/bin/activate"
echo ""
echo "For more info: https://github.com/microsoft/BitNet"
