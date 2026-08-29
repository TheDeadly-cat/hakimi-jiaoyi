from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.experiment_manifest import (
    build_reproducible_experiment_manifest,
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)
from quant_bot.models import Portfolio, Signal
from quant_bot.reporting import save_json_report
from quant_bot.risk import RiskManager
from quant_bot.strategies.base import StrategyBase


class HoldStrategy(StrategyBase):
    name = "manifest_hold"
    version = "v1"

    def generate_signal(self, _data: pd.DataFrame, _portfolio: Portfolio) -> Signal:
        return Signal.hold("manifest fixture")


def _frame() -> pd.DataFrame:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    index = pd.DatetimeIndex([start + timedelta(days=offset) for offset in range(40)])
    close = [100.0 + offset for offset in range(40)]
    return pd.DataFrame({
        "open": close,
        "high": [value + 1.0 for value in close],
        "low": [value - 1.0 for value in close],
        "close": close,
        "volume": [1000.0] * 40,
    }, index=index)


class ReproducibleExperimentManifestV1Tests(unittest.TestCase):
    @staticmethod
    def context(**overrides) -> dict:
        values = {
            "git_commit_sha": "a" * 40,
            "git_worktree_clean": True,
            "dependency_lock_hash": "b" * 64,
            "dependency_lock_fully_pinned": True,
            "dependency_lock_name": "requirements.lock",
            "random_seed": 7,
            "runtime_version": "CPython 3.14.0",
            "evaluation_role": "FROZEN_TEST",
            "evaluation_protocol_hash": "c" * 64,
            "evaluation_protocol_verified": True,
        }
        values.update(overrides)
        return values

    @classmethod
    def report(cls, context: dict | None = None):
        config = BotConfig(market="stock", symbol="AAPL", timeframe="1d")
        config.execution.fee_rate = 0.001
        config.execution.slippage_pct = 0.002
        return BacktestEngine(
            config,
            HoldStrategy(),
            RiskManager(config.risk),
            experiment_context=context,
        ).run(_frame())

    @staticmethod
    def result_payload(report) -> dict:
        payload = report.to_dict()
        payload.pop("experiment_manifest")
        return payload

    def test_backtest_embeds_complete_verified_manifest(self) -> None:
        report = self.report(self.context())
        manifest = report.experiment_manifest
        self.assertEqual(manifest["status"], "PASS")
        self.assertTrue(manifest["ranking_gate"]["input_allowed"])
        self.assertFalse(manifest["parameter_selection_allowed"])
        self.assertFalse(manifest["paper_authorized"])
        self.assertFalse(manifest["live_order_allowed"])
        self.assertTrue(
            verify_reproducible_experiment_manifest(
                manifest,
                self.result_payload(report),
            )
        )

    def test_default_context_is_present_but_fail_closed(self) -> None:
        manifest = self.report().experiment_manifest
        self.assertEqual(manifest["status"], "BLOCK")
        self.assertIn("git_commit_sha_missing_or_invalid", manifest["blockers"])
        self.assertIn("dependency_lock_not_fully_pinned", manifest["blockers"])
        self.assertFalse(manifest["ranking_gate"]["input_allowed"])

    def test_dirty_worktree_blocks_reproducibility(self) -> None:
        manifest = self.report(self.context(git_worktree_clean=False)).experiment_manifest
        self.assertIn("git_worktree_not_clean", manifest["blockers"])
        self.assertEqual(manifest["status"], "BLOCK")

    def test_unpinned_dependency_set_blocks_reproducibility(self) -> None:
        manifest = self.report(
            self.context(dependency_lock_fully_pinned=False)
        ).experiment_manifest
        self.assertIn("dependency_lock_not_fully_pinned", manifest["blockers"])
        self.assertFalse(manifest["ranking_gate"]["input_allowed"])

    def test_unclassified_run_cannot_enter_ranking_input(self) -> None:
        manifest = self.report(self.context(
            evaluation_role="UNCLASSIFIED",
            evaluation_protocol_hash="",
            evaluation_protocol_verified=False,
        )).experiment_manifest
        self.assertEqual(manifest["status"], "PASS")
        self.assertIn(
            "evaluation_role_not_rankable",
            manifest["ranking_gate"]["blockers"],
        )

    def test_training_run_cannot_enter_ranking_input(self) -> None:
        manifest = self.report(self.context(evaluation_role="TRAIN")).experiment_manifest
        self.assertEqual(manifest["status"], "PASS")
        self.assertIn("training_result_not_rankable", manifest["ranking_gate"]["blockers"])

    def test_result_tamper_invalidates_manifest(self) -> None:
        report = self.report(self.context())
        payload = self.result_payload(report)
        payload["final_equity"] = 999999.0
        self.assertFalse(
            verify_reproducible_experiment_manifest(report.experiment_manifest, payload)
        )

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        report = self.report(self.context())
        tampered = deepcopy(report.experiment_manifest)
        tampered["paper_authorized"] = True
        tampered["manifest_hash"] = canonical_payload_hash({
            key: value for key, value in tampered.items() if key != "manifest_hash"
        })
        self.assertFalse(
            verify_reproducible_experiment_manifest(
                tampered,
                self.result_payload(report),
            )
        )

    def test_deterministic_experiment_id_drives_report_filename(self) -> None:
        first = self.report(self.context())
        second = self.report(self.context())
        self.assertEqual(
            first.experiment_manifest["experiment_id"],
            second.experiment_manifest["experiment_id"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_json_report(
                first.to_dict(),
                temp_dir,
                "backtest",
                artifact_id=first.experiment_manifest["experiment_id"],
            )
            self.assertEqual(
                Path(path).name,
                f"backtest_{first.experiment_manifest['experiment_id']}.json",
            )
            stored = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(json.dumps(stored, sort_keys=True).encode("utf-8")).hexdigest(),
            hashlib.sha256(json.dumps(first.to_dict(), sort_keys=True).encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
