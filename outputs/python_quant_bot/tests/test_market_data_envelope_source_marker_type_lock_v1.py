from __future__ import annotations

import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
    consume_market_data_envelope,
)
from exchange_terminal.domain.contracts import MarketDataSourceManifest


class MarketDataEnvelopeSourceMarkerTypeLockV1Tests(unittest.TestCase):
    @staticmethod
    def _payload(*, provider, row_source) -> dict:
        return {
            "ok": True,
            "symbol": "TEST",
            "source": provider,
            "rows": [
                {
                    "close": 101.0,
                    "complete": True,
                    "source": row_source,
                }
            ],
        }

    @staticmethod
    def _attach(payload: dict) -> dict:
        return attach_market_data_envelope(
            payload,
            symbol="TEST",
            timeframe="1D",
        )

    @staticmethod
    def _consume(attached: dict) -> dict:
        return consume_market_data_envelope(
            attached,
            expected_symbol="TEST",
            expected_timeframe="1D",
            required=True,
            require_complete=True,
        )

    def test_non_string_control_and_oversized_sources_are_fail_closed(self) -> None:
        invalid_values = (
            123,
            True,
            {"name": "okx"},
            ["okx"],
            "okx\nforged",
            "okx\u2028forged",
            "x" * 257,
        )
        for value in invalid_values:
            with self.subTest(value=repr(value)[:80]):
                attached = self._attach(
                    self._payload(provider=value, row_source=value)
                )
                manifest = attached["market_data_envelope"]["source_manifest"]
                self.assertEqual(manifest["provider"], "unknown")
                self.assertEqual(manifest["real_rows"], 0)
                self.assertEqual(manifest["synthetic_rows"], 1)
                self.assertTrue(manifest["fallback"])
                with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
                    self._consume(attached)

    def test_invalid_row_source_preserves_provider_but_blocks_complete_consumer(self) -> None:
        attached = self._attach(self._payload(provider="okx", row_source=123))
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["provider"], "okx")
        self.assertEqual(manifest["synthetic_rows"], 1)
        self.assertTrue(manifest["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_invalid_provider_normalizes_to_unknown_without_string_coercion(self) -> None:
        attached = self._attach(self._payload(provider=123, row_source="okx"))
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["provider"], "unknown")
        self.assertEqual(manifest["real_rows"], 1)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertTrue(manifest["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_domain_manifest_rejects_control_and_oversized_provider_values(self) -> None:
        for provider in ("okx\nforged", "okx\u2029forged", "x" * 257):
            with self.subTest(provider=repr(provider)[:80]):
                with self.assertRaisesRegex(
                    ValueError,
                    "market_data_source_manifest_provider_invalid",
                ):
                    MarketDataSourceManifest(
                        provider=provider,
                        real_rows=1,
                        cache_rows=0,
                        synthetic_rows=0,
                        fallback=False,
                        complete=True,
                        dataset_hash="a" * 64,
                    )

    def test_valid_source_trim_case_and_cache_behavior_remain_compatible(self) -> None:
        payload = self._payload(
            provider=" OKX_CACHE ",
            row_source=" OKX_CACHE ",
        )
        attached = self._attach(payload)
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["provider"], "OKX_CACHE")
        self.assertEqual(manifest["real_rows"], 1)
        self.assertEqual(manifest["cache_rows"], 1)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertFalse(manifest["fallback"])
        self.assertEqual(self._consume(attached), payload)


if __name__ == "__main__":
    unittest.main()
