from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from typing import Any

from .execution_authority import authority_violations


PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION = (
    "portfolio-forward-local-source-anchor-v1"
)
PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE = (
    "LOCAL_ARCHIVE_CROSS_ARTIFACT_BINDING_ONLY"
)
MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_ROWS = 1024

PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_FIELDS = frozenset({
    "schema_version",
    "status",
    "reason",
    "candidate_hash",
    "archive_manifest_hash",
    "archive_generated_at",
    "observation_count",
    "first_observation_date",
    "last_observation_date",
    "settlement_count",
    "first_settlement_date",
    "last_settlement_date",
    "observer_projection_hash",
    "settlement_projection_hash",
    "cross_binding_hash",
    "shadow_database_sha256",
    "performance_database_sha256",
    "trust_scope",
    "external_authenticity_proven",
    "profitability_proven",
    "research_only",
    "observation_only",
    "simulation_only",
    "paper_authorized",
    "live_order_allowed",
    "anchor_hash",
})
PORTFOLIO_FORWARD_LOCAL_SOURCE_OBSERVER_ROW_FIELDS = frozenset({
    "signal_date",
    "observation_hash",
    "change_projection_hash",
})
PORTFOLIO_FORWARD_LOCAL_SOURCE_SETTLEMENT_ROW_FIELDS = frozenset({
    "date",
    "settlement_type",
    "settlement_hash",
    "previous_settlement_hash",
    "strategy_equity",
    "benchmark_equity",
    "strategy_daily_return_pct",
    "benchmark_daily_return_pct",
    "rebalance_executed",
})
PORTFOLIO_FORWARD_LOCAL_SOURCE_CROSS_BINDING_ROW_FIELDS = frozenset({
    "date",
    "settlement_hash",
    "observation_hash",
})
PORTFOLIO_FORWARD_LOCAL_SOURCE_NOT_AVAILABLE_REASONS = frozenset({
    "ARCHIVE_SCHEMA_NOT_SUPPORTED",
    "CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE",
})


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_integer(value: Any, *, minimum: int = 0) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > MAX_SAFE_INTEGER
    ):
        return None
    return value


