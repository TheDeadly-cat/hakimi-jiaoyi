"""Default startup and offline request boundaries, without production data."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import urllib.parse

SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"


class IntegratedLocalModeTests(unittest.TestCase):
    def test_default_configuration_and_market_import_do_not_create_runtime_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sentinel.bin").write_bytes(b"original")
            environment = os.environ.copy()
            environment.pop("HAKIMI_RUNTIME_READ_ONLY", None)
            environment.update(HAKIMI_RUNTIME_DIR=folder, HAKIMI_SKIP_LOCAL_AI_ENV="1", HAKIMI_TEST_MODE="1")
            result = subprocess.run([sys.executable, "-c", "from exchange_terminal import config; assert config.RUNTIME_READ_ONLY is True; from exchange_terminal.market_data import stock_candles_io; print('DEFAULT_READ_ONLY_OK')"],
                                    env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "DEFAULT_READ_ONLY_OK")
            self.assertEqual({p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}, {"sentinel.bin": b"original"})

    def test_local_mode_rejects_every_model_entry_before_calling_provider(self):
        handler = next(n for n in ast.parse(SERVER.read_text(encoding="utf-8")).body if isinstance(n, ast.ClassDef) and n.name == "ExchangeTerminalHandler")
        nodes = [n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name in {"do_POST", "handle_api"}]
        responses = []
        provider = Mock(side_effect=AssertionError("provider called in local mode"))
        scope = {"LOCAL_ONLY": True, "RUNTIME_READ_ONLY": True,
                 "RETIRED_MANAGEMENT_PATHS": set(), "MUTATION_PATHS": set(),
                 "POST_API_PATHS": {"/api/ai/deepseek/analyze", "/api/ai/market/dual-analysis", "/api/ai/trading-agents/discuss"},
                 "QUANT_WORKSPACE": SimpleNamespace(handle=lambda _: False),
                 "block_non_loopback_client": lambda _: False, "urllib": urllib,
                 "json_response": lambda _, body, status=200: responses.append((status, body)),
                 "deepseek_opportunity_scan": provider, "deepseek_platform_review": provider,
                 "deepseek_strategy_snapshot_analysis": provider, "market_dual_ai_analysis": provider}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SERVER), "exec"), scope)
        for path in scope["POST_API_PATHS"]:
            scope["do_POST"](SimpleNamespace(path=path))
        for path in ("/api/ai/deepseek/opportunities", "/api/ai/deepseek/platform-review"):
            scope["handle_api"](SimpleNamespace(), path, {})
        self.assertEqual(len(responses), 5)
        self.assertTrue(all(status == 423 and body["request_attempts"] == 0 for status, body in responses))
        provider.assert_not_called()
