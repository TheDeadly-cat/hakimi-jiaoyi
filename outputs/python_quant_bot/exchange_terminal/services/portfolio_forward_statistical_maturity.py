from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any

from .execution_authority import authority_violations
from .portfolio_candidate import PORTFOLIO_CANDIDATE_SCHEMA_VERSION
from .portfolio_evidence_archive import verify_portfolio_backup_status
from .portfolio_forward_local_source_anchor import (
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
    portfolio_local_source_observer_projection_from_chain,
    normalize_portfolio_local_source_settlement_projection,
    portfolio_local_source_projection_hashes,
    verify_portfolio_forward_local_source_anchor,
)
from .portfolio_forward_performance import (
    PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    build_forward_performance_readiness,
    forward_evidence_thresholds_from_spec,
    forward_evidence_thresholds_v3_from_spec,
)
from .portfolio_forward_statistical_audit import (
    FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS,
    FORWARD_STATISTICAL_AUDIT_V2_CONTENT_FIELDS,
    PORTFOLIO_FORWARD_DECISION_POLICY,
    PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
    _historical_contract,
    _v2_historical_safe_integer_blockers,
    _v2_prefix_risk_acceptance,
    first_joint_maturity_prefix,
    forward_statistical_audit_content,
    forward_statistical_audit_v2_content,
)
from .portfolio_shadow import (
    PORTFOLIO_SHADOW_SCHEMA_VERSION,
    verify_forward_status_artifact,
)
from .portfolio_forward_watchdog import verify_portfolio_forward_watchdog_status
from .portfolio_statistical_audit import (
    DEFAULT_BLOCK_LENGTH,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_MINIMUM_OBSERVATIONS,
    DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
    DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
    DEFAULT_RESAMPLE_COUNT,
    PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
    audit_paired_equity_curve_stage,
    statistical_bootstrap_budget_blockers,
)


PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V1_SCHEMA_VERSION = (
    "portfolio-forward-statistical-maturity-v1"
)
PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION = (
    "portfolio-forward-statistical-maturity-v2"
)
PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION = (
    "portfolio-forward-statistical-maturity-v3"
)
PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION = (
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION
)
PORTFOLIO_FORWARD_SOURCE_BINDING_SCHEMA_VERSION = (
    "portfolio-forward-source-binding-v1"
)
_BACKUP_STATUS_V1_SCHEMA_VERSION = "portfolio-forward-backup-status-v1"
_BACKUP_STATUS_V2_SCHEMA_VERSION = "portfolio-forward-backup-status-v2"
_WATCHDOG_V2_SCHEMA_VERSION = "portfolio-forward-watchdog-v2"
_WATCHDOG_V3_SCHEMA_VERSION = "portfolio-forward-watchdog-v3"

