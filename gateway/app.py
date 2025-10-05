#!/usr/bin/env python3
"""
API Gateway for Hybrid AI Stack
Routes requests to local or cloud models based on complexity
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from dotenv import load_dotenv
import redis

# Add parent directory to path to import smart_router
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from smart_router import SmartRouter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Redis for caching (optional)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_client = None

# Initialize Smart Router
router = SmartRouter(
    use_local=os.getenv('USE_LOCAL_FOR_SIMPLE', 'true').lower() == 'true',
    complexity_threshold=float(os.getenv('COMPLEXITY_THRESHOLD', '0.5'))
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'api_gateway_requests_total',
    'Total requests to API gateway',
    ['model', 'backend', 'status']
)
REQUEST_LATENCY = Histogram(
    'api_gateway_request_duration_seconds',
    'Request latency in seconds',
    ['model', 'backend']
)
COST_TRACKER = Counter(
    'api_gateway_cost_total',
    'Total estimated cost in USD',
    ['model']
)


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'service': 'Hybrid AI Stack - API Gateway',
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/health')
def health():
    """Detailed health check"""
    health_status = {
        'api_gateway': 'healthy',
        'redis': 'healthy' if redis_client else 'unavailable',
        'router': 'initialized',
        'timestamp': datetime.utcnow().isoformat()
    }

    # Check Ollama connectivity
    try:
        import requests as req
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        response = req.get(f"{ollama_url}/api/tags", timeout=2)
        health_status['ollama'] = 'healthy' if response.status_code == 200 else 'error'
    except:
        health_status['ollama'] = 'unavailable'

    # Check Claude API key
    health_status['claude_api'] = 'configured' if os.getenv('ANTHROPIC_API_KEY') else 'not configured'

    return jsonify(health_status)


@app.route('/api/v1/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint - routes request through smart router

    Request body:
    {
        "prompt": "Your question or task",
        "model": "auto" (optional - auto, tinyllama, phi2, claude-sonnet)
    }
    """
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request body'}), 400

        prompt = data['prompt']
        model_override = data.get('model', 'auto')

        logger.info(f"Received chat request: {prompt[:50]}...")

        # Use smart router to process request
        import time
        start_time = time.time()

        if model_override != 'auto':
            # Direct model selection
            if model_override in ['tinyllama', 'phi2']:
                result = router.execute_ollama_request(model_override, prompt)
            elif model_override == 'claude-sonnet':
                result = router.execute_claude_request(prompt)
            else:
                return jsonify({'error': f'Unknown model: {model_override}'}), 400

            # Add routing metadata
            result['routing'] = {
                'complexity': 0,
                'reasoning': f'Manual model selection: {model_override}',
                'estimated_cost': result.get('cost', 0)
            }
        else:
            # Smart routing
            result = router.process_request(prompt)

        # Calculate latency
        latency = time.time() - start_time
        result['latency_seconds'] = latency

        # Update Prometheus metrics
        model = result['model']
        backend = result['backend']
        REQUEST_COUNT.labels(model=model, backend=backend, status='success').inc()
        REQUEST_LATENCY.labels(model=model, backend=backend).observe(latency)
        COST_TRACKER.labels(model=model).inc(result.get('cost', 0))

        logger.info(f"Request processed: model={model}, latency={latency:.2f}s, cost=${result.get('cost', 0):.6f}")

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Chat request failed: {e}", exc_info=True)
        REQUEST_COUNT.labels(model='unknown', backend='unknown', status='error').inc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/complexity', methods=['POST'])
def estimate_complexity():
    """
    Estimate prompt complexity without executing it

    Request body:
    {
        "prompt": "Your question or task"
    }
    """
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request body'}), 400

        prompt = data['prompt']

        # Get complexity estimate
        complexity, reasoning = router.estimate_complexity(prompt)
        selected_model = router.select_model(complexity)

        return jsonify({
            'complexity': complexity,
            'reasoning': reasoning,
            'recommended_model': selected_model,
            'backend': router.MODELS[selected_model]['backend'],
            'estimated_cost': router.estimate_cost(prompt, selected_model)
        }), 200

    except Exception as e:
        logger.error(f"Complexity estimation failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Get routing statistics"""
    try:
        stats = router.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    port = int(os.getenv('GATEWAY_PORT', '8080'))
    host = os.getenv('GATEWAY_HOST', '0.0.0.0')

    logger.info(f"Starting API Gateway on {host}:{port}")
    app.run(host=host, port=port, debug=False)
