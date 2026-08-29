from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8
    as registration_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-consumer-"
    "registration-candidate-v9"
)
STATIC_FINGERPRINT = (
    "20260823-registry-identity-gap-presentation-registration-v9-"
    "unmounted-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
DECISION = (
    "REGISTRATION_V8_AND_REGISTRY_IDENTITY_GAP_PRESENTATION_V2_ASSETS_"
    "PINNED_SOURCE_TRUST_BROWSER_ROUTE_MOUNT_AND_ACTIVATION_UNBOUND"
)
REGISTRATION_V8_IMPLEMENTATION_SHA256 = (
    "7d20b84dd84c7afd228fddedc4510bfb022889b4e488d58ff1e2026f2f1fbe47"
)
REUSED_V1_STYLESHEET_SHA256 = (
    "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad"
)

_EXPECTED_ASSETS = {
    "anti_replay_gap_card_v2_js": (
        "39d7c985a95f9247adb9fb72d745b275ed717c5e850cf618dc52f8b37e67443b"
    ),
    "anti_replay_gap_consumer_fixture_v2_js": (
        "c23a91d96a81fa44cccd85d56e4e9e4610310532643ffe41b5e3762fa7aed50a"
    ),
    "anti_replay_gap_cross_runtime_test_v2_py": (
        "990dc0d0b0c4b41c03a6bbcfe66b7ac33a548e5dc57af4fd1a94e1a15b27a6ed"
    ),
    "anti_replay_gap_presentation_adr_0246": (
        "072fb342bd02f7b99ae4052b23194d9ae3fa92ed3f23663463499d646bc16d2e"
    ),
    "anti_replay_gap_presentation_test_v2_js": (
        "b9e32fecd5e908c200b5acbf84687e2b8d4b23713dba737a572d423de8a7831c"
    ),
    "anti_replay_gap_projection_v2_js": (
        "ab755cd4579dc5bc7855c54f4625862e9ff3203179303057a23d80f613ab2677"
    ),
}
_ASSET_ROLES = {
    "anti_replay_gap_card_v2_js": "production",
    "anti_replay_gap_consumer_fixture_v2_js": "production",
    "anti_replay_gap_cross_runtime_test_v2_py": "verification",
    "anti_replay_gap_presentation_adr_0246": "decision",
    "anti_replay_gap_presentation_test_v2_js": "verification",
    "anti_replay_gap_projection_v2_js": "production",
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
    "PYTHON_PROCESS_AUTHENTICATION_UNVERIFIED",
    "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
    "SIGNER_ROLE_IDENTITY_UNVERIFIED",
    "EXTERNAL_SOURCE_TRUST_UNPROVEN",
    "REVOCATION_CONTENT_UNVERIFIED",
    "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
    "EXTERNAL_ADAPTER_CONFORMANCE_UNEXECUTED",
    "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
    "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
    "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
    "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
    "ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNBOUND",
)


def expected_presentation_asset_sha256_v9() -> dict[str, str]:
    return dict(_EXPECTED_ASSETS)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_asset_manifest(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("presentation asset manifest-v9 must be a mapping")
    supplied = dict(value)
    if supplied != _EXPECTED_ASSETS:
        raise ValueError("presentation asset manifest-v9 is not exact")
    return supplied


def _verify_predecessor(
    registration_v8_document: Any,
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    presentation_asset_sha256_v8: Any,
) -> dict[str, Any]:
    result = registration_v8.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8(
        registration_v8_document,
        registration_v7_document,
        current_implementation_sha256,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
        presentation_asset_sha256_v8,
    )
    if result.get("status") != "PASS":
        raise ValueError("presentation consumer registration-v8 is not exact")
    return result


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
    registration_v8_document: Any,
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    presentation_asset_sha256_v8: Any,
    presentation_asset_sha256_v9: Any,
) -> dict[str, Any]:
    predecessor = _verify_predecessor(
        registration_v8_document,
        registration_v7_document,
        current_implementation_sha256,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
        presentation_asset_sha256_v8,
    )
    assets = _validate_asset_manifest(presentation_asset_sha256_v9)
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
                "REGISTRATION_V8_EXACT",
                "PRESENTATION_V2_STATIC_ASSET_PINNING",
                "SIGNER_ROLE_AND_EXTERNAL_SOURCE_TRUST",
                "EVIDENCE_PAYLOAD_SEMANTIC_VALIDATION",
                "PYTHON_PROCESS_AUTHENTICATION",
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
                "REGISTRATION_V8_EXACT",
                "PRESENTATION_V2_ASSET_MANIFEST_EXACT",
                "PRESENTATION_V2_STAGE_ORDER_EXACT",
                "PRESENTATION_V2_IDENTITY_LEDGER_NEUTRAL",
                "PRESENTATION_V2_UNMOUNTED_FIXTURE_EXACT",
                "PRESENTATION_V1_STYLESHEET_REUSED_UNCHANGED",
                "SIX_ARTIFACT_LOCAL_CRYPTOGRAPHIC_SOURCE_BOUND",
            ],
            "consumer": {
                "card_schema_version": "anti-replay-registry-gap-card-v2",
                "fixture_schema_version": (
                    "anti-replay-registry-gap-presentation-consumer-fixture-v2"
                ),
                "fixture_status": "UNMOUNTED",
                "identity_evidence_local_observation_count": 2,
                "identity_evidence_unverified_count": 6,
                "predecessor_card_schema_version": (
                    "anti-replay-registry-gap-card-v1"
                ),
                "projection_schema_version": (
                    "anti-replay-registry-gap-projection-v2"
                ),
                "stage_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
                "stylesheet_asset": (
                    "evidence_anti_replay_registry_gap_card_v1.css"
                ),
                "stylesheet_reused_without_modification": True,
            },
            "contract_pins": {
                "predecessor_registration_schema_version": (
                    registration_v8.SCHEMA_VERSION
                ),
                "registration_v8_implementation_sha256": (
                    REGISTRATION_V8_IMPLEMENTATION_SHA256
                ),
                "reused_v1_stylesheet_sha256": REUSED_V1_STYLESHEET_SHA256,
            },
            "decision": DECISION,
            "facts": {
                "app_imported": False,
                "browser_visual_review_performed": False,
                "current_artifact_written": False,
                "evidence_payload_semantics_verified": False,
                "external_adapter_conformance_verified": False,
                "external_linearizability_verified": False,
                "external_source_trust_verified": False,
                "fixture_unmounted": True,
                "local_key_possession_source_bound": True,
                "paper_authorized": False,
                "python_process_authenticated": False,
                "registry_organization_identity_verified": False,
                "revocation_content_verified": False,
                "route_bound": False,
                "runtime_assets_accessed": False,
                "signer_role_identity_verified": False,
                "six_artifact_cryptographic_source_bound": True,
                "target_consumption_receipt_issued": False,
                "writer_allowed": False,
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "artifact_files_read": False,
                "artifacts": asset_rows,
                "artifacts_executed": False,
                "local_contract_complete": True,
                "predecessor_registration_v8_exact": True,
                "predecessor_registration_v8_hash": registration_v8_document[
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


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
    document: Any,
    registration_v8_document: Any,
    registration_v7_document: Any,
    current_implementation_sha256: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    presentation_asset_sha256_v8: Any,
    presentation_asset_sha256_v9: Any,
) -> dict[str, Any]:
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            registration_v8_document,
            registration_v7_document,
            current_implementation_sha256,
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
            projection_v6_document,
            execution_preregistration_v1_document,
            presentation_asset_sha256_v8,
            presentation_asset_sha256_v9,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "blockers": (
            []
            if exact
            else ["PRESENTATION_CONSUMER_REGISTRATION_V9_EXACT_REBUILD"]
        ),
        "browser_visual_review_performed": False,
        "current_admission_allowed": False,
        "fixture_status": "UNMOUNTED" if exact else "UNKNOWN",
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "registration_document_exactly_rebuilt": exact,
        "registration_hash": (
            expected["registration_hash"]
            if exact and expected is not None
            else None
        ),
        "registration_status": "BLOCKED" if exact else "UNKNOWN",
        "registry_identity_admission_allowed": False,
        "route_bound": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }
