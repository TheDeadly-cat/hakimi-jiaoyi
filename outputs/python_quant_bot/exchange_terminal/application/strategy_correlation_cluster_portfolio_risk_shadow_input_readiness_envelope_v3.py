"""Consumer-first readiness envelope v3 with signed-time evidence binding.

The envelope fully reverifies its v2 source and the detached trusted-clock v3
attestation.  It proves only local evidence integrity.  External authority,
trusted current time, runtime consumption, and trading permissions remain absent.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2
    as readiness_v2_contract,
)
from exchange_terminal.services import trusted_clock_authority_v3 as trusted_clock_contract


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-shadow-input-readiness-envelope-v3"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-shadow-input-readiness-envelope-3"
SOURCE_STATE = "LOCAL_INPUT_SET_AND_SIGNED_TIME_QUORUM_VERIFIED"
GAP_STATE = "EXTERNAL_TRUST_AND_RUNTIME_CONSUMER_UNPROVEN"
MATURITY_STATE = (
    "LOCAL_INPUT_SET_AND_SIGNED_TIME_QUORUM_VERIFIED_EXTERNAL_TRUST_UNPROVEN"
)
PERMISSION_STATE = "DENIED"
CLOCK_CONTEXT_DOMAIN = (
    "hakimi.strategy-correlation.portfolio-risk-shadow-readiness-v3.clock-context.v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_V2_CONTEXT_KEYS = {
    "readiness_v1",
    "portfolio_inputs",
    "readiness_v1_verification_context",
    "portfolio_verification_contexts",
}
_CLOCK_CONTEXT_KEYS = {
    "registration",
    "receipts",
    "authority_public_keys_by_id",
    "expected_registration_hash",
    "expected_receipt_hashes",
    "request_nonce_hash",
    "request_context_hash",
    "verification_time_ms",
}


class ReadinessEnvelopeV3ContractError(ValueError):
    """Raised when a source cannot support the bounded v3 projection."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ReadinessEnvelopeV3ContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != expected:
        raise ReadinessEnvelopeV3ContractError(f"{label} keys do not match schema")
    return result


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ReadinessEnvelopeV3ContractError(f"{label} must be lowercase sha256")
    return value


def _validate_json_tree(value: Any, label: str = "payload") -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for item in value:
            _validate_json_tree(item, label)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ReadinessEnvelopeV3ContractError(f"{label} has a non-string key")
            _validate_json_tree(item, label)
        return
    raise ReadinessEnvelopeV3ContractError(f"{label} has a non-contract JSON value")


def _canonical_bytes(value: Any) -> bytes:
    _validate_json_tree(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["envelope_hash"] = _sha256(payload)
    return result


def derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
    readiness_v2: Any,
) -> str:
    """Derive the only accepted clock request-context for one v2 envelope."""

    source = _require_dict(readiness_v2, "readiness_v2")
    if source.get("schema_version") != readiness_v2_contract.SCHEMA_VERSION:
        raise ReadinessEnvelopeV3ContractError("readiness v2 schema mismatch")
    envelope_hash = _require_hash(source.get("envelope_hash"), "readiness_v2.envelope_hash")
    lineage = _require_dict(source.get("source_lineage"), "readiness_v2.source_lineage")
    source_attestation_hash = _require_hash(
        lineage.get("source_attestation_hash"), "source_attestation_hash"
    )
    future_evaluation_id_hash = _require_hash(
        lineage.get("future_evaluation_id_hash"), "future_evaluation_id_hash"
    )
    return _sha256(
        {
            "domain": CLOCK_CONTEXT_DOMAIN,
            "consumer_schema_version": SCHEMA_VERSION,
            "readiness_v2_schema_version": source["schema_version"],
            "readiness_v2_envelope_hash": envelope_hash,
            "source_attestation_hash": source_attestation_hash,
            "future_evaluation_id_hash": future_evaluation_id_hash,
        }
    )


