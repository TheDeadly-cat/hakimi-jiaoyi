from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
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
from quant_bot import config as config_module
from quant_bot.config import BotConfig


class ArchivedOptimizerSourceBoundaryV1Tests(unittest.TestCase):
    ARCHIVE_SHA256 = "fafb2a18deaf71f1f598bdf7205ce4e0a14fff7c42ac7320edc70de951c4337a"

    def test_original_implementation_is_preserved_outside_formal_source(self) -> None:
        archived = REPOSITORY_ROOT / "archive" / "legacy_optimizer" / "optimizer.py"
        formal = PROJECT_ROOT / "quant_bot" / "optimizer.py"
        self.assertTrue(archived.is_file())
        self.assertFalse(formal.exists())
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(), self.ARCHIVE_SHA256)

    def test_formal_package_exposes_no_optimizer_module_or_config_type(self) -> None:
        self.assertNotIn("optimizer", quant_bot.__all__)
        self.assertIsNone(importlib.util.find_spec("quant_bot.optimizer"))
        self.assertFalse(hasattr(config_module, "OptimizerConfig"))
        self.assertNotIn("optimizer", BotConfig.__dataclass_fields__)

    def test_product_catalog_keeps_parameter_optimization_archived(self) -> None:
        catalog = build_product_capability_catalog().to_dict()
        self.assertEqual(catalog["capabilities"]["parameter_optimization"], "Archived")
        self.assertEqual(catalog["cli_commands"]["optimize"], "Archived")

    def test_optimizer_configuration_is_rejected_explicitly(self) -> None:
        for payload in (
            {"mode": "optimize"},
            {"mode": "backtest", "optimizer": {}},
            {"mode": "backtest", "optimizer": {"metric": "sharpe_ratio"}},
        ):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "config.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "archived and permanently disabled"):
                    BotConfig.from_file(path)

    def test_backtest_configuration_without_optimizer_remains_loadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text('{"mode":"backtest"}', encoding="utf-8")
            config = BotConfig.from_file(path)
        self.assertEqual(config.mode, "backtest")
        self.assertFalse(hasattr(config, "optimizer"))


if __name__ == "__main__":
    unittest.main()
