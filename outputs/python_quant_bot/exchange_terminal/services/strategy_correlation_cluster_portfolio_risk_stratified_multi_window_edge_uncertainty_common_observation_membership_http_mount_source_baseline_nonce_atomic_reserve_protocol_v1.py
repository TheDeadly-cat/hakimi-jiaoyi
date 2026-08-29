"""Synthetic compare-and-swap protocol for nonce replay reservations.

The protocol is pure and unmounted.  It verifies an immutable state transition
and an Ed25519 signature over its receipt, but deliberately does not claim that
the returned state was persisted, serialized, or produced by a trusted registry.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_replay_snapshot_gate_v1 import (
    build_nonce_replay_key_v1,
)


STATIC_FINGERPRINT = "20260823-membership-nonce-atomic-reserve-protocol-1"
REGISTRY_SCOPE = "source-baseline-signed-review-attestation-v1"

REGISTRY_STATE_SCHEMA = (
    "strategy-correlation-cluster-nonce-registry-synthetic-state-v1"
)
RESERVE_REQUEST_SCHEMA = (
    "strategy-correlation-cluster-nonce-atomic-reserve-request-v1"
)
TRANSITION_RECEIPT_SCHEMA = (
    "strategy-correlation-cluster-nonce-atomic-reserve-transition-receipt-v1"
)
AUTHORITY_REGISTRATION_SCHEMA = (
    "strategy-correlation-cluster-nonce-registry-authority-registration-v1"
)
SIGNED_RECEIPT_SCHEMA = (
    "strategy-correlation-cluster-nonce-atomic-reserve-signed-receipt-v1"
)
SIGNED_RECEIPT_EVIDENCE_SCHEMA = (
    "strategy-correlation-cluster-nonce-atomic-reserve-signed-evidence-v1"
)

_HEX = frozenset("0123456789abcdef")
_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "registry_scope",
        "sequence",
        "previous_registry_head_hash",
        "entry_count",
        "reserved_replay_key_hashes",
        "state_origin",
        "durability_verified",
        "linearizable_storage_verified",
        "registry_authority_authenticated",
        "registry_head_hash",
    }
)
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "registry_scope",
        "candidate_replay_key_hash",
        "expected_registry_head_hash",
        "request_nonce_hash",
        "reserve_request_hash",
    }
)
_TRANSITION_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "status",
        "gate_status",
        "outcome",
        "reason_code",
        "reserve_request_hash",
        "candidate_replay_key_hash",
        "expected_registry_head_hash",
        "observed_registry_head_hash",
        "returned_registry_head_hash",
        "registry_sequence_before",
        "registry_sequence_after",
        "state_changed",
        "synthetic_compare_and_swap_verified",
        "atomic_storage_commit_verified",
        "durable_commit_verified",
        "linearizable_storage_verified",
        "registry_authority_authenticated",
        "absence_authorizes_progression",
        "http_registered",
        "ui_mounted",
        "current_activated",
        "paper_authorized",
        "live_authorized",
        "profitability_proven",
        "research_only",
        "reserve_transition_receipt_hash",
    }
)
_AUTHORITY_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "registry_scope",
        "algorithm",
        "registry_authority_id_hash",
        "public_key_base64",
        "public_key_sha256",
        "real_world_identity_verified",
        "key_governance_verified",
        "registry_source_authenticated",
        "authority_registration_hash",
    }
)
_SIGNED_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "algorithm",
        "reserve_transition_receipt_hash",
        "authority_registration_hash",
        "public_key_sha256",
        "signature_message",
        "signature_base64",
        "signature_sha256",
        "signature_verified_at_build",
        "signed_reserve_receipt_hash",
    }
)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _HEX for character in value)
    )


def _require_sha256(name: str, value: Any) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_nonnegative_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _decode_canonical_base64(name: str, value: Any, expected_length: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be canonical base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{name} must be canonical base64") from exc
    if len(decoded) != expected_length:
        raise ValueError(f"{name} must decode to {expected_length} bytes")
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{name} must be canonical base64")
    return decoded


def _valid_replay_key(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        rebuilt = build_nonce_replay_key_v1(
            signed_attestation_hash=value["signed_attestation_hash"],
            reviewer_key_sha256=value["reviewer_key_sha256"],
            review_nonce_hash=value["review_nonce_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def build_nonce_registry_synthetic_state_v1(
    *,
    reserved_replay_key_hashes: Sequence[str],
    sequence: int,
    previous_registry_head_hash: str | None,
) -> dict[str, Any]:
    """Build an immutable synthetic registry state.

    The state is suitable for protocol and adversarial tests only.  Its hash is
    an integrity commitment, not persistence or registry-authority evidence.
    """

    if isinstance(reserved_replay_key_hashes, (str, bytes, bytearray)):
        raise ValueError("reserved_replay_key_hashes must be a sequence")
    normalized = [
        _require_sha256("reserved_replay_key_hash", value)
        for value in reserved_replay_key_hashes
    ]
    if len(set(normalized)) != len(normalized):
        raise ValueError("reserved_replay_key_hashes must be unique")
    normalized.sort()

    normalized_sequence = _require_nonnegative_int("sequence", sequence)
    if normalized_sequence != len(normalized):
        raise ValueError("sequence must equal the number of reserved replay keys")
    if normalized_sequence == 0:
        if previous_registry_head_hash is not None:
            raise ValueError("genesis state must not have a previous head")
        normalized_previous_head = None
    else:
        normalized_previous_head = _require_sha256(
            "previous_registry_head_hash", previous_registry_head_hash
        )

    document = {
        "schema_version": REGISTRY_STATE_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_scope": REGISTRY_SCOPE,
        "sequence": normalized_sequence,
        "previous_registry_head_hash": normalized_previous_head,
        "entry_count": len(normalized),
        "reserved_replay_key_hashes": normalized,
        "state_origin": "SYNTHETIC_CALLER_STATE",
        "durability_verified": False,
        "linearizable_storage_verified": False,
        "registry_authority_authenticated": False,
    }
    return seal_strict_canonical_document(document, "registry_head_hash")


def _valid_registry_state(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _STATE_FIELDS:
        return False
    if not isinstance(value.get("reserved_replay_key_hashes"), list):
        return False
    try:
        rebuilt = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=value["reserved_replay_key_hashes"],
            sequence=value["sequence"],
            previous_registry_head_hash=value["previous_registry_head_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def _build_reserve_request_from_hashes(
    *,
    candidate_replay_key_hash: str,
    expected_registry_head_hash: str,
    request_nonce_hash: str,
) -> dict[str, Any]:
    document = {
        "schema_version": RESERVE_REQUEST_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_scope": REGISTRY_SCOPE,
        "candidate_replay_key_hash": _require_sha256(
            "candidate_replay_key_hash", candidate_replay_key_hash
        ),
        "expected_registry_head_hash": _require_sha256(
            "expected_registry_head_hash", expected_registry_head_hash
        ),
        "request_nonce_hash": _require_sha256(
            "request_nonce_hash", request_nonce_hash
        ),
    }
    return seal_strict_canonical_document(document, "reserve_request_hash")


def build_nonce_atomic_reserve_request_v1(
    *,
    candidate_replay_key: Mapping[str, Any],
    expected_registry_head_hash: str,
    request_nonce_hash: str,
) -> dict[str, Any]:
    if not _valid_replay_key(candidate_replay_key):
        raise ValueError("candidate_replay_key must be an exact replay-key-v1 document")
    return _build_reserve_request_from_hashes(
        candidate_replay_key_hash=candidate_replay_key["replay_key_hash"],
        expected_registry_head_hash=expected_registry_head_hash,
        request_nonce_hash=request_nonce_hash,
    )


def _valid_reserve_request(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _REQUEST_FIELDS:
        return False
    try:
        rebuilt = _build_reserve_request_from_hashes(
            candidate_replay_key_hash=value["candidate_replay_key_hash"],
            expected_registry_head_hash=value["expected_registry_head_hash"],
            request_nonce_hash=value["request_nonce_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def _build_transition_receipt(
    *,
    reserve_request: Mapping[str, Any],
    observed_state: Mapping[str, Any],
    returned_state: Mapping[str, Any],
    outcome: str,
    gate_status: str,
    reason_code: str,
    state_changed: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": TRANSITION_RECEIPT_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "gate_status": gate_status,
        "outcome": outcome,
        "reason_code": reason_code,
        "reserve_request_hash": reserve_request["reserve_request_hash"],
        "candidate_replay_key_hash": reserve_request["candidate_replay_key_hash"],
        "expected_registry_head_hash": reserve_request[
            "expected_registry_head_hash"
        ],
        "observed_registry_head_hash": observed_state["registry_head_hash"],
        "returned_registry_head_hash": returned_state["registry_head_hash"],
        "registry_sequence_before": observed_state["sequence"],
        "registry_sequence_after": returned_state["sequence"],
        "state_changed": state_changed,
        "synthetic_compare_and_swap_verified": True,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_storage_verified": False,
        "registry_authority_authenticated": False,
        "absence_authorizes_progression": False,
        "http_registered": False,
        "ui_mounted": False,
        "current_activated": False,
        "paper_authorized": False,
        "live_authorized": False,
        "profitability_proven": False,
        "research_only": True,
    }
    return seal_strict_canonical_document(document, "reserve_transition_receipt_hash")


def simulate_nonce_atomic_reserve_v1(
    *,
    registry_state: Mapping[str, Any],
    reserve_request: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Apply one immutable compare-and-swap transition to synthetic state."""

    if not _valid_registry_state(registry_state):
        raise ValueError("registry_state must be an exact synthetic-state-v1 document")
    if not _valid_reserve_request(reserve_request):
        raise ValueError("reserve_request must be an exact reserve-request-v1 document")

    candidate_hash = reserve_request["candidate_replay_key_hash"]
    current_hashes = registry_state["reserved_replay_key_hashes"]
    if candidate_hash in current_hashes:
        returned_state = deepcopy(dict(registry_state))
        outcome = "ALREADY_RESERVED"
        gate_status = "BLOCK"
        reason_code = "REPLAY_KEY_ALREADY_RESERVED"
        state_changed = False
    elif (
        reserve_request["expected_registry_head_hash"]
        != registry_state["registry_head_hash"]
    ):
        returned_state = deepcopy(dict(registry_state))
        outcome = "COMPARE_AND_SWAP_CONFLICT"
        gate_status = "UNKNOWN"
        reason_code = "EXPECTED_REGISTRY_HEAD_STALE"
        state_changed = False
    else:
        returned_state = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=[*current_hashes, candidate_hash],
            sequence=registry_state["sequence"] + 1,
            previous_registry_head_hash=registry_state["registry_head_hash"],
        )
        outcome = "RESERVED_IN_RETURNED_STATE"
        gate_status = "UNKNOWN"
        reason_code = "SYNTHETIC_STATE_RETURNED_NOT_DURABLE"
        state_changed = True

    receipt = _build_transition_receipt(
        reserve_request=reserve_request,
        observed_state=registry_state,
        returned_state=returned_state,
        outcome=outcome,
        gate_status=gate_status,
        reason_code=reason_code,
        state_changed=state_changed,
    )
    return {
        "next_registry_state": returned_state,
        "transition_receipt": receipt,
    }


