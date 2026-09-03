from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importing configuration is itself part of the contract under test: it must
# never inspect a local credential file in the isolated test process.
os.environ.setdefault("HAKIMI_SKIP_LOCAL_AI_ENV", "1")

from exchange_terminal import config


class ConfigSafetyTests(unittest.TestCase):
    def test_isolated_modes_return_before_any_local_env_path_access(self) -> None:
        protected_names = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "GPT_MODEL")
        before = {name: os.environ.get(name) for name in protected_names}
        isolated_modes = (
            {"HAKIMI_LOAD_LOCAL_AI_ENV": "1", "HAKIMI_SKIP_LOCAL_AI_ENV": "1", "HAKIMI_RUNTIME_READ_ONLY": "0", "HAKIMI_TEST_MODE": "0"},
            {"HAKIMI_LOAD_LOCAL_AI_ENV": "1", "HAKIMI_SKIP_LOCAL_AI_ENV": "0", "HAKIMI_RUNTIME_READ_ONLY": "1", "HAKIMI_TEST_MODE": "0"},
            {"HAKIMI_LOAD_LOCAL_AI_ENV": "1", "HAKIMI_SKIP_LOCAL_AI_ENV": "0", "HAKIMI_RUNTIME_READ_ONLY": "0", "HAKIMI_TEST_MODE": "1"},
        )

        for environment in isolated_modes:
            with self.subTest(environment=environment):
                with (
                    patch.dict(os.environ, environment, clear=False),
                    patch.object(Path, "is_file", side_effect=AssertionError("local env path was inspected")),
                    patch.object(Path, "read_text", side_effect=AssertionError("local env file was read")),
                ):
                    config.load_local_ai_env()

        self.assertEqual({name: os.environ.get(name) for name in protected_names}, before)

    def test_default_import_policy_returns_before_local_env_path_access(self) -> None:
        with (
            patch.dict(os.environ, {"HAKIMI_LOAD_LOCAL_AI_ENV": "0"}, clear=True),
            patch.object(Path, "is_file", side_effect=AssertionError("local env path was inspected")),
            patch.object(Path, "read_text", side_effect=AssertionError("local env file was read")),
        ):
            self.assertFalse(config.load_local_ai_env())

    def test_explicit_opt_in_loads_only_allowlisted_mock_values(self) -> None:
        mock_document = (
            "OPENAI_MODEL=test-model\n"
            "IGNORED_SECRET=must-not-load\n"
        )
        with (
            patch.dict(os.environ, {"HAKIMI_LOAD_LOCAL_AI_ENV": "1"}, clear=True),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "read_text", return_value=mock_document),
        ):
            self.assertTrue(config.load_local_ai_env())
            self.assertEqual(os.environ.get("OPENAI_MODEL"), "test-model")
            self.assertNotIn("IGNORED_SECRET", os.environ)

    def test_external_environment_cannot_disable_live_trading_hard_block(self) -> None:
        environment = os.environ.copy()
        environment.update({
            "HAKIMI_SKIP_LOCAL_AI_ENV": "1",
            "HAKIMI_TEST_MODE": "1",
            "LIVE_TRADING_HARD_BLOCK": "false",
        })
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from exchange_terminal import config; "
                    "assert config.LIVE_TRADING_HARD_BLOCK is True; "
                    "print('LIVE_HARD_BLOCK_PASS')"
                ),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "LIVE_HARD_BLOCK_PASS")


if __name__ == "__main__":
    unittest.main()
