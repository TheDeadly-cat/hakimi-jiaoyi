"""Real local HTTP/locking with fake economics and temporary workspaces only."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.services import quant_workspace as quant


class Service:
    def __init__(self, workspace):
        self.workspace = workspace
        self.calls = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def read(self, resource, identity=None):
        return {"resource": resource, "identity": identity, "workspace": str(self.workspace),
                "execution_permission": {"research_only": True, "live_order_allowed": False}}

    def mutate(self, action, payload):
        self.calls.append((action, payload))
        self.entered.set()
        if not self.release.wait(5):
            raise RuntimeError("test_release_not_received")
        return {"fake_operation": True, "new_economic_runs": 0}


class QuantWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before = list(sys.path)
        cls.kernel = quant._load_kernel()
        if sys.path != before:
            raise AssertionError("kernel loader changed global dependency search paths")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-quant-integration-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = quant.QuantWorkspace(self.root / "runtime")
        self.fake_kernel = SimpleNamespace(root=self.kernel.root, desktop=self.kernel.desktop,
                                           service=Service, version=self.kernel.version)
        self.loader = patch.object(quant, "_load_kernel", return_value=self.fake_kernel)
        self.loader_mock = self.loader.start()
        self.addCleanup(self.loader.stop)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if not owner.module.handle(self):
                    self.send_response(404)
                    self.end_headers()

            do_POST = do_GET
            do_OPTIONS = do_GET

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        if self.module._service is not None:
            self.module._service.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        deadline = time.monotonic() + 3
        while self.module.pending and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.module.close())

    def request(self, path, body=None, *, headers=(), method=None, raw=None, length=None):
        method = method or ("POST" if body is not None or raw is not None else "GET")
        if raw is None and body is not None:
            raw = json.dumps(body).encode()
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.putrequest(method, path, skip_host=True)
        supplied = {key.lower() for key, _ in headers}
        standard = [("Host", self.origin.removeprefix("http://")), ("Origin", self.origin),
                    ("X-Hakimi-Token", self.module._token)]
        if raw is not None or length is not None:
            standard += [("Content-Type", "application/json"),
                         ("Content-Length", str(len(raw or b"") if length is None else length))]
        for key, value in standard:
            if key.lower() not in supplied:
                connection.putheader(key, value)
        for key, value in headers:
            connection.putheader(key, value)
        # Keep these small fixture headers/body in one send. Otherwise an early
        # header rejection can close the socket before http.client sends its
        # separate body chunk, replacing the 400/403 response with a Windows RST.
        send = connection.send
        chunks = []
        connection.send = chunks.append
        try:
            connection.endheaders(raw)
        finally:
            connection.send = send
        send(b"".join(chunks))
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def load(self):
        status, _, _ = self.request("/api/quant/status")
        self.assertEqual(status, 200)
        return self.module._service

    def terminal(self, request_id):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            result = self.module._jobs.get(request_id)
            if result["status"] not in {"queued", "running"}:
                return result
            time.sleep(.01)
        self.fail("job did not reach terminal status")

    def test_constructor_and_unrelated_routes_do_not_load_or_create_workspace(self):
        self.assertFalse(self.module.initialized)
        self.assertFalse(self.module.pending)
        self.assertEqual(self.request("/api/health")[0], 404)
        self.loader_mock.assert_not_called()
        self.assertFalse(self.module.runtime_dir.exists())

    def test_original_source_guard_blocks_new_jobs_but_keeps_history_readable(self):
        service = self.load()
        for observation in (None, {}, {"schema_version": "capability-v1", "status": "PASS", "restart_required": False},
                            {"schema_version": "hakimi-runtime-build-v1", "status": "BLOCK", "restart_required": True}):
            self.module._mutation_guard = lambda value=observation: value
            status, _, raw = self.request("/api/quant/actions/create_task", {"request_id": "guard-gated-request", "payload": {}})
            self.assertEqual(status, 400)
            self.assertIn("source_changed_restart_required", raw.decode())
            self.assertFalse(self.module.pending)
            self.assertEqual(self.request("/api/quant/tasks")[0], 200)
        self.assertEqual(service.calls, [])
        self.module._mutation_guard = lambda: {"schema_version": "hakimi-runtime-build-v1", "status": "PASS", "restart_required": False}
        self.assertEqual(self.request("/api/quant/actions/create_task", {"request_id": "guard-gated-request", "payload": {}})[0], 202)
        self.assertEqual(self.terminal("guard-gated-request")["status"], "succeeded")
        self.assertEqual(len(service.calls), 1)

    def test_exact_security_boundaries_precede_loading_and_writes(self):
        request = {"request_id": "quant-protected-request", "payload": {}}
        cases = [
            [("Origin", "http://foreign.invalid")],
            [("Origin", self.origin), ("Origin", self.origin)],
            [("Origin", "")],
            [("Host", "evil.invalid")],
            [("Host", self.origin[7:]), ("Host", self.origin[7:])],
            [("X-Hakimi-Token", "wrong")],
            [("X-Hakimi-Token", self.module._token), ("X-Hakimi-Token", self.module._token)],
            [("Sec-Fetch-Site", "cross-site")],
            [("Sec-Fetch-Site", "same-origin"), ("Sec-Fetch-Site", "same-origin")],
        ]
        for headers in cases:
            with self.subTest(headers=[key for key, _ in headers]):
                self.assertEqual(self.request("/api/quant/actions/create_task", request, headers=headers)[0], 403)
        self.loader_mock.assert_not_called()
        self.assertFalse(self.module.runtime_dir.exists())

    def test_same_origin_page_adapts_all_three_features_without_mutating_kernel(self):
        source = self.kernel.root / "resources" / "desktop.html"
        before = sha256(source.read_bytes()).hexdigest()
        status, headers, raw = self.request("/quant/", headers=[("X-Hakimi-Token", "")])
        html = raw.decode()
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("frame-ancestors 'self'", headers["Content-Security-Policy"])
        self.assertIn("<title>量化任务与回测 · 哈基米交易</title>", html)
        for feature in ("save_csv_template", "prepare_teaching_examples", "configuration_differences_from_first"):
            self.assertIn(feature, html)
        self.assertIn("fetch('/api/quant/'+path", html)
        self.assertIn("document.currentScript?.remove()", html)
        self.assertEqual(html.count(self.module._token), 1)
        self.assertNotIn("hakimi-local-token", html)
        self.assertNotIn('class="brand"', html)
        self.assertEqual(sha256(source.read_bytes()).hexdigest(), before)
        self.assertNotIn(self.module._token, str(headers))

    def test_status_has_single_authoritative_workspace_and_no_secret(self):
        status, headers, raw = self.request("/api/quant/status")
        value = json.loads(raw)["data"]
        self.assertEqual(status, 200)
        self.assertEqual(Path(value["workspace"]).resolve(), (self.root / "runtime" / "research-workspace").resolve())
        self.assertEqual(Path(value["product_workspace"]).resolve(), (self.root / "runtime").resolve())
        self.assertEqual(value["version"], "0.5.0.dev8")
        self.assertTrue(value["session"]["embedded"])
        self.assertTrue(value["execution_permission"]["research_only"])
        self.assertFalse(value["execution_permission"]["live_order_allowed"])
        self.assertNotIn(self.module._token.encode(), raw)
        self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_read_only_allows_reads_but_rejects_actions_before_loading(self):
        self.module.read_only = True
        self.assertEqual(self.request("/api/quant/actions/create_task", {"request_id": "readonly-request-0001", "payload": {}})[0], 423)
        self.loader_mock.assert_not_called()
        self.assertEqual(self.request("/api/quant/tasks")[0], 200)
        self.assertFalse(self.module.workspace.exists())
        self.assertEqual(self.module._service.calls, [])

    def test_invalid_lengths_types_and_nonfinite_json_never_dispatch(self):
        request = b'{"request_id":"invalid-request-0001","payload":{}}'
        cases = [
            # Invalid framing is refused before body reads. Do not race an
            # unread body against the server's early close on Windows TCP.
            dict(raw=b"", length=len(request), headers=[("Content-Length", str(len(request))), ("Content-Length", str(len(request)))]),
            dict(raw=b"", length=len(request), headers=[("Transfer-Encoding", "chunked")]),
            dict(raw=b"", length=len(request), headers=[("Content-Type", "application/json"), ("Content-Type", "application/json")]),
            dict(raw=b'{"request_id":"invalid-request-0001","payload":{"number":NaN}}'),
            dict(raw=b'{"request_id":"invalid-request-0001","payload":{"number":1e309}}'),
            dict(raw=b'{"request_id":"invalid-request-0001","payload":{},"payload":{}}'),
        ]
        for case_index, kwargs in enumerate(cases):
            with self.subTest(case=case_index, kwargs=list(kwargs)):
                self.assertEqual(self.request("/api/quant/actions/create_task", **kwargs)[0], 400)
        self.assertEqual(self.request("/api/quant/actions/create_task", method="POST", length=quant.MAX_REQUEST + 1)[0], 413)
        self.loader_mock.assert_not_called()

    def test_request_identity_and_serial_jobs_are_preserved(self):
        service = self.load()
        service.release.clear()
        body = {"request_id": "quant-concurrent-request", "payload": {"x": 1}}
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.request("/api/quant/actions/run_task", body), range(2)))
        self.assertEqual([result[0] for result in responses], [202, 202])
        self.assertTrue(service.entered.wait(2))
        self.assertEqual(len(service.calls), 1)
        self.assertEqual(self.request("/api/quant/actions/run_task", dict(body, payload={"x": 2}))[0], 400)
        service.release.set()
        self.assertEqual(self.terminal(body["request_id"])["status"], "succeeded")
        self.assertEqual(self.request("/api/quant/actions/run_task", body)[0], 202)
        self.assertEqual(len(service.calls), 1)
        self.assertNotIn("request", self.terminal(body["request_id"]))

    def test_close_refuses_live_work_and_success_prevents_future_submission(self):
        service = self.load()
        service.release.clear()
        body = {"request_id": "quant-close-request-0001", "payload": {}}
        self.assertEqual(self.request("/api/quant/actions/run_task", body)[0], 202)
        self.assertTrue(service.entered.wait(2))
        self.assertTrue(self.module.pending)
        self.assertFalse(self.module.close())
        self.assertTrue(self.module.initialized)
        service.release.set()
        self.terminal(body["request_id"])
        # A saved result can precede the worker finally releasing ownership.
        deadline = time.monotonic() + 3
        while self.module.pending and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(self.module.pending, "worker did not release job ownership")
        self.assertTrue(self.module.close())
        self.assertFalse(self.module.initialized)
        self.assertEqual(self.request("/api/quant/actions/run_task", dict(body, request_id="quant-close-request-0002"))[0], 400)
        self.assertEqual(len(service.calls), 1)

    def test_workspace_lock_prevents_a_second_owner(self):
        self.load()
        other = quant.QuantWorkspace(self.module.runtime_dir)
        self.addCleanup(other.close)
        with self.assertRaisesRegex(RuntimeError, "workspace_already_open"):
            other._ensure()
        self.assertFalse(other.initialized)

    def test_unknown_retained_jobs_are_not_replayed(self):
        service = self.load()
        identity = "quant-retained-request-0001"
        request = {"action": "run_task", "payload": {}}
        record = {"job_id": identity, "action": "run_task", "status": "running", "request": {},
                  "request_sha256": sha256(self.kernel.desktop.encode(request)).hexdigest()}
        path = self.module._jobs.directory / (identity + ".json")
        original = json.dumps(record).encode()
        path.write_bytes(original)
        status, _, raw = self.request("/api/quant/actions/run_task", {"request_id": identity, "payload": {}})
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(raw)["data"]["status"], "unknown")
        self.assertEqual(service.calls, [])
        self.assertEqual(path.read_bytes(), original)

    def test_query_tokens_and_unknown_routes_do_not_reach_service(self):
        self.assertEqual(self.request("/quant/?token=untrusted")[0], 400)
        self.assertEqual(self.request("/api/quant/shutdown", {}, method="POST")[0], 404)
        self.loader_mock.assert_not_called()
        self.assertEqual(self.request("/api/quant/not_a_resource")[0], 404)
        self.assertEqual(self.module._service.calls, [])

    def test_accepted_package_rejects_changed_source_before_import(self):
        vendor = self.root / "vendor"
        shutil.copytree(self.kernel.root, vendor / "hakimi_terminal_research", ignore=shutil.ignore_patterns("__pycache__"))
        target = vendor / "hakimi_terminal_research" / "desktop_service.py"
        target.write_bytes(target.read_bytes() + b"\n# changed\n")
        with self.assertRaisesRegex(ValueError, "source_identity_mismatch"):
            quant._verified_package_root(vendor)


if __name__ == "__main__":
    unittest.main()
