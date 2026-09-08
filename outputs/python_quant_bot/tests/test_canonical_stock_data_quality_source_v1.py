from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from _canonical_source import activate_canonical_source

activate_canonical_source()

from tests._stock_schedule_fixture import build_stock_schedule_fixture
import hakimi_research.stock_candle_quality as canonical_candle
import hakimi_research.stock_data_quality as canonical_boundary
import hakimi_research.stock_metadata as canonical_metadata
import hakimi_research.stock_quote_quality as canonical_quote
import hakimi_research.stock_session as canonical_session
from exchange_terminal.market_data import stock_candle_quality as legacy_candle
from exchange_terminal.market_data import stock_quote_quality as legacy_quote
from exchange_terminal.market_data import stock_session as legacy_session
from exchange_terminal.market_data import stocks as legacy_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
WORKFLOW_SOURCE = REPOSITORY_ROOT / ".github" / "workflows" / "research-contracts.yml"

CANONICAL_MODULES = {
    "stock_data_quality": canonical_boundary,
    "stock_metadata": canonical_metadata,
    "stock_session": canonical_session,
    "stock_candle_quality": canonical_candle,
    "stock_quote_quality": canonical_quote,
}
LEGACY_MODULES = {
    "stocks": legacy_metadata,
    "stock_session": legacy_session,
    "stock_candle_quality": legacy_candle,
    "stock_quote_quality": legacy_quote,
}
ARCHIVE_HASHES = {
    "adr0550_exchange_terminal_stocks.py": "9774debac062c8880ea7034a63d9b55b0a98bf805c741e082335f0c5767e1d5d",
    "adr0550_exchange_terminal_stock_session.py": "7d7b556211415bf938f5619e432969430df875d5bddfe5905075086db6c3a277",
    "adr0550_exchange_terminal_stock_candle_quality.py": "78137f385ad885f01ed85ded09d3173df1d2b27ce868481a00903405d185d5b7",
    "adr0550_exchange_terminal_stock_quote_quality.py": "d3c8141656f8103d9dbd8a72ea0578fba4c4888b623bd83e7ac15d84803c1628",
    "adr0558_stock_session_v1.py": "da0bd7f3a01e02c9fb6e13d79ab23f1f86f9326db2706faeb5efec36e01e026b",
    "adr0558_stock_candle_quality_v1.py": "5514f18ae9f1ea3bde0b93546511613d63b19d021b7accce2b42835a6faf8c05",
    "adr0558_stock_quote_quality_v1.py": "c3b5fc397ba02d88eae1d099eda7bb088c8cf470d154734e894655193488feb6",
    "adr0559_stock_candle_quality_v2.py": "fb1b0f194b05577a22bb4b979fff1382de15dff81a9bf32704862194e1eca675",
    "adr0587_stock_data_quality_boundary_v2.py": "be0e836598c84972cfa538f7f9f4b2dce6ab697ed384b51e13bbbdea8eb968c2",
    "adr0587_stock_candle_quality_v4.py": "4ccd9d7bb71d06c2121be8b93926c0e632722e416d58e7de70256ac7468af1a5",
    "adr0588_stock_candle_quality_v5.py": "fe24582f7771e1384b31dfc571d46dd8e1561adc4e950bf029fcd15b27ed03cb",
    "adr0589_stock_quote_quality_v3.py": "a2ea01edb2ce18bb65860c9635708e667209238c9633e97968dc64f743612135",
}
CONSUMERS = {
    "exchange_terminal/server.py": (
        "hakimi_research.stock_metadata",
        "hakimi_research.stock_session",
        "hakimi_research.stock_candle_quality",
        "hakimi_research.stock_quote_quality",
    ),
    "exchange_terminal/market_data/futu.py": (
        "hakimi_research.stock_metadata",
        "hakimi_research.stock_session",
    ),
    "exchange_terminal/market_data/futu_quotes.py": ("hakimi_research.stock_metadata",),
    "exchange_terminal/market_data/futu_deep.py": ("hakimi_research.stock_metadata",),
    "../../src/hakimi_research/stock_candles.py": ("hakimi_research.stock_metadata",),
    "exchange_terminal/market_data/stock_candles_io.py": ("hakimi_research.stock_metadata",),
    "exchange_terminal/research/stock_research.py": (
        "hakimi_research.stock_metadata",
        "hakimi_research.stock_candle_quality",
    ),
    "exchange_terminal/services/corporate_action_ledger.py": ("hakimi_research.stock_candle_quality",),
}


