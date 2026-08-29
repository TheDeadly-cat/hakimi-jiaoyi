from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange_terminal.application import (  # noqa: E402
    strategy_correlation_history_covered_budget_universe_cluster_exposure_readonly_projection_v1
    as readonly_projection,
)
from exchange_terminal.application import (  # noqa: E402
    strategy_correlation_history_covered_budget_universe_cluster_exposure_source_receipt_adapter_v1
    as source_adapter,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (  # noqa: E402
    POLICY_RESULT_UNKNOWN,
    POLICY_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
)
from tests import (  # noqa: E402
    test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_fixture_module,
)


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def reseal(document: dict) -> dict:
    mutated = copy.deepcopy(document)
    mutated.pop("readonly_projection_hash", None)
    mutated["readonly_projection_hash"] = digest(mutated)
    return mutated


def policy(
    *,
    max_portfolio_gross_bps: int = 8_000,
    max_cluster_gross_bps: int = 3_000,
    max_single_proposal_gross_bps: int = 2_000,
) -> ClusterExposurePolicyV1:
    return ClusterExposurePolicyV1(
        policy_version=POLICY_VERSION,
        policy_id="readonly-cluster-exposure-policy-20260824",
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


class ClusterExposureReadonlyProjectionV1Tests(unittest.TestCase):
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
        cls.projected_symbols = tuple(
            cls.projection["derivation"]["projected_symbols"]
        )
        if len(cls.projected_symbols) < 2:
            raise AssertionError("synthetic fixture needs two projected symbols")

    @classmethod
    def batch_document(cls, proposals):
        return cls.fixture._evaluate([item.symbol for item in proposals])

    @classmethod
    def build(
        cls,
        proposals,
        *,
        exposure_policy=None,
        batch_document=None,
        expected_batch_hash=None,
    ):
        source_document = (
            cls.batch_document(proposals)
            if batch_document is None
            else batch_document
        )
        source_hash = (
            source_document["preflight_hash"]
            if expected_batch_hash is None
            else expected_batch_hash
        )
        return readonly_projection.build_cluster_exposure_readonly_projection_from_verified_batch_v1(
            source_document,
            cls.projection,
            proposals,
            policy() if exposure_policy is None else exposure_policy,
            expected_batch_preflight_hash=source_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_exact_distinct_clusters_emit_neutral_redacted_summary(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_000),
            proposal("p-2", second, 1_100),
        )
        document = self.build(proposals)

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(
            document["status"],
            readonly_projection.PUBLIC_STATUS_WITHIN_LIMIT,
        )
        self.assertEqual(
            document["summary"],
            {
                "proposal_count": 2,
                "independent_cluster_count": 2,
                "total_gross_bps": 2_100,
                "maximum_cluster_gross_bps": 1_100,
            },
        )
        self.assertEqual(document["decision_path"]["permission"], "NOT_AUTHORIZED")
        self.assertFalse(document["authority"]["current_admission_allowed"])
        self.assertTrue(document["facts"]["within_limit_is_not_admission"])

    def test_exact_duplicate_symbol_batch_emits_shared_limit_breach(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (
            proposal("p-1", symbol, 1_600),
            proposal("p-2", symbol, 1_500),
        )
        document = self.build(proposals)

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(
            document["status"],
            readonly_projection.PUBLIC_STATUS_LIMIT_BREACH,
        )
        self.assertEqual(document["summary"]["independent_cluster_count"], 1)
        self.assertEqual(document["summary"]["total_gross_bps"], 3_100)
        self.assertEqual(document["summary"]["maximum_cluster_gross_bps"], 3_100)
        self.assertEqual(
            document["policy_blocker_codes"],
            ["CLUSTER_GROSS_LIMIT_EXCEEDED"],
        )
        self.assertFalse(document["authority"]["paper_authorized"])

    def test_invalid_policy_emits_unknown_without_metrics(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (proposal("p-1", symbol, 400),)
        invalid_policy = policy(
            max_cluster_gross_bps=500,
            max_single_proposal_gross_bps=600,
        )
        document = self.build(proposals, exposure_policy=invalid_policy)

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document["status"], readonly_projection.PUBLIC_STATUS_UNKNOWN)
        self.assertEqual(
            document["summary"],
            {
                "proposal_count": None,
                "independent_cluster_count": None,
                "total_gross_bps": None,
                "maximum_cluster_gross_bps": None,
            },
        )
        self.assertEqual(
            document["policy_blocker_codes"],
            ["POLICY_LIMIT_ORDER_INVALID"],
        )
        self.assertIsNone(document["source"]["policy_fingerprint_sha256"])

    def test_exact_verifier_rejects_resealed_authority_promotion(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_000),
            proposal("p-2", second, 1_000),
        )
        batch_document = self.batch_document(proposals)
        document = self.build(proposals, batch_document=batch_document)
        self.assertIsNotNone(document)
        assert document is not None

        self.assertTrue(
            readonly_projection.verify_cluster_exposure_readonly_projection_from_verified_batch_v1(
                document,
                batch_document,
                self.projection,
                proposals,
                policy(),
                expected_readonly_projection_hash=document[
                    "readonly_projection_hash"
                ],
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(document)
        tampered["authority"]["readonly_projection_activation_allowed"] = True
        tampered = reseal(tampered)
        self.assertFalse(
            readonly_projection.verify_cluster_exposure_readonly_projection_from_verified_batch_v1(
                tampered,
                batch_document,
                self.projection,
                proposals,
                policy(),
                expected_readonly_projection_hash=tampered[
                    "readonly_projection_hash"
                ],
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_occurrence_order_cannot_reuse_another_batch_document(self) -> None:
        first, second = self.projected_symbols[:2]
        original = (
            proposal("p-1", first, 900),
            proposal("p-2", second, 900),
        )
        reordered = (
            proposal("p-2", second, 900),
            proposal("p-1", first, 900),
        )
        batch_document = self.batch_document(original)

        self.assertIsNone(
            self.build(
                reordered,
                batch_document=batch_document,
                expected_batch_hash=batch_document["preflight_hash"],
            )
        )

    def test_raw_symbols_and_cluster_ids_do_not_enter_projection(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_000),
            proposal("p-2", second, 1_000),
        )
        document = self.build(proposals)
        self.assertIsNotNone(document)
        assert document is not None
        serialized = json.dumps(document, ensure_ascii=False, sort_keys=True)

        for symbol in (first, second):
            self.assertNotIn(json.dumps(symbol), serialized)
        budget = self.context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        for cluster in budget["expected_clusters"]:
            self.assertNotIn(json.dumps(cluster["cluster_id"]), serialized)

    def test_unallowlisted_blocker_cannot_enter_public_projection(self) -> None:
        symbol = self.projected_symbols[0]
        proposals = (proposal("p-1", symbol, 500),)
        batch_document = self.batch_document(proposals)
        result = source_adapter.evaluate_cluster_exposure_from_verified_batch_v1(
            batch_document,
            self.projection,
            proposals,
            policy(),
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertIsNotNone(result)
        assert result is not None
        forged = replace(
            result,
            policy_result=POLICY_RESULT_UNKNOWN,
            blocker_codes=("<script>alert(1)</script>",),
            proposal_count=None,
            independent_cluster_count=None,
            total_gross_bps=None,
            cluster_gross_bps=(),
        )
        self.assertIsNone(
            readonly_projection._build_projection_from_result_v1(forged)
        )

    def test_inconsistent_aggregate_metrics_are_rejected(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 700),
            proposal("p-2", second, 800),
        )
        batch_document = self.batch_document(proposals)
        result = source_adapter.evaluate_cluster_exposure_from_verified_batch_v1(
            batch_document,
            self.projection,
            proposals,
            policy(),
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertIsNotNone(result)
        assert result is not None
        forged = replace(result, total_gross_bps=(result.total_gross_bps or 0) + 1)
        self.assertIsNone(
            readonly_projection._build_projection_from_result_v1(forged)
        )

    def test_projection_hash_is_deterministic(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 600),
            proposal("p-2", second, 700),
        )
        first_document = self.build(proposals)
        second_document = self.build(proposals)

        self.assertEqual(first_document, second_document)
        assert first_document is not None
        self.assertRegex(
            first_document["readonly_projection_hash"],
            r"^[0-9a-f]{64}$",
        )

    def test_projection_source_has_no_io_or_runtime_registration(self) -> None:
        source = Path(readonly_projection.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "requests.",
            "urllib.",
            "sqlite3",
            "subprocess",
            "socket.",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
