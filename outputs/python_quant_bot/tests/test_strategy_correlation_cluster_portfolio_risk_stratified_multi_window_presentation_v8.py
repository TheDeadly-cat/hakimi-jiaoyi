from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7 as adapter_cases
import test_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7 as presentation_cases

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class StratifiedMultiWindowPresentationV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.presentation_fixture = presentation_cases.StrategyCorrelationClusterPortfolioRiskStratifiedPresentationV7Tests(
            methodName="test_exact_joint_local_clear_remains_unmounted_and_unauthorized"
        )
        self.presentation_fixture.setUp()
        self.adapter_fixture = adapter_cases.StratifiedMultiWindowAdapterV7Tests(
            methodName="test_exact_anchor_and_stable_gate_pass_research_only"
        )
        self.adapter_fixture.setUp()
        self.presentation = copy.deepcopy(self.presentation_fixture.presentation)
        self.budget = copy.deepcopy(self.presentation_fixture.budget_pass)
        self.budget_context = copy.deepcopy(self.presentation_fixture.budget_context)
        self.gate = copy.deepcopy(self.adapter_fixture.gate_document)
        self.presentation_context = {
            "budget_v3_document": self.budget,
            "budget_v3_verification_context": self.budget_context,
            "envelope_v6_document": {},
            "envelope_v6_verification_context": {},
        }
        self.adapter = self._adapter_document(self.gate, "PASS")
        self.adapter_context = {
            "anchor_budget_v3_document": self.budget,
            "anchor_budget_v3_verification_context": self.budget_context,
            "risk_increasing": True,
            "stability_gate_v2_document": self.gate,
            "stability_gate_v2_verification_context": {},
        }

    @staticmethod
    def _adapter_authority() -> dict:
        return {
            "local_decision_only": True,
            "research_only": True,
            "writer_allowed": False,
            "risk_service_invocation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "formal_registry_activation_allowed": False,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _adapter_document(self, gate: dict, status: str) -> dict:
        blocked = status == "BLOCK"
        return seal_strict_canonical_document(
            {
                "authority": self._adapter_authority(),
                "blockers": ["multi_window_stratified_stability_component_block"] if blocked else [],
                "checks": {"synthetic_exact_boundary": True},
                "component_states": {
                    "anchor_budget_v3_decision": self.budget["decision"],
                    "anchor_budget_v3_status": self.budget["status"],
                    "stability_gate_v2_decision": gate["decision"],
                    "stability_gate_v2_status": gate["status"],
                },
                "decision": (
                    "BLOCK_MULTI_WINDOW_STRATIFIED_STABILITY_COMPONENT"
                    if blocked
                    else "PASS_ANCHOR_AND_MULTI_WINDOW_STRATIFIED_RESEARCH_GATE"
                ),
                "facts": {
                    "anchor_budget_and_context_cross_bound": True,
                    "anchor_budget_v3_exactly_verified": True,
                    "joint_local_research_decision_made": True,
                    "source_documents_embedded": False,
                    "stability_gate_v2_exactly_verified": True,
                    "trade_identity_cross_bound": True,
                    "verification_contexts_embedded": False,
                },
                "schema_version": subject.adapter_v7.SCHEMA_VERSION,
                "source": {
                    "anchor_budget_v3_hash": self.budget["budget_v3_hash"],
                    "anchor_window_id": "anchor",
                    "source_documents_embedded": False,
                    "stability_gate_v2_hash": gate["stability_gate_v2_hash"],
                    "trade_identity_hash": gate["source"]["trade_identity_hash"],
                    "verification_contexts_embedded": False,
                },
                "static_fingerprint": subject.adapter_v7.STATIC_FINGERPRINT,
                "status": status,
            },
            "adapter_v7_hash",
        )

    @staticmethod
    def _presentation_receipt(document: dict) -> dict:
        return {
            "blockers": [],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_decision": document["decision"],
            "presentation_status": "BLOCK",
            "presentation_v7_hash": document["presentation_v7_hash"],
            "runtime_gate_activation_allowed": False,
            "schema_version": subject.presentation_v7.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS",
            "writer_allowed": False,
        }

    @staticmethod
    def _adapter_receipt(document: dict) -> dict:
        return {
            "adapter_v7_exactly_verified": True,
            "adapter_v7_hash": document["adapter_v7_hash"],
            "adapter_v7_status": document["status"],
            "blockers": [],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "risk_service_invocation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": subject.adapter_v7.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS",
            "writer_allowed": False,
        }

    def _build(
        self,
        *,
        presentation=None,
        adapter=None,
        presentation_context=None,
        adapter_context=None,
        presentation_receipt=None,
        adapter_receipt=None,
        presentation_error=None,
        adapter_error=None,
    ):
        presentation = self.presentation if presentation is None else presentation
        adapter = self.adapter if adapter is None else adapter
        presentation_context = self.presentation_context if presentation_context is None else presentation_context
        adapter_context = self.adapter_context if adapter_context is None else adapter_context

        def verify_presentation(document, *_args, **_kwargs):
            if presentation_error is not None:
                raise presentation_error
            return self._presentation_receipt(document) if presentation_receipt is None else presentation_receipt

        def verify_adapter(document, *_args, **_kwargs):
            if adapter_error is not None:
                raise adapter_error
            return self._adapter_receipt(document) if adapter_receipt is None else adapter_receipt

        with patch.object(subject, "_VERIFY_PRESENTATION_V7", side_effect=verify_presentation), patch.object(
            subject, "_VERIFY_ADAPTER_V7", side_effect=verify_adapter
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
                copy.deepcopy(presentation),
                copy.deepcopy(adapter),
                presentation_v7_verification_context=copy.deepcopy(presentation_context),
                adapter_v7_verification_context=copy.deepcopy(adapter_context),
            )

    def test_two_exact_clear_components_remain_outer_blocked_and_unmounted(self):
        document = self._build()
        self.assertEqual(document["local_decision"]["joint_status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["stages"][3]["state"], "NONE")
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])

    def test_multi_window_adapter_block_overrides_presentation_v7_local_clear(self):
        gate = copy.deepcopy(self.gate)
        gate.pop("stability_gate_v2_hash")
        gate["status"] = "BLOCK"
        gate["decision"] = "BLOCK_REGISTERED_WINDOW_STRATIFIED_BUDGET"
        gate["blockers"] = ["registered_window_stratified_budget_block"]
        gate["summary"]["any_registered_window_blocked"] = True
        gate = seal_strict_canonical_document(gate, "stability_gate_v2_hash")
        adapter = self._adapter_document(gate, "BLOCK")
        context = copy.deepcopy(self.adapter_context)
        context["stability_gate_v2_document"] = gate
        document = self._build(adapter=adapter, adapter_context=context)
        self.assertEqual(self.presentation["local_decision"]["joint_status"], "PASS")
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(
            document["local_decision"]["joint_decision"],
            "BLOCK_STRATIFIED_MULTI_WINDOW_ADAPTER_V7",
        )
        self.assertTrue(document["multi_window_summary"]["any_registered_window_blocked"])

    def test_presentation_v7_local_block_is_preserved(self):
        presentation = copy.deepcopy(self.presentation)
        presentation.pop("presentation_v7_hash")
        presentation["local_decision"]["joint_status"] = "BLOCK"
        presentation["local_decision"]["joint_decision"] = "BLOCK_PORTFOLIO_RISK_V6"
        presentation["local_decision"]["portfolio_risk_v6_status"] = "BLOCK"
        presentation["local_decision"]["portfolio_risk_v6_decision"] = "BLOCK_LOCAL_COMPONENT"
        presentation = seal_strict_canonical_document(presentation, "presentation_v7_hash")
        document = self._build(presentation=presentation)
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(
            document["local_decision"]["joint_decision"],
            "BLOCK_PRESENTATION_V7_LOCAL_COMPONENT",
        )

    def test_anchor_budget_document_and_context_splices_are_unknown(self):
        document_context = copy.deepcopy(self.adapter_context)
        spliced = copy.deepcopy(self.budget)
        spliced.pop("budget_v3_hash")
        spliced["policy"]["presentation_splice"] = True
        document_context["anchor_budget_v3_document"] = seal_strict_canonical_document(
            spliced, "budget_v3_hash"
        )
        verification_context = copy.deepcopy(self.adapter_context)
        verification_context["anchor_budget_v3_verification_context"] = copy.deepcopy(
            self.budget_context
        )
        verification_context["anchor_budget_v3_verification_context"]["proposed_notional"] += 1
        for context in (document_context, verification_context):
            self.assertEqual(
                self._build(adapter_context=context)["source"]["state"], "UNKNOWN"
            )

    def test_anchor_hash_status_and_decision_splices_are_unknown(self):
        mutations = (
            lambda body: body["source"].__setitem__("anchor_budget_v3_hash", "f" * 64),
            lambda body: body["component_states"].__setitem__("anchor_budget_v3_status", "BLOCK"),
            lambda body: body["component_states"].__setitem__("anchor_budget_v3_decision", "SPLICED"),
        )
        for mutate in mutations:
            adapter = copy.deepcopy(self.adapter)
            adapter.pop("adapter_v7_hash")
            mutate(adapter)
            adapter = seal_strict_canonical_document(adapter, "adapter_v7_hash")
            self.assertEqual(self._build(adapter=adapter)["source"]["state"], "UNKNOWN")

    def test_gate_hash_and_trade_identity_splices_are_unknown(self):
        for key in ("stability_gate_v2_hash", "trade_identity_hash"):
            adapter = copy.deepcopy(self.adapter)
            adapter.pop("adapter_v7_hash")
            adapter["source"][key] = "e" * 64
            adapter = seal_strict_canonical_document(adapter, "adapter_v7_hash")
            self.assertEqual(self._build(adapter=adapter)["source"]["state"], "UNKNOWN")

    def test_extra_context_bad_receipt_and_verifier_exception_are_unknown(self):
        extra_presentation = copy.deepcopy(self.presentation_context)
        extra_presentation["route"] = None
        extra_adapter = copy.deepcopy(self.adapter_context)
        extra_adapter["mount"] = False
        bad_presentation = self._presentation_receipt(self.presentation)
        bad_presentation["paper_authorized"] = True
        bad_adapter = self._adapter_receipt(self.adapter)
        bad_adapter["adapter_v7_exactly_verified"] = False
        cases = [
            {"presentation_context": extra_presentation},
            {"adapter_context": extra_adapter},
            {"presentation_receipt": bad_presentation},
            {"adapter_receipt": bad_adapter},
            {"presentation_error": RuntimeError("presentation")},
            {"adapter_error": RuntimeError("adapter")},
        ]
        for override in cases:
            with self.subTest(case=next(iter(override))):
                self.assertEqual(self._build(**override)["source"]["state"], "UNKNOWN")

    def test_unknown_source_hides_all_partial_summaries(self):
        document = self._build(adapter_context={})
        self.assertEqual(document["local_decision"]["joint_status"], "UNKNOWN")
        self.assertEqual(document["risk_summary"]["dimension_results"], [])
        self.assertIsNone(document["multi_window_summary"]["registered_window_count"])
        self.assertIsNone(document["source"]["adapter_v7_hash"])
        self.assertIsNone(document["source"]["presentation_v7_hash"])

    def test_multi_window_projection_is_bounded_aggregate_only(self):
        document = self._build()
        self.assertTrue(document["facts"]["multi_window_summary_projected"])
        self.assertEqual(document["multi_window_summary"]["verified_window_count"], 3)
        self.assertNotIn("window_summaries", document)
        self.assertNotIn("positions", document)
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["verification_contexts_embedded"])

    def test_axis_order_and_neutral_permission_are_fixed(self):
        document = self._build()
        self.assertEqual(document["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual([stage["axis"] for stage in document["stages"]], list(subject.AXIS_ORDER))
        self.assertEqual(document["stages"][2]["state"], "CANDIDATE")
        self.assertEqual(document["stages"][3]["detail"], "NO_EXECUTION_OR_ACTIVATION_PERMISSION")
        self.assertFalse(document["facts"]["http_candidate_registered"])

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        document = self._build()
        with patch.object(
            subject,
            "_VERIFY_PRESENTATION_V7",
            side_effect=lambda value, *_args, **_kwargs: self._presentation_receipt(value),
        ), patch.object(
            subject,
            "_VERIFY_ADAPTER_V7",
            side_effect=lambda value, *_args, **_kwargs: self._adapter_receipt(value),
        ):
            receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
                document,
                self.presentation,
                self.adapter,
                presentation_v7_verification_context=self.presentation_context,
                adapter_v7_verification_context=self.adapter_context,
            )
            self.assertEqual(receipt["status"], "PASS")
            promoted = copy.deepcopy(document)
            promoted.pop("presentation_v8_hash")
            promoted["authority"]["paper_authorized"] = True
            promoted = seal_strict_canonical_document(promoted, "presentation_v8_hash")
            rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
                promoted,
                self.presentation,
                self.adapter,
                presentation_v7_verification_context=self.presentation_context,
                adapter_v7_verification_context=self.adapter_context,
            )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["presentation_v8_exactly_verified"])

    def test_implementation_pins_match_current_sources(self):
        paths = {
            ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7.py": subject.PRESENTATION_V7_IMPLEMENTATION_SHA256,
            ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7.py": subject.ADAPTER_V7_IMPLEMENTATION_SHA256,
            ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_multi_window_stratified_stability_gate_v2.py": subject.STABILITY_GATE_V2_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
