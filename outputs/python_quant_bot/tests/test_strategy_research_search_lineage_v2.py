from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
    build_strategy_research_search_lineage,
    build_strategy_research_search_lineage_v2,
    canonical_hash,
    verify_strategy_research_search_lineage,
)


class StrategyResearchSearchLineageV2Tests(unittest.TestCase):
    @staticmethod
    def _prior(report_schema_version: int = 16) -> dict:
        return {
            "registration_id": "prior-v5",
            "protocol_hash": "a" * 64,
            "registered_event_hash": "b" * 64,
            "search_family_id": "causal-trend-global-search",
            "report_schema_version": report_schema_version,
            "lineage_mode": "BOUND",
            "current_trial_count": 3,
            "cumulative_trial_count": 3,
        }

    def test_v1_remains_frozen_and_rejects_schema16_prior(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "strategy_search_prior_report_schema_invalid",
        ):
            build_strategy_research_search_lineage(
                search_family_id="causal-trend-global-search",
                prior_registrations=[self._prior()],
                current_trial_count=2,
            )
        genesis = build_strategy_research_search_lineage(
            search_family_id="causal-trend-global-search",
            prior_registrations=[],
            current_trial_count=2,
        )
        self.assertEqual(
            genesis["schema_version"],
            STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION,
        )
        self.assertEqual(
            verify_strategy_research_search_lineage(genesis)["status"],
            "PASS",
        )

    def test_v2_accepts_schema16_prior_and_replays_exactly(self) -> None:
        lineage = build_strategy_research_search_lineage_v2(
            search_family_id="causal-trend-global-search",
            prior_registrations=[self._prior()],
            current_trial_count=2,
        )
        verification = verify_strategy_research_search_lineage(
            lineage,
            expected_search_family_id="causal-trend-global-search",
            expected_current_trial_count=2,
            expected_prior_registrations=[self._prior()],
        )
        self.assertEqual(
            lineage["schema_version"],
            STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
        )
        self.assertEqual(lineage["prior_registration_count"], 1)
        self.assertEqual(lineage["prior_trial_count"], 3)
        self.assertEqual(lineage["cumulative_trial_count"], 5)
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(lineage["parameter_selection_allowed"])
        self.assertFalse(lineage["live_order_allowed"])

    def test_v2_rejects_report_schema_above_registered_target(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "strategy_search_prior_report_schema_invalid",
        ):
            build_strategy_research_search_lineage_v2(
                search_family_id="causal-trend-global-search",
                prior_registrations=[self._prior(17)],
                current_trial_count=2,
            )

    def test_coherent_downgrade_or_count_reseal_is_blocked(self) -> None:
        lineage = build_strategy_research_search_lineage_v2(
            search_family_id="causal-trend-global-search",
            prior_registrations=[self._prior()],
            current_trial_count=2,
        )
        downgrade = deepcopy(lineage)
        downgrade["schema_version"] = STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION
        count = deepcopy(lineage)
        count["cumulative_trial_count"] = 999
        for forged in (downgrade, count):
            clean = dict(forged)
            clean.pop("lineage_hash")
            forged["lineage_hash"] = canonical_hash(clean)
            verification = verify_strategy_research_search_lineage(
                forged,
                expected_search_family_id="causal-trend-global-search",
                expected_current_trial_count=2,
                expected_prior_registrations=[self._prior()],
            )
            self.assertEqual(verification["status"], "BLOCK")
