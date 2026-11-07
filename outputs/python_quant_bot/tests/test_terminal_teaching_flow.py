"""One fictional input through the real frozen importer; no task or research."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from threading import RLock
import base64
import json
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.quant_workspace import _load_kernel
from exchange_terminal.services.terminal_teaching_flow import prepare_teaching_input, PARAMS


def hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()} if root.exists() else {}


class TeachingInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = _load_kernel()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="teaching-input-only-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.core = self.kernel.service(self.root / "workspace")
        self.service = SimpleNamespace(core=self.core, workspace=self.core.workspace,
                                       _lock=RLock(), _safe=self.core._safe)
        self.addCleanup(patch.stopall)
        patch("socket.socket.connect", side_effect=AssertionError("No network")).start()
        patch("hakimi_terminal_research.trade_cli.initialize_demo", side_effect=AssertionError("No two-task demo")).start()
        patch("hakimi_terminal_research.task_manager.create_family", side_effect=AssertionError("No task creation")).start()
        patch("hakimi_terminal_research.backtest.BacktestEngine.run", side_effect=AssertionError("No research")).start()

    def test_first_prepare_imports_one_real_verified_input_without_tasks_or_runs(self):
        self.assertFalse(self.core.workspace.exists())
        result = prepare_teaching_input(self.service, {})
        self.assertEqual(result["schema_version"], "terminal-teaching-input-v1")
        self.assertEqual(result["status"], "READY")
        self.assertFalse(result["reused"])
        self.assertEqual(result["params"], PARAMS)
        self.assertEqual((result["strategy_key"], result["sessions"], result["currency"]), ("price.dual_ma@1", 22, "USD"))
        self.assertEqual((result["new_tasks"], result["new_economic_runs"]), (0, 0))
        self.assertFalse(result["source_truth_verified"])
        self.assertTrue(result["permissions"]["research_only"])
        self.assertFalse(any(result["permissions"][key] for key in ("paper_allowed", "live_allowed", "order_allowed")))
        inputs = self.core.read("inputs")["items"]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0]["id"], result["input_id"])
        self.assertEqual(inputs[0]["input_id"], result["snapshot_id"])
        self.assertEqual(inputs[0]["evidence_kind"], "SYNTHETIC_TEST")
        self.assertEqual(self.core.read("tasks")["items"], [])
        self.assertEqual(self.core.read("runs")["items"], [])

    def test_repeated_explicit_preparation_reuses_original_id_and_every_saved_byte(self):
        first = prepare_teaching_input(self.service, {})
        before = hashes(self.core.workspace)
        with patch.object(self.core, "mutate", side_effect=AssertionError("Existing input must not be imported again")):
            second = prepare_teaching_input(self.service, {})
        self.assertTrue(second["reused"])
        self.assertEqual(second["input_id"], first["input_id"])
        self.assertEqual(hashes(self.core.workspace), before)
        self.assertEqual(self.core.read("tasks")["items"], [])

    def test_semantically_identical_pretty_original_is_reused_without_canonical_rewrite(self):
        from importlib.resources import files
        from hakimi_terminal_research.equity_dataset import build_equity_snapshot
        from hakimi_terminal_research.documents import parse_document
        resources=files("hakimi_terminal_research").joinpath("resources")
        snapshot=build_equity_snapshot(resources.joinpath("trade-demo.csv").read_bytes(),parse_document(resources.joinpath("trade-demo-import.json").read_bytes())).document
        raw=(json.dumps(snapshot, ensure_ascii=False, indent=3)+"\n").encode()
        saved=self.core.mutate("import_document",{"filename":"old-teaching.json","document_base64":base64.b64encode(raw).decode()})
        before=hashes(self.core.workspace)
        result=prepare_teaching_input(self.service,{})
        self.assertEqual(result["input_id"], saved["id"])
        self.assertTrue(result["reused"])
        self.assertEqual(hashes(self.core.workspace),before)

    def test_rejected_payloads_do_not_create_or_read_a_workspace(self):
        for payload in (None, [], {"run": True}, {"initial_cash": 100}, {"filename":"outside.json"}):
            with self.subTest(payload=payload), patch.object(self.core,"read",side_effect=AssertionError("No read")), self.assertRaisesRegex(ValueError,"empty_payload"):
                prepare_teaching_input(self.service,payload)
        self.assertFalse(self.core.workspace.exists())

    def test_incomplete_inventory_and_conflicting_existing_identity_never_import(self):
        with patch.object(self.core,"read",return_value={"items":[],"warnings":["Existing record unreadable"]}), patch.object(self.core,"mutate",side_effect=AssertionError("No import")):
            with self.assertRaisesRegex(ValueError,"inventory_incomplete"):
                prepare_teaching_input(self.service,{})
        first=prepare_teaching_input(self.service,{})
        bad=deepcopy(first["input"]);bad["evidence_kind"]="IMPORTED_UNVERIFIED"
        before=hashes(self.core.workspace)
        with patch.object(self.core,"read",return_value={"items":[bad],"warnings":[]}), patch.object(self.core,"mutate",side_effect=AssertionError("No import")):
            with self.assertRaisesRegex(ValueError,"existing_identity"):
                prepare_teaching_input(self.service,{})
        self.assertEqual(hashes(self.core.workspace),before)

    def test_partial_or_foreign_workspace_is_retained_without_repair(self):
        self.core.workspace.mkdir()
        marker=self.core.workspace/"preserve.txt";marker.write_text("Unrelated original",encoding="utf-8")
        before=hashes(self.core.workspace)
        with self.assertRaisesRegex(ValueError,"workspace_not_initialized"):
            prepare_teaching_input(self.service,{})
        self.assertEqual(hashes(self.core.workspace),before)


if __name__ == "__main__":
    unittest.main()
