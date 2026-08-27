import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.workflow import agent_app
from src.agents.query_agent import query_agent_node
from src.search.engine import ProductHybridSearchEngine
from src.agents.base import get_search_engine

class TestMoneyFiltersAndUpsell(unittest.TestCase):
    """
    Tests for robust money/price filter extraction, catalog price intelligence,
    and graceful upsell reasoning when requested budgets are below catalog floors.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = get_search_engine()

    def test_query_agent_price_ceiling_extraction(self):
        """Tests that Query Agent parses price ceiling 'under $50' properly."""
        state = {
            "original_query": "men running shoes under $50",
            "current_query": "men running shoes under $50",
            "conversation_history": []
        }
        res = query_agent_node(state)
        filters = res.get("filters", {})
        
        self.assertIn("price", filters)
        self.assertIn("$lte", filters["price"])
        self.assertEqual(filters["price"]["$lte"], 50.0)
        self.assertNotIn("$50", res.get("current_query", ""))

    def test_query_agent_price_range_extraction(self):
        """Tests that Query Agent parses price ranges 'between $30 and $70'."""
        state = {
            "original_query": "casual shirts between $30 and $70",
            "current_query": "casual shirts between $30 and $70",
            "conversation_history": []
        }
        res = query_agent_node(state)
        filters = res.get("filters", {})
        
        self.assertIn("price", filters)
        self.assertEqual(filters["price"].get("$gte"), 30.0)
        self.assertEqual(filters["price"].get("$lte"), 70.0)

    def test_catalog_price_bounds_inspection(self):
        """Tests calculating minimum and average price for a category in Atlas."""
        bounds = self.engine.inspect_category_price_bounds(article_type="Watches")
        self.assertGreater(bounds["min_price"], 0)
        self.assertGreaterEqual(bounds["min_price"], 70.0)
        self.assertGreater(bounds["count"], 500)

    def test_search_engine_price_gap_detection(self):
        """
        Tests that searching for a watch under $20 detects the price gap
        and retrieves entry-level watches starting at the catalog floor.
        """
        filter_dict = self.engine.build_filter(
            article_type="Watches",
            max_price=20.0
        )
        results, price_analysis = self.engine.hybrid_search_with_price_intelligence(
            query="luxury watch",
            filter_dict=filter_dict,
            limit=5
        )

        self.assertTrue(price_analysis["price_gap_detected"])
        self.assertEqual(price_analysis["requested_max_price"], 20.0)
        self.assertGreaterEqual(price_analysis["catalog_min_price"], 70.0)
        self.assertGreaterEqual(len(results), 1)
        # Verify returned products are actual watches sorted by entry-level price
        for r in results:
            self.assertEqual(r.get("article_type"), "Watches")

    def test_end_to_end_agent_pipeline_budget_reasoning(self):
        """
        End-to-end multi-agent pipeline test:
        When user asks for 'watches under $15', the pipeline validates results,
        provides a concierge explanation noting the baseline, and returns closest options.
        """
        input_state = {
            "original_query": "watches under $15",
            "current_query": "watches under $15"
        }
        config = {"configurable": {"thread_id": "test_budget_upsell_1"}}
        res = agent_app.invoke(input_state, config=config)

        self.assertFalse(res.get("needs_clarification", False))
        search_results = res.get("search_results", [])
        self.assertGreater(len(search_results), 0)

        val_res = res.get("validation_result", {})
        self.assertTrue(val_res.get("validated", False))
        explanation = val_res.get("explanation", "")
        self.assertTrue(len(explanation) > 0)
        print("\n[Validation Rationale & Budget Upsell]:", explanation)


if __name__ == "__main__":
    unittest.main()
