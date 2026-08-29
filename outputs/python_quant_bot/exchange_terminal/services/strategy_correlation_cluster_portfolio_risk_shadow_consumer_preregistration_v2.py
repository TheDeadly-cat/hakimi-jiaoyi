from __future__ import annotations

import re
from typing import Any

from .portfolio_shadow_risk import PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION
from .strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    ADAPTER_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1 import (
    DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 import (
    BINDING_SCHEMA_VERSION as LEGACY_MATRIX_BINDING_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 import (
    MANIFEST_SCHEMA_VERSION as NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION,
)
from .strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    EVALUATION_SCHEMA_VERSION as SESSION_FRESHNESS_EVALUATION_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as SESSION_FRESHNESS_REGISTRATION_SCHEMA_VERSION,
)
from . import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1
    as preregistration_v1_contract,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v2"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-shadow-preregistration-v2-lock-1"
V1_PREREGISTRATION_HASH = (
    "d722e9a04c840a75afcd84f90db29c16178040108cf1f686f02511c52b99206d"
)

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
    "legacy_matrix_derivation_binding_v1": (
        "144ec7b141dd96362c7f58bafd745243945b9afa2e0774ef7e95b03586235890"
    ),
    "legacy_portfolio_risk_v1": (
        "a97042a0265cc6bc552c8a818feadfd26e917b7eb75e36f9d4b8ca924717af19"
    ),
    "legacy_shadow_service_v1": (
        "c7e6010e8fa6eaa0e6b1ba081c80cced224a55100804aec57ac28376837a3111"
    ),
    "native_cutoff_manifest_v1": (
        "cc79e280d7e4d25e33c66bfa65b577fbe924a1e5008e81fbcd53cea2f5c11a1c"
    ),
    "projection_v1": (
        "46e45b030edd45d2b9f145924c6d673df4e59ab5c960c693236987b6dd1dd084"
    ),
    "risk_service": "6dc4ca89e61ae5907129f8307166a1ae84afd85b74924ee2b0f82106d7681244",
    "session_freshness_v1": (
        "2bacefd4b3649ccbba8e254a0e8f8c176d08e458744f74dc19145fb6d5363299"
    ),
    "shadow_preregistration_v1": (
        "105ec897334bbf181f677c6cdcf88ae95cb6942dc408877a3437589ff28666d6"
    ),
}

IMPLEMENTATION_PATHS = {
    **preregistration_v1_contract.IMPLEMENTATION_PATHS,
    "legacy_matrix_derivation_binding_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1.py"
    ),
    "native_cutoff_manifest_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1.py"
    ),
    "session_freshness_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_session_freshness_v1.py"
    ),
    "shadow_preregistration_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1.py"
    ),
}

CLOSED_LOCAL_BLOCKERS = [
    {
        "blocker": "legacy_matrix_derivation_binding_missing",
        "closure": "ADR0170_LOCAL_DETERMINISTIC_DERIVATION_BINDING_PINNED",
    },
    {
        "blocker": "native_cutoff_observation_manifest_missing",
        "closure": "ADR0171_NATIVE_SESSION_LABEL_CUTOFF_MANIFEST_PINNED",
    },
    {
        "blocker": "shadow_freshness_policy_missing",
        "closure": "ADR0172_COMPLETED_SESSION_LAG_POLICY_PINNED_EXTERNAL_TIME_TRUST_UNPROVEN",
    },
]

FIXED_REMAINING_BLOCKERS = [
    "legacy_shadow_service_not_adapter_v1_aware",
    "provider_dataset_key_control_unproven",
    "external_provider_data_issuance_unproven",
    "provider_replay_registry_unchecked",
    "external_time_authority_unauthenticated",
    "shadow_application_consumer_missing",
    "risk_service_adapter_contract_not_versioned",
    "independent_shadow_review_missing",
    "current_switch_unauthorized",
]

ACTIVATION_ORDER = [
    "BIND_AUTHENTICATED_PROVIDER_IDENTITY_KEY_CONTROL_AND_DATA_ISSUANCE",
    "VERIFY_PROVIDER_REPLAY_REGISTRY_FOR_BOUND_DATASET_LINEAGE",
    "AUTHENTICATE_EXTERNAL_TIME_AUTHORITY_FOR_FRESHNESS_REFERENCE",
    "IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V2",
    "INDEPENDENTLY_REVIEW_SYNTHETIC_SHADOW_CALLS",
    "VERSION_RISK_SERVICE_INPUT_CONTRACT",
    "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
]

