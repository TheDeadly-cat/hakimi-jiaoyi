from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
activate_canonical_source()

from hakimi_research.compatibility_source_audit import (  # noqa: E402
    QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK,
    QUANT_BOT_EXPECTED_MODULES,
    evaluate_quant_bot_compatibility_package,
    verify_quant_bot_compatibility_package,
)


def current_sources() -> dict[str, str]:
    root = PROJECT_ROOT / "quant_bot"
    sources: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).with_suffix("")
        module = "quant_bot." + ".".join(relative.parts)
        sources[module] = path.read_text(encoding="utf-8-sig")
    return sources


class QuantBotCompatibilityPackageV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = current_sources()
        self.audit = evaluate_quant_bot_compatibility_package(self.sources)

    def test_current_package_is_exact_compatibility_reexport_only(self) -> None:
        self.assertEqual(self.audit["status"], "PASS")
        self.assertEqual(
            self.audit["decision"],
            "COMPATIBILITY_REEXPORT_PACKAGE_ONLY",
        )
        self.assertEqual(self.audit["module_count"], 14)
        self.assertEqual(set(self.sources), {item[0] for item in QUANT_BOT_EXPECTED_MODULES})
        self.assertEqual(self.audit["violations"], [])
        for field in (
            "native_source_mapping_verified",
            "module_set_exact",
            "all_modules_ast_parsed",
            "definitions_absent",
            "canonical_import_targets_exact",
            "dynamic_code_absent",
            "compatibility_statements_only",
            "formal_implementation_absent",
        ):
            self.assertTrue(self.audit["facts"][field])
        for field in (
            "raw_source_embedded",
            "filesystem_io_performed",
            "runtime_import_execution_performed",
        ):
            self.assertFalse(self.audit["facts"][field])
        self.assertFalse(any(self.audit["authority"].values()))
        self.assertEqual(
            self.audit["authority"],
            QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK,
        )

    def test_records_bind_every_source_without_embedding_source(self) -> None:
        self.assertEqual(len(self.audit["module_records"]), 14)
        for record in self.audit["module_records"]:
            self.assertRegex(record["source_hash"], r"^[0-9a-f]{64}$")
            self.assertTrue(record["definitions_absent"])
            self.assertTrue(record["canonical_import_target_exact"])
            self.assertTrue(record["dynamic_code_absent"])
            self.assertTrue(record["compatibility_statements_only"])
        serialized = json.dumps(self.audit, sort_keys=True)
        self.assertNotIn("from hakimi_research", serialized)
        self.assertNotIn("class ", serialized)
        self.assertNotIn("def ", serialized)

    def test_formal_definition_import_drift_and_dynamic_code_block(self) -> None:
        mutations = (
            lambda value: value.__setitem__(
                "quant_bot.backtest",
                value["quant_bot.backtest"] + "\nclass Broker: pass\n",
            ),
            lambda value: value.__setitem__(
                "quant_bot.risk",
                value["quant_bot.risk"].replace(
                    "hakimi_research.risk",
                    "hakimi_research.execution",
                ),
            ),
            lambda value: value.__setitem__(
                "quant_bot.models",
                value["quant_bot.models"] + "\n__import__('socket')\n",
            ),
        )
        for mutate in mutations:
            candidate = deepcopy(self.sources)
            mutate(candidate)
            audit = evaluate_quant_bot_compatibility_package(candidate)
            self.assertEqual(audit["status"], "BLOCK")
            self.assertFalse(audit["facts"]["formal_implementation_absent"])

    def test_missing_or_added_module_blocks_exact_inventory(self) -> None:
        missing = deepcopy(self.sources)
        missing.pop("quant_bot.backtest")
        added = deepcopy(self.sources)
        added["quant_bot.broker"] = "from hakimi_research.execution import ResearchExecutionSimulator\n"
        for candidate in (missing, added):
            audit = evaluate_quant_bot_compatibility_package(candidate)
            self.assertEqual(audit["status"], "BLOCK")
            self.assertIn("MODULE_SET_MISMATCH", audit["violations"])

    def test_non_native_mapping_is_unknown_without_controlled_methods(self) -> None:
        class MappingAlias(dict):
            reached = False

            def items(self):
                type(self).reached = True
                return super().items()

        audit = evaluate_quant_bot_compatibility_package(MappingAlias(self.sources))
        self.assertEqual(audit["status"], "UNKNOWN")
        self.assertFalse(MappingAlias.reached)

    def test_exact_verifier_rejects_resealed_promotion(self) -> None:
        self.assertTrue(
            verify_quant_bot_compatibility_package(self.audit, self.sources)
        )
        promoted = deepcopy(self.audit)
        promoted["authority"]["formal_implementation_in_outputs"] = True
        self.assertFalse(
            verify_quant_bot_compatibility_package(promoted, self.sources)
        )

    def test_readme_describes_completed_core_compatibility_boundary(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("compatibility re-export only", readme)
        self.assertNotIn("quant_bot              # pending consumer-first migration", readme)


if __name__ == "__main__":
    unittest.main()
