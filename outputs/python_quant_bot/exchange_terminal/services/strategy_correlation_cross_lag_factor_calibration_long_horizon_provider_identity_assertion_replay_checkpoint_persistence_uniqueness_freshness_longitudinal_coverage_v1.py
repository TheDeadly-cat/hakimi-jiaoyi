from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1 as source_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-"
    "longitudinal-coverage-registration-v1"
)
REGISTRATION_RECEIPT_SCHEMA = f"{REGISTRATION_SCHEMA}-receipt"
EVALUATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-"
    "longitudinal-coverage-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20261003-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-uniqueness-freshness-"
    "longitudinal-coverage-1"
)
REGISTERED_STATUS = "LONGITUDINAL_COVERAGE_WINDOW_REGISTERED_EVALUATIONS_UNOBSERVED"
VERIFIED_STATUS = (
    "CONTIGUOUS_SIGNED_SINGLE_OCCURRENCE_CLAIM_PREFIX_VERIFIED_"
    "EXTERNAL_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"

CHECKPOINT_SEQUENCE_POLICY = "every-tree-size-in-closed-range-v1"
SEGMENT_HANDOFF_POLICY = "next-previous-segment-equals-prior-current-segment-v1"
ASSERTION_STABILITY_POLICY = "same-assertion-digest-and-leaf-index-v1"
WITNESS_STABILITY_POLICY = "same-evidence-registration-and-role-identities-v1"
REFERENCE_TIME_POLICY = "strictly-increasing-bounded-gap-v1"
MIN_EVALUATIONS = 3
MAX_EVALUATIONS = 256
MAX_REFERENCE_GAP_MS = 31 * 24 * 60 * 60 * 1000

_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_REGISTRATION_FIELDS = frozenset(
    {
        "schema",
        "window_id",
        "adapter_id",
        "adapter_implementation_hash",
        "source_evaluation_schema",
        "source_evaluation_static_fingerprint",
        "source_evidence_registration_receipt_hash",
        "replay_registry_id",
        "replay_registry_namespace",
        "assertion_receipt_hash",
        "assertion_leaf_index",
        "start_tree_size",
        "end_tree_size",
        "checkpoint_step",
        "expected_evaluation_count",
        "max_reference_time_gap_ms",
        "checkpoint_sequence_policy",
        "segment_handoff_policy",
        "assertion_stability_policy",
        "witness_stability_policy",
        "reference_time_policy",
    }
)
_ITEM_FIELDS = frozenset({"evaluation", "inputs"})
_SOURCE_INPUT_FIELDS = frozenset(
    {
        "lineage_evaluation",
        "current_segment",
        "previous_segment",
        "evidence_registration",
        "evidence_registration_receipt",
        "occurrence_receipt",
        "occurrence_provider_public_key",
        "time_receipt",
        "time_authority_public_key",
    }
)
_EXACT_REGISTRATION_FIELDS = {
    "schema": REGISTRATION_SCHEMA,
    "source_evaluation_schema": source_contract.EVALUATION_SCHEMA,
    "source_evaluation_static_fingerprint": source_contract.STATIC_FINGERPRINT,
    "checkpoint_step": 1,
    "checkpoint_sequence_policy": CHECKPOINT_SEQUENCE_POLICY,
    "segment_handoff_policy": SEGMENT_HANDOFF_POLICY,
    "assertion_stability_policy": ASSERTION_STABILITY_POLICY,
    "witness_stability_policy": WITNESS_STABILITY_POLICY,
    "reference_time_policy": REFERENCE_TIME_POLICY,
}


def _authority() -> dict[str, bool]:
    return {
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
        "replay_registry_checked": False,
        "pinned_checkpoint_authoritative": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _registration_facts() -> dict[str, bool]:
    return {
        "registration_shape_verified": False,
        "source_contract_pinned": False,
        "coverage_window_preregistered": False,
        "evaluation_batch_observed": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
    }


def _evaluation_facts() -> dict[str, bool]:
    return {
        "coverage_registration_verified": False,
        "source_evaluations_reverified": False,
        "preregistered_window_complete": False,
        "tree_size_sequence_contiguous": False,
        "segment_handoffs_exact": False,
        "assertion_identity_stable": False,
        "witness_identity_stable": False,
        "reference_time_sequence_bounded": False,
        "signed_single_occurrence_claim_prefix_verified": False,
        "bounded_prefix_only": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _registration_evidence() -> dict[str, Any]:
    return {
        "window_id": None,
        "source_evidence_registration_receipt_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "assertion_receipt_hash": None,
        "assertion_leaf_index": None,
        "start_tree_size": None,
        "end_tree_size": None,
        "expected_evaluation_count": None,
        "max_reference_time_gap_ms": None,
    }


def _evaluation_evidence() -> dict[str, Any]:
    return {
        "coverage_registration_receipt_hash": None,
        "source_evidence_registration_receipt_hash": None,
        "window_id": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "assertion_receipt_hash": None,
        "assertion_leaf_index": None,
        "evaluation_count": None,
        "start_tree_size": None,
        "end_tree_size": None,
        "first_source_evaluation_receipt_hash": None,
        "last_source_evaluation_receipt_hash": None,
        "first_checkpoint_hash": None,
        "last_checkpoint_hash": None,
        "first_reference_time_ms_claim": None,
        "last_reference_time_ms_claim": None,
        "maximum_observed_reference_time_gap_ms": None,
        "occurrence_provider_id": None,
        "time_authority_id": None,
    }


def _sealed_registration(
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": REGISTRATION_RECEIPT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts or _registration_facts(),
            "evidence": evidence or _registration_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _sealed_evaluation(
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts or _evaluation_facts(),
            "evidence": evidence or _evaluation_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _strict_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = 2**63 - 1) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _validate_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict:
        return None, "registration_shape_invalid"
    if set(value) != _REGISTRATION_FIELDS:
        return None, "registration_fields_invalid"
    for field, expected in _EXACT_REGISTRATION_FIELDS.items():
        if value.get(field) != expected or type(value.get(field)) is not type(expected):
            return None, f"registration_{field}_invalid"
    for field in ("window_id", "adapter_id", "replay_registry_id", "replay_registry_namespace"):
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    for field in (
        "adapter_implementation_hash",
        "source_evidence_registration_receipt_hash",
        "assertion_receipt_hash",
    ):
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    start = value.get("start_tree_size")
    end = value.get("end_tree_size")
    count = value.get("expected_evaluation_count")
    leaf_index = value.get("assertion_leaf_index")
    if not _strict_int(start, minimum=1):
        return None, "registration_start_tree_size_invalid"
    if not _strict_int(end, minimum=start + MIN_EVALUATIONS - 1):
        return None, "registration_end_tree_size_invalid"
    if not _strict_int(count, minimum=MIN_EVALUATIONS, maximum=MAX_EVALUATIONS):
        return None, "registration_expected_evaluation_count_invalid"
    if count != end - start + 1:
        return None, "registration_evaluation_count_range_mismatch"
    if not _strict_int(leaf_index) or leaf_index >= start:
        return None, "registration_assertion_leaf_index_invalid"
    max_gap = value.get("max_reference_time_gap_ms")
    if not _strict_int(max_gap, minimum=1, maximum=MAX_REFERENCE_GAP_MS):
        return None, "registration_max_reference_time_gap_ms_invalid"
    return value, None


def build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    clean, reason = _validate_registration(registration)
    if clean is None:
        return _sealed_registration(status=UNKNOWN_STATUS, reason=reason)
    facts = _registration_facts()
    facts.update(
        {
            "registration_shape_verified": True,
            "source_contract_pinned": True,
            "coverage_window_preregistered": True,
        }
    )
    evidence = _registration_evidence()
    for field in evidence:
        evidence[field] = clean[field]
    return _sealed_registration(
        status=REGISTERED_STATUS,
        reason=None,
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
    receipt: Any,
    *,
    registration: Any,
) -> bool:
    return type(receipt) is dict and receipt == build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
        registration
    )


def _source_item(
    item: Any,
    *,
    registration: dict[str, Any],
    expected_tree_size: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(item) is not dict or set(item) != _ITEM_FIELDS:
        return None, "evaluation_item_shape_invalid"
    evaluation = item.get("evaluation")
    inputs = item.get("inputs")
    if type(evaluation) is not dict or type(inputs) is not dict:
        return None, "evaluation_item_payload_shape_invalid"
    if set(inputs) != _SOURCE_INPUT_FIELDS:
        return None, "source_evaluation_inputs_fields_invalid"
    try:
        verified = source_contract.verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1(
            evaluation,
            **inputs,
        )
    except (KeyError, TypeError, ValueError):
        verified = False
    if not verified or evaluation.get("status") != source_contract.VERIFIED_STATUS:
        return None, "source_evaluation_unverified"
    evidence = evaluation.get("evidence")
    facts = evaluation.get("facts")
    authority = evaluation.get("authority")
    source_registration_receipt = inputs.get("evidence_registration_receipt")
    lineage_evaluation = inputs.get("lineage_evaluation")
    current_segment = inputs.get("current_segment")
    if not all(
        type(value) is dict
        for value in (
            evidence,
            facts,
            authority,
            source_registration_receipt,
            lineage_evaluation,
            current_segment,
        )
    ):
        return None, "source_evaluation_nested_shape_invalid"
    exact = {
        "registration_receipt_hash": registration[
            "source_evidence_registration_receipt_hash"
        ],
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
        "assertion_receipt_hash": registration["assertion_receipt_hash"],
        "assertion_leaf_index": registration["assertion_leaf_index"],
        "checkpoint_tree_size": expected_tree_size,
        "occurrence_count_claim": 1,
        "occurrence_leaf_indices_claim": [registration["assertion_leaf_index"]],
    }
    for field, expected in exact.items():
        if evidence.get(field) != expected or type(evidence.get(field)) is not type(expected):
            return None, f"source_{field}_mismatch"
    if source_registration_receipt.get("receipt_hash") != registration[
        "source_evidence_registration_receipt_hash"
    ]:
        return None, "source_registration_receipt_hash_mismatch"
    for field in (
        "lineage_receipt_hash",
        "occurrence_receipt_hash",
        "time_receipt_hash",
        "checkpoint_root_hash",
        "checkpoint_hash",
        "assertion_receipt_hash",
    ):
        if not _strict_hash(evidence.get(field)):
            return None, f"source_{field}_invalid"
    for field in (
        "scan_completed_at_ms_claim",
        "reference_time_ms_claim",
    ):
        if not _strict_int(evidence.get(field), minimum=1):
            return None, f"source_{field}_invalid"
    if evidence["scan_completed_at_ms_claim"] > evidence["reference_time_ms_claim"]:
        return None, "source_scan_after_reference_time"
    if type(evidence.get("occurrence_provider_id")) is not str or type(
        evidence.get("time_authority_id")
    ) is not str:
        return None, "source_witness_identity_invalid"
    for field in (
        "complete_scan_claim_verified",
        "exactly_one_occurrence_claim_verified",
        "time_window_claim_verified",
    ):
        if facts.get(field) is not True:
            return None, f"source_{field}_not_verified"
    for field in (
        "assertion_uniqueness_verified",
        "freshness_verified",
        "replay_absence_verified",
        "complete_history_verified",
    ):
        if facts.get(field) is not False:
            return None, f"source_{field}_must_remain_false"
    if not authority or any(value is not False for value in authority.values()):
        return None, "source_authority_not_negative"
    lineage_evidence = lineage_evaluation.get("evidence")
    current_binding = current_segment.get("binding")
    if type(lineage_evidence) is not dict or type(current_binding) is not dict:
        return None, "source_lineage_handoff_shape_invalid"
    if lineage_evidence.get("current_binding_receipt_hash") != current_binding.get(
        "receipt_hash"
    ):
        return None, "source_current_binding_receipt_hash_mismatch"
    if evaluation.get("receipt_hash") is None or not _strict_hash(evaluation["receipt_hash"]):
        return None, "source_evaluation_receipt_hash_invalid"
    return {
        "evaluation": evaluation,
        "inputs": inputs,
        "evidence": evidence,
        "lineage_evidence": lineage_evidence,
        "current_binding_receipt_hash": current_binding["receipt_hash"],
    }, None


def evaluate_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    evaluation_items: Any,
) -> dict[str, Any]:
    if not verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
        registration_receipt,
        registration=registration,
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="coverage_registration_unverified")
    if registration_receipt.get("status") != REGISTERED_STATUS:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="coverage_registration_not_registered")
    if type(evaluation_items) is not list or len(evaluation_items) != registration[
        "expected_evaluation_count"
    ]:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="evaluation_batch_count_mismatch")
    normalized: list[dict[str, Any]] = []
    for offset, item in enumerate(evaluation_items):
        clean, reason = _source_item(
            item,
            registration=registration,
            expected_tree_size=registration["start_tree_size"] + offset,
        )
        if clean is None:
            return _sealed_evaluation(
                status=UNKNOWN_STATUS,
                reason=f"item_{offset}_{reason}",
            )
        normalized.append(clean)
    first_evidence = normalized[0]["evidence"]
    occurrence_provider_id = first_evidence["occurrence_provider_id"]
    time_authority_id = first_evidence["time_authority_id"]
    evaluation_hashes: set[str] = set()
    checkpoint_hashes: set[str] = set()
    occurrence_hashes: set[str] = set()
    references: list[int] = []
    scans: list[int] = []
    for index, item in enumerate(normalized):
        evidence = item["evidence"]
        evaluation_hash = item["evaluation"]["receipt_hash"]
        checkpoint_hash = evidence["checkpoint_hash"]
        occurrence_hash = evidence["occurrence_receipt_hash"]
        if evaluation_hash in evaluation_hashes:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_evaluation_receipt_hash_reused")
        if checkpoint_hash in checkpoint_hashes:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="checkpoint_hash_reused")
        if occurrence_hash in occurrence_hashes:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="occurrence_receipt_hash_reused")
        evaluation_hashes.add(evaluation_hash)
        checkpoint_hashes.add(checkpoint_hash)
        occurrence_hashes.add(occurrence_hash)
        if evidence["occurrence_provider_id"] != occurrence_provider_id:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="occurrence_provider_identity_drift")
        if evidence["time_authority_id"] != time_authority_id:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="time_authority_identity_drift")
        references.append(evidence["reference_time_ms_claim"])
        scans.append(evidence["scan_completed_at_ms_claim"])
        if index == 0:
            continue
        previous = normalized[index - 1]
        if item["inputs"]["previous_segment"] != previous["inputs"]["current_segment"]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="segment_handoff_mismatch")
        if item["lineage_evidence"].get("previous_binding_receipt_hash") != previous[
            "current_binding_receipt_hash"
        ]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="lineage_previous_binding_mismatch")
        if scans[index] <= scans[index - 1]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="scan_time_not_strictly_increasing")
        if references[index] <= references[index - 1]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="reference_time_not_strictly_increasing")
        if references[index] - references[index - 1] > registration[
            "max_reference_time_gap_ms"
        ]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason="reference_time_gap_exceeds_registration")
    gaps = [references[index] - references[index - 1] for index in range(1, len(references))]
    facts = _evaluation_facts()
    facts.update(
        {
            "coverage_registration_verified": True,
            "source_evaluations_reverified": True,
            "preregistered_window_complete": True,
            "tree_size_sequence_contiguous": True,
            "segment_handoffs_exact": True,
            "assertion_identity_stable": True,
            "witness_identity_stable": True,
            "reference_time_sequence_bounded": True,
            "signed_single_occurrence_claim_prefix_verified": True,
            "bounded_prefix_only": True,
        }
    )
    evidence = _evaluation_evidence()
    evidence.update(
        {
            "coverage_registration_receipt_hash": registration_receipt["receipt_hash"],
            "source_evidence_registration_receipt_hash": registration[
                "source_evidence_registration_receipt_hash"
            ],
            "window_id": registration["window_id"],
            "replay_registry_id": registration["replay_registry_id"],
            "replay_registry_namespace": registration["replay_registry_namespace"],
            "assertion_receipt_hash": registration["assertion_receipt_hash"],
            "assertion_leaf_index": registration["assertion_leaf_index"],
            "evaluation_count": len(normalized),
            "start_tree_size": registration["start_tree_size"],
            "end_tree_size": registration["end_tree_size"],
            "first_source_evaluation_receipt_hash": normalized[0]["evaluation"]["receipt_hash"],
            "last_source_evaluation_receipt_hash": normalized[-1]["evaluation"]["receipt_hash"],
            "first_checkpoint_hash": normalized[0]["evidence"]["checkpoint_hash"],
            "last_checkpoint_hash": normalized[-1]["evidence"]["checkpoint_hash"],
            "first_reference_time_ms_claim": references[0],
            "last_reference_time_ms_claim": references[-1],
            "maximum_observed_reference_time_gap_ms": max(gaps),
            "occurrence_provider_id": occurrence_provider_id,
            "time_authority_id": time_authority_id,
        }
    )
    return _sealed_evaluation(
        status=VERIFIED_STATUS,
        reason=None,
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1(
    evaluation: Any,
    *,
    registration: Any,
    registration_receipt: Any,
    evaluation_items: Any,
) -> bool:
    if type(evaluation) is not dict:
        return False
    try:
        expected = evaluate_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_v1(
            registration=registration,
            registration_receipt=registration_receipt,
            evaluation_items=evaluation_items,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return evaluation == expected
