from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1 as post_merge_gate  # noqa: E402
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import POLICY_VERSION, ClusterExposurePolicyV1, ClusterExposureProposalV1  # noqa: E402
from tests import test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1 as batch_fixture_module  # noqa: E402


def policy(*, max_cluster=3000, max_portfolio=8000):
    return ClusterExposurePolicyV1(policy_version=POLICY_VERSION, policy_id="post-merge-exposure-policy-20260824", max_proposals=8, max_portfolio_gross_bps=max_portfolio, max_cluster_gross_bps=max_cluster, max_single_proposal_gross_bps=max_cluster)


def proposal(proposal_id, symbol, gross):
    return ClusterExposureProposalV1(proposal_id=proposal_id, symbol=symbol, requested_gross_bps=gross)


class PostMergeClusterExposureGateV1Tests(unittest.TestCase):
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
        cls.excluded_symbols = tuple(cls.projection["derivation"]["excluded_symbols"])

    @classmethod
    def snapshot(cls, values, snapshot_id="synthetic-incumbent-20260824"):
        built = post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(snapshot_id=snapshot_id, projection_preregistration_hash=cls.projection_hash, source_clusters=cls.source_clusters, cluster_gross_bps=tuple(sorted(values)))
        if built is None:
            raise AssertionError("snapshot did not build")
        return built

    @classmethod
    def evaluate(cls, proposals, incumbent, *, exposure_policy=None, batch_document=None, expected_snapshot_hash=None):
        source_document = cls.fixture._evaluate([item.symbol for item in proposals]) if batch_document is None else batch_document
        return post_merge_gate.evaluate_post_merge_cluster_exposure_from_verified_batch_v1(source_document, cls.projection, proposals, policy() if exposure_policy is None else exposure_policy, incumbent, expected_incumbent_snapshot_hash=incumbent.snapshot_hash if expected_snapshot_hash is None else expected_snapshot_hash, expected_batch_preflight_hash=source_document["preflight_hash"], expected_projection_preregistration_hash=cls.projection_hash, projection_verification_context=cls.context)

    def test_proposal_only_passes_but_post_merge_cluster_limit_blocks(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot(((self.symbol_to_cluster[first], 2500), (self.symbol_to_cluster[second], 1000)))
        result = self.evaluate((proposal("p-1", first, 600), proposal("p-2", second, 400)), snapshot)
        self.assertEqual(result.status, post_merge_gate.STATUS_POST_MERGE_LIMIT_BREACH)
        self.assertEqual(result.blocker_codes, ("POST_MERGE_CLUSTER_GROSS_LIMIT_EXCEEDED",))
        self.assertEqual(result.maximum_post_merge_cluster_gross_bps, 3100)
        self.assertEqual(result.proposed_total_gross_bps, 1000)
        self.assertFalse(result.permission)

    def test_portfolio_total_can_breach_without_cluster_breach(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot(((self.symbol_to_cluster[first], 2500), (self.symbol_to_cluster[second], 2500)))
        result = self.evaluate((proposal("p-1", first, 500), proposal("p-2", second, 700)), snapshot, exposure_policy=policy(max_cluster=4000, max_portfolio=6000))
        self.assertEqual(result.blocker_codes, ("POST_MERGE_PORTFOLIO_GROSS_LIMIT_EXCEEDED",))
        self.assertEqual(result.maximum_post_merge_cluster_gross_bps, 3200)
        self.assertEqual(result.post_merge_total_gross_bps, 6200)

    def test_within_limit_merge_reports_redacted_counts_and_totals(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot(((self.symbol_to_cluster[first], 1000), (self.symbol_to_cluster[second], 1000)))
        result = self.evaluate((proposal("p-1", first, 500), proposal("p-2", second, 500)), snapshot)
        self.assertEqual(result.status, post_merge_gate.STATUS_WITHIN_POST_MERGE_LIMIT)
        self.assertEqual(result.blocker_codes, ())
        self.assertEqual(result.incumbent_total_gross_bps, 2000)
        self.assertEqual(result.proposed_total_gross_bps, 1000)
        self.assertEqual(result.post_merge_total_gross_bps, 3000)
        self.assertEqual(result.post_merge_cluster_count, 2)

    def test_empty_snapshot_reduces_to_proposal_exposure(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot(())
        result = self.evaluate((proposal("p-1", first, 500), proposal("p-2", second, 700)), snapshot)
        self.assertEqual(result.incumbent_cluster_count, 0)
        self.assertEqual(result.incumbent_total_gross_bps, 0)
        self.assertEqual(result.post_merge_total_gross_bps, 1200)
        self.assertEqual(result.maximum_post_merge_cluster_gross_bps, 700)

    def test_excluded_source_cluster_still_contributes_incumbent_risk(self):
        first = self.symbols[0]
        excluded = self.excluded_symbols[0]
        snapshot = self.snapshot(((self.symbol_to_cluster[excluded], 2900),))
        result = self.evaluate((proposal("p-1", first, 200),), snapshot)
        self.assertEqual(result.status, post_merge_gate.STATUS_WITHIN_POST_MERGE_LIMIT)
        self.assertEqual(result.incumbent_cluster_count, 1)
        self.assertEqual(result.post_merge_cluster_count, 2)
        self.assertEqual(result.maximum_post_merge_cluster_gross_bps, 2900)

    def test_projection_or_snapshot_content_drift_fails_exactly(self):
        first = self.symbols[0]
        snapshot = self.snapshot(((self.symbol_to_cluster[first], 1000),))
        projection_drift = replace(snapshot, projection_preregistration_hash="0" * 64)
        gross_drift = replace(snapshot, cluster_gross_bps=((self.symbol_to_cluster[first], 1100),))
        proposals = (proposal("p-1", first, 200),)
        self.assertIsNone(self.evaluate(proposals, projection_drift, expected_snapshot_hash=snapshot.snapshot_hash))
        self.assertIsNone(self.evaluate(proposals, gross_drift, expected_snapshot_hash=snapshot.snapshot_hash))

    def test_snapshot_builder_rejects_unknown_duplicate_and_noncanonical_clusters(self):
        first = self.symbols[0]
        cluster_id = self.symbol_to_cluster[first]
        common = dict(snapshot_id="invalid-snapshot", projection_preregistration_hash=self.projection_hash, source_clusters=self.source_clusters)
        self.assertIsNone(post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(**common, cluster_gross_bps=(("unknown-cluster", 100),)))
        self.assertIsNone(post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(**common, cluster_gross_bps=((cluster_id, 100), (cluster_id, 200))))
        values = tuple(reversed(sorted(((cluster_id, 100), (self.symbol_to_cluster[self.symbols[1]], 200)))))
        self.assertIsNone(post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(**common, cluster_gross_bps=values))

    def test_upstream_proposal_limit_block_hides_merge_metrics(self):
        symbol = self.symbols[0]
        snapshot = self.snapshot(())
        result = self.evaluate((proposal("p-1", symbol, 2000), proposal("p-2", symbol, 1500)), snapshot)
        self.assertEqual(result.status, post_merge_gate.STATUS_UPSTREAM_PROPOSAL_LIMIT_BREACH)
        self.assertEqual(result.blocker_codes, ("UPSTREAM_PROPOSAL_EXPOSURE_LIMIT_BREACH",))
        self.assertIsNone(result.post_merge_total_gross_bps)
        self.assertFalse(result.permission)

    def test_result_hashes_are_deterministic_and_cluster_ids_are_redacted(self):
        first, second = self.symbols[:2]
        snapshot = self.snapshot(((self.symbol_to_cluster[first], 500),))
        proposals = (proposal("p-1", first, 300), proposal("p-2", second, 400))
        one = self.evaluate(proposals, snapshot)
        two = self.evaluate(proposals, snapshot)
        self.assertEqual(one, two)
        self.assertRegex(one.source_proposal_result_hash, r"^[0-9a-f]{64}$")
        rendered = repr(one)
        for cluster in self.source_clusters:
            self.assertNotIn(cluster["cluster_id"], rendered)

    def test_production_gate_has_no_portfolio_reader_io_or_runtime_api(self):
        source = Path(post_merge_gate.__file__).read_text(encoding="utf-8")
        for forbidden in ("open(", "requests.", "urllib.", "socket.", "sqlite3", "subprocess", "portfolio_reader", "register_route(", "write_current_pointer("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
