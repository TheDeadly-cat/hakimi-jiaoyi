from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import unittest

from cryptography.hazmat.primitives import serialization

import tests.test_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_cross_runtime_v1 as aggregation_support


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = r"""
"use strict";
const crypto = require("node:crypto");
const fs = require("node:fs");
const canonical = require("./exchange_terminal/static/strict_canonical_json_v1.js");
const projectionV1 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_projection_v1.js");
const aggregationV1 = require("./exchange_terminal/static/evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js");
const projectionV2 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_projection_v2.js");
const cardV2 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_card_v2.js");
const fixtureV2 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_consumer_fixture_v2.js");
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
  const aggregate =
    aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
      input.envelope,
      items
    );
  const aggregateExact =
    aggregationV1.verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
      input.envelope,
      items,
      aggregate
    );
  const predecessorBody = {
    authority: {
      current_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      post_registration_receipt_issuance_allowed: false,
      presentation_mount_allowed: false,
      runtime_gate_activation_allowed: false,
      writer_allowed: false,
    },
    blockers: [
      "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
      "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
      "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
      "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
      "TRUSTED_REGISTRY_TIME_UNVERIFIED",
      "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
      "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
    ],
    decision:
      "LOCAL_REGISTRY_KEY_POSSESSION_OBSERVED_EXTERNAL_EVIDENCE_GAPS_REMAIN",
    facts: {
      adapter_conformance_verified: false,
      external_linearizability_verified: false,
      gap_count: 7,
      local_registry_key_possession_verified: true,
      post_registration_receipt_issued: false,
      projection_descriptive_only: true,
      registry_organization_identity_verified: false,
      target_consumption_receipt_issued: false,
      trusted_registry_time_verified: false,
    },
    schema_version: projectionV1.PROJECTION_SCHEMA_VERSION,
    source: {
      attestation_hash: "a".repeat(64),
      challenge_hash: "b".repeat(64),
      key_algorithm: "Ed25519",
      policy_hash: "c".repeat(64),
      preregistration_hash: "d".repeat(64),
      public_key_spki_sha256: aggregate.source.public_key_spki_sha256,
      registry_id:
        input.mode === "binding-mismatch"
          ? "synthetic.substituted.registry"
          : aggregate.source.registry_id,
      verification_hash: "e".repeat(64),
    },
    stage_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
    stages: {
      gap: {
        items: projectionV1.GAP_ITEMS.map((item) => ({ ...item })),
        state: "OPEN",
      },
      maturity: {
        adapter_conformance: "UNEXECUTED",
        external_registry_behavior: "UNVERIFIED",
        local_key_possession: "PASS",
        state: "LOCAL_ONLY",
      },
      permission: {
        current: "LOCKED",
        live: "LOCKED",
        mount: "LOCKED",
        paper: "LOCKED",
        receipt_issuance: "LOCKED",
        runtime: "LOCKED",
        state: "LOCKED",
        writer: "LOCKED",
      },
      source: {
        contract:
          "anti-replay-registry-ed25519-key-possession-verification-candidate-v1",
        local_key_possession: "PASS",
        state: "HASH_BOUND",
      },
    },
    static_fingerprint: projectionV1.PROJECTION_STATIC_FINGERPRINT,
    status: "BLOCKED",
  };
  const predecessor = canonical.sealDocument(
    predecessorBody,
    "projection_hash"
  );
  const predecessorExact = {
    blockers: [],
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    projection_document_exactly_rebuilt: true,
    projection_status: "BLOCKED",
    runtime_gate_activation_allowed: false,
    schema_version: "anti-replay-registry-gap-projection-exact-rebuild-v1",
    status: "PASS",
    writer_allowed: false,
  };
  const projection = projectionV2.buildAntiReplayRegistryGapProjectionV2(
    predecessor,
    predecessorExact,
    aggregate,
    aggregateExact
  );
  const fixture =
    fixtureV2.buildAntiReplayRegistryGapPresentationConsumerFixtureV2(
      projection
    );
  let candidate = fixture;
  if (input.mode === "tamper-fixture") {
    candidate = structuredClone(fixture);
    candidate.facts.mounted = true;
  }
  const fixtureExact =
    fixtureV2.verifyAntiReplayRegistryGapPresentationConsumerFixtureV2(
      projection,
      candidate
    );
  process.stdout.write(JSON.stringify({
    aggregate,
    fixture,
    fixture_exact: fixtureExact,
    html: cardV2.renderAntiReplayRegistryGapCardV2(projection),
    projection,
    view_model: cardV2.buildAntiReplayRegistryGapViewModelV2(projection),
  }));
} catch (error) {
  process.stdout.write(JSON.stringify({
    error: error instanceof Error ? error.message : String(error),
  }));
}
"""


