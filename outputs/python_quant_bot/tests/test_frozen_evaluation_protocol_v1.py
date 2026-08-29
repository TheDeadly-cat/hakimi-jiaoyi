from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import unittest

import pandas as pd

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
activate_canonical_source()

from hakimi_research.frozen_evaluation import (  # noqa: E402
    AUTHORITY_LOCK,
    EVIDENCE_SCOPE,
    MARKDOWN_REPORT_VERSION,
    STANDARD_REPORT_COVERAGE_GAPS,
    build_frozen_evaluation_protocol,
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_protocol,
    verify_frozen_evaluation_report,
)
from quant_bot.config import BotConfig  # noqa: E402
from quant_bot.experiment_manifest import canonical_payload_hash  # noqa: E402


def synthetic_frame() -> pd.DataFrame:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    index = pd.DatetimeIndex([start + timedelta(days=offset) for offset in range(128)])
    close = [100.0 + offset * 0.2 + math.sin(offset / 5.0) for offset in range(128)]
    return pd.DataFrame(
        {
            "open": [value - 0.1 for value in close],
            "high": [value + 0.5 for value in close],
            "low": [value - 0.5 for value in close],
            "close": close,
            "volume": [1000.0 + offset for offset in range(128)],
        },
        index=index,
    )


def config() -> BotConfig:
    value = BotConfig(market="stock", symbol="SYNTH-001", timeframe="1d")
    value.data.provider = "csv"
    value.data.use_cache = False
    value.strategy.name = "dual_ma"
    value.strategy.params = {
        "fast_window": 5,
        "slow_window": 20,
        "position_pct": 0.2,
        "take_profit_pct": 0.05,
        "stop_loss_pct": 0.03,
    }
    value.execution.fee_rate = 0.001
    value.execution.slippage_pct = 0.001
    value.execution.live_trading_enabled = False
    return value


def context() -> dict:
    return {
        "git_commit_sha": "a" * 40,
        "git_worktree_clean": True,
        "dependency_lock_hash": "b" * 64,
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "runtime_version": "python-test",
    }


def protocol(frame: pd.DataFrame | None = None, value: BotConfig | None = None) -> dict:
    return build_frozen_evaluation_protocol(
        frame if frame is not None else synthetic_frame(),
        value if value is not None else config(),
        train_rows=40,
        purge_rows=4,
        validation_rows=40,
        embargo_rows=4,
        frozen_test_rows=40,
        random_seed=17,
    )


