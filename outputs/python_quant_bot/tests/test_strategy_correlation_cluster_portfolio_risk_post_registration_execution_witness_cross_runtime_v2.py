from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1
    as issuance_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1
    as envelope_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7
    as registration_v7,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v4 as receipt_test_support


class PostRegistrationExecutionWitnessCrossRuntimeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        case = receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
            "test_python_clear_projection_produces_exact_local_receipt"
        )
        case.setUp()
        cls.addClassCleanup(case.doCleanups)
        manifest = (
            registration_v7.expected_presentation_consumer_implementation_sha256_v7()
        )
        cls._bundles = {}
        for state, projection in (
            ("CLEAR", case._projection()),
            ("TAIL_BLOCK", case._projection(coupled=True)),
            ("EXACT_UNKNOWN", case._projection(observations=[])),
        ):
            node = case._node(projection, f"witness-v2-{state.lower()}")
            evidence = evidence_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )
            registration = registration_v7.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )
            raw_nonce = (
                f"synthetic-cross-runtime-witness-v2-{state}-0123456789abcdef"
            )
            issuance_id = f"cross-runtime-witness-v2-{state.lower()}-0001"
            commitment = sha256(raw_nonce.encode("ascii")).hexdigest()
            preregistration = issuance_v1.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
                registration,
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
                issuance_id,
                commitment,
            )
            envelope = envelope_v1.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
                preregistration,
                registration,
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
                issuance_id,
                commitment,
            )
            cls._bundles[state] = {
                "preregistration": preregistration,
                "envelope": envelope,
                "rawNonce": raw_nonce,
            }

    def _node(self, state: str = "CLEAR", mode: str = "valid") -> dict:
        project_root = Path(__file__).resolve().parents[1]
        payload = {
            **self._bundles[state],
            "mode": mode,
            "modulePath": str(
                project_root
                / "exchange_terminal"
                / "static"
                / "evidence_portfolio_risk_post_registration_execution_witness_signature_candidate_v2.js"
            ),
            "canonicalPath": str(
                project_root
                / "exchange_terminal"
                / "static"
                / "strict_canonical_json_v1.js"
            ),
        }
        script = r"""
const fs = require('node:fs');
const crypto = require('node:crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const witness = require(input.modulePath);
const canonical = require(input.canonicalPath);
const pair = crypto.generateKeyPairSync('ed25519');
const publicDer = pair.publicKey.export({type:'spki', format:'der'});
const publicHash = crypto.createHash('sha256').update(publicDer).digest('hex');
const policy = witness.buildPostRegistrationExecutionWitnessPolicyV2(
  input.preregistration,
  input.envelope,
  {
    witness_id: 'synthetic-cross-runtime-witness-v2',
    public_key_spki_sha256: publicHash,
    policy_nonce: crypto.createHash('sha256').update('cross-runtime-policy-v2').digest('hex'),
  },
);
const rawNonce = input.mode === 'nonce-mismatch' ? input.rawNonce + '-wrong' : input.rawNonce;
const challenge = witness.buildPostRegistrationDocumentBundleChallengeV2(
  input.preregistration,
  input.envelope,
  policy,
  rawNonce,
);
const signingKey = input.mode === 'signature-substitution'
  ? crypto.generateKeyPairSync('ed25519').privateKey
  : pair.privateKey;
const signature = crypto.sign(
  null,
  Buffer.from(canonical.strictCanonicalStringify(challenge), 'utf8'),
  signingKey,
);
const attestation = canonical.sealDocument({
  schema_version: witness.ATTESTATION_SCHEMA_VERSION,
  static_fingerprint: witness.ATTESTATION_STATIC_FINGERPRINT,
  policy_hash: policy.policy_hash,
  challenge_hash: challenge.challenge_hash,
  witness_id: policy.witness.witness_id,
  key_algorithm: 'Ed25519',
  public_key_spki_sha256: publicHash,
  signed_payload: 'STRICT_CANONICAL_CHALLENGE_DOCUMENT',
  signature_base64: signature.toString('base64'),
}, 'attestation_hash');
const consumption = input.mode === 'unexpected-consumption' ? {unsupported:true} : null;
const verification = witness.verifyPostRegistrationWitnessSignatureCandidateV2(
  input.preregistration,
  input.envelope,
  policy,
  challenge,
  attestation,
  pair.publicKey,
  rawNonce,
  consumption,
);
const exact = witness.verifyPostRegistrationWitnessVerificationDocumentV2(
  verification,
  input.preregistration,
  input.envelope,
  policy,
  challenge,
  attestation,
  pair.publicKey,
  rawNonce,
  consumption,
);
process.stdout.write(JSON.stringify({policy, challenge, verification, exact}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=project_root,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_real_cross_runtime_signature_verifies_key_possession_only(
        self,
    ) -> None:
        result = self._node()
        self.assertEqual(result["policy"]["status"], "BLOCKED")
        self.assertTrue(result["policy"]["facts"]["local_policy_complete"])
        self.assertEqual(result["verification"]["status"], "BLOCKED")
        self.assertEqual(
            result["verification"]["local_signature_status"],
            "PASS",
        )
        self.assertTrue(
            result["verification"]["facts"][
                "cryptographic_key_possession_verified"
            ]
        )
        self.assertEqual(result["exact"]["status"], "PASS")
        self.assertFalse(result["exact"]["anti_replay_registry_bound"])

    def test_three_python_semantics_are_preserved_by_node(self) -> None:
        for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"):
            with self.subTest(state=state):
                result = self._node(state)
                self.assertEqual(
                    result["policy"]["source"]["execution_semantic_state"],
                    state,
                )
                self.assertEqual(
                    result["verification"]["local_signature_status"],
                    "PASS",
                )
                self.assertFalse(
                    result["verification"]["authority"]["paper_authorized"]
                )

    def test_signature_substitution_blocks_local_verification(self) -> None:
        result = self._node(mode="signature-substitution")
        self.assertEqual(
            result["verification"]["local_signature_status"],
            "BLOCK",
        )
        self.assertEqual(result["exact"]["status"], "BLOCK")

    def test_nonce_mismatch_blocks_challenge(self) -> None:
        result = self._node(mode="nonce-mismatch")
        self.assertFalse(
            result["challenge"]["facts"]["local_challenge_complete"]
        )
        self.assertEqual(
            result["verification"]["local_signature_status"],
            "BLOCK",
        )

    def test_unimplemented_consumption_receipt_is_rejected(self) -> None:
        result = self._node(mode="unexpected-consumption")
        self.assertEqual(
            result["verification"]["local_signature_status"],
            "BLOCK",
        )
        self.assertFalse(
            result["verification"]["facts"][
                "anti_replay_consumption_receipt_supported"
            ]
        )


if __name__ == "__main__":
    unittest.main()
