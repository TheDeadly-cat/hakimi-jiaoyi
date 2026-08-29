from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import (  # noqa: E402
    strategy_correlation_history_covered_budget_universe_cluster_exposure_source_receipt_adapter_v1
    as adapter,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (  # noqa: E402
    POLICY_RESULT_LIMIT_BREACH,
    POLICY_RESULT_UNKNOWN,
    POLICY_RESULT_WITHIN_LIMIT,
    POLICY_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
)
from tests import (  # noqa: E402
    test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_fixture_module,
)


def policy(
    *,
    max_portfolio_gross_bps: int = 8_000,
    max_cluster_gross_bps: int = 3_000,
    max_single_proposal_gross_bps: int = 2_000,
) -> ClusterExposurePolicyV1:
    return ClusterExposurePolicyV1(
        policy_version=POLICY_VERSION,
        policy_id="adapter-preregistered-cluster-budget-20260824",
        max_proposals=8,
        max_portfolio_gross_bps=max_portfolio_gross_bps,
        max_cluster_gross_bps=max_cluster_gross_bps,
        max_single_proposal_gross_bps=max_single_proposal_gross_bps,
    )


def proposal(
    proposal_id: str,
    symbol: str,
    requested_gross_bps: int,
) -> ClusterExposureProposalV1:
    return ClusterExposureProposalV1(
        proposal_id=proposal_id,
        symbol=symbol,
        requested_gross_bps=requested_gross_bps,
    )


class ClusterExposureSourceReceiptAdapterV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            batch_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.projection = fixture.projection
        cls.projection_hash = fixture.projection_hash
        cls.context = fixture.context

        budget = cls.context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        projected = set(cls.projection["derivation"]["projected_symbols"])
        projected_groups = []
        for cluster in budget["expected_clusters"]:
            members = [
                member for member in cluster["members"] if member in projected
            ]
            if members:
                projected_groups.append((cluster["cluster_id"], members))
        if len(projected_groups) < 2:
            raise AssertionError("synthetic fixture needs two projected clusters")
        cls.primary_symbol = projected_groups[0][1][0]
        cls.distinct_pair = (
            projected_groups[0][1][0],
            projected_groups[1][1][0],
        )

    @classmethod
    def batch_document(cls, symbols: list[str]):
        return cls.fixture._evaluate(symbols)

    @classmethod
    def build_receipt(
        cls,
        symbols: list[str],
        *,
        document=None,
        expected_hash=None,
        projection=None,
        context=None,
    ):
        source_document = cls.batch_document(symbols) if document is None else document
        source_hash = (
            source_document["preflight_hash"]
            if expected_hash is None
            else expected_hash
        )
        return adapter.build_cluster_exposure_source_receipt_v1(
            source_document,
            cls.projection if projection is None else projection,
            symbols,
            expected_batch_preflight_hash=source_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=(
                cls.context if context is None else context
            ),
        )

    @classmethod
    def evaluate(
        cls,
        proposals: tuple[ClusterExposureProposalV1, ...],
        *,
        document=None,
        expected_hash=None,
        exposure_policy=None,
    ):
        symbols = [item.symbol for item in proposals]
        source_document = cls.batch_document(symbols) if document is None else document
        source_hash = (
            source_document["preflight_hash"]
            if expected_hash is None
            else expected_hash
        )
        return adapter.evaluate_cluster_exposure_from_verified_batch_v1(
            source_document,
            cls.projection,
            proposals,
            policy() if exposure_policy is None else exposure_policy,
            expected_batch_preflight_hash=source_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_receipt_binds_exact_batch_hash_and_source_owned_cluster(self) -> None:
        symbols = list(self.distinct_pair)
        document = self.batch_document(symbols)
        receipt = self.build_receipt(symbols, document=document)

        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(
            receipt.source_batch_fingerprint_sha256,
            document["preflight_hash"],
        )
        self.assertTrue(receipt.structurally_complete)
        self.assertFalse(receipt.permission)
        self.assertEqual(tuple(sorted(receipt.symbol_cluster_pairs)), receipt.symbol_cluster_pairs)
        self.assertEqual(len({pair[1] for pair in receipt.symbol_cluster_pairs}), 2)

    def test_correlated_partition_preserves_shared_cluster_hash_binding(self) -> None:
        batch_preflight = batch_fixture_module.batch_preflight
        proposed_symbols = ["A", "B"]
        source_symbols = ["A", "B", "C"]
        source_clusters = [
            {"cluster_id": "cluster-ab", "members": ["A", "B"]},
            {"cluster_id": "cluster-c", "members": ["C"]},
        ]
        projection = {
            "derivation": {
                "projected_symbols": ["A", "B"],
                "excluded_symbols": ["C"],
            }
        }
        context = {
            "structural_gate_verification_context": {
                "budget_cluster_preregistration": {
                    "expected_symbols": source_symbols,
                    "expected_clusters": source_clusters,
                }
            }
        }
        partition = adapter._extract_verified_partition(
            projection,
            proposed_symbols,
            context,
        )
        self.assertIsNotNone(partition)
        assert partition is not None
        symbol_to_cluster, ordered_clusters = partition
        self.assertEqual(
            symbol_to_cluster,
            {"A": "cluster-ab", "B": "cluster-ab", "C": "cluster-c"},
        )

        derivation = batch_preflight.derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
            proposed_symbols,
            source_symbols,
            source_clusters,
            ["A", "B"],
            ["C"],
        )
        self.assertIsNotNone(derivation)
        assert derivation is not None
        document = {
            "schema_version": batch_preflight.PREFLIGHT_SCHEMA_VERSION,
            "static_fingerprint": batch_preflight.STATIC_FINGERPRINT,
            "consumer_status": batch_preflight.CONSUMER_STATUS,
            "registered": False,
            "status": batch_preflight.PROJECTED_IMMATURE_STATUS,
            "authority": copy.deepcopy(adapter._EXPECTED_AUTHORITY),
            "facts": copy.deepcopy(adapter._EXPECTED_FACTS),
            "ticket_summary": dict(derivation["counts"]),
            "evidence": {
                "unique_proposal_symbol_hashes": list(
                    derivation["unique_proposal_symbol_hashes"]
                ),
                "projected_cluster_id_hashes": list(
                    derivation["projected_cluster_id_hashes"]
                ),
                "excluded_cluster_id_hashes": list(
                    derivation["excluded_cluster_id_hashes"]
                ),
                "unknown_proposal_symbol_hashes": list(
                    derivation["unknown_proposal_symbol_hashes"]
                ),
            },
        }
        self.assertTrue(
            adapter._document_bindings_hold(
                document,
                proposed_symbols,
                symbol_to_cluster,
                ordered_clusters,
            )
        )

    def test_distinct_verified_clusters_remain_within_shared_policy(self) -> None:
        first, second = self.distinct_pair
        result = self.evaluate(
            (
                proposal("p-1", first, 1_000),
                proposal("p-2", second, 1_100),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.policy_result, POLICY_RESULT_WITHIN_LIMIT)
        self.assertEqual(result.independent_cluster_count, 2)
        self.assertFalse(result.permission)

    def test_duplicate_occurrences_bind_once_but_exposure_sums(self) -> None:
        symbol = self.primary_symbol
        result = self.evaluate(
            (
                proposal("p-1", symbol, 700),
                proposal("p-2", symbol, 800),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.policy_result, POLICY_RESULT_WITHIN_LIMIT)
        self.assertEqual(result.proposal_count, 2)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.total_gross_bps, 1_500)

    def test_excluded_and_unknown_batches_produce_no_receipt(self) -> None:
        excluded_symbol = self.projection["derivation"]["excluded_symbols"][0]
        excluded_receipt = self.build_receipt([excluded_symbol])
        unknown_receipt = self.build_receipt(["UNKNOWN-SYMBOL"])

        self.assertIsNone(excluded_receipt)
        self.assertIsNone(unknown_receipt)

    def test_document_permission_tamper_produces_no_receipt(self) -> None:
        symbols = list(self.distinct_pair)
        document = self.batch_document(symbols)
        tampered = copy.deepcopy(document)
        tampered["authority"]["paper_authorized"] = True

        self.assertIsNone(self.build_receipt(symbols, document=tampered))

    def test_wrong_expected_batch_hash_produces_no_receipt(self) -> None:
        symbols = list(self.distinct_pair)
        document = self.batch_document(symbols)
        self.assertIsNone(
            self.build_receipt(
                symbols,
                document=document,
                expected_hash="0" * 64,
            )
        )

    def test_proposal_occurrence_order_is_bound_to_batch_document(self) -> None:
        first, second = self.distinct_pair
        original = [first, second]
        document = self.batch_document(original)
        self.assertIsNone(
            self.build_receipt(
                [second, first],
                document=document,
                expected_hash=document["preflight_hash"],
            )
        )

    def test_projection_context_drift_produces_no_receipt(self) -> None:
        symbols = list(self.distinct_pair)
        document = self.batch_document(symbols)
        drifted_context = copy.deepcopy(self.context)
        budget = drifted_context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        budget["expected_clusters"][0]["cluster_id"] += "-drift"

        self.assertIsNone(
            self.build_receipt(
                symbols,
                document=document,
                context=drifted_context,
            )
        )

    def test_invalid_policy_remains_unknown_and_unauthorized(self) -> None:
        symbol = self.primary_symbol
        invalid_policy = policy(max_cluster_gross_bps=500, max_single_proposal_gross_bps=600)
        result = self.evaluate(
            (proposal("p-1", symbol, 400),),
            exposure_policy=invalid_policy,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(result.blocker_codes, ("POLICY_LIMIT_ORDER_INVALID",))
        self.assertFalse(result.permission)

    def test_adapter_source_has_no_io_or_runtime_registration(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "requests.",
            "urllib.",
            "sqlite3",
            "subprocess",
            "socket.",
            "register_route",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
