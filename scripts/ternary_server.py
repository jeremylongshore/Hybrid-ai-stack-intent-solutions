#!/usr/bin/env python3
"""
Ternary Model Server
Serves BitNet ternary-quantized models via HTTP API
Compatible with hybrid-ai-stack smart router
"""

from flask import Flask, request, jsonify
import subprocess
import time
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
BITNET_PATH = os.getenv('BITNET_PATH', os.path.expanduser("~/ai_stack/bitnet.cpp"))
MODEL_PATH = os.getenv('MODEL_PATH', os.path.expanduser("~/ai_stack/models/ternary"))
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'bitnet-2b')

# Model mapping
MODELS = {
    'bitnet-2b': 'bitnet-2b/ggml-model-i2_s.gguf',
    'mistral-7b-ternary': 'falcon3-7b/ggml-model-i2_s.gguf',  # Falcon3 as Mistral alternative
    'llama-8b-ternary': 'llama3-8b-ternary/ggml-model-i2_s.gguf',
    'falcon3-7b': 'falcon3-7b/ggml-model-i2_s.gguf',
    'falcon3-3b': 'falcon3-3b/ggml-model-i2_s.gguf',
}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    models_available = []

    for model_key, model_path in MODELS.items():
        full_path = Path(MODEL_PATH) / model_path
        if full_path.exists():
            models_available.append(model_key)

    return jsonify({
        "status": "healthy",
        "ternary": True,
        "framework": "BitNet.cpp",
        "models_available": models_available,
        "bitnet_path": BITNET_PATH,
        "model_path": MODEL_PATH
    })

@app.route('/generate', methods=['POST'])
def generate():
    """Generate text using ternary model"""
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', DEFAULT_MODEL)
    max_tokens = data.get('max_tokens', 512)
    temperature = data.get('temperature', 0.7)

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    # Get model path
    if model not in MODELS:
        logger.warning(f"Unknown model '{model}', using default: {DEFAULT_MODEL}")
        model = DEFAULT_MODEL

    model_file = Path(MODEL_PATH) / MODELS[model]

    if not model_file.exists():
        return jsonify({
            "error": f"Model not found: {model}",
            "path": str(model_file),
            "available_models": [k for k, v in MODELS.items() if (Path(MODEL_PATH) / v).exists()]
        }), 404

    logger.info(f"Generating with model: {model}, prompt length: {len(prompt)} chars")

    # Run BitNet inference
    start_time = time.time()

    try:
        # BitNet.cpp run_inference.py command
        inference_script = Path(BITNET_PATH) / "run_inference.py"

        if not inference_script.exists():
            return jsonify({"error": "BitNet inference script not found"}), 500

        # Activate venv and run inference
        venv_python = Path(BITNET_PATH) / "venv" / "bin" / "python"

        cmd = [
            str(venv_python),
            str(inference_script),
            "-m", str(model_file),
            "-p", prompt,
            "-n", str(max_tokens),
            "-t", str(temperature)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=BITNET_PATH
        )

        inference_time = (time.time() - start_time) * 1000

        if result.returncode != 0:
            logger.error(f"Inference failed: {result.stderr}")
            return jsonify({
                "error": "Inference failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }), 500

        # Parse output
        response_text = result.stdout.strip()

        # Calculate tokens per second
        tokens_per_second = max_tokens / (inference_time / 1000) if inference_time > 0 else 0

        logger.info(f"Inference completed: {inference_time:.2f}ms, {tokens_per_second:.1f} tok/s")

        return jsonify({
            "text": response_text,
            "model": model,
            "inference_time_ms": inference_time,
            "tokens_per_second": tokens_per_second,
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": max_tokens,
            "backend": "ternary",
            "quantization": "1.58-bit"
        })

    except subprocess.TimeoutExpired:
        logger.error("Inference timeout")
        return jsonify({"error": "Inference timeout (60s)"}), 504
    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    available = []

    for model_key, model_path in MODELS.items():
        full_path = Path(MODEL_PATH) / model_path
        if full_path.exists():
            size_mb = full_path.stat().st_size / (1024 * 1024)
            available.append({
                "name": model_key,
                "path": model_path,
                "size_mb": round(size_mb, 2),
                "quantization": "1.58-bit"
            })

    return jsonify({
        "models": available,
        "count": len(available)
    })

if __name__ == '__main__':
    # Verify BitNet installation
    if not Path(BITNET_PATH).exists():
        logger.error(f"BitNet not found at {BITNET_PATH}")
        logger.error("Run ./scripts/install_ternary.sh first")
        exit(1)

    if not Path(MODEL_PATH).exists():
        logger.warning(f"Model directory not found: {MODEL_PATH}")
        logger.warning("Run ./scripts/download_ternary_models.sh to download models")

    logger.info(f"Starting Ternary Model Server")
    logger.info(f"BitNet path: {BITNET_PATH}")
    logger.info(f"Model path: {MODEL_PATH}")

    # Start Flask server
    app.run(host='0.0.0.0', port=8003, debug=False)
