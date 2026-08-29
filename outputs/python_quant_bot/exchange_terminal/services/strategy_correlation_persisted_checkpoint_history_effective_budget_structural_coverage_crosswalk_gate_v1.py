from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1
    as provenance_binding,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-structural-coverage-"
    "crosswalk-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-structural-coverage-"
    "crosswalk-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-history-effective-budget-structural-"
    "coverage-crosswalk-gate-v1-synthetic-unmounted-authority-lock-1"
)
CROSSWALK_RELATIONSHIP = "ORDER_ONLY_ALIAS_CANDIDATE_SEMANTICS_UNPROVEN"
CROSSWALK_POLICY = (
    "EVERY_BUDGET_SYMBOL_REQUIRES_PERSISTED_HISTORY_COVERAGE_NO_IMPLICIT_INDEPENDENCE"
)
PREREGISTERED_STATUS = "PREREGISTERED_UNMOUNTED_STRUCTURAL_COVERAGE_CROSSWALK"
BLOCKED_UNIVERSE_STATUS = "BLOCKED_BUDGET_UNIVERSE_NOT_FULLY_HISTORY_COVERED"
BLOCKED_POLICY_STATUS = "BLOCKED_SOURCE_POLICY_PROFILE_MISMATCH"
BLOCKED_CLUSTER_STATUS = "BLOCKED_SHARED_CLUSTER_PROJECTION_MISMATCH"
BLOCKED_WINDOW_STATUS = "BLOCKED_WINDOW_SEMANTIC_IDENTITY_UNPROVEN"
STRUCTURAL_ONLY_STATUS = "STRUCTURAL_COVERAGE_COMPATIBLE_SEMANTIC_EQUIVALENCE_UNPROVEN"
UNKNOWN_STATUS = "UNKNOWN"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_CONTEXT_KEYS = {
    "history_coverage_registration",
    "history_coverage_registration_receipt",
    "uncertainty_budget_binding_preregistration",
    "budget_binding_preregistration_verification_context",
}
_CLUSTER_CONTEXT_KEYS = {"expected_symbols", "expected_clusters", "expected_windows"}
_POLICY_PROFILE_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "gate_contract_hash",
    "uncertainty_policy_hash",
    "upstream_uncertainty_audit_source_sha256",
    "activation_sequence",
    "parameters",
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


