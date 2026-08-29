"""Consumer-first isolated harness for future snapshot storage adapters.

Only a driver protocol is invoked.  This module owns no path, connection,
credential, backend, runtime storage, scheduler, browser, or trading action.
"""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as storage_preregistration,
)
from exchange_terminal.application.ports import (
    witness_ownership_snapshot_storage_harness_driver_v1 as port,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


CONTRACT_VERSION = "witness-ownership-snapshot-isolated-storage-harness-v1"
PLAN_SCHEMA_VERSION = "witness-ownership-snapshot-storage-harness-plan-v1"
EXECUTION_BUNDLE_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-harness-execution-bundle-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-isolated-storage-harness-v1-lock-1"
)

EXECUTION_MODE_DRIVER = "DRIVER_EXECUTABLE"
EXECUTION_MODE_OBSERVER_ONLY = "INDEPENDENT_OBSERVER_HANDOFF_ONLY"
OBSERVER_ONLY_REQUIREMENT_ID = "INDEPENDENT_DURABILITY_AND_READ_OBSERVER"

OUTCOME_PASS = "PASS"
OUTCOME_BLOCK = "BLOCK"
OUTCOME_UNKNOWN = "UNKNOWN"
ALLOWED_OUTCOMES = frozenset({OUTCOME_PASS, OUTCOME_BLOCK, OUTCOME_UNKNOWN})

STATUS_DRIVER_SCENARIOS_COMPLETE = (
    "DRIVER_SCENARIOS_STRUCTURALLY_COMPLETE_OBSERVER_HANDOFF_PENDING"
)
STATUS_BLOCK = "BLOCK"
GATE_STATUS_UNKNOWN = "UNKNOWN"
GATE_STATUS_BLOCK = "BLOCK"
PERMISSION_STATE = "RESEARCH_ONLY"

RUNNER_FAILURE_NONE = ""
RUNNER_FAILURE_DRIVER_EXCEPTION = "DRIVER_EXCEPTION"
RUNNER_FAILURE_DRIVER_RESULT_INVALID = "DRIVER_RESULT_INVALID"
_ALLOWED_RUNNER_FAILURES = frozenset(
    {
        RUNNER_FAILURE_NONE,
        RUNNER_FAILURE_DRIVER_EXCEPTION,
        RUNNER_FAILURE_DRIVER_RESULT_INVALID,
    }
)

STORAGE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "04afd17f55c4a287852f727aadf771772d6770e0f1f9db8ebd98040bb95bb52f"
)
STORAGE_EVIDENCE_QUORUM_IMPLEMENTATION_SHA256 = (
    "7111362ca0c1fa914bf6ea65a358347e6889e2f63184a520f5cdf0cdc37665a3"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any) -> bool:
    return type(value) is str and _TOKEN_RE.fullmatch(value) is not None


