#!/usr/bin/env python3
"""
Tests for Smart Router
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from smart_router import SmartRouter


class TestComplexityEstimation:
    """Test complexity estimation logic"""

    def setup_method(self):
        self.router = SmartRouter()

    def test_simple_question(self):
        """Simple questions should have low complexity"""
        complexity, _ = self.router.estimate_complexity("What is Python?")
        assert complexity < 0.3

    def test_medium_prompt(self):
        """Medium-length prompts with neutral keywords score in the middle range"""
        # >100 chars (0.3 length) + neutral keywords (0.1) = 0.4
        prompt = "Please explain how the garbage collector works in Java and what strategies it uses. " * 2
        complexity, _ = self.router.estimate_complexity(prompt)
        assert 0.2 <= complexity <= 0.6

    def test_complex_code_request(self):
        """Code generation with complex keywords should have high complexity"""
        # build (+0.2 creative) + implement (+0.1 complex keyword) + >100 chars (0.3) + code patterns
        prompt = (
            "Build and implement a complete REST API with authentication, "
            "database models, and comprehensive test coverage. "
            "```python\nclass UserModel:\n    pass\n```"
        )
        complexity, _ = self.router.estimate_complexity(prompt)
        assert complexity > 0.6

    def test_code_presence_increases_complexity(self):
        """Presence of code blocks should increase complexity"""
        simple = self.router.estimate_complexity("What is a variable?")[0]
        with_code = self.router.estimate_complexity(
            "What does this code do? ```python\ndef foo():\n    import os\n    return os.getcwd()\n```"
        )[0]
        assert with_code > simple

    def test_empty_prompt(self):
        """Empty prompt should have minimal complexity"""
        complexity, _ = self.router.estimate_complexity("")
        assert complexity >= 0.0
        assert complexity <= 1.0

    def test_very_long_prompt(self):
        """Very long prompts should score high on length factor"""
        prompt = "analyze this data " * 200  # >500 chars
        complexity, _ = self.router.estimate_complexity(prompt)
        assert complexity >= 0.5

    def test_none_handling(self):
        """None prompt should raise an error"""
        with pytest.raises((TypeError, AttributeError)):
            self.router.estimate_complexity(None)

    def test_complexity_always_normalized(self):
        """Complexity should always be between 0.0 and 1.0"""
        prompts = [
            "",
            "hi",
            "What is Python?",
            "analyze and design " * 100,
            "```python\ndef x():\n    pass\n```" * 5,
        ]
        for p in prompts:
            c, _ = self.router.estimate_complexity(p)
            assert 0.0 <= c <= 1.0, f"Complexity {c} out of range for prompt: {p[:50]}"


class TestModelSelection:
    """Test model selection logic"""

    def setup_method(self):
        self.router = SmartRouter()

    def test_tinyllama_for_simple(self):
        """TinyLlama should be selected for simple prompts"""
        model = self.router.select_model(0.2)
        assert model == 'tinyllama'

    def test_phi2_for_medium(self):
        """Phi-2 should be selected for medium prompts"""
        model = self.router.select_model(0.5)
        assert model == 'phi2'

    def test_claude_for_complex(self):
        """Claude should be selected for complex prompts"""
        model = self.router.select_model(0.8)
        assert model == 'claude-sonnet'

    def test_boundary_low(self):
        """Boundary: exactly 0.3 should select phi2"""
        model = self.router.select_model(0.3)
        assert model == 'phi2'

    def test_boundary_high(self):
        """Boundary: exactly 0.6 should select phi2"""
        model = self.router.select_model(0.6)
        assert model == 'phi2'

    def test_above_0_6(self):
        """Above 0.6 should select claude-sonnet"""
        model = self.router.select_model(0.61)
        assert model == 'claude-sonnet'


class TestTernaryRouting:
    """Test ternary model routing (4B)"""

    def setup_method(self):
        self.router = SmartRouter()
        self.router.ternary_available = True

    def test_ternary_simple_selects_bitnet(self):
        """Simple prompts should route to bitnet-2b when ternary available"""
        model = self.router.select_model(0.3)
        assert model == 'bitnet-2b'

    def test_ternary_medium_selects_mistral(self):
        """Medium prompts should route to mistral-7b-ternary"""
        model = self.router.select_model(0.6)
        assert model == 'mistral-7b-ternary'

    def test_ternary_complex_selects_claude(self):
        """Complex prompts still go to Claude even with ternary"""
        model = self.router.select_model(0.9)
        assert model == 'claude-sonnet'

    def test_ternary_boundary_0_5(self):
        """Boundary: 0.5 should select mistral-7b-ternary"""
        model = self.router.select_model(0.5)
        assert model == 'mistral-7b-ternary'

    def test_ternary_boundary_0_8(self):
        """Boundary: 0.8 should select claude-sonnet"""
        model = self.router.select_model(0.8)
        assert model == 'claude-sonnet'

    @patch('smart_router.requests.post')
    def test_ternary_execute_success(self, mock_post):
        """Ternary execution should return properly structured result"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'text': 'Hello!',
            'inference_time_ms': 50,
            'tokens_per_second': 100,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.router.execute_ternary_request('bitnet-2b', 'Hello')
        assert result['model'] == 'bitnet-2b'
        assert result['backend'] == 'ternary'
        assert result['cost'] == 0.0
        assert result['response'] == 'Hello!'

    @patch('smart_router.requests.post')
    def test_ternary_fallback_to_claude(self, mock_post):
        """Ternary failure should fall back to Claude"""
        mock_post.side_effect = ConnectionError("Ternary server down")
        self.router.anthropic_client = MagicMock()

        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Fallback response")]
        mock_msg.usage.input_tokens = 10
        mock_msg.usage.output_tokens = 20
        self.router.anthropic_client.messages.create.return_value = mock_msg

        result = self.router.execute_ternary_request('bitnet-2b', 'Hello')
        assert result['backend'] == 'cloud'
        assert result['model'] == 'claude-sonnet'


