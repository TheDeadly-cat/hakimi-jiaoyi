"""Detached signed multi-authority trusted-clock evidence contract v3.

This module verifies local cryptographic and policy facts only.  It does not
authenticate the real-world operators behind registered keys, establish a
trusted current time, or grant paper/live trading permission.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


REGISTRATION_SCHEMA_VERSION = "trusted-clock-authority-registration-v3"
RECEIPT_SCHEMA_VERSION = "trusted-clock-authority-receipt-v3"
ATTESTATION_SCHEMA_VERSION = "trusted-clock-authority-attestation-v3"
STATIC_FINGERPRINT = "20260822-signed-trusted-clock-authority-3"
KEY_ROLE = "TRUSTED_TIME_AUTHORITY"
SIGNATURE_DOMAIN = "hakimi.trusted-clock.authority-receipt.v3"
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "RFC8785_JCS_UTF8_RESTRICTED_SCHEMA"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
REFERENCE_POLICY = "MEDIAN_LOW_REGISTERED_SIGNED_SOURCES_V1"
VERIFICATION_STATE = (
    "SIGNED_MULTI_AUTHORITY_TIME_QUORUM_VERIFIED_"
    "EXTERNAL_AUTHORITY_TRUST_UNPROVEN"
)

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TrustedClockAuthorityContractError(ValueError):
    """Raised when a v3 contract input is malformed or unverifiable."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TrustedClockAuthorityContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != expected:
        raise TrustedClockAuthorityContractError(f"{label} keys do not match schema")
    return result


def _require_sequence(value: Any, label: str) -> list[Any] | tuple[Any, ...]:
    if type(value) not in (list, tuple):
        raise TrustedClockAuthorityContractError(f"{label} must be a list or tuple")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        raise TrustedClockAuthorityContractError(f"{label} is not a valid identifier")
    return value


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise TrustedClockAuthorityContractError(f"{label} must be lowercase sha256")
    return value


def _require_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise TrustedClockAuthorityContractError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise TrustedClockAuthorityContractError(f"{label} is below its minimum")
    return value


def _validate_json_tree(value: Any, label: str = "payload") -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for item in value:
            _validate_json_tree(item, label)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TrustedClockAuthorityContractError(f"{label} has a non-string key")
            _validate_json_tree(item, label)
        return
    raise TrustedClockAuthorityContractError(f"{label} has a non-contract JSON value")


