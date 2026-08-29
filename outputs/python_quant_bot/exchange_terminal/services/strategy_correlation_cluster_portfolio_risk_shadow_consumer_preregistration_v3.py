from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any

from . import strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2 as v2_contract
from . import strategy_correlation_provider_dataset_content_attestation_v1 as content_attestation_contract
from . import strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as content_replay_contract
from . import strategy_correlation_provider_dataset_key_lifecycle_gate_v1 as lifecycle_contract
from . import strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as lifecycle_replay_contract
from .execution_authority import authority_violations


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v3"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
    "preregistration-v3-verification-v1"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-shadow-preregistration-v3-lock-1"
V2_PREREGISTRATION_HASH = (
    "93a89e449f908d72710a3536dce3ec509285d39b36fba92db29d4eac3049d9c5"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_V2_CONTEXT_KEYS = {
    "preregistration_v1",
    "v1_implementation_sha256",
    "current_implementation_sha256",
}
_EXPECTED_V2_IMPLEMENTATION_SHA256 = {
    "adapter_v1": "e3154743d7fb74a79d600b948f84c53a2a8666b13b0fc1cd00e9eca5590e8cee",
    "calendar_provider_composition_v1": "922e626c72c3eb6be64a7a7d07ea0339655318eacac44a5121370cf8e11b1197",
    "dataset_content_attestation_v1": "91dcad9660f379c47c2e912bda5032cbabc72dc5af8c42ece2ea3bede19bc654",
    "dual_source_receipt_v1": "728f6230e00eddd40eca137d5c736d83537e516f7568d4bbc24dd90f8ae4f612",
    "legacy_matrix_derivation_binding_v1": "144ec7b141dd96362c7f58bafd745243945b9afa2e0774ef7e95b03586235890",
    "legacy_portfolio_risk_v1": "a97042a0265cc6bc552c8a818feadfd26e917b7eb75e36f9d4b8ca924717af19",
    "legacy_shadow_service_v1": "c7e6010e8fa6eaa0e6b1ba081c80cced224a55100804aec57ac28376837a3111",
    "native_cutoff_manifest_v1": "cc79e280d7e4d25e33c66bfa65b577fbe924a1e5008e81fbcd53cea2f5c11a1c",
    "projection_v1": "46e45b030edd45d2b9f145924c6d673df4e59ab5c960c693236987b6dd1dd084",
    "risk_service": "6dc4ca89e61ae5907129f8307166a1ae84afd85b74924ee2b0f82106d7681244",
    "session_freshness_v1": "2bacefd4b3649ccbba8e254a0e8f8c176d08e458744f74dc19145fb6d5363299",
    "shadow_preregistration_v1": "105ec897334bbf181f677c6cdcf88ae95cb6942dc408877a3437589ff28666d6",
}
_EXPECTED_IMPLEMENTATION_SHA256 = {
    **_EXPECTED_V2_IMPLEMENTATION_SHA256,
    "dataset_key_lifecycle_gate_v1": (
        "c779ef769383935dec7b9a9a81ea896ccf505144e0ce1bec46f39fc840c19369"
    ),
    "dataset_key_lifecycle_replay_gate_v1": (
        "a34bdc06efe5c68e38955a4c7698c53587257f1cdd13482afd70f14a872a1c27"
    ),
    "dataset_content_issuance_replay_gate_v1": (
        "9832b2c8375bc814107cd1769264667c362b1eb1b9eda3533abb1f373c25371e"
    ),
    "shadow_preregistration_v2": (
        "e4ab1097ae47d11bde2674976abe521d7f335f662b5c8c1f8786ad7eb41a653a"
    ),
}
_ARTIFACT_PATHS = {
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
    "legacy_matrix_derivation_binding_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_"
        "legacy_matrix_derivation_binding_v1.py"
    ),
    "legacy_portfolio_risk_v1": (
        "exchange_terminal/services/portfolio_risk.py"
    ),
    "legacy_shadow_service_v1": (
        "exchange_terminal/services/portfolio_shadow_risk.py"
    ),
    "native_cutoff_manifest_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1.py"
    ),
    "projection_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_projection_v1.py"
    ),
    "risk_service": "exchange_terminal/services/risk_service.py",
    "session_freshness_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_session_freshness_v1.py"
    ),
    "shadow_preregistration_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_"
        "shadow_consumer_preregistration_v1.py"
    ),
    "dataset_key_lifecycle_gate_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_provider_dataset_key_lifecycle_gate_v1.py"
    ),
    "dataset_key_lifecycle_replay_gate_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1.py"
    ),
    "dataset_content_issuance_replay_gate_v1": (
        "exchange_terminal/services/"
        "strategy_correlation_provider_dataset_content_issuance_replay_gate_v1.py"
    ),
    "shadow_preregistration_v2": (
        "exchange_terminal/services/"
        "strategy_correlation_cluster_portfolio_risk_"
        "shadow_consumer_preregistration_v2.py"
    ),
}
_EXPECTED_V2_BLOCKERS = [
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
_EXPECTED_V2_CLOSED_LOCAL_BLOCKERS = [
    {
        "blocker": "legacy_matrix_derivation_binding_missing",
        "closure": "ADR0170_LOCAL_DETERMINISTIC_DERIVATION_BINDING_PINNED",
        "closure_verified": True,
    },
    {
        "blocker": "native_cutoff_observation_manifest_missing",
        "closure": "ADR0171_NATIVE_SESSION_LABEL_CUTOFF_MANIFEST_PINNED",
        "closure_verified": True,
    },
    {
        "blocker": "shadow_freshness_policy_missing",
        "closure": (
            "ADR0172_COMPLETED_SESSION_LAG_POLICY_PINNED_"
            "EXTERNAL_TIME_TRUST_UNPROVEN"
        ),
        "closure_verified": True,
    },
]
_EXPECTED_V2_REQUIRED_INPUTS = [
    {
        "input": "dual_source_receipt",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-dual-source-receipt-v1"
        ),
    },
    {
        "input": "portfolio_risk_adapter",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-adapter-v1"
        ),
    },
    {
        "input": "legacy_matrix_derivation_binding",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-"
            "legacy-matrix-derivation-binding-v1"
        ),
    },
    {
        "input": "native_cutoff_manifest",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-"
            "native-cutoff-manifest-v1"
        ),
    },
    {
        "input": "session_freshness_registration",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-"
            "session-freshness-policy-registration-v1"
        ),
    },
    {
        "input": "session_freshness_evaluation",
        "schema_version": (
            "strategy-correlation-cluster-portfolio-risk-"
            "session-freshness-evaluation-v1"
        ),
    },
]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _manifest_matches(value: Any, expected: dict[str, str]) -> bool:
    return (
        type(value) is dict
        and set(value) == set(expected)
        and all(
            type(value[key]) is str
            and _valid_sha256(value[key])
            and value[key] == expected_hash
            for key, expected_hash in expected.items()
        )
    )


