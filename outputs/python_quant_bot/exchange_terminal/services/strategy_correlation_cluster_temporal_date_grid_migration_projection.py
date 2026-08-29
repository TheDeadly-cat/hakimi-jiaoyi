from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
    MODE_DRY_RUN,
    MODE_LIST,
    PLANNED_STEP_COUNT,
    verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment,
)


PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1-"
    "verification-v1"
)
STATIC_FINGERPRINT = "20260822-report22-date-grid-migration-projection-lock-1"

STATE_NOT_SUPPLIED = "NOT_SUPPLIED"
STATE_UNKNOWN = "UNKNOWN"
STATE_PLAN_LISTED = "PLAN_LISTED"
STATE_DRY_RUN_VERIFIED = "DRY_RUN_VERIFIED"

_NOT_SUPPLIED = object()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        if list(left) != list(right):
            return False
        return all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def _public_summary(state: str, *, report22_decision: str) -> dict[str, Any]:
    source_values = {
        STATE_NOT_SUPPLIED: {
            "assessment_contract": "NOT_SUPPLIED",
            "assessment_mode": "NOT_SUPPLIED",
            "report22_contract": "NOT_SUPPLIED",
            "report22_decision": "NOT_SUPPLIED",
        },
        STATE_UNKNOWN: {
            "assessment_contract": "UNKNOWN",
            "assessment_mode": "UNKNOWN",
            "report22_contract": "UNKNOWN",
            "report22_decision": "UNKNOWN",
        },
        STATE_PLAN_LISTED: {
            "assessment_contract": "VERIFIED",
            "assessment_mode": MODE_LIST,
            "report22_contract": "NOT_EVALUATED",
            "report22_decision": "NOT_EVALUATED",
        },
        STATE_DRY_RUN_VERIFIED: {
            "assessment_contract": "VERIFIED",
            "assessment_mode": MODE_DRY_RUN,
            "report22_contract": "VERIFIED",
            "report22_decision": report22_decision,
        },
    }
    gap_values = {
        STATE_NOT_SUPPLIED: "ASSESSMENT_NOT_SUPPLIED",
        STATE_UNKNOWN: "ASSESSMENT_UNKNOWN",
        STATE_PLAN_LISTED: "PLAN_ONLY",
        STATE_DRY_RUN_VERIFIED: "DRY_RUN_ONLY",
    }
    maturity_values = {
        STATE_NOT_SUPPLIED: "NOT_SUPPLIED",
        STATE_UNKNOWN: "UNKNOWN",
        STATE_PLAN_LISTED: "PLAN_LISTED_NOT_EXECUTED",
        STATE_DRY_RUN_VERIFIED: "DRY_RUN_VERIFIED_NOT_EXECUTED",
    }
    if state not in source_values:
        raise ValueError("unsupported public projection state")

    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
        "contract_fingerprint": STATIC_FINGERPRINT,
        "axis_order": ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        "source": {
            "state": state,
            **source_values[state],
        },
        "gap": {
            "state": gap_values[state],
            "execution": "NOT_EXECUTED",
            "runtime_mutations": "NONE",
            "migration_execution": "NOT_ALLOWED",
            "fresh_migration": "NOT_ALLOWED",
            "formal_registry": "NOT_BOUND",
            "writer": "NOT_AVAILABLE",
            "current": "NOT_ADMITTED",
        },
        "maturity": {
            "state": maturity_values[state],
            "report22_evaluation": source_values[state]["report22_contract"],
            "formal_registry": "NOT_BOUND",
            "current": "NOT_ADMITTED",
        },
        "permission": {
            "state": "RESEARCH_ONLY",
            "descriptive_only": True,
            "profitability_claim_allowed": False,
            "migration_execution_allowed": False,
            "writer_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "redaction": {
            "assessment_hash_exposed": False,
            "candidate_registration_hash_exposed": False,
            "report22_extension_hash_exposed": False,
            "expected_hashes_exposed": False,
            "identity_bindings_exposed": False,
            "raw_dates_exposed": False,
            "raw_prices_exposed": False,
            "returns_exposed": False,
            "correlations_exposed": False,
            "plan_details_exposed": False,
            "blocker_details_exposed": False,
            "profitability_metrics_exposed": False,
            "external_assets_embedded": False,
        },
    }


def _verification_arguments(
    *,
    candidate_registration: Any,
    mode: Any,
    expected_candidate_registration_hash: Any,
    report22_extension: Any,
    expected_report22_extension_hash: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_report21_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
    expected_temporal_date_grid_bindings: Any,
) -> dict[str, Any] | None:
    if candidate_registration is _NOT_SUPPLIED:
        return None
    arguments = {
        "candidate_registration": candidate_registration,
        "mode": mode,
        "expected_candidate_registration_hash": expected_candidate_registration_hash,
        "expected_report22_extension_hash": expected_report22_extension_hash,
        "expected_base_report_hash": expected_base_report_hash,
        "expected_global_independence_extension_hash": (
            expected_global_independence_extension_hash
        ),
        "expected_cluster_stability_extension_hash": (
            expected_cluster_stability_extension_hash
        ),
        "expected_report21_extension_hash": expected_report21_extension_hash,
        "expected_registry_bindings": expected_registry_bindings,
        "expected_stability_bindings": expected_stability_bindings,
        "expected_temporal_stability_bindings": (
            expected_temporal_stability_bindings
        ),
        "expected_temporal_date_grid_bindings": (
            expected_temporal_date_grid_bindings
        ),
    }
    if report22_extension is not _NOT_SUPPLIED:
        arguments["report22_extension"] = report22_extension
    return arguments


