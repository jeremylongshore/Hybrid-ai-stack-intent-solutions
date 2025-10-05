#!/usr/bin/env python3
"""
Prompt Templates and Benchmarks for Hybrid AI Stack

This module provides categorized prompts for testing and benchmarking
the smart routing system's complexity estimation and model selection.
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class PromptTemplate:
    """Template for a test prompt"""
    prompt: str
    category: str
    expected_complexity: str  # 'low', 'medium', 'high'
    expected_model: str  # 'tinyllama', 'phi2', 'claude-sonnet'
    description: str

class PromptLibrary:
    """Collection of test prompts for benchmarking"""

    # Simple prompts (should route to TinyLlama)
    SIMPLE_PROMPTS = [
        PromptTemplate(
            prompt="What is Python?",
            category="knowledge",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Basic factual question"
        ),
        PromptTemplate(
            prompt="List the days of the week.",
            category="knowledge",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Simple list retrieval"
        ),
        PromptTemplate(
            prompt="What is 2 + 2?",
            category="math",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Basic arithmetic"
        ),
        PromptTemplate(
            prompt="Translate 'hello' to Spanish.",
            category="language",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Simple translation"
        ),
        PromptTemplate(
            prompt="What is the capital of France?",
            category="knowledge",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Basic geography"
        ),
    ]

    # Medium complexity prompts (should route to Phi-2)
    MEDIUM_PROMPTS = [
        PromptTemplate(
            prompt="Explain the difference between Python lists and tuples.",
            category="knowledge",
            expected_complexity="medium",
            expected_model="phi2",
            description="Comparative explanation"
        ),
        PromptTemplate(
            prompt="What are the main benefits of using Docker containers?",
            category="technology",
            expected_complexity="medium",
            expected_model="phi2",
            description="Conceptual explanation"
        ),
        PromptTemplate(
            prompt="Summarize the key features of agile software development.",
            category="methodology",
            expected_complexity="medium",
            expected_model="phi2",
            description="Summary of concepts"
        ),
        PromptTemplate(
            prompt="How does HTTP differ from HTTPS?",
            category="networking",
            expected_complexity="medium",
            expected_model="phi2",
            description="Technical comparison"
        ),
        PromptTemplate(
            prompt="What are the advantages of microservices architecture?",
            category="architecture",
            expected_complexity="medium",
            expected_model="phi2",
            description="Architectural concepts"
        ),
    ]

    # Complex prompts (should route to Claude)
    COMPLEX_PROMPTS = [
        PromptTemplate(
            prompt="""Write a Python function to implement a binary search tree with the following methods:
- insert(value)
- delete(value)
- search(value)
- in_order_traversal()

Include proper error handling and documentation.""",
            category="programming",
            expected_complexity="high",
            expected_model="claude-sonnet",
            description="Complex code generation"
        ),
        PromptTemplate(
            prompt="""Design a microservices architecture for an e-commerce platform.
Include:
- Service decomposition strategy
- Communication patterns
- Data consistency approach
- Deployment strategy
- Monitoring and observability

Provide detailed reasoning for your choices.""",
            category="architecture",
            expected_complexity="high",
            expected_model="claude-sonnet",
            description="Complex architectural design"
        ),
        PromptTemplate(
            prompt="""Analyze the following code and suggest improvements for performance, security, and maintainability:

```python
def process_data(data):
    result = []
    for item in data:
        if item['status'] == 'active':
            value = item['value'] * 2
            result.append(value)
    return result
```

Provide specific code examples for each improvement.""",
            category="code_review",
            expected_complexity="high",
            expected_model="claude-sonnet",
            description="Code analysis and refactoring"
        ),
        PromptTemplate(
            prompt="""Explain the CAP theorem and provide real-world examples of systems that prioritize:
1. Consistency and Partition Tolerance (CP)
2. Availability and Partition Tolerance (AP)

Include specific database systems and when you would choose each approach.""",
            category="distributed_systems",
            expected_complexity="high",
            expected_model="claude-sonnet",
            description="Advanced distributed systems concepts"
        ),
        PromptTemplate(
            prompt="""Create a comprehensive testing strategy for a React application including:
- Unit testing approach and tools
- Integration testing strategy
- End-to-end testing setup
- Performance testing considerations
- CI/CD integration

