"""Bind ADR0351 windows to one common ADR0122 lifecycle-replay view.

This unmounted adapter delegates all signature, Merkle, consistency, scan,
cardinality, and freshness semantics to ADR0122. It verifies one exact replay
gate per ADR0351 window, requires a common registry/checkpoint/snapshot view,
and binds each distinct lifecycle receipt to a distinct leaf index. External
registry authority, durable publication, split-view absence, global
uniqueness, future replay absence, and trading authority remain unproven.
"""

from __future__ import annotations

from copy import deepcopy
from hmac import compare_digest
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1
    as lifecycle_replay_v1,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1
    as lifecycle_binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-binding-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-binding-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-observation-"
    "membership-provider-attestation-lifecycle-replay-binding-gate-v1-"
    "synthetic-unmounted-common-view-lock-1"
)
LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256 = (
    "4a86a2028dc6cc7976b361a62d50c3f6ec2837b8606555b53d1387e9b4790343"
)
LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256 = (
    "a34bdc06efe5c68e38955a4c7698c53587257f1cdd13482afd70f14a872a1c27"
)
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_ADR0351_PREREGISTRATION",
    "PREREGISTER_ONE_ADR0122_BINDING_PER_ADR0351_WINDOW",
    "REQUIRE_ONE_COMMON_REGISTRY_CHECKPOINT_AND_SCAN_VIEW",
    "REQUIRE_DISTINCT_LIFECYCLE_RECEIPTS_AND_LEAF_INDICES",
    "VERIFY_EXACT_ADR0351_GATE",
    "VERIFY_EXACT_ADR0122_GATE_PER_WINDOW",
    "BIND_REPLAY_RECEIPTS_TO_ADR0351_LIFECYCLE_RECEIPTS",
    "PRESERVE_ADR0351_BLOCK",
    "BIND_EXTERNAL_CONSISTENCY_OBSERVERS_AND_CONTENT_REPLAY_BEFORE_ACTIVATION",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_AUTHORITY = {
    "research_evidence_only": True,
    "current_admission_allowed": False,
    "effective_budget_activation_allowed": False,
    "http_registration_allowed": False,
    "runtime_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_BASE_ACTIVATION_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "EXTERNAL_REPLAY_REGISTRY_AUTHORITY_UNPROVEN",
    "EXTERNAL_OCCURRENCE_AUDITOR_AUTHORITY_UNPROVEN",
    "DURABLE_CHECKPOINT_PUBLICATION_UNPROVEN",
    "MULTI_OBSERVER_SPLIT_VIEW_GATE_NOT_BOUND",
    "GLOBAL_LIFECYCLE_RECEIPT_UNIQUENESS_UNPROVEN",
    "FUTURE_REPLAY_ABSENCE_UNPROVEN",
    "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
    "DURABLE_EXTERNAL_REGISTRY_UNPROVEN",
    "NO_EFFECTIVE_BUDGET_CONSUMER_BOUND",
    "PAPER_LIVE_UNAUTHORIZED",
)
_REPLAY_BUNDLE_FIELDS = frozenset(
    {
        "checkpoint",
        "consistency_proof",
        "inclusion_proof",
        "occurrence_audit",
        "occurrence_auditor_public_key_base64",
        "pinned_checkpoint",
        "replay_gate_document",
        "replay_registration",
        "replay_registry_public_key_base64",
        "window_id",
    }
)
_REPLAY_BINDING_FIELDS = frozenset(
    {
        "adapter_id",
        "adapter_implementation_hash",
        "audit_issued_at_utc",
        "checkpoint_hash",
        "checkpoint_issued_at_utc",
        "checkpoint_root_hash",
        "checkpoint_tree_size",
        "consistency_proof_hash",
        "declared_at_utc",
        "excluded_upstream_public_key_set_hash",
        "inclusion_proof_hash",
        "index_snapshot_record_count",
        "index_snapshot_root_hash",
        "lifecycle_receipt_hash",
        "lifecycle_verification_hash",
        "max_checkpoint_age_seconds",
        "max_occurrence_receipt_issue_delay_seconds",
        "max_scan_age_seconds",
        "occurrence_audit_hash",
        "occurrence_auditor_id",
        "occurrence_auditor_key_id",
        "occurrence_auditor_public_key_sha256",
        "occurrence_count_claim",
        "occurrence_leaf_index",
        "pinned_checkpoint_hash",
        "previous_checkpoint_hash",
        "previous_checkpoint_root_hash",
        "previous_checkpoint_tree_size",
        "reference_time_utc",
        "replay_registration_hash",
        "replay_registry_id",
        "replay_registry_key_id",
        "replay_registry_namespace",
        "replay_registry_public_key_sha256",
        "scan_completed_at_utc",
        "scan_end_index_exclusive",
        "scan_start_index",
        "window_id",
    }
)
_COMMON_VIEW_FIELDS = (
    "adapter_id",
    "adapter_implementation_hash",
    "audit_issued_at_utc",
    "checkpoint_issued_at_utc",
    "checkpoint_root_hash",
    "checkpoint_tree_size",
    "consistency_proof_hash",
    "declared_at_utc",
    "index_snapshot_record_count",
    "index_snapshot_root_hash",
    "max_checkpoint_age_seconds",
    "max_occurrence_receipt_issue_delay_seconds",
    "max_scan_age_seconds",
    "occurrence_auditor_id",
    "occurrence_auditor_key_id",
    "occurrence_auditor_public_key_sha256",
    "previous_checkpoint_hash",
    "previous_checkpoint_root_hash",
    "previous_checkpoint_tree_size",
    "reference_time_utc",
    "replay_registry_id",
    "replay_registry_key_id",
    "replay_registry_namespace",
    "replay_registry_public_key_sha256",
    "scan_completed_at_utc",
    "scan_end_index_exclusive",
    "scan_start_index",
)
_PREREGISTRATION_FIELDS = frozenset(
    {
        "activation_sequence",
        "authority",
        "common_registry_view_hash",
        "expected_replay_bindings",
        "expected_window_count",
        "expected_windows",
        "gate_contract_hash",
        "lifecycle_binding_preregistration_hash",
        "lifecycle_binding_v1_implementation_sha256",
        "lifecycle_replay_v1_implementation_sha256",
        "preregistration_hash",
        "registration_sequence",
        "schema_version",
        "static_fingerprint",
        "status",
        "study_identity_hash",
        "window_order_hash",
    }
)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _positive_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value >= 0


