"""Temporary synthetic fixtures for original-engine task/data/result binding."""
from copy import deepcopy
from datetime import date, timedelta
import base64
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.terminal_research import ENGINE_ID, TerminalResearchService, validate_terminal_strategy_params, _core_chart
from exchange_terminal.services.backtest_engine import run_causal_long_only_backtest
from exchange_terminal.services.strategy_signals import build_strategy_signal_fn, rolling_strategy_signal, strategy_startup_candles_for_params


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_core_import_qa_fixture(*, marked_synthetic=False, manifest_mutator=None):
    """Fabricated QA values modeling ordinary import metadata, never market truth.

    Uses an offline XNYS schedule solely to exercise real session validation. The
    ordinary branch deliberately models IMPORTED_UNVERIFIED; the separately
    marked SYNTHETIC_TEST branch must remain blocked by the native bridge.
    """
    from exchange_terminal.services.quant_workspace import _load_kernel
    from exchange_terminal.services.market_calendar import _exchange_sessions
    _load_kernel()
    from hakimi_terminal_research.equity_dataset import build_equity_snapshot

    schedule = _exchange_sessions("XNYS", "2024-01-02", "2024-07-31")[0]
    first, last = date.fromisoformat(schedule[0]["date"]), date.fromisoformat(schedule[-1]["date"])
    by_date = {row["date"]: row for row in schedule}
    days = []
    for offset in range((last - first).days + 1):
        current = first + timedelta(days=offset)
        if current.isoformat() in by_date:
            row = by_date[current.isoformat()]
            days.append({"date": row["date"], "kind": "OPEN", "open_utc": row["open_utc"].replace("+00:00", "Z"),
                         "close_utc": row["close_utc"].replace("+00:00", "Z"), "early_close": row["early_close"]})
        else:
            days.append({"date": current.isoformat(), "kind": "CLOSED", "reason": "WEEKEND" if current.weekday() >= 5 else "HOLIDAY"})
    csv_rows = ["session_date,open,high,low,close,volume"]
    for index, session in enumerate(schedule):
        price = round(100 + index * .1 + math.sin(index / 7) * 4, 4)
        csv_rows.append(f"{session['date']},{price},{price + 2},{price - 2},{price + .5},{1000 + index}")
    raw_csv = ("\n".join(csv_rows) + "\n").encode()
    def source(name, raw):
        return {"name": ("SYNTHETIC_TEST " if marked_synthetic else "QA simulated ordinary import ") + name,
                "reference": "urn:hakimi:qa:simulated-import:" + name,
                "retrieved_at": "2024-08-10T00:00:00Z", "raw_base64": base64.b64encode(raw).decode()}
    declaration = b"FICTIONAL QA ONLY: fabricated ordinary-import metadata, no source authentication or actual market evidence."
    manifest = {"schema_version": "us-equity-daily-import-v1",
        "security": {"security_id": "QA:SIMULATED:COMMON_STOCK", "symbol": "QADEMO", "exchange": "XNYS",
                     "currency": "USD", "instrument_type": "COMMON_STOCK"},
        "identity": {"stable_within_coverage": True, "valid_from": first.isoformat(), "valid_through": last.isoformat(),
                     "selection_basis": declaration.decode(), "source": source("identity", declaration)},
        "calendar": {"timezone": "America/New_York", "coverage_start": first.isoformat(), "coverage_end": last.isoformat(),
                     "source": source("calendar", json.dumps(days).encode()), "days": days},
        "corporate_actions": {"coverage_start": first.isoformat(), "coverage_end": last.isoformat(),
                              "coverage_status": "DECLARED_COMPLETE", "source": source("actions", declaration), "actions": []},
        "price_source": source("provider", raw_csv), "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares",
        "bar_timestamp_semantics": "SESSION_DATE", "completed_bars_only": True,
        "as_of": "2024-08-09T00:00:00Z", "retrieved_at": "2024-08-10T00:00:00Z",
        "bar_availability_lag_seconds": 60, "evidence_kind": "SYNTHETIC_TEST" if marked_synthetic else "IMPORTED_UNVERIFIED"}
    if manifest_mutator:
        manifest_mutator(manifest)
    return build_equity_snapshot(raw_csv, manifest).document


def write_core_import_qa_fixture(directory, *, marked_synthetic=False):
    """Write only to the caller's dedicated fixture directory; return its path."""
    root = Path(directory).absolute()
    if "research-workspace" in root.parts or root.name == "runtime":
        raise ValueError("qa_fixture_requires_separate_directory")
    root.mkdir(parents=True, exist_ok=True)
    path = root / ("qa-marked-synthetic-blocked.json" if marked_synthetic else "qa-simulated-ordinary-import.json")
    raw = json.dumps(build_core_import_qa_fixture(marked_synthetic=marked_synthetic), ensure_ascii=False, indent=2).encode("utf-8")
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("qa_fixture_existing_bytes_differ")
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return path


