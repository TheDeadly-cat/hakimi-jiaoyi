import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from hakimi_research.source_identity import package_content_identity
from hakimi_research.source_layout import PACKAGE_ROOT, REPOSITORY_ROOT


class RuntimePackageBoundaryTests(unittest.TestCase):
    def test_formal_runtime_manifest_excludes_repository_only_tools(self):
        identity = package_content_identity(PACKAGE_ROOT)
        self.assertIn("runtime-files.json", identity["file_hashes"])
        self.assertIn("experiment.py", identity["file_hashes"])
        self.assertIn("reporting_legacy_v2.py", identity["file_hashes"])
        self.assertNotIn("terminal_config.py", identity["file_hashes"])
        self.assertFalse(any(name.startswith("deterministic_") for name in identity["file_hashes"]))
        if REPOSITORY_ROOT is None:
            self.assertIsNone(importlib.util.find_spec("hakimi_research.terminal_config"))
            self.assertIsNone(importlib.util.find_spec("hakimi_research.deterministic_strategy_family_benchmark"))

    def test_missing_declared_and_unexpected_installed_sources_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {"schema_version": "research-runtime-files-v1", "files": ["core.py", "runtime-files.json"]}
            (root / "runtime-files.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing"):
                package_content_identity(root)
            (root / "core.py").write_text("value = 1\n", encoding="utf-8")
            before = package_content_identity(root)
            (root / "unexpected.py").write_text("value = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected"):
                package_content_identity(root)
            (root / "unexpected.py").unlink()
            self.assertEqual(package_content_identity(root), before)

    def test_source_checkout_ignores_only_explicitly_unshipped_developer_files(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            root = checkout / "src" / "hakimi_research"
            root.mkdir(parents=True)
            (root / "core.py").write_text("value = 1\n", encoding="utf-8")
            (root / "runtime-files.json").write_text(json.dumps({
                "schema_version": "research-runtime-files-v1",
                "files": ["core.py", "runtime-files.json"],
            }), encoding="utf-8")
            original = package_content_identity(root)
            (root / "developer_only.py").write_text("needs_checkout = True\n", encoding="utf-8")
            self.assertEqual(package_content_identity(root), original)
            (root / "core.py").write_text("value = 2\n", encoding="utf-8")
            self.assertNotEqual(package_content_identity(root), original)
