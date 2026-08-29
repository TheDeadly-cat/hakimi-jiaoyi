"""Threshold-signed synthetic genesis admission and unreserved replay key."""

from __future__ import annotations

import base64
import binascii
import copy
import re
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.application import (
    challenge_consumption_provider_bootstrap_topology_v1 as bootstrap,
)
from exchange_terminal.application import (
    challenge_consumption_provider_registration_clock_binding_v1 as clock_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION = (
    "challenge-consumption-provider-threshold-genesis-admission-claim-v1"
)
SIGNED_GENESIS_ADMISSION_SCHEMA_VERSION = (
    "challenge-consumption-provider-threshold-genesis-admission-candidate-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "challenge-consumption-provider-threshold-genesis-admission-evidence-v1"
)
GENESIS_ADMISSION_REPLAY_KEY_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-admission-replay-key-v1"
)
STATIC_FINGERPRINT = (
    "20260824-challenge-consumption-provider-threshold-genesis-admission-"
    "v1-synthetic-lock-1"
)
BOOTSTRAP_TOPOLOGY_IMPLEMENTATION_SHA256 = (
    "ac39291a0f0e62bb47b42163cbf78ddd712f290ca1061b6ef9784700eb0c7e1d"
)
CLOCK_BINDING_IMPLEMENTATION_SHA256 = (
    "f57ee0863658e80a751d29884c77672441d82149109e488975e756314b3361b9"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_DOMAIN = (
    "hakimi.challenge-consumption-provider.threshold-genesis-admission.v1"
)
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_SIGNATURE_FIELDS = {"public_key_spki_base64", "signature_base64"}


class ChallengeConsumptionProviderThresholdGenesisAdmissionError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} must be a strict identifier"
        )
    return value


def _decode_base64(
    value: Any, label: str, *, expected_length: int | None = None
) -> bytes:
    if type(value) is not str or not value:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        )
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        ) from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        )
    if expected_length is not None and len(decoded) != expected_length:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            f"{label} length mismatch"
        )
    return decoded


def _load_ed25519_spki(value: Any) -> tuple[Ed25519PublicKey, bytes]:
    der = _decode_base64(value, "public_key_spki_base64")
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "public key must be canonical Ed25519 DER-SPKI"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "public key must be Ed25519"
        )
    canonical = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical != der:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "public key DER-SPKI is not canonical"
        )
    return key, der


def _authority() -> dict[str, bool]:
    return {
        "genesis_admission_allowed": False,
        "replay_reservation_allowed": False,
        "challenge_consumption_allowed": False,
        "provider_registration_allowed": False,
        "external_conformance_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _exact_topology(
    topology_document: Any,
    provider_preregistration_document: Any,
    topology_build_kwargs: Any,
) -> dict[str, Any]:
    if type(topology_build_kwargs) is not dict:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "topology_build_kwargs must be a dict"
        )
    try:
        expected = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                provider_preregistration_document,
                **copy.deepcopy(topology_build_kwargs),
            )
        )
    except (TypeError, ValueError) as exc:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "bootstrap topology kwargs are invalid"
        ) from exc
    if topology_document != expected:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "bootstrap topology is not exact"
        )
    return expected


