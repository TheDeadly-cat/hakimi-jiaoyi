from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
MODULE = (
    "./exchange_terminal/static/"
    "evidence_anti_replay_registry_organization_identity_"
    "signed_artifact_candidate_v1.js"
)

NODE_SCRIPT = r"""
"use strict";
const crypto = require("node:crypto");
const fs = require("node:fs");
const candidateV1 = require(inputModulePlaceholder);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const publicKey = crypto.createPublicKey({
  key: Buffer.from(input.public_key_der_b64, "base64"),
  format: "der",
  type: "spki",
});
const signature = Buffer.from(input.signature_b64, "base64");
const verification =
  candidateV1.verifyRegistryOrganizationIdentitySignedArtifactCandidateV1(
    input.reference,
    input.payload,
    publicKey,
    signature
  );
let document = verification;
if (input.mode === "tamper-verification") {
  document = structuredClone(verification);
  document.facts.registry_organization_identity_verified = true;
}
const exact =
  candidateV1.verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
    input.reference,
    input.payload,
    publicKey,
    signature,
    document
  );
process.stdout.write(JSON.stringify({ exact, verification }));
""".replace("inputModulePlaceholder", json.dumps(MODULE))


def _canonical_bytes(document: dict) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_hash(document: dict) -> str:
    return sha256(_canonical_bytes(document)).hexdigest()


