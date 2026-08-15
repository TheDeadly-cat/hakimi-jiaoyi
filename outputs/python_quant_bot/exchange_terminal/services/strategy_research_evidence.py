from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from .backtest_engine import EXECUTION_MODEL_VERSION, prepare_backtest_dataset
from .market_history_store import build_history_dataset_evidence
from .implementation_manifest import verify_embedded_implementation_manifest
from .execution_authority import authority_violations
from .strategy_benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    align_completed_daily_payloads,
    build_calendar_split_schedule,
)
from .strategy_matrix_evidence import verify_matrix_research_governance
from .strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    verify_strategy_hypothesis_preregistration,
)
from .strategy_cost_stress import (
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_TEST_COST_STRESS_STAGE,
    SELECTION_COST_STRESS_STAGE,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3,
    STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION,
    build_strategy_cost_stress_contract,
    build_strategy_cost_stress_evidence,
    normalize_strategy_cost_risk,
)
from .strategy_chronological_slice import (
    COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V1_REPORT_SCHEMA_VERSIONS,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION,
    STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5,
    build_fixed_chronological_slice_evidence,
    build_fixed_chronological_slice_evidence_v2,
)
from .strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
    aggregate_validation_variant,
    build_legacy_parameter_stability_snapshot_v1,
    build_parameter_stability_snapshot,
    canonical_hash,
    freeze_validation_candidates,
)
from .strategy_selection_replay import (
    DEVELOPMENT_SELECTION_SPLIT_POLICY,
    STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION,
    build_development_selection_prefix_schedule,
    build_strategy_selection_replay_evidence,
)
from .strategy_selection_alignment import (
    alignment_row_projection,
    verify_strategy_selection_alignment_input_snapshot,
)
from .strategy_frozen_evaluation_replay import (
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
    STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1,
    STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2,
    build_strategy_frozen_evaluation_replay_evidence,
    rebuild_strategy_frozen_confirmation_context,
)
from .strategy_preregistered_failure_admission import (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    build_strategy_preregistered_failure_admission,
    build_strategy_preregistered_failure_admission_v2,
    verify_strategy_preregistered_failure_admission_v3_receipt,
)
from .strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
    verify_strategy_research_search_lineage,
)


LEGACY_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION = 3
PARAMETER_STABILITY_V2_REPORT_SCHEMA_VERSION = 4
SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION = 5
IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION = 6
HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION = (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION
)
STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION = (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
)
STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION = (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
)
PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS = frozenset({
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
})
SUPPORTED_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS = frozenset({
    LEGACY_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
    PARAMETER_STABILITY_V2_REPORT_SCHEMA_VERSION,
    SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION,
    IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
    HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
})
LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION = (
    "strategy-research-selection-cell-evidence-v2"
)
STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION = (
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5
)
SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS = frozenset({
    SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION,
    IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
    HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
})
SELECTION_CELL_EVIDENCE_V3_REPORT_SCHEMA_VERSIONS = frozenset({
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
})
SELECTION_CELL_EVIDENCE_V4_REPORT_SCHEMA_VERSIONS = frozenset({
    *FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V1_REPORT_SCHEMA_VERSIONS,
})
SELECTION_CELL_EVIDENCE_V5_REPORT_SCHEMA_VERSIONS = frozenset({
    *FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS,
})
REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS = (
    SELECTION_CELL_EVIDENCE_V5_REPORT_SCHEMA_VERSIONS
)
POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS = frozenset({
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
})
HYPOTHESIS_BOUND_REPORT_SCHEMA_VERSIONS = frozenset({
    HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
})
IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSIONS = frozenset({
    IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
    HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
})
STRATEGY_RESEARCH_WORKFLOW = "NESTED_VARIANT_RESEARCH"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _native_finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _native_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _close_number(left: Any, right: Any, *, tolerance: float = 1e-6) -> bool:
    return _native_finite(left) and _native_finite(right) and math.isclose(
        float(left),
        float(right),
        rel_tol=0.0,
        abs_tol=tolerance,
    )


def _verify_current_batch_spec_contract(batch_spec: dict[str, Any]) -> list[str]:
    """Keep current batch limits typed; legacy reports keep their old semantics."""

    blockers: list[str] = []
    for field, minimum in (
        ("limit", 360),
        ("max_test_candidates", 1),
        ("max_confirmation_candidates", 1),
    ):
        value = batch_spec.get(field)
        if not _native_nonnegative_int(value) or value < minimum:
            blockers.append(f"research_batch_numeric_contract_invalid:{field}")
    if batch_spec.get("report_schema_version") in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        frozen_risks = [("batch", batch_spec.get("risk"))]
        frozen_risks.extend(
            (
                str(variant.get("variant_id") or "UNKNOWN"),
                variant.get("risk"),
            )
            for variant in _sequence(batch_spec.get("variants"))
            if isinstance(variant, dict)
        )
        for identity, raw_risk in frozen_risks:
            try:
                risk = _mapping(raw_risk)
                normalized = normalize_strategy_cost_risk(risk)
            except (TypeError, ValueError):
                blockers.append(f"research_batch_cost_risk_invalid:{identity}")
                continue
            if any(
                not isinstance(risk.get(field), float)
                or risk.get(field) != normalized[field]
                for field in ("fee_rate", "slippage_bps")
            ):
                blockers.append(f"research_batch_cost_risk_not_canonical:{identity}")
    return blockers


def _embedded_hash_matches(payload: Any, field: str) -> bool:
    if not isinstance(payload, dict):
        return False
    expected = str(payload.get(field) or "")
    return bool(expected) and canonical_hash({
        key: value for key, value in payload.items() if key != field
    }) == expected


def _created_at_ms(value: Any) -> int:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def strategy_research_result_hash(report: dict[str, Any] | Any) -> str:
    payload = _mapping(report)
    result_payload = {
        "spec_hash": str(payload.get("batch_spec_hash") or ""),
        "dataset_hash": str(payload.get("dataset_manifest_hash") or ""),
        "selection_runs": [
            str(cell.get("run_hash") or "")
            for cell in _sequence(payload.get("selection_cells"))
            if isinstance(cell, dict)
        ],
        "validation_rankings": _sequence(payload.get("validation_rankings")),
        "frozen_candidates": _sequence(payload.get("frozen_candidates")),
        "test_runs": [
            str(cell.get("run_hash") or "")
            for cell in _sequence(payload.get("test_cells"))
            if isinstance(cell, dict)
        ],
        "test_results": _sequence(payload.get("test_results")),
        "holdout_runs": [
            str(cell.get("run_hash") or "")
            for cell in _sequence(payload.get("holdout_cells"))
            if isinstance(cell, dict)
        ],
        "holdout_results": _sequence(payload.get("holdout_results")),
        "forward_candidates": _sequence(payload.get("forward_candidates")),
    }
    # Keep historical v3/v4 report hashes stable; reports opt into the
    # descriptive parameter-plateau projection by carrying the field.
    if "parameter_stability" in payload:
        result_payload["parameter_stability"] = _mapping(payload.get("parameter_stability"))
    if (
        isinstance(payload.get("schema_version"), int)
        and not isinstance(payload.get("schema_version"), bool)
        and payload.get("schema_version") >= IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION
    ):
        result_payload["report_schema_version"] = int(payload.get("schema_version"))
        result_payload["implementation_manifest"] = _mapping(payload.get("implementation_manifest"))
    if payload.get("schema_version") in (
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS
    ):
        result_payload["preregistered_failure_admission"] = _mapping(
            payload.get("preregistered_failure_admission")
        )
    return canonical_hash(result_payload)


