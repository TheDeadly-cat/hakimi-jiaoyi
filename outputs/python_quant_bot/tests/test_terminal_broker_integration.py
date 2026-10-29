"""Real authenticated handler and candidate storage; no server or broker IO."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from email.message import Message
from io import BytesIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote

from exchange_terminal.services import quant_workspace as quant
from exchange_terminal.services.terminal_research import TerminalResearchService
from exchange_terminal.services.terminal_broker_candidate_service import PERMISSIONS
from tests.test_terminal_broker_candidate_service import RESOLUTION, REF, SIM


class BrokerIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="broker-route-new-fixture-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.guard = Mock(return_value={"schema_version": "hakimi-runtime-build-v1", "status": "PASS", "restart_required": False})
        self.shell = quant.QuantWorkspace(self.root / "runtime", mutation_guard=self.guard)
        core = SimpleNamespace(workspace=self.shell.workspace)
        self.runner = Mock(side_effect=AssertionError("No research runs in router tests"))
        self.service = TerminalResearchService(core, Mock(), lambda: [], self.runner, Mock())
        self.shell._kernel, self.shell._service = SimpleNamespace(), self.service
        self.jobs = Mock()
        # The handler remains real. This immediate job stub only delegates the
        # normal action; durable Jobs semantics have their separate suite.
        self.jobs.submit.side_effect = lambda action, body, identity: {
            "job_id": identity, "status": "succeeded", "result": self.service.mutate(action, body)}
        self.shell._jobs = self.jobs
        self.addCleanup(self.service.close)
        self.network = patch("socket.socket.connect", side_effect=AssertionError("No external calls")).start()
        self.addCleanup(patch.stopall)

    def request(self, route, body=None, *, token=True, origin=True, raw=None, content_type="application/json"):
        headers = Message()
        headers["Host"] = "127.0.0.1:54999"
        if token:
            headers["X-Hakimi-Token"] = self.shell._token
        if origin:
            headers["Origin"] = "http://127.0.0.1:54999"
        method = "GET" if body is None and raw is None else "POST"
        encoded = raw if raw is not None else json.dumps(body).encode() if method == "POST" else b""
        if method == "POST":
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(encoded))
        handler = SimpleNamespace(path="/api/quant/" + route, command=method, headers=headers,
            server=SimpleNamespace(server_address=("127.0.0.1", 54999)), client_address=("127.0.0.1", 12000),
            connection=Mock(), rfile=BytesIO(encoded), wfile=BytesIO(),
            send_header=lambda *_: None, end_headers=lambda: None)
        handler.send_response = lambda status: setattr(handler, "status", status)
        self.assertTrue(self.shell.handle(handler))
        return handler.status, json.loads(handler.wfile.getvalue())

    def read(self, resource, identity=None):
        suffix = "" if identity is None else "/" + quote(json.dumps(identity), safe="")
        return self.request(resource + suffix)

    def inventory(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def stop(self, identity="stop-route-request-1"):
        return self.request("broker-candidate/stop", {"mode": SIM, "request_id": identity, "reason": "Explicit local fixture stop"})

    def test_status_and_unknown_receipt_are_lazy_read_only(self):
        before = self.inventory()
        code, response = self.read("terminal_broker_status")
        self.assertEqual(code, 200)
        self.assertEqual(response["data"]["permissions"], PERMISSIONS)
        self.assertEqual(response["data"]["connection_state"], "NOT_CONNECTED")
        code, receipt = self.read("terminal_broker_receipt", {"mode": SIM, "request_id": "never-started-0001"})
        self.assertEqual(code, 200)
        self.assertEqual(receipt["data"]["status"], "NOT_RECORDED")
        self.assertFalse(receipt["data"]["retry_allowed"])
        self.assertEqual(before, self.inventory())
        self.assertFalse(self.service._broker().root.exists())
        self.jobs.submit.assert_not_called()
        self.runner.assert_not_called()
        self.network.assert_not_called()

    def test_saved_candidate_binds_trusted_resolver_and_reads_immutable_receipt(self):
        with patch("exchange_terminal.services.terminal_saved_results.resolve_execution_research",
                   return_value=deepcopy(RESOLUTION)) as resolver:
            payload = {"mode": SIM, "request_id": "candidate-route-save-1", "config": {}, "research_reference": REF}
            code, response = self.request("actions/terminal_broker_save_candidate", {"payload": payload, "request_id": "outer-job-1"})
            self.assertEqual(code, 202, response)
            saved = response["data"]["result"]
            self.assertEqual(saved["status"], "SAVED_OFFLINE_CANDIDATE")
            resolver.assert_called_once_with(self.service, REF)
        before = self.inventory()
        code, response = self.read("terminal_broker_check", {"mode": SIM, "config_id": saved["config_id"]})
        self.assertEqual(code, 200)
        self.assertEqual(response["data"]["status"], "MISSING")
        self.assertFalse(response["data"]["account_verified"])
        code, receipt = self.read("terminal_broker_receipt", {"mode": SIM, "request_id": payload["request_id"]})
        self.assertEqual(code, 200)
        self.assertEqual(receipt["data"]["receipt"]["action"], "save")
        self.assertEqual(before, self.inventory())
        self.assertEqual(self.service._broker().root, self.shell.workspace / "broker-candidates-v2")
        self.assertEqual(self.read("terminal_broker_check", {"mode": SIM, "config_id": saved["config_id"], "submit_allowed": True})[0], 400)

    def test_stop_bypasses_research_and_shell_mutex_and_changed_source_guard(self):
        self.read("terminal_broker_status")
        self.guard.return_value = {"status": "RESTART_REQUIRED", "restart_required": True}
        with ThreadPoolExecutor(max_workers=1) as worker:
            with self.shell._mutex, self.service._lock:
                code, response = worker.submit(self.stop).result(timeout=2)
        self.assertEqual(code, 200, response)
        result = response["data"]
        self.assertEqual(result["status"], "STOPPED")
        self.assertFalse(result["broker_orders_cancelled"])
        self.assertEqual(result["permissions"], PERMISSIONS)
        self.jobs.submit.assert_not_called()
        self.guard.assert_not_called()
        code, receipt = self.read("terminal_broker_receipt", {"mode": SIM, "request_id": "stop-route-request-1"})
        self.assertEqual(code, 200)
        self.assertEqual(receipt["data"]["receipt"]["id"], result["stop_receipt_id"])

    def test_resume_requires_current_stop_and_remains_offline(self):
        stopped = self.stop()[1]["data"]
        wrong = {"mode": SIM, "request_id": "resume-route-wrong-1", "expected_stop_receipt_id": "f" * 64, "reason": "Explicit resume"}
        self.assertEqual(self.request("actions/terminal_broker_resume", {"payload": wrong, "request_id": "outer-wrong"})[0], 400)
        payload = {**wrong, "request_id": "resume-route-valid-1", "expected_stop_receipt_id": stopped["stop_receipt_id"]}
        code, response = self.request("actions/terminal_broker_resume", {"payload": payload, "request_id": "outer-resume"})
        self.assertEqual(code, 202, response)
        self.assertEqual(response["data"]["result"]["status"], "OFFLINE_PREPARATION_RESUMED")
        self.assertEqual(response["data"]["result"]["permissions"], PERMISSIONS)
        self.network.assert_not_called()

    def test_stop_auth_read_only_and_body_contracts_do_not_write(self):
        payload = {"mode": SIM, "request_id": "stop-boundary-0001", "reason": "test"}
        for options in ({"token": False}, {"origin": False}, {"content_type": "text/plain"}):
            before = self.inventory()
            code, _ = self.request("broker-candidate/stop", payload, **options)
            self.assertIn(code, {400, 403})
            self.assertEqual(before, self.inventory())
        self.shell.read_only = True
        self.assertEqual(self.request("broker-candidate/stop", payload)[0], 423)
        self.shell.read_only = False
        self.assertEqual(self.request("broker-candidate/stop", raw=b'{"mode":"OFFICIAL_SIMULATION","mode":"LIVE_CANDIDATE"}')[0], 400)
        self.assertEqual(self.inventory(), {})

    def test_unavailable_and_job_stop_never_claim_success(self):
        self.assertEqual(self.request("actions/terminal_broker_stop", {"payload": {}, "request_id": "queued-stop-1"})[0], 400)
        self.jobs.submit.assert_not_called()
        self.shell._service = None
        self.assertEqual(self.stop()[0], 400)
        self.assertEqual(self.inventory(), {})


if __name__ == "__main__":
    unittest.main()
