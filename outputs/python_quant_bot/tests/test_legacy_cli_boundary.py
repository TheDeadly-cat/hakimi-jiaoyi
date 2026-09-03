from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

import run_bot
from quant_bot.data import (
    OkxPublicDataProvider,
    SyntheticDataProvider,
    build_data_provider,
)


class LegacyCliBoundaryTests(unittest.TestCase):
    def args(self) -> argparse.Namespace:
        return argparse.Namespace(config="config.example.json", cycles=1)

    def test_environment_cannot_enable_legacy_paper(self) -> None:
        with patch.dict(os.environ, {"HAKIMI_LEGACY_PAPER_ENABLED": "true"}), patch.object(
            run_bot, "load_stack", side_effect=AssertionError("stack must not load")
        ):
            with self.assertRaisesRegex(RuntimeError, "permanently disabled"):
                run_bot.command_paper(self.args())

    def test_environment_cannot_enable_legacy_optimize(self) -> None:
        with patch.dict(os.environ, {"HAKIMI_LEGACY_OPTIMIZE_ENABLED": "true"}), patch.object(
            run_bot, "load_stack", side_effect=AssertionError("stack must not load")
        ):
            with self.assertRaisesRegex(RuntimeError, "permanently disabled"):
                run_bot.command_optimize(self.args())

    def test_product_configuration_cannot_select_synthetic_data(self) -> None:
        config = SimpleNamespace(data=SimpleNamespace(
            provider="synthetic",
            cache_dir="unused",
            use_cache=False,
            csv_path="",
        ))
        with self.assertRaisesRegex(RuntimeError, "test-only"):
            build_data_provider(config)

    def test_partial_okx_history_fails_instead_of_returning_implicit_data(self) -> None:
        index = pd.date_range("2026-01-01", periods=2, freq="D", tz="UTC")
        partial = pd.DataFrame({
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.1, 1.2],
            "volume": [10.0, 11.0],
        }, index=index)
        provider = OkxPublicDataProvider(use_cache=False)
        with patch.object(provider, "_fetch_remote_history", return_value=partial):
            with self.assertRaisesRegex(RuntimeError, "Insufficient real OKX history"):
                provider.get_history("BTC-USDT", "1d", 3)

    def test_explicit_injected_synthetic_fallback_is_test_only(self) -> None:
        provider = OkxPublicDataProvider(fallback=SyntheticDataProvider(), use_cache=False)
        with patch.object(provider, "_fetch_remote_history", return_value=pd.DataFrame()):
            data = provider.get_history("BTC-USDT", "1d", 3)
        self.assertEqual(len(data), 3)

    def test_list_strategies_does_not_create_runtime_directory(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                with patch.object(sys, "argv", ["run_bot.py", "list-strategies"]), redirect_stdout(io.StringIO()):
                    run_bot.main()
                self.assertFalse((Path(temp_dir) / "runtime").exists())
            finally:
                os.chdir(previous)

    def test_capabilities_command_is_machine_readable_and_side_effect_free(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with patch.object(sys, "argv", ["run_bot.py", "capabilities"]), redirect_stdout(output):
                    run_bot.main()
                payload = json.loads(output.getvalue())
                self.assertEqual(payload["schema_version"], "product-capability-catalog-v1")
                self.assertEqual(payload["cli_commands"]["paper"], "Archived")
                self.assertEqual(payload["cli_commands"]["optimize"], "Archived")
                self.assertEqual(payload["cli_commands"]["frozen-benchmark"], "Supported")
                self.assertFalse((Path(temp_dir) / "runtime").exists())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
