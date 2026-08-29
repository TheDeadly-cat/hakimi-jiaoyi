from __future__ import annotations

import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
    consume_market_data_envelope,
    verify_market_data_envelope,
)


class MarketDataEnvelopeSourceMarkerFailClosedV1Tests(unittest.TestCase):
    @staticmethod
    def _payload(*, provider: str, row_source: str | None = None) -> dict:
        row = {"close": 101.0, "complete": True}
        if row_source is not None:
            row["source"] = row_source
        return {
            "ok": True,
            "symbol": "TEST-USDT",
            "source": provider,
            "rows": [row],
        }

    @classmethod
    def _attach(cls, *, provider: str, row_source: str | None = None) -> tuple[dict, dict]:
        payload = cls._payload(provider=provider, row_source=row_source)
        return payload, attach_market_data_envelope(
            payload,
            symbol="TEST-USDT",
            timeframe="1D",
        )

    def _assert_complete_consumer_blocks(self, attached: dict) -> None:
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            consume_market_data_envelope(
                attached,
                expected_symbol="TEST-USDT",
                expected_timeframe="1D",
                required=True,
                require_complete=True,
            )

    def test_explicit_non_real_marker_vocabulary_is_fail_closed(self) -> None:
        markers = (
            "generated_model",
            "mock_feed",
            "fixture_rows",
            "demo_source",
            "sample_data",
            "simulated_market",
            "random_walk",
            "placeholder_feed",
            "testnet_feed",
            "paper_replay",
        )
        for marker in markers:
            with self.subTest(marker=marker):
                _, attached = self._attach(provider=marker, row_source=marker)
                manifest = attached["market_data_envelope"]["source_manifest"]
                self.assertEqual(manifest["real_rows"], 0)
                self.assertEqual(manifest["synthetic_rows"], 1)
                self.assertTrue(manifest["fallback"])
                self._assert_complete_consumer_blocks(attached)

    def test_missing_row_source_is_classified_as_synthetic_fallback(self) -> None:
        _, attached = self._attach(provider="okx", row_source=None)
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 0)
        self.assertEqual(manifest["synthetic_rows"], 1)
        self.assertTrue(manifest["fallback"])
        self._assert_complete_consumer_blocks(attached)

    def test_non_real_provider_blocks_even_when_row_marker_looks_real(self) -> None:
        _, attached = self._attach(provider="generated_gateway", row_source="okx")
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 1)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertTrue(manifest["fallback"])
        self._assert_complete_consumer_blocks(attached)

    def test_manifest_verification_and_complete_consumption_keep_separate_roles(self) -> None:
        payload, attached = self._attach(
            provider="generated_model",
            row_source="generated_model",
        )
        envelope = attached["market_data_envelope"]
        verification = verify_market_data_envelope(
            envelope,
            expected_symbol="TEST-USDT",
            expected_timeframe="1D",
            expected_rows=payload["rows"],
            expected_provider=payload["source"],
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(envelope["source_manifest"]["fallback"])
        self._assert_complete_consumer_blocks(attached)

    def test_known_cache_marker_remains_compatible(self) -> None:
        payload, attached = self._attach(provider="okx_cache", row_source="okx_cache")
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 1)
        self.assertEqual(manifest["cache_rows"], 1)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertFalse(manifest["fallback"])
        self.assertEqual(
            consume_market_data_envelope(
                attached,
                expected_symbol="TEST-USDT",
                expected_timeframe="1D",
                required=True,
                require_complete=True,
            ),
            payload,
        )


if __name__ == "__main__":
    unittest.main()
