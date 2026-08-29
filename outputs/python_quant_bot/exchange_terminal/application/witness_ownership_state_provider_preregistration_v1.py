"""Fail-closed provider profile preregistration for ADR0413."""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import witness_ownership_state_service
from exchange_terminal.application.ports import (
    witness_ownership_state_store_v1 as witness_ownership_state_store,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "witness-ownership-state-provider-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-preregistration-v1-lock-1"
)
PROVIDER_PROTOCOL_VERSION = (
    "witness-ownership-state-compare-consume-and-advance-port-v1"
)
TARGET_SIGNED_RECEIPT_SCHEMA_VERSION = (
    "witness-ownership-state-provider-signed-receipt-v1"
)
PORT_IMPLEMENTATION_SHA256 = (
    "36a43ef91efcc472664c5b4bdc8519046532eb5a2d7c36fe398e9ac6262f72e8"
)
CONSUMER_IMPLEMENTATION_SHA256 = (
    "4b3c711e614416ce78bb62bd9cc28dce077f3b6e99fb20891be295557d40178c"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
STRICT_ED25519_PUBLIC_IMPLEMENTATION_SHA256 = (
    "cfba98df59681ff8318d8a5f70aa37cb9f277f3db12d2f4e33dc427c6fb882d9"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "provider_activation_allowed",
    "provider_identity_trust_allowed",
    "runtime_gate_activation_allowed",
    "signed_receipt_trust_allowed",
    "writer_allowed",
)
_BLOCKERS = (
    "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
    "PROVIDER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "DURABLE_ATOMIC_COMPARE_CONSUME_AND_ADVANCE_UNVERIFIED",
    "LINEARIZABLE_READ_AFTER_WRITE_UNVERIFIED",
    "ROLLBACK_RESISTANCE_UNVERIFIED",
    "SIGNED_PROVIDER_OPERATION_RECEIPT_MISSING",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _require_hash(name: str, value: Any) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_identifier(name: str, value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _require_claim(name: str, value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be a normalized non-empty claim")
    if len(value) > 256:
        raise ValueError(f"{name} exceeds its length bound")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must be ASCII") from exc
    return value


def build_witness_ownership_state_provider_preregistration_v1(
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    provider_implementation_claim_sha256: Any,
) -> dict[str, Any]:
    registry = _require_identifier("registry_id", registry_id)
    operator_claim = _require_claim(
        "operator_identity_claim", operator_identity_claim
    )
    public_key_hash = _require_hash(
        "public_key_spki_sha256", public_key_spki_sha256
    )
    domain = _require_identifier("trust_domain", trust_domain)
    implementation_claim = _require_hash(
        "provider_implementation_claim_sha256",
        provider_implementation_claim_sha256,
    )
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "PROVIDER_PROFILE_PREREGISTERED_IDENTITY_KEY_CONTROL_AND_"
            "EXTERNAL_CONFORMANCE_UNVERIFIED"
        ),
        "blockers": list(_BLOCKERS),
        "identity": {
            "registry_id": registry,
            "operator_identity_claim_hash": strict_canonical_hash(
                {"operator_identity_claim": operator_claim}
            ),
            "public_key_spki_sha256": public_key_hash,
            "trust_domain": domain,
            "provider_implementation_claim_sha256": implementation_claim,
        },
        "contract": {
            "namespace": (
                witness_ownership_state_store.WITNESS_OWNERSHIP_NAMESPACE
            ),
            "provider_protocol_version": PROVIDER_PROTOCOL_VERSION,
            "command_schema_version": (
                witness_ownership_state_store.COMMAND_SCHEMA_VERSION
            ),
            "result_schema_version": (
                witness_ownership_state_store.RESULT_SCHEMA_VERSION
            ),
            "receipt_claim_schema_version": (
                witness_ownership_state_store.RECEIPT_CLAIM_SCHEMA_VERSION
            ),
            "consumer_evaluation_schema_version": (
                witness_ownership_state_service.EVALUATION_SCHEMA_VERSION
            ),
            "target_signed_receipt_schema_version": (
                TARGET_SIGNED_RECEIPT_SCHEMA_VERSION
            ),
            "signature_algorithm": "ED25519",
            "signature_message_format": (
                "STRICT_CANONICAL_DOMAIN_SEPARATED_SHA256_DIGEST_BYTES_V1"
            ),
        },
        "source": {
            "port_implementation_sha256": PORT_IMPLEMENTATION_SHA256,
            "consumer_implementation_sha256": CONSUMER_IMPLEMENTATION_SHA256,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "strict_ed25519_public_implementation_sha256": (
                STRICT_ED25519_PUBLIC_IMPLEMENTATION_SHA256
            ),
        },
        "facts": {
            "provider_profile_preregistered": True,
            "provider_organization_identity_verified": False,
            "provider_key_control_continuity_verified": False,
            "provider_implementation_verified": False,
            "external_provider_conformance_verified": False,
            "signed_provider_receipt_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "runtime_assets_accessed": False,
            "network_accessed": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(body, "preregistration_hash")


def verify_witness_ownership_state_provider_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_witness_ownership_state_provider_preregistration_v1(
            **build_kwargs
        )
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "CONSUMER_IMPLEMENTATION_SHA256",
    "PORT_IMPLEMENTATION_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_PROTOCOL_VERSION",
    "STATIC_FINGERPRINT",
    "TARGET_SIGNED_RECEIPT_SCHEMA_VERSION",
    "build_witness_ownership_state_provider_preregistration_v1",
    "verify_witness_ownership_state_provider_preregistration_v1",
]
