from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1:
    contract_version: str
    scenario_sequence: int
    scenario_id: str
    requirement_id: str
    execution_mode: str
    driver_id: str
    storage_adapter_preregistration_hash: str
    isolated_domain_id_hash: str
    scenario_preregistration_hash: str
    harness_run_nonce_hash: str
    scenario_run_nonce_hash: str
    expected_adapter_implementation_sha256: str
    expected_storage_backend_kind: str
    command_hash: str


@dataclass(frozen=True)
class WitnessOwnershipSnapshotStorageHarnessScenarioResultV1:
    contract_version: str
    outcome: str
    command_hash: str
    scenario_id: str
    requirement_id: str
    isolated_domain_id_hash: str
    transcript_hash: str
    observed_artifact_hash: str
    runtime_mutations_outside_isolated_domain_claimed: bool
    paper_or_live_operation_claimed: bool
    automatic_retry_or_reissue_claimed: bool
    driver_result_hash: str


@runtime_checkable
class WitnessOwnershipSnapshotStorageHarnessDriverV1(Protocol):
    def execute_scenario(
        self,
        command: WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1,
        /,
    ) -> WitnessOwnershipSnapshotStorageHarnessScenarioResultV1:
        """Execute exactly one preregistered scenario in an isolated domain."""


__all__ = [
    "WitnessOwnershipSnapshotStorageHarnessDriverV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioResultV1",
]
