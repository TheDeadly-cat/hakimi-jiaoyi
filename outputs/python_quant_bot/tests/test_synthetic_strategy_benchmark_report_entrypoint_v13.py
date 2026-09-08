from __future__ import annotations

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import examples.build_synthetic_strategy_benchmark_report_v13 as v13


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = _sha256_json(unsigned)


def _fake_source_v12() -> dict[str, object]:
    return {
        "schema_version": "synthetic-strategy-benchmark-report-v12",
        "report_sha256": "1" * 64,
        "plan": v13.plan_synthetic_strategy_benchmark_report_v12(),
        "total_logical_run_count": 222,
        "authority": {
            "blind_test_complete": False,
            "formal_inference_authorized": False,
            "live_authorized": False,
            "order_entry_authorized": False,
            "paper_authorized": False,
            "profitability_proven": False,
        },
        "runtime_mutations": False,
    }


class SyntheticStrategyBenchmarkReportEntrypointV13Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _fake_source_v12()
        cls.material = v13.load_statistical_reference_material_v2()
        with patch.object(
            v13,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"status": "BLOCK"},
        ):
            cls.report = v13.build_synthetic_strategy_benchmark_report_v13(
                cls.source,
                cls.material,
                execute=True,
            )
            cls.receipt = v13.verify_synthetic_strategy_benchmark_report_v13(
                cls.report
            )

    def _verify(self, report: dict[str, object]) -> dict[str, object]:
        with patch.object(
            v13,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"status": "BLOCK"},
        ):
            return v13.verify_synthetic_strategy_benchmark_report_v13(report)

    def test_01_plan_binds_both_sources_without_summing_runs(self) -> None:
        plan = v13.plan_synthetic_strategy_benchmark_report_v13()
        self.assertEqual(plan["source_logical_run_count"], 222)
        self.assertEqual(plan["statistical_reference_executed_run_count"], 179)
        self.assertIsNone(plan["combined_total_logical_run_count"])
        self.assertFalse(plan["run_accounting_additive"])
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)

    def test_02_plan_retains_legacy_v1_and_binds_reference_v2(self) -> None:
        plan = v13.plan_synthetic_strategy_benchmark_report_v13()
        self.assertEqual(
            plan["legacy_bootstrap_plan_schemas"],
            ["synthetic-strategy-bootstrap-validation-plan-v1"],
        )
        binding = plan["statistical_reference_binding_plan"]
        self.assertEqual(
            binding["receipt_sha256"],
            "9f072ee64a55af2b8fc624a9336794c370a702880783783f960edf6cc67c9509",
        )
        self.assertEqual(
            binding["bootstrap_bundle_sha256"],
            "edca33bd9db62dc5d118ec181667b0c8cd36d5754b911ad088b5ccf8e11beceb",
        )

    def test_03_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    v13.build_synthetic_strategy_benchmark_report_v13(
                        execute=value  # type: ignore[arg-type]
                    )

    def test_04_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            v13.build_synthetic_strategy_benchmark_report_v13(execute=True)
        with self.assertRaises(ValueError):
            v13.build_synthetic_strategy_benchmark_report_v13(
                self.source, execute=True
            )
        with self.assertRaises(ValueError):
            v13.build_synthetic_strategy_benchmark_report_v13(
                statistical_reference_material_v2=self.material,
                execute=True,
            )

    def test_05_receipt_is_a_denied_alignment_gap(self) -> None:
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(self.receipt["source_alignment_proven"])
        self.assertFalse(
            self.receipt["statistical_reference_applied_to_source_report"]
        )
        self.assertFalse(self.receipt["bootstrap_v2_replaces_legacy_v1"])
        self.assertFalse(self.receipt["run_accounting_additive"])
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_06_source_and_reference_bindings_are_exact(self) -> None:
        bindings = self.report["bindings"]
        self.assertEqual(
            bindings["source_report_v12_sha256"], self.source["report_sha256"]
        )
        self.assertEqual(
            bindings["statistical_reference_receipt_sha256"],
            self.material["receipt"]["receipt_sha256"],
        )
        self.assertEqual(
            bindings["statistical_reference_manifest_sha256"],
            self.material["manifest"]["manifest_sha256"],
        )

    def test_07_alignment_gaps_are_explicit(self) -> None:
        gaps = set(self.report["gaps"])
        for gap in v13._ALIGNMENT_GAPS:
            self.assertIn(gap, gaps)
        self.assertIn("REAL_DATASET_GAP", gaps)
        self.assertIn("NO_FORMAL_INFERENCE_AUTHORITY", gaps)

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v12_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            self._verify(tampered)

    def test_09_resealed_reference_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["statistical_reference_receipt_sha256"] = "f" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            self._verify(tampered)

    def test_10_reference_material_tamper_fails_before_composition(self) -> None:
        tampered = copy.deepcopy(self.material)
        tampered["receipt"]["bootstrap_replicate_count"] = 999
        with patch.object(
            v13,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"status": "BLOCK"},
        ):
            with self.assertRaises(ValueError):
                v13.build_synthetic_strategy_benchmark_report_v13(
                    self.source,
                    tampered,
                    execute=True,
                )

    def test_11_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            self._verify(DictAlias(self.report))
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            self._verify(tampered)

    def test_12_renderer_is_non_current_neutral_and_ordered(self) -> None:
        plan_markdown = v13.render_synthetic_strategy_benchmark_report_plan_markdown_v13(
            v13.plan_synthetic_strategy_benchmark_report_v13()
        )
        with patch.object(
            v13,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"status": "BLOCK"},
        ):
            report_markdown = (
                v13.render_synthetic_strategy_benchmark_report_markdown_v13(
                    self.report
                )
            )
        for markdown in (plan_markdown, report_markdown):
            self.assertIn("NON-CURRENT RESEARCH-ONLY ALIGNMENT GATE", markdown)
            self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
            self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
            self.assertLess(
                markdown.index("## MATURITY"), markdown.index("## PERMISSION")
            )
            self.assertIn("Source alignment proven: FALSE", markdown)
            self.assertIn("Profitability proven: FALSE", markdown)
            self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
