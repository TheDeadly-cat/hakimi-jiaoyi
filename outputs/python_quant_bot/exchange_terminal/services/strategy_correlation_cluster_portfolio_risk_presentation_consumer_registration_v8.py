from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7 as registration_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v8"
)
STATIC_FINGERPRINT = (
    "20260823-anti-replay-gap-presentation-registration-v8-unmounted-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "REGISTRATION_V7_AND_ANTI_REPLAY_GAP_PRESENTATION_ASSETS_PINNED_"
    "EXTERNAL_IDENTITY_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)
REGISTRATION_V7_IMPLEMENTATION_SHA256 = (
    "23f1cf3fe1e8be3b3740d0b4d592a78f32f518b399e680d3cd79044a138956e2"
)

_EXPECTED_ASSETS = {
    "anti_replay_gap_card_v1_css": (
        "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad"
    ),
    "anti_replay_gap_card_v1_js": (
        "169898482300498c1c574439a949a8f3c373499cd2f68943ed13985d66f8f3b4"
    ),
    "anti_replay_gap_consumer_fixture_v1_js": (
        "51574be1838e8a7f47bcdc8a089f9d54e8f8763cac35823af52dbddcacff48dd"
    ),
    "anti_replay_gap_cross_runtime_test_v1_py": (
        "1b768e79e41c365884001bdda424ab4a2677334d37c8ec82985e8527a8496a1b"
    ),
    "anti_replay_gap_presentation_adr_0239": (
        "d99bc6e5aeabdf0847391f4481bd16e9bd67f1894a4517a846098133016cb405"
    ),
    "anti_replay_gap_presentation_test_v1_js": (
        "a0c0e5a77b01deb884c0cbdf6ae9797f38dd76932f82af5ad1bbadb80f7bc801"
    ),
    "anti_replay_gap_projection_v1_js": (
        "021a4618caf5968057b13dd744918bf059d2a756eb47fe4cc1a55b538de1ca7d"
    ),
}
_ASSET_ROLES = {
    "anti_replay_gap_card_v1_css": "production",
    "anti_replay_gap_card_v1_js": "production",
    "anti_replay_gap_consumer_fixture_v1_js": "production",
    "anti_replay_gap_cross_runtime_test_v1_py": "verification",
    "anti_replay_gap_presentation_adr_0239": "decision",
    "anti_replay_gap_presentation_test_v1_js": "verification",
    "anti_replay_gap_projection_v1_js": "production",
}
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "current_pointer_written",
    "formal_registration_activation_allowed",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_mount_allowed",
    "route_binding_allowed",
    "runtime_gate_activation_allowed",
    "writer_allowed",
)
_BLOCKERS = (
    "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
    "EXTERNAL_ADAPTER_CONFORMANCE_UNEXECUTED",
    "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
    "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
    "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
    "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
    "ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNBOUND",
)


def expected_presentation_asset_sha256_v8() -> dict[str, str]:
    return dict(_EXPECTED_ASSETS)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_asset_manifest(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("presentation asset manifest-v8 must be a mapping")
    supplied = dict(value)
    if supplied != _EXPECTED_ASSETS:
        raise ValueError("presentation asset manifest-v8 is not exact")
    return supplied


def _verify_predecessor(
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    result = registration_v7.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
        registration_v7_document,
        current_implementation_sha256,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    if result.get("status") != "PASS":
        raise ValueError("presentation consumer registration-v7 is not exact")
    return result


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8(
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    presentation_asset_sha256: Any,
) -> dict[str, Any]:
    predecessor = _verify_predecessor(
        registration_v7_document,
        current_implementation_sha256,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    assets = _validate_asset_manifest(presentation_asset_sha256)
    asset_rows = [
        {
            "artifact": name,
            "role": _ASSET_ROLES[name],
            "sha256": digest,
        }
        for name, digest in assets.items()
    ]
    return seal_strict_canonical_document(
        {
            "activation_order": [
                "STATIC_ASSET_PINNING",
                "REGISTRY_ORGANIZATION_IDENTITY",
                "EXTERNAL_ADAPTER_CONFORMANCE",
                "SIGNED_CONSUMPTION_RECEIPT_V1",
                "POST_REGISTRATION_RECEIPT_V5",
                "BROWSER_VISUAL_REVIEW",
                "ROUTE_AND_MOUNT_BINDING",
                "CURRENT_AND_RUNTIME_ACTIVATION",
            ],
            "authority": _locked_authority(),
            "blockers": list(_BLOCKERS),
            "closed_local_blockers": [
                "REGISTRATION_V7_EXACT",
                "ANTI_REPLAY_GAP_ASSET_MANIFEST_EXACT",
                "SCOPED_STYLESHEET_RESPONSIVE_REDUCED_MOTION_AND_FORCED_COLORS",
                "UNMOUNTED_CONSUMER_FIXTURE_EXACT",
            ],
            "consumer": {
                "card_schema_version": "anti-replay-registry-gap-card-v1",
                "fixture_schema_version": (
                    "anti-replay-registry-gap-presentation-consumer-fixture-v1"
                ),
                "fixture_status": "UNMOUNTED",
                "projection_schema_version": (
                    "anti-replay-registry-gap-projection-v1"
                ),
                "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
                "stylesheet_asset": (
                    "evidence_anti_replay_registry_gap_card_v1.css"
                ),
            },
            "contract_pins": {
                "predecessor_registration_schema_version": (
                    registration_v7.SCHEMA_VERSION
                ),
                "registration_v7_implementation_sha256": (
                    REGISTRATION_V7_IMPLEMENTATION_SHA256
                ),
            },
            "decision": DECISION,
            "facts": {
                "app_imported": False,
                "browser_visual_review_performed": False,
                "current_artifact_written": False,
                "external_adapter_conformance_verified": False,
                "external_linearizability_verified": False,
                "fixture_unmounted": True,
                "local_key_possession_source_bound": True,
                "paper_authorized": False,
                "post_registration_receipt_issued": False,
                "route_bound": False,
                "runtime_assets_accessed": False,
                "target_consumption_receipt_issued": False,
                "writer_allowed": False,
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "artifact_files_read": False,
                "artifacts": asset_rows,
                "artifacts_executed": False,
                "local_contract_complete": True,
                "predecessor_registration_v7_exact": True,
                "predecessor_registration_v7_hash": registration_v7_document[
                    "registration_hash"
                ],
                "predecessor_verification_status": predecessor["status"],
                "presentation_asset_manifest_sha256": strict_canonical_hash(
                    assets
                ),
                "presentation_asset_pin_count": len(assets),
                "static_source_only": True,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": STATUS,
        },
        "registration_hash",
    )


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8(
    document: Any,
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    presentation_asset_sha256: Any,
) -> dict[str, Any]:
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8(
            registration_v7_document,
            current_implementation_sha256,
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
            projection_v6_document,
            execution_preregistration_v1_document,
            presentation_asset_sha256,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "blockers": [] if exact else ["PRESENTATION_CONSUMER_REGISTRATION_V8_EXACT_REBUILD"],
        "browser_visual_review_performed": False,
        "current_admission_allowed": False,
        "fixture_status": "UNMOUNTED" if exact else "UNKNOWN",
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "registration_document_exactly_rebuilt": exact,
        "registration_hash": (
            expected["registration_hash"] if exact and expected is not None else None
        ),
        "registration_status": "BLOCKED" if exact else "UNKNOWN",
        "route_bound": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }
