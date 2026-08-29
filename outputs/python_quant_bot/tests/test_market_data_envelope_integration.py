from __future__ import annotations

import copy
import unittest
from unittest import mock

import run_internal_strategy_matrix as strategy_matrix
from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
)


class MarketDataEnvelopeLoaderIntegrationTest(unittest.TestCase):
    @staticmethod
    def _payload(
        symbol: str,
        *,
        source: str = "unverified_primary_feed",
    ) -> dict:
        return {
            "ok": True,
            "symbol": symbol,
            "source": source,
            "rows": [
                {
                    "ts_ms": 1_800_000_000_000,
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 10.0,
                    "complete": True,
                    "source": source,
                }
            ],
        }

    def test_required_missing_envelope_blocks_before_alignment(self) -> None:
        align = mock.Mock()
        with (
            mock.patch.object(
                strategy_matrix.server,
                "backtest_market_rows",
                return_value=self._payload("BTC-USDT"),
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                align,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "market_data_envelope_required"):
                strategy_matrix.load_payloads(
                    ["BTC-USDT"],
                    10,
                    require_market_data_envelope=True,
                )
        align.assert_not_called()

    def test_fixture_marked_envelope_blocks_before_alignment(self) -> None:
        payload = self._payload("BTC-USDT", source="fixture_cache")
        attached = attach_market_data_envelope(
            payload,
            symbol="BTC-USDT",
            timeframe="1D",
        )
        align = mock.Mock()
        with (
            mock.patch.object(
                strategy_matrix.server,
                "backtest_market_rows",
                return_value=attached,
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                align,
            ),
        ):
            with self.assertRaises(ValueError) as caught:
                strategy_matrix.load_payloads(
                    ["BTC-USDT"],
                    10,
                    require_market_data_envelope=True,
                )
        message = str(caught.exception)
        self.assertIn("market_data_envelope_fallback_not_allowed", message)
        self.assertIn("market_data_envelope_synthetic_not_allowed", message)
        align.assert_not_called()

    def test_resealed_authority_tamper_blocks_before_alignment(self) -> None:
        payload = self._payload("BTC-USDT")
        attached = attach_market_data_envelope(
            payload,
            symbol="BTC-USDT",
            timeframe="1D",
        )
        attached["market_data_envelope"]["live_order_allowed"] = True
        align = mock.Mock()
        with (
            mock.patch.object(
                strategy_matrix.server,
                "backtest_market_rows",
                return_value=attached,
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                align,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "market_data_envelope_live_authority_invalid",
            ):
                strategy_matrix.load_payloads(
                    ["BTC-USDT"],
                    10,
                    require_market_data_envelope=True,
                )
        align.assert_not_called()

    def test_payload_symbol_drift_and_pseudo_ok_block_before_alignment(self) -> None:
        payload = self._payload("BTC-USDT")
        attached = attach_market_data_envelope(
            payload,
            symbol="BTC-USDT",
            timeframe="1D",
        )
        symbol_drift = copy.deepcopy(attached)
        symbol_drift["symbol"] = "ETH-USDT"
        pseudo_ok = copy.deepcopy(attached)
        pseudo_ok["ok"] = "true"

        cases = (
            (symbol_drift, "market_data_envelope_payload_symbol_mismatch"),
            (pseudo_ok, "market_data_envelope_payload_ok_invalid"),
        )
        for candidate, blocker in cases:
            align = mock.Mock()
            with self.subTest(blocker=blocker):
                with (
                    mock.patch.object(
                        strategy_matrix.server,
                        "backtest_market_rows",
                        return_value=candidate,
                    ),
                    mock.patch.object(
                        strategy_matrix,
                        "align_completed_daily_payloads",
                        align,
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, blocker):
                        strategy_matrix.load_payloads(
                            ["BTC-USDT"],
                            10,
                            require_market_data_envelope=True,
                        )
            align.assert_not_called()

    def test_valid_envelopes_are_stripped_before_alignment(self) -> None:
        symbols = ["BTC-USDT", "ETH-USDT"]
        raw_payloads = {symbol: self._payload(symbol) for symbol in symbols}
        attached_payloads = {
            symbol: attach_market_data_envelope(
                payload,
                symbol=symbol,
                timeframe="1D",
            )
            for symbol, payload in raw_payloads.items()
        }
        observed: dict[str, dict] = {}

        def load_fixture(symbol: str, *_args: object) -> dict:
            return copy.deepcopy(attached_payloads[symbol])

        def align_fixture(payloads: dict[str, dict], **_kwargs: object):
            observed.update(copy.deepcopy(payloads))
            return payloads, {"status": "PASS", "blockers": []}

        manifests = [
            {"symbol": symbol, "status": "PASS", "blockers": []}
            for symbol in symbols
        ]
        with (
            mock.patch.object(
                strategy_matrix.server,
                "backtest_market_rows",
                side_effect=load_fixture,
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                side_effect=align_fixture,
            ),
            mock.patch.object(
                strategy_matrix,
                "dataset_manifests",
                return_value=manifests,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "is_stock_symbol",
                return_value=True,
            ),
        ):
            aligned, projected_manifests, alignment = strategy_matrix.load_payloads(
                symbols,
                10,
                manifest_role="SELECTION",
                manifest_timeframe="1D",
                require_market_data_envelope=True,
            )

        self.assertEqual(observed, raw_payloads)
        self.assertEqual(aligned, raw_payloads)
        self.assertEqual(alignment["status"], "PASS")
        self.assertTrue(
            all("market_data_envelope" not in payload for payload in observed.values())
        )
        self.assertTrue(
            all(item["role"] == "SELECTION" for item in projected_manifests)
        )
        self.assertTrue(
            all(item["timeframe"] == "1D" for item in projected_manifests)
        )

    def test_legacy_missing_envelope_reaches_alignment_when_optional(self) -> None:
        payload = self._payload("BTC-USDT")
        align = mock.Mock(
            return_value=(
                {"BTC-USDT": payload},
                {"status": "PASS", "blockers": []},
            )
        )
        with (
            mock.patch.object(
                strategy_matrix.server,
                "backtest_market_rows",
                return_value=payload,
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                align,
            ),
            mock.patch.object(
                strategy_matrix,
                "dataset_manifests",
                return_value=[
                    {"symbol": "BTC-USDT", "status": "PASS", "blockers": []}
                ],
            ),
            mock.patch.object(
                strategy_matrix.server,
                "is_stock_symbol",
                return_value=True,
            ),
        ):
            aligned, _manifests, alignment = strategy_matrix.load_payloads(
                ["BTC-USDT"],
                10,
                require_market_data_envelope=False,
            )

        align.assert_called_once()
        self.assertEqual(aligned, {"BTC-USDT": payload})
        self.assertEqual(alignment["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
