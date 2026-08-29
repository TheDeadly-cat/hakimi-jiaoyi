from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1 as source_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-lineage-"
    "history-coverage-registration-v1"
)
REGISTRATION_RECEIPT_SCHEMA_VERSION = f"{REGISTRATION_SCHEMA_VERSION}-receipt"
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-lineage-"
    "history-coverage-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-multi-window-lifecycle-replay-checkpoint-"
    "persistence-lineage-history-coverage-gate-v1-synthetic-unmounted-lock-1"
)
SOURCE_IMPLEMENTATION_SHA256 = (
    "a8fefe0d86f6caa6e7774ca629f211d8cff86c0816ab7c90601293d2ef97cdf9"
)
SOURCE_PASS_REASON = "PASS_PERSISTED_CHECKPOINT_LINEAGE"
REGISTERED_STATUS = "HISTORY_COVERAGE_REGISTERED_FUTURE_SEGMENTS_UNOBSERVED"
PASS_STATUS = "PASS"
PASS_REASON = "PASS_PREREGISTERED_BOUNDED_PERSISTED_CHECKPOINT_HISTORY_COVERAGE"
UNKNOWN_STATUS = "UNKNOWN"

CHECKPOINT_SEQUENCE_POLICY = "every-tree-size-in-registered-closed-range-v1"
SEGMENT_SEQUENCE_POLICY = "anchor-then-exact-previous-segment-handoffs-v1"
ASSET_HANDOFF_POLICY = "next-previous-asset-hash-equals-prior-current-asset-hash-v1"
IDENTITY_STABILITY_POLICY = "registered-study-window-registry-and-persistence-identity-v1"
TIME_POLICY = "anchor-before-registration-future-assets-in-bounded-window-v1"
MIN_SEGMENTS = 3
MAX_SEGMENTS = 64
MAX_ASSET_TIME_GAP_SECONDS = 31 * 24 * 60 * 60

_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_REGISTRATION_FIELDS = frozenset(
    {
        "schema_version",
        "history_id",
        "source_gate_schema_version",
        "source_gate_static_fingerprint",
        "source_gate_implementation_sha256",
        "anchor_gate_hash",
        "anchor_asset_hash",
        "expected_study_identity_hash",
        "expected_window_order_hash",
        "expected_replay_registry_id",
        "expected_replay_registry_namespace",
        "expected_persistence_configuration_hash",
        "anchor_checkpoint_tree_size",
        "final_checkpoint_tree_size",
        "expected_segment_count",
        "checkpoint_tree_step",
        "registered_at_utc",
        "future_coverage_not_before_utc",
        "future_coverage_not_after_utc",
        "max_future_asset_time_gap_seconds",
        "checkpoint_sequence_policy",
        "segment_sequence_policy",
        "asset_handoff_policy",
        "identity_stability_policy",
        "time_policy",
    }
)
_ITEM_FIELDS = frozenset(
    {"gate_document", "current_segment", "previous_segment", "expected_gate_hash"}
)
_EXACT_REGISTRATION_FIELDS = {
    "schema_version": REGISTRATION_SCHEMA_VERSION,
    "source_gate_schema_version": source_contract.SCHEMA_VERSION,
    "source_gate_static_fingerprint": source_contract.STATIC_FINGERPRINT,
    "source_gate_implementation_sha256": SOURCE_IMPLEMENTATION_SHA256,
    "checkpoint_tree_step": 1,
    "checkpoint_sequence_policy": CHECKPOINT_SEQUENCE_POLICY,
    "segment_sequence_policy": SEGMENT_SEQUENCE_POLICY,
    "asset_handoff_policy": ASSET_HANDOFF_POLICY,
    "identity_stability_policy": IDENTITY_STABILITY_POLICY,
    "time_policy": TIME_POLICY,
}
GATE_CONTRACT_HASH = hashlib.sha256(
    (
        GATE_SCHEMA_VERSION
        + "|"
        + REGISTRATION_SCHEMA_VERSION
        + "|"
        + source_contract.SCHEMA_VERSION
        + "|"
        + SOURCE_IMPLEMENTATION_SHA256
        + "|"
        + CHECKPOINT_SEQUENCE_POLICY
        + "|"
        + SEGMENT_SEQUENCE_POLICY
        + "|"
        + ASSET_HANDOFF_POLICY
        + "|"
        + IDENTITY_STABILITY_POLICY
        + "|"
        + TIME_POLICY
    ).encode("ascii")
).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "authoritative_future_pin_allowed": False,
        "candidate_activation_allowed": False,
        "complete_history_claim_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "durable_checkpoint_claim_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "persistence_provider_use_allowed": False,
        "profitability_claim_allowed": False,
        "writer_allowed": False,
    }


