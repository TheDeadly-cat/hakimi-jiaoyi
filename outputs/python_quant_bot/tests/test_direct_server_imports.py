from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PACKAGE_ROOT = PROJECT_ROOT / "exchange_terminal"


class DirectServerImportTests(unittest.TestCase):
    def test_services_import_when_server_runs_as_a_script(self) -> None:
        modules = [
            "services.backtest_engine",
            "services.market_data_revision_ledger",
            "services.market_regime",
            "services.portfolio_backtest",
            "services.portfolio_backtest_replay",
            "services.portfolio_risk",
            "services.strategy_benchmark",
            "services.strategy_data_admission",
            "services.strategy_matrix_protocol",
            "services.strategy_research_evidence",
        ]
        code = (
            "import importlib,sys;"
            f"sys.path.insert(0,{str(SERVER_PACKAGE_ROOT)!r});"
            f"[importlib.import_module(name) for name in {modules!r}]"
        )

        completed = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
