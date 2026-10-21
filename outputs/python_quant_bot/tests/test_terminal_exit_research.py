"""Offline receipts and integrity checks for separate fixed-entry exit research."""
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import causal_structure, exit_comparison_math, terminal_exit_research
from exchange_terminal.services.terminal_research import TerminalResearchService, _seal
from exchange_terminal.services.quant_workspace import _READ_RESOURCES


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


class Core:
    def __init__(self, workspace):
        self.workspace = workspace

    def read(self, resource, identity=None):
        return {"items": []} if resource == "strategies" else {"resource": resource, "identity": identity}

    def mutate(self, action, payload):
        return {"action": action, "payload": payload}


class TerminalExitResearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-exit-offline-")
        self.addCleanup(temporary.cleanup)
        self.core = Core(Path(temporary.name) / "research-workspace")
        rows = []
        for index in range(100):
            session = (date(2020, 1, 1) + timedelta(days=index)).isoformat()
            price = 100 + index * .2
            rows.append({"date": session, "ts_ms": 1577836800000 + index * 86400000,
                         "open": price, "high": price + 2, "low": price - 2,
                         "close": price + .5, "volume": 1000 + index,
                         "complete": True, "provisional": False, "source": "qa-provider"})
        self.market = {"symbol": "QADEMO", "bar": "1D", "source_id": "qa-local-source",
                       "meta": {"asset_class": "EQUITY", "interval": "1D", "session": "REGULAR",
                                "price_basis": "RAW", "source_lineage": ["qa-provider"],
                                "origin_reference": "urn:qa:exit", "volume_unit": "shares"},
                       "quality": {"status": "REVIEW", "blockers": [], "warnings": ["QA only"],
                                   "source_authenticated": False, "research_only": True,
                                   "core_us_equity_import_allowed": False},
                       "excluded_incomplete_count": 0, "rows": rows}
        self.market["digest"] = digest(self.market)
        self.reader = Mock(side_effect=lambda symbol, limit=2000, source_id=None: deepcopy(self.market))
        self.catalog = [{"id": "dual_ma", "name": "Original MA", "params": {"fast_window": 20,
                         "slow_window": 60}, "capability": {"known": True, "backtest_supported": True,
                         "new_research_allowed": True}}]
        self.fingerprint = lambda strategy, params: digest({"strategy": strategy, "params": params})
        self.runner = Mock(side_effect=self.native_runner)
        self.service = self.new_service()

    def new_service(self):
        return TerminalResearchService(self.core, self.reader, lambda: deepcopy(self.catalog),
                                       self.runner, self.fingerprint)

    @staticmethod
    def native_runner(**kwargs):
        rows = kwargs["market_payload"]["rows"]
        entry = rows[80]
        trades = [{"signal_date": rows[79]["date"], "date": entry["date"], "side": "BUY",
                   "price": entry["open"], "quantity": 2, "fee": .12, "reason": "QA",
                   "fill_basis": "NEXT_BAR_OPEN"},
                  {"date": rows[85]["date"], "side": "SELL", "price": rows[85]["open"],
                   "quantity": 2, "fee": .12, "reason": "QA", "fill_basis": "NEXT_BAR_OPEN"}]
        curve = [{"date": row["date"], "ts_ms": row["ts_ms"], "equity": 10000 + index}
                 for index, row in enumerate(rows[80:])]
        return {"ok": True, "trades": trades, "order_event_count": len(trades),
                "equity_curve": curve, "evaluation_window": {"evaluated_rows": len(curve)},
                "total_return_pct": 1, "max_drawdown_pct": 1}

    def native_run(self):
        frozen = self.service.mutate("terminal_freeze_market", {"symbol": "QADEMO", "limit": 2000,
            "source_id": "qa-local-source", "expected_digest": self.market["digest"]})
        task = self.service.mutate("terminal_save_task", {"name": "Exit QA task",
            "strategy_id": "dual_ma", "strategy_params": {"fast_window": 10, "slow_window": 40},
            "input_id": frozen["id"], "risk": {"position_pct": 25, "take_profit_pct": 0,
            "stop_loss_pct": 8, "leverage": 1}, "costs": {"fee_rate": .0005, "slippage_bps": 2}})
        run = self.service.mutate("terminal_run_task", {"task_id": task["id"]})
        return frozen, task, run

    def spec(self):
        rows = self.market["rows"]
        return {"split": {
            "TRAIN": {"start_date": rows[0]["date"], "end_date": rows[59]["date"]},
            "VALIDATION": {"start_date": rows[60]["date"], "end_date": rows[79]["date"]},
            "TEST": {"start_date": rows[80]["date"], "end_date": rows[99]["date"]}},
            "fixed_stop_pct": 6, "atr_window": 14, "atr_mult": 2,
            "structure_left_window": 3, "structure_right_window": 3,
            "emergency_stop_pct": 12, "max_hold_bars": 10,
            "costs": {"fee_rate": .0005, "slippage_bps": 2}}

    def register_payload(self, run, *, request="register-exit-0001"):
        return {"client_request_id": request, "original_run_id": run["id"], "spec": self.spec()}

    def test_register_run_reopen_and_replay_preserve_original_bytes_and_do_not_recalculate(self):
        frozen, task, run = self.native_run()
        original = self.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"
        input_path = self.core.workspace / "terminal-inputs" / (frozen["id"] + ".json")
        old_bytes = (original.read_bytes(), input_path.read_bytes())
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        self.assertEqual(experiment["status"], "REGISTERED")
        self.assertEqual(experiment["cohort_count"], 1)
        self.assertEqual(experiment["cohort"][0]["signal_date"], self.market["rows"][79]["date"])
        self.assertEqual(experiment["source_hashes"]["causal_structure.py"], causal_structure.LOADED_SOURCE_SHA256)
        completed = self.service.mutate("terminal_run_exit_experiment", {
            "client_request_id": "run-exit-0001", "experiment_id": experiment["id"]})
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["result"]["cohort_count"], 1)
        self.assertEqual(len(completed["result"]["samples"]), 1)
        self.assertEqual(set(completed["result"]["samples"][0]["outcomes"]),
                         {"fixed_pct", "atr_trailing", "confirmed_structure"})
        self.assertIsNone(completed["result"]["portfolio_equity_curve"])
        self.assertEqual(old_bytes, (original.read_bytes(), input_path.read_bytes()))
        reopened = self.new_service()
        with patch.object(exit_comparison_math, "compare_exit_rules",
                          side_effect=AssertionError("historical result recalculated")):
            detail = reopened.read("terminal_exit_runs", completed["exit_run_id"])
            replay = reopened.read("terminal_exit_replay", completed["exit_run_id"])
        self.assertEqual(detail["result"], completed["result"])
        self.assertTrue(replay["available"])
        self.assertEqual(replay["source"], "EXIT_RESEARCH_FROZEN")
        self.assertEqual(replay["input_id"], frozen["id"])
        self.assertEqual(replay["trades"], [])
        self.assertNotIn("run_id", replay)
        self.assertNotIn("equity_curve", replay)
        self.assertEqual(replay["record_hash"], completed["record_hash"])
        self.assertEqual(len(replay["rows"]), frozen["row_count"])

    def test_register_and_run_requests_are_idempotent_and_conflict_on_changed_payload(self):
        _, _, run = self.native_run()
        payload = self.register_payload(run)
        experiment = self.service.mutate("terminal_register_exit_experiment", payload)
        self.assertEqual(self.service.mutate("terminal_register_exit_experiment", payload)["id"], experiment["id"])
        with self.assertRaisesRegex(ValueError, "request_id_conflict"):
            self.service.mutate("terminal_register_exit_experiment", {**payload,
                "spec": {**payload["spec"], "fixed_stop_pct": 7}})
        request = {"client_request_id": "run-exit-0002", "experiment_id": experiment["id"]}
        first = self.service.mutate("terminal_run_exit_experiment", request)
        with patch.object(exit_comparison_math, "compare_exit_rules", side_effect=AssertionError("rerun")):
            self.assertEqual(self.service.mutate("terminal_run_exit_experiment", request)["record_hash"], first["record_hash"])
            self.assertTrue(self.service.mutate("terminal_run_exit_experiment", {
                "client_request_id": "another-run-exit-0002", "experiment_id": experiment["id"]})["reused"])
        with self.assertRaisesRegex(ValueError, "request_id_conflict"):
            self.service.mutate("terminal_run_exit_experiment", {**request, "experiment_id": "a" * 64})

    def test_started_without_report_is_unknown_and_never_reruns(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        original_write = self.service._write
        def interrupted(path, value):
            if Path(path).name == "report.json" and "terminal-exit-runs" in Path(path).parts:
                raise OSError("QA interrupted after start receipt")
            return original_write(path, value)
        request = {"client_request_id": "run-exit-0003", "experiment_id": experiment["id"]}
        with patch.object(self.service, "_write", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.service.mutate("terminal_run_exit_experiment", request)
        self.assertEqual(self.runner.call_count, 1)
        with patch.object(exit_comparison_math, "compare_exit_rules", side_effect=AssertionError("rerun")):
            again = self.new_service().mutate("terminal_run_exit_experiment", request)
        self.assertEqual(again["status"], "UNKNOWN")
        self.assertFalse(again["automatic_retry"])
        self.assertFalse(self.new_service().read("terminal_exit_replay", again["exit_run_id"])["available"])

    def test_add_or_missing_buy_fields_and_split_outside_buy_are_rejected(self):
        _, _, run = self.native_run()
        with patch.object(self.service.exit_research, "_original", wraps=self.service.exit_research._original) as source:
            original, frozen, cohort = source(run["id"])
        amended = deepcopy(original)
        amended["result"]["trades"].append({"date": cohort[0]["date"], "side": "ADD"})
        amended["result"]["order_event_count"] += 1
        with patch.object(self.service, "read", return_value=amended):
            with self.assertRaisesRegex(ValueError, "non_buy_add"):
                self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        outside = self.register_payload(run)
        outside["spec"]["split"]["TEST"]["start_date"] = self.market["rows"][90]["date"]
        with self.assertRaisesRegex(ValueError, "entry_outside"):
            self.service.mutate("terminal_register_exit_experiment", outside)

    def test_blocked_strategy_and_core_id_cannot_register(self):
        _, _, run = self.native_run()
        self.catalog[0]["capability"]["new_research_allowed"] = False
        with self.assertRaisesRegex(ValueError, "new_research_blocked"):
            self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        with self.assertRaisesRegex(ValueError, "original_run_id_invalid"):
            self.service.mutate("terminal_register_exit_experiment", {
                **self.register_payload(run), "original_run_id": "a" * 24})

    def test_strategy_disabled_after_registration_blocks_first_run_without_start(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        self.catalog[0]["capability"]["new_research_allowed"] = False
        with self.assertRaisesRegex(ValueError, "new_research_blocked"):
            self.service.mutate("terminal_run_exit_experiment", {
                "client_request_id": "blocked-run-exit-0001", "experiment_id": experiment["id"]})
        self.assertFalse((self.core.workspace / "terminal-exit-runs").exists())
        self.assertEqual(self.service.read("terminal_exit_experiments", experiment["id"])["status"], "REGISTERED")

    def test_intent_only_register_and_run_show_unknown_without_read_side_writes(self):
        _, _, run = self.native_run()
        original_write = self.service._write
        def interrupted_register(path, value):
            if Path(path).name == "experiment.json":
                raise OSError("QA interrupted after register intent")
            return original_write(path, value)
        with patch.object(self.service, "_write", side_effect=interrupted_register):
            with self.assertRaises(OSError):
                self.service.mutate("terminal_register_exit_experiment",
                                    self.register_payload(run, request="intent-register-0001"))
        before = sorted(str(path) for path in self.core.workspace.rglob("*.json"))
        registered = self.new_service().read("terminal_exit_experiments")["items"]
        self.assertEqual(len(registered), 1)
        self.assertEqual(registered[0]["status"], "UNKNOWN")
        self.assertEqual(registered[0]["client_request_id"], "intent-register-0001")
        self.assertFalse(registered[0]["automatic_retry"])
        self.assertEqual(before, sorted(str(path) for path in self.core.workspace.rglob("*.json")))
        # A distinct explicit registration is allowed and remains separate.
        experiment = self.service.mutate("terminal_register_exit_experiment",
                                         self.register_payload(run, request="intent-register-0002"))
        def interrupted_run(path, value):
            if Path(path).name == "started.json" and "terminal-exit-runs" in Path(path).parts:
                raise OSError("QA interrupted after run intent")
            return original_write(path, value)
        with patch.object(self.service, "_write", side_effect=interrupted_run):
            with self.assertRaises(OSError):
                self.service.mutate("terminal_run_exit_experiment", {
                    "client_request_id": "intent-run-exit-0001", "experiment_id": experiment["id"]})
        before = sorted(str(path) for path in self.core.workspace.rglob("*.json"))
        queued = self.new_service().read("terminal_exit_runs")["items"]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["status"], "UNKNOWN")
        self.assertEqual(queued[0]["client_request_id"], "intent-run-exit-0001")
        self.assertEqual(queued[0]["experiment_id"], experiment["id"])
        self.assertFalse(queued[0]["automatic_retry"])
        self.assertEqual(before, sorted(str(path) for path in self.core.workspace.rglob("*.json")))

    def test_missing_or_changed_old_source_makes_replay_unavailable_without_rewriting_it(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        completed = self.service.mutate("terminal_run_exit_experiment", {
            "client_request_id": "run-exit-0004", "experiment_id": experiment["id"]})
        old_path = self.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"
        old_path.write_bytes(b"{}")
        reopened = self.new_service()
        self.assertEqual(reopened.read("terminal_exit_experiments", experiment["id"])["status"], "UNKNOWN")
        self.assertEqual(reopened.read("terminal_exit_runs", completed["exit_run_id"])["status"], "UNKNOWN")
        self.assertFalse(reopened.read("terminal_exit_replay", completed["exit_run_id"])["available"])

    def test_loaded_source_drift_blocks_new_run_before_started_receipt(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        with patch.object(exit_comparison_math, "assert_loaded_source_current",
                          side_effect=ValueError("exit_comparison_source_changed_restart_required")):
            with self.assertRaisesRegex(ValueError, "source_changed_restart_required"):
                self.service.mutate("terminal_run_exit_experiment", {
                    "client_request_id": "run-exit-0005", "experiment_id": experiment["id"]})
        self.assertFalse((self.core.workspace / "terminal-exit-runs").exists())

    def test_forged_sample_entry_at_first_run_is_unknown_not_replayable(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        original_math = exit_comparison_math.compare_exit_rules
        def falsified(rows, entries, spec):
            result = original_math(rows, entries, spec)
            result["samples"][0]["entry"]["price"] = 999
            return result
        with patch.object(exit_comparison_math, "compare_exit_rules", side_effect=falsified):
            detail = self.service.mutate("terminal_run_exit_experiment", {
                "client_request_id": "forged-sample-exit-0001", "experiment_id": experiment["id"]})
        self.assertEqual(detail["status"], "UNKNOWN")
        self.assertIn("sample_entry_binding_invalid", detail["error"])
        self.assertFalse(self.service.read("terminal_exit_replay", detail["exit_run_id"])["available"])

    def test_resealed_historical_sample_or_path_entry_is_unknown_without_recomputation(self):
        _, _, run = self.native_run()
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        detail = self.service.mutate("terminal_run_exit_experiment", {
            "client_request_id": "historical-path-exit-0001", "experiment_id": experiment["id"]})
        path = self.core.workspace / "terminal-exit-runs" / detail["exit_run_id"] / "report.json"
        original = path.read_bytes()
        for target in ("sample", "path"):
            with self.subTest(target=target):
                body = json.loads(original)
                body.pop("id")
                if target == "sample":
                    body["result"]["samples"][0]["entry"]["price"] = 999
                else:
                    body["result"]["exit_paths"][0]["entry"]["price"] = 999
                body["result_hash"] = digest(body["result"])
                sealed = _seal(body)
                path.write_bytes(json.dumps(sealed, ensure_ascii=False, sort_keys=True,
                                            separators=(",", ":")).encode("utf-8"))
                reopened = self.new_service()
                with patch.object(exit_comparison_math, "compare_exit_rules",
                                  side_effect=AssertionError("historical read recalculated")):
                    self.assertEqual(reopened.read("terminal_exit_runs", detail["exit_run_id"])["status"], "UNKNOWN")
                    self.assertFalse(reopened.read("terminal_exit_replay", detail["exit_run_id"])["available"])
                path.write_bytes(original)

    def test_legacy_three_source_experiment_remains_readable_but_cannot_start_new_run(self):
        _, _, run = self.native_run()
        current = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        completed = self.service.mutate("terminal_run_exit_experiment", {
            "client_request_id": "current-four-hash-run-0001", "experiment_id": current["id"]})
        self.assertEqual(set(current["source_hashes"]), {"causal_structure.py", "exit_comparison_math.py",
                                                        "indicator_math.py", "terminal_exit_research.py"})
        body = {key: deepcopy(value) for key, value in current.items()
                if key not in {"id", "experiment_id", "record_hash", "status", "integrity_status",
                               "input_summary", "new_economic_runs", "automatic_retry", "run_compatibility",
                               "requires_revision", "run_blocker"}}
        body["source_hashes"].pop("terminal_exit_research.py")
        legacy = _seal(body)
        legacy_path = self.core.workspace / "terminal-exit-experiments" / legacy["id"] / "experiment.json"
        self.service._write(legacy_path, legacy)
        reopened = self.new_service()
        detail = reopened.read("terminal_exit_experiments", legacy["id"])
        self.assertEqual(detail["status"], "REGISTERED")
        self.assertTrue(detail["requires_revision"])
        self.assertEqual(detail["run_compatibility"], "REQUIRES_NEW_REGISTRATION")
        self.assertIn("terminal_exit_service_source_not_bound", detail["run_blocker"])
        legacy_run_id = reopened.exit_research._exit_run_id(legacy["id"])
        with self.assertRaisesRegex(ValueError, "source_changed_register_new_experiment"):
            reopened.mutate("terminal_run_exit_experiment", {
                "client_request_id": "legacy-first-run-0001", "experiment_id": legacy["id"]})
        self.assertFalse((self.core.workspace / "terminal-exit-runs" / legacy_run_id / "started.json").exists())
        # Simulate a previously completed old-schema receipt without rewriting it.
        current_root = self.core.workspace / "terminal-exit-runs" / completed["exit_run_id"]
        start_body = json.loads((current_root / "started.json").read_bytes())
        start_body.pop("id")
        start_body.update(exit_run_id=legacy_run_id, experiment_id=legacy["id"],
                          source_hashes=legacy["source_hashes"])
        legacy_start = _seal(start_body)
        report_body = json.loads((current_root / "report.json").read_bytes())
        report_body.pop("id")
        report_body.update(exit_run_id=legacy_run_id, experiment_id=legacy["id"],
                           started_hash=legacy_start["id"], source_hashes=legacy["source_hashes"])
        legacy_report = _seal(report_body)
        legacy_root = self.core.workspace / "terminal-exit-runs" / legacy_run_id
        self.service._write(legacy_root / "started.json", legacy_start)
        self.service._write(legacy_root / "report.json", legacy_report)
        with patch.object(exit_comparison_math, "compare_exit_rules",
                          side_effect=AssertionError("legacy result recalculated")):
            historical = self.new_service().read("terminal_exit_runs", legacy_run_id)
            replay = self.new_service().read("terminal_exit_replay", legacy_run_id)
        self.assertEqual(historical["status"], "COMPLETED")
        self.assertTrue(replay["available"])
        self.assertEqual(replay["record_hash"], legacy_report["id"])

    def test_current_service_source_drift_blocks_new_registration_and_first_run(self):
        _, _, run = self.native_run()
        with patch.object(terminal_exit_research, "assert_loaded_source_current",
                          side_effect=ValueError("terminal_exit_service_source_changed_restart_required")):
            with self.assertRaisesRegex(ValueError, "service_source_changed_restart_required"):
                self.service.mutate("terminal_register_exit_experiment",
                                    self.register_payload(run, request="service-drift-register-0001"))
        self.assertFalse((self.core.workspace / "terminal-exit-experiments").exists())
        experiment = self.service.mutate("terminal_register_exit_experiment", self.register_payload(run))
        with patch.object(terminal_exit_research, "assert_loaded_source_current",
                          side_effect=ValueError("terminal_exit_service_source_changed_restart_required")):
            with self.assertRaisesRegex(ValueError, "service_source_changed_restart_required"):
                self.service.mutate("terminal_run_exit_experiment", {
                    "client_request_id": "service-drift-run-0001", "experiment_id": experiment["id"]})
        self.assertFalse((self.core.workspace / "terminal-exit-runs").exists())

    def test_structure_only_replay_is_derived_and_read_only(self):
        frozen, _, _ = self.native_run()
        before = list((self.core.workspace).rglob("*.json"))
        chart = self.service.read("terminal_structure_replay", frozen["id"])
        self.assertTrue(chart["available"])
        self.assertEqual(chart["source"], "STRUCTURE_FROZEN")
        self.assertEqual(chart["input_id"], frozen["id"])
        self.assertEqual(chart["trades"], [])
        self.assertTrue(chart["derived"])
        self.assertEqual(chart["structure"]["schema_version"], "causal-structure-v1")
        self.assertEqual(before, list((self.core.workspace).rglob("*.json")))
        self.assertIn("terminal_structure_replay", _READ_RESOURCES)
        self.assertIn("terminal_exit_replay", _READ_RESOURCES)


if __name__ == "__main__":
    unittest.main()
