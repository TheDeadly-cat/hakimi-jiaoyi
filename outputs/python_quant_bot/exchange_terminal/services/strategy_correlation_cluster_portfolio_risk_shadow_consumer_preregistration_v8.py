"""Evidence-aware shadow consumer preregistration v8.

V8 consumes the exact ADR0197 local registration evidence binding and closes
two local evidence blockers.  It remains a detached preregistration with every
activation and trading authority denied.
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
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
    as preregistration_v7,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
    as execution_binding_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1
    as registration_evidence_binding_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v8"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-preregistration-v8-local-evidence-closures-lock-1"
)

V7_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v6_document",
        "v6_verification_context",
        "successor_implementation_sha256",
    }
)
REGISTRATION_EVIDENCE_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "execution_binding_document",
        "registration_candidate_document",
        "execution_binding_verification_context",
        "registration_candidate_verification_context",
        "current_implementation_sha256",
    }
)

EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256 = {
    "shadow_preregistration_v7": (
        "f2d3f688e6841e709f5a108bb56542d6930758b57cfab8299f2e6750e06caf95"
    ),
    "presentation_execution_evidence_binding_v1": (
        "b40e50db01e5bb5d6c8c19944f46edceca3a1c420cfb519a5ecf68f50c8d855d"
    ),
    "presentation_registration_evidence_binding_v1": (
        "f57a39c5dd3fadac47ed7883700bb76f31b66eb63a7fba39ca3c772c24f6b8ff"
    ),
}

_VERIFY_V7 = getattr(
    preregistration_v7,
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_"
    "preregistration_v7",
    None,
)
_VERIFY_REGISTRATION_EVIDENCE = getattr(
    registration_evidence_binding_v1,
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_"
    "registration_evidence_binding_v1",
    None,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MISSING = object()
_CLOSED_EVIDENCE_BLOCKERS = frozenset(
    {
        "presentation_consumer_fixture_v3_execution_evidence_not_bound",
        "presentation_consumer_registration_candidate_v1_evidence_not_bound",
    }
)
_NEW_REMAINING_BLOCKERS = (
    "presentation_render_descriptor_independent_review_missing",
    "presentation_consumer_registration_activation_unauthorized",
)
_COMPLETED_ACTIVATION_STEPS = frozenset(
    {
        "REGISTER_UNMOUNTED_PRESENTATION_CONSUMER_FIXTURE_V3",
        "EXECUTE_ADR0192_FIXTURE_WITH_SYNTHETIC_PROJECTION_MATRIX",
        "BIND_AND_EXACTLY_VERIFY_ADR0193_PRESENTATION_REGISTRATION_CANDIDATE",
    }
)


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


def _call_v7_verifier(document: Any, context: Any) -> tuple[dict[str, Any], bool]:
    if not _exact_context(context, V7_VERIFICATION_CONTEXT_KEYS) or not callable(
        _VERIFY_V7
    ):
        return {}, False
    try:
        receipt = _VERIFY_V7(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration_v6_document"]),
            copy.deepcopy(context["v6_verification_context"]),
            copy.deepcopy(context["successor_implementation_sha256"]),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _call_registration_evidence_verifier(
    document: Any,
    preregistration_v7_document: Any,
    context: Any,
) -> tuple[dict[str, Any], bool]:
    if not _exact_context(
        context, REGISTRATION_EVIDENCE_VERIFICATION_CONTEXT_KEYS
    ) or not callable(_VERIFY_REGISTRATION_EVIDENCE):
        return {}, False
    try:
        receipt = _VERIFY_REGISTRATION_EVIDENCE(
            copy.deepcopy(document),
            copy.deepcopy(preregistration_v7_document),
            copy.deepcopy(context["execution_binding_document"]),
            copy.deepcopy(context["registration_candidate_document"]),
            execution_binding_verification_context=copy.deepcopy(
                context["execution_binding_verification_context"]
            ),
            registration_candidate_verification_context=copy.deepcopy(
                context["registration_candidate_verification_context"]
            ),
            current_implementation_sha256=copy.deepcopy(
                context["current_implementation_sha256"]
            ),
        )
    except Exception:
        return {}, False
    return (receipt, _verification_passed(receipt)) if type(receipt) is dict else ({}, False)


def _successor_manifest_exact(value: Any) -> bool:
    if type(value) is not dict or set(value) != set(
        EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
    ):
        return False
    return all(
        _is_hash(value.get(key))
        and hmac.compare_digest(value[key], expected)
        for key, expected in EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256.items()
    )


def _verification_checks(
    preregistration_v7_document: Any,
    registration_evidence_binding_document: Any,
    *,
    v7_verification_context: Any,
    registration_evidence_binding_verification_context: Any,
    successor_implementation_sha256: Any,
) -> tuple[dict[str, bool], dict[str, Any], dict[str, Any]]:
    v7_context_exact = _exact_context(
        v7_verification_context, V7_VERIFICATION_CONTEXT_KEYS
    )
    evidence_context_exact = _exact_context(
        registration_evidence_binding_verification_context,
        REGISTRATION_EVIDENCE_VERIFICATION_CONTEXT_KEYS,
    )
    v7_receipt, v7_exact = _call_v7_verifier(
        preregistration_v7_document, v7_verification_context
    )
    evidence_receipt, evidence_exact = _call_registration_evidence_verifier(
        registration_evidence_binding_document,
        preregistration_v7_document,
        registration_evidence_binding_verification_context,
    )

    v7_hash = (
        _sha256(preregistration_v7_document)
        if type(preregistration_v7_document) is dict
        else None
    )
    evidence_v7_hash = _hash_at(
        registration_evidence_binding_document,
        "source_hashes",
        "shadow_preregistration_v7_document_sha256",
    )
    evidence_execution_implementation = _hash_at(
        registration_evidence_binding_document,
        "source_hashes",
        "presentation_execution_evidence_binding_v1_implementation_sha256",
    )
    evidence_registration_implementation = _hash_at(
        registration_evidence_binding_document,
        "source_hashes",
        "presentation_registration_candidate_v1_implementation_sha256",
    )

    checks = {
        "v7_verification_context_exact": v7_context_exact,
        "registration_evidence_verification_context_exact": evidence_context_exact,
        "immutable_v7_exactly_verified": v7_exact,
        "registration_evidence_binding_exactly_verified": evidence_exact,
        "successor_implementation_manifest_exact": _successor_manifest_exact(
            successor_implementation_sha256
        ),
        "immutable_v7_remains_blocked": (
            type(preregistration_v7_document) is dict
            and preregistration_v7_document.get("status") == "BLOCKED"
        ),
        "registration_evidence_binding_status_pass": (
            type(registration_evidence_binding_document) is dict
            and registration_evidence_binding_document.get("schema")
            == registration_evidence_binding_v1.SCHEMA
            and registration_evidence_binding_document.get("status") == "PASS"
        ),
        "registration_evidence_v7_document_identity": _same_hash(
            v7_hash, evidence_v7_hash
        ),
        "execution_binding_implementation_identity": _same_hash(
            evidence_execution_implementation,
            EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                "presentation_execution_evidence_binding_v1"
            ],
        ),
        "registration_candidate_implementation_identity": _same_hash(
            evidence_registration_implementation,
            _path(
                preregistration_v7_document,
                "contract_pins",
                "presentation_registration_implementation_sha256",
            ),
        ),
        "fixture_execution_evidence_bound": (
            _path(
                registration_evidence_binding_document,
                "facts",
                "local_fixture_execution_evidence_bound",
            )
            is True
        ),
        "registration_candidate_evidence_bound": (
            _path(
                registration_evidence_binding_document,
                "facts",
                "registration_candidate_evidence_bound_in_successor",
            )
            is True
            and _path(
                registration_evidence_binding_document,
                "facts",
                "registration_candidate_exactly_verified",
            )
            is True
        ),
        "registration_activation_remains_false": (
            _path(
                registration_evidence_binding_document,
                "facts",
                "registration_activated",
            )
            is False
        ),
        "all_source_authority_locked": (
            _authority_locked(preregistration_v7_document)
            and _authority_locked(registration_evidence_binding_document)
        ),
        "verification_receipts_summary_only": (
            type(v7_receipt) is dict
            and type(evidence_receipt) is dict
            and "document" not in v7_receipt
            and "document" not in evidence_receipt
        ),
        "source_hashes_valid": (
            _is_hash(v7_hash)
            and _is_hash(
                _hash_at(registration_evidence_binding_document, "binding_sha256")
            )
            and _is_hash(evidence_execution_implementation)
            and _is_hash(evidence_registration_implementation)
        ),
    }
    receipts = {
        "v7": v7_receipt,
        "registration_evidence": evidence_receipt,
    }
    source = {
        "immutable_v7_document_sha256": v7_hash,
        "registration_evidence_binding_sha256": _hash_at(
            registration_evidence_binding_document, "binding_sha256"
        ),
        "registration_evidence_projection_document_sha256": _hash_at(
            registration_evidence_binding_document,
            "source_hashes",
            "projection_document_sha256",
        ),
        "registration_evidence_fixture_descriptor_sha256": _hash_at(
            registration_evidence_binding_document,
            "source_hashes",
            "fixture_descriptor_sha256",
        ),
    }
    return checks, receipts, source


def _closed_local_blockers(
    preregistration_v7_document: Any,
    registration_evidence_hash: str | None,
    contract_known: bool,
) -> list[Any]:
    predecessor = _path(preregistration_v7_document, "closed_local_blockers")
    result = copy.deepcopy(predecessor) if type(predecessor) is list else []
    if not contract_known:
        return result
    result.extend(
        [
            {
                "blocker": (
                    "presentation_consumer_fixture_v3_execution_evidence_not_bound"
                ),
                "closure": (
                    "ADR0196_LOCAL_FIXTURE_EXECUTION_EVIDENCE_EXACTLY_BOUND"
                ),
                "closure_verified": True,
                "evidence_binding_sha256": registration_evidence_hash,
            },
            {
                "blocker": (
                    "presentation_consumer_registration_candidate_v1_"
                    "evidence_not_bound"
                ),
                "closure": (
                    "ADR0197_LOCAL_REGISTRATION_CANDIDATE_EVIDENCE_EXACTLY_"
                    "BOUND_ACTIVATION_UNAUTHORIZED"
                ),
                "closure_verified": True,
                "evidence_binding_sha256": registration_evidence_hash,
            },
        ]
    )
    return result


def _remaining_blockers(
    preregistration_v7_document: Any, contract_known: bool
) -> list[Any]:
    predecessor = _path(preregistration_v7_document, "blockers")
    result = copy.deepcopy(predecessor) if type(predecessor) is list else []
    if not contract_known:
        return result
    result = [item for item in result if item not in _CLOSED_EVIDENCE_BLOCKERS]
    for blocker in _NEW_REMAINING_BLOCKERS:
        if blocker not in result:
            result.append(blocker)
    return result


def _blocker_refinements(
    preregistration_v7_document: Any, contract_known: bool
) -> list[Any]:
    predecessor = _path(preregistration_v7_document, "blocker_refinements")
    result = copy.deepcopy(predecessor) if type(predecessor) is list else []
    if not contract_known:
        return result
    retained = [
        item
        for item in result
        if type(item) is not dict
        or item.get("source_blocker") != "presentation_consumer_v3_registered"
    ]
    retained.append(
        {
            "source_blocker": "presentation_consumer_v3_registered",
            "source_blocker_closed": False,
            "local_contract_state": (
                "ADR0196_FIXTURE_EXECUTION_AND_ADR0197_REGISTRATION_"
                "CANDIDATE_EVIDENCE_EXACTLY_BOUND_ACTIVATION_UNAUTHORIZED"
            ),
            "remaining_requirements": [
                "presentation_render_descriptor_independent_review_missing",
                "isolated_dom_contract_review_not_performed",
                "browser_visual_review_v3_not_performed",
                "presentation_http_contract_v3_not_versioned",
                "presentation_consumer_registration_activation_unauthorized",
                "presentation_mount_unauthorized",
                "current_switch_unauthorized",
            ],
        }
    )
    return retained


def _activation_order(preregistration_v7_document: Any, contract_known: bool) -> list[Any]:
    predecessor = _path(preregistration_v7_document, "activation_order")
    result = copy.deepcopy(predecessor) if type(predecessor) is list else []
    if not contract_known:
        return result
    return [item for item in result if item not in _COMPLETED_ACTIVATION_STEPS]


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
    preregistration_v7_document: Mapping[str, Any],
    registration_evidence_binding_document: Mapping[str, Any],
    *,
    v7_verification_context: Mapping[str, Any],
    registration_evidence_binding_verification_context: Mapping[str, Any],
    successor_implementation_sha256: Mapping[str, str],
) -> dict[str, Any]:
    checks, _receipts, source_hashes = _verification_checks(
        preregistration_v7_document,
        registration_evidence_binding_document,
        v7_verification_context=v7_verification_context,
        registration_evidence_binding_verification_context=(
            registration_evidence_binding_verification_context
        ),
        successor_implementation_sha256=successor_implementation_sha256,
    )
    contract_known = all(checks.values())
    evidence_hash = source_hashes["registration_evidence_binding_sha256"]
    predecessor_facts = _path(preregistration_v7_document, "facts")
    required_inputs = _path(
        preregistration_v7_document, "required_shadow_input_schemas"
    )
    reuse_plan = _path(preregistration_v7_document, "reuse_plan")
    predecessor_pin_count = (
        predecessor_facts.get("implementation_pin_count")
        if type(predecessor_facts) is dict
        else None
    )
    total_pin_count = (
        predecessor_pin_count + len(EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)
        if type(predecessor_pin_count) is int
        and type(predecessor_pin_count) is not bool
        else None
    )
    closed_local_blockers = _closed_local_blockers(
        preregistration_v7_document, evidence_hash, contract_known
    )
    reuse = copy.deepcopy(reuse_plan) if type(reuse_plan) is list else []
    if contract_known:
        reuse.extend(
            [
                {
                    "capability": "PRESENTATION_FIXTURE_EXECUTION_EVIDENCE",
                    "decision": (
                        "REUSE_ADR0196_EXACT_LOCAL_EVIDENCE_RUNTIME_UNBOUND"
                    ),
                },
                {
                    "capability": "PRESENTATION_REGISTRATION_EVIDENCE",
                    "decision": (
                        "REUSE_ADR0197_EXACT_LOCAL_EVIDENCE_ACTIVATION_"
                        "UNAUTHORIZED"
                    ),
                },
            ]
        )

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "contract_state": "KNOWN" if contract_known else "UNKNOWN",
        "decision": (
            "SUCCESSOR_PREREGISTERED_LOCAL_FIXTURE_AND_REGISTRATION_EVIDENCE_"
            "BOUND_INDEPENDENT_DOM_BROWSER_HTTP_MOUNT_CURRENT_UNAUTHORIZED"
            if contract_known
            else "SUCCESSOR_PREREGISTRATION_BLOCKED_EXACT_LOCAL_EVIDENCE_"
            "CLOSURES_NOT_PROVEN"
        ),
        "source": {
            "immutable_v7_exactly_verified": checks[
                "immutable_v7_exactly_verified"
            ],
            "immutable_v7_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v7"
                ]
            ),
            "immutable_v7_preregistration_hash": _hash_at(
                preregistration_v7_document, "preregistration_hash"
            ),
            "registration_evidence_binding_exactly_verified": checks[
                "registration_evidence_binding_exactly_verified"
            ],
            "registration_evidence_binding_sha256": evidence_hash,
            "successor_manifest_contract_verified": checks[
                "successor_implementation_manifest_exact"
            ],
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "total_implementation_pin_count": total_pin_count,
            "new_artifacts": [
                {
                    "artifact_id": "shadow_preregistration_v7",
                    "path": (
                        "exchange_terminal/services/strategy_correlation_cluster_"
                        "portfolio_risk_shadow_consumer_preregistration_v7.py"
                    ),
                    "expected_sha256": EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "shadow_preregistration_v7"
                    ],
                },
                {
                    "artifact_id": (
                        "presentation_execution_evidence_binding_v1"
                    ),
                    "path": (
                        "exchange_terminal/services/strategy_correlation_cluster_"
                        "portfolio_risk_shadow_presentation_execution_evidence_"
                        "binding_v1.py"
                    ),
                    "expected_sha256": EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "presentation_execution_evidence_binding_v1"
                    ],
                },
                {
                    "artifact_id": (
                        "presentation_registration_evidence_binding_v1"
                    ),
                    "path": (
                        "exchange_terminal/services/strategy_correlation_cluster_"
                        "portfolio_risk_shadow_presentation_registration_evidence_"
                        "binding_v1.py"
                    ),
                    "expected_sha256": EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "presentation_registration_evidence_binding_v1"
                    ],
                },
            ],
            "verification_checks": checks,
            "evidence_summary_hashes": source_hashes,
        },
        "contract_pins": {
            "immutable_v7_contract_pins": copy.deepcopy(
                _path(preregistration_v7_document, "contract_pins")
            ),
            "immutable_v7_schema_version": _path(
                preregistration_v7_document, "schema_version"
            ),
            "immutable_v7_static_fingerprint": _path(
                preregistration_v7_document, "static_fingerprint"
            ),
            "immutable_v7_preregistration_hash": _hash_at(
                preregistration_v7_document, "preregistration_hash"
            ),
            "immutable_v7_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v7"
                ]
            ),
            "presentation_execution_evidence_binding_schema_version": (
                execution_binding_v1.SCHEMA
            ),
            "presentation_execution_evidence_binding_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "presentation_execution_evidence_binding_v1"
                ]
            ),
            "presentation_registration_evidence_binding_schema_version": (
                registration_evidence_binding_v1.SCHEMA
            ),
            "presentation_registration_evidence_binding_static_fingerprint": (
                registration_evidence_binding_v1.STATIC_FINGERPRINT
            ),
            "presentation_registration_evidence_binding_implementation_sha256": (
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "presentation_registration_evidence_binding_v1"
                ]
            ),
            "local_evidence_closure_policy": (
                "EXACT_ADR0197_PUBLIC_REVERIFICATION_SAME_V7_DOCUMENT_AND_"
                "THREE_IMPLEMENTATION_PINS_V1"
            ),
        },
        "required_shadow_input_schemas": (
            copy.deepcopy(required_inputs) if type(required_inputs) is list else []
        ),
        "closed_local_blockers": closed_local_blockers,
        "blocker_refinements": _blocker_refinements(
            preregistration_v7_document, contract_known
        ),
        "blockers": _remaining_blockers(
            preregistration_v7_document, contract_known
        ),
        "reuse_plan": reuse,
        "activation_order": _activation_order(
            preregistration_v7_document, contract_known
        ),
        "facts": {
            "immutable_v7_exactly_verified": checks[
                "immutable_v7_exactly_verified"
            ],
            "registration_evidence_binding_exactly_verified": checks[
                "registration_evidence_binding_exactly_verified"
            ],
            "local_evidence_closure_count": 2 if contract_known else 0,
            "required_shadow_input_count": (
                len(required_inputs) if type(required_inputs) is list else 0
            ),
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "implementation_pin_count": total_pin_count,
            "closed_local_blocker_count": len(closed_local_blockers),
            "consumer_fixture_v3_executed": contract_known,
            "consumer_fixture_v3_execution_evidence_bound": contract_known,
            "presentation_registration_v1_exactly_verified": contract_known,
            "presentation_registration_v1_evidence_bound": contract_known,
            "presentation_registration_v1_activated": False,
            "render_descriptor_independently_reviewed": False,
            "dom_contract_v3_reviewed": False,
            "browser_visual_review_v3_performed": False,
            "presentation_http_contract_v3_versioned": False,
            "server_route_registered": False,
            "ui_mounted": False,
            "runtime_assets_accessed": False,
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
            "formal_registry_activation_allowed": False,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    document["preregistration_hash"] = _sha256(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
    document: Any,
    preregistration_v7_document: Any,
    registration_evidence_binding_document: Any,
    *,
    v7_verification_context: Any,
    registration_evidence_binding_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
        preregistration_v7_document,
        registration_evidence_binding_document,
        v7_verification_context=v7_verification_context,
        registration_evidence_binding_verification_context=(
            registration_evidence_binding_verification_context
        ),
        successor_implementation_sha256=successor_implementation_sha256,
    )
    document_is_dict = type(document) is dict
    supplied_hash = document.get("preregistration_hash") if document_is_dict else None
    unhashed = copy.deepcopy(document) if document_is_dict else {}
    unhashed.pop("preregistration_hash", None)
    checks = {
        "document_is_exact_dict": document_is_dict,
        "schema_version_exact": (
            document_is_dict and document.get("schema_version") == SCHEMA_VERSION
        ),
        "static_fingerprint_exact": (
            document_is_dict
            and document.get("static_fingerprint") == STATIC_FINGERPRINT
        ),
        "status_remains_blocked": (
            document_is_dict and document.get("status") == "BLOCKED"
        ),
        "contract_state_known": (
            document_is_dict and document.get("contract_state") == "KNOWN"
        ),
        "preregistration_hash_valid": _is_hash(supplied_hash),
        "preregistration_hash_exact": (
            _is_hash(supplied_hash)
            and hmac.compare_digest(supplied_hash, _sha256(unhashed))
        ),
        "exact_rebuild_match": document_is_dict and document == rebuilt,
        "rebuilt_contract_state_known": rebuilt.get("contract_state") == "KNOWN",
        "authority_remains_locked": _authority_locked(rebuilt),
    }
    verified = all(checks.values())
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if verified else "BLOCK",
        "preregistration_exactly_verified": verified,
        "preregistration_status": "BLOCKED" if verified else "UNKNOWN",
        "blockers": [] if verified else ["preregistration_v8_exact_rebuild"],
        "checks": checks,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V7_VERIFICATION_CONTEXT_KEYS",
    "REGISTRATION_EVIDENCE_VERIFICATION_CONTEXT_KEYS",
    "EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8",
]
