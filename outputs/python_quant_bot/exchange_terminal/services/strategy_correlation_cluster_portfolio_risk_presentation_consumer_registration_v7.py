from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6
    as registration_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v7"
)
STATIC_FINGERPRINT = (
    "20260823-downside-tail-evidence-v4-registration-v7-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "REGISTRATION_V6_AND_DOWNSIDE_TAIL_EXECUTION_EVIDENCE_V4_PINNED_"
    "POST_REGISTRATION_RECEIPT_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)
REGISTRATION_V6_IMPLEMENTATION_SHA256 = (
    "061bae89a89ca090ab3565ff706e5144902f6a1083df970fad172245538d8e60"
)
EVIDENCE_V4_IMPLEMENTATION_SHA256 = (
    "c1e9bb3f122dd94cb6fd45a9eb1f1c40ecefc539a2af9d12be5f680c5a3819b5"
)

_EXPECTED_DELTA_MANIFEST = {
    "presentation_registration_v6": (
        REGISTRATION_V6_IMPLEMENTATION_SHA256
    ),
    "portfolio_risk_adapter_v6": (
        "cedfcc01bb11a5179db093acf806fcb2a49c92fb291182f0a8e34b1a66e464a2"
    ),
    "portfolio_risk_adapter_v6_test": (
        "854b37bb0874aaa7f0373d5f5dd29263e7110957dd293386a0b2a8678796525e"
    ),
    "portfolio_risk_presentation_envelope_v1": (
        "ec8977a0b3750b17a5ac35c20c6fe1791573a0529e0d8e61a81a07010ebf02dd"
    ),
    "portfolio_risk_presentation_envelope_v1_test": (
        "f592e2aa653708b1d94ada4dfae2ff180a81e4916fa246c614e85d6ff2160e7d"
    ),
    "portfolio_risk_http_candidate_v6": (
        "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096"
    ),
    "portfolio_risk_http_candidate_v6_test": (
        "0d246d7bbe1e24756cd176496cd2fd10794e248ccb6372d0b83f9a73096fcffc"
    ),
    "portfolio_risk_projection_v6": (
        "ec136f1cc713f443581f835116610c0210d0fe2faeb638ee815d93709e1566d6"
    ),
    "portfolio_risk_projection_v6_test": (
        "c4fce8c9e95d53c407a5263b0c979d6d8ebc71d84ce7b1b3bb04cab9e5f063b6"
    ),
    "downside_tail_card_v6_js": (
        "a75e6e033872cd1db418488c5ee57814e642c764887c633f74e8e592b08be22d"
    ),
    "downside_tail_card_v6_css": (
        "0f7870b549c0cdb671f92cb59b7776c33ac25ca101f2cf25c4420a7ad8268c83"
    ),
    "downside_tail_consumer_v6_js": (
        "e98af5ea40f9e5cf56787cac0af14071b2acd1d2cdd3febc79db230c8c5f3ce7"
    ),
    "downside_tail_consumer_v6_node_test_js": (
        "4925e10ec2659137cc8346e6816a7e3e4ef9e6910e4409616674172e0f6bb7e4"
    ),
    "downside_tail_consumer_v6_cross_runtime_test_py": (
        "6c74b8b5119a918ac1ab10dae1eb1c751e17633d8f317d626ce0272a836eac02"
    ),
    "downside_tail_execution_receipt_v4_js": (
        "cfc312b5971953e0d2cfa35e691f7aba826266b66bb7a54e4dfeab5d0b3cae39"
    ),
    "downside_tail_execution_receipt_v4_node_test_js": (
        "4276370f86236440fa04fff316cf177f93e893ef1c2b102ad13d6e7b2beead78"
    ),
    "downside_tail_execution_receipt_v4_cross_runtime_test_py": (
        "ecf1dd8662b24d5245e1c355627a5c6d1bd8f62d0193f01bdd5080548b9e659e"
    ),
    "downside_tail_execution_evidence_v4_py": (
        EVIDENCE_V4_IMPLEMENTATION_SHA256
    ),
    "downside_tail_execution_evidence_v4_test_py": (
        "fc16d6011326bb83a46147b1d8af64ddc5d113bdeb25d1c3cb6da2b2553b435a"
    ),
    "adapter_v6_downside_tail_joint_risk_gate_adr": (
        "5714bc8c7a50ebbf629697c1dd008ae9641719f4eca76672f0d1136cd7e9f6d1"
    ),
    "adapter_v6_neutral_presentation_envelope_v1_adr": (
        "0250e16b69dd6bfd51b45e270c012696ee9a4605b98a8b93b874751f07c8637e"
    ),
    "envelope_first_http_candidate_v6_adr": (
        "7a6bd8d0ce4ffadd2a76f09f92220181eb9f172033cdef56f8dbef1ee9eaa93a"
    ),
    "candidate_v6_frontend_projection_v6_adr": (
        "d26ba5b1016f199ce9dc13a7d5c95f27ffc8ba981b41cad79e22e5ceb6e265a4"
    ),
    "projection_v6_node_consumer_cross_runtime_adr": (
        "5ef06bb5b497febbb498e7f70a137f58cf820198b1ae17313ca79a9f73460a8f"
    ),
    "downside_tail_node_execution_receipt_v4_adr": (
        "9a41f3b79f80f915328c5708febc18c628d1d12bec6c1b1570c713b45757bb24"
    ),
    "downside_tail_python_execution_evidence_v4_adr": (
        "a170ddd9ca4bffbab4b87a7385a648717fce32a36523954d2873fc418b8cab71"
    ),
}
_ARTIFACT_ROLES = {
    "presentation_registration_v6": "predecessor",
    "portfolio_risk_adapter_v6": "production",
    "portfolio_risk_adapter_v6_test": "verification",
    "portfolio_risk_presentation_envelope_v1": "production",
    "portfolio_risk_presentation_envelope_v1_test": "verification",
    "portfolio_risk_http_candidate_v6": "production",
    "portfolio_risk_http_candidate_v6_test": "verification",
    "portfolio_risk_projection_v6": "production",
    "portfolio_risk_projection_v6_test": "verification",
    "downside_tail_card_v6_js": "production",
    "downside_tail_card_v6_css": "production",
    "downside_tail_consumer_v6_js": "production",
    "downside_tail_consumer_v6_node_test_js": "verification",
    "downside_tail_consumer_v6_cross_runtime_test_py": "verification",
    "downside_tail_execution_receipt_v4_js": "production",
    "downside_tail_execution_receipt_v4_node_test_js": "verification",
    "downside_tail_execution_receipt_v4_cross_runtime_test_py": (
        "verification"
    ),
    "downside_tail_execution_evidence_v4_py": "production",
    "downside_tail_execution_evidence_v4_test_py": "verification",
    "adapter_v6_downside_tail_joint_risk_gate_adr": "decision",
    "adapter_v6_neutral_presentation_envelope_v1_adr": "decision",
    "envelope_first_http_candidate_v6_adr": "decision",
    "candidate_v6_frontend_projection_v6_adr": "decision",
    "projection_v6_node_consumer_cross_runtime_adr": "decision",
    "downside_tail_node_execution_receipt_v4_adr": "decision",
    "downside_tail_python_execution_evidence_v4_adr": "decision",
}
_AUTHORITY = {
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
_ALLOWED_SEMANTIC_STATES = {"CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"}


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


def _manifest_exact(value: Any) -> bool:
    return isinstance(value, dict) and strict_json_contract_equal(
        value,
        _EXPECTED_DELTA_MANIFEST,
    )


def _predecessor_registration() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = (
        registration_v6.expected_presentation_consumer_implementation_sha256_v6()
    )
    document = registration_v6.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
        manifest
    )
    verification = registration_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
        document,
        manifest,
    )
    return document, verification


