from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PATH = REPO_ROOT / "src" / "hakimi_research" / "config.py"
LEGACY_PATH = PROJECT_ROOT / "quant_bot" / "config.py"
ACTIVE_CONFIG_PATH = REPO_ROOT / "configs" / "examples" / "btc_spot_1h.json"

activate_canonical_source()

from hakimi_research import config as canonical  # noqa: E402
from quant_bot import config as legacy  # noqa: E402


MIGRATED_SYMBOLS = (
    "CONFIG_SCHEMA_VERSION",
    "BotConfig",
    "DataConfig",
    "ExecutionConfig",
    "LoggingConfig",
    "RiskConfig",
    "StrategyConfig",
    "validate_research_config",
)


class CanonicalResearchConfigSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs(self) -> None:
        self.assertTrue(CANONICAL_PATH.is_file())
        self.assertNotIn("outputs", CANONICAL_PATH.relative_to(REPO_ROOT).parts)
        self.assertEqual(canonical.CONFIG_SCHEMA_VERSION, "research-config-v1")

    def test_legacy_module_reexports_identical_objects(self) -> None:
        for symbol in MIGRATED_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_active_consumers_import_canonical_config_directly(self) -> None:
        paths = (
            REPO_ROOT / "src" / "hakimi_research" / "backtest.py",
            REPO_ROOT / "src" / "hakimi_research" / "data.py",
            REPO_ROOT / "src" / "hakimi_research" / "risk.py",
            REPO_ROOT / "src" / "hakimi_research" / "experiment.py",
            REPO_ROOT / "src" / "hakimi_research" / "frozen_evaluation.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("hakimi_research.config", source)
                self.assertNotIn("from quant_bot.config", source)

    def test_legacy_module_contains_no_definitions(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        self.assertFalse(any(
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            for node in tree.body
        ))

    def test_safe_file_config_preserves_research_identity(self) -> None:
        raw = json.loads(ACTIVE_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(raw["mode"], "backtest")
        self.assertEqual(raw["data"]["provider"], "csv")
        self.assertFalse(raw["data"]["use_cache"])
        self.assertNotIn("broker", raw["execution"])
        self.assertNotIn("exchange", raw["execution"])
        self.assertNotIn("poll_seconds", raw["execution"])
        self.assertNotIn("live_trading_enabled", raw["execution"])
        self.assertEqual(raw["logging"]["log_dir"], "artifacts/logs")
        config = canonical.BotConfig.from_file(ACTIVE_CONFIG_PATH)
        self.assertEqual(config.execution.broker, "research_simulator")
        self.assertEqual(config.execution.exchange, "disabled")
        self.assertFalse(config.execution.live_trading_enabled)

    def test_archived_and_nonfinite_file_intent_is_rejected(self) -> None:
        payloads = (
            '{"mode":"paper"}',
            '{"mode":"live","execution":{"broker":"ccxt","live_trading_enabled":true}}',
            '{"mode":"optimize"}',
            '{"mode":"backtest","data":{"provider":"synthetic"}}',
            '{"mode":"backtest","initial_cash":NaN}',
            '{"mode":"backtest","execution":{"broker":"paper"}}',
            '{"mode":"backtest","execution":{"exchange":"okx"}}',
        )
        for index, payload in enumerate(payloads):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "config.json"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ValueError):
                    canonical.BotConfig.from_file(path)

    def test_direct_unsafe_construction_and_subclasses_fail_before_coercion(self) -> None:
        class EvilFloat(float):
            reached = False

            def __float__(self):
                type(self).reached = True
                raise AssertionError("hostile float reached")

        class EvilDict(dict):
            reached = False

            def items(self):
                type(self).reached = True
                return super().items()

        with self.assertRaisesRegex(ValueError, "mode_must_be_backtest"):
            canonical.BotConfig(mode="live")
        with self.assertRaisesRegex(ValueError, "broker_must_be_research_simulator"):
            canonical.ExecutionConfig(broker="paper")
        with self.assertRaisesRegex(ValueError, "initial_cash_exact_finite_number_required"):
            canonical.BotConfig(initial_cash=EvilFloat(10000.0))
        self.assertFalse(EvilFloat.reached)
        with self.assertRaisesRegex(ValueError, "params_exact_native_dict_required"):
            canonical.StrategyConfig(params=EvilDict({"fast_window": 5}))
        self.assertFalse(EvilDict.reached)

    def test_path_subclass_is_rejected_before_path_protocol(self) -> None:
        class EvilPath(str):
            reached = False

            def __fspath__(self):
                type(self).reached = True
                raise AssertionError("hostile path reached")

        with self.assertRaisesRegex(ValueError, "path_exact_native_required"):
            canonical.BotConfig.from_file(EvilPath(str(ACTIVE_CONFIG_PATH)))
        self.assertFalse(EvilPath.reached)


if __name__ == "__main__":
    unittest.main()
