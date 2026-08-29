from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5
    as registration_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v6"
)
STATIC_FINGERPRINT = (
    "20260823-witness-descriptor-review-registration-v6-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "REGISTRATION_V5_WITNESS_SIGNATURE_DESCRIPTOR_STATIC_REVIEW_PINNED_"
    "EXTERNAL_IDENTITY_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)
REGISTRATION_V5_IMPLEMENTATION_SHA256 = (
    "5205b4dfb3a33e5903c9f8c0015383352f2cd1fd84eb38563f2f6364f08d08d3"
)
STRICT_CANONICAL_PYTHON_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
WITNESS_SIGNATURE_JAVASCRIPT_SHA256 = (
    "8d085ae6528d16f50888b167b7ed3c913a5eed12977f80290c02bc07c55e7156"
)
WITNESS_SIGNATURE_TEST_JAVASCRIPT_SHA256 = (
    "616651425f13af8208bbb71de3abbfc1aa775c92f00451872cf0b08c6973fca9"
)
WITNESS_SIGNATURE_CROSS_RUNTIME_TEST_PYTHON_SHA256 = (
    "98bc1e2923bcf49ee7b0525cf88887a3fa33a0193e5868829446410e0fbd7a52"
)
ADR_0222_SHA256 = (
    "594e75db853854c46c577c15b8f3c04796c4ea32ebcfa0e18e2ab6ab88df4345"
)
DESCRIPTOR_REVIEW_JAVASCRIPT_SHA256 = (
    "cd6b70d2b7c131678e3c5f9de4095f9d8508836e336a8936efc61d21aa2424d5"
)
DESCRIPTOR_REVIEW_TEST_JAVASCRIPT_SHA256 = (
    "5e1cfe5e2fcca9bf40beb33940fa0c91b838238cadf92687b0a7fdb997edbca3"
)
DESCRIPTOR_REVIEW_CROSS_RUNTIME_TEST_PYTHON_SHA256 = (
    "4db2b635718e0ed5ebc607e1eca7f0cf1be93e99eaeeb04933b73c509ccd4d98"
)
ADR_0223_SHA256 = (
    "c3a6b01671324fc4f5e7b8ba41ccc7493f3dd34faf18e68f4dfb4050940ea4bc"
)
WITNESS_POLICY_SCHEMA_VERSION = (
    "portfolio-risk-execution-witness-preregistration-policy-v1"
)
WITNESS_CHALLENGE_SCHEMA_VERSION = (
    "portfolio-risk-execution-witness-document-bundle-challenge-v1"
)
WITNESS_VERIFICATION_SCHEMA_VERSION = (
    "portfolio-risk-execution-witness-signature-verification-candidate-v1"
)
DESCRIPTOR_REVIEW_SCHEMA_VERSION = (
    "portfolio-risk-joint-evidence-descriptor-load-order-static-review-v1"
)

_EXPECTED_MANIFEST = {
    "presentation_registration_v5": REGISTRATION_V5_IMPLEMENTATION_SHA256,
    "strict_canonical_json_hash_py": STRICT_CANONICAL_PYTHON_SHA256,
    "strict_canonical_json_v1_js": STRICT_CANONICAL_JAVASCRIPT_SHA256,
    "execution_witness_signature_candidate_v1_js": (
        WITNESS_SIGNATURE_JAVASCRIPT_SHA256
    ),
    "execution_witness_signature_candidate_v1_test_js": (
        WITNESS_SIGNATURE_TEST_JAVASCRIPT_SHA256
    ),
    "execution_witness_signature_cross_runtime_v1_test_py": (
        WITNESS_SIGNATURE_CROSS_RUNTIME_TEST_PYTHON_SHA256
    ),
    "execution_witness_signature_candidate_v1_adr": ADR_0222_SHA256,
    "descriptor_load_order_review_v1_js": (
        DESCRIPTOR_REVIEW_JAVASCRIPT_SHA256
    ),
    "descriptor_load_order_review_v1_test_js": (
        DESCRIPTOR_REVIEW_TEST_JAVASCRIPT_SHA256
    ),
    "descriptor_load_order_review_cross_runtime_v1_test_py": (
        DESCRIPTOR_REVIEW_CROSS_RUNTIME_TEST_PYTHON_SHA256
    ),
    "descriptor_load_order_review_v1_adr": ADR_0223_SHA256,
}
_ARTIFACT_ROLES = {
    "presentation_registration_v5": "predecessor",
    "strict_canonical_json_hash_py": "contract",
    "strict_canonical_json_v1_js": "contract",
    "execution_witness_signature_candidate_v1_js": "production",
    "execution_witness_signature_candidate_v1_test_js": "verification",
    "execution_witness_signature_cross_runtime_v1_test_py": "verification",
    "execution_witness_signature_candidate_v1_adr": "decision",
    "descriptor_load_order_review_v1_js": "production",
    "descriptor_load_order_review_v1_test_js": "verification",
    "descriptor_load_order_review_cross_runtime_v1_test_py": "verification",
    "descriptor_load_order_review_v1_adr": "decision",
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
        registration_v5.expected_presentation_consumer_implementation_sha256_v5()
    )
    document = (
        registration_v5.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            manifest
        )
    )
    verification = (
        registration_v5.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
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


def expected_presentation_consumer_implementation_sha256_v6() -> dict[str, str]:
    return dict(_EXPECTED_MANIFEST)


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    manifest_exact = _manifest_exact(current_implementation_sha256)
    predecessor, predecessor_verification = _predecessor_registration()
    predecessor_exact = bool(
        predecessor_verification.get("status") == "PASS"
        and predecessor.get("schema_version") == registration_v5.SCHEMA_VERSION
        and predecessor.get("static_fingerprint")
        == registration_v5.STATIC_FINGERPRINT
        and _is_hash(predecessor.get("registration_hash"))
    )
    local_contract_complete = manifest_exact and predecessor_exact

    blockers = [
        "EXTERNAL_WITNESS_POLICY_REGISTRY_AND_IDENTITY_UNBOUND",
        "INDEPENDENT_EXECUTION_PROCESS_WITNESS_AND_ANTI_REPLAY_UNVERIFIED",
        "BROWSER_VISUAL_REVIEW_UNPERFORMED",
        "PRODUCTION_ROUTE_MOUNT_AND_ACTIVATION_UNAUTHORIZED",
    ]
    if not manifest_exact:
        blockers.insert(0, "IMPLEMENTATION_MANIFEST_MISMATCH")
    if not predecessor_exact:
        blockers.insert(0, "PREDECESSOR_REGISTRATION_V5_NOT_EXACT")

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
                registration_v5.SCHEMA_VERSION
            ),
            "predecessor_registration_static_fingerprint": (
                registration_v5.STATIC_FINGERPRINT
            ),
            "predecessor_registration_implementation_sha256": (
                REGISTRATION_V5_IMPLEMENTATION_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "witness_policy_schema_version": WITNESS_POLICY_SCHEMA_VERSION,
            "witness_challenge_schema_version": (
                WITNESS_CHALLENGE_SCHEMA_VERSION
            ),
            "witness_verification_schema_version": (
                WITNESS_VERIFICATION_SCHEMA_VERSION
            ),
            "witness_implementation_sha256": (
                WITNESS_SIGNATURE_JAVASCRIPT_SHA256
            ),
            "descriptor_review_schema_version": (
                DESCRIPTOR_REVIEW_SCHEMA_VERSION
            ),
            "descriptor_review_implementation_sha256": (
                DESCRIPTOR_REVIEW_JAVASCRIPT_SHA256
            ),
            "registration_state": "CANDIDATE_BLOCKED",
        },
        "contract_pins": {
            "registration_v5_implementation_sha256": (
                REGISTRATION_V5_IMPLEMENTATION_SHA256
            ),
            "witness_signature_implementation_sha256": (
                WITNESS_SIGNATURE_JAVASCRIPT_SHA256
            ),
            "descriptor_review_implementation_sha256": (
                DESCRIPTOR_REVIEW_JAVASCRIPT_SHA256
            ),
            "predecessor_registration_hash": (
                predecessor.get("registration_hash")
                if predecessor_exact
                else None
            ),
            "witness_and_review_version_chain_exact": local_contract_complete,
        },
        "closed_local_blockers": (
            [
                "PREREGISTERED_KEY_POSSESSION_VERIFICATION_VERSIONED",
                "DESCRIPTOR_STATIC_REVIEW_VERSIONED",
                "DEPENDENCY_LOAD_ORDER_STATIC_REVIEW_VERSIONED",
            ]
            if local_contract_complete
            else []
        ),
        "blockers": blockers,
        "activation_order": [
            "REGISTRATION_V5_RECEIPT_EVIDENCE_CHAIN",
            "WITNESS_SIGNATURE_KEY_POSSESSION_CANDIDATE",
            "DESCRIPTOR_AND_LOAD_ORDER_STATIC_REVIEW",
            "REGISTRATION_V6_STATIC_CANDIDATE",
            "EXTERNAL_POLICY_REGISTRY_AND_WITNESS_IDENTITY",
            "INDEPENDENT_PROCESS_WITNESS_AND_SHARED_ANTI_REPLAY",
            "EXPLICIT_BROWSER_VISUAL_REVIEW",
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        ],
        "facts": {
            "registration_candidate_built": True,
            "registration_activated": False,
            "predecessor_registration_preserved": predecessor_exact,
            "witness_signature_contract_pinned": manifest_exact,
            "cryptographic_key_possession_verification_versioned": (
                manifest_exact
            ),
            "external_witness_policy_registry_bound": False,
            "witness_organization_identity_verified": False,
            "independent_execution_process_witnessed": False,
            "shared_anti_replay_registry_checked": False,
            "descriptor_static_review_pinned": manifest_exact,
            "dependency_load_order_static_review_pinned": manifest_exact,
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


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
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
        blockers.append("registration_v6_exact_rebuild")
    if not manifest_exact:
        blockers.append("registration_v6_manifest_exact")
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
