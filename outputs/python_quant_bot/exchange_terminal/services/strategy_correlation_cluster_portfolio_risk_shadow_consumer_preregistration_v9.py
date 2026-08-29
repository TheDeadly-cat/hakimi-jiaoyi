"""Shadow preregistration v9 with an exact HTTP candidate closure."""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_presentation_candidate_v3
    as http_candidate_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
    as preregistration_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v9"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-preregistration-v9-http-candidate-lock-1"
)

V8_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "v7_verification_context",
        "registration_evidence_binding_verification_context",
        "successor_implementation_sha256",
    }
)
EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256 = {
    "shadow_preregistration_v8": (
        "01bee069cd249f5a2e4037893e20e64fbcb313be85e1ad04ff4918b25d2b7e29"
    ),
    "presentation_http_candidate_v3": (
        "59e6db95fbf62f5562c5731f9ba7cf55aea5833e1acef0bdb17705c85b7371e1"
    ),
}

_VERIFY_V8 = (
    preregistration_v8.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
)
_VERIFY_HTTP_CANDIDATE = (
    http_candidate_v3.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HTTP_VERSION_BLOCKER = "presentation_http_contract_v3_not_versioned"
_HTTP_TRANSPORT_BLOCKER = (
    "presentation_http_transport_unregistered_and_unexercised"
)
_HTTP_VERSION_ACTIVATION_STEP = (
    "VERSION_PRESENTATION_HTTP_CONTRACT_V3_BEFORE_MOUNT"
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or type(hash_field) is not str:
        return False
    supplied = document.get(hash_field)
    if not _is_hash(supplied):
        return False
    unhashed = copy.deepcopy(document)
    unhashed.pop(hash_field, None)
    try:
        expected = strict_canonical_hash(unhashed)
    except ValueError:
        return False
    return hmac.compare_digest(supplied, expected)


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


def _context_valid(context: Any) -> bool:
    return (
        type(context) is dict
        and frozenset(context) == V8_VERIFICATION_CONTEXT_KEYS
        and all(type(context[key]) is dict for key in V8_VERIFICATION_CONTEXT_KEYS)
    )


def _request_valid(request: Any) -> bool:
    return (
        type(request) is dict
        and frozenset(request)
        == frozenset(
            {
                "schema_version",
                "preregistration_v8_document",
                "preregistration_v7_document",
                "registration_evidence_binding_document",
            }
        )
        and request.get("schema_version") == http_candidate_v3.REQUEST_SCHEMA_VERSION
        and all(
            type(request.get(key)) is dict
            for key in (
                "preregistration_v8_document",
                "preregistration_v7_document",
                "registration_evidence_binding_document",
            )
        )
    )


def _v8_receipt_passed(receipt: Any) -> bool:
    if (
        type(receipt) is not dict
        or receipt.get("status") != "PASS"
        or receipt.get("preregistration_exactly_verified") is not True
        or receipt.get("preregistration_status") != "BLOCKED"
        or receipt.get("blockers") != []
    ):
        return False
    checks = receipt.get("checks")
    return (
        type(checks) is dict
        and bool(checks)
        and all(type(value) is bool and value is True for value in checks.values())
    )


def _call_v8_verifier(
    document: Any, request: Any, context: Any
) -> tuple[dict[str, Any], bool]:
    if not _request_valid(request) or not _context_valid(context):
        return {}, False
    try:
        receipt = _VERIFY_V8(
            copy.deepcopy(document),
            copy.deepcopy(request["preregistration_v7_document"]),
            copy.deepcopy(request["registration_evidence_binding_document"]),
            v7_verification_context=copy.deepcopy(
                context["v7_verification_context"]
            ),
            registration_evidence_binding_verification_context=copy.deepcopy(
                context["registration_evidence_binding_verification_context"]
            ),
            successor_implementation_sha256=copy.deepcopy(
                context["successor_implementation_sha256"]
            ),
        )
    except Exception:
        return {}, False
    return (receipt, _v8_receipt_passed(receipt)) if type(receipt) is dict else ({}, False)


def _call_http_verifier(response: Any, request: Any, context: Any) -> bool:
    if not _request_valid(request) or not _context_valid(context):
        return False
    try:
        return (
            _VERIFY_HTTP_CANDIDATE(
                copy.deepcopy(response),
                copy.deepcopy(request),
                v8_verification_context=copy.deepcopy(context),
            )
            is True
        )
    except Exception:
        return False


def _manifest_exact(value: Any) -> bool:
    if type(value) is not dict or set(value) != set(
        EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
    ):
        return False
    return all(
        _same_hash(value.get(key), expected)
        for key, expected in EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256.items()
    )


def _transport_locked(response: Any) -> bool:
    expected = {
        "registered": False,
        "externally_callable": False,
        "method": None,
        "route": None,
        "runtime_reads": False,
        "runtime_mutations": False,
        "cache_reads": False,
        "cache_writes": False,
    }
    return type(response) is dict and response.get("transport") == expected


def _http_response_presentable(response: Any) -> bool:
    if (
        type(response) is not dict
        or response.get("schema_version") != http_candidate_v3.RESPONSE_SCHEMA_VERSION
        or response.get("static_fingerprint") != http_candidate_v3.STATIC_FINGERPRINT
        or response.get("interface_status") != "UNREGISTERED_CANDIDATE"
        or response.get("state") != "KNOWN_BLOCKED"
        or not _sealed_hash_exact(response, "response_hash")
        or response.get("blockers") != ["SOURCE_PREREGISTRATION_BLOCKED"]
        or not _transport_locked(response)
        or not _authority_locked(response)
    ):
        return False
    payload = response.get("payload")
    facts = response.get("facts")
    lineage = response.get("lineage")
    if not all(type(value) is dict for value in (payload, facts, lineage)):
        return False
    summary = payload.get("summary")
    stages = payload.get("stages")
    return (
        payload.get("schema_version") == http_candidate_v3.PAYLOAD_SCHEMA_VERSION
        and payload.get("presentation_status") == "UNMOUNTED_HTTP_CANDIDATE"
        and payload.get("axis_order") == list(http_candidate_v3.AXIS_ORDER)
        and type(stages) is list
        and [stage.get("axis") for stage in stages if type(stage) is dict]
        == list(http_candidate_v3.AXIS_ORDER)
        and stages[-1].get("state") == "UNAUTHORIZED"
        and type(summary) is dict
        and summary.get("contract_state") == "KNOWN"
        and summary.get("public_status") == "BLOCKED"
        and summary.get("implementation_pin_count") == 39
        and summary.get("closed_local_blocker_count") == 5
        and summary.get("registration_activated") is False
        and facts.get("source_preregistration_verified") is True
        and facts.get("route_registered") is False
        and facts.get("runtime_mutations_performed") is False
        and facts.get("profitability_proven") is False
        and lineage.get("request_documents_embedded") is False
        and lineage.get("verification_context_embedded") is False
        and _same_hash(
            lineage.get("source_preregistration_implementation_sha256"),
            EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                "shadow_preregistration_v8"
            ],
        )
    )


def _checks(
    preregistration_v8_document: Any,
    http_candidate_response: Any,
    http_candidate_request: Any,
    *,
    v8_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, bool]:
    context_exact = _context_valid(v8_verification_context)
    request_exact = _request_valid(http_candidate_request)
    _receipt, v8_exact = _call_v8_verifier(
        preregistration_v8_document,
        http_candidate_request,
        v8_verification_context,
    )
    http_exact = _call_http_verifier(
        http_candidate_response,
        http_candidate_request,
        v8_verification_context,
    )
    request_v8 = (
        http_candidate_request.get("preregistration_v8_document")
        if request_exact
        else None
    )
    response_lineage = (
        http_candidate_response.get("lineage")
        if type(http_candidate_response) is dict
        else None
    )
    return {
        "v8_verification_context_exact": context_exact,
        "http_candidate_request_exact": request_exact,
        "immutable_v8_exactly_verified": v8_exact,
        "http_candidate_response_exactly_verified": http_exact,
        "successor_implementation_manifest_exact": _manifest_exact(
            successor_implementation_sha256
        ),
        "immutable_v8_known_and_blocked": (
            type(preregistration_v8_document) is dict
            and preregistration_v8_document.get("schema_version")
            == preregistration_v8.SCHEMA_VERSION
            and preregistration_v8_document.get("contract_state") == "KNOWN"
            and preregistration_v8_document.get("status") == "BLOCKED"
        ),
        "request_v8_document_identity": (
            type(request_v8) is dict and request_v8 == preregistration_v8_document
        ),
        "http_candidate_response_presentable": _http_response_presentable(
            http_candidate_response
        ),
        "http_candidate_response_seal_exact": _sealed_hash_exact(
            http_candidate_response, "response_hash"
        ),
        "http_candidate_v8_hash_identity": (
            type(response_lineage) is dict
            and _same_hash(
                response_lineage.get("source_preregistration_hash"),
                preregistration_v8_document.get("preregistration_hash")
                if type(preregistration_v8_document) is dict
                else None,
            )
        ),
        "http_transport_remains_unregistered": _transport_locked(
            http_candidate_response
        ),
        "all_source_authority_locked": (
            _authority_locked(preregistration_v8_document)
            and _authority_locked(http_candidate_response)
        ),
        "source_hashes_valid": (
            type(preregistration_v8_document) is dict
            and _is_hash(preregistration_v8_document.get("preregistration_hash"))
            and type(http_candidate_response) is dict
            and _is_hash(http_candidate_response.get("response_hash"))
        ),
    }


def _remaining_blockers(v8: Any, known: bool) -> list[Any]:
    source = v8.get("blockers") if type(v8) is dict else None
    result = copy.deepcopy(source) if type(source) is list else []
    if not known:
        return result
    result = [item for item in result if item != _HTTP_VERSION_BLOCKER]
    if _HTTP_TRANSPORT_BLOCKER not in result:
        result.append(_HTTP_TRANSPORT_BLOCKER)
    return result


def _closed_local_blockers(v8: Any, response_hash: Any, known: bool) -> list[Any]:
    source = v8.get("closed_local_blockers") if type(v8) is dict else None
    result = copy.deepcopy(source) if type(source) is list else []
    if known:
        result.append(
            {
                "blocker": _HTTP_VERSION_BLOCKER,
                "closure": (
                    "ADR0199_UNREGISTERED_HTTP_CANDIDATE_V3_EXACTLY_VERSIONED_"
                    "NO_ROUTE"
                ),
                "closure_verified": True,
                "http_candidate_response_sha256": response_hash,
            }
        )
    return result


def _refinements(v8: Any, known: bool) -> list[Any]:
    source = v8.get("blocker_refinements") if type(v8) is dict else None
    result = copy.deepcopy(source) if type(source) is list else []
    if not known:
        return result
    for refinement in result:
        if type(refinement) is not dict:
            continue
        remaining = refinement.get("remaining_requirements")
        if type(remaining) is list and _HTTP_VERSION_BLOCKER in remaining:
            refinement["remaining_requirements"] = [
                _HTTP_TRANSPORT_BLOCKER if item == _HTTP_VERSION_BLOCKER else item
                for item in remaining
            ]
            refinement["local_contract_state"] = (
                "ADR0199_HTTP_CANDIDATE_V3_VERSIONED_TRANSPORT_UNREGISTERED"
            )
    return result


def _activation_order(v8: Any, known: bool) -> list[Any]:
    source = v8.get("activation_order") if type(v8) is dict else None
    result = copy.deepcopy(source) if type(source) is list else []
    if not known:
        return result
    return [item for item in result if item != _HTTP_VERSION_ACTIVATION_STEP]


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
    preregistration_v8_document: Any,
    http_candidate_response: Any,
    http_candidate_request: Any,
    *,
    v8_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    checks = _checks(
        preregistration_v8_document,
        http_candidate_response,
        http_candidate_request,
        v8_verification_context=v8_verification_context,
        successor_implementation_sha256=successor_implementation_sha256,
    )
    known = all(checks.values())
    v8_facts = (
        preregistration_v8_document.get("facts")
        if type(preregistration_v8_document) is dict
        else None
    )
    predecessor_pin_count = (
        v8_facts.get("implementation_pin_count")
        if type(v8_facts) is dict
        else None
    )
    total_pin_count = (
        predecessor_pin_count + len(EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)
        if type(predecessor_pin_count) is int
        and type(predecessor_pin_count) is not bool
        else None
    )
    response_hash = (
        http_candidate_response.get("response_hash")
        if type(http_candidate_response) is dict
        else None
    )
    closed = _closed_local_blockers(
        preregistration_v8_document, response_hash, known
    )
    reuse = (
        copy.deepcopy(preregistration_v8_document.get("reuse_plan"))
        if type(preregistration_v8_document) is dict
        and type(preregistration_v8_document.get("reuse_plan")) is list
        else []
    )
    if known:
        reuse.append(
            {
                "capability": "PRESENTATION_HTTP_CANDIDATE_V3",
                "decision": (
                    "REUSE_ADR0199_EXACT_UNREGISTERED_CANDIDATE_NO_TRANSPORT"
                ),
            }
        )

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "contract_state": "KNOWN" if known else "UNKNOWN",
        "decision": (
            "SUCCESSOR_PREREGISTERED_HTTP_CANDIDATE_V3_VERSIONED_TRANSPORT_"
            "REVIEW_DOM_BROWSER_MOUNT_CURRENT_UNAUTHORIZED"
            if known
            else "SUCCESSOR_PREREGISTRATION_BLOCKED_EXACT_HTTP_CANDIDATE_"
            "CLOSURE_NOT_PROVEN"
        ),
        "source": {
            "immutable_v8_exactly_verified": checks[
                "immutable_v8_exactly_verified"
            ],
            "immutable_v8_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v8"
                ]
            ),
            "immutable_v8_preregistration_hash": (
                preregistration_v8_document.get("preregistration_hash")
                if type(preregistration_v8_document) is dict
                else None
            ),
            "http_candidate_response_exactly_verified": checks[
                "http_candidate_response_exactly_verified"
            ],
            "http_candidate_response_sha256": response_hash,
            "successor_manifest_contract_verified": checks[
                "successor_implementation_manifest_exact"
            ],
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": 2,
            "total_implementation_pin_count": total_pin_count,
            "new_artifacts": [
                {
                    "artifact_id": "shadow_preregistration_v8",
                    "path": (
                        "exchange_terminal/services/strategy_correlation_cluster_"
                        "portfolio_risk_shadow_consumer_preregistration_v8.py"
                    ),
                    "expected_sha256": EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "shadow_preregistration_v8"
                    ],
                },
                {
                    "artifact_id": "presentation_http_candidate_v3",
                    "path": (
                        "exchange_terminal/interfaces/http/strategy_correlation_"
                        "cluster_portfolio_risk_presentation_candidate_v3.py"
                    ),
                    "expected_sha256": EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "presentation_http_candidate_v3"
                    ],
                },
            ],
            "verification_checks": checks,
        },
        "contract_pins": {
            "immutable_v8_contract_pins": copy.deepcopy(
                preregistration_v8_document.get("contract_pins")
                if type(preregistration_v8_document) is dict
                else None
            ),
            "immutable_v8_schema_version": preregistration_v8.SCHEMA_VERSION,
            "immutable_v8_static_fingerprint": preregistration_v8.STATIC_FINGERPRINT,
            "immutable_v8_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v8"
                ]
            ),
            "http_candidate_request_schema_version": (
                http_candidate_v3.REQUEST_SCHEMA_VERSION
            ),
            "http_candidate_payload_schema_version": (
                http_candidate_v3.PAYLOAD_SCHEMA_VERSION
            ),
            "http_candidate_response_schema_version": (
                http_candidate_v3.RESPONSE_SCHEMA_VERSION
            ),
            "http_candidate_static_fingerprint": http_candidate_v3.STATIC_FINGERPRINT,
            "http_candidate_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "presentation_http_candidate_v3"
                ]
            ),
            "http_candidate_interface_status": "UNREGISTERED_CANDIDATE",
            "http_transport_policy": (
                "NO_METHOD_NO_ROUTE_NO_RUNTIME_OR_CACHE_IO_V1"
            ),
        },
        "required_shadow_input_schemas": copy.deepcopy(
            preregistration_v8_document.get("required_shadow_input_schemas", [])
            if type(preregistration_v8_document) is dict
            else []
        ),
        "closed_local_blockers": closed,
        "blocker_refinements": _refinements(preregistration_v8_document, known),
        "blockers": _remaining_blockers(preregistration_v8_document, known),
        "reuse_plan": reuse,
        "activation_order": _activation_order(preregistration_v8_document, known),
        "facts": {
            "immutable_v8_exactly_verified": checks[
                "immutable_v8_exactly_verified"
            ],
            "http_candidate_response_exactly_verified": checks[
                "http_candidate_response_exactly_verified"
            ],
            "required_shadow_input_count": (
                v8_facts.get("required_shadow_input_count", 0)
                if type(v8_facts) is dict
                else 0
            ),
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": 2,
            "implementation_pin_count": total_pin_count,
            "closed_local_blocker_count": len(closed),
            "local_evidence_closure_count": (
                v8_facts.get("local_evidence_closure_count", 0)
                if type(v8_facts) is dict
                else 0
            ),
            "local_http_contract_closure_count": 1 if known else 0,
            "consumer_fixture_v3_execution_evidence_bound": known,
            "presentation_registration_v1_evidence_bound": known,
            "presentation_registration_v1_activated": False,
            "presentation_http_contract_v3_versioned": known,
            "presentation_http_transport_registered": False,
            "presentation_http_transport_exercised": False,
            "render_descriptor_independently_reviewed": False,
            "dom_contract_v3_reviewed": False,
            "browser_visual_review_v3_performed": False,
            "server_route_registered": False,
            "ui_mounted": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "writer_allowed": False,
            "migration_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_mount_allowed": False,
            "http_route_registration_allowed": False,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
    document: Any,
    preregistration_v8_document: Any,
    http_candidate_response: Any,
    http_candidate_request: Any,
    *,
    v8_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        verified = False
    else:
        try:
            rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
                preregistration_v8_document,
                http_candidate_response,
                http_candidate_request,
                v8_verification_context=v8_verification_context,
                successor_implementation_sha256=successor_implementation_sha256,
            )
            verified = (
                strict_json_contract_equal(document, rebuilt)
                and document.get("schema_version") == SCHEMA_VERSION
                and document.get("status") == "BLOCKED"
                and document.get("contract_state") == "KNOWN"
                and _authority_locked(document)
            )
        except Exception:
            verified = False
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if verified else "BLOCK",
        "preregistration_exactly_verified": verified,
        "preregistration_status": "BLOCKED" if verified else "UNKNOWN",
        "blockers": [] if verified else ["preregistration_v9_exact_rebuild"],
        "writer_allowed": False,
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V8_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9",
]
