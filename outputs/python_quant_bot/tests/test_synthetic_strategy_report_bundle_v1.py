from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

import exchange_terminal.application.synthetic_strategy_report_bundle_v1 as legacy_bundle
from hakimi_research import synthetic_strategy_report_bundle as canonical_bundle

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    SyntheticStrategyReportBundleError,
    build_synthetic_strategy_report_bundle_v1,
    canonical_sha256,
    plan_synthetic_strategy_report_bundle_v1,
    render_synthetic_strategy_report_bundle_markdown_v1,
    replay_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
)


class SyntheticStrategyReportBundleV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_synthetic_strategy_report_bundle_v1(execute=True)

    def test_00_canonical_source_and_legacy_identity(self) -> None:
        source_path = Path(canonical_bundle.__file__).resolve()
        repo_root = Path(__file__).resolve().parents[3]
        self.assertEqual(
            source_path,
            repo_root / "src" / "hakimi_research" / "synthetic_strategy_report_bundle.py",
        )
        self.assertNotIn("outputs", source_path.relative_to(repo_root).parts)
        self.assertIs(
            legacy_bundle.build_synthetic_strategy_report_bundle_v1,
            canonical_bundle.build_synthetic_strategy_report_bundle_v1,
        )
        self.assertIs(legacy_bundle._run_backtest, canonical_bundle._run_backtest)

    def test_01_plan_is_dry_and_exactly_32_runs(self) -> None:
        plan = plan_synthetic_strategy_report_bundle_v1()
        self.assertEqual(plan["planned_run_count"], 32)
        self.assertEqual(len(plan["planned_runs"]), 32)
        self.assertEqual(plan["executed_run_count"], 0)
        self.assertFalse(plan["runtime_mutations"])
        self.assertEqual(plan["plan_sha256"], canonical_sha256({k: v for k, v in plan.items() if k != "plan_sha256"}))

    def test_02_execution_requires_exact_true(self) -> None:
        for value in (False, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyReportBundleError):
                    build_synthetic_strategy_report_bundle_v1(execute=value)  # type: ignore[arg-type]

    def test_03_bundle_verifies_and_keeps_authority_false(self) -> None:
        receipt = verify_synthetic_strategy_report_bundle_v1(self.bundle)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["verified_run_count"], 32)
        self.assertTrue(all(value is False for value in self.bundle["authority"].values()))
        self.assertFalse(self.bundle["runtime_mutations"])
        self.assertEqual(self.bundle["status"], "BLOCK")

    def test_04_inventory_uses_six_real_strategies_and_ensemble_gap(self) -> None:
        self.assertEqual(
            [report["strategy_id"] for report in self.bundle["strategy_reports"]],
            ["bollinger", "dual_ma", "grid", "macd", "momentum", "rsi"],
        )
        summary = {item["family_id"]: item for item in self.bundle["family_summary"]}
        self.assertEqual(summary["RANGE"]["report_count"], 3)
        self.assertEqual(summary["TREND"]["report_count"], 3)
        self.assertEqual(summary["ENSEMBLE"]["status"], "GAP")
        self.assertEqual(summary["ENSEMBLE"]["report_count"], 0)

    def test_05_partitions_purge_embargo_and_cost_stress_are_bound(self) -> None:
        protocol = self.bundle["fixture"]["partition_protocol"]
        self.assertEqual(protocol["purge_rows"], 10)
        self.assertEqual(protocol["embargo_rows"], 10)
        self.assertEqual(protocol["partitions"]["train"]["row_count"], 200)
        self.assertEqual(protocol["partitions"]["validation"]["row_count"], 180)
        self.assertEqual(protocol["partitions"]["frozen"]["row_count"], 200)
        for report in self.bundle["strategy_reports"]:
            self.assertEqual(report["runs"]["frozen_1x"]["cost_multiplier"], 1)
            self.assertEqual(report["runs"]["frozen_2x"]["cost_multiplier"], 2)
            self.assertEqual(report["runs"]["frozen_3x"]["cost_multiplier"], 3)

    def test_06_cash_and_buy_hold_benchmarks_are_frozen_only(self) -> None:
        self.assertEqual(set(self.bundle["benchmarks"]), {"cash", "buy_and_hold"})
        frozen_hash = self.bundle["fixture"]["partition_protocol"]["partitions"]["frozen"]["dataset_sha256"]
        for run in self.bundle["benchmarks"].values():
            self.assertEqual(run["evaluation_role"], "FROZEN_COST_1X")
            self.assertEqual(run["dataset_sha256"], frozen_hash)

    def test_07_distribution_evidence_is_present_for_every_strategy(self) -> None:
        for report in self.bundle["strategy_reports"]:
            binding = report["frozen_distribution"]
            self.assertEqual(binding["source_report"]["strategy_id"], report["strategy_id"])
            self.assertEqual(binding["source_report"]["result"], report["runs"]["frozen_1x"]["result"])
            self.assertEqual(len(binding["binding_sha256"]), 64)

    def test_08_renderer_is_neutral_and_gap_complete(self) -> None:
        markdown = render_synthetic_strategy_report_bundle_markdown_v1(self.bundle)
        self.assertIn("## SOURCE", markdown)
        self.assertIn("## GAP", markdown)
        self.assertIn("## MATURITY", markdown)
        self.assertIn("## PERMISSION", markdown)
        self.assertIn("ENSEMBLE_STRATEGY_NOT_IMPLEMENTED", markdown)
        self.assertIn("SYNTHETIC_OBSERVATION_ONLY", markdown)
        self.assertNotIn("READY", markdown)

    def test_09_tamper_and_exact_type_alias_fail_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["strategy_reports"][0]["runs"]["frozen_1x"]["result"]["total_return"] += 0.01
        self.assertEqual(verify_synthetic_strategy_report_bundle_v1(tampered)["status"], "BLOCK")

        escalated = deepcopy(self.bundle)
        escalated["authority"]["paper_authorized"] = True
        escalated["bundle_sha256"] = canonical_sha256(
            {key: value for key, value in escalated.items() if key != "bundle_sha256"}
        )
        self.assertEqual(verify_synthetic_strategy_report_bundle_v1(escalated)["status"], "BLOCK")

        class StrAlias(str):
            pass

        aliased = deepcopy(self.bundle)
        aliased["schema_version"] = StrAlias(aliased["schema_version"])
        self.assertEqual(verify_synthetic_strategy_report_bundle_v1(aliased)["status"], "BLOCK")

    def test_10_full_replay_is_byte_exact(self) -> None:
        receipt = replay_synthetic_strategy_report_bundle_v1(self.bundle)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_run_count"], 32)
        self.assertFalse(receipt["runtime_mutations"])


if __name__ == "__main__":
    unittest.main()