def build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
    storage_preregistration_document: Any,
    *,
    driver_id: Any,
    driver_implementation_sha256: Any,
    isolated_domain_id_hash: Any,
    plan_nonce_hash: Any,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(storage_preregistration_kwargs) is not dict:
        return {}
    if not storage_preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
        storage_preregistration_document,
        **storage_preregistration_kwargs,
    ):
        return {}
    if not _is_token(driver_id):
        return {}
    hashes = (
        driver_implementation_sha256,
        isolated_domain_id_hash,
        plan_nonce_hash,
    )
    if not all(_is_sha256(value) for value in hashes) or len(set(hashes)) != 3:
        return {}
    requirements = storage_preregistration_document["required_evidence"]
    scenarios: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        requirement_id = requirement["requirement_id"]
        execution_mode = (
            EXECUTION_MODE_OBSERVER_ONLY
            if requirement_id == OBSERVER_ONLY_REQUIREMENT_ID
            else EXECUTION_MODE_DRIVER
        )
        scenario_payload = {
            "scenario_sequence": index,
            "scenario_id": f"STORAGE_REQUIREMENT_{index:02d}",
            "requirement_id": requirement_id,
            "requirement_scope": requirement["requirement_scope"],
            "execution_mode": execution_mode,
            "storage_adapter_preregistration_hash": (
                storage_preregistration_document[
                    "storage_adapter_preregistration_hash"
                ]
            ),
            "isolated_domain_id_hash": isolated_domain_id_hash,
            "plan_nonce_hash": plan_nonce_hash,
        }
        scenarios.append(
            {
                **scenario_payload,
                "scenario_preregistration_hash": strict_canonical_hash(
                    scenario_payload
                ),
            }
        )
    driver_count = sum(
        row["execution_mode"] == EXECUTION_MODE_DRIVER for row in scenarios
    )
    observer_count = len(scenarios) - driver_count
    if driver_count != len(requirements) - 1 or observer_count != 1:
        return {}
    document = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": "UNMOUNTED_ISOLATED_HARNESS_PLAN",
        "storage_adapter_preregistration_hash": storage_preregistration_document[
            "storage_adapter_preregistration_hash"
        ],
        "storage_preregistration_implementation_sha256": (
            STORAGE_PREREGISTRATION_IMPLEMENTATION_SHA256
        ),
        "storage_evidence_quorum_implementation_sha256": (
            STORAGE_EVIDENCE_QUORUM_IMPLEMENTATION_SHA256
        ),
        "driver_id": driver_id,
        "driver_implementation_sha256": driver_implementation_sha256,
        "isolated_domain_id_hash": isolated_domain_id_hash,
        "plan_nonce_hash": plan_nonce_hash,
        "expected_scenario_count": len(scenarios),
        "expected_driver_scenario_count": driver_count,
        "expected_observer_handoff_count": observer_count,
        "scenarios": scenarios,
        "driver_runtime_observed": False,
        "isolated_domain_confinement_verified": False,
        "current_chain_activated": False,
    }
    return seal_strict_canonical_document(document, "harness_plan_hash")


def verify_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
    document: Any,
    storage_preregistration_document: Any,
    **build_kwargs: Any,
) -> bool:
    expected = build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
        storage_preregistration_document,
        **build_kwargs,
    )
    return bool(expected) and strict_json_contract_equal(document, expected)


def _scenario_by_id(plan_document: dict[str, Any], scenario_id: str) -> dict[str, Any] | None:
    rows = [row for row in plan_document["scenarios"] if row["scenario_id"] == scenario_id]
    return rows[0] if len(rows) == 1 else None


def build_witness_ownership_snapshot_storage_harness_scenario_command_v1(
    plan_document: Any,
    storage_preregistration_document: Any,
    *,
    scenario_id: Any,
    harness_run_nonce_hash: Any,
    plan_build_kwargs: Any,
    storage_preregistration_kwargs: Any,
) -> port.WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1 | None:
    if type(plan_build_kwargs) is not dict or not _is_sha256(harness_run_nonce_hash):
        return None
    if not verify_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
        plan_document,
        storage_preregistration_document,
        **plan_build_kwargs,
    ):
        return None
    if not _is_token(scenario_id):
        return None
    scenario = _scenario_by_id(plan_document, scenario_id)
    if scenario is None or scenario["execution_mode"] != EXECUTION_MODE_DRIVER:
        return None
    scenario_run_nonce_hash = strict_canonical_hash(
        {
            "harness_run_nonce_hash": harness_run_nonce_hash,
            "scenario_preregistration_hash": scenario[
                "scenario_preregistration_hash"
            ],
        }
    )
    payload = {
        "contract_version": CONTRACT_VERSION,
        "scenario_sequence": scenario["scenario_sequence"],
        "scenario_id": scenario["scenario_id"],
        "requirement_id": scenario["requirement_id"],
        "execution_mode": scenario["execution_mode"],
        "driver_id": plan_document["driver_id"],
        "storage_adapter_preregistration_hash": plan_document[
            "storage_adapter_preregistration_hash"
        ],
        "isolated_domain_id_hash": plan_document["isolated_domain_id_hash"],
        "scenario_preregistration_hash": scenario[
            "scenario_preregistration_hash"
        ],
        "harness_run_nonce_hash": harness_run_nonce_hash,
        "scenario_run_nonce_hash": scenario_run_nonce_hash,
        "expected_adapter_implementation_sha256": (
            storage_preregistration_document["storage_adapter"][
                "adapter_implementation_sha256"
            ]
        ),
        "expected_storage_backend_kind": storage_preregistration_document[
            "storage_domain"
        ]["storage_backend_kind"],
    }
    return port.WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1(
        **payload,
        command_hash=strict_canonical_hash(payload),
    )


