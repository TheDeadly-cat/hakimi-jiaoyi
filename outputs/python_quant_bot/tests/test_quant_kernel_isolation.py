"""The frozen terminal kernel coexists with the current canonical safety package."""
from hashlib import sha256
import importlib
from importlib.resources import files
import json
from pathlib import Path
import sys
import unittest

from exchange_terminal.services import quant_workspace as quant


class QuantKernelIsolationTests(unittest.TestCase):
    def test_static_namespace_is_the_only_change_to_pinned_sources(self):
        origin = json.loads((quant._VENDOR / "ORIGIN.json").read_bytes())
        root = quant._verified_package_root(quant._VENDOR)
        names = json.loads((root / "runtime-files.json").read_bytes())["files"]
        self.assertEqual(set(names), set(origin["original_file_sha256"]))
        self.assertEqual(set(names), set(origin["derived_file_sha256"]))
        self.assertEqual(len(names), 84)
        for name in names:
            raw = (root / name).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(), origin["derived_file_sha256"][name], name)
            original = raw.replace(b"hakimi_terminal_research", b"hakimi_research") if name.endswith(".py") else raw
            self.assertEqual(sha256(original).hexdigest(), origin["original_file_sha256"][name], name)
        digest = lambda value: sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest(origin["original_file_sha256"]), origin["source_content_sha256"])
        self.assertEqual(digest(origin["derived_file_sha256"]), quant.ACCEPTED_SOURCE_SHA256)

    def test_loading_terminal_preserves_canonical_modules_and_search_paths(self):
        canonical = importlib.import_module("hakimi_research.http_contract")
        package = importlib.import_module("hakimi_research")
        before_path = list(sys.path)
        before_module = canonical.__file__
        kernel = quant._load_kernel()
        self.assertEqual(sys.path, before_path)
        self.assertIs(importlib.import_module("hakimi_research.http_contract"), canonical)
        self.assertEqual(canonical.__file__, before_module)
        self.assertTrue(Path(package.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src"))
        self.assertEqual(kernel.service.__module__, "hakimi_terminal_research.desktop_service")
        self.assertTrue(files("hakimi_terminal_research").joinpath("resources/desktop.html").is_file())


if __name__ == "__main__":
    unittest.main()
