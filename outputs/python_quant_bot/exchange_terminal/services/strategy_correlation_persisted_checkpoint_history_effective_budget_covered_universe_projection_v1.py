from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_structural_coverage_crosswalk_gate_v1
    as structural_gate,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate,
)


DERIVATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-atomic-history-covered-budget-universe-"
    "projection-derivation-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-covered-universe-"
    "projection-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-history-effective-budget-covered-"
    "universe-projection-v1-synthetic-unmounted-fresh-evidence-lock-1"
)
PROJECTION_POLICY = (
    "PROJECT_ONLY_FULLY_HISTORY_COVERED_CLUSTERS_NO_IMPLICIT_INDEPENDENCE"
)
CLUSTER_EXCLUSION_POLICY = (
    "DROP_ENTIRE_CLUSTER_IF_ANY_MEMBER_LACKS_PERSISTED_HISTORY_COVERAGE"
)
STALE_EVIDENCE_POLICY = "REJECT_ALL_ORIGINAL_FULL_UNIVERSE_EVALUATION_ARTIFACTS"
PREREGISTERED_STATUS = (
    "PREREGISTERED_UNMOUNTED_COVERED_UNIVERSE_REQUIRES_FRESH_BUDGET_EVALUATION"
)
DERIVED_STATUS = "DERIVED_UNMOUNTED_CLUSTER_ATOMIC_PROJECTION"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_STRUCTURAL_CONTEXT_KEYS = {
    "crosswalk_preregistration",
    "provenance_preregistration",
    "history_cluster_preregistration",
    "budget_cluster_preregistration",
    "window_crosswalk",
    "expected_crosswalk_preregistration_hash",
    "expected_provenance_preregistration_hash",
    "provenance_preregistration_verification_context",
    "expected_history_cluster_preregistration_hash",
    "history_cluster_preregistration_verification_context",
    "expected_budget_cluster_preregistration_hash",
    "budget_cluster_preregistration_verification_context",
}
_REQUIRED_FRESH_ARTIFACTS = (
    "PROJECTED_MULTI_WINDOW_AUDITS_V1",
    "PROJECTED_MULTI_WINDOW_CLUSTER_GATE_V1",
    "PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_PREREGISTRATION_V1",
    "PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_EVALUATION_V1",
)
_BLOCKERS = (
    "FRESH_PROJECTED_MULTI_WINDOW_AUDITS_NOT_PROVIDED",
    "FRESH_PROJECTED_CLUSTER_GATE_NOT_PROVIDED",
    "FRESH_PROJECTED_EFFECTIVE_BUDGET_BINDING_NOT_PROVIDED",
    "WINDOW_SEMANTIC_IDENTITY_UNPROVEN",
    "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
    "READONLY_PROJECTION_ADAPTER_NOT_ELIGIBLE",
    "RUNTIME_CONSUMER_NOT_REGISTERED",
    "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
)


