"""An accepted local entry preserves records and refuses drift before startup."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_workbench_desktop as DESKTOP

SPEC = importlib.util.spec_from_file_location("bundle_fixture", Path(__file__).with_name("test_release_wheel_bundle.py"))
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


class WorkbenchDesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = FIXTURE.fixture(self.root)
        self.python = self.root / "虚构 test environment" / "python.exe"
        self.python.parent.mkdir()
        self.python.write_bytes(b"FAKE_PYTHON_FOR_MOCKED_INSTALLATION")
        self.electron = self.root / "Electron with spaces.exe"
        self.electron.write_bytes(b"FAKE_ELECTRON_NOT_EXECUTED")
        self.receipt["python"] = str(self.python)
        self.acceptance = self.root / "acceptance.json"
        self.acceptance.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.workspace = self.root / "原有 工作区"
        self.workspace.mkdir()
        (self.workspace / "old-record.json").write_bytes(b'"ORIGINAL_IMMUTABLE_RECORD"\n')
        self.output = self.root / "独立 candidate entry"
        source = self.receipt["installed_runtime"]["source_identity"]
        environment = self.receipt["installed_runtime"]["environment_verified"]
        self.actual = dict(version="0.2.1", source_status="BUILD_VERIFIED", source_sha256=source["content_sha256"],
                           build_receipt=source["build_receipt"], environment_status="VERIFIED",
                           lock_sha256=environment["lock_sha256"], python=str(self.python.resolve()),
                           package_directory=str(self.python.parent / "site-packages/hakimi_research"),
                           isolated_venv=True, package_inside_venv=True)
        self.probe = patch.object(DESKTOP, "_probe_installation", return_value=self.actual).start()
        self.addCleanup(patch.stopall)

    def prepare(self):
        return DESKTOP.prepare(self.acceptance, self.electron, self.workspace, self.output)

    def test_exact_artifacts_and_bound_entry_leave_existing_records_untouched(self):
        before = (self.workspace / "old-record.json").read_bytes()
        manifest = self.prepare()
        self.assertEqual(DESKTOP.verify(self.output), manifest)
        self.assertEqual((self.output / "accepted-wheel" / Path(self.receipt["wheel"]).name).read_bytes(),
                         Path(self.receipt["wheel"]).read_bytes())
        self.assertEqual((self.workspace / "old-record.json").read_bytes(), before)
        self.assertEqual(len(list(self.workspace.iterdir())), 1)
        cmd = (self.output / "Start-Workbench.cmd").read_text(encoding="utf-8")
        self.assertIn("DisableDelayedExpansion", cmd)
        self.assertIn('"%~dp0launch_workbench.py" --launch', cmd)
        self.assertNotIn(str(self.workspace), cmd)
        with self.assertRaisesRegex(ValueError, "已存在"):
            self.prepare()
        self.assertEqual(DESKTOP.verify(self.output), manifest)

    def test_package_dependency_or_build_drift_refuses_before_entry_creation(self):
        for key, value in [("version", "different"), ("source_sha256", "0" * 64),
                           ("environment_status", "MISMATCH"), ("build_receipt", {}),
                           ("isolated_venv", False), ("package_inside_venv", False)]:
            with self.subTest(key=key):
                actual = deepcopy(self.actual)
                actual[key] = value
                self.probe.return_value = actual
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_existing_acceptance_validator_rejects_incomplete_proof(self):
        self.receipt["test_execution"]["errors"] = 1
        self.acceptance.write_text(json.dumps(self.receipt), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_launch_checks_bytes_and_current_installation_before_running_electron(self):
        manifest = self.prepare()
        with patch.object(DESKTOP.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(DESKTOP.launch(self.output), 0)
            args, kwargs = run.call_args
            self.assertEqual(args[0], [str(self.electron.resolve()), str((self.output / "research-main.js").resolve())])
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["env"]["HAKIMI_RESEARCH_WORKSPACE"], str(self.workspace.resolve()))
            self.assertEqual(kwargs["env"]["HAKIMI_RESEARCH_DESKTOP_PROFILE"], manifest["profile"])
            run.reset_mock()
            self.probe.return_value = {**self.actual, "source_sha256": "f" * 64}
            with self.assertRaisesRegex(ValueError, "不匹配"):
                DESKTOP.launch(self.output)
            run.assert_not_called()
            self.probe.return_value = self.actual
            (self.output / "research-main.js").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "已变化"):
                DESKTOP.launch(self.output)
            run.assert_not_called()

    def test_electron_change_and_missing_wheel_are_rejected_without_startup(self):
        self.prepare()
        original = self.electron.read_bytes()
        self.electron.write_bytes(b"UPDATED_EXECUTABLE")
        with self.assertRaisesRegex(ValueError, "Electron"):
            DESKTOP.verify(self.output)
        self.electron.write_bytes(original)
        (self.output / "accepted-wheel" / Path(self.receipt["wheel"]).name).unlink()
        with self.assertRaisesRegex(ValueError, "缺失或已变化"):
            DESKTOP.verify(self.output)

    def test_cmd_quotes_percent_without_delayed_expansion_or_shell_data_paths(self):
        command = DESKTOP._cmd(Path("C:/space and 中文/100% test/python.exe"))
        self.assertIn("100%% test", command)
        self.assertNotIn("call ", command.lower())
        with self.assertRaisesRegex(ValueError, "换行或引号"):
            DESKTOP._cmd(Path('C:/bad"path/python.exe'))


if __name__ == "__main__":
    unittest.main()
