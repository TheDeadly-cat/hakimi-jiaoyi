from __future__ import annotations

import unittest

from exchange_terminal.application.market_data_envelope import (
    build_market_data_envelope,
    verify_market_data_envelope,
)
from exchange_terminal.domain.contracts import (
    CapabilityContract,
    MarketDataEnvelope,
    MarketDataSourceManifest,
    ProductCapabilityCatalog,
    build_product_capability_catalog,
    build_research_only_capability,
)


class DomainContractsFailClosedV1Tests(unittest.TestCase):
    @staticmethod
    def _manifest(**overrides) -> MarketDataSourceManifest:
        values = {
            "provider": "synthetic-test-provider",
            "real_rows": 1,
            "cache_rows": 0,
            "synthetic_rows": 0,
            "fallback": False,
            "complete": True,
            "dataset_hash": "a" * 64,
        }
        values.update(overrides)
        return MarketDataSourceManifest(**values)

    @classmethod
    def _envelope(cls, **overrides) -> MarketDataEnvelope:
        values = {
            "symbol": "BTC-USDT",
            "timeframe": "1D",
            "rows": [{"close": 101.0, "complete": True}],
            "source_manifest": cls._manifest(),
        }
        values.update(overrides)
        return MarketDataEnvelope(**values)

    def test_capability_contract_permanently_locks_research_only_authority(self) -> None:
        self.assertEqual(
            build_research_only_capability().to_dict(),
            {
                "product_mode": "research_only",
                "research_only": True,
                "paper_allowed": False,
                "live_allowed": False,
                "schema_version": "capability-v1",
            },
        )
        invalid = (
            {"product_mode": "paper"},
            {"research_only": False},
            {"paper_allowed": True},
            {"live_allowed": True},
            {"schema_version": "capability-v2"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "capability_contract_"):
                    CapabilityContract(**overrides)

    def test_product_capability_catalog_rejects_status_and_binding_drift(self) -> None:
        catalog = build_product_capability_catalog().to_dict()
        self.assertEqual(catalog["capabilities"]["historical_backtest"], "Supported")
        self.assertEqual(catalog["capabilities"]["parameter_optimization"], "Archived")
        self.assertEqual(catalog["capabilities"]["paper_execution"], "Archived")
        self.assertEqual(catalog["capabilities"]["live_execution"], "Archived")
        self.assertEqual(catalog["capabilities"]["order_entry"], "Disabled")
        invalid = (
            {"product_mode": "paper"},
            {"capability_statuses": (("historical_backtest", "Supported"),)},
            {"cli_bindings": (("backtest", "paper_execution"),)},
            {"schema_version": "product-capability-catalog-v2"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "product_capability_catalog_"):
                    ProductCapabilityCatalog(**overrides)

    def test_manifest_requires_canonical_counts_flags_hash_and_schema(self) -> None:
        self.assertEqual(self._manifest().to_dict()["dataset_hash"], "a" * 64)
        invalid = (
            {"provider": ""},
            {"provider": " provider "},
            {"real_rows": True},
            {"real_rows": -1},
            {"cache_rows": 2},
            {"synthetic_rows": -1},
            {"synthetic_rows": 1, "fallback": False},
            {"fallback": 1},
            {"complete": 1},
            {"dataset_hash": "A" * 64},
            {"dataset_hash": "a" * 63},
            {"schema_version": "market-data-source-manifest-v2"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "market_data_source_manifest_"):
                    self._manifest(**overrides)

    def test_envelope_rejects_shape_count_schema_and_authority_drift(self) -> None:
        invalid = (
            {"symbol": ""},
            {"symbol": " BTC-USDT"},
            {"timeframe": ""},
            {"rows": ({"close": 101.0},)},
            {"rows": [object()]},
            {"source_manifest": object()},
            {"rows": [], "source_manifest": self._manifest()},
            {"research_only": False},
            {"paper_authorized": True},
            {"live_order_allowed": True},
            {"schema_version": "market-data-envelope-v2"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "market_data_envelope_"):
                    self._envelope(**overrides)

    def test_envelope_copies_input_and_serialized_rows(self) -> None:
        rows = [{"close": 101.0, "complete": True}]
        envelope = self._envelope(rows=rows)
        rows[0]["close"] = 999.0
        self.assertEqual(envelope.rows[0]["close"], 101.0)
        serialized = envelope.to_dict()
        serialized["rows"][0]["close"] = 888.0
        self.assertEqual(envelope.rows[0]["close"], 101.0)

    def test_existing_builder_and_verifier_remain_compatible(self) -> None:
        rows = [
            {
                "close": 101.0,
                "complete": True,
                "source": "okx_cache",
            }
        ]
        envelope = build_market_data_envelope(
            {"source": "okx_cache", "rows": rows},
            symbol="BTC-USDT",
            timeframe="1D",
        )
        verification = verify_market_data_envelope(
            envelope,
            expected_symbol="BTC-USDT",
            expected_timeframe="1D",
            expected_rows=rows,
            expected_provider="okx_cache",
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["research_only"])
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
