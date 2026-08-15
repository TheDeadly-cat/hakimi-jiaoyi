from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.implementation_manifest import (
    build_implementation_manifest,
    verify_implementation_manifest,
)


class ImplementationManifestTests(unittest.TestCase):
    def test_exact_verification_does_not_rebuild_the_import_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])

            with patch(
                "exchange_terminal.services.implementation_manifest._source_closure",
                side_effect=AssertionError("import graph must not be rebuilt during verification"),
            ):
                result = verify_implementation_manifest(manifest)

        self.assertEqual(result["status"], "PASS")

    def test_exact_verification_detects_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])
            source.write_text("VALUE = 2\n", encoding="utf-8")

            result = verify_implementation_manifest(manifest)

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(item.startswith("implementation_source_changed:") for item in result["blockers"]))

    def test_exact_verification_detects_runtime_manifest_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])
            tampered = deepcopy(manifest)
            tampered["runtime"]["python_version"] = "0.0.0"

            result = verify_implementation_manifest(tampered)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("implementation_manifest_fingerprint_invalid", result["blockers"])
        self.assertIn("implementation_runtime_changed", result["blockers"])

    def test_source_path_policy_blocks_before_reading_an_untrusted_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])
            source.unlink()

            result = verify_implementation_manifest(
                manifest,
                source_path_allowed=lambda _path: False,
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("implementation_source_path_not_allowed:0", result["blockers"])
        self.assertFalse(any(
            item.startswith("implementation_source_unavailable:")
            for item in result["blockers"]
        ))

    def test_malformed_runtime_manifest_fails_closed_without_throwing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])
            manifest["runtime"]["distributions"] = ["not-a-record"]
            manifest["fingerprint"] = "0" * 64

            result = verify_implementation_manifest(manifest)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "implementation_manifest_runtime_distributions_invalid",
            result["blockers"],
        )

    def test_entrypoint_verification_rebuilds_closure_and_blocks_resealed_omission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            helper = root / "helper.py"
            source = root / "engine.py"
            helper.write_text("VALUE = 1\n", encoding="utf-8")
            source.write_text("from helper import VALUE\n", encoding="utf-8")
            manifest = build_implementation_manifest([source])
            tampered = deepcopy(manifest)
            tampered["files"] = [
                row for row in tampered["files"] if Path(row["path"]).name != "helper.py"
            ]
            core = {
                "schema_version": tampered["schema_version"],
                "verification_policy": tampered["verification_policy"],
                "files": tampered["files"],
                "runtime": tampered["runtime"],
            }
            encoded = json.dumps(
                core,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            tampered["fingerprint"] = hashlib.sha256(encoded).hexdigest()

            result = verify_implementation_manifest(
                tampered,
                source_entrypoints=[source],
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("implementation_source_closure_changed", result["blockers"])


if __name__ == "__main__":
    unittest.main()
