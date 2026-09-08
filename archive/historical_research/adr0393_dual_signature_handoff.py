"""Exact dual-signature handoff for ADR0393, with no runtime authority."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_registration_challenge_signed_source_v1 as challenge_source,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_signed_registration_v1 as provider_registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


HANDOFF_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-registration-challenge-"
    "consumption-provider-registration-challenge-handoff-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-challenge-consumption-provider-registration-challenge-"
    "handoff-v1-synthetic-lock-1"
)
CHALLENGE_SOURCE_IMPLEMENTATION_SHA256 = (
    "c5fb0854eda601ec20aeb4c3c532308be0231d4069886fdaecb41b275033a2fe"
)
PROVIDER_SIGNED_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "4e3ea7637734c9a7393ff1ab1ed668bd26710430511d72a1a5c54b702b43c145"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")


class ChallengeConsumptionProviderRegistrationChallengeHandoffError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ChallengeConsumptionProviderRegistrationChallengeHandoffError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_kwargs(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ChallengeConsumptionProviderRegistrationChallengeHandoffError(
            f"{label} must be a dict"
        )
    return copy.deepcopy(value)


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def _authority() -> dict[str, bool]:
    return {
        "challenge_consumption_allowed": False,
        "provider_registration_allowed": False,
        "external_conformance_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def evaluate_challenge_consumption_provider_registration_challenge_handoff_v1(
    challenge_evidence_document: Any,
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    provider_registration_evidence_document: Any,
    signed_provider_registration_document: Any,
    provider_registration_claim_document: Any,
    *,
    expected_challenge_evidence_hash: Any,
    expected_provider_registration_evidence_hash: Any,
    challenge_evaluation_kwargs: Any,
    provider_registration_evaluation_kwargs: Any,
) -> dict[str, Any]:
    challenge_evidence_exact = False
    provider_registration_evidence_exact = False
    challenge_source_key_signature_verified = False
    provider_key_signature_verified = False
    signed_challenge_hash_bound = False
    registration_nonce_bound = False
    provider_preregistration_bound = False
    signed_challenge_hash: str | None = None
    challenge_hash: str | None = None
    registration_claim_hash: str | None = None
    provider_preregistration_hash: str | None = None

    try:
        challenge_kwargs = _require_kwargs(
            challenge_evaluation_kwargs, "challenge_evaluation_kwargs"
        )
        registration_kwargs = _require_kwargs(
            provider_registration_evaluation_kwargs,
            "provider_registration_evaluation_kwargs",
        )
        expected_challenge_evidence = (
            challenge_source.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                signed_challenge_document,
                challenge_document,
                provider_preregistration_document,
                challenge_authority_preregistration_document,
                **challenge_kwargs,
            )
        )
        expected_challenge_hash = _require_hash(
            expected_challenge_evidence_hash,
            "expected_challenge_evidence_hash",
        )
        challenge_evidence_exact = (
            challenge_evidence_document == expected_challenge_evidence
            and expected_challenge_hash
            == expected_challenge_evidence["verification_evidence_hash"]
        )
        expected_provider_evidence = (
            provider_registration.evaluate_signed_challenge_consumption_provider_registration_v1(
                signed_provider_registration_document,
                provider_registration_claim_document,
                provider_preregistration_document,
                **registration_kwargs,
            )
        )
        expected_provider_hash = _require_hash(
            expected_provider_registration_evidence_hash,
            "expected_provider_registration_evidence_hash",
        )
        provider_registration_evidence_exact = (
            provider_registration_evidence_document == expected_provider_evidence
            and expected_provider_hash
            == expected_provider_evidence["verification_evidence_hash"]
        )
        challenge_source_key_signature_verified = (
            challenge_evidence_exact
            and expected_challenge_evidence["status"] == "PASS"
            and expected_challenge_evidence["facts"][
                "preregistered_challenge_key_signature_verified"
            ]
            is True
        )
        provider_key_signature_verified = (
            provider_registration_evidence_exact
            and expected_provider_evidence["status"] == "PASS"
            and expected_provider_evidence["facts"][
                "preregistered_key_signature_verified"
            ]
            is True
        )

        signed_challenge_hash = _require_hash(
            signed_challenge_document["signed_challenge_hash"],
            "signed_challenge_hash",
        )
        challenge_hash = _require_hash(
            challenge_document["challenge_hash"], "challenge_hash"
        )
        registration_claim_hash = _require_hash(
            provider_registration_claim_document["claim_hash"],
            "provider_registration_claim_hash",
        )
        provider_preregistration_hash = _require_hash(
            provider_preregistration_document["preregistration_hash"],
            "provider_preregistration_hash",
        )
        signed_challenge_hash_bound = (
            signed_challenge_document["challenge_hash"] == challenge_hash
            and provider_registration_claim_document["binding"]["challenge_hash"]
            == signed_challenge_hash
            and expected_challenge_evidence["source"]["signed_challenge_hash"]
            == signed_challenge_hash
            and expected_provider_evidence["source"]["claim_hash"]
            == registration_claim_hash
        )
        registration_nonce_bound = (
            challenge_document["binding"]["registration_nonce_hash"]
            == provider_registration_claim_document["binding"][
                "registration_nonce_hash"
            ]
        )
        provider_preregistration_bound = (
            challenge_document["source"]["provider_preregistration_hash"]
            == provider_preregistration_hash
            and provider_registration_claim_document["source"][
                "preregistration_hash"
            ]
            == provider_preregistration_hash
            and expected_challenge_evidence["source"][
                "provider_preregistration_hash"
            ]
            == provider_preregistration_hash
            and expected_provider_evidence["source"]["preregistration_hash"]
            == provider_preregistration_hash
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    handoff_exact = (
        challenge_source_key_signature_verified
        and provider_key_signature_verified
        and signed_challenge_hash_bound
        and registration_nonce_bound
        and provider_preregistration_bound
    )
    facts = {
        "challenge_evidence_exact": challenge_evidence_exact,
        "provider_registration_evidence_exact": (
            provider_registration_evidence_exact
        ),
        "challenge_source_key_signature_verified": (
            challenge_source_key_signature_verified
        ),
        "provider_key_signature_verified": provider_key_signature_verified,
        "signed_challenge_hash_bound_to_registration_claim": (
            signed_challenge_hash_bound
        ),
        "registration_nonce_bound_end_to_end": registration_nonce_bound,
        "provider_preregistration_bound_end_to_end": (
            provider_preregistration_bound
        ),
        "dual_signature_handoff_exact": handoff_exact,
        "challenge_authority_identity_verified": False,
        "challenge_authority_implementation_verified": False,
        "challenge_time_source_authoritative": False,
        "current_time_established": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "provider_registered": False,
        "provider_identity_verified": False,
        "provider_implementation_verified": False,
        "provider_key_control_continuity_verified": False,
        "external_provider_conformance_verified": False,
        "external_atomicity_verified": False,
        "durability_verified": False,
        "linearizability_verified": False,
        "raw_public_keys_redacted": True,
        "raw_signatures_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }
    blockers = [
        "CHALLENGE_AUTHORITY_IDENTITY_UNVERIFIED",
        "CHALLENGE_AUTHORITY_IMPLEMENTATION_UNVERIFIED",
        "CLAIMED_TIME_SOURCE_UNVERIFIED",
        "CURRENT_TIME_UNESTABLISHED",
        "CHALLENGE_FRESHNESS_UNVERIFIED",
        "REGISTRATION_REPLAY_UNCONSUMED",
        "PROVIDER_IDENTITY_UNVERIFIED",
        "PROVIDER_IMPLEMENTATION_UNVERIFIED",
        "PROVIDER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
        "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
        "EXTERNAL_ATOMICITY_DURABILITY_LINEARIZABILITY_UNVERIFIED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not handoff_exact:
        blockers.insert(
            0, "SIGNED_REGISTRATION_CHALLENGE_HANDOFF_UNKNOWN_OR_INVALID"
        )
    evidence = {
        "schema_version": HANDOFF_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if handoff_exact else "BLOCK",
        "decision": (
            "DUAL_SIGNATURE_HANDOFF_EXACT_FRESHNESS_AND_CONSUMPTION_UNVERIFIED"
            if handoff_exact
            else "SIGNED_REGISTRATION_CHALLENGE_HANDOFF_UNKNOWN_OR_INVALID"
        ),
        "registration_status": "BLOCKED",
        "source": {
            "challenge_source_implementation_sha256": (
                CHALLENGE_SOURCE_IMPLEMENTATION_SHA256
            ),
            "provider_signed_registration_implementation_sha256": (
                PROVIDER_SIGNED_REGISTRATION_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "provider_preregistration_hash": _safe_hash(
                provider_preregistration_hash
            ),
            "challenge_hash": _safe_hash(challenge_hash),
            "signed_challenge_hash": _safe_hash(signed_challenge_hash),
            "provider_registration_claim_hash": _safe_hash(
                registration_claim_hash
            ),
            "challenge_evidence_hash": _safe_hash(
                expected_challenge_evidence_hash
            ),
            "provider_registration_evidence_hash": _safe_hash(
                expected_provider_registration_evidence_hash
            ),
        },
        "facts": facts,
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(evidence, "handoff_evidence_hash")


def verify_challenge_consumption_provider_registration_challenge_handoff_v1(
    evidence_document: Any,
    *evaluation_args: Any,
    expected_handoff_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    try:
        expected = (
            evaluate_challenge_consumption_provider_registration_challenge_handoff_v1(
                *evaluation_args, **evaluation_kwargs
            )
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_handoff_evidence_hash,
                "expected_handoff_evidence_hash",
            )
            == expected["handoff_evidence_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderRegistrationChallengeHandoffError):
        return False


__all__ = [
    "CHALLENGE_SOURCE_IMPLEMENTATION_SHA256",
    "HANDOFF_EVIDENCE_SCHEMA_VERSION",
    "PROVIDER_SIGNED_REGISTRATION_IMPLEMENTATION_SHA256",
    "ChallengeConsumptionProviderRegistrationChallengeHandoffError",
    "evaluate_challenge_consumption_provider_registration_challenge_handoff_v1",
    "verify_challenge_consumption_provider_registration_challenge_handoff_v1",
]
