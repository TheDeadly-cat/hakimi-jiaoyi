"""Bind registration-v2 and fixture execution evidence-v2 without activation."""

from __future__ import annotations

import copy
import hmac
import re
from collections.abc import Mapping
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2
    as registration_v2,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2
    as execution_evidence_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA = (
    "strategy-correlation-cluster-portfolio-risk-shadow-presentation-"
    "execution-evidence-binding-v2"
)
VERIFICATION_SCHEMA = f"{SCHEMA}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-weighted-diversification-shadow-execution-evidence-"
    "binding-v2-lock-1"
)

REGISTRATION_VERIFICATION_CONTEXT_KEYS = frozenset(
    {"current_implementation_sha256"}
)
EVIDENCE_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "node_execution_receipt",
        "expected_projection_hash",
        "expected_registration_hash",
    }
)
EXPECTED_IMPLEMENTATION_SHA256 = {
    "presentation_execution_evidence_binding_v1": (
        "b40e50db01e5bb5d6c8c19944f46edceca3a1c420cfb519a5ecf68f50c8d855d"
    ),
    "presentation_registration_v2": (
        "c190e3aa49777b1c73a7cf0a12e534ef829003227818cc6412b68b388980f4cc"
    ),
    "fixture_execution_receipt_v2_js": (
        "829c7ade8410bb5f74e0bffd984e00ab19e815093a34ab974a9821c457546ae9"
    ),
    "presentation_fixture_execution_evidence_v2": (
        "b36efaef7bdac80d2a30181455099f8e8e750e50dc5a06e091fa52f8d0244471"
    ),
}

