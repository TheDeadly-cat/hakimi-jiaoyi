"""Threshold-signed clock-trust genesis admission with no execution authority."""

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
    genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1 as bootstrap,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-genesis-admission-claim-v1"
)
SIGNED_GENESIS_ADMISSION_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-signed-genesis-admission-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-genesis-admission-evidence-v1"
)
GENESIS_COMMITMENT_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-genesis-commitment-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-provider-clock-trust-threshold-"
    "genesis-admission-v1-synthetic-lock-1"
)
BOOTSTRAP_TOPOLOGY_IMPLEMENTATION_SHA256 = (
    "948ddd4c9889376fd7262cc51fb952aa9230944f51959ede081f10d7426f1bde"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_DOMAIN = bootstrap.GENESIS_SIGNATURE_DOMAIN
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_SIGNATURE_FIELDS = {"public_key_spki_base64", "signature_base64"}


class ClockTrustThresholdGenesisAdmissionError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} must be a strict identifier"
        )
    return value


def _decode_base64(
    value: Any, label: str, *, expected_length: int | None = None
) -> bytes:
    if type(value) is not str or not value:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        )
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        ) from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} must be canonical base64"
        )
    if expected_length is not None and len(decoded) != expected_length:
        raise ClockTrustThresholdGenesisAdmissionError(
            f"{label} length mismatch"
        )
    return decoded


def _load_ed25519_spki(value: Any) -> tuple[Ed25519PublicKey, bytes]:
    der = _decode_base64(value, "public_key_spki_base64")
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise ClockTrustThresholdGenesisAdmissionError(
            "public key must be canonical Ed25519 DER-SPKI"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise ClockTrustThresholdGenesisAdmissionError(
            "public key must be Ed25519"
        )
    canonical = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical != der:
        raise ClockTrustThresholdGenesisAdmissionError(
            "public key DER-SPKI is not canonical"
        )
    return key, der


def _authority() -> dict[str, bool]:
    return {
        "genesis_admission_allowed": False,
        "genesis_commitment_install_allowed": False,
        "clock_registration_governance_allowed": False,
        "verification_time_source_trust_allowed": False,
        "trusted_current_time_established": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "provider_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _exact_topology(
    topology_document: Any, topology_build_kwargs: Any
) -> dict[str, Any]:
    if type(topology_build_kwargs) is not dict:
        raise ClockTrustThresholdGenesisAdmissionError(
            "topology_build_kwargs must be a dict"
        )
    try:
        expected = bootstrap.build_clock_trust_bootstrap_topology_v1(
            **copy.deepcopy(topology_build_kwargs)
        )
    except (TypeError, ValueError) as exc:
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust topology kwargs are invalid"
        ) from exc
    if topology_document != expected:
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust bootstrap topology is not exact"
        )
    return expected


def _exact_plan(
    plan_document: Any,
    topology_document: Any,
    plan_build_kwargs: Any,
) -> dict[str, Any]:
    if type(plan_build_kwargs) is not dict:
        raise ClockTrustThresholdGenesisAdmissionError(
            "plan_build_kwargs must be a dict"
        )
    try:
        expected = bootstrap.build_clock_trust_genesis_admission_plan_v1(
            topology_document, **copy.deepcopy(plan_build_kwargs)
        )
    except (TypeError, ValueError) as exc:
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust genesis plan kwargs are invalid"
        ) from exc
    if (
        plan_document != expected
        or expected.get("status") != "BLOCKED"
        or expected.get("facts", {}).get("plan_only") is not True
        or expected.get("facts", {}).get("ceremony_executed") is not False
    ):
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust genesis admission plan is not exact and unexecuted"
        )
    return expected