def _verify_readiness_v2(
    readiness_v2: Any, readiness_v2_verification_context: Any
) -> dict[str, Any]:
    context = _require_exact_keys(
        readiness_v2_verification_context,
        _V2_CONTEXT_KEYS,
        "readiness_v2_verification_context",
    )
    if not readiness_v2_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
        readiness_v2,
        context["readiness_v1"],
        context["portfolio_inputs"],
        readiness_v1_verification_context=context["readiness_v1_verification_context"],
        portfolio_verification_contexts=context["portfolio_verification_contexts"],
    ):
        raise ReadinessEnvelopeV3ContractError("readiness v2 public re-verification failed")
    source = _require_dict(readiness_v2, "readiness_v2")
    if source.get("schema_version") != readiness_v2_contract.SCHEMA_VERSION:
        raise ReadinessEnvelopeV3ContractError("readiness v2 schema mismatch")
    if (
        source.get("status") != "UNKNOWN"
        or source.get("source_state") != "LOCAL_INPUT_SET_VERIFIED"
        or source.get("gap_state") != GAP_STATE
        or source.get("maturity_state")
        != "LOCAL_INPUT_SET_VERIFIED_EXTERNAL_TRUST_UNPROVEN"
        or source.get("permission_state") != PERMISSION_STATE
    ):
        raise ReadinessEnvelopeV3ContractError("readiness v2 state is not the pinned source state")
    inventory = source.get("input_inventory")
    if type(inventory) is not list or len(inventory) != 13:
        raise ReadinessEnvelopeV3ContractError("readiness v2 input inventory is not complete")
    if any(
        type(item) is not dict or item.get("state") != "VERIFIED" for item in inventory
    ):
        raise ReadinessEnvelopeV3ContractError("readiness v2 contains an unverified input")
    summary = _require_dict(source.get("summary"), "readiness_v2.summary")
    if summary != {
        "required_input_count": 13,
        "verified_input_count": 13,
        "unverified_input_count": 0,
        "not_supplied_input_count": 0,
    }:
        raise ReadinessEnvelopeV3ContractError("readiness v2 summary mismatch")
    facts = _require_dict(source.get("facts"), "readiness_v2.facts")
    if facts.get("local_required_input_set_verified") is not True:
        raise ReadinessEnvelopeV3ContractError("readiness v2 local input set is unverified")
    if facts.get("external_time_authority_authenticated") is not False:
        raise ReadinessEnvelopeV3ContractError("readiness v2 time-authority claim was inflated")
    permissions = _require_dict(source.get("permissions"), "readiness_v2.permissions")
    if any(value is not False for value in permissions.values()):
        raise ReadinessEnvelopeV3ContractError("readiness v2 permissions were inflated")
    authority = _require_dict(source.get("authority"), "readiness_v2.authority")
    if authority.get("descriptive_only") is not True or any(
        value is not False for key, value in authority.items() if key != "descriptive_only"
    ):
        raise ReadinessEnvelopeV3ContractError("readiness v2 authority was inflated")
    return source


