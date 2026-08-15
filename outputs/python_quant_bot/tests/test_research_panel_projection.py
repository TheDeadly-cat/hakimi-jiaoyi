from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.research_panel_projection import (
    RESEARCH_PANEL_PROJECTION_SCHEMA,
    build_research_panel_projection,
)


class ResearchPanelProjectionTests(unittest.TestCase):
    def test_panel_is_pure_and_neutralizes_nested_research_semantics(self) -> None:
        payload = {
            "ok": True,
            "summary": "raw research panel",
            "focus": {
                "cards": [{"tone": "up", "preferred": "偏多", "status": "READY"}],
                "checklist": [{"status": "PASS", "action": "BUY"}],
            },
            "nested": {"execution_allowed": "true"},
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(payload)

        result = build_research_panel_projection(payload)

        self.assertEqual(payload, before)
        self.assertEqual(result["projection_schema_version"], RESEARCH_PANEL_PROJECTION_SCHEMA)
        self.assertEqual(result["focus"]["cards"][0]["tone"], "flat")
        self.assertEqual(result["focus"]["cards"][0]["raw_tone"], "up")
        self.assertEqual(result["focus"]["cards"][0]["preferred"], "研究观察")
        self.assertEqual(result["focus"]["cards"][0]["status"], "研究证据已核对")
        self.assertEqual(result["focus"]["checklist"][0]["action"], "观察 / 仅研究 / 非订单")
        self.assertFalse(result["nested"]["execution_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["direction_signal_allowed"])
        self.assertIn("research_panel.focus.cards[0].tone", result["authority_sanitized_paths"])
        self.assertIn("research_panel.nested.execution_allowed", result["authority_sanitized_paths"])

    def test_invalid_payload_fails_closed(self) -> None:
        result = build_research_panel_projection(None)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertTrue(result["research_only"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_read_only_route_finishes_through_projection(self) -> None:
        server_source = (
            PROJECT_ROOT / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "json_response(self, build_research_panel_projection(",
            server_source,
        )


if __name__ == "__main__":
    unittest.main()
