from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (  # noqa: E402
    EXPECTED_PRODUCER_CONTRACT_VERSION,
    POLICY_RESULT_LIMIT_BREACH,
    POLICY_RESULT_UNKNOWN,
    POLICY_RESULT_WITHIN_LIMIT,
    POLICY_VERSION,
    SOURCE_RECEIPT_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
    ClusterExposureSourceReceiptV1,
    evaluate_cluster_exposure_preflight_v1,
)


SOURCE_SHA = "a" * 64


def source_receipt() -> ClusterExposureSourceReceiptV1:
    return ClusterExposureSourceReceiptV1(
        receipt_version=SOURCE_RECEIPT_VERSION,
        producer_contract_version=EXPECTED_PRODUCER_CONTRACT_VERSION,
        source_batch_fingerprint_sha256=SOURCE_SHA,
        structurally_complete=True,
        permission=False,
        symbol_cluster_pairs=(
            ("AAA", "cluster-a"),
            ("AAB", "cluster-a"),
            ("BBB", "cluster-b"),
            ("CCC", "cluster-c"),
        ),
    )


def policy() -> ClusterExposurePolicyV1:
    return ClusterExposurePolicyV1(
        policy_version=POLICY_VERSION,
        policy_id="preregistered-cluster-budget-20260824",
        max_proposals=8,
        max_portfolio_gross_bps=8_000,
        max_cluster_gross_bps=3_000,
        max_single_proposal_gross_bps=2_000,
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


class ClusterExposurePreflightV1Tests(unittest.TestCase):
    def evaluate(
        self,
        proposals: tuple[ClusterExposureProposalV1, ...],
        *,
        source: ClusterExposureSourceReceiptV1 | object | None = None,
        exposure_policy: ClusterExposurePolicyV1 | object | None = None,
    ):
        return evaluate_cluster_exposure_preflight_v1(
            source=source_receipt() if source is None else source,
            policy=policy() if exposure_policy is None else exposure_policy,
            proposals=proposals,
        )

    def test_correlated_symbols_collapse_to_one_exposure_bucket(self) -> None:
        result = self.evaluate(
            (
                proposal("p-1", "AAA", 1_200),
                proposal("p-2", "AAB", 800),
            )
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_WITHIN_LIMIT)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.cluster_gross_bps, (("cluster-a", 2_000),))
        self.assertEqual(result.total_gross_bps, 2_000)
        self.assertFalse(result.permission)
        self.assertTrue(result.research_only)

    def test_correlated_symbols_cannot_evade_cluster_limit(self) -> None:
        result = self.evaluate(
            (
                proposal("p-1", "AAA", 1_800),
                proposal("p-2", "AAB", 1_500),
            )
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_LIMIT_BREACH)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.cluster_gross_bps, (("cluster-a", 3_300),))
        self.assertEqual(
            result.blocker_codes,
            ("CLUSTER_GROSS_LIMIT_EXCEEDED",),
        )
        self.assertFalse(result.permission)

    def test_distinct_clusters_remain_distinct_and_canonical(self) -> None:
        result = self.evaluate(
            (
                proposal("p-b", "BBB", 1_600),
                proposal("p-a", "AAA", 1_100),
            )
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_WITHIN_LIMIT)
        self.assertEqual(result.independent_cluster_count, 2)
        self.assertEqual(
            result.cluster_gross_bps,
            (("cluster-a", 1_100), ("cluster-b", 1_600)),
        )

    def test_repeated_symbol_proposals_sum_in_source_owned_cluster(self) -> None:
        result = self.evaluate(
            (
                proposal("p-1", "AAA", 900),
                proposal("p-2", "AAA", 1_100),
            )
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_WITHIN_LIMIT)
        self.assertEqual(result.proposal_count, 2)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.cluster_gross_bps, (("cluster-a", 2_000),))

    def test_unmapped_symbol_is_unknown_and_exposes_no_metrics(self) -> None:
        result = self.evaluate((proposal("p-1", "ZZZ", 500),))

        self.assertEqual(result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(
            result.blocker_codes,
            ("PROPOSAL_SYMBOL_NOT_IN_SOURCE_MAP",),
        )
        self.assertIsNone(result.proposal_count)
        self.assertIsNone(result.independent_cluster_count)
        self.assertIsNone(result.total_gross_bps)
        self.assertEqual(result.cluster_gross_bps, ())
        self.assertFalse(result.permission)

    def test_duplicate_proposal_id_is_unknown(self) -> None:
        result = self.evaluate(
            (
                proposal("same-id", "AAA", 500),
                proposal("same-id", "BBB", 500),
            )
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(result.blocker_codes, ("DUPLICATE_PROPOSAL_ID",))
        self.assertIsNone(result.total_gross_bps)

    def test_source_map_must_be_unique_and_canonical(self) -> None:
        noncanonical = replace(
            source_receipt(),
            symbol_cluster_pairs=(
                ("BBB", "cluster-b"),
                ("AAA", "cluster-a"),
            ),
        )
        duplicate = replace(
            source_receipt(),
            symbol_cluster_pairs=(
                ("AAA", "cluster-a"),
                ("AAA", "cluster-b"),
            ),
        )

        noncanonical_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            source=noncanonical,
        )
        duplicate_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            source=duplicate,
        )

        self.assertEqual(noncanonical_result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertIn(
            "SOURCE_CLUSTER_MAP_NOT_CANONICAL",
            noncanonical_result.blocker_codes,
        )
        self.assertEqual(duplicate_result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertIn(
            "SOURCE_CLUSTER_MAP_DUPLICATE_SYMBOL",
            duplicate_result.blocker_codes,
        )

    def test_incomplete_or_authority_claiming_source_is_unknown(self) -> None:
        incomplete = replace(source_receipt(), structurally_complete=False)
        authority_claiming = replace(source_receipt(), permission=True)

        incomplete_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            source=incomplete,
        )
        authority_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            source=authority_claiming,
        )

        self.assertIn(
            "SOURCE_NOT_STRUCTURALLY_COMPLETE",
            incomplete_result.blocker_codes,
        )
        self.assertIn(
            "SOURCE_PERMISSION_MUST_REMAIN_FALSE",
            authority_result.blocker_codes,
        )
        self.assertFalse(incomplete_result.permission)
        self.assertFalse(authority_result.permission)

    def test_version_and_fingerprint_drift_fail_closed(self) -> None:
        drifted = replace(
            source_receipt(),
            producer_contract_version="batch-cluster-preflight-v2",
            source_batch_fingerprint_sha256="A" * 64,
        )
        result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            source=drifted,
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(
            result.blocker_codes,
            (
                "SOURCE_PRODUCER_VERSION_MISMATCH",
                "SOURCE_BATCH_FINGERPRINT_INVALID",
            ),
        )
        self.assertIsNone(result.source_batch_fingerprint_sha256)

    def test_policy_rejects_bool_and_non_monotonic_limits(self) -> None:
        bool_count = replace(policy(), max_proposals=True)
        non_monotonic = replace(
            policy(),
            max_cluster_gross_bps=1_000,
            max_single_proposal_gross_bps=1_500,
        )

        bool_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            exposure_policy=bool_count,
        )
        order_result = self.evaluate(
            (proposal("p-1", "AAA", 500),),
            exposure_policy=non_monotonic,
        )

        self.assertEqual(bool_result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertIn(
            "POLICY_MAX_PROPOSALS_INVALID",
            bool_result.blocker_codes,
        )
        self.assertEqual(order_result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(order_result.blocker_codes, ("POLICY_LIMIT_ORDER_INVALID",))

    def test_all_limit_breaches_have_stable_order(self) -> None:
        strict_policy = replace(
            policy(),
            max_proposals=1,
            max_portfolio_gross_bps=2_500,
            max_cluster_gross_bps=2_000,
            max_single_proposal_gross_bps=1_500,
        )
        result = self.evaluate(
            (
                proposal("p-1", "AAA", 1_800),
                proposal("p-2", "AAB", 1_000),
            ),
            exposure_policy=strict_policy,
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_LIMIT_BREACH)
        self.assertEqual(
            result.blocker_codes,
            (
                "PROPOSAL_COUNT_LIMIT_EXCEEDED",
                "SINGLE_PROPOSAL_GROSS_LIMIT_EXCEEDED",
                "CLUSTER_GROSS_LIMIT_EXCEEDED",
                "PORTFOLIO_GROSS_LIMIT_EXCEEDED",
            ),
        )
        self.assertFalse(result.permission)

    def test_output_is_deterministic_across_proposal_order(self) -> None:
        first = self.evaluate(
            (
                proposal("p-1", "AAA", 1_000),
                proposal("p-2", "BBB", 700),
            )
        )
        second = self.evaluate(
            (
                proposal("p-2", "BBB", 700),
                proposal("p-1", "AAA", 1_000),
            )
        )

        self.assertEqual(first.policy_result, second.policy_result)
        self.assertEqual(first.cluster_gross_bps, second.cluster_gross_bps)
        self.assertEqual(first.total_gross_bps, second.total_gross_bps)
        self.assertEqual(
            first.policy_fingerprint_sha256,
            second.policy_fingerprint_sha256,
        )
        self.assertRegex(first.policy_fingerprint_sha256 or "", r"^[0-9a-f]{64}$")

    def test_noncanonical_proposal_container_is_unknown(self) -> None:
        result = evaluate_cluster_exposure_preflight_v1(
            source=source_receipt(),
            policy=policy(),
            proposals=[proposal("p-1", "AAA", 500)],  # type: ignore[arg-type]
        )

        self.assertEqual(result.policy_result, POLICY_RESULT_UNKNOWN)
        self.assertEqual(result.blocker_codes, ("PROPOSAL_SET_NOT_CANONICAL",))
        self.assertFalse(result.permission)


if __name__ == "__main__":
    unittest.main()
