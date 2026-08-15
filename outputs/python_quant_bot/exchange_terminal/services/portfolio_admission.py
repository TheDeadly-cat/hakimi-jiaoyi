from __future__ import annotations

import hashlib
import json
from typing import Any

from .portfolio_experiment import verify_experiment_binding
from .portfolio_universe import (
    PORTFOLIO_UNIVERSE_CONTRACT_VERSION,
    build_static_research_universe_contract,
    verify_universe_contract,
)
from .provider_governance import verify_provider_governance_contract


PORTFOLIO_ADMISSION_SCHEMA_VERSION = "portfolio-backtest-admission-v3"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_research_universe_contract(
    *,
    benchmark_symbol: str,
    tradable_symbols: list[str],
    declared_at: str,
    selection_basis: str,
) -> dict[str, Any]:
    return build_static_research_universe_contract(
        benchmark_symbol=benchmark_symbol,
        tradable_symbols=tradable_symbols,
        declared_at=declared_at,
        selection_basis=selection_basis,
    )


def build_internal_backtest_admission(report: dict[str, Any]) -> dict[str, Any]:
    manifest = report.get("dataset_manifest") if isinstance(report.get("dataset_manifest"), dict) else {}
    development = report.get("development_checks") if isinstance(report.get("development_checks"), dict) else {}
    exposure = report.get("temporal_exposure_audit") if isinstance(report.get("temporal_exposure_audit"), dict) else {}
    universe = report.get("universe_contract") if isinstance(report.get("universe_contract"), dict) else {}
    provider_governance = (
        report.get("provider_governance")
        if isinstance(report.get("provider_governance"), dict)
        else {}
    )
    experiment_binding = (
        report.get("experiment_governance")
        if isinstance(report.get("experiment_governance"), dict)
        else {}
    )
    experiment_verification = verify_experiment_binding(experiment_binding)
    universe_verification = verify_universe_contract(universe)
    provider_governance_verification = verify_provider_governance_contract(
        provider_governance,
        verification_at=str(provider_governance.get("generated_at") or ""),
    )
    internal_checks = {
        "mechanism_promising": str(report.get("mechanism_status") or "") == "PROMISING_NEEDS_FRESH_HOLDOUT",
        "dataset_contract_pass": str(manifest.get("status") or "") == "PASS",
        "validation_run_pass": (report.get("validation") or {}).get("ok") is True,
        "test_run_pass": (report.get("test") or {}).get("ok") is True,
        "full_run_pass": (report.get("full") or {}).get("ok") is True,
        "causal_prefix_audit_pass": str((report.get("causal_audit") or {}).get("status") or "") == "PASS",
        "validation_schedule_pass": development.get("validation_rebalance_schedule_pass") is True,
        "test_schedule_pass": development.get("test_rebalance_schedule_pass") is True,
        "full_schedule_pass": development.get("full_rebalance_schedule_pass") is True,
        "adjustment_contracts_pass": development.get("adjustment_contracts_pass") is True,
        "return_accounting_pass": development.get("return_accounting_double_count_protection_pass") is True,
        "universe_contract_present": bool(universe.get("contract_hash")),
        "universe_contract_integrity_pass": universe_verification.get("status") == "PASS",
        "provider_governance_contract_integrity_pass": provider_governance_verification.get("status") == "PASS",
        "temporal_exposure_audit_present": bool(exposure.get("audit_hash")),
        "experiment_preregistered_and_single_claimed": experiment_verification.get("status") == "PASS",
        "no_execution_authority": report.get("research_only") is True
        and report.get("paper_authorized") is False
        and report.get("live_order_allowed") is False,
    }
    internal_ready = all(internal_checks.values())
    claim_checks = {
        "temporal_holdout_unexposed": exposure.get("status") == "PASS" and exposure.get("fresh_holdout_eligible") is True,
        "point_in_time_universe_verified": universe_verification.get("historical_membership_verified") is True,
        "fresh_holdout_requirement_satisfied": report.get("fresh_holdout_required") is False,
        "forward_observation_requirement_satisfied": report.get("forward_observation_required") is False,
    }
    claim_ready = internal_ready and all(claim_checks.values())
    blockers: list[str] = []
    if not internal_ready:
        blockers.extend(f"internal_check_failed:{name}" for name, passed in internal_checks.items() if not passed)
    if not claim_checks["temporal_holdout_unexposed"]:
        blockers.append("temporal_holdout_previously_exposed")
    if not claim_checks["point_in_time_universe_verified"]:
        blockers.append("static_universe_has_survivorship_bias")
    if not claim_checks["fresh_holdout_requirement_satisfied"]:
        blockers.append("fresh_temporal_holdout_required")
    if not claim_checks["forward_observation_requirement_satisfied"]:
        blockers.append("forward_observation_required")
    payload = {
        "schema_version": PORTFOLIO_ADMISSION_SCHEMA_VERSION,
        "status": "INTERNAL_BACKTEST_READY" if internal_ready else "INTERNAL_BACKTEST_BLOCKED",
        "statistical_claim_status": "INDEPENDENT_EVIDENCE_READY" if claim_ready else "DEVELOPMENT_EVIDENCE_ONLY",
        "paper_admission_status": "BLOCKED",
        "internal_checks": internal_checks,
        "experiment_binding_verification": experiment_verification,
        "universe_contract_verification": universe_verification,
        "provider_governance_verification": provider_governance_verification,
        "statistical_claim_checks": claim_checks,
        "blockers": list(dict.fromkeys(blockers)),
        "manual_review_required": True,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["admission_hash"] = _canonical_hash(payload)
    return payload


def verify_internal_backtest_admission(audit: dict[str, Any]) -> dict[str, Any]:
    payload = dict(audit or {})
    expected_hash = str(payload.pop("admission_hash", "") or "")
    blockers: list[str] = []
    if str(audit.get("schema_version") or "") != PORTFOLIO_ADMISSION_SCHEMA_VERSION:
        blockers.append("admission_schema_invalid")
    if str(audit.get("status") or "") != "INTERNAL_BACKTEST_READY":
        blockers.append("internal_backtest_not_ready")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("admission_hash_mismatch")
    if str(audit.get("paper_admission_status") or "") != "BLOCKED":
        blockers.append("paper_admission_must_remain_blocked")
    if (
        audit.get("research_only") is not True
        or audit.get("paper_authorized") is not False
        or audit.get("live_order_allowed") is not False
        or audit.get("automatic_paper_activation_allowed") is not False
    ):
        blockers.append("admission_has_execution_authority")
    internal_checks = audit.get("internal_checks") if isinstance(audit.get("internal_checks"), dict) else {}
    if not internal_checks or any(not isinstance(value, bool) for value in internal_checks.values()):
        blockers.append("admission_internal_check_types_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "expected_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
