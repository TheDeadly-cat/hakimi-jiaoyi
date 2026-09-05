from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

import quant_bot
from hakimi_research.product_capabilities import build_product_capability_catalog
from quant_bot import execution
from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig


class ArchivedPaperExecutionSourceBoundaryV1Tests(unittest.TestCase):
    ARCHIVED_HASHES = {
        "execution_with_paper_broker.py": "f1399e616f761475e4a17a6908c7732088e2e1e28519d43c3c9f58e14962d14e",
        "engine.py": "a896c07c1037ebac4dc745a0a1aeb0a986149f078343930342d2f53572ec2d2a",
        "tests/test_quant_bot_engine_decision_reservation_v1.py": "aa221d62e7e881a48987a2870309a9a55e61c3832d4676b69aff7776b2d047fb",
        "tests/test_quant_bot_broker_selector_fail_closed_v1.py": "fa45a162cd307dcc0b86846359b38e55e1f6bbeeeca3c8a62e13e6b111ef6010",
    }

    def test_legacy_sources_and_tests_are_preserved_outside_formal_tree(self) -> None:
        archive = REPOSITORY_ROOT / "archive" / "legacy_paper"
        for relative, expected_hash in self.ARCHIVED_HASHES.items():
            with self.subTest(relative=relative):
                path = archive / relative
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)

    def test_formal_package_exposes_no_legacy_paper_engine_or_broker(self) -> None:
        self.assertFalse((PROJECT_ROOT / "quant_bot" / "engine.py").exists())
        self.assertNotIn("engine", quant_bot.__all__)
        for name in ("BrokerBase", "PaperBroker", "build_broker"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(execution, name))
        self.assertTrue(hasattr(execution, "ResearchExecutionSimulator"))

    def test_canonical_cli_does_not_construct_a_broker(self) -> None:
        source = (REPOSITORY_ROOT / "src" / "hakimi_research" / "cli.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("build_broker", source)
        self.assertNotIn("with_broker", source)
        self.assertNotIn("TradingEngine", source)

    def test_backtest_engine_rejects_archived_execution_authority(self) -> None:
        for mode, broker, enabled in (
            ("paper", "research_simulator", False),
            ("live", "research_simulator", False),
            ("backtest", "ccxt", False),
            ("backtest", "paper", False),
            ("backtest", "research_simulator", True),
        ):
            with self.subTest(mode=mode, broker=broker, enabled=enabled):
                config = BotConfig()
                config.mode = mode
                config.execution.broker = broker
                config.execution.live_trading_enabled = enabled
                with self.assertRaisesRegex(ValueError, "exact backtest-only"):
                    BacktestEngine(config, object(), object())

    def test_product_catalog_keeps_paper_execution_archived(self) -> None:
        catalog = build_product_capability_catalog().to_dict()
        self.assertEqual(catalog["capabilities"]["paper_execution"], "Archived")
        self.assertEqual(catalog["cli_commands"]["paper"], "Archived")
        self.assertFalse(catalog["authority"]["paper_allowed"])


if __name__ == "__main__":
    unittest.main()
