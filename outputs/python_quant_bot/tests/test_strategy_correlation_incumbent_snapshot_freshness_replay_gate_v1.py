from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1 as post_merge_gate  # noqa: E402
from exchange_terminal.application import strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate  # noqa: E402
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import POLICY_VERSION as EXPOSURE_POLICY_VERSION, ClusterExposurePolicyV1, ClusterExposureProposalV1  # noqa: E402
from tests import test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1 as batch_fixture_module  # noqa: E402


STREAM_ID = "synthetic-incumbent-stream"


def exposure_policy():
    return ClusterExposurePolicyV1(policy_version=EXPOSURE_POLICY_VERSION, policy_id="freshness-source-exposure-policy-20260824", max_proposals=8, max_portfolio_gross_bps=8000, max_cluster_gross_bps=3000, max_single_proposal_gross_bps=3000)


def freshness_policy():
    return replay_gate.IncumbentSnapshotFreshnessReplayPolicyV1(policy_version=replay_gate.POLICY_VERSION, policy_id="freshness-replay-policy-20260824", max_sequence_lag=1, max_forward_sequence_jump=2)


def proposal(proposal_id, symbol, gross):
    return ClusterExposureProposalV1(proposal_id=proposal_id, symbol=symbol, requested_gross_bps=gross)


