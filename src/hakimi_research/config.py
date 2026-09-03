from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONFIG_SCHEMA_VERSION = "research-config-v1"
_NATIVE_PATH_TYPE = type(Path())
_TOP_LEVEL_FIELDS = frozenset({
    "name",
    "mode",
    "market",
    "symbol",
    "timeframe",
    "initial_cash",
    "data",
    "strategy",
    "risk",
    "execution",
    "logging",
})
_SECTION_FIELDS = {
    "data": frozenset({"provider", "history_limit", "csv_path", "cache_dir", "use_cache"}),
    "strategy": frozenset({"name", "params"}),
    "risk": frozenset({
        "max_position_pct",
        "max_single_loss_pct",
        "max_daily_loss_pct",
        "max_leverage",
        "min_cash_pct",
    }),
    "execution": frozenset({
        "broker",
        "exchange",
        "fee_rate",
        "slippage_pct",
        "poll_seconds",
        "live_trading_enabled",
    }),
    "logging": frozenset({"level", "log_dir"}),
}


def _is_exact_native_json(value: Any) -> bool:
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_is_exact_native_json(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_exact_native_json(item)
            for key, item in value.items()
        )
    return False


def _require_text(value: Any, field_name: str, *, allow_empty: bool = False) -> None:
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise ValueError(f"research_config_{field_name}_exact_text_required")


def _require_bool(value: Any, field_name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"research_config_{field_name}_exact_bool_required")


def _require_positive_int(value: Any, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"research_config_{field_name}_positive_int_required")


def _require_number(
    value: Any,
    field_name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strictly_positive: bool = False,
) -> None:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"research_config_{field_name}_exact_finite_number_required")
    numeric = float(value)
    if strictly_positive and numeric <= 0:
        raise ValueError(f"research_config_{field_name}_positive_number_required")
    if minimum is not None and numeric < minimum:
        raise ValueError(f"research_config_{field_name}_below_minimum")
    if maximum is not None and numeric > maximum:
        raise ValueError(f"research_config_{field_name}_above_maximum")


@dataclass
class DataConfig:
    provider: str = "csv"
    history_limit: int = 500
    csv_path: str = ""
    cache_dir: str = ""
    use_cache: bool = False

    def __post_init__(self) -> None:
        _validate_data_config(self, allow_synthetic=True)


@dataclass
class StrategyConfig:
    name: str = "dual_ma"
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.name, "strategy_name")
        if type(self.params) is not dict or not _is_exact_native_json(self.params):
            raise ValueError("research_config_strategy_params_exact_native_dict_required")


@dataclass
class RiskConfig:
    max_position_pct: float = 0.35
    max_single_loss_pct: float = 0.03
    max_daily_loss_pct: float = 0.05
    max_leverage: float = 2.0
    min_cash_pct: float = 0.05

    def __post_init__(self) -> None:
        _validate_risk_config(self)


@dataclass
class ExecutionConfig:
    broker: str = "research_simulator"
    exchange: str = "disabled"
    fee_rate: float = 0.0008
    slippage_pct: float = 0.0005
    poll_seconds: int = 5
    live_trading_enabled: bool = False

    def __post_init__(self) -> None:
        _validate_execution_config(self)


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "runtime/logs"

    def __post_init__(self) -> None:
        _require_text(self.level, "logging_level")
        _require_text(self.log_dir, "logging_log_dir", allow_empty=True)


