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
    strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
    as batch_identity_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as position_post_merge,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2
    as identity_binding,
)


SCHEMA_VERSION = (
    "strategy-correlation-history-covered-budget-universe-identity-bound-"
    "position-derived-post-merge-cluster-exposure-gate-candidate-v3"
)
STATIC_FINGERPRINT = (
    "20260825-strategy-correlation-identity-bound-position-derived-post-merge-"
    "candidate-v3-synthetic-unmounted-permission-lock-1"
)
CONSUMER_STATUS = (
    "UNMOUNTED_IDENTITY_BOUND_POSITION_DERIVED_POST_MERGE_CANDIDATE"
)
MAX_PROPOSAL_OCCURRENCES = batch_identity_gate.MAX_PROPOSAL_OCCURRENCES

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PROPOSAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_PROPOSAL_KEYS = {
    "proposal_id",
    "requested_gross_bps",
    "symbol",
    "venue_id",
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
    return type(value) is str and _HEX64_RE.fullmatch(value) is not None


def _valid_proposals(value: Any) -> bool:
    if (
        type(value) is not list
        or not value
        or len(value) > MAX_PROPOSAL_OCCURRENCES
    ):
        return False
    proposal_ids: set[str] = set()
    for proposal in value:
        if type(proposal) is not dict or set(proposal.keys()) != _PROPOSAL_KEYS:
            return False
        proposal_id = proposal.get("proposal_id")
        requested_gross_bps = proposal.get("requested_gross_bps")
        if (
            type(proposal_id) is not str
            or _PROPOSAL_ID_RE.fullmatch(proposal_id) is None
            or proposal_id in proposal_ids
            or type(proposal.get("symbol")) is not str
            or type(proposal.get("venue_id")) is not str
            or type(requested_gross_bps) is not int
            or not 1
            <= requested_gross_bps
            <= exposure_preflight.MAX_GROSS_BPS
        ):
            return False
        proposal_ids.add(proposal_id)
    return True


def _stripped_identity_proposals(proposals: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "proposal_id": proposal["proposal_id"],
            "venue_id": proposal["venue_id"],
            "symbol": proposal["symbol"],
        }
        for proposal in proposals
    ]


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
        "post_merge_admission_allowed": False,
        "profitability_claim_allowed": False,
        "readonly_projection_adapter_activation_allowed": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "research_evidence_only": True,
    }


def _policy_payload(
    policy: exposure_preflight.ClusterExposurePolicyV1,
) -> dict[str, Any] | None:
    if not isinstance(policy, exposure_preflight.ClusterExposurePolicyV1):
        return None
    return {
        "policy_version": policy.policy_version,
        "policy_id": policy.policy_id,
        "max_proposals": policy.max_proposals,
        "max_portfolio_gross_bps": policy.max_portfolio_gross_bps,
        "max_cluster_gross_bps": policy.max_cluster_gross_bps,
        "max_single_proposal_gross_bps": policy.max_single_proposal_gross_bps,
    }


def _registry_budget_symbol(
    identity_preregistration: Mapping[str, Any],
    *,
    canonical_instrument_hash: str,
    budget_symbol_hash: str,
) -> str | None:
    entries = identity_preregistration.get("entries")
    if type(entries) is not list:
        return None
    matches: set[str] = set()
    for entry in entries:
        if type(entry) is not dict:
            return None
        canonical_instrument_id = entry.get("canonical_instrument_id")
        budget_symbol = entry.get("budget_symbol")
        if type(canonical_instrument_id) is not str or type(budget_symbol) is not str:
            return None
        if (
            _text_digest(canonical_instrument_id) == canonical_instrument_hash
            and _text_digest(budget_symbol) == budget_symbol_hash
        ):
            matches.add(budget_symbol)
    return next(iter(matches)) if len(matches) == 1 else None


