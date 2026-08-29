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
from exchange_terminal.application import (
    anti_replay_registry_signer_source_trust_preregistration_v1 as source_trust_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class AntiReplayRegistrySignerSourceTrustPreregistrationV1Tests(
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
        cls.preregistration = source_trust_v1.build_anti_replay_registry_signer_source_trust_preregistration_v1(
            cls.intake,
            cls.identity,
            **cls.kwargs,
        )

    def _verify(self, document: dict, **kwargs):
        return source_trust_v1.verify_anti_replay_registry_signer_source_trust_preregistration_v1(
            document,
            self.intake,
            self.identity,
            **(self.kwargs | kwargs),
        )

    def test_exact_preregistration_is_blocked_and_source_free(self) -> None:
        document = self.preregistration
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(document["facts"]["source_trust_record_count"], 0)
        self.assertEqual(document["facts"]["source_adapter_count"], 0)
        self.assertEqual(document["facts"]["trust_anchor_count"], 0)
        self.assertFalse(document["facts"]["external_sources_invoked"])
        self.assertFalse(document["facts"]["external_source_trust_verified"])
        self.assertFalse(document["facts"]["signer_role_identity_verified"])

    def test_six_exact_role_specific_requirements_are_unobserved(self) -> None:
        rows = self.preregistration["requirements"]
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({row["evidence_kind"] for row in rows}), 6)
        self.assertEqual(len({row["signer_role"] for row in rows}), 6)
        self.assertEqual(len({row["authority_role"] for row in rows}), 6)
        self.assertTrue(all(row["state"] == "UNOBSERVED" for row in rows))
        self.assertTrue(all(row["independent_trust_anchor_required"] for row in rows))
        self.assertTrue(
            all(
                row["source_adapter_id_and_implementation_hash_required"]
                for row in rows
            )
        )

    def test_separation_policy_forbids_self_attestation_and_boolean_trust(self) -> None:
        policy = self.preregistration["separation_policy"]
        self.assertTrue(policy["source_record_self_attestation_forbidden"])
        self.assertTrue(policy["caller_supplied_trust_boolean_forbidden"])
        self.assertTrue(policy["local_signature_pass_is_not_source_trust"])
        self.assertTrue(
            policy["namespace_and_key_difference_is_not_governance_proof"]
        )
        self.assertTrue(
            policy[
                "source_adapter_and_trust_anchor_require_separate_authorization"
            ]
        )

    def test_no_payload_endpoint_secret_or_raw_operator_claim_is_embedded(self) -> None:
        serialized = repr(self.preregistration).lower()
        self.assertNotIn("endpoint", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("artifact_payload", serialized)
        self.assertNotIn("signature_material", serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertTrue(
            all(value is False for value in self.preregistration["authority"].values())
        )

    def test_upstream_implementation_pins_are_current(self) -> None:
        paths = {
            source_trust_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "application"
            / "anti_replay_registry_identity_preregistration_v1.py",
            source_trust_v1.INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "application"
            / "anti_replay_registry_organization_identity_intake_preregistration_v1.py",
            source_trust_v1.ORGANIZATION_IDENTITY_REFERENCE_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal"
            / "application"
            / "ports"
            / "registry_organization_identity_v1.py",
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)

    def test_public_exact_pass_grants_no_identity_or_authority(self) -> None:
        exact = self._verify(self.preregistration)
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["source_trust_status"], "BLOCKED")
        self.assertEqual(exact["source_trust_record_count"], 0)
        self.assertFalse(exact["external_source_trust_verified"])
        self.assertFalse(exact["signer_role_identity_verified"])
        self.assertFalse(exact["registry_organization_identity_verified"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_identity_substitution_fails_exact_rebuild(self) -> None:
        exact = self._verify(
            self.preregistration,
            registry_id="synthetic.substituted.registry",
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["source_trust_status"], "UNKNOWN")

    def test_resealed_adversarial_promotions_and_aliases_are_unknown(self) -> None:
        def promote_fact(body: dict) -> None:
            body["facts"]["external_source_trust_verified"] = True

        def promote_signer(body: dict) -> None:
            body["facts"]["signer_role_identity_verified"] = True

        def promote_identity(body: dict) -> None:
            body["facts"]["registry_organization_identity_verified"] = True

        def promote_authority(body: dict) -> None:
            body["authority"]["writer_allowed"] = True

        def invent_records(body: dict) -> None:
            body["facts"]["source_trust_record_count"] = 6

        def mark_observed(body: dict) -> None:
            body["requirements"][0]["state"] = "OBSERVED"

        def collide_roles(body: dict) -> None:
            body["requirements"][0]["authority_role"] = body["requirements"][1][
                "authority_role"
            ]

        def disable_separation(body: dict) -> None:
            body["separation_policy"][
                "source_record_self_attestation_forbidden"
            ] = False

        def alias_port(body: dict) -> None:
            body["source"]["source_trust_source_port_version"] += ".0"

        def drift_predecessor(body: dict) -> None:
            body["source"]["intake_preregistration_hash"] = "0" * 64

        mutations = (
            promote_fact,
            promote_signer,
            promote_identity,
            promote_authority,
            invent_records,
            mark_observed,
            collide_roles,
            disable_separation,
            alias_port,
            drift_predecessor,
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                body = deepcopy(self.preregistration)
                body.pop("source_trust_preregistration_hash")
                mutate(body)
                resealed = seal_strict_canonical_document(
                    body,
                    "source_trust_preregistration_hash",
                )
                exact = self._verify(resealed)
                self.assertEqual(exact["status"], "BLOCK")
                self.assertEqual(exact["source_trust_status"], "UNKNOWN")
                self.assertFalse(exact["external_source_trust_verified"])
                self.assertFalse(exact["writer_allowed"])


if __name__ == "__main__":
    unittest.main()