def _canonical_bytes(value: Any) -> bytes:
    _validate_json_tree(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result[field] = _sha256_bytes(_canonical_bytes(payload))
    return result


def _verify_seal(payload: dict[str, Any], field: str, label: str) -> None:
    claimed = _require_hash(payload.get(field), field)
    unsigned = {key: copy.deepcopy(value) for key, value in payload.items() if key != field}
    actual = _sha256_bytes(_canonical_bytes(unsigned))
    if claimed != actual:
        raise TrustedClockAuthorityContractError(f"{label} seal mismatch")


def _decode_base64(value: Any, label: str, *, expected_length: int) -> bytes:
    if type(value) is not str:
        raise TrustedClockAuthorityContractError(f"{label} must be base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TrustedClockAuthorityContractError(f"{label} is not valid base64") from exc
    if len(decoded) != expected_length:
        raise TrustedClockAuthorityContractError(f"{label} has the wrong byte length")
    if base64.b64encode(decoded).decode("ascii") != value:
        raise TrustedClockAuthorityContractError(f"{label} is not canonical base64")
    return decoded


def _claim_limits() -> dict[str, bool]:
    return {
        "local_registration_integrity": True,
        "external_authority_trust_verified": False,
        "registration_governance_verified": False,
        "verification_time_source_trusted": False,
        "request_nonce_uniqueness_verified": False,
        "replay_registry_verified": False,
        "current_time_established": False,
        "profitability_proven": False,
    }


def _permission() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "current_activation_authorized": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
    }


def build_trusted_clock_authority_registration_v3(
    authorities: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    minimum_sources: int,
    max_receipt_age_ms: int,
    max_provider_spread_ms: int,
    max_local_skew_ms: int,
    max_receipt_issue_delay_ms: int,
    valid_from_ms: int,
    valid_until_ms: int,
    declared_at_ms: int,
) -> dict[str, Any]:
    """Build a hash-sealed local registration without retaining raw keys."""

    source = _require_sequence(authorities, "authorities")
    if not 2 <= len(source) <= 16:
        raise TrustedClockAuthorityContractError("authorities must contain 2 through 16 entries")

    normalized: list[dict[str, str]] = []
    authority_ids: set[str] = set()
    key_ids: set[str] = set()
    public_key_hashes: set[str] = set()
    expected_input_keys = {"authority_id", "key_id", "public_key_base64"}
    for index, raw_entry in enumerate(source):
        entry = _require_exact_keys(raw_entry, expected_input_keys, f"authorities[{index}]")
        authority_id = _require_identifier(entry["authority_id"], "authority_id")
        key_id = _require_identifier(entry["key_id"], "key_id")
        public_key = _decode_base64(
            entry["public_key_base64"], "public_key_base64", expected_length=32
        )
        public_key_sha256 = _sha256_bytes(public_key)
        if authority_id in authority_ids:
            raise TrustedClockAuthorityContractError("authority_id values must be unique")
        if key_id in key_ids:
            raise TrustedClockAuthorityContractError("key_id values must be unique")
        if public_key_sha256 in public_key_hashes:
            raise TrustedClockAuthorityContractError("public keys must be unique")
        authority_ids.add(authority_id)
        key_ids.add(key_id)
        public_key_hashes.add(public_key_sha256)
        normalized.append(
            {
                "authority_id": authority_id,
                "key_id": key_id,
                "public_key_sha256": public_key_sha256,
            }
        )
    normalized.sort(key=lambda item: item["authority_id"])

    minimum = _require_int(minimum_sources, "minimum_sources", minimum=2)
    if minimum > len(normalized):
        raise TrustedClockAuthorityContractError("minimum_sources exceeds authority count")
    age = _require_int(max_receipt_age_ms, "max_receipt_age_ms", minimum=1)
    spread = _require_int(max_provider_spread_ms, "max_provider_spread_ms", minimum=0)
    skew = _require_int(max_local_skew_ms, "max_local_skew_ms", minimum=0)
    issue_delay = _require_int(
        max_receipt_issue_delay_ms, "max_receipt_issue_delay_ms", minimum=0
    )
    declared = _require_int(declared_at_ms, "declared_at_ms", minimum=0)
    valid_from = _require_int(valid_from_ms, "valid_from_ms", minimum=0)
    valid_until = _require_int(valid_until_ms, "valid_until_ms", minimum=0)
    if not declared <= valid_from < valid_until:
        raise TrustedClockAuthorityContractError("registration validity ordering is invalid")

    payload: dict[str, Any] = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "key_role": KEY_ROLE,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "authorities": normalized,
        "policy": {
            "minimum_sources": minimum,
            "max_receipt_age_ms": age,
            "max_provider_spread_ms": spread,
            "max_local_skew_ms": skew,
            "max_receipt_issue_delay_ms": issue_delay,
            "reference_policy": REFERENCE_POLICY,
        },
        "validity": {
            "declared_at_ms": declared,
            "valid_from_ms": valid_from,
            "valid_until_ms": valid_until,
        },
        "claim_limits": _claim_limits(),
        "permission": _permission(),
    }
    return _seal(payload, "registration_hash")


