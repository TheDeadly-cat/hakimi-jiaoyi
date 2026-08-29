from __future__ import annotations

import base64
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import unittest

from exchange_terminal.services import strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as lifecycle_replay
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1 as persistence_binding
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1 as lineage_contract
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_history_coverage_gate_v1 as coverage_contract
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1 as persistence_receipts
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1 as lineage_fixture_module


FIXTURE_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-real-"
    "three-segment-synthetic-conformance-v1"
)
UPSTREAM_FIXTURE_PATCH_TARGETS = (
    "strategy_correlation_uncertainty_audit.verify_correlation_matrix_replay",
    "calendar_session_verifier_v1.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1",
    "provider_identity_assertion_verifier_v1.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1",
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{label} did not produce a document")
    return value


def _build_tree_five_context(
    fixture: unittest.TestCase,
    context_four: dict[str, object],
) -> dict[str, object]:
    replay_fixture = fixture.binding.persistence.source.source
    context_five = deepcopy(context_four)
    lifecycle_bundles = context_five["lifecycle_bundles"]
    receipt_hashes = [
        bundle["lifecycle_receipt"]["lifecycle_receipt_hash"]
        for bundle in lifecycle_bundles
    ]
    leaves = [
        lifecycle_replay.hash_lifecycle_replay_leaf_v1(receipt_hash)
        for receipt_hash in receipt_hashes
    ]
    anchor_root = fixture.binding.context["replay_preregistration"][
        "expected_replay_bindings"
    ][0]["previous_checkpoint_root_hash"]
    extra_leaf_four = lifecycle_replay.hash_lifecycle_replay_leaf_v1(
        _hash("lineage-extra-lifecycle-receipt")
    )
    left_root = lifecycle_replay.hash_lifecycle_replay_node_v1(
        anchor_root, leaves[0]
    )
    right_root = lifecycle_replay.hash_lifecycle_replay_node_v1(
        leaves[1], extra_leaf_four
    )
    root_four = lifecycle_replay.hash_lifecycle_replay_node_v1(
        left_root, right_root
    )
    expected_root_four = context_four["replay_preregistration"][
        "expected_replay_bindings"
    ][0]["checkpoint_root_hash"]
    if root_four != expected_root_four:
        raise AssertionError("tree-four root drifted from the reviewed fixture")

    extra_leaf_five = lifecycle_replay.hash_lifecycle_replay_leaf_v1(
        _hash("lineage-extra-lifecycle-receipt-2")
    )
    root_five = lifecycle_replay.hash_lifecycle_replay_node_v1(
        root_four, extra_leaf_five
    )
    consistency_proof = [extra_leaf_five]
    if not lifecycle_replay._verify_consistency(
        old_size=4,
        new_size=5,
        old_root=root_four,
        new_root=root_five,
        proof=consistency_proof,
    ):
        raise AssertionError("tree-four to tree-five consistency proof invalid")

    replay_bundles: list[dict[str, object]] = []
    replay_bindings: list[dict[str, object]] = []
    for position, (window_id, lifecycle_bundle, prior_bundle) in enumerate(
        zip(
            context_five["windows"],
            lifecycle_bundles,
            context_four["replay_bundles"],
            strict=True,
        )
    ):
        registration = prior_bundle["replay_registration"]
        prior_audit = prior_bundle["occurrence_audit"]
        pinned = lifecycle_replay.build_pinned_lifecycle_replay_checkpoint_v1(
            registration,
            tree_size=4,
            root_hash=root_four,
            checkpoint_hash=_hash("lineage-tree-four-checkpoint"),
        )
        unsigned_checkpoint = (
            lifecycle_replay.build_unsigned_lifecycle_replay_checkpoint_v1(
                registration,
                pinned,
                tree_size=5,
                root_hash=root_five,
                issued_at_utc=prior_bundle["checkpoint"]["issued_at_utc"],
            )
        )
        checkpoint_signature = replay_fixture.registry_private_key.sign(
            bytes.fromhex(unsigned_checkpoint["receipt_content_sha256"])
        )
        checkpoint = lifecycle_replay.assemble_lifecycle_replay_checkpoint_v1(
            unsigned_checkpoint,
            base64.b64encode(checkpoint_signature).decode("ascii"),
        )
        inclusion_proof = (
            [anchor_root, right_root, extra_leaf_five]
            if position == 0
            else [extra_leaf_four, left_root, extra_leaf_five]
        )
        if not lifecycle_replay._verify_inclusion(
            lifecycle_receipt_hash=receipt_hashes[position],
            leaf_index=position + 1,
            tree_size=5,
            root_hash=root_five,
            proof=inclusion_proof,
        ):
            raise AssertionError(f"window {position} tree-five inclusion proof invalid")
        unsigned_audit = (
            lifecycle_replay.build_unsigned_lifecycle_replay_occurrence_audit_v1(
                registration,
                checkpoint,
                inclusion_proof,
                consistency_proof,
                occurrence_leaf_index=position + 1,
                scan_start_index=0,
                scan_end_index_exclusive=5,
                index_snapshot_record_count=5,
                occurrence_count=1,
                occurrence_leaf_indices=[position + 1],
                index_snapshot_root_hash=_hash(
                    "lineage-tree-five-index-snapshot"
                ),
                scan_completed_at_utc=prior_audit["scan_completed_at_utc"],
                audit_issued_at_utc=prior_audit["audit_issued_at_utc"],
                reference_time_utc=prior_audit["reference_time_utc"],
            )
        )
        audit_signature = replay_fixture.auditor_private_key.sign(
            bytes.fromhex(unsigned_audit["receipt_content_sha256"])
        )
        audit = lifecycle_replay.assemble_lifecycle_replay_occurrence_audit_v1(
            unsigned_audit,
            base64.b64encode(audit_signature).decode("ascii"),
        )
        lifecycle_context = replay_fixture._lifecycle_context(lifecycle_bundle)
        replay_gate = (
            lifecycle_replay.evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
                lifecycle_bundle["lifecycle_gate_document"],
                lifecycle_context,
                registration,
                replay_fixture.registry_public_key_base64,
                replay_fixture.auditor_public_key_base64,
                pinned,
                checkpoint,
                inclusion_proof,
                consistency_proof,
                audit,
                expected_registration_hash=registration["registration_hash"],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
                reference_time_utc=prior_audit["reference_time_utc"],
            )
        )
        if replay_gate["status"] != "PASS":
            raise AssertionError(f"window {position} tree-five replay gate failed")
        bundle = {
            "checkpoint": checkpoint,
            "consistency_proof": consistency_proof,
            "inclusion_proof": inclusion_proof,
            "occurrence_audit": audit,
            "occurrence_auditor_public_key_base64": replay_fixture.auditor_public_key_base64,
            "pinned_checkpoint": pinned,
            "replay_gate_document": replay_gate,
            "replay_registration": registration,
            "replay_registry_public_key_base64": replay_fixture.registry_public_key_base64,
            "window_id": window_id,
        }
        replay_bundles.append(bundle)
        replay_bindings.append(
            replay_fixture._expected_binding(
                window_id, lifecycle_bundle, bundle
            )
        )

    replay_preregistration = replay_fixture._preregister(
        context_five, replay_bindings
    )
    _require_dict(replay_preregistration, "tree-five replay preregistration")
    context_five["replay_bundles"] = replay_bundles
    context_five["replay_bindings"] = replay_bindings
    context_five["replay_preregistration"] = replay_preregistration
    source_gate = replay_fixture._evaluate(context_five)
    if source_gate["status"] != "PASS" or source_gate["summary"][
        "checkpoint_tree_size"
    ] != 5:
        raise AssertionError("tree-five common source gate failed")
    return context_five


