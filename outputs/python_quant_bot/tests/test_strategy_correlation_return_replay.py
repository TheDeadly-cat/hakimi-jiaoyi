from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import math
import random
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
    build_replayed_correlation_cluster_gate,
    verify_correlation_completed_price_input,
    verify_correlation_matrix_replay,
    verify_replayed_correlation_cluster_gate,
)


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StrategyCorrelationReturnReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        base_rng = random.Random(7)
        base = [base_rng.uniform(-0.012, 0.012) for _ in range(60)]
        tech_noise = [random.Random(17 + index).uniform(-0.0002, 0.0002) for index in range(60)]
        self.returns = {
            "AAPL": base,
            "MSFT": [value * 0.95 + tech_noise[index] for index, value in enumerate(base)],
            "NVDA": [value * 1.05 - tech_noise[index] for index, value in enumerate(base)],
            "TLT": [random.Random(100 + index).uniform(-0.012, 0.012) for index in range(60)],
            "GLD": [random.Random(200 + index).uniform(-0.012, 0.012) for index in range(60)],
        }
        self.preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "mega_cap_tech", "members": ["AAPL", "MSFT", "NVDA"]},
            {"cluster_id": "rates", "members": ["TLT"]},
            {"cluster_id": "gold", "members": ["GLD"]},
        ])

    @staticmethod
    def _price_rows(returns: list[float], *, start: date = date(2026, 1, 1)) -> list[dict[str, object]]:
        price = 100.0
        rows: list[dict[str, object]] = [{"date": start.isoformat(), "close": price, "complete": True}]
        for index, value in enumerate(returns, start=1):
            price *= 1.0 + value
            rows.append({"date": (start + timedelta(days=index)).isoformat(), "close": price, "complete": True})
        return rows

    def _sources(self, returns: dict[str, list[float]] | None = None):
        values = returns or self.returns
        payloads = {}
        manifests = []
        for symbol, series in values.items():
            rows = self._price_rows(series)
            payloads[symbol] = {"source": "frozen-fixture", "rows": rows}
            manifests.append({
                "role": "SELECTION",
                "symbol": symbol,
                "timeframe": "1D",
                "source": "frozen-fixture",
                "data_hash": hashlib.sha256(symbol.encode("ascii")).hexdigest(),
                "row_count": len(rows),
            })
        return payloads, manifests

    def _input(self, returns: dict[str, list[float]] | None = None, preregistration=None):
        payloads, manifests = self._sources(returns)
        return build_correlation_completed_price_input(
            payloads,
            manifests,
            preregistration or self.preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="a" * 64,
        )

    @staticmethod
    def _cells(statuses: dict[str, str]):
        return [
            {"strategy_id": "trend", "variant_id": "fixed-v1", "symbol": symbol, "lane": "RAW_EXCESS", "gate_status": status}
            for symbol, status in statuses.items()
        ]

    def test_price_replay_recomputes_matrix_and_collapses_symbol_majority(self) -> None:
        completed = self._input()
        replay = build_correlation_matrix_replay(completed, self.preregistration)
        result = build_replayed_correlation_cluster_gate(
            replay,
            self._cells({"AAPL": "PASS", "MSFT": "PASS", "NVDA": "PASS", "TLT": "BLOCK", "GLD": "BLOCK"}),
            strategy_id="trend",
            variant_id="fixed-v1",
            lane="RAW_EXCESS",
        )
        self.assertEqual(verify_correlation_completed_price_input(completed, preregistration=self.preregistration)["status"], "PASS")
        self.assertEqual(verify_correlation_matrix_replay(replay)["status"], "PASS")
        self.assertEqual(verify_replayed_correlation_cluster_gate(result)["status"], "PASS")
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["gate"]["passing_cluster_count"], 1)
        self.assertEqual(result["gate"]["required_cluster_votes"], 2)

    def test_coherently_resealed_self_reported_matrix_cannot_replace_replay(self) -> None:
        replay = build_correlation_matrix_replay(self._input(), self.preregistration)
        tampered = deepcopy(replay)
        tampered["correlation_matrix"]["pairs"][0]["pearson_correlation"] = 0.0
        matrix_body = {key: value for key, value in tampered["correlation_matrix"].items() if key != "matrix_hash"}
        tampered["correlation_matrix"]["matrix_hash"] = _canonical_hash(matrix_body)
        replay_body = {key: value for key, value in tampered.items() if key != "replay_hash"}
        tampered["replay_hash"] = _canonical_hash(replay_body)
        check = verify_correlation_matrix_replay(tampered)
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("correlation_replay_semantic_mismatch", check["blockers"])

    def test_incomplete_or_non_native_price_rows_fail_closed(self) -> None:
        payloads, manifests = self._sources()
        payloads["AAPL"]["rows"][0]["complete"] = False
        with self.assertRaisesRegex(ValueError, "rows_insufficient"):
            build_correlation_completed_price_input(
                payloads, manifests, self.preregistration,
                cutoff_date="2026-03-02", selection_alignment_input_hash="a" * 64,
            )
        for invalid in (True, "100", float("nan")):
            payloads, manifests = self._sources()
            payloads["AAPL"]["rows"][1]["close"] = invalid
            with self.subTest(invalid=repr(invalid)), self.assertRaises(ValueError):
                build_correlation_completed_price_input(
                    payloads, manifests, self.preregistration,
                    cutoff_date="2026-03-02", selection_alignment_input_hash="a" * 64,
                )

    def test_cutoff_excludes_future_completed_rows(self) -> None:
        payloads, manifests = self._sources()
        for manifest in manifests:
            symbol = manifest["symbol"]
            payloads[symbol]["rows"].append({"date": "2026-03-03", "close": 999.0, "complete": True})
            manifest["row_count"] += 1
        completed = build_correlation_completed_price_input(
            payloads, manifests, self.preregistration,
            cutoff_date="2026-03-02", selection_alignment_input_hash="a" * 64,
        )
        self.assertTrue(all(item["last_date"] == "2026-03-02" for item in completed["datasets"]))
        self.assertTrue(all(item["price_rows"][-1]["close"] != 999.0 for item in completed["datasets"]))

    def test_negative_cross_cluster_replay_blocks_topology(self) -> None:
        base = self.returns["AAPL"]
        split_returns = {"AAPL": base, "MSFT": [-value for value in base], "GLD": self.returns["GLD"]}
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "a", "members": ["AAPL"]},
            {"cluster_id": "b", "members": ["MSFT"]},
            {"cluster_id": "c", "members": ["GLD"]},
        ])
        replay = build_correlation_matrix_replay(self._input(split_returns, preregistration), preregistration)
        result = build_replayed_correlation_cluster_gate(
            replay,
            self._cells({"AAPL": "PASS", "MSFT": "PASS", "GLD": "PASS"}),
            strategy_id="trend", variant_id="fixed-v1", lane="RAW_EXCESS",
        )
        self.assertEqual(result["gate"]["first_blocking_tier"], "TOPOLOGY")
        self.assertLess(result["gate"]["cross_cluster_conflicts"][0]["pearson_correlation"], -0.99)

    def test_zero_variance_cannot_be_reported_as_zero_correlation(self) -> None:
        constant = {symbol: [0.001] * 60 for symbol in self.returns}
        completed = self._input(constant)
        with self.assertRaisesRegex(ValueError, "variance_zero"):
            build_correlation_matrix_replay(completed, self.preregistration)

    def test_nested_authority_alias_invalidates_replayed_gate(self) -> None:
        replay = build_correlation_matrix_replay(self._input(), self.preregistration)
        result = build_replayed_correlation_cluster_gate(
            replay,
            self._cells({symbol: "PASS" for symbol in self.returns}),
            strategy_id="trend", variant_id="fixed-v1", lane="RAW_EXCESS",
        )
        result["matrix_replay"]["liveOrderAllowed"] = True
        body = {key: value for key, value in result.items() if key != "evaluation_hash"}
        result["evaluation_hash"] = _canonical_hash(body)
        check = verify_replayed_correlation_cluster_gate(result)
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("execution_authority_invalid", check["blockers"])


if __name__ == "__main__":
    unittest.main()