def _validate_registration_seal_only(registration: Any) -> dict[str, Any]:
    expected = {
        "schema_version",
        "static_fingerprint",
        "key_role",
        "signature_algorithm",
        "authorities",
        "policy",
        "validity",
        "claim_limits",
        "permission",
        "registration_hash",
    }
    value = _require_exact_keys(registration, expected, "registration")
    if value["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise TrustedClockAuthorityContractError("registration schema mismatch")
    if value["static_fingerprint"] != STATIC_FINGERPRINT:
        raise TrustedClockAuthorityContractError("registration fingerprint mismatch")
    if value["key_role"] != KEY_ROLE or value["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise TrustedClockAuthorityContractError("registration cryptographic role mismatch")
    if value["claim_limits"] != _claim_limits() or value["permission"] != _permission():
        raise TrustedClockAuthorityContractError("registration claim limits were inflated")

    authorities = _require_sequence(value["authorities"], "registration.authorities")
    if not 2 <= len(authorities) <= 16:
        raise TrustedClockAuthorityContractError("registered authority count is invalid")
    authority_ids: set[str] = set()
    key_ids: set[str] = set()
    key_hashes: set[str] = set()
    previous_id: str | None = None
    for index, raw_entry in enumerate(authorities):
        entry = _require_exact_keys(
            raw_entry,
            {"authority_id", "key_id", "public_key_sha256"},
            f"registration.authorities[{index}]",
        )
        authority_id = _require_identifier(entry["authority_id"], "authority_id")
        key_id = _require_identifier(entry["key_id"], "key_id")
        key_hash = _require_hash(entry["public_key_sha256"], "public_key_sha256")
        if previous_id is not None and authority_id <= previous_id:
            raise TrustedClockAuthorityContractError("registered authorities are not canonically ordered")
        if authority_id in authority_ids or key_id in key_ids or key_hash in key_hashes:
            raise TrustedClockAuthorityContractError("registered authority identities are not unique")
        authority_ids.add(authority_id)
        key_ids.add(key_id)
        key_hashes.add(key_hash)
        previous_id = authority_id

    policy = _require_exact_keys(
        value["policy"],
        {
            "minimum_sources",
            "max_receipt_age_ms",
            "max_provider_spread_ms",
            "max_local_skew_ms",
            "max_receipt_issue_delay_ms",
            "reference_policy",
        },
        "registration.policy",
    )
    minimum = _require_int(policy["minimum_sources"], "minimum_sources", minimum=2)
    if minimum > len(authorities):
        raise TrustedClockAuthorityContractError("registered minimum_sources is invalid")
    _require_int(policy["max_receipt_age_ms"], "max_receipt_age_ms", minimum=1)
    _require_int(policy["max_provider_spread_ms"], "max_provider_spread_ms", minimum=0)
    _require_int(policy["max_local_skew_ms"], "max_local_skew_ms", minimum=0)
    _require_int(
        policy["max_receipt_issue_delay_ms"], "max_receipt_issue_delay_ms", minimum=0
    )
    if policy["reference_policy"] != REFERENCE_POLICY:
        raise TrustedClockAuthorityContractError("reference policy mismatch")

    validity = _require_exact_keys(
        value["validity"],
        {"declared_at_ms", "valid_from_ms", "valid_until_ms"},
        "registration.validity",
    )
    declared = _require_int(validity["declared_at_ms"], "declared_at_ms", minimum=0)
    valid_from = _require_int(validity["valid_from_ms"], "valid_from_ms", minimum=0)
    valid_until = _require_int(validity["valid_until_ms"], "valid_until_ms", minimum=0)
    if not declared <= valid_from < valid_until:
        raise TrustedClockAuthorityContractError("registration validity ordering is invalid")
    _verify_seal(value, "registration_hash", "registration")
    return value


def _normalize_public_keys(
    registration: dict[str, Any], authority_public_keys_by_id: Any
) -> dict[str, bytes]:
    supplied = _require_dict(authority_public_keys_by_id, "authority_public_keys_by_id")
    registered = {entry["authority_id"]: entry for entry in registration["authorities"]}
    if set(supplied) != set(registered):
        raise TrustedClockAuthorityContractError("public key map must exactly match registration")
    result: dict[str, bytes] = {}
    for authority_id, entry in registered.items():
        raw = _decode_base64(
            supplied[authority_id], f"public key for {authority_id}", expected_length=32
        )
        if _sha256_bytes(raw) != entry["public_key_sha256"]:
            raise TrustedClockAuthorityContractError("registered public key hash mismatch")
        result[authority_id] = raw
    return result


def _validate_registration(
    registration: Any,
    authority_public_keys_by_id: Any,
    expected_registration_hash: Any,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    value = _validate_registration_seal_only(registration)
    expected_hash = _require_hash(expected_registration_hash, "expected_registration_hash")
    if value["registration_hash"] != expected_hash:
        raise TrustedClockAuthorityContractError("expected registration hash mismatch")
    keys = _normalize_public_keys(value, authority_public_keys_by_id)
    rebuild_authorities = [
        {
            "authority_id": entry["authority_id"],
            "key_id": entry["key_id"],
            "public_key_base64": authority_public_keys_by_id[entry["authority_id"]],
        }
        for entry in value["authorities"]
    ]
    rebuilt = build_trusted_clock_authority_registration_v3(
        rebuild_authorities,
        minimum_sources=value["policy"]["minimum_sources"],
        max_receipt_age_ms=value["policy"]["max_receipt_age_ms"],
        max_provider_spread_ms=value["policy"]["max_provider_spread_ms"],
        max_local_skew_ms=value["policy"]["max_local_skew_ms"],
        max_receipt_issue_delay_ms=value["policy"]["max_receipt_issue_delay_ms"],
        valid_from_ms=value["validity"]["valid_from_ms"],
        valid_until_ms=value["validity"]["valid_until_ms"],
        declared_at_ms=value["validity"]["declared_at_ms"],
    )
    if rebuilt != value:
        raise TrustedClockAuthorityContractError("registration does not rebuild exactly")
    return value, keys


def verify_trusted_clock_authority_registration_v3(
    registration: Any,
    authority_public_keys_by_id: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    """Fully reverify a local registration and its caller-pinned key material."""

    try:
        _validate_registration(
            registration, authority_public_keys_by_id, expected_registration_hash
        )
    except TrustedClockAuthorityContractError:
        return False
    return True


def build_unsigned_trusted_clock_authority_receipt_v3(
    registration: Any,
    *,
    authority_id: Any,
    key_id: Any,
    request_nonce_hash: Any,
    request_context_hash: Any,
    observed_at_ms: Any,
    issued_at_ms: Any,
) -> dict[str, Any]:
    """Build the exact receipt payload that an external signer must sign."""

    registered = _validate_registration_seal_only(registration)
    wanted_authority = _require_identifier(authority_id, "authority_id")
    wanted_key = _require_identifier(key_id, "key_id")
    nonce_hash = _require_hash(request_nonce_hash, "request_nonce_hash")
    context_hash = _require_hash(request_context_hash, "request_context_hash")
    observed = _require_int(observed_at_ms, "observed_at_ms", minimum=0)
    issued = _require_int(issued_at_ms, "issued_at_ms", minimum=0)
    if observed > issued:
        raise TrustedClockAuthorityContractError("receipt was issued before observation")
    validity = registered["validity"]
    if not validity["valid_from_ms"] <= observed <= issued <= validity["valid_until_ms"]:
        raise TrustedClockAuthorityContractError("receipt lies outside registration validity")
    if issued - observed > registered["policy"]["max_receipt_issue_delay_ms"]:
        raise TrustedClockAuthorityContractError("receipt issue delay exceeds policy")

    matching = [
        entry
        for entry in registered["authorities"]
        if entry["authority_id"] == wanted_authority and entry["key_id"] == wanted_key
    ]
    if len(matching) != 1:
        raise TrustedClockAuthorityContractError("authority/key pair is not registered")
    authority = matching[0]
    payload: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registered["registration_hash"],
        "authority": {
            "authority_id": authority["authority_id"],
            "key_id": authority["key_id"],
            "public_key_sha256": authority["public_key_sha256"],
            "key_role": KEY_ROLE,
        },
        "request": {
            "nonce_hash": nonce_hash,
            "context_hash": context_hash,
        },
        "time": {
            "observed_at_ms": observed,
            "issued_at_ms": issued,
        },
        "signature_contract": {
            "domain": SIGNATURE_DOMAIN,
            "algorithm": SIGNATURE_ALGORITHM,
            "encoding": RECEIPT_ENCODING,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
    }
    return _seal(payload, "receipt_content_hash")


_UNSIGNED_RECEIPT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "authority",
    "request",
    "time",
    "signature_contract",
    "receipt_content_hash",
}


def _validate_unsigned_receipt(
    registration: dict[str, Any], unsigned_receipt: Any
) -> dict[str, Any]:
    value = _require_exact_keys(unsigned_receipt, _UNSIGNED_RECEIPT_KEYS, "unsigned_receipt")
    if value["schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise TrustedClockAuthorityContractError("receipt schema mismatch")
    if value["static_fingerprint"] != STATIC_FINGERPRINT:
        raise TrustedClockAuthorityContractError("receipt fingerprint mismatch")
    if value["registration_hash"] != registration["registration_hash"]:
        raise TrustedClockAuthorityContractError("receipt registration hash mismatch")
    authority = _require_exact_keys(
        value["authority"],
        {"authority_id", "key_id", "public_key_sha256", "key_role"},
        "receipt.authority",
    )
    request = _require_exact_keys(
        value["request"], {"nonce_hash", "context_hash"}, "receipt.request"
    )
    timing = _require_exact_keys(
        value["time"], {"observed_at_ms", "issued_at_ms"}, "receipt.time"
    )
    signature_contract = _require_exact_keys(
        value["signature_contract"],
        {"domain", "algorithm", "encoding", "message_format"},
        "receipt.signature_contract",
    )
    expected_signature_contract = {
        "domain": SIGNATURE_DOMAIN,
        "algorithm": SIGNATURE_ALGORITHM,
        "encoding": RECEIPT_ENCODING,
        "message_format": SIGNATURE_MESSAGE_FORMAT,
    }
    if authority["key_role"] != KEY_ROLE:
        raise TrustedClockAuthorityContractError("receipt key role mismatch")
    if signature_contract != expected_signature_contract:
        raise TrustedClockAuthorityContractError("receipt signature contract mismatch")
    _require_hash(authority["public_key_sha256"], "public_key_sha256")
    rebuilt = build_unsigned_trusted_clock_authority_receipt_v3(
        registration,
        authority_id=authority["authority_id"],
        key_id=authority["key_id"],
        request_nonce_hash=request["nonce_hash"],
        request_context_hash=request["context_hash"],
        observed_at_ms=timing["observed_at_ms"],
        issued_at_ms=timing["issued_at_ms"],
    )
    if rebuilt != value:
        raise TrustedClockAuthorityContractError("unsigned receipt does not rebuild exactly")
    return value


def assemble_trusted_clock_authority_receipt_v3(
    registration: Any,
    unsigned_receipt: Any,
    signature_base64: Any,
) -> dict[str, Any]:
    """Attach a detached Ed25519 signature without accepting signer secrets."""

    registered = _validate_registration_seal_only(registration)
    unsigned = _validate_unsigned_receipt(registered, unsigned_receipt)
    signature = _decode_base64(signature_base64, "signature_base64", expected_length=64)
    payload = copy.deepcopy(unsigned)
    payload["signature"] = {
        "signature_base64": signature_base64,
        "signature_sha256": _sha256_bytes(signature),
    }
    return _seal(payload, "receipt_hash")


_SIGNED_RECEIPT_KEYS = _UNSIGNED_RECEIPT_KEYS | {"signature", "receipt_hash"}


def _validate_signed_receipt(
    registration: dict[str, Any], signed_receipt: Any
) -> tuple[dict[str, Any], bytes]:
    value = _require_exact_keys(signed_receipt, _SIGNED_RECEIPT_KEYS, "signed_receipt")
    unsigned = {key: copy.deepcopy(value[key]) for key in _UNSIGNED_RECEIPT_KEYS}
    _validate_unsigned_receipt(registration, unsigned)
    signature_data = _require_exact_keys(
        value["signature"], {"signature_base64", "signature_sha256"}, "receipt.signature"
    )
    signature = _decode_base64(
        signature_data["signature_base64"], "signature_base64", expected_length=64
    )
    if signature_data["signature_sha256"] != _sha256_bytes(signature):
        raise TrustedClockAuthorityContractError("signature hash mismatch")
    _verify_seal(value, "receipt_hash", "signed receipt")
    return value, signature


def evaluate_trusted_clock_authority_v3(
    registration: Any,
    receipts: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    authority_public_keys_by_id: Any,
    *,
    expected_registration_hash: Any,
    expected_receipt_hashes: Any,
    request_nonce_hash: Any,
    request_context_hash: Any,
    verification_time_ms: Any,
) -> dict[str, Any]:
    """Verify signed local evidence and return a deliberately bounded attestation."""

    registered, public_keys = _validate_registration(
        registration, authority_public_keys_by_id, expected_registration_hash
    )
    supplied_receipts = _require_sequence(receipts, "receipts")
    if not 1 <= len(supplied_receipts) <= len(registered["authorities"]):
        raise TrustedClockAuthorityContractError("receipt count is invalid")
    if len(supplied_receipts) < registered["policy"]["minimum_sources"]:
        raise TrustedClockAuthorityContractError("signed receipt quorum is not met")
    nonce_hash = _require_hash(request_nonce_hash, "request_nonce_hash")
    context_hash = _require_hash(request_context_hash, "request_context_hash")
    verification_time = _require_int(
        verification_time_ms, "verification_time_ms", minimum=0
    )
    validity = registered["validity"]
    if not validity["valid_from_ms"] <= verification_time <= validity["valid_until_ms"]:
        raise TrustedClockAuthorityContractError("verification time lies outside registration validity")

    expected_hashes = _require_dict(expected_receipt_hashes, "expected_receipt_hashes")
    normalized_expected: dict[str, str] = {}
    for authority_id, receipt_hash in expected_hashes.items():
        normalized_id = _require_identifier(authority_id, "expected receipt authority_id")
        normalized_expected[normalized_id] = _require_hash(
            receipt_hash, "expected receipt hash"
        )

    registered_by_id = {
        entry["authority_id"]: entry for entry in registered["authorities"]
    }
    seen: set[str] = set()
    observations: list[int] = []
    source_receipts: list[dict[str, Any]] = []
    for raw_receipt in supplied_receipts:
        receipt, signature = _validate_signed_receipt(registered, raw_receipt)
        authority = receipt["authority"]
        authority_id = authority["authority_id"]
        if authority_id in seen:
            raise TrustedClockAuthorityContractError("duplicate authority receipt")
        if authority_id not in registered_by_id:
            raise TrustedClockAuthorityContractError("receipt authority is not registered")
        seen.add(authority_id)
        expected_authority = registered_by_id[authority_id]
        if (
            authority["key_id"] != expected_authority["key_id"]
            or authority["public_key_sha256"] != expected_authority["public_key_sha256"]
        ):
            raise TrustedClockAuthorityContractError("receipt authority binding mismatch")
        if receipt["request"] != {
            "nonce_hash": nonce_hash,
            "context_hash": context_hash,
        }:
            raise TrustedClockAuthorityContractError("receipt request binding mismatch")
        if normalized_expected.get(authority_id) != receipt["receipt_hash"]:
            raise TrustedClockAuthorityContractError("expected receipt hash mismatch")

        timing = receipt["time"]
        issued = timing["issued_at_ms"]
        observed = timing["observed_at_ms"]
        if issued > verification_time:
            raise TrustedClockAuthorityContractError("receipt was issued after verification time")
        if verification_time - issued > registered["policy"]["max_receipt_age_ms"]:
            raise TrustedClockAuthorityContractError("receipt is stale against supplied time")
        try:
            Ed25519PublicKey.from_public_bytes(public_keys[authority_id]).verify(
                signature, bytes.fromhex(receipt["receipt_content_hash"])
            )
        except InvalidSignature as exc:
            raise TrustedClockAuthorityContractError("receipt signature verification failed") from exc
        observations.append(observed)
        source_receipts.append(
            {
                "authority_id": authority_id,
                "key_id": authority["key_id"],
                "public_key_sha256": authority["public_key_sha256"],
                "receipt_hash": receipt["receipt_hash"],
                "signature_sha256": receipt["signature"]["signature_sha256"],
                "observed_at_ms": observed,
                "issued_at_ms": issued,
            }
        )
    if set(normalized_expected) != seen:
        raise TrustedClockAuthorityContractError("expected receipt hash map is not exact")

    ordered_observations = sorted(observations)
    provider_spread = ordered_observations[-1] - ordered_observations[0]
    if provider_spread > registered["policy"]["max_provider_spread_ms"]:
        raise TrustedClockAuthorityContractError("signed provider spread exceeds policy")
    reference_time = ordered_observations[(len(ordered_observations) - 1) // 2]
    local_skew = abs(verification_time - reference_time)
    if local_skew > registered["policy"]["max_local_skew_ms"]:
        raise TrustedClockAuthorityContractError("local skew exceeds policy")

    source_receipts.sort(key=lambda item: item["authority_id"])
    payload: dict[str, Any] = {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_lineage": {
            "registration_hash": registered["registration_hash"],
            "receipt_hashes_by_authority_id": {
                authority_id: normalized_expected[authority_id]
                for authority_id in sorted(normalized_expected)
            },
            "request_nonce_hash": nonce_hash,
            "request_context_hash": context_hash,
        },
        "verification": {
            "status": "PASS",
            "state": VERIFICATION_STATE,
            "source_count": len(source_receipts),
            "minimum_sources": registered["policy"]["minimum_sources"],
            "verification_time_ms": verification_time,
            "reference_time_ms": reference_time,
            "reference_policy": REFERENCE_POLICY,
            "provider_spread_ms": provider_spread,
            "local_skew_ms": local_skew,
        },
        "source_receipts": source_receipts,
        "facts": {
            "registration_integrity_verified": True,
            "registered_public_key_hashes_verified": True,
            "detached_signatures_verified": True,
            "multi_authority_quorum_verified": True,
            "receipt_age_against_supplied_time_checked": True,
            "provider_spread_checked": True,
            "local_skew_checked": True,
            "external_time_authority_trust_verified": False,
            "registration_governance_verified": False,
            "verification_time_source_trusted": False,
            "request_nonce_uniqueness_verified": False,
            "replay_registry_verified": False,
            "current_time_established": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
            "profitability_proven": False,
        },
        "blockers": [
            "EXTERNAL_TIME_AUTHORITY_TRUST_UNPROVEN",
            "REGISTRATION_GOVERNANCE_UNPROVEN",
            "VERIFICATION_TIME_SOURCE_UNTRUSTED",
            "REQUEST_NONCE_UNIQUENESS_UNPROVEN",
            "REPLAY_REGISTRY_UNPROVEN",
            "CURRENT_TIME_NOT_ESTABLISHED",
            "PAPER_LIVE_PERMISSION_DENIED",
        ],
        "permission": _permission(),
    }
    return _seal(payload, "attestation_hash")


def verify_trusted_clock_authority_attestation_v3(
    attestation: Any,
    registration: Any,
    receipts: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    authority_public_keys_by_id: Any,
    *,
    expected_registration_hash: Any,
    expected_receipt_hashes: Any,
    request_nonce_hash: Any,
    request_context_hash: Any,
    verification_time_ms: Any,
) -> bool:
    """Rebuild the full result from signed inputs; never trust its seal alone."""

    try:
        rebuilt = evaluate_trusted_clock_authority_v3(
            registration,
            receipts,
            authority_public_keys_by_id,
            expected_registration_hash=expected_registration_hash,
            expected_receipt_hashes=expected_receipt_hashes,
            request_nonce_hash=request_nonce_hash,
            request_context_hash=request_context_hash,
            verification_time_ms=verification_time_ms,
        )
    except TrustedClockAuthorityContractError:
        return False
    return type(attestation) is dict and attestation == rebuilt


__all__ = [
    "ATTESTATION_SCHEMA_VERSION",
    "KEY_ROLE",
    "RECEIPT_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_MESSAGE_FORMAT",
    "STATIC_FINGERPRINT",
    "TrustedClockAuthorityContractError",
    "VERIFICATION_STATE",
    "assemble_trusted_clock_authority_receipt_v3",
    "build_trusted_clock_authority_registration_v3",
    "build_unsigned_trusted_clock_authority_receipt_v3",
    "evaluate_trusted_clock_authority_v3",
    "verify_trusted_clock_authority_attestation_v3",
    "verify_trusted_clock_authority_registration_v3",
]