def _build_tree_five_segment(
    fixture: unittest.TestCase,
    context_five: dict[str, object],
    previous_segment: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    replay_fixture = fixture.binding.persistence.source.source
    registration_fixture = fixture.binding.persistence.source
    persistence_fixture = fixture.binding.persistence
    source_gate = replay_fixture._evaluate(context_five)
    original_context = registration_fixture.context
    registration_fixture.context = context_five
    try:
        configuration = registration_fixture._configuration()
        registration = registration_fixture._build(configuration=configuration)
    finally:
        registration_fixture.context = original_context
    registration = _require_dict(registration, "tree-five persistence registration")
    asset = persistence_receipts.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
        registration,
        asset_created_at_utc="2026-12-20T02:51:00Z",
        previous_persisted_asset_hash=previous_segment["persistence_inputs"][
            "expected_asset_hash"
        ],
    )
    asset = _require_dict(asset, "tree-five persistence asset")
    unsigned_write = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
        registration,
        asset,
        session_id="LINEAGE-WRITE-SESSION-03",
        written_at_utc="2026-12-20T02:54:00Z",
    )
    unsigned_write = _require_dict(unsigned_write, "tree-five unsigned write")
    write_receipt = persistence_fixture._sign(
        unsigned_write,
        persistence_fixture.private_key,
        persistence_receipts.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
    )
    unsigned_reopen = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
        registration,
        asset,
        write_receipt,
        session_id="LINEAGE-REOPEN-SESSION-03",
        reopened_at_utc="2026-12-20T02:57:00Z",
    )
    unsigned_reopen = _require_dict(unsigned_reopen, "tree-five unsigned reopen")
    reopen_receipt = persistence_fixture._sign(
        unsigned_reopen,
        persistence_fixture.private_key,
        persistence_receipts.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
    )
    evaluation = persistence_receipts.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
        registration,
        context_five["replay_preregistration"],
        context_five["lifecycle_preregistration"],
        context_five["binding_preregistration"],
        context_five["overlap_preregistration"],
        context_five["multi_preregistration"],
        configuration,
        persistence_fixture.public_key_base64,
        asset,
        write_receipt,
        reopen_receipt,
        expected_registration_hash=registration["registration_hash"],
        expected_asset_hash=asset["asset_hash"],
        expected_write_receipt_hash=write_receipt["write_receipt_hash"],
        expected_reopen_receipt_hash=reopen_receipt["reopen_receipt_hash"],
    )
    if evaluation["status"] != "PASS":
        raise AssertionError("tree-five persistence receipt verification failed")
    source_inputs = fixture.binding._source_inputs(context_five, source_gate)
    persistence_inputs = fixture.binding._persistence_inputs(
        registration,
        configuration,
        asset,
        write_receipt,
        reopen_receipt,
        evaluation,
    )
    binding_gate = persistence_binding.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
        source_gate,
        source_inputs,
        evaluation,
        persistence_inputs,
    )
    if binding_gate["status"] != "PASS":
        raise AssertionError("tree-five persistence binding gate failed")
    segment = fixture._segment(
        binding_gate,
        source_gate,
        source_inputs,
        evaluation,
        persistence_inputs,
    )
    gate = fixture._evaluate(segment, previous_segment)
    if gate["status"] != "PASS":
        raise AssertionError("tree-five persisted-checkpoint lineage gate failed")
    return segment, gate


