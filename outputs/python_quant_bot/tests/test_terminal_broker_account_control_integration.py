"""Real service/handler/account barriers on new SYNTHETIC_TEST TEMP stores only.

The existing route fixture is used by composition, not inherited or re-exported:
unittest discovers only this module's independent integration cases. The job
stub delegates to the real service; no listener, broker, SDK or old DB is used.
"""
import builtins
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote, unquote, urlparse

from exchange_terminal.services import quant_workspace as quant
from exchange_terminal.services import terminal_broker_account_control as control
from exchange_terminal.services.terminal_research import TerminalResearchService
from tests import test_terminal_broker_integration as route_fixture


SIM, LIVE = "OFFICIAL_SIMULATION", "LIVE_CANDIDATE"
ACCOUNT, OTHER_ACCOUNT = "900000000000001", "900000000000002"


class BrokerAccountControlIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="new-broker-account-route-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        program = self.root / "fixture-program"
        program.mkdir()
        self.bound = control.bind_host_root(self.root / "shared-host-root", program_root=program,
                                            record_domain="SYNTHETIC_TEST")
        self.sequence = 0
        original_connect = sqlite3.connect

        def only_new_database(database, *args, **kwargs):
            value = os.fspath(database)
            if value.startswith("file:"):
                value = unquote(urlparse(value).path)
                if os.name == "nt" and value.startswith("/"):
                    value = value[1:]
            if not Path(value).resolve().is_relative_to(self.root):
                raise AssertionError("Only this integration test's new TEMP DB may open")
            return original_connect(database, *args, **kwargs)

        original_import = builtins.__import__

        def no_sdk(name, *args, **kwargs):
            if name == "futu" or name.startswith("futu."):
                raise AssertionError("No SDK import in account control integration")
            return original_import(name, *args, **kwargs)

        for target, replacement in (("sqlite3.connect", only_new_database), ("builtins.__import__", no_sdk)):
            blocker = patch(target, side_effect=replacement)
            blocker.start()
            self.addCleanup(blocker.stop)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.socket.bind",
                       "socket.create_connection", "socket.getaddrinfo", "subprocess.Popen", "urllib.request.urlopen"):
            blocker = patch(target, side_effect=AssertionError("No external operation in account integration"))
            denied = blocker.start()
            self.addCleanup(blocker.stop)
            self.addCleanup(denied.assert_not_called)
        self.a = self.peer("workspace-a", self.bound)
        self.b = self.peer("workspace-b", self.bound)

    def peer(self, name, bound):
        helper = route_fixture.BrokerIntegrationTests(methodName="runTest")
        helper.root = self.root
        helper.guard = Mock(return_value={"schema_version": "hakimi-runtime-build-v1",
                                           "status": "PASS", "restart_required": False})
        helper.shell = quant.QuantWorkspace(self.root / name, mutation_guard=helper.guard)
        helper.runner = Mock(side_effect=AssertionError("No research run in account integration"))
        helper.service = TerminalResearchService(SimpleNamespace(workspace=helper.shell.workspace),
            Mock(), lambda: [], helper.runner, Mock(), broker_control_root=bound)
        helper.shell._kernel, helper.shell._service = SimpleNamespace(), helper.service
        helper.jobs = Mock()
        helper.jobs.submit.side_effect = lambda action, body, identity: {
            "job_id": identity, "status": "succeeded", "result": helper.service.mutate(action, body)}
        helper.shell._jobs = helper.jobs
        self.addCleanup(helper.service.close)
        self.addCleanup(helper.runner.assert_not_called)
        return helper

    def request_id(self, label):
        self.sequence += 1
        return "account-integration-" + label + "-" + str(self.sequence).zfill(4)

    def inventory(self):
        return {p.relative_to(self.root).as_posix(): (sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file()}

    def save(self, peer, *, account=ACCOUNT, mode=SIM, config=None, research_reference=None):
        payload = {"mode": mode, "request_id": self.request_id("save"),
                   "config": {"account_id": account} if config is None else config}
        if research_reference is not None:
            payload["research_reference"] = research_reference
        code, response = peer.request("actions/terminal_broker_save_candidate",
            {"payload": payload, "request_id": self.request_id("outer-save")})
        self.assertEqual(code, 202, response)
        return response["data"]["result"]["config_id"]

    def stop_payload(self, config_id, *, mode=SIM):
        return {"mode": mode, "config_id": config_id, "request_id": self.request_id("stop"),
                "reason": "Explicit stop of a synthetic fixture account"}

    def stop(self, peer, config_id, *, mode=SIM, payload=None):
        code, response = peer.request("broker-account/stop", payload or self.stop_payload(config_id, mode=mode))
        self.assertEqual(code, 200, response)
        return response["data"]

    def read(self, peer, config_id, *, mode=SIM, request_id=None):
        payload = {"mode": mode, "config_id": config_id}
        resource = "terminal_broker_account_control"
        if request_id is not None:
            resource = "terminal_broker_account_receipt"
            payload["request_id"] = request_id
        code, response = peer.read(resource, payload)
        self.assertEqual(code, 200, response)
        return response["data"]

    def barrier(self, peer, config_id, *, mode=SIM, local=0, account=0):
        return peer.service.broker_dispatch_barrier(mode=mode, config_id=config_id,
            local_revision=local, account_revision=account)

    def assert_permissions_locked(self, result):
        self.assertFalse(any(result["permissions"].values()))
        self.assertFalse(result["control"]["dispatch_authorized"])
        self.assertFalse(result["control"]["automatic_resume"])
        self.assertFalse(result["broker_orders_cancelled"])

    def test_stop_is_shared_between_workspaces_and_both_dispatch_barriers_reject(self):
        a, b = self.save(self.a), self.save(self.b)
        before = self.inventory()
        self.assertEqual(self.read(self.a, a)["control"]["revision"], 0)
        self.assertEqual(self.read(self.b, b)["control"]["revision"], 0)
        self.assertEqual(before, self.inventory())
        self.assertFalse(self.bound.path.exists())
        stopped = self.stop(self.a, a)
        other = self.read(self.b, b)
        self.assertEqual(stopped["account_scope_id"], other["account_scope_id"])
        self.assertEqual(stopped["control"], other["control"])
        self.assertEqual(stopped["account"], {"provider": "FUTU", "mode": SIM, "account_id": ACCOUNT})
        self.assertEqual(stopped["record_domain"], "SYNTHETIC_TEST")
        self.assertTrue(other["control"]["stopped"])
        for peer, identity in ((self.a, a), (self.b, b)):
            for revision in (0, stopped["control"]["revision"]):
                with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
                    with self.barrier(peer, identity, account=revision):
                        self.fail("Stopped account reached dispatch")
        self.assert_permissions_locked(stopped)

    def test_other_account_and_mode_keep_their_independent_control(self):
        stopped_id = self.save(self.a)
        other_account = self.save(self.b, account=OTHER_ACCOUNT)
        other_mode = self.save(self.b, mode=LIVE)
        stopped = self.stop(self.a, stopped_id)
        for identity, mode in ((other_account, SIM), (other_mode, LIVE)):
            result = self.read(self.b, identity, mode=mode)
            self.assertNotEqual(result["account_scope_id"], stopped["account_scope_id"])
            self.assertFalse(result["control"]["stopped"])
            self.assertEqual(result["control"]["revision"], 0)
            with self.barrier(self.b, identity, mode=mode) as local:
                self.assertFalse(local["control"]["new_intents_blocked"])
            self.assert_permissions_locked(result)

    def test_direct_stop_bypasses_research_candidate_and_quant_locks_and_changed_source_guard(self):
        identity = self.save(self.a)
        self.a.guard.reset_mock()
        self.a.jobs.reset_mock()
        self.a.guard.return_value = {"status": "RESTART_REQUIRED", "restart_required": True}
        with patch("exchange_terminal.services.terminal_saved_results.resolve_execution_research",
                   side_effect=AssertionError("Stop must not resolve research")) as resolver:
            with ThreadPoolExecutor(max_workers=1) as workers:
                with self.a.shell._mutex, self.a.service._lock, self.a.service._broker()._lock:
                    result = workers.submit(self.stop, self.a, identity).result(timeout=2)
            resolver.assert_not_called()
        self.assertTrue(result["control"]["stopped"])
        self.a.jobs.submit.assert_not_called()
        self.a.guard.assert_not_called()

    def test_request_cannot_replace_root_provider_or_account_from_saved_config(self):
        identity = self.save(self.a)
        payload = self.stop_payload(identity)
        before = self.inventory()
        for key, value in (("root", str(self.root / "injected")), ("shared_root", str(self.root / "injected")),
                           ("provider", "OTHER"), ("account_id", OTHER_ACCOUNT), ("record_domain", "EXTERNAL_RECORD")):
            with self.subTest(field=key):
                code, _ = self.a.request("broker-account/stop", {**payload, key: value})
                self.assertEqual(code, 400)
                self.assertEqual(self.a.read("terminal_broker_account_control",
                    {"mode": SIM, "config_id": identity, key: value})[0], 400)
                self.assertEqual(before, self.inventory())
        for changed in ({"config_id": "f" * 64}, {"mode": LIVE}):
            code, _ = self.a.request("broker-account/stop", {**payload, **changed})
            self.assertIn(code, (400, 404))
            self.assertEqual(before, self.inventory())
        self.assertFalse(self.bound.path.exists())
        self.assertEqual(self.stop(self.a, identity, payload=payload)["account"]["account_id"], ACCOUNT)

    def test_unbound_service_reads_unavailable_and_rejects_mutations_without_files(self):
        peer = self.peer("workspace-unbound", None)
        identity = "a" * 64
        before = self.inventory()
        for request in (None, "never-created-account-request"):
            result = self.read(peer, identity, request_id=request)
            self.assertFalse(result["service_available"])
            self.assertTrue(result["read_only"])
            self.assertEqual(result["reason"], "HOST_BINDING_UNAVAILABLE")
            self.assertFalse(any(result["permissions"].values()))
        payload = self.stop_payload(identity)
        self.assertEqual(peer.request("broker-account/stop", payload)[0], 400)
        resume = {**payload, "expected_stop_receipt_id": "b" * 64}
        self.assertEqual(peer.request("actions/terminal_broker_account_resume",
            {"payload": resume, "request_id": self.request_id("unbound-resume")})[0], 400)
        with self.assertRaisesRegex(ValueError, "host_binding_unavailable"):
            peer.service.broker_execution_journal(mode=SIM, config_id=identity)
        self.assertEqual(before, self.inventory())
        self.assertFalse(peer.shell.runtime_dir.exists())
        self.assertFalse(self.bound.path.exists())

    def test_stop_and_resume_auth_origin_readonly_and_direct_route_contracts(self):
        identity = self.save(self.a)
        payload = self.stop_payload(identity)
        resume = {**payload, "expected_stop_receipt_id": "b" * 64}
        before = self.inventory()
        for resource in ("terminal_broker_account_control", "terminal_broker_account_receipt"):
            reference = {"mode": SIM, "config_id": identity}
            if resource.endswith("receipt"):
                reference["request_id"] = "unknown-account-receipt"
            self.assertEqual(self.a.request(resource + "/" + quote(json.dumps(reference), safe=""), token=False)[0], 403)
            self.assertEqual(before, self.inventory())
        for route, body in (("broker-account/stop", payload), ("actions/terminal_broker_account_resume",
                {"payload": resume, "request_id": self.request_id("outer-auth")})):
            for options in ({"token": False}, {"origin": False}, {"content_type": "text/plain"}):
                code, _ = self.a.request(route, body, **options)
                self.assertIn(code, (400, 403))
                self.assertEqual(before, self.inventory())
            self.a.shell.read_only = True
            self.assertEqual(self.a.request(route, body)[0], 423)
            self.a.shell.read_only = False
        self.a.jobs.reset_mock()
        self.assertEqual(self.a.request("actions/terminal_broker_account_stop",
            {"payload": payload, "request_id": self.request_id("queued-stop")})[0], 400)
        self.a.jobs.submit.assert_not_called()
        self.assertEqual(self.a.request("broker-account/stop", raw=b'{"mode":"OFFICIAL_SIMULATION","mode":"LIVE_CANDIDATE"}')[0], 400)
        self.assertEqual(before, self.inventory())
        self.assertFalse(self.bound.path.exists())

    def test_latest_resume_is_explicit_and_never_renews_old_account_revision(self):
        a, b = self.save(self.a), self.save(self.b)
        first = self.stop(self.a, a)
        latest = self.stop(self.b, b)
        resume = {"mode": SIM, "config_id": a, "request_id": self.request_id("resume"),
                  "reason": "Explicit synthetic review", "expected_stop_receipt_id": first["receipt"]["id"]}
        before = self.inventory()
        self.assertEqual(self.a.request("actions/terminal_broker_account_resume",
            {"payload": resume, "request_id": self.request_id("outer-stale-resume")})[0], 400)
        self.assertEqual(before, self.inventory())
        resume["expected_stop_receipt_id"] = latest["receipt"]["id"]
        code, response = self.a.request("actions/terminal_broker_account_resume",
            {"payload": resume, "request_id": self.request_id("outer-resume")})
        self.assertEqual(code, 202, response)
        result = response["data"]["result"]
        self.assertEqual(result["control"]["revision"], 3)
        self.assertFalse(result["control"]["stopped"])
        for peer, identity in ((self.a, a), (self.b, b)):
            with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
                with self.barrier(peer, identity, account=0):
                    self.fail("Stop/resume renewed an old dispatch binding")
            with self.barrier(peer, identity, account=3):
                pass
        self.assert_permissions_locked(result)
        self.a.runner.assert_not_called()
        self.b.runner.assert_not_called()

    def test_reads_receipt_replay_and_account_resume_preserve_old_local_stop_bytes(self):
        a, b = self.save(self.a), self.save(self.b)
        local_stop = self.a.stop("legacy-local-stop-preserved")[1]["data"]
        local_before = {p: value for p, value in self.inventory().items() if p.startswith("workspace-a/")}
        payload = self.stop_payload(a)
        stopped = self.stop(self.a, a, payload=payload)
        before = self.inventory()
        for _ in range(2):
            self.assertEqual(self.read(self.b, b, request_id=payload["request_id"])["receipt"], stopped["receipt"])
            self.assertIsNone(self.read(self.b, b, request_id="not-recorded-account-receipt")["receipt"])
            self.assertTrue(self.stop(self.a, a, payload=payload)["replayed"])
            self.assertEqual(before, self.inventory())
        resume = {"mode": SIM, "config_id": a, "request_id": self.request_id("resume-local-stopped"),
                  "reason": "Resume only the shared synthetic account", "expected_stop_receipt_id": stopped["receipt"]["id"]}
        self.assertEqual(self.a.request("actions/terminal_broker_account_resume",
            {"payload": resume, "request_id": self.request_id("outer-resume-local")})[0], 202)
        local_after = {p: value for p, value in self.inventory().items() if p.startswith("workspace-a/")}
        self.assertEqual(local_before, local_after)
        self.assertEqual(self.a.service._broker().read_plan_control(SIM)["control"]["latest_stop_receipt_id"], local_stop["stop_receipt_id"])
        with self.assertRaisesRegex(ValueError, "candidate_plan_control_changed_or_stopped"):
            with self.barrier(self.a, a, local=1, account=2):
                self.fail("Shared resume cleared the old workspace stop")
        before = self.inventory()
        replay = self.stop(self.a, a, payload=payload)
        self.assertFalse(replay["control"]["stopped"])
        self.assertEqual(replay["receipt"], stopped["receipt"])
        self.assertEqual(before, self.inventory())

    def test_real_journal_begin_action_uses_combined_barrier_and_records_nothing_after_peer_stop(self):
        from exchange_terminal.services import terminal_broker_wire_profile as wire
        from tests import test_terminal_broker_wire_profile as profile_fixture

        args = profile_fixture.fixture()
        with patch("exchange_terminal.services.terminal_saved_results.resolve_execution_research",
                   return_value=deepcopy(args["research_resolution"])):
            identity = self.save(self.a, config=deepcopy(args["candidate_config"]["config"]),
                research_reference=deepcopy(args["candidate_config"]["research"]["reference"]))
        self.assertEqual(identity, args["candidate_config"]["id"])
        peer_id = self.save(self.b)
        profile = wire.prepare_wire_profile(**args)
        store = self.a.service.broker_execution_journal(mode=SIM, config_id=identity)
        # This is the fixture's historical synthetic clock, not current broker
        # evidence or a claim of real-time freshness.
        store._clock = lambda: profile_fixture.NOW
        self.addCleanup(store.close)
        head = store.read()["head"]
        store.snapshot({"evidence_id": "9" * 64, "query_started_at": profile_fixture.NOW.isoformat(),
            "observed_at": profile_fixture.NOW.isoformat(), "covered_head": head,
            "valid_until": (profile_fixture.NOW + timedelta(seconds=60)).isoformat(),
            "cash_available": "100", "positions": []}, expected_head=head, request_id=self.request_id("snapshot"))
        barrier = lambda: self.barrier(self.a, identity)
        store.claim(profile, evidence_id="9" * 64, authorization_id="8" * 64,
                    request_id=self.request_id("claim"), control_barrier=barrier)
        first_request = self.request_id("original-action")
        original = store.begin_action(profile, "quote_connect", request_id=first_request, frame_sha256=None,
            frame_bytes=0, authorization_id="8" * 64, control_barrier=barrier)
        before_state, before_bytes = store.read(), store.path.read_bytes()
        self.stop(self.b, peer_id)
        operation = self.request_id("blocked-action")
        with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
            store.begin_action(profile, "trade_submit", request_id=operation, frame_sha256="a" * 64,
                frame_bytes=100, authorization_id="8" * 64, control_barrier=barrier)
        self.assertEqual(store.path.read_bytes(), before_bytes)
        self.assertEqual(store.read(), before_state)
        self.assertIsNone(store.read(operation)["receipt"])
        self.assertEqual(set(store.read()["actions"]), {first_request})
        self.assertEqual(store.read(first_request)["receipt"], original["receipt"])
        replayed = store.begin_action(profile, "quote_connect", request_id=first_request, frame_sha256=None,
            frame_bytes=0, authorization_id="8" * 64, control_barrier=barrier)
        self.assertTrue(replayed["replayed"])
        self.assertEqual(replayed["receipt"], original["receipt"])
        self.assertEqual(store.path.read_bytes(), before_bytes)

    def test_trusted_journal_factory_shares_scope_without_creation_or_http_write_surface(self):
        a, b = self.save(self.a), self.save(self.b)
        other_account = self.save(self.b, account=OTHER_ACCOUNT)
        other_mode = self.save(self.b, mode=LIVE)
        before = self.inventory()
        stores = [self.a.service.broker_execution_journal(mode=SIM, config_id=a),
                  self.b.service.broker_execution_journal(mode=SIM, config_id=b),
                  self.b.service.broker_execution_journal(mode=SIM, config_id=other_account),
                  self.b.service.broker_execution_journal(mode=LIVE, config_id=other_mode)]
        for store in stores:
            self.addCleanup(store.close)
            self.assertEqual(store.domain, "SYNTHETIC_TEST")
            self.assertTrue(store.path.is_relative_to(self.bound.path))
            value = store.read("unknown-factory-request")
            self.assertTrue(value["read_only"])
            self.assertEqual(value["event_count"], 0)
            self.assertIsNone(value["receipt"])
            self.assertFalse(value["automatic_resume"])
            self.assertFalse(any(value["permissions"].values()))
        self.assertEqual(stores[0].path, stores[1].path)
        self.assertEqual(len({stores[0].path, stores[2].path, stores[3].path}), 3)
        with self.assertRaises(TypeError):
            self.a.service.broker_execution_journal(mode=SIM, config_id=a, shared_root=self.root / "injected")
        self.assertEqual(self.a.read("terminal_broker_execution_journal", {"mode": SIM, "config_id": a})[0], 404)
        self.assertEqual(self.a.request("actions/terminal_broker_execution_journal",
            {"payload": {"mode": SIM, "config_id": a}, "request_id": self.request_id("journal-http")})[0], 400)
        self.assertEqual(before, self.inventory())
        self.assertFalse(self.bound.path.exists())

    def test_external_journal_factory_rejects_synthetic_profile_without_recording_a_claim(self):
        from exchange_terminal.services import terminal_broker_execution_journal as journal
        from exchange_terminal.services import terminal_broker_wire_profile as wire
        from tests import test_terminal_broker_wire_profile as profile_fixture

        external_root = control.bind_host_root(self.bound.path, program_root=self.root / "fixture-program",
                                               record_domain="EXTERNAL_RECORD")
        peer = self.peer("workspace-external-domain-test-only", external_root)
        args = profile_fixture.fixture()
        with patch("exchange_terminal.services.terminal_saved_results.resolve_execution_research",
                   return_value=deepcopy(args["research_resolution"])):
            identity = self.save(peer, config=deepcopy(args["candidate_config"]["config"]),
                research_reference=deepcopy(args["candidate_config"]["research"]["reference"]))
        store = peer.service.broker_execution_journal(mode=SIM, config_id=identity)
        self.addCleanup(store.close)
        store._clock = lambda: profile_fixture.NOW  # Synthetic fixture time only.
        profile = wire.prepare_wire_profile(**args)
        self.assertEqual(store.domain, "EXTERNAL_RECORD")
        self.assertFalse(store.path.exists())
        self.assertEqual(store.read()["event_count"], 0)
        self.assertFalse(store.path.exists())
        request = self.request_id("external-rejected")
        with self.assertRaisesRegex(journal.JournalError, "synthetic_profile_cannot_enter_external_journal"):
            store.claim(profile, evidence_id="9" * 64, authorization_id="8" * 64, request_id=request,
                        control_barrier=lambda: self.barrier(peer, identity))
        self.assertEqual(store.read()["event_count"], 0)
        self.assertEqual(store.read()["claims"], {})
        self.assertIsNone(store.read(request)["receipt"])


if __name__ == "__main__":
    unittest.main()
