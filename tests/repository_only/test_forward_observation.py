"""Offline timing and replay contracts for the installed-wheel observer sidecar."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from hakimi_research.dataset_registry import build_csv_snapshot, utc_text
from hakimi_research.documents import digest, read_document

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("forward_observer", ROOT / "tools" / "observe_forward.py")
observer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(observer)
CUTOFF = "2024-01-01T06:00:00Z"


def request(strategy="rsi"):
    params = ({"window": 3, "oversold": 30, "overbought": 70, "position_pct": 0.15, "stop_loss_pct": 0.03}
              if strategy == "rsi" else {"fast_window": 2, "slow_window": 3, "position_pct": 0.25})
    return {"name": "synthetic-forward-test", "strategy": {"name": strategy, "params": params},
            "state_policy": "FLAT_REFERENCE_OBSERVATION", "context_rows": 6, "first_cutoff": CUTOFF,
            "reference_portfolio": {"cash": 10000, "position_qty": 0, "avg_entry_price": 0,
                                    "realized_pnl": 0, "entry_fees": 0}}


def snapshot(closes=None, *, retrieved="2024-01-01T06:01:00Z", older=False, future=False):
    closes = closes or [110, 109, 108, 107, 106, 105]
    times = pd.date_range("2024-01-01", periods=6, freq="h", tz="UTC")
    values = list(zip(times, closes))
    if older:
        values.insert(0, (times[0] - pd.Timedelta(hours=1), 111))
    if future:
        values.append((pd.Timestamp(CUTOFF), 104))
    raw = "time,open,high,low,close,volume\n" + "".join(
        f"{utc_text(stamp)},{value},{value + 1},{value - 1},{value},100\n" for stamp, value in values)
    metadata = {"market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT",
                "timeframe": "1h", "source": "synthetic software contract fixture", "retrieved_at": retrieved,
                "as_of": CUTOFF, "volume_unit": "base_currency", "quote_unit": "USDT", "timezone": "UTC",
                "start": "2024-01-01T00:00:00Z", "end_exclusive": CUTOFF, "completed_bars_only": True}
    return build_csv_snapshot(raw.encode("utf-8"), metadata)


class ForwardObservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = {"source_identity": {"status": "BUILD_VERIFIED", "content_sha256": "a" * 64},
                        "environment_verified": {"status": "VERIFIED", "python_version": "3.14.6",
                                                 "packages": {"numpy": {"required": "2.4.6", "installed": "2.4.6"}}},
                        "dependency_lock": {"sha256": "b" * 64}}
        for context in (patch.object(observer, "REPOSITORY_ROOT", None),
                        patch.object(observer, "build_runtime_provenance", side_effect=lambda: copy.deepcopy(self.runtime))):
            context.start()
            self.addCleanup(context.stop)
        self.plan = self.freeze(request())

    def freeze(self, spec):
        with patch.object(observer, "_now", return_value="2024-01-01T00:00:00Z"):
            return read_document(observer.freeze_plan(spec, self.root / "plans"))

    def observe(self, *, time="2024-01-01T06:01:00Z", source=None, backfill=False, folder="observations"):
        with patch.object(observer, "_now", return_value=time):
            return observer.observe(self.plan, source or snapshot(), CUTOFF, self.root / folder, backfill=backfill)

    def test_real_rsi_and_dual_ma_signals_have_flat_state_and_no_order_calls(self):
        with patch("hakimi_research.risk.RiskManager.signal_to_order") as orders, \
                patch("hakimi_research.execution.ResearchExecutionSimulator.submit_order") as submit:
            rsi_record = read_document(self.observe())
            self.assertEqual(rsi_record["signal"]["action"], "BUY")
            self.assertIn("RSI oversold", rsi_record["signal"]["reason"])
            self.plan = self.freeze(request("dual_ma"))
            ma_record = read_document(self.observe(source=snapshot([100, 100, 100, 98, 98, 106]), folder="ma"))
            self.assertEqual(ma_record["signal"]["action"], "BUY")
            self.assertEqual(ma_record["signal"]["reason"], "fast MA crossed above slow MA")
            orders.assert_not_called()
            submit.assert_not_called()
        for record in (rsi_record, ma_record):
            self.assertFalse(record["position_state_observed"])
            self.assertEqual(record["reference_portfolio"]["position_qty"], 0)
            self.assertEqual(record["state_policy"], "FLAT_REFERENCE_OBSERVATION")
            self.assertEqual(record["output_hash"], digest(record["signal"]))
            self.assertEqual(record["input_hash"], digest(record["input"]))
            self.assertFalse(record["execution_permission"]["order_allowed"])

    def test_actual_clock_distinguishes_on_time_late_and_backfill(self):
        cases = (("2024-01-01T06:05:00Z", False, "ON_TIME"),
                 ("2024-01-01T06:05:00.000001Z", False, "LATE"),
                 ("2024-01-01T06:01:00Z", True, "BACKFILL"))
        for time, backfill, expected in cases:
            with self.subTest(expected=expected):
                record = read_document(self.observe(time=time, backfill=backfill, folder=expected))
                self.assertEqual(record["timing_status"], expected)
                self.assertEqual(record["recorded_at_utc"], time)
                self.assertEqual(record["signal_available_at"], time)
                self.assertEqual(record["input"]["input_available_at"], "2024-01-01T06:01:00Z")

    def test_duplicate_retries_keep_original_clock_and_changed_input_conflicts(self):
        path = self.observe()
        before = path.read_bytes()
        self.assertEqual(self.observe(time="2024-01-02T00:00:00Z"), path)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            self.observe(source=snapshot([110, 109, 108, 107, 106, 104]))
        with self.assertRaises(FileExistsError):
            self.observe(backfill=True)
        self.assertEqual(path.read_bytes(), before)

    def test_future_cutoff_and_input_retrieved_after_observation_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "future_cutoff"):
            self.observe(time="2024-01-01T05:59:59Z")
        with self.assertRaisesRegex(ValueError, "retrieval_after_observation"):
            self.observe(source=snapshot(retrieved="2024-01-01T06:02:00Z"))
        self.assertFalse((self.root / "observations").exists())

    def test_older_raw_rows_are_allowed_but_future_raw_rows_are_rejected(self):
        record = read_document(self.observe(source=snapshot(older=True)))
        self.assertEqual(record["input"]["context_rows"], 6)
        self.assertEqual(record["input"]["older_raw_rows_excluded"], 1)
        with self.assertRaisesRegex(ValueError, "future_raw_row"):
            self.observe(source=snapshot(future=True, retrieved="2024-01-01T07:01:00Z"),
                         time="2024-01-01T07:02:00Z", folder="future")
        self.assertFalse((self.root / "future").exists())

    def test_plan_is_frozen_before_first_cutoff_and_requires_explicit_flat_state(self):
        with patch.object(observer, "_now", return_value=CUTOFF), self.assertRaisesRegex(ValueError, "actual_freeze_time"):
            observer.freeze_plan(request(), self.root / "past-plan")
        for change in (lambda spec: spec["reference_portfolio"].__setitem__("position_qty", 1),
                       lambda spec: spec["strategy"].__setitem__("name", "buy_and_hold"),
                       lambda spec: spec.__setitem__("state_policy", "SIMULATED_ACCOUNT")):
            spec = request()
            change(spec)
            with self.assertRaises(ValueError):
                self.freeze(spec)

    def test_source_environment_and_installed_build_are_required(self):
        self.runtime["source_identity"]["content_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "frozen_source"):
            self.observe()
        self.runtime["source_identity"]["content_sha256"] = "a" * 64
        self.runtime["environment_verified"]["status"] = "MISMATCH"
        with self.assertRaisesRegex(ValueError, "verified_environment"):
            self.observe()
        self.runtime["environment_verified"]["status"] = "VERIFIED"
        self.runtime["source_identity"]["status"] = "CONTENT_HASHED"
        with self.assertRaisesRegex(ValueError, "verified_installed_build"):
            self.observe()

    def test_replay_preserves_original_clock_and_rejects_resealed_signal_or_clock(self):
        path = self.observe()
        record = read_document(path)
        with patch.object(observer, "_now", side_effect=AssertionError("replay cannot generate an observation time")):
            replay = observer.replay(self.plan, snapshot(), record)
        self.assertEqual(replay["status"], "VERIFIED")
        self.assertFalse(replay["new_observation_created"])
        self.assertEqual(replay["original_recorded_at_utc"], record["recorded_at_utc"])
        for field, value in (("signal", {**record["signal"], "action": "HOLD"}),
                             ("signal_available_at", "2024-01-01T06:00:00Z")):
            changed = {**record, field: value}
            changed["record_hash"] = digest({key: item for key, item in changed.items() if key != "record_hash"})
            with self.assertRaisesRegex(ValueError, "replay_mismatch"):
                observer.replay(self.plan, snapshot(), changed)

    def test_context_drift_and_cutoff_alias_cannot_create_another_record(self):
        other = request()
        other["context_rows"] = 7
        self.plan = self.freeze(other)
        with self.assertRaisesRegex(ValueError, "exact_completed_context"):
            self.observe()
        with patch.object(observer, "_now", return_value="2024-01-01T06:01:00Z"):
            with self.assertRaisesRegex(ValueError, "canonical_cutoff"):
                observer.observe(self.plan, snapshot(), "2024-01-01T06:00Z", self.root / "alias")


if __name__ == "__main__":
    unittest.main()
