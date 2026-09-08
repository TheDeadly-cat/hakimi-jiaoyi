from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.environment import build_runtime_provenance, git_state, verify_dependency_environment
from hakimi_research.experiment_manifest import build_local_experiment_context
from hakimi_research.source_identity import package_content_identity
from hakimi_research.source_layout import DEFAULT_CONFIG_PATH, CANONICAL_DEPENDENCY_LOCK, default_artifact_root


class ProvenanceTests(unittest.TestCase):
    def test_git_status_failure_is_unknown_even_with_valid_commit(self):
        def run(arguments, **kwargs):
            return subprocess.CompletedProcess(arguments, 0, "a" * 40, "") if "rev-parse" in arguments else subprocess.CompletedProcess(arguments, 1, "", "failed")
        with patch("hakimi_research.environment.subprocess.run", side_effect=run):
            state = git_state(Path.cwd())
            self.assertEqual(state["status"], "UNKNOWN")
            self.assertEqual(state["commit"], "a" * 40)
            context = build_local_experiment_context(Path.cwd())
            self.assertIsNone(context["git_worktree_clean"])
            self.assertEqual(context["git_worktree_status"], "UNKNOWN")

    def test_git_timeout_is_unknown_and_successful_empty_status_is_clean(self):
        with patch("hakimi_research.environment.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 3)):
            self.assertEqual(git_state(Path.cwd())["status"], "UNKNOWN")
        def clean(arguments, **kwargs):
            return subprocess.CompletedProcess(arguments, 0, "a" * 40 if "rev-parse" in arguments else "", "")
        with patch("hakimi_research.environment.subprocess.run", side_effect=clean):
            self.assertEqual(git_state(Path.cwd())["status"], "CLEAN")

    def test_pinned_lock_and_actual_installed_versions_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "requirements.lock"
            lock.write_text("sample==1.0\nother==2.0\n", encoding="utf-8")
            def installed(name):
                if name == "other":
                    raise metadata.PackageNotFoundError(name)
                return "9.0"
            with patch("hakimi_research.environment.metadata.version", side_effect=installed):
                evidence = verify_dependency_environment(lock)
            self.assertTrue(evidence["lock_fully_pinned"])
            self.assertEqual(evidence["lock_sha256"], hashlib.sha256(lock.read_bytes()).hexdigest())
            self.assertEqual(evidence["status"], "MISMATCH")
            self.assertEqual(evidence["mismatched"], ["sample"])
            self.assertEqual(evidence["missing"], ["other"])
            with patch("hakimi_research.environment.metadata.version", side_effect=lambda name: {"sample": "1.0", "other": "2.0"}[name]):
                self.assertEqual(verify_dependency_environment(lock)["status"], "VERIFIED")

    def test_unreadable_or_nonexact_lock_never_verifies(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "requirements.lock"
            self.assertEqual(verify_dependency_environment(lock)["status"], "UNKNOWN")
            for content in ("sample>=1.0", "-r other.lock\nsample==1.0", "sample==1.0\nsample==1.0"):
                lock.write_text(content, encoding="utf-8")
                self.assertEqual(verify_dependency_environment(lock)["status"], "INVALID_LOCK")

    def test_distribution_with_missing_version_metadata_is_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "requirements.lock"
            lock.write_text("sample==1.0\n", encoding="utf-8")
            for installed in (None, ""):
                with patch("hakimi_research.environment.metadata.version", return_value=installed):
                    self.assertEqual(verify_dependency_environment(lock)["status"], "UNKNOWN")

    def test_source_content_tracks_dirty_bytes_and_is_portable(self):
        with tempfile.TemporaryDirectory() as folder:
            left, right = Path(folder) / "left", Path(folder) / "right"
            left.mkdir(); right.mkdir()
            for directory in (left, right):
                (directory / "core.py").write_bytes(b"value = 1\n")
            self.assertEqual(package_content_identity(left), package_content_identity(right))
            before = package_content_identity(left)
            (left / "core.py").write_bytes(b"value = 2\n")
            self.assertNotEqual(before["content_sha256"], package_content_identity(left)["content_sha256"])

    def test_build_receipt_is_checked_against_actual_installed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "core.py").write_text("x = 1\n", encoding="utf-8")
            receipt = {"schema_version": "research-build-source-v1", **package_content_identity(package)}
            (package / "_build_identity.json").write_text(json.dumps(receipt), encoding="utf-8")
            before = build_runtime_provenance(package_root=package)
            self.assertEqual(before["source_identity"]["status"], "BUILD_VERIFIED")
            self.assertEqual(before["replay_verified"]["status"], "NOT_RUN")
            (package / "core.py").write_text("x = 2\n", encoding="utf-8")
            self.assertEqual(build_runtime_provenance(package_root=package)["source_identity"]["status"], "BUILD_MISMATCH")

    def test_missing_wheel_build_receipt_has_its_own_failure_status(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "core.py").write_text("x = 1\n", encoding="utf-8")
            with patch("hakimi_research.environment.REPOSITORY_ROOT", None):
                source = build_runtime_provenance(package_root=package)["source_identity"]
            self.assertEqual(source["status"], "BUILD_MISSING")
            self.assertEqual(len(source["content_sha256"]), 64)
            self.assertEqual(source["error"], "build_receipt_missing_for_installed_package")

    def test_packaged_resources_and_artifact_path_are_independent(self):
        self.assertTrue(DEFAULT_CONFIG_PATH.is_file())
        self.assertTrue(CANONICAL_DEPENDENCY_LOCK.is_file())
        with tempfile.TemporaryDirectory() as folder, patch.dict("os.environ", {"HAKIMI_RESEARCH_HOME": str(Path(folder) / "data")}):
            artifact_path = default_artifact_root()
            self.assertEqual(artifact_path, (Path(folder) / "data").resolve())
            self.assertFalse(artifact_path.exists())


if __name__ == "__main__":
    unittest.main()
