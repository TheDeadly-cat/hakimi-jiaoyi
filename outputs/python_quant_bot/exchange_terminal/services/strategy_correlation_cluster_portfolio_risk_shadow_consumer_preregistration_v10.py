"""Fail-closed successor preregistration for signed review and execution v2.

This contract consumes the immutable v9 preregistration, the bounded signed
review evidence, and the sealed execution-evidence binding-v2.  It cross-binds
the reviewed descriptor to the executed fixture descriptor and refines the
remaining activation order without registering transport, mounting a consumer,
or granting trading authority.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1
    as signed_review_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
    as preregistration_v9,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2
    as execution_binding_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v10"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-shadow-preregistration-v10-review-execution-"
    "binding-lock-1"
)

V9_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v8_document",
        "http_candidate_response",
        "http_candidate_request",
        "v8_verification_context",
        "successor_implementation_sha256",
    }
)
SIGNED_REVIEW_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "registration",
        "signed_attestation",
        "review_request_document",
        "review_claim",
        "claim_intake_document",
        "public_key_base64",
        "expected_registration_hash",
        "expected_signed_attestation_hash",
        "review_nonce_hash",
        "v9_verification_context",
    }
)
EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "registration_candidate_document",
        "fixture_execution_evidence",
        "registration_verification_context",
        "fixture_execution_evidence_verification_context",
        "current_implementation_sha256",
    }
)

EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256 = {
    "shadow_preregistration_v9": (
        "46fdc8db9f191adc188ea3619ac44d142013991830c77148fd9aec647a459c3e"
    ),
    "signed_review_attestation_v1": (
        "0e68e0aec1cd1f4876698b7b780cdafc0dd3cc6522d9dc3e9f311fc2a5314269"
    ),
    "presentation_execution_evidence_binding_v2": (
        "2866137e17a559c3199effe642ddc173f864280226abc12d40c2556e62f5e267"
    ),
    "strict_canonical_json_hash": (
        "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
    ),
}

SIGNED_REVIEW_REMAINING_BLOCKERS = (
    "reviewer_real_world_identity_unproven",
    "reviewer_process_independence_unproven",
    "reviewer_key_registration_governance_unproven",
    "review_nonce_uniqueness_unproven",
    "review_replay_registry_unproven",
    "descriptor_content_review_not_observed_by_system",
    "external_independent_review_not_completed",
)
EXECUTION_REMAINING_BLOCKERS = (
    "external_fixture_artifact_attestation_unproven",
    "fixture_execution_process_identity_unproven",
    "fixture_execution_receipt_signature_missing",
    "stylesheet_dom_browser_execution_unproven",
    "presentation_registration_v2_not_activated",
    "runtime_presentation_consumer_unbound",
)
ACTIVATION_ORDER = (
    "ESTABLISH_PROVIDER_TRUST_AND_SOURCE_GOVERNANCE",
    "ESTABLISH_REVIEWER_REAL_WORLD_IDENTITY_AND_PROCESS_INDEPENDENCE",
    "GOVERN_REVIEWER_KEY_REGISTRATION_NONCE_AND_REPLAY",
    "OBSERVE_DESCRIPTOR_CONTENT_REVIEW_AND_COMPLETE_EXTERNAL_INDEPENDENT_REVIEW",
    "ATTEST_FIXTURE_ARTIFACT_AND_AUTHENTICATE_EXECUTION_PROCESS",
    "SIGN_FIXTURE_EXECUTION_RECEIPT",
    "REVIEW_STYLESHEET_DOM_AND_BROWSER_RENDER_CONTRACT",
    "REGISTER_AND_EXERCISE_READ_ONLY_PRESENTATION_HTTP_TRANSPORT",
    "MOUNT_READ_ONLY_PRESENTATION_CANDIDATE",
    "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
)

_VERIFY_V9 = (
    preregistration_v9.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
)
_VERIFY_SIGNED_REVIEW = (
    signed_review_v1.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_evidence_v1
)
_VERIFY_EXECUTION_BINDING = (
    execution_binding_v2.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_OLD_REVIEW_BLOCKER = "presentation_render_descriptor_independent_review_missing"


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


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


def _descriptive_authority_locked(document: Any) -> bool:
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


def _all_false_authority(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and bool(authority)
        and all(type(value) is bool and value is False for value in authority.values())
    )


def _exact_context(value: Any, keys: frozenset[str]) -> bool:
    return type(value) is dict and frozenset(value) == keys


def _v9_context_valid(context: Any) -> bool:
    return _exact_context(context, V9_VERIFICATION_CONTEXT_KEYS) and all(
        type(context[key]) is dict for key in V9_VERIFICATION_CONTEXT_KEYS
    )


def _signed_review_context_valid(context: Any) -> bool:
    if not _exact_context(context, SIGNED_REVIEW_VERIFICATION_CONTEXT_KEYS):
        return False
    document_keys = {
        "registration",
        "signed_attestation",
        "review_request_document",
        "review_claim",
        "claim_intake_document",
        "v9_verification_context",
    }
    hash_keys = {
        "expected_registration_hash",
        "expected_signed_attestation_hash",
        "review_nonce_hash",
    }
    return (
        all(type(context[key]) is dict for key in document_keys)
        and all(_is_hash(context[key]) for key in hash_keys)
        and type(context["public_key_base64"]) is str
        and bool(context["public_key_base64"])
    )


def _execution_binding_context_valid(context: Any) -> bool:
    if not _exact_context(context, EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS):
        return False
    return all(
        type(context[key]) is dict
        for key in EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS
    )


def _manifest_exact(value: Any) -> bool:
    return (
        type(value) is dict
        and set(value) == set(EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)
        and all(
            _same_hash(value.get(key), expected)
            for key, expected in EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256.items()
        )
    )


def _v9_receipt_passed(receipt: Any) -> bool:
    if (
        type(receipt) is not dict
        or receipt.get("status") != "PASS"
        or receipt.get("preregistration_exactly_verified") is not True
        or receipt.get("preregistration_status") != "BLOCKED"
        or receipt.get("blockers") != []
    ):
        return False
    locked = {
        "writer_allowed",
        "http_route_registration_allowed",
        "presentation_mount_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
    }
    return all(receipt.get(key) is False for key in locked)


def _execution_binding_receipt_passed(receipt: Any) -> bool:
    checks = receipt.get("checks") if type(receipt) is dict else None
    return (
        type(receipt) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("verified") is True
        and type(checks) is dict
        and bool(checks)
        and all(type(value) is bool and value is True for value in checks.values())
    )


def _call_v9_verifier(document: Any, context: Any) -> bool:
    if not _v9_context_valid(context):
        return False
    try:
        receipt = _VERIFY_V9(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration_v8_document"]),
            copy.deepcopy(context["http_candidate_response"]),
            copy.deepcopy(context["http_candidate_request"]),
            v8_verification_context=copy.deepcopy(
                context["v8_verification_context"]
            ),
            successor_implementation_sha256=copy.deepcopy(
                context["successor_implementation_sha256"]
            ),
        )
    except Exception:
        return False
    return _v9_receipt_passed(receipt)


def _call_signed_review_verifier(
    evidence: Any, preregistration_v9_document: Any, context: Any
) -> bool:
    if not _signed_review_context_valid(context):
        return False
    try:
        return (
            _VERIFY_SIGNED_REVIEW(
                copy.deepcopy(evidence),
                registration=copy.deepcopy(context["registration"]),
                signed_attestation=copy.deepcopy(context["signed_attestation"]),
                review_request_document=copy.deepcopy(
                    context["review_request_document"]
                ),
                review_claim=copy.deepcopy(context["review_claim"]),
                claim_intake_document=copy.deepcopy(
                    context["claim_intake_document"]
                ),
                preregistration_v9_document=copy.deepcopy(
                    preregistration_v9_document
                ),
                public_key_base64=context["public_key_base64"],
                expected_registration_hash=context["expected_registration_hash"],
                expected_signed_attestation_hash=context[
                    "expected_signed_attestation_hash"
                ],
                review_nonce_hash=context["review_nonce_hash"],
                v9_verification_context=copy.deepcopy(
                    context["v9_verification_context"]
                ),
            )
            is True
        )
    except Exception:
        return False


def _call_execution_binding_verifier(document: Any, context: Any) -> bool:
    if not _execution_binding_context_valid(context):
        return False
    try:
        receipt = _VERIFY_EXECUTION_BINDING(
            copy.deepcopy(document),
            copy.deepcopy(context["registration_candidate_document"]),
            copy.deepcopy(context["fixture_execution_evidence"]),
            registration_verification_context=copy.deepcopy(
                context["registration_verification_context"]
            ),
            fixture_execution_evidence_verification_context=copy.deepcopy(
                context["fixture_execution_evidence_verification_context"]
            ),
            current_implementation_sha256=copy.deepcopy(
                context["current_implementation_sha256"]
            ),
        )
    except Exception:
        return False
    return _execution_binding_receipt_passed(receipt)


def _v9_presentable(document: Any) -> bool:
    facts = document.get("facts") if type(document) is dict else None
    blockers = document.get("blockers") if type(document) is dict else None
    return (
        type(document) is dict
        and document.get("schema_version") == preregistration_v9.SCHEMA_VERSION
        and document.get("static_fingerprint") == preregistration_v9.STATIC_FINGERPRINT
        and document.get("status") == "BLOCKED"
        and document.get("contract_state") == "KNOWN"
        and _sealed_hash_exact(document, "preregistration_hash")
        and _descriptive_authority_locked(document)
        and type(facts) is dict
        and facts.get("implementation_pin_count") == 41
        and facts.get("consumer_fixture_v3_execution_evidence_bound") is True
        and facts.get("presentation_registration_v1_evidence_bound") is True
        and facts.get("render_descriptor_independently_reviewed") is False
        and facts.get("presentation_http_transport_registered") is False
        and facts.get("browser_visual_review_v3_performed") is False
        and type(blockers) is list
        and _OLD_REVIEW_BLOCKER in blockers
        and "presentation_http_transport_unregistered_and_unexercised" in blockers
    )


def _signed_review_presentable(document: Any) -> bool:
    facts = document.get("facts") if type(document) is dict else None
    blockers = document.get("blockers") if type(document) is dict else None
    lineage = document.get("source_lineage") if type(document) is dict else None
    return (
        type(document) is dict
        and document.get("schema_version") == signed_review_v1.EVIDENCE_SCHEMA_VERSION
        and document.get("static_fingerprint") == signed_review_v1.STATIC_FINGERPRINT
        and document.get("status") == "PASS"
        and _sealed_hash_exact(document, "evidence_hash")
        and _descriptive_authority_locked(document)
        and type(facts) is dict
        and facts.get("detached_signature_verified") is True
        and facts.get("descriptor_hash_bound") is True
        and facts.get("review_request_exactly_verified") is True
        and facts.get("claim_intake_exactly_verified") is True
        and facts.get("independent_review_complete") is False
        and facts.get("real_world_reviewer_identity_verified") is False
        and facts.get("reviewer_process_independence_verified") is False
        and facts.get("descriptor_content_review_observed_by_system") is False
        and facts.get("runtime_mutations_performed") is False
        and type(blockers) is list
        and all(item in blockers for item in SIGNED_REVIEW_REMAINING_BLOCKERS)
        and type(lineage) is dict
        and _is_hash(lineage.get("descriptor_sha256"))
    )


def _execution_binding_presentable(document: Any) -> bool:
    facts = document.get("facts") if type(document) is dict else None
    checks = document.get("checks") if type(document) is dict else None
    hashes = document.get("source_hashes") if type(document) is dict else None
    return (
        type(document) is dict
        and document.get("schema") == execution_binding_v2.SCHEMA
        and document.get("static_fingerprint")
        == execution_binding_v2.STATIC_FINGERPRINT
        and document.get("status") == "PASS"
        and _sealed_hash_exact(document, "binding_sha256")
        and _all_false_authority(document)
        and type(checks) is dict
        and bool(checks)
        and all(type(value) is bool and value is True for value in checks.values())
        and type(facts) is dict
        and facts.get("fixture_execution_evidence_bound") is True
        and facts.get("fixture_execution_receipt_bound_via_evidence") is True
        and facts.get("registration_candidate_evidence_bound") is True
        and facts.get("registration_candidate_remains_blocked") is True
        and facts.get("independent_review_completed") is False
        and facts.get("external_artifact_attestation_verified") is False
        and facts.get("process_identity_authenticated") is False
        and facts.get("execution_receipt_signed") is False
        and facts.get("mount_performed") is False
        and type(hashes) is dict
        and _is_hash(hashes.get("fixture_descriptor_hash"))
    )


def _checks(
    preregistration_v9_document: Any,
    signed_review_evidence: Any,
    execution_evidence_binding_v2_document: Any,
    *,
    v9_verification_context: Any,
    signed_review_evidence_verification_context: Any,
    execution_binding_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, bool]:
    review_lineage = (
        signed_review_evidence.get("source_lineage")
        if type(signed_review_evidence) is dict
        else None
    )
    execution_hashes = (
        execution_evidence_binding_v2_document.get("source_hashes")
        if type(execution_evidence_binding_v2_document) is dict
        else None
    )
    return {
        "v9_verification_context_exact": _v9_context_valid(
            v9_verification_context
        ),
        "signed_review_verification_context_exact": _signed_review_context_valid(
            signed_review_evidence_verification_context
        ),
        "execution_binding_verification_context_exact": _execution_binding_context_valid(
            execution_binding_verification_context
        ),
        "successor_implementation_manifest_exact": _manifest_exact(
            successor_implementation_sha256
        ),
        "immutable_v9_exactly_verified": _call_v9_verifier(
            preregistration_v9_document, v9_verification_context
        ),
        "signed_review_evidence_exactly_verified": _call_signed_review_verifier(
            signed_review_evidence,
            preregistration_v9_document,
            signed_review_evidence_verification_context,
        ),
        "execution_binding_v2_exactly_verified": _call_execution_binding_verifier(
            execution_evidence_binding_v2_document,
            execution_binding_verification_context,
        ),
        "immutable_v9_known_and_blocked": _v9_presentable(
            preregistration_v9_document
        ),
        "signed_review_claim_presentable_without_independence_promotion": _signed_review_presentable(
            signed_review_evidence
        ),
        "execution_binding_presentable_without_authority_promotion": _execution_binding_presentable(
            execution_evidence_binding_v2_document
        ),
        "reviewed_descriptor_matches_executed_fixture": (
            type(review_lineage) is dict
            and type(execution_hashes) is dict
            and _same_hash(
                review_lineage.get("descriptor_sha256"),
                execution_hashes.get("fixture_descriptor_hash"),
            )
        ),
    }


def _copy_list(document: Any, key: str) -> list[Any]:
    value = document.get(key) if type(document) is dict else None
    return copy.deepcopy(value) if type(value) is list else []


def _remaining_blockers(v9_document: Any, known: bool) -> list[str]:
    if not known:
        return ["preregistration_v10_exact_source_closure_unproven"]
    result = [
        item
        for item in _copy_list(v9_document, "blockers")
        if type(item) is str and item != _OLD_REVIEW_BLOCKER
    ]
    for item in (*SIGNED_REVIEW_REMAINING_BLOCKERS, *EXECUTION_REMAINING_BLOCKERS):
        if item not in result:
            result.append(item)
    return result


def _closed_local_blockers(
    v9_document: Any,
    signed_review_evidence: Any,
    execution_binding: Any,
    known: bool,
) -> list[Any]:
    result = _copy_list(v9_document, "closed_local_blockers") if known else []
    if known:
        result.extend(
            [
                {
                    "blocker": "signed_render_descriptor_review_claim_evidence_not_bound",
                    "closure": (
                        "ADR0202_SIGNED_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_"
                        "UNPROVEN"
                    ),
                    "closure_verified": True,
                    "signed_review_evidence_sha256": signed_review_evidence.get(
                        "evidence_hash"
                    ),
                },
                {
                    "blocker": "presentation_execution_evidence_binding_v2_not_bound",
                    "closure": (
                        "ADR0209_REGISTRATION_V2_AND_FIXTURE_V4_EXECUTION_"
                        "EVIDENCE_BOUND_NO_RUNTIME"
                    ),
                    "closure_verified": True,
                    "execution_binding_sha256": execution_binding.get(
                        "binding_sha256"
                    ),
                },
            ]
        )
    return result


def _blocker_refinements(v9_document: Any, known: bool) -> list[Any]:
    result = _copy_list(v9_document, "blocker_refinements") if known else []
    if known:
        result.append(
            {
                "blocker": _OLD_REVIEW_BLOCKER,
                "local_contract_state": (
                    "SIGNED_REVIEW_CLAIM_AND_DESCRIPTOR_HASH_BOUND_EXTERNAL_"
                    "INDEPENDENCE_UNPROVEN"
                ),
                "remaining_requirements": list(SIGNED_REVIEW_REMAINING_BLOCKERS),
            }
        )
    return result


def _authority() -> dict[str, bool]:
    return {
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
    }


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
    preregistration_v9_document: Any,
    signed_review_evidence: Any,
    execution_evidence_binding_v2_document: Any,
    *,
    v9_verification_context: Any,
    signed_review_evidence_verification_context: Any,
    execution_binding_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    """Build the unmounted successor gate after exact source re-verification."""

    checks = _checks(
        preregistration_v9_document,
        signed_review_evidence,
        execution_evidence_binding_v2_document,
        v9_verification_context=v9_verification_context,
        signed_review_evidence_verification_context=(
            signed_review_evidence_verification_context
        ),
        execution_binding_verification_context=(
            execution_binding_verification_context
        ),
        successor_implementation_sha256=successor_implementation_sha256,
    )
    known = all(checks.values())
    v9_facts = (
        preregistration_v9_document.get("facts")
        if type(preregistration_v9_document) is dict
        else None
    )
    predecessor_pin_count = (
        v9_facts.get("implementation_pin_count")
        if type(v9_facts) is dict
        else None
    )
    total_pin_count = (
        predecessor_pin_count + len(EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)
        if known
        and type(predecessor_pin_count) is int
        and type(predecessor_pin_count) is not bool
        else None
    )
    closed = _closed_local_blockers(
        preregistration_v9_document,
        signed_review_evidence,
        execution_evidence_binding_v2_document,
        known,
    )
    review_lineage = (
        signed_review_evidence.get("source_lineage")
        if type(signed_review_evidence) is dict
        else None
    )
    reuse = _copy_list(preregistration_v9_document, "reuse_plan") if known else []
    if known:
        reuse.extend(
            [
                {
                    "capability": "SIGNED_RENDER_DESCRIPTOR_REVIEW_CLAIM_V1",
                    "decision": (
                        "REUSE_CRYPTOGRAPHIC_CLAIM_ONLY_EXTERNAL_INDEPENDENCE_"
                        "UNPROVEN"
                    ),
                },
                {
                    "capability": "PRESENTATION_EXECUTION_EVIDENCE_BINDING_V2",
                    "decision": (
                        "REUSE_LOCAL_FIXTURE_V4_BINDING_NO_RUNTIME_OR_AUTHORITY"
                    ),
                },
            ]
        )

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "contract_state": "KNOWN" if known else "UNKNOWN",
        "decision": (
            "SUCCESSOR_PREREGISTERED_SIGNED_REVIEW_CLAIM_AND_EXECUTION_BINDING_"
            "V2_BOUND_EXTERNAL_INDEPENDENCE_TRANSPORT_DOM_BROWSER_RUNTIME_"
            "CURRENT_UNAUTHORIZED"
            if known
            else "SUCCESSOR_PREREGISTRATION_BLOCKED_EXACT_V10_SOURCE_CLOSURE_"
            "NOT_PROVEN"
        ),
        "source": {
            "immutable_v9_exactly_verified": checks[
                "immutable_v9_exactly_verified"
            ],
            "immutable_v9_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v9"
                ]
            ),
            "immutable_v9_preregistration_hash": (
                preregistration_v9_document.get("preregistration_hash")
                if type(preregistration_v9_document) is dict
                else None
            ),
            "signed_review_evidence_exactly_verified": checks[
                "signed_review_evidence_exactly_verified"
            ],
            "signed_review_evidence_sha256": (
                signed_review_evidence.get("evidence_hash")
                if type(signed_review_evidence) is dict
                else None
            ),
            "execution_binding_v2_exactly_verified": checks[
                "execution_binding_v2_exactly_verified"
            ],
            "execution_binding_v2_sha256": (
                execution_evidence_binding_v2_document.get("binding_sha256")
                if type(execution_evidence_binding_v2_document) is dict
                else None
            ),
            "reviewed_and_executed_descriptor_sha256": (
                review_lineage.get("descriptor_sha256")
                if known and type(review_lineage) is dict
                else None
            ),
            "successor_manifest_contract_verified": checks[
                "successor_implementation_manifest_exact"
            ],
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "total_implementation_pin_count": total_pin_count,
            "verification_checks": checks,
        },
        "contract_pins": {
            "immutable_v9_contract_pins": copy.deepcopy(
                preregistration_v9_document.get("contract_pins")
                if known and type(preregistration_v9_document) is dict
                else None
            ),
            "immutable_v9_schema_version": preregistration_v9.SCHEMA_VERSION,
            "immutable_v9_static_fingerprint": preregistration_v9.STATIC_FINGERPRINT,
            "signed_review_evidence_schema_version": (
                signed_review_v1.EVIDENCE_SCHEMA_VERSION
            ),
            "signed_review_static_fingerprint": signed_review_v1.STATIC_FINGERPRINT,
            "execution_binding_v2_schema": execution_binding_v2.SCHEMA,
            "execution_binding_v2_static_fingerprint": (
                execution_binding_v2.STATIC_FINGERPRINT
            ),
            "successor_implementation_sha256": copy.deepcopy(
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
        },
        "required_shadow_input_schemas": (
            _copy_list(preregistration_v9_document, "required_shadow_input_schemas")
            if known
            else []
        ),
        "required_presentation_evidence_schemas": (
            [
                signed_review_v1.EVIDENCE_SCHEMA_VERSION,
                execution_binding_v2.SCHEMA,
            ]
            if known
            else []
        ),
        "closed_local_blockers": closed,
        "blocker_refinements": _blocker_refinements(
            preregistration_v9_document, known
        ),
        "blockers": _remaining_blockers(preregistration_v9_document, known),
        "reuse_plan": reuse,
        "activation_order": list(ACTIVATION_ORDER) if known else [],
        "facts": {
            "immutable_v9_exactly_verified": known,
            "signed_review_evidence_exactly_verified": known,
            "signed_review_claim_cryptographically_verified": known,
            "reviewed_descriptor_matches_executed_fixture": known,
            "render_descriptor_independently_reviewed": False,
            "reviewer_real_world_identity_verified": False,
            "reviewer_process_independence_verified": False,
            "descriptor_content_review_observed": False,
            "execution_binding_v2_exactly_verified": known,
            "consumer_fixture_v4_execution_evidence_bound": known,
            "fixture_execution_receipt_v2_bound": known,
            "external_fixture_artifact_attestation_verified": False,
            "fixture_execution_process_identity_authenticated": False,
            "fixture_execution_receipt_signed": False,
            "presentation_registration_v2_evidence_bound": known,
            "presentation_registration_v2_activated": False,
            "stylesheet_contract_reviewed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "presentation_http_transport_registered": False,
            "presentation_http_transport_exercised": False,
            "ui_mounted": False,
            "runtime_consumer_bound": False,
            "current_pointer_written": False,
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "implementation_pin_count": total_pin_count,
            "closed_local_blocker_count": len(closed),
            "local_evidence_closure_count": (
                v9_facts.get("local_evidence_closure_count", 0) + 2
                if known and type(v9_facts) is dict
                else 0
            ),
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
    document: Any,
    preregistration_v9_document: Any,
    signed_review_evidence: Any,
    execution_evidence_binding_v2_document: Any,
    *,
    v9_verification_context: Any,
    signed_review_evidence_verification_context: Any,
    execution_binding_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    """Rebuild from every source and return a non-authorizing receipt."""

    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
            preregistration_v9_document,
            signed_review_evidence,
            execution_evidence_binding_v2_document,
            v9_verification_context=v9_verification_context,
            signed_review_evidence_verification_context=(
                signed_review_evidence_verification_context
            ),
            execution_binding_verification_context=(
                execution_binding_verification_context
            ),
            successor_implementation_sha256=successor_implementation_sha256,
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, rebuilt)
            and document.get("schema_version") == SCHEMA_VERSION
            and document.get("status") == "BLOCKED"
            and document.get("contract_state") == "KNOWN"
            and _sealed_hash_exact(document, "preregistration_hash")
            and _descriptive_authority_locked(document)
        )
    except Exception:
        exact = False
    checks = {
        "exact_rebuild_match": exact,
        "known_blocked_state": exact,
        "authority_remains_locked": exact,
    }
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "preregistration_exactly_verified": exact,
        "preregistration_status": "BLOCKED" if exact else "UNKNOWN",
        "checks": checks,
        "blockers": [] if exact else ["preregistration_v10_exact_rebuild"],
        "writer_allowed": False,
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "ACTIVATION_ORDER",
    "EXECUTION_BINDING_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "SIGNED_REVIEW_VERIFICATION_CONTEXT_KEYS",
    "STATIC_FINGERPRINT",
    "V9_VERIFICATION_CONTEXT_KEYS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10",
]
