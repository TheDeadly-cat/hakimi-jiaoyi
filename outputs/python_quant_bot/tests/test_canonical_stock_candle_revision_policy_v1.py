from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from _canonical_source import activate_canonical_source

activate_canonical_source()

import hakimi_research.stock_candle_revision_policy as canonical
from exchange_terminal.market_data import stock_candles_io
from exchange_terminal.services import corporate_action_ledger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
IO_SOURCE = PROJECT_ROOT / "exchange_terminal" / "market_data" / "stock_candles_io.py"
CORPORATE_SOURCE = PROJECT_ROOT / "exchange_terminal" / "services" / "corporate_action_ledger.py"
ARCHIVED_SOURCE = REPOSITORY_ROOT / "archive" / "historical_research" / "adr0552_exchange_terminal_stock_candles_io_pre_policy_split.py"
WORKFLOW_SOURCE = REPOSITORY_ROOT / ".github" / "workflows" / "research-contracts.yml"
ORIGINAL_IO_SHA256 = "d5c635c60910f0772789c3527cdb9cc22227c8540ec9841396a68019ffd315a6"


def row(date: str, close: float, source: str, *, complete: bool = True, volume: float = 10.0) -> dict[str, object]:
    return {
        "ts": 1_700_000_000_000 + int(date[-2:]) * 86_400_000,
        "date": date,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": volume,
        "complete": complete,
        "source": source,
        "session": "regular",
    }


class CanonicalStockCandleRevisionPolicyV1Tests(unittest.TestCase):
    def test_canonical_policy_is_versioned_and_outside_outputs(self) -> None:
        source = REPOSITORY_ROOT / "src" / "hakimi_research" / "stock_candle_revision_policy.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.parts)
        self.assertEqual(canonical.STOCK_CANDLE_REVISION_POLICY_VERSION, "stock-candle-revision-policy-v1")

    def test_pre_split_infrastructure_source_is_archived_byte_identically(self) -> None:
        self.assertEqual(hashlib.sha256(ARCHIVED_SOURCE.read_bytes()).hexdigest(), ORIGINAL_IO_SHA256)

    def test_infrastructure_defines_no_migrated_policy_functions(self) -> None:
        tree = ast.parse(IO_SOURCE.read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue({
            "_stock_candle_source_priority",
            "_series_adjustment_contract",
            "_canonical_adjusted_price",
        }.isdisjoint(names))
        source = IO_SOURCE.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.stock_candle_revision_policy import", source)
        self.assertIn("prepare_stock_candle_revision_policy(", source)

    def test_adjustment_basis_has_one_canonical_object(self) -> None:
        self.assertIs(corporate_action_ledger.infer_adjustment_basis, canonical.infer_adjustment_basis)
        self.assertIs(stock_candles_io.infer_adjustment_basis, canonical.infer_adjustment_basis)
        tree = ast.parse(CORPORATE_SOURCE.read_text(encoding="utf-8"))
        local = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "infer_adjustment_basis"
        ]
        self.assertEqual(local, [])

    def test_compatible_daily_vintages_chain_link_without_rewriting_frozen_overlap(self) -> None:
        incoming = [
            row("2026-01-02", 100.0, "futu"),
            row("2026-01-03", 110.0, "futu"),
        ]
        existing = [row("2026-01-02", 50.0, "yahoo_adjusted")]
        result = canonical.prepare_stock_candle_revision_policy(incoming, existing, "futu", "1d")
        self.assertTrue(result["chain_linked"])
        self.assertEqual(result["price_scale"], 0.5)
        self.assertEqual(result["anchor_date"], "2026-01-02")
        self.assertEqual(result["rows"][0]["close"], 50.0)
        self.assertEqual(result["rows"][1]["close"], 55.0)
        self.assertEqual(result["rows"][1]["volume"], 20.0)

    def test_provider_upgrade_and_incompatible_or_nonuniform_vintages_fail_closed(self) -> None:
        upgrade = canonical.prepare_stock_candle_revision_policy(
            [row("2026-01-02", 100.0, "futu")],
            [row("2026-01-01", 100.0, "stooq")],
            "futu",
            "1d",
        )
        self.assertTrue(upgrade["verified_provider_upgrade"])
        with self.assertRaisesRegex(ValueError, "daily_adjustment_basis_incompatible_with_cached_vintage"):
            canonical.prepare_stock_candle_revision_policy(
                [row("2026-01-02", 100.0, "yahoo")],
                [row("2026-01-01", 100.0, "stooq")],
                "yahoo",
                "1d",
            )
        with self.assertRaisesRegex(ValueError, "daily_adjustment_vintage_overlap_is_not_uniform"):
            canonical.prepare_stock_candle_revision_policy(
                [
                    row("2026-01-01", 100.0, "futu"),
                    row("2026-01-02", 100.0, "futu"),
                    row("2026-01-03", 100.0, "futu"),
                ],
                [
                    row("2026-01-01", 50.0, "yahoo_adjusted"),
                    row("2026-01-02", 80.0, "yahoo_adjusted"),
                ],
                "futu",
                "1d",
            )

    def test_non_native_values_fail_before_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapNumber:
            def __float__(self) -> float:
                calls.append("number.__float__")
                return 100.0

        class TrapText(str):
            def __str__(self) -> str:
                calls.append("text.__str__")
                return "futu"

            def strip(self) -> str:
                calls.append("text.strip")
                return self

        class TrapList(list[object]):
            def __iter__(self):
                calls.append("list.__iter__")
                return super().__iter__()

        result = canonical.prepare_stock_candle_revision_policy(
            TrapList([row("2026-01-01", 100.0, "futu")]),
            TrapList([]),
            TrapText("futu"),
            TrapText("1d"),
        )
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["source"], "")
        self.assertEqual(canonical.stock_candle_source_priority(TrapText("futu")), 0)
        self.assertEqual(canonical.infer_adjustment_basis(TrapText("futu"), TrapText("QFQ")), "UNKNOWN")
        self.assertEqual(canonical.series_adjustment_contract(TrapList(["futu"])), ("MIXED_UNVERIFIED", "UNKNOWN"))
        with self.assertRaisesRegex(ValueError, "adjusted_price_not_exact_native_finite"):
            canonical.canonical_adjusted_price(TrapNumber())
        self.assertEqual(calls, [])

    def test_adapter_rejects_non_native_rows_without_opening_database(self) -> None:
        calls: list[str] = []

        class TrapList(list[object]):
            def __iter__(self):
                calls.append("list.__iter__")
                return super().__iter__()

        original = stock_candles_io.ensure_stock_candle_cache_db
        stock_candles_io.ensure_stock_candle_cache_db = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("database opened"))
        try:
            result = stock_candles_io.prepare_stock_candle_cache_rows(
                "AAPL", "1d", "regular", TrapList([row("2026-01-01", 100.0, "futu")]), "futu"
            )
        finally:
            stock_candles_io.ensure_stock_candle_cache_db = original
        self.assertEqual(result["rows"], [])
        self.assertEqual(calls, [])

    def test_root_workflow_runs_this_contract(self) -> None:
        workflow = WORKFLOW_SOURCE.read_text(encoding="utf-8")
        self.assertIn("tests.test_canonical_stock_candle_revision_policy_v1", workflow)


if __name__ == "__main__":
    unittest.main()
