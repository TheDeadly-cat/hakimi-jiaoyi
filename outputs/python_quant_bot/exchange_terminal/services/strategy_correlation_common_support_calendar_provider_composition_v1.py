from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Any

from . import strategy_correlation_common_support_derivation_receipt_v1 as derivation
from . import strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as calendar_source
from . import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as provider_source
from .execution_authority import authority_violations


SCHEMA_VERSION = "strategy-correlation-common-support-calendar-provider-composition-v1"
STATIC_FINGERPRINT = "20260822-strategy-correlation-common-support-calendar-provider-composition-1"
COMPOSITION_STATE = (
    "LOCAL_COMMON_SUPPORT_CALENDAR_SESSIONS_AND_PROVIDER_IDENTITY_CLAIM_BOUND_"
    "EXTERNAL_TRUST_UNPROVEN"
)
CALENDAR_ALIGNMENT_POLICY = (
    "ADR_COMMON_PRICE_INDEX_EQUALS_VERIFIED_BATCH_CONTIGUOUS_SUFFIX"
)
DATASET_PROVIDER_BINDING_POLICY = (
    "EXACT_DATASET_SOURCE_LABEL_EQUALS_VERIFIED_PROVIDER_ID"
)

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_CALENDAR_BUNDLE_KEYS = {
    "calendar_registration_v1",
    "calendar_registration_verification_context",
    "batch_verification_v1",
    "batch_verification_context",
    "observation_batch",
    "expected_calendar_registration_hash",
    "expected_batch_verification_hash",
}
_PROVIDER_BUNDLE_KEYS = {
    "provider_identity_registration_v1",
    "provider_identity_registration_verification_context",
    "identity_assertion_receipt",
    "expected_provider_identity_registration_hash",
    "expected_identity_assertion_hash",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _verification(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "BLOCK" if blockers else "PASS",
        "blockers": sorted(set(blockers)),
    }


def _valid_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_date(value: Any) -> str:
    if type(value) is not str or value != value.strip() or not value:
        raise ValueError("calendar_observation_date_invalid")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("calendar_observation_date_invalid") from error
    if parsed.isoformat() != value:
        raise ValueError("calendar_observation_date_invalid")
    return value


def _calendar_source_verified(document: Any, bundle: Any) -> bool:
    if type(bundle) is not dict or set(bundle) != _CALENDAR_BUNDLE_KEYS:
        return False
    if not _valid_sha256(bundle.get("expected_calendar_registration_hash")):
        return False
    if not _valid_sha256(bundle.get("expected_batch_verification_hash")):
        return False
    try:
        return calendar_source.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
            document,
            bundle["calendar_registration_v1"],
            bundle["calendar_registration_verification_context"],
            bundle["batch_verification_v1"],
            bundle["batch_verification_context"],
            bundle["observation_batch"],
            expected_calendar_registration_hash=bundle[
                "expected_calendar_registration_hash"
            ],
            expected_batch_verification_hash=bundle[
                "expected_batch_verification_hash"
            ],
        )
    except (KeyError, MemoryError, RecursionError, TypeError, ValueError):
        return False


def _provider_source_verified(document: Any, bundle: Any) -> bool:
    if type(bundle) is not dict or set(bundle) != _PROVIDER_BUNDLE_KEYS:
        return False
    if not _valid_sha256(bundle.get("expected_provider_identity_registration_hash")):
        return False
    if not _valid_sha256(bundle.get("expected_identity_assertion_hash")):
        return False
    try:
        return provider_source.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
            document,
            bundle["provider_identity_registration_v1"],
            bundle["provider_identity_registration_verification_context"],
            bundle["identity_assertion_receipt"],
            expected_provider_identity_registration_hash=bundle[
                "expected_provider_identity_registration_hash"
            ],
            expected_identity_assertion_hash=bundle[
                "expected_identity_assertion_hash"
            ],
        )
    except (KeyError, MemoryError, RecursionError, TypeError, ValueError):
        return False


def _derive_common_price_index(
    matrix_replay: dict[str, Any],
    derivation_receipt: dict[str, Any],
) -> list[str]:
    datasets = matrix_replay["completed_price_input"]["datasets"]
    date_sets = [
        {row["date"] for row in dataset["price_rows"]}
        for dataset in datasets
    ]
    if not date_sets:
        raise ValueError("composition_dataset_coverage_invalid")
    common_price_index = sorted(set.intersection(*date_sets))[
        -derivation.MAXIMUM_COMMON_PRICE_ROWS:
    ]
    if (
        len(common_price_index) != derivation_receipt["common_price_row_count"]
        or _sha256(common_price_index)
        != derivation_receipt["common_price_index_hash"]
        or _sha256(common_price_index[1:])
        != derivation_receipt["common_observation_index_hash"]
    ):
        raise ValueError("composition_common_price_index_mismatch")
    return common_price_index


