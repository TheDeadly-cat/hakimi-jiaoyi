"""Blocked shadow-consumer preregistration v4 with ADR0181 contract pins.

This module pins a future consumer contract.  It deliberately accepts no
readiness-envelope evidence and performs no consumer, runtime, or trading work.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1
    as readiness_v1_contract,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2
    as readiness_v2_contract,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3
    as readiness_v3_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3
    as preregistration_v3_contract,
)
from exchange_terminal.services import trusted_clock_authority_v3 as trusted_clock_contract


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v4"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v4-verification-v1"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-shadow-preregistration-v4-lock-1"
STATUS = "BLOCKED"
DECISION = (
    "SUCCESSOR_PREREGISTERED_ADR0181_READINESS_CONTRACT_PINNED_EVIDENCE_NOT_BOUND"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_V3_CONTEXT_KEYS = {"preregistration_v2", "v2_verification_context"}
_NEW_IMPLEMENTATION_PINS = {
    "shadow_input_readiness_envelope_v1": (
        "exchange_terminal/application/strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1.py",
        "4bd1743df7e359636a96338b1d6fafdfcf406e9441af8380b60fcc59a55c8671",
    ),
    "shadow_input_readiness_envelope_v2": (
        "exchange_terminal/application/strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2.py",
        "92d9848682fe68b8ca55b82be8cff46665593e6c6c68d963d04f60f811da60c6",
    ),
    "trusted_clock_authority_v3": (
        "exchange_terminal/services/trusted_clock_authority_v3.py",
        "9a12682fb00dee3d6851ac62d4a37de0c66992e3f57d8e9715e23712d25a8c62",
    ),
    "shadow_input_readiness_envelope_v3": (
        "exchange_terminal/application/strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3.py",
        "f76b454730d4da9430129c50f9fc4bb81894f7ee66ce440c493d4ecce273a584",
    ),
    "shadow_preregistration_v3": (
        "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3.py",
        "ecd0affef70ac6461deabab8b0c00db94265eb175bf87c0c066deaa1d051bd36",
    ),
}


class ShadowConsumerPreregistrationV4ContractError(ValueError):
    """Raised when an immutable predecessor or implementation pin drifts."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ShadowConsumerPreregistrationV4ContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != expected:
        raise ShadowConsumerPreregistrationV4ContractError(
            f"{label} keys do not match schema"
        )
    return result


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ShadowConsumerPreregistrationV4ContractError(
            f"{label} must be lowercase sha256"
        )
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["preregistration_hash"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return result


def expected_shadow_consumer_implementation_sha256_v4() -> dict[str, str]:
    """Return the exact predecessor plus readiness-contract source manifest."""

    result = preregistration_v3_contract.expected_shadow_consumer_implementation_sha256_v3()
    result.update(
        {artifact_id: pin[1] for artifact_id, pin in _NEW_IMPLEMENTATION_PINS.items()}
    )
    return dict(sorted(result.items()))


def _verify_manifest(current_implementation_sha256: Any) -> dict[str, str]:
    supplied = _require_dict(
        current_implementation_sha256, "current_implementation_sha256"
    )
    expected = expected_shadow_consumer_implementation_sha256_v4()
    if set(supplied) != set(expected):
        raise ShadowConsumerPreregistrationV4ContractError(
            "implementation manifest must exactly match v4"
        )
    normalized: dict[str, str] = {}
    for artifact_id in sorted(expected):
        actual_hash = _require_hash(supplied[artifact_id], f"hash for {artifact_id}")
        if actual_hash != expected[artifact_id]:
            raise ShadowConsumerPreregistrationV4ContractError(
                f"implementation fingerprint drift for {artifact_id}"
            )
        normalized[artifact_id] = actual_hash
    return normalized


def _verify_v3_source(
    preregistration_v3: Any,
    v3_verification_context: Any,
    manifest: dict[str, str],
) -> dict[str, Any]:
    context = _require_exact_keys(
        v3_verification_context, _V3_CONTEXT_KEYS, "v3_verification_context"
    )
    v3_manifest_keys = set(
        preregistration_v3_contract.expected_shadow_consumer_implementation_sha256_v3()
    )
    v3_manifest = {key: manifest[key] for key in v3_manifest_keys}
    verification = preregistration_v3_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
        preregistration_v3,
        context["preregistration_v2"],
        context["v2_verification_context"],
        v3_manifest,
    )
    if (
        type(verification) is not dict
        or verification.get("status") != "PASS"
        or verification.get("preregistration_exactly_verified") is not True
        or verification.get("preregistration_status") != "BLOCKED"
    ):
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 public re-verification failed"
        )
    source = _require_dict(preregistration_v3, "preregistration_v3")
    if (
        source.get("schema_version")
        != "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v3"
        or source.get("static_fingerprint")
        != preregistration_v3_contract.STATIC_FINGERPRINT
        or source.get("status") != "BLOCKED"
    ):
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 source state mismatch"
        )
    _require_hash(source.get("preregistration_hash"), "v3 preregistration_hash")
    closed = source.get("closed_local_blockers")
    if type(closed) is not list or len(closed) != 3:
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 local closure count drifted"
        )
    capabilities = source.get("newly_pinned_local_capabilities")
    if type(capabilities) is not list or len(capabilities) != 1:
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 capability pins drifted"
        )
    content_pin = capabilities[0]
    if (
        content_pin.get("capability")
        != "PROVIDER_DATASET_CONTENT_ISSUANCE_REPLAY_CONTRACT"
        or content_pin.get("contract_pinned") is not True
        or content_pin.get("evidence_bound") is not False
        or content_pin.get("external_authority_verified") is not False
    ):
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 content-replay pin drifted"
        )
    authority = _require_dict(source.get("authority"), "v3 authority")
    if authority.get("descriptive_only") is not True or any(
        value is not False for key, value in authority.items() if key != "descriptive_only"
    ):
        raise ShadowConsumerPreregistrationV4ContractError(
            "immutable v3 authority was inflated"
        )
    return source