_PROGRESS_FIELDS = (
    "forward_outcomes",
    "required_forward_outcomes",
    "remaining_forward_outcomes",
    "settlements",
    "captured_observations",
    "executed_rebalances",
    "required_executed_rebalances",
    "remaining_executed_rebalances",
)
_SERIES_ROW_FIELDS = {
    "date",
    "settlement_type",
    "settlement_hash",
    "previous_settlement_hash",
    "strategy_equity",
    "benchmark_equity",
    "strategy_daily_return_pct",
    "benchmark_daily_return_pct",
    "rebalance_executed",
}
_SERIES_FIELDS = {
    "schema_version",
    "candidate_hash",
    "settlement_count",
    "outcome_period_count",
    "rebalance_execution_count",
    "first_settlement_date",
    "last_settlement_date",
    "first_settlement_hash",
    "latest_settlement_hash",
    "ordered_settlement_hashes",
    "rows",
    "source_validation",
    "research_only",
    "observation_only",
    "simulation_only",
    "paper_authorized",
    "live_order_allowed",
    "series_hash",
}
_FORWARD_AUDIT_RECEIPT_FIELDS = {
    "generated_at",
    "audit_hash",
    "verification_status",
    "verification_blockers",
    "semantic_recomputed",
}
_COPIED_STATISTICAL_CONTRACT_FIELDS = (
    "method",
    "periods_per_year",
    "resample_count",
    "block_length",
    "confidence_level",
    "required_positive_probability",
    "required_selection_adjusted_probability",
    "selection_adjustment",
    "selection_trial_count",
)
_MAX_SERIES_SETTLEMENTS = 1_024
_STATUS_MAP = {
    "COLLECTING": "NOT_DUE",
    "RESEARCH_REVIEW_READY": "REVIEW_REQUIRED",
    "RESEARCH_REVIEW_BLOCKED": "STOP_RESEARCH",
    "BLOCK": "BLOCK",
}
_MAX_CLOCK_SKEW_MS = 5_000
_WATCHDOG_RECEIPT_STALE_AFTER_MS = 45 * 60 * 1_000
_BACKUP_RECEIPT_STALE_AFTER_MS = 36 * 60 * 60 * 1_000
_SOURCE_BINDING_STATUSES = {
    "FULL",
    "PREFIX",
    "CONTRADICTION",
    "NOT_AVAILABLE",
}


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _strict_timestamp(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _strict_nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _strict_positive_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _close(left: Any, right: Any, *, tolerance: float = 2e-5) -> bool:
    left_number = _finite_number(left)
    right_number = _finite_number(right)
    return (
        left_number is not None
        and right_number is not None
        and abs(left_number - right_number) <= tolerance
    )


def _iso_date(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 10:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return ""


def _empty_progress() -> dict[str, int]:
    return {field: 0 for field in _PROGRESS_FIELDS}


def _source_binding(
    *,
    status: str,
    current_observation_count: int = 0,
    anchored_observation_count: int = 0,
    current_settlement_count: int = 0,
    anchored_settlement_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_FORWARD_SOURCE_BINDING_SCHEMA_VERSION,
        "status": (
            status if status in _SOURCE_BINDING_STATUSES else "CONTRADICTION"
        ),
        "trust_scope": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
        "current_observation_count": max(int(current_observation_count), 0),
        "anchored_observation_count": max(int(anchored_observation_count), 0),
        "current_settlement_count": max(int(current_settlement_count), 0),
        "anchored_settlement_count": max(int(anchored_settlement_count), 0),
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _projection(
    *,
    status: str,
    candidate_hash: str = "",
    progress: dict[str, int] | None = None,
    source_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
        "status": status if status in set(_STATUS_MAP.values()) else "BLOCK",
        "candidate_hash": candidate_hash,
        "progress": dict(progress or _empty_progress()),
        "source_binding": dict(
            source_binding or _source_binding(status="NOT_AVAILABLE")
        ),
        "verification_scope": (
            "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY"
        ),
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _projection_v3(
    *,
    status: str,
    candidate_hash: str = "",
    progress: dict[str, int] | None = None,
    source_binding: dict[str, Any] | None = None,
    decision_status: str = "BLOCK",
    research_action: str = "BLOCK",
    decision_hash: str = "",
    stage_hash: str = "",
    risk_acceptance_hash: str = "",
    first_due_settlement_hash: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        "status": status if status in set(_STATUS_MAP.values()) else "BLOCK",
        "candidate_hash": candidate_hash,
        "progress": dict(progress or _empty_progress()),
        "source_binding": dict(
            source_binding or _source_binding(status="NOT_AVAILABLE")
        ),
        "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "decision_status": (
            decision_status
            if decision_status in {"NOT_DUE", "PASS", "BLOCK"}
            else "BLOCK"
        ),
        "research_action": (
            research_action
            if research_action in {
                "COLLECT_MORE",
                "REVIEW_REQUIRED",
                "STOP_RESEARCH",
                "BLOCK",
            }
            else "BLOCK"
        ),
        "decision_hash": decision_hash if _sha256_hex(decision_hash) else "",
        "stage_hash": stage_hash if _sha256_hex(stage_hash) else "",
        "risk_acceptance_hash": (
            risk_acceptance_hash if _sha256_hex(risk_acceptance_hash) else ""
        ),
        "first_due_settlement_hash": (
            first_due_settlement_hash
            if _sha256_hex(first_due_settlement_hash)
            else ""
        ),
        "verification_scope": (
            "PERSISTED_READINESS_V3_AND_FIRST_JOINT_MATURITY_DECISION_REBUILT_"
            "FROM_EMBEDDED_FULL_SERIES_NO_SETTLEMENT_REPLAY"
        ),
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _canonical_candidate(candidate: dict[str, Any]) -> tuple[str, str] | None:
    payload = dict(candidate or {})
    declared_hash = str(payload.pop("candidate_hash", "") or "")
    spec = dict(candidate.get("spec") or {})
    spec_hash = _canonical_hash(spec)
    if (
        candidate.get("schema_version") != PORTFOLIO_CANDIDATE_SCHEMA_VERSION
        or candidate.get("status") != "FROZEN_DEVELOPMENT_CANDIDATE"
        or len(declared_hash) != 64
        or declared_hash != _canonical_hash(payload)
        or str(candidate.get("spec_hash") or "") != spec_hash
        or candidate.get("fresh_holdout_required") is not True
        or candidate.get("forward_observation_required") is not True
        or str(candidate.get("authorization_state") or "")
        != "BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD"
        or candidate.get("research_only") is not True
        or candidate.get("paper_authorized") is not False
        or candidate.get("live_order_allowed") is not False
        or authority_violations(candidate)
    ):
        return None
    return declared_hash, spec_hash


def _validated_shadow_audit(
    shadow_audit: dict[str, Any],
    *,
    candidate_hash: str,
) -> dict[str, Any] | None:
    count_fields = (
        "observation_count",
        "valid_observation_count",
        "timely_observation_count",
        "externally_attested_observation_count",
        "activation_verified_observation_count",
        "forward_state_verified_observation_count",
        "clock_attestation_violation_count",
        "candidate_activation_violation_count",
        "risk_pass_observation_count",
        "planned_rebalance_count",
        "observation_chain_count",
        "risk_reassessment_count",
        "risk_block_reassessment_count",
        "capture_violation_count",
        "neutral_capture_event_count",
        "missed_capture_count",
        "decision_replay_conflict_count",
        "execution_authority_violation_count",
    )
    counts = {
        field: _strict_nonnegative_integer(shadow_audit.get(field))
        for field in count_fields
    }
    observation_chain = shadow_audit.get("observation_chain")
    integrity_violations = shadow_audit.get("integrity_violations")
    capture_event_types = shadow_audit.get("capture_event_types")
    if (
        any(value is None for value in counts.values())
        or shadow_audit.get("schema_version") != PORTFOLIO_SHADOW_SCHEMA_VERSION
        or shadow_audit.get("status") != "PASS"
        or shadow_audit.get("candidate_hash") != candidate_hash
        or not isinstance(observation_chain, list)
        or not isinstance(integrity_violations, list)
        or integrity_violations != []
        or not isinstance(capture_event_types, dict)
        or shadow_audit.get("observation_only") is not True
        or shadow_audit.get("paper_authorized") is not False
        or shadow_audit.get("live_order_allowed") is not False
    ):
        return None

    valid_count = int(counts["valid_observation_count"])
    if (
        counts["observation_count"] != valid_count
        or counts["timely_observation_count"] != valid_count
        or counts["externally_attested_observation_count"] != valid_count
        or counts["activation_verified_observation_count"] != valid_count
        or counts["forward_state_verified_observation_count"] != valid_count
        or counts["clock_attestation_violation_count"] != 0
        or counts["candidate_activation_violation_count"] != 0
        or int(counts["risk_pass_observation_count"]) > valid_count
        or int(counts["planned_rebalance_count"]) > valid_count
        or counts["observation_chain_count"] != valid_count
        or len(observation_chain) != valid_count
        or counts["risk_block_reassessment_count"]
        > int(counts["risk_reassessment_count"])
        or counts["capture_violation_count"] != 0
        or counts["missed_capture_count"] != 0
        or counts["decision_replay_conflict_count"] != 0
        or counts["execution_authority_violation_count"] != 0
    ):
        return None

    clean_capture_types: dict[str, int] = {}
    for event_type, raw_count in capture_event_types.items():
        event_count = _strict_nonnegative_integer(raw_count)
        if (
            not isinstance(event_type, str)
            or event_type != "PRE_ACTIVATION_SKIPPED"
            or event_count is None
            or event_count == 0
        ):
            return None
        clean_capture_types[event_type] = event_count
    if sum(clean_capture_types.values()) != counts["neutral_capture_event_count"]:
        return None

    chain_dates: list[str] = []
    for raw_item in observation_chain:
        if (
            not isinstance(raw_item, dict)
            or set(raw_item)
            != {"signal_date", "observation_hash", "change_projection_hash"}
        ):
            return None
        signal_date = _iso_date(raw_item.get("signal_date"))
        if (
            not signal_date
            or raw_item.get("signal_date") != signal_date
            or not _sha256_hex(raw_item.get("observation_hash"))
            or not _sha256_hex(raw_item.get("change_projection_hash"))
        ):
            return None
        chain_dates.append(signal_date)
    if (
        chain_dates != sorted(chain_dates)
        or len(chain_dates) != len(set(chain_dates))
        or shadow_audit.get("observation_chain_hash")
        != _canonical_hash(observation_chain)
        or shadow_audit.get("first_signal_date")
        != (chain_dates[0] if chain_dates else "")
        or shadow_audit.get("last_signal_date")
        != (chain_dates[-1] if chain_dates else "")
    ):
        return None

    latest_hash_fields = (
        "latest_dataset_hash",
        "latest_decision_hash",
        "latest_observation_hash",
        "latest_forward_state_contract_hash",
        "latest_observation_risk_snapshot_hash",
    )
    if valid_count:
        if (
            not all(_sha256_hex(shadow_audit.get(field)) for field in latest_hash_fields)
            or shadow_audit.get("latest_observation_hash")
            != observation_chain[-1]["observation_hash"]
        ):
            return None
    elif not all(shadow_audit.get(field) == "" for field in latest_hash_fields):
        return None
    return {
        "signal_dates": chain_dates,
        "valid_observation_count": valid_count,
        "observation_chain": [dict(item) for item in observation_chain],
    }


def _validated_forward_series(
    series: dict[str, Any],
    *,
    candidate_hash: str,
) -> dict[str, Any] | None:
    if not isinstance(series, dict) or set(series) != _SERIES_FIELDS:
        return None
    settlement_count = _strict_nonnegative_integer(series.get("settlement_count"))
    ordered_hashes = series.get("ordered_settlement_hashes")
    raw_rows = series.get("rows")
    if (
        settlement_count is None
        or settlement_count > _MAX_SERIES_SETTLEMENTS
        or not isinstance(ordered_hashes, list)
        or not isinstance(raw_rows, list)
        or len(ordered_hashes) != settlement_count
        or len(raw_rows) != settlement_count
        or not all(_sha256_hex(item) for item in ordered_hashes)
    ):
        return None

    rows: list[dict[str, Any]] = []
    dates: list[str] = []
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, dict) or set(raw_row) != _SERIES_ROW_FIELDS:
            return None
        row = dict(raw_row)
        row_date = _iso_date(row.get("date"))
        strategy_equity = _finite_number(row.get("strategy_equity"))
        benchmark_equity = _finite_number(row.get("benchmark_equity"))
        strategy_return = _finite_number(row.get("strategy_daily_return_pct"))
        benchmark_return = _finite_number(row.get("benchmark_daily_return_pct"))
        expected_type = "BASELINE" if index == 0 else "DAILY_CLOSE"
        expected_previous_hash = "" if index == 0 else str(ordered_hashes[index - 1])
        if (
            not row_date
            or row.get("date") != row_date
            or row.get("settlement_type") != expected_type
            or row.get("settlement_hash") != ordered_hashes[index]
            or row.get("previous_settlement_hash") != expected_previous_hash
            or strategy_equity is None
            or strategy_equity <= 0
            or benchmark_equity is None
            or benchmark_equity <= 0
            or strategy_return is None
            or benchmark_return is None
            or not isinstance(row.get("rebalance_executed"), bool)
        ):
            return None
        if index == 0:
            if (
                row.get("rebalance_executed") is not False
                or not _close(strategy_return, 0.0)
                or not _close(benchmark_return, 0.0)
            ):
                return None
        else:
            previous = rows[index - 1]
            expected_strategy_return = (
                strategy_equity / float(previous["strategy_equity"]) - 1.0
            ) * 100.0
            expected_benchmark_return = (
                benchmark_equity / float(previous["benchmark_equity"]) - 1.0
            ) * 100.0
            if not _close(strategy_return, expected_strategy_return) or not _close(
                benchmark_return,
                expected_benchmark_return,
            ):
                return None
        rows.append({
            **row,
            "strategy_equity": strategy_equity,
            "benchmark_equity": benchmark_equity,
            "strategy_daily_return_pct": strategy_return,
            "benchmark_daily_return_pct": benchmark_return,
        })
        dates.append(row_date)

    if dates != sorted(dates) or len(dates) != len(set(dates)):
        return None
    outcome_count = max(settlement_count - 1, 0)
    rebalance_count = sum(bool(row["rebalance_executed"]) for row in rows[1:])
    series_content = dict(series)
    declared_series_hash = series_content.pop("series_hash", None)
    if (
        series.get("schema_version")
        != PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION
        or series.get("candidate_hash") != candidate_hash
        or series.get("outcome_period_count") != outcome_count
        or series.get("rebalance_execution_count") != rebalance_count
        or series.get("first_settlement_date") != (dates[0] if dates else "")
        or series.get("last_settlement_date") != (dates[-1] if dates else "")
        or series.get("first_settlement_hash")
        != (ordered_hashes[0] if ordered_hashes else "")
        or series.get("latest_settlement_hash")
        != (ordered_hashes[-1] if ordered_hashes else "")
        or not _sha256_hex(declared_series_hash)
        or declared_series_hash != _canonical_hash(series_content)
        or series.get("source_validation")
        != "FULL_SETTLEMENT_SEMANTIC_CHAIN_RECOMPUTED"
        or series.get("research_only") is not True
        or series.get("observation_only") is not True
        or series.get("simulation_only") is not True
        or series.get("paper_authorized") is not False
        or series.get("live_order_allowed") is not False
    ):
        return None

    cumulative_excess_return_pct = 0.0
    strategy_max_drawdown_pct = 0.0
    if rows:
        first_strategy = float(rows[0]["strategy_equity"])
        first_benchmark = float(rows[0]["benchmark_equity"])
        last_strategy = float(rows[-1]["strategy_equity"])
        last_benchmark = float(rows[-1]["benchmark_equity"])
        cumulative_excess_return_pct = round(
            (
                (last_strategy / first_strategy - 1.0)
                - (last_benchmark / first_benchmark - 1.0)
            )
            * 100.0,
            8,
        )
        peak = first_strategy
        for row in rows:
            equity = float(row["strategy_equity"])
            peak = max(peak, equity)
            strategy_max_drawdown_pct = max(
                strategy_max_drawdown_pct,
                max(0.0, 1.0 - equity / peak) * 100.0,
            )
        strategy_max_drawdown_pct = round(strategy_max_drawdown_pct, 8)
    return {
        "rows": rows,
        "settlement_count": settlement_count,
        "outcome_period_count": outcome_count,
        "rebalance_execution_count": rebalance_count,
        "first_settlement_date": dates[0] if dates else "",
        "last_settlement_date": dates[-1] if dates else "",
        "latest_settlement_hash": ordered_hashes[-1] if ordered_hashes else "",
        "series_hash": declared_series_hash,
        "ordered_settlement_hashes_hash": _canonical_hash(ordered_hashes),
        "cumulative_excess_return_pct": cumulative_excess_return_pct,
        "strategy_max_drawdown_pct": strategy_max_drawdown_pct,
    }


def _expected_statistical_contract(
    *,
    candidate: dict[str, Any],
    historical_audit: dict[str, Any],
    required_outcomes: int,
    reported_contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    spec = dict(candidate.get("spec") or {})
    trial_count_raw = spec.get("trial_count")
    if trial_count_raw is None:
        trial_count_raw = candidate.get("development_trial_count")
    trial_count = _strict_positive_integer(trial_count_raw)
    source_input_binding_hash = reported_contract.get(
        "source_historical_input_binding_hash"
    )
    if (
        trial_count is None
        or trial_count > 1_000_000
        or not _sha256_hex(source_input_binding_hash)
    ):
        return None
    historical_status = historical_audit.get("status")
    expected_historical_conclusion = {
        "PASS": "STATISTICAL_PROMOTION_EVIDENCE_PASS",
        "BLOCK": "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE",
    }.get(historical_status)
    if (
        expected_historical_conclusion is None
        or historical_audit.get("conclusion") != expected_historical_conclusion
    ):
        return None

    historical_config = {
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": DEFAULT_RESAMPLE_COUNT,
        "block_length": DEFAULT_BLOCK_LENGTH,
        "minimum_observations": DEFAULT_MINIMUM_OBSERVATIONS,
        "confidence_level": DEFAULT_CONFIDENCE_LEVEL,
        "required_positive_probability": DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
        "required_selection_adjusted_probability": (
            DEFAULT_REQUIRED_ADJUSTED_PROBABILITY
        ),
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": trial_count,
    }
    contract_content = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
        **{
            field: historical_config[field]
            for field in _COPIED_STATISTICAL_CONTRACT_FIELDS
        },
        "minimum_observations": required_outcomes,
        "minimum_observations_policy": (
            "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR"
        ),
        "source_historical_minimum_observations": DEFAULT_MINIMUM_OBSERVATIONS,
        "source_historical_audit_schema_version": (
            PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION
        ),
        "source_historical_audit_hash": historical_audit.get("audit_hash"),
        "source_historical_artifact_hash": historical_audit.get("artifact_hash"),
        "source_historical_claim_status": historical_status,
        "source_historical_config_hash": _canonical_hash(historical_config),
        "source_historical_input_binding_hash": source_input_binding_hash,
    }
    expected_contract = {
        **contract_content,
        "contract_hash": _canonical_hash(contract_content),
    }
    if _canonical_bytes(reported_contract) != _canonical_bytes(expected_contract):
        return None
    field_comparison = {
        field: {
            "historical": historical_config[field],
            "forward": expected_contract[field],
            "matches": True,
        }
        for field in _COPIED_STATISTICAL_CONTRACT_FIELDS
    }
    expected_comparison = {
        "status": "PASS",
        "copied_fields": field_comparison,
        "allowed_difference": {
            "field": "minimum_observations",
            "historical": DEFAULT_MINIMUM_OBSERVATIONS,
            "forward": required_outcomes,
            "reason": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        },
        "other_differences_allowed": False,
    }
    return expected_contract, expected_comparison


def _forward_audit_semantics(
    audit: dict[str, Any],
    *,
    candidate: dict[str, Any],
    candidate_hash: str,
    spec_hash: str,
    historical_audit: dict[str, Any],
    observer_generated_at: int,
    performance_generated_at: int,
) -> dict[str, Any] | None:
    expected_audit_fields = set(FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS) | (
        _FORWARD_AUDIT_RECEIPT_FIELDS
    )
    if (
        not isinstance(audit, dict)
        or set(audit) != expected_audit_fields
        or not isinstance(audit.get("series_evidence"), dict)
        or not isinstance(audit.get("statistical_contract"), dict)
        or not isinstance(audit.get("input_binding"), dict)
        or not isinstance(audit.get("contract_comparison"), dict)
        or not isinstance(audit.get("maturity"), dict)
        or not isinstance(audit.get("stage"), dict)
        or not isinstance(audit.get("checks"), dict)
        or audit.get("verification_status") != "PASS"
        or audit.get("verification_blockers") != []
        or audit.get("semantic_recomputed") is not True
        or authority_violations(audit)
    ):
        return None
    audit_generated_at = _strict_timestamp(audit.get("generated_at"))
    if (
        audit_generated_at is None
        or audit_generated_at < observer_generated_at
        or audit_generated_at > performance_generated_at
    ):
        return None

    series = dict(audit["series_evidence"])
    series_semantics = _validated_forward_series(
        series,
        candidate_hash=candidate_hash,
    )
    threshold_contract = forward_evidence_thresholds_from_spec(
        dict(candidate.get("spec") or {})
    )
    if series_semantics is None or threshold_contract.get("status") != "PASS":
        return None
    required_outcomes = _strict_positive_integer(
        threshold_contract.get("minimum_forward_performance_outcomes")
    )
    required_rebalances = _strict_positive_integer(
        threshold_contract.get("minimum_planned_rebalances")
    )
    if required_outcomes is None or required_rebalances is None:
        return None

    contract_result = _expected_statistical_contract(
        candidate=candidate,
        historical_audit=historical_audit,
        required_outcomes=required_outcomes,
        reported_contract=dict(audit["statistical_contract"]),
    )
    if contract_result is None:
        return None
    statistical_contract, contract_comparison = contract_result
    binding_content = {
        "candidate_hash": candidate_hash,
        "candidate_spec_hash": spec_hash,
        "candidate_declared_spec_hash": candidate.get("spec_hash"),
        "historical_statistical_audit_schema_version": (
            PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION
        ),
        "historical_statistical_audit_hash": historical_audit.get("audit_hash"),
        "historical_statistical_artifact_hash": historical_audit.get(
            "artifact_hash"
        ),
        "historical_statistical_config_hash": statistical_contract.get(
            "source_historical_config_hash"
        ),
        "historical_statistical_input_binding_hash": statistical_contract.get(
            "source_historical_input_binding_hash"
        ),
        "statistical_contract_hash": statistical_contract.get("contract_hash"),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "forward_series_hash": series_semantics["series_hash"],
        "ordered_settlement_hashes_hash": series_semantics[
            "ordered_settlement_hashes_hash"
        ],
        "first_settlement_date": series.get("first_settlement_date"),
        "last_settlement_date": series.get("last_settlement_date"),
        "first_settlement_hash": series.get("first_settlement_hash"),
        "latest_settlement_hash": series_semantics["latest_settlement_hash"],
        "settlement_count": series_semantics["settlement_count"],
        "outcome_period_count": series_semantics["outcome_period_count"],
        "rebalance_execution_count": series_semantics[
            "rebalance_execution_count"
        ],
    }
    expected_binding = {
        **binding_content,
        "binding_hash": _canonical_hash(binding_content),
    }
    if _canonical_bytes(audit["input_binding"]) != _canonical_bytes(expected_binding):
        return None

    outcome_count = int(series_semantics["outcome_period_count"])
    rebalance_count = int(series_semantics["rebalance_execution_count"])
    due = outcome_count >= required_outcomes and rebalance_count >= required_rebalances
    expected_maturity = {
        "status": "DUE" if due else "NOT_DUE",
        "forward_outcomes": outcome_count,
        "required_forward_outcomes": required_outcomes,
        "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
        "executed_rebalances": rebalance_count,
        "required_executed_rebalances": required_rebalances,
        "remaining_executed_rebalances": max(
            required_rebalances - rebalance_count,
            0,
        ),
        "both_thresholds_required": True,
    }
    expected_stage: dict[str, Any] = {}
    if due:
        rows = list(series_semantics["rows"])
        baseline = dict(rows[0])
        outcomes = [dict(item) for item in rows[1:]]
        seed = int(
            _canonical_hash({
                "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
                "input_binding": expected_binding,
                "statistical_contract": statistical_contract,
                "stage": "natural_forward",
            })[:16],
            16,
        )
        expected_stage = audit_paired_equity_curve_stage(
            stage="natural_forward",
            strategy_report={
                "initial_cash": baseline["strategy_equity"],
                "equity_curve": [
                    {"date": item["date"], "equity": item["strategy_equity"]}
                    for item in outcomes
                ],
            },
            benchmark_report={
                "initial_cash": baseline["benchmark_equity"],
                "equity_curve": [
                    {"date": item["date"], "equity": item["benchmark_equity"]}
                    for item in outcomes
                ],
            },
            resample_count=DEFAULT_RESAMPLE_COUNT,
            block_length=DEFAULT_BLOCK_LENGTH,
            minimum_observations=required_outcomes,
            confidence_level=DEFAULT_CONFIDENCE_LEVEL,
            required_positive_probability=DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
            required_adjusted_probability=DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
            selection_trial_count=int(statistical_contract["selection_trial_count"]),
            seed=seed,
        )

    stage_pass = due and expected_stage.get("status") == "PASS"
    expected_blockers = (
        []
        if not due or stage_pass
        else [
            f"natural_forward:{item}"
            for item in expected_stage.get("blockers")
            or ["statistical_stage_not_passed"]
        ]
    )
    if not due:
        status = "NOT_DUE"
        conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
    elif stage_pass:
        status = "PASS"
        conclusion = "FORWARD_STATISTICAL_CONTRACT_PASS"
    else:
        status = "BLOCK"
        conclusion = "FORWARD_STATISTICAL_CONTRACT_FAILED"
    expected_checks = {
        "candidate_authority_is_research_only": True,
        "forward_threshold_contract_pass": True,
        "settlement_series_integrity_pass": True,
        "historical_statistical_contract_verified": True,
        "same_statistical_contract_except_forward_maturity_floor": True,
        "maturity_requires_outcomes_and_rebalances": due,
        "natural_forward_statistical_stage_pass": stage_pass,
        "zero_execution_authority": True,
    }
    expected_content = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "status": status,
        "conclusion": conclusion,
        "blockers": expected_blockers,
        "input_binding": expected_binding,
        "maturity": expected_maturity,
        "contract_comparison": contract_comparison,
        "statistical_contract": statistical_contract,
        "series_evidence": series,
        "stage": expected_stage,
        "checks": expected_checks,
        "evidence_scope": "NATURAL_FORWARD_PAIRED_PORTFOLIO_STATISTICS_ONLY",
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if (
        _canonical_bytes(forward_statistical_audit_content(audit))
        != _canonical_bytes(expected_content)
        or audit.get("audit_hash") != _canonical_hash(expected_content)
    ):
        return None
    return {**series_semantics, "audit_status": status}


def _decision_series_evidence_v2(
    *,
    candidate_hash: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered_hashes = [str(item.get("settlement_hash") or "") for item in rows]
    content = {
        "schema_version": PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
        "candidate_hash": candidate_hash,
        "settlement_count": len(rows),
        "outcome_period_count": max(len(rows) - 1, 0),
        "rebalance_execution_count": sum(
            int(item.get("rebalance_executed") is True) for item in rows
        ),
        "first_settlement_date": str(rows[0].get("date") or "") if rows else "",
        "last_settlement_date": str(rows[-1].get("date") or "") if rows else "",
        "first_settlement_hash": ordered_hashes[0] if ordered_hashes else "",
        "latest_settlement_hash": ordered_hashes[-1] if ordered_hashes else "",
        "ordered_settlement_hashes": ordered_hashes,
        "rows": [dict(item) for item in rows],
        "source_validation": "FULL_SETTLEMENT_SEMANTIC_CHAIN_RECOMPUTED",
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "series_hash": _canonical_hash(content)}


def _forward_audit_v2_semantics(
    audit: dict[str, Any],
    *,
    candidate: dict[str, Any],
    candidate_hash: str,
    spec_hash: str,
    historical_audit: dict[str, Any],
    observer_generated_at: int,
    performance_generated_at: int,
) -> dict[str, Any] | None:
    expected_audit_fields = set(FORWARD_STATISTICAL_AUDIT_V2_CONTENT_FIELDS) | (
        _FORWARD_AUDIT_RECEIPT_FIELDS
    )
    if (
        not isinstance(audit, dict)
        or set(audit) != expected_audit_fields
        or audit.get("schema_version")
        != PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION
        or not isinstance(audit.get("series_evidence"), dict)
        or not isinstance(audit.get("statistical_contract"), dict)
        or not isinstance(audit.get("input_binding"), dict)
        or not isinstance(audit.get("contract_comparison"), dict)
        or not isinstance(audit.get("maturity"), dict)
        or not isinstance(audit.get("stage"), dict)
        or not isinstance(audit.get("decision_window"), dict)
        or not isinstance(audit.get("checks"), dict)
        or audit.get("verification_status") != "PASS"
        or audit.get("verification_blockers") != []
        or audit.get("semantic_recomputed") is not True
        or authority_violations(audit)
    ):
        return None
    audit_generated_at = _strict_timestamp(audit.get("generated_at"))
    if (
        audit_generated_at is None
        or audit_generated_at < observer_generated_at
        or audit_generated_at > performance_generated_at
    ):
        return None

    series = dict(audit["series_evidence"])
    series_semantics = _validated_forward_series(
        series,
        candidate_hash=candidate_hash,
    )
    threshold_contract = forward_evidence_thresholds_v3_from_spec(
        dict(candidate.get("spec") or {})
    )
    if series_semantics is None or threshold_contract.get("status") != "PASS":
        return None
    required_outcomes = _strict_positive_integer(
        threshold_contract.get("minimum_forward_performance_outcomes")
    )
    required_rebalances = _strict_positive_integer(
        threshold_contract.get("minimum_planned_rebalances")
    )
    if required_outcomes is None or required_rebalances is None:
        return None

    statistical_contract, contract_comparison, contract_blockers = (
        _historical_contract(
            candidate=candidate,
            historical_statistical_audit=historical_audit,
            forward_minimum_observations=required_outcomes,
        )
    )
    historical_safe_integer_blockers = _v2_historical_safe_integer_blockers(
        candidate=candidate,
        historical_statistical_audit=historical_audit,
    )
    if (
        contract_blockers
        or historical_safe_integer_blockers
        or authority_violations(historical_audit)
        or _canonical_bytes(audit["statistical_contract"])
        != _canonical_bytes(statistical_contract)
        or _canonical_bytes(audit["contract_comparison"])
        != _canonical_bytes(contract_comparison)
    ):
        return None

    outcome_count = int(series_semantics["outcome_period_count"])
    rebalance_count = int(series_semantics["rebalance_execution_count"])
    due = outcome_count >= required_outcomes and rebalance_count >= required_rebalances
    prefix = first_joint_maturity_prefix(
        series,
        required_forward_outcomes=required_outcomes,
        required_executed_rebalances=required_rebalances,
    )
    if prefix.get("status") not in {"DUE", "NOT_DUE"} or prefix.get("blockers") != []:
        return None
    if due is not (prefix.get("status") == "DUE"):
        return None

    maturity = {
        "status": "DUE" if due else "NOT_DUE",
        "forward_outcomes": outcome_count,
        "required_forward_outcomes": required_outcomes,
        "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
        "executed_rebalances": rebalance_count,
        "required_executed_rebalances": required_rebalances,
        "remaining_executed_rebalances": max(
            required_rebalances - rebalance_count,
            0,
        ),
        "both_thresholds_required": True,
        "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "first_joint_maturity_status": str(prefix.get("status") or "BLOCK"),
        "first_due_settlement_index": prefix.get("first_due_settlement_index"),
        "first_due_settlement_date": str(
            prefix.get("first_due_settlement_date") or ""
        ),
        "first_due_settlement_hash": str(
            prefix.get("first_due_settlement_hash") or ""
        ),
    }

    decision_series: dict[str, Any] = {}
    if due:
        first_due_index = prefix.get("first_due_settlement_index")
        if not isinstance(first_due_index, int):
            return None
        decision_rows = [
            dict(item)
            for item in list(series_semantics["rows"])[: first_due_index + 1]
        ]
        decision_series = _decision_series_evidence_v2(
            candidate_hash=candidate_hash,
            rows=decision_rows,
        )
        if (
            decision_series.get("settlement_count") != prefix.get("settlement_count")
            or decision_series.get("outcome_period_count")
            != prefix.get("outcome_period_count")
            or decision_series.get("rebalance_execution_count")
            != prefix.get("rebalance_execution_count")
            or decision_series.get("latest_settlement_hash")
            != prefix.get("first_due_settlement_hash")
        ):
            return None
        if statistical_bootstrap_budget_blockers(
            resample_count=statistical_contract.get("resample_count"),
            block_length=statistical_contract.get("block_length"),
            sample_size=decision_series.get("outcome_period_count"),
        ):
            return None

    risk_acceptance, risk_integrity_blockers, risk_evidence_blockers = (
        _v2_prefix_risk_acceptance(
            spec=dict(candidate.get("spec") or {}),
            prefix=prefix,
            decision_series_evidence=decision_series,
        )
    )
    if risk_integrity_blockers:
        return None

    stage: dict[str, Any] = {}
    if due:
        decision_rows = [dict(item) for item in decision_series.get("rows") or []]
        if not decision_rows:
            return None
        baseline = dict(decision_rows[0])
        outcomes = [dict(item) for item in decision_rows[1:]]
        seed = int(
            _canonical_hash({
                "schema_version": (
                    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION
                ),
                "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
                "candidate_hash": candidate_hash,
                "candidate_spec_hash": spec_hash,
                "statistical_contract_hash": statistical_contract.get(
                    "contract_hash"
                ),
                "forward_threshold_contract_hash": _canonical_hash(
                    threshold_contract
                ),
                "decision_series_hash": decision_series.get("series_hash"),
                "first_joint_maturity_prefix": prefix,
            })[:16],
            16,
        )
        stage = audit_paired_equity_curve_stage(
            stage="natural_forward_first_joint_maturity",
            strategy_report={
                "initial_cash": baseline["strategy_equity"],
                "equity_curve": [
                    {"date": item["date"], "equity": item["strategy_equity"]}
                    for item in outcomes
                ],
            },
            benchmark_report={
                "initial_cash": baseline["benchmark_equity"],
                "equity_curve": [
                    {"date": item["date"], "equity": item["benchmark_equity"]}
                    for item in outcomes
                ],
            },
            resample_count=int(statistical_contract["resample_count"]),
            block_length=int(statistical_contract["block_length"]),
            minimum_observations=int(statistical_contract["minimum_observations"]),
            confidence_level=float(statistical_contract["confidence_level"]),
            required_positive_probability=float(
                statistical_contract["required_positive_probability"]
            ),
            required_adjusted_probability=float(
                statistical_contract["required_selection_adjusted_probability"]
            ),
            selection_trial_count=int(statistical_contract["selection_trial_count"]),
            seed=seed,
        )

    stage_blockers = (
        [
            f"natural_forward_first_joint_maturity:{item}"
            for item in stage.get("blockers")
            or ["statistical_stage_not_passed"]
        ]
        if due and stage.get("status") != "PASS"
        else []
    )
    risk_blockers = [
        f"first_joint_maturity_risk:{item}" for item in risk_evidence_blockers
    ]
    if not due:
        decision_window_status = "NOT_DUE"
        decision_status = "NOT_DUE"
        research_action = "COLLECT_MORE"
    elif stage.get("status") == "PASS" and risk_acceptance.get("status") == "PASS":
        decision_window_status = "FROZEN"
        decision_status = "PASS"
        research_action = "REVIEW_REQUIRED"
    else:
        decision_window_status = "FROZEN"
        decision_status = "BLOCK"
        research_action = "STOP_RESEARCH"

    decision_window_content = {
        "schema_version": PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION,
        "policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "status": decision_window_status,
        "decision_status": decision_status,
        "research_action": research_action,
        "candidate_hash": candidate_hash,
        "candidate_spec_hash": spec_hash,
        "candidate_declared_spec_hash": str(candidate.get("spec_hash") or ""),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "statistical_contract_hash": str(
            statistical_contract.get("contract_hash") or ""
        ),
        "first_joint_maturity_prefix": prefix,
        "decision_series_hash": str(decision_series.get("series_hash") or ""),
        "stage_hash": str(stage.get("stage_hash") or ""),
        "risk_acceptance": risk_acceptance,
        "risk_acceptance_hash": str(risk_acceptance.get("risk_hash") or ""),
        "blockers": list(dict.fromkeys([*stage_blockers, *risk_blockers])),
        "later_settlements_used": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    decision_window = {
        **decision_window_content,
        "decision_hash": _canonical_hash(decision_window_content),
    }

    binding_content = {
        "candidate_hash": candidate_hash,
        "candidate_spec_hash": spec_hash,
        "candidate_declared_spec_hash": candidate.get("spec_hash"),
        "historical_statistical_audit_schema_version": str(
            historical_audit.get("schema_version") or ""
        ),
        "historical_statistical_audit_hash": historical_audit.get("audit_hash"),
        "historical_statistical_artifact_hash": historical_audit.get(
            "artifact_hash"
        ),
        "historical_statistical_config_hash": _canonical_hash(
            dict(historical_audit.get("config") or {})
        ),
        "historical_statistical_input_binding_hash": str(
            dict(historical_audit.get("input_binding") or {}).get("binding_hash")
            or ""
        ),
        "statistical_contract_hash": statistical_contract.get("contract_hash"),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "forward_series_hash": series_semantics["series_hash"],
        "ordered_settlement_hashes_hash": series_semantics[
            "ordered_settlement_hashes_hash"
        ],
        "first_settlement_date": series.get("first_settlement_date"),
        "last_settlement_date": series.get("last_settlement_date"),
        "first_settlement_hash": series.get("first_settlement_hash"),
        "latest_settlement_hash": series_semantics["latest_settlement_hash"],
        "settlement_count": series_semantics["settlement_count"],
        "outcome_period_count": outcome_count,
        "rebalance_execution_count": rebalance_count,
        "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "decision_hash": decision_window["decision_hash"],
        "decision_series_hash": str(decision_series.get("series_hash") or ""),
        "risk_acceptance_hash": str(risk_acceptance.get("risk_hash") or ""),
        "first_due_settlement_index": prefix.get("first_due_settlement_index"),
        "first_due_settlement_date": str(
            prefix.get("first_due_settlement_date") or ""
        ),
        "first_due_settlement_hash": str(
            prefix.get("first_due_settlement_hash") or ""
        ),
    }
    expected_binding = {
        **binding_content,
        "binding_hash": _canonical_hash(binding_content),
    }
    checks = {
        "candidate_authority_is_research_only": True,
        "forward_threshold_contract_pass": True,
        "settlement_series_integrity_pass": True,
        "historical_statistical_contract_verified": True,
        "same_statistical_contract_except_forward_maturity_floor": True,
        "maturity_requires_outcomes_and_rebalances": due,
        "first_joint_maturity_prefix_integrity_pass": True,
        "single_statistical_look_uses_frozen_prefix_only": True,
        "natural_forward_statistical_stage_pass": (
            stage.get("status") == "PASS" if due else False
        ),
        "first_joint_maturity_risk_acceptance_pass": (
            risk_acceptance.get("status") == "PASS" if due else False
        ),
        "first_joint_maturity_risk_acceptance_integrity_pass": True,
        "zero_execution_authority": True,
    }
    blockers = list(dict.fromkeys([*stage_blockers, *risk_blockers]))
    if not due:
        status = "NOT_DUE"
        conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
    elif stage.get("status") == "PASS" and risk_acceptance.get("status") == "PASS":
        status = "PASS"
        conclusion = "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_PASS"
    else:
        status = "BLOCK"
        conclusion = "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_FAILED"
    expected_content = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
        "status": status,
        "conclusion": conclusion,
        "blockers": blockers,
        "input_binding": expected_binding,
        "maturity": maturity,
        "contract_comparison": contract_comparison,
        "statistical_contract": statistical_contract,
        "series_evidence": series,
        "stage": stage,
        "checks": checks,
        "evidence_scope": (
            "NATURAL_FORWARD_FIRST_JOINT_MATURITY_SINGLE_LOOK_"
            "PAIRED_PORTFOLIO_STATISTICS_AND_PREFIX_DRAWDOWN_ONLY"
        ),
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "decision_window": decision_window,
    }
    if (
        _canonical_bytes(forward_statistical_audit_v2_content(audit))
        != _canonical_bytes(expected_content)
        or audit.get("audit_hash") != _canonical_hash(expected_content)
    ):
        return None
    return {
        **series_semantics,
        "audit_status": status,
        "decision_status": decision_status,
        "research_action": research_action,
        "decision_hash": decision_window["decision_hash"],
        "stage_hash": str(stage.get("stage_hash") or ""),
        "risk_acceptance_hash": str(risk_acceptance.get("risk_hash") or ""),
        "first_due_settlement_hash": str(
            prefix.get("first_due_settlement_hash") or ""
        ),
    }


def _verified_source_binding(
    *,
    candidate_hash: str,
    observation_chain: list[dict[str, Any]],
    settlement_rows: list[dict[str, Any]],
    backup_status: dict[str, Any],
    watchdog_status: dict[str, Any],
    backup_read_status: str,
    watchdog_read_status: str,
    observed_now_ms: int,
) -> dict[str, Any]:
    current_observation_count = len(observation_chain)
    current_settlement_count = len(settlement_rows)

    def binding(
        status: str,
        *,
        anchored_observation_count: int = 0,
        anchored_settlement_count: int = 0,
    ) -> dict[str, Any]:
        return _source_binding(
            status=status,
            current_observation_count=current_observation_count,
            anchored_observation_count=anchored_observation_count,
            current_settlement_count=current_settlement_count,
            anchored_settlement_count=anchored_settlement_count,
        )

    read_statuses = {backup_read_status, watchdog_read_status}
    if not read_statuses.issubset({"READABLE", "MISSING", "UNREADABLE"}):
        return binding("CONTRADICTION")
    if backup_read_status == "MISSING" and watchdog_read_status == "MISSING":
        return binding("NOT_AVAILABLE")
    if "UNREADABLE" in read_statuses:
        return binding("CONTRADICTION")

    backup_schema = str(backup_status.get("schema_version") or "")
    watchdog_schema = str(watchdog_status.get("schema_version") or "")
    backup_legacy = backup_schema == _BACKUP_STATUS_V1_SCHEMA_VERSION
    watchdog_legacy = watchdog_schema == _WATCHDOG_V2_SCHEMA_VERSION
    backup_current = backup_schema == _BACKUP_STATUS_V2_SCHEMA_VERSION
    watchdog_current = watchdog_schema == _WATCHDOG_V3_SCHEMA_VERSION

    if (
        backup_read_status == "READABLE"
        and watchdog_read_status == "READABLE"
        and backup_legacy
        and watchdog_legacy
    ):
        return binding("NOT_AVAILABLE")
    if (
        backup_read_status == "MISSING"
        and watchdog_read_status == "READABLE"
        and watchdog_legacy
    ) or (
        watchdog_read_status == "MISSING"
        and backup_read_status == "READABLE"
        and backup_legacy
    ):
        return binding("NOT_AVAILABLE")
    if (
        backup_read_status != "READABLE"
        or watchdog_read_status != "READABLE"
        or not backup_current
        or not watchdog_current
    ):
        return binding("CONTRADICTION")

    if (
        verify_portfolio_backup_status(backup_status).get("status") != "PASS"
        or verify_portfolio_forward_watchdog_status(watchdog_status).get("status")
        != "PASS"
    ):
        return binding("CONTRADICTION")

    backup_generated_at = _strict_timestamp(backup_status.get("generated_at"))
    watchdog_generated_at = _strict_timestamp(watchdog_status.get("generated_at"))
    observed_now = _strict_timestamp(observed_now_ms)
    if (
        backup_generated_at is None
        or watchdog_generated_at is None
        or observed_now is None
        or backup_generated_at > watchdog_generated_at
        or backup_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
        or watchdog_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
        or watchdog_status.get("backup_schema_version") != backup_schema
        or str(watchdog_status.get("backup_status_hash") or "")
        != str(backup_status.get("status_hash") or "")
    ):
        return binding("CONTRADICTION")

    backup_anchor = backup_status.get("local_source_anchor")
    watchdog_anchor = watchdog_status.get("verified_source_anchor")
    if not isinstance(backup_anchor, dict) or not isinstance(watchdog_anchor, dict):
        return binding("CONTRADICTION")
    backup_anchor_verification = verify_portfolio_forward_local_source_anchor(
        backup_anchor
    )
    watchdog_anchor_verification = verify_portfolio_forward_local_source_anchor(
        watchdog_anchor
    )
    if (
        backup_anchor_verification.get("status") != "PASS"
        or watchdog_anchor_verification.get("status") != "PASS"
        or _canonical_bytes(backup_anchor) != _canonical_bytes(watchdog_anchor)
    ):
        return binding("CONTRADICTION")

    anchor_status = str(backup_anchor.get("status") or "")
    watchdog_anchor_status = str(
        watchdog_status.get("local_source_anchor_status") or ""
    )
    if watchdog_anchor_status == "CONTRADICTION":
        return binding("CONTRADICTION")
    if anchor_status == "NOT_AVAILABLE" and watchdog_anchor_status == "NOT_AVAILABLE":
        return binding("NOT_AVAILABLE")
    if anchor_status != "VERIFIED" or watchdog_anchor_status != "VERIFIED":
        return binding("CONTRADICTION")

    anchored_observation_count = _strict_positive_integer(
        backup_anchor.get("observation_count")
    )
    anchored_settlement_count = _strict_positive_integer(
        backup_anchor.get("settlement_count")
    )
    if anchored_observation_count is None or anchored_settlement_count is None:
        return binding("CONTRADICTION")
    anchored = {
        "anchored_observation_count": anchored_observation_count,
        "anchored_settlement_count": anchored_settlement_count,
    }
    archive_generated_at = _strict_timestamp(
        backup_anchor.get("archive_generated_at")
    )
    manifest_hash = str(backup_anchor.get("archive_manifest_hash") or "")
    if (
        archive_generated_at is None
        or archive_generated_at > backup_generated_at
        or backup_anchor.get("schema_version")
        != PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION
        or backup_anchor.get("candidate_hash") != candidate_hash
        or backup_status.get("candidate_hash") != candidate_hash
        or watchdog_status.get("candidate_hash") != candidate_hash
        or backup_status.get("status") != "PASS"
        or backup_status.get("verification_status") != "PASS"
        or manifest_hash != str(backup_status.get("manifest_hash") or "")
        or manifest_hash != str(watchdog_status.get("backup_manifest_hash") or "")
        or anchored_observation_count != anchored_settlement_count
    ):
        return binding("CONTRADICTION", **anchored)

    receipt_stale = (
        observed_now - watchdog_generated_at > _WATCHDOG_RECEIPT_STALE_AFTER_MS
        or observed_now - backup_generated_at > _BACKUP_RECEIPT_STALE_AFTER_MS
    )
    if receipt_stale:
        return binding("NOT_AVAILABLE", **anchored)
    if (
        current_observation_count < anchored_observation_count
        or current_settlement_count < anchored_settlement_count
        or current_observation_count != current_settlement_count
    ):
        return binding("CONTRADICTION", **anchored)

    observer_prefix = portfolio_local_source_observer_projection_from_chain(
        observation_chain[:anchored_observation_count]
    )
    settlement_prefix = normalize_portfolio_local_source_settlement_projection(
        settlement_rows[:anchored_settlement_count]
    )
    hashes = portfolio_local_source_projection_hashes(
        observer_projection=observer_prefix,
        settlement_projection=settlement_prefix,
    )
    if (
        hashes.get("observer_projection_hash")
        != backup_anchor.get("observer_projection_hash")
        or hashes.get("settlement_projection_hash")
        != backup_anchor.get("settlement_projection_hash")
        or hashes.get("cross_binding_hash") != backup_anchor.get("cross_binding_hash")
        or observer_prefix[0]["signal_date"]
        != backup_anchor.get("first_observation_date")
        or observer_prefix[-1]["signal_date"]
        != backup_anchor.get("last_observation_date")
        or settlement_prefix[0]["date"]
        != backup_anchor.get("first_settlement_date")
        or settlement_prefix[-1]["date"]
        != backup_anchor.get("last_settlement_date")
    ):
        return binding("CONTRADICTION", **anchored)
    return binding(
        (
            "FULL"
            if current_observation_count == anchored_observation_count
            and current_settlement_count == anchored_settlement_count
            else "PREFIX"
        ),
        **anchored,
    )


def _verified_projection(
    *,
    active_candidate: dict[str, Any],
    observer_status: dict[str, Any],
    performance_status: dict[str, Any],
    backup_status: dict[str, Any],
    watchdog_status: dict[str, Any],
    backup_read_status: str,
    watchdog_read_status: str,
    observed_now_ms: int,
) -> dict[str, Any]:
    observed_now = _strict_timestamp(observed_now_ms)
    canonical_candidate = _canonical_candidate(active_candidate)
    if observed_now is None or canonical_candidate is None:
        return _projection(status="BLOCK")
    candidate_hash, spec_hash = canonical_candidate
    blocked = _projection(status="BLOCK", candidate_hash=candidate_hash)

    if (
        not observer_status
        or not performance_status
        or authority_violations(observer_status)
        or authority_violations(performance_status)
    ):
        return blocked
    observer_verification = verify_forward_status_artifact(
        observer_status,
        candidate_hash=candidate_hash,
    )
    if observer_verification.get("status") != "PASS":
        return blocked

    observer_generated_at = _strict_timestamp(observer_status.get("generated_at"))
    performance_generated_at = _strict_timestamp(performance_status.get("generated_at"))
    if (
        observer_generated_at is None
        or performance_generated_at is None
        or performance_generated_at < observer_generated_at
        or observer_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
        or performance_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
    ):
        return blocked

    performance_summary = dict(performance_status.get("performance") or {})
    shadow_audit = dict(performance_status.get("shadow_audit") or {})
    observer_audit = dict(dict(observer_status.get("ledger") or {}).get("forward_audit") or {})
    historical_audit = dict(performance_status.get("historical_statistical_audit") or {})
    forward_audit = dict(performance_status.get("forward_statistical_audit") or {})
    declared_readiness = dict(performance_status.get("readiness") or {})
    historical_verification_blockers = historical_audit.get("verification_blockers")
    shadow_semantics = _validated_shadow_audit(
        shadow_audit,
        candidate_hash=candidate_hash,
    )
    if (
        performance_status.get("ok") is not True
        or performance_status.get("observation_only") is not True
        or performance_status.get("simulation_only") is not True
        or performance_status.get("paper_authorized") is not False
        or performance_status.get("live_order_allowed") is not False
        or str(performance_status.get("candidate_hash") or "") != candidate_hash
        or str(performance_summary.get("candidate_hash") or "") != candidate_hash
        or performance_summary.get("status") != "PASS"
        or not shadow_audit
        or shadow_semantics is None
        or str(performance_status.get("shadow_audit_hash") or "")
        != _canonical_hash(shadow_audit)
        or not observer_audit
        or _canonical_bytes(observer_audit) != _canonical_bytes(shadow_audit)
        or historical_audit.get("verification_status") != "PASS"
        or historical_audit.get("semantic_recomputed") is not True
        or not isinstance(historical_verification_blockers, list)
        or historical_verification_blockers != []
        or not _sha256_hex(historical_audit.get("audit_hash"))
        or not _sha256_hex(historical_audit.get("artifact_hash"))
    ):
        return blocked

    audit_semantics = _forward_audit_semantics(
        forward_audit,
        candidate=active_candidate,
        candidate_hash=candidate_hash,
        spec_hash=spec_hash,
        historical_audit=historical_audit,
        observer_generated_at=observer_generated_at,
        performance_generated_at=performance_generated_at,
    )
    if (
        audit_semantics is None
        or shadow_semantics["signal_dates"]
        != [str(row["date"]) for row in audit_semantics["rows"]]
    ):
        return blocked

    settlement_count = int(audit_semantics["settlement_count"])
    strategy_summary = performance_summary.get("strategy")
    unsettled_dates = performance_summary.get("unsettled_observation_dates")
    performance_failure_lists = (
        unsettled_dates,
        performance_summary.get("unexpected_settlement_dates"),
        performance_summary.get("observation_hash_mismatch_dates"),
        performance_summary.get("integrity_violations"),
    )
    performance_shape_valid = (
        performance_summary.get("schema_version")
        == PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION
        and performance_summary.get("candidate_hash") == candidate_hash
        and performance_summary.get("first_settlement_date")
        == audit_semantics["first_settlement_date"]
        and performance_summary.get("last_settlement_date")
        == audit_semantics["last_settlement_date"]
        and all(
            isinstance(items, list) and items == []
            for items in performance_failure_lists
        )
        and performance_summary.get("observation_only") is True
        and performance_summary.get("simulation_only") is True
        and performance_summary.get("paper_authorized") is False
        and performance_summary.get("live_order_allowed") is False
    )
    performance_counts_match = (
        _strict_nonnegative_integer(performance_summary.get("settlement_count"))
        == settlement_count
        and _strict_nonnegative_integer(
            performance_summary.get("outcome_period_count")
        )
        == audit_semantics["outcome_period_count"]
        and _strict_nonnegative_integer(
            performance_summary.get("rebalance_execution_count")
        )
        == audit_semantics["rebalance_execution_count"]
        and _strict_nonnegative_integer(shadow_audit.get("valid_observation_count"))
        == settlement_count
        and _strict_nonnegative_integer(
            shadow_audit.get("execution_authority_violation_count")
        )
        == 0
        and _strict_nonnegative_integer(
            performance_summary.get("execution_authority_violation_count")
        )
        == 0
    )
    latest_hash_matches = (
        performance_summary.get("latest_settlement_hash")
        == audit_semantics["latest_settlement_hash"]
        if settlement_count
        else not performance_summary.get("latest_settlement_hash")
    )
    strategy_drawdown_matches = (
        isinstance(strategy_summary, dict)
        and _close(
            strategy_summary.get("max_drawdown_pct"),
            audit_semantics["strategy_max_drawdown_pct"],
        )
        if settlement_count
        else isinstance(strategy_summary, dict) and strategy_summary == {}
    )
    if (
        not performance_shape_valid
        or not performance_counts_match
        or not latest_hash_matches
        or not _close(
            performance_summary.get("cumulative_excess_return_pct"),
            audit_semantics["cumulative_excess_return_pct"],
        )
        or not strategy_drawdown_matches
    ):
        return blocked

    rebuilt_performance_summary = dict(performance_summary)
    rebuilt_performance_summary["cumulative_excess_return_pct"] = audit_semantics[
        "cumulative_excess_return_pct"
    ]
    if settlement_count:
        rebuilt_strategy = dict(strategy_summary)
        rebuilt_strategy["max_drawdown_pct"] = audit_semantics[
            "strategy_max_drawdown_pct"
        ]
        rebuilt_performance_summary["strategy"] = rebuilt_strategy

    rebuilt = build_forward_performance_readiness(
        candidate=active_candidate,
        shadow_audit=shadow_audit,
        performance_summary=rebuilt_performance_summary,
        historical_statistical_audit=historical_audit,
        forward_statistical_audit=forward_audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    )
    source_status = str(rebuilt.get("status") or "")
    if (
        rebuilt.get("schema_version") != PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION
        or _canonical_bytes(rebuilt) != _canonical_bytes(declared_readiness)
        or str(performance_status.get("status") or "") != source_status
        or source_status not in _STATUS_MAP
    ):
        return blocked

    progress_source = dict(rebuilt.get("progress") or {})
    progress = {
        field: _strict_nonnegative_integer(progress_source.get(field))
        for field in _PROGRESS_FIELDS
    }
    if any(value is None for value in progress.values()):
        return blocked
    projected_status = _STATUS_MAP[source_status]
    source_binding = _verified_source_binding(
        candidate_hash=candidate_hash,
        observation_chain=list(shadow_semantics["observation_chain"]),
        settlement_rows=list(audit_semantics["rows"]),
        backup_status=backup_status,
        watchdog_status=watchdog_status,
        backup_read_status=backup_read_status,
        watchdog_read_status=watchdog_read_status,
        observed_now_ms=observed_now_ms,
    )
    if source_binding["status"] == "CONTRADICTION":
        return _projection(
            status="BLOCK",
            candidate_hash=candidate_hash,
            source_binding=source_binding,
        )
    return _projection(
        status=projected_status,
        candidate_hash=candidate_hash,
        progress=(
            {field: int(progress[field]) for field in _PROGRESS_FIELDS}
            if projected_status != "BLOCK"
            else _empty_progress()
        ),
        source_binding=source_binding,
    )


def _verified_projection_v3(
    *,
    active_candidate: dict[str, Any],
    observer_status: dict[str, Any],
    performance_status: dict[str, Any],
    backup_status: dict[str, Any],
    watchdog_status: dict[str, Any],
    backup_read_status: str,
    watchdog_read_status: str,
    observed_now_ms: int,
) -> dict[str, Any]:
    observed_now = _strict_timestamp(observed_now_ms)
    canonical_candidate = _canonical_candidate(active_candidate)
    if observed_now is None or canonical_candidate is None:
        return _projection_v3(status="BLOCK")
    candidate_hash, spec_hash = canonical_candidate
    blocked = _projection_v3(status="BLOCK", candidate_hash=candidate_hash)

    if (
        not observer_status
        or not performance_status
        or authority_violations(observer_status)
        or authority_violations(performance_status)
    ):
        return blocked
    observer_verification = verify_forward_status_artifact(
        observer_status,
        candidate_hash=candidate_hash,
    )
    if observer_verification.get("status") != "PASS":
        return blocked

    observer_generated_at = _strict_timestamp(observer_status.get("generated_at"))
    performance_generated_at = _strict_timestamp(performance_status.get("generated_at"))
    if (
        observer_generated_at is None
        or performance_generated_at is None
        or performance_generated_at < observer_generated_at
        or observer_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
        or performance_generated_at > observed_now + _MAX_CLOCK_SKEW_MS
    ):
        return blocked

    performance_summary = dict(performance_status.get("performance") or {})
    shadow_audit = dict(performance_status.get("shadow_audit") or {})
    observer_audit = dict(
        dict(observer_status.get("ledger") or {}).get("forward_audit") or {}
    )
    historical_audit = dict(
        performance_status.get("historical_statistical_audit") or {}
    )
    forward_audit = dict(performance_status.get("forward_statistical_audit") or {})
    declared_readiness = dict(performance_status.get("readiness") or {})
    historical_verification_blockers = historical_audit.get(
        "verification_blockers"
    )
    shadow_semantics = _validated_shadow_audit(
        shadow_audit,
        candidate_hash=candidate_hash,
    )
    if (
        performance_status.get("ok") is not True
        or performance_status.get("observation_only") is not True
        or performance_status.get("simulation_only") is not True
        or performance_status.get("paper_authorized") is not False
        or performance_status.get("live_order_allowed") is not False
        or str(performance_status.get("candidate_hash") or "") != candidate_hash
        or str(performance_summary.get("candidate_hash") or "") != candidate_hash
        or performance_summary.get("status") != "PASS"
        or not shadow_audit
        or shadow_semantics is None
        or str(performance_status.get("shadow_audit_hash") or "")
        != _canonical_hash(shadow_audit)
        or not observer_audit
        or _canonical_bytes(observer_audit) != _canonical_bytes(shadow_audit)
        or historical_audit.get("verification_status") != "PASS"
        or historical_audit.get("semantic_recomputed") is not True
        or not isinstance(historical_verification_blockers, list)
        or historical_verification_blockers != []
        or not _sha256_hex(historical_audit.get("audit_hash"))
        or not _sha256_hex(historical_audit.get("artifact_hash"))
    ):
        return blocked

    audit_semantics = _forward_audit_v2_semantics(
        forward_audit,
        candidate=active_candidate,
        candidate_hash=candidate_hash,
        spec_hash=spec_hash,
        historical_audit=historical_audit,
        observer_generated_at=observer_generated_at,
        performance_generated_at=performance_generated_at,
    )
    if (
        audit_semantics is None
        or shadow_semantics["signal_dates"]
        != [str(row["date"]) for row in audit_semantics["rows"]]
    ):
        return blocked

    settlement_count = int(audit_semantics["settlement_count"])
    strategy_summary = performance_summary.get("strategy")
    unsettled_dates = performance_summary.get("unsettled_observation_dates")
    performance_failure_lists = (
        unsettled_dates,
        performance_summary.get("unexpected_settlement_dates"),
        performance_summary.get("observation_hash_mismatch_dates"),
        performance_summary.get("integrity_violations"),
    )
    performance_shape_valid = (
        performance_summary.get("schema_version")
        == PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION
        and performance_summary.get("candidate_hash") == candidate_hash
        and performance_summary.get("first_settlement_date")
        == audit_semantics["first_settlement_date"]
        and performance_summary.get("last_settlement_date")
        == audit_semantics["last_settlement_date"]
        and all(
            isinstance(items, list) and items == []
            for items in performance_failure_lists
        )
        and performance_summary.get("observation_only") is True
        and performance_summary.get("simulation_only") is True
        and performance_summary.get("paper_authorized") is False
        and performance_summary.get("live_order_allowed") is False
    )
    performance_counts_match = (
        _strict_nonnegative_integer(performance_summary.get("settlement_count"))
        == settlement_count
        and _strict_nonnegative_integer(
            performance_summary.get("outcome_period_count")
        )
        == audit_semantics["outcome_period_count"]
        and _strict_nonnegative_integer(
            performance_summary.get("rebalance_execution_count")
        )
        == audit_semantics["rebalance_execution_count"]
        and _strict_nonnegative_integer(shadow_audit.get("valid_observation_count"))
        == settlement_count
        and _strict_nonnegative_integer(
            shadow_audit.get("execution_authority_violation_count")
        )
        == 0
        and _strict_nonnegative_integer(
            performance_summary.get("execution_authority_violation_count")
        )
        == 0
    )
    latest_hash_matches = (
        performance_summary.get("latest_settlement_hash")
        == audit_semantics["latest_settlement_hash"]
        if settlement_count
        else not performance_summary.get("latest_settlement_hash")
    )
    strategy_drawdown_matches = (
        isinstance(strategy_summary, dict)
        and _close(
            strategy_summary.get("max_drawdown_pct"),
            audit_semantics["strategy_max_drawdown_pct"],
        )
        if settlement_count
        else isinstance(strategy_summary, dict) and strategy_summary == {}
    )
    if (
        not performance_shape_valid
        or not performance_counts_match
        or not latest_hash_matches
        or not _close(
            performance_summary.get("cumulative_excess_return_pct"),
            audit_semantics["cumulative_excess_return_pct"],
        )
        or not strategy_drawdown_matches
    ):
        return blocked

    rebuilt_performance_summary = dict(performance_summary)
    rebuilt_performance_summary["cumulative_excess_return_pct"] = audit_semantics[
        "cumulative_excess_return_pct"
    ]
    if settlement_count:
        rebuilt_strategy = dict(strategy_summary)
        rebuilt_strategy["max_drawdown_pct"] = audit_semantics[
            "strategy_max_drawdown_pct"
        ]
        rebuilt_performance_summary["strategy"] = rebuilt_strategy

    rebuilt = build_forward_performance_readiness(
        candidate=active_candidate,
        shadow_audit=shadow_audit,
        performance_summary=rebuilt_performance_summary,
        historical_statistical_audit=historical_audit,
        forward_statistical_audit=forward_audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    )
    source_status = str(rebuilt.get("status") or "")
    if (
        rebuilt.get("schema_version")
        != PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION
        or _canonical_bytes(rebuilt) != _canonical_bytes(declared_readiness)
        or str(performance_status.get("status") or "") != source_status
        or source_status not in _STATUS_MAP
        or str(rebuilt.get("decision_policy") or "")
        != PORTFOLIO_FORWARD_DECISION_POLICY
        or str(rebuilt.get("decision_status") or "")
        != audit_semantics["decision_status"]
        or str(rebuilt.get("research_action") or "")
        != audit_semantics["research_action"]
    ):
        return blocked

    progress_source = dict(rebuilt.get("progress") or {})
    progress = {
        field: _strict_nonnegative_integer(progress_source.get(field))
        for field in _PROGRESS_FIELDS
    }
    if any(value is None for value in progress.values()):
        return blocked
    projected_status = _STATUS_MAP[source_status]
    source_binding = _verified_source_binding(
        candidate_hash=candidate_hash,
        observation_chain=list(shadow_semantics["observation_chain"]),
        settlement_rows=list(audit_semantics["rows"]),
        backup_status=backup_status,
        watchdog_status=watchdog_status,
        backup_read_status=backup_read_status,
        watchdog_read_status=watchdog_read_status,
        observed_now_ms=observed_now_ms,
    )
    if source_binding["status"] == "CONTRADICTION":
        return _projection_v3(
            status="BLOCK",
            candidate_hash=candidate_hash,
            source_binding=source_binding,
        )
    return _projection_v3(
        status=projected_status,
        candidate_hash=candidate_hash,
        progress=(
            {field: int(progress[field]) for field in _PROGRESS_FIELDS}
            if projected_status != "BLOCK"
            else _empty_progress()
        ),
        source_binding=source_binding,
        decision_status=audit_semantics["decision_status"],
        research_action=audit_semantics["research_action"],
        decision_hash=audit_semantics["decision_hash"],
        stage_hash=audit_semantics["stage_hash"],
        risk_acceptance_hash=audit_semantics["risk_acceptance_hash"],
        first_due_settlement_hash=audit_semantics[
            "first_due_settlement_hash"
        ],
    )


def build_portfolio_forward_statistical_maturity(
    *,
    active_candidate: dict[str, Any] | None,
    observer_status: dict[str, Any] | None,
    performance_status: dict[str, Any] | None,
    backup_status: dict[str, Any] | None = None,
    watchdog_status: dict[str, Any] | None = None,
    backup_read_status: str = "MISSING",
    watchdog_read_status: str = "MISSING",
    observed_now_ms: int,
    maturity_schema_version: str = PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Join current observer and performance evidence into a public safe projection.

    This rebuilds readiness and the embedded paired-series statistical stage.
    It does not replay the live settlement ledger or prove external authenticity.
    """

    if (
        maturity_schema_version
        not in {
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
        }
    ):
        return _projection_v3(status="BLOCK")

    try:
        if (
            maturity_schema_version
            == PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION
        ):
            return _verified_projection_v3(
                active_candidate=dict(active_candidate or {}),
                observer_status=dict(observer_status or {}),
                performance_status=dict(performance_status or {}),
                backup_status=dict(backup_status or {}),
                watchdog_status=dict(watchdog_status or {}),
                backup_read_status=str(backup_read_status or ""),
                watchdog_read_status=str(watchdog_read_status or ""),
                observed_now_ms=observed_now_ms,
            )
        return _verified_projection(
            active_candidate=dict(active_candidate or {}),
            observer_status=dict(observer_status or {}),
            performance_status=dict(performance_status or {}),
            backup_status=dict(backup_status or {}),
            watchdog_status=dict(watchdog_status or {}),
            backup_read_status=str(backup_read_status or ""),
            watchdog_read_status=str(watchdog_read_status or ""),
            observed_now_ms=observed_now_ms,
        )
    except (
        AttributeError,
        KeyError,
        MemoryError,
        OverflowError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        if (
            maturity_schema_version
            == PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION
        ):
            return _projection_v3(status="BLOCK")
        return _projection(status="BLOCK")