def build_witness_ownership_snapshot_storage_harness_scenario_result_v1(
    command: Any,
    *,
    outcome: Any,
    transcript_hash: Any,
    observed_artifact_hash: Any,
    runtime_mutations_outside_isolated_domain_claimed: Any,
    paper_or_live_operation_claimed: Any,
    automatic_retry_or_reissue_claimed: Any,
) -> port.WitnessOwnershipSnapshotStorageHarnessScenarioResultV1 | None:
    if type(command) is not port.WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1:
        return None
    if outcome not in ALLOWED_OUTCOMES:
        return None
    if not _is_sha256(transcript_hash) or not _is_sha256(observed_artifact_hash):
        return None
    if transcript_hash == observed_artifact_hash:
        return None
    claims = (
        runtime_mutations_outside_isolated_domain_claimed,
        paper_or_live_operation_claimed,
        automatic_retry_or_reissue_claimed,
    )
    if any(type(value) is not bool for value in claims) or claims != (
        False,
        False,
        False,
    ):
        return None
    payload = {
        "contract_version": CONTRACT_VERSION,
        "outcome": outcome,
        "command_hash": command.command_hash,
        "scenario_id": command.scenario_id,
        "requirement_id": command.requirement_id,
        "isolated_domain_id_hash": command.isolated_domain_id_hash,
        "transcript_hash": transcript_hash,
        "observed_artifact_hash": observed_artifact_hash,
        "runtime_mutations_outside_isolated_domain_claimed": claims[0],
        "paper_or_live_operation_claimed": claims[1],
        "automatic_retry_or_reissue_claimed": claims[2],
    }
    return port.WitnessOwnershipSnapshotStorageHarnessScenarioResultV1(
        **payload,
        driver_result_hash=strict_canonical_hash(payload),
    )


def _is_exact_result(document: Any, command: Any) -> bool:
    if type(document) is not port.WitnessOwnershipSnapshotStorageHarnessScenarioResultV1:
        return False
    if (
        document.command_hash != command.command_hash
        or document.scenario_id != command.scenario_id
        or document.requirement_id != command.requirement_id
        or document.isolated_domain_id_hash != command.isolated_domain_id_hash
    ):
        return False
    rebuilt = build_witness_ownership_snapshot_storage_harness_scenario_result_v1(
        command,
        outcome=document.outcome,
        transcript_hash=document.transcript_hash,
        observed_artifact_hash=document.observed_artifact_hash,
        runtime_mutations_outside_isolated_domain_claimed=(
            document.runtime_mutations_outside_isolated_domain_claimed
        ),
        paper_or_live_operation_claimed=document.paper_or_live_operation_claimed,
        automatic_retry_or_reissue_claimed=(
            document.automatic_retry_or_reissue_claimed
        ),
    )
    return rebuilt == document


