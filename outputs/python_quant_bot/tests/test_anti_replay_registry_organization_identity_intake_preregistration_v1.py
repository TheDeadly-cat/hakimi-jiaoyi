from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1 as intake_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


ROOT = Path(__file__).resolve().parents[1]


class AntiReplayRegistryOrganizationIdentityIntakePreregistrationV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kwargs = {
            "registry_id": "synthetic.organization.registry",
            "operator_identity_claim": "synthetic-organization-operator-claim",
            "public_key_spki_sha256": sha256(b"synthetic-organization-key").hexdigest(),
            "trust_domain": "synthetic.organization.test",
        }
        cls.identity = identity_v1.build_anti_replay_registry_identity_preregistration_v1(
            **cls.kwargs
        )
        cls.intake = intake_v1.build_anti_replay_registry_organization_identity_intake_preregistration_v1(
            cls.identity,
            **cls.kwargs,
        )

    def test_exact_intake_is_blocked_with_zero_observed_references(self) -> None:
        self.assertEqual(self.intake["status"], "BLOCKED")
        self.assertEqual(self.intake["facts"]["evidence_reference_count"], 0)
        self.assertFalse(self.intake["facts"]["external_sources_invoked"])
        self.assertFalse(
            self.intake["facts"]["registry_organization_identity_verified"]
        )
        self.assertTrue(self.intake["facts"]["evidence_requirements_preregistered"])

    def test_six_requirements_have_exact_unique_roles_and_nonzero_freshness(self) -> None:
        requirements = self.intake["requirements"]
        self.assertEqual(len(requirements), 6)
        self.assertEqual(len({row["evidence_kind"] for row in requirements}), 6)
        self.assertEqual(len({row["signer_role"] for row in requirements}), 6)
        self.assertTrue(all(row["state"] == "UNOBSERVED" for row in requirements))
        self.assertTrue(all(row["freshness_max_age_ms"] > 0 for row in requirements))
        self.assertTrue(all(row["independent_signature_required"] for row in requirements))

    def test_existing_generic_contract_schemas_are_reused_exactly(self) -> None:
        schemas = {
            row["evidence_kind"]: row["evidence_schema_version"]
            for row in self.intake["requirements"]
        }
        self.assertEqual(
            schemas["KEY_GOVERNANCE_EVALUATION"],
            "provider-identity-witness-conformance-key-governance-evaluation-v1",
        )
        self.assertEqual(
            schemas["AUDITOR_PROVENANCE_EVALUATION"],
            "provider-identity-auditor-provenance-suite-reproducibility-evaluation-v1",
        )
        self.assertEqual(
            schemas["ARTIFACT_TRANSPARENCY_EVALUATION"],
            "provider-identity-artifact-transparency-availability-evaluation-v1",
        )

    def test_intake_contains_no_payload_endpoint_or_signature_material(self) -> None:
        serialized = repr(self.intake).lower()
        self.assertNotIn("endpoint", serialized)
        self.assertNotIn("artifact_payload", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("signature_material", serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertEqual(
            self.intake["identity"]["operator_identity_claim_hash"],
            strict_canonical_hash(self.kwargs["operator_identity_claim"]),
        )
        self.assertTrue(all(value is False for value in self.intake["authority"].values()))

    def test_upstream_implementation_pins_are_current(self) -> None:
        paths = {
            intake_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "application"
            / "anti_replay_registry_identity_preregistration_v1.py",
            intake_v1.KEY_GOVERNANCE_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "services"
            / "provider_identity_witness_conformance_key_governance_v1.py",
            intake_v1.AUDITOR_PROVENANCE_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "services"
            / "provider_identity_auditor_provenance_suite_reproducibility_v1.py",
            intake_v1.ARTIFACT_TRANSPARENCY_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "services"
            / "provider_identity_artifact_transparency_availability_v1.py",
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)

    def test_public_verifier_pass_means_exact_blocked_preregistration(self) -> None:
        exact = intake_v1.verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
            self.intake,
            self.identity,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["intake_status"], "BLOCKED")
        self.assertEqual(exact["evidence_reference_count"], 0)
        self.assertFalse(exact["external_sources_invoked"])
        self.assertFalse(exact["registry_organization_identity_verified"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_identity_substitution_fails_exact_rebuild(self) -> None:
        changed = dict(self.kwargs)
        changed["registry_id"] = "synthetic.substituted.registry"
        exact = intake_v1.verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
            self.intake,
            self.identity,
            **changed,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["intake_status"], "UNKNOWN")
        self.assertFalse(exact["registry_organization_identity_verified"])

    def test_resealed_requirement_role_drift_fails_exact_rebuild(self) -> None:
        body = deepcopy(self.intake)
        body.pop("intake_preregistration_hash")
        body["requirements"][0]["signer_role"] = "domain_control_auditor"
        drift = seal_strict_canonical_document(body, "intake_preregistration_hash")
        exact = intake_v1.verify_anti_replay_registry_organization_identity_intake_preregistration_v1(
            drift,
            self.identity,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["intake_status"], "UNKNOWN")

    def test_resealed_identity_preregistration_authority_drift_is_rejected(self) -> None:
        body = deepcopy(self.identity)
        body.pop("preregistration_hash")
        body["authority"]["writer_allowed"] = True
        promoted = seal_strict_canonical_document(body, "preregistration_hash")
        with self.assertRaises(ValueError):
            intake_v1.build_anti_replay_registry_organization_identity_intake_preregistration_v1(
                promoted,
                **self.kwargs,
            )


if __name__ == "__main__":
    unittest.main()
