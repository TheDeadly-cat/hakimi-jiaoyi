"""Portable local CLI regression for calendar coverage and point-in-time events."""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.documents import read_document
from hakimi_research.equity_cli import main
from hakimi_research.equity_dataset import build_equity_snapshot, save_equity_snapshot
from hakimi_research.equity_events import build_equity_event, save_equity_event


def snapshot_fixture():
    """All data and attestations are fictional and supplied in memory."""
    raw = b"session_date,open,high,low,close,volume\n2024-11-29,100,102,99,101,1000\n2024-12-02,101,103,100,102,1000\n2024-12-03,102,104,101,103,1000\n"
    days = [
        {"date": "2024-11-29", "kind": "OPEN", "open_utc": "2024-11-29T14:30:00Z", "close_utc": "2024-11-29T18:00:00Z", "early_close": True},
        {"date": "2024-11-30", "kind": "CLOSED", "reason": "WEEKEND"},
        {"date": "2024-12-01", "kind": "CLOSED", "reason": "WEEKEND"},
        {"date": "2024-12-02", "kind": "OPEN", "open_utc": "2024-12-02T14:30:00Z", "close_utc": "2024-12-02T21:00:00Z", "early_close": False},
        {"date": "2024-12-03", "kind": "OPEN", "open_utc": "2024-12-03T14:30:00Z", "close_utc": "2024-12-03T21:00:00Z", "early_close": False},
    ]
    def source(label, content):
        return {"name": "Synthetic " + label, "reference": "urn:synthetic:equity-cli:" + label,
                "retrieved_at": "2024-12-04T00:00:00Z", "raw_base64": base64.b64encode(content).decode("ascii")}
    manifest = {
        "schema_version": "us-equity-daily-import-v1",
        "security": {"security_id": "SYNTHETIC:CLI:TEST", "symbol": "TEST", "exchange": "XNYS", "currency": "USD", "instrument_type": "COMMON_STOCK"},
        "identity": {"stable_within_coverage": True, "valid_from": "2024-11-29", "valid_through": "2024-12-03", "selection_basis": "Fictional fixed fixture only", "source": source("identity", b"Fictional stable TEST")},
        "calendar": {"timezone": "America/New_York", "coverage_start": "2024-11-29", "coverage_end": "2024-12-03", "source": source("calendar", json.dumps(days).encode()), "days": days},
        "corporate_actions": {"coverage_start": "2024-11-29", "coverage_end": "2024-12-03", "coverage_status": "DECLARED_COMPLETE", "source": source("actions", b"Fictional empty action list"), "actions": []},
        "price_source": source("prices", raw), "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares", "bar_timestamp_semantics": "SESSION_DATE", "completed_bars_only": True,
        "as_of": "2024-12-03T21:01:00Z", "retrieved_at": "2024-12-04T00:00:00Z", "bar_availability_lag_seconds": 60, "evidence_kind": "SYNTHETIC_TEST",
    }
    return build_equity_snapshot(raw, manifest)


def event_fixture(public_at, *, event_id="SYNTHETIC:CLI:EARNINGS", previous=None):
    item = {
        "event_id": event_id, "security_id": "SYNTHETIC:CLI:TEST", "event_kind": "EARNINGS",
        "version": 1 if previous is None else previous["version"] + 1,
        "prior_version_hash": None if previous is None else previous["event_hash"],
        "source": {"url": "https://example.invalid/ir/cli-test", "kind": "SYNTHETIC_FIXTURE", "document_type": "PRESS_RELEASE", "disclosure_items": [], "official_source_status": "DECLARED_UNVERIFIED"},
        "first_public_at": public_at if previous is None else previous["first_public_at"], "version_public_at": public_at,
        "publication_clock": {"status": "ATTESTED", "verification_method": "DETERMINISTIC_SYNTHETIC_FIXTURE", "evidence": "Fictional test clocks, not a real publisher attestation."},
        "retrieved_at": "2024-12-04T00:00:00Z",
        "timing": {"mode": "HISTORICAL_RECONSTRUCTION", "received_at": None, "extraction_completed_at": "2024-12-04T00:01:00Z", "collection_delay_seconds": 1, "processing_delay_seconds": 1},
        "scheduled_release_at": None, "facts": [], "uncertainties": ["Synthetic fixture with no financial interpretation."],
    }
    return build_equity_event(b"Fictional disclosure published at " + public_at.encode("ascii"), item)


class EquityCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.snapshot = save_equity_snapshot(snapshot_fixture(), self.root / "snapshots")
        self.events = self.root / "events"

    def align(self, events, *, as_of="2024-12-03T21:01:00Z"):
        for event in events:
            save_equity_event(event, self.events)
        stdout = io.StringIO()
        # Audit hooks cannot be removed. Avoid changing other portable tests'
        # process policy; this test performs only explicit temporary local I/O.
        with patch("hakimi_research.equity_cli.sys.addaudithook") as audit, redirect_stdout(stdout):
            main(["event-eligibility", "--snapshot", str(self.snapshot), "--event-dir", str(self.events),
                  "--as-of", as_of, "--output-dir", str(self.root / "outputs")])
        audit.assert_called_once()
        result = json.loads(stdout.getvalue())
        stored = read_document(result["report_path"])
        self.assertEqual(stored, {key: value for key, value in result.items() if key != "report_path"})
        self.assertFalse(result["execution_permission"]["order_allowed"])
        return result

    def test_event_before_calendar_coverage_does_not_shift_to_first_covered_day(self):
        event = event_fixture("2024-11-25T18:05:00Z")
        result = self.align([event])
        self.assertEqual(result["selected_event_hashes"], [event["event_hash"]])
        row = result["rows"][0]
        self.assertEqual(row["status"], "NOT_READY")
        self.assertEqual(row["reason"], "EVENT_AVAILABILITY_PRECEDES_CALENDAR_COVERAGE")
        self.assertIsNone(row["observation_session"])
        self.assertIsNone(row["confirmation_available_at"])
        self.assertIsNone(row["entry_session"])
        self.assertIsNone(row["earliest_entry_at"])

    def test_coverage_boundary_uses_new_york_date_not_utc_date(self):
        # The UTC date is Nov 29, but New York is still the uncovered Nov 28.
        row = self.align([event_fixture("2024-11-29T03:55:00Z")])["rows"][0]
        self.assertEqual(row["reason"], "EVENT_AVAILABILITY_PRECEDES_CALENDAR_COVERAGE")
        self.assertIsNone(row["earliest_entry_at"])

    def test_first_covered_day_premarket_can_observe_that_full_session(self):
        row = self.align([event_fixture("2024-11-29T13:00:00Z")])["rows"][0]
        self.assertEqual(row["status"], "READY")
        self.assertEqual(row["observation_session"]["date"], "2024-11-29")
        self.assertEqual(row["confirmation_available_at"], "2024-11-29T18:01:00Z")
        self.assertEqual(row["earliest_entry_at"], "2024-12-02T14:30:00Z")

    def test_covered_weekend_uses_monday_then_tuesday_without_fake_bars(self):
        row = self.align([event_fixture("2024-11-30T12:00:00Z")])["rows"][0]
        self.assertEqual(row["status"], "READY")
        self.assertEqual(row["observation_session"]["date"], "2024-12-02")
        self.assertEqual(row["confirmation_available_at"], "2024-12-02T21:01:00Z")
        self.assertEqual(row["earliest_entry_at"], "2024-12-03T14:30:00Z")

    def test_future_event_is_excluded_before_assumed_availability(self):
        event = event_fixture("2024-11-29T18:05:00Z")
        result = self.align([event], as_of="2024-11-29T18:05:01Z")
        self.assertEqual(result["selected_event_hashes"], [])
        self.assertEqual(result["rows"], [])

    def test_future_revision_cannot_replace_the_version_known_asof(self):
        first = event_fixture("2024-11-29T13:00:00Z")
        second = event_fixture("2024-12-02T13:00:00Z", previous=first)
        result = self.align([first, second], as_of="2024-11-30T12:00:00Z")
        self.assertEqual(result["selected_event_hashes"], [first["event_hash"]])
        self.assertEqual(result["rows"][0]["event_hash"], first["event_hash"])
        self.assertEqual(result["rows"][0]["observation_session"]["date"], "2024-11-29")


if __name__ == "__main__":
    unittest.main()
