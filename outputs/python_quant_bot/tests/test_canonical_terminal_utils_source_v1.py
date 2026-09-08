from __future__ import annotations

import ast
import hashlib
import inspect
import math
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PATH = REPO_ROOT / "src" / "hakimi_research" / "terminal_utils.py"
LEGACY_PATH = PROJECT_ROOT / "exchange_terminal" / "utils.py"
ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0547_exchange_terminal_utils.py"
ORPHAN_ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0393_dual_signature_handoff.py"
activate_canonical_source()

from exchange_terminal import utils as legacy  # noqa: E402
from hakimi_research import terminal_utils as canonical  # noqa: E402


MIGRATED_SYMBOLS = (
    "TERMINAL_UTILS_SCHEMA_VERSION",
    "average",
    "choice",
    "clamp",
    "clean_json_value",
    "flag",
    "human_age_ms",
    "market_source_name",
    "now_ms",
    "pct",
    "recent_volatility",
    "safe_volume_ratio",
    "trend_score",
)


class CanonicalTerminalUtilsSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs(self) -> None:
        source = Path(inspect.getsourcefile(canonical.pct) or "").resolve()
        self.assertEqual(source, CANONICAL_PATH)
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(canonical.TERMINAL_UTILS_SCHEMA_VERSION, "terminal-utils-v1")

    def test_legacy_wrapper_reexports_identical_objects(self) -> None:
        for symbol in MIGRATED_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_legacy_wrapper_contains_no_definitions(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = [
            node for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertEqual(definitions, [])

    def test_every_active_consumer_imports_canonical_source_directly(self) -> None:
        paths = (
            REPO_ROOT / "src" / "hakimi_research" / "research_execution_rehearsal.py",
            PROJECT_ROOT / "exchange_terminal" / "server.py",
            PROJECT_ROOT / "exchange_terminal" / "research" / "stock_research.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu_quotes.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu_deep.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "stock_candles_io.py",
            REPO_ROOT / "src" / "hakimi_research" / "stock_candles.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8-sig")
                self.assertIn("from hakimi_research.terminal_utils import", source)
                self.assertNotIn("from exchange_terminal.utils import", source)

    def test_original_implementation_and_orphan_are_archived_exactly(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "a7887e88d1d3b47f0f98b6fbbece79b025215809e765bffff61b20921995ad02",
        )
        self.assertEqual(
            hashlib.sha256(ORPHAN_ARCHIVE_PATH.read_bytes()).hexdigest(),
            "c3568182be093993242c18dcc9099f59b6e18b1fe6a8d08a7c82790c83894ebf",
        )
        self.assertFalse((REPO_ROOT / "exchange_terminal").exists())

    def test_behavior_remains_deterministic_and_fail_soft(self) -> None:
        self.assertEqual(canonical.pct("1.5"), 1.5)
        self.assertEqual(canonical.pct(float("nan"), 7.0), 7.0)
        self.assertTrue(canonical.flag("yes"))
        self.assertFalse(canonical.flag(None))
        self.assertEqual(canonical.choice("a", {"A", "B"}, "B"), "A")
        self.assertEqual(canonical.average([]), 0.0)
        self.assertEqual(canonical.human_age_ms(1_000), "1秒")
        self.assertEqual(canonical.market_source_name("offline-seed"), "离线种子")
        self.assertIsNone(canonical.clean_json_value(float("inf")))
        self.assertTrue(math.isfinite(canonical.recent_volatility([])))
        self.assertEqual(canonical.trend_score([1.0] * 59), 0.0)


if __name__ == "__main__":
    unittest.main()