REQUIRED_SHADOW_INPUT_SCHEMAS = [
    {
        "input": "dual_source_receipt",
        "schema_version": DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
    },
    {"input": "portfolio_risk_adapter", "schema_version": ADAPTER_SCHEMA_VERSION},
    {
        "input": "legacy_matrix_derivation_binding",
        "schema_version": LEGACY_MATRIX_BINDING_SCHEMA_VERSION,
    },
    {
        "input": "native_cutoff_manifest",
        "schema_version": NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION,
    },
    {
        "input": "session_freshness_registration",
        "schema_version": SESSION_FRESHNESS_REGISTRATION_SCHEMA_VERSION,
    },
    {
        "input": "session_freshness_evaluation",
        "schema_version": SESSION_FRESHNESS_EVALUATION_SCHEMA_VERSION,
    },
]

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def expected_shadow_consumer_implementation_sha256_v2() -> dict[str, str]:
    return dict(EXPECTED_IMPLEMENTATION_SHA256)


def _strict_manifest(value: Any, expected: dict[str, str]) -> bool:
    return bool(
        type(value) is dict
        and set(value) == set(expected)
        and all(
            type(key) is str
            and type(item) is str
            and _HASH_PATTERN.fullmatch(item) is not None
            for key, item in value.items()
        )
    )


def _authority() -> dict[str, bool]:
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


