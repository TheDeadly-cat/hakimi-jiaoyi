from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v3 as _budget_v3_fixture_module
from tests import test_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1 as _envelope_v6_fixture_module


ROOT = Path(__file__).resolve().parents[1]


class StrategyCorrelationClusterPortfolioRiskStratifiedPresentationV7Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.v6_fixture = _envelope_v6_fixture_module.AdapterV6PresentationEnvelopeV1Tests(
            methodName="test_exact_clear_local_gate_remains_neutral_and_unauthorized"
        )
        self.v6_fixture.setUp()
        self.v3_fixture = _budget_v3_fixture_module.StrategyCorrelationClusterEffectiveBetBudgetV3Tests(
            methodName="test_balanced_active_exposure_in_separate_strata_passes"
        )
        self.v3_fixture.setUp()
        (
            self.budget_pass,
            self.strata_registration,
            self.strata_gate,
            self.complete_link_gate,
            self.budget_kwargs,
        ) = self.v3_fixture._evaluate(shared=False)
        self.v6_context = {
            "adapter_v6_document": self.v6_fixture.adapter_v6,
            "adapter_v5_document": self.v6_fixture.adapter_v5,
            "downside_tail_registration": self.v6_fixture.registration,
            "downside_tail_evaluation": self.v6_fixture.evaluation,
            "expected_adapter_v6_hash": self.v6_fixture.adapter_v6[
                "adapter_v6_hash"
            ],
            "adapter_v5_verification_context": self.v6_fixture.adapter_context,
            "downside_tail_verification_context": self.v6_fixture.tail_context,
        }
        self.budget_context = self._budget_context(
            self.strata_registration,
            self.strata_gate,
            self.complete_link_gate,
            self.budget_kwargs,
        )
        self.presentation = self._build(
            self.budget_pass,
            self.budget_context,
        )

    def _budget_context(self, registration, gate, complete_link_gate, kwargs):
        return {
            "preregistration": self.v3_fixture.preregistration,
            "correlation_matrix": self.v3_fixture.matrix,
            "complete_link_audit": self.v3_fixture.audit,
            "strata_registration": registration,
            "strata_gate": gate,
            "complete_link_gate": complete_link_gate,
            **kwargs,
        }

    def _build(self, budget_document, budget_context, v6_context=None):
        with patch.object(
            subject.envelope_v6.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=self.v6_fixture._verify_adapter_v6_boundary,
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
                self.v6_fixture.envelope,
                budget_document,
                envelope_v6_verification_context=v6_context or self.v6_context,
                budget_v3_verification_context=budget_context,
            )

    def _verify(self, document, budget_document=None, budget_context=None):
        with patch.object(
            subject.envelope_v6.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=self.v6_fixture._verify_adapter_v6_boundary,
        ):
            return subject.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
                document,
                self.v6_fixture.envelope,
                budget_document or self.budget_pass,
                envelope_v6_verification_context=self.v6_context,
                budget_v3_verification_context=budget_context or self.budget_context,
            )

    def test_exact_joint_local_clear_remains_unmounted_and_unauthorized(self) -> None:
        document = self.presentation
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "EXACT_JOINT_LOCAL_CLEAR_PROJECTED_UNMOUNTED",
        )
        self.assertEqual(document["local_decision"]["joint_status"], "PASS")
        self.assertEqual(
            document["local_decision"]["stratified_budget_status"],
            "PASS",
        )
        self.assertEqual(
            document["risk_summary"][
                "conservative_weighted_effective_strata_count"
            ],
            2.0,
        )
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(document["facts"]["http_candidate_registered"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_budget_v3_block_overrides_v6_local_clear(self) -> None:
        budget_block, registration, gate, complete_link_gate, kwargs = (
            self.v3_fixture._evaluate(shared=True)
        )
        context = self._budget_context(
            registration,
            gate,
            complete_link_gate,
            kwargs,
        )
        document = self._build(budget_block, context)
        self.assertEqual(document["local_decision"]["portfolio_risk_v6_status"], "PASS")
        self.assertEqual(document["local_decision"]["stratified_budget_status"], "BLOCK")
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(
            document["local_decision"]["joint_decision"],
            "BLOCK_STRATIFIED_EFFECTIVE_BET_BUDGET",
        )
        row = document["risk_summary"]["dimension_results"][0]
        self.assertEqual(row["active_stratum_count"], 1)
        self.assertEqual(row["maximum_stratum_gross_pct"], 50.0)
        self.assertEqual(document["stages"][1]["state"], "OPEN")

    def test_unknown_or_spliced_context_hides_partial_summary(self) -> None:
        wrong_v6 = deepcopy(self.v6_context)
        wrong_v6["expected_adapter_v6_hash"] = "0" * 64
        unknown_v6 = self._build(
            self.budget_pass,
            self.budget_context,
            v6_context=wrong_v6,
        )
        self.assertEqual(unknown_v6["source"]["state"], "UNKNOWN")
        self.assertEqual(unknown_v6["local_decision"]["joint_status"], "UNKNOWN")
        self.assertEqual(unknown_v6["risk_summary"]["dimension_results"], [])

        wrong_budget = deepcopy(self.budget_context)
        wrong_budget["proposed_notional"] = 999
        unknown_budget = self._build(self.budget_pass, wrong_budget)
        self.assertEqual(unknown_budget["source"]["state"], "UNKNOWN")
        self.assertIsNone(
            unknown_budget["risk_summary"][
                "conservative_weighted_effective_strata_count"
            ]
        )

    def test_risk_reduction_is_visible_but_never_authority(self) -> None:
        kwargs = {
            "equity": 10_000,
            "positions": [],
            "proposed_symbol": "A",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": False,
        }
        document = budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            None,
            None,
            None,
            **kwargs,
        )
        context = {
            "preregistration": None,
            "correlation_matrix": None,
            "complete_link_audit": None,
            "strata_registration": None,
            "strata_gate": None,
            "complete_link_gate": None,
            **kwargs,
        }
        presentation = self._build(document, context)
        self.assertEqual(
            presentation["local_decision"]["stratified_budget_decision"],
            "RISK_REDUCTION_PATH",
        )
        self.assertEqual(presentation["local_decision"]["joint_status"], "PASS")
        self.assertEqual(presentation["risk_summary"]["dimension_results"], [])
        self.assertFalse(presentation["authority"]["paper_authorized"])
        self.assertFalse(presentation["authority"]["live_order_allowed"])

    def test_axis_order_and_neutral_gap_language_are_fixed(self) -> None:
        self.assertEqual(
            self.presentation["axis_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(
            [row["axis"] for row in self.presentation["stages"]],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        encoded = json.dumps(self.presentation, sort_keys=True).upper()
        self.assertNotIn("READY", encoded)
        self.assertNotIn("PROFIT", encoded.replace("PROFITABILITY_PROVEN", ""))

    def test_output_is_bounded_summary_only(self) -> None:
        encoded = json.dumps(self.presentation, sort_keys=True).lower()
        for forbidden_key in (
            "positions",
            "correlation_matrix",
            "pearson_correlation",
            "return_series",
            "cluster_exposures",
            "strata_registration",
            "verification_context",
        ):
            self.assertNotIn(f'"{forbidden_key}":', encoded)
        self.assertFalse(self.presentation["facts"]["source_documents_embedded"])
        self.assertFalse(self.presentation["facts"]["positions_embedded"])
        self.assertFalse(self.presentation["facts"]["matrices_embedded"])
        self.assertFalse(
            self.presentation["facts"]["verification_contexts_embedded"]
        )

    def test_inputs_are_not_mutated(self) -> None:
        originals = deepcopy(
            (
                self.v6_fixture.envelope,
                self.budget_pass,
                self.v6_context,
                self.budget_context,
            )
        )
        self._build(self.budget_pass, self.budget_context)
        self.assertEqual(
            (
                self.v6_fixture.envelope,
                self.budget_pass,
                self.v6_context,
                self.budget_context,
            ),
            originals,
        )

    def test_exact_verifier_rejects_resealed_promotions(self) -> None:
        self.assertEqual(self._verify(self.presentation)["status"], "PASS")
        mutations = (
            lambda body: body["authority"].__setitem__("writer_allowed", True),
            lambda body: body["local_decision"].__setitem__("joint_status", "BLOCK"),
            lambda body: body["risk_summary"].__setitem__(
                "conservative_weighted_effective_strata_count",
                9.0,
            ),
            lambda body: body["stages"][3].__setitem__("state", "ALLOWED"),
            lambda body: body["source"].__setitem__("state", "CURRENT"),
        )
        for mutate in mutations:
            with self.subTest(mutation=repr(mutate)):
                body = deepcopy(self.presentation)
                body.pop("presentation_v7_hash")
                mutate(body)
                resealed = seal_strict_canonical_document(
                    body,
                    "presentation_v7_hash",
                )
                receipt = self._verify(resealed)
                self.assertEqual(receipt["status"], "BLOCK")
                self.assertEqual(receipt["presentation_status"], "UNKNOWN")
                self.assertFalse(receipt["writer_allowed"])

    def test_implementation_pins_match_current_sources(self) -> None:
        paths = {
            subject.ENVELOPE_V6_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1.py",
            subject.BUDGET_V3_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget_v3.py",
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strict_canonical_json_hash.py",
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)

    def test_static_contract_remains_unmounted(self) -> None:
        self.assertEqual(self.presentation["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(
            self.presentation["static_fingerprint"],
            subject.STATIC_FINGERPRINT,
        )
        self.assertEqual(
            set(self.v6_context),
            set(subject.V6_CONTEXT_KEYS),
        )
        self.assertEqual(
            set(self.budget_context),
            set(subject.BUDGET_V3_CONTEXT_KEYS),
        )
        self.assertFalse(self.presentation["facts"]["runtime_consumer_bound"])
        self.assertFalse(self.presentation["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
