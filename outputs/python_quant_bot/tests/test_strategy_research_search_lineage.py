from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage,
    verify_strategy_research_search_lineage,
)


class StrategyResearchSearchLineageTests(unittest.TestCase):
    def test_genesis_and_chained_lineage_are_exact_and_cumulative(self) -> None:
        genesis = build_strategy_research_search_lineage(
            search_family_id="causal-breakout-v1",
            prior_registrations=[],
            current_trial_count=3,
        )
        self.assertEqual(genesis["prior_trial_count"], 0)
        self.assertEqual(genesis["cumulative_trial_count"], 3)
        self.assertIsNone(genesis["parent_registration_hash"])
        self.assertEqual(
            verify_strategy_research_search_lineage(
                genesis,
                expected_search_family_id="causal-breakout-v1",
                expected_current_trial_count=3,
                expected_prior_registrations=[],
            )["status"],
            "PASS",
        )

        prior = [{
            "registration_id": "registration-1",
            "protocol_hash": "a" * 64,
            "registered_event_hash": "b" * 64,
            "search_family_id": "causal-breakout-v1",
            "report_schema_version": 14,
            "lineage_mode": "BOUND",
            "current_trial_count": 3,
            "cumulative_trial_count": 3,
        }]
        chained = build_strategy_research_search_lineage(
            search_family_id="causal-breakout-v1",
            prior_registrations=prior,
            current_trial_count=6,
        )
        self.assertEqual(chained["prior_registration_count"], 1)
        self.assertEqual(chained["prior_trial_count"], 3)
        self.assertEqual(chained["cumulative_trial_count"], 9)
        self.assertEqual(chained["parent_registration_hash"], "a" * 64)
        self.assertEqual(chained["parent_registry_event_hash"], "b" * 64)
        self.assertEqual(
            verify_strategy_research_search_lineage(
                chained,
                expected_search_family_id="causal-breakout-v1",
                expected_current_trial_count=6,
                expected_prior_registrations=prior,
            )["status"],
            "PASS",
        )

    def test_self_reseal_cannot_replace_registry_derived_prior_chain(self) -> None:
        expected_prior = [{
            "registration_id": "registration-1",
            "protocol_hash": "a" * 64,
            "registered_event_hash": "b" * 64,
            "search_family_id": "causal-breakout-v1",
            "report_schema_version": 14,
            "lineage_mode": "BOUND",
            "current_trial_count": 3,
            "cumulative_trial_count": 3,
        }]
        forged = build_strategy_research_search_lineage(
            search_family_id="causal-breakout-v1",
            prior_registrations=[],
            current_trial_count=3,
        )
        result = verify_strategy_research_search_lineage(
            forged,
            expected_search_family_id="causal-breakout-v1",
            expected_current_trial_count=3,
            expected_prior_registrations=expected_prior,
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("strategy_search_registry_lineage_mismatch", result["blockers"])

        tampered = deepcopy(forged)
        tampered["cumulative_trial_count"] = 300
        self.assertEqual(
            verify_strategy_research_search_lineage(tampered)["status"],
            "BLOCK",
        )

    def test_prior_cumulative_chain_must_equal_sum_of_registered_trials(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "strategy_search_prior_cumulative_chain_invalid",
        ):
            build_strategy_research_search_lineage(
                search_family_id="causal-breakout-v1",
                prior_registrations=[{
                    "registration_id": "registration-1",
                    "protocol_hash": "a" * 64,
                    "registered_event_hash": "b" * 64,
                    "search_family_id": "causal-breakout-v1",
                    "report_schema_version": 14,
                    "lineage_mode": "BOUND",
                    "current_trial_count": 3,
                    "cumulative_trial_count": 2,
                }],
                current_trial_count=3,
            )


if __name__ == "__main__":
    unittest.main()