class RegistryOrganizationIdentitySignedArtifactCrossRuntimeV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key_der = cls.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cls.metadata = {
            "evidence_kind": "ORGANIZATION_REGISTRY_ATTESTATION",
            "evidence_schema_version": (
                "registry-organization-authority-attestation-v1"
            ),
            "expires_at_ms": 20_000_000,
            "issued_at_ms": 10_000_000,
            "signature_algorithm": "ed25519",
            "signer_public_key_spki_sha256": sha256(
                cls.public_key_der
            ).hexdigest(),
            "signer_role": "organization_registry_authority",
            "subject_public_key_spki_sha256": sha256(
                b"synthetic-cross-runtime-subject-key"
            ).hexdigest(),
            "subject_registry_id": "synthetic.cross.runtime.organization.registry",
        }
        cls.payload = {
            "evidence_body": {
                "record_sha256": sha256(
                    b"synthetic-cross-runtime-organization-record"
                ).hexdigest(),
                "record_type": "synthetic_organization_registry_record",
                "synthetic": True,
            },
            "evidence_kind": cls.metadata["evidence_kind"],
            "expires_at_ms": cls.metadata["expires_at_ms"],
            "issued_at_ms": cls.metadata["issued_at_ms"],
            "schema_version": cls.metadata["evidence_schema_version"],
            "signature_algorithm": cls.metadata["signature_algorithm"],
            "signed_payload_context": (
                "STRICT_CANONICAL_REGISTRY_ORGANIZATION_IDENTITY_"
                "EVIDENCE_ARTIFACT_V1"
            ),
            "signer": {
                "public_key_spki_sha256": cls.metadata[
                    "signer_public_key_spki_sha256"
                ],
                "role": cls.metadata["signer_role"],
            },
            "subject": {
                "public_key_spki_sha256": cls.metadata[
                    "subject_public_key_spki_sha256"
                ],
                "registry_id": cls.metadata["subject_registry_id"],
            },
        }
        cls.reference = {
            **cls.metadata,
            "artifact_sha256": _canonical_hash(cls.payload),
            "schema_version": (
                "registry-organization-identity-evidence-reference-v1"
            ),
        }
        cls.signature = cls.private_key.sign(_canonical_bytes(cls.payload))

    @staticmethod
    def _run_node(payload: dict) -> dict:
        completed = subprocess.run(
            ["node", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(payload, sort_keys=True),
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def _verify(
        self,
        *,
        mode: str = "verify",
        payload: dict | None = None,
        public_key_der: bytes | None = None,
        reference: dict | None = None,
        signature: bytes | None = None,
    ) -> dict:
        return self._run_node(
            {
                "mode": mode,
                "payload": payload or self.payload,
                "public_key_der_b64": base64.b64encode(
                    public_key_der or self.public_key_der
                ).decode("ascii"),
                "reference": reference or self.reference,
                "signature_b64": base64.b64encode(
                    signature or self.signature
                ).decode("ascii"),
            }
        )

    def test_python_payload_hash_and_signature_verify_in_node(self) -> None:
        row = self._verify()
        verification = row["verification"]
        exact = row["exact"]
        self.assertEqual(verification["status"], "BLOCKED")
        self.assertEqual(verification["local_signed_artifact_status"], "PASS")
        self.assertTrue(verification["facts"]["evidence_signature_verified"])
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["verification_status"], "BLOCKED")
        self.assertFalse(exact["evidence_payload_semantics_verified"])
        self.assertFalse(exact["external_source_trust_verified"])
        self.assertFalse(exact["registry_organization_identity_verified"])

    def test_resigned_payload_substitution_still_fails_reference_hash(self) -> None:
        payload = deepcopy(self.payload)
        payload["evidence_body"]["record_sha256"] = sha256(
            b"substituted-cross-runtime-record"
        ).hexdigest()
        signature = self.private_key.sign(_canonical_bytes(payload))
        row = self._verify(payload=payload, signature=signature)
        self.assertEqual(
            row["verification"]["local_signed_artifact_status"], "BLOCK"
        )
        self.assertFalse(row["verification"]["facts"]["artifact_hash_matched"])
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertEqual(row["exact"]["verification_status"], "BLOCKED")

    def test_reference_subject_substitution_fails_payload_binding(self) -> None:
        reference = dict(self.reference)
        reference["subject_registry_id"] = "synthetic.substituted.registry"
        row = self._verify(reference=reference)
        self.assertEqual(
            row["verification"]["local_signed_artifact_status"], "BLOCK"
        )
        self.assertFalse(
            row["verification"]["facts"]["evidence_payload_schema_bound"]
        )

    def test_signature_and_public_key_substitution_fail_closed(self) -> None:
        signature = bytearray(self.signature)
        signature[0] ^= 0xFF
        signature_row = self._verify(signature=bytes(signature))
        other_public_der = (
            Ed25519PrivateKey.generate()
            .public_key()
            .public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        key_row = self._verify(public_key_der=other_public_der)
        for row in (signature_row, key_row):
            with self.subTest(blockers=row["verification"]["blockers"]):
                self.assertEqual(
                    row["verification"]["local_signed_artifact_status"],
                    "BLOCK",
                )
                self.assertEqual(row["exact"]["status"], "BLOCK")
                self.assertFalse(
                    row["exact"]["registry_organization_identity_verified"]
                )

    def test_tampered_promotion_is_unknown_and_has_no_authority(self) -> None:
        row = self._verify(mode="tamper-verification")
        exact = row["exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["verification_document_exactly_rebuilt"])
        self.assertEqual(exact["verification_status"], "UNKNOWN")
        self.assertFalse(exact["current_admission_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_verification_output_contains_no_input_material(self) -> None:
        row = self._verify()
        serialized = json.dumps(row["verification"], sort_keys=True)
        private_key_der = self.private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.assertNotIn(self.signature.hex(), serialized)
        self.assertNotIn(base64.b64encode(self.signature).decode("ascii"), serialized)
        self.assertNotIn(
            base64.b64encode(self.public_key_der).decode("ascii"), serialized
        )
        self.assertNotIn(
            base64.b64encode(private_key_der).decode("ascii"), serialized
        )
        self.assertNotIn(private_key_der.hex(), serialized)
        self.assertNotIn(self.payload["evidence_body"]["record_type"], serialized)
        self.assertFalse(
            row["verification"]["facts"]["private_key_material_received"]
        )


if __name__ == "__main__":
    unittest.main()
