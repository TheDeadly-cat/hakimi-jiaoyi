"""Preregistered-key signed replay-cursor provider receipt for ADR0478."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1
    as signed_registration,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as provider_port,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


RECEIPT_CLAIM_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-receipt-claim-v1"
)
SIGNED_RECEIPT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-signed-receipt-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-signed-receipt-verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260825-replay-cursor-provider-signed-receipt-v1-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "RAW_RECEIPT_CLAIM_SHA256_DIGEST_BYTES_V1"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.incumbent-snapshot.replay-cursor."
    "provider-receipt.v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_RECEIPT_CANONICAL_BYTES = 8192
_MAX_JSON_DEPTH = 6
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "provider_activation_allowed",
    "provider_identity_trust_allowed",
    "runtime_gate_activation_allowed",
    "replay_cursor_commit_trust_allowed",
    "trading_allowed",
    "writer_allowed",
)
_SOURCE_TRUTH_BLOCKERS = (
    "PROVIDER_IDENTITY_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "PROVIDER_REGISTRATION_UNVERIFIED",
    "ACTUAL_PROVIDER_INVOCATION_UNVERIFIED",
    "EXTERNAL_ATOMIC_COMPARE_AND_ADVANCE_UNVERIFIED",
    "DURABLE_COMMIT_UNVERIFIED",
    "LINEARIZABLE_READ_AFTER_WRITE_UNVERIFIED",
    "ROLLBACK_RESISTANCE_UNVERIFIED",
    "CONSUME_ONCE_SEMANTICS_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _normalize_json(value: Any, *, depth: int = 0) -> Any:
    if depth > _MAX_JSON_DEPTH:
        raise ValueError("provider receipt JSON exceeds the depth limit")
    if isinstance(value, Enum):
        return _normalize_json(value.value, depth=depth + 1)
    if value is None or type(value) in (bool, int, str):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _normalize_json(
                getattr(value, item.name), depth=depth + 1
            )
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            if type(key) is not str or not key:
                raise ValueError("provider receipt keys must be non-empty strings")
            normalized[key] = _normalize_json(
                value[key], depth=depth + 1
            )
        return normalized
    if type(value) in (list, tuple):
        return [
            _normalize_json(item, depth=depth + 1) for item in value
        ]
    raise ValueError("provider receipt contains a non-JSON contract value")


def _bounded_receipt_hash(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _normalize_json(value)
    encoded = json.dumps(
        normalized,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    if len(encoded) > _MAX_RECEIPT_CANONICAL_BYTES:
        raise ValueError("provider receipt exceeds the canonical byte limit")
    return strict_canonical_hash(
        {
            "schema_version": "bounded-provider-receipt-content-v1",
            "content": normalized,
        }
    )


def _dataclass_snapshot(value: Any, expected_type: type[Any]) -> dict[str, Any]:
    if type(value) is not expected_type or not is_dataclass(value):
        raise ValueError("provider command or result has an inexact type")
    projected: dict[str, Any] = {}
    for item in fields(value):
        raw = getattr(value, item.name)
        if "receipt" in item.name:
            projected[item.name] = {
                "present": raw is not None,
                "content_sha256": _bounded_receipt_hash(raw),
            }
        else:
            projected[item.name] = _normalize_json(raw)
    return projected


def _field_name(value: Any, exact: tuple[str, ...], terms: tuple[str, ...]) -> str:
    for name in exact:
        if hasattr(value, name):
            return name
    candidates = [
        item.name
        for item in fields(value)
        if all(term in item.name for term in terms)
    ]
    if len(candidates) != 1:
        raise ValueError("provider command/result cursor field is ambiguous")
    return candidates[0]


def _cursor_hash(value: Any, role: str) -> str:
    nested_name = {
        "base": "base_cursor",
        "proposed": "proposed_cursor",
    }.get(role)
    if nested_name is not None and hasattr(value, nested_name):
        nested_cursor = getattr(value, nested_name)
        return _require_hash(
            f"{nested_name}.cursor_hash",
            getattr(nested_cursor, "cursor_hash", None),
        )
    definitions = {
        "base": (
            (
                "base_cursor_hash",
                "expected_cursor_hash",
                "base_replay_cursor_hash",
                "expected_replay_cursor_hash",
            ),
            ("cursor", "hash"),
            ("base", "expected", "observed", "prior"),
        ),
        "proposed": (
            (
                "proposed_cursor_hash",
                "candidate_cursor_hash",
                "proposed_replay_cursor_hash",
                "candidate_replay_cursor_hash",
            ),
            ("cursor", "hash"),
            ("proposed", "candidate", "next"),
        ),
        "observed": (
            ("observed_cursor_hash", "observed_replay_cursor_hash"),
            ("cursor", "hash"),
            ("observed", "base", "prior"),
        ),
        "returned": (
            (
                "returned_cursor_hash",
                "returned_replay_cursor_hash",
                "resulting_cursor_hash",
            ),
            ("cursor", "hash"),
            ("returned", "resulting", "current", "committed"),
        ),
    }
    exact, required, role_terms = definitions[role]
    try:
        name = _field_name(value, exact, required + (role_terms[0],))
    except ValueError:
        candidates = [
            item.name
            for item in fields(value)
            if all(term in item.name for term in required)
            and any(term in item.name for term in role_terms)
        ]
        if len(candidates) != 1:
            raise ValueError(f"{role} replay cursor field is ambiguous")
        name = candidates[0]
    return _require_hash(name, getattr(value, name))


def _result_revision(provider_result: Any) -> int:
    preferred = (
        "returned_registry_revision",
        "returned_revision",
        "registry_revision",
        "revision",
    )
    for name in preferred:
        if hasattr(provider_result, name):
            value = getattr(provider_result, name)
            break
    else:
        candidates = [
            item.name
            for item in fields(provider_result)
            if "revision" in item.name
        ]
        if len(candidates) != 1:
            raise ValueError("provider result revision field is ambiguous")
        value = getattr(provider_result, candidates[0])
    if type(value) is not int or value < 0:
        raise ValueError("provider result revision must be a non-negative integer")
    return value


def _nested_strings(value: Any) -> tuple[str, ...]:
    if type(value) is str:
        return (value,)
    if isinstance(value, Mapping):
        result: list[str] = []
        for item in value.values():
            result.extend(_nested_strings(item))
        return tuple(result)
    if type(value) in (list, tuple):
        result = []
        for item in value:
            result.extend(_nested_strings(item))
        return tuple(result)
    return ()


def _validate_registration_context(
    registration_evidence_document: Any,
    signed_registration_document: Any,
    registration_claim_document: Any,
    preregistration_document: Any,
    *,
    expected_registration_evidence_hash: Any,
    registration_verification_kwargs: Any,
) -> tuple[Mapping[str, Any], str]:
    expected_hash = _require_hash(
        "expected_registration_evidence_hash",
        expected_registration_evidence_hash,
    )
    if (
        type(registration_evidence_document) is not dict
        or type(signed_registration_document) is not dict
        or type(registration_claim_document) is not dict
        or type(preregistration_document) is not dict
        or type(registration_verification_kwargs) is not dict
        or "expected_verification_evidence_hash"
        in registration_verification_kwargs
    ):
        raise ValueError("provider registration context has an inexact type")
    if not signed_registration.verify_signed_replay_cursor_provider_registration_evidence_v1(
        registration_evidence_document,
        signed_registration_document,
        registration_claim_document,
        preregistration_document,
        expected_verification_evidence_hash=expected_hash,
        **dict(registration_verification_kwargs),
    ):
        raise ValueError("provider signed registration evidence is not exact")
    identity = preregistration_document.get("identity")
    evidence_source = registration_evidence_document.get("source")
    if not isinstance(identity, Mapping) or not isinstance(
        evidence_source, Mapping
    ):
        raise ValueError("provider registration identity/source is missing")
    registry_id = identity.get("registry_id")
    key_hash = identity.get("public_key_spki_sha256")
    if (
        type(registry_id) is not str
        or not registry_id
        or not _is_hash(key_hash)
        or evidence_source.get("public_key_spki_sha256") != key_hash
        or SIGNED_RECEIPT_SCHEMA_VERSION
        not in _nested_strings(preregistration_document.get("source"))
    ):
        raise ValueError("provider preregistration receipt binding drifted")
    return identity, expected_hash


def _validate_operation(
    command: Any,
    provider_result: Any,
    registry_id: str,
) -> tuple[dict[str, Any], dict[str, Any], str, int]:
    command_snapshot = _dataclass_snapshot(
        command, provider_port.ReplayCursorCompareAndAdvanceCommandV1
    )
    result_snapshot = _dataclass_snapshot(
        provider_result,
        provider_port.ReplayCursorCompareAndAdvanceResultV1,
    )
    command_hash = _require_hash(
        "command.command_hash", getattr(command, "command_hash", None)
    )
    intent_hash = _require_hash(
        "command.intent_hash", getattr(command, "intent_hash", None)
    )
    if (
        getattr(provider_result, "command_hash", None) != command_hash
        or getattr(provider_result, "intent_hash", None) != intent_hash
        or getattr(provider_result, "registry_id", None) != registry_id
    ):
        raise ValueError("provider result does not bind the exact command")
    if hasattr(command, "registry_id") and command.registry_id != registry_id:
        raise ValueError("provider command registry identity drifted")
    outcome_raw = getattr(provider_result, "outcome", None)
    outcome = outcome_raw.value if isinstance(outcome_raw, Enum) else outcome_raw
    if outcome not in ("ADVANCED", "DUPLICATE_REJECTED", "CONFLICT_REJECTED"):
        raise ValueError("provider result outcome is unsupported")
    base_hash = _cursor_hash(command, "base")
    proposed_hash = _cursor_hash(command, "proposed")
    observed_hash = _cursor_hash(provider_result, "observed")
    returned_hash = _cursor_hash(provider_result, "returned")
    if outcome == "ADVANCED":
        if observed_hash != base_hash or returned_hash != proposed_hash:
            raise ValueError("ADVANCED result cursor transition is incoherent")
    elif returned_hash != observed_hash:
        raise ValueError("rejected result must not advance the replay cursor")
    return command_snapshot, result_snapshot, outcome, _result_revision(
        provider_result
    )


def build_replay_cursor_provider_receipt_claim_v1(
    command: Any,
    provider_result: Any,
    registration_evidence_document: Any,
    signed_registration_document: Any,
    registration_claim_document: Any,
    preregistration_document: Any,
    *,
    expected_registration_evidence_hash: Any,
    registration_verification_kwargs: Any,
) -> dict[str, Any]:
    identity, registration_evidence_hash = _validate_registration_context(
        registration_evidence_document,
        signed_registration_document,
        registration_claim_document,
        preregistration_document,
        expected_registration_evidence_hash=(
            expected_registration_evidence_hash
        ),
        registration_verification_kwargs=registration_verification_kwargs,
    )
    command_snapshot, result_snapshot, outcome, revision = (
        _validate_operation(command, provider_result, identity["registry_id"])
    )
    body = {
        "schema_version": RECEIPT_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": "PREREGISTERED_KEY_SIGNATURE_REQUIRED",
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "preregistration_hash": preregistration_document[
            "preregistration_hash"
        ],
        "registration_evidence_hash": registration_evidence_hash,
        "registration_claim_hash": registration_evidence_document["source"][
            "claim_hash"
        ],
        "signed_registration_hash": registration_evidence_document["source"][
            "signed_registration_hash"
        ],
        "public_key_spki_sha256": identity["public_key_spki_sha256"],
        "registry_id": identity["registry_id"],
        "command_hash": command.command_hash,
        "intent_hash": command.intent_hash,
        "provider_outcome": outcome,
        "returned_registry_revision": revision,
        "command_snapshot_sha256": strict_canonical_hash(
            {
                "schema_version": "replay-cursor-provider-command-snapshot-v1",
                "fields": command_snapshot,
            }
        ),
        "provider_result_snapshot_sha256": strict_canonical_hash(
            {
                "schema_version": "replay-cursor-provider-result-snapshot-v1",
                "fields": result_snapshot,
            }
        ),
        "command_snapshot": command_snapshot,
        "provider_result_snapshot": result_snapshot,
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(body, "receipt_claim_hash")


def build_signed_replay_cursor_provider_receipt_v1(
    receipt_claim_document: Any,
    command: Any,
    provider_result: Any,
    registration_evidence_document: Any,
    signed_registration_document: Any,
    registration_claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_receipt_claim_hash: Any,
    expected_registration_evidence_hash: Any,
    registration_verification_kwargs: Any,
) -> dict[str, Any]:
    expected_claim_hash = _require_hash(
        "expected_receipt_claim_hash", expected_receipt_claim_hash
    )
    expected_claim = build_replay_cursor_provider_receipt_claim_v1(
        command,
        provider_result,
        registration_evidence_document,
        signed_registration_document,
        registration_claim_document,
        preregistration_document,
        expected_registration_evidence_hash=(
            expected_registration_evidence_hash
        ),
        registration_verification_kwargs=registration_verification_kwargs,
    )
    if (
        expected_claim["receipt_claim_hash"] != expected_claim_hash
        or not strict_json_contract_equal(
            receipt_claim_document, expected_claim
        )
    ):
        raise ValueError("provider receipt claim is not exact")
    if type(public_key_spki_base64) is not str or not public_key_spki_base64:
        raise ValueError("public_key_spki_base64 must be non-empty")
    spki_bytes = decode_canonical_base64_v1(
        public_key_spki_base64, "public_key_spki_base64"
    )
    load_canonical_ed25519_public_key_v1(spki_bytes)
    if type(signature_base64) is not str or not signature_base64:
        raise ValueError("signature_base64 must be non-empty")
    signature = decode_canonical_base64_v1(
        signature_base64, "signature_base64"
    )
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must be exactly 64 bytes")
    body = {
        "schema_version": SIGNED_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_CANDIDATE",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_message_hash": expected_claim_hash,
        "signature_base64": signature_base64,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(spki_bytes).hexdigest(),
        "receipt_claim_hash": expected_claim_hash,
        "preregistration_hash": receipt_claim_document[
            "preregistration_hash"
        ],
        "registration_evidence_hash": (
            expected_registration_evidence_hash
        ),
        "registry_id": receipt_claim_document["registry_id"],
        "command_hash": receipt_claim_document["command_hash"],
        "intent_hash": receipt_claim_document["intent_hash"],
        "provider_outcome": receipt_claim_document["provider_outcome"],
        "returned_registry_revision": receipt_claim_document[
            "returned_registry_revision"
        ],
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(body, "signed_receipt_hash")


def evaluate_signed_replay_cursor_provider_receipt_v1(
    signed_receipt_document: Any,
    receipt_claim_document: Any,
    command: Any,
    provider_result: Any,
    registration_evidence_document: Any,
    signed_registration_document: Any,
    registration_claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_signed_receipt_hash: Any,
    expected_receipt_claim_hash: Any,
    expected_registration_evidence_hash: Any,
    registration_verification_kwargs: Any,
) -> dict[str, Any]:
    registration_evidence_exact = False
    operation_claim_exact = False
    signed_receipt_exact = False
    preregistered_key_hash_matches = False
    registration_and_receipt_key_match = False
    cryptographic_signature_verified = False
    signed_receipt_hash: str | None = None
    receipt_claim_hash: str | None = None
    public_key_hash: str | None = None
    try:
        expected_signed_receipt_hash = _require_hash(
            "expected_signed_receipt_hash", expected_signed_receipt_hash
        )
        expected_receipt_claim_hash = _require_hash(
            "expected_receipt_claim_hash", expected_receipt_claim_hash
        )
        expected_claim = build_replay_cursor_provider_receipt_claim_v1(
            command,
            provider_result,
            registration_evidence_document,
            signed_registration_document,
            registration_claim_document,
            preregistration_document,
            expected_registration_evidence_hash=(
                expected_registration_evidence_hash
            ),
            registration_verification_kwargs=(
                registration_verification_kwargs
            ),
        )
        registration_evidence_exact = True
        receipt_claim_hash = expected_claim["receipt_claim_hash"]
        operation_claim_exact = (
            receipt_claim_hash == expected_receipt_claim_hash
            and strict_json_contract_equal(
                receipt_claim_document, expected_claim
            )
        )
        expected_signed = build_signed_replay_cursor_provider_receipt_v1(
            receipt_claim_document,
            command,
            provider_result,
            registration_evidence_document,
            signed_registration_document,
            registration_claim_document,
            preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_receipt_claim_hash=expected_receipt_claim_hash,
            expected_registration_evidence_hash=(
                expected_registration_evidence_hash
            ),
            registration_verification_kwargs=(
                registration_verification_kwargs
            ),
        )
        signed_receipt_hash = expected_signed["signed_receipt_hash"]
        signed_receipt_exact = (
            signed_receipt_hash == expected_signed_receipt_hash
            and strict_json_contract_equal(
                signed_receipt_document, expected_signed
            )
        )
        spki_bytes = decode_canonical_base64_v1(
            public_key_spki_base64, "public_key_spki_base64"
        )
        public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
        signature = decode_canonical_base64_v1(
            signature_base64, "signature_base64"
        )
        if len(signature) != 64:
            raise ValueError("Ed25519 signature must be exactly 64 bytes")
        public_key_hash = sha256(spki_bytes).hexdigest()
        preregistered_key_hash_matches = (
            public_key_hash
            == preregistration_document["identity"][
                "public_key_spki_sha256"
            ]
        )
        registration_and_receipt_key_match = (
            public_key_hash
            == registration_evidence_document["source"][
                "public_key_spki_sha256"
            ]
        )
        try:
            public_key.verify(
                signature, bytes.fromhex(expected_receipt_claim_hash)
            )
            cryptographic_signature_verified = True
        except (InvalidSignature, ValueError):
            cryptographic_signature_verified = False
    except (KeyError, TypeError, ValueError):
        pass

    local_receipt_signature_verified = all(
        (
            registration_evidence_exact,
            operation_claim_exact,
            signed_receipt_exact,
            preregistered_key_hash_matches,
            registration_and_receipt_key_match,
            cryptographic_signature_verified,
        )
    )
    dynamic_blockers: list[str] = []
    for ok, blocker in (
        (
            registration_evidence_exact,
            "SIGNED_PROVIDER_REGISTRATION_EVIDENCE_NOT_EXACT",
        ),
        (operation_claim_exact, "PROVIDER_RECEIPT_CLAIM_NOT_EXACT"),
        (signed_receipt_exact, "SIGNED_PROVIDER_RECEIPT_NOT_EXACT"),
        (
            preregistered_key_hash_matches,
            "PREREGISTERED_PUBLIC_KEY_HASH_MISMATCH",
        ),
        (
            registration_and_receipt_key_match,
            "REGISTRATION_AND_RECEIPT_KEY_MISMATCH",
        ),
        (
            cryptographic_signature_verified,
            "ED25519_PROVIDER_RECEIPT_SIGNATURE_INVALID",
        ),
    ):
        if not ok:
            dynamic_blockers.append(blocker)

    body = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_receipt_signature_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "receipt_status": (
            "PREREGISTERED_KEY_RECEIPT_SIGNATURE_OBSERVED_LOCAL_ONLY"
            if local_receipt_signature_verified
            else "UNKNOWN"
        ),
        "decision": (
            "LOCAL_RECEIPT_SIGNATURE_VERIFIED_EXTERNAL_PROVIDER_SOURCE_TRUTH_BLOCKED"
            if local_receipt_signature_verified
            else "SIGNED_PROVIDER_RECEIPT_UNKNOWN_OR_INVALID"
        ),
        "blockers": dynamic_blockers + list(_SOURCE_TRUTH_BLOCKERS),
        "checks": [
            {
                "name": "signed_provider_registration_evidence_exact",
                "ok": registration_evidence_exact,
            },
            {
                "name": "operation_receipt_claim_exact",
                "ok": operation_claim_exact,
            },
            {
                "name": "signed_provider_receipt_exact",
                "ok": signed_receipt_exact,
            },
            {
                "name": "preregistered_public_key_hash_matches",
                "ok": preregistered_key_hash_matches,
            },
            {
                "name": "registration_and_receipt_key_match",
                "ok": registration_and_receipt_key_match,
            },
            {
                "name": "ed25519_provider_receipt_signature_verified",
                "ok": cryptographic_signature_verified,
            },
        ],
        "facts": {
            "signed_provider_registration_evidence_exact": (
                registration_evidence_exact
            ),
            "operation_command_and_result_exact": operation_claim_exact,
            "signed_provider_receipt_exact": signed_receipt_exact,
            "preregistered_key_hash_matched": (
                preregistered_key_hash_matches
            ),
            "same_key_observed_for_registration_and_receipt": (
                registration_and_receipt_key_match
            ),
            "cryptographic_receipt_signature_verified": (
                cryptographic_signature_verified
            ),
            "provider_key_possession_observed_local_only": (
                local_receipt_signature_verified
            ),
            "provider_identity_verified": False,
            "provider_implementation_verified": False,
            "provider_registered": False,
            "actual_provider_invocation_verified": False,
            "external_atomic_compare_and_advance_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "consume_once_semantics_verified": False,
            "replay_cursor_persistence_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "network_accessed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "source": {
            "preregistration_hash": (
                preregistration_document.get("preregistration_hash")
                if isinstance(preregistration_document, Mapping)
                else None
            ),
            "registration_evidence_hash": (
                expected_registration_evidence_hash
                if _is_hash(expected_registration_evidence_hash)
                else None
            ),
            "receipt_claim_hash": receipt_claim_hash,
            "signed_receipt_hash": signed_receipt_hash,
            "public_key_spki_sha256": public_key_hash,
        },
        "authority": _locked_authority(),
        "redaction": {
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "raw_provider_receipt_redacted": True,
            "raw_registration_documents_embedded": False,
            "raw_runtime_state_embedded": False,
        },
        "limitations": [
            "A valid local signature proves only possession of the preregistered key for the exact domain-separated receipt claim.",
            "It does not prove provider identity, registration, implementation, invocation, atomicity, durability, linearizability, rollback resistance, consume-once behavior, or persistence.",
            "No current, runtime, paper, live, writer, execution, profitability, or trading authority is granted.",
        ],
    }
    return seal_strict_canonical_document(body, "verification_evidence_hash")


def verify_signed_replay_cursor_provider_receipt_evidence_v1(
    evidence_document: Any,
    signed_receipt_document: Any,
    receipt_claim_document: Any,
    command: Any,
    provider_result: Any,
    registration_evidence_document: Any,
    signed_registration_document: Any,
    registration_claim_document: Any,
    preregistration_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_verification_evidence_hash):
        return False
    expected = evaluate_signed_replay_cursor_provider_receipt_v1(
        signed_receipt_document,
        receipt_claim_document,
        command,
        provider_result,
        registration_evidence_document,
        signed_registration_document,
        registration_claim_document,
        preregistration_document,
        **evaluation_kwargs,
    )
    return (
        expected["verification_evidence_hash"]
        == expected_verification_evidence_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "RECEIPT_CLAIM_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_MESSAGE_FORMAT",
    "SIGNED_RECEIPT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "build_replay_cursor_provider_receipt_claim_v1",
    "build_signed_replay_cursor_provider_receipt_v1",
    "evaluate_signed_replay_cursor_provider_receipt_v1",
    "verify_signed_replay_cursor_provider_receipt_evidence_v1",
]
