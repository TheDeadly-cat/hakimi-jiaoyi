"""Static registration successor pinning presentation HTTP candidate-v5."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v3"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v3-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260823-presentation-http-candidate-v5-registration-v3-lock-1"
)
STATUS = "BLOCKED"
DECISION = (
    "HTTP_CANDIDATE_V5_PINNED_FRONTEND_PROJECTION_ROUTE_DOM_BROWSER_AND_ACTIVATION_UNBOUND"
)

PRESENTATION_REGISTRATION_V2_SHA256 = (
    "c190e3aa49777b1c73a7cf0a12e534ef829003227818cc6412b68b388980f4cc"
)
PRESENTATION_HTTP_CANDIDATE_V5_SHA256 = (
    "ec407914dc260a1110e17ee932c80a5d5786183e4c34601f9604d0e88482358b"
)
PRESENTATION_HTTP_CANDIDATE_V5_TEST_SHA256 = (
    "e11b3e813ca5d6bb9e322c1b482d7534577ab4bc21a60f72147ed9766871c543"
)
PRESENTATION_HTTP_CANDIDATE_V5_ADR_SHA256 = (
    "60788393e579242d028565f0737d39af28da6ef2a0dba21b8617d29bfb06b57b"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_EXPECTED_MANIFEST = {
    "presentation_registration_v2": PRESENTATION_REGISTRATION_V2_SHA256,
    "presentation_http_candidate_v5": PRESENTATION_HTTP_CANDIDATE_V5_SHA256,
    "presentation_http_candidate_v5_test": PRESENTATION_HTTP_CANDIDATE_V5_TEST_SHA256,
    "presentation_http_candidate_v5_adr": PRESENTATION_HTTP_CANDIDATE_V5_ADR_SHA256,
    "strict_canonical_json_hash_py": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
}
_ARTIFACTS = (
    {
        "artifact_id": "presentation_registration_v2",
        "path": "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2.py",
        "role": "PREDECESSOR",
        "expected_sha256": PRESENTATION_REGISTRATION_V2_SHA256,
    },
    {
        "artifact_id": "presentation_http_candidate_v5",
        "path": "exchange_terminal/interfaces/http/strategy_correlation_cluster_portfolio_risk_presentation_candidate_v5.py",
        "role": "PRODUCTION",
        "expected_sha256": PRESENTATION_HTTP_CANDIDATE_V5_SHA256,
    },
    {
        "artifact_id": "presentation_http_candidate_v5_test",
        "path": "tests/test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v5.py",
        "role": "VERIFICATION",
        "expected_sha256": PRESENTATION_HTTP_CANDIDATE_V5_TEST_SHA256,
    },
    {
        "artifact_id": "presentation_http_candidate_v5_adr",
        "path": "docs/adr/0214-presentation-http-candidate-v5-adapter-v5-binding.md",
        "role": "DECISION_RECORD",
        "expected_sha256": PRESENTATION_HTTP_CANDIDATE_V5_ADR_SHA256,
    },
    {
        "artifact_id": "strict_canonical_json_hash_py",
        "path": "exchange_terminal/services/strict_canonical_json_hash.py",
        "role": "PRODUCTION",
        "expected_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    },
)
_BLOCKERS = (
    "implementation_manifest_external_attestation_not_bound",
    "candidate_v5_external_artifact_attestation_not_bound",
    "candidate_v5_execution_evidence_not_independently_bound",
    "http_candidate_to_frontend_projection_v5_unversioned",
    "http_route_unregistered",
    "isolated_dom_contract_review_not_performed",
    "browser_visual_review_not_performed",
    "presentation_consumer_registration_activation_unauthorized",
    "presentation_mount_unauthorized",
    "current_switch_unauthorized",
)
_ACTIVATION_ORDER = (
    "BIND_EXTERNAL_IMPLEMENTATION_MANIFEST_ATTESTATION",
    "INDEPENDENTLY_BIND_CANDIDATE_V5_EXECUTION_EVIDENCE",
    "VERSION_HTTP_CANDIDATE_V5_TO_FRONTEND_PROJECTION_CONSUMER",
    "EXECUTE_STATIC_CROSS_RUNTIME_CONSUMER_FIXTURE",
    "INDEPENDENTLY_REVIEW_RENDER_DESCRIPTOR_AND_LOAD_ORDER",
    "AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW",
    "AUTHORIZE_BROWSER_VISUAL_REVIEW",
    "SEPARATELY_AUTHORIZE_PRESENTATION_CONSUMER_REGISTRATION",
    "SEPARATELY_AUTHORIZE_HTTP_ROUTE_AND_PRESENTATION_MOUNT",
    "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
)


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _manifest_exact(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(_EXPECTED_MANIFEST)
        and all(_is_hash(item) for item in value.values())
        and strict_json_contract_equal(value, _EXPECTED_MANIFEST)
    )


def _authority() -> dict[str, bool]:
    return {
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


def expected_presentation_consumer_implementation_sha256_v3() -> dict[str, str]:
    """Return a detached exact manifest expected from an external caller."""

    return deepcopy(_EXPECTED_MANIFEST)


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Build a static blocked registration record without reading artifact files."""

    manifest_exact = _manifest_exact(current_implementation_sha256)
    blockers = list(_BLOCKERS)
    if not manifest_exact:
        blockers.insert(0, "implementation_manifest_contract_invalid")

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION,
        "source": {
            "implementation_manifest_contract_verified": manifest_exact,
            "implementation_fingerprints_match": manifest_exact,
            "implementation_pin_count": len(_EXPECTED_MANIFEST),
            "predecessor_pin_count": 1,
            "production_pin_count": 2,
            "verification_pin_count": 1,
            "decision_record_pin_count": 1,
            "expected_manifest_sha256": strict_canonical_hash(_EXPECTED_MANIFEST),
            "supplied_manifest_embedded": False,
            "artifact_files_read": False,
            "artifacts": deepcopy(list(_ARTIFACTS)),
        },
        "contract_pins": {
            "predecessor_registration_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v2"
            ),
            "predecessor_registration_static_fingerprint": (
                "20260823-weighted-diversification-presentation-consumer-registration-v2-lock-1"
            ),
            "predecessor_registration_implementation_sha256": (
                PRESENTATION_REGISTRATION_V2_SHA256
            ),
            "http_candidate_request_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-request-v5"
            ),
            "http_candidate_response_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v5"
            ),
            "http_candidate_payload_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v5"
            ),
            "http_candidate_static_fingerprint": (
                "20260823-portfolio-risk-presentation-http-adapter-v5-unregistered-candidate-1"
            ),
            "http_candidate_implementation_sha256": (
                PRESENTATION_HTTP_CANDIDATE_V5_SHA256
            ),
            "http_candidate_test_sha256": PRESENTATION_HTTP_CANDIDATE_V5_TEST_SHA256,
            "http_candidate_adr_sha256": PRESENTATION_HTTP_CANDIDATE_V5_ADR_SHA256,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
            "composition_policy": (
                "PINNED_HTTP_CANDIDATE_V5_PREREQUISITE_ONLY_NO_FRONTEND_BINDING"
            ),
            "implementation_identity_policy": (
                "EXTERNAL_MANIFEST_EXACT_NO_SELF_CERTIFICATION_V3"
            ),
            "mount_policy": "NO_ROUTE_NO_DOM_TARGET_NO_SELECTOR_NO_MOUNT_API_V3",
            "permission_policy": "ALWAYS_UNAUTHORIZED_V3",
        },
        "consumer": {
            "consumer_id": "portfolio-risk-weighted-diversification-v4",
            "input_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-projection-v4"
            ),
            "output_schema_version": (
                "portfolio-risk-weighted-diversification-presentation-consumer-fixture-v4"
            ),
            "http_candidate_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v5"
            ),
            "http_to_projection_binding_state": "UNBOUND",
            "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
            "registration_state": "CANDIDATE_ONLY",
            "execution_mode": "UNMOUNTED_STATIC_REGISTRATION_ONLY",
            "dom_target": None,
            "selector": None,
        },
        "closed_local_blockers": (
            ["presentation_http_contract_not_versioned"] if manifest_exact else []
        ),
        "blockers": blockers,
        "activation_order": list(_ACTIVATION_ORDER),
        "facts": {
            "registration_candidate_built": True,
            "registration_activated": False,
            "predecessor_registration_preserved": manifest_exact,
            "presentation_http_contract_versioned": manifest_exact,
            "presentation_http_candidate_v5_pinned": manifest_exact,
            "presentation_http_candidate_v5_test_pinned": manifest_exact,
            "presentation_http_candidate_v5_adr_pinned": manifest_exact,
            "implementation_manifest_externally_attested": False,
            "candidate_v5_execution_evidence_independently_bound": False,
            "http_candidate_to_frontend_projection_bound": False,
            "static_cross_runtime_consumer_executed": False,
            "render_descriptor_reviewed": False,
            "dependency_load_order_reviewed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "ui_mounted": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Verify an exact static rebuild and return a non-authoritative receipt."""

    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
        current_implementation_sha256
    )
    exact = (
        isinstance(document, dict)
        and strict_json_contract_equal(document, expected)
        and document.get("registration_hash") == expected.get("registration_hash")
    )
    manifest_exact = _manifest_exact(current_implementation_sha256)
    passed = exact and manifest_exact
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "registration_exactly_verified": exact,
        "implementation_manifest_exactly_verified": manifest_exact,
        "registration_status": document.get("status") if exact else None,
        "registration_hash": document.get("registration_hash") if exact else None,
        "blockers": [] if passed else ["REGISTRATION_V3_OR_MANIFEST_NOT_EXACT"],
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
