from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_covered_universe_projection_v1
    as covered_projection,
)


SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-proposal-preflight-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-history-covered-budget-universe-proposal-"
    "preflight-v1-synthetic-unmounted-hash-only-permission-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_APPLICATION_PREFLIGHT_CANDIDATE"
EXCLUDED_STATUS = "BLOCKED_HISTORY_COVERAGE_EXCLUDED_SYMBOL"
PROJECTED_IMMATURE_STATUS = "BLOCKED_FRESH_PROJECTED_EVIDENCE_INCOMPLETE"
UNKNOWN_STATUS = "UNKNOWN_SYMBOL_OUTSIDE_VERIFIED_BUDGET_UNIVERSE"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_PROJECTION_CONTEXT_KEYS = {
    "structural_coverage_gate",
    "expected_structural_coverage_gate_hash",
    "structural_gate_verification_context",
}


def _authority_lock() -> dict[str, bool]:
    return {
        "consumer_registration_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "effective_budget_activation_allowed": False,
        "http_registration_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "proposal_admission_allowed": False,
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


def _source_preregistrations(
    verification_context: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    structural_context = verification_context.get(
        "structural_gate_verification_context"
    )
    if not isinstance(structural_context, Mapping):
        return None
    history = structural_context.get("history_cluster_preregistration")
    budget = structural_context.get("budget_cluster_preregistration")
    if not isinstance(history, Mapping) or not isinstance(budget, Mapping):
        return None
    return history, budget


def _source_cluster(
    symbol: str,
    budget_cluster_preregistration: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    clusters = budget_cluster_preregistration.get("expected_clusters")
    if not isinstance(clusters, list):
        return None
    matches = []
    for cluster in clusters:
        if not isinstance(cluster, Mapping):
            return None
        members = cluster.get("members")
        if not isinstance(members, list):
            return None
        if symbol in members:
            matches.append(cluster)
    return matches[0] if len(matches) == 1 else None


def _classification(
    symbol: str,
    projection: Mapping[str, Any],
    history: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> dict[str, Any] | None:
    derivation = projection.get("derivation")
    if not isinstance(derivation, Mapping):
        return None
    projected_symbols = derivation.get("projected_symbols")
    excluded_symbols = derivation.get("excluded_symbols")
    history_symbols = history.get("expected_symbols")
    budget_symbols = budget.get("expected_symbols")
    if not all(
        isinstance(value, list)
        for value in (
            projected_symbols,
            excluded_symbols,
            history_symbols,
            budget_symbols,
        )
    ):
        return None

    known_in_history = symbol in history_symbols
    known_in_budget = symbol in budget_symbols
    source_cluster = _source_cluster(symbol, budget) if known_in_budget else None
    cluster_id_hash = None
    cluster_members_hash = None
    if source_cluster is not None:
        cluster_id = source_cluster.get("cluster_id")
        members = source_cluster.get("members")
        if not isinstance(cluster_id, str) or not isinstance(members, list):
            return None
        cluster_id_hash = _text_digest(cluster_id)
        cluster_members_hash = _digest(members)

    if symbol in excluded_symbols:
        return {
            "status": EXCLUDED_STATUS,
            "classification": "EXCLUDED_BY_CLUSTER_ATOMIC_HISTORY_COVERAGE_POLICY",
            "gap": "PERSISTED_HISTORY_COVERAGE_MISSING_OR_CLUSTER_ATOMIC_EXCLUSION",
            "maturity": "EXCLUDED_BY_PREREGISTERED_PROJECTION_POLICY",
            "known_in_history": known_in_history,
            "known_in_budget": known_in_budget,
            "projected_universe_member": False,
            "excluded_universe_member": True,
            "source_cluster_id_sha256": cluster_id_hash,
            "source_cluster_members_hash": cluster_members_hash,
            "blockers": [
                "PROPOSED_SYMBOL_EXCLUDED_BY_HISTORY_COVERAGE_POLICY",
                "SOURCE_CLUSTER_NOT_ELIGIBLE_FOR_PROJECTION",
                "PROPOSAL_ADMISSION_NOT_ALLOWED",
            ],
        }
    if symbol in projected_symbols:
        return {
            "status": PROJECTED_IMMATURE_STATUS,
            "classification": "PROJECTED_UNIVERSE_MEMBER_FRESH_EVIDENCE_ABSENT",
            "gap": "FRESH_PROJECTED_BUDGET_EVIDENCE_INCOMPLETE",
            "maturity": "PROJECTED_UNIVERSE_PREREGISTERED_ONLY",
            "known_in_history": known_in_history,
            "known_in_budget": known_in_budget,
            "projected_universe_member": True,
            "excluded_universe_member": False,
            "source_cluster_id_sha256": cluster_id_hash,
            "source_cluster_members_hash": cluster_members_hash,
            "blockers": [
                "FRESH_PROJECTED_MULTI_WINDOW_AUDITS_NOT_PROVIDED",
                "FRESH_PROJECTED_CLUSTER_GATE_NOT_PROVIDED",
                "FRESH_PROJECTED_EFFECTIVE_BUDGET_BINDING_NOT_PROVIDED",
                "PROPOSAL_ADMISSION_NOT_ALLOWED",
            ],
        }
    return {
        "status": UNKNOWN_STATUS,
        "classification": "SYMBOL_OUTSIDE_PROJECTED_AND_EXCLUDED_BUDGET_SETS",
        "gap": "SYMBOL_OUTSIDE_VERIFIED_PROJECTED_BUDGET_UNIVERSE",
        "maturity": "UNVERIFIED_SYMBOL",
        "known_in_history": known_in_history,
        "known_in_budget": known_in_budget,
        "projected_universe_member": False,
        "excluded_universe_member": False,
        "source_cluster_id_sha256": cluster_id_hash,
        "source_cluster_members_hash": cluster_members_hash,
        "blockers": [
            "PROPOSED_SYMBOL_OUTSIDE_VERIFIED_PROJECTED_BUDGET_UNIVERSE",
            "PROPOSAL_ADMISSION_NOT_ALLOWED",
        ],
    }


def evaluate_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
    projection_preregistration: Any,
    proposed_symbol: Any,
    *,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    if not isinstance(proposed_symbol, str) or _SYMBOL_RE.fullmatch(proposed_symbol) is None:
        return None
    if not _verify_projection(
        projection_preregistration,
        expected_projection_hash=expected_projection_preregistration_hash,
        verification_context=projection_verification_context,
    ):
        return None
    source_bundle = _source_preregistrations(projection_verification_context)
    if source_bundle is None:
        return None
    history, budget = source_bundle
    classification = _classification(
        proposed_symbol,
        projection_preregistration,
        history,
        budget,
    )
    if classification is None:
        return None
    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": classification["status"],
        "reason_code": classification["classification"],
        "proposal": {
            "symbol_sha256": _text_digest(proposed_symbol),
            "source_cluster_id_sha256": classification[
                "source_cluster_id_sha256"
            ],
            "source_cluster_members_hash": classification[
                "source_cluster_members_hash"
            ],
        },
        "decision_path": {
            "source": "ADR0365_PROJECTION_EXACTLY_VERIFIED",
            "gap": classification["gap"],
            "maturity": classification["maturity"],
            "permission": "NOT_AUTHORIZED",
        },
        "facts": {
            "excluded_universe_member": classification[
                "excluded_universe_member"
            ],
            "fresh_projected_budget_evidence_completed": False,
            "known_in_budget_source": classification["known_in_budget"],
            "known_in_history_source": classification["known_in_history"],
            "projection_exactly_verified": True,
            "projected_universe_member": classification[
                "projected_universe_member"
            ],
            "proposal_admission_allowed": False,
            "raw_symbol_redacted": True,
            "synthetic_only": True,
        },
        "blockers": classification["blockers"]
        + [
            "RUNTIME_CONSUMER_NOT_REGISTERED",
            "PAPER_LIVE_UNAUTHORIZED",
        ],
        "authority": _authority_lock(),
    }
    return _seal(core, "preflight_hash")


def verify_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
    document: Any,
    projection_preregistration: Any,
    proposed_symbol: Any,
    *,
    expected_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_preflight_hash):
        return False
    expected = evaluate_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
        projection_preregistration,
        proposed_symbol,
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
