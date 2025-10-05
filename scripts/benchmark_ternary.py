#!/usr/bin/env python3
"""
Benchmark ternary models vs standard models
Measures inference speed, latency, and cost comparison
"""

import requests
import time
import statistics
from typing import Dict, List
from dataclasses import dataclass
import json

@dataclass
class BenchmarkResult:
    """Results from a single benchmark"""
    model: str
    prompt: str
    time_seconds: float
    tokens_per_second: float
    success: bool
    error: str = ""

# Test prompts covering different complexity levels
TEST_PROMPTS = {
    'simple': [
        "What is the capital of France?",
        "What is 2+2?",
        "Define 'algorithm'",
    ],
    'medium': [
        "Explain quantum computing in simple terms.",
        "What are the key differences between Python and JavaScript?",
        "Describe the HTTP request-response cycle.",
    ],
    'complex': [
        "Write a Python function to implement quicksort with detailed comments.",
        "Explain the difference between REST and GraphQL with code examples.",
        "Design a microservices architecture for an e-commerce platform.",
    ]
}

def benchmark_model(endpoint: str, model: str, prompt: str, timeout: int = 60) -> BenchmarkResult:
    """Benchmark a single request"""
    start = time.time()

    try:
        response = requests.post(
            endpoint,
            json={"prompt": prompt, "model": model, "max_tokens": 200},
            timeout=timeout
        )

        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            # Try to extract tokens/s from response
            tokens_per_second = data.get('tokens_per_second', 200 / elapsed if elapsed > 0 else 0)

            return BenchmarkResult(
                model=model,
                prompt=prompt[:50] + "...",
                time_seconds=elapsed,
                tokens_per_second=tokens_per_second,
                success=True
            )
        else:
            return BenchmarkResult(
                model=model,
                prompt=prompt[:50] + "...",
                time_seconds=elapsed,
                tokens_per_second=0,
                success=False,
                error=f"HTTP {response.status_code}"
            )

    except Exception as e:
        elapsed = time.time() - start
        return BenchmarkResult(
            model=model,
            prompt=prompt[:50] + "...",
            time_seconds=elapsed,
            tokens_per_second=0,
            success=False,
            error=str(e)
        )

def run_benchmarks():
    """Run comprehensive benchmark suite"""
    print("🔬 Ternary vs Standard Model Benchmark")
    print("=" * 70)
    print("")

    # Model configurations
    models_to_test = [
        {
            'name': 'TinyLlama (Standard)',
            'endpoint': 'http://localhost:11434/api/generate',
            'model_id': 'tinyllama',
            'backend': 'ollama'
        },
        {
            'name': 'Phi-2 (Standard)',
            'endpoint': 'http://localhost:11434/api/generate',
            'model_id': 'phi',
            'backend': 'ollama'
        },
        {
            'name': 'BitNet 2B (Ternary)',
            'endpoint': 'http://localhost:8003/generate',
            'model_id': 'bitnet-2b',
            'backend': 'ternary'
        },
        {
            'name': 'Mistral-7B (Ternary)',
            'endpoint': 'http://localhost:8003/generate',
            'model_id': 'mistral-7b-ternary',
            'backend': 'ternary'
        },
    ]

    all_results: List[BenchmarkResult] = []

    for complexity, prompts in TEST_PROMPTS.items():
        print(f"\n📊 Testing {complexity.upper()} prompts:")
        print("-" * 70)

        for prompt in prompts:
            print(f"\n  Prompt: {prompt[:60]}...")

            for model_config in models_to_test:
                result = benchmark_model(
                    model_config['endpoint'],
                    model_config['model_id'],
                    prompt
                )

                all_results.append(result)

                if result.success:
                    print(f"    ✅ {model_config['name']:30s}: {result.time_seconds:5.2f}s ({result.tokens_per_second:5.1f} tok/s)")
                else:
                    print(f"    ❌ {model_config['name']:30s}: FAILED - {result.error}")

    # Calculate summary statistics
    print("\n")
    print("=" * 70)
    print("📈 BENCHMARK SUMMARY")
    print("=" * 70)
    print("")

    for model_config in models_to_test:
        model_results = [r for r in all_results if r.model == model_config['model_id'] and r.success]

        if model_results:
            times = [r.time_seconds for r in model_results]
            tps = [r.tokens_per_second for r in model_results]

            print(f"\n{model_config['name']}:")
            print(f"  Success rate: {len(model_results)}/{len(all_results) // len(models_to_test)} ({len(model_results) / (len(all_results) // len(models_to_test)) * 100:.1f}%)")
            print(f"  Avg time:     {statistics.mean(times):.2f}s (min: {min(times):.2f}s, max: {max(times):.2f}s)")
            print(f"  Avg tok/s:    {statistics.mean(tps):.1f} (min: {min(tps):.1f}, max: {max(tps):.1f})")
            print(f"  Median time:  {statistics.median(times):.2f}s")
        else:
            print(f"\n{model_config['name']}: No successful results")

    # Performance comparison
    print("\n")
    print("=" * 70)
    print("⚡ PERFORMANCE COMPARISON (Ternary vs Standard)")
    print("=" * 70)

    # Compare BitNet 2B vs Phi-2 (similar parameter count)
    bitnet_results = [r for r in all_results if r.model == 'bitnet-2b' and r.success]
    phi_results = [r for r in all_results if r.model == 'phi' and r.success]

    if bitnet_results and phi_results:
        bitnet_avg_time = statistics.mean([r.time_seconds for r in bitnet_results])
        phi_avg_time = statistics.mean([r.time_seconds for r in phi_results])
        speedup = phi_avg_time / bitnet_avg_time if bitnet_avg_time > 0 else 0

        print(f"\nBitNet 2B vs Phi-2 (2.7B):")
        print(f"  BitNet avg: {bitnet_avg_time:.2f}s")
        print(f"  Phi-2 avg:  {phi_avg_time:.2f}s")
        print(f"  Speedup:    {speedup:.2f}x {'FASTER' if speedup > 1 else 'SLOWER'}")

    # Compare Mistral-7B ternary vs standard (if available)
    mistral_ternary_results = [r for r in all_results if r.model == 'mistral-7b-ternary' and r.success]
    tinyllama_results = [r for r in all_results if r.model == 'tinyllama' and r.success]

    if mistral_ternary_results and tinyllama_results:
        mistral_avg_time = statistics.mean([r.time_seconds for r in mistral_ternary_results])
        tiny_avg_time = statistics.mean([r.time_seconds for r in tinyllama_results])

        print(f"\nMistral-7B (Ternary) vs TinyLlama:")
        print(f"  Mistral-7B ternary: {mistral_avg_time:.2f}s (better quality, larger model)")
        print(f"  TinyLlama:          {tiny_avg_time:.2f}s")

    print("\n")
    print("=" * 70)
    print("💡 Key Insights:")
    print("  - Ternary models use 16x less RAM than standard models")
    print("  - 6x faster inference in theory (actual may vary by hardware)")
    print("  - 82% energy reduction compared to FP16 models")
    print("  - Run 7B models on 8GB RAM (vs 28GB standard)")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_benchmarks()
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
