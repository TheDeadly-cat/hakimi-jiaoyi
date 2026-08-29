from __future__ import annotations

import base64
import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
MODULE = (
    "./exchange_terminal/static/"
    "evidence_anti_replay_registry_organization_identity_signed_artifact_"
    "bundle_aggregation_candidate_v1.js"
)
NODE_SCRIPT = r"""
"use strict";
const crypto = require("node:crypto");
const fs = require("node:fs");
const aggregationV1 = require(inputModulePlaceholder);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
try {
  const items = input.items.map((item) => ({
    detachedSignature: Buffer.from(item.signature_b64, "base64"),
    payload: item.payload,
    publicKey: crypto.createPublicKey({
      key: Buffer.from(item.public_key_der_b64, "base64"),
      format: "der",
      type: "spki",
    }),
    reference: item.reference,
  }));
  const aggregation =
    aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
      input.envelope,
      items
    );
  let document = aggregation;
  if (input.mode === "tamper-aggregation") {
    document = structuredClone(aggregation);
    document.facts.registry_organization_identity_verified = true;
  }
  const exact =
    aggregationV1.verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
      input.envelope,
      items,
      document
    );
  process.stdout.write(JSON.stringify({ aggregation, exact }));
} catch (error) {
  process.stdout.write(JSON.stringify({
    error: error instanceof Error ? error.message : String(error),
  }));
}
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


class RegistryOrganizationIdentitySignedArtifactBundleCrossRuntimeV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_time_ms = 10_000_000
        cls.kwargs = {
            "registry_id": "synthetic.cross.runtime.aggregate.registry",
            "operator_identity_claim": "synthetic-cross-runtime-aggregate-claim",
            "public_key_spki_sha256": sha256(
                b"synthetic-cross-runtime-aggregate-subject"
            ).hexdigest(),
            "trust_domain": "synthetic.cross.runtime.aggregate.test",
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
        cls.private_keys: list[Ed25519PrivateKey] = []
        cls.items: list[dict] = []
        references = []
        for kind in RegistryOrganizationIdentityEvidenceKindV1:
            private_key = Ed25519PrivateKey.generate()
            public_key_der = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            metadata = {
                "evidence_kind": kind.value,
                "evidence_schema_version": expected_evidence_schema_v1(kind),
                "expires_at_ms": cls.reference_time_ms + 1_000,
                "issued_at_ms": cls.reference_time_ms - 1_000,
                "signature_algorithm": "ed25519",
                "signer_public_key_spki_sha256": sha256(
                    public_key_der
                ).hexdigest(),
                "signer_role": expected_signer_role_v1(kind),
                "subject_public_key_spki_sha256": cls.kwargs[
                    "public_key_spki_sha256"
                ],
                "subject_registry_id": cls.kwargs["registry_id"],
            }
            payload = {
                "evidence_body": {
                    "marker": f"cross-runtime-body:{kind.value}",
                    "record_sha256": sha256(
                        f"cross-runtime-record:{kind.value}".encode("ascii")
                    ).hexdigest(),
                    "synthetic": True,
                },
                "evidence_kind": metadata["evidence_kind"],
                "expires_at_ms": metadata["expires_at_ms"],
                "issued_at_ms": metadata["issued_at_ms"],
                "schema_version": metadata["evidence_schema_version"],
                "signature_algorithm": metadata["signature_algorithm"],
                "signed_payload_context": (
                    "STRICT_CANONICAL_REGISTRY_ORGANIZATION_IDENTITY_"
                    "EVIDENCE_ARTIFACT_V1"
                ),
                "signer": {
                    "public_key_spki_sha256": metadata[
                        "signer_public_key_spki_sha256"
                    ],
                    "role": metadata["signer_role"],
                },
                "subject": {
                    "public_key_spki_sha256": metadata[
                        "subject_public_key_spki_sha256"
                    ],
                    "registry_id": metadata["subject_registry_id"],
                },
            }
            artifact_hash = _canonical_hash(payload)
            reference = RegistryOrganizationIdentityEvidenceReferenceV1(
                kind=kind,
                evidence_schema_version=metadata["evidence_schema_version"],
                artifact_sha256=artifact_hash,
                signer_role=metadata["signer_role"],
                signer_public_key_spki_sha256=metadata[
                    "signer_public_key_spki_sha256"
                ],
                subject_registry_id=metadata["subject_registry_id"],
                subject_public_key_spki_sha256=metadata[
                    "subject_public_key_spki_sha256"
                ],
                issued_at_ms=metadata["issued_at_ms"],
                expires_at_ms=metadata["expires_at_ms"],
            )
            reference_document = {
                "artifact_sha256": reference.artifact_sha256,
                "evidence_kind": reference.kind.value,
                "evidence_schema_version": reference.evidence_schema_version,
                "expires_at_ms": reference.expires_at_ms,
                "issued_at_ms": reference.issued_at_ms,
                "schema_version": reference.schema_version,
                "signature_algorithm": reference.signature_algorithm,
                "signer_public_key_spki_sha256": (
                    reference.signer_public_key_spki_sha256
                ),
                "signer_role": reference.signer_role,
                "subject_public_key_spki_sha256": (
                    reference.subject_public_key_spki_sha256
                ),
                "subject_registry_id": reference.subject_registry_id,
            }
            cls.private_keys.append(private_key)
            cls.items.append(
                {
                    "payload": payload,
                    "public_key_der_b64": base64.b64encode(
                        public_key_der
                    ).decode("ascii"),
                    "reference": reference_document,
                    "signature_b64": base64.b64encode(
                        private_key.sign(_canonical_bytes(payload))
                    ).decode("ascii"),
                }
            )
            references.append(reference)
        cls.references = tuple(references)
        cls.evaluation = evaluation_v1.evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
            cls.intake,
            cls.identity,
            cls.references,
            cls.reference_time_ms,
            **cls.kwargs,
        )
        cls.envelope = envelope_v1.build_anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1(
            cls.evaluation,
            cls.intake,
            cls.identity,
            cls.references,
            cls.reference_time_ms,
            **cls.kwargs,
        )

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
        envelope: dict | None = None,
        items: list[dict] | None = None,
        mode: str = "verify",
    ) -> dict:
        return self._run_node(
            {
                "envelope": envelope or self.envelope,
                "items": items or self.items,
                "mode": mode,
            }
        )

    def test_real_python_envelope_and_six_signatures_aggregate_in_node(self) -> None:
        row = self._verify()
        aggregation = row["aggregation"]
        exact = row["exact"]
        self.assertEqual(aggregation["status"], "BLOCKED")
        self.assertEqual(
            aggregation["local_signed_artifact_bundle_status"],
            "CRYPTOGRAPHIC_BINDING_PASS",
        )
        self.assertTrue(aggregation["facts"]["evidence_signatures_verified"])
        self.assertFalse(aggregation["facts"]["python_process_authenticated"])
        self.assertFalse(
            aggregation["facts"]["registry_organization_identity_verified"]
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["aggregation_status"], "BLOCKED")
        self.assertFalse(exact["registry_organization_identity_verified"])

    def test_single_signature_substitution_remains_exact_local_block(self) -> None:
        items = copy.deepcopy(self.items)
        signature = bytearray(base64.b64decode(items[0]["signature_b64"]))
        signature[0] ^= 0xFF
        items[0]["signature_b64"] = base64.b64encode(signature).decode("ascii")
        row = self._verify(items=items)
        self.assertEqual(
            row["aggregation"]["local_signed_artifact_bundle_status"],
            "BLOCK",
        )
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertTrue(row["exact"]["aggregation_document_exactly_rebuilt"])
        self.assertEqual(row["exact"]["aggregation_status"], "BLOCKED")

    def test_resigned_payload_substitution_fails_frozen_reference(self) -> None:
        items = copy.deepcopy(self.items)
        payload = items[0]["payload"]
        payload["evidence_body"]["record_sha256"] = sha256(
            b"cross-runtime-substituted-record"
        ).hexdigest()
        items[0]["signature_b64"] = base64.b64encode(
            self.private_keys[0].sign(_canonical_bytes(payload))
        ).decode("ascii")
        row = self._verify(items=items)
        self.assertEqual(
            row["aggregation"]["local_signed_artifact_bundle_status"],
            "BLOCK",
        )
        self.assertFalse(
            row["aggregation"]["artifacts"][0]["evidence_signature_verified"]
        )

    def test_public_key_substitution_fails_closed(self) -> None:
        items = copy.deepcopy(self.items)
        other_public_der = (
            Ed25519PrivateKey.generate()
            .public_key()
            .public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        items[0]["public_key_der_b64"] = base64.b64encode(
            other_public_der
        ).decode("ascii")
        row = self._verify(items=items)
        self.assertEqual(
            row["aggregation"]["local_signed_artifact_bundle_status"],
            "BLOCK",
        )
        self.assertEqual(row["exact"]["status"], "BLOCK")

    def test_resealed_python_envelope_promotion_is_rejected(self) -> None:
        body = copy.deepcopy(self.envelope)
        body.pop("envelope_hash")
        body["facts"]["registry_organization_identity_verified"] = True
        envelope = seal_strict_canonical_document(body, "envelope_hash")
        row = self._verify(envelope=envelope)
        self.assertIn("not exact", row["error"])

    def test_tampered_aggregate_promotion_becomes_unknown(self) -> None:
        row = self._verify(mode="tamper-aggregation")
        exact = row["exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["aggregation_document_exactly_rebuilt"])
        self.assertEqual(exact["aggregation_status"], "UNKNOWN")
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_aggregate_output_contains_no_input_material(self) -> None:
        row = self._verify()
        serialized = json.dumps(row["aggregation"], sort_keys=True)
        for index, item in enumerate(self.items):
            private_der = self.private_keys[index].private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            self.assertNotIn(
                item["payload"]["evidence_body"]["marker"],
                serialized,
            )
            self.assertNotIn(item["public_key_der_b64"], serialized)
            self.assertNotIn(item["signature_b64"], serialized)
            self.assertNotIn(
                base64.b64encode(private_der).decode("ascii"),
                serialized,
            )
            self.assertNotIn(private_der.hex(), serialized)
        self.assertFalse(
            row["aggregation"]["facts"]["private_key_material_received"]
        )


if __name__ == "__main__":
    unittest.main()