Provide code examples for each testing type.""",
            category="testing",
            expected_complexity="high",
            expected_model="claude-sonnet",
            description="Comprehensive testing strategy"
        ),
    ]

    # Edge case prompts
    EDGE_CASE_PROMPTS = [
        PromptTemplate(
            prompt="",
            category="edge_case",
            expected_complexity="low",
            expected_model="tinyllama",
            description="Empty prompt"
        ),
        PromptTemplate(
            prompt="a" * 1000,
            category="edge_case",
            expected_complexity="medium",
            expected_model="phi2",
            description="Very long repetitive prompt"
        ),
        PromptTemplate(
            prompt="```python\ndef foo():\n    pass\n```",
            category="edge_case",
            expected_complexity="medium",
            expected_model="phi2",
            description="Code block only"
        ),
    ]

    @classmethod
    def get_all_prompts(cls) -> List[PromptTemplate]:
        """Get all prompt templates"""
        return (
            cls.SIMPLE_PROMPTS +
            cls.MEDIUM_PROMPTS +
            cls.COMPLEX_PROMPTS +
            cls.EDGE_CASE_PROMPTS
        )

    @classmethod
    def get_by_category(cls, category: str) -> List[PromptTemplate]:
        """Get prompts by category"""
        all_prompts = cls.get_all_prompts()
        return [p for p in all_prompts if p.category == category]

    @classmethod
    def get_by_complexity(cls, complexity: str) -> List[PromptTemplate]:
        """Get prompts by expected complexity"""
        all_prompts = cls.get_all_prompts()
        return [p for p in all_prompts if p.expected_complexity == complexity]

    @classmethod
    def get_benchmark_suite(cls) -> List[PromptTemplate]:
        """Get a balanced benchmark suite"""
        return [
            cls.SIMPLE_PROMPTS[0],
            cls.SIMPLE_PROMPTS[1],
            cls.MEDIUM_PROMPTS[0],
            cls.MEDIUM_PROMPTS[1],
            cls.COMPLEX_PROMPTS[0],
            cls.COMPLEX_PROMPTS[1],
        ]


def generate_custom_prompts() -> Dict[str, List[str]]:
    """Generate additional custom prompts for specific use cases"""

    return {
        'data_analysis': [
            "Calculate the mean, median, and mode of this dataset: [1, 2, 3, 4, 5, 5]",
            "Write a SQL query to find the top 10 customers by revenue.",
            "Analyze this CSV data and identify trends and anomalies: [data]",
        ],
        'customer_support': [
            "What are your business hours?",
            "How do I reset my password?",
            "I'm experiencing an error when trying to checkout. The error message is [...]",
        ],
        'content_generation': [
            "Write a tweet about AI safety.",
            "Create a product description for a smart watch.",
            "Write a comprehensive blog post about the benefits of cloud computing.",
        ],
        'code_debugging': [
            "Why is this code not working? [code snippet]",
            "How do I fix this error: 'NoneType object has no attribute X'?",
            "Optimize this function for better performance: [code]",
        ],
        'translation': [
            "Translate 'hello world' to French.",
            "Translate this paragraph to Spanish: [text]",
            "Provide a professional translation of this business email: [email]",
        ]
    }


def print_prompt_stats():
    """Print statistics about the prompt library"""
    all_prompts = PromptLibrary.get_all_prompts()

    print("\n" + "="*60)
    print("PROMPT LIBRARY STATISTICS")
    print("="*60)
    print(f"Total Prompts: {len(all_prompts)}")
    print()

    # By complexity
    for complexity in ['low', 'medium', 'high']:
        prompts = PromptLibrary.get_by_complexity(complexity)
        print(f"  {complexity.capitalize()} Complexity: {len(prompts)}")

    print()

    # By category
    categories = set(p.category for p in all_prompts)
    print("Categories:")
    for cat in sorted(categories):
        prompts = PromptLibrary.get_by_category(cat)
        print(f"  {cat}: {len(prompts)}")

    print("="*60 + "\n")


def main():
    """Demo usage of prompt templates"""
    print_prompt_stats()

    print("BENCHMARK SUITE:")
    print("-" * 60)
    for i, prompt in enumerate(PromptLibrary.get_benchmark_suite(), 1):
        print(f"\n{i}. [{prompt.expected_complexity.upper()}] {prompt.category}")
        print(f"   Description: {prompt.description}")
        print(f"   Expected Model: {prompt.expected_model}")
        print(f"   Prompt: {prompt.prompt[:80]}...")


if __name__ == '__main__':
    main()
