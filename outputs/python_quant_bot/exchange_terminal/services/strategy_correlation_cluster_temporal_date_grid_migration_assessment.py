"""List/dry-run-only migration assessment for the report22 candidate."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_candidate_registration import (
    REGISTRATION_SCHEMA_VERSION as CANDIDATE_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    EXTENSION_SCHEMA_VERSION as REPORT22_EXTENSION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_report_extension,
)


ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-assessment-v1"
)
ASSESSMENT_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-assessment-v1-verification-v1"
)
MODE_LIST = "LIST"
MODE_DRY_RUN = "DRY_RUN"
PLANNED_STEP_COUNT = 3

_NOT_SUPPLIED = object()
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_PLAN_STEP_IDS = [
    "VERIFY_CANDIDATE_REGISTRATION_V10",
    "VERIFY_REPORT22_EXTENSION",
    "ASSESS_MIGRATION_PREREQUISITES",
]


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _verification(
    blockers: list[str],
    *,
    assessment_status: str = "BLOCK",
    report22_decision: str = "UNKNOWN",
) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    status = "PASS" if not unique else "BLOCK"
    return {
        "schema_version": ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": unique,
        "assessment_status": assessment_status if status == "PASS" else "BLOCK",
        "report22_decision": report22_decision if status == "PASS" else "UNKNOWN",
        "planned": PLANNED_STEP_COUNT,
        "executed": 0,
        "runtime_mutations": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def assess_strategy_correlation_cluster_temporal_date_grid_migration(
    candidate_registration: Any,
    *,
    mode: Any,
    expected_candidate_registration_hash: Any,
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
    if type(mode) is not str or mode not in {MODE_LIST, MODE_DRY_RUN}:
        raise ValueError("temporal_date_grid_migration_mode_invalid")
    registration = (
        candidate_registration if type(candidate_registration) is dict else {}
    )
    try:
        registration_verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
    except (KeyError, TypeError, ValueError):
        registration_verification = {"status": "BLOCK"}
    registration_verified = registration_verification.get("status") == "PASS"
    registration_hash_bound = (
        _is_sha256(expected_candidate_registration_hash)
        and registration.get("registration_hash")
        == expected_candidate_registration_hash
    )

    report_supplied = report22_extension is not _NOT_SUPPLIED
    report_verified = False
    report_hash_bound = False
    report22_decision = "NOT_EVALUATED" if mode == MODE_LIST else "UNKNOWN"
    if mode == MODE_DRY_RUN:
        report = report22_extension if type(report22_extension) is dict else {}
        try:
            report_verification = (
                verify_strategy_correlation_cluster_temporal_date_grid_report_extension(
                    report,
                    expected_base_report_hash=expected_base_report_hash,
                    expected_global_independence_extension_hash=(
                        expected_global_independence_extension_hash
                    ),
                    expected_cluster_stability_extension_hash=(
                        expected_cluster_stability_extension_hash
                    ),
                    expected_report21_extension_hash=(
                        expected_report21_extension_hash
                    ),
                    expected_registry_bindings=expected_registry_bindings,
                    expected_stability_bindings=expected_stability_bindings,
                    expected_temporal_stability_bindings=(
                        expected_temporal_stability_bindings
                    ),
                    expected_temporal_date_grid_bindings=(
                        expected_temporal_date_grid_bindings
                    ),
                )
                if type(report22_extension) is dict
                else {"status": "BLOCK", "decision": "BLOCK"}
            )
        except (KeyError, TypeError, ValueError):
            report_verification = {"status": "BLOCK", "decision": "BLOCK"}
        report_verified = report_verification.get("status") == "PASS"
        report_hash_bound = (
            _is_sha256(expected_report22_extension_hash)
            and report.get("extension_hash") == expected_report22_extension_hash
        )
        if report_verified and report_verification.get("decision") in {
            "PASS",
            "BLOCK",
        }:
            report22_decision = report_verification["decision"]

    facts = {
        "candidate_registration_v10_verified": registration_verified,
        "candidate_registration_hash_bound": registration_hash_bound,
        "report22_not_evaluated_in_list_mode": (
            mode != MODE_LIST or report_supplied is False
        ),
        "report22_extension_verified_in_dry_run": (
            mode != MODE_DRY_RUN or report_verified
        ),
        "report22_extension_hash_bound_in_dry_run": (
            mode != MODE_DRY_RUN or report_hash_bound
        ),
        "zero_execution_proven": True,
        "zero_runtime_mutation_proven": True,
    }
    blockers = [name for name, passed in facts.items() if passed is not True]
    if blockers:
        assessment_status = "BLOCK"
    elif mode == MODE_LIST:
        assessment_status = "PLAN_LISTED"
    else:
        assessment_status = "DRY_RUN_VERIFIED"

    if mode == MODE_LIST:
        step_statuses = ["VERIFIED", "NOT_EVALUATED", "PLANNED"]
    else:
        step_statuses = [
            "VERIFIED" if registration_verified and registration_hash_bound else "BLOCK",
            "VERIFIED" if report_verified and report_hash_bound else "BLOCK",
            "SATISFIED" if not blockers else "BLOCK",
        ]
    plan = [
        {"step_id": step_id, "status": step_status}
        for step_id, step_status in zip(
            _PLAN_STEP_IDS,
            step_statuses,
            strict=True,
        )
    ]
    assessment = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "mode": mode,
        "status": assessment_status,
        "candidate_registration_schema_version": (
            CANDIDATE_REGISTRATION_SCHEMA_VERSION
        ),
        "candidate_registration_hash": registration.get(
            "registration_hash", ""
        ),
        "report22_extension_schema_version": REPORT22_EXTENSION_SCHEMA_VERSION,
        "report22_extension_hash": (
            report22_extension.get("extension_hash", "")
            if mode == MODE_DRY_RUN and type(report22_extension) is dict
            else ""
        ),
        "report22_decision": report22_decision,
        "facts": facts,
        "blockers": blockers,
        "plan": plan,
        "planned": PLANNED_STEP_COUNT,
        "executed": 0,
        "runtime_mutations": False,
        "filesystem_reads": False,
        "filesystem_writes": False,
        "cache_reads": False,
        "cache_writes": False,
        "database_reads": False,
        "database_writes": False,
        "network_calls": False,
        "service_starts": False,
        "scheduler_mutations": False,
        "external_assets_embedded": False,
        "migration_prerequisites_observed": (
            assessment_status == "DRY_RUN_VERIFIED"
        ),
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "candidate_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(assessment, "assessment_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment(
    document: Any,
    *,
    candidate_registration: Any,
    mode: Any,
    expected_candidate_registration_hash: Any,
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
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("temporal_date_grid_migration_assessment_invalid")
    elif strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    try:
        expected = assess_strategy_correlation_cluster_temporal_date_grid_migration(
            candidate_registration,
            mode=mode,
            expected_candidate_registration_hash=(
                expected_candidate_registration_hash
            ),
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
    except (KeyError, TypeError, ValueError):
        return _verification(["temporal_date_grid_migration_source_invalid"])
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("temporal_date_grid_migration_contract_invalid")
    return _verification(
        blockers,
        assessment_status=expected["status"],
        report22_decision=expected["report22_decision"],
    )


__all__ = [
    "ASSESSMENT_SCHEMA_VERSION",
    "ASSESSMENT_VERIFICATION_SCHEMA_VERSION",
    "MODE_DRY_RUN",
    "MODE_LIST",
    "PLANNED_STEP_COUNT",
    "assess_strategy_correlation_cluster_temporal_date_grid_migration",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment",
]