def build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
    preregistration_v3: Any,
    v3_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Pin ADR0181 without accepting or binding an ADR0181 evidence instance."""

    manifest = _verify_manifest(current_implementation_sha256)
    source = _verify_v3_source(preregistration_v3, v3_verification_context, manifest)

    artifacts = copy.deepcopy(source["source"]["artifacts"])
    existing_ids = {item["artifact_id"] for item in artifacts}
    for artifact_id, (path, expected_hash) in _NEW_IMPLEMENTATION_PINS.items():
        if artifact_id not in existing_ids:
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "path": path,
                    "expected_sha256": expected_hash,
                }
            )

    capabilities = copy.deepcopy(source["newly_pinned_local_capabilities"])
    capabilities.append(
        {
            "capability": "PORTFOLIO_RISK_SHADOW_INPUT_READINESS_ENVELOPE_V3",
            "pin": "ADR0181_SCHEMA_FINGERPRINT_AND_IMPLEMENTATION_CHAIN_PINNED_EVIDENCE_NOT_BOUND",
            "contract_pinned": True,
            "evidence_bound": False,
            "consumer_executed": False,
            "external_authority_verified": False,
        }
    )

    required_schemas = copy.deepcopy(source["required_shadow_input_schemas"])
    required_schemas.append(
        {
            "input": "signed_trusted_clock_authority_attestation",
            "schema_version": trusted_clock_contract.ATTESTATION_SCHEMA_VERSION,
        }
    )

    blockers = list(source["blockers"])
    for blocker in (
        "readiness_envelope_v3_evidence_not_bound",
        "readiness_envelope_v3_exact_hash_not_verified",
        "signed_time_external_authority_trust_unproven",
        "trusted_clock_nonce_and_replay_durability_unproven",
    ):
        if blocker not in blockers:
            blockers.append(blocker)

    facts = copy.deepcopy(source["facts"])
    facts.update(
        {
            "immutable_v3_exactly_verified": True,
            "readiness_envelope_v3_contract_pinned": True,
            "readiness_envelope_v3_implementation_chain_pinned": True,
            "readiness_envelope_v3_evidence_bound": False,
            "readiness_envelope_v3_exactly_verified": False,
            "signed_time_evidence_bound": False,
            "signed_time_external_authority_trust_verified": False,
            "trusted_clock_nonce_and_replay_durability_verified": False,
            "shadow_application_consumer_implemented": False,
            "shadow_consumer_executed": False,
            "risk_service_invoked": False,
            "runtime_assets_accessed": False,
            "server_route_registered": False,
            "ui_mounted": False,
        }
    )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": DECISION,
        "source": {
            "immutable_v3_exactly_verified": True,
            "immutable_v3_schema_version": source["schema_version"],
            "immutable_v3_preregistration_hash": source["preregistration_hash"],
            "immutable_v3_implementation_sha256": manifest[
                "shadow_preregistration_v3"
            ],
            "successor_manifest_contract_verified": True,
            "successor_implementation_fingerprints_match": True,
            "artifacts": artifacts,
        },
        "contract_pins": {
            "immutable_v3_schema_version": source["schema_version"],
            "immutable_v3_preregistration_hash": source["preregistration_hash"],
            "immutable_v3_contract_pins": copy.deepcopy(source["contract_pins"]),
            "readiness_v1_schema_version": readiness_v1_contract.SCHEMA_VERSION,
            "readiness_v2_schema_version": readiness_v2_contract.SCHEMA_VERSION,
            "trusted_clock_attestation_schema_version": (
                trusted_clock_contract.ATTESTATION_SCHEMA_VERSION
            ),
            "trusted_clock_static_fingerprint": trusted_clock_contract.STATIC_FINGERPRINT,
            "readiness_v3_schema_version": readiness_v3_contract.SCHEMA_VERSION,
            "readiness_v3_static_fingerprint": readiness_v3_contract.STATIC_FINGERPRINT,
            "readiness_v3_maturity_state": readiness_v3_contract.MATURITY_STATE,
            "readiness_v3_required_input_count": 14,
            "readiness_v3_evidence_binding_policy": (
                "EXACT_ENVELOPE_HASH_AND_FULL_PUBLIC_REVERIFICATION_REQUIRED_V1"
            ),
        },
        "required_shadow_input_schemas": required_schemas,
        "closed_local_blockers": copy.deepcopy(source["closed_local_blockers"]),
        "newly_pinned_local_capabilities": capabilities,
        "blocker_refinements": copy.deepcopy(source["blocker_refinements"]),
        "blockers": blockers,
        "facts": facts,
        "reuse_plan": copy.deepcopy(source["reuse_plan"]),
        "activation_order": [
            "BIND_AUTHENTICATED_PROVIDER_IDENTITY_KEY_CONTROL_AND_DATA_ISSUANCE",
            "SUPPLY_EXACT_ADR0176_REGISTRATION_CHECKPOINT_PROOFS_AND_AUDIT",
            "VERIFY_EXTERNAL_CONTENT_REPLAY_REGISTRY_AUTHORITY_AND_DURABLE_PUBLICATION",
            "AUTHENTICATE_EXTERNAL_TIME_AUTHORITY_FOR_FRESHNESS_REFERENCE",
            "SUPPLY_AND_EXACTLY_VERIFY_ADR0181_READINESS_ENVELOPE",
            "BIND_DURABLE_TRUSTED_CLOCK_NONCE_AND_REPLAY_ENFORCEMENT",
            "IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V4",
            "INDEPENDENTLY_REVIEW_SYNTHETIC_SHADOW_CALLS",
            "VERSION_RISK_SERVICE_INPUT_CONTRACT",
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        ],
        "authority": copy.deepcopy(source["authority"]),
    }
    return _seal(payload)


def verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
    document: Any,
    preregistration_v3: Any,
    v3_verification_context: Any,
    current_implementation_sha256: Any,
) -> dict[str, Any]:
    """Rebuild the preregistration and return a fail-closed verification result."""

    blockers: list[str] = []
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
            preregistration_v3,
            v3_verification_context,
            current_implementation_sha256,
        )
        exactly_verified = type(document) is dict and document == rebuilt
        if not exactly_verified:
            blockers.append("PREREGISTRATION_V4_EXACT_REBUILD_MISMATCH")
    except (ShadowConsumerPreregistrationV4ContractError, ValueError, TypeError):
        exactly_verified = False
        blockers.append("PREREGISTRATION_V4_SOURCE_OR_MANIFEST_UNVERIFIED")

    authority = document.get("authority", {}) if type(document) is dict else {}
    authority_denied = (
        type(authority) is dict
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )
    if not authority_denied:
        blockers.append("PREREGISTRATION_V4_AUTHORITY_NOT_FAIL_CLOSED")
    passed = exactly_verified and authority_denied
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "preregistration_exactly_verified": exactly_verified,
        "preregistration_status": document.get("status") if type(document) is dict else None,
        "blockers": blockers,
        "shadow_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "DECISION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS",
    "ShadowConsumerPreregistrationV4ContractError",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4",
    "expected_shadow_consumer_implementation_sha256_v4",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4",
]