def _calendar_alignment(
    symbols: list[str],
    common_price_index: list[str],
    calendar_session_verification: dict[str, Any],
    calendar_verification_bundle: dict[str, Any],
) -> dict[str, Any]:
    batch = calendar_verification_bundle["observation_batch"]
    registration = calendar_verification_bundle["calendar_registration_v1"]
    if type(batch) is not dict or type(registration) is not dict:
        raise ValueError("calendar_composition_bundle_invalid")
    rows = batch.get("rows")
    if type(rows) is not list or not rows:
        raise ValueError("calendar_composition_rows_invalid")
    batch_dates: list[str] = []
    for row in rows:
        if type(row) is not dict or type(row.get("returns")) is not dict:
            raise ValueError("calendar_composition_row_invalid")
        batch_dates.append(_canonical_date(row.get("observation_date")))
        if sorted(row["returns"]) != symbols:
            raise ValueError("calendar_composition_identity_mismatch")
    if batch_dates != sorted(set(batch_dates)):
        raise ValueError("calendar_composition_date_topology_invalid")
    if (
        len(batch_dates) < len(common_price_index)
        or batch_dates[-len(common_price_index):] != common_price_index
    ):
        raise ValueError("calendar_common_price_suffix_mismatch")
    if (
        batch.get("observation_batch_hash")
        != calendar_session_verification.get("observation_batch_hash")
        or calendar_session_verification.get("row_count") != len(batch_dates)
        or calendar_session_verification.get("session_check_count") != len(batch_dates)
        or calendar_session_verification.get("completed_common_session_count")
        != len(batch_dates)
        or calendar_session_verification.get("first_observation_date")
        != batch_dates[0]
        or calendar_session_verification.get("last_observation_date")
        != batch_dates[-1]
    ):
        raise ValueError("calendar_composition_summary_mismatch")

    assignments = registration.get("identity_calendar_assignments")
    distinct_calendar_ids = registration.get("distinct_calendar_ids")
    if type(assignments) is not list or len(assignments) != len(symbols):
        raise ValueError("calendar_composition_assignment_invalid")
    normalized_assignments: list[dict[str, Any]] = []
    calendar_ids: list[str] = []
    for expected_index, assignment in enumerate(assignments):
        if type(assignment) is not dict or set(assignment) != {
            "identity_index",
            "calendar_id",
        }:
            raise ValueError("calendar_composition_assignment_invalid")
        calendar_id = assignment["calendar_id"]
        if (
            type(assignment["identity_index"]) is not int
            or assignment["identity_index"] != expected_index
            or type(calendar_id) is not str
            or not calendar_id
            or calendar_id != calendar_id.strip()
        ):
            raise ValueError("calendar_composition_assignment_invalid")
        calendar_ids.append(calendar_id)
        normalized_assignments.append({
            "identity_index": expected_index,
            "symbol_hash": _sha256(symbols[expected_index]),
            "calendar_id_hash": _sha256(calendar_id),
        })
    if (
        type(distinct_calendar_ids) is not list
        or distinct_calendar_ids != sorted(set(calendar_ids))
        or calendar_session_verification.get("identity_count") != len(symbols)
        or calendar_session_verification.get("distinct_calendar_count")
        != len(distinct_calendar_ids)
    ):
        raise ValueError("calendar_composition_assignment_summary_mismatch")
    return {
        "batch_dates": batch_dates,
        "normalized_assignments": normalized_assignments,
        "distinct_calendar_count": len(distinct_calendar_ids),
    }


