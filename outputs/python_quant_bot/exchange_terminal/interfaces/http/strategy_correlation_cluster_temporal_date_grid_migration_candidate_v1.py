from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_projection as projection_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    MODE_DRY_RUN,
    MODE_LIST,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-"
    "request-v1"
)
VERIFICATION_CONTEXT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-"
    "verification-context-v1"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-"
    "response-v1"
)
STATIC_FINGERPRINT = "20260822-report22-date-grid-migration-http-candidate-1"
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"

SOURCE_PROJECTION_SCHEMA = projection_contract.PUBLIC_SUMMARY_SCHEMA_VERSION
SOURCE_PROJECTION_FINGERPRINT = projection_contract.STATIC_FINGERPRINT
SOURCE_PROJECTION_VERIFICATION_SCHEMA = (
    projection_contract.PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION
)

_MISSING = object()
_REQUEST_FIELDS = frozenset({"schema_version"})
_LIST_CONTEXT_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_registration",
        "mode",
        "expected_candidate_registration_hash",
    }
)
_DRY_RUN_CONTEXT_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_registration",
        "mode",
        "expected_candidate_registration_hash",
        "report22_extension",
        "expected_report22_extension_hash",
        "expected_base_report_hash",
        "expected_global_independence_extension_hash",
        "expected_cluster_stability_extension_hash",
        "expected_report21_extension_hash",
        "expected_registry_bindings",
        "expected_stability_bindings",
        "expected_temporal_stability_bindings",
        "expected_temporal_date_grid_bindings",
    }
)

_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "contract_fingerprint",
        "axis_order",
        "source",
        "gap",
        "maturity",
        "permission",
        "redaction",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "state",
        "assessment_contract",
        "assessment_mode",
        "report22_contract",
        "report22_decision",
    }
)
_GAP_FIELDS = frozenset(
    {
        "state",
        "execution",
        "runtime_mutations",
        "migration_execution",
        "fresh_migration",
        "formal_registry",
        "writer",
        "current",
    }
)
_MATURITY_FIELDS = frozenset(
    {"state", "report22_evaluation", "formal_registry", "current"}
)
_PERMISSION_FIELDS = frozenset(
    {
        "state",
        "descriptive_only",
        "profitability_claim_allowed",
        "migration_execution_allowed",
        "writer_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
    }
)
_REDACTION_FIELDS = frozenset(
    {
        "assessment_hash_exposed",
        "candidate_registration_hash_exposed",
        "report22_extension_hash_exposed",
        "expected_hashes_exposed",
        "identity_bindings_exposed",
        "raw_dates_exposed",
        "raw_prices_exposed",
        "returns_exposed",
        "correlations_exposed",
        "plan_details_exposed",
        "blocker_details_exposed",
        "profitability_metrics_exposed",
        "external_assets_embedded",
    }
)
_VERIFICATION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "blockers",
        "source_state",
        "exact_reconstruction",
        "descriptive_only",
        "migration_execution_allowed",
        "writer_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
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
        "request_body_logging": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "route_registration_allowed": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "request_contract_valid": False,
        "trusted_context_contract_valid": False,
        "migration_assessment_supplied": False,
        "source_projection_verified": False,
        "source_assessment_observed": False,
        "report22_evaluated": False,
        "payload_available": False,
        "transport_registered": False,
        "runtime_asset_accessed": False,
    }


