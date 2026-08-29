from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services import (
    provider_identity_artifact_transparency_availability_v1 as source_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


SCHEMA_VERSION = "provider-identity-artifact-transparency-presentation-envelope-v1"
STATIC_FINGERPRINT = (
    "20260822-provider-identity-artifact-transparency-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
POSITIVE_DISPLAY_STATE = (
    "LOCAL_ARTIFACTS_AND_SIGNED_RETRIEVAL_CLAIMS_BOUND_"
    "EXTERNAL_AVAILABILITY_GAP"
)
UNKNOWN_DISPLAY_STATE = "UNKNOWN"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

SOURCE_SCHEMA = source_contract.EVALUATION_SCHEMA
SOURCE_STATIC_FINGERPRINT = source_contract.STATIC_FINGERPRINT
SOURCE_VERIFIED_STATUS = source_contract.VERIFIED_STATUS

SOURCE_EVIDENCE_KEYS = (
    "artifact_catalog_root_hash",
    "artifact_count",
    "checkpoint_root_hash",
    "checkpoint_tree_size",
    "observer_a_receipt_hash",
    "observer_b_receipt_hash",
    "observer_result_transcript_root_hash",
    "reference_time_ms",
    "registration_receipt_hash",
    "source_reproducibility_evaluation_receipt_hash",
    "total_payload_bytes",
    "transparency_checkpoint_hash",
)
SOURCE_FACT_KEYS = (
    "all_artifact_inclusion_proofs_verified",
    "append_only_consistency_verified",
    "artifact_catalog_root_verified",
    "auditor_independence_verified",
    "complete_dual_observer_retrieval_claims_verified",
    "dual_observer_result_agreement_verified",
    "external_log_trust_attested",
    "external_persistence_verified",
    "external_time_truth_verified",
    "local_artifact_content_hashes_verified",
    "local_artifact_sizes_verified",
    "observer_a_signature_verified",
    "observer_b_signature_verified",
    "profitability_verified",
    "public_artifact_availability_verified",
    "source_and_new_roles_separated",
    "source_reproducibility_reverified",
    "suite_completeness_verified",
    "transparency_checkpoint_signature_verified",
)
SOURCE_AUTHORITY_KEYS = (
    "live_allowed",
    "observation_admission_allowed",
    "paper_allowed",
    "parameter_selection_allowed",
    "promotion_allowed",
    "research_only",
)
SOURCE_TRUE_FACTS = (
    "all_artifact_inclusion_proofs_verified",
    "append_only_consistency_verified",
    "artifact_catalog_root_verified",
    "complete_dual_observer_retrieval_claims_verified",
    "dual_observer_result_agreement_verified",
    "local_artifact_content_hashes_verified",
    "local_artifact_sizes_verified",
    "observer_a_signature_verified",
    "observer_b_signature_verified",
    "source_and_new_roles_separated",
    "source_reproducibility_reverified",
    "transparency_checkpoint_signature_verified",
)
SOURCE_FALSE_FACTS = (
    "auditor_independence_verified",
    "external_log_trust_attested",
    "external_persistence_verified",
    "external_time_truth_verified",
    "profitability_verified",
    "public_artifact_availability_verified",
    "suite_completeness_verified",
)
VERIFIED_BLOCKERS = (
    "EXTERNAL_LOG_GOVERNANCE_UNPROVEN",
    "PUBLIC_ARTIFACT_AVAILABILITY_UNPROVEN",
    "OBSERVER_OPERATIONAL_INDEPENDENCE_UNPROVEN",
    "EXTERNAL_PERSISTENCE_UNPROVEN",
    "EXTERNAL_TIME_TRUTH_UNPROVEN",
    "TRADING_AUTHORITY_NOT_GRANTED",
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "artifact_promotion_allowed": False,
        "public_availability_promotion_allowed": False,
        "parameter_selection_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "result_available": False,
        "source_evaluation_verified": False,
        "catalog_scope_verified": False,
        "local_artifact_content_verified": False,
        "signed_checkpoint_verified": False,
        "inclusion_set_verified": False,
        "append_only_consistency_verified": False,
        "dual_observer_claims_verified": False,
        "dual_observer_result_agreement_verified": False,
        "external_log_trust_verified": False,
        "public_availability_verified": False,
        "external_persistence_verified": False,
        "external_time_truth_verified": False,
        "observer_independence_verified": False,
        "profitability_verified": False,
    }


def _summary() -> dict[str, int | None]:
    return {
        "artifact_count": None,
        "total_payload_bytes": None,
        "checkpoint_tree_size": None,
        "observer_count": None,
        "verified_inclusion_count": None,
        "signed_retrieval_claim_count": None,
    }


def _lineage() -> dict[str, str | None]:
    return {
        "source_evaluation_receipt_hash": None,
        "registration_receipt_hash": None,
        "artifact_catalog_root_hash": None,
        "transparency_checkpoint_hash": None,
        "transparency_checkpoint_root_hash": None,
        "observer_a_receipt_hash": None,
        "observer_b_receipt_hash": None,
        "observer_result_transcript_root_hash": None,
    }


def _unknown_axes(detail: str) -> list[dict[str, str]]:
    return [
        {
            "axis": axis,
            "state": "UNKNOWN",
            "signal": "UNKNOWN",
            "headline": "Evidence unavailable",
            "detail": detail,
        }
        for axis in AXIS_ORDER
    ]


def _sealed(
    *,
    display_state: str,
    source_schema: str | None,
    source_fingerprint: str | None,
    axes: list[dict[str, str]],
    summary: dict[str, int | None],
    lineage: dict[str, str | None],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "source_evaluation_schema": source_schema,
            "source_evaluation_fingerprint": source_fingerprint,
            "display_state": display_state,
            "axis_order": list(AXIS_ORDER),
            "axes": axes,
            "summary": summary,
            "lineage": lineage,
            "facts": facts,
            "authority": _authority(),
            "blockers": blockers,
        },
        "presentation_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    detail = (
        "The sealed artifact-transparency source did not verify for detached "
        "presentation."
    )
    return _sealed(
        display_state=UNKNOWN_DISPLAY_STATE,
        source_schema=None,
        source_fingerprint=None,
        axes=_unknown_axes(detail),
        summary=_summary(),
        lineage=_lineage(),
        facts=_facts(),
        blockers=[reason],
    )


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= 2**63 - 1


def _exact_dict(value: Any, keys: tuple[str, ...]) -> bool:
    return type(value) is dict and set(value) == set(keys)


def build_provider_identity_artifact_transparency_presentation_envelope_v1(
    source_evaluation_v1: Any,
    source_evaluation_inputs: Any,
    *,
    expected_source_evaluation_hash: Any,
) -> dict[str, Any]:
    if not _strict_hash(expected_source_evaluation_hash):
        return _unknown("EXPECTED_SOURCE_EVALUATION_HASH_INVALID")
    if type(source_evaluation_v1) is not dict or type(source_evaluation_inputs) is not dict:
        return _unknown("SOURCE_EVALUATION_INPUTS_INVALID")
    if source_evaluation_v1.get("receipt_hash") != expected_source_evaluation_hash:
        return _unknown("SOURCE_EVALUATION_HASH_MISMATCH")
    try:
        source_verified = source_contract.verify_provider_identity_artifact_transparency_availability_evaluation_v1(
            source_evaluation_v1,
            **source_evaluation_inputs,
        )
    except (KeyError, TypeError, ValueError):
        source_verified = False
    if not source_verified:
        return _unknown("SOURCE_EVALUATION_UNVERIFIED")
    if source_evaluation_v1.get("status") != SOURCE_VERIFIED_STATUS:
        return _unknown("SOURCE_EVALUATION_STATUS_INVALID")
    if (
        source_evaluation_v1.get("schema") != SOURCE_SCHEMA
        or source_evaluation_v1.get("static_fingerprint")
        != SOURCE_STATIC_FINGERPRINT
    ):
        return _unknown("SOURCE_CONTRACT_IDENTITY_INVALID")

    evidence = source_evaluation_v1.get("evidence")
    source_facts = source_evaluation_v1.get("facts")
    source_authority = source_evaluation_v1.get("authority")
    if not _exact_dict(evidence, SOURCE_EVIDENCE_KEYS):
        return _unknown("SOURCE_EVIDENCE_SHAPE_INVALID")
    if not _exact_dict(source_facts, SOURCE_FACT_KEYS):
        return _unknown("SOURCE_FACTS_SHAPE_INVALID")
    if not _exact_dict(source_authority, SOURCE_AUTHORITY_KEYS):
        return _unknown("SOURCE_AUTHORITY_SHAPE_INVALID")

    hash_fields = (
        "artifact_catalog_root_hash",
        "checkpoint_root_hash",
        "observer_a_receipt_hash",
        "observer_b_receipt_hash",
        "observer_result_transcript_root_hash",
        "registration_receipt_hash",
        "source_reproducibility_evaluation_receipt_hash",
        "transparency_checkpoint_hash",
    )
    if any(not _strict_hash(evidence[field]) for field in hash_fields):
        return _unknown("SOURCE_EVIDENCE_HASH_INVALID")
    if any(
        not _strict_int(evidence[field], minimum=1)
        for field in ("artifact_count", "checkpoint_tree_size")
    ) or any(
        not _strict_int(evidence[field])
        for field in ("total_payload_bytes", "reference_time_ms")
    ):
        return _unknown("SOURCE_EVIDENCE_INTEGER_INVALID")
    if evidence["checkpoint_tree_size"] < evidence["artifact_count"]:
        return _unknown("SOURCE_CHECKPOINT_SCOPE_INVALID")
    if evidence["observer_a_receipt_hash"] == evidence["observer_b_receipt_hash"]:
        return _unknown("SOURCE_OBSERVER_RECEIPTS_NOT_DISTINCT")

    if any(source_facts[field] is not True for field in SOURCE_TRUE_FACTS):
        return _unknown("SOURCE_POSITIVE_FACTS_INCOMPLETE")
    if any(source_facts[field] is not False for field in SOURCE_FALSE_FACTS):
        return _unknown("SOURCE_EXTERNAL_FACT_PROMOTION_REJECTED")
    for field in SOURCE_FACT_KEYS:
        if type(source_facts[field]) is not bool:
            return _unknown("SOURCE_FACT_TYPE_INVALID")
    for field in SOURCE_AUTHORITY_KEYS:
        expected = field == "research_only"
        if source_authority[field] is not expected:
            return _unknown("SOURCE_AUTHORITY_PROMOTION_REJECTED")

    artifact_count = evidence["artifact_count"]
    summary = {
        "artifact_count": artifact_count,
        "total_payload_bytes": evidence["total_payload_bytes"],
        "checkpoint_tree_size": evidence["checkpoint_tree_size"],
        "observer_count": 2,
        "verified_inclusion_count": artifact_count,
        "signed_retrieval_claim_count": artifact_count * 2,
    }
    lineage = {
        "source_evaluation_receipt_hash": source_evaluation_v1["receipt_hash"],
        "registration_receipt_hash": evidence["registration_receipt_hash"],
        "artifact_catalog_root_hash": evidence["artifact_catalog_root_hash"],
        "transparency_checkpoint_hash": evidence["transparency_checkpoint_hash"],
        "transparency_checkpoint_root_hash": evidence["checkpoint_root_hash"],
        "observer_a_receipt_hash": evidence["observer_a_receipt_hash"],
        "observer_b_receipt_hash": evidence["observer_b_receipt_hash"],
        "observer_result_transcript_root_hash": evidence[
            "observer_result_transcript_root_hash"
        ],
    }
    facts = _facts()
    facts.update(
        {
            "result_available": True,
            "source_evaluation_verified": True,
            "catalog_scope_verified": True,
            "local_artifact_content_verified": True,
            "signed_checkpoint_verified": True,
            "inclusion_set_verified": True,
            "append_only_consistency_verified": True,
            "dual_observer_claims_verified": True,
            "dual_observer_result_agreement_verified": True,
        }
    )
    axes = [
        {
            "axis": "SOURCE",
            "state": "LOCAL CONTENT BOUND",
            "signal": "VERIFIED_LOCAL",
            "headline": f"{artifact_count} supplied artifacts match the catalog",
            "detail": (
                f"{evidence['total_payload_bytes']} supplied bytes match catalog "
                "hashes and sizes; payload bytes are not projected."
            ),
        },
        {
            "axis": "GAP",
            "state": "PUBLIC AVAILABILITY OPEN",
            "signal": "BLOCKED",
            "headline": "External log and network retrieval remain unproven",
            "detail": (
                "Signed claims do not establish public reachability, independent "
                "operators, durable storage, or external time truth."
            ),
        },
        {
            "axis": "MATURITY",
            "state": "SIGNED CLAIM SET",
            "signal": "PARTIAL",
            "headline": f"{artifact_count} inclusions and two observer transcripts",
            "detail": (
                f"Checkpoint tree size {evidence['checkpoint_tree_size']} is bound "
                "with append-only consistency and matching signed result roots."
            ),
        },
        {
            "axis": "PERMISSION",
            "state": "RESEARCH ONLY",
            "signal": "LOCKED",
            "headline": "No promotion or trading authority",
            "detail": (
                "The detached view is descriptive only. Current admission, pointer "
                "writes, paper authorization, and live orders remain disabled."
            ),
        },
    ]
    return _sealed(
        display_state=POSITIVE_DISPLAY_STATE,
        source_schema=SOURCE_SCHEMA,
        source_fingerprint=SOURCE_STATIC_FINGERPRINT,
        axes=axes,
        summary=summary,
        lineage=lineage,
        facts=facts,
        blockers=list(VERIFIED_BLOCKERS),
    )


def verify_provider_identity_artifact_transparency_presentation_envelope_v1(
    document: Any,
    source_evaluation_v1: Any,
    source_evaluation_inputs: Any,
    *,
    expected_source_evaluation_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_provider_identity_artifact_transparency_presentation_envelope_v1(
            source_evaluation_v1,
            source_evaluation_inputs,
            expected_source_evaluation_hash=expected_source_evaluation_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected
