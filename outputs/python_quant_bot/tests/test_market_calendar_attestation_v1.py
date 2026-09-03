from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.market_calendar import (
    MARKET_CALENDAR_SCHEMA_VERSION,
    MARKET_SCHEDULE_ATTESTATION_VERSION,
    build_market_calendar_contract,
    build_market_schedule_attestation,
    canonical_market_calendar_hash,
    infer_market_calendar,
    verify_market_schedule_attestation,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sessions(*, early_close: bool = False) -> list[dict[str, object]]:
    return [
        {
            "date": "2026-07-02",
            "open_utc": "2026-07-02T14:30:00+00:00",
            "close_utc": "2026-07-02T21:00:00+00:00",
            "early_close": False,
        },
        {
            "date": "2026-07-03",
            "open_utc": "2026-07-03T14:30:00+00:00",
            "close_utc": (
                "2026-07-03T17:00:00+00:00"
                if early_close
                else "2026-07-03T21:00:00+00:00"
            ),
            "early_close": early_close,
        },
        {
            "date": "2026-07-06",
            "open_utc": "2026-07-06T14:30:00+00:00",
            "close_utc": "2026-07-06T21:00:00+00:00",
            "early_close": False,
        },
    ]


def attestation(
    *,
    source_class: str = "THIRD_PARTY_LIBRARY",
    early_close: bool = False,
) -> dict[str, object]:
    return build_market_schedule_attestation(
        calendar_name="XNYS",
        timezone_name="America/New_York",
        coverage_start="2026-07-02",
        coverage_end="2026-07-06",
        source_class=source_class,
        source_name=(
            "NYSE official schedule document"
            if source_class == "OFFICIAL_EXCHANGE_DOCUMENT"
            else "exchange_calendars"
        ),
        source_version="fixture-1",
        sessions=sessions(early_close=early_close),
    )


class MarketCalendarAttestationV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs_and_adapter_is_explicit(self) -> None:
        canonical_path = REPOSITORY_ROOT / "src" / "hakimi_research" / "market_calendar.py"
        adapter_path = PROJECT_ROOT / "exchange_terminal" / "services" / "market_calendar.py"
        canonical_source = canonical_path.read_text(encoding="utf-8")
        adapter_source = adapter_path.read_text(encoding="utf-8")

        self.assertTrue(canonical_path.is_file())
        self.assertNotIn("outputs", canonical_path.parts)
        self.assertNotIn("exchange_calendars", canonical_source)
        self.assertIn("from hakimi_research.market_calendar import", adapter_source)
        self.assertIn("def _exchange_sessions", adapter_source)

    def test_third_party_schedule_is_bound_but_never_official_truth(self) -> None:
        schedule_attestation = attestation()
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=["2026-07-02", "2026-07-03", "2026-07-06"],
            schedule_attestation=schedule_attestation,
        )

        self.assertEqual(MARKET_CALENDAR_SCHEMA_VERSION, "exchange-session-calendar-v2")
        self.assertEqual(
            MARKET_SCHEDULE_ATTESTATION_VERSION,
            "market-schedule-attestation-v1",
        )
        self.assertTrue(verify_market_schedule_attestation(schedule_attestation))
        self.assertEqual(contract["status"], "PASS")
        self.assertEqual(contract["research_admission_status"], "RESEARCH_ONLY")
        self.assertEqual(contract["source_class"], "THIRD_PARTY_LIBRARY")
        self.assertFalse(contract["official_source_claimed"])
        self.assertFalse(contract["official_source_verified"])
        self.assertFalse(contract["external_truth_verified"])
        self.assertTrue(all(value is False for value in contract["authority"].values()))

    def test_official_document_claim_cannot_self_verify_external_truth(self) -> None:
        schedule_attestation = attestation(source_class="OFFICIAL_EXCHANGE_DOCUMENT")
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            schedule_attestation=schedule_attestation,
        )

        self.assertTrue(schedule_attestation["official_source_claimed"])
        self.assertFalse(schedule_attestation["official_source_verified"])
        self.assertFalse(schedule_attestation["external_truth_verified"])
        self.assertTrue(contract["official_source_claimed"])
        self.assertFalse(contract["official_source_verified"])

    def test_duplicate_observed_dates_cannot_be_set_deduplicated(self) -> None:
        contract = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=[
                "2026-07-02",
                "2026-07-02",
                "2026-07-03",
                "2026-07-06",
            ],
            schedule_attestation=attestation(),
        )

        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(contract["duplicate_observed_date_count"], 1)
        self.assertIn("duplicate_observed_dates:1", contract["blockers"])

    def test_early_close_requires_and_replays_session_window(self) -> None:
        schedule_attestation = attestation(early_close=True)
        observed_dates = ["2026-07-02", "2026-07-03", "2026-07-06"]
        missing_window = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=observed_dates,
            schedule_attestation=schedule_attestation,
        )
        matched = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=observed_dates,
            observed_sessions=sessions(early_close=True),
            schedule_attestation=schedule_attestation,
        )
        mismatched_sessions = sessions(early_close=True)
        mismatched_sessions[1] = {
            **mismatched_sessions[1],
            "close_utc": "2026-07-03T21:00:00+00:00",
            "early_close": False,
        }
        mismatched = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2026-07-02",
            end_date="2026-07-06",
            observed_dates=observed_dates,
            observed_sessions=mismatched_sessions,
            schedule_attestation=schedule_attestation,
        )

        self.assertEqual(missing_window["status"], "PASS")
        self.assertFalse(missing_window["early_close_observation_complete"])
        self.assertIn("early_close_session_window_unobserved", missing_window["warnings"])
        self.assertEqual(matched["status"], "PASS")
        self.assertTrue(matched["early_close_observation_complete"])
        self.assertEqual(mismatched["status"], "BLOCK")
        self.assertIn("session_window_mismatch:1", mismatched["blockers"])

    def test_attestation_tamper_and_reseal_attempt_fail_verification(self) -> None:
        original = attestation()
        tampered = deepcopy(original)
        tampered["sessions"][0]["close_utc"] = "2026-07-02T20:00:00+00:00"

        with self.assertRaisesRegex(ValueError, "attestation_verification_failed"):
            verify_market_schedule_attestation(tampered)

        resealed = deepcopy(original)
        resealed["source_class"] = "FORGED_OFFICIAL_ALIAS"
        resealed["source_artifact_sha256"] = canonical_market_calendar_hash({
            "calendar_name": resealed["calendar_name"],
            "source_class": resealed["source_class"],
            "source_name": resealed["source_name"],
            "source_version": resealed["source_version"],
            "coverage_start": resealed["coverage_start"],
            "coverage_end": resealed["coverage_end"],
            "schedule_hash": resealed["schedule_hash"],
        })
        resealed_core = {
            key: value
            for key, value in resealed.items()
            if key != "attestation_hash"
        }
        resealed["attestation_hash"] = canonical_market_calendar_hash(resealed_core)
        with self.assertRaisesRegex(ValueError, "attestation_identity_invalid"):
            verify_market_schedule_attestation(resealed)

    def test_hostile_identity_types_do_not_run_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapIdentity:
            def __str__(self) -> str:
                calls.append("identity.__str__")
                return "XNYS"

        inferred = infer_market_calendar("AAPL", explicit=TrapIdentity())
        contract = build_market_calendar_contract(
            calendar_name=TrapIdentity(),
            start_date="2026-07-02",
            end_date="2026-07-06",
        )

        self.assertEqual(inferred, "UNVERIFIED")
        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
