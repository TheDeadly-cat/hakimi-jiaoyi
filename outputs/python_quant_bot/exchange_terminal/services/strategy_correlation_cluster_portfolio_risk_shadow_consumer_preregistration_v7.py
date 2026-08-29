"""Immutable shadow preregistration v7 for presentation consumer contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
    as presentation_registration_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6
    as preregistration_v6,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v7"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-preregistration-v7-"
    "presentation-registration-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "SUCCESSOR_PREREGISTERED_ADR0192_ADR0193_CONTRACTS_PINNED_"
    "EVIDENCE_REGISTRATION_DOM_BROWSER_HTTP_AND_MOUNT_NOT_BOUND"
)
V6_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v5_document",
        "v5_verification_context",
        "v6_implementation_sha256",
    }
)

_EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256 = {
    "shadow_preregistration_v6": (
        "5e609926baea27c13fd11c072dc9b153296332db37eda81e3e996525667bbd0f"
    ),
    "portfolio_risk_freshness_gate_consumer_fixture_v3_js": (
        "6e9c1da54ed9ee6e8d5ba70d1473d920c67b0c0534bb9110cafb604518430b0d"
    ),
    "portfolio_risk_presentation_consumer_registration_v1": (
        "6a5b4cd9a8a0e3552ec34b355c9a27f4560b5621557d605413aa8076c769cc7e"
    ),
}

_SUCCESSOR_ARTIFACT_PATHS = {
    "shadow_preregistration_v6": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_shadow_consumer_"
        "preregistration_v6.py"
    ),
    "portfolio_risk_freshness_gate_consumer_fixture_v3_js": (
        "exchange_terminal/static/"
        "evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js"
    ),
    "portfolio_risk_presentation_consumer_registration_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_presentation_"
        "consumer_registration_v1.py"
    ),
}

_NEW_BLOCKERS = (
    "presentation_consumer_fixture_v3_execution_evidence_not_bound",
    "presentation_consumer_registration_candidate_v1_evidence_not_bound",
)

_EXPECTED_REGISTRATION_DOCUMENT_HASH = (
    "eab3477889e172c337cc231e493f307f7929c006d476fcb4fb204359a30bc6e3"
)


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _strict_sha256(value: Any) -> str | None:
    if type(value) is not str or len(value) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected_shadow_consumer_successor_implementation_sha256_v7() -> dict[str, str]:
    return dict(_EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)


def _exact_v6_context(value: Any) -> dict[str, Any] | None:
    if type(value) is not dict or set(value) != V6_VERIFICATION_CONTEXT_KEYS:
        return None
    return value


def _verify_v6(document: Any, context: dict[str, Any] | None) -> dict[str, Any]:
    if context is None:
        return {}
    try:
        return preregistration_v6.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
            document,
            context["preregistration_v5_document"],
            context["v5_verification_context"],
            context["v6_implementation_sha256"],
        )
    except Exception:
        return {}


def _authority_locked(value: Any) -> bool:
    authority = _dict(value)
    return bool(authority) and all(
        authority.get(key) is False
        for key in (
            "current_admission_allowed",
            "current_pointer_written",
            "formal_registry_activation_allowed",
            "live_order_allowed",
            "migration_allowed",
            "paper_authorized",
            "presentation_consumer_activation_allowed",
            "runtime_gate_activation_allowed",
            "shadow_consumer_activation_allowed",
            "writer_allowed",
        )
    )


def _extend_activation_order(predecessor_order: list[Any]) -> list[str]:
    order = [item for item in predecessor_order if type(item) is str]
    current = "SEPARATELY_AUTHORIZE_CURRENT_SWITCH"
    if order and order[-1] == current:
        order = order[:-1]
    marker = "AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW_V3"
    insertion = [
        "EXECUTE_ADR0192_FIXTURE_WITH_SYNTHETIC_PROJECTION_MATRIX",
        "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
        "BIND_AND_EXACTLY_VERIFY_ADR0193_PRESENTATION_REGISTRATION_CANDIDATE",
    ]
    if marker in order:
        index = order.index(marker)
        order = order[:index] + insertion + order[index:]
    else:
        order.extend(insertion)
    return order + [
        "SEPARATELY_AUTHORIZE_PRESENTATION_REGISTRATION_ACTIVATION",
        "SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT",
        current,
    ]


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7(
    preregistration_v6_document: Any,
    v6_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    context = _exact_v6_context(v6_verification_context)
    predecessor = _dict(preregistration_v6_document)
    receipt = _verify_v6(preregistration_v6_document, context)
    predecessor_exact = bool(
        context is not None
        and receipt.get("status") == "PASS"
        and receipt.get("preregistration_exactly_verified") is True
        and receipt.get("preregistration_status") == "BLOCKED"
        and predecessor.get("schema_version") == preregistration_v6.SCHEMA_VERSION
        and predecessor.get("static_fingerprint")
        == preregistration_v6.STATIC_FINGERPRINT
        and predecessor.get("status") == preregistration_v6.STATUS
        and _strict_sha256(predecessor.get("preregistration_hash"))
        and _authority_locked(predecessor.get("authority"))
        and all(
            receipt.get(key) is False
            for key in (
                "current_admission_allowed",
                "live_order_allowed",
                "paper_authorized",
                "presentation_consumer_activation_allowed",
                "runtime_gate_activation_allowed",
                "shadow_consumer_activation_allowed",
                "writer_allowed",
            )
        )
    )
    successor_manifest_exact = bool(
        type(successor_implementation_sha256) is dict
        and successor_implementation_sha256
        == _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
    )
    inputs_valid = predecessor_exact and successor_manifest_exact

    predecessor_blockers = (
        copy.deepcopy(_list(predecessor.get("blockers")))
        if predecessor_exact
        else []
    )
    blockers = predecessor_blockers + list(_NEW_BLOCKERS)
    if not predecessor_exact:
        blockers.insert(0, "immutable_v6_exact_verification_failed")
    if not successor_manifest_exact:
        blockers.insert(0, "successor_implementation_manifest_mismatch")

    predecessor_pin_count = (
        _dict(predecessor.get("facts")).get("implementation_pin_count")
        if predecessor_exact
        else 0
    )
    if type(predecessor_pin_count) is not int or predecessor_pin_count < 0:
        predecessor_pin_count = 0

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION if inputs_valid else "PREREGISTRATION_INPUT_INVALID_FAIL_CLOSED",
        "source": {
            "immutable_v6_schema_version": (
                predecessor.get("schema_version") if predecessor_exact else "UNKNOWN"
            ),
            "immutable_v6_preregistration_hash": (
                predecessor.get("preregistration_hash") if predecessor_exact else None
            ),
            "immutable_v6_implementation_sha256": (
                _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v6"
                ]
            ),
            "immutable_v6_exactly_verified": predecessor_exact,
            "successor_manifest_contract_verified": successor_manifest_exact,
            "successor_implementation_fingerprints_match": successor_manifest_exact,
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "total_implementation_pin_count": predecessor_pin_count
            + len(_EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256),
            "new_artifacts": [
                {
                    "artifact_id": artifact_id,
                    "path": _SUCCESSOR_ARTIFACT_PATHS[artifact_id],
                    "expected_sha256": expected_sha256,
                }
                for artifact_id, expected_sha256 in sorted(
                    _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256.items()
                )
            ],
        },
        "contract_pins": {
            "immutable_v6_schema_version": preregistration_v6.SCHEMA_VERSION,
            "immutable_v6_static_fingerprint": preregistration_v6.STATIC_FINGERPRINT,
            "immutable_v6_preregistration_hash": (
                predecessor.get("preregistration_hash") if predecessor_exact else None
            ),
            "immutable_v6_contract_pins": (
                copy.deepcopy(_dict(predecessor.get("contract_pins")))
                if predecessor_exact
                else {}
            ),
            "consumer_fixture_schema_version": (
                "portfolio-risk-freshness-presentation-consumer-fixture-v3"
            ),
            "consumer_fixture_static_fingerprint": (
                "20260822-portfolio-risk-freshness-consumer-fixture-lock-1"
            ),
            "consumer_fixture_global_name": (
                "HakimiPortfolioRiskFreshnessGateConsumerFixtureV3"
            ),
            "consumer_fixture_javascript_sha256": (
                _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "portfolio_risk_freshness_gate_consumer_fixture_v3_js"
                ]
            ),
            "presentation_registration_schema_version": (
                presentation_registration_v1.SCHEMA_VERSION
            ),
            "presentation_registration_static_fingerprint": (
                presentation_registration_v1.STATIC_FINGERPRINT
            ),
            "presentation_registration_verification_schema_version": (
                presentation_registration_v1.VERIFICATION_SCHEMA_VERSION
            ),
            "presentation_registration_implementation_sha256": (
                _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                    "portfolio_risk_presentation_consumer_registration_v1"
                ]
            ),
            "presentation_registration_expected_document_hash": (
                _EXPECTED_REGISTRATION_DOCUMENT_HASH
            ),
            "presentation_registration_status": presentation_registration_v1.STATUS,
            "presentation_registration_binding_policy": (
                "PIN_CANDIDATE_IMPLEMENTATION_AND_EXPECTED_DOCUMENT_HASH_"
                "WITHOUT_ACCEPTING_REGISTRATION_EVIDENCE_V1"
            ),
        },
        "required_shadow_input_schemas": (
            copy.deepcopy(_list(predecessor.get("required_shadow_input_schemas")))
            if predecessor_exact
            else []
        ),
        "closed_local_blockers": (
            copy.deepcopy(_list(predecessor.get("closed_local_blockers")))
            if predecessor_exact
            else []
        ),
        "blocker_refinements": (
            copy.deepcopy(_list(predecessor.get("blocker_refinements")))
            if predecessor_exact
            else []
        )
        + [
            {
                "source_blocker": "presentation_consumer_v3_registered",
                "source_blocker_closed": False,
                "local_contract_state": (
                    "ADR0192_FIXTURE_AND_ADR0193_REGISTRATION_CANDIDATE_PINNED_"
                    "NO_EXECUTION_OR_REGISTRATION_EVIDENCE_BOUND"
                ),
                "remaining_requirements": list(_NEW_BLOCKERS),
            }
        ],
        "newly_pinned_local_capabilities": [
            {
                "capability": "PORTFOLIO_RISK_PRESENTATION_CONSUMER_FIXTURE_V3",
                "contract_pinned": successor_manifest_exact,
                "evidence_bound": False,
                "consumer_executed": False,
                "external_authority_verified": False,
                "pin": "ADR0192_FIXTURE_IMPLEMENTATION_SCHEMA_AND_FINGERPRINT_PINNED",
            },
            {
                "capability": "PORTFOLIO_RISK_PRESENTATION_CONSUMER_REGISTRATION_V1",
                "contract_pinned": successor_manifest_exact,
                "evidence_bound": False,
                "consumer_executed": False,
                "external_authority_verified": False,
                "pin": "ADR0193_REGISTRATION_IMPLEMENTATION_AND_EXPECTED_DOCUMENT_HASH_PINNED",
            },
        ],
        "reuse_plan": (
            copy.deepcopy(_list(predecessor.get("reuse_plan")))
            if predecessor_exact
            else []
        )
        + [
            {
                "capability": "PRESENTATION_RENDER_COMPOSITION",
                "decision": "REUSE_ADR0192_DOM_FREE_FIXTURE_NO_MOUNT",
            },
            {
                "capability": "PRESENTATION_CONSUMER_REGISTRATION",
                "decision": "REUSE_ADR0193_STATIC_CANDIDATE_NO_ACTIVATION",
            },
        ],
        "blockers": blockers,
        "activation_order": _extend_activation_order(
            copy.deepcopy(_list(predecessor.get("activation_order")))
            if predecessor_exact
            else []
        ),
        "facts": {
            "immutable_v6_exactly_verified": predecessor_exact,
            "required_shadow_input_count": (
                len(_list(predecessor.get("required_shadow_input_schemas")))
                if predecessor_exact
                else 0
            ),
            "closed_local_blocker_count": (
                len(_list(predecessor.get("closed_local_blockers")))
                if predecessor_exact
                else 0
            ),
            "predecessor_implementation_pin_count": predecessor_pin_count,
            "successor_implementation_pin_count": len(
                _EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
            ),
            "implementation_pin_count": predecessor_pin_count
            + len(_EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256),
            "consumer_fixture_v3_contract_pinned": successor_manifest_exact,
            "presentation_registration_v1_contract_pinned": successor_manifest_exact,
            "presentation_registration_expected_hash_pinned": successor_manifest_exact,
            "consumer_fixture_v3_execution_evidence_bound": False,
            "consumer_fixture_v3_executed": False,
            "presentation_registration_v1_evidence_bound": False,
            "presentation_registration_v1_exactly_verified": False,
            "presentation_registration_v1_activated": False,
            "dom_contract_v3_reviewed": False,
            "browser_visual_review_v3_performed": False,
            "presentation_http_contract_v3_versioned": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "ui_mounted": False,
        },
        "authority": {
            "descriptive_only": True,
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "formal_registry_activation_allowed": False,
            "live_order_allowed": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_mount_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    document["preregistration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7(
    document: Any,
    preregistration_v6_document: Any,
    v6_verification_context: Any,
    successor_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7(
        preregistration_v6_document,
        v6_verification_context,
        successor_implementation_sha256,
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "preregistration_exactly_verified": exact,
        "preregistration_status": expected.get("status") if exact else "UNKNOWN",
        "blockers": [] if exact else ["preregistration_v7_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "DECISION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS",
    "V6_VERIFICATION_CONTEXT_KEYS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7",
    "expected_shadow_consumer_successor_implementation_sha256_v7",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7",
]
