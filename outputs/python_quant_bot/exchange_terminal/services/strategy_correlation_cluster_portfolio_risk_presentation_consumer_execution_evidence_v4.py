from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v6
    as projection_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "execution-evidence-v4"
)
STATIC_FINGERPRINT = (
    "20260823-downside-tail-consumer-v6-receipt-v4-python-evidence-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
RECEIPT_V4_SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-consumer-execution-receipt-v4"
)
RECEIPT_V4_STATIC_FINGERPRINT = (
    "20260823-downside-tail-consumer-v6-node-execution-receipt-v4-lock-1"
)
RECEIPT_V4_VERIFICATION_SCHEMA_VERSION = (
    f"{RECEIPT_V4_SCHEMA_VERSION}-verification-v1"
)
RECEIPT_V4_IMPLEMENTATION_SHA256 = (
    "cfc312b5971953e0d2cfa35e691f7aba826266b66bb7a54e4dfeab5d0b3cae39"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-consumer-execution-preregistration-v1"
)
PREREGISTRATION_STATIC_FINGERPRINT = (
    "20260823-downside-tail-consumer-v6-local-node-preregistration-lock-1"
)
PROJECTION_V6_IMPLEMENTATION_SHA256 = (
    "ec136f1cc713f443581f835116610c0210d0fe2faeb638ee815d93709e1566d6"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
STRICT_CANONICAL_PYTHON_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
HTTP_CANDIDATE_V6_IMPLEMENTATION_SHA256 = (
    "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096"
)
CARD_V6_JAVASCRIPT_SHA256 = (
    "a75e6e033872cd1db418488c5ee57814e642c764887c633f74e8e592b08be22d"
)
CARD_V6_STYLESHEET_SHA256 = (
    "0f7870b549c0cdb671f92cb59b7776c33ac25ca101f2cf25c4420a7ad8268c83"
)
CONSUMER_V6_JAVASCRIPT_SHA256 = (
    "e98af5ea40f9e5cf56787cac0af14071b2acd1d2cdd3febc79db230c8c5f3ce7"
)
EXECUTION_PROFILE = "LOCAL_NODE_CONTRACT_PROCESS_UNMOUNTED"
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_RECEIPT_DECISION = (
    "LOCAL_NODE_DOWNSIDE_TAIL_CONSUMER_V6_EXECUTED_EXACTLY_UNMOUNTED_"
    "AUTHORITY_UNCHANGED"
)
_PROJECTION_DECISION = (
    "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED"
)
_DESCRIPTOR_DECISION = (
    "KNOWN_BLOCKED_PROJECTION_V6_RENDER_DESCRIPTOR_ONLY"
)
_HTTP_CANDIDATE_V6_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-"
    "candidate-response-v6"
)
_HTTP_CANDIDATE_V6_STATIC_FINGERPRINT = (
    "20260823-adapter-v6-envelope-first-http-unregistered-candidate-1"
)

_PREREGISTRATION_AUTHORITY = {
    "descriptive_only": True,
    "current_admission_allowed": False,
    "formal_registration_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "presentation_consumer_activation_allowed": False,
    "presentation_mount_allowed": False,
    "runtime_gate_activation_allowed": False,
    "writer_allowed": False,
}
_RECEIPT_AUTHORITY = {
    "descriptive_only": True,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registration_activation_allowed": False,
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
    "frontend_projection_only": True,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registry_activation_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "presentation_consumer_activation_allowed": False,
    "presentation_mount_allowed": False,
    "runtime_gate_activation_allowed": False,
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
    "execution_preregistration_bound": True,
    "formal_registration_bound": False,
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
    "execution_preregistration_v1_exact",
    "projection_v6_seal_verified",
    "projection_v5_schema_alias_rejected",
    "card_v6_view_model_built",
    "consumer_v6_descriptor_exact_rebuild",
    "source_tail_and_local_state_preserved",
    "consumer_v6_remained_unmounted",
    "projection_and_descriptor_authority_locked",
    "stylesheet_declared_but_not_executed",
    "formal_registration_not_claimed",
)
_SEMANTIC_PRESENTATION = {
    ("PASS", "PASS", "OBSERVED"): {
        "execution_semantic_state": "CLEAR",
        "view_status_label": "LOCAL CHECKS CLEAR",
        "view_tone": "bounded",
    },
    ("BLOCK", "BLOCK", "OBSERVED"): {
        "execution_semantic_state": "TAIL_BLOCK",
        "view_status_label": "TAIL COUPLING BLOCK",
        "view_tone": "critical",
    },
    ("UNKNOWN", "UNKNOWN", "UNKNOWN"): {
        "execution_semantic_state": "EXACT_UNKNOWN",
        "view_status_label": "SOURCE UNKNOWN",
        "view_tone": "unknown",
    },
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


def _valid_preregistration_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= 256


def _expected_preregistration(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    preregistration_id = document.get("preregistration_id")
    if not _valid_preregistration_id(preregistration_id):
        return None
    expected = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": PREREGISTRATION_STATIC_FINGERPRINT,
        "preregistration_id": preregistration_id,
        "projection_implementation_sha256": (
            PROJECTION_V6_IMPLEMENTATION_SHA256
        ),
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_JAVASCRIPT_SHA256
        ),
        "card_implementation_sha256": CARD_V6_JAVASCRIPT_SHA256,
        "card_stylesheet_sha256": CARD_V6_STYLESHEET_SHA256,
        "consumer_implementation_sha256": CONSUMER_V6_JAVASCRIPT_SHA256,
        "execution_profile": EXECUTION_PROFILE,
        "authority": _PREREGISTRATION_AUTHORITY,
    }
    return seal_strict_canonical_document(expected, "preregistration_hash")


