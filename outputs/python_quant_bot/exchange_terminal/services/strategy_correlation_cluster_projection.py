from __future__ import annotations

from typing import Any

from .execution_authority import authority_violations
from .strategy_correlation_cluster_gate import (
    ABSOLUTE_PEARSON_THRESHOLD,
    LOOKBACK_OBSERVATIONS,
    MINIMUM_PAIR_OVERLAP,
)
from .strategy_correlation_return_replay import (
    REPLAY_SCOPE,
    REQUIRED_PRICE_ROWS,
    verify_replayed_correlation_cluster_gate,
)


CORRELATION_CLUSTER_PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-public-summary-v1"
)

_GAP_CATEGORY = {
    None: "NONE",
    "PREREGISTRATION": "PREREGISTRATION_NOT_VERIFIED",
    "COVERAGE": "SOURCE_OR_CELL_COVERAGE_GAP",
    "TOPOLOGY": "CROSS_CLUSTER_CORRELATION_GAP",
    "CLUSTER_VOTE": "INDEPENDENT_CLUSTER_VOTE_GAP",
}


def _empty_summary() -> dict[str, Any]:
    return {
        "schema_version": CORRELATION_CLUSTER_PUBLIC_SUMMARY_SCHEMA_VERSION,
        "status": "UNKNOWN",
        "source_status": "UNKNOWN",
        "gate_status": "UNKNOWN",
        "first_gap_category": "INPUT_INTEGRITY",
        "lane": "UNKNOWN",
        "cluster_count": None,
        "passing_cluster_count": None,
        "required_cluster_votes": None,
        "cross_cluster_conflict_count": None,
        "pair_count": None,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "cluster_vote_rule": "ALL_MEMBERS_PASS_ONE_VOTE_PER_CLUSTER",
        "replay_scope": REPLAY_SCOPE,
        "interpretation": "DESCRIPTIVE_CORRELATION_INDEPENDENCE_ONLY",
        "full_manifest_reverified": False,
        "preregistered_cutoff_bound": False,
        "formal_registry_bound": False,
        "current_report_schema_bound": False,
        "next_evidence_required": "FORMAL_PROTOCOL_BINDING_AND_NEW_REPORT_SCHEMA",
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_correlation_cluster_public_summary(document: Any) -> dict[str, Any]:
    verification = verify_replayed_correlation_cluster_gate(document)
    if verification["status"] != "PASS" or type(document) is not dict:
        return _empty_summary()
    gate = document["gate"]
    replay = document["matrix_replay"]
    preregistration = replay["preregistration"]
    first_tier = gate["first_blocking_tier"]
    if first_tier not in _GAP_CATEGORY:
        return _empty_summary()
    result = {
        "schema_version": CORRELATION_CLUSTER_PUBLIC_SUMMARY_SCHEMA_VERSION,
        "status": "DESCRIPTIVE_PASS" if gate["status"] == "PASS" else "DESCRIPTIVE_BLOCK",
        "source_status": "VERIFIED_LOCAL_REPLAY",
        "gate_status": gate["status"],
        "first_gap_category": _GAP_CATEGORY[first_tier],
        "lane": document["lane"],
        "cluster_count": len(preregistration["clusters"]),
        "passing_cluster_count": gate["passing_cluster_count"],
        "required_cluster_votes": gate["required_cluster_votes"],
        "cross_cluster_conflict_count": len(gate["cross_cluster_conflicts"]),
        "pair_count": replay["pair_count"],
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "cluster_vote_rule": "ALL_MEMBERS_PASS_ONE_VOTE_PER_CLUSTER",
        "replay_scope": REPLAY_SCOPE,
        "interpretation": "DESCRIPTIVE_CORRELATION_INDEPENDENCE_ONLY",
        "full_manifest_reverified": False,
        "preregistered_cutoff_bound": False,
        "formal_registry_bound": False,
        "current_report_schema_bound": False,
        "next_evidence_required": "FORMAL_PROTOCOL_BINDING_AND_NEW_REPORT_SCHEMA",
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if authority_violations(result):
        return _empty_summary()
    return result


__all__ = [
    "CORRELATION_CLUSTER_PUBLIC_SUMMARY_SCHEMA_VERSION",
    "build_correlation_cluster_public_summary",
]
