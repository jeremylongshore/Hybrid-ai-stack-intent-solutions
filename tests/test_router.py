#!/usr/bin/env python3
"""
Tests for Smart Router
"""

import sys
import os
import pytest

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

    def test_medium_explanation(self):
        """Explanations should have medium complexity"""
        complexity, _ = self.router.estimate_complexity(
            "Explain the difference between lists and tuples in Python."
        )
        assert 0.3 <= complexity <= 0.6

    def test_complex_code_request(self):
        """Code generation should have high complexity"""
        complexity, _ = self.router.estimate_complexity(
            "Write a Python function to implement binary search tree with insert, delete, and search methods."
        )
        assert complexity > 0.6

    def test_code_presence_increases_complexity(self):
        """Presence of code should increase complexity"""
        simple = self.router.estimate_complexity("What is a variable?")[0]
        with_code = self.router.estimate_complexity("What is a variable? ```python\nx = 5\n```")[0]
        assert with_code > simple

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

    def test_claude_has_cost(self):
        """Claude should have non-zero cost"""
        cost = self.router.estimate_cost("test prompt" * 100, "claude-sonnet")
        assert cost > 0.0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
