from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import inspect
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1
    as replay_binding_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = replay_binding_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayBindingGateV1Tests(
            methodName="test_common_registry_view_passes_locally"
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.context = self.source.context
        self.persistence_private_key = Ed25519PrivateKey.generate()
        self.persistence_public_key_base64 = _public_key_base64(
            self.persistence_private_key
        )
        self.configuration = self._configuration()
        self.registration = self._build()
        self.assertIsNotNone(self.registration)

    def _excluded_rows(self) -> list[dict[str, object]]:
        rows = []
        for window_id, bundle in zip(
            self.context["windows"],
            self.context["lifecycle_bundles"],
            strict=True,
        ):
            lifecycle_document = bundle["lifecycle_gate_document"]
            attestation_registration = bundle["attestation_context"][
                "registration"
            ]
            rows.append(
                {
                    "public_key_sha256s": sorted(
                        {
                            lifecycle_document[
                                "provider_dataset_public_key_sha256"
                            ],
                            lifecycle_document[
                                "governance_public_key_sha256"
                            ],
                            attestation_registration[
                                "identity_registry_public_key_sha256"
                            ],
                            attestation_registration[
                                "timestamp_adapter_public_key_sha256"
                            ],
                        }
                    ),
                    "window_id": window_id,
                }
            )
        return rows

    def _configuration(self, **overrides: object) -> dict[str, object]:
        configuration = {
            "declared_at_utc": "2026-08-24T00:00:00Z",
            "excluded_upstream_public_key_hashes_by_window": self._excluded_rows(),
            "max_reopen_receipt_delay_seconds": 7200,
            "max_write_receipt_delay_seconds": 3600,
            "min_reopen_separation_seconds": 60,
            "persistence_adapter_id": "LIFECYCLE-REPLAY-PERSISTENCE-ADAPTER-01",
            "persistence_adapter_implementation_hash": _hash(
                "adr0353-persistence-adapter-v1"
            ),
            "persistence_namespace": (
                "STRATEGY-CORRELATION.LIFECYCLE-REPLAY-CHECKPOINT.V1"
            ),
            "persistence_provider_id": (
                "LIFECYCLE-REPLAY-PERSISTENCE-PROVIDER-01"
            ),
            "persistence_provider_key_id": (
                "LIFECYCLE-REPLAY-PERSISTENCE-PROVIDER-KEY-01"
            ),
            "persistence_provider_public_key_base64": (
                self.persistence_public_key_base64
            ),
        }
        configuration.update(overrides)
        return configuration

    def _build(
        self,
        *,
        source_preregistration: dict[str, object] | None = None,
        configuration: dict[str, object] | None = None,
    ) -> dict[str, object] | None:
        return subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
            source_preregistration
            or self.context["replay_preregistration"],
            self.context["lifecycle_preregistration"],
            self.context["binding_preregistration"],
            self.context["overlap_preregistration"],
            self.context["multi_preregistration"],
            configuration or self.configuration,
        )

    def _verify(
        self,
        document: dict[str, object],
        *,
        expected_registration_hash: str | None = None,
    ) -> bool:
        return subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
            document,
            self.context["replay_preregistration"],
            self.context["lifecycle_preregistration"],
            self.context["binding_preregistration"],
            self.context["overlap_preregistration"],
            self.context["multi_preregistration"],
            self.configuration,
            expected_registration_hash=(
                expected_registration_hash or document["registration_hash"]
            ),
        )

    def test_adr0352_pass_still_has_no_persistence_evidence(self) -> None:
        gate = self.source._evaluate(self.context)

        self.assertEqual(gate["status"], "PASS")
        self.assertFalse(
            gate["facts"]["durable_checkpoint_publication_verified"]
        )
        self.assertFalse(
            any("persist" in key.lower() for key in gate)
        )

    def test_registration_binds_source_common_view_and_receipt_contracts(self) -> None:
        source = self.context["replay_preregistration"]
        common = source["expected_replay_bindings"][0]

        self.assertEqual(
            self.registration["source_preregistration_hash"],
            source["preregistration_hash"],
        )
        self.assertEqual(
            self.registration["source_common_registry_view_hash"],
            source["common_registry_view_hash"],
        )
        self.assertEqual(
            self.registration["source_checkpoint_root_hash"],
            common["checkpoint_root_hash"],
        )
        self.assertEqual(
            self.registration["asset_schema_version"],
            subject.CHECKPOINT_ASSET_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.registration["record_cardinality_policy"],
            subject.RECORD_CARDINALITY_POLICY,
        )
        self.assertFalse(
            self.registration["facts"]["write_receipt_observed"]
        )
        self.assertFalse(
            self.registration["facts"]["reopen_receipt_observed"]
        )

    def test_registration_is_deterministic_exact_and_input_immutable(self) -> None:
        original = deepcopy(self.configuration)

        self.assertEqual(self.registration, self._build())
        self.assertTrue(self._verify(self.registration))
        self.assertEqual(self.configuration, original)

    def test_source_preregistration_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.context["replay_preregistration"])
        drifted["common_registry_view_hash"] = _hash("drifted-common-view")
        unsigned = deepcopy(drifted)
        unsigned.pop("preregistration_hash")
        drifted = seal_strict_canonical_document(
            unsigned,
            "preregistration_hash",
        )

        self.assertIsNone(self._build(source_preregistration=drifted))

    def test_configuration_shape_is_exact(self) -> None:
        missing = deepcopy(self.configuration)
        missing.pop("persistence_namespace")
        self.assertIsNone(self._build(configuration=missing))

        extra = deepcopy(self.configuration)
        extra["compatibility_mode"] = True
        self.assertIsNone(self._build(configuration=extra))

    def test_public_key_encoding_is_strict(self) -> None:
        for value in ("bad", " " + self.persistence_public_key_base64, ""):
            with self.subTest(value=value):
                configuration = self._configuration(
                    persistence_provider_public_key_base64=value
                )
                self.assertIsNone(self._build(configuration=configuration))

    def test_provider_key_cannot_reuse_replay_auditor_or_upstream_role(self) -> None:
        replay_bundle = self.context["replay_bundles"][0]
        lifecycle_bundle = self.context["lifecycle_bundles"][0]
        collision_keys = (
            replay_bundle["replay_registry_public_key_base64"],
            replay_bundle["occurrence_auditor_public_key_base64"],
            lifecycle_bundle["governance_public_key_base64"],
        )
        for value in collision_keys:
            with self.subTest(value=value[:12]):
                configuration = self._configuration(
                    persistence_provider_public_key_base64=value
                )
                self.assertIsNone(self._build(configuration=configuration))

    def test_provider_key_id_cannot_reuse_replay_or_auditor_role(self) -> None:
        common = self.context["replay_preregistration"][
            "expected_replay_bindings"
        ][0]
        for value in (
            common["replay_registry_key_id"],
            common["occurrence_auditor_key_id"],
        ):
            with self.subTest(value=value):
                configuration = self._configuration(
                    persistence_provider_key_id=value
                )
                self.assertIsNone(self._build(configuration=configuration))

    def test_excluded_key_windows_and_hashes_are_exact(self) -> None:
        rows = self._excluded_rows()
        configuration = self._configuration(
            excluded_upstream_public_key_hashes_by_window=list(reversed(rows))
        )
        self.assertIsNone(self._build(configuration=configuration))

        configuration = self._configuration(
            excluded_upstream_public_key_hashes_by_window=rows[:1]
        )
        self.assertIsNone(self._build(configuration=configuration))

        rows = self._excluded_rows()
        rows[0]["public_key_sha256s"][0] = _hash("wrong-upstream-key")
        rows[0]["public_key_sha256s"].sort()
        configuration = self._configuration(
            excluded_upstream_public_key_hashes_by_window=rows
        )
        self.assertIsNone(self._build(configuration=configuration))

    def test_time_and_delay_policies_are_strict(self) -> None:
        invalid = (
            {"max_write_receipt_delay_seconds": True},
            {"max_reopen_receipt_delay_seconds": 0},
            {"min_reopen_separation_seconds": 7201},
            {"declared_at_utc": "2026-12-20T03:30:00Z"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                self.assertIsNone(
                    self._build(configuration=self._configuration(**overrides))
                )

    def test_output_redacts_raw_keys_and_keeps_authority_false(self) -> None:
        rendered = json.dumps(self.registration, sort_keys=True)

        self.assertNotIn(self.persistence_public_key_base64, rendered)
        self.assertNotIn('"public_key_sha256s"', rendered)
        self.assertFalse(any(self.registration["authority"].values()))
        self.assertEqual(
            self.registration["permissions"],
            {"paper_authorized": False, "live_order_allowed": False},
        )

    def test_source_pin_matches_reviewed_implementation(self) -> None:
        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        path = services / "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1.py"

        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.REPLAY_BINDING_V1_IMPLEMENTATION_SHA256,
        )

    def test_public_api_never_accepts_private_key(self) -> None:
        functions = (
            subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1,
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1,
        )
        for function in functions:
            with self.subTest(function=function.__name__):
                parameters = inspect.signature(function).parameters
                self.assertFalse(
                    any("private" in name.lower() for name in parameters)
                )


if __name__ == "__main__":
    unittest.main()
