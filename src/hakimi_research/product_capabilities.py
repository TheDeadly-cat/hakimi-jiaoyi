from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from hakimi_research.capability_definition import build_product_capability_definition


PRODUCT_CAPABILITY_DEFINITION_RESOURCE = (
    "hakimi_research/contracts/product-capabilities.json"
)
_DEFINITION_SCHEMA_VERSION = "product-capability-definition-v1"
_PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION = "product-capability-catalog-v2"
_CAPABILITY_SCHEMA_VERSION = "capability-v1"
_SAFE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SAFE_COMMAND_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_ALLOWED_STATUSES = frozenset({"Supported", "Experimental", "Archived", "Disabled"})
_LOCKED_AUTHORITY = {
    "schema_version": _CAPABILITY_SCHEMA_VERSION,
    "product_mode": "research_only",
    "research_only": True,
    "paper_allowed": False,
    "live_allowed": False,
}
_LOCKED_CAPABILITY_STATUSES = {
    "parameter_optimization": "Archived",
    "paper_execution": "Archived",
    "live_execution": "Archived",
    "order_entry": "Disabled",
}
_LOCKED_CLI_BINDINGS = {
    "optimize": "parameter_optimization",
    "paper": "paper_execution",
}


def _exact_dict(value: Any, fields: set[str]) -> bool:
    return type(value) is dict and set(value) == fields


def _load_product_capability_definition() -> dict[str, Any]:
    raw = build_product_capability_definition()

    if not _exact_dict(raw, {"$schema", "definition_schema_version", "catalog"}):
        raise RuntimeError("product_capability_definition_shape_invalid")
    if raw["$schema"] != "./product-capabilities.schema.json":
        raise RuntimeError("product_capability_definition_schema_reference_invalid")
    if raw["definition_schema_version"] != _DEFINITION_SCHEMA_VERSION:
        raise RuntimeError("product_capability_definition_version_invalid")

    catalog = raw["catalog"]
    if not _exact_dict(
        catalog,
        {
            "schema_version",
            "product_mode",
            "authority",
            "capabilities",
            "cli_bindings",
        },
    ):
        raise RuntimeError("product_capability_definition_catalog_shape_invalid")
    if catalog["schema_version"] != _PRODUCT_CAPABILITY_CATALOG_SCHEMA_VERSION:
        raise RuntimeError("product_capability_definition_catalog_version_invalid")
    if catalog["product_mode"] != "research_only":
        raise RuntimeError("product_capability_definition_product_mode_invalid")
    authority = catalog["authority"]
    if not _exact_dict(authority, set(_LOCKED_AUTHORITY)) or any(
        type(authority[field]) is not type(expected) or authority[field] != expected
        for field, expected in _LOCKED_AUTHORITY.items()
    ):
        raise RuntimeError("product_capability_definition_authority_invalid")

    capabilities = catalog["capabilities"]
    if type(capabilities) is not list or not capabilities:
        raise RuntimeError("product_capability_definition_capabilities_invalid")
    capability_items: list[tuple[str, str]] = []
    for item in capabilities:
        if not _exact_dict(item, {"name", "status"}):
            raise RuntimeError("product_capability_definition_capability_shape_invalid")
        name = item["name"]
        status = item["status"]
        if type(name) is not str or _SAFE_NAME_RE.fullmatch(name) is None:
            raise RuntimeError("product_capability_definition_capability_name_invalid")
        if type(status) is not str or status not in _ALLOWED_STATUSES:
            raise RuntimeError("product_capability_definition_capability_status_invalid")
        capability_items.append((name, status))
    if len({name for name, _status in capability_items}) != len(capability_items):
        raise RuntimeError("product_capability_definition_capability_duplicate")

    capability_statuses = dict(capability_items)
    for name, expected_status in _LOCKED_CAPABILITY_STATUSES.items():
        if capability_statuses.get(name) != expected_status:
            raise RuntimeError("product_capability_definition_execution_lock_invalid")

    cli_bindings = catalog["cli_bindings"]
    if type(cli_bindings) is not list or not cli_bindings:
        raise RuntimeError("product_capability_definition_cli_bindings_invalid")
    binding_items: list[tuple[str, str]] = []
    for item in cli_bindings:
        if not _exact_dict(item, {"command", "capability"}):
            raise RuntimeError("product_capability_definition_cli_binding_shape_invalid")
        command = item["command"]
        capability = item["capability"]
        if type(command) is not str or _SAFE_COMMAND_RE.fullmatch(command) is None:
            raise RuntimeError("product_capability_definition_cli_command_invalid")
        if type(capability) is not str or capability not in capability_statuses:
            raise RuntimeError("product_capability_definition_cli_capability_invalid")
        binding_items.append((command, capability))
    if len({command for command, _capability in binding_items}) != len(binding_items):
        raise RuntimeError("product_capability_definition_cli_command_duplicate")

    bindings = dict(binding_items)
    for command, expected_capability in _LOCKED_CLI_BINDINGS.items():
        if bindings.get(command) != expected_capability:
            raise RuntimeError("product_capability_definition_archived_cli_lock_invalid")

    return {
        "capability_items": tuple(capability_items),
        "cli_bindings": tuple(binding_items),
    }


_PRODUCT_CAPABILITY_DEFINITION = _load_product_capability_definition()
_PRODUCT_CAPABILITY_ITEMS = _PRODUCT_CAPABILITY_DEFINITION["capability_items"]
_PRODUCT_CLI_BINDINGS = _PRODUCT_CAPABILITY_DEFINITION["cli_bindings"]


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
