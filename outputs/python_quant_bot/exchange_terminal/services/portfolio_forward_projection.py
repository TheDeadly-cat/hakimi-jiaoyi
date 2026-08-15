from __future__ import annotations

from typing import Any

from .execution_authority import authority_violations, sanitize_authority_claims
from .portfolio_forward_scheduler import build_forward_observation_dashboard
from .portfolio_forward_statistical_maturity import (
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
    build_portfolio_forward_statistical_maturity,
)


PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V5_SCHEMA_VERSION = (
    "portfolio-forward-dashboard-v5"
)
PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V6_SCHEMA_VERSION = (
    "portfolio-forward-dashboard-v6"
)
PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION = (
    "portfolio-forward-dashboard-v7"
)
PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION = (
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION
)


def build_portfolio_forward_status_projection(
    payload: dict[str, Any],
    *,
    observed_now_ms: int,
    live_trading_hard_block: bool,
    observer_artifact_evidence: dict[str, Any] | None = None,
    active_candidate: dict[str, Any] | None = None,
    observer_status: dict[str, Any] | None = None,
    performance_status: dict[str, Any] | None = None,
    backup_status: dict[str, Any] | None = None,
    watchdog_status: dict[str, Any] | None = None,
    backup_read_status: str = "MISSING",
    watchdog_read_status: str = "MISSING",
    dashboard_schema_version: str = PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Attach the fixed authority envelope and read-only dashboard projection."""

    result = {
        **payload,
        "read_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    operational_dashboard = build_forward_observation_dashboard(
        result,
        now_ms=observed_now_ms,
        live_trading_hard_block=live_trading_hard_block is True,
        observer_artifact_evidence=observer_artifact_evidence,
    )
    dashboard_route_invalid = dashboard_schema_version not in {
        PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V5_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V6_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
    }
    if dashboard_route_invalid:
        dashboard_schema_version = PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION
        active_candidate = None
        observer_status = None
        performance_status = None
    maturity_kwargs = {
        "active_candidate": active_candidate,
        "observer_status": observer_status,
        "performance_status": performance_status,
        "backup_status": backup_status,
        "watchdog_status": watchdog_status,
        "backup_read_status": backup_read_status,
        "watchdog_read_status": watchdog_read_status,
        "observed_now_ms": observed_now_ms,
    }
    if dashboard_schema_version == PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION:
        statistical_maturity = build_portfolio_forward_statistical_maturity(
            **maturity_kwargs,
            maturity_schema_version=PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        )
    else:
        statistical_maturity = build_portfolio_forward_statistical_maturity(
            **{
                **maturity_kwargs,
                "active_candidate": None,
                "observer_status": None,
                "performance_status": None,
            },
            maturity_schema_version=PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
        )
    routed_dashboard = dict(operational_dashboard)
    if dashboard_route_invalid:
        routed_dashboard["status"] = "BLOCK"
        routed_dashboard["blockers"] = list(dict.fromkeys([
            *list(routed_dashboard.get("blockers") or []),
            "portfolio_forward_dashboard_schema_unsupported",
        ]))
    elif dashboard_schema_version != PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION:
        routed_dashboard["status"] = "BLOCK"
        routed_dashboard["blockers"] = list(dict.fromkeys([
            *list(routed_dashboard.get("blockers") or []),
            "portfolio_forward_dashboard_legacy_maturity_not_current",
        ]))
    result["incremental_observation"] = {
        **routed_dashboard,
        "schema_version": dashboard_schema_version,
        "statistical_maturity": statistical_maturity,
    }
    sanitized, _sanitized_paths = sanitize_authority_claims(
        result,
        path="portfolio_forward",
    )
    if authority_violations(sanitized):
        safe_maturity_kwargs = {
            "active_candidate": None,
            "observer_status": None,
            "performance_status": None,
            "observed_now_ms": observed_now_ms,
        }
        if dashboard_schema_version == PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION:
            safe_maturity = build_portfolio_forward_statistical_maturity(
                **safe_maturity_kwargs,
                maturity_schema_version=PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
            )
        else:
            safe_maturity = build_portfolio_forward_statistical_maturity(
                **safe_maturity_kwargs,
                maturity_schema_version=PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
            )
        return {
            "status": "BLOCK",
            "blockers": ["portfolio_forward_projection_authority_blocked"],
            "read_only": True,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "incremental_observation": {
                "schema_version": dashboard_schema_version,
                "status": "BLOCK",
                "read_only": True,
                "observation_only": True,
                "simulation_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
                "statistical_maturity": safe_maturity,
            },
        }
    return dict(sanitized)
