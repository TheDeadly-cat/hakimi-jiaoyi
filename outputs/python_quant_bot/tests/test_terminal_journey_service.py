"""Only fresh preference databases and synthetic read fixtures; no economic run."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
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


if __name__ == "__main__":
    unittest.main()
