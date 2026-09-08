from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.experiment_manifest import (
    build_reproducible_experiment_manifest,
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)
from hakimi_research.experiment_provenance_binding_v1 import (
    MANIFEST_V2_SCHEMA_VERSION,
    PROVENANCE_BINDING_VERSION,
    build_reproducible_experiment_manifest_v2,
    verify_reproducible_experiment_manifest_v2,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _reproducibility() -> dict[str, object]:
    return {
        "run_hash": "d" * 64,
        "config_hash": "e" * 64,
        "data_hash": "f" * 64,
        "data_start": "2025-01-01T00:00:00Z",
        "data_end": "2025-02-01T00:00:00Z",
        "strategy_version": "v1",
        "random_seed": 7,
        "param_hash": "8" * 64,
    }


def _context() -> dict[str, object]:
    return {
        "git_commit_sha": "a" * 40,
        "git_worktree_clean": True,
        "dependency_lock_hash": "b" * 64,
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "random_seed": 7,
        "runtime_version": "python-test",
    }


def _source_context() -> dict[str, object]:
    return {
        **_context(),
        "evaluation_role": "FROZEN_TEST",
        "evaluation_protocol_hash": "c" * 64,
        "evaluation_protocol_verified": True,
    }


def _identity(experiment_id: str) -> dict[str, object]:
    return {
        "experiment_id": experiment_id,
        "strategy_name": "dual_ma",
        "strategy_version": "v1",
        "symbol": "SYNTH-001",
        "timeframe": "1d",
        "fee_rate": 0.001,
        "slippage_pct": 0.001,
        "evaluation_role": "FROZEN_TEST",
        "evaluation_protocol_hash": "c" * 64,
        "evaluation_protocol_verified": True,
    }


def _material() -> tuple[dict[str, object], ...]:
    reproducibility = _reproducibility()
    result = {"metric": 1.0, "reproducibility": reproducibility}
    source = build_reproducible_experiment_manifest(
        result_payload=result,
        reproducibility=reproducibility,
        strategy_name="dual_ma",
        strategy_version="v1",
        symbol="SYNTH-001",
        timeframe="1d",
        fee_rate=0.001,
        slippage_pct=0.001,
        context=_source_context(),
    )
    identity = _identity(str(source["experiment_id"]))
    envelope = build_reproducible_experiment_manifest_v2(
        source_manifest=source,
        result_payload=result,
        expected_reproducibility=reproducibility,
        expected_context=_context(),
        expected_identity=identity,
    )
    return source, result, reproducibility, _context(), identity, envelope


def _reseal_source(source: dict[str, object]) -> None:
    source["manifest_hash"] = canonical_payload_hash({
        key: value for key, value in source.items() if key != "manifest_hash"
    })


class ExperimentProvenanceBindingV1Tests(unittest.TestCase):
    def test_native_candidate_binds_all_independent_inputs(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()

        self.assertEqual(envelope["schema_version"], MANIFEST_V2_SCHEMA_VERSION)
        self.assertEqual(envelope["binding_version"], PROVENANCE_BINDING_VERSION)
        self.assertEqual(envelope["status"], "PASS")
        self.assertTrue(envelope["ranking_gate"]["input_allowed"])
        self.assertTrue(verify_reproducible_experiment_manifest_v2(
            envelope,
            source_manifest=source,
            result_payload=result,
            expected_reproducibility=reproducibility,
            expected_context=context,
            expected_identity=identity,
        ))
        for field in (
            "parameter_selection_allowed",
            "paper_authorized",
            "live_order_allowed",
            "order_entry_allowed",
            "result_is_profitability_proof",
        ):
            self.assertIs(envelope[field], False)

    def test_resealed_source_provenance_that_v1_accepts_is_rejected(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()
        attacks = {
            "dataset_hash": "0" * 64,
            "config_hash": "1" * 64,
            "source_run_hash": "2" * 64,
            "dependency_lock_hash": "3" * 64,
            "git_commit_sha": "4" * 40,
            "strategy_name": "foreign_strategy",
            "symbol": "FOREIGN-001",
            "timeframe": "5m",
            "fee_model": {"kind": "proportional", "rate": "0.25"},
            "evaluation_protocol_hash": "5" * 64,
        }
        for field, replacement in attacks.items():
            with self.subTest(field=field):
                attacked = deepcopy(source)
                attacked[field] = replacement
                _reseal_source(attacked)
                self.assertTrue(
                    verify_reproducible_experiment_manifest(attacked, result),
                    field,
                )
                rejected = build_reproducible_experiment_manifest_v2(
                    source_manifest=attacked,
                    result_payload=result,
                    expected_reproducibility=reproducibility,
                    expected_context=context,
                    expected_identity=identity,
                )
                self.assertEqual(rejected["status"], "BLOCK", field)
                self.assertFalse(verify_reproducible_experiment_manifest_v2(
                    envelope,
                    source_manifest=attacked,
                    result_payload=result,
                    expected_reproducibility=reproducibility,
                    expected_context=context,
                    expected_identity=identity,
                ), field)

    def test_result_reproducibility_and_expected_reproducibility_are_both_bound(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()
        result_attack = deepcopy(result)
        result_attack["reproducibility"]["data_hash"] = "0" * 64
        expected_attack = deepcopy(reproducibility)
        expected_attack["config_hash"] = "1" * 64

        for attacked_result, attacked_expected in (
            (result_attack, reproducibility),
            (result, expected_attack),
        ):
            self.assertFalse(verify_reproducible_experiment_manifest_v2(
                envelope,
                source_manifest=source,
                result_payload=attacked_result,
                expected_reproducibility=attacked_expected,
                expected_context=context,
                expected_identity=identity,
            ))

    def test_context_and_identity_are_consumer_owned(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()
        context_attack = deepcopy(context)
        context_attack["dependency_lock_hash"] = "0" * 64
        identity_attack = deepcopy(identity)
        identity_attack["slippage_pct"] = 0.25

        self.assertFalse(verify_reproducible_experiment_manifest_v2(
            envelope,
            source_manifest=source,
            result_payload=result,
            expected_reproducibility=reproducibility,
            expected_context=context_attack,
            expected_identity=identity,
        ))
        self.assertFalse(verify_reproducible_experiment_manifest_v2(
            envelope,
            source_manifest=source,
            result_payload=result,
            expected_reproducibility=reproducibility,
            expected_context=context,
            expected_identity=identity_attack,
        ))

    def test_protocol_bound_nonranking_roles_remain_nonrankable(self) -> None:
        reproducibility = _reproducibility()
        result = {"metric": 1.0, "reproducibility": reproducibility}
        for role in ("TRAIN", "UNCLASSIFIED"):
            with self.subTest(role=role):
                source_context = {
                    **_context(),
                    "evaluation_role": role,
                    "evaluation_protocol_hash": "c" * 64,
                    "evaluation_protocol_verified": True,
                }
                source = build_reproducible_experiment_manifest(
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
                identity = {
                    **_identity(str(source["experiment_id"])),
                    "evaluation_role": role,
                    "evaluation_protocol_hash": "c" * 64,
                    "evaluation_protocol_verified": True,
                }
                envelope = build_reproducible_experiment_manifest_v2(
                    source_manifest=source,
                    result_payload=result,
                    expected_reproducibility=reproducibility,
                    expected_context=_context(),
                    expected_identity=identity,
                )

                self.assertEqual(envelope["status"], "PASS")
                self.assertFalse(envelope["ranking_gate"]["input_allowed"])
                self.assertTrue(verify_reproducible_experiment_manifest_v2(
                    envelope,
                    source_manifest=source,
                    result_payload=result,
                    expected_reproducibility=reproducibility,
                    expected_context=_context(),
                    expected_identity=identity,
                ))

    def test_resealed_v2_envelope_cannot_override_consumer_inputs(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()
        attacked = deepcopy(envelope)
        attacked["context_hash"] = "0" * 64
        attacked["manifest_hash"] = canonical_payload_hash({
            key: value for key, value in attacked.items() if key != "manifest_hash"
        })

        self.assertFalse(verify_reproducible_experiment_manifest_v2(
            attacked,
            source_manifest=source,
            result_payload=result,
            expected_reproducibility=reproducibility,
            expected_context=context,
            expected_identity=identity,
        ))

    def test_non_native_subclasses_fail_before_controlled_methods(self) -> None:
        source, result, reproducibility, context, identity, envelope = _material()
        calls: list[str] = []

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return super().get(key, default)

        class TrapText(str):
            def strip(self, chars: str | None = None) -> str:
                calls.append("text.strip")
                return str(self)

        with self.assertRaisesRegex(ValueError, "source_manifest_exact_native"):
            build_reproducible_experiment_manifest_v2(
                source_manifest=TrapDict(source),
                result_payload=result,
                expected_reproducibility=reproducibility,
                expected_context=context,
                expected_identity=identity,
            )
        hostile_context = deepcopy(context)
        hostile_context["runtime_version"] = TrapText("python-test")
        self.assertFalse(verify_reproducible_experiment_manifest_v2(
            envelope,
            source_manifest=source,
            result_payload=result,
            expected_reproducibility=reproducibility,
            expected_context=hostile_context,
            expected_identity=identity,
        ))
        self.assertEqual(calls, [])

    def test_binding_activation_is_transitive_through_current_ledger(self) -> None:
        ledger_source = (
            REPOSITORY_ROOT
            / "src"
            / "hakimi_research"
            / "frozen_experiment_provenance.py"
        ).read_text(encoding="utf-8")
        adapter_source = (
            REPOSITORY_ROOT
            / "src"
            / "hakimi_research"
            / "experiment_provenance_consumer_adapter_v1.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "experiment_provenance_consumer_adapter_v1",
            ledger_source,
        )
        self.assertIn("experiment_provenance_binding_v1", adapter_source)
        current_sources = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "experiment_manifest.py",
            REPOSITORY_ROOT / "src" / "hakimi_research" / "frozen_evaluation.py",
            REPOSITORY_ROOT / "src" / "hakimi_research" / "multiple_testing.py",
            REPOSITORY_ROOT / "src" / "hakimi_research" / "deterministic_frozen_benchmark.py",
        )
        for path in current_sources:
            self.assertNotIn(
                "from hakimi_research.experiment_provenance_binding_v1 import",
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
