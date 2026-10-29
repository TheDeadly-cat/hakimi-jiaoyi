"""Actual service/resolver/loader wiring with NEW explicitly synthetic records.

No runner, SDK import, HTTP server, installed package or old workspace is used.
The TEMP package uses the loader's real manifest verifier, never a verified flag.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_package_loader as loader
from exchange_terminal.services.terminal_broker_plan_service import ACTION
from tests.test_terminal_saved_results import create_synthetic_native_saved_fixture
from tests import test_terminal_broker_execution_plan as plan_fixture
from tests import test_terminal_broker_package_loader as package_fixture


class BrokerPlanIntegrationTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "socket.socket.bind", "socket.getaddrinfo", "subprocess.Popen"):
            blocked = patch(target, side_effect=AssertionError("No external integration operations"))
            blocked.start(); self.addCleanup(blocked.stop)
        for obj, name, value in ((loader, "_anchor", None), (loader, "_anchor_invalid", False),
            (package_fixture.bootstrap, "_VERIFIED_PACKAGE", None), (package_fixture.bootstrap, "_ACTIVATED_LOADER", None)):
            changed = patch.object(obj, name, value); changed.start(); self.addCleanup(changed.stop)
        self.fixture, self.task, self.report = create_synthetic_native_saved_fixture(self)
        self.service, self.workspace = self.fixture.service, self.fixture.core.workspace
        self.reference = {"kind": "terminal_run", "id": self.report["id"]}

    def package(self):
        case = package_fixture.BrokerPackageLoaderTests("runTest")
        self.addCleanup(case.doCleanups)
        root = case.bundle()
        case.install_verified_fixture(root)
        return root

    def candidate(self):
        now = datetime.now(timezone.utc)
        config = plan_fixture.config()
        config.update(asset_code="US.SYNTH", expires_at=(now + timedelta(hours=1)).isoformat())
        result = self.service.mutate("terminal_broker_save_candidate", {"mode": plan_fixture.SIM,
            "request_id": "integration-candidate-0001", "config": config, "research_reference": self.reference})
        prepared = self.service.mutate("terminal_broker_prepare_intent", {"mode": plan_fixture.SIM,
            "request_id": "integration-intent-0001", "config_id": result["config_id"]})
        bounds = plan_fixture.bounds(); bounds["valid_until"] = (now + timedelta(minutes=10)).isoformat()
        return {"mode": plan_fixture.SIM, "request_id": "integration-plan-0001", "config_id": result["config_id"],
            "intent_id": prepared["intent"]["id"], "expected_control_revision": 0, "bounds": bounds}

    def read(self, resource, payload):
        return self.service.read(resource, json.dumps(payload))

    def retained(self):
        return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.workspace.rglob("*")
                if p.is_file() and "broker-plans-v1" not in p.parts}

    def test_production_factory_uses_real_repository_loader_and_lazy_reads(self):
        before = self.retained()
        capabilities = self.read("terminal_broker_plan_capabilities", {"mode": plan_fixture.SIM})
        self.assertEqual(capabilities["status"], "NOT_PACKAGED")
        self.assertIs(self.service._broker_plan_service._loader, loader.load_broker_runtime_identity)
        self.assertEqual(self.read("terminal_broker_plans", {"mode": plan_fixture.SIM})["requests"], [])
        self.assertEqual(self.read("terminal_broker_plan_receipt", {"mode": plan_fixture.SIM, "request_id": "missing-request-0001"})["status"], "NOT_RECORDED")
        self.assertFalse((self.workspace / "broker-plans-v1").exists())
        self.assertFalse((self.workspace / "broker-candidates-v2").exists())
        self.assertEqual(self.retained(), before)
        self.fixture.runner.assert_not_called()

    def test_real_saved_resolver_original_candidate_manifest_loader_to_plan_without_research(self):
        self.package()
        payload = self.candidate()
        before = self.retained()
        old_research = self.read("terminal_broker_research", {"reference": self.reference})
        self.assertNotIn("source_hash", old_research["binding"])
        self.assertNotIn("recorded_source_identity", old_research)
        with patch("exchange_terminal.services.terminal_research._engine_source_identity", side_effect=AssertionError("No today's-source substitution")), \
             patch.object(self.service, "fingerprint", side_effect=AssertionError("No recomputation")):
            value = self.service.mutate(ACTION, payload)
        self.assertEqual(value["status"], "PLAN_SAVED")
        plan = self.read("terminal_broker_plan", {"mode": payload["mode"], "plan_id": value["result"]["plan_id"]})["plan"]
        self.assertEqual(plan["research"]["recorded_source"]["record"]["source_files"], self.task["engine_source_identity"])
        self.assertEqual(plan["research"]["resolution"]["reference"], self.reference)
        self.assertEqual(plan["candidate_intent"]["id"], payload["intent_id"])
        self.assertEqual(plan["order"]["asset_code"], "US.SYNTH")
        self.assertEqual(plan["research_eligibility"]["status"], "SYNTHETIC_OFFLINE_ONLY")
        self.assertFalse(plan["research_eligibility"]["external_research_eligible"])
        self.assertFalse(any(value["permissions"].values()))
        self.assertFalse(any(plan["permissions"].values()))
        self.assertEqual(self.retained(), before)
        self.assertEqual(self.read("terminal_broker_plan_receipt", {"mode": payload["mode"], "request_id": payload["request_id"]})["receipt"], value["receipt"])
        self.fixture.runner.assert_not_called()

    def test_original_receipt_and_plan_survive_package_change_but_new_prepare_refuses(self):
        root = self.package(); payload = self.candidate()
        original = self.service.mutate(ACTION, payload)
        changed = root / loader.LOADER_PATH
        changed.write_bytes(changed.read_bytes() + b"\n# explicitly altered TEMP fixture\n")
        with self.assertRaisesRegex(loader.PackageLoaderError, "PACKAGE_CHANGED"):
            self.read("terminal_broker_plan_capabilities", {"mode": payload["mode"]})
        self.assertEqual(self.read("terminal_broker_plan_receipt", {"mode": payload["mode"], "request_id": payload["request_id"]})["receipt"], original["receipt"])
        self.assertEqual(self.service.mutate(ACTION, payload)["receipt"], original["receipt"])
        refused = self.service.mutate(ACTION, {**payload, "request_id": "integration-plan-0002"})
        self.assertEqual(refused["result"]["reason"], "PACKAGE_CHANGED")
        self.assertEqual(refused["status"], "PLAN_NOT_CREATED")
        listing = self.read("terminal_broker_plans", {"mode": payload["mode"]})
        self.assertEqual(len(listing["items"]), 1); self.assertEqual(len(listing["requests"]), 2)
        self.fixture.runner.assert_not_called()

    def test_stale_control_rejects_and_renderer_cannot_supply_package_or_originals(self):
        self.package(); payload = self.candidate()
        for key in ("runtime", "research", "config", "intent", "workspace", "permissions"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.service.mutate(ACTION, {**payload, key: deepcopy(payload)})
        self.assertFalse((self.workspace / "broker-plans-v1").exists())
        stopped = self.service.stop_broker_candidate({"mode": payload["mode"], "request_id": "integration-stop-0001", "reason": "explicit local stop"})
        self.assertEqual(stopped["status"], "STOPPED")
        result = self.service.mutate(ACTION, payload)
        self.assertEqual(result["status"], "PLAN_NOT_CREATED")
        self.assertIsNone(result["result"]["plan_id"])
        self.assertEqual(self.read("terminal_broker_plans", {"mode": payload["mode"]})["items"], [])
        self.fixture.runner.assert_not_called()

    def test_sdk_changed_during_actual_resolver_is_detected_by_later_fresh_loader(self):
        root = self.package(); payload = self.candidate()
        plans = self.service._broker_plans()
        original_resolver = plans._resolver
        def resolve_then_change(reference):
            value = original_resolver(reference)
            sdk = root / package_fixture.SDK
            sdk.write_bytes(sdk.read_bytes() + b"\n# TEMP SDK changed while saved-result resolution was pending\n")
            return value
        with patch.object(plans, "_resolver", side_effect=resolve_then_change):
            result = self.service.mutate(ACTION, payload)
        self.assertEqual(result["status"], "PLAN_NOT_CREATED")
        self.assertEqual(result["result"]["reason"], "PACKAGE_CHANGED")
        self.assertEqual(self.read("terminal_broker_plans", {"mode": payload["mode"]})["items"], [])
        self.fixture.runner.assert_not_called()

    def test_terminal_service_close_marks_plan_service_closed_without_recovery_writes(self):
        payload = self.candidate()
        result = self.service.mutate(ACTION, payload)
        self.assertEqual(result["result"]["reason"], "NOT_PACKAGED")
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.workspace.rglob("*") if p.is_file()}
        plan_service = self.service._broker_plan_service
        self.service.close()
        with self.assertRaisesRegex(ValueError, "service_closed"): plan_service.plans(payload["mode"])
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.workspace.rglob("*") if p.is_file()})
        self.fixture.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