def build_clock_trust_genesis_admission_claim_v1(
    topology_document: Any,
    plan_document: Any,
    *,
    expected_out_of_band_genesis_commitment_hash: Any,
    topology_build_kwargs: Any,
    plan_build_kwargs: Any,
) -> dict[str, Any]:
    topology = _exact_topology(topology_document, topology_build_kwargs)
    plan = _exact_plan(plan_document, topology_document, plan_build_kwargs)
    expected_commitment = _require_hash(
        expected_out_of_band_genesis_commitment_hash,
        "expected_out_of_band_genesis_commitment_hash",
    )
    forbidden = {
        topology["topology_hash"],
        plan["plan_hash"],
        plan["binding"]["ceremony_id_hash"],
        plan["binding"]["admission_nonce_hash"],
    }
    if expected_commitment in forbidden:
        raise ClockTrustThresholdGenesisAdmissionError(
            "out-of-band commitment must be distinct from topology and ceremony bindings"
        )
    root_set = topology["root_authority_set"]
    document = {
        "schema_version": GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "CLOCK_TRUST_GENESIS_ADMISSION_CLAIM_UNSIGNED_EXTERNAL_ROOT_"
            "IDENTITY_GOVERNANCE_AND_INSTALLATION_UNVERIFIED"
        ),
        "source": {
            "topology_hash": topology["topology_hash"],
            "plan_hash": plan["plan_hash"],
            "root_authority_set_hash": root_set[
                "root_authority_set_hash"
            ],
            "clock_registration_hash": topology["source"][
                "clock_registration_hash"
            ],
            "verification_time_source_preregistration_hash": topology["source"][
                "verification_time_source_preregistration_hash"
            ],
            "bootstrap_topology_implementation_sha256": (
                BOOTSTRAP_TOPOLOGY_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "binding": {
            "genesis_registry_namespace": (
                bootstrap.GENESIS_REGISTRY_NAMESPACE
            ),
            "governance_domain": topology["bootstrap"][
                "governance_domain"
            ],
            "genesis_policy_hash": topology["bootstrap"][
                "genesis_policy_hash"
            ],
            "ceremony_id_hash": plan["binding"]["ceremony_id_hash"],
            "admission_nonce_hash": plan["binding"][
                "admission_nonce_hash"
            ],
            "expected_out_of_band_genesis_commitment_hash": (
                expected_commitment
            ),
            "minimum_root_signatures": root_set["minimum_signatures"],
            "root_authority_count": len(root_set["authorities"]),
        },
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "bootstrap_topology_exact": True,
            "genesis_admission_plan_exact": True,
            "plan_confirmed_unexecuted": True,
            "claim_bindings_exact": True,
            "threshold_root_signatures_verified": False,
            "external_root_identity_verified": False,
            "external_root_governance_verified": False,
            "root_member_independence_verified": False,
            "out_of_band_genesis_commitment_verified": False,
            "genesis_commitment_installed": False,
            "clock_registration_governance_verified": False,
            "verification_time_source_trusted": False,
            "trusted_current_time_established": False,
            "challenge_freshness_verified": False,
            "registration_replay_consumed": False,
            "provider_registered": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "THRESHOLD_ROOT_SIGNATURES_UNVERIFIED",
            "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
            "EXTERNAL_ROOT_GOVERNANCE_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "OUT_OF_BAND_GENESIS_COMMITMENT_UNVERIFIED",
            "GENESIS_COMMITMENT_NOT_INSTALLED",
            "CLOCK_REGISTRATION_GOVERNANCE_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_TRUST_UNVERIFIED",
            "TRUSTED_CURRENT_TIME_UNESTABLISHED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(
        document, "genesis_admission_claim_hash"
    )


def verify_clock_trust_genesis_admission_claim_v1(
    document: Any,
    *args: Any,
    expected_genesis_admission_claim_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = build_clock_trust_genesis_admission_claim_v1(
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
    except (TypeError, ClockTrustThresholdGenesisAdmissionError):
        return False


def _exact_claim(
    claim_document: Any,
    topology_document: Any,
    plan_document: Any,
    expected_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    if type(claim_build_kwargs) is not dict:
        raise ClockTrustThresholdGenesisAdmissionError(
            "claim_build_kwargs must be a dict"
        )
    try:
        expected = build_clock_trust_genesis_admission_claim_v1(
            topology_document,
            plan_document,
            **copy.deepcopy(claim_build_kwargs),
        )
    except (TypeError, ValueError) as exc:
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust genesis claim kwargs are invalid"
        ) from exc
    claim_hash = _require_hash(expected_claim_hash, "expected_claim_hash")
    if (
        claim_document != expected
        or claim_hash != expected["genesis_admission_claim_hash"]
    ):
        raise ClockTrustThresholdGenesisAdmissionError(
            "clock-trust genesis admission claim is not exact"
        )
    return expected


def build_threshold_signed_clock_trust_genesis_admission_v1(
    claim_document: Any,
    topology_document: Any,
    plan_document: Any,
    *,
    signatures_by_authority_id: Any,
    expected_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    expected_claim = _exact_claim(
        claim_document,
        topology_document,
        plan_document,
        expected_claim_hash,
        claim_build_kwargs,
    )
    if type(signatures_by_authority_id) is not dict:
        raise ClockTrustThresholdGenesisAdmissionError(
            "signatures_by_authority_id must be a dict"
        )
    root_count = expected_claim["binding"]["root_authority_count"]
    if not 1 <= len(signatures_by_authority_id) <= root_count:
        raise ClockTrustThresholdGenesisAdmissionError(
            "signature count must be between one and root authority count"
        )
    records = []
    for authority_id, material in signatures_by_authority_id.items():
        identifier = _require_identifier(authority_id, "authority_id")
        if type(material) is not dict or set(material) != _SIGNATURE_FIELDS:
            raise ClockTrustThresholdGenesisAdmissionError(
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
                "public_key_spki_base64": material[
                    "public_key_spki_base64"
                ],
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
        "topology_hash": expected_claim["source"]["topology_hash"],
        "plan_hash": expected_claim["source"]["plan_hash"],
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
    return seal_strict_canonical_document(
        document, "signed_genesis_admission_hash"
    )


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def evaluate_threshold_signed_clock_trust_genesis_admission_v1(
    signed_admission_document: Any,
    claim_document: Any,
    topology_document: Any,
    plan_document: Any,
    *,
    signatures_by_authority_id: Any,
    expected_claim_hash: Any,
    expected_signed_admission_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_exact = False
    signed_exact = False
    all_supplied_signatures_valid = False
    configured_threshold_met = False
    valid_signer_ids: list[str] = []
    cryptographic_signature_count = 0
    registered_key_match_count = 0
    minimum_root_signatures = None
    root_authority_count = None
    claim_hash = _safe_hash(expected_claim_hash)
    signed_hash = _safe_hash(expected_signed_admission_hash)
    topology_hash = None
    plan_hash = None
    root_set_hash = None
    clock_registration_hash = None
    time_source_hash = None
    try:
        expected_claim = _exact_claim(
            claim_document,
            topology_document,
            plan_document,
            expected_claim_hash,
            claim_build_kwargs,
        )
        claim_exact = True
        expected_signed = (
            build_threshold_signed_clock_trust_genesis_admission_v1(
                claim_document,
                topology_document,
                plan_document,
                signatures_by_authority_id=signatures_by_authority_id,
                expected_claim_hash=expected_claim[
                    "genesis_admission_claim_hash"
                ],
                claim_build_kwargs=claim_build_kwargs,
            )
        )
        signed_exact = (
            signed_admission_document == expected_signed
            and _require_hash(
                expected_signed_admission_hash,
                "expected_signed_admission_hash",
            )
            == expected_signed["signed_genesis_admission_hash"]
        )
        root_set = topology_document["root_authority_set"]
        root_by_id = {
            item["authority_id"]: item for item in root_set["authorities"]
        }
        minimum_root_signatures = root_set["minimum_signatures"]
        root_authority_count = len(root_set["authorities"])
        topology_hash = topology_document["topology_hash"]
        plan_hash = plan_document["plan_hash"]
        root_set_hash = root_set["root_authority_set_hash"]
        clock_registration_hash = topology_document["source"][
            "clock_registration_hash"
        ]
        time_source_hash = topology_document["source"][
            "verification_time_source_preregistration_hash"
        ]
        supplied_valid = []
        for record in expected_signed["signatures"]:
            key, der = _load_ed25519_spki(
                record["public_key_spki_base64"]
            )
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
        configured_threshold_met = (
            all_supplied_signatures_valid
            and len(valid_signer_ids) >= minimum_root_signatures
        )
    except (KeyError, TypeError, ValueError):
        pass

    local_threshold_verified = (
        claim_exact
        and signed_exact
        and all_supplied_signatures_valid
        and configured_threshold_met
    )
    facts = {
        "genesis_admission_claim_exact": claim_exact,
        "signed_admission_document_exact": signed_exact,
        "all_supplied_signatures_cryptographically_and_structurally_valid": (
            all_supplied_signatures_valid
        ),
        "configured_threshold_met": configured_threshold_met,
        "threshold_root_signatures_verified": local_threshold_verified,
        "external_root_identity_verified": False,
        "external_root_governance_verified": False,
        "root_member_independence_verified": False,
        "out_of_band_genesis_commitment_verified": False,
        "genesis_commitment_installed": False,
        "clock_registration_governance_verified": False,
        "verification_time_source_trusted": False,
        "trusted_current_time_established": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "provider_registered": False,
        "raw_public_keys_redacted": True,
        "raw_signatures_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }
    blockers = [
        "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
        "EXTERNAL_ROOT_GOVERNANCE_UNVERIFIED",
        "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
        "OUT_OF_BAND_GENESIS_COMMITMENT_UNVERIFIED",
        "GENESIS_COMMITMENT_NOT_INSTALLED",
        "CLOCK_REGISTRATION_GOVERNANCE_UNVERIFIED",
        "VERIFICATION_TIME_SOURCE_TRUST_UNVERIFIED",
        "TRUSTED_CURRENT_TIME_UNESTABLISHED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not local_threshold_verified:
        blockers.insert(
            0, "CLOCK_TRUST_THRESHOLD_GENESIS_ADMISSION_UNKNOWN_OR_INVALID"
        )
    evidence = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_threshold_verified else "BLOCK",
        "decision": (
            "CONFIGURED_ROOT_THRESHOLD_SIGNATURES_OBSERVED_EXTERNAL_IDENTITY_"
            "GOVERNANCE_COMMITMENT_INSTALLATION_AND_TIME_TRUST_UNVERIFIED"
            if local_threshold_verified
            else "CLOCK_TRUST_THRESHOLD_GENESIS_ADMISSION_UNKNOWN_OR_INVALID"
        ),
        "admission_status": "BLOCKED",
        "source": {
            "topology_hash": _safe_hash(topology_hash),
            "plan_hash": _safe_hash(plan_hash),
            "root_authority_set_hash": _safe_hash(root_set_hash),
            "clock_registration_hash": _safe_hash(
                clock_registration_hash
            ),
            "verification_time_source_preregistration_hash": _safe_hash(
                time_source_hash
            ),
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
    return seal_strict_canonical_document(
        evidence, "verification_evidence_hash"
    )


def verify_threshold_signed_clock_trust_genesis_admission_evidence_v1(
    evidence_document: Any,
    *args: Any,
    expected_verification_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = (
            evaluate_threshold_signed_clock_trust_genesis_admission_v1(
                *args, **kwargs
            )
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_verification_evidence_hash,
                "expected_verification_evidence_hash",
            )
            == expected["verification_evidence_hash"]
        )
    except (TypeError, ClockTrustThresholdGenesisAdmissionError):
        return False


def build_clock_trust_genesis_commitment_v1(
    evidence_document: Any,
    signed_admission_document: Any,
    claim_document: Any,
    topology_document: Any,
    plan_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    evaluation_kwargs: Any,
) -> dict[str, Any]:
    if type(evaluation_kwargs) is not dict:
        raise ClockTrustThresholdGenesisAdmissionError(
            "evaluation_kwargs must be a dict"
        )
    expected = (
        evaluate_threshold_signed_clock_trust_genesis_admission_v1(
            signed_admission_document,
            claim_document,
            topology_document,
            plan_document,
            **copy.deepcopy(evaluation_kwargs),
        )
    )
    evidence_hash = _require_hash(
        expected_verification_evidence_hash,
        "expected_verification_evidence_hash",
    )
    if (
        evidence_document != expected
        or evidence_hash != expected["verification_evidence_hash"]
        or expected["status"] != "PASS"
    ):
        raise ClockTrustThresholdGenesisAdmissionError(
            "threshold genesis admission evidence is not an exact local PASS"
        )
    document = {
        "schema_version": GENESIS_COMMITMENT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "CLOCK_TRUST_GENESIS_COMMITMENT_DERIVED_EXACTLY_EXTERNAL_MATCH_"
            "INSTALLATION_ROLLBACK_PROTECTION_AND_TIME_TRUST_UNVERIFIED"
        ),
        "source": {
            "topology_hash": topology_document["topology_hash"],
            "plan_hash": plan_document["plan_hash"],
            "root_authority_set_hash": topology_document[
                "root_authority_set"
            ]["root_authority_set_hash"],
            "clock_registration_hash": claim_document["source"][
                "clock_registration_hash"
            ],
            "verification_time_source_preregistration_hash": claim_document[
                "source"
            ]["verification_time_source_preregistration_hash"],
            "genesis_admission_claim_hash": claim_document[
                "genesis_admission_claim_hash"
            ],
            "signed_genesis_admission_hash": signed_admission_document[
                "signed_genesis_admission_hash"
            ],
            "verification_evidence_hash": evidence_hash,
        },
        "binding": {
            "genesis_registry_namespace": claim_document["binding"][
                "genesis_registry_namespace"
            ],
            "governance_domain": claim_document["binding"][
                "governance_domain"
            ],
            "genesis_policy_hash": claim_document["binding"][
                "genesis_policy_hash"
            ],
            "ceremony_id_hash": claim_document["binding"][
                "ceremony_id_hash"
            ],
            "admission_nonce_hash": claim_document["binding"][
                "admission_nonce_hash"
            ],
            "expected_out_of_band_genesis_commitment_hash": claim_document[
                "binding"
            ]["expected_out_of_band_genesis_commitment_hash"],
        },
        "facts": {
            "threshold_admission_evidence_exact": True,
            "genesis_commitment_bindings_exact": True,
            "out_of_band_genesis_commitment_verified": False,
            "genesis_commitment_installed": False,
            "installation_rollback_protection_verified": False,
            "clock_registration_governance_verified": False,
            "verification_time_source_trusted": False,
            "trusted_current_time_established": False,
            "runtime_mutations": False,
        },
        "authority": _authority(),
        "blockers": [
            "OUT_OF_BAND_GENESIS_COMMITMENT_UNVERIFIED",
            "GENESIS_COMMITMENT_NOT_INSTALLED",
            "INSTALLATION_ROLLBACK_PROTECTION_UNVERIFIED",
            "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "CLOCK_REGISTRATION_GOVERNANCE_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_TRUST_UNVERIFIED",
            "TRUSTED_CURRENT_TIME_UNESTABLISHED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(
        document, "genesis_commitment_hash"
    )


def verify_clock_trust_genesis_commitment_v1(
    document: Any,
    *args: Any,
    expected_genesis_commitment_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = build_clock_trust_genesis_commitment_v1(
            *args, **kwargs
        )
        return (
            document == expected
            and _require_hash(
                expected_genesis_commitment_hash,
                "expected_genesis_commitment_hash",
            )
            == expected["genesis_commitment_hash"]
        )
    except (TypeError, ClockTrustThresholdGenesisAdmissionError):
        return False


__all__ = [
    "GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION",
    "GENESIS_COMMITMENT_SCHEMA_VERSION",
    "SIGNED_GENESIS_ADMISSION_SCHEMA_VERSION",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "ClockTrustThresholdGenesisAdmissionError",
    "build_clock_trust_genesis_admission_claim_v1",
    "build_clock_trust_genesis_commitment_v1",
    "build_threshold_signed_clock_trust_genesis_admission_v1",
    "evaluate_threshold_signed_clock_trust_genesis_admission_v1",
    "verify_clock_trust_genesis_admission_claim_v1",
    "verify_clock_trust_genesis_commitment_v1",
    "verify_threshold_signed_clock_trust_genesis_admission_evidence_v1",
]
