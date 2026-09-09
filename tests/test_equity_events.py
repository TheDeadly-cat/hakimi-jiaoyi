"""Synthetic PIT and raw-source boundaries; no network, account or order calls."""
from __future__ import annotations

import base64
import copy
from pathlib import Path
import tempfile
import unittest

from hakimi_research.documents import digest
from hakimi_research.equity_events import (
    build_equity_event, event_session_eligibility, save_equity_event,
    select_event_versions, verify_equity_event,
)


RAW = (
    "SYNTHETIC fixture.\r\n"
    "FY2024 Q3 revenue was USD 120 million on a GAAP basis.\r\n"
    "EPS was USD 1.25. Guidance is uncertain.\r\n"
).encode("utf-8")


def metadata():
    return {
        "event_id": "TEST:EARNINGS:2024Q3", "security_id": "SYNTHETIC:COMMON:TEST:2024",
        "event_kind": "EARNINGS", "version": 1, "prior_version_hash": None,
        "source": {"url": "https://example.invalid/ir/q3", "kind": "SYNTHETIC_FIXTURE",
                   "document_type": "PRESS_RELEASE", "disclosure_items": [],
                   "official_source_status": "DECLARED_UNVERIFIED"},
        "first_public_at": "2024-11-29T18:05:00Z", "version_public_at": "2024-11-29T18:05:00Z",
        "publication_clock": {"status": "ATTESTED", "verification_method": "SYNTHETIC_FIXTURE",
                              "evidence": "Test clock; not a real authenticated source."},
        "retrieved_at": "2026-09-09T00:00:00Z",
        "timing": {"mode": "HISTORICAL_RECONSTRUCTION", "received_at": None,
                   "extraction_completed_at": "2026-09-09T00:01:00Z",
                   "collection_delay_seconds": 60, "processing_delay_seconds": 60},
        "scheduled_release_at": None,
        "facts": [{"name": "revenue", "status": "KNOWN", "value": "120", "value_text": "120",
                   "scale": "1000000", "currency": "USD", "unit": "CURRENCY",
                   "fiscal_period": "FY2024-Q3", "basis": "GAAP", "reason": None,
                   "evidence": [{"quote": "FY2024 Q3 revenue was USD 120 million on a GAAP basis."}]},
                  {"name": "consensus_eps", "status": "MISSING", "value": None,
                   "value_text": None, "scale": None, "currency": None, "unit": None,
                   "fiscal_period": None, "basis": None, "evidence": [], "reason": "No estimate snapshot."}],
        "uncertainties": ["Synthetic fixture, no real-world timestamp attestation."],
    }


def sessions():
    return [
        {"date": "2024-11-29", "open_utc": "2024-11-29T14:30:00Z", "close_utc": "2024-11-29T18:00:00Z", "early_close": True},
        {"date": "2024-12-02", "open_utc": "2024-12-02T14:30:00Z", "close_utc": "2024-12-02T21:00:00Z", "early_close": False},
        {"date": "2024-12-03", "open_utc": "2024-12-03T14:30:00Z", "close_utc": "2024-12-03T21:00:00Z", "early_close": False},
        {"date": "2024-12-04", "open_utc": "2024-12-04T14:30:00Z", "close_utc": "2024-12-04T21:00:00Z", "early_close": False},
    ]


def observed(public, available):
    item = metadata()
    item["first_public_at"] = item["version_public_at"] = public
    item["retrieved_at"] = public
    item["timing"].update({"mode": "OBSERVED", "received_at": public,
                           "extraction_completed_at": available,
                           "collection_delay_seconds": None, "processing_delay_seconds": None})
    return build_equity_event(RAW, item)


def revision(first):
    item = metadata()
    item.update({"version": 2, "prior_version_hash": first["event_hash"],
                 "version_public_at": "2024-12-02T18:05:00Z"})
    item["facts"][0].update({"value": "110", "value_text": "110",
                              "evidence": [{"quote": "FY2024 Q3 revenue was USD 110 million on a GAAP basis."}]})
    return build_equity_event(RAW.replace(b"120", b"110"), item)


