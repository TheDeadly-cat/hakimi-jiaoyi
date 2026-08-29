from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CAPABILITY_SCHEMA_VERSION = "capability-v1"
_PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION = "product-capability-catalog-v1"
_PRODUCT_CAPABILITY_ITEMS = (
    ("product_capability_catalog", "Supported"),
    ("market_data_research", "Supported"),
    ("historical_backtest", "Supported"),
    ("research_reporting", "Supported"),
    ("strategy_catalog", "Supported"),
    ("local_research_terminal", "Experimental"),
    ("parameter_optimization", "Archived"),
    ("paper_execution", "Archived"),
    ("live_execution", "Archived"),
    ("order_entry", "Disabled"),
)
_PRODUCT_CLI_BINDINGS = (
    ("backtest", "historical_backtest"),
    ("capabilities", "product_capability_catalog"),
    ("list-strategies", "strategy_catalog"),
    ("optimize", "parameter_optimization"),
    ("paper", "paper_execution"),
)
_MANIFEST_SCHEMA_VERSION = "market-data-source-manifest-v1"
_ENVELOPE_SCHEMA_VERSION = "market-data-envelope-v1"
_SOURCE_MARKER_MAX_LENGTH = 256
_ENVELOPE_IDENTITY_MAX_LENGTH = 128
_DECISION_ID_COMPONENT_MAX_LENGTHS = {
    "strategy": 128,
    "symbol": 128,
    "timeframe": 128,
    "candle_close_time": 256,
    "action": 128,
    "strategy_version": 128,
}


@dataclass(frozen=True)
class CapabilityContract:
    product_mode: str = "research_only"
    research_only: bool = True
    paper_allowed: bool = False
    live_allowed: bool = False
    schema_version: str = "capability-v1"

    def __post_init__(self) -> None:
        if self.product_mode != "research_only":
            raise ValueError("capability_contract_product_mode_invalid")
        if self.research_only is not True:
            raise ValueError("capability_contract_research_only_lock_invalid")
        if self.paper_allowed is not False:
            raise ValueError("capability_contract_paper_lock_invalid")
        if self.live_allowed is not False:
            raise ValueError("capability_contract_live_lock_invalid")
        if self.schema_version != _CAPABILITY_SCHEMA_VERSION:
            raise ValueError("capability_contract_schema_invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_mode": self.product_mode,
            "research_only": self.research_only,
            "paper_allowed": self.paper_allowed,
            "live_allowed": self.live_allowed,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ProductCapabilityCatalog:
    product_mode: str = "research_only"
    capability_statuses: tuple[tuple[str, str], ...] = _PRODUCT_CAPABILITY_ITEMS
    cli_bindings: tuple[tuple[str, str], ...] = _PRODUCT_CLI_BINDINGS
    schema_version: str = _PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.product_mode) is not str or self.product_mode != "research_only":
            raise ValueError("product_capability_catalog_product_mode_invalid")
        if (
            type(self.capability_statuses) is not tuple
            or self.capability_statuses != _PRODUCT_CAPABILITY_ITEMS
            or any(
                type(item) is not tuple
                or len(item) != 2
                or any(type(value) is not str for value in item)
                for item in self.capability_statuses
            )
        ):
            raise ValueError("product_capability_catalog_capabilities_invalid")
        if (
            type(self.cli_bindings) is not tuple
            or self.cli_bindings != _PRODUCT_CLI_BINDINGS
            or any(
                type(item) is not tuple
                or len(item) != 2
                or any(type(value) is not str for value in item)
                for item in self.cli_bindings
            )
        ):
            raise ValueError("product_capability_catalog_cli_bindings_invalid")
        if (
            type(self.schema_version) is not str
            or self.schema_version != _PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION
        ):
            raise ValueError("product_capability_catalog_schema_invalid")

    def to_dict(self) -> dict[str, Any]:
        capability_statuses = dict(self.capability_statuses)
        return {
            "schema_version": self.schema_version,
            "product_mode": self.product_mode,
            "capabilities": capability_statuses,
            "cli_commands": {
                command: capability_statuses[capability]
                for command, capability in self.cli_bindings
            },
            "authority": build_research_only_capability().to_dict(),
        }


