"""Offline stock-session and action-admission checks; prices are fictional."""
import base64
import copy
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import tempfile
import unittest
from zoneinfo import ZoneInfo

from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_dataset import (
    build_equity_snapshot, load_equity_snapshot, save_equity_snapshot, verify_equity_snapshot,
)


def fixture():
    """Portable in-memory fixture; no source checkout or examples directory."""
    first, last = date(2024, 10, 21), date(2024, 12, 3)
    days, dates = [], []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day.weekday() >= 5 or day == date(2024, 11, 28):
            days.append({"date": day.isoformat(), "kind": "CLOSED",
                         "reason": "WEEKEND" if day.weekday() >= 5 else "HOLIDAY"})
        else:
            early = day == date(2024, 11, 29)
            def stamp(hour, minute=0):
                value = datetime.combine(day, time(hour, minute), ZoneInfo("America/New_York"))
                return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            days.append({"date": day.isoformat(), "kind": "OPEN", "open_utc": stamp(9, 30),
                         "close_utc": stamp(13 if early else 16), "early_close": early})
            dates.append(day.isoformat())
    rows = ["session_date,open,high,low,close,volume"]
    for index, day in enumerate(dates):
        opening = 100 + index * 0.25
        rows.append(f"{day},{opening:.2f},{opening + 1.5:.2f},{opening - 1:.2f},{opening + 0.5:.2f},{10000 + index * 100}")
    raw = ("\n".join(rows) + "\n").encode()
    def source(name, content):
        return {"name": "SYNTHETIC_" + name, "reference": "urn:synthetic:equity-dataset:" + name,
                "retrieved_at": "2024-12-04T00:00:00Z", "raw_base64": base64.b64encode(content).decode()}
    manifest = {
        "schema_version": "us-equity-daily-import-v1",
        "security": {"security_id": "SYNTHETIC:DATASET:TEST", "symbol": "TEST", "exchange": "XNAS",
                     "currency": "USD", "instrument_type": "COMMON_STOCK"},
        "identity": {"stable_within_coverage": True, "valid_from": first.isoformat(), "valid_through": last.isoformat(),
                     "selection_basis": "Fictional software fixture, not a real security or universe",
                     "source": source("identity", b"Fictional stable TEST identity")},
        "calendar": {"timezone": "America/New_York", "coverage_start": first.isoformat(),
                     "coverage_end": last.isoformat(), "source": source("calendar", json.dumps(days).encode()), "days": days},
        "corporate_actions": {"coverage_start": first.isoformat(), "coverage_end": last.isoformat(),
                              "coverage_status": "DECLARED_COMPLETE", "source": source("actions", b"Synthetic complete empty action list"),
                              "actions": []},
        "price_source": source("price", raw), "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares",
        "bar_timestamp_semantics": "SESSION_DATE", "completed_bars_only": True,
        "as_of": "2024-12-03T21:01:00Z", "retrieved_at": "2024-12-04T00:00:00Z",
        "bar_availability_lag_seconds": 60, "evidence_kind": "SYNTHETIC_TEST",
    }
    return raw, manifest


def with_csv(manifest, raw):
    manifest["price_source"]["raw_base64"] = base64.b64encode(raw).decode("ascii")
    return manifest


def reseal(document):
    document["snapshot_id"] = digest({key: value for key, value in document.items() if key != "snapshot_id"})
    return document


