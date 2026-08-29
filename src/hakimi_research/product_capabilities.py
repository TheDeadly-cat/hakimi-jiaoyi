from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
