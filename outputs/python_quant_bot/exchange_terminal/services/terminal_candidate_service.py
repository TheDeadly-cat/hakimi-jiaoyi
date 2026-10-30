"""Bind current-rule explanations to server-verified saved native inputs.

The HTTP owner checks the current runtime guard before this derived read.
Historical report reads remain independent of that new-computation guard.
"""
from copy import deepcopy
from datetime import datetime, timezone

from . import indicator_math
from .terminal_research import ENGINE_ID, _engine_source_identity, _fields, validate_terminal_strategy_params
from .terminal_strategy_candidates import CATALOG_ORDER, diagnose_strategy, recommend_candidates


def strategy_candidates(service, payload):
    _fields(payload, {"input_id", "strategy_id", "strategy_params", "cutoff_session", "position_context"},
            {"input_id", "position_context"})
    if "strategy_params" in payload and "strategy_id" not in payload:
        raise ValueError("candidate_parameter_overrides_require_one_strategy")
    data = service._input(payload["input_id"])
    if not data.get("rows"):
        raise ValueError("candidate_saved_history_required")
    cutoff = payload.get("cutoff_session", data["rows"][-1]["date"])
    observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    catalog = [item for item in service._catalog()["items"] if item["id"] in CATALOG_ORDER
               and item.get("capability", {}).get("new_research_allowed") is True
               and item.get("capability", {}).get("backtest_supported") is True]
    if "strategy_id" in payload:
        catalog = [item for item in catalog if item["id"] == payload["strategy_id"]]
    if not catalog:
        raise ValueError("candidate_current_research_strategy_unavailable")
    indicator_math.assert_loaded_source_current()
    sources = _engine_source_identity()
    diagnostics = []
    for item in catalog:
        params = validate_terminal_strategy_params(item, payload.get("strategy_params", {}))
        spec = {"id": item["id"], "name": item.get("name", item["id"]), "params": params,
                "engine_id": ENGINE_ID, "fingerprint": service.fingerprint(item["id"], deepcopy(params)),
                "engine_source_identity": sources}
        diagnostics.append(diagnose_strategy(data, spec, cutoff_session=cutoff, observed_at=observed,
                                             position_context=payload["position_context"]))
    if _engine_source_identity() != sources:
        raise ValueError("candidate_source_changed_restart_required")
    indicator_math.assert_loaded_source_current()
    result = recommend_candidates(diagnostics)
    result.update(read_only=True, input_id=data["id"], cutoff_session=cutoff,
                  interpretation="检查已保存行情截止日的真实规则条件；不创建回测、任务或订单。")
    return result
