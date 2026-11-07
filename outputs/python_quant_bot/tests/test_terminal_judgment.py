"""Offline tests for additive judgment receipts and frozen replay."""
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import indicator_math
from exchange_terminal.services import terminal_research as research
from exchange_terminal.services.terminal_research import TerminalResearchService, _seal
from exchange_terminal.services.quant_workspace import _READ_RESOURCES


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


class Core:
    def __init__(self, workspace):
        self.workspace = workspace

    def read(self, resource, identity=None):
        return {"resource": resource, "identity": identity}

    def mutate(self, action, payload):
        return {"action": action, "payload": payload}


class TerminalJudgmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-judgment-offline-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.core = Core(self.root / "research-workspace")
        rows = []
        for index in range(100):
            session = (date(2020, 1, 1) + timedelta(days=index)).isoformat()
            rows.append({"date": session, "ts_ms": 1577836800000 + index * 86400000,
                         "open": 100.0 + index, "high": 102.0 + index,
                         "low": 99.0 + index, "close": 101.0 + index,
                         "volume": 1000.0 + index, "complete": True,
                         "provisional": False, "source": "qa-claimed-provider"})
        self.market = {"symbol": "QADEMO", "bar": "1D", "source_id": "qa-local-source",
                       "meta": {"asset_class": "EQUITY", "interval": "1D", "session": "REGULAR",
                                "price_basis": "RAW", "source_lineage": ["qa-claimed-provider"],
                                "origin_reference": "urn:qa:judgment", "volume_unit": "shares"},
                       "quality": {"status": "REVIEW", "blockers": [], "warnings": ["QA only"],
                                   "source_authenticated": False, "research_only": True,
                                   "core_us_equity_import_allowed": False},
                       "excluded_incomplete_count": 0, "rows": rows}
        self.market["digest"] = digest(self.market)
        self.reader = Mock(side_effect=lambda symbol, limit=2000, source_id=None: deepcopy(self.market))
        self.catalog = lambda: [{"id": "dual_ma", "name": "Original MA", "params": {"fast_window": 20,
                          "slow_window": 60}, "capability": {"known": True, "backtest_supported": True,
                          "new_research_allowed": True}}]
        self.fingerprint = lambda strategy, params: digest({"strategy": strategy, "params": params})
        self.service = self.new_service()

    def new_service(self):
        return TerminalResearchService(self.core, self.reader, self.catalog, self.runner, self.fingerprint)

    @staticmethod
    def runner(**kwargs):
        rows = kwargs["market_payload"]["rows"]
        curve = [{"date": row["date"], "ts_ms": row["ts_ms"], "equity": 10000 + index}
                 for index, row in enumerate(rows[80:])]
        return {"ok": True, "trades": [{"date": rows[80]["date"], "side": "BUY",
                 "price": rows[80]["open"], "quantity": 1, "reason": "QA"}],
                "equity_curve": curve, "order_event_count": 1,
                "evaluation_window": {"evaluated_rows": len(curve)},
                "total_return_pct": 1, "max_drawdown_pct": 1}

    def frozen(self):
        return self.service.mutate("terminal_freeze_market", {"symbol": "QADEMO", "limit": 2000,
            "source_id": "qa-local-source", "expected_digest": self.market["digest"]})

    def task(self, frozen):
        return self.service.mutate("terminal_save_task", {"name": "QA judgment task",
            "strategy_id": "dual_ma", "strategy_params": {"fast_window": 10, "slow_window": 40},
            "input_id": frozen["id"], "risk": {"position_pct": 25, "take_profit_pct": 0,
            "stop_loss_pct": 8, "leverage": 1}, "costs": {"fee_rate": .0005, "slippage_bps": 2}})

    def payload(self, frozen, *, binding=None, request_id="create-judgment-0001"):
        return {"client_request_id": request_id, "input_id": frozen["id"],
                "binding": binding or {"kind": "terminal_input", "id": frozen["id"]},
                "direction": "WAIT", "as_of": frozen["date_end"],
                "thesis": "等待结构确认；这是事后录入的研究观察。",
                "trigger_condition": "日线收盘站上前高后再观察。",
                "invalidation_condition": "跌破观察区则作废。",
                "counter_evidence": ["成交量尚未确认"]}

    def test_create_reopen_seals_values_without_recalculation_or_old_file_changes(self):
        frozen = self.frozen()
        task = self.task(frozen)
        run = self.service.mutate("terminal_run_task", {"task_id": task["id"]})
        original_paths = [self.core.workspace / "terminal-inputs" / (frozen["id"] + ".json"),
                          self.core.workspace / "terminal-tasks" / task["family_id"] / "versions" / (task["id"] + ".json"),
                          self.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"]
        before = [path.read_bytes() for path in original_paths]
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen,
            binding={"kind": "terminal_run", "id": run["id"]}))
        self.assertEqual(created["status"], "RECORDED")
        self.assertEqual(created["binding"]["engine_id"], run["engine_id"])
        self.assertEqual(created["indicator_snapshot"]["contract"], indicator_math.CONTRACT)
        self.assertEqual(created["indicator_snapshot"]["provenance"], "INDEPENDENT_INDICATOR_MATH")
        self.assertEqual(created["indicator_snapshot"]["source_sha256"], indicator_math.LOADED_SOURCE_SHA256)
        self.assertAlmostEqual(created["indicator_snapshot"]["values"]["sma"], 190.5)
        self.assertEqual(created["recorded_at"], created["created_at"])
        self.assertEqual(before, [path.read_bytes() for path in original_paths])
        reopened = self.new_service()
        with patch.object(indicator_math, "sma", side_effect=AssertionError("historical read recalculated")):
            detail = reopened.read("terminal_judgments", created["id"])
        self.assertEqual(detail["indicator_snapshot"], created["indicator_snapshot"])
        self.assertEqual(detail["input_summary"]["input_id"], frozen["id"])
        self.assertEqual(detail["task_configuration"]["engine_id"], run["engine_id"])
        self.assertEqual(detail["run_summary"]["report_hash"], run["report_hash"])
        self.assertEqual(reopened.read("terminal_judgments")["items"][0]["id"], created["id"])

    def test_historical_as_of_seals_only_the_known_prefix_and_replays_no_future_rows(self):
        frozen = self.frozen()
        historical_date = self.market["rows"][40]["date"]
        payload = {**self.payload(frozen, request_id="historical-as-of-0001"), "as_of": historical_date}
        created = self.service.mutate("terminal_save_judgment", payload)
        expected_rows = frozen["rows"][:41]
        self.assertEqual(created["prefix_row_count"], 41)
        self.assertEqual(created["prefix_rows_hash"], digest(expected_rows))
        self.assertEqual(created["indicator_snapshot"]["bar_date"], historical_date)
        self.assertEqual(created["indicator_snapshot"]["prefix_rows_hash"], digest(expected_rows))
        self.assertAlmostEqual(created["indicator_snapshot"]["values"]["sma"], 131.5)
        self.assertEqual(created["recording_relation"], "RECORDED_AFTER_AS_OF")
        self.assertGreater(created["recorded_at"][:10], created["as_of"])
        chart = self.service.read("terminal_judgment_replay", created["id"])
        self.assertEqual(len(chart["rows"]), 41)
        self.assertEqual(chart["rows"][-1]["date"], historical_date)
        with patch.object(indicator_math, "sma", side_effect=AssertionError("historical read recalculated")):
            detail = self.new_service().read("terminal_judgments", created["id"])
        self.assertEqual(detail["status"], "RECORDED")
        self.assertEqual(detail["prefix_summary"]["row_count"], 41)

    def test_as_of_can_be_between_sessions_and_uses_last_available_completed_bar(self):
        missing_session = self.market["rows"][41]["date"]
        del self.market["rows"][41]
        self.market["digest"] = digest({key: value for key, value in self.market.items() if key != "digest"})
        frozen = self.frozen()
        created = self.service.mutate("terminal_save_judgment", {**self.payload(frozen,
            request_id="between-sessions-0001"), "as_of": missing_session})
        self.assertEqual(created["as_of"], missing_session)
        self.assertEqual(created["prefix_row_count"], 41)
        self.assertEqual(created["indicator_snapshot"]["bar_date"], self.market["rows"][40]["date"])
        self.assertEqual(len(self.service.read("terminal_judgment_replay", created["id"])["rows"]), 41)

    def test_changed_indicator_source_blocks_new_receipt_before_any_judgment_write(self):
        frozen = self.frozen()
        with patch.object(indicator_math, "assert_loaded_source_current",
                          side_effect=ValueError("indicator_source_changed_restart_required")):
            with self.assertRaisesRegex(ValueError, "indicator_source_changed_restart_required"):
                self.service.mutate("terminal_save_judgment", self.payload(frozen))
        self.assertFalse((self.core.workspace / "terminal-judgments").exists())
        self.assertFalse((self.core.workspace / "terminal-judgment-requests").exists())

    def test_task_and_input_bindings_replay_exact_frozen_rows_without_invented_run(self):
        frozen = self.frozen()
        task = self.task(frozen)
        for index, binding in enumerate(({"kind": "terminal_input", "id": frozen["id"]},
                                          {"kind": "terminal_task", "id": task["id"]})):
            created = self.service.mutate("terminal_save_judgment", self.payload(frozen,
                binding=binding, request_id=f"create-judgment-{index:04d}"))
            chart = self.service.read("terminal_judgment_replay", created["id"])
            self.assertTrue(chart["available"])
            self.assertEqual(chart["source"], "JUDGMENT_FROZEN_INPUT")
            self.assertEqual(chart["input_id"], frozen["id"])
            self.assertEqual(len(chart["rows"]), frozen["row_count"])
            self.assertEqual(chart["trades"], [])
            self.assertNotIn("run_id", chart)
            self.assertNotIn("report_hash", chart)
            self.assertEqual(chart["record_hash"], created["id"])

    def test_readable_v6_task_retains_old_engine_identity_with_new_independent_indicator_values(self):
        frozen = self.frozen()
        current = self.task(frozen)
        original = self.service._task_record(current["id"])
        legacy_body = {key: deepcopy(value) for key, value in original.items() if key != "id"}
        legacy_body["engine_id"] = "terminal.causal-long-only-signals-v6"
        legacy_body["engine_source_identity"] = {"archived": "a" * 64}
        legacy = _seal(legacy_body)
        family_root = self.core.workspace / "terminal-tasks" / current["family_id"]
        self.service._write(family_root / "versions" / (legacy["id"] + ".json"), legacy)
        event_path = family_root / "journal" / "000001.json"
        old_event = json.loads(event_path.read_bytes())
        new_event = _seal({**{key: value for key, value in old_event.items() if key != "id"},
                           "task_id": legacy["id"]})
        event_path.write_bytes(json.dumps(new_event, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")).encode("utf-8"))
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen,
            binding={"kind": "terminal_task", "id": legacy["id"]}, request_id="old-v6-judgment-0001"))
        self.assertEqual(created["binding"]["engine_id"], "terminal.causal-long-only-signals-v6")
        self.assertEqual(created["task_configuration"]["engine_source_identity"], {"archived": "a" * 64})
        self.assertEqual(created["indicator_snapshot"]["provenance"], "INDEPENDENT_INDICATOR_MATH")
        self.assertEqual(self.new_service().read("terminal_judgments", created["id"])["status"], "RECORDED")

    def test_v6_run_can_be_bound_without_rewriting_or_upgrading_its_old_report(self):
        frozen = self.frozen()
        old_sources = research._engine_source_identity()
        old_sources.pop("indicator_math.py", None)
        ordinary_seal = research._seal
        def legacy_seal(value, key="id"):
            value = deepcopy(value)
            if value.get("schema_version") == "hakimi-terminal-task-v1":
                value.pop("indicator_contract", None)
            return ordinary_seal(value, key)
        with patch.object(research, "ENGINE_ID", "terminal.causal-long-only-signals-v6"), \
             patch.object(research, "_seal", legacy_seal), \
             patch.object(research, "_engine_source_identity", return_value=old_sources):
            task = self.task(frozen)
            run = self.service.mutate("terminal_run_task", {"task_id": task["id"]})
        old_report = self.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"
        original_bytes = old_report.read_bytes()
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen,
            binding={"kind": "terminal_run", "id": run["id"]}, request_id="old-v6-run-judgment-0001"))
        self.assertEqual(created["status"], "RECORDED")
        self.assertEqual(created["binding"]["engine_id"], "terminal.causal-long-only-signals-v6")
        self.assertNotIn("indicator_contract", created["task_configuration"])
        self.assertEqual(created["indicator_snapshot"]["contract"], indicator_math.CONTRACT)
        self.assertEqual(old_report.read_bytes(), original_bytes)
        self.assertEqual(self.new_service().read("terminal_judgments", created["id"])["status"], "RECORDED")

    def test_event_chain_is_append_only_idempotent_and_optimistically_serialized(self):
        frozen = self.frozen()
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen))
        payload = {"client_request_id": "event-judgment-0001", "judgment_id": created["id"],
                   "expected_head": None, "event_type": "OBSERVATION",
                   "as_of": frozen["date_end"], "note": "继续等待。"}
        first = self.service.mutate("terminal_append_judgment_event", payload)
        self.assertEqual(first["event_count"], 1)
        self.assertEqual(self.service.mutate("terminal_append_judgment_event", payload)["head"], first["head"])
        with self.assertRaisesRegex(ValueError, "request_id_conflict"):
            self.service.mutate("terminal_append_judgment_event", {**payload, "note": "同 id 不同内容"})
        with self.assertRaisesRegex(ValueError, "head_changed"):
            self.service.mutate("terminal_append_judgment_event", {**payload,
                "client_request_id": "event-judgment-0002", "event_type": "TRIGGERED"})
        second = self.service.mutate("terminal_append_judgment_event", {**payload,
            "client_request_id": "event-judgment-0003", "expected_head": first["head"],
            "event_type": "USER_ACTION", "note": "用户声明曾手动观察，未核验订单。"})
        self.assertEqual(second["event_count"], 2)
        self.assertEqual(second["events"][1]["previous_hash"], first["head"])
        self.assertEqual(second["events"][1]["action_verification"], "USER_REPORTED_UNVERIFIED")
        self.assertFalse(second["events"][1]["order_authorized"])

    def test_create_idempotency_and_pending_intent_are_visible_without_automatic_retry(self):
        frozen = self.frozen()
        payload = self.payload(frozen)
        original_write = self.service._write
        def interrupted(path, value):
            if Path(path).name == "record.json":
                raise OSError("QA interrupted after durable intent")
            return original_write(path, value)
        with patch.object(self.service, "_write", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "QA interrupted"):
                self.service.mutate("terminal_save_judgment", payload)
        pending = self.service.read("terminal_judgments")["items"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["status"], "UNKNOWN")
        self.assertEqual(pending[0]["client_request_id"], payload["client_request_id"])
        self.assertFalse(pending[0]["automatic_retry"])
        recovered = self.service.mutate("terminal_save_judgment", payload)
        self.assertEqual(recovered["status"], "RECORDED")
        self.assertEqual(recovered["id"], self.service.mutate("terminal_save_judgment", payload)["id"])
        self.assertEqual(self.service.read("terminal_judgments")["items"][0]["client_request_id"], payload["client_request_id"])
        with self.assertRaisesRegex(ValueError, "request_id_conflict"):
            self.service.mutate("terminal_save_judgment", {**payload, "thesis": "different"})

    def test_missing_or_tampered_retained_evidence_is_unknown_and_unreplayed(self):
        frozen = self.frozen()
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen))
        detail = self.service.mutate("terminal_append_judgment_event", {
            "client_request_id": "event-judgment-0010", "judgment_id": created["id"],
            "expected_head": None, "event_type": "OBSERVATION", "as_of": frozen["date_end"], "note": "QA"})
        event_path = (self.core.workspace / "terminal-judgments" / created["id"] / "events" / "000001.json")
        event_path.write_bytes(event_path.read_bytes().replace(b'"QA"', b'"QX"'))
        unknown = self.service.read("terminal_judgments", created["id"])
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertFalse(self.service.read("terminal_judgment_replay", created["id"])["available"])
        self.assertEqual(detail["head"], detail["events"][0]["id"])

    def test_missing_frozen_input_does_not_silently_rebuild_from_current_market(self):
        frozen = self.frozen()
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen))
        self.reader.reset_mock()
        (self.core.workspace / "terminal-inputs" / (frozen["id"] + ".json")).unlink()
        reopened = self.new_service()
        self.assertEqual(reopened.read("terminal_judgments", created["id"])["status"], "UNKNOWN")
        self.assertFalse(reopened.read("terminal_judgment_replay", created["id"])["available"])
        self.reader.assert_not_called()

    def test_interrupted_event_retains_unknown_until_explicit_same_request_recovery(self):
        frozen = self.frozen()
        created = self.service.mutate("terminal_save_judgment", self.payload(frozen))
        payload = {"client_request_id": "event-pending-0001", "judgment_id": created["id"],
                   "expected_head": None, "event_type": "OBSERVATION",
                   "as_of": frozen["date_end"], "note": "QA pending event"}
        original_write = self.service._write
        def interrupted(path, value):
            if Path(path).name == "000001.json":
                raise OSError("QA event publication interrupted")
            return original_write(path, value)
        with patch.object(self.service, "_write", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "event publication interrupted"):
                self.service.mutate("terminal_append_judgment_event", payload)
        unknown = self.service.read("terminal_judgments", created["id"])
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertFalse(self.service.read("terminal_judgment_replay", created["id"])["available"])
        recovered = self.service.mutate("terminal_append_judgment_event", payload)
        self.assertEqual(recovered["status"], "RECORDED")
        self.assertEqual(recovered["events"][0]["client_request_id"], payload["client_request_id"])

    def test_mismatched_and_future_contaminated_bindings_do_not_write(self):
        frozen = self.frozen()
        task = self.task(frozen)
        other = self.frozen()
        # A separate immutable input with different completed rows is still a different identity.
        changed = deepcopy(self.market)
        changed["rows"][-1]["close"] += 0.5
        changed["digest"] = digest({key: value for key, value in changed.items() if key != "digest"})
        self.reader.side_effect = lambda symbol, limit=2000, source_id=None: deepcopy(changed)
        other = self.service.mutate("terminal_freeze_market", {"symbol": "QADEMO", "limit": 2000,
            "source_id": "qa-local-source", "expected_digest": changed["digest"]})
        with self.assertRaisesRegex(ValueError, "binding_input_mismatch"):
            self.service.mutate("terminal_save_judgment", self.payload(other,
                binding={"kind": "terminal_task", "id": task["id"]}, request_id="bad-binding-0001"))
        with self.assertRaisesRegex(ValueError, "as_of_outside_frozen_coverage"):
            self.service.mutate("terminal_save_judgment", {**self.payload(frozen,
                request_id="bad-date-0001"), "as_of": "2019-12-31"})
        with self.assertRaisesRegex(ValueError, "as_of_outside_frozen_coverage"):
            self.service.mutate("terminal_save_judgment", {**self.payload(frozen,
                request_id="bad-date-0002"), "as_of": "2021-01-01"})
        self.assertEqual(len(self.service.read("terminal_judgments")["items"]), 0)
        self.assertEqual(other["symbol"], frozen["symbol"])

    def test_core_run_binding_requires_exact_imported_snapshot_identity(self):
        frozen = self.frozen()
        native = self.service._input(frozen["id"])
        native["core_reference"] = {"snapshot_hash": "snapshot-1"}
        native["meta"]["core_snapshot_id"] = "snapshot-1"
        fake_replay = {"snapshot": {"snapshot_id": "snapshot-1"}, "symbol": "QADEMO",
                       "configuration": {"strategy": "core"}, "engine_id": "research.accepted-equity",
                       "task_id": "core-task", "run_id": "core-run", "report_hash": "core-report"}
        with patch.object(self.service, "_core_replay", return_value=fake_replay):
            receipt, config, _ = self.service.judgments._binding({"kind": "core_run", "id": "a" * 24}, native)
            self.assertEqual(receipt["core_snapshot_id"], "snapshot-1")
            self.assertEqual(config, fake_replay["configuration"])
            native["meta"]["core_snapshot_id"] = "different"
            with self.assertRaisesRegex(ValueError, "core_run_input_mismatch"):
                self.service.judgments._binding({"kind": "core_run", "id": "a" * 24}, native)

    def test_read_routes_exist_and_read_only_listing_creates_no_artifacts(self):
        self.assertIn("terminal_judgments", _READ_RESOURCES)
        self.assertIn("terminal_judgment_replay", _READ_RESOURCES)
        self.assertEqual(self.service.read("terminal_judgments"), {"items": [], "warnings": [], "new_economic_runs": 0})
        self.assertFalse(self.core.workspace.exists())


if __name__ == "__main__":
    unittest.main()
