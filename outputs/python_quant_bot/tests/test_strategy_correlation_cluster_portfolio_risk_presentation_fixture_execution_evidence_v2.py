from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2
    as registration_v2,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2
    as module,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_projection_v4
    as projection_tests,
)


STATIC_DIR = Path(__file__).resolve().parents[1] / "exchange_terminal" / "static"
FIXTURE_PATH = (
    STATIC_DIR
    / "evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js"
)
RECEIPT_PATH = (
    STATIC_DIR
    / "evidence_portfolio_risk_weighted_diversification_fixture_execution_receipt_v2.js"
)


def _node_receipt(projection):
    script = f"""
const fixture = require({json.dumps(str(FIXTURE_PATH))});
const receipts = require({json.dumps(str(RECEIPT_PATH))});
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {{
  const projection = JSON.parse(input);
  const descriptor = fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(projection);
  const receipt = receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(projection, descriptor);
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


class PortfolioRiskPresentationFixtureExecutionEvidenceV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projection_case = projection_tests.PortfolioRiskProjectionV4Tests(
            methodName="test_base_pass_projects_neutral_four_stage_shape"
        )
        cls.projection_case.setUp()
        manifest = (
            registration_v2.expected_presentation_consumer_implementation_sha256_v2()
        )
        cls.registration = registration_v2.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            manifest
        )

    def _build(self, **overrides):
        case = self.projection_case.adapter_case._build_case(**overrides)
        projection = self.projection_case._build_projection(case)["projection"]
        receipt = _node_receipt(projection)
        evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            projection["projection_hash"],
            self.registration["registration_hash"],
        )
        return projection, receipt, evidence

    def test_concentrated_node_receipt_binds_as_local_only_evidence(self):
        projection, receipt, evidence = self._build(
            positions=[
                {"symbol": "A", "notional": 2_200, "direction": "LONG"},
                {"symbol": "C", "notional": 200, "direction": "LONG"},
            ],
            proposed_notional=2_200,
            legacy_limits={
                "max_gross_exposure_pct": 100.0,
                "max_correlated_cluster_pct": 45.0,
            },
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["source"]["projection_hash"], projection["projection_hash"]
        )
        self.assertEqual(
            evidence["source"]["registration_candidate_hash"],
            self.registration["registration_hash"],
        )

    def test_balanced_and_risk_reduction_receipts_bind_exactly(self):
        for overrides in ({}, {"risk_increasing": False}):
            with self.subTest(overrides=overrides):
                _, receipt, evidence = self._build(**overrides)
                self.assertEqual(receipt["status"], "PASS")
                self.assertEqual(evidence["status"], "PASS")
                self.assertFalse(evidence["authority"]["presentation_mount_allowed"])

    def test_valid_shape_projection_hash_substitution_blocks(self):
        projection, _, _ = self._build()
        tampered = copy.deepcopy(projection)
        self.assertNotEqual(tampered["projection_hash"], "f" * 64)
        tampered["projection_hash"] = "f" * 64
        receipt = _node_receipt(tampered)
        evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            tampered["projection_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(evidence["status"], "BLOCK")

    def test_receipt_hash_tamper_blocks(self):
        projection, receipt, _ = self._build()
        receipt["receipt_hash"] = "0" * 64
        evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            projection["projection_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_projection_hash_cross_splice_blocks(self):
        _, receipt, _ = self._build()
        evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            "0" * 64,
            self.registration["registration_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_registration_hash_cross_splice_blocks(self):
        projection, receipt, _ = self._build()
        evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            projection["projection_hash"],
            "0" * 64,
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_extra_field_and_bool_alias_block(self):
        projection, receipt, _ = self._build()
        extra = copy.deepcopy(receipt)
        extra["unexpected"] = True
        alias = copy.deepcopy(receipt)
        alias["verification"]["projection_seal_verified"] = 1
        for value in (extra, alias):
            evidence = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
                value,
                projection["projection_hash"],
                self.registration["registration_hash"],
            )
            self.assertEqual(evidence["status"], "BLOCK")

    def test_node_and_python_canonical_receipt_hash_agree(self):
        _, receipt, evidence = self._build()
        self.assertEqual(
            evidence["source"]["node_receipt_hash"], receipt["receipt_hash"]
        )
        self.assertEqual(len(evidence["evidence_hash"]), 64)

    def test_local_receipt_does_not_claim_authenticated_process_or_review(self):
        _, _, evidence = self._build()
        for key in (
            "node_process_identity_authenticated",
            "receipt_signature_verified",
            "external_execution_authority_verified",
            "independent_review_performed",
            "dom_contract_reviewed",
            "browser_visual_review_performed",
            "stylesheet_executed",
            "runtime_consumer_bound",
            "ui_mounted",
        ):
            self.assertIs(evidence["facts"][key], False)

    def test_output_is_summary_only(self):
        _, _, evidence = self._build()
        serialized = json.dumps(evidence, sort_keys=True)
        for forbidden in (
            '"node_execution_receipt"',
            '"projection_document"',
            '"fixture_descriptor"',
            '"markup"',
            '"positions"',
            '"return_series"',
            '"correlation_matrix"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self):
        projection, receipt, evidence = self._build()
        result = module.verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            evidence,
            receipt,
            projection["projection_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(result["status"], "PASS")
        tampered = copy.deepcopy(evidence)
        tampered["authority"]["presentation_mount_allowed"] = True
        result = module.verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            tampered,
            receipt,
            projection["projection_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_build_is_deterministic_and_does_not_mutate_receipt(self):
        projection, receipt, first = self._build()
        before = copy.deepcopy(receipt)
        second = module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            receipt,
            projection["projection_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(first, second)
        self.assertEqual(receipt, before)

    def test_api_and_import_boundary_are_narrow(self):
        parameters = list(
            inspect.signature(
                module.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2
            ).parameters
        )
        self.assertEqual(
            parameters,
            [
                "node_execution_receipt",
                "expected_projection_hash",
                "expected_registration_hash",
            ],
        )
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
        _, _, evidence = self._build()
        for key, value in evidence["authority"].items():
            self.assertIs(value, key == "descriptive_only")
        self.assertNotRegex(json.dumps(evidence).upper(), r"\bREADY\b")
        self.assertFalse(evidence["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
