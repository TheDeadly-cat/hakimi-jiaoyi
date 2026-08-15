from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_data_admission import (
    build_strategy_data_admission,
    verify_strategy_data_admission,
)


NOW_MS = 1_800_000_000_000
DATA_HASH = "a" * 64


def rows() -> list[dict[str, object]]:
    return [
        {
            "date": "2027-01-12",
            "ts_ms": NOW_MS - 2 * 86_400_000,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1_000.0,
            "complete": True,
            "complete_attested": True,
        },
        {
            "date": "2027-01-13",
            "ts_ms": NOW_MS - 86_400_000,
            "open": 101.0,
            "high": 103.0,
            "low": 100.0,
            "close": 102.0,
            "volume": 1_100.0,
            "complete": True,
            "complete_attested": True,
        },
    ]


def manifest(symbol: str = "BTC-USDT", market: str = "crypto") -> dict[str, object]:
    values = rows()
    return {
        "symbol": symbol,
        "market": market,
        "timeframe": "1D",
        "source": "okx_history_candles",
        "status": "PASS",
        "hash_scope": "FULL_OHLCV",
        "data_hash": DATA_HASH,
        "row_count": len(values),
        "first": values[0]["date"],
        "last": values[-1]["date"],
        "first_ts_ms": values[0]["ts_ms"],
        "last_ts_ms": values[-1]["ts_ms"],
        "blockers": [],
    }


class StrategyDataAdmissionTests(unittest.TestCase):
    def test_crypto_frozen_dataset_passes_and_is_bound_to_lineage(self) -> None:
        evidence = build_strategy_data_admission(
            market_payload={"symbol": "BTC-USDT", "source": "okx_history_candles", "rows": rows()},
            dataset_manifest=manifest(),
            dataset_lineage_id="strategy-backtest:test-1",
            market="crypto",
            generated_at=NOW_MS,
        )

        audit = verify_strategy_data_admission(
            evidence,
            expected_symbol="BTC-USDT",
            expected_data_hash=DATA_HASH,
            expected_lineage_id="strategy-backtest:test-1",
            verification_at=NOW_MS,
        )

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["paper_gate_status"], "PASS")
        self.assertEqual(audit["status"], "PASS")

    def test_preview_is_research_visible_but_never_paper_admitted(self) -> None:
        evidence = build_strategy_data_admission(
            market_payload={"symbol": "BTC-USDT", "source": "okx_history_candles", "rows": rows()},
            dataset_manifest=manifest(),
            dataset_lineage_id="",
            market="crypto",
            generated_at=NOW_MS,
        )

        self.assertEqual(evidence["status"], "REVIEW")
        self.assertEqual(evidence["research_gate_status"], "PASS")
        self.assertEqual(evidence["paper_gate_status"], "BLOCK")
        self.assertIn("immutable_dataset_lineage_missing", evidence["blockers"])

    def test_frozen_evidence_expires_when_the_dataset_becomes_stale(self) -> None:
        evidence = build_strategy_data_admission(
            market_payload={"symbol": "BTC-USDT", "source": "okx_history_candles", "rows": rows()},
            dataset_manifest=manifest(),
            dataset_lineage_id="strategy-backtest:test-2",
            market="crypto",
            generated_at=NOW_MS,
        )

        audit = verify_strategy_data_admission(
            evidence,
            expected_symbol="BTC-USDT",
            expected_data_hash=DATA_HASH,
            expected_lineage_id="strategy-backtest:test-2",
            verification_at=NOW_MS + 6 * 86_400_000,
        )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("dataset_stale", audit["blockers"])

    def test_tampering_and_malformed_payloads_fail_closed(self) -> None:
        evidence = build_strategy_data_admission(
            market_payload={"symbol": "BTC-USDT", "source": "okx_history_candles", "rows": rows()},
            dataset_manifest=manifest(),
            dataset_lineage_id="strategy-backtest:test-3",
            market="crypto",
            generated_at=NOW_MS,
        )
        evidence["dataset"]["data_hash"] = "b" * 64

        tampered = verify_strategy_data_admission(
            evidence,
            expected_symbol="BTC-USDT",
            expected_data_hash=DATA_HASH,
            verification_at=NOW_MS,
        )
        malformed = verify_strategy_data_admission(
            ["not", "a", "mapping"],
            expected_symbol="BTC-USDT",
            expected_data_hash=DATA_HASH,
            verification_at=NOW_MS,
        )

        self.assertEqual(tampered["status"], "BLOCK")
        self.assertIn("data_admission_evidence_hash_invalid", tampered["blockers"])
        self.assertIn("data_admission_dataset_hash_mismatch", tampered["blockers"])
        self.assertEqual(malformed["status"], "BLOCK")
        self.assertIn("data_admission_type_invalid", malformed["blockers"])

    def test_stock_dataset_without_adjustment_and_revision_contracts_is_blocked(self) -> None:
        stock_manifest = manifest("AAPL", "stock")
        stock_manifest["source"] = "futu"
        evidence = build_strategy_data_admission(
            market_payload={"symbol": "AAPL", "source": "futu", "rows": rows()},
            dataset_manifest=stock_manifest,
            dataset_lineage_id="strategy-backtest:stock-test",
            market="stock",
            generated_at=NOW_MS,
        )

        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("stock_adjustment_contract", evidence["research_blockers"])
        self.assertIn("stock_revision_ledger", evidence["blockers"])
        self.assertIn("independent_cross_source_evidence", evidence["blockers"])


if __name__ == "__main__":
    unittest.main()
