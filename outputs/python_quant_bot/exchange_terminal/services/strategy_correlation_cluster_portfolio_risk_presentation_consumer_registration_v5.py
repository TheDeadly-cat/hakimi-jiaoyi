from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
    as registration_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v5"
)
STATIC_FINGERPRINT = (
    "20260823-consumer-v5-receipt-evidence-registration-v5-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "REGISTRATION_V4_RECEIPT_V3_EVIDENCE_V3_PINNED_PROCESS_IDENTITY_"
    "DESCRIPTOR_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)
REGISTRATION_V4_IMPLEMENTATION_SHA256 = (
    "b7b0b8faf64d34796b6ae97e6594ea08a0fcd930272fa4841e4a7bd0ebecd897"
)
STRICT_CANONICAL_PYTHON_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
RECEIPT_V3_JAVASCRIPT_SHA256 = (
    "9a90650656f63cd8026fcee224ed4e3d690ced6a7d8bd2970772c653e55c2acb"
)
RECEIPT_V3_TEST_JAVASCRIPT_SHA256 = (
    "45c1a6ae1c46a95977df4d74b2da99dc753c0294806de78f937a21971d4c4cdd"
)
RECEIPT_V3_CROSS_RUNTIME_TEST_PYTHON_SHA256 = (
    "01998bd7802b38d81adea7fd5a219749f9e7312966548a5e74361f1e88e5053c"
)
ADR_0219_SHA256 = (
    "f085564db95e8a4427acf20cd573cb2d5d17e24eb21eba20d482f6c39ec577e7"
)
EVIDENCE_V3_PYTHON_SHA256 = (
    "0c42538f37bfc165d15ca34fe4136f87df9fdffb411ed1a64d8f2be26c2fdb85"
)
EVIDENCE_V3_TEST_PYTHON_SHA256 = (
    "e6ace457247b65202690c5dd73a0f816c4821268af85f1c81b7eef44bc912228"
)
ADR_0220_SHA256 = (
    "3a00d053285d1f130cae5c99efb3ac2115bf440f3601a5c383faa87825725df6"
)
RECEIPT_V3_SCHEMA_VERSION = (
    "portfolio-risk-joint-evidence-consumer-execution-receipt-v3"
)
EVIDENCE_V3_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "execution-evidence-v3"
)

_EXPECTED_MANIFEST = {
    "presentation_registration_v4": REGISTRATION_V4_IMPLEMENTATION_SHA256,
    "strict_canonical_json_hash_py": STRICT_CANONICAL_PYTHON_SHA256,
    "consumer_execution_receipt_v3_js": RECEIPT_V3_JAVASCRIPT_SHA256,
    "consumer_execution_receipt_v3_test_js": (
        RECEIPT_V3_TEST_JAVASCRIPT_SHA256
    ),
    "consumer_execution_receipt_v3_cross_runtime_test_py": (
        RECEIPT_V3_CROSS_RUNTIME_TEST_PYTHON_SHA256
    ),
    "consumer_execution_receipt_v3_adr": ADR_0219_SHA256,
    "consumer_execution_evidence_v3_py": EVIDENCE_V3_PYTHON_SHA256,
    "consumer_execution_evidence_v3_test_py": (
        EVIDENCE_V3_TEST_PYTHON_SHA256
    ),
    "consumer_execution_evidence_v3_adr": ADR_0220_SHA256,
}
_ARTIFACT_ROLES = {
    "presentation_registration_v4": "predecessor",
    "strict_canonical_json_hash_py": "contract",
    "consumer_execution_receipt_v3_js": "production",
    "consumer_execution_receipt_v3_test_js": "verification",
    "consumer_execution_receipt_v3_cross_runtime_test_py": "verification",
    "consumer_execution_receipt_v3_adr": "decision",
    "consumer_execution_evidence_v3_py": "production",
    "consumer_execution_evidence_v3_test_py": "verification",
    "consumer_execution_evidence_v3_adr": "decision",
}
_AUTHORITY = {
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


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _manifest_exact(value: Any) -> bool:
    return isinstance(value, dict) and strict_json_contract_equal(
        value,
        _EXPECTED_MANIFEST,
    )


def _predecessor_registration() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = (
        registration_v4.expected_presentation_consumer_implementation_sha256_v4()
    )
    document = (
        registration_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            manifest
        )
    )
    verification = (
        registration_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            document,
            manifest,
        )
    )
    return document, verification


def _artifact_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact": name,
            "role": _ARTIFACT_ROLES[name],
            "sha256": _EXPECTED_MANIFEST[name],
        }
        for name in sorted(_EXPECTED_MANIFEST)
    ]


