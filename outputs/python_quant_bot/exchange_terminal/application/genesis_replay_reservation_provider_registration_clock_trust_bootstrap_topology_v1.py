"""Non-circular offline threshold topology for clock-trust genesis admission."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.services import trusted_clock_authority_v3 as clock_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


VERIFICATION_TIME_SOURCE_PREREGISTRATION_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-verification-time-source-preregistration-v1"
)
ROOT_AUTHORITY_SET_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-root-authority-set-v1"
)
TOPOLOGY_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-bootstrap-topology-v1"
)
GENESIS_ADMISSION_PLAN_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-clock-trust-genesis-admission-plan-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-provider-clock-trust-bootstrap-"
    "topology-v1-synthetic-lock-1"
)
BOOTSTRAP_MODE = "OFFLINE_THRESHOLD_CLOCK_TRUST_GENESIS_V1"
GENESIS_REGISTRY_NAMESPACE = (
    "hakimi.strategy-correlation.clock-trust.genesis.v1"
)
CLOCK_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "9a12682fb00dee3d6851ac62d4a37de0c66992e3f57d8e9715e23712d25a8c62"
)
TARGET_CLOCK_BINDING_IMPLEMENTATION_SHA256 = (
    "60f01be568b0ef978819c75dbb39146c5b0b06cd2e351f2de2fac9ab3c54b94b"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
GENESIS_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.clock-trust.genesis-admission.v1"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")


class ClockTrustBootstrapTopologyError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ClockTrustBootstrapTopologyError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ClockTrustBootstrapTopologyError(
            f"{label} must be a strict identifier"
        )
    return value


def _require_threshold(value: Any, authority_count: int) -> int:
    if type(value) is not int or value < 2 or value > authority_count:
        raise ClockTrustBootstrapTopologyError(
            "minimum_root_signatures must be an integer between two and root count"
        )
    return value


def _copy_kwargs(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ClockTrustBootstrapTopologyError(f"{label} must be a dict")
    return copy.deepcopy(value)


def _authority() -> dict[str, bool]:
    return {
        "clock_registration_governance_allowed": False,
        "verification_time_source_trust_allowed": False,
        "genesis_admission_execution_allowed": False,
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


def build_verification_time_source_preregistration_v1(
    *,
    source_id: Any,
    key_id: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    implementation_claim_sha256: Any,
    monotonic_epoch_namespace: Any,
) -> dict[str, Any]:
    identity = {
        "source_id": _require_identifier(source_id, "source_id"),
        "key_id": _require_identifier(key_id, "key_id"),
        "public_key_spki_sha256": _require_hash(
            public_key_spki_sha256, "public_key_spki_sha256"
        ),
        "trust_domain": _require_identifier(trust_domain, "trust_domain"),
        "implementation_claim_sha256": _require_hash(
            implementation_claim_sha256, "implementation_claim_sha256"
        ),
        "monotonic_epoch_namespace": _require_identifier(
            monotonic_epoch_namespace, "monotonic_epoch_namespace"
        ),
    }
    document = {
        "schema_version": VERIFICATION_TIME_SOURCE_PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "VERIFICATION_TIME_SOURCE_PREREGISTERED_IDENTITY_KEY_CONTROL_"
            "MONOTONICITY_AND_TRUST_UNVERIFIED"
        ),
        "identity": identity,
        "facts": {
            "local_preregistration_complete": True,
            "identity_fields_preregistered": True,
            "public_key_hash_preregistered": True,
            "implementation_claim_preregistered": True,
            "monotonic_epoch_namespace_preregistered": True,
            "source_identity_verified": False,
            "source_key_possession_verified": False,
            "source_implementation_verified": False,
            "monotonicity_verified": False,
            "rollback_resistance_verified": False,
            "verification_time_source_trusted": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "VERIFICATION_TIME_SOURCE_IDENTITY_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_KEY_POSSESSION_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_IMPLEMENTATION_UNVERIFIED",
            "MONOTONICITY_UNVERIFIED",
            "ROLLBACK_RESISTANCE_UNVERIFIED",
            "CLOCK_TRUST_GENESIS_ADMISSION_MISSING",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_verification_time_source_preregistration_v1(
    document: Any, **kwargs: Any
) -> bool:
    try:
        return document == build_verification_time_source_preregistration_v1(
            **kwargs
        )
    except (TypeError, ClockTrustBootstrapTopologyError):
        return False


def _exact_time_source_preregistration(
    document: Any, kwargs: Any
) -> dict[str, Any]:
    clean = _copy_kwargs(
        kwargs, "verification_time_source_preregistration_kwargs"
    )
    try:
        expected = build_verification_time_source_preregistration_v1(**clean)
    except (TypeError, ClockTrustBootstrapTopologyError) as exc:
        raise ClockTrustBootstrapTopologyError(
            "verification time source preregistration kwargs are invalid"
        ) from exc
    if document != expected:
        raise ClockTrustBootstrapTopologyError(
            "verification time source preregistration is not exact"
        )
    return expected


def _exact_clock_registration(
    document: Any,
    public_keys_by_id: Any,
    expected_registration_hash: Any,
) -> tuple[dict[str, Any], set[str]]:
    if type(document) is not dict or type(public_keys_by_id) is not dict:
        raise ClockTrustBootstrapTopologyError(
            "clock registration and public keys must be dicts"
        )
    expected_hash = _require_hash(
        expected_registration_hash, "expected_clock_registration_hash"
    )
    try:
        verified = clock_contract.verify_trusted_clock_authority_registration_v3(
            document,
            copy.deepcopy(public_keys_by_id),
            expected_registration_hash=expected_hash,
        )
    except (
        TypeError,
        ValueError,
        clock_contract.TrustedClockAuthorityContractError,
    ) as exc:
        raise ClockTrustBootstrapTopologyError(
            "clock registration verification failed"
        ) from exc
    if not verified or document.get("registration_hash") != expected_hash:
        raise ClockTrustBootstrapTopologyError(
            "clock registration is not exact"
        )
    key_hashes = {
        _require_hash(entry.get("public_key_sha256"), "clock public key hash")
        for entry in document.get("authorities", [])
        if type(entry) is dict
    }
    if len(key_hashes) != len(document.get("authorities", [])):
        raise ClockTrustBootstrapTopologyError(
            "clock authority key hashes are not unique"
        )
    return copy.deepcopy(document), key_hashes


def _normalize_root_authorities(
    value: Any, forbidden_key_hashes: set[str]
) -> list[dict[str, str]]:
    if type(value) not in (list, tuple) or len(value) < 3:
        raise ClockTrustBootstrapTopologyError(
            "root_authorities must contain at least three entries"
        )
    expected_keys = {
        "authority_id",
        "key_id",
        "organization_claim",
        "public_key_spki_sha256",
    }
    normalized: list[dict[str, str]] = []
    authority_ids: set[str] = set()
    key_ids: set[str] = set()
    organization_claims: set[str] = set()
    key_hashes: set[str] = set()
    for entry in value:
        if type(entry) is not dict or set(entry) != expected_keys:
            raise ClockTrustBootstrapTopologyError(
                "root authority entry schema is not exact"
            )
        clean = {
            "authority_id": _require_identifier(
                entry["authority_id"], "root authority_id"
            ),
            "key_id": _require_identifier(entry["key_id"], "root key_id"),
            "organization_claim": _require_identifier(
                entry["organization_claim"], "root organization_claim"
            ),
            "public_key_spki_sha256": _require_hash(
                entry["public_key_spki_sha256"], "root public key hash"
            ),
        }
        if clean["authority_id"] in authority_ids:
            raise ClockTrustBootstrapTopologyError(
                "root authority ids must be unique"
            )
        if clean["key_id"] in key_ids:
            raise ClockTrustBootstrapTopologyError(
                "root key ids must be unique"
            )
        if clean["organization_claim"] in organization_claims:
            raise ClockTrustBootstrapTopologyError(
                "root organization claims must be syntactically distinct"
            )
        if clean["public_key_spki_sha256"] in key_hashes:
            raise ClockTrustBootstrapTopologyError(
                "root public key hashes must be unique"
            )
        if clean["public_key_spki_sha256"] in forbidden_key_hashes:
            raise ClockTrustBootstrapTopologyError(
                "root keys must be separate from operational clock and time-source keys"
            )
        authority_ids.add(clean["authority_id"])
        key_ids.add(clean["key_id"])
        organization_claims.add(clean["organization_claim"])
        key_hashes.add(clean["public_key_spki_sha256"])
        normalized.append(clean)
    normalized.sort(key=lambda item: item["authority_id"])
    return normalized


def build_clock_trust_bootstrap_topology_v1(
    *,
    clock_registration_document: Any,
    clock_public_keys_by_id: Any,
    expected_clock_registration_hash: Any,
    verification_time_source_preregistration_document: Any,
    verification_time_source_preregistration_kwargs: Any,
    root_authorities: Any,
    minimum_root_signatures: Any,
    governance_domain: Any,
    genesis_policy_hash: Any,
) -> dict[str, Any]:
    clock_registration, clock_key_hashes = _exact_clock_registration(
        clock_registration_document,
        clock_public_keys_by_id,
        expected_clock_registration_hash,
    )
    time_source = _exact_time_source_preregistration(
        verification_time_source_preregistration_document,
        verification_time_source_preregistration_kwargs,
    )
    forbidden = set(clock_key_hashes)
    forbidden.add(time_source["identity"]["public_key_spki_sha256"])
    roots = _normalize_root_authorities(root_authorities, forbidden)
    threshold = _require_threshold(minimum_root_signatures, len(roots))
    domain = _require_identifier(governance_domain, "governance_domain")
    policy_hash = _require_hash(genesis_policy_hash, "genesis_policy_hash")
    root_set = seal_strict_canonical_document(
        {
            "schema_version": ROOT_AUTHORITY_SET_SCHEMA_VERSION,
            "governance_domain": domain,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "signature_domain": GENESIS_SIGNATURE_DOMAIN,
            "minimum_signatures": threshold,
            "authorities": roots,
        },
        "root_authority_set_hash",
    )
    topology = {
        "schema_version": TOPOLOGY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "NON_CIRCULAR_CLOCK_TRUST_GENESIS_TOPOLOGY_DECLARED_"
            "ROOT_SIGNATURES_IDENTITIES_AND_EXECUTION_UNVERIFIED"
        ),
        "bootstrap": {
            "mode": BOOTSTRAP_MODE,
            "registry_namespace": GENESIS_REGISTRY_NAMESPACE,
            "governance_domain": domain,
            "genesis_policy_hash": policy_hash,
        },
        "source": {
            "clock_registration_hash": clock_registration["registration_hash"],
            "clock_registration_schema_version": (
                clock_contract.REGISTRATION_SCHEMA_VERSION
            ),
            "clock_registration_implementation_sha256": (
                CLOCK_REGISTRATION_IMPLEMENTATION_SHA256
            ),
            "verification_time_source_preregistration_hash": (
                time_source["preregistration_hash"]
            ),
            "verification_time_source_preregistration_schema_version": (
                VERIFICATION_TIME_SOURCE_PREREGISTRATION_SCHEMA_VERSION
            ),
            "target_clock_binding_implementation_sha256": (
                TARGET_CLOCK_BINDING_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "root_authority_set": root_set,
        "dependency_graph": {
            "nodes": [
                "OFFLINE_ROOT_AUTHORITY_SET",
                "CLOCK_REGISTRATION_COMMITMENT",
                "VERIFICATION_TIME_SOURCE_COMMITMENT",
                "CLOCK_TRUST_GENESIS_ADMISSION",
                "RUNTIME_CLOCK_BINDING_CONSUMER",
            ],
            "edges": [
                {
                    "source": "OFFLINE_ROOT_AUTHORITY_SET",
                    "target": "CLOCK_TRUST_GENESIS_ADMISSION",
                },
                {
                    "source": "CLOCK_REGISTRATION_COMMITMENT",
                    "target": "CLOCK_TRUST_GENESIS_ADMISSION",
                },
                {
                    "source": "VERIFICATION_TIME_SOURCE_COMMITMENT",
                    "target": "CLOCK_TRUST_GENESIS_ADMISSION",
                },
                {
                    "source": "CLOCK_TRUST_GENESIS_ADMISSION",
                    "target": "RUNTIME_CLOCK_BINDING_CONSUMER",
                },
            ],
            "forbidden_edges": [
                {
                    "source": "RUNTIME_CLOCK_BINDING_CONSUMER",
                    "target": "OFFLINE_ROOT_AUTHORITY_SET",
                },
                {
                    "source": "RUNTIME_CLOCK_BINDING_CONSUMER",
                    "target": "CLOCK_TRUST_GENESIS_ADMISSION",
                },
            ],
        },
        "facts": {
            "clock_registration_exact": True,
            "clock_registered_public_key_hashes_exact": True,
            "verification_time_source_preregistration_exact": True,
            "root_authority_set_preregistered": True,
            "root_key_separation_enforced": True,
            "root_organization_claims_syntactically_distinct": True,
            "bootstrap_dependency_cycle_absent": True,
            "offline_threshold_genesis_required": True,
            "root_signatures_verified": False,
            "root_identities_verified": False,
            "root_member_independence_verified": False,
            "clock_registration_governance_verified": False,
            "verification_time_source_identity_verified": False,
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
            "OFFLINE_ROOT_SIGNATURES_MISSING",
            "EXTERNAL_ROOT_IDENTITIES_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "CLOCK_REGISTRATION_GOVERNANCE_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_IDENTITY_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_KEY_POSSESSION_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_MONOTONICITY_UNVERIFIED",
            "TRUSTED_CURRENT_TIME_UNESTABLISHED",
            "CHALLENGE_FRESHNESS_UNVERIFIED",
            "REGISTRATION_REPLAY_UNCONSUMED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(topology, "topology_hash")


def verify_clock_trust_bootstrap_topology_v1(
    document: Any,
    *,
    expected_topology_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_clock_trust_bootstrap_topology_v1(**build_kwargs)
        return (
            document == expected
            and _require_hash(expected_topology_hash, "expected_topology_hash")
            == expected["topology_hash"]
        )
    except (TypeError, ClockTrustBootstrapTopologyError):
        return False


def _exact_topology(document: Any, kwargs: Any) -> dict[str, Any]:
    clean = _copy_kwargs(kwargs, "topology_build_kwargs")
    try:
        expected = build_clock_trust_bootstrap_topology_v1(**clean)
    except (TypeError, ClockTrustBootstrapTopologyError) as exc:
        raise ClockTrustBootstrapTopologyError(
            "topology build kwargs are invalid"
        ) from exc
    if document != expected:
        raise ClockTrustBootstrapTopologyError(
            "clock trust bootstrap topology is not exact"
        )
    return expected


def build_clock_trust_genesis_admission_plan_v1(
    topology_document: Any,
    *,
    expected_topology_hash: Any,
    topology_build_kwargs: Any,
    ceremony_id_hash: Any,
    admission_nonce_hash: Any,
) -> dict[str, Any]:
    topology = _exact_topology(topology_document, topology_build_kwargs)
    topology_hash = _require_hash(
        expected_topology_hash, "expected_topology_hash"
    )
    if topology_hash != topology["topology_hash"]:
        raise ClockTrustBootstrapTopologyError(
            "expected topology hash mismatch"
        )
    ceremony = _require_hash(ceremony_id_hash, "ceremony_id_hash")
    nonce = _require_hash(admission_nonce_hash, "admission_nonce_hash")
    if ceremony == nonce:
        raise ClockTrustBootstrapTopologyError(
            "ceremony id and admission nonce hashes must be distinct"
        )
    plan = {
        "schema_version": GENESIS_ADMISSION_PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "OFFLINE_THRESHOLD_CLOCK_TRUST_GENESIS_ADMISSION_"
            "PLANNED_NOT_EXECUTED"
        ),
        "source": {
            "topology_hash": topology_hash,
            "root_authority_set_hash": topology["root_authority_set"][
                "root_authority_set_hash"
            ],
            "clock_registration_hash": topology["source"][
                "clock_registration_hash"
            ],
            "verification_time_source_preregistration_hash": topology["source"][
                "verification_time_source_preregistration_hash"
            ],
        },
        "binding": {
            "ceremony_id_hash": ceremony,
            "admission_nonce_hash": nonce,
            "genesis_registry_namespace": GENESIS_REGISTRY_NAMESPACE,
            "genesis_policy_hash": topology["bootstrap"][
                "genesis_policy_hash"
            ],
            "signature_domain": GENESIS_SIGNATURE_DOMAIN,
            "minimum_root_signatures": topology["root_authority_set"][
                "minimum_signatures"
            ],
        },
        "required_checks": [
            "EXACT_TOPOLOGY_HASH",
            "EXACT_ROOT_AUTHORITY_SET_HASH",
            "EXACT_CLOCK_REGISTRATION_HASH",
            "EXACT_VERIFICATION_TIME_SOURCE_PREREGISTRATION_HASH",
            "DISTINCT_CEREMONY_AND_ADMISSION_NONCE_HASHES",
            "DETACHED_ED25519_SIGNATURE_PER_ROOT",
            "THRESHOLD_OF_DISTINCT_PREREGISTERED_ROOT_KEYS",
            "NO_OPERATIONAL_KEY_AS_ROOT_KEY",
            "NO_CURRENT_TIME_DEPENDENCY_AT_GENESIS",
            "NO_REPLAY_REGISTRY_DEPENDENCY_AT_GENESIS",
            "OUT_OF_BAND_GENESIS_COMMITMENT_MATCH",
            "MANUAL_CEREMONY_EXECUTION_ONLY",
        ],
        "facts": {
            "topology_exact": True,
            "plan_only": True,
            "ceremony_executed": False,
            "root_signatures_collected": False,
            "threshold_verified": False,
            "out_of_band_genesis_commitment_verified": False,
            "clock_registration_governance_verified": False,
            "verification_time_source_trusted": False,
            "trusted_current_time_established": False,
            "runtime_mutations": False,
        },
        "authority": _authority(),
        "blockers": [
            "GENESIS_CEREMONY_NOT_EXECUTED",
            "OFFLINE_ROOT_SIGNATURES_MISSING",
            "OUT_OF_BAND_GENESIS_COMMITMENT_UNVERIFIED",
            "EXTERNAL_ROOT_IDENTITIES_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "CLOCK_REGISTRATION_GOVERNANCE_UNVERIFIED",
            "VERIFICATION_TIME_SOURCE_TRUST_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(plan, "plan_hash")


def verify_clock_trust_genesis_admission_plan_v1(
    document: Any,
    topology_document: Any,
    *,
    expected_plan_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_clock_trust_genesis_admission_plan_v1(
            topology_document, **build_kwargs
        )
        return (
            document == expected
            and _require_hash(expected_plan_hash, "expected_plan_hash")
            == expected["plan_hash"]
        )
    except (TypeError, ClockTrustBootstrapTopologyError):
        return False


__all__ = [
    "BOOTSTRAP_MODE",
    "GENESIS_ADMISSION_PLAN_SCHEMA_VERSION",
    "ROOT_AUTHORITY_SET_SCHEMA_VERSION",
    "TOPOLOGY_SCHEMA_VERSION",
    "VERIFICATION_TIME_SOURCE_PREREGISTRATION_SCHEMA_VERSION",
    "ClockTrustBootstrapTopologyError",
    "build_clock_trust_bootstrap_topology_v1",
    "build_clock_trust_genesis_admission_plan_v1",
    "build_verification_time_source_preregistration_v1",
    "verify_clock_trust_bootstrap_topology_v1",
    "verify_clock_trust_genesis_admission_plan_v1",
    "verify_verification_time_source_preregistration_v1",
]
