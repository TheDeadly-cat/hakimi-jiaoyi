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
from exchange_terminal.services.paper_executor import PaperExecutor
from exchange_terminal.services.paper_ledger import PaperLedger
from exchange_terminal.services.portfolio_experiment import PortfolioExperimentRegistry
from exchange_terminal.services.portfolio_paper_account import PortfolioPaperLedger
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
    def _legacy_order(
        order_id: str,
        *,
        risk_request_id: str,
        created_at: int,
    ) -> dict[str, object]:
        return {
            "order_id": order_id,
            "risk_request_id": risk_request_id,
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "mark_price": 100.0,
            "limit_price": 0.0,
            "requested_notional": 100.0,
            "requested_qty": 1.0,
            "quantity_constrained": True,
            "state": "REJECTED",
            "created_at": created_at,
            "updated_at": created_at,
            "reduce_only": False,
            "position_side_before": "FLAT",
            "idempotency_key": f"legacy-key-{order_id}",
            "request_signature": f"legacy-signature-{order_id}",
            "run_id": "legacy-run",
            "transitions": [
                {"state": "REJECTED", "time": created_at, "reason": "legacy fixture"}
            ],
            "execution_report": {
                "status": "REJECTED",
                "avg_price": 0.0,
                "filled_qty": 0.0,
                "filled_notional": 0.0,
                "fee": 0.0,
                "funding_estimate": 0.0,
                "funding_charged": 0.0,
            },
        }

    @classmethod
    def _create_legacy_paper_database(
        cls,
        path: Path,
        *,
        duplicate_risk_request: bool = False,
    ) -> list[dict[str, object]]:
        orders = [
            cls._legacy_order(
                "legacy-order-1",
                risk_request_id="legacy-risk-1",
                created_at=101,
            )
        ]
        if duplicate_risk_request:
            orders.append(cls._legacy_order(
                "legacy-order-2",
                risk_request_id="legacy-risk-1",
                created_at=102,
            ))
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(
                """
                CREATE TABLE paper_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE paper_account_state (
                    account_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE paper_account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    UNIQUE(account_id, version)
                );
                CREATE TABLE paper_lifecycle_orders (
                    order_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    state TEXT NOT NULL,
                    risk_request_id TEXT,
                    market_snapshot_id TEXT,
                    strategy_id TEXT,
                    run_id TEXT,
                    account_applied INTEGER NOT NULL DEFAULT 0,
                    account_version INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE paper_fills (
                    fill_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    notional REAL NOT NULL,
                    fee REAL NOT NULL,
                    funding REAL NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                INSERT INTO paper_schema(key, value) VALUES('schema_version', '3');
                INSERT INTO paper_account_state(account_id, version, updated_at, state_json)
                VALUES('default', 1, 100, '{}');
                """
            )
            for order in orders:
                connection.execute(
                    """
                    INSERT INTO paper_lifecycle_orders(
                        order_id, idempotency_key, symbol, side, state,
                        risk_request_id, market_snapshot_id, strategy_id, run_id,
                        created_at, updated_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, '', '', ?, ?, ?, ?)
                    """,
                    (
                        order["order_id"],
                        order["idempotency_key"],
                        order["symbol"],
                        order["side"],
                        order["state"],
                        order["risk_request_id"],
                        order["run_id"],
                        order["created_at"],
                        order["updated_at"],
                        json.dumps(order, sort_keys=True, separators=(",", ":")),
                    ),
                )
            connection.commit()
        return orders

    def test_all_runtime_ledgers_remain_byte_identical_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            now_ms = lambda: 1_780_000_000_000

            paper_path = root / "paper.sqlite3"
            portfolio_paper_path = root / "portfolio_paper.sqlite"
            audit_path = root / "audit.jsonl"
            mutation_path = root / "mutation.sqlite3"
            strategy_path = root / "strategy.sqlite3"
            research_path = root / "research.sqlite3"
            experiment_path = root / "experiments.sqlite3"
            corporate_path = root / "corporate.sqlite"
            revision_path = root / "revisions.sqlite"
            matrix_registry_path = root / "matrix_registry.sqlite3"

            PaperLedger(db_path=paper_path, now_ms=now_ms)
            portfolio_writer = PortfolioPaperLedger(db_path=portfolio_paper_path, now_ms=now_ms)
            portfolio_writer.initialize(0.0, simulation_enabled=False)
            AuditLog(path=audit_path, ensure_runtime=lambda: root.mkdir(exist_ok=True), now_ms=now_ms)
            MutationJournal(db_path=mutation_path, now_ms=now_ms)
            StrategyPipeline(db_path=strategy_path, now_ms=now_ms)
            ResearchBridge(db_path=research_path, now_ms=now_ms)
            PortfolioExperimentRegistry(db_path=experiment_path, now_ms=now_ms)
            CorporateActionLedger(corporate_path, now_ms)
            MarketDataRevisionLedger(revision_path, now_ms)
            StrategyMatrixRegistrationStore(db_path=matrix_registry_path, now_ms=now_ms)

            before = self._snapshot(root)
            self.assertEqual(len(before), 10)

            paper = PaperLedger(db_path=paper_path, now_ms=now_ms, read_only=True)
            portfolio = PortfolioPaperLedger(db_path=portfolio_paper_path, now_ms=now_ms, read_only=True)
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

            paper.summary()
            portfolio.mark_to_market()
            audit.summary()
            mutation.summary()
            strategy.snapshot()
            research.list()
            experiments.summary()
            corporate.summary()
            revisions.summary()
            matrix_registry.audit()

            blocked_calls = [
                lambda: paper.migrate_legacy({}),
                lambda: portfolio.initialize(0.0),
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

    def test_missing_read_only_database_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.sqlite"
            ledger = PaperLedger(db_path=path, now_ms=lambda: 1, read_only=True)
            self.assertEqual(ledger.load_account(), {})
            summary = ledger.summary()
            self.assertFalse(summary["ok"])
            self.assertEqual(summary["status"], "DATABASE_MISSING")
            self.assertEqual(summary["schema_compatibility"], "BLOCK")
            self.assertFalse(summary["restart_ready"])
            self.assertFalse(summary["paper_authorized"])
            self.assertFalse(summary["live_order_allowed"])
            self.assertFalse(path.exists())

    def test_legacy_paper_schema_restores_in_memory_without_mutating_database(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "legacy-paper.sqlite3"
            self._create_legacy_paper_database(path)
            before = self._snapshot(root)

            ledger = PaperLedger(db_path=path, now_ms=lambda: 200, read_only=True)
            orders = ledger.load_lifecycle_orders()
            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0]["account_id"], "default")
            with closing(sqlite3.connect(
                f"{path.resolve().as_uri()}?mode=ro&immutable=1",
                uri=True,
            )) as connection:
                stored_payload = json.loads(connection.execute(
                    "SELECT payload_json FROM paper_lifecycle_orders LIMIT 1"
                ).fetchone()[0])
            self.assertNotIn("account_id", stored_payload)
            self.assertEqual(ledger.get_lifecycle_order("legacy-order-1"), orders[0])
            self.assertFalse(ledger.is_order_applied("legacy-order-1"))
            self.assertEqual(ledger.load_run_orders("legacy-run"), orders)
            self.assertEqual(
                ledger.find_by_idempotency_key("legacy-key-legacy-order-1"),
                orders[0],
            )
            self.assertEqual(ledger.find_by_risk_request_id("legacy-risk-1"), orders[0])
            self.assertEqual(ledger.run_metrics("legacy-run")["order_count"], 1)

            summary = ledger.summary()
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["schema_version"], 3)
            self.assertEqual(summary["schema_compatibility"], "LEGACY_READ_ONLY_COMPAT")
            self.assertFalse(summary["risk_request_unique"])

            executor = PaperExecutor(
                now_ms=lambda: 200,
                history_loader=ledger.load_lifecycle_orders,
            )
            self.assertEqual(executor.snapshot()["restore_status"], "PASS")
            self.assertEqual(executor.snapshot()["order_count"], 1)

            isolated = PaperLedger(
                db_path=path,
                now_ms=lambda: 200,
                account_id="not-default",
                read_only=True,
            )
            with self.assertRaisesRegex(ValueError, "paper_legacy_schema_account_isolation_block"):
                isolated.load_lifecycle_orders()
            self.assertEqual(isolated.summary()["status"], "ACCOUNT_ISOLATION_BLOCKED")
            self.assertEqual(self._snapshot(root), before)

    def test_legacy_duplicate_risk_request_fails_closed_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "legacy-duplicate.sqlite3"
            self._create_legacy_paper_database(path, duplicate_risk_request=True)
            before = self._snapshot(root)

            ledger = PaperLedger(db_path=path, now_ms=lambda: 200, read_only=True)
            with self.assertRaisesRegex(ValueError, "paper_risk_request_history_conflict"):
                ledger.find_by_risk_request_id("legacy-risk-1")
            executor = PaperExecutor(
                now_ms=lambda: 200,
                history_loader=ledger.load_lifecycle_orders,
            )
            self.assertEqual(executor.snapshot()["restore_status"], "BLOCK")
            self.assertIn(
                "paper_order_history_risk_request_conflict",
                executor.snapshot()["restore_blockers"],
            )
            self.assertEqual(self._snapshot(root), before)

    def test_writable_legacy_migration_normalizes_payload_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy-writable.sqlite3"
            self._create_legacy_paper_database(path)

            ledger = PaperLedger(db_path=path, now_ms=lambda: 300)
            orders = ledger.load_lifecycle_orders()
            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0]["account_id"], "default")
            summary = ledger.summary()
            self.assertEqual(summary["schema_version"], PaperLedger.SCHEMA_VERSION)
            self.assertEqual(summary["schema_compatibility"], "CURRENT")
            self.assertTrue(summary["risk_request_unique"])

            with closing(sqlite3.connect(path)) as connection:
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        "PRAGMA table_info(paper_lifecycle_orders)"
                    ).fetchall()
                }
                stored_payload = json.loads(connection.execute(
                    "SELECT payload_json FROM paper_lifecycle_orders LIMIT 1"
                ).fetchone()[0])
            self.assertIn("account_id", columns)
            self.assertEqual(stored_payload["account_id"], "default")

            executor = PaperExecutor(
                now_ms=lambda: 300,
                history_loader=ledger.load_lifecycle_orders,
                order_writer=ledger.record_lifecycle_order,
            )
            self.assertEqual(executor.snapshot()["restore_status"], "PASS")
            self.assertTrue(executor.snapshot()["restart_ready"])

    def test_incomplete_read_only_paper_schema_reports_block_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "incomplete-paper.sqlite3"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "CREATE TABLE paper_schema (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO paper_schema(key, value) VALUES('schema_version', '1')"
                )
                connection.commit()
            before = self._snapshot(root)
            ledger = PaperLedger(db_path=path, now_ms=lambda: 200, read_only=True)
            summary = ledger.summary()
            self.assertFalse(summary["ok"])
            self.assertEqual(summary["status"], "SCHEMA_MISSING")
            self.assertIn("paper_lifecycle_orders", summary["missing_tables"])
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
