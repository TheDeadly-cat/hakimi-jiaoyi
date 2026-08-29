"""Bind an exact ADR0476 candidate to an uncommitted replay-cursor CAS result.

The caller cannot provide a freshness result.  This contract reconstructs it
from an exactly verified ADR0476 binding, builds the existing CAS intent, and
simulates the transition against a caller-observed cursor.  A changed returned
cursor is only an in-memory candidate; no storage commit or provider trust is
established.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final

from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_freshness_replay_binding_v1
    as source_binding,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1
    as cas_contract,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-cluster-v9-position-derived-snapshot-"
    "replay-cursor-cas-binding-v1"
)
STATUS_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE: Final = (
    "OBSERVED_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE"
)
STATUS_BLOCKED: Final = "BLOCKED"
STATUS_UNKNOWN: Final = "UNKNOWN"
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_CONTEXT_KEYS = {
    "adapter_result",
    "v9_document",
    "v9_verification_context",
    "position_derived_result",
    "batch_preflight_document",
    "projection_preregistration",
    "proposals",
    "exposure_policy",
    "attestation",
    "reference",
    "cursor",
    "freshness_policy",
    "expected_adapter_hash",
    "expected_v9_reconciliation_hash",
    "expected_position_derived_result_hash",
    "expected_batch_preflight_hash",
    "expected_projection_preregistration_hash",
    "projection_verification_context",
    "expected_attestation_hash",
    "expected_reference_hash",
    "expected_cursor_hash",
    "expected_stream_id",
}


@dataclass(frozen=True, slots=True)
class V9PositionDerivedSnapshotReplayCursorCasBindingResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    source_freshness_binding_hash: str
    source_adapter_hash: str
    source_position_derived_result_hash: str
    source_derived_incumbent_snapshot_hash: str
    freshness_result_fingerprint_sha256: str
    request_nonce_hash: str
    intent_hash: str
    receipt_hash: str
    outcome: str
    gate_status: str
    stream_id: str
    projection_preregistration_hash: str
    attestation_hash: str
    expected_cursor_hash: str
    observed_cursor_hash: str
    returned_cursor_hash: str
    candidate_sequence: int
    observed_high_water_sequence: int
    returned_high_water_sequence: int
    returned_cursor_changed: bool
    returned_cursor: freshness_gate.IncumbentSnapshotReplayCursorV1
    source_binding_exactly_verified: bool
    freshness_result_reconstructed_from_source_binding: bool
    cas_intent_exactly_bound: bool
    input_cursor_mutation_performed: bool
    observed_cursor_provider_registered: bool
    observed_cursor_source_truth_verified: bool
    consume_once_verified: bool
    atomic_storage_commit_verified: bool
    durable_commit_verified: bool
    linearizable_read_verified: bool
    replay_registry_persistence_verified: bool
    cursor_write_performed: bool
    runtime_consumer_bound: bool
    current_admission_allowed: bool
    paper_authorized: bool
    live_order_allowed: bool
    profitability_proven: bool
    binding_hash: str


def _is_hash(value: object) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _canonical_sha256(value: object) -> str | None:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _reconstruct_freshness_result(
    binding: source_binding.V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
) -> freshness_gate.IncumbentSnapshotFreshnessReplayResultV1:
    return freshness_gate.IncumbentSnapshotFreshnessReplayResultV1(
        contract_version=freshness_gate.CONTRACT_VERSION,
        status=binding.freshness_status,
        permission_state="UNAUTHORIZED",
        permission=False,
        research_only=True,
        blocker_codes=binding.blocker_codes,
        post_merge_result_hash=binding.freshness_post_merge_result_hash,
        post_merge_status=binding.freshness_post_merge_status,
        attestation_hash=binding.attestation_hash,
        reference_hash=binding.reference_hash,
        cursor_hash=binding.cursor_hash,
        policy_fingerprint_sha256=(
            binding.freshness_policy_fingerprint_sha256
        ),
        snapshot_sequence=binding.snapshot_sequence,
        head_sequence=binding.head_sequence,
        sequence_lag=binding.sequence_lag,
        cursor_high_water_sequence=binding.cursor_high_water_sequence,
        cursor_mutation_performed=False,
    )


def _returned_cursor_payload(
    cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
) -> dict[str, object]:
    return {
        "cursor_version": cursor.cursor_version,
        "stream_id": cursor.stream_id,
        "projection_preregistration_hash": (
            cursor.projection_preregistration_hash
        ),
        "high_water_sequence": cursor.high_water_sequence,
        "high_water_attestation_hash": cursor.high_water_attestation_hash,
        "consumed_attestation_hashes": list(cursor.consumed_attestation_hashes),
        "cursor_hash": cursor.cursor_hash,
    }


def _binding_core(fields: dict[str, object]) -> dict[str, object]:
    core = dict(fields)
    cursor = core["returned_cursor"]
    if not isinstance(cursor, freshness_gate.IncumbentSnapshotReplayCursorV1):
        raise TypeError("returned cursor type drift")
    core["returned_cursor"] = _returned_cursor_payload(cursor)
    return core


def evaluate_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
    freshness_binding_result: source_binding.V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
    freshness_binding_verification_context: Any,
    attestation: freshness_gate.IncumbentSnapshotSequenceAttestationV1,
    base_cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    *,
    expected_freshness_binding_hash: Any,
    request_nonce_hash: Any,
    expected_observed_cursor_hash: Any,
) -> V9PositionDerivedSnapshotReplayCursorCasBindingResultV1 | None:
    if (
        not isinstance(
            freshness_binding_result,
            source_binding.V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
        )
        or type(freshness_binding_verification_context) is not dict
        or set(freshness_binding_verification_context)
        != _SOURCE_CONTEXT_KEYS
        or not isinstance(
            attestation,
            freshness_gate.IncumbentSnapshotSequenceAttestationV1,
        )
        or not isinstance(
            base_cursor,
            freshness_gate.IncumbentSnapshotReplayCursorV1,
        )
        or not isinstance(
            observed_cursor,
            freshness_gate.IncumbentSnapshotReplayCursorV1,
        )
        or not _is_hash(expected_freshness_binding_hash)
        or freshness_binding_result.binding_hash
        != expected_freshness_binding_hash
        or not _is_hash(request_nonce_hash)
        or not _is_hash(expected_observed_cursor_hash)
        or observed_cursor.cursor_hash != expected_observed_cursor_hash
        or freshness_binding_result.status
        != source_binding.STATUS_FRESH_UNREPLAYED_BOUND_CANDIDATE
        or freshness_binding_result.blocker_codes != ()
        or freshness_binding_result.local_sequence_freshness_candidate_observed
        is not True
        or freshness_binding_verification_context.get("attestation")
        != attestation
        or freshness_binding_verification_context.get("cursor") != base_cursor
    ):
        return None
    try:
        source_exact = source_binding.verify_v9_position_derived_snapshot_freshness_replay_binding_v1(
            freshness_binding_result,
            **deepcopy(freshness_binding_verification_context),
        )
    except (KeyError, TypeError, ValueError):
        source_exact = False
    if not source_exact:
        return None

    freshness_result = _reconstruct_freshness_result(
        freshness_binding_result
    )
    fingerprint = cas_contract.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
        freshness_result
    )
    if fingerprint is None:
        return None
    intent = cas_contract.build_incumbent_snapshot_replay_cursor_cas_transition_intent_v1(
        freshness_result,
        attestation,
        base_cursor,
        request_nonce_hash=request_nonce_hash,
        expected_freshness_result_fingerprint_sha256=fingerprint,
        expected_attestation_hash=attestation.attestation_hash,
        expected_cursor_hash=base_cursor.cursor_hash,
    )
    if intent is None:
        return None
    simulation = cas_contract.simulate_incumbent_snapshot_replay_cursor_cas_transition_v1(
        base_cursor,
        observed_cursor,
        attestation,
        freshness_result,
        intent,
        expected_intent_hash=intent.intent_hash,
        expected_freshness_result_fingerprint_sha256=fingerprint,
        expected_attestation_hash=attestation.attestation_hash,
        expected_base_cursor_hash=base_cursor.cursor_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
        expected_stream_id=base_cursor.stream_id,
        expected_projection_preregistration_hash=(
            base_cursor.projection_preregistration_hash
        ),
    )
    if simulation is None:
        return None
    receipt = simulation.receipt
    returned_cursor = simulation.returned_cursor
    if receipt.outcome == cas_contract.OUTCOME_ADVANCED_IN_RETURNED_CURSOR:
        status = STATUS_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE
    elif receipt.gate_status == cas_contract.GATE_STATUS_BLOCK:
        status = STATUS_BLOCKED
    else:
        status = STATUS_UNKNOWN
    fields: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "permission_state": PERMISSION_STATE_UNAUTHORIZED,
        "permission": False,
        "research_only": True,
        "source_freshness_binding_hash": freshness_binding_result.binding_hash,
        "source_adapter_hash": freshness_binding_result.source_adapter_hash,
        "source_position_derived_result_hash": (
            freshness_binding_result.source_position_derived_result_hash
        ),
        "source_derived_incumbent_snapshot_hash": (
            freshness_binding_result.derived_incumbent_snapshot_hash
        ),
        "freshness_result_fingerprint_sha256": fingerprint,
        "request_nonce_hash": request_nonce_hash,
        "intent_hash": intent.intent_hash,
        "receipt_hash": receipt.receipt_hash,
        "outcome": receipt.outcome,
        "gate_status": receipt.gate_status,
        "stream_id": returned_cursor.stream_id,
        "projection_preregistration_hash": (
            returned_cursor.projection_preregistration_hash
        ),
        "attestation_hash": receipt.attestation_hash,
        "expected_cursor_hash": receipt.expected_cursor_hash,
        "observed_cursor_hash": receipt.observed_cursor_hash,
        "returned_cursor_hash": receipt.returned_cursor_hash,
        "candidate_sequence": receipt.candidate_sequence,
        "observed_high_water_sequence": receipt.observed_high_water_sequence,
        "returned_high_water_sequence": receipt.returned_high_water_sequence,
        "returned_cursor_changed": receipt.returned_cursor_changed,
        "returned_cursor": returned_cursor,
        "source_binding_exactly_verified": True,
        "freshness_result_reconstructed_from_source_binding": True,
        "cas_intent_exactly_bound": True,
        "input_cursor_mutation_performed": False,
        "observed_cursor_provider_registered": False,
        "observed_cursor_source_truth_verified": False,
        "consume_once_verified": False,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_read_verified": False,
        "replay_registry_persistence_verified": False,
        "cursor_write_performed": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
    }
    binding_hash = _canonical_sha256(_binding_core(fields))
    if binding_hash is None:
        return None
    return V9PositionDerivedSnapshotReplayCursorCasBindingResultV1(
        **fields,
        binding_hash=binding_hash,
    )


def verify_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
    document: Any,
    freshness_binding_result: source_binding.V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
    freshness_binding_verification_context: Any,
    attestation: freshness_gate.IncumbentSnapshotSequenceAttestationV1,
    base_cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    *,
    expected_freshness_binding_hash: Any,
    request_nonce_hash: Any,
    expected_observed_cursor_hash: Any,
) -> bool:
    if not isinstance(
        document,
        V9PositionDerivedSnapshotReplayCursorCasBindingResultV1,
    ):
        return False
    rebuilt = evaluate_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
        freshness_binding_result,
        freshness_binding_verification_context,
        attestation,
        base_cursor,
        observed_cursor,
        expected_freshness_binding_hash=expected_freshness_binding_hash,
        request_nonce_hash=request_nonce_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
    )
    return rebuilt is not None and document == rebuilt


__all__ = [
    "CONTRACT_VERSION",
    "PERMISSION_STATE_UNAUTHORIZED",
    "STATUS_BLOCKED",
    "STATUS_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE",
    "STATUS_UNKNOWN",
    "V9PositionDerivedSnapshotReplayCursorCasBindingResultV1",
    "evaluate_v9_position_derived_snapshot_replay_cursor_cas_binding_v1",
    "verify_v9_position_derived_snapshot_replay_cursor_cas_binding_v1",
]
