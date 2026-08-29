"""Compatibility shim for the witness-ownership publication-provider application port."""

from exchange_terminal.application.ports.witness_ownership_key_revocation_snapshot_publication_provider_v1 import (
    WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1,
    WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1,
    WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1,
    WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1,
)


__all__ = [
    "WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1",
]