def _require_source_facts(
    calendar_session_verification: dict[str, Any],
    provider_identity_verification: dict[str, Any],
) -> None:
    calendar_facts = calendar_session_verification.get("facts")
    provider_facts = provider_identity_verification.get("facts")
    calendar_authority = calendar_session_verification.get("authority")
    provider_authority = provider_identity_verification.get("authority")
    if (
        type(calendar_facts) is not dict
        or type(provider_facts) is not dict
        or type(calendar_authority) is not dict
        or type(provider_authority) is not dict
    ):
        raise ValueError("composition_source_facts_invalid")
    calendar_required_false = {
        "calendar_enforcement_activated",
        "candidate_activation_allowed",
        "current_admission_allowed",
        "current_pointer_written",
        "future_evaluation_allowed",
        "live_order_allowed",
        "observation_admission_allowed",
        "paper_authorized",
        "profitability_claim_allowed",
    }
    provider_required_false = {
        "candidate_activation_allowed",
        "current_admission_allowed",
        "current_pointer_written",
        "external_provider_identity_verified",
        "future_evaluation_allowed",
        "identity_assertion_use_allowed",
        "live_order_allowed",
        "paper_authorized",
        "profitability_claim_allowed",
        "provider_identity_admission_allowed",
    }
    if (
        any(calendar_authority.get(key) is not False for key in calendar_required_false)
        or any(provider_authority.get(key) is not False for key in provider_required_false)
    ):
        raise ValueError("composition_execution_authority_invalid")
    calendar_required_true = {
        "calendar_registration_verified",
        "source_batch_verified",
        "schedule_cross_binding_verified",
        "calendar_sessions_evaluated",
        "common_session_intersection_verified",
        "all_registered_sessions_completed",
    }
    provider_required_true = {
        "source_registration_verified",
        "source_bindings_verified",
        "assertion_receipt_seal_verified",
        "assertion_content_hash_verified",
        "identity_registry_key_match",
        "identity_registry_signature_verified",
        "snapshot_membership_verified",
        "assertion_chronology_claim_valid",
    }
    if any(calendar_facts.get(key) is not True for key in calendar_required_true):
        raise ValueError("calendar_composition_source_fact_missing")
    if any(provider_facts.get(key) is not True for key in provider_required_true):
        raise ValueError("provider_composition_source_fact_missing")
    if (
        calendar_facts.get("external_provider_identity_verified") is not False
        or calendar_facts.get("observation_admission_allowed") is not False
        or provider_facts.get("provider_identity_verified") is not False
        or provider_facts.get("external_identity_registry_authenticity_proven")
        is not False
    ):
        raise ValueError("composition_source_truth_promotion_invalid")


def build_correlation_common_support_calendar_provider_composition_v1(
    derivation_receipt: dict[str, Any],
    matrix_replay: dict[str, Any],
    calendar_session_verification: dict[str, Any],
    calendar_verification_bundle: dict[str, Any],
    provider_identity_verification: dict[str, Any],
    provider_verification_bundle: dict[str, Any],
) -> dict[str, Any]:
    if _authority_invalid([
        derivation_receipt,
        matrix_replay,
        calendar_session_verification,
        calendar_verification_bundle,
        provider_identity_verification,
        provider_verification_bundle,
    ]):
        raise ValueError("composition_execution_authority_invalid")
    derivation_check = derivation.verify_correlation_common_support_derivation_receipt_v1(
        derivation_receipt,
        matrix_replay=matrix_replay,
    )
    if derivation_check["status"] != "PASS":
        raise ValueError("composition_derivation_receipt_invalid")
    if not _calendar_source_verified(
        calendar_session_verification,
        calendar_verification_bundle,
    ):
        raise ValueError("composition_calendar_source_invalid")
    if not _provider_source_verified(
        provider_identity_verification,
        provider_verification_bundle,
    ):
        raise ValueError("composition_provider_source_invalid")
    if (
        calendar_session_verification.get("schema_version")
        != calendar_source.SCHEMA_VERSION
        or calendar_session_verification.get("static_fingerprint")
        != calendar_source.STATIC_FINGERPRINT
        or calendar_session_verification.get("source_state") != "VERIFIED"
        or provider_identity_verification.get("schema_version")
        != provider_source.SCHEMA_VERSION
        or provider_identity_verification.get("static_fingerprint")
        != provider_source.STATIC_FINGERPRINT
        or provider_identity_verification.get("source_state") != "VERIFIED"
    ):
        raise ValueError("composition_source_contract_mismatch")
    _require_source_facts(
        calendar_session_verification,
        provider_identity_verification,
    )

    symbols = sorted(matrix_replay["preregistration"]["symbols"])
    common_price_index = _derive_common_price_index(
        matrix_replay,
        derivation_receipt,
    )
    calendar_alignment = _calendar_alignment(
        symbols,
        common_price_index,
        calendar_session_verification,
        calendar_verification_bundle,
    )

    provider_id = provider_identity_verification.get("provider_id")
    provider_registration = provider_verification_bundle[
        "provider_identity_registration_v1"
    ]
    identity_receipt = provider_verification_bundle["identity_assertion_receipt"]
    if (
        type(provider_id) is not str
        or not provider_id
        or provider_id != provider_id.strip()
        or calendar_session_verification.get("provider_id") != provider_id
        or type(provider_registration) is not dict
        or provider_registration.get("provider_id") != provider_id
        or type(identity_receipt) is not dict
        or identity_receipt.get("provider_id") != provider_id
        or calendar_session_verification.get("future_evaluation_id")
        != provider_identity_verification.get("future_evaluation_id")
    ):
        raise ValueError("composition_provider_identity_mismatch")

    datasets = matrix_replay["completed_price_input"]["datasets"]
    if [dataset["symbol"] for dataset in datasets] != symbols:
        raise ValueError("composition_dataset_order_mismatch")
    dataset_bindings: list[dict[str, str]] = []
    for dataset in datasets:
        if dataset.get("source") != provider_id:
            raise ValueError("composition_dataset_provider_label_mismatch")
        dataset_bindings.append({
            "symbol_hash": _sha256(dataset["symbol"]),
            "source_label_hash": _sha256(dataset["source"]),
            "dataset_data_hash": dataset["dataset_data_hash"],
            "dataset_manifest_hash": dataset["dataset_manifest_hash"],
        })

    batch_dates = calendar_alignment["batch_dates"]
    facts = {
        "source_derivation_receipt_verified": True,
        "calendar_session_source_verified": True,
        "calendar_common_session_intersection_verified": True,
        "calendar_price_suffix_exact": True,
        "calendar_identity_mapping_exact": True,
        "provider_identity_assertion_signature_and_membership_verified": True,
        "dataset_source_label_matches_provider_id": True,
        "dataset_content_attested_by_provider": False,
        "external_calendar_authority_verified": False,
        "external_provider_identity_verified": False,
        "observation_admission_allowed": False,
        "profitability_verified": False,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "composition_state": COMPOSITION_STATE,
        "calendar_alignment_policy": CALENDAR_ALIGNMENT_POLICY,
        "dataset_provider_binding_policy": DATASET_PROVIDER_BINDING_POLICY,
        "source_derivation_receipt_hash": derivation_receipt["receipt_hash"],
        "source_matrix_replay_hash": matrix_replay["replay_hash"],
        "source_completed_price_input_hash": matrix_replay[
            "completed_price_input"
        ]["input_hash"],
        "source_common_support_matrix_hash": derivation_receipt[
            "common_support_matrix_hash"
        ],
        "source_calendar_session_verification_hash": calendar_session_verification[
            "verification_hash"
        ],
        "source_calendar_session_evaluation_hash": calendar_session_verification[
            "calendar_session_evaluation_hash"
        ],
        "source_calendar_registration_hash": calendar_session_verification[
            "source_calendar_registration_hash"
        ],
        "source_calendar_observation_batch_hash": calendar_session_verification[
            "observation_batch_hash"
        ],
        "source_provider_identity_verification_hash": provider_identity_verification[
            "verification_hash"
        ],
        "source_provider_identity_registration_hash": provider_identity_verification[
            "source_provider_identity_registration_hash"
        ],
        "source_provider_identity_assertion_hash": provider_identity_verification[
            "assertion_hash"
        ],
        "source_provider_identity_document_hash": provider_identity_verification[
            "provider_identity_document_sha256"
        ],
        "provider_id_hash": _sha256(provider_id),
        "future_evaluation_id_hash": _sha256(
            calendar_session_verification["future_evaluation_id"]
        ),
        "common_price_row_count": len(common_price_index),
        "common_price_index_hash": derivation_receipt[
            "common_price_index_hash"
        ],
        "common_observation_count": derivation_receipt[
            "common_observation_count"
        ],
        "common_observation_index_hash": derivation_receipt[
            "common_observation_index_hash"
        ],
        "calendar_batch_session_count": len(batch_dates),
        "calendar_batch_date_index_hash": _sha256(batch_dates),
        "calendar_suffix_start_offset": len(batch_dates) - len(common_price_index),
        "symbol_count": len(symbols),
        "symbol_order_hash": _sha256(symbols),
        "calendar_assignment_hash": _sha256(
            calendar_alignment["normalized_assignments"]
        ),
        "distinct_calendar_count": calendar_alignment[
            "distinct_calendar_count"
        ],
        "dataset_count": len(dataset_bindings),
        "dataset_provider_binding_hash": _sha256(dataset_bindings),
        "facts": facts,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "composition_hash": _sha256(body)}


def verify_correlation_common_support_calendar_provider_composition_v1(
    document: Any,
    derivation_receipt: Any,
    matrix_replay: Any,
    calendar_session_verification: Any,
    calendar_verification_bundle: Any,
    provider_identity_verification: Any,
    provider_verification_bundle: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["calendar_provider_composition_invalid"])
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    try:
        rebuilt = build_correlation_common_support_calendar_provider_composition_v1(
            derivation_receipt,
            matrix_replay,
            calendar_session_verification,
            calendar_verification_bundle,
            provider_identity_verification,
            provider_verification_bundle,
        )
    except (
        ArithmeticError,
        KeyError,
        MemoryError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        blockers.append("calendar_provider_composition_source_invalid")
        return _verification(blockers)
    if document != rebuilt:
        blockers.append("calendar_provider_composition_semantic_mismatch")
    return _verification(blockers)


__all__ = [
    "CALENDAR_ALIGNMENT_POLICY",
    "COMPOSITION_STATE",
    "DATASET_PROVIDER_BINDING_POLICY",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_correlation_common_support_calendar_provider_composition_v1",
    "verify_correlation_common_support_calendar_provider_composition_v1",
]
