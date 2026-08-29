"""Unregistered, summary-only HTTP candidate for preregistration-v10.

The interface has no method, route, runtime I/O, or mount.  It fully reverifies
the immutable v10 source and projects a neutral SOURCE/GAP/MATURITY/PERMISSION
payload without exposing source documents or verification contexts.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10
    as preregistration_v10,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-"
    "request-v4"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v4"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-"
    "response-v4"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-presentation-http-unregistered-candidate-4"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
V10_IMPLEMENTATION_SHA256 = (
    "47461f4ce12904723097eba1ef85875375696fa8ed2661ed2ca9255ec9b717a7"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "preregistration_v10_document",
        "preregistration_v9_document",
        "signed_review_evidence_document",
        "execution_evidence_binding_v2_document",
    }
)
_V10_CONTEXT_FIELDS = frozenset(
    {
        "v9_verification_context",
        "signed_review_evidence_verification_context",
        "execution_binding_verification_context",
        "successor_implementation_sha256",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFY_V10 = (
    preregistration_v10.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _sealed_hash_exact(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(hash_field)):
        return False
    unhashed = copy.deepcopy(document)
    supplied = unhashed.pop(hash_field)
    try:
        expected = strict_canonical_hash(unhashed)
    except ValueError:
        return False
    return hmac.compare_digest(supplied, expected)


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
        "signed_review_claim_bound": False,
        "reviewed_descriptor_matches_executed_fixture": False,
        "execution_binding_v2_bound": False,
        "external_independent_review_completed": False,
        "execution_provenance_authenticated": False,
        "transport_registered": False,
        "route_registered": False,
        "ui_mounted": False,
        "runtime_mutations_performed": False,
        "profitability_proven": False,
    }


def _lineage(*, source_bound: bool, source_hash: str | None = None) -> dict[str, Any]:
    return {
        "source_preregistration_schema_version": (
            preregistration_v10.SCHEMA_VERSION if source_bound else None
        ),
        "source_preregistration_static_fingerprint": (
            preregistration_v10.STATIC_FINGERPRINT if source_bound else None
        ),
        "source_preregistration_implementation_sha256": (
            V10_IMPLEMENTATION_SHA256 if source_bound else None
        ),
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_IMPLEMENTATION_SHA256 if source_bound else None
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
        and all(
            type(request_payload.get(field)) is dict
            for field in _REQUEST_FIELDS
            if field != "schema_version"
        )
    )


def _context_valid(context: Any) -> bool:
    return (
        type(context) is dict
        and frozenset(context) == _V10_CONTEXT_FIELDS
        and all(type(context[field]) is dict for field in _V10_CONTEXT_FIELDS)
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
    if (
        type(checks) is not dict
        or not checks
        or not all(type(value) is bool and value is True for value in checks.values())
    ):
        return False
    return all(
        value is False
        for key, value in receipt.items()
        if type(key) is str
        and (key.endswith("_allowed") or key.endswith("_authorized"))
    )


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and bool(authority)
        and authority.get("descriptive_only") is True
        and all(type(value) is bool for value in authority.values())
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _v10_presentable(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != preregistration_v10.SCHEMA_VERSION
        or document.get("static_fingerprint")
        != preregistration_v10.STATIC_FINGERPRINT
        or document.get("status") != "BLOCKED"
        or document.get("contract_state") != "KNOWN"
        or not _sealed_hash_exact(document, "preregistration_hash")
        or not _authority_locked(document)
    ):
        return False
    facts = document.get("facts")
    blockers = document.get("blockers")
    shadow_inputs = document.get("required_shadow_input_schemas")
    evidence_schemas = document.get("required_presentation_evidence_schemas")
    activation_order = document.get("activation_order")
    if not all(
        type(value) is list
        for value in (blockers, shadow_inputs, evidence_schemas, activation_order)
    ) or type(facts) is not dict:
        return False
    required_blockers = {
        "provider_trust_unproven",
        "external_independent_review_not_completed",
        "external_fixture_artifact_attestation_unproven",
        "presentation_http_transport_unregistered_and_unexercised",
    }
    return (
        len(shadow_inputs) == 14
        and evidence_schemas
        == [
            preregistration_v10.signed_review_v1.EVIDENCE_SCHEMA_VERSION,
            preregistration_v10.execution_binding_v2.SCHEMA,
        ]
        and activation_order == list(preregistration_v10.ACTIVATION_ORDER)
        and required_blockers.issubset(set(blockers))
        and facts.get("implementation_pin_count") == 45
        and facts.get("closed_local_blocker_count") == 8
        and facts.get("local_evidence_closure_count") == 4
        and facts.get("signed_review_claim_cryptographically_verified") is True
        and facts.get("reviewed_descriptor_matches_executed_fixture") is True
        and facts.get("render_descriptor_independently_reviewed") is False
        and facts.get("execution_binding_v2_exactly_verified") is True
        and facts.get("consumer_fixture_v4_execution_evidence_bound") is True
        and facts.get("external_fixture_artifact_attestation_verified") is False
        and facts.get("fixture_execution_process_identity_authenticated") is False
        and facts.get("fixture_execution_receipt_signed") is False
        and facts.get("presentation_registration_v2_activated") is False
        and facts.get("stylesheet_contract_reviewed") is False
        and facts.get("dom_contract_reviewed") is False
        and facts.get("browser_visual_review_performed") is False
        and facts.get("presentation_http_transport_registered") is False
        and facts.get("presentation_http_transport_exercised") is False
        and facts.get("ui_mounted") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("current_pointer_written") is False
        and facts.get("profitability_proven") is False
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
            "implementation_sha256": V10_IMPLEMENTATION_SHA256,
        },
        "stages": [
            {
                "axis": "SOURCE",
                "state": "VERIFIED",
                "detail": "V10_EXACT_REBUILD",
            },
            {
                "axis": "GAP",
                "state": "PRESENT",
                "detail": (
                    "EXTERNAL_TRUST_REVIEW_EXECUTION_TRANSPORT_AND_MOUNT_GAPS"
                ),
            },
            {
                "axis": "MATURITY",
                "state": "LOCAL_EVIDENCE_BOUND",
                "detail": (
                    "SIGNED_CLAIM_AND_LOCAL_EXECUTION_BINDING_V2_BOUND_ONLY"
                ),
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
            "required_shadow_input_count": len(
                document["required_shadow_input_schemas"]
            ),
            "required_presentation_evidence_count": len(
                document["required_presentation_evidence_schemas"]
            ),
            "implementation_pin_count": facts["implementation_pin_count"],
            "closed_local_blocker_count": facts["closed_local_blocker_count"],
            "local_evidence_closure_count": facts[
                "local_evidence_closure_count"
            ],
            "remaining_blocker_count": len(blockers),
            "remaining_blockers": copy.deepcopy(blockers),
            "signed_review_claim_verified": True,
            "independent_review_completed": False,
            "execution_binding_v2_verified": True,
            "descriptor_cross_binding_verified": True,
            "registration_activated": False,
        },
        "facts": {
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "signed_review_claim_bound": True,
            "external_independent_review_completed": False,
            "execution_binding_v2_bound": True,
            "execution_provenance_authenticated": False,
            "descriptor_cross_binding_verified": True,
            "http_candidate_versioned": True,
            "http_route_registered": False,
            "ui_mounted": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }


def build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
    request_payload: Any,
    *,
    v10_verification_context: Any,
) -> dict[str, Any]:
    """Build a side-effect-free candidate response from an exact v10 request."""

    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")
    if not _context_valid(v10_verification_context):
        return _unknown("VERIFICATION_CONTEXT_INVALID")

    v10_document = request_payload["preregistration_v10_document"]
    try:
        receipt = _VERIFY_V10(
            copy.deepcopy(v10_document),
            copy.deepcopy(request_payload["preregistration_v9_document"]),
            copy.deepcopy(request_payload["signed_review_evidence_document"]),
            copy.deepcopy(
                request_payload["execution_evidence_binding_v2_document"]
            ),
            v9_verification_context=copy.deepcopy(
                v10_verification_context["v9_verification_context"]
            ),
            signed_review_evidence_verification_context=copy.deepcopy(
                v10_verification_context[
                    "signed_review_evidence_verification_context"
                ]
            ),
            execution_binding_verification_context=copy.deepcopy(
                v10_verification_context[
                    "execution_binding_verification_context"
                ]
            ),
            successor_implementation_sha256=copy.deepcopy(
                v10_verification_context["successor_implementation_sha256"]
            ),
        )
    except Exception:
        return _unknown("SOURCE_PREREGISTRATION_VERIFIER_ERROR")
    if not _verification_passed(receipt) or not _v10_presentable(v10_document):
        return _unknown("SOURCE_PREREGISTRATION_UNVERIFIED")

    facts = _facts()
    facts.update(
        {
            "request_contract_valid": True,
            "source_preregistration_verified": True,
            "source_contract_state_known": True,
            "result_available": True,
            "signed_review_claim_bound": True,
            "reviewed_descriptor_matches_executed_fixture": True,
            "execution_binding_v2_bound": True,
        }
    )
    return _sealed(
        state=KNOWN_BLOCKED_STATE,
        payload=_payload(v10_document),
        facts=facts,
        lineage=_lineage(
            source_bound=True,
            source_hash=v10_document["preregistration_hash"],
        ),
        blockers=["SOURCE_PREREGISTRATION_BLOCKED"],
    )


def verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
    document: Any,
    request_payload: Any,
    *,
    v10_verification_context: Any,
) -> bool:
    """Rebuild the response exactly without accepting a transport alias."""

    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
            request_payload,
            v10_verification_context=v10_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "AXIS_ORDER",
    "INTERFACE_STATUS",
    "KNOWN_BLOCKED_STATE",
    "PAYLOAD_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "UNKNOWN_STATE",
    "V10_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4",
]
