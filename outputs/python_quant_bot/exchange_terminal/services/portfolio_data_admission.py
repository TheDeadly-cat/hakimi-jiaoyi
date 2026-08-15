from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .corporate_action_ledger import verify_adjustment_evidence
from .market_data_revision_ledger import verify_cross_source_evidence
from .portfolio_backtest import portfolio_revision_evidence_hash
from .portfolio_universe import verify_universe_contract
from .provider_governance import (
    required_provider_ids_from_evidence,
    verify_provider_governance_contract,
)
from .portfolio_evidence_bundle import (
    expand_portfolio_evidence_bundle,
    pack_portfolio_evidence_bundle,
)


PORTFOLIO_DATA_ADMISSION_SCHEMA_VERSION = "portfolio-data-admission-v4"
AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "live_order_allowed",
    "paper_authorized",
}
REQUIREMENT_TEXT = {
    "POINT_IN_TIME_UNIVERSE": (
        "Authoritative dated membership records cover the full research window, including removals and delistings."
    ),
    "OFFICIAL_CORPORATE_ACTION_MASTER": (
        "Split, dividend, suspension and delisting events are reconciled to a cryptographically identified official source."
    ),
    "RECENT_INDEPENDENT_SOURCE_OVERLAP": (
        "Each symbol has a recent verified PASS overlap from two independent provider families under the same adjustment basis."
    ),
    "PROVIDER_LICENSE_AND_RATE_LIMIT_REVIEW": (
        "Provider terms, storage rights, redistribution limits, quotas, retry policy and approval receipt are recorded and current."
    ),
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _native_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _timestamp_iso(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return ""
    try:
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return ""


def authority_violations(payload: Any, *, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if key in AUTHORITY_FIELDS and value is not False:
                violations.append(child)
            violations.extend(authority_violations(value, path=child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            violations.extend(authority_violations(value, path=f"{path}[{index}]"))
    return violations


def _revision_integrity(revision: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    expected_hash = str(revision.get("evidence_hash") or "")
    if not expected_hash or portfolio_revision_evidence_hash(revision) != expected_hash:
        blockers.append("portfolio_revision_evidence_hash_invalid")
    status = str(revision.get("status") or "").upper()
    children = [
        dict(revision.get(name) or {})
        for name in ("accepted_cache", "backtest_dataset")
        if isinstance(revision.get(name), dict) and revision.get(name)
    ]
    child_statuses = [str(item.get("status") or "REVIEW").upper() for item in children]
    if not children:
        blockers.append("portfolio_revision_children_missing")
    if any(item not in {"PASS", "REVIEW", "BLOCK"} for item in child_statuses):
        blockers.append("portfolio_revision_child_status_invalid")
    expected_status = (
        "BLOCK" if "BLOCK" in child_statuses else "REVIEW" if "REVIEW" in child_statuses else "PASS"
    )
    if status != expected_status:
        blockers.append("portfolio_revision_status_semantic_mismatch")
    if authority_violations(revision):
        blockers.append("portfolio_revision_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "evidence_hash": expected_hash,
        "revision_status": status or "MISSING",
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _cross_source_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    records = [dict(item) for item in evidence.get("cross_source") or [] if isinstance(item, dict)]
    audited = [(item, verify_cross_source_evidence(item)) for item in records]
    verified = [item for item, audit in audited if audit.get("status") == "PASS"]
    passing = [item for item in verified if item.get("status") == "PASS"]
    selected = min(
        passing or verified or records,
        key=lambda item: _native_nonnegative_int(item.get("latest_overlap_gap_days"))
        if isinstance(item.get("latest_overlap_gap_days"), int)
        and not isinstance(item.get("latest_overlap_gap_days"), bool)
        else 10**9,
        default={},
    )
    audit_blockers = [
        f"record_{index}:{reason}"
        for index, (_, audit) in enumerate(audited)
        for reason in audit.get("blockers") or []
    ]
    integrity_pass = bool(records) and len(verified) == len(records)
    return {
        "record_count": len(records),
        "integrity_status": "PASS" if integrity_pass else "BLOCK",
        "integrity_blockers": audit_blockers or ([] if records else ["cross_source_evidence_missing"]),
        "status": str(selected.get("status") or "MISSING"),
        "primary_provider": str(selected.get("primary_provider") or ""),
        "secondary_provider": str(selected.get("secondary_provider") or ""),
        "independent_provider_families": selected.get("independent_provider_families") is True,
        "overlap_count": _native_nonnegative_int(selected.get("overlap_count")),
        "overlap_last": str(selected.get("overlap_last") or ""),
        "latest_overlap_gap_days": (
            selected.get("latest_overlap_gap_days")
            if isinstance(selected.get("latest_overlap_gap_days"), int)
            and not isinstance(selected.get("latest_overlap_gap_days"), bool)
            else None
        ),
        "warnings": list(selected.get("warnings") or []),
        "evidence_hash": str(selected.get("evidence_hash") or ""),
    }


def _symbol_rows(
    symbols: list[str],
    adjustments: dict[str, Any],
    revisions: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        adjustment = dict(adjustments.get(symbol) or {})
        revision = dict(revisions.get(symbol) or {})
        adjustment_audit = verify_adjustment_evidence(adjustment)
        revision_audit = _revision_integrity(revision)
        cross_source = _cross_source_summary(revision)
        official_verified = (
            adjustment_audit.get("status") == "PASS"
            and adjustment_audit.get("official_source_verified") is True
        )
        recent_overlap = (
            cross_source.get("integrity_status") == "PASS"
            and cross_source.get("status") == "PASS"
            and cross_source.get("independent_provider_families") is True
            and isinstance(cross_source.get("latest_overlap_gap_days"), int)
            and int(cross_source["latest_overlap_gap_days"]) <= 10
        )
        rows.append({
            "symbol": symbol,
            "dataset_source": str(adjustment.get("source") or ""),
            "adjustment_status": str(adjustment.get("status") or "MISSING"),
            "adjustment_integrity_status": str(adjustment_audit.get("status") or "BLOCK"),
            "adjustment_integrity_blockers": list(adjustment_audit.get("blockers") or []),
            "adjustment_basis": str(adjustment.get("adjustment_basis") or ""),
            "corporate_action_coverage": str(adjustment.get("corporate_action_coverage") or "UNKNOWN").upper(),
            "corporate_action_count": _native_nonnegative_int(adjustment.get("corporate_action_count")),
            "official_corporate_action_source": official_verified,
            "revision_status": str(revision.get("status") or "MISSING"),
            "revision_integrity_status": str(revision_audit.get("status") or "BLOCK"),
            "revision_integrity_blockers": list(revision_audit.get("blockers") or []),
            "cross_source": cross_source,
            "recent_independent_overlap_pass": recent_overlap,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        })
    return rows


def _requirements(
    rows: list[dict[str, Any]],
    *,
    point_in_time_verified: bool,
    provider_approved: bool,
) -> list[dict[str, Any]]:
    symbols = [str(item.get("symbol") or "") for item in rows]
    static_symbols = [] if point_in_time_verified else symbols
    unofficial = [str(item.get("symbol") or "") for item in rows if item.get("official_corporate_action_source") is not True]
    stale = [str(item.get("symbol") or "") for item in rows if item.get("recent_independent_overlap_pass") is not True]
    affected = {
        "POINT_IN_TIME_UNIVERSE": static_symbols,
        "OFFICIAL_CORPORATE_ACTION_MASTER": unofficial,
        "RECENT_INDEPENDENT_SOURCE_OVERLAP": stale,
        "PROVIDER_LICENSE_AND_RATE_LIMIT_REVIEW": [] if provider_approved else symbols,
    }
    return [
        {
            "gate_id": gate_id,
            "status": "PASS" if not affected_symbols else (
                "NOT_ASSESSED" if gate_id == "PROVIDER_LICENSE_AND_RATE_LIMIT_REVIEW" else "BLOCK"
            ),
            "affected_symbols": affected_symbols,
            "acceptance_criteria": REQUIREMENT_TEXT[gate_id],
        }
        for gate_id, affected_symbols in affected.items()
    ]


def _coverage_summary(
    rows: list[dict[str, Any]],
    *,
    point_in_time_verified: bool,
    survivorship_bias_status: str,
) -> dict[str, Any]:
    return {
        "adjustment_contract_pass_count": sum(
            item.get("adjustment_status") == "PASS" and item.get("adjustment_integrity_status") == "PASS"
            for item in rows
        ),
        "revision_ledger_pass_count": sum(
            item.get("revision_status") == "PASS" and item.get("revision_integrity_status") == "PASS"
            for item in rows
        ),
        "cross_source_integrity_pass_count": sum(
            (item.get("cross_source") or {}).get("integrity_status") == "PASS" for item in rows
        ),
        "recent_independent_overlap_pass_count": sum(
            item.get("recent_independent_overlap_pass") is True for item in rows
        ),
        "official_corporate_action_source_count": sum(
            item.get("official_corporate_action_source") is True for item in rows
        ),
        "point_in_time_universe_verified": point_in_time_verified,
        "survivorship_bias_status": survivorship_bias_status,
    }


def build_portfolio_data_admission_audit(
    *,
    generated_at: int,
    active_status: str,
    candidate: dict[str, Any],
    report: dict[str, Any],
    candidate_file: str,
    candidate_file_sha256: str,
    report_file: str,
    report_file_sha256: str,
    expected_report_file_sha256: str,
) -> dict[str, Any]:
    expanded_report, source_bundle_audit = expand_portfolio_evidence_bundle(
        report,
        require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    report = expanded_report
    candidate_hash = str(candidate.get("candidate_hash") or "")
    manifest = dict(report.get("dataset_manifest") or {})
    universe = dict(report.get("universe_contract") or {})
    provider_governance = dict(report.get("provider_governance") or {})
    symbols = sorted({str(item).upper() for item in manifest.get("symbols") or [] if str(item)})
    adjustments = dict(manifest.get("adjustment_evidence") or {})
    revisions = dict(manifest.get("data_revision_evidence") or {})
    rows = _symbol_rows(symbols, adjustments, revisions)
    required_providers = required_provider_ids_from_evidence(adjustments, revisions)
    universe_audit = verify_universe_contract(universe)
    provider_audit = verify_provider_governance_contract(
        provider_governance,
        required_providers=required_providers,
        verification_at=_timestamp_iso(generated_at),
    )
    frozen_candidate = dict(report.get("frozen_candidate") or {})
    source_binding_checks = {
        "research_evidence_bundle_pass": source_bundle_audit.get("status") == "PASS",
        "active_candidate_pass": str(active_status or "") == "PASS",
        "candidate_hash_present": _valid_sha256(candidate_hash),
        "report_candidate_matches": str(frozen_candidate.get("candidate_hash") or "") == candidate_hash,
        "dataset_hash_matches": str(manifest.get("data_hash") or "") == str(candidate.get("dataset_hash") or ""),
        "dataset_symbols_match": symbols
        == sorted({str(item).upper() for item in candidate.get("dataset_symbols") or [] if str(item)}),
        "research_batch_matches": str(report.get("batch_run_hash") or "")
        == str(candidate.get("research_report_hash") or ""),
        "candidate_file_hash_present": _valid_sha256(candidate_file_sha256),
        "research_file_hash_matches_receipt": _valid_sha256(report_file_sha256)
        and report_file_sha256 == str(expected_report_file_sha256 or ""),
    }
    source_authority_paths = authority_violations({"candidate": candidate, "report": report})
    research_checks = {
        "source_binding_pass": all(source_binding_checks.values()),
        "dataset_manifest_pass": manifest.get("status") == "PASS",
        "universe_contract_integrity_pass": universe_audit.get("status") == "PASS",
        "provider_governance_contract_integrity_pass": provider_audit.get("status") == "PASS",
        "all_symbols_have_adjustment_contracts": bool(rows)
        and all(
            item["adjustment_status"] == "PASS" and item["adjustment_integrity_status"] == "PASS"
            for item in rows
        ),
        "all_symbols_have_revision_ledgers": bool(rows)
        and all(
            item["revision_status"] == "PASS" and item["revision_integrity_status"] == "PASS"
            for item in rows
        ),
        "every_symbol_has_cross_source_evidence": bool(rows)
        and all(
            int(item["cross_source"]["record_count"]) > 0
            and item["cross_source"]["integrity_status"] == "PASS"
            for item in rows
        ),
        "no_execution_authority": not source_authority_paths,
    }
    point_in_time_verified = (
        universe_audit.get("status") == "PASS"
        and universe_audit.get("historical_membership_verified") is True
        and universe_audit.get("point_in_time_constituents") is True
    )
    provider_approved = (
        provider_audit.get("status") == "PASS"
        and provider_audit.get("approved_for_research_storage") is True
        and provider_audit.get("license_review_status") == "PASS"
        and provider_audit.get("rate_limit_policy_status") == "PASS"
    )
    paper_gate_checks = {
        "research_data_contract_pass": all(research_checks.values()),
        "point_in_time_universe_verified": point_in_time_verified,
        "official_corporate_action_master_complete": bool(rows)
        and all(item["official_corporate_action_source"] is True for item in rows),
        "recent_independent_overlap_for_every_symbol": bool(rows)
        and all(item["recent_independent_overlap_pass"] is True for item in rows),
        "provider_license_and_rate_limit_review_pass": provider_approved,
        "manual_review_required": True,
    }
    research_ready = all(research_checks.values())
    paper_ready = research_ready and all(
        value is True for name, value in paper_gate_checks.items() if name != "manual_review_required"
    )
    requirements = _requirements(
        rows,
        point_in_time_verified=point_in_time_verified,
        provider_approved=provider_approved,
    )
    integrity_blockers = [name for name, value in source_binding_checks.items() if not value]
    integrity_blockers.extend(f"execution_authority:{path}" for path in source_authority_paths)
    payload = {
        "schema_version": PORTFOLIO_DATA_ADMISSION_SCHEMA_VERSION,
        "status": "AUDIT_COMPLETE" if not integrity_blockers else "AUDIT_BLOCKED",
        "generated_at": int(generated_at),
        "candidate_hash": candidate_hash,
        "source_artifacts": {
            "candidate_file": str(candidate_file),
            "candidate_file_sha256": str(candidate_file_sha256),
            "research_file": str(report_file),
            "research_file_sha256": str(report_file_sha256),
        },
        "source_binding_checks": source_binding_checks,
        "source_authority_violations": source_authority_paths,
        "research_evidence_bundle_verification": source_bundle_audit,
        "evidence_contracts": {
            "dataset_manifest_status": str(manifest.get("status") or ""),
            "universe_contract": universe,
            "provider_governance": provider_governance,
            "required_provider_ids": required_providers,
            "adjustment_evidence": adjustments,
            "data_revision_evidence": revisions,
        },
        "universe_contract_verification": universe_audit,
        "provider_governance_verification": provider_audit,
        "research_checks": research_checks,
        "paper_gate_checks": paper_gate_checks,
        "internal_research_data_status": "READY_WITH_LIMITATIONS" if research_ready else "BLOCK",
        "paper_data_admission_status": "READY_FOR_MANUAL_REVIEW" if paper_ready else "BLOCK",
        "live_data_admission_status": "BLOCK",
        "symbol_count": len(rows),
        "symbols": rows,
        "coverage_summary": _coverage_summary(
            rows,
            point_in_time_verified=point_in_time_verified,
            survivorship_bias_status=str(universe.get("survivorship_bias_status") or "UNKNOWN"),
        ),
        "requirements": requirements,
        "blockers": list(dict.fromkeys(integrity_blockers)),
        "admission_blockers": [item["gate_id"] for item in requirements if item["status"] != "PASS"],
        "manual_review_required": True,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["audit_hash"] = canonical_hash(payload)
    return pack_portfolio_evidence_bundle(payload)


def verify_portfolio_data_admission_audit(payload: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    payload, artifact_bundle_audit = expand_portfolio_evidence_bundle(
        payload,
        require_bundle=True,
    )
    if artifact_bundle_audit.get("status") != "PASS":
        blockers.extend(
            f"data_admission_evidence_bundle:{item}"
            for item in artifact_bundle_audit.get("blockers") or ["verification_failed"]
        )
    payload = dict(payload) if isinstance(payload, dict) else {}
    clean = dict(payload)
    expected_hash = str(clean.pop("audit_hash", "") or "")
    if payload.get("schema_version") != PORTFOLIO_DATA_ADMISSION_SCHEMA_VERSION:
        blockers.append("data_admission_schema_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("data_admission_hash_invalid")
    contracts = payload.get("evidence_contracts") if isinstance(payload.get("evidence_contracts"), dict) else {}
    universe = dict(contracts.get("universe_contract") or {})
    provider_governance = dict(contracts.get("provider_governance") or {})
    adjustments = dict(contracts.get("adjustment_evidence") or {})
    revisions = dict(contracts.get("data_revision_evidence") or {})
    declared_providers = list(contracts.get("required_provider_ids") or [])
    expected_providers = required_provider_ids_from_evidence(adjustments, revisions)
    if declared_providers != expected_providers:
        blockers.append("data_admission_required_providers_mismatch")
    rows_payload = payload.get("symbols") if isinstance(payload.get("symbols"), list) else []
    symbols = [str(item.get("symbol") or "") for item in rows_payload if isinstance(item, dict)]
    rebuilt_rows = _symbol_rows(symbols, adjustments, revisions)
    if rows_payload != rebuilt_rows:
        blockers.append("data_admission_symbol_semantics_mismatch")
    if payload.get("symbol_count") != len(rebuilt_rows):
        blockers.append("data_admission_symbol_count_mismatch")
    universe_audit = verify_universe_contract(universe)
    provider_audit = verify_provider_governance_contract(
        provider_governance,
        required_providers=expected_providers,
        verification_at=_timestamp_iso(payload.get("generated_at")),
    )
    if payload.get("universe_contract_verification") != universe_audit:
        blockers.append("data_admission_universe_verification_mismatch")
    if payload.get("provider_governance_verification") != provider_audit:
        blockers.append("data_admission_provider_verification_mismatch")
    source_checks = payload.get("source_binding_checks") if isinstance(payload.get("source_binding_checks"), dict) else {}
    if not source_checks or any(not isinstance(value, bool) for value in source_checks.values()):
        blockers.append("data_admission_source_check_types_invalid")
    source_authority_paths = payload.get("source_authority_violations")
    if not isinstance(source_authority_paths, list) or any(not isinstance(item, str) for item in source_authority_paths):
        blockers.append("data_admission_source_authority_paths_invalid")
        source_authority_paths = []
    source_bundle_audit = payload.get("research_evidence_bundle_verification")
    if not isinstance(source_bundle_audit, dict) or source_bundle_audit.get("status") != "PASS":
        blockers.append("data_admission_source_evidence_bundle_invalid")
    expected_research_checks = {
        "source_binding_pass": bool(source_checks) and all(source_checks.values()),
        "dataset_manifest_pass": contracts.get("dataset_manifest_status") == "PASS",
        "universe_contract_integrity_pass": universe_audit.get("status") == "PASS",
        "provider_governance_contract_integrity_pass": provider_audit.get("status") == "PASS",
        "all_symbols_have_adjustment_contracts": bool(rebuilt_rows)
        and all(
            item["adjustment_status"] == "PASS" and item["adjustment_integrity_status"] == "PASS"
            for item in rebuilt_rows
        ),
        "all_symbols_have_revision_ledgers": bool(rebuilt_rows)
        and all(
            item["revision_status"] == "PASS" and item["revision_integrity_status"] == "PASS"
            for item in rebuilt_rows
        ),
        "every_symbol_has_cross_source_evidence": bool(rebuilt_rows)
        and all(
            int(item["cross_source"]["record_count"]) > 0
            and item["cross_source"]["integrity_status"] == "PASS"
            for item in rebuilt_rows
        ),
        "no_execution_authority": not source_authority_paths,
    }
    if payload.get("research_checks") != expected_research_checks:
        blockers.append("data_admission_research_checks_mismatch")
    research_ready = all(expected_research_checks.values())
    point_in_time_verified = (
        universe_audit.get("status") == "PASS"
        and universe_audit.get("historical_membership_verified") is True
        and universe_audit.get("point_in_time_constituents") is True
    )
    provider_approved = (
        provider_audit.get("status") == "PASS"
        and provider_audit.get("approved_for_research_storage") is True
        and provider_audit.get("license_review_status") == "PASS"
        and provider_audit.get("rate_limit_policy_status") == "PASS"
    )
    expected_paper_checks = {
        "research_data_contract_pass": research_ready,
        "point_in_time_universe_verified": point_in_time_verified,
        "official_corporate_action_master_complete": bool(rebuilt_rows)
        and all(item["official_corporate_action_source"] is True for item in rebuilt_rows),
        "recent_independent_overlap_for_every_symbol": bool(rebuilt_rows)
        and all(item["recent_independent_overlap_pass"] is True for item in rebuilt_rows),
        "provider_license_and_rate_limit_review_pass": provider_approved,
        "manual_review_required": True,
    }
    if payload.get("paper_gate_checks") != expected_paper_checks:
        blockers.append("data_admission_paper_gate_checks_mismatch")
    paper_ready = research_ready and all(
        value is True for name, value in expected_paper_checks.items() if name != "manual_review_required"
    )
    expected_requirements = _requirements(
        rebuilt_rows,
        point_in_time_verified=point_in_time_verified,
        provider_approved=provider_approved,
    )
    if payload.get("requirements") != expected_requirements:
        blockers.append("data_admission_requirements_mismatch")
    expected_admission_blockers = [
        item["gate_id"] for item in expected_requirements if item["status"] != "PASS"
    ]
    if payload.get("admission_blockers") != expected_admission_blockers:
        blockers.append("data_admission_gate_blockers_mismatch")
    expected_coverage = _coverage_summary(
        rebuilt_rows,
        point_in_time_verified=point_in_time_verified,
        survivorship_bias_status=str(universe.get("survivorship_bias_status") or "UNKNOWN"),
    )
    if payload.get("coverage_summary") != expected_coverage:
        blockers.append("data_admission_coverage_summary_mismatch")
    expected_integrity_blockers = [name for name, value in source_checks.items() if value is not True]
    expected_integrity_blockers.extend(f"execution_authority:{path}" for path in source_authority_paths)
    expected_integrity_blockers = list(dict.fromkeys(expected_integrity_blockers))
    if payload.get("blockers") != expected_integrity_blockers:
        blockers.append("data_admission_integrity_blockers_mismatch")
    expected_status = "AUDIT_COMPLETE" if not expected_integrity_blockers else "AUDIT_BLOCKED"
    if payload.get("status") != expected_status:
        blockers.append("data_admission_status_semantic_mismatch")
    expected_internal = "READY_WITH_LIMITATIONS" if research_ready else "BLOCK"
    if payload.get("internal_research_data_status") != expected_internal:
        blockers.append("internal_research_data_status_semantic_mismatch")
    expected_paper = "READY_FOR_MANUAL_REVIEW" if paper_ready else "BLOCK"
    if payload.get("paper_data_admission_status") != expected_paper:
        blockers.append("paper_data_admission_status_semantic_mismatch")
    if payload.get("live_data_admission_status") != "BLOCK":
        blockers.append("live_data_admission_must_remain_blocked")
    if payload.get("manual_review_required") is not True:
        blockers.append("data_admission_manual_review_not_required")
    if payload.get("automatic_paper_activation_allowed") is not False:
        blockers.append("automatic_paper_activation_not_blocked")
    if authority_violations(payload):
        blockers.append("data_admission_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "expected_hash": expected_hash,
        "paper_data_admission_status": expected_paper,
        "evidence_bundle_verification": artifact_bundle_audit,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
