from __future__ import annotations

import ast
import hashlib
import math
import sys
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research import indicators as canonical  # noqa: E402
from quant_bot import indicators as legacy  # noqa: E402


ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0534_indicators.py"
LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "indicators.py"
TEMPLATES_PATH = SRC_ROOT / "hakimi_research" / "strategies" / "templates.py"
DETERMINISTIC_PATH = SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"


class SeriesSubclass(pd.Series):
    pass


class HostileInt(int):
    pass


class CanonicalResearchIndicatorsSourceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.series = pd.Series(
            [100.0 + index for index in range(40)],
            index=pd.date_range("2026-01-01", periods=40, freq="h", tz="UTC"),
        )

    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(canonical.INDICATOR_SCHEMA_VERSION, "research-indicators-v1")
        for name in ("sma", "ema", "bollinger", "macd", "rsi", "momentum"):
            self.assertIs(getattr(legacy, name), getattr(canonical, name))

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_historical_implementation_is_byte_preserved(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "315f02e3858469b61e944f2aac09dca16a5689bec7449e11079131914907b2cc",
        )

    def test_templates_and_source_envelope_use_canonical_indicators(self) -> None:
        templates = TEMPLATES_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.indicators import", templates)
        self.assertNotIn("from quant_bot.indicators import", templates)
        deterministic = DETERMINISTIC_PATH.read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/indicators.py"', deterministic)
        self.assertNotIn('"outputs/python_quant_bot/quant_bot/indicators.py"', deterministic)

    def test_valid_outputs_preserve_index_and_do_not_alias_input(self) -> None:
        outputs = [
            canonical.sma(self.series, 5),
            canonical.ema(self.series, 5),
            *canonical.bollinger(self.series, 5, 2.0),
            *canonical.macd(self.series, 5, 20, 4),
            canonical.rsi(self.series, 14),
            canonical.momentum(self.series, 5),
        ]
        for output in outputs:
            self.assertIs(type(output), pd.Series)
            self.assertTrue(output.index.equals(self.series.index))
        first = outputs[0].copy(deep=True)
        self.series.iloc[-1] = 999.0
        pd.testing.assert_series_equal(outputs[0], first)

    def test_series_input_requires_exact_finite_numeric_ordered_data(self) -> None:
        invalid = []
        invalid.append(SeriesSubclass(self.series))
        nonfinite = self.series.copy()
        nonfinite.iloc[0] = math.nan
        invalid.append(nonfinite)
        infinite = self.series.copy()
        infinite.iloc[0] = math.inf
        invalid.append(infinite)
        invalid.append(self.series.iloc[::-1])
        duplicate = pd.concat([self.series.iloc[:1], self.series])
        invalid.append(duplicate)
        invalid.append(pd.Series(["1", "2"]))
        invalid.append(pd.Series(dtype="float64"))
        for series in invalid:
            with self.assertRaises(ValueError):
                canonical.sma(series, 2)

    def test_window_and_multiplier_domains_are_exact(self) -> None:
        invalid_windows = (0, -1, True, 1.5, "5", HostileInt(5))
        for window in invalid_windows:
            with self.assertRaises(ValueError):
                canonical.sma(self.series, window)  # type: ignore[arg-type]
        for multiplier in (0, -1, True, math.nan, math.inf, "2"):
            with self.assertRaises(ValueError):
                canonical.bollinger(self.series, 5, multiplier)  # type: ignore[arg-type]

    def test_macd_and_momentum_domains_are_explicit(self) -> None:
        with self.assertRaises(ValueError):
            canonical.macd(self.series, 20, 5, 4)
        with self.assertRaises(ValueError):
            canonical.macd(self.series, 5, 5, 4)
        with self.assertRaises(ValueError):
            canonical.macd(self.series, 5, 20, 0)
        with self.assertRaises(ValueError):
            canonical.momentum(self.series, 0)


if __name__ == "__main__":
    unittest.main()
