from __future__ import annotations

import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
    consume_market_data_envelope,
    verify_market_data_envelope,
)


class MarketDataEnvelopeSourceAffinityLockV1Tests(unittest.TestCase):
    @staticmethod
    def _payload(*, provider: str, row_sources: tuple[str, ...]) -> dict:
        return {
            "ok": True,
            "symbol": "TEST",
            "source": provider,
            "rows": [
                {
                    "close": float(index + 1),
                    "complete": True,
                    "source": source,
                }
                for index, source in enumerate(row_sources)
            ],
        }

    @classmethod
    def _attach(cls, *, provider: str, row_sources: tuple[str, ...]) -> tuple[dict, dict]:
        payload = cls._payload(provider=provider, row_sources=row_sources)
        attached = attach_market_data_envelope(
            payload,
            symbol="TEST",
            timeframe="1D",
        )
        return payload, attached

    @staticmethod
    def _consume(attached: dict) -> dict:
        return consume_market_data_envelope(
            attached,
            expected_symbol="TEST",
            expected_timeframe="1D",
            required=True,
            require_complete=True,
        )

    def test_cross_provider_row_source_is_fallback_and_blocked(self) -> None:
        _, attached = self._attach(provider="okx", row_sources=("futu",))
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 1)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertTrue(manifest["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_provider_and_cache_label_mismatch_is_not_implicitly_equated(self) -> None:
        _, attached = self._attach(provider="okx", row_sources=("okx_cache",))
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["cache_rows"], 1)
        self.assertTrue(manifest["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_one_mismatched_row_marks_the_whole_manifest_fallback(self) -> None:
        _, attached = self._attach(
            provider="okx",
            row_sources=("okx", "okx", "futu"),
        )
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 3)
        self.assertTrue(manifest["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_structural_verifier_accepts_self_consistent_fallback_then_consumer_blocks(self) -> None:
        payload, attached = self._attach(provider="okx", row_sources=("futu",))
        envelope = attached["market_data_envelope"]
        verification = verify_market_data_envelope(
            envelope,
            expected_symbol="TEST",
            expected_timeframe="1D",
            expected_rows=payload["rows"],
            expected_provider="okx",
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(envelope["source_manifest"]["fallback"])
        with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
            self._consume(attached)

    def test_case_and_trim_normalization_preserve_exact_source_affinity(self) -> None:
        payload, attached = self._attach(
            provider="OKX",
            row_sources=(" okx ", "OKX"),
        )
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["real_rows"], 2)
        self.assertEqual(manifest["synthetic_rows"], 0)
        self.assertFalse(manifest["fallback"])
        self.assertEqual(self._consume(attached), payload)

    def test_exact_cache_affinity_remains_compatible(self) -> None:
        payload, attached = self._attach(
            provider="okx_cache",
            row_sources=("okx_cache",),
        )
        manifest = attached["market_data_envelope"]["source_manifest"]
        self.assertEqual(manifest["cache_rows"], 1)
        self.assertFalse(manifest["fallback"])
        self.assertEqual(self._consume(attached), payload)


if __name__ == "__main__":
    unittest.main()
