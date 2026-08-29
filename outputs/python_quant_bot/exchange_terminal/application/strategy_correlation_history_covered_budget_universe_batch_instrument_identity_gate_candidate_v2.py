from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2
    as identity_binding,
)


SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-batch-instrument-"
    "identity-gate-candidate-v2"
)
STATIC_FINGERPRINT = (
    "20260825-strategy-correlation-batch-instrument-identity-gate-candidate-"
    "v2-synthetic-unmounted-permission-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_APPLICATION_BATCH_IDENTITY_GATE_CANDIDATE"
DUPLICATE_STATUS = "BLOCKED_BATCH_DUPLICATE_CANONICAL_INSTRUMENT"
UNKNOWN_IDENTITY_STATUS = "UNKNOWN_BATCH_INSTRUMENT_IDENTITY"
MAX_PROPOSAL_OCCURRENCES = batch_preflight.MAX_PROPOSAL_OCCURRENCES

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PROPOSAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_PROPOSAL_KEYS = {"proposal_id", "symbol", "venue_id"}


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


def _valid_proposals(value: Any) -> bool:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_PROPOSAL_OCCURRENCES
    ):
        return False
    proposal_ids: set[str] = set()
    for proposal in value:
        if not isinstance(proposal, Mapping) or set(proposal.keys()) != _PROPOSAL_KEYS:
            return False
        proposal_id = proposal.get("proposal_id")
        if (
            not isinstance(proposal_id, str)
            or _PROPOSAL_ID_RE.fullmatch(proposal_id) is None
            or proposal_id in proposal_ids
            or not isinstance(proposal.get("symbol"), str)
            or not isinstance(proposal.get("venue_id"), str)
        ):
            return False
        proposal_ids.add(proposal_id)
    return True


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _deduplicated_blockers(values: list[Any]) -> list[str]:
    blockers: list[str] = []
    for value in values:
        if isinstance(value, str) and value not in blockers:
            blockers.append(value)
    return blockers


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


def _registry_entry_by_hash(
    identity_preregistration: Mapping[str, Any],
    identity_entry_hash: Any,
) -> Mapping[str, Any] | None:
    if not _is_hash(identity_entry_hash):
        return None
    entries = identity_preregistration.get("entries")
    if not isinstance(entries, list):
        return None
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and _digest(dict(entry)) == identity_entry_hash
    ]
    return matches[0] if len(matches) == 1 else None


