from __future__ import annotations

import copy
import unittest
from unittest import mock

import run_internal_strategy_matrix as strategy_matrix


class MarketDataEnvelopeServerIntegrationTest(unittest.TestCase):
    def test_crypto_server_producer_reaches_loader_without_network_or_sidecar_leak(self) -> None:
        now_ms = 1_800_000_000_000
        source = "unverified_primary_cache"
        candle = {
            "ts_ms": now_ms - 86_400_000,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
            "complete": True,
            "source": source,
        }
        cache_payload = {
            "status": "PASS",
            "rows": [candle],
            "manifest": {"schema_version": "fixture-cache-manifest-v1"},
            "path": "fixture-only",
        }
        observed_before_alignment: dict[str, dict] = {}

        def merge_rows(left: list[dict], right: list[dict], *, limit: int):
            rows = [*left, *right]
            rows.sort(key=lambda row: int(row.get("ts_ms") or 0))
            return rows[-limit:]

        def align_rows(payloads: dict[str, dict], **_kwargs: object):
            observed_before_alignment.update(copy.deepcopy(payloads))
            return payloads, {"status": "PASS", "blockers": []}

        def history_evidence(**kwargs: object) -> dict:
            rows = list(kwargs.get("rows") or [])
            return {
                "schema_version": "fixture-history-evidence-v1",
                "status": "PASS",
                "row_count": len(rows),
                "cache_admitted": True,
                "cache_manifest": {},
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }

        fetch = mock.Mock(return_value=[])
        with (
            mock.patch.object(
                strategy_matrix.server,
                "is_stock_symbol",
                return_value=False,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "read_market_history_cache",
                return_value=cache_payload,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "normalize_backtest_candle",
                side_effect=lambda row: dict(row),
            ),
            mock.patch.object(
                strategy_matrix.server,
                "merge_backtest_history",
                side_effect=merge_rows,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "fetch_okx_daily_history",
                fetch,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "now_ms",
                return_value=now_ms,
            ),
            mock.patch.object(
                strategy_matrix.server,
                "build_history_dataset_evidence",
                side_effect=history_evidence,
            ),
            mock.patch.object(
                strategy_matrix,
                "align_completed_daily_payloads",
                side_effect=align_rows,
            ),
            mock.patch.object(
                strategy_matrix,
                "dataset_manifests",
                return_value=[
                    {"symbol": "ETH-USDT", "status": "PASS", "blockers": []}
                ],
            ),
        ):
            aligned, manifests, alignment = strategy_matrix.load_payloads(
                ["ETH-USDT"],
                1,
                dataset_lineage_prefix="fixture-selection",
                manifest_role="SELECTION",
                manifest_timeframe="1D",
                require_market_data_envelope=True,
            )

        fetch.assert_not_called()
        self.assertEqual(alignment["status"], "PASS")
        self.assertEqual(aligned["ETH-USDT"]["rows"], [candle])
        self.assertEqual(
            observed_before_alignment["ETH-USDT"]["source"],
            source,
        )
        self.assertNotIn(
            "market_data_envelope",
            observed_before_alignment["ETH-USDT"],
        )
        self.assertEqual(manifests[0]["role"], "SELECTION")
        self.assertEqual(manifests[0]["timeframe"], "1D")


if __name__ == "__main__":
    unittest.main()
