from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from hakimi_research import experiment_manifest as experiment_manifest_source
from hakimi_research.experiment_manifest import build_local_experiment_context
from hakimi_research.deterministic_frozen_benchmark import (
    verify_deterministic_frozen_benchmark_reference,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
LOCK_PATH = REPO_ROOT / "requirements.research.lock"
LEGACY_LOCK_PATH = PROJECT_ROOT / "requirements.research.lock"
EXAMPLE_ROOT = REPO_ROOT / "examples" / "deterministic_frozen_benchmark_v2"
ROBUSTNESS_REFERENCE_ROOT = (
    REPO_ROOT / "examples" / "deterministic_strategy_robustness_benchmark_v1"
)
STATISTICAL_CORRECTION_REFERENCE_ROOT = (
    REPO_ROOT
    / "examples"
    / "deterministic_strategy_statistical_correction_benchmark_v1"
)
ARCHIVE_ROOT = REPO_ROOT / "archive" / "historical_research" / "adr0525_input_identity_v1"
ATTRIBUTES_PATH = REPO_ROOT / ".gitattributes"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchDependencyLockV1Tests(unittest.TestCase):
    def test_lock_is_exact_minimal_runtime_closure(self) -> None:
        self.assertFalse(LEGACY_LOCK_PATH.exists())
        entries = [
            line.strip()
            for line in LOCK_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            entries,
            [
                "numpy==2.4.6",
                "pandas==3.0.3",
                "python-dateutil==2.9.0.post0",
                "six==1.17.0",
                "tzdata==2026.2",
            ],
        )
        self.assertTrue(all(re.fullmatch(r"[a-z0-9-]+==[^=<>!~]+", item) for item in entries))

    def test_experiment_context_prefers_research_lock(self) -> None:
        with patch.object(experiment_manifest_source, "_git_output", return_value=""):
            context = build_local_experiment_context(REPO_ROOT)
        self.assertEqual(context["dependency_lock_name"], "requirements.research.lock")
        self.assertEqual(context["dependency_lock_hash"], _sha256(LOCK_PATH))
        self.assertTrue(context["dependency_lock_fully_pinned"])

    def test_example_input_identity_matches_expected_result(self) -> None:
        manifest = json.loads(
            (EXAMPLE_ROOT / "fixture_manifest.json").read_text(encoding="utf-8")
        )
        attributes = [
            line
            for line in ATTRIBUTES_PATH.read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertEqual(
            attributes,
            [
                "archive/historical_research/adr0525_input_identity_v1/config.json text eol=lf",
                "archive/historical_research/adr0525_input_identity_v1/dataset.csv text eol=lf",
                "archive/historical_research/adr0525_input_identity_v1/expected_result.json text eol=lf",
                "archive/historical_research/adr0525_input_identity_v1/README.md text eol=lf",
                "archive/historical_research/adr0525_input_identity_v1/verify.py text eol=lf",
                "archive/historical_research/adr0526_experiment_manifest.py text eol=lf",
                "archive/historical_research/adr0527_config.py text eol=lf",
                "archive/historical_research/adr0528_models.py text eol=lf",
                "archive/historical_research/adr0529_execution.py text eol=lf",
                "archive/historical_research/adr0530_risk.py text eol=lf",
                "archive/historical_research/adr0531_backtest.py text eol=lf",
                "archive/historical_research/adr0532_data.py text eol=lf",
                "archive/historical_research/adr0533_strategy_base.py text eol=lf",
                "archive/historical_research/adr0533_strategy_templates.py text eol=lf",
                "archive/historical_research/adr0533_strategy_init.py text eol=lf",
                "archive/historical_research/adr0534_indicators.py text eol=lf",
                "archive/historical_research/adr0535_logging_setup.py text eol=lf",
                "archive/historical_research/adr0535_reporting.py text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/config.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/dataset.csv text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/experiment_context.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/expected_report.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/expected_report.md text eol=lf",
                "examples/deterministic_frozen_benchmark_v1/fixture_manifest.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/config.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/dataset.csv text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/dataset_governance.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/experiment_context.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/expected_report.json text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/expected_report.md text eol=lf",
                "examples/deterministic_frozen_benchmark_v2/fixture_manifest.json text eol=lf",
                "examples/deterministic_strategy_family_benchmark_v1/expected_bundle.json text eol=lf",
                "examples/deterministic_strategy_family_benchmark_v1/expected_bundle.md text eol=lf",
                "examples/deterministic_strategy_family_benchmark_v1/fixture_manifest.json text eol=lf",
                "examples/deterministic_strategy_robustness_benchmark_v1/expected_receipt.json text eol=lf",
                "examples/deterministic_strategy_robustness_benchmark_v1/expected_receipt.md text eol=lf",
                "examples/deterministic_strategy_robustness_benchmark_v1/fixture_manifest.json text eol=lf",
                "examples/deterministic_strategy_statistical_correction_benchmark_v1/expected_receipt.json text eol=lf",
                "examples/deterministic_strategy_statistical_correction_benchmark_v1/expected_receipt.md text eol=lf",
                "examples/deterministic_strategy_statistical_correction_benchmark_v1/fixture_manifest.json text eol=lf",
                "requirements.research.lock text eol=lf",
            ],
        )
        for name in (
            "config.json",
            "dataset.csv",
            "dataset_governance.json",
            "experiment_context.json",
            "expected_report.json",
            "expected_report.md",
            "fixture_manifest.json",
        ):
            self.assertNotIn(b"\r", (EXAMPLE_ROOT / name).read_bytes())
        for name in (
            "expected_receipt.json",
            "expected_receipt.md",
            "fixture_manifest.json",
        ):
            self.assertNotIn(
                b"\r",
                (ROBUSTNESS_REFERENCE_ROOT / name).read_bytes(),
            )
        for name in (
            "expected_receipt.json",
            "expected_receipt.md",
            "fixture_manifest.json",
        ):
            self.assertNotIn(
                b"\r",
                (STATISTICAL_CORRECTION_REFERENCE_ROOT / name).read_bytes(),
            )
        self.assertEqual(
            manifest["input_files"]["dataset.csv"],
            _sha256(EXAMPLE_ROOT / "dataset.csv"),
        )
        self.assertEqual(
            manifest["input_files"]["config.json"],
            _sha256(EXAMPLE_ROOT / "config.json"),
        )
        self.assertEqual(
            manifest["input_files"]["dataset_governance.json"],
            _sha256(EXAMPLE_ROOT / "dataset_governance.json"),
        )
        with (EXAMPLE_ROOT / "dataset.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), manifest["data_rows"])
        self.assertEqual(len(rows), 128)
        self.assertEqual(len({row["timestamp"] for row in rows}), len(rows))

    def test_example_is_local_only_and_has_no_authority(self) -> None:
        config = json.loads((EXAMPLE_ROOT / "config.json").read_text(encoding="utf-8"))
        report = json.loads(
            (EXAMPLE_ROOT / "expected_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["mode"], "backtest")
        self.assertEqual(config["data"]["provider"], "csv")
        self.assertFalse(config["data"]["use_cache"])
        self.assertEqual(config["execution"]["broker"], "research_simulator")
        self.assertFalse(config["execution"]["live_trading_enabled"])
        self.assertEqual(report["quality_gate"]["status"], "BLOCK")
        self.assertFalse(report["quality_gate"]["frozen_test_is_blind"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_example_verifier_passes(self) -> None:
        result = verify_deterministic_frozen_benchmark_reference()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["checks"].values()))

    def test_old_input_only_fixture_is_byte_identically_archived(self) -> None:
        expected = {
            "config.json": "5ded5c5f350bcfbd42eb5a782e9064024f9c5a34bc9d20b113ab121de9fda82f",
            "dataset.csv": "0a76f74772bd9830428684d90bd72578ce828ef47b04102dedead3135a80e23a",
            "expected_result.json": "23b56240b99c98d9fc38c5a364ac15d3b05cb54e75206b7f48608ac234cbac66",
            "README.md": "88ed18e84a750d4113f8853c09582c44ecbd17955f9dcae45573acfc2c662cc0",
            "verify.py": "395e96dca3cd6a94b0fbdee9cdd8030b41f3c1f76b30f90b7147c3d417dde19b",
        }
        self.assertFalse((PROJECT_ROOT / "examples" / "deterministic_experiment").exists())
        self.assertEqual(
            {name: _sha256(ARCHIVE_ROOT / name) for name in expected},
            expected,
        )


if __name__ == "__main__":
    unittest.main()
