"""Exact local adapter from a verified v9 snapshot to a gross-position claim.

The adapter consumes only the synthetic, detached v9 verification chain.  It
converts signed snapshot notionals to gross basis points without direction
netting and builds the canonical position claim used by the position-derived
post-merge v2 gate.  Provider identity, source truth, freshness, and all
runtime or trading authority remain explicitly unverified.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as position_gate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as v9_contract,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-cluster-dual-budget-v9-signed-snapshot-"
    "position-claim-adapter-v1"
)
STATUS_EXACT_LOCAL_POSITION_CLAIM: Final = (
    "OBSERVED_EXACT_V9_SIGNED_SNAPSHOT_CANONICAL_GROSS_POSITION_CLAIM"
)
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"
GROSS_BPS_ROUNDING: Final = "CEILING"
BASIS_POINTS_DENOMINATOR: Final = 10_000
SOURCE_V9_IMPLEMENTATION_SHA256: Final = (
    "95ff61abd70a17b9cd74f604ecd8a89af3d1cd71db17c6d51d849a40b7203e59"
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,31}$")
_DIRECTIONS = {"LONG", "SHORT"}
_V9_CONTEXT_KEYS = {
    "preregistration",
    "proposal_reconciliation_v8_document",
    "proposal_reconciliation_v8_context",
    "expected_portfolio_snapshot_preregistration_v9_hash",
}
_EXPECTED_SNAPSHOT_KEYS = {
    "equity_minor",
    "snapshot_sequence",
    "observed_at_unix_ms",
    "legacy_portfolio_unit_to_minor",
    "snapshot_position_semantics",
    "position_reconciliation_rule",
}
_SNAPSHOT_CLAIM_KEYS = {
    "provider_preregistration_kwargs",
    "snapshot_id_hash",
    "snapshot_sequence",
    "observed_at_unix_ms",
    "equity",
    "positions",
}


@dataclass(frozen=True, slots=True)
class V9SignedSnapshotPositionClaimAdapterResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    source_v9_schema_version: str
    source_v9_static_fingerprint: str
    source_v9_implementation_sha256: str
    source_v9_reconciliation_hash: str
    source_v9_preregistration_hash: str
    source_legacy_snapshot_claim_hash: str
    source_signed_snapshot_hash: str
    source_dynamic_positions_before_hash: str
    directional_positions_fingerprint_sha256: str
    snapshot_id_hash: str
    snapshot_sequence: int
    observed_at_unix_ms: int
    equity_minor: int
    legacy_portfolio_unit_to_minor: int
    gross_bps_rounding: str
    basis_points_denominator: int
    position_count: int
    total_gross_bps: int
    position_claim: position_gate.IncumbentPositionGrossSnapshotClaimV1
    v9_reconciliation_exactly_verified: bool
    local_signed_snapshot_claim_bound: bool
    direction_netting_applied: bool
    provider_identity_verified: bool
    source_truth_verified: bool
    freshness_verified: bool
    runtime_consumer_bound: bool
    current_admission_allowed: bool
    paper_authorized: bool
    live_order_allowed: bool
    profitability_proven: bool
    raw_provider_registration_embedded: bool
    raw_signatures_embedded: bool
    adapter_hash: str


def _is_hash(value: object) -> bool:
    return type(value) is str and _HEX64_RE.fullmatch(value) is not None


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _canonical_sha256(value: object) -> str | None:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _position_claim_payload(
    claim: position_gate.IncumbentPositionGrossSnapshotClaimV1,
) -> dict[str, object]:
    return {
        "claim_version": claim.claim_version,
        "snapshot_id": claim.snapshot_id,
        "projection_preregistration_hash": (
            claim.projection_preregistration_hash
        ),
        "positions": [
            {"symbol": item.symbol, "gross_bps": item.gross_bps}
            for item in claim.positions
        ],
        "observed_sequence": claim.observed_sequence,
        "position_count": claim.position_count,
        "total_gross_bps": claim.total_gross_bps,
        "positions_fingerprint_sha256": claim.positions_fingerprint_sha256,
        "provider_identity_verified": claim.provider_identity_verified,
        "source_truth_verified": claim.source_truth_verified,
        "freshness_verified": claim.freshness_verified,
        "permission": claim.permission,
        "claim_hash": claim.claim_hash,
    }


def _v9_exactly_verified(
    document: object,
    verification_context: object,
    expected_reconciliation_hash: object,
) -> bool:
    if (
        type(document) is not dict
        or type(verification_context) is not dict
        or set(verification_context) != _V9_CONTEXT_KEYS
        or not _is_hash(expected_reconciliation_hash)
        or document.get("schema_version")
        != v9_contract.RECONCILIATION_SCHEMA_VERSION
        or document.get("static_fingerprint") != v9_contract.STATIC_FINGERPRINT
        or document.get("portfolio_snapshot_reconciliation_v9_hash")
        != expected_reconciliation_hash
        or document.get("status") != "PASS"
        or document.get("combined_budget_status")
        != "LOCAL_RESEARCH_SCOPE_RECONCILED"
        or document.get("combined_admission_status") != "BLOCKED"
    ):
        return False
    try:
        receipt = v9_contract.verify_dual_budget_portfolio_snapshot_reconciliation_v9(
            deepcopy(document),
            **deepcopy(verification_context),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        type(receipt) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("reconciliation_exactly_verified") is True
        and receipt.get("portfolio_scope_status") == "PASS"
        and receipt.get("combined_budget_status")
        == "LOCAL_RESEARCH_SCOPE_RECONCILED"
        and receipt.get("combined_admission_status") == "BLOCKED"
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _extract_bound_snapshot(
    verification_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    try:
        preregistration = verification_context["preregistration"]
        v8_context = verification_context[
            "proposal_reconciliation_v8_context"
        ]
        snapshot_evaluation = v8_context["legacy_budget_v11_context"][
            "kwargs"
        ]["snapshot_evaluation_kwargs"]
        claim_kwargs = snapshot_evaluation["claim_build_kwargs"]
    except (KeyError, TypeError):
        return None
    if (
        type(preregistration) is not dict
        or type(snapshot_evaluation) is not dict
        or type(claim_kwargs) is not dict
    ):
        return None
    return preregistration, snapshot_evaluation, claim_kwargs


def _adapter_core(fields: dict[str, object]) -> dict[str, object]:
    core = dict(fields)
    claim = core["position_claim"]
    if not isinstance(
        claim,
        position_gate.IncumbentPositionGrossSnapshotClaimV1,
    ):
        raise TypeError("position claim type drift")
    core["position_claim"] = _position_claim_payload(claim)
    return core


def build_v9_signed_snapshot_position_claim_adapter_v1(
    v9_document: Any,
    v9_verification_context: Any,
    *,
    expected_v9_reconciliation_hash: Any,
    expected_projection_preregistration_hash: Any,
) -> V9SignedSnapshotPositionClaimAdapterResultV1 | None:
    if (
        not _is_hash(expected_projection_preregistration_hash)
        or not _v9_exactly_verified(
            v9_document,
            v9_verification_context,
            expected_v9_reconciliation_hash,
        )
    ):
        return None
    extracted = _extract_bound_snapshot(v9_verification_context)
    if extracted is None:
        return None
    preregistration, snapshot_evaluation, claim_kwargs = extracted
    try:
        preregistration_source = preregistration["source"]
        expected_snapshot = preregistration["expected_snapshot"]
        preregistration_hash = preregistration[
            "portfolio_snapshot_preregistration_v9_hash"
        ]
        expected_preregistration_hash = v9_verification_context[
            "expected_portfolio_snapshot_preregistration_v9_hash"
        ]
        legacy_claim_hash = preregistration_source[
            "legacy_snapshot_claim_hash"
        ]
        dynamic_positions_hash = preregistration_source[
            "dynamic_positions_before_hash"
        ]
        expected_snapshot_claim_hash = snapshot_evaluation[
            "expected_snapshot_claim_hash"
        ]
        signed_snapshot_hash = snapshot_evaluation[
            "expected_signed_snapshot_hash"
        ]
    except (KeyError, TypeError):
        return None
    if (
        type(preregistration_source) is not dict
        or type(expected_snapshot) is not dict
        or set(expected_snapshot) != _EXPECTED_SNAPSHOT_KEYS
        or set(claim_kwargs) != _SNAPSHOT_CLAIM_KEYS
        or not _is_hash(preregistration_hash)
        or preregistration_hash != expected_preregistration_hash
        or not _is_hash(legacy_claim_hash)
        or legacy_claim_hash != expected_snapshot_claim_hash
        or not _is_hash(signed_snapshot_hash)
        or not _is_hash(dynamic_positions_hash)
    ):
        return None

    snapshot_id_hash = claim_kwargs.get("snapshot_id_hash")
    snapshot_sequence = claim_kwargs.get("snapshot_sequence")
    observed_at_unix_ms = claim_kwargs.get("observed_at_unix_ms")
    legacy_equity = claim_kwargs.get("equity")
    raw_positions = claim_kwargs.get("positions")
    unit_to_minor = expected_snapshot.get("legacy_portfolio_unit_to_minor")
    equity_minor = expected_snapshot.get("equity_minor")
    if (
        not _is_hash(snapshot_id_hash)
        or not _is_plain_int(snapshot_sequence)
        or snapshot_sequence < 1
        or not _is_plain_int(observed_at_unix_ms)
        or observed_at_unix_ms < 0
        or not _is_plain_int(legacy_equity)
        or legacy_equity <= 0
        or not _is_plain_int(unit_to_minor)
        or not 1 <= unit_to_minor <= 10**9
        or not _is_plain_int(equity_minor)
        or equity_minor <= 0
        or legacy_equity * unit_to_minor != equity_minor
        or expected_snapshot.get("snapshot_sequence") != snapshot_sequence
        or expected_snapshot.get("observed_at_unix_ms")
        != observed_at_unix_ms
        or expected_snapshot.get("snapshot_position_semantics")
        != "PRE_PROPOSAL_POSITIONS"
        or expected_snapshot.get("position_reconciliation_rule")
        != "EXACT_SYMBOL_DIRECTION_NOTIONAL_AFTER_INTEGER_UNIT_SCALE"
        or type(raw_positions) is not list
        or len(raw_positions) > position_gate.MAX_POSITIONS
    ):
        return None

    gross_positions: list[position_gate.IncumbentGrossPositionV1] = []
    directional_rows: list[dict[str, object]] = []
    seen_symbols: set[str] = set()
    previous_symbol: str | None = None
    for row in raw_positions:
        if type(row) is not dict or set(row) != {
            "symbol",
            "notional",
            "direction",
        }:
            return None
        symbol = row.get("symbol")
        notional = row.get("notional")
        direction = row.get("direction")
        if (
            type(symbol) is not str
            or _SYMBOL_RE.fullmatch(symbol) is None
            or symbol in seen_symbols
            or (previous_symbol is not None and symbol <= previous_symbol)
            or not _is_plain_int(notional)
            or notional <= 0
            or direction not in _DIRECTIONS
        ):
            return None
        notional_minor = notional * unit_to_minor
        if not 1 <= notional_minor <= 2**63 - 1:
            return None
        gross_bps = (
            notional_minor * BASIS_POINTS_DENOMINATOR + equity_minor - 1
        ) // equity_minor
        gross_positions.append(
            position_gate.IncumbentGrossPositionV1(
                symbol=symbol,
                gross_bps=gross_bps,
            )
        )
        directional_rows.append(
            {
                "symbol": symbol,
                "direction": direction,
                "notional_minor": notional_minor,
            }
        )
        seen_symbols.add(symbol)
        previous_symbol = symbol
    directional_hash = _canonical_sha256(directional_rows)
    if directional_hash is None:
        return None
    position_claim = position_gate.build_incumbent_position_gross_snapshot_claim_v1(
        snapshot_id=snapshot_id_hash,
        projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        positions=tuple(gross_positions),
        observed_sequence=snapshot_sequence,
    )
    if position_claim is None:
        return None

    fields: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": STATUS_EXACT_LOCAL_POSITION_CLAIM,
        "permission_state": PERMISSION_STATE_UNAUTHORIZED,
        "permission": False,
        "research_only": True,
        "source_v9_schema_version": v9_contract.RECONCILIATION_SCHEMA_VERSION,
        "source_v9_static_fingerprint": v9_contract.STATIC_FINGERPRINT,
        "source_v9_implementation_sha256": SOURCE_V9_IMPLEMENTATION_SHA256,
        "source_v9_reconciliation_hash": expected_v9_reconciliation_hash,
        "source_v9_preregistration_hash": preregistration_hash,
        "source_legacy_snapshot_claim_hash": legacy_claim_hash,
        "source_signed_snapshot_hash": signed_snapshot_hash,
        "source_dynamic_positions_before_hash": dynamic_positions_hash,
        "directional_positions_fingerprint_sha256": directional_hash,
        "snapshot_id_hash": snapshot_id_hash,
        "snapshot_sequence": snapshot_sequence,
        "observed_at_unix_ms": observed_at_unix_ms,
        "equity_minor": equity_minor,
        "legacy_portfolio_unit_to_minor": unit_to_minor,
        "gross_bps_rounding": GROSS_BPS_ROUNDING,
        "basis_points_denominator": BASIS_POINTS_DENOMINATOR,
        "position_count": position_claim.position_count,
        "total_gross_bps": position_claim.total_gross_bps,
        "position_claim": position_claim,
        "v9_reconciliation_exactly_verified": True,
        "local_signed_snapshot_claim_bound": True,
        "direction_netting_applied": False,
        "provider_identity_verified": False,
        "source_truth_verified": False,
        "freshness_verified": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
        "raw_provider_registration_embedded": False,
        "raw_signatures_embedded": False,
    }
    adapter_hash = _canonical_sha256(_adapter_core(fields))
    if adapter_hash is None:
        return None
    return V9SignedSnapshotPositionClaimAdapterResultV1(
        **fields,
        adapter_hash=adapter_hash,
    )


def verify_v9_signed_snapshot_position_claim_adapter_v1(
    document: Any,
    v9_document: Any,
    v9_verification_context: Any,
    *,
    expected_v9_reconciliation_hash: Any,
    expected_projection_preregistration_hash: Any,
) -> bool:
    if not isinstance(
        document,
        V9SignedSnapshotPositionClaimAdapterResultV1,
    ):
        return False
    expected = build_v9_signed_snapshot_position_claim_adapter_v1(
        v9_document,
        v9_verification_context,
        expected_v9_reconciliation_hash=expected_v9_reconciliation_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
    )
    return expected is not None and document == expected


__all__ = [
    "BASIS_POINTS_DENOMINATOR",
    "CONTRACT_VERSION",
    "GROSS_BPS_ROUNDING",
    "PERMISSION_STATE_UNAUTHORIZED",
    "SOURCE_V9_IMPLEMENTATION_SHA256",
    "STATUS_EXACT_LOCAL_POSITION_CLAIM",
    "V9SignedSnapshotPositionClaimAdapterResultV1",
    "build_v9_signed_snapshot_position_claim_adapter_v1",
    "verify_v9_signed_snapshot_position_claim_adapter_v1",
]
