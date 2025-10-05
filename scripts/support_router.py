#!/usr/bin/env python3
"""
Customer Support Router - Example Use Case

Demonstrates intelligent routing for customer support queries.
Simple FAQ-style questions handled locally, complex issues escalated to Claude.

Cost Comparison (10,000 queries/month):
- Cloud Only:  10,000 × $0.01 avg = $100/month
- Hybrid:      7,000 local + 3,000 cloud = $30/month
  Savings: $70/month (70% reduction)
"""

import sys
import os
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from smart_router import SmartRouter

class SupportRouter:
    """
    Intelligent customer support routing system
    """

    # Common FAQ patterns that can be handled locally
    FAQ_KEYWORDS = [
        'hours', 'open', 'closed', 'location', 'address',
        'shipping', 'delivery', 'tracking',
        'return', 'refund', 'exchange',
        'password', 'reset', 'login',
        'price', 'cost', 'discount',
        'account', 'cancel', 'unsubscribe'
    ]

    def __init__(self):
        self.router = SmartRouter()
        self.stats = {
            'total_queries': 0,
            'faq_handled': 0,
            'escalated': 0,
            'total_cost': 0.0
        }

        # Simple FAQ knowledge base (in production, this would be larger)
        self.faq_db = {
            'hours': "We're open Monday-Friday 9 AM - 6 PM EST",
            'shipping': "Standard shipping takes 3-5 business days. Free over $50.",
            'returns': "30-day return policy. Items must be unused with tags.",
            'password': "Click 'Forgot Password' on the login page to reset.",
            'pricing': "Check our pricing page for current rates and discounts."
        }

    def is_simple_query(self, query: str) -> bool:
        """Check if query matches FAQ patterns"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.FAQ_KEYWORDS)

    def handle_faq(self, query: str) -> Dict:
        """Handle FAQ using local model"""
        self.stats['faq_handled'] += 1

        # Build context from FAQ database
        faq_context = "\n".join([f"Q: {k} - A: {v}" for k, v in self.faq_db.items()])

        prompt = f"""You are a helpful customer support assistant.

FAQ Knowledge Base:
{faq_context}

Customer Question: {query}

Provide a concise, helpful answer based on the FAQ knowledge base.
If the question isn't covered, say "I need to escalate this to a specialist."
"""
        # Use Phi-2 for better FAQ handling
        result = self.router.execute_ollama_request('phi2', prompt)

        return {
            'answer': result['response'],
            'handled_by': 'local_faq',
            'model': 'phi2',
            'cost': 0.0,
            'confidence': 'high' if not 'escalate' in result['response'].lower() else 'low'
        }

    def escalate_to_expert(self, query: str, context: str = "") -> Dict:
        """Escalate complex query to Claude"""
        self.stats['escalated'] += 1

        prompt = f"""You are an expert customer support specialist.

Customer Question: {query}

{f"Previous Context: {context}" if context else ""}

Provide a detailed, empathetic, and helpful response.
Address all aspects of the customer's concern.
Offer specific solutions or next steps.
"""
        result = self.router.execute_claude_request(prompt)

        self.stats['total_cost'] += result.get('cost', 0)

        return {
            'answer': result['response'],
            'handled_by': 'expert_escalation',
            'model': 'claude-sonnet',
            'cost': result.get('cost', 0),
            'confidence': 'expert'
        }

    def process_query(self, query: str) -> Dict:
        """Main query processing pipeline"""
        self.stats['total_queries'] += 1

        # Step 1: Check if it's a simple FAQ
        if self.is_simple_query(query):
            result = self.handle_faq(query)

            # Check if FAQ handler is confident
            if result['confidence'] == 'high':
                return result
            else:
                # FAQ handler not confident, escalate
                return self.escalate_to_expert(query, result['answer'])
        else:
            # Complex query - go straight to expert
            return self.escalate_to_expert(query)

    def get_performance_stats(self) -> Dict:
        """Calculate performance and cost metrics"""
        total = self.stats['total_queries']
        if total == 0:
            return {}

        # Cloud-only cost estimate
        cloud_only_cost = total * 0.01  # $0.01 average per query

        # Hybrid cost (only escalations)
        hybrid_cost = self.stats['total_cost']

        savings = cloud_only_cost - hybrid_cost
        savings_pct = (savings / cloud_only_cost * 100) if cloud_only_cost > 0 else 0

        return {
            'total_queries': total,
            'faq_handled': self.stats['faq_handled'],
            'escalated': self.stats['escalated'],
            'faq_percentage': (self.stats['faq_handled'] / total * 100),
            'cloud_only_cost': cloud_only_cost,
            'hybrid_cost': hybrid_cost,
            'savings': savings,
            'savings_percent': savings_pct
        }

    def print_summary(self):
        """Print performance summary"""
        stats = self.get_performance_stats()

        if not stats:
            print("No queries processed yet")
            return

        print("\n" + "="*60)
        print("CUSTOMER SUPPORT ROUTER SUMMARY")
        print("="*60)
        print(f"Total Queries: {stats['total_queries']}")
        print(f"   Handled by FAQ (local):  {stats['faq_handled']} ({stats['faq_percentage']:.1f}%)")
        print(f"   Escalated to Expert:     {stats['escalated']} ({100-stats['faq_percentage']:.1f}%)")
        print()
        print("COST COMPARISON:")
        print(f"  Cloud Only:  ${stats['cloud_only_cost']:.4f}")
        print(f"  Hybrid:      ${stats['hybrid_cost']:.4f}")
        print(f"  Savings:     ${stats['savings']:.4f} ({stats['savings_percent']:.1f}%)")
        print("="*60 + "\n")


def demo():
    """Demonstration of support router"""

    router = SupportRouter()

    # Sample support queries
    queries = [
        "What are your business hours?",
        "How long does shipping take?",
        "I want to return a product",
        "How do I reset my password?",
        "What are your prices?",
        # Complex queries that need escalation
        "I ordered product X but received product Y, and now the original item is out of stock. What are my options?",
        "I'm experiencing a technical issue where the app crashes when I try to upload photos on iOS 17.",
    ]

    print("\nCustomer Support Router Demo")
    print("="*60)

    for i, query in enumerate(queries, 1):
        print(f"\n[Query {i}] {query}")
        print("-" * 60)

        result = router.process_query(query)

        print(f"Handled by: {result['handled_by']}")
        print(f"Model: {result['model']}")
        print(f"Cost: ${result['cost']:.6f}")
        print(f"Confidence: {result['confidence']}")
        print(f"\nResponse: {result['answer'][:200]}...")

    # Print summary
    router.print_summary()

    # Scaling example
    print("\nScaling Example: 10,000 Queries/Month")
    print("-" * 60)
    print("Assuming 70% FAQ, 30% complex:")
    print()
    print("  Cloud Only Approach:")
    print("    10,000 queries × $0.01 = $100.00/month")
    print()
    print("  Hybrid Approach:")
    print("    7,000 FAQ (local) =      $0.00")
    print("    3,000 complex (cloud) = $30.00")
    print("    Total = $30.00/month")
    print()
    print("  =° Savings: $70.00/month (70% reduction)")
    print("="*60)


if __name__ == '__main__':
    demo()
