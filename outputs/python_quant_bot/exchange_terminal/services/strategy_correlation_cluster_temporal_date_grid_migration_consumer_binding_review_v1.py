from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REVIEW_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-consumer-binding-"
    "review-v1"
)
STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-consumer-binding-review-1"
)

HTTP_CANDIDATE_SHA256 = (
    "2acd18017a1d3e7cd6afce5102f6391b6b63ac3824ba0214e807679f543681e4"
)
PUBLIC_PROJECTION_SHA256 = (
    "4f6df866f6923fe175e41e6f260539c8921d76b13db2232ebcd28b70d32c7f02"
)
MOUNT_PREREGISTRATION_SHA256 = (
    "2c84f3997f5de7fb08b4c7936f84bdc4ca9d75fd6c1d22fa2bfa765d18e7d59c"
)
LOCKBOARD_SHA256 = (
    "becc07c17f68786c92e698d3ba594e24f395856130edd67f1978080a64b6b0bc"
)
HTTP_BINDING_SHA256 = (
    "6b3b41c657ed02a127fdf333e2d9e09654de70cf19ea2a6af61222dc0c8f6892"
)
NODE_BINDING_TEST_SHA256 = (
    "1ccf6af5ca00818d14a4e41d3ee7148ea1ad8d2fded8bab58d6bd04c83c91889"
)
PRESENTATION_SUITE_V15_SHA256 = (
    "dfa72af7eca749078ff701c222675c35568e9ee6baedf4c9e5571207614b3d36"
)
PYTHON_CROSS_RUNTIME_TEST_SHA256 = (
    "8ea7b156415b0708e08802a116ec63dbb1dcc178df18f1c66b62de4354f2f57d"
)

HTTP_CANDIDATE_RESPONSE_SCHEMA = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-"
    "response-v1"
)
HTTP_CANDIDATE_STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-http-candidate-1"
)
PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1"
)
PUBLIC_SUMMARY_STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-projection-lock-1"
)
MOUNT_PREREGISTRATION_SCHEMA = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-mount-"
    "preregistration-v1"
)
MOUNT_PREREGISTRATION_STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-http-mount-preregistration-1"
)

REVIEW_BLOCKERS = (
    "ACTUAL_HTTP_TRANSPORT_NOT_EXERCISED",
    "FRONTEND_DOM_MOUNT_NOT_REGISTERED",
    "BROWSER_VISUAL_REVIEW_NOT_COMPLETED",
    "TRUSTED_MIGRATION_EVIDENCE_PROVIDER_UNREGISTERED",
    "MOUNT_PREREGISTRATION_V1_REMAINS_BLOCKED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "review_promotion_allowed": False,
        "mount_allowed": False,
        "route_registration_allowed": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "CANDIDATE_BOUND_NOT_MOUNTED",
            "source_contract_pins": {
                "http_candidate": {
                    "schema_version": HTTP_CANDIDATE_RESPONSE_SCHEMA,
                    "static_fingerprint": HTTP_CANDIDATE_STATIC_FINGERPRINT,
                    "sha256": HTTP_CANDIDATE_SHA256,
                },
                "public_projection": {
                    "schema_version": PUBLIC_SUMMARY_SCHEMA,
                    "static_fingerprint": PUBLIC_SUMMARY_STATIC_FINGERPRINT,
                    "sha256": PUBLIC_PROJECTION_SHA256,
                },
                "mount_preregistration_v1": {
                    "schema_version": MOUNT_PREREGISTRATION_SCHEMA,
                    "static_fingerprint": (
                        MOUNT_PREREGISTRATION_STATIC_FINGERPRINT
                    ),
                    "sha256": MOUNT_PREREGISTRATION_SHA256,
                },
                "node_lockboard": {"sha256": LOCKBOARD_SHA256},
                "node_http_binding": {"sha256": HTTP_BINDING_SHA256},
            },
            "executable_evidence_pins": {
                "node_binding_test_sha256": NODE_BINDING_TEST_SHA256,
                "presentation_suite_v15_sha256": PRESENTATION_SUITE_V15_SHA256,
                "python_cross_runtime_test_sha256": (
                    PYTHON_CROSS_RUNTIME_TEST_SHA256
                ),
                "test_execution_results_embedded": False,
                "historical_test_totals_embedded": False,
            },
            "binding_contract": {
                "input_response_schema": HTTP_CANDIDATE_RESPONSE_SCHEMA,
                "payload_schema": PUBLIC_SUMMARY_SCHEMA,
                "canonical_hash_contract": (
                    "SHA256_UTF8_SORTED_KEYS_COMPACT_JSON"
                ),
                "axis_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
                "state_matrix": [
                    "NOT_SUPPLIED",
                    "UNKNOWN",
                    "PLAN_LISTED",
                    "DRY_RUN_REPORT22_PASS",
                    "DRY_RUN_REPORT22_BLOCK",
                ],
                "commonjs_contract_available": True,
                "browser_global_vm_contract_available": True,
                "verified_payload_only": True,
                "invalid_response_fallback": "UNKNOWN",
            },
            "review": {
                "static_consumer_binding_review_complete": True,
                "response_hash_recomputation_required": True,
                "exact_response_shape_required": True,
                "payload_state_consistency_required": True,
                "authority_reseal_rejected": True,
                "actual_http_transport_review_complete": False,
                "frontend_dom_mount_review_complete": False,
                "browser_visual_review_complete": False,
                "runtime_asset_review_complete": False,
            },
            "facts": {
                "source_hashes_pinned": True,
                "executable_evidence_sources_pinned": True,
                "cross_runtime_contract_available": True,
                "actual_http_transport_exercised": False,
                "frontend_dom_mounted": False,
                "browser_process_exercised": False,
                "runtime_assets_accessed": False,
                "route_registered": False,
                "mount_preregistration_v1_blocked": True,
            },
            "authority": _authority(),
            "blockers": list(REVIEW_BLOCKERS),
        },
        "review_hash",
    )


def verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(
    document: Any,
) -> bool:
    if type(document) is not dict:
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(),
    )


__all__ = [
    "HTTP_BINDING_SHA256",
    "HTTP_CANDIDATE_SHA256",
    "LOCKBOARD_SHA256",
    "MOUNT_PREREGISTRATION_SHA256",
    "NODE_BINDING_TEST_SHA256",
    "PRESENTATION_SUITE_V15_SHA256",
    "PUBLIC_PROJECTION_SHA256",
    "PYTHON_CROSS_RUNTIME_TEST_SHA256",
    "REVIEW_BLOCKERS",
    "REVIEW_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1",
]
