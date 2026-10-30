"""Saved-file candidate routing, without market calls or economic runs."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_candidate_service import strategy_candidates
from tests import test_terminal_research as fixtures
from tests.test_terminal_strategy_candidates import CATALOG_ORDER, native, spec


class CandidateServiceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TerminalResearchTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.fixture.catalog = [{"id": identity, "name": identity, "params": spec(identity)["params"],
                                 "capability": {"new_research_allowed": True, "backtest_supported": True}}
                                for identity in CATALOG_ORDER]
        self.record = native()
        self.path = self.service.workspace / "terminal-inputs" / (self.record["id"] + ".json")
        self.service._write(self.path, self.record)
        self.payload = {"input_id": self.record["id"], "position_context": {"has_position": False}}

    def inventory(self):
        return {str(path): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in self.service.workspace.rglob("*") if path.is_file()}

    def test_actual_saved_input_yields_nine_bound_rules_without_writes_or_run(self):
        before = self.inventory()
        result = strategy_candidates(self.service, self.payload)
        rows = [row for group in result["groups"] for row in group["items"]]
        self.assertEqual(set(row["strategy_id"] for row in rows), set(CATALOG_ORDER))
        self.assertTrue(all(row["input_id"] == self.record["id"] for row in rows))
        self.assertTrue(all(row["freshness"]["immediate_execution_eligible"] is False for row in rows))
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.fixture.runner.call_count, 0)
        self.assertFalse(any(call[0] == "mutate" for call in self.fixture.core.calls))

    def test_parameter_preview_is_one_rule_and_preserves_original_input(self):
        before = self.inventory()
        result = strategy_candidates(self.service, {**self.payload, "strategy_id": "dual_ma",
                                                    "strategy_params": {"fast_window": 7, "slow_window": 30}})
        rows = [row for group in result["groups"] for row in group["items"]]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strategy_params"]["fast_window"], 7)
        self.assertEqual(rows[0]["factors"][0]["window"], [7, 30])
        self.assertEqual(self.inventory(), before)

    def test_client_cannot_supply_rule_identity_reports_paths_or_fake_clock(self):
        for extra in ({"fingerprint": "a" * 64}, {"engine_id": "forged"}, {"observed_at": "2030-01-01T00:00:00Z"},
                      {"report": {}}, {"path": "../history"}, {"strategy_params": {"fast_window": 5}},
                      {"strategy_id": "grid"}, {"position_context": {"has_position": "false"}}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                strategy_candidates(self.service, {**self.payload, **extra})

    def test_tampered_saved_input_is_not_repaired_or_diagnosed(self):
        document = deepcopy(self.record)
        document["rows"][-1]["close"] += 10
        self.path.write_text(json.dumps(document), encoding="utf-8")
        before = self.inventory()
        with self.assertRaises(ValueError):
            strategy_candidates(self.service, self.payload)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.fixture.runner.call_count, 0)

    def test_source_change_during_read_is_refused(self):
        with patch("exchange_terminal.services.terminal_candidate_service._engine_source_identity") as sources:
            original = spec("dual_ma")["engine_source_identity"]
            sources.side_effect = [original, {**original, "strategy_signals.py": "b" * 64}]
            with self.assertRaisesRegex(ValueError, "source_changed"):
                strategy_candidates(self.service, self.payload)

    def test_service_read_route_has_same_read_only_contract(self):
        before = self.inventory()
        result = self.service.read("terminal_strategy_candidates", json.dumps(self.payload))
        self.assertTrue(result["read_only"])
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.fixture.runner.call_count, 0)


if __name__ == "__main__":
    unittest.main()
