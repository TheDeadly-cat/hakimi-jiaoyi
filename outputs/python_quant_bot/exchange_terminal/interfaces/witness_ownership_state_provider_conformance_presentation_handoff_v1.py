"""Bounded unmounted handoff for the neutral ADR0415 presentation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from exchange_terminal.application import (
    witness_ownership_state_provider_conformance_presentation_envelope_v1 as presentation,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


HANDOFF_SCHEMA_VERSION = (
    "witness-ownership-provider-conformance-neutral-presentation-handoff-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-neutral-presentation-handoff-v1-lock-1"
)
VERIFICATION_STATUS = "EXACTLY_VERIFIED_NEUTRAL_BLOCKED_PRESENTATION_V1"
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)
PROTECTED_APP_SHA256 = (
    "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
)
PROTECTED_EVIDENCE_PRESENTATION_SHA256 = (
    "9822b147c583d29fc7c6d4866d73a0015914e2971458239ab3d1d1c2ff39e409"
)


def _permission() -> dict[str, bool | str]:
    return {
        "state": "BLOCKED",
        "descriptive_only": True,
        "asset_write_allowed": False,
        "browser_execution_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_witness_ownership_provider_conformance_presentation_handoff_v1(
    presentation_document: Any,
    observer_quorum_evidence_document: Any,
    signed_report_documents: Any,
    conformance_plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_presentation_envelope_hash: Any,
    presentation_build_kwargs: Any,
) -> dict[str, Any] | None:
    if type(presentation_build_kwargs) is not dict:
        return None
    if not presentation.verify_witness_ownership_provider_conformance_presentation_envelope_v1(
        presentation_document,
        observer_quorum_evidence_document,
        signed_report_documents,
        conformance_plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        expected_presentation_envelope_hash=(
            expected_presentation_envelope_hash
        ),
        **dict(presentation_build_kwargs),
    ):
        return None
    if (
        not isinstance(presentation_document, Mapping)
        or presentation_document.get("presentation_status")
        != presentation.PRESENTATION_STATUS
        or presentation_document.get("display_tone") != "NEUTRAL"
        or presentation_document.get("ordered_stage_contract")
        != list(presentation.ORDERED_STAGES)
        or presentation_document.get("axes", [{}])[-1].get("state")
        != "BLOCKED"
    ):
        return None
    payload = {
        "display_tone": presentation_document["display_tone"],
        "display_state": presentation_document["display_state"],
        "ordered_stage_contract": deepcopy(
            presentation_document["ordered_stage_contract"]
        ),
        "axes": deepcopy(presentation_document["axes"]),
        "summary": deepcopy(presentation_document["summary"]),
        "blockers": deepcopy(presentation_document["blockers"]),
        "permission": _permission(),
        "lineage": {
            "presentation_envelope_hash": (
                expected_presentation_envelope_hash
            )
        },
    }
    body = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_status": VERIFICATION_STATUS,
        "consumer_status": "UNMOUNTED_PAYLOAD_CANDIDATE",
        "payload": payload,
        "asset_boundary": {
            "consumer_javascript_sha256": None,
            "consumer_stylesheet_sha256": None,
            "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
            "protected_app_sha256": PROTECTED_APP_SHA256,
            "protected_evidence_presentation_sha256": (
                PROTECTED_EVIDENCE_PRESENTATION_SHA256
            ),
        },
        "facts": {
            "presentation_exactly_verified": True,
            "bounded_payload_built": True,
            "raw_source_documents_embedded": False,
            "raw_observer_reports_embedded": False,
            "raw_identity_material_embedded": False,
            "consumer_implementation_present": False,
            "asset_manifest_complete": False,
            "browser_executed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_assets_accessed": False,
            "profitability_proven": False,
        },
        "authority": _permission(),
    }
    return seal_strict_canonical_document(body, "handoff_hash")


def verify_witness_ownership_provider_conformance_presentation_handoff_v1(
    document: Any,
    presentation_document: Any,
    observer_quorum_evidence_document: Any,
    signed_report_documents: Any,
    conformance_plan_document: Any,
    provider_preregistration_document: Any,
    signed_receipt_evidence_document: Any,
    *,
    expected_handoff_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    expected = build_witness_ownership_provider_conformance_presentation_handoff_v1(
        presentation_document,
        observer_quorum_evidence_document,
        signed_report_documents,
        conformance_plan_document,
        provider_preregistration_document,
        signed_receipt_evidence_document,
        **build_kwargs,
    )
    return (
        expected is not None
        and expected.get("handoff_hash") == expected_handoff_hash
        and strict_json_contract_equal(dict(document), expected)
    )


__all__ = [
    "HANDOFF_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_STATUS",
    "build_witness_ownership_provider_conformance_presentation_handoff_v1",
    "verify_witness_ownership_provider_conformance_presentation_handoff_v1",
]
