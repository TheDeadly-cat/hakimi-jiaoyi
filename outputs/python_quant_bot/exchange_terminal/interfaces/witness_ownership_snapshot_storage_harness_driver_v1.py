"""Compatibility shim for the witness-ownership storage-harness driver application port."""

from exchange_terminal.application.ports.witness_ownership_snapshot_storage_harness_driver_v1 import (
    WitnessOwnershipSnapshotStorageHarnessDriverV1,
    WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1,
    WitnessOwnershipSnapshotStorageHarnessScenarioResultV1,
)


__all__ = [
    "WitnessOwnershipSnapshotStorageHarnessDriverV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioResultV1",
]
