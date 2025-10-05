#!/usr/bin/env python3
"""
Smart AI Request Router
Estimates prompt complexity and routes to optimal model (local vs cloud)
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Tuple
from dataclasses import dataclass
import requests
from anthropic import Anthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Routing decision with metadata"""
    model: str
    complexity: float
    estimated_cost: float
    reasoning: str
    backend: str  # 'local' or 'cloud'

class SmartRouter:
    """Intelligent router for AI requests"""

    # Model configurations
    MODELS = {
        'tinyllama': {
            'backend': 'local',
            'max_complexity': 0.3,
            'cost_per_token': 0.0,  # Free (local)
            'endpoint': 'http://localhost:11434/api/generate'
        },
        'phi2': {
            'backend': 'local',
            'max_complexity': 0.6,
            'cost_per_token': 0.0,  # Free (local)
            'endpoint': 'http://localhost:11434/api/generate'
        },
        # NEW: Ternary models (BitNet 1.58-bit)
        'bitnet-2b': {
            'backend': 'ternary',
            'max_complexity': 0.5,
            'cost_per_token': 0.0,  # Free (local)
            'endpoint': 'http://localhost:8003/generate',
            'speed_multiplier': 6.0,  # 6x faster than standard
            'energy_savings': 0.82  # 82% energy reduction
        },
        'mistral-7b-ternary': {
            'backend': 'ternary',
            'max_complexity': 0.8,
            'cost_per_token': 0.0,  # Free (local)
            'endpoint': 'http://localhost:8003/generate',
            'speed_multiplier': 6.0,
            'energy_savings': 0.82
        },
        'claude-sonnet': {
            'backend': 'cloud',
            'max_complexity': 1.0,
            'cost_per_1m_tokens': 3.0,  # $3 per 1M tokens
            'cost_per_token': 0.000003
        }
    }

    # Complexity keywords
    COMPLEX_KEYWORDS = [
        'analyze', 'design', 'architect', 'implement', 'refactor',
        'optimize', 'debug', 'explain in detail', 'comprehensive',
        'write code', 'create function', 'build', 'develop'
    ]

    SIMPLE_KEYWORDS = [
        'summarize', 'list', 'what is', 'define', 'yes or no',
        'classify', 'categorize', 'is this', 'true or false'
    ]

    CODE_PATTERNS = [
        r'```',  # Code blocks
        r'\bdef\b', r'\bclass\b', r'\bfunction\b',  # Function/class definitions
        r'\bimport\b', r'\bfrom\b',  # Imports
        r'[{}\[\]();]',  # Code-like syntax
    ]

    def __init__(self, use_local: bool = True, complexity_threshold: float = 0.5, use_ternary: bool = True):
        """Initialize router with configuration"""
        self.use_local = use_local
        self.complexity_threshold = complexity_threshold
        self.use_ternary = use_ternary
        self.ternary_available = False
        self.anthropic_client = None

        # Check if ternary runtime is available
        if self.use_ternary:
            self.ternary_available = self._check_ternary_available()
            if self.ternary_available:
                logger.info("✅ Ternary runtime detected and available")
            else:
                logger.info("ℹ️  Ternary runtime not available, using standard models")

        # Initialize Anthropic client if API key available
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic_client = Anthropic(api_key=api_key)
        else:
            logger.warning("ANTHROPIC_API_KEY not set - cloud routing disabled")

    def _check_ternary_available(self) -> bool:
        """Check if ternary runtime is installed and running"""
        try:
            ternary_url = os.getenv('TERNARY_URL', 'http://localhost:8003')
            response = requests.get(f"{ternary_url}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('ternary', False)
            return False
        except:
            return False

    def estimate_complexity(self, prompt: str) -> Tuple[float, str]:
        """
        Estimate prompt complexity on 0-1 scale
        Returns: (complexity_score, reasoning)
        """
        factors = []
        score = 0.0

        # Factor 1: Length (longer = more complex)
        length = len(prompt)
        if length < 100:
            length_score = 0.1
            factors.append("short prompt")
        elif length < 500:
            length_score = 0.3
            factors.append("medium length")
        else:
            length_score = 0.5
            factors.append("long prompt")
        score += length_score

        # Factor 2: Complexity keywords
        prompt_lower = prompt.lower()
        complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in prompt_lower)
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in prompt_lower)

        if complex_count > 0:
            keyword_score = min(0.3, complex_count * 0.1)
            factors.append(f"{complex_count} complex keywords")
        elif simple_count > 0:
            keyword_score = -0.1
            factors.append("simple task keywords")
        else:
            keyword_score = 0.1
            factors.append("neutral keywords")
        score += keyword_score

        # Factor 3: Code detection
        code_matches = sum(1 for pattern in self.CODE_PATTERNS
                          if re.search(pattern, prompt))
        if code_matches >= 2:
            code_score = 0.3
            factors.append("contains code")
        else:
            code_score = 0.0
        score += code_score

        # Factor 4: Questions vs instructions
        if '?' in prompt and prompt.count('?') <= 2:
            question_score = -0.1
            factors.append("simple question")
        elif 'create' in prompt_lower or 'build' in prompt_lower:
            question_score = 0.2
            factors.append("creative task")
        else:
            question_score = 0.0
        score += question_score

        # Normalize to 0-1 range
        final_score = max(0.0, min(1.0, score))
        reasoning = f"Complexity {final_score:.2f}: {', '.join(factors)}"

        return final_score, reasoning

    def select_model(self, complexity: float) -> str:
        """Select optimal model based on complexity"""
        # Ternary-optimized routing (if available)
        if self.ternary_available:
            if complexity < 0.5:
                return 'bitnet-2b'  # Fast, efficient 2B model
            elif complexity < 0.8:
                return 'mistral-7b-ternary'  # 7B quality, 2.5GB RAM
            else:
                return 'claude-sonnet'  # Ultra-complex only
        # Standard routing (no ternary)
        elif not self.use_local or complexity > 0.6:
            return 'claude-sonnet'
        elif complexity < 0.3:
            return 'tinyllama'
        else:
            return 'phi2'

    def estimate_cost(self, prompt: str, model: str, response_length: int = 500) -> float:
        """Estimate cost for request"""
        model_config = self.MODELS.get(model)
        if not model_config or model_config['backend'] == 'local':
            return 0.0

        # Rough token estimation (4 chars H 1 token)
        prompt_tokens = len(prompt) / 4
        total_tokens = prompt_tokens + response_length

        cost = total_tokens * model_config['cost_per_token']
        return cost

    def route_request(self, prompt: str) -> RoutingDecision:
        """
        Main routing logic - determines which model to use
        Returns RoutingDecision with all metadata
        """
        # Estimate complexity
        complexity, reasoning = self.estimate_complexity(prompt)

        # Select model
        model = self.select_model(complexity)
        model_config = self.MODELS[model]

        # Estimate cost
        cost = self.estimate_cost(prompt, model)

        decision = RoutingDecision(
            model=model,
            complexity=complexity,
            estimated_cost=cost,
            reasoning=reasoning,
            backend=model_config['backend']
        )

        logger.info(f"Routing decision: {model} (complexity: {complexity:.2f}, cost: ${cost:.6f})")
        logger.info(f"Reasoning: {reasoning}")

        return decision

    def execute_ternary_request(self, model: str, prompt: str) -> Dict:
        """Execute request on ternary model server (BitNet)"""
        ternary_url = os.getenv('TERNARY_URL', 'http://localhost:8003')
        endpoint = f"{ternary_url}/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": 512
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            return {
                'model': model,
                'backend': 'ternary',
                'response': result.get('text', ''),
                'inference_time_ms': result.get('inference_time_ms', 0),
                'tokens_per_second': result.get('tokens_per_second', 0),
                'cost': 0.0,
                'quantization': '1.58-bit'
            }
        except Exception as e:
            logger.error(f"Ternary request failed: {e}, falling back to cloud")
            # Fallback to Claude if ternary fails
            return self.execute_claude_request(prompt)

    def execute_ollama_request(self, model: str, prompt: str) -> Dict:
        """Execute request on local Ollama server"""
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        endpoint = f"{ollama_url}/api/generate"

        # Map our model names to Ollama model names
        ollama_models = {
            'tinyllama': 'tinyllama',
            'phi2': 'phi'
        }
        ollama_model = ollama_models.get(model, model)

        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            return {
                'model': model,
                'backend': 'local',
                'response': result.get('response', ''),
                'tokens': result.get('total_duration', 0),
                'cost': 0.0
            }
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def execute_claude_request(self, prompt: str) -> Dict:
        """Execute request on Claude API"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Calculate actual cost
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost = (input_tokens + output_tokens) * self.MODELS['claude-sonnet']['cost_per_token']

            return {
                'model': 'claude-sonnet',
                'backend': 'cloud',
                'response': message.content[0].text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost': cost
            }
        except Exception as e:
            logger.error(f"Claude request failed: {e}")
            raise

    def process_request(self, prompt: str) -> Dict:
        """
        Complete request processing: route + execute
        Returns full response with metadata
        """
        # Route the request
        decision = self.route_request(prompt)

        # Execute based on backend
        if decision.backend == 'ternary':
            result = self.execute_ternary_request(decision.model, prompt)
        elif decision.backend == 'local':
            result = self.execute_ollama_request(decision.model, prompt)
        else:
            result = self.execute_claude_request(prompt)

        # Add routing metadata
        result['routing'] = {
            'complexity': decision.complexity,
            'reasoning': decision.reasoning,
            'estimated_cost': decision.estimated_cost
        }

        # Log to Taskwarrior (if available)
        self.log_to_taskwarrior(decision, result)

        return result

    def log_to_taskwarrior(self, decision: RoutingDecision, result: Dict):
        """Log routing decision to Taskwarrior"""
        try:
            annotation = (
                f"Model: {decision.model}, "
                f"Complexity: {decision.complexity:.2f}, "
                f"Cost: ${result.get('cost', 0):.6f}"
            )

            # Create task in Taskwarrior
            os.system(
                f'task add "AI Request: {decision.model}" '
                f'project:vps_ai.router +routing '
                f'"{annotation}" 2>/dev/null'
            )
        except Exception as e:
            logger.debug(f"Taskwarrior logging failed: {e}")

    def get_stats(self) -> Dict:
        """Get routing statistics (from Taskwarrior)"""
        try:
            # Query Taskwarrior for stats
            import subprocess
            result = subprocess.run(
                ['task', 'project:vps_ai.router', 'export'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout:
                tasks = json.loads(result.stdout)

                total_requests = len(tasks)
                local_requests = sum(1 for t in tasks if 'tinyllama' in str(t) or 'phi2' in str(t))
                cloud_requests = sum(1 for t in tasks if 'claude' in str(t))

                return {
                    'total_requests': total_requests,
                    'local_requests': local_requests,
                    'cloud_requests': cloud_requests,
                    'local_percentage': (local_requests / total_requests * 100) if total_requests > 0 else 0
                }
        except:
            pass

        return {'total_requests': 0, 'local_requests': 0, 'cloud_requests': 0, 'local_percentage': 0}


def main():
    """CLI interface for smart router"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python smart_router.py <prompt>")
        print("Example: python smart_router.py 'What is Python?'")
        sys.exit(1)

    prompt = ' '.join(sys.argv[1:])

    # Initialize router
    router = SmartRouter()

    # Process request
    result = router.process_request(prompt)

    # Display results
    print(f"\n{'='*60}")
    print(f"Model: {result['model']} ({result['backend']})")
    print(f"Complexity: {result['routing']['complexity']:.2f}")
    print(f"Reasoning: {result['routing']['reasoning']}")
    print(f"Cost: ${result['cost']:.6f}")
    print(f"{'='*60}\n")
    print(result['response'])
    print(f"\n{'='*60}")

    # Show stats
    stats = router.get_stats()
    print(f"\nRouting Stats:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Local: {stats['local_requests']} ({stats['local_percentage']:.1f}%)")
    print(f"  Cloud: {stats['cloud_requests']}")


if __name__ == '__main__':
    main()
