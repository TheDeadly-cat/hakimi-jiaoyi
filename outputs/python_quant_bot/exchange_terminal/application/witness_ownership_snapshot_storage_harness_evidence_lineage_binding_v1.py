"""Bind signed storage evidence to one exact isolated harness execution.

Every component is independently rebuilt before cross-layer scenario, artifact,
and observer-handoff lineage is checked.  No driver or external source is called.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1 as harness,
)
from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as evidence,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_observer_identity_admission_v1 as observer_admission,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-harness-evidence-lineage-binding-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-harness-evidence-lineage-"
    "binding-v1-lock-1"
)
STATUS_LINEAGE_BOUND = (
    "HARNESS_RESULTS_SIGNED_EVIDENCE_AND_OBSERVER_ADMISSION_LINEAGE_BOUND_"
    "EXTERNAL_PERSISTENCE_UNPROVEN"
)
STATUS_BLOCK = "BLOCK"
GATE_STATUS_UNKNOWN = "UNKNOWN"
GATE_STATUS_BLOCK = "BLOCK"
PERMISSION_STATE = "RESEARCH_ONLY"

EVIDENCE_IMPLEMENTATION_SHA256 = (
    "7111362ca0c1fa914bf6ea65a358347e6889e2f63184a520f5cdf0cdc37665a3"
)
HARNESS_IMPLEMENTATION_SHA256 = (
    "a0212ece7ffe67b9f2dc5515e3effbbdebc8e5512dd1e9b32eadaae41ef80811"
)
OBSERVER_ADMISSION_IMPLEMENTATION_SHA256 = (
    "a285225bc97cc61a5405d7472e0439295b04ca1442e0a9bcf8039a3e0c648578"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _build_binding(
    *,
    identity_source_preregistration_document: dict[str, Any],
    storage_preregistration_document: dict[str, Any],
    storage_evidence_evaluation_document: dict[str, Any],
    harness_plan_document: dict[str, Any],
    harness_execution_bundle_document: dict[str, Any],
    observer_admission_evaluation_document: dict[str, Any],
    signed_report_documents: list[dict[str, Any]],
    status: str,
    gate_status: str,
    blocker_codes: tuple[str, ...],
    bound_driver_requirement_count: int,
    bound_observer_requirement_count: int,
    verified: bool,
) -> dict[str, Any]:
    component_hashes = {
        "identity_source_adapter_preregistration_hash": (
            identity_source_preregistration_document[
                "adapter_preregistration_hash"
            ]
        ),
        "storage_adapter_preregistration_hash": storage_preregistration_document[
            "storage_adapter_preregistration_hash"
        ],
        "storage_evidence_quorum_evaluation_hash": (
            storage_evidence_evaluation_document["quorum_evaluation_hash"]
        ),
        "harness_plan_hash": harness_plan_document["harness_plan_hash"],
        "harness_execution_bundle_hash": harness_execution_bundle_document[
            "harness_execution_bundle_hash"
        ],
        "observer_admission_evaluation_hash": observer_admission_evaluation_document[
            "observer_admission_evaluation_hash"
        ],
    }
    report_hashes = sorted(
        document["signed_observer_report_hash"]
        for document in signed_report_documents
    )
    lineage_bundle_hash = strict_canonical_hash(
        {
            "component_hashes": component_hashes,
            "signed_observer_report_hashes": report_hashes,
        }
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "gate_status": gate_status,
        "blocker_codes": list(blocker_codes),
        "component_hashes": component_hashes,
        "evidence_implementation_sha256": EVIDENCE_IMPLEMENTATION_SHA256,
        "harness_implementation_sha256": HARNESS_IMPLEMENTATION_SHA256,
        "observer_admission_implementation_sha256": (
            OBSERVER_ADMISSION_IMPLEMENTATION_SHA256
        ),
        "lineage_bundle_hash": lineage_bundle_hash,
        "expected_driver_requirement_count": 13,
        "bound_driver_requirement_count": bound_driver_requirement_count,
        "expected_observer_requirement_count": 1,
        "bound_observer_requirement_count": bound_observer_requirement_count,
        "bound_signed_report_count": len(signed_report_documents),
        "component_contracts_verified": True,
        "component_success_statuses_verified": verified,
        "driver_scenario_lineage_verified": verified,
        "driver_artifact_lineage_verified": verified,
        "observer_handoff_lineage_verified": verified,
        "external_observer_identity_verified": False,
        "real_adapter_execution_verified": False,
        "external_persistence_independently_verified": False,
        "permission_state": PERMISSION_STATE,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
    }
    return seal_strict_canonical_document(document, "lineage_binding_hash")


def evaluate_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
    storage_evidence_evaluation_document: Any,
    signed_report_documents: Any,
    harness_execution_bundle_document: Any,
    harness_plan_document: Any,
    observer_admission_evaluation_document: Any,
    dual_signed_observer_identity_assertion_documents: Any,
    identity_source_preregistration_document: Any,
    storage_preregistration_document: Any,
    observer_registration_documents: Any,
    *,
    storage_preregistration_kwargs: Any,
    harness_plan_build_kwargs: Any,
    identity_source_preregistration_kwargs: Any,
) -> dict[str, Any]:
    documents = (
        storage_evidence_evaluation_document,
        harness_execution_bundle_document,
        harness_plan_document,
        observer_admission_evaluation_document,
        identity_source_preregistration_document,
        storage_preregistration_document,
    )
    if not all(type(document) is dict for document in documents):
        return {}
    if type(signed_report_documents) is not list:
        return {}
    if not evidence.verify_witness_ownership_snapshot_storage_evidence_quorum_v1(
        storage_evidence_evaluation_document,
        signed_report_documents,
        storage_preregistration_document,
        observer_registration_documents,
        expected_quorum_evaluation_hash=storage_evidence_evaluation_document.get(
            "quorum_evaluation_hash"
        ),
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    ):
        return {}
    if not harness.verify_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
        harness_execution_bundle_document,
        harness_plan_document,
        storage_preregistration_document,
        expected_harness_execution_bundle_hash=harness_execution_bundle_document.get(
            "harness_execution_bundle_hash"
        ),
        plan_build_kwargs=harness_plan_build_kwargs,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    ):
        return {}
    if not observer_admission.verify_witness_ownership_storage_observer_identity_admission_v1(
        observer_admission_evaluation_document,
        dual_signed_observer_identity_assertion_documents,
        identity_source_preregistration_document,
        observer_registration_documents,
        expected_observer_admission_evaluation_hash=(
            observer_admission_evaluation_document.get(
                "observer_admission_evaluation_hash"
            )
        ),
        identity_source_preregistration_kwargs=(
            identity_source_preregistration_kwargs
        ),
    ):
        return {}
    if storage_preregistration_document["governance_anchor_hashes"][
        "identity_source_adapter_preregistration_hash"
    ] != identity_source_preregistration_document["adapter_preregistration_hash"]:
        return _build_binding(
            identity_source_preregistration_document=identity_source_preregistration_document,
            storage_preregistration_document=storage_preregistration_document,
            storage_evidence_evaluation_document=storage_evidence_evaluation_document,
            harness_plan_document=harness_plan_document,
            harness_execution_bundle_document=harness_execution_bundle_document,
            observer_admission_evaluation_document=observer_admission_evaluation_document,
            signed_report_documents=signed_report_documents,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("identity_source_to_storage_lineage_invalid",),
            bound_driver_requirement_count=0,
            bound_observer_requirement_count=0,
            verified=False,
        )

    component_statuses = (
        storage_evidence_evaluation_document.get("status")
        == evidence.STATUS_SIGNED_STRUCTURAL_COVERAGE,
        harness_execution_bundle_document.get("evaluation", {}).get("status")
        == harness.STATUS_DRIVER_SCENARIOS_COMPLETE,
        observer_admission_evaluation_document.get("status")
        == observer_admission.STATUS_DUAL_SIGNED_ADMISSION_CANDIDATE,
    )
    if not all(component_statuses):
        return _build_binding(
            identity_source_preregistration_document=identity_source_preregistration_document,
            storage_preregistration_document=storage_preregistration_document,
            storage_evidence_evaluation_document=storage_evidence_evaluation_document,
            harness_plan_document=harness_plan_document,
            harness_execution_bundle_document=harness_execution_bundle_document,
            observer_admission_evaluation_document=observer_admission_evaluation_document,
            signed_report_documents=signed_report_documents,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("component_success_status_invalid",),
            bound_driver_requirement_count=0,
            bound_observer_requirement_count=0,
            verified=False,
        )

    plan_by_requirement = {
        row["requirement_id"]: row for row in harness_plan_document["scenarios"]
    }
    result_by_requirement = {
        result["requirement_id"]: result
        for result in harness_execution_bundle_document["scenario_result_documents"]
    }
    reports_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for signed_document in signed_report_documents:
        report = signed_document["report_document"]
        reports_by_requirement.setdefault(report["requirement_id"], []).append(
            report
        )

    bound_driver = 0
    bound_observer = 0
    blocker = ""
    for requirement_id, plan_row in plan_by_requirement.items():
        reports = reports_by_requirement.get(requirement_id, [])
        if len(reports) != 2:
            blocker = "signed_report_requirement_pair_invalid"
            break
        if any(
            report["scenario_preregistration_hash"]
            != plan_row["scenario_preregistration_hash"]
            for report in reports
        ):
            blocker = "report_to_harness_scenario_lineage_invalid"
            break
        if plan_row["execution_mode"] == harness.EXECUTION_MODE_DRIVER:
            result = result_by_requirement.get(requirement_id)
            if result is None:
                blocker = "driver_result_requirement_lineage_missing"
                break
            if any(
                report["observed_artifact_hash"]
                != result["observed_artifact_hash"]
                for report in reports
            ):
                blocker = "report_to_driver_artifact_lineage_invalid"
                break
            bound_driver += 1
        else:
            handoff_hash = harness_execution_bundle_document["evaluation"].get(
                "observer_handoff_hash"
            )
            if not _is_sha256(handoff_hash) or any(
                report["observed_artifact_hash"] != handoff_hash
                for report in reports
            ):
                blocker = "report_to_observer_handoff_lineage_invalid"
                break
            bound_observer += 1

    verified = not blocker and bound_driver == 13 and bound_observer == 1
    if not verified and not blocker:
        blocker = "lineage_binding_coverage_invalid"
    return _build_binding(
        identity_source_preregistration_document=identity_source_preregistration_document,
        storage_preregistration_document=storage_preregistration_document,
        storage_evidence_evaluation_document=storage_evidence_evaluation_document,
        harness_plan_document=harness_plan_document,
        harness_execution_bundle_document=harness_execution_bundle_document,
        observer_admission_evaluation_document=observer_admission_evaluation_document,
        signed_report_documents=signed_report_documents,
        status=STATUS_LINEAGE_BOUND if verified else STATUS_BLOCK,
        gate_status=GATE_STATUS_UNKNOWN if verified else GATE_STATUS_BLOCK,
        blocker_codes=() if verified else (blocker,),
        bound_driver_requirement_count=bound_driver,
        bound_observer_requirement_count=bound_observer,
        verified=verified,
    )


def verify_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
    document: Any,
    *evaluation_args: Any,
    expected_lineage_binding_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_lineage_binding_hash):
        return False
    expected = evaluate_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
        *evaluation_args,
        **evaluation_kwargs,
    )
    return (
        bool(expected)
        and expected.get("lineage_binding_hash") == expected_lineage_binding_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "GATE_STATUS_BLOCK",
    "GATE_STATUS_UNKNOWN",
    "PERMISSION_STATE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "STATUS_LINEAGE_BOUND",
    "evaluate_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1",
    "verify_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1",
]
