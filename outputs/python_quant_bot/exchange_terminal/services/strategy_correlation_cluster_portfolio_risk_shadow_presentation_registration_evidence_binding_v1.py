"""Bind local fixture execution evidence to a registration candidate.

The result is detached successor evidence only.  It never activates the
registration candidate, mounts a consumer, changes current, or grants runtime,
paper, or live authority.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
    as registration_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
    as execution_binding_v1,
)


SCHEMA = (
    "strategy-correlation-cluster-portfolio-risk-shadow-presentation-"
    "registration-evidence-binding-v1"
)
VERIFICATION_SCHEMA = f"{SCHEMA}-verification-v1"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-presentation-registration-evidence-lock-1"
)

EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "fixture_execution_evidence",
        "preregistration_v7_verification_context",
        "fixture_execution_evidence_verification_context",
        "current_implementation_sha256",
    }
)
REGISTRATION_VERIFICATION_CONTEXT_KEYS = frozenset(
    {"current_implementation_sha256"}
)

EXPECTED_IMPLEMENTATION_SHA256 = {
    "presentation_execution_evidence_binding_v1": (
        "b40e50db01e5bb5d6c8c19944f46edceca3a1c420cfb519a5ecf68f50c8d855d"
    ),
    "presentation_registration_candidate_v1": (
        "6a5b4cd9a8a0e3552ec34b355c9a27f4560b5621557d605413aa8076c769cc7e"
    ),
}

_VERIFY_EXECUTION_BINDING = getattr(
    execution_binding_v1,
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_"
    "execution_evidence_binding_v1",
    None,
)
_VERIFY_REGISTRATION = getattr(
    registration_v1,
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_"
    "registration_v1",
    None,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MISSING = object()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _path(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if type(current) is not dict or key not in current:
            return _MISSING
        current = current[key]
    return current


def _hash_at(value: Any, *keys: str) -> str | None:
    candidate = _path(value, *keys)
    return candidate if _is_hash(candidate) else None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _exact_context(value: Any, keys: frozenset[str]) -> bool:
    return type(value) is dict and frozenset(value) == keys


def _authority_locked(document: Any) -> bool:
    authority = _path(document, "authority")
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


def _verification_passed(receipt: Any) -> bool:
    if type(receipt) is not dict or receipt.get("status") != "PASS":
        return False
    blockers = receipt.get("blockers", [])
    if type(blockers) is not list or blockers:
        return False

    proof_markers: list[bool] = []
    if "verified" in receipt:
        proof_markers.append(receipt["verified"] is True)
    for key, value in receipt.items():
        if type(key) is str and key.endswith("_exactly_verified"):
            proof_markers.append(value is True)
    checks = receipt.get("checks")
    if checks is not None:
        if type(checks) is not dict or not checks:
            return False
        proof_markers.append(
            all(type(value) is bool and value is True for value in checks.values())
        )
    for key, value in receipt.items():
        if (
            type(key) is str
            and (
                key.endswith("_allowed")
                or key.endswith("_authorized")
                or key == "current_pointer_written"
            )
            and value is not False
        ):
            return False
    return bool(proof_markers) and all(proof_markers)


def _call_execution_binding_verifier(
    document: Any,
    preregistration_v7_document: Any,
    context: Any,
) -> tuple[dict[str, Any], bool]:
    if not _exact_context(
        context, EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS
    ) or not callable(_VERIFY_EXECUTION_BINDING):
        return {}, False
    try:
        receipt = _VERIFY_EXECUTION_BINDING(
            copy.deepcopy(document),
            copy.deepcopy(preregistration_v7_document),
            copy.deepcopy(context["fixture_execution_evidence"]),
            preregistration_v7_verification_context=copy.deepcopy(
                context["preregistration_v7_verification_context"]
            ),
            fixture_execution_evidence_verification_context=copy.deepcopy(
                context["fixture_execution_evidence_verification_context"]
            ),
            current_implementation_sha256=copy.deepcopy(
                context["current_implementation_sha256"]
            ),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _call_registration_verifier(
    document: Any, context: Any
) -> tuple[dict[str, Any], bool]:
    if not _exact_context(
        context, REGISTRATION_VERIFICATION_CONTEXT_KEYS
    ) or not callable(_VERIFY_REGISTRATION):
        return {}, False
    try:
        receipt = _VERIFY_REGISTRATION(
            copy.deepcopy(document),
            copy.deepcopy(context["current_implementation_sha256"]),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _implementation_manifest_exact(value: Any) -> bool:
    if type(value) is not dict or set(value) != set(EXPECTED_IMPLEMENTATION_SHA256):
        return False
    return all(
        _is_hash(value.get(key))
        and hmac.compare_digest(value[key], expected)
        for key, expected in EXPECTED_IMPLEMENTATION_SHA256.items()
    )


def _source_hashes(
    preregistration_v7_document: Any,
    execution_binding_document: Any,
    registration_candidate_document: Any,
) -> dict[str, str | None]:
    return {
        "shadow_preregistration_v7_document_sha256": (
            _sha256(preregistration_v7_document)
            if type(preregistration_v7_document) is dict
            else None
        ),
        "presentation_execution_evidence_binding_sha256": _hash_at(
            execution_binding_document, "binding_sha256"
        ),
        "presentation_registration_candidate_sha256": _hash_at(
            registration_candidate_document, "registration_hash"
        ),
        "projection_document_sha256": _hash_at(
            execution_binding_document,
            "source_hashes",
            "projection_document_sha256",
        ),
        "fixture_descriptor_sha256": _hash_at(
            execution_binding_document,
            "source_hashes",
            "fixture_descriptor_sha256",
        ),
        "presentation_execution_evidence_binding_v1_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256[
                "presentation_execution_evidence_binding_v1"
            ]
        ),
        "presentation_registration_candidate_v1_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256[
                "presentation_registration_candidate_v1"
            ]
        ),
    }


def _binding_checks(
    preregistration_v7_document: Any,
    execution_binding_document: Any,
    registration_candidate_document: Any,
    *,
    execution_binding_verification_context: Any,
    registration_candidate_verification_context: Any,
    current_implementation_sha256: Any,
) -> tuple[dict[str, bool], dict[str, str | None]]:
    execution_context_exact = _exact_context(
        execution_binding_verification_context,
        EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS,
    )
    registration_context_exact = _exact_context(
        registration_candidate_verification_context,
        REGISTRATION_VERIFICATION_CONTEXT_KEYS,
    )
    execution_receipt, execution_exact = _call_execution_binding_verifier(
        execution_binding_document,
        preregistration_v7_document,
        execution_binding_verification_context,
    )
    registration_receipt, registration_exact = _call_registration_verifier(
        registration_candidate_document,
        registration_candidate_verification_context,
    )

    v7_registration_hash = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "presentation_registration_expected_document_hash",
    )
    v7_registration_implementation = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "presentation_registration_implementation_sha256",
    )
    registration_hash = _hash_at(
        registration_candidate_document, "registration_hash"
    )

    v7_fixture = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "consumer_fixture_javascript_sha256",
    )
    registration_fixture = _hash_at(
        registration_candidate_document,
        "contract_pins",
        "consumer_fixture_javascript_sha256",
    )
    v7_projection = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "immutable_v6_contract_pins",
        "projection_v3_implementation_sha256",
    )
    registration_projection = _hash_at(
        registration_candidate_document,
        "contract_pins",
        "projection_implementation_sha256",
    )
    v7_card_js = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "immutable_v6_contract_pins",
        "freshness_gate_card_v3_javascript_sha256",
    )
    registration_card_js = _hash_at(
        registration_candidate_document,
        "contract_pins",
        "card_javascript_sha256",
    )
    v7_card_css = _hash_at(
        preregistration_v7_document,
        "contract_pins",
        "immutable_v6_contract_pins",
        "freshness_gate_card_v3_stylesheet_sha256",
    )
    registration_card_css = _hash_at(
        registration_candidate_document,
        "contract_pins",
        "card_stylesheet_sha256",
    )

    v7_document_hash = (
        _sha256(preregistration_v7_document)
        if type(preregistration_v7_document) is dict
        else None
    )
    binding_v7_hash = _hash_at(
        execution_binding_document,
        "source_hashes",
        "shadow_preregistration_v7_document_sha256",
    )
    source_hashes = _source_hashes(
        preregistration_v7_document,
        execution_binding_document,
        registration_candidate_document,
    )

    checks = {
        "execution_binding_verification_context_exact": execution_context_exact,
        "registration_candidate_verification_context_exact": (
            registration_context_exact
        ),
        "execution_binding_exactly_verified": execution_exact,
        "registration_candidate_exactly_verified": registration_exact,
        "implementation_manifest_exact": _implementation_manifest_exact(
            current_implementation_sha256
        ),
        "execution_binding_schema_and_status_exact": (
            type(execution_binding_document) is dict
            and execution_binding_document.get("schema") == execution_binding_v1.SCHEMA
            and execution_binding_document.get("status") == "PASS"
        ),
        "preregistration_v7_remains_blocked": (
            type(preregistration_v7_document) is dict
            and preregistration_v7_document.get("status") == "BLOCKED"
        ),
        "registration_candidate_schema_and_status_pinned": (
            type(registration_candidate_document) is dict
            and registration_candidate_document.get("schema_version")
            == _path(
                preregistration_v7_document,
                "contract_pins",
                "presentation_registration_schema_version",
            )
            and registration_candidate_document.get("status")
            == _path(
                preregistration_v7_document,
                "contract_pins",
                "presentation_registration_status",
            )
            == "BLOCKED"
        ),
        "registration_document_hash_identity": _same_hash(
            registration_hash, v7_registration_hash
        ),
        "registration_implementation_identity": (
            _same_hash(
                v7_registration_implementation,
                EXPECTED_IMPLEMENTATION_SHA256[
                    "presentation_registration_candidate_v1"
                ],
            )
        ),
        "fixture_implementation_pin_identity": _same_hash(
            v7_fixture, registration_fixture
        ),
        "projection_implementation_pin_identity": _same_hash(
            v7_projection, registration_projection
        ),
        "card_javascript_pin_identity": _same_hash(
            v7_card_js, registration_card_js
        ),
        "card_stylesheet_pin_identity": _same_hash(
            v7_card_css, registration_card_css
        ),
        "execution_binding_v7_document_identity": _same_hash(
            v7_document_hash, binding_v7_hash
        ),
        "execution_binding_local_fixture_evidence_bound": (
            _path(
                execution_binding_document,
                "facts",
                "local_fixture_execution_evidence_bound",
            )
            is True
        ),
        "execution_binding_registration_still_unbound": (
            _path(
                execution_binding_document,
                "facts",
                "presentation_consumer_registration_evidence_bound",
            )
            is False
            and _path(
                execution_binding_document,
                "facts",
                "presentation_consumer_registration_activated",
            )
            is False
        ),
        "registration_candidate_built_and_inactive": (
            _path(
                registration_candidate_document,
                "facts",
                "registration_candidate_built",
            )
            is True
            and _path(
                registration_candidate_document,
                "facts",
                "registration_activated",
            )
            is False
            and _path(
                registration_candidate_document, "facts", "ui_mounted"
            )
            is False
            and _path(
                registration_candidate_document,
                "facts",
                "server_route_registered",
            )
            is False
        ),
        "all_source_authority_locked": (
            _authority_locked(preregistration_v7_document)
            and _authority_locked(execution_binding_document)
            and _authority_locked(registration_candidate_document)
        ),
        "verification_receipts_summary_only": (
            type(execution_receipt) is dict
            and type(registration_receipt) is dict
            and "document" not in execution_receipt
            and "document" not in registration_receipt
        ),
        "source_summary_hashes_valid": all(
            _is_hash(value) for value in source_hashes.values()
        ),
    }
    return checks, source_hashes


def build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
    preregistration_v7_document: Mapping[str, Any],
    execution_binding_document: Mapping[str, Any],
    registration_candidate_document: Mapping[str, Any],
    *,
    execution_binding_verification_context: Mapping[str, Any],
    registration_candidate_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    checks, source_hashes = _binding_checks(
        preregistration_v7_document,
        execution_binding_document,
        registration_candidate_document,
        execution_binding_verification_context=(
            execution_binding_verification_context
        ),
        registration_candidate_verification_context=(
            registration_candidate_verification_context
        ),
        current_implementation_sha256=current_implementation_sha256,
    )
    passed = all(checks.values())
    document: dict[str, Any] = {
        "schema": SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCKED",
        "decision": (
            "LOCAL_REGISTRATION_CANDIDATE_EVIDENCE_BOUND_ACTIVATION_"
            "INDEPENDENT_DOM_BROWSER_HTTP_MOUNT_CURRENT_UNAUTHORIZED"
            if passed
            else "BLOCKED_EXACT_LOCAL_REGISTRATION_CANDIDATE_EVIDENCE_"
            "BINDING_NOT_PROVEN"
        ),
        "source_hashes": source_hashes,
        "checks": checks,
        "facts": {
            "local_fixture_execution_evidence_bound": (
                checks["execution_binding_local_fixture_evidence_bound"]
            ),
            "projection_lineage_bound_via_execution_binding": passed,
            "registration_candidate_exactly_verified": (
                checks["registration_candidate_exactly_verified"]
            ),
            "registration_candidate_evidence_bound_in_successor": passed,
            "preregistration_v7_remains_blocked": (
                checks["preregistration_v7_remains_blocked"]
            ),
            "registration_candidate_remains_blocked": (
                checks["registration_candidate_schema_and_status_pinned"]
            ),
            "source_documents_mutated": False,
            "registration_activated": False,
            "independent_review_completed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_completed": False,
            "presentation_http_contract_versioned": False,
            "ui_mounted": False,
            "server_route_registered": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "research_runtime": False,
            "registration_activation": False,
            "consumer_activation": False,
            "presentation_mount": False,
            "current_switch": False,
            "paper_trading": False,
            "live_trading": False,
        },
    }
    document["binding_sha256"] = _sha256(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
    document: Mapping[str, Any],
    preregistration_v7_document: Mapping[str, Any],
    execution_binding_document: Mapping[str, Any],
    registration_candidate_document: Mapping[str, Any],
    *,
    execution_binding_verification_context: Mapping[str, Any],
    registration_candidate_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
        preregistration_v7_document,
        execution_binding_document,
        registration_candidate_document,
        execution_binding_verification_context=(
            execution_binding_verification_context
        ),
        registration_candidate_verification_context=(
            registration_candidate_verification_context
        ),
        current_implementation_sha256=current_implementation_sha256,
    )
    document_is_dict = type(document) is dict
    supplied_hash = document.get("binding_sha256") if document_is_dict else None
    unhashed = copy.deepcopy(document) if document_is_dict else {}
    unhashed.pop("binding_sha256", None)
    checks = {
        "document_is_exact_dict": document_is_dict,
        "schema_exact": document_is_dict and document.get("schema") == SCHEMA,
        "static_fingerprint_exact": (
            document_is_dict
            and document.get("static_fingerprint") == STATIC_FINGERPRINT
        ),
        "binding_sha256_valid": _is_hash(supplied_hash),
        "binding_sha256_exact": (
            _is_hash(supplied_hash)
            and hmac.compare_digest(supplied_hash, _sha256(unhashed))
        ),
        "exact_rebuild_match": document_is_dict and document == rebuilt,
        "rebuilt_status_pass": rebuilt.get("status") == "PASS",
        "authority_remains_locked": _authority_locked(rebuilt),
    }
    verified = all(checks.values())
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "PASS" if verified else "FAIL",
        "verified": verified,
        "checks": checks,
        "document_sha256": _sha256(document) if document_is_dict else None,
    }


__all__ = [
    "SCHEMA",
    "VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS",
    "REGISTRATION_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1",
]