class AntiReplayRegistryGapPresentationCrossRuntimeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        support_type = (
            aggregation_support.RegistryOrganizationIdentitySignedArtifactBundleCrossRuntimeV1Tests
        )
        support_type.setUpClass()
        cls.support_type = support_type

    def _node(self, mode: str = "valid") -> dict:
        completed = subprocess.run(
            ["node", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(
                {
                    "envelope": self.support_type.envelope,
                    "items": self.support_type.items,
                    "mode": mode,
                },
                sort_keys=True,
            ),
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_real_six_signature_aggregate_builds_blocked_v2_projection(self) -> None:
        row = self._node()
        projection = row["projection"]
        self.assertEqual(projection["status"], "BLOCKED")
        self.assertEqual(
            projection["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(
            projection["identity_evidence"]["local_observation_count"],
            2,
        )
        self.assertEqual(
            projection["identity_evidence"]["unverified_count"],
            6,
        )
        self.assertFalse(
            projection["facts"]["registry_organization_identity_verified"]
        )

    def test_v2_html_is_neutral_and_exposes_both_evidence_ledgers(self) -> None:
        html = self._node()["html"]
        self.assertNotRegex(html.upper(), r"\bREADY\b")
        self.assertNotRegex(html.lower(), r"profit|return|alpha|win rate")
        self.assertIn("IDENTITY EVIDENCE LEDGER", html)
        self.assertIn("OPEN SYSTEM GAP REGISTER", html)
        self.assertIn("OBSERVED-LOCAL", html)
        self.assertIn("UNVERIFIED", html)
        self.assertIn("LOCKED", html)

    def test_fixture_remains_unmounted_and_has_no_authority(self) -> None:
        row = self._node()
        fixture = row["fixture"]
        exact = row["fixture_exact"]
        self.assertEqual(fixture["status"], "UNMOUNTED")
        self.assertFalse(fixture["facts"]["mounted"])
        self.assertFalse(fixture["facts"]["route_bound"])
        self.assertFalse(fixture["facts"]["app_imported"])
        self.assertFalse(fixture["facts"]["browser_visual_review_performed"])
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["fixture_status"], "UNMOUNTED")
        self.assertFalse(exact["registry_identity_admission_allowed"])
        self.assertFalse(exact["presentation_mount_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])

    def test_html_contains_no_payload_key_signature_or_private_material(self) -> None:
        html = self._node()["html"]
        for index, item in enumerate(self.support_type.items):
            private_der = self.support_type.private_keys[index].private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            for material in (
                item["payload"]["evidence_body"]["marker"],
                item["public_key_der_b64"],
                item["signature_b64"],
                base64.b64encode(private_der).decode("ascii"),
                private_der.hex(),
            ):
                self.assertNotIn(material, html)

    def test_registry_binding_mismatch_is_rejected(self) -> None:
        row = self._node("binding-mismatch")
        self.assertIn("do not match", row["error"])

    def test_fixture_tamper_becomes_block_unknown(self) -> None:
        exact = self._node("tamper-fixture")["fixture_exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["fixture_status"], "UNKNOWN")
        self.assertFalse(exact["mounted"])
        self.assertFalse(exact["presentation_mount_allowed"])


if __name__ == "__main__":
    unittest.main()
