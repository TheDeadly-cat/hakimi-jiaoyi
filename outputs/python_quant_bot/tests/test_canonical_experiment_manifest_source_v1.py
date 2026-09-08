from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import inspect
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PATH = REPO_ROOT / "src" / "hakimi_research" / "experiment_manifest.py"
LEGACY_PATH = PROJECT_ROOT / "quant_bot" / "experiment_manifest.py"
ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0526_experiment_manifest.py"

activate_canonical_source()

from hakimi_research import experiment_manifest as canonical  # noqa: E402
from quant_bot import experiment_manifest as legacy  # noqa: E402


MIGRATED_SYMBOLS = (
    "SCHEMA_VERSION",
    "build_local_experiment_context",
    "build_reproducible_experiment_manifest",
    "canonical_payload_hash",
    "verify_reproducible_experiment_manifest",
)


def _context() -> dict:
    return {
        "git_commit_sha": "a" * 40,
        "git_worktree_clean": True,
        "dependency_lock_hash": "b" * 64,
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "random_seed": 7,
        "runtime_version": "python-test",
        "evaluation_role": "FROZEN_TEST",
        "evaluation_protocol_hash": "c" * 64,
        "evaluation_protocol_verified": True,
    }


def _reproducibility() -> dict:
    return {
        "run_hash": "d" * 64,
        "config_hash": "e" * 64,
        "data_hash": "f" * 64,
        "data_start": "2025-01-01T00:00:00Z",
        "data_end": "2025-02-01T00:00:00Z",
    }


def _build(**overrides):
    values = {
        "result_payload": {"metric": 1.0},
        "reproducibility": _reproducibility(),
        "strategy_name": "dual_ma",
        "strategy_version": "v1",
        "symbol": "SYNTH-001",
        "timeframe": "1d",
        "fee_rate": 0.001,
        "slippage_pct": 0.001,
        "context": _context(),
    }
    values.update(overrides)
    return canonical.build_reproducible_experiment_manifest(**values)


class CanonicalExperimentManifestSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs(self) -> None:
        source = Path(inspect.getsourcefile(canonical.canonical_payload_hash) or "").resolve()
        self.assertEqual(source, CANONICAL_PATH)
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)

    def test_legacy_module_reexports_identical_public_objects(self) -> None:
        for symbol in MIGRATED_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_active_consumers_import_canonical_module_directly(self) -> None:
        paths = (
            REPO_ROOT / "src" / "hakimi_research" / "backtest.py",
            REPO_ROOT / "src" / "hakimi_research" / "frozen_evaluation.py",
            REPO_ROOT / "src" / "hakimi_research" / "cli.py",
            PROJECT_ROOT
            / "exchange_terminal"
            / "application"
            / "synthetic_strategy_reproducibility_provenance_gap_audit_v1.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("hakimi_research.experiment_manifest", source)
                self.assertNotIn("from quant_bot.experiment_manifest", source)

    def test_legacy_module_contains_no_contract_definitions(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(definitions)

    def test_old_implementation_is_byte_identically_archived(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "9b77e81fd18659a8e39ced8978f5c24c358c85b9c7f1b1e7b49da2e204a60b53",
        )

    def test_mapping_subclasses_are_rejected_before_controlled_methods(self) -> None:
        class AliasGetDict(dict):
            reached = False

            def get(self, key, default=None):
                type(self).reached = True
                return super().get(key, default)

        class AliasItemsDict(dict):
            reached = False

            def items(self):
                type(self).reached = True
                return {"metric": 2.0}.items()

        with self.assertRaisesRegex(ValueError, "reproducibility_exact_native_required"):
            _build(reproducibility=AliasGetDict(_reproducibility()))
        self.assertFalse(AliasGetDict.reached)
        self.assertEqual(canonical.canonical_payload_hash(AliasItemsDict({"metric": 1.0})), "")
        self.assertFalse(AliasItemsDict.reached)

    def test_nested_and_numeric_subclasses_fail_closed(self) -> None:
        class EvilStr(str):
            pass

        class EvilFloat(float):
            reached = False

            def __float__(self):
                type(self).reached = True
                return 0.001

        self.assertEqual(canonical.canonical_payload_hash({"value": EvilStr("x")}), "")
        with self.assertRaisesRegex(ValueError, "fee_rate_exact_finite_number_required"):
            _build(fee_rate=EvilFloat(999.0))
        self.assertFalse(EvilFloat.reached)
        manifest = _build()
        hostile = deepcopy(manifest)
        hostile["blockers"] = type("EvilList", (list,), {})(hostile["blockers"])
        self.assertFalse(
            canonical.verify_reproducible_experiment_manifest(
                hostile,
                {"metric": 1.0},
            )
        )

    def test_native_manifest_identity_and_authority_remain_stable(self) -> None:
        manifest = _build()
        self.assertEqual(manifest["status"], "PASS")
        self.assertTrue(manifest["ranking_gate"]["input_allowed"])
        self.assertTrue(
            canonical.verify_reproducible_experiment_manifest(
                manifest,
                {"metric": 1.0},
            )
        )
        for field in (
            "parameter_selection_allowed",
            "paper_authorized",
            "live_order_allowed",
            "order_entry_allowed",
            "result_is_profitability_proof",
        ):
            self.assertIs(manifest[field], False)


if __name__ == "__main__":
    unittest.main()
