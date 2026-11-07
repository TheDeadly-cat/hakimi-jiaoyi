"""Authenticated dispatch and independent replay controls; no broker or server.

The replay API is a spy here: ledger/admission behavior has its own real-store
suite. These checks exercise the actual terminal service and HTTP handler.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import Mock
import unittest
from urllib.parse import quote

from tests import test_terminal_broker_integration as handler_fixture


class ReplayRouteTests(unittest.TestCase):
    request = handler_fixture.BrokerIntegrationTests.request

    def setUp(self):
        handler_fixture.BrokerIntegrationTests.setUp(self)
        self.api = Mock()
        self.service._replay_api = self.api
        self.account = "replay-route-fixture"
        self.payload = {"account_id": self.account, "request_id": "pause-fixture-001",
                        "expected_head": "a" * 64, "reason": "明确暂停"}

    def test_read_resources_dispatch_only_the_requested_saved_identity(self):
        for resource, payload in (("accounts", {}), ("status", {"account_id": self.account}),
                                  ("receipt", {"account_id": self.account, "request_id": "original-001"})):
            self.api.read.return_value = {"resource": resource, "read_only": True}
            suffix = "" if resource == "accounts" else "/" + quote(json.dumps(payload), safe="")
            code, result = self.request("terminal_replay_" + resource + suffix)
            self.assertEqual(code, 200)
            self.assertEqual(result["data"]["resource"], resource)
            self.assertEqual(result["data"]["schema_version"], "hakimi-terminal-replay-view-v1")
            self.assertRegex(result["data"]["workspace_context"], r"^[a-f0-9]{64}$")
            self.api.read.assert_called_with(resource, payload)
        self.api.mutate.assert_not_called()
        self.jobs.submit.assert_not_called()
        self.runner.assert_not_called()

    def test_direct_pause_does_not_wait_for_research_worker_or_source_guard(self):
        self.guard.return_value = {"schema_version": "hakimi-runtime-build-v1",
                                   "status": "RESTART_REQUIRED", "restart_required": True}
        self.api.mutate.return_value = {"status": "PAUSED", "automatic_next_step": False}
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.shell._mutex, self.service._lock:
                future = pool.submit(self.request, "continuous-replay/pause", self.payload)
                code, result = future.result(timeout=2)
        self.assertEqual((code, result["data"]["status"]), (200, "PAUSED"))
        self.api.mutate.assert_called_once_with("pause", self.payload)
        self.guard.assert_not_called()
        self.jobs.submit.assert_not_called()
        self.runner.assert_not_called()

    def test_reconciliation_uses_jobs_without_enabling_new_steps_after_source_change(self):
        self.guard.return_value = {"schema_version": "hakimi-runtime-build-v1",
                                   "status": "RESTART_REQUIRED", "restart_required": True}
        payload = {key: value for key, value in self.payload.items() if key != "reason"}
        self.api.mutate.return_value = {"status": "RECONCILED_PAUSED"}
        code, _ = self.request("actions/terminal_replay_reconcile",
                               {"payload": payload, "request_id": "outer-reconcile-001"})
        self.assertEqual(code, 202)
        self.api.mutate.assert_called_once_with("reconcile", payload)
        self.guard.assert_not_called()
        self.jobs.submit.assert_called_once()
        for action in ("create", "seed", "step", "resume", "adopt"):
            code, _ = self.request("actions/terminal_replay_" + action,
                                   {"payload": payload, "request_id": "outer-" + action + "-001"})
            self.assertGreaterEqual(code, 400)
        self.api.mutate.assert_called_once()
        self.jobs.submit.assert_called_once()

    def test_direct_pause_still_requires_auth_origin_finite_json_and_write_mode(self):
        for options in ({"token": False}, {"origin": False}, {"content_type": "text/plain"},
                        {"raw": b'{"account_id":"one","account_id":"two"}'},
                        {"raw": b'{"expected_head":NaN}'}):
            code, _ = self.request("continuous-replay/pause", self.payload, **options)
            self.assertGreaterEqual(code, 400)
        self.shell.read_only = True
        self.assertEqual(self.request("continuous-replay/pause", self.payload)[0], 423)
        self.api.mutate.assert_not_called()
        self.jobs.submit.assert_not_called()

    def test_pause_never_queues_and_uninitialized_service_cannot_acknowledge(self):
        code, _ = self.request("actions/terminal_replay_pause",
                               {"payload": self.payload, "request_id": "queued-pause-001"})
        self.assertGreaterEqual(code, 400)
        self.shell._service = None
        code, _ = self.request("continuous-replay/pause", self.payload)
        self.assertGreaterEqual(code, 400)
        self.api.mutate.assert_not_called()
        self.jobs.submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