@dataclass(frozen=True)
class MarketDataSourceManifest:
    provider: str
    real_rows: int
    cache_rows: int
    synthetic_rows: int
    fallback: bool
    complete: bool
    dataset_hash: str
    schema_version: str = "market-data-source-manifest-v1"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider, str)
            or not self.provider
            or self.provider != self.provider.strip()
            or len(self.provider) > _SOURCE_MARKER_MAX_LENGTH
            or any(
                ord(character) < 0x20
                or ord(character) in {0x7F, 0x2028, 0x2029}
                for character in self.provider
            )
        ):
            raise ValueError("market_data_source_manifest_provider_invalid")
        for field in ("real_rows", "cache_rows", "synthetic_rows"):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise ValueError(f"market_data_source_manifest_{field}_invalid")
        if self.cache_rows > self.real_rows:
            raise ValueError("market_data_source_manifest_cache_rows_exceed_real_rows")
        if type(self.fallback) is not bool:
            raise ValueError("market_data_source_manifest_fallback_invalid")
        if type(self.complete) is not bool:
            raise ValueError("market_data_source_manifest_complete_invalid")
        if self.synthetic_rows > 0 and self.fallback is not True:
            raise ValueError("market_data_source_manifest_synthetic_without_fallback")
        if not isinstance(self.dataset_hash, str) or _SHA256_RE.fullmatch(self.dataset_hash) is None:
            raise ValueError("market_data_source_manifest_dataset_hash_invalid")
        if self.schema_version != _MANIFEST_SCHEMA_VERSION:
            raise ValueError("market_data_source_manifest_schema_invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "real_rows": int(self.real_rows),
            "cache_rows": int(self.cache_rows),
            "synthetic_rows": int(self.synthetic_rows),
            "fallback": bool(self.fallback),
            "complete": bool(self.complete),
            "dataset_hash": self.dataset_hash,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MarketDataEnvelope:
    symbol: str
    timeframe: str
    rows: list[dict[str, Any]]
    source_manifest: MarketDataSourceManifest
    research_only: bool = True
    paper_authorized: bool = False
    live_order_allowed: bool = False
    schema_version: str = "market-data-envelope-v1"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str)
            or not self.symbol
            or self.symbol != self.symbol.strip()
            or len(self.symbol) > _ENVELOPE_IDENTITY_MAX_LENGTH
            or "|" in self.symbol
            or any(
                ord(character) < 0x20
                or ord(character) in {0x7F, 0x2028, 0x2029}
                for character in self.symbol
            )
        ):
            raise ValueError("market_data_envelope_symbol_invalid")
        if (
            not isinstance(self.timeframe, str)
            or not self.timeframe
            or self.timeframe != self.timeframe.strip()
            or len(self.timeframe) > _ENVELOPE_IDENTITY_MAX_LENGTH
            or "|" in self.timeframe
            or any(
                ord(character) < 0x20
                or ord(character) in {0x7F, 0x2028, 0x2029}
                for character in self.timeframe
            )
        ):
            raise ValueError("market_data_envelope_timeframe_invalid")
        if not isinstance(self.rows, list) or any(not isinstance(row, Mapping) for row in self.rows):
            raise ValueError("market_data_envelope_rows_invalid")
        if not isinstance(self.source_manifest, MarketDataSourceManifest):
            raise ValueError("market_data_envelope_source_manifest_invalid")
        if self.source_manifest.real_rows + self.source_manifest.synthetic_rows != len(self.rows):
            raise ValueError("market_data_envelope_row_count_mismatch")
        if self.research_only is not True:
            raise ValueError("market_data_envelope_research_only_lock_invalid")
        if self.paper_authorized is not False:
            raise ValueError("market_data_envelope_paper_lock_invalid")
        if self.live_order_allowed is not False:
            raise ValueError("market_data_envelope_live_lock_invalid")
        if self.schema_version != _ENVELOPE_SCHEMA_VERSION:
            raise ValueError("market_data_envelope_schema_invalid")
        object.__setattr__(self, "rows", [dict(row) for row in self.rows])

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "rows": [dict(row) for row in self.rows],
            "source_manifest": self.source_manifest.to_dict(),
            "research_only": self.research_only,
            "paper_authorized": self.paper_authorized,
            "live_order_allowed": self.live_order_allowed,
            "schema_version": self.schema_version,
        }


def _normalize_candle_decision_component(
    value: Any,
    *,
    field: str,
    fallback: str | None,
    case: str | None = None,
    reject_outer_whitespace: bool = False,
) -> str:
    if value is None:
        if fallback is None:
            raise ValueError(f"candle_decision_id_{field}_invalid")
        normalized = fallback
    elif not isinstance(value, str):
        raise ValueError(f"candle_decision_id_{field}_invalid")
    else:
        stripped = value.strip()
        if reject_outer_whitespace and value != stripped:
            raise ValueError(f"candle_decision_id_{field}_invalid")
        if not stripped:
            if fallback is None:
                raise ValueError(f"candle_decision_id_{field}_invalid")
            normalized = fallback
        else:
            normalized = stripped
    if case == "lower":
        normalized = normalized.lower()
    elif case == "upper":
        normalized = normalized.upper()
    if len(normalized) > _DECISION_ID_COMPONENT_MAX_LENGTHS[field]:
        raise ValueError(f"candle_decision_id_{field}_too_long")
    if "|" in normalized or any(
        ord(character) < 0x20 or ord(character) in {0x7F, 0x2028, 0x2029}
        for character in normalized
    ):
        raise ValueError(f"candle_decision_id_{field}_invalid")
    return normalized


def build_candle_decision_id(
    *,
    strategy: str,
    symbol: str,
    timeframe: str,
    candle_close_time: str,
    action: str,
    strategy_version: str | None = None,
) -> str:
    clean_strategy = _normalize_candle_decision_component(
        strategy,
        field="strategy",
        fallback="legacy",
        case="lower",
    )
    clean_symbol = _normalize_candle_decision_component(
        symbol,
        field="symbol",
        fallback="unknown",
        case="lower",
    )
    clean_timeframe = _normalize_candle_decision_component(
        timeframe,
        field="timeframe",
        fallback="unknown",
        case="lower",
    )
    clean_candle_close_time = _normalize_candle_decision_component(
        candle_close_time,
        field="candle_close_time",
        fallback=None,
        reject_outer_whitespace=True,
    )
    clean_action = _normalize_candle_decision_component(
        action,
        field="action",
        fallback="NONE",
        case="upper",
    )
    clean_version = _normalize_candle_decision_component(
        strategy_version,
        field="strategy_version",
        fallback="v1",
    )
    return "|".join([
        f"strategy:{clean_strategy}",
        f"symbol:{clean_symbol}",
        f"timeframe:{clean_timeframe}",
        f"candle:{clean_candle_close_time}",
        f"action:{clean_action}",
        f"version:{clean_version}",
    ])


def build_research_only_capability() -> CapabilityContract:
    return CapabilityContract(
        product_mode="research_only",
        research_only=True,
        paper_allowed=False,
        live_allowed=False,
    )


def build_product_capability_catalog() -> ProductCapabilityCatalog:
    return ProductCapabilityCatalog()


def product_capability_status_for_cli_command(command: Any) -> str | None:
    if type(command) is not str:
        return None
    catalog = build_product_capability_catalog()
    capability = dict(catalog.cli_bindings).get(command)
    if capability is None:
        return None
    return dict(catalog.capability_statuses)[capability]


def supported_cli_commands() -> tuple[str, ...]:
    catalog = build_product_capability_catalog()
    capability_statuses = dict(catalog.capability_statuses)
    return tuple(
        command
        for command, capability in catalog.cli_bindings
        if capability_statuses[capability] == "Supported"
    )
