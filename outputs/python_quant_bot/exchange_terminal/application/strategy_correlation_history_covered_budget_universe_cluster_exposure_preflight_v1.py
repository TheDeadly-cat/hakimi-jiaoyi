"""Pure research-only cluster exposure preflight.

This module is additive and deliberately has no runtime, HTTP, engine, storage,
or trading integration.  A future adapter may build the immutable source
receipt from the covered-universe batch-cluster preflight, but this version is
not an authority switch.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Final


CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "cluster-exposure-preflight-v1"
)
SOURCE_RECEIPT_VERSION: Final = "correlation-cluster-exposure-source-receipt-v1"
EXPECTED_PRODUCER_CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "batch-cluster-preflight-v1"
)
POLICY_VERSION: Final = "correlation-cluster-exposure-policy-v1"

POLICY_RESULT_UNKNOWN: Final = "UNKNOWN"
POLICY_RESULT_LIMIT_BREACH: Final = "LIMIT_BREACH"
POLICY_RESULT_WITHIN_LIMIT: Final = "WITHIN_PREREGISTERED_LIMIT"
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

MAX_SOURCE_SYMBOLS: Final = 256
MAX_PROPOSAL_ROWS: Final = 256
MAX_GROSS_BPS: Final = 10_000

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,31}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")


@dataclass(frozen=True, slots=True)
class ClusterExposureSourceReceiptV1:
    """Normalized read-only output expected from a future upstream adapter."""

    receipt_version: str
    producer_contract_version: str
    source_batch_fingerprint_sha256: str
    structurally_complete: bool
    permission: bool
    symbol_cluster_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ClusterExposurePolicyV1:
    """Preregistered integer-basis-point exposure limits."""

    policy_version: str
    policy_id: str
    max_proposals: int
    max_portfolio_gross_bps: int
    max_cluster_gross_bps: int
    max_single_proposal_gross_bps: int


@dataclass(frozen=True, slots=True)
class ClusterExposureProposalV1:
    """A proposal references a symbol, never a caller-supplied cluster id."""

    proposal_id: str
    symbol: str
    requested_gross_bps: int


@dataclass(frozen=True, slots=True)
class ClusterExposurePreflightResultV1:
    """Neutral policy evidence; never a paper or live permission."""

    contract_version: str
    policy_result: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    source_batch_fingerprint_sha256: str | None
    policy_fingerprint_sha256: str | None
    proposal_count: int | None
    independent_cluster_count: int | None
    total_gross_bps: int | None
    cluster_gross_bps: tuple[tuple[str, int], ...]


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _policy_fingerprint(policy: ClusterExposurePolicyV1) -> str:
    return _canonical_sha256(
        {
            "max_cluster_gross_bps": policy.max_cluster_gross_bps,
            "max_portfolio_gross_bps": policy.max_portfolio_gross_bps,
            "max_proposals": policy.max_proposals,
            "max_single_proposal_gross_bps": (
                policy.max_single_proposal_gross_bps
            ),
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
        }
    )


def _validate_source(source: object) -> tuple[str, ...]:
    if not isinstance(source, ClusterExposureSourceReceiptV1):
        return ("SOURCE_RECEIPT_INVALID",)

    codes: list[str] = []
    if source.receipt_version != SOURCE_RECEIPT_VERSION:
        codes.append("SOURCE_RECEIPT_VERSION_MISMATCH")
    if source.producer_contract_version != EXPECTED_PRODUCER_CONTRACT_VERSION:
        codes.append("SOURCE_PRODUCER_VERSION_MISMATCH")
    if not isinstance(source.source_batch_fingerprint_sha256, str) or not _SHA256_RE.fullmatch(
        source.source_batch_fingerprint_sha256
    ):
        codes.append("SOURCE_BATCH_FINGERPRINT_INVALID")
    if type(source.structurally_complete) is not bool or not source.structurally_complete:
        codes.append("SOURCE_NOT_STRUCTURALLY_COMPLETE")
    if type(source.permission) is not bool or source.permission is not False:
        codes.append("SOURCE_PERMISSION_MUST_REMAIN_FALSE")

    pairs = source.symbol_cluster_pairs
    if type(pairs) is not tuple or not 1 <= len(pairs) <= MAX_SOURCE_SYMBOLS:
        codes.append("SOURCE_CLUSTER_MAP_INVALID")
        return _ordered_unique(codes)

    valid_pairs: list[tuple[str, str]] = []
    seen_symbols: set[str] = set()
    for item in pairs:
        if type(item) is not tuple or len(item) != 2:
            codes.append("SOURCE_CLUSTER_MAP_INVALID")
            continue
        symbol, cluster_id = item
        if not isinstance(symbol, str) or not _SYMBOL_RE.fullmatch(symbol):
            codes.append("SOURCE_SYMBOL_INVALID")
            continue
        if not isinstance(cluster_id, str) or not _OPAQUE_ID_RE.fullmatch(cluster_id):
            codes.append("SOURCE_CLUSTER_ID_INVALID")
            continue
        if symbol in seen_symbols:
            codes.append("SOURCE_CLUSTER_MAP_DUPLICATE_SYMBOL")
        seen_symbols.add(symbol)
        valid_pairs.append((symbol, cluster_id))

    if len(valid_pairs) == len(pairs) and tuple(sorted(valid_pairs)) != pairs:
        codes.append("SOURCE_CLUSTER_MAP_NOT_CANONICAL")
    return _ordered_unique(codes)


def _validate_policy(policy: object) -> tuple[str, ...]:
    if not isinstance(policy, ClusterExposurePolicyV1):
        return ("POLICY_INVALID",)

    codes: list[str] = []
    if policy.policy_version != POLICY_VERSION:
        codes.append("POLICY_VERSION_MISMATCH")
    if not isinstance(policy.policy_id, str) or not _OPAQUE_ID_RE.fullmatch(
        policy.policy_id
    ):
        codes.append("POLICY_ID_INVALID")
    if not _is_plain_int(policy.max_proposals) or not 1 <= policy.max_proposals <= MAX_PROPOSAL_ROWS:
        codes.append("POLICY_MAX_PROPOSALS_INVALID")

    limit_fields = (
        ("POLICY_PORTFOLIO_GROSS_LIMIT_INVALID", policy.max_portfolio_gross_bps),
        ("POLICY_CLUSTER_GROSS_LIMIT_INVALID", policy.max_cluster_gross_bps),
        (
            "POLICY_SINGLE_PROPOSAL_GROSS_LIMIT_INVALID",
            policy.max_single_proposal_gross_bps,
        ),
    )
    for code, value in limit_fields:
        if not _is_plain_int(value) or not 1 <= value <= MAX_GROSS_BPS:
            codes.append(code)

    if not codes and not (
        policy.max_single_proposal_gross_bps
        <= policy.max_cluster_gross_bps
        <= policy.max_portfolio_gross_bps
    ):
        codes.append("POLICY_LIMIT_ORDER_INVALID")
    return _ordered_unique(codes)


def _validate_proposals(
    proposals: object,
    symbol_to_cluster: dict[str, str],
) -> tuple[str, ...]:
    if type(proposals) is not tuple:
        return ("PROPOSAL_SET_NOT_CANONICAL",)
    if not proposals:
        return ("PROPOSAL_SET_EMPTY",)
    if len(proposals) > MAX_PROPOSAL_ROWS:
        return ("PROPOSAL_SET_TOO_LARGE",)

    codes: list[str] = []
    seen_proposal_ids: set[str] = set()
    for proposal in proposals:
        if not isinstance(proposal, ClusterExposureProposalV1):
            codes.append("PROPOSAL_ROW_INVALID")
            continue
        if not isinstance(proposal.proposal_id, str) or not _OPAQUE_ID_RE.fullmatch(
            proposal.proposal_id
        ):
            codes.append("PROPOSAL_ID_INVALID")
        elif proposal.proposal_id in seen_proposal_ids:
            codes.append("DUPLICATE_PROPOSAL_ID")
        else:
            seen_proposal_ids.add(proposal.proposal_id)

        if not isinstance(proposal.symbol, str) or not _SYMBOL_RE.fullmatch(
            proposal.symbol
        ):
            codes.append("PROPOSAL_SYMBOL_INVALID")
        elif proposal.symbol not in symbol_to_cluster:
            codes.append("PROPOSAL_SYMBOL_NOT_IN_SOURCE_MAP")

        if (
            not _is_plain_int(proposal.requested_gross_bps)
            or not 1 <= proposal.requested_gross_bps <= MAX_GROSS_BPS
        ):
            codes.append("PROPOSAL_GROSS_BPS_INVALID")
    return _ordered_unique(codes)


def _unknown_result(
    blocker_codes: tuple[str, ...],
    *,
    source_fingerprint: str | None = None,
    policy_fingerprint: str | None = None,
) -> ClusterExposurePreflightResultV1:
    return ClusterExposurePreflightResultV1(
        contract_version=CONTRACT_VERSION,
        policy_result=POLICY_RESULT_UNKNOWN,
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=blocker_codes or ("UNSPECIFIED_INPUT_FAILURE",),
        source_batch_fingerprint_sha256=source_fingerprint,
        policy_fingerprint_sha256=policy_fingerprint,
        proposal_count=None,
        independent_cluster_count=None,
        total_gross_bps=None,
        cluster_gross_bps=(),
    )


def evaluate_cluster_exposure_preflight_v1(
    *,
    source: ClusterExposureSourceReceiptV1,
    policy: ClusterExposurePolicyV1,
    proposals: tuple[ClusterExposureProposalV1, ...],
) -> ClusterExposurePreflightResultV1:
    """Aggregate gross exposure by source-owned cluster and apply policy.

    Invalid or incomplete provenance produces ``UNKNOWN`` with no metrics.
    A within-limit result remains research-only and never grants permission.
    """

    source_codes = _validate_source(source)
    policy_codes = _validate_policy(policy)
    source_fingerprint = (
        source.source_batch_fingerprint_sha256
        if not source_codes and isinstance(source, ClusterExposureSourceReceiptV1)
        else None
    )
    policy_fingerprint = (
        _policy_fingerprint(policy)
        if not policy_codes and isinstance(policy, ClusterExposurePolicyV1)
        else None
    )
    if source_codes or policy_codes:
        return _unknown_result(
            _ordered_unique([*source_codes, *policy_codes]),
            source_fingerprint=source_fingerprint,
            policy_fingerprint=policy_fingerprint,
        )

    symbol_to_cluster = dict(source.symbol_cluster_pairs)
    proposal_codes = _validate_proposals(proposals, symbol_to_cluster)
    if proposal_codes:
        return _unknown_result(
            proposal_codes,
            source_fingerprint=source_fingerprint,
            policy_fingerprint=policy_fingerprint,
        )

    cluster_totals: dict[str, int] = {}
    total_gross_bps = 0
    single_proposal_limit_breached = False
    for proposal in proposals:
        cluster_id = symbol_to_cluster[proposal.symbol]
        cluster_totals[cluster_id] = (
            cluster_totals.get(cluster_id, 0) + proposal.requested_gross_bps
        )
        total_gross_bps += proposal.requested_gross_bps
        if proposal.requested_gross_bps > policy.max_single_proposal_gross_bps:
            single_proposal_limit_breached = True

    blocker_codes: list[str] = []
    if len(proposals) > policy.max_proposals:
        blocker_codes.append("PROPOSAL_COUNT_LIMIT_EXCEEDED")
    if single_proposal_limit_breached:
        blocker_codes.append("SINGLE_PROPOSAL_GROSS_LIMIT_EXCEEDED")
    if any(
        gross_bps > policy.max_cluster_gross_bps
        for gross_bps in cluster_totals.values()
    ):
        blocker_codes.append("CLUSTER_GROSS_LIMIT_EXCEEDED")
    if total_gross_bps > policy.max_portfolio_gross_bps:
        blocker_codes.append("PORTFOLIO_GROSS_LIMIT_EXCEEDED")

    return ClusterExposurePreflightResultV1(
        contract_version=CONTRACT_VERSION,
        policy_result=(
            POLICY_RESULT_LIMIT_BREACH
            if blocker_codes
            else POLICY_RESULT_WITHIN_LIMIT
        ),
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=tuple(blocker_codes),
        source_batch_fingerprint_sha256=source_fingerprint,
        policy_fingerprint_sha256=policy_fingerprint,
        proposal_count=len(proposals),
        independent_cluster_count=len(cluster_totals),
        total_gross_bps=total_gross_bps,
        cluster_gross_bps=tuple(sorted(cluster_totals.items())),
    )


__all__ = [
    "CONTRACT_VERSION",
    "EXPECTED_PRODUCER_CONTRACT_VERSION",
    "PERMISSION_STATE_UNAUTHORIZED",
    "POLICY_RESULT_LIMIT_BREACH",
    "POLICY_RESULT_UNKNOWN",
    "POLICY_RESULT_WITHIN_LIMIT",
    "POLICY_VERSION",
    "SOURCE_RECEIPT_VERSION",
    "ClusterExposurePolicyV1",
    "ClusterExposurePreflightResultV1",
    "ClusterExposureProposalV1",
    "ClusterExposureSourceReceiptV1",
    "evaluate_cluster_exposure_preflight_v1",
]
