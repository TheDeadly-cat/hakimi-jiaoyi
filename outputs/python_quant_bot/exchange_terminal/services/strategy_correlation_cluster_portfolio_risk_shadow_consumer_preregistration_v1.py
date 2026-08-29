from __future__ import annotations

import re
from typing import Any

from .portfolio_risk import PORTFOLIO_RISK_SCHEMA_VERSION
from .portfolio_shadow_risk import PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION
from .strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    ADAPTER_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1 import (
    DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_projection_v1 import (
    PROJECTION_SCHEMA_VERSION,
)
from .strategy_correlation_common_support_calendar_provider_composition_v1 import (
    SCHEMA_VERSION as CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION,
)
from .strategy_correlation_provider_dataset_content_attestation_v1 import (
    SCHEMA_VERSION as DATASET_CONTENT_ATTESTATION_SCHEMA_VERSION,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v1"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-shadow-preregistration-lock-1"

EXPECTED_IMPLEMENTATION_SHA256 = {
    "adapter_v1": "e3154743d7fb74a79d600b948f84c53a2a8666b13b0fc1cd00e9eca5590e8cee",
    "calendar_provider_composition_v1": (
        "922e626c72c3eb6be64a7a7d07ea0339655318eacac44a5121370cf8e11b1197"
    ),
    "dataset_content_attestation_v1": (
        "91dcad9660f379c47c2e912bda5032cbabc72dc5af8c42ece2ea3bede19bc654"
    ),
    "dual_source_receipt_v1": (
        "728f6230e00eddd40eca137d5c736d83537e516f7568d4bbc24dd90f8ae4f612"
    ),
    "legacy_portfolio_risk_v1": (
        "a97042a0265cc6bc552c8a818feadfd26e917b7eb75e36f9d4b8ca924717af19"
    ),
    "legacy_shadow_service_v1": (
        "c7e6010e8fa6eaa0e6b1ba081c80cced224a55100804aec57ac28376837a3111"
    ),
    "projection_v1": "46e45b030edd45d2b9f145924c6d673df4e59ab5c960c693236987b6dd1dd084",
    "risk_service": "6dc4ca89e61ae5907129f8307166a1ae84afd85b74924ee2b0f82106d7681244",
}
IMPLEMENTATION_PATHS = {
    "adapter_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_adapter_v1.py"
    ),
    "calendar_provider_composition_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_common_support_calendar_provider_composition_v1.py"
    ),
    "dataset_content_attestation_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_provider_dataset_content_attestation_v1.py"
    ),
    "dual_source_receipt_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1.py"
    ),
    "legacy_portfolio_risk_v1": "exchange_terminal/services/portfolio_risk.py",
    "legacy_shadow_service_v1": (
        "exchange_terminal/services/portfolio_shadow_risk.py"
    ),
    "projection_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_projection_v1.py"
    ),
    "risk_service": "exchange_terminal/services/risk_service.py",
}
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

FIXED_BLOCKERS = [
    "legacy_shadow_service_not_adapter_v1_aware",
    "legacy_matrix_derivation_binding_missing",
    "provider_dataset_key_control_unproven",
    "external_provider_data_issuance_unproven",
    "provider_replay_registry_unchecked",
    "native_cutoff_observation_manifest_missing",
    "shadow_freshness_policy_missing",
    "shadow_application_consumer_missing",
    "risk_service_adapter_contract_not_versioned",
    "independent_shadow_review_missing",
    "current_switch_unauthorized",
]

ACTIVATION_ORDER = [
    "BIND_LEGACY_MATRIX_TO_ATTESTED_COMPLETED_PRICE_INPUT",
    "BIND_AUTHENTICATED_PROVIDER_IDENTITY_AND_DATASET_KEY_CONTROL",
    "VERIFY_NATIVE_CUTOFF_OBSERVATION_MANIFEST",
    "PREREGISTER_SHADOW_FRESHNESS_AND_TIMEOUT_POLICY",
    "IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER",
    "INDEPENDENTLY_REVIEW_SYNTHETIC_SHADOW_CALLS",
    "VERSION_RISK_SERVICE_INPUT_CONTRACT",
    "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
]


def expected_shadow_consumer_implementation_sha256_v1() -> dict[str, str]:
    return dict(EXPECTED_IMPLEMENTATION_SHA256)


def _strict_manifest(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value) == set(EXPECTED_IMPLEMENTATION_SHA256)
        and all(
            type(key) is str
            and type(item) is str
            and _HASH_PATTERN.fullmatch(item) is not None
            for key, item in value.items()
        )
    )


