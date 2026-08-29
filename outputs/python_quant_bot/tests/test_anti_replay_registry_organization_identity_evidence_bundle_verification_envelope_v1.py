from __future__ import annotations

import base64
import copy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1
    as evaluation_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1
    as envelope_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1
    as intake_v1,
)
from exchange_terminal.interfaces.registry_organization_identity import (
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
    expected_evidence_schema_v1,
    expected_signer_role_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = r"""
"use strict";
const fs = require("node:fs");
const canonical = require(
  "./exchange_terminal/static/strict_canonical_json_v1.js"
);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const envelope = input.envelope;
const serialized = JSON.stringify(envelope);
process.stdout.write(JSON.stringify({
  authority_locked: Object.values(envelope.authority).every(
    (value) => value === false
  ),
  claim_absent: !serialized.includes(input.operator_identity_claim),
  documents_absent:
    envelope.facts.evaluation_document_embedded === false &&
    envelope.facts.identity_preregistration_document_embedded === false &&
    envelope.facts.intake_preregistration_document_embedded === false,
  envelope_sealed: canonical.verifySealedDocument(
    envelope,
    "envelope_hash"
  ),
  schema_exact:
    envelope.schema_version ===
    "anti-replay-registry-organization-identity-evidence-bundle-python-verification-envelope-v1",
  status: envelope.status,
}));
"""


class RegistryOrganizationIdentityBundleVerificationEnvelopeV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_time_ms = 10_000_000
        cls.kwargs = {
            "registry_id": "synthetic.envelope.registry",
            "operator_identity_claim": "synthetic-envelope-operator-claim",
            "public_key_spki_sha256": sha256(
                b"synthetic-envelope-subject-key"
            ).hexdigest(),
            "trust_domain": "synthetic.envelope.test",
            "adapter_protocol_version": identity_v1.ADAPTER_PROTOCOL_VERSION,
        }
        identity_kwargs = dict(cls.kwargs)
        identity_kwargs.pop("adapter_protocol_version")
        cls.identity = (
            identity_v1.build_anti_replay_registry_identity_preregistration_v1(
                **identity_kwargs
            )
        )
        cls.intake = intake_v1.build_anti_replay_registry_organization_identity_intake_preregistration_v1(
            cls.identity,
            **cls.kwargs,
        )
        cls.references = tuple(
            RegistryOrganizationIdentityEvidenceReferenceV1(
                kind=kind,
                evidence_schema_version=expected_evidence_schema_v1(kind),
                artifact_sha256=sha256(
                    f"envelope:{kind.value}:artifact".encode("ascii")
                ).hexdigest(),
                signer_role=expected_signer_role_v1(kind),
                signer_public_key_spki_sha256=sha256(
                    f"envelope:{kind.value}:signer".encode("ascii")
                ).hexdigest(),
                subject_registry_id=cls.kwargs["registry_id"],
                subject_public_key_spki_sha256=cls.kwargs[
                    "public_key_spki_sha256"
                ],
                issued_at_ms=cls.reference_time_ms - 1_000,
                expires_at_ms=cls.reference_time_ms + 1_000,
            )
            for kind in RegistryOrganizationIdentityEvidenceKindV1
        )
        cls.evaluation = evaluation_v1.evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
            cls.intake,
            cls.identity,
            cls.references,
            cls.reference_time_ms,
            **cls.kwargs,
        )

    def _inputs(self) -> tuple:
        return (
            copy.deepcopy(self.evaluation),
            copy.deepcopy(self.intake),
            copy.deepcopy(self.identity),
            self.references,
            self.reference_time_ms,
        )

    def _build(self, inputs: tuple | None = None) -> dict:
        return envelope_v1.build_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            *(self._inputs() if inputs is None else inputs),
            **self.kwargs,
        )

    def test_public_versions_and_implementation_pins_are_exact(self) -> None:
        self.assertTrue(envelope_v1.SCHEMA_VERSION.endswith("envelope-v1"))
        self.assertEqual(
            envelope_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256,
            "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f",
        )
        self.assertEqual(
            envelope_v1.INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256,
            "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56",
        )
        self.assertEqual(
            envelope_v1.EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256,
            "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f",
        )
        self.assertEqual(
            envelope_v1.BUNDLE_EVALUATION_IMPLEMENTATION_SHA256,
            "fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055",
        )
        self.assertEqual(
            envelope_v1.SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256,
            "3f31febbc017d57cee6dd666751f83f2796fd60257aab0d211156e70b47cfecc",
        )

    def test_exact_local_bundle_builds_pass_summary_envelope(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(
            envelope["verification"]["bundle_evaluation_status"],
            "BLOCKED",
        )
        self.assertEqual(
            envelope["verification"]["bundle_local_status"],
            evaluation_v1.LOCAL_PASS_STATUS,
        )
        self.assertEqual(envelope["source"]["evidence_reference_count"], 6)
        self.assertTrue(
            envelope["facts"]["local_structure_binding_freshness_verified"]
        )
        self.assertFalse(
            envelope["facts"]["registry_organization_identity_verified"]
        )
        self.assertFalse(envelope["facts"]["evidence_signatures_verified"])

    def test_public_exact_verifier_requires_exact_pass_envelope(self) -> None:
        inputs = self._inputs()
        envelope = self._build(inputs)
        exact = envelope_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            envelope,
            *inputs,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["envelope_status"], "PASS")
        self.assertEqual(exact["bundle_evaluation_status"], "BLOCKED")
        self.assertFalse(exact["evidence_signatures_verified"])
        self.assertFalse(exact["external_source_trust_verified"])
        self.assertFalse(exact["registry_organization_identity_verified"])
        self.assertFalse(exact["current_admission_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_exact_stale_bundle_envelope_remains_public_verifier_block(self) -> None:
        references = list(self.references)
        references[0] = replace(
            references[0],
            issued_at_ms=1,
            expires_at_ms=2,
        )
        stale_references = tuple(references)
        evaluation = evaluation_v1.evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
            self.intake,
            self.identity,
            stale_references,
            self.reference_time_ms,
            **self.kwargs,
        )
        inputs = (
            evaluation,
            self.intake,
            self.identity,
            stale_references,
            self.reference_time_ms,
        )
        envelope = self._build(inputs)
        self.assertEqual(envelope["status"], "BLOCK")
        exact = envelope_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            envelope,
            *inputs,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertTrue(exact["envelope_exactly_rebuilt"])
        self.assertEqual(exact["envelope_status"], "BLOCK")

    def test_resealed_evaluation_promotion_blocks_envelope(self) -> None:
        inputs = list(self._inputs())
        body = inputs[0]
        body.pop("evaluation_hash")
        body["facts"]["evidence_signatures_verified"] = True
        inputs[0] = seal_strict_canonical_document(body, "evaluation_hash")
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
            "bundle_evaluation_v1_public_exact_verifier_pass",
            envelope["blockers"],
        )
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
            "signature_source_revocation_and_identity_remain_unverified",
            envelope["blockers"],
        )

    def test_intake_hash_substitution_blocks_both_hash_edges(self) -> None:
        inputs = list(self._inputs())
        intake = inputs[1]
        intake.pop("intake_preregistration_hash")
        intake["source"]["identity_preregistration_hash"] = "a" * 64
        inputs[1] = seal_strict_canonical_document(
            intake,
            "intake_preregistration_hash",
        )
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
            "organization_identity_intake_v1_exact",
            envelope["blockers"],
        )
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
            "identity_preregistration_hash_edge_exact",
            envelope["blockers"],
        )

    def test_missing_or_duplicate_reference_set_blocks_without_throwing(self) -> None:
        invalid_sets = (
            self.references[:-1],
            self.references[:-1] + (self.references[0],),
        )
        for references in invalid_sets:
            with self.subTest(count=len(references)):
                inputs = list(self._inputs())
                inputs[3] = references
                envelope = self._build(tuple(inputs))
                self.assertEqual(envelope["status"], "BLOCK")
                self.assertIn(
                    "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
                    "six_reference_set_and_order_exact",
                    envelope["blockers"],
                )

    def test_reference_time_substitution_blocks_exact_evaluation(self) -> None:
        inputs = list(self._inputs())
        inputs[4] = self.reference_time_ms + 1
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:"
            "bundle_evaluation_v1_public_exact_verifier_pass",
            envelope["blockers"],
        )
        self.assertIn(
            "BUNDLE_PYTHON_ENVELOPE_CHECK_FAILED:explicit_reference_time_exact",
            envelope["blockers"],
        )

    def test_resealed_envelope_authority_promotion_is_not_exact(self) -> None:
        inputs = self._inputs()
        envelope = self._build(inputs)
        body = envelope
        body.pop("envelope_hash")
        body["authority"]["writer_allowed"] = True
        tampered = seal_strict_canonical_document(body, "envelope_hash")
        exact = envelope_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            tampered,
            *inputs,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["envelope_exactly_rebuilt"])
        self.assertEqual(exact["envelope_status"], "UNKNOWN")

    def test_envelope_is_hash_only_neutral_and_material_free(self) -> None:
        envelope = self._build()
        serialized = json.dumps(envelope, sort_keys=True)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertNotIn("artifact_payload", serialized)
        self.assertNotIn("signature_material", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertFalse(envelope["facts"]["evaluation_document_embedded"])
        self.assertFalse(envelope["facts"]["evidence_references_embedded"])
        self.assertFalse(envelope["facts"]["operator_identity_claim_embedded"])
        self.assertFalse(envelope["facts"]["node_process_executed"])
        self.assertFalse(envelope["facts"]["profitability_proven"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(serialized, promotion)

    def test_python_envelope_seal_is_consumable_by_node(self) -> None:
        envelope = self._build()
        completed = subprocess.run(
            ["node", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(
                {
                    "envelope": envelope,
                    "operator_identity_claim": self.kwargs[
                        "operator_identity_claim"
                    ],
                },
                sort_keys=True,
            ),
            capture_output=True,
            check=True,
            text=True,
        )
        row = json.loads(completed.stdout)
        self.assertTrue(row["envelope_sealed"])
        self.assertTrue(row["schema_exact"])
        self.assertTrue(row["authority_locked"])
        self.assertTrue(row["claim_absent"])
        self.assertTrue(row["documents_absent"])
        self.assertEqual(row["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
