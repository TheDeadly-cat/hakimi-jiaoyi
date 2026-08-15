from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
import unicodedata


_LOCALIZED_EXECUTION_AUTHORITY_FIELDS = frozenset({
    "可下单",
    "已授权",
    "实盘授权",
})
EXECUTION_AUTHORITY_FIELDS = frozenset({
    "armed",
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "direction_signal_allowed",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "paper_authorized",
    "live_trading_allowed",
    "live_trading_enabled",
    "mission_authorized",
    "order_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "parameter_selection_authority",
    "performance_claim_allowed",
    "performance_claim_proven",
    "profitability_proven",
    "role_assignment_allowed",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
}) | _LOCALIZED_EXECUTION_AUTHORITY_FIELDS
EXECUTION_AUTHORITY_FIELD_KEYS = frozenset(
    "".join(
        character
        for character in unicodedata.normalize("NFKC", field).casefold()
        if character.isalnum()
    )
    for field in EXECUTION_AUTHORITY_FIELDS
)
_LOCALIZED_EXECUTION_AUTHORITY_FIELD_KEYS = frozenset(
    "".join(
        character
        for character in unicodedata.normalize("NFKC", field).casefold()
        if character.isalnum()
    )
    for field in _LOCALIZED_EXECUTION_AUTHORITY_FIELDS
)


def canonical_authority_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value))
    return "".join(
        character for character in normalized.casefold() if character.isalnum()
    )


def sanitize_authority_claims(
    payload: Any,
    *,
    path: str = "$",
    authority_field_keys: frozenset[str] = EXECUTION_AUTHORITY_FIELD_KEYS,
) -> tuple[Any, list[str]]:
    """Copy a payload while forcing selected authority-like fields to ``False``.

    Field matching uses the same canonical key contract as evidence validation,
    while returned paths retain the original key spelling for auditability.
    Callers may pass a narrower canonical field-key set when their projection
    intentionally preserves other descriptive state. Explicit localized
    execution-authority semantics remain mandatory under every narrower set.
    """

    # Local projection allowlists may intentionally narrow the English fields,
    # but explicit localized execution semantics are never optional.
    field_keys = (
        frozenset(authority_field_keys)
        | _LOCALIZED_EXECUTION_AUTHORITY_FIELD_KEYS
    )

    def sanitize(value: Any, *, current_path: str) -> tuple[Any, list[str]]:
        if isinstance(value, Mapping):
            clean: dict[Any, Any] = {}
            paths: list[str] = []
            for key, nested in value.items():
                nested_path = f"{current_path}.{key}"
                if canonical_authority_key(key) in field_keys:
                    clean[key] = False
                    if nested is not False:
                        paths.append(nested_path)
                    continue
                projected, nested_paths = sanitize(
                    nested,
                    current_path=nested_path,
                )
                clean[key] = projected
                paths.extend(nested_paths)
            return clean, paths
        if isinstance(value, list):
            clean_items: list[Any] = []
            paths: list[str] = []
            for index, nested in enumerate(value):
                projected, nested_paths = sanitize(
                    nested,
                    current_path=f"{current_path}[{index}]",
                )
                clean_items.append(projected)
                paths.extend(nested_paths)
            return clean_items, paths
        if isinstance(value, tuple):
            projected, paths = sanitize(list(value), current_path=current_path)
            return tuple(projected), paths
        return deepcopy(value), []

    return sanitize(payload, current_path=path)


def authority_violations(payload: Any, *, path: str = "$") -> list[str]:
    """Return paths whose authority-like field is anything except native ``False``."""

    violations: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if (
                canonical_authority_key(key) in EXECUTION_AUTHORITY_FIELD_KEYS
                and value is not False
            ):
                violations.append(child)
            violations.extend(authority_violations(value, path=child))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            violations.extend(authority_violations(value, path=f"{path}[{index}]"))
    return violations
