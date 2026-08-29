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
    strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_gate_v1
    as concentration_gate,
)
from exchange_terminal.application import (  # noqa: E402
    strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_readonly_projection_v1
    as readonly_projection,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (  # noqa: E402
    POLICY_VERSION as EXPOSURE_POLICY_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposureProposalV1,
)
from tests import (  # noqa: E402
    test_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_fixture_module,
)


def exposure_policy() -> ClusterExposurePolicyV1:
    return ClusterExposurePolicyV1(
        policy_version=EXPOSURE_POLICY_VERSION,
        policy_id="concentration-projection-source-policy-20260824",
        max_proposals=8,
        max_portfolio_gross_bps=8_000,
        max_cluster_gross_bps=3_000,
        max_single_proposal_gross_bps=3_000,
    )


def concentration_policy() -> concentration_gate.ClusterExposureConcentrationPolicyV1:
    return concentration_gate.ClusterExposureConcentrationPolicyV1(
        policy_version=concentration_gate.POLICY_VERSION,
        policy_id="concentration-projection-policy-20260824",
        min_independent_clusters=2,
        max_largest_cluster_share_bps=6_000,
        max_hhi_ppm=550_000,
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


def reseal(document: dict) -> dict:
    mutated = copy.deepcopy(document)
    mutated.pop("readonly_projection_hash", None)
    encoded = json.dumps(
        mutated,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    mutated["readonly_projection_hash"] = hashlib.sha256(encoded).hexdigest()
    return mutated


class ClusterExposureConcentrationReadonlyProjectionV1Tests(unittest.TestCase):
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
    def build(
        cls,
        proposals,
        *,
        source_policy=None,
        policy=None,
        batch_document=None,
    ):
        source_document = (
            cls.fixture._evaluate([item.symbol for item in proposals])
            if batch_document is None
            else batch_document
        )
        return readonly_projection.build_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
            source_document,
            cls.projection,
            proposals,
            exposure_policy() if source_policy is None else source_policy,
            concentration_policy() if policy is None else policy,
            expected_batch_preflight_hash=source_document["preflight_hash"],
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_balanced_clusters_emit_neutral_observed_projection(self) -> None:
        first, second = self.projected_symbols[:2]
        document = self.build(
            (
                proposal("p-1", first, 2_000),
                proposal("p-2", second, 2_000),
            )
        )

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(
            document["status"],
            concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT,
        )
        self.assertEqual(
            document["summary"],
            {
                "proposal_count": 2,
                "independent_cluster_count": 2,
                "total_gross_bps": 4_000,
                "largest_cluster_share_bps_ceiling": 5_000,
                "hhi_ppm_ceiling": 500_000,
                "effective_cluster_count_milli_floor": 2_000,
            },
        )
        self.assertEqual(document["policy_blocker_codes"], [])
        self.assertEqual(document["decision_path"]["permission"], "NOT_AUTHORIZED")
        self.assertFalse(document["authority"]["diversification_claim_allowed"])

    def test_absolute_limits_pass_but_concentration_projection_is_blocked(self) -> None:
        first, second = self.projected_symbols[:2]
        document = self.build(
            (
                proposal("p-1", first, 3_000),
                proposal("p-2", second, 1_000),
            )
        )

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(
            document["status"],
            concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH,
        )
        self.assertEqual(
            document["policy_blocker_codes"],
            [
                "LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED",
                "CLUSTER_HHI_LIMIT_EXCEEDED",
            ],
        )
        self.assertEqual(
            document["summary"]["largest_cluster_share_bps_ceiling"],
            7_500,
        )
        self.assertEqual(document["summary"]["hhi_ppm_ceiling"], 625_000)
        self.assertFalse(document["authority"]["paper_authorized"])

    def test_upstream_absolute_limit_block_hides_concentration_metrics(self) -> None:
        symbol = self.projected_symbols[0]
        document = self.build(
            (
                proposal("p-1", symbol, 2_000),
                proposal("p-2", symbol, 1_500),
            )
        )

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(
            document["status"],
            concentration_gate.STATUS_UPSTREAM_LIMIT_BREACH,
        )
        self.assertEqual(
            document["policy_blocker_codes"],
            ["UPSTREAM_EXPOSURE_LIMIT_BREACH"],
        )
        self.assertTrue(all(value is None for value in document["summary"].values()))

    def test_invalid_concentration_policy_emits_unknown_without_metrics(self) -> None:
        first, second = self.projected_symbols[:2]
        invalid_policy = replace(concentration_policy(), max_hhi_ppm=True)
        document = self.build(
            (
                proposal("p-1", first, 1_000),
                proposal("p-2", second, 1_000),
            ),
            policy=invalid_policy,
        )

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document["status"], concentration_gate.STATUS_UNKNOWN)
        self.assertEqual(document["policy_blocker_codes"], ["MAX_CLUSTER_HHI_INVALID"])
        self.assertTrue(all(value is None for value in document["summary"].values()))
        self.assertIsNone(
            document["source"]["concentration_policy_fingerprint_sha256"]
        )

    def test_exact_verifier_rejects_resealed_authority_promotion(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 2_000),
            proposal("p-2", second, 2_000),
        )
        batch_document = self.fixture._evaluate([item.symbol for item in proposals])
        document = self.build(proposals, batch_document=batch_document)
        self.assertIsNotNone(document)
        assert document is not None
        projection_hash = document["readonly_projection_hash"]
        self.assertTrue(
            readonly_projection.verify_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
                document,
                batch_document,
                self.projection,
                proposals,
                exposure_policy(),
                concentration_policy(),
                expected_readonly_projection_hash=projection_hash,
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(document)
        tampered["authority"]["diversification_claim_allowed"] = True
        tampered = reseal(tampered)
        self.assertFalse(
            readonly_projection.verify_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
                tampered,
                batch_document,
                self.projection,
                proposals,
                exposure_policy(),
                concentration_policy(),
                expected_readonly_projection_hash=tampered[
                    "readonly_projection_hash"
                ],
                expected_batch_preflight_hash=batch_document["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_batch_occurrence_order_cannot_reuse_original_projection(self) -> None:
        first, second = self.projected_symbols[:2]
        original = (
            proposal("p-1", first, 900),
            proposal("p-2", second, 800),
        )
        reordered = (
            proposal("p-2", second, 800),
            proposal("p-1", first, 900),
        )
        batch_document = self.fixture._evaluate([item.symbol for item in original])
        self.assertIsNone(self.build(reordered, batch_document=batch_document))

    def test_unallowlisted_blocker_cannot_enter_projection(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 2_000),
            proposal("p-2", second, 2_000),
        )
        batch_document = self.fixture._evaluate([item.symbol for item in proposals])
        result = concentration_gate.evaluate_cluster_exposure_concentration_from_verified_batch_v1(
            batch_document,
            self.projection,
            proposals,
            exposure_policy(),
            concentration_policy(),
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertIsNotNone(result)
        assert result is not None
        forged = replace(result, blocker_codes=("<script>alert(1)</script>",))
        self.assertIsNone(readonly_projection._build_projection_from_result_v1(forged))

    def test_inconsistent_effective_cluster_metric_is_rejected(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 2_000),
            proposal("p-2", second, 2_000),
        )
        batch_document = self.fixture._evaluate([item.symbol for item in proposals])
        result = concentration_gate.evaluate_cluster_exposure_concentration_from_verified_batch_v1(
            batch_document,
            self.projection,
            proposals,
            exposure_policy(),
            concentration_policy(),
            expected_batch_preflight_hash=batch_document["preflight_hash"],
            expected_projection_preregistration_hash=self.projection_hash,
            projection_verification_context=self.context,
        )
        self.assertIsNotNone(result)
        assert result is not None
        forged = replace(result, effective_cluster_count_milli_floor=2_001)
        self.assertIsNone(readonly_projection._build_projection_from_result_v1(forged))

    def test_projection_is_redacted_and_hash_deterministic(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_200),
            proposal("p-2", second, 1_100),
        )
        first_document = self.build(proposals)
        second_document = self.build(proposals)
        self.assertEqual(first_document, second_document)
        self.assertIsNotNone(first_document)
        assert first_document is not None
        serialized = json.dumps(first_document, ensure_ascii=False)
        for symbol in (first, second):
            self.assertNotIn(json.dumps(symbol), serialized)
        budget = self.context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        for cluster in budget["expected_clusters"]:
            self.assertNotIn(json.dumps(cluster["cluster_id"]), serialized)
        self.assertRegex(first_document["readonly_projection_hash"], r"^[0-9a-f]{64}$")

    def test_production_projection_has_no_io_or_runtime_registration(self) -> None:
        source = Path(readonly_projection.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "subprocess",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
