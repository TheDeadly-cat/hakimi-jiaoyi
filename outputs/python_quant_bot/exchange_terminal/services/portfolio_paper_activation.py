from __future__ import annotations

import hashlib
import json
import math
from typing import Any


PORTFOLIO_PAPER_ACTIVATION_SCHEMA_VERSION = "portfolio-paper-activation-v1"
PAPER_ACTIVATION_SCOPE = "ISOLATED_PORTFOLIO_PAPER"
READY_STATUS = "READY_FOR_FROZEN_EVALUATION"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _is_sha256(value: Any) -> bool:
    clean = str(value or "").lower()
    return len(clean) == 64 and all(character in "0123456789abcdef" for character in clean)


def evaluate_paper_forward_context(context: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(context or {})
    readiness = dict(snapshot.get("readiness") or {})
    active = dict(snapshot.get("active_candidate") or {})
    scheduler = dict(snapshot.get("scheduler") or {})
    experiments = dict(snapshot.get("experiment_registry") or {})
    experiment_audit = dict(experiments.get("registry_audit") or {})
    progress = dict(readiness.get("progress") or {})
    critical_checks = dict(readiness.get("critical_checks") or {})
    candidate_hash = str(snapshot.get("candidate_hash") or readiness.get("candidate_hash") or "")
    blockers: list[str] = []

    if str(snapshot.get("status") or "") != READY_STATUS or str(readiness.get("status") or "") != READY_STATUS:
        blockers.append("forward_readiness_not_complete")
    if not _is_sha256(candidate_hash):
        blockers.append("active_candidate_hash_invalid")
    if str(readiness.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_candidate_hash_mismatch")
    if str(active.get("candidate_hash") or "") != candidate_hash:
        blockers.append("active_registry_candidate_hash_mismatch")
    if str(active.get("status") or "") != "ACTIVE_RESEARCH_CANDIDATE":
        blockers.append("active_candidate_registry_invalid")
    if str(snapshot.get("robustness_status") or "") != "ROBUSTNESS_PASS":
        blockers.append("robustness_not_passed")
    if str(experiments.get("status") or "") != "PASS" or str(experiment_audit.get("status") or "") != "PASS":
        blockers.append("experiment_registry_not_passed")
    if str(scheduler.get("status") or "") != "UP_TO_DATE" or str(scheduler.get("health") or "") != "PASS":
        blockers.append("forward_scheduler_not_healthy")
    if not critical_checks or not all(value is True for value in critical_checks.values()):
        blockers.append("forward_critical_checks_not_passed")
    if any(not isinstance(value, bool) for value in critical_checks.values()):
        blockers.append("forward_critical_check_type_invalid")

    progress_pairs = (
        ("natural_observations", "required_natural_observations"),
        ("externally_attested_observations", "required_externally_attested_observations"),
        ("planned_rebalances", "required_planned_rebalances"),
    )
    for actual_key, required_key in progress_pairs:
        actual = _integer(progress.get(actual_key))
        required = _integer(progress.get(required_key))
        if actual is None or required is None:
            blockers.append(f"forward_progress_type_invalid:{actual_key}")
            continue
        if required <= 0 or actual < required:
            blockers.append(f"forward_progress_incomplete:{actual_key}:{actual}/{required}")

    authority_payloads = {
        "snapshot": snapshot,
        "readiness": readiness,
        "active_candidate": active,
        "experiment_registry": experiments,
        "scheduler": scheduler,
    }
    for scope, item in authority_payloads.items():
        for key in ("paper_authorized", "live_order_allowed"):
            value = item.get(key)
            if not isinstance(value, bool):
                blockers.append(f"forward_authority_boolean_invalid:{scope}:{key}")
            elif value:
                blockers.append("forward_evidence_contains_execution_authority")

    generated_at = _integer(snapshot.get("generated_at"))
    if generated_at is None:
        blockers.append("forward_generation_time_invalid")
    evidence = {
        "candidate_hash": candidate_hash,
        "active_registry_hash": str(active.get("registry_hash") or ""),
        "robustness_hash": str(active.get("robustness_hash") or ""),
        "experiment_completion_receipt_hash": str(active.get("experiment_completion_receipt_hash") or ""),
        "forward_readiness_hash": str(readiness.get("readiness_hash") or ""),
        "scheduler_status_hash": str(scheduler.get("status_hash") or ""),
        "forward_generated_at": generated_at or 0,
    }
    for key, value in evidence.items():
        if key == "forward_generated_at":
            if int(value) <= 0:
                blockers.append("forward_generation_time_missing")
        elif not _is_sha256(value):
            blockers.append(f"forward_evidence_hash_invalid:{key}")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "evidence": evidence,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_paper_activation_receipt(
    *,
    account_id: str,
    forward_context: dict[str, Any],
    manual_approval: dict[str, Any],
    initial_cash: float,
    maximum_initial_cash: float = 1_000_000.0,
) -> dict[str, Any]:
    account = str(account_id or "").strip()
    context_audit = evaluate_paper_forward_context(forward_context)
    evidence = dict(context_audit.get("evidence") or {})
    approval = dict(manual_approval or {})
    cash = _number(initial_cash, -1.0)
    cash_limit = _number(maximum_initial_cash, -1.0)
    approved_at = _integer(approval.get("approved_at"))
    blockers = list(context_audit.get("blockers") or [])

    if not account:
        blockers.append("paper_account_id_missing")
    if cash <= 0:
        blockers.append("paper_initial_cash_not_positive")
    if cash_limit <= 0 or cash > cash_limit:
        blockers.append("paper_initial_cash_exceeds_limit")
    if approval.get("approved") is not True:
        blockers.append("manual_paper_approval_missing")
    if "approved" in approval and not isinstance(approval.get("approved"), bool):
        blockers.append("manual_paper_approval_type_invalid")
    if str(approval.get("scope") or "") != PAPER_ACTIVATION_SCOPE:
        blockers.append("manual_paper_approval_scope_invalid")
    if not str(approval.get("approver") or "").strip():
        blockers.append("manual_paper_approver_missing")
    if not str(approval.get("decision_id") or "").strip():
        blockers.append("manual_paper_decision_id_missing")
    if approved_at is None:
        blockers.append("manual_paper_approval_time_invalid")
    elif approved_at <= int(evidence.get("forward_generated_at") or 0):
        blockers.append("manual_paper_approval_must_follow_forward_evidence")
    if str(approval.get("candidate_hash") or "") != str(evidence.get("candidate_hash") or ""):
        blockers.append("manual_paper_candidate_hash_mismatch")
    if str(approval.get("forward_readiness_hash") or "") != str(evidence.get("forward_readiness_hash") or ""):
        blockers.append("manual_paper_readiness_hash_mismatch")

    payload = {
        "schema_version": PORTFOLIO_PAPER_ACTIVATION_SCHEMA_VERSION,
        "status": "APPROVED_FOR_ISOLATED_PAPER" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "scope": PAPER_ACTIVATION_SCOPE,
        "account_id": account,
        "initial_cash": cash,
        "maximum_initial_cash": cash_limit,
        **evidence,
        "manual_approval": approval,
        "manual_approval_required": True,
        "automatic_activation_allowed": False,
        "paper_authorized": not blockers,
        "live_order_allowed": False,
    }
    payload["receipt_hash"] = _canonical_hash(payload)
    return payload


def verify_paper_activation_receipt(
    receipt: dict[str, Any],
    *,
    expected_account_id: str = "",
    expected_candidate_hash: str = "",
) -> dict[str, Any]:
    payload = dict(receipt or {})
    expected_hash = str(payload.pop("receipt_hash", "") or "")
    blockers: list[str] = []
    if str(receipt.get("schema_version") or "") != PORTFOLIO_PAPER_ACTIVATION_SCHEMA_VERSION:
        blockers.append("paper_activation_schema_invalid")
    if str(receipt.get("status") or "") != "APPROVED_FOR_ISOLATED_PAPER":
        blockers.append("paper_activation_not_approved")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("paper_activation_receipt_hash_mismatch")
    if str(receipt.get("scope") or "") != PAPER_ACTIVATION_SCOPE:
        blockers.append("paper_activation_scope_invalid")
    if expected_account_id and str(receipt.get("account_id") or "") != str(expected_account_id):
        blockers.append("paper_activation_account_mismatch")
    candidate_hash = str(receipt.get("candidate_hash") or "")
    if not _is_sha256(candidate_hash):
        blockers.append("paper_activation_candidate_hash_invalid")
    if expected_candidate_hash and candidate_hash != str(expected_candidate_hash):
        blockers.append("paper_activation_candidate_mismatch")
    for key in (
        "active_registry_hash",
        "robustness_hash",
        "experiment_completion_receipt_hash",
        "forward_readiness_hash",
        "scheduler_status_hash",
    ):
        if not _is_sha256(receipt.get(key)):
            blockers.append(f"paper_activation_evidence_hash_invalid:{key}")
    if _number(receipt.get("initial_cash"), -1.0) <= 0:
        blockers.append("paper_activation_initial_cash_invalid")
    if _number(receipt.get("initial_cash"), 0.0) > _number(receipt.get("maximum_initial_cash"), -1.0):
        blockers.append("paper_activation_cash_limit_invalid")
    approval = dict(receipt.get("manual_approval") or {})
    if (
        approval.get("approved") is not True
        or not isinstance(approval.get("approved"), bool)
        or str(approval.get("scope") or "") != PAPER_ACTIVATION_SCOPE
        or not str(approval.get("approver") or "").strip()
        or not str(approval.get("decision_id") or "").strip()
    ):
        blockers.append("paper_activation_manual_approval_invalid")
    approved_at = _integer(approval.get("approved_at"))
    forward_generated_at = _integer(receipt.get("forward_generated_at"))
    if approved_at is None or forward_generated_at is None or approved_at <= forward_generated_at:
        blockers.append("paper_activation_manual_approval_time_invalid")
    if str(approval.get("candidate_hash") or "") != candidate_hash:
        blockers.append("paper_activation_manual_candidate_mismatch")
    if str(approval.get("forward_readiness_hash") or "") != str(receipt.get("forward_readiness_hash") or ""):
        blockers.append("paper_activation_manual_readiness_mismatch")
    if receipt.get("manual_approval_required") is not True:
        blockers.append("paper_activation_manual_review_contract_invalid")
    if receipt.get("automatic_activation_allowed") is not False:
        blockers.append("paper_activation_cannot_be_automatic")
    if receipt.get("paper_authorized") is not True or receipt.get("live_order_allowed") is not False:
        blockers.append("paper_activation_authority_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt_hash": expected_hash,
        "paper_authorized": not blockers,
        "live_order_allowed": False,
    }


def verify_current_paper_authorization(
    receipt: dict[str, Any],
    forward_context: dict[str, Any],
    *,
    expected_account_id: str,
    require_activation_readiness_hash: bool = False,
) -> dict[str, Any]:
    receipt_audit = verify_paper_activation_receipt(
        receipt,
        expected_account_id=expected_account_id,
    )
    context_audit = evaluate_paper_forward_context(forward_context)
    context_evidence = dict(context_audit.get("evidence") or {})
    blockers = [
        *(f"receipt:{item}" for item in receipt_audit.get("blockers") or []),
        *(f"current:{item}" for item in context_audit.get("blockers") or []),
    ]
    identity_keys = (
        "candidate_hash",
        "active_registry_hash",
        "robustness_hash",
        "experiment_completion_receipt_hash",
    )
    if require_activation_readiness_hash:
        identity_keys = (*identity_keys, "forward_readiness_hash")
    for key in identity_keys:
        if str(receipt.get(key) or "") != str(context_evidence.get(key) or ""):
            blockers.append(f"paper_activation_current_identity_mismatch:{key}")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": str(receipt.get("candidate_hash") or ""),
        "receipt_hash": str(receipt.get("receipt_hash") or ""),
        "paper_authorized": not blockers,
        "live_order_allowed": False,
    }
