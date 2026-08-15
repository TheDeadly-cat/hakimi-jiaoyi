from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.portfolio_candidate import PORTFOLIO_CANDIDATE_SCHEMA_VERSION
from exchange_terminal.services.portfolio_forward_performance import (
    PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    build_forward_performance_readiness,
    forward_evidence_thresholds_from_spec,
)
from exchange_terminal.services.portfolio_evidence_archive import (
    build_portfolio_backup_status,
    verify_portfolio_backup_status,
)
from exchange_terminal.services.portfolio_forward_local_source_anchor import (
    build_portfolio_forward_local_source_anchor,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
    audit_forward_portfolio_statistics_v2,
    forward_statistical_audit_content,
)
from exchange_terminal.services.portfolio_forward_statistical_maturity import (
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V1_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_SOURCE_BINDING_SCHEMA_VERSION,
    build_portfolio_forward_statistical_maturity,
)
from exchange_terminal.services.portfolio_forward_watchdog import (
    build_portfolio_forward_watchdog_status,
)
from exchange_terminal.services.portfolio_shadow import (
    PORTFOLIO_SHADOW_SCHEMA_VERSION,
    seal_forward_status_artifact,
)
from exchange_terminal.services.portfolio_statistical_audit import (
    DEFAULT_BLOCK_LENGTH,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_MINIMUM_OBSERVATIONS,
    DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
    DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
    DEFAULT_RESAMPLE_COUNT,
    PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
    audit_paired_equity_curve_stage,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def frozen_candidate(*, required: int = 2) -> dict[str, object]:
    spec = {
        "minimum_forward_observations": required,
        "minimum_forward_performance_outcomes": required,
        "minimum_planned_rebalances": required,
        "trial_count": 1,
        "acceptance_contract": {
            "validation_and_test_max_drawdown_below_pct": 15.0,
        },
    }
    payload: dict[str, object] = {
        "schema_version": PORTFOLIO_CANDIDATE_SCHEMA_VERSION,
        "status": "FROZEN_DEVELOPMENT_CANDIDATE",
        "spec": spec,
        "spec_hash": canonical_hash(spec),
        "development_trial_count": 1,
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "authorization_state": "BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["candidate_hash"] = canonical_hash(payload)
    return payload


def maturity_bundle(
    source_status: str,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    required = DEFAULT_BLOCK_LENGTH
    candidate = frozen_candidate(required=required)
    candidate_hash = str(candidate["candidate_hash"])
    due = source_status != "COLLECTING"
    if source_status == "RESEARCH_REVIEW_BLOCKED":
        strategy_equities = [100.0]
        for index in range(required):
            loss = 0.01 if index % 2 == 0 else 0.02
            strategy_equities.append(
                round(strategy_equities[-1] * (1.0 - loss), 8)
            )
    elif due:
        strategy_equities = [100.0]
        for index in range(required):
            gain = 0.01 if index % 2 == 0 else 0.02
            strategy_equities.append(
                round(strategy_equities[-1] * (1.0 + gain), 8)
            )
    else:
        strategy_equities = [100.0, 101.0]
    benchmark_equities = [100.0 for _ in strategy_equities]
    settlement_count = len(strategy_equities)
    outcomes = settlement_count - 1
    rebalances = outcomes
    signal_dates = [f"2026-08-{index + 1:02d}" for index in range(settlement_count)]
    observation_chain = [
        {
            "signal_date": signal_date,
            "observation_hash": canonical_hash(f"observation-{index}"),
            "change_projection_hash": canonical_hash(f"change-{index}"),
        }
        for index, signal_date in enumerate(signal_dates)
    ]
    shadow_audit = {
        "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
        "status": "PASS",
        "candidate_hash": candidate_hash,
        "observation_count": settlement_count,
        "valid_observation_count": settlement_count,
        "timely_observation_count": settlement_count,
        "externally_attested_observation_count": settlement_count,
        "activation_verified_observation_count": settlement_count,
        "forward_state_verified_observation_count": settlement_count,
        "clock_attestation_violation_count": 0,
        "candidate_activation_violation_count": 0,
        "risk_pass_observation_count": settlement_count,
        "planned_rebalance_count": rebalances,
        "first_signal_date": signal_dates[0],
        "last_signal_date": signal_dates[-1],
        "observation_chain": observation_chain,
        "observation_chain_count": settlement_count,
        "observation_chain_hash": canonical_hash(observation_chain),
        "latest_dataset_hash": canonical_hash("latest-dataset"),
        "latest_decision_hash": canonical_hash("latest-decision"),
        "latest_observation_hash": observation_chain[-1]["observation_hash"],
        "latest_forward_state_contract_hash": canonical_hash("latest-forward-state"),
        "latest_observation_risk_snapshot_hash": canonical_hash("latest-risk"),
        "risk_reassessment_count": 0,
        "risk_block_reassessment_count": 0,
        "capture_violation_count": 0,
        "neutral_capture_event_count": 0,
        "missed_capture_count": 0,
        "decision_replay_conflict_count": 0,
        "capture_event_types": {},
        "execution_authority_violation_count": 0,
        "integrity_violations": [],
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    observer = seal_forward_status_artifact({
        "status": "OBSERVED",
        "generated_at": 100,
        "candidate_hash": candidate_hash,
        "ledger": {"forward_audit": shadow_audit},
        "readiness": {"ledger_audit": shadow_audit},
    })

    def daily_returns(equities: list[float]) -> list[float]:
        return [
            0.0
            if index == 0
            else round((equity / equities[index - 1] - 1.0) * 100.0, 8)
            for index, equity in enumerate(equities)
        ]

    strategy_returns = daily_returns(strategy_equities)
    benchmark_returns = daily_returns(benchmark_equities)
    peak = strategy_equities[0]
    max_drawdown = 0.0
    for equity in strategy_equities:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, max(0.0, 1.0 - equity / peak) * 100.0)
    cumulative_excess = round(
        (
            (strategy_equities[-1] / strategy_equities[0] - 1.0)
            - (benchmark_equities[-1] / benchmark_equities[0] - 1.0)
        )
        * 100.0,
        8,
    )
    performance_summary = {
        "schema_version": PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
        "status": "PASS",
        "candidate_hash": candidate_hash,
        "settlement_count": settlement_count,
        "outcome_period_count": outcomes,
        "first_settlement_date": signal_dates[0],
        "last_settlement_date": signal_dates[-1],
        "rebalance_execution_count": rebalances,
        "execution_authority_violation_count": 0,
        "unsettled_observation_dates": [],
        "unexpected_settlement_dates": [],
        "observation_hash_mismatch_dates": [],
        "integrity_violations": [],
        "latest_settlement_hash": canonical_hash(f"settlement-{settlement_count - 1}"),
        "strategy": {"max_drawdown_pct": round(max_drawdown, 8)},
        "cumulative_excess_return_pct": cumulative_excess,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    historical = {
        "status": "BLOCK",
        "conclusion": "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE",
        "audit_hash": "a" * 64,
        "artifact_hash": "b" * 64,
        "verification_status": "PASS",
        "verification_blockers": [],
        "semantic_recomputed": True,
    }
    ordered_hashes = [
        canonical_hash(f"settlement-{index}") for index in range(settlement_count)
    ]
    rows = []
    for index, settlement_hash in enumerate(ordered_hashes):
        rows.append({
            "date": f"2026-08-{index + 1:02d}",
            "settlement_type": "BASELINE" if index == 0 else "DAILY_CLOSE",
            "settlement_hash": settlement_hash,
            "previous_settlement_hash": "" if index == 0 else ordered_hashes[index - 1],
            "strategy_equity": strategy_equities[index],
            "benchmark_equity": benchmark_equities[index],
            "strategy_daily_return_pct": strategy_returns[index],
            "benchmark_daily_return_pct": benchmark_returns[index],
            "rebalance_executed": index > 0,
        })
    series_content = {
        "schema_version": PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
        "candidate_hash": candidate_hash,
        "settlement_count": settlement_count,
        "outcome_period_count": outcomes,
        "rebalance_execution_count": rebalances,
        "first_settlement_date": rows[0]["date"],
        "last_settlement_date": rows[-1]["date"],
        "first_settlement_hash": ordered_hashes[0],
        "latest_settlement_hash": ordered_hashes[-1],
        "ordered_settlement_hashes": ordered_hashes,
        "rows": rows,
        "source_validation": "FULL_SETTLEMENT_SEMANTIC_CHAIN_RECOMPUTED",
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    series = {**series_content, "series_hash": canonical_hash(series_content)}
    historical_config = {
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": DEFAULT_RESAMPLE_COUNT,
        "block_length": DEFAULT_BLOCK_LENGTH,
        "minimum_observations": DEFAULT_MINIMUM_OBSERVATIONS,
        "confidence_level": DEFAULT_CONFIDENCE_LEVEL,
        "required_positive_probability": DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
        "required_selection_adjusted_probability": DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": 1,
    }
    statistical_contract = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": DEFAULT_RESAMPLE_COUNT,
        "block_length": DEFAULT_BLOCK_LENGTH,
        "confidence_level": DEFAULT_CONFIDENCE_LEVEL,
        "required_positive_probability": DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
        "required_selection_adjusted_probability": DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": 1,
        "minimum_observations": required,
        "minimum_observations_policy": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        "source_historical_minimum_observations": DEFAULT_MINIMUM_OBSERVATIONS,
        "source_historical_audit_schema_version": PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "source_historical_audit_hash": historical["audit_hash"],
        "source_historical_artifact_hash": historical["artifact_hash"],
        "source_historical_claim_status": historical["status"],
        "source_historical_config_hash": canonical_hash(historical_config),
        "source_historical_input_binding_hash": canonical_hash({
            "fixture": "historical-input-binding"
        }),
    }
    statistical_contract["contract_hash"] = canonical_hash(statistical_contract)
    copied_fields = {
        field: {
            "historical": historical_config[field],
            "forward": statistical_contract[field],
            "matches": True,
        }
        for field in (
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
    }
    contract_comparison = {
        "status": "PASS",
        "copied_fields": copied_fields,
        "allowed_difference": {
            "field": "minimum_observations",
            "historical": DEFAULT_MINIMUM_OBSERVATIONS,
            "forward": required,
            "reason": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        },
        "other_differences_allowed": False,
    }
    binding = {
        "candidate_hash": candidate_hash,
        "candidate_spec_hash": canonical_hash(candidate["spec"]),
        "candidate_declared_spec_hash": candidate["spec_hash"],
        "historical_statistical_audit_schema_version": PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "historical_statistical_audit_hash": historical["audit_hash"],
        "historical_statistical_artifact_hash": historical["artifact_hash"],
        "historical_statistical_config_hash": statistical_contract[
            "source_historical_config_hash"
        ],
        "historical_statistical_input_binding_hash": statistical_contract[
            "source_historical_input_binding_hash"
        ],
        "statistical_contract_hash": statistical_contract["contract_hash"],
        "forward_threshold_contract_hash": canonical_hash(
            forward_evidence_thresholds_from_spec(dict(candidate["spec"]))
        ),
        "forward_series_hash": series["series_hash"],
        "ordered_settlement_hashes_hash": canonical_hash(ordered_hashes),
        "first_settlement_date": series["first_settlement_date"],
        "last_settlement_date": series["last_settlement_date"],
        "first_settlement_hash": series["first_settlement_hash"],
        "latest_settlement_hash": series["latest_settlement_hash"],
        "settlement_count": settlement_count,
        "outcome_period_count": outcomes,
        "rebalance_execution_count": rebalances,
    }
    binding["binding_hash"] = canonical_hash(binding)
    maturity = {
        "status": "DUE" if due else "NOT_DUE",
        "forward_outcomes": outcomes,
        "required_forward_outcomes": required,
        "remaining_forward_outcomes": max(required - outcomes, 0),
        "executed_rebalances": rebalances,
        "required_executed_rebalances": required,
        "remaining_executed_rebalances": max(required - rebalances, 0),
        "both_thresholds_required": True,
    }
    stage: dict[str, object] = {}
    if due:
        seed = int(canonical_hash({
            "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
            "input_binding": binding,
            "statistical_contract": statistical_contract,
            "stage": "natural_forward",
        })[:16], 16)
        stage = audit_paired_equity_curve_stage(
            stage="natural_forward",
            strategy_report={
                "initial_cash": strategy_equities[0],
                "equity_curve": [
                    {"date": rows[index]["date"], "equity": strategy_equities[index]}
                    for index in range(1, settlement_count)
                ],
            },
            benchmark_report={
                "initial_cash": benchmark_equities[0],
                "equity_curve": [
                    {"date": rows[index]["date"], "equity": benchmark_equities[index]}
                    for index in range(1, settlement_count)
                ],
            },
            resample_count=DEFAULT_RESAMPLE_COUNT,
            block_length=DEFAULT_BLOCK_LENGTH,
            minimum_observations=required,
            confidence_level=DEFAULT_CONFIDENCE_LEVEL,
            required_positive_probability=DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
            required_adjusted_probability=DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
            selection_trial_count=1,
            seed=seed,
        )
    stage_pass = due and stage.get("status") == "PASS"
    if not due:
        audit_status = "NOT_DUE"
        audit_conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
        audit_blockers: list[str] = []
    elif stage_pass:
        audit_status = "PASS"
        audit_conclusion = "FORWARD_STATISTICAL_CONTRACT_PASS"
        audit_blockers = []
    else:
        audit_status = "BLOCK"
        audit_conclusion = "FORWARD_STATISTICAL_CONTRACT_FAILED"
        audit_blockers = [
            f"natural_forward:{item}"
            for item in stage.get("blockers") or ["statistical_stage_not_passed"]
        ]
    checks = {
        "candidate_authority_is_research_only": True,
        "forward_threshold_contract_pass": True,
        "settlement_series_integrity_pass": True,
        "historical_statistical_contract_verified": True,
        "same_statistical_contract_except_forward_maturity_floor": True,
        "maturity_requires_outcomes_and_rebalances": due,
        "natural_forward_statistical_stage_pass": stage_pass,
        "zero_execution_authority": True,
    }
    audit: dict[str, object] = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "status": audit_status,
        "conclusion": audit_conclusion,
        "blockers": audit_blockers,
        "input_binding": binding,
        "maturity": maturity,
        "contract_comparison": contract_comparison,
        "statistical_contract": statistical_contract,
        "series_evidence": series,
        "stage": stage,
        "checks": checks,
        "evidence_scope": "NATURAL_FORWARD_PAIRED_PORTFOLIO_STATISTICS_ONLY",
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "generated_at": 150,
    }
    audit["audit_hash"] = canonical_hash(forward_statistical_audit_content(audit))
    audit.update({
        "verification_status": "PASS",
        "verification_blockers": [],
        "semantic_recomputed": True,
    })
    readiness = build_forward_performance_readiness(
        candidate=candidate,
        shadow_audit=shadow_audit,
        performance_summary=performance_summary,
        historical_statistical_audit=historical,
        forward_statistical_audit=audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    )
    if readiness["status"] != source_status:
        raise AssertionError((readiness["status"], readiness["blockers"]))
    performance = {
        "ok": True,
        "status": source_status,
        "generated_at": 200,
        "candidate_hash": candidate_hash,
        "shadow_audit": shadow_audit,
        "shadow_audit_hash": canonical_hash(shadow_audit),
        "performance": performance_summary,
        "historical_statistical_audit": historical,
        "forward_statistical_audit": audit,
        "readiness": readiness,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return candidate, observer, performance


def synthetic_single_look_stage(*, status: str):
    def build(**kwargs: object) -> dict[str, object]:
        strategy_report = dict(kwargs["strategy_report"])
        observation_count = len(strategy_report["equity_curve"])
        content: dict[str, object] = {
            "stage": str(kwargs["stage"]),
            "status": status,
            "blockers": (
                [] if status == "PASS" else ["synthetic_statistical_threshold"]
            ),
            "observation_count": observation_count,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return {**content, "stage_hash": canonical_hash(content)}

    return build


def v3_historical_audit(candidate: dict[str, object]) -> dict[str, object]:
    config = {
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": 200,
        "block_length": 5,
        "minimum_observations": 120,
        "confidence_level": 0.90,
        "required_positive_probability": 0.95,
        "required_selection_adjusted_probability": 0.90,
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": int(candidate["spec"]["trial_count"]),
    }
    binding = {
        "batch_run_hash": "1" * 64,
        "candidate_hash": candidate["candidate_hash"],
        "dataset_hash": "2" * 64,
        "spec_hash": candidate["spec_hash"],
        "validation_run_hash": "3" * 64,
        "validation_benchmark_run_hash": "4" * 64,
        "test_run_hash": "5" * 64,
        "test_benchmark_run_hash": "6" * 64,
    }
    binding["binding_hash"] = canonical_hash(binding)
    return {
        "schema_version": PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "status": "BLOCK",
        "conclusion": "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE",
        "audit_hash": "a" * 64,
        "artifact_hash": "b" * 64,
        "verification_status": "PASS",
        "verification_blockers": [],
        "semantic_recomputed": True,
        "config": config,
        "input_binding": binding,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def v3_series(
    candidate_hash: str,
    strategy_equities: list[float],
) -> dict[str, object]:
    benchmark_equities = [100.0 for _ in strategy_equities]
    ordered_hashes = [
        canonical_hash(f"settlement-{index}")
        for index in range(len(strategy_equities))
    ]
    rows: list[dict[str, object]] = []
    for index, strategy_equity in enumerate(strategy_equities):
        strategy_return = (
            0.0
            if index == 0
            else round(
                (strategy_equity / strategy_equities[index - 1] - 1.0) * 100.0,
                8,
            )
        )
        rows.append({
            "date": f"2026-08-{index + 1:02d}",
            "settlement_type": "BASELINE" if index == 0 else "DAILY_CLOSE",
            "settlement_hash": ordered_hashes[index],
            "previous_settlement_hash": (
                "" if index == 0 else ordered_hashes[index - 1]
            ),
            "strategy_equity": float(strategy_equity),
            "benchmark_equity": benchmark_equities[index],
            "strategy_daily_return_pct": strategy_return,
            "benchmark_daily_return_pct": 0.0,
            "rebalance_executed": index > 0,
        })
    content: dict[str, object] = {
        "schema_version": PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
        "candidate_hash": candidate_hash,
        "settlement_count": len(rows),
        "outcome_period_count": max(len(rows) - 1, 0),
        "rebalance_execution_count": max(len(rows) - 1, 0),
        "first_settlement_date": rows[0]["date"],
        "last_settlement_date": rows[-1]["date"],
        "first_settlement_hash": ordered_hashes[0],
        "latest_settlement_hash": ordered_hashes[-1],
        "ordered_settlement_hashes": ordered_hashes,
        "rows": rows,
        "source_validation": "FULL_SETTLEMENT_SEMANTIC_CHAIN_RECOMPUTED",
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "series_hash": canonical_hash(content)}


def v3_maturity_bundle(
    *,
    stage_status: str,
    strategy_equities: list[float],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
    candidate_hash = str(candidate["candidate_hash"])
    series = v3_series(candidate_hash, strategy_equities)
    rows = list(series["rows"])
    settlement_count = len(rows)
    outcomes = settlement_count - 1
    historical = v3_historical_audit(candidate)

    observation_chain = [
        {
            "signal_date": row["date"],
            "observation_hash": canonical_hash(f"observation-{index}"),
            "change_projection_hash": canonical_hash(f"change-{index}"),
        }
        for index, row in enumerate(rows)
    ]
    shadow = deepcopy(performance["shadow_audit"])
    for field in (
        "observation_count",
        "valid_observation_count",
        "timely_observation_count",
        "externally_attested_observation_count",
        "activation_verified_observation_count",
        "forward_state_verified_observation_count",
        "risk_pass_observation_count",
        "observation_chain_count",
    ):
        shadow[field] = settlement_count
    shadow["planned_rebalance_count"] = outcomes
    shadow["first_signal_date"] = rows[0]["date"]
    shadow["last_signal_date"] = rows[-1]["date"]
    shadow["observation_chain"] = observation_chain
    shadow["observation_chain_hash"] = canonical_hash(observation_chain)
    shadow["latest_observation_hash"] = observation_chain[-1]["observation_hash"]

    observer_payload = deepcopy(observer)
    observer_payload["ledger"]["forward_audit"] = shadow
    observer_payload["readiness"]["ledger_audit"] = shadow
    observer = seal_forward_status_artifact(observer_payload)

    performance_summary = deepcopy(performance["performance"])
    peak = float(strategy_equities[0])
    max_drawdown = 0.0
    for equity in strategy_equities:
        peak = max(peak, float(equity))
        max_drawdown = max(max_drawdown, (1.0 - float(equity) / peak) * 100.0)
    performance_summary.update({
        "settlement_count": settlement_count,
        "outcome_period_count": outcomes,
        "rebalance_execution_count": outcomes,
        "first_settlement_date": rows[0]["date"],
        "last_settlement_date": rows[-1]["date"],
        "latest_settlement_hash": rows[-1]["settlement_hash"],
        "strategy": {"max_drawdown_pct": round(max_drawdown, 8)},
        "cumulative_excess_return_pct": round(
            (float(strategy_equities[-1]) / float(strategy_equities[0]) - 1.0)
            * 100.0,
            8,
        ),
    })

    required_outcomes = int(candidate["spec"]["minimum_forward_performance_outcomes"])
    prefix_rows = [dict(item) for item in rows[: required_outcomes + 1]]
    prefix_series = v3_series(
        candidate_hash,
        [float(item["strategy_equity"]) for item in prefix_rows],
    )

    def series_from_length(*, settlements: list[dict[str, object]], **_kwargs: object):
        return (
            (deepcopy(series), [])
            if len(settlements) == settlement_count
            else (deepcopy(prefix_series), [])
        )

    stage_builder = synthetic_single_look_stage(status=stage_status)
    with patch(
        "exchange_terminal.services.portfolio_forward_statistical_audit."
        "_forward_series_evidence",
        side_effect=series_from_length,
    ), patch(
        "exchange_terminal.services.portfolio_forward_statistical_audit."
        "audit_paired_equity_curve_stage",
        side_effect=stage_builder,
    ):
        report = audit_forward_portfolio_statistics_v2(
            candidate=candidate,
            settlements=[{} for _ in rows],
            historical_statistical_audit=historical,
            generated_at=150,
        )
    audit = {
        **report,
        "verification_status": "PASS",
        "verification_blockers": [],
        "semantic_recomputed": True,
    }
    readiness = build_forward_performance_readiness(
        candidate=candidate,
        shadow_audit=shadow,
        performance_summary=performance_summary,
        historical_statistical_audit=historical,
        forward_statistical_audit=audit,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    )
    performance.update({
        "status": readiness["status"],
        "shadow_audit": shadow,
        "shadow_audit_hash": canonical_hash(shadow),
        "performance": performance_summary,
        "historical_statistical_audit": historical,
        "forward_statistical_audit": audit,
        "readiness": readiness,
    })
    return candidate, observer, performance


def local_source_receipts(
    candidate: dict[str, object],
    observer: dict[str, object],
    performance: dict[str, object],
    *,
    anchor_count: int | None = None,
    backup_generated_at: int = 250,
    watchdog_generated_at: int = 260,
    observer_hash_drift: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    candidate_hash = str(candidate["candidate_hash"])
    observation_chain = deepcopy(
        performance["shadow_audit"]["observation_chain"]
    )
    settlement_rows = deepcopy(
        performance["forward_statistical_audit"]["series_evidence"]["rows"]
    )
    count = len(observation_chain) if anchor_count is None else anchor_count
    observation_chain = observation_chain[:count]
    settlement_rows = settlement_rows[:count]
    if observer_hash_drift:
        observation_chain[-1]["observation_hash"] = canonical_hash(
            "different-archived-observation"
        )
    manifest_hash = "c" * 64
    anchor = build_portfolio_forward_local_source_anchor(
        candidate_hash=candidate_hash,
        archive_manifest_hash=manifest_hash,
        archive_generated_at=backup_generated_at,
        observer_projection=observation_chain,
        settlement_projection=settlement_rows,
        shadow_database_sha256="d" * 64,
        performance_database_sha256="e" * 64,
    )
    archive_verification = {
        "status": "PASS",
        "blockers": [],
        "candidate_hash": candidate_hash,
        "manifest_hash": manifest_hash,
        "local_source_anchor": anchor,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    backup = build_portfolio_backup_status(
        generated_at=backup_generated_at,
        result={
            "status": "ARCHIVED",
            "candidate_hash": candidate_hash,
            "bundle_path": "C:/synthetic/local-archive",
            "manifest_hash": manifest_hash,
            "pack_hash": "f" * 64,
            "verification": archive_verification,
        },
    )
    backup_verification = verify_portfolio_backup_status(backup)
    if backup_verification["status"] != "PASS":
        raise AssertionError(backup_verification)
    watchdog = build_portfolio_forward_watchdog_status(
        now_ms=watchdog_generated_at,
        active={"status": "PASS", "candidate": candidate, "registry": {}},
        scheduler={
            "health": "PASS",
            "candidate_hash": candidate_hash,
            "scheduled_invocation": True,
            "status_age_ms": 0,
            "status": "PASS",
        },
        observation=observer,
        performance=performance,
        backup=backup,
        backup_verification=backup_verification,
        backup_archive_verification=archive_verification,
        task_probe={"status": "BLOCK", "tasks": {}},
    )
    return backup, watchdog


class PortfolioForwardStatisticalMaturityTests(unittest.TestCase):
    def project(self, source_status: str) -> dict[str, object]:
        candidate, observer, performance = maturity_bundle(source_status)
        return build_portfolio_forward_statistical_maturity(
            active_candidate=candidate,
            observer_status=observer,
            performance_status=performance,
            observed_now_ms=300,
            maturity_schema_version=(
                PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION
            ),
        )

    def project_v3(
        self,
        candidate: dict[str, object],
        observer: dict[str, object],
        performance: dict[str, object],
        *,
        stage_status: str,
    ) -> dict[str, object]:
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_maturity."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_single_look_stage(status=stage_status),
        ):
            return build_portfolio_forward_statistical_maturity(
                active_candidate=candidate,
                observer_status=observer,
                performance_status=performance,
                observed_now_ms=300,
                maturity_schema_version=(
                    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION
                ),
            )

    def test_v3_freezes_first_block_and_first_pass_across_full_tail(self) -> None:
        cases = (
            (
                "BLOCK",
                [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 120.0, 140.0],
                "STOP_RESEARCH",
                "BLOCK",
            ),
            (
                "PASS",
                [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 70.0, 50.0],
                "REVIEW_REQUIRED",
                "PASS",
            ),
        )
        for stage_status, equities, expected_status, expected_decision in cases:
            with self.subTest(stage_status=stage_status):
                candidate, observer, performance = v3_maturity_bundle(
                    stage_status=stage_status,
                    strategy_equities=equities,
                )
                projection = self.project_v3(
                    candidate,
                    observer,
                    performance,
                    stage_status=stage_status,
                )

                audit = performance["forward_statistical_audit"]
                decision = audit["decision_window"]
                self.assertEqual(
                    projection["schema_version"],
                    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
                )
                self.assertEqual(projection["status"], expected_status)
                self.assertEqual(projection["decision_status"], expected_decision)
                self.assertEqual(
                    projection["research_action"],
                    decision["research_action"],
                )
                self.assertEqual(
                    projection["decision_hash"],
                    decision["decision_hash"],
                )
                self.assertEqual(
                    projection["first_due_settlement_hash"],
                    decision["first_joint_maturity_prefix"][
                        "first_due_settlement_hash"
                    ],
                )
                self.assertEqual(
                    audit["stage"]["observation_count"],
                    DEFAULT_BLOCK_LENGTH,
                )
                self.assertEqual(projection["progress"]["forward_outcomes"], 7)
                self.assertFalse(authority_violations(projection))

    def test_v3_prefix_risk_is_frozen_and_missing_or_mixed_risk_blocks(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
                70.0,
                50.0,
            ],
        )
        projection = self.project_v3(
            candidate,
            observer,
            performance,
            stage_status="PASS",
        )
        risk = performance["forward_statistical_audit"]["decision_window"][
            "risk_acceptance"
        ]
        self.assertEqual(risk["status"], "PASS")
        self.assertEqual(projection["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            projection["risk_acceptance_hash"],
            risk["risk_hash"],
        )

        risk_candidate, risk_observer, risk_performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 95.0, 90.0, 85.0, 80.0, 80.0, 120.0],
        )
        risk_projection = self.project_v3(
            risk_candidate,
            risk_observer,
            risk_performance,
            stage_status="PASS",
        )
        self.assertEqual(
            risk_performance["forward_statistical_audit"]["decision_window"][
                "risk_acceptance"
            ]["status"],
            "BLOCK",
        )
        self.assertEqual(risk_projection["status"], "STOP_RESEARCH")

        missing = deepcopy(performance)
        missing["forward_statistical_audit"]["decision_window"].pop(
            "risk_acceptance"
        )
        missing_projection = self.project_v3(
            candidate,
            observer,
            missing,
            stage_status="PASS",
        )
        self.assertEqual(missing_projection["status"], "BLOCK")
        self.assertEqual(missing_projection["decision_hash"], "")

        mixed = deepcopy(performance)
        mixed["forward_statistical_audit"]["schema_version"] = (
            PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION
        )
        mixed_projection = self.project_v3(
            candidate,
            observer,
            mixed,
            stage_status="PASS",
        )
        self.assertEqual(mixed_projection["status"], "BLOCK")

    def test_v3_full_tail_integrity_and_version_routes_fail_closed(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        )
        tampered = deepcopy(performance)
        tampered["forward_statistical_audit"]["series_evidence"]["rows"][-1][
            "strategy_equity"
        ] = 999.0
        projection = self.project_v3(
            candidate,
            observer,
            tampered,
            stage_status="PASS",
        )
        self.assertEqual(projection["status"], "BLOCK")

        unknown = build_portfolio_forward_statistical_maturity(
            active_candidate=candidate,
            observer_status=observer,
            performance_status=performance,
            observed_now_ms=300,
            maturity_schema_version="portfolio-forward-statistical-maturity-v999",
        )
        self.assertEqual(unknown["status"], "BLOCK")
        self.assertEqual(
            unknown["schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        )

        current = build_portfolio_forward_statistical_maturity(
            active_candidate=candidate,
            observer_status=observer,
            performance_status=performance,
            observed_now_ms=300,
        )
        self.assertEqual(
            current["schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_SCHEMA_VERSION,
        )
        self.assertEqual(current["status"], "BLOCK")

    def test_v3_not_due_rebuilds_hashed_risk_without_a_stage(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 101.0],
        )
        projection = self.project_v3(
            candidate,
            observer,
            performance,
            stage_status="PASS",
        )
        decision = performance["forward_statistical_audit"]["decision_window"]
        self.assertEqual(projection["status"], "NOT_DUE")
        self.assertEqual(projection["decision_status"], "NOT_DUE")
        self.assertEqual(projection["research_action"], "COLLECT_MORE")
        self.assertEqual(projection["stage_hash"], "")
        self.assertEqual(
            projection["risk_acceptance_hash"],
            decision["risk_acceptance"]["risk_hash"],
        )
        self.assertEqual(decision["risk_acceptance"]["status"], "NOT_DUE")
        self.assertEqual(projection["first_due_settlement_hash"], "")

    def test_v3_recursive_input_fails_closed(self) -> None:
        recursive: dict[str, object] = {}
        recursive["spec"] = recursive
        projection = build_portfolio_forward_statistical_maturity(
            active_candidate=recursive,
            observer_status={},
            performance_status={},
            observed_now_ms=300,
            maturity_schema_version=(
                PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION
            ),
        )
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(projection["decision_hash"], "")

    def test_v3_unsafe_historical_integer_blocks_before_bootstrap(self) -> None:
        candidate, observer, performance = v3_maturity_bundle(
            stage_status="PASS",
            strategy_equities=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        )
        performance["historical_statistical_audit"]["config"][
            "resample_count"
        ] = 9_007_199_254_740_992

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_maturity."
            "audit_paired_equity_curve_stage"
        ) as stage_builder:
            projection = build_portfolio_forward_statistical_maturity(
                active_candidate=candidate,
                observer_status=observer,
                performance_status=performance,
                observed_now_ms=300,
                maturity_schema_version=(
                    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION
                ),
            )

        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(projection["decision_hash"], "")
        stage_builder.assert_not_called()

    def test_v3_bootstrap_budget_blocks_before_stage(self) -> None:
        for field, value in (
            ("resample_count", 50_001),
            ("block_length", DEFAULT_BLOCK_LENGTH + 1),
        ):
            with self.subTest(field=field):
                candidate, observer, performance = v3_maturity_bundle(
                    stage_status="PASS",
                    strategy_equities=[
                        100.0,
                        101.0,
                        102.0,
                        103.0,
                        104.0,
                        105.0,
                        106.0,
                    ],
                )
                performance["historical_statistical_audit"]["config"][field] = value

                with patch(
                    "exchange_terminal.services.portfolio_forward_statistical_maturity."
                    "audit_paired_equity_curve_stage"
                ) as stage_builder:
                    projection = build_portfolio_forward_statistical_maturity(
                        active_candidate=candidate,
                        observer_status=observer,
                        performance_status=performance,
                        observed_now_ms=300,
                        maturity_schema_version=(
                            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION
                        ),
                    )

                self.assertEqual(projection["status"], "BLOCK")
                self.assertEqual(projection["decision_hash"], "")
                stage_builder.assert_not_called()

    def test_projects_the_four_strict_public_states(self) -> None:
        expected = {
            "COLLECTING": "NOT_DUE",
            "RESEARCH_REVIEW_READY": "REVIEW_REQUIRED",
            "RESEARCH_REVIEW_BLOCKED": "STOP_RESEARCH",
        }
        for source_status, public_status in expected.items():
            with self.subTest(source_status=source_status):
                projection = self.project(source_status)
                self.assertEqual(
                    projection["schema_version"],
                    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
                )
                self.assertEqual(projection["status"], public_status)
                self.assertFalse(authority_violations(projection))

        candidate, observer, _performance = maturity_bundle("COLLECTING")
        blocked = build_portfolio_forward_statistical_maturity(
            active_candidate=candidate,
            observer_status=observer,
            performance_status=None,
            observed_now_ms=300,
        )
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertEqual(set(blocked["progress"]), {
            "forward_outcomes",
            "required_forward_outcomes",
            "remaining_forward_outcomes",
            "settlements",
            "captured_observations",
            "executed_rebalances",
            "required_executed_rebalances",
            "remaining_executed_rebalances",
        })
        self.assertTrue(all(value == 0 for value in blocked["progress"].values()))

    def test_verified_local_archive_binding_projects_full_and_prefix_without_operational_promotion(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
        expected_source_fields = {
            "schema_version",
            "status",
            "trust_scope",
            "current_observation_count",
            "anchored_observation_count",
            "current_settlement_count",
            "anchored_settlement_count",
            "external_authenticity_proven",
            "profitability_proven",
            "research_only",
            "observation_only",
            "simulation_only",
            "paper_authorized",
            "live_order_allowed",
        }
        self.assertEqual(
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V1_SCHEMA_VERSION,
            "portfolio-forward-statistical-maturity-v1",
        )
        for anchor_count, expected_status in (
            (DEFAULT_BLOCK_LENGTH + 1, "FULL"),
            (DEFAULT_BLOCK_LENGTH, "PREFIX"),
        ):
            with self.subTest(expected_status=expected_status):
                backup, watchdog = local_source_receipts(
                    candidate,
                    observer,
                    performance,
                    anchor_count=anchor_count,
                )
                self.assertEqual(watchdog["status"], "BLOCK")
                projection = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=observer,
                    performance_status=performance,
                    backup_status=backup,
                    watchdog_status=watchdog,
                    backup_read_status="READABLE",
                    watchdog_read_status="READABLE",
                    observed_now_ms=300,
                    maturity_schema_version=(
                        PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION
                    ),
                )
                source = projection["source_binding"]
                self.assertEqual(projection["status"], "REVIEW_REQUIRED")
                self.assertEqual(source["schema_version"], PORTFOLIO_FORWARD_SOURCE_BINDING_SCHEMA_VERSION)
                self.assertEqual(source["status"], expected_status)
                self.assertEqual(set(source), expected_source_fields)
                self.assertEqual(source["anchored_observation_count"], anchor_count)
                self.assertEqual(source["anchored_settlement_count"], anchor_count)
                serialized = json.dumps(source, ensure_ascii=True, sort_keys=True)
                for forbidden in ("hash", "path", "reason"):
                    self.assertNotIn(forbidden, serialized)
                self.assertIs(source["external_authenticity_proven"], False)
                self.assertIs(source["profitability_proven"], False)
                self.assertIs(source["paper_authorized"], False)
                self.assertIs(source["live_order_allowed"], False)

    def test_local_archive_binding_contradictions_block_and_zero_progress(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
        valid_backup, valid_watchdog = local_source_receipts(
            candidate,
            observer,
            performance,
        )
        _other_backup, mismatched_watchdog = local_source_receipts(
            candidate,
            observer,
            performance,
            observer_hash_drift=True,
        )
        drift_backup, drift_watchdog = local_source_receipts(
            candidate,
            observer,
            performance,
            observer_hash_drift=True,
        )
        short_candidate, short_observer, short_performance = maturity_bundle("COLLECTING")
        cases = (
            (
                "projection_hash_drift",
                candidate,
                observer,
                performance,
                drift_backup,
                drift_watchdog,
                "READABLE",
                "READABLE",
            ),
            (
                "current_shorter_than_anchor",
                short_candidate,
                short_observer,
                short_performance,
                valid_backup,
                valid_watchdog,
                "READABLE",
                "READABLE",
            ),
            (
                "one_new_one_missing",
                candidate,
                observer,
                performance,
                valid_backup,
                {},
                "READABLE",
                "MISSING",
            ),
            (
                "new_malformed",
                candidate,
                observer,
                performance,
                {"schema_version": "portfolio-forward-backup-status-v2"},
                valid_watchdog,
                "READABLE",
                "READABLE",
            ),
            (
                "receipt_mismatch",
                candidate,
                observer,
                performance,
                valid_backup,
                mismatched_watchdog,
                "READABLE",
                "READABLE",
            ),
        )
        for (
            label,
            active,
            raw_observer,
            raw_performance,
            backup,
            watchdog,
            backup_read,
            watchdog_read,
        ) in cases:
            with self.subTest(label=label):
                result = build_portfolio_forward_statistical_maturity(
                    active_candidate=active,
                    observer_status=raw_observer,
                    performance_status=raw_performance,
                    backup_status=backup,
                    watchdog_status=watchdog,
                    backup_read_status=backup_read,
                    watchdog_read_status=watchdog_read,
                    observed_now_ms=300,
                    maturity_schema_version=(
                        PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION
                    ),
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["source_binding"]["status"], "CONTRADICTION")
                self.assertTrue(all(value == 0 for value in result["progress"].values()))

    def test_missing_legacy_and_stale_receipts_are_not_available_without_promotion(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
        backup, watchdog = local_source_receipts(candidate, observer, performance)
        cases = (
            ("both_missing", {}, {}, "MISSING", "MISSING", 300),
            (
                "explicit_legacy",
                {"schema_version": "portfolio-forward-backup-status-v1"},
                {"schema_version": "portfolio-forward-watchdog-v2"},
                "READABLE",
                "READABLE",
                300,
            ),
            ("equal_but_stale", backup, watchdog, "READABLE", "READABLE", 2_800_261),
        )
        for label, raw_backup, raw_watchdog, backup_read, watchdog_read, now_ms in cases:
            with self.subTest(label=label):
                result = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=observer,
                    performance_status=performance,
                    backup_status=raw_backup,
                    watchdog_status=raw_watchdog,
                    backup_read_status=backup_read,
                    watchdog_read_status=watchdog_read,
                    observed_now_ms=now_ms,
                    maturity_schema_version=(
                        PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION
                    ),
                )
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["source_binding"]["status"], "NOT_AVAILABLE")

    def test_future_and_invalid_receipt_order_are_contradictions(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
        future_backup, future_watchdog = local_source_receipts(
            candidate,
            observer,
            performance,
            backup_generated_at=20_000,
            watchdog_generated_at=21_000,
        )
        ordered_backup, out_of_order_watchdog = local_source_receipts(
            candidate,
            observer,
            performance,
            backup_generated_at=20_000,
            watchdog_generated_at=19_000,
        )
        for label, backup, watchdog, now_ms in (
            ("future", future_backup, future_watchdog, 300),
            ("invalid_order", ordered_backup, out_of_order_watchdog, 30_000),
        ):
            with self.subTest(label=label):
                result = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=observer,
                    performance_status=performance,
                    backup_status=backup,
                    watchdog_status=watchdog,
                    backup_read_status="READABLE",
                    watchdog_read_status="READABLE",
                    observed_now_ms=now_ms,
                    maturity_schema_version=(
                        PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION
                    ),
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["source_binding"]["status"], "CONTRADICTION")

    def test_identity_hash_ledger_time_and_authority_drift_fail_closed(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")
        cases: list[tuple[str, dict[str, object], dict[str, object], dict[str, object], int]] = []

        wrong_candidate = deepcopy(performance)
        wrong_candidate["candidate_hash"] = "f" * 64
        cases.append(("candidate", candidate, observer, wrong_candidate, 300))

        wrong_ledger = deepcopy(observer)
        wrong_ledger["ledger"]["forward_audit"]["valid_observation_count"] += 1
        wrong_ledger = seal_forward_status_artifact(wrong_ledger)
        cases.append(("ledger", candidate, wrong_ledger, performance, 300))

        older_performance = deepcopy(performance)
        older_performance["generated_at"] = 99
        cases.append(("time", candidate, observer, older_performance, 300))

        audit_hash_drift = deepcopy(performance)
        audit_hash_drift["forward_statistical_audit"]["conclusion"] = "FORGED"
        cases.append(("audit_hash", candidate, observer, audit_hash_drift, 300))

        binding_hash_drift = deepcopy(performance)
        binding_hash_drift["forward_statistical_audit"]["input_binding"][
            "outcome_period_count"
        ] += 1
        cases.append(("binding_hash", candidate, observer, binding_hash_drift, 300))

        authority_alias = deepcopy(performance)
        authority_alias["nested"] = {"ｃａｎ－ｔｒａｄｅ": "false"}
        cases.append(("authority", candidate, observer, authority_alias, 300))

        for label, active, raw_observer, raw_performance, now in cases:
            with self.subTest(label=label):
                result = build_portfolio_forward_statistical_maturity(
                    active_candidate=active,
                    observer_status=raw_observer,
                    performance_status=raw_performance,
                    observed_now_ms=now,
                )
                self.assertEqual(result["status"], "BLOCK")

    def test_coherent_reseal_and_missing_receipts_do_not_bypass_bindings(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")

        resealed = deepcopy(performance)
        audit = resealed["forward_statistical_audit"]
        audit["input_binding"]["candidate_hash"] = "e" * 64
        binding_content = dict(audit["input_binding"])
        binding_content.pop("binding_hash", None)
        audit["input_binding"]["binding_hash"] = canonical_hash(binding_content)
        audit["audit_hash"] = canonical_hash(forward_statistical_audit_content(audit))

        missing_receipt = deepcopy(performance)
        del missing_receipt["forward_statistical_audit"]["semantic_recomputed"]

        missing_historical_receipt = deepcopy(performance)
        del missing_historical_receipt["historical_statistical_audit"]["semantic_recomputed"]

        missing_performance_scope = deepcopy(performance)
        del missing_performance_scope["simulation_only"]

        missing_audit_scope = deepcopy(performance)
        del missing_audit_scope["forward_statistical_audit"]["evidence_scope"]
        missing_audit_scope["forward_statistical_audit"]["audit_hash"] = canonical_hash(
            forward_statistical_audit_content(
                missing_audit_scope["forward_statistical_audit"]
            )
        )

        malformed_series = deepcopy(performance)
        malformed_audit = malformed_series["forward_statistical_audit"]
        malformed_audit["series_evidence"]["ordered_settlement_hashes"] = "not-a-list"
        series_content = dict(malformed_audit["series_evidence"])
        series_content.pop("series_hash", None)
        malformed_audit["series_evidence"]["series_hash"] = canonical_hash(series_content)
        malformed_audit["input_binding"]["forward_series_hash"] = malformed_audit[
            "series_evidence"
        ]["series_hash"]
        malformed_audit["input_binding"]["ordered_settlement_hashes_hash"] = canonical_hash(
            "not-a-list"
        )
        binding_content = dict(malformed_audit["input_binding"])
        binding_content.pop("binding_hash", None)
        malformed_audit["input_binding"]["binding_hash"] = canonical_hash(binding_content)
        malformed_audit["audit_hash"] = canonical_hash(
            forward_statistical_audit_content(malformed_audit)
        )

        for label, forged in (
            ("coherent_reseal", resealed),
            ("missing_forward_receipt", missing_receipt),
            ("missing_historical_receipt", missing_historical_receipt),
            ("missing_performance_scope", missing_performance_scope),
            ("missing_audit_scope", missing_audit_scope),
            ("malformed_series", malformed_series),
        ):
            with self.subTest(label=label):
                result = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=observer,
                    performance_status=forged,
                    observed_now_ms=300,
                )
                self.assertEqual(result["status"], "BLOCK")

    def test_series_recomputation_rejects_bidirectional_decision_reseals(self) -> None:
        candidate, observer, blocked_performance = maturity_bundle(
            "RESEARCH_REVIEW_BLOCKED"
        )
        _candidate, _observer, ready_performance = maturity_bundle(
            "RESEARCH_REVIEW_READY"
        )

        def rebuild_declared_readiness(performance: dict[str, object]) -> None:
            readiness = build_forward_performance_readiness(
                candidate=candidate,
                shadow_audit=performance["shadow_audit"],
                performance_summary=performance["performance"],
                historical_statistical_audit=performance[
                    "historical_statistical_audit"
                ],
                forward_statistical_audit=performance[
                    "forward_statistical_audit"
                ],
                readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
            )
            performance["readiness"] = readiness
            performance["status"] = readiness["status"]

        blocked_to_pass = deepcopy(blocked_performance)
        blocked_summary = blocked_to_pass["performance"]
        blocked_summary["cumulative_excess_return_pct"] = 999.0
        blocked_audit = blocked_to_pass["forward_statistical_audit"]
        blocked_audit["status"] = "PASS"
        blocked_audit["conclusion"] = "FORWARD_STATISTICAL_CONTRACT_PASS"
        blocked_audit["blockers"] = []
        blocked_audit["stage"] = deepcopy(
            ready_performance["forward_statistical_audit"]["stage"]
        )
        blocked_audit["checks"]["natural_forward_statistical_stage_pass"] = True
        blocked_audit["audit_hash"] = canonical_hash(
            forward_statistical_audit_content(blocked_audit)
        )
        rebuild_declared_readiness(blocked_to_pass)
        self.assertEqual(
            blocked_to_pass["readiness"]["status"],
            "RESEARCH_REVIEW_READY",
        )

        ready_to_block = deepcopy(ready_performance)
        ready_summary = ready_to_block["performance"]
        ready_summary["cumulative_excess_return_pct"] = -999.0
        ready_audit = ready_to_block["forward_statistical_audit"]
        ready_audit["status"] = "BLOCK"
        ready_audit["conclusion"] = "FORWARD_STATISTICAL_CONTRACT_FAILED"
        ready_audit["blockers"] = ["natural_forward:forged_failure"]
        ready_audit["stage"] = deepcopy(
            blocked_performance["forward_statistical_audit"]["stage"]
        )
        ready_audit["checks"]["natural_forward_statistical_stage_pass"] = False
        ready_audit["audit_hash"] = canonical_hash(
            forward_statistical_audit_content(ready_audit)
        )
        rebuild_declared_readiness(ready_to_block)
        self.assertEqual(
            ready_to_block["readiness"]["status"],
            "RESEARCH_REVIEW_BLOCKED",
        )

        for label, forged in (
            ("blocked_to_pass_999", blocked_to_pass),
            ("ready_to_block_negative", ready_to_block),
        ):
            with self.subTest(label=label):
                projection = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=observer,
                    performance_status=forged,
                    observed_now_ms=300,
                )
                self.assertEqual(projection["status"], "BLOCK")

    def test_resealed_series_contract_summary_and_capture_attacks_fail_closed(self) -> None:
        candidate, observer, performance = maturity_bundle("RESEARCH_REVIEW_READY")

        def reseal_audit(performance_payload: dict[str, object]) -> None:
            audit = performance_payload["forward_statistical_audit"]
            series = audit["series_evidence"]
            series_content = dict(series)
            series_content.pop("series_hash", None)
            series["series_hash"] = canonical_hash(series_content)
            contract = audit["statistical_contract"]
            contract_content = dict(contract)
            contract_content.pop("contract_hash", None)
            contract["contract_hash"] = canonical_hash(contract_content)
            binding = audit["input_binding"]
            binding["forward_series_hash"] = series["series_hash"]
            binding["ordered_settlement_hashes_hash"] = canonical_hash(
                series["ordered_settlement_hashes"]
            )
            binding["statistical_contract_hash"] = contract["contract_hash"]
            binding_content = dict(binding)
            binding_content.pop("binding_hash", None)
            binding["binding_hash"] = canonical_hash(binding_content)
            audit["audit_hash"] = canonical_hash(
                forward_statistical_audit_content(audit)
            )
            readiness = build_forward_performance_readiness(
                candidate=candidate,
                shadow_audit=performance_payload["shadow_audit"],
                performance_summary=performance_payload["performance"],
                historical_statistical_audit=performance_payload[
                    "historical_statistical_audit"
                ],
                forward_statistical_audit=audit,
                readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
            )
            performance_payload["readiness"] = readiness
            performance_payload["status"] = readiness["status"]

        wrong_return = deepcopy(performance)
        wrong_return["forward_statistical_audit"]["series_evidence"]["rows"][1][
            "strategy_daily_return_pct"
        ] = 77.0
        reseal_audit(wrong_return)

        wrong_chain = deepcopy(performance)
        wrong_chain["forward_statistical_audit"]["series_evidence"]["rows"][1][
            "previous_settlement_hash"
        ] = "f" * 64
        reseal_audit(wrong_chain)

        baseline_rebalance_swap = deepcopy(performance)
        swapped_rows = baseline_rebalance_swap["forward_statistical_audit"][
            "series_evidence"
        ]["rows"]
        swapped_rows[0]["rebalance_executed"] = True
        swapped_rows[1]["rebalance_executed"] = False
        reseal_audit(baseline_rebalance_swap)

        forged_drawdown = deepcopy(performance)
        forged_drawdown["performance"]["strategy"]["max_drawdown_pct"] = 9.0
        reseal_audit(forged_drawdown)

        summary_failures = deepcopy(performance)
        summary_failures["performance"]["integrity_violations"] = [
            "declared_chain_break"
        ]
        summary_failures["performance"]["unexpected_settlement_dates"] = [
            "2026-08-31"
        ]
        summary_failures["performance"]["observation_hash_mismatch_dates"] = [
            "2026-08-30"
        ]
        reseal_audit(summary_failures)

        summary_scope = deepcopy(performance)
        summary_scope["performance"]["observation_only"] = False
        summary_scope["performance"]["simulation_only"] = False
        reseal_audit(summary_scope)

        captured_performance = deepcopy(performance)
        captured_shadow = captured_performance["shadow_audit"]
        captured_shadow["valid_observation_count"] += 1
        captured_performance["shadow_audit_hash"] = canonical_hash(captured_shadow)
        captured_observer = seal_forward_status_artifact({
            "status": "OBSERVED",
            "generated_at": 100,
            "candidate_hash": candidate["candidate_hash"],
            "ledger": {"forward_audit": deepcopy(captured_shadow)},
            "readiness": {"ledger_audit": deepcopy(captured_shadow)},
        })
        reseal_audit(captured_performance)

        shadow_authority = deepcopy(performance)
        authority_shadow = shadow_authority["shadow_audit"]
        authority_shadow["execution_authority_violation_count"] = 1
        shadow_authority["shadow_audit_hash"] = canonical_hash(authority_shadow)
        authority_observer = seal_forward_status_artifact({
            "status": "OBSERVED",
            "generated_at": 100,
            "candidate_hash": candidate["candidate_hash"],
            "ledger": {"forward_audit": deepcopy(authority_shadow)},
            "readiness": {"ledger_audit": deepcopy(authority_shadow)},
        })
        reseal_audit(shadow_authority)

        shadow_integrity = deepcopy(performance)
        integrity_shadow = shadow_integrity["shadow_audit"]
        integrity_shadow["integrity_violations"] = ["declared_chain_break"]
        integrity_shadow["capture_violation_count"] = 1
        shadow_integrity["shadow_audit_hash"] = canonical_hash(integrity_shadow)
        integrity_observer = seal_forward_status_artifact({
            "status": "OBSERVED",
            "generated_at": 100,
            "candidate_hash": candidate["candidate_hash"],
            "ledger": {"forward_audit": deepcopy(integrity_shadow)},
            "readiness": {"ledger_audit": deepcopy(integrity_shadow)},
        })
        reseal_audit(shadow_integrity)

        shadow_date_drift = deepcopy(performance)
        date_shadow = shadow_date_drift["shadow_audit"]
        for index, chain_item in enumerate(date_shadow["observation_chain"]):
            chain_item["signal_date"] = f"2026-07-{index + 1:02d}"
        date_shadow["first_signal_date"] = date_shadow["observation_chain"][0][
            "signal_date"
        ]
        date_shadow["last_signal_date"] = date_shadow["observation_chain"][-1][
            "signal_date"
        ]
        date_shadow["observation_chain_hash"] = canonical_hash(
            date_shadow["observation_chain"]
        )
        shadow_date_drift["shadow_audit_hash"] = canonical_hash(date_shadow)
        date_observer = seal_forward_status_artifact({
            "status": "OBSERVED",
            "generated_at": 100,
            "candidate_hash": candidate["candidate_hash"],
            "ledger": {"forward_audit": deepcopy(date_shadow)},
            "readiness": {"ledger_audit": deepcopy(date_shadow)},
        })
        reseal_audit(shadow_date_drift)

        shadow_latest_hash = deepcopy(performance)
        latest_shadow = shadow_latest_hash["shadow_audit"]
        latest_shadow["latest_observation_hash"] = canonical_hash(
            "different-latest-observation"
        )
        shadow_latest_hash["shadow_audit_hash"] = canonical_hash(latest_shadow)
        latest_observer = seal_forward_status_artifact({
            "status": "OBSERVED",
            "generated_at": 100,
            "candidate_hash": candidate["candidate_hash"],
            "ledger": {"forward_audit": deepcopy(latest_shadow)},
            "readiness": {"ledger_audit": deepcopy(latest_shadow)},
        })
        reseal_audit(shadow_latest_hash)

        cases = (
            ("row_return", observer, wrong_return),
            ("row_chain", observer, wrong_chain),
            ("baseline_rebalance_swap", observer, baseline_rebalance_swap),
            ("summary_drawdown", observer, forged_drawdown),
            ("summary_failures", observer, summary_failures),
            ("summary_scope", observer, summary_scope),
            ("captured_count", captured_observer, captured_performance),
            ("shadow_authority", authority_observer, shadow_authority),
            ("shadow_integrity", integrity_observer, shadow_integrity),
            ("shadow_series_date_drift", date_observer, shadow_date_drift),
            ("shadow_latest_hash_drift", latest_observer, shadow_latest_hash),
        )
        for label, raw_observer, forged in cases:
            with self.subTest(label=label):
                projection = build_portfolio_forward_statistical_maturity(
                    active_candidate=candidate,
                    observer_status=raw_observer,
                    performance_status=forged,
                    observed_now_ms=300,
                )
                self.assertEqual(projection["status"], "BLOCK")

        oversized_contract = deepcopy(performance)
        contract = oversized_contract["forward_statistical_audit"][
            "statistical_contract"
        ]
        contract["resample_count"] = 10**9
        contract["source_historical_config_hash"] = "d" * 64
        comparison = oversized_contract["forward_statistical_audit"][
            "contract_comparison"
        ]
        comparison["copied_fields"]["resample_count"] = {
            "historical": 10**9,
            "forward": 10**9,
            "matches": True,
        }
        oversized_contract["forward_statistical_audit"]["input_binding"][
            "historical_statistical_config_hash"
        ] = "d" * 64
        reseal_audit(oversized_contract)
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_maturity."
            "audit_paired_equity_curve_stage"
        ) as stage_recompute:
            projection = build_portfolio_forward_statistical_maturity(
                active_candidate=candidate,
                observer_status=observer,
                performance_status=oversized_contract,
                observed_now_ms=300,
            )
        stage_recompute.assert_not_called()
        self.assertEqual(projection["status"], "BLOCK")

    def test_public_projection_never_exposes_returns_blockers_or_paths(self) -> None:
        projection = self.project("RESEARCH_REVIEW_BLOCKED")
        serialized = json.dumps(projection, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            "cumulative_excess_return_pct",
            "max_drawdown_pct",
            "blockers",
            "ledger_path",
            "shadow_ledger_path",
            "status_artifact",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(
            projection["verification_scope"],
            "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY",
        )


if __name__ == "__main__":
    unittest.main()
