from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from _canonical_source import activate_canonical_source

activate_canonical_source()

import hakimi_research.candle_contract as canonical
from exchange_terminal.market_data import candle_contract as legacy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
CANONICAL_SOURCE = REPOSITORY_ROOT / "src" / "hakimi_research" / "candle_contract.py"
LEGACY_SOURCE = PROJECT_ROOT / "exchange_terminal" / "market_data" / "candle_contract.py"
ARCHIVED_SOURCE = REPOSITORY_ROOT / "archive" / "historical_research" / "adr0549_exchange_terminal_candle_contract.py"
WORKFLOW_SOURCE = REPOSITORY_ROOT / ".github" / "workflows" / "research-contracts.yml"
ORIGINAL_SOURCE_SHA256 = "add2f0ab6f18ff122ba1dc04db13ab3def87dc7ff747d519ee04a20d0e89e671"

ACTIVE_CONSUMERS = (
    "../../src/hakimi_research/stock_candles.py",
    "exchange_terminal/market_data/stock_candles_io.py",
    "exchange_terminal/services/backtest_engine.py",
    "exchange_terminal/services/market_data_revision_ledger.py",
    "exchange_terminal/services/market_regime.py",
    "exchange_terminal/services/market_history_store.py",
    "exchange_terminal/services/portfolio_backtest.py",
    "exchange_terminal/services/portfolio_backtest_replay.py",
    "exchange_terminal/services/portfolio_risk.py",
    "exchange_terminal/services/strategy_benchmark.py",
    "exchange_terminal/services/strategy_correlation_return_replay.py",
)


class CanonicalCandleContractSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_versioned_and_outside_outputs(self) -> None:
        self.assertTrue(CANONICAL_SOURCE.is_file())
        self.assertNotIn("outputs", CANONICAL_SOURCE.parts)
        self.assertEqual(
            canonical.CANDLE_COMPLETENESS_CONTRACT_VERSION,
            "candle-completeness-v1",
        )

    def test_original_implementation_is_archived_byte_identically(self) -> None:
        archived_bytes = ARCHIVED_SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(archived_bytes).hexdigest(), ORIGINAL_SOURCE_SHA256)

    def test_legacy_wrapper_contains_no_definitions(self) -> None:
        tree = ast.parse(LEGACY_SOURCE.read_text(encoding="utf-8"))
        definitions = tuple(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
        )
        self.assertEqual(definitions, ())

    def test_legacy_wrapper_reexports_identical_public_objects(self) -> None:
        self.assertEqual(legacy.__all__, canonical.__all__)
        for name in canonical.__all__:
            self.assertIs(getattr(legacy, name), getattr(canonical, name), name)

    def test_active_consumers_import_canonical_source_directly(self) -> None:
        for relative_path in ACTIVE_CONSUMERS:
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("from hakimi_research.candle_contract import", source, relative_path)
            self.assertNotIn("market_data.candle_contract import", source, relative_path)
            self.assertNotIn("from .candle_contract import", source, relative_path)

    def test_subclass_controlled_methods_are_rejected_before_invocation(self) -> None:
        calls: list[str] = []

        class ForgedStatus(str):
            def strip(self) -> str:
                calls.append("str.strip")
                return "complete"

        class ForgedRow(dict[str, object]):
            def __contains__(self, key: object) -> bool:
                calls.append("dict.__contains__")
                return True

            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return "complete"

        self.assertIsNone(canonical.explicit_boolean(ForgedStatus("incomplete")))
        self.assertFalse(canonical.candle_is_complete(ForgedRow()))
        self.assertEqual(calls, [])

    def test_native_behavior_and_non_boolean_default_remain_fail_closed(self) -> None:
        self.assertIs(canonical.explicit_boolean(" completed "), True)
        self.assertIs(canonical.explicit_boolean(" incomplete "), False)
        self.assertTrue(canonical.candle_is_complete({"confirmed": 1}))
        self.assertFalse(canonical.candle_is_complete({"confirmed": 0}))
        self.assertTrue(canonical.candle_is_complete({}, default_if_missing=True))
        self.assertFalse(canonical.candle_is_complete({}, default_if_missing=1))

    def test_root_research_workflow_runs_this_contract(self) -> None:
        workflow = WORKFLOW_SOURCE.read_text(encoding="utf-8")
        self.assertIn("tests.test_canonical_candle_contract_source_v1", workflow)


if __name__ == "__main__":
    unittest.main()
