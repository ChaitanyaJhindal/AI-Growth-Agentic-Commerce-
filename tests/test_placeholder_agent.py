import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.placeholder_agent import get_placeholder_agent

def run_placeholder_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  TESTING GEN-Z DYNAMIC PLACEHOLDER AGENT (openai/gpt-oss-20b)")
    print("=" * 80)

    agent = get_placeholder_agent()
    print(f"\n1. Initialized Placeholder Agent with model: {agent.model}")

    # Test 1: Immediate next prompt rotation
    prompt1 = agent.get_next_prompt()
    prompt2 = agent.get_next_prompt()
    assert prompt1 and isinstance(prompt1, str), "Failed to get prompt 1"
    assert prompt2 and isinstance(prompt2, str), "Failed to get prompt 2"
    print(f"✓ Prompt 1: \"{prompt1}\"")
    print(f"✓ Prompt 2: \"{prompt2}\"")

    # Test 2: Token Streaming Generator
    tokens = list(agent.stream_tokens(prompt1[:10]))
    assert len(tokens) == 10, "Streaming tokens length mismatch"
    print(f"✓ Token Streaming verified: {''.join(tokens)}")

    # Test 3: Dynamic Pipeline Steps
    print("\n2. Testing Dynamic Pipeline Steps Generation...")
    pipeline_steps = agent.get_dynamic_pipeline_steps()
    assert len(pipeline_steps) == 5, f"Expected 5 steps, got {len(pipeline_steps)}"
    print(f"✓ Dynamic Pipeline Steps ({len(pipeline_steps)} steps loaded):")
    for s in pipeline_steps:
        print(f"   [{s['step']}] {s['agent']}: {s['thought']}")

    # Test 4: Fresh Batch Generation via openai/gpt-oss-20b
    print("\n3. Calling Groq (openai/gpt-oss-20b) for fresh Gen-Z batch...")
    batch = agent.generate_fresh_batch(count=3)
    assert len(batch) >= 1, "Failed to generate batch"
    print(f"✓ Fresh batch generated ({len(batch)} items):")
    for i, p in enumerate(batch, 1):
        print(f"   [{i}] {p}")

    print("\n" + "=" * 80)
    print("🎉 ALL PLACEHOLDER & PROGRESS AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_placeholder_tests()
