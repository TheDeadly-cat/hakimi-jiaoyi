from __future__ import annotations

import ast
import hashlib
import inspect
import os
from pathlib import Path
import subprocess
import sys
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PATH = REPO_ROOT / "src" / "hakimi_research" / "terminal_config.py"
LEGACY_PATH = PROJECT_ROOT / "exchange_terminal" / "config.py"
ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0548_exchange_terminal_config.py"
os.environ.setdefault("HAKIMI_SKIP_LOCAL_AI_ENV", "1")
activate_canonical_source()

from exchange_terminal import config as legacy  # noqa: E402
from hakimi_research import terminal_config as canonical  # noqa: E402


class CanonicalTerminalConfigSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs_and_paths_are_preserved(self) -> None:
        source = Path(inspect.getsourcefile(canonical.load_local_ai_env) or "").resolve()
        self.assertEqual(source, CANONICAL_PATH)
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(canonical.TERMINAL_CONFIG_SCHEMA_VERSION, "terminal-config-v1")
        self.assertEqual(canonical.ROOT_DIR, PROJECT_ROOT / "exchange_terminal")
        self.assertEqual(canonical.PROJECT_DIR, PROJECT_ROOT)
        self.assertEqual(canonical.STATIC_DIR, PROJECT_ROOT / "exchange_terminal" / "static")

    def test_legacy_wrapper_reexports_every_public_object(self) -> None:
        self.assertEqual(legacy.__all__, canonical.__all__)
        for symbol in canonical.__all__:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_legacy_wrapper_contains_no_definitions(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = [
            node for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertEqual(definitions, [])

    def test_active_consumers_import_canonical_source_directly(self) -> None:
        paths = (
            PROJECT_ROOT / "exchange_terminal" / "server.py",
            PROJECT_ROOT / "exchange_terminal" / "research" / "stock_research.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu_deep.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "okx.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "futu_quotes.py",
            PROJECT_ROOT / "exchange_terminal" / "market_data" / "stock_candles_io.py",
            REPO_ROOT / "src" / "hakimi_research" / "stock_metadata.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8-sig")
                self.assertIn("from hakimi_research.terminal_config import", source)
                self.assertNotIn("from exchange_terminal.config import", source)

    def test_original_implementation_is_archived_byte_identically(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "13c6b13447cf17760678170f6c7934f20da7b58eceffc0ba006b4115676a41f4",
        )

    def test_fresh_process_default_import_never_checks_local_env_path(self) -> None:
        environment = os.environ.copy()
        for name in (
            "HAKIMI_LOAD_LOCAL_AI_ENV",
            "HAKIMI_SKIP_LOCAL_AI_ENV",
            "HAKIMI_RUNTIME_READ_ONLY",
            "HAKIMI_TEST_MODE",
        ):
            environment.pop(name, None)
        environment["PYTHONPATH"] = str(REPO_ROOT / "src")
        script = (
            "from pathlib import Path;"
            "Path.is_file=lambda self:(_ for _ in ()).throw(AssertionError('path inspected'));"
            "import hakimi_research.terminal_config as c;"
            "assert c.LIVE_TRADING_HARD_BLOCK is True;"
            "print('DEFAULT_NO_ENV_READ_PASS')"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "DEFAULT_NO_ENV_READ_PASS")


if __name__ == "__main__":
    unittest.main()
