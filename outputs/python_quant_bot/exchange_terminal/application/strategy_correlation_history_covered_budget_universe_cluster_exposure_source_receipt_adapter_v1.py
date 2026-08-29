"""Exact, in-memory adapter from ADR0367 to ADR0369.

The ADR0367 public document intentionally redacts raw symbols and cluster ids.
This adapter therefore verifies that document exactly, binds its hash evidence
back to the same verified ADR0365 projection context, and creates a short-lived
receipt.  It has no serializer, persistence, runtime registration, or authority
path.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_preflight,
)
from exchange_terminal.application.strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1 import (
    EXPECTED_PRODUCER_CONTRACT_VERSION,
    SOURCE_RECEIPT_VERSION,
    ClusterExposurePolicyV1,
    ClusterExposurePreflightResultV1,
    ClusterExposureProposalV1,
    ClusterExposureSourceReceiptV1,
    evaluate_cluster_exposure_preflight_v1,
)


ADAPTER_CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "cluster-exposure-source-receipt-adapter-v1"
)
STATIC_FINGERPRINT: Final = (
    "20260824-correlation-cluster-exposure-source-receipt-adapter-v1-"
    "exact-batch-projection-bind-ephemeral-permission-lock-1"
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,31}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")

_EXPECTED_AUTHORITY = {
    "batch_admission_allowed": False,
    "consumer_registration_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "effective_budget_activation_allowed": False,
    "http_registration_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "profitability_claim_allowed": False,
    "readonly_projection_adapter_activation_allowed": False,
    "runtime_activation_allowed": False,
    "writer_allowed": False,
    "research_evidence_only": True,
}

_EXPECTED_FACTS = {
    "batch_admission_allowed": False,
    "cluster_atomic_source_partition_verified": True,
    "correlated_proposals_counted_by_unique_cluster": True,
    "fresh_projected_budget_evidence_completed": False,
    "projection_exactly_verified": True,
    "raw_symbols_and_cluster_ids_redacted": True,
    "synthetic_only": True,
}


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _valid_proposed_symbols(value: object) -> bool:
    return (
        isinstance(value, list)
        and 1 <= len(value) <= batch_preflight.MAX_PROPOSAL_OCCURRENCES
        and all(
            isinstance(symbol, str) and _SYMBOL_RE.fullmatch(symbol)
            for symbol in value
        )
    )


def _extract_verified_partition(
    projection_preregistration: Mapping[str, Any],
    proposed_symbols: list[str],
    projection_verification_context: Mapping[str, Any],
) -> tuple[dict[str, str], list[tuple[str, list[str]]]] | None:
    structural_context = projection_verification_context.get(
        "structural_gate_verification_context"
    )
    if not isinstance(structural_context, Mapping):
        return None
    budget = structural_context.get("budget_cluster_preregistration")
    derivation = projection_preregistration.get("derivation")
    if not isinstance(budget, Mapping) or not isinstance(derivation, Mapping):
        return None

    expected_symbols = budget.get("expected_symbols")
    expected_clusters = budget.get("expected_clusters")
    projected_symbols = derivation.get("projected_symbols")
    excluded_symbols = derivation.get("excluded_symbols")
    if (
        not isinstance(expected_symbols, list)
        or not expected_symbols
        or len(expected_symbols) != len(set(expected_symbols))
        or not isinstance(expected_clusters, list)
        or not expected_clusters
        or not isinstance(projected_symbols, list)
        or len(projected_symbols) != len(set(projected_symbols))
        or not isinstance(excluded_symbols, list)
        or len(excluded_symbols) != len(set(excluded_symbols))
    ):
        return None

    source_set = set(expected_symbols)
    projected_set = set(projected_symbols)
    excluded_set = set(excluded_symbols)
    if projected_set.intersection(excluded_set) or projected_set.union(excluded_set) != source_set:
        return None

    symbol_to_cluster: dict[str, str] = {}
    ordered_clusters: list[tuple[str, list[str]]] = []
    seen_cluster_ids: set[str] = set()
    for cluster in expected_clusters:
        if not isinstance(cluster, Mapping) or set(cluster.keys()) != {
            "cluster_id",
            "members",
        }:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            not isinstance(cluster_id, str)
            or not _OPAQUE_ID_RE.fullmatch(cluster_id)
            or cluster_id in seen_cluster_ids
            or not isinstance(members, list)
            or not members
            or len(members) != len(set(members))
        ):
            return None
        if any(
            not isinstance(member, str)
            or not _SYMBOL_RE.fullmatch(member)
            or member not in source_set
            or member in symbol_to_cluster
            for member in members
        ):
            return None
        member_set = set(members)
        if not (
            member_set.issubset(projected_set)
            or member_set.issubset(excluded_set)
        ):
            return None
        seen_cluster_ids.add(cluster_id)
        ordered_clusters.append((cluster_id, list(members)))
        for member in members:
            symbol_to_cluster[member] = cluster_id

    if set(symbol_to_cluster) != source_set:
        return None
    if any(symbol not in projected_set for symbol in proposed_symbols):
        return None
    return symbol_to_cluster, ordered_clusters


def _document_bindings_hold(
    document: Mapping[str, Any],
    proposed_symbols: list[str],
    symbol_to_cluster: Mapping[str, str],
    ordered_clusters: list[tuple[str, list[str]]],
) -> bool:
    if (
        document.get("schema_version") != batch_preflight.PREFLIGHT_SCHEMA_VERSION
        or document.get("static_fingerprint") != batch_preflight.STATIC_FINGERPRINT
        or document.get("consumer_status") != batch_preflight.CONSUMER_STATUS
        or document.get("registered") is not False
        or document.get("status") != batch_preflight.PROJECTED_IMMATURE_STATUS
        or document.get("authority") != _EXPECTED_AUTHORITY
        or document.get("facts") != _EXPECTED_FACTS
    ):
        return False

    unique_symbols = _ordered_unique(proposed_symbols)
    proposed_cluster_ids = [
        cluster_id
        for cluster_id, members in ordered_clusters
        if set(members).intersection(unique_symbols)
    ]
    counts = document.get("ticket_summary")
    if not isinstance(counts, Mapping):
        return False
    expected_counts = {
        "proposal_occurrence_count": len(proposed_symbols),
        "unique_proposal_symbol_count": len(unique_symbols),
        "unique_projected_symbol_count": len(unique_symbols),
        "effective_projected_ticket_count": len(proposed_cluster_ids),
        "cluster_collapse_reduction_count": (
            len(unique_symbols) - len(proposed_cluster_ids)
        ),
        "excluded_symbol_count": 0,
        "unknown_symbol_count": 0,
    }
    if set(counts.keys()) != set(expected_counts):
        return False
    if any(
        not _is_plain_int(counts.get(key)) or counts.get(key) != value
        for key, value in expected_counts.items()
    ):
        return False

    evidence = document.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("unique_proposal_symbol_hashes") != [
        _text_digest(symbol) for symbol in unique_symbols
    ]:
        return False
    if evidence.get("projected_cluster_id_hashes") != [
        _text_digest(cluster_id) for cluster_id in proposed_cluster_ids
    ]:
        return False
    if evidence.get("excluded_cluster_id_hashes") != []:
        return False
    if evidence.get("unknown_proposal_symbol_hashes") != []:
        return False
    return all(symbol in symbol_to_cluster for symbol in unique_symbols)


def build_cluster_exposure_source_receipt_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposed_symbols: Any,
    *,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> ClusterExposureSourceReceiptV1 | None:
    """Build an ephemeral receipt only after exact upstream verification."""

    if (
        not isinstance(batch_preflight_document, Mapping)
        or not isinstance(projection_preregistration, Mapping)
        or not isinstance(projection_verification_context, Mapping)
        or not _valid_proposed_symbols(proposed_symbols)
        or not isinstance(expected_batch_preflight_hash, str)
        or not _HEX64_RE.fullmatch(expected_batch_preflight_hash)
    ):
        return None
    try:
        verified = batch_preflight.verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
            batch_preflight_document,
            projection_preregistration,
            proposed_symbols,
            expected_preflight_hash=expected_batch_preflight_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not verified:
        return None

    partition = _extract_verified_partition(
        projection_preregistration,
        proposed_symbols,
        projection_verification_context,
    )
    if partition is None:
        return None
    symbol_to_cluster, ordered_clusters = partition
    if not _document_bindings_hold(
        batch_preflight_document,
        proposed_symbols,
        symbol_to_cluster,
        ordered_clusters,
    ):
        return None

    unique_symbols = _ordered_unique(proposed_symbols)
    return ClusterExposureSourceReceiptV1(
        receipt_version=SOURCE_RECEIPT_VERSION,
        producer_contract_version=EXPECTED_PRODUCER_CONTRACT_VERSION,
        source_batch_fingerprint_sha256=expected_batch_preflight_hash,
        structurally_complete=True,
        permission=False,
        symbol_cluster_pairs=tuple(
            sorted((symbol, symbol_to_cluster[symbol]) for symbol in unique_symbols)
        ),
    )


def evaluate_cluster_exposure_from_verified_batch_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[ClusterExposureProposalV1, ...],
    policy: ClusterExposurePolicyV1,
    *,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> ClusterExposurePreflightResultV1 | None:
    """Bind exact proposal occurrences to ADR0367 and evaluate ADR0369."""

    if type(proposals) is not tuple or not proposals or any(
        not isinstance(proposal, ClusterExposureProposalV1)
        for proposal in proposals
    ):
        return None
    receipt = build_cluster_exposure_source_receipt_v1(
        batch_preflight_document,
        projection_preregistration,
        [proposal.symbol for proposal in proposals],
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if receipt is None:
        return None
    return evaluate_cluster_exposure_preflight_v1(
        source=receipt,
        policy=policy,
        proposals=proposals,
    )


__all__ = [
    "ADAPTER_CONTRACT_VERSION",
    "STATIC_FINGERPRINT",
    "build_cluster_exposure_source_receipt_v1",
    "evaluate_cluster_exposure_from_verified_batch_v1",
]