def _verify_trusted_clock(
    readiness_v2: dict[str, Any],
    trusted_clock_attestation: Any,
    trusted_clock_verification_context: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _require_exact_keys(
        trusted_clock_verification_context,
        _CLOCK_CONTEXT_KEYS,
        "trusted_clock_verification_context",
    )
    derived_context_hash = (
        derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
            readiness_v2
        )
    )
    if context["request_context_hash"] != derived_context_hash:
        raise ReadinessEnvelopeV3ContractError("trusted-clock request context is not consumer-bound")
    if not trusted_clock_contract.verify_trusted_clock_authority_attestation_v3(
        trusted_clock_attestation,
        context["registration"],
        context["receipts"],
        context["authority_public_keys_by_id"],
        expected_registration_hash=context["expected_registration_hash"],
        expected_receipt_hashes=context["expected_receipt_hashes"],
        request_nonce_hash=context["request_nonce_hash"],
        request_context_hash=context["request_context_hash"],
        verification_time_ms=context["verification_time_ms"],
    ):
        raise ReadinessEnvelopeV3ContractError("trusted-clock public re-verification failed")
    attestation = _require_dict(trusted_clock_attestation, "trusted_clock_attestation")
    if attestation.get("schema_version") != trusted_clock_contract.ATTESTATION_SCHEMA_VERSION:
        raise ReadinessEnvelopeV3ContractError("trusted-clock schema mismatch")
    verification = _require_dict(
        attestation.get("verification"), "trusted_clock_attestation.verification"
    )
    if (
        verification.get("status") != "PASS"
        or verification.get("state") != trusted_clock_contract.VERIFICATION_STATE
        or type(verification.get("source_count")) is not int
        or verification["source_count"] < 2
    ):
        raise ReadinessEnvelopeV3ContractError("trusted-clock bounded state mismatch")
    lineage = _require_dict(
        attestation.get("source_lineage"), "trusted_clock_attestation.source_lineage"
    )
    if lineage.get("request_context_hash") != derived_context_hash:
        raise ReadinessEnvelopeV3ContractError("trusted-clock attestation context mismatch")
    if lineage.get("request_nonce_hash") != context["request_nonce_hash"]:
        raise ReadinessEnvelopeV3ContractError("trusted-clock nonce lineage mismatch")
    facts = _require_dict(attestation.get("facts"), "trusted_clock_attestation.facts")
    required_true = (
        "registration_integrity_verified",
        "registered_public_key_hashes_verified",
        "detached_signatures_verified",
        "multi_authority_quorum_verified",
        "receipt_age_against_supplied_time_checked",
        "provider_spread_checked",
        "local_skew_checked",
    )
    required_false = (
        "external_time_authority_trust_verified",
        "registration_governance_verified",
        "verification_time_source_trusted",
        "request_nonce_uniqueness_verified",
        "replay_registry_verified",
        "current_time_established",
        "paper_trading_authorized",
        "live_trading_authorized",
        "profitability_proven",
    )
    if any(facts.get(key) is not True for key in required_true):
        raise ReadinessEnvelopeV3ContractError("trusted-clock local fact is unverified")
    if any(facts.get(key) is not False for key in required_false):
        raise ReadinessEnvelopeV3ContractError("trusted-clock external claim was inflated")
    permission = _require_dict(
        attestation.get("permission"), "trusted_clock_attestation.permission"
    )
    if permission.get("research_evidence_only") is not True or any(
        value is not False for key, value in permission.items() if key != "research_evidence_only"
    ):
        raise ReadinessEnvelopeV3ContractError("trusted-clock permission was inflated")
    _require_hash(attestation.get("attestation_hash"), "trusted_clock attestation_hash")
    return attestation, context