class IncumbentSnapshotFreshnessReplayGateV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests
        fixture.setUpClass()
        cls.fixture = fixture
        cls.projection = fixture.projection
        cls.projection_hash = fixture.projection_hash
        cls.context = fixture.context
        cls.symbols = tuple(cls.projection["derivation"]["projected_symbols"])
        budget = cls.context["structural_gate_verification_context"]["budget_cluster_preregistration"]
        cls.source_clusters = budget["expected_clusters"]
        cls.symbol_to_cluster = {member: cluster["cluster_id"] for cluster in cls.source_clusters for member in cluster["members"]}

    @classmethod
    def snapshot(cls):
        built = post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(snapshot_id="freshness-synthetic-snapshot", projection_preregistration_hash=cls.projection_hash, source_clusters=cls.source_clusters, cluster_gross_bps=((cls.symbol_to_cluster[cls.symbols[0]], 500),))
        if built is None:
            raise AssertionError("snapshot did not build")
        return built

    @classmethod
    def temporal(cls, snapshot, *, sequence=10, head=10, high_water=9, high_water_attestation_hash=None, consumed=None, max_lag=1, max_jump=2):
        attestation = replay_gate.build_incumbent_snapshot_sequence_attestation_v1(stream_id=STREAM_ID, projection_preregistration_hash=cls.projection_hash, incumbent_snapshot_hash=snapshot.snapshot_hash, sequence=sequence)
        reference = replay_gate.build_incumbent_snapshot_sequence_head_reference_v1(reference_id="synthetic-head-reference", stream_id=STREAM_ID, projection_preregistration_hash=cls.projection_hash, head_sequence=head)
        previous_hash = (high_water_attestation_hash or "e" * 64) if high_water > 0 else None
        consumed_values = tuple(sorted((previous_hash,) if consumed is None and previous_hash else (() if consumed is None else consumed)))
        cursor = replay_gate.build_incumbent_snapshot_replay_cursor_v1(stream_id=STREAM_ID, projection_preregistration_hash=cls.projection_hash, high_water_sequence=high_water, high_water_attestation_hash=previous_hash, consumed_attestation_hashes=consumed_values)
        policy = replace(freshness_policy(), max_sequence_lag=max_lag, max_forward_sequence_jump=max_jump)
        if None in (attestation, reference, cursor):
            raise AssertionError("temporal fixture did not build")
        return attestation, reference, cursor, policy

    @classmethod
    def evaluate(cls, proposals, snapshot, temporal, *, source_policy=None, expected_hashes=None):
        attestation, reference, cursor, policy = temporal
        batch = cls.fixture._evaluate([item.symbol for item in proposals])
        hashes = expected_hashes or (attestation.attestation_hash, reference.reference_hash, cursor.cursor_hash)
        return replay_gate.evaluate_incumbent_snapshot_freshness_replay_gate_v1(batch, cls.projection, proposals, exposure_policy() if source_policy is None else source_policy, snapshot, attestation, reference, cursor, policy, expected_incumbent_snapshot_hash=snapshot.snapshot_hash, expected_attestation_hash=hashes[0], expected_reference_hash=hashes[1], expected_cursor_hash=hashes[2], expected_stream_id=STREAM_ID, expected_batch_preflight_hash=batch["preflight_hash"], expected_projection_preregistration_hash=cls.projection_hash, projection_verification_context=cls.context)

    def test_fresh_unseen_monotonic_snapshot_is_candidate_only(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot()
        temporal = self.temporal(snapshot)
        result = self.evaluate((proposal("p-1", first, 300), proposal("p-2", second, 400)), snapshot, temporal)
        self.assertEqual(result.status, replay_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE)
        self.assertEqual(result.blocker_codes, ())
        self.assertEqual(result.sequence_lag, 0)
        self.assertFalse(result.cursor_mutation_performed)
        self.assertFalse(result.permission)

    def test_consumed_nonmonotonic_attestation_is_rejected(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        attestation = replay_gate.build_incumbent_snapshot_sequence_attestation_v1(stream_id=STREAM_ID, projection_preregistration_hash=self.projection_hash, incumbent_snapshot_hash=snapshot.snapshot_hash, sequence=10)
        temporal = self.temporal(snapshot, sequence=10, head=10, high_water=10, high_water_attestation_hash=attestation.attestation_hash, consumed=(attestation.attestation_hash,))
        result = self.evaluate((proposal("p-1", first, 200),), snapshot, temporal)
        self.assertEqual(result.status, replay_gate.STATUS_BLOCKED_FRESHNESS_OR_REPLAY)
        self.assertEqual(result.blocker_codes, ("SNAPSHOT_ATTESTATION_ALREADY_CONSUMED", "SNAPSHOT_SEQUENCE_NOT_ABOVE_HIGH_WATER"))

    def test_stale_sequence_is_blocked(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        temporal = self.temporal(snapshot, sequence=8, head=10, high_water=7, max_lag=1)
        result = self.evaluate((proposal("p-1", first, 200),), snapshot, temporal)
        self.assertEqual(result.blocker_codes, ("SNAPSHOT_SEQUENCE_LAG_EXCEEDS_POLICY",))
        self.assertEqual(result.sequence_lag, 2)

    def test_sequence_ahead_of_reference_is_unknown(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        result = self.evaluate((proposal("p-1", first, 200),), snapshot, self.temporal(snapshot, sequence=10, head=9, high_water=9))
        self.assertEqual(result.status, replay_gate.STATUS_UNKNOWN)
        self.assertEqual(result.blocker_codes, ("SNAPSHOT_SEQUENCE_AHEAD_OF_REFERENCE_HEAD",))
        self.assertIsNone(result.sequence_lag)

    def test_forward_jump_beyond_policy_is_blocked(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        result = self.evaluate((proposal("p-1", first, 200),), snapshot, self.temporal(snapshot, sequence=10, head=10, high_water=5, max_jump=2))
        self.assertIn("SNAPSHOT_SEQUENCE_JUMP_EXCEEDS_POLICY", result.blocker_codes)

    def test_attestation_snapshot_or_stream_drift_fails_exactly(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        temporal = self.temporal(snapshot)
        drifted_attestation = replace(temporal[0], incumbent_snapshot_hash="0" * 64)
        self.assertIsNone(self.evaluate((proposal("p-1", first, 200),), snapshot, (drifted_attestation, *temporal[1:])))
        drifted_reference = replace(temporal[1], stream_id="other-stream")
        self.assertIsNone(self.evaluate((proposal("p-1", first, 200),), snapshot, (temporal[0], drifted_reference, temporal[2], temporal[3])))

    def test_wrong_expected_temporal_hashes_fail_exactly(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        temporal = self.temporal(snapshot)
        for index in range(3):
            hashes = [temporal[0].attestation_hash, temporal[1].reference_hash, temporal[2].cursor_hash]
            hashes[index] = "0" * 64
            self.assertIsNone(self.evaluate((proposal("p-1", first, 200),), snapshot, temporal, expected_hashes=tuple(hashes)))

    def test_cursor_builder_rejects_duplicate_noncanonical_and_invalid_high_water(self):
        common = dict(stream_id=STREAM_ID, projection_preregistration_hash=self.projection_hash)
        self.assertIsNone(replay_gate.build_incumbent_snapshot_replay_cursor_v1(**common, high_water_sequence=1, high_water_attestation_hash="a" * 64, consumed_attestation_hashes=("a" * 64, "a" * 64)))
        self.assertIsNone(replay_gate.build_incumbent_snapshot_replay_cursor_v1(**common, high_water_sequence=1, high_water_attestation_hash="b" * 64, consumed_attestation_hashes=("b" * 64, "a" * 64)))
        self.assertIsNone(replay_gate.build_incumbent_snapshot_replay_cursor_v1(**common, high_water_sequence=0, high_water_attestation_hash="a" * 64, consumed_attestation_hashes=("a" * 64,)))

    def test_fresh_snapshot_does_not_override_upstream_post_merge_block(self):
        first = self.symbols[0]
        snapshot = post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(snapshot_id="blocking-snapshot", projection_preregistration_hash=self.projection_hash, source_clusters=self.source_clusters, cluster_gross_bps=((self.symbol_to_cluster[first], 2900),))
        result = self.evaluate((proposal("p-1", first, 200),), snapshot, self.temporal(snapshot))
        self.assertEqual(result.status, replay_gate.STATUS_BLOCKED_UPSTREAM_POST_MERGE)
        self.assertEqual(result.blocker_codes, ("UPSTREAM_POST_MERGE_GATE_NOT_WITHIN_LIMIT",))
        self.assertFalse(result.permission)

    def test_result_is_deterministic_redacted_and_never_mutates_cursor(self):
        first = self.symbols[0]
        snapshot = self.snapshot()
        temporal = self.temporal(snapshot)
        proposals = (proposal("p-1", first, 200),)
        one = self.evaluate(proposals, snapshot, temporal)
        two = self.evaluate(proposals, snapshot, temporal)
        self.assertEqual(one, two)
        self.assertFalse(one.cursor_mutation_performed)
        rendered = repr(one)
        for cluster in self.source_clusters:
            self.assertNotIn(cluster["cluster_id"], rendered)

    def test_production_gate_has_no_clock_storage_or_runtime_mutation_api(self):
        source = Path(replay_gate.__file__).read_text(encoding="utf-8")
        for forbidden in ("datetime", "time.time", "open(", "sqlite3", "requests.", "subprocess", "save_cursor", "advance_cursor", "register_route(", "write_current_pointer("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
