from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature

from . import strategy_correlation_cluster_effective_bet_budget_v6 as budget_v6
from .strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1 as _decode_canonical_base64,
    load_canonical_ed25519_public_key_v1 as _load_ed25519_public_key,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = (
    "20260824-signed-evaluation-clock-effective-budget-v7-synthetic-lock-1"
)
CLOCK_PROVIDER_SCHEMA_VERSION = (
    "strategy-correlation-evaluation-clock-provider-preregistration-v1"
)
CLOCK_CLAIM_SCHEMA_VERSION = "strategy-correlation-evaluation-time-claim-v1"
SIGNED_CLOCK_SCHEMA_VERSION = (
    "strategy-correlation-evaluation-time-signed-attestation-v1"
)
CLOCK_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-evaluation-time-signature-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v7"

_MAX_TIME_MS = 9_999_999_999_999_999
_SIGNATURE_DOMAIN = "hakimi.strategy-correlation.evaluation-clock.v1"
_SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
_CLOCK_LIMITATIONS = [
    "CLOCK_PROVIDER_IDENTITY_UNVERIFIED",
    "CLOCK_PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "CLOCK_TIME_SOURCE_TRUTH_UNVERIFIED",
    "CLOCK_COUNTER_CONTINUITY_UNVERIFIED",
    "ATOMIC_CURRENT_HEAD_PERSISTENCE_UNVERIFIED",
    "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "clock_source_trust_allowed": False,
        "snapshot_source_trust_allowed": False,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return deepcopy(value)


def _require_identifier(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 160
        or value != value.strip()
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"{field} must be a compact nonempty identifier")
    return value


def _require_int(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = _MAX_TIME_MS,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{field} is outside the allowed range")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _document_sha256(value: Any) -> str | None:
    try:
        return _require_sha256(value, "document hash")
    except ValueError:
        return None


def _document_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"check_id": check_id, "status": "PASS" if passed else "BLOCK"}


def _blockers(checks: list[dict[str, str]]) -> list[str]:
    return [item["check_id"] for item in checks if item["status"] != "PASS"]


def build_evaluation_clock_provider_preregistration_v1(
    *,
    provider_id: Any,
    key_id: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    account_scope_hash: Any,
    implementation_claim_sha256: Any,
) -> dict[str, Any]:
    document = {
        "schema_version": CLOCK_PROVIDER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "EVALUATION_CLOCK_PROVIDER_PREREGISTERED_"
            "IDENTITY_IMPLEMENTATION_AND_TIME_TRUTH_UNVERIFIED"
        ),
        "identity": {
            "provider_id": _require_identifier(provider_id, "provider_id"),
            "key_id": _require_identifier(key_id, "key_id"),
            "public_key_spki_sha256": _require_sha256(
                public_key_spki_sha256,
                "public_key_spki_sha256",
            ),
            "trust_domain": _require_identifier(trust_domain, "trust_domain"),
            "account_scope_hash": _require_sha256(
                account_scope_hash,
                "account_scope_hash",
            ),
            "implementation_claim_sha256": _require_sha256(
                implementation_claim_sha256,
                "implementation_claim_sha256",
            ),
        },
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "local_preregistration_complete": True,
            "provider_identity_verified": False,
            "provider_key_possession_verified": False,
            "provider_implementation_verified": False,
            "time_source_truth_verified": False,
            "clock_counter_continuity_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_CLOCK_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "clock_provider_hash")


def verify_evaluation_clock_provider_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        rebuilt = build_evaluation_clock_provider_preregistration_v1(**build_kwargs)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, rebuilt)


