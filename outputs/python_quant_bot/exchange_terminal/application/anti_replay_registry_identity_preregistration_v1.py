from __future__ import annotations

import re
from typing import Any, Mapping

from exchange_terminal.application.ports.anti_replay_registry_v1 import (
    ANTI_REPLAY_NAMESPACE,
    COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION,
    COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION,
    CONSUMPTION_REQUEST_SCHEMA_VERSION,
    TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "anti-replay-registry-identity-preregistration-v1"
)
PREREGISTRATION_STATIC_FINGERPRINT = (
    "20260823-anti-replay-registry-identity-preregistration-v1-lock-1"
)
PREREGISTRATION_EXACT_VERIFICATION_SCHEMA_VERSION = (
    "anti-replay-registry-identity-preregistration-exact-rebuild-v1"
)
CONFORMANCE_PLAN_SCHEMA_VERSION = "anti-replay-registry-adapter-conformance-plan-v1"
CONFORMANCE_PLAN_STATIC_FINGERPRINT = (
    "20260823-anti-replay-registry-adapter-conformance-plan-v1-lock-1"
)
CONFORMANCE_PLAN_EXACT_VERIFICATION_SCHEMA_VERSION = (
    "anti-replay-registry-adapter-conformance-plan-exact-rebuild-v1"
)
ADAPTER_PROTOCOL_VERSION = "anti-replay-compare-and-consume-port-v1"
TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-consumer-post-registration-execution-receipt-v5"
)
REFERENCE_MODEL_IMPLEMENTATION_SHA256 = (
    "c56055d08b8ba6cc7f35437bbea7e042618b02e0d5ffed66e702f18103f8d587"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "post_registration_receipt_issuance_allowed",
    "presentation_mount_allowed",
    "runtime_gate_activation_allowed",
    "writer_allowed",
)
_BLOCKERS = (
    "REGISTRY_KEY_POSSESSION_UNVERIFIED",
    "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
    "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
    "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
    "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
    "TRUSTED_REGISTRY_TIME_UNVERIFIED",
    "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
    "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
)
_REQUIRED_CAPABILITIES = (
    "ATOMIC_COMPARE_AND_CONSUME",
    "EXACT_DUPLICATE_REJECTION",
    "SAME_SCOPE_CONFLICT_REJECTION",
    "DURABLE_RESTART_RECOVERY",
    "ROLLBACK_RESISTANCE",
    "TIMEOUT_AFTER_COMMIT_IDEMPOTENCY",
    "SIGNED_RECEIPT_V1",
    "PREREGISTERED_ED25519_REGISTRY_KEY",
    "TRUSTED_MONOTONIC_REGISTRY_TIME",
    "INDEPENDENT_CONFORMANCE_OBSERVER",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_hash(name: str, value: Any) -> str:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _validate_identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _validate_claim(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be a non-empty bounded string")
    return value


def _preregistration_body(
    *,
    registry_id: str,
    operator_identity_claim: str,
    public_key_spki_sha256: str,
    trust_domain: str,
    adapter_protocol_version: str,
) -> dict[str, Any]:
    return {
        "authority": _locked_authority(),
        "blockers": list(_BLOCKERS),
        "checks": [
            {
                "blocking": True,
                "name": "registry_identity_fields_preregistered",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "registry_ed25519_public_key_hash_preregistered",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "adapter_protocol_and_target_schemas_exact",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "external_identity_and_conformance_not_self_claimed",
                "ok": True,
            },
        ],
        "decision": (
            "REGISTRY_IDENTITY_PREREGISTERED_KEY_POSSESSION_IDENTITY_AND_"
            "EXTERNAL_CONFORMANCE_UNVERIFIED"
        ),
        "facts": {
            "adapter_conformance_verified": False,
            "durable_atomic_compare_and_consume_verified": False,
            "external_endpoint_verified": False,
            "external_linearizability_verified": False,
            "local_preregistration_complete": True,
            "network_accessed": False,
            "post_registration_receipt_issued": False,
            "registry_key_possession_verified": False,
            "registry_organization_identity_verified": False,
            "registry_public_key_hash_preregistered": True,
            "runtime_assets_accessed": False,
            "signed_target_consumption_receipt_verified": False,
            "target_consumption_receipt_issued": False,
            "trusted_registry_time_verified": False,
        },
        "identity": {
            "key_algorithm": "Ed25519",
            "operator_identity_claim": operator_identity_claim,
            "public_key_spki_sha256": public_key_spki_sha256,
            "registry_id": registry_id,
            "trust_domain": trust_domain,
        },
        "requirements": list(_REQUIRED_CAPABILITIES),
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "source": {
            "adapter_protocol_version": adapter_protocol_version,
            "anti_replay_namespace": ANTI_REPLAY_NAMESPACE,
            "command_schema_version": COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION,
            "consumption_request_schema_version": CONSUMPTION_REQUEST_SCHEMA_VERSION,
            "reference_model_implementation_sha256": (
                REFERENCE_MODEL_IMPLEMENTATION_SHA256
            ),
            "result_schema_version": COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "target_consumption_receipt_schema_version": (
                TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION
            ),
            "target_post_registration_receipt_schema_version": (
                TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION
            ),
        },
        "static_fingerprint": PREREGISTRATION_STATIC_FINGERPRINT,
        "status": "BLOCKED",
    }


def build_anti_replay_registry_identity_preregistration_v1(
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    registry_id = _validate_identifier("registry_id", registry_id)
    operator_identity_claim = _validate_claim(
        "operator_identity_claim", operator_identity_claim
    )
    public_key_spki_sha256 = _validate_hash(
        "public_key_spki_sha256", public_key_spki_sha256
    )
    trust_domain = _validate_identifier("trust_domain", trust_domain)
    if adapter_protocol_version != ADAPTER_PROTOCOL_VERSION:
        raise ValueError("adapter protocol aliases are forbidden")
    return seal_strict_canonical_document(
        _preregistration_body(
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        ),
        "preregistration_hash",
    )


def verify_anti_replay_registry_identity_preregistration_v1(
    document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    try:
        expected = build_anti_replay_registry_identity_preregistration_v1(
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
        exact = strict_json_contract_equal(document, expected)
    except (TypeError, ValueError):
        exact = False
        expected = None
    return {
        "adapter_conformance_verified": False,
        "blockers": [] if exact else ["REGISTRY_IDENTITY_PREREGISTRATION_EXACT_REBUILD"],
        "current_admission_allowed": False,
        "external_linearizability_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "post_registration_receipt_issued": False,
        "preregistration_document_exactly_rebuilt": exact,
        "preregistration_hash": (
            expected["preregistration_hash"] if exact and expected is not None else None
        ),
        "preregistration_status": "BLOCKED" if exact else "UNKNOWN",
        "registry_identity_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": PREREGISTRATION_EXACT_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "target_consumption_receipt_issued": False,
        "trusted_registry_time_verified": False,
        "writer_allowed": False,
    }


def _conformance_cases() -> list[dict[str, Any]]:
    return [
        {
            "attack": "NONE",
            "case_id": "FIRST_CONSUME",
            "expected": "ONE_SIGNED_CONSUMED_RECEIPT",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "EXACT_RETRY",
            "case_id": "EXACT_DUPLICATE",
            "expected": "DUPLICATE_REJECTED_WITH_ORIGINAL_BINDING",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "SAME_SCOPE_DIFFERENT_REQUEST",
            "case_id": "SAME_SCOPE_CONFLICT",
            "expected": "CONFLICT_REJECTED_WITHOUT_STATE_CHANGE",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "PARALLEL_COLLISION",
            "case_id": "PARALLEL_COMPARE_AND_CONSUME",
            "expected": "EXACTLY_ONE_CONSUMED_ALL_OTHERS_REJECTED",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "TIMEOUT_AFTER_COMMIT",
            "case_id": "TIMEOUT_RETRY_IDEMPOTENCY",
            "expected": "RETRY_CANNOT_CREATE_SECOND_CONSUMPTION",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "PROCESS_RESTART",
            "case_id": "DURABLE_RESTART_RECOVERY",
            "expected": "CONSUMED_SCOPE_REMAINS_UNAVAILABLE_AFTER_RESTART",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "STATE_ROLLBACK",
            "case_id": "ROLLBACK_RESISTANCE",
            "expected": "ROLLBACK_CANNOT_REOPEN_CONSUMED_SCOPE",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "RECEIPT_SUBSTITUTION",
            "case_id": "SIGNED_RECEIPT_BINDING",
            "expected": "HASH_OR_SIGNATURE_MISMATCH_REJECTED",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "UNPREREGISTERED_KEY_OR_ROTATION",
            "case_id": "REGISTRY_KEY_BINDING",
            "expected": "UNPREREGISTERED_SIGNING_KEY_REJECTED",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
        {
            "attack": "NON_MONOTONIC_OR_UNTRUSTED_TIME",
            "case_id": "TRUSTED_TIME_MONOTONICITY",
            "expected": "UNTRUSTED_OR_NON_MONOTONIC_TIME_REJECTED",
            "requires_external_runtime": True,
            "requires_independent_observer": True,
        },
    ]


def build_anti_replay_registry_adapter_conformance_plan_v1(
    preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    verification = verify_anti_replay_registry_identity_preregistration_v1(
        preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
        adapter_protocol_version=adapter_protocol_version,
    )
    if verification["status"] != "PASS":
        raise ValueError("registry identity preregistration is not exact")
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "blockers": [
                "CONFORMANCE_CASES_NOT_EXECUTED",
                "EXTERNAL_ADAPTER_NOT_INVOKED",
                "INDEPENDENT_OBSERVER_NOT_BOUND",
                "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
                "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
                "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
            ],
            "cases": _conformance_cases(),
            "decision": (
                "CONFORMANCE_PLAN_PREREGISTERED_EXTERNAL_EXECUTION_AND_"
                "INDEPENDENT_OBSERVATION_REQUIRED"
            ),
            "facts": {
                "adapter_conformance_verified": False,
                "conformance_cases_executed": False,
                "conformance_cases_preregistered": True,
                "external_adapter_invoked": False,
                "external_linearizability_verified": False,
                "external_runtime_accessed": False,
                "independent_observer_bound": False,
                "network_accessed": False,
                "post_registration_receipt_issued": False,
                "target_consumption_receipt_issued": False,
            },
            "schema_version": CONFORMANCE_PLAN_SCHEMA_VERSION,
            "source": {
                "adapter_protocol_version": adapter_protocol_version,
                "preregistration_hash": preregistration_document[
                    "preregistration_hash"
                ],
                "public_key_spki_sha256": public_key_spki_sha256,
                "registry_id": registry_id,
                "target_consumption_receipt_schema_version": (
                    TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION
                ),
            },
            "static_fingerprint": CONFORMANCE_PLAN_STATIC_FINGERPRINT,
            "status": "BLOCKED",
        },
        "plan_hash",
    )


def verify_anti_replay_registry_adapter_conformance_plan_v1(
    document: Any,
    preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    adapter_protocol_version: Any = ADAPTER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    try:
        expected = build_anti_replay_registry_adapter_conformance_plan_v1(
            preregistration_document,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            adapter_protocol_version=adapter_protocol_version,
        )
        exact = strict_json_contract_equal(document, expected)
    except (TypeError, ValueError):
        exact = False
        expected = None
    return {
        "adapter_conformance_verified": False,
        "blockers": [] if exact else ["ADAPTER_CONFORMANCE_PLAN_EXACT_REBUILD"],
        "conformance_cases_executed": False,
        "current_admission_allowed": False,
        "external_linearizability_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "plan_document_exactly_rebuilt": exact,
        "plan_hash": expected["plan_hash"] if exact and expected is not None else None,
        "plan_status": "BLOCKED" if exact else "UNKNOWN",
        "post_registration_receipt_issued": False,
        "registry_identity_verified": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": CONFORMANCE_PLAN_EXACT_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "target_consumption_receipt_issued": False,
        "trusted_registry_time_verified": False,
        "writer_allowed": False,
    }