def _iso_date(value: Any) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return ""
    return text if parsed.isoformat() == text else ""


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalize_portfolio_local_source_observer_projection(
    rows: Any,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("local_source_observer_projection_invalid")
    if len(rows) > MAX_PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_ROWS:
        raise ValueError("local_source_observer_projection_size_limit_exceeded")
    projection: list[dict[str, Any]] = []
    for index, raw_row in enumerate(rows):
        row = dict(raw_row or {}) if isinstance(raw_row, dict) else {}
        if set(row) != PORTFOLIO_FORWARD_LOCAL_SOURCE_OBSERVER_ROW_FIELDS:
            raise ValueError(f"local_source_observer_row_fields_invalid:{index}")
        clean_date = _iso_date(row.get("signal_date"))
        observation_hash = str(row.get("observation_hash") or "")
        change_projection_hash = str(row.get("change_projection_hash") or "")
        if not clean_date:
            raise ValueError(f"local_source_observer_date_invalid:{index}")
        if not _sha256_hex(observation_hash):
            raise ValueError(f"local_source_observer_hash_invalid:{index}")
        if not _sha256_hex(change_projection_hash):
            raise ValueError(f"local_source_observer_change_hash_invalid:{index}")
        projection.append({
            "signal_date": clean_date,
            "observation_hash": observation_hash,
            "change_projection_hash": change_projection_hash,
        })
    dates = [str(row["signal_date"]) for row in projection]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("local_source_observer_dates_invalid")
    return projection


def portfolio_local_source_observer_projection_from_chain(
    observation_chain: Any,
) -> list[dict[str, Any]]:
    if not isinstance(observation_chain, list):
        raise ValueError("local_source_observation_chain_invalid")
    rows: list[dict[str, Any]] = []
    for index, raw_row in enumerate(observation_chain):
        row = dict(raw_row or {}) if isinstance(raw_row, dict) else {}
        if set(row) != PORTFOLIO_FORWARD_LOCAL_SOURCE_OBSERVER_ROW_FIELDS:
            raise ValueError(f"local_source_observation_chain_fields_invalid:{index}")
        rows.append({
            "signal_date": str(row.get("signal_date") or ""),
            "observation_hash": str(row.get("observation_hash") or ""),
            "change_projection_hash": str(row.get("change_projection_hash") or ""),
        })
    return normalize_portfolio_local_source_observer_projection(rows)


def normalize_portfolio_local_source_settlement_projection(
    rows: Any,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("local_source_settlement_projection_invalid")
    if len(rows) > MAX_PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_ROWS:
        raise ValueError("local_source_settlement_projection_size_limit_exceeded")
    projection: list[dict[str, Any]] = []
    for index, raw_row in enumerate(rows):
        row = dict(raw_row or {}) if isinstance(raw_row, dict) else {}
        if set(row) != PORTFOLIO_FORWARD_LOCAL_SOURCE_SETTLEMENT_ROW_FIELDS:
            raise ValueError(f"local_source_settlement_row_fields_invalid:{index}")
        clean_date = _iso_date(row.get("date"))
        settlement_type = str(row.get("settlement_type") or "")
        settlement_hash = str(row.get("settlement_hash") or "")
        previous_settlement_hash = str(row.get("previous_settlement_hash") or "")
        strategy_equity = _finite_number(row.get("strategy_equity"))
        benchmark_equity = _finite_number(row.get("benchmark_equity"))
        strategy_return = _finite_number(row.get("strategy_daily_return_pct"))
        benchmark_return = _finite_number(row.get("benchmark_daily_return_pct"))
        rebalance_executed = row.get("rebalance_executed")
        if not clean_date:
            raise ValueError(f"local_source_settlement_date_invalid:{index}")
        if not settlement_type:
            raise ValueError(f"local_source_settlement_type_invalid:{index}")
        if not _sha256_hex(settlement_hash):
            raise ValueError(f"local_source_settlement_hash_invalid:{index}")
        if index == 0:
            if previous_settlement_hash:
                raise ValueError("local_source_initial_previous_settlement_hash_invalid")
        elif previous_settlement_hash != str(projection[index - 1]["settlement_hash"]):
            raise ValueError(f"local_source_previous_settlement_hash_invalid:{index}")
        if strategy_equity is None or strategy_equity <= 0:
            raise ValueError(f"local_source_strategy_equity_invalid:{index}")
        if benchmark_equity is None or benchmark_equity <= 0:
            raise ValueError(f"local_source_benchmark_equity_invalid:{index}")
        if strategy_return is None or benchmark_return is None:
            raise ValueError(f"local_source_daily_return_invalid:{index}")
        if not isinstance(rebalance_executed, bool):
            raise ValueError(f"local_source_rebalance_flag_invalid:{index}")
        projection.append({
            "date": clean_date,
            "settlement_type": settlement_type,
            "settlement_hash": settlement_hash,
            "previous_settlement_hash": previous_settlement_hash,
            "strategy_equity": strategy_equity,
            "benchmark_equity": benchmark_equity,
            "strategy_daily_return_pct": strategy_return,
            "benchmark_daily_return_pct": benchmark_return,
            "rebalance_executed": rebalance_executed,
        })
    dates = [str(row["date"]) for row in projection]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("local_source_settlement_dates_invalid")
    if projection:
        if projection[0]["settlement_type"] != "BASELINE":
            raise ValueError("local_source_settlement_baseline_missing")
        if sum(row["settlement_type"] == "BASELINE" for row in projection) != 1:
            raise ValueError("local_source_settlement_baseline_count_invalid")
    return projection


def portfolio_local_source_settlement_projection_from_settlements(
    settlements: Any,
) -> list[dict[str, Any]]:
    if not isinstance(settlements, list):
        raise ValueError("local_source_settlements_invalid")
    rows: list[dict[str, Any]] = []
    for raw_settlement in settlements:
        settlement = dict(raw_settlement or {}) if isinstance(raw_settlement, dict) else {}
        strategy = dict(settlement.get("strategy") or {})
        benchmark = dict(settlement.get("benchmark") or {})
        decision = dict(settlement.get("decision_execution") or {})
        rows.append({
            "date": str(settlement.get("settlement_date") or ""),
            "settlement_type": str(settlement.get("settlement_type") or ""),
            "settlement_hash": str(settlement.get("settlement_hash") or ""),
            "previous_settlement_hash": str(settlement.get("previous_settlement_hash") or ""),
            "strategy_equity": strategy.get("equity"),
            "benchmark_equity": benchmark.get("equity"),
            "strategy_daily_return_pct": strategy.get("daily_return_pct"),
            "benchmark_daily_return_pct": benchmark.get("daily_return_pct"),
            "rebalance_executed": bool(
                decision.get("execute") is True
                and str(decision.get("reason") or "") == "relative_strength_rebalance"
                and str(decision.get("status") or "") in {"EXECUTED", "EXECUTED_NO_FILL"}
            ),
        })
    return normalize_portfolio_local_source_settlement_projection(rows)


def build_portfolio_local_source_cross_binding_projection(
    observer_projection: Any,
    settlement_projection: Any,
) -> list[dict[str, Any]]:
    observers = normalize_portfolio_local_source_observer_projection(observer_projection)
    settlements = normalize_portfolio_local_source_settlement_projection(settlement_projection)
    observer_dates = [str(row["signal_date"]) for row in observers]
    settlement_dates = [str(row["date"]) for row in settlements]
    if not observers or observer_dates != settlement_dates:
        raise ValueError("local_source_cross_binding_dates_invalid")
    return [
        {
            "date": str(settlement["date"]),
            "settlement_hash": str(settlement["settlement_hash"]),
            "observation_hash": str(observer["observation_hash"]),
        }
        for observer, settlement in zip(observers, settlements)
    ]


def portfolio_local_source_projection_hashes(
    *,
    observer_projection: Any,
    settlement_projection: Any,
) -> dict[str, Any]:
    observers = normalize_portfolio_local_source_observer_projection(observer_projection)
    settlements = normalize_portfolio_local_source_settlement_projection(settlement_projection)
    cross_binding = build_portfolio_local_source_cross_binding_projection(
        observers,
        settlements,
    )
    return {
        "observer_projection": observers,
        "settlement_projection": settlements,
        "cross_binding_projection": cross_binding,
        "observer_projection_hash": canonical_hash(observers),
        "settlement_projection_hash": canonical_hash(settlements),
        "cross_binding_hash": canonical_hash(cross_binding),
    }


def _seal_anchor(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["anchor_hash"] = canonical_hash(result)
    return result


def build_portfolio_forward_local_source_anchor(
    *,
    candidate_hash: str,
    archive_manifest_hash: str,
    archive_generated_at: int,
    observer_projection: Any,
    settlement_projection: Any,
    shadow_database_sha256: str,
    performance_database_sha256: str,
) -> dict[str, Any]:
    if not _sha256_hex(candidate_hash):
        raise ValueError("local_source_anchor_candidate_hash_invalid")
    if not _sha256_hex(archive_manifest_hash):
        raise ValueError("local_source_anchor_manifest_hash_invalid")
    generated_at = _safe_integer(archive_generated_at, minimum=1)
    if generated_at is None:
        raise ValueError("local_source_anchor_generated_at_invalid")
    if not _sha256_hex(shadow_database_sha256):
        raise ValueError("local_source_anchor_shadow_database_hash_invalid")
    if not _sha256_hex(performance_database_sha256):
        raise ValueError("local_source_anchor_performance_database_hash_invalid")
    projections = portfolio_local_source_projection_hashes(
        observer_projection=observer_projection,
        settlement_projection=settlement_projection,
    )
    observers = list(projections["observer_projection"])
    settlements = list(projections["settlement_projection"])
    if not observers or len(observers) != len(settlements):
        raise ValueError("local_source_anchor_projection_count_invalid")
    payload = {
        "schema_version": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION,
        "status": "VERIFIED",
        "reason": "",
        "candidate_hash": candidate_hash,
        "archive_manifest_hash": archive_manifest_hash,
        "archive_generated_at": generated_at,
        "observation_count": len(observers),
        "first_observation_date": str(observers[0]["signal_date"]),
        "last_observation_date": str(observers[-1]["signal_date"]),
        "settlement_count": len(settlements),
        "first_settlement_date": str(settlements[0]["date"]),
        "last_settlement_date": str(settlements[-1]["date"]),
        "observer_projection_hash": str(projections["observer_projection_hash"]),
        "settlement_projection_hash": str(projections["settlement_projection_hash"]),
        "cross_binding_hash": str(projections["cross_binding_hash"]),
        "shadow_database_sha256": shadow_database_sha256,
        "performance_database_sha256": performance_database_sha256,
        "trust_scope": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return _seal_anchor(payload)


def build_portfolio_forward_local_source_anchor_not_available(
    *,
    reason: str,
    candidate_hash: str = "",
    archive_manifest_hash: str = "",
    archive_generated_at: int = 0,
) -> dict[str, Any]:
    if reason not in PORTFOLIO_FORWARD_LOCAL_SOURCE_NOT_AVAILABLE_REASONS:
        raise ValueError("local_source_anchor_not_available_reason_invalid")
    if candidate_hash and not _sha256_hex(candidate_hash):
        raise ValueError("local_source_anchor_candidate_hash_invalid")
    if archive_manifest_hash and not _sha256_hex(archive_manifest_hash):
        raise ValueError("local_source_anchor_manifest_hash_invalid")
    generated_at = _safe_integer(archive_generated_at)
    if generated_at is None:
        raise ValueError("local_source_anchor_generated_at_invalid")
    return _seal_anchor({
        "schema_version": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION,
        "status": "NOT_AVAILABLE",
        "reason": reason,
        "candidate_hash": candidate_hash,
        "archive_manifest_hash": archive_manifest_hash,
        "archive_generated_at": generated_at,
        "observation_count": 0,
        "first_observation_date": "",
        "last_observation_date": "",
        "settlement_count": 0,
        "first_settlement_date": "",
        "last_settlement_date": "",
        "observer_projection_hash": "",
        "settlement_projection_hash": "",
        "cross_binding_hash": "",
        "shadow_database_sha256": "",
        "performance_database_sha256": "",
        "trust_scope": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    })


def verify_portfolio_forward_local_source_anchor(payload: Any) -> dict[str, Any]:
    blockers: list[str] = []
    anchor = dict(payload or {}) if isinstance(payload, dict) else {}
    if not isinstance(payload, dict) or set(anchor) != PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_FIELDS:
        blockers.append("local_source_anchor_fields_invalid")
    if anchor.get("schema_version") != PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION:
        blockers.append("local_source_anchor_schema_invalid")
    clean = dict(anchor)
    expected_hash = str(clean.pop("anchor_hash", "") or "")
    if not _sha256_hex(expected_hash) or canonical_hash(clean) != expected_hash:
        blockers.append("local_source_anchor_hash_invalid")
    if anchor.get("trust_scope") != PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE:
        blockers.append("local_source_anchor_trust_scope_invalid")
    if (
        anchor.get("external_authenticity_proven") is not False
        or anchor.get("profitability_proven") is not False
        or anchor.get("research_only") is not True
        or anchor.get("observation_only") is not True
        or anchor.get("simulation_only") is not True
        or anchor.get("paper_authorized") is not False
        or anchor.get("live_order_allowed") is not False
    ):
        blockers.append("local_source_anchor_authority_invalid")
    if authority_violations(anchor):
        blockers.append("local_source_anchor_contains_execution_authority")

    status = str(anchor.get("status") or "")
    generated_at = _safe_integer(anchor.get("archive_generated_at"))
    if generated_at is None:
        blockers.append("local_source_anchor_generated_at_invalid")
    if status == "VERIFIED":
        if generated_at is None or generated_at < 1:
            blockers.append("local_source_anchor_generated_at_invalid")
        if str(anchor.get("reason") or ""):
            blockers.append("local_source_anchor_verified_reason_invalid")
        for field in (
            "candidate_hash",
            "archive_manifest_hash",
            "observer_projection_hash",
            "settlement_projection_hash",
            "cross_binding_hash",
            "shadow_database_sha256",
            "performance_database_sha256",
        ):
            if not _sha256_hex(anchor.get(field)):
                blockers.append(f"local_source_anchor_{field}_invalid")
        observation_count = _safe_integer(anchor.get("observation_count"), minimum=1)
        settlement_count = _safe_integer(anchor.get("settlement_count"), minimum=1)
        if (
            observation_count is None
            or settlement_count is None
            or observation_count != settlement_count
            or observation_count > MAX_PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_ROWS
        ):
            blockers.append("local_source_anchor_count_invalid")
        observation_dates = (
            _iso_date(anchor.get("first_observation_date")),
            _iso_date(anchor.get("last_observation_date")),
        )
        settlement_dates = (
            _iso_date(anchor.get("first_settlement_date")),
            _iso_date(anchor.get("last_settlement_date")),
        )
        if (
            not all(observation_dates)
            or not all(settlement_dates)
            or observation_dates != settlement_dates
            or observation_dates[0] > observation_dates[1]
        ):
            blockers.append("local_source_anchor_dates_invalid")
    elif status == "NOT_AVAILABLE":
        if str(anchor.get("reason") or "") not in PORTFOLIO_FORWARD_LOCAL_SOURCE_NOT_AVAILABLE_REASONS:
            blockers.append("local_source_anchor_not_available_reason_invalid")
        unavailable_fields = (
            "first_observation_date",
            "last_observation_date",
            "first_settlement_date",
            "last_settlement_date",
            "observer_projection_hash",
            "settlement_projection_hash",
            "cross_binding_hash",
            "shadow_database_sha256",
            "performance_database_sha256",
        )
        if any(str(anchor.get(field) or "") for field in unavailable_fields):
            blockers.append("local_source_anchor_not_available_evidence_invalid")
        if anchor.get("observation_count") != 0 or anchor.get("settlement_count") != 0:
            blockers.append("local_source_anchor_not_available_count_invalid")
        for field in ("candidate_hash", "archive_manifest_hash"):
            value = str(anchor.get(field) or "")
            if value and not _sha256_hex(value):
                blockers.append(f"local_source_anchor_{field}_invalid")
    else:
        blockers.append("local_source_anchor_status_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "anchor_status": status if status in {"VERIFIED", "NOT_AVAILABLE"} else "BLOCK",
        "candidate_hash": str(anchor.get("candidate_hash") or ""),
        "anchor_hash": expected_hash,
        "trust_scope": PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_TRUST_SCOPE,
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
