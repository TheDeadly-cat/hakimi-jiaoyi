from __future__ import annotations

from itertools import combinations
import math
import re
from datetime import datetime
from typing import Any

from .portfolio_risk import PORTFOLIO_RISK_SCHEMA_VERSION
from .strategy_correlation_cluster_gate import (
    CORRELATION_MATRIX_SCHEMA_VERSION,
    RETURN_SERIES,
    verify_correlation_matrix_contract,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SOURCE_ENVELOPE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-source-envelope-v1"
)
SOURCE_ENVELOPE_VERIFICATION_SCHEMA_VERSION = (
    f"{SOURCE_ENVELOPE_SCHEMA_VERSION}-verification-v1"
)
DUAL_SOURCE_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-dual-source-receipt-v1"
)
DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION = (
    f"{DUAL_SOURCE_RECEIPT_SCHEMA_VERSION}-verification-v1"
)
STATIC_FINGERPRINT = "20260822-dual-source-cutoff-receipt-lock-1"

LEGACY_SOURCE_ROLE = "LEGACY_PROPOSAL_CENTERED_CORRELATION"
CLUSTER_SOURCE_ROLE = "ALL_CLUSTER_COMPLETE_LINK_CORRELATION"
_SOURCE_ROLES = frozenset({LEGACY_SOURCE_ROLE, CLUSTER_SOURCE_ROLE})
_PROVIDER_PATTERN = re.compile(r"^[A-Z][A-Z0-9._:-]{1,63}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _strict_provider_id(value: Any) -> bool:
    return type(value) is str and _PROVIDER_PATTERN.fullmatch(value) is not None


def _strict_cutoff(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def _strict_symbols(value: Any) -> list[str] | None:
    if type(value) is not list or len(value) < 2:
        return None
    if any(type(item) is not str or not item.strip() for item in value):
        return None
    normalized = [item.strip().upper() for item in value]
    if value != normalized or value != sorted(value) or len(set(value)) != len(value):
        return None
    return list(value)


def _strict_document_hash(document: Any, hash_field: str) -> bool:
    if type(document) is not dict:
        return False
    supplied = document.get(hash_field)
    if type(supplied) is not str or _HASH_PATTERN.fullmatch(supplied) is None:
        return False
    body = {key: value for key, value in document.items() if key != hash_field}
    try:
        return strict_canonical_hash(body) == supplied
    except (TypeError, ValueError, OverflowError):
        return False


def _legacy_payload_authority_locked(payload: Any) -> bool:
    return bool(
        type(payload) is dict
        and payload.get("observation_only") is True
        and payload.get("paper_authorized") is False
        and payload.get("live_order_allowed") is False
    )


def _cluster_payload_authority_locked(payload: Any) -> bool:
    permissions = _dict(_dict(payload).get("permissions"))
    return bool(
        permissions.get("paper_authorized") is False
        and permissions.get("live_order_allowed") is False
    )


def _legacy_payload_contract(payload: Any) -> tuple[bool, dict[str, Any]]:
    if type(payload) is not dict:
        return False, {}
    expected_keys = {
        "blockers",
        "live_order_allowed",
        "lookback",
        "matrix_hash",
        "minimum_overlap",
        "observation_only",
        "pairs",
        "paper_authorized",
        "schema_version",
        "status",
        "symbols",
    }
    symbols = _strict_symbols(payload.get("symbols"))
    lookback = payload.get("lookback")
    minimum_overlap = payload.get("minimum_overlap")
    pairs = payload.get("pairs")
    basic = bool(
        set(payload) == expected_keys
        and payload.get("schema_version") == PORTFOLIO_RISK_SCHEMA_VERSION
        and payload.get("status") == "PASS"
        and payload.get("blockers") == []
        and _legacy_payload_authority_locked(payload)
        and symbols is not None
        and type(lookback) is int
        and lookback >= 2
        and type(minimum_overlap) is int
        and 2 <= minimum_overlap <= lookback
        and type(pairs) is dict
        and _strict_document_hash(payload, "matrix_hash")
    )
    if not basic or symbols is None:
        return False, {}

    expected_pairs = {
        "|".join(pair) for pair in combinations(symbols, 2)
    }
    if set(pairs) != expected_pairs:
        return False, {}
    pair_keys = {
        "blockers",
        "correlation",
        "overlap",
        "required_overlap",
        "status",
    }
    for key in sorted(expected_pairs):
        item = pairs.get(key)
        if type(item) is not dict or set(item) != pair_keys:
            return False, {}
        correlation = item.get("correlation")
        if not (
            item.get("status") == "PASS"
            and item.get("blockers") == []
            and type(correlation) is float
            and math.isfinite(correlation)
            and -1.0 <= correlation <= 1.0
            and type(item.get("overlap")) is int
            and item["overlap"] >= minimum_overlap
            and type(item.get("required_overlap")) is int
            and item["required_overlap"] == minimum_overlap
        ):
            return False, {}
    return True, {
        "schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
        "payload_hash": payload["matrix_hash"],
        "symbols": symbols,
        "lookback_observations": lookback,
        "minimum_pair_overlap": minimum_overlap,
    }


def _cluster_payload_contract(payload: Any) -> tuple[bool, dict[str, Any]]:
    if type(payload) is not dict:
        return False, {}
    symbols = _strict_symbols(payload.get("symbols"))
    lookback = payload.get("lookback_observations")
    minimum_overlap = payload.get("minimum_pair_overlap")
    verification: dict[str, Any] = {}
    if symbols is not None:
        try:
            candidate = verify_correlation_matrix_contract(
                payload,
                expected_symbols=symbols,
            )
            if type(candidate) is dict:
                verification = candidate
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            verification = {}
    valid = bool(
        payload.get("schema_version") == CORRELATION_MATRIX_SCHEMA_VERSION
        and payload.get("status") == "PASS"
        and payload.get("return_series") == RETURN_SERIES
        and _cluster_payload_authority_locked(payload)
        and symbols is not None
        and type(lookback) is int
        and lookback >= 2
        and type(minimum_overlap) is int
        and 2 <= minimum_overlap <= lookback
        and _strict_document_hash(payload, "matrix_hash")
        and verification.get("status") == "PASS"
        and not _list(verification.get("blockers"))
    )
    if not valid or symbols is None:
        return False, {}
    return True, {
        "schema_version": CORRELATION_MATRIX_SCHEMA_VERSION,
        "payload_hash": payload["matrix_hash"],
        "symbols": symbols,
        "lookback_observations": lookback,
        "minimum_pair_overlap": minimum_overlap,
    }


def _payload_contract(
    payload: Any,
    source_role: Any,
) -> tuple[bool, dict[str, Any]]:
    if source_role == LEGACY_SOURCE_ROLE:
        return _legacy_payload_contract(payload)
    if source_role == CLUSTER_SOURCE_ROLE:
        return _cluster_payload_contract(payload)
    return False, {}


def _payload_authority_locked(payload: Any, source_role: Any) -> bool:
    if source_role == LEGACY_SOURCE_ROLE:
        return _legacy_payload_authority_locked(payload)
    if source_role == CLUSTER_SOURCE_ROLE:
        return _cluster_payload_authority_locked(payload)
    return False


def _check(name: str, ok: bool, pass_message: str, block_message: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "blocking": True,
        "message": pass_message if ok else block_message,
    }


def _research_authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def build_portfolio_risk_correlation_source_envelope_v1(
    payload: Any,
    *,
    source_role: Any,
    provider_id: Any,
    observation_cutoff_utc: Any,
    return_series: Any = RETURN_SERIES,
) -> dict[str, Any]:
    metadata_ok = bool(
        source_role in _SOURCE_ROLES
        and _strict_provider_id(provider_id)
        and _strict_cutoff(observation_cutoff_utc)
        and return_series == RETURN_SERIES
        and type(return_series) is str
    )
    payload_ok, payload_summary = _payload_contract(payload, source_role)
    authority_ok = _payload_authority_locked(payload, source_role)
    checks = [
        _check(
            "source_metadata_contract",
            metadata_ok,
            "Provider assertion metadata is strict and complete.",
            "Provider assertion metadata is invalid or ambiguous.",
        ),
        _check(
            "source_payload_contract",
            payload_ok,
            "Correlation payload schema and canonical hash are verified.",
            "Correlation payload schema or canonical hash is invalid.",
        ),
        _check(
            "source_payload_authority_lock",
            authority_ok,
            "Correlation payload remains observation-only.",
            "Correlation payload authority lock is missing or invalid.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"
    source = {
        "source_role": source_role if source_role in _SOURCE_ROLES else None,
        "provider_id": provider_id if _strict_provider_id(provider_id) else None,
        "observation_cutoff_utc": (
            observation_cutoff_utc if _strict_cutoff(observation_cutoff_utc) else None
        ),
        "return_series": return_series if return_series == RETURN_SERIES else None,
        "payload_schema_version": (
            payload_summary.get("schema_version") if payload_ok else None
        ),
        "payload_hash": payload_summary.get("payload_hash") if payload_ok else None,
        "symbols": payload_summary.get("symbols") if payload_ok else [],
        "lookback_observations": (
            payload_summary.get("lookback_observations") if payload_ok else None
        ),
        "minimum_pair_overlap": (
            payload_summary.get("minimum_pair_overlap") if payload_ok else None
        ),
    }
    document: dict[str, Any] = {
        "schema_version": SOURCE_ENVELOPE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "SEALED_PROVIDER_ASSERTION"
            if status == "PASS"
            else "BLOCKED_SOURCE_ENVELOPE"
        ),
        "source": source,
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "payload_embedded": False,
            "payload_cutoff_native": False,
            "provider_identity_authenticated": False,
            "provider_assertion_only": True,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _research_authority(),
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def verify_portfolio_risk_correlation_source_envelope_v1(
    document: Any,
    payload: Any,
    *,
    source_role: Any,
    provider_id: Any,
    observation_cutoff_utc: Any,
    return_series: Any = RETURN_SERIES,
) -> dict[str, Any]:
    expected = build_portfolio_risk_correlation_source_envelope_v1(
        payload,
        source_role=source_role,
        provider_id=provider_id,
        observation_cutoff_utc=observation_cutoff_utc,
        return_series=return_series,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": SOURCE_ENVELOPE_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["source_envelope_exact_rebuild_mismatch"],
        "envelope_decision": expected["decision"] if exact else "UNKNOWN",
        "envelope_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
    }


def _envelope_authority_locked(document: Any) -> bool:
    authority = _dict(_dict(document).get("authority"))
    return bool(
        authority.get("descriptive_only") is True
        and all(
            authority.get(key) is False
            for key in (
                "current_admission_allowed",
                "current_pointer_written",
                "formal_registry_activation_allowed",
                "live_order_allowed",
                "migration_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "writer_allowed",
            )
        )
    )


def build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
    legacy_payload: Any,
    legacy_envelope: Any,
    cluster_payload: Any,
    cluster_envelope: Any,
    *,
    expected_symbols: Any,
    expected_observation_cutoff_utc: Any,
    expected_legacy_provider_id: Any,
    expected_cluster_provider_id: Any,
    expected_return_series: Any = RETURN_SERIES,
) -> dict[str, Any]:
    expected_symbol_list = _strict_symbols(expected_symbols)
    expected_metadata_ok = bool(
        expected_symbol_list is not None
        and _strict_cutoff(expected_observation_cutoff_utc)
        and _strict_provider_id(expected_legacy_provider_id)
        and _strict_provider_id(expected_cluster_provider_id)
        and type(expected_return_series) is str
        and expected_return_series == RETURN_SERIES
    )
    legacy_verification = verify_portfolio_risk_correlation_source_envelope_v1(
        legacy_envelope,
        legacy_payload,
        source_role=LEGACY_SOURCE_ROLE,
        provider_id=expected_legacy_provider_id,
        observation_cutoff_utc=expected_observation_cutoff_utc,
        return_series=expected_return_series,
    )
    cluster_verification = verify_portfolio_risk_correlation_source_envelope_v1(
        cluster_envelope,
        cluster_payload,
        source_role=CLUSTER_SOURCE_ROLE,
        provider_id=expected_cluster_provider_id,
        observation_cutoff_utc=expected_observation_cutoff_utc,
        return_series=expected_return_series,
    )
    legacy_exact = bool(
        legacy_verification.get("status") == "PASS"
        and legacy_verification.get("envelope_exactly_verified") is True
        and _dict(legacy_envelope).get("status") == "PASS"
    )
    cluster_exact = bool(
        cluster_verification.get("status") == "PASS"
        and cluster_verification.get("envelope_exactly_verified") is True
        and _dict(cluster_envelope).get("status") == "PASS"
    )
    legacy_source = _dict(_dict(legacy_envelope).get("source")) if legacy_exact else {}
    cluster_source = (
        _dict(_dict(cluster_envelope).get("source")) if cluster_exact else {}
    )
    cutoff_aligned = bool(
        legacy_exact
        and cluster_exact
        and legacy_source.get("observation_cutoff_utc")
        == expected_observation_cutoff_utc
        and cluster_source.get("observation_cutoff_utc")
        == expected_observation_cutoff_utc
    )
    symbols_aligned = bool(
        expected_symbol_list is not None
        and legacy_exact
        and cluster_exact
        and legacy_source.get("symbols") == expected_symbol_list
        and cluster_source.get("symbols") == expected_symbol_list
    )
    lookback_aligned = bool(
        legacy_exact
        and cluster_exact
        and type(legacy_source.get("lookback_observations")) is int
        and legacy_source.get("lookback_observations")
        == cluster_source.get("lookback_observations")
    )
    overlap_aligned = bool(
        legacy_exact
        and cluster_exact
        and type(legacy_source.get("minimum_pair_overlap")) is int
        and legacy_source.get("minimum_pair_overlap")
        == cluster_source.get("minimum_pair_overlap")
    )
    series_aligned = bool(
        legacy_exact
        and cluster_exact
        and legacy_source.get("return_series") == expected_return_series
        and cluster_source.get("return_series") == expected_return_series
    )
    authority_locked = bool(
        legacy_exact
        and cluster_exact
        and _envelope_authority_locked(legacy_envelope)
        and _envelope_authority_locked(cluster_envelope)
    )
    checks = [
        _check(
            "expected_metadata_contract",
            expected_metadata_ok,
            "Expected provider metadata is strict and complete.",
            "Expected provider metadata is invalid or ambiguous.",
        ),
        _check(
            "legacy_source_envelope_exact",
            legacy_exact,
            "Legacy source envelope matches exact trusted inputs.",
            "Legacy source envelope cannot be verified exactly.",
        ),
        _check(
            "cluster_source_envelope_exact",
            cluster_exact,
            "All-cluster source envelope matches exact trusted inputs.",
            "All-cluster source envelope cannot be verified exactly.",
        ),
        _check(
            "shared_observation_cutoff",
            cutoff_aligned,
            "Both provider assertions bind the expected UTC cutoff.",
            "Provider assertion cutoffs differ or are unavailable.",
        ),
        _check(
            "shared_symbol_universe",
            symbols_aligned,
            "Both correlation sources bind the expected symbol universe.",
            "Correlation source symbol universes differ or are unavailable.",
        ),
        _check(
            "shared_lookback_window",
            lookback_aligned,
            "Both correlation sources use the same lookback window.",
            "Correlation source lookback windows differ or are unavailable.",
        ),
        _check(
            "shared_minimum_pair_overlap",
            overlap_aligned,
            "Both correlation sources use the same minimum pair overlap.",
            "Correlation source overlap requirements differ or are unavailable.",
        ),
        _check(
            "shared_return_series",
            series_aligned,
            "Both provider assertions use completed daily returns.",
            "Correlation source return-series assertions differ or are unavailable.",
        ),
        _check(
            "source_envelope_authority_lock",
            authority_locked,
            "Both source envelopes remain research-only.",
            "A source envelope authority lock is missing or invalid.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"
    document: dict[str, Any] = {
        "schema_version": DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "DUAL_SOURCE_PROVIDER_ASSERTIONS_ALIGNED"
            if status == "PASS"
            else "BLOCKED_DUAL_SOURCE_ALIGNMENT"
        ),
        "source": {
            "legacy": {
                "provider_id": legacy_source.get("provider_id") if legacy_exact else None,
                "payload_hash": legacy_source.get("payload_hash") if legacy_exact else None,
                "envelope_hash": (
                    _text_or_none(_dict(legacy_envelope).get("envelope_hash"))
                    if legacy_exact
                    else None
                ),
            },
            "all_cluster": {
                "provider_id": (
                    cluster_source.get("provider_id") if cluster_exact else None
                ),
                "payload_hash": (
                    cluster_source.get("payload_hash") if cluster_exact else None
                ),
                "envelope_hash": (
                    _text_or_none(_dict(cluster_envelope).get("envelope_hash"))
                    if cluster_exact
                    else None
                ),
            },
            "shared": {
                "observation_cutoff_utc": (
                    expected_observation_cutoff_utc if cutoff_aligned else None
                ),
                "return_series": expected_return_series if series_aligned else None,
                "symbols": expected_symbol_list if symbols_aligned else [],
                "lookback_observations": (
                    legacy_source.get("lookback_observations")
                    if lookback_aligned
                    else None
                ),
                "minimum_pair_overlap": (
                    legacy_source.get("minimum_pair_overlap")
                    if overlap_aligned
                    else None
                ),
            },
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "payloads_embedded": False,
            "source_envelopes_embedded": False,
            "payload_cutoff_native": False,
            "provider_identity_authenticated": False,
            "provider_assertion_only": True,
            "shadow_consumer_input_candidate": status == "PASS",
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _research_authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
    document: Any,
    legacy_payload: Any,
    legacy_envelope: Any,
    cluster_payload: Any,
    cluster_envelope: Any,
    *,
    expected_symbols: Any,
    expected_observation_cutoff_utc: Any,
    expected_legacy_provider_id: Any,
    expected_cluster_provider_id: Any,
    expected_return_series: Any = RETURN_SERIES,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
            legacy_payload,
            legacy_envelope,
            cluster_payload,
            cluster_envelope,
            expected_symbols=expected_symbols,
            expected_observation_cutoff_utc=expected_observation_cutoff_utc,
            expected_legacy_provider_id=expected_legacy_provider_id,
            expected_cluster_provider_id=expected_cluster_provider_id,
            expected_return_series=expected_return_series,
        )
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["dual_source_receipt_exact_rebuild_mismatch"],
        "receipt_decision": expected["decision"] if exact else "UNKNOWN",
        "receipt_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
    }


__all__ = [
    "SOURCE_ENVELOPE_SCHEMA_VERSION",
    "SOURCE_ENVELOPE_VERIFICATION_SCHEMA_VERSION",
    "DUAL_SOURCE_RECEIPT_SCHEMA_VERSION",
    "DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "LEGACY_SOURCE_ROLE",
    "CLUSTER_SOURCE_ROLE",
    "build_portfolio_risk_correlation_source_envelope_v1",
    "verify_portfolio_risk_correlation_source_envelope_v1",
    "build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1",
]