@dataclass
class BotConfig:
    name: str = "quant_bot"
    mode: str = "backtest"
    market: str = "crypto"
    symbol: str = "BTC-USDT"
    timeframe: str = "1h"
    initial_cash: float = 10000.0
    data: DataConfig = field(default_factory=DataConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def __post_init__(self) -> None:
        validate_research_config(self, allow_synthetic=True)

    @classmethod
    def from_file(cls, path: str | Path) -> "BotConfig":
        raw = _read_config_document(path)
        if raw.get("mode") == "optimize" or "optimizer" in raw:
            raise ValueError(
                "Legacy optimizer configuration is archived and permanently disabled "
                "in the research-only product."
            )
        unknown = set(raw).difference(_TOP_LEVEL_FIELDS)
        if unknown:
            raise ValueError("research_config_unknown_top_level_fields")
        mode = raw.get("mode", "backtest")
        if mode != "backtest":
            raise ValueError(
                "Archived execution configuration is rejected by the research-only product."
            )
        sections = {
            name: _read_section(raw, name)
            for name in ("data", "strategy", "risk", "execution", "logging")
        }
        data_raw = sections["data"]
        if data_raw.get("provider", "csv") == "synthetic":
            raise ValueError("research_config_synthetic_provider_is_test_only")
        execution_raw = sections["execution"]
        if execution_raw.get("broker", "research_simulator") != "research_simulator":
            raise ValueError("research_config_archived_broker_rejected")
        if execution_raw.get("exchange", "disabled") != "disabled":
            raise ValueError("research_config_execution_exchange_must_be_disabled")
        if execution_raw.get("live_trading_enabled", False) is not False:
            raise ValueError("research_config_live_trading_must_be_false")
        try:
            return cls(
                name=raw.get("name", "quant_bot"),
                mode=mode,
                market=raw.get("market", "crypto"),
                symbol=raw.get("symbol", "BTC-USDT"),
                timeframe=raw.get("timeframe", "1h"),
                initial_cash=raw.get("initial_cash", 10000.0),
                data=DataConfig(**data_raw),
                strategy=StrategyConfig(**sections["strategy"]),
                risk=RiskConfig(**sections["risk"]),
                execution=ExecutionConfig(**execution_raw),
                logging=LoggingConfig(**sections["logging"]),
            )
        except TypeError as exc:
            raise ValueError("research_config_field_shape_invalid") from exc


def _validate_data_config(value: Any, *, allow_synthetic: bool) -> None:
    if type(value) is not DataConfig:
        raise ValueError("research_config_data_exact_type_required")
    _require_text(value.provider, "data_provider")
    allowed = {"csv", "okx"}
    if allow_synthetic:
        allowed.add("synthetic")
    if value.provider not in allowed:
        raise ValueError("research_config_data_provider_invalid")
    _require_positive_int(value.history_limit, "history_limit")
    _require_text(value.csv_path, "csv_path", allow_empty=True)
    _require_text(value.cache_dir, "cache_dir", allow_empty=True)
    _require_bool(value.use_cache, "use_cache")


def _validate_risk_config(value: Any) -> None:
    if type(value) is not RiskConfig:
        raise ValueError("research_config_risk_exact_type_required")
    for field_name in (
        "max_position_pct",
        "max_single_loss_pct",
        "max_daily_loss_pct",
        "min_cash_pct",
    ):
        _require_number(getattr(value, field_name), field_name, minimum=0.0, maximum=1.0)
    _require_number(value.max_leverage, "max_leverage", strictly_positive=True)


def _validate_execution_config(value: Any) -> None:
    if type(value) is not ExecutionConfig:
        raise ValueError("research_config_execution_exact_type_required")
    if type(value.broker) is not str or value.broker != "research_simulator":
        raise ValueError("research_config_execution_broker_must_be_research_simulator")
    if type(value.exchange) is not str or value.exchange != "disabled":
        raise ValueError("research_config_execution_exchange_must_be_disabled")
    _require_number(value.fee_rate, "fee_rate", minimum=0.0, maximum=1.0)
    _require_number(value.slippage_pct, "slippage_pct", minimum=0.0, maximum=1.0)
    _require_positive_int(value.poll_seconds, "poll_seconds")
    if value.live_trading_enabled is not False:
        raise ValueError("research_config_live_trading_must_be_false")


def validate_research_config(
    value: Any,
    *,
    allow_synthetic: bool = True,
) -> BotConfig:
    if type(allow_synthetic) is not bool:
        raise ValueError("research_config_allow_synthetic_exact_bool_required")
    if type(value) is not BotConfig:
        raise ValueError("research_config_bot_exact_type_required")
    for field_name in ("name", "market", "symbol", "timeframe"):
        _require_text(getattr(value, field_name), field_name)
    if type(value.mode) is not str or value.mode != "backtest":
        raise ValueError("research_config_mode_must_be_backtest")
    _require_number(value.initial_cash, "initial_cash", strictly_positive=True)
    _validate_data_config(value.data, allow_synthetic=allow_synthetic)
    if type(value.strategy) is not StrategyConfig:
        raise ValueError("research_config_strategy_exact_type_required")
    value.strategy.__post_init__()
    _validate_risk_config(value.risk)
    _validate_execution_config(value.execution)
    if type(value.logging) is not LoggingConfig:
        raise ValueError("research_config_logging_exact_type_required")
    value.logging.__post_init__()
    return value


def _read_config_document(path: str | Path) -> dict[str, Any]:
    if type(path) is str:
        if not path or path != path.strip():
            raise ValueError("research_config_path_invalid")
        resolved = Path(path)
    elif type(path) is _NATIVE_PATH_TYPE:
        resolved = path
    else:
        raise ValueError("research_config_path_exact_native_required")
    try:
        raw = json.loads(
            resolved.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"research_config_read_failed:{type(exc).__name__}") from exc
    if type(raw) is not dict or not _is_exact_native_json(raw):
        raise ValueError("research_config_document_exact_native_dict_required")
    return raw


def _reject_json_constant(_value: str) -> None:
    raise ValueError("research_config_nonfinite_json_rejected")


def _read_section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if type(value) is not dict:
        raise ValueError(f"research_config_{name}_exact_dict_required")
    if set(value).difference(_SECTION_FIELDS[name]):
        raise ValueError(f"research_config_{name}_unknown_fields")
    return value


__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "BotConfig",
    "DataConfig",
    "ExecutionConfig",
    "LoggingConfig",
    "RiskConfig",
    "StrategyConfig",
    "validate_research_config",
]
