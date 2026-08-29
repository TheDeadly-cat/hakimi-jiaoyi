"""Bind a local Node fixture execution receipt without promoting its trust."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-fixture-"
    "execution-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-presentation-fixture-execution-evidence-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
NODE_RECEIPT_SCHEMA_VERSION = (
    "portfolio-risk-freshness-fixture-execution-receipt-v1"
)
NODE_RECEIPT_STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-freshness-fixture-execution-receipt-lock-1"
)
PROJECTION_IMPLEMENTATION_SHA256 = (
    "a983593e70f7dfd707c4933e41422335ccb7825f84c1c689339518e47186f1bf"
)
CARD_IMPLEMENTATION_SHA256 = (
    "0999f934aafe7bcb193e99bfe36362dbc2a91f2015c7d131ce7fb3b252e36f29"
)
FIXTURE_IMPLEMENTATION_SHA256 = (
    "6e9c1da54ed9ee6e8d5ba70d1473d920c67b0c0534bb9110cafb604518430b0d"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_TOP_KEYS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "status",
        "decision",
        "source",
        "verification",
        "checks",
        "blockers",
        "facts",
        "authority",
        "receipt_hash",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "projection_schema_version",
        "projection_hash",
        "projection_implementation_sha256",
        "card_implementation_sha256",
        "fixture_schema_version",
        "fixture_static_fingerprint",
        "fixture_implementation_sha256",
        "execution_environment",
    }
)
_VERIFICATION_KEYS = frozenset(
    {
        "descriptor_exactly_rebuilt",
        "descriptor_status",
        "descriptor_contract_state",
        "descriptor_sha256",
        "stage_order",
    }
)
_CHECK_NAMES = (
    "known_projection_consumed",
    "fixture_descriptor_exact_rebuild",
    "fixture_execution_remained_unmounted",
    "fixture_authority_not_promoted",
)
_FACT_KEYS = frozenset(
    {
        "local_process_execution_observed",
        "node_process_identity_authenticated",
        "receipt_signature_verified",
        "external_execution_authority_verified",
        "projection_document_embedded",
        "fixture_descriptor_embedded",
        "markup_embedded",
        "dom_accessed",
        "browser_visual_review_performed",
        "network_accessed",
        "runtime_consumer_bound",
        "profitability_proven",
    }
)
_AUTHORITY_KEYS = frozenset(
    {
        "descriptive_only",
        "current_admission_allowed",
        "current_pointer_written",
        "live_order_allowed",
        "migration_allowed",
        "paper_authorized",
        "presentation_consumer_activation_allowed",
        "presentation_mount_allowed",
        "runtime_gate_activation_allowed",
        "shadow_consumer_activation_allowed",
        "writer_allowed",
    }
)


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


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


def _exact_dict(value: Any, keys: frozenset[str]) -> dict[str, Any] | None:
    if type(value) is not dict or set(value) != keys:
        return None
    return value


def _receipt_hash_matches(receipt: dict[str, Any]) -> bool:
    observed = _strict_sha256(receipt.get("receipt_hash"))
    body = dict(receipt)
    body.pop("receipt_hash", None)
    try:
        return observed == _canonical_hash(body)
    except (TypeError, ValueError):
        return False


def _checks_pass(value: Any) -> bool:
    if type(value) is not list or len(value) != len(_CHECK_NAMES):
        return False
    for expected_name, item in zip(_CHECK_NAMES, value):
        if (
            type(item) is not dict
            or set(item) != {"name", "ok", "blocking"}
            or item.get("name") != expected_name
            or item.get("ok") is not True
            or item.get("blocking") is not True
        ):
            return False
    return True


def _facts_are_local_only(value: Any) -> bool:
    facts = _exact_dict(value, _FACT_KEYS)
    if facts is None or facts.get("local_process_execution_observed") is not True:
        return False
    return all(
        facts.get(key) is False
        for key in _FACT_KEYS - {"local_process_execution_observed"}
    )


def _authority_locked(value: Any) -> bool:
    authority = _exact_dict(value, _AUTHORITY_KEYS)
    if authority is None or authority.get("descriptive_only") is not True:
        return False
    return all(
        authority.get(key) is False
        for key in _AUTHORITY_KEYS - {"descriptive_only"}
    )


def build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
    node_execution_receipt: Any,
    expected_projection_hash: Any,
) -> dict[str, Any]:
    receipt = _exact_dict(node_execution_receipt, _TOP_KEYS)
    source = _exact_dict(
        receipt.get("source") if receipt is not None else None,
        _SOURCE_KEYS,
    )
    verification = _exact_dict(
        receipt.get("verification") if receipt is not None else None,
        _VERIFICATION_KEYS,
    )
    projection_hash = _strict_sha256(expected_projection_hash)
    exact = bool(
        receipt is not None
        and source is not None
        and verification is not None
        and projection_hash is not None
        and receipt.get("schema_version") == NODE_RECEIPT_SCHEMA_VERSION
        and receipt.get("static_fingerprint") == NODE_RECEIPT_STATIC_FINGERPRINT
        and receipt.get("status") == "PASS"
        and receipt.get("decision")
        == "LOCAL_NODE_FIXTURE_DESCRIPTOR_EXACTLY_REBUILT_UNMOUNTED"
        and source.get("projection_schema_version")
        == "strategy-correlation-cluster-portfolio-risk-projection-v3"
        and source.get("projection_hash") == projection_hash
        and source.get("projection_implementation_sha256")
        == PROJECTION_IMPLEMENTATION_SHA256
        and source.get("card_implementation_sha256")
        == CARD_IMPLEMENTATION_SHA256
        and source.get("fixture_schema_version")
        == "portfolio-risk-freshness-presentation-consumer-fixture-v3"
        and source.get("fixture_static_fingerprint")
        == "20260822-portfolio-risk-freshness-consumer-fixture-lock-1"
        and source.get("fixture_implementation_sha256")
        == FIXTURE_IMPLEMENTATION_SHA256
        and source.get("execution_environment") == "NODE_CONTRACT_PROCESS"
        and verification.get("descriptor_exactly_rebuilt") is True
        and verification.get("descriptor_status") == "PASS"
        and verification.get("descriptor_contract_state") == "KNOWN"
        and _strict_sha256(verification.get("descriptor_sha256"))
        and verification.get("stage_order") == list(STAGE_ORDER)
        and _checks_pass(receipt.get("checks"))
        and receipt.get("blockers") == []
        and _facts_are_local_only(receipt.get("facts"))
        and _authority_locked(receipt.get("authority"))
        and _receipt_hash_matches(receipt)
    )

    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if exact else "BLOCK",
        "decision": (
            "LOCAL_NODE_FIXTURE_EXECUTION_RECEIPT_BOUND_"
            "PROCESS_IDENTITY_SIGNATURE_DOM_AND_BROWSER_UNPROVEN"
            if exact
            else "LOCAL_NODE_FIXTURE_EXECUTION_EVIDENCE_BLOCKED"
        ),
        "source": {
            "node_receipt_schema_version": (
                receipt.get("schema_version") if exact else "UNKNOWN"
            ),
            "node_receipt_hash": (
                receipt.get("receipt_hash") if exact else None
            ),
            "projection_hash": projection_hash if exact else None,
            "descriptor_hash": (
                verification.get("descriptor_sha256") if exact else None
            ),
            "projection_implementation_sha256": PROJECTION_IMPLEMENTATION_SHA256,
            "card_implementation_sha256": CARD_IMPLEMENTATION_SHA256,
            "fixture_implementation_sha256": FIXTURE_IMPLEMENTATION_SHA256,
        },
        "checks": [
            {
                "name": "node_receipt_canonical_hash_and_contract",
                "ok": exact,
                "blocking": True,
            },
            {
                "name": "external_execution_authority_not_promoted",
                "ok": True,
                "blocking": True,
            },
        ],
        "blockers": [] if exact else ["node_fixture_execution_receipt_invalid"],
        "facts": {
            "local_node_fixture_execution_receipt_bound": exact,
            "node_process_identity_authenticated": False,
            "receipt_signature_verified": False,
            "external_execution_authority_verified": False,
            "independent_review_performed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "projection_document_embedded": False,
            "fixture_descriptor_embedded": False,
            "markup_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
        },
        "authority": {
            "descriptive_only": True,
            "current_admission_allowed": False,
            "current_pointer_written": False,
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
    evidence["evidence_hash"] = _canonical_hash(evidence)
    return evidence


def verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
    document: Any,
    node_execution_receipt: Any,
    expected_projection_hash: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1(
        node_execution_receipt,
        expected_projection_hash,
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "evidence_exactly_verified": exact,
        "evidence_status": expected.get("status") if exact else "UNKNOWN",
        "blockers": [] if exact else ["fixture_execution_evidence_exact_rebuild"],
        "browser_visual_review_verified": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "CARD_IMPLEMENTATION_SHA256",
    "FIXTURE_IMPLEMENTATION_SHA256",
    "NODE_RECEIPT_SCHEMA_VERSION",
    "NODE_RECEIPT_STATIC_FINGERPRINT",
    "PROJECTION_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STAGE_ORDER",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1",
]