def evaluate_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
    batch_identity_gate_document: Any,
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposals: Any,
    exposure_policy: Any,
    position_snapshot_claim: Any,
    *,
    expected_batch_identity_gate_hash: Any,
    expected_identity_preregistration_hash: Any,
    expected_position_snapshot_claim_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    if not _valid_proposals(proposals):
        return None
    policy_payload = _policy_payload(exposure_policy)
    if policy_payload is None or not all(
        _is_hash(value)
        for value in (
            expected_batch_identity_gate_hash,
            expected_identity_preregistration_hash,
            expected_position_snapshot_claim_hash,
            expected_projection_preregistration_hash,
        )
    ):
        return None
    if not identity_binding.verify_strategy_correlation_instrument_identity_preregistration_v1(
        identity_preregistration,
        expected_identity_preregistration_hash=(
            expected_identity_preregistration_hash
        ),
    ):
        return None

    stripped_proposals = _stripped_identity_proposals(proposals)
    if not batch_identity_gate.verify_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
        batch_identity_gate_document,
        identity_preregistration,
        projection_preregistration,
        stripped_proposals,
        expected_batch_identity_gate_hash=expected_batch_identity_gate_hash,
        expected_identity_preregistration_hash=(
            expected_identity_preregistration_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    ):
        return None

    incumbent_snapshot = position_post_merge.build_position_derived_incumbent_cluster_exposure_snapshot_v2(
        position_snapshot_claim,
        expected_position_snapshot_claim_hash=(
            expected_position_snapshot_claim_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if incumbent_snapshot is None:
        return None

    gate_evidence = batch_identity_gate_document.get("evidence")
    occurrence_evidence = (
        gate_evidence.get("proposal_occurrences")
        if isinstance(gate_evidence, Mapping)
        else None
    )
    if not isinstance(occurrence_evidence, list) or len(
        occurrence_evidence
    ) != len(proposals):
        return None

    exposure_occurrences: list[dict[str, Any]] = []
    resolved_exposure_proposals: list[
        exposure_preflight.ClusterExposureProposalV1
    ] = []
    for proposal, identity_evidence in zip(proposals, occurrence_evidence):
        if not isinstance(identity_evidence, Mapping):
            return None
        proposal_id = proposal["proposal_id"]
        canonical_hash = identity_evidence.get(
            "canonical_instrument_id_sha256"
        )
        budget_hash = identity_evidence.get("budget_symbol_sha256")
        if identity_evidence.get("proposal_id_sha256") != _text_digest(
            proposal_id
        ):
            return None
        if canonical_hash is None:
            if budget_hash is not None:
                return None
            budget_symbol = None
        else:
            if not _is_hash(canonical_hash) or not _is_hash(budget_hash):
                return None
            budget_symbol = _registry_budget_symbol(
                identity_preregistration,
                canonical_instrument_hash=canonical_hash,
                budget_symbol_hash=budget_hash,
            )
            if budget_symbol is None:
                return None
            resolved_exposure_proposals.append(
                exposure_preflight.ClusterExposureProposalV1(
                    proposal_id=proposal_id,
                    symbol=budget_symbol,
                    requested_gross_bps=proposal["requested_gross_bps"],
                )
            )
        exposure_occurrences.append({
            "proposal_id_sha256": identity_evidence.get(
                "proposal_id_sha256"
            ),
            "identity_binding_hash": identity_evidence.get(
                "identity_binding_hash"
            ),
            "canonical_instrument_id_sha256": canonical_hash,
            "budget_symbol_sha256": budget_hash,
            "requested_gross_bps": proposal["requested_gross_bps"],
        })

    exposure_binding_core = {
        "batch_identity_gate_hash": expected_batch_identity_gate_hash,
        "position_snapshot_claim_hash": expected_position_snapshot_claim_hash,
        "projection_preregistration_hash": (
            expected_projection_preregistration_hash
        ),
        "ordered_exposure_occurrences": exposure_occurrences,
        "requested_total_gross_bps": sum(
            proposal["requested_gross_bps"] for proposal in proposals
        ),
        "requested_policy_hash": _digest(policy_payload),
    }
    exposure_binding_hash = _digest(exposure_binding_core)
    if exposure_binding_hash is None:
        return None

    gate_status = batch_identity_gate_document.get("status")
    gate_decision = batch_identity_gate_document.get("decision_path")
    gate_blockers = batch_identity_gate_document.get("blockers")
    gate_summary = batch_identity_gate_document.get("ticket_summary")
    gate_source = batch_identity_gate_document.get("source")
    if not all(
        isinstance(value, Mapping)
        for value in (gate_decision, gate_summary, gate_source)
    ) or not isinstance(gate_blockers, list):
        return None

    downstream = None
    source_batch = None
    eligible_for_post_merge = (
        gate_status == batch_preflight.PROJECTED_IMMATURE_STATUS
        and gate_summary.get("unknown_identity_occurrence_count") == 0
        and gate_summary.get(
            "duplicate_canonical_instrument_occurrence_count"
        )
        == 0
        and len(resolved_exposure_proposals) == len(proposals)
    )
    if eligible_for_post_merge:
        resolved_budget_symbols = [
            proposal.symbol for proposal in resolved_exposure_proposals
        ]
        source_batch = batch_preflight.evaluate_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
            projection_preregistration,
            resolved_budget_symbols,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
        expected_source_batch_hash = gate_source.get(
            "source_batch_preflight_hash"
        )
        if (
            source_batch is None
            or source_batch.get("preflight_hash") != expected_source_batch_hash
            or not batch_preflight.verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
                source_batch,
                projection_preregistration,
                resolved_budget_symbols,
                expected_preflight_hash=expected_source_batch_hash,
                expected_projection_preregistration_hash=(
                    expected_projection_preregistration_hash
                ),
                projection_verification_context=projection_verification_context,
            )
        ):
            return None
        downstream = position_post_merge.evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2(
            source_batch,
            projection_preregistration,
            tuple(resolved_exposure_proposals),
            exposure_policy,
            position_snapshot_claim,
            expected_position_snapshot_claim_hash=(
                expected_position_snapshot_claim_hash
            ),
            expected_batch_preflight_hash=expected_source_batch_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
        if downstream is None or not position_post_merge.verify_position_derived_post_merge_cluster_exposure_result_v2(
            downstream,
            source_batch,
            projection_preregistration,
            tuple(resolved_exposure_proposals),
            exposure_policy,
            position_snapshot_claim,
            expected_position_snapshot_claim_hash=(
                expected_position_snapshot_claim_hash
            ),
            expected_batch_preflight_hash=expected_source_batch_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        ):
            return None

    if downstream is None:
        status = gate_status
        gap = gate_decision.get("gap")
        maturity = gate_decision.get("maturity")
        blockers = list(gate_blockers) + [
            "POSITION_DERIVED_POST_MERGE_NOT_EVALUATED",
        ]
    else:
        status = downstream.status
        gap = (
            "POSITION_DERIVED_POST_MERGE_LIMIT_RESULT_OBSERVED"
            if downstream.blocker_codes
            else "POSITION_DERIVED_POST_MERGE_WITHIN_LIMIT_OBSERVED"
        )
        maturity = "SYNTHETIC_POST_MERGE_UNVERIFIED_PROVIDER_AND_FRESHNESS"
        blockers = list(downstream.blocker_codes)

    risk_summary = {
        "proposal_count": downstream.proposal_count
        if downstream is not None
        else None,
        "incumbent_cluster_count": downstream.incumbent_cluster_count
        if downstream is not None
        else None,
        "proposed_cluster_count": downstream.proposed_cluster_count
        if downstream is not None
        else None,
        "post_merge_cluster_count": downstream.post_merge_cluster_count
        if downstream is not None
        else None,
        "incumbent_total_gross_bps": downstream.incumbent_total_gross_bps
        if downstream is not None
        else None,
        "proposed_total_gross_bps": downstream.proposed_total_gross_bps
        if downstream is not None
        else None,
        "post_merge_total_gross_bps": downstream.post_merge_total_gross_bps
        if downstream is not None
        else None,
        "maximum_post_merge_cluster_gross_bps": (
            downstream.maximum_post_merge_cluster_gross_bps
            if downstream is not None
            else None
        ),
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": status,
        "source": {
            "batch_identity_gate_hash": expected_batch_identity_gate_hash,
            "identity_preregistration_hash": (
                expected_identity_preregistration_hash
            ),
            "projection_preregistration_hash": (
                expected_projection_preregistration_hash
            ),
            "position_snapshot_claim_hash": (
                expected_position_snapshot_claim_hash
            ),
            "derived_incumbent_snapshot_hash": incumbent_snapshot.snapshot_hash,
            "source_batch_preflight_hash": source_batch.get("preflight_hash")
            if isinstance(source_batch, Mapping)
            else None,
            "position_derived_post_merge_result_hash": downstream.result_hash
            if downstream is not None
            else None,
        },
        "decision_path": {
            "source": "ADR0485_BATCH_IDENTITY_AND_POSITION_DERIVED_V2_EXACTLY_VERIFIED",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "exposure_binding": {
            **exposure_binding_core,
            "exposure_binding_hash": exposure_binding_hash,
        },
        "risk_summary": risk_summary,
        "facts": {
            "batch_identity_gate_exactly_verified": True,
            "canonical_duplicate_batch_rejected_before_post_merge": (
                gate_status == batch_identity_gate.DUPLICATE_STATUS
            ),
            "incumbent_position_claim_exactly_verified": True,
            "position_derived_post_merge_exactly_verified": downstream
            is not None,
            "proposal_amounts_bound_in_order": True,
            "provider_identity_verified": False,
            "raw_identifiers_redacted": True,
            "source_truth_verified": False,
            "freshness_verified": False,
            "post_merge_admission_allowed": False,
            "synthetic_only": True,
        },
        "blockers": _deduplicated_blockers(
            blockers
            + [
                "INCUMBENT_PROVIDER_IDENTITY_NOT_VERIFIED",
                "INCUMBENT_SOURCE_TRUTH_NOT_VERIFIED",
                "INCUMBENT_FRESHNESS_NOT_VERIFIED",
                "IDENTITY_BOUND_POST_MERGE_CANDIDATE_UNMOUNTED",
                "POST_MERGE_ADMISSION_NOT_ALLOWED",
                "PAPER_LIVE_UNAUTHORIZED",
            ]
        ),
        "authority": _authority_lock(),
    }
    return _seal(core, "identity_bound_post_merge_hash")


def verify_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
    document: Any,
    batch_identity_gate_document: Any,
    identity_preregistration: Any,
    projection_preregistration: Any,
    proposals: Any,
    exposure_policy: Any,
    position_snapshot_claim: Any,
    *,
    expected_identity_bound_post_merge_hash: Any,
    expected_batch_identity_gate_hash: Any,
    expected_identity_preregistration_hash: Any,
    expected_position_snapshot_claim_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_identity_bound_post_merge_hash):
        return False
    expected = evaluate_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
        batch_identity_gate_document,
        identity_preregistration,
        projection_preregistration,
        proposals,
        exposure_policy,
        position_snapshot_claim,
        expected_batch_identity_gate_hash=expected_batch_identity_gate_hash,
        expected_identity_preregistration_hash=(
            expected_identity_preregistration_hash
        ),
        expected_position_snapshot_claim_hash=(
            expected_position_snapshot_claim_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("identity_bound_post_merge_hash")
        == expected_identity_bound_post_merge_hash
        and document.get("identity_bound_post_merge_hash")
        == expected_identity_bound_post_merge_hash
        and dict(document) == expected
    )