def evaluate_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposals: Any,
    *,
    expected_identity_preregistration_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    if (
        not _valid_proposals(proposals)
        or not _is_hash(expected_projection_preregistration_hash)
        or not identity_binding.verify_strategy_correlation_instrument_identity_preregistration_v1(
            identity_preregistration,
            expected_identity_preregistration_hash=(
                expected_identity_preregistration_hash
            ),
        )
    ):
        return None

    occurrence_evidence: list[dict[str, Any]] = []
    resolved_budget_symbols: list[str] = []
    canonical_identity_hashes: list[str] = []
    identity_binding_hashes: list[str] = []
    unknown_identity_count = 0

    for proposal in proposals:
        proposal_id = proposal["proposal_id"]
        venue_id = proposal["venue_id"]
        symbol = proposal["symbol"]
        binding = identity_binding.evaluate_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
            identity_preregistration,
            projection_preregistration,
            venue_id,
            symbol,
            expected_identity_preregistration_hash=(
                expected_identity_preregistration_hash
            ),
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
        if binding is None:
            return None
        binding_hash = binding.get("identity_binding_hash")
        if not _is_hash(binding_hash) or not identity_binding.verify_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
            binding,
            identity_preregistration,
            projection_preregistration,
            venue_id,
            symbol,
            expected_identity_binding_hash=binding_hash,
            expected_identity_preregistration_hash=(
                expected_identity_preregistration_hash
            ),
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        ):
            return None
        binding_proposal = binding.get("proposal")
        if not isinstance(binding_proposal, Mapping):
            return None

        canonical_hash = binding_proposal.get(
            "canonical_instrument_id_sha256"
        )
        budget_hash = binding_proposal.get("budget_symbol_sha256")
        identity_entry_hash = binding_proposal.get("identity_entry_hash")
        if canonical_hash is None:
            if budget_hash is not None or identity_entry_hash is not None:
                return None
            unknown_identity_count += 1
        else:
            if not _is_hash(canonical_hash) or not _is_hash(budget_hash):
                return None
            registry_entry = _registry_entry_by_hash(
                identity_preregistration,
                identity_entry_hash,
            )
            if registry_entry is None:
                return None
            budget_symbol = registry_entry.get("budget_symbol")
            canonical_instrument_id = registry_entry.get(
                "canonical_instrument_id"
            )
            if (
                not isinstance(budget_symbol, str)
                or not isinstance(canonical_instrument_id, str)
                or _text_digest(budget_symbol) != budget_hash
                or _text_digest(canonical_instrument_id) != canonical_hash
            ):
                return None
            resolved_budget_symbols.append(budget_symbol)
            canonical_identity_hashes.append(canonical_hash)

        identity_binding_hashes.append(binding_hash)
        occurrence_evidence.append({
            "proposal_id_sha256": _text_digest(proposal_id),
            "input_symbol_sha256": binding_proposal.get("input_symbol_sha256"),
            "venue_id_sha256": binding_proposal.get("venue_id_sha256"),
            "identity_binding_hash": binding_hash,
            "canonical_instrument_id_sha256": canonical_hash,
            "budget_symbol_sha256": budget_hash,
            "source_cluster_id_sha256": binding_proposal.get(
                "source_cluster_id_sha256"
            ),
            "source_cluster_members_hash": binding_proposal.get(
                "source_cluster_members_hash"
            ),
        })

    unique_canonical_hashes = _ordered_unique(canonical_identity_hashes)
    canonical_counts = {
        value: canonical_identity_hashes.count(value)
        for value in unique_canonical_hashes
    }
    duplicate_canonical_hashes = [
        value for value in unique_canonical_hashes if canonical_counts[value] > 1
    ]
    duplicate_occurrence_count = len(canonical_identity_hashes) - len(
        unique_canonical_hashes
    )

    source_batch = None
    if unknown_identity_count == 0:
        source_batch = batch_preflight.evaluate_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
            projection_preregistration,
            resolved_budget_symbols,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
        if source_batch is None:
            return None
        source_batch_hash = source_batch.get("preflight_hash")
        if not _is_hash(source_batch_hash) or not batch_preflight.verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
            source_batch,
            projection_preregistration,
            resolved_budget_symbols,
            expected_preflight_hash=source_batch_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        ):
            return None

    if unknown_identity_count > 0:
        status = UNKNOWN_IDENTITY_STATUS
        gap = "BATCH_CONTAINS_UNPREREGISTERED_INSTRUMENT_IDENTITY"
        maturity = "UNVERIFIED_BATCH_INSTRUMENT_IDENTITY"
        blockers = [
            "BATCH_CONTAINS_UNPREREGISTERED_INSTRUMENT_IDENTITY",
            "CANONICAL_TICKET_DERIVATION_INCOMPLETE",
            "BATCH_ADMISSION_NOT_ALLOWED",
        ]
    else:
        source_status = source_batch.get("status")
        source_decision = source_batch.get("decision_path")
        source_blockers = source_batch.get("blockers")
        if not isinstance(source_decision, Mapping) or not isinstance(
            source_blockers, list
        ):
            return None
        if source_status in {
            batch_preflight.UNKNOWN_STATUS,
            batch_preflight.EXCLUDED_STATUS,
        }:
            status = source_status
            gap = source_decision.get("gap")
            maturity = source_decision.get("maturity")
            blockers = list(source_blockers)
        elif duplicate_occurrence_count > 0:
            status = DUPLICATE_STATUS
            gap = "MULTIPLE_PROPOSALS_SHARE_ONE_CANONICAL_INSTRUMENT"
            maturity = "CANONICAL_TICKET_COLLISION_BLOCKED"
            blockers = [
                "BATCH_DUPLICATE_CANONICAL_INSTRUMENT",
                "DUPLICATE_CANONICAL_TICKET_NOT_ADMITTED",
                "BATCH_ADMISSION_NOT_ALLOWED",
            ]
        else:
            status = source_status
            gap = source_decision.get("gap")
            maturity = source_decision.get("maturity")
            blockers = list(source_blockers)

    source_ticket_summary = (
        source_batch.get("ticket_summary")
        if isinstance(source_batch, Mapping)
        and isinstance(source_batch.get("ticket_summary"), Mapping)
        else {}
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": status,
        "source": {
            "identity_preregistration_hash": (
                expected_identity_preregistration_hash
            ),
            "projection_preregistration_hash": (
                expected_projection_preregistration_hash
            ),
            "source_batch_preflight_hash": source_batch.get("preflight_hash")
            if isinstance(source_batch, Mapping)
            else None,
        },
        "decision_path": {
            "source": "ADR0484_IDENTITY_BINDINGS_AND_BATCH_V1_EXACTLY_VERIFIED",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "ticket_summary": {
            "proposal_occurrence_count": len(proposals),
            "resolved_identity_occurrence_count": len(
                canonical_identity_hashes
            ),
            "unknown_identity_occurrence_count": unknown_identity_count,
            "unique_canonical_instrument_count": len(
                unique_canonical_hashes
            ),
            "duplicate_canonical_instrument_occurrence_count": (
                duplicate_occurrence_count
            ),
            "identity_collapse_reduction_count": duplicate_occurrence_count,
            "unique_budget_symbol_count": len(set(resolved_budget_symbols)),
            "source_unique_projected_symbol_count": source_ticket_summary.get(
                "unique_projected_symbol_count"
            ),
            "source_effective_projected_ticket_count": source_ticket_summary.get(
                "effective_projected_ticket_count"
            ),
        },
        "evidence": {
            "proposal_occurrences": occurrence_evidence,
            "identity_binding_hashes": identity_binding_hashes,
            "unique_canonical_instrument_hashes": unique_canonical_hashes,
            "duplicate_canonical_instrument_hashes": duplicate_canonical_hashes,
        },
        "facts": {
            "all_identity_bindings_exactly_verified": True,
            "batch_admission_allowed": False,
            "canonical_aliases_cannot_increase_independent_ticket_count": True,
            "canonical_duplicate_occurrences_blocked": (
                duplicate_occurrence_count > 0
            ),
            "identity_preregistration_exactly_verified": True,
            "proposal_ids_bound_in_order": True,
            "raw_identifiers_redacted": True,
            "source_batch_preflight_exactly_verified": source_batch is not None,
            "synthetic_only": True,
        },
        "blockers": _deduplicated_blockers(
            blockers
            + [
                "BATCH_IDENTITY_GATE_CANDIDATE_UNMOUNTED",
                "BATCH_ADMISSION_NOT_ALLOWED",
                "PAPER_LIVE_UNAUTHORIZED",
            ]
        ),
        "authority": _authority_lock(),
    }
    return _seal(core, "batch_identity_gate_hash")


def verify_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
    document: Any,
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposals: Any,
    *,
    expected_batch_identity_gate_hash: Any,
    expected_identity_preregistration_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_batch_identity_gate_hash):
        return False
    expected = evaluate_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
        identity_preregistration,
        projection_preregistration,
        proposals,
        expected_identity_preregistration_hash=(
            expected_identity_preregistration_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("batch_identity_gate_hash")
        == expected_batch_identity_gate_hash
        and document.get("batch_identity_gate_hash")
        == expected_batch_identity_gate_hash
        and dict(document) == expected
    )
