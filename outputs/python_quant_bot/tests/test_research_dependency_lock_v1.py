from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

from quant_bot.experiment_manifest import build_local_experiment_context


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PROJECT_ROOT / "requirements.research.lock"
EXAMPLE_ROOT = PROJECT_ROOT / "examples" / "deterministic_experiment"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchDependencyLockV1Tests(unittest.TestCase):
    def test_lock_is_exact_minimal_runtime_closure(self) -> None:
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
        context = build_local_experiment_context(PROJECT_ROOT)
        self.assertEqual(context["dependency_lock_name"], "requirements.research.lock")
        self.assertEqual(context["dependency_lock_hash"], _sha256(LOCK_PATH))
        self.assertTrue(context["dependency_lock_fully_pinned"])

    def test_example_input_identity_matches_expected_result(self) -> None:
        expected = json.loads(
            (EXAMPLE_ROOT / "expected_result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(expected["dataset_sha256"], _sha256(EXAMPLE_ROOT / "dataset.csv"))
        self.assertEqual(expected["config_sha256"], _sha256(EXAMPLE_ROOT / "config.json"))
        with (EXAMPLE_ROOT / "dataset.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), expected["data_rows"])
        self.assertEqual(len({row["timestamp"] for row in rows}), len(rows))

    def test_example_is_local_only_and_has_no_authority(self) -> None:
        config = json.loads((EXAMPLE_ROOT / "config.json").read_text(encoding="utf-8"))
        expected = json.loads(
            (EXAMPLE_ROOT / "expected_result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["mode"], "backtest")
        self.assertEqual(config["data"]["provider"], "csv")
        self.assertFalse(config["data"]["use_cache"])
        self.assertFalse(expected["performance_metrics_included"])
        self.assertTrue(all(value is False for value in expected["authority"].values()))

    def test_example_verifier_passes(self) -> None:
        verifier_path = EXAMPLE_ROOT / "verify.py"
        spec = importlib.util.spec_from_file_location("deterministic_example_verify", verifier_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