def build_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
    plan_document: Any,
    storage_preregistration_document: Any,
    scenario_result_documents: Any,
    *,
    harness_run_nonce_hash: Any,
    runner_failure_code: Any,
    failed_scenario_id: Any,
    plan_build_kwargs: Any,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if runner_failure_code not in _ALLOWED_RUNNER_FAILURES:
        return {}
    if type(scenario_result_documents) is not list:
        return {}
    if not verify_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
        plan_document,
        storage_preregistration_document,
        **plan_build_kwargs,
    ):
        return {}
    if not _is_sha256(harness_run_nonce_hash):
        return {}
    driver_rows = [
        row
        for row in plan_document["scenarios"]
        if row["execution_mode"] == EXECUTION_MODE_DRIVER
    ]
    if len(scenario_result_documents) > len(driver_rows):
        return {}
    normalized_results: list[dict[str, Any]] = []
    for index, result in enumerate(scenario_result_documents):
        command = build_witness_ownership_snapshot_storage_harness_scenario_command_v1(
            plan_document,
            storage_preregistration_document,
            scenario_id=driver_rows[index]["scenario_id"],
            harness_run_nonce_hash=harness_run_nonce_hash,
            plan_build_kwargs=plan_build_kwargs,
            storage_preregistration_kwargs=storage_preregistration_kwargs,
        )
        if command is None or not _is_exact_result(result, command):
            return {}
        normalized_results.append(asdict(result))

    next_scenario_id = (
        driver_rows[len(scenario_result_documents)]["scenario_id"]
        if len(scenario_result_documents) < len(driver_rows)
        else None
    )
    if runner_failure_code:
        if failed_scenario_id != next_scenario_id:
            return {}
        blocker = (
            "harness_driver_exception"
            if runner_failure_code == RUNNER_FAILURE_DRIVER_EXCEPTION
            else "harness_driver_result_invalid"
        )
    elif failed_scenario_id is not None:
        return {}
    elif any(result["outcome"] != OUTCOME_PASS for result in normalized_results):
        blocker = "harness_scenario_outcome_not_pass"
    elif len(normalized_results) != len(driver_rows):
        blocker = "harness_scenario_coverage_incomplete"
    elif len({result["transcript_hash"] for result in normalized_results}) != len(
        normalized_results
    ):
        blocker = "harness_transcript_replay_detected"
    elif len(
        {result["observed_artifact_hash"] for result in normalized_results}
    ) != len(normalized_results):
        blocker = "harness_observed_artifact_replay_detected"
    else:
        blocker = ""

    result_hashes = [result["driver_result_hash"] for result in normalized_results]
    driver_bundle_hash = (
        strict_canonical_hash({"driver_result_hashes": result_hashes})
        if result_hashes
        else None
    )
    observer_row = next(
        row
        for row in plan_document["scenarios"]
        if row["execution_mode"] == EXECUTION_MODE_OBSERVER_ONLY
    )
    observer_handoff_hash = (
        strict_canonical_hash(
            {
                "harness_plan_hash": plan_document["harness_plan_hash"],
                "driver_bundle_hash": driver_bundle_hash,
                "observer_requirement_id": observer_row["requirement_id"],
                "observer_scenario_preregistration_hash": observer_row[
                    "scenario_preregistration_hash"
                ],
            }
        )
        if not blocker
        else None
    )
    verified = not blocker
    evaluation = {
        "status": STATUS_DRIVER_SCENARIOS_COMPLETE if verified else STATUS_BLOCK,
        "gate_status": GATE_STATUS_UNKNOWN if verified else GATE_STATUS_BLOCK,
        "blocker_codes": [] if verified else [blocker],
        "expected_driver_scenario_count": len(driver_rows),
        "executed_driver_scenario_count": len(normalized_results),
        "expected_observer_handoff_count": 1,
        "observer_handoff_descriptor_built": verified,
        "observer_handoff_hash": observer_handoff_hash,
        "driver_scenarios_structurally_complete": verified,
        "driver_calls_per_scenario_maximum": 1,
        "driver_runtime_execution_verified": False,
        "isolated_domain_confinement_independently_verified": False,
        "external_observer_identity_verified": False,
        "external_persistence_independently_verified": False,
        "permission_state": PERMISSION_STATE,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
    }
    document = {
        "schema_version": EXECUTION_BUNDLE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "harness_plan_hash": plan_document["harness_plan_hash"],
        "harness_run_nonce_hash": harness_run_nonce_hash,
        "runner_failure_code": runner_failure_code,
        "failed_scenario_id": failed_scenario_id,
        "driver_bundle_hash": driver_bundle_hash,
        "scenario_result_documents": normalized_results,
        "evaluation": evaluation,
    }
    return seal_strict_canonical_document(document, "harness_execution_bundle_hash")