class EquityEventTests(unittest.TestCase):
    def test_raw_bytes_roundtrip_and_assumed_clock_remains_separate(self):
        source = metadata()
        event = build_equity_event(RAW, source)
        self.assertEqual(base64.b64decode(event["raw"]["content_base64"]), RAW)
        self.assertEqual(verify_equity_event(event), event)
        self.assertEqual(event["availability"]["assumed_available_at"], "2024-11-29T18:07:00Z")
        self.assertIsNone(event["availability"]["observed_available_at"])
        self.assertEqual(event["retrieved_at"], "2026-09-09T00:00:00Z")
        self.assertIsNone(event["timing"]["received_at"])
        self.assertFalse(event["authority"]["publisher_authenticated"])
        self.assertFalse(event["authority"]["order_allowed"])
        source["facts"][0]["value"] = "999"
        self.assertEqual(event["facts"][0]["value"], "120")

    def test_historical_requires_two_positive_delays_and_no_fake_receipt(self):
        for key, value in (("collection_delay_seconds", 0), ("processing_delay_seconds", -1),
                           ("processing_delay_seconds", True), ("received_at", "2024-11-29T18:06:00Z")):
            with self.subTest(key=key, value=value):
                item = metadata()
                item["timing"][key] = value
                with self.assertRaises(ValueError):
                    build_equity_event(RAW, item)

    def test_observed_availability_and_today_retrieval_cannot_be_historical_receipt(self):
        event = observed("2024-11-29T18:05:00Z", "2024-11-29T18:07:00Z")
        self.assertEqual(event["availability"]["available_at_kind"], "OBSERVED")
        self.assertEqual(event["availability"]["observed_available_at"], "2024-11-29T18:07:00Z")
        item = {key: value for key, value in event.items() if key in metadata()}
        item["retrieved_at"] = "2026-09-09T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "extraction_before_retrieval"):
            build_equity_event(RAW, item)

    def test_unknown_publication_is_stored_but_not_admitted(self):
        item = metadata()
        item.update({"first_public_at": None, "version_public_at": None,
                     "publication_clock": {"status": "UNKNOWN", "verification_method": None, "evidence": None}})
        event = build_equity_event(RAW, item)
        self.assertIsNone(event["availability"]["available_at"])
        self.assertEqual(select_event_versions([event], "2026-09-09T12:00:00Z"), [])
        self.assertEqual(event_session_eligibility(event, sessions(), 60)["reason"], "PUBLICATION_CLOCK_UNKNOWN")

    def test_imprecise_or_unzoned_publication_is_rejected(self):
        for stamp in ("2024-11-29", "2024-11-29T18:05", "2024-11-29T18:05:00", "2024-11-29T13:05:00-05:00"):
            with self.subTest(stamp=stamp):
                item = metadata()
                item["first_public_at"] = item["version_public_at"] = stamp
                with self.assertRaises(ValueError):
                    build_equity_event(RAW, item)

    def test_asof_boundaries_and_revised_numbers_do_not_flow_back(self):
        first = build_equity_event(RAW, metadata())
        second = revision(first)
        self.assertEqual(select_event_versions([second, first], "2024-11-29T18:06:59Z"), [])
        self.assertEqual(select_event_versions([second, first], "2024-11-29T18:07:00Z"), [first])
        self.assertEqual(select_event_versions([first, second], "2024-12-02T18:06:59Z"), [first])
        self.assertEqual(select_event_versions([first, second], "2024-12-02T18:07:00Z"), [second])
        self.assertEqual(first["facts"][0]["value"], "120")

    def test_revision_cannot_borrow_original_publication_or_skip_lineage(self):
        first = build_equity_event(RAW, metadata())
        second = revision(first)
        item = metadata()
        item.update({"version": 2, "prior_version_hash": first["event_hash"]})
        with self.assertRaisesRegex(ValueError, "revision_cannot_borrow"):
            build_equity_event(RAW, item)
        with self.assertRaisesRegex(ValueError, "lineage_incomplete"):
            select_event_versions([second], "2026-09-09T12:00:00Z")
        tampered = copy.deepcopy(second)
        tampered["prior_version_hash"] = "a" * 64
        tampered["event_hash"] = digest({key: value for key, value in tampered.items() if key != "event_hash"})
        with self.assertRaisesRegex(ValueError, "lineage_hash_mismatch"):
            select_event_versions([first, tampered], "2026-09-09T12:00:00Z")

    def test_ledger_is_append_only_idempotent_and_conflict_fails(self):
        first = build_equity_event(RAW, metadata())
        second = revision(first)
        with tempfile.TemporaryDirectory() as directory:
            one = save_equity_event(first, directory)
            old_bytes = one.read_bytes()
            two = save_equity_event(second, directory)
            self.assertNotEqual(one, two)
            self.assertEqual(save_equity_event(first, directory), one)
            self.assertEqual(one.read_bytes(), old_bytes)
            conflicting = metadata()
            conflicting["uncertainties"].append("Different claim at the same version.")
            with self.assertRaisesRegex(ValueError, "duplicate_version_conflict"):
                save_equity_event(build_equity_event(RAW, conflicting), directory)
            self.assertEqual(len(list(Path(directory).glob("event_*.json"))), 2)
            self.assertEqual(one.read_bytes(), old_bytes)

    def test_invalid_existing_ledger_cannot_be_masked_by_save(self):
        event = build_equity_event(RAW, metadata())
        with tempfile.TemporaryDirectory() as directory:
            path = save_equity_event(event, directory)
            path.write_bytes(b"{corrupt existing receipt")
            with self.assertRaises(ValueError):
                save_equity_event(event, directory)
            self.assertEqual(path.read_bytes(), b"{corrupt existing receipt")

    def test_exact_quotes_offsets_and_numeric_evidence(self):
        text = RAW.decode("utf-8")
        item = metadata()
        quote = item["facts"][0]["evidence"][0]["quote"]
        start = text.index(quote)
        item["facts"][0]["evidence"] = [{"start": start, "end": start + len(quote), "quote": quote}]
        verify_equity_event(build_equity_event(RAW, item))
        item["facts"][0]["evidence"][0]["end"] -= 1
        with self.assertRaisesRegex(ValueError, "offset_mismatch"):
            build_equity_event(RAW, item)
        item = metadata()
        item["facts"][0]["evidence"] = [{"quote": "This invented sentence is not in the source."}]
        with self.assertRaisesRegex(ValueError, "quote_mismatch"):
            build_equity_event(RAW, item)
        for number in ("20", "125"):
            item = metadata()
            item["facts"][0].update({"value": number, "value_text": number})
            with self.assertRaisesRegex(ValueError, "source_token_absent"):
                build_equity_event(RAW, item)

    def test_consensus_missing_uncertainty_and_no_numeric_coercion(self):
        item = metadata()
        event = build_equity_event(RAW, item)
        self.assertIsNone(event["facts"][1]["value"])
        consensus = copy.deepcopy(item["facts"][0])
        consensus["name"] = "consensus_eps"
        item["facts"][1] = consensus
        with self.assertRaisesRegex(ValueError, "consensus_not_supported"):
            build_equity_event(RAW, item)
        item = metadata()
        uncertain = copy.deepcopy(item["facts"][1])
        uncertain.update({"name": "guidance", "status": "UNCERTAIN", "reason": "Unquantified.",
                          "evidence": [{"quote": "Guidance is uncertain."}]})
        item["facts"].append(uncertain)
        verify_equity_event(build_equity_event(RAW, item))
        item["facts"][0]["value"] = 120.0
        with self.assertRaisesRegex(ValueError, "no_floats"):
            build_equity_event(RAW, item)

    def test_forged_computed_availability_or_hash_is_rejected(self):
        event = build_equity_event(RAW, metadata())
        event["availability"]["available_at"] = "2024-11-29T18:05:00Z"
        event["event_hash"] = digest({key: value for key, value in event.items() if key != "event_hash"})
        with self.assertRaisesRegex(ValueError, "document_binding_mismatch"):
            verify_equity_event(event)

    def test_8k_material_disclosure_is_not_automatically_earnings(self):
        item = metadata()
        item["source"].update({"document_type": "8-K", "disclosure_items": ["1.01"]})
        item["event_kind"] = "MATERIAL_COMPANY"
        self.assertEqual(build_equity_event(RAW, item)["event_kind"], "MATERIAL_COMPANY")
        item["event_kind"] = "EARNINGS"
        with self.assertRaisesRegex(ValueError, "8k_earnings_requires_results_item"):
            build_equity_event(RAW, item)

    def test_preannounced_schedule_is_separate_and_point_in_time(self):
        item = metadata()
        item["event_id"] = "TEST:EARNINGS:SCHEDULE"
        item["event_kind"] = "EARNINGS_SCHEDULE"
        item["scheduled_release_at"] = "2024-12-02T21:05:00Z"
        event = build_equity_event(RAW, item)
        self.assertEqual(select_event_versions([event], "2024-11-29T18:06:00Z"), [])
        self.assertEqual(select_event_versions([event], "2024-11-29T18:07:00Z"), [event])
        self.assertEqual(event_session_eligibility(event, sessions(), 60)["reason"], "SCHEDULE_IS_RISK_CALENDAR_NOT_RELEASE_CONTENT")
        item["scheduled_release_at"] = None
        with self.assertRaises(ValueError):
            build_equity_event(RAW, item)

    def test_friday_after_early_close_uses_monday_then_tuesday(self):
        event = build_equity_event(RAW, metadata())
        result = event_session_eligibility(event, sessions(), 60)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["observation_session"]["date"], "2024-12-02")
        self.assertEqual(result["confirmation_available_at"], "2024-12-02T21:01:00Z")
        self.assertEqual(result["earliest_entry_at"], "2024-12-03T14:30:00Z")
        self.assertFalse(result["order_allowed"])

    def test_preopen_or_exact_open_uses_full_session_but_intraday_cannot(self):
        for available, expected in (("2024-11-29T14:29:59Z", "2024-11-29"),
                                    ("2024-11-29T14:30:00Z", "2024-11-29"),
                                    ("2024-11-29T14:30:00.000001Z", "2024-12-02")):
            with self.subTest(available=available):
                event = observed("2024-11-29T14:00:00Z", available)
                result = event_session_eligibility(event, sessions(), 60)
                self.assertEqual(result["observation_session"]["date"], expected)
                if expected == "2024-11-29":
                    self.assertEqual(result["confirmation_available_at"], "2024-11-29T18:01:00Z")

    def test_weekend_missing_next_session_and_latency_cannot_reuse_open(self):
        weekend = observed("2024-11-30T12:00:00Z", "2024-11-30T12:02:00Z")
        result = event_session_eligibility(weekend, sessions()[:2], 60)
        self.assertEqual(result["status"], "NOT_READY")
        self.assertIsNone(result["earliest_entry_at"])
        # Monday 21:00 plus 17h30m reaches Tuesday open exactly, so skip it.
        result = event_session_eligibility(weekend, sessions(), 17 * 3600 + 30 * 60)
        self.assertEqual(result["earliest_entry_at"], "2024-12-04T14:30:00Z")
        result = event_session_eligibility(weekend, sessions()[:1], 60)
        self.assertEqual(result["reason"], "FULL_POST_AVAILABILITY_SESSION_NOT_IN_CALENDAR")

    def test_sessions_require_order_and_never_synthesize_missing_days(self):
        event = build_equity_event(RAW, metadata())
        for bad in (list(reversed(sessions())), sessions() + [sessions()[-1]]):
            with self.assertRaisesRegex(ValueError, "session_order_or_window"):
                event_session_eligibility(event, bad, 60)
        self.assertEqual(event_session_eligibility(event, [], 60)["status"], "NOT_READY")
        with self.assertRaisesRegex(ValueError, "delay_seconds"):
            event_session_eligibility(event, sessions(), True)

if __name__ == "__main__":
    unittest.main()
