from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.validation_receipts import (
    build_controlled_input_manifest,
    build_validation_action,
    canonical_hash,
    create_validation_receipt,
    result_from_process,
    verify_validation_receipt,
)


class ValidationReceiptTests(unittest.TestCase):
    def fixture_project(self, root: Path) -> Path:
        project = root / "outputs" / "python_quant_bot"
        (project / "exchange_terminal" / "static").mkdir(parents=True)
        (project / "tests").mkdir()
        (root / "outputs" / "hakimi_trade_electron").mkdir()
        (project / "run_lean_validation.py").write_text("print('lean')\n", encoding="utf-8")
        (project / "requirements.txt").write_text("example==1\n", encoding="utf-8")
        (project / "exchange_terminal" / "server.py").write_text("VALUE = 1\n", encoding="utf-8")
        (project / "exchange_terminal" / "static" / "app.js").write_text("void 0;\n", encoding="utf-8")
        (project / "tests" / "test_example.py").write_text("def test_value(): pass\n", encoding="utf-8")
        (root / "outputs" / "hakimi_trade_electron" / "package-lock.json").write_text("{}\n", encoding="utf-8")
        return project

    def action(self, project: Path, *, manifest: dict[str, object] | None = None, contract: str = "exit-zero") -> dict[str, object]:
        toolchain: dict[str, object] = {"python": {"version": "test"}}
        toolchain["sha256"] = canonical_hash(toolchain)
        return build_validation_action(
            check_id="example-check",
            argv=["python", "-m", "unittest" if contract == "unittest" else "py_compile"],
            cwd=project,
            manifest=manifest or build_controlled_input_manifest(project),
            toolchain=toolchain,
            result_contract=contract,
            minimum_tests=1 if contract == "unittest" else 0,
        )

    def test_exact_action_receipt_verifies_and_tampering_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.fixture_project(Path(directory))
            action = self.action(project)
            result = result_from_process(
                action=action,
                exit_code=0,
                stdout="ok\n",
                stderr="",
                duration_sec=0.1,
            )
            receipt = create_validation_receipt(
                action=action,
                result=result,
                started_at="2026-08-10T00:00:00+00:00",
                finished_at="2026-08-10T00:00:01+00:00",
            )
            self.assertEqual(verify_validation_receipt(receipt, expected_action=action)["status"], "PASS")

            tampered = deepcopy(receipt)
            tampered["predicate"]["action"]["argv"] = ["echo", "ok"]
            blocked = verify_validation_receipt(tampered, expected_action=action)

        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("validation_action_digest_invalid", blocked["blockers"])

    def test_source_change_invalidates_the_expected_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.fixture_project(Path(directory))
            action = self.action(project)
            result = result_from_process(action=action, exit_code=0, stdout="ok", stderr="", duration_sec=0.1)
            receipt = create_validation_receipt(
                action=action,
                result=result,
                started_at="2026-08-10T00:00:00+00:00",
                finished_at="2026-08-10T00:00:01+00:00",
            )
            (project / "exchange_terminal" / "server.py").write_text("VALUE = 2\n", encoding="utf-8")
            changed_action = self.action(project)

            blocked = verify_validation_receipt(receipt, expected_action=changed_action)

        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("validation_action_current_context_mismatch", blocked["blockers"])

    def test_manifest_never_touches_protected_local_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.fixture_project(Path(directory))
            electron = project.parent / "hakimi_trade_electron"
            protected = {
                electron / "config.local.json",
                electron / "runtime-private.json",
            }
            for path in protected:
                path.write_text("PROTECTED_SENTINEL", encoding="utf-8")
            original_open = Path.open
            original_stat = Path.stat

            def guarded_open(path: Path, *args: object, **kwargs: object):
                if path in protected:
                    raise AssertionError(f"protected file opened: {path.name}")
                return original_open(path, *args, **kwargs)

            def guarded_stat(path: Path, *args: object, **kwargs: object):
                if path in protected:
                    raise AssertionError(f"protected file inspected: {path.name}")
                return original_stat(path, *args, **kwargs)

            with patch.object(Path, "open", guarded_open), patch.object(Path, "stat", guarded_stat):
                manifest = build_controlled_input_manifest(project)

        listed = {row["path"] for row in manifest["files"]}
        self.assertFalse(any("config.local.json" in path for path in listed))
        self.assertFalse(any("runtime-private.json" in path for path in listed))

    def test_unittest_receipt_requires_a_real_nonzero_test_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.fixture_project(Path(directory))
            action = self.action(project, contract="unittest")
            result = result_from_process(action=action, exit_code=0, stdout="OK\n", stderr="", duration_sec=0.1)
            receipt = create_validation_receipt(
                action=action,
                result=result,
                started_at="2026-08-10T00:00:00+00:00",
                finished_at="2026-08-10T00:00:01+00:00",
            )

            blocked = verify_validation_receipt(receipt, expected_action=action)

        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("validation_unittest_result_invalid", blocked["blockers"])
        self.assertFalse(receipt["predicate"]["result"]["safety"]["paper_authorized"])
        self.assertFalse(receipt["predicate"]["result"]["safety"]["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