def build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
    readiness_v2: Any,
    trusted_clock_attestation: Any,
    *,
    readiness_v2_verification_context: Any,
    trusted_clock_verification_context: Any,
) -> dict[str, Any]:
    """Build the 14-input detached envelope after full source re-verification."""

    source = _verify_readiness_v2(readiness_v2, readiness_v2_verification_context)
    clock, clock_context = _verify_trusted_clock(
        source, trusted_clock_attestation, trusted_clock_verification_context
    )
    clock_lineage = clock["source_lineage"]
    clock_verification = clock["verification"]

    input_inventory = copy.deepcopy(source["input_inventory"])
    input_inventory.append(
        {
            "input": "signed_trusted_clock_authority_attestation",
            "schema_version": trusted_clock_contract.ATTESTATION_SCHEMA_VERSION,
            "state": "VERIFIED",
        }
    )

    facts = copy.deepcopy(source["facts"])
    facts.update(
        {
            "readiness_v2_verified": True,
            "signed_trusted_clock_attestation_verified": True,
            "signed_time_registration_integrity_verified": True,
            "signed_time_public_key_hashes_verified": True,
            "signed_time_detached_signatures_verified": True,
            "signed_time_multi_authority_quorum_verified": True,
            "signed_time_policy_checks_verified": True,
            "signed_time_external_authority_trust_verified": False,
            "signed_time_registration_governance_verified": False,
            "signed_time_verification_source_trusted": False,
            "signed_time_nonce_uniqueness_verified": False,
            "signed_time_replay_registry_verified": False,
            "current_time_established": False,
            "profitability_verified": False,
        }
    )

    blockers = list(source["blockers"])
    additions = [
        "external_time_authority_key_ownership_unproven",
        "trusted_time_registration_governance_unproven",
        "trusted_clock_verification_time_source_untrusted",
        "trusted_clock_nonce_uniqueness_unproven",
        "trusted_clock_replay_registry_unproven",
    ]
    blockers.extend(item for item in additions if item not in blockers)

    gate_outcomes = copy.deepcopy(source["gate_outcomes"])
    gate_outcomes["signed_trusted_clock_authority"] = {
        "status": clock_verification["status"],
        "state": clock_verification["state"],
        "source_count": clock_verification["source_count"],
        "reference_policy": clock_verification["reference_policy"],
        "provider_spread_ms": clock_verification["provider_spread_ms"],
        "local_skew_ms": clock_verification["local_skew_ms"],
        "registration_integrity_verified": True,
        "detached_signatures_verified": True,
        "multi_authority_quorum_verified": True,
        "external_authority_trust_verified": False,
        "current_time_established": False,
    }

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "source_state": SOURCE_STATE,
        "gap_state": GAP_STATE,
        "maturity_state": MATURITY_STATE,
        "permission_state": PERMISSION_STATE,
        "axes": {
            "source": SOURCE_STATE,
            "gap": GAP_STATE,
            "maturity": MATURITY_STATE,
            "permission": PERMISSION_STATE,
        },
        "source_lineage": {
            "readiness_v2_envelope_hash": source["envelope_hash"],
            "source_attestation_hash": source["source_lineage"]["source_attestation_hash"],
            "future_evaluation_id_hash": source["source_lineage"]["future_evaluation_id_hash"],
            "trusted_clock_attestation_hash": clock["attestation_hash"],
            "trusted_clock_registration_hash": clock_lineage["registration_hash"],
            "trusted_clock_receipt_set_hash": _sha256(
                clock_lineage["receipt_hashes_by_authority_id"]
            ),
            "trusted_clock_request_nonce_hash": clock_lineage["request_nonce_hash"],
            "trusted_clock_request_context_hash": clock_lineage["request_context_hash"],
        },
        "input_inventory": input_inventory,
        "summary": {
            "required_input_count": 14,
            "verified_input_count": 14,
            "unverified_input_count": 0,
            "not_supplied_input_count": 0,
        },
        "facts": facts,
        "gate_outcomes": gate_outcomes,
        "blockers": blockers,
        "permissions": copy.deepcopy(source["permissions"]),
        "authority": copy.deepcopy(source["authority"]),
    }
    if clock_context["request_context_hash"] != payload["source_lineage"][
        "trusted_clock_request_context_hash"
    ]:
        raise ReadinessEnvelopeV3ContractError("clock context changed during projection")
    return _seal(payload)


def verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
    document: Any,
    readiness_v2: Any,
    trusted_clock_attestation: Any,
    *,
    readiness_v2_verification_context: Any,
    trusted_clock_verification_context: Any,
) -> bool:
    """Rebuild from every source input instead of trusting the envelope seal."""

    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
            readiness_v2,
            trusted_clock_attestation,
            readiness_v2_verification_context=readiness_v2_verification_context,
            trusted_clock_verification_context=trusted_clock_verification_context,
        )
    except (ReadinessEnvelopeV3ContractError, ValueError, TypeError):
        return False
    return type(document) is dict and document == rebuilt


__all__ = [
    "CLOCK_CONTEXT_DOMAIN",
    "GAP_STATE",
    "MATURITY_STATE",
    "PERMISSION_STATE",
    "ReadinessEnvelopeV3ContractError",
    "SCHEMA_VERSION",
    "SOURCE_STATE",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3",
    "derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3",
    "verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3",
]
