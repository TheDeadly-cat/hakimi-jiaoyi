from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_json_hash import canonical_hash
from .execution_authority import authority_violations
from .strategy_correlation_multiplicity_protocol import (
    TARGET_MATRIX_REPORT_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
)
from .strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
)
from .strategy_research_evidence import (
    STRATEGY_RESEARCH_MULTIPLICITY_REPORT_SCHEMA_VERSION,
    verify_strategy_research_report,
)


STRATEGY_MATRIX_MULTIPLICITY_REPORT_SCHEMA_VERSION = 8
STRATEGY_MATRIX_MULTIPLICITY_REPORT_VERIFICATION_SCHEMA_VERSION = (
    "strategy-matrix-multiplicity-report-verification-v1"
)

_REPORT_FIELDS = frozenset({
    "schema_version",
    "status",
    "decision_status",
    "inner_report",
    "inner_report_hash",
    "inner_batch_run_hash",
    "protocol_hash",
    "multiplicity_evidence_hash",
    "inner_report_verification_status",
    "multiplicity_evidence_verification_status",
    "required_protocol_schema_version",
    "required_inner_report_schema_version",
    "formal_registry_bound",
    "current_report_schema_bound",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "research_only",
    "permissions",
    "next_evidence_required",
    "blockers",
    "report_hash",
})


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    document = dict(payload)
    document["report_hash"] = canonical_hash(document)
    return document


def _invalid_report() -> dict[str, Any]:
    return _sealed({
        "schema_version": STRATEGY_MATRIX_MULTIPLICITY_REPORT_SCHEMA_VERSION,
        "status": "BLOCK",
        "decision_status": "BLOCK",
        "inner_report": None,
        "inner_report_hash": None,
        "inner_batch_run_hash": None,
        "protocol_hash": None,
        "multiplicity_evidence_hash": None,
        "inner_report_verification_status": "BLOCK",
        "multiplicity_evidence_verification_status": "BLOCK",
        "required_protocol_schema_version": (
            STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION
        ),
        "required_inner_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "formal_registry_bound": False,
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "parameter_selection_allowed": False,
        "performance_claim_allowed": False,
        "profitability_proven": False,
        "research_only": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "next_evidence_required": "VALID_SCHEMA16_RESEARCH_REPORT",
        "blockers": ["matrix_multiplicity_report_chain_invalid"],
    })


def build_strategy_matrix_multiplicity_report(
    inner_report: Any,
) -> dict[str, Any]:
    inner = _mapping(inner_report)
    governance = _mapping(inner.get("research_governance"))
    protocol = _mapping(governance.get("protocol"))
    batch_spec = _mapping(inner.get("batch_spec"))
    evidence = _mapping(inner.get("correlation_multiplicity_evidence"))
    inner_verification = verify_strategy_research_report(
        inner_report,
        require_formal=True,
    )
    evidence_verification = _mapping(
        inner_verification.get("correlation_multiplicity_verification")
    )

    chain_valid = all((
        inner_verification.get("status") == "PASS",
        evidence_verification.get("status") == "PASS",
        inner.get("schema_version")
        == STRATEGY_RESEARCH_MULTIPLICITY_REPORT_SCHEMA_VERSION,
        inner.get("schema_version") == TARGET_REPORT_SCHEMA_VERSION,
        protocol.get("schema_version")
        == STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
        governance.get("protocol_hash") == protocol.get("protocol_hash"),
        inner.get("batch_spec") == protocol.get("batch_spec"),
        inner.get("batch_spec_hash") == protocol.get("batch_spec_hash"),
        batch_spec.get("report_schema_version") == TARGET_REPORT_SCHEMA_VERSION,
        evidence.get("protocol_hash") == protocol.get("protocol_hash"),
        evidence.get("required_matrix_report_schema_version")
        == TARGET_MATRIX_REPORT_SCHEMA_VERSION,
    ))
    if not chain_valid:
        return _invalid_report()

    formal_registry_bound = all((
        governance.get("status") == "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE",
        governance.get("single_use_claim") is True,
        bool(str(governance.get("claim_hash") or "")),
        bool(str(governance.get("completion_hash") or "")),
    ))
    decision_status = str(evidence.get("decision_status") or "BLOCK")
    if decision_status != "PASS":
        next_evidence = str(
            evidence.get("next_evidence_required")
            or "RESOLVE_MULTIPLICITY_EVIDENCE_BLOCK"
        )
    elif not formal_registry_bound:
        next_evidence = "PROTOCOL_V5_REGISTRY_TRANSACTION"
    else:
        next_evidence = "SCHEMA8_CONSUMER_ACTIVATION_REVIEW"

    return _sealed({
        "schema_version": STRATEGY_MATRIX_MULTIPLICITY_REPORT_SCHEMA_VERSION,
        "status": "PASS",
        "decision_status": decision_status,
        "inner_report": deepcopy(inner),
        "inner_report_hash": canonical_hash(inner),
        "inner_batch_run_hash": str(inner.get("batch_run_hash") or ""),
        "protocol_hash": str(protocol.get("protocol_hash") or ""),
        "multiplicity_evidence_hash": str(evidence.get("evidence_hash") or ""),
        "inner_report_verification_status": "PASS",
        "multiplicity_evidence_verification_status": "PASS",
        "required_protocol_schema_version": (
            STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION
        ),
        "required_inner_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "formal_registry_bound": formal_registry_bound,
        "current_report_schema_bound": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "parameter_selection_allowed": False,
        "performance_claim_allowed": False,
        "profitability_proven": False,
        "research_only": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "next_evidence_required": next_evidence,
        "blockers": list(evidence.get("blockers") or []),
    })


def verify_strategy_matrix_multiplicity_report(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(document)
    if set(payload) != _REPORT_FIELDS:
        blockers.append("matrix_multiplicity_report_fields_invalid")
    if (
        payload.get("schema_version")
        != STRATEGY_MATRIX_MULTIPLICITY_REPORT_SCHEMA_VERSION
    ):
        blockers.append("matrix_multiplicity_report_schema_invalid")
    if payload.get("status") != "PASS":
        blockers.append("matrix_multiplicity_report_chain_blocked")
    clean = dict(payload)
    observed_hash = str(clean.pop("report_hash", "") or "")
    if not observed_hash or canonical_hash(clean) != observed_hash:
        blockers.append("matrix_multiplicity_report_hash_invalid")
    expected = build_strategy_matrix_multiplicity_report(
        payload.get("inner_report"),
    )
    if payload != expected:
        blockers.append("matrix_multiplicity_report_replay_mismatch")
    blockers.extend(
        f"matrix_multiplicity_report_authority:{item}"
        for item in authority_violations(payload)
    )
    return {
        "schema_version": (
            STRATEGY_MATRIX_MULTIPLICITY_REPORT_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "report_status": str(payload.get("status") or "BLOCK"),
        "decision_status": str(payload.get("decision_status") or "BLOCK"),
        "report_hash": observed_hash or None,
        "blockers": sorted(set(blockers)),
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
