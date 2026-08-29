from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
    as registration_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v5 as projection_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "execution-evidence-v3"
)
STATIC_FINGERPRINT = (
    "20260823-consumer-v5-receipt-v3-python-evidence-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
RECEIPT_V3_SCHEMA_VERSION = (
    "portfolio-risk-joint-evidence-consumer-execution-receipt-v3"
)
RECEIPT_V3_STATIC_FINGERPRINT = (
    "20260823-joint-evidence-consumer-v5-node-execution-receipt-v3-lock-1"
)
RECEIPT_V3_IMPLEMENTATION_SHA256 = (
    "9a90650656f63cd8026fcee224ed4e3d690ced6a7d8bd2970772c653e55c2acb"
)
PROJECTION_V5_IMPLEMENTATION_SHA256 = (
    "eadaec98c0b2882b28a6523779a02171afd39e7f5ed0caf0d581bfd81ee983c1"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
CARD_V5_JAVASCRIPT_SHA256 = (
    "8282b85316a2d238202d2a553af775f98be9f829ad86a49ab0463654bb9c358d"
)
CARD_V5_STYLESHEET_SHA256 = (
    "90ea35644b6d7fdc33f0bb1b1025ab37d6a876d10be00ec81e9b7a257552ed1a"
)
CONSUMER_V5_JAVASCRIPT_SHA256 = (
    "401a16ab303eec51e4a5d65f51e6ca4250f3bb1c281b8b07adb193ec89de8849"
)
REGISTRATION_V4_IMPLEMENTATION_SHA256 = (
    "b7b0b8faf64d34796b6ae97e6594ea08a0fcd930272fa4841e4a7bd0ebecd897"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_RECEIPT_AUTHORITY = {
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
}
_PROJECTION_AUTHORITY = {
    "research_only": True,
    "presentation_only": True,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registry_activation_allowed": False,
    "live_order_allowed": False,
    "migration_allowed": False,
    "paper_authorized": False,
    "runtime_gate_activation_allowed": False,
    "shadow_consumer_activation_allowed": False,
    "writer_allowed": False,
}
_RECEIPT_FACTS = {
    "local_process_execution_observed": True,
    "node_process_identity_authenticated": False,
    "receipt_signature_verified": False,
    "external_execution_authority_verified": False,
    "projection_document_embedded": False,
    "consumer_descriptor_embedded": False,
    "source_evidence_embedded": False,
    "markup_embedded": False,
    "stylesheet_declared": True,
    "stylesheet_executed": False,
    "dom_accessed": False,
    "browser_visual_review_performed": False,
    "network_accessed": False,
    "runtime_assets_accessed": False,
    "runtime_consumer_bound": False,
    "profitability_proven": False,
}
_RECEIPT_CHECK_NAMES = (
    "node_contract_process_observed",
    "registration_v4_binding_exact",
    "projection_v5_seal_verified",
    "projection_schema_alias_rejected",
    "card_v5_view_model_built",
    "consumer_v5_descriptor_exact_rebuild",
    "local_joint_gate_state_preserved",
    "consumer_v5_remained_unmounted",
    "projection_and_descriptor_authority_locked",
    "stylesheet_declared_but_not_executed",
)
_RECEIPT_SOURCE_PINS = {
    "projection_implementation_sha256": PROJECTION_V5_IMPLEMENTATION_SHA256,
    "strict_canonical_implementation_sha256": (
        STRICT_CANONICAL_JAVASCRIPT_SHA256
    ),
    "card_schema_version": "portfolio-risk-joint-evidence-card-v5",
    "card_static_fingerprint": (
        "20260823-portfolio-risk-joint-evidence-card-v5-projection-lock-1"
    ),
    "card_implementation_sha256": CARD_V5_JAVASCRIPT_SHA256,
    "card_stylesheet_asset": (
        "evidence_portfolio_risk_joint_evidence_card_v5.css"
    ),
    "card_stylesheet_sha256": CARD_V5_STYLESHEET_SHA256,
    "consumer_schema_version": (
        "portfolio-risk-joint-evidence-presentation-consumer-fixture-v5"
    ),
    "consumer_static_fingerprint": (
        "20260823-portfolio-risk-joint-evidence-consumer-v5-unmounted-lock-1"
    ),
    "consumer_implementation_sha256": CONSUMER_V5_JAVASCRIPT_SHA256,
    "registration_schema_version": registration_v4.SCHEMA_VERSION,
    "registration_static_fingerprint": registration_v4.STATIC_FINGERPRINT,
    "registration_implementation_sha256": (
        REGISTRATION_V4_IMPLEMENTATION_SHA256
    ),
    "execution_environment": "NODE_CONTRACT_PROCESS",
}


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed_exact(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    try:
        expected = seal_strict_canonical_document(document, hash_field)
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _exact_dict(actual: Any, expected: dict[str, Any]) -> bool:
    return isinstance(actual, dict) and strict_json_contract_equal(
        actual,
        expected,
    )


def _receipt_source_pins_exact(source: Any) -> bool:
    return isinstance(source, dict) and all(
        source.get(key) == value
        for key, value in _RECEIPT_SOURCE_PINS.items()
    )


def _receipt_checks_exact(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    checks = receipt.get("checks")
    if not isinstance(checks, list) or len(checks) != len(
        _RECEIPT_CHECK_NAMES
    ):
        return False
    names = tuple(
        check.get("name") if isinstance(check, dict) else None
        for check in checks
    )
    return (
        names == _RECEIPT_CHECK_NAMES
        and all(
            isinstance(check, dict)
            and check.get("ok") is True
            and check.get("blocking") is True
            for check in checks
        )
        and receipt.get("blockers") == []
    )


def _local_gate_cross_bound(receipt: Any, projection: Any) -> bool:
    if not isinstance(receipt, dict) or not isinstance(projection, dict):
        return False
    local_decision = projection.get("local_decision")
    verification = receipt.get("verification")
    if not isinstance(local_decision, dict) or not isinstance(
        verification,
        dict,
    ):
        return False
    status = local_decision.get("status")
    if status not in {"PASS", "BLOCK"}:
        return False
    passed = status == "PASS"
    expected_label = "LOCAL GATE PASS" if passed else "LOCAL GATE BLOCK"
    return (
        local_decision.get("joint_risk_gate_passed") is passed
        and verification.get("local_joint_gate_status") == status
        and verification.get("local_joint_gate_passed") is passed
        and verification.get("local_joint_gate_state_preserved") is True
        and verification.get("view_status_label") == expected_label
    )


def _registration_verification(document: Any) -> dict[str, Any]:
    try:
        return registration_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            document,
            registration_v4.expected_presentation_consumer_implementation_sha256_v4(),
        )
    except (TypeError, ValueError):
        return {"status": "BLOCK"}


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
    receipt_v3_document: Any,
    projection_v5_document: Any,
    registration_v4_document: Any,
) -> dict[str, Any]:
    receipt_sealed = _sealed_exact(receipt_v3_document, "receipt_hash")
    receipt_schema_exact = bool(
        isinstance(receipt_v3_document, dict)
        and receipt_v3_document.get("schema_version")
        == RECEIPT_V3_SCHEMA_VERSION
        and receipt_v3_document.get("static_fingerprint")
        == RECEIPT_V3_STATIC_FINGERPRINT
    )
    receipt_status_pass = bool(
        isinstance(receipt_v3_document, dict)
        and receipt_v3_document.get("status") == "PASS"
        and receipt_v3_document.get("decision")
        == (
            "LOCAL_NODE_CONSUMER_V5_EXECUTED_EXACTLY_UNMOUNTED_"
            "AUTHORITY_UNCHANGED"
        )
        and receipt_v3_document.get("blockers") == []
    )
    receipt_source = (
        receipt_v3_document.get("source")
        if isinstance(receipt_v3_document, dict)
        else None
    )
    receipt_verification = (
        receipt_v3_document.get("verification")
        if isinstance(receipt_v3_document, dict)
        else None
    )
    receipt_pins_exact = _receipt_source_pins_exact(receipt_source)
    receipt_checks_exact = _receipt_checks_exact(receipt_v3_document)
    receipt_authority_locked = bool(
        isinstance(receipt_v3_document, dict)
        and _exact_dict(
            receipt_v3_document.get("authority"),
            _RECEIPT_AUTHORITY,
        )
    )
    receipt_facts_calibrated = bool(
        isinstance(receipt_v3_document, dict)
        and _exact_dict(receipt_v3_document.get("facts"), _RECEIPT_FACTS)
    )

    projection_sealed = _sealed_exact(
        projection_v5_document,
        "projection_hash",
    )
    projection_identity_exact = bool(
        isinstance(projection_v5_document, dict)
        and projection_v5_document.get("schema_version")
        == projection_v5.SCHEMA_VERSION
        and projection_v5_document.get("static_fingerprint")
        == projection_v5.STATIC_FINGERPRINT
        and projection_v5_document.get("status") == "BLOCK"
    )
    projection_authority_locked = bool(
        isinstance(projection_v5_document, dict)
        and _exact_dict(
            projection_v5_document.get("authority"),
            _PROJECTION_AUTHORITY,
        )
    )
    receipt_to_projection_bound = bool(
        isinstance(receipt_source, dict)
        and isinstance(projection_v5_document, dict)
        and receipt_source.get("projection_schema_version")
        == projection_v5_document.get("schema_version")
        and receipt_source.get("projection_static_fingerprint")
        == projection_v5_document.get("static_fingerprint")
        and receipt_source.get("projection_hash")
        == projection_v5_document.get("projection_hash")
        and _is_hash(receipt_source.get("projection_hash"))
    )

    registration_verification = _registration_verification(
        registration_v4_document
    )
    registration_exact = bool(
        isinstance(registration_v4_document, dict)
        and registration_verification.get("status") == "PASS"
        and registration_v4_document.get("schema_version")
        == registration_v4.SCHEMA_VERSION
        and registration_v4_document.get("static_fingerprint")
        == registration_v4.STATIC_FINGERPRINT
        and _is_hash(registration_v4_document.get("registration_hash"))
    )
    receipt_to_registration_bound = bool(
        isinstance(receipt_source, dict)
        and isinstance(registration_v4_document, dict)
        and receipt_source.get("registration_hash")
        == registration_v4_document.get("registration_hash")
        and _is_hash(receipt_source.get("registration_hash"))
    )
    local_gate_cross_bound = _local_gate_cross_bound(
        receipt_v3_document,
        projection_v5_document,
    )
    descriptor_hash_bound = bool(
        isinstance(receipt_verification, dict)
        and receipt_verification.get("descriptor_exactly_rebuilt") is True
        and _is_hash(receipt_verification.get("descriptor_sha256"))
        and receipt_verification.get("stage_order") == list(STAGE_ORDER)
    )

    checks = [
        {
            "name": "receipt_v3_strict_canonical_seal_exact",
            "ok": receipt_sealed,
            "blocking": True,
        },
        {
            "name": "receipt_v3_schema_and_fingerprint_exact",
            "ok": receipt_schema_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v3_status_pass_without_blockers",
            "ok": receipt_status_pass,
            "blocking": True,
        },
        {
            "name": "receipt_v3_dependency_pins_exact",
            "ok": receipt_pins_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v3_checks_all_true",
            "ok": receipt_checks_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v3_authority_locked",
            "ok": receipt_authority_locked,
            "blocking": True,
        },
        {
            "name": "receipt_v3_facts_calibrated",
            "ok": receipt_facts_calibrated,
            "blocking": True,
        },
        {
            "name": "projection_v5_strict_canonical_seal_exact",
            "ok": projection_sealed,
            "blocking": True,
        },
        {
            "name": "projection_v5_identity_exact",
            "ok": projection_identity_exact,
            "blocking": True,
        },
        {
            "name": "projection_v5_authority_locked",
            "ok": projection_authority_locked,
            "blocking": True,
        },
        {
            "name": "receipt_v3_to_projection_v5_hash_bound",
            "ok": receipt_to_projection_bound,
            "blocking": True,
        },
        {
            "name": "registration_v4_exactly_verified",
            "ok": registration_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v3_to_registration_v4_hash_bound",
            "ok": receipt_to_registration_bound,
            "blocking": True,
        },
        {
            "name": "local_joint_gate_state_cross_bound",
            "ok": local_gate_cross_bound,
            "blocking": True,
        },
        {
            "name": "descriptor_hash_and_stage_order_bound",
            "ok": descriptor_hash_bound,
            "blocking": True,
        },
    ]
    blockers = [
        check["name"] for check in checks if check.get("ok") is not True
    ]
    passed = not blockers

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCK",
        "decision": (
            "LOCAL_PYTHON_RECEIPT_V3_PROJECTION_V5_REGISTRATION_V4_"
            "CROSS_BINDING_VERIFIED_IDENTITY_UNVERIFIED"
            if passed
            else "LOCAL_PYTHON_RECEIPT_V3_CROSS_BINDING_BLOCKED"
        ),
        "source": {
            "receipt_v3_schema_version": (
                receipt_v3_document.get("schema_version")
                if receipt_schema_exact
                else "UNKNOWN"
            ),
            "receipt_v3_static_fingerprint": (
                receipt_v3_document.get("static_fingerprint")
                if receipt_schema_exact
                else "UNKNOWN"
            ),
            "receipt_v3_hash": (
                receipt_v3_document.get("receipt_hash")
                if receipt_sealed
                else None
            ),
            "receipt_v3_implementation_sha256": (
                RECEIPT_V3_IMPLEMENTATION_SHA256
            ),
            "projection_v5_schema_version": (
                projection_v5_document.get("schema_version")
                if projection_identity_exact
                else "UNKNOWN"
            ),
            "projection_v5_hash": (
                projection_v5_document.get("projection_hash")
                if projection_sealed
                else None
            ),
            "projection_v5_implementation_sha256": (
                PROJECTION_V5_IMPLEMENTATION_SHA256
            ),
            "registration_v4_schema_version": (
                registration_v4_document.get("schema_version")
                if registration_exact
                else "UNKNOWN"
            ),
            "registration_v4_hash": (
                registration_v4_document.get("registration_hash")
                if registration_exact
                else None
            ),
            "registration_v4_implementation_sha256": (
                REGISTRATION_V4_IMPLEMENTATION_SHA256
            ),
            "verification_environment": "PYTHON_CONTRACT_PROCESS",
        },
        "verification": {
            "receipt_v3_seal_exact": receipt_sealed,
            "receipt_v3_status": (
                receipt_v3_document.get("status")
                if isinstance(receipt_v3_document, dict)
                else "UNKNOWN"
            ),
            "receipt_v3_check_count": (
                len(receipt_v3_document.get("checks", []))
                if isinstance(receipt_v3_document, dict)
                and isinstance(receipt_v3_document.get("checks"), list)
                else 0
            ),
            "projection_v5_seal_exact": projection_sealed,
            "registration_v4_verification_status": (
                registration_verification.get("status", "BLOCK")
            ),
            "local_joint_gate_status": (
                receipt_verification.get("local_joint_gate_status", "UNKNOWN")
                if isinstance(receipt_verification, dict)
                else "UNKNOWN"
            ),
            "local_joint_gate_passed": (
                receipt_verification.get("local_joint_gate_passed")
                if isinstance(receipt_verification, dict)
                else None
            ),
            "descriptor_sha256": (
                receipt_verification.get("descriptor_sha256")
                if descriptor_hash_bound
                else None
            ),
            "stage_order": list(STAGE_ORDER),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "local_python_contract_execution_observed": True,
            "receipt_reports_local_node_execution": bool(
                isinstance(receipt_v3_document, dict)
                and isinstance(receipt_v3_document.get("facts"), dict)
                and receipt_v3_document["facts"].get(
                    "local_process_execution_observed"
                )
                is True
            ),
            "independent_node_process_witnessed": False,
            "node_process_identity_authenticated": False,
            "receipt_signature_verified": False,
            "external_execution_authority_verified": False,
            "receipt_implementation_runtime_verified": False,
            "projection_semantics_replayed": False,
            "receipt_document_embedded": False,
            "projection_document_embedded": False,
            "registration_document_embedded": False,
            "source_evidence_embedded": False,
            "consumer_descriptor_embedded": False,
            "markup_embedded": False,
            "stylesheet_executed": False,
            "dom_accessed": False,
            "browser_visual_review_performed": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
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
    return seal_strict_canonical_document(evidence, "evidence_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
    document: Any,
    receipt_v3_document: Any,
    projection_v5_document: Any,
    registration_v4_document: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
            receipt_v3_document,
            projection_v5_document,
            registration_v4_document,
        )
    )
    exact = _sealed_exact(document, "evidence_hash") and strict_json_contract_equal(
        document,
        expected,
    )
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "evidence_seal_verified": _sealed_exact(document, "evidence_hash"),
        "evidence_exactly_rebuilt": exact,
        "evidence_status": expected.get("status") if exact else "UNKNOWN",
        "evidence_hash": expected.get("evidence_hash") if exact else None,
        "blockers": (
            []
            if exact
            else ["consumer_execution_evidence_v3_exact_rebuild"]
        ),
        "independent_node_process_witnessed": False,
        "node_process_identity_authenticated": False,
        "receipt_signature_verified": False,
        "browser_visual_review_verified": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
