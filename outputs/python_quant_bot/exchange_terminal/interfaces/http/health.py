from __future__ import annotations

from typing import Any

try:
    from application.health_contract import build_research_disabled_payload, build_runtime_health_payload
except ModuleNotFoundError:
    from exchange_terminal.application.health_contract import build_research_disabled_payload, build_runtime_health_payload


def build_health_response(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def build_health_response_from_runtime(
    runtime_build: dict[str, Any],
    paper_snapshot: dict[str, Any],
    *,
    read_only: bool,
    runtime_mutations_allowed: bool,
    live_trading_hard_block: bool,
    guardian_worker_running: bool,
) -> dict[str, Any]:
    return build_runtime_health_payload(
        runtime_build,
        paper_snapshot,
        read_only=read_only,
        runtime_mutations_allowed=runtime_mutations_allowed,
        live_trading_hard_block=live_trading_hard_block,
        guardian_worker_running=guardian_worker_running,
    )


def build_research_disabled_response(paper_snapshot: dict[str, Any]) -> dict[str, Any]:
    return build_research_disabled_payload(paper_snapshot)
