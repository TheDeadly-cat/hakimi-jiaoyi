from __future__ import annotations

import ast
from copy import deepcopy
import inspect
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from _canonical_source import SOURCE_LAYOUT_SCHEMA_VERSION, activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MODULE_PATH = REPO_ROOT / "src" / "hakimi_research" / "product_capabilities.py"
CONTRACT_PATH = (
    REPO_ROOT
    / "src"
    / "hakimi_research"
    / "contracts"
    / "product-capabilities.json"
)
CONTRACT_SCHEMA_PATH = CONTRACT_PATH.with_name("product-capabilities.schema.json")
LEGACY_MODULE_PATH = PROJECT_ROOT / "exchange_terminal" / "domain" / "contracts.py"
NODE_CONTRACT_PATH = REPO_ROOT / "outputs" / "hakimi_trade_electron" / "backend-runtime-contract.js"

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

    def test_versioned_definition_is_the_canonical_cross_language_source(self) -> None:
        definition = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            canonical.PRODUCT_CAPABILITY_DEFINITION_RESOURCE,
            "hakimi_research/contracts/product-capabilities.json",
        )
        self.assertEqual(
            definition["definition_schema_version"],
            "product-capability-definition-v1",
        )
        self.assertEqual(
            definition["$schema"],
            "./product-capabilities.schema.json",
        )
        self.assertEqual(
            schema["properties"]["catalog"]["properties"]["product_mode"]["const"],
            "research_only",
        )
        catalog = canonical.build_product_capability_catalog().to_dict()
        capability_statuses = {
            item["name"]: item["status"]
            for item in definition["catalog"]["capabilities"]
        }
        cli_commands = {
            item["command"]: capability_statuses[item["capability"]]
            for item in definition["catalog"]["cli_bindings"]
        }
        self.assertEqual(catalog["capabilities"], capability_statuses)
        self.assertEqual(catalog["cli_commands"], cli_commands)
        self.assertEqual(catalog["authority"], definition["catalog"]["authority"])
        self.assertEqual(definition, canonical.build_product_capability_definition())
        result = subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "tools/generate_product_capabilities.py"), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "src/hakimi_research/contracts/product-capabilities.json text eol=lf",
            (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8"),
        )

    def test_python_definition_is_detached_and_runtime_does_not_consume_editable_json(self) -> None:
        first = canonical.build_product_capability_definition()
        first["catalog"]["authority"]["paper_allowed"] = True
        self.assertIs(canonical.build_product_capability_definition()["catalog"]["authority"]["paper_allowed"], False)
        source = CANONICAL_MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.capability_definition import", source)
        self.assertNotIn("read_text", source)
        self.assertNotIn("json.loads", source)

    def test_python_definition_loader_preserves_execution_locks(self) -> None:
        definition = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        unsafe_authority = deepcopy(definition)
        unsafe_authority["catalog"]["authority"]["paper_allowed"] = True
        numeric_authority = deepcopy(definition)
        numeric_authority["catalog"]["authority"]["paper_allowed"] = 0
        unsafe_capability = deepcopy(definition)
        next(
            item
            for item in unsafe_capability["catalog"]["capabilities"]
            if item["name"] == "paper_execution"
        )["status"] = "Supported"
        unsafe_binding = deepcopy(definition)
        next(
            item
            for item in unsafe_binding["catalog"]["cli_bindings"]
            if item["command"] == "paper"
        )["capability"] = "historical_backtest"
        cases = (
            (unsafe_authority, "authority_invalid"),
            (numeric_authority, "authority_invalid"),
            (unsafe_capability, "execution_lock_invalid"),
            (unsafe_binding, "archived_cli_lock_invalid"),
        )
        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error), patch.object(
                canonical,
                "build_product_capability_definition",
                return_value=payload,
            ):
                with self.assertRaisesRegex(RuntimeError, expected_error):
                    canonical._load_product_capability_definition()

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

    def test_electron_exact_catalog_matches_canonical_product_truth(self) -> None:
        script = (
            "const c=require(process.argv[1]);"
            "process.stdout.write(JSON.stringify({"
            "capabilities:c.EXPECTED_PRODUCT_CAPABILITIES,"
            "cli_commands:c.EXPECTED_CLI_COMMANDS,"
            "definition_path:c.PRODUCT_CAPABILITY_DEFINITION_PATH}));"
        )
        result = subprocess.run(
            ["node", "-e", script, str(NODE_CONTRACT_PATH)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        projection = json.loads(result.stdout)
        catalog = canonical.build_product_capability_catalog().to_dict()
        self.assertEqual(projection["capabilities"], catalog["capabilities"])
        self.assertEqual(projection["cli_commands"], catalog["cli_commands"])
        self.assertEqual(Path(projection["definition_path"]).resolve(), CONTRACT_PATH)

    def test_python_node_and_fixture_do_not_embed_duplicate_capability_tables(self) -> None:
        python_source = CANONICAL_MODULE_PATH.read_text(encoding="utf-8")
        node_source = NODE_CONTRACT_PATH.read_text(encoding="utf-8")
        fixture_source = NODE_CONTRACT_PATH.with_name(
            "backend-runtime-contract.test.js"
        ).read_text(encoding="utf-8")
        duplicated_entry = '"backtest": "Supported"'
        self.assertNotIn(duplicated_entry, python_source)
        self.assertNotIn(duplicated_entry, node_source)
        self.assertNotIn(duplicated_entry, fixture_source)
        self.assertIn("definitionPath = PRODUCT_CAPABILITY_DEFINITION_PATH", node_source)
        self.assertIn("readFileSync(definitionPath", node_source)
        self.assertIn("EXPECTED_CLI_COMMANDS", fixture_source)


if __name__ == "__main__":
    unittest.main()
