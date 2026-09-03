from __future__ import annotations

import ast
import hashlib
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.config import BotConfig  # noqa: E402
from hakimi_research.data import (  # noqa: E402
    MARKET_DATA_SCHEMA_VERSION,
    CsvDataProvider,
    OkxPublicDataProvider,
    SyntheticDataProvider,
    build_data_provider,
    market_data_fingerprint,
    okx_bar,
    validate_market_data_frame,
)
from quant_bot import data as legacy_data  # noqa: E402


ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0532_data.py"
LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "data.py"
CLI_PATH = SRC_ROOT / "hakimi_research" / "cli.py"


class HostileStr(str):
    pass


class CanonicalResearchDataSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(MARKET_DATA_SCHEMA_VERSION, "research-market-data-v1")
        for name in (
            "CsvDataProvider",
            "OkxPublicDataProvider",
            "SyntheticDataProvider",
            "build_data_provider",
            "okx_bar",
            "validate_market_data_frame",
            "market_data_fingerprint",
        ):
            self.assertIs(getattr(legacy_data, name), globals()[name])

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_historical_implementation_is_byte_preserved(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "a5d6a66ae22d547f978b30fd3fac8538092e0a7c7127d2a28e1d7c5e9b53e4a1",
        )

    def test_cli_imports_canonical_data_factory_directly(self) -> None:
        source = CLI_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.data import build_data_provider", source)
        self.assertNotIn("from quant_bot.data import", source)

    def test_factory_requires_exact_config_and_blocks_product_synthetic(self) -> None:
        fake = SimpleNamespace(data=SimpleNamespace(provider="csv", csv_path="fixture.csv"))
        with self.assertRaises(ValueError):
            build_data_provider(fake)  # type: ignore[arg-type]

        csv_config = BotConfig()
        csv_config.data.csv_path = "fixture.csv"
        self.assertIsInstance(build_data_provider(csv_config), CsvDataProvider)

        synthetic_config = BotConfig()
        synthetic_config.data.provider = "synthetic"
        with self.assertRaisesRegex(RuntimeError, "test-only"):
            build_data_provider(synthetic_config)

    def test_factory_constructs_inert_okx_provider_without_io(self) -> None:
        config = BotConfig()
        config.data.provider = "okx"
        config.data.cache_dir = ""
        config.data.use_cache = False
        self.assertIsInstance(build_data_provider(config), OkxPublicDataProvider)

    def test_csv_constructor_rejects_empty_and_subclass_paths(self) -> None:
        with self.assertRaises(ValueError):
            CsvDataProvider("")
        with self.assertRaises(ValueError):
            CsvDataProvider(HostileStr("fixture.csv"))
        self.assertEqual(CsvDataProvider("fixture.csv").csv_path, "fixture.csv")

    def test_synthetic_provider_is_fixed_and_repeatable(self) -> None:
        provider = SyntheticDataProvider()
        first = provider.get_history("SYNTH", "1h", 40)
        second = provider.get_history("SYNTH", "1h", 40)
        pd.testing.assert_frame_equal(first, second, check_exact=True)
        self.assertEqual(first.index[-1], pd.Timestamp("2024-01-01T00:00:00Z"))
        self.assertEqual(len(first), 40)
        self.assertTrue(first.index.is_unique)
        self.assertTrue(first.index.is_monotonic_increasing)

    def test_synthetic_request_gates_are_exact(self) -> None:
        provider = SyntheticDataProvider()
        invalid = (
            ("SYNTH", "1h", 0),
            ("SYNTH", "1h", -1),
            ("SYNTH", "1h", True),
            ("SYNTH", "1h", "40"),
            (HostileStr("SYNTH"), "1h", 40),
            ("SYNTH", HostileStr("1h"), 40),
            ("SYNTH", "unknown", 40),
        )
        for args in invalid:
            with self.assertRaises(ValueError):
                provider.get_history(*args)  # type: ignore[arg-type]

    def test_okx_timeframe_mapping_is_exact(self) -> None:
        self.assertEqual(okx_bar("1h"), "1H")
        with self.assertRaises(ValueError):
            okx_bar("unknown")
        with self.assertRaises(ValueError):
            okx_bar(HostileStr("1h"))

    def test_frame_validation_normalizes_utc_copy(self) -> None:
        source = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        validated = validate_market_data_frame(source)
        self.assertIsNot(validated, source)
        self.assertEqual(str(validated.index.tz), "UTC")
        source.iloc[0, 0] = -1.0
        self.assertGreater(validated.iloc[0, 0], 0.0)

    def test_frame_validation_rejects_quality_failures(self) -> None:
        valid = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        cases = []
        duplicate = pd.concat([valid.iloc[:1], valid])
        cases.append(duplicate)
        unordered = valid.iloc[::-1]
        cases.append(unordered)
        naive = valid.copy()
        naive.index = naive.index.tz_localize(None)
        cases.append(naive)
        nonfinite = valid.copy()
        nonfinite.iloc[0, 0] = math.nan
        cases.append(nonfinite)
        negative_volume = valid.copy()
        negative_volume.iloc[0, 4] = -1.0
        cases.append(negative_volume)
        invalid_high = valid.copy()
        invalid_high.iloc[0, 1] = invalid_high.iloc[0].iloc[[0, 3]].min() - 1.0
        cases.append(invalid_high)
        for frame in cases:
            with self.assertRaises(ValueError):
                validate_market_data_frame(frame)

    def test_market_data_fingerprint_is_stable_and_content_bound(self) -> None:
        first = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        second = first.copy(deep=True)
        self.assertEqual(market_data_fingerprint(first), market_data_fingerprint(second))
        second.iloc[0, 0] += 0.01
        self.assertNotEqual(market_data_fingerprint(first), market_data_fingerprint(second))


if __name__ == "__main__":
    unittest.main()
