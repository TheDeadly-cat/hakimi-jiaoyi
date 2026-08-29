from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_provider_evidence_public_projection_v1 as projection_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-provider-evidence-presentation-envelope-v1"
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-evidence-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
POSITIVE_DISPLAY_STATE = "SOURCE_CONTRACTS_VERIFIED_GATE_OUTCOME_UNPROJECTED"
UNKNOWN_DISPLAY_STATE = "UNKNOWN"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

SOURCE_PROJECTION_SCHEMA = projection_contract.PROJECTION_SCHEMA_VERSION
SOURCE_PROJECTION_FINGERPRINT = projection_contract.STATIC_FINGERPRINT

VERIFIED_BLOCKERS = (
    "PROVIDER_GATE_OUTCOME_NOT_PROJECTED",
    "CURRENT_CONSUMER_BINDING_ABSENT",
    "NATURAL_FORWARD_CHAIN_BINDING_ABSENT",
    "DURABLE_EXTERNAL_PUBLICATION_UNPROVEN",
    "EXTERNAL_REGISTRY_AUTHORITY_UNPROVEN",
    "FUTURE_REPLAY_ABSENCE_UNPROVEN",
    "TRADING_AUTHORITY_NOT_GRANTED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "provider_gate_outcome_promotion_allowed": False,
        "maturity_promotion_allowed": False,
        "profitability_claim_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "result_available": False,
        "source_projection_verified": False,
        "protocol_summary_verified": False,
        "provider_replay_gate_verified": False,
        "semantic_gate_outcome_projected": False,
        "natural_forward_maturity_proven": False,
        "market_outcome_evidence_present": False,
        "profitability_proven": False,
    }


def _summary() -> dict[str, Any]:
    return {
        "source_contracts_verified": False,
        "provider_gate_outcome": None,
        "natural_forward_maturity": None,
        "current_reference_present": False,
    }