def _activation_blockers() -> list[str]:
    return [
        "UNMOUNTED_CANDIDATE",
        "EXTERNAL_PERSISTENCE_PROVIDER_AUTHORITY_UNPROVEN",
        "REAL_STORAGE_DURABILITY_UNPROVEN",
        "AUTHORITATIVE_FUTURE_PIN_UNPROVEN",
        "COMPLETE_PERSISTED_CHECKPOINT_HISTORY_UNPROVEN",
        "OUTSIDE_REGISTERED_WINDOW_COVERAGE_UNPROVEN",
        "LONGITUDINAL_EXTERNAL_COVERAGE_UNPROVEN",
        "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
        "PAPER_LIVE_UNAUTHORIZED",
    ]


def _registration_facts() -> dict[str, bool]:
    return {
        "registration_shape_verified": False,
        "source_contract_pinned": False,
        "anchor_gate_and_asset_pinned": False,
        "future_checkpoint_window_preregistered": False,
        "lineage_items_observed": False,
        "external_persistence_provider_authority_verified": False,
        "real_storage_durability_verified": False,
    }


def _registration_evidence() -> dict[str, Any]:
    return {
        "history_id": None,
        "anchor_gate_hash": None,
        "anchor_asset_hash": None,
        "expected_study_identity_hash": None,
        "expected_window_order_hash": None,
        "expected_replay_registry_id": None,
        "expected_replay_registry_namespace": None,
        "expected_persistence_configuration_hash": None,
        "anchor_checkpoint_tree_size": None,
        "final_checkpoint_tree_size": None,
        "expected_segment_count": None,
        "registered_at_utc": None,
        "future_coverage_not_before_utc": None,
        "future_coverage_not_after_utc": None,
        "max_future_asset_time_gap_seconds": None,
    }


def _gate_facts() -> dict[str, bool]:
    return {
        "coverage_registration_verified": False,
        "source_lineage_gates_reverified": False,
        "registered_anchor_exact": False,
        "preregistered_history_window_complete": False,
        "checkpoint_tree_sequence_contiguous": False,
        "segment_handoffs_exact": False,
        "asset_hash_chain_exact": False,
        "registered_identities_stable": False,
        "future_asset_times_bounded": False,
        "preregistered_bounded_history_prefix_verified": False,
        "bounded_history_prefix_only": False,
        "complete_persisted_checkpoint_history_verified": False,
        "outside_registered_window_coverage_verified": False,
        "authoritative_future_pin_verified": False,
        "durable_checkpoint_publication_verified": False,
        "external_persistence_provider_authority_verified": False,
        "paper_authorized": False,
        "profitability_proven": False,
        "runtime_mutations_performed": False,
        "synthetic_only": True,
    }


def _gate_source() -> dict[str, Any]:
    return {
        "coverage_registration_receipt_hash": None,
        "history_id": None,
        "source_lineage_gate_implementation_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "anchor_gate_hash": None,
        "last_gate_hash": None,
        "anchor_asset_hash": None,
        "last_asset_hash": None,
        "study_identity_hash": None,
        "window_order_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "persistence_configuration_hash": None,
    }


