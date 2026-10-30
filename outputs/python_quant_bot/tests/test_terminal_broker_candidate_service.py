"""Draft integration tests: new temporary directories, no real account or client."""
import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

if Path(__file__).with_name("terminal_broker_candidate_service.py").exists():
    # Isolated review copy. Repo tests use the normal package import below.
    import terminal_broker_candidate_service as candidate_module
else:
    from exchange_terminal.services import terminal_broker_candidate_service as candidate_module
BrokerCandidateService = candidate_module.BrokerCandidateService
CandidateError, MODES, PERMISSIONS = candidate_module.CandidateError, candidate_module.MODES, candidate_module.PERMISSIONS


SIM, LIVE = "OFFICIAL_SIMULATION", "LIVE_CANDIDATE"
REF = {"kind": "terminal_run", "id": "a" * 64}
SDK = {"name": "futu-api", "version": "10.7.6708", "manifest_sha256": "b" * 64}
RESOLUTION = {"binding": {"schema_version": "hakimi-offline-research-binding-v1", "status": "COMPLETED",
    "engine_id": "terminal.fictional-qa-rule", "strategy_id": "dual_ma", "strategy_params": {"window": 7},
    "task_id": "c" * 64, "task_version": 1, "input_id": "d" * 64, "report_id": REF["id"], "report_hash": REF["id"],
    "security_id": "QA:TEST", "risk": {"position_pct": 25}, "costs": {"fee_rate": .0005}},
    "display": {"security_id": "QA:TEST", "symbol": "TEST", "currency": "USD", "asset_class": "US_EQUITY"},
    "assumptions": {"fill_model": "NEXT_BAR_OPEN"}, "owner_id": "family:fictional-qa-family"}


class BrokerCandidateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-offline-broker-draft-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "new-candidates"
        self.now = datetime(2026, 10, 29, 8, tzinfo=timezone.utc)
        self.resolver = Mock(side_effect=lambda reference: deepcopy(RESOLUTION))
        self.service = self.reopen()
        self.seq = 0
        self.network = patch("socket.socket.connect", side_effect=AssertionError("No network"))
        self.network.start(); self.addCleanup(self.network.stop)

    def reopen(self):
        return BrokerCandidateService(self.root, research_resolver=self.resolver,
                                      verified_sdk_metadata=SDK, clock=lambda: self.now)

    def request(self):
        self.seq += 1
        return "draft-request-%04d" % self.seq

    def config(self):
        # Fictional declaration only: never sent or validated against a broker.
        return {"account_id": "900000000000001", "market": "US", "asset_class": "EQUITY", "asset_code": "US.TEST",
                "currency": "USD", "max_quantity": 2, "max_notional": "50.00", "side": "BUY",
                "quantity": 1, "limit_price": "20.00", "time_in_force": "DAY",
                "expires_at": (self.now + timedelta(hours=1)).isoformat()}

    def save(self, mode=SIM, **overrides):
        payload = dict(mode=mode, request_id=self.request(), config=self.config(), research_reference=deepcopy(REF))
        payload.update(overrides)
        return payload, self.service.save(payload)

    def inventory(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file()}

    def test_first_status_is_no_io_no_connection_and_no_false_ready(self):
        value = self.service.read("terminal_broker_status")
        self.assertEqual([v["state"] for v in value["modes"]], ["NOT_CONFIGURED", "NOT_CONFIGURED"])
        self.assertEqual(value["sdk"]["package_metadata"]["version"], "10.7.6708")
        self.assertEqual(value["sdk"]["official_docs_version"], "10.12")
        self.assertEqual(value["sdk"]["runtime_compatibility"], "NOT_VERIFIED")
        self.assertNotIn("READY", json.dumps(value))
        self.assertTrue(all(v is False for v in value["permissions"].values()))
        self.resolver.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_save_missing_configuration_can_be_reviewed_without_any_permission(self):
        _, saved = self.save(config={}, research_reference=REF)
        result = self.service.check(SIM, saved["config_id"])
        self.assertEqual(result["status"], "MISSING")
        self.assertTrue({"account_id", "asset_code", "max_quantity", "max_notional", "side", "limit_price", "expires_at"}
                        <= {row["field"] for row in result["missing"]})
        with self.assertRaisesRegex(CandidateError, "incomplete"):
            self.service.prepare_intent(dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
        self.assertFalse((self.root / MODES[SIM] / "intents").exists())

    def test_exact_saved_version_intent_replay_and_reopen_only_read_existing_bytes(self):
        payload, saved = self.save()
        request = dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"])
        intent = self.service.mutate("terminal_broker_prepare_intent", request)
        self.assertEqual(intent["status"], "UNSENT_OFFLINE_PREVIEW")
        self.assertEqual(intent["intent"]["config_id"], saved["config_id"])
        self.assertEqual(intent["intent"]["permissions"], PERMISSIONS)
        before = self.inventory()
        calls = self.resolver.call_count
        self.assertEqual(self.service.save(payload), saved)
        self.assertEqual(self.service.prepare_intent(request), intent)
        reopened = self.reopen()
        self.assertEqual(reopened.prepare_intent(request), intent)
        self.assertEqual(self.resolver.call_count, calls)
        reopened.status(); reopened.check(SIM, saved["config_id"]); reopened.receipts(SIM)
        self.assertEqual(self.inventory(), before)
        changed = deepcopy(payload); changed["config"]["quantity"] = 2
        with self.assertRaisesRegex(CandidateError, "request_id_payload_conflict"):
            self.service.save(changed)

    def test_modes_have_separate_identities_and_cannot_read_each_others_configuration(self):
        payload, simulated = self.save()
        live = self.service.save({**payload, "mode": LIVE})
        self.assertNotEqual(live["config_id"], simulated["config_id"])
        with self.assertRaises(FileNotFoundError):
            self.service.check(LIVE, simulated["config_id"])
        self.service.stop(dict(mode=SIM, request_id=self.request(), reason="pause local preview"))
        self.assertEqual(self.service.check(SIM, simulated["config_id"])["status"], "BLOCKED")
        self.assertEqual(self.service.check(LIVE, live["config_id"])["status"], "OFFLINE_PREVIEW_ONLY")
        self.assertTrue((self.root / MODES[SIM]).is_dir())
        self.assertTrue((self.root / MODES[LIVE]).is_dir())

    def test_research_is_resolved_by_server_and_changed_binding_blocks_new_intent(self):
        _, saved = self.save()
        self.resolver.side_effect = lambda reference: {**deepcopy(RESOLUTION), "binding": {"changed": True}}
        with self.assertRaisesRegex(CandidateError, "saved_research_binding_changed"):
            self.service.prepare_intent(dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
        with self.assertRaisesRegex(CandidateError, "fields_invalid"):
            self.save(research_reference={**REF, "completed": True})
        self.resolver.side_effect = lambda reference: {**deepcopy(RESOLUTION), "binding": {**deepcopy(RESOLUTION["binding"]), "status": "UNKNOWN"}}
        with self.assertRaisesRegex(CandidateError, "verified_completed_research_required"):
            self.save()

    def test_stop_is_prompt_during_resolver_work_and_persists_without_cancellation_claim(self):
        _, saved = self.save()
        entered, release = threading.Event(), threading.Event()
        def resolve(reference):
            entered.set()
            if not release.wait(3): raise RuntimeError("fixture release missing")
            return deepcopy(RESOLUTION)
        self.resolver.side_effect = resolve
        with ThreadPoolExecutor(max_workers=2) as pool:
            preparing = pool.submit(self.service.prepare_intent, dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
            try:
                self.assertTrue(entered.wait(1))
                stopping = pool.submit(self.service.stop, dict(mode=SIM, request_id=self.request(), reason="user stopped"))
                stopped = stopping.result(timeout=1)
                self.assertFalse(stopped["broker_orders_cancelled"])
                self.assertFalse(preparing.done())
            finally:
                release.set()
            with self.assertRaisesRegex(CandidateError, "incomplete_expired_or_stopped"):
                preparing.result(timeout=2)
        self.assertEqual(self.reopen().status()["modes"][0]["state"], "STOPPED")
        self.assertFalse((self.root / MODES[SIM] / "intents").exists())

    def test_invalid_stop_request_does_not_change_candidate_state(self):
        _, saved = self.save()
        with self.assertRaisesRegex(CandidateError, "bounded_request_id_required"):
            self.service.stop(dict(mode=SIM, request_id="bad", reason="stop"))
        self.assertEqual(self.service.check(SIM, saved["config_id"])["status"], "OFFLINE_PREVIEW_ONLY")

    def test_stop_has_its_own_durable_capacity_and_request_ids_cannot_cross_actions(self):
        with patch.object(candidate_module, "MAX_RECORDS", 1):
            payload, saved = self.save()
            with self.assertRaisesRegex(CandidateError, "capacity_exceeded"):
                self.save()
            with self.assertRaisesRegex(CandidateError, "request_id_payload_conflict"):
                self.service.stop(dict(mode=SIM, request_id=payload["request_id"], reason="conflicting ID"))
            stopped = self.service.stop(dict(mode=SIM, request_id=self.request(), reason="stop despite candidate capacity"))
            self.assertEqual(stopped["status"], "STOPPED")
            self.assertEqual(self.reopen().status()["modes"][0]["state"], "STOPPED")
            self.assertEqual(len(self.service.receipts(SIM)["items"]), 2)

    def test_quantity_notional_and_expiry_are_bounded_without_inventing_broker_validation(self):
        config = self.config(); config.update(quantity=3, max_notional="40.00")
        _, saved = self.save(config=config)
        checked = self.service.check(SIM, saved["config_id"])
        self.assertEqual(checked["blockers"], ["QUANTITY_EXCEEDS_CANDIDATE_LIMIT", "NOTIONAL_EXCEEDS_CANDIDATE_LIMIT"])
        self.assertEqual(checked["order_notional_excluding_fees"], "60.00")
        self.assertFalse(checked["fee_verified"]); self.assertFalse(checked["account_verified"])
        self.now += timedelta(hours=2)
        self.assertIn("CANDIDATE_EXPIRED", self.service.check(SIM, saved["config_id"])["blockers"])
        for key, value in (("limit_price", "NaN"), ("max_notional", 10.0), ("quantity", True), ("side", "SHORT"),
                           ("expires_at", (self.now + timedelta(days=2)).isoformat()), ("credential", "never-read")):
            config = self.config(); config[key] = value
            with self.subTest(key=key), self.assertRaises(CandidateError): self.save(config=config)

    def test_tampered_and_cross_named_records_are_rejected_without_repair(self):
        _, first = self.save()
        config = self.config(); config["limit_price"] = "21.00"
        _, second = self.save(config=config)
        directory = self.root / MODES[SIM] / "configs"
        path = directory / (first["config_id"] + ".json")
        path.write_bytes((directory / (second["config_id"] + ".json")).read_bytes())
        before = self.inventory()
        with self.assertRaisesRegex(CandidateError, "identity_mismatch"):
            self.service.check(SIM, first["config_id"])
        self.assertEqual(self.inventory(), before)

    def test_mutated_caller_payload_cannot_change_intent_during_resolution(self):
        _, saved = self.save()
        request = dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"])
        original_id = request["request_id"]
        def resolve(reference):
            request.update(mode=LIVE, request_id="foreign-request-0001")
            return deepcopy(RESOLUTION)
        self.resolver.side_effect = resolve
        value = self.service.prepare_intent(request)
        self.assertEqual(value["mode"], SIM)
        self.assertEqual(value["intent"]["request_id"], original_id)
        self.assertFalse((self.root / MODES[LIVE]).exists())

    def test_actual_resolver_shape_and_trusted_wrapper_fields_do_not_require_top_status(self):
        _, saved = self.save()
        checked = self.service.check(SIM, saved["config_id"])
        self.assertEqual(checked["security_binding"]["status"], "MATCHED_SAVED_DECLARATION")
        self.assertFalse(checked["security_binding"]["broker_mapping_verified"])
        self.resolver.side_effect = lambda reference: {**deepcopy(RESOLUTION), "reference": reference,
            "owner_continuity": "VERIFIED_TASK_FAMILY", "view_schema_version": "hakimi-terminal-execution-view-v1",
            "permissions": {"order_allowed": False}, "display_only_note": "trusted unused field"}
        result = self.service.prepare_intent(dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
        self.assertEqual(result["status"], "UNSENT_OFFLINE_PREVIEW")
        self.assertFalse(result["intent"]["security_binding"]["asset_rules_verified"])
        self.assertFalse(result["intent"]["security_binding"]["account_verified"])

    def test_reference_names_and_hash_lengths_match_real_application(self):
        for reference in ({"kind":"native_run","id":"a"*64}, {"kind":"terminal_run","id":"a"*24},
                          {"kind":"core_run","id":"a"*64}):
            with self.subTest(reference=reference), self.assertRaisesRegex(CandidateError,"saved_research_reference_required"):
                self.save(research_reference=reference)
        core = {"kind":"core_run","id":"c"*24}
        resolution = deepcopy(RESOLUTION)
        resolution["binding"].update(engine_id="research.accepted-equity",report_id="saved-core-manifest-run-id",report_hash="e"*64)
        self.resolver.side_effect = lambda reference: {**deepcopy(resolution),"reference":reference}
        _, saved = self.save(research_reference=core)
        result = self.service.prepare_intent(dict(mode=SIM,request_id=self.request(),config_id=saved["config_id"]))
        self.assertEqual(result["status"],"UNSENT_OFFLINE_PREVIEW")
        self.resolver.assert_called_with(core)

    def test_wrong_security_currency_and_unsupported_mapping_block_intent(self):
        cases = [("asset_code","US.OTHER","RESEARCH_ASSET_CODE_MISMATCH"),
                 ("currency","HKD","RESEARCH_CURRENCY_MISMATCH"),
                 ("market","HK","RESEARCH_MARKET_MISMATCH")]
        for key,value,blocker in cases:
            config=self.config();config[key]=value
            _,saved=self.save(config=config)
            with self.subTest(key=key):
                self.assertIn(blocker,self.service.check(SIM,saved["config_id"])["blockers"])
                with self.assertRaisesRegex(CandidateError,"incomplete"):
                    self.service.prepare_intent(dict(mode=SIM,request_id=self.request(),config_id=saved["config_id"]))
        for mutation,blocker in ((lambda row:row["binding"].update(security_id="OTHER:ID"),"RESEARCH_SECURITY_IDENTITY_MISMATCH"),
                                 (lambda row:row["display"].update(asset_class="HK_EQUITY",currency="HKD",symbol="00700"),"SAVED_RESEARCH_MARKET_MAPPING_UNSUPPORTED")):
            resolution=deepcopy(RESOLUTION);mutation(resolution)
            self.resolver.side_effect=lambda reference,value=resolution:deepcopy(value)
            _,saved=self.save()
            self.assertIn(blocker,self.service.check(SIM,saved["config_id"])["blockers"])
            with self.assertRaisesRegex(CandidateError,"incomplete"):
                self.service.prepare_intent(dict(mode=SIM,request_id=self.request(),config_id=saved["config_id"]))
        self.assertFalse((self.root/MODES[SIM]/"intents").exists())

    def test_missing_saved_security_fields_remain_missing_and_are_not_inferred(self):
        for container,key in (("display","symbol"),("display","currency"),("display","asset_class"),
                              ("display","security_id"),("binding","security_id")):
            resolution=deepcopy(RESOLUTION);resolution[container].pop(key)
            self.resolver.side_effect=lambda reference,value=resolution:deepcopy(value)
            _,saved=self.save()
            checked=self.service.check(SIM,saved["config_id"])
            with self.subTest(container=container,key=key):
                self.assertEqual(checked["status"],"MISSING")
                self.assertIn("research."+container+"."+key,{row["field"] for row in checked["missing"]})
                with self.assertRaisesRegex(CandidateError,"incomplete"):
                    self.service.prepare_intent(dict(mode=SIM,request_id=self.request(),config_id=saved["config_id"]))

    def test_replay_requires_retained_target_and_false_permissions(self):
        _,saved=self.save()
        request=dict(mode=SIM,request_id=self.request(),config_id=saved["config_id"])
        result=self.service.prepare_intent(request)
        intent_path=self.root/MODES[SIM]/"intents"/(result["intent"]["id"]+".json")
        raw=intent_path.read_bytes();intent_path.unlink()  # only this new TEMP fixture
        with self.assertRaises(FileNotFoundError):self.service.prepare_intent(request)
        intent_path.write_bytes(raw)
        receipt_path=self.root/MODES[SIM]/"receipts"/(sha256(request["request_id"].encode()).hexdigest()+".json")
        receipt=json.loads(receipt_path.read_bytes());receipt.pop("id")
        receipt["result"]["permissions"]["submit_allowed"]=True
        receipt_path.write_text(json.dumps(candidate_module._seal(receipt)),encoding="utf-8")
        before=self.inventory()
        with self.assertRaisesRegex(CandidateError,"permissions_changed"):self.service.prepare_intent(request)
        self.assertEqual(self.inventory(),before)

    def test_no_executable_external_adapter_or_credential_dependency(self):
        path = Path(candidate_module.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        imports |= {alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
        self.assertFalse({"futu", "socket", "requests", "urllib", "subprocess", "keyring"} & imports)
        for action in ("terminal_broker_submit", "terminal_broker_query", "terminal_broker_cancel", "terminal_broker_unlock"):
            with self.assertRaisesRegex(CandidateError, "action_not_found"):
                self.service.mutate(action, {})
        self.assertFalse(self.root.exists())

    def stop_payload(self):
        return dict(mode=SIM, request_id=self.request(), reason="Explicitly stop offline preparation")

    def resume_payload(self, stopped):
        return dict(mode=SIM, request_id=self.request(), expected_stop_receipt_id=stopped["stop_receipt_id"],
                    reason="Explicitly resume offline preparation only")

    def test_manual_resume_is_durable_across_instances_but_never_revives_expired_configuration(self):
        _, saved = self.save()
        other = self.reopen()
        stopped = self.service.stop(self.stop_payload())
        self.assertEqual(other.status()["modes"][0]["control"]["latest_stop_receipt_id"], stopped["stop_receipt_id"])
        self.assertEqual(other.check(SIM, saved["config_id"])["status"], "BLOCKED")
        self.now += timedelta(hours=2)
        resumed = other.mutate("terminal_broker_resume", self.resume_payload(stopped))
        self.assertEqual(resumed["status"], "OFFLINE_PREPARATION_RESUMED")
        self.assertTrue(all(value is False for value in resumed["permissions"].values()))
        self.assertFalse(resumed["broker_orders_cancelled"])
        self.assertNotIn("CANDIDATE_STOPPED", self.service.check(SIM, saved["config_id"])["blockers"])
        self.assertIn("CANDIDATE_EXPIRED", self.service.check(SIM, saved["config_id"])["blockers"])
        with self.assertRaisesRegex(CandidateError, "incomplete_expired_or_stopped"):
            self.service.prepare_intent(dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
        _, fresh = self.save()
        self.assertEqual(self.reopen().prepare_intent(dict(mode=SIM, request_id=self.request(), config_id=fresh["config_id"]))["status"], "UNSENT_OFFLINE_PREVIEW")
        self.assertEqual([row["action"] for row in self.service.receipts(SIM)["items"] if row["kind"] == "controls"], ["stop", "resume"])

    def test_resume_requires_latest_exact_stop_and_reason_and_never_affects_other_mode(self):
        stopped = self.service.stop(self.stop_payload())
        newest = self.reopen().stop(self.stop_payload())
        with self.assertRaisesRegex(CandidateError, "latest_stop_confirmation"):
            self.service.resume(self.resume_payload(stopped))
        request = self.resume_payload(newest)
        with self.assertRaisesRegex(CandidateError, "bounded_stop_reason"):
            self.service.resume(dict(request, reason=" "))
        with self.assertRaisesRegex(CandidateError, "latest_stop_confirmation"):
            self.service.resume(dict(request, mode=LIVE))
        self.assertEqual(self.reopen().status()["modes"][0]["state"], "STOPPED")

    def test_stop_bypasses_slow_history_scan_and_instance_lock(self):
        self.save()
        entered, release = threading.Event(), threading.Event()
        original = self.service._records
        def slow(mode, kind):
            entered.set()
            if not release.wait(3): raise AssertionError("release history fixture")
            return original(mode, kind)
        with patch.object(self.service, "_records", side_effect=slow), ThreadPoolExecutor(max_workers=2) as pool:
            reading = pool.submit(self.service.status)
            try:
                self.assertTrue(entered.wait(1))
                stopped = pool.submit(self.service.stop, self.stop_payload()).result(timeout=1)
                self.assertEqual(stopped["status"], "STOPPED")
                self.assertFalse(reading.done())
            finally:
                release.set()
            reading.result(timeout=2)

    def test_inflight_prepare_cannot_continue_automatically_after_stop_then_resume(self):
        _, saved = self.save()
        entered, release = threading.Event(), threading.Event()
        def resolve(reference):
            entered.set()
            if not release.wait(3): raise AssertionError("release resolver fixture")
            return deepcopy(RESOLUTION)
        self.resolver.side_effect = resolve
        with ThreadPoolExecutor(max_workers=1) as pool:
            preparing = pool.submit(self.service.prepare_intent,
                dict(mode=SIM, request_id=self.request(), config_id=saved["config_id"]))
            try:
                self.assertTrue(entered.wait(1))
                stopped = self.reopen().stop(self.stop_payload())
                self.reopen().resume(self.resume_payload(stopped))
            finally:
                release.set()
            with self.assertRaisesRegex(CandidateError, "control_changed_during_preparation"):
                preparing.result(timeout=2)
        self.assertFalse((self.root / MODES[SIM] / "intents").exists())

    def test_replayed_resume_and_stop_are_historical_receipts_not_new_state_transitions(self):
        stop_request = self.stop_payload()
        stopped = self.service.stop(stop_request)
        resume_request = self.resume_payload(stopped)
        resumed = self.service.resume(resume_request)
        newest = self.service.stop(self.stop_payload())
        before = self.inventory()
        self.assertEqual(self.reopen().resume(resume_request), resumed)
        self.assertEqual(self.reopen().stop(stop_request), stopped)
        self.assertEqual(self.service.status()["modes"][0]["control"]["latest_stop_receipt_id"], newest["stop_receipt_id"])
        self.assertEqual(self.inventory(), before)

    def test_control_capacity_always_reserves_room_for_next_stop(self):
        with patch.object(candidate_module, "MAX_RECORDS", 3):
            stopped = self.service.stop(self.stop_payload())
            self.service.resume(self.resume_payload(stopped))
            stopped = self.service.stop(self.stop_payload())
            before = self.inventory()
            with self.assertRaisesRegex(CandidateError, "control_capacity_exceeded"):
                self.service.resume(self.resume_payload(stopped))
            self.assertEqual(self.reopen().status()["modes"][0]["state"], "STOPPED")
            self.assertFalse(self.reopen().status()["modes"][0]["control"]["resume_allowed"])
            self.assertEqual(self.inventory(), before)

    def test_unknown_after_commit_can_be_read_without_resubmission(self):
        request = self.stop_payload()
        with patch.object(self.service, "_control_result", side_effect=RuntimeError("synthetic response lost")):
            with self.assertRaisesRegex(RuntimeError, "response lost"):
                self.service.stop(request)
        before = self.inventory()
        found = self.reopen().read("terminal_broker_receipt", {"mode": SIM, "request_id": request["request_id"]})
        self.assertEqual(found["status"], "FOUND")
        self.assertEqual(found["receipt"]["action"], "stop")
        self.assertEqual(found["receipt"]["payload"], request)
        self.assertFalse(found["retry_allowed"])
        missing = self.service.receipt(SIM, "never-started-request")
        self.assertEqual(missing["status"], "NOT_RECORDED")
        self.assertFalse(missing["retry_allowed"])
        self.assertEqual(self.inventory(), before)

    def test_readonly_research_and_check_use_trusted_fields_without_writes(self):
        resolved = self.service.read("terminal_broker_research", {"reference": REF})
        self.assertEqual(resolved["display"]["symbol"], "TEST")
        self.assertEqual(resolved["permissions"], PERMISSIONS)
        self.assertFalse(self.root.exists())
        _, saved = self.save()
        before = self.inventory()
        self.assertEqual(self.service.read("terminal_broker_check", {"mode": SIM, "config_id": saved["config_id"]})["status"], "OFFLINE_PREVIEW_ONLY")
        self.assertEqual(self.inventory(), before)

    def test_control_tamper_stops_read_and_resume_without_repair(self):
        stopped = self.service.stop(self.stop_payload())
        path = self.root / MODES[SIM] / "control.sqlite3"
        with closing(candidate_module.sqlite3.connect(path)) as connection, connection:
            row = json.loads(connection.execute("SELECT body FROM controls").fetchone()[0])
            row.pop("id"); row["result"]["permissions"]["submit_allowed"] = True
            row = candidate_module._seal(row)
            connection.execute("UPDATE controls SET identity=?,body=?", (row["id"], candidate_module._json(row)))
        before = self.inventory()
        with self.assertRaisesRegex(CandidateError, "control_permissions_changed"):
            self.reopen().status()
        with self.assertRaisesRegex(CandidateError, "control_permissions_changed"):
            self.service.resume(self.resume_payload(stopped))
        self.assertEqual(self.inventory(), before)

    def test_concurrent_new_stop_and_resume_cannot_leave_obsolete_resume_active(self):
        stopped = self.service.stop(self.stop_payload())
        start = threading.Barrier(2)
        stop_request, resume_request = self.stop_payload(), self.resume_payload(stopped)
        def act(service, action, payload):
            start.wait(timeout=2)
            return service.mutate(action, payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            stopping = pool.submit(act, self.service, "terminal_broker_stop", stop_request)
            resuming = pool.submit(act, self.reopen(), "terminal_broker_resume", resume_request)
            newest = stopping.result(timeout=3)
            try:
                resuming.result(timeout=3)
            except CandidateError as error:
                self.assertIn("latest_stop_confirmation", str(error))
        self.assertEqual(self.reopen().status()["modes"][0]["control"]["latest_stop_receipt_id"], newest["stop_receipt_id"])
        self.assertEqual(self.service.status()["modes"][0]["state"], "STOPPED")
        self.service.receipts(SIM)

    def test_second_process_observes_and_changes_same_control_state(self):
        _, saved = self.save()
        worker = """import importlib.util,json,sys
from datetime import datetime,timezone
spec=importlib.util.spec_from_file_location('candidate_worker',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
service=m.BrokerCandidateService(sys.argv[2],research_resolver=lambda _:None,clock=lambda:datetime(2026,10,29,8,tzinfo=timezone.utc))
print(json.dumps(service.mutate(sys.argv[3],json.loads(sys.argv[4]))))
"""
        def invoke(action, request):
            result = subprocess.run([sys.executable, "-B", "-c", worker, str(Path(candidate_module.__file__).resolve()),
                str(self.root), action, json.dumps(request)], cwd=Path(__file__).resolve().parent,
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        stopped = invoke("terminal_broker_stop", self.stop_payload())
        self.assertIn("CANDIDATE_STOPPED", self.service.check(SIM, saved["config_id"])["blockers"])
        invoke("terminal_broker_resume", self.resume_payload(stopped))
        self.assertEqual(self.service.check(SIM, saved["config_id"])["status"], "OFFLINE_PREVIEW_ONLY")


def parent_fixture():
    # Only the terminal/test import root is added. Canonical dependencies must
    # belong to the supplied interpreter; no src/vendor injection or skip.
    parent = Path(os.environ.get("HAKIMI_BROKER_DRAFT_PARENT", Path(__file__).resolve().parents[3])).resolve(strict=True)
    terminal = parent / "outputs" / "python_quant_bot"
    if str(terminal) not in sys.path:
        sys.path.insert(0,str(terminal))
    path=terminal/"tests"/"test_terminal_research.py"
    spec=importlib.util.spec_from_file_location("broker_r2_native_qa",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class RealSavedResolverIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixtures=parent_fixture()
        self.temp=tempfile.TemporaryDirectory(prefix="broker-r2-real-resolver-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.now=datetime(2026,10,29,8,tzinfo=timezone.utc)
        self.network=patch("socket.socket.connect",side_effect=AssertionError("No network"))
        self.network.start();self.addCleanup(self.network.stop)

    def config(self,symbol):
        return {"account_id":"900000000000001","market":"US","asset_class":"EQUITY","asset_code":"US."+symbol,
                "currency":"USD","max_quantity":2,"max_notional":"50.00","side":"BUY","quantity":1,"limit_price":"20.00",
                "time_in_force":"DAY","expires_at":(self.now+timedelta(hours=1)).isoformat()}

    def candidate(self,resolver,reference,symbol,root):
        service=BrokerCandidateService(root,research_resolver=resolver,clock=lambda:self.now)
        saved=service.save(dict(mode=SIM,request_id="actual-save-0001",config=self.config(symbol),research_reference=reference))
        result=service.prepare_intent(dict(mode=SIM,request_id="actual-preview-0001",config_id=saved["config_id"]))
        self.assertEqual(result["status"],"UNSENT_OFFLINE_PREVIEW")
        self.assertEqual(result["intent"]["security_binding"]["status"],"MATCHED_SAVED_DECLARATION")
        self.assertTrue(all(value is False for value in result["permissions"].values()))
        self.assertFalse(result["intent"]["security_binding"]["account_verified"])
        self.assertFalse(result["intent"]["security_binding"]["asset_rules_verified"])

    def test_new_temp_native_saved_report_uses_actual_trusted_resolver_without_rerun(self):
        fixture=self.fixtures.TerminalResearchTests("runTest");fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.addCleanup(fixture.service.close)
        fixture.market["meta"].update(security_id="QA:SYNTH",currency="USD",asset_class="US_EQUITY")
        fixture.market["digest"]=self.fixtures.digest({key:value for key,value in fixture.market.items() if key!="digest"})
        task=fixture.task();report=fixture.run_task(task)
        from exchange_terminal.services.terminal_saved_results import resolve_execution_research
        reference={"kind":"terminal_run","id":report["id"]}
        resolution=resolve_execution_research(fixture.service,reference)
        self.assertNotIn("status",resolution)
        self.assertEqual(resolution["binding"]["status"],"COMPLETED")
        before={str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in fixture.core.workspace.rglob("*") if p.is_file()}
        calls=fixture.runner.call_count
        self.candidate(lambda ref:resolve_execution_research(fixture.service,ref),reference,"SYNTH",self.root/"native-candidates")
        self.assertEqual(fixture.runner.call_count,calls)
        self.assertEqual({str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in fixture.core.workspace.rglob("*") if p.is_file()},before)

    def test_new_temp_frozen_core_24_character_reference_uses_real_saved_verifier(self):
        # Loading a copied frozen package changes the private module namespace.
        # Isolate the real verifier fixture so other gate tests retain theirs.
        worker = """import importlib.util,json,sys
from pathlib import Path
path=Path(sys.argv[1]).resolve();sys.path.insert(0,str(path.parents[1]));sys.path.insert(0,str(path.parent))
spec=importlib.util.spec_from_file_location('broker_core_qa',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert Path(module.candidate_module.__file__).resolve()==Path(sys.argv[2]).resolve()
case=module.RealSavedResolverIntegrationTests('runTest');case.setUp()
try:
    case._exercise_real_frozen_verifier()
    print(json.dumps({'core_child_status':'PASSED_REAL_FROZEN_VERIFIER'}))
finally:
    case.doCleanups()
"""
        result = subprocess.run([sys.executable, "-B", "-c", worker, str(Path(__file__).resolve()), str(Path(candidate_module.__file__).resolve())],
            cwd=Path(__file__).resolve().parent, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["core_child_status"], "PASSED_REAL_FROZEN_VERIFIER")

    def _exercise_real_frozen_verifier(self):
        from exchange_terminal.services.quant_workspace import _load_kernel,_verified_package_root,_VENDOR,ACCEPTED_SOURCE_SHA256
        from exchange_terminal.services.terminal_research import TerminalResearchService
        from exchange_terminal.services.terminal_saved_results import resolve_execution_research
        source=_verified_package_root(_VENDOR)
        vendor=self.root/"installed"/"vendor"/"research";package=vendor/"hakimi_terminal_research"
        for name in json.loads((source/"runtime-files.json").read_bytes())["files"]:
            target=package/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
        kernel=_load_kernel(vendor)
        from hakimi_terminal_research import offline_app
        from hakimi_terminal_research.desktop_service import DesktopService
        from hakimi_terminal_research.environment import build_runtime_provenance
        from hakimi_terminal_research.source_identity import package_content_identity,BUILD_IDENTITY_FILENAME
        identity=package_content_identity(package)
        self.assertEqual(identity["content_sha256"],ACCEPTED_SOURCE_SHA256)
        (package/BUILD_IDENTITY_FILENAME).write_text(json.dumps({"schema_version":"research-build-source-v1",**identity,
            "git":{"commit":"","status":"UNKNOWN"},"test_scope":"TEMP_REAL_FROZEN_COPY_ONLY"}),encoding="utf-8")
        runtime=build_runtime_provenance()
        self.assertEqual(runtime["source_identity"]["status"],"BUILD_VERIFIED")
        self.assertEqual(runtime["environment_verified"]["status"],"VERIFIED")
        core=DesktopService(self.root/"new-synthetic-research")
        forbidden=Mock(side_effect=AssertionError("No native data/runner"))
        service=TerminalResearchService(core,forbidden,forbidden,forbidden,forbidden)
        self.addCleanup(service.close)
        core.mutate("initialize_demo",{})
        task=next(row for row in core.read("tasks")["items"] if row["name"]=="price")
        with patch.object(offline_app,"run_strategy",wraps=offline_app.run_strategy) as run:
            saved=core.mutate("run_task",{"task_id":task["id"]})
        self.assertEqual(run.call_count,1)
        reference={"kind":"core_run","id":saved["id"]};self.assertEqual(len(reference["id"]),24)
        resolved=resolve_execution_research(service,reference)
        before={str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in core.workspace.rglob("*") if p.is_file()}
        with patch.object(offline_app,"run_strategy",side_effect=AssertionError("No second research run")):
            self.candidate(lambda ref:resolve_execution_research(service,ref),reference,resolved["display"]["symbol"],self.root/"core-candidates")
        self.assertEqual({str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in core.workspace.rglob("*") if p.is_file()},before)
        forbidden.assert_not_called()


if __name__ == "__main__":
    unittest.main()