def _authority_lock() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "effective_budget_activation_allowed": False,
        "http_registration_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "readonly_projection_adapter_activation_allowed": False,
        "runtime_activation_allowed": False,
        "semantic_identity_equivalence_claim_allowed": False,
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


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    payload = dict(core)
    digest = _digest(payload)
    if digest is None:
        return None
    payload[hash_field] = digest
    return payload


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _valid_unique_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def derive_strategy_correlation_cluster_atomic_history_covered_budget_universe_projection_v1(
    budget_symbols: Any,
    budget_clusters: Any,
    history_covered_symbols: Any,
) -> dict[str, Any] | None:
    if not _valid_unique_string_list(budget_symbols):
        return None
    if not _valid_unique_string_list(history_covered_symbols):
        return None
    if not isinstance(budget_clusters, list) or not budget_clusters:
        return None

    budget_symbol_set = set(budget_symbols)
    history_symbol_set = set(history_covered_symbols)
    observed_members: set[str] = set()
    observed_cluster_ids: set[str] = set()
    normalized_clusters: list[dict[str, Any]] = []
    for cluster in budget_clusters:
        if not isinstance(cluster, Mapping):
            return None
        if set(cluster.keys()) != {"cluster_id", "members"}:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            not isinstance(cluster_id, str)
            or not cluster_id
            or cluster_id in observed_cluster_ids
            or not _valid_unique_string_list(members)
            or any(member not in budget_symbol_set for member in members)
            or observed_members.intersection(members)
        ):
            return None
        observed_cluster_ids.add(cluster_id)
        observed_members.update(members)
        normalized_clusters.append(
            {"cluster_id": cluster_id, "members": list(members)}
        )
    if observed_members != budget_symbol_set:
        return None

    retained_clusters: list[dict[str, Any]] = []
    excluded_cluster_ids: list[str] = []
    partially_covered_cluster_ids: list[str] = []
    fully_uncovered_cluster_ids: list[str] = []
    retained_symbol_set: set[str] = set()
    for cluster in normalized_clusters:
        covered_members = [
            member for member in cluster["members"] if member in history_symbol_set
        ]
        if len(covered_members) == len(cluster["members"]):
            retained_clusters.append(cluster)
            retained_symbol_set.update(cluster["members"])
            continue
        excluded_cluster_ids.append(cluster["cluster_id"])
        if covered_members:
            partially_covered_cluster_ids.append(cluster["cluster_id"])
        else:
            fully_uncovered_cluster_ids.append(cluster["cluster_id"])

    projected_symbols = [
        symbol for symbol in budget_symbols if symbol in retained_symbol_set
    ]
    excluded_symbols = [
        symbol for symbol in budget_symbols if symbol not in retained_symbol_set
    ]
    history_symbols_outside_budget = [
        symbol for symbol in history_covered_symbols if symbol not in budget_symbol_set
    ]
    core = {
        "schema_version": DERIVATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": DERIVED_STATUS,
        "projection_policy": PROJECTION_POLICY,
        "cluster_exclusion_policy": CLUSTER_EXCLUSION_POLICY,
        "projected_symbols": projected_symbols,
        "projected_clusters": retained_clusters,
        "excluded_symbols": excluded_symbols,
        "excluded_cluster_ids": excluded_cluster_ids,
        "partially_covered_cluster_ids": partially_covered_cluster_ids,
        "fully_uncovered_cluster_ids": fully_uncovered_cluster_ids,
        "history_symbols_outside_budget": history_symbols_outside_budget,
        "facts": {
            "cluster_atomic_projection": True,
            "every_projected_cluster_fully_history_covered": all(
                all(member in history_symbol_set for member in cluster["members"])
                for cluster in retained_clusters
            ),
            "partially_covered_clusters_fully_excluded": True,
            "projection_reduces_original_budget_universe": len(projected_symbols)
            < len(budget_symbols),
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }
    return _seal(core, "derivation_hash")


def _verify_structural_gate(
    document: Any,
    *,
    expected_gate_hash: Any,
    verification_context: Any,
) -> bool:
    if not _is_hash(expected_gate_hash):
        return False
    if not isinstance(verification_context, Mapping):
        return False
    if set(verification_context.keys()) != _STRUCTURAL_CONTEXT_KEYS:
        return False
    try:
        return bool(
            structural_gate.verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
                document,
                verification_context["crosswalk_preregistration"],
                verification_context["provenance_preregistration"],
                verification_context["history_cluster_preregistration"],
                verification_context["budget_cluster_preregistration"],
                verification_context["window_crosswalk"],
                expected_gate_hash=expected_gate_hash,
                expected_crosswalk_preregistration_hash=verification_context[
                    "expected_crosswalk_preregistration_hash"
                ],
                expected_provenance_preregistration_hash=verification_context[
                    "expected_provenance_preregistration_hash"
                ],
                provenance_preregistration_verification_context=verification_context[
                    "provenance_preregistration_verification_context"
                ],
                expected_history_cluster_preregistration_hash=verification_context[
                    "expected_history_cluster_preregistration_hash"
                ],
                history_cluster_preregistration_verification_context=verification_context[
                    "history_cluster_preregistration_verification_context"
                ],
                expected_budget_cluster_preregistration_hash=verification_context[
                    "expected_budget_cluster_preregistration_hash"
                ],
                budget_cluster_preregistration_verification_context=verification_context[
                    "budget_cluster_preregistration_verification_context"
                ],
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _source_bundle_from_context(
    verification_context: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    history = verification_context.get("history_cluster_preregistration")
    budget = verification_context.get("budget_cluster_preregistration")
    if not isinstance(history, Mapping) or not isinstance(budget, Mapping):
        return None
    return history, budget


def _projected_preregistration_is_exact(
    projected_preregistration: Any,
    derivation: Mapping[str, Any],
    budget_windows: Any,
) -> bool:
    if not isinstance(projected_preregistration, Mapping):
        return False
    if not _valid_unique_string_list(budget_windows):
        return False
    try:
        return bool(
            cluster_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                projected_preregistration,
                expected_symbols=derivation["projected_symbols"],
                expected_clusters=derivation["projected_clusters"],
                expected_windows=budget_windows,
                expected_preregistration_hash=projected_preregistration.get(
                    "preregistration_hash"
                ),
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _projection_core(
    structural_coverage_gate: Mapping[str, Any],
    structural_gate_verification_context: Mapping[str, Any],
    derivation: Mapping[str, Any],
    projected_cluster_preregistration: Mapping[str, Any],
) -> dict[str, Any]:
    history = structural_gate_verification_context[
        "history_cluster_preregistration"
    ]
    budget = structural_gate_verification_context[
        "budget_cluster_preregistration"
    ]
    return {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": PREREGISTERED_STATUS,
        "projection_policy": PROJECTION_POLICY,
        "cluster_exclusion_policy": CLUSTER_EXCLUSION_POLICY,
        "stale_evidence_policy": STALE_EVIDENCE_POLICY,
        "source": {
            "structural_coverage_gate_hash": structural_coverage_gate["gate_hash"],
            "structural_crosswalk_preregistration_hash": structural_gate_verification_context[
                "expected_crosswalk_preregistration_hash"
            ],
            "history_cluster_preregistration_hash": history["preregistration_hash"],
            "original_budget_cluster_preregistration_hash": budget[
                "preregistration_hash"
            ],
            "original_budget_symbol_order_hash": budget["symbol_order_hash"],
            "original_budget_cluster_partition_hash": budget[
                "cluster_partition_hash"
            ],
            "original_budget_window_order_hash": budget["window_order_hash"],
        },
        "derivation": dict(derivation),
        "projected_cluster_preregistration": dict(
            projected_cluster_preregistration
        ),
        "projected": {
            "cluster_preregistration_hash": projected_cluster_preregistration[
                "preregistration_hash"
            ],
            "symbol_order_hash": projected_cluster_preregistration[
                "symbol_order_hash"
            ],
            "cluster_partition_hash": projected_cluster_preregistration[
                "cluster_partition_hash"
            ],
            "window_order_hash": projected_cluster_preregistration[
                "window_order_hash"
            ],
        },
        "fresh_evidence_contract": {
            "required_artifacts_in_order": list(_REQUIRED_FRESH_ARTIFACTS),
            "original_full_universe_evidence_reuse_allowed": False,
            "projected_evaluation_completed": False,
            "readonly_projection_adapter_eligible": False,
        },
        "facts": {
            "all_projected_symbols_have_persisted_history_coverage": True,
            "cluster_atomic_projection_verified": True,
            "fresh_projected_budget_evidence_completed": False,
            "mounted": False,
            "original_full_universe_evidence_reuse_allowed": False,
            "projected_cluster_preregistration_exactly_verified": True,
            "semantic_study_identity_equivalence_verified": False,
            "source_structural_gate_exactly_verified": True,
            "synthetic_only": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": _authority_lock(),
    }


def build_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
    structural_coverage_gate: Any,
    *,
    expected_structural_coverage_gate_hash: Any,
    structural_gate_verification_context: Any,
) -> dict[str, Any] | None:
    if not _verify_structural_gate(
        structural_coverage_gate,
        expected_gate_hash=expected_structural_coverage_gate_hash,
        verification_context=structural_gate_verification_context,
    ):
        return None
    if structural_coverage_gate.get("status") != structural_gate.BLOCKED_UNIVERSE_STATUS:
        return None
    source_bundle = _source_bundle_from_context(structural_gate_verification_context)
    if source_bundle is None:
        return None
    history, budget = source_bundle
    history_symbols = history.get("expected_symbols")
    budget_symbols = budget.get("expected_symbols")
    budget_clusters = budget.get("expected_clusters")
    budget_windows = budget.get("expected_windows")
    derivation = derive_strategy_correlation_cluster_atomic_history_covered_budget_universe_projection_v1(
        budget_symbols,
        budget_clusters,
        history_symbols,
    )
    if derivation is None or not derivation.get("projected_symbols"):
        return None
    if derivation.get("excluded_symbols") != structural_coverage_gate.get(
        "coverage", {}
    ).get("budget_uncovered_symbols"):
        return None
    try:
        projected_preregistration = cluster_gate.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            derivation["projected_symbols"],
            derivation["projected_clusters"],
            budget_windows,
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not _projected_preregistration_is_exact(
        projected_preregistration,
        derivation,
        budget_windows,
    ):
        return None
    if projected_preregistration.get("preregistration_hash") == budget.get(
        "preregistration_hash"
    ):
        return None
    core = _projection_core(
        structural_coverage_gate,
        structural_gate_verification_context,
        derivation,
        projected_preregistration,
    )
    return _seal(core, "projection_preregistration_hash")


def verify_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
    document: Any,
    structural_coverage_gate: Any,
    *,
    expected_projection_preregistration_hash: Any,
    expected_structural_coverage_gate_hash: Any,
    structural_gate_verification_context: Any,
) -> bool:
    if not _is_hash(expected_projection_preregistration_hash):
        return False
    expected = build_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
        structural_coverage_gate,
        expected_structural_coverage_gate_hash=expected_structural_coverage_gate_hash,
        structural_gate_verification_context=structural_gate_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("projection_preregistration_hash")
        == expected_projection_preregistration_hash
        and document.get("projection_preregistration_hash")
        == expected_projection_preregistration_hash
        and dict(document) == expected
    )