def expected_shadow_consumer_implementation_sha256_v3() -> dict[str, str]:
    return dict(_EXPECTED_IMPLEMENTATION_SHA256)


def _verify_v2_source(
    preregistration_v2: Any,
    v2_verification_context: Any,
    current_implementation_sha256: Any,
) -> None:
    if (
        type(v2_verification_context) is not dict
        or set(v2_verification_context) != _V2_CONTEXT_KEYS
        or not _manifest_matches(
            v2_verification_context.get("current_implementation_sha256"),
            _EXPECTED_V2_IMPLEMENTATION_SHA256,
        )
        or not _manifest_matches(
            current_implementation_sha256,
            _EXPECTED_IMPLEMENTATION_SHA256,
        )
        or any(
            current_implementation_sha256[key]
            != v2_verification_context["current_implementation_sha256"][key]
            for key in _EXPECTED_V2_IMPLEMENTATION_SHA256
        )
    ):
        raise ValueError("shadow_preregistration_v3_manifest_invalid")
    verification = (
        v2_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
            preregistration_v2,
            v2_verification_context["preregistration_v1"],
            v2_verification_context["v1_implementation_sha256"],
            v2_verification_context["current_implementation_sha256"],
        )
    )
    if (
        type(verification) is not dict
        or verification.get("schema_version")
        != v2_contract.PREREGISTRATION_VERIFICATION_SCHEMA_VERSION
        or verification.get("status") != "PASS"
        or verification.get("preregistration_exactly_verified") is not True
        or verification.get("preregistration_status") != "BLOCKED"
        or verification.get("blockers") != []
        or verification.get("current_admission_allowed") is not False
        or verification.get("runtime_gate_activation_allowed") is not False
        or verification.get("shadow_consumer_activation_allowed") is not False
        or verification.get("paper_authorized") is not False
        or verification.get("live_order_allowed") is not False
    ):
        raise ValueError("shadow_preregistration_v3_v2_verification_invalid")
    if (
        type(preregistration_v2) is not dict
        or preregistration_v2.get("schema_version")
        != v2_contract.PREREGISTRATION_SCHEMA_VERSION
        or preregistration_v2.get("static_fingerprint")
        != v2_contract.STATIC_FINGERPRINT
        or preregistration_v2.get("preregistration_hash")
        != V2_PREREGISTRATION_HASH
        or preregistration_v2.get("status") != "BLOCKED"
        or preregistration_v2.get("blockers") != _EXPECTED_V2_BLOCKERS
        or preregistration_v2.get("closed_local_blockers")
        != _EXPECTED_V2_CLOSED_LOCAL_BLOCKERS
        or preregistration_v2.get("required_shadow_input_schemas")
        != _EXPECTED_V2_REQUIRED_INPUTS
        or preregistration_v2.get("facts", {}).get(
            "provider_replay_registry_verified"
        )
        is not False
        or preregistration_v2.get("facts", {}).get("runtime_consumer_bound")
        is not False
        or preregistration_v2.get("facts", {}).get("ui_mounted") is not False
        or preregistration_v2.get("authority", {}).get(
            "current_admission_allowed"
        )
        is not False
        or preregistration_v2.get("authority", {}).get(
            "shadow_consumer_activation_allowed"
        )
        is not False
    ):
        raise ValueError("shadow_preregistration_v3_v2_contract_mismatch")


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
    preregistration_v2: Any,
    v2_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    if _authority_invalid(
        [
            preregistration_v2,
            v2_verification_context,
            current_implementation_sha256,
        ]
    ):
        raise ValueError("shadow_preregistration_v3_authority_invalid")
    _verify_v2_source(
        preregistration_v2,
        v2_verification_context,
        current_implementation_sha256,
    )

    source_artifacts = [
        {
            "artifact_id": artifact_id,
            "path": _ARTIFACT_PATHS[artifact_id],
            "expected_sha256": expected_hash,
        }
        for artifact_id, expected_hash in _EXPECTED_IMPLEMENTATION_SHA256.items()
    ]
    required_inputs = deepcopy(_EXPECTED_V2_REQUIRED_INPUTS) + [
        {
            "input": "provider_dataset_content_attestation_verification",
            "schema_version": content_attestation_contract.SCHEMA_VERSION,
        },
        {
            "input": "provider_dataset_key_lifecycle_replay_verification",
            "schema_version": lifecycle_replay_contract.SCHEMA_VERSION,
        },
        {
            "input": "provider_dataset_content_issuance_replay_registration",
            "schema_version": content_replay_contract.REGISTRATION_SCHEMA_VERSION,
        },
        {
            "input": "provider_dataset_content_issuance_replay_pinned_checkpoint",
            "schema_version": (
                content_replay_contract.PINNED_CHECKPOINT_SCHEMA_VERSION
            ),
        },
        {
            "input": "provider_dataset_content_issuance_replay_checkpoint",
            "schema_version": content_replay_contract.CHECKPOINT_SCHEMA_VERSION,
        },
        {
            "input": "provider_dataset_content_issuance_replay_occurrence_audit",
            "schema_version": (
                content_replay_contract.OCCURRENCE_AUDIT_SCHEMA_VERSION
            ),
        },
        {
            "input": "provider_dataset_content_issuance_replay_verification",
            "schema_version": content_replay_contract.SCHEMA_VERSION,
        },
    ]
    closed_local_blockers = deepcopy(_EXPECTED_V2_CLOSED_LOCAL_BLOCKERS)
    newly_pinned_local_capabilities = [
        {
            "capability": (
                "PROVIDER_DATASET_CONTENT_ISSUANCE_REPLAY_CONTRACT"
            ),
            "pin": (
                "ADR0176_IMPLEMENTATION_AND_SCHEMA_FAMILY_PINNED_"
                "EVIDENCE_NOT_BOUND"
            ),
            "contract_pinned": True,
            "evidence_bound": False,
            "external_authority_verified": False,
        }
    ]
    blocker_refinements = [
        {
            "source_blocker": "provider_replay_registry_unchecked",
            "local_contract_state": (
                "ADR0176_CONTRACT_PINNED_NO_REGISTRATION_CHECKPOINT_"
                "PROOF_OR_AUDIT_BOUND"
            ),
            "source_blocker_closed": False,
            "remaining_requirements": [
                "provider_content_issuance_replay_evidence_not_bound",
                "external_content_replay_registry_authority_unproven",
                "external_occurrence_auditor_authority_unproven",
                "durable_content_checkpoint_publication_unproven",
                "runtime_consumption_replay_enforcement_missing",
                "future_replay_absence_unproven",
            ],
        }
    ]
    blockers = list(_EXPECTED_V2_BLOCKERS) + [
        "provider_content_issuance_replay_evidence_not_bound",
        "external_content_replay_registry_authority_unproven",
        "external_occurrence_auditor_authority_unproven",
        "durable_content_checkpoint_publication_unproven",
        "runtime_consumption_replay_enforcement_missing",
        "future_replay_absence_unproven",
    ]
    facts = {
        "immutable_v2_exactly_verified": True,
        "local_blocker_closure_verified": True,
        "closed_local_blocker_count": 3,
        "local_content_issuance_replay_contract_pinned": True,
        "content_issuance_replay_evidence_bound": False,
        "provider_replay_registry_verified": False,
        "external_content_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "external_provider_key_control_verified": False,
        "external_provider_data_issuance_verified": False,
        "durable_content_checkpoint_publication_verified": False,
        "runtime_consumption_replay_enforcement_verified": False,
        "future_replay_absence_verified": False,
        "external_time_authority_authenticated": False,
        "provider_identity_stack_duplicated": False,
        "dataset_attestation_stack_duplicated": False,
        "legacy_shadow_replaced": False,
        "runtime_assets_accessed": False,
        "runtime_consumer_bound": False,
        "server_route_registered": False,
        "ui_mounted": False,
    }
    authority = {
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "SUCCESSOR_PREREGISTERED_ADR0176_CONTRACT_PINNED_"
            "REPLAY_EVIDENCE_NOT_BOUND"
        ),
        "source": {
            "immutable_v2_exactly_verified": True,
            "immutable_v2_schema_version": (
                v2_contract.PREREGISTRATION_SCHEMA_VERSION
            ),
            "immutable_v2_preregistration_hash": V2_PREREGISTRATION_HASH,
            "immutable_v2_implementation_sha256": (
                _EXPECTED_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v2"
                ]
            ),
            "successor_manifest_contract_verified": True,
            "successor_implementation_fingerprints_match": True,
            "artifacts": source_artifacts,
        },
        "contract_pins": {
            "immutable_v2_schema_version": (
                v2_contract.PREREGISTRATION_SCHEMA_VERSION
            ),
            "immutable_v2_preregistration_hash": V2_PREREGISTRATION_HASH,
            "immutable_v2_contract_pins": deepcopy(
                preregistration_v2["contract_pins"]
            ),
            "dataset_content_attestation_schema_version": (
                content_attestation_contract.SCHEMA_VERSION
            ),
            "dataset_key_lifecycle_schema_version": lifecycle_contract.SCHEMA_VERSION,
            "dataset_key_lifecycle_replay_schema_version": (
                lifecycle_replay_contract.SCHEMA_VERSION
            ),
            "content_issuance_replay_registration_schema_version": (
                content_replay_contract.REGISTRATION_SCHEMA_VERSION
            ),
            "content_issuance_replay_pinned_checkpoint_schema_version": (
                content_replay_contract.PINNED_CHECKPOINT_SCHEMA_VERSION
            ),
            "content_issuance_replay_checkpoint_schema_version": (
                content_replay_contract.CHECKPOINT_SCHEMA_VERSION
            ),
            "content_issuance_replay_occurrence_audit_schema_version": (
                content_replay_contract.OCCURRENCE_AUDIT_SCHEMA_VERSION
            ),
            "content_issuance_replay_gate_schema_version": (
                content_replay_contract.SCHEMA_VERSION
            ),
            "content_issuance_replay_verification_state": (
                content_replay_contract.VERIFICATION_STATE
            ),
            "content_issuance_log_protocol": (
                content_replay_contract.LOG_PROTOCOL
            ),
            "content_issuance_scan_policy": (
                content_replay_contract.SCAN_POLICY
            ),
            "content_issuance_cardinality_policy": (
                content_replay_contract.CARDINALITY_POLICY
            ),
            "content_issuance_identity_policy": (
                content_replay_contract.CONTENT_IDENTITY_POLICY
            ),
        },
        "closed_local_blockers": closed_local_blockers,
        "newly_pinned_local_capabilities": newly_pinned_local_capabilities,
        "blocker_refinements": blocker_refinements,
        "required_shadow_input_schemas": required_inputs,
        "reuse_plan": [
            {
                "capability": "PROVIDER_IDENTITY_AND_KEY_LIFECYCLE",
                "decision": (
                    "REUSE_EXISTING_CONTRACTS_EXTERNAL_TRUST_STILL_REQUIRED"
                ),
            },
            {
                "capability": "DATASET_CONTENT_ATTESTATION",
                "decision": "REUSE_EXISTING_CONTRACT",
            },
            {
                "capability": "DATASET_CONTENT_ISSUANCE_REPLAY",
                "decision": (
                    "REUSE_ADR0176_PINNED_LOCAL_CONTRACT_EVIDENCE_NOT_BOUND"
                ),
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
                "decision": (
                    "REUSE_ADR0172_PINNED_EXTERNAL_TIME_TRUST_UNPROVEN"
                ),
            },
            {
                "capability": "SHADOW_APPLICATION_CONSUMER",
                "decision": "NEW_VERSIONED_CONSUMER_V3_REQUIRED",
            },
        ],
        "activation_order": [
            "BIND_AUTHENTICATED_PROVIDER_IDENTITY_KEY_CONTROL_AND_DATA_ISSUANCE",
            "SUPPLY_EXACT_ADR0176_REGISTRATION_CHECKPOINT_PROOFS_AND_AUDIT",
            "VERIFY_EXTERNAL_CONTENT_REPLAY_REGISTRY_AUTHORITY_AND_DURABLE_PUBLICATION",
            "AUTHENTICATE_EXTERNAL_TIME_AUTHORITY_FOR_FRESHNESS_REFERENCE",
            "IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V3",
            "INDEPENDENTLY_REVIEW_SYNTHETIC_SHADOW_CALLS",
            "VERSION_RISK_SERVICE_INPUT_CONTRACT",
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        ],
        "blockers": blockers,
        "facts": facts,
        "authority": authority,
    }
    return {**body, "preregistration_hash": _sha256(body)}


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
    document: Any,
    preregistration_v2: Any,
    v2_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    rebuilt: dict[str, Any] | None = None
    if type(document) is not dict:
        blockers.append("preregistration_document_invalid")
    elif _authority_invalid(document):
        blockers.append("preregistration_authority_invalid")
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
            preregistration_v2,
            v2_verification_context,
            current_implementation_sha256,
        )
    except (
        ArithmeticError,
        KeyError,
        MemoryError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        blockers.append("preregistration_rebuild_failed")
    if (
        type(document) is dict
        and rebuilt is not None
        and document != rebuilt
    ):
        blockers.append("preregistration_exact_mismatch")
    exact = not blockers and document == rebuilt
    return {
        "schema_version": PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "FAIL",
        "preregistration_exactly_verified": exact,
        "preregistration_status": (
            document.get("status")
            if type(document) is dict
            and document.get("status") in {"BLOCKED", "UNKNOWN"}
            else "UNKNOWN"
        ),
        "blockers": blockers,
        "shadow_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
