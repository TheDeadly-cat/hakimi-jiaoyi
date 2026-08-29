"""Freeze a non-circular bootstrap topology for provider genesis admission."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1 as provider_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


TOPOLOGY_SCHEMA_VERSION = (
    "challenge-consumption-provider-bootstrap-topology-v1"
)
ROOT_AUTHORITY_SET_SCHEMA_VERSION = (
    "challenge-consumption-provider-bootstrap-root-authority-set-v1"
)
GENESIS_ADMISSION_PLAN_SCHEMA_VERSION = (
    "challenge-consumption-provider-bootstrap-genesis-admission-plan-v1"
)
STATIC_FINGERPRINT = (
    "20260824-challenge-consumption-provider-bootstrap-topology-v1-lock-1"
)
BOOTSTRAP_MODE = "OFFLINE_THRESHOLD_GENESIS_ADMISSION_V1"
GENESIS_REGISTRY_NAMESPACE = (
    "strategy-correlation-challenge-consumption-provider-genesis-admission-v1"
)
TARGET_GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION = (
    "challenge-consumption-provider-threshold-genesis-admission-claim-v1"
)
TARGET_THRESHOLD_RECEIPT_SCHEMA_VERSION = (
    "challenge-consumption-provider-threshold-genesis-admission-receipt-v1"
)
PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "867dd73a4cbb8219654265f21f3fff70d3031f18f23057fb3b69ebd6afc71bbb"
)
CLOCK_BINDING_IMPLEMENTATION_SHA256 = (
    "f57ee0863658e80a751d29884c77672441d82149109e488975e756314b3361b9"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_ROOT_FIELDS = {
    "authority_id",
    "public_key_spki_sha256",
    "trust_domain",
    "governance_implementation_claim_sha256",
}
_PLAN_CASES = (
    "external_root_identity_and_governance",
    "root_threshold_key_possession",
    "exact_genesis_admission_claim",
    "candidate_key_exclusion_recheck",
    "candidate_operator_independence_recheck",
    "candidate_trust_domain_independence_recheck",
    "threshold_signature_uniqueness",
    "signed_claim_replay_registry",
    "candidate_provider_conformance_all_13_cases",
    "atomic_genesis_registry_create",
    "durable_restart_and_rollback_resistance",
    "independent_admission_observer",
)


class ChallengeConsumptionProviderBootstrapTopologyError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            f"{label} must be a strict identifier"
        )
    return value


def _require_threshold(value: Any, authority_count: int) -> int:
    if type(value) is not int:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "minimum_root_signatures must be an integer"
        )
    if value < 2 or value > authority_count:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "minimum_root_signatures is outside authority count"
        )
    if value * 2 <= authority_count:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "minimum_root_signatures must be a strict majority"
        )
    return value


def _authority() -> dict[str, bool]:
    return {
        "genesis_admission_allowed": False,
        "challenge_consumption_allowed": False,
        "provider_registration_allowed": False,
        "external_conformance_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _exact_provider_preregistration(
    document: Any, kwargs: Any
) -> dict[str, Any]:
    if type(kwargs) is not dict:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "provider_preregistration_kwargs must be a dict"
        )
    try:
        expected = (
            provider_preregistration.build_challenge_consumption_provider_preregistration_v1(
                **copy.deepcopy(kwargs)
            )
        )
    except (TypeError, ValueError) as exc:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "provider preregistration kwargs are invalid"
        ) from exc
    if document != expected:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "provider preregistration is not exact"
        )
    return expected


def _build_root_authority_set(
    *,
    root_authorities: Any,
    minimum_root_signatures: Any,
    candidate_identity: dict[str, Any],
) -> dict[str, Any]:
    if type(root_authorities) is not list:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "root_authorities must be a list"
        )
    if not 2 <= len(root_authorities) <= 7:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "root authority count must be between 2 and 7"
        )
    normalized = []
    for index, authority in enumerate(root_authorities):
        if type(authority) is not dict or set(authority) != _ROOT_FIELDS:
            raise ChallengeConsumptionProviderBootstrapTopologyError(
                f"root_authorities[{index}] fields are not exact"
            )
        normalized.append(
            {
                "authority_id": _require_identifier(
                    authority["authority_id"],
                    f"root_authorities[{index}].authority_id",
                ),
                "public_key_spki_sha256": _require_hash(
                    authority["public_key_spki_sha256"],
                    f"root_authorities[{index}].public_key_spki_sha256",
                ),
                "trust_domain": _require_identifier(
                    authority["trust_domain"],
                    f"root_authorities[{index}].trust_domain",
                ),
                "governance_implementation_claim_sha256": _require_hash(
                    authority["governance_implementation_claim_sha256"],
                    (
                        f"root_authorities[{index}]."
                        "governance_implementation_claim_sha256"
                    ),
                ),
            }
        )
    ids = [item["authority_id"] for item in normalized]
    keys = [item["public_key_spki_sha256"] for item in normalized]
    domains = [item["trust_domain"] for item in normalized]
    if len(set(ids)) != len(ids):
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "root authority ids must be unique"
        )
    if len(set(keys)) != len(keys):
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "root authority keys must be unique"
        )
    if len(set(domains)) != len(domains):
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "root authority trust domains must be unique"
        )
    if candidate_identity["public_key_spki_sha256"] in keys:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "candidate provider key cannot be a bootstrap root key"
        )
    if candidate_identity["operator_identity_claim"] in ids:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "candidate operator cannot be a bootstrap root authority"
        )
    if candidate_identity["trust_domain"] in domains:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "candidate trust domain cannot be a bootstrap root trust domain"
        )
    threshold = _require_threshold(minimum_root_signatures, len(normalized))
    normalized.sort(key=lambda item: item["authority_id"])
    document = {
        "schema_version": ROOT_AUTHORITY_SET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "bootstrap_mode": BOOTSTRAP_MODE,
        "minimum_root_signatures": threshold,
        "authority_count": len(normalized),
        "authorities": normalized,
        "separation": {
            "candidate_public_key_excluded": True,
            "candidate_operator_excluded": True,
            "candidate_trust_domain_excluded": True,
            "root_authority_ids_unique": True,
            "root_public_keys_unique": True,
            "root_trust_domains_unique": True,
            "strict_majority_threshold": True,
        },
        "facts": {
            "root_identity_verified": False,
            "root_key_possession_verified": False,
            "root_governance_verified": False,
            "root_independence_verified": False,
        },
    }
    return seal_strict_canonical_document(document, "root_authority_set_hash")


def build_challenge_consumption_provider_bootstrap_topology_v1(
    provider_preregistration_document: Any,
    *,
    root_authorities: Any,
    minimum_root_signatures: Any,
    provider_preregistration_kwargs: Any,
) -> dict[str, Any]:
    provider = _exact_provider_preregistration(
        provider_preregistration_document,
        provider_preregistration_kwargs,
    )
    candidate = provider["identity"]
    root_set = _build_root_authority_set(
        root_authorities=copy.deepcopy(root_authorities),
        minimum_root_signatures=minimum_root_signatures,
        candidate_identity=candidate,
    )
    document = {
        "schema_version": TOPOLOGY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "NON_CIRCULAR_BOOTSTRAP_TOPOLOGY_FROZEN_EXTERNAL_ROOT_"
            "GOVERNANCE_AND_GENESIS_EXECUTION_UNVERIFIED"
        ),
        "source": {
            "provider_preregistration_hash": provider["preregistration_hash"],
            "provider_preregistration_implementation_sha256": (
                PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "clock_binding_implementation_sha256": (
                CLOCK_BINDING_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "candidate_binding": {
            "registry_id": candidate["registry_id"],
            "operator_identity_claim": candidate["operator_identity_claim"],
            "public_key_spki_sha256": candidate["public_key_spki_sha256"],
            "trust_domain": candidate["trust_domain"],
            "provider_implementation_claim_sha256": candidate[
                "provider_implementation_claim_sha256"
            ],
        },
        "bootstrap_root": {
            "mode": BOOTSTRAP_MODE,
            "genesis_registry_namespace": GENESIS_REGISTRY_NAMESPACE,
            "root_authority_set": root_set,
            "target_genesis_admission_claim_schema_version": (
                TARGET_GENESIS_ADMISSION_CLAIM_SCHEMA_VERSION
            ),
            "target_threshold_receipt_schema_version": (
                TARGET_THRESHOLD_RECEIPT_SCHEMA_VERSION
            ),
        },
        "facts": {
            "provider_preregistration_exact": True,
            "bootstrap_topology_structurally_non_circular": True,
            "candidate_public_key_excluded_from_root": True,
            "candidate_operator_excluded_from_root": True,
            "candidate_trust_domain_excluded_from_root": True,
            "strict_majority_threshold_frozen": True,
            "external_root_identity_verified": False,
            "external_root_key_possession_verified": False,
            "external_root_governance_verified": False,
            "root_member_independence_verified": False,
            "threshold_genesis_admission_signed": False,
            "genesis_registry_created": False,
            "provider_registered": False,
            "external_provider_conformance_verified": False,
            "runtime_mutations": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "EXTERNAL_ROOT_IDENTITY_UNVERIFIED",
            "EXTERNAL_ROOT_KEY_POSSESSION_UNVERIFIED",
            "EXTERNAL_ROOT_GOVERNANCE_UNVERIFIED",
            "ROOT_MEMBER_INDEPENDENCE_UNVERIFIED",
            "THRESHOLD_GENESIS_ADMISSION_UNSIGNED",
            "GENESIS_ADMISSION_REPLAY_REGISTRY_MISSING",
            "ATOMIC_GENESIS_REGISTRY_CREATE_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "bootstrap_topology_hash")


def verify_challenge_consumption_provider_bootstrap_topology_v1(
    document: Any,
    provider_preregistration_document: Any,
    *,
    expected_bootstrap_topology_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_challenge_consumption_provider_bootstrap_topology_v1(
            provider_preregistration_document, **build_kwargs
        )
        return (
            document == expected
            and _require_hash(
                expected_bootstrap_topology_hash,
                "expected_bootstrap_topology_hash",
            )
            == expected["bootstrap_topology_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderBootstrapTopologyError):
        return False


def build_challenge_consumption_provider_genesis_admission_plan_v1(
    topology_document: Any,
    provider_preregistration_document: Any,
    **topology_build_kwargs: Any,
) -> dict[str, Any]:
    expected_topology = (
        build_challenge_consumption_provider_bootstrap_topology_v1(
            provider_preregistration_document,
            **copy.deepcopy(topology_build_kwargs),
        )
    )
    if topology_document != expected_topology:
        raise ChallengeConsumptionProviderBootstrapTopologyError(
            "bootstrap topology is not exact"
        )
    cases = [
        {
            "case_id": f"B{index:02d}",
            "name": name,
            "executed": False,
            "observed": None,
        }
        for index, name in enumerate(_PLAN_CASES, start=1)
    ]
    document = {
        "schema_version": GENESIS_ADMISSION_PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "NON_CIRCULAR_GENESIS_ADMISSION_PLAN_FROZEN_ALL_EXTERNAL_"
            "GOVERNANCE_SIGNATURE_STORAGE_AND_CONFORMANCE_STEPS_UNEXECUTED"
        ),
        "source": {
            "bootstrap_topology_hash": expected_topology[
                "bootstrap_topology_hash"
            ],
            "provider_preregistration_hash": expected_topology["source"][
                "provider_preregistration_hash"
            ],
            "root_authority_set_hash": expected_topology["bootstrap_root"][
                "root_authority_set"
            ]["root_authority_set_hash"],
        },
        "summary": {
            "planned_case_count": len(cases),
            "executed_case_count": 0,
            "passed_case_count": 0,
            "failed_case_count": 0,
            "runtime_mutations": False,
        },
        "cases": cases,
        "facts": {
            "plan_shape_frozen": True,
            "all_cases_unexecuted": True,
            "external_root_bound": False,
            "threshold_admission_verified": False,
            "genesis_registry_created": False,
            "provider_registered": False,
            "external_provider_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "EXTERNAL_ROOT_UNBOUND",
            "GENESIS_ADMISSION_CASES_UNEXECUTED",
            "THRESHOLD_GENESIS_ADMISSION_UNSIGNED",
            "GENESIS_REGISTRY_NOT_CREATED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "genesis_admission_plan_hash")


def verify_challenge_consumption_provider_genesis_admission_plan_v1(
    document: Any,
    topology_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_genesis_admission_plan_hash: Any,
    **topology_build_kwargs: Any,
) -> bool:
    try:
        expected = build_challenge_consumption_provider_genesis_admission_plan_v1(
            topology_document,
            provider_preregistration_document,
            **topology_build_kwargs,
        )
        return (
            document == expected
            and _require_hash(
                expected_genesis_admission_plan_hash,
                "expected_genesis_admission_plan_hash",
            )
            == expected["genesis_admission_plan_hash"]
        )
    except (TypeError, ChallengeConsumptionProviderBootstrapTopologyError):
        return False


__all__ = [
    "BOOTSTRAP_MODE",
    "GENESIS_ADMISSION_PLAN_SCHEMA_VERSION",
    "ROOT_AUTHORITY_SET_SCHEMA_VERSION",
    "TOPOLOGY_SCHEMA_VERSION",
    "ChallengeConsumptionProviderBootstrapTopologyError",
    "build_challenge_consumption_provider_bootstrap_topology_v1",
    "build_challenge_consumption_provider_genesis_admission_plan_v1",
    "verify_challenge_consumption_provider_bootstrap_topology_v1",
    "verify_challenge_consumption_provider_genesis_admission_plan_v1",
]