def _verify_provenance_preregistration(
    document: Any,
    *,
    expected_hash: Any,
    verification_context: Any,
) -> bool:
    if not isinstance(verification_context, Mapping):
        return False
    if set(verification_context.keys()) != _SOURCE_CONTEXT_KEYS:
        return False
    if not _is_hash(expected_hash):
        return False
    try:
        return bool(
            provenance_binding.verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
                document,
                verification_context["history_coverage_registration"],
                verification_context["history_coverage_registration_receipt"],
                verification_context["uncertainty_budget_binding_preregistration"],
                expected_preregistration_hash=expected_hash,
                budget_binding_preregistration_verification_context=verification_context[
                    "budget_binding_preregistration_verification_context"
                ],
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_cluster_preregistration(
    document: Any,
    *,
    expected_hash: Any,
    verification_context: Any,
) -> bool:
    if not isinstance(verification_context, Mapping):
        return False
    if set(verification_context.keys()) != _CLUSTER_CONTEXT_KEYS:
        return False
    if not _is_hash(expected_hash):
        return False
    try:
        return bool(
            cluster_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                document,
                expected_symbols=verification_context["expected_symbols"],
                expected_clusters=verification_context["expected_clusters"],
                expected_windows=verification_context["expected_windows"],
                expected_preregistration_hash=expected_hash,
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_source_bundle(
    provenance_preregistration: Any,
    history_cluster_preregistration: Any,
    budget_cluster_preregistration: Any,
    *,
    expected_provenance_preregistration_hash: Any,
    provenance_preregistration_verification_context: Any,
    expected_history_cluster_preregistration_hash: Any,
    history_cluster_preregistration_verification_context: Any,
    expected_budget_cluster_preregistration_hash: Any,
    budget_cluster_preregistration_verification_context: Any,
) -> bool:
    if not _verify_provenance_preregistration(
        provenance_preregistration,
        expected_hash=expected_provenance_preregistration_hash,
        verification_context=provenance_preregistration_verification_context,
    ):
        return False
    if not _verify_cluster_preregistration(
        history_cluster_preregistration,
        expected_hash=expected_history_cluster_preregistration_hash,
        verification_context=history_cluster_preregistration_verification_context,
    ):
        return False
    if not _verify_cluster_preregistration(
        budget_cluster_preregistration,
        expected_hash=expected_budget_cluster_preregistration_hash,
        verification_context=budget_cluster_preregistration_verification_context,
    ):
        return False
    if not all(
        isinstance(document, Mapping)
        for document in (
            provenance_preregistration,
            history_cluster_preregistration,
            budget_cluster_preregistration,
        )
    ):
        return False
    if provenance_preregistration.get("history_window_order_hash") != (
        history_cluster_preregistration.get("window_order_hash")
    ):
        return False
    if provenance_preregistration.get("budget_window_order_hash") != (
        budget_cluster_preregistration.get("window_order_hash")
    ):
        return False
    if provenance_preregistration.get("budget_symbol_order_hash") != (
        budget_cluster_preregistration.get("symbol_order_hash")
    ):
        return False
    if provenance_preregistration.get("budget_cluster_partition_hash") != (
        budget_cluster_preregistration.get("cluster_partition_hash")
    ):
        return False
    return True


def _policy_profile(document: Mapping[str, Any]) -> dict[str, Any]:
    return {field: document.get(field) for field in _POLICY_PROFILE_FIELDS}


def _project_partition(clusters: Any, shared_symbols: list[str]) -> list[list[str]] | None:
    if not isinstance(clusters, list):
        return None
    shared = set(shared_symbols)
    projected: list[list[str]] = []
    observed: set[str] = set()
    for cluster in clusters:
        if not isinstance(cluster, Mapping) or set(cluster.keys()) != {"cluster_id", "members"}:
            return None
        members = cluster.get("members")
        if not isinstance(members, list) or any(not isinstance(member, str) for member in members):
            return None
        selected = sorted(member for member in members if member in shared)
        if selected:
            if observed.intersection(selected):
                return None
            observed.update(selected)
            projected.append(selected)
    if observed != shared:
        return None
    return sorted(projected)


def _analyze_sources(
    history_cluster_preregistration: Mapping[str, Any],
    budget_cluster_preregistration: Mapping[str, Any],
) -> dict[str, Any] | None:
    history_symbols = history_cluster_preregistration.get("expected_symbols")
    budget_symbols = budget_cluster_preregistration.get("expected_symbols")
    history_windows = history_cluster_preregistration.get("expected_windows")
    budget_windows = budget_cluster_preregistration.get("expected_windows")
    if not all(isinstance(value, list) for value in (history_symbols, budget_symbols, history_windows, budget_windows)):
        return None
    if any(not isinstance(item, str) for sequence in (history_symbols, budget_symbols, history_windows, budget_windows) for item in sequence):
        return None
    if any(len(sequence) != len(set(sequence)) for sequence in (history_symbols, budget_symbols, history_windows, budget_windows)):
        return None
    history_symbol_set = set(history_symbols)
    budget_symbol_set = set(budget_symbols)
    shared_symbols = [symbol for symbol in budget_symbols if symbol in history_symbol_set]
    uncovered_budget_symbols = [
        symbol for symbol in budget_symbols if symbol not in history_symbol_set
    ]
    history_only_symbols = [
        symbol for symbol in history_symbols if symbol not in budget_symbol_set
    ]
    history_projection = _project_partition(
        history_cluster_preregistration.get("expected_clusters"), shared_symbols
    )
    budget_projection = _project_partition(
        budget_cluster_preregistration.get("expected_clusters"), shared_symbols
    )
    if history_projection is None or budget_projection is None:
        return None
    history_blockers = history_cluster_preregistration.get("blockers")
    budget_blockers = budget_cluster_preregistration.get("blockers")
    if not isinstance(history_blockers, list) or not isinstance(budget_blockers, list):
        return None
    history_policy = _policy_profile(history_cluster_preregistration)
    budget_policy = _policy_profile(budget_cluster_preregistration)
    policy_profile_hash = _digest(history_policy) if history_policy == budget_policy else None
    return {
        "policy_profile_match": history_policy == budget_policy,
        "shared_policy_profile_hash": policy_profile_hash,
        "all_budget_symbols_history_covered": not uncovered_budget_symbols,
        "budget_uncovered_symbols": uncovered_budget_symbols,
        "history_only_symbols": history_only_symbols,
        "shared_symbols": shared_symbols,
        "symbol_order_identity_equal": history_symbols == budget_symbols,
        "history_symbol_universe_is_budget_subset": history_symbol_set.issubset(
            budget_symbol_set
        ),
        "full_cluster_partition_identity_equal": history_cluster_preregistration.get(
            "cluster_partition_hash"
        )
        == budget_cluster_preregistration.get("cluster_partition_hash"),
        "shared_symbol_cluster_projection_equal": history_projection == budget_projection,
        "history_shared_cluster_projection": history_projection,
        "budget_shared_cluster_projection": budget_projection,
        "window_count_equal": len(history_windows) == len(budget_windows),
        "window_order_identity_equal": history_windows == budget_windows,
        "window_label_issuer_binding_verified": (
            "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN" not in history_blockers
            and "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN" not in budget_blockers
        ),
        "semantic_study_identity_equivalence_verified": False,
    }


def _normalize_crosswalk(
    value: Any,
    history_windows: list[str],
    budget_windows: list[str],
) -> list[dict[str, str]] | None:
    if not isinstance(value, list) or len(value) != len(history_windows):
        return None
    if len(history_windows) != len(budget_windows):
        return None
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            return None
        if set(item.keys()) != {
            "history_window_id",
            "budget_window_id",
            "relationship",
        }:
            return None
        expected = {
            "history_window_id": history_windows[index],
            "budget_window_id": budget_windows[index],
            "relationship": CROSSWALK_RELATIONSHIP,
        }
        if dict(item) != expected:
            return None
        normalized.append(expected)
    return normalized


def _dynamic_blockers(analysis: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if analysis.get("policy_profile_match") is not True:
        blockers.append("SOURCE_POLICY_PROFILE_MISMATCH")
    if analysis.get("all_budget_symbols_history_covered") is not True:
        blockers.append("BUDGET_SYMBOLS_MISSING_PERSISTED_HISTORY_COVERAGE")
    if analysis.get("history_only_symbols"):
        blockers.append("HISTORY_SYMBOLS_OUTSIDE_BUDGET_UNIVERSE")
    if analysis.get("shared_symbol_cluster_projection_equal") is not True:
        blockers.append("SHARED_SYMBOL_CLUSTER_PROJECTION_DIFFERS")
    if analysis.get("full_cluster_partition_identity_equal") is not True:
        blockers.append("FULL_CLUSTER_PARTITION_IDENTITY_DIFFERS")
    if analysis.get("window_order_identity_equal") is not True:
        blockers.append("WINDOW_ORDER_IDENTITY_DIFFERS")
    if analysis.get("window_label_issuer_binding_verified") is not True:
        blockers.append("WINDOW_LABEL_ISSUER_BINDING_UNPROVEN")
    blockers.extend(
        [
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
            "RUNTIME_CONSUMER_NOT_REGISTERED",
        ]
    )
    return blockers


def _preregistration_core(
    provenance_preregistration: Mapping[str, Any],
    history_cluster_preregistration: Mapping[str, Any],
    budget_cluster_preregistration: Mapping[str, Any],
    crosswalk: list[dict[str, str]],
    analysis: Mapping[str, Any],
) -> dict[str, Any] | None:
    crosswalk_hash = _digest(crosswalk)
    if crosswalk_hash is None:
        return None
    return {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": PREREGISTERED_STATUS,
        "crosswalk_policy": CROSSWALK_POLICY,
        "window_crosswalk": crosswalk,
        "window_crosswalk_hash": crosswalk_hash,
        "source": {
            "provenance_binding_preregistration_hash": provenance_preregistration[
                "preregistration_hash"
            ],
            "history_cluster_preregistration_hash": history_cluster_preregistration[
                "preregistration_hash"
            ],
            "budget_cluster_preregistration_hash": budget_cluster_preregistration[
                "preregistration_hash"
            ],
            "history_window_order_hash": history_cluster_preregistration[
                "window_order_hash"
            ],
            "budget_window_order_hash": budget_cluster_preregistration[
                "window_order_hash"
            ],
            "history_symbol_order_hash": history_cluster_preregistration[
                "symbol_order_hash"
            ],
            "budget_symbol_order_hash": budget_cluster_preregistration[
                "symbol_order_hash"
            ],
            "history_cluster_partition_hash": history_cluster_preregistration[
                "cluster_partition_hash"
            ],
            "budget_cluster_partition_hash": budget_cluster_preregistration[
                "cluster_partition_hash"
            ],
        },
        "expected_gap": {
            "budget_uncovered_symbols": list(analysis["budget_uncovered_symbols"]),
            "history_only_symbols": list(analysis["history_only_symbols"]),
            "shared_symbols": list(analysis["shared_symbols"]),
        },
        "facts": {
            "all_budget_symbols_history_covered": analysis[
                "all_budget_symbols_history_covered"
            ],
            "full_cluster_partition_identity_equal": analysis[
                "full_cluster_partition_identity_equal"
            ],
            "policy_profile_match": analysis["policy_profile_match"],
            "semantic_study_identity_equivalence_verified": False,
            "shared_symbol_cluster_projection_equal": analysis[
                "shared_symbol_cluster_projection_equal"
            ],
            "source_preregistrations_exactly_verified": True,
            "synthetic_only": True,
            "window_count_equal": analysis["window_count_equal"],
            "window_label_issuer_binding_verified": analysis[
                "window_label_issuer_binding_verified"
            ],
            "window_order_identity_equal": analysis["window_order_identity_equal"],
        },
        "blockers": _dynamic_blockers(analysis),
        "authority": _authority_lock(),
    }


def build_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
    provenance_preregistration: Any,
    history_cluster_preregistration: Any,
    budget_cluster_preregistration: Any,
    window_crosswalk: Any,
    *,
    expected_provenance_preregistration_hash: Any,
    provenance_preregistration_verification_context: Any,
    expected_history_cluster_preregistration_hash: Any,
    history_cluster_preregistration_verification_context: Any,
    expected_budget_cluster_preregistration_hash: Any,
    budget_cluster_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if not _verify_source_bundle(
        provenance_preregistration,
        history_cluster_preregistration,
        budget_cluster_preregistration,
        expected_provenance_preregistration_hash=expected_provenance_preregistration_hash,
        provenance_preregistration_verification_context=provenance_preregistration_verification_context,
        expected_history_cluster_preregistration_hash=expected_history_cluster_preregistration_hash,
        history_cluster_preregistration_verification_context=history_cluster_preregistration_verification_context,
        expected_budget_cluster_preregistration_hash=expected_budget_cluster_preregistration_hash,
        budget_cluster_preregistration_verification_context=budget_cluster_preregistration_verification_context,
    ):
        return None
    history_windows = history_cluster_preregistration.get("expected_windows")
    budget_windows = budget_cluster_preregistration.get("expected_windows")
    if not isinstance(history_windows, list) or not isinstance(budget_windows, list):
        return None
    normalized_crosswalk = _normalize_crosswalk(
        window_crosswalk, history_windows, budget_windows
    )
    if normalized_crosswalk is None:
        return None
    analysis = _analyze_sources(
        history_cluster_preregistration, budget_cluster_preregistration
    )
    if analysis is None:
        return None
    core = _preregistration_core(
        provenance_preregistration,
        history_cluster_preregistration,
        budget_cluster_preregistration,
        normalized_crosswalk,
        analysis,
    )
    return None if core is None else _seal(core, "preregistration_hash")


def verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
    document: Any,
    provenance_preregistration: Any,
    history_cluster_preregistration: Any,
    budget_cluster_preregistration: Any,
    window_crosswalk: Any,
    *,
    expected_crosswalk_preregistration_hash: Any,
    expected_provenance_preregistration_hash: Any,
    provenance_preregistration_verification_context: Any,
    expected_history_cluster_preregistration_hash: Any,
    history_cluster_preregistration_verification_context: Any,
    expected_budget_cluster_preregistration_hash: Any,
    budget_cluster_preregistration_verification_context: Any,
) -> bool:
    if not _is_hash(expected_crosswalk_preregistration_hash):
        return False
    expected = build_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
        provenance_preregistration,
        history_cluster_preregistration,
        budget_cluster_preregistration,
        window_crosswalk,
        expected_provenance_preregistration_hash=expected_provenance_preregistration_hash,
        provenance_preregistration_verification_context=provenance_preregistration_verification_context,
        expected_history_cluster_preregistration_hash=expected_history_cluster_preregistration_hash,
        history_cluster_preregistration_verification_context=history_cluster_preregistration_verification_context,
        expected_budget_cluster_preregistration_hash=expected_budget_cluster_preregistration_hash,
        budget_cluster_preregistration_verification_context=budget_cluster_preregistration_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("preregistration_hash") == expected_crosswalk_preregistration_hash
        and document.get("preregistration_hash") == expected_crosswalk_preregistration_hash
        and dict(document) == expected
    )


def _gate_status(analysis: Mapping[str, Any]) -> str:
    if analysis.get("policy_profile_match") is not True:
        return BLOCKED_POLICY_STATUS
    if analysis.get("all_budget_symbols_history_covered") is not True:
        return BLOCKED_UNIVERSE_STATUS
    if analysis.get("shared_symbol_cluster_projection_equal") is not True:
        return BLOCKED_CLUSTER_STATUS
    if (
        analysis.get("window_order_identity_equal") is not True
        or analysis.get("window_label_issuer_binding_verified") is not True
    ):
        return BLOCKED_WINDOW_STATUS
    return STRUCTURAL_ONLY_STATUS


def _unknown_gate() -> dict[str, Any]:
    core = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason_code": "SOURCE_OR_CROSSWALK_VERIFICATION_FAILED",
        "facts": {
            "all_budget_symbols_history_covered": False,
            "semantic_study_identity_equivalence_verified": False,
            "source_preregistrations_exactly_verified": False,
            "synthetic_only": True,
        },
        "blockers": [
            "SOURCE_OR_CROSSWALK_VERIFICATION_FAILED",
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
        ],
        "authority": _authority_lock(),
    }
    sealed = _seal(core, "gate_hash")
    if sealed is None:  # pragma: no cover - constant-only payload.
        raise RuntimeError("constant gate payload is not serializable")
    return sealed