class EquityDatasetTests(unittest.TestCase):
    def test_daily_rows_follow_real_session_shapes_without_weekend_padding(self):
        raw, manifest = fixture()
        snapshot = build_equity_snapshot(raw, manifest)
        doc = verify_equity_snapshot(snapshot.document)
        self.assertEqual(doc["quality"]["accepted_rows"], 31)
        self.assertEqual(len(doc["calendar"]["days"]), 44)
        self.assertTrue(doc["research_admission"]["allowed"])
        self.assertTrue(doc["research_admission"]["synthetic_only"])
        self.assertFalse(doc["research_admission"]["source_truth_verified"])
        self.assertEqual(doc["price_source"]["truth_status"], "DECLARED_SOURCE_NOT_AUTHENTICATED")
        sessions = {row["date"]: row for row in doc["sessions"]}
        self.assertEqual(sessions["2024-11-01"]["open_utc"], "2024-11-01T13:30:00Z")
        self.assertEqual(sessions["2024-11-04"]["open_utc"], "2024-11-04T14:30:00Z")
        self.assertEqual(sessions["2024-11-29"]["close_utc"], "2024-11-29T18:00:00Z")
        self.assertNotIn("2024-11-28", sessions)
        self.assertNotIn("2024-11-30", sessions)
        self.assertEqual([stamp.isoformat().replace("+00:00", "Z") for stamp in snapshot.frame().index],
                         [row["open_utc"] for row in doc["sessions"]])
        self.assertEqual(doc["candles"][0][1:], [100.0, 101.5, 99.0, 100.5, 10000.0])

    def test_spring_dst_transition_uses_next_declared_session(self):
        _, manifest = fixture()
        first, last = date(2024, 3, 8), date(2024, 3, 11)
        days = []
        for offset in range(4):
            day = first + timedelta(days=offset)
            if day.weekday() >= 5:
                days.append({"date": day.isoformat(), "kind": "CLOSED", "reason": "WEEKEND"})
            else:
                def stamp(hour, minute):
                    value = datetime.combine(day, time(hour, minute), ZoneInfo("America/New_York"))
                    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                days.append({"date": day.isoformat(), "kind": "OPEN", "open_utc": stamp(9, 30),
                             "close_utc": stamp(16, 0), "early_close": False})
        manifest["calendar"].update(coverage_start=first.isoformat(), coverage_end=last.isoformat(), days=days)
        manifest["corporate_actions"].update(coverage_start=first.isoformat(), coverage_end=last.isoformat())
        manifest["identity"].update(valid_from=first.isoformat(), valid_through=last.isoformat())
        raw = b"session_date,open,high,low,close,volume\n2024-03-08,100,101,99,100,10\n2024-03-11,100,101,99,100,10\n"
        result = build_equity_snapshot(raw, with_csv(manifest, raw)).document
        self.assertEqual([s["open_utc"] for s in result["sessions"]],
                         ["2024-03-08T14:30:00Z", "2024-03-11T13:30:00Z"])

    def test_missing_actual_session_and_offhours_row_are_rejected(self):
        raw, manifest = fixture()
        lines = raw.splitlines()
        for edited in [b"\n".join(lines[:-1]) + b"\n",
                       raw + b"2024-12-03,100,101,99,100,100\n"]:
            with self.subTest(edited=edited[-45:]), self.assertRaisesRegex(ValueError, "session_count"):
                build_equity_snapshot(edited, with_csv(copy.deepcopy(manifest), edited))
        for altered_date in [b"2024-10-20", b"2024-10-21T13:30:00Z", b"2024-10-22"]:
            edited = raw.replace(b"2024-10-21", altered_date, 1)
            with self.subTest(altered_date=altered_date), self.assertRaisesRegex(ValueError, "session_missing_extra_duplicate_or_out_of_order"):
                build_equity_snapshot(edited, with_csv(copy.deepcopy(manifest), edited))

    def test_calendar_requires_every_closed_date_and_refuses_weekend_sessions(self):
        raw, manifest = fixture()
        manifest["calendar"]["days"].pop(5)
        with self.assertRaisesRegex(ValueError, "every_calendar_date"):
            build_equity_snapshot(raw, manifest)
        raw, manifest = fixture()
        day = manifest["calendar"]["days"][5]
        day.update(kind="OPEN", open_utc="2024-10-26T13:30:00Z", close_utc="2024-10-26T20:00:00Z", early_close=False)
        day.pop("reason")
        with self.assertRaisesRegex(ValueError, "regular_session_day"):
            build_equity_snapshot(raw, manifest)

    def test_calendar_does_not_accept_silent_dst_or_early_close_relabel(self):
        for day, field, value in [("2024-11-04", "open_utc", "2024-11-04T13:30:00Z"),
                                  ("2024-11-29", "early_close", False),
                                  ("2024-11-29", "close_utc", "2024-11-29T21:00:00Z")]:
            raw, manifest = fixture()
            next(row for row in manifest["calendar"]["days"] if row["date"] == day)[field] = value
            with self.subTest(day=day, field=field), self.assertRaisesRegex(ValueError, "session_time_or_dst"):
                build_equity_snapshot(raw, manifest)

    def test_unclosed_or_not_yet_available_bar_is_rejected(self):
        for cutoff in ["2024-12-03T20:59:59Z", "2024-12-03T21:00:59Z"]:
            raw, manifest = fixture()
            manifest["as_of"] = cutoff
            with self.subTest(cutoff=cutoff), self.assertRaisesRegex(ValueError, "not_complete_and_available"):
                build_equity_snapshot(raw, manifest)
        raw, manifest = fixture()
        manifest["as_of"] = "2024-12-05T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "as_of_after_retrieval"):
            build_equity_snapshot(raw, manifest)

    def test_explicit_positive_latency_and_completion_declaration_required(self):
        for lag in [0, -1, True, 60.0, "60", 604801]:
            raw, manifest = fixture()
            manifest["bar_availability_lag_seconds"] = lag
            with self.subTest(lag=lag), self.assertRaisesRegex(ValueError, "explicit_bar_availability_lag"):
                build_equity_snapshot(raw, manifest)
        raw, manifest = fixture()
        manifest["completed_bars_only"] = 1
        with self.assertRaisesRegex(ValueError, "completed_bars_only"):
            build_equity_snapshot(raw, manifest)

    def test_mixed_adjustment_or_volume_basis_is_rejected(self):
        for field, value in [("price_basis", "SPLIT_ADJUSTED"), ("price_basis", "TOTAL_RETURN"),
                             ("volume_unit", "quote_currency"), ("bar_timestamp_semantics", "UTC_MIDNIGHT")]:
            raw, manifest = fixture()
            manifest[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                build_equity_snapshot(raw, manifest)
        raw, manifest = fixture()
        raw = raw.replace(b"session_date,open,high,low,close,volume", b"session_date,open,high,low,adj_close,volume")
        with self.assertRaisesRegex(ValueError, "exact_daily_header"):
            build_equity_snapshot(raw, with_csv(manifest, raw))

    def test_empty_actions_without_source_or_coverage_cannot_be_admitted(self):
        raw, manifest = fixture()
        manifest["corporate_actions"]["coverage_status"] = "UNKNOWN"
        result = build_equity_snapshot(raw, manifest).document
        self.assertFalse(result["research_admission"]["allowed"])
        self.assertIn("CORPORATE_ACTION_COVERAGE_UNVERIFIED_OR_INCOMPLETE", result["research_admission"]["block_reasons"])
        manifest["corporate_actions"]["coverage_status"] = "DECLARED_COMPLETE"
        manifest["corporate_actions"]["coverage_start"] = "2024-10-22"
        self.assertFalse(build_equity_snapshot(raw, manifest).document["research_admission"]["allowed"])
        manifest["corporate_actions"].pop("source")
        with self.assertRaisesRegex(ValueError, "corporate_actions_fields"):
            build_equity_snapshot(raw, manifest)

    def test_split_dividend_delisting_and_unknown_actions_are_preserved_and_blocked(self):
        for action_type in ["SPLIT", "DIVIDEND", "DELISTING", "SUSPENSION", "SPINOFF", "UNKNOWN"]:
            raw, manifest = fixture()
            action = {"action_id": "event-1", "security_id": manifest["security"]["security_id"],
                      "action_type": action_type, "effective_date": "2024-11-05",
                      "source_reference": "urn:synthetic:event-1", "details": {"declaration": "fictional event"}}
            manifest["corporate_actions"]["actions"] = [action]
            result = build_equity_snapshot(raw, manifest).document
            with self.subTest(action_type=action_type):
                self.assertEqual(result["corporate_actions"]["actions"], [action])
                self.assertEqual(result["research_admission"]["block_reasons"],
                                 ["CORPORATE_ACTION_ACCOUNTING_NOT_IMPLEMENTED:event-1"])
                self.assertFalse(result["research_admission"]["allowed"])
                self.assertEqual(verify_equity_snapshot(result), result)

    def test_unstable_identity_and_incomplete_lifetime_block_research(self):
        raw, manifest = fixture()
        manifest["identity"].update(stable_within_coverage=False, valid_through="2024-11-15")
        result = build_equity_snapshot(raw, manifest).document
        self.assertFalse(result["research_admission"]["allowed"])
        self.assertEqual(result["research_admission"]["block_reasons"],
                         ["SECURITY_IDENTITY_NOT_STABLE", "SECURITY_IDENTITY_COVERAGE_INCOMPLETE"])
        manifest["security"]["instrument_type"] = "LEVERAGED_ETF"
        with self.assertRaisesRegex(ValueError, "common_stock_only"):
            build_equity_snapshot(raw, manifest)

    def test_source_evidence_is_required_and_price_receipt_binds_actual_csv(self):
        for source_section in ["calendar", "corporate_actions", "identity"]:
            raw, manifest = fixture()
            manifest[source_section]["source"]["raw_base64"] = ""
            with self.subTest(source_section=source_section), self.assertRaisesRegex(ValueError, "source_size_invalid"):
                build_equity_snapshot(raw, manifest)
        raw, manifest = fixture()
        manifest["price_source"]["raw_base64"] = base64.b64encode(b"unrelated receipt").decode()
        with self.assertRaisesRegex(ValueError, "price_source_bytes_mismatch"):
            build_equity_snapshot(raw, manifest)

    def test_whitespace_changes_identity_while_retaining_normalized_values(self):
        raw, manifest = fixture()
        canonical = canonical_bytes(manifest)
        pretty = json.dumps(manifest, indent=2).encode()
        original = build_equity_snapshot(raw, canonical)
        revised = build_equity_snapshot(raw, pretty)
        self.assertEqual(original.document["data_hash"], revised.document["data_hash"])
        self.assertNotEqual(original.snapshot_id, revised.snapshot_id)
        self.assertEqual(base64.b64decode(revised.document["raw_input"]["manifest_base64"]), pretty)
        self.assertEqual(revised.document["raw_input"]["manifest_sha256"], hashlib.sha256(pretty).hexdigest())
        self.assertEqual(revised.document["raw_input"]["manifest_encoding"], "ORIGINAL_JSON_BYTES")

    def test_resealed_normalized_changes_are_rejected_by_raw_reconstruction(self):
        raw, manifest = fixture()
        original = build_equity_snapshot(raw, manifest).document
        for field in ["candles", "security", "sessions", "research_admission", "order_allowed"]:
            changed = copy.deepcopy(original)
            if field == "candles":
                changed[field][0][4] += 0.25
                changed["data_hash"] = digest(changed[field])
            elif field == "security":
                changed[field]["symbol"] = "OTHER"
            elif field == "sessions":
                changed[field][0]["close_utc"] = "2024-10-21T21:00:00Z"
            elif field == "research_admission":
                changed[field]["source_truth_verified"] = True
            else:
                changed[field] = True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "content_or_receipt_mismatch"):
                verify_equity_snapshot(reseal(changed))

    def test_manifest_duplicate_keys_and_non_native_values_are_rejected(self):
        raw, manifest = fixture()
        duplicate = canonical_bytes(manifest)[:-1] + b',"schema_version":"us-equity-daily-import-v1"}'
        with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
            build_equity_snapshot(raw, duplicate)
        manifest["calendar"]["days"] = tuple(manifest["calendar"]["days"])
        with self.assertRaisesRegex(ValueError, "exact_finite_json"):
            build_equity_snapshot(raw, manifest)

    def test_saved_snapshot_replays_original_bytes_and_cannot_be_overwritten(self):
        raw, manifest = fixture()
        snapshot = build_equity_snapshot(raw, manifest)
        manifest["security"]["symbol"] = "MUTATED"
        self.assertEqual(snapshot.document["security"]["symbol"], "TEST")
        with tempfile.TemporaryDirectory() as directory:
            path = save_equity_snapshot(snapshot, directory)
            before = path.read_bytes()
            self.assertEqual(save_equity_snapshot(snapshot, directory), path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(load_equity_snapshot(path).document, snapshot.document)
            self.assertEqual(load_equity_snapshot(path).frame().to_dict(), snapshot.frame().to_dict())
            path.write_bytes(b"different prior evidence")
            with self.assertRaises(FileExistsError):
                save_equity_snapshot(snapshot, directory)


if __name__ == "__main__":
    unittest.main()
