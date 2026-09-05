from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERVICES = ROOT / "outputs" / "python_quant_bot" / "exchange_terminal" / "services"
TESTS = ROOT / "outputs" / "python_quant_bot" / "tests"
ARCHIVE = ROOT / "archive" / "legacy_paper"
REMOVED_MODULES = {"paper_ledger", "portfolio_paper_account", "portfolio_paper_activation"}
EXPECTED_ARCHIVE_HASHES = {
    ARCHIVE / "exchange_terminal_services" / "paper_ledger.py": "b3380975818f4ab0f190f978cbed528e45903aca1c77168ac6510dd6362752a1",
    ARCHIVE / "exchange_terminal_services" / "portfolio_paper_account.py": "75bfdaa68b1407d1085a7867e4ed0c5383125bafce569d173e245e2c2a84fd06",
    ARCHIVE / "exchange_terminal_services" / "portfolio_paper_activation.py": "ec13b2ae1c5a9362bf810e9eb4917a14ed88117ef292e57907cc2566ac72f1fa",
    ARCHIVE / "tests" / "test_portfolio_paper_account.py": "5b2eb1952b990bf9524833a058995298b66e383363f1365fafcc1597636c870a",
    ARCHIVE / "tests" / "test_core_services_before_paper_persistence_archive.py": "3a1fd3c4cbb3d838c76b6a56baa4fdad967f49937453d75bf9bb7ffedb53feb3",
    ARCHIVE / "tests" / "test_runtime_sqlite_read_only_before_paper_persistence_archive.py": "2513b88af119786580d7f376eb0386a3174e45fbd8874e543e00d4429fa1fc57",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if alias.name.split(".")[-1] in REMOVED_MODULES)
        elif isinstance(node, ast.ImportFrom):
            tail = (node.module or "").split(".")[-1]
            if tail in REMOVED_MODULES:
                found.append(node.module or "")
            found.extend(alias.name for alias in node.names if alias.name in REMOVED_MODULES)
    return found


class ArchivedPaperPersistenceSourceV1Tests(unittest.TestCase):
    def test_formal_persistence_modules_and_dedicated_test_are_absent(self) -> None:
        for name in REMOVED_MODULES:
            self.assertFalse((SERVICES / f"{name}.py").exists(), name)
        self.assertFalse((TESTS / "test_portfolio_paper_account.py").exists())

    def test_archive_preserves_exact_bytes(self) -> None:
        for path, expected in EXPECTED_ARCHIVE_HASHES.items():
            self.assertTrue(path.is_file(), path)
            self.assertEqual(_sha256(path), expected, path)

    def test_formal_service_import_graph_has_no_persistence_edge(self) -> None:
        violations = {str(path.relative_to(ROOT)): _target_imports(path) for path in sorted(SERVICES.glob("*.py")) if _target_imports(path)}
        self.assertEqual(violations, {})

    def test_shared_core_test_no_longer_claims_paper_ledger_support(self) -> None:
        path = TESTS / "test_core_services.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("PaperLedger", names)
        self.assertEqual(_target_imports(path), [])

    def test_runtime_read_only_test_retains_non_paper_coverage_only(self) -> None:
        path = TESTS / "test_runtime_sqlite_read_only.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        methods = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertFalse(names & {"PaperExecutor", "PaperLedger", "PortfolioPaperLedger"})
        self.assertIn("test_all_runtime_ledgers_remain_byte_identical_in_read_only_mode", methods)
        self.assertIn("test_stock_candle_cache_read_does_not_initialize_or_mutate_schema", methods)
        self.assertNotIn("_create_legacy_paper_database", methods)
        self.assertEqual(_target_imports(path), [])

    def test_root_runner_has_no_archived_persistence_import_edges(self) -> None:
        path = ROOT / "outputs" / "python_quant_bot" / "run_internal_portfolio_research.py"
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "portfolio_paper_account_module",
            "portfolio_paper_activation_module",
            "paper_account_module",
            "paper_ledger_module",
            "paper_strategy_clock_module",
        ):
            self.assertNotIn(forbidden, source)

    def test_archive_is_review_only_while_research_rehearsal_is_canonical(self) -> None:
        self.assertFalse((ARCHIVE / "exchange_terminal_services" / "__init__.py").exists())
        self.assertTrue((ARCHIVE / "adr0524_paper_executor.py").is_file())
        self.assertTrue((ARCHIVE / "adr0524_paper_order_contract.py").is_file())
        self.assertTrue((ROOT / "src" / "hakimi_research" / "research_execution_rehearsal.py").is_file())
        self.assertTrue((ROOT / "src" / "hakimi_research" / "research_order_lifecycle_contract.py").is_file())
        self.assertTrue((SERVICES / "portfolio_execution_rehearsal.py").is_file())



class Adr0524ResearchExecutionArchiveBoundaryTests(unittest.TestCase):
    def test_old_executor_contract_and_identity_test_are_archive_only(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        quant_root = repo_root / "outputs" / "python_quant_bot"
        self.assertFalse((quant_root / "exchange_terminal" / "services" / "paper_executor.py").exists())
        self.assertFalse((quant_root / "exchange_terminal" / "services" / "paper_order_contract.py").exists())
        self.assertFalse((quant_root / "tests" / "test_paper_executor_risk_authorization_identity_v1.py").exists())

    def test_current_consumers_use_research_rehearsal_modules(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        quant_root = repo_root / "outputs" / "python_quant_bot"
        expectations = {
            quant_root / "exchange_terminal" / "services" / "portfolio_execution_rehearsal.py": (
                "hakimi_research.research_execution_rehearsal",
            ),
            quant_root / "run_internal_execution_rehearsal.py": (
                "_ADR0524_SRC_ROOT",
                "portfolio_execution_rehearsal",
            ),
            quant_root / "run_internal_portfolio_research.py": (
                "research_execution_rehearsal_module",
                "research_order_lifecycle_contract_module",
            ),
        }
        for path, required_tokens in expectations.items():
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("exchange_terminal.services.paper_executor", source)
            self.assertNotIn("exchange_terminal.services.paper_order_contract", source)
            for token in required_tokens:
                self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
