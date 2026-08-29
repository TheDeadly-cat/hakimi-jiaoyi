from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as subject,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1
    as post_merge_gate,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (
    POLICY_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
)
from tests import (
    test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_fixture_module,
)


def _policy(*, max_cluster: int = 3000, max_portfolio: int = 8000):
    return ClusterExposurePolicyV1(
        policy_version=POLICY_VERSION,
        policy_id="position-derived-post-merge-policy-20260825",
        max_proposals=8,
        max_portfolio_gross_bps=max_portfolio,
        max_cluster_gross_bps=max_cluster,
        max_single_proposal_gross_bps=max_cluster,
    )


def _proposal(proposal_id: str, symbol: str, gross_bps: int):
    return ClusterExposureProposalV1(
        proposal_id=proposal_id,
        symbol=symbol,
        requested_gross_bps=gross_bps,
    )


class PositionDerivedPostMergeClusterExposureGateV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = (
            batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.projection = fixture.projection
        cls.projection_hash = fixture.projection_hash
        cls.context = fixture.context
        cls.symbols = tuple(cls.projection["derivation"]["projected_symbols"])
        budget = cls.context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        cls.source_clusters = budget["expected_clusters"]
        cls.symbol_to_cluster = {
            member: cluster["cluster_id"]
            for cluster in cls.source_clusters
            for member in cluster["members"]
        }

    @classmethod
    def _claim(cls, values=(), *, sequence=10):
        positions = tuple(
            sorted(
                (
                    subject.IncumbentGrossPositionV1(symbol, gross)
                    for symbol, gross in values
                ),
                key=lambda item: item.symbol,
            )
        )
        claim = subject.build_incumbent_position_gross_snapshot_claim_v1(
            snapshot_id="position-derived-synthetic-snapshot",
            projection_preregistration_hash=cls.projection_hash,
            positions=positions,
            observed_sequence=sequence,
        )
        if claim is None:
            raise AssertionError("position claim did not build")
        return claim

    @classmethod
    def _evaluate(
        cls,
        proposals,
        claim,
        *,
        exposure_policy=None,
        expected_claim_hash=None,
        expected_projection_hash=None,
        context=None,
    ):
        batch = cls.fixture._evaluate([item.symbol for item in proposals])
        return subject.evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2(
            batch,
            cls.projection,
            proposals,
            _policy() if exposure_policy is None else exposure_policy,
            claim,
            expected_position_snapshot_claim_hash=(
                claim.claim_hash
                if expected_claim_hash is None
                else expected_claim_hash
            ),
            expected_batch_preflight_hash=batch["preflight_hash"],
            expected_projection_preregistration_hash=(
                cls.projection_hash
                if expected_projection_hash is None
                else expected_projection_hash
            ),
            projection_verification_context=(
                cls.context if context is None else context
            ),
        )

    def test_caller_understatement_gap_is_closed_by_position_derivation(self):
        symbol = self.symbols[0]
        cluster_id = self.symbol_to_cluster[symbol]
        proposals = (_proposal("p-1", symbol, 600),)
        batch = self.fixture._evaluate([symbol])
        understated = post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(
            snapshot_id="caller-understated-snapshot",
            projection_preregistration_hash=self.projection_hash,
            source_clusters=self.source_clusters,
            cluster_gross_bps=((cluster_id, 500),),
        )
        old_result = post_merge_gate.evaluate_post_merge_cluster_exposure_from_verified_batch_v1(
            batch,
            self.projection,
            proposals,
            _policy(),
            understated,
            expected_incumbent_snapshot_hash=understated.snapshot_hash,
            expected_batch_preflight_hash=batch["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertEqual(
            old_result.status,
            post_merge_gate.STATUS_WITHIN_POST_MERGE_LIMIT,
        )

        derived_result = self._evaluate(
            proposals,
            self._claim(((symbol, 2500),)),
        )
        self.assertEqual(
            derived_result.status,
            post_merge_gate.STATUS_POST_MERGE_LIMIT_BREACH,
        )
        self.assertEqual(
            derived_result.blocker_codes,
            ("POST_MERGE_CLUSTER_GROSS_LIMIT_EXCEEDED",),
        )
        self.assertEqual(
            derived_result.maximum_post_merge_cluster_gross_bps,
            3100,
        )

    def test_within_limit_result_uses_exact_position_totals(self):
        first, second = self.symbols[:2]
        claim = self._claim(((first, 700), (second, 800)))
        result = self._evaluate(
            (_proposal("p-1", first, 200),),
            claim,
        )
        self.assertEqual(result.incumbent_total_gross_bps, 1500)
        self.assertEqual(result.proposed_total_gross_bps, 200)
        self.assertEqual(result.post_merge_total_gross_bps, 1700)
        self.assertEqual(result.source_position_count, 2)

    def test_empty_position_snapshot_reduces_to_proposal_exposure(self):
        symbol = self.symbols[0]
        result = self._evaluate(
            (_proposal("p-1", symbol, 500),),
            self._claim(()),
        )
        self.assertEqual(result.incumbent_total_gross_bps, 0)
        self.assertEqual(result.post_merge_total_gross_bps, 500)

    def test_unknown_position_symbol_is_rejected_not_silently_omitted(self):
        claim = self._claim((("UNKNOWN-SYMBOL", 500),))
        result = self._evaluate(
            (_proposal("p-1", self.symbols[0], 200),),
            claim,
        )
        self.assertIsNone(result)

    def test_claim_builder_rejects_duplicates_noncanonical_and_bool_values(self):
        common = {
            "snapshot_id": "invalid-position-claim",
            "projection_preregistration_hash": self.projection_hash,
            "observed_sequence": 10,
        }
        first, second = sorted(self.symbols[:2])
        duplicate = (
            subject.IncumbentGrossPositionV1(first, 100),
            subject.IncumbentGrossPositionV1(first, 200),
        )
        reversed_positions = (
            subject.IncumbentGrossPositionV1(second, 100),
            subject.IncumbentGrossPositionV1(first, 100),
        )
        bool_gross = (subject.IncumbentGrossPositionV1(first, True),)
        self.assertIsNone(
            subject.build_incumbent_position_gross_snapshot_claim_v1(
                **common,
                positions=duplicate,
            )
        )
        self.assertIsNone(
            subject.build_incumbent_position_gross_snapshot_claim_v1(
                **common,
                positions=reversed_positions,
            )
        )
        self.assertIsNone(
            subject.build_incumbent_position_gross_snapshot_claim_v1(
                **common,
                positions=bool_gross,
            )
        )
        self.assertIsNone(
            subject.build_incumbent_position_gross_snapshot_claim_v1(
                **{**common, "observed_sequence": True},
                positions=(),
            )
        )

    def test_claim_content_hash_and_projection_are_bound(self):
        symbol = self.symbols[0]
        claim = self._claim(((symbol, 500),))
        drifted = replace(
            claim,
            positions=(subject.IncumbentGrossPositionV1(symbol, 600),),
        )
        proposals = (_proposal("p-1", symbol, 200),)
        self.assertIsNone(self._evaluate(proposals, drifted))
        self.assertIsNone(
            self._evaluate(
                proposals,
                claim,
                expected_projection_hash="0" * 64,
            )
        )

    def test_context_partition_splice_is_rejected(self):
        symbol = self.symbols[0]
        context = deepcopy(self.context)
        context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]["expected_clusters"][0]["members"].append("SPLICE")
        self.assertIsNone(
            self._evaluate(
                (_proposal("p-1", symbol, 200),),
                self._claim(((symbol, 500),)),
                context=context,
            )
        )

    def test_upstream_proposal_block_remains_blocked_and_redacted(self):
        symbol = self.symbols[0]
        result = self._evaluate(
            (
                _proposal("p-1", symbol, 2000),
                _proposal("p-2", symbol, 1500),
            ),
            self._claim(()),
        )
        self.assertEqual(
            result.status,
            post_merge_gate.STATUS_UPSTREAM_PROPOSAL_LIMIT_BREACH,
        )
        self.assertIsNone(result.post_merge_total_gross_bps)

    def test_provider_truth_freshness_and_permissions_remain_closed(self):
        symbol = self.symbols[0]
        claim = self._claim(((symbol, 500),))
        result = self._evaluate((_proposal("p-1", symbol, 200),), claim)
        self.assertFalse(claim.provider_identity_verified)
        self.assertFalse(claim.source_truth_verified)
        self.assertFalse(claim.freshness_verified)
        self.assertFalse(result.provider_identity_verified)
        self.assertFalse(result.source_truth_verified)
        self.assertFalse(result.freshness_verified)
        self.assertFalse(result.cursor_mutation_performed)
        self.assertFalse(result.permission)
        self.assertEqual(result.permission_state, "UNAUTHORIZED")

    def test_result_is_deterministic_redacted_and_exactly_verified(self):
        symbol = self.symbols[0]
        proposals = (_proposal("p-1", symbol, 200),)
        claim = self._claim(((symbol, 500),))
        one = self._evaluate(proposals, claim)
        two = self._evaluate(proposals, claim)
        self.assertEqual(one, two)
        for cluster in self.source_clusters:
            self.assertNotIn(cluster["cluster_id"], repr(one))
        batch = self.fixture._evaluate([symbol])
        self.assertTrue(
            subject.verify_position_derived_post_merge_cluster_exposure_result_v2(
                one,
                batch,
                self.projection,
                proposals,
                _policy(),
                claim,
                expected_position_snapshot_claim_hash=claim.claim_hash,
                expected_batch_preflight_hash=batch["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        promoted = replace(one, permission=True)
        self.assertFalse(
            subject.verify_position_derived_post_merge_cluster_exposure_result_v2(
                promoted,
                batch,
                self.projection,
                proposals,
                _policy(),
                claim,
                expected_position_snapshot_claim_hash=claim.claim_hash,
                expected_batch_preflight_hash=batch["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_production_contract_has_no_io_clock_runtime_or_cursor_api(self):
        source = Path(subject.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "datetime",
            "time.time",
            "open(",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "subprocess",
            "portfolio_reader",
            "save_cursor",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
