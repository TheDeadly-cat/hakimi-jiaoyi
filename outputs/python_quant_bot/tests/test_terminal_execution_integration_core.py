"""New synthetic workspaces only: real frozen core and native family admission.

No existing workspace, historical UNKNOWN, provider, HTTP host or native window
is opened. The core case explicitly initializes its labelled synthetic example
and runs it once; every subsequent operation uses only the saved identities.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.quant_workspace import _load_kernel, _verified_package_root, _VENDOR, ACCEPTED_SOURCE_SHA256
from exchange_terminal.services.terminal_research import TerminalResearchService, _seal
from exchange_terminal.services.terminal_saved_results import resolve_execution_research
from tests import test_terminal_research as native_fixtures


def retained_inventory(workspace):
    """Exclude only the new account ledger, retain bytes and modification times."""
    return {path.relative_to(workspace).as_posix(): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for path in workspace.rglob("*") if path.is_file()
            and path.relative_to(workspace).parts[0] != "offline-execution"}


def account_payload(security_id, symbol):
    return dict(client_request_id="core-integration-create-0001", account_id="core-integration-synthetic",
        label="明确的全新合成账户", evidence_kind="SYNTHETIC_TEST", initial_cash="1000",
        securities={security_id: {"symbol": symbol, "tick_size": "0.01"}},
        rules=dict(max_order_notional="500", max_total_exposure="800", max_security_exposure="500",
                   cash_floor="100", fee_buffer="1", max_account_loss="200", quote_max_age_ms=60000))


class CoreSavedExecutionIntegrationTests(unittest.TestCase):
    def test_real_frozen_core_saved_result_binds_plan_without_second_run(self):
        # A fresh process prevents the installed TEMP package from replacing a
        # kernel already loaded by another test. It never starts an HTTP host.
        # Match the gate's terminal import root while keeping canonical imports
        # owned by sys.executable's installed environment, not a PYTHONPATH shim.
        completed = subprocess.run([sys.executable, "-m", "tests.test_terminal_execution_integration_core", "--installed-core-child"],
                                   cwd=Path(__file__).resolve().parents[1],
                                   capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def exercise_installed_core_saved_result(self):
        with tempfile.TemporaryDirectory(prefix="hakimi-new-core-execution-") as temp:
            source = _verified_package_root(_VENDOR)
            vendor = Path(temp) / "installed" / "vendor" / "research"
            package = vendor / "hakimi_terminal_research"
            files = json.loads((source / "runtime-files.json").read_bytes())["files"]
            for name in files:
                destination = package / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / name, destination)
            kernel = _load_kernel(vendor)
            from hakimi_terminal_research import offline_app
            from hakimi_terminal_research.desktop_service import DesktopService
            from hakimi_terminal_research.environment import build_runtime_provenance
            from hakimi_terminal_research.source_identity import package_content_identity, BUILD_IDENTITY_FILENAME
            # Same installed-source receipt mechanism as setup.py and
            # test_packaging_provenance: hash actual copied bytes, never patch
            # VERIFIED status, dependencies or the immutable runtime manifest.
            identity = package_content_identity(package)
            self.assertEqual(identity["content_sha256"], ACCEPTED_SOURCE_SHA256)
            receipt = {"schema_version": "research-build-source-v1", **identity,
                       "git": {"commit": "", "status": "UNKNOWN"},
                       "test_scope": "TEMP_INSTALLED_COPY_OF_ACCEPTED_FROZEN_BYTES"}
            (package / BUILD_IDENTITY_FILENAME).write_text(json.dumps(receipt), encoding="utf-8")
            runtime = build_runtime_provenance()
            self.assertEqual(runtime["source_identity"]["status"], "BUILD_VERIFIED")
            self.assertEqual(runtime["environment_verified"]["status"], "VERIFIED")
            workspace = Path(temp) / "explicit-synthetic-workspace"
            core = DesktopService(workspace)
            self.assertEqual(type(core).__module__, "hakimi_terminal_research.desktop_service")
            self.assertTrue(Path(offline_app.__file__).resolve().is_relative_to(kernel.root))
            native_reader = Mock(side_effect=AssertionError("no native market source in core readback"))
            native_runner = Mock(side_effect=AssertionError("no native research computation in core readback"))
            native_catalog = Mock(side_effect=AssertionError("core does not use the native catalog"))
            native_fingerprint = Mock(side_effect=AssertionError("core does not use native fingerprints"))
            service = TerminalResearchService(core, native_reader, native_catalog, native_runner, native_fingerprint)
            try:
                initialized = core.mutate("initialize_demo", {})
                self.assertTrue(initialized["initialized"])
                header = json.loads((workspace / "workspace.json").read_bytes())
                self.assertEqual(header["data_kind"], "SYNTHETIC_TEST")
                task = next(row for row in core.read("tasks")["items"] if row["name"] == "price")
                with patch.object(offline_app, "run_strategy", wraps=offline_app.run_strategy) as original_run:
                    saved = core.mutate("run_task", {"task_id": task["id"]})
                self.assertEqual(original_run.call_count, 1)
                self.assertEqual(saved["operation"], "RUN_REQUEST_COMPLETED")
                manifest, report, snapshot = offline_app.verify_run(core._lookup("runs", saved["id"]))
                self.assertEqual(snapshot.document["evidence_kind"], "SYNTHETIC_TEST")
                reference = {"kind": "core_run", "id": saved["id"]}
                before = retained_inventory(workspace)

                with patch.object(offline_app, "run_strategy", side_effect=AssertionError("saved read must never recompute")) as forbidden_run:
                    resolved = resolve_execution_research(service, reference)
                    self.assertEqual(resolved["owner_id"], "task:" + manifest["task_id"])
                    self.assertEqual(resolved["binding"]["task_id"], manifest["task_id"])
                    self.assertEqual(resolved["binding"]["report_hash"], report["report_hash"])
                    self.assertEqual(resolved["binding"]["strategy_params"], report["spec"]["strategy"]["params"])
                    self.assertEqual(resolved["binding"]["security_id"], snapshot.document["security"]["security_id"])
                    self.assertEqual(resolved["display"]["symbol"], snapshot.document["security"]["symbol"])
                    self.assertEqual(resolved["display"]["currency"], "USD")
                    self.assertEqual(resolved["display"]["asset_class"], "US_EQUITY")
                    view = service.read("terminal_execution_research", json.dumps({"reference": reference}))
                    self.assertEqual(view["binding"], resolved["binding"])
                    self.assertEqual(view["owner_continuity"], "IMMUTABLE_TASK_ONLY_NO_CROSS_VERSION_CONTINUITY")
                    self.assertFalse((workspace / "offline-execution").exists())
                    self.assertEqual(retained_inventory(workspace), before)

                    creation = account_payload(resolved["display"]["security_id"], resolved["display"]["symbol"])
                    created = service.mutate("terminal_execution_create_account", creation)
                    result = service.mutate("terminal_execution_create_plan", dict(
                        client_request_id="core-integration-plan-0001", account_id=creation["account_id"],
                        account_context=created["account_context"], reference=reference, stage="SIMULATION"))
                    self.assertEqual(result["receipt"]["outcome"]["status"], "PLAN_SAVED")
                    ledger = result["account"]["ledger"]
                    self.assertEqual(len(ledger["plans"]), 1)
                    self.assertEqual(ledger["plans"][0]["research_binding"], resolved["binding"])
                    self.assertEqual(ledger["orders"], [])
                    self.assertEqual(ledger["positions"], [])
                    link = result["account"]["plan_links"][0]
                    self.assertEqual(link["owner_source"], resolved["owner_id"])
                    self.assertEqual(link["owner_continuity"], "IMMUTABLE_TASK_ONLY_NO_CROSS_VERSION_CONTINUITY")
                    for permissions in (view["permissions"], result["permissions"], result["receipt"]["permissions"]):
                        for key in ("paper_order_allowed", "live_order_allowed", "order_allowed", "broker_connection_allowed", "model_calls_allowed"):
                            self.assertIs(permissions[key], False)
                    self.assertEqual(service.read("terminal_execution_research", json.dumps({"reference": reference}))["binding"], resolved["binding"])
                    self.assertEqual(retained_inventory(workspace), before)
                    self.assertEqual(len(list((workspace / "runs").glob("run-*"))), 1)
                    forbidden_run.assert_not_called()
                for callback in (native_reader, native_runner, native_catalog, native_fingerprint):
                    callback.assert_not_called()
                store = service._execution_service._stores[creation["account_id"]]["store"]
                service.close()
                with self.assertRaises(Exception):
                    store.snapshot()
            finally:
                service.close()


class NativeFamilyExecutionRejectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixtures.TerminalResearchTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.addCleanup(self.service.close)
        self.workspace = self.fixture.core.workspace
        self.fixture.market["meta"].update(security_id="QA:SYNTH", currency="USD", asset_class="US_EQUITY")
        self.fixture.market["digest"] = native_fixtures.digest({key: value for key, value in self.fixture.market.items() if key != "digest"})
        self.first = self.fixture.task()
        self.second = self.fixture.task(parent_task_id=self.first["id"], strategy_params={"fast_window": 7, "slow_window": 45})
        self.saved = self.fixture.run_task(self.second)
        self.assertEqual(self.saved["status"], "COMPLETED")
        self.reference = {"kind": "terminal_run", "id": self.saved["id"]}
        self.created = self.service.mutate("terminal_execution_create_account", account_payload("QA:SYNTH", "SYNTH"))
        self.family = self.workspace / "terminal-tasks" / self.first["family_id"]

    def assert_rejected_without_repair(self, reason):
        before, runs = retained_inventory(self.workspace), self.fixture.runner.call_count
        account_before = self.service.read("terminal_execution_account", self.created["account_id"])
        # Saved task/input/report identities remain independently verifiable.
        self.assertEqual(self.service.read("terminal_runs", self.saved["id"])["status"], "COMPLETED")
        for call in (
            lambda: resolve_execution_research(self.service, self.reference),
            lambda: self.service.read("terminal_execution_research", json.dumps({"reference": self.reference})),
            lambda: self.service.mutate("terminal_execution_create_plan", dict(
                client_request_id="native-rejected-plan-0001", account_id=self.created["account_id"],
                account_context=self.created["account_context"], reference=self.reference, stage="SIMULATION")),
        ):
            with self.assertRaisesRegex(ValueError, reason):
                call()
        after = self.service.read("terminal_execution_account", self.created["account_id"])
        self.assertEqual(after["ledger"], account_before["ledger"])
        self.assertEqual(after["ledger"]["plans"], [])
        self.assertEqual(after["ledger"]["orders"], [])
        receipt = self.service.read("terminal_execution_receipt", json.dumps({
            "account_id": self.created["account_id"], "request_id": "native-rejected-plan-0001"}))
        self.assertEqual(receipt["status"], "NOT_RECORDED")
        self.assertEqual(retained_inventory(self.workspace), before)
        self.assertEqual(self.fixture.runner.call_count, runs)

    def test_resealed_broken_family_previous_hash_rejects_without_repair(self):
        path = self.family / "journal" / "000002.json"
        event = json.loads(path.read_bytes())
        event.pop("id")
        event["previous_hash"] = "a" * 64
        # Valid self-hash must not hide a broken cross-event chain.
        path.write_text(json.dumps(_seal(event)), encoding="utf-8")
        self.assert_rejected_without_repair("terminal_task_journal_invalid")

    def test_uncommitted_later_version_rejects_without_recreating_missing_journal(self):
        # Remove only a newly created TEMP fixture event to model lost commit.
        (self.family / "journal" / "000002.json").unlink()
        self.assertEqual(self.service._family(self.first["family_id"])["task_id"], self.first["id"])
        self.assert_rejected_without_repair("execution_research_family_version_uncommitted")
        self.assertFalse((self.family / "journal" / "000002.json").exists())

    def test_same_version_uncommitted_sibling_rejects_despite_valid_current_chain(self):
        original = json.loads((self.family / "versions" / (self.second["id"] + ".json")).read_bytes())
        original.pop("id")
        original["title"] = "全新合成分叉：此版本才被当前日志提交"
        sibling = _seal(original)
        sibling_path = self.family / "versions" / (sibling["id"] + ".json")
        with sibling_path.open("x", encoding="utf-8") as stream:
            json.dump(sibling, stream)
        event_path = self.family / "journal" / "000002.json"
        event = json.loads(event_path.read_bytes())
        event.pop("id")
        event["task_id"] = sibling["id"]
        event_path.write_text(json.dumps(_seal(event)), encoding="utf-8")
        current = self.service._family(self.first["family_id"])
        self.assertEqual(current["version"], self.second["version"])
        self.assertEqual(current["task_id"], sibling["id"])
        self.assert_rejected_without_repair("execution_research_not_in_verified_family")


if __name__ == "__main__":
    if sys.argv[1:] == ["--installed-core-child"]:
        suite = unittest.TestSuite([CoreSavedExecutionIntegrationTests("exercise_installed_core_saved_result")])
        sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
    unittest.main()
