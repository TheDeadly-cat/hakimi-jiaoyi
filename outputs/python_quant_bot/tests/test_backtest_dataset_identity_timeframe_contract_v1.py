from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from exchange_terminal.services.backtest_engine import (
    DATASET_IDENTITY_CONTRACT_VERSION,
    DATASET_SCHEMA_VERSION,
    TIMEFRAME_CONTRACT_VERSION,
    prepare_backtest_dataset,
)


def contract_rows(indices=range(8)) -> list[dict[str, object]]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    for index in indices:
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


class BacktestDatasetIdentityTimeframeContractV1Tests(unittest.TestCase):
    @staticmethod
    def _prepare(*, symbol="BTC-USDT", source="contract-fixture", timeframe="1D", rows=None):
        return prepare_backtest_dataset(
            contract_rows() if rows is None else rows,
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            minimum_rows=6,
            market="crypto",
        )

    def test_blank_identity_fails_closed_under_dataset_v5(self) -> None:
        prepared = self._prepare(symbol="", source="")
        manifest = prepared["manifest"]

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertEqual(DATASET_SCHEMA_VERSION, "backtest-dataset-v5")
        self.assertEqual(manifest["schema_version"], DATASET_SCHEMA_VERSION)
        self.assertEqual(
            manifest["dataset_identity_contract_version"],
            DATASET_IDENTITY_CONTRACT_VERSION,
        )
        self.assertIn("dataset_identity_contract:symbol_missing", manifest["blockers"])
        self.assertIn("dataset_identity_contract:source_missing", manifest["blockers"])

    def test_noncanonical_or_nonstring_identity_is_explicitly_rejected(self) -> None:
        cases = (
            ({"symbol": " BTC-USDT "}, "dataset_identity_contract:symbol_noncanonical"),
            ({"source": " contract-fixture "}, "dataset_identity_contract:source_noncanonical"),
            ({"symbol": 123}, "dataset_identity_contract:symbol_not_string"),
            ({"source": False}, "dataset_identity_contract:source_not_string"),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                prepared = self._prepare(**overrides)
                self.assertEqual(prepared["status"], "BLOCK")
                self.assertIn(expected, prepared["manifest"]["blockers"])

    def test_unknown_timeframe_cannot_bypass_missing_daily_bar(self) -> None:
        missing_daily_bar = contract_rows([0, 1, 2, 4, 5, 6, 7])

        unknown = self._prepare(
            timeframe="not-a-timeframe",
            rows=missing_daily_bar,
        )
        daily_control = self._prepare(timeframe="1D", rows=missing_daily_bar)

        self.assertEqual(unknown["status"], "BLOCK")
        self.assertIn(
            "timeframe_contract:timeframe_unsupported:not-a-timeframe",
            unknown["manifest"]["blockers"],
        )
        self.assertEqual(daily_control["status"], "BLOCK")
        self.assertIn(
            "temporal_gaps_exceed_policy:1",
            daily_control["manifest"]["blockers"],
        )

    def test_supported_timeframes_are_normalized_without_alias_drift(self) -> None:
        cases = (
            (" 1D ", "1d"),
            ("daily", "1d"),
            (" 1H ", "1h"),
            ("60m", "60m"),
            ("1W", "1w"),
        )
        for requested, normalized in cases:
            with self.subTest(requested=requested):
                prepared = self._prepare(timeframe=requested)
                manifest = prepared["manifest"]
                self.assertEqual(prepared["status"], "PASS")
                self.assertEqual(manifest["timeframe_normalized"], normalized)
                self.assertEqual(
                    manifest["timeframe_contract_version"],
                    TIMEFRAME_CONTRACT_VERSION,
                )

    def test_unmodelled_multi_day_interval_fails_closed(self) -> None:
        prepared = self._prepare(timeframe="2D")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn(
            "timeframe_contract:timeframe_unsupported:2d",
            prepared["manifest"]["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
