"""Neutral, bounded presentation of the ADR0425 persistence decision.

The projection exposes hashes, bounded counts, gaps, and locked permissions.
It does not embed source documents, authorize an isolated test, mount a
backend, activate current, or authorize paper/live activity.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_snapshot_storage_persistence_admission_decision_v1 as admission,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-persistence-admission-presentation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-persistence-admission-"
    "presentation-v1-unmounted-lock-1"
)
PRESENTATION_STATUS = "UNMOUNTED_RESEARCH_EVIDENCE"
UNKNOWN_PRESENTATION_STATUS = "UNMOUNTED_UNKNOWN"
DISPLAY_TONE = "NEUTRAL"
DISPLAY_STATE = "STRUCTURAL_LINEAGE_PRESENT_PERMISSION_BLOCKED"
INCOMPLETE_DISPLAY_STATE = "LINEAGE_INCOMPLETE_PERMISSION_BLOCKED"
ORDERED_STAGES = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_EXPECTED_HASH_INVALID = (
    "EXPECTED_PERSISTENCE_ADMISSION_DECISION_HASH_NOT_EXACT"
)
_EXPECTED_LINEAGE_HASH_INVALID = "EXPECTED_LINEAGE_BINDING_HASH_NOT_EXACT"
_SOURCE_NOT_EXACT = "SOURCE_PERSISTENCE_ADMISSION_DECISION_NOT_EXACT"
_SOURCE_SEMANTICS_UNSAFE = "SOURCE_DECISION_SEMANTICS_NOT_SAFE"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_FALSE_DECISION_FIELDS = (
    "explicit_isolated_test_authorization_supplied",
    "isolated_backend_test_authorized",
    "backend_mount_authorized",
    "real_identity_source_truth_verified",
    "external_observer_identity_verified",
    "real_adapter_execution_verified",
    "isolated_domain_confinement_verified",
    "external_persistence_independently_verified",
    "permission",
    "paper_authorized",
    "live_authorized",
    "snapshot_publication_authorized",
    "current_chain_activated",
)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "asset_write_allowed": False,
        "browser_execution_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "isolated_backend_test_allowed": False,
        "backend_mount_allowed": False,
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts(*, exact: bool, candidate: bool) -> dict[str, bool]:
    return {
        "source_decision_exactly_verified": exact,
        "bounded_projection": True,
        "structural_lineage_verified": exact and candidate,
        "isolated_backend_test_candidate": exact and candidate,
        "explicit_isolated_test_authorization_supplied": False,
        "real_identity_source_truth_verified": False,
        "external_observer_identity_verified": False,
        "real_adapter_execution_verified": False,
        "isolated_domain_confinement_verified": False,
        "external_persistence_independently_verified": False,
        "isolated_backend_test_authorized": False,
        "backend_mount_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
        "raw_decision_document_embedded": False,
        "raw_lineage_document_embedded": False,
        "raw_component_hash_map_embedded": False,
        "raw_key_material_embedded": False,
        "raw_signature_material_embedded": False,
    }


def _stages(*, candidate: bool, reason: str | None = None) -> list[dict[str, str]]:
    if reason is not None:
        return [
            {"axis": "SOURCE", "state": "UNKNOWN", "reason_code": reason},
            {"axis": "GAP", "state": "OPEN", "reason_code": reason},
            {"axis": "MATURITY", "state": "UNKNOWN", "reason_code": reason},
            {
                "axis": "PERMISSION",
                "state": "BLOCKED",
                "reason_code": "CURRENT_AND_EXECUTION_PERMISSIONS_BLOCKED",
            },
        ]
    return [
        {
            "axis": "SOURCE",
            "state": "HASH_BOUND_LOCAL",
            "reason_code": (
                "EXACT_LOCAL_HASH_CHAIN_ONLY_EXTERNAL_TRUTH_UNVERIFIED"
            ),
        },
        {
            "axis": "GAP",
            "state": "OPEN",
            "reason_code": (
                "SIX_EXTERNAL_AND_AUTHORIZATION_GAPS_OPEN"
                if candidate
                else "LINEAGE_BINDING_NOT_COMPLETE"
            ),
        },
        {
            "axis": "MATURITY",
            "state": (
                "STRUCTURAL_TEST_CANDIDATE" if candidate else "LINEAGE_INCOMPLETE"
            ),
            "reason_code": (
                "STRUCTURAL_CANDIDATE_IS_NOT_TEST_AUTHORIZATION"
                if candidate
                else "STRUCTURAL_LINEAGE_REQUIREMENTS_NOT_COMPLETE"
            ),
        },
        {
            "axis": "PERMISSION",
            "state": "BLOCKED",
            "reason_code": "DO_NOT_MOUNT_CURRENT_PAPER_LIVE_AND_WRITER_LOCKED",
        },
    ]


def _seal(
    *,
    presentation_status: str,
    display_state: str,
    stages: list[dict[str, str]],
    source: dict[str, str | None],
    summary: dict[str, int | None],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": presentation_status,
        "display_tone": DISPLAY_TONE,
        "display_state": display_state,
        "stage_order": list(ORDERED_STAGES),
        "stages": stages,
        "source": source,
        "summary": summary,
        "facts": facts,
        "blockers": blockers,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "presentation_hash")


def _unknown(reason: str) -> dict[str, Any]:
    return _seal(
        presentation_status=UNKNOWN_PRESENTATION_STATUS,
        display_state="UNKNOWN",
        stages=_stages(candidate=False, reason=reason),
        source={
            "persistence_admission_decision_hash": None,
            "lineage_binding_hash": None,
            "lineage_bundle_hash": None,
            "lineage_implementation_sha256": None,
        },
        summary={"blocker_count": None, "component_count": None},
        facts=_facts(exact=False, candidate=False),
        blockers=[reason],
    )


def _safe_semantics(document: Any) -> tuple[bool, bool]:
    if type(document) is not dict:
        return False, False
    if any(document.get(field) is not False for field in _FALSE_DECISION_FIELDS):
        return False, False
    if (
        document.get("gate_status") != admission.GATE_STATUS_BLOCK
        or document.get("decision") != admission.DECISION_DO_NOT_MOUNT
        or document.get("permission_state") != admission.PERMISSION_STATE
        or type(document.get("component_hashes")) is not dict
    ):
        return False, False
    candidate = document.get("isolated_backend_test_candidate") is True
    if candidate:
        safe = (
            document.get("status") == admission.STATUS_STRUCTURAL_TEST_CANDIDATE
            and document.get("structural_lineage_verified") is True
            and document.get("blocker_codes") == list(admission.PENDING_CONDITIONS)
        )
        return safe, True
    safe = (
        document.get("status") == admission.STATUS_BLOCK
        and document.get("structural_lineage_verified") is False
        and document.get("blocker_codes") == ["LINEAGE_BINDING_NOT_COMPLETE"]
    )
    return safe, False


def build_witness_ownership_snapshot_storage_persistence_admission_presentation_v1(
    persistence_admission_decision_document: Any,
    lineage_binding_document: Any,
    *lineage_evaluation_args: Any,
    expected_persistence_admission_decision_hash: Any,
    expected_lineage_binding_hash: Any,
    **lineage_evaluation_kwargs: Any,
) -> dict[str, Any]:
    if not _is_sha256(expected_persistence_admission_decision_hash):
        return _unknown(_EXPECTED_HASH_INVALID)
    if not _is_sha256(expected_lineage_binding_hash):
        return _unknown(_EXPECTED_LINEAGE_HASH_INVALID)
    if not admission.verify_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
        persistence_admission_decision_document,
        lineage_binding_document,
        *lineage_evaluation_args,
        expected_persistence_admission_decision_hash=(
            expected_persistence_admission_decision_hash
        ),
        expected_lineage_binding_hash=expected_lineage_binding_hash,
        **lineage_evaluation_kwargs,
    ):
        return _unknown(_SOURCE_NOT_EXACT)
    safe, candidate = _safe_semantics(persistence_admission_decision_document)
    if not safe:
        return _unknown(_SOURCE_SEMANTICS_UNSAFE)
    blockers = list(persistence_admission_decision_document["blocker_codes"])
    return _seal(
        presentation_status=PRESENTATION_STATUS,
        display_state=(DISPLAY_STATE if candidate else INCOMPLETE_DISPLAY_STATE),
        stages=_stages(candidate=candidate),
        source={
            "persistence_admission_decision_hash": (
                persistence_admission_decision_document[
                    "persistence_admission_decision_hash"
                ]
            ),
            "lineage_binding_hash": persistence_admission_decision_document[
                "lineage_binding_hash"
            ],
            "lineage_bundle_hash": persistence_admission_decision_document[
                "lineage_bundle_hash"
            ],
            "lineage_implementation_sha256": (
                persistence_admission_decision_document[
                    "lineage_implementation_sha256"
                ]
            ),
        },
        summary={
            "blocker_count": len(blockers),
            "component_count": len(
                persistence_admission_decision_document["component_hashes"]
            ),
        },
        facts=_facts(exact=True, candidate=candidate),
        blockers=blockers,
    )


def verify_witness_ownership_snapshot_storage_persistence_admission_presentation_v1(
    document: Any,
    persistence_admission_decision_document: Any,
    lineage_binding_document: Any,
    *lineage_evaluation_args: Any,
    expected_presentation_hash: Any,
    expected_persistence_admission_decision_hash: Any,
    expected_lineage_binding_hash: Any,
    **lineage_evaluation_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_presentation_hash):
        return False
    expected = build_witness_ownership_snapshot_storage_persistence_admission_presentation_v1(
        persistence_admission_decision_document,
        lineage_binding_document,
        *lineage_evaluation_args,
        expected_persistence_admission_decision_hash=(
            expected_persistence_admission_decision_hash
        ),
        expected_lineage_binding_hash=expected_lineage_binding_hash,
        **lineage_evaluation_kwargs,
    )
    return (
        expected.get("presentation_hash") == expected_presentation_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "DISPLAY_STATE",
    "DISPLAY_TONE",
    "INCOMPLETE_DISPLAY_STATE",
    "ORDERED_STAGES",
    "PRESENTATION_STATUS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_PRESENTATION_STATUS",
    "build_witness_ownership_snapshot_storage_persistence_admission_presentation_v1",
    "verify_witness_ownership_snapshot_storage_persistence_admission_presentation_v1",
]
