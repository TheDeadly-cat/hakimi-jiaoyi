"""Redacted public projection for ADR0181 plus ADR0182 evidence.

The projection is descriptive and unmounted.  It independently reverifies both
source contracts but does not bind ADR0181 evidence into ADR0182, execute a shadow
consumer, establish external authority, or grant any trading permission.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3
    as readiness_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4
    as preregistration_contract,
)


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-readiness-public-projection-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-readiness-public-projection-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260822-shadow-readiness-evidence-stair-projection-lock-1"
SOURCE_STATE = "LOCAL_EVIDENCE_VERIFIED"
GAP_STATE = "EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN"
MATURITY_STATE = "UNMOUNTED_CANDIDATE"
PERMISSION_STATE = "UNAUTHORIZED"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_READINESS_CONTEXT_KEYS = {
    "readiness_v2",
    "trusted_clock_attestation",
    "readiness_v2_verification_context",
    "trusted_clock_verification_context",
}
_PREREGISTRATION_CONTEXT_KEYS = {
    "preregistration_v3",
    "v3_verification_context",
    "current_implementation_sha256",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["projection_hash"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return result


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _pipeline(source_state: str, gap_state: str) -> list[dict[str, str]]:
    return [
        {"stage": "SOURCE", "state": source_state},
        {"stage": "GAP", "state": gap_state},
        {"stage": "MATURITY", "state": MATURITY_STATE},
        {"stage": "PERMISSION", "state": PERMISSION_STATE},
    ]


def _blank_projection(status: str) -> dict[str, Any]:
    source_state = "NOT_SUPPLIED" if status == "NOT_SUPPLIED" else "UNKNOWN"
    gap_state = "NOT_SUPPLIED" if status == "NOT_SUPPLIED" else "UNKNOWN"
    return _seal(
        {
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "pipeline": _pipeline(source_state, gap_state),
            "source": {
                "readiness_envelope_supplied": False,
                "readiness_envelope_exactly_verified": False,
                "readiness_schema_version": None,
                "readiness_envelope_hash": None,
                "preregistration_supplied": False,
                "preregistration_exactly_verified": False,
                "preregistration_schema_version": None,
                "preregistration_hash": None,
                "contract_pin_aligned": False,
                "readiness_evidence_bound_to_preregistration": False,
            },
            "summary": {
                "required_input_count": None,
                "verified_input_count": None,
                "signed_clock_source_count": None,
                "closed_local_blocker_count": None,
                "readiness_blocker_count": None,
                "preregistration_blocker_count": None,
                "preregistration_status": None,
                "contract_pin_aligned": False,
                "readiness_evidence_bound_to_preregistration": False,
                "consumer_executed": False,
                "external_time_authority_authenticated": False,
                "current_time_established": False,
            },
            "facts": {
                "source_documents_embedded": False,
                "verification_contexts_embedded": False,
                "public_keys_embedded": False,
                "signatures_embedded": False,
                "raw_receipts_embedded": False,
                "runtime_assets_accessed": False,
                "runtime_consumer_mounted": False,
                "risk_service_invoked": False,
                "natural_forward_chain_changed": False,
                "profitability_proof": False,
            },
            "authority": _authority(),
        }
    )


def _is_exact_dict(value: Any, expected_keys: set[str]) -> bool:
    return type(value) is dict and set(value) == expected_keys


def _has_locked_authority(document: dict[str, Any]) -> bool:
    authority = document.get("authority")
    return (
        type(authority) is dict
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _verify_sources(
    readiness_document: Any,
    preregistration_document: Any,
    readiness_verification_context: Any,
    preregistration_verification_context: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not _is_exact_dict(readiness_verification_context, _READINESS_CONTEXT_KEYS):
        return None
    if not _is_exact_dict(
        preregistration_verification_context, _PREREGISTRATION_CONTEXT_KEYS
    ):
        return None
    if type(readiness_document) is not dict or type(preregistration_document) is not dict:
        return None
    try:
        readiness_verified = readiness_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
            readiness_document,
            readiness_verification_context["readiness_v2"],
            readiness_verification_context["trusted_clock_attestation"],
            readiness_v2_verification_context=readiness_verification_context[
                "readiness_v2_verification_context"
            ],
            trusted_clock_verification_context=readiness_verification_context[
                "trusted_clock_verification_context"
            ],
        )
        preregistration_verification = preregistration_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
            preregistration_document,
            preregistration_verification_context["preregistration_v3"],
            preregistration_verification_context["v3_verification_context"],
            preregistration_verification_context["current_implementation_sha256"],
        )
    except (ValueError, TypeError, KeyError):
        return None
    if readiness_verified is not True:
        return None
    if (
        type(preregistration_verification) is not dict
        or preregistration_verification.get("status") != "PASS"
        or preregistration_verification.get("preregistration_exactly_verified")
        is not True
    ):
        return None
    return readiness_document, preregistration_document


def _supports_observed_projection(
    readiness: dict[str, Any], preregistration: dict[str, Any]
) -> bool:
    readiness_summary = readiness.get("summary")
    readiness_facts = readiness.get("facts")
    gate = readiness.get("gate_outcomes", {}).get("signed_trusted_clock_authority")
    preregistration_facts = preregistration.get("facts")
    pins = preregistration.get("contract_pins")
    capabilities = preregistration.get("newly_pinned_local_capabilities")
    if (
        readiness.get("schema_version") != readiness_contract.SCHEMA_VERSION
        or readiness.get("static_fingerprint") != readiness_contract.STATIC_FINGERPRINT
        or readiness.get("status") != "UNKNOWN"
        or readiness.get("source_state") != readiness_contract.SOURCE_STATE
        or readiness.get("gap_state") != readiness_contract.GAP_STATE
        or readiness.get("maturity_state") != readiness_contract.MATURITY_STATE
        or readiness.get("permission_state") != readiness_contract.PERMISSION_STATE
        or not _has_locked_authority(readiness)
    ):
        return False
    if (
        type(readiness_summary) is not dict
        or readiness_summary
        != {
            "required_input_count": 14,
            "verified_input_count": 14,
            "unverified_input_count": 0,
            "not_supplied_input_count": 0,
        }
        or type(readiness_facts) is not dict
        or readiness_facts.get("signed_time_detached_signatures_verified") is not True
        or readiness_facts.get("signed_time_multi_authority_quorum_verified") is not True
        or readiness_facts.get("signed_time_external_authority_trust_verified") is not False
        or readiness_facts.get("current_time_established") is not False
        or type(gate) is not dict
        or type(gate.get("source_count")) is not int
        or gate["source_count"] < 2
    ):
        return False
    if (
        preregistration.get("schema_version") != preregistration_contract.SCHEMA_VERSION
        or preregistration.get("static_fingerprint")
        != preregistration_contract.STATIC_FINGERPRINT
        or preregistration.get("status") != "BLOCKED"
        or not _has_locked_authority(preregistration)
        or type(preregistration_facts) is not dict
        or preregistration_facts.get("readiness_envelope_v3_contract_pinned") is not True
        or preregistration_facts.get("readiness_envelope_v3_evidence_bound") is not False
        or preregistration_facts.get("readiness_envelope_v3_exactly_verified") is not False
        or type(pins) is not dict
        or pins.get("readiness_v3_schema_version") != readiness["schema_version"]
        or pins.get("readiness_v3_static_fingerprint")
        != readiness["static_fingerprint"]
        or pins.get("readiness_v3_maturity_state") != readiness["maturity_state"]
        or pins.get("readiness_v3_required_input_count") != 14
        or type(capabilities) is not list
        or len(capabilities) < 2
    ):
        return False
    readiness_capability = capabilities[-1]
    return (
        readiness_capability.get("capability")
        == "PORTFOLIO_RISK_SHADOW_INPUT_READINESS_ENVELOPE_V3"
        and readiness_capability.get("contract_pinned") is True
        and readiness_capability.get("evidence_bound") is False
        and readiness_capability.get("consumer_executed") is False
        and readiness_capability.get("external_authority_verified") is False
    )


def build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1(
    readiness_document: Any = None,
    preregistration_document: Any = None,
    *,
    readiness_verification_context: Any = None,
    preregistration_verification_context: Any = None,
) -> dict[str, Any]:
    """Build an observed, unknown, or not-supplied redacted projection."""

    if all(
        value is None
        for value in (
            readiness_document,
            preregistration_document,
            readiness_verification_context,
            preregistration_verification_context,
        )
    ):
        return _blank_projection("NOT_SUPPLIED")
    verified = _verify_sources(
        readiness_document,
        preregistration_document,
        readiness_verification_context,
        preregistration_verification_context,
    )
    if verified is None:
        return _blank_projection("UNKNOWN")
    readiness, preregistration = verified
    if not _supports_observed_projection(readiness, preregistration):
        return _blank_projection("UNKNOWN")

    readiness_hash = readiness.get("envelope_hash")
    preregistration_hash = preregistration.get("preregistration_hash")
    if (
        type(readiness_hash) is not str
        or _HASH_PATTERN.fullmatch(readiness_hash) is None
        or type(preregistration_hash) is not str
        or _HASH_PATTERN.fullmatch(preregistration_hash) is None
    ):
        return _blank_projection("UNKNOWN")
    clock_source_count = readiness["gate_outcomes"][
        "signed_trusted_clock_authority"
    ]["source_count"]
    return _seal(
        {
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "OBSERVED",
            "pipeline": _pipeline(SOURCE_STATE, GAP_STATE),
            "source": {
                "readiness_envelope_supplied": True,
                "readiness_envelope_exactly_verified": True,
                "readiness_schema_version": readiness["schema_version"],
                "readiness_envelope_hash": readiness_hash,
                "preregistration_supplied": True,
                "preregistration_exactly_verified": True,
                "preregistration_schema_version": preregistration["schema_version"],
                "preregistration_hash": preregistration_hash,
                "contract_pin_aligned": True,
                "readiness_evidence_bound_to_preregistration": False,
            },
            "summary": {
                "required_input_count": 14,
                "verified_input_count": 14,
                "signed_clock_source_count": clock_source_count,
                "closed_local_blocker_count": len(
                    preregistration["closed_local_blockers"]
                ),
                "readiness_blocker_count": len(readiness["blockers"]),
                "preregistration_blocker_count": len(preregistration["blockers"]),
                "preregistration_status": "BLOCKED",
                "contract_pin_aligned": True,
                "readiness_evidence_bound_to_preregistration": False,
                "consumer_executed": False,
                "external_time_authority_authenticated": False,
                "current_time_established": False,
            },
            "facts": {
                "source_documents_embedded": False,
                "verification_contexts_embedded": False,
                "public_keys_embedded": False,
                "signatures_embedded": False,
                "raw_receipts_embedded": False,
                "runtime_assets_accessed": False,
                "runtime_consumer_mounted": False,
                "risk_service_invoked": False,
                "natural_forward_chain_changed": False,
                "profitability_proof": False,
            },
            "authority": _authority(),
        }
    )


def verify_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1(
    document: Any,
    readiness_document: Any = None,
    preregistration_document: Any = None,
    *,
    readiness_verification_context: Any = None,
    preregistration_verification_context: Any = None,
) -> dict[str, Any]:
    """Rebuild the projection from all source inputs and compare exactly."""

    rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1(
        readiness_document,
        preregistration_document,
        readiness_verification_context=readiness_verification_context,
        preregistration_verification_context=preregistration_verification_context,
    )
    exact = type(document) is dict and document == rebuilt
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "FAIL",
        "projection_exactly_verified": exact,
        "projection_status": document.get("status") if type(document) is dict else None,
        "blockers": [] if exact else ["PUBLIC_PROJECTION_EXACT_REBUILD_MISMATCH"],
        "runtime_consumer_mounted": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "GAP_STATE",
    "MATURITY_STATE",
    "PERMISSION_STATE",
    "PROJECTION_SCHEMA_VERSION",
    "SOURCE_STATE",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1",
]