def _valid_transition_receipt(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _TRANSITION_FIELDS:
        return False
    for field in (
        "reserve_request_hash",
        "candidate_replay_key_hash",
        "expected_registry_head_hash",
        "observed_registry_head_hash",
        "returned_registry_head_hash",
        "reserve_transition_receipt_hash",
    ):
        if not _is_sha256(value.get(field)):
            return False
    before = value.get("registry_sequence_before")
    after = value.get("registry_sequence_after")
    if (
        isinstance(before, bool)
        or not isinstance(before, int)
        or before < 0
        or isinstance(after, bool)
        or not isinstance(after, int)
        or after < 0
    ):
        return False

    fixed = {
        "schema_version": TRANSITION_RECEIPT_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "synthetic_compare_and_swap_verified": True,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_storage_verified": False,
        "registry_authority_authenticated": False,
        "absence_authorizes_progression": False,
        "http_registered": False,
        "ui_mounted": False,
        "current_activated": False,
        "paper_authorized": False,
        "live_authorized": False,
        "profitability_proven": False,
        "research_only": True,
    }
    if any(value.get(field) != expected for field, expected in fixed.items()):
        return False

    outcome = value.get("outcome")
    observed = value["observed_registry_head_hash"]
    returned = value["returned_registry_head_hash"]
    expected = value["expected_registry_head_hash"]
    if outcome == "RESERVED_IN_RETURNED_STATE":
        semantic_valid = (
            value.get("gate_status") == "UNKNOWN"
            and value.get("reason_code") == "SYNTHETIC_STATE_RETURNED_NOT_DURABLE"
            and value.get("state_changed") is True
            and expected == observed
            and returned != observed
            and after == before + 1
        )
    elif outcome == "ALREADY_RESERVED":
        semantic_valid = (
            value.get("gate_status") == "BLOCK"
            and value.get("reason_code") == "REPLAY_KEY_ALREADY_RESERVED"
            and value.get("state_changed") is False
            and returned == observed
            and after == before
        )
    elif outcome == "COMPARE_AND_SWAP_CONFLICT":
        semantic_valid = (
            value.get("gate_status") == "UNKNOWN"
            and value.get("reason_code") == "EXPECTED_REGISTRY_HEAD_STALE"
            and value.get("state_changed") is False
            and expected != observed
            and returned == observed
            and after == before
        )
    else:
        semantic_valid = False
    if not semantic_valid:
        return False

    unsealed = dict(value)
    actual_hash = unsealed.pop("reserve_transition_receipt_hash")
    rebuilt = seal_strict_canonical_document(
        unsealed, "reserve_transition_receipt_hash"
    )
    return actual_hash == rebuilt["reserve_transition_receipt_hash"]


def build_nonce_registry_authority_registration_v1(
    *, registry_authority_id_hash: str, public_key_base64: str
) -> dict[str, Any]:
    public_key_bytes = _decode_canonical_base64(
        "public_key_base64", public_key_base64, 32
    )
    Ed25519PublicKey.from_public_bytes(public_key_bytes)
    document = {
        "schema_version": AUTHORITY_REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registry_scope": REGISTRY_SCOPE,
        "algorithm": "Ed25519",
        "registry_authority_id_hash": _require_sha256(
            "registry_authority_id_hash", registry_authority_id_hash
        ),
        "public_key_base64": public_key_base64,
        "public_key_sha256": sha256(public_key_bytes).hexdigest(),
        "real_world_identity_verified": False,
        "key_governance_verified": False,
        "registry_source_authenticated": False,
    }
    return seal_strict_canonical_document(document, "authority_registration_hash")


def _valid_authority_registration(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _AUTHORITY_FIELDS:
        return False
    try:
        rebuilt = build_nonce_registry_authority_registration_v1(
            registry_authority_id_hash=value["registry_authority_id_hash"],
            public_key_base64=value["public_key_base64"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def build_signed_nonce_reserve_receipt_v1(
    *,
    transition_receipt: Mapping[str, Any],
    authority_registration: Mapping[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    if not _valid_transition_receipt(transition_receipt):
        raise ValueError("transition_receipt must be an exact transition-receipt-v1")
    if not _valid_authority_registration(authority_registration):
        raise ValueError("authority_registration must be an exact registration-v1")

    signature_bytes = _decode_canonical_base64(
        "signature_base64", signature_base64, 64
    )
    public_key_bytes = _decode_canonical_base64(
        "public_key_base64", authority_registration["public_key_base64"], 32
    )
    message = bytes.fromhex(
        transition_receipt["reserve_transition_receipt_hash"]
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            signature_bytes, message
        )
    except InvalidSignature as exc:
        raise ValueError("signature does not verify for the registered key") from exc

    document = {
        "schema_version": SIGNED_RECEIPT_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "algorithm": "Ed25519",
        "reserve_transition_receipt_hash": transition_receipt[
            "reserve_transition_receipt_hash"
        ],
        "authority_registration_hash": authority_registration[
            "authority_registration_hash"
        ],
        "public_key_sha256": authority_registration["public_key_sha256"],
        "signature_message": "reserve_transition_receipt_hash_bytes",
        "signature_base64": signature_base64,
        "signature_sha256": sha256(signature_bytes).hexdigest(),
        "signature_verified_at_build": True,
    }
    return seal_strict_canonical_document(document, "signed_reserve_receipt_hash")


def _valid_signed_receipt(
    value: Any,
    *,
    transition_receipt: Mapping[str, Any],
    authority_registration: Mapping[str, Any],
) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _SIGNED_RECEIPT_FIELDS:
        return False
    try:
        rebuilt = build_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition_receipt,
            authority_registration=authority_registration,
            signature_base64=value["signature_base64"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def _build_signed_evidence(
    *,
    status: str,
    gate_status: str,
    reason_code: str,
    outcome: str | None,
    transition_receipt_hash: str | None,
    authority_registration_hash: str | None,
    public_key_sha256: str | None,
    signature_sha256: str | None,
    signature_verified: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": SIGNED_RECEIPT_EVIDENCE_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "gate_status": gate_status,
        "reason_code": reason_code,
        "outcome": outcome,
        "reserve_transition_receipt_hash": transition_receipt_hash,
        "authority_registration_hash": authority_registration_hash,
        "public_key_sha256": public_key_sha256,
        "signature_sha256": signature_sha256,
        "signature_verified": signature_verified,
        "cryptographic_key_possession_verified": signature_verified,
        "synthetic_compare_and_swap_verified": signature_verified,
        "registry_authority_identity_verified": False,
        "registry_key_governance_verified": False,
        "registry_source_authenticated": False,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_storage_verified": False,
        "absence_authorizes_progression": False,
        "http_registered": False,
        "ui_mounted": False,
        "current_activated": False,
        "paper_authorized": False,
        "live_authorized": False,
        "profitability_proven": False,
        "research_only": True,
    }
    return seal_strict_canonical_document(document, "signed_reserve_evidence_hash")


def evaluate_signed_nonce_reserve_receipt_v1(
    *,
    transition_receipt: Mapping[str, Any],
    authority_registration: Mapping[str, Any],
    signed_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify a signed synthetic receipt without promoting storage authority."""

    if not _valid_transition_receipt(transition_receipt):
        return _build_signed_evidence(
            status="UNKNOWN",
            gate_status="UNKNOWN",
            reason_code="INVALID_TRANSITION_RECEIPT",
            outcome=None,
            transition_receipt_hash=None,
            authority_registration_hash=None,
            public_key_sha256=None,
            signature_sha256=None,
            signature_verified=False,
        )
    if not _valid_authority_registration(authority_registration):
        return _build_signed_evidence(
            status="UNKNOWN",
            gate_status="UNKNOWN",
            reason_code="INVALID_AUTHORITY_REGISTRATION",
            outcome=None,
            transition_receipt_hash=transition_receipt[
                "reserve_transition_receipt_hash"
            ],
            authority_registration_hash=None,
            public_key_sha256=None,
            signature_sha256=None,
            signature_verified=False,
        )
    if not _valid_signed_receipt(
        signed_receipt,
        transition_receipt=transition_receipt,
        authority_registration=authority_registration,
    ):
        return _build_signed_evidence(
            status="UNKNOWN",
            gate_status="UNKNOWN",
            reason_code="INVALID_SIGNED_RESERVE_RECEIPT",
            outcome=None,
            transition_receipt_hash=transition_receipt[
                "reserve_transition_receipt_hash"
            ],
            authority_registration_hash=authority_registration[
                "authority_registration_hash"
            ],
            public_key_sha256=authority_registration["public_key_sha256"],
            signature_sha256=None,
            signature_verified=False,
        )

    if transition_receipt["gate_status"] == "BLOCK":
        gate_status = "BLOCK"
        reason_code = "SIGNED_REPLAY_RESERVE_RECEIPT_BLOCK"
    else:
        gate_status = "UNKNOWN"
        reason_code = "SIGNED_SYNTHETIC_RECEIPT_NOT_DURABLE"
    return _build_signed_evidence(
        status="PASS",
        gate_status=gate_status,
        reason_code=reason_code,
        outcome=transition_receipt["outcome"],
        transition_receipt_hash=transition_receipt[
            "reserve_transition_receipt_hash"
        ],
        authority_registration_hash=authority_registration[
            "authority_registration_hash"
        ],
        public_key_sha256=authority_registration["public_key_sha256"],
        signature_sha256=signed_receipt["signature_sha256"],
        signature_verified=True,
    )
