"""Fail-closed quarantine for the unresolved ADR0402 commitment semantics.

The ADR0402 commitment is exact and blocked, but its out-of-band commitment
hash must remain opaque until one semantic profile is explicitly preregistered.
This module selects no profile and grants no installation or activation power.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1 as genesis,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "genesis-replay-reservation-commitment-semantic-profile-quarantine-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-commitment-semantic-profile-"
    "quarantine-v1-unresolved-lock-1"
)
STATUS_BLOCK = "BLOCK"
DECISION_DO_NOT_INTERPRET_OR_ACTIVATE = "DO_NOT_INTERPRET_OR_ACTIVATE"
PROFILE_STATE_UNRESOLVED = "UNRESOLVED"
ADR0402_IMPLEMENTATION_SHA256 = (
    "693966381aec8b79d03ee13a9f0e6070dbf7657802e93b650cae61eabf2a098f"
)

SEMANTIC_PROFILE_CANDIDATES = (
    "PRE_CEREMONY_AUTHORIZATION_MANIFEST_ANCHOR",
    "POST_DERIVATION_GENESIS_COMMITMENT_MATCH_TARGET",
)

QUARANTINE_BLOCKERS = (
    "OUT_OF_BAND_COMMITMENT_SEMANTICS_AMBIGUOUS",
    "SEMANTIC_PROFILE_NOT_PREREGISTERED",
    "SEMANTIC_PROFILE_NOT_SELECTED",
    "PROFILE_SELECTION_COMMITMENT_ABSENT",
    "PROFILE_DOMAIN_SEPARATION_UNVERIFIED",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_KEYS = (
    "current_activation_allowed",
    "genesis_admission_allowed",
    "genesis_commitment_install_allowed",
    "live_order_allowed",
    "paper_authorized",
    "profile_interpretation_allowed",
    "profile_selection_allowed",
    "provider_registration_allowed",
    "runtime_gate_activation_allowed",
    "writer_allowed",
)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _native_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) not in {dict, list}:
        raise TypeError("quarantine inputs require native strict JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic quarantine inputs are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_native_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("quarantine keys must be strings")
            snapshot[key] = _native_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _profiles() -> dict[str, Any]:
    return {
        "profile_state": PROFILE_STATE_UNRESOLVED,
        "candidate_profiles": [
            {"profile_id": profile_id, "selected": False}
            for profile_id in SEMANTIC_PROFILE_CANDIDATES
        ],
        "selected_profile_id": None,
        "selected_profile_commitment_hash": None,
    }


def _facts(*, source_exact: bool) -> dict[str, bool]:
    return {
        "source_commitment_exactly_verified": source_exact,
        "source_commitment_blocked": source_exact,
        "opaque_hash_preserved_without_interpretation": source_exact,
        "semantic_profile_preregistered": False,
        "semantic_profile_selected": False,
        "profile_selection_commitment_verified": False,
        "profile_domain_separation_verified": False,
        "out_of_band_genesis_commitment_verified": False,
        "genesis_commitment_installed": False,
        "installation_rollback_protection_verified": False,
        "trusted_current_time_established": False,
        "raw_source_commitment_embedded": False,
        "raw_evidence_embedded": False,
        "raw_signature_or_key_material_embedded": False,
        "runtime_mutations_performed": False,
        "current_activated": False,
    }


def _seal(
    *,
    status: str,
    decision: str,
    source: dict[str, str | None],
    source_blockers: list[str],
    source_exact: bool,
    blockers: list[str],
) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": source,
        "semantic_profiles": _profiles(),
        "source_blockers": source_blockers,
        "facts": _facts(source_exact=source_exact),
        "blockers": blockers,
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "semantic_quarantine_hash")


def _unknown(reason: str) -> dict[str, Any]:
    return _seal(
        status="UNKNOWN",
        decision=DECISION_DO_NOT_INTERPRET_OR_ACTIVATE,
        source={
            "adr0402_implementation_sha256": ADR0402_IMPLEMENTATION_SHA256,
            "genesis_commitment_hash": None,
            "genesis_admission_claim_hash": None,
            "verification_evidence_hash": None,
            "opaque_out_of_band_genesis_commitment_hash": None,
        },
        source_blockers=[],
        source_exact=False,
        blockers=[reason, *QUARANTINE_BLOCKERS],
    )


def _source_semantics_safe(document: Any) -> bool:
    return (
        type(document) is dict
        and document.get("schema_version") == genesis.GENESIS_COMMITMENT_SCHEMA_VERSION
        and document.get("status") == "BLOCKED"
        and type(document.get("binding")) is dict
        and _is_sha256(
            document["binding"].get(
                "expected_out_of_band_genesis_commitment_hash"
            )
        )
        and type(document.get("source")) is dict
        and _is_sha256(document["source"].get("genesis_admission_claim_hash"))
        and _is_sha256(document["source"].get("verification_evidence_hash"))
        and type(document.get("facts")) is dict
        and document["facts"].get("out_of_band_genesis_commitment_verified")
        is False
        and document["facts"].get("genesis_commitment_installed") is False
        and document["facts"].get(
            "installation_rollback_protection_verified"
        )
        is False
        and type(document.get("authority")) is dict
        and all(value is False for value in document["authority"].values())
        and type(document.get("blockers")) is list
        and all(type(item) is str and item for item in document["blockers"])
    )


def evaluate_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
    genesis_commitment_document: Any,
    *genesis_commitment_verification_args: Any,
    expected_genesis_commitment_hash: Any,
    **genesis_commitment_verification_kwargs: Any,
) -> dict[str, Any]:
    if not _is_sha256(expected_genesis_commitment_hash):
        return _unknown("EXPECTED_GENESIS_COMMITMENT_HASH_NOT_EXACT")
    try:
        commitment = _native_json_snapshot(genesis_commitment_document)
    except Exception:
        return _unknown("SOURCE_GENESIS_COMMITMENT_NOT_NATIVE_STRICT_JSON")
    if not genesis.verify_clock_trust_genesis_commitment_v1(
        commitment,
        *genesis_commitment_verification_args,
        expected_genesis_commitment_hash=expected_genesis_commitment_hash,
        **genesis_commitment_verification_kwargs,
    ):
        return _unknown("SOURCE_GENESIS_COMMITMENT_NOT_EXACT")
    if not _source_semantics_safe(commitment):
        return _unknown("SOURCE_GENESIS_COMMITMENT_SEMANTICS_NOT_SAFE")
    source_blockers = list(commitment["blockers"])
    return _seal(
        status=STATUS_BLOCK,
        decision=DECISION_DO_NOT_INTERPRET_OR_ACTIVATE,
        source={
            "adr0402_implementation_sha256": ADR0402_IMPLEMENTATION_SHA256,
            "genesis_commitment_hash": commitment["genesis_commitment_hash"],
            "genesis_admission_claim_hash": commitment["source"][
                "genesis_admission_claim_hash"
            ],
            "verification_evidence_hash": commitment["source"][
                "verification_evidence_hash"
            ],
            "opaque_out_of_band_genesis_commitment_hash": commitment["binding"][
                "expected_out_of_band_genesis_commitment_hash"
            ],
        },
        source_blockers=source_blockers,
        source_exact=True,
        blockers=[*source_blockers, *QUARANTINE_BLOCKERS],
    )


def verify_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
    document: Any,
    genesis_commitment_document: Any,
    *genesis_commitment_verification_args: Any,
    expected_semantic_quarantine_hash: Any,
    expected_genesis_commitment_hash: Any,
    **genesis_commitment_verification_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_semantic_quarantine_hash):
        return False
    try:
        snapshot = _native_json_snapshot(document)
    except Exception:
        return False
    expected = (
        evaluate_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1(
            genesis_commitment_document,
            *genesis_commitment_verification_args,
            expected_genesis_commitment_hash=expected_genesis_commitment_hash,
            **genesis_commitment_verification_kwargs,
        )
    )
    return (
        expected.get("semantic_quarantine_hash")
        == expected_semantic_quarantine_hash
        and strict_json_contract_equal(snapshot, expected)
    )


__all__ = [
    "ADR0402_IMPLEMENTATION_SHA256",
    "DECISION_DO_NOT_INTERPRET_OR_ACTIVATE",
    "PROFILE_STATE_UNRESOLVED",
    "QUARANTINE_BLOCKERS",
    "SCHEMA_VERSION",
    "SEMANTIC_PROFILE_CANDIDATES",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "evaluate_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1",
    "verify_genesis_replay_reservation_commitment_semantic_profile_quarantine_v1",
]
