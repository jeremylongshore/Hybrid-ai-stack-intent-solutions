#!/usr/bin/env python3
"""
API Gateway for Hybrid AI Stack
Routes requests to local or cloud models based on complexity
"""

import hashlib
import json
import os
import sys
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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
CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))
MAX_PROMPT_LENGTH = 100_000

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_client = None

# Rate limiting (3C)
RATE_LIMIT = os.getenv('RATE_LIMIT', '60/minute')
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[RATE_LIMIT],
    storage_uri=f"redis://{REDIS_HOST}:{REDIS_PORT}" if redis_client else "memory://",
)

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
CACHE_COUNTER = Counter(
    'api_gateway_cache_total',
    'Cache hit/miss counts',
    ['result']
)


def _cache_key(prompt: str, model: str) -> str:
    """SHA-256 hash of prompt + model for exact-match caching."""
    raw = f"{prompt}|{model}"
    return f"cache:{hashlib.sha256(raw.encode()).hexdigest()}"


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'service': 'Hybrid AI Stack - API Gateway',
        'status': 'healthy',
        'version': '1.1.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/health')
@limiter.exempt
def health():
    """Detailed health check"""
    health_status = {
        'api_gateway': 'healthy',
        'redis': 'healthy' if redis_client else 'unavailable',
        'router': 'initialized',
        'timestamp': datetime.utcnow().isoformat()
    }

    # Check Ollama connectivity and model availability
    try:
        import requests as req
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        response = req.get(f"{ollama_url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            pulled = {m['name'].split(':')[0] for m in data.get('models', [])}
            required = {'tinyllama', 'phi'}
            missing = required - pulled
            if missing:
                health_status['ollama'] = 'degraded'
                health_status['ollama_missing_models'] = sorted(missing)
            else:
                health_status['ollama'] = 'healthy'
        else:
            health_status['ollama'] = 'error'
    except Exception:
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
        "model": "auto" (optional - auto, tinyllama, phi2, bitnet-2b, claude-sonnet)
    }
    """
    try:
        data = request.get_json(silent=True)

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request body'}), 400

        prompt = data['prompt']

        # Validate prompt length (3C)
        if len(prompt) > MAX_PROMPT_LENGTH:
            return jsonify({'error': f'Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters'}), 413

        model_override = data.get('model', 'auto')
        no_cache = request.headers.get('Cache-Control') == 'no-cache'

        logger.info(f"Received chat request: {prompt[:50]}...")

        # Check cache (3A) — only for exact prompt+model match
        cache_key = _cache_key(prompt, model_override)
        if redis_client and not no_cache:
            cached = redis_client.get(cache_key)
            if cached:
                CACHE_COUNTER.labels(result='hit').inc()
                result = json.loads(cached)
                result['cached'] = True
                return jsonify(result), 200

        CACHE_COUNTER.labels(result='miss').inc()

        start_time = time.time()

        if model_override != 'auto':
            # Direct model selection via MODELS config
            model_config = router.MODELS.get(model_override)
            if not model_config:
                return jsonify({'error': f'Unknown model: {model_override}'}), 400

            backend = model_config['backend']
            if backend == 'local':
                result = router.execute_ollama_request(model_override, prompt)
            elif backend == 'ternary':
                result = router.execute_ternary_request(model_override, prompt)
            elif backend == 'cloud':
                result = router.execute_claude_request(prompt)
            else:
                return jsonify({'error': f'Unknown backend: {backend}'}), 400

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
        result['cached'] = False

        # Update Prometheus metrics
        model = result['model']
        backend = result['backend']
        REQUEST_COUNT.labels(model=model, backend=backend, status='success').inc()
        REQUEST_LATENCY.labels(model=model, backend=backend).observe(latency)
        COST_TRACKER.labels(model=model).inc(result.get('cost', 0))

        logger.info(f"Request processed: model={model}, latency={latency:.2f}s, cost=${result.get('cost', 0):.6f}")

        # Store in cache (3A)
        if redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(result))
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

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
        data = request.get_json(silent=True)

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


@app.route('/api/v1/models', methods=['GET'])
def list_models():
    """List available models with status (3B)"""
    try:
        import requests as req

        # Check Ollama models
        ollama_models = set()
        try:
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            response = req.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                ollama_models = {
                    m['name'].split(':')[0] for m in response.json().get('models', [])
                }
        except Exception:
            pass

        # Check ternary health
        ternary_ok = False
        try:
            ternary_url = os.getenv('TERNARY_URL', 'http://localhost:8003')
            resp = req.get(f"{ternary_url}/health", timeout=2)
            ternary_ok = resp.status_code == 200
        except Exception:
            pass

        has_claude_key = bool(os.getenv('ANTHROPIC_API_KEY'))

        # Map our model names to Ollama names for availability check
        ollama_name_map = {'tinyllama': 'tinyllama', 'phi2': 'phi'}

        models = []
        for name, config in router.MODELS.items():
            backend = config['backend']
            if backend == 'local':
                available = ollama_name_map.get(name, name) in ollama_models
            elif backend == 'ternary':
                available = ternary_ok
            elif backend == 'cloud':
                available = has_claude_key
            else:
                available = False

            models.append({
                'name': name,
                'backend': backend,
                'available': available,
                'cost_per_token': config.get('cost_per_token', 0.0),
                'max_complexity': config.get('max_complexity', 1.0),
            })

        return jsonify({'models': models}), 200
    except Exception as e:
        logger.error(f"Model listing failed: {e}")
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
@limiter.exempt
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    port = int(os.getenv('GATEWAY_PORT', '8080'))
    host = os.getenv('GATEWAY_HOST', '0.0.0.0')

    logger.info(f"Starting API Gateway on {host}:{port}")
    app.run(host=host, port=port, debug=False)
