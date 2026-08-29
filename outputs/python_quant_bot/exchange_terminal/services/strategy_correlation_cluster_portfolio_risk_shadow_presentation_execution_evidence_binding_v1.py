"""Fail-closed local presentation execution evidence binding.

This module binds the immutable shadow preregistration v7 contract to the
local, deterministic fixture execution evidence from ADR0195.  A PASS here is
only a local contract-binding result.  It does not activate a consumer or
establish process identity, signature, independent review, DOM/browser
execution, runtime authority, or trading authority.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1
    as fixture_execution_evidence_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
    as shadow_preregistration_v7,
)


SCHEMA = (
    "strategy-correlation-cluster-portfolio-risk-shadow-presentation-"
    "execution-evidence-binding-v1"
)
VERIFICATION_SCHEMA = f"{SCHEMA}-verification"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-presentation-local-execution-binding-lock-1"
)

V7_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v6_document",
        "v6_verification_context",
        "successor_implementation_sha256",
    }
)
EVIDENCE_VERIFICATION_CONTEXT_KEYS = frozenset(
    {"node_execution_receipt", "expected_projection_hash"}
)

EXPECTED_IMPLEMENTATION_SHA256 = {
    "shadow_preregistration_v7": (
        "f2d3f688e6841e709f5a108bb56542d6930758b57cfab8299f2e6750e06caf95"
    ),
    "fixture_execution_receipt_v1_js": (
        "d088ac43737f77683adbe74fefffd9e7f31ddd8c6adf79d342387c80b56b119f"
    ),
    "presentation_fixture_execution_evidence_v1": (
        "0b28e846117f77a37d945ff3bba6a079db78f7d7874137bcdbe9c33c2446073c"
    ),
}

_VERIFY_V7 = getattr(
    shadow_preregistration_v7,
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_"
    "preregistration_v7",
    None,
)
_VERIFY_FIXTURE_EVIDENCE = getattr(
    fixture_execution_evidence_v1,
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_"
    "execution_evidence_v1",
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


def _is_strict_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_exact_mapping(value: Any, keys: frozenset[str]) -> bool:
    return type(value) is dict and frozenset(value) == keys


def _path(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if type(current) is not dict or key not in current:
            return _MISSING
        current = current[key]
    return current


def _single_consistent_hash(value: Any, paths: tuple[tuple[str, ...], ...]) -> str | None:
    """Return one strict hash from explicit versioned contract paths."""

    found = []
    for path in paths:
        candidate = _path(value, *path)
        if candidate is not _MISSING:
            if not _is_strict_sha256(candidate):
                return None
            found.append(candidate)
    if not found or any(candidate != found[0] for candidate in found[1:]):
        return None
    return found[0]


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


def _call_verifier(
    verifier: Callable[..., Any] | None,
    document: Any,
    context: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    if not callable(verifier):
        return {}, False
    try:
        receipt = verifier(copy.deepcopy(document), **copy.deepcopy(dict(context)))
    except Exception:
        return {}, False
    if type(receipt) is not dict:
        return {}, False
    return receipt, _verification_passed(receipt)


def _implementation_manifest_exact(value: Any) -> bool:
    if type(value) is not dict or set(value) != set(EXPECTED_IMPLEMENTATION_SHA256):
        return False
    return all(
        _is_strict_sha256(value.get(key))
        and hmac.compare_digest(value[key], expected)
        for key, expected in EXPECTED_IMPLEMENTATION_SHA256.items()
    )


def _source_hashes(
    preregistration_v7_document: Any,
    fixture_execution_evidence: Any,
    fixture_execution_evidence_verification_context: Mapping[str, Any],
) -> dict[str, str | None]:
    node_receipt = fixture_execution_evidence_verification_context.get(
        "node_execution_receipt"
    )
    expected_projection_hash = fixture_execution_evidence_verification_context.get(
        "expected_projection_hash"
    )
    receipt_hash = _single_consistent_hash(node_receipt, (("receipt_hash",),))
    evidence_receipt_hash = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "node_receipt_hash"),),
    )
    descriptor_hash = _single_consistent_hash(
        node_receipt,
        (("verification", "descriptor_sha256"),),
    )
    evidence_descriptor_hash = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "descriptor_hash"),),
    )

    return {
        "shadow_preregistration_v7_document_sha256": (
            _sha256(preregistration_v7_document)
            if type(preregistration_v7_document) is dict
            else None
        ),
        "fixture_execution_evidence_document_sha256": (
            _sha256(fixture_execution_evidence)
            if type(fixture_execution_evidence) is dict
            else None
        ),
        "node_execution_receipt_sha256": (
            receipt_hash
            if receipt_hash is not None
            and evidence_receipt_hash is not None
            and hmac.compare_digest(receipt_hash, evidence_receipt_hash)
            else None
        ),
        "projection_document_sha256": (
            expected_projection_hash
            if _is_strict_sha256(expected_projection_hash)
            else None
        ),
        "fixture_descriptor_sha256": (
            descriptor_hash
            if descriptor_hash is not None
            and evidence_descriptor_hash is not None
            and hmac.compare_digest(descriptor_hash, evidence_descriptor_hash)
            else None
        ),
        "shadow_preregistration_v7_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256["shadow_preregistration_v7"]
        ),
        "fixture_execution_receipt_v1_javascript_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256["fixture_execution_receipt_v1_js"]
        ),
        "presentation_fixture_execution_evidence_v1_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256[
                "presentation_fixture_execution_evidence_v1"
            ]
        ),
    }


def _binding_checks(
    preregistration_v7_document: Any,
    fixture_execution_evidence: Any,
    *,
    preregistration_v7_verification_context: Any,
    fixture_execution_evidence_verification_context: Any,
    current_implementation_sha256: Any,
) -> tuple[dict[str, bool], dict[str, str | None]]:
    v7_context_exact = _is_exact_mapping(
        preregistration_v7_verification_context, V7_VERIFICATION_CONTEXT_KEYS
    )
    evidence_context_exact = _is_exact_mapping(
        fixture_execution_evidence_verification_context,
        EVIDENCE_VERIFICATION_CONTEXT_KEYS,
    )

    v7_receipt, v7_exact = _call_verifier(
        _VERIFY_V7,
        preregistration_v7_document,
        preregistration_v7_verification_context
        if v7_context_exact
        else {},
    )
    evidence_receipt, evidence_exact = _call_verifier(
        _VERIFY_FIXTURE_EVIDENCE,
        fixture_execution_evidence,
        fixture_execution_evidence_verification_context
        if evidence_context_exact
        else {},
    )

    v7_fixture_pin = _single_consistent_hash(
        preregistration_v7_document,
        (("contract_pins", "consumer_fixture_javascript_sha256"),),
    )
    v7_projection_pin = _single_consistent_hash(
        preregistration_v7_document,
        (
            (
                "contract_pins",
                "immutable_v6_contract_pins",
                "projection_v3_implementation_sha256",
            ),
        ),
    )
    v7_card_pin = _single_consistent_hash(
        preregistration_v7_document,
        (
            (
                "contract_pins",
                "immutable_v6_contract_pins",
                "freshness_gate_card_v3_javascript_sha256",
            ),
        ),
    )

    evidence_fixture_pin = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "fixture_implementation_sha256"),),
    )
    evidence_projection_pin = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "projection_implementation_sha256"),),
    )
    evidence_card_pin = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "card_implementation_sha256"),),
    )
    evidence_projection_hash = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "projection_hash"),),
    )
    expected_projection_hash = (
        fixture_execution_evidence_verification_context.get(
            "expected_projection_hash"
        )
        if evidence_context_exact
        else None
    )
    node_receipt = (
        fixture_execution_evidence_verification_context.get(
            "node_execution_receipt"
        )
        if evidence_context_exact
        else None
    )
    node_receipt_hash = _single_consistent_hash(
        node_receipt, (("receipt_hash",),)
    )
    evidence_receipt_hash = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "node_receipt_hash"),),
    )
    node_descriptor_hash = _single_consistent_hash(
        node_receipt,
        (("verification", "descriptor_sha256"),),
    )
    evidence_descriptor_hash = _single_consistent_hash(
        fixture_execution_evidence,
        (("source", "descriptor_hash"),),
    )

    source_hashes = _source_hashes(
        preregistration_v7_document,
        fixture_execution_evidence,
        fixture_execution_evidence_verification_context
        if evidence_context_exact
        else {},
    )

    checks = {
        "preregistration_v7_verification_context_exact": v7_context_exact,
        "fixture_execution_evidence_verification_context_exact": (
            evidence_context_exact
        ),
        "preregistration_v7_exactly_verified": v7_exact,
        "fixture_execution_evidence_exactly_verified": evidence_exact,
        "implementation_manifest_exact": _implementation_manifest_exact(
            current_implementation_sha256
        ),
        "preregistration_v7_remains_blocked": (
            type(preregistration_v7_document) is dict
            and preregistration_v7_document.get("status") == "BLOCKED"
        ),
        "fixture_execution_evidence_status_pass": (
            type(fixture_execution_evidence) is dict
            and fixture_execution_evidence.get("status") == "PASS"
        ),
        "fixture_implementation_pin_identity": (
            v7_fixture_pin is not None
            and evidence_fixture_pin is not None
            and hmac.compare_digest(v7_fixture_pin, evidence_fixture_pin)
        ),
        "projection_implementation_pin_identity": (
            v7_projection_pin is not None
            and evidence_projection_pin is not None
            and hmac.compare_digest(v7_projection_pin, evidence_projection_pin)
        ),
        "card_implementation_pin_identity": (
            v7_card_pin is not None
            and evidence_card_pin is not None
            and hmac.compare_digest(v7_card_pin, evidence_card_pin)
        ),
        "projection_hash_chain_exact": (
            evidence_projection_hash is not None
            and _is_strict_sha256(expected_projection_hash)
            and hmac.compare_digest(
                evidence_projection_hash, expected_projection_hash
            )
        ),
        "node_receipt_hash_chain_exact": (
            node_receipt_hash is not None
            and evidence_receipt_hash is not None
            and hmac.compare_digest(node_receipt_hash, evidence_receipt_hash)
        ),
        "fixture_descriptor_hash_chain_exact": (
            node_descriptor_hash is not None
            and evidence_descriptor_hash is not None
            and hmac.compare_digest(
                node_descriptor_hash, evidence_descriptor_hash
            )
        ),
        "preregistration_v7_authority_locked": _authority_locked(
            preregistration_v7_document
        ),
        "fixture_execution_evidence_authority_locked": _authority_locked(
            fixture_execution_evidence
        ),
        "verification_receipts_are_summary_only": (
            type(v7_receipt) is dict
            and type(evidence_receipt) is dict
            and "document" not in v7_receipt
            and "document" not in evidence_receipt
        ),
        "source_summary_hashes_valid": all(
            _is_strict_sha256(value) for value in source_hashes.values()
        ),
    }
    return checks, source_hashes


def build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
    preregistration_v7_document: Mapping[str, Any],
    fixture_execution_evidence: Mapping[str, Any],
    *,
    preregistration_v7_verification_context: Mapping[str, Any],
    fixture_execution_evidence_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    """Build a detached, local-only shadow evidence binding."""

    checks, source_hashes = _binding_checks(
        preregistration_v7_document,
        fixture_execution_evidence,
        preregistration_v7_verification_context=(
            preregistration_v7_verification_context
        ),
        fixture_execution_evidence_verification_context=(
            fixture_execution_evidence_verification_context
        ),
        current_implementation_sha256=current_implementation_sha256,
    )
    passed = all(checks.values())
    document: dict[str, Any] = {
        "schema": SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCKED",
        "decision": (
            "LOCAL_FIXTURE_EXECUTION_EVIDENCE_BOUND_REGISTRATION_PROCESS_"
            "IDENTITY_SIGNATURE_INDEPENDENT_DOM_BROWSER_UNPROVEN"
            if passed
            else "BLOCKED_EXACT_LOCAL_PRESENTATION_EXECUTION_EVIDENCE_"
            "BINDING_NOT_PROVEN"
        ),
        "source_hashes": source_hashes,
        "checks": checks,
        "facts": {
            "local_fixture_execution_evidence_bound": passed,
            "shadow_preregistration_v7_remains_blocked": (
                checks["preregistration_v7_remains_blocked"]
            ),
            "shadow_preregistration_v7_mutated": False,
            "presentation_consumer_registration_evidence_bound": False,
            "presentation_consumer_registration_activated": False,
            "process_identity_authenticated": False,
            "execution_receipt_signed": False,
            "independent_review_completed": False,
            "dom_execution_proven": False,
            "browser_execution_proven": False,
            "runtime_mutations_performed": False,
            "mount_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "research_runtime": False,
            "consumer_activation": False,
            "presentation_registration": False,
            "mount": False,
            "browser": False,
            "paper_trading": False,
            "live_trading": False,
        },
    }
    document["binding_sha256"] = _sha256(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
    document: Mapping[str, Any],
    preregistration_v7_document: Mapping[str, Any],
    fixture_execution_evidence: Mapping[str, Any],
    *,
    preregistration_v7_verification_context: Mapping[str, Any],
    fixture_execution_evidence_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    """Exactly rebuild and verify a v1 binding document."""

    rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
        preregistration_v7_document,
        fixture_execution_evidence,
        preregistration_v7_verification_context=(
            preregistration_v7_verification_context
        ),
        fixture_execution_evidence_verification_context=(
            fixture_execution_evidence_verification_context
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
        "binding_sha256_valid": _is_strict_sha256(supplied_hash),
        "binding_sha256_exact": (
            _is_strict_sha256(supplied_hash)
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
    "V7_VERIFICATION_CONTEXT_KEYS",
    "EVIDENCE_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1",
]
