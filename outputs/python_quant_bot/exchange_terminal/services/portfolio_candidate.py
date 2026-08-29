from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .portfolio_admission import verify_internal_backtest_admission
from .portfolio_experiment import verify_experiment_binding
from .implementation_manifest import (
    build_implementation_manifest,
    verify_implementation_manifest,
)
from .portfolio_universe import verify_universe_contract
from .portfolio_evidence_bundle import verify_portfolio_evidence_bundle

PORTFOLIO_CANDIDATE_SCHEMA_VERSION = "frozen-portfolio-candidate-v7"
PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION = "frozen-portfolio-candidate-self-consistency-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _canonical_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def implementation_fingerprint(source_files: list[Path | str]) -> dict[str, Any]:
    return build_implementation_manifest(source_files)


def build_frozen_portfolio_candidate(
    report: dict[str, Any],
    *,
    source_files: list[Path | str],
) -> dict[str, Any]:
    blockers: list[str] = []
    evidence_bundle_verification = verify_portfolio_evidence_bundle(
        report,
        require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
    )
    if evidence_bundle_verification.get("status") != "PASS":
        blockers.extend(
            f"evidence_bundle:{item}"
            for item in evidence_bundle_verification.get("blockers") or ["verification_failed"]
        )
    if str(report.get("mechanism_status") or "") != "PROMISING_NEEDS_FRESH_HOLDOUT":
        blockers.append("mechanism_not_promising")
    if (report.get("causal_audit") or {}).get("status") != "PASS":
        blockers.append("causal_audit_not_passed")
    if (report.get("correlation_matrix") or {}).get("status") != "PASS":
        blockers.append("correlation_coverage_not_passed")
    if (
        report.get("research_only") is not True
        or report.get("paper_authorized") is not False
        or report.get("live_order_allowed") is not False
    ):
        blockers.append("research_report_has_invalid_execution_authority")
    admission = dict(report.get("backtest_admission") or {})
    admission_verification = verify_internal_backtest_admission(admission)
    if admission_verification.get("status") != "PASS":
        blockers.extend(
            f"backtest_admission:{item}"
            for item in admission_verification.get("blockers") or ["verification_failed"]
        )
    universe_contract = dict(report.get("universe_contract") or {})
    universe_verification = verify_universe_contract(universe_contract)
    if universe_verification.get("status") != "PASS":
        blockers.extend(
            f"universe_contract:{item}"
            for item in universe_verification.get("blockers") or ["verification_failed"]
        )
    temporal_exposure = dict(report.get("temporal_exposure_audit") or {})
    exposure_hash = str(temporal_exposure.get("audit_hash") or "")
    exposure_payload = dict(temporal_exposure)
    exposure_payload.pop("audit_hash", None)
    if not exposure_hash or _canonical_hash(exposure_payload) != exposure_hash:
        blockers.append("temporal_exposure_audit_hash_invalid")
    experiment_binding = (
        report.get("experiment_governance")
        if isinstance(report.get("experiment_governance"), dict)
        else {}
    )
    experiment_verification = verify_experiment_binding(experiment_binding)
    if experiment_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_binding:{item}"
            for item in experiment_verification.get("blockers") or ["verification_failed"]
        )
    fingerprint = implementation_fingerprint(source_files)
    if str(experiment_binding.get("implementation_fingerprint") or "") != str(fingerprint.get("fingerprint") or ""):
        blockers.append("experiment_binding_implementation_fingerprint_mismatch")
    spec = dict(report.get("spec") or {})
    manifest = dict(report.get("dataset_manifest") or {})
    candidate_id = str(spec.get("research_generation") or "PORTFOLIO_CANDIDATE")
    research_report_hash = report.get("batch_run_hash")
    spec_hash = report.get("spec_hash") or _canonical_hash(spec)
    dataset_hash = manifest.get("data_hash")
    for field_name, value in (
        ("research_report_hash", research_report_hash),
        ("spec_hash", spec_hash),
        ("dataset_hash", dataset_hash),
    ):
        if not _canonical_nonempty_text(value):
            blockers.append(f"candidate_anchor_invalid:{field_name}")
    payload = {
        "schema_version": PORTFOLIO_CANDIDATE_SCHEMA_VERSION,
        "self_consistency_version": PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION,
        "status": "FROZEN_DEVELOPMENT_CANDIDATE" if not blockers else "BLOCK",
        "blockers": blockers,
        "candidate_id": candidate_id,
        "research_report_hash": str(research_report_hash or ""),
        "spec": spec,
        "spec_hash": str(spec_hash or ""),
        "dataset_hash": str(dataset_hash or ""),
        "dataset_first": str(manifest.get("first") or ""),
        "dataset_last": str(manifest.get("last") or ""),
        "dataset_row_count": int(manifest.get("row_count") or 0),
        "dataset_symbols": list(manifest.get("symbols") or []),
        "implementation": fingerprint,
        "development_trial_count": int(spec.get("trial_count") or 0),
        "observed_development_report_count": int(temporal_exposure.get("prior_report_count") or 0) + 1,
        "distinct_exposed_test_run_count": int(temporal_exposure.get("distinct_test_run_count") or 0),
        "research_governance": {
            "universe_contract": universe_contract,
            "universe_contract_verification": universe_verification,
            "temporal_exposure_audit": temporal_exposure,
            "backtest_admission": admission,
            "experiment_binding": experiment_binding,
            "evidence_bundle_verification": evidence_bundle_verification,
        },
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "authorization_state": "BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["candidate_hash"] = _canonical_hash(payload)
    return payload


def verify_frozen_portfolio_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {
            "schema_version": PORTFOLIO_CANDIDATE_SCHEMA_VERSION,
            "self_consistency_version": PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION,
            "status": "BLOCK",
            "blockers": ["candidate_object_required"],
            "expected_hash": "",
            "actual_hash": "",
            "current_implementation_fingerprint": "",
            "implementation_verification": {"status": "BLOCK"},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    payload = dict(candidate or {})
    expected_hash = str(payload.pop("candidate_hash", "") or "")
    actual_hash = _canonical_hash(payload)
    blockers: list[str] = []
    if str(candidate.get("schema_version") or "") != PORTFOLIO_CANDIDATE_SCHEMA_VERSION:
        blockers.append("candidate_schema_invalid")
    if (
        str(candidate.get("self_consistency_version") or "")
        != PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION
    ):
        blockers.append("candidate_self_consistency_version_invalid")
    if str(candidate.get("status") or "") != "FROZEN_DEVELOPMENT_CANDIDATE":
        blockers.append("candidate_status_invalid")
    if not expected_hash or actual_hash != expected_hash:
        blockers.append("candidate_hash_mismatch")
    if (
        candidate.get("research_only") is not True
        or candidate.get("paper_authorized") is not False
        or candidate.get("live_order_allowed") is not False
    ):
        blockers.append("candidate_has_invalid_execution_authority")
    if candidate.get("fresh_holdout_required") is not True or candidate.get("forward_observation_required") is not True:
        blockers.append("candidate_research_gate_missing")
    if str(candidate.get("authorization_state") or "") != "BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD":
        blockers.append("candidate_authorization_state_invalid")
    spec = candidate.get("spec") if isinstance(candidate.get("spec"), dict) else {}
    if not isinstance(candidate.get("spec"), dict):
        blockers.append("candidate_spec_invalid")
    expected_candidate_id = str(spec.get("research_generation") or "PORTFOLIO_CANDIDATE")
    if str(candidate.get("candidate_id") or "") != expected_candidate_id:
        blockers.append("candidate_id_spec_mismatch")
    for field_name in ("research_report_hash", "spec_hash", "dataset_hash"):
        if not _canonical_nonempty_text(candidate.get(field_name)):
            blockers.append(f"candidate_anchor_invalid:{field_name}")
    governance = candidate.get("research_governance") if isinstance(candidate.get("research_governance"), dict) else {}
    universe_contract = (
        governance.get("universe_contract")
        if isinstance(governance.get("universe_contract"), dict)
        else {}
    )
    universe_verification = verify_universe_contract(universe_contract)
    if universe_verification.get("status") != "PASS":
        blockers.extend(
            f"candidate_universe_contract:{item}"
            for item in universe_verification.get("blockers") or ["verification_failed"]
        )
    temporal_exposure = (
        governance.get("temporal_exposure_audit")
        if isinstance(governance.get("temporal_exposure_audit"), dict)
        else {}
    )
    temporal_hash = str(temporal_exposure.get("audit_hash") or "")
    temporal_payload = dict(temporal_exposure)
    temporal_payload.pop("audit_hash", None)
    if not temporal_hash or _canonical_hash(temporal_payload) != temporal_hash:
        blockers.append("candidate_temporal_exposure_audit_hash_invalid")
    admission_verification = verify_internal_backtest_admission(dict(governance.get("backtest_admission") or {}))
    if admission_verification.get("status") != "PASS":
        blockers.extend(
            f"candidate_backtest_admission:{item}"
            for item in admission_verification.get("blockers") or ["verification_failed"]
        )
    experiment_verification = verify_experiment_binding(dict(governance.get("experiment_binding") or {}))
    if experiment_verification.get("status") != "PASS":
        blockers.extend(
            f"candidate_experiment_binding:{item}"
            for item in experiment_verification.get("blockers") or ["verification_failed"]
        )
    evidence_bundle_verification = governance.get("evidence_bundle_verification")
    if (
        not isinstance(evidence_bundle_verification, dict)
        or evidence_bundle_verification.get("status") != "PASS"
    ):
        blockers.append("candidate_evidence_bundle_verification_invalid")
    implementation = candidate.get("implementation") if isinstance(candidate.get("implementation"), dict) else {}
    implementation_verification = verify_implementation_manifest(implementation)
    if implementation_verification.get("status") != "PASS":
        blockers.extend(
            f"candidate_implementation:{item}"
            for item in implementation_verification.get("blockers") or ["verification_failed"]
        )
    current_fingerprint = str(implementation_verification.get("current_fingerprint") or "")
    binding = governance.get("experiment_binding") if isinstance(governance.get("experiment_binding"), dict) else {}
    if str(binding.get("implementation_fingerprint") or "") != str(implementation.get("fingerprint") or ""):
        blockers.append("candidate_experiment_implementation_fingerprint_mismatch")
    return {
        "schema_version": PORTFOLIO_CANDIDATE_SCHEMA_VERSION,
        "self_consistency_version": PORTFOLIO_CANDIDATE_SELF_CONSISTENCY_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "current_implementation_fingerprint": current_fingerprint,
        "implementation_verification": implementation_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
