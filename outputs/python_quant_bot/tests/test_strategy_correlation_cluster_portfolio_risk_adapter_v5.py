from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v5 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskAdapterV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.weighted_context = self._weighted_context()
        self.weighted_document = seal_strict_canonical_document(
            {
                "schema_version": subject.adapter_v4.weighted_v2.BUDGET_SCHEMA_VERSION,
                "static_fingerprint": subject.adapter_v4.weighted_v2.STATIC_FINGERPRINT,
                "status": "PASS",
                "decision": "PASS_WEIGHTED_RESEARCH_BUDGET",
                "checks": [
                    {
                        "name": "weighted_effective_cluster_gate",
                        "blocking": True,
                        "ok": True,
                    }
                ],
                "facts": {"risk_increasing": True},
                "blockers": [],
                "authority": {
                    "descriptive_only": True,
                    "writer_allowed": False,
                    "runtime_gate_activation_allowed": False,
                    "current_admission_allowed": False,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            },
            "budget_v2_hash",
        )
        self.adapter_v4 = self._adapter_v4("PASS")
        self.stability_gate = self._stability_gate("PASS")
        self.adapter_context = {
            "adapter_v3_document": {},
            "weighted_budget_v2_document": self.weighted_document,
            "adapter_v3_verification_context": {},
            "weighted_budget_v2_verification_context": self.weighted_context,
        }
        self.stability_context = {
            "preregistration": {},
            "window_budget_documents": {
                "short": {},
                "medium": self.weighted_document,
                "long": {},
            },
            "window_verification_contexts": {
                "short": {},
                "medium": self.weighted_context,
                "long": {},
            },
            "expected_preregistration_hash": "9" * 64,
            "anchor_window_id": "medium",
        }

    def _weighted_context(self) -> dict:
        return {
            "preregistration": {"symbols": ["A", "B", "C"]},
            "correlation_matrix": {
                "symbols": ["A", "B", "C"],
                "return_series": "COMPLETED_DAILY_RETURNS",
            },
            "complete_link_audit": {"absolute_pearson_threshold": 0.75},
            "equity": 10000,
            "positions": [
                {"symbol": "A", "direction": "LONG", "notional": 1800},
                {"symbol": "C", "direction": "LONG", "notional": 1800},
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": True,
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

    @staticmethod
    def _stability_authority() -> dict:
        return {
            "descriptive_only": True,
            "writer_allowed": False,
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _adapter_v4(self, status: str) -> dict:
        blocked = status == "BLOCK"
        return seal_strict_canonical_document(
            {
                "schema_version": subject.adapter_v4.SCHEMA_VERSION,
                "static_fingerprint": subject.adapter_v4.STATIC_FINGERPRINT,
                "status": status,
                "decision": (
                    "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION"
                    if blocked
                    else "WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY"
                ),
                "source": {
                    "weighted_budget_v2_hash": self.weighted_document[
                        "budget_v2_hash"
                    ],
                },
                "component_states": {},
                "checks": [],
                "policy": {},
                "portfolio": {},
                "facts": {
                    "temporal_and_session_freshness_preserved": True,
                    "weighted_diversification_consumed": True,
                    "joint_local_research_decision_made": True,
                    "source_documents_embedded": False,
                    "component_documents_embedded": False,
                    "correlation_matrices_embedded": False,
                    "positions_embedded": False,
                    "runtime_assets_accessed": False,
                    "runtime_consumer_bound": False,
                    "profitability_proven": False,
                },
                "blockers": ["WEIGHTED_EFFECTIVE_CLUSTER_GATE_BLOCKED"] if blocked else [],
                "warnings": [],
                "authority": self._adapter_authority(),
            },
            "adapter_hash",
        )

    def _stability_gate(self, status: str) -> dict:
        blocked = status == "BLOCK"
        trade_identity_hash = subject._trade_identity_hash(self.weighted_context)
        return seal_strict_canonical_document(
            {
                "schema_version": subject.stability_v1.GATE_SCHEMA_VERSION,
                "static_fingerprint": subject.stability_v1.STATIC_FINGERPRINT,
                "status": status,
                "decision": (
                    "BLOCK_REGISTERED_WINDOW_CLUSTER_PARTITION_DRIFT"
                    if blocked
                    else "PASS_MULTI_WINDOW_STABLE_RESEARCH_GATE"
                ),
                "source": {
                    "preregistration_hash": "9" * 64,
                    "trade_identity_hash": trade_identity_hash,
                    "source_documents_embedded": False,
                    "verification_contexts_embedded": False,
                },
                "window_summaries": [
                    {
                        "window_id": "short",
                        "budget_v2_hash": "1" * 64,
                    },
                    {
                        "window_id": "medium",
                        "budget_v2_hash": self.weighted_document[
                            "budget_v2_hash"
                        ],
                    },
                    {
                        "window_id": "long",
                        "budget_v2_hash": "3" * 64,
                    },
                ],
                "summary": {},
                "facts": {
                    "preregistration_exactly_verified": True,
                    "all_registered_windows_exactly_verified": True,
                    "trade_identity_consistent_across_windows": True,
                    "matrix_hashes_unique_across_windows": True,
                    "single_window_independence_assumption_used": False,
                    "correlation_matrices_embedded": False,
                    "complete_link_audits_embedded": False,
                    "positions_embedded": False,
                    "runtime_assets_accessed": False,
                    "runtime_gate_integrated": False,
                    "profitability_proven": False,
                },
                "blockers": ["registered_window_cluster_partition_drift"] if blocked else [],
                "authority": self._stability_authority(),
            },
            "stability_gate_hash",
        )

    @staticmethod
    def _adapter_receipt(document: dict) -> dict:
        return {
            "status": "PASS",
            "adapter_v4_exactly_verified": True,
            "adapter_v4_status": document["status"],
            "adapter_v4_hash": document["adapter_hash"],
            "blockers": [],
            "writer_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "formal_registry_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    @staticmethod
    def _stability_receipt(document: dict) -> dict:
        return {
            "status": "PASS",
            "stability_gate_exactly_verified": True,
            "stability_gate_decision": document["decision"],
            "blockers": [],
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _evaluate(
        self,
        *,
        adapter_document=None,
        stability_document=None,
        adapter_context=None,
        stability_context=None,
        adapter_receipt=None,
        stability_receipt=None,
        adapter_error=None,
        stability_error=None,
    ):
        adapter_document = self.adapter_v4 if adapter_document is None else adapter_document
        stability_document = self.stability_gate if stability_document is None else stability_document

        def verify_adapter(*_args, **_kwargs):
            if adapter_error is not None:
                raise adapter_error
            return copy.deepcopy(
                self._adapter_receipt(adapter_document)
                if adapter_receipt is None
                else adapter_receipt
            )

        def verify_stability(*_args, **_kwargs):
            if stability_error is not None:
                raise stability_error
            return copy.deepcopy(
                self._stability_receipt(stability_document)
                if stability_receipt is None
                else stability_receipt
            )

        with (
            patch.object(subject, "_VERIFY_ADAPTER_V4", side_effect=verify_adapter),
            patch.object(
                subject, "_VERIFY_STABILITY_GATE", side_effect=verify_stability
            ),
        ):
            return subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5(
                copy.deepcopy(adapter_document),
                copy.deepcopy(stability_document),
                adapter_v4_verification_context=copy.deepcopy(
                    self.adapter_context if adapter_context is None else adapter_context
                ),
                stability_gate_verification_context=copy.deepcopy(
                    self.stability_context
                    if stability_context is None
                    else stability_context
                ),
            )

    def test_both_components_pass_joint_research_gate(self) -> None:
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE",
        )
        self.assertTrue(all(document["checks"].values()))
        self.assertTrue(document["facts"]["anchor_window_budget_and_context_bound"])
        self.assertTrue(document["facts"]["trade_identity_cross_bound"])

    def test_adapter_pass_is_overridden_by_stability_block(self) -> None:
        stability = self._stability_gate("BLOCK")
        document = self._evaluate(stability_document=stability)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCK_MULTI_WINDOW_STABILITY_COMPONENT")
        self.assertEqual(document["blockers"], ["multi_window_stability_component_block"])

    def test_adapter_component_block_is_preserved(self) -> None:
        adapter = self._adapter_v4("BLOCK")
        document = self._evaluate(adapter_document=adapter)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCK_ADAPTER_V4_COMPONENT")

    def test_anchor_window_missing_duplicate_and_alias_fail_closed(self) -> None:
        missing = copy.deepcopy(self.stability_context)
        missing["anchor_window_id"] = "missing"
        alias = copy.deepcopy(self.stability_context)
        alias["anchor_window_id"] = "short"
        for context in (missing, alias):
            self.assertEqual(
                self._evaluate(stability_context=context)["status"], "UNKNOWN"
            )

    def test_anchor_document_context_and_budget_hash_cross_splice_fail_closed(self) -> None:
        document_splice = copy.deepcopy(self.stability_context)
        document_splice["window_budget_documents"]["medium"] = {
            "budget_v2_hash": "0" * 64
        }
        context_splice = copy.deepcopy(self.stability_context)
        context_splice["window_verification_contexts"]["medium"][
            "proposed_notional"
        ] = 501
        gate_hash_splice = copy.deepcopy(self.stability_gate)
        gate_hash_splice["window_summaries"][1]["budget_v2_hash"] = "0" * 64
        gate_hash_splice = seal_strict_canonical_document(
            {key: value for key, value in gate_hash_splice.items() if key != "stability_gate_hash"},
            "stability_gate_hash",
        )
        self.assertEqual(
            self._evaluate(stability_context=document_splice)["status"], "UNKNOWN"
        )
        self.assertEqual(
            self._evaluate(stability_context=context_splice)["status"], "UNKNOWN"
        )
        self.assertEqual(
            self._evaluate(stability_document=gate_hash_splice)["status"], "UNKNOWN"
        )

    def test_trade_identity_and_preregistration_hash_splice_fail_closed(self) -> None:
        identity = copy.deepcopy(self.stability_gate)
        identity["source"]["trade_identity_hash"] = "0" * 64
        identity = seal_strict_canonical_document(
            {key: value for key, value in identity.items() if key != "stability_gate_hash"},
            "stability_gate_hash",
        )
        preregistration = copy.deepcopy(self.stability_context)
        preregistration["expected_preregistration_hash"] = "8" * 64
        self.assertEqual(
            self._evaluate(stability_document=identity)["status"], "UNKNOWN"
        )
        self.assertEqual(
            self._evaluate(stability_context=preregistration)["status"], "UNKNOWN"
        )

    def test_each_context_missing_extra_and_scalar_alias_fails_closed(self) -> None:
        for argument, context in (
            ("adapter_context", self.adapter_context),
            ("stability_context", self.stability_context),
        ):
            missing = copy.deepcopy(context)
            missing.pop(next(iter(missing)))
            extra = copy.deepcopy(context)
            extra["extra"] = {}
            for value in (missing, extra, []):
                with self.subTest(argument=argument, value=value):
                    self.assertEqual(
                        self._evaluate(**{argument: value})["status"], "UNKNOWN"
                    )

    def test_source_verifier_failure_and_exception_fail_closed(self) -> None:
        bad_adapter = self._adapter_receipt(self.adapter_v4)
        bad_adapter["status"] = "BLOCK"
        bad_stability = self._stability_receipt(self.stability_gate)
        bad_stability["stability_gate_exactly_verified"] = False
        cases = (
            {"adapter_receipt": bad_adapter},
            {"stability_receipt": bad_stability},
            {"adapter_error": RuntimeError("adapter")},
            {"stability_error": RuntimeError("stability")},
        )
        for overrides in cases:
            self.assertEqual(self._evaluate(**overrides)["status"], "UNKNOWN")

    def test_source_status_seal_and_authority_promotions_fail_closed(self) -> None:
        adapter = copy.deepcopy(self.adapter_v4)
        adapter["authority"]["current_admission_allowed"] = True
        adapter = seal_strict_canonical_document(
            {key: value for key, value in adapter.items() if key != "adapter_hash"},
            "adapter_hash",
        )
        stability = copy.deepcopy(self.stability_gate)
        stability["status"] = "READY"
        stability = seal_strict_canonical_document(
            {key: value for key, value in stability.items() if key != "stability_gate_hash"},
            "stability_gate_hash",
        )
        self.assertEqual(self._evaluate(adapter_document=adapter)["status"], "UNKNOWN")
        self.assertEqual(
            self._evaluate(stability_document=stability)["status"], "UNKNOWN"
        )

    def test_output_is_summary_only_and_authority_locked(self) -> None:
        document = self._evaluate()
        rendered = str(document)
        self.assertNotIn("pearson_correlation", rendered)
        self.assertNotIn("notional", rendered)
        self.assertNotIn("cluster_results", rendered)
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["positions_embedded"])
        self.assertTrue(document["authority"]["local_decision_only"])
        self.assertTrue(document["authority"]["research_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key not in {"local_decision_only", "research_only"}
            )
        )

    def test_evaluation_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        inputs = (
            self.adapter_v4,
            self.stability_gate,
            self.adapter_context,
            self.stability_context,
        )
        before = copy.deepcopy(inputs)
        first = self._evaluate()
        second = self._evaluate()
        self.assertEqual(first, second)
        self.assertEqual(inputs, before)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self) -> None:
        document = self._evaluate()
        with (
            patch.object(
                subject,
                "_VERIFY_ADAPTER_V4",
                return_value=self._adapter_receipt(self.adapter_v4),
            ),
            patch.object(
                subject,
                "_VERIFY_STABILITY_GATE",
                return_value=self._stability_receipt(self.stability_gate),
            ),
        ):
            receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v5(
                document,
                self.adapter_v4,
                self.stability_gate,
                adapter_v4_verification_context=self.adapter_context,
                stability_gate_verification_context=self.stability_context,
            )
            self.assertEqual(receipt["status"], "PASS")
            tampered = copy.deepcopy(document)
            tampered["facts"]["runtime_consumer_bound"] = True
            tampered = seal_strict_canonical_document(
                {key: value for key, value in tampered.items() if key != "adapter_v5_hash"},
                "adapter_v5_hash",
            )
            blocked = subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v5(
                tampered,
                self.adapter_v4,
                self.stability_gate,
                adapter_v4_verification_context=self.adapter_context,
                stability_gate_verification_context=self.stability_context,
            )
            self.assertEqual(blocked["status"], "BLOCK")

    def test_dependency_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            root / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v4.py": subject.ADAPTER_V4_IMPLEMENTATION_SHA256,
            root / "exchange_terminal/services/strategy_correlation_cluster_multi_window_stability_gate_v1.py": subject.STABILITY_GATE_V1_IMPLEMENTATION_SHA256,
            root / "exchange_terminal/services/strict_canonical_json_hash.py": subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_api_has_no_runtime_order_or_precomputed_joint_metric_inputs(self) -> None:
        signature = inspect.signature(
            subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5
        )
        self.assertEqual(
            list(signature.parameters),
            [
                "adapter_v4_document",
                "stability_gate_document",
                "adapter_v4_verification_context",
                "stability_gate_verification_context",
            ],
        )
        source = inspect.getsource(subject)
        self.assertNotIn('"READY"', source)
        self.assertNotIn("exchange_terminal.server", source)
        self.assertNotIn("order_executor", source)


if __name__ == "__main__":
    unittest.main()
