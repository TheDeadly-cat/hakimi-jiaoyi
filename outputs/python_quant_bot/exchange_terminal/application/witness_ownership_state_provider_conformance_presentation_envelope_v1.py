"""Neutral unmounted presentation envelope for ADR0414 evidence."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.application import (
    witness_ownership_state_provider_conformance_evidence_v1 as conformance_evidence,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-provider-conformance-neutral-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-neutral-presentation-v1-lock-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
UNKNOWN_PRESENTATION_STATUS = "UNMOUNTED_UNKNOWN"
DISPLAY_TONE = "NEUTRAL"
DISPLAY_STATE = (
    "LOCAL_EVIDENCE_BOUND_EXTERNAL_SOURCE_TRUTH_GAPS_OPEN_PERMISSION_BLOCKED"
)
ORDERED_STAGES = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_BLOCKERS = (
    "OBSERVER_ORGANIZATION_IDENTITIES_UNVERIFIED",
    "OBSERVER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
    "OBSERVER_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
    "OBSERVER_TEST_EXECUTION_SOURCE_TRUTH_UNVERIFIED",
    "PROVIDER_ENDPOINT_AND_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "DURABILITY_LINEARIZABILITY_AND_ROLLBACK_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "asset_write_allowed": False,
        "browser_execution_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "provider_call_allowed": False,
        "observer_report_trust_allowed": False,
        "provider_conformance_trust_allowed": False,
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _positive_axes() -> list[dict[str, str]]:
    return [
        {
            "stage": "SOURCE",
            "state": "LOCALLY_BOUND",
            "detail": (
                "ADR0412_ATOMIC_PORT_ADR0413_SIGNED_RECEIPT_ADR0414_"
                "OBSERVER_QUORUM_EXACTLY_REBUILT"
            ),
        },
        {
            "stage": "GAP",
            "state": "OPEN",
            "detail": (
                "OBSERVER_IDENTITY_INDEPENDENCE_EXTERNAL_EXECUTION_PROVIDER_"
                "SOURCE_TRUTH_DURABILITY_LINEARIZABILITY_ROLLBACK_UNVERIFIED"
            ),
        },
        {
            "stage": "MATURITY",
            "state": "SIGNED_REPORT_CANDIDATE",
            "detail": (
                "18_CASE_RESULTS_CLAIMED_BY_TWO_OF_THREE_LOCAL_SIGNATURE_"
                "QUORUM_EXTERNAL_EXECUTION_UNVERIFIED"
            ),
        },
        {
            "stage": "PERMISSION",
            "state": "BLOCKED",
            "detail": (
                "ASSETS_ROUTE_BROWSER_MOUNT_CURRENT_RUNTIME_PAPER_LIVE_DISABLED"
            ),
        },
    ]


def _unknown_axes(reason: str) -> list[dict[str, str]]:
    return [
        {"stage": stage, "state": "UNKNOWN", "detail": reason}
        for stage in ORDERED_STAGES
    ]


def _seal(
    *,
    presentation_status: str,
    display_state: str,
    axes: list[dict[str, str]],
    summary: dict[str, int | None],
    lineage: dict[str, str | None],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": presentation_status,
        "display_tone": DISPLAY_TONE,
        "display_state": display_state,
        "ordered_stage_contract": list(ORDERED_STAGES),
        "axes": axes,
        "summary": summary,
        "lineage": lineage,
        "facts": facts,
        "blockers": blockers,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "presentation_envelope_hash")


def _unknown(reason: str) -> dict[str, Any]:
    return _seal(
        presentation_status=UNKNOWN_PRESENTATION_STATUS,
        display_state="UNKNOWN",
        axes=_unknown_axes(reason),
        summary={
            "required_case_count": None,
            "claimed_case_count": None,
            "verified_execution_case_count": None,
            "submitted_observer_report_count": None,
            "passing_observer_report_count": None,
            "required_observer_quorum": None,
            "open_gap_count": None,
        },
        lineage={
            "provider_preregistration_hash": None,
            "signed_receipt_evidence_hash": None,
            "conformance_plan_hash": None,
            "observer_quorum_evidence_hash": None,
        },
        facts={
            "source_chain_exactly_verified": False,
            "bounded_projection": True,
            "signed_observer_report_quorum_verified": False,
            "raw_observer_reports_embedded": False,
            "raw_public_keys_embedded": False,
            "raw_signatures_embedded": False,
            "raw_provider_or_ownership_documents_embedded": False,
            "observer_test_execution_source_truth_verified": False,
            "external_provider_conformance_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "browser_executed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_assets_accessed": False,
            "profitability_proven": False,
        },
        blockers=[reason],
    )


def build_witness_ownership_provider_conformance_presentation_envelope_v1(
    observer_quorum_evidence_document: Any,
    signed_report_documents: Any,
    conformance_plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_observer_quorum_evidence_hash: Any,
    observer_quorum_evaluation_kwargs: Any,
) -> dict[str, Any]:
    if type(observer_quorum_evaluation_kwargs) is not dict:
        return _unknown("OBSERVER_QUORUM_EVALUATION_KWARGS_NOT_EXACT")
    try:
        exact = conformance_evidence.verify_witness_ownership_provider_conformance_observer_quorum_v1(
            observer_quorum_evidence_document,
            signed_report_documents,
            conformance_plan_document,
            provider_preregistration_document,
            signed_receipt_evidence_document,
            expected_quorum_evidence_hash=(
                expected_observer_quorum_evidence_hash
            ),
            **dict(observer_quorum_evaluation_kwargs),
        )
    except (KeyError, TypeError, ValueError):
        exact = False
    if not exact:
        return _unknown("OBSERVER_QUORUM_EVIDENCE_NOT_EXACT")
    if (
        not isinstance(observer_quorum_evidence_document, Mapping)
        or observer_quorum_evidence_document.get("status") != "PASS"
        or observer_quorum_evidence_document.get("admission_status")
        != "BLOCKED"
        or observer_quorum_evidence_document.get("conformance_status")
        != "SIGNED_OBSERVER_REPORT_QUORUM_CANDIDATE_BLOCKED"
    ):
        return _unknown("OBSERVER_QUORUM_STATUS_NOT_PRESENTABLE")

    facts = observer_quorum_evidence_document.get("facts")
    quorum_summary = observer_quorum_evidence_document.get("quorum_summary")
    source = observer_quorum_evidence_document.get("source")
    if (
        not isinstance(facts, Mapping)
        or not isinstance(quorum_summary, Mapping)
        or not isinstance(source, Mapping)
        or facts.get("signed_observer_report_quorum_verified") is not True
        or facts.get("observer_test_execution_source_truth_verified") is not False
        or facts.get("external_provider_conformance_verified") is not False
        or facts.get("durable_commit_verified") is not False
        or facts.get("linearizable_read_after_write_verified") is not False
        or facts.get("rollback_resistance_verified") is not False
    ):
        return _unknown("OBSERVER_QUORUM_FACTS_NOT_PRESENTABLE")
    passing_ids = quorum_summary.get("passing_observer_ids")
    if type(passing_ids) is not list or len(passing_ids) < 2:
        return _unknown("OBSERVER_QUORUM_SUMMARY_NOT_PRESENTABLE")

    return _seal(
        presentation_status=PRESENTATION_STATUS,
        display_state=DISPLAY_STATE,
        axes=_positive_axes(),
        summary={
            "required_case_count": 18,
            "claimed_case_count": 18,
            "verified_execution_case_count": 0,
            "submitted_observer_report_count": quorum_summary[
                "submitted_report_count"
            ],
            "passing_observer_report_count": len(passing_ids),
            "required_observer_quorum": quorum_summary[
                "required_signature_quorum"
            ],
            "open_gap_count": len(_BLOCKERS),
        },
        lineage={
            "provider_preregistration_hash": source[
                "provider_preregistration_hash"
            ],
            "signed_receipt_evidence_hash": source[
                "signed_receipt_evidence_hash"
            ],
            "conformance_plan_hash": source["conformance_plan_hash"],
            "observer_quorum_evidence_hash": (
                expected_observer_quorum_evidence_hash
            ),
        },
        facts={
            "source_chain_exactly_verified": True,
            "bounded_projection": True,
            "signed_observer_report_quorum_verified": True,
            "raw_observer_reports_embedded": False,
            "raw_public_keys_embedded": False,
            "raw_signatures_embedded": False,
            "raw_provider_or_ownership_documents_embedded": False,
            "observer_test_execution_source_truth_verified": False,
            "external_provider_conformance_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "browser_executed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_assets_accessed": False,
            "profitability_proven": False,
        },
        blockers=list(_BLOCKERS),
    )


def verify_witness_ownership_provider_conformance_presentation_envelope_v1(
    document: Any,
    observer_quorum_evidence_document: Any,
    signed_report_documents: Any,
    conformance_plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_presentation_envelope_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    expected = build_witness_ownership_provider_conformance_presentation_envelope_v1(
        observer_quorum_evidence_document,
        signed_report_documents,
        conformance_plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **build_kwargs,
    )
    return (
        expected.get("presentation_envelope_hash")
        == expected_presentation_envelope_hash
        and strict_json_contract_equal(dict(document), expected)
    )


__all__ = [
    "DISPLAY_STATE",
    "DISPLAY_TONE",
    "ORDERED_STAGES",
    "PRESENTATION_STATUS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_witness_ownership_provider_conformance_presentation_envelope_v1",
    "verify_witness_ownership_provider_conformance_presentation_envelope_v1",
]