class TestCostEstimation:
    """Test cost estimation"""

    def setup_method(self):
        self.router = SmartRouter()

    def test_local_models_zero_cost(self):
        """Local models should have zero cost"""
        cost_tinyllama = self.router.estimate_cost("test prompt", "tinyllama")
        cost_phi2 = self.router.estimate_cost("test prompt", "phi2")
        assert cost_tinyllama == 0.0
        assert cost_phi2 == 0.0

    def test_ternary_models_zero_cost(self):
        """Ternary models should have zero cost"""
        cost = self.router.estimate_cost("test prompt", "bitnet-2b")
        assert cost == 0.0
        cost2 = self.router.estimate_cost("test prompt", "mistral-7b-ternary")
        assert cost2 == 0.0

    def test_claude_has_cost(self):
        """Claude should have non-zero cost"""
        cost = self.router.estimate_cost("test prompt" * 100, "claude-sonnet")
        assert cost > 0.0

    def test_unknown_model_zero_cost(self):
        """Unknown model should return zero cost"""
        cost = self.router.estimate_cost("test", "nonexistent-model")
        assert cost == 0.0

    def test_token_counting_with_tiktoken(self):
        """Token count should be reasonable for known text"""
        count = SmartRouter._count_tokens("Hello, world!")
        # tiktoken should give us a precise count; fallback gives len//4
        assert count > 0
        assert count < 100  # "Hello, world!" is ~4 tokens

    def test_token_count_empty_string(self):
        """Empty string should have zero tokens"""
        count = SmartRouter._count_tokens("")
        assert count == 0


class TestErrorPaths:
    """Test error handling (4C)"""

    def setup_method(self):
        self.router = SmartRouter()

    @patch('smart_router.requests.post')
    def test_ollama_connection_failure(self, mock_post):
        """Ollama connection failure should raise"""
        mock_post.side_effect = ConnectionError("Connection refused")
        with pytest.raises(ConnectionError):
            self.router.execute_ollama_request('tinyllama', 'Hello')

    def test_claude_missing_api_key(self):
        """Claude request without API key should raise ValueError"""
        self.router.anthropic_client = None
        with pytest.raises(ValueError, match="Anthropic API key not configured"):
            self.router.execute_claude_request("Hello")

    @patch('smart_router.requests.post')
    def test_ollama_malformed_response(self, mock_post):
        """Malformed Ollama response should handle gracefully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing 'response' key
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.router.execute_ollama_request('tinyllama', 'Hello')
        assert result['response'] == ''  # .get() returns default ''

    @patch('smart_router.requests.post')
    def test_ollama_http_error(self, mock_post):
        """Ollama HTTP error should propagate"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="500 Server Error"):
            self.router.execute_ollama_request('tinyllama', 'Hello')


class TestTaskwarriorLogging:
    """Test Taskwarrior logging safety"""

    def setup_method(self):
        self.router = SmartRouter()

    def test_logging_disabled_by_default(self):
        """Taskwarrior logging should be disabled by default"""
        assert not self.router.taskwarrior_enabled

    @patch.dict(os.environ, {'ENABLE_TASKWARRIOR_LOGGING': 'true'})
    @patch('smart_router.subprocess.run')
    def test_logging_uses_subprocess(self, mock_run):
        """When enabled, should use subprocess.run with list args"""
        router = SmartRouter()
        router.taskwarrior_enabled = True

        from smart_router import RoutingDecision
        decision = RoutingDecision(
            model='tinyllama', complexity=0.2,
            estimated_cost=0.0, reasoning='test', backend='local'
        )
        router.log_to_taskwarrior(decision, {'cost': 0.0})

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)
        assert args[0] == 'task'
        assert 'AI Request: tinyllama' in args


class TestGetStats:
    """Test stats parsing"""

    def setup_method(self):
        self.router = SmartRouter()

    @patch('smart_router.subprocess.run')
    def test_stats_parsing_correct(self, mock_run):
        """Stats should parse task descriptions properly"""
        tasks = [
            {'description': 'AI Request: tinyllama', 'status': 'completed'},
            {'description': 'AI Request: phi2', 'status': 'completed'},
            {'description': 'AI Request: claude-sonnet', 'status': 'completed'},
            {'description': 'AI Request: bitnet-2b', 'status': 'completed'},
            {'description': 'Some other task', 'status': 'completed'},
        ]
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(tasks)
        )

        stats = self.router.get_stats()
        assert stats['total_requests'] == 4
        assert stats['local_requests'] == 2  # tinyllama + phi2
        assert stats['cloud_requests'] == 1  # claude-sonnet
        assert stats['ternary_requests'] == 1  # bitnet-2b

    @patch('smart_router.subprocess.run')
    def test_stats_empty(self, mock_run):
        """Empty Taskwarrior should return zeros"""
        mock_run.return_value = MagicMock(returncode=0, stdout='[]')
        stats = self.router.get_stats()
        assert stats['total_requests'] == 0

    @patch('smart_router.subprocess.run')
    def test_stats_taskwarrior_unavailable(self, mock_run):
        """Missing Taskwarrior should return zeros gracefully"""
        mock_run.side_effect = FileNotFoundError("task not found")
        stats = self.router.get_stats()
        assert stats['total_requests'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