def _artifact_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact": name,
            "role": _ARTIFACT_ROLES[name],
            "sha256": _EXPECTED_DELTA_MANIFEST[name],
        }
        for name in sorted(_EXPECTED_DELTA_MANIFEST)
    ]


def expected_presentation_consumer_implementation_sha256_v7() -> dict[str, str]:
    return dict(_EXPECTED_DELTA_MANIFEST)


def _verify_evidence(
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    try:
        return evidence_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
            projection_v6_document,
            execution_preregistration_v1_document,
        )
    except (TypeError, ValueError):
        return {"status": "BLOCK", "execution_semantic_state": "UNVERIFIED"}


def _pre_registration_formal_absence_exact(
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
) -> bool:
    if not all(
        isinstance(value, dict)
        for value in (
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
        )
    ):
        return False
    evidence_source = execution_evidence_v4_document.get("source")
    evidence_facts = execution_evidence_v4_document.get("facts")
    evidence_verification = execution_evidence_v4_document.get("verification")
    receipt_source = receipt_v4_document.get("source")
    receipt_facts = receipt_v4_document.get("facts")
    receipt_verification = receipt_v4_document.get("verification")
    return bool(
        isinstance(evidence_source, dict)
        and evidence_source.get("formal_registration_schema_version") is None
        and evidence_source.get("formal_registration_hash") is None
        and isinstance(evidence_facts, dict)
        and evidence_facts.get("formal_registration_bound") is False
        and isinstance(evidence_verification, dict)
        and evidence_verification.get("formal_registration_bound") is False
        and isinstance(receipt_source, dict)
        and receipt_source.get("formal_registration_schema_version") is None
        and receipt_source.get("formal_registration_hash") is None
        and isinstance(receipt_facts, dict)
        and receipt_facts.get("formal_registration_bound") is False
        and isinstance(receipt_verification, dict)
        and receipt_verification.get("formal_registration_bound") is False
        and receipt_v4_verification_document.get(
            "formal_registration_verified"
        )
        is False
    )


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    manifest_exact = _manifest_exact(current_implementation_sha256)
    predecessor, predecessor_verification = _predecessor_registration()
    predecessor_exact = bool(
        predecessor_verification.get("status") == "PASS"
        and predecessor.get("schema_version") == registration_v6.SCHEMA_VERSION
        and predecessor.get("static_fingerprint")
        == registration_v6.STATIC_FINGERPRINT
        and predecessor.get("status") == "BLOCKED"
        and _is_hash(predecessor.get("registration_hash"))
    )
    evidence_verification = _verify_evidence(
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    semantic_state = evidence_verification.get(
        "execution_semantic_state",
        "UNVERIFIED",
    )
    evidence_exact = bool(
        isinstance(execution_evidence_v4_document, dict)
        and evidence_verification.get("status") == "PASS"
        and execution_evidence_v4_document.get("schema_version")
        == evidence_v4.SCHEMA_VERSION
        and execution_evidence_v4_document.get("static_fingerprint")
        == evidence_v4.STATIC_FINGERPRINT
        and execution_evidence_v4_document.get("status") == "PASS"
        and _is_hash(execution_evidence_v4_document.get("evidence_hash"))
        and semantic_state in _ALLOWED_SEMANTIC_STATES
    )
    pre_registration_formal_absence_exact = (
        _pre_registration_formal_absence_exact(
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
        )
    )
    local_contract_complete = bool(
        manifest_exact
        and predecessor_exact
        and evidence_exact
        and pre_registration_formal_absence_exact
    )

    blockers = [
        "POST_REGISTRATION_EXECUTION_RECEIPT_NOT_ISSUED",
        "EXTERNAL_WITNESS_POLICY_REGISTRY_AND_IDENTITY_UNBOUND",
        "INDEPENDENT_EXECUTION_PROCESS_WITNESS_AND_ANTI_REPLAY_UNVERIFIED",
        "BROWSER_VISUAL_REVIEW_UNPERFORMED",
        "PRODUCTION_ROUTE_MOUNT_AND_ACTIVATION_UNAUTHORIZED",
        "CURRENT_ADMISSION_LOCKED",
    ]
    if not manifest_exact:
        blockers.insert(0, "IMPLEMENTATION_DELTA_MANIFEST_MISMATCH")
    if not predecessor_exact:
        blockers.insert(0, "PREDECESSOR_REGISTRATION_V6_NOT_EXACT")
    if not evidence_exact:
        blockers.insert(0, "EXECUTION_EVIDENCE_V4_NOT_EXACT")
    if not pre_registration_formal_absence_exact:
        blockers.insert(
            0,
            "PRE_REGISTRATION_RECEIPT_FORMAL_ABSENCE_NOT_EXACT",
        )

    evidence_source = (
        execution_evidence_v4_document.get("source", {})
        if evidence_exact
        else {}
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION,
        "source": {
            "implementation_delta_manifest_contract_verified": (
                manifest_exact
            ),
            "implementation_fingerprints_match": manifest_exact,
            "expected_delta_manifest_sha256": strict_canonical_hash(
                _EXPECTED_DELTA_MANIFEST
            ),
            "implementation_pin_count": len(_EXPECTED_DELTA_MANIFEST),
            "production_pin_count": sum(
                role == "production" for role in _ARTIFACT_ROLES.values()
            ),
            "verification_pin_count": sum(
                role == "verification" for role in _ARTIFACT_ROLES.values()
            ),
            "decision_record_pin_count": sum(
                role == "decision" for role in _ARTIFACT_ROLES.values()
            ),
            "predecessor_pin_count": sum(
                role == "predecessor" for role in _ARTIFACT_ROLES.values()
            ),
            "artifacts": _artifact_rows(),
            "artifact_files_read": False,
            "artifacts_executed": False,
            "supplied_manifest_embedded": False,
            "predecessor_registration_v6_exact": predecessor_exact,
            "execution_evidence_v4_exact": evidence_exact,
            "pre_registration_formal_absence_exact": (
                pre_registration_formal_absence_exact
            ),
            "local_contract_complete": local_contract_complete,
        },
        "consumer": {
            "predecessor_registration_schema_version": (
                registration_v6.SCHEMA_VERSION
            ),
            "predecessor_registration_static_fingerprint": (
                registration_v6.STATIC_FINGERPRINT
            ),
            "predecessor_registration_implementation_sha256": (
                REGISTRATION_V6_IMPLEMENTATION_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "execution_evidence_schema_version": (
                evidence_v4.SCHEMA_VERSION if evidence_exact else "UNKNOWN"
            ),
            "execution_evidence_static_fingerprint": (
                evidence_v4.STATIC_FINGERPRINT
                if evidence_exact
                else "UNKNOWN"
            ),
            "execution_evidence_implementation_sha256": (
                EVIDENCE_V4_IMPLEMENTATION_SHA256
            ),
            "execution_evidence_hash": (
                execution_evidence_v4_document.get("evidence_hash")
                if evidence_exact
                else None
            ),
            "execution_evidence_status": (
                execution_evidence_v4_document.get("status")
                if evidence_exact
                else "UNKNOWN"
            ),
            "execution_semantic_state": (
                semantic_state if evidence_exact else "UNVERIFIED"
            ),
            "receipt_v4_schema_version": (
                evidence_source.get("receipt_v4_schema_version", "UNKNOWN")
            ),
            "receipt_v4_hash": evidence_source.get("receipt_v4_hash"),
            "receipt_v4_verification_hash": evidence_source.get(
                "receipt_v4_verification_hash"
            ),
            "projection_v6_schema_version": evidence_source.get(
                "projection_v6_schema_version",
                "UNKNOWN",
            ),
            "projection_v6_hash": evidence_source.get("projection_v6_hash"),
            "execution_preregistration_v1_schema_version": (
                evidence_source.get(
                    "execution_preregistration_v1_schema_version",
                    "UNKNOWN",
                )
            ),
            "execution_preregistration_v1_hash": evidence_source.get(
                "execution_preregistration_v1_hash"
            ),
            "pre_registration_receipt_formal_registration_schema_version": (
                None
            ),
            "pre_registration_receipt_formal_registration_hash": None,
            "registration_state": "CANDIDATE_BLOCKED",
        },
        "contract_pins": {
            "registration_v6_implementation_sha256": (
                REGISTRATION_V6_IMPLEMENTATION_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "execution_evidence_v4_implementation_sha256": (
                EVIDENCE_V4_IMPLEMENTATION_SHA256
            ),
            "execution_evidence_v4_hash": (
                execution_evidence_v4_document.get("evidence_hash")
                if evidence_exact
                else None
            ),
            "receipt_v4_hash": evidence_source.get("receipt_v4_hash"),
            "receipt_v4_verification_hash": evidence_source.get(
                "receipt_v4_verification_hash"
            ),
            "projection_v6_hash": evidence_source.get("projection_v6_hash"),
            "execution_preregistration_v1_hash": evidence_source.get(
                "execution_preregistration_v1_hash"
            ),
            "execution_semantic_state": (
                semantic_state if evidence_exact else "UNVERIFIED"
            ),
            "pre_registration_receipt_formal_registration_absent": (
                pre_registration_formal_absence_exact
            ),
            "downside_tail_version_chain_exact": local_contract_complete,
        },
        "closed_local_blockers": (
            [
                "REGISTRATION_V6_PREDECESSOR_CHAIN_PRESERVED",
                "DOWNSIDE_TAIL_CORRELATED_CLUSTER_JOINT_GATE_VERSIONED",
                "NEUTRAL_SOURCE_GAP_MATURITY_PERMISSION_PROJECTION_VERSIONED",
                "UNMOUNTED_CONSUMER_AND_STYLESHEET_PINNED",
                "EXECUTION_PREREGISTRATION_AND_RECEIPT_V4_VERSIONED",
                "PYTHON_EXECUTION_EVIDENCE_V4_THREE_STATE_CROSS_BINDING_VERSIONED",
            ]
            if local_contract_complete
            else []
        ),
        "blockers": blockers,
        "activation_order": [
            "REGISTRATION_V6_PREDECESSOR_CHAIN",
            "DOWNSIDE_TAIL_JOINT_RISK_ADAPTER_AND_NEUTRAL_ENVELOPE",
            "HTTP_CANDIDATE_PROJECTION_AND_UNMOUNTED_CONSUMER_V6",
            "LOCAL_NODE_EXECUTION_PREREGISTRATION_V1",
            "PRE_REGISTRATION_LOCAL_NODE_EXECUTION_RECEIPT_V4",
            "PYTHON_EXECUTION_EVIDENCE_V4",
            "REGISTRATION_V7_STATIC_CANDIDATE",
            "FUTURE_POST_REGISTRATION_EXECUTION_RECEIPT",
            "EXTERNAL_POLICY_REGISTRY_AND_WITNESS_IDENTITY",
            "INDEPENDENT_PROCESS_WITNESS_AND_SHARED_ANTI_REPLAY",
            "EXPLICIT_BROWSER_VISUAL_REVIEW",
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        ],
        "facts": {
            "registration_candidate_built": True,
            "registration_activated": False,
            "formal_registration_candidate_versioned": True,
            "predecessor_registration_preserved": predecessor_exact,
            "implementation_delta_manifest_pinned": manifest_exact,
            "execution_evidence_v4_bound": evidence_exact,
            "execution_evidence_semantic_state_preserved": evidence_exact,
            "pre_registration_execution_receipt_bound": evidence_exact,
            "pre_registration_receipt_formal_registration_bound": False,
            "post_registration_execution_receipt_required": True,
            "post_registration_execution_receipt_issued": False,
            "formal_registry_activated": False,
            "external_witness_policy_registry_bound": False,
            "witness_organization_identity_verified": False,
            "independent_execution_process_witnessed": False,
            "shared_anti_replay_registry_checked": False,
            "browser_visual_review_performed": False,
            "server_route_registered": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "implementation_manifest_externally_attested": False,
            "implementation_hashes_runtime_verified": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
    document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
        current_implementation_sha256,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    exact = isinstance(document, dict) and strict_json_contract_equal(
        document,
        expected,
    )
    seal_exact = exact and _sealed_exact(document, "registration_hash")
    manifest_exact = _manifest_exact(current_implementation_sha256)
    local_contract_complete = bool(
        expected.get("source", {}).get("local_contract_complete") is True
    )
    passed = bool(
        exact and seal_exact and manifest_exact and local_contract_complete
    )
    blockers = []
    if not exact or not seal_exact:
        blockers.append("registration_v7_exact_rebuild")
    if not manifest_exact:
        blockers.append("registration_v7_delta_manifest_exact")
    if not local_contract_complete:
        blockers.append("registration_v7_local_contract_complete")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "registration_exactly_rebuilt": exact,
        "registration_seal_verified": seal_exact,
        "manifest_exact": manifest_exact,
        "local_contract_complete": local_contract_complete,
        "registration_status": (
            expected.get("status") if exact else "UNKNOWN"
        ),
        "execution_semantic_state": (
            expected.get("consumer", {}).get(
                "execution_semantic_state",
                "UNVERIFIED",
            )
            if exact
            else "UNVERIFIED"
        ),
        "registration_hash": (
            expected.get("registration_hash") if passed else None
        ),
        "blockers": blockers,
        "post_registration_execution_receipt_issued": False,
        "formal_registry_activated": False,
        "external_witness_policy_registry_bound": False,
        "witness_organization_identity_verified": False,
        "independent_execution_process_witnessed": False,
        "browser_visual_review_verified": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
