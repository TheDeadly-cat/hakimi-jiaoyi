from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_requested_runtime = str(os.getenv("HAKIMI_TEST_RUNTIME_DIR") or "").strip()
_existing_runtime = str(os.getenv("HAKIMI_RUNTIME_DIR") or "").strip()
if _existing_runtime and os.getenv("HAKIMI_TEST_MODE") == "1":
    TEST_RUNTIME_DIR = Path(_existing_runtime).expanduser().resolve()
elif _requested_runtime:
    TEST_RUNTIME_DIR = Path(_requested_runtime).expanduser().resolve()
    TEST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
else:
    TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="hakimi-trade-tests-"))
    atexit.register(shutil.rmtree, TEST_RUNTIME_DIR, ignore_errors=True)

os.environ["HAKIMI_TEST_MODE"] = "1"
os.environ["HAKIMI_RUNTIME_DIR"] = str(TEST_RUNTIME_DIR)

from exchange_terminal import config


class RuntimeIsolationTests(unittest.TestCase):
    def test_test_suite_uses_an_ephemeral_runtime_root(self) -> None:
        production_runtime = (PROJECT_ROOT / "runtime").resolve()

        self.assertEqual(config.RUNTIME_DIR.resolve(), TEST_RUNTIME_DIR.resolve())
        self.assertNotEqual(config.RUNTIME_DIR.resolve(), production_runtime)

    def test_all_mutable_config_paths_stay_under_the_test_runtime(self) -> None:
        mutable_paths = (
            config.STATE_FILE,
            config.LEDGER_FILE,
            config.API_CONFIG_FILE,
            config.PROFILE_FILE,
            config.EXPORT_DIR,
            config.BTC_DAILY_DATA_DIR,
            config.BTC_DAILY_DB,
            config.BTC_DAILY_CSV,
            config.BTC_DAILY_DB_CACHE,
            config.MARKET_HISTORY_CACHE_DB,
            config.STOCK_CANDLE_CACHE_DB,
            config.CORPORATE_ACTION_DB,
            config.MARKET_DATA_REVISION_DB,
            config.PORTFOLIO_PAPER_DB,
            config.ANOMALY_EVENT_DB,
        )
        runtime = config.RUNTIME_DIR.resolve()

        for path in mutable_paths:
            with self.subTest(path=path):
                self.assertTrue(Path(path).resolve().is_relative_to(runtime))


if __name__ == "__main__":
    unittest.main()
