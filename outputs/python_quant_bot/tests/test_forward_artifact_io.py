from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.forward_artifact_io import (
    read_forward_json_artifact,
    windows_safe_artifact_basename,
)


class ForwardArtifactIoTests(unittest.TestCase):
    def test_valid_object_preserves_exact_bounded_bytes(self) -> None:
        raw = b'{"status":"PASS","nested":{"value":1}}\n'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.json"
            path.write_bytes(raw)

            result = read_forward_json_artifact(path, byte_limit=len(raw))

        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.raw, raw)
        self.assertEqual(result.payload["nested"], {"value": 1})
        self.assertEqual(result.blocker, "")

    def test_duplicate_nonfinite_deep_and_non_object_json_are_blocked(self) -> None:
        deeply_nested = (b'{"nested":' * 140) + b"0" + (b"}" * 140)
        cases = {
            "duplicate": (b'{"status":"PASS","status":"BLOCK"}', "strict_json_duplicate_object_key"),
            "nan": (b'{"value":NaN}', "strict_json_non_finite_number"),
            "infinity": (b'{"value":1e999}', "strict_json_non_finite_number"),
            "deep": (deeply_nested, "strict_json_nesting_limit_exceeded"),
            "root": (b"[]", "strict_json_object_required"),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, (raw, blocker) in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_bytes(raw)
                    result = read_forward_json_artifact(path, byte_limit=len(raw))
                    self.assertEqual(result.status, "BLOCK")
                    self.assertEqual(result.blocker, blocker)
                    self.assertEqual(result.raw, raw)

    def test_oversize_missing_and_link_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            oversized = root / "oversized.json"
            oversized.write_bytes(b'{"value":1}')
            oversize_result = read_forward_json_artifact(
                oversized,
                byte_limit=2,
                size_limit_blocker="test_size_limit_exceeded",
            )
            missing_result = read_forward_json_artifact(
                root / "missing.json",
                byte_limit=32,
            )

            self.assertEqual(oversize_result.status, "BLOCK")
            self.assertEqual(oversize_result.blocker, "test_size_limit_exceeded")
            self.assertEqual(missing_result.status, "MISSING")
            self.assertEqual(missing_result.blocker, "artifact_bundle_member_unavailable")

            target = root / "target.json"
            target.write_bytes(b"{}")
            link = root / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                return
            link_result = read_forward_json_artifact(link, byte_limit=32)
            self.assertEqual(link_result.status, "BLOCK")
            self.assertEqual(
                link_result.blocker,
                "artifact_bundle_member_link_or_reparse_forbidden",
            )

    def test_windows_basename_contract_rejects_aliases_and_unsafe_names(self) -> None:
        self.assertEqual(
            windows_safe_artifact_basename("portfolio_research.json"),
            "portfolio_research.json",
        )
        for value in (
            "CON.json",
            "portfolio_research.json:stream",
            "portfolio_research.json.",
            "portfolio_research.json ",
            "portfolio/research.json",
            "portfolio\\research.json",
            "portfolio＿research.json",
            "",
            None,
        ):
            with self.subTest(value=value):
                self.assertIsNone(windows_safe_artifact_basename(value))

    def test_memory_failure_is_contained_without_path_disclosure(self) -> None:
        private_path = Path("C:/private/forward-status.json")
        with patch(
            "exchange_terminal.services.forward_artifact_io.read_bounded_artifact",
            side_effect=MemoryError(str(private_path)),
        ):
            result = read_forward_json_artifact(private_path, byte_limit=32)

        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.blocker, "portfolio_forward_artifact_memory_exhausted")
        self.assertNotIn(str(private_path), result.blocker)


if __name__ == "__main__":
    unittest.main()
