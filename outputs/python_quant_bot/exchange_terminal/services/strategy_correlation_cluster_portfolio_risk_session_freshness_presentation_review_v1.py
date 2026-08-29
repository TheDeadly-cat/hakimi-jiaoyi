from __future__ import annotations

from typing import Any

from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REVIEW_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-presentation-review-v1"
)
STATIC_FINGERPRINT = "20260822-session-lag-ledger-consumer-review-1"

SESSION_FRESHNESS_EVALUATION_SHA256 = (
    "2bacefd4b3649ccbba8e254a0e8f8c176d08e458744f74dc19145fb6d5363299"
)
PUBLIC_PROJECTION_SHA256 = (
    "bbdf5d7734901c547c4508177f67b819c5b2f1f2c3e2319912e97ff5e81b34c1"
)
CARD_JAVASCRIPT_SHA256 = (
    "85eef197936cc3c77482bab62b3c981a41b44069940296f77e595b9a8e371a44"
)
CARD_STYLESHEET_SHA256 = (
    "d61ab32f6f243dfe8dffba2eb8ad7370caf71838a76c568798c37094e79b69bc"
)
APP_JAVASCRIPT_SHA256 = (
    "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
)
INDEX_HTML_SHA256 = (
    "553b33b0c4ef4ffb3e2f49d6671fe011f687696b95a7f5ff069f51f57bd5cd13"
)

SESSION_FRESHNESS_TEST_SHA256 = (
    "1e350e0d011814eee226a9b440e2c728336424b173c9ba6bb8f32af444107618"
)
PYTHON_CROSS_RUNTIME_TEST_SHA256 = (
    "e205ee531a813fe583a271b3de26fca9d430eb39117ec3269c72424f8241703b"
)
NODE_CARD_TEST_SHA256 = (
    "44e91e2cedff2f6a2c8e9992b29dadbe1a7fc52f1af2732fa6ae33a5160532d6"
)
PRESENTATION_SUITE_V17_SHA256 = (
    "68f94c9ff8e6247fe7ac46ea1b1f1cb7e132d736053b11426cfda8fdc4060421"
)

SESSION_FRESHNESS_EVALUATION_SCHEMA = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-evaluation-v1"
)
SESSION_FRESHNESS_STATIC_FINGERPRINT = (
    "20260822-completed-session-lag-freshness-1"
)
PUBLIC_PROJECTION_SCHEMA = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-public-projection-v1"
)
PUBLIC_PROJECTION_STATIC_FINGERPRINT = (
    "20260822-session-lag-ledger-projection-lock-1"
)

