"""Deterministic external-review request for the unmounted ADR0426 assets.

The request binds a review target and rubric.  It does not deliver the request,
authenticate a reviewer, accept a claim, complete a review, register a
consumer, modify host assets, or activate any runtime or trading authority.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "witness-storage-persistence-admission-presentation-external-review-request-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-storage-persistence-admission-presentation-external-"
    "review-request-v1-undelivered-lock-1"
)
SOURCE_PRESENTATION_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-persistence-admission-presentation-v1"
)
SOURCE_PRESENTATION_STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-persistence-admission-"
    "presentation-v1-unmounted-lock-1"
)
VIEW_MODEL_SCHEMA_VERSION = "witness-storage-persistence-admission-view-model-v1"
VIEW_MODEL_STATIC_FINGERPRINT = (
    "20260824-witness-storage-persistence-admission-view-model-v1-"
    "unmounted-lock-1"
)
EXPECTED_SOURCE_HASH_POLICY = "OUT_OF_BAND_EXACT_PRESENTATION_HASH_REQUIRED"
ORDERED_STAGES = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_REVIEW_ARTIFACT_HASHES = {
    "docs/adr/0426-witness-ownership-snapshot-storage-persistence-admission-presentation-v1.md": (
        "fdaae4133026fa8cdcc40aaba2a080c57a4dfdfbee7403e184f61eebe8c9b234"
    ),
    "exchange_terminal/application/witness_ownership_snapshot_storage_persistence_admission_presentation_v1.py": (
        "32ef091b5f5012feb7c7d7093fb57296ddf37051e3de601a4605dab6badd62d6"
    ),
    "exchange_terminal/services/strict_canonical_json_hash.py": (
        "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
    ),
    "exchange_terminal/static/strict_canonical_json_v1.js": (
        "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
    ),
    "exchange_terminal/static/witness_storage_persistence_admission_view_model_v1.js": (
        "81133bc3ba27e712083eba76346a4d6eba29b75585266cc92aec5ea319468e6a"
    ),
    "exchange_terminal/static/witness_storage_persistence_admission_view_model_v1.test.js": (
        "dc7772113087f37550208d49d410185657cd690e88dd997ab446403acc3d323d"
    ),
    "tests/test_witness_ownership_snapshot_storage_persistence_admission_presentation_v1.py": (
        "4ad93507ac770d4169fc10fc8f135192519a7eeaaa80474edb349eefd1ecb2f5"
    ),
}

_PROTECTED_HOST_PREIMAGES = {
    "exchange_terminal/static/app.js": (
        "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
    ),
    "exchange_terminal/static/evidence_presentation.js": (
        "9822b147c583d29fc7c6d4866d73a0015914e2971458239ab3d1d1c2ff39e409"
    ),
    "exchange_terminal/static/styles.css": (
        "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
    ),
}

REVIEW_RUBRIC_KEYS = frozenset(
    {
        "adr0425_exact_verification_and_hash_lineage",
        "bounded_hash_count_and_blocker_projection",
        "current_writer_paper_live_and_mount_authority_locked",
        "dom_network_runtime_and_storage_operations_absent",
        "out_of_band_expected_presentation_hash_required",
        "protected_host_preimages_unchanged_and_consumer_unmounted",
        "raw_documents_keys_signatures_and_locators_absent",
        "source_gap_maturity_permission_order_and_neutral_tone",
        "strict_shape_and_plain_json_input_limits",
        "unknown_and_resealed_promotion_fail_closed",
    }
)

_AUTHORITY_KEYS = (
    "asset_write_allowed",
    "browser_execution_allowed",
    "claim_intake_allowed",
    "consumer_preregistration_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "external_review_completion_allowed",
    "live_order_allowed",
    "paper_authorized",
    "review_request_delivery_allowed",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "writer_allowed",
)

_BLOCKERS = (
    "REVIEW_REQUEST_DELIVERY_NOT_AUTHORIZED",
    "REVIEWER_IDENTITY_UNAUTHENTICATED",
    "REVIEWER_PROCESS_UNAUTHENTICATED",
    "ATTESTATION_SIGNATURE_ABSENT",
    "REVIEW_REPLAY_DURABILITY_UNPROVEN",
    "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
    "CONSUMER_PREREGISTRATION_BLOCKED_PENDING_REVIEW",
)


def expected_review_artifact_hashes_v1() -> dict[str, str]:
    return dict(_REVIEW_ARTIFACT_HASHES)


def expected_protected_host_preimages_v1() -> dict[str, str]:
    return dict(_PROTECTED_HOST_PREIMAGES)


def _native_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) not in {dict, list}:
        raise TypeError("review requests require native strict JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic review requests are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_native_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("review request keys must be strings")
            snapshot[key] = _native_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _review_target() -> dict[str, Any]:
    return {
        "source_contract": {
            "presentation_schema_version": SOURCE_PRESENTATION_SCHEMA_VERSION,
            "presentation_static_fingerprint": (
                SOURCE_PRESENTATION_STATIC_FINGERPRINT
            ),
            "presentation_hash_field": "presentation_hash",
            "view_model_schema_version": VIEW_MODEL_SCHEMA_VERSION,
            "view_model_static_fingerprint": VIEW_MODEL_STATIC_FINGERPRINT,
            "view_model_hash_field": "view_model_hash",
            "expected_source_hash_policy": EXPECTED_SOURCE_HASH_POLICY,
            "ordered_stages": list(ORDERED_STAGES),
        },
        "review_artifact_sha256": expected_review_artifact_hashes_v1(),
        "protected_host_preimages": expected_protected_host_preimages_v1(),
        "declared_local_contract_baseline": {
            "evidence_kind": "PURE_SYNTHETIC_IN_MEMORY_NO_DOM",
            "python_projection_targeted_case_count": 9,
            "node_view_model_targeted_case_count": 13,
            "explicit_adr0413_adr0426_matrix_case_count": 239,
            "python_syntax_gate_declared": True,
            "node_syntax_gate_declared": True,
            "browser_visual_review_performed": False,
            "real_source_truth_verified": False,
            "external_persistence_verified": False,
        },
        "permission_baseline": {
            "review_request_delivered": False,
            "reviewer_authenticated": False,
            "external_independent_review_complete": False,
            "consumer_preregistered": False,
            "host_assets_modified": False,
            "route_registered": False,
            "dom_mounted": False,
            "current_activated": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }


def build_witness_storage_persistence_admission_presentation_external_review_request_v1() -> dict[str, Any]:
    target = _review_target()
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "AWAITING_EXTERNAL_INDEPENDENT_REVIEW",
        "request_state": (
            "EXACT_REVIEW_TARGET_BOUND_AWAITING_AUTHENTICATED_EXTERNAL_REVIEW"
        ),
        "review_target": target,
        "target_manifest_hash": strict_canonical_hash(target),
        "rubric": {
            key: "REVIEWER_MUST_ATTEST_TRUE" for key in sorted(REVIEW_RUBRIC_KEYS)
        },
        "facts": {
            "review_target_hashes_bound": True,
            "review_rubric_bound": True,
            "synthetic_contract_baseline_declared": True,
            "source_files_read_at_runtime": False,
            "raw_projection_document_embedded": False,
            "raw_view_model_document_embedded": False,
            "raw_key_or_signature_material_embedded": False,
            "review_request_delivered": False,
            "reviewer_identity_authenticated": False,
            "reviewer_process_authenticated": False,
            "attestation_signature_verified": False,
            "review_replay_durability_proven": False,
            "external_independent_review_complete": False,
            "consumer_preregistered": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "review_request_hash")


def verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _native_json_snapshot(document)
    except Exception:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_witness_storage_persistence_admission_presentation_external_review_request_v1(),
    )


__all__ = [
    "EXPECTED_SOURCE_HASH_POLICY",
    "ORDERED_STAGES",
    "REQUEST_SCHEMA_VERSION",
    "REVIEW_RUBRIC_KEYS",
    "SOURCE_PRESENTATION_SCHEMA_VERSION",
    "SOURCE_PRESENTATION_STATIC_FINGERPRINT",
    "STATIC_FINGERPRINT",
    "VIEW_MODEL_SCHEMA_VERSION",
    "VIEW_MODEL_STATIC_FINGERPRINT",
    "build_witness_storage_persistence_admission_presentation_external_review_request_v1",
    "expected_protected_host_preimages_v1",
    "expected_review_artifact_hashes_v1",
    "verify_witness_storage_persistence_admission_presentation_external_review_request_v1",
]
