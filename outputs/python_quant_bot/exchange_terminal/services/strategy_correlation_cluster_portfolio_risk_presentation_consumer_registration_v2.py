"""Static registration candidate for the sealed weighted-diversification view."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
    as registration_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v4 as projection_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v2"
)
STATIC_FINGERPRINT = (
    "20260823-weighted-diversification-presentation-consumer-"
    "registration-v2-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "UNMOUNTED_WEIGHTED_DIVERSIFICATION_CONSUMER_V4_REGISTERED_AS_"
    "CANDIDATE_HASHES_EXACT_EXECUTION_REVIEW_DOM_BROWSER_HTTP_AND_"
    "ACTIVATION_UNBOUND"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_EXPECTED_IMPLEMENTATION_SHA256 = {
    "presentation_registration_v1": (
        "6a5b4cd9a8a0e3552ec34b355c9a27f4560b5621557d605413aa8076c769cc7e"
    ),
    "portfolio_risk_projection_v4": (
        "a41f0a263a9fae6ec67e737ed24fa2d8b9a00a13cc9e868132611b26d9334f94"
    ),
    "portfolio_risk_projection_v4_test": (
        "3a93ef8ddfd0cd5f5eaeea2a68e837085b75ec25f3c988ec25946da0a57e0fb1"
    ),
    "strict_canonical_json_v1_js": (
        "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
    ),
    "weighted_diversification_card_v4_js": (
        "ff7e5868a0d8121f5d2076555a5fff994d1f3d2c2375be6dbf665c080cfa9163"
    ),
    "weighted_diversification_card_v4_css": (
        "b7da3a38748df65f7f35a0c17939acff115abacda65b30343ac0b49391663bdb"
    ),
    "weighted_diversification_card_v4_test_js": (
        "2c6b75644219380312e307275f954937b85258a1b834f06d3248a01078727acf"
    ),
    "weighted_diversification_consumer_fixture_v4_js": (
        "fc48c5c20f3d95cc62e4ab639e1edb3c2cc90f6212e9bbf04623e4fa886dc872"
    ),
    "weighted_diversification_consumer_fixture_v4_test_js": (
        "bc9089aff8a937e84a6dc30f69be189baff7eed4ba0af839f793c7d75c33bf3f"
    ),
    "weighted_diversification_cross_runtime_v4_test_py": (
        "f496bca5786418c77507a3316a49e3a6a4fb5bdff545209e78aa723a789d4872"
    ),
}

_ARTIFACT_PATHS = {
    "presentation_registration_v1": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_"
        "risk_presentation_consumer_registration_v1.py"
    ),
    "portfolio_risk_projection_v4": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_"
        "risk_projection_v4.py"
    ),
    "portfolio_risk_projection_v4_test": (
        "tests/test_strategy_correlation_cluster_portfolio_risk_projection_v4.py"
    ),
    "strict_canonical_json_v1_js": (
        "exchange_terminal/static/strict_canonical_json_v1.js"
    ),
    "weighted_diversification_card_v4_js": (
        "exchange_terminal/static/evidence_portfolio_risk_weighted_"
        "diversification_card_v4.js"
    ),
    "weighted_diversification_card_v4_css": (
        "exchange_terminal/static/evidence_portfolio_risk_weighted_"
        "diversification_card_v4.css"
    ),
    "weighted_diversification_card_v4_test_js": (
        "exchange_terminal/static/evidence_portfolio_risk_weighted_"
        "diversification_card_v4.test.js"
    ),
    "weighted_diversification_consumer_fixture_v4_js": (
        "exchange_terminal/static/evidence_portfolio_risk_weighted_"
        "diversification_consumer_fixture_v4.js"
    ),
    "weighted_diversification_consumer_fixture_v4_test_js": (
        "exchange_terminal/static/evidence_portfolio_risk_weighted_"
        "diversification_consumer_fixture_v4.test.js"
    ),
    "weighted_diversification_cross_runtime_v4_test_py": (
        "tests/test_strategy_correlation_cluster_portfolio_risk_"
        "presentation_consumer_cross_runtime_v4.py"
    ),
}

_ARTIFACT_ROLES = {
    "presentation_registration_v1": "PREDECESSOR",
    "portfolio_risk_projection_v4": "PRODUCTION",
    "portfolio_risk_projection_v4_test": "VERIFICATION",
    "strict_canonical_json_v1_js": "PRODUCTION",
    "weighted_diversification_card_v4_js": "PRODUCTION",
    "weighted_diversification_card_v4_css": "PRODUCTION",
    "weighted_diversification_card_v4_test_js": "VERIFICATION",
    "weighted_diversification_consumer_fixture_v4_js": "PRODUCTION",
    "weighted_diversification_consumer_fixture_v4_test_js": "VERIFICATION",
    "weighted_diversification_cross_runtime_v4_test_py": "VERIFICATION",
}

_BLOCKERS = (
    "implementation_manifest_external_attestation_not_bound",
    "projection_v4_evidence_not_bound",
    "consumer_fixture_v4_execution_evidence_not_bound",
    "consumer_fixture_v4_execution_receipt_not_versioned",
    "render_descriptor_independent_review_not_performed",
    "isolated_dom_contract_review_not_performed",
    "browser_visual_review_not_performed",
    "presentation_http_contract_not_versioned",
    "presentation_consumer_registration_activation_unauthorized",
    "presentation_mount_unauthorized",
    "current_switch_unauthorized",
)


def expected_presentation_consumer_implementation_sha256_v2() -> dict[str, str]:
    return dict(_EXPECTED_IMPLEMENTATION_SHA256)


def _manifest_exact(value: Any) -> bool:
    return type(value) is dict and strict_json_contract_equal(
        value, _EXPECTED_IMPLEMENTATION_SHA256
    )


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    manifest_exact = _manifest_exact(current_implementation_sha256)
    blockers = list(_BLOCKERS)
    if not manifest_exact:
        blockers.insert(0, "implementation_manifest_mismatch")

    artifacts = [
        {
            "artifact_id": artifact_id,
            "path": _ARTIFACT_PATHS[artifact_id],
            "role": _ARTIFACT_ROLES[artifact_id],
            "expected_sha256": expected_sha256,
        }
        for artifact_id, expected_sha256 in sorted(
            _EXPECTED_IMPLEMENTATION_SHA256.items()
        )
    ]
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION if manifest_exact else "REGISTRATION_INPUT_INVALID_FAIL_CLOSED",
        "source": {
            "implementation_manifest_contract_verified": manifest_exact,
            "implementation_fingerprints_match": manifest_exact,
            "implementation_pin_count": len(_EXPECTED_IMPLEMENTATION_SHA256),
            "predecessor_pin_count": 1,
            "production_pin_count": 5,
            "verification_pin_count": 4,
            "expected_manifest_sha256": strict_canonical_hash(
                _EXPECTED_IMPLEMENTATION_SHA256
            ),
            "supplied_manifest_embedded": False,
            "artifact_files_read": False,
            "artifacts": artifacts,
        },
        "contract_pins": {
            "predecessor_registration_schema_version": registration_v1.SCHEMA_VERSION,
            "predecessor_registration_static_fingerprint": (
                registration_v1.STATIC_FINGERPRINT
            ),
            "predecessor_registration_implementation_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256["presentation_registration_v1"]
            ),
            "projection_schema_version": projection_v4.SCHEMA_VERSION,
            "projection_static_fingerprint": projection_v4.STATIC_FINGERPRINT,
            "projection_verification_schema_version": (
                projection_v4.VERIFICATION_SCHEMA_VERSION
            ),
            "projection_implementation_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_projection_v4"
            ],
            "projection_test_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "portfolio_risk_projection_v4_test"
            ],
            "strict_canonical_global_name": "HakimiStrictCanonicalJsonV1",
            "strict_canonical_javascript_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "strict_canonical_json_v1_js"
            ],
            "strict_canonical_usage_policy": (
                "UTF8_SHA256_PRIMITIVE_WITH_PROJECTION_V4_SCHEMA_AWARE_"
                "PYTHON_CANONICAL_ENCODER"
            ),
            "card_schema_version": (
                "portfolio-risk-weighted-diversification-card-v4"
            ),
            "card_static_fingerprint": (
                "20260823-weighted-diversification-card-v4-"
                "sealed-projection-lock-2"
            ),
            "card_global_name": (
                "HakimiPortfolioRiskWeightedDiversificationCardV4"
            ),
            "card_javascript_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "weighted_diversification_card_v4_js"
            ],
            "card_stylesheet_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "weighted_diversification_card_v4_css"
            ],
            "card_test_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "weighted_diversification_card_v4_test_js"
            ],
            "consumer_fixture_schema_version": (
                "portfolio-risk-weighted-diversification-presentation-"
                "consumer-fixture-v4"
            ),
            "consumer_fixture_static_fingerprint": (
                "20260823-weighted-diversification-consumer-fixture-v4-"
                "sealed-projection-lock-2"
            ),
            "consumer_fixture_global_name": (
                "HakimiPortfolioRiskWeightedDiversificationConsumerFixtureV4"
            ),
            "consumer_fixture_javascript_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256[
                    "weighted_diversification_consumer_fixture_v4_js"
                ]
            ),
            "consumer_fixture_test_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "weighted_diversification_consumer_fixture_v4_test_js"
            ],
            "cross_runtime_test_sha256": _EXPECTED_IMPLEMENTATION_SHA256[
                "weighted_diversification_cross_runtime_v4_test_py"
            ],
            "stage_order": list(STAGE_ORDER),
            "dependency_order": [
                "HakimiStrictCanonicalJsonV1",
                "HakimiPortfolioRiskWeightedDiversificationCardV4",
                "HakimiPortfolioRiskWeightedDiversificationConsumerFixtureV4",
            ],
            "composition_policy": (
                "EXACT_PROJECTION_V4_SEAL_TO_STRICT_CARD_V4_TO_DEEP_FROZEN_"
                "UNMOUNTED_DESCRIPTOR_V2"
            ),
            "implementation_identity_policy": (
                "EXTERNAL_MANIFEST_EXACT_NO_SELF_CERTIFICATION_V2"
            ),
            "mount_policy": "NO_DOM_TARGET_NO_SELECTOR_NO_MOUNT_API_V2",
            "permission_policy": "ALWAYS_UNAUTHORIZED_V2",
        },
        "consumer": {
            "consumer_id": "portfolio-risk-weighted-diversification-v4",
            "input_schema_version": projection_v4.SCHEMA_VERSION,
            "output_schema_version": (
                "portfolio-risk-weighted-diversification-presentation-"
                "consumer-fixture-v4"
            ),
            "stage_order": list(STAGE_ORDER),
            "registration_state": "CANDIDATE_ONLY",
            "execution_mode": "UNMOUNTED_RENDER_DESCRIPTOR_ONLY",
            "dom_target": None,
            "selector": None,
        },
        "blockers": blockers,
        "activation_order": [
            "BIND_AND_EXACTLY_VERIFY_PROJECTION_V4_EVIDENCE",
            "VERSION_AND_EXECUTE_FIXTURE_V4_SYNTHETIC_MATRIX_RECEIPT",
            "INDEPENDENTLY_BIND_FIXTURE_V4_EXECUTION_EVIDENCE",
            "INDEPENDENTLY_REVIEW_FIXTURE_V4_RENDER_DESCRIPTOR_AND_LOAD_ORDER",
            "AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW",
            "AUTHORIZE_BROWSER_VISUAL_REVIEW",
            "VERSION_PRESENTATION_HTTP_CONTRACT_BEFORE_MOUNT",
            "SEPARATELY_AUTHORIZE_PRESENTATION_CONSUMER_REGISTRATION",
            "SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT",
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        ],
        "facts": {
            "registration_candidate_built": manifest_exact,
            "registration_activated": False,
            "predecessor_registration_preserved": manifest_exact,
            "projection_contract_pinned": manifest_exact,
            "strict_canonical_dependency_pinned": manifest_exact,
            "card_javascript_pinned": manifest_exact,
            "card_stylesheet_pinned": manifest_exact,
            "consumer_fixture_javascript_pinned": manifest_exact,
            "verification_artifacts_pinned": manifest_exact,
            "implementation_manifest_externally_attested": False,
            "projection_evidence_bound": False,
            "consumer_fixture_executed": False,
            "fixture_execution_receipt_versioned": False,
            "fixture_execution_evidence_bound": False,
            "render_descriptor_reviewed": False,
            "dependency_load_order_reviewed": False,
            "dom_contract_reviewed": False,
            "browser_visual_review_performed": False,
            "presentation_http_contract_versioned": False,
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
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
        current_implementation_sha256
    )
    exact = type(document) is dict and strict_json_contract_equal(document, expected)
    manifest_exact = bool(
        exact
        and expected["source"]["implementation_manifest_contract_verified"]
        is True
    )
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "registration_exactly_verified": exact,
        "implementation_manifest_exactly_verified": manifest_exact,
        "registration_status": expected.get("status") if exact else "UNKNOWN",
        "registration_activated": False,
        "blockers": [] if exact else ["registration_v2_exact_rebuild"],
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
    "STAGE_ORDER",
    "STATIC_FINGERPRINT",
    "STATUS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2",
    "expected_presentation_consumer_implementation_sha256_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2",
]
