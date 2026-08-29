from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import unittest

from exchange_terminal.services.backtest_engine import (
    CHECKPOINT_RATIO_CONTRACT_VERSION,
    causal_prefix_invariance_check,
)


def contract_rows(count: int = 12) -> list[dict[str, object]]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    for index in range(count):
        stamp = start + timedelta(days=index)
        rows.append({
            "date": stamp.date().isoformat(),
            "ts_ms": int(stamp.timestamp() * 1000),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1_000.0,
            "complete": True,
        })
    return rows


class BacktestCheckpointRatioContractV1Tests(unittest.TestCase):
    @staticmethod
    def _run(checkpoint_ratios, *, signal_factory=None, rows=None):
        factory = signal_factory or (
            lambda _rows: (
                lambda *_args: {"action": "HOLD", "reason": "contract fixture"}
            )
        )
        return causal_prefix_invariance_check(
            rows=contract_rows() if rows is None else rows,
            symbol="BTC-USDT",
            source="contract-fixture",
            signal_factory=factory,
            position_pct=10.0,
            take_profit_pct=0.0,
            stop_loss_pct=0.0,
            startup_candles=2,
            market="crypto",
            timeframe="1D",
            checkpoint_ratios=checkpoint_ratios,
        )

    def test_invalid_container_blocks_before_data_or_strategy_use(self) -> None:
        calls = []

        def forbidden_factory(_rows):
            calls.append(True)
            raise AssertionError("strategy factory must not run")

        for value, type_name in (
            (None, "NoneType"),
            ("0.5", "str"),
            ({"ratio": 0.5}, "dict"),
            ({0.5}, "set"),
        ):
            with self.subTest(value=repr(value)):
                report = self._run(
                    value,
                    signal_factory=forbidden_factory,
                    rows=[],
                )
                self.assertEqual(report["status"], "BLOCK")
                self.assertEqual(report["checks"], [])
                self.assertIn(
                    f"checkpoint_ratio_contract:checkpoint_ratios:not_sequence:{type_name}",
                    report["issues"],
                )
                self.assertFalse(report["paper_authorized"])
                self.assertFalse(report["live_order_allowed"])

        self.assertEqual(calls, [])

    def test_invalid_elements_have_explicit_contract_issues(self) -> None:
        cases = (
            (True, "not_numeric"),
            ("invalid", "not_numeric"),
            (math.nan, "not_finite"),
            (math.inf, "not_finite"),
            (0.0, "outside_open_unit_interval"),
            (1.0, "outside_open_unit_interval"),
            (-0.1, "outside_open_unit_interval"),
            (1.1, "outside_open_unit_interval"),
        )
        for value, issue in cases:
            with self.subTest(value=repr(value)):
                report = self._run((value,), rows=[])
                self.assertEqual(report["status"], "BLOCK")
                self.assertIn(
                    f"checkpoint_ratio_contract:checkpoint_ratios[0]:{issue}",
                    report["issues"],
                )

    def test_empty_sequence_is_rejected_explicitly(self) -> None:
        report = self._run((), rows=[])

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(
            report["issues"],
            ["checkpoint_ratio_contract:checkpoint_ratios:empty"],
        )

    def test_numeric_string_ratio_is_normalized_and_remains_compatible(self) -> None:
        report = self._run(("0.5",))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            report["checkpoint_ratio_contract_version"],
            CHECKPOINT_RATIO_CONTRACT_VERSION,
        )
        self.assertEqual(report["checkpoint_ratios"], [0.5])
        self.assertEqual(report["checkpoint_count"], 1)


if __name__ == "__main__":
    unittest.main()
