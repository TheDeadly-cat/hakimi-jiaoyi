from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1 as review_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1 as mount_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-mount-"
    "preregistration-v2"
)
STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-http-mount-preregistration-2"
)

SOURCE_V1_FILE_SHA256 = (
    "2c84f3997f5de7fb08b4c7936f84bdc4ca9d75fd6c1d22fa2bfa765d18e7d59c"
)
SOURCE_V1_ARTIFACT_HASH = (
    "52052a632112c83afd17d0b01572b33032bed5d32bb83fb4fbdf77dd95873c20"
)
CONSUMER_REVIEW_V1_FILE_SHA256 = (
    "0e2f2580c49a8332d6da07838ae1ef26294e6876e1cbfd5ea61976854422035f"
)
CONSUMER_REVIEW_V1_ARTIFACT_HASH = (
    "513b134d389a6391ec333d43db06a9cb8c7a05a3d3be81fc7dc1b3ae030a90c8"
)

MOUNT_BLOCKERS = (
    "AUTHENTICATION_MECHANISM_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_MIGRATION_EVIDENCE_PROVIDER_UNREGISTERED",
    "REQUEST_LOG_REDACTION_POLICY_UNREGISTERED",
    "ACTUAL_HTTP_TRANSPORT_REVIEW_REQUIRED",
    "FRONTEND_DOM_MOUNT_NOT_REGISTERED",
    "BROWSER_VISUAL_REVIEW_REQUIRED",
    "INDEPENDENT_MOUNT_REVIEW_REQUIRED",
    "ROUTE_NOT_REGISTERED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "consumer_review_promotion_allowed": False,
        "mount_allowed": False,
        "registration_allowed": False,
        "externally_callable": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verified_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    source = mount_v1.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()
    review = review_v1.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1()
    if (
        not mount_v1.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(
            source
        )
        or not review_v1.verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(
            review
        )
        or source.get("preregistration_hash") != SOURCE_V1_ARTIFACT_HASH
        or review.get("review_hash") != CONSUMER_REVIEW_V1_ARTIFACT_HASH
        or source.get("status") != "BLOCKED"
        or review.get("status") != "CANDIDATE_BOUND_NOT_MOUNTED"
    ):
        raise ValueError("mount_preregistration_v2_source_unverified")
    return source, review


def build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2() -> dict[str, Any]:
    source, review = _verified_sources()
    controls = deepcopy(source["unregistered_controls"])
    controls["consumer_binding_review"] = {
        "required": True,
        "completed": True,
        "review_schema_version": review["schema_version"],
        "review_static_fingerprint": review["static_fingerprint"],
        "review_hash": review["review_hash"],
        "static_scope_only": True,
        "frontend_mounted": False,
    }
    controls["actual_http_transport_review"] = {
        "required": True,
        "completed": False,
        "review_id": None,
        "service_started": False,
    }
    controls["frontend_dom_mount"] = {
        "required": True,
        "registered": False,
        "mount_id": None,
    }
    controls["browser_visual_review"] = {
        "required": True,
        "completed": False,
        "review_id": None,
        "browser_process_exercised": False,
    }

    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "predecessor": {
                "schema_version": source["schema_version"],
                "static_fingerprint": source["static_fingerprint"],
                "file_sha256": SOURCE_V1_FILE_SHA256,
                "artifact_hash": source["preregistration_hash"],
                "immutable": True,
            },
            "consumer_binding_review": {
                "schema_version": review["schema_version"],
                "static_fingerprint": review["static_fingerprint"],
                "file_sha256": CONSUMER_REVIEW_V1_FILE_SHA256,
                "artifact_hash": review["review_hash"],
                "status": review["status"],
                "static_review_complete": True,
                "mount_authority_granted": False,
            },
            "candidate": deepcopy(source["candidate"]),
            "public_projection": deepcopy(source["public_projection"]),
            "source_baseline_pins": deepcopy(source["source_baseline_pins"]),
            "proposed_transport": deepcopy(source["proposed_transport"]),
            "required_transport_controls": deepcopy(
                source["required_transport_controls"]
            ),
            "unregistered_controls": controls,
            "facts": {
                "policy_preregistered": True,
                "predecessor_verified": True,
                "predecessor_immutable": True,
                "consumer_binding_review_verified": True,
                "static_consumer_binding_review_complete": True,
                "actual_http_transport_review_complete": False,
                "frontend_dom_mount_registered": False,
                "browser_visual_review_complete": False,
                "trusted_migration_evidence_provider_available": False,
                "mount_controls_complete": False,
                "route_registered": False,
                "mount_allowed": False,
            },
            "authority": _authority(),
            "blockers": list(MOUNT_BLOCKERS),
        },
        "preregistration_hash",
    )


def verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2(
    document: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2()
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "CONSUMER_REVIEW_V1_ARTIFACT_HASH",
    "CONSUMER_REVIEW_V1_FILE_SHA256",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "SOURCE_V1_ARTIFACT_HASH",
    "SOURCE_V1_FILE_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2",
]