class CanonicalStockDataQualitySourceV1Tests(unittest.TestCase):
    def test_canonical_sources_are_versioned_and_outside_outputs(self) -> None:
        self.assertEqual(
            canonical_boundary.STOCK_DATA_QUALITY_BOUNDARY_VERSION,
            "stock-data-quality-boundary-v3",
        )
        versions = {
            canonical_metadata.STOCK_METADATA_CONTRACT_VERSION,
            canonical_session.STOCK_SESSION_CONTRACT_VERSION,
            canonical_candle.STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
            canonical_quote.STOCK_QUOTE_QUALITY_CONTRACT_VERSION,
        }
        self.assertEqual(
            versions,
            {"stock-metadata-v1", "stock-session-v3", "stock-candle-quality-v6", "stock-quote-quality-v4"},
        )
        for name in CANONICAL_MODULES:
            source = REPOSITORY_ROOT / "src" / "hakimi_research" / f"{name}.py"
            self.assertTrue(source.is_file(), name)
            self.assertNotIn("outputs", source.parts)

    def test_original_sources_are_archived_byte_identically(self) -> None:
        archive_root = REPOSITORY_ROOT / "archive" / "historical_research"
        for name, expected_hash in ARCHIVE_HASHES.items():
            self.assertEqual(hashlib.sha256((archive_root / name).read_bytes()).hexdigest(), expected_hash, name)

    def test_legacy_wrappers_have_no_definitions_and_reexport_identical_objects(self) -> None:
        target_names = {
            "stocks": "stock_metadata",
            "stock_session": "stock_session",
            "stock_candle_quality": "stock_candle_quality",
            "stock_quote_quality": "stock_quote_quality",
        }
        for legacy_name, canonical_name in target_names.items():
            source = PROJECT_ROOT / "exchange_terminal" / "market_data" / f"{legacy_name}.py"
            tree = ast.parse(source.read_text(encoding="utf-8"))
            definitions = tuple(
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
            )
            self.assertEqual(definitions, (), legacy_name)
            legacy = LEGACY_MODULES[legacy_name]
            canonical = CANONICAL_MODULES[canonical_name]
            self.assertEqual(legacy.__all__, canonical.__all__)
            for public_name in canonical.__all__:
                self.assertIs(getattr(legacy, public_name), getattr(canonical, public_name), public_name)

    def test_active_consumers_import_only_canonical_quality_sources(self) -> None:
        forbidden = (
            "market_data.stocks import",
            "market_data.stock_session import",
            "market_data.stock_candle_quality import",
            "market_data.stock_quote_quality import",
        )
        for relative_path, modules in CONSUMERS.items():
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            for module in modules:
                self.assertIn(f"from {module} import", source, relative_path)
            for fragment in forbidden:
                self.assertNotIn(fragment, source, relative_path)

    def test_non_native_values_fail_before_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapNumber:
            def __float__(self) -> float:
                calls.append("number.__float__")
                return 100.0

        class TrapText(str):
            def upper(self) -> str:
                calls.append("text.upper")
                return "AAPL"

            def __str__(self) -> str:
                calls.append("text.__str__")
                return "futu"

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return TrapNumber()

            def items(self):
                calls.append("dict.items")
                return (("status", "PASS"),)

        self.assertFalse(canonical_metadata.is_stock_symbol(TrapText("AAPL")))
        candle = canonical_candle.analyze_stock_candle_series(
            [{"close": TrapNumber()}],
            symbol="AAPL",
            interval="1d",
            source="futu",
        )
        self.assertEqual(candle["status"], "BLOCK")
        self.assertEqual(candle["total_rows"], 0)
        public = canonical_candle.stock_candle_quality_public(TrapDict())
        self.assertEqual(public["status"], "BLOCK")
        quote = canonical_quote.normalize_stock_quote_quality({"source": TrapText("futu"), "last": TrapNumber()})
        self.assertEqual(quote["quote_quality"]["status"], "REVIEW")
        sessions = canonical_session.normalize_stock_session_prices({"last": TrapNumber()})
        self.assertFalse(sessions["regular"]["available"])
        contract = canonical_session.build_stock_session_contract("AAPL", TrapDict(), now_ms_value=0)
        self.assertFalse(contract["execution_eligible"])
        self.assertEqual(calls, [])

    def test_native_quality_statuses_are_neutral_and_non_authorizing(self) -> None:
        rows = [{
            "ts": 1_700_000_000_000,
            "date": "2023-11-14",
            "open": 99,
            "high": 101,
            "low": 98,
            "close": 100,
            "volume": 1_000,
            "complete": True,
            "source": "futu",
        }]
        candle = canonical_candle.analyze_stock_candle_series(
            rows,
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=build_stock_schedule_fixture(rows),
        )
        quote = canonical_quote.normalize_stock_quote_quality(
            {
                "source": "futu",
                "last": 100,
                "open24h": 99,
                "high24h": 101,
                "low24h": 90,
                "bidPx": 99.9,
                "askPx": 100.1,
                "ts": 1_700_000_000_000,
            },
            previous_close=100,
            change_basis="previous_close",
            now_ms=1_700_000_000_500,
        )
        session = canonical_session.build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100, "ts": 1_700_000_000_000, "sec_status": "NORMAL"},
            market_state="MORNING",
            now_ms_value=1_700_000_000_500,
        )
        self.assertEqual(candle["status"], "PASS")
        self.assertEqual(quote["quote_quality"]["status"], "PASS")
        self.assertFalse(session["execution_eligible"])
        self.assertFalse(session["execution_authority"])
        self.assertTrue(all(value is False for value in candle["authority"].values()))
        self.assertTrue(
            all(value is False for value in quote["quote_quality"]["authority"].values())
        )
        self.assertEqual(session["safe_action"], "SOURCE -> GAP -> MATURITY -> PERMISSION")

    def test_session_source_depends_only_on_canonical_metadata(self) -> None:
        source = (REPOSITORY_ROOT / "src" / "hakimi_research" / "stock_session.py").read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.stock_metadata import", source)
        self.assertIn("from hakimi_research.stock_data_quality import", source)
        self.assertNotIn("exchange_terminal", source)
        self.assertNotIn("market_data.stocks", source)

    def test_structure_quality_is_consumed_before_research_or_backtest_use(self) -> None:
        consumers = {
            "exchange_terminal/research/stock_research.py": "candle_quality.get(\"structure_complete\") is not True",
            "exchange_terminal/server.py": "candle_quality.get(\"structure_complete\") is not True",
            "exchange_terminal/services/corporate_action_ledger.py": "quality.get(\"structure_complete\") is not True",
        }
        for relative_path, expected in consumers.items():
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(expected, source, relative_path)
            self.assertIn("temporal_conformance_complete", source, relative_path)

    def test_root_research_workflow_runs_this_contract(self) -> None:
        workflow = WORKFLOW_SOURCE.read_text(encoding="utf-8")
        self.assertIn("tests.test_canonical_stock_data_quality_source_v1", workflow)


if __name__ == "__main__":
    unittest.main()
