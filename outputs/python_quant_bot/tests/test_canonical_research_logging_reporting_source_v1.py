from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, mock_open, patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research import logging_setup as canonical_logging  # noqa: E402
from hakimi_research import reporting as canonical_reporting  # noqa: E402
from quant_bot import logging_setup as legacy_logging  # noqa: E402
from quant_bot import reporting as legacy_reporting  # noqa: E402


ARCHIVE_LOGGING_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0535_logging_setup.py"
ARCHIVE_REPORTING_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0535_reporting.py"
LEGACY_LOGGING_PATH = OUTPUT_ROOT / "quant_bot" / "logging_setup.py"
LEGACY_REPORTING_PATH = OUTPUT_ROOT / "quant_bot" / "reporting.py"
CLI_PATH = SRC_ROOT / "hakimi_research" / "cli.py"
MANIFEST_TEST_PATH = OUTPUT_ROOT / "tests" / "test_reproducible_experiment_manifest_v1.py"
VALID_ARTIFACT_ID = "hexp-" + ("a" * 20)


class StringAlias(str):
    pass


class DictAlias(dict):
    pass


class ListAlias(list):
    pass


class IntAlias(int):
    pass


class CanonicalResearchLoggingReportingSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identities_are_canonical(self) -> None:
        self.assertEqual(canonical_logging.RESEARCH_LOGGING_SCHEMA_VERSION, "research-logging-v1")
        self.assertEqual(canonical_reporting.RESEARCH_JSON_REPORT_SCHEMA_VERSION, "research-json-report-v1")
        self.assertIs(legacy_logging.setup_logging, canonical_logging.setup_logging)
        self.assertIs(legacy_reporting.save_json_report, canonical_reporting.save_json_report)

    def test_legacy_modules_are_definition_free(self) -> None:
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        for path in (LEGACY_LOGGING_PATH, LEGACY_REPORTING_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_historical_implementations_are_byte_preserved(self) -> None:
        self.assertEqual(hashlib.sha256(ARCHIVE_LOGGING_PATH.read_bytes()).hexdigest(), "64dcff0c00a4b085dafc2b6e7756847ca240cd6c8f45e55735c673683b9751da")
        self.assertEqual(hashlib.sha256(ARCHIVE_REPORTING_PATH.read_bytes()).hexdigest(), "de44f6562f316e9c9e8f9dc4e993bbe5da8586f7deb9b60c1cd3d720bd1b43db")

    def test_consumers_import_canonical_sources(self) -> None:
        cli = CLI_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.logging_setup import setup_logging", cli)
        self.assertIn("from hakimi_research.reporting import (", cli)
        self.assertIn("save_json_report_bundle_v2", cli)
        self.assertNotIn("from quant_bot.logging_setup import", cli)
        self.assertNotIn("from quant_bot.reporting import", cli)
        manifest_test = MANIFEST_TEST_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.reporting import save_json_report", manifest_test)

    def test_logging_rejects_invalid_contract_before_effects(self) -> None:
        invalid = (("", "INFO"), (" logs ", "INFO"), (StringAlias("logs"), "INFO"), ("logs", "info"), ("logs", "NOT_A_LEVEL"), ("logs", StringAlias("INFO")))
        with patch.object(canonical_logging.Path, "mkdir") as mkdir_mock, patch.object(canonical_logging.logging, "FileHandler") as file_handler_mock, patch.object(canonical_logging.logging, "basicConfig") as basic_config_mock:
            for log_dir, level in invalid:
                with self.subTest(log_dir=log_dir, level=level):
                    with self.assertRaises(ValueError):
                        canonical_logging.setup_logging(log_dir, level)  # type: ignore[arg-type]
            mkdir_mock.assert_not_called()
            file_handler_mock.assert_not_called()
            basic_config_mock.assert_not_called()

    def test_valid_logging_configuration_is_explicit_and_mocked(self) -> None:
        file_handler = Mock()
        console_handler = Mock()
        with patch.object(canonical_logging.Path, "mkdir") as mkdir_mock, patch.object(canonical_logging.logging, "FileHandler", return_value=file_handler) as file_handler_mock, patch.object(canonical_logging.logging, "StreamHandler", return_value=console_handler), patch.object(canonical_logging.logging, "basicConfig") as basic_config_mock:
            canonical_logging.setup_logging("logs", "DEBUG")
        mkdir_mock.assert_called_once_with(parents=True, exist_ok=True)
        file_handler_mock.assert_called_once_with(Path("logs") / "bot.log", encoding="utf-8")
        file_handler.setLevel.assert_called_once_with(canonical_logging.logging.DEBUG)
        console_handler.setLevel.assert_called_once_with(canonical_logging.logging.WARNING)
        self.assertEqual(basic_config_mock.call_args.kwargs["level"], canonical_logging.logging.DEBUG)
        self.assertTrue(basic_config_mock.call_args.kwargs["force"])

    def test_report_rendering_is_canonical(self) -> None:
        payload = {"z": [3, 2, 1], "a": {"text": "hakimi", "ok": True}}
        expected = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        self.assertEqual(canonical_reporting.render_json_report(payload), expected)

    def test_report_payload_requires_recursive_exact_native_json(self) -> None:
        cycle: list[object] = []
        cycle.append(cycle)
        too_deep: list[object] = []
        cursor = too_deep
        for _ in range(65):
            child: list[object] = []
            cursor.append(child)
            cursor = child
        invalid = (DictAlias({"ok": True}), {"value": ListAlias([1])}, {StringAlias("key"): 1}, {"value": StringAlias("x")}, {"value": IntAlias(1)}, {"value": (1, 2)}, {"value": math.nan}, {"value": math.inf}, {"value": cycle}, {"value": too_deep})
        for payload in invalid:
            with self.subTest(payload_type=type(payload)):
                with self.assertRaises(ValueError):
                    canonical_reporting.render_json_report(payload)  # type: ignore[arg-type]

    def test_invalid_report_contract_has_no_filesystem_effect(self) -> None:
        invalid = (({}, "reports", "backtest", ""), ({}, "reports", "../escape", VALID_ARTIFACT_ID), ({}, StringAlias("reports"), "backtest", VALID_ARTIFACT_ID), ({}, "reports", StringAlias("backtest"), VALID_ARTIFACT_ID), ({}, "reports", "backtest", StringAlias(VALID_ARTIFACT_ID)), ({"metric": math.nan}, "reports", "backtest", VALID_ARTIFACT_ID))
        with patch.object(canonical_reporting.Path, "mkdir") as mkdir_mock, patch.object(canonical_reporting.Path, "open", mock_open()) as open_mock:
            for payload, directory, prefix, artifact_id in invalid:
                with self.subTest(prefix=prefix, artifact_id=artifact_id):
                    with self.assertRaises(ValueError):
                        canonical_reporting.save_json_report(payload, directory, prefix, artifact_id=artifact_id)  # type: ignore[arg-type]
            mkdir_mock.assert_not_called()
            open_mock.assert_not_called()

    def test_report_write_is_deterministic_exclusive_and_idempotent(self) -> None:
        payload = {"metric": 1.0, "status": "BLOCK"}
        rendered = canonical_reporting.render_json_report(payload)
        writer = mock_open()
        with patch.object(canonical_reporting.Path, "mkdir") as mkdir_mock, patch.object(canonical_reporting.Path, "open", writer):
            path = canonical_reporting.save_json_report(payload, "reports", "backtest", artifact_id=VALID_ARTIFACT_ID)
        self.assertEqual(Path(path).name, f"backtest_{VALID_ARTIFACT_ID}.json")
        mkdir_mock.assert_called_once_with(parents=True, exist_ok=True)
        writer.assert_called_once_with("x", encoding="utf-8", newline="\n")
        writer().write.assert_called_once_with(rendered)

        with patch.object(canonical_reporting.Path, "mkdir"), patch.object(canonical_reporting.Path, "open", side_effect=FileExistsError), patch.object(canonical_reporting.Path, "read_text", return_value=rendered):
            retry = canonical_reporting.save_json_report(payload, "reports", "backtest", artifact_id=VALID_ARTIFACT_ID)
        self.assertEqual(retry, path)

        with patch.object(canonical_reporting.Path, "mkdir"), patch.object(canonical_reporting.Path, "open", side_effect=FileExistsError), patch.object(canonical_reporting.Path, "read_text", return_value="different\n"):
            with self.assertRaises(FileExistsError):
                canonical_reporting.save_json_report(payload, "reports", "backtest", artifact_id=VALID_ARTIFACT_ID)


if __name__ == "__main__":
    unittest.main()
