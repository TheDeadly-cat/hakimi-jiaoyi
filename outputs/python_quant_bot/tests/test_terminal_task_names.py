from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.quant_workspace import _load_kernel
from exchange_terminal.services.terminal_research import TerminalResearchService
from exchange_terminal.services.terminal_task_names import core_task_name_payload


class TaskNameTests(unittest.TestCase):
    def test_ordinary_names_have_stable_internal_identity_and_keep_display_text(self):
        for name in ("r3 原生流程验证 20261029", "AAPL / 均线（5,20）", "CON"):
            source = {"name": name, "task_id": "old-id"}
            normalized = core_task_name_payload(source)
            self.assertEqual(normalized["title"], name)
            self.assertRegex(normalized["name"], r"^named-[0-9a-f]{32}$")
            self.assertEqual(normalized, core_task_name_payload(source))
            self.assertEqual(source["name"], name)
        self.assertEqual(core_task_name_payload({"name": "原任务-123"}), {"name": "原任务-123"})
        for name in ("", " ", "x\ny", "x\0y", "x" * 65):
            with self.assertRaises(ValueError):
                core_task_name_payload({"name": name})

    def test_real_core_copy_keeps_chinese_display_name_without_overwriting_source(self):
        kernel = _load_kernel()
        with tempfile.TemporaryDirectory(prefix="terminal-names-fixture-") as directory:
            core = kernel.service(Path(directory) / "workspace")
            service = TerminalResearchService(core, lambda *args, **kwargs: None, lambda: [],
                lambda **kwargs: self.fail("No economic runner allowed"), lambda *args: "unused")
            core.mutate("initialize_demo", {})
            source = next(item for item in core.read("tasks")["items"] if item["strategy"] == "price.dual_ma@1")
            before = {str(path): sha256(path.read_bytes()).hexdigest() for path in core.workspace.rglob("*") if path.is_file()}
            result = service.mutate("copy_task", {"task_id": source["id"], "name": "原生验证 含空格"})
            self.assertEqual(result["title"], "原生验证 含空格")
            self.assertNotEqual(result["id"], source["id"])
            self.assertEqual(core.read("runs")["items"], [])
            for path, digest in before.items():
                self.assertEqual(sha256(Path(path).read_bytes()).hexdigest(), digest)
            with self.assertRaises((ValueError, FileExistsError)):
                service.mutate("copy_task", {"task_id": source["id"], "name": "原生验证 含空格"})


if __name__ == "__main__":
    unittest.main()
