"""Neutral, bounded presentation envelope for an exact v9 reconciliation."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as source_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-dual-budget-portfolio-snapshot-"
    "presentation-envelope-v1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-dual-budget-portfolio-snapshot-neutral-presentation-envelope-1"
)
SOURCE_V9_IMPLEMENTATION_SHA256 = (
    "95ff61abd70a17b9cd74f604ecd8a89af3d1cd71db17c6d51d849a40b7203e59"
)
SOURCE_SCHEMA_VERSION = source_contract.RECONCILIATION_SCHEMA_VERSION
SOURCE_STATIC_FINGERPRINT = source_contract.STATIC_FINGERPRINT
SOURCE_HASH_FIELD = "portfolio_snapshot_reconciliation_v9_hash"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_GAPS = (
    "EXTERNAL_PORTFOLIO_PROVIDER_IDENTITY_UNPROVEN",
    "EXTERNAL_PORTFOLIO_SOURCE_TRUTH_UNPROVEN",
    "EXTERNAL_PORTFOLIO_FRESHNESS_UNPROVEN",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_STATUSES = {"PASS", "BLOCK", "UNKNOWN"}
_AUTHORITY = {
    "research_only": True,
    "presentation_only": True,
    "descriptive_only": True,
    "frontend_mount_allowed": False,
    "presentation_consumer_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "current_admission_allowed": False,
    "runtime_gate_activation_allowed": False,
    "paper_allowed": False,
    "live_allowed": False,
    "trading_allowed": False,
    "current_pointer_written": False,
    "legacy_artifact_reissued": False,
}


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _receipt_verified(receipt: Any) -> bool:
    return receipt is True or (
        type(receipt) is dict and receipt.get("verified") is True
    )


def _source_check(
    source_document: Any,
    source_verification_context: Any,
    expected_source_hash: Any,
) -> tuple[bool, str]:
    if not _is_hash(expected_source_hash):
        return False, "EXPECTED_SOURCE_HASH_INVALID"
    if type(source_document) is not dict:
        return False, "SOURCE_V9_DOCUMENT_INVALID"
    if type(source_verification_context) is not dict:
        return False, "SOURCE_V9_VERIFICATION_CONTEXT_INVALID"
    if source_document.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return False, "SOURCE_V9_SCHEMA_MISMATCH"
    if source_document.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT:
        return False, "SOURCE_V9_FINGERPRINT_MISMATCH"
    if source_document.get(SOURCE_HASH_FIELD) != expected_source_hash:
        return False, "SOURCE_V9_HASH_MISMATCH"
    if source_document.get("status") not in _SOURCE_STATUSES:
        return False, "SOURCE_V9_STATUS_INVALID"
    try:
        receipt = source_contract.verify_dual_budget_portfolio_snapshot_reconciliation_v9(
            deepcopy(source_document),
            **deepcopy(source_verification_context),
        )
    except (KeyError, TypeError, ValueError):
        return False, "SOURCE_V9_UNVERIFIED"
    if not _receipt_verified(receipt):
        return False, "SOURCE_V9_UNVERIFIED"
    return True, ""


def _stages(source_known: bool, source_status: str | None) -> list[dict[str, str]]:
    if not source_known:
        source_state = "UNKNOWN"
        source_headline = "Source contract could not be exactly verified"
    elif source_status == "PASS":
        source_state = "LOCAL_CONTRACT_OBSERVED"
        source_headline = "Exact local v9 contract observed"
    else:
        source_state = "LOCAL_CONTRACT_NOT_PASS"
        source_headline = "Exact local v9 non-pass state observed"
    return [
        {
            "axis": "SOURCE",
            "state": source_state,
            "headline": source_headline,
        },
        {
            "axis": "GAP",
            "state": "OPEN",
            "headline": "External portfolio source truth remains unproven",
        },
        {
            "axis": "MATURITY",
            "state": "SYNTHETIC_CONTRACT_ONLY",
            "headline": "Synthetic contract evidence only",
        },
        {
            "axis": "PERMISSION",
            "state": "LOCKED",
            "headline": "No execution or activation permission",
        },
    ]


def _facts(source_known: bool, source_status: str | None) -> dict[str, bool]:
    return {
        "source_exactly_verified": source_known,
        "source_local_contract_pass_observed": (
            source_known and source_status == "PASS"
        ),
        "synthetic_contract_evidence_only": True,
        "external_portfolio_provider_identity_verified": False,
        "external_portfolio_source_truth_verified": False,
        "external_portfolio_freshness_verified": False,
        "formal_market_evidence_verified": False,
        "profitability_proven": False,
    }


def _sealed(
    *,
    source_known: bool,
    source_status: str | None,
    source_hash: str | None,
    reason: str | None,
) -> dict[str, Any]:
    local_not_pass = source_known and source_status != "PASS"
    blockers = list(PRESENTATION_GAPS)
    if reason is not None:
        blockers.insert(0, reason)
    elif local_not_pass:
        blockers.insert(0, "SOURCE_V9_LOCAL_STATUS_NOT_PASS")
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if source_known and source_status == "PASS" else "BLOCK",
        "decision": (
            "EXACT_V9_LOCAL_RESEARCH_STATE_PROJECTED_AUTHORITY_UNCHANGED"
            if source_known
            else "UNKNOWN_SOURCE"
        ),
        "axis_order": list(AXIS_ORDER),
        "source": {
            "state": "OBSERVED" if source_known else "UNKNOWN",
            "schema_version": SOURCE_SCHEMA_VERSION if source_known else None,
            "static_fingerprint": (
                SOURCE_STATIC_FINGERPRINT if source_known else None
            ),
            "implementation_sha256": (
                SOURCE_V9_IMPLEMENTATION_SHA256 if source_known else None
            ),
            "portfolio_snapshot_reconciliation_v9_hash": (
                source_hash if source_known else None
            ),
            "local_contract_status": source_status if source_known else None,
        },
        "gaps": {
            "state": "OPEN",
            "count": len(PRESENTATION_GAPS),
            "items": list(PRESENTATION_GAPS),
        },
        "stages": _stages(source_known, source_status),
        "facts": _facts(source_known, source_status),
        "authority": deepcopy(_AUTHORITY),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def build_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
    source_document: Any,
    source_verification_context: Any,
    *,
    expected_source_hash: Any,
) -> dict[str, Any]:
    """Build an unmounted summary without promoting v9 authority."""

    source_known, reason = _source_check(
        source_document,
        source_verification_context,
        expected_source_hash,
    )
    if not source_known:
        return _sealed(
            source_known=False,
            source_status=None,
            source_hash=None,
            reason=reason,
        )
    return _sealed(
        source_known=True,
        source_status=source_document["status"],
        source_hash=expected_source_hash,
        reason=None,
    )


def verify_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
    document: Any,
    source_document: Any,
    source_verification_context: Any,
    *,
    expected_source_hash: Any,
) -> dict[str, Any]:
    """Verify the envelope by exact deterministic reconstruction."""

    expected = build_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1(
        source_document,
        source_verification_context,
        expected_source_hash=expected_source_hash,
    )
    exact = strict_json_contract_equal(document, expected)
    receipt = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "verified": exact,
        "envelope_status": expected["status"] if exact else "UNKNOWN",
        "envelope_hash": expected["envelope_hash"] if exact else None,
        "blockers": [] if exact else ["PRESENTATION_ENVELOPE_NOT_EXACT"],
        "authority": deepcopy(_AUTHORITY),
    }
    return seal_strict_canonical_document(receipt, "verification_hash")


__all__ = [
    "AXIS_ORDER",
    "PRESENTATION_GAPS",
    "SCHEMA_VERSION",
    "SOURCE_HASH_FIELD",
    "SOURCE_STATIC_FINGERPRINT",
    "SOURCE_V9_IMPLEMENTATION_SHA256",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1",
    "verify_strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1",
]