def expected_presentation_consumer_implementation_sha256_v5() -> dict[str, str]:
    return dict(_EXPECTED_MANIFEST)


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    manifest_exact = _manifest_exact(current_implementation_sha256)
    predecessor, predecessor_verification = _predecessor_registration()
    predecessor_exact = bool(
        predecessor_verification.get("status") == "PASS"
        and predecessor.get("schema_version") == registration_v4.SCHEMA_VERSION
        and predecessor.get("static_fingerprint")
        == registration_v4.STATIC_FINGERPRINT
        and _is_hash(predecessor.get("registration_hash"))
    )
    local_contract_complete = manifest_exact and predecessor_exact

    blockers = [
        "INDEPENDENT_NODE_PROCESS_WITNESS_UNVERIFIED",
        "PROCESS_IDENTITY_AND_RECEIPT_SIGNATURE_UNVERIFIED",
        "DESCRIPTOR_AND_DEPENDENCY_LOAD_ORDER_REVIEW_UNPERFORMED",
        "DOM_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNAUTHORIZED",
    ]
    if not manifest_exact:
        blockers.insert(0, "IMPLEMENTATION_MANIFEST_MISMATCH")
    if not predecessor_exact:
        blockers.insert(0, "PREDECESSOR_REGISTRATION_V4_NOT_EXACT")

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION,
        "source": {
            "implementation_manifest_contract_verified": manifest_exact,
            "implementation_fingerprints_match": manifest_exact,
            "expected_manifest_sha256": strict_canonical_hash(
                _EXPECTED_MANIFEST
            ),
            "implementation_pin_count": len(_EXPECTED_MANIFEST),
            "production_pin_count": sum(
                role == "production" for role in _ARTIFACT_ROLES.values()
            ),
            "verification_pin_count": sum(
                role == "verification"
                for role in _ARTIFACT_ROLES.values()
            ),
            "decision_record_pin_count": sum(
                role == "decision" for role in _ARTIFACT_ROLES.values()
            ),
            "predecessor_pin_count": sum(
                role == "predecessor"
                for role in _ARTIFACT_ROLES.values()
            ),
            "contract_pin_count": sum(
                role == "contract" for role in _ARTIFACT_ROLES.values()
            ),
            "artifacts": _artifact_rows(),
            "artifact_files_read": False,
            "artifacts_executed": False,
            "supplied_manifest_embedded": False,
        },
        "consumer": {
            "predecessor_registration_schema_version": (
                registration_v4.SCHEMA_VERSION
            ),
            "predecessor_registration_static_fingerprint": (
                registration_v4.STATIC_FINGERPRINT
            ),
            "predecessor_registration_implementation_sha256": (
                REGISTRATION_V4_IMPLEMENTATION_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "receipt_schema_version": RECEIPT_V3_SCHEMA_VERSION,
            "receipt_implementation_sha256": RECEIPT_V3_JAVASCRIPT_SHA256,
            "evidence_schema_version": EVIDENCE_V3_SCHEMA_VERSION,
            "evidence_implementation_sha256": EVIDENCE_V3_PYTHON_SHA256,
            "registration_state": "CANDIDATE_BLOCKED",
        },
        "contract_pins": {
            "registration_v4_implementation_sha256": (
                REGISTRATION_V4_IMPLEMENTATION_SHA256
            ),
            "receipt_v3_implementation_sha256": (
                RECEIPT_V3_JAVASCRIPT_SHA256
            ),
            "evidence_v3_implementation_sha256": EVIDENCE_V3_PYTHON_SHA256,
            "strict_canonical_python_sha256": (
                STRICT_CANONICAL_PYTHON_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "receipt_to_evidence_version_chain_exact": local_contract_complete,
        },
        "closed_local_blockers": (
            [
                "CONSUMER_V5_EXECUTION_RECEIPT_VERSIONED",
                "CONSUMER_V5_EXECUTION_EVIDENCE_CROSS_DOCUMENT_BOUND",
                "REGISTRATION_V4_RECEIPT_V3_EVIDENCE_V3_STATIC_CHAIN_PINNED",
            ]
            if local_contract_complete
            else []
        ),
        "blockers": blockers,
        "activation_order": [
            "REGISTRATION_V4_STATIC_FRONTEND_CHAIN",
            "RECEIPT_V3_LOCAL_NODE_EXECUTION_OBSERVATION",
            "EVIDENCE_V3_PYTHON_CROSS_DOCUMENT_BINDING",
            "REGISTRATION_V5_STATIC_CANDIDATE",
            "INDEPENDENT_EXECUTION_IDENTITY_OR_SIGNATURE_EVIDENCE",
            "DESCRIPTOR_AND_DEPENDENCY_LOAD_ORDER_REVIEW",
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        ],
        "facts": {
            "registration_candidate_built": True,
            "registration_activated": False,
            "predecessor_registration_preserved": predecessor_exact,
            "receipt_v3_contract_pinned": manifest_exact,
            "evidence_v3_contract_pinned": manifest_exact,
            "receipt_to_evidence_version_chain_pinned": local_contract_complete,
            "verification_artifacts_pinned": manifest_exact,
            "implementation_manifest_externally_attested": False,
            "implementation_hashes_runtime_verified": False,
            "independent_node_process_witnessed": False,
            "node_process_identity_authenticated": False,
            "receipt_signature_verified": False,
            "render_descriptor_reviewed": False,
            "dependency_load_order_reviewed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "server_route_registered": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            current_implementation_sha256
        )
    )
    exact = isinstance(document, dict) and strict_json_contract_equal(
        document,
        expected,
    )
    manifest_exact = _manifest_exact(current_implementation_sha256)
    seal_exact = bool(
        exact
        and _is_hash(document.get("registration_hash"))
        and document.get("registration_hash")
        == expected.get("registration_hash")
    )
    passed = exact and seal_exact and manifest_exact
    blockers = []
    if not exact or not seal_exact:
        blockers.append("registration_v5_exact_rebuild")
    if not manifest_exact:
        blockers.append("registration_v5_manifest_exact")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "registration_exactly_rebuilt": exact,
        "registration_seal_verified": seal_exact,
        "manifest_exact": manifest_exact,
        "registration_status": (
            expected.get("status") if exact else "UNKNOWN"
        ),
        "registration_hash": (
            expected.get("registration_hash") if passed else None
        ),
        "blockers": blockers,
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
