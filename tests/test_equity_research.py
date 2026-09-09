"""Portable economic/session checks with in-memory fictional stock inputs.

No provider, repository examples, broker, live account or external data is used.
"""
import base64
import copy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

from hakimi_research.benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from hakimi_research.documents import digest
from hakimi_research.equity_dataset import build_equity_snapshot
from hakimi_research.equity_research import (
    EquityExperimentRunner, EquityExperimentSpec, EquityResearchReport,
    replay_equity_report, verify_equity_report,
)


def stock_inputs():
    first, last = date(2024, 11, 1), date(2024, 12, 3)
    days, sessions = [], []
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
            session = {"date": day.isoformat(), "kind": "OPEN", "open_utc": stamp(9, 30),
                       "close_utc": stamp(13 if early else 16), "early_close": early}
            days.append(session)
            sessions.append(session)
    rows = ["session_date,open,high,low,close,volume"]
    for index, session in enumerate(sessions):
        rows.append(f"{session['date']},{100 + index},{102 + index},{99 + index},{101 + index},10000")
    raw = ("\n".join(rows) + "\n").encode()
    def source(name, content):
        return {"name": "SYNTHETIC_" + name, "reference": "urn:synthetic:equity-research:" + name,
                "retrieved_at": "2024-12-04T00:00:00Z", "raw_base64": base64.b64encode(content).decode()}
    manifest = {
        "schema_version": "us-equity-daily-import-v1",
        "security": {"security_id": "SYNTHETIC:RESEARCH:TEST", "symbol": "TEST", "exchange": "XNYS",
                     "currency": "USD", "instrument_type": "COMMON_STOCK"},
        "identity": {"stable_within_coverage": True, "valid_from": first.isoformat(), "valid_through": last.isoformat(),
                     "selection_basis": "Fictional fixed fixture, not a historical stock universe",
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


def stock_snapshot():
    return build_equity_snapshot(*stock_inputs())


def spec_document(snapshot, strategy="cash", *, fee=0.0, slip=0.0, purpose="SYNTHETIC_REGRESSION"):
    sessions = snapshot.document["sessions"]
    params = {"target_position_pct": 1.0} if strategy == "buy_and_hold" else {}
    return {"schema_version": "us-equity-experiment-spec-v1", "name": "portable fictional equity check",
            "snapshot_id": snapshot.snapshot_id, "score_start_session": sessions[1]["date"],
            "score_end_session": sessions[-1]["date"], "strategy": {"name": strategy, "params": params},
            "initial_cash": 10000.0, "fee_rate": fee, "slippage_pct": slip,
            "risk": {"max_position_pct": 1.0, "max_single_loss_pct": 0.03, "max_daily_loss_pct": 1.0,
                     "min_cash_pct": 0.0, "max_leverage": 1.0}, "end_policy": "MARK_TO_MARKET", "purpose": purpose,
            "quantity_policy": "FRACTIONAL_SHARES_RESEARCH_APPROXIMATION",
            "execution_policy": BUY_AND_HOLD_POLICY if strategy == "buy_and_hold" else STANDARD_RISK_POLICY}


def run(snapshot, **kwargs):
    return EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(spec_document(snapshot, **kwargs)))


def reseal(report, *, result_changed=False, spec_changed=False):
    if spec_changed:
        report["spec_hash"] = digest(report["spec"])
    if result_changed or spec_changed:
        report["result_hash"] = digest({"snapshot_id": report["dataset"]["snapshot_id"], "spec": report["spec"], "result": report["result"]})
    report["report_hash"] = digest({key: value for key, value in report.items() if key != "report_hash"})
    return report


class EquityResearchTests(unittest.TestCase):
    def test_cash_has_zero_economic_activity_and_correct_session_count(self):
        snapshot = stock_snapshot()
        doc = verify_equity_report(run(snapshot).document)
        result = doc["result"]
        self.assertEqual(result["fills"], [])
        self.assertEqual(result["order_count"], 0)
        self.assertEqual(result["fill_count"], 0)
        self.assertEqual(result["final_cash"], 10000.0)
        self.assertEqual(result["final_equity"], 10000.0)
        self.assertEqual(result["total_return"], 0.0)
        self.assertEqual(len(result["equity_curve"]), len(snapshot.document["sessions"]))
        self.assertEqual(doc["scoring_protocol"]["scored_sessions"], len(snapshot.document["sessions"]) - 1)
        self.assertEqual(doc["scoring_protocol"]["available_context_sessions"], 1)
        self.assertEqual(result["statistical_status"]["periods_per_year"], 252)
        self.assertTrue(all(point["equity"] == 10000.0 for point in result["equity_curve"]))

    def test_buy_hold_fee_slippage_and_final_mark_match_cash_arithmetic(self):
        snapshot = stock_snapshot()
        doc = verify_equity_report(run(snapshot, strategy="buy_and_hold", fee=0.01, slip=0.01).document)
        result = doc["result"]
        self.assertEqual(result["fill_count"], 1)
        self.assertEqual(result["sell_fees"], 0)
        self.assertEqual(result["round_trip_count"], 0)
        fill = result["fills"][0]
        entry_raw = Decimal(str(snapshot.document["candles"][1][1]))
        expected_price = entry_raw * Decimal("1.01")
        expected_qty = Decimal("10000") / (expected_price * Decimal("1.01"))
        expected_fee = expected_qty * expected_price * Decimal("0.01")
        end_mark = Decimal(str(snapshot.document["candles"][-1][4]))
        self.assertAlmostEqual(fill["price"], float(expected_price), places=9)
        self.assertAlmostEqual(fill["quantity"], float(expected_qty), places=9)
        self.assertAlmostEqual(fill["fee"], float(expected_fee), places=9)
        self.assertAlmostEqual(result["final_cash"], 0, places=8)
        self.assertAlmostEqual(result["final_equity"], float(expected_qty * end_mark), places=8)
        self.assertAlmostEqual(result["open_position_qty"], float(expected_qty), places=9)
        self.assertEqual(result["end_position_policy"], "MARK_TO_MARKET_NO_FORCED_LIQUIDATION")

    def test_dst_early_close_and_weekend_clock_never_backdate_available_signal(self):
        snapshot = stock_snapshot()
        result = run(snapshot, strategy="buy_and_hold").document["result"]
        sessions = snapshot.document["sessions"]
        first_fill = result["fills"][0]
        self.assertEqual(pd.Timestamp(first_fill["signal_time"]), pd.Timestamp("2024-11-01T20:01:00Z"))
        self.assertEqual(pd.Timestamp(first_fill["fill_time"]), pd.Timestamp("2024-11-04T14:30:00Z"))
        marks = {pd.Timestamp(point["bar_time"]).date().isoformat(): point for point in result["equity_curve"][1:]}
        self.assertEqual(pd.Timestamp(marks["2024-11-29"]["time"]), pd.Timestamp("2024-11-29T18:00:00Z"))
        self.assertNotIn("2024-11-28", marks)
        self.assertNotIn("2024-11-30", marks)
        for signal, completed, following in zip(result["signals"], sessions[:-1], sessions[1:]):
            self.assertEqual(pd.Timestamp(signal["time"]), pd.Timestamp(completed["close_utc"]) + pd.Timedelta(seconds=60))
            self.assertLess(pd.Timestamp(signal["time"]), pd.Timestamp(following["open_utc"]))
        self.assertEqual(len(result["signals"]), len(sessions) - 1)

    def test_declared_latency_crossing_next_open_is_rejected(self):
        raw, manifest = stock_inputs()
        manifest["bar_availability_lag_seconds"] = 86400
        manifest["as_of"] = "2024-12-05T00:00:00Z"
        manifest["retrieved_at"] = "2024-12-05T00:00:00Z"
        manifest["price_source"]["retrieved_at"] = manifest["retrieved_at"]
        snapshot = build_equity_snapshot(raw, manifest)
        with self.assertRaisesRegex(ValueError, "bar_unavailable_before_next_open"):
            run(snapshot)

    def test_unknown_actions_or_action_within_window_cannot_reach_engine(self):
        for scenario in ("UNKNOWN", "SPLIT", "DIVIDEND"):
            raw, manifest = stock_inputs()
            if scenario == "UNKNOWN":
                manifest["corporate_actions"]["coverage_status"] = "UNKNOWN"
            else:
                manifest["corporate_actions"]["actions"] = [{"action_id": "blocked-event", "security_id": manifest["security"]["security_id"],
                    "action_type": scenario, "effective_date": "2024-11-20", "source_reference": "urn:synthetic:event", "details": {}}]
            snapshot = build_equity_snapshot(raw, manifest)
            with self.subTest(scenario=scenario), patch("hakimi_research.equity_research._SessionEngine") as engine:
                with self.assertRaisesRegex(ValueError, "economic_research_blocked"):
                    run(snapshot)
                engine.assert_not_called()

    def test_real_import_development_purpose_is_supported_without_promoting_truth(self):
        raw, manifest = stock_inputs()
        # This remains fictional input; only the importer declaration is changed
        # to exercise the distinct non-synthetic development-purpose branch.
        manifest["evidence_kind"] = "IMPORTED_UNVERIFIED"
        snapshot = build_equity_snapshot(raw, manifest)
        doc = verify_equity_report(run(snapshot, purpose="DESCRIPTIVE_DEVELOPMENT").document)
        self.assertEqual(doc["spec"]["purpose"], "DESCRIPTIVE_DEVELOPMENT")
        self.assertFalse(doc["dataset"]["research_admission"]["source_truth_verified"])
        self.assertFalse(doc["scoring_protocol"]["confirmation_evaluation"])

    def test_synthetic_prices_cannot_become_descriptive_market_evidence(self):
        with self.assertRaisesRegex(ValueError, "synthetic_equity_cannot_be_market_evidence"):
            run(stock_snapshot(), purpose="DESCRIPTIVE_DEVELOPMENT")

    def test_spec_snapshot_identity_and_closed_score_dates_are_rejected(self):
        snapshot = stock_snapshot()
        bad = spec_document(snapshot)
        bad["snapshot_id"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "spec_snapshot_mismatch"):
            EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(bad))
        for day in ["2024-11-03", "2024-11-28"]:
            bad = spec_document(snapshot)
            bad["score_start_session"] = day
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "score_session_not_in_snapshot"):
                EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(bad))
        bad = spec_document(snapshot)
        bad["score_start_session"] = snapshot.document["sessions"][0]["date"]
        with self.assertRaisesRegex(ValueError, "insufficient_context"):
            EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(bad))

    def test_report_resealing_does_not_admit_invalid_mark_or_available_signal(self):
        original = run(stock_snapshot(), strategy="buy_and_hold").document
        for scenario in ("mark", "signal", "initial_mark", "signal_count"):
            modified = copy.deepcopy(original)
            if scenario == "mark":
                modified["result"]["equity_curve"][1]["time"] = "2024-11-04T14:30:00Z"
            elif scenario == "signal":
                modified["result"]["signals"][0]["time"] = "2024-11-01T20:00:00Z"
            elif scenario == "initial_mark":
                modified["result"]["equity_curve"][0]["time"] = "2024-11-03T14:30:00Z"
            else:
                modified["result"]["signals"].pop()
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                verify_equity_report(reseal(modified, result_changed=True))

    def test_report_resealing_cannot_claim_closed_day_or_pre_signal_fill(self):
        original = run(stock_snapshot(), strategy="buy_and_hold").document
        for field, timestamp in [("fill_time", "2024-11-03T14:30:00Z"),
                                 ("fill_time", "2024-11-28T14:30:00Z"),
                                 ("signal_time", "2024-11-04T14:30:00Z")]:
            modified = copy.deepcopy(original)
            modified["result"]["fills"][0][field] = timestamp
            with self.subTest(field=field, timestamp=timestamp), self.assertRaisesRegex(ValueError, "fill_before_signal_or_outside_session"):
                verify_equity_report(reseal(modified, result_changed=True))

    def test_report_resealing_cannot_disconnect_spec_or_enable_order_permission(self):
        original = run(stock_snapshot()).document
        for scenario in ("snapshot", "order"):
            modified = copy.deepcopy(original)
            if scenario == "snapshot":
                modified["spec"]["snapshot_id"] = "a" * 64
            else:
                modified["execution_permission"]["order_allowed"] = True
            with self.subTest(scenario=scenario), self.assertRaisesRegex(ValueError, "identity_or_permission"):
                verify_equity_report(reseal(modified, spec_changed=True))

    def test_next_open_fill_must_bind_its_actual_prior_session_available_signal(self):
        modified = copy.deepcopy(run(stock_snapshot(), strategy="buy_and_hold").document)
        # Earlier than the fill is insufficient: the full previous daily bar
        # could not have supplied this signal at its own opening timestamp.
        modified["result"]["fills"][0]["signal_time"] = "2024-11-01T13:30:00Z"
        with self.assertRaises(ValueError):
            verify_equity_report(reseal(modified, result_changed=True))

    def test_unknown_fill_basis_cannot_bypass_the_signal_clock(self):
        modified = copy.deepcopy(run(stock_snapshot(), strategy="buy_and_hold").document)
        modified["result"]["fills"][0]["fill_basis"] = "UNSUPPORTED_BASIS"
        modified["result"]["fills"][0]["signal_time"] = "2024-11-05T21:01:00Z"
        with self.assertRaises(ValueError):
            verify_equity_report(reseal(modified, result_changed=True))

    def test_save_and_replay_identical_input_passes_measured_source_and_environment(self):
        snapshot = stock_snapshot()
        report = run(snapshot, strategy="buy_and_hold", fee=0.001)
        with tempfile.TemporaryDirectory() as directory:
            path = report.save(directory)
            loaded = EquityResearchReport(json.loads(path.read_bytes()))
            receipt = replay_equity_report(snapshot, loaded)
        self.assertTrue(receipt["result_matches"])
        self.assertTrue(receipt["source_matches"])
        self.assertTrue(receipt["environment_verified"])
        self.assertTrue(receipt["replay_verified"])
        self.assertFalse(receipt["execution_permission"]["order_allowed"])

    def test_failed_source_or_environment_cannot_be_promoted_by_matching_hash(self):
        snapshot = stock_snapshot()
        original = run(snapshot)
        for target, label in [("source_identity", "FAILED"), ("environment_verified", "FAILED")]:
            modified = copy.deepcopy(original.document)
            modified["provenance"][target]["status"] = label
            reseal(modified)
            with self.subTest(target=target):
                receipt = replay_equity_report(snapshot, EquityResearchReport(modified))
                self.assertTrue(receipt["result_matches"])
                self.assertFalse(receipt["replay_verified"])
                self.assertFalse(receipt["source_matches"] if target == "source_identity" else receipt["environment_verified"])


if __name__ == "__main__":
    unittest.main()
