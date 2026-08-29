"""Bind an exact ADR0352 gate to exact ADR0354 persistence receipts.

This pure composition gate accepts strict source and persistence bundles. It
reruns both public verifiers, binds the persisted asset to the verified common
replay view, and preserves ADR0352 BLOCK. External provider trust, real
durability, authoritative pinning, lineage, and trading authority stay false.
"""

from __future__ import annotations

from copy import deepcopy
from hmac import compare_digest
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1
    as replay_binding_v1,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1
    as persistence_receipts_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-binding-"
    "gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-multi-window-lifecycle-replay-checkpoint-"
    "persistence-binding-gate-v1-synthetic-unmounted-lock-1"
)
REPLAY_BINDING_V1_IMPLEMENTATION_SHA256 = (
    "44872a353d2380a09f9d45ba3a3e229c1e54aba3c737439a6f841ab181f9bef9"
)
PERSISTENCE_RECEIPTS_V1_IMPLEMENTATION_SHA256 = (
    "8e18be55b3abf1fc01f71dafa1bdfa3cc2ccc4806a7352f8079e3bdbc4f24e92"
)
_SOURCE_INPUT_FIELDS = frozenset(
    {
        "expected_gate_hash",
        "expected_lifecycle_binding_gate_hash",
        "expected_lifecycle_binding_preregistration_hash",
        "expected_multi_window_gate_hash",
        "expected_multi_window_preregistration_hash",
        "expected_overlap_evidence_hash",
        "expected_overlap_gate_hash",
        "expected_overlap_preregistration_hash",
        "expected_preregistration_hash",
        "expected_provider_binding_gate_hash",
        "expected_provider_binding_preregistration_hash",
        "expected_window_audit_hashes",
        "lifecycle_binding_gate_document",
        "lifecycle_binding_preregistration",
        "multi_window_gate_document",
        "multi_window_preregistration",
        "overlap_evidence",
        "overlap_gate_document",
        "overlap_preregistration",
        "preregistration",
        "provider_binding_gate_document",
        "provider_binding_preregistration",
        "window_audits",
        "window_lifecycle_bundles",
        "window_lifecycle_replay_bundles",
        "window_provider_attestation_bundles",
    }
)
_PERSISTENCE_INPUT_FIELDS = frozenset(
    {
        "checkpoint_asset",
        "expected_asset_hash",
        "expected_registration_hash",
        "expected_reopen_receipt_hash",
        "expected_verification_hash",
        "expected_write_receipt_hash",
        "persistence_configuration",
        "persistence_provider_public_key_base64",
        "persistence_registration",
        "reopen_receipt",
        "write_receipt",
    }
)
_AUTHORITY = {
    "authoritative_future_pin_allowed": False,
    "candidate_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "durable_checkpoint_claim_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "persistence_provider_use_allowed": False,
    "profitability_claim_allowed": False,
    "writer_allowed": False,
}
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_BASE_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "EXTERNAL_PERSISTENCE_PROVIDER_AUTHORITY_UNPROVEN",
    "REAL_STORAGE_DURABILITY_UNPROVEN",
    "EXTERNAL_PERSISTENCE_TIME_UNPROVEN",
    "AUTHORITATIVE_FUTURE_PIN_UNPROVEN",
    "PERSISTED_CHECKPOINT_LINEAGE_UNPROVEN",
    "LONGITUDINAL_COVERAGE_UNPROVEN",
    "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
    "PAPER_LIVE_UNAUTHORIZED",
)
_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contracts": {
        "adr0352": {
            "schema_version": replay_binding_v1.GATE_SCHEMA_VERSION,
            "implementation_sha256": REPLAY_BINDING_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
        "adr0354": {
            "schema_version": persistence_receipts_v1.EVALUATION_SCHEMA_VERSION,
            "implementation_sha256": PERSISTENCE_RECEIPTS_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
    },
    "binding_policy": (
        "EXACT_ASSET_SOURCE_TO_VERIFIED_COMMON_REGISTRY_VIEW_V1"
    ),
    "upstream_block_action": "PRESERVE_ADR0352_BLOCK",
    "external_durability_claimed": False,
    "authoritative_pin_claimed": False,
    "lineage_claimed": False,
    "longitudinal_coverage_claimed": False,
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _source_exact(document: Any, inputs: Any) -> bool:
    if (
        type(document) is not dict
        or type(inputs) is not dict
        or frozenset(inputs) != _SOURCE_INPUT_FIELDS
    ):
        return False
    try:
        return replay_binding_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
            document,
            inputs["preregistration"],
            inputs["lifecycle_binding_gate_document"],
            inputs["lifecycle_binding_preregistration"],
            inputs["provider_binding_gate_document"],
            inputs["provider_binding_preregistration"],
            inputs["overlap_gate_document"],
            inputs["overlap_preregistration"],
            inputs["overlap_evidence"],
            inputs["multi_window_gate_document"],
            inputs["multi_window_preregistration"],
            inputs["window_audits"],
            inputs["window_provider_attestation_bundles"],
            inputs["window_lifecycle_bundles"],
            inputs["window_lifecycle_replay_bundles"],
            expected_gate_hash=inputs["expected_gate_hash"],
            expected_preregistration_hash=inputs[
                "expected_preregistration_hash"
            ],
            expected_lifecycle_binding_gate_hash=inputs[
                "expected_lifecycle_binding_gate_hash"
            ],
            expected_lifecycle_binding_preregistration_hash=inputs[
                "expected_lifecycle_binding_preregistration_hash"
            ],
            expected_provider_binding_gate_hash=inputs[
                "expected_provider_binding_gate_hash"
            ],
            expected_provider_binding_preregistration_hash=inputs[
                "expected_provider_binding_preregistration_hash"
            ],
            expected_overlap_gate_hash=inputs["expected_overlap_gate_hash"],
            expected_overlap_preregistration_hash=inputs[
                "expected_overlap_preregistration_hash"
            ],
            expected_overlap_evidence_hash=inputs[
                "expected_overlap_evidence_hash"
            ],
            expected_multi_window_gate_hash=inputs[
                "expected_multi_window_gate_hash"
            ],
            expected_multi_window_preregistration_hash=inputs[
                "expected_multi_window_preregistration_hash"
            ],
            expected_window_audit_hashes=inputs[
                "expected_window_audit_hashes"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _persistence_exact(
    document: Any,
    source_inputs: dict[str, Any],
    inputs: Any,
) -> bool:
    if (
        type(document) is not dict
        or type(inputs) is not dict
        or frozenset(inputs) != _PERSISTENCE_INPUT_FIELDS
    ):
        return False
    try:
        return persistence_receipts_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
            document,
            inputs["persistence_registration"],
            source_inputs["preregistration"],
            source_inputs["lifecycle_binding_preregistration"],
            source_inputs["provider_binding_preregistration"],
            source_inputs["overlap_preregistration"],
            source_inputs["multi_window_preregistration"],
            inputs["persistence_configuration"],
            inputs["persistence_provider_public_key_base64"],
            inputs["checkpoint_asset"],
            inputs["write_receipt"],
            inputs["reopen_receipt"],
            expected_verification_hash=inputs["expected_verification_hash"],
            expected_registration_hash=inputs["expected_registration_hash"],
            expected_asset_hash=inputs["expected_asset_hash"],
            expected_write_receipt_hash=inputs[
                "expected_write_receipt_hash"
            ],
            expected_reopen_receipt_hash=inputs[
                "expected_reopen_receipt_hash"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _source_facts_valid(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != replay_binding_v1.GATE_SCHEMA_VERSION
        or document.get("static_fingerprint") != replay_binding_v1.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or type(document.get("facts")) is not dict
    ):
        return False
    facts = document["facts"]
    return bool(
        facts.get("all_lifecycle_replay_gates_exactly_verified") is True
        and facts.get("all_lifecycle_binding_windows_replay_bound") is True
        and facts.get("common_registry_view_bound") is True
        and facts.get("distinct_lifecycle_receipts_verified") is True
        and facts.get("distinct_occurrence_leaf_indices_verified") is True
        and facts.get("signed_lifecycle_replay_evidence_checked") is True
        and facts.get("durable_checkpoint_publication_verified") is False
        and facts.get("global_lifecycle_receipt_uniqueness_verified") is False
        and facts.get("future_replay_absence_verified") is False
    )


def _persistence_facts_valid(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version")
        != persistence_receipts_v1.EVALUATION_SCHEMA_VERSION
        or document.get("static_fingerprint")
        != persistence_receipts_v1.STATIC_FINGERPRINT
        or document.get("status") != "PASS"
        or document.get("verification_state")
        != persistence_receipts_v1.VERIFICATION_STATE
        or type(document.get("facts")) is not dict
        or type(document.get("authority")) is not dict
        or any(value is not False for value in document["authority"].values())
    ):
        return False
    facts = document["facts"]
    positive = (
        "checkpoint_asset_seal_verified",
        "exact_record_replay_verified",
        "persistence_provider_public_key_hash_bound",
        "persistence_registration_exactly_verified",
        "reopen_cardinality_one_verified",
        "reopen_receipt_observed",
        "reopen_receipt_signature_verified",
        "source_common_registry_view_bound",
        "source_write_receipt_bound",
        "timestamp_and_delay_policy_verified",
        "write_cardinality_one_verified",
        "write_receipt_observed",
        "write_receipt_signature_verified",
        "write_reopen_session_separation_verified",
    )
    negative = (
        "authoritative_future_pin_verified",
        "durable_checkpoint_publication_verified",
        "external_persistence_provider_authority_verified",
        "external_persistence_time_verified",
        "local_io_performed",
        "source_replay_binding_gate_verified",
    )
    return bool(
        all(facts.get(field) is True for field in positive)
        and all(facts.get(field) is False for field in negative)
    )


def _facts(*, verified: bool) -> dict[str, Any]:
    return {
        "asset_source_common_view_bound": verified,
        "authoritative_future_pin_verified": False,
        "content_issuance_replay_verified": False,
        "current_activated": False,
        "durable_checkpoint_publication_verified": False,
        "external_persistence_provider_authority_verified": False,
        "historical_market_data_accessed": False,
        "longitudinal_checkpoint_coverage_verified": False,
        "paper_authorized": False,
        "persisted_checkpoint_lineage_verified": False,
        "persistence_receipts_exactly_verified": verified,
        "profitability_proven": False,
        "runtime_mutations_performed": False,
        "source_replay_binding_gate_verified": verified,
        "synthetic_only": True,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "activation_blockers": list(_BASE_BLOCKERS),
            "authority": deepcopy(_AUTHORITY),
            "facts": _facts(verified=False),
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "reason_code": "UNKNOWN_PERSISTENCE_SOURCE_BINDING",
            "schema_version": SCHEMA_VERSION,
            "source": None,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
        },
        "gate_hash",
    )


def _binding_valid(
    source_gate: dict[str, Any],
    source_inputs: dict[str, Any],
    persistence_evaluation: dict[str, Any],
    persistence_inputs: dict[str, Any],
) -> bool:
    source_preregistration = source_inputs["preregistration"]
    expected_rows = source_preregistration["expected_replay_bindings"]
    source_receipts = source_gate["window_lifecycle_replay_receipts"]
    common = expected_rows[0]
    registration = persistence_inputs["persistence_registration"]
    asset = persistence_inputs["checkpoint_asset"]
    evidence = persistence_evaluation["evidence"]
    return bool(
        type(source_receipts) is list
        and strict_json_contract_equal(source_receipts, expected_rows)
        and source_gate["source"]["common_registry_view_hash"]
        == source_preregistration["common_registry_view_hash"]
        and source_gate["source"][
            "lifecycle_replay_binding_preregistration_hash"
        ]
        == source_preregistration["preregistration_hash"]
        and registration["source_preregistration_hash"]
        == source_preregistration["preregistration_hash"]
        and registration["source_common_registry_view_hash"]
        == source_preregistration["common_registry_view_hash"]
        and registration["source_checkpoint_root_hash"]
        == common["checkpoint_root_hash"]
        and registration["source_checkpoint_tree_size"]
        == common["checkpoint_tree_size"]
        and registration["source_checkpoint_issued_at_utc"]
        == common["checkpoint_issued_at_utc"]
        and registration["source_reference_time_utc"]
        == common["reference_time_utc"]
        and registration["source_replay_registry_id"]
        == common["replay_registry_id"]
        and registration["source_replay_registry_namespace"]
        == common["replay_registry_namespace"]
        and asset["persistence_registration_hash"]
        == registration["registration_hash"]
        and asset["source_preregistration_hash"]
        == source_preregistration["preregistration_hash"]
        and asset["source_common_registry_view_hash"]
        == source_preregistration["common_registry_view_hash"]
        and asset["source_checkpoint_root_hash"]
        == common["checkpoint_root_hash"]
        and asset["source_checkpoint_tree_size"]
        == common["checkpoint_tree_size"]
        and asset["source_checkpoint_issued_at_utc"]
        == common["checkpoint_issued_at_utc"]
        and asset["source_reference_time_utc"]
        == common["reference_time_utc"]
        and asset["source_replay_registry_id"]
        == common["replay_registry_id"]
        and asset["source_replay_registry_namespace"]
        == common["replay_registry_namespace"]
        and evidence["checkpoint_asset_hash"] == asset["asset_hash"]
        and evidence["persistence_registration_hash"]
        == registration["registration_hash"]
        and evidence["source_preregistration_hash"]
        == source_preregistration["preregistration_hash"]
        and evidence["source_common_registry_view_hash"]
        == source_preregistration["common_registry_view_hash"]
    )


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
    source_gate_document: Any,
    source_inputs: Any,
    persistence_evaluation: Any,
    persistence_inputs: Any,
) -> dict[str, Any]:
    if not _source_exact(source_gate_document, source_inputs):
        return _unknown("ADR0352_SOURCE_GATE_EXACT_REBUILD_FAILED")
    if not _persistence_exact(
        persistence_evaluation,
        source_inputs,
        persistence_inputs,
    ):
        return _unknown("ADR0354_PERSISTENCE_RECEIPTS_EXACT_REBUILD_FAILED")
    if not _source_facts_valid(source_gate_document):
        return _unknown("ADR0352_SOURCE_FACTS_INVALID")
    if not _persistence_facts_valid(persistence_evaluation):
        return _unknown("ADR0354_PERSISTENCE_FACTS_INVALID")
    try:
        binding_valid = _binding_valid(
            source_gate_document,
            source_inputs,
            persistence_evaluation,
            persistence_inputs,
        )
    except (KeyError, TypeError, ValueError):
        binding_valid = False
    if not binding_valid:
        return _unknown("PERSISTED_ASSET_SOURCE_BINDING_INVALID")

    source_status = source_gate_document["status"]
    gate_blockers = (
        ["LIFECYCLE_REPLAY_BINDING_GATE_V1_BLOCKED"]
        if source_status == "BLOCK"
        else []
    )
    status = "BLOCK" if gate_blockers else "PASS"
    persistence_registration = persistence_inputs["persistence_registration"]
    asset = persistence_inputs["checkpoint_asset"]
    source_preregistration = source_inputs["preregistration"]
    document = {
        "activation_blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": _facts(verified=True),
        "gate_blockers": gate_blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "reason_code": (
            "BLOCK_PERSISTED_COMMON_VIEW_SOURCE_BINDING"
            if status == "BLOCK"
            else "PASS_PERSISTED_COMMON_VIEW_SOURCE_BINDING"
        ),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "checkpoint_asset_hash": asset["asset_hash"],
            "common_registry_view_hash": source_preregistration[
                "common_registry_view_hash"
            ],
            "persistence_evaluation_hash": persistence_evaluation[
                "verification_hash"
            ],
            "persistence_receipts_v1_implementation_sha256": (
                PERSISTENCE_RECEIPTS_V1_IMPLEMENTATION_SHA256
            ),
            "persistence_registration_hash": persistence_registration[
                "registration_hash"
            ],
            "replay_binding_gate_hash": source_gate_document["gate_hash"],
            "replay_binding_preregistration_hash": source_preregistration[
                "preregistration_hash"
            ],
            "replay_binding_v1_implementation_sha256": (
                REPLAY_BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "study_identity_hash": source_preregistration[
                "study_identity_hash"
            ],
            "window_order_hash": source_preregistration[
                "window_order_hash"
            ],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "checkpoint_tree_size": asset["source_checkpoint_tree_size"],
            "persisted_asset_count": 1,
            "reopen_receipt_count": 1,
            "source_window_count": source_preregistration[
                "expected_window_count"
            ],
            "write_receipt_count": 1,
        },
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
    document: Any,
    source_gate_document: Any,
    source_inputs: Any,
    persistence_evaluation: Any,
    persistence_inputs: Any,
    *,
    expected_gate_hash: Any,
) -> bool:
    if (
        type(document) is not dict
        or not _exact_hash(expected_gate_hash)
        or document.get("gate_hash") != expected_gate_hash
    ):
        return False
    try:
        rebuilt = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            source_gate_document,
            source_inputs,
            persistence_evaluation,
            persistence_inputs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, rebuilt)
        and compare_digest(document["gate_hash"], rebuilt["gate_hash"])
    )


__all__ = [
    "GATE_CONTRACT_HASH",
    "PERSISTENCE_RECEIPTS_V1_IMPLEMENTATION_SHA256",
    "REPLAY_BINDING_V1_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1",
]
