from __future__ import annotations

import ast
import inspect
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.application import archived_paper_runtime as legacy
from hakimi_research import archived_paper_runtime as canonical
from hakimi_research.http_contract import archived_execution_route_state


class ArchivedPaperRuntimeFacadeV1Tests(unittest.TestCase):
    PUBLIC_NAMES = (
        "ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION",
        "LEGACY_ORDER_TYPES",
        "ArchivedPaperAccount",
        "ArchivedPaperExecutor",
        "ArchivedPaperLedger",
        "ArchivedPortfolioPaperLedger",
        "build_archived_paper_runtime",
    )

    def test_canonical_source_and_legacy_identity(self) -> None:
        expected = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "archived_paper_runtime.py"
        ).resolve()
        actual = Path(inspect.getsourcefile(canonical.build_archived_paper_runtime) or "").resolve()
        self.assertEqual(actual, expected)
        self.assertNotIn("outputs", actual.parts)
        for name in self.PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy, name), getattr(canonical, name))

    def test_facade_readers_are_static_and_authority_free(self) -> None:
        account, ledger, executor, portfolio, reconciliation = (
            canonical.build_archived_paper_runtime()
        )
        first = account.snapshot(123.45)
        second = account.snapshot(123.45)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "ARCHIVED")
        self.assertEqual(first["mark_price"], 123.45)
        self.assertFalse(first["armed"])
        self.assertFalse(first["paper_authorized"])
        self.assertFalse(first["live_order_allowed"])
        self.assertEqual(first["orders"], [])
        self.assertEqual(ledger.summary()["backend"], "ARCHIVED_STATIC")
        self.assertEqual(ledger.load_lifecycle_orders(100), [])
        self.assertEqual(executor.list(100), [])
        self.assertEqual(executor.snapshot()["status"], "ARCHIVED")
        self.assertFalse(portfolio.mark_to_market()["simulation_enabled"])
        self.assertEqual(portfolio.mark_to_market()["positions"], [])
        self.assertEqual(reconciliation["status"], "ARCHIVED")

    def test_every_facade_write_path_fails_closed(self) -> None:
        account, ledger, executor, portfolio, _ = canonical.build_archived_paper_runtime()
        calls = (
            lambda: account.process_strategy_bars([]),
            lambda: ledger.save_account({}, "test", []),
            lambda: ledger.record_lifecycle_order({}),
            lambda: executor.submit({}),
            lambda: portfolio.initialize(0.0),
        )
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(RuntimeError, "archived and permanently disabled"):
                    call()

    def test_server_source_has_no_paper_persistence_construction(self) -> None:
        source = (PROJECT_ROOT / "exchange_terminal" / "server.py").read_text(
            encoding="utf-8"
        )
        forbidden = (
            "services.paper_account import",
            "services.paper_executor import",
            "services.paper_ledger import",
            "services.portfolio_paper_account import",
            "PaperAccount(",
            "PaperExecutor(",
            "PaperLedger(",
            "PortfolioPaperLedger(",
            "configure_paper_account_runtime(",
            "LEGACY_PAPER_STATE",
            "read_json(STATE_FILE",
            "simulated_execution_report(",
            'if path == "/api/order/estimate"',
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        self.assertIn("build_archived_paper_runtime()", source)

    def test_order_estimate_is_part_of_the_archived_execution_wall(self) -> None:
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual(
                    archived_execution_route_state(method, "/api/order/estimate"),
                    "BLOCK",
                )

    def test_legacy_shim_defines_no_functions_or_classes(self) -> None:
        path = (
            PROJECT_ROOT
            / "exchange_terminal"
            / "application"
            / "archived_paper_runtime.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        self.assertEqual(definitions, [])


if __name__ == "__main__":
    unittest.main()