def build_evaluation_time_claim_v1(
    clock_provider_preregistration_document: Any,
    *,
    clock_provider_preregistration_kwargs: Any,
    attestation_id_hash: Any,
    clock_counter: Any,
    evaluated_at_unix_ms: Any,
    subject_policy_hash: Any,
    subject_transition_hash: Any,
    subject_current_state_hash: Any,
    subject_snapshot_claim_hash: Any,
) -> dict[str, Any]:
    provider_kwargs = _require_mapping(
        clock_provider_preregistration_kwargs,
        "clock_provider_preregistration_kwargs",
    )
    if not verify_evaluation_clock_provider_preregistration_v1(
        clock_provider_preregistration_document,
        **provider_kwargs,
    ):
        raise ValueError("clock provider preregistration is not exact")
    provider = _mapping(clock_provider_preregistration_document)
    identity = _mapping(provider.get("identity"))

    document = {
        "schema_version": CLOCK_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "EVALUATION_TIME_CLAIM_UNSIGNED_"
            "CLOCK_IDENTITY_IMPLEMENTATION_COUNTER_AND_TIME_TRUTH_UNVERIFIED"
        ),
        "source": {
            "clock_provider_hash": _require_sha256(
                provider.get("clock_provider_hash"),
                "clock_provider_hash",
            ),
            "provider_id": _require_identifier(
                identity.get("provider_id"),
                "provider_id",
            ),
            "key_id": _require_identifier(identity.get("key_id"), "key_id"),
            "account_scope_hash": _require_sha256(
                identity.get("account_scope_hash"),
                "account_scope_hash",
            ),
        },
        "clock_reading": {
            "attestation_id_hash": _require_sha256(
                attestation_id_hash,
                "attestation_id_hash",
            ),
            "clock_counter": _require_int(clock_counter, "clock_counter"),
            "evaluated_at_unix_ms": _require_int(
                evaluated_at_unix_ms,
                "evaluated_at_unix_ms",
            ),
        },
        "subject": {
            "purpose": "STRATEGY_CORRELATION_EFFECTIVE_BET_BUDGET",
            "policy_hash": _require_sha256(
                subject_policy_hash,
                "subject_policy_hash",
            ),
            "transition_hash": _require_sha256(
                subject_transition_hash,
                "subject_transition_hash",
            ),
            "current_state_hash": _require_sha256(
                subject_current_state_hash,
                "subject_current_state_hash",
            ),
            "snapshot_claim_hash": _require_sha256(
                subject_snapshot_claim_hash,
                "subject_snapshot_claim_hash",
            ),
        },
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "clock_provider_preregistration_exact": True,
            "subject_hashes_exact": True,
            "clock_signature_verified": False,
            "clock_provider_identity_verified": False,
            "clock_provider_implementation_verified": False,
            "clock_counter_continuity_verified": False,
            "time_source_truth_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_CLOCK_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "clock_claim_hash")


