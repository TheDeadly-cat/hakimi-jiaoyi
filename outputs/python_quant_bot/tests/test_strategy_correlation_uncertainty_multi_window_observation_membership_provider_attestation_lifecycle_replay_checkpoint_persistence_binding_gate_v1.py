from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1
    as replay_binding,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1
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
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1
    as persistence_receipt_fixtures,
)


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceBindingGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.persistence = persistence_receipt_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceReceiptVerifierV1Tests(
            methodName="test_valid_receipts_pass_local_crypto_contract"
        )
        self.persistence.setUp()
        self.addCleanup(self.persistence.doCleanups)
        self.context = self.persistence.context
        self.source_gate = self.persistence.source.source._evaluate(self.context)
        self.persistence_evaluation = self.persistence._evaluate()
        self.source_inputs = self._source_inputs(
            self.context,
            self.source_gate,
        )
        self.persistence_inputs = self._persistence_inputs(
            self.persistence.registration,
            self.persistence.configuration,
            self.persistence.asset,
            self.persistence.write_receipt,
            self.persistence.reopen_receipt,
            self.persistence_evaluation,
        )

    @staticmethod
    def _source_inputs(
        context: dict[str, object],
        source_gate: dict[str, object],
    ) -> dict[str, object]:
        return {
            "expected_gate_hash": source_gate["gate_hash"],
            "expected_lifecycle_binding_gate_hash": context[
                "lifecycle_gate"
            ]["gate_hash"],
            "expected_lifecycle_binding_preregistration_hash": context[
                "lifecycle_preregistration"
            ]["preregistration_hash"],
            "expected_multi_window_gate_hash": context["multi_gate"][
                "gate_hash"
            ],
            "expected_multi_window_preregistration_hash": context[
                "multi_preregistration"
            ]["preregistration_hash"],
            "expected_overlap_evidence_hash": context["overlap_evidence"][
                "evidence_hash"
            ],
            "expected_overlap_gate_hash": context["overlap_gate"][
                "gate_hash"
            ],
            "expected_overlap_preregistration_hash": context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            "expected_preregistration_hash": context[
                "replay_preregistration"
            ]["preregistration_hash"],
            "expected_provider_binding_gate_hash": context["provider_gate"][
                "gate_hash"
            ],
            "expected_provider_binding_preregistration_hash": context[
                "binding_preregistration"
            ]["preregistration_hash"],
            "expected_window_audit_hashes": context["audit_hashes"],
            "lifecycle_binding_gate_document": context["lifecycle_gate"],
            "lifecycle_binding_preregistration": context[
                "lifecycle_preregistration"
            ],
            "multi_window_gate_document": context["multi_gate"],
            "multi_window_preregistration": context[
                "multi_preregistration"
            ],
            "overlap_evidence": context["overlap_evidence"],
            "overlap_gate_document": context["overlap_gate"],
            "overlap_preregistration": context["overlap_preregistration"],
            "preregistration": context["replay_preregistration"],
            "provider_binding_gate_document": context["provider_gate"],
            "provider_binding_preregistration": context[
                "binding_preregistration"
            ],
            "window_audits": context["window_audits"],
            "window_lifecycle_bundles": context["lifecycle_bundles"],
            "window_lifecycle_replay_bundles": context["replay_bundles"],
            "window_provider_attestation_bundles": context[
                "provider_bundles"
            ],
        }

    def _persistence_inputs(
        self,
        registration: dict[str, object],
        configuration: dict[str, object],
        asset: dict[str, object],
        write_receipt: dict[str, object],
        reopen_receipt: dict[str, object],
        evaluation: dict[str, object],
    ) -> dict[str, object]:
        return {
            "checkpoint_asset": asset,
            "expected_asset_hash": asset["asset_hash"],
            "expected_registration_hash": registration["registration_hash"],
            "expected_reopen_receipt_hash": reopen_receipt[
                "reopen_receipt_hash"
            ],
            "expected_verification_hash": evaluation["verification_hash"],
            "expected_write_receipt_hash": write_receipt[
                "write_receipt_hash"
            ],
            "persistence_configuration": configuration,
            "persistence_provider_public_key_base64": (
                self.persistence.public_key_base64
            ),
            "persistence_registration": registration,
            "reopen_receipt": reopen_receipt,
            "write_receipt": write_receipt,
        }

    def _evaluate(
        self,
        *,
        source_gate: dict[str, object] | None = None,
        source_inputs: dict[str, object] | None = None,
        persistence_evaluation: dict[str, object] | None = None,
        persistence_inputs: dict[str, object] | None = None,
    ) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            source_gate or self.source_gate,
            source_inputs or self.source_inputs,
            persistence_evaluation or self.persistence_evaluation,
            persistence_inputs or self.persistence_inputs,
        )
        self.assertIsInstance(result, dict)
        return result

    def _verify(
        self,
        document: dict[str, object],
        *,
        expected_gate_hash: str | None = None,
    ) -> bool:
        return subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            document,
            self.source_gate,
            self.source_inputs,
            self.persistence_evaluation,
            self.persistence_inputs,
            expected_gate_hash=expected_gate_hash or document["gate_hash"],
        )

    def _material_for_context(
        self,
        context: dict[str, object],
    ) -> tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        dict[str, object],
    ]:
        replay_fixture = self.persistence.source.source
        registration_fixture = self.persistence.source
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
            asset_created_at_utc="2026-12-20T02:21:00Z",
        )
        self.assertIsNotNone(asset)
        unsigned_write = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
            registration,
            asset,
            session_id="BLOCK-WRITE-SESSION-01",
            written_at_utc="2026-12-20T02:25:00Z",
        )
        write = self.persistence._sign(
            unsigned_write,
            self.persistence.private_key,
            persistence_receipts.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
        )
        unsigned_reopen = persistence_receipts.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
            registration,
            asset,
            write,
            session_id="BLOCK-REOPEN-SESSION-01",
            reopened_at_utc="2026-12-20T02:30:00Z",
        )
        reopen = self.persistence._sign(
            unsigned_reopen,
            self.persistence.private_key,
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
            self.persistence.public_key_base64,
            asset,
            write,
            reopen,
            expected_registration_hash=registration["registration_hash"],
            expected_asset_hash=asset["asset_hash"],
            expected_write_receipt_hash=write["write_receipt_hash"],
            expected_reopen_receipt_hash=reopen["reopen_receipt_hash"],
        )
        source_inputs = self._source_inputs(context, source_gate)
        persistence_inputs = self._persistence_inputs(
            registration,
            configuration,
            asset,
            write,
            reopen,
            evaluation,
        )
        return source_gate, source_inputs, evaluation, persistence_inputs

    def test_adr0354_pass_still_has_no_source_gate_binding(self) -> None:
        self.assertEqual(self.persistence_evaluation["status"], "PASS")
        self.assertFalse(
            self.persistence_evaluation["facts"][
                "source_replay_binding_gate_verified"
            ]
        )

    def test_valid_composition_passes_locally(self) -> None:
        gate = self._evaluate()

        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(gate["facts"]["source_replay_binding_gate_verified"])
        self.assertTrue(gate["facts"]["asset_source_common_view_bound"])
        self.assertFalse(
            gate["facts"]["durable_checkpoint_publication_verified"]
        )
        self.assertEqual(gate["summary"]["persisted_asset_count"], 1)

    def test_composition_is_deterministic_and_exactly_verifiable(self) -> None:
        first = self._evaluate()
        second = self._evaluate()

        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_source_input_shape_is_exact(self) -> None:
        missing = deepcopy(self.source_inputs)
        missing.pop("overlap_evidence")
        self.assertEqual(
            self._evaluate(source_inputs=missing)["status"],
            "UNKNOWN",
        )
        extra = deepcopy(self.source_inputs)
        extra["compatibility_mode"] = True
        self.assertEqual(
            self._evaluate(source_inputs=extra)["status"],
            "UNKNOWN",
        )

    def test_persistence_input_shape_is_exact(self) -> None:
        missing = deepcopy(self.persistence_inputs)
        missing.pop("checkpoint_asset")
        self.assertEqual(
            self._evaluate(persistence_inputs=missing)["status"],
            "UNKNOWN",
        )
        extra = deepcopy(self.persistence_inputs)
        extra["verified"] = True
        self.assertEqual(
            self._evaluate(persistence_inputs=extra)["status"],
            "UNKNOWN",
        )

    def test_source_gate_drift_is_unknown(self) -> None:
        source_gate = deepcopy(self.source_gate)
        source_gate["facts"]["common_registry_view_bound"] = False

        gate = self._evaluate(source_gate=source_gate)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0352_SOURCE_GATE_EXACT_REBUILD_FAILED"],
        )

    def test_persistence_evaluation_drift_is_unknown(self) -> None:
        evaluation = deepcopy(self.persistence_evaluation)
        evaluation["facts"]["exact_record_replay_verified"] = False

        self.assertEqual(
            self._evaluate(persistence_evaluation=evaluation)["status"],
            "UNKNOWN",
        )

    def test_source_preregistration_splice_is_unknown(self) -> None:
        block_context = self.persistence.source.source._context(
            duplicate_windows=True
        )
        source_inputs = deepcopy(self.source_inputs)
        source_inputs["preregistration"] = block_context[
            "replay_preregistration"
        ]
        source_inputs["expected_preregistration_hash"] = block_context[
            "replay_preregistration"
        ]["preregistration_hash"]

        self.assertEqual(
            self._evaluate(source_inputs=source_inputs)["status"],
            "UNKNOWN",
        )

    def test_local_binding_rejects_asset_splice_if_verifier_weakens(self) -> None:
        inputs = deepcopy(self.persistence_inputs)
        asset = inputs["checkpoint_asset"]
        asset["source_common_registry_view_hash"] = "0" * 64
        unsigned = deepcopy(asset)
        unsigned.pop("asset_hash")
        asset = seal_strict_canonical_document(unsigned, "asset_hash")
        inputs["expected_asset_hash"] = asset["asset_hash"]

        with patch.object(
            persistence_receipts,
            "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1",
            return_value=True,
        ):
            gate = self._evaluate(persistence_inputs=inputs)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["PERSISTED_ASSET_SOURCE_BINDING_INVALID"],
        )

    def test_lifecycle_replay_block_is_preserved(self) -> None:
        context = self.persistence.source.source._context(
            duplicate_windows=True
        )
        source_gate, source_inputs, evaluation, persistence_inputs = (
            self._material_for_context(context)
        )

        gate = self._evaluate(
            source_gate=source_gate,
            source_inputs=source_inputs,
            persistence_evaluation=evaluation,
            persistence_inputs=persistence_inputs,
        )

        self.assertEqual(source_gate["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["gate_blockers"],
            ["LIFECYCLE_REPLAY_BINDING_GATE_V1_BLOCKED"],
        )

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        gate = self._evaluate()
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")

        self.assertFalse(
            self._verify(
                forged,
                expected_gate_hash=forged["gate_hash"],
            )
        )

    def test_output_redaction_claims_and_source_pins(self) -> None:
        gate = self._evaluate()
        rendered = json.dumps(gate, sort_keys=True)

        self.assertNotIn(self.persistence.public_key_base64, rendered)
        self.assertNotIn(self.persistence.write_receipt["signature_base64"], rendered)
        self.assertNotIn('"source_inputs"', rendered)
        self.assertNotIn('"persistence_inputs"', rendered)
        self.assertFalse(any(gate["authority"].values()))
        self.assertFalse(gate["facts"]["authoritative_future_pin_verified"])

        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        expected = {
            "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1.py": subject.REPLAY_BINDING_V1_IMPLEMENTATION_SHA256,
            "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1.py": subject.PERSISTENCE_RECEIPTS_V1_IMPLEMENTATION_SHA256,
        }
        for filename, expected_hash in expected.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    sha256((services / filename).read_bytes()).hexdigest(),
                    expected_hash,
                )


if __name__ == "__main__":
    unittest.main()