REVIEW_BLOCKERS = (
    "EXTERNAL_TIME_AUTHORITY_UNAUTHENTICATED",
    "SHADOW_CONSUMER_NOT_BOUND",
    "ACTUAL_HTTP_TRANSPORT_NOT_DEFINED_OR_EXERCISED",
    "FRONTEND_DOM_MOUNT_NOT_REGISTERED",
    "BROWSER_VISUAL_REVIEW_NOT_COMPLETED",
    "INDEPENDENT_REVIEW_NOT_COMPLETED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "review_promotion_allowed": False,
        "mount_allowed": False,
        "route_registration_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1() -> dict[str, Any]:
    document = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE_BOUND_NOT_MOUNTED",
        "source_contract_pins": {
            "session_freshness_evaluation": {
                "schema_version": SESSION_FRESHNESS_EVALUATION_SCHEMA,
                "static_fingerprint": SESSION_FRESHNESS_STATIC_FINGERPRINT,
                "sha256": SESSION_FRESHNESS_EVALUATION_SHA256,
            },
            "public_projection": {
                "schema_version": PUBLIC_PROJECTION_SCHEMA,
                "static_fingerprint": PUBLIC_PROJECTION_STATIC_FINGERPRINT,
                "sha256": PUBLIC_PROJECTION_SHA256,
            },
            "browser_card": {
                "payload_schema_version": PUBLIC_PROJECTION_SCHEMA,
                "static_fingerprint": PUBLIC_PROJECTION_STATIC_FINGERPRINT,
                "javascript_sha256": CARD_JAVASCRIPT_SHA256,
                "stylesheet_sha256": CARD_STYLESHEET_SHA256,
            },
            "reviewed_frontend_mount_sources": {
                "app_javascript_sha256": APP_JAVASCRIPT_SHA256,
                "index_html_sha256": INDEX_HTML_SHA256,
            },
        },
        "executable_evidence_pins": {
            "session_freshness_test_sha256": SESSION_FRESHNESS_TEST_SHA256,
            "python_cross_runtime_test_sha256": PYTHON_CROSS_RUNTIME_TEST_SHA256,
            "node_card_test_sha256": NODE_CARD_TEST_SHA256,
            "presentation_suite_v17_sha256": PRESENTATION_SUITE_V17_SHA256,
            "test_execution_results_embedded": False,
            "historical_test_totals_embedded": False,
        },
        "binding_contract": {
            "input_evaluation_schema": SESSION_FRESHNESS_EVALUATION_SCHEMA,
            "payload_schema": PUBLIC_PROJECTION_SCHEMA,
            "canonical_hash_contract": "SHA256_UTF8_SORTED_KEYS_COMPACT_JSON",
            "axis_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
            "state_matrix": [
                "NOT_SUPPLIED",
                "UNKNOWN",
                "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
                "SESSION_LAG_POLICY_GAP_PRESENT",
                "UNVERIFIED_FRESHNESS_EVIDENCE_GAP",
            ],
            "complete_source_hash_lineage_required": True,
            "commonjs_contract_available": True,
            "browser_global_vm_contract_available": True,
            "python_to_node_contract_available": True,
            "invalid_projection_fallback": "UNKNOWN",
            "permission_fallback": "UNAUTHORIZED",
        },
        "review": {
            "static_consumer_binding_review_complete": True,
            "python_projection_source_review_complete": True,
            "javascript_view_model_source_review_complete": True,
            "stylesheet_contract_source_review_complete": True,
            "frontend_mount_source_review_complete": True,
            "cross_runtime_test_definition_review_complete": True,
            "actual_http_transport_review_complete": False,
            "frontend_dom_mount_review_complete": False,
            "browser_visual_review_complete": False,
            "runtime_asset_review_complete": False,
            "independent_review_complete": False,
        },
        "facts": {
            "source_hashes_pinned": True,
            "executable_evidence_sources_pinned": True,
            "app_and_index_hashes_pinned": True,
            "cross_runtime_contract_available": True,
            "current_frontend_sources_do_not_mount_candidate": True,
            "actual_http_transport_exercised": False,
            "frontend_dom_mounted": False,
            "browser_process_exercised": False,
            "runtime_assets_accessed": False,
            "route_registered": False,
            "external_time_authority_authenticated": False,
            "freshness_externally_proven": False,
        },
        "authority": _authority(),
        "blockers": list(REVIEW_BLOCKERS),
    }
    return seal_strict_canonical_document(document, "review_hash")


def verify_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1(
    document: Any,
) -> bool:
    if type(document) is not dict:
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1(),
    )


__all__ = [
    "APP_JAVASCRIPT_SHA256",
    "CARD_JAVASCRIPT_SHA256",
    "CARD_STYLESHEET_SHA256",
    "INDEX_HTML_SHA256",
    "NODE_CARD_TEST_SHA256",
    "PRESENTATION_SUITE_V17_SHA256",
    "PUBLIC_PROJECTION_SHA256",
    "PYTHON_CROSS_RUNTIME_TEST_SHA256",
    "REVIEW_BLOCKERS",
    "REVIEW_SCHEMA_VERSION",
    "SESSION_FRESHNESS_EVALUATION_SHA256",
    "SESSION_FRESHNESS_TEST_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1",
]