def _research_authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    manifest_contract_ok = _strict_manifest(current_implementation_sha256)
    implementation_pins_match = bool(
        manifest_contract_ok
        and current_implementation_sha256 == EXPECTED_IMPLEMENTATION_SHA256
    )
    schema_pins_match = bool(
        PORTFOLIO_RISK_SCHEMA_VERSION == "portfolio-risk-budget-v1"
        and PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION == "portfolio-shadow-risk-v1"
        and ADAPTER_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-adapter-v1"
        and PROJECTION_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-public-projection-v1"
        and DUAL_SOURCE_RECEIPT_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-dual-source-receipt-v1"
        and DATASET_CONTENT_ATTESTATION_SCHEMA_VERSION
        == "strategy-correlation-provider-dataset-content-attestation-verification-v1"
        and CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION
        == "strategy-correlation-common-support-calendar-provider-composition-v1"
    )
    blockers = list(FIXED_BLOCKERS)
    if not manifest_contract_ok:
        blockers.insert(0, "implementation_manifest_contract_invalid")
    elif not implementation_pins_match:
        blockers.insert(0, "implementation_fingerprint_mismatch")
    if not schema_pins_match:
        blockers.insert(0, "upstream_schema_pin_mismatch")

    source_artifacts = [
        {
            "artifact_id": artifact_id,
            "path": IMPLEMENTATION_PATHS[artifact_id],
            "expected_sha256": EXPECTED_IMPLEMENTATION_SHA256[artifact_id],
        }
        for artifact_id in sorted(EXPECTED_IMPLEMENTATION_SHA256)
    ]
    document: dict[str, Any] = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": "PREREGISTERED_NOT_BOUND",
        "source": {
            "implementation_manifest_contract_verified": manifest_contract_ok,
            "implementation_fingerprints_match": implementation_pins_match,
            "upstream_schema_pins_match": schema_pins_match,
            "artifacts": source_artifacts,
        },
        "contract_pins": {
            "legacy_portfolio_risk_schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
            "legacy_shadow_schema_version": PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION,
            "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
            "projection_schema_version": PROJECTION_SCHEMA_VERSION,
            "dual_source_receipt_schema_version": DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
            "dataset_content_attestation_schema_version": (
                DATASET_CONTENT_ATTESTATION_SCHEMA_VERSION
            ),
            "calendar_provider_composition_schema_version": (
                CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION
            ),
        },
        "reuse_plan": [
            {
                "capability": "PROVIDER_IDENTITY_AND_KEY_LIFECYCLE",
                "decision": "REUSE_EXISTING_CONTRACTS",
            },
            {
                "capability": "DATASET_CONTENT_ATTESTATION",
                "decision": "REUSE_EXISTING_CONTRACT",
            },
            {
                "capability": "COMMON_SUPPORT_CALENDAR_PROVIDER_COMPOSITION",
                "decision": "REUSE_EXISTING_CONTRACT",
            },
            {
                "capability": "DUAL_CORRELATION_SOURCE_ALIGNMENT",
                "decision": "REUSE_ADR0168_PROVIDER_ASSERTION_ONLY",
            },
            {
                "capability": "LEGACY_MATRIX_DERIVATION_BINDING",
                "decision": "NEW_NARROW_ADAPTER_REQUIRED",
            },
            {
                "capability": "SHADOW_APPLICATION_CONSUMER",
                "decision": "NEW_VERSIONED_CONSUMER_REQUIRED",
            },
        ],
        "activation_order": list(ACTIVATION_ORDER),
        "blockers": blockers,
        "facts": {
            "legacy_shadow_accepts_dual_source_receipt": False,
            "legacy_shadow_accepts_complete_link_audit": False,
            "legacy_shadow_accepts_adapter_v1": False,
            "legacy_shadow_replaced": False,
            "provider_identity_stack_duplicated": False,
            "dataset_attestation_stack_duplicated": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "ui_mounted": False,
        },
        "authority": _research_authority(),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
    document: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
            current_implementation_sha256
        )
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["shadow_preregistration_exact_rebuild_mismatch"],
        "preregistration_status": expected["status"] if exact else "UNKNOWN",
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
    }


__all__ = [
    "PREREGISTRATION_SCHEMA_VERSION",
    "PREREGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "EXPECTED_IMPLEMENTATION_SHA256",
    "IMPLEMENTATION_PATHS",
    "FIXED_BLOCKERS",
    "ACTIVATION_ORDER",
    "expected_shadow_consumer_implementation_sha256_v1",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1",
]
