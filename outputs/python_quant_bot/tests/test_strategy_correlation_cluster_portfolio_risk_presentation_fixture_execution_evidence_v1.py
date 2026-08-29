from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import subprocess
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1 as module
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1 import (
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1,
    verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_projection_v3 import (
    build_projection_v3_fixture,
)


STATIC_DIR = Path(__file__).resolve().parents[1] / "exchange_terminal" / "static"
FIXTURE_PATH = STATIC_DIR / "evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js"
RECEIPT_PATH = STATIC_DIR / "evidence_portfolio_risk_freshness_gate_fixture_execution_receipt_v1.js"


def _node_receipt(projection):
    script = f"""
const fixture = require({json.dumps(str(FIXTURE_PATH))});
const receipts = require({json.dumps(str(RECEIPT_PATH))});
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {{
  const projection = JSON.parse(input);
  const descriptor = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection);
  const receipt = receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(projection, descriptor);
  process.stdout.write(JSON.stringify(receipt));
}});
"""
    completed = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(projection, sort_keys=True),
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _build(reference_utc=None, adapter_overrides=None):
    _, _, _, _, projection = build_projection_v3_fixture(
        reference_utc=reference_utc,
        adapter_overrides=adapter_overrides,
    )
    receipt = _node_receipt(projection)
    evidence = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
        receipt,
        projection["projection_hash"],
    )
    return projection, receipt, evidence


class PortfolioRiskPresentationFixtureExecutionEvidenceV1Tests(unittest.TestCase):
    def test_fresh_node_receipt_binds_as_local_only_evidence(self):
        projection, receipt, evidence = _build()
        self.assertEqual(evidence["schema_version"], SCHEMA_VERSION)
        self.assertEqual(evidence["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["source"]["projection_hash"], projection["projection_hash"])

    def test_stale_risk_increase_receipt_still_binds_exact_execution(self):
        _, receipt, evidence = _build(reference_utc="2026-12-29T00:00:00Z")
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertFalse(evidence["facts"]["browser_visual_review_performed"])

    def test_stale_reduction_receipt_still_binds_exact_execution(self):
        _, _, evidence = _build(
            reference_utc="2026-12-29T00:00:00Z",
            adapter_overrides={"risk_increasing": False},
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertFalse(evidence["authority"]["presentation_mount_allowed"])

    def test_receipt_hash_tamper_blocks(self):
        projection, receipt, _ = _build()
        receipt["receipt_hash"] = "0" * 64
        evidence = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
            receipt, projection["projection_hash"]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_projection_hash_cross_splice_blocks(self):
        _, receipt, _ = _build()
        evidence = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
            receipt, "0" * 64
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_extra_field_and_scalar_alias_block(self):
        projection, receipt, _ = _build()
        extra = copy.deepcopy(receipt)
        extra["unexpected"] = True
        alias = copy.deepcopy(receipt)
        alias["verification"]["descriptor_exactly_rebuilt"] = 1
        for value in (extra, alias):
            evidence = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
                value, projection["projection_hash"]
            )
            self.assertEqual(evidence["status"], "BLOCK")

    def test_node_and_python_canonical_receipt_hash_agree(self):
        _, receipt, evidence = _build()
        self.assertEqual(evidence["source"]["node_receipt_hash"], receipt["receipt_hash"])
        self.assertEqual(len(evidence["evidence_hash"]), 64)

    def test_local_receipt_does_not_claim_authenticated_process_or_signature(self):
        _, _, evidence = _build()
        for key in (
            "node_process_identity_authenticated",
            "receipt_signature_verified",
            "external_execution_authority_verified",
            "independent_review_performed",
            "dom_contract_reviewed",
            "browser_visual_review_performed",
            "runtime_consumer_bound",
            "ui_mounted",
        ):
            self.assertIs(evidence["facts"][key], False)

    def test_output_is_summary_only(self):
        _, _, evidence = _build()
        serialized = json.dumps(evidence, sort_keys=True)
        for forbidden in (
            '"node_execution_receipt"',
            '"projection_document"',
            '"fixture_descriptor"',
            '"markup"',
            '"positions"',
            '"return_series"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self):
        projection, receipt, evidence = _build()
        result = verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
            evidence, receipt, projection["projection_hash"]
        )
        self.assertEqual(result["status"], "PASS")
        tampered = copy.deepcopy(evidence)
        tampered["authority"]["presentation_mount_allowed"] = True
        result = verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
            tampered, receipt, projection["projection_hash"]
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_build_is_deterministic_and_does_not_mutate_receipt(self):
        projection, receipt, first = _build()
        before = copy.deepcopy(receipt)
        second = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
            receipt, projection["projection_hash"]
        )
        self.assertEqual(first, second)
        self.assertEqual(receipt, before)

    def test_api_and_import_boundary_are_narrow(self):
        parameters = list(
            inspect.signature(
                build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1
            ).parameters
        )
        self.assertEqual(parameters, ["node_execution_receipt", "expected_projection_hash"])
        source = inspect.getsource(module)
        for forbidden in (
            "subprocess",
            "risk_service",
            "exchange_terminal.server",
            "selenium",
            "playwright",
            "requests",
            "sqlite3",
        ):
            self.assertNotIn(forbidden, source)

    def test_authority_and_wording_remain_neutral(self):
        _, _, evidence = _build()
        for key, value in evidence["authority"].items():
            if key == "descriptive_only":
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)
        self.assertNotRegex(json.dumps(evidence).upper(), r"\bREADY\b")
        self.assertFalse(evidence["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
