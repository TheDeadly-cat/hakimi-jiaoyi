from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_cluster_dual_budget_v9_signed_snapshot_position_claim_adapter_v1
    as adapter_contract,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_freshness_replay_binding_v1
    as subject,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as position_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1
    as post_merge_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (
    ClusterExposureProposalV1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as v9_contract,
)
from tests import (
    test_strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as v9_support,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_support,
)


class V9PositionDerivedSnapshotFreshnessReplayBindingV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        v9_case = v9_support.DualBudgetPortfolioSnapshotReconciliationV9Tests(
            "test_fully_aligned_portfolio_scope_passes_without_admission"
        )
        v9_case.setUp()
        real = v9_contract.evaluate_dual_budget_portfolio_snapshot_reconciliation_v9
        with patch.object(
            v9_support,
            "evaluate_dual_budget_portfolio_snapshot_reconciliation_v9",
            wraps=real,
        ) as spy:
            v9_case.test_fully_aligned_portfolio_scope_passes_without_admission()
        parameters = deepcopy(dict(spy.call_args_list[0].kwargs))
        cls.v9_document = real(**deepcopy(parameters))
        cls.v9_context = {
            "preregistration": parameters["preregistration"],
            "proposal_reconciliation_v8_document": parameters[
                "proposal_reconciliation_v8_document"
            ],
            "proposal_reconciliation_v8_context": parameters[
                "proposal_reconciliation_v8_context"
            ],
            "expected_portfolio_snapshot_preregistration_v9_hash": parameters[
                "expected_portfolio_snapshot_preregistration_v9_hash"
            ],
        }
        cls.v9_hash = cls.v9_document[
            "portfolio_snapshot_reconciliation_v9_hash"
        ]

        freshness_support.IncumbentSnapshotFreshnessReplayGateV1Tests.setUpClass()
        cls.fixture = freshness_support.IncumbentSnapshotFreshnessReplayGateV1Tests
        cls.projection = cls.fixture.projection
        cls.projection_hash = cls.fixture.projection_hash
        cls.context = cls.fixture.context
        cls.source_clusters = cls.fixture.source_clusters
        cls.symbol_to_cluster = cls.fixture.symbol_to_cluster
        cls.adapter = adapter_contract.build_v9_signed_snapshot_position_claim_adapter_v1(
            cls.v9_document,
            cls.v9_context,
            expected_v9_reconciliation_hash=cls.v9_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
        )
        cls.proposal = ClusterExposureProposalV1(
            proposal_id="binding-p-1",
            symbol="A",
            requested_gross_bps=400,
        )
        cls.proposals = (cls.proposal,)
        cls.exposure_policy = freshness_support.exposure_policy()
        cls.batch = cls.fixture.fixture._evaluate([cls.proposal.symbol])
        cls.position_result = position_gate.evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2(
            cls.batch,
            cls.projection,
            cls.proposals,
            cls.exposure_policy,
            cls.adapter.position_claim,
            expected_position_snapshot_claim_hash=(
                cls.adapter.position_claim.claim_hash
            ),
            expected_batch_preflight_hash=cls.batch["preflight_hash"],
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )
        cls.snapshot = position_gate.build_position_derived_incumbent_cluster_exposure_snapshot_v2(
            cls.adapter.position_claim,
            expected_position_snapshot_claim_hash=(
                cls.adapter.position_claim.claim_hash
            ),
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )
        cls.temporal = cls.fixture.temporal(
            cls.snapshot,
            sequence=cls.adapter.snapshot_sequence,
            head=cls.adapter.snapshot_sequence,
            high_water=cls.adapter.snapshot_sequence - 1,
        )

    @classmethod
    def _kwargs(cls, temporal=None):
        attestation, reference, cursor, policy = (
            cls.temporal if temporal is None else temporal
        )
        return {
            "adapter_result": cls.adapter,
            "v9_document": cls.v9_document,
            "v9_verification_context": cls.v9_context,
            "position_derived_result": cls.position_result,
            "batch_preflight_document": cls.batch,
            "projection_preregistration": cls.projection,
            "proposals": cls.proposals,
            "exposure_policy": cls.exposure_policy,
            "attestation": attestation,
            "reference": reference,
            "cursor": cursor,
            "freshness_policy": policy,
            "expected_adapter_hash": cls.adapter.adapter_hash,
            "expected_v9_reconciliation_hash": cls.v9_hash,
            "expected_position_derived_result_hash": (
                cls.position_result.result_hash
            ),
            "expected_batch_preflight_hash": cls.batch["preflight_hash"],
            "expected_projection_preregistration_hash": cls.projection_hash,
            "projection_verification_context": cls.context,
            "expected_attestation_hash": attestation.attestation_hash,
            "expected_reference_hash": reference.reference_hash,
            "expected_cursor_hash": cursor.cursor_hash,
            "expected_stream_id": freshness_support.STREAM_ID,
        }

    def test_different_snapshot_hash_gap_is_rejected(self):
        cluster_id = self.symbol_to_cluster["A"]
        alternate = post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(
            snapshot_id="fresh-but-different-snapshot",
            projection_preregistration_hash=self.projection_hash,
            source_clusters=self.source_clusters,
            cluster_gross_bps=((cluster_id, 500),),
        )
        temporal = self.fixture.temporal(
            alternate,
            sequence=self.adapter.snapshot_sequence,
            head=self.adapter.snapshot_sequence,
            high_water=self.adapter.snapshot_sequence - 1,
        )
        direct = self.fixture.evaluate(self.proposals, alternate, temporal)
        self.assertEqual(
            direct.status,
            freshness_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE,
        )
        self.assertNotEqual(
            alternate.snapshot_hash,
            self.position_result.derived_incumbent_snapshot_hash,
        )
        self.assertIsNone(
            subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
                **self._kwargs(temporal)
            )
        )

    def test_exact_hash_and_sequence_bound_chain_is_candidate_only(self):
        result = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **self._kwargs()
        )
        self.assertEqual(
            result.status,
            subject.STATUS_FRESH_UNREPLAYED_BOUND_CANDIDATE,
        )
        self.assertEqual(
            result.derived_incumbent_snapshot_hash,
            self.snapshot.snapshot_hash,
        )
        self.assertEqual(result.snapshot_sequence, self.adapter.snapshot_sequence)
        self.assertTrue(result.snapshot_hash_bound_across_contracts)
        self.assertTrue(result.snapshot_sequence_bound_across_contracts)

    def test_same_hash_with_different_sequence_is_rejected(self):
        temporal = self.fixture.temporal(
            self.snapshot,
            sequence=self.adapter.snapshot_sequence + 1,
            head=self.adapter.snapshot_sequence + 1,
            high_water=self.adapter.snapshot_sequence,
        )
        direct = self.fixture.evaluate(self.proposals, self.snapshot, temporal)
        self.assertEqual(
            direct.status,
            freshness_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE,
        )
        self.assertIsNone(
            subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
                **self._kwargs(temporal)
            )
        )

    def test_stale_bound_snapshot_remains_blocked(self):
        temporal = self.fixture.temporal(
            self.snapshot,
            sequence=self.adapter.snapshot_sequence,
            head=self.adapter.snapshot_sequence + 2,
            high_water=self.adapter.snapshot_sequence - 1,
            max_lag=1,
        )
        result = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **self._kwargs(temporal)
        )
        self.assertEqual(result.status, subject.STATUS_BLOCKED_BOUND_SNAPSHOT)
        self.assertEqual(
            result.blocker_codes,
            ("SNAPSHOT_SEQUENCE_LAG_EXCEEDS_POLICY",),
        )
        self.assertFalse(result.local_sequence_freshness_candidate_observed)

    def test_replayed_bound_snapshot_remains_blocked(self):
        attestation = freshness_gate.build_incumbent_snapshot_sequence_attestation_v1(
            stream_id=freshness_support.STREAM_ID,
            projection_preregistration_hash=self.projection_hash,
            incumbent_snapshot_hash=self.snapshot.snapshot_hash,
            sequence=self.adapter.snapshot_sequence,
        )
        temporal = self.fixture.temporal(
            self.snapshot,
            sequence=self.adapter.snapshot_sequence,
            head=self.adapter.snapshot_sequence,
            high_water=self.adapter.snapshot_sequence,
            high_water_attestation_hash=attestation.attestation_hash,
            consumed=(attestation.attestation_hash,),
        )
        result = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **self._kwargs(temporal)
        )
        self.assertEqual(result.status, subject.STATUS_BLOCKED_BOUND_SNAPSHOT)
        self.assertIn(
            "SNAPSHOT_ATTESTATION_ALREADY_CONSUMED",
            result.blocker_codes,
        )

    def test_adapter_and_position_result_tamper_fail_exactly(self):
        kwargs = self._kwargs()
        kwargs["adapter_result"] = replace(self.adapter, paper_authorized=True)
        self.assertIsNone(
            subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
                **kwargs
            )
        )
        kwargs = self._kwargs()
        kwargs["position_derived_result"] = replace(
            self.position_result,
            derived_incumbent_snapshot_hash="0" * 64,
        )
        self.assertIsNone(
            subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
                **kwargs
            )
        )

    def test_wrong_temporal_hash_fails_closed(self):
        kwargs = self._kwargs()
        kwargs["expected_attestation_hash"] = "0" * 64
        self.assertIsNone(
            subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
                **kwargs
            )
        )

    def test_external_truth_persistence_profitability_and_authority_stay_closed(self):
        result = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **self._kwargs()
        )
        self.assertFalse(result.provider_identity_verified)
        self.assertFalse(result.source_truth_verified)
        self.assertFalse(result.external_freshness_verified)
        self.assertFalse(result.replay_registry_persistence_verified)
        self.assertFalse(result.cursor_mutation_performed)
        self.assertFalse(result.runtime_consumer_bound)
        self.assertFalse(result.current_admission_allowed)
        self.assertFalse(result.paper_authorized)
        self.assertFalse(result.live_order_allowed)
        self.assertFalse(result.profitability_proven)
        self.assertFalse(result.permission)

    def test_result_is_redacted_deterministic_and_exactly_verified(self):
        kwargs = self._kwargs()
        one = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **kwargs
        )
        two = subject.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **kwargs
        )
        self.assertEqual(one, two)
        for cluster in self.source_clusters:
            self.assertNotIn(cluster["cluster_id"], repr(one))
        self.assertTrue(
            subject.verify_v9_position_derived_snapshot_freshness_replay_binding_v1(
                one,
                **kwargs,
            )
        )
        self.assertFalse(
            subject.verify_v9_position_derived_snapshot_freshness_replay_binding_v1(
                replace(one, live_order_allowed=True),
                **kwargs,
            )
        )

    def test_production_binding_has_no_io_runtime_clock_or_cursor_mutation_api(self):
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
            "save_cursor",
            "advance_cursor",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
