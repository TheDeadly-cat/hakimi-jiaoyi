"""Actual cache/HTTP response functions with in-memory dependencies only."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any
import unittest
from unittest.mock import Mock

from hakimi_research.candle_contract import candle_is_complete
from hakimi_research.stock_candle_revision_policy import prepare_stock_candle_revision_policy
from exchange_terminal.services.corporate_action_ledger import (
    build_adjustment_evidence,
    infer_adjustment_basis,
    verify_adjustment_evidence,
)


ROOT = Path(__file__).parents[1] / "exchange_terminal"


def load_functions(relative, names, scope):
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(nodes) != len(names):
        raise AssertionError("source function missing")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)


def candle(source, close):
    return {
        "ts": 1792416600000, "date": "2026-10-19",
        "open": close - 2, "high": close + 3, "low": close - 3,
        "close": close, "volume": 34573181,
        "session": "regular", "complete": True, "source": source,
    }


class StockDeliveryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.existing = [candle("yahoo_adjusted", 343.2358)]
        self.incoming = [candle("futu", 342.94)]
        self.connection = Mock()
        self.connection.execute.return_value.fetchall.side_effect = lambda: copy.deepcopy(self.existing)
        self.scope = {
            "Any": Any, "hashlib": hashlib, "json": json, "median": median,
            "stock_meta": lambda symbol: {"symbol": symbol},
            "stock_cache_interval": lambda interval: interval.lower(),
            "clean_stock_session": lambda session: session,
            "normalize_stock_cache_candle": lambda row, symbol: dict(row),
            "ensure_stock_candle_cache_db": Mock(return_value=self.connection),
            "infer_adjustment_basis": infer_adjustment_basis,
            "build_adjustment_evidence": build_adjustment_evidence,
            "candle_is_complete": candle_is_complete,
            "prepare_stock_candle_revision_policy": prepare_stock_candle_revision_policy,
            "_COMPATIBLE_FORWARD_ADJUSTED_BASES": {
                "FORWARD_ADJUSTED_QFQ", "FORWARD_ADJUSTED_TOTAL_RETURN",
            },
        }
        load_functions("market_data/stock_candles_io.py", {
            "_canonical_hash", "prepare_stock_candle_cache_rows",
            "reconcile_stock_candle_delivery",
        }, self.scope)
        self.provider = {
            "ok": True, "source": "futu", "rows": self.incoming,
            "adjustment_basis": "FORWARD_ADJUSTED_QFQ",
            "corporate_actions": [],
            "adjustment_evidence": build_adjustment_evidence(
                symbol="AAPL", rows=self.incoming, source="futu",
                adjustment_basis="FORWARD_ADJUSTED_QFQ",
            ),
        }
        self.accepted_revision = {
            "status": "PASS", "role": "ACCEPTED_CACHE",
            "current": {"provider": "accepted_stock_cache",
                        "adjustment_basis": "FORWARD_ADJUSTED_TOTAL_RETURN"},
        }

    def prepared_payload(self):
        prepared = self.scope["prepare_stock_candle_cache_rows"](
            "AAPL", "1d", "regular", self.incoming, "futu",
        )
        return {
            **self.provider, "rows": prepared["rows"],
            "cache_vintage": {key: value for key, value in prepared.items() if key != "rows"},
            "data_revision_evidence": self.accepted_revision,
            "provider_revision_evidence": {"status": "PASS", "role": "PROVIDER_OBSERVATION"},
        }

    def reconcile(self, payload):
        return self.scope["reconcile_stock_candle_delivery"](
            payload, "AAPL", "1d", "regular", provider_payload=self.provider,
        )

    def test_retained_yahoo_row_is_not_delivered_as_futu_qfq(self):
        payload = self.prepared_payload()
        original = copy.deepcopy(payload)
        result = self.reconcile(payload)
        self.assertEqual(payload, original)
        self.assertEqual(result["rows"][0]["close"], 343.2358)
        self.assertEqual(result["rows"][0]["source"], "yahoo_adjusted")
        self.assertEqual(result["source"], "stock_sqlite_cache")
        self.assertEqual(result["origin_sources"], ["yahoo_adjusted"])
        self.assertEqual(result["adjustment_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertEqual(result["adjustment_evidence"]["source"], "yahoo_adjusted")
        self.assertEqual(result["adjustment_evidence"]["adjustment_basis"], result["adjustment_basis"])
        self.assertEqual(verify_adjustment_evidence(result["adjustment_evidence"])["status"], "PASS")
        observed = result["provider_observation"]
        self.assertEqual(observed["source"], "futu")
        self.assertEqual(observed["adjustment_basis"], "FORWARD_ADJUSTED_QFQ")
        self.assertEqual(observed["latest_row"]["close"], 342.94)
        self.assertFalse(observed["delivered_as_provider_rows"])
        self.assertIs(result["data_revision_evidence"], self.accepted_revision)
        self.assertEqual(result["provider_revision_evidence"], payload["provider_revision_evidence"])
        self.connection.commit.assert_not_called()

    def test_direct_provider_without_retained_vintage_keeps_original_identity(self):
        self.existing = []
        payload = self.prepared_payload()
        self.assertIs(self.reconcile(payload), payload)
        self.assertEqual(payload["source"], "futu")
        self.assertEqual(payload["rows"][0]["close"], 342.94)

    def test_same_provider_completed_row_is_also_a_cache_vintage(self):
        self.existing[0]["source"] = "futu"
        result = self.reconcile(self.prepared_payload())
        self.assertEqual(result["source"], "stock_sqlite_cache")
        self.assertEqual(result["origin_source"], "futu")
        self.assertEqual(result["adjustment_basis"], "FORWARD_ADJUSTED_QFQ")

    def test_new_provider_date_keeps_chain_reference_and_mixed_lineage(self):
        self.incoming.append({**self.incoming[0], "date": "2026-10-20", "ts": 1792503000000})
        result = self.reconcile(self.prepared_payload())
        self.assertEqual(result["origin_sources"], ["futu", "yahoo_adjusted"])
        self.assertEqual(result["origin_source"], "mixed")
        self.assertEqual(result["adjustment_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertTrue(result["cache_vintage"]["chain_linked"])
        self.assertEqual(result["cache_vintage"]["reference_sources"], ["yahoo_adjusted"])
        self.assertAlmostEqual(result["rows"][1]["close"], 343.2358, places=4)

    def test_missing_basis_does_not_inherit_provider_qfq(self):
        payload = self.prepared_payload()
        del payload["cache_vintage"]["adjustment_basis"]
        result = self.reconcile(payload)
        self.assertEqual(result["adjustment_basis"], "UNKNOWN")
        self.assertFalse(result["adjustment_evidence"]["backtest_eligible"])
        self.assertNotEqual(result["adjustment_evidence"]["status"], "PASS")

    def test_block_or_missing_gate_cannot_be_upgraded_by_response_correction(self):
        for gate, status in (("data_revision_evidence", "BLOCK"),
                             ("data_revision_evidence", None),
                             ("adjustment_evidence", "BLOCK")):
            with self.subTest(gate=gate, status=status):
                payload = self.prepared_payload()
                if gate == "adjustment_evidence":
                    self.provider[gate] = {**self.provider[gate], "status": status,
                                           "backtest_eligible": False}
                else:
                    payload[gate] = {"status": status} if status else {}
                result = self.reconcile(payload)
                self.assertFalse(result["adjustment_evidence"]["backtest_eligible"])
                self.assertNotEqual(result["adjustment_evidence"]["status"], "PASS")
                self.assertEqual(result["data_revision_evidence"], payload["data_revision_evidence"])

    def test_rejected_prior_gate_produces_a_verifiable_block_not_a_new_pass(self):
        for status in (None, "REVIEW", "BLOCK"):
            with self.subTest(prior_status=status):
                payload = self.prepared_payload()
                payload["data_revision_evidence"] = {} if status is None else {"status": status}
                result = self.reconcile(payload)
                evidence = result["adjustment_evidence"]
                self.assertEqual(evidence["status"], "BLOCK")
                self.assertFalse(evidence["backtest_eligible"])
                self.assertEqual(verify_adjustment_evidence(evidence)["status"], "PASS")
                self.assertEqual(result["data_revision_evidence"], payload["data_revision_evidence"])

    def test_both_prior_restrictions_survive_canonical_json_roundtrip(self):
        payload = self.prepared_payload()
        payload["data_revision_evidence"] = {"status": "BLOCK"}
        self.provider["adjustment_evidence"] = {"status": "BLOCK", "backtest_eligible": False}
        evidence = self.reconcile(payload)["adjustment_evidence"]
        reopened = json.loads(json.dumps(evidence, sort_keys=True))
        self.assertEqual(reopened["status"], "BLOCK")
        self.assertEqual(verify_adjustment_evidence(reopened)["status"], "PASS")
        self.assertEqual(len([x for x in reopened["blockers"] if x.startswith("delivery_prior_gate_not_pass:")]), 2)

    def test_prior_gate_tampering_and_unknown_shapes_fail_verification(self):
        evidence = self.reconcile(self.prepared_payload())["adjustment_evidence"]
        original = copy.deepcopy(evidence)
        evidence["delivery_prior_gates"]["accepted_cache"]["status"] = "BLOCK"
        self.assertIn("adjustment_evidence_hash_invalid", verify_adjustment_evidence(evidence)["blockers"])
        for value in (None, [], {}, {"accepted_cache": {"status": "PASS"}},
                      {"provider_adjustment": {"status": "PASS", "backtest_eligible": "true"}, "accepted_cache": {"status": "PASS"}},
                      {"provider_adjustment": {"status": "PASS", "backtest_eligible": True}, "accepted_cache": {"status": "READY"}},
                      {"provider_adjustment": {"status": "PASS", "backtest_eligible": True}, "accepted_cache": {"status": "PASS", "override": True}}):
            with self.subTest(prior_gates=value):
                forged = copy.deepcopy(original)
                forged["delivery_prior_gates"] = value
                forged["evidence_hash"] = self.scope["_canonical_hash"]({k: v for k, v in forged.items() if k != "evidence_hash"})
                audit = verify_adjustment_evidence(forged)
                self.assertEqual(audit["status"], "BLOCK")
                self.assertIn("adjustment_delivery_prior_gates_invalid", audit["blockers"])

    def test_claimed_prior_pass_never_overrides_canonical_blockers(self):
        payload = self.prepared_payload()
        payload["cache_vintage"].pop("adjustment_basis")
        evidence = self.reconcile(payload)["adjustment_evidence"]
        self.assertTrue(all(gate["status"] == "PASS" for gate in evidence["delivery_prior_gates"].values()))
        self.assertFalse(evidence["backtest_eligible"])
        forged = {**evidence, "status": "PASS", "backtest_eligible": True, "blockers": []}
        forged["evidence_hash"] = self.scope["_canonical_hash"]({k: v for k, v in forged.items() if k != "evidence_hash"})
        audit = verify_adjustment_evidence(forged)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("adjustment_declared_blockers_semantic_mismatch", audit["blockers"])

    def test_existing_provider_evidence_without_delivery_fields_is_unchanged(self):
        before = copy.deepcopy(self.provider["adjustment_evidence"])
        self.assertNotIn("delivery_prior_gates", before)
        self.assertEqual(verify_adjustment_evidence(before)["status"], "PASS")
        self.reconcile(self.prepared_payload())
        self.assertEqual(self.provider["adjustment_evidence"], before)
        self.assertEqual(verify_adjustment_evidence(before)["status"], "PASS")

    def test_relabel_does_not_bypass_canonical_time_or_completion_guards(self):
        for mutation in (lambda row: row.update(date="2026-10-20"),
                         lambda row: row.pop("complete")):
            payload = self.prepared_payload()
            mutation(payload["rows"][0])
            result = self.reconcile(payload)
            self.assertEqual(result["adjustment_evidence"]["status"], "BLOCK")
            self.assertFalse(result["adjustment_evidence"]["backtest_eligible"])
            self.assertTrue(any("stock_candle_" in item for item in result["adjustment_evidence"]["blockers"]))
            self.assertEqual(result["rows"], payload["rows"])
            self.connection.commit.assert_not_called()

    def test_force_http_path_retains_data_and_corrects_memory_response(self):
        saved = Mock(return_value=1)
        observation = Mock(return_value={"status": "PASS", "role": "PROVIDER_OBSERVATION"})
        scope = {
            **self.scope, "RUNTIME_READ_ONLY": False,
            "normalize_stock_history_session": lambda interval, session: session,
            "stock_candle_stale_warning": lambda *args: "",
            "enrich_stock_series_contract": lambda payload, *args, **kwargs: payload,
            "record_stock_revision_snapshot": observation,
            "upsert_stock_candle_cache": saved,
            "attest_stock_candle_cache": lambda *args: self.accepted_revision,
            "now_ms": lambda: 1792503000000,
            "stock_candle_cache_key": lambda *args: tuple(args),
            "STOCK_CANDLE_CACHE": {},
            "with_stock_freshness": lambda payload, *args: payload,
            "read_stock_candle_cache": Mock(side_effect=AssertionError("force must bypass memory")),
            "read_stock_persistent_candle_cache": lambda *args: None,
            "futu_status_snapshot": lambda *args: {"opend_online": True},
            "read_futu_stock_candles": lambda *args, **kwargs: self.provider,
            "stock_candle_needs_source_comparison": lambda *args: False,
        }
        load_functions("server.py", {"cache_stock_candles", "read_stock_candles"}, scope)
        original_rows = copy.deepcopy(self.incoming)
        original_cache = copy.deepcopy(self.existing)
        result = scope["read_stock_candles"]("AAPL", 30, "1d", "regular", force=True)
        self.assertEqual(result["source"], "stock_sqlite_cache")
        self.assertEqual(result["adjustment_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertEqual(result["rows"], original_cache)
        self.assertEqual(self.incoming, original_rows)
        self.assertEqual(self.existing, original_cache)
        self.assertEqual(observation.call_args.kwargs["rows"], original_rows)
        self.assertEqual(saved.call_args.args[3], original_cache)
        cached = scope["STOCK_CANDLE_CACHE"][("AAPL", "1d", "regular")]["payload"]
        self.assertEqual(cached["source"], "stock_sqlite_cache")
        self.assertEqual(cached["provider_observation"]["latest_row"]["close"], 342.94)
        self.connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
