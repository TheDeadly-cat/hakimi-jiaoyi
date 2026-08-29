"""Consumer-first evaluator for the unmounted ADR0412 provider port."""

from __future__ import annotations

import re
from typing import Any, Mapping

from exchange_terminal.application.ports import (
    witness_ownership_state_store_v1 as store,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v11 as budget_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


EVALUATION_SCHEMA_VERSION = (
    "witness-ownership-state-persistence-consumer-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-state-consumer-first-lock-1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "current_pointer_written",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "provider_activation_allowed",
    "runtime_gate_activation_allowed",
    "witness_ownership_state_trust_allowed",
    "writer_allowed",
)
_SOURCE_TRUTH_BLOCKERS = (
    "PROVIDER_IDENTITY_UNVERIFIED",
    "PROVIDER_SIGNED_RECEIPT_MISSING",
    "DURABLE_COMMIT_UNVERIFIED",
    "LINEARIZABLE_READ_AFTER_WRITE_UNVERIFIED",
    "ROLLBACK_RESISTANCE_UNVERIFIED",
    "INDEPENDENT_PROVIDER_CONFORMANCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def evaluate_witness_ownership_state_persistence_consumer_v1(
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    *,
    expected_budget_v11_hash: Any,
    budget_v11_verify_args: Any,
    budget_v11_verify_kwargs: Any,
    expected_command_hash: Any,
    expected_registry_id: Any,
) -> dict[str, Any] | None:
    if (
        type(budget_v11_document) is not dict
        or type(command)
        is not store.WitnessOwnershipCompareConsumeAndAdvanceCommandV1
        or type(provider_result)
        is not store.WitnessOwnershipCompareConsumeAndAdvanceResultV1
        or type(budget_v11_verify_args) is not tuple
        or type(budget_v11_verify_kwargs) is not dict
        or not _is_hash(expected_budget_v11_hash)
        or not _is_hash(expected_command_hash)
        or type(expected_registry_id) is not str
        or not expected_registry_id
        or expected_registry_id != expected_registry_id.strip()
        or "expected_budget_v11_hash" in budget_v11_verify_kwargs
    ):
        return None
    try:
        v11_exact = budget_v11.verify_strategy_correlation_cluster_effective_bet_budget_v11(
            budget_v11_document,
            *budget_v11_verify_args,
            expected_budget_v11_hash=expected_budget_v11_hash,
            **dict(budget_v11_verify_kwargs),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not v11_exact:
        return None

    source = budget_v11_document.get("source")
    facts = budget_v11_document.get("facts")
    authority = budget_v11_document.get("authority")
    if (
        not isinstance(source, Mapping)
        or not isinstance(facts, Mapping)
        or not isinstance(authority, Mapping)
        or budget_v11_document.get("status") != "PASS"
        or budget_v11_document.get("admission_status") != "BLOCKED"
        or authority.get("descriptive_only") is not True
        or any(
            value is not False
            for name, value in authority.items()
            if name != "descriptive_only"
        )
        or facts.get("witness_ownership_state_persistence_verified") is not False
        or facts.get("atomic_compare_and_swap_verified") is not False
        or facts.get("durability_verified") is not False
        or facts.get("runtime_gate_integrated") is not False
        or command.command_hash != expected_command_hash
        or command.ownership_claim_hash != source.get("ownership_claim_hash")
        or command.ownership_evidence_hash
        != source.get("ownership_evidence_hash")
        or command.expected_state_hash
        != source.get("previous_ownership_state_hash")
        or command.proposed_state_hash
        != source.get("next_ownership_state_hash")
    ):
        return None

    try:
        rebuilt_command = (
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=(
                    command.namespace_preregistration_hash
                ),
                ownership_claim_hash=command.ownership_claim_hash,
                ownership_evidence_hash=command.ownership_evidence_hash,
                expected_state_hash=command.expected_state_hash,
                proposed_state_hash=command.proposed_state_hash,
                expected_registry_revision=command.expected_registry_revision,
                request_nonce_hash=command.request_nonce_hash,
            )
        )
    except (TypeError, ValueError):
        return None
    if rebuilt_command != command:
        return None

    result_exact = (
        store.verify_witness_ownership_compare_consume_and_advance_result_v1(
            provider_result,
            command,
            expected_registry_id=expected_registry_id,
        )
    )
    if not result_exact:
        return None

    advanced = (
        provider_result.outcome
        is store.WitnessOwnershipProviderOutcomeV1.ADVANCED
    )
    blockers = list(_SOURCE_TRUTH_BLOCKERS)
    if not advanced:
        blockers.insert(0, "PROVIDER_RESULT_NOT_ADVANCED")
    checks = [
        {"name": "budget_v11_exact_rebuild", "ok": True, "blocking": True},
        {
            "name": "ownership_hashes_bound_to_v11",
            "ok": True,
            "blocking": True,
        },
        {
            "name": "atomic_compare_consume_and_advance_command_exact",
            "ok": True,
            "blocking": True,
        },
        {
            "name": "provider_result_exact_and_command_bound",
            "ok": True,
            "blocking": True,
        },
        {
            "name": "provider_result_advanced",
            "ok": advanced,
            "blocking": True,
        },
        {
            "name": "provider_identity_remains_unverified",
            "ok": True,
            "blocking": True,
        },
        {
            "name": "durability_and_linearizability_remain_unverified",
            "ok": True,
            "blocking": True,
        },
    ]
    payload = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN" if advanced else "BLOCKED",
        "admission_status": "BLOCKED",
        "decision": (
            "STRUCTURALLY_BOUND_PROVIDER_ADVANCE_SOURCE_TRUTH_UNVERIFIED"
            if advanced
            else "PROVIDER_DID_NOT_ADVANCE_OWNERSHIP_STATE"
        ),
        "blockers": blockers,
        "checks": checks,
        "source": {
            "budget_v11_hash": expected_budget_v11_hash,
            "namespace": store.WITNESS_OWNERSHIP_NAMESPACE,
            "namespace_preregistration_hash": (
                command.namespace_preregistration_hash
            ),
            "ownership_claim_hash": command.ownership_claim_hash,
            "ownership_evidence_hash": command.ownership_evidence_hash,
            "previous_ownership_state_hash": command.expected_state_hash,
            "next_ownership_state_hash": command.proposed_state_hash,
            "command_hash": command.command_hash,
            "consumption_key": command.consumption_key,
            "registry_id": provider_result.registry_id,
            "provider_receipt_claim_hash": (
                provider_result.receipt_document.get("receipt_claim_hash")
                if advanced
                and isinstance(provider_result.receipt_document, Mapping)
                else None
            ),
        },
        "transition_summary": {
            "outcome": provider_result.outcome.value,
            "expected_registry_revision": command.expected_registry_revision,
            "observed_registry_revision": (
                provider_result.observed_registry_revision
            ),
            "returned_registry_revision": (
                provider_result.returned_registry_revision
            ),
            "single_atomic_operation_required": True,
            "two_phase_consume_then_advance_allowed": False,
        },
        "facts": {
            "atomic_provider_operation_contract_defined": True,
            "provider_result_structurally_bound": True,
            "provider_advance_claimed": advanced,
            "provider_identity_verified": False,
            "provider_receipt_signature_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "independent_provider_conformance_verified": False,
            "witness_ownership_state_persistence_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "network_accessed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
        "redaction": {
            "raw_budget_documents_embedded": False,
            "raw_ownership_documents_embedded": False,
            "raw_provider_credentials_embedded": False,
            "raw_provider_endpoint_embedded": False,
            "raw_signatures_or_keys_embedded": False,
        },
        "limitations": [
            "A structurally exact provider result is only a provider claim.",
            "No provider identity, key control, signature, durability, linearizability, rollback resistance, or external conformance is verified.",
            "This unmounted consumer does not activate current, paper, live, writer, migration, or runtime authority.",
        ],
    }
    return seal_strict_canonical_document(payload, "evaluation_hash")


def verify_witness_ownership_state_persistence_consumer_v1(
    document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    *,
    expected_evaluation_hash: Any,
    expected_budget_v11_hash: Any,
    budget_v11_verify_args: Any,
    budget_v11_verify_kwargs: Any,
    expected_command_hash: Any,
    expected_registry_id: Any,
) -> bool:
    if type(document) is not dict or not _is_hash(expected_evaluation_hash):
        return False
    rebuilt = evaluate_witness_ownership_state_persistence_consumer_v1(
        budget_v11_document,
        command,
        provider_result,
        expected_budget_v11_hash=expected_budget_v11_hash,
        budget_v11_verify_args=budget_v11_verify_args,
        budget_v11_verify_kwargs=budget_v11_verify_kwargs,
        expected_command_hash=expected_command_hash,
        expected_registry_id=expected_registry_id,
    )
    return (
        rebuilt is not None
        and rebuilt["evaluation_hash"] == expected_evaluation_hash
        and strict_json_contract_equal(document, rebuilt)
    )


__all__ = [
    "EVALUATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "evaluate_witness_ownership_state_persistence_consumer_v1",
    "verify_witness_ownership_state_persistence_consumer_v1",
]
