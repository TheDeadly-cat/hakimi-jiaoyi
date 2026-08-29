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

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as preregistration_v1,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE = (
    "./exchange_terminal/static/"
    "evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js"
)

NODE_SCRIPT = r"""
"use strict";
const crypto = require("node:crypto");
const fs = require("node:fs");
const candidateV1 = require(inputModulePlaceholder);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const rawNonce = Buffer.from(input.raw_nonce_b64, "base64");

if (input.mode === "challenge") {
  const policy = candidateV1.buildAntiReplayRegistryKeyPossessionPolicyV1(
    input.preregistration
  );
  const challenge = candidateV1.buildAntiReplayRegistryKeyPossessionChallengeV1(
    policy,
    rawNonce
  );
  process.stdout.write(JSON.stringify({ policy, challenge }));
} else {
  const publicKey = crypto.createPublicKey({
    key: Buffer.from(input.public_key_der_b64, "base64"),
    format: "der",
    type: "spki",
  });
  const signature = Buffer.from(input.signature_b64, "base64");
  const verification = candidateV1.verifyAntiReplayRegistryKeyPossessionCandidateV1(
    input.preregistration,
    input.policy,
    input.challenge,
    rawNonce,
    publicKey,
    signature
  );
  let document = verification;
  if (input.mode === "tamper-verification") {
    document = structuredClone(verification);
    document.facts.registry_organization_identity_verified = true;
  }
  const exact =
    candidateV1.verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1(
      input.preregistration,
      input.policy,
      input.challenge,
      rawNonce,
      publicKey,
      signature,
      document
    );
  process.stdout.write(JSON.stringify({ exact, verification }));
}
""".replace("inputModulePlaceholder", json.dumps(MODULE))


def _canonical_bytes(document: dict) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class AntiReplayRegistryEd25519KeyPossessionCrossRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key_der = cls.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cls.raw_nonce = sha256(b"synthetic-registry-key-possession-nonce").digest()
        cls.preregistration = (
            preregistration_v1.build_anti_replay_registry_identity_preregistration_v1(
                registry_id="synthetic.cross.runtime.registry",
                operator_identity_claim="synthetic-cross-runtime-operator-claim",
                public_key_spki_sha256=sha256(cls.public_key_der).hexdigest(),
                trust_domain="synthetic.cross.runtime.test",
            )
        )
        challenge = cls._run_node(
            {
                "mode": "challenge",
                "preregistration": cls.preregistration,
                "raw_nonce_b64": base64.b64encode(cls.raw_nonce).decode("ascii"),
            }
        )
        cls.policy = challenge["policy"]
        cls.challenge = challenge["challenge"]
        cls.signature = cls.private_key.sign(_canonical_bytes(cls.challenge))

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
        raw_nonce: bytes | None = None,
        public_key_der: bytes | None = None,
        signature: bytes | None = None,
    ) -> dict:
        return self._run_node(
            {
                "challenge": self.challenge,
                "mode": mode,
                "policy": self.policy,
                "preregistration": self.preregistration,
                "public_key_der_b64": base64.b64encode(
                    public_key_der or self.public_key_der
                ).decode("ascii"),
                "raw_nonce_b64": base64.b64encode(
                    raw_nonce or self.raw_nonce
                ).decode("ascii"),
                "signature_b64": base64.b64encode(
                    signature or self.signature
                ).decode("ascii"),
            }
        )

    def test_python_preregistration_and_signature_verify_in_node(self) -> None:
        row = self._verify()
        self.assertEqual(row["verification"]["status"], "BLOCKED")
        self.assertEqual(
            row["verification"]["local_registry_key_possession_status"], "PASS"
        )
        self.assertEqual(row["exact"]["status"], "PASS")
        self.assertEqual(row["exact"]["verification_status"], "BLOCKED")
        self.assertFalse(row["exact"]["registry_organization_identity_verified"])
        self.assertFalse(row["exact"]["adapter_conformance_verified"])

    def test_signature_substitution_fails_closed(self) -> None:
        signature = bytearray(self.signature)
        signature[0] ^= 0xFF
        row = self._verify(signature=bytes(signature))
        self.assertEqual(
            row["verification"]["local_registry_key_possession_status"], "BLOCK"
        )
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertTrue(row["exact"]["verification_document_exactly_rebuilt"])

    def test_nonce_mismatch_fails_closed(self) -> None:
        row = self._verify(raw_nonce=sha256(b"wrong-nonce").digest())
        self.assertEqual(
            row["verification"]["local_registry_key_possession_status"], "BLOCK"
        )
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertFalse(row["exact"]["registry_key_possession_verified"])

    def test_public_key_substitution_fails_closed(self) -> None:
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        row = self._verify(public_key_der=other)
        self.assertEqual(
            row["verification"]["local_registry_key_possession_status"], "BLOCK"
        )
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertFalse(row["exact"]["registry_key_possession_verified"])

    def test_tampered_verification_is_unknown_and_has_no_authority(self) -> None:
        row = self._verify(mode="tamper-verification")
        exact = row["exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["verification_document_exactly_rebuilt"])
        self.assertEqual(exact["verification_status"], "UNKNOWN")
        self.assertFalse(exact["current_admission_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])


if __name__ == "__main__":
    unittest.main()
