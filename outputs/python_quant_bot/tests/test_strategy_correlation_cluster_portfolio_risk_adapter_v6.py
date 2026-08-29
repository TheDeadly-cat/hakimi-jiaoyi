from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v6 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_downside_tail_gate as downside_tail,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v5 as adapter_v5_support


class PortfolioRiskAdapterV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v5_case = adapter_v5_support.PortfolioRiskAdapterV5Tests(
            "test_both_components_pass_joint_research_gate"
        )
        self.v5_case.setUp()
        self.addCleanup(self.v5_case.doCleanups)
        self.adapter_v4 = copy.deepcopy(self.v5_case.adapter_v4)
        self.stability_gate = copy.deepcopy(self.v5_case.stability_gate)
        self.adapter_v5 = self.v5_case._evaluate()
        self.adapter_context = {
            "adapter_v4_document": self.adapter_v4,
            "stability_gate_document": self.stability_gate,
            "adapter_v4_verification_context": copy.deepcopy(
                self.v5_case.adapter_context
            ),
            "stability_gate_verification_context": copy.deepcopy(
                self.v5_case.stability_context
            ),
        }
        weighted = self.v5_case.adapter_context[
            "weighted_budget_v2_verification_context"
        ]
        self.symbols = sorted(
            {
                *(item["symbol"] for item in weighted["positions"]),
                weighted["proposed_symbol"],
            }
        )

    def _registration(
        self,
        symbols: list[str] | None = None,
    ) -> dict:
        identities = symbols or self.symbols
        return downside_tail.build_strategy_correlation_downside_tail_registration(
            registration_id="adapter-v6-synthetic-tail",
            stratum_by_identity={
                symbol: f"S{index + 1}"
                for index, symbol in enumerate(identities)
            },
        )

    @staticmethod
    def _observations(
        symbols: list[str],
        *,
        coupled: bool,
    ) -> list[dict[str, object]]:
        tail_sets = {
            symbol: (
                set(range(12))
                if coupled
                else set(range(index * 12, (index + 1) * 12))
            )
            for index, symbol in enumerate(symbols)
        }
        rows = []
        for index in range(60):
            rows.append(
                {
                    "observation_id": f"OBS-{index:03d}",
                    "returns": {
                        symbol: float(
                            -1_000 + index
                            if index in tail_sets[symbol]
                            else index
                        )
                        for symbol in symbols
                    },
                }
            )
        return rows

    def _tail(
        self,
        *,
        coupled: bool = True,
        symbols: list[str] | None = None,
        observations: list[dict[str, object]] | None = None,
    ) -> tuple[dict, dict, dict]:
        identities = symbols or self.symbols
        registration = self._registration(identities)
        evaluation = (
            downside_tail.evaluate_strategy_correlation_downside_tail_gate(
                registration,
                observations
                if observations is not None
                else self._observations(identities, coupled=coupled),
                expected_registration_hash=registration["registration_hash"],
            )
        )
        context = {
            "expected_registration_hash": registration["registration_hash"],
            "expected_evaluation_hash": evaluation["evaluation_hash"],
        }
        return registration, evaluation, context

    def _evaluate(
        self,
        *,
        adapter_v5_document: dict | None = None,
        adapter_context: dict | None = None,
        registration: dict | None = None,
        evaluation: dict | None = None,
        tail_context: dict | None = None,
        coupled: bool = True,
    ) -> dict:
        if registration is None or evaluation is None or tail_context is None:
            registration, evaluation, tail_context = self._tail(
                coupled=coupled
            )
        adapter_v5_document = (
            self.adapter_v5
            if adapter_v5_document is None
            else adapter_v5_document
        )
        adapter_context = (
            self.adapter_context if adapter_context is None else adapter_context
        )
        with patch.object(
            subject.adapter_v5,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v5",
            side_effect=self._verify_adapter_v5_boundary,
        ):
            return subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v6(
                adapter_v5_document,
                registration,
                evaluation,
                adapter_v5_verification_context=adapter_context,
                downside_tail_verification_context=tail_context,
            )

    def _verify_adapter_v5_boundary(
        self,
        document: object,
        adapter_v4_document: object,
        stability_gate_document: object,
        *,
        adapter_v4_verification_context: object,
        stability_gate_verification_context: object,
    ) -> dict:
        try:
            expected = self.v5_case._evaluate(
                adapter_document=adapter_v4_document,
                stability_document=stability_gate_document,
                adapter_context=adapter_v4_verification_context,
                stability_context=stability_gate_verification_context,
            )
            exact = strict_json_contract_equal(document, expected)
        except (KeyError, MemoryError, TypeError, ValueError):
            exact = False
        return {
            "schema_version": subject.adapter_v5.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if exact else "BLOCK",
            "adapter_v5_exactly_verified": exact,
            "adapter_v5_status": (
                document.get("status")
                if exact and type(document) is dict
                else "UNKNOWN"
            ),
            "adapter_v5_hash": (
                document.get("adapter_v5_hash")
                if exact and type(document) is dict
                else None
            ),
            "blockers": [] if exact else ["adapter_v5_exact_rebuild"],
            "writer_allowed": False,
            "risk_service_invocation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _verify(
        self,
        document: dict,
        registration: dict,
        evaluation: dict,
        tail_context: dict,
    ) -> dict:
        with patch.object(
            subject.adapter_v5,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v5",
            side_effect=self._verify_adapter_v5_boundary,
        ):
            return subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6(
                document,
                self.adapter_v5,
                registration,
                evaluation,
                adapter_v5_verification_context=self.adapter_context,
                downside_tail_verification_context=tail_context,
            )

    def test_adapter_v5_pass_is_overridden_by_downside_tail_block(self) -> None:
        document = self._evaluate(coupled=True)
        self.assertEqual(self.adapter_v5["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_DOWNSIDE_TAIL_COUPLING",
        )
        self.assertEqual(
            document["component_states"]["downside_tail_gate_decision"],
            "BLOCK",
        )
        self.assertTrue(
            document["facts"][
                "linear_and_multi_window_pass_can_be_overridden_by_tail_block"
            ]
        )

    def test_tail_clear_and_adapter_v5_pass_allow_research_pass(self) -> None:
        document = self._evaluate(coupled=False)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE",
        )
        self.assertEqual(document["blockers"], [])
        self.assertFalse(document["authority"]["paper_authorized"])

    def test_adapter_v5_component_block_is_preserved(self) -> None:
        blocked_v4 = self.v5_case._adapter_v4("BLOCK")
        blocked_v5 = self.v5_case._evaluate(
            adapter_document=blocked_v4
        )
        context = copy.deepcopy(self.adapter_context)
        context["adapter_v4_document"] = blocked_v4
        document = self._evaluate(
            adapter_v5_document=blocked_v5,
            adapter_context=context,
            coupled=False,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCK_ADAPTER_V5_COMPONENT")

    def test_exact_unknown_tail_source_blocks_joint_gate(self) -> None:
        registration, evaluation, context = self._tail(
            observations=[],
        )
        self.assertEqual(evaluation["source_state"], "UNKNOWN")
        document = self._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("downside_tail_source_observed", document["blockers"])

    def test_tail_registration_and_evaluation_hash_mismatch_fail_closed(
        self,
    ) -> None:
        registration, evaluation, context = self._tail(coupled=False)
        variants = []
        wrong_registration = copy.deepcopy(context)
        wrong_registration["expected_registration_hash"] = "f" * 64
        variants.append(wrong_registration)
        wrong_evaluation = copy.deepcopy(context)
        wrong_evaluation["expected_evaluation_hash"] = "f" * 64
        variants.append(wrong_evaluation)
        for value in variants:
            document = self._evaluate(
                registration=registration,
                evaluation=evaluation,
                tail_context=value,
            )
            self.assertEqual(document["status"], "BLOCK")
            self.assertIn(
                "downside_tail_evaluation_exact",
                document["blockers"],
            )

    def test_same_count_different_tail_identity_set_cannot_cross_bind(
        self,
    ) -> None:
        symbols = [*self.symbols[:-1], "X"]
        registration, evaluation, context = self._tail(
            coupled=False,
            symbols=symbols,
        )
        document = self._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "trade_symbol_set_to_tail_identity_set_bound",
            document["blockers"],
        )

    def test_adapter_trade_context_symbol_splice_fails_source_verification(
        self,
    ) -> None:
        context = copy.deepcopy(self.adapter_context)
        context["adapter_v4_verification_context"][
            "weighted_budget_v2_verification_context"
        ]["positions"][0]["symbol"] = "X"
        document = self._evaluate(
            adapter_context=context,
            coupled=False,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "adapter_v5_exact_public_verification",
            document["blockers"],
        )

    def test_resealed_tail_authority_promotion_cannot_pass(self) -> None:
        registration, evaluation, context = self._tail(coupled=False)
        altered = copy.deepcopy(evaluation)
        altered["authority"]["paper_authorized"] = True
        altered = seal_strict_canonical_document(
            altered,
            "evaluation_hash",
        )
        context["expected_evaluation_hash"] = altered["evaluation_hash"]
        document = self._evaluate(
            registration=registration,
            evaluation=altered,
            tail_context=context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "downside_tail_evaluation_exact",
            document["blockers"],
        )

    def test_resealed_adapter_v5_authority_promotion_cannot_pass(self) -> None:
        altered = copy.deepcopy(self.adapter_v5)
        altered["authority"]["paper_authorized"] = True
        altered = seal_strict_canonical_document(
            altered,
            "adapter_v5_hash",
        )
        document = self._evaluate(
            adapter_v5_document=altered,
            coupled=False,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "adapter_v5_exact_public_verification",
            document["blockers"],
        )

    def test_risk_reduction_joint_exemption_is_explicitly_not_claimed(
        self,
    ) -> None:
        document = self._evaluate(coupled=False)
        self.assertFalse(
            document["policy"][
                "risk_reduction_joint_exemption_implemented"
            ]
        )
        self.assertFalse(
            document["facts"]["risk_reduction_joint_exemption_implemented"]
        )
        self.assertIn(
            "NO_JOINT_EXEMPTION",
            document["policy"]["risk_reduction"],
        )

    def test_output_is_summary_only_and_does_not_embed_sensitive_rows(
        self,
    ) -> None:
        document = self._evaluate(coupled=False)
        encoded = json.dumps(document, sort_keys=True)
        self.assertNotIn('"aligned_observations"', encoded)
        self.assertNotIn('"pair_results"', encoded)
        self.assertNotIn('"positions"', encoded)
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["aligned_observations_embedded"])
        self.assertFalse(document["facts"]["pair_results_embedded"])

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self) -> None:
        registration, evaluation, context = self._tail(coupled=False)
        document = self._evaluate(
            registration=registration,
            evaluation=evaluation,
            tail_context=context,
        )
        verification = self._verify(
            document,
            registration,
            evaluation,
            context,
        )
        self.assertEqual(verification["status"], "PASS")
        altered = copy.deepcopy(document)
        altered["authority"]["live_order_allowed"] = True
        altered = seal_strict_canonical_document(
            altered,
            "adapter_v6_hash",
        )
        verification = self._verify(
            altered,
            registration,
            evaluation,
            context,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_dependency_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v5.py": subject.ADAPTER_V5_IMPLEMENTATION_SHA256,
            root
            / "exchange_terminal/services/strategy_correlation_downside_tail_gate.py": subject.DOWNSIDE_TAIL_IMPLEMENTATION_SHA256,
            root
            / "exchange_terminal/services/strict_canonical_json_hash.py": subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                expected,
            )

    def test_api_accepts_no_observations_or_precomputed_tail_metrics(
        self,
    ) -> None:
        signature = inspect.signature(
            subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v6
        )
        self.assertEqual(
            list(signature.parameters),
            [
                "adapter_v5_document",
                "downside_tail_registration",
                "downside_tail_evaluation",
                "adapter_v5_verification_context",
                "downside_tail_verification_context",
            ],
        )
        for forbidden in (
            "aligned_observations",
            "tail_overlap",
            "p_value",
            "runtime_order",
        ):
            self.assertNotIn(forbidden, signature.parameters)

    def test_authority_profitability_runtime_and_promotion_remain_locked(
        self,
    ) -> None:
        document = self._evaluate(coupled=False)
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertFalse(document["facts"]["risk_service_invoked"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(document), promotion)


if __name__ == "__main__":
    unittest.main()
