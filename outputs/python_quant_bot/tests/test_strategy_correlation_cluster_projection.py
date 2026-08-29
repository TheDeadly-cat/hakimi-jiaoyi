from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import random
import unittest

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.strategy_correlation_cluster_gate import build_correlation_cluster_preregistration
from exchange_terminal.services.strategy_correlation_cluster_projection import (
    build_correlation_cluster_public_summary,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
    build_replayed_correlation_cluster_gate,
)


class StrategyCorrelationClusterProjectionTests(unittest.TestCase):
    def _evaluation(self, *, blocked: bool = False):
        symbols = ["AAPL", "MSFT", "TLT", "GLD"]
        base = [random.Random(5 + index).uniform(-0.01, 0.01) for index in range(60)]
        returns = {
            "AAPL": base,
            "MSFT": [value * 0.95 + random.Random(90 + index).uniform(-0.0001, 0.0001) for index, value in enumerate(base)],
            "TLT": [random.Random(190 + index).uniform(-0.01, 0.01) for index in range(60)],
            "GLD": [random.Random(290 + index).uniform(-0.01, 0.01) for index in range(60)],
        }
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "tech", "members": ["AAPL", "MSFT"]},
            {"cluster_id": "rates", "members": ["TLT"]},
            {"cluster_id": "gold", "members": ["GLD"]},
        ])
        payloads = {}
        manifests = []
        for symbol in symbols:
            price = 100.0
            rows = [{"date": date(2026, 1, 1).isoformat(), "close": price, "complete": True}]
            for index, value in enumerate(returns[symbol], start=1):
                price *= 1 + value
                rows.append({"date": (date(2026, 1, 1) + timedelta(days=index)).isoformat(), "close": price, "complete": True})
            payloads[symbol] = {"source": "frozen-fixture", "rows": rows}
            manifests.append({
                "role": "SELECTION", "symbol": symbol, "timeframe": "1D",
                "source": "frozen-fixture", "data_hash": hashlib.sha256(symbol.encode()).hexdigest(),
                "row_count": len(rows),
            })
        completed = build_correlation_completed_price_input(
            payloads, manifests, preregistration,
            cutoff_date="2026-03-02", selection_alignment_input_hash="b" * 64,
        )
        replay = build_correlation_matrix_replay(completed, preregistration)
        statuses = {symbol: "PASS" for symbol in symbols}
        if blocked:
            statuses.update({"TLT": "BLOCK", "GLD": "BLOCK"})
        cells = [
            {"strategy_id": "trend", "variant_id": "private-v1", "symbol": symbol, "lane": "RAW_EXCESS", "gate_status": status}
            for symbol, status in statuses.items()
        ]
        return build_replayed_correlation_cluster_gate(
            replay, cells, strategy_id="trend", variant_id="private-v1", lane="RAW_EXCESS",
        )

    def test_verified_pass_is_neutral_non_authorizing_and_redacted(self) -> None:
        summary = build_correlation_cluster_public_summary(self._evaluation())
        self.assertEqual(summary["status"], "DESCRIPTIVE_PASS")
        self.assertEqual(summary["source_status"], "VERIFIED_LOCAL_REPLAY")
        self.assertEqual(summary["cluster_count"], 3)
        self.assertEqual(summary["passing_cluster_count"], 3)
        self.assertFalse(summary["full_manifest_reverified"])
        self.assertFalse(summary["preregistered_cutoff_bound"])
        self.assertFalse(summary["formal_registry_bound"])
        self.assertFalse(summary["current_report_schema_bound"])
        self.assertEqual(
            summary["next_evidence_required"],
            "FORMAL_PROTOCOL_BINDING_AND_NEW_REPORT_SCHEMA",
        )
        self.assertFalse(summary["current_admission_allowed"])
        self.assertFalse(summary["paper_authorized"])
        self.assertEqual(authority_violations(summary), [])
        serialized = json.dumps(summary)
        for secret in ("AAPL", "MSFT", "private-v1", "tech", "preregistration_hash", "matrix_hash"):
            self.assertNotIn(secret, serialized)

    def test_verified_negative_result_preserves_counts_without_raw_blockers(self) -> None:
        summary = build_correlation_cluster_public_summary(self._evaluation(blocked=True))
        self.assertEqual(summary["status"], "DESCRIPTIVE_BLOCK")
        self.assertEqual(summary["first_gap_category"], "INDEPENDENT_CLUSTER_VOTE_GAP")
        self.assertEqual(summary["passing_cluster_count"], 1)
        self.assertEqual(summary["required_cluster_votes"], 2)
        self.assertNotIn("blockers", summary)

    def test_tamper_returns_unknown_and_hides_all_counts(self) -> None:
        evaluation = self._evaluation()
        evaluation["gate"]["passing_cluster_count"] = 999
        summary = build_correlation_cluster_public_summary(evaluation)
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["first_gap_category"], "INPUT_INTEGRITY")
        self.assertIsNone(summary["cluster_count"])
        self.assertIsNone(summary["pair_count"])

    def test_authority_alias_returns_unknown_even_if_outer_hash_is_resealed(self) -> None:
        evaluation = self._evaluation()
        evaluation["selection_cells"][0]["paperReady"] = True
        body = {key: value for key, value in evaluation.items() if key != "evaluation_hash"}
        raw = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        evaluation["evaluation_hash"] = hashlib.sha256(raw.encode()).hexdigest()
        summary = build_correlation_cluster_public_summary(evaluation)
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
