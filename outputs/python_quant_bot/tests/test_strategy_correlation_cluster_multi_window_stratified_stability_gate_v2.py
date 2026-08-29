from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_stratified_stability_gate_v2
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class MultiWindowStratifiedStabilityGateV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = [
            {"window_id": "short", "lookback_observations": 20},
            {"window_id": "anchor", "lookback_observations": 60},
            {"window_id": "long", "lookback_observations": 120},
        ]
        self.preregistration = subject.build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
            self.specs
        )
        self.expected_hash = self.preregistration["preregistration_v2_hash"]
        matrix_hashes = {"short": "1" * 64, "anchor": "2" * 64, "long": "3" * 64}
        self.contexts = {
            spec["window_id"]: self._context(
                lookback=spec["lookback_observations"],
                matrix_hash=matrix_hashes[spec["window_id"]],
            )
            for spec in self.specs
        }
        self.documents = {
            window_id: self._budget(self.contexts[window_id])
            for window_id in self.contexts
        }

    @staticmethod
    def _registration(topology: str = "stable") -> dict:
        strata = (
            [
                {"cluster_ids": ["cluster-0"], "stratum_id": "family-ab"},
                {"cluster_ids": ["cluster-1"], "stratum_id": "family-c"},
            ]
            if topology == "stable"
            else [
                {
                    "cluster_ids": ["cluster-0", "cluster-1"],
                    "stratum_id": "merged-family",
                }
            ]
        )
        return seal_strict_canonical_document(
            {
                "dimensions": [
                    {"dimension_id": "asset-family", "strata": strata}
                ]
            },
            "registration_hash",
        )

    def _context(
        self,
        *,
        lookback: int,
        matrix_hash: str,
        partition=(('A', 'B'), ('C',)),
        topology: str = "stable",
    ) -> dict:
        symbols = sorted(member for cluster in partition for member in cluster)
        registration = self._registration(topology)
        return {
            "preregistration": {"symbols": symbols},
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
            "strata_registration": registration,
            "strata_gate": {"gate_hash": "4" * 64},
            "complete_link_gate": {"gate_hash": "5" * 64},
            "equity": 10_000,
            "positions": [
                {"symbol": "A", "direction": "LONG", "notional": 1_800},
                {"symbol": "C", "direction": "LONG", "notional": 1_800},
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": True,
        }

    @staticmethod
    def _authority() -> dict:
        return {
            "descriptive_only": True,
            "writer_allowed": False,
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _budget(self, context: dict, *, status: str = "PASS") -> dict:
        blocked = status == "BLOCK"
        registration = context["strata_registration"]
        row = {
            "active_stratum_count": 2,
            "dimension_id": "asset-family",
            "diversification_status": "BLOCK" if blocked else "PASS",
            "dominant_stratum_id": "family-ab",
            "dominant_stratum_share_of_active_gross_pct": 50.0,
            "gross_limit_status": "BLOCK" if blocked else "PASS",
            "maximum_stratum_gross_pct": 50.0 if blocked else 40.0,
            "over_limit_stratum_count": 1 if blocked else 0,
            "status": status,
            "weighted_effective_strata_count": 1.0 if blocked else 2.0,
        }
        return seal_strict_canonical_document(
            {
                "authority": self._authority(),
                "blockers": ["stratum_gross_limit_exceeded:asset-family"] if blocked else [],
                "checks": [
                    {
                        "blocking": True,
                        "message": "synthetic",
                        "name": "stratified_budget_gate",
                        "ok": not blocked,
                    }
                ],
                "decision": (
                    "BLOCK_STRATIFIED_RESEARCH_BUDGET"
                    if blocked
                    else "PASS_STRATIFIED_RESEARCH_BUDGET"
                ),
                "facts": {
                    "risk_increasing": True,
                    "profitability_proven": False,
                    "source_documents_embedded": False,
                },
                "policy": {},
                "portfolio": {
                    "active_cluster_count": 2,
                    "active_dimension_count": 1,
                    "conservative_weighted_effective_strata_count": row[
                        "weighted_effective_strata_count"
                    ],
                    "dimension_results": [row],
                    "symbol_ticket_count": 3,
                    "total_active_gross_pct": 41.0,
                    "v2_weighted_effective_cluster_count": 2.0,
                    "weighted_diversification_gate_applied": True,
                },
                "schema_version": subject.budget_v3.BUDGET_SCHEMA_VERSION,
                "source": {
                    "complete_link_gate_hash": context["complete_link_gate"]["gate_hash"],
                    "strata_gate_hash": context["strata_gate"]["gate_hash"],
                    "strata_registration_hash": registration["registration_hash"],
                },
                "static_fingerprint": subject.budget_v3.STATIC_FINGERPRINT,
                "status": status,
            },
            "budget_v3_hash",
        )

    @staticmethod
    def _receipt(document: dict) -> dict:
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

    def _evaluate(self, *, documents=None, contexts=None, verifier_error=None):
        def verifier(document, *_args, **_kwargs):
            if verifier_error is not None:
                raise verifier_error
            return self._receipt(document)

        with patch.object(subject, "_VERIFY_BUDGET_V3", side_effect=verifier):
            return subject.evaluate_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
                copy.deepcopy(self.preregistration),
                copy.deepcopy(self.documents if documents is None else documents),
                window_verification_contexts=copy.deepcopy(
                    self.contexts if contexts is None else contexts
                ),
                expected_preregistration_v2_hash=self.expected_hash,
                risk_increasing=True,
            )

    def test_preregistration_is_deterministic_and_hash_pinned(self):
        second = subject.build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
            copy.deepcopy(self.specs)
        )
        self.assertEqual(second, self.preregistration)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
                self.preregistration,
                self.specs,
                expected_preregistration_v2_hash=self.expected_hash,
            )
        )
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
                self.preregistration,
                self.specs,
                expected_preregistration_v2_hash="0" * 64,
            )
        )

    def test_preregistration_rejects_count_id_and_lookback_drift(self):
        cases = [
            self.specs[:2],
            [self.specs[0], self.specs[0], self.specs[2]],
            [self.specs[0], {"window_id": "anchor", "lookback_observations": 19}, self.specs[2]],
            [self.specs[1], self.specs[0], self.specs[2]],
        ]
        for specs in cases:
            with self.subTest(specs=specs):
                with self.assertRaises(subject.MultiWindowStratifiedStabilityContractError):
                    subject.build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(specs)

    def test_three_exact_stable_v3_windows_pass_research_only(self):
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_MULTI_WINDOW_STRATIFIED_STABLE_RESEARCH_GATE",
        )
        self.assertEqual(document["summary"]["verified_window_count"], 3)
        self.assertEqual(document["summary"]["unique_matrix_hash_count"], 3)
        self.assertTrue(document["facts"]["strata_topology_stable"])
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])

    def test_any_registered_window_v3_block_is_conservative(self):
        documents = copy.deepcopy(self.documents)
        documents["long"] = self._budget(self.contexts["long"], status="BLOCK")
        document = self._evaluate(documents=documents)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCK_REGISTERED_WINDOW_STRATIFIED_BUDGET"
        )
        self.assertTrue(document["summary"]["any_registered_window_blocked"])
        self.assertEqual(
            document["summary"]["worst_window_maximum_active_stratum_gross_pct"],
            50.0,
        )

    def test_complete_link_partition_drift_blocks_all_pass_windows(self):
        contexts = copy.deepcopy(self.contexts)
        contexts["long"] = self._context(
            lookback=120,
            matrix_hash="3" * 64,
            partition=(("A", "B", "C"),),
        )
        documents = copy.deepcopy(self.documents)
        documents["long"] = self._budget(contexts["long"])
        document = self._evaluate(documents=documents, contexts=contexts)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_REGISTERED_WINDOW_CLUSTER_PARTITION_DRIFT",
        )
        self.assertEqual(document["summary"]["unique_partition_count"], 2)

    def test_strata_topology_drift_blocks_all_pass_windows(self):
        contexts = copy.deepcopy(self.contexts)
        contexts["long"] = self._context(
            lookback=120,
            matrix_hash="3" * 64,
            topology="merged",
        )
        documents = copy.deepcopy(self.documents)
        documents["long"] = self._budget(contexts["long"])
        document = self._evaluate(documents=documents, contexts=contexts)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_REGISTERED_WINDOW_STRATA_TOPOLOGY_DRIFT",
        )
        self.assertEqual(document["summary"]["unique_strata_topology_count"], 2)

    def test_spliced_source_hash_and_verifier_failure_are_unknown(self):
        documents = copy.deepcopy(self.documents)
        body = copy.deepcopy(documents["long"])
        body.pop("budget_v3_hash")
        body["source"]["strata_registration_hash"] = "f" * 64
        documents["long"] = seal_strict_canonical_document(body, "budget_v3_hash")
        spliced = self._evaluate(documents=documents)
        failed = self._evaluate(verifier_error=ValueError("synthetic verifier failure"))
        for document in (spliced, failed):
            self.assertEqual(document["status"], "UNKNOWN")
            self.assertEqual(document["window_summaries"], [])
            self.assertIsNone(document["source"]["trade_identity_hash"])

    def test_missing_extra_and_duplicate_matrix_window_fail_closed(self):
        missing = copy.deepcopy(self.documents)
        missing.pop("long")
        extra = copy.deepcopy(self.documents)
        extra["extra"] = copy.deepcopy(self.documents["long"])
        duplicate_contexts = copy.deepcopy(self.contexts)
        duplicate_contexts["long"]["correlation_matrix"]["matrix_hash"] = "2" * 64
        duplicate_contexts["long"]["complete_link_audit"]["matrix_hash"] = "2" * 64
        for documents, contexts in (
            (missing, self.contexts),
            (extra, self.contexts),
            (self.documents, duplicate_contexts),
        ):
            with self.subTest(size=len(documents)):
                self.assertEqual(
                    self._evaluate(documents=documents, contexts=contexts)["status"],
                    "UNKNOWN",
                )

    def test_risk_reduction_is_source_free_and_verifier_is_not_called(self):
        with patch.object(subject, "_VERIFY_BUDGET_V3") as verifier:
            document = subject.evaluate_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
                None,
                None,
                window_verification_contexts=None,
                expected_preregistration_v2_hash=None,
                risk_increasing=False,
            )
        verifier.assert_not_called()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_RISK_REDUCTION_SOURCE_FREE")
        self.assertTrue(document["facts"]["risk_reduction_source_free"])
        self.assertEqual(document["window_summaries"], [])

    def test_exact_verifier_rejects_resealed_promotion_and_unknown(self):
        document = self._evaluate()
        with patch.object(
            subject,
            "_VERIFY_BUDGET_V3",
            side_effect=lambda value, *_args, **_kwargs: self._receipt(value),
        ):
            receipt = subject.verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
                document,
                self.preregistration,
                self.documents,
                window_verification_contexts=self.contexts,
                expected_preregistration_v2_hash=self.expected_hash,
                risk_increasing=True,
            )
            self.assertEqual(receipt["status"], "PASS")
            promoted = copy.deepcopy(document)
            promoted.pop("stability_gate_v2_hash")
            promoted["authority"]["paper_authorized"] = True
            promoted = seal_strict_canonical_document(promoted, "stability_gate_v2_hash")
            rejected = subject.verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
                promoted,
                self.preregistration,
                self.documents,
                window_verification_contexts=self.contexts,
                expected_preregistration_v2_hash=self.expected_hash,
                risk_increasing=True,
            )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["stability_gate_exactly_verified"])

        unknown = self._evaluate(documents={})
        unknown_receipt = subject.verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
            unknown,
            self.preregistration,
            {},
            window_verification_contexts=self.contexts,
            expected_preregistration_v2_hash=self.expected_hash,
            risk_increasing=True,
        )
        self.assertEqual(unknown_receipt["status"], "BLOCK")

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        documents_before = copy.deepcopy(self.documents)
        contexts_before = copy.deepcopy(self.contexts)
        document = self._evaluate()
        self.assertEqual(self.documents, documents_before)
        self.assertEqual(self.contexts, contexts_before)
        self.assertNotIn("positions", document["source"])
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["verification_contexts_embedded"])
        self.assertFalse(document["facts"]["runtime_gate_integrated"])

    def test_implementation_pin_matches_current_budget_v3(self):
        path = ROOT / "exchange_terminal" / "services" / "strategy_correlation_cluster_effective_bet_budget_v3.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.BUDGET_V3_IMPLEMENTATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