def _lineage(*, source_bound: bool) -> dict[str, Any]:
    return {
        "source_projection_schema_version": (
            SOURCE_PROJECTION_SCHEMA if source_bound else None
        ),
        "source_projection_static_fingerprint": (
            SOURCE_PROJECTION_FINGERPRINT if source_bound else None
        ),
        "request_documents_embedded": False,
        "migration_assessment_embedded": False,
        "verification_context_embedded": False,
        "report22_extension_embedded": False,
        "source_hashes_embedded": False,
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


def _unknown(
    reason: str,
    *,
    request_valid: bool = False,
    context_valid: bool = False,
    assessment_supplied: bool = False,
) -> dict[str, Any]:
    facts = _facts()
    facts.update(
        {
            "request_contract_valid": request_valid,
            "trusted_context_contract_valid": context_valid,
            "migration_assessment_supplied": assessment_supplied,
        }
    )
    return _sealed(
        state="UNKNOWN",
        payload=None,
        facts=facts,
        lineage=_lineage(source_bound=False),
        blockers=[reason],
    )


def _request_valid(request_payload: Any) -> bool:
    return bool(
        type(request_payload) is dict
        and frozenset(request_payload) == _REQUEST_FIELDS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
    )


def _verification_arguments(context: Any) -> dict[str, Any] | None:
    if type(context) is not dict:
        return None
    if context.get("schema_version") != VERIFICATION_CONTEXT_SCHEMA_VERSION:
        return None
    mode = context.get("mode")
    expected_fields = (
        _LIST_CONTEXT_FIELDS
        if type(mode) is str and mode == MODE_LIST
        else _DRY_RUN_CONTEXT_FIELDS
        if type(mode) is str and mode == MODE_DRY_RUN
        else None
    )
    if expected_fields is None or frozenset(context) != expected_fields:
        return None
    if type(context.get("candidate_registration")) is not dict:
        return None
    if type(context.get("expected_candidate_registration_hash")) is not str:
        return None
    return {
        key: value
        for key, value in context.items()
        if key != "schema_version"
    }


def _exact_section(document: Any, fields: frozenset[str]) -> bool:
    return type(document) is dict and frozenset(document) == fields


def _state_contract_valid(summary: dict[str, Any]) -> bool:
    source = summary["source"]
    gap = summary["gap"]
    maturity = summary["maturity"]
    state = source["state"]
    fixed = {
        "NOT_SUPPLIED": (
            "NOT_SUPPLIED",
            "NOT_SUPPLIED",
            "NOT_SUPPLIED",
            "NOT_SUPPLIED",
            "ASSESSMENT_NOT_SUPPLIED",
            "NOT_SUPPLIED",
            "NOT_SUPPLIED",
        ),
        "UNKNOWN": (
            "UNKNOWN",
            "UNKNOWN",
            "UNKNOWN",
            "UNKNOWN",
            "ASSESSMENT_UNKNOWN",
            "UNKNOWN",
            "UNKNOWN",
        ),
        "PLAN_LISTED": (
            "VERIFIED",
            MODE_LIST,
            "NOT_EVALUATED",
            "NOT_EVALUATED",
            "PLAN_ONLY",
            "PLAN_LISTED_NOT_EXECUTED",
            "NOT_EVALUATED",
        ),
    }
    if state in fixed:
        expected = fixed[state]
        actual = (
            source["assessment_contract"],
            source["assessment_mode"],
            source["report22_contract"],
            source["report22_decision"],
            gap["state"],
            maturity["state"],
            maturity["report22_evaluation"],
        )
        return all(
            type(actual_value) is type(expected_value)
            and actual_value == expected_value
            for actual_value, expected_value in zip(actual, expected)
        )
    return bool(
        state == "DRY_RUN_VERIFIED"
        and source["assessment_contract"] == "VERIFIED"
        and source["assessment_mode"] == MODE_DRY_RUN
        and source["report22_contract"] == "VERIFIED"
        and type(source["report22_decision"]) is str
        and source["report22_decision"] in {"PASS", "BLOCK"}
        and gap["state"] == "DRY_RUN_ONLY"
        and maturity["state"] == "DRY_RUN_VERIFIED_NOT_EXECUTED"
        and maturity["report22_evaluation"] == "VERIFIED"
    )


def _projection_presentable(summary: Any, verification: Any) -> bool:
    if (
        not _exact_section(summary, _ROOT_FIELDS)
        or not _exact_section(summary.get("source"), _SOURCE_FIELDS)
        or not _exact_section(summary.get("gap"), _GAP_FIELDS)
        or not _exact_section(summary.get("maturity"), _MATURITY_FIELDS)
        or not _exact_section(summary.get("permission"), _PERMISSION_FIELDS)
        or not _exact_section(summary.get("redaction"), _REDACTION_FIELDS)
        or not _exact_section(verification, _VERIFICATION_FIELDS)
    ):
        return False
    if (
        summary["schema_version"] != SOURCE_PROJECTION_SCHEMA
        or summary["contract_fingerprint"] != SOURCE_PROJECTION_FINGERPRINT
        or summary["axis_order"] != ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
        or verification["schema_version"]
        != SOURCE_PROJECTION_VERIFICATION_SCHEMA
        or verification["status"] != "PASS"
        or verification["blockers"] != []
        or verification["source_state"] != summary["source"]["state"]
        or verification["exact_reconstruction"] is not True
        or verification["descriptive_only"] is not True
    ):
        return False
    for field in (
        "migration_execution_allowed",
        "writer_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
    ):
        if verification[field] is not False:
            return False
    gap = summary["gap"]
    maturity = summary["maturity"]
    permission = summary["permission"]
    if (
        gap["execution"] != "NOT_EXECUTED"
        or gap["runtime_mutations"] != "NONE"
        or gap["migration_execution"] != "NOT_ALLOWED"
        or gap["fresh_migration"] != "NOT_ALLOWED"
        or gap["formal_registry"] != "NOT_BOUND"
        or gap["writer"] != "NOT_AVAILABLE"
        or gap["current"] != "NOT_ADMITTED"
        or maturity["formal_registry"] != "NOT_BOUND"
        or maturity["current"] != "NOT_ADMITTED"
        or permission["state"] != "RESEARCH_ONLY"
        or permission["descriptive_only"] is not True
    ):
        return False
    for field in _PERMISSION_FIELDS - {"state", "descriptive_only"}:
        if permission[field] is not False:
            return False
    if any(value is not False for value in summary["redaction"].values()):
        return False
    return _state_contract_valid(summary)


def _state_blockers(summary: dict[str, Any]) -> list[str]:
    state = summary["source"]["state"]
    blockers = ["TRANSPORT_UNREGISTERED", "MIGRATION_EXECUTION_NOT_ALLOWED"]
    if state == "NOT_SUPPLIED":
        blockers.append("MIGRATION_ASSESSMENT_NOT_SUPPLIED")
    elif state == "UNKNOWN":
        blockers.append("MIGRATION_ASSESSMENT_UNKNOWN")
    elif state == "PLAN_LISTED":
        blockers.append("REPORT22_NOT_EVALUATED")
    elif summary["source"]["report22_decision"] == "BLOCK":
        blockers.append("REPORT22_DECISION_BLOCK")
    return blockers


def build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
    request_payload: Any,
    *,
    migration_assessment: Any = _MISSING,
    verification_context: Any = None,
) -> dict[str, Any]:
    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")

    assessment_supplied = migration_assessment is not _MISSING
    if not assessment_supplied:
        if verification_context is not None:
            return _unknown(
                "VERIFICATION_CONTEXT_UNEXPECTED",
                request_valid=True,
            )
        arguments: dict[str, Any] = {}
    else:
        parsed_arguments = _verification_arguments(verification_context)
        if parsed_arguments is None:
            return _unknown(
                "VERIFICATION_CONTEXT_INVALID",
                request_valid=True,
                assessment_supplied=True,
            )
        arguments = parsed_arguments

    try:
        if assessment_supplied:
            summary = projection_contract.build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                migration_assessment,
                **arguments,
            )
            verification = projection_contract.verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                summary,
                migration_assessment,
                **arguments,
            )
        else:
            summary = projection_contract.build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary()
            verification = projection_contract.verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                summary
            )
    except Exception:
        return _unknown(
            "SOURCE_PROJECTION_VERIFIER_ERROR",
            request_valid=True,
            context_valid=True,
            assessment_supplied=assessment_supplied,
        )
    if not _projection_presentable(summary, verification):
        return _unknown(
            "SOURCE_PROJECTION_UNVERIFIED",
            request_valid=True,
            context_valid=True,
            assessment_supplied=assessment_supplied,
        )

    state = summary["source"]["state"]
    facts = _facts()
    facts.update(
        {
            "request_contract_valid": True,
            "trusted_context_contract_valid": True,
            "migration_assessment_supplied": assessment_supplied,
            "source_projection_verified": True,
            "source_assessment_observed": state
            in {"PLAN_LISTED", "DRY_RUN_VERIFIED"},
            "report22_evaluated": state == "DRY_RUN_VERIFIED",
            "payload_available": True,
        }
    )
    return _sealed(
        state=state,
        payload=summary,
        facts=facts,
        lineage=_lineage(source_bound=True),
        blockers=_state_blockers(summary),
    )


def verify_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
    document: Any,
    request_payload: Any,
    *,
    migration_assessment: Any = _MISSING,
    verification_context: Any = None,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            request_payload,
            migration_assessment=migration_assessment,
            verification_context=verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "INTERFACE_STATUS",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_CONTEXT_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1",
]