def evaluate_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
    crosswalk_preregistration: Any,
    provenance_preregistration: Any,
    history_cluster_preregistration: Any,
    budget_cluster_preregistration: Any,
    window_crosswalk: Any,
    *,
    expected_crosswalk_preregistration_hash: Any,
    expected_provenance_preregistration_hash: Any,
    provenance_preregistration_verification_context: Any,
    expected_history_cluster_preregistration_hash: Any,
    history_cluster_preregistration_verification_context: Any,
    expected_budget_cluster_preregistration_hash: Any,
    budget_cluster_preregistration_verification_context: Any,
) -> dict[str, Any]:
    if not verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
        crosswalk_preregistration,
        provenance_preregistration,
        history_cluster_preregistration,
        budget_cluster_preregistration,
        window_crosswalk,
        expected_crosswalk_preregistration_hash=expected_crosswalk_preregistration_hash,
        expected_provenance_preregistration_hash=expected_provenance_preregistration_hash,
        provenance_preregistration_verification_context=provenance_preregistration_verification_context,
        expected_history_cluster_preregistration_hash=expected_history_cluster_preregistration_hash,
        history_cluster_preregistration_verification_context=history_cluster_preregistration_verification_context,
        expected_budget_cluster_preregistration_hash=expected_budget_cluster_preregistration_hash,
        budget_cluster_preregistration_verification_context=budget_cluster_preregistration_verification_context,
    ):
        return _unknown_gate()
    analysis = _analyze_sources(
        history_cluster_preregistration, budget_cluster_preregistration
    )
    if analysis is None:
        return _unknown_gate()
    core = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": _gate_status(analysis),
        "reason_code": (
            "BUDGET_UNIVERSE_REQUIRES_HISTORY_COVERAGE_BEFORE_EFFECTIVE_BUDGET_USE"
            if analysis["budget_uncovered_symbols"]
            else "STRUCTURAL_COVERAGE_DOES_NOT_PROVE_SEMANTIC_EQUIVALENCE"
        ),
        "source": dict(crosswalk_preregistration["source"]),
        "crosswalk": {
            "policy": CROSSWALK_POLICY,
            "window_crosswalk_hash": crosswalk_preregistration[
                "window_crosswalk_hash"
            ],
            "relationship": CROSSWALK_RELATIONSHIP,
        },
        "coverage": {
            "budget_uncovered_symbols": list(analysis["budget_uncovered_symbols"]),
            "history_only_symbols": list(analysis["history_only_symbols"]),
            "shared_symbols": list(analysis["shared_symbols"]),
            "history_shared_cluster_projection": list(
                analysis["history_shared_cluster_projection"]
            ),
            "budget_shared_cluster_projection": list(
                analysis["budget_shared_cluster_projection"]
            ),
        },
        "facts": {
            "all_budget_symbols_history_covered": analysis[
                "all_budget_symbols_history_covered"
            ],
            "full_cluster_partition_identity_equal": analysis[
                "full_cluster_partition_identity_equal"
            ],
            "history_symbol_universe_is_budget_subset": analysis[
                "history_symbol_universe_is_budget_subset"
            ],
            "policy_profile_match": analysis["policy_profile_match"],
            "semantic_study_identity_equivalence_verified": False,
            "shared_symbol_cluster_projection_equal": analysis[
                "shared_symbol_cluster_projection_equal"
            ],
            "source_preregistrations_exactly_verified": True,
            "synthetic_only": True,
            "window_count_equal": analysis["window_count_equal"],
            "window_label_issuer_binding_verified": analysis[
                "window_label_issuer_binding_verified"
            ],
            "window_order_identity_equal": analysis["window_order_identity_equal"],
        },
        "blockers": _dynamic_blockers(analysis),
        "authority": _authority_lock(),
    }
    sealed = _seal(core, "gate_hash")
    return sealed if sealed is not None else _unknown_gate()


def verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
    document: Any,
    crosswalk_preregistration: Any,
    provenance_preregistration: Any,
    history_cluster_preregistration: Any,
    budget_cluster_preregistration: Any,
    window_crosswalk: Any,
    *,
    expected_gate_hash: Any,
    expected_crosswalk_preregistration_hash: Any,
    expected_provenance_preregistration_hash: Any,
    provenance_preregistration_verification_context: Any,
    expected_history_cluster_preregistration_hash: Any,
    history_cluster_preregistration_verification_context: Any,
    expected_budget_cluster_preregistration_hash: Any,
    budget_cluster_preregistration_verification_context: Any,
) -> bool:
    if not _is_hash(expected_gate_hash):
        return False
    expected = evaluate_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
        crosswalk_preregistration,
        provenance_preregistration,
        history_cluster_preregistration,
        budget_cluster_preregistration,
        window_crosswalk,
        expected_crosswalk_preregistration_hash=expected_crosswalk_preregistration_hash,
        expected_provenance_preregistration_hash=expected_provenance_preregistration_hash,
        provenance_preregistration_verification_context=provenance_preregistration_verification_context,
        expected_history_cluster_preregistration_hash=expected_history_cluster_preregistration_hash,
        history_cluster_preregistration_verification_context=history_cluster_preregistration_verification_context,
        expected_budget_cluster_preregistration_hash=expected_budget_cluster_preregistration_hash,
        budget_cluster_preregistration_verification_context=budget_cluster_preregistration_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected.get("gate_hash") == expected_gate_hash
        and document.get("gate_hash") == expected_gate_hash
        and dict(document) == expected
    )
