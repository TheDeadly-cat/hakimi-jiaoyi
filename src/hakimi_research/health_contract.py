from __future__ import annotations

from typing import Any

from hakimi_research.product_capabilities import (
    build_product_capability_catalog,
    build_research_only_capability,
)


def build_runtime_health_payload(
    runtime_build: dict[str, Any],
    paper_snapshot: dict[str, Any],
    *,
    read_only: bool,
    runtime_mutations_allowed: bool,
    live_trading_hard_block: bool,
    guardian_worker_running: bool,
) -> dict[str, Any]:
    capability = build_research_only_capability()
    product_capability_catalog = build_product_capability_catalog().to_dict()
    return {
        "ok": runtime_build.get("status") == "PASS" and live_trading_hard_block is True,
        "time": int(runtime_build.get("time", 0)),
        "runtime_build": {
            **{
                key: value
                for key, value in runtime_build.items()
                if key not in {
                    "product_mode",
                    "research_only",
                    "paper_allowed",
                    "live_allowed",
                    "capability",
                    "product_capability_catalog",
                }
            },
            "capability": capability.to_dict(),
            "product_capability_catalog": product_capability_catalog,
        },
        "capability": capability.to_dict(),
        "product_capability_catalog": product_capability_catalog,
        "read_only": bool(read_only),
        "runtime_mutations_allowed": bool(runtime_mutations_allowed),
        "paper_authorized": False,
        "binding_authorized": False,
        "paper_order_allowed": False,
        "automated_paper_order_allowed": False,
        "paper_armed": paper_snapshot.get("armed") is True,
        "live_order_allowed": False,
        "live_trading_hard_block": bool(live_trading_hard_block),
        "guardian_worker_running": bool(guardian_worker_running),
    }


def build_research_disabled_payload(paper_snapshot: dict[str, Any]) -> dict[str, Any]:
    capability = build_research_only_capability()
    return {
        "ok": False,
        "error": "CAPABILITY_DISABLED: 研究模式下 paper 执行已关闭",
        "capability": capability.to_dict(),
        "product_capability_catalog": build_product_capability_catalog().to_dict(),
        "paper": paper_snapshot,
        "paper_order_allowed": False,
        "live_order_allowed": False,
    }
