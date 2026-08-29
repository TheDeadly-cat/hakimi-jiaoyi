from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import Mock
import unittest

from exchange_terminal.services import strategy_correlation_uncertainty_audit as correlation_replay_contract
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1 as lineage_contract
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_history_coverage_gate_v1 as coverage_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_persisted_checkpoint_history_coverage_real_source_integration_v1 as adr0358_fixture
from tests import test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1 as lineage_fixture_module


FIXTURE_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-"
    "correlation-replay-seam-closure-v1"
)
REMOVED_PATCH_TARGET = (
    "strategy_correlation_uncertainty_audit.verify_correlation_matrix_replay"
)
REMAINING_PATCH_TARGETS = (
    "strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1",
    "strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1",
)


def _patch_target_name(patcher: object) -> str:
    target = patcher.getter()
    module_name = target.__name__.rsplit(".", 1)[-1]
    return f"{module_name}.{patcher.attribute}"


def _remove_redundant_correlation_replay_patch(
    fixture: unittest.TestCase,
) -> dict[str, object]:
    provider_fixture = fixture.binding.persistence.source.source.source.source
    matches: list[tuple[object, object]] = []
    for entry in list(provider_fixture._cleanups):
        callback = entry[0]
        patcher = getattr(callback, "__self__", None)
        if patcher is None:
            continue
        target = patcher.getter()
        if (
            target is correlation_replay_contract
            and patcher.attribute == "verify_correlation_matrix_replay"
        ):
            matches.append((entry, patcher))
    if len(matches) != 1:
        raise AssertionError("expected exactly one correlation replay patch")
    entry, patcher = matches[0]
    mocked = getattr(correlation_replay_contract, patcher.attribute)
    original = patcher.temp_original
    captured_calls = list(mocked.call_args_list)
    original_results = [
        original(*call.args, **call.kwargs) for call in captured_calls
    ]
    if not captured_calls or any(
        result.get("status") != "PASS"
        for result in original_results
        if isinstance(result, dict)
    ):
        raise AssertionError("captured correlation replay call did not pass original verifier")
    if any(not isinstance(result, dict) for result in original_results):
        raise AssertionError("correlation replay original result shape invalid")
    patcher.stop()
    provider_fixture._cleanups.remove(entry)
    if isinstance(
        correlation_replay_contract.verify_correlation_matrix_replay, Mock
    ):
        raise AssertionError("correlation replay verifier remained mocked")
    remaining = tuple(
        _patch_target_name(getattr(cleanup[0], "__self__"))
        for cleanup in provider_fixture._cleanups
    )
    if remaining != REMAINING_PATCH_TARGETS:
        raise AssertionError("remaining upstream fixture seams drifted")
    return {
        "captured_original_pass_count": len(captured_calls),
        "removed_patch_target": REMOVED_PATCH_TARGET,
        "remaining_patch_targets": remaining,
        "correlation_replay_verifier_is_original": True,
    }


def _coverage_registration(
    segment_three: dict[str, object],
    gate_three: dict[str, object],
) -> dict[str, object]:
    anchor_asset = segment_three["persistence_inputs"]["checkpoint_asset"]
    return {
        "schema_version": coverage_contract.REGISTRATION_SCHEMA_VERSION,
        "history_id": "two-seam-real-three-segment-history-v1",
        "source_gate_schema_version": lineage_contract.SCHEMA_VERSION,
        "source_gate_static_fingerprint": lineage_contract.STATIC_FINGERPRINT,
        "source_gate_implementation_sha256": coverage_contract.SOURCE_IMPLEMENTATION_SHA256,
        "anchor_gate_hash": gate_three["gate_hash"],
        "anchor_asset_hash": gate_three["source"]["current_asset_hash"],
        "expected_study_identity_hash": gate_three["source"][
            "study_identity_hash"
        ],
        "expected_window_order_hash": gate_three["source"]["window_order_hash"],
        "expected_replay_registry_id": anchor_asset["source_replay_registry_id"],
        "expected_replay_registry_namespace": anchor_asset[
            "source_replay_registry_namespace"
        ],
        "expected_persistence_configuration_hash": coverage_contract.canonical_value_sha256_v1(
            segment_three["persistence_inputs"]["persistence_configuration"]
        ),
        "anchor_checkpoint_tree_size": 3,
        "final_checkpoint_tree_size": 5,
        "expected_segment_count": 3,
        "checkpoint_tree_step": 1,
        "registered_at_utc": "2026-12-20T02:30:00Z",
        "future_coverage_not_before_utc": "2026-12-20T02:46:00Z",
        "future_coverage_not_after_utc": "2026-12-20T02:59:00Z",
        "max_future_asset_time_gap_seconds": 1500,
        "checkpoint_sequence_policy": coverage_contract.CHECKPOINT_SEQUENCE_POLICY,
        "segment_sequence_policy": coverage_contract.SEGMENT_SEQUENCE_POLICY,
        "asset_handoff_policy": coverage_contract.ASSET_HANDOFF_POLICY,
        "identity_stability_policy": coverage_contract.IDENTITY_STABILITY_POLICY,
        "time_policy": coverage_contract.TIME_POLICY,
    }


