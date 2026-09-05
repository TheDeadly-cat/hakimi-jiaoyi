"""Thin scheduler driver contracts; collection and observation are isolated."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

from hakimi_research.dataset_registry import build_csv_snapshot, save_snapshot, utc_text
from hakimi_research.documents import digest
from hakimi_research.reporting import save_json_report

_spec = importlib.util.spec_from_file_location("forward_cycle", Path(__file__).resolve().parents[2] / "tools/run_forward_cycle.py")
driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(driver)


class ForwardCycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.first = "2024-01-01T00:00:00Z"
        items = []
        for number, strategy in enumerate(("dual_ma", "rsi")):
            plan = {"plan_hash": str(number + 1) * 64,
                    "spec": {"strategy": {"name": strategy}, "context_rows": 72, "first_cutoff": self.first}}
            path = self.root / (strategy + ".json")
            path.write_text(json.dumps(plan), encoding="utf-8")
            items.append({"plan": str(path)})
        self.deployment = self.root / "deployment-plans.json"
        self.deployment.write_text(json.dumps({"first_cutoff": self.first, "plans": items}), encoding="utf-8")
        def observe(plan, snapshot, cutoff, directory):
            identity = digest({"plan_hash": plan["plan_hash"], "cutoff": cutoff})
            return Path(save_json_report({"record_hash": identity, "timing_status": "ON_TIME"},
                                         directory, "forward_observation", artifact_id=identity))
        self.observer = SimpleNamespace(_plan=lambda plan: plan, observe=observe,
                                        replay=lambda *args: {"status": "VERIFIED"})
        for context in (patch.object(driver, "_runtime_python"), patch.object(driver, "_observer", return_value=self.observer)):
            context.start()
            self.addCleanup(context.stop)

    def test_before_first_cutoff_is_not_due_and_does_not_collect(self):
        with patch.object(driver, "_now", return_value=pd.Timestamp("2023-12-31T23:59:00Z")), \
                patch.object(driver, "_collect") as collect:
            result = driver.run_cycle(self.deployment, self.root)
        self.assertEqual(result["status"], "NOT_DUE")
        collect.assert_not_called()
        self.assertFalse((self.root / "forward").exists())

    def test_hour_is_collected_once_retries_verify_and_missed_hours_stay_absent(self):
        def collect(root, start, cutoff, hour):
            times = pd.date_range(start, cutoff, freq="h", inclusive="left")
            raw = "time,open,high,low,close,volume\n" + "".join(
                f"{utc_text(stamp)},100,101,99,100,100\n" for stamp in times)
            metadata = {"market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT", "timeframe": "1h",
                        "source": "driver synthetic fixture", "retrieved_at": utc_text(cutoff + pd.Timedelta(minutes=1)),
                        "as_of": utc_text(cutoff), "volume_unit": "base_currency", "quote_unit": "USDT", "timezone": "UTC",
                        "start": utc_text(start), "end_exclusive": utc_text(cutoff), "completed_bars_only": True}
            snapshot_path = save_snapshot(build_csv_snapshot(raw.encode(), metadata), hour / "datasets")
            capture_path = save_json_report({"synthetic_fixture": True}, hour / "captures", "capture")
            return {"snapshot": str(snapshot_path), "capture": capture_path}
        with patch.object(driver, "_now", return_value=pd.Timestamp("2024-01-01T02:01:00Z")), \
                patch.object(driver, "_collect", side_effect=collect) as collector:
            first = driver.run_cycle(self.deployment, self.root)
            second = driver.run_cycle(self.deployment, self.root)
            self.assertEqual(first, second)
            self.assertEqual(collector.call_count, 1)
            self.assertEqual(first["observations"], 2)
            self.assertEqual(first["replays_verified"], 2)
            self.assertEqual([item["cutoff"] for item in first["prior_absences"]],
                             ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"])
            self.assertFalse(first["automatic_backfill"])
            receipt = json.loads(Path(first["input_receipt"]).read_text())
            capture_path = self.root / receipt["files"]["capture"]["path"]
            capture_path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "original_input_changed"):
                driver.run_cycle(self.deployment, self.root)
            self.assertEqual(collector.call_count, 1)


if __name__ == "__main__":
    unittest.main()
