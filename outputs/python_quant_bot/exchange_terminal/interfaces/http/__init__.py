"""HTTP transport boundary exports and compatibility module aliases."""

from __future__ import annotations

import sys as _sys

from exchange_terminal.application.ports import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as _readonly_projection_application_port,
)


_LEGACY_READONLY_PROJECTION_BASENAME = (
    "portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1"
)
_LEGACY_READONLY_PROJECTION_MODULE = (
    f"{__name__}.{_LEGACY_READONLY_PROJECTION_BASENAME}"
)

# Keep the ADR0318-pinned legacy file byte-exact on disk while making every
# ordinary import resolve to the canonical application-port module object.
_sys.modules[_LEGACY_READONLY_PROJECTION_MODULE] = (
    _readonly_projection_application_port
)
globals()[_LEGACY_READONLY_PROJECTION_BASENAME] = (
    _readonly_projection_application_port
)

__all__ = [_LEGACY_READONLY_PROJECTION_BASENAME]