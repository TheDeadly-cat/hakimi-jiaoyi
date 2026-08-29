from __future__ import annotations

from typing import Any

from exchange_terminal.application import (
    strategy_correlation_provider_evidence_presentation_envelope_v1 as envelope_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-provider-evidence-http-candidate-request-v1"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-provider-evidence-http-candidate-response-v1"
)
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-evidence-http-candidate-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
OBSERVED_STATE = "OBSERVED"
UNKNOWN_STATE = "UNKNOWN"

SOURCE_ENVELOPE_SCHEMA = envelope_contract.SCHEMA_VERSION
SOURCE_ENVELOPE_FINGERPRINT = envelope_contract.STATIC_FINGERPRINT

_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_summary",
        "provider_replay_gate",
    }
)


def _transport() -> dict[str, Any]:
    return {
        "registered": False,
        "externally_callable": False,
        "method": None,
        "route": None,
        "runtime_reads": False,
        "runtime_mutations": False,
        "cache_reads": False,
        "cache_writes": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "request_contract_valid": False,
        "source_envelope_verified": False,
        "source_envelope_observed": False,
        "result_available": False,
        "transport_registered": False,
    }


def _lineage(*, source_bound: bool) -> dict[str, Any]:
    return {
        "source_envelope_schema_version": (
            SOURCE_ENVELOPE_SCHEMA if source_bound else None
        ),
        "source_envelope_static_fingerprint": (
            SOURCE_ENVELOPE_FINGERPRINT if source_bound else None
        ),
        "request_documents_embedded": False,
        "verification_context_embedded": False,
    }


def _sealed(
    *,
    state: str,
    payload: dict[str, Any] | None,
    facts: dict[str, bool],
    lineage: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "interface_status": INTERFACE_STATUS,
            "state": state,
            "payload": payload,
            "facts": facts,
            "lineage": lineage,
            "transport": _transport(),
            "authority": _authority(),
            "blockers": blockers,
        },
        "response_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed(
        state=UNKNOWN_STATE,
        payload=None,
        facts=_facts(),
        lineage=_lineage(source_bound=False),
        blockers=[reason],
    )


def _request_valid(request_payload: Any) -> bool:
    return (
        type(request_payload) is dict
        and frozenset(request_payload) == _REQUEST_FIELDS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and type(request_payload.get("protocol_summary")) is dict
        and type(request_payload.get("provider_replay_gate")) is dict
    )


def _envelope_presentable(envelope: Any) -> bool:
    if type(envelope) is not dict:
        return False
    if (
        envelope.get("schema_version") != SOURCE_ENVELOPE_SCHEMA
        or envelope.get("static_fingerprint") != SOURCE_ENVELOPE_FINGERPRINT
        or envelope.get("presentation_status") != "UNMOUNTED_CANDIDATE"
        or envelope.get("axis_order") != list(envelope_contract.AXIS_ORDER)
    ):
        return False
    authority = envelope.get("authority")
    lineage = envelope.get("lineage")
    facts = envelope.get("facts")
    axes = envelope.get("axes")
    if not all(type(value) is dict for value in (authority, lineage, facts)):
        return False
    if type(axes) is not list or len(axes) != len(envelope_contract.AXIS_ORDER):
        return False
    if [axis.get("axis") for axis in axes if type(axis) is dict] != list(
        envelope_contract.AXIS_ORDER
    ):
        return False
    if (
        authority.get("descriptive_only") is not True
        or lineage.get("source_documents_embedded") is not False
        or lineage.get("verification_context_embedded") is not False
    ):
        return False
    for field in (
        "provider_gate_outcome_promotion_allowed",
        "maturity_promotion_allowed",
        "profitability_claim_allowed",
        "current_admission_allowed",
        "current_pointer_written",
        "paper_authorized",
        "live_order_allowed",
    ):
        if authority.get(field) is not False:
            return False
    display_state = envelope.get("display_state")
    if display_state == envelope_contract.POSITIVE_DISPLAY_STATE:
        return (
            facts.get("result_available") is True
            and facts.get("source_projection_verified") is True
            and facts.get("semantic_gate_outcome_projected") is False
            and axes[2].get("state") == "UNKNOWN"
            and axes[3].get("signal") == "LOCKED"
        )
    if display_state == envelope_contract.UNKNOWN_DISPLAY_STATE:
        return (
            facts.get("result_available") is False
            and facts.get("source_projection_verified") is False
            and all(axis.get("state") == "UNKNOWN" for axis in axes)
        )
    return False


def build_strategy_correlation_provider_evidence_http_candidate_response_v1(
    request_payload: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> dict[str, Any]:
    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")
    if (
        type(protocol_verification_context) is not dict
        or type(provider_replay_verification_context) is not dict
    ):
        return _unknown("VERIFICATION_CONTEXT_INVALID")

    protocol_summary = request_payload["protocol_summary"]
    provider_replay_gate = request_payload["provider_replay_gate"]
    try:
        envelope = envelope_contract.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
            protocol_summary,
            provider_replay_gate,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
        verified = envelope_contract.verify_strategy_correlation_provider_evidence_presentation_envelope_v1(
            envelope,
            protocol_summary,
            provider_replay_gate,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
    except Exception:
        return _unknown("SOURCE_ENVELOPE_VERIFIER_ERROR")
    if verified is not True or not _envelope_presentable(envelope):
        return _unknown("SOURCE_ENVELOPE_UNVERIFIED")

    observed = envelope.get("display_state") == envelope_contract.POSITIVE_DISPLAY_STATE
    facts = _facts()
    facts.update(
        {
            "request_contract_valid": True,
            "source_envelope_verified": True,
            "source_envelope_observed": observed,
            "result_available": observed,
        }
    )
    return _sealed(
        state=OBSERVED_STATE if observed else UNKNOWN_STATE,
        payload=envelope,
        facts=facts,
        lineage=_lineage(source_bound=True),
        blockers=[] if observed else ["SOURCE_PRESENTATION_UNKNOWN"],
    )


def verify_strategy_correlation_provider_evidence_http_candidate_response_v1(
    document: Any,
    request_payload: Any,
    *,
    protocol_verification_context: Any,
    provider_replay_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_provider_evidence_http_candidate_response_v1(
            request_payload,
            protocol_verification_context=protocol_verification_context,
            provider_replay_verification_context=provider_replay_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "INTERFACE_STATUS",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_provider_evidence_http_candidate_response_v1",
    "verify_strategy_correlation_provider_evidence_http_candidate_response_v1",
]
