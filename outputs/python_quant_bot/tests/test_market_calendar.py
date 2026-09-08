from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.market_calendar import (
    TEST_CALENDAR_NAME,
    build_market_calendar_contract,
)
from exchange_terminal.services.security_lifecycle import align_security_to_market_calendar


def row(session_date: str, close: float = 100.0) -> dict[str, object]:
    return {
        "date": session_date,
        "ts_ms": 1,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1_000_000,
        "complete": True,
    }


class MarketCalendarTests(unittest.TestCase):
    def test_xnys_excludes_independence_day_observed_holiday(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=["2026-07-02", "2026-07-06"],
        )

        self.assertEqual(contract["status"], "PASS")
        self.assertEqual(contract["expected_dates"], ["2026-07-02", "2026-07-06"])
        self.assertNotIn("2026-07-03", contract["expected_dates"])
        self.assertEqual(contract["research_admission_status"], "RESEARCH_ONLY")
        self.assertEqual(contract["source_class"], "THIRD_PARTY_LIBRARY")
        self.assertFalse(contract["official_source_verified"])
        self.assertFalse(contract["external_truth_verified"])

    def test_official_calendar_rejects_a_weekend_row(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=["2026-07-02", "2026-07-04", "2026-07-06"],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(contract["unexpected_dates"], ["2026-07-04"])

    def test_official_calendar_rejects_a_missing_session(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=["2026-07-02"],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(contract["missing_dates"], ["2026-07-06"])

    def test_weekday_fixture_is_deterministic_for_unit_tests(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name=TEST_CALENDAR_NAME,
            start_date="2026-07-02",
            end_date="2026-07-06",
        )

        self.assertEqual(contract["provider"], "deterministic_test_fixture")
        self.assertEqual(contract["expected_dates"], ["2026-07-02", "2026-07-03", "2026-07-06"])
        self.assertEqual(contract["research_admission_status"], "TEST_ONLY")

    def test_duplicate_observed_session_is_not_deduplicated_into_pass(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name=TEST_CALENDAR_NAME,
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=[
                "2026-07-02",
                "2026-07-02",
                "2026-07-03",
                "2026-07-06",
            ],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(contract["duplicate_observed_date_count"], 1)
        self.assertIn("duplicate_observed_dates:1", contract["blockers"])

    def test_early_close_requires_observed_session_window(self) -> None:
        missing_window = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-11-27",
            end_date="2026-11-27",
            observed_dates=["2026-11-27"],
        )
        matched = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-11-27",
            end_date="2026-11-27",
            observed_dates=["2026-11-27"],
            observed_sessions=missing_window["schedule"],
        )

        self.assertEqual(missing_window["status"], "PASS")
        self.assertFalse(missing_window["early_close_observation_complete"])
        self.assertIn("early_close_session_window_unobserved", missing_window["warnings"])
        self.assertEqual(matched["status"], "PASS")
        self.assertTrue(matched["early_close_observation_complete"])

    def test_declared_suspension_keeps_the_market_session_for_valuation(self) -> None:
        contract = align_security_to_market_calendar(
            symbol="AAA",
            rows_by_date={"2026-07-01": row("2026-07-01"), "2026-07-03": row("2026-07-03", 101.0)},
            expected_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
            lifecycle_events=[{
                "status": "SUSPENDED",
                "start_date": "2026-07-02",
                "end_date": "2026-07-02",
            }],
        )

        self.assertEqual(contract["status"], "PASS")
        self.assertEqual(len(contract["rows"]), 3)
        self.assertFalse(contract["rows"][1]["tradable"])
        self.assertEqual(contract["rows"][1]["close"], 100.0)
        self.assertEqual(contract["rows"][1]["valuation_basis"], "CARRY_FORWARD_LAST_CLOSE")

    def test_undeclared_missing_session_blocks_research(self) -> None:
        contract = align_security_to_market_calendar(
            symbol="AAA",
            rows_by_date={"2026-07-01": row("2026-07-01"), "2026-07-03": row("2026-07-03")},
            expected_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertIn("unverified_missing_sessions:1", contract["blockers"])

    def test_delisting_without_cash_settlement_blocks_research(self) -> None:
        contract = align_security_to_market_calendar(
            symbol="AAA",
            rows_by_date={"2026-07-01": row("2026-07-01")},
            expected_dates=["2026-07-01", "2026-07-02"],
            lifecycle_events=[{"status": "DELISTED", "start_date": "2026-07-02"}],
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertIn("delisting_settlement_price_missing:2026-07-02", contract["blockers"])

    def test_delisting_with_cash_settlement_creates_a_mandatory_event(self) -> None:
        contract = align_security_to_market_calendar(
            symbol="AAA",
            rows_by_date={"2026-07-01": row("2026-07-01")},
            expected_dates=["2026-07-01", "2026-07-02"],
            lifecycle_events=[{
                "status": "DELISTED",
                "start_date": "2026-07-02",
                "cash_settlement_price": 77.0,
            }],
        )

        self.assertEqual(contract["status"], "PASS")
        self.assertTrue(contract["rows"][1]["mandatory_cash_settlement"])
        self.assertEqual(contract["rows"][1]["open"], 77.0)


if __name__ == "__main__":
    unittest.main()