def _exact_clock_binding(
    clock_binding_evidence: Any,
    provider_preregistration_document: Any,
    *,
    expected_clock_binding_evidence_hash: Any,
    clock_binding_verification_args: Any,
    clock_binding_verification_kwargs: Any,
) -> dict[str, Any]:
    if type(clock_binding_verification_args) not in (list, tuple):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock_binding_verification_args must be a list or tuple"
        )
    if len(clock_binding_verification_args) != 13:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock binding verification args length mismatch"
        )
    if clock_binding_verification_args[8] != provider_preregistration_document:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock binding provider preregistration is not exact"
        )
    if type(clock_binding_verification_kwargs) is not dict:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock_binding_verification_kwargs must be a dict"
        )
    if "expected_clock_binding_evidence_hash" in clock_binding_verification_kwargs:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock binding evidence hash must be passed separately"
        )
    expected_hash = _require_hash(
        expected_clock_binding_evidence_hash,
        "expected_clock_binding_evidence_hash",
    )
    args = copy.deepcopy(tuple(clock_binding_verification_args))
    kwargs = copy.deepcopy(clock_binding_verification_kwargs)
    if not clock_binding.verify_challenge_consumption_provider_registration_clock_binding_v1(
        clock_binding_evidence,
        *args,
        expected_clock_binding_evidence_hash=expected_hash,
        **kwargs,
    ):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock binding evidence is not exact"
        )
    if (
        type(clock_binding_evidence) is not dict
        or clock_binding_evidence.get("status") != "PASS"
    ):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "clock binding evidence is not a local PASS"
        )
    return clock_binding_evidence


