from __future__ import annotations

from dataclasses import replace
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
        policy_id="concentration-source-exposure-policy-20260824",
        max_proposals=8,
        max_portfolio_gross_bps=8_000,
        max_cluster_gross_bps=3_000,
        max_single_proposal_gross_bps=3_000,
    )


def concentration_policy() -> concentration_gate.ClusterExposureConcentrationPolicyV1:
    return concentration_gate.ClusterExposureConcentrationPolicyV1(
        policy_version=concentration_gate.POLICY_VERSION,
        policy_id="preregistered-cluster-concentration-20260824",
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


class ClusterExposureConcentrationGateV1Tests(unittest.TestCase):
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
    def evaluate(
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
        return concentration_gate.evaluate_cluster_exposure_concentration_from_verified_batch_v1(
            source_document,
            cls.projection,
            proposals,
            exposure_policy() if source_policy is None else source_policy,
            concentration_policy() if policy is None else policy,
            expected_batch_preflight_hash=source_document["preflight_hash"],
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_balanced_absolute_limits_pass_concentration_structure_only(self) -> None:
        first, second = self.projected_symbols[:2]
        result = self.evaluate(
            (
                proposal("p-1", first, 2_000),
                proposal("p-2", second, 2_000),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(
            result.status,
            concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT,
        )
        self.assertEqual(result.largest_cluster_share_bps_ceiling, 5_000)
        self.assertEqual(result.hhi_ppm_ceiling, 500_000)
        self.assertEqual(result.effective_cluster_count_milli_floor, 2_000)
        self.assertEqual(result.blocker_codes, ())
        self.assertFalse(result.permission)

    def test_absolute_limits_can_pass_while_concentration_fails(self) -> None:
        first, second = self.projected_symbols[:2]
        result = self.evaluate(
            (
                proposal("p-1", first, 3_000),
                proposal("p-2", second, 1_000),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(
            result.status,
            concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH,
        )
        self.assertEqual(result.largest_cluster_share_bps_ceiling, 7_500)
        self.assertEqual(result.hhi_ppm_ceiling, 625_000)
        self.assertEqual(result.effective_cluster_count_milli_floor, 1_600)
        self.assertEqual(
            result.blocker_codes,
            (
                "LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED",
                "CLUSTER_HHI_LIMIT_EXCEEDED",
            ),
        )
        self.assertFalse(result.permission)

    def test_single_effective_cluster_triggers_all_concentration_guards(self) -> None:
        symbol = self.projected_symbols[0]
        result = self.evaluate(
            (
                proposal("p-1", symbol, 1_000),
                proposal("p-2", symbol, 1_000),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(
            result.blocker_codes,
            (
                "INDEPENDENT_CLUSTER_COUNT_BELOW_MINIMUM",
                "LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED",
                "CLUSTER_HHI_LIMIT_EXCEEDED",
            ),
        )
        self.assertEqual(result.largest_cluster_share_bps_ceiling, 10_000)
        self.assertEqual(result.hhi_ppm_ceiling, 1_000_000)
        self.assertEqual(result.effective_cluster_count_milli_floor, 1_000)

    def test_ratio_rounding_is_conservative_and_integer_only(self) -> None:
        first, second = self.projected_symbols[:2]
        result = self.evaluate(
            (
                proposal("p-1", first, 2),
                proposal("p-2", second, 1),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.largest_cluster_share_bps_ceiling, 6_667)
        self.assertEqual(result.hhi_ppm_ceiling, 555_556)
        self.assertEqual(result.effective_cluster_count_milli_floor, 1_800)
        self.assertEqual(
            result.status,
            concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH,
        )

    def test_upstream_exposure_limit_breach_prevents_concentration_claim(self) -> None:
        symbol = self.projected_symbols[0]
        result = self.evaluate(
            (
                proposal("p-1", symbol, 2_000),
                proposal("p-2", symbol, 1_500),
            )
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(
            result.status,
            concentration_gate.STATUS_UPSTREAM_LIMIT_BREACH,
        )
        self.assertEqual(result.blocker_codes, ("UPSTREAM_EXPOSURE_LIMIT_BREACH",))
        self.assertIsNone(result.largest_cluster_share_bps_ceiling)
        self.assertIsNone(result.hhi_ppm_ceiling)
        self.assertFalse(result.permission)

    def test_unknown_upstream_policy_exposes_no_concentration_metrics(self) -> None:
        symbol = self.projected_symbols[0]
        invalid_source_policy = replace(
            exposure_policy(),
            max_cluster_gross_bps=500,
            max_single_proposal_gross_bps=600,
        )
        result = self.evaluate(
            (proposal("p-1", symbol, 400),),
            source_policy=invalid_source_policy,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, concentration_gate.STATUS_UNKNOWN)
        self.assertEqual(
            result.blocker_codes,
            ("UPSTREAM_EXPOSURE_CONTRACT_UNKNOWN",),
        )
        self.assertIsNone(result.proposal_count)
        self.assertIsNone(result.total_gross_bps)

    def test_invalid_concentration_policy_is_unknown_and_bool_is_rejected(self) -> None:
        first, second = self.projected_symbols[:2]
        invalid_policy = replace(concentration_policy(), max_hhi_ppm=True)
        result = self.evaluate(
            (
                proposal("p-1", first, 1_000),
                proposal("p-2", second, 1_000),
            ),
            policy=invalid_policy,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, concentration_gate.STATUS_UNKNOWN)
        self.assertEqual(result.blocker_codes, ("MAX_CLUSTER_HHI_INVALID",))
        self.assertIsNone(result.concentration_policy_fingerprint_sha256)
        self.assertIsNone(result.hhi_ppm_ceiling)
        self.assertFalse(result.permission)

    def test_source_and_policy_hashes_are_deterministic(self) -> None:
        first, second = self.projected_symbols[:2]
        proposals = (
            proposal("p-1", first, 1_200),
            proposal("p-2", second, 1_100),
        )
        first_result = self.evaluate(proposals)
        second_result = self.evaluate(proposals)

        self.assertEqual(first_result, second_result)
        assert first_result is not None
        self.assertRegex(first_result.source_exposure_result_hash, r"^[0-9a-f]{64}$")
        self.assertRegex(
            first_result.concentration_policy_fingerprint_sha256 or "",
            r"^[0-9a-f]{64}$",
        )

    def test_batch_occurrence_order_remains_exactly_bound(self) -> None:
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
        self.assertIsNone(
            self.evaluate(reordered, batch_document=batch_document)
        )

    def test_result_redacts_cluster_ids_and_production_has_no_io(self) -> None:
        first, second = self.projected_symbols[:2]
        result = self.evaluate(
            (
                proposal("p-1", first, 1_000),
                proposal("p-2", second, 1_000),
            )
        )
        self.assertIsNotNone(result)
        assert result is not None
        rendered = repr(result)
        budget = self.context["structural_gate_verification_context"][
            "budget_cluster_preregistration"
        ]
        for cluster in budget["expected_clusters"]:
            self.assertNotIn(cluster["cluster_id"], rendered)

        source = Path(concentration_gate.__file__).read_text(encoding="utf-8")
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
