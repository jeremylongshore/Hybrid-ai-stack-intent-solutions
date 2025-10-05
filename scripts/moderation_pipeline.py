#!/usr/bin/env python3
"""
Content Moderation Pipeline - Example Use Case

Demonstrates how using local models for initial classification can reduce costs
by 90%+ compared to cloud-only approaches.

Cost Comparison:
- Cloud Only:  1000 posts × $0.015/analysis = $15.00
- Hybrid:      950 safe (local) + 50 flagged (cloud) = $0.75
  Savings: $14.25 (95% reduction)
"""

import sys
import os
from typing import Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from smart_router import SmartRouter

class ContentModerator:
    """
    Two-stage content moderation pipeline:
    1. Local model (TinyLlama) for initial classification
    2. Cloud model (Claude) only for flagged content
    """

    def __init__(self):
        self.router = SmartRouter()
        self.stats = {
            'total_processed': 0,
            'local_safe': 0,
            'cloud_reviewed': 0,
            'total_cost': 0.0
        }

    def classify_content(self, content: str) -> Tuple[str, str, float]:
        """
        Quick classification using local model
        Returns: (classification, reasoning, cost)
        """
        prompt = f"""Classify this content as SAFE or FLAGGED.

Content: {content}

Respond with ONLY one word: SAFE or FLAGGED
"""
        # Force TinyLlama for fast classification
        result = self.router.execute_ollama_request('tinyllama', prompt)

        classification = result['response'].strip().upper()
        return classification, "Fast local classification", 0.0

    def deep_review(self, content: str) -> Dict:
        """
        Detailed review using Claude for flagged content
        """
        prompt = f"""Perform a detailed content moderation review.

Content: {content}

Provide:
1. Safety classification (SAFE/UNSAFE)
2. Specific issues if any (harassment, hate speech, violence, etc.)
3. Severity level (LOW/MEDIUM/HIGH)
4. Recommended action (APPROVE/REVIEW/REJECT)

Be thorough and explain your reasoning.
"""
        result = self.router.execute_claude_request(prompt)

        self.stats['total_cost'] += result.get('cost', 0)

        return {
            'review': result['response'],
            'cost': result.get('cost', 0),
            'model': 'claude-sonnet'
        }

    def moderate(self, content: str) -> Dict:
        """
        Full moderation pipeline
        """
        self.stats['total_processed'] += 1

        # Stage 1: Quick local classification
        classification, reasoning, cost = self.classify_content(content)

        if 'SAFE' in classification:
            # Content appears safe - no need for expensive review
            self.stats['local_safe'] += 1
            return {
                'status': 'approved',
                'stage': 'local_classification',
                'cost': cost,
                'reasoning': 'Passed initial safety check'
            }
        else:
            # Flagged content - requires detailed review
            self.stats['cloud_reviewed'] += 1
            review = self.deep_review(content)

            return {
                'status': 'needs_review',
                'stage': 'cloud_review',
                'cost': review['cost'],
                'review': review['review']
            }

    def get_cost_savings(self) -> Dict:
        """Calculate cost savings vs cloud-only approach"""
        # Cloud-only cost: all requests to Claude
        cloud_only_cost = self.stats['total_processed'] * 0.015

        # Hybrid cost: only flagged content to Claude
        hybrid_cost = self.stats['total_cost']

        savings = cloud_only_cost - hybrid_cost
        savings_pct = (savings / cloud_only_cost * 100) if cloud_only_cost > 0 else 0

        return {
            'total_processed': self.stats['total_processed'],
            'local_safe': self.stats['local_safe'],
            'cloud_reviewed': self.stats['cloud_reviewed'],
            'cloud_only_cost': cloud_only_cost,
            'hybrid_cost': hybrid_cost,
            'savings': savings,
            'savings_percent': savings_pct
        }

    def print_summary(self):
        """Print moderation summary"""
        summary = self.get_cost_savings()

        print("\n" + "="*60)
        print("CONTENT MODERATION SUMMARY")
        print("="*60)
        print(f"Total Posts Processed: {summary['total_processed']}")
        print(f"   Safe (local):      {summary['local_safe']}")
        print(f"    Flagged (cloud):   {summary['cloud_reviewed']}")
        print()
        print("COST COMPARISON:")
        print(f"  Cloud Only:  ${summary['cloud_only_cost']:.4f}")
        print(f"  Hybrid:      ${summary['hybrid_cost']:.4f}")
        print(f"  Savings:     ${summary['savings']:.4f} ({summary['savings_percent']:.1f}%)")
        print("="*60 + "\n")


def demo():
    """Demonstration of moderation pipeline"""

    moderator = ContentModerator()

    # Sample content to moderate
    test_content = [
        "Great product! Highly recommend it.",
        "Thanks for the helpful tutorial.",
        "Looking forward to the next update!",
        "This feature is exactly what I needed.",
        "Excellent customer service experience.",
        # This one will likely be flagged for review
        "I hate this stupid product and everyone who uses it!!!",
    ]

    print("\nContent Moderation Pipeline Demo")
    print("="*60)

    for i, content in enumerate(test_content, 1):
        print(f"\n[{i}/{len(test_content)}] Processing: {content[:50]}...")

        result = moderator.moderate(content)

        print(f"  Status: {result['status']}")
        print(f"  Stage: {result['stage']}")
        print(f"  Cost: ${result['cost']:.6f}")

        if result['status'] == 'needs_review':
            print(f"  Review Required!")

    # Print final summary
    moderator.print_summary()

    # Example: Process 1000 posts
    print("\nScaling Example: 1000 Posts")
    print("-" * 60)
    print("Assuming 95% safe content, 5% flagged:")
    print()
    print("  Cloud Only Approach:")
    print("    1000 posts × $0.015 = $15.00")
    print()
    print("  Hybrid Approach:")
    print("    950 safe (local) =  $0.00")
    print("    50 flagged (cloud) = $0.75")
    print("    Total = $0.75")
    print()
    print("  =° Savings: $14.25 (95% reduction)")
    print("="*60)


if __name__ == '__main__':
    demo()
