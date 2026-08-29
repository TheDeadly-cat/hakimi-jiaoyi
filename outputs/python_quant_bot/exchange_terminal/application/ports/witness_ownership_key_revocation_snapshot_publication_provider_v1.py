from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1:
    manifest_version: str
    stream_id: str
    revision: int
    snapshot_hash: str
    source_evaluation_hash: str
    publication_manifest_hash: str


@dataclass(frozen=True)
class WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1:
    head_version: str
    stream_id: str
    revision: int
    snapshot_hash: str | None
    publication_manifest_hash: str | None
    head_hash: str


@dataclass(frozen=True)
class WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1:
    contract_version: str
    request_version: str
    stream_id: str
    expected_head_hash: str
    expected_revision: int
    candidate_manifest: WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1
    request_nonce_hash: str
    request_hash: str


@dataclass(frozen=True)
class WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1:
    contract_version: str
    receipt_version: str
    outcome: str
    request_hash: str
    observed_head: WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1
    returned_head: WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1
    provider_content_addressed_object_claimed: bool
    provider_atomic_head_compare_and_swap_claimed: bool
    provider_durable_commit_claimed: bool
    receipt_hash: str


@runtime_checkable
class WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1(Protocol):
    """External publication boundary; implementations own all storage I/O."""

    def compare_and_swap_publish(
        self,
        request: WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1,
        /,
    ) -> WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1:
        """Attempt exactly one immutable-object publish and current-head CAS."""

    def read_current_head(
        self,
        *,
        stream_id: str,
    ) -> WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1:
        """Return the provider's current head for one preregistered stream."""


__all__ = [
    "WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1",
]
