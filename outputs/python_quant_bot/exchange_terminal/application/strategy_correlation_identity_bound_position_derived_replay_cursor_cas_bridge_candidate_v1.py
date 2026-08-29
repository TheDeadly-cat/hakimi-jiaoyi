from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_freshness_replay_binding_v1
    as freshness_binding,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_replay_cursor_cas_binding_v1
    as cas_binding,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3
    as identity_post_merge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)


SCHEMA_VERSION = (
    "strategy-correlation-identity-bound-position-derived-replay-cursor-cas-"
    "bridge-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260825-strategy-correlation-identity-bound-position-derived-replay-"
    "cursor-cas-bridge-candidate-v1-synthetic-unmounted-permission-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_IDENTITY_BOUND_REPLAY_CURSOR_CAS_BRIDGE_CANDIDATE"
STATUS_UNCOMMITTED_CANDIDATE = (
    "OBSERVED_IDENTITY_BOUND_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE"
)
STATUS_BLOCKED = "BLOCKED_IDENTITY_BOUND_REPLAY_CURSOR_CAS"
STATUS_UNKNOWN = "UNKNOWN_IDENTITY_BOUND_REPLAY_CURSOR_CAS"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_CONTEXT_KEYS = {
    "batch_identity_gate_document",
    "identity_preregistration",
    "projection_preregistration",
    "proposals",
    "exposure_policy",
    "position_snapshot_claim",
    "expected_batch_identity_gate_hash",
    "expected_identity_preregistration_hash",
    "expected_position_snapshot_claim_hash",
    "expected_projection_preregistration_hash",
    "projection_verification_context",
}
_FRESHNESS_CONTEXT_KEYS = {
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


def _canonical_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None


def _digest(value: Any) -> str | None:
    encoded = _canonical_bytes(value)
    return hashlib.sha256(encoded).hexdigest() if encoded is not None else None


def _text_digest(value: Any) -> str | None:
    if type(value) is not str:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    payload = dict(core)
    digest = _digest(payload)
    if digest is None:
        return None
    payload[hash_field] = digest
    return payload


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _deduplicated_blockers(values: list[Any]) -> list[str]:
    blockers: list[str] = []
    for value in values:
        if isinstance(value, str) and value not in blockers:
            blockers.append(value)
    return blockers


def _authority_lock() -> dict[str, bool]:
    return {
        "atomic_storage_commit_verified": False,
        "consume_once_verified": False,
        "current_admission_allowed": False,
        "cursor_write_performed": False,
        "durable_commit_verified": False,
        "http_registration_allowed": False,
        "linearizable_read_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "replay_registry_persistence_verified": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "research_evidence_only": True,
    }


def _proposal_alignment(
    identity_result: Mapping[str, Any],
    identity_context: Mapping[str, Any],
    freshness_context: Mapping[str, Any],
) -> bool:
    identity_proposals = identity_context.get("proposals")
    canonical_proposals = freshness_context.get("proposals")
    exposure_binding = identity_result.get("exposure_binding")
    occurrences = (
        exposure_binding.get("ordered_exposure_occurrences")
        if isinstance(exposure_binding, Mapping)
        else None
    )
    if (
        type(identity_proposals) is not list
        or type(canonical_proposals) is not tuple
        or type(occurrences) is not list
        or len(identity_proposals) != len(canonical_proposals)
        or len(identity_proposals) != len(occurrences)
    ):
        return False
    for identity_proposal, canonical_proposal, occurrence in zip(
        identity_proposals,
        canonical_proposals,
        occurrences,
    ):
        if (
            type(identity_proposal) is not dict
            or type(occurrence) is not dict
            or type(canonical_proposal.proposal_id) is not str
            or type(canonical_proposal.symbol) is not str
            or type(canonical_proposal.requested_gross_bps) is not int
            or type(identity_proposal.get("proposal_id")) is not str
            or type(identity_proposal.get("symbol")) is not str
            or type(identity_proposal.get("venue_id")) is not str
            or type(identity_proposal.get("requested_gross_bps")) is not int
            or occurrence.get("proposal_id_sha256")
            != _text_digest(canonical_proposal.proposal_id)
            or occurrence.get("proposal_id_sha256")
            != _text_digest(identity_proposal.get("proposal_id", ""))
            or occurrence.get("budget_symbol_sha256")
            != _text_digest(canonical_proposal.symbol)
            or occurrence.get("requested_gross_bps")
            != canonical_proposal.requested_gross_bps
            or identity_proposal.get("requested_gross_bps")
            != canonical_proposal.requested_gross_bps
        ):
            return False
    return True


def evaluate_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
    identity_bound_result: Any,
    identity_bound_verification_context: Any,
    freshness_binding_result: Any,
    freshness_binding_verification_context: Any,
    replay_cursor_cas_binding_result: Any,
    attestation: Any,
    base_cursor: Any,
    observed_cursor: Any,
    *,
    expected_identity_bound_post_merge_hash: Any,
    expected_freshness_binding_hash: Any,
    expected_replay_cursor_cas_binding_hash: Any,
    request_nonce_hash: Any,
    expected_observed_cursor_hash: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(identity_bound_result, Mapping)
        or type(identity_bound_verification_context) is not dict
        or set(identity_bound_verification_context) != _IDENTITY_CONTEXT_KEYS
        or not isinstance(
            freshness_binding_result,
            freshness_binding.V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
        )
        or type(freshness_binding_verification_context) is not dict
        or set(freshness_binding_verification_context)
        != _FRESHNESS_CONTEXT_KEYS
        or not isinstance(
            replay_cursor_cas_binding_result,
            cas_binding.V9PositionDerivedSnapshotReplayCursorCasBindingResultV1,
        )
        or not isinstance(
            attestation,
            freshness_gate.IncumbentSnapshotSequenceAttestationV1,
        )
        or not isinstance(base_cursor, freshness_gate.IncumbentSnapshotReplayCursorV1)
        or not isinstance(
            observed_cursor,
            freshness_gate.IncumbentSnapshotReplayCursorV1,
        )
        or not all(
            _is_hash(value)
            for value in (
                expected_identity_bound_post_merge_hash,
                expected_freshness_binding_hash,
                expected_replay_cursor_cas_binding_hash,
                request_nonce_hash,
                expected_observed_cursor_hash,
            )
        )
        or identity_bound_result.get("identity_bound_post_merge_hash")
        != expected_identity_bound_post_merge_hash
        or freshness_binding_result.binding_hash
        != expected_freshness_binding_hash
        or replay_cursor_cas_binding_result.binding_hash
        != expected_replay_cursor_cas_binding_hash
    ):
        return None

    if not identity_post_merge.verify_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
        identity_bound_result,
        expected_identity_bound_post_merge_hash=(
            expected_identity_bound_post_merge_hash
        ),
        **identity_bound_verification_context,
    ):
        return None
    try:
        freshness_exact = freshness_binding.verify_v9_position_derived_snapshot_freshness_replay_binding_v1(
            freshness_binding_result,
            **deepcopy(freshness_binding_verification_context),
        )
    except (KeyError, TypeError, ValueError):
        freshness_exact = False
    if not freshness_exact or not cas_binding.verify_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
        replay_cursor_cas_binding_result,
        freshness_binding_result,
        deepcopy(freshness_binding_verification_context),
        attestation,
        base_cursor,
        observed_cursor,
        expected_freshness_binding_hash=expected_freshness_binding_hash,
        request_nonce_hash=request_nonce_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
    ):
        return None

    identity_source = identity_bound_result.get("source")
    identity_facts = identity_bound_result.get("facts")
    identity_risk = identity_bound_result.get("risk_summary")
    identity_exposure = identity_bound_result.get("exposure_binding")
    freshness_position_result = freshness_binding_verification_context.get(
        "position_derived_result"
    )
    freshness_batch = freshness_binding_verification_context.get(
        "batch_preflight_document"
    )
    adapter_result = freshness_binding_verification_context.get("adapter_result")
    if not all(
        isinstance(value, Mapping)
        for value in (
            identity_source,
            identity_facts,
            identity_risk,
            identity_exposure,
            freshness_batch,
        )
    ):
        return None
    if (
        identity_facts.get("position_derived_post_merge_exactly_verified")
        is not True
        or identity_source.get("position_derived_post_merge_result_hash")
        != freshness_binding_result.source_position_derived_result_hash
        or identity_source.get("position_derived_post_merge_result_hash")
        != replay_cursor_cas_binding_result.source_position_derived_result_hash
        or identity_source.get("derived_incumbent_snapshot_hash")
        != freshness_binding_result.derived_incumbent_snapshot_hash
        or identity_source.get("derived_incumbent_snapshot_hash")
        != replay_cursor_cas_binding_result.source_derived_incumbent_snapshot_hash
        or identity_source.get("position_snapshot_claim_hash")
        != freshness_binding_result.source_position_claim_hash
        or identity_source.get("position_snapshot_claim_hash")
        != adapter_result.position_claim.claim_hash
        or identity_bound_verification_context.get("position_snapshot_claim")
        != adapter_result.position_claim
        or identity_source.get("source_batch_preflight_hash")
        != freshness_batch.get("preflight_hash")
        or identity_source.get("projection_preregistration_hash")
        != freshness_binding_verification_context.get(
            "expected_projection_preregistration_hash"
        )
        or replay_cursor_cas_binding_result.projection_preregistration_hash
        != identity_source.get("projection_preregistration_hash")
        or identity_risk.get("proposed_total_gross_bps")
        != freshness_position_result.proposed_total_gross_bps
        or identity_exposure.get("requested_total_gross_bps")
        != freshness_position_result.proposed_total_gross_bps
        or freshness_binding_result.snapshot_sequence
        != adapter_result.snapshot_sequence
        or replay_cursor_cas_binding_result.candidate_sequence
        != freshness_binding_result.snapshot_sequence
        or not _proposal_alignment(
            identity_bound_result,
            identity_bound_verification_context,
            freshness_binding_verification_context,
        )
    ):
        return None

    if (
        replay_cursor_cas_binding_result.status
        == cas_binding.STATUS_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE
    ):
        status = STATUS_UNCOMMITTED_CANDIDATE
        gap = "RETURNED_CURSOR_NOT_PROVIDER_COMMITTED"
        maturity = "IDENTITY_AMOUNT_SNAPSHOT_SEQUENCE_CAS_BOUND_IN_MEMORY"
    elif replay_cursor_cas_binding_result.status == cas_binding.STATUS_BLOCKED:
        status = STATUS_BLOCKED
        gap = "REPLAY_CURSOR_CAS_BLOCKED"
        maturity = "BLOCKED_BY_REPLAY_OR_MONOTONICITY_CONTRACT"
    else:
        status = STATUS_UNKNOWN
        gap = "REPLAY_CURSOR_CAS_OUTCOME_UNKNOWN_OR_CONFLICT"
        maturity = "UNVERIFIED_REPLAY_CURSOR_TRANSITION"

    blockers = [
        "OBSERVED_CURSOR_PROVIDER_NOT_REGISTERED",
        "OBSERVED_CURSOR_SOURCE_TRUTH_NOT_VERIFIED",
        "ATOMIC_STORAGE_COMMIT_NOT_VERIFIED",
        "DURABLE_COMMIT_NOT_VERIFIED",
        "LINEARIZABLE_READ_NOT_VERIFIED",
        "REPLAY_REGISTRY_PERSISTENCE_NOT_VERIFIED",
        "IDENTITY_BOUND_CAS_BRIDGE_CANDIDATE_UNMOUNTED",
        "CURRENT_ADMISSION_NOT_ALLOWED",
        "PAPER_LIVE_UNAUTHORIZED",
    ]
    if status != STATUS_UNCOMMITTED_CANDIDATE:
        blockers.insert(0, f"CAS_OUTCOME_{replay_cursor_cas_binding_result.outcome}")

    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": status,
        "source": {
            "identity_bound_post_merge_hash": (
                expected_identity_bound_post_merge_hash
            ),
            "batch_identity_gate_hash": identity_source.get(
                "batch_identity_gate_hash"
            ),
            "exposure_binding_hash": identity_exposure.get(
                "exposure_binding_hash"
            ),
            "position_snapshot_claim_hash": identity_source.get(
                "position_snapshot_claim_hash"
            ),
            "position_derived_post_merge_result_hash": identity_source.get(
                "position_derived_post_merge_result_hash"
            ),
            "freshness_binding_hash": expected_freshness_binding_hash,
            "replay_cursor_cas_binding_hash": (
                expected_replay_cursor_cas_binding_hash
            ),
            "derived_incumbent_snapshot_hash": identity_source.get(
                "derived_incumbent_snapshot_hash"
            ),
            "attestation_hash": replay_cursor_cas_binding_result.attestation_hash,
            "observed_cursor_hash": (
                replay_cursor_cas_binding_result.observed_cursor_hash
            ),
            "returned_cursor_hash": (
                replay_cursor_cas_binding_result.returned_cursor_hash
            ),
            "request_nonce_hash": request_nonce_hash,
        },
        "decision_path": {
            "source": "ADR0486_AND_V9_FRESHNESS_CAS_EXACTLY_CROSS_BOUND",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "observations": {
            "proposal_occurrence_count": len(
                identity_exposure.get("ordered_exposure_occurrences", [])
            ),
            "requested_total_gross_bps": identity_exposure.get(
                "requested_total_gross_bps"
            ),
            "snapshot_sequence": freshness_binding_result.snapshot_sequence,
            "observed_high_water_sequence": (
                replay_cursor_cas_binding_result.observed_high_water_sequence
            ),
            "returned_high_water_sequence": (
                replay_cursor_cas_binding_result.returned_high_water_sequence
            ),
            "cas_outcome": replay_cursor_cas_binding_result.outcome,
            "returned_cursor_changed": (
                replay_cursor_cas_binding_result.returned_cursor_changed
            ),
        },
        "facts": {
            "identity_bound_post_merge_exactly_verified": True,
            "freshness_binding_exactly_verified": True,
            "replay_cursor_cas_binding_exactly_verified": True,
            "position_result_hash_bound_across_contracts": True,
            "incumbent_snapshot_hash_bound_across_contracts": True,
            "position_claim_hash_bound_across_contracts": True,
            "proposal_ids_symbols_amounts_bound_across_contracts": True,
            "snapshot_sequence_bound_across_contracts": True,
            "returned_cursor_is_in_memory_candidate_only": True,
            "observed_cursor_provider_registered": False,
            "observed_cursor_source_truth_verified": False,
            "consume_once_verified": False,
            "atomic_storage_commit_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_verified": False,
            "replay_registry_persistence_verified": False,
            "cursor_write_performed": False,
            "current_admission_allowed": False,
            "synthetic_only": True,
        },
        "blockers": _deduplicated_blockers(blockers),
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_bound_cas_bridge_hash")


def verify_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
    document: Any,
    identity_bound_result: Any,
    identity_bound_verification_context: Any,
    freshness_binding_result: Any,
    freshness_binding_verification_context: Any,
    replay_cursor_cas_binding_result: Any,
    attestation: Any,
    base_cursor: Any,
    observed_cursor: Any,
    *,
    expected_identity_bound_cas_bridge_hash: Any,
    expected_identity_bound_post_merge_hash: Any,
    expected_freshness_binding_hash: Any,
    expected_replay_cursor_cas_binding_hash: Any,
    request_nonce_hash: Any,
    expected_observed_cursor_hash: Any,
) -> bool:
    if not _is_hash(expected_identity_bound_cas_bridge_hash):
        return False
    expected = evaluate_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
        identity_bound_result,
        identity_bound_verification_context,
        freshness_binding_result,
        freshness_binding_verification_context,
        replay_cursor_cas_binding_result,
        attestation,
        base_cursor,
        observed_cursor,
        expected_identity_bound_post_merge_hash=(
            expected_identity_bound_post_merge_hash
        ),
        expected_freshness_binding_hash=expected_freshness_binding_hash,
        expected_replay_cursor_cas_binding_hash=(
            expected_replay_cursor_cas_binding_hash
        ),
        request_nonce_hash=request_nonce_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("identity_bound_cas_bridge_hash")
        == expected_identity_bound_cas_bridge_hash
        and document.get("identity_bound_cas_bridge_hash")
        == expected_identity_bound_cas_bridge_hash
        and dict(document) == expected
    )
