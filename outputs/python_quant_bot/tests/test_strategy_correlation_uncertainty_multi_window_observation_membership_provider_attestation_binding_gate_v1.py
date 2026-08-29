from __future__ import annotations

import base64
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_common_support_calendar_provider_composition_v1 as composition_v1
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as calendar_source
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as provider_source
from exchange_terminal.services import strategy_correlation_provider_dataset_content_attestation_v1 as provider_attestation_v1
from exchange_terminal.services import strategy_correlation_uncertainty_audit as uncertainty
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1 as overlap_gate
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1 as subject
from exchange_terminal.services.strategy_correlation_common_support_derivation_receipt_v1 import (
    build_correlation_common_support_derivation_receipt_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests import (
    test_strategy_correlation_common_support_calendar_provider_composition_v1
    as composition_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationBindingGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        patches = (
            patch.object(
                uncertainty,
                "verify_correlation_matrix_replay",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch.object(
                calendar_source,
                "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1",
                return_value=True,
            ),
            patch.object(
                provider_source,
                "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1",
                return_value=True,
            ),
        )
        for source_patch in patches:
            source_patch.start()
            self.addCleanup(source_patch.stop)

    def _provider_window(
        self,
        *,
        day_offset: int,
        data_hash_suffix: str,
        dataset_private_key: Ed25519PrivateKey,
    ) -> dict[str, object]:
        source = composition_fixtures.StrategyCorrelationCommonSupportCalendarProviderCompositionV1Tests(
            methodName="test_positive_composition_is_bounded_and_inactive"
        )
        source.setUp()
        if day_offset:
            shifted = [
                (date.fromisoformat(label) + timedelta(days=day_offset)).isoformat()
                for label in source.batch_dates
            ]
            source.batch_dates = shifted
            for row, label in zip(source.batch_rows, shifted, strict=True):
                row["observation_date"] = label
        source.matrix_replay = source.replay(data_hash_suffix=data_hash_suffix)
        source.derivation_receipt = (
            build_correlation_common_support_derivation_receipt_v1(
                source.matrix_replay
            )
        )
        source.calendar_document, source.calendar_bundle = source.calendar_evidence()
        source.provider_document, source.provider_bundle = source.provider_evidence()

        timestamp_private_key = Ed25519PrivateKey.generate()
        registry_private_key = Ed25519PrivateKey.generate()
        calendar_bundle = deepcopy(source.calendar_bundle)
        calendar_bundle["batch_verification_context"] = {
            "signature_verification_context": {
                "attestation_receipt": {
                    "public_key_base64": _public_key_base64(
                        timestamp_private_key
                    )
                }
            }
        }
        provider_bundle = deepcopy(source.provider_bundle)
        provider_bundle["identity_assertion_receipt"][
            "registry_public_key_base64"
        ] = _public_key_base64(registry_private_key)
        composition_document = composition_v1.build_correlation_common_support_calendar_provider_composition_v1(
            source.derivation_receipt,
            source.matrix_replay,
            source.calendar_document,
            calendar_bundle,
            source.provider_document,
            provider_bundle,
        )
        composition_context = {
            "derivation_receipt": source.derivation_receipt,
            "matrix_replay": source.matrix_replay,
            "calendar_session_verification": source.calendar_document,
            "calendar_verification_bundle": calendar_bundle,
            "provider_identity_verification": source.provider_document,
            "provider_verification_bundle": provider_bundle,
        }
        dataset_public_key_base64 = _public_key_base64(dataset_private_key)
        registration = provider_attestation_v1.build_provider_dataset_content_attestation_registration_v1(
            composition_document,
            composition_context,
            provider_dataset_key_id="DATASET-KEY-2026-01",
            provider_dataset_public_key_base64=dataset_public_key_base64,
            declared_at_utc="2026-08-22T00:00:00Z",
            valid_from_utc="2026-08-22T00:00:00Z",
            valid_until_utc="2027-08-22T00:00:00Z",
        )
        unsigned = provider_attestation_v1.build_unsigned_provider_dataset_content_attestation_v1(
            registration,
            composition_document,
            issued_at_utc="2026-12-20T01:00:00Z",
        )
        signature = dataset_private_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        attestation_receipt = provider_attestation_v1.assemble_provider_dataset_content_attestation_receipt_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )
        verification_document = provider_attestation_v1.evaluate_provider_dataset_content_attestation_v1(
            composition_document,
            composition_context,
            registration,
            dataset_public_key_base64,
            attestation_receipt,
            expected_registration_hash=registration["registration_hash"],
            expected_attestation_hash=attestation_receipt["attestation_hash"],
        )
        datasets = source.matrix_replay["completed_price_input"]["datasets"]
        common_dates = sorted(
            set.intersection(
                *(
                    {row["date"] for row in dataset["price_rows"]}
                    for dataset in datasets
                )
            )
        )[-composition_document["common_price_row_count"] :]
        observation_ids = common_dates[1:]
        self.assertEqual(
            strict_canonical_hash(common_dates),
            composition_document["common_price_index_hash"],
        )
        self.assertEqual(
            strict_canonical_hash(observation_ids),
            composition_document["common_observation_index_hash"],
        )
        return {
            "source": source,
            "composition_document": composition_document,
            "composition_context": composition_context,
            "registration": registration,
            "dataset_public_key_base64": dataset_public_key_base64,
            "attestation_receipt": attestation_receipt,
            "verification_document": verification_document,
            "observation_ids": observation_ids,
        }

    @staticmethod
    def _issuer_binding(
        window_id: str,
        provider_window: dict[str, object],
    ) -> dict[str, object]:
        composition = provider_window["composition_document"]
        registration = provider_window["registration"]
        attestation = provider_window["attestation_receipt"]
        verification = provider_window["verification_document"]
        return {
            "common_observation_count": composition[
                "common_observation_count"
            ],
            "common_observation_index_hash": composition[
                "common_observation_index_hash"
            ],
            "common_price_index_hash": composition["common_price_index_hash"],
            "composition_hash": composition["composition_hash"],
            "dataset_provider_binding_hash": composition[
                "dataset_provider_binding_hash"
            ],
            "provider_dataset_attestation_hash": attestation[
                "attestation_hash"
            ],
            "provider_dataset_key_id": registration[
                "provider_dataset_key_id"
            ],
            "provider_dataset_public_key_sha256": registration[
                "provider_dataset_public_key_sha256"
            ],
            "provider_dataset_registration_hash": registration[
                "registration_hash"
            ],
            "provider_dataset_verification_hash": verification[
                "verification_hash"
            ],
            "provider_id_hash": composition["provider_id_hash"],
            "source_matrix_replay_hash": composition[
                "source_matrix_replay_hash"
            ],
            "window_id": window_id,
        }

    @staticmethod
    def _provider_bundle(
        window_id: str,
        provider_window: dict[str, object],
    ) -> dict[str, object]:
        return {
            "attestation_receipt": provider_window["attestation_receipt"],
            "composition_context": provider_window["composition_context"],
            "composition_document": provider_window["composition_document"],
            "provider_dataset_public_key_base64": provider_window[
                "dataset_public_key_base64"
            ],
            "registration": provider_window["registration"],
            "verification_document": provider_window["verification_document"],
            "window_id": window_id,
        }

    def _context(
        self,
        *,
        second_day_offset: int = 365,
        membership_overrides: dict[int, list[str]] | None = None,
        price_grid_overrides: dict[int, str] | None = None,
    ) -> dict[str, object]:
        dataset_key = Ed25519PrivateKey.generate()
        provider_windows = [
            self._provider_window(
                day_offset=0,
                data_hash_suffix="window-one",
                dataset_private_key=dataset_key,
            ),
            self._provider_window(
                day_offset=second_day_offset,
                data_hash_suffix="window-two",
                dataset_private_key=dataset_key,
            ),
        ]
        windows = ["window-01", "window-02"]
        audits = [
            uncertainty.build_strategy_correlation_uncertainty_audit(
                provider_window["source"].matrix_replay
            )
            for provider_window in provider_windows
        ]
        replay_preregistration = provider_windows[0]["source"].matrix_replay[
            "preregistration"
        ]
        multi_preregistration = cluster_gate.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            replay_preregistration["symbols"],
            replay_preregistration["clusters"],
            windows,
        )
        self.assertIsNotNone(multi_preregistration)
        window_audits = [
            {"window_id": window_id, "uncertainty_audit": audit}
            for window_id, audit in zip(windows, audits, strict=True)
        ]
        audit_hashes = [audit["audit_hash"] for audit in audits]
        multi_gate = cluster_gate.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            multi_preregistration,
            window_audits,
            expected_preregistration_hash=multi_preregistration[
                "preregistration_hash"
            ],
            expected_window_audit_hashes=audit_hashes,
        )
        self.assertIsNotNone(multi_gate)
        overlap_preregistration = overlap_gate.build_strategy_correlation_uncertainty_multi_window_observation_overlap_preregistration_v1(
            multi_preregistration,
            study_identity_hash=_hash("provider-attested-study"),
            observation_identifier_scheme_hash=_hash(
                "iso-date-observation-id-v1"
            ),
            registration_sequence=1,
        )
        self.assertIsNotNone(overlap_preregistration)
        issuer_bindings = [
            self._issuer_binding(window_id, provider_window)
            for window_id, provider_window in zip(
                windows, provider_windows, strict=True
            )
        ]
        binding_preregistration = subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1(
            overlap_preregistration,
            multi_preregistration,
            issuer_bindings,
            registration_sequence=2,
        )
        self.assertIsNotNone(binding_preregistration)
        membership_overrides = membership_overrides or {}
        price_grid_overrides = price_grid_overrides or {}
        evidence_rows = []
        for index, (window_id, provider_window, audit) in enumerate(
            zip(windows, provider_windows, audits, strict=True)
        ):
            observation_ids = membership_overrides.get(
                index,
                provider_window["observation_ids"],
            )
            composition = provider_window["composition_document"]
            evidence_rows.append(
                {
                    "common_observation_membership_gate_v2_hash": _hash(
                        f"membership-gate-{index}"
                    ),
                    "common_observation_membership_hash": strict_canonical_hash(
                        observation_ids
                    ),
                    "common_price_date_grid_hash": price_grid_overrides.get(
                        index,
                        composition["common_price_index_hash"],
                    ),
                    "common_sample_count": len(observation_ids),
                    "date_grid_audit_hash": _hash(f"date-grid-audit-{index}"),
                    "observation_ids": list(observation_ids),
                    "uncertainty_audit_hash": audit["audit_hash"],
                    "window_id": window_id,
                }
            )
        overlap_evidence = overlap_gate.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
            overlap_preregistration,
            evidence_rows,
            evidence_sequence=3,
        )
        self.assertIsNotNone(overlap_evidence)
        overlap_gate_document = overlap_gate.evaluate_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
            overlap_preregistration,
            overlap_evidence,
            multi_gate,
            multi_preregistration,
            window_audits,
            expected_preregistration_hash=overlap_preregistration[
                "preregistration_hash"
            ],
            expected_evidence_hash=overlap_evidence["evidence_hash"],
            expected_multi_window_gate_hash=multi_gate["gate_hash"],
            expected_multi_window_preregistration_hash=multi_preregistration[
                "preregistration_hash"
            ],
            expected_window_audit_hashes=audit_hashes,
        )
        provider_bundles = [
            self._provider_bundle(window_id, provider_window)
            for window_id, provider_window in zip(
                windows, provider_windows, strict=True
            )
        ]
        return {
            "provider_windows": provider_windows,
            "windows": windows,
            "audits": audits,
            "multi_preregistration": multi_preregistration,
            "window_audits": window_audits,
            "audit_hashes": audit_hashes,
            "multi_gate": multi_gate,
            "overlap_preregistration": overlap_preregistration,
            "binding_preregistration": binding_preregistration,
            "overlap_evidence": overlap_evidence,
            "overlap_gate": overlap_gate_document,
            "provider_bundles": provider_bundles,
        }

    def _evaluate(self, context: dict[str, object]) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
            context["binding_preregistration"],
            context["overlap_gate"],
            context["overlap_preregistration"],
            context["overlap_evidence"],
            context["multi_gate"],
            context["multi_preregistration"],
            context["window_audits"],
            context["provider_bundles"],
            expected_preregistration_hash=context["binding_preregistration"][
                "preregistration_hash"
            ],
            expected_overlap_gate_hash=context["overlap_gate"]["gate_hash"],
            expected_overlap_preregistration_hash=context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            expected_overlap_evidence_hash=context["overlap_evidence"][
                "evidence_hash"
            ],
            expected_multi_window_gate_hash=context["multi_gate"]["gate_hash"],
            expected_multi_window_preregistration_hash=context[
                "multi_preregistration"
            ]["preregistration_hash"],
            expected_window_audit_hashes=context["audit_hashes"],
        )
        self.assertIsInstance(result, dict)
        return result

    def test_provider_signed_disjoint_memberships_pass_locally(self) -> None:
        context = self._context()
        gate = self._evaluate(context)

        self.assertEqual(context["multi_gate"]["status"], "PASS")
        self.assertEqual(context["overlap_gate"]["status"], "PASS")
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(
            gate["summary"]["provider_attestation_verified_window_count"],
            2,
        )
        self.assertTrue(
            gate["facts"]["all_memberships_bound_to_signed_compositions"]
        )

    def test_adr0349_can_pass_arbitrary_membership_but_binding_gate_is_unknown(self) -> None:
        arbitrary = [f"synthetic-{index:04d}" for index in range(60)]
        context = self._context(membership_overrides={0: arbitrary})

        gate = self._evaluate(context)

        self.assertEqual(context["overlap_gate"]["status"], "PASS")
        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["SIGNED_COMPOSITION_MEMBERSHIP_BINDING_SPLICE"],
        )

    def test_common_price_grid_splice_is_unknown(self) -> None:
        context = self._context(
            price_grid_overrides={0: _hash("spliced-price-grid")}
        )

        gate = self._evaluate(context)

        self.assertEqual(context["overlap_gate"]["status"], "PASS")
        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["SIGNED_COMPOSITION_MEMBERSHIP_BINDING_SPLICE"],
        )

    def test_provider_signature_tamper_is_unknown(self) -> None:
        context = self._context()
        receipt = context["provider_bundles"][0]["attestation_receipt"]
        raw = bytearray(base64.b64decode(receipt["signature_base64"]))
        raw[0] ^= 1
        receipt["signature_base64"] = base64.b64encode(bytes(raw)).decode(
            "ascii"
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0120_PROVIDER_ATTESTATION_EXACT_REBUILD_FAILED"],
        )

    def test_provider_verification_document_drift_is_unknown(self) -> None:
        context = self._context()
        document = context["provider_bundles"][0]["verification_document"]
        document["dataset_count"] += 1

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0120_PROVIDER_ATTESTATION_EXACT_REBUILD_FAILED"],
        )

    def test_reordered_or_missing_provider_bundles_are_unknown(self) -> None:
        context = self._context()
        context["provider_bundles"] = list(
            reversed(context["provider_bundles"])
        )
        reordered = self._evaluate(context)
        self.assertEqual(reordered["status"], "UNKNOWN")

        context = self._context()
        context["provider_bundles"] = context["provider_bundles"][:1]
        missing = self._evaluate(context)
        self.assertEqual(missing["status"], "UNKNOWN")

    def test_preregistered_attestation_hash_splice_is_unknown(self) -> None:
        context = self._context()
        preregistration = deepcopy(context["binding_preregistration"])
        preregistration["expected_window_issuer_bindings"][0][
            "provider_dataset_attestation_hash"
        ] = _hash("other-attestation")
        unsigned = deepcopy(preregistration)
        unsigned.pop("preregistration_hash")
        context["binding_preregistration"] = seal_strict_canonical_document(
            unsigned,
            "preregistration_hash",
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0120_PROVIDER_ATTESTATION_EXACT_REBUILD_FAILED"],
        )

    def test_provider_attested_duplicate_windows_preserve_overlap_block(self) -> None:
        context = self._context(second_day_offset=0)

        gate = self._evaluate(context)

        self.assertEqual(context["overlap_gate"]["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["gate_blockers"],
            ["OBSERVATION_OVERLAP_GATE_V1_BLOCKED"],
        )

    def test_preregistration_rejects_reordered_or_duplicate_source_bindings(self) -> None:
        context = self._context()
        bindings = deepcopy(
            context["binding_preregistration"][
                "expected_window_issuer_bindings"
            ]
        )
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1(
                context["overlap_preregistration"],
                context["multi_preregistration"],
                list(reversed(bindings)),
                registration_sequence=4,
            )
        )
        bindings[1]["composition_hash"] = bindings[0]["composition_hash"]
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1(
                context["overlap_preregistration"],
                context["multi_preregistration"],
                bindings,
                registration_sequence=4,
            )
        )

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        context = self._context()
        gate = self._evaluate(context)
        arguments = {
            "expected_gate_hash": gate["gate_hash"],
            "expected_preregistration_hash": context[
                "binding_preregistration"
            ]["preregistration_hash"],
            "expected_overlap_gate_hash": context["overlap_gate"]["gate_hash"],
            "expected_overlap_preregistration_hash": context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            "expected_overlap_evidence_hash": context["overlap_evidence"][
                "evidence_hash"
            ],
            "expected_multi_window_gate_hash": context["multi_gate"][
                "gate_hash"
            ],
            "expected_multi_window_preregistration_hash": context[
                "multi_preregistration"
            ]["preregistration_hash"],
            "expected_window_audit_hashes": context["audit_hashes"],
        }
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
                gate,
                context["binding_preregistration"],
                context["overlap_gate"],
                context["overlap_preregistration"],
                context["overlap_evidence"],
                context["multi_gate"],
                context["multi_preregistration"],
                context["window_audits"],
                context["provider_bundles"],
                **arguments,
            )
        )
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")
        arguments["expected_gate_hash"] = forged["gate_hash"]
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
                forged,
                context["binding_preregistration"],
                context["overlap_gate"],
                context["overlap_preregistration"],
                context["overlap_evidence"],
                context["multi_gate"],
                context["multi_preregistration"],
                context["window_audits"],
                context["provider_bundles"],
                **arguments,
            )
        )

    def test_output_is_redacted_and_all_external_trust_remains_false(self) -> None:
        context = self._context()
        gate = self._evaluate(context)
        rendered = json.dumps(gate, sort_keys=True)
        first_provider = context["provider_windows"][0]

        self.assertNotIn('"observation_ids":', rendered)
        self.assertNotIn('"composition_document":', rendered)
        self.assertNotIn('"signature_base64":', rendered)
        self.assertNotIn(
            first_provider["dataset_public_key_base64"],
            rendered,
        )
        self.assertNotIn(first_provider["observation_ids"][0], rendered)
        self.assertFalse(
            gate["facts"]["external_provider_dataset_key_control_verified"]
        )
        self.assertFalse(
            gate["facts"]["external_provider_data_issuance_verified"]
        )
        self.assertFalse(gate["facts"]["dataset_key_lifecycle_verified"])
        self.assertFalse(gate["facts"]["content_issuance_replay_verified"])
        self.assertTrue(
            all(
                value is False
                for key, value in gate["authority"].items()
                if key != "research_evidence_only"
            )
        )

    def test_source_pins_match_reviewed_implementations(self) -> None:
        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        expected = {
            "strategy_correlation_common_support_calendar_provider_composition_v1.py": subject.COMPOSITION_V1_IMPLEMENTATION_SHA256,
            "strategy_correlation_provider_dataset_content_attestation_v1.py": subject.PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256,
            "strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1.py": subject.OVERLAP_GATE_V1_IMPLEMENTATION_SHA256,
        }
        for filename, expected_hash in expected.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    sha256((services / filename).read_bytes()).hexdigest(),
                    expected_hash,
                )


if __name__ == "__main__":
    unittest.main()
