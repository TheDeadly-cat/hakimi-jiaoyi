"""Static blocked registration for the projection/card/consumer-v5 chain."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v4"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v4-verification-v1"
)
STATIC_FINGERPRINT = "20260823-joint-evidence-frontend-registration-v4-lock-1"
STATUS = "BLOCKED"
DECISION = (
    "PROJECTION_V5_CARD_V5_CONSUMER_V5_PINNED_EXECUTION_RECEIPT_REVIEW_DOM_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)

REGISTRATION_V3_SHA256 = (
    "716218e403107b84e83aa33f37400b33c20dffc0668e55d6db8dca4832ef5b0a"
)
PROJECTION_V5_SHA256 = (
    "eadaec98c0b2882b28a6523779a02171afd39e7f5ed0caf0d581bfd81ee983c1"
)
PROJECTION_V5_TEST_SHA256 = (
    "7f1e03bcb648b39b57507401f8dc648c252b8eaf558e7cf1d1d407848ebb3ce3"
)
CARD_V5_JAVASCRIPT_SHA256 = (
    "8282b85316a2d238202d2a553af775f98be9f829ad86a49ab0463654bb9c358d"
)
CARD_V5_STYLESHEET_SHA256 = (
    "90ea35644b6d7fdc33f0bb1b1025ab37d6a876d10be00ec81e9b7a257552ed1a"
)
CARD_V5_TEST_SHA256 = (
    "871dbcc4c2ac6922a11d7f0b7f03af71e7890fa61d59e4803d4ec4e8aa71ca1e"
)
CONSUMER_V5_JAVASCRIPT_SHA256 = (
    "401a16ab303eec51e4a5d65f51e6ca4250f3bb1c281b8b07adb193ec89de8849"
)
CONSUMER_V5_TEST_SHA256 = (
    "88cbb42d5ebe3bfbdaa4f202c0a3c0d5de46d3acb043de0c49433b539050924b"
)
CROSS_RUNTIME_V5_TEST_SHA256 = (
    "7593f4a6b88b35d1588328f2aae2e7b48ee19478ddf0269e083140df05f78acb"
)
ADR_0217_SHA256 = (
    "9c2545c75654f98ff26291ef59314fc1fec5eae78f34eefb3dde0e1f47859bd4"
)
STRICT_CANONICAL_JAVASCRIPT_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
STRICT_CANONICAL_PYTHON_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_EXPECTED_MANIFEST = {
    "presentation_registration_v3": REGISTRATION_V3_SHA256,
    "portfolio_risk_projection_v5": PROJECTION_V5_SHA256,
    "portfolio_risk_projection_v5_test": PROJECTION_V5_TEST_SHA256,
    "strict_canonical_json_hash_py": STRICT_CANONICAL_PYTHON_SHA256,
    "strict_canonical_json_v1_js": STRICT_CANONICAL_JAVASCRIPT_SHA256,
    "joint_evidence_card_v5_js": CARD_V5_JAVASCRIPT_SHA256,
    "joint_evidence_card_v5_css": CARD_V5_STYLESHEET_SHA256,
    "joint_evidence_card_v5_test_js": CARD_V5_TEST_SHA256,
    "joint_evidence_consumer_v5_js": CONSUMER_V5_JAVASCRIPT_SHA256,
    "joint_evidence_consumer_v5_test_js": CONSUMER_V5_TEST_SHA256,
    "joint_evidence_cross_runtime_v5_test_py": CROSS_RUNTIME_V5_TEST_SHA256,
    "joint_evidence_frontend_v5_adr": ADR_0217_SHA256,
}
_ARTIFACTS = (
    ("presentation_registration_v3", "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3.py", "PREDECESSOR"),
    ("portfolio_risk_projection_v5", "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_projection_v5.py", "PRODUCTION"),
    ("portfolio_risk_projection_v5_test", "tests/test_strategy_correlation_cluster_portfolio_risk_projection_v5.py", "VERIFICATION"),
    ("strict_canonical_json_hash_py", "exchange_terminal/services/strict_canonical_json_hash.py", "PRODUCTION"),
    ("strict_canonical_json_v1_js", "exchange_terminal/static/strict_canonical_json_v1.js", "PRODUCTION"),
    ("joint_evidence_card_v5_js", "exchange_terminal/static/evidence_portfolio_risk_joint_evidence_card_v5.js", "PRODUCTION"),
    ("joint_evidence_card_v5_css", "exchange_terminal/static/evidence_portfolio_risk_joint_evidence_card_v5.css", "PRODUCTION"),
    ("joint_evidence_card_v5_test_js", "exchange_terminal/static/evidence_portfolio_risk_joint_evidence_card_v5.test.js", "VERIFICATION"),
    ("joint_evidence_consumer_v5_js", "exchange_terminal/static/evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js", "PRODUCTION"),
    ("joint_evidence_consumer_v5_test_js", "exchange_terminal/static/evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.test.js", "VERIFICATION"),
    ("joint_evidence_cross_runtime_v5_test_py", "tests/test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_cross_runtime_v5.py", "VERIFICATION"),
    ("joint_evidence_frontend_v5_adr", "docs/adr/0217-projection-v5-static-card-and-consumer-v5.md", "DECISION_RECORD"),
)
_BLOCKERS = (
    "implementation_manifest_external_attestation_not_bound",
    "candidate_v5_execution_evidence_not_independently_bound",
    "consumer_v5_execution_receipt_not_versioned",
    "consumer_v5_execution_evidence_not_independently_bound",
    "render_descriptor_and_load_order_independent_review_not_performed",
    "isolated_dom_contract_review_not_performed",
    "browser_visual_review_not_performed",
    "http_route_unregistered",
    "presentation_consumer_registration_activation_unauthorized",
    "presentation_mount_unauthorized",
    "current_switch_unauthorized",
)
_ACTIVATION_ORDER = (
    "BIND_EXTERNAL_IMPLEMENTATION_MANIFEST_ATTESTATION",
    "VERSION_CONSUMER_V5_EXECUTION_RECEIPT",
    "INDEPENDENTLY_BIND_CONSUMER_V5_EXECUTION_EVIDENCE",
    "INDEPENDENTLY_REVIEW_RENDER_DESCRIPTOR_AND_LOAD_ORDER",
    "AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW",
    "AUTHORIZE_BROWSER_VISUAL_REVIEW",
    "SEPARATELY_AUTHORIZE_HTTP_ROUTE",
    "SEPARATELY_AUTHORIZE_PRESENTATION_CONSUMER_REGISTRATION",
    "SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT",
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


def expected_presentation_consumer_implementation_sha256_v4() -> dict[str, str]:
    return deepcopy(_EXPECTED_MANIFEST)


def _artifact_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact_id": artifact_id,
            "path": path,
            "role": role,
            "expected_sha256": _EXPECTED_MANIFEST[artifact_id],
        }
        for artifact_id, path, role in _ARTIFACTS
    ]


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Build a sealed static registration without reading or executing artifacts."""

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
            "production_pin_count": 6,
            "verification_pin_count": 4,
            "decision_record_pin_count": 1,
            "expected_manifest_sha256": strict_canonical_hash(_EXPECTED_MANIFEST),
            "supplied_manifest_embedded": False,
            "artifact_files_read": False,
            "artifacts_executed": False,
            "artifacts": _artifact_rows(),
        },
        "contract_pins": {
            "predecessor_registration_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v3"
            ),
            "predecessor_registration_static_fingerprint": (
                "20260823-presentation-http-candidate-v5-registration-v3-lock-1"
            ),
            "predecessor_registration_implementation_sha256": REGISTRATION_V3_SHA256,
            "projection_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-projection-v5"
            ),
            "projection_static_fingerprint": (
                "20260823-http-candidate-v5-frontend-projection-lock-1"
            ),
            "projection_verification_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-projection-v5-verification-v1"
            ),
            "projection_implementation_sha256": PROJECTION_V5_SHA256,
            "projection_test_sha256": PROJECTION_V5_TEST_SHA256,
            "strict_canonical_global_name": "HakimiStrictCanonicalJsonV1",
            "strict_canonical_javascript_sha256": (
                STRICT_CANONICAL_JAVASCRIPT_SHA256
            ),
            "strict_canonical_python_sha256": STRICT_CANONICAL_PYTHON_SHA256,
            "card_schema_version": "portfolio-risk-joint-evidence-card-v5",
            "card_static_fingerprint": (
                "20260823-portfolio-risk-joint-evidence-card-v5-projection-lock-1"
            ),
            "card_global_name": "HakimiPortfolioRiskJointEvidenceCardV5",
            "card_javascript_sha256": CARD_V5_JAVASCRIPT_SHA256,
            "card_stylesheet_sha256": CARD_V5_STYLESHEET_SHA256,
            "card_test_sha256": CARD_V5_TEST_SHA256,
            "consumer_fixture_schema_version": (
                "portfolio-risk-joint-evidence-presentation-consumer-fixture-v5"
            ),
            "consumer_fixture_static_fingerprint": (
                "20260823-portfolio-risk-joint-evidence-consumer-v5-unmounted-lock-1"
            ),
            "consumer_fixture_global_name": (
                "HakimiPortfolioRiskJointEvidenceConsumerFixtureV5"
            ),
            "consumer_fixture_javascript_sha256": CONSUMER_V5_JAVASCRIPT_SHA256,
            "consumer_fixture_test_sha256": CONSUMER_V5_TEST_SHA256,
            "cross_runtime_test_sha256": CROSS_RUNTIME_V5_TEST_SHA256,
            "decision_record_sha256": ADR_0217_SHA256,
            "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
            "dependency_order": [
                "HakimiStrictCanonicalJsonV1",
                "HakimiPortfolioRiskJointEvidenceCardV5",
                "HakimiPortfolioRiskJointEvidenceConsumerFixtureV5",
            ],
            "composition_policy": (
                "EXACT_PROJECTION_V5_TO_SCHEMA_AWARE_CARD_V5_TO_SEALED_FROZEN_UNMOUNTED_DESCRIPTOR_V5"
            ),
            "implementation_identity_policy": (
                "EXTERNAL_MANIFEST_EXACT_NO_SELF_CERTIFICATION_V4"
            ),
            "mount_policy": "NO_ROUTE_NO_DOM_TARGET_NO_SELECTOR_NO_MOUNT_API_V4",
            "permission_policy": "ALWAYS_UNAUTHORIZED_V4",
        },
        "consumer": {
            "consumer_id": "portfolio-risk-joint-evidence-v5",
            "input_schema_version": (
                "strategy-correlation-cluster-portfolio-risk-projection-v5"
            ),
            "output_schema_version": (
                "portfolio-risk-joint-evidence-presentation-consumer-fixture-v5"
            ),
            "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
            "registration_state": "CANDIDATE_ONLY",
            "execution_mode": "UNMOUNTED_RENDER_DESCRIPTOR_ONLY",
            "dom_target": None,
            "selector": None,
        },
        "closed_local_blockers": (
            ["http_candidate_to_frontend_projection_v5_unversioned"]
            if manifest_exact
            else []
        ),
        "blockers": blockers,
        "activation_order": list(_ACTIVATION_ORDER),
        "facts": {
            "registration_candidate_built": True,
            "registration_activated": False,
            "predecessor_registration_preserved": manifest_exact,
            "projection_v5_contract_pinned": manifest_exact,
            "card_v5_javascript_pinned": manifest_exact,
            "card_v5_stylesheet_pinned": manifest_exact,
            "consumer_v5_javascript_pinned": manifest_exact,
            "verification_artifacts_pinned": manifest_exact,
            "http_candidate_to_frontend_projection_contract_versioned": manifest_exact,
            "static_cross_runtime_contract_versioned": manifest_exact,
            "implementation_manifest_externally_attested": False,
            "consumer_v5_execution_receipt_versioned": False,
            "consumer_v5_execution_evidence_independently_bound": False,
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


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
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
        "blockers": [] if passed else ["REGISTRATION_V4_OR_MANIFEST_NOT_EXACT"],
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
