from __future__ import annotations

import unittest

from exchange_terminal.services.strategy_research_currentness_facts import (
    build_strategy_research_currentness_facts,
)


class StrategyResearchCurrentnessFactsTests(unittest.TestCase):
    def test_complete_facts_report_exact_utc_ages_without_policy_claim(self) -> None:
        facts = build_strategy_research_currentness_facts(
            report_created_at="2026-08-10T12:00:00+00:00",
            summary_common_as_of="2026-08-09",
            selection_common_as_of="2026-08-09",
            observed_at_ms=1786536000000,
        )

        self.assertEqual(facts["status"], "FACTS_AVAILABLE")
        self.assertEqual(facts["report_age_ms"], 172_800_000)
        self.assertEqual(facts["calendar_days_since_dataset_as_of"], 3)
        self.assertEqual(facts["dataset_as_of_source"], "REPORT_SUMMARY_AND_SELECTION_ALIGNMENT")
        self.assertTrue(facts["facts_complete"])
        self.assertFalse(facts["threshold_applied"])
        self.assertIsNone(facts["report_age_threshold_ms"])
        self.assertIsNone(facts["dataset_age_threshold_calendar_days"])
        self.assertEqual(facts["report_age_policy_status"], "NOT_DEFINED")
        self.assertEqual(facts["dataset_freshness_policy_status"], "NOT_DEFINED")
        self.assertFalse(facts["paper_authorized"])
        self.assertFalse(facts["live_order_allowed"])

    def test_missing_dataset_date_is_partial_not_fabricated_zero(self) -> None:
        facts = build_strategy_research_currentness_facts(
            report_created_at="2026-08-12T02:03:04Z",
            summary_common_as_of="",
            selection_common_as_of=None,
            observed_at_ms=1786507384000,
        )

        self.assertEqual(facts["status"], "PARTIAL")
        self.assertIsNone(facts["dataset_as_of"])
        self.assertIsNone(facts["calendar_days_since_dataset_as_of"])
        self.assertGreater(facts["report_age_ms"], 0)
        self.assertIn("research_dataset_as_of_not_available", facts["evidence_gaps"])

    def test_mismatched_report_dataset_dates_fail_closed(self) -> None:
        facts = build_strategy_research_currentness_facts(
            report_created_at="2026-08-12T02:03:04+00:00",
            summary_common_as_of="2026-08-10",
            selection_common_as_of="2026-08-09",
            observed_at_ms=1786507384000,
        )

        self.assertEqual(facts["status"], "BLOCK")
        self.assertIsNone(facts["dataset_as_of"])
        self.assertIn("research_dataset_as_of_sources_mismatch", facts["blockers"])
        self.assertFalse(facts["freshness_conclusion_allowed"])

    def test_future_report_or_dataset_never_becomes_a_negative_age(self) -> None:
        report_future = build_strategy_research_currentness_facts(
            report_created_at="2026-08-13T00:00:00+00:00",
            summary_common_as_of="2026-08-12",
            selection_common_as_of="2026-08-12",
            observed_at_ms=1786507384000,
        )
        dataset_future = build_strategy_research_currentness_facts(
            report_created_at="2026-08-12T02:03:04+00:00",
            summary_common_as_of="2026-08-13",
            selection_common_as_of="2026-08-13",
            observed_at_ms=1786507384000,
        )

        self.assertEqual(report_future["status"], "BLOCK")
        self.assertIsNone(report_future["report_age_ms"])
        self.assertIn("research_report_created_after_observation", report_future["blockers"])
        self.assertEqual(dataset_future["status"], "BLOCK")
        self.assertIsNone(dataset_future["calendar_days_since_dataset_as_of"])
        self.assertIn("research_dataset_as_of_after_observation", dataset_future["blockers"])

    def test_numeric_strings_and_booleans_are_not_accepted_as_observation_time(self) -> None:
        for value in ("1786507384000", True, 1.5, -1):
            with self.subTest(value=value):
                facts = build_strategy_research_currentness_facts(
                    report_created_at="2026-08-12T02:03:04+00:00",
                    summary_common_as_of="2026-08-10",
                    selection_common_as_of="2026-08-10",
                    observed_at_ms=value,
                )
                self.assertEqual(facts["status"], "BLOCK")
                self.assertIsNone(facts["observed_at_ms"])
                self.assertIn("currentness_observation_time_invalid", facts["blockers"])


if __name__ == "__main__":
    unittest.main()
