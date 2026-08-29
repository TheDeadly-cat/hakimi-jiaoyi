from __future__ import annotations

import copy
import unittest
from unittest import mock

from exchange_terminal.application import market_data_envelope as envelope_module
from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
    consume_market_data_envelope,
    consume_market_data_payloads,
    verify_market_data_envelope,
)


class MarketDataEnvelopeTest(unittest.TestCase):
    @staticmethod
    def _payload(*, source: str = "okx_cache", complete: bool = True) -> dict:
        return {
            "ok": True,
            "symbol": "BTC-USDT",
            "source": source,
            "rows": [{
                "ts": 1_800_000_000_000,
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 10.0,
                "complete": complete,
                "source": source,
            }],
        }

    def test_round_trip_binds_rows_source_and_authority_then_strips_sidecar(self) -> None:
        payload = self._payload()
        attached = attach_market_data_envelope(payload, symbol="BTC-USDT", timeframe="1D")
        verification = verify_market_data_envelope(
            attached["market_data_envelope"],
            expected_symbol="BTC-USDT",
            expected_timeframe="1D",
            expected_rows=payload["rows"],
            expected_provider=payload["source"],
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["research_only"])
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])
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

    def test_verification_hashes_the_observed_rows_only_once(self) -> None:
        payload = self._payload()
        attached = attach_market_data_envelope(
            payload,
            symbol="BTC-USDT",
            timeframe="1D",
        )
        original_hash = envelope_module._canonical_hash
        with mock.patch.object(
            envelope_module,
            "_canonical_hash",
            wraps=original_hash,
        ) as hash_rows:
            verification = verify_market_data_envelope(
                attached["market_data_envelope"],
                expected_symbol="BTC-USDT",
                expected_timeframe="1D",
                expected_rows=payload["rows"],
                expected_provider=payload["source"],
            )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(hash_rows.call_count, 1)

    def test_authority_hash_source_and_payload_row_tampering_block(self) -> None:
        attached = attach_market_data_envelope(self._payload(), symbol="BTC-USDT", timeframe="1D")
        mutations = []
        authority = copy.deepcopy(attached)
        authority["market_data_envelope"]["paper_authorized"] = True
        mutations.append(authority)
        dataset_hash = copy.deepcopy(attached)
        dataset_hash["market_data_envelope"]["source_manifest"]["dataset_hash"] = "0" * 64
        mutations.append(dataset_hash)
        source = copy.deepcopy(attached)
        source["source"] = "different_provider"
        mutations.append(source)
        row = copy.deepcopy(attached)
        row["rows"][0]["close"] = 999.0
        mutations.append(row)
        for mutated in mutations:
            with self.subTest(mutated=mutated):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
                    consume_market_data_envelope(
                        mutated,
                        expected_symbol="BTC-USDT",
                        expected_timeframe="1D",
                        required=True,
                        require_complete=True,
                    )

    def test_required_complete_gate_rejects_missing_synthetic_fallback_and_incomplete(self) -> None:
        with self.assertRaisesRegex(ValueError, "market_data_envelope_required"):
            consume_market_data_envelope(
                self._payload(),
                expected_symbol="BTC-USDT",
                expected_timeframe="1D",
                required=True,
                require_complete=True,
            )
        for payload in (self._payload(source="synthetic_fallback"), self._payload(complete=False)):
            attached = attach_market_data_envelope(payload, symbol="BTC-USDT", timeframe="1D")
            with self.subTest(source=payload["source"], complete=payload["rows"][0]["complete"]):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_blocked"):
                    consume_market_data_envelope(
                        attached,
                        expected_symbol="BTC-USDT",
                        expected_timeframe="1D",
                        required=True,
                        require_complete=True,
                    )

    def test_batch_consumer_is_consumer_first_and_legacy_missing_is_optional(self) -> None:
        btc = self._payload()
        eth = copy.deepcopy(btc)
        eth["symbol"] = "ETH-USDT"
        attached = {
            "BTC-USDT": attach_market_data_envelope(btc, symbol="BTC-USDT", timeframe="1D"),
            "ETH-USDT": attach_market_data_envelope(eth, symbol="ETH-USDT", timeframe="1D"),
        }
        self.assertEqual(
            consume_market_data_payloads(
                attached,
                expected_timeframe="1D",
                required=True,
                require_complete=True,
            ),
            {"BTC-USDT": btc, "ETH-USDT": eth},
        )
        self.assertEqual(
            consume_market_data_envelope(
                btc,
                expected_symbol="BTC-USDT",
                expected_timeframe="1D",
                required=False,
                require_complete=False,
            ),
            btc,
        )


if __name__ == "__main__":
    unittest.main()
