"""Temporary fictional data, in-memory HTTP handlers and no provider/server IO."""
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from email.message import Message
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.quant_workspace import QuantWorkspace
from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from exchange_terminal.services.terminal_public_daily_access import PublicDailyAccess, PublicDailyAccessError
from exchange_terminal.services.terminal_research import TerminalResearchService, _bytes, _seal
from hakimi_research import daily_updates, stock_intake
from tests.test_terminal_daily_research import fixtures, file_hashes
from tests.test_terminal_daily_bridge import fixture as bridge_fixture


class Handler:
    def __init__(self, owner, path, body=None, headers=None):
        self.command = "GET" if body is None else "POST"
        self.path = path
        self.server = SimpleNamespace(server_address=("127.0.0.1", 18765))
        self.client_address = ("127.0.0.1", 12345)
        self.headers = Message()
        defaults = {"Host": "127.0.0.1:18765", "Origin": "http://127.0.0.1:18765", "X-Hakimi-Token": owner._token}
        raw = b"" if body is None else json.dumps(body).encode()
        if body is not None:
            defaults.update({"Content-Type": "application/json", "Content-Length": str(len(raw))})
        defaults.update(headers or {})
        for key, value in defaults.items():
            if value is not None:
                self.headers[key] = value
        self.rfile, self.wfile = BytesIO(raw), BytesIO()
        self.connection = SimpleNamespace(settimeout=lambda _: None)
        self.status = None

    def send_response(self, status): self.status = status
    def send_header(self, *unused): pass
    def end_headers(self): pass
    def json(self): return json.loads(self.wfile.getvalue())


class DailyIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-daily-integration-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / "new-workspace"
        self.now = daily_updates._clock("2026-10-23T21:00:00Z")
        data = fixtures()
        _, _, _, first, latest = stock_intake._coverage(self.now, 20, "XNYS")
        response = data.source_reply((date.fromisoformat(first) - timedelta(days=120)).isoformat(), latest)
        response["chart"]["result"][0]["meta"].update(dataGranularity="1d", longName="Fictional integration Corporation")
        self.reply = data.encoded(response)
        self.transport = Mock(return_value=self.reply)
        self.runner = Mock(side_effect=AssertionError("No economic run"))
        self.core = SimpleNamespace(workspace=self.workspace, read=Mock(), mutate=Mock())
        self.service = TerminalResearchService(self.core, Mock(), lambda: [], self.runner, Mock(),
            daily_factory=lambda workspace, fetcher: TerminalDailyResearch(workspace, fetcher=fetcher, clock=lambda: self.now))
        self.module = QuantWorkspace(self.root / "runtime", public_daily_fetcher=self.transport)
        self.service.configure_public_daily_access(self.module._public_daily, self.module._token)
        self.addCleanup(self.service.close)
        forbidden = patch("hakimi_research.daily_updates._fetch", side_effect=AssertionError("No real source"))
        forbidden.start(); self.addCleanup(forbidden.stop)
        economics = patch("hakimi_research.workbench_service.run_task", side_effect=AssertionError("No automatic economic run"))
        economics.start(); self.addCleanup(economics.stop)
        self.sequence = 0

    def request(self, path, body=None, headers=None):
        handler = Handler(self.module, path, body, headers)
        self.assertTrue(self.module.handle(handler))
        return handler.status, handler.json()

    def payload(self, **values):
        self.sequence += 1
        return dict(operation_id="integration-op-%04d" % self.sequence, **values)

    def grant(self, action, payload):
        code, result = self.request("/api/quant/public-daily-access/allow-once", dict(action=action, payload=payload))
        self.assertEqual(code, 200, result)
        return result["data"]

    def initial(self):
        payload = self.payload(symbol="TEST", history_sessions=20)
        self.grant("terminal_daily_check_stock", payload)
        checked = self.service.mutate("terminal_daily_check_stock", payload)
        self.assertEqual(checked["status"], "REVIEW_REQUIRED")
        self.assertEqual(checked["public_daily_request"]["actual_attempts"], 1)
        saved = self.service.mutate("terminal_daily_save_stock", self.payload(intake_id=checked["id"],
            expected_check_hash=checked["check_hash"], confirmed_security=checked["security"]))
        self.assertEqual(saved["action_status"], "STOCK_INPUT_SAVED")
        return checked, saved

    def test_lazy_reads_and_controls_do_not_create_writer_or_expose_session(self):
        self.assertIsNone(self.service._daily_backend)
        self.assertEqual(self.service.read("terminal_daily_inputs")["items"], [])
        self.assertIsNone(self.service._daily_backend._writer)
        self.assertIsNone(self.service._execution_service)
        self.assertFalse(self.workspace.exists())
        self.module._ensure = Mock(side_effect=AssertionError("Control must not initialize jobs"))
        code, result = self.request("/api/quant/public-daily-access")
        self.assertEqual((code, result["data"]["state"]), (200, "DISABLED"))
        self.assertNotIn(self.module._token, json.dumps(result))
        self.grant("terminal_daily_check_stock", self.payload(symbol="TEST", history_sessions=20))
        self.assertEqual(self.request("/api/quant/public-daily-access/revoke", {})[0], 200)
        self.module._ensure.assert_not_called()
        self.transport.assert_not_called()
        self.assertFalse(self.module.runtime_dir.exists())

    def test_boundary_exact_payload_readonly_and_ungranted_job_fail_before_dispatch(self):
        payload = self.payload(symbol="TEST", history_sessions=20)
        body = dict(action="terminal_daily_check_stock", payload=payload)
        self.module._ensure = Mock(side_effect=AssertionError("Must not initialize jobs"))
        for headers in ({"Origin": "https://foreign.invalid"}, {"X-Hakimi-Token": "foreign"}, {"Origin": None}):
            self.assertEqual(self.request("/api/quant/public-daily-access/allow-once", body, headers)[0], 403)
        self.assertEqual(self.request("/api/quant/actions/terminal_daily_check_stock", {"request_id": "daily-job-0001", "payload": payload})[0], 403)
        code, result = self.request("/api/quant/public-daily-access/allow-once", {**body, "action": "terminal_run_task"})
        self.assertEqual((code, result["error"]["code"]), (403, "PUBLIC_DAILY_ACTION_NOT_ALLOWED"))
        self.assertEqual(self.request("/api/quant/public-daily-access/allow-once", {**body, "session": "foreign"})[0], 400)
        self.grant(body["action"], payload)
        self.module.read_only = True
        self.assertEqual(self.request("/api/quant/public-daily-access/allow-once", body)[0], 423)
        self.assertEqual(self.request("/api/quant/public-daily-access/revoke", {})[0], 200)
        self.module._ensure.assert_not_called()
        self.transport.assert_not_called()

    def test_real_check_save_update_and_unchanged_freeze_need_only_check_grants(self):
        checked, saved = self.initial()
        retained = self.service.read("terminal_daily_intakes", checked["id"])
        self.assertEqual(retained["public_daily_request"]["actual_attempts"], 1)
        self.assertEqual(retained["public_daily_request_scope"], "CURRENT_SESSION_ACTUAL_TRANSPORT")
        listed = self.service.read("terminal_daily_intakes")["items"]
        self.assertEqual(next(row for row in listed if row["id"] == checked["id"])["public_daily_request"]["actual_attempts"], 1)
        self.assertEqual(self.transport.call_count, 1)
        protected = file_hashes(self.service._daily().root / "data")
        payload = self.payload(input_id=saved["id"])
        self.grant("terminal_daily_check_update", payload)
        update = self.service.mutate("terminal_daily_check_update", payload)
        self.assertEqual(update["status"], "UNCHANGED")
        self.assertEqual(file_hashes(self.service._daily().root / "data"), protected)
        before = file_hashes(self.workspace)
        frozen = self.service.mutate("terminal_daily_freeze_update", self.payload(update_id=update["id"], expected_check_hash=update["check_hash"]))
        self.assertEqual(frozen["adoption_status"], "UNCHANGED_NO_NEW_VERSION")
        self.assertEqual(file_hashes(self.workspace), before)
        self.assertEqual(self.transport.call_count, 2)
        self.runner.assert_not_called()

    def test_actual_jobs_bind_session_and_transport_once_without_a_server(self):
        def factory(core):
            return TerminalResearchService(core, Mock(), lambda: [], self.runner, Mock(),
                daily_factory=lambda workspace, fetcher: TerminalDailyResearch(workspace, fetcher=fetcher, clock=lambda: self.now))
        self.module = QuantWorkspace(self.root / "job-runtime", public_daily_fetcher=self.transport, service_factory=factory)
        self.addCleanup(self.module.close)
        payload = self.payload(symbol="TEST", history_sessions=20)
        self.grant("terminal_daily_check_stock", payload)
        self.assertFalse(self.module.initialized)
        code, result = self.request("/api/quant/actions/terminal_daily_check_stock",
                                    {"request_id": "daily-job-through-0001", "payload": payload})
        self.assertEqual(code, 202, result)
        self.module._jobs.close()  # Join only this private test worker; no listener exists.
        job = self.module._jobs.get("daily-job-through-0001")
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(job["result"]["status"], "REVIEW_REQUIRED")
        self.assertIs(self.module._service._daily_access, self.module._public_daily)
        self.assertEqual(self.transport.call_count, 1)
        code, read = self.request("/api/quant/terminal_daily_intakes/" + job["result"]["id"])
        self.assertEqual(code, 200, read)
        self.assertEqual(read["data"]["public_daily_request"]["actual_attempts"], 1)
        code, replay = self.request("/api/quant/actions/terminal_daily_check_stock",
                                    {"request_id": "daily-job-through-0002", "payload": payload})
        self.assertEqual((code, replay["error"]["code"]), (403, "PUBLIC_DAILY_PERMISSION_CONSUMED"))
        self.assertEqual(self.transport.call_count, 1)
        self.runner.assert_not_called()

    def test_candidate_read_checks_current_source_but_historical_read_survives(self):
        self.module._ensure = Mock()
        self.module._service = SimpleNamespace(read=Mock(return_value={"items": []}))
        guard = Mock(return_value={"schema_version": "hakimi-runtime-build-v1", "status": "RESTART_REQUIRED", "restart_required": True})
        self.module._mutation_guard = guard
        code, rejected = self.request("/api/quant/terminal_strategy_candidates/%7B%7D")
        self.assertEqual(code, 400)
        self.assertIn("source_changed_restart_required", rejected["error"]["detail"])
        self.module._service.read.assert_not_called()
        code, historical = self.request("/api/quant/terminal_runs")
        self.assertEqual((code, historical["data"]), (200, {"items": []}))
        guard.assert_called_once()
        guard.return_value = {"schema_version": "hakimi-runtime-build-v1", "status": "PASS", "restart_required": False}
        self.assertEqual(self.request("/api/quant/terminal_strategy_candidates/%7B%7D")[0], 200)
        self.module._service.read.assert_called_with("terminal_strategy_candidates", "{}")
        self.transport.assert_not_called()

    def test_revoked_queued_request_is_known_zero_request_refusal_and_not_regrantable(self):
        payload = self.payload(symbol="TEST", history_sessions=20)
        self.grant("terminal_daily_check_stock", payload)
        self.request("/api/quant/public-daily-access/revoke", {})
        result = self.service.mutate("terminal_daily_check_stock", payload)
        self.assertEqual(result["status"], "PUBLIC_DAILY_REQUEST_REFUSED")
        self.assertEqual(result["public_daily_request"]["actual_attempts"], 0)
        self.assertFalse(result["public_daily_request"]["operation_in_flight"])
        self.assertFalse(self.workspace.exists())
        self.transport.assert_not_called()
        self.assertEqual(self.request("/api/quant/public-daily-access/allow-once", dict(action="terminal_daily_check_stock", payload=payload))[0], 403)
        self.grant("terminal_daily_check_stock", self.payload(symbol="TEST", history_sessions=20))

    def test_revoke_does_not_wait_for_inflight_service_lock_and_does_not_claim_cancellation(self):
        entered, release = threading.Event(), threading.Event()
        def transport(_url):
            entered.set()
            if not release.wait(5): raise RuntimeError("test transport release missing")
            return self.reply
        self.transport.side_effect = transport
        payload = self.payload(symbol="TEST", history_sessions=20)
        self.grant("terminal_daily_check_stock", payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            work = pool.submit(self.service.mutate, "terminal_daily_check_stock", payload)
            try:
                self.assertTrue(entered.wait(3))
                revoke = pool.submit(self.request, "/api/quant/public-daily-access/revoke", {})
                code, response = revoke.result(timeout=1)
                self.assertEqual((code, response["data"]["state"]), (200, "REVOKED_IN_FLIGHT"))
                self.assertFalse(response["data"]["request_cancellation_supported"])
                self.assertFalse(work.done())
            finally:
                release.set()
            result = work.result(timeout=5)
        self.assertTrue(result["public_daily_request"]["revoked"])
        self.assertEqual(result["public_daily_request"]["actual_attempts"], 1)
        self.assertEqual(result["public_daily_request"]["outcome"], "COMPLETED_AFTER_REVOCATION")

    def test_bridge_keeps_exact_originals_idempotent_and_readback_revalidates(self):
        from hakimi_research.input_workflow import _retain
        raw, snapshot, identity = bridge_fixture()
        _retain(self.workspace / "daily", raw)
        original_before = file_hashes(self.workspace / "daily")
        imported = self.service.mutate("terminal_import_daily_input", {"input_id": identity})
        self.assertEqual(imported["status"], "IMPORTED")
        self.assertRegex(imported["input_id"], r"^[a-f0-9]{64}$")
        original = self.workspace / "terminal-inputs" / "daily-originals" / (sha256(raw).hexdigest() + ".json")
        self.assertEqual(original.read_bytes(), raw)
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.workspace.rglob("*") if p.is_file()}
        self.assertEqual(self.service.mutate("terminal_import_daily_input", {"input_id": identity}), imported)
        self.service.read("terminal_inputs", imported["input_id"])
        self.assertEqual({str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.workspace.rglob("*") if p.is_file()}, before)
        self.assertEqual(file_hashes(self.workspace / "daily"), original_before)
        original.write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "original_bytes_changed"):
            self.service.read("terminal_inputs", imported["input_id"])
        self.transport.assert_not_called(); self.runner.assert_not_called()

    def test_bridge_resealed_reference_cannot_redirect_read_or_enter_core_namespace(self):
        from hakimi_research.input_workflow import _retain
        raw, _, identity = bridge_fixture()
        _retain(self.workspace / "daily", raw)
        imported = self.service.mutate("terminal_import_daily_input", {"input_id": identity})
        path = self.workspace / "terminal-inputs" / (imported["input_id"] + ".json")
        record = json.loads(path.read_bytes())
        record["daily_reference"]["original_bytes_path"] = "../must-not-read.json"
        changed = _seal({key: value for key, value in record.items() if key != "id"})
        (path.parent / (changed["id"] + ".json")).write_bytes(_bytes(changed))
        with self.assertRaisesRegex(ValueError, "daily_reference_changed"):
            self.service.read("terminal_inputs", changed["id"])
        self.core.mutate.assert_not_called()
        self.assertFalse((self.workspace / "data").exists())

    def test_bridge_failed_receipt_preserves_one_original_and_retry_does_not_rewrite(self):
        from hakimi_research.input_workflow import _retain
        raw, _, identity = bridge_fixture()
        _retain(self.workspace / "daily", raw)
        with patch.object(self.service, "_write", side_effect=OSError("synthetic publication failure")):
            with self.assertRaisesRegex(OSError, "synthetic publication failure"):
                self.service.mutate("terminal_import_daily_input", {"input_id": identity})
        originals = self.workspace / "terminal-inputs" / "daily-originals"
        paths = list(originals.iterdir())
        self.assertEqual(len(paths), 1)
        original = paths[0]
        before = (original.read_bytes(), original.stat().st_mtime_ns)
        self.assertEqual(before[0], raw)
        imported = self.service.mutate("terminal_import_daily_input", {"input_id": identity})
        self.assertEqual(imported["status"], "IMPORTED")
        self.assertEqual(list(originals.iterdir()), paths)
        self.assertEqual((original.read_bytes(), original.stat().st_mtime_ns), before)
        self.transport.assert_not_called(); self.runner.assert_not_called()

    def test_service_close_preserves_execution_close_and_revokes_daily_grants(self):
        execution = Mock()
        self.service._execution_service = execution
        self.grant("terminal_daily_check_stock", self.payload(symbol="TEST", history_sessions=20))
        self.service.close()
        execution.close.assert_called_once()
        self.assertTrue(self.module._public_daily.status()["closed"])
        self.assertEqual(self.module._public_daily.status()["unconsumed_authorizations"], 0)


class LegacyLocalOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).resolve().parents[1] / "exchange_terminal/server.py"
        cls.tree = ast.parse(cls.path.read_text(encoding="utf-8"))

    def functions(self, names, namespace):
        selected = [node for node in self.tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in selected}, set(names))
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(self.path), "exec"), namespace)

    def test_all_legacy_network_wrappers_refuse_local_mode_before_transport(self):
        names = {"_require_legacy_market_network", "read_bodyless_okx", "read_signed_okx", "okx_first", "okx_rows", "okx_rows_with_error", "binance_daily_history"}
        transport = Mock(side_effect=AssertionError("No legacy network"))
        namespace = {"LOCAL_ONLY": True, "Any": object, "read_bodyless_okx_io": transport,
                     "okx_first_io": transport, "okx_rows_io": transport, "okx_rows_with_error_io": transport}
        self.functions(names, namespace)
        for name in names - {"_require_legacy_market_network"}:
            with self.subTest(name=name), self.assertRaisesRegex(PermissionError, "LOCAL_ONLY_MARKET_NETWORK_BLOCKED"):
                namespace[name]("TEST", {}) if name != "binance_daily_history" else namespace[name]("TEST")
        transport.assert_not_called()
        namespace["LOCAL_ONLY"] = False
        transport.side_effect = None; transport.return_value = {"cached": False}
        self.assertEqual(namespace["read_bodyless_okx"]("/api/v5/market/ticker", {}), {"cached": False})
        transport.assert_called_once()

    def test_six_http_routes_block_with_zero_attempts_and_cached_read_stays_available(self):
        handler_class = next(node for node in self.tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeTerminalHandler")
        method = next(node for node in handler_class.body if isinstance(node, ast.FunctionDef) and node.name == "handle_api")
        responses = []
        cached = {"rows": [{"date": "FICTIONAL"}], "source": "local-cache"}
        namespace = {"LOCAL_ONLY": True, "Any": object, "RETIRED_MANAGEMENT_PATHS": frozenset(),
            "json_response": lambda handler, value, status=200: responses.append((status, value)),
            "archived_execution_route_state": lambda *args: "READ", "read_local_btc_daily": lambda limit: cached,
            "QUANT_WORKSPACE": Mock(), "read_bodyless_okx": Mock(side_effect=AssertionError("No legacy network"))}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(self.path), "exec"), namespace)
        for route in ("candles", "history-candles", "ticker", "tickers", "index-tickers", "trades"):
            namespace["handle_api"](SimpleNamespace(command="GET"), "/api/okx/" + route, {})
            self.assertEqual((responses[-1][0], responses[-1][1]["request_attempts"]), (423, 0))
        namespace["handle_api"](SimpleNamespace(command="GET"), "/api/local/btc-daily", {})
        self.assertEqual(responses[-1], (200, cached))
        namespace["read_bodyless_okx"].assert_not_called()

    def test_current_banner_changes_do_not_rewrite_archived_locks_or_permissions(self):
        namespace = {}
        self.functions({"current_product_copy"}, namespace)
        static = self.path.parent / "static"
        index = namespace["current_product_copy"]("index.html", (static / "index.html").read_bytes()).decode()
        app = namespace["current_product_copy"]("app.js", (static / "app.js").read_bytes()).decode()
        self.assertIn("本地合成演练", index)
        self.assertIn("公开日线仅在明确点击检查时获取", index)
        self.assertIn("本地研究 / 合成演练 · 外部券商与实盘未开启", app)
        self.assertIn("只读观察 · 模拟未授权 · 实盘永久硬锁", app)
        self.assertIn("模拟运行（未授权）· 实盘下单（永久硬锁）", index)


if __name__ == "__main__":
    unittest.main()