def _gate_summary() -> dict[str, Any]:
    return {
        "verified_segment_count": None,
        "anchor_checkpoint_tree_size": None,
        "final_checkpoint_tree_size": None,
        "maximum_observed_future_asset_time_gap_seconds": None,
    }


def _sealed_registration(
    *,
    status: str,
    reason_code: str | None,
    facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": REGISTRATION_RECEIPT_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason_code": reason_code,
            "facts": facts or _registration_facts(),
            "evidence": evidence or _registration_evidence(),
            "authority": _authority(),
        },
        "registration_receipt_hash",
    )


def _sealed_gate(
    *,
    status: str,
    reason_code: str,
    gate_blockers: list[str],
    facts: dict[str, bool] | None = None,
    source: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": GATE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason_code": reason_code,
            "facts": facts or _gate_facts(),
            "source": source or _gate_source(),
            "summary": summary or _gate_summary(),
            "gate_blockers": gate_blockers,
            "activation_blockers": _activation_blockers(),
            "authority": _authority(),
            "gate_contract_hash": GATE_CONTRACT_HASH,
        },
        "gate_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed_gate(
        status=UNKNOWN_STATUS,
        reason_code=f"UNKNOWN_{reason.upper()}",
        gate_blockers=[reason],
    )


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _strict_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = 2**63 - 1) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _utc_second(value: Any) -> int | None:
    if type(value) is not str or _UTC_SECOND.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    return int(parsed.timestamp())


def canonical_value_sha256_v1(value: Any) -> str | None:
    try:
        return seal_strict_canonical_document(
            {"value": value}, "value_sha256"
        )["value_sha256"]
    except (KeyError, TypeError, ValueError):
        return None


def _validate_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict:
        return None, "registration_shape_invalid"
    if set(value) != _REGISTRATION_FIELDS:
        return None, "registration_fields_invalid"
    for field, expected in _EXACT_REGISTRATION_FIELDS.items():
        if value.get(field) != expected or type(value.get(field)) is not type(expected):
            return None, f"registration_{field}_invalid"
    for field in (
        "history_id",
        "expected_replay_registry_id",
        "expected_replay_registry_namespace",
    ):
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    for field in (
        "anchor_gate_hash",
        "anchor_asset_hash",
        "expected_study_identity_hash",
        "expected_window_order_hash",
        "expected_persistence_configuration_hash",
    ):
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    count = value.get("expected_segment_count")
    anchor_size = value.get("anchor_checkpoint_tree_size")
    final_size = value.get("final_checkpoint_tree_size")
    if not _strict_int(count, minimum=MIN_SEGMENTS, maximum=MAX_SEGMENTS):
        return None, "registration_expected_segment_count_invalid"
    if not _strict_int(anchor_size, minimum=1):
        return None, "registration_anchor_checkpoint_tree_size_invalid"
    if not _strict_int(final_size, minimum=anchor_size + MIN_SEGMENTS - 1):
        return None, "registration_final_checkpoint_tree_size_invalid"
    if final_size != anchor_size + count - 1:
        return None, "registration_segment_count_range_mismatch"
    max_gap = value.get("max_future_asset_time_gap_seconds")
    if not _strict_int(max_gap, minimum=1, maximum=MAX_ASSET_TIME_GAP_SECONDS):
        return None, "registration_max_future_asset_time_gap_seconds_invalid"
    registered = _utc_second(value.get("registered_at_utc"))
    not_before = _utc_second(value.get("future_coverage_not_before_utc"))
    not_after = _utc_second(value.get("future_coverage_not_after_utc"))
    if registered is None:
        return None, "registration_registered_at_utc_invalid"
    if not_before is None:
        return None, "registration_future_coverage_not_before_utc_invalid"
    if not_after is None:
        return None, "registration_future_coverage_not_after_utc_invalid"
    if not registered < not_before <= not_after:
        return None, "registration_future_coverage_time_order_invalid"
    return value, None


