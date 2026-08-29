from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1
    as lifecycle_replay,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1
    as persistence_binding,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1
    as persistence_receipts,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1
    as persistence_binding_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceLineageGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.binding = persistence_binding_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceBindingGateV1Tests(
            methodName="test_valid_composition_passes_locally"
        )
        self.binding.setUp()
        self.addCleanup(self.binding.doCleanups)
        self.previous_segment = self._base_segment()

    @staticmethod
    def _segment(
        binding_gate: dict[str, object],
        source_gate: dict[str, object],
        source_inputs: dict[str, object],
        persistence_evaluation: dict[str, object],
        persistence_inputs: dict[str, object],
    ) -> dict[str, object]:
        return {
            "binding_gate_document": binding_gate,
            "expected_binding_gate_hash": binding_gate["gate_hash"],
            "persistence_evaluation": persistence_evaluation,
            "persistence_inputs": persistence_inputs,
            "source_gate_document": source_gate,
            "source_inputs": source_inputs,
        }

    def _base_segment(self) -> dict[str, object]:
        gate = self.binding._evaluate()
        return self._segment(
            gate,
            self.binding.source_gate,
            self.binding.source_inputs,
            self.binding.persistence_evaluation,
            self.binding.persistence_inputs,
        )

    def _extended_context(self) -> dict[str, object]:
        fixture = self.binding.persistence.source.source
        context = deepcopy(self.binding.context)
        lifecycle_bundles = context["lifecycle_bundles"]
        source_hashes = [
            bundle["lifecycle_receipt"]["lifecycle_receipt_hash"]
            for bundle in lifecycle_bundles
        ]
        previous_common = context["replay_preregistration"][
            "expected_replay_bindings"
        ][0]
        anchor_root = previous_common["previous_checkpoint_root_hash"]
        previous_root = previous_common["checkpoint_root_hash"]
        leaves = [
            lifecycle_replay.hash_lifecycle_replay_leaf_v1(value)
            for value in source_hashes
        ]
        extra_leaf = lifecycle_replay.hash_lifecycle_replay_leaf_v1(
            _hash("lineage-extra-lifecycle-receipt")
        )
        left = lifecycle_replay.hash_lifecycle_replay_node_v1(
            anchor_root,
            leaves[0],
        )
        right = lifecycle_replay.hash_lifecycle_replay_node_v1(
            leaves[1],
            extra_leaf,
        )
        current_root = lifecycle_replay.hash_lifecycle_replay_node_v1(
            left,
            right,
        )
        consistency = [leaves[1], extra_leaf, left]
        bundles = []
        bindings = []
        for position, (window_id, lifecycle_bundle, prior_bundle) in enumerate(
            zip(
                context["windows"],
                lifecycle_bundles,
                context["replay_bundles"],
                strict=True,
            )
        ):
            registration = prior_bundle["replay_registration"]
            pinned = lifecycle_replay.build_pinned_lifecycle_replay_checkpoint_v1(
                registration,
                tree_size=3,
                root_hash=previous_root,
                checkpoint_hash=_hash("lineage-tree-three-checkpoint"),
            )
            unsigned_checkpoint = lifecycle_replay.build_unsigned_lifecycle_replay_checkpoint_v1(
                registration,
                pinned,
                tree_size=4,
                root_hash=current_root,
                issued_at_utc="2026-12-20T02:45:00Z",
            )
            checkpoint_signature = fixture.registry_private_key.sign(
                bytes.fromhex(unsigned_checkpoint["receipt_content_sha256"])
            )
            checkpoint = lifecycle_replay.assemble_lifecycle_replay_checkpoint_v1(
                unsigned_checkpoint,
                base64.b64encode(checkpoint_signature).decode("ascii"),
            )
            inclusion = (
                [anchor_root, right]
                if position == 0
                else [extra_leaf, left]
            )
            unsigned_audit = lifecycle_replay.build_unsigned_lifecycle_replay_occurrence_audit_v1(
                registration,
                checkpoint,
                inclusion,
                consistency,
                occurrence_leaf_index=position + 1,
                scan_start_index=0,
                scan_end_index_exclusive=4,
                index_snapshot_record_count=4,
                occurrence_count=1,
                occurrence_leaf_indices=[position + 1],
                index_snapshot_root_hash=_hash(
                    "lineage-tree-four-index-snapshot"
                ),
                scan_completed_at_utc="2026-12-20T02:50:00Z",
                audit_issued_at_utc="2026-12-20T02:55:00Z",
                reference_time_utc="2026-12-20T03:00:00Z",
            )
            audit_signature = fixture.auditor_private_key.sign(
                bytes.fromhex(unsigned_audit["receipt_content_sha256"])
            )
            audit = lifecycle_replay.assemble_lifecycle_replay_occurrence_audit_v1(
                unsigned_audit,
                base64.b64encode(audit_signature).decode("ascii"),
            )
            lifecycle_context = fixture._lifecycle_context(lifecycle_bundle)
            replay_gate = lifecycle_replay.evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
                lifecycle_bundle["lifecycle_gate_document"],
                lifecycle_context,
                registration,
                fixture.registry_public_key_base64,
                fixture.auditor_public_key_base64,
                pinned,
                checkpoint,
                inclusion,
                consistency,
                audit,
                expected_registration_hash=registration["registration_hash"],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
                reference_time_utc="2026-12-20T03:00:00Z",
            )
            bundle = {
                "checkpoint": checkpoint,
                "consistency_proof": consistency,
                "inclusion_proof": inclusion,
                "occurrence_audit": audit,
                "occurrence_auditor_public_key_base64": (
                    fixture.auditor_public_key_base64
                ),
                "pinned_checkpoint": pinned,
                "replay_gate_document": replay_gate,
                "replay_registration": registration,
                "replay_registry_public_key_base64": (
                    fixture.registry_public_key_base64
                ),
                "window_id": window_id,
            }
            bundles.append(bundle)
            bindings.append(
                fixture._expected_binding(
                    window_id,
                    lifecycle_bundle,
                    bundle,
                )
            )
        preregistration = fixture._preregister(context, bindings)
        self.assertIsNotNone(preregistration)
        context["replay_bundles"] = bundles
        context["replay_bindings"] = bindings
        context["replay_preregistration"] = preregistration
        self.assertEqual(fixture._evaluate(context)["status"], "PASS")
        return context

    def _segment_for_context(
        self,
        context: dict[str, object],
        *,
        previous_asset_hash: str | None,
    ) -> dict[str, object]:
        replay_fixture = self.binding.persistence.source.source
        registration_fixture = self.binding.persistence.source
        persistence_fixture = self.binding.persistence
        source_gate = replay_fixture._evaluate(context)
        original_context = registration_fixture.context
        try:
            registration_fixture.context = context
            configuration = registration_fixture._configuration()
            registration = registration_fixture._build(
                configuration=configuration
            )
        finally:
            registration_fixture.context = original_context
        self.assertIsNotNone(registration)
        asset = persistence_receipts.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
            registration,
            asset_created_at_utc="2026-12-20T02:46:00Z",
            previous_persisted_asset_hash=previous_asset_hash,
        )
        self.assertIsNotNone(asset)
        unsigned_write = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
            registration,
            asset,
            session_id="LINEAGE-WRITE-SESSION-02",
            written_at_utc="2026-12-20T02:50:00Z",
        )
        write = persistence_fixture._sign(
            unsigned_write,
            persistence_fixture.private_key,
            persistence_receipts.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
        )
        unsigned_reopen = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
            registration,
            asset,
            write,
            session_id="LINEAGE-REOPEN-SESSION-02",
            reopened_at_utc="2026-12-20T02:55:00Z",
        )
        reopen = persistence_fixture._sign(
            unsigned_reopen,
            persistence_fixture.private_key,
            persistence_receipts.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )
        evaluation = persistence_receipts.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
            registration,
            context["replay_preregistration"],
            context["lifecycle_preregistration"],
            context["binding_preregistration"],
            context["overlap_preregistration"],
            context["multi_preregistration"],
            configuration,
            persistence_fixture.public_key_base64,
            asset,
            write,
            reopen,
            expected_registration_hash=registration["registration_hash"],
            expected_asset_hash=asset["asset_hash"],
            expected_write_receipt_hash=write["write_receipt_hash"],
            expected_reopen_receipt_hash=reopen["reopen_receipt_hash"],
        )
        source_inputs = self.binding._source_inputs(context, source_gate)
        persistence_inputs = self.binding._persistence_inputs(
            registration,
            configuration,
            asset,
            write,
            reopen,
            evaluation,
        )
        binding_gate = persistence_binding.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            source_gate,
            source_inputs,
            evaluation,
            persistence_inputs,
        )
        self.assertIn(binding_gate["status"], {"PASS", "BLOCK"})
        return self._segment(
            binding_gate,
            source_gate,
            source_inputs,
            evaluation,
            persistence_inputs,
        )

    def _evaluate(
        self,
        current_segment: dict[str, object] | None = None,
        previous_segment: dict[str, object] | None = None,
    ) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
            current_segment or self.previous_segment,
            previous_segment,
        )
        self.assertIsInstance(result, dict)
        return result

    def test_adr0355_pass_still_has_no_lineage(self) -> None:
        gate = self.previous_segment["binding_gate_document"]

        self.assertEqual(gate["status"], "PASS")
        self.assertFalse(gate["facts"]["persisted_checkpoint_lineage_verified"])

    def test_registered_source_pin_anchor_passes_locally(self) -> None:
        gate = self._evaluate()

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["lineage_mode"], subject.REGISTERED_SOURCE_PIN_MODE)
        self.assertTrue(gate["facts"]["registered_source_pin_anchor_verified"])
        self.assertFalse(
            gate["facts"]["complete_persisted_checkpoint_history_verified"]
        )

    def test_real_previous_persisted_asset_segment_passes(self) -> None:
        context = self._extended_context()
        previous_asset_hash = self.previous_segment["persistence_inputs"][
            "checkpoint_asset"
        ]["asset_hash"]
        current_segment = self._segment_for_context(
            context,
            previous_asset_hash=previous_asset_hash,
        )

        gate = self._evaluate(current_segment, self.previous_segment)

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(
            gate["lineage_mode"],
            subject.PREVIOUS_PERSISTED_ASSET_MODE,
        )
        self.assertTrue(
            gate["facts"]["previous_persisted_asset_lineage_verified"]
        )
        self.assertEqual(gate["summary"]["previous_checkpoint_tree_size"], 3)
        self.assertEqual(gate["summary"]["current_checkpoint_tree_size"], 4)

    def test_segment_shape_is_exact(self) -> None:
        current = deepcopy(self.previous_segment)
        current["verified"] = True
        self.assertEqual(self._evaluate(current)["status"], "UNKNOWN")

        current = deepcopy(self.previous_segment)
        current.pop("source_inputs")
        self.assertEqual(self._evaluate(current)["status"], "UNKNOWN")

    def test_current_binding_drift_is_unknown(self) -> None:
        current = deepcopy(self.previous_segment)
        current["binding_gate_document"]["facts"][
            "asset_source_common_view_bound"
        ] = False

        self.assertEqual(self._evaluate(current)["status"], "UNKNOWN")

    def test_anchor_requires_null_previous_asset(self) -> None:
        current = deepcopy(self.previous_segment)
        asset = current["persistence_inputs"]["checkpoint_asset"]
        asset["previous_persisted_asset_hash"] = "0" * 64
        unsigned = deepcopy(asset)
        unsigned.pop("asset_hash")
        asset = seal_strict_canonical_document(unsigned, "asset_hash")
        current["persistence_inputs"]["expected_asset_hash"] = asset[
            "asset_hash"
        ]

        with patch.object(
            persistence_binding,
            "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1",
            return_value=True,
        ):
            gate = self._evaluate(current)

        self.assertEqual(
            gate["gate_blockers"],
            ["REGISTERED_SOURCE_PIN_REQUIRES_NULL_PREVIOUS_ASSET"],
        )

    def test_previous_asset_hash_mismatch_is_unknown(self) -> None:
        context = self._extended_context()
        current = self._segment_for_context(
            context,
            previous_asset_hash="0" * 64,
        )

        gate = self._evaluate(current, self.previous_segment)

        self.assertEqual(
            gate["gate_blockers"],
            ["PREVIOUS_PERSISTED_ASSET_HASH_MISMATCH"],
        )

    def test_previous_checkpoint_content_mismatch_is_unknown(self) -> None:
        context = self._extended_context()
        previous_asset_hash = self.previous_segment["persistence_inputs"][
            "checkpoint_asset"
        ]["asset_hash"]
        current = self._segment_for_context(
            context,
            previous_asset_hash=previous_asset_hash,
        )
        current["source_inputs"]["preregistration"][
            "expected_replay_bindings"
        ][0]["previous_checkpoint_root_hash"] = "0" * 64

        with patch.object(
            persistence_binding,
            "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1",
            return_value=True,
        ):
            gate = self._evaluate(current, self.previous_segment)

        self.assertEqual(
            gate["gate_blockers"],
            ["PREVIOUS_CHECKPOINT_CONTENT_MISMATCH"],
        )

    def test_stable_registry_lineage_drift_is_unknown(self) -> None:
        context = self._extended_context()
        previous_asset_hash = self.previous_segment["persistence_inputs"][
            "checkpoint_asset"
        ]["asset_hash"]
        current = self._segment_for_context(
            context,
            previous_asset_hash=previous_asset_hash,
        )
        current["source_inputs"]["preregistration"][
            "expected_replay_bindings"
        ][0]["replay_registry_id"] = "DRIFTED-REPLAY-REGISTRY"

        with patch.object(
            persistence_binding,
            "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1",
            return_value=True,
        ):
            gate = self._evaluate(current, self.previous_segment)

        self.assertEqual(
            gate["gate_blockers"],
            ["PERSISTED_CHECKPOINT_STABLE_LINEAGE_DRIFT"],
        )

    def test_current_block_is_preserved_in_anchor_mode(self) -> None:
        context = self.binding.persistence.source.source._context(
            duplicate_windows=True
        )
        source_gate, source_inputs, evaluation, persistence_inputs = (
            self.binding._material_for_context(context)
        )
        binding_gate = persistence_binding.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            source_gate,
            source_inputs,
            evaluation,
            persistence_inputs,
        )
        segment = self._segment(
            binding_gate,
            source_gate,
            source_inputs,
            evaluation,
            persistence_inputs,
        )

        gate = self._evaluate(segment)

        self.assertEqual(binding_gate["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        gate = self._evaluate()
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
                gate,
                self.previous_segment,
                expected_gate_hash=gate["gate_hash"],
            )
        )
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
                forged,
                self.previous_segment,
                expected_gate_hash=forged["gate_hash"],
            )
        )

    def test_output_redaction_and_source_pin(self) -> None:
        gate = self._evaluate()
        rendered = json.dumps(gate, sort_keys=True)

        self.assertNotIn('"current_segment"', rendered)
        self.assertNotIn('"previous_segment"', rendered)
        self.assertNotIn(self.binding.persistence.public_key_base64, rendered)
        self.assertFalse(any(gate["authority"].values()))
        self.assertFalse(
            gate["facts"]["durable_checkpoint_publication_verified"]
        )

        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        path = services / "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1.py"
        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.PERSISTENCE_BINDING_V1_IMPLEMENTATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
