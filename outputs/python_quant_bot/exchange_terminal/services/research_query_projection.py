from __future__ import annotations

from typing import Any


def build_research_context_projection(
    *,
    contract: dict[str, Any],
    market: dict[str, Any],
    research_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the Trading Analysis context response from completed queries."""

    return {
        "ok": True,
        "contract": contract,
        "market": market,
        "research_summaries": research_summaries,
        "live_order_allowed": False,
        "read_only": True,
    }


def build_research_summaries_projection(
    *,
    schema: dict[str, Any],
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the ResearchBrief query response from completed queries."""

    return {
        "ok": True,
        "schema": schema,
        "summaries": summaries,
        "live_order_allowed": False,
        "read_only": True,
    }
