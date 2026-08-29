from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3
    as evidence_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5
    as registration_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3 as evidence_test_support


class PortfolioRiskPresentationExecutionWitnessCrossRuntimeV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.root = pathlib.Path(__file__).resolve().parents[1]
        self.evidence_case = (
            evidence_test_support.PortfolioRiskPresentationConsumerExecutionEvidenceV3Tests(
                "test_local_pass_receipt_builds_cross_bound_python_evidence"
            )
        )
        self.evidence_case.setUp()
        self.addCleanup(self.evidence_case.doCleanups)

    def _bundle(self) -> dict:
        receipt, projection, registration_v4 = self.evidence_case._bundle(
            "PASS"
        )
        evidence = evidence_v3.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
            receipt,
            projection,
            registration_v4,
        )
        registration = registration_v5.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            registration_v5.expected_presentation_consumer_implementation_sha256_v5()
        )
        return {
            "receipt": receipt,
            "evidence": evidence,
            "registration": registration,
        }

    def _node(self, bundle: dict, mode: str = "valid") -> dict:
        script = r"""
const fs = require("node:fs");
const crypto = require("node:crypto");
const strictCanonical = require("./exchange_terminal/static/strict_canonical_json_v1.js");
const witness = require("./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_execution_witness_signature_candidate_v1.js");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const keys = crypto.generateKeyPairSync("ed25519");
const publicKeyPem = keys.publicKey.export({format:"pem",type:"spki"}).toString();
const policy = witness.buildPreregisteredExecutionWitnessPolicyV1(
  "synthetic-cross-runtime-witness",
  publicKeyPem,
  "cross_runtime_policy_nonce_0123456789abcdef"
);
const challenge = witness.buildExecutionWitnessDocumentBundleChallengeV1(
  payload.bundle.receipt,
  payload.bundle.evidence,
  payload.bundle.registration,
  policy,
  "cross_runtime_challenge_nonce_0123456789abcd"
);
let signature = crypto.sign(
  null,
  Buffer.from(strictCanonical.strictCanonicalStringify(challenge), "utf8"),
  keys.privateKey
);
if (payload.mode === "tamper_signature") signature[0] ^= 1;
const attestation = {
  schema_version: witness.ATTESTATION_SCHEMA_VERSION,
  static_fingerprint: witness.ATTESTATION_STATIC_FINGERPRINT,
  witness_id: "synthetic-cross-runtime-witness",
  policy_hash: policy.policy_hash,
  challenge_hash: challenge.challenge_hash,
  public_key_spki_pem: publicKeyPem,
  signature_base64: signature.toString("base64")
};
const verification = witness.verifyPreregisteredExecutionWitnessSignatureCandidateV1(
  attestation,
  policy,
  challenge,
  payload.bundle.receipt,
  payload.bundle.evidence,
  payload.bundle.registration
);
const exact = witness.verifyExecutionWitnessSignatureVerificationDocumentV1(
  verification,
  attestation,
  policy,
  challenge,
  payload.bundle.receipt,
  payload.bundle.evidence,
  payload.bundle.registration
);
process.stdout.write(JSON.stringify({policy,challenge,verification,exact}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(
                {"bundle": bundle, "mode": mode},
                separators=(",", ":"),
                sort_keys=True,
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_real_cross_runtime_bundle_verifies_key_possession_only(
        self,
    ) -> None:
        result = self._node(self._bundle())
        self.assertEqual(result["policy"]["status"], "CANDIDATE")
        self.assertEqual(result["challenge"]["status"], "PASS")
        self.assertEqual(result["verification"]["status"], "PASS")
        self.assertEqual(result["exact"]["status"], "PASS")
        self.assertTrue(
            result["verification"]["facts"][
                "cryptographic_key_possession_verified"
            ]
        )
        self.assertFalse(
            result["verification"]["facts"][
                "witness_organization_identity_verified"
            ]
        )
        self.assertFalse(
            result["verification"]["facts"][
                "independent_execution_process_witnessed"
            ]
        )
        self.assertFalse(
            result["verification"]["authority"]["paper_authorized"]
        )

    def test_resealed_evidence_receipt_hash_substitution_blocks_challenge(
        self,
    ) -> None:
        bundle = self._bundle()
        evidence = copy.deepcopy(bundle["evidence"])
        evidence["source"]["receipt_v3_hash"] = "f" * 64
        bundle["evidence"] = seal_strict_canonical_document(
            evidence,
            "evidence_hash",
        )
        result = self._node(bundle)
        self.assertEqual(result["challenge"]["status"], "BLOCK")
        self.assertIn(
            "receipt_v3_to_evidence_v3_hash_bound",
            result["challenge"]["blockers"],
        )
        self.assertEqual(result["verification"]["status"], "BLOCK")

    def test_signature_substitution_blocks_cross_runtime_verification(
        self,
    ) -> None:
        result = self._node(self._bundle(), "tamper_signature")
        self.assertEqual(result["challenge"]["status"], "PASS")
        self.assertEqual(result["verification"]["status"], "BLOCK")
        self.assertIn(
            "ed25519_detached_signature_verified",
            result["verification"]["blockers"],
        )
        self.assertFalse(
            result["verification"]["facts"][
                "cryptographic_key_possession_verified"
            ]
        )


if __name__ == "__main__":
    unittest.main()
