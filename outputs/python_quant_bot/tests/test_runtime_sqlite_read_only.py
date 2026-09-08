from __future__ import annotations

import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.market_data import stock_candles_io
from exchange_terminal.services.audit_log import AuditLog
from exchange_terminal.services.corporate_action_ledger import CorporateActionLedger
from exchange_terminal.services.market_data_revision_ledger import MarketDataRevisionLedger
from exchange_terminal.services.mutation_journal import MutationJournal
from exchange_terminal.services.portfolio_experiment import PortfolioExperimentRegistry
from exchange_terminal.services.research_bridge import ResearchBridge
from exchange_terminal.services.sqlite_runtime import RuntimeReadOnlyError
from exchange_terminal.services.strategy_matrix_protocol import StrategyMatrixRegistrationStore
from exchange_terminal.services.strategy_pipeline import StrategyPipeline


class RuntimeSqliteReadOnlyTests(unittest.TestCase):
    @staticmethod
    def _snapshot(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    @staticmethod

    @classmethod

    def test_all_runtime_ledgers_remain_byte_identical_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            now_ms = lambda: 1_780_000_000_000

            audit_path = root / "audit.jsonl"
            mutation_path = root / "mutation.sqlite3"
            strategy_path = root / "strategy.sqlite3"
            research_path = root / "research.sqlite3"
            experiment_path = root / "experiments.sqlite3"
            corporate_path = root / "corporate.sqlite"
            revision_path = root / "revisions.sqlite"
            matrix_registry_path = root / "matrix_registry.sqlite3"

            AuditLog(path=audit_path, ensure_runtime=lambda: root.mkdir(exist_ok=True), now_ms=now_ms)
            MutationJournal(db_path=mutation_path, now_ms=now_ms)
            StrategyPipeline(db_path=strategy_path, now_ms=now_ms)
            ResearchBridge(db_path=research_path, now_ms=now_ms)
            PortfolioExperimentRegistry(db_path=experiment_path, now_ms=now_ms)
            CorporateActionLedger(corporate_path, now_ms)
            MarketDataRevisionLedger(revision_path, now_ms)
            StrategyMatrixRegistrationStore(db_path=matrix_registry_path, now_ms=now_ms)

            before = self._snapshot(root)
            self.assertEqual(len(before), 8)

            audit = AuditLog(
                path=audit_path,
                ensure_runtime=lambda: root.mkdir(exist_ok=True),
                now_ms=now_ms,
                read_only=True,
            )
            mutation = MutationJournal(db_path=mutation_path, now_ms=now_ms, read_only=True)
            strategy = StrategyPipeline(db_path=strategy_path, now_ms=now_ms, read_only=True)
            research = ResearchBridge(db_path=research_path, now_ms=now_ms, read_only=True)
            experiments = PortfolioExperimentRegistry(db_path=experiment_path, now_ms=now_ms, read_only=True)
            corporate = CorporateActionLedger(corporate_path, now_ms, read_only=True)
            revisions = MarketDataRevisionLedger(revision_path, now_ms, read_only=True)
            matrix_registry = StrategyMatrixRegistrationStore(
                db_path=matrix_registry_path,
                now_ms=now_ms,
                read_only=True,
            )

            audit.summary()
            mutation.summary()
            strategy.snapshot()
            research.list()
            experiments.summary()
            corporate.summary()
            revisions.summary()
            matrix_registry.audit()

            blocked_calls = [
                lambda: audit.append({"type": "blocked"}),
                lambda: mutation.begin("/api/test", "readonly-test-key", {}),
                lambda: strategy.define(strategy_id="test", symbol="AAPL"),
                lambda: research.import_summary({}),
                lambda: experiments.register(protocol={}, source_files=[], clock_attestation={}),
                lambda: corporate.record(symbol="AAPL", provider="test", actions=[], evidence={}),
                lambda: revisions.record_snapshot({}),
                lambda: matrix_registry.register({}),
            ]
            for call in blocked_calls:
                with self.subTest(call=repr(call)):
                    with self.assertRaises(RuntimeReadOnlyError):
                        call()

            self.assertEqual(self._snapshot(root), before)






    def test_stock_candle_cache_read_does_not_initialize_or_mutate_schema(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "stock_candles.sqlite3"
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", path),
                patch.object(stock_candles_io, "RUNTIME_READ_ONLY", False),
            ):
                conn = stock_candles_io.ensure_stock_candle_cache_db(write=True)
                conn.close()
            before = self._snapshot(root)

            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", path),
                patch.object(stock_candles_io, "RUNTIME_READ_ONLY", True),
            ):
                conn = stock_candles_io.ensure_stock_candle_cache_db()
                self.assertIsNotNone(conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'stock_candles'"
                ).fetchone())
                conn.close()
                with self.assertRaises(RuntimeReadOnlyError):
                    stock_candles_io.ensure_stock_candle_cache_db(write=True)

            self.assertEqual(self._snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