def _lineage(*, source_bound: bool) -> dict[str, Any]:
    return {
        "source_projection_schema_version": (
            SOURCE_PROJECTION_SCHEMA if source_bound else None
        ),
        "source_projection_static_fingerprint": (
            SOURCE_PROJECTION_FINGERPRINT if source_bound else None
        ),
        "source_documents_embedded": False,
        "verification_context_embedded": False,
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


def _positive_axes() -> list[dict[str, str]]:
    return [
        {
            "axis": "SOURCE",
            "state": "VERIFIED DOCUMENTS",
            "signal": "OBSERVED",
            "headline": "Registered source contracts verified",
            "detail": "The protocol summary and provider replay document passed their registered verifiers; this proves document integrity only.",
        },
        {
            "axis": "GAP",
            "state": "OUTCOME UNPROJECTED",
            "signal": "BLOCKED",
            "headline": "Provider gate outcome remains outside this view",
            "detail": "External publication, registry authority, future replay absence, and current consumer binding remain unproven.",
        },
        {
            "axis": "MATURITY",
            "state": "UNKNOWN",
            "signal": "UNKNOWN",
            "headline": "No maturity promotion",
            "detail": "Verified source documents do not establish natural-forward maturity or market outcomes.",
        },
        {
            "axis": "PERMISSION",
            "state": "RESEARCH ONLY",
            "signal": "LOCKED",
            "headline": "No admission or trading authority",
            "detail": "The envelope is descriptive and unmounted. Current writes, paper authorization, and live orders remain disabled.",
        },
    ]


def _sealed(
    *,
    display_state: str,
    axes: list[dict[str, str]],
    summary: dict[str, Any],
    lineage: dict[str, Any],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
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
    return _sealed(
        display_state=UNKNOWN_DISPLAY_STATE,
        axes=_unknown_axes(
            "The provider evidence projection did not verify for presentation."
        ),
        summary=_summary(),
        lineage=_lineage(source_bound=False),
        facts=_facts(),
        blockers=[reason],
    )


def _projection_is_presentable(
    projection: Any,
    verification: Any,
) -> bool:
    if type(projection) is not dict or type(verification) is not dict:
        return False
    if (
        projection.get("schema_version") != SOURCE_PROJECTION_SCHEMA
        or projection.get("static_fingerprint") != SOURCE_PROJECTION_FINGERPRINT
        or verification.get("status") != "PASS"
        or verification.get("upstream_source_contracts_verified") is not True
        or verification.get("provider_gate_outcome_proven") is not False
        or verification.get("current_admission_allowed") is not False
        or verification.get("paper_authorized") is not False
        or verification.get("live_order_allowed") is not False
    ):
        return False

    source = projection.get("source")
    gap = projection.get("gap")
    maturity = projection.get("maturity")
    activation = projection.get("activation")
    claims = projection.get("claims")
    redaction = projection.get("redaction")
    permission = projection.get("permission")
    if not all(
        type(value) is dict
        for value in (
            source,
            gap,
            maturity,
            activation,
            claims,
            redaction,
            permission,
        )
    ):
        return False
    if (
        source.get("status") != "OBSERVED"
        or source.get("strata_protocol_public_summary") != "VERIFIED"
        or source.get("provider_dataset_key_lifecycle_replay_gate") != "VERIFIED"
        or source.get("semantic_gate_outcome_projected") is not False
        or gap.get("status") != "OPEN"
        or gap.get("provider_gate_outcome") != "NOT_PROJECTED"
        or maturity.get("status") != "UNKNOWN"
        or maturity.get("source_contracts_verified") is not True
        or maturity.get("natural_forward_maturity_proven") is not False
        or maturity.get("market_outcome_evidence_present") is not False
        or activation.get("status") != "INACTIVE_CANDIDATE"
        or activation.get("current_reference_present") is not False
        or activation.get("automatic_activation_allowed") is not False
        or activation.get("current_pointer_mutation_allowed") is not False
        or claims.get("source_contract_integrity_verified") is not True
        or claims.get("provider_gate_outcome_proven") is not False
        or claims.get("profitability_proven") is not False
        or permission.get("status") != "RESEARCH_ONLY"
        or permission.get("descriptive_only") is not True
    ):
        return False
    for field in (
        "profitability_claim_allowed",
        "current_admission_allowed",
        "current_writer_activation_allowed",
        "paper_authorized",
        "live_order_allowed",
    ):
        if permission.get(field) is not False:
            return False
    return bool(redaction) and all(value is False for value in redaction.values())


def build_strategy_correlation_provider_evidence_presentation_envelope_v1(
    protocol_summary: Any,
    provider_replay_gate: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> dict[str, Any]:
    try:
        projection = projection_contract.build_strategy_correlation_provider_evidence_public_projection_v1(
            protocol_summary,
            provider_replay_gate,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
        verification = projection_contract.verify_strategy_correlation_provider_evidence_public_projection_v1(
            projection,
            protocol_summary,
            provider_replay_gate,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
    except Exception:
        return _unknown("SOURCE_PROJECTION_VERIFIER_ERROR")
    if not _projection_is_presentable(projection, verification):
        return _unknown("SOURCE_PROJECTION_UNVERIFIED")

    summary = _summary()
    summary["source_contracts_verified"] = True
    facts = _facts()
    facts.update(
        {
            "result_available": True,
            "source_projection_verified": True,
            "protocol_summary_verified": True,
            "provider_replay_gate_verified": True,
        }
    )
    return _sealed(
        display_state=POSITIVE_DISPLAY_STATE,
        axes=_positive_axes(),
        summary=summary,
        lineage=_lineage(source_bound=True),
        facts=facts,
        blockers=list(VERIFIED_BLOCKERS),
    )


def verify_strategy_correlation_provider_evidence_presentation_envelope_v1(
    document: Any,
    protocol_summary: Any,
    provider_replay_gate: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_provider_evidence_presentation_envelope_v1(
            protocol_summary,
            provider_replay_gate,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "AXIS_ORDER",
    "PRESENTATION_STATUS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_provider_evidence_presentation_envelope_v1",
    "verify_strategy_correlation_provider_evidence_presentation_envelope_v1",
]
