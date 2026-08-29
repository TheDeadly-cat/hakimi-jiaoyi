from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest

from _canonical_source import SOURCE_LAYOUT_SCHEMA_VERSION, activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MODULE_PATH = REPO_ROOT / "src" / "hakimi_research" / "product_capabilities.py"
LEGACY_MODULE_PATH = PROJECT_ROOT / "exchange_terminal" / "domain" / "contracts.py"

activate_canonical_source()

import run_bot  # noqa: E402
from exchange_terminal.domain import contracts as legacy  # noqa: E402
from hakimi_research import product_capabilities as canonical  # noqa: E402


MIGRATED_SYMBOLS = (
    "CapabilityContract",
    "ProductCapabilityCatalog",
    "build_product_capability_catalog",
    "build_research_only_capability",
    "product_capability_status_for_cli_command",
    "supported_cli_commands",
)


class CanonicalProductCapabilitySourceV1Tests(unittest.TestCase):
    def test_canonical_source_root_is_outside_outputs(self) -> None:
        self.assertEqual(SOURCE_LAYOUT_SCHEMA_VERSION, "canonical-source-layout-v1")
        self.assertEqual(activate_canonical_source(), REPO_ROOT / "src")
        source_path = Path(inspect.getsourcefile(canonical.CapabilityContract) or "").resolve()
        self.assertEqual(source_path, CANONICAL_MODULE_PATH)
        self.assertNotIn("outputs", source_path.relative_to(REPO_ROOT).parts)

    def test_legacy_module_reexports_identical_objects(self) -> None:
        for symbol in MIGRATED_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_active_cli_consumes_canonical_objects(self) -> None:
        self.assertIs(
            run_bot.build_product_capability_catalog,
            canonical.build_product_capability_catalog,
        )
        self.assertIs(
            run_bot.product_capability_status_for_cli_command,
            canonical.product_capability_status_for_cli_command,
        )
        self.assertIs(run_bot.supported_cli_commands, canonical.supported_cli_commands)

    def test_dashboard_imports_canonical_boundary_directly(self) -> None:
        source = (PROJECT_ROOT / "dashboard_app.py").read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.product_capabilities import", source)
        self.assertNotIn(
            "from exchange_terminal.domain.contracts import build_product_capability_catalog",
            source,
        )

    def test_legacy_module_cannot_redefine_migrated_symbols(self) -> None:
        tree = ast.parse(LEGACY_MODULE_PATH.read_text(encoding="utf-8"))
        definitions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(definitions.intersection(MIGRATED_SYMBOLS))
        canonical_tree = ast.parse(CANONICAL_MODULE_PATH.read_text(encoding="utf-8"))
        canonical_definitions = {
            node.name
            for node in canonical_tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue(set(MIGRATED_SYMBOLS).issubset(canonical_definitions))


if __name__ == "__main__":
    unittest.main()
