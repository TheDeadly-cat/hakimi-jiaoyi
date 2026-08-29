from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import random
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_common_support_derivation_receipt_v1 import (
    MAXIMUM_COMMON_PRICE_ROWS,
    MINIMUM_COMMON_PRICE_ROWS,
    build_correlation_common_support_derivation_receipt_v1,
    evaluate_correlation_common_support_derived_gate_v1,
    verify_correlation_common_support_derivation_receipt_v1,
    verify_correlation_common_support_derived_gate_v1,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
    verify_correlation_matrix_replay,
)


def _canonical_hash(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StrategyCorrelationCommonSupportDerivationReceiptV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = ["AAA", "BBB", "CCC"]
        self.preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "alpha", "members": ["AAA"]},
            {"cluster_id": "beta", "members": ["BBB"]},
            {"cluster_id": "gamma", "members": ["CCC"]},
        ])
        self.common_dates = self.dates(60)
        self.returns = {
            symbol: [
                random.Random((index + 1) * seed).uniform(-0.012, 0.012)
                for index in range(60)
            ]
            for seed, symbol in enumerate(self.symbols, start=101)
        }

    @staticmethod
    def dates(count: int, *, offset: int = 0) -> list[str]:
        start = date(2026, 1, 1) + timedelta(days=offset)
        return [(start + timedelta(days=index)).isoformat() for index in range(count)]

    def replay(
        self,
        returns: dict[str, list[float]] | None = None,
        return_dates: dict[str, list[str]] | None = None,
    ) -> dict[str, object]:
        values = returns or self.returns
        date_values = return_dates or {
            symbol: self.common_dates for symbol in self.symbols
        }
        earliest = min(item for items in date_values.values() for item in items)
        initial_date = (date.fromisoformat(earliest) - timedelta(days=1)).isoformat()
        cutoff_date = max(item for items in date_values.values() for item in items)
        payloads = {}
        manifests = []
        for symbol in self.symbols:
            series = values[symbol]
            labels = sorted(date_values[symbol])
            self.assertEqual(len(series), len(labels))
            price = 100.0
            rows: list[dict[str, object]] = [
                {"date": initial_date, "close": price, "complete": True}
            ]
            for label, value in zip(labels, series):
                price *= 1.0 + value
                rows.append({"date": label, "close": price, "complete": True})
            payloads[symbol] = {"source": "frozen-fixture", "rows": rows}
            manifests.append({
                "role": "SELECTION",
                "symbol": symbol,
                "timeframe": "1D",
                "source": "frozen-fixture",
                "data_hash": hashlib.sha256(
                    (symbol + "|" + "|".join(labels)).encode("ascii")
                ).hexdigest(),
                "row_count": len(rows),
            })
        completed = build_correlation_completed_price_input(
            payloads,
            manifests,
            self.preregistration,
            cutoff_date=cutoff_date,
            selection_alignment_input_hash="a" * 64,
        )
        return build_correlation_matrix_replay(completed, self.preregistration)

    def cells(self, statuses: dict[str, str] | None = None) -> list[dict[str, str]]:
        values = statuses or {symbol: "PASS" for symbol in self.symbols}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "fixed-v2",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in values.items()
        ]

    def evaluate(
        self,
        replay: dict[str, object],
        receipt: dict[str, object] | None = None,
        cells: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        source_receipt = receipt or build_correlation_common_support_derivation_receipt_v1(replay)
        return evaluate_correlation_common_support_derived_gate_v1(
            source_receipt,
            replay,
            cells or self.cells(),
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )

    def test_pairwise_40_global_20_gap_blocks_derivation(self) -> None:
        groups = {
            name: self.dates(20, offset=offset)
            for name, offset in (("T", 0), ("AB", 20), ("AC", 40), ("BC", 60))
        }
        support = {
            "AAA": sorted(groups["T"] + groups["AB"] + groups["AC"]),
            "BBB": sorted(groups["T"] + groups["AB"] + groups["BC"]),
            "CCC": sorted(groups["T"] + groups["AC"] + groups["BC"]),
        }
        replay = self.replay(return_dates=support)
        self.assertEqual(verify_correlation_matrix_replay(replay)["status"], "PASS")
        self.assertEqual(
            [pair["overlap_observations"] for pair in replay["correlation_matrix"]["pairs"]],
            [40, 40, 40],
        )
        self.assertEqual(len(set.intersection(*(set(value) for value in support.values()))), 20)
        with self.assertRaisesRegex(ValueError, "common_price_rows_insufficient"):
            build_correlation_common_support_derivation_receipt_v1(replay)

    def test_exact_minimum_common_support_passes(self) -> None:
        common = self.dates(40)
        support = {
            symbol: sorted(common + self.dates(20, offset=100 + index * 20))
            for index, symbol in enumerate(self.symbols)
        }
        replay = self.replay(return_dates=support)
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        self.assertEqual(receipt["common_price_row_count"], MINIMUM_COMMON_PRICE_ROWS)
        self.assertEqual(receipt["common_observation_count"], 40)

    def test_receipt_uses_maximum_shared_window(self) -> None:
        receipt = build_correlation_common_support_derivation_receipt_v1(self.replay())
        self.assertEqual(receipt["common_price_row_count"], MAXIMUM_COMMON_PRICE_ROWS)
        self.assertEqual(receipt["common_observation_count"], 60)
        self.assertEqual(
            receipt["common_observation_index_hash"],
            receipt["common_support_matrix"]["common_observation_index_hash"],
        )

    def test_receipt_is_deterministic_and_does_not_project_source_rows(self) -> None:
        replay = self.replay()
        first = build_correlation_common_support_derivation_receipt_v1(replay)
        second = build_correlation_common_support_derivation_receipt_v1(replay)
        self.assertEqual(first, second)
        rendered = repr(first)
        self.assertNotIn("2026-", rendered)
        self.assertNotIn("price_rows", rendered)
        self.assertNotIn("close", rendered)

    def test_receipt_verifier_accepts_exact_rebuild(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        check = verify_correlation_common_support_derivation_receipt_v1(
            receipt,
            matrix_replay=replay,
        )
        self.assertEqual(check["status"], "PASS")

    def test_receipt_is_bound_to_exact_source_replay(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        shifted = {
            symbol: self.dates(60, offset=1) for symbol in self.symbols
        }
        alternate = self.replay(return_dates=shifted)
        check = verify_correlation_common_support_derivation_receipt_v1(
            receipt,
            matrix_replay=alternate,
        )
        self.assertEqual(check["status"], "BLOCK")

    def test_coherently_resealed_matrix_drift_is_rejected(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        receipt["common_support_matrix"]["pairs"][0]["pearson_correlation"] += 0.01
        matrix_body = {
            key: value
            for key, value in receipt["common_support_matrix"].items()
            if key != "matrix_hash"
        }
        receipt["common_support_matrix"]["matrix_hash"] = _canonical_hash(matrix_body)
        receipt["common_support_matrix_hash"] = receipt["common_support_matrix"]["matrix_hash"]
        receipt["receipt_hash"] = _canonical_hash({
            key: value for key, value in receipt.items() if key != "receipt_hash"
        })
        check = verify_correlation_common_support_derivation_receipt_v1(
            receipt,
            matrix_replay=replay,
        )
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("common_support_derivation_receipt_semantic_mismatch", check["blockers"])

    def test_source_replay_tampering_is_rejected(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        replay["completed_price_input"]["datasets"][0]["price_rows"][1]["close"] += 1.0
        check = verify_correlation_common_support_derivation_receipt_v1(
            receipt,
            matrix_replay=replay,
        )
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("source_matrix_replay_invalid", check["blockers"])

    def test_authority_injection_is_rejected(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        receipt["permissions"]["paper_authorized"] = True
        receipt["receipt_hash"] = _canonical_hash({
            key: value for key, value in receipt.items() if key != "receipt_hash"
        })
        check = verify_correlation_common_support_derivation_receipt_v1(
            receipt,
            matrix_replay=replay,
        )
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("execution_authority_invalid", check["blockers"])

    def test_derived_gate_passes_without_authority(self) -> None:
        result = self.evaluate(self.replay())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["derivation_verified"])
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertEqual(result["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_derived_gate_verifier_accepts_exact_output(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        cells = self.cells()
        result = self.evaluate(replay, receipt, cells)
        self.assertTrue(verify_correlation_common_support_derived_gate_v1(
            result,
            receipt,
            replay,
            cells,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        ))

    def test_derived_gate_verifier_rejects_resealed_drift(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        cells = self.cells()
        result = self.evaluate(replay, receipt, cells)
        result["passing_cluster_count"] += 1
        result["gate_hash"] = _canonical_hash({
            key: value for key, value in result.items() if key != "gate_hash"
        })
        self.assertFalse(verify_correlation_common_support_derived_gate_v1(
            result,
            receipt,
            replay,
            cells,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        ))

    def test_topology_blocker_is_preserved(self) -> None:
        base = [random.Random(index + 1).uniform(-0.012, 0.012) for index in range(60)]
        replay = self.replay(returns={
            "AAA": base,
            "BBB": list(base),
            "CCC": self.returns["CCC"],
        })
        result = self.evaluate(replay)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_cluster_first_blocking_tier"], "TOPOLOGY")

    def test_cluster_vote_blocker_is_preserved(self) -> None:
        result = self.evaluate(
            self.replay(),
            cells=self.cells({"AAA": "PASS", "BBB": "BLOCK", "CCC": "BLOCK"}),
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_cluster_first_blocking_tier"], "CLUSTER_VOTE")

    def test_coverage_blocker_is_preserved(self) -> None:
        result = self.evaluate(self.replay(), cells=self.cells()[:-1])
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_cluster_first_blocking_tier"], "COVERAGE")

    def test_invalid_identity_blocks_before_derivation(self) -> None:
        replay = self.replay()
        receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        result = evaluate_correlation_common_support_derived_gate_v1(
            receipt,
            replay,
            self.cells(),
            strategy_id=" trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["first_blocking_tier"], "IDENTITY")
        self.assertEqual(result["tiers"][1]["status"], "NOT_EVALUATED")

    def test_common_date_shift_changes_index_and_receipt_hashes(self) -> None:
        first = build_correlation_common_support_derivation_receipt_v1(self.replay())
        shifted = {symbol: self.dates(60, offset=1) for symbol in self.symbols}
        second = build_correlation_common_support_derivation_receipt_v1(
            self.replay(return_dates=shifted)
        )
        self.assertNotEqual(first["common_price_index_hash"], second["common_price_index_hash"])
        self.assertNotEqual(first["common_observation_index_hash"], second["common_observation_index_hash"])
        self.assertNotEqual(first["receipt_hash"], second["receipt_hash"])


if __name__ == "__main__":
    unittest.main()
