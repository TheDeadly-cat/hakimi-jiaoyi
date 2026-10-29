"""Installed original-terminal packaging boundaries; no service is started."""
import json
import os
import shutil
import tempfile
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

    def staged_components(self):
        temporary = tempfile.TemporaryDirectory(prefix="terminal-build-identities-")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        for destination, source in terminal.source_files(ROOT).items():
            if destination.startswith(("components/canonical/", "components/terminal/vendor/research/")):
                target = output / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        return output

    def test_installed_receipts_hash_actual_components_and_keep_frozen_origin_separate(self):
        output = self.staged_components()
        canonical_package = output / "components/canonical/hakimi_research"
        frozen_package = output / "components/terminal/vendor/research/hakimi_terminal_research"
        identities = {name: terminal.package_identity(package) for name, package in
                      (("canonical", canonical_package), ("frozen", frozen_package))}
        raw_vendor = ROOT / "outputs/python_quant_bot/vendor/research/hakimi_terminal_research"
        self.assertFalse((raw_vendor / "_build_identity.json").exists())
        git = dict(commit="a" * 40, status="DIRTY")
        generated = terminal.generate_build_identities(output, ROOT, dict(git=git))
        for name, package in (("canonical", canonical_package), ("frozen", frozen_package)):
            receipt = json.loads((package / "_build_identity.json").read_bytes())
            self.assertEqual(receipt["content_sha256"], identities[name]["content_sha256"])
            self.assertEqual(receipt["file_hashes"], identities[name]["file_hashes"])
            self.assertEqual(terminal.package_identity(package), identities[name])
            self.assertEqual(generated[name]["sha256"], terminal.sha((package / "_build_identity.json").read_bytes()))
            self.assertEqual(receipt["wrapper_build_commit"], git["commit"])
            self.assertEqual(receipt["wrapper_build_git_status"], "DIRTY")
            self.assertNotIn("status", receipt)
            self.assertEqual(receipt["build_definition_sha256"]["setup.py"], terminal.sha((ROOT / "setup.py").read_bytes()))
        frozen = json.loads((frozen_package / "_build_identity.json").read_bytes())
        self.assertEqual(frozen["git"], {"commit": "", "status": "UNKNOWN"})
        self.assertNotEqual(frozen["frozen_source_origin"]["source_commit"], git["commit"])
        self.assertEqual(json.loads((canonical_package / "_build_identity.json").read_bytes())["git"], git)
        self.assertFalse((raw_vendor / "_build_identity.json").exists())

    def test_changed_frozen_bytes_cannot_receive_an_accepted_build_receipt(self):
        output = self.staged_components()
        package = output / "components/terminal/vendor/research/hakimi_terminal_research"
        with (package / "config.py").open("ab") as handle:
            handle.write(b"\n# altered fixture\n")
        with self.assertRaisesRegex(ValueError, "frozen_accepted_identity_changed"):
            terminal.generate_build_identities(output, ROOT, dict(git=dict(commit="b" * 40, status="CLEAN")))
        self.assertFalse((package / "_build_identity.json").exists())
        self.assertFalse((output / "components/canonical/hakimi_research/_build_identity.json").exists())

    def test_execution_probe_is_private_temporary_and_incomplete_success_is_rejected(self):
        observed = {}
        def run(arguments, **options):
            observed["temporary"] = Path(options["cwd"])
            self.assertTrue(observed["temporary"].is_dir())
            self.assertEqual(arguments[1:6], ["-I", "-S", "-B", "-X", "utf8"])
            self.assertEqual(arguments[6:8], ["-c", terminal.EXECUTION_PROBE])
            for key in ("HAKIMI_RUNTIME_DIR", "HAKIMI_QUANT_WORKSPACE_DIR", "FUTU_PY_APPDATA", "HAKIMI_RESEARCH_HOME"):
                self.assertTrue(Path(options["env"][key]).is_relative_to(observed["temporary"]))
            self.assertNotIn("PYTHONPATH", options["env"])
            self.assertNotIn("CHROME_CRASHPAD_PIPE_NAME", options["env"])
            return SimpleNamespace(returncode=0, stdout='{"status":"VERIFIED_NEW_SYNTHETIC_RUN","synthetic_runs":1,"evidence_kind":"SYNTHETIC_TEST"}', stderr="")
        with patch.dict(os.environ, HAKIMI_RUNTIME_DIR="HOSTILE_OLD", HAKIMI_QUANT_WORKSPACE_DIR="HOSTILE_QUANT", PYTHONPATH="HOSTILE", CHROME_CRASHPAD_PIPE_NAME="foreign"):
            with patch.object(terminal.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(ValueError, "execution_proof_invalid"):
                    terminal.probe_installed_execution(ROOT)
        self.assertFalse(observed["temporary"].exists())

    def test_execution_probe_failure_is_not_downgraded_to_import_success(self):
        with patch.object(terminal.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="runtime_source_or_dependencies_unverified")):
            with self.assertRaisesRegex(ValueError, "private_execution_probe_failed.*runtime_source_or_dependencies_unverified"):
                terminal.probe_installed_execution(ROOT)

    def test_changed_installed_identity_algorithm_is_rejected_before_execution(self):
        output = self.staged_components()
        package = output / "components/terminal/vendor/research/hakimi_terminal_research"
        (package / "source_identity.py").write_text("raise AssertionError('altered staged code must never run')\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source_identity_algorithm_changed"):
            terminal.generate_build_identities(output, ROOT, dict(git=dict(commit="c" * 40, status="CLEAN")))
        self.assertFalse((package / "_build_identity.json").exists())


if __name__ == "__main__":
    unittest.main()