def strategy_research_selection_cell_hash(cell: dict[str, Any], risk: dict[str, Any]) -> str:
    """Reproduce the historical schema-3/4 selection-cell hash.

    This function intentionally ignores the nested robustness details because
    changing it would reinterpret already-issued report hashes. New reports
    must use ``strategy_research_selection_cell_hash_for_report`` instead.
    """
    return canonical_hash({
        "phase": cell.get("phase"),
        "symbol": cell.get("symbol"),
        "variant_id": cell.get("variant_id"),
        "param_hash": cell.get("param_hash"),
        "implementation_fingerprint": cell.get("implementation_fingerprint"),
        "risk": risk,
        "dataset_hash": cell.get("dataset_hash"),
        "selection_input_end": cell.get("selection_input_end"),
        "metrics": {
            "train_return_pct": cell.get("train_return_pct"),
            "validation_return_pct": cell.get("validation_return_pct"),
            "validation_excess_return_pct": cell.get("validation_excess_return_pct"),
            "validation_drawdown_improvement_pct": cell.get("validation_drawdown_improvement_pct"),
            "validation_sharpe_excess": cell.get("validation_sharpe_excess"),
            "validation_risk_efficiency_excess": cell.get("validation_risk_efficiency_excess"),
            "validation_trade_count": cell.get("validation_trade_count"),
            "fold_stability_status": cell.get("fold_stability_status"),
            "cost_sensitivity_status": cell.get("cost_sensitivity_status"),
            "lookahead_status": cell.get("lookahead_status"),
        },
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_selection_cell_hash_v2(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: int = SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION,
) -> str:
    """Seal the complete stable selection cell for schema-5 reports.

    ``elapsed_ms`` remains diagnostic-only so repeatable evidence is not tied
    to machine timing. Every other stored field is bound, including the full
    fold/cost/lookahead evidence and the research/paper/live authority flags.
    """
    stable_cell = {
        key: value
        for key, value in _mapping(cell).items()
        if key not in {"run_hash", "elapsed_ms"}
    }
    return canonical_hash({
        "cell_evidence_schema_version": (
            LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
        ),
        "report_schema_version": report_schema_version,
        "cell": stable_cell,
        "risk": _mapping(risk),
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_selection_cell_hash_v3(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: int = COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
) -> str:
    """Seal the schema-8 cell under the versioned cost-stress contract."""

    stable_cell = {
        key: value
        for key, value in _mapping(cell).items()
        if key not in {"run_hash", "elapsed_ms"}
    }
    return canonical_hash({
        "cell_evidence_schema_version": (
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3
        ),
        "report_schema_version": report_schema_version,
        "cell": stable_cell,
        "risk": _mapping(risk),
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_selection_cell_hash_v4(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: int = LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
) -> str:
    """Seal the schema-9 cell and its versioned chronological topology."""

    stable_cell = {
        key: value
        for key, value in _mapping(cell).items()
        if key not in {"run_hash", "elapsed_ms"}
    }
    return canonical_hash({
        "cell_evidence_schema_version": (
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
        ),
        "report_schema_version": report_schema_version,
        "cell": stable_cell,
        "risk": _mapping(risk),
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_selection_cell_hash_v5(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: int = FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
) -> str:
    """Seal the schema-10 cell and its replayed chronological evidence."""

    stable_cell = {
        key: value
        for key, value in _mapping(cell).items()
        if key not in {"run_hash", "elapsed_ms"}
    }
    return canonical_hash({
        "cell_evidence_schema_version": (
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5
        ),
        "report_schema_version": report_schema_version,
        "cell": stable_cell,
        "risk": _mapping(risk),
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_selection_cell_hash_for_report(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: Any,
) -> str:
    """Select the frozen cell-hash contract declared by the report schema."""
    if report_schema_version in SELECTION_CELL_EVIDENCE_V5_REPORT_SCHEMA_VERSIONS:
        return strategy_research_selection_cell_hash_v5(
            cell,
            risk,
            report_schema_version=int(report_schema_version),
        )
    if report_schema_version in SELECTION_CELL_EVIDENCE_V4_REPORT_SCHEMA_VERSIONS:
        return strategy_research_selection_cell_hash_v4(
            cell,
            risk,
            report_schema_version=int(report_schema_version),
        )
    if report_schema_version in SELECTION_CELL_EVIDENCE_V3_REPORT_SCHEMA_VERSIONS:
        return strategy_research_selection_cell_hash_v3(
            cell,
            risk,
            report_schema_version=int(report_schema_version),
        )
    if report_schema_version in SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS:
        return strategy_research_selection_cell_hash_v2(
            cell,
            risk,
            report_schema_version=int(report_schema_version),
        )
    return strategy_research_selection_cell_hash(cell, risk)


def strategy_research_test_cell_hash(cell: dict[str, Any], risk: dict[str, Any]) -> str:
    """Reproduce the historical schema-3..7 frozen-test cell hash."""

    return canonical_hash({
        "phase": cell.get("phase"),
        "symbol": cell.get("symbol"),
        "variant_id": cell.get("variant_id"),
        "param_hash": cell.get("param_hash"),
        "risk": risk,
        "dataset_hash": cell.get("dataset_hash"),
        "test_start": cell.get("test_start"),
        "test_end": cell.get("test_end"),
        "metrics": {
            "test_return_pct": cell.get("test_return_pct"),
            "test_excess_return_pct": cell.get("test_excess_return_pct"),
            "test_drawdown_improvement_pct": cell.get("test_drawdown_improvement_pct"),
            "test_sharpe_excess": cell.get("test_sharpe_excess"),
            "test_risk_efficiency_excess": cell.get("test_risk_efficiency_excess"),
            "test_trade_count": cell.get("test_trade_count"),
            "test_cost_status": cell.get("test_cost_status"),
        },
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_test_cell_hash_v2(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: int = COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
) -> str:
    stable_cell = {
        key: value
        for key, value in _mapping(cell).items()
        if key not in {"run_hash", "elapsed_ms"}
    }
    return canonical_hash({
        "test_cell_evidence_schema_version": (
            STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION
        ),
        "report_schema_version": report_schema_version,
        "cell": stable_cell,
        "risk": _mapping(risk),
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_test_cell_hash_for_report(
    cell: dict[str, Any],
    risk: dict[str, Any],
    *,
    report_schema_version: Any,
) -> str:
    if report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
        stable_cell = {
            key: value
            for key, value in _mapping(cell).items()
            if key not in {"run_hash", "elapsed_ms"}
        }
        return canonical_hash({
            "test_cell_evidence_schema_version": (
                STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2
            ),
            "report_schema_version": int(report_schema_version),
            "cell": stable_cell,
            "risk": _mapping(risk),
            "execution_model": EXECUTION_MODEL_VERSION,
        })
    if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        return strategy_research_test_cell_hash_v2(
            cell,
            risk,
            report_schema_version=int(report_schema_version),
        )
    return strategy_research_test_cell_hash(cell, risk)


def strategy_research_holdout_cell_hash(cell: dict[str, Any], candidate: dict[str, Any]) -> str:
    return canonical_hash({
        "phase": "HOLDOUT_CONFIRMATION",
        "source_run_hash": cell.get("source_run_hash"),
        "symbol": cell.get("symbol"),
        "strategy_id": cell.get("strategy_id"),
        "variant_id": cell.get("variant_id"),
        "param_hash": candidate.get("param_hash"),
        "risk": candidate.get("risk"),
        "dataset_hash": cell.get("dataset_hash"),
        "metrics": {
            "test_return_pct": cell.get("test_return_pct"),
            "test_excess_return_pct": cell.get("test_excess_return_pct"),
            "test_drawdown_improvement_pct": cell.get("test_drawdown_improvement_pct"),
            "test_sharpe_excess": cell.get("test_sharpe_excess"),
            "test_risk_efficiency_excess": cell.get("test_risk_efficiency_excess"),
            "test_trade_count": cell.get("test_trade_count"),
            "cost_sensitivity_status": cell.get("cost_sensitivity_status"),
            "temporal_status": cell.get("temporal_status"),
            "walk_forward_status": cell.get("walk_forward_status"),
            "lookahead_status": cell.get("lookahead_status"),
        },
        "execution_model": EXECUTION_MODEL_VERSION,
    })


def strategy_research_holdout_cell_hash_for_report(
    cell: dict[str, Any],
    candidate: dict[str, Any],
    *,
    report_schema_version: Any,
) -> str:
    if report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
        stable_cell = {
            key: value
            for key, value in _mapping(cell).items()
            if key not in {"run_hash", "elapsed_ms"}
        }
        return canonical_hash({
            "holdout_cell_evidence_schema_version": (
                STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1
            ),
            "report_schema_version": int(report_schema_version),
            "cell": stable_cell,
            "candidate_identity": {
                field: candidate.get(field)
                for field in (
                    "strategy_id",
                    "variant_id",
                    "params",
                    "param_hash",
                    "implementation_fingerprint",
                    "risk",
                    "risk_hash",
                    "selection_lane",
                )
            },
            "execution_model": EXECUTION_MODEL_VERSION,
        })
    return strategy_research_holdout_cell_hash(cell, candidate)


def _verify_dataset_snapshot(
    report: dict[str, Any],
    *,
    batch_spec: dict[str, Any],
    expected_batch_hash: str,
    dataset_manifest: list[Any],
    expected_dataset_hash: str,
) -> list[str]:
    blockers: list[str] = []
    snapshot = _mapping(report.get("dataset_snapshot"))
    if snapshot.get("schema_version") != "strategy-matrix-dataset-snapshot-v1":
        blockers.append("research_dataset_snapshot_schema_invalid")
    if not _embedded_hash_matches(snapshot, "snapshot_hash"):
        blockers.append("research_dataset_snapshot_hash_invalid")
    if str(snapshot.get("batch_spec_hash") or "") != expected_batch_hash:
        blockers.append("research_dataset_snapshot_batch_mismatch")
    if (
        canonical_hash(_sequence(snapshot.get("dataset_manifest"))) != expected_dataset_hash
        or str(snapshot.get("dataset_manifest_hash") or "") != expected_dataset_hash
    ):
        blockers.append("research_dataset_snapshot_manifest_mismatch")
    if (
        snapshot.get("research_only") is not True
        or snapshot.get("paper_authorized") is not False
        or snapshot.get("live_order_allowed") is not False
    ):
        blockers.append("research_dataset_snapshot_has_execution_authority")

    datasets = [item for item in _sequence(snapshot.get("datasets")) if isinstance(item, dict)]
    if len(datasets) != len(_sequence(snapshot.get("datasets"))):
        blockers.append("research_dataset_snapshot_dataset_type_invalid")
    if snapshot.get("dataset_count") != len(datasets):
        blockers.append("research_dataset_snapshot_count_mismatch")
    if snapshot.get("row_count") != sum(len(_sequence(item.get("rows"))) for item in datasets):
        blockers.append("research_dataset_snapshot_row_count_mismatch")

    manifest_by_symbol = {
        str(item.get("symbol") or "").upper(): item
        for item in dataset_manifest
        if isinstance(item, dict) and str(item.get("symbol") or "").strip()
    }
    if len(manifest_by_symbol) != len(dataset_manifest):
        blockers.append("research_dataset_manifest_symbols_not_unique")
    selection_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("selection_symbols"))
    }
    holdout_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("confirmation_symbols"))
    }
    snapshot_symbols: set[str] = set()
    for item in datasets:
        symbol = str(item.get("symbol") or "").upper()
        source = str(item.get("source") or "")
        market = str(item.get("market") or "")
        rows = _sequence(item.get("rows"))
        if not symbol or symbol in snapshot_symbols:
            blockers.append(f"research_dataset_snapshot_symbol_invalid:{symbol or 'UNKNOWN'}")
            continue
        snapshot_symbols.add(symbol)
        manifest = _mapping(manifest_by_symbol.get(symbol))
        if not manifest:
            blockers.append(f"research_dataset_snapshot_manifest_missing:{symbol}")
            continue
        expected_role = (
            "SELECTION" if symbol in selection_symbols
            else "CONFIRMATION" if symbol in holdout_symbols
            else ""
        )
        if str(item.get("role") or "") != expected_role or not expected_role:
            blockers.append(f"research_dataset_snapshot_role_mismatch:{symbol}")
        if str(manifest.get("source") or "") != source:
            blockers.append(f"research_dataset_snapshot_source_mismatch:{symbol}")
        if market == "crypto":
            history = _mapping(item.get("market_history_evidence"))
            rebuilt = build_history_dataset_evidence(
                symbol=symbol,
                rows=rows,
                source=source,
                dataset_lineage_id=str(history.get("dataset_lineage_id") or ""),
                cache_manifest=dict(history.get("cache_manifest") or {}),
                cache_admitted=history.get("cache_admitted") is True,
            )
            if history != rebuilt:
                blockers.append(f"research_crypto_history_evidence_mismatch:{symbol}")
            if history != _mapping(manifest.get("market_history_evidence")):
                blockers.append(f"research_crypto_history_manifest_mismatch:{symbol}")
        elif market == "stock":
            revision = _mapping(item.get("data_revision_evidence"))
            if revision != _mapping(manifest.get("data_revision_evidence")):
                blockers.append(f"research_stock_revision_manifest_mismatch:{symbol}")
            if revision.get("status") != "PASS":
                blockers.append(f"research_stock_revision_not_passed:{symbol}")
        recomputed = prepare_backtest_dataset(
            rows,
            symbol=symbol,
            source=source,
            timeframe="1D",
            minimum_rows=1,
            market=market,
        )["manifest"]
        for field in ("data_hash", "row_count", "first", "last"):
            if recomputed.get(field) != manifest.get(field):
                blockers.append(f"research_dataset_snapshot_{field}_mismatch:{symbol}")
    if snapshot_symbols != set(manifest_by_symbol):
        blockers.append("research_dataset_snapshot_symbol_set_mismatch")
    return blockers


def _verify_development_projection(
    report: dict[str, Any],
    *,
    batch_spec: dict[str, Any],
    selection_symbols: set[str],
) -> list[str]:
    blockers: list[str] = []
    alignment = _mapping(report.get("selection_alignment"))
    if alignment.get("status") != "PASS":
        return blockers
    schedule = _mapping(report.get("selection_calendar_schedule"))
    governance = _mapping(report.get("research_governance"))
    summary = _mapping(report.get("summary"))
    schema10 = report.get("schema_version") in SELECTION_CELL_EVIDENCE_V5_REPORT_SCHEMA_VERSIONS
    expected_policy = (
        DEVELOPMENT_SELECTION_SPLIT_POLICY if schema10 else "TRAIN_VALIDATION_ONLY"
    )
    if schedule.get("projection_policy") != expected_policy:
        blockers.append("research_development_projection_policy_missing")
    if (
        schedule.get("protected_test_rows_persisted") is not False
        or alignment.get("protected_test_rows_persisted") is not False
        or governance.get("protected_test_rows_persisted") is not False
        or summary.get("protected_test_rows_persisted") is not False
    ):
        blockers.append("research_development_protected_rows_flag_invalid")

    boundaries = _mapping(schedule.get("symbol_boundaries"))
    snapshot = _mapping(report.get("dataset_snapshot"))
    selection_datasets = {
        str(item.get("symbol") or "").upper(): item
        for item in _sequence(snapshot.get("datasets"))
        if isinstance(item, dict) and item.get("role") == "SELECTION"
    }
    if set(selection_datasets) != selection_symbols:
        blockers.append("research_development_selection_snapshot_set_mismatch")
    if schema10:
        split_policy = _mapping(batch_spec.get("split_policy"))
        try:
            rebuilt = build_development_selection_prefix_schedule(
                {
                    symbol: {"rows": _sequence(_mapping(dataset).get("rows"))}
                    for symbol, dataset in selection_datasets.items()
                },
                train_ratio=split_policy.get("train_ratio"),
                validation_ratio=split_policy.get("validation_ratio"),
                minimum_segment_rows=split_policy.get("minimum_segment_rows"),
            )
        except (TypeError, ValueError, KeyError, OverflowError):
            rebuilt = {"status": "BLOCK", "blockers": ["rebuild_failed"]}
        if rebuilt.get("status") != "PASS":
            blockers.append("research_development_selection_split_rebuild_blocked")
        if schedule != rebuilt:
            blockers.append("research_development_selection_schedule_semantic_mismatch")
        boundaries = _mapping(rebuilt.get("symbol_boundaries"))
    validation_end = str(schedule.get("validation_end") or "")[:10]
    for symbol in sorted(selection_symbols):
        boundary = _mapping(boundaries.get(symbol))
        rows = _sequence(_mapping(selection_datasets.get(symbol)).get("rows"))
        counts = _mapping(boundary.get("counts"))
        if counts.get("test") != 0:
            blockers.append(f"research_development_test_rows_persisted:{symbol}")
        if (
            boundary.get("validation_end_index") != len(rows)
            or boundary.get("row_count") != len(rows)
        ):
            blockers.append(f"research_development_snapshot_boundary_mismatch:{symbol}")
        last = str(_mapping(rows[-1]).get("date") or "")[:10] if rows else ""
        if not last or (validation_end and last > validation_end):
            blockers.append(f"research_development_snapshot_past_validation:{symbol}")
    return blockers


def _verify_selection_cell_evidence_v2(
    cell: dict[str, Any],
    *,
    variant_id: str,
    symbol: str,
    expected_schema_version: str = (
        LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
    ),
    expected_evaluation_mode: str = "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
) -> list[str]:
    blockers: list[str] = []
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    if cell.get("cell_evidence_schema_version") != expected_schema_version:
        blockers.append(f"research_selection_cell_evidence_schema_invalid:{identity}")

    fold_stability = cell.get("fold_stability")
    cost_sensitivity = cell.get("cost_sensitivity")
    lookahead_issues = cell.get("lookahead_issues")
    if not isinstance(fold_stability, dict):
        blockers.append(f"research_selection_fold_evidence_type_invalid:{identity}")
    else:
        if fold_stability.get("status") != cell.get("fold_stability_status"):
            blockers.append(f"research_selection_fold_status_mismatch:{identity}")
        if (
            fold_stability.get("evaluation_mode") != expected_evaluation_mode
            or fold_stability.get("parameters_refit_per_fold") is not False
            or fold_stability.get("walk_forward_optimization_claim_allowed") is not False
        ):
            blockers.append(f"research_selection_fold_claim_boundary_invalid:{identity}")
        if fold_stability.get("status") == "PASS":
            folds = fold_stability.get("folds")
            valid_folds = [
                fold for fold in folds or []
                if isinstance(fold, dict)
                and fold.get("ok") is True
                and _native_finite(fold.get("total_return_pct"))
                and _native_finite(fold.get("max_drawdown_pct"))
                and _native_nonnegative_int(fold.get("trade_count"))
            ] if isinstance(folds, list) else []
            if not isinstance(folds, list) or not folds or len(valid_folds) != len(folds):
                blockers.append(f"research_selection_fold_summary_invalid:{identity}")
            else:
                expected_fold_summary = {
                    "fold_count": len(folds),
                    "usable_folds": len(valid_folds),
                    "positive_folds": sum(
                        float(fold["total_return_pct"]) > 0 for fold in valid_folds
                    ),
                    "total_trades": sum(int(fold["trade_count"]) for fold in valid_folds),
                    "worst_drawdown_pct": max(
                        float(fold["max_drawdown_pct"]) for fold in valid_folds
                    ),
                }
                for field, expected in expected_fold_summary.items():
                    actual = fold_stability.get(field)
                    matches = (
                        _close_number(actual, expected)
                        if field == "worst_drawdown_pct"
                        else actual == expected
                    )
                    if not matches:
                        blockers.append(f"research_selection_fold_summary_mismatch:{identity}:{field}")
    if not isinstance(cost_sensitivity, dict):
        blockers.append(f"research_selection_cost_evidence_type_invalid:{identity}")
    else:
        if cost_sensitivity.get("status") != cell.get("cost_sensitivity_status"):
            blockers.append(f"research_selection_cost_status_mismatch:{identity}")
        if cost_sensitivity.get("status") == "PASS":
            scenarios = cost_sensitivity.get("scenarios")
            valid_scenarios = [
                scenario for scenario in scenarios or []
                if isinstance(scenario, dict)
                and scenario.get("ok") is True
                and _native_finite(scenario.get("total_return_pct"))
                and _native_finite(scenario.get("max_drawdown_pct"))
            ] if isinstance(scenarios, list) else []
            baseline = cost_sensitivity.get("baseline_return_pct")
            if (
                not isinstance(scenarios, list)
                or not scenarios
                or len(valid_scenarios) != len(scenarios)
                or not _native_finite(baseline)
            ):
                blockers.append(f"research_selection_cost_summary_invalid:{identity}")
            else:
                worst_return = min(float(item["total_return_pct"]) for item in valid_scenarios)
                worst_drawdown = max(float(item["max_drawdown_pct"]) for item in valid_scenarios)
                expected_cost_summary = {
                    "worst_return_pct": round(worst_return, 2),
                    "worst_drawdown_pct": round(worst_drawdown, 2),
                    "break_even_preserved": worst_return > 0,
                    "minimum_stressed_return_pct": 0.0,
                    "return_degradation_pct": round(float(baseline) - worst_return, 2),
                    "allowed_degradation_pct": round(max(5.0, abs(float(baseline)) * 0.75), 2),
                }
                for field, expected in expected_cost_summary.items():
                    actual = cost_sensitivity.get(field)
                    matches = (
                        actual == expected
                        if isinstance(expected, bool)
                        else _close_number(actual, expected)
                    )
                    if not matches:
                        blockers.append(f"research_selection_cost_summary_mismatch:{identity}:{field}")
    if not isinstance(lookahead_issues, list):
        blockers.append(f"research_selection_lookahead_evidence_type_invalid:{identity}")
    if not isinstance(cell.get("lookahead_status"), str) or not str(cell.get("lookahead_status") or ""):
        blockers.append(f"research_selection_lookahead_status_invalid:{identity}")

    if (
        cell.get("research_only") is not True
        or cell.get("paper_authorized") is not False
        or cell.get("live_order_allowed") is not False
    ):
        blockers.append(f"research_selection_cell_has_execution_authority:{identity}")
    if cell.get("test_rows_evaluated") is not False:
        blockers.append(f"research_selection_cell_touched_test_rows:{identity}")
    return blockers


def _verify_selection_cell_evidence_v3(
    cell: dict[str, Any],
    *,
    variant_id: str,
    symbol: str,
    risk: dict[str, Any],
    expected_schema_version: str = (
        STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3
    ),
    expected_evaluation_mode: str = "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
) -> list[str]:
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    blockers = _verify_selection_cell_evidence_v2(
        cell,
        variant_id=variant_id,
        symbol=symbol,
        expected_schema_version=expected_schema_version,
        expected_evaluation_mode=expected_evaluation_mode,
    )
    fold_stability = _mapping(cell.get("fold_stability"))
    if (
        _native_finite(fold_stability.get("worst_drawdown_pct"))
        and float(fold_stability["worst_drawdown_pct"]) < 0
    ):
        blockers.append(f"research_selection_fold_drawdown_negative:{identity}:summary")
    for index, fold in enumerate(_sequence(fold_stability.get("folds")), start=1):
        if (
            isinstance(fold, dict)
            and _native_finite(fold.get("max_drawdown_pct"))
            and float(fold["max_drawdown_pct"]) < 0
        ):
            blockers.append(
                f"research_selection_fold_drawdown_negative:{identity}:{index}"
            )
    cost = cell.get("cost_sensitivity")
    if not isinstance(cost, dict):
        return blockers
    baseline = cost.get("baseline")
    scenarios = cost.get("scenarios")
    try:
        expected = build_strategy_cost_stress_evidence(
            stage=SELECTION_COST_STRESS_STAGE,
            risk=risk,
            baseline=baseline,
            scenarios=scenarios,
        )
    except (TypeError, ValueError):
        blockers.append(f"research_selection_cost_contract_invalid:{identity}")
        return blockers
    if cost != expected:
        blockers.append(f"research_selection_cost_evidence_semantic_mismatch:{identity}")
    if expected.get("verification_status") != "PASS":
        blockers.append(f"research_selection_cost_evidence_integrity_blocked:{identity}")

    baseline_row = _mapping(baseline)
    linked_fields = (
        ("ok", "validation_ok", False),
        ("total_return_pct", "validation_return_pct", True),
        ("max_drawdown_pct", "validation_max_drawdown_pct", True),
        ("trade_count", "validation_trade_count", False),
    )
    for evidence_field, cell_field, numeric in linked_fields:
        evidence_value = baseline_row.get(evidence_field)
        cell_value = cell.get(cell_field)
        matches = (
            _close_number(evidence_value, cell_value)
            if numeric
            else evidence_value == cell_value
        )
        if not matches:
            blockers.append(
                f"research_selection_cost_baseline_mismatch:{identity}:{evidence_field}"
            )
    return blockers


def _verify_selection_cell_evidence_v4(
    cell: dict[str, Any],
    *,
    variant_id: str,
    symbol: str,
    risk: dict[str, Any],
    selection_rows: list[dict[str, Any]],
    source: str,
    market: str,
    timeframe: str = "1D",
) -> list[str]:
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    blockers = _verify_selection_cell_evidence_v3(
        cell,
        variant_id=variant_id,
        symbol=symbol,
        risk=risk,
        expected_schema_version=(
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
        ),
    )
    evidence = cell.get("fold_stability")
    if not isinstance(evidence, dict):
        return blockers
    if (
        evidence.get("schema_version")
        != STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION
    ):
        blockers.append(f"research_selection_fold_evidence_schema_invalid:{identity}")
        return blockers
    try:
        expected = build_fixed_chronological_slice_evidence(
            selection_rows=selection_rows,
            symbol=symbol,
            source=source,
            market=market,
            timeframe=timeframe,
            fold_plans=_sequence(evidence.get("folds")),
            fold_reports=_sequence(evidence.get("folds")),
            minimum_fold_rows=evidence.get("minimum_fold_rows"),
        )
    except (TypeError, ValueError):
        blockers.append(f"research_selection_fold_contract_invalid:{identity}")
        return blockers
    if evidence != expected:
        blockers.append(f"research_selection_fold_evidence_semantic_mismatch:{identity}")
    if expected.get("verification_status") != "PASS":
        blockers.append(f"research_selection_fold_evidence_integrity_blocked:{identity}")
    selection_prefix = _mapping(expected.get("selection_prefix"))
    for evidence_field, cell_field in (
        ("data_hash", "dataset_hash"),
        ("row_count", "selection_input_rows"),
        ("last", "selection_input_end"),
    ):
        if selection_prefix.get(evidence_field) != cell.get(cell_field):
            blockers.append(
                f"research_selection_prefix_binding_mismatch:{identity}:{evidence_field}"
            )
    return blockers


def _verify_selection_cell_evidence_v5(
    cell: dict[str, Any],
    *,
    variant_id: str,
    symbol: str,
    implementation_fingerprint: str,
    strategy_id: str,
    params: dict[str, Any],
    param_hash: str,
    risk: dict[str, Any],
    selection_rows: list[dict[str, Any]],
    train_end_index: int,
    source: str,
    market: str,
    timeframe: str = "1D",
) -> list[str]:
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    blockers = _verify_selection_cell_evidence_v3(
        cell,
        variant_id=variant_id,
        symbol=symbol,
        risk=risk,
        expected_schema_version=(
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5
        ),
        expected_evaluation_mode="FIXED_PARAMETER_CHRONOLOGICAL_SLICES_REPLAYED",
    )
    evidence = cell.get("fold_stability")
    if not isinstance(evidence, dict):
        return blockers
    if (
        evidence.get("schema_version")
        != STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2
    ):
        blockers.append(f"research_selection_fold_evidence_schema_invalid:{identity}")
        return blockers
    try:
        expected = build_fixed_chronological_slice_evidence_v2(
            selection_rows=selection_rows,
            symbol=symbol,
            source=source,
            market=market,
            timeframe=timeframe,
            strategy_id=strategy_id,
            params=params,
            param_hash=param_hash,
            risk=risk,
        )
    except (TypeError, ValueError, KeyError, OverflowError):
        blockers.append(f"research_selection_fold_contract_invalid:{identity}")
        return blockers
    if evidence != expected:
        blockers.append(f"research_selection_fold_result_semantic_mismatch:{identity}")
    if expected.get("verification_status") != "PASS":
        blockers.append(f"research_selection_fold_evidence_integrity_blocked:{identity}")
    selection_prefix = _mapping(expected.get("selection_prefix"))
    for evidence_field, cell_field in (
        ("data_hash", "dataset_hash"),
        ("row_count", "selection_input_rows"),
        ("last", "selection_input_end"),
    ):
        if selection_prefix.get(evidence_field) != cell.get(cell_field):
            blockers.append(
                f"research_selection_prefix_binding_mismatch:{identity}:{evidence_field}"
            )
    selection_replay = cell.get("selection_replay")
    if not isinstance(selection_replay, dict):
        blockers.append(f"research_selection_replay_missing_or_invalid:{identity}")
        return blockers
    if selection_replay.get("schema_version") != STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION:
        blockers.append(f"research_selection_replay_schema_invalid:{identity}")
        return blockers
    try:
        expected_replay = build_strategy_selection_replay_evidence(
            selection_rows=selection_rows,
            train_end_index=train_end_index,
            symbol=symbol,
            source=source,
            market=market,
            timeframe=timeframe,
            variant_id=variant_id,
            strategy_id=strategy_id,
            params=params,
            param_hash=param_hash,
            implementation_fingerprint=implementation_fingerprint,
            risk=risk,
        )
    except (TypeError, ValueError, KeyError, OverflowError):
        blockers.append(f"research_selection_replay_contract_invalid:{identity}")
        return blockers
    if selection_replay != expected_replay:
        blockers.append(f"research_selection_replay_semantic_mismatch:{identity}")
    if expected_replay.get("verification_status") != "PASS":
        blockers.append(f"research_selection_replay_integrity_blocked:{identity}")
    expected_metrics = _mapping(expected_replay.get("flat_metric_projection"))
    for field, expected_value in expected_metrics.items():
        if cell.get(field) != expected_value:
            blockers.append(f"research_selection_replay_metric_mismatch:{identity}:{field}")
    return blockers


def _verify_test_cell_evidence_v1(
    cell: dict[str, Any],
    *,
    variant_id: str,
    symbol: str,
    risk: dict[str, Any],
) -> list[str]:
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    blockers: list[str] = []
    if (
        cell.get("test_cell_evidence_schema_version")
        != STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION
    ):
        blockers.append(f"research_test_cell_evidence_schema_invalid:{identity}")
    evidence = cell.get("cost_stress_evidence")
    if not isinstance(evidence, dict):
        blockers.append(f"research_test_cost_evidence_type_invalid:{identity}")
        return blockers
    try:
        expected = build_strategy_cost_stress_evidence(
            stage=FROZEN_TEST_COST_STRESS_STAGE,
            risk=risk,
            baseline=evidence.get("baseline"),
            scenarios=evidence.get("scenarios"),
        )
    except (TypeError, ValueError):
        blockers.append(f"research_test_cost_contract_invalid:{identity}")
        return blockers
    if evidence != expected:
        blockers.append(f"research_test_cost_evidence_semantic_mismatch:{identity}")
    if expected.get("verification_status") != "PASS":
        blockers.append(f"research_test_cost_evidence_integrity_blocked:{identity}")
    if cell.get("test_cost_status") != expected.get("status"):
        blockers.append(f"research_test_cost_status_mismatch:{identity}")

    baseline = _mapping(evidence.get("baseline"))
    for evidence_field, cell_field, numeric in (
        ("ok", "test_ok", False),
        ("total_return_pct", "test_return_pct", True),
        ("max_drawdown_pct", "test_max_drawdown_pct", True),
        ("trade_count", "test_trade_count", False),
    ):
        evidence_value = baseline.get(evidence_field)
        cell_value = cell.get(cell_field)
        matches = (
            _close_number(evidence_value, cell_value)
            if numeric
            else evidence_value == cell_value
        )
        if not matches:
            blockers.append(
                f"research_test_cost_baseline_mismatch:{identity}:{evidence_field}"
            )
    severe = next(
        (
            item for item in _sequence(evidence.get("scenarios"))
            if isinstance(item, dict) and item.get("name") == "severe"
        ),
        {},
    )
    if not _close_number(
        _mapping(severe).get("total_return_pct"),
        cell.get("test_severe_cost_return_pct"),
    ):
        blockers.append(f"research_test_severe_return_mismatch:{identity}")
    if (
        cell.get("research_only") is not True
        or cell.get("paper_authorized") is not False
        or cell.get("live_order_allowed") is not False
    ):
        blockers.append(f"research_test_cell_has_execution_authority:{identity}")
    return blockers


def _verify_frozen_evaluation_cell_replay(
    cell: dict[str, Any],
    *,
    role: str,
    variant_id: str,
    symbol: str,
    candidate: dict[str, Any],
    rows: list[dict[str, Any]],
    train_end_index: int,
    validation_end_index: int,
    source: str,
    market: str,
    timeframe: str,
) -> list[str]:
    identity = f"{variant_id or 'UNKNOWN'}:{symbol or 'UNKNOWN'}"
    prefix = (
        "research_frozen_test"
        if role == FROZEN_TEST_ROLE
        else "research_holdout"
    )
    blockers: list[str] = []
    expected_cell_schema = (
        STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2
        if role == FROZEN_TEST_ROLE
        else STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1
    )
    cell_schema_field = (
        "test_cell_evidence_schema_version"
        if role == FROZEN_TEST_ROLE
        else "holdout_cell_evidence_schema_version"
    )
    if cell.get(cell_schema_field) != expected_cell_schema:
        blockers.append(f"{prefix}_cell_evidence_schema_invalid:{identity}")
    replay = cell.get("frozen_evaluation_replay")
    if not isinstance(replay, dict):
        blockers.append(f"{prefix}_replay_missing_or_invalid:{identity}")
        return blockers
    if replay.get("schema_version") != STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION:
        blockers.append(f"{prefix}_replay_schema_invalid:{identity}")
    if replay.get("role") != role:
        blockers.append(f"{prefix}_replay_role_invalid:{identity}")
    if (
        role == FROZEN_TEST_ROLE
        and cell.get("frozen_before_test") is not True
    ):
        blockers.append(
            f"research_frozen_test_not_frozen_before_evaluation:{identity}"
        )
    if (
        role == HOLDOUT_CONFIRMATION_ROLE
        and cell.get("phase") != HOLDOUT_CONFIRMATION_ROLE
    ):
        blockers.append(f"research_holdout_phase_invalid:{identity}")
    if role == HOLDOUT_CONFIRMATION_ROLE and "source_run_hash" in cell:
        blockers.append(
            f"research_holdout_legacy_source_hash_forbidden:{identity}"
        )
    try:
        expected = build_strategy_frozen_evaluation_replay_evidence(
            role=role,
            rows=rows,
            train_end_index=train_end_index,
            validation_end_index=validation_end_index,
            symbol=symbol,
            source=source,
            market=market,
            timeframe=timeframe,
            variant_id=variant_id,
            strategy_id=str(candidate.get("strategy_id") or ""),
            params=_mapping(candidate.get("params")),
            param_hash=str(candidate.get("param_hash") or ""),
            implementation_fingerprint=str(
                candidate.get("implementation_fingerprint") or ""
            ),
            risk=_mapping(candidate.get("risk")),
        )
    except (TypeError, ValueError, KeyError, OverflowError):
        blockers.append(f"{prefix}_replay_source_context_invalid:{identity}")
        return blockers
    if replay != expected:
        blockers.append(f"{prefix}_replay_semantic_mismatch:{identity}")
    if expected.get("verification_status") != "PASS":
        blockers.append(f"{prefix}_replay_integrity_blocked:{identity}")
    for field, expected_value in _mapping(
        expected.get("flat_metric_projection")
    ).items():
        if cell.get(field) != expected_value:
            blockers.append(f"{prefix}_replay_metric_mismatch:{identity}:{field}")
    if (
        cell.get("research_only") is not True
        or cell.get("paper_authorized") is not False
        or cell.get("live_order_allowed") is not False
    ):
        blockers.append(f"{prefix}_cell_has_execution_authority:{identity}")
    return blockers


def _verify_research_semantics(
    report: dict[str, Any],
    *,
    batch_spec: dict[str, Any],
    formal: bool,
) -> list[str]:
    blockers: list[str] = []
    report_schema_version = report.get("schema_version")
    uses_cell_evidence_v2 = report_schema_version in SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS
    uses_cell_evidence_v3 = report_schema_version in SELECTION_CELL_EVIDENCE_V3_REPORT_SCHEMA_VERSIONS
    uses_cell_evidence_v4 = report_schema_version in SELECTION_CELL_EVIDENCE_V4_REPORT_SCHEMA_VERSIONS
    uses_cell_evidence_v5 = report_schema_version in SELECTION_CELL_EVIDENCE_V5_REPORT_SCHEMA_VERSIONS
    uses_frozen_evaluation_replay = (
        report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS
    )
    if report_schema_version in {
        SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION,
        IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
        HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
        COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        blockers.extend(_verify_current_batch_spec_contract(batch_spec))
    variants = [dict(item) for item in _sequence(batch_spec.get("variants")) if isinstance(item, dict)]
    variant_by_id = {
        str(item.get("variant_id") or ""): item
        for item in variants
        if str(item.get("variant_id") or "")
    }
    if len(variants) != len(_sequence(batch_spec.get("variants"))) or len(variant_by_id) != len(variants):
        blockers.append("research_variant_registry_invalid")
    if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        for variant in variants:
            variant_id = str(variant.get("variant_id") or "UNKNOWN")
            try:
                expected_contract = build_strategy_cost_stress_contract(
                    _mapping(variant.get("risk"))
                )
            except (TypeError, ValueError):
                blockers.append(f"research_cost_stress_contract_invalid:{variant_id}")
                continue
            if variant.get("cost_stress_contract") != expected_contract:
                blockers.append(f"research_cost_stress_contract_mismatch:{variant_id}")
    selection_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("selection_symbols"))
    }
    holdout_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("confirmation_symbols"))
    }
    selection_cells = [
        dict(item) for item in _sequence(report.get("selection_cells")) if isinstance(item, dict)
    ]
    if len(selection_cells) != len(_sequence(report.get("selection_cells"))):
        blockers.append("research_selection_cell_type_invalid")
    selection_keys: list[tuple[str, str]] = []
    selection_datasets = {
        str(item.get("symbol") or "").upper(): item
        for item in _sequence(_mapping(report.get("dataset_snapshot")).get("datasets"))
        if isinstance(item, dict) and item.get("role") == "SELECTION"
    }
    reported_selection_schedule = _mapping(report.get("selection_calendar_schedule"))
    selection_boundaries = _mapping(reported_selection_schedule.get("symbol_boundaries"))
    reported_selection_alignment = _mapping(report.get("selection_alignment"))
    selection_alignment_passed = reported_selection_alignment.get("status") == "PASS"
    if uses_cell_evidence_v5:
        split_policy = _mapping(batch_spec.get("split_policy"))
        data_policy = _mapping(batch_spec.get("data_policy"))
        all_manifests = [
            dict(item)
            for item in _sequence(report.get("dataset_manifest"))
            if isinstance(item, dict)
        ]
        if len(all_manifests) != len(_sequence(report.get("dataset_manifest"))):
            blockers.append("research_dataset_manifest_item_invalid")
        selection_manifests = [
            item for item in all_manifests if item.get("role") == "SELECTION"
        ]
        alignment_input_verification = (
            verify_strategy_selection_alignment_input_snapshot(
                reported_selection_alignment.get("input_snapshot"),
                expected_symbols=selection_symbols,
                manifests=selection_manifests,
            )
        )
        if alignment_input_verification.get("status") != "PASS":
            blockers.extend(
                f"research_{item}"
                for item in alignment_input_verification.get("blockers") or []
            )
        alignment_input_payloads = _mapping(
            alignment_input_verification.get("payloads")
        )
        try:
            rebuilt_aligned_payloads, rebuilt_selection_alignment = (
                align_completed_daily_payloads(
                    alignment_input_payloads,
                    max_endpoint_skew_days=data_policy.get(
                        "max_endpoint_skew_days"
                    ),
                    max_boundary_skew_days=data_policy.get(
                        "max_boundary_skew_days"
                    ),
                )
            )
        except (TypeError, ValueError, KeyError, OverflowError):
            rebuilt_aligned_payloads = {}
            rebuilt_selection_alignment = {
                "status": "BLOCK",
                "blockers": ["selection_alignment_rebuild_failed"],
            }
        try:
            selection_payloads = {
                symbol: {
                    "rows": [
                        dict(row)
                        for row in _sequence(_mapping(dataset).get("rows"))
                        if isinstance(row, dict)
                    ]
                }
                for symbol, dataset in selection_datasets.items()
            }
            rebuilt_selection_schedule = (
                build_calendar_split_schedule(
                    selection_payloads,
                    train_ratio=split_policy.get("train_ratio"),
                    validation_ratio=split_policy.get("validation_ratio"),
                    minimum_segment_rows=split_policy.get("minimum_segment_rows"),
                )
                if formal
                else build_development_selection_prefix_schedule(
                    selection_payloads,
                    train_ratio=split_policy.get("train_ratio"),
                    validation_ratio=split_policy.get("validation_ratio"),
                    minimum_segment_rows=split_policy.get("minimum_segment_rows"),
                )
            )
        except (TypeError, ValueError, KeyError, OverflowError):
            rebuilt_selection_schedule = {
                "status": "BLOCK",
                "symbol_boundaries": {},
                "blockers": ["calendar_split_rebuild_failed"],
            }
        if rebuilt_selection_alignment.get("status") == "PASS":
            expected_dataset_symbols = set(selection_symbols)
            if set(selection_datasets) != expected_dataset_symbols:
                blockers.append("research_selection_dataset_role_coverage_mismatch")
            for symbol in sorted(expected_dataset_symbols & set(selection_datasets)):
                aligned_rows = _sequence(
                    _mapping(rebuilt_aligned_payloads.get(symbol)).get("rows")
                )
                frozen_rows = _sequence(_mapping(selection_datasets[symbol]).get("rows"))
                try:
                    aligned_projection = [
                        alignment_row_projection(row) for row in aligned_rows
                    ]
                    frozen_projection = [
                        alignment_row_projection(row) for row in frozen_rows
                    ]
                except ValueError:
                    aligned_projection = []
                    frozen_projection = [None]
                if aligned_projection != frozen_projection:
                    blockers.append(
                        f"research_selection_aligned_rows_mismatch:{symbol}"
                    )
            if rebuilt_selection_schedule.get("status") != "PASS":
                rebuilt_selection_alignment["status"] = "BLOCK"
                rebuilt_selection_alignment["blockers"] = list(dict.fromkeys([
                    *(rebuilt_selection_alignment.get("blockers") or []),
                    *[
                        f"calendar_split:{item}"
                        for item in rebuilt_selection_schedule.get("blockers") or []
                    ],
                ]))
            manifest_blockers = [
                (
                    f"{manifest.get('symbol')}:"
                    f"{'selection_manifest' if formal else 'projected_manifest'}:"
                    f"{blocker}"
                )
                for manifest in selection_manifests
                if manifest.get("status") != "PASS"
                for blocker in (manifest.get("blockers") or ["status_not_pass"])
            ]
            if manifest_blockers:
                rebuilt_selection_alignment["status"] = "BLOCK"
                rebuilt_selection_alignment["blockers"] = list(dict.fromkeys([
                    *(rebuilt_selection_alignment.get("blockers") or []),
                    *manifest_blockers,
                ]))
        elif selection_datasets:
            blockers.append("research_blocked_alignment_contains_selection_datasets")
        if not formal:
            rebuilt_selection_alignment["projection_policy"] = (
                DEVELOPMENT_SELECTION_SPLIT_POLICY
            )
            rebuilt_selection_alignment["protected_test_rows_persisted"] = False
        reported_alignment_core = dict(reported_selection_alignment)
        reported_alignment_core.pop("input_snapshot", None)
        if reported_alignment_core != rebuilt_selection_alignment:
            blockers.append("research_selection_alignment_semantic_mismatch")
        if reported_selection_schedule != rebuilt_selection_schedule:
            blockers.append(
                "research_selection_calendar_schedule_semantic_mismatch"
                if formal
                else "research_development_selection_schedule_semantic_mismatch"
            )
        selection_boundaries = _mapping(
            rebuilt_selection_schedule.get("symbol_boundaries")
        )
        selection_alignment_passed = (
            rebuilt_selection_alignment.get("status") == "PASS"
        )
        if not selection_alignment_passed:
            blockers.append("research_selection_alignment_rebuild_not_passed")
    for cell in selection_cells:
        variant_id = str(cell.get("variant_id") or "")
        symbol = str(cell.get("symbol") or "").upper()
        variant = _mapping(variant_by_id.get(variant_id))
        selection_keys.append((variant_id, symbol))
        if not variant:
            blockers.append(f"research_selection_variant_unknown:{variant_id or 'UNKNOWN'}")
            continue
        for field in ("strategy_id", "params", "param_hash", "implementation_fingerprint"):
            if cell.get(field) != variant.get(field):
                blockers.append(f"research_selection_identity_mismatch:{variant_id}:{field}")
        if cell.get("phase") != "TRAIN_VALIDATION_SELECTION":
            blockers.append(f"research_selection_phase_invalid:{variant_id}:{symbol}")
        if uses_cell_evidence_v5 or uses_cell_evidence_v4:
            dataset = _mapping(selection_datasets.get(symbol))
            rows = _sequence(dataset.get("rows"))
            boundary = _mapping(selection_boundaries.get(symbol))
            validation_end = boundary.get("validation_end_index")
            train_end = boundary.get("train_end_index")
            if (
                not _native_nonnegative_int(train_end)
                or not _native_nonnegative_int(validation_end)
                or train_end < 1
                or train_end >= validation_end
                or validation_end < 1
                or validation_end > len(rows)
            ):
                blockers.append(
                    f"research_selection_fold_source_context_invalid:{variant_id}:{symbol}"
                )
                selection_prefix_rows: list[dict[str, Any]] = []
            else:
                selection_prefix_rows = [
                    dict(item) for item in rows[:validation_end] if isinstance(item, dict)
                ]
            if uses_cell_evidence_v5:
                blockers.extend(_verify_selection_cell_evidence_v5(
                    cell,
                    variant_id=variant_id,
                    symbol=symbol,
                    implementation_fingerprint=str(
                        variant.get("implementation_fingerprint") or ""
                    ),
                    strategy_id=str(variant.get("strategy_id") or ""),
                    params=_mapping(variant.get("params")),
                    param_hash=str(variant.get("param_hash") or ""),
                    risk=_mapping(variant.get("risk")),
                    selection_rows=selection_prefix_rows,
                    train_end_index=(train_end if _native_nonnegative_int(train_end) else 0),
                    source=str(dataset.get("source") or ""),
                    market=str(dataset.get("market") or ""),
                    timeframe=str(dataset.get("timeframe") or "1D"),
                ))
            else:
                blockers.extend(_verify_selection_cell_evidence_v4(
                    cell,
                    variant_id=variant_id,
                    symbol=symbol,
                    risk=_mapping(variant.get("risk")),
                    selection_rows=selection_prefix_rows,
                    source=str(dataset.get("source") or ""),
                    market=str(dataset.get("market") or ""),
                    timeframe=str(dataset.get("timeframe") or "1D"),
                ))
        elif uses_cell_evidence_v3:
            blockers.extend(_verify_selection_cell_evidence_v3(
                cell,
                variant_id=variant_id,
                symbol=symbol,
                risk=_mapping(variant.get("risk")),
            ))
        elif uses_cell_evidence_v2:
            blockers.extend(_verify_selection_cell_evidence_v2(
                cell,
                variant_id=variant_id,
                symbol=symbol,
            ))
        if cell.get("run_hash") != strategy_research_selection_cell_hash_for_report(
            cell,
            _mapping(variant.get("risk")),
            report_schema_version=report_schema_version,
        ):
            blockers.append(f"research_selection_cell_hash_mismatch:{variant_id}:{symbol}")
    if len(set(selection_keys)) != len(selection_keys):
        blockers.append("research_selection_cell_duplicate")
    expected_selection_keys = {
        (variant_id, symbol) for variant_id in variant_by_id for symbol in selection_symbols
    } if selection_alignment_passed else set()
    if set(selection_keys) != expected_selection_keys:
        blockers.append("research_selection_cell_coverage_mismatch")

    ranking_trial_count = len(variants)
    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        lineage_verification = verify_strategy_research_search_lineage(
            batch_spec.get("search_lineage"),
            expected_search_family_id=str(
                _mapping(batch_spec.get("hypothesis_preregistration")).get(
                    "search_family_id"
                )
                or ""
            ),
            expected_current_trial_count=len(variants),
        )
        blockers.extend(
            f"research_search_lineage:{item}"
            for item in lineage_verification.get("blockers") or []
        )
        cumulative_trial_count = lineage_verification.get(
            "cumulative_trial_count"
        )
        if (
            lineage_verification.get("status") == "PASS"
            and isinstance(cumulative_trial_count, int)
            and not isinstance(cumulative_trial_count, bool)
            and cumulative_trial_count >= len(variants)
        ):
            ranking_trial_count = cumulative_trial_count
    expected_rankings = [
        aggregate_validation_variant(
            variant,
            [cell for cell in selection_cells if cell.get("variant_id") == variant.get("variant_id")],
            required_symbols=len(selection_symbols),
            total_variant_trials=ranking_trial_count,
        )
        for variant in variants
    ] if selection_alignment_passed else []
    expected_rankings.sort(
        key=lambda row: float(row.get("adjusted_score") or -1e9),
        reverse=True,
    )
    if _sequence(report.get("validation_rankings")) != expected_rankings:
        blockers.append("research_validation_rankings_semantic_mismatch")
    parameter_stability_present = "parameter_stability" in report
    parameter_stability = _mapping(report.get("parameter_stability"))
    parameter_stability_schema = str(parameter_stability.get("schema_version") or "")
    expected_stability: dict[str, Any] = {}
    if report_schema_version == LEGACY_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION:
        if parameter_stability_present:
            if parameter_stability_schema != "strategy-parameter-plateau-v1":
                blockers.append("research_legacy_parameter_stability_schema_invalid")
            else:
                expected_stability = build_legacy_parameter_stability_snapshot_v1(expected_rankings)
                if parameter_stability != expected_stability:
                    blockers.append("research_parameter_stability_semantic_mismatch")
    elif report_schema_version in {
        PARAMETER_STABILITY_V2_REPORT_SCHEMA_VERSION,
        SELECTION_CELL_EVIDENCE_V2_REPORT_SCHEMA_VERSION,
        IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
        HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
        COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        if not parameter_stability_present:
            blockers.append("research_parameter_stability_missing")
        elif parameter_stability_schema != "strategy-parameter-plateau-v2":
            blockers.append("research_parameter_stability_schema_invalid")
        else:
            expected_stability = build_parameter_stability_snapshot(
                expected_rankings,
                frozen_variants=[
                    dict(item) for item in _sequence(batch_spec.get("variants"))
                    if isinstance(item, dict)
                ],
            )
            if parameter_stability != expected_stability:
                blockers.append("research_parameter_stability_semantic_mismatch")
    expected_validation_candidates = freeze_validation_candidates(
        expected_rankings,
        max_candidates=int(batch_spec.get("max_test_candidates") or 0),
    )
    if _sequence(report.get("validation_candidates")) != expected_validation_candidates:
        blockers.append("research_validation_candidates_semantic_mismatch")
    expected_admission: dict[str, Any] = {}
    if report_schema_version in PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS:
        if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
            governance = _mapping(report.get("research_governance"))
            admission_verification = (
                verify_strategy_preregistered_failure_admission_v3_receipt(
                    report.get("preregistered_failure_admission"),
                    batch_spec=batch_spec,
                    hypothesis_preregistration=_mapping(
                        batch_spec.get("hypothesis_preregistration")
                    ),
                    parameter_stability=expected_stability,
                    selection_cells=selection_cells,
                    validation_candidates=expected_validation_candidates,
                    registration_context={
                        "ok": formal,
                        "status": "RUNNING" if formal else "BLOCK",
                        "registration_id": str(
                            governance.get("registration_id") or ""
                        ),
                        "protocol": _mapping(governance.get("protocol")),
                        "claim": _mapping(
                            governance.get("single_use_claim_receipt")
                        ),
                        # A completed report can verify the persisted audit
                        # receipt's consistency, not the registry's live state.
                        "registry_audit": {"status": "PASS"},
                    },
                )
            )
            blockers.extend(
                f"research_preregistered_failure_admission:{item}"
                for item in admission_verification.get("blockers") or []
            )
            expected_admission = _mapping(
                admission_verification.get("expected_admission")
            )
        else:
            admission_builder = (
                build_strategy_preregistered_failure_admission_v2
                if report_schema_version
                == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                else build_strategy_preregistered_failure_admission
            )
            expected_admission = admission_builder(
                batch_spec=batch_spec,
                hypothesis_preregistration=_mapping(
                    batch_spec.get("hypothesis_preregistration")
                ),
                parameter_stability=expected_stability,
                selection_cells=selection_cells,
                validation_candidates=expected_validation_candidates,
            )
            if _mapping(report.get("preregistered_failure_admission")) != expected_admission:
                blockers.append("research_preregistered_failure_admission_semantic_mismatch")
        admitted_ids = set(
            str(item or "")
            for item in _sequence(expected_admission.get("admitted_variant_ids"))
        )
        expected_frozen = [
            item for item in expected_validation_candidates
            if formal and str(item.get("variant_id") or "") in admitted_ids
        ]
    else:
        expected_frozen = expected_validation_candidates if formal else []
    if _sequence(report.get("frozen_candidates")) != expected_frozen:
        blockers.append("research_frozen_candidates_semantic_mismatch")

    candidate_by_id = {
        str(item.get("variant_id") or ""): item for item in expected_frozen
    }
    test_cells = [dict(item) for item in _sequence(report.get("test_cells")) if isinstance(item, dict)]
    if len(test_cells) != len(_sequence(report.get("test_cells"))):
        blockers.append("research_test_cell_type_invalid")
    test_keys: list[tuple[str, str]] = []
    for cell in test_cells:
        variant_id = str(cell.get("variant_id") or "")
        symbol = str(cell.get("symbol") or "").upper()
        candidate = _mapping(candidate_by_id.get(variant_id))
        test_keys.append((variant_id, symbol))
        if not candidate:
            blockers.append(f"research_test_variant_unknown:{variant_id or 'UNKNOWN'}")
            continue
        for field in ("strategy_id", "params", "param_hash", "implementation_fingerprint"):
            if cell.get(field) != candidate.get(field):
                blockers.append(f"research_test_identity_mismatch:{variant_id}:{field}")
        if cell.get("phase") != "FROZEN_TEST_ONCE":
            blockers.append(f"research_test_phase_invalid:{variant_id}:{symbol}")
        if uses_frozen_evaluation_replay:
            dataset = _mapping(selection_datasets.get(symbol))
            boundary = _mapping(selection_boundaries.get(symbol))
            blockers.extend(_verify_frozen_evaluation_cell_replay(
                cell,
                role=FROZEN_TEST_ROLE,
                variant_id=variant_id,
                symbol=symbol,
                candidate=candidate,
                rows=[
                    dict(item)
                    for item in _sequence(dataset.get("rows"))
                    if isinstance(item, dict)
                ],
                train_end_index=(
                    boundary.get("train_end_index")
                    if _native_nonnegative_int(
                        boundary.get("train_end_index")
                    )
                    else 0
                ),
                validation_end_index=(
                    boundary.get("validation_end_index")
                    if _native_nonnegative_int(
                        boundary.get("validation_end_index")
                    )
                    else 0
                ),
                source=str(dataset.get("source") or ""),
                market=str(dataset.get("market") or ""),
                timeframe=str(dataset.get("timeframe") or "1D"),
            ))
        elif report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
            blockers.extend(_verify_test_cell_evidence_v1(
                cell,
                variant_id=variant_id,
                symbol=symbol,
                risk=_mapping(candidate.get("risk")),
            ))
        if cell.get("run_hash") != strategy_research_test_cell_hash_for_report(
            cell,
            _mapping(candidate.get("risk")),
            report_schema_version=report_schema_version,
        ):
            blockers.append(f"research_test_cell_hash_mismatch:{variant_id}:{symbol}")
    if len(set(test_keys)) != len(test_keys):
        blockers.append("research_test_cell_duplicate")
    expected_test_keys = {
        (variant_id, symbol) for variant_id in candidate_by_id for symbol in selection_symbols
    }
    if set(test_keys) != expected_test_keys:
        blockers.append("research_test_cell_coverage_mismatch")
    expected_test_results = [
        aggregate_frozen_test(
            candidate,
            [cell for cell in test_cells if cell.get("variant_id") == candidate.get("variant_id")],
            required_symbols=len(selection_symbols),
        )
        for candidate in expected_frozen
    ]
    if _sequence(report.get("test_results")) != expected_test_results:
        blockers.append("research_test_results_semantic_mismatch")

    holdout_candidates = [row for row in expected_test_results if row.get("eligible_for_holdout") is True]
    holdout_candidate_by_id = {
        str(item.get("variant_id") or ""): item for item in holdout_candidates
    }
    confirmation_datasets = {
        str(item.get("symbol") or "").upper(): item
        for item in _sequence(
            _mapping(report.get("dataset_snapshot")).get("datasets")
        )
        if isinstance(item, dict) and item.get("role") == "CONFIRMATION"
    }
    reported_holdout_schedule = _mapping(
        report.get("holdout_calendar_schedule")
    )
    holdout_context_blockers: list[str] = []
    rebuilt_holdout_schedule: dict[str, Any] = {}
    rebuilt_holdout_alignment: dict[str, Any] = {}
    rebuilt_holdout_payloads: dict[str, dict[str, Any]] = {}
    holdout_replay_ready = False
    if uses_frozen_evaluation_replay and holdout_candidates:
        confirmation_manifests = [
            item for item in all_manifests if item.get("role") == "CONFIRMATION"
        ]
        verified_selection_alignment = _mapping(
            rebuilt_selection_alignment
        )
        rebuilt_holdout_context = (
            rebuild_strategy_frozen_confirmation_context(
                datasets=confirmation_datasets,
                expected_symbols=holdout_symbols,
                manifests=confirmation_manifests,
                split_policy=_mapping(batch_spec.get("split_policy")),
                data_policy=_mapping(batch_spec.get("data_policy")),
                required_start=str(
                    verified_selection_alignment.get("common_start") or ""
                ),
                required_as_of=str(
                    verified_selection_alignment.get("common_as_of") or ""
                ),
                reported_alignment=report.get("holdout_alignment"),
                reported_schedule=reported_holdout_schedule,
            )
        )
        holdout_context_blockers.extend(
            str(item)
            for item in rebuilt_holdout_context.get("blockers") or []
        )
        rebuilt_holdout_payloads = _mapping(
            rebuilt_holdout_context.get("payloads")
        )
        rebuilt_holdout_alignment = _mapping(
            rebuilt_holdout_context.get("alignment")
        )
        rebuilt_holdout_schedule = _mapping(
            rebuilt_holdout_context.get("schedule")
        )
        holdout_replay_ready = not holdout_context_blockers
        blockers.extend(
            f"research_{item}" for item in holdout_context_blockers
        )
    elif uses_frozen_evaluation_replay:
        expected_not_run = {
            "status": "NOT_RUN",
            "blockers": [
                "no_test_candidate"
                if formal
                else "formal_registration_required"
            ],
        }
        if confirmation_datasets:
            blockers.append(
                "research_unexpected_holdout_confirmation_datasets"
            )
        if _mapping(report.get("holdout_alignment")) != expected_not_run:
            blockers.append(
                "research_holdout_alignment_not_run_semantic_mismatch"
            )
        if reported_holdout_schedule != expected_not_run:
            blockers.append(
                "research_holdout_calendar_schedule_not_run_semantic_mismatch"
            )
    holdout_cells = [dict(item) for item in _sequence(report.get("holdout_cells")) if isinstance(item, dict)]
    if len(holdout_cells) != len(_sequence(report.get("holdout_cells"))):
        blockers.append("research_holdout_cell_type_invalid")
    holdout_keys: list[tuple[str, str]] = []
    for cell in holdout_cells:
        variant_id = str(cell.get("variant_id") or "")
        symbol = str(cell.get("symbol") or "").upper()
        candidate = _mapping(holdout_candidate_by_id.get(variant_id))
        holdout_keys.append((variant_id, symbol))
        if not candidate:
            blockers.append(f"research_holdout_variant_unknown:{variant_id or 'UNKNOWN'}")
            continue
        identity_fields = (
            ("strategy_id", "params", "param_hash", "implementation_fingerprint")
            if uses_frozen_evaluation_replay
            else ("strategy_id",)
        )
        for field in identity_fields:
            if cell.get(field) != candidate.get(field):
                blockers.append(
                    f"research_holdout_identity_mismatch:{variant_id}:{field}"
                )
        if uses_frozen_evaluation_replay:
            dataset = _mapping(confirmation_datasets.get(symbol))
            boundary = _mapping(
                _mapping(rebuilt_holdout_schedule.get("symbol_boundaries")).get(
                    symbol
                )
            )
            blockers.extend(_verify_frozen_evaluation_cell_replay(
                cell,
                role=HOLDOUT_CONFIRMATION_ROLE,
                variant_id=variant_id,
                symbol=symbol,
                candidate=candidate,
                rows=[
                    dict(item)
                    for item in _sequence(
                        _mapping(rebuilt_holdout_payloads.get(symbol)).get(
                            "rows"
                        )
                    )
                    if isinstance(item, dict)
                ],
                train_end_index=(
                    boundary.get("train_end_index")
                    if _native_nonnegative_int(
                        boundary.get("train_end_index")
                    )
                    else 0
                ),
                validation_end_index=(
                    boundary.get("validation_end_index")
                    if _native_nonnegative_int(
                        boundary.get("validation_end_index")
                    )
                    else 0
                ),
                source=str(dataset.get("source") or ""),
                market=str(dataset.get("market") or ""),
                timeframe=str(dataset.get("timeframe") or "1D"),
            ))
        if cell.get("run_hash") != strategy_research_holdout_cell_hash_for_report(
            cell,
            candidate,
            report_schema_version=report_schema_version,
        ):
            blockers.append(f"research_holdout_cell_hash_mismatch:{variant_id}:{symbol}")
    if len(set(holdout_keys)) != len(holdout_keys):
        blockers.append("research_holdout_cell_duplicate")
    holdout_alignment_passed = (
        holdout_replay_ready
        if uses_frozen_evaluation_replay
        else _mapping(report.get("holdout_alignment")).get("status") == "PASS"
    )
    expected_holdout_keys = {
        (variant_id, symbol) for variant_id in holdout_candidate_by_id for symbol in holdout_symbols
    } if holdout_alignment_passed else set()
    if set(holdout_keys) != expected_holdout_keys:
        blockers.append("research_holdout_cell_coverage_mismatch")

    expected_holdout_results: list[dict[str, Any]] = []
    for candidate in holdout_candidates:
        summary = aggregate_holdout_confirmation(
            candidate,
            [cell for cell in holdout_cells if cell.get("variant_id") == candidate.get("variant_id")],
            required_symbols=len(holdout_symbols),
        )
        summary.update({
            "variant_id": candidate.get("variant_id"),
            "params": candidate.get("params"),
            "param_hash": candidate.get("param_hash"),
        })
        if not holdout_alignment_passed:
            summary["status"] = "BLOCK"
            summary["forward_candidate"] = False
            summary["blockers"] = list(dict.fromkeys([
                *(summary.get("blockers") or []),
                *[
                    f"holdout_alignment:{item}"
                    for item in (
                        holdout_context_blockers
                        if uses_frozen_evaluation_replay
                        else _mapping(report.get("holdout_alignment")).get("blockers") or []
                    )
                ],
            ]))
        expected_holdout_results.append(summary)
    if _sequence(report.get("holdout_results")) != expected_holdout_results:
        blockers.append("research_holdout_results_semantic_mismatch")
    expected_forward = [
        str(row.get("variant_id") or "")
        for row in expected_holdout_results
        if row.get("forward_candidate") is True
    ]
    if _sequence(report.get("forward_candidates")) != expected_forward:
        blockers.append("research_forward_candidates_semantic_mismatch")
    return blockers


def verify_strategy_research_report(
    report: dict[str, Any] | Any,
    *,
    require_formal: bool = True,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(report, dict):
        blockers.append("research_report_type_invalid")
    report = _mapping(report)
    required_types = {
        "batch_spec": dict,
        "dataset_manifest": list,
        "dataset_snapshot": dict,
        "selection_alignment": dict,
        "selection_calendar_schedule": dict,
        "selection_cells": list,
        "validation_rankings": list,
        "validation_candidates": list,
        "frozen_candidates": list,
        "test_cells": list,
        "test_results": list,
        "holdout_alignment": dict,
        "holdout_calendar_schedule": dict,
        "holdout_cells": list,
        "holdout_results": list,
        "forward_candidates": list,
        "summary": dict,
        "research_governance": dict,
    }
    for field, expected_type in required_types.items():
        if not isinstance(report.get(field), expected_type):
            blockers.append(f"research_field_type_invalid:{field}")
    report_schema_version = report.get("schema_version")
    if report_schema_version not in SUPPORTED_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS:
        blockers.append("research_report_schema_invalid")
    if report_schema_version in PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS:
        if not isinstance(report.get("preregistered_failure_admission"), dict):
            blockers.append(
                "research_field_type_invalid:preregistered_failure_admission"
            )
    elif "preregistered_failure_admission" in report:
        blockers.append(
            "research_legacy_schema_has_preregistered_failure_admission"
        )
    if (
        report.get("research_only") is not True
        or report.get("paper_authorized") is not False
        or report.get("live_order_allowed") is not False
    ):
        blockers.append("research_report_has_execution_authority")
    if report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
        blockers.extend(
            f"research_execution_authority:{path}"
            for path in authority_violations(report)
        )

    batch_spec = _mapping(report.get("batch_spec"))
    declared_report_schema = batch_spec.get("report_schema_version")
    if report_schema_version in IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSIONS:
        if declared_report_schema != report_schema_version:
            blockers.append("research_report_schema_declaration_invalid")
    elif declared_report_schema is not None and declared_report_schema != report_schema_version:
        blockers.append("research_report_schema_declaration_mismatch")
    if batch_spec.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        blockers.append("research_batch_schema_invalid")
    if batch_spec.get("research_schema_version") != STRATEGY_RESEARCH_SCHEMA_VERSION:
        blockers.append("research_nested_schema_invalid")
    if batch_spec.get("workflow") != STRATEGY_RESEARCH_WORKFLOW:
        blockers.append("research_workflow_invalid")
    if batch_spec.get("optimizer_used") is not False or batch_spec.get("fixed_parameter_grid_used") is not True:
        blockers.append("research_parameter_policy_invalid")
    if (
        batch_spec.get("research_only") is not True
        or batch_spec.get("paper_authorized") is not False
        or batch_spec.get("live_order_allowed") is not False
    ):
        blockers.append("research_batch_has_execution_authority")
    selection_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("selection_symbols"))
    }
    holdout_symbols = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("confirmation_symbols"))
    }
    if not selection_symbols or not holdout_symbols or selection_symbols & holdout_symbols:
        blockers.append("research_symbol_roles_invalid")

    if report_schema_version in IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSIONS:
        implementation = report.get("implementation_manifest")
        if not isinstance(implementation, dict):
            blockers.append("research_field_type_invalid:implementation_manifest")
            implementation_verification = {
                "status": "BLOCK",
                "blockers": ["implementation_manifest_type_invalid"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        else:
            implementation_verification = verify_embedded_implementation_manifest(implementation)
        blockers.extend(
            f"research_implementation:{item}"
            for item in implementation_verification.get("blockers") or []
        )
    else:
        implementation_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    if report_schema_version in HYPOTHESIS_BOUND_REPORT_SCHEMA_VERSIONS:
        hypothesis = batch_spec.get("hypothesis_preregistration")
        hypothesis_verification = verify_strategy_hypothesis_preregistration(
            hypothesis,
            expected_strategy_ids=[
                str(item or "") for item in _sequence(batch_spec.get("strategies"))
            ],
            expected_research_generation=str(
                batch_spec.get("research_generation") or ""
            ),
            expected_schema_version=(
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                if report_schema_version
                == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
                else (
                    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
                    if report_schema_version
                    == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                    else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION
                )
            ),
        )
        blockers.extend(
            f"research_hypothesis:{item}"
            for item in hypothesis_verification.get("blockers") or []
        )
        if str(batch_spec.get("hypothesis_preregistration_hash") or "") != str(
            _mapping(hypothesis).get("hypothesis_hash") or ""
        ):
            blockers.append("research_hypothesis_hash_binding_mismatch")
    else:
        hypothesis_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "hypothesis_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if (
            "hypothesis_preregistration" in batch_spec
            or "hypothesis_preregistration_hash" in batch_spec
        ):
            blockers.append("research_legacy_schema_has_hypothesis_contract")

    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        lineage_verification = verify_strategy_research_search_lineage(
            batch_spec.get("search_lineage"),
            expected_search_family_id=str(
                _mapping(batch_spec.get("hypothesis_preregistration")).get(
                    "search_family_id"
                )
                or ""
            ),
            expected_current_trial_count=len(
                _sequence(batch_spec.get("variants"))
            ),
        )
        blockers.extend(
            f"research_search_lineage:{item}"
            for item in lineage_verification.get("blockers") or []
        )
    else:
        lineage_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "lineage_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if "search_lineage" in batch_spec:
            blockers.append("research_legacy_schema_has_search_lineage")

    dataset_manifest = _sequence(report.get("dataset_manifest"))
    expected_batch_hash = canonical_hash(batch_spec)
    expected_dataset_hash = canonical_hash(dataset_manifest)
    expected_result_hash = strategy_research_result_hash(report)
    if str(report.get("batch_spec_hash") or "") != expected_batch_hash:
        blockers.append("research_batch_spec_hash_mismatch")
    if str(report.get("dataset_manifest_hash") or "") != expected_dataset_hash:
        blockers.append("research_dataset_manifest_hash_mismatch")
    if str(report.get("batch_run_hash") or "") != expected_result_hash:
        blockers.append("research_result_hash_mismatch")
    blockers.extend(_verify_dataset_snapshot(
        report,
        batch_spec=batch_spec,
        expected_batch_hash=expected_batch_hash,
        dataset_manifest=dataset_manifest,
        expected_dataset_hash=expected_dataset_hash,
    ))

    governance = _mapping(report.get("research_governance"))
    formal = governance.get("status") == "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE"
    governance_audit: dict[str, Any]
    if formal:
        governance_audit = verify_matrix_research_governance(
            governance,
            report_created_at_ms=_created_at_ms(report.get("created_at")),
            batch_spec_hash=expected_batch_hash,
            result_hash=expected_result_hash,
            dataset_manifest_hash=expected_dataset_hash,
        )
        blockers.extend(governance_audit.get("blockers") or [])
        if batch_spec.get("selection_test_policy") != "BLIND_ONCE":
            blockers.append("research_formal_policy_invalid")
        if str(_mapping(report.get("dataset_snapshot")).get("registration_id") or "") != str(
            governance.get("registration_id") or ""
        ):
            blockers.append("research_dataset_snapshot_registration_mismatch")
    else:
        clean_governance = dict(governance)
        expected_governance_hash = str(clean_governance.pop("governance_hash", "") or "")
        development_blockers: list[str] = []
        if not expected_governance_hash or canonical_hash(clean_governance) != expected_governance_hash:
            development_blockers.append("research_development_governance_hash_invalid")
        if governance.get("status") != "DEVELOPMENT_SELECTION_ONLY":
            development_blockers.append("research_development_status_invalid")
        if governance.get("development_only") is not True or governance.get("single_use_claim") is not False:
            development_blockers.append("research_development_policy_invalid")
        if (
            governance.get("test_rows_evaluated") is not False
            or governance.get("holdout_data_loaded") is not False
            or governance.get("protected_test_rows_persisted") is not False
        ):
            development_blockers.append("research_development_isolation_claim_invalid")
        if batch_spec.get("selection_test_policy") != "DEVELOPMENT_ONLY":
            development_blockers.append("research_development_batch_policy_invalid")
        if any(_sequence(report.get(field)) for field in (
            "frozen_candidates",
            "test_cells",
            "test_results",
            "holdout_cells",
            "holdout_results",
            "forward_candidates",
        )):
            development_blockers.append("research_development_touched_protected_stage")
        if (
            governance.get("research_only") is not True
            or governance.get("paper_authorized") is not False
            or governance.get("live_order_allowed") is not False
        ):
            development_blockers.append("research_development_has_execution_authority")
        blockers.extend(development_blockers)
        governance_audit = {
            "status": "PASS" if not development_blockers else "BLOCK",
            "blockers": development_blockers,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if require_formal:
            blockers.append("research_report_not_formal_single_use")

    blockers.extend(_verify_research_semantics(
        report,
        batch_spec=batch_spec,
        formal=formal,
    ))
    if not formal:
        blockers.extend(_verify_development_projection(
            report,
            batch_spec=batch_spec,
            selection_symbols=selection_symbols,
        ))

    validation_ids = {
        str(row.get("variant_id") or "")
        for row in _sequence(report.get("validation_candidates"))
        if isinstance(row, dict)
    }
    frozen = {
        str(row.get("variant_id") or ""): row
        for row in _sequence(report.get("frozen_candidates"))
        if isinstance(row, dict)
    }
    if not set(frozen).issubset(validation_ids):
        blockers.append("research_frozen_candidate_not_selected")
    test_results = {
        str(row.get("variant_id") or ""): row
        for row in _sequence(report.get("test_results"))
        if isinstance(row, dict)
    }
    if not set(test_results).issubset(frozen):
        blockers.append("research_test_candidate_not_frozen")
    eligible_holdout = {
        variant_id for variant_id, row in test_results.items()
        if row.get("eligible_for_holdout") is True
    }
    holdout_cell_ids = {
        str(row.get("variant_id") or "")
        for row in _sequence(report.get("holdout_cells"))
        if isinstance(row, dict)
    }
    if not holdout_cell_ids.issubset(eligible_holdout):
        blockers.append("research_holdout_cell_without_test_pass")
    for variant_id, test_result in test_results.items():
        frozen_lane = str(_mapping(frozen.get(variant_id)).get("selection_lane") or "")
        if str(test_result.get("test_lane") or "") != frozen_lane:
            blockers.append(f"research_test_lane_drift:{variant_id}")
    forward_ids = set(str(item or "") for item in _sequence(report.get("forward_candidates")))
    passed_holdout_ids = {
        str(row.get("variant_id") or "")
        for row in _sequence(report.get("holdout_results"))
        if isinstance(row, dict) and row.get("forward_candidate") is True
    }
    if forward_ids != passed_holdout_ids:
        blockers.append("research_forward_candidate_mismatch")

    summary = _mapping(report.get("summary"))
    expected_counts = {
        "selection_cells": len(_sequence(report.get("selection_cells"))),
        "frozen_test_candidates": len(_sequence(report.get("frozen_candidates"))),
        "test_cells": len(_sequence(report.get("test_cells"))),
        "holdout_cells": len(_sequence(report.get("holdout_cells"))),
        "forward_candidates": len(_sequence(report.get("forward_candidates"))),
    }
    for field, expected in expected_counts.items():
        if summary.get(field) != expected:
            blockers.append(f"research_summary_count_mismatch:{field}")
    admission = _mapping(report.get("preregistered_failure_admission"))
    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        admission_verification = (
            verify_strategy_preregistered_failure_admission_v3_receipt(
                admission,
                batch_spec=batch_spec,
                hypothesis_preregistration=_mapping(
                    batch_spec.get("hypothesis_preregistration")
                ),
                parameter_stability=_mapping(report.get("parameter_stability")),
                selection_cells=[
                    dict(item)
                    for item in _sequence(report.get("selection_cells"))
                    if isinstance(item, dict)
                ],
                validation_candidates=[
                    dict(item)
                    for item in _sequence(report.get("validation_candidates"))
                    if isinstance(item, dict)
                ],
                registration_context={
                    "ok": formal,
                    "status": "RUNNING" if formal else "BLOCK",
                    "registration_id": str(
                        governance.get("registration_id") or ""
                    ),
                    "protocol": _mapping(governance.get("protocol")),
                    "claim": _mapping(
                        governance.get("single_use_claim_receipt")
                    ),
                    "registry_audit": {"status": "PASS"},
                },
            )
        )
    else:
        admission_verification = {
            "status": (
                "PASS"
                if report_schema_version
                in PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS
                else "NOT_REQUIRED"
            ),
            "blockers": [],
            "verification_scope": "LEGACY_REPORT_SEMANTICS",
            "live_registry_verified": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if report_schema_version in PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS:
        if summary.get("preregistered_failure_admission_status") != admission.get(
            "status"
        ):
            blockers.append("research_summary_admission_status_mismatch")
        if summary.get("preregistered_failure_admitted_candidates") != len(
            _sequence(admission.get("admitted_variant_ids"))
        ):
            blockers.append("research_summary_admission_count_mismatch")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "formal_single_use": formal,
        "outcome_status": "FORWARD_CANDIDATE" if forward_ids else "NO_FORWARD_CANDIDATE",
        "batch_spec_hash": expected_batch_hash,
        "dataset_manifest_hash": expected_dataset_hash,
        "batch_run_hash": expected_result_hash,
        "governance_verification": governance_audit,
        "implementation_manifest_verification": implementation_verification,
        "hypothesis_preregistration_verification": hypothesis_verification,
        "search_lineage_verification": lineage_verification,
        "preregistered_failure_admission_verification": admission_verification,
        "preregistered_failure_admission_status": (
            str(admission.get("status") or "BLOCK")
            if report_schema_version
            in PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSIONS
            else "NOT_REQUIRED"
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