@contextmanager
def two_seam_three_segment_fixture_v1():
    fixture = lineage_fixture_module.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceLineageGateV1Tests()
    fixture.setUp()
    try:
        seam_evidence = _remove_redundant_correlation_replay_patch(fixture)
        segment_three = deepcopy(fixture.previous_segment)
        gate_three = fixture._evaluate(segment_three, None)
        context_four = fixture._extended_context()
        segment_four = fixture._segment_for_context(
            context_four,
            previous_asset_hash=segment_three["persistence_inputs"][
                "expected_asset_hash"
            ],
        )
        gate_four = fixture._evaluate(segment_four, segment_three)
        context_five = adr0358_fixture._build_tree_five_context(
            fixture, context_four
        )
        segment_five, gate_five = adr0358_fixture._build_tree_five_segment(
            fixture, context_five, segment_four
        )
        lineage_items = [
            {
                "gate_document": gate_three,
                "current_segment": segment_three,
                "previous_segment": None,
                "expected_gate_hash": gate_three["gate_hash"],
            },
            {
                "gate_document": gate_four,
                "current_segment": segment_four,
                "previous_segment": deepcopy(segment_three),
                "expected_gate_hash": gate_four["gate_hash"],
            },
            {
                "gate_document": gate_five,
                "current_segment": segment_five,
                "previous_segment": deepcopy(segment_four),
                "expected_gate_hash": gate_five["gate_hash"],
            },
        ]
        registration = _coverage_registration(segment_three, gate_three)
        registration_receipt = coverage_contract.build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
            registration
        )
        coverage_gate = coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=registration,
            registration_receipt=registration_receipt,
            lineage_items=lineage_items,
        )
        yield {
            "fixture_fingerprint": FIXTURE_FINGERPRINT,
            **seam_evidence,
            "registration": registration,
            "registration_receipt": registration_receipt,
            "lineage_items": lineage_items,
            "coverage_gate": coverage_gate,
        }
    finally:
        fixture.doCleanups()


class StrategyCorrelationPersistedCheckpointHistoryCoverageCorrelationReplaySeamClosureV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_context = two_seam_three_segment_fixture_v1()
        cls.material = cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_context.__exit__(None, None, None)

    def test_captured_calls_pass_original_correlation_replay_verifier(self) -> None:
        self.assertGreater(self.material["captured_original_pass_count"], 0)
        self.assertTrue(self.material["correlation_replay_verifier_is_original"])
        self.assertEqual(
            self.material["removed_patch_target"], REMOVED_PATCH_TARGET
        )

    def test_exactly_two_upstream_fixture_seams_remain(self) -> None:
        self.assertEqual(
            self.material["remaining_patch_targets"], REMAINING_PATCH_TARGETS
        )
        self.assertEqual(len(REMAINING_PATCH_TARGETS), 2)

    def test_three_lineage_gates_pass_after_seam_removal(self) -> None:
        gates = [
            item["gate_document"] for item in self.material["lineage_items"]
        ]
        self.assertEqual([gate["status"] for gate in gates], ["PASS"] * 3)
        self.assertEqual(
            [gate["summary"]["current_checkpoint_tree_size"] for gate in gates],
            [3, 4, 5],
        )

    def test_all_adr0356_documents_reverify_with_original_correlation_replay(self) -> None:
        self.assertFalse(
            isinstance(
                correlation_replay_contract.verify_correlation_matrix_replay,
                Mock,
            )
        )
        for item in self.material["lineage_items"]:
            self.assertTrue(
                lineage_contract.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
                    item["gate_document"],
                    item["current_segment"],
                    item["previous_segment"],
                    expected_gate_hash=item["expected_gate_hash"],
                )
            )

    def test_coverage_passes_and_remains_bounded(self) -> None:
        gate = self.material["coverage_gate"]
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["summary"]["verified_segment_count"], 3)
        self.assertTrue(gate["facts"]["bounded_history_prefix_only"])
        self.assertFalse(
            gate["facts"]["complete_persisted_checkpoint_history_verified"]
        )
        self.assertTrue(all(value is False for value in gate["authority"].values()))

    def test_missing_middle_segment_is_unknown(self) -> None:
        items = deepcopy(self.material["lineage_items"])
        result = coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=self.material["registration"],
            registration_receipt=self.material["registration_receipt"],
            lineage_items=[items[0], items[2]],
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        gate = self.material["coverage_gate"]
        tampered = deepcopy(gate)
        tampered["authority"]["candidate_activation_allowed"] = True
        tampered.pop("gate_hash")
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        kwargs = {
            "registration": self.material["registration"],
            "registration_receipt": self.material["registration_receipt"],
            "lineage_items": self.material["lineage_items"],
        }
        self.assertTrue(
            coverage_contract.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                gate,
                expected_gate_hash=gate["gate_hash"],
                **kwargs,
            )
        )
        self.assertFalse(
            coverage_contract.verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
                tampered,
                expected_gate_hash=tampered["gate_hash"],
                **kwargs,
            )
        )


if __name__ == "__main__":
    unittest.main()