class Core:
    def __init__(self, root):
        self.workspace = root
        self.calls = []

    def read(self, resource, identity=None):
        self.calls.append(("read", resource, identity))
        if resource == "strategies":
            return {"items": [{"key": "price.dual_ma@1", "title": "Different crossover rule"}]}
        if resource == "runs":
            return {"summary": {"task_display_name": "core result", "task_version_number": 1,
                                "total_return": .02, "max_drawdown": .01, "total_fees": 2}, "configuration": {}}
        return {"resource": resource, "identity": identity}

    def mutate(self, action, payload):
        self.calls.append(("mutate", action, payload))
        return {"core_action": action, "payload": payload}


class TerminalResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-terminal-task-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.core = Core(self.root / "research-workspace")
        self.market = {"symbol": "SYNTH", "bar": "1D", "source_id": "terminal-cache:test-fixture",
                       "meta": {"asset_class": "EQUITY", "interval": "1D", "session": "REGULAR",
                                "price_basis": "UNKNOWN", "source_lineage": ["fixture-provider"], "origin_reference": "test", "volume_unit": "UNKNOWN"},
                       "quality": {"status": "REVIEW", "blockers": [], "warnings": ["unverified fixture"],
                                   "source_authenticated": False, "research_only": True, "core_us_equity_import_allowed": False},
                       "excluded_incomplete_count": 2,
                       "rows": [{"date": (date(2020, 1, 1) + timedelta(days=index)).isoformat(),
                                 "ts_ms": 1577836800000 + index * 86400000,
                                 "open": 10 + index, "high": 12 + index, "low": 9 + index, "close": 11 + index,
                                 "volume": 100, "complete": True, "provisional": False, "source": "fixture-provider"}
                                for index in range(100)]}
        self.market["digest"] = digest(self.market)
        self.reader = Mock(side_effect=lambda symbol, limit=2000, source_id=None: deepcopy(self.market))
        self.catalog = [{"id": "dual_ma", "name": "原双均线", "params": {"fast_window": 20, "slow_window": 60,
                         "position_pct": .25, "stop_loss_pct": .03},
                         "capability": {"known": True, "backtest_supported": True, "new_research_allowed": True}},
                        {"id": "trend_pullback", "name": "原历史策略", "params": {"window": 20},
                         "capability": {"known": True, "backtest_supported": True, "new_research_allowed": False}},
                        {"id": "grid", "name": "原网格", "params": {"lookback": 80},
                         "capability": {"known": True, "backtest_supported": False, "new_research_allowed": False}}]
        self.code_version = "fixed-code"
        self.fingerprint = lambda strategy, params: digest([strategy, params, self.code_version])
        self.runner = Mock(side_effect=self.fake_runner)
        self.history = Mock(return_value={"items": [{"id": "original-history", "report_hash": "retained"}], "warnings": []})
        self.service = TerminalResearchService(self.core, self.reader, lambda: deepcopy(self.catalog), self.runner,
                                              self.fingerprint, history_reader=self.history)

    @staticmethod
    def fake_runner(**kwargs):
        rows = kwargs["market_payload"]["rows"]
        curve = [{"date": row["date"], "ts_ms": row["ts_ms"], "equity": 10000 + index} for index, row in enumerate(rows[80:])]
        return {"ok": True, "trades": [{"date": rows[80]["date"], "side": "BUY"}], "equity_curve": curve,
                "order_event_count": 1, "evaluation_window": {"start_index": 80, "start": rows[80]["date"],
                                                             "end": rows[-1]["date"], "evaluated_rows": len(curve)},
                "total_return_pct": kwargs["position_pct"] / 10, "max_drawdown_pct": 1,
                "total_fees": 3, "final_equity": 10000 + kwargs["position_pct"]}

    def freeze(self):
        return self.service.mutate("terminal_freeze_market", {"symbol": "SYNTH", "limit": 2000, "expected_digest": self.market["digest"]})

    def task(self, **changes):
        data = self.freeze()
        payload = {"name": "原策略练习", "strategy_id": "dual_ma", "strategy_params": {"fast_window": 10, "slow_window": 40},
                   "input_id": data["id"], "risk": {"position_pct": 25, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1},
                   "costs": {"fee_rate": .0005, "slippage_bps": 2}}
        payload.update(changes)
        return self.service.mutate("terminal_save_task", payload)

    def run_task(self, task):
        return self.service.mutate("terminal_run_task", {"task_id": task["id"]})

    def test_reads_are_lazy_and_core_routes_pass_through(self):
        self.assertEqual(self.service.read("terminal_tasks")["items"], [])
        self.assertFalse(self.core.workspace.exists())
        self.assertEqual(self.service.read("status"), {"resource": "status", "identity": None})
        self.assertEqual(self.service.mutate("save_csv_template", {"name": "original"})["core_action"], "save_csv_template")
        self.assertFalse(self.core.workspace.exists())

    def test_catalog_keeps_distinct_engine_and_blocked_original_strategies(self):
        catalog = self.service.read("terminal_catalog")
        self.assertEqual([item["id"] for item in catalog["items"]], ["dual_ma", "trend_pullback", "grid"])
        self.assertEqual(catalog["core_items"][0]["key"], "price.dual_ma@1")
        item = catalog["items"][0]
        self.assertEqual(item["engine_id"], ENGINE_ID)
        self.assertIsNone(item["equivalent_core_strategy"])
        self.assertEqual(item["default_risk"]["take_profit_pct"], 0)
        self.assertEqual(item["default_risk"]["stop_loss_pct"], 8)
        self.assertFalse(self.core.workspace.exists())

    def test_freeze_requires_same_preview_digest_and_does_not_write_on_drift(self):
        with self.assertRaisesRegex(ValueError, "changed_preview"):
            self.service.mutate("terminal_freeze_market", {"symbol": "SYNTH", "expected_digest": "f" * 64})
        self.assertFalse(self.core.workspace.exists())

    def test_freeze_is_immutable_deduplicated_and_preserves_quality(self):
        first = self.freeze()
        path = self.core.workspace / "terminal-inputs" / (first["id"] + ".json")
        original = path.read_bytes()
        second = self.freeze()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(first["quality"]["status"], "REVIEW")
        self.assertFalse(first["quality"]["source_authenticated"])
        self.assertFalse(first["quality"]["core_us_equity_import_allowed"])
        self.assertEqual(first["excluded_incomplete_count"], 2)

    def test_incomplete_rows_are_excluded_with_retained_count(self):
        self.market["rows"][-1]["complete"] = False
        self.market["digest"] = digest({k: v for k, v in self.market.items() if k != "digest"})
        frozen = self.freeze()
        self.assertEqual(frozen["row_count"], 99)
        self.assertEqual(frozen["excluded_incomplete_count"], 3)
        self.assertTrue(all(row["complete"] for row in frozen["rows"]))

    def test_saved_parameters_and_risk_units_are_exact_and_not_core_mapping(self):
        task = self.task()
        self.assertEqual(task["strategy_id"], "dual_ma")
        self.assertEqual(task["strategy_params"]["fast_window"], 10)
        self.assertEqual(task["strategy_params"]["slow_window"], 40)
        self.assertEqual(task["risk"]["position_pct"], 25)
        self.assertEqual(task["risk"]["take_profit_pct"], 0)
        self.assertEqual(task["risk"]["stop_loss_pct"], 8)
        self.assertEqual(task["fingerprint"], self.fingerprint("dual_ma", task["strategy_params"]))
        self.assertEqual(task["version"], 1)
        self.runner.assert_not_called()

    def test_revision_preserves_old_version_and_paused_state(self):
        first = self.task()
        original_path = self.core.workspace / "terminal-tasks" / first["family_id"] / "versions" / (first["id"] + ".json")
        original = original_path.read_bytes()
        self.service.mutate("terminal_set_task_state", {"family_id": first["family_id"], "state": "PAUSED", "expected_task_id": first["id"]})
        second = self.task(parent_task_id=first["id"], strategy_params={"fast_window": 12, "slow_window": 45})
        self.assertEqual(second["family_id"], first["family_id"])
        self.assertEqual(second["version"], 2)
        self.assertEqual(second["state"], "PAUSED")
        self.assertEqual(original_path.read_bytes(), original)
        self.assertFalse(self.service.read("terminal_tasks", first["id"])["selected"])
        with self.assertRaisesRegex(ValueError, "paused"):
            self.run_task(second)
        with self.assertRaisesRegex(ValueError, "version_changed"):
            self.run_task(first)

    def test_run_receives_frozen_rows_parameters_risk_and_full_history(self):
        task = self.task()
        self.reader.reset_mock()
        self.market["rows"][0]["close"] = 999
        report = self.run_task(task)
        self.reader.assert_not_called()
        arguments = self.runner.call_args.kwargs
        self.assertEqual(arguments["strategy_params"], task["strategy_params"])
        self.assertEqual(arguments["position_pct"], 25)
        self.assertEqual(arguments["take_profit_pct"], 0)
        self.assertEqual(arguments["market_payload"]["source"], "fixture-provider")
        self.assertEqual(arguments["market_payload"]["source_id"], "terminal-cache:test-fixture")
        self.assertEqual(arguments["market_payload"]["rows"][0]["close"], 11)
        self.assertEqual(report["status"], "COMPLETED")
        self.assertEqual(report["evidence_status"], "UNVERIFIED")
        self.assertEqual(report["chart"]["rows"][0]["close"], 11)
        self.assertEqual(report["chart"]["source"], "FROZEN_RUN_INPUT")
        self.assertFalse(report["permissions"]["paper_authorized"])
        reopened = self.service.read("terminal_runs", report["id"])
        self.assertEqual(reopened["chart"], report["chart"])
        self.assertEqual(self.run_task(task)["new_economic_runs"], 0)
        self.runner.assert_called_once()

    def test_blocked_and_short_inputs_do_not_run(self):
        self.market["quality"]["status"] = "BLOCK"
        with self.assertRaisesRegex(ValueError, "market_blocked"):
            self.task()
        self.market["quality"]["status"] = "REVIEW"
        task = self.task()
        blocked = self.service._input(task["input_id"])
        blocked["quality"]["status"] = "BLOCK"
        with patch.object(self.service, "_input", return_value=blocked), self.assertRaisesRegex(ValueError, "input_blocked"):
            self.run_task(task)
        self.market["rows"] = self.market["rows"][:30]
        self.market["digest"] = digest(self.market["rows"])
        short = self.task()
        with self.assertRaisesRegex(ValueError, "warmup"):
            self.run_task(short)
        self.runner.assert_not_called()

    def test_falsified_and_unsupported_strategies_cannot_save_or_run(self):
        for identity in ("trend_pullback", "grid", "G50", "G51", "price.dual_ma@1"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.task(strategy_id=identity, strategy_params={})
        task = self.task()
        self.catalog[0]["capability"]["new_research_allowed"] = False
        with self.assertRaisesRegex(ValueError, "new_research_blocked"):
            self.run_task(task)
        self.runner.assert_not_called()

    def test_changed_implementation_blocks_before_started_record(self):
        task = self.task()
        self.code_version = "different-code"
        with self.assertRaisesRegex(ValueError, "implementation_changed"):
            self.run_task(task)
        self.assertFalse((self.core.workspace / "terminal-runs").exists())
        self.runner.assert_not_called()

    def test_callback_exception_is_unknown_and_never_replayed(self):
        task = self.task()
        self.runner.side_effect = RuntimeError("synthetic interruption")
        first = self.run_task(task)
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertFalse(first["automatic_retry"])
        self.assertEqual(self.run_task(task)["status"], "UNKNOWN")
        self.runner.assert_called_once()

    def test_unpublished_result_remains_unknown_without_rerun(self):
        task = self.task()
        original_write = self.service._write
        def fail_report(path, value):
            if path.name == "report.json":
                raise OSError("synthetic publication failure")
            original_write(path, value)
        with patch.object(self.service, "_write", side_effect=fail_report), self.assertRaises(OSError):
            self.run_task(task)
        resumed = self.run_task(task)
        self.assertEqual(resumed["status"], "UNKNOWN")
        self.assertFalse(resumed["automatic_retry"])
        self.runner.assert_called_once()

    def test_truncated_history_is_unknown_not_a_complete_replay(self):
        task = self.task()
        def truncated(**kwargs):
            result = self.fake_runner(**kwargs)
            result["equity_curve"] = result["equity_curve"][-2:]
            return result
        self.runner.side_effect = truncated
        report = self.run_task(task)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("history_truncated", report["error"])

    def test_tampered_input_is_rejected_without_execution(self):
        task = self.task()
        path = self.core.workspace / "terminal-inputs" / (task["input_id"] + ".json")
        value = json.loads(path.read_bytes())
        value["rows"][0]["close"] = 100
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed_or_schema"):
            self.run_task(task)
        self.runner.assert_not_called()

    def test_comparison_checks_frozen_conditions_and_keeps_engines_separate(self):
        first_task = self.task()
        first = self.run_task(first_task)
        second_task = self.task(parent_task_id=first_task["id"], risk={"position_pct": 10, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1})
        second = self.run_task(second_task)
        compared = self.service.mutate("terminal_compare", {"run_ids": [first["id"], second["id"]]})
        self.assertEqual(compared["status"], "COMPARABLE_CONDITIONS")
        self.assertEqual(compared["differences_from_first"][0]["total_return_pct"], -1.5)
        mixed = self.service.mutate("terminal_compare", {"run_ids": [first["id"], "a" * 24]})
        self.assertEqual(mixed["status"], "NOT_COMPARABLE")
        self.assertEqual(mixed["differences_from_first"], [])
        self.assertEqual(self.runner.call_count, 2)

    def test_original_history_is_read_through_without_resigning(self):
        view = self.service.read("terminal_history", "legacy-id")
        self.history.assert_called_once_with("legacy-id")
        self.assertEqual(view["items"][0]["report_hash"], "retained")
        self.assertFalse(self.core.workspace.exists())

    def test_original_report_files_are_read_through_without_resigning_or_workspace_writes(self):
        original = {"items": [{"id": "original-report", "file_sha256": "c" * 64}], "warnings": []}
        self.history.reports = Mock(return_value=original)
        self.assertIs(self.service.read("terminal_reports", "original-report"), original)
        self.history.reports.assert_called_once_with("original-report")
        self.assertFalse(self.core.workspace.exists())
        self.service.history_reader = None
        missing = self.service.read("terminal_reports")
        self.assertEqual(missing["items"], [])
        self.assertEqual(missing["warnings"], ["terminal_report_file_reader_unavailable"])

    def test_exact_source_selection_is_passed_and_never_substituted(self):
        self.service.read("terminal_market", "SYNTH/terminal-cache:test-fixture")
        self.reader.assert_called_with("SYNTH", limit=2000, source_id="terminal-cache:test-fixture")
        frozen = self.service.mutate("terminal_freeze_market", {"symbol": "SYNTH", "source_id": "terminal-cache:test-fixture",
                                                               "expected_digest": self.market["digest"]})
        self.assertEqual(frozen["source_id"], "terminal-cache:test-fixture")
        with self.assertRaisesRegex(ValueError, "source_selection_changed"):
            self.service.read("terminal_market", "SYNTH/different-source")
        self.market.update(source_id=None, rows=[])
        self.market["quality"] = {"status": "BLOCK", "blockers": ["selected_source_missing"]}
        preview = self.service.read("terminal_market", "SYNTH/missing-source")
        self.assertEqual(preview["quality"]["blockers"], ["selected_source_missing"])

    def test_marked_synthetic_and_preview_sources_cannot_freeze_or_reach_runner(self):
        for provider in ("synthetic", "yahoo:preview_seed", "offline-seed", "quick_preview"):
            with self.subTest(provider=provider):
                self.market["meta"]["source_lineage"] = [provider]
                for row in self.market["rows"]:
                    row["source"] = provider
                self.market["digest"] = digest({k: v for k, v in self.market.items() if k != "digest"})
                with self.assertRaisesRegex(ValueError, "synthetic_or_preview_source"):
                    self.freeze()
        self.runner.assert_not_called()
        self.assertFalse(self.core.workspace.exists())

    def test_existing_marked_seed_input_cannot_run_under_hashed_source_id(self):
        task = self.task()
        seed = self.service._input(task["input_id"])
        seed["source_id"] = "terminal-cache:" + "a" * 64
        seed["meta"]["source_lineage"] = ["preview_seed"]
        for row in seed["rows"]:
            row["source"] = "preview_seed"
        with patch.object(self.service, "_input", return_value=seed), self.assertRaisesRegex(ValueError, "synthetic_or_preview_source"):
            self.run_task(task)
        self.runner.assert_not_called()
        self.assertFalse((self.core.workspace / "terminal-runs").exists())

    def test_real_original_engine_accepts_full_synthetic_history_without_false_truncation(self):
        def pure_runner(**kwargs):
            return run_causal_long_only_backtest(rows=kwargs["market_payload"]["rows"], symbol=kwargs["symbol"],
                source=kwargs["market_payload"]["source"], signal_fn=build_strategy_signal_fn(kwargs["strategy_id"], kwargs["strategy_params"]),
                startup_candles=strategy_startup_candles_for_params(kwargs["strategy_id"], kwargs["strategy_params"]),
                position_pct=kwargs["position_pct"], take_profit_pct=kwargs["take_profit_pct"],
                stop_loss_pct=kwargs["stop_loss_pct"], leverage=kwargs["leverage"], fee_rate=kwargs["fee_rate"],
                slippage_bps=kwargs["slippage_bps"], market="crypto", timeframe="1D")
        self.runner.side_effect = pure_runner
        report = self.run_task(self.task())
        self.assertEqual(report["status"], "COMPLETED", report.get("error"))
        result = report["result"]
        self.assertEqual(result["order_event_count"], len(result["trades"]))
        self.assertEqual(result["evaluation_window"]["evaluated_rows"], len(result["equity_curve"]))
        self.assertGreater(len(result["trades"]), 0)
        self.assertEqual(len(report["chart"]["rows"]), 100)


class CoreInputReuseTests(unittest.TestCase):
    def setUp(self):
        from exchange_terminal.services.quant_workspace import _load_kernel
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-core-reference-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.core = _load_kernel().service(self.root / "research-workspace")
        self.runner = Mock(side_effect=AssertionError("import/list must not execute a strategy"))
        self.reader = Mock(side_effect=AssertionError("import must not read current market cache"))
        self.catalog = [{"id": "macd", "name": "MACD", "params": {},
                         "capability": {"backtest_supported": True, "new_research_allowed": True}}]
        self.service = TerminalResearchService(self.core, self.reader, lambda: self.catalog, self.runner,
                                               lambda strategy, params: digest([strategy, params]))

    def store(self, snapshot=None, *, name="input.json"):
        snapshot = snapshot if snapshot is not None else build_core_import_qa_fixture()
        path = self.core.workspace / "data" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        # Deliberately noncanonical spacing proves that retained evidence is the
        # exact original bytes, not a reserialized/re-signed core document.
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return path, self.core._id(path), snapshot

    def test_verified_import_preserves_original_bytes_and_same_rows_without_execution(self):
        path, identity, snapshot = self.store()
        raw = path.read_bytes()
        listed = self.service.read("terminal_core_inputs")["items"][0]
        self.assertTrue(listed["available"], listed["blockers"])
        self.assertEqual(listed["input_id"], identity)
        self.assertEqual(listed["snapshot_hash"], snapshot["snapshot_id"])
        self.assertEqual(listed["source_manifest_hash"], snapshot["raw_input"]["manifest_sha256"])
        self.assertGreaterEqual(listed["row_count"], 120)
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())
        frozen = self.service.mutate("terminal_import_core_input", {"input_id": identity})
        self.assertEqual(frozen["quality"]["status"], "REVIEW")
        self.assertFalse(frozen["quality"]["source_authenticated"])
        self.assertEqual(frozen["evidence_status"], "UNVERIFIED")
        self.assertEqual(frozen["source"], snapshot["price_source"]["name"])
        self.assertEqual(frozen["meta"]["calendar"], snapshot["calendar"])
        self.assertEqual(frozen["meta"]["security_identity"], snapshot["security_identity"])
        self.assertEqual(frozen["meta"]["corporate_actions"], snapshot["corporate_actions"])
        self.assertEqual([[row[k] for k in ("open", "high", "low", "close", "volume")] for row in frozen["rows"]],
                         [row[1:] for row in snapshot["candles"]])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual((self.core.workspace / frozen["core_reference"]["original_bytes_path"]).read_bytes(), raw)
        self.assertEqual(self.service.mutate("terminal_import_core_input", {"input_id": identity})["id"], frozen["id"])
        self.assertEqual(self.service.read("terminal_inputs", frozen["id"]), frozen)
        self.runner.assert_not_called()
        self.reader.assert_not_called()

    def test_marked_synthetic_and_disguised_seed_sources_remain_blocked(self):
        samples = [build_core_import_qa_fixture(marked_synthetic=True),
                   build_core_import_qa_fixture(manifest_mutator=lambda m: m["price_source"].update(reference="urn:local:preview_seed:prices")),
                   build_core_import_qa_fixture(manifest_mutator=lambda m: m["price_source"].update(name="offline-seed")),
                   build_core_import_qa_fixture(manifest_mutator=lambda m: m["security"].update(security_id="SYNTHETIC:FAKE"))]
        for index, sample in enumerate(samples):
            with self.subTest(index=index):
                _, identity, _ = self.store(sample, name=f"blocked-{index}.json")
                item = self.service.read("terminal_core_inputs", identity)["items"][0]
                self.assertFalse(item["available"])
                self.assertTrue(any("synthetic" in reason for reason in item["blockers"]))
                with self.assertRaisesRegex(ValueError, "core_input_blocked"):
                    self.service.mutate("terminal_import_core_input", {"input_id": identity})
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())
        self.runner.assert_not_called()

    def test_original_corporate_action_and_identity_admission_cannot_be_bypassed(self):
        def action(manifest):
            manifest["corporate_actions"]["actions"] = [{"action_id": "qa-action", "security_id": manifest["security"]["security_id"],
                "action_type": "SPLIT", "effective_date": "2024-03-01", "source_reference": "urn:qa:action", "details": {"ratio": 2}}]
        cases = [(lambda m: m["identity"].update(stable_within_coverage=False), "SECURITY_IDENTITY_NOT_STABLE"),
                 (lambda m: m["corporate_actions"].update(coverage_status="UNKNOWN"), "CORPORATE_ACTION_COVERAGE"),
                 (action, "CORPORATE_ACTION_ACCOUNTING")]
        for index, (mutator, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                _, identity, _ = self.store(build_core_import_qa_fixture(manifest_mutator=mutator), name=f"admission-{index}.json")
                item = self.service.read("terminal_core_inputs", identity)["items"][0]
                self.assertFalse(item["available"])
                self.assertTrue(any(reason in blocker for blocker in item["blockers"]))
                with self.assertRaisesRegex(ValueError, reason):
                    self.service.mutate("terminal_import_core_input", {"input_id": identity})
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())

    def test_declared_availability_after_next_open_is_blocked(self):
        sample = build_core_import_qa_fixture(manifest_mutator=lambda m: m.update(bar_availability_lag_seconds=24 * 3600))
        self.assertTrue(sample["research_admission"]["allowed"])
        _, identity, _ = self.store(sample)
        item = self.service.read("terminal_core_inputs")["items"][0]
        self.assertIn("core_bar_unavailable_before_next_open", item["blockers"])
        with self.assertRaisesRegex(ValueError, "bar_unavailable_before_next_open"):
            self.service.mutate("terminal_import_core_input", {"input_id": identity})
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())

    def test_core_verifier_rejects_tampered_prices_session_or_raw_manifest(self):
        for field in ("price", "session", "manifest"):
            sample = build_core_import_qa_fixture()
            if field == "price":
                sample["candles"][0][1] += .01
            elif field == "session":
                sample["sessions"][0]["open_utc"] = "2024-01-02T15:30:00Z"
            else:
                sample["raw_input"]["manifest_sha256"] = "f" * 64
            with self.subTest(field=field):
                _, identity, _ = self.store(sample, name=field + ".json")
                with self.assertRaisesRegex(ValueError, "content_or_receipt_mismatch"):
                    self.service.mutate("terminal_import_core_input", {"input_id": identity})
        listing = self.service.read("terminal_core_inputs")
        self.assertEqual(listing["items"], [])
        self.assertEqual(len(listing["warnings"]), 3)
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())
        self.runner.assert_not_called()

    def test_client_cannot_supply_rows_paths_or_snapshot_id_instead_of_opaque_id(self):
        path, identity, sample = self.store()
        for payload in ({"input_id": identity, "rows": []}, {"input_id": str(path)}, {"input_id": sample["snapshot_id"]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.service.mutate("terminal_import_core_input", payload)
        self.assertFalse((self.core.workspace / "terminal-inputs").exists())

    def test_retained_original_independent_of_latest_source_and_tamper_is_detected(self):
        path, identity, _ = self.store()
        frozen = self.service.mutate("terminal_import_core_input", {"input_id": identity})
        path.write_text('{"changed":true}', encoding="utf-8")
        self.assertEqual(self.service.read("terminal_inputs", frozen["id"])["rows"], frozen["rows"])
        retained = self.core.workspace / frozen["core_reference"]["original_bytes_path"]
        retained.write_bytes(retained.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "original_bytes_changed"):
            self.service.read("terminal_inputs", frozen["id"])
        self.runner.assert_not_called()

    def test_imported_fixture_runs_original_macd_with_exact_frozen_data_and_full_history(self):
        _, identity, _ = self.store()
        frozen = self.service.mutate("terminal_import_core_input", {"input_id": identity})
        task = self.service.mutate("terminal_save_task", {"name": "虚构QA模拟普通导入", "strategy_id": "macd",
            "input_id": frozen["id"], "strategy_params": {"fast": 12, "slow": 26, "signal": 9},
            "risk": {"position_pct": 25, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1},
            "costs": {"fee_rate": .0005, "slippage_bps": 2}})
        def pure_runner(**kwargs):
            self.assertEqual(kwargs["market_payload"]["rows"], frozen["rows"])
            self.assertEqual(kwargs["market_payload"]["source"], frozen["source"])
            return run_causal_long_only_backtest(rows=kwargs["market_payload"]["rows"], symbol=kwargs["symbol"],
                source=kwargs["market_payload"]["source"], signal_fn=build_strategy_signal_fn(kwargs["strategy_id"], kwargs["strategy_params"]),
                startup_candles=strategy_startup_candles_for_params(kwargs["strategy_id"], kwargs["strategy_params"]),
                position_pct=kwargs["position_pct"], take_profit_pct=kwargs["take_profit_pct"], stop_loss_pct=kwargs["stop_loss_pct"],
                leverage=kwargs["leverage"], fee_rate=kwargs["fee_rate"], slippage_bps=kwargs["slippage_bps"], market="stock", timeframe="1D")
        self.runner.side_effect = pure_runner
        run = self.service.mutate("terminal_run_task", {"task_id": task["id"]})
        self.assertEqual(run["status"], "COMPLETED", run.get("error"))
        self.assertEqual(run["chart"]["rows"], frozen["rows"])
        self.assertEqual(run["chart"]["input_id"], frozen["id"])
        self.assertEqual(run["result"]["order_event_count"], len(run["result"]["trades"]))
        self.assertGreater(run["result"]["order_event_count"], 0)
        self.reader.assert_not_called()

    def test_qa_file_helper_writes_only_separate_fixture_directory(self):
        path = write_core_import_qa_fixture(self.root / "fixtures")
        self.assertTrue(path.is_file())
        self.assertEqual(path, write_core_import_qa_fixture(self.root / "fixtures"))
        self.assertIn("FICTIONAL QA ONLY", path.read_text(encoding="utf-8"))
        marked = write_core_import_qa_fixture(self.root / "fixtures", marked_synthetic=True)
        self.assertEqual(json.loads(marked.read_bytes())["evidence_kind"], "SYNTHETIC_TEST")
        self.assertFalse(self.core.workspace.exists())
        with self.assertRaisesRegex(ValueError, "separate_directory"):
            write_core_import_qa_fixture(self.core.workspace)


class NativeParameterValidationTests(unittest.TestCase):
    def test_engine_clamps_and_defaulting_values_are_rejected(self):
        invalid = [("dual_ma", {"fast_window": 1}), ("dual_ma", {"fast_window": 60, "slow_window": 20}),
                   ("bollinger", {"window": 9}), ("bollinger", {"std_mult": .49}),
                   ("macd", {"fast": 1}), ("macd", {"fast": 30, "slow": 20}), ("macd", {"signal": 1}),
                   ("rsi", {"window": 4}), ("rsi", {"oversold": 0}), ("rsi", {"oversold": 80, "overbought": 70}),
                   ("momentum", {"window": 4}), ("momentum", {"threshold": 0}),
                   ("livermore", {"pivot_window": 19}), ("livermore", {"confirm_pct": 0}),
                   ("turtle", {"entry_window": 9}), ("turtle", {"exit_window": 4}),
                   ("darvas", {"box_window": 19}), ("darvas", {"confirm_pct": 0}),
                   ("volume_trend", {"volume_ratio": .49}), ("volume_trend", {"min_atr_pct": 0}),
                   ("volume_trend", {"min_atr_pct": .09, "max_atr_pct": .08}),
                   ("squeeze_breakout", {"atr_short_window": 48, "atr_long_window": 50}),
                   ("dual_ma", {"fast_window": True}), ("dual_ma", {"fast_window": 2.5})]
        for identity, values in invalid:
            with self.subTest(identity=identity, values=values), self.assertRaises(ValueError):
                validate_terminal_strategy_params({"id": identity, "params": {}}, values)

    def test_native_parameters_reach_actual_signal_without_silent_replacement(self):
        params = validate_terminal_strategy_params({"id": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}},
                                                   {"fast": 2, "slow": 3, "signal": 2})
        with patch("exchange_terminal.services.strategy_signals._macd_state", return_value=(1, 0, 2, 0)) as state:
            result = rolling_strategy_signal("macd", list(range(1, 101)), 100, False, params=params)
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(state.call_args.args[1:], (2, 3, 2))

    def test_omitted_signal_defaults_are_explicit_and_unused_metadata_is_not_editable(self):
        params = validate_terminal_strategy_params({"id": "volume_trend", "params": {"fast_window": 50, "position_pct": .22}}, {})
        self.assertEqual(params["fast_window"], 50)
        self.assertEqual(params["atr_window"], 14)
        self.assertEqual(params["min_atr_pct"], .01)
        self.assertEqual(params["position_pct"], .22)
        with self.assertRaisesRegex(ValueError, "legacy_metadata_not_signal"):
            validate_terminal_strategy_params({"id": "dual_ma", "params": {"position_pct": .25}}, {"position_pct": .5})

    def test_verified_core_chart_uses_retained_session_date_and_security_identity(self):
        snapshot = {"schema_version": "us-equity-daily-snapshot-v1", "market": "us_equity", "snapshot_id": "a" * 64,
                    "security": {"symbol": "TEST", "security_id": "retained-security", "exchange": "XNAS", "currency": "USD"},
                    "timezone": "America/New_York", "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares",
                    "sessions": [{"date": "2026-01-02", "open_utc": "2026-01-02T14:30:00Z"}],
                    "candles": [["2026-01-02T14:30:00Z", 10, 12, 9, 11, 100]]}
        fills = [{"fill_time": "2026-01-02 14:30:00+00:00", "action": "BUY", "price": 10, "filled_quantity": 2}]
        chart = _core_chart(snapshot, fills, run_id="run-1", report_hash="b" * 64)
        self.assertEqual(chart["rows"][0]["date"], snapshot["sessions"][0]["date"])
        self.assertEqual(chart["trades"][0]["date"], "2026-01-02")
        self.assertEqual(chart["trades"][0]["side"], "BUY")
        self.assertEqual(chart["meta"]["security_id"], "retained-security")
        self.assertEqual(chart["meta"]["price_basis"], "RAW_UNADJUSTED")
        self.assertEqual(chart["input_id"], snapshot["snapshot_id"])
        fills[0]["fill_time"] = "2026-01-03T14:30:00Z"
        with self.assertRaisesRegex(ValueError, "fill_session_binding"):
            _core_chart(snapshot, fills, run_id="run-1", report_hash="b" * 64)


if __name__ == "__main__":
    unittest.main()
