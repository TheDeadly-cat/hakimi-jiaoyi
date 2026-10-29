"""Installed original-terminal packaging boundaries; no service is started."""
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import build_windows_terminal as terminal
import terminal_package_bootstrap as bootstrap


class TerminalPackagingTests(unittest.TestCase):
    def test_component_closure_preserves_formal_manifest_and_frozen_identity(self):
        files = terminal.source_files(ROOT)
        self.assertIn("components/terminal/exchange_terminal/server.py", files)
        self.assertIn("components/terminal/exchange_terminal/static/terminal-quant-ui.js", files)
        self.assertIn("components/terminal-canonical/hakimi_research/terminal_config.py", files)
        self.assertNotIn("components/canonical/hakimi_research/terminal_config.py", files)
        self.assertEqual(files["components/canonical/hakimi_research/runtime-files.json"], ROOT / "src/hakimi_research/runtime-files.json")
        frozen = ROOT / "outputs/python_quant_bot/vendor/research/hakimi_terminal_research"
        manifest = json.loads((frozen / "runtime-files.json").read_bytes())
        for name in manifest["files"]:
            self.assertEqual(files["components/terminal/vendor/research/hakimi_terminal_research/" + name], frozen / name)
        self.assertFalse(any("config.local" in name or "/runtime/" in name or "/src/" in name for name in files))
        self.assertNotIn("resources/app/trial-main.js", files)
        self.assertNotIn("resources/app/research-main.js", files)

    def test_final_build_rejects_dirty_sources_before_output(self):
        with patch.object(terminal.subprocess, "check_output", side_effect=[b"a" * 40 + b"\n", b" M main.js\n"]):
            with self.assertRaisesRegex(ValueError, "clean_committed_source"):
                terminal.source_provenance(ROOT, {}, False)

    def test_dirty_probe_never_claims_clean_provenance(self):
        with patch.object(terminal.subprocess, "check_output", side_effect=[b"a" * 40 + b"\n", b" M main.js\n"]):
            result = terminal.source_provenance(ROOT, {}, True)
        self.assertEqual(result["git"]["status"], "DIRTY")
        self.assertTrue(result["development_probe"])
        self.assertIn("tools/terminal_package_bootstrap.py", result["files_sha256"])

    def test_archive_rejects_reparse_input(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "original.txt"
            source.write_bytes(b"test")
            alias = root / "alias.txt"
            try:
                alias.symlink_to(source)
            except OSError:
                self.skipTest("host cannot create file symlinks")
            with self.assertRaisesRegex(ValueError, "reparse_source"):
                terminal.regular(alias)

    def test_builder_probe_overrides_both_inherited_workspace_paths(self):
        observed = {}
        def run(args, **kwargs):
            env = kwargs["env"]
            observed["temporary"] = Path(env["HAKIMI_RUNTIME_DIR"])
            self.assertTrue(observed["temporary"].is_dir())
            self.assertEqual(env["HAKIMI_QUANT_WORKSPACE_DIR"], env["HAKIMI_RUNTIME_DIR"])
            self.assertEqual(kwargs["cwd"], env["HAKIMI_RUNTIME_DIR"])
            self.assertEqual(env["HAKIMI_QUANT_READ_ONLY"], "1")
            self.assertNotEqual(env["HAKIMI_RUNTIME_DIR"], "HOSTILE_OLD_DATA")
            self.assertNotIn("PYTHONPATH", env)
            return SimpleNamespace(returncode=0, stdout='{"status":"VERIFIED"}', stderr="")
        with patch.dict(os.environ, HAKIMI_RUNTIME_DIR="HOSTILE_OLD_DATA", HAKIMI_QUANT_WORKSPACE_DIR="HOSTILE_QUANT_DATA", PYTHONPATH="HOSTILE_MODULES"):
            with patch.object(terminal.subprocess, "run", side_effect=run):
                self.assertEqual(terminal.probe_installation(ROOT)["status"], "VERIFIED")
        self.assertFalse(observed["temporary"].exists())

    def test_direct_bootstrap_probe_owns_temporary_roots_and_cleans_up(self):
        observed = {}
        def initialize(*unused):
            observed["temporary"] = Path(os.environ["HAKIMI_RUNTIME_DIR"])
            self.assertTrue(observed["temporary"].is_dir())
            self.assertEqual(os.environ["HAKIMI_QUANT_WORKSPACE_DIR"], str(observed["temporary"]))
            self.assertEqual(os.environ["FUTU_PY_APPDATA"], str(observed["temporary"] / "futu-sdk"))
            self.assertNotEqual(str(observed["temporary"]), "HOSTILE_OLD_DATA")
        with patch.dict(os.environ, HAKIMI_RUNTIME_DIR="HOSTILE_OLD_DATA", HAKIMI_QUANT_WORKSPACE_DIR="HOSTILE_QUANT_DATA", FUTU_PY_APPDATA="HOSTILE_SDK_DATA"):
            with patch.object(bootstrap, "initialize", side_effect=initialize), patch.object(bootstrap, "probe", return_value={"status": "VERIFIED"}), patch.object(bootstrap.logging, "shutdown") as shutdown:
                result = bootstrap.run_probe(ROOT, {})
                self.assertTrue(result["probe_workspace_temporary"])
                shutdown.assert_called_once()
        self.assertFalse(observed["temporary"].exists())


if __name__ == "__main__":
    unittest.main()