def _strict_id(value: Any) -> bool:
    return type(value) is str and bool(_ID_RE.fullmatch(value))


def _strict_timestamp(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _checkpoint_commitment(value: Any) -> bool:
    return value == lifecycle_replay_v1.GENESIS_COMMITMENT or _exact_hash(value)


def _sealed_document_valid(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _exact_hash(document.get(hash_field)):
        return False
    try:
        unsigned = deepcopy(document)
        unsigned.pop(hash_field)
        expected = seal_strict_canonical_document(unsigned, hash_field)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _lifecycle_preregistration_exact(
    document: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
) -> bool:
    if not all(
        type(value) is dict
        for value in (
            document,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
    ):
        return False
    try:
        expected = lifecycle_binding_v1.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_preregistration_v1(
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
            document.get("expected_lifecycle_bindings"),
            registration_sequence=document.get("registration_sequence"),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(expected) is dict
        and strict_json_contract_equal(document, expected)
    )


def _replay_binding_valid(value: Any) -> bool:
    if type(value) is not dict or frozenset(value) != _REPLAY_BINDING_FIELDS:
        return False
    hash_fields = {
        "adapter_implementation_hash",
        "checkpoint_hash",
        "checkpoint_root_hash",
        "consistency_proof_hash",
        "excluded_upstream_public_key_set_hash",
        "inclusion_proof_hash",
        "index_snapshot_root_hash",
        "lifecycle_receipt_hash",
        "lifecycle_verification_hash",
        "occurrence_audit_hash",
        "occurrence_auditor_public_key_sha256",
        "pinned_checkpoint_hash",
        "previous_checkpoint_root_hash",
        "replay_registration_hash",
        "replay_registry_public_key_sha256",
    }
    id_fields = {
        "adapter_id",
        "occurrence_auditor_id",
        "occurrence_auditor_key_id",
        "replay_registry_id",
        "replay_registry_key_id",
        "replay_registry_namespace",
        "window_id",
    }
    timestamp_fields = {
        "audit_issued_at_utc",
        "checkpoint_issued_at_utc",
        "declared_at_utc",
        "reference_time_utc",
        "scan_completed_at_utc",
    }
    positive_fields = {
        "checkpoint_tree_size",
        "index_snapshot_record_count",
        "max_checkpoint_age_seconds",
        "max_occurrence_receipt_issue_delay_seconds",
        "max_scan_age_seconds",
        "occurrence_count_claim",
        "scan_end_index_exclusive",
    }
    nonnegative_fields = {
        "occurrence_leaf_index",
        "previous_checkpoint_tree_size",
        "scan_start_index",
    }
    return bool(
        all(_exact_hash(value.get(field)) for field in hash_fields)
        and all(_strict_id(value.get(field)) for field in id_fields)
        and all(_strict_timestamp(value.get(field)) for field in timestamp_fields)
        and all(_positive_int(value.get(field)) for field in positive_fields)
        and all(_nonnegative_int(value.get(field)) for field in nonnegative_fields)
        and _checkpoint_commitment(value.get("previous_checkpoint_hash"))
        and value["occurrence_count_claim"] == 1
        and value["scan_start_index"] == 0
        and value["scan_end_index_exclusive"] == value["checkpoint_tree_size"]
        and value["index_snapshot_record_count"] == value["checkpoint_tree_size"]
        and value["occurrence_leaf_index"] < value["checkpoint_tree_size"]
    )


def _common_view(value: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(value[field]) for field in _COMMON_VIEW_FIELDS}


def _replay_bindings_valid(
    value: Any,
    windows: Any,
    lifecycle_rows: Any,
) -> bool:
    if (
        type(value) is not list
        or type(windows) is not list
        or type(lifecycle_rows) is not list
        or len(value) != len(windows)
        or len(lifecycle_rows) != len(windows)
        or not value
        or not all(_replay_binding_valid(row) for row in value)
        or [row["window_id"] for row in value] != windows
    ):
        return False
    for replay_row, lifecycle_row in zip(value, lifecycle_rows, strict=True):
        if (
            type(lifecycle_row) is not dict
            or replay_row["window_id"] != lifecycle_row.get("window_id")
            or replay_row["lifecycle_verification_hash"]
            != lifecycle_row.get("lifecycle_verification_hash")
            or replay_row["lifecycle_receipt_hash"]
            != lifecycle_row.get("lifecycle_governance_receipt_hash")
            or replay_row["reference_time_utc"]
            != lifecycle_row.get("reference_time_utc")
        ):
            return False
    for field in (
        "checkpoint_hash",
        "lifecycle_receipt_hash",
        "lifecycle_verification_hash",
        "occurrence_audit_hash",
        "occurrence_leaf_index",
        "pinned_checkpoint_hash",
        "replay_registration_hash",
    ):
        if len({row[field] for row in value}) != len(value):
            return False
    common = _common_view(value[0])
    if any(not strict_json_contract_equal(_common_view(row), common) for row in value):
        return False
    return len(value) <= value[0]["checkpoint_tree_size"]


_CONTRACT_MANIFEST = {
    "schema_version": GATE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contracts": {
        "adr0122": {
            "schema_version": lifecycle_replay_v1.SCHEMA_VERSION,
            "implementation_sha256": LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
        "adr0351": {
            "schema_version": lifecycle_binding_v1.GATE_SCHEMA_VERSION,
            "implementation_sha256": LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
    },
    "common_view_policy": (
        "ONE_REGISTRY_KEY_CHECKPOINT_ROOT_SCAN_SNAPSHOT_AND_REFERENCE_TIME"
    ),
    "cardinality_policy": "DISTINCT_RECEIPT_AND_LEAF_INDEX_PER_WINDOW",
    "external_registry_authority_claimed": False,
    "durable_publication_claimed": False,
    "split_view_absence_claimed": False,
    "global_uniqueness_claimed": False,
    "future_replay_absence_claimed": False,
    "content_issuance_replay_claimed": False,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_preregistration_v1(
    lifecycle_binding_preregistration: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    expected_replay_bindings: Any,
    *,
    registration_sequence: Any,
) -> dict[str, Any] | None:
    """Preregister one common-view ADR0122 binding for every ADR0351 window."""
    if (
        not _lifecycle_preregistration_exact(
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
        or not _positive_int(registration_sequence)
        or registration_sequence
        <= lifecycle_binding_preregistration["registration_sequence"]
    ):
        return None
    windows = lifecycle_binding_preregistration["expected_windows"]
    lifecycle_rows = lifecycle_binding_preregistration[
        "expected_lifecycle_bindings"
    ]
    if not _replay_bindings_valid(
        expected_replay_bindings,
        windows,
        lifecycle_rows,
    ):
        return None
    document = {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "authority": deepcopy(_AUTHORITY),
        "common_registry_view_hash": strict_canonical_hash(
            _common_view(expected_replay_bindings[0])
        ),
        "expected_replay_bindings": deepcopy(expected_replay_bindings),
        "expected_window_count": len(windows),
        "expected_windows": deepcopy(windows),
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "lifecycle_binding_preregistration_hash": (
            lifecycle_binding_preregistration["preregistration_hash"]
        ),
        "lifecycle_binding_v1_implementation_sha256": (
            LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256
        ),
        "lifecycle_replay_v1_implementation_sha256": (
            LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256
        ),
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "study_identity_hash": lifecycle_binding_preregistration[
            "study_identity_hash"
        ],
        "window_order_hash": lifecycle_binding_preregistration[
            "window_order_hash"
        ],
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def _preregistration_valid(document: Any) -> bool:
    return bool(
        type(document) is dict
        and frozenset(document) == _PREREGISTRATION_FIELDS
        and document.get("schema_version") == PREREGISTRATION_SCHEMA_VERSION
        and document.get("static_fingerprint") == STATIC_FINGERPRINT
        and document.get("status") == "PREREGISTERED_UNMOUNTED"
        and document.get("gate_contract_hash") == GATE_CONTRACT_HASH
        and document.get("authority") == _AUTHORITY
        and document.get("activation_sequence") == list(ACTIVATION_SEQUENCE)
        and document.get("lifecycle_binding_v1_implementation_sha256")
        == LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256
        and document.get("lifecycle_replay_v1_implementation_sha256")
        == LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256
        and _exact_hash(document.get("lifecycle_binding_preregistration_hash"))
        and _exact_hash(document.get("study_identity_hash"))
        and _exact_hash(document.get("window_order_hash"))
        and _exact_hash(document.get("common_registry_view_hash"))
        and _positive_int(document.get("registration_sequence"))
        and type(document.get("expected_windows")) is list
        and document.get("expected_window_count")
        == len(document.get("expected_windows", []))
        and document.get("window_order_hash")
        == strict_canonical_hash(document.get("expected_windows"))
        and _replay_bindings_valid(
            document.get("expected_replay_bindings"),
            document.get("expected_windows"),
            [
                {
                    "window_id": row.get("window_id"),
                    "lifecycle_verification_hash": row.get(
                        "lifecycle_verification_hash"
                    ),
                    "lifecycle_governance_receipt_hash": row.get(
                        "lifecycle_receipt_hash"
                    ),
                    "reference_time_utc": row.get("reference_time_utc"),
                }
                for row in document.get("expected_replay_bindings", [])
                if type(row) is dict
            ],
        )
        and document.get("common_registry_view_hash")
        == strict_canonical_hash(
            _common_view(document.get("expected_replay_bindings")[0])
        )
        and _sealed_document_valid(document, "preregistration_hash")
    )


def _facts(*, verified: bool) -> dict[str, Any]:
    return {
        "all_lifecycle_binding_windows_replay_bound": verified,
        "all_lifecycle_replay_gates_exactly_verified": verified,
        "common_registry_view_bound": verified,
        "complete_scan_claims_verified": verified,
        "content_issuance_replay_verified": False,
        "current_activated": False,
        "distinct_lifecycle_receipts_verified": verified,
        "distinct_occurrence_leaf_indices_verified": verified,
        "durable_checkpoint_publication_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "external_replay_registry_authority_verified": False,
        "future_replay_absence_verified": False,
        "global_lifecycle_receipt_uniqueness_verified": False,
        "historical_market_data_accessed": False,
        "lifecycle_receipt_replay_registry_checked": False,
        "multi_observer_split_view_absence_verified": False,
        "paper_authorized": False,
        "profitability_proven": False,
        "runtime_mutations_performed": False,
        "signed_lifecycle_replay_evidence_checked": verified,
        "synthetic_only": True,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
            "authority": deepcopy(_AUTHORITY),
            "facts": _facts(verified=False),
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "reason_code": "UNKNOWN_LIFECYCLE_REPLAY_BINDING",
            "schema_version": GATE_SCHEMA_VERSION,
            "source": {
                "common_registry_view_hash": None,
                "lifecycle_binding_gate_hash": None,
                "lifecycle_binding_preregistration_hash": None,
                "lifecycle_binding_v1_implementation_sha256": (
                    LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256
                ),
                "lifecycle_replay_binding_preregistration_hash": None,
                "lifecycle_replay_v1_implementation_sha256": (
                    LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256
                ),
                "study_identity_hash": None,
                "window_order_hash": None,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
            "window_lifecycle_replay_receipts": [],
        },
        "gate_hash",
    )


def _lifecycle_context(
    lifecycle_bundle: dict[str, Any],
    reference_time_utc: str,
) -> dict[str, Any]:
    registration = lifecycle_bundle["lifecycle_registration"]
    receipt = lifecycle_bundle["lifecycle_receipt"]
    return {
        "attestation_document": lifecycle_bundle["attestation_document"],
        "attestation_context": lifecycle_bundle["attestation_context"],
        "lifecycle_registration": registration,
        "governance_public_key_base64": lifecycle_bundle[
            "governance_public_key_base64"
        ],
        "lifecycle_receipt": receipt,
        "expected_registration_hash": registration["registration_hash"],
        "expected_lifecycle_receipt_hash": receipt["lifecycle_receipt_hash"],
        "reference_time_utc": reference_time_utc,
    }


def _replay_facts_valid(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != lifecycle_replay_v1.SCHEMA_VERSION
        or document.get("static_fingerprint")
        != lifecycle_replay_v1.STATIC_FINGERPRINT
        or document.get("status") != "PASS"
        or document.get("verification_state")
        != lifecycle_replay_v1.VERIFICATION_STATE
        or document.get("current_writer_activation_allowed") is not False
        or document.get("current_admission_allowed") is not False
        or document.get("permissions")
        != {"paper_authorized": False, "live_order_allowed": False}
        or type(document.get("authority")) is not dict
        or any(value is not False for value in document["authority"].values())
        or type(document.get("facts")) is not dict
    ):
        return False
    facts = document["facts"]
    positive = (
        "append_only_consistency_verified",
        "checkpoint_and_scan_window_verified",
        "checkpoint_signature_verified",
        "complete_scan_claim_verified",
        "exactly_one_occurrence_claim_verified",
        "lifecycle_receipt_inclusion_verified",
        "occurrence_audit_signature_verified",
        "signed_replay_registry_evidence_checked",
        "source_lifecycle_gate_reverified",
        "source_lifecycle_receipt_bound",
    )
    negative = (
        "durable_checkpoint_publication_verified",
        "external_occurrence_auditor_authority_verified",
        "external_replay_registry_authority_verified",
        "future_replay_absence_verified",
        "global_lifecycle_receipt_uniqueness_verified",
        "observation_admission_allowed",
        "profitability_verified",
        "source_lifecycle_replay_registry_checked",
    )
    return bool(
        all(facts.get(field) is True for field in positive)
        and all(facts.get(field) is False for field in negative)
    )


def _actual_binding(
    window_id: str,
    lifecycle_document: dict[str, Any],
    lifecycle_bundle: dict[str, Any],
    replay_bundle: dict[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    replay_document = replay_bundle["replay_gate_document"]
    registration = replay_bundle["replay_registration"]
    checkpoint = replay_bundle["checkpoint"]
    pinned = replay_bundle["pinned_checkpoint"]
    audit = replay_bundle["occurrence_audit"]
    attestation_registration = lifecycle_bundle["attestation_context"][
        "registration"
    ]
    upstream_key_hashes = {
        lifecycle_document["provider_dataset_public_key_sha256"],
        lifecycle_document["governance_public_key_sha256"],
        attestation_registration["identity_registry_public_key_sha256"],
        attestation_registration["timestamp_adapter_public_key_sha256"],
    }
    if (
        len(upstream_key_hashes) != 4
        or not all(_exact_hash(value) for value in upstream_key_hashes)
    ):
        raise ValueError("upstream_key_set_invalid")
    binding = {
        "adapter_id": registration["adapter_id"],
        "adapter_implementation_hash": registration[
            "adapter_implementation_hash"
        ],
        "audit_issued_at_utc": audit["audit_issued_at_utc"],
        "checkpoint_hash": replay_document["checkpoint_hash"],
        "checkpoint_issued_at_utc": checkpoint["issued_at_utc"],
        "checkpoint_root_hash": replay_document["checkpoint_root_hash"],
        "checkpoint_tree_size": replay_document["checkpoint_tree_size"],
        "consistency_proof_hash": audit["consistency_proof_hash"],
        "declared_at_utc": registration["declared_at_utc"],
        "excluded_upstream_public_key_set_hash": strict_canonical_hash(
            sorted(upstream_key_hashes)
        ),
        "inclusion_proof_hash": audit["inclusion_proof_hash"],
        "index_snapshot_record_count": audit[
            "index_snapshot_record_count"
        ],
        "index_snapshot_root_hash": audit["index_snapshot_root_hash"],
        "lifecycle_receipt_hash": replay_document[
            "source_lifecycle_receipt_hash"
        ],
        "lifecycle_verification_hash": replay_document[
            "source_lifecycle_verification_hash"
        ],
        "max_checkpoint_age_seconds": registration[
            "max_checkpoint_age_seconds"
        ],
        "max_occurrence_receipt_issue_delay_seconds": registration[
            "max_occurrence_receipt_issue_delay_seconds"
        ],
        "max_scan_age_seconds": registration["max_scan_age_seconds"],
        "occurrence_audit_hash": replay_document["occurrence_audit_hash"],
        "occurrence_auditor_id": registration["occurrence_auditor_id"],
        "occurrence_auditor_key_id": registration[
            "occurrence_auditor_key_id"
        ],
        "occurrence_auditor_public_key_sha256": registration[
            "occurrence_auditor_public_key_sha256"
        ],
        "occurrence_count_claim": replay_document[
            "occurrence_count_claim"
        ],
        "occurrence_leaf_index": replay_document["occurrence_leaf_index"],
        "pinned_checkpoint_hash": replay_document[
            "pinned_checkpoint_hash"
        ],
        "previous_checkpoint_hash": checkpoint["previous_checkpoint_hash"],
        "previous_checkpoint_root_hash": replay_document[
            "previous_checkpoint_root_hash"
        ],
        "previous_checkpoint_tree_size": replay_document[
            "previous_checkpoint_tree_size"
        ],
        "reference_time_utc": replay_document["reference_time_utc"],
        "replay_registration_hash": replay_document[
            "replay_registration_hash"
        ],
        "replay_registry_id": replay_document["replay_registry_id"],
        "replay_registry_key_id": registration["replay_registry_key_id"],
        "replay_registry_namespace": registration[
            "replay_registry_namespace"
        ],
        "replay_registry_public_key_sha256": registration[
            "replay_registry_public_key_sha256"
        ],
        "scan_completed_at_utc": replay_document[
            "scan_completed_at_utc"
        ],
        "scan_end_index_exclusive": audit["scan_end_index_exclusive"],
        "scan_start_index": audit["scan_start_index"],
        "window_id": window_id,
    }
    if (
        pinned["pin_hash"] != binding["pinned_checkpoint_hash"]
        or checkpoint["checkpoint_hash"] != binding["checkpoint_hash"]
        or audit["occurrence_audit_hash"] != binding["occurrence_audit_hash"]
    ):
        raise ValueError("replay_output_source_mismatch")
    return binding, upstream_key_hashes


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
    preregistration: Any,
    lifecycle_binding_gate_document: Any,
    lifecycle_binding_preregistration: Any,
    provider_binding_gate_document: Any,
    provider_binding_preregistration: Any,
    overlap_gate_document: Any,
    overlap_preregistration: Any,
    overlap_evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    window_provider_attestation_bundles: Any,
    window_lifecycle_bundles: Any,
    window_lifecycle_replay_bundles: Any,
    *,
    expected_preregistration_hash: Any,
    expected_lifecycle_binding_gate_hash: Any,
    expected_lifecycle_binding_preregistration_hash: Any,
    expected_provider_binding_gate_hash: Any,
    expected_provider_binding_preregistration_hash: Any,
    expected_overlap_gate_hash: Any,
    expected_overlap_preregistration_hash: Any,
    expected_overlap_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> dict[str, Any]:
    if (
        not _preregistration_valid(preregistration)
        or not _exact_hash(expected_preregistration_hash)
        or not compare_digest(
            preregistration["preregistration_hash"],
            expected_preregistration_hash,
        )
        or not _lifecycle_preregistration_exact(
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
        or preregistration["lifecycle_binding_preregistration_hash"]
        != lifecycle_binding_preregistration.get("preregistration_hash")
        or lifecycle_binding_preregistration.get("preregistration_hash")
        != expected_lifecycle_binding_preregistration_hash
    ):
        return _unknown("LIFECYCLE_REPLAY_BINDING_PREREGISTRATION_INVALID")
    try:
        lifecycle_exact = lifecycle_binding_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
            lifecycle_binding_gate_document,
            lifecycle_binding_preregistration,
            provider_binding_gate_document,
            provider_binding_preregistration,
            overlap_gate_document,
            overlap_preregistration,
            overlap_evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            window_provider_attestation_bundles,
            window_lifecycle_bundles,
            expected_gate_hash=expected_lifecycle_binding_gate_hash,
            expected_preregistration_hash=(
                expected_lifecycle_binding_preregistration_hash
            ),
            expected_provider_binding_gate_hash=(
                expected_provider_binding_gate_hash
            ),
            expected_provider_binding_preregistration_hash=(
                expected_provider_binding_preregistration_hash
            ),
            expected_overlap_gate_hash=expected_overlap_gate_hash,
            expected_overlap_preregistration_hash=(
                expected_overlap_preregistration_hash
            ),
            expected_overlap_evidence_hash=expected_overlap_evidence_hash,
            expected_multi_window_gate_hash=expected_multi_window_gate_hash,
            expected_multi_window_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        lifecycle_exact = False
    if not lifecycle_exact:
        return _unknown("ADR0351_LIFECYCLE_BINDING_GATE_EXACT_REBUILD_FAILED")
    lifecycle_status = lifecycle_binding_gate_document.get("status")
    if lifecycle_status not in {"PASS", "BLOCK"}:
        return _unknown("ADR0351_GATE_STATUS_NOT_DECISION_KNOWN")

    windows = preregistration["expected_windows"]
    expected_rows = preregistration["expected_replay_bindings"]
    lifecycle_rows = lifecycle_binding_preregistration[
        "expected_lifecycle_bindings"
    ]
    lifecycle_receipts = lifecycle_binding_gate_document.get(
        "window_lifecycle_receipts"
    )
    if (
        type(window_lifecycle_bundles) is not list
        or type(window_lifecycle_replay_bundles) is not list
        or type(lifecycle_receipts) is not list
        or len(window_lifecycle_bundles) != len(windows)
        or len(window_lifecycle_replay_bundles) != len(windows)
        or len(lifecycle_receipts) != len(windows)
    ):
        return _unknown("WINDOW_LIFECYCLE_REPLAY_SET_NOT_EXACT")

    actual_rows: list[dict[str, Any]] = []
    all_upstream_key_hashes: set[str] = set()
    for index, window_id in enumerate(windows):
        expected = expected_rows[index]
        lifecycle_row = lifecycle_rows[index]
        lifecycle_receipt = lifecycle_receipts[index]
        lifecycle_bundle = window_lifecycle_bundles[index]
        replay_bundle = window_lifecycle_replay_bundles[index]
        if (
            type(lifecycle_receipt) is not dict
            or not strict_json_contract_equal(lifecycle_receipt, lifecycle_row)
            or type(lifecycle_bundle) is not dict
            or lifecycle_bundle.get("window_id") != window_id
            or type(replay_bundle) is not dict
            or frozenset(replay_bundle) != _REPLAY_BUNDLE_FIELDS
            or replay_bundle.get("window_id") != window_id
        ):
            return _unknown("WINDOW_LIFECYCLE_REPLAY_ORDER_OR_SHAPE_INVALID")
        try:
            lifecycle_document = lifecycle_bundle["lifecycle_gate_document"]
            lifecycle_context = _lifecycle_context(
                lifecycle_bundle,
                expected["reference_time_utc"],
            )
            replay_exact = lifecycle_replay_v1.verify_provider_dataset_key_lifecycle_replay_gate_v1(
                replay_bundle["replay_gate_document"],
                lifecycle_document,
                lifecycle_context,
                replay_bundle["replay_registration"],
                replay_bundle["replay_registry_public_key_base64"],
                replay_bundle["occurrence_auditor_public_key_base64"],
                replay_bundle["pinned_checkpoint"],
                replay_bundle["checkpoint"],
                replay_bundle["inclusion_proof"],
                replay_bundle["consistency_proof"],
                replay_bundle["occurrence_audit"],
                expected_registration_hash=expected[
                    "replay_registration_hash"
                ],
                expected_pinned_checkpoint_hash=expected[
                    "pinned_checkpoint_hash"
                ],
                expected_checkpoint_hash=expected["checkpoint_hash"],
                expected_occurrence_audit_hash=expected[
                    "occurrence_audit_hash"
                ],
                reference_time_utc=expected["reference_time_utc"],
            )
        except (KeyError, TypeError, ValueError):
            replay_exact = False
        if not replay_exact:
            return _unknown("ADR0122_LIFECYCLE_REPLAY_GATE_EXACT_REBUILD_FAILED")
        if not _replay_facts_valid(replay_bundle["replay_gate_document"]):
            return _unknown("ADR0122_LIFECYCLE_REPLAY_FACTS_INVALID")
        try:
            actual, upstream_key_hashes = _actual_binding(
                window_id,
                lifecycle_document,
                lifecycle_bundle,
                replay_bundle,
            )
        except (KeyError, TypeError, ValueError):
            return _unknown("LIFECYCLE_REPLAY_BINDING_SOURCE_INVALID")
        if not strict_json_contract_equal(actual, expected):
            return _unknown("LIFECYCLE_REPLAY_TO_WINDOW_BINDING_SPLICE")
        actual_rows.append(actual)
        all_upstream_key_hashes.update(upstream_key_hashes)

    if not _replay_bindings_valid(actual_rows, windows, lifecycle_rows):
        return _unknown("COMMON_LIFECYCLE_REPLAY_VIEW_INVALID")
    common = actual_rows[0]
    if (
        common["replay_registry_public_key_sha256"]
        in all_upstream_key_hashes
        or common["occurrence_auditor_public_key_sha256"]
        in all_upstream_key_hashes
        or common["replay_registry_public_key_sha256"]
        == common["occurrence_auditor_public_key_sha256"]
    ):
        return _unknown("CROSS_WINDOW_REPLAY_KEY_ROLE_COLLISION")

    blockers = (
        ["LIFECYCLE_BINDING_GATE_V1_BLOCKED"]
        if lifecycle_status == "BLOCK"
        else []
    )
    status = "BLOCK" if blockers else "PASS"
    reason_code = (
        "BLOCK_LIFECYCLE_REPLAY_BINDING"
        if blockers
        else "PASS_LIFECYCLE_REPLAY_BINDING"
    )
    document = {
        "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": _facts(verified=True),
        "gate_blockers": blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "reason_code": reason_code,
        "schema_version": GATE_SCHEMA_VERSION,
        "source": {
            "common_registry_view_hash": preregistration[
                "common_registry_view_hash"
            ],
            "lifecycle_binding_gate_hash": lifecycle_binding_gate_document[
                "gate_hash"
            ],
            "lifecycle_binding_preregistration_hash": (
                lifecycle_binding_preregistration["preregistration_hash"]
            ),
            "lifecycle_binding_v1_implementation_sha256": (
                LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "lifecycle_replay_binding_preregistration_hash": (
                preregistration["preregistration_hash"]
            ),
            "lifecycle_replay_v1_implementation_sha256": (
                LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256
            ),
            "study_identity_hash": preregistration["study_identity_hash"],
            "window_order_hash": preregistration["window_order_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "checkpoint_tree_size": common["checkpoint_tree_size"],
            "distinct_lifecycle_receipt_count": len(
                {row["lifecycle_receipt_hash"] for row in actual_rows}
            ),
            "distinct_occurrence_leaf_index_count": len(
                {row["occurrence_leaf_index"] for row in actual_rows}
            ),
            "registry_view_count": 1,
            "window_count": len(windows),
        },
        "window_lifecycle_replay_receipts": deepcopy(actual_rows),
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
    document: Any,
    *args: Any,
    expected_gate_hash: Any,
    **kwargs: Any,
) -> bool:
    if (
        type(document) is not dict
        or not _exact_hash(expected_gate_hash)
        or document.get("gate_hash") != expected_gate_hash
    ):
        return False
    try:
        rebuilt = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
            *args,
            **kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, rebuilt)
        and compare_digest(document["gate_hash"], rebuilt["gate_hash"])
    )


__all__ = [
    "ACTIVATION_SEQUENCE",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256",
    "LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1",
]
