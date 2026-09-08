"""Synthetic paging and independently timed import preserve canonical identities."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from hakimi_research.dataset_registry import load_snapshot
from hakimi_research.documents import read_document

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PipelineInputTests(unittest.TestCase):
    def test_page_boundary_reimport_preserves_synthetic_label_and_fixed_context(self):
        builder, importer = load("build_profile_fixture"), load("profile_capture_import")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = builder.build(301, root / "inputs")
            capture = read_document(inputs["capture"])
            self.assertEqual(len(capture["pages"]), 2)
            snapshot = load_snapshot(inputs["snapshot"])
            self.assertEqual(snapshot.document["quality"]["accepted_rows"], 301)
            self.assertEqual(snapshot.document["quality"]["missing_rows"], 0)
            self.assertEqual(snapshot.document["evidence_kind"], "SYNTHETIC_TEST")
            spec = read_document(inputs["spec"])
            self.assertEqual(spec["purpose"], "SYNTHETIC_REGRESSION")
            self.assertEqual(spec["score_start"], "2024-01-04T00:00:00Z")
            before = Path(inputs["capture"]).read_bytes()
            result = importer.profile(Path(inputs["capture"]), Path(inputs["snapshot"]), root / "import-profile")
            receipt = read_document(result["profile"])
            self.assertTrue(receipt["snapshot_matches_original"])
            self.assertTrue(receipt["original_capture_unchanged"])
            self.assertEqual(receipt["snapshot_id"], snapshot.snapshot_id)
            self.assertEqual(before, Path(inputs["capture"]).read_bytes())
            self.assertNotIn(str(root), Path(result["profile"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
