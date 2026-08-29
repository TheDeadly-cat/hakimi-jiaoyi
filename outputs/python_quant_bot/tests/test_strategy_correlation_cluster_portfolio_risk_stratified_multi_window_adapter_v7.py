from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import test_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2 as gate_cases

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class StratifiedMultiWindowAdapterV7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate_fixture = gate_cases.MultiWindowStratifiedStabilityGateV2Tests(
            methodName="test_three_exact_stable_v3_windows_pass_research_only"
        )
        self.gate_fixture.setUp()
        self.documents = copy.deepcopy(self.gate_fixture.documents)
        self.contexts = copy.deepcopy(self.gate_fixture.contexts)
        self.anchor_document = self.documents["anchor"]
        self.anchor_context = self.contexts["anchor"]
        self.gate_document = self.gate_fixture._evaluate(
            documents=self.documents,
            contexts=self.contexts,
        )
        self.gate_context = self._gate_context(self.documents, self.contexts)

    def _gate_context(self, documents, contexts, *, anchor="anchor") -> dict:
        return {
            "anchor_window_id": anchor,
            "expected_preregistration_v2_hash": self.gate_fixture.expected_hash,
            "preregistration": self.gate_fixture.preregistration,
            "risk_increasing": True,
            "window_budget_v3_documents": documents,
            "window_verification_contexts": contexts,
        }

    @staticmethod
    def _budget_receipt(document: dict) -> dict:
        return {
            "budget_decision": document["decision"],
            "budget_v3_hash": document["budget_v3_hash"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": subject.budget_v3.BUDGET_VERIFICATION_SCHEMA_VERSION,
            "status": "PASS",
            "writer_allowed": False,
        }

    @staticmethod
    def _gate_receipt(document: dict) -> dict:
        return {
            "blockers": [],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": subject.stability_v2.VERIFICATION_SCHEMA_VERSION,
            "stability_gate_decision": document["decision"],
            "stability_gate_exactly_verified": True,
            "stability_gate_status": document["status"],
            "stability_gate_v2_hash": document["stability_gate_v2_hash"],
            "status": "PASS",
            "writer_allowed": False,
        }

    def _evaluate(
        self,
        *,
        anchor_document=None,
        anchor_context=None,
        gate_document=None,
        gate_context=None,
        budget_receipt=None,
        gate_receipt=None,
        budget_error=None,
        gate_error=None,
    ):
        anchor_document = self.anchor_document if anchor_document is None else anchor_document
        anchor_context = self.anchor_context if anchor_context is None else anchor_context
        gate_document = self.gate_document if gate_document is None else gate_document
        gate_context = self.gate_context if gate_context is None else gate_context

        def verify_budget(document, *_args, **_kwargs):
            if budget_error is not None:
                raise budget_error
            return self._budget_receipt(document) if budget_receipt is None else budget_receipt

        def verify_gate(document, *_args, **_kwargs):
            if gate_error is not None:
                raise gate_error
            return self._gate_receipt(document) if gate_receipt is None else gate_receipt

        with patch.object(subject, "_VERIFY_BUDGET_V3", side_effect=verify_budget), patch.object(
            subject, "_VERIFY_STABILITY_GATE_V2", side_effect=verify_gate
        ):
            return subject.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
                copy.deepcopy(anchor_document),
                copy.deepcopy(gate_document),
                anchor_budget_v3_verification_context=copy.deepcopy(anchor_context),
                stability_gate_v2_verification_context=copy.deepcopy(gate_context),
                risk_increasing=True,
            )

    def test_exact_anchor_and_stable_gate_pass_research_only(self):
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_ANCHOR_AND_MULTI_WINDOW_STRATIFIED_RESEARCH_GATE",
        )
        self.assertTrue(document["facts"]["anchor_budget_and_context_cross_bound"])
        self.assertTrue(document["facts"]["trade_identity_cross_bound"])
        self.assertEqual(document["source"]["anchor_window_id"], "anchor")
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])

    def test_anchor_pass_is_overridden_by_long_window_block(self):
        documents = copy.deepcopy(self.documents)
        documents["long"] = self.gate_fixture._budget(
            self.contexts["long"], status="BLOCK"
        )
        gate = self.gate_fixture._evaluate(documents=documents, contexts=self.contexts)
        gate_context = self._gate_context(documents, self.contexts)
        document = self._evaluate(gate_document=gate, gate_context=gate_context)
        self.assertEqual(self.anchor_document["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_MULTI_WINDOW_STRATIFIED_STABILITY_COMPONENT",
        )

    def test_anchor_block_is_preserved_before_gate_block(self):
        documents = copy.deepcopy(self.documents)
        documents["anchor"] = self.gate_fixture._budget(
            self.contexts["anchor"], status="BLOCK"
        )
        gate = self.gate_fixture._evaluate(documents=documents, contexts=self.contexts)
        gate_context = self._gate_context(documents, self.contexts)
        document = self._evaluate(
            anchor_document=documents["anchor"],
            gate_document=gate,
            gate_context=gate_context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCK_ANCHOR_STRATIFIED_BUDGET_COMPONENT"
        )

    def test_anchor_document_context_and_summary_splices_fail_closed(self):
        document_splice = copy.deepcopy(self.gate_context)
        spliced_budget = copy.deepcopy(self.documents["short"])
        spliced_budget.pop("budget_v3_hash")
        spliced_budget["policy"]["synthetic_window_identity"] = "short"
        document_splice["window_budget_v3_documents"]["anchor"] = (
            seal_strict_canonical_document(spliced_budget, "budget_v3_hash")
        )
        context_splice = copy.deepcopy(self.gate_context)
        context_splice["window_verification_contexts"]["anchor"] = copy.deepcopy(
            self.contexts["short"]
        )
        summary_splice = copy.deepcopy(self.gate_document)
        summary_splice.pop("stability_gate_v2_hash")
        summary_splice["window_summaries"][1]["budget_v3_hash"] = "f" * 64
        summary_splice = seal_strict_canonical_document(
            summary_splice, "stability_gate_v2_hash"
        )
        for gate_document, gate_context in (
            (self.gate_document, document_splice),
            (self.gate_document, context_splice),
            (summary_splice, self.gate_context),
        ):
            with self.subTest(case=gate_document["stability_gate_v2_hash"][:4]):
                self.assertEqual(
                    self._evaluate(
                        gate_document=gate_document, gate_context=gate_context
                    )["status"],
                    "UNKNOWN",
                )

    def test_trade_identity_and_preregistration_hash_splices_fail_closed(self):
        identity = copy.deepcopy(self.gate_document)
        identity.pop("stability_gate_v2_hash")
        identity["source"]["trade_identity_hash"] = "e" * 64
        identity = seal_strict_canonical_document(identity, "stability_gate_v2_hash")
        preregistration = copy.deepcopy(self.gate_context)
        preregistration["expected_preregistration_v2_hash"] = "d" * 64
        self.assertEqual(self._evaluate(gate_document=identity)["status"], "UNKNOWN")
        self.assertEqual(
            self._evaluate(gate_context=preregistration)["status"], "UNKNOWN"
        )

    def test_missing_duplicate_and_lookback_alias_anchor_fail_closed(self):
        missing = copy.deepcopy(self.gate_context)
        missing["anchor_window_id"] = "missing"
        duplicate = copy.deepcopy(self.gate_document)
        duplicate.pop("stability_gate_v2_hash")
        duplicate["window_summaries"].append(
            copy.deepcopy(duplicate["window_summaries"][1])
        )
        duplicate = seal_strict_canonical_document(duplicate, "stability_gate_v2_hash")
        lookback = copy.deepcopy(self.gate_document)
        lookback.pop("stability_gate_v2_hash")
        lookback["window_summaries"][1]["lookback_observations"] = 61
        lookback = seal_strict_canonical_document(lookback, "stability_gate_v2_hash")
        for gate_document, gate_context in (
            (self.gate_document, missing),
            (duplicate, self.gate_context),
            (lookback, self.gate_context),
        ):
            self.assertEqual(
                self._evaluate(
                    gate_document=gate_document, gate_context=gate_context
                )["status"],
                "UNKNOWN",
            )

    def test_extra_context_keys_bad_receipts_and_exceptions_are_unknown(self):
        extra_anchor = copy.deepcopy(self.anchor_context)
        extra_anchor["runtime"] = False
        extra_gate = copy.deepcopy(self.gate_context)
        extra_gate["route"] = None
        bad_budget = self._budget_receipt(self.anchor_document)
        bad_budget["paper_authorized"] = True
        bad_gate = self._gate_receipt(self.gate_document)
        bad_gate["stability_gate_exactly_verified"] = False
        cases = [
            {"anchor_context": extra_anchor},
            {"gate_context": extra_gate},
            {"budget_receipt": bad_budget},
            {"gate_receipt": bad_gate},
            {"budget_error": RuntimeError("budget")},
            {"gate_error": RuntimeError("gate")},
        ]
        for override in cases:
            with self.subTest(override=next(iter(override))):
                self.assertEqual(self._evaluate(**override)["status"], "UNKNOWN")

    def test_risk_reduction_is_source_free_and_skips_both_verifiers(self):
        with patch.object(subject, "_VERIFY_BUDGET_V3") as budget_verifier, patch.object(
            subject, "_VERIFY_STABILITY_GATE_V2"
        ) as gate_verifier:
            document = subject.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
                None,
                None,
                anchor_budget_v3_verification_context=None,
                stability_gate_v2_verification_context=None,
                risk_increasing=False,
            )
        budget_verifier.assert_not_called()
        gate_verifier.assert_not_called()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_RISK_REDUCTION_SOURCE_FREE")
        self.assertTrue(document["facts"]["risk_reduction_source_free"])

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        document = self._evaluate()
        with patch.object(
            subject,
            "_VERIFY_BUDGET_V3",
            side_effect=lambda value, *_args, **_kwargs: self._budget_receipt(value),
        ), patch.object(
            subject,
            "_VERIFY_STABILITY_GATE_V2",
            side_effect=lambda value, *_args, **_kwargs: self._gate_receipt(value),
        ):
            receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
                document,
                self.anchor_document,
                self.gate_document,
                anchor_budget_v3_verification_context=self.anchor_context,
                stability_gate_v2_verification_context=self.gate_context,
                risk_increasing=True,
            )
            self.assertEqual(receipt["status"], "PASS")
            promoted = copy.deepcopy(document)
            promoted.pop("adapter_v7_hash")
            promoted["authority"]["live_order_allowed"] = True
            promoted = seal_strict_canonical_document(promoted, "adapter_v7_hash")
            rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
                promoted,
                self.anchor_document,
                self.gate_document,
                anchor_budget_v3_verification_context=self.anchor_context,
                stability_gate_v2_verification_context=self.gate_context,
                risk_increasing=True,
            )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["adapter_v7_exactly_verified"])

    def test_unknown_source_hides_partial_component_states(self):
        unknown = self._evaluate(anchor_context={})
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertEqual(unknown["component_states"]["anchor_budget_v3_status"], "UNKNOWN")
        self.assertEqual(unknown["component_states"]["stability_gate_v2_status"], "UNKNOWN")
        self.assertIsNone(unknown["source"]["anchor_budget_v3_hash"])
        self.assertIsNone(unknown["source"]["stability_gate_v2_hash"])

    def test_output_is_bounded_deterministic_and_inputs_are_not_mutated(self):
        anchor_before = copy.deepcopy(self.anchor_document)
        gate_before = copy.deepcopy(self.gate_document)
        first = self._evaluate()
        second = self._evaluate()
        self.assertEqual(first, second)
        self.assertEqual(self.anchor_document, anchor_before)
        self.assertEqual(self.gate_document, gate_before)
        self.assertFalse(first["facts"]["source_documents_embedded"])
        self.assertFalse(first["facts"]["verification_contexts_embedded"])
        self.assertFalse(first["facts"]["runtime_consumer_bound"])

    def test_implementation_pins_match_current_sources(self):
        paths = {
            ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_effective_bet_budget_v3.py": subject.BUDGET_V3_IMPLEMENTATION_SHA256,
            ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_multi_window_stratified_stability_gate_v2.py": subject.STABILITY_GATE_V2_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
