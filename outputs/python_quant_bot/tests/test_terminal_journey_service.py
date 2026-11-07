"""Only fresh preference databases and synthetic read fixtures; no economic run."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from exchange_terminal.services.terminal_journey_service import TerminalJourneyService, _json
from exchange_terminal.services.terminal_broker_candidate_service import _project_research


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.calls = []
        self.ref = dict(kind="terminal_run", id="a"*64)
        self.binding = dict(schema_version="hakimi-offline-research-binding-v1", status="COMPLETED", engine_id="native", strategy_id="dual_ma", strategy_params={"fast": 5}, task_id="b"*64, task_version=1, input_id="c"*64, report_id="a"*64, report_hash="a"*64)
        self.research = dict(reference=self.ref, binding=self.binding, display={}, assumptions={})
        self.selected = dict(task=dict(kind="terminal_task", id="b"*64, task_id="b"*64), research=self.ref, view="continuous", replay={"account_id":"replay-one"}, manual={"account_id":"manual-one", "plan_id":"d"*64}, broker=dict(mode="OFFICIAL_SIMULATION", config_id="e"*64, intent_id="f"*64, plan_id="1"*64))
        projection = _project_research(self.research, self.ref)
        self.config = dict(config_id="e"*64, research_reference=self.ref, research_binding_sha256=sha256(_json(projection).encode()).hexdigest(), config={"account_id":"123"})
        self.intent = dict(id="f"*64, mode="OFFICIAL_SIMULATION", config_id="e"*64, research_sha256=self.config["research_binding_sha256"])
        self.plan = dict(id="1"*64, mode="OFFICIAL_SIMULATION", candidate_config={"id":"e"*64}, candidate_intent={"id":"f"*64}, research={"resolution":projection})
        self.records = {"terminal_execution_research":self.research, "terminal_tasks":{"task_id":"b"*64}, "terminal_replay_status":{"account_id":"replay-one", "display_summary":{"reference":self.ref}}, "terminal_execution_account":{"account_id":"manual-one", "ledger":{"plans":[{"plan_id":"d"*64,"research_binding":self.binding}]}}, "terminal_broker_status":{"modes":[{"mode":"OFFICIAL_SIMULATION", "configurations":[self.config]}]}, "terminal_broker_receipts":{"items":[{"result":{"intent":self.intent}}]}, "terminal_broker_plan":{"status":"FOUND","plan":self.plan}}
        self.service = TerminalJourneyService(self.workspace, reader=self.read)

    def read(self, resource, identity=None):
        self.calls.append((resource,identity))
        value = self.records[resource]
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    def save(self, request="selection-0001", revision=0, selected=None, service=None):
        target=service or self.service
        return target.save(dict(request_id=request, workspace_context=target.context, expected_revision=revision, selection=deepcopy(selected or self.selected)))

    def test_empty_read_creates_no_workspace(self):
        value = self.service.read()
        self.assertEqual(value["status"], "EMPTY")
        self.assertFalse(self.workspace.exists())
        self.assertEqual(self.calls, [])

    def test_restart_same_workspace_resolves_exact_originals_read_only(self):
        self.save()
        before = {p: (p.read_bytes(),p.stat().st_mtime_ns) for p in self.workspace.rglob('*') if p.is_file()}
        other = TerminalJourneyService(self.workspace, reader=self.read)
        value = other.read()
        self.assertEqual(value["selection"], self.selected)
        self.assertEqual(value["workspace_context"], self.service.context)
        self.assertTrue(all(v["status"] == "VERIFIED" for v in value["resolution"].values()))
        self.assertEqual(before, {p: (p.read_bytes(),p.stat().st_mtime_ns) for p in before})
        self.assertEqual(value["new_economic_runs"], 0)

    def test_cas_idempotency_and_unchanged(self):
        first = self.save()
        self.assertEqual(first["revision"], 1)
        self.assertTrue(self.save()["replayed"])
        self.assertEqual(self.save("selection-0002", 0)["status"], "REVISION_CONFLICT")
        self.assertEqual(self.save("selection-0003", 1)["status"], "UNCHANGED")
        changed = deepcopy(self.selected); changed["view"]="broker"
        with self.assertRaisesRegex(ValueError, "request_id_payload_conflict"):
            self.save(selected=changed)
        self.assertEqual(self.service.read()["revision"], 1)

    def test_two_instances_cannot_overwrite_one_revision(self):
        self.save()
        second=TerminalJourneyService(self.workspace, reader=self.read)
        a=deepcopy(self.selected); a["view"]="broker"
        b=deepcopy(self.selected); b["view"]="execution"
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(self.save,"concurrent-0001",1,a),pool.submit(self.save,"concurrent-0002",1,b,second)]
            values=[f.result() for f in futures]
        self.assertEqual(sorted(v["status"] for v in values),["REVISION_CONFLICT","SAVED"])

    def test_missing_source_and_changed_task_retain_refs_and_other_nodes(self):
        self.save()
        self.records["terminal_execution_research"]=ValueError("source_original_unavailable")
        self.records["terminal_tasks"]={"task_id":"new-task"}
        value=self.service.read()
        self.assertEqual(value["selection"],self.selected)
        self.assertEqual(value["resolution"]["research"]["status"],"UNAVAILABLE")
        self.assertEqual(value["resolution"]["task"]["status"],"VERSION_CHANGED")
        self.assertEqual(value["resolution"]["replay"]["status"],"VERIFIED")
        self.assertTrue(value["resolution"]["manual"]["original_reference_retained"])

    def test_same_labels_cannot_replace_report_or_plan_binding(self):
        self.save()
        self.records["terminal_replay_status"]["display_summary"]["reference"]={"kind":"terminal_run","id":"9"*64}
        self.records["terminal_execution_account"]["ledger"]["plans"][0]["research_binding"]={**self.binding,"task_id":"different"}
        self.plan["candidate_intent"]={"id":"8"*64}
        value=self.service.read()
        for name in ("replay","manual","broker"):
            self.assertEqual(value["resolution"][name]["status"],"BINDING_MISMATCH")
        self.assertEqual(value["resolution"]["research"]["status"],"VERIFIED")

    def test_same_report_reference_with_changed_broker_digest_is_rejected(self):
        self.save(); self.config["research_binding_sha256"]="0"*64
        self.assertEqual(self.service.read()["resolution"]["broker"]["status"],"BINDING_MISMATCH")

    def test_foreign_workspace_store_not_adopted(self):
        self.save()
        target=Path(self.temp.name)/"foreign"
        shutil.copytree(self.workspace,target)
        with self.assertRaisesRegex(ValueError,"workspace_or_store_mismatch"):
            TerminalJourneyService(target,reader=self.read).read()

    def test_old_window_cannot_write_same_revision_in_other_workspace(self):
        other=TerminalJourneyService(Path(self.temp.name)/"other",reader=self.read)
        with self.assertRaisesRegex(ValueError,"workspace_context_mismatch"):
            other.save(dict(request_id="selection-0001",workspace_context=self.service.context,expected_revision=0,selection=self.selected))
        self.assertFalse(other.workspace.exists())

    def test_only_opaque_refs_accepted_no_authority_or_paths(self):
        for change in ({"secret":"token"},{"manual":{"account_id":"../account","plan_id":None}},{"research":{"kind":"terminal_run","id":"a","parameters":{}}}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.save(selected={**self.selected,**change})
        self.assertFalse(self.workspace.exists())

    @staticmethod
    def short_path(path):
        """Ask Windows for a real alias; never fake Path.resolve or _safe."""
        import ctypes
        from ctypes import wintypes
        get_short = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_short.restype = wintypes.DWORD
        size = get_short(str(path), None, 0)
        if not size:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_unicode_buffer(size)
        if not get_short(str(path), buffer, size):
            raise ctypes.WinError(ctypes.get_last_error())
        return Path(buffer.value)

    @unittest.skipUnless(os.name == "nt", "real Windows path aliases")
    def test_real_short_parent_empty_read_does_not_create_workspace(self):
        parent = Path(self.temp.name) / "Long Journey Parent Directory"
        parent.mkdir()
        short = self.short_path(parent)
        self.assertTrue(short.samefile(parent))
        self.assertNotEqual(os.path.normcase(str(short)), os.path.normcase(str(parent.resolve())))
        missing = short / "Uncreated Journey Workspace"
        service = TerminalJourneyService(missing, reader=self.read)
        self.assertEqual(service.read()["status"], "EMPTY")
        self.assertEqual(service.workspace, missing.resolve())
        self.assertFalse(missing.exists())
        self.assertEqual(self.calls, [])

    @unittest.skipUnless(os.name == "nt", "real Windows short and case aliases")
    def test_real_short_root_save_reopens_same_store_through_long_and_case_aliases(self):
        physical = Path(self.temp.name) / "Long Journey Workspace Directory"
        physical.mkdir()
        short = self.short_path(physical)
        self.assertTrue(short.samefile(physical))
        self.assertNotEqual(os.path.normcase(str(short)), os.path.normcase(str(physical.resolve())))
        aliased = TerminalJourneyService(short, reader=self.read)
        expected_context = TerminalJourneyService(physical, reader=self.read).context
        self.assertEqual(aliased.context, expected_context)
        self.assertEqual(self.save(service=aliased)["revision"], 1)
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in physical.rglob('*') if p.is_file()}
        upper = Path(str(physical).upper())
        self.assertTrue(upper.samefile(physical))
        for spelling in (physical, upper, short):
            reopened = TerminalJourneyService(spelling, reader=self.read)
            value = reopened.read()
            self.assertEqual(reopened.path, aliased.path)
            self.assertEqual(value["workspace_context"], expected_context)
            self.assertEqual(value["selection"], self.selected)
            self.assertEqual(value["revision"], 1)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_canonical_root_still_rejects_an_outside_store_before_creating_files(self):
        outside = Path(self.temp.name) / "outside" / "store.sqlite3"
        self.service.path = outside
        with self.assertRaisesRegex(ValueError, "history_path_outside_workspace"):
            self.service.read()
        self.assertFalse(outside.parent.exists())
        self.assertFalse(self.workspace.exists())

    def test_existing_workspace_replacement_is_not_adopted(self):
        self.workspace.mkdir()
        service = TerminalJourneyService(self.workspace, reader=self.read)
        retained = Path(self.temp.name) / "retained-workspace"
        root = Path(self.temp.name).resolve()
        self.assertTrue(self.workspace.resolve().is_relative_to(root))
        self.assertTrue(retained.resolve().is_relative_to(root))
        self.workspace.rename(retained)
        self.workspace.mkdir()
        with self.assertRaisesRegex(ValueError, "journey_workspace_replaced"):
            service.read()
        self.assertFalse((self.workspace / "ui").exists())
        self.assertFalse((retained / "ui").exists())

    def test_raw_workspace_and_store_parent_links_are_rejected_before_resolution(self):
        root = Path(self.temp.name)
        physical = root / "physical-workspace"
        physical.mkdir()
        link = root / "linked-workspace"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(physical), str(link))
        else:
            link.symlink_to(physical, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "history_reparse_path_not_supported"):
            TerminalJourneyService(link, reader=self.read)
        self.workspace.mkdir()
        if os.name == "nt":
            _winapi.CreateJunction(str(physical), str(self.workspace / "ui"))
        else:
            (self.workspace / "ui").symlink_to(physical, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "history_reparse_path_not_supported"):
            self.service.read()
        self.assertEqual(list(physical.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
