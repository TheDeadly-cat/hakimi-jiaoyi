from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.strategy_correlation_multiplicity_audit import (
    build_strategy_correlation_multiplicity_audit,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    verify_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    assess_strategy_correlation_multiplicity_binding,
)
from exchange_terminal.services.strategy_correlation_multiplicity_report import (
    build_strategy_correlation_multiplicity_report_evidence,
    verify_strategy_correlation_multiplicity_report_evidence,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
    build_replayed_correlation_cluster_gate,
    verify_correlation_matrix_replay,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
)


_LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})
_COMMON_FINITE_FIELDS = (
    "train_return_pct",
    "validation_return_pct",
    "validation_excess_return_pct",
    "validation_trade_count",
    "validation_max_drawdown_pct",
    "validation_sharpe",
    "validation_drawdown_improvement_pct",
    "validation_sharpe_excess",
    "validation_risk_efficiency_excess",
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _cell_passes_lane(cell: dict[str, Any], lane: str) -> bool:
    metrics = {field: _finite_number(cell.get(field)) for field in _COMMON_FINITE_FIELDS}
    if any(value is None for value in metrics.values()):
        return False
    common_pass = all((
        cell.get("dataset_status") == "PASS",
        cell.get("train_ok") is True,
        cell.get("validation_ok") is True,
        cell.get("fold_stability_status") == "PASS",
        cell.get("cost_sensitivity_status") == "PASS",
        cell.get("lookahead_status") == "PASS",
        metrics["train_return_pct"] > 0,
        metrics["validation_return_pct"] > 0,
        metrics["validation_trade_count"] >= 2,
        metrics["validation_max_drawdown_pct"] < 25,
    ))
    if not common_pass:
        return False
    if lane == "RAW_EXCESS":
        return metrics["validation_excess_return_pct"] > 0
    return all((
        metrics["validation_max_drawdown_pct"] < 15,
        metrics["validation_return_pct"] >= 2,
        metrics["validation_excess_return_pct"] >= -3,
        metrics["validation_drawdown_improvement_pct"] > 0,
        metrics["validation_sharpe_excess"] > 0,
        metrics["validation_risk_efficiency_excess"] > 0,
    ))


def _registered_evaluation(protocol: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if protocol.get("schema_version") != STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION:
        raise ValueError("correlation_research_protocol_v5_required")
    registration = protocol.get("correlation_multiplicity_protocol_registration")
    verification = verify_strategy_correlation_multiplicity_protocol_registration(
        registration
    )
    if verification.get("status") != "PASS" or not isinstance(registration, dict):
        raise ValueError("correlation_research_protocol_registration_invalid")
    source = registration.get("source_protocol_registration")
    evaluations = source.get("evaluations") if isinstance(source, dict) else None
    if not isinstance(evaluations, list) or len(evaluations) != 1:
        raise ValueError("correlation_research_evaluation_cardinality_invalid")
    evaluation = evaluations[0]
    if not isinstance(evaluation, dict) or evaluation.get("lane") not in _LANES:
        raise ValueError("correlation_research_evaluation_invalid")
    return registration, evaluation


def _selection_gate_projection(
    *,
    protocol: dict[str, Any],
    selection_cells: list[dict[str, Any]],
    validation_rankings: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    registration, evaluation = _registered_evaluation(protocol)
    source = dict(registration["source_protocol_registration"])
    preregistration = dict(source["preregistration"])
    strategy_id = str(evaluation.get("strategy_id") or "")
    variant_id = str(evaluation.get("variant_id") or "")
    lane = str(evaluation.get("lane") or "")
    if not isinstance(selection_cells, list) or not isinstance(validation_rankings, list):
        raise ValueError("correlation_research_selection_container_invalid")
    if authority_violations(selection_cells) or authority_violations(validation_rankings):
        raise ValueError("correlation_research_selection_authority_invalid")

    matching_rankings = [
        dict(item)
        for item in validation_rankings
        if isinstance(item, dict)
        and item.get("strategy_id") == strategy_id
        and item.get("variant_id") == variant_id
    ]
    if len(matching_rankings) != 1:
        raise ValueError("correlation_research_ranking_identity_invalid")
    ranking = matching_rankings[0]
    global_lane_pass = all((
        ranking.get("status") == "PASS",
        ranking.get("eligible_for_test") is True,
        ranking.get("selection_lane") == lane,
    ))

    cells_by_symbol: dict[str, dict[str, Any]] = {}
    expected_symbols = list(preregistration.get("symbols") or [])
    for item in selection_cells:
        if not isinstance(item, dict):
            raise ValueError("correlation_research_selection_cell_invalid")
        if item.get("strategy_id") != strategy_id or item.get("variant_id") != variant_id:
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or symbol in cells_by_symbol:
            raise ValueError("correlation_research_selection_cell_identity_invalid")
        cells_by_symbol[symbol] = dict(item)
    if set(cells_by_symbol) != set(expected_symbols):
        raise ValueError("correlation_research_selection_cell_coverage_invalid")

    projected = [
        {
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "symbol": symbol,
            "lane": lane,
            "gate_status": (
                "PASS"
                if global_lane_pass and _cell_passes_lane(cells_by_symbol[symbol], lane)
                else "BLOCK"
            ),
        }
        for symbol in expected_symbols
    ]
    return projected, registration, evaluation


def build_strategy_correlation_research_multiplicity_evidence(
    protocol: dict[str, Any],
    matrix_replay: dict[str, Any],
    selection_cells: list[dict[str, Any]],
    validation_rankings: list[dict[str, Any]],
) -> dict[str, Any]:
    projected_cells, registration, evaluation = _selection_gate_projection(
        protocol=protocol,
        selection_cells=selection_cells,
        validation_rankings=validation_rankings,
    )
    if verify_correlation_matrix_replay(matrix_replay).get("status") != "PASS":
        raise ValueError("correlation_research_matrix_replay_invalid")
    source = dict(registration["source_protocol_registration"])
    completed_input = matrix_replay.get("completed_price_input")
    if not isinstance(completed_input, dict) or any((
        completed_input.get("selection_alignment_input_hash")
        != source.get("selection_alignment_input_hash"),
        completed_input.get("preregistration_hash")
        != dict(source.get("preregistration") or {}).get("preregistration_hash"),
    )):
        raise ValueError("correlation_research_matrix_source_binding_invalid")

    gate = build_replayed_correlation_cluster_gate(
        deepcopy(matrix_replay),
        projected_cells,
        strategy_id=str(evaluation["strategy_id"]),
        variant_id=str(evaluation["variant_id"]),
        lane=str(evaluation["lane"]),
    )
    uncertainty = build_strategy_correlation_uncertainty_audit(matrix_replay)
    multiplicity = build_strategy_correlation_multiplicity_audit(uncertainty)
    family_assessment = assess_strategy_correlation_multiplicity_binding(
        registration["family_registration"],
        multiplicity,
    )
    evidence = build_strategy_correlation_multiplicity_report_evidence(
        protocol,
        gate,
        uncertainty,
        multiplicity,
        family_assessment,
    )
    verification = verify_strategy_correlation_multiplicity_report_evidence(
        evidence,
        protocol=protocol,
    )
    if verification.get("status") != "PASS":
        raise ValueError("correlation_research_multiplicity_evidence_invalid")
    return evidence


def build_strategy_correlation_research_multiplicity_evidence_from_selection(
    protocol: dict[str, Any],
    selection_payloads: dict[str, dict[str, Any]],
    selection_manifests: list[dict[str, Any]],
    selection_alignment: dict[str, Any],
    selection_cells: list[dict[str, Any]],
    validation_rankings: list[dict[str, Any]],
) -> dict[str, Any]:
    registration, _evaluation = _registered_evaluation(protocol)
    source = dict(registration["source_protocol_registration"])
    input_snapshot = selection_alignment.get("input_snapshot")
    if not isinstance(input_snapshot, dict) or (
        input_snapshot.get("input_hash")
        != source.get("selection_alignment_input_hash")
    ):
        raise ValueError("correlation_research_selection_alignment_binding_invalid")
    completed_input = build_correlation_completed_price_input(
        selection_payloads,
        selection_manifests,
        dict(source["preregistration"]),
        cutoff_date=str(source["cutoff_date"]),
        selection_alignment_input_hash=str(input_snapshot["input_hash"]),
    )
    matrix_replay = build_correlation_matrix_replay(
        completed_input,
        dict(source["preregistration"]),
    )
    return build_strategy_correlation_research_multiplicity_evidence(
        protocol,
        matrix_replay,
        selection_cells,
        validation_rankings,
    )
