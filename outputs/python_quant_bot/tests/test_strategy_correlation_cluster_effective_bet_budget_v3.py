from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from inspect import signature
from itertools import combinations
import json
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_effective_bet_budget_v2 import (
    evaluate_strategy_correlation_cluster_effective_bet_budget_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as subject,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class StrategyCorrelationClusterEffectiveBetBudgetV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-a", "members": ["A"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
        )
        correlations = {
            pair: 0.10 for pair in combinations(self.preregistration["symbols"], 2)
        }
        self.matrix = build_correlation_matrix_contract(
            self.preregistration["symbols"],
            correlations,
        )
        self.audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.matrix,
        )
        self.cells = [
            {
                "gate_status": "PASS",
                "lane": "RAW_EXCESS",
                "strategy_id": "synthetic-strategy",
                "symbol": symbol,
                "variant_id": "synthetic-variant",
            }
            for symbol in self.preregistration["symbols"]
        ]
        self.complete_link_gate = self._complete_link_gate(self.cells)
        self.base_inputs = {
            "equity": 10_000,
            "positions": [
                {"symbol": "A", "notional": 2_500, "direction": "LONG"}
            ],
            "proposed_symbol": "B",
            "proposed_notional": 2_500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": True,
        }

    def _complete_link_gate(self, cells: list[dict]) -> dict:
        return evaluate_correlation_cluster_gate_v2(
            self.preregistration,
            self.matrix,
            cells,
            strategy_id="synthetic-strategy",
            variant_id="synthetic-variant",
            lane="RAW_EXCESS",
        )

    def _strata_sources(self, *, shared: bool = True, cells=None):
        strata = (
            [
                {
                    "stratum_id": "shared-family",
                    "cluster_ids": ["cluster-a", "cluster-b"],
                },
                {
                    "stratum_id": "independent-family",
                    "cluster_ids": ["cluster-c"],
                },
            ]
            if shared
            else [
                {"stratum_id": "family-a", "cluster_ids": ["cluster-a"]},
                {"stratum_id": "family-b", "cluster_ids": ["cluster-b"]},
                {"stratum_id": "family-c", "cluster_ids": ["cluster-c"]},
            ]
        )
        registration = build_strategy_correlation_strata_preregistration(
            self.preregistration,
            [{"dimension_id": "asset-family", "strata": strata}],
        )
        complete_link_gate = self._complete_link_gate(cells or self.cells)
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            complete_link_gate,
            source_preregistration=self.preregistration,
        )
        return registration, gate, complete_link_gate

    def _evaluate(self, *, shared: bool = True, cells=None, inputs=None):
        registration, gate, complete_link_gate = self._strata_sources(
            shared=shared,
            cells=cells,
        )
        kwargs = self.base_inputs | (inputs or {})
        document = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            self.preregistration,
            self.matrix,
            self.audit,
            strata_registration=registration,
            strata_gate=gate,
            complete_link_gate=complete_link_gate,
            **kwargs,
        )
        return document, registration, gate, complete_link_gate, kwargs

    def _verify(self, document: dict, registration, gate, complete_link_gate, kwargs):
        return subject.verify_strategy_correlation_cluster_effective_bet_budget_v3(
            document,
            self.preregistration,
            self.matrix,
            self.audit,
            strata_registration=registration,
            strata_gate=gate,
            complete_link_gate=complete_link_gate,
            **kwargs,
        )

    def test_reproduced_v2_same_stratum_gap_is_blocked(self) -> None:
        v2_document = evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            self.preregistration,
            self.matrix,
            self.audit,
            **self.base_inputs,
        )
        self.assertEqual(v2_document["status"], "PASS")
        self.assertEqual(
            v2_document["portfolio"]["weighted_effective_cluster_count"],
            2.0,
        )

        document, _, gate, _, _ = self._evaluate(shared=True)
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        row = document["portfolio"]["dimension_results"][0]
        self.assertEqual(row["active_stratum_count"], 1)
        self.assertEqual(row["weighted_effective_strata_count"], 1.0)
        self.assertEqual(row["maximum_stratum_gross_pct"], 50.0)
        self.assertIn(
            "stratum_gross_limit_exceeded:asset-family",
            document["blockers"],
        )
        self.assertIn(
            "weighted_effective_strata_gate:asset-family",
            document["blockers"],
        )

    def test_balanced_active_exposure_in_separate_strata_passes(self) -> None:
        document, registration, gate, complete_link_gate, kwargs = self._evaluate(
            shared=False
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_STRATIFIED_RESEARCH_BUDGET")
        self.assertEqual(
            document["portfolio"]["conservative_weighted_effective_strata_count"],
            2.0,
        )
        self.assertEqual(
            self._verify(
                document,
                registration,
                gate,
                complete_link_gate,
                kwargs,
            )["status"],
            "PASS",
        )

    def test_preregistered_minimum_35_plus_15_passes(self) -> None:
        document, *_ = self._evaluate(
            shared=False,
            inputs={
                "positions": [
                    {"symbol": "A", "notional": 3_500, "direction": "LONG"}
                ],
                "proposed_notional": 1_500,
            },
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["portfolio"]["conservative_weighted_effective_strata_count"],
            1.724138,
        )

    def test_same_stratum_below_trigger_is_one_descriptive_bet(self) -> None:
        document, *_ = self._evaluate(
            shared=True,
            inputs={
                "positions": [
                    {"symbol": "A", "notional": 2_000, "direction": "LONG"}
                ],
                "proposed_notional": 2_000,
            },
        )
        self.assertEqual(document["status"], "PASS")
        row = document["portfolio"]["dimension_results"][0]
        self.assertEqual(row["weighted_effective_strata_count"], 1.0)
        self.assertEqual(row["diversification_status"], "NOT_APPLICABLE")
        self.assertEqual(row["maximum_stratum_gross_pct"], 40.0)

    def test_blocked_strata_gate_is_preserved(self) -> None:
        cells = deepcopy(self.cells)
        cells[2]["gate_status"] = "BLOCK"
        document, _, gate, _, _ = self._evaluate(shared=True, cells=cells)
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("strata_gate_decision", document["blockers"])

    def test_risk_reduction_path_remains_source_free(self) -> None:
        kwargs = {
            "equity": 10_000,
            "positions": [],
            "proposed_symbol": "A",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": False,
        }
        document = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            None,
            None,
            None,
            **kwargs,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "RISK_REDUCTION_PATH")
        self.assertFalse(document["facts"]["strata_required"])
        self.assertEqual(document["portfolio"]["dimension_results"], [])

    def test_registration_and_gate_tampering_fail_closed(self) -> None:
        document, registration, gate, complete_link_gate, kwargs = self._evaluate(
            shared=False
        )
        self.assertEqual(document["status"], "PASS")

        registration_body = deepcopy(registration)
        registration_body.pop("registration_hash")
        registration_body["dimensions"][0]["strata"][0]["cluster_ids"] = [
            "cluster-a",
            "cluster-b",
        ]
        resealed_registration = seal_strict_canonical_document(
            registration_body,
            "registration_hash",
        )
        blocked_registration = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            self.preregistration,
            self.matrix,
            self.audit,
            strata_registration=resealed_registration,
            strata_gate=gate,
            complete_link_gate=complete_link_gate,
            **kwargs,
        )
        self.assertEqual(blocked_registration["status"], "BLOCK")

        gate_body = deepcopy(gate)
        gate_body.pop("gate_hash")
        gate_body["permissions"]["paper_authorized"] = True
        resealed_gate = seal_strict_canonical_document(gate_body, "gate_hash")
        blocked_gate = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            self.preregistration,
            self.matrix,
            self.audit,
            strata_registration=registration,
            strata_gate=resealed_gate,
            complete_link_gate=complete_link_gate,
            **kwargs,
        )
        self.assertEqual(blocked_gate["status"], "BLOCK")

    def test_strict_input_aliases_preserve_v1_v2_blocks(self) -> None:
        for patch in (
            {"max_cluster_gross_pct": "45"},
            {"risk_increasing": 1},
            {"equity": True},
            {"proposed_notional": float("inf")},
        ):
            with self.subTest(patch=patch):
                document, *_ = self._evaluate(inputs=patch)
                self.assertEqual(document["status"], "BLOCK")
                self.assertNotEqual(document["source"]["v2_status"], "PASS")

    def test_exact_verifier_rejects_resealed_promotions(self) -> None:
        document, registration, gate, complete_link_gate, kwargs = self._evaluate(
            shared=False
        )
        self.assertEqual(
            self._verify(
                document,
                registration,
                gate,
                complete_link_gate,
                kwargs,
            )["status"],
            "PASS",
        )
        variants = []
        for mutate in (
            lambda body: body["authority"].__setitem__("writer_allowed", True),
            lambda body: body.__setitem__("decision", "PASS_RESEARCH_BUDGET"),
            lambda body: body["portfolio"].__setitem__(
                "conservative_weighted_effective_strata_count",
                9.0,
            ),
            lambda body: body["source"].__setitem__(
                "same_source_preregistration_verified",
                False,
            ),
        ):
            body = deepcopy(document)
            body.pop("budget_v3_hash")
            mutate(body)
            variants.append(seal_strict_canonical_document(body, "budget_v3_hash"))
        for variant in variants:
            with self.subTest(hash=variant["budget_v3_hash"]):
                receipt = self._verify(
                    variant,
                    registration,
                    gate,
                    complete_link_gate,
                    kwargs,
                )
                self.assertEqual(receipt["status"], "BLOCK")
                self.assertEqual(receipt["budget_decision"], "UNKNOWN")
                self.assertFalse(receipt["writer_allowed"])

    def test_output_is_summary_only_and_inputs_are_not_mutated(self) -> None:
        registration, gate, complete_link_gate = self._strata_sources(shared=False)
        originals = deepcopy(
            (
                self.preregistration,
                self.matrix,
                self.audit,
                registration,
                gate,
                complete_link_gate,
                self.base_inputs,
            )
        )
        document = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            self.preregistration,
            self.matrix,
            self.audit,
            strata_registration=registration,
            strata_gate=gate,
            complete_link_gate=complete_link_gate,
            **self.base_inputs,
        )
        self.assertEqual(
            (
                self.preregistration,
                self.matrix,
                self.audit,
                registration,
                gate,
                complete_link_gate,
                self.base_inputs,
            ),
            originals,
        )
        encoded = json.dumps(document, sort_keys=True)
        for forbidden in (
            "cluster_exposures",
            "gross_notional",
            "pearson_correlation",
            "return_series",
            "positions",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["strata_membership_rows_embedded"])

    def test_implementation_pins_match_current_predecessors(self) -> None:
        paths = {
            subject.V1_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget.py",
            subject.V2_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget_v2.py",
            subject.STRATA_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_preregistered_strata.py",
            subject.COMPLETE_LINK_IMPLEMENTATION_SHA256: ROOT
            / "exchange_terminal/services/strategy_correlation_cluster_complete_link.py",
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)

    def test_schema_authority_and_api_are_research_only(self) -> None:
        document, *_ = self._evaluate(shared=False)
        self.assertEqual(document["schema_version"], subject.BUDGET_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)
        parameters = signature(
            subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v3
        ).parameters
        self.assertNotIn("precomputed_v1_result", parameters)
        self.assertNotIn("precomputed_v2_result", parameters)
        self.assertNotIn("runtime_gate", parameters)
        self.assertFalse(document["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
