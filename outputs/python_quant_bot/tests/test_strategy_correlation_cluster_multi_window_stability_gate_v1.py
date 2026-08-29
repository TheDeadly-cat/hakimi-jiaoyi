from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_stability_gate_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class MultiWindowStabilityGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = [
            {"window_id": "short", "lookback_observations": 20},
            {"window_id": "medium", "lookback_observations": 60},
            {"window_id": "long", "lookback_observations": 120},
        ]
        self.preregistration = subject.build_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
            self.specs
        )
        self.expected_hash = self.preregistration["preregistration_hash"]
        hashes = {"short": "1" * 64, "medium": "2" * 64, "long": "3" * 64}
        self.contexts = {
            spec["window_id"]: self._context(
                spec["lookback_observations"],
                hashes[spec["window_id"]],
                (("A", "B"), ("C",)),
            )
            for spec in self.specs
        }
        self.documents = {
            window_id: self._budget("PASS", "PASS_WEIGHTED_RESEARCH_BUDGET", True)
            for window_id in self.contexts
        }

    def _context(
        self,
        lookback: int,
        matrix_hash: str,
        partition: tuple[tuple[str, ...], ...],
        *,
        risk_increasing: bool = True,
    ) -> dict:
        symbols = sorted(member for cluster in partition for member in cluster)
        return {
            "preregistration": {
                "symbols": symbols,
                "absolute_pearson_threshold": 0.75,
            },
            "correlation_matrix": {
                "schema_version": "strategy-selection-correlation-matrix-v1",
                "status": "PASS",
                "lookback_observations": lookback,
                "matrix_hash": matrix_hash,
                "symbols": symbols,
                "return_series": "COMPLETED_DAILY_RETURNS",
                "permissions": {
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            },
            "complete_link_audit": {
                "schema_version": "strategy-correlation-cluster-complete-link-audit-v1",
                "status": "PASS",
                "matrix_hash": matrix_hash,
                "absolute_pearson_threshold": 0.75,
                "cluster_results": [
                    {
                        "cluster_id": f"cluster-{index}",
                        "members": list(cluster),
                    }
                    for index, cluster in enumerate(partition)
                ],
                "permissions": {
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            },
            "equity": 10000,
            "positions": [
                {"symbol": "A", "direction": "LONG", "notional": 1800},
                {"symbol": "C", "direction": "LONG", "notional": 1800},
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": risk_increasing,
        }

    def _budget(self, status: str, decision: str, risk_increasing: bool) -> dict:
        blocked = status == "BLOCK"
        return seal_strict_canonical_document(
            {
                "schema_version": subject.weighted_v2.BUDGET_SCHEMA_VERSION,
                "static_fingerprint": subject.weighted_v2.STATIC_FINGERPRINT,
                "status": status,
                "decision": decision,
                "source": {},
                "policy": {},
                "portfolio": {},
                "checks": [
                    {
                        "name": "weighted_effective_cluster_gate",
                        "blocking": True,
                        "ok": not blocked,
                        "message": "synthetic",
                    }
                ],
                "facts": {
                    "risk_increasing": risk_increasing,
                    "weighted_metrics_exactly_derived": True,
                    "source_documents_embedded": False,
                    "runtime_assets_accessed": False,
                    "runtime_gate_integrated": False,
                    "profitability_proven": False,
                },
                "blockers": ["weighted_effective_cluster_gate"] if blocked else [],
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

    @staticmethod
    def _receipt(document: dict) -> dict:
        return {
            "status": "PASS",
            "budget_decision": document["decision"],
            "blockers": [],
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _evaluate(
        self,
        *,
        preregistration=None,
        documents=None,
        contexts=None,
        expected_hash=None,
        verifier_side_effect=None,
    ):
        def verifier(document, *_args, **_kwargs):
            if verifier_side_effect is not None:
                raise verifier_side_effect
            return self._receipt(document)

        with patch.object(subject, "_VERIFY_WEIGHTED_V2", side_effect=verifier):
            return subject.evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1(
                copy.deepcopy(
                    self.preregistration
                    if preregistration is None
                    else preregistration
                ),
                copy.deepcopy(self.documents if documents is None else documents),
                window_verification_contexts=copy.deepcopy(
                    self.contexts if contexts is None else contexts
                ),
                expected_preregistration_hash=(
                    self.expected_hash if expected_hash is None else expected_hash
                ),
            )

    def test_preregistration_is_deterministic_and_hash_pinned(self) -> None:
        second = subject.build_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
            copy.deepcopy(self.specs)
        )
        self.assertEqual(second, self.preregistration)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
                self.preregistration,
                self.specs,
                expected_preregistration_hash=self.expected_hash,
            )
        )
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
                self.preregistration,
                self.specs,
                expected_preregistration_hash="0" * 64,
            )
        )

    def test_preregistration_rejects_count_id_and_lookback_drift(self) -> None:
        cases = [
            self.specs[:2],
            [self.specs[0], self.specs[0], self.specs[2]],
            [
                self.specs[0],
                {"window_id": "medium", "lookback_observations": 19},
                self.specs[2],
            ],
            [
                self.specs[1],
                self.specs[0],
                self.specs[2],
            ],
        ]
        for specs in cases:
            with self.subTest(specs=specs):
                with self.assertRaises(subject.MultiWindowStabilityContractError):
                    subject.build_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
                        specs
                    )

    def test_three_stable_pass_windows_allow_research_gate_only(self) -> None:
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_MULTI_WINDOW_STABLE_RESEARCH_GATE")
        self.assertEqual(document["summary"]["verified_window_count"], 3)
        self.assertEqual(document["summary"]["unique_matrix_hash_count"], 3)
        self.assertEqual(document["summary"]["unique_partition_count"], 1)
        self.assertTrue(document["facts"]["cluster_partition_stable"])
        self.assertFalse(document["facts"]["single_window_independence_assumption_used"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_any_registered_window_budget_block_blocks_risk_increase(self) -> None:
        documents = copy.deepcopy(self.documents)
        documents["long"] = self._budget("BLOCK", "BLOCK", True)
        document = self._evaluate(documents=documents)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCK_REGISTERED_WINDOW_WEIGHTED_BUDGET")
        self.assertEqual(document["blockers"], ["registered_window_weighted_budget_block"])

    def test_partition_drift_blocks_even_when_every_window_budget_passes(self) -> None:
        contexts = copy.deepcopy(self.contexts)
        contexts["long"] = self._context(
            120,
            "3" * 64,
            (("A", "B", "C"),),
        )
        document = self._evaluate(contexts=contexts)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_REGISTERED_WINDOW_CLUSTER_PARTITION_DRIFT",
        )
        self.assertFalse(document["facts"]["cluster_partition_stable"])
        self.assertEqual(document["summary"]["unique_partition_count"], 2)

    def test_single_window_pass_cannot_hide_long_window_merged_cluster(self) -> None:
        contexts = copy.deepcopy(self.contexts)
        contexts["short"] = self._context(20, "1" * 64, (("A", "B"), ("C",)))
        contexts["long"] = self._context(120, "3" * 64, (("A", "B", "C"),))
        document = self._evaluate(contexts=contexts)
        self.assertEqual(document["window_summaries"][0]["budget_status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("partition", document["blockers"][0])

    def test_risk_reduction_is_exempt_after_all_sources_verify(self) -> None:
        contexts = {
            key: self._context(
                context["correlation_matrix"]["lookback_observations"],
                context["correlation_matrix"]["matrix_hash"],
                (("A", "B", "C"),) if key == "long" else (("A", "B"), ("C",)),
                risk_increasing=False,
            )
            for key, context in self.contexts.items()
        }
        documents = {
            key: self._budget("PASS", "RISK_REDUCTION_EXEMPT", False)
            for key in contexts
        }
        document = self._evaluate(documents=documents, contexts=contexts)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_RISK_REDUCTION_MULTI_WINDOW_EXEMPT")
        self.assertTrue(document["facts"]["risk_reduction_exemption_applied"])

    def test_missing_extra_window_and_duplicate_matrix_hash_fail_closed(self) -> None:
        missing = copy.deepcopy(self.documents)
        missing.pop("long")
        extra = copy.deepcopy(self.documents)
        extra["extra"] = self._budget("PASS", "PASS_WEIGHTED_RESEARCH_BUDGET", True)
        duplicate = copy.deepcopy(self.contexts)
        duplicate["long"]["correlation_matrix"]["matrix_hash"] = "2" * 64
        duplicate["long"]["complete_link_audit"]["matrix_hash"] = "2" * 64
        for documents, contexts in (
            (missing, self.contexts),
            (extra, self.contexts),
            (self.documents, duplicate),
        ):
            with self.subTest(documents=documents, contexts=contexts):
                self.assertEqual(
                    self._evaluate(documents=documents, contexts=contexts)["status"],
                    "UNKNOWN",
                )

    def test_lookback_and_trade_identity_splice_fail_closed(self) -> None:
        lookback = copy.deepcopy(self.contexts)
        lookback["long"]["correlation_matrix"]["lookback_observations"] = 60
        identity = copy.deepcopy(self.contexts)
        identity["long"]["proposed_notional"] = 501
        for contexts in (lookback, identity):
            self.assertEqual(self._evaluate(contexts=contexts)["status"], "UNKNOWN")

    def test_verifier_failure_exception_and_hash_pin_fail_closed(self) -> None:
        def false_verifier(*_args, **_kwargs):
            return {
                "status": "BLOCK",
                "budget_decision": "UNKNOWN",
                "blockers": ["failed"],
            }

        with patch.object(subject, "_VERIFY_WEIGHTED_V2", side_effect=false_verifier):
            failed = subject.evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1(
                self.preregistration,
                self.documents,
                window_verification_contexts=self.contexts,
                expected_preregistration_hash=self.expected_hash,
            )
        self.assertEqual(failed["status"], "UNKNOWN")
        self.assertEqual(
            self._evaluate(verifier_side_effect=RuntimeError("source"))["status"],
            "UNKNOWN",
        )
        self.assertEqual(
            self._evaluate(expected_hash="0" * 64)["status"],
            "UNKNOWN",
        )

    def test_budget_seal_status_and_authority_promotion_fail_closed(self) -> None:
        mutations = []
        seal = copy.deepcopy(self.documents)
        seal["short"]["budget_v2_hash"] = "0" * 64
        mutations.append(seal)
        status = copy.deepcopy(self.documents)
        status["short"]["status"] = "READY"
        status["short"] = seal_strict_canonical_document(
            {key: value for key, value in status["short"].items() if key != "budget_v2_hash"},
            "budget_v2_hash",
        )
        mutations.append(status)
        authority = copy.deepcopy(self.documents)
        authority["short"]["authority"]["current_admission_allowed"] = True
        authority["short"] = seal_strict_canonical_document(
            {key: value for key, value in authority["short"].items() if key != "budget_v2_hash"},
            "budget_v2_hash",
        )
        mutations.append(authority)
        for documents in mutations:
            self.assertEqual(self._evaluate(documents=documents)["status"], "UNKNOWN")

    def test_output_is_summary_only(self) -> None:
        document = self._evaluate()
        rendered = str(document)
        self.assertNotIn("pearson_correlation", rendered)
        self.assertNotIn("left_symbol", rendered)
        self.assertNotIn("right_symbol", rendered)
        self.assertNotIn("notional", rendered)
        self.assertNotIn("cluster_results", rendered)
        self.assertFalse(document["facts"]["correlation_matrices_embedded"])
        self.assertFalse(document["facts"]["complete_link_audits_embedded"])
        self.assertFalse(document["facts"]["positions_embedded"])
        self.assertEqual(len(document["window_summaries"]), 3)
        expected_summary_fields = {
            "window_id",
            "lookback_observations",
            "matrix_hash",
            "budget_v2_hash",
            "budget_status",
            "budget_decision",
            "cluster_count",
            "cluster_partition_hash",
            "weighted_budget_exactly_verified",
        }
        for summary in document["window_summaries"]:
            self.assertEqual(set(summary), expected_summary_fields)

    def test_evaluation_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        inputs = (
            self.preregistration,
            self.documents,
            self.contexts,
            self.expected_hash,
        )
        before = copy.deepcopy(inputs)
        first = self._evaluate()
        second = self._evaluate()
        self.assertEqual(first, second)
        self.assertEqual(inputs, before)

    def test_public_verifier_accepts_exact_and_rejects_resealed_tamper(self) -> None:
        document = self._evaluate()

        def verifier(weighted_document, *_args, **_kwargs):
            return self._receipt(weighted_document)

        with patch.object(subject, "_VERIFY_WEIGHTED_V2", side_effect=verifier):
            receipt = subject.verify_strategy_correlation_cluster_multi_window_stability_gate_v1(
                document,
                self.preregistration,
                self.documents,
                window_verification_contexts=self.contexts,
                expected_preregistration_hash=self.expected_hash,
            )
            self.assertEqual(receipt["status"], "PASS")
            tampered = copy.deepcopy(document)
            tampered["summary"]["cluster_partition_stable"] = False
            tampered = seal_strict_canonical_document(
                {key: value for key, value in tampered.items() if key != "stability_gate_hash"},
                "stability_gate_hash",
            )
            blocked = subject.verify_strategy_correlation_cluster_multi_window_stability_gate_v1(
                tampered,
                self.preregistration,
                self.documents,
                window_verification_contexts=self.contexts,
                expected_preregistration_hash=self.expected_hash,
            )
            self.assertEqual(blocked["status"], "BLOCK")

    def test_dependency_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        weighted = root / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget_v2.py"
        strict = root / "exchange_terminal/services/strict_canonical_json_hash.py"
        self.assertEqual(
            hashlib.sha256(weighted.read_bytes()).hexdigest(),
            subject.WEIGHTED_V2_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(strict.read_bytes()).hexdigest(),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        )

    def test_api_has_no_runtime_order_or_precomputed_stability_inputs(self) -> None:
        signature = inspect.signature(
            subject.evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1
        )
        self.assertEqual(
            list(signature.parameters),
            [
                "preregistration",
                "window_budget_documents",
                "window_verification_contexts",
                "expected_preregistration_hash",
            ],
        )
        source = inspect.getsource(subject)
        self.assertNotIn('"READY"', source)
        self.assertNotIn("exchange_terminal.server", source)
        self.assertNotIn("order_executor", source)


if __name__ == "__main__":
    unittest.main()
