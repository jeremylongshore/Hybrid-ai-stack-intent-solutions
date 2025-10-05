#!/bin/bash
# Download ternary-quantized models (BitNet 1.58-bit)
# Models from Microsoft, TII (Falcon), and community sources

set -e

echo "📥 Downloading Ternary Models (BitNet 1.58-bit)"
echo "=============================================="
echo ""

# Determine install location
INSTALL_DIR="${HOME}/ai_stack"
MODEL_DIR="$INSTALL_DIR/models/ternary"
mkdir -p "$MODEL_DIR"

echo "Model directory: $MODEL_DIR"
echo ""

# Check if huggingface-cli is available
if ! command -v huggingface-cli &> /dev/null; then
    echo "Installing huggingface-cli..."
    pip install --upgrade huggingface-hub
fi

echo "Available ternary models:"
echo "1. Microsoft BitNet b1.58 2B (400MB) - RECOMMENDED"
echo "2. Falcon3-7B-Instruct-1.58bit (2.8GB) - High quality"
echo "3. Falcon3-3B-Instruct-1.58bit (1.2GB) - Balanced"
echo "4. HF1BitLLM Llama3-8B-1.58 (3GB) - Community model"
echo ""

read -p "Which model to download? (1-4, or 'all'): " choice

download_model() {
    local model_id=$1
    local model_name=$2
    local format=$3

    echo ""
    echo "📥 Downloading $model_name..."

    if [ "$format" == "gguf" ]; then
        huggingface-cli download "$model_id" \
            --include "*.gguf" \
            --local-dir "$MODEL_DIR/$model_name" \
            --local-dir-use-symlinks False
    else
        huggingface-cli download "$model_id" \
            --local-dir "$MODEL_DIR/$model_name" \
            --local-dir-use-symlinks False
    fi

    echo "✅ $model_name downloaded to $MODEL_DIR/$model_name"
}

case $choice in
    1)
        download_model "microsoft/BitNet-b1.58-2B-4T-gguf" "bitnet-2b" "gguf"
        ;;
    2)
        download_model "tiiuae/Falcon3-7B-Instruct-1.58bit" "falcon3-7b" "standard"
        ;;
    3)
        download_model "tiiuae/Falcon3-3B-Instruct-1.58bit" "falcon3-3b" "standard"
        ;;
    4)
        download_model "HF1BitLLM/Llama3-8B-1.58-100B-tokens" "llama3-8b-ternary" "standard"
        ;;
    all)
        download_model "microsoft/BitNet-b1.58-2B-4T-gguf" "bitnet-2b" "gguf"
        download_model "tiiuae/Falcon3-7B-Instruct-1.58bit" "falcon3-7b" "standard"
        download_model "tiiuae/Falcon3-3B-Instruct-1.58bit" "falcon3-3b" "standard"
        echo "Note: Skipping Llama3-8B to save space (download separately if needed)"
        ;;
    *)
        echo "Invalid choice, exiting"
        exit 1
        ;;
esac

echo ""
echo "✅ Model download complete!"
echo ""
echo "Models location: $MODEL_DIR"
echo ""
echo "To quantize models for BitNet.cpp:"
echo "cd $INSTALL_DIR/bitnet.cpp"
echo "source venv/bin/activate"
echo "python setup_env.py -md $MODEL_DIR/[model-name] -q i2_s"
echo ""
echo "Next step: Setup ternary server"
echo "./scripts/setup_ternary_service.sh"
