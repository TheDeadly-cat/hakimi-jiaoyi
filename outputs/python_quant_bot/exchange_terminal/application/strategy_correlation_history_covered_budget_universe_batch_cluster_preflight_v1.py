from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_covered_universe_projection_v1
    as covered_projection,
)


DERIVATION_SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-batch-cluster-ticket-"
    "derivation-v1"
)
PREFLIGHT_SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-batch-cluster-"
    "preflight-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-history-covered-budget-universe-batch-cluster-"
    "preflight-v1-synthetic-unmounted-hash-only-permission-lock-1"
)
DERIVED_STATUS = "DERIVED_CLUSTER_COLLAPSED_EFFECTIVE_TICKET_SUMMARY"
CONSUMER_STATUS = "UNMOUNTED_APPLICATION_BATCH_PREFLIGHT_CANDIDATE"
UNKNOWN_STATUS = "UNKNOWN_BATCH_CONTAINS_UNVERIFIED_SYMBOL"
EXCLUDED_STATUS = "BLOCKED_BATCH_CONTAINS_HISTORY_COVERAGE_EXCLUDED_SYMBOL"
PROJECTED_IMMATURE_STATUS = "BLOCKED_FRESH_PROJECTED_EVIDENCE_INCOMPLETE"
MAX_PROPOSAL_OCCURRENCES = 64

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_PROJECTION_CONTEXT_KEYS = {
    "structural_coverage_gate",
    "expected_structural_coverage_gate_hash",
    "structural_gate_verification_context",
}


