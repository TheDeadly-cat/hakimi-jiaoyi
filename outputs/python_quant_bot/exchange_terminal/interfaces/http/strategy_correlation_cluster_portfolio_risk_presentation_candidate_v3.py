"""Unregistered HTTP candidate for the portfolio-risk v3 presentation."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
    as preregistration_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-"
    "request-v3"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v3"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-"
    "response-v3"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-presentation-http-unregistered-candidate-3"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
V8_IMPLEMENTATION_SHA256 = (
    "01bee069cd249f5a2e4037893e20e64fbcb313be85e1ad04ff4918b25d2b7e29"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "preregistration_v8_document",
        "preregistration_v7_document",
        "registration_evidence_binding_document",
    }
)
_V8_CONTEXT_FIELDS = frozenset(
    {
        "v7_verification_context",
        "registration_evidence_binding_verification_context",
        "successor_implementation_sha256",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFY_V8 = (
    preregistration_v8.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _transport() -> dict[str, Any]:
    return {
        "registered": False,
        "externally_callable": False,
        "method": None,
        "route": None,
        "runtime_reads": False,
        "runtime_mutations": False,
        "cache_reads": False,
        "cache_writes": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "route_registration_allowed": False,
        "consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "request_contract_valid": False,
        "source_preregistration_verified": False,
        "source_contract_state_known": False,
        "result_available": False,
        "presentation_http_contract_candidate_versioned": True,
        "transport_registered": False,
        "route_registered": False,
        "ui_mounted": False,
        "runtime_mutations_performed": False,
        "profitability_proven": False,
    }


def _lineage(*, source_bound: bool, source_hash: str | None = None) -> dict[str, Any]:
    return {
        "source_preregistration_schema_version": (
            preregistration_v8.SCHEMA_VERSION if source_bound else None
        ),
        "source_preregistration_static_fingerprint": (
            preregistration_v8.STATIC_FINGERPRINT if source_bound else None
        ),
        "source_preregistration_implementation_sha256": (
            V8_IMPLEMENTATION_SHA256 if source_bound else None
        ),
        "source_preregistration_hash": source_hash if source_bound else None,
        "request_documents_embedded": False,
        "verification_context_embedded": False,
    }


def _sealed(
    *,
    state: str,
    payload: dict[str, Any] | None,
    facts: dict[str, bool],
    lineage: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "interface_status": INTERFACE_STATUS,
            "state": state,
            "payload": payload,
            "facts": facts,
            "lineage": lineage,
            "transport": _transport(),
            "authority": _authority(),
            "blockers": blockers,
        },
        "response_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed(
        state=UNKNOWN_STATE,
        payload=None,
        facts=_facts(),
        lineage=_lineage(source_bound=False),
        blockers=[reason],
    )


def _request_valid(request_payload: Any) -> bool:
    return (
        type(request_payload) is dict
        and frozenset(request_payload) == _REQUEST_FIELDS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and type(request_payload.get("preregistration_v8_document")) is dict
        and type(request_payload.get("preregistration_v7_document")) is dict
        and type(request_payload.get("registration_evidence_binding_document"))
        is dict
    )


def _context_valid(context: Any) -> bool:
    return (
        type(context) is dict
        and frozenset(context) == _V8_CONTEXT_FIELDS
        and all(type(context[field]) is dict for field in _V8_CONTEXT_FIELDS)
    )


def _verification_passed(receipt: Any) -> bool:
    if (
        type(receipt) is not dict
        or receipt.get("status") != "PASS"
        or receipt.get("preregistration_exactly_verified") is not True
        or receipt.get("preregistration_status") != "BLOCKED"
        or receipt.get("blockers") != []
    ):
        return False
    checks = receipt.get("checks")
    if type(checks) is not dict or not checks:
        return False
    if not all(type(value) is bool and value is True for value in checks.values()):
        return False
    for key, value in receipt.items():
        if (
            type(key) is str
            and (key.endswith("_allowed") or key.endswith("_authorized"))
            and value is not False
        ):
            return False
    return True


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    if type(authority) is not dict or not authority:
        return False
    for key, value in authority.items():
        if type(key) is not str or type(value) is not bool:
            return False
        if key == "descriptive_only":
            if value is not True:
                return False
        elif value is not False:
            return False
    return True


def _v8_presentable(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != preregistration_v8.SCHEMA_VERSION
        or document.get("static_fingerprint")
        != preregistration_v8.STATIC_FINGERPRINT
        or document.get("status") != "BLOCKED"
        or document.get("contract_state") != "KNOWN"
        or not _is_hash(document.get("preregistration_hash"))
        or not _authority_locked(document)
    ):
        return False
    facts = document.get("facts")
    blockers = document.get("blockers")
    if type(facts) is not dict or type(blockers) is not list:
        return False
    return (
        facts.get("local_evidence_closure_count") == 2
        and facts.get("required_shadow_input_count") == 14
        and facts.get("implementation_pin_count") == 39
        and facts.get("closed_local_blocker_count") == 5
        and facts.get("consumer_fixture_v3_execution_evidence_bound") is True
        and facts.get("presentation_registration_v1_evidence_bound") is True
        and facts.get("presentation_registration_v1_activated") is False
        and facts.get("render_descriptor_independently_reviewed") is False
        and facts.get("presentation_http_contract_v3_versioned") is False
        and facts.get("ui_mounted") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("profitability_proven") is False
        and "presentation_render_descriptor_independent_review_missing" in blockers
        and "presentation_consumer_registration_activation_unauthorized" in blockers
    )


def _payload(document: dict[str, Any]) -> dict[str, Any]:
    facts = document["facts"]
    blockers = document["blockers"]
    return {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "presentation_status": "UNMOUNTED_HTTP_CANDIDATE",
        "axis_order": list(AXIS_ORDER),
        "source": {
            "schema_version": document["schema_version"],
            "static_fingerprint": document["static_fingerprint"],
            "preregistration_hash": document["preregistration_hash"],
            "implementation_sha256": V8_IMPLEMENTATION_SHA256,
        },
        "stages": [
            {
                "axis": "SOURCE",
                "state": "VERIFIED",
                "detail": "V8_EXACT_REBUILD",
            },
            {
                "axis": "GAP",
                "state": "PRESENT",
                "detail": "INDEPENDENT_REVIEW_HTTP_ROUTE_AND_ACTIVATION_GAPS",
            },
            {
                "axis": "MATURITY",
                "state": "LOCAL_EVIDENCE_BOUND",
                "detail": "FIXTURE_AND_REGISTRATION_EVIDENCE_BOUND_LOCAL_ONLY",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
            },
        ],
        "summary": {
            "contract_state": document["contract_state"],
            "public_status": document["status"],
            "required_shadow_input_count": facts["required_shadow_input_count"],
            "implementation_pin_count": facts["implementation_pin_count"],
            "closed_local_blocker_count": facts["closed_local_blocker_count"],
            "local_evidence_closure_count": facts["local_evidence_closure_count"],
            "remaining_blockers": copy.deepcopy(blockers),
            "registration_activated": False,
        },
        "facts": {
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "independent_review_completed": False,
            "http_candidate_versioned": True,
            "http_route_registered": False,
            "ui_mounted": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }


def build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
    request_payload: Any,
    *,
    v8_verification_context: Any,
) -> dict[str, Any]:
    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")
    if not _context_valid(v8_verification_context):
        return _unknown("VERIFICATION_CONTEXT_INVALID")

    v8_document = request_payload["preregistration_v8_document"]
    try:
        receipt = _VERIFY_V8(
            v8_document,
            request_payload["preregistration_v7_document"],
            request_payload["registration_evidence_binding_document"],
            v7_verification_context=v8_verification_context[
                "v7_verification_context"
            ],
            registration_evidence_binding_verification_context=(
                v8_verification_context[
                    "registration_evidence_binding_verification_context"
                ]
            ),
            successor_implementation_sha256=v8_verification_context[
                "successor_implementation_sha256"
            ],
        )
    except Exception:
        return _unknown("SOURCE_PREREGISTRATION_VERIFIER_ERROR")
    if not _verification_passed(receipt) or not _v8_presentable(v8_document):
        return _unknown("SOURCE_PREREGISTRATION_UNVERIFIED")

    facts = _facts()
    facts.update(
        {
            "request_contract_valid": True,
            "source_preregistration_verified": True,
            "source_contract_state_known": True,
            "result_available": True,
        }
    )
    return _sealed(
        state=KNOWN_BLOCKED_STATE,
        payload=_payload(v8_document),
        facts=facts,
        lineage=_lineage(
            source_bound=True,
            source_hash=v8_document["preregistration_hash"],
        ),
        blockers=["SOURCE_PREREGISTRATION_BLOCKED"],
    )


def verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
    document: Any,
    request_payload: Any,
    *,
    v8_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
            request_payload,
            v8_verification_context=v8_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "REQUEST_SCHEMA_VERSION",
    "PAYLOAD_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "INTERFACE_STATUS",
    "KNOWN_BLOCKED_STATE",
    "UNKNOWN_STATE",
    "V8_IMPLEMENTATION_SHA256",
    "AXIS_ORDER",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3",
]
