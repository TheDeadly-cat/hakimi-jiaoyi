from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_selection_alignment import (
    build_strategy_selection_alignment_input_snapshot,
    verify_strategy_selection_alignment_input_snapshot,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StrategySelectionAlignmentTests(unittest.TestCase):
    def fixture(self) -> tuple[dict[str, object], list[dict[str, object]]]:
        payloads: dict[str, object] = {
            "BTC-USDC": {
                "source": "UNIT_TEST",
                "rows": [
                    {"date": "2026-01-01", "complete": True},
                    {"date": "2026-01-02", "complete": True},
                ],
            }
        }
        manifests: list[dict[str, object]] = [{
            "role": "SELECTION",
            "symbol": "BTC-USDC",
            "source": "UNIT_TEST",
            "status": "PASS",
            "row_count": 2,
            "blockers": [],
        }]
        return payloads, manifests

    def test_snapshot_binds_source_role_and_symbol_coverage(self) -> None:
        payloads, manifests = self.fixture()
        snapshot = build_strategy_selection_alignment_input_snapshot(
            payloads,
            manifests,
        )
        baseline = verify_strategy_selection_alignment_input_snapshot(
            snapshot,
            expected_symbols={"BTC-USDC"},
            manifests=manifests,
        )
        self.assertEqual(baseline["status"], "PASS", baseline["blockers"])

        forged_source = json.loads(json.dumps(snapshot))
        forged_source["datasets"][0]["source"] = "FORGED_SOURCE"
        content = dict(forged_source)
        content.pop("input_hash", None)
        forged_source["input_hash"] = canonical_hash(content)
        source_result = verify_strategy_selection_alignment_input_snapshot(
            forged_source,
            expected_symbols={"BTC-USDC"},
            manifests=manifests,
        )
        self.assertEqual(source_result["status"], "BLOCK")
        self.assertIn(
            "strategy_selection_alignment_input_source_mismatch:BTC-USDC",
            source_result["blockers"],
        )

        wrong_role = json.loads(json.dumps(snapshot))
        wrong_role["datasets"][0]["role"] = "CONFIRMATION"
        role_content = dict(wrong_role)
        role_content.pop("input_hash", None)
        wrong_role["input_hash"] = canonical_hash(role_content)
        role_result = verify_strategy_selection_alignment_input_snapshot(
            wrong_role,
            expected_symbols={"BTC-USDC"},
            manifests=manifests,
        )
        self.assertEqual(role_result["status"], "BLOCK")

        deleted = json.loads(json.dumps(snapshot))
        deleted["datasets"] = []
        deleted["dataset_count"] = 0
        deleted["row_count"] = 0
        deleted_content = dict(deleted)
        deleted_content.pop("input_hash", None)
        deleted["input_hash"] = canonical_hash(deleted_content)
        deleted_result = verify_strategy_selection_alignment_input_snapshot(
            deleted,
            expected_symbols={"BTC-USDC"},
            manifests=manifests,
        )
        self.assertEqual(deleted_result["status"], "BLOCK")
        self.assertIn(
            "strategy_selection_alignment_input_coverage_mismatch",
            deleted_result["blockers"],
        )

    def test_builder_rejects_source_drift_before_sealing(self) -> None:
        payloads, manifests = self.fixture()
        payloads["BTC-USDC"]["source"] = "FORGED_SOURCE"
        with self.assertRaisesRegex(
            ValueError,
            "strategy_selection_alignment_source_mismatch",
        ):
            build_strategy_selection_alignment_input_snapshot(payloads, manifests)


if __name__ == "__main__":
    unittest.main()
