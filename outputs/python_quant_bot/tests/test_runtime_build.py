from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from exchange_terminal.services.runtime_build import (
    RUNTIME_BUILD_SCHEMA_VERSION,
    RuntimeBuildGuard,
    build_runtime_source_manifest,
)


class RuntimeBuildTests(unittest.TestCase):
    def test_manifest_is_stable_and_only_includes_python_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "exchange_terminal"
            source.mkdir()
            (source / "b.py").write_text("B = 2\n", encoding="utf-8")
            (source / "a.py").write_text("A = 1\n", encoding="utf-8")
            (source / "ignored.txt").write_text("ignored\n", encoding="utf-8")

            first = build_runtime_source_manifest(project, [source])
            second = build_runtime_source_manifest(project, [source])

            self.assertEqual(first["status"], "PASS")
            self.assertEqual(first["schema_version"], RUNTIME_BUILD_SCHEMA_VERSION)
            self.assertEqual(first["fingerprint"], second["fingerprint"])
            self.assertEqual([row["path"] for row in first["files"]], [
                "exchange_terminal/a.py",
                "exchange_terminal/b.py",
            ])

    def test_guard_requires_restart_after_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "exchange_terminal"
            source.mkdir()
            target = source / "server.py"
            target.write_text("VERSION = 1\n", encoding="utf-8")
            guard = RuntimeBuildGuard(
                project_root=project,
                source_roots=[source],
                cache_ttl_ms=0,
                now_ms=lambda: 1_000,
            )

            initial = guard.snapshot(force=True)
            target.write_text("VERSION = 2\n", encoding="utf-8")
            changed = guard.snapshot(force=True)

            self.assertEqual(initial["status"], "PASS")
            self.assertFalse(initial["restart_required"])
            self.assertEqual(changed["status"], "RESTART_REQUIRED")
            self.assertTrue(changed["source_changed_after_start"])
            self.assertIn("runtime_source_tree_changed_after_start", changed["blockers"])
            self.assertFalse(changed["paper_authorized"])
            self.assertFalse(changed["live_order_allowed"])

    def test_guard_detects_added_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "exchange_terminal"
            source.mkdir()
            (source / "server.py").write_text("VERSION = 1\n", encoding="utf-8")
            guard = RuntimeBuildGuard(
                project_root=project,
                source_roots=[source],
                cache_ttl_ms=0,
                now_ms=lambda: 1_000,
            )

            (source / "new_service.py").write_text("READY = True\n", encoding="utf-8")
            changed = guard.snapshot(force=True)

            self.assertEqual(changed["loaded_source_count"], 1)
            self.assertEqual(changed["disk_source_count"], 2)
            self.assertTrue(changed["restart_required"])


if __name__ == "__main__":
    unittest.main()
