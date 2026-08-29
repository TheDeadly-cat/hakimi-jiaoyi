"""Redacted first-consumer projection for provider replay evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from exchange_terminal.services.strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 import (
        verify_provider_dataset_key_lifecycle_replay_gate_v1 as verify_provider_replay_gate,
    )
    from exchange_terminal.services.strategy_correlation_strata_protocol_projection import (
        verify_strategy_correlation_strata_protocol_migration_public_summary as verify_protocol_summary,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )
except ModuleNotFoundError:
    from services.strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 import (
        verify_provider_dataset_key_lifecycle_replay_gate_v1 as verify_provider_replay_gate,
    )
    from services.strategy_correlation_strata_protocol_projection import (
        verify_strategy_correlation_strata_protocol_migration_public_summary as verify_protocol_summary,
    )
    from services.strict_canonical_json_hash import strict_json_contract_equal


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-provider-evidence-public-projection-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-evidence-public-projection-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-evidence-public-projection-1"
)


def _permission() -> dict[str, Any]:
    return {
        "status": "RESEARCH_ONLY",
        "descriptive_only": True,
        "profitability_claim_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _redaction() -> dict[str, bool]:
    return {
        "symbol_identities_exposed": False,
        "provider_identity_exposed": False,
        "dataset_identity_exposed": False,
        "key_identifiers_exposed": False,
        "signature_material_exposed": False,
        "merkle_paths_exposed": False,
        "verification_context_exposed": False,
    }


def _verifier_passed(
    verifier: Callable[..., Any],
    document: Any,
    context: Any,
) -> bool:
    if type(document) is not dict or type(context) is not dict:
        return False
    try:
        result = verifier(document, **context)
    except Exception:
        return False
    return type(result) is dict and result.get("status") == "PASS"


def _projection(*, sources_verified: bool) -> dict[str, Any]:
    verification_status = "VERIFIED" if sources_verified else "UNKNOWN"
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "OBSERVED" if sources_verified else "UNKNOWN",
            "strata_protocol_public_summary": verification_status,
            "provider_dataset_key_lifecycle_replay_gate": verification_status,
            "semantic_gate_outcome_projected": False,
        },
        "gap": {
            "status": "OPEN",
            "provider_gate_outcome": "NOT_PROJECTED",
            "current_consumer_binding": "ABSENT",
            "natural_forward_chain_binding": "ABSENT",
            "durable_external_publication": "NOT_PROVEN",
            "external_registry_authority": "NOT_PROVEN",
            "future_replay_absence": "NOT_PROVEN",
        },
        "maturity": {
            "status": "UNKNOWN",
            "source_contracts_verified": sources_verified,
            "consumer_first_projection_only": True,
            "natural_forward_maturity_proven": False,
            "market_outcome_evidence_present": False,
        },
        "activation": {
            "status": "INACTIVE_CANDIDATE",
            "current_reference_present": False,
            "automatic_activation_allowed": False,
            "current_pointer_mutation_allowed": False,
        },
        "claims": {
            "source_contract_integrity_verified": sources_verified,
            "provider_gate_outcome_proven": False,
            "global_dataset_key_uniqueness_proven": False,
            "future_replay_absence_proven": False,
            "external_registry_authority_proven": False,
            "profitability_proven": False,
        },
        "redaction": _redaction(),
        "permission": _permission(),
    }


def build_strategy_correlation_provider_evidence_public_projection_v1(
    protocol_summary: Any,
    provider_replay_gate: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> dict[str, Any]:
    """Project verifier state without projecting private inputs or gate outcome."""

    protocol_verified = _verifier_passed(
        verify_protocol_summary,
        protocol_summary,
        protocol_verification_context,
    )
    provider_replay_verified = _verifier_passed(
        verify_provider_replay_gate,
        provider_replay_gate,
        provider_replay_verification_context,
    )
    return _projection(
        sources_verified=protocol_verified and provider_replay_verified
    )


def verify_strategy_correlation_provider_evidence_public_projection_v1(
    document: Any,
    protocol_summary: Any,
    provider_replay_gate: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> dict[str, Any]:
    """Verify an exact rebuild; PASS does not mean the upstream gate passed."""

    expected = build_strategy_correlation_provider_evidence_public_projection_v1(
        protocol_summary,
        provider_replay_gate,
        protocol_verification_context=protocol_verification_context,
        provider_replay_verification_context=provider_replay_verification_context,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("provider_evidence_public_projection_contract_invalid")
    elif not strict_json_contract_equal(document, expected):
        blockers.append("provider_evidence_public_projection_exact_rebuild_mismatch")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "upstream_source_contracts_verified": expected["maturity"][
            "source_contracts_verified"
        ],
        "provider_gate_outcome_proven": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "PROJECTION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_provider_evidence_public_projection_v1",
    "verify_strategy_correlation_provider_evidence_public_projection_v1",
]
