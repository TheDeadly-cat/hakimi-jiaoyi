from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, NoReturn


ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION = "archived-paper-runtime-v1"
LEGACY_ORDER_TYPES = frozenset(
    {"MARKET", "CURRENT", "LIMIT", "POST_ONLY", "IOC", "FOK", "OCO"}
)


def _finite_nonnegative(value: Any) -> float:
    if type(value) not in {int, float}:
        return 0.0
    parsed = float(value)
    return parsed if math.isfinite(parsed) and parsed >= 0 else 0.0


def _archived_write() -> NoReturn:
    raise RuntimeError(
        "Legacy paper execution is archived and permanently disabled in the "
        "research-only product."
    )


@dataclass(frozen=True)
class ArchivedPaperAccount:
    armed: bool = False
    symbol: str = ""
    strategy_id: str = ""
    pipeline_run_id: str = ""
    timeframe: str = ""
    position_qty: float = 0.0
    entry_price: float = 0.0
    last_scale_price: float = 0.0
    order_type: str = "ARCHIVED"
    margin_mode: str = "ARCHIVED"
    direction_mode: str = "LONG_ONLY"
    leverage: float = 1.0
    position_pct: float = 0.0
    reduce_only: bool = True
    max_drawdown_pct: float = 0.0
    trailing_take_pct: float = 0.0
    trailing_stop_pct: float = 0.0
    orders: tuple[dict[str, Any], ...] = ()
    signals: tuple[dict[str, Any], ...] = ()

    def equity(self, _price: Any = 0.0) -> float:
        return 0.0

    def snapshot(self, price: Any = 0.0) -> dict[str, Any]:
        mark_price = _finite_nonnegative(price)
        return {
            "status": "ARCHIVED",
            "source": "ARCHIVED_STATIC_COMPATIBILITY",
            "version": 0,
            "schema_version": ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "armed": False,
            "symbol": "",
            "timeframe": "",
            "strategy": {"id": "", "name": "Archived paper execution", "params": {}},
            "strategy_clock": {"status": "ARCHIVED"},
            "cash": 0.0,
            "available_cash": 0.0,
            "equity": 0.0,
            "equity_curve": [],
            "position_qty": 0.0,
            "position_side": "FLAT",
            "position_value": 0.0,
            "entry_price": 0.0,
            "last_scale_price": 0.0,
            "mark_price": mark_price,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "drawdown_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "maintenance_margin": 0.0,
            "margin_used": 0.0,
            "short_margin": 0.0,
            "liquidation_price": 0.0,
            "order_type": "ARCHIVED",
            "margin_mode": "ARCHIVED",
            "direction_mode": "LONG_ONLY",
            "leverage": 1.0,
            "position_pct": 0.0,
            "reduce_only": True,
            "take_profit_pct": 0.0,
            "take_profit_price": 0.0,
            "stop_loss_pct": 0.0,
            "stop_loss_price": 0.0,
            "trailing_take_enabled": False,
            "trailing_take_pct": 0.0,
            "trailing_take_price": 0.0,
            "trailing_stop_enabled": False,
            "trailing_stop_pct": 0.0,
            "trailing_stop_price": 0.0,
            "trailing_peak_price": 0.0,
            "risk_source": "ARCHIVED",
            "risk_status": "ARCHIVED",
            "risk_value_mode": "ARCHIVED",
            "orders": [],
            "signals": [],
            "conditional_orders": [],
            "pending_signal": {},
            "ai_analysis": {},
            "last_attempt_bar_ts": 0,
            "last_fill_bar_ts": 0,
            "last_poll_ms": 0,
            "last_seen_bar_ts": 0,
            "last_signal_bar_ts": 0,
        }

    def emergency_stop(self, price: Any = 0.0, reason: str = "") -> dict[str, Any]:
        payload = self.snapshot(price)
        payload["archive_reason"] = str(reason or "archived")
        return payload

    def evaluate(self, price: Any = 0.0) -> dict[str, Any]:
        return self.snapshot(price)

    def process_strategy_bars(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        _archived_write()


@dataclass(frozen=True)
class ArchivedPaperLedger:
    def summary(self) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "ARCHIVED",
            "backend": "ARCHIVED_STATIC",
            "db_path": "",
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "account_id": "archived",
            "account_version": 0,
            "schema_version": ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION,
            "supported_schema_version": ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION,
            "schema_compatibility": "ARCHIVED",
            "restart_ready": False,
            "risk_request_unique": True,
            "missing_tables": [],
            "order_count": 0,
            "fill_count": 0,
            "snapshot_count": 0,
            "pending_settlement_count": 0,
            "updated_at": 0,
        }

    def run_metrics(self, run_id: Any) -> dict[str, Any]:
        return {
            "run_id": str(run_id or ""),
            "order_count": 0,
            "filled_order_count": 0,
            "closed_trade_count": 0,
            "first_order_at": 0,
            "last_order_at": 0,
        }

    def get_lifecycle_order(self, _order_id: Any) -> None:
        return None

    def load_run_orders(self, _run_id: Any, _limit: Any = 0) -> list[dict[str, Any]]:
        return []

    def load_lifecycle_orders(self, _limit: Any = 0) -> list[dict[str, Any]]:
        return []

    def find_by_idempotency_key(self, _key: Any) -> None:
        return None

    def find_by_risk_request_id(self, _request_id: Any) -> None:
        return None

    def is_order_applied(self, _order_id: Any) -> bool:
        return False

    def save_account(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        _archived_write()

    def record_lifecycle_order(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        _archived_write()


@dataclass(frozen=True)
class ArchivedPaperExecutor:
    def list(self, _limit: Any = 0) -> list[dict[str, Any]]:
        return []

    def snapshot(self) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "ARCHIVED",
            "durability_mode": "ARCHIVED_STATIC",
            "order_count": 0,
            "working_count": 0,
            "counts": {},
            "persistence_failed_count": 0,
            "restart_ready": False,
            "restore_status": "ARCHIVED",
            "restore_error": "",
            "restore_blockers": ["paper_execution_archived"],
            "live_order_allowed": False,
        }

    def submit(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        _archived_write()


@dataclass(frozen=True)
class ArchivedPortfolioPaperLedger:
    def mark_to_market(self, _prices: Any = None) -> dict[str, Any]:
        return {
            "status": "ARCHIVED",
            "schema_version": ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION,
            "account_id": "portfolio-research-archived",
            "version": 0,
            "simulation_enabled": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "cash": 0.0,
            "equity": 0.0,
            "market_value": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "position_count": 0,
            "positions": [],
            "blockers": ["paper_execution_archived"],
            "activation_status": "ARCHIVED",
            "activation_blockers": ["paper_execution_archived"],
            "activation_receipt_hash": "",
            "active_candidate_hash": "",
            "last_price": 0.0,
        }

    def summary(self) -> dict[str, Any]:
        return {**self.mark_to_market(), "path": "", "fill_count": 0}

    def initialize(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        _archived_write()


def build_archived_paper_runtime() -> tuple[
    ArchivedPaperAccount,
    ArchivedPaperLedger,
    ArchivedPaperExecutor,
    ArchivedPortfolioPaperLedger,
    dict[str, Any],
]:
    reconciliation = {
        "ok": False,
        "status": "ARCHIVED",
        "applied": 0,
        "read_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return (
        ArchivedPaperAccount(),
        ArchivedPaperLedger(),
        ArchivedPaperExecutor(),
        ArchivedPortfolioPaperLedger(),
        reconciliation,
    )


__all__ = (
    "ARCHIVED_PAPER_RUNTIME_SCHEMA_VERSION",
    "LEGACY_ORDER_TYPES",
    "ArchivedPaperAccount",
    "ArchivedPaperExecutor",
    "ArchivedPaperLedger",
    "ArchivedPortfolioPaperLedger",
    "build_archived_paper_runtime",
)