_VERIFY_REGISTRATION = getattr(
    registration_v2,
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_"
    "registration_v2",
    None,
)
_VERIFY_EXECUTION_EVIDENCE = getattr(
    execution_evidence_v2,
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_"
    "execution_evidence_v2",
    None,
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _same_hash(*values: Any) -> bool:
    if not values or any(not _is_hash(value) for value in values):
        return False
    return all(hmac.compare_digest(values[0], value) for value in values[1:])


def _path(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if type(current) is not dict or key not in current:
            return None
        current = current[key]
    return current


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
    if receipt.get("blockers", []) != []:
        return False
    markers = [
        value is True
        for key, value in receipt.items()
        if type(key) is str and key.endswith("_exactly_verified")
    ]
    if "verified" in receipt:
        markers.append(receipt["verified"] is True)
    checks = receipt.get("checks")
    if checks is not None:
        if type(checks) is not dict or not checks:
            return False
        markers.append(
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
    return bool(markers) and all(markers)


def _call_registration_verifier(
    document: Any, context: Any
) -> tuple[dict[str, Any], bool]:
    if not _exact_context(context, REGISTRATION_VERIFICATION_CONTEXT_KEYS):
        return {}, False
    if not callable(_VERIFY_REGISTRATION):
        return {}, False
    try:
        receipt = _VERIFY_REGISTRATION(
            copy.deepcopy(document),
            copy.deepcopy(context["current_implementation_sha256"]),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _call_evidence_verifier(
    document: Any, context: Any
) -> tuple[dict[str, Any], bool]:
    if not _exact_context(context, EVIDENCE_VERIFICATION_CONTEXT_KEYS):
        return {}, False
    if not callable(_VERIFY_EXECUTION_EVIDENCE):
        return {}, False
    try:
        receipt = _VERIFY_EXECUTION_EVIDENCE(
            copy.deepcopy(document),
            copy.deepcopy(context["node_execution_receipt"]),
            copy.deepcopy(context["expected_projection_hash"]),
            copy.deepcopy(context["expected_registration_hash"]),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _manifest_exact(value: Any) -> bool:
    return type(value) is dict and strict_json_contract_equal(
        value, EXPECTED_IMPLEMENTATION_SHA256
    )


def _source_hashes(
    registration_candidate_document: Any,
    fixture_execution_evidence: Any,
    evidence_context: Any,
) -> dict[str, str | None]:
    node_receipt = (
        evidence_context.get("node_execution_receipt")
        if type(evidence_context) is dict
        else None
    )
    return {
        "registration_candidate_document_sha256": (
            strict_canonical_hash(registration_candidate_document)
            if type(registration_candidate_document) is dict
            else None
        ),
        "registration_candidate_hash": _path(
            registration_candidate_document, "registration_hash"
        ),
        "fixture_execution_evidence_document_sha256": (
            strict_canonical_hash(fixture_execution_evidence)
            if type(fixture_execution_evidence) is dict
            else None
        ),
        "fixture_execution_evidence_hash": _path(
            fixture_execution_evidence, "evidence_hash"
        ),
        "node_execution_receipt_hash": _path(node_receipt, "receipt_hash"),
        "projection_hash": (
            evidence_context.get("expected_projection_hash")
            if type(evidence_context) is dict
            else None
        ),
        "fixture_descriptor_hash": _path(
            node_receipt, "verification", "descriptor_sha256"
        ),
        "predecessor_binding_v1_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256[
                "presentation_execution_evidence_binding_v1"
            ]
        ),
        "presentation_registration_v2_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256["presentation_registration_v2"]
        ),
        "fixture_execution_receipt_v2_javascript_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256["fixture_execution_receipt_v2_js"]
        ),
        "presentation_fixture_execution_evidence_v2_implementation_sha256": (
            EXPECTED_IMPLEMENTATION_SHA256[
                "presentation_fixture_execution_evidence_v2"
            ]
        ),
    }


def _binding_checks(
    registration_candidate_document: Any,
    fixture_execution_evidence: Any,
    *,
    registration_verification_context: Any,
    fixture_execution_evidence_verification_context: Any,
    current_implementation_sha256: Any,
) -> tuple[dict[str, bool], dict[str, str | None]]:
    registration_context_exact = _exact_context(
        registration_verification_context,
        REGISTRATION_VERIFICATION_CONTEXT_KEYS,
    )
    evidence_context_exact = _exact_context(
        fixture_execution_evidence_verification_context,
        EVIDENCE_VERIFICATION_CONTEXT_KEYS,
    )
    registration_receipt, registration_exact = _call_registration_verifier(
        registration_candidate_document,
        registration_verification_context if registration_context_exact else {},
    )
    evidence_receipt, evidence_exact = _call_evidence_verifier(
        fixture_execution_evidence,
        (
            fixture_execution_evidence_verification_context
            if evidence_context_exact
            else {}
        ),
    )
    node_receipt = (
        fixture_execution_evidence_verification_context[
            "node_execution_receipt"
        ]
        if evidence_context_exact
        else None
    )
    expected_projection_hash = (
        fixture_execution_evidence_verification_context[
            "expected_projection_hash"
        ]
        if evidence_context_exact
        else None
    )
    expected_registration_hash = (
        fixture_execution_evidence_verification_context[
            "expected_registration_hash"
        ]
        if evidence_context_exact
        else None
    )
    registration_hash = _path(
        registration_candidate_document, "registration_hash"
    )
    receipt_registration_hash = _path(
        node_receipt, "source", "registration_candidate_hash"
    )
    evidence_registration_hash = _path(
        fixture_execution_evidence, "source", "registration_candidate_hash"
    )
    receipt_projection_hash = _path(
        node_receipt, "source", "projection_hash"
    )
    evidence_projection_hash = _path(
        fixture_execution_evidence, "source", "projection_hash"
    )
    receipt_hash = _path(node_receipt, "receipt_hash")
    evidence_receipt_hash = _path(
        fixture_execution_evidence, "source", "node_receipt_hash"
    )
    descriptor_hash = _path(
        node_receipt, "verification", "descriptor_sha256"
    )
    evidence_descriptor_hash = _path(
        fixture_execution_evidence, "source", "descriptor_hash"
    )
    registration_pins = _path(registration_candidate_document, "contract_pins")
    receipt_source = _path(node_receipt, "source")
    evidence_source = _path(fixture_execution_evidence, "source")
    source_hashes = _source_hashes(
        registration_candidate_document,
        fixture_execution_evidence,
        (
            fixture_execution_evidence_verification_context
            if evidence_context_exact
            else {}
        ),
    )

    checks = {
        "registration_verification_context_exact": registration_context_exact,
        "execution_evidence_verification_context_exact": evidence_context_exact,
        "registration_candidate_exactly_verified": registration_exact,
        "fixture_execution_evidence_exactly_verified": evidence_exact,
        "binding_implementation_manifest_exact": _manifest_exact(
            current_implementation_sha256
        ),
        "registration_candidate_blocked_built_and_inactive": (
            type(registration_candidate_document) is dict
            and registration_candidate_document.get("schema_version")
            == registration_v2.SCHEMA_VERSION
            and registration_candidate_document.get("status") == "BLOCKED"
            and _path(
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
        ),
        "node_receipt_schema_and_status_exact": (
            type(node_receipt) is dict
            and node_receipt.get("schema_version")
            == execution_evidence_v2.NODE_RECEIPT_SCHEMA_VERSION
            and node_receipt.get("status") == "PASS"
        ),
        "fixture_execution_evidence_schema_and_status_exact": (
            type(fixture_execution_evidence) is dict
            and fixture_execution_evidence.get("schema_version")
            == execution_evidence_v2.SCHEMA_VERSION
            and fixture_execution_evidence.get("status") == "PASS"
        ),
        "registration_hash_chain_exact": _same_hash(
            registration_hash,
            expected_registration_hash,
            receipt_registration_hash,
            evidence_registration_hash,
        ),
        "projection_hash_chain_exact": _same_hash(
            expected_projection_hash,
            receipt_projection_hash,
            evidence_projection_hash,
        ),
        "node_receipt_hash_chain_exact": _same_hash(
            receipt_hash, evidence_receipt_hash
        ),
        "descriptor_hash_chain_exact": _same_hash(
            descriptor_hash, evidence_descriptor_hash
        ),
        "registration_implementation_pin_identity": (
            type(receipt_source) is dict
            and type(evidence_source) is dict
            and _same_hash(
                EXPECTED_IMPLEMENTATION_SHA256["presentation_registration_v2"],
                receipt_source.get("registration_implementation_sha256"),
                evidence_source.get("registration_implementation_sha256"),
            )
        ),
        "projection_implementation_pin_identity": (
            type(registration_pins) is dict
            and type(receipt_source) is dict
            and type(evidence_source) is dict
            and _same_hash(
                registration_pins.get("projection_implementation_sha256"),
                receipt_source.get("projection_implementation_sha256"),
                evidence_source.get("projection_implementation_sha256"),
            )
        ),
        "strict_canonical_pin_identity": (
            type(registration_pins) is dict
            and type(receipt_source) is dict
            and type(evidence_source) is dict
            and _same_hash(
                registration_pins.get("strict_canonical_javascript_sha256"),
                receipt_source.get("strict_canonical_implementation_sha256"),
                evidence_source.get("strict_canonical_implementation_sha256"),
            )
        ),
        "card_implementation_pin_identity": (
            type(registration_pins) is dict
            and type(receipt_source) is dict
            and type(evidence_source) is dict
            and _same_hash(
                registration_pins.get("card_javascript_sha256"),
                receipt_source.get("card_implementation_sha256"),
                evidence_source.get("card_implementation_sha256"),
            )
        ),
        "fixture_implementation_pin_identity": (
            type(registration_pins) is dict
            and type(receipt_source) is dict
            and type(evidence_source) is dict
            and _same_hash(
                registration_pins.get("consumer_fixture_javascript_sha256"),
                receipt_source.get("fixture_implementation_sha256"),
                evidence_source.get("fixture_implementation_sha256"),
            )
        ),
        "registration_candidate_authority_locked": _authority_locked(
            registration_candidate_document
        ),
        "node_receipt_authority_locked": _authority_locked(node_receipt),
        "fixture_execution_evidence_authority_locked": _authority_locked(
            fixture_execution_evidence
        ),
        "registration_manifest_not_externally_attested": (
            _path(
                registration_candidate_document,
                "facts",
                "implementation_manifest_externally_attested",
            )
            is False
        ),
        "execution_provenance_not_externally_authenticated": (
            _path(
                fixture_execution_evidence,
                "facts",
                "node_process_identity_authenticated",
            )
            is False
            and _path(
                fixture_execution_evidence,
                "facts",
                "receipt_signature_verified",
            )
            is False
            and _path(
                fixture_execution_evidence,
                "facts",
                "external_execution_authority_verified",
            )
            is False
        ),
        "verification_receipts_summary_only": (
            type(registration_receipt) is dict
            and type(evidence_receipt) is dict
            and "document" not in registration_receipt
            and "document" not in evidence_receipt
        ),
        "source_summary_hashes_valid": all(
            _is_hash(value) for value in source_hashes.values()
        ),
    }
    return checks, source_hashes


def build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
    registration_candidate_document: Mapping[str, Any],
    fixture_execution_evidence: Mapping[str, Any],
    *,
    registration_verification_context: Mapping[str, Any],
    fixture_execution_evidence_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    checks, source_hashes = _binding_checks(
        registration_candidate_document,
        fixture_execution_evidence,
        registration_verification_context=registration_verification_context,
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
            "LOCAL_REGISTRATION_AND_SEALED_FIXTURE_V4_EXECUTION_EVIDENCE_"
            "BOUND_EXTERNAL_ATTESTATION_PROCESS_IDENTITY_SIGNATURE_"
            "INDEPENDENT_DOM_BROWSER_ACTIVATION_UNPROVEN"
            if passed
            else "BLOCKED_EXACT_WEIGHTED_PRESENTATION_EXECUTION_EVIDENCE_"
            "BINDING_NOT_PROVEN"
        ),
        "source_hashes": source_hashes,
        "checks": checks,
        "facts": {
            "registration_candidate_evidence_bound": passed,
            "fixture_execution_receipt_bound_via_evidence": passed,
            "fixture_execution_evidence_bound": passed,
            "binding_implementation_manifest_exact": checks[
                "binding_implementation_manifest_exact"
            ],
            "predecessor_binding_v1_preserved": checks[
                "binding_implementation_manifest_exact"
            ],
            "registration_candidate_remains_blocked": checks[
                "registration_candidate_blocked_built_and_inactive"
            ],
            "registration_activated": False,
            "source_documents_embedded": False,
            "source_documents_mutated": False,
            "external_artifact_attestation_verified": False,
            "process_identity_authenticated": False,
            "execution_receipt_signed": False,
            "independent_review_completed": False,
            "stylesheet_execution_proven": False,
            "dom_execution_proven": False,
            "browser_execution_proven": False,
            "runtime_mutations_performed": False,
            "mount_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "research_runtime": False,
            "registration_activation": False,
            "consumer_activation": False,
            "presentation_mount": False,
            "current_switch": False,
            "browser": False,
            "paper_trading": False,
            "live_trading": False,
        },
    }
    return seal_strict_canonical_document(document, "binding_sha256")


def verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
    document: Mapping[str, Any],
    registration_candidate_document: Mapping[str, Any],
    fixture_execution_evidence: Mapping[str, Any],
    *,
    registration_verification_context: Mapping[str, Any],
    fixture_execution_evidence_verification_context: Mapping[str, Any],
    current_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
        registration_candidate_document,
        fixture_execution_evidence,
        registration_verification_context=registration_verification_context,
        fixture_execution_evidence_verification_context=(
            fixture_execution_evidence_verification_context
        ),
        current_implementation_sha256=current_implementation_sha256,
    )
    document_is_dict = type(document) is dict
    supplied_hash = document.get("binding_sha256") if document_is_dict else None
    payload = copy.deepcopy(document) if document_is_dict else {}
    payload.pop("binding_sha256", None)
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
            and hmac.compare_digest(
                supplied_hash, strict_canonical_hash(payload)
            )
        ),
        "exact_rebuild_match": (
            document_is_dict and strict_json_contract_equal(document, rebuilt)
        ),
        "rebuilt_status_pass": rebuilt.get("status") == "PASS",
        "authority_remains_locked": _authority_locked(rebuilt),
    }
    verified = all(checks.values())
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "PASS" if verified else "FAIL",
        "verified": verified,
        "checks": checks,
        "document_sha256": (
            strict_canonical_hash(document) if document_is_dict else None
        ),
    }


__all__ = [
    "SCHEMA",
    "VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "REGISTRATION_VERIFICATION_CONTEXT_KEYS",
    "EVIDENCE_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2",
]
