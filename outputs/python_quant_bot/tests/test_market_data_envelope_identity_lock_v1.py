from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
    consume_market_data_envelope,
    verify_market_data_envelope,
)
from exchange_terminal.domain.contracts import (
    MarketDataEnvelope,
    MarketDataSourceManifest,
)


class MarketDataEnvelopeIdentityLockV1Tests(unittest.TestCase):
    @staticmethod
    def _payload() -> dict:
        return {
            "ok": True,
            "symbol": "BTC-USDT",
            "source": "okx",
            "rows": [
                {
                    "close": 101.0,
                    "complete": True,
                    "source": "okx",
                }
            ],
        }

    @staticmethod
    def _manifest() -> MarketDataSourceManifest:
        return MarketDataSourceManifest(
            provider="okx",
            real_rows=1,
            cache_rows=0,
            synthetic_rows=0,
            fallback=False,
            complete=True,
            dataset_hash="a" * 64,
        )

    def test_builder_rejects_non_string_symbol_and_timeframe(self) -> None:
        invalid = (
            {"symbol": 123, "timeframe": "1D"},
            {"symbol": "BTC-USDT", "timeframe": True},
            {"symbol": {"value": "BTC-USDT"}, "timeframe": "1D"},
        )
        for values in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_"):
                    attach_market_data_envelope(self._payload(), **values)

    def test_builder_rejects_control_pipe_and_oversized_identity_values(self) -> None:
        invalid = (
            {"symbol": "BTC\nFORGED", "timeframe": "1D"},
            {"symbol": "BTC-USDT", "timeframe": "1D|version:v2"},
            {"symbol": "BTC\u2028USDT", "timeframe": "1D"},
            {"symbol": "S" * 129, "timeframe": "1D"},
            {"symbol": "BTC-USDT", "timeframe": "T" * 129},
        )
        for values in invalid:
            with self.subTest(values=repr(values)[:100]):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_"):
                    attach_market_data_envelope(self._payload(), **values)

    def test_builder_preserves_existing_trim_behavior_for_valid_strings(self) -> None:
        payload = self._payload()
        attached = attach_market_data_envelope(
            payload,
            symbol=" BTC-USDT ",
            timeframe=" 1D ",
        )
        envelope = attached["market_data_envelope"]
        self.assertEqual(envelope["symbol"], "BTC-USDT")
        self.assertEqual(envelope["timeframe"], "1D")
        self.assertEqual(
            consume_market_data_envelope(
                attached,
                expected_symbol="BTC-USDT",
                expected_timeframe="1D",
                required=True,
                require_complete=True,
            ),
            payload,
        )

    def test_domain_constructor_rejects_noncanonical_identity_values(self) -> None:
        invalid = (
            {"symbol": "BTC\nFORGED", "timeframe": "1D"},
            {"symbol": "BTC-USDT", "timeframe": "1D|v2"},
            {"symbol": " BTC-USDT", "timeframe": "1D"},
            {"symbol": "BTC-USDT", "timeframe": "T" * 129},
        )
        for values in invalid:
            with self.subTest(values=repr(values)[:100]):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_"):
                    MarketDataEnvelope(
                        rows=[{"close": 101.0}],
                        source_manifest=self._manifest(),
                        **values,
                    )

    def test_verifier_blocks_tampered_serialized_identity_values(self) -> None:
        attached = attach_market_data_envelope(
            self._payload(),
            symbol="BTC-USDT",
            timeframe="1D",
        )
        for field, value in (
            ("symbol", "BTC\nFORGED"),
            ("timeframe", "1D|version:v2"),
            ("symbol", " BTC-USDT"),
        ):
            with self.subTest(field=field, value=repr(value)):
                envelope = copy.deepcopy(attached["market_data_envelope"])
                envelope[field] = value
                verification = verify_market_data_envelope(envelope)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertIn(
                    f"market_data_envelope_{field}_invalid",
                    verification["blockers"],
                )


if __name__ == "__main__":
    unittest.main()