class FrozenEvaluationProtocolV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = synthetic_frame()
        cls.config = config()
        cls.protocol = protocol(cls.frame, cls.config)
        cls.report = build_frozen_evaluation_report(
            cls.protocol,
            cls.frame,
            cls.config,
            experiment_context=context(),
        )

    def test_protocol_is_deterministic_and_exactly_verifiable(self) -> None:
        self.assertEqual(self.protocol, protocol(self.frame, self.config))
        self.assertTrue(verify_frozen_evaluation_protocol(self.protocol, self.frame, self.config))
        self.assertEqual(self.protocol["evidence_scope"], EVIDENCE_SCOPE)

    def test_partition_order_and_gaps_are_exact(self) -> None:
        windows = self.protocol["partition_plan"]["windows"]
        self.assertEqual([item["name"] for item in windows], [
            "TRAIN", "PURGE", "VALIDATION", "EMBARGO", "FROZEN_TEST"
        ])
        self.assertEqual([item["row_count"] for item in windows], [40, 4, 40, 4, 40])
        self.assertEqual(windows[-1]["end_position_exclusive"], len(self.frame))

    def test_cost_scenarios_and_benchmarks_are_fixed(self) -> None:
        self.assertEqual(
            [(item["scenario_id"], item["multiplier"]) for item in self.protocol["cost_scenarios"]],
            [("BASE", 1), ("DOUBLE_COST", 2), ("TRIPLE_COST", 3)],
        )
        self.assertEqual(
            [item["benchmark_id"] for item in self.protocol["benchmarks"]],
            ["CASH", "ENGINE_BUY_AND_HOLD"],
        )

    def test_partition_types_totals_and_minimums_fail_closed(self) -> None:
        kwargs = dict(
            data=self.frame,
            config=self.config,
            train_rows=40,
            purge_rows=4,
            validation_rows=40,
            embargo_rows=4,
            frozen_test_rows=40,
        )
        for override in (
            {"train_rows": True},
            {"train_rows": 39},
            {"purge_rows": 0, "train_rows": 44},
            {"frozen_test_rows": 39},
        ):
            with self.subTest(override=override):
                values = dict(kwargs)
                values.update(override)
                with self.assertRaisesRegex(ValueError, "frozen_evaluation_"):
                    build_frozen_evaluation_protocol(**values)

    def test_noncanonical_dataset_and_ohlcv_fail_closed(self) -> None:
        duplicate = self.frame.copy()
        duplicate.index = pd.DatetimeIndex([self.frame.index[0], *self.frame.index[:-1]])
        invalid = self.frame.copy()
        invalid.iloc[0, invalid.columns.get_loc("high")] = 1.0
        for candidate in (duplicate, invalid, self.frame.reset_index(drop=True)):
            with self.subTest(kind=type(candidate.index).__name__):
                with self.assertRaisesRegex(ValueError, "frozen_evaluation_dataset_"):
                    protocol(candidate, self.config)

    def test_dataset_and_config_drift_are_rejected(self) -> None:
        changed_data = self.frame.copy()
        changed_data.iloc[-1, changed_data.columns.get_loc("close")] += 0.1
        changed_config = deepcopy(self.config)
        changed_config.execution.fee_rate = 0.002
        with self.assertRaisesRegex(ValueError, "protocol_verification_failed"):
            verify_frozen_evaluation_protocol(self.protocol, changed_data, self.config)
        with self.assertRaisesRegex(ValueError, "protocol_verification_failed"):
            verify_frozen_evaluation_protocol(self.protocol, self.frame, changed_config)

    def test_resealed_partition_protocol_is_rejected(self) -> None:
        tampered = deepcopy(self.protocol)
        tampered["partition_plan"]["windows"][0]["end_time"] = tampered[
            "partition_plan"
        ]["windows"][0]["start_time"]
        core = {key: value for key, value in tampered.items() if key not in {"protocol_id", "protocol_hash"}}
        tampered["protocol_hash"] = canonical_payload_hash(core)
        tampered["protocol_id"] = f"hfep-{tampered['protocol_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "protocol_verification_failed"):
            verify_frozen_evaluation_protocol(tampered, self.frame, self.config)

    def test_report_has_complete_role_cost_and_benchmark_matrix(self) -> None:
        self.assertTrue(
            verify_frozen_evaluation_report(self.report, self.protocol, self.frame, self.config)
        )
        self.assertEqual(len(self.report["strategy_runs"]), 7)
        self.assertEqual(len(self.report["benchmark_runs"]), 4)
        for record in [*self.report["strategy_runs"], *self.report["benchmark_runs"]]:
            manifest = record["experiment_manifest"]
            self.assertEqual(manifest["evaluation_role"], record["role"])
            self.assertEqual(manifest["evaluation_protocol_hash"], self.protocol["protocol_hash"])
            self.assertTrue(manifest["evaluation_protocol_verified"])

    def test_report_remains_blocked_and_non_authorizing(self) -> None:
        self.assertEqual(self.report["quality_gate"]["status"], "BLOCK")
        self.assertEqual(self.report["authority"], AUTHORITY_LOCK)
        self.assertFalse(self.report["quality_gate"]["frozen_test_is_blind"])
        self.assertFalse(self.report["quality_gate"]["natural_forward_evidence"])
        self.assertIn("SINGLE_CONSUMPTION_NOT_ENFORCED", self.report["quality_gate"]["blockers"])

    def test_frozen_nested_pass_cannot_grant_parameter_selection(self) -> None:
        frozen = [
            item for item in self.report["strategy_runs"] if item["role"] == "FROZEN_TEST"
        ]
        self.assertTrue(all(item["experiment_manifest"]["status"] == "PASS" for item in frozen))
        self.assertTrue(
            all(item["experiment_manifest"]["ranking_gate"]["input_allowed"] for item in frozen)
        )
        self.assertFalse(self.report["authority"]["parameter_selection"])
        self.assertFalse(self.report["authority"]["ranking"])

    def test_result_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.report)
        tampered["strategy_runs"][0]["result"]["final_equity"] += 1.0
        with self.assertRaisesRegex(ValueError, "strategy_run_verification_failed|report_hash_invalid"):
            verify_frozen_evaluation_report(tampered, self.protocol, self.frame, self.config)

    def test_markdown_report_is_deterministic_neutral_and_complete(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        )
        self.assertEqual(
            rendered,
            render_frozen_evaluation_markdown(
                self.report,
                self.protocol,
                self.frame,
                self.config,
            ),
        )
        self.assertIn(f"Renderer: `{MARKDOWN_REPORT_VERSION}`", rendered)
        for section in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertEqual(rendered.count(section), 1)
        for gap in STANDARD_REPORT_COVERAGE_GAPS:
            self.assertIn(f"`{gap}`", rendered)
        self.assertIn(self.report["report_hash"], rendered)
        self.assertIn(self.protocol["protocol_hash"], rendered)
        for identity in (
            "BASE",
            "DOUBLE_COST",
            "TRIPLE_COST",
            "CASH",
            "ENGINE_BUY_AND_HOLD",
        ):
            self.assertEqual(rendered.count(f"| FROZEN_TEST | {identity} |"), 1)
        self.assertIn("| `paper` | `false` |", rendered)
        self.assertIn("| `live` | `false` |", rendered)
        self.assertIn("| `order` | `false` |", rendered)
        self.assertNotIn("READY", rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_markdown_report_verifies_input_and_normalizes_run_order(self) -> None:
        baseline = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        )
        reordered = deepcopy(self.report)
        reordered["strategy_runs"].reverse()
        reordered["benchmark_runs"].reverse()
        core = {
            key: value
            for key, value in reordered.items()
            if key not in {"report_id", "report_hash"}
        }
        reordered["report_hash"] = canonical_payload_hash(core)
        reordered["report_id"] = f"hfer-{reordered['report_hash'][:20]}"
        self.assertTrue(
            verify_frozen_evaluation_report(
                reordered,
                self.protocol,
                self.frame,
                self.config,
            )
        )
        normalized = render_frozen_evaluation_markdown(
            reordered,
            self.protocol,
            self.frame,
            self.config,
        )
        self.assertNotEqual(reordered["report_hash"], self.report["report_hash"])
        self.assertNotEqual(normalized, baseline)
        self.assertEqual(
            normalized.replace(reordered["report_hash"], self.report["report_hash"])
            .replace(reordered["report_id"], self.report["report_id"]),
            baseline,
        )
        tampered = deepcopy(self.report)
        tampered["strategy_runs"][0]["result"]["final_equity"] += 1.0
        with self.assertRaisesRegex(
            ValueError,
            "strategy_run_verification_failed|report_hash_invalid",
        ):
            render_frozen_evaluation_markdown(
                tampered,
                self.protocol,
                self.frame,
                self.config,
            )

    def test_resealed_authority_escalation_is_rejected_and_cli_stays_dormant(self) -> None:
        tampered = deepcopy(self.report)
        tampered["authority"]["paper"] = True
        core = {key: value for key, value in tampered.items() if key not in {"report_id", "report_hash"}}
        tampered["report_hash"] = canonical_payload_hash(core)
        tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "report_binding_invalid"):
            verify_frozen_evaluation_report(tampered, self.protocol, self.frame, self.config)
        cli_source = (REPO_ROOT / "src" / "hakimi_research" / "cli.py").read_text(encoding="utf-8")
        self.assertNotIn("frozen-evaluate", cli_source)
        self.assertNotIn("build_frozen_evaluation_report", cli_source)


if __name__ == "__main__":
    unittest.main()
