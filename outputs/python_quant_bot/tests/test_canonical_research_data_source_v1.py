from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.config import BotConfig  # noqa: E402
from hakimi_research.data import (  # noqa: E402
    MARKET_DATA_SCHEMA_VERSION,
    OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION,
    OKX_COMPLETED_CANDLE_SCHEMA_VERSION,
    OKX_SPOT_VOLUME_UNIT,
    CsvDataProvider,
    OkxPublicDataProvider,
    SyntheticDataProvider,
    build_data_provider,
    market_data_fingerprint,
    okx_bar,
    parse_okx_candle_response,
    parse_okx_completed_candle_rows,
    validate_market_data_frame,
    verify_okx_candle_source_receipt,
)
from quant_bot import data as legacy_data  # noqa: E402


LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "data.py"
CLI_PATH = SRC_ROOT / "hakimi_research" / "cli.py"


class HostileStr(str):
    pass


class HostileBytes(bytes):
    pass


class HostileDict(dict):
    pass


class CanonicalResearchDataSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(MARKET_DATA_SCHEMA_VERSION, "research-market-data-v1")
        for name in (
            "OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION",
            "OKX_COMPLETED_CANDLE_SCHEMA_VERSION",
            "OKX_SPOT_VOLUME_UNIT",
            "CsvDataProvider",
            "OkxPublicDataProvider",
            "SyntheticDataProvider",
            "build_data_provider",
            "okx_bar",
            "validate_market_data_frame",
            "market_data_fingerprint",
            "parse_okx_candle_response",
            "parse_okx_completed_candle_rows",
            "verify_okx_candle_source_receipt",
        ):
            self.assertIs(getattr(legacy_data, name), globals()[name])

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_formal_cli_admits_snapshots_without_a_provider_factory(self) -> None:
        source = CLI_PATH.read_text(encoding="utf-8")
        self.assertIn("from hakimi_research.dataset_registry import", source)
        self.assertIn("load_snapshot(args.snapshot)", source)
        self.assertNotIn("build_data_provider", source)
        self.assertNotIn(".get_history(", source)
        self.assertNotIn("from quant_bot.data import", source)

    def test_factory_requires_exact_config_and_blocks_product_synthetic(self) -> None:
        fake = SimpleNamespace(data=SimpleNamespace(provider="csv", csv_path="fixture.csv"))
        with self.assertRaises(ValueError):
            build_data_provider(fake)  # type: ignore[arg-type]

        csv_config = BotConfig()
        csv_config.data.csv_path = "fixture.csv"
        self.assertIsInstance(build_data_provider(csv_config), CsvDataProvider)

        synthetic_config = BotConfig()
        synthetic_config.data.provider = "synthetic"
        with self.assertRaisesRegex(RuntimeError, "test-only"):
            build_data_provider(synthetic_config)

    def test_factory_constructs_inert_okx_provider_without_io(self) -> None:
        config = BotConfig()
        config.market = "crypto_spot"
        config.data.provider = "okx"
        config.data.cache_dir = ""
        config.data.use_cache = False
        self.assertIsInstance(build_data_provider(config), OkxPublicDataProvider)

        wrong_market = BotConfig()
        wrong_market.data.provider = "okx"
        wrong_market.data.cache_dir = ""
        wrong_market.data.use_cache = False
        with self.assertRaisesRegex(ValueError, "crypto_spot_market_required"):
            build_data_provider(wrong_market)

    def test_csv_constructor_rejects_empty_and_subclass_paths(self) -> None:
        with self.assertRaises(ValueError):
            CsvDataProvider("")
        with self.assertRaises(ValueError):
            CsvDataProvider(HostileStr("fixture.csv"))
        self.assertEqual(CsvDataProvider("fixture.csv").csv_path, "fixture.csv")

    def test_synthetic_provider_is_fixed_and_repeatable(self) -> None:
        provider = SyntheticDataProvider()
        first = provider.get_history("SYNTH", "1h", 40)
        second = provider.get_history("SYNTH", "1h", 40)
        pd.testing.assert_frame_equal(first, second, check_exact=True)
        self.assertEqual(first.index[-1], pd.Timestamp("2024-01-01T00:00:00Z"))
        self.assertEqual(len(first), 40)
        self.assertTrue(first.index.is_unique)
        self.assertTrue(first.index.is_monotonic_increasing)

    def test_synthetic_request_gates_are_exact(self) -> None:
        provider = SyntheticDataProvider()
        invalid = (
            ("SYNTH", "1h", 0),
            ("SYNTH", "1h", -1),
            ("SYNTH", "1h", True),
            ("SYNTH", "1h", "40"),
            (HostileStr("SYNTH"), "1h", 40),
            ("SYNTH", HostileStr("1h"), 40),
            ("SYNTH", "unknown", 40),
        )
        for args in invalid:
            with self.assertRaises(ValueError):
                provider.get_history(*args)  # type: ignore[arg-type]

    def test_okx_timeframe_mapping_is_exact(self) -> None:
        self.assertEqual(okx_bar("1h"), "1H")
        with self.assertRaises(ValueError):
            okx_bar("unknown")
        with self.assertRaises(ValueError):
            okx_bar(HostileStr("1h"))

    @staticmethod
    def okx_rows() -> list[list[str]]:
        return [
            [
                "1722474000000",
                "100",
                "102",
                "99",
                "101",
                "12",
                "1212",
                "1212",
                "0",
            ],
            [
                "1722470400000",
                "98",
                "101",
                "97",
                "100",
                "10",
                "1000",
                "1000",
                "1",
            ],
        ]

    def test_okx_parser_excludes_uncompleted_rows_and_emits_receipt(self) -> None:
        frame, receipt = parse_okx_completed_candle_rows(self.okx_rows())
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.index[0], pd.Timestamp("2024-08-01T00:00:00Z"))
        self.assertEqual(receipt["schema_version"], OKX_COMPLETED_CANDLE_SCHEMA_VERSION)
        self.assertEqual(receipt["accepted_complete_row_count"], 1)
        self.assertEqual(receipt["rejected_uncompleted_row_count"], 1)
        self.assertEqual(receipt["rejection_reasons"], ["OKX_CANDLE_UNCOMPLETED"])
        self.assertTrue(receipt["complete_only"])
        self.assertEqual(receipt["volume_unit"], OKX_SPOT_VOLUME_UNIT)
        self.assertEqual(len(receipt["source_rows_sha256"]), 64)

        provider = OkxPublicDataProvider(cache_dir="", use_cache=False)
        pd.testing.assert_frame_equal(provider._rows_to_frame(self.okx_rows()), frame)

    def test_okx_parser_rejects_malformed_completion_evidence(self) -> None:
        whitespace_timestamp = self.okx_rows()[1].copy()
        whitespace_timestamp[0] = " 1722470400000"
        cases = (
            tuple(self.okx_rows()),
            [self.okx_rows()[0][:-1]],
            [[*self.okx_rows()[0][:-1], "unknown"]],
            [[*self.okx_rows()[0][:-1], True]],
            [whitespace_timestamp],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    parse_okx_completed_candle_rows(rows)  # type: ignore[arg-type]

    def test_all_uncompleted_rows_stay_empty_and_source_hash_is_content_bound(self) -> None:
        source = [self.okx_rows()[0]]
        frame, receipt = parse_okx_completed_candle_rows(source)
        self.assertTrue(frame.empty)
        self.assertIsInstance(frame.index, pd.DatetimeIndex)
        self.assertEqual(str(frame.index.tz), "UTC")
        self.assertEqual(receipt["accepted_complete_row_count"], 0)
        self.assertEqual(receipt["rejected_uncompleted_row_count"], 1)

        changed = [source[0].copy()]
        changed[0][5] = "13"
        _, changed_receipt = parse_okx_completed_candle_rows(changed)
        self.assertNotEqual(
            receipt["source_rows_sha256"],
            changed_receipt["source_rows_sha256"],
        )

    def test_exact_okx_response_bytes_bind_source_identity_and_projection(self) -> None:
        raw = json.dumps(
            {"code": "0", "msg": "", "data": self.okx_rows()},
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        params = {"instId": "BTC-USDT", "bar": "1H", "limit": 2}
        frame, receipt = parse_okx_candle_response(
            raw,
            endpoint="/api/v5/market/candles",
            params=params,
            retrieved_at="2024-08-01T02:00:00Z",
        )
        self.assertEqual(len(frame), 1)
        self.assertEqual(
            receipt["schema_version"],
            OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION,
        )
        self.assertEqual(receipt["raw_response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt["raw_response_size"], len(raw))
        self.assertEqual(receipt["market"], "crypto_spot")
        self.assertEqual(receipt["instrument_type"], "SPOT")
        self.assertEqual(receipt["symbol"], "BTC-USDT")
        self.assertEqual(receipt["timeframe"], "1h")
        self.assertFalse(receipt["paper_allowed"])
        self.assertFalse(receipt["live_allowed"])
        self.assertTrue(
            verify_okx_candle_source_receipt(
                receipt,
                raw,
                endpoint="/api/v5/market/candles",
                params=params,
                retrieved_at="2024-08-01T02:00:00Z",
            )
        )

        tampered = dict(receipt)
        tampered["symbol"] = "ETH-USDT"
        with self.assertRaisesRegex(ValueError, "verification_failed"):
            verify_okx_candle_source_receipt(
                tampered,
                raw,
                endpoint="/api/v5/market/candles",
                params=params,
                retrieved_at="2024-08-01T02:00:00Z",
            )

    def test_okx_response_boundary_rejects_aliases_and_envelope_drift(self) -> None:
        valid_raw = json.dumps(
            {"code": "0", "msg": "", "data": self.okx_rows()},
            separators=(",", ":"),
        ).encode("ascii")
        params = {"instId": "BTC-USDT", "bar": "1H", "limit": 2}
        cases = (
            (HostileBytes(valid_raw), "/api/v5/market/candles", params, "2024-08-01T02:00:00Z"),
            (valid_raw, "/api/v5/market/trades", params, "2024-08-01T02:00:00Z"),
            (valid_raw, "/api/v5/market/candles", HostileDict(params), "2024-08-01T02:00:00Z"),
            (valid_raw, "/api/v5/market/candles", {**params, "instId": "BTC-USDT-SWAP"}, "2024-08-01T02:00:00Z"),
            (valid_raw, "/api/v5/market/candles", {**params, "limit": True}, "2024-08-01T02:00:00Z"),
            (valid_raw, "/api/v5/market/candles", params, "2024-08-01T02:00:00+00:00"),
            (b'{"code":"0","msg":"","data":[],"extra":1}', "/api/v5/market/candles", params, "2024-08-01T02:00:00Z"),
            (b'{"code":"1","msg":"failed","data":[]}', "/api/v5/market/candles", params, "2024-08-01T02:00:00Z"),
            (b'{"code":"0","msg":"","data":[],"x":NaN}', "/api/v5/market/candles", params, "2024-08-01T02:00:00Z"),
        )
        for raw, endpoint, request_params, retrieved_at in cases:
            with self.subTest(endpoint=endpoint, retrieved_at=retrieved_at):
                with self.assertRaises(ValueError):
                    parse_okx_candle_response(
                        raw,  # type: ignore[arg-type]
                        endpoint=endpoint,
                        params=request_params,  # type: ignore[arg-type]
                        retrieved_at=retrieved_at,
                    )

    def test_okx_spot_and_cache_boundaries_reject_derivatives_before_io(self) -> None:
        provider = OkxPublicDataProvider(cache_dir="", use_cache=False)
        with self.assertRaisesRegex(ValueError, "okx_spot_symbol_required"):
            provider._cache_path("BTC-USDT-SWAP", "1h")
        with patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("network I/O forbidden in contract tests"),
        ) as urlopen:
            with self.assertRaisesRegex(ValueError, "okx_spot_symbol_required"):
                provider._fetch_page(
                    "/api/v5/market/candles",
                    "BTC-USDT-SWAP",
                    "1h",
                    10,
                )
            urlopen.assert_not_called()
        self.assertIn(
            OKX_COMPLETED_CANDLE_SCHEMA_VERSION,
            provider._cache_path("BTC-USDT", "1h").name,
        )

    def test_frame_validation_normalizes_utc_copy(self) -> None:
        source = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        validated = validate_market_data_frame(source)
        self.assertIsNot(validated, source)
        self.assertEqual(str(validated.index.tz), "UTC")
        source.iloc[0, 0] = -1.0
        self.assertGreater(validated.iloc[0, 0], 0.0)

    def test_frame_validation_rejects_quality_failures(self) -> None:
        valid = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        cases = []
        duplicate = pd.concat([valid.iloc[:1], valid])
        cases.append(duplicate)
        unordered = valid.iloc[::-1]
        cases.append(unordered)
        naive = valid.copy()
        naive.index = naive.index.tz_localize(None)
        cases.append(naive)
        nonfinite = valid.copy()
        nonfinite.iloc[0, 0] = math.nan
        cases.append(nonfinite)
        negative_volume = valid.copy()
        negative_volume.iloc[0, 4] = -1.0
        cases.append(negative_volume)
        invalid_high = valid.copy()
        invalid_high.iloc[0, 1] = invalid_high.iloc[0].iloc[[0, 3]].min() - 1.0
        cases.append(invalid_high)
        for frame in cases:
            with self.assertRaises(ValueError):
                validate_market_data_frame(frame)

    def test_market_data_fingerprint_is_stable_and_content_bound(self) -> None:
        first = SyntheticDataProvider().get_history("SYNTH", "1h", 40)
        second = first.copy(deep=True)
        self.assertEqual(market_data_fingerprint(first), market_data_fingerprint(second))
        second.iloc[0, 0] += 0.01
        self.assertNotEqual(market_data_fingerprint(first), market_data_fingerprint(second))


if __name__ == "__main__":
    unittest.main()
