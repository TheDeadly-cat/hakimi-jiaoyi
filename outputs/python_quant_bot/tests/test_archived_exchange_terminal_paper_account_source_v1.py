from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FORMAL_SERVICES = ROOT / "outputs" / "python_quant_bot" / "exchange_terminal" / "services"
FORMAL_TESTS = ROOT / "outputs" / "python_quant_bot" / "tests"
ARCHIVE = ROOT / "archive" / "legacy_paper"

EXPECTED_ARCHIVE_HASHES = {
    ARCHIVE / "exchange_terminal_services" / "paper_account.py": "656ca2609543e220188b2d13ba641d01a497ac0db7b4a0ba05a8dc7a5d02a428",
    ARCHIVE / "exchange_terminal_services" / "paper_strategy_clock.py": "b0b4be66f4003fc7476ff1f3ace0cc6bc38af54b19fd404087e3deb9433bc24b",
    ARCHIVE / "tests" / "test_paper_strategy_clock.py": "cd61c974a6a768d06465d6ed0e781c59a48671fdc8a26045a1cd1603d3e64fb1",
    ARCHIVE / "tests" / "test_core_services_before_paper_account_archive.py": "e3e5963b79a04af9be7c2e644fc2f4f1650a7e3395520d46d0f2a2f1098e8c74",
}
TARGET_MODULES = {"paper_account", "paper_strategy_clock"}
TARGET_SYMBOLS = {
    "PaperAccount",
    "configure_paper_account_runtime",
    "execution_report_contract_errors",
    "paper_clock_transition",
}
REMOVED_TEST_METHODS = {
    "test_account_execution_report_contract_rejects_wrong_identity_and_arithmetic",
    "test_paper_account_close_uses_requested_quantity_and_only_charged_funding",
    "test_paper_account_does_not_apply_an_idempotent_fill_twice",
    "test_paper_account_preserves_single_symbol_binding_and_lock_on_reset",
    "test_paper_account_does_not_record_zero_fill_ioc_as_an_order",
    "test_conditional_orders_use_unified_long_short_execution_once",
    "test_paper_account_rejects_invalid_manual_and_conditional_size_without_expansion",
    "test_paper_account_blocks_persistent_condition_orders_at_service_boundary",
    "test_paper_account_reset_preserves_consumed_order_identity",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] in TARGET_MODULES:
                    matches.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module_tail = (node.module or "").split(".")[-1]
            if module_tail in TARGET_MODULES:
                matches.append(node.module or "")
            for alias in node.names:
                if alias.name in TARGET_MODULES:
                    matches.append(f"{node.module}:{alias.name}")
    return matches


class ArchivedExchangeTerminalPaperAccountSourceV1Tests(unittest.TestCase):
    def test_formal_modules_and_dedicated_test_are_absent(self) -> None:
        self.assertFalse((FORMAL_SERVICES / "paper_account.py").exists())
        self.assertFalse((FORMAL_SERVICES / "paper_strategy_clock.py").exists())
        self.assertFalse((FORMAL_TESTS / "test_paper_strategy_clock.py").exists())

    def test_archive_preserves_exact_source_and_test_bytes(self) -> None:
        for path, expected_hash in EXPECTED_ARCHIVE_HASHES.items():
            self.assertTrue(path.is_file(), path)
            self.assertEqual(_sha256(path), expected_hash, path)

    def test_archived_source_retains_historical_identity(self) -> None:
        account_tree = ast.parse(
            (ARCHIVE / "exchange_terminal_services" / "paper_account.py").read_text(encoding="utf-8")
        )
        clock_tree = ast.parse(
            (ARCHIVE / "exchange_terminal_services" / "paper_strategy_clock.py").read_text(encoding="utf-8")
        )
        account_classes = {node.name for node in account_tree.body if isinstance(node, ast.ClassDef)}
        account_functions = {node.name for node in account_tree.body if isinstance(node, ast.FunctionDef)}
        clock_functions = {node.name for node in clock_tree.body if isinstance(node, ast.FunctionDef)}
        self.assertIn("PaperAccount", account_classes)
        self.assertIn("configure_paper_account_runtime", account_functions)
        self.assertIn("execution_report_contract_errors", account_functions)
        self.assertIn("paper_clock_transition", clock_functions)

    def test_formal_service_import_graph_has_no_legacy_account_edge(self) -> None:
        scanned = sorted(FORMAL_SERVICES.glob("*.py"))
        violations = {str(path.relative_to(ROOT)): _target_imports(path) for path in scanned if _target_imports(path)}
        self.assertEqual(violations, {})

    def test_shared_core_test_no_longer_claims_legacy_account_support(self) -> None:
        path = FORMAL_TESTS / "test_core_services.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        methods = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(names & TARGET_SYMBOLS)
        self.assertFalse(methods & REMOVED_TEST_METHODS)
        self.assertEqual(_target_imports(path), [])

    def test_archive_directory_is_not_an_import_package(self) -> None:
        self.assertFalse((ARCHIVE / "exchange_terminal_services" / "__init__.py").exists())


if __name__ == "__main__":
    unittest.main()