def _preregistration_exact(document: Any) -> bool:
    expected = _expected_preregistration(document)
    return bool(
        expected is not None
        and _sealed_exact(document, "preregistration_hash")
        and strict_json_contract_equal(document, expected)
    )


def _receipt_checks_exact(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    checks = receipt.get("checks")
    expected = [
        {"name": name, "ok": True, "blocking": True}
        for name in _RECEIPT_CHECK_NAMES
    ]
    return strict_json_contract_equal(checks, expected)


def _projection_identity_exact(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    stages = document.get("stages")
    stage_axes = (
        tuple(
            stage.get("axis") if isinstance(stage, dict) else None
            for stage in stages
        )
        if isinstance(stages, list)
        else ()
    )
    return (
        document.get("schema_version") == projection_v6.SCHEMA_VERSION
        and document.get("static_fingerprint")
        == projection_v6.STATIC_FINGERPRINT
        and document.get("status") == "BLOCK"
        and document.get("decision") == _PROJECTION_DECISION
        and document.get("axis_order") == list(STAGE_ORDER)
        and stage_axes == STAGE_ORDER
    )


def _projection_source_lineage_exact(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    source = document.get("source")
    if not isinstance(source, dict):
        return False
    expected_keys = {
        "adapter_v6_hash",
        "candidate_state",
        "candidate_v6_implementation_sha256",
        "candidate_v6_response_hash",
        "candidate_v6_schema_version",
        "candidate_v6_static_fingerprint",
        "presentation_envelope_v1_hash",
        "state",
        "strict_canonical_implementation_sha256",
    }
    return (
        set(source) == expected_keys
        and _is_hash(source.get("adapter_v6_hash"))
        and source.get("candidate_state") == "KNOWN_BLOCKED"
        and source.get("candidate_v6_implementation_sha256")
        == HTTP_CANDIDATE_V6_IMPLEMENTATION_SHA256
        and _is_hash(source.get("candidate_v6_response_hash"))
        and source.get("candidate_v6_schema_version")
        == _HTTP_CANDIDATE_V6_SCHEMA_VERSION
        and source.get("candidate_v6_static_fingerprint")
        == _HTTP_CANDIDATE_V6_STATIC_FINGERPRINT
        and _is_hash(source.get("presentation_envelope_v1_hash"))
        and source.get("state") in {"OBSERVED", "UNKNOWN"}
        and source.get("strict_canonical_implementation_sha256")
        == STRICT_CANONICAL_PYTHON_SHA256
    )


def _semantic_contract(
    receipt: Any,
    projection: Any,
) -> dict[str, Any] | None:
    if not isinstance(receipt, dict) or not isinstance(projection, dict):
        return None
    receipt_verification = receipt.get("verification")
    local_decision = projection.get("local_decision")
    projection_source = projection.get("source")
    if not all(
        isinstance(value, dict)
        for value in (
            receipt_verification,
            local_decision,
            projection_source,
        )
    ):
        return None
    local_status = local_decision.get("status")
    tail_decision = local_decision.get("downside_tail_gate_decision")
    source_state = local_decision.get("downside_tail_source_state")
    presentation = _SEMANTIC_PRESENTATION.get(
        (local_status, tail_decision, source_state)
    )
    if (
        presentation is None
        or projection_source.get("state") != source_state
        or not _is_hash(receipt_verification.get("descriptor_hash"))
    ):
        return None
    expected_receipt_verification = {
        "node_process_observed": True,
        "execution_preregistration_exact": True,
        "projection_seal_verified": True,
        "projection_schema_alias_rejected": True,
        "descriptor_exactly_rebuilt": True,
        "source_tail_and_local_state_preserved": True,
        "formal_registration_bound": False,
        "descriptor_status": "BLOCK",
        "descriptor_decision": _DESCRIPTOR_DECISION,
        "descriptor_hash": receipt_verification["descriptor_hash"],
        "local_status": local_status,
        "downside_tail_gate_decision": tail_decision,
        "view_contract_state": "KNOWN_BLOCKED",
        "view_source_state": source_state,
        "view_status_label": presentation["view_status_label"],
        "view_tone": presentation["view_tone"],
        "stage_order": list(STAGE_ORDER),
    }
    if not _exact_dict(receipt_verification, expected_receipt_verification):
        return None
    return {
        "execution_semantic_state": presentation[
            "execution_semantic_state"
        ],
        "local_status": local_status,
        "downside_tail_gate_decision": tail_decision,
        "source_state": source_state,
        "descriptor_hash": receipt_verification["descriptor_hash"],
    }


def _expected_receipt_source(
    projection: Any,
    preregistration: Any,
) -> dict[str, Any] | None:
    if not isinstance(projection, dict) or not isinstance(
        preregistration,
        dict,
    ):
        return None
    projection_hash = projection.get("projection_hash")
    preregistration_hash = preregistration.get("preregistration_hash")
    if not _is_hash(projection_hash) or not _is_hash(preregistration_hash):
        return None
    return {
        "projection_schema_version": projection_v6.SCHEMA_VERSION,
        "projection_static_fingerprint": projection_v6.STATIC_FINGERPRINT,
        "projection_hash": projection_hash,
        "projection_implementation_sha256": (
            PROJECTION_V6_IMPLEMENTATION_SHA256
        ),
        "strict_canonical_implementation_sha256": (
            STRICT_CANONICAL_JAVASCRIPT_SHA256
        ),
        "card_schema_version": "portfolio-risk-downside-tail-card-v6",
        "card_static_fingerprint": (
            "20260823-portfolio-risk-downside-tail-card-v6-unmounted-lock-1"
        ),
        "card_implementation_sha256": CARD_V6_JAVASCRIPT_SHA256,
        "card_stylesheet_asset": (
            "evidence_portfolio_risk_downside_tail_card_v6.css"
        ),
        "card_stylesheet_sha256": CARD_V6_STYLESHEET_SHA256,
        "consumer_schema_version": (
            "portfolio-risk-downside-tail-presentation-consumer-fixture-v6"
        ),
        "consumer_static_fingerprint": (
            "20260823-portfolio-risk-downside-tail-consumer-v6-unmounted-"
            "lock-1"
        ),
        "consumer_implementation_sha256": CONSUMER_V6_JAVASCRIPT_SHA256,
        "execution_preregistration_schema_version": (
            PREREGISTRATION_SCHEMA_VERSION
        ),
        "execution_preregistration_static_fingerprint": (
            PREREGISTRATION_STATIC_FINGERPRINT
        ),
        "execution_preregistration_hash": preregistration_hash,
        "formal_registration_schema_version": None,
        "formal_registration_hash": None,
        "execution_environment": "NODE_CONTRACT_PROCESS",
    }


def _expected_receipt_verification(
    receipt: Any,
) -> dict[str, Any] | None:
    if not isinstance(receipt, dict) or not _is_hash(
        receipt.get("receipt_hash")
    ):
        return None
    expected = {
        "schema_version": RECEIPT_V4_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS",
        "receipt_seal_verified": True,
        "receipt_exactly_rebuilt": True,
        "receipt_status": "PASS",
        "receipt_hash": receipt["receipt_hash"],
        "blockers": [],
        "browser_visual_review_verified": False,
        "current_admission_allowed": False,
        "formal_registration_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
    return seal_strict_canonical_document(expected, "verification_hash")


def _formal_registration_absent(
    receipt: Any,
    receipt_verification: Any,
    preregistration: Any,
) -> bool:
    if not all(
        isinstance(value, dict)
        for value in (receipt, receipt_verification, preregistration)
    ):
        return False
    source = receipt.get("source")
    facts = receipt.get("facts")
    internal_verification = receipt.get("verification")
    receipt_authority = receipt.get("authority")
    preregistration_authority = preregistration.get("authority")
    return bool(
        isinstance(source, dict)
        and source.get("formal_registration_schema_version") is None
        and source.get("formal_registration_hash") is None
        and isinstance(facts, dict)
        and facts.get("formal_registration_bound") is False
        and isinstance(internal_verification, dict)
        and internal_verification.get("formal_registration_bound") is False
        and isinstance(receipt_authority, dict)
        and receipt_authority.get("formal_registration_activation_allowed")
        is False
        and isinstance(preregistration_authority, dict)
        and preregistration_authority.get("formal_registration_allowed")
        is False
        and receipt_verification.get("formal_registration_verified") is False
    )


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    preregistration_sealed = _sealed_exact(
        execution_preregistration_v1_document,
        "preregistration_hash",
    )
    preregistration_schema_exact = bool(
        isinstance(execution_preregistration_v1_document, dict)
        and execution_preregistration_v1_document.get("schema_version")
        == PREREGISTRATION_SCHEMA_VERSION
        and execution_preregistration_v1_document.get("static_fingerprint")
        == PREREGISTRATION_STATIC_FINGERPRINT
        and execution_preregistration_v1_document.get("execution_profile")
        == EXECUTION_PROFILE
    )
    preregistration_authority_locked = bool(
        isinstance(execution_preregistration_v1_document, dict)
        and _exact_dict(
            execution_preregistration_v1_document.get("authority"),
            _PREREGISTRATION_AUTHORITY,
        )
    )
    preregistration_exact = _preregistration_exact(
        execution_preregistration_v1_document
    )

    receipt_sealed = _sealed_exact(receipt_v4_document, "receipt_hash")
    receipt_schema_exact = bool(
        isinstance(receipt_v4_document, dict)
        and receipt_v4_document.get("schema_version")
        == RECEIPT_V4_SCHEMA_VERSION
        and receipt_v4_document.get("static_fingerprint")
        == RECEIPT_V4_STATIC_FINGERPRINT
    )
    receipt_status_pass = bool(
        isinstance(receipt_v4_document, dict)
        and receipt_v4_document.get("status") == "PASS"
        and receipt_v4_document.get("decision") == _RECEIPT_DECISION
        and receipt_v4_document.get("blockers") == []
    )
    receipt_source = (
        receipt_v4_document.get("source")
        if isinstance(receipt_v4_document, dict)
        else None
    )
    expected_receipt_source = _expected_receipt_source(
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    receipt_source_exact = bool(
        expected_receipt_source is not None
        and _exact_dict(receipt_source, expected_receipt_source)
    )
    receipt_to_projection_bound = bool(
        isinstance(receipt_source, dict)
        and isinstance(projection_v6_document, dict)
        and _is_hash(projection_v6_document.get("projection_hash"))
        and receipt_source.get("projection_hash")
        == projection_v6_document.get("projection_hash")
    )
    receipt_to_preregistration_bound = bool(
        isinstance(receipt_source, dict)
        and isinstance(execution_preregistration_v1_document, dict)
        and _is_hash(
            execution_preregistration_v1_document.get(
                "preregistration_hash"
            )
        )
        and receipt_source.get("execution_preregistration_hash")
        == execution_preregistration_v1_document.get(
            "preregistration_hash"
        )
    )
    receipt_checks_exact = _receipt_checks_exact(receipt_v4_document)
    receipt_authority_locked = bool(
        isinstance(receipt_v4_document, dict)
        and _exact_dict(
            receipt_v4_document.get("authority"),
            _RECEIPT_AUTHORITY,
        )
    )
    receipt_facts_calibrated = bool(
        isinstance(receipt_v4_document, dict)
        and _exact_dict(receipt_v4_document.get("facts"), _RECEIPT_FACTS)
    )

    projection_sealed = _sealed_exact(
        projection_v6_document,
        "projection_hash",
    )
    projection_identity_exact = _projection_identity_exact(
        projection_v6_document
    )
    projection_source_lineage_exact = _projection_source_lineage_exact(
        projection_v6_document
    )
    projection_authority_locked = bool(
        isinstance(projection_v6_document, dict)
        and _exact_dict(
            projection_v6_document.get("authority"),
            _PROJECTION_AUTHORITY,
        )
    )
    semantic_contract = _semantic_contract(
        receipt_v4_document,
        projection_v6_document,
    )
    semantic_cross_bound = semantic_contract is not None

    receipt_verification_sealed = _sealed_exact(
        receipt_v4_verification_document,
        "verification_hash",
    )
    expected_receipt_verification = _expected_receipt_verification(
        receipt_v4_document
    )
    receipt_verification_exact = bool(
        expected_receipt_verification is not None
        and receipt_verification_sealed
        and strict_json_contract_equal(
            receipt_v4_verification_document,
            expected_receipt_verification,
        )
    )
    formal_registration_absent = _formal_registration_absent(
        receipt_v4_document,
        receipt_v4_verification_document,
        execution_preregistration_v1_document,
    )

    checks = [
        {
            "name": "execution_preregistration_v1_strict_canonical_seal_exact",
            "ok": preregistration_sealed,
            "blocking": True,
        },
        {
            "name": "execution_preregistration_v1_schema_profile_exact",
            "ok": preregistration_schema_exact,
            "blocking": True,
        },
        {
            "name": "execution_preregistration_v1_authority_locked",
            "ok": preregistration_authority_locked,
            "blocking": True,
        },
        {
            "name": "execution_preregistration_v1_exactly_rebuilt",
            "ok": preregistration_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v4_strict_canonical_seal_exact",
            "ok": receipt_sealed,
            "blocking": True,
        },
        {
            "name": "receipt_v4_schema_and_fingerprint_exact",
            "ok": receipt_schema_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v4_execution_status_pass_without_blockers",
            "ok": receipt_status_pass,
            "blocking": True,
        },
        {
            "name": "receipt_v4_dependency_source_exact",
            "ok": receipt_source_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v4_to_projection_v6_hash_bound",
            "ok": receipt_to_projection_bound,
            "blocking": True,
        },
        {
            "name": "receipt_v4_to_preregistration_v1_hash_bound",
            "ok": receipt_to_preregistration_bound,
            "blocking": True,
        },
        {
            "name": "receipt_v4_checks_all_true",
            "ok": receipt_checks_exact,
            "blocking": True,
        },
        {
            "name": "receipt_v4_authority_locked",
            "ok": receipt_authority_locked,
            "blocking": True,
        },
        {
            "name": "receipt_v4_facts_calibrated",
            "ok": receipt_facts_calibrated,
            "blocking": True,
        },
        {
            "name": "projection_v6_strict_canonical_seal_exact",
            "ok": projection_sealed,
            "blocking": True,
        },
        {
            "name": "projection_v6_identity_and_stage_order_exact",
            "ok": projection_identity_exact,
            "blocking": True,
        },
        {
            "name": "projection_v6_source_lineage_shape_exact",
            "ok": projection_source_lineage_exact,
            "blocking": True,
        },
        {
            "name": "projection_v6_authority_locked",
            "ok": projection_authority_locked,
            "blocking": True,
        },
        {
            "name": "clear_tail_block_or_exact_unknown_state_cross_bound",
            "ok": semantic_cross_bound,
            "blocking": True,
        },
        {
            "name": "receipt_v4_verification_hash_and_receipt_edge_exact",
            "ok": receipt_verification_exact,
            "blocking": True,
        },
        {
            "name": "formal_registration_remains_explicitly_absent",
            "ok": formal_registration_absent,
            "blocking": True,
        },
    ]
    blockers = [
        check["name"] for check in checks if check.get("ok") is not True
    ]
    passed = not blockers
    verified_semantic = semantic_contract or {
        "execution_semantic_state": "UNVERIFIED",
        "local_status": "UNKNOWN",
        "downside_tail_gate_decision": "UNKNOWN",
        "source_state": "UNKNOWN",
        "descriptor_hash": None,
    }

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCK",
        "decision": (
            "LOCAL_PYTHON_RECEIPT_V4_PREREGISTRATION_V1_PROJECTION_V6_"
            "CROSS_BINDING_VERIFIED_IDENTITY_UNVERIFIED"
            if passed
            else "LOCAL_PYTHON_RECEIPT_V4_EXECUTION_EVIDENCE_BLOCKED"
        ),
        "source": {
            "receipt_v4_schema_version": (
                receipt_v4_document.get("schema_version")
                if receipt_schema_exact
                else "UNKNOWN"
            ),
            "receipt_v4_static_fingerprint": (
                receipt_v4_document.get("static_fingerprint")
                if receipt_schema_exact
                else "UNKNOWN"
            ),
            "receipt_v4_hash": (
                receipt_v4_document.get("receipt_hash")
                if receipt_sealed
                else None
            ),
            "receipt_v4_implementation_sha256": (
                RECEIPT_V4_IMPLEMENTATION_SHA256
            ),
            "receipt_v4_verification_schema_version": (
                receipt_v4_verification_document.get("schema_version")
                if receipt_verification_exact
                else "UNKNOWN"
            ),
            "receipt_v4_verification_hash": (
                receipt_v4_verification_document.get("verification_hash")
                if receipt_verification_exact
                else None
            ),
            "projection_v6_schema_version": (
                projection_v6_document.get("schema_version")
                if projection_identity_exact
                else "UNKNOWN"
            ),
            "projection_v6_hash": (
                projection_v6_document.get("projection_hash")
                if projection_sealed
                else None
            ),
            "projection_v6_implementation_sha256": (
                PROJECTION_V6_IMPLEMENTATION_SHA256
            ),
            "execution_preregistration_v1_schema_version": (
                execution_preregistration_v1_document.get("schema_version")
                if preregistration_schema_exact
                else "UNKNOWN"
            ),
            "execution_preregistration_v1_hash": (
                execution_preregistration_v1_document.get(
                    "preregistration_hash"
                )
                if preregistration_sealed
                else None
            ),
            "execution_preregistration_id": (
                execution_preregistration_v1_document.get(
                    "preregistration_id"
                )
                if preregistration_exact
                else "UNKNOWN"
            ),
            "formal_registration_schema_version": None,
            "formal_registration_hash": None,
            "verification_environment": "PYTHON_CONTRACT_PROCESS",
        },
        "verification": {
            "receipt_v4_seal_exact": receipt_sealed,
            "receipt_v4_status": (
                receipt_v4_document.get("status")
                if isinstance(receipt_v4_document, dict)
                else "UNKNOWN"
            ),
            "receipt_v4_verification_exact": receipt_verification_exact,
            "execution_preregistration_v1_exact": preregistration_exact,
            "projection_v6_seal_exact": projection_sealed,
            "projection_v6_source_lineage_shape_exact": (
                projection_source_lineage_exact
            ),
            "execution_semantic_state": verified_semantic[
                "execution_semantic_state"
            ],
            "local_status": verified_semantic["local_status"],
            "downside_tail_gate_decision": verified_semantic[
                "downside_tail_gate_decision"
            ],
            "source_state": verified_semantic["source_state"],
            "descriptor_hash": verified_semantic["descriptor_hash"],
            "formal_registration_bound": False,
            "stage_order": list(STAGE_ORDER),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "local_python_contract_execution_observed": True,
            "receipt_reports_local_node_execution": bool(
                isinstance(receipt_v4_document, dict)
                and isinstance(receipt_v4_document.get("facts"), dict)
                and receipt_v4_document["facts"].get(
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
            "projection_lineage_documents_replayed": False,
            "receipt_document_embedded": False,
            "receipt_verification_document_embedded": False,
            "projection_document_embedded": False,
            "execution_preregistration_document_embedded": False,
            "source_evidence_embedded": False,
            "consumer_descriptor_embedded": False,
            "markup_embedded": False,
            "formal_registration_bound": False,
            "stylesheet_executed": False,
            "dom_accessed": False,
            "browser_visual_review_performed": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": _RECEIPT_AUTHORITY,
    }
    return seal_strict_canonical_document(evidence, "evidence_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
    document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    sealed = _sealed_exact(document, "evidence_hash")
    exact = sealed and strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "evidence_seal_verified": sealed,
        "evidence_exactly_rebuilt": exact,
        "evidence_status": expected.get("status") if exact else "UNKNOWN",
        "execution_semantic_state": (
            expected.get("verification", {}).get(
                "execution_semantic_state",
                "UNVERIFIED",
            )
            if exact
            else "UNVERIFIED"
        ),
        "evidence_hash": expected.get("evidence_hash") if exact else None,
        "blockers": (
            []
            if exact
            else ["consumer_execution_evidence_v4_exact_rebuild"]
        ),
        "independent_node_process_witnessed": False,
        "node_process_identity_authenticated": False,
        "receipt_signature_verified": False,
        "formal_registration_verified": False,
        "browser_visual_review_verified": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