def verify_evaluation_time_claim_v1(
    document: Any,
    clock_provider_preregistration_document: Any,
    *,
    expected_clock_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_clock_claim_hash,
            "expected_clock_claim_hash",
        )
        rebuilt = build_evaluation_time_claim_v1(
            clock_provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("clock_claim_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_signed_evaluation_time_attestation_v1(
    clock_claim_document: Any,
    clock_provider_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_clock_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_kwargs = _require_mapping(claim_build_kwargs, "claim_build_kwargs")
    claim_hash = _require_sha256(
        expected_clock_claim_hash,
        "expected_clock_claim_hash",
    )
    if not verify_evaluation_time_claim_v1(
        clock_claim_document,
        clock_provider_preregistration_document,
        expected_clock_claim_hash=claim_hash,
        **claim_kwargs,
    ):
        raise ValueError("evaluation time claim is not exact")

    spki_bytes = _decode_canonical_base64(
        public_key_spki_base64,
        "public_key_spki_base64",
    )
    _load_ed25519_public_key(spki_bytes)
    signature_bytes = _decode_canonical_base64(signature_base64, "signature_base64")
    if len(signature_bytes) != 64:
        raise ValueError("Ed25519 signature must be 64 bytes")

    provider = _mapping(clock_provider_preregistration_document)
    identity = _mapping(provider.get("identity"))
    spki_hash = hashlib.sha256(spki_bytes).hexdigest()
    if spki_hash != identity.get("public_key_spki_sha256"):
        raise ValueError("public key hash does not match clock provider preregistration")

    document = {
        "schema_version": SIGNED_CLOCK_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "clock_claim_hash": claim_hash,
        "clock_provider_hash": _require_sha256(
            provider.get("clock_provider_hash"),
            "clock_provider_hash",
        ),
        "signature_algorithm": "ED25519",
        "signature_domain": _SIGNATURE_DOMAIN,
        "signature_message_format": _SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": spki_hash,
        "signature_base64": signature_base64,
        "signature_sha256": hashlib.sha256(signature_bytes).hexdigest(),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "signed_clock_attestation_hash")


def verify_signed_evaluation_time_attestation_v1(
    document: Any,
    clock_claim_document: Any,
    clock_provider_preregistration_document: Any,
    *,
    expected_signed_clock_attestation_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_signed_clock_attestation_hash,
            "expected_signed_clock_attestation_hash",
        )
        rebuilt = build_signed_evaluation_time_attestation_v1(
            clock_claim_document,
            clock_provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("signed_clock_attestation_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_signed_evaluation_time_attestation_v1(
    signed_clock_attestation_document: Any,
    clock_claim_document: Any,
    clock_provider_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_clock_claim_hash: Any,
    expected_signed_clock_attestation_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_clock_claim_hash,
        "expected_clock_claim_hash",
    )
    signed_hash = _require_sha256(
        expected_signed_clock_attestation_hash,
        "expected_signed_clock_attestation_hash",
    )
    signed_exact = verify_signed_evaluation_time_attestation_v1(
        signed_clock_attestation_document,
        clock_claim_document,
        clock_provider_preregistration_document,
        expected_signed_clock_attestation_hash=signed_hash,
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        expected_clock_claim_hash=claim_hash,
        claim_build_kwargs=claim_build_kwargs,
    )

    signature_verified = False
    key_hash_matches = False
    try:
        spki_bytes = _decode_canonical_base64(
            public_key_spki_base64,
            "public_key_spki_base64",
        )
        signature_bytes = _decode_canonical_base64(
            signature_base64,
            "signature_base64",
        )
        public_key = _load_ed25519_public_key(spki_bytes)
        provider = _mapping(clock_provider_preregistration_document)
        identity = _mapping(provider.get("identity"))
        key_hash_matches = (
            hashlib.sha256(spki_bytes).hexdigest()
            == identity.get("public_key_spki_sha256")
        )
        if signed_exact and key_hash_matches:
            public_key.verify(signature_bytes, bytes.fromhex(claim_hash))
            signature_verified = True
    except (InvalidSignature, TypeError, ValueError):
        signature_verified = False

    claim = _mapping(clock_claim_document)
    source = _mapping(claim.get("source"))
    reading = _mapping(claim.get("clock_reading"))
    subject = _mapping(claim.get("subject"))
    local_signature_pass = bool(signed_exact and key_hash_matches and signature_verified)
    checks = [
        _check("SIGNED_CLOCK_ATTESTATION_EXACT", signed_exact),
        _check("CLOCK_KEY_HASH_MATCHES_PREREGISTRATION", key_hash_matches),
        _check("CLOCK_SIGNATURE_VERIFIED", signature_verified),
    ]
    document = {
        "schema_version": CLOCK_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_signature_pass else "BLOCKED",
        "decision": (
            "PREREGISTERED_CLOCK_KEY_SIGNATURE_OBSERVED_"
            "IDENTITY_IMPLEMENTATION_COUNTER_AND_TIME_TRUTH_UNVERIFIED"
            if local_signature_pass
            else "BLOCK_EVALUATION_CLOCK_SIGNATURE_CONTRACT"
        ),
        "source": {
            "clock_provider_hash": _document_sha256(
                source.get("clock_provider_hash")
            ),
            "clock_claim_hash": claim_hash,
            "signed_clock_attestation_hash": signed_hash,
            "clock_public_key_spki_sha256": _document_sha256(
                _mapping(signed_clock_attestation_document).get(
                    "public_key_spki_sha256"
                )
            ),
            "attestation_id_hash": _document_sha256(
                reading.get("attestation_id_hash")
            ),
            "account_scope_hash": _document_sha256(
                source.get("account_scope_hash")
            ),
        },
        "clock_summary": {
            "clock_counter": _document_int(reading.get("clock_counter")),
            "evaluated_at_unix_ms": _document_int(
                reading.get("evaluated_at_unix_ms")
            ),
        },
        "subject": deepcopy(subject),
        "checks": checks,
        "facts": {
            "clock_claim_exact": signed_exact,
            "signed_clock_attestation_exact": signed_exact,
            "clock_key_hash_matches_preregistration": key_hash_matches,
            "cryptographic_signature_verified": signature_verified,
            "preregistered_clock_key_signature_verified": local_signature_pass,
            "clock_provider_identity_verified": False,
            "clock_provider_implementation_verified": False,
            "clock_counter_continuity_verified": False,
            "time_source_truth_verified": False,
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_CLOCK_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "clock_evidence_hash")


def verify_signed_evaluation_time_evidence_v1(
    document: Any,
    *args: Any,
    expected_clock_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_clock_evidence_hash,
            "expected_clock_evidence_hash",
        )
        rebuilt = evaluate_signed_evaluation_time_attestation_v1(*args, **kwargs)
    except Exception:
        return False
    return (
        rebuilt.get("clock_evidence_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v7(
    clock_evidence_document: Any,
    signed_clock_attestation_document: Any,
    clock_claim_document: Any,
    clock_provider_preregistration_document: Any,
    transition_document: Any,
    previous_state_document: Any,
    policy_document: Any,
    snapshot_evidence_document: Any,
    signed_snapshot_document: Any,
    snapshot_claim_document: Any,
    snapshot_provider_preregistration_document: Any,
    correlation_preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    expected_clock_evidence_hash: Any,
    clock_evaluation_kwargs: Any,
    expected_transition_hash: Any,
    transition_evaluation_kwargs: Any,
    expected_current_state_hash: Any,
    expected_snapshot_evidence_hash: Any,
    snapshot_evaluation_kwargs: Any,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
    positions_after: Any = None,
    risk_reduction_transition: Any = None,
) -> dict[str, Any]:
    clock_evidence_hash = _require_sha256(
        expected_clock_evidence_hash,
        "expected_clock_evidence_hash",
    )
    transition_hash = _require_sha256(
        expected_transition_hash,
        "expected_transition_hash",
    )
    current_state_hash = _require_sha256(
        expected_current_state_hash,
        "expected_current_state_hash",
    )
    snapshot_evidence_hash = _require_sha256(
        expected_snapshot_evidence_hash,
        "expected_snapshot_evidence_hash",
    )
    clock_kwargs = _require_mapping(
        clock_evaluation_kwargs,
        "clock_evaluation_kwargs",
    )
    transition_kwargs = _require_mapping(
        transition_evaluation_kwargs,
        "transition_evaluation_kwargs",
    )
    snapshot_kwargs = _require_mapping(
        snapshot_evaluation_kwargs,
        "snapshot_evaluation_kwargs",
    )

    clock_evidence_exact = verify_signed_evaluation_time_evidence_v1(
        clock_evidence_document,
        signed_clock_attestation_document,
        clock_claim_document,
        clock_provider_preregistration_document,
        expected_clock_evidence_hash=clock_evidence_hash,
        **clock_kwargs,
    )
    clock_evidence = _mapping(clock_evidence_document)
    clock_facts = _mapping(clock_evidence.get("facts"))
    clock_source = _mapping(clock_evidence.get("source"))
    clock_summary = _mapping(clock_evidence.get("clock_summary"))
    clock_subject = _mapping(clock_evidence.get("subject"))
    signed_clock_pass = bool(
        clock_evidence_exact
        and clock_evidence.get("status") == "PASS"
        and clock_facts.get("preregistered_clock_key_signature_verified") is True
    )
    evaluation_time = _document_int(clock_summary.get("evaluated_at_unix_ms"))

    if signed_clock_pass and evaluation_time is not None:
        try:
            v6_result = (
                budget_v6.evaluate_strategy_correlation_cluster_effective_bet_budget_v6(
                    transition_document,
                    previous_state_document,
                    policy_document,
                    snapshot_evidence_document,
                    signed_snapshot_document,
                    snapshot_claim_document,
                    snapshot_provider_preregistration_document,
                    correlation_preregistration,
                    correlation_matrix,
                    complete_link_audit,
                    expected_transition_hash=transition_hash,
                    transition_evaluation_kwargs=transition_kwargs,
                    expected_current_state_hash=current_state_hash,
                    expected_snapshot_evidence_hash=snapshot_evidence_hash,
                    snapshot_evaluation_kwargs=snapshot_kwargs,
                    evaluated_at_unix_ms=evaluation_time,
                    strata_registration=strata_registration,
                    strata_gate=strata_gate,
                    complete_link_gate=complete_link_gate,
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                    risk_increasing=risk_increasing,
                    positions_after=positions_after,
                    risk_reduction_transition=risk_reduction_transition,
                )
            )
        except Exception:
            v6_result = {}
    else:
        v6_result = {}

    v6_document = _mapping(v6_result)
    v6_source = _mapping(v6_document.get("source"))
    v6_authority = _mapping(v6_document.get("authority"))
    policy = _mapping(policy_document)
    policy_source = _mapping(policy.get("source"))
    clock_provider = _mapping(clock_provider_preregistration_document)
    clock_identity = _mapping(clock_provider.get("identity"))

    subject_binding_exact = bool(
        signed_clock_pass
        and clock_subject.get("purpose")
        == "STRATEGY_CORRELATION_EFFECTIVE_BET_BUDGET"
        and clock_subject.get("policy_hash")
        == policy.get("policy_hash")
        == v6_source.get("policy_hash")
        and clock_subject.get("transition_hash")
        == transition_hash
        == v6_source.get("transition_hash")
        and clock_subject.get("current_state_hash")
        == current_state_hash
        == v6_source.get("current_state_hash")
        and clock_subject.get("snapshot_claim_hash")
        == v6_source.get("snapshot_claim_hash")
    )
    account_scope_binding_exact = bool(
        signed_clock_pass
        and clock_source.get("account_scope_hash")
        == clock_identity.get("account_scope_hash")
        == policy_source.get("account_scope_hash")
    )
    v6_local_pass = bool(
        v6_document.get("status") == "PASS"
        and v6_document.get("blockers") == []
    )
    v6_authority_locked = bool(
        v6_document.get("admission_status") == "BLOCKED"
        and v6_authority.get("current_admission_allowed") is False
        and v6_authority.get("paper_authorized") is False
        and v6_authority.get("live_order_allowed") is False
    )

    checks = [
        _check("SIGNED_CLOCK_EVIDENCE_EXACT", clock_evidence_exact),
        _check("SIGNED_CLOCK_KEY_SIGNATURE_PASS", signed_clock_pass),
        _check("CLOCK_SUBJECT_BINDING_EXACT", subject_binding_exact),
        _check("CLOCK_ACCOUNT_SCOPE_BINDING_EXACT", account_scope_binding_exact),
        _check("V6_EFFECTIVE_BUDGET_PASS", v6_local_pass),
        _check("V6_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v6_authority_locked),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_SIGNED_EVALUATION_TIME_BOUND_EFFECTIVE_BUDGET_"
            "CLOCK_IDENTITY_IMPLEMENTATION_TIME_TRUTH_AND_ATOMIC_HEAD_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_SIGNED_EVALUATION_TIME_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "clock_provider_hash": _document_sha256(
                clock_source.get("clock_provider_hash")
            ),
            "clock_claim_hash": _document_sha256(
                clock_source.get("clock_claim_hash")
            ),
            "signed_clock_attestation_hash": _document_sha256(
                clock_source.get("signed_clock_attestation_hash")
            ),
            "clock_evidence_hash": clock_evidence_hash,
            "policy_hash": _document_sha256(v6_source.get("policy_hash")),
            "transition_hash": transition_hash,
            "current_state_hash": current_state_hash,
            "snapshot_claim_hash": _document_sha256(
                v6_source.get("snapshot_claim_hash")
            ),
            "snapshot_evidence_hash": snapshot_evidence_hash,
            "v6_budget_hash": _document_sha256(v6_document.get("budget_v6_hash")),
        },
        "clock_summary": {
            "attestation_id_hash": _document_sha256(
                clock_source.get("attestation_id_hash")
            ),
            "clock_counter": _document_int(clock_summary.get("clock_counter")),
            "evaluated_at_unix_ms": evaluation_time,
        },
        "snapshot_summary": deepcopy(v6_document.get("snapshot_summary")),
        "budget_summary": deepcopy(v6_document.get("budget_summary")),
        "checks": checks,
        "facts": {
            "clock_evidence_exact": clock_evidence_exact,
            "preregistered_clock_key_signature_verified": signed_clock_pass,
            "signed_evaluation_time_bound_to_budget": subject_binding_exact,
            "clock_account_scope_bound_to_snapshot_policy": account_scope_binding_exact,
            "caller_evaluation_time_input_accepted": False,
            "predecessor_admission_authority_preserved_blocked": (
                v6_authority_locked
            ),
            "clock_provider_identity_verified": False,
            "clock_provider_implementation_verified": False,
            "clock_counter_continuity_verified": False,
            "trusted_evaluation_clock_verified": False,
            "time_source_truth_verified": False,
            "atomic_current_head_persistence_verified": False,
            "snapshot_source_truth_verified": False,
            "runtime_gate_integrated": False,
            "execution_verified": False,
            "profitability_proven": False,
            "raw_public_key_embedded": False,
            "raw_signature_embedded": False,
            "raw_positions_embedded": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_CLOCK_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "budget_v7_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v7(
    document: Any,
    *args: Any,
    expected_budget_v7_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v7_hash,
            "expected_budget_v7_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v7(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v7_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
