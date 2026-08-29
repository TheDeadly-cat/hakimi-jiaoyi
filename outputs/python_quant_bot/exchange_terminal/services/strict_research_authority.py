"""Strict fail-closed authority checks for research evidence contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    from services.execution_authority import authority_violations
except ModuleNotFoundError:
    from exchange_terminal.services.execution_authority import authority_violations


EXPLICIT_RESEARCH_AUTHORITY_KEYS = frozenset(
    {
        "current_admission_allowed",
        "current_writer_activation_allowed",
        "formal_registry_activation_allowed",
        "writer_implemented",
        "paper_authorized",
        "live_order_allowed",
    }
)


def _explicit_authority_violations(
    value: Any,
    *,
    path: str,
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if (
                key in EXPLICIT_RESEARCH_AUTHORITY_KEYS
                and nested is not False
            ):
                violations.append(nested_path)
            violations.extend(
                _explicit_authority_violations(nested, path=nested_path)
            )
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            violations.extend(
                _explicit_authority_violations(
                    nested,
                    path=f"{path}[{index}]",
                )
            )
    return violations


def strict_research_authority_violations(
    value: Any,
    *,
    path: str = "$",
) -> list[str]:
    return sorted(
        set(
            authority_violations(value, path=path)
            + _explicit_authority_violations(value, path=path)
        )
    )


def strict_research_authority_invalid(value: Any) -> bool:
    return bool(strict_research_authority_violations(value))
