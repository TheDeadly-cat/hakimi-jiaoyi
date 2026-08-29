"""Bind an undelivered external review request for ADR0348 and ADR0428.

This contract binds source hashes and a review rubric. It does not read files,
deliver a request, accept a claim, authenticate a reviewer, register assets,
execute a browser, mount UI, or grant operational or trading authority.
"""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-effective-budget-card-style-"
    "external-review-request-v1"
)
STATIC_FINGERPRINT = (
    "20260824-correlation-uncertainty-effective-budget-card-style-"
    "external-review-request-v1-undelivered-lock-1"
)
CARD_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-effective-budget-"
    "neutral-card-v1"
)
CARD_STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-effective-budget-"
    "neutral-card-v1-unmounted-semantic-lock-1"
)
STYLE_NAMESPACE = "hakimi-uncertainty-budget-card-v1"
STYLE_FILENAME = (
    "strategy_correlation_uncertainty_multi_window_effective_budget_"
    "neutral_card_v1.css"
)
ORDERED_STAGES = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_REVIEW_ARTIFACT_HASHES = {
    "docs/adr/0348-correlation-uncertainty-multi-window-effective-budget-neutral-card-v1.md": (
        "e97baac2fa7d3bf9b071fa2ffe656589884a58de62c696ccf4896e80031f6b9c"
    ),
    "docs/adr/0428-correlation-uncertainty-multi-window-effective-budget-neutral-card-style-candidate-v1.md": (
        "0588f903efbc54b5e336c20edc254267692d3b1401e3ad95b44028c47bef7695"
    ),
    "exchange_terminal/static/strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.css": (
        "25990e410ff6bbe2a1ad0f295149ffb24cbddf7b37abc5dd334e5deeb2900c1e"
    ),
    "exchange_terminal/static/strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.js": (
        "ff6df4552dd735483325ccde8f146f161228d3963685848b5f2905d5fdf59354"
    ),
    "exchange_terminal/static/strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.test.js": (
        "3acf29a3cd1385ef255a444750d98b79b9044f38860f83276f88c3c45e512eb8"
    ),
    "exchange_terminal/static/strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_style_v1.test.js": (
        "280416407c4ca29c22446d6f7a767d0eed172568aaacfac8275c20eacefd8d23"
    ),
    "exchange_terminal/static/strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js": (
        "70cdc9a565e2b57be7c7c8c4da474df6a308aead2880419e3da344838ac0b65a"
    ),
    "exchange_terminal/static/strict_canonical_json_v1.js": (
        "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
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
        "card_and_stylesheet_hash_pair_exact",
        "css_namespace_and_host_scope_isolation_exact",
        "desktop_container_and_narrow_layout_intent_coherent",
        "external_fonts_images_urls_and_executable_css_absent",
        "forced_colors_contrast_print_and_reduced_motion_fallbacks_coherent",
        "open_gaps_and_permission_lock_visually_distinct",
        "protected_host_preimages_unchanged_and_assets_unmounted",
        "raw_source_payload_and_sensitive_locator_disclosure_absent",
        "source_gap_maturity_permission_order_and_text_cues_preserved",
        "upstream_sealed_presentation_and_card_validation_exact",
        "visual_copy_neutral_and_non_directional",
    }
)

_BLOCKERS = (
    "REVIEW_REQUEST_DELIVERY_NOT_AUTHORIZED",
    "REVIEWER_IDENTITY_UNAUTHENTICATED",
    "REVIEWER_PROCESS_UNAUTHENTICATED",
    "ATTESTATION_SIGNATURE_ABSENT",
    "REVIEW_REPLAY_DURABILITY_UNPROVEN",
    "EXTERNAL_STYLE_REVIEW_NOT_COMPLETED",
    "ASSET_PAIR_PREREGISTRATION_BLOCKED_PENDING_REVIEW",
    "BROWSER_REVIEW_NOT_AUTHORIZED",
    "HOST_MOUNT_NOT_AUTHORIZED",
)

_AUTHORITY_KEYS = (
    "asset_pair_preregistration_allowed",
    "asset_write_allowed",
    "browser_execution_allowed",
    "claim_intake_allowed",
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
        "asset_pair_contract": {
            "card_schema_version": CARD_SCHEMA_VERSION,
            "card_static_fingerprint": CARD_STATIC_FINGERPRINT,
            "card_hash_field": "presentation_hash",
            "style_filename": STYLE_FILENAME,
            "style_namespace": STYLE_NAMESPACE,
            "ordered_stages": list(ORDERED_STAGES),
            "pair_state": "UNMOUNTED_REVIEW_TARGET_ONLY",
        },
        "review_artifact_sha256": expected_review_artifact_hashes_v1(),
        "protected_host_preimages": expected_protected_host_preimages_v1(),
        "declared_local_contract_baseline": {
            "evidence_kind": "PURE_STATIC_AND_SYNTHETIC_NO_BROWSER",
            "card_contract_case_count": 14,
            "style_contract_case_count": 13,
            "combined_case_count": 27,
            "node_syntax_gate_declared": True,
            "browser_visual_review_performed": False,
            "screen_reader_review_performed": False,
            "native_zoom_review_performed": False,
            "real_market_source_verified": False,
        },
        "style_characteristics": {
            "namespace_scoped": True,
            "global_host_selectors_absent": True,
            "external_resources_absent": True,
            "finite_motion_only": True,
            "reduced_motion_fallback_declared": True,
            "forced_colors_fallback_declared": True,
            "increased_contrast_fallback_declared": True,
            "print_fallback_declared": True,
            "responsive_container_rules_declared": True,
            "text_state_cues_preserved": True,
        },
        "permission_baseline": {
            "review_request_delivered": False,
            "reviewer_authenticated": False,
            "external_style_review_complete": False,
            "asset_pair_preregistered": False,
            "host_assets_modified": False,
            "route_registered": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }


def build_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1() -> dict[str, Any]:
    target = _review_target()
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "AWAITING_EXTERNAL_INDEPENDENT_STYLE_REVIEW",
        "request_state": (
            "EXACT_CARD_STYLE_TARGET_BOUND_AWAITING_AUTHENTICATED_EXTERNAL_REVIEW"
        ),
        "review_target": target,
        "target_manifest_hash": strict_canonical_hash(target),
        "rubric": {
            key: "REVIEWER_MUST_ATTEST_TRUE" for key in sorted(REVIEW_RUBRIC_KEYS)
        },
        "facts": {
            "review_target_hashes_bound": True,
            "review_rubric_bound": True,
            "static_contract_baseline_declared": True,
            "source_files_read_at_runtime": False,
            "raw_markup_embedded": False,
            "raw_stylesheet_embedded": False,
            "raw_source_projection_embedded": False,
            "review_request_delivered": False,
            "reviewer_identity_authenticated": False,
            "reviewer_process_authenticated": False,
            "attestation_signature_verified": False,
            "review_replay_durability_proven": False,
            "external_style_review_complete": False,
            "asset_pair_preregistered": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "review_request_hash")


def verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _native_json_snapshot(document)
    except Exception:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(),
    )


__all__ = [
    "CARD_SCHEMA_VERSION",
    "CARD_STATIC_FINGERPRINT",
    "ORDERED_STAGES",
    "REQUEST_SCHEMA_VERSION",
    "REVIEW_RUBRIC_KEYS",
    "STATIC_FINGERPRINT",
    "STYLE_FILENAME",
    "STYLE_NAMESPACE",
    "build_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1",
    "expected_protected_host_preimages_v1",
    "expected_review_artifact_hashes_v1",
    "verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1",
]
