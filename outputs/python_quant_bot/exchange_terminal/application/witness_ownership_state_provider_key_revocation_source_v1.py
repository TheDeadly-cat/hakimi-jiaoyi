"""Local revocation-authority quorum candidate for ADR0417."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    witness_ownership_state_provider_key_continuity_v1 as continuity,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as provider_preregistration,
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


AUTHORITY_SET_SCHEMA_VERSION = (
    "witness-ownership-provider-key-revocation-authority-set-v1"
)
REVOCATION_SNAPSHOT_SCHEMA_VERSION = (
    "witness-ownership-provider-key-revocation-snapshot-v1"
)
SIGNED_STATEMENT_SCHEMA_VERSION = (
    "witness-ownership-provider-key-revocation-signed-authority-statement-v1"
)
QUORUM_EVIDENCE_SCHEMA_VERSION = (
    "witness-ownership-provider-key-revocation-authority-quorum-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-key-revocation-source-v1-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = (
    "STRICT_CANONICAL_DOMAIN_SEPARATED_SHA256_DIGEST_BYTES_V1"
)
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.provider-key-revocation.v1"
)
ZERO_HASH = "0" * 64

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_AUTHORITY_ROW_KEYS = frozenset(
    {
        "authority_id",
        "public_key_spki_sha256",
        "organization_claim_hash",
        "trust_domain",
    }
)
_PERMANENT_BLOCKERS = (
    "REVOCATION_AUTHORITY_ORGANIZATION_IDENTITIES_UNVERIFIED",
    "REVOCATION_AUTHORITY_KEY_CONTINUITY_UNVERIFIED",
    "REVOCATION_AUTHORITY_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
    "REVOCATION_SNAPSHOT_PUBLICATION_UNVERIFIED",
    "REVOCATION_SNAPSHOT_PERSISTENCE_UNVERIFIED",
    "TRUSTED_REVOCATION_CLOCK_UNVERIFIED",
    "PROVIDER_KEY_CONTROL_CONTINUITY_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_identifier(name: str, value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _require_integer(name: str, value: Any, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _decode_public_key(value: Any):
    if type(value) is not str or not value:
        raise ValueError("public_key_spki_base64 must be non-empty")
    spki_bytes = decode_canonical_base64_v1(
        value, "public_key_spki_base64"
    )
    return spki_bytes, load_canonical_ed25519_public_key_v1(spki_bytes)


def _decode_signature(value: Any) -> bytes:
    if type(value) is not str or not value:
        raise ValueError("signature_base64 must be non-empty")
    signature = decode_canonical_base64_v1(value, "signature_base64")
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must be exactly 64 bytes")
    return signature


def _authority_lock() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "revocation_snapshot_trust_allowed": False,
        "provider_key_rotation_allowed": False,
        "provider_activation_allowed": False,
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _normalize_authorities(
    authority_registrations: Any,
    *,
    provider_key_hash: str,
) -> list[dict[str, str]]:
    if type(authority_registrations) is not list or len(authority_registrations) != 3:
        raise ValueError("exactly three revocation authorities are required")
    rows: list[dict[str, str]] = []
    for row in authority_registrations:
        if type(row) is not dict or frozenset(row) != _AUTHORITY_ROW_KEYS:
            raise ValueError("revocation authority row shape is not exact")
        rows.append(
            {
                "authority_id": _require_identifier(
                    "authority_id", row["authority_id"]
                ),
                "public_key_spki_sha256": _require_hash(
                    "public_key_spki_sha256",
                    row["public_key_spki_sha256"],
                ),
                "organization_claim_hash": _require_hash(
                    "organization_claim_hash",
                    row["organization_claim_hash"],
                ),
                "trust_domain": _require_identifier(
                    "trust_domain", row["trust_domain"]
                ),
            }
        )
    ids = [row["authority_id"] for row in rows]
    keys = [row["public_key_spki_sha256"] for row in rows]
    organizations = [row["organization_claim_hash"] for row in rows]
    if (
        len(set(ids)) != 3
        or len(set(keys)) != 3
        or len(set(organizations)) != 3
        or provider_key_hash in keys
    ):
        raise ValueError("revocation authority separation requirements failed")
    return sorted(rows, key=lambda row: row["authority_id"])


def build_witness_ownership_provider_key_revocation_authority_set_v1(
    provider_preregistration_document: Any,
    *,
    authority_registrations: Any,
    policy_id: Any,
    policy_version: Any,
    policy_hash: Any,
    provider_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(provider_preregistration_kwargs) is not dict or not provider_preregistration.verify_witness_ownership_state_provider_preregistration_v1(
        provider_preregistration_document,
        **dict(provider_preregistration_kwargs),
    ):
        raise ValueError("provider preregistration is not exact")
    if not isinstance(provider_preregistration_document, Mapping):
        raise ValueError("provider preregistration must be a mapping")
    provider_key_hash = provider_preregistration_document["identity"][
        "public_key_spki_sha256"
    ]
    authorities = _normalize_authorities(
        authority_registrations,
        provider_key_hash=provider_key_hash,
    )
    body = {
        "schema_version": AUTHORITY_SET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "REVOCATION_AUTHORITY_SET_PREREGISTERED_EXTERNAL_IDENTITIES_"
            "INDEPENDENCE_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "provider": {
            "registry_id": provider_preregistration_document["identity"][
                "registry_id"
            ],
            "provider_preregistration_hash": (
                provider_preregistration_document["preregistration_hash"]
            ),
            "provider_public_key_spki_sha256": provider_key_hash,
        },
        "policy": {
            "policy_id": _require_identifier("policy_id", policy_id),
            "policy_version": _require_integer(
                "policy_version", policy_version, minimum=1
            ),
            "policy_hash": _require_hash("policy_hash", policy_hash),
            "registered_authority_count": 3,
            "required_signature_quorum": 2,
            "authority_keys_must_differ_from_provider_key": True,
            "authority_ids_keys_and_organizations_must_be_unique": True,
            "structural_difference_is_not_identity_or_independence_proof": True,
        },
        "authorities": authorities,
        "facts": {
            "authority_profiles_preregistered": True,
            "authority_organization_identities_verified": False,
            "authority_key_continuity_verified": False,
            "authority_independence_source_truth_verified": False,
            "revocation_source_trust_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority_lock(),
    }
    return seal_strict_canonical_document(body, "authority_set_hash")


def verify_witness_ownership_provider_key_revocation_authority_set_v1(
    document: Any,
    provider_preregistration_document: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_witness_ownership_provider_key_revocation_authority_set_v1(
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def build_witness_ownership_provider_key_revocation_snapshot_v1(
    authority_set_document: Any,
    provider_preregistration_document: Any,
    *,
    previous_key_epoch: Any,
    next_key_epoch: Any,
    previous_public_key_spki_sha256: Any,
    next_public_key_spki_sha256: Any,
    rotation_nonce_hash: Any,
    previous_revocation_snapshot_hash: Any,
    revocation_sequence: Any,
    revocation_reason_code: Any,
    authority_set_build_kwargs: Any,
) -> dict[str, Any]:
    if type(authority_set_build_kwargs) is not dict or not verify_witness_ownership_provider_key_revocation_authority_set_v1(
        authority_set_document,
        provider_preregistration_document,
        **dict(authority_set_build_kwargs),
    ):
        raise ValueError("revocation authority set is not exact")
    previous_epoch = _require_integer("previous_key_epoch", previous_key_epoch)
    next_epoch = _require_integer("next_key_epoch", next_key_epoch)
    if next_epoch != previous_epoch + 1:
        raise ValueError("revocation snapshot key epoch must advance by one")
    previous_key_hash = _require_hash(
        "previous_public_key_spki_sha256",
        previous_public_key_spki_sha256,
    )
    next_key_hash = _require_hash(
        "next_public_key_spki_sha256", next_public_key_spki_sha256
    )
    if previous_key_hash == next_key_hash:
        raise ValueError("revocation snapshot must replace the provider key")
    if (
        previous_epoch == 0
        and previous_key_hash
        != provider_preregistration_document["identity"][
            "public_key_spki_sha256"
        ]
    ):
        raise ValueError("epoch-zero snapshot must revoke preregistered key")
    nonce_hash = _require_hash("rotation_nonce_hash", rotation_nonce_hash)
    predecessor_hash = _require_hash(
        "previous_revocation_snapshot_hash",
        previous_revocation_snapshot_hash,
    )
    sequence = _require_integer(
        "revocation_sequence", revocation_sequence, minimum=1
    )
    if (sequence == 1 and predecessor_hash != ZERO_HASH) or (
        sequence > 1 and predecessor_hash == ZERO_HASH
    ):
        raise ValueError("revocation snapshot predecessor is inconsistent")
    if type(revocation_reason_code) is not str or revocation_reason_code not in continuity.ROTATION_REASON_CODES:
        raise ValueError("revocation reason code is not preregistered")
    body = {
        "schema_version": REVOCATION_SNAPSHOT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "authority_set_hash": authority_set_document["authority_set_hash"],
        "provider": {
            "registry_id": provider_preregistration_document["identity"][
                "registry_id"
            ],
            "provider_preregistration_hash": (
                provider_preregistration_document["preregistration_hash"]
            ),
        },
        "policy": deepcopy(authority_set_document["policy"]),
        "snapshot": {
            "revocation_sequence": sequence,
            "previous_revocation_snapshot_hash": predecessor_hash,
            "previous_key_epoch": previous_epoch,
            "next_key_epoch": next_epoch,
            "previous_public_key_spki_sha256": previous_key_hash,
            "next_public_key_spki_sha256": next_key_hash,
            "rotation_nonce_hash": nonce_hash,
            "revocation_reason_code": revocation_reason_code,
        },
        "facts": {
            "snapshot_structure_complete": True,
            "authority_signature_quorum_verified": False,
            "revocation_snapshot_source_verified": False,
            "snapshot_persistence_verified": False,
            "trusted_revocation_clock_verified": False,
            "provider_key_control_continuity_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority_lock(),
    }
    return seal_strict_canonical_document(body, "revocation_snapshot_hash")


def verify_witness_ownership_provider_key_revocation_snapshot_v1(
    document: Any,
    authority_set_document: Any,
    provider_preregistration_document: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_witness_ownership_provider_key_revocation_snapshot_v1(
            authority_set_document,
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def build_witness_ownership_provider_key_revocation_signature_message_hash_v1(
    snapshot_document: Any,
    authority_set_document: Any,
) -> str:
    if (
        type(snapshot_document) is not dict
        or type(authority_set_document) is not dict
        or not _is_hash(snapshot_document.get("revocation_snapshot_hash"))
        or not _is_hash(authority_set_document.get("authority_set_hash"))
    ):
        raise ValueError("revocation signature message inputs are invalid")
    snapshot = snapshot_document["snapshot"]
    return strict_canonical_hash(
        {
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "authority_set_hash": authority_set_document[
                "authority_set_hash"
            ],
            "revocation_snapshot_hash": snapshot_document[
                "revocation_snapshot_hash"
            ],
            "registry_id": snapshot_document["provider"]["registry_id"],
            "revocation_sequence": snapshot["revocation_sequence"],
            "previous_key_epoch": snapshot["previous_key_epoch"],
            "next_key_epoch": snapshot["next_key_epoch"],
            "previous_public_key_spki_sha256": snapshot[
                "previous_public_key_spki_sha256"
            ],
            "next_public_key_spki_sha256": snapshot[
                "next_public_key_spki_sha256"
            ],
            "rotation_nonce_hash": snapshot["rotation_nonce_hash"],
            "policy_hash": snapshot_document["policy"]["policy_hash"],
        }
    )


def build_signed_witness_ownership_provider_key_revocation_authority_statement_v1(
    snapshot_document: Any,
    authority_set_document: Any,
    provider_preregistration_document: Any,
    *,
    authority_id: Any,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_revocation_snapshot_hash: Any,
    snapshot_build_kwargs: Any,
) -> dict[str, Any]:
    if type(snapshot_build_kwargs) is not dict or not verify_witness_ownership_provider_key_revocation_snapshot_v1(
        snapshot_document,
        authority_set_document,
        provider_preregistration_document,
        **dict(snapshot_build_kwargs),
    ):
        raise ValueError("revocation snapshot is not exact")
    snapshot_hash = _require_hash(
        "expected_revocation_snapshot_hash",
        expected_revocation_snapshot_hash,
    )
    if snapshot_document["revocation_snapshot_hash"] != snapshot_hash:
        raise ValueError("revocation snapshot hash binding drifted")
    authority = _require_identifier("authority_id", authority_id)
    registrations = {
        row["authority_id"]: row for row in authority_set_document["authorities"]
    }
    if authority not in registrations:
        raise ValueError("revocation authority is not preregistered")
    spki_bytes, _ = _decode_public_key(public_key_spki_base64)
    _decode_signature(signature_base64)
    key_hash = sha256(spki_bytes).hexdigest()
    if key_hash != registrations[authority]["public_key_spki_sha256"]:
        raise ValueError("revocation authority public key hash mismatch")
    message_hash = build_witness_ownership_provider_key_revocation_signature_message_hash_v1(
        snapshot_document,
        authority_set_document,
    )
    body = {
        "schema_version": SIGNED_STATEMENT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_STATEMENT_CANDIDATE",
        "authority_id": authority,
        "authority_set_hash": authority_set_document["authority_set_hash"],
        "revocation_snapshot_hash": snapshot_hash,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_message_hash": message_hash,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": key_hash,
        "signature_base64": signature_base64,
        "authority": _authority_lock(),
    }
    return seal_strict_canonical_document(body, "signed_statement_hash")


def evaluate_witness_ownership_provider_key_revocation_authority_quorum_v1(
    signed_statement_documents: Any,
    snapshot_document: Any,
    authority_set_document: Any,
    rotation_evidence_document: Any,
    signed_rotation_document: Any,
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    authority_set_build_kwargs: Any,
    snapshot_build_kwargs: Any,
    expected_rotation_evidence_hash: Any,
    rotation_evidence_verify_kwargs: Any,
) -> dict[str, Any]:
    upstream_exact = False
    rotation_binding_exact = False
    try:
        if (
            type(authority_set_build_kwargs) is not dict
            or type(snapshot_build_kwargs) is not dict
            or type(rotation_evidence_verify_kwargs) is not dict
            or not verify_witness_ownership_provider_key_revocation_authority_set_v1(
                authority_set_document,
                provider_preregistration_document,
                **dict(authority_set_build_kwargs),
            )
            or not verify_witness_ownership_provider_key_revocation_snapshot_v1(
                snapshot_document,
                authority_set_document,
                provider_preregistration_document,
                **dict(snapshot_build_kwargs),
            )
            or not continuity.verify_dual_signed_witness_ownership_provider_key_rotation_evidence_v1(
                rotation_evidence_document,
                signed_rotation_document,
                rotation_claim_document,
                previous_key_state_document,
                provider_preregistration_document,
                expected_rotation_evidence_hash=expected_rotation_evidence_hash,
                **dict(rotation_evidence_verify_kwargs),
            )
        ):
            raise ValueError("revocation upstream chain is not exact")
        upstream_exact = True
        snapshot = snapshot_document["snapshot"]
        transition = rotation_claim_document["transition"]
        rotation_binding_exact = (
            rotation_evidence_document.get("status") == "PASS"
            and rotation_evidence_document.get("admission_status") == "BLOCKED"
            and rotation_evidence_document.get("facts", {}).get(
                "revocation_snapshot_source_verified"
            )
            is False
            and snapshot_document["revocation_snapshot_hash"]
            == transition["revocation_snapshot_hash"]
            and snapshot["previous_key_epoch"]
            == transition["previous_key_epoch"]
            and snapshot["next_key_epoch"] == transition["next_key_epoch"]
            and snapshot["previous_public_key_spki_sha256"]
            == transition["previous_public_key_spki_sha256"]
            and snapshot["next_public_key_spki_sha256"]
            == transition["next_public_key_spki_sha256"]
            and snapshot["rotation_nonce_hash"]
            == transition["rotation_nonce_hash"]
            and snapshot["revocation_reason_code"]
            == transition["rotation_reason_code"]
        )
    except (KeyError, TypeError, ValueError):
        pass

    rows = signed_statement_documents if type(signed_statement_documents) is list else []
    registrations = (
        {
            row["authority_id"]: row
            for row in authority_set_document.get("authorities", [])
        }
        if isinstance(authority_set_document, Mapping)
        else {}
    )
    authority_results: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    for statement in rows:
        authority_id = (
            statement.get("authority_id")
            if isinstance(statement, Mapping)
            else None
        )
        statement_exact = False
        signature_verified = False
        signed_statement_hash = None
        try:
            if not upstream_exact or not rotation_binding_exact or type(statement) is not dict:
                raise ValueError("signed revocation statement upstream invalid")
            expected = build_signed_witness_ownership_provider_key_revocation_authority_statement_v1(
                snapshot_document,
                authority_set_document,
                provider_preregistration_document,
                authority_id=authority_id,
                public_key_spki_base64=statement["public_key_spki_base64"],
                signature_base64=statement["signature_base64"],
                expected_revocation_snapshot_hash=snapshot_document[
                    "revocation_snapshot_hash"
                ],
                snapshot_build_kwargs=snapshot_build_kwargs,
            )
            signed_statement_hash = expected["signed_statement_hash"]
            statement_exact = strict_json_contract_equal(statement, expected)
            _, public_key = _decode_public_key(
                statement["public_key_spki_base64"]
            )
            signature = _decode_signature(statement["signature_base64"])
            if (
                sha256(
                    decode_canonical_base64_v1(
                        statement["public_key_spki_base64"],
                        "public_key_spki_base64",
                    )
                ).hexdigest()
                != registrations[authority_id]["public_key_spki_sha256"]
            ):
                raise ValueError("authority key registration drifted")
            try:
                public_key.verify(
                    signature,
                    bytes.fromhex(expected["signature_message_hash"]),
                )
                signature_verified = True
            except (InvalidSignature, ValueError):
                signature_verified = False
        except (KeyError, TypeError, ValueError):
            pass
        row_pass = statement_exact and signature_verified
        if type(authority_id) is str:
            seen_ids.append(authority_id)
        authority_results.append(
            {
                "authority_id": authority_id,
                "signed_statement_hash": signed_statement_hash,
                "statement_exact": statement_exact,
                "signature_verified": signature_verified,
                "status": "PASS" if row_pass else "BLOCK",
            }
        )
    authority_results.sort(
        key=lambda row: (
            str(row["authority_id"]),
            str(row["signed_statement_hash"]),
        )
    )
    duplicates = len(seen_ids) != len(set(seen_ids))
    passing_ids = sorted(
        row["authority_id"]
        for row in authority_results
        if row["status"] == "PASS" and type(row["authority_id"]) is str
    )
    local_quorum_verified = (
        upstream_exact
        and rotation_binding_exact
        and len(rows) in (2, 3)
        and not duplicates
        and len(set(passing_ids)) >= 2
    )
    dynamic_blockers: list[str] = []
    if not upstream_exact:
        dynamic_blockers.append("REVOCATION_UPSTREAM_CHAIN_NOT_EXACT")
    if not rotation_binding_exact:
        dynamic_blockers.append("REVOCATION_SNAPSHOT_ROTATION_BINDING_INVALID")
    if len(rows) not in (2, 3):
        dynamic_blockers.append("REVOCATION_STATEMENT_COUNT_NOT_TWO_OR_THREE")
    if duplicates:
        dynamic_blockers.append("DUPLICATE_REVOCATION_AUTHORITY_ID")
    if len(set(passing_ids)) < 2:
        dynamic_blockers.append("REVOCATION_AUTHORITY_SIGNATURE_QUORUM_NOT_MET")

    body = {
        "schema_version": QUORUM_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_quorum_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "revocation_status": (
            "LOCAL_TWO_OF_THREE_REVOCATION_SNAPSHOT_CANDIDATE_BLOCKED"
            if local_quorum_verified
            else "UNKNOWN"
        ),
        "decision": (
            "REVOCATION_SNAPSHOT_BOUND_TO_DUAL_SIGNED_ROTATION_AND_LOCAL_"
            "AUTHORITY_QUORUM_EXTERNAL_SOURCE_TRUTH_STILL_BLOCKED"
            if local_quorum_verified
            else "REVOCATION_SOURCE_BINDING_INVALID_OR_INCOMPLETE"
        ),
        "blockers": dynamic_blockers + list(_PERMANENT_BLOCKERS),
        "authority_results": authority_results,
        "quorum_summary": {
            "registered_authority_count": 3,
            "submitted_statement_count": len(rows),
            "required_signature_quorum": 2,
            "passing_authority_ids": passing_ids,
            "duplicate_authority_ids_detected": duplicates,
        },
        "source": {
            "provider_preregistration_hash": (
                provider_preregistration_document.get("preregistration_hash")
                if isinstance(provider_preregistration_document, Mapping)
                else None
            ),
            "authority_set_hash": (
                authority_set_document.get("authority_set_hash")
                if isinstance(authority_set_document, Mapping)
                else None
            ),
            "revocation_snapshot_hash": (
                snapshot_document.get("revocation_snapshot_hash")
                if isinstance(snapshot_document, Mapping)
                else None
            ),
            "rotation_claim_hash": (
                rotation_claim_document.get("rotation_claim_hash")
                if isinstance(rotation_claim_document, Mapping)
                else None
            ),
            "rotation_evidence_hash": (
                expected_rotation_evidence_hash
                if _is_hash(expected_rotation_evidence_hash)
                else None
            ),
        },
        "facts": {
            "upstream_chain_exact": upstream_exact,
            "revocation_snapshot_bound_to_rotation": rotation_binding_exact,
            "local_revocation_authority_signature_quorum_verified": (
                local_quorum_verified
            ),
            "revocation_authority_organization_identities_verified": False,
            "revocation_authority_key_continuity_verified": False,
            "revocation_authority_independence_source_truth_verified": False,
            "revocation_snapshot_source_verified": False,
            "revocation_snapshot_publication_verified": False,
            "revocation_snapshot_persistence_verified": False,
            "trusted_revocation_clock_verified": False,
            "provider_key_control_continuity_verified": False,
            "provider_implementation_update_verified": False,
            "external_provider_conformance_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "network_accessed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": _authority_lock(),
        "redaction": {
            "raw_public_keys_redacted": True,
            "raw_signatures_redacted": True,
            "raw_revocation_snapshot_payload_embedded": False,
            "raw_provider_credentials_embedded": False,
        },
        "limitations": [
            "A local 2-of-3 authority signature quorum proves only signatures over the exact snapshot hash.",
            "Structurally distinct authority profiles do not prove organization identity, independence, publication, persistence, trusted time, or external source trust.",
            "No provider key, preregistration, runtime, current, pointer, paper, live, writer, migration, or trading authority is changed.",
        ],
    }
    return seal_strict_canonical_document(body, "quorum_evidence_hash")


def verify_witness_ownership_provider_key_revocation_authority_quorum_v1(
    document: Any,
    signed_statement_documents: Any,
    snapshot_document: Any,
    authority_set_document: Any,
    rotation_evidence_document: Any,
    signed_rotation_document: Any,
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_quorum_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if type(document) is not dict or not _is_hash(expected_quorum_evidence_hash):
        return False
    expected = evaluate_witness_ownership_provider_key_revocation_authority_quorum_v1(
        signed_statement_documents,
        snapshot_document,
        authority_set_document,
        rotation_evidence_document,
        signed_rotation_document,
        rotation_claim_document,
        previous_key_state_document,
        provider_preregistration_document,
        **evaluation_kwargs,
    )
    return (
        expected["quorum_evidence_hash"] == expected_quorum_evidence_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "AUTHORITY_SET_SCHEMA_VERSION",
    "QUORUM_EVIDENCE_SCHEMA_VERSION",
    "REVOCATION_SNAPSHOT_SCHEMA_VERSION",
    "SIGNATURE_DOMAIN",
    "SIGNED_STATEMENT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "ZERO_HASH",
    "build_signed_witness_ownership_provider_key_revocation_authority_statement_v1",
    "build_witness_ownership_provider_key_revocation_authority_set_v1",
    "build_witness_ownership_provider_key_revocation_signature_message_hash_v1",
    "build_witness_ownership_provider_key_revocation_snapshot_v1",
    "evaluate_witness_ownership_provider_key_revocation_authority_quorum_v1",
    "verify_witness_ownership_provider_key_revocation_authority_quorum_v1",
]
