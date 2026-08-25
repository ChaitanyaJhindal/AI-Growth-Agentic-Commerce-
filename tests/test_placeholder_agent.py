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

    # Test 5: Dynamic Context-Aware Outfit Combo Synthesis
    print("\n4. Testing Dynamic Outfit Combo Synthesis (openai/gpt-oss-20b)...")
    mock_anchor = {"name": "Puma Classic Grey Running T-Shirt", "brand": "Puma", "article_type": "Tshirts"}
    mock_pairings = [
        {"name": "Nike Tech Fleece Black Track Pants", "article_type": "Track Pants"},
        {"name": "Puma Nitro Carbon White Running Shoes", "article_type": "Sports Shoes"}
    ]
    combo_tip = agent.generate_combo_suggestion(mock_anchor, mock_pairings)
    assert combo_tip and len(combo_tip) > 10, "Failed to generate combo suggestion"
    print(f"✓ AI Stylist Combo Suggestion: \"{combo_tip}\"")

    print("\n" + "=" * 80)
    print("🎉 ALL PLACEHOLDER & STYLIST COMBO AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_placeholder_tests()