@contextmanager
def real_three_segment_fixture_v1():
    fixture = lineage_fixture_module.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceLineageGateV1Tests()
    fixture.setUp()
    try:
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
        context_five = _build_tree_five_context(fixture, context_four)
        segment_five, gate_five = _build_tree_five_segment(
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
        anchor_asset = segment_three["persistence_inputs"]["checkpoint_asset"]
        registration = {
            "schema_version": coverage_contract.REGISTRATION_SCHEMA_VERSION,
            "history_id": "real-three-segment-synthetic-history-v1",
            "source_gate_schema_version": lineage_contract.SCHEMA_VERSION,
            "source_gate_static_fingerprint": lineage_contract.STATIC_FINGERPRINT,
            "source_gate_implementation_sha256": coverage_contract.SOURCE_IMPLEMENTATION_SHA256,
            "anchor_gate_hash": gate_three["gate_hash"],
            "anchor_asset_hash": gate_three["source"]["current_asset_hash"],
            "expected_study_identity_hash": gate_three["source"][
                "study_identity_hash"
            ],
            "expected_window_order_hash": gate_three["source"]["window_order_hash"],
            "expected_replay_registry_id": anchor_asset[
                "source_replay_registry_id"
            ],
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
            "upstream_fixture_patch_targets": UPSTREAM_FIXTURE_PATCH_TARGETS,
            "registration": registration,
            "registration_receipt": registration_receipt,
            "lineage_items": lineage_items,
            "coverage_gate": coverage_gate,
        }
    finally:
        fixture.doCleanups()


class StrategyCorrelationPersistedCheckpointHistoryCoverageRealSourceIntegrationV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_context = real_three_segment_fixture_v1()
        cls.material = cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_context.__exit__(None, None, None)

    def test_three_real_source_lineage_gates_form_tree_three_to_five(self) -> None:
        gates = [item["gate_document"] for item in self.material["lineage_items"]]
        self.assertEqual([gate["status"] for gate in gates], ["PASS"] * 3)
        self.assertEqual(
            [gate["summary"]["current_checkpoint_tree_size"] for gate in gates],
            [3, 4, 5],
        )
        self.assertEqual(
            [gate["lineage_mode"] for gate in gates],
            ["REGISTERED_SOURCE_PIN", "PREVIOUS_PERSISTED_ASSET", "PREVIOUS_PERSISTED_ASSET"],
        )

    def test_every_adr0356_gate_reverifies_under_declared_fixture_seams(self) -> None:
        for item in self.material["lineage_items"]:
            self.assertTrue(
                lineage_contract.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
                    item["gate_document"],
                    item["current_segment"],
                    item["previous_segment"],
                    expected_gate_hash=item["expected_gate_hash"],
                )
            )

    def test_upstream_fixture_patch_boundary_is_explicit(self) -> None:
        self.assertEqual(
            self.material["upstream_fixture_patch_targets"],
            UPSTREAM_FIXTURE_PATCH_TARGETS,
        )

    def test_preregistered_real_source_prefix_passes(self) -> None:
        self.assertEqual(
            self.material["registration_receipt"]["status"],
            coverage_contract.REGISTERED_STATUS,
        )
        gate = self.material["coverage_gate"]
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["reason_code"], coverage_contract.PASS_REASON)
        self.assertEqual(gate["summary"]["verified_segment_count"], 3)

    def test_result_remains_bounded_and_fail_closed(self) -> None:
        gate = self.material["coverage_gate"]
        self.assertTrue(gate["facts"]["bounded_history_prefix_only"])
        self.assertFalse(
            gate["facts"]["complete_persisted_checkpoint_history_verified"]
        )
        self.assertTrue(all(value is False for value in gate["authority"].values()))

    def _evaluate(self, items: list[dict[str, object]]) -> dict[str, object]:
        return coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=self.material["registration"],
            registration_receipt=self.material["registration_receipt"],
            lineage_items=items,
        )

    def test_missing_middle_segment_is_unknown(self) -> None:
        items = deepcopy(self.material["lineage_items"])
        self.assertEqual(self._evaluate([items[0], items[2]])["status"], "UNKNOWN")

    def test_real_previous_segment_handoff_drift_is_unknown(self) -> None:
        items = deepcopy(self.material["lineage_items"])
        items[2]["previous_segment"]["drift"] = True
        self.assertEqual(self._evaluate(items)["status"], "UNKNOWN")

    def test_real_asset_hash_handoff_drift_is_unknown(self) -> None:
        items = deepcopy(self.material["lineage_items"])
        items[2]["current_segment"]["persistence_inputs"]["checkpoint_asset"][
            "previous_persisted_asset_hash"
        ] = _hash("wrong-real-previous-asset")
        self.assertEqual(self._evaluate(items)["status"], "UNKNOWN")

    def test_real_tree_size_skip_is_unknown(self) -> None:
        items = deepcopy(self.material["lineage_items"])
        items[2]["gate_document"]["summary"]["current_checkpoint_tree_size"] = 6
        self.assertEqual(self._evaluate(items)["status"], "UNKNOWN")

    def test_resealed_consumer_authority_promotion_is_rejected(self) -> None:
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