def _verify_v1(
    preregistration_v1: Any,
    v1_implementation_sha256: Any,
) -> bool:
    if (
        type(preregistration_v1) is not dict
        or v1_implementation_sha256
        != preregistration_v1_contract.EXPECTED_IMPLEMENTATION_SHA256
        or preregistration_v1.get("preregistration_hash") != V1_PREREGISTRATION_HASH
        or preregistration_v1.get("status") != "BLOCKED"
        or preregistration_v1.get("decision") != "PREREGISTERED_NOT_BOUND"
        or preregistration_v1.get("blockers")
        != preregistration_v1_contract.FIXED_BLOCKERS
        or preregistration_v1.get("source", {}).get(
            "implementation_fingerprints_match"
        )
        is not True
    ):
        return False
    verification = preregistration_v1_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
        preregistration_v1,
        v1_implementation_sha256,
    )
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and verification.get("preregistration_exactly_verified") is True
        and not verification.get("blockers")
    )


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
    preregistration_v1: Any,
    v1_implementation_sha256: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    v1_manifest_ok = _strict_manifest(
        v1_implementation_sha256,
        preregistration_v1_contract.EXPECTED_IMPLEMENTATION_SHA256,
    )
    v1_exact = bool(v1_manifest_ok and _verify_v1(preregistration_v1, v1_implementation_sha256))
    successor_manifest_ok = _strict_manifest(
        current_implementation_sha256,
        EXPECTED_IMPLEMENTATION_SHA256,
    )
    implementation_pins_match = bool(
        successor_manifest_ok
        and current_implementation_sha256 == EXPECTED_IMPLEMENTATION_SHA256
    )
    schema_pins_match = bool(
        PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION == "portfolio-shadow-risk-v1"
        and ADAPTER_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-adapter-v1"
        and DUAL_SOURCE_RECEIPT_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-dual-source-receipt-v1"
        and LEGACY_MATRIX_BINDING_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-legacy-matrix-derivation-binding-v1"
        and NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-native-cutoff-manifest-v1"
        and SESSION_FRESHNESS_REGISTRATION_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-session-freshness-policy-registration-v1"
        and SESSION_FRESHNESS_EVALUATION_SCHEMA_VERSION
        == "strategy-correlation-cluster-portfolio-risk-session-freshness-evaluation-v1"
    )
    local_closure_verified = bool(v1_exact and implementation_pins_match and schema_pins_match)

    blockers = list(FIXED_REMAINING_BLOCKERS)
    if not v1_manifest_ok:
        blockers.insert(0, "v1_implementation_manifest_contract_invalid")
    elif not v1_exact:
        blockers.insert(0, "immutable_v1_preregistration_mismatch")
    if not successor_manifest_ok:
        blockers.insert(0, "successor_implementation_manifest_contract_invalid")
    elif not implementation_pins_match:
        blockers.insert(0, "successor_implementation_fingerprint_mismatch")
    if not schema_pins_match:
        blockers.insert(0, "successor_upstream_schema_pin_mismatch")

    artifacts = [
        {
            "artifact_id": artifact_id,
            "path": IMPLEMENTATION_PATHS[artifact_id],
            "expected_sha256": EXPECTED_IMPLEMENTATION_SHA256[artifact_id],
        }
        for artifact_id in sorted(EXPECTED_IMPLEMENTATION_SHA256)
    ]
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "SUCCESSOR_PREREGISTERED_LOCAL_INPUT_CHAIN_CLOSED_NOT_BOUND"
            if local_closure_verified
            else "BLOCKED_SOURCE_OR_SCHEMA_DRIFT"
        ),
        "source": {
            "immutable_v1_exactly_verified": v1_exact,
            "immutable_v1_preregistration_hash": (
                V1_PREREGISTRATION_HASH if v1_exact else None
            ),
            "successor_manifest_contract_verified": successor_manifest_ok,
            "successor_implementation_fingerprints_match": implementation_pins_match,
            "successor_upstream_schema_pins_match": schema_pins_match,
            "artifacts": artifacts,
        },
        "contract_pins": {
            "immutable_v1_schema_version": (
                preregistration_v1_contract.PREREGISTRATION_SCHEMA_VERSION
            ),
            "immutable_v1_preregistration_hash": V1_PREREGISTRATION_HASH,
            "legacy_shadow_schema_version": PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION,
            "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
            "dual_source_receipt_schema_version": DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
            "legacy_matrix_derivation_binding_schema_version": (
                LEGACY_MATRIX_BINDING_SCHEMA_VERSION
            ),
            "native_cutoff_manifest_schema_version": (
                NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION
            ),
            "session_freshness_registration_schema_version": (
                SESSION_FRESHNESS_REGISTRATION_SCHEMA_VERSION
            ),
            "session_freshness_evaluation_schema_version": (
                SESSION_FRESHNESS_EVALUATION_SCHEMA_VERSION
            ),
        },
        "closed_local_blockers": [
            {
                **item,
                "closure_verified": local_closure_verified,
            }
            for item in CLOSED_LOCAL_BLOCKERS
        ],
        "required_shadow_input_schemas": list(REQUIRED_SHADOW_INPUT_SCHEMAS),
        "reuse_plan": [
            {
                "capability": "PROVIDER_IDENTITY_AND_KEY_LIFECYCLE",
                "decision": "REUSE_EXISTING_CONTRACTS_EXTERNAL_TRUST_STILL_REQUIRED",
            },
            {
                "capability": "DATASET_CONTENT_ATTESTATION",
                "decision": "REUSE_EXISTING_CONTRACT",
            },
            {
                "capability": "LEGACY_MATRIX_DERIVATION_BINDING",
                "decision": "REUSE_ADR0170_PINNED_LOCAL_ONLY",
            },
            {
                "capability": "NATIVE_SESSION_LABEL_CUTOFF",
                "decision": "REUSE_ADR0171_PINNED_NOT_FRESHNESS",
            },
            {
                "capability": "COMPLETED_SESSION_LAG_POLICY",
                "decision": "REUSE_ADR0172_PINNED_EXTERNAL_TIME_TRUST_UNPROVEN",
            },
            {
                "capability": "SHADOW_APPLICATION_CONSUMER",
                "decision": "NEW_VERSIONED_CONSUMER_V2_REQUIRED",
            },
        ],
        "activation_order": list(ACTIVATION_ORDER),
        "blockers": blockers,
        "facts": {
            "local_legacy_matrix_binding_pinned": local_closure_verified,
            "local_native_cutoff_manifest_pinned": local_closure_verified,
            "local_session_freshness_policy_pinned": local_closure_verified,
            "local_blocker_closure_verified": local_closure_verified,
            "provider_identity_stack_duplicated": False,
            "dataset_attestation_stack_duplicated": False,
            "external_provider_key_control_verified": False,
            "external_provider_data_issuance_verified": False,
            "provider_replay_registry_verified": False,
            "external_time_authority_authenticated": False,
            "legacy_shadow_replaced": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "server_route_registered": False,
            "ui_mounted": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
    document: Any,
    preregistration_v1: Any,
    v1_implementation_sha256: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
        preregistration_v1,
        v1_implementation_sha256,
        current_implementation_sha256,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["shadow_preregistration_v2_exact_rebuild_mismatch"],
        "preregistration_status": expected["status"] if exact else "UNKNOWN",
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
    }


__all__ = [
    "ACTIVATION_ORDER",
    "CLOSED_LOCAL_BLOCKERS",
    "EXPECTED_IMPLEMENTATION_SHA256",
    "FIXED_REMAINING_BLOCKERS",
    "IMPLEMENTATION_PATHS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PREREGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "REQUIRED_SHADOW_INPUT_SCHEMAS",
    "STATIC_FINGERPRINT",
    "V1_PREREGISTRATION_HASH",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2",
    "expected_shadow_consumer_implementation_sha256_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2",
]
