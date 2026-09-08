from __future__ import annotations

import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from hakimi_research.strategies.base import StrategyBase
from hakimi_research.strategies.templates import STRATEGY_REGISTRY


STRATEGY_FAMILY_INVENTORY_VERSION = "strategy-family-inventory-v1"
EXPECTED_REGISTERED_STRATEGY_IDS = (
    "bollinger",
    "dual_ma",
    "grid",
    "macd",
    "momentum",
    "rsi",
)
RANGE_MEMBER_IDS = ("bollinger", "grid", "rsi")
TREND_MEMBER_IDS = ("dual_ma", "macd", "momentum")

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")
_AUTHORITY_FIELDS = (
    "profitability_proven",
    "blind_test_complete",
    "paper_authorized",
    "live_authorized",
    "order_entry_authorized",
)


class StrategyFamilyInventoryError(ValueError):
    """Raised when strategy inventory identity or projection is invalid."""


_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


def _fail(path: str, message: str) -> None:
    raise StrategyFamilyInventoryError(f"{path}: {message}")


def _require_exact_native(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "object keys must be exact str values")
            _require_exact_native(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_native(item, f"{path}[{index}]")
        return
    if value_type in (str, int, bool) or value is None:
        return
    _fail(path, f"unsupported non-native type {value_type.__name__}")


def _canonical_sha256(value: Any, path: str) -> str:
    _require_exact_native(value, path)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _require_strategy_id(value: Any, path: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        _fail(path, "must be an exact canonical strategy identifier")
    return value


def build_strategy_family_inventory(
    registered_strategy_ids: list[str],
) -> dict[str, Any]:
    """Project the real registry into mechanism families without inventing strategies."""

    if type(registered_strategy_ids) is not list:
        _fail("registered_strategy_ids", "must be an exact list")
    ids = [
        _require_strategy_id(item, f"registered_strategy_ids[{index}]")
        for index, item in enumerate(registered_strategy_ids)
    ]
    if len(ids) != len(set(ids)):
        _fail("registered_strategy_ids", "must not contain duplicates")
    ids = sorted(ids)
    registered = set(ids)
    expected = set(EXPECTED_REGISTERED_STRATEGY_IDS)
    missing_registry_ids = sorted(expected - registered)
    unexpected_registry_ids = sorted(registered - expected)

    range_present = [item for item in RANGE_MEMBER_IDS if item in registered]
    range_missing = [item for item in RANGE_MEMBER_IDS if item not in registered]
    trend_present = [item for item in TREND_MEMBER_IDS if item in registered]
    trend_missing = [item for item in TREND_MEMBER_IDS if item not in registered]
    ensemble_aliases = [item for item in ids if "ensemble" in item]

    blockers = ["ENSEMBLE_STRATEGY_NOT_IMPLEMENTED"]
    blockers.extend(f"EXPECTED_STRATEGY_MISSING:{item}" for item in missing_registry_ids)
    blockers.extend(f"UNVERSIONED_STRATEGY_REGISTERED:{item}" for item in unexpected_registry_ids)
    if ensemble_aliases:
        blockers.append("UNVERSIONED_ENSEMBLE_ALIAS_PRESENT")
    blockers = sorted(set(blockers))

    inventory: dict[str, Any] = {
        "schema_version": STRATEGY_FAMILY_INVENTORY_VERSION,
        "status": "GAP",
        "registered_strategy_ids": ids,
        "expected_registered_strategy_ids": list(EXPECTED_REGISTERED_STRATEGY_IDS),
        "missing_registry_ids": missing_registry_ids,
        "unexpected_registry_ids": unexpected_registry_ids,
        "families": [
            {
                "family_id": "RANGE",
                "status": "OBSERVED" if not range_missing else "GAP",
                "registered_member_ids": range_present,
                "missing_member_ids": range_missing,
                "gap_code": None if not range_missing else "RANGE_MEMBERS_INCOMPLETE",
            },
            {
                "family_id": "TREND",
                "status": "OBSERVED" if not trend_missing else "GAP",
                "registered_member_ids": trend_present,
                "missing_member_ids": trend_missing,
                "gap_code": None if not trend_missing else "TREND_MEMBERS_INCOMPLETE",
            },
            {
                "family_id": "ENSEMBLE",
                "status": "GAP",
                "registered_member_ids": ensemble_aliases,
                "missing_member_ids": ["ensemble"],
                "gap_code": "NO_REGISTERED_ENSEMBLE_STRATEGY",
            },
        ],
        "report_fixture": {
            "status": "BLOCK",
            "executable_family_ids": ["RANGE", "TREND"],
            "blocked_family_ids": ["ENSEMBLE"],
            "blockers": list(blockers),
        },
        "blockers": blockers,
        "authority": {field: False for field in _AUTHORITY_FIELDS},
    }
    inventory["inventory_sha256"] = _canonical_sha256(
        inventory,
        "strategy_family_inventory_without_digest",
    )
    return inventory


def build_current_strategy_family_inventory() -> dict[str, Any]:
    """Project the exact read-only canonical strategy registry."""

    if type(STRATEGY_REGISTRY) is not _MAPPING_PROXY_TYPE:
        _fail("STRATEGY_REGISTRY", "must be the exact canonical mappingproxy")
    strategy_ids: list[str] = []
    for strategy_id, strategy_class in STRATEGY_REGISTRY.items():
        if type(strategy_id) is not str:
            _fail("STRATEGY_REGISTRY", "keys must be exact str values")
        if type(strategy_class) is not type or not issubclass(
            strategy_class,
            StrategyBase,
        ):
            _fail(
                f"STRATEGY_REGISTRY.{strategy_id}",
                "value is not a StrategyBase class",
            )
        strategy_ids.append(strategy_id)
    return build_strategy_family_inventory(strategy_ids)


def verify_strategy_family_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the projection from the registered IDs and require exact equality."""

    _require_exact_native(inventory, "strategy_family_inventory")
    if type(inventory) is not dict:
        _fail("strategy_family_inventory", "must be an exact dict")
    if inventory.get("schema_version") != STRATEGY_FAMILY_INVENTORY_VERSION:
        _fail("strategy_family_inventory.schema_version", "schema version mismatch")
    authority = inventory.get("authority")
    if type(authority) is not dict or set(authority) != set(_AUTHORITY_FIELDS):
        _fail("strategy_family_inventory.authority", "authority fields are incomplete")
    for field in _AUTHORITY_FIELDS:
        if type(authority[field]) is not bool or authority[field] is not False:
            _fail(f"strategy_family_inventory.authority.{field}", "must be exact false")
    rebuilt = build_strategy_family_inventory(inventory.get("registered_strategy_ids"))
    if inventory != rebuilt:
        _fail("strategy_family_inventory", "does not match the canonical registry projection")
    return {
        "status": inventory["status"],
        "report_fixture_status": inventory["report_fixture"]["status"],
        "blockers": list(inventory["blockers"]),
    }


__all__ = [
    "EXPECTED_REGISTERED_STRATEGY_IDS",
    "RANGE_MEMBER_IDS",
    "STRATEGY_FAMILY_INVENTORY_VERSION",
    "TREND_MEMBER_IDS",
    "StrategyFamilyInventoryError",
    "build_current_strategy_family_inventory",
    "build_strategy_family_inventory",
    "verify_strategy_family_inventory",
]
