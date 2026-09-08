from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.experiment_manifest import (
    build_reproducible_experiment_manifest,
    canonical_payload_hash,
)
from hakimi_research.experiment_provenance_consumer_adapter_v1 import (
    CLI_REPORT_BUNDLE_CONSUMER,
    CONSUMER_ADAPTER_VERSION,
    FROZEN_RUN_CONSUMER,
    MULTIPLE_TESTING_OBSERVATION_CONSUMER,
    build_cli_report_provenance_bundle_candidate,
    build_frozen_run_provenance_candidate,
    build_multiple_testing_observation_provenance_candidate,
    verify_cli_report_provenance_bundle_candidate,
    verify_frozen_run_provenance_candidate,
    verify_multiple_testing_observation_provenance_candidate,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _material(
    role: str = "FROZEN_TEST",
    *,
    param_hash: str = "8" * 64,
) -> dict[str, object]:
    protocol_hash = "c" * 64 if role in {"VALIDATION", "FROZEN_TEST"} else ""
    protocol_verified = role in {"VALIDATION", "FROZEN_TEST"}
    reproducibility: dict[str, object] = {
        "run_hash": "d" * 64,
        "config_hash": "e" * 64,
        "data_hash": "f" * 64,
        "data_start": "2025-01-01T00:00:00Z",
        "data_end": "2025-02-01T00:00:00Z",
        "strategy_version": "v1",
        "random_seed": 7,
        "param_hash": param_hash,
    }
    context: dict[str, object] = {
        "git_commit_sha": "a" * 40,
        "git_worktree_clean": True,
        "dependency_lock_hash": "b" * 64,
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "random_seed": 7,
        "runtime_version": "python-test",
    }
    source_context = {
        **context,
        "evaluation_role": role,
        "evaluation_protocol_hash": protocol_hash,
        "evaluation_protocol_verified": protocol_verified,
    }
    result = {"metric": 1.0, "reproducibility": reproducibility}
    manifest = build_reproducible_experiment_manifest(
        result_payload=result,
        reproducibility=reproducibility,
        strategy_name="dual_ma",
        strategy_version="v1",
        symbol="SYNTH-001",
        timeframe="1d",
        fee_rate=0.001,
        slippage_pct=0.001,
        context=source_context,
    )
    manifest_identity = {
        "experiment_id": manifest["experiment_id"],
        "strategy_name": "dual_ma",
        "strategy_version": "v1",
        "symbol": "SYNTH-001",
        "timeframe": "1d",
        "fee_rate": 0.001,
        "slippage_pct": 0.001,
        "evaluation_role": role,
        "evaluation_protocol_hash": protocol_hash,
        "evaluation_protocol_verified": protocol_verified,
    }
    return {
        "result": result,
        "manifest": manifest,
        "reproducibility": reproducibility,
        "context": context,
        "manifest_identity": manifest_identity,
    }


def _different_native(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is float:
        return value + 0.125
    if type(value) is str:
        return value + "-tampered"
    if type(value) is dict:
        return {**value, "tampered": True}
    if type(value) is list:
        return [*value, "tampered"]
    raise AssertionError(f"unsupported synthetic value: {type(value)!r}")


def _stability_observation_material() -> dict[str, object]:
    params = {"fast": 10, "slow": 30}
    material = _material(
        "UNCLASSIFIED",
        param_hash=canonical_payload_hash(params),
    )
    identity = {
        "run_kind": "PARAMETER_STABILITY_OBSERVATION",
        "role": "VALIDATION",
        "scenario_id": "BASE",
        "fee_rate": 0.001,
        "slippage_pct": 0.001,
        "strategy_name": "dual_ma",
        "strategy_version": "v1",
        "cell_id": "CELL-01",
        "segment": "VALIDATION",
        "is_center": True,
        "axes": {"fast": 10, "slow": 30},
        "params": params,
        "params_hash": material["reproducibility"]["param_hash"],
        "cell_hash": "1" * 64,
        "method_spec_hash": "2" * 64,
        "matrix_hash": "3" * 64,
    }
    record = {
        **identity,
        "result": material["result"],
        "experiment_manifest": material["manifest"],
    }
    return {
        "material": material,
        "identity": identity,
        "record": record,
    }


def _cli_artifact_identity(material: dict[str, object]) -> dict[str, object]:
    artifact_id = material["manifest"]["experiment_id"]
    prefix = "backtest_dual_ma_SYNTH-001"
    return {
        "artifact_id": artifact_id,
        "prefix": prefix,
        "report_schema_version": "research-json-report-v1",
        "filename": f"{prefix}_{artifact_id}.json",
    }


class ExperimentProvenanceConsumerAdapterV1Tests(unittest.TestCase):
    def test_frozen_run_candidate_binds_record_and_manifest_inputs(self) -> None:
        material = _material()
        record_identity = {
            "run_kind": "REGISTERED_STRATEGY",
            "role": "FROZEN_TEST",
            "scenario_id": "BASE",
            "fee_rate": 0.001,
            "slippage_pct": 0.001,
            "strategy_name": "dual_ma",
            "strategy_version": "v1",
        }
        record = {
            **record_identity,
            "result": material["result"],
            "experiment_manifest": material["manifest"],
        }
        expectations = {
            "expected_reproducibility": material["reproducibility"],
            "expected_context": material["context"],
            "expected_manifest_identity": material["manifest_identity"],
            "expected_record_identity": record_identity,
        }
        receipt = build_frozen_run_provenance_candidate(record, **expectations)

        self.assertEqual(receipt["schema_version"], CONSUMER_ADAPTER_VERSION)
        self.assertEqual(receipt["consumer_kind"], FROZEN_RUN_CONSUMER)
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["candidate_ranking_gate"]["input_allowed"])
        self.assertFalse(receipt["current_activation"])
        self.assertTrue(verify_frozen_run_provenance_candidate(
            receipt,
            record,
            **expectations,
        ))

    def test_frozen_run_polymorphic_identity_blocks_resealed_aliases(self) -> None:
        material = _material()
        base_identity = {
            "role": "FROZEN_TEST",
            "scenario_id": "BASE",
            "fee_rate": 0.001,
            "slippage_pct": 0.001,
            "strategy_name": "dual_ma",
            "strategy_version": "v1",
        }
        variants = {
            "REGISTERED_STRATEGY": {},
            "REGISTERED_EXECUTION_ADVERSITY": {
                "source_scenario_id": "BASE",
                "source_result_hash": material["manifest"]["result_hash"],
                "scenario_policy_hash": "1" * 64,
                "scenario_metadata": {"scenario_id": "SPREAD_X2"},
                "observation_status": "OBSERVED",
                "source_result_delta": {"total_return": -0.01},
                "source_input_dataset_hash": "2" * 64,
                "stressed_input_dataset_hash": "3" * 64,
                "unmodelled_gaps": [],
            },
            "REGISTERED_LIQUIDITY_CAPACITY_PROBE": {
                "source_scenario_id": "BASE",
                "source_benchmark_id": "ENGINE_BUY_AND_HOLD",
                "source_result_hash": material["manifest"]["result_hash"],
                "scenario_policy_hash": "4" * 64,
                "source_result_delta": {"total_return": -0.02},
                "source_input_dataset_hash": "5" * 64,
                "stressed_input_dataset_hash": "6" * 64,
                "liquidity_capacity_summary": {"status": "OBSERVED"},
                "unmodelled_gaps": [],
            },
            "FIXED_BENCHMARK": {
                "benchmark_id": "ENGINE_BUY_AND_HOLD",
                "benchmark_spec_hash": "7" * 64,
                "benchmark_params": {"mode": "long_only"},
            },
            "PREREGISTERED_VOLATILITY_TARGET_BENCHMARK": {
                "benchmark_id": "PRIOR_WINDOW_VOLATILITY_TARGET",
                "method_spec_hash": "8" * 64,
                "calibration": {"start_row": 0, "end_row": 9},
                "benchmark_params": {"target_volatility": 0.1},
            },
            "FIXED_PARAMETER_WALK_FORWARD": {
                "fold_id": "WF01",
                "method_spec_hash": "9" * 64,
                "schedule_hash": "a" * 64,
                "calibration_window": {"start_row": 0, "end_row": 9},
                "purge_window": {"start_row": 10, "end_row": 10},
                "evaluation_window": {"start_row": 11, "end_row": 20},
            },
            "PARAMETER_STABILITY_OBSERVATION": {
                "cell_id": "CELL-01",
                "segment": "VALIDATION",
                "is_center": True,
                "axes": {"fast": 10, "slow": 30},
                "params": {"fast": 10, "slow": 30},
                "params_hash": material["reproducibility"]["param_hash"],
                "cell_hash": "b" * 64,
                "method_spec_hash": "c" * 64,
                "matrix_hash": "d" * 64,
            },
        }
        for run_kind, extension_identity in variants.items():
            with self.subTest(run_kind=run_kind, phase="baseline"):
                record_identity = {
                    "run_kind": run_kind,
                    **base_identity,
                    **extension_identity,
                }
                record = {
                    **record_identity,
                    "result": material["result"],
                    "experiment_manifest": material["manifest"],
                }
                expectations = {
                    "expected_reproducibility": material["reproducibility"],
                    "expected_context": material["context"],
                    "expected_manifest_identity": material["manifest_identity"],
                    "expected_record_identity": record_identity,
                }
                receipt = build_frozen_run_provenance_candidate(
                    record,
                    **expectations,
                )
                self.assertEqual(receipt["status"], "PASS")
                self.assertTrue(verify_frozen_run_provenance_candidate(
                    receipt,
                    record,
                    **expectations,
                ))

            for field, value in extension_identity.items():
                with self.subTest(run_kind=run_kind, field=field):
                    attacked = deepcopy(record)
                    attacked[field] = _different_native(value)
                    resealed = build_frozen_run_provenance_candidate(
                        attacked,
                        **expectations,
                    )
                    self.assertEqual(resealed["status"], "BLOCK")
                    self.assertIn(
                        f"consumer_record_{field}_mismatch",
                        resealed["blockers"],
                    )
                    self.assertFalse(verify_frozen_run_provenance_candidate(
                        resealed,
                        attacked,
                        **expectations,
                    ))

        fixed_identity = {
            "run_kind": "FIXED_BENCHMARK",
            **base_identity,
            **variants["FIXED_BENCHMARK"],
        }
        fixed_record = {
            **fixed_identity,
            "result": material["result"],
            "experiment_manifest": material["manifest"],
            "unregistered_field": "alias",
        }
        with self.assertRaisesRegex(ValueError, "frozen_record_fields_invalid"):
            build_frozen_run_provenance_candidate(
                fixed_record,
                expected_reproducibility=material["reproducibility"],
                expected_context=material["context"],
                expected_manifest_identity=material["manifest_identity"],
                expected_record_identity=fixed_identity,
            )

    def test_multiple_testing_candidate_binds_observation_identity(self) -> None:
        observation = _stability_observation_material()
        material = observation["material"]
        observation_identity = observation["identity"]
        record = observation["record"]
        expectations = {
            "expected_reproducibility": material["reproducibility"],
            "expected_context": material["context"],
            "expected_manifest_identity": material["manifest_identity"],
            "expected_observation_identity": observation_identity,
        }
        receipt = build_multiple_testing_observation_provenance_candidate(
            record,
            **expectations,
        )

        self.assertEqual(
            receipt["consumer_kind"],
            MULTIPLE_TESTING_OBSERVATION_CONSUMER,
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["candidate_ranking_gate"]["input_allowed"])
        self.assertTrue(verify_multiple_testing_observation_provenance_candidate(
            receipt,
            record,
            **expectations,
        ))

    def test_cli_bundle_binds_artifact_identity_without_writing(self) -> None:
        material = _material("UNCLASSIFIED")
        report = {
            **material["result"],
            "experiment_manifest": material["manifest"],
        }
        original = deepcopy(report)
        artifact_identity = _cli_artifact_identity(material)
        expectations = {
            "expected_reproducibility": material["reproducibility"],
            "expected_context": material["context"],
            "expected_manifest_identity": material["manifest_identity"],
            "expected_artifact_identity": artifact_identity,
        }
        receipt = build_cli_report_provenance_bundle_candidate(
            report,
            **expectations,
        )

        self.assertEqual(receipt["consumer_kind"], CLI_REPORT_BUNDLE_CONSUMER)
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["runtime_write_performed"])
        self.assertEqual(report, original)
        self.assertTrue(verify_cli_report_provenance_bundle_candidate(
            receipt,
            report,
            **expectations,
        ))

    def test_each_consumer_rejects_its_record_identity_drift(self) -> None:
        frozen = _material()
        frozen_identity = {
            "run_kind": "REGISTERED_STRATEGY",
            "role": "FROZEN_TEST",
            "scenario_id": "BASE",
            "fee_rate": 0.001,
            "slippage_pct": 0.001,
            "strategy_name": "dual_ma",
            "strategy_version": "v1",
        }
        frozen_record = {
            **frozen_identity,
            "result": frozen["result"],
            "experiment_manifest": frozen["manifest"],
        }
        frozen_record["fee_rate"] = 0.25
        frozen_receipt = build_frozen_run_provenance_candidate(
            frozen_record,
            expected_reproducibility=frozen["reproducibility"],
            expected_context=frozen["context"],
            expected_manifest_identity=frozen["manifest_identity"],
            expected_record_identity=frozen_identity,
        )

        observation = _stability_observation_material()
        multiple = observation["material"]
        observation_identity = observation["identity"]
        multiple_record = deepcopy(observation["record"])
        multiple_record["params_hash"] = "0" * 64
        multiple_receipt = build_multiple_testing_observation_provenance_candidate(
            multiple_record,
            expected_reproducibility=multiple["reproducibility"],
            expected_context=multiple["context"],
            expected_manifest_identity=multiple["manifest_identity"],
            expected_observation_identity=observation_identity,
        )

        report = {
            **multiple["result"],
            "experiment_manifest": multiple["manifest"],
        }
        cli_receipt = build_cli_report_provenance_bundle_candidate(
            report,
            expected_reproducibility=multiple["reproducibility"],
            expected_context=multiple["context"],
            expected_manifest_identity=multiple["manifest_identity"],
            expected_artifact_identity={
                "artifact_id": "0" * 64,
                "prefix": "backtest_dual_ma_SYNTH-001",
                "report_schema_version": "research-json-report-v1",
                "filename": (
                    "backtest_dual_ma_SYNTH-001_" + "0" * 64 + ".json"
                ),
            },
        )

        for receipt in (frozen_receipt, multiple_receipt, cli_receipt):
            self.assertEqual(receipt["status"], "BLOCK")
            self.assertFalse(receipt["candidate_ranking_gate"]["input_allowed"])

    def test_resealed_source_manifest_does_not_cross_adapter(self) -> None:
        material = _material()
        attacked_manifest = deepcopy(material["manifest"])
        attacked_manifest["dataset_hash"] = "0" * 64
        attacked_manifest["manifest_hash"] = canonical_payload_hash({
            key: value
            for key, value in attacked_manifest.items()
            if key != "manifest_hash"
        })
        record_identity = {
            "run_kind": "REGISTERED_STRATEGY",
            "role": "FROZEN_TEST",
            "scenario_id": "BASE",
            "fee_rate": 0.001,
            "slippage_pct": 0.001,
            "strategy_name": "dual_ma",
            "strategy_version": "v1",
        }
        record = {
            **record_identity,
            "result": material["result"],
            "experiment_manifest": attacked_manifest,
        }
        receipt = build_frozen_run_provenance_candidate(
            record,
            expected_reproducibility=material["reproducibility"],
            expected_context=material["context"],
            expected_manifest_identity=material["manifest_identity"],
            expected_record_identity=record_identity,
        )

        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn(
            "manifest_dataset_hash_reproducibility_mismatch",
            receipt["blockers"],
        )

    def test_non_native_consumer_inputs_fail_before_controlled_methods(self) -> None:
        material = _material()
        calls: list[str] = []

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return super().get(key, default)

        record_identity = {
            "run_kind": "REGISTERED_STRATEGY",
            "role": "FROZEN_TEST",
            "scenario_id": "BASE",
            "fee_rate": 0.001,
            "slippage_pct": 0.001,
            "strategy_name": "dual_ma",
            "strategy_version": "v1",
        }
        with self.assertRaisesRegex(ValueError, "frozen_record_exact_native"):
            build_frozen_run_provenance_candidate(
                TrapDict({
                    **record_identity,
                    "result": material["result"],
                    "experiment_manifest": material["manifest"],
                }),
                expected_reproducibility=material["reproducibility"],
                expected_context=material["context"],
                expected_manifest_identity=material["manifest_identity"],
                expected_record_identity=record_identity,
            )
        self.assertEqual(calls, [])

    def test_adapter_activation_is_isolated_in_current_provenance_ledger(self) -> None:
        activated_source = (
            REPOSITORY_ROOT
            / "src"
            / "hakimi_research"
            / "frozen_experiment_provenance.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "experiment_provenance_consumer_adapter_v1",
            activated_source,
        )
        cli_source = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "cli.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "from hakimi_research.experiment_provenance_consumer_adapter_v1 import",
            cli_source,
        )
        current_sources = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "frozen_evaluation.py",
            REPOSITORY_ROOT / "src" / "hakimi_research" / "multiple_testing.py",
            REPOSITORY_ROOT / "src" / "hakimi_research" / "reporting.py",
        )
        for path in current_sources:
            self.assertNotIn(
                "from hakimi_research.experiment_provenance_consumer_adapter_v1 import",
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
