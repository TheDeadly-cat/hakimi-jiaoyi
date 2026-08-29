"""Provider identity binding and conformance plan for anti-replay port v2."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.application.anti_replay_registry_identity_preregistration_v1 import (
    ADAPTER_PROTOCOL_VERSION as SOURCE_ADAPTER_PROTOCOL_VERSION,
    verify_anti_replay_registry_identity_preregistration_v1,
)
from exchange_terminal.application.anti_replay_registry_signer_source_trust_preregistration_v1 import (
    verify_anti_replay_registry_signer_source_trust_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_namespace_preregistration_v1 import (
    SOURCE_NAMESPACE,
    TARGET_RECEIPT_SCHEMA_VERSION,
    verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1,
)
from exchange_terminal.application.ports.anti_replay_registry_v2 import (
    COMMAND_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = "20260823-source-baseline-provider-conformance-v2-lock-1"
PROVIDER_IDENTITY_BINDING_SCHEMA_VERSION = (
    "source-baseline-anti-replay-provider-identity-binding-v2"
)
PROVIDER_CONFORMANCE_PLAN_SCHEMA_VERSION = (
    "source-baseline-anti-replay-provider-conformance-plan-v2"
)
PORT_V2_PROTOCOL_VERSION = "anti-replay-compare-and-consume-port-v2"

IDENTITY_PREREGISTRATION_V1_IMPLEMENTATION_SHA256 = (
    "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f"
)
ORGANIZATION_IDENTITY_INTAKE_V1_IMPLEMENTATION_SHA256 = (
    "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56"
)
SIGNER_SOURCE_TRUST_V1_IMPLEMENTATION_SHA256 = (
    "12565b61f7984e87821f5abb86edd005436b5214f527549a93c011cb158cd51c"
)
ANTI_REPLAY_REGISTRY_V2_IMPLEMENTATION_SHA256 = (
    "ff5d027d7b8352455be7792b495076070347de67534b736ff46cc1872f927f21"
)
SOURCE_BASELINE_NAMESPACE_V1_IMPLEMENTATION_SHA256 = (
    "c716d91765aba195bb4f65be0d2fd6b9cc6e768ddcb544a2f0633eb894dc2e29"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)


def _claim_hash(field: str, value: Any) -> str:
    return strict_canonical_hash({"field": field, "value": value})


def _verify_upstreams(
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> tuple[bool, dict[str, Any] | None, dict[str, Any] | None]:
    if not verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1(
        namespace_preregistration_document
    ):
        return False, None, None
    try:
        identity_verification = (
            verify_anti_replay_registry_identity_preregistration_v1(
                identity_preregistration_document,
                registry_id=registry_id,
                operator_identity_claim=operator_identity_claim,
                public_key_spki_sha256=public_key_spki_sha256,
                trust_domain=trust_domain,
            )
        )
        source_trust_verification = (
            verify_anti_replay_registry_signer_source_trust_preregistration_v1(
                signer_source_trust_preregistration_document,
                organization_identity_intake_document,
                identity_preregistration_document,
                registry_id=registry_id,
                operator_identity_claim=operator_identity_claim,
                public_key_spki_sha256=public_key_spki_sha256,
                trust_domain=trust_domain,
            )
        )
    except (KeyError, TypeError, ValueError):
        return False, None, None
    exact = (
        identity_verification.get("status") == "PASS"
        and identity_verification.get("preregistration_document_exactly_rebuilt")
        is True
        and source_trust_verification.get("status") == "PASS"
    )
    return exact, identity_verification, source_trust_verification


def _build_binding_document(
    *,
    status: str,
    binding_status: str,
    reason_code: str,
    source_documents_exactly_verified: bool,
    namespace_preregistration_hash: str | None,
    identity_preregistration_hash: str | None,
    organization_identity_intake_hash: str | None,
    signer_source_trust_preregistration_hash: str | None,
    registry_id_claim_hash: str | None,
    operator_identity_claim_hash: str | None,
    public_key_spki_sha256: str | None,
    trust_domain_claim_hash: str | None,
) -> dict[str, Any]:
    document = {
        "schema_version": PROVIDER_IDENTITY_BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_status": binding_status,
        "reason_code": reason_code,
        "permission_state": "BLOCKED",
        "source_bindings": {
            "namespace_preregistration_hash": namespace_preregistration_hash,
            "identity_preregistration_hash": identity_preregistration_hash,
            "organization_identity_intake_hash": organization_identity_intake_hash,
            "signer_source_trust_preregistration_hash": signer_source_trust_preregistration_hash,
            "registry_id_claim_hash": registry_id_claim_hash,
            "operator_identity_claim_hash": operator_identity_claim_hash,
            "public_key_spki_sha256": public_key_spki_sha256,
            "trust_domain_claim_hash": trust_domain_claim_hash,
        },
        "protocol_binding": {
            "source_adapter_protocol_version": SOURCE_ADAPTER_PROTOCOL_VERSION,
            "target_adapter_protocol_version": PORT_V2_PROTOCOL_VERSION,
            "anti_replay_namespace": SOURCE_NAMESPACE,
            "target_receipt_schema_version": TARGET_RECEIPT_SCHEMA_VERSION,
            "request_schema_version": REQUEST_SCHEMA_VERSION,
            "command_schema_version": COMMAND_SCHEMA_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
        },
        "implementation_bindings": {
            "identity_preregistration_v1_sha256": IDENTITY_PREREGISTRATION_V1_IMPLEMENTATION_SHA256,
            "organization_identity_intake_v1_sha256": ORGANIZATION_IDENTITY_INTAKE_V1_IMPLEMENTATION_SHA256,
            "signer_source_trust_v1_sha256": SIGNER_SOURCE_TRUST_V1_IMPLEMENTATION_SHA256,
            "anti_replay_registry_v2_sha256": ANTI_REPLAY_REGISTRY_V2_IMPLEMENTATION_SHA256,
            "source_baseline_namespace_v1_sha256": SOURCE_BASELINE_NAMESPACE_V1_IMPLEMENTATION_SHA256,
            "strict_canonical_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "source_documents_exactly_verified": source_documents_exactly_verified,
            "source_protocol_is_v1": source_documents_exactly_verified,
            "target_protocol_is_v2": source_documents_exactly_verified,
            "v1_conformance_plan_applies_to_v2": False,
            "registry_identity_verified": False,
            "organization_identity_verified": False,
            "external_source_trust_verified": False,
            "signer_role_identity_verified": False,
            "key_governance_verified": False,
            "provider_conformance_verified": False,
            "provider_endpoint_embedded": False,
            "raw_operator_claim_embedded": False,
            "private_key_embedded": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "provider_call_allowed": False,
            "writer_allowed": False,
            "runtime_gate_activation_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "provider_identity_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding_document(
        status="UNKNOWN",
        binding_status="UNKNOWN",
        reason_code=reason_code,
        source_documents_exactly_verified=False,
        namespace_preregistration_hash=None,
        identity_preregistration_hash=None,
        organization_identity_intake_hash=None,
        signer_source_trust_preregistration_hash=None,
        registry_id_claim_hash=None,
        operator_identity_claim_hash=None,
        public_key_spki_sha256=None,
        trust_domain_claim_hash=None,
    )


def build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> dict[str, Any]:
    exact, _, _ = _verify_upstreams(
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    if not exact:
        return _unknown_binding("UPSTREAM_IDENTITY_OR_SOURCE_TRUST_NOT_EXACT")
    try:
        return _build_binding_document(
            status="BLOCKED",
            binding_status="CLAIM_BOUND_UNAUTHENTICATED",
            reason_code="V1_IDENTITY_SOURCE_BOUND_TO_V2_SCOPE_EXTERNAL_IDENTITY_AND_CONFORMANCE_UNPROVEN",
            source_documents_exactly_verified=True,
            namespace_preregistration_hash=namespace_preregistration_document[
                "namespace_preregistration_hash"
            ],
            identity_preregistration_hash=identity_preregistration_document[
                "preregistration_hash"
            ],
            organization_identity_intake_hash=organization_identity_intake_document[
                "intake_preregistration_hash"
            ],
            signer_source_trust_preregistration_hash=signer_source_trust_preregistration_document[
                "source_trust_preregistration_hash"
            ],
            registry_id_claim_hash=_claim_hash("registry_id", registry_id),
            operator_identity_claim_hash=_claim_hash(
                "operator_identity_claim", operator_identity_claim
            ),
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain_claim_hash=_claim_hash("trust_domain", trust_domain),
        )
    except (KeyError, TypeError, ValueError):
        return _unknown_binding("UPSTREAM_IDENTITY_BINDING_FIELDS_INVALID")


def verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
    document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    rebuilt = build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    return strict_json_contract_equal(dict(document), rebuilt)


def expected_source_baseline_nonce_anti_replay_provider_conformance_cases_v2() -> list[dict[str, Any]]:
    case_ids = (
        "EXACT_REQUEST_ACCEPTANCE",
        "NAMESPACE_REBINDING_REJECTION",
        "SCOPE_REBINDING_REJECTION",
        "CONSUMPTION_KEY_REBINDING_REJECTION",
        "DUPLICATE_REJECTION",
        "COMPARE_AND_CONSUME_CONFLICT",
        "CONSUMED_RECEIPT_BINDING",
        "RECEIPT_SCHEMA_ALIAS_REJECTION",
        "REGISTRY_REVISION_MONOTONICITY",
        "CONCURRENT_SAME_KEY_SINGLE_CONSUMER",
        "RESTART_REPLAY_RETENTION",
        "DURABLE_COMMIT_ACKNOWLEDGEMENT",
        "IDENTITY_KEY_ROTATION_AND_REVOCATION",
        "TRUSTED_REGISTRY_REVISION_SOURCE",
    )
    return [
        {
            "case_id": case_id,
            "required": True,
            "execution_status": "NOT_RUN",
            "evidence_hash": None,
        }
        for case_id in case_ids
    ]


def _build_plan_document(
    *,
    status: str,
    plan_status: str,
    reason_code: str,
    provider_identity_binding_hash: str | None,
    source_binding_exactly_verified: bool,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    document = {
        "schema_version": PROVIDER_CONFORMANCE_PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "plan_status": plan_status,
        "reason_code": reason_code,
        "permission_state": "BLOCKED",
        "provider_identity_binding_hash": provider_identity_binding_hash,
        "target": {
            "adapter_protocol_version": PORT_V2_PROTOCOL_VERSION,
            "anti_replay_namespace": SOURCE_NAMESPACE,
            "request_schema_version": REQUEST_SCHEMA_VERSION,
            "command_schema_version": COMMAND_SCHEMA_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "receipt_schema_version": TARGET_RECEIPT_SCHEMA_VERSION,
        },
        "cases": cases,
        "facts": {
            "source_binding_exactly_verified": source_binding_exactly_verified,
            "case_count": len(cases),
            "executed_case_count": 0,
            "passed_case_count": 0,
            "provider_bound": False,
            "provider_endpoint_embedded": False,
            "provider_credentials_embedded": False,
            "provider_called": False,
            "network_accessed": False,
            "registry_identity_verified": False,
            "external_source_trust_verified": False,
            "provider_conformance_verified": False,
            "atomic_compare_and_consume_verified": False,
            "linearizability_verified": False,
            "durable_commit_verified": False,
            "authenticated_consumption_receipt_issued": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "provider_call_allowed": False,
            "writer_allowed": False,
            "runtime_gate_activation_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "conformance_plan_hash")


def _unknown_plan(reason_code: str) -> dict[str, Any]:
    return _build_plan_document(
        status="UNKNOWN",
        plan_status="UNKNOWN",
        reason_code=reason_code,
        provider_identity_binding_hash=None,
        source_binding_exactly_verified=False,
        cases=[],
    )


def build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> dict[str, Any]:
    if not verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    ):
        return _unknown_plan("PROVIDER_IDENTITY_BINDING_NOT_EXACT")
    if provider_identity_binding_document.get("status") != "BLOCKED":
        return _unknown_plan("PROVIDER_IDENTITY_BINDING_STATUS_INVALID")
    return _build_plan_document(
        status="BLOCKED",
        plan_status="PREREGISTERED_NOT_RUN",
        reason_code="V2_CONFORMANCE_CASES_PREREGISTERED_EXTERNAL_PROVIDER_UNBOUND",
        provider_identity_binding_hash=provider_identity_binding_document[
            "provider_identity_binding_hash"
        ],
        source_binding_exactly_verified=True,
        cases=expected_source_baseline_nonce_anti_replay_provider_conformance_cases_v2(),
    )


def verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
    document: Any,
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    rebuilt = build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    return strict_json_contract_equal(dict(document), rebuilt)