def build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    clean, reason = _validate_registration(registration)
    if clean is None:
        return _sealed_registration(status=UNKNOWN_STATUS, reason_code=reason)
    facts = _registration_facts()
    facts.update(
        {
            "registration_shape_verified": True,
            "source_contract_pinned": True,
            "anchor_gate_and_asset_pinned": True,
            "future_checkpoint_window_preregistered": True,
        }
    )
    evidence = _registration_evidence()
    for field in evidence:
        evidence[field] = clean[field]
    return _sealed_registration(
        status=REGISTERED_STATUS,
        reason_code=None,
        facts=facts,
        evidence=evidence,
    )


def verify_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
    receipt: Any,
    *,
    registration: Any,
) -> bool:
    return type(receipt) is dict and receipt == build_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
        registration
    )


def evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    lineage_items: Any,
) -> dict[str, Any]:
    clean_registration, registration_reason = _validate_registration(registration)
    if clean_registration is None:
        return _unknown(registration_reason or "coverage_registration_invalid")
    if not verify_strategy_correlation_persisted_checkpoint_history_coverage_registration_v1(
        registration_receipt,
        registration=clean_registration,
    ):
        return _unknown("coverage_registration_unverified")
    if registration_receipt.get("status") != REGISTERED_STATUS:
        return _unknown("coverage_registration_not_registered")
    if type(lineage_items) is not list or len(lineage_items) != clean_registration[
        "expected_segment_count"
    ]:
        return _unknown("lineage_item_count_mismatch")

    registered_at = _utc_second(clean_registration["registered_at_utc"])
    future_not_before = _utc_second(
        clean_registration["future_coverage_not_before_utc"]
    )
    future_not_after = _utc_second(
        clean_registration["future_coverage_not_after_utc"]
    )
    if registered_at is None or future_not_before is None or future_not_after is None:
        return _unknown("coverage_registration_time_invalid")

    normalized: list[dict[str, Any]] = []
    gate_hashes: set[str] = set()
    asset_hashes: set[str] = set()
    previous_asset_time: int | None = None
    maximum_gap = 0

    for index, item in enumerate(lineage_items):
        if type(item) is not dict or set(item) != _ITEM_FIELDS:
            return _unknown(f"item_{index}_shape_invalid")
        gate = item.get("gate_document")
        current_segment = item.get("current_segment")
        previous_segment = item.get("previous_segment")
        expected_gate_hash = item.get("expected_gate_hash")
        if type(gate) is not dict or type(current_segment) is not dict:
            return _unknown(f"item_{index}_payload_shape_invalid")
        if not _strict_hash(expected_gate_hash):
            return _unknown(f"item_{index}_expected_gate_hash_invalid")
        try:
            source_verified = source_contract.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
                gate,
                current_segment,
                previous_segment,
                expected_gate_hash=expected_gate_hash,
            )
        except (KeyError, TypeError, ValueError):
            source_verified = False
        if not source_verified:
            return _unknown(f"item_{index}_source_lineage_gate_unverified")
        if gate.get("schema_version") != clean_registration["source_gate_schema_version"]:
            return _unknown(f"item_{index}_source_gate_schema_mismatch")
        if gate.get("static_fingerprint") != clean_registration[
            "source_gate_static_fingerprint"
        ]:
            return _unknown(f"item_{index}_source_gate_fingerprint_mismatch")
        if gate.get("status") != PASS_STATUS or gate.get("reason_code") != SOURCE_PASS_REASON:
            return _unknown(f"item_{index}_source_gate_not_pass")
        if gate.get("gate_hash") != expected_gate_hash:
            return _unknown(f"item_{index}_source_gate_hash_mismatch")
        authority = gate.get("authority")
        facts = gate.get("facts")
        source = gate.get("source")
        summary = gate.get("summary")
        persistence_inputs = current_segment.get("persistence_inputs")
        if not all(
            type(value) is dict
            for value in (
                authority,
                facts,
                source,
                summary,
                persistence_inputs,
            )
        ):
            return _unknown(f"item_{index}_source_nested_shape_invalid")
        if not authority or any(value is not False for value in authority.values()):
            return _unknown(f"item_{index}_source_authority_not_negative")
        if facts.get("complete_persisted_checkpoint_history_verified") is not False:
            return _unknown(f"item_{index}_source_complete_history_must_remain_false")
        if facts.get("runtime_mutations_performed") is not False or facts.get(
            "synthetic_only"
        ) is not True:
            return _unknown(f"item_{index}_source_not_synthetic_read_only")
        checkpoint_asset = persistence_inputs.get("checkpoint_asset")
        persistence_configuration = persistence_inputs.get("persistence_configuration")
        if type(checkpoint_asset) is not dict or type(persistence_configuration) is not dict:
            return _unknown(f"item_{index}_persistence_payload_shape_invalid")

        current_asset_hash = source.get("current_asset_hash")
        previous_asset_hash = source.get("previous_asset_hash")
        current_tree_size = summary.get("current_checkpoint_tree_size")
        previous_tree_size = summary.get("previous_checkpoint_tree_size")
        expected_tree_size = clean_registration["anchor_checkpoint_tree_size"] + index
        asset_time = _utc_second(checkpoint_asset.get("asset_created_at_utc"))
        configuration_hash = canonical_value_sha256_v1(persistence_configuration)
        if not _strict_hash(current_asset_hash):
            return _unknown(f"item_{index}_current_asset_hash_invalid")
        if checkpoint_asset.get("asset_hash") != current_asset_hash or persistence_inputs.get(
            "expected_asset_hash"
        ) != current_asset_hash:
            return _unknown(f"item_{index}_current_asset_binding_mismatch")
        if not _strict_int(current_tree_size, minimum=1) or current_tree_size != expected_tree_size:
            return _unknown(f"item_{index}_checkpoint_tree_sequence_mismatch")
        if asset_time is None:
            return _unknown(f"item_{index}_asset_created_at_utc_invalid")
        if source.get("study_identity_hash") != clean_registration[
            "expected_study_identity_hash"
        ]:
            return _unknown(f"item_{index}_study_identity_drift")
        if source.get("window_order_hash") != clean_registration[
            "expected_window_order_hash"
        ]:
            return _unknown(f"item_{index}_window_order_drift")
        if checkpoint_asset.get("source_replay_registry_id") != clean_registration[
            "expected_replay_registry_id"
        ]:
            return _unknown(f"item_{index}_replay_registry_id_drift")
        if checkpoint_asset.get("source_replay_registry_namespace") != clean_registration[
            "expected_replay_registry_namespace"
        ]:
            return _unknown(f"item_{index}_replay_registry_namespace_drift")
        if configuration_hash != clean_registration[
            "expected_persistence_configuration_hash"
        ]:
            return _unknown(f"item_{index}_persistence_configuration_drift")
        if source.get("persistence_binding_v1_implementation_sha256") != (
            "7dcdca13d6d658dc9963d5cc5f4dea47575d42305831dfbe301a4db6ee90e522"
        ):
            return _unknown(f"item_{index}_persistence_binding_source_drift")
        if expected_gate_hash in gate_hashes:
            return _unknown("source_gate_hash_reused")
        if current_asset_hash in asset_hashes:
            return _unknown("current_asset_hash_reused")
        gate_hashes.add(expected_gate_hash)
        asset_hashes.add(current_asset_hash)

        if index == 0:
            if previous_segment is not None or gate.get("lineage_mode") != "REGISTERED_SOURCE_PIN":
                return _unknown("registered_anchor_mode_invalid")
            if previous_asset_hash is not None or checkpoint_asset.get(
                "previous_persisted_asset_hash"
            ) is not None:
                return _unknown("registered_anchor_previous_asset_not_null")
            if expected_gate_hash != clean_registration["anchor_gate_hash"]:
                return _unknown("registered_anchor_gate_hash_mismatch")
            if current_asset_hash != clean_registration["anchor_asset_hash"]:
                return _unknown("registered_anchor_asset_hash_mismatch")
            if asset_time > registered_at:
                return _unknown("registered_anchor_created_after_registration")
        else:
            previous = normalized[index - 1]
            if previous_segment != previous["current_segment"]:
                return _unknown("segment_handoff_mismatch")
            if gate.get("lineage_mode") != "PREVIOUS_PERSISTED_ASSET":
                return _unknown(f"item_{index}_previous_asset_mode_invalid")
            if previous_asset_hash != previous["current_asset_hash"] or checkpoint_asset.get(
                "previous_persisted_asset_hash"
            ) != previous["current_asset_hash"]:
                return _unknown("asset_hash_handoff_mismatch")
            if previous_tree_size != previous["current_tree_size"]:
                return _unknown("checkpoint_tree_handoff_mismatch")
            if not future_not_before <= asset_time <= future_not_after:
                return _unknown(f"item_{index}_outside_preregistered_future_window")
            if previous_asset_time is None or asset_time <= previous_asset_time:
                return _unknown("asset_time_not_strictly_increasing")
            gap = asset_time - previous_asset_time
            if gap > clean_registration["max_future_asset_time_gap_seconds"]:
                return _unknown("asset_time_gap_exceeds_registration")
            maximum_gap = max(maximum_gap, gap)

        previous_asset_time = asset_time
        normalized.append(
            {
                "gate": gate,
                "current_segment": current_segment,
                "current_asset_hash": current_asset_hash,
                "current_tree_size": current_tree_size,
            }
        )

    first = normalized[0]
    last = normalized[-1]
    facts = _gate_facts()
    facts.update(
        {
            "coverage_registration_verified": True,
            "source_lineage_gates_reverified": True,
            "registered_anchor_exact": True,
            "preregistered_history_window_complete": True,
            "checkpoint_tree_sequence_contiguous": True,
            "segment_handoffs_exact": True,
            "asset_hash_chain_exact": True,
            "registered_identities_stable": True,
            "future_asset_times_bounded": True,
            "preregistered_bounded_history_prefix_verified": True,
            "bounded_history_prefix_only": True,
        }
    )
    source = _gate_source()
    source.update(
        {
            "coverage_registration_receipt_hash": registration_receipt[
                "registration_receipt_hash"
            ],
            "history_id": clean_registration["history_id"],
            "anchor_gate_hash": first["gate"]["gate_hash"],
            "last_gate_hash": last["gate"]["gate_hash"],
            "anchor_asset_hash": first["current_asset_hash"],
            "last_asset_hash": last["current_asset_hash"],
            "study_identity_hash": clean_registration["expected_study_identity_hash"],
            "window_order_hash": clean_registration["expected_window_order_hash"],
            "replay_registry_id": clean_registration["expected_replay_registry_id"],
            "replay_registry_namespace": clean_registration[
                "expected_replay_registry_namespace"
            ],
            "persistence_configuration_hash": clean_registration[
                "expected_persistence_configuration_hash"
            ],
        }
    )
    summary = _gate_summary()
    summary.update(
        {
            "verified_segment_count": len(normalized),
            "anchor_checkpoint_tree_size": first["current_tree_size"],
            "final_checkpoint_tree_size": last["current_tree_size"],
            "maximum_observed_future_asset_time_gap_seconds": maximum_gap,
        }
    )
    return _sealed_gate(
        status=PASS_STATUS,
        reason_code=PASS_REASON,
        gate_blockers=[],
        facts=facts,
        source=source,
        summary=summary,
    )


def verify_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
    document: Any,
    *,
    registration: Any,
    registration_receipt: Any,
    lineage_items: Any,
    expected_gate_hash: Any,
) -> bool:
    if type(document) is not dict or not _strict_hash(expected_gate_hash):
        return False
    if document.get("gate_hash") != expected_gate_hash:
        return False
    try:
        expected = evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=registration,
            registration_receipt=registration_receipt,
            lineage_items=lineage_items,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected
