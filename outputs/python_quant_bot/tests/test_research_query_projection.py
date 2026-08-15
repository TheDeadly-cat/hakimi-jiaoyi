from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.research_query_projection import (
    build_research_context_projection,
    build_research_summaries_projection,
)


class ResearchQueryProjectionTests(unittest.TestCase):
    def test_context_projection_is_pure_and_keeps_authority_at_the_envelope(self) -> None:
        contract = {
            "name": "ResearchBrief",
            "version": "1.1",
            "live_order_allowed": True,
        }
        market = {
            "symbol": "BTC-USDT",
            "snapshot_id": "snapshot-1",
            "live_order_allowed": True,
        }
        summaries = [{"summary_id": "summary-1", "live_order_allowed": True}]
        before = copy.deepcopy((contract, market, summaries))

        result = build_research_context_projection(
            contract=contract,
            market=market,
            research_summaries=summaries,
        )

        self.assertEqual((contract, market, summaries), before)
        self.assertEqual(
            set(result),
            {"ok", "contract", "market", "research_summaries", "live_order_allowed", "read_only"},
        )
        self.assertEqual(result["contract"], contract)
        self.assertEqual(result["market"], market)
        self.assertEqual(result["research_summaries"], summaries)
        self.assertIs(result["read_only"], True)
        self.assertIs(result["live_order_allowed"], False)

    def test_summary_projection_is_pure_and_preserves_the_existing_shape(self) -> None:
        schema = {
            "name": "ResearchBrief",
            "supported_versions": ["1.0", "1.1"],
            "contract_hash": "contract-hash",
            "live_order_allowed": True,
        }
        summaries = [{
            "summary_id": "summary-1",
            "research_only": True,
            "live_order_allowed": True,
        }]
        before = copy.deepcopy((schema, summaries))

        result = build_research_summaries_projection(
            schema=schema,
            summaries=summaries,
        )

        self.assertEqual((schema, summaries), before)
        self.assertEqual(
            set(result),
            {"ok", "schema", "summaries", "live_order_allowed", "read_only"},
        )
        self.assertEqual(result["schema"], schema)
        self.assertEqual(result["summaries"], summaries)
        self.assertIs(result["read_only"], True)
        self.assertIs(result["live_order_allowed"], False)


if __name__ == "__main__":
    unittest.main()
