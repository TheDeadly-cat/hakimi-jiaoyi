"""Neutral unmounted presentation for source-baseline provider conformance."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_plan_v2 import (
    verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2,
    verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-anti-replay-provider-conformance-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-presentation-v1-lock-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
DISPLAY_STATE = "SOURCE_BOUND_CONFORMANCE_NOT_RUN_PERMISSION_BLOCKED"
UNKNOWN_DISPLAY_STATE = "UNKNOWN"
ORDERED_STAGES = ("SOURCE", "GAP", "MATURITY", "PERMISSION")


def _authority() -> dict[str, bool]:
    return {
        "provider_call_allowed": False,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _unknown_axes(reason: str) -> list[dict[str, str]]:
    return [
        {
            "stage": stage,
            "state": "UNKNOWN",
            "detail": reason,
        }
        for stage in ORDERED_STAGES
    ]


def _positive_axes() -> list[dict[str, str]]:
    return [
        {
            "stage": "SOURCE",
            "state": "BOUND",
            "detail": "V1_IDENTITY_AND_SOURCE_TRUST_EXACT_V2_BINDING_BLOCKED",
        },
        {
            "stage": "GAP",
            "state": "OPEN",
            "detail": "EXTERNAL_IDENTITY_TRUST_CONFORMANCE_ATOMICITY_DURABILITY_UNVERIFIED",
        },
        {
            "stage": "MATURITY",
            "state": "PREREGISTERED_NOT_RUN",
            "detail": "14_REQUIRED_CASES_0_EXECUTED_0_PASSED",
        },
        {
            "stage": "PERMISSION",
            "state": "BLOCKED",
            "detail": "PROVIDER_HTTP_UI_CURRENT_PAPER_LIVE_DISABLED",
        },
    ]


def _sealed(
    *,
    display_state: str,
    axes: list[dict[str, str]],
    summary: dict[str, int | None],
    lineage: dict[str, str | None],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_tone": "NEUTRAL",
        "display_state": display_state,
        "ordered_stage_contract": list(ORDERED_STAGES),
        "axes": axes,
        "summary": summary,
        "lineage": lineage,
        "facts": facts,
        "blockers": blockers,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "presentation_envelope_hash")


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed(
        display_state=UNKNOWN_DISPLAY_STATE,
        axes=_unknown_axes(reason),
        summary={
            "source_document_count": None,
            "required_case_count": None,
            "executed_case_count": None,
            "passed_case_count": None,
            "open_gap_count": None,
        },
        lineage={
            "provider_identity_binding_hash": None,
            "conformance_plan_hash": None,
            "namespace_preregistration_hash": None,
            "identity_preregistration_hash": None,
            "organization_identity_intake_hash": None,
            "signer_source_trust_preregistration_hash": None,
        },
        facts={
            "source_documents_exactly_verified": False,
            "bounded_projection": True,
            "raw_conformance_cases_embedded": False,
            "raw_identity_material_embedded": False,
            "provider_bound": False,
            "provider_called": False,
            "provider_conformance_verified": False,
            "atomic_compare_and_consume_verified": False,
            "linearizability_verified": False,
            "durable_commit_verified": False,
            "authenticated_consumption_receipt_issued": False,
            "http_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "profitability_proven": False,
        },
        blockers=[reason],
    )


def build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
    conformance_plan_document: Any,
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> dict[str, Any]:
    binding_exact = (
        verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
            provider_identity_binding_document,
            namespace_preregistration_document,
            identity_preregistration_document,
            organization_identity_intake_document,
            signer_source_trust_preregistration_document,
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
        )
    )
    if not binding_exact:
        return _unknown("PROVIDER_IDENTITY_BINDING_NOT_EXACT")
    plan_exact = verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
        conformance_plan_document,
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    if not plan_exact:
        return _unknown("PROVIDER_CONFORMANCE_PLAN_NOT_EXACT")
    if (
        conformance_plan_document.get("status") != "BLOCKED"
        or conformance_plan_document.get("plan_status")
        != "PREREGISTERED_NOT_RUN"
        or provider_identity_binding_document.get("status") != "BLOCKED"
    ):
        return _unknown("SOURCE_STATUS_NOT_PRESENTABLE")

    cases = conformance_plan_document["cases"]
    if (
        not isinstance(cases, list)
        or len(cases) != 14
        or any(item.get("execution_status") != "NOT_RUN" for item in cases)
    ):
        return _unknown("CONFORMANCE_CASE_COUNTS_NOT_EXACT")
    source_bindings = provider_identity_binding_document["source_bindings"]
    return _sealed(
        display_state=DISPLAY_STATE,
        axes=_positive_axes(),
        summary={
            "source_document_count": 6,
            "required_case_count": 14,
            "executed_case_count": 0,
            "passed_case_count": 0,
            "open_gap_count": 7,
        },
        lineage={
            "provider_identity_binding_hash": provider_identity_binding_document[
                "provider_identity_binding_hash"
            ],
            "conformance_plan_hash": conformance_plan_document[
                "conformance_plan_hash"
            ],
            "namespace_preregistration_hash": source_bindings[
                "namespace_preregistration_hash"
            ],
            "identity_preregistration_hash": source_bindings[
                "identity_preregistration_hash"
            ],
            "organization_identity_intake_hash": source_bindings[
                "organization_identity_intake_hash"
            ],
            "signer_source_trust_preregistration_hash": source_bindings[
                "signer_source_trust_preregistration_hash"
            ],
        },
        facts={
            "source_documents_exactly_verified": True,
            "bounded_projection": True,
            "raw_conformance_cases_embedded": False,
            "raw_identity_material_embedded": False,
            "provider_bound": False,
            "provider_called": False,
            "provider_conformance_verified": False,
            "atomic_compare_and_consume_verified": False,
            "linearizability_verified": False,
            "durable_commit_verified": False,
            "authenticated_consumption_receipt_issued": False,
            "http_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "profitability_proven": False,
        },
        blockers=[
            "EXTERNAL_REGISTRY_IDENTITY_UNVERIFIED",
            "EXTERNAL_SOURCE_TRUST_UNVERIFIED",
            "PROVIDER_CONFORMANCE_CASES_NOT_RUN",
            "ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
            "LINEARIZABILITY_UNVERIFIED",
            "DURABLE_COMMIT_UNVERIFIED",
            "AUTHENTICATED_CONSUMPTION_RECEIPT_NOT_ISSUED",
        ],
    )


def verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
    document: Any,
    conformance_plan_document: Any,
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    rebuilt = build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
        conformance_plan_document,
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    return strict_json_contract_equal(dict(document), rebuilt)
