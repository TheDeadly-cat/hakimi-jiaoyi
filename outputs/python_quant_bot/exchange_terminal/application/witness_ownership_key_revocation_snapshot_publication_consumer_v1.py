"""Consumer-first publication contract for witness key-revocation snapshots.

This module performs no filesystem, database, network, scheduler, or trading
I/O.  It binds one content-addressed snapshot manifest to one monotonic CAS
request, validates the provider receipt, and performs at most one post-success
current-head read.  It never retries or activates a public/current chain.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

from exchange_terminal.application.ports import (
    witness_ownership_key_revocation_snapshot_publication_provider_v1 as port,
)


CONTRACT_VERSION = (
    "witness-ownership-key-revocation-snapshot-publication-consumer-v1"
)
MANIFEST_VERSION = (
    "witness-ownership-key-revocation-snapshot-publication-manifest-v1"
)
HEAD_VERSION = "witness-ownership-key-revocation-snapshot-publication-head-v1"
REQUEST_VERSION = (
    "witness-ownership-key-revocation-snapshot-publication-request-v1"
)
RECEIPT_VERSION = (
    "witness-ownership-key-revocation-snapshot-publication-receipt-v1"
)
RESULT_VERSION = (
    "witness-ownership-key-revocation-snapshot-publication-result-v1"
)

OUTCOME_PUBLISHED = "PUBLISHED"
OUTCOME_ALREADY_CURRENT = "ALREADY_CURRENT"
OUTCOME_HEAD_CONFLICT = "HEAD_CONFLICT"
OUTCOME_BLOCK = "BLOCK"

STATUS_PUBLISHED_CURRENT_OBSERVED = "PUBLISHED_CURRENT_OBSERVED"
STATUS_ALREADY_CURRENT_OBSERVED = "ALREADY_CURRENT_OBSERVED"
STATUS_HEAD_CONFLICT = "HEAD_CONFLICT"
STATUS_BLOCK = "BLOCK"

GATE_STATUS_UNKNOWN = "UNKNOWN"
GATE_STATUS_BLOCK = "BLOCK"
PERMISSION_STATE_RESEARCH_ONLY = "RESEARCH_ONLY"

MAX_REVISION = (2**63) - 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")


@dataclass(frozen=True)
class WitnessOwnershipKeyRevocationSnapshotPublicationResultV1:
    contract_version: str
    result_version: str
    status: str
    gate_status: str
    blocker_codes: tuple[str, ...]
    stream_id: str
    candidate_revision: int
    candidate_snapshot_hash: str
    source_evaluation_hash: str
    publication_manifest_hash: str
    request_hash: str
    base_head_hash: str
    returned_head_hash: str | None
    post_read_head_hash: str | None
    provider_reported_publication_performed: bool
    post_read_current_head_observed: bool
    provider_content_addressed_object_claimed: bool
    provider_atomic_head_compare_and_swap_claimed: bool
    provider_durable_commit_claimed: bool
    external_persistence_independently_verified: bool
    provider_identity_verified: bool
    external_source_truth_verified: bool
    permission_state: str
    permission: bool
    paper_authorized: bool
    live_authorized: bool
    current_chain_activated: bool
    result_hash: str


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any) -> bool:
    return type(value) is str and _TOKEN_RE.fullmatch(value) is not None


def _is_revision(value: Any, *, allow_zero: bool) -> bool:
    minimum = 0 if allow_zero else 1
    return type(value) is int and minimum <= value <= MAX_REVISION


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return sha256(canonical).hexdigest()


def build_witness_ownership_key_revocation_snapshot_publication_manifest_v1(
    *,
    stream_id: Any,
    revision: Any,
    snapshot_hash: Any,
    source_evaluation_hash: Any,
) -> port.WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1 | None:
    if (
        not _is_token(stream_id)
        or not _is_revision(revision, allow_zero=False)
        or not _is_sha256(snapshot_hash)
        or not _is_sha256(source_evaluation_hash)
    ):
        return None
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "stream_id": stream_id,
        "revision": revision,
        "snapshot_hash": snapshot_hash,
        "source_evaluation_hash": source_evaluation_hash,
    }
    return port.WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1(
        **payload,
        publication_manifest_hash=_hash_payload(payload),
    )


def build_witness_ownership_key_revocation_snapshot_publication_head_v1(
    *,
    stream_id: Any,
    revision: Any,
    snapshot_hash: Any,
    publication_manifest_hash: Any,
) -> port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1 | None:
    if not _is_token(stream_id) or not _is_revision(revision, allow_zero=True):
        return None
    if revision == 0:
        if snapshot_hash is not None or publication_manifest_hash is not None:
            return None
    elif not (
        _is_sha256(snapshot_hash) and _is_sha256(publication_manifest_hash)
    ):
        return None
    payload = {
        "head_version": HEAD_VERSION,
        "stream_id": stream_id,
        "revision": revision,
        "snapshot_hash": snapshot_hash,
        "publication_manifest_hash": publication_manifest_hash,
    }
    return port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1(
        **payload,
        head_hash=_hash_payload(payload),
    )


def _is_exact_manifest(value: Any) -> bool:
    if type(value) is not port.WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1:
        return False
    rebuilt = build_witness_ownership_key_revocation_snapshot_publication_manifest_v1(
        stream_id=value.stream_id,
        revision=value.revision,
        snapshot_hash=value.snapshot_hash,
        source_evaluation_hash=value.source_evaluation_hash,
    )
    return rebuilt == value


def _is_exact_head(value: Any) -> bool:
    if type(value) is not port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1:
        return False
    rebuilt = build_witness_ownership_key_revocation_snapshot_publication_head_v1(
        stream_id=value.stream_id,
        revision=value.revision,
        snapshot_hash=value.snapshot_hash,
        publication_manifest_hash=value.publication_manifest_hash,
    )
    return rebuilt == value


def build_witness_ownership_key_revocation_snapshot_publication_request_v1(
    base_head: port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    *,
    candidate_revision: Any,
    candidate_snapshot_hash: Any,
    candidate_source_evaluation_hash: Any,
    request_nonce_hash: Any,
    expected_base_head_hash: Any,
    expected_stream_id: Any,
) -> port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1 | None:
    if not _is_exact_head(base_head):
        return None
    if (
        not _is_sha256(expected_base_head_hash)
        or expected_base_head_hash != base_head.head_hash
        or not _is_token(expected_stream_id)
        or expected_stream_id != base_head.stream_id
        or not _is_sha256(request_nonce_hash)
        or not _is_revision(candidate_revision, allow_zero=False)
        or candidate_revision != base_head.revision + 1
    ):
        return None
    manifest = (
        build_witness_ownership_key_revocation_snapshot_publication_manifest_v1(
            stream_id=base_head.stream_id,
            revision=candidate_revision,
            snapshot_hash=candidate_snapshot_hash,
            source_evaluation_hash=candidate_source_evaluation_hash,
        )
    )
    if manifest is None:
        return None
    payload = {
        "contract_version": CONTRACT_VERSION,
        "request_version": REQUEST_VERSION,
        "stream_id": base_head.stream_id,
        "expected_head_hash": base_head.head_hash,
        "expected_revision": base_head.revision,
        "candidate_manifest": asdict(manifest),
        "request_nonce_hash": request_nonce_hash,
    }
    return port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1(
        contract_version=CONTRACT_VERSION,
        request_version=REQUEST_VERSION,
        stream_id=base_head.stream_id,
        expected_head_hash=base_head.head_hash,
        expected_revision=base_head.revision,
        candidate_manifest=manifest,
        request_nonce_hash=request_nonce_hash,
        request_hash=_hash_payload(payload),
    )


def _is_exact_request(value: Any) -> bool:
    if type(value) is not port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1:
        return False
    if (
        value.contract_version != CONTRACT_VERSION
        or value.request_version != REQUEST_VERSION
        or not _is_token(value.stream_id)
        or not _is_sha256(value.expected_head_hash)
        or not _is_revision(value.expected_revision, allow_zero=True)
        or not _is_exact_manifest(value.candidate_manifest)
        or value.candidate_manifest.stream_id != value.stream_id
        or value.candidate_manifest.revision != value.expected_revision + 1
        or not _is_sha256(value.request_nonce_hash)
        or not _is_sha256(value.request_hash)
    ):
        return False
    payload = {
        "contract_version": value.contract_version,
        "request_version": value.request_version,
        "stream_id": value.stream_id,
        "expected_head_hash": value.expected_head_hash,
        "expected_revision": value.expected_revision,
        "candidate_manifest": asdict(value.candidate_manifest),
        "request_nonce_hash": value.request_nonce_hash,
    }
    return value.request_hash == _hash_payload(payload)


def _candidate_head(
    request: port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1,
) -> port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1 | None:
    if not _is_exact_request(request):
        return None
    manifest = request.candidate_manifest
    return build_witness_ownership_key_revocation_snapshot_publication_head_v1(
        stream_id=request.stream_id,
        revision=manifest.revision,
        snapshot_hash=manifest.snapshot_hash,
        publication_manifest_hash=manifest.publication_manifest_hash,
    )


def build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
    request: port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1,
    observed_head: port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    returned_head: port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    *,
    outcome: Any,
    provider_content_addressed_object_claimed: Any,
    provider_atomic_head_compare_and_swap_claimed: Any,
    provider_durable_commit_claimed: Any,
) -> port.WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1 | None:
    if (
        not _is_exact_request(request)
        or not _is_exact_head(observed_head)
        or not _is_exact_head(returned_head)
        or observed_head.stream_id != request.stream_id
        or returned_head.stream_id != request.stream_id
        or type(provider_content_addressed_object_claimed) is not bool
        or type(provider_atomic_head_compare_and_swap_claimed) is not bool
        or type(provider_durable_commit_claimed) is not bool
    ):
        return None
    candidate_head = _candidate_head(request)
    if candidate_head is None:
        return None
    claims = (
        provider_content_addressed_object_claimed,
        provider_atomic_head_compare_and_swap_claimed,
        provider_durable_commit_claimed,
    )
    if outcome == OUTCOME_PUBLISHED:
        valid = (
            observed_head.head_hash == request.expected_head_hash
            and observed_head.revision == request.expected_revision
            and returned_head == candidate_head
            and claims == (True, True, True)
        )
    elif outcome == OUTCOME_ALREADY_CURRENT:
        valid = (
            observed_head == candidate_head
            and returned_head == candidate_head
            and claims == (True, False, True)
        )
    elif outcome == OUTCOME_HEAD_CONFLICT:
        valid = (
            observed_head == returned_head
            and observed_head.head_hash != request.expected_head_hash
            and observed_head != candidate_head
            and claims == (False, False, False)
        )
    elif outcome == OUTCOME_BLOCK:
        valid = observed_head == returned_head and claims == (False, False, False)
    else:
        return None
    if not valid:
        return None
    payload = {
        "contract_version": CONTRACT_VERSION,
        "receipt_version": RECEIPT_VERSION,
        "outcome": outcome,
        "request_hash": request.request_hash,
        "observed_head": asdict(observed_head),
        "returned_head": asdict(returned_head),
        "provider_content_addressed_object_claimed": claims[0],
        "provider_atomic_head_compare_and_swap_claimed": claims[1],
        "provider_durable_commit_claimed": claims[2],
    }
    return port.WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1(
        contract_version=CONTRACT_VERSION,
        receipt_version=RECEIPT_VERSION,
        outcome=outcome,
        request_hash=request.request_hash,
        observed_head=observed_head,
        returned_head=returned_head,
        provider_content_addressed_object_claimed=claims[0],
        provider_atomic_head_compare_and_swap_claimed=claims[1],
        provider_durable_commit_claimed=claims[2],
        receipt_hash=_hash_payload(payload),
    )


def _receipt_matches_request(value: Any, request: Any) -> bool:
    if (
        type(value) is not port.WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1
        or not _is_exact_request(request)
        or value.contract_version != CONTRACT_VERSION
        or value.receipt_version != RECEIPT_VERSION
        or value.request_hash != request.request_hash
        or not _is_sha256(value.receipt_hash)
    ):
        return False
    rebuilt = build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
        request,
        value.observed_head,
        value.returned_head,
        outcome=value.outcome,
        provider_content_addressed_object_claimed=(
            value.provider_content_addressed_object_claimed
        ),
        provider_atomic_head_compare_and_swap_claimed=(
            value.provider_atomic_head_compare_and_swap_claimed
        ),
        provider_durable_commit_claimed=value.provider_durable_commit_claimed,
    )
    return rebuilt == value


def _build_result(
    request: port.WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1,
    base_head: port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    *,
    status: str,
    gate_status: str,
    blocker_codes: tuple[str, ...],
    receipt: port.WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1 | None,
    post_read_head_hash: str | None,
    post_read_current_head_observed: bool,
) -> WitnessOwnershipKeyRevocationSnapshotPublicationResultV1:
    manifest = request.candidate_manifest
    payload = {
        "contract_version": CONTRACT_VERSION,
        "result_version": RESULT_VERSION,
        "status": status,
        "gate_status": gate_status,
        "blocker_codes": list(blocker_codes),
        "stream_id": request.stream_id,
        "candidate_revision": manifest.revision,
        "candidate_snapshot_hash": manifest.snapshot_hash,
        "source_evaluation_hash": manifest.source_evaluation_hash,
        "publication_manifest_hash": manifest.publication_manifest_hash,
        "request_hash": request.request_hash,
        "base_head_hash": base_head.head_hash,
        "returned_head_hash": (
            receipt.returned_head.head_hash if receipt is not None else None
        ),
        "post_read_head_hash": post_read_head_hash,
        "provider_reported_publication_performed": (
            receipt is not None and receipt.outcome == OUTCOME_PUBLISHED
        ),
        "post_read_current_head_observed": post_read_current_head_observed,
        "provider_content_addressed_object_claimed": (
            receipt.provider_content_addressed_object_claimed
            if receipt is not None
            else False
        ),
        "provider_atomic_head_compare_and_swap_claimed": (
            receipt.provider_atomic_head_compare_and_swap_claimed
            if receipt is not None
            else False
        ),
        "provider_durable_commit_claimed": (
            receipt.provider_durable_commit_claimed
            if receipt is not None
            else False
        ),
        "external_persistence_independently_verified": False,
        "provider_identity_verified": False,
        "external_source_truth_verified": False,
        "permission_state": PERMISSION_STATE_RESEARCH_ONLY,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "current_chain_activated": False,
    }
    return WitnessOwnershipKeyRevocationSnapshotPublicationResultV1(
        contract_version=CONTRACT_VERSION,
        result_version=RESULT_VERSION,
        status=status,
        gate_status=gate_status,
        blocker_codes=blocker_codes,
        stream_id=request.stream_id,
        candidate_revision=manifest.revision,
        candidate_snapshot_hash=manifest.snapshot_hash,
        source_evaluation_hash=manifest.source_evaluation_hash,
        publication_manifest_hash=manifest.publication_manifest_hash,
        request_hash=request.request_hash,
        base_head_hash=base_head.head_hash,
        returned_head_hash=payload["returned_head_hash"],
        post_read_head_hash=post_read_head_hash,
        provider_reported_publication_performed=payload[
            "provider_reported_publication_performed"
        ],
        post_read_current_head_observed=post_read_current_head_observed,
        provider_content_addressed_object_claimed=payload[
            "provider_content_addressed_object_claimed"
        ],
        provider_atomic_head_compare_and_swap_claimed=payload[
            "provider_atomic_head_compare_and_swap_claimed"
        ],
        provider_durable_commit_claimed=payload["provider_durable_commit_claimed"],
        external_persistence_independently_verified=False,
        provider_identity_verified=False,
        external_source_truth_verified=False,
        permission_state=PERMISSION_STATE_RESEARCH_ONLY,
        permission=False,
        paper_authorized=False,
        live_authorized=False,
        current_chain_activated=False,
        result_hash=_hash_payload(payload),
    )


def publish_witness_ownership_key_revocation_snapshot_v1(
    provider: port.WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1,
    base_head: port.WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1,
    *,
    candidate_revision: Any,
    candidate_snapshot_hash: Any,
    candidate_source_evaluation_hash: Any,
    request_nonce_hash: Any,
    expected_base_head_hash: Any,
    expected_stream_id: Any,
) -> WitnessOwnershipKeyRevocationSnapshotPublicationResultV1 | None:
    request = build_witness_ownership_key_revocation_snapshot_publication_request_v1(
        base_head,
        candidate_revision=candidate_revision,
        candidate_snapshot_hash=candidate_snapshot_hash,
        candidate_source_evaluation_hash=candidate_source_evaluation_hash,
        request_nonce_hash=request_nonce_hash,
        expected_base_head_hash=expected_base_head_hash,
        expected_stream_id=expected_stream_id,
    )
    if request is None:
        return None

    request_hash_before = request.request_hash
    base_head_hash_before = base_head.head_hash
    try:
        receipt = provider.compare_and_swap_publish(request)
    except Exception:
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_provider_exception",),
            receipt=None,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )

    if (
        not _is_exact_request(request)
        or request.request_hash != request_hash_before
        or not _is_exact_head(base_head)
        or base_head.head_hash != base_head_hash_before
        or not _receipt_matches_request(receipt, request)
    ):
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_receipt_invalid",),
            receipt=None,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )

    if receipt.outcome == OUTCOME_HEAD_CONFLICT:
        return _build_result(
            request,
            base_head,
            status=STATUS_HEAD_CONFLICT,
            gate_status=GATE_STATUS_UNKNOWN,
            blocker_codes=("publication_head_compare_and_swap_conflict",),
            receipt=receipt,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )
    if receipt.outcome == OUTCOME_BLOCK:
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_provider_blocked",),
            receipt=receipt,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )

    try:
        post_read_head = provider.read_current_head(stream_id=request.stream_id)
    except Exception:
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_post_read_exception",),
            receipt=receipt,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )
    if not _is_exact_head(post_read_head):
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_post_read_invalid",),
            receipt=receipt,
            post_read_head_hash=None,
            post_read_current_head_observed=False,
        )
    if post_read_head != receipt.returned_head:
        return _build_result(
            request,
            base_head,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("publication_post_read_mismatch",),
            receipt=receipt,
            post_read_head_hash=post_read_head.head_hash,
            post_read_current_head_observed=False,
        )

    status = (
        STATUS_PUBLISHED_CURRENT_OBSERVED
        if receipt.outcome == OUTCOME_PUBLISHED
        else STATUS_ALREADY_CURRENT_OBSERVED
    )
    return _build_result(
        request,
        base_head,
        status=status,
        gate_status=GATE_STATUS_UNKNOWN,
        blocker_codes=(),
        receipt=receipt,
        post_read_head_hash=post_read_head.head_hash,
        post_read_current_head_observed=True,
    )


__all__ = [
    "CONTRACT_VERSION",
    "GATE_STATUS_BLOCK",
    "GATE_STATUS_UNKNOWN",
    "HEAD_VERSION",
    "MANIFEST_VERSION",
    "OUTCOME_ALREADY_CURRENT",
    "OUTCOME_BLOCK",
    "OUTCOME_HEAD_CONFLICT",
    "OUTCOME_PUBLISHED",
    "PERMISSION_STATE_RESEARCH_ONLY",
    "RECEIPT_VERSION",
    "REQUEST_VERSION",
    "RESULT_VERSION",
    "STATUS_ALREADY_CURRENT_OBSERVED",
    "STATUS_BLOCK",
    "STATUS_HEAD_CONFLICT",
    "STATUS_PUBLISHED_CURRENT_OBSERVED",
    "WitnessOwnershipKeyRevocationSnapshotPublicationResultV1",
    "build_witness_ownership_key_revocation_snapshot_publication_head_v1",
    "build_witness_ownership_key_revocation_snapshot_publication_manifest_v1",
    "build_witness_ownership_key_revocation_snapshot_publication_receipt_v1",
    "build_witness_ownership_key_revocation_snapshot_publication_request_v1",
    "publish_witness_ownership_key_revocation_snapshot_v1",
]