def build_challenge_consumption_provider_genesis_admission_claim_v1(
    provider_preregistration_document: Any,
    topology_document: Any,
    clock_binding_evidence: Any,
    *,
    admission_nonce_hash: Any,
    expected_genesis_registry_head_hash: Any,
    expected_clock_binding_evidence_hash: Any,
    topology_build_kwargs: Any,
    clock_binding_verification_args: Any,
    clock_binding_verification_kwargs: Any,
) -> dict[str, Any]:
    topology = _exact_topology(
        topology_document,
        provider_preregistration_document,
        topology_build_kwargs,
    )
    clock_evidence = _exact_clock_binding(
        clock_binding_evidence,
        provider_preregistration_document,
        expected_clock_binding_evidence_hash=(
            expected_clock_binding_evidence_hash
        ),
        clock_binding_verification_args=clock_binding_verification_args,
        clock_binding_verification_kwargs=clock_binding_verification_kwargs,
    )
    nonce_hash = _require_hash(admission_nonce_hash, "admission_nonce_hash")
    expected_head = _require_hash(
        expected_genesis_registry_head_hash,
        "expected_genesis_registry_head_hash",
    )
    if nonce_hash == expected_head:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "admission nonce and expected genesis head must be distinct"
        )
    root_set = topology["bootstrap_root"]["root_authority_set"]
    candidate = topology["candidate_binding"]
    document = {
        "schema_version": GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "GENESIS_ADMISSION_CLAIM_UNSIGNED_EXTERNAL_ROOT_GOVERNANCE_"
            "GENESIS_EXECUTION_AND_REPLAY_RESERVATION_UNVERIFIED"
        ),
        "source": {
            "bootstrap_topology_hash": topology["bootstrap_topology_hash"],
            "root_authority_set_hash": root_set["root_authority_set_hash"],
            "provider_preregistration_hash": topology["source"][
                "provider_preregistration_hash"
            ],
            "clock_binding_evidence_hash": clock_evidence[
                "clock_binding_evidence_hash"
            ],
            "signed_challenge_hash": clock_evidence["source"][
                "signed_challenge_hash"
            ],
            "bootstrap_topology_implementation_sha256": (
                BOOTSTRAP_TOPOLOGY_IMPLEMENTATION_SHA256
            ),
            "clock_binding_implementation_sha256": (
                CLOCK_BINDING_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "binding": {
            "genesis_registry_namespace": bootstrap.GENESIS_REGISTRY_NAMESPACE,
            "admission_nonce_hash": nonce_hash,
            "expected_genesis_registry_head_hash": expected_head,
            "target_provider_revision": 0,
            "candidate_registry_id": candidate["registry_id"],
            "candidate_public_key_spki_sha256": candidate[
                "public_key_spki_sha256"
            ],
            "candidate_provider_implementation_claim_sha256": candidate[
                "provider_implementation_claim_sha256"
            ],
            "minimum_root_signatures": root_set[
                "minimum_root_signatures"
            ],
            "root_authority_count": root_set["authority_count"],
        },
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "bootstrap_topology_exact": True,
            "clock_binding_evidence_exact": True,
            "claim_bindings_exact": True,
            "threshold_root_signatures_verified": False,
            "external_root_identity_verified": False,
            "external_root_governance_verified": False,
            "root_member_independence_verified": False,
            "trusted_current_time_established": False,
            "challenge_freshness_verified": False,
            "genesis_replay_key_reserved": False,
            "atomic_genesis_registry_create_verified": False,
            "provider_registered": False,
            "external_provider_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "THRESHOLD_ROOT_SIGNATURES_UNVERIFIED",
            "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
            "EXTERNAL_ROOT_GOVERNANCE_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "TRUSTED_CURRENT_TIME_UNESTABLISHED",
            "CHALLENGE_FRESHNESS_UNVERIFIED",
            "GENESIS_ADMISSION_REPLAY_UNRESERVED",
            "ATOMIC_GENESIS_REGISTRY_CREATE_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "genesis_admission_claim_hash")


def verify_challenge_consumption_provider_genesis_admission_claim_v1(
    document: Any,
    *args: Any,
    expected_genesis_admission_claim_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = build_challenge_consumption_provider_genesis_admission_claim_v1(
            *args, **kwargs
        )
        return (
            document == expected
            and _require_hash(
                expected_genesis_admission_claim_hash,
                "expected_genesis_admission_claim_hash",
            )
            == expected["genesis_admission_claim_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderThresholdGenesisAdmissionError):
        return False


def _exact_claim(
    claim_document: Any,
    provider_preregistration_document: Any,
    topology_document: Any,
    clock_binding_evidence: Any,
    expected_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    if type(claim_build_kwargs) is not dict:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "claim_build_kwargs must be a dict"
        )
    expected = build_challenge_consumption_provider_genesis_admission_claim_v1(
        provider_preregistration_document,
        topology_document,
        clock_binding_evidence,
        **copy.deepcopy(claim_build_kwargs),
    )
    claim_hash = _require_hash(expected_claim_hash, "expected_claim_hash")
    if (
        claim_document != expected
        or claim_hash != expected["genesis_admission_claim_hash"]
    ):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "genesis admission claim is not exact"
        )
    return expected


def build_threshold_signed_genesis_admission_v1(
    claim_document: Any,
    provider_preregistration_document: Any,
    topology_document: Any,
    clock_binding_evidence: Any,
    *,
    signatures_by_authority_id: Any,
    expected_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    expected_claim = _exact_claim(
        claim_document,
        provider_preregistration_document,
        topology_document,
        clock_binding_evidence,
        expected_claim_hash,
        claim_build_kwargs,
    )
    if type(signatures_by_authority_id) is not dict:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "signatures_by_authority_id must be a dict"
        )
    if not 1 <= len(signatures_by_authority_id) <= 7:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "signature count must be between 1 and 7"
        )
    records = []
    for authority_id, material in signatures_by_authority_id.items():
        identifier = _require_identifier(authority_id, "authority_id")
        if type(material) is not dict or set(material) != _SIGNATURE_FIELDS:
            raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
                f"signature material fields are not exact for {identifier}"
            )
        _, der = _load_ed25519_spki(material["public_key_spki_base64"])
        signature = _decode_base64(
            material["signature_base64"],
            "signature_base64",
            expected_length=64,
        )
        records.append(
            {
                "authority_id": identifier,
                "public_key_spki_base64": material["public_key_spki_base64"],
                "public_key_spki_sha256": sha256(der).hexdigest(),
                "signature_base64": material["signature_base64"],
                "signature_sha256": sha256(signature).hexdigest(),
            }
        )
    records.sort(key=lambda item: item["authority_id"])
    document = {
        "schema_version": SIGNED_GENESIS_ADMISSION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "genesis_admission_claim_hash": expected_claim[
            "genesis_admission_claim_hash"
        ],
        "bootstrap_topology_hash": expected_claim["source"][
            "bootstrap_topology_hash"
        ],
        "root_authority_set_hash": expected_claim["source"][
            "root_authority_set_hash"
        ],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "claimed_signer_count": len(records),
        "signatures": records,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "signed_genesis_admission_hash")


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def evaluate_threshold_signed_genesis_admission_v1(
    signed_admission_document: Any,
    claim_document: Any,
    provider_preregistration_document: Any,
    topology_document: Any,
    clock_binding_evidence: Any,
    *,
    signatures_by_authority_id: Any,
    expected_claim_hash: Any,
    expected_signed_admission_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_exact = False
    signed_exact = False
    all_supplied_signatures_valid = False
    threshold_met = False
    valid_signer_ids: list[str] = []
    cryptographic_signature_count = 0
    registered_key_match_count = 0
    minimum_root_signatures = None
    root_authority_count = None
    claim_hash = _safe_hash(expected_claim_hash)
    signed_hash = _safe_hash(expected_signed_admission_hash)
    topology_hash = None
    root_set_hash = None
    clock_hash = None
    try:
        expected_claim = _exact_claim(
            claim_document,
            provider_preregistration_document,
            topology_document,
            clock_binding_evidence,
            expected_claim_hash,
            claim_build_kwargs,
        )
        claim_exact = True
        expected_signed = build_threshold_signed_genesis_admission_v1(
            claim_document,
            provider_preregistration_document,
            topology_document,
            clock_binding_evidence,
            signatures_by_authority_id=signatures_by_authority_id,
            expected_claim_hash=expected_claim["genesis_admission_claim_hash"],
            claim_build_kwargs=claim_build_kwargs,
        )
        signed_exact = (
            signed_admission_document == expected_signed
            and _require_hash(
                expected_signed_admission_hash,
                "expected_signed_admission_hash",
            )
            == expected_signed["signed_genesis_admission_hash"]
        )
        root_set = topology_document["bootstrap_root"]["root_authority_set"]
        root_by_id = {
            item["authority_id"]: item
            for item in root_set["authorities"]
        }
        minimum_root_signatures = root_set["minimum_root_signatures"]
        root_authority_count = root_set["authority_count"]
        topology_hash = topology_document["bootstrap_topology_hash"]
        root_set_hash = root_set["root_authority_set_hash"]
        clock_hash = clock_binding_evidence["clock_binding_evidence_hash"]
        supplied_valid = []
        for record in expected_signed["signatures"]:
            key, der = _load_ed25519_spki(record["public_key_spki_base64"])
            signature = _decode_base64(
                record["signature_base64"],
                "signature_base64",
                expected_length=64,
            )
            try:
                key.verify(
                    signature,
                    bytes.fromhex(
                        expected_claim["genesis_admission_claim_hash"]
                    ),
                )
                cryptographic_signature_count += 1
                cryptographic_valid = True
            except InvalidSignature:
                cryptographic_valid = False
            registered = root_by_id.get(record["authority_id"])
            key_matches = (
                registered is not None
                and sha256(der).hexdigest()
                == registered["public_key_spki_sha256"]
            )
            if key_matches:
                registered_key_match_count += 1
            valid = cryptographic_valid and key_matches
            supplied_valid.append(valid)
            if valid:
                valid_signer_ids.append(record["authority_id"])
        all_supplied_signatures_valid = bool(supplied_valid) and all(
            supplied_valid
        )
        threshold_met = (
            all_supplied_signatures_valid
            and len(valid_signer_ids) >= minimum_root_signatures
        )
    except (KeyError, TypeError, ValueError):
        pass

    local_threshold_verified = (
        claim_exact
        and signed_exact
        and all_supplied_signatures_valid
        and threshold_met
    )
    facts = {
        "genesis_admission_claim_exact": claim_exact,
        "signed_admission_document_exact": signed_exact,
        "all_supplied_signatures_cryptographically_and_structurally_valid": (
            all_supplied_signatures_valid
        ),
        "strict_majority_threshold_met": threshold_met,
        "threshold_root_signatures_verified": local_threshold_verified,
        "external_root_identity_verified": False,
        "external_root_governance_verified": False,
        "root_member_independence_verified": False,
        "trusted_current_time_established": False,
        "challenge_freshness_verified": False,
        "genesis_admission_replay_reserved": False,
        "atomic_genesis_registry_create_verified": False,
        "provider_registered": False,
        "external_provider_conformance_verified": False,
        "raw_public_keys_redacted": True,
        "raw_signatures_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }
    blockers = [
        "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
        "EXTERNAL_ROOT_GOVERNANCE_UNVERIFIED",
        "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
        "TRUSTED_CURRENT_TIME_UNESTABLISHED",
        "CHALLENGE_FRESHNESS_UNVERIFIED",
        "GENESIS_ADMISSION_REPLAY_UNRESERVED",
        "ATOMIC_GENESIS_REGISTRY_CREATE_UNVERIFIED",
        "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not local_threshold_verified:
        blockers.insert(0, "THRESHOLD_GENESIS_ADMISSION_UNKNOWN_OR_INVALID")
    evidence = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_threshold_verified else "BLOCK",
        "decision": (
            "STRICT_MAJORITY_ROOT_SIGNATURES_OBSERVED_GENESIS_EXECUTION_"
            "AND_REPLAY_RESERVATION_UNVERIFIED"
            if local_threshold_verified
            else "THRESHOLD_GENESIS_ADMISSION_UNKNOWN_OR_INVALID"
        ),
        "admission_status": "BLOCKED",
        "source": {
            "bootstrap_topology_hash": _safe_hash(topology_hash),
            "root_authority_set_hash": _safe_hash(root_set_hash),
            "clock_binding_evidence_hash": _safe_hash(clock_hash),
            "genesis_admission_claim_hash": claim_hash,
            "signed_genesis_admission_hash": signed_hash,
        },
        "threshold_observation": {
            "root_authority_count": root_authority_count,
            "minimum_root_signatures": minimum_root_signatures,
            "supplied_signer_count": (
                len(signatures_by_authority_id)
                if type(signatures_by_authority_id) is dict
                else None
            ),
            "cryptographic_signature_count": cryptographic_signature_count,
            "registered_key_match_count": registered_key_match_count,
            "valid_registered_signer_count": len(valid_signer_ids),
            "valid_signer_ids": sorted(valid_signer_ids),
        },
        "facts": facts,
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(evidence, "verification_evidence_hash")


def verify_threshold_signed_genesis_admission_evidence_v1(
    evidence_document: Any,
    *args: Any,
    expected_verification_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = evaluate_threshold_signed_genesis_admission_v1(
            *args, **kwargs
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_verification_evidence_hash,
                "expected_verification_evidence_hash",
            )
            == expected["verification_evidence_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderThresholdGenesisAdmissionError):
        return False


def build_genesis_admission_replay_key_v1(
    evidence_document: Any,
    signed_admission_document: Any,
    claim_document: Any,
    provider_preregistration_document: Any,
    topology_document: Any,
    clock_binding_evidence: Any,
    *,
    expected_verification_evidence_hash: Any,
    evaluation_kwargs: Any,
) -> dict[str, Any]:
    if type(evaluation_kwargs) is not dict:
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "evaluation_kwargs must be a dict"
        )
    expected = evaluate_threshold_signed_genesis_admission_v1(
        signed_admission_document,
        claim_document,
        provider_preregistration_document,
        topology_document,
        clock_binding_evidence,
        **copy.deepcopy(evaluation_kwargs),
    )
    expected_evidence_hash = _require_hash(
        expected_verification_evidence_hash,
        "expected_verification_evidence_hash",
    )
    if (
        evidence_document != expected
        or expected_evidence_hash != expected["verification_evidence_hash"]
        or expected["status"] != "PASS"
    ):
        raise ChallengeConsumptionProviderThresholdGenesisAdmissionError(
            "threshold genesis admission evidence is not an exact local PASS"
        )
    document = {
        "schema_version": GENESIS_ADMISSION_REPLAY_KEY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "GENESIS_ADMISSION_REPLAY_KEY_DERIVED_EXACTLY_RESERVATION_"
            "DURABILITY_AND_GENESIS_EXECUTION_UNVERIFIED"
        ),
        "source": {
            "bootstrap_topology_hash": topology_document[
                "bootstrap_topology_hash"
            ],
            "root_authority_set_hash": topology_document["bootstrap_root"][
                "root_authority_set"
            ]["root_authority_set_hash"],
            "provider_preregistration_hash": claim_document["source"][
                "provider_preregistration_hash"
            ],
            "clock_binding_evidence_hash": clock_binding_evidence[
                "clock_binding_evidence_hash"
            ],
            "genesis_admission_claim_hash": claim_document[
                "genesis_admission_claim_hash"
            ],
            "signed_genesis_admission_hash": signed_admission_document[
                "signed_genesis_admission_hash"
            ],
            "verification_evidence_hash": expected_evidence_hash,
        },
        "binding": {
            "genesis_registry_namespace": claim_document["binding"][
                "genesis_registry_namespace"
            ],
            "admission_nonce_hash": claim_document["binding"][
                "admission_nonce_hash"
            ],
            "expected_genesis_registry_head_hash": claim_document["binding"][
                "expected_genesis_registry_head_hash"
            ],
            "candidate_public_key_spki_sha256": claim_document["binding"][
                "candidate_public_key_spki_sha256"
            ],
        },
        "facts": {
            "threshold_admission_evidence_exact": True,
            "replay_key_bindings_exact": True,
            "replay_key_reserved": False,
            "atomic_reservation_verified": False,
            "durable_reservation_verified": False,
            "linearizable_reservation_verified": False,
            "genesis_registry_created": False,
            "provider_registered": False,
            "runtime_mutations": False,
        },
        "authority": _authority(),
        "blockers": [
            "GENESIS_ADMISSION_REPLAY_UNRESERVED",
            "ATOMIC_REPLAY_RESERVATION_UNVERIFIED",
            "DURABLE_REPLAY_RESERVATION_UNVERIFIED",
            "LINEARIZABLE_REPLAY_RESERVATION_UNVERIFIED",
            "GENESIS_REGISTRY_NOT_CREATED",
            "PROVIDER_REGISTRATION_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(
        document, "genesis_admission_replay_key_hash"
    )


def verify_genesis_admission_replay_key_v1(
    document: Any,
    *args: Any,
    expected_genesis_admission_replay_key_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = build_genesis_admission_replay_key_v1(*args, **kwargs)
        return (
            document == expected
            and _require_hash(
                expected_genesis_admission_replay_key_hash,
                "expected_genesis_admission_replay_key_hash",
            )
            == expected["genesis_admission_replay_key_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderThresholdGenesisAdmissionError):
        return False


__all__ = [
    "GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION",
    "GENESIS_ADMISSION_REPLAY_KEY_SCHEMA_VERSION",
    "SIGNED_GENESIS_ADMISSION_SCHEMA_VERSION",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "ChallengeConsumptionProviderThresholdGenesisAdmissionError",
    "build_challenge_consumption_provider_genesis_admission_claim_v1",
    "build_genesis_admission_replay_key_v1",
    "build_threshold_signed_genesis_admission_v1",
    "evaluate_threshold_signed_genesis_admission_v1",
    "verify_challenge_consumption_provider_genesis_admission_claim_v1",
    "verify_genesis_admission_replay_key_v1",
    "verify_threshold_signed_genesis_admission_evidence_v1",
]
