from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
    as batch_identity_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3
    as subject,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as position_post_merge,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1
    as post_merge_gate,
)
from exchange_terminal.services.execution_authority import authority_violations
from tests import (
    test_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
    as batch_fixture_module,
)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(document, hash_field):
    mutated = copy.deepcopy(document)
    mutated.pop(hash_field, None)
    mutated[hash_field] = _digest(mutated)
    return mutated


def proposal(proposal_id, venue_id, symbol, requested_gross_bps):
    return {
        "proposal_id": proposal_id,
        "venue_id": venue_id,
        "symbol": symbol,
        "requested_gross_bps": requested_gross_bps,
    }


def policy(*, max_cluster=3000, max_portfolio=8000):
    return exposure_preflight.ClusterExposurePolicyV1(
        policy_version=exposure_preflight.POLICY_VERSION,
        policy_id="identity-bound-position-derived-policy-20260825",
        max_proposals=8,
        max_portfolio_gross_bps=max_portfolio,
        max_cluster_gross_bps=max_cluster,
        max_single_proposal_gross_bps=max_cluster,
    )


class StrategyCorrelationHistoryCoveredBudgetUniverseIdentityBoundPositionDerivedPostMergeClusterExposureGateCandidateV3Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        upstream = (
            batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchInstrumentIdentityGateCandidateV2Tests
        )
        upstream.setUpClass()
        cls.projection = upstream.projection
        cls.projection_hash = upstream.projection_hash
        cls.context = upstream.context
        cls.registry = upstream.registry
        cls.registry_hash = upstream.registry_hash
        cls.unique_proposals = [
            proposal("p-a", "XNYS", "A", 600),
            proposal("p-b", "XNYS", "B.N", 400),
        ]
        cls.duplicate_proposals = [
            proposal("p-a", "XNYS", "A", 200),
            proposal("p-a-alias", "xnys", "a.n", 300),
        ]
        cls.unknown_proposals = [
            proposal("p-a", "XNYS", "A", 200),
            proposal("p-unknown", "XNYS", "A-N", 300),
        ]
        cls.excluded_proposals = [
            proposal("p-c", "XNYS", "C", 200),
            proposal("p-c-alias", "XNYS", "C.N", 300),
        ]
        cls.empty_claim = cls._claim(())
        cls.unique_gate = cls._identity_gate(cls.unique_proposals)
        cls.duplicate_gate = cls._identity_gate(cls.duplicate_proposals)
        cls.unknown_gate = cls._identity_gate(cls.unknown_proposals)
        cls.excluded_gate = cls._identity_gate(cls.excluded_proposals)
        cls.unique = cls._evaluate(
            cls.unique_gate,
            cls.unique_proposals,
            cls.empty_claim,
        )
        cls.duplicate = cls._evaluate(
            cls.duplicate_gate,
            cls.duplicate_proposals,
            cls.empty_claim,
        )
        cls.unknown = cls._evaluate(
            cls.unknown_gate,
            cls.unknown_proposals,
            cls.empty_claim,
        )
        cls.excluded = cls._evaluate(
            cls.excluded_gate,
            cls.excluded_proposals,
            cls.empty_claim,
        )
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _claim(cls, values, *, sequence=20):
        positions = tuple(
            sorted(
                (
                    position_post_merge.IncumbentGrossPositionV1(symbol, gross)
                    for symbol, gross in values
                ),
                key=lambda item: item.symbol,
            )
        )
        claim = position_post_merge.build_incumbent_position_gross_snapshot_claim_v1(
            snapshot_id="identity-bound-synthetic-position-snapshot",
            projection_preregistration_hash=cls.projection_hash,
            positions=positions,
            observed_sequence=sequence,
        )
        if claim is None:
            raise AssertionError("position claim did not build")
        return claim

    @classmethod
    def _identity_gate(cls, proposals):
        stripped = [
            {
                "proposal_id": item["proposal_id"],
                "venue_id": item["venue_id"],
                "symbol": item["symbol"],
            }
            for item in proposals
        ]
        gate = batch_identity_gate.evaluate_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
            cls.registry,
            cls.projection,
            stripped,
            expected_identity_preregistration_hash=cls.registry_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )
        if gate is None:
            raise AssertionError("batch identity gate did not build")
        return gate

    @classmethod
    def _evaluate(
        cls,
        gate,
        proposals,
        claim,
        *,
        exposure_policy=None,
        expected_gate_hash=None,
        expected_claim_hash=None,
    ):
        return subject.evaluate_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
            gate,
            cls.registry,
            cls.projection,
            proposals,
            policy() if exposure_policy is None else exposure_policy,
            claim,
            expected_batch_identity_gate_hash=gate["batch_identity_gate_hash"]
            if expected_gate_hash is None
            else expected_gate_hash,
            expected_identity_preregistration_hash=cls.registry_hash,
            expected_position_snapshot_claim_hash=claim.claim_hash
            if expected_claim_hash is None
            else expected_claim_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_unique_identity_amounts_reach_exact_position_derived_post_merge(self):
        self.assertEqual(
            self.unique["status"],
            post_merge_gate.STATUS_WITHIN_POST_MERGE_LIMIT,
        )
        self.assertEqual(
            self.unique["exposure_binding"]["requested_total_gross_bps"],
            1000,
        )
        self.assertEqual(self.unique["risk_summary"]["proposed_total_gross_bps"], 1000)
        self.assertEqual(self.unique["risk_summary"]["post_merge_total_gross_bps"], 1000)
        self.assertTrue(
            self.unique["facts"]["position_derived_post_merge_exactly_verified"]
        )
        self.assertIsNotNone(
            self.unique["source"]["position_derived_post_merge_result_hash"]
        )

    def test_incumbent_position_derivation_preserves_cluster_limit_breach(self):
        proposals = [proposal("p-a", "XNYS", "A.N", 600)]
        gate = self._identity_gate(proposals)
        claim = self._claim((("A", 2500),))
        result = self._evaluate(gate, proposals, claim)
        self.assertEqual(
            result["status"], post_merge_gate.STATUS_POST_MERGE_LIMIT_BREACH
        )
        self.assertEqual(
            result["risk_summary"]["maximum_post_merge_cluster_gross_bps"],
            3100,
        )
        self.assertIn(
            "POST_MERGE_CLUSTER_GROSS_LIMIT_EXCEEDED",
            result["blockers"],
        )

    def test_duplicate_canonical_identity_stops_before_post_merge(self):
        self.assertEqual(
            self.duplicate["status"], batch_identity_gate.DUPLICATE_STATUS
        )
        self.assertEqual(
            self.duplicate["exposure_binding"]["requested_total_gross_bps"],
            500,
        )
        self.assertIsNone(
            self.duplicate["source"]["position_derived_post_merge_result_hash"]
        )
        self.assertTrue(
            self.duplicate["facts"][
                "canonical_duplicate_batch_rejected_before_post_merge"
            ]
        )
        self.assertTrue(
            all(value is None for value in self.duplicate["risk_summary"].values())
        )

    def test_unknown_and_excluded_batches_stop_before_post_merge(self):
        self.assertEqual(
            self.unknown["status"], batch_identity_gate.UNKNOWN_IDENTITY_STATUS
        )
        self.assertEqual(
            self.excluded["status"],
            batch_identity_gate.batch_preflight.EXCLUDED_STATUS,
        )
        for evidence in (self.unknown, self.excluded):
            with self.subTest(evidence=evidence):
                self.assertIsNone(
                    evidence["source"][
                        "position_derived_post_merge_result_hash"
                    ]
                )
                self.assertIn(
                    "POSITION_DERIVED_POST_MERGE_NOT_EVALUATED",
                    evidence["blockers"],
                )

    def test_requested_amount_mutation_changes_binding_and_exact_result(self):
        mutated_proposals = copy.deepcopy(self.unique_proposals)
        mutated_proposals[0]["requested_gross_bps"] = 601
        mutated = self._evaluate(
            self.unique_gate,
            mutated_proposals,
            self.empty_claim,
        )
        self.assertIsNotNone(mutated)
        self.assertNotEqual(
            mutated["exposure_binding"]["exposure_binding_hash"],
            self.unique["exposure_binding"]["exposure_binding_hash"],
        )
        self.assertEqual(
            mutated["risk_summary"]["proposed_total_gross_bps"], 1001
        )
        self.assertFalse(
            subject.verify_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
                self.unique,
                self.unique_gate,
                self.registry,
                self.projection,
                mutated_proposals,
                policy(),
                self.empty_claim,
                expected_identity_bound_post_merge_hash=self.unique[
                    "identity_bound_post_merge_hash"
                ],
                expected_batch_identity_gate_hash=self.unique_gate[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_position_snapshot_claim_hash=self.empty_claim.claim_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_identity_order_or_proposal_id_splice_is_rejected(self):
        reordered = list(reversed(self.unique_proposals))
        self.assertIsNone(
            self._evaluate(self.unique_gate, reordered, self.empty_claim)
        )
        spliced = copy.deepcopy(self.unique_proposals)
        spliced[0]["proposal_id"] = "spliced-id"
        self.assertIsNone(
            self._evaluate(self.unique_gate, spliced, self.empty_claim)
        )

    def test_invalid_amounts_and_incumbent_claim_tamper_fail_closed(self):
        for invalid in (0, True, exposure_preflight.MAX_GROSS_BPS + 1):
            proposals = copy.deepcopy(self.unique_proposals)
            proposals[0]["requested_gross_bps"] = invalid
            with self.subTest(invalid=invalid):
                self.assertIsNone(
                    self._evaluate(self.unique_gate, proposals, self.empty_claim)
                )
        drifted_claim = replace(
            self.empty_claim,
            observed_sequence=self.empty_claim.observed_sequence + 1,
        )
        self.assertIsNone(
            self._evaluate(
                self.unique_gate,
                self.unique_proposals,
                drifted_claim,
                expected_claim_hash=self.empty_claim.claim_hash,
            )
        )

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        self.assertTrue(
            subject.verify_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
                self.unique,
                self.unique_gate,
                self.registry,
                self.projection,
                self.unique_proposals,
                policy(),
                self.empty_claim,
                expected_identity_bound_post_merge_hash=self.unique[
                    "identity_bound_post_merge_hash"
                ],
                expected_batch_identity_gate_hash=self.unique_gate[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_position_snapshot_claim_hash=self.empty_claim.claim_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        promoted = copy.deepcopy(self.unique)
        promoted["authority"]["post_merge_admission_allowed"] = True
        promoted["decision_path"]["permission"] = "AUTHORIZED"
        promoted = _reseal(promoted, "identity_bound_post_merge_hash")
        self.assertFalse(
            subject.verify_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
                promoted,
                self.unique_gate,
                self.registry,
                self.projection,
                self.unique_proposals,
                policy(),
                self.empty_claim,
                expected_identity_bound_post_merge_hash=promoted[
                    "identity_bound_post_merge_hash"
                ],
                expected_batch_identity_gate_hash=self.unique_gate[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_position_snapshot_claim_hash=self.empty_claim.claim_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_provider_truth_freshness_and_permissions_remain_closed(self):
        self.assertFalse(self.unique["facts"]["provider_identity_verified"])
        self.assertFalse(self.unique["facts"]["source_truth_verified"])
        self.assertFalse(self.unique["facts"]["freshness_verified"])
        self.assertFalse(self.unique["facts"]["post_merge_admission_allowed"])
        self.assertIn(
            "INCUMBENT_PROVIDER_IDENTITY_NOT_VERIFIED",
            self.unique["blockers"],
        )
        self.assertIn(
            "INCUMBENT_FRESHNESS_NOT_VERIFIED",
            self.unique["blockers"],
        )

    def test_public_output_is_redacted_neutral_and_authority_clean(self):
        rendered = json.dumps(self.unique, ensure_ascii=False, sort_keys=True)
        for raw_identifier in (
            "p-a",
            "B.N",
            "XNYS",
            "US:ISSUER-B:COMMON",
        ):
            self.assertNotIn(raw_identifier, rendered)
        self.assertNotIn("READY", rendered)
        self.assertEqual(
            self.unique["decision_path"]["permission"], "NOT_AUTHORIZED"
        )
        self.assertEqual(authority_violations(self.unique), [])
        self.assertFalse(self.unique["registered"])


if __name__ == "__main__":
    unittest.main()
