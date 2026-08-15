from __future__ import annotations

from typing import Any

from .execution_authority import authority_violations, sanitize_authority_claims


_AUTHORITY_POSTCONDITION_ERROR = (
    "strategy_backtest_preview_authority_postcondition_failed"
)


def build_strategy_backtest_preview_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the final read-only preview response without mutating the report."""

    source = report if isinstance(report, dict) else {}
    projected, sanitized_paths = sanitize_authority_claims(source, path="report")
    payload = dict(projected)
    payload.update(
        {
            "preview": True,
            "pipeline_run": None,
            "historical_backtest_only": True,
            "profitability_proven": False,
            "performance_claim_allowed": False,
            "parameter_selection_allowed": False,
            "automatic_paper_activation_allowed": False,
            "execution_allowed": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    )
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    if authority_violations(payload):
        return build_strategy_backtest_preview_error(
            _AUTHORITY_POSTCONDITION_ERROR
        )
    return payload


def build_strategy_backtest_preview_error(error: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": str(error),
        "preview": True,
        "pipeline_run": None,
        "historical_backtest_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "execution_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