def _verified_public_state(
    verification: Any,
    *,
    mode: Any,
) -> tuple[str, str] | None:
    if type(verification) is not dict:
        return None
    if not _strict_equal(
        verification.get("schema_version"),
        ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
    ):
        return None
    if not _strict_equal(verification.get("status"), "PASS"):
        return None
    if not _strict_equal(verification.get("blockers"), []):
        return None
    if not _strict_equal(verification.get("planned"), PLANNED_STEP_COUNT):
        return None
    if not _strict_equal(verification.get("executed"), 0):
        return None
    for field in (
        "runtime_mutations",
        "migration_execution_allowed",
        "fresh_migration_allowed",
        "formal_registry_bound",
        "writer_available",
        "current_admission_allowed",
        "current_writer_activation_allowed",
    ):
        if not _strict_equal(verification.get(field), False):
            return None
    if not _strict_equal(
        verification.get("permissions"),
        {"paper_authorized": False, "live_order_allowed": False},
    ):
        return None

    assessment_status = verification.get("assessment_status")
    report22_decision = verification.get("report22_decision")
    if (
        _strict_equal(mode, MODE_LIST)
        and _strict_equal(assessment_status, STATE_PLAN_LISTED)
        and _strict_equal(report22_decision, "NOT_EVALUATED")
    ):
        return STATE_PLAN_LISTED, "NOT_EVALUATED"
    if (
        _strict_equal(mode, MODE_DRY_RUN)
        and _strict_equal(assessment_status, STATE_DRY_RUN_VERIFIED)
        and type(report22_decision) is str
        and report22_decision in {"PASS", "BLOCK"}
    ):
        return STATE_DRY_RUN_VERIFIED, report22_decision
    return None


def build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
    migration_assessment: Any = _NOT_SUPPLIED,
    *,
    candidate_registration: Any = _NOT_SUPPLIED,
    mode: Any = None,
    expected_candidate_registration_hash: Any = None,
    report22_extension: Any = _NOT_SUPPLIED,
    expected_report22_extension_hash: Any = None,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_report21_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
    expected_temporal_date_grid_bindings: Any = None,
) -> dict[str, Any]:
    if migration_assessment is _NOT_SUPPLIED:
        return _public_summary(STATE_NOT_SUPPLIED, report22_decision="NOT_SUPPLIED")

    arguments = _verification_arguments(
        candidate_registration=candidate_registration,
        mode=mode,
        expected_candidate_registration_hash=expected_candidate_registration_hash,
        report22_extension=report22_extension,
        expected_report22_extension_hash=expected_report22_extension_hash,
        expected_base_report_hash=expected_base_report_hash,
        expected_global_independence_extension_hash=(
            expected_global_independence_extension_hash
        ),
        expected_cluster_stability_extension_hash=(
            expected_cluster_stability_extension_hash
        ),
        expected_report21_extension_hash=expected_report21_extension_hash,
        expected_registry_bindings=expected_registry_bindings,
        expected_stability_bindings=expected_stability_bindings,
        expected_temporal_stability_bindings=expected_temporal_stability_bindings,
        expected_temporal_date_grid_bindings=expected_temporal_date_grid_bindings,
    )
    if arguments is None:
        return _public_summary(STATE_UNKNOWN, report22_decision="UNKNOWN")

    try:
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment(
                migration_assessment,
                **arguments,
            )
        )
    except (KeyError, TypeError, ValueError):
        return _public_summary(STATE_UNKNOWN, report22_decision="UNKNOWN")

    verified_state = _verified_public_state(verification, mode=mode)
    if verified_state is None:
        return _public_summary(STATE_UNKNOWN, report22_decision="UNKNOWN")
    state, report22_decision = verified_state
    return _public_summary(state, report22_decision=report22_decision)


def verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
    document: Any,
    migration_assessment: Any = _NOT_SUPPLIED,
    *,
    candidate_registration: Any = _NOT_SUPPLIED,
    mode: Any = None,
    expected_candidate_registration_hash: Any = None,
    report22_extension: Any = _NOT_SUPPLIED,
    expected_report22_extension_hash: Any = None,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_report21_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
    expected_temporal_date_grid_bindings: Any = None,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
            migration_assessment,
            candidate_registration=candidate_registration,
            mode=mode,
            expected_candidate_registration_hash=expected_candidate_registration_hash,
            report22_extension=report22_extension,
            expected_report22_extension_hash=expected_report22_extension_hash,
            expected_base_report_hash=expected_base_report_hash,
            expected_global_independence_extension_hash=(
                expected_global_independence_extension_hash
            ),
            expected_cluster_stability_extension_hash=(
                expected_cluster_stability_extension_hash
            ),
            expected_report21_extension_hash=expected_report21_extension_hash,
            expected_registry_bindings=expected_registry_bindings,
            expected_stability_bindings=expected_stability_bindings,
            expected_temporal_stability_bindings=(
                expected_temporal_stability_bindings
            ),
            expected_temporal_date_grid_bindings=(
                expected_temporal_date_grid_bindings
            ),
        )
    )
    exact_reconstruction = _strict_equal(document, expected)
    return {
        "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact_reconstruction else "BLOCK",
        "blockers": [] if exact_reconstruction else ["public_summary_exact_reconstruction"],
        "source_state": expected["source"]["state"],
        "exact_reconstruction": exact_reconstruction,
        "descriptive_only": True,
        "migration_execution_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATE_NOT_SUPPLIED",
    "STATE_UNKNOWN",
    "STATE_PLAN_LISTED",
    "STATE_DRY_RUN_VERIFIED",
    "build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
]
