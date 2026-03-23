#!/usr/bin/env python3
"""
Tests for API Gateway (4A)
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gateway'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import once at module level to avoid Prometheus re-registration errors
import app as gateway_app


@pytest.fixture
def client():
    """Create Flask test client with mocked Redis."""
    gateway_app.app.config['TESTING'] = True
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True

    original_redis = gateway_app.redis_client
    gateway_app.redis_client = mock_redis

    with gateway_app.app.test_client() as c:
        yield c, gateway_app, mock_redis

    gateway_app.redis_client = original_redis


class TestIndexEndpoint:
    def test_index_returns_service_info(self, client):
        c, _, _ = client
        resp = c.get('/')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'
        assert 'Hybrid AI Stack' in data['service']


class TestHealthEndpoint:
    def test_health_returns_status(self, client):
        c, _, _ = client
        resp = c.get('/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'api_gateway' in data
        assert data['api_gateway'] == 'healthy'

    def test_health_reports_redis_status(self, client):
        c, _, _ = client
        resp = c.get('/health')
        data = resp.get_json()
        assert 'redis' in data


class TestChatEndpoint:
    def test_chat_missing_prompt(self, client):
        c, _, _ = client
        resp = c.post('/api/v1/chat',
                       json={},
                       content_type='application/json')
        assert resp.status_code == 400
        assert 'Missing prompt' in resp.get_json()['error']

    def test_chat_empty_body(self, client):
        c, _, _ = client
        resp = c.post('/api/v1/chat',
                       data='',
                       content_type='application/json')
        assert resp.status_code == 400

    @patch('app.router')
    def test_chat_auto_routing(self, mock_router, client):
        c, _, _ = client
        mock_router.process_request.return_value = {
            'model': 'tinyllama',
            'backend': 'local',
            'response': 'Hello!',
            'cost': 0.0,
            'routing': {'complexity': 0.1, 'reasoning': 'test', 'estimated_cost': 0.0}
        }

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'What is Python?'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['model'] == 'tinyllama'
        assert data['cached'] is False

    @patch('app.router')
    def test_chat_manual_model_override(self, mock_router, client):
        c, _, _ = client
        mock_router.MODELS = {
            'tinyllama': {'backend': 'local', 'cost_per_token': 0.0},
        }
        mock_router.execute_ollama_request.return_value = {
            'model': 'tinyllama',
            'backend': 'local',
            'response': 'Hi!',
            'cost': 0.0,
        }

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'Hello', 'model': 'tinyllama'},
                       content_type='application/json')
        assert resp.status_code == 200

    @patch('app.router')
    def test_chat_unknown_model_returns_400(self, mock_router, client):
        c, _, _ = client
        mock_router.MODELS = {}

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'Hello', 'model': 'nonexistent'},
                       content_type='application/json')
        assert resp.status_code == 400
        assert 'Unknown model' in resp.get_json()['error']

    def test_chat_prompt_too_long(self, client):
        c, _, _ = client
        resp = c.post('/api/v1/chat',
                       json={'prompt': 'x' * 200_000},
                       content_type='application/json')
        assert resp.status_code == 413

    @patch('app.router')
    def test_chat_cache_hit(self, mock_router, client):
        c, app, mock_redis = client
        cached_response = json.dumps({
            'model': 'tinyllama', 'backend': 'local',
            'response': 'Cached!', 'cost': 0.0,
            'cached': False, 'latency_seconds': 0.5,
            'routing': {'complexity': 0.1, 'reasoning': 'test', 'estimated_cost': 0.0},
        })
        mock_redis.get.return_value = cached_response

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'What is Python?'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['cached'] is True

    @patch('app.router')
    def test_chat_cache_bypass(self, mock_router, client):
        c, app, mock_redis = client
        cached_response = json.dumps({
            'model': 'tinyllama', 'backend': 'local',
            'response': 'Cached!', 'cost': 0.0,
        })
        mock_redis.get.return_value = cached_response

        mock_router.process_request.return_value = {
            'model': 'tinyllama', 'backend': 'local',
            'response': 'Fresh!', 'cost': 0.0,
            'routing': {'complexity': 0.1, 'reasoning': 'test', 'estimated_cost': 0.0},
        }

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'What is Python?'},
                       headers={'Cache-Control': 'no-cache'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['cached'] is False

    @patch('app.router')
    def test_chat_ternary_model_override(self, mock_router, client):
        c, _, _ = client
        mock_router.MODELS = {
            'bitnet-2b': {'backend': 'ternary', 'cost_per_token': 0.0},
        }
        mock_router.execute_ternary_request.return_value = {
            'model': 'bitnet-2b',
            'backend': 'ternary',
            'response': 'Ternary response!',
            'cost': 0.0,
        }

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'Hello', 'model': 'bitnet-2b'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['model'] == 'bitnet-2b'

    @patch('app.router')
    def test_chat_cloud_model_override(self, mock_router, client):
        c, _, _ = client
        mock_router.MODELS = {
            'claude-sonnet': {'backend': 'cloud', 'cost_per_token': 0.000003},
        }
        mock_router.execute_claude_request.return_value = {
            'model': 'claude-sonnet',
            'backend': 'cloud',
            'response': 'Cloud response!',
            'cost': 0.001,
        }

        resp = c.post('/api/v1/chat',
                       json={'prompt': 'Complex question', 'model': 'claude-sonnet'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['backend'] == 'cloud'


class TestComplexityEndpoint:
    @patch('app.router')
    def test_complexity_returns_estimate(self, mock_router, client):
        c, _, _ = client
        mock_router.estimate_complexity.return_value = (0.3, 'test reasoning')
        mock_router.select_model.return_value = 'phi2'
        mock_router.MODELS = {'phi2': {'backend': 'local'}}
        mock_router.estimate_cost.return_value = 0.0

        resp = c.post('/api/v1/complexity',
                       json={'prompt': 'Hello'},
                       content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'complexity' in data
        assert 'recommended_model' in data

    def test_complexity_missing_prompt(self, client):
        c, _, _ = client
        resp = c.post('/api/v1/complexity',
                       json={},
                       content_type='application/json')
        assert resp.status_code == 400


class TestModelsEndpoint:
    def test_models_returns_list(self, client):
        c, _, _ = client
        resp = c.get('/api/v1/models')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'models' in data
        assert len(data['models']) > 0
        for m in data['models']:
            assert 'name' in m
            assert 'backend' in m
            assert 'available' in m
            assert 'cost_per_token' in m


class TestStatsEndpoint:
    @patch('app.router')
    def test_stats_returns_data(self, mock_router, client):
        c, _, _ = client
        mock_router.get_stats.return_value = {
            'total_requests': 10, 'local_requests': 7,
            'cloud_requests': 3, 'ternary_requests': 0,
            'local_percentage': 70.0,
        }
        resp = c.get('/api/v1/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_requests'] == 10


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        c, _, _ = client
        resp = c.get('/metrics')
        assert resp.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