def _authority_lock() -> dict[str, bool]:
    return {
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
    if encoded is None:
        return None
    return hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    payload = dict(core)
    digest = _digest(payload)
    if digest is None:
        return None
    payload[hash_field] = digest
    return payload


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _valid_symbols(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(
            isinstance(symbol, str) and _SYMBOL_RE.fullmatch(symbol) is not None
            for symbol in value
        )
    )


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
    proposed_symbols: Any,
    source_symbols: Any,
    source_clusters: Any,
    projected_symbols: Any,
    excluded_symbols: Any,
) -> dict[str, Any] | None:
    if (
        not _valid_symbols(proposed_symbols)
        or len(proposed_symbols) > MAX_PROPOSAL_OCCURRENCES
        or not _valid_symbols(source_symbols)
        or len(source_symbols) != len(set(source_symbols))
        or not _valid_symbols(projected_symbols, allow_empty=True)
        or len(projected_symbols) != len(set(projected_symbols))
        or not _valid_symbols(excluded_symbols, allow_empty=True)
        or len(excluded_symbols) != len(set(excluded_symbols))
        or not isinstance(source_clusters, list)
        or not source_clusters
    ):
        return None

    source_set = set(source_symbols)
    projected_set = set(projected_symbols)
    excluded_set = set(excluded_symbols)
    if (
        projected_set.intersection(excluded_set)
        or projected_set.union(excluded_set) != source_set
    ):
        return None

    symbol_to_cluster: dict[str, dict[str, Any]] = {}
    normalized_clusters: list[dict[str, Any]] = []
    cluster_ids: set[str] = set()
    for cluster in source_clusters:
        if not isinstance(cluster, Mapping):
            return None
        if set(cluster.keys()) != {"cluster_id", "members"}:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            not isinstance(cluster_id, str)
            or not cluster_id
            or cluster_id in cluster_ids
            or not _valid_symbols(members)
            or len(members) != len(set(members))
        ):
            return None
        member_set = set(members)
        if (
            not member_set.issubset(source_set)
            or any(member in symbol_to_cluster for member in members)
            or not (
                member_set.issubset(projected_set)
                or member_set.issubset(excluded_set)
            )
        ):
            return None
        cluster_ids.add(cluster_id)
        normalized = {"cluster_id": cluster_id, "members": list(members)}
        normalized_clusters.append(normalized)
        for member in members:
            symbol_to_cluster[member] = normalized
    if set(symbol_to_cluster) != source_set:
        return None

    unique_proposals = _ordered_unique(proposed_symbols)
    projected_proposals = [
        symbol for symbol in unique_proposals if symbol in projected_set
    ]
    excluded_proposals = [
        symbol for symbol in unique_proposals if symbol in excluded_set
    ]
    unknown_proposals = [
        symbol for symbol in unique_proposals if symbol not in source_set
    ]

    proposed_projected_cluster_ids: list[str] = []
    proposed_excluded_cluster_ids: list[str] = []
    for cluster in normalized_clusters:
        cluster_id = cluster["cluster_id"]
        members = set(cluster["members"])
        if members.intersection(projected_proposals):
            proposed_projected_cluster_ids.append(cluster_id)
        if members.intersection(excluded_proposals):
            proposed_excluded_cluster_ids.append(cluster_id)

    naive_count = len(projected_proposals)
    effective_count = len(proposed_projected_cluster_ids)
    core = {
        "schema_version": DERIVATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": DERIVED_STATUS,
        "proposal_occurrence_symbol_hashes": [
            _text_digest(symbol) for symbol in proposed_symbols
        ],
        "unique_proposal_symbol_hashes": [
            _text_digest(symbol) for symbol in unique_proposals
        ],
        "projected_proposal_symbol_hashes": [
            _text_digest(symbol) for symbol in projected_proposals
        ],
        "excluded_proposal_symbol_hashes": [
            _text_digest(symbol) for symbol in excluded_proposals
        ],
        "unknown_proposal_symbol_hashes": [
            _text_digest(symbol) for symbol in unknown_proposals
        ],
        "projected_cluster_id_hashes": [
            _text_digest(cluster_id) for cluster_id in proposed_projected_cluster_ids
        ],
        "excluded_cluster_id_hashes": [
            _text_digest(cluster_id) for cluster_id in proposed_excluded_cluster_ids
        ],
        "counts": {
            "proposal_occurrence_count": len(proposed_symbols),
            "unique_proposal_symbol_count": len(unique_proposals),
            "unique_projected_symbol_count": naive_count,
            "effective_projected_ticket_count": effective_count,
            "cluster_collapse_reduction_count": naive_count - effective_count,
            "excluded_symbol_count": len(excluded_proposals),
            "unknown_symbol_count": len(unknown_proposals),
        },
        "facts": {
            "cluster_atomic_source_partition_verified": True,
            "correlated_proposals_collapsed_by_source_cluster": True,
            "duplicate_proposals_do_not_increase_effective_ticket_count": True,
            "raw_symbols_and_cluster_ids_redacted": True,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "derivation_hash")


def _verify_projection(
    document: Any,
    *,
    expected_projection_hash: Any,
    verification_context: Any,
) -> bool:
    if not _is_hash(expected_projection_hash):
        return False
    if not isinstance(verification_context, Mapping):
        return False
    if set(verification_context.keys()) != _PROJECTION_CONTEXT_KEYS:
        return False
    try:
        return bool(
            covered_projection.verify_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
                document,
                verification_context["structural_coverage_gate"],
                expected_projection_preregistration_hash=expected_projection_hash,
                expected_structural_coverage_gate_hash=verification_context[
                    "expected_structural_coverage_gate_hash"
                ],
                structural_gate_verification_context=verification_context[
                    "structural_gate_verification_context"
                ],
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _source_budget(
    verification_context: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    structural_context = verification_context.get(
        "structural_gate_verification_context"
    )
    if not isinstance(structural_context, Mapping):
        return None
    budget = structural_context.get("budget_cluster_preregistration")
    return budget if isinstance(budget, Mapping) else None


def _decision(derivation: Mapping[str, Any]) -> tuple[str, str, str, list[str]]:
    counts = derivation.get("counts")
    if not isinstance(counts, Mapping):
        raise ValueError("invalid derivation counts")
    if counts.get("unknown_symbol_count", 0) > 0:
        return (
            UNKNOWN_STATUS,
            "BATCH_CONTAINS_SYMBOL_OUTSIDE_VERIFIED_BUDGET_UNIVERSE",
            "UNVERIFIED_BATCH_MEMBERSHIP",
            [
                "BATCH_CONTAINS_UNVERIFIED_SYMBOL",
                "BATCH_ADMISSION_NOT_ALLOWED",
            ],
        )
    if counts.get("excluded_symbol_count", 0) > 0:
        return (
            EXCLUDED_STATUS,
            "BATCH_CONTAINS_CLUSTER_ATOMIC_HISTORY_COVERAGE_EXCLUSION",
            "EXCLUDED_BY_PREREGISTERED_PROJECTION_POLICY",
            [
                "BATCH_CONTAINS_HISTORY_COVERAGE_EXCLUDED_SYMBOL",
                "EXCLUDED_SOURCE_CLUSTER_NOT_ELIGIBLE_FOR_PROJECTION",
                "BATCH_ADMISSION_NOT_ALLOWED",
            ],
        )
    return (
        PROJECTED_IMMATURE_STATUS,
        "FRESH_PROJECTED_BUDGET_EVIDENCE_INCOMPLETE",
        "PROJECTED_UNIVERSE_PREREGISTERED_ONLY",
        [
            "FRESH_PROJECTED_MULTI_WINDOW_AUDITS_NOT_PROVIDED",
            "FRESH_PROJECTED_CLUSTER_GATE_NOT_PROVIDED",
            "FRESH_PROJECTED_EFFECTIVE_BUDGET_BINDING_NOT_PROVIDED",
            "BATCH_ADMISSION_NOT_ALLOWED",
        ],
    )


def evaluate_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
    projection_preregistration: Any,
    proposed_symbols: Any,
    *,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    if not _verify_projection(
        projection_preregistration,
        expected_projection_hash=expected_projection_preregistration_hash,
        verification_context=projection_verification_context,
    ):
        return None
    budget = _source_budget(projection_verification_context)
    derivation_source = projection_preregistration.get("derivation")
    if budget is None or not isinstance(derivation_source, Mapping):
        return None
    derivation = derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
        proposed_symbols,
        budget.get("expected_symbols"),
        budget.get("expected_clusters"),
        derivation_source.get("projected_symbols"),
        derivation_source.get("excluded_symbols"),
    )
    if derivation is None:
        return None
    try:
        status, gap, maturity, blockers = _decision(derivation)
    except (TypeError, ValueError):
        return None
    core = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": status,
        "source": {
            "projection_preregistration_hash": projection_preregistration[
                "projection_preregistration_hash"
            ],
            "batch_derivation_hash": derivation["derivation_hash"],
        },
        "decision_path": {
            "source": "ADR0365_PROJECTION_EXACTLY_VERIFIED",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "ticket_summary": dict(derivation["counts"]),
        "evidence": {
            "unique_proposal_symbol_hashes": list(
                derivation["unique_proposal_symbol_hashes"]
            ),
            "projected_cluster_id_hashes": list(
                derivation["projected_cluster_id_hashes"]
            ),
            "excluded_cluster_id_hashes": list(
                derivation["excluded_cluster_id_hashes"]
            ),
            "unknown_proposal_symbol_hashes": list(
                derivation["unknown_proposal_symbol_hashes"]
            ),
        },
        "facts": {
            "batch_admission_allowed": False,
            "cluster_atomic_source_partition_verified": True,
            "correlated_proposals_counted_by_unique_cluster": True,
            "fresh_projected_budget_evidence_completed": False,
            "projection_exactly_verified": True,
            "raw_symbols_and_cluster_ids_redacted": True,
            "synthetic_only": True,
        },
        "blockers": blockers
        + [
            "RUNTIME_CONSUMER_NOT_REGISTERED",
            "PAPER_LIVE_UNAUTHORIZED",
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "preflight_hash")


def verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
    document: Any,
    projection_preregistration: Any,
    proposed_symbols: Any,
    *,
    expected_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_preflight_hash):
        return False
    expected = evaluate_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
        projection_preregistration,
        proposed_symbols,
        expected_projection_preregistration_hash=expected_projection_preregistration_hash,
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("preflight_hash") == expected_preflight_hash
        and document.get("preflight_hash") == expected_preflight_hash
        and dict(document) == expected
    )
