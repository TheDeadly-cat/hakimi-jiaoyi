"""Fail-closed persistence admission decision for the storage evidence chain.

Structural lineage may create a candidate for a future explicitly authorized
isolated test.  It never authorizes that test, a backend mount, publication, or
trading.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1 as lineage,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-persistence-admission-decision-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-persistence-admission-"
    "decision-v1-lock-1"
)
STATUS_STRUCTURAL_TEST_CANDIDATE = (
    "STRUCTURAL_LINEAGE_COMPLETE_EXPLICIT_ISOLATED_TEST_AUTHORIZATION_REQUIRED"
)
STATUS_BLOCK = "BLOCK"
GATE_STATUS_BLOCK = "BLOCK"
DECISION_DO_NOT_MOUNT = "DO_NOT_MOUNT"
PERMISSION_STATE = "RESEARCH_ONLY"

LINEAGE_IMPLEMENTATION_SHA256 = (
    "4c47934b9945626b1665c6e61f873123a45ddc935064e2084897ece7eb48d639"
)

PENDING_CONDITIONS = (
    "EXPLICIT_ISOLATED_TEST_AUTHORIZATION_NOT_SUPPLIED",
    "REAL_IDENTITY_SOURCE_TRUTH_UNVERIFIED",
    "EXTERNAL_OBSERVER_IDENTITY_UNVERIFIED",
    "REAL_ADAPTER_EXECUTION_UNVERIFIED",
    "ISOLATED_DOMAIN_CONFINEMENT_UNVERIFIED",
    "EXTERNAL_PERSISTENCE_UNVERIFIED",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def evaluate_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
    lineage_binding_document: Any,
    *lineage_evaluation_args: Any,
    expected_lineage_binding_hash: Any,
    **lineage_evaluation_kwargs: Any,
) -> dict[str, Any]:
    if not _is_sha256(expected_lineage_binding_hash):
        return {}
    if not lineage.verify_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
        lineage_binding_document,
        *lineage_evaluation_args,
        expected_lineage_binding_hash=expected_lineage_binding_hash,
        **lineage_evaluation_kwargs,
    ):
        return {}
    structural_candidate = (
        lineage_binding_document.get("status") == lineage.STATUS_LINEAGE_BOUND
        and lineage_binding_document.get("gate_status")
        == lineage.GATE_STATUS_UNKNOWN
    )
    blockers = (
        list(PENDING_CONDITIONS)
        if structural_candidate
        else ["LINEAGE_BINDING_NOT_COMPLETE"]
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            STATUS_STRUCTURAL_TEST_CANDIDATE
            if structural_candidate
            else STATUS_BLOCK
        ),
        "gate_status": GATE_STATUS_BLOCK,
        "decision": DECISION_DO_NOT_MOUNT,
        "blocker_codes": blockers,
        "lineage_binding_hash": lineage_binding_document["lineage_binding_hash"],
        "lineage_bundle_hash": lineage_binding_document["lineage_bundle_hash"],
        "lineage_implementation_sha256": LINEAGE_IMPLEMENTATION_SHA256,
        "component_hashes": lineage_binding_document["component_hashes"],
        "structural_lineage_verified": structural_candidate,
        "isolated_backend_test_candidate": structural_candidate,
        "explicit_isolated_test_authorization_supplied": False,
        "isolated_backend_test_authorized": False,
        "backend_mount_authorized": False,
        "real_identity_source_truth_verified": False,
        "external_observer_identity_verified": False,
        "real_adapter_execution_verified": False,
        "isolated_domain_confinement_verified": False,
        "external_persistence_independently_verified": False,
        "permission_state": PERMISSION_STATE,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
    }
    return seal_strict_canonical_document(document, "persistence_admission_decision_hash")


def verify_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
    document: Any,
    lineage_binding_document: Any,
    *lineage_evaluation_args: Any,
    expected_persistence_admission_decision_hash: Any,
    expected_lineage_binding_hash: Any,
    **lineage_evaluation_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_persistence_admission_decision_hash):
        return False
    expected = evaluate_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
        lineage_binding_document,
        *lineage_evaluation_args,
        expected_lineage_binding_hash=expected_lineage_binding_hash,
        **lineage_evaluation_kwargs,
    )
    return (
        bool(expected)
        and expected.get("persistence_admission_decision_hash")
        == expected_persistence_admission_decision_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "DECISION_DO_NOT_MOUNT",
    "GATE_STATUS_BLOCK",
    "LINEAGE_IMPLEMENTATION_SHA256",
    "PENDING_CONDITIONS",
    "PERMISSION_STATE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "STATUS_STRUCTURAL_TEST_CANDIDATE",
    "evaluate_witness_ownership_snapshot_storage_persistence_admission_decision_v1",
    "verify_witness_ownership_snapshot_storage_persistence_admission_decision_v1",
]
