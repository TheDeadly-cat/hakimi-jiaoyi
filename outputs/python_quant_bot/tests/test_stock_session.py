from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.market_data.stock_session import build_stock_session_contract
from exchange_terminal.market_data.stocks import stock_timezone
from hakimi_research.market_calendar import build_market_schedule_attestation


def timestamp(symbol: str, value: str) -> int:
    local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=stock_timezone(symbol))
    return int(local.timestamp() * 1000)


def schedule(session_date: str) -> dict[str, object]:
    return build_market_schedule_attestation(
        calendar_name="XNYS",
        timezone_name="America/New_York",
        coverage_start=session_date,
        coverage_end=session_date,
        source_class="DETERMINISTIC_TEST_FIXTURE",
        source_name="stock-session-contract-test",
        source_version="1",
        sessions=[{
            "date": session_date,
            "open_utc": f"{session_date}T13:30:00+00:00",
            "close_utc": f"{session_date}T20:00:00+00:00",
            "early_close": False,
        }],
    )


class StockSessionContractTests(unittest.TestCase):
    def test_futu_after_hours_uses_post_price(self) -> None:
        now = timestamp("AAPL", "2026-07-31 17:09:30")
        result = build_stock_session_contract(
            "AAPL",
            {
                "source": "futu",
                "last": 308.91,
                "change24h_pct": -7.35,
                "after_price": 307.20,
                "after_change_rate": -0.553,
                "ts": now - 500,
                "sec_status": "NORMAL",
            },
            market_state="AFTER_HOURS_BEGIN",
            now_ms_value=now,
            schedule_attestation=schedule("2026-07-31"),
        )

        self.assertEqual(result["phase"], "post")
        self.assertEqual(result["status"], "LIVE_SESSION")
        self.assertEqual(result["active_session"], "post")
        self.assertAlmostEqual(result["active_price"], 307.20)
        self.assertFalse(result["execution_eligible"])

    def test_closed_futu_quote_is_last_session_not_stale(self) -> None:
        now = timestamp("AAPL", "2026-08-01 10:00:00")
        result = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 308.91, "ts": now - 14 * 60 * 60 * 1000},
            market_state="CLOSED",
            now_ms_value=now,
        )

        self.assertEqual(result["phase"], "closed")
        self.assertEqual(result["status"], "LAST_SESSION")
        self.assertTrue(result["analysis_ready"])
        self.assertFalse(result["is_open"])

    def test_external_source_is_marked_as_inferred(self) -> None:
        now = timestamp("AAPL", "2026-07-31 10:15:00")
        result = build_stock_session_contract(
            "AAPL",
            {"source": "yahoo", "last": 200, "ts": now - 30_000},
            now_ms_value=now,
            schedule_attestation=schedule("2026-07-31"),
        )

        self.assertEqual(result["phase"], "regular")
        self.assertEqual(result["status"], "DELAYED_SOURCE")
        self.assertFalse(result["provider_confirmed"])
        self.assertFalse(result["execution_eligible"])

    def test_regular_session_never_grants_execution_authority(self) -> None:
        now = timestamp("AAPL", "2026-07-31 11:00:00")
        result = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 205, "ts": now - 500, "sec_status": "NORMAL"},
            market_state="MORNING",
            now_ms_value=now,
            schedule_attestation=schedule("2026-07-31"),
        )

        self.assertEqual(result["status"], "LIVE_SESSION")
        self.assertTrue(result["regular_open"])
        self.assertFalse(result["execution_eligible"])
        self.assertFalse(result["execution_authority"])
        self.assertEqual(result["safe_action"], "SOURCE -> GAP -> MATURITY -> PERMISSION")


if __name__ == "__main__":
    unittest.main()