def run_witness_ownership_snapshot_isolated_storage_harness_v1(
    driver: port.WitnessOwnershipSnapshotStorageHarnessDriverV1,
    plan_document: Any,
    storage_preregistration_document: Any,
    *,
    harness_run_nonce_hash: Any,
    expected_harness_plan_hash: Any,
    plan_build_kwargs: Any,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if (
        not _is_sha256(expected_harness_plan_hash)
        or plan_document.get("harness_plan_hash") != expected_harness_plan_hash
    ):
        return {}
    driver_rows = [
        row
        for row in plan_document["scenarios"]
        if row["execution_mode"] == EXECUTION_MODE_DRIVER
    ]
    results: list[port.WitnessOwnershipSnapshotStorageHarnessScenarioResultV1] = []
    for row in driver_rows:
        command = build_witness_ownership_snapshot_storage_harness_scenario_command_v1(
            plan_document,
            storage_preregistration_document,
            scenario_id=row["scenario_id"],
            harness_run_nonce_hash=harness_run_nonce_hash,
            plan_build_kwargs=plan_build_kwargs,
            storage_preregistration_kwargs=storage_preregistration_kwargs,
        )
        if command is None:
            return {}
        try:
            result = driver.execute_scenario(command)
        except Exception:
            return build_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
                plan_document,
                storage_preregistration_document,
                results,
                harness_run_nonce_hash=harness_run_nonce_hash,
                runner_failure_code=RUNNER_FAILURE_DRIVER_EXCEPTION,
                failed_scenario_id=row["scenario_id"],
                plan_build_kwargs=plan_build_kwargs,
                storage_preregistration_kwargs=storage_preregistration_kwargs,
            )
        if not _is_exact_result(result, command):
            return build_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
                plan_document,
                storage_preregistration_document,
                results,
                harness_run_nonce_hash=harness_run_nonce_hash,
                runner_failure_code=RUNNER_FAILURE_DRIVER_RESULT_INVALID,
                failed_scenario_id=row["scenario_id"],
                plan_build_kwargs=plan_build_kwargs,
                storage_preregistration_kwargs=storage_preregistration_kwargs,
            )
        results.append(result)
        if result.outcome != OUTCOME_PASS:
            break
    return build_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
        plan_document,
        storage_preregistration_document,
        results,
        harness_run_nonce_hash=harness_run_nonce_hash,
        runner_failure_code=RUNNER_FAILURE_NONE,
        failed_scenario_id=None,
        plan_build_kwargs=plan_build_kwargs,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    )


def verify_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
    document: Any,
    plan_document: Any,
    storage_preregistration_document: Any,
    *,
    expected_harness_execution_bundle_hash: Any,
    plan_build_kwargs: Any,
    storage_preregistration_kwargs: Any,
) -> bool:
    if type(document) is not dict or not _is_sha256(
        expected_harness_execution_bundle_hash
    ):
        return False
    try:
        raw_results = document["scenario_result_documents"]
        results = [
            port.WitnessOwnershipSnapshotStorageHarnessScenarioResultV1(**item)
            for item in raw_results
        ]
        expected = build_witness_ownership_snapshot_storage_harness_execution_bundle_v1(
            plan_document,
            storage_preregistration_document,
            results,
            harness_run_nonce_hash=document["harness_run_nonce_hash"],
            runner_failure_code=document["runner_failure_code"],
            failed_scenario_id=document["failed_scenario_id"],
            plan_build_kwargs=plan_build_kwargs,
            storage_preregistration_kwargs=storage_preregistration_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        bool(expected)
        and expected.get("harness_execution_bundle_hash")
        == expected_harness_execution_bundle_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "ALLOWED_OUTCOMES",
    "CONTRACT_VERSION",
    "EXECUTION_BUNDLE_SCHEMA_VERSION",
    "EXECUTION_MODE_DRIVER",
    "EXECUTION_MODE_OBSERVER_ONLY",
    "GATE_STATUS_BLOCK",
    "GATE_STATUS_UNKNOWN",
    "OBSERVER_ONLY_REQUIREMENT_ID",
    "OUTCOME_BLOCK",
    "OUTCOME_PASS",
    "OUTCOME_UNKNOWN",
    "PERMISSION_STATE",
    "PLAN_SCHEMA_VERSION",
    "RUNNER_FAILURE_DRIVER_EXCEPTION",
    "RUNNER_FAILURE_DRIVER_RESULT_INVALID",
    "RUNNER_FAILURE_NONE",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "STATUS_DRIVER_SCENARIOS_COMPLETE",
    "build_witness_ownership_snapshot_isolated_storage_harness_plan_v1",
    "build_witness_ownership_snapshot_storage_harness_execution_bundle_v1",
    "build_witness_ownership_snapshot_storage_harness_scenario_command_v1",
    "build_witness_ownership_snapshot_storage_harness_scenario_result_v1",
    "run_witness_ownership_snapshot_isolated_storage_harness_v1",
    "verify_witness_ownership_snapshot_isolated_storage_harness_plan_v1",
    "verify_witness_ownership_snapshot_storage_harness_execution_bundle_v1",
]
