from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.reporting import save_json_report


class ReportPersistenceTests(unittest.TestCase):
    def test_idempotent_same_content_and_reject_different_content(self):
        with tempfile.TemporaryDirectory() as folder:
            first = save_json_report({"value": 1}, folder, "report", artifact_id="fixed")
            before = Path(first).read_bytes()
            self.assertEqual(save_json_report({"value": 1}, folder, "report", artifact_id="fixed"), first)
            with self.assertRaises(FileExistsError):
                save_json_report({"value": 2}, folder, "report", artifact_id="fixed")
            self.assertEqual(Path(first).read_bytes(), before)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_concurrent_identical_writers_and_different_writers(self):
        with tempfile.TemporaryDirectory() as folder:
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: save_json_report({"value": 1}, folder, "same", artifact_id="fixed"), range(16)))
            self.assertEqual(len(set(results)), 1)
            def save(value):
                try:
                    save_json_report({"value": value}, folder, "different", artifact_id="fixed")
                    return value
                except FileExistsError:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                successes = [value for value in pool.map(save, range(16)) if value is not None]
            self.assertEqual(len(successes), 1)
            self.assertEqual(json.loads((Path(folder) / "different_fixed.json").read_text())["value"], successes[0])

    def test_disk_failure_before_publish_leaves_no_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("hakimi_research.reporting.os.fsync", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_json_report({"value": 1}, folder, "report", artifact_id="fixed")
            self.assertEqual(list(Path(folder).iterdir()), [])
            save_json_report({"value": 1}, folder, "report", artifact_id="fixed")

    def test_partial_write_failure_remains_temporary_and_is_cleaned(self):
        original_fdopen = os.fdopen
        class FullDiskStream:
            def __init__(self, descriptor):
                self.stream = original_fdopen(descriptor, "wb")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def write(self, data):
                self.stream.write(data[:5])
                self.stream.flush()
                raise OSError("disk full after partial staging write")
        with tempfile.TemporaryDirectory() as folder:
            with patch("hakimi_research.reporting.os.fdopen", side_effect=lambda descriptor, mode: FullDiskStream(descriptor)):
                with self.assertRaises(OSError):
                    save_json_report({"value": "long enough to be incomplete"}, folder, "report", artifact_id="fixed")
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_publish_failure_does_not_create_or_replace_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("hakimi_research.reporting.os.link", side_effect=OSError("unsupported filesystem")):
                with self.assertRaises(OSError):
                    save_json_report({"value": 1}, folder, "report", artifact_id="fixed")
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_process_interrupt_before_publish_leaves_only_ignored_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            code = "import os,sys; from hakimi_research import reporting; reporting.os.link=lambda *a,**k:os._exit(73); reporting.save_json_report({'value':1},sys.argv[1],'report',artifact_id='fixed')"
            crashed = subprocess.run([sys.executable, "-c", code, folder], capture_output=True, text=True)
            self.assertEqual(crashed.returncode, 73, crashed.stderr)
            self.assertEqual(list(Path(folder).glob("*.json")), [])
            self.assertTrue(list(Path(folder).glob(".*.staging-*.tmp")))
            final = Path(save_json_report({"value": 1}, folder, "report", artifact_id="fixed"))
            self.assertEqual(json.loads(final.read_text()), {"value": 1})

    def test_invalid_json_and_path_components_have_no_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "missing"
            for payload, prefix, artifact in (({"x": float("nan")}, "report", "ok"), ({}, "../bad", "ok"), ({}, "report", "../bad")):
                with self.assertRaises(ValueError):
                    save_json_report(payload, destination, prefix, artifact_id=artifact)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
