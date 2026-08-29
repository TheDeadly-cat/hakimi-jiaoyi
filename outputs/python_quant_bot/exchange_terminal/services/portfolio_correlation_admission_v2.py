from __future__ import annotations

import math
from typing import Any

from .execution_authority import authority_violations
from .portfolio_admission import verify_universe_contract
from .portfolio_correlation_admission_v1 import (
    build_portfolio_correlation_admission_v1,
    verify_portfolio_correlation_admission_v1,
)
from .strategy_correlation_cluster_gate import (
    verify_correlation_cluster_preregistration,
)
from .strict_canonical_json_hash import (
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "portfolio-correlation-admission-v2"
VERIFICATION_SCHEMA_VERSION = "portfolio-correlation-admission-verification-v2"
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-common-universe-v2-unbound-lock-1"
)
COMMON_UNIVERSE_POLICY = (
    "EXACT_UNIQUE_TRADABLE_SYMBOL_SET_EQUALS_PREREGISTERED_SYMBOL_SET"
)
LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}

_CHECK_ORDER = (
    (
        "input_identity_exact",
        "INPUT_IDENTITY",
        "strategy_variant_or_lane_identity_invalid",
    ),
    (
        "report_universe_contract_exact",
        "REPORT_UNIVERSE",
        "report_universe_contract_verification_failed",
    ),
    (
        "correlation_preregistration_exact",
        "CORRELATION_PREREGISTRATION",
        "correlation_preregistration_verification_failed",
    ),
    (
        "common_universe_exact",
        "COMMON_UNIVERSE",
        "report_and_correlation_universe_mismatch",
    ),
    (
        "v1_admission_exact",
        "V1_ADMISSION",
        "portfolio_correlation_admission_v1_verification_failed",
    ),
    (
        "v1_admission_pass",
        "V1_ADMISSION",
        "portfolio_correlation_admission_v1_blocked",
    ),
    (
        "evidence_has_no_execution_authority",
        "PERMISSION",
        "correlation_evidence_has_execution_authority",
    ),
)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    """Copy one native JSON tree and reject subclasses, cycles, and non-finite data."""
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("evidence must use native JSON containers and scalars")

    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic evidence is not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("evidence object keys must be native strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _identity_exact(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _display_identity(value: Any) -> str:
    return value if _identity_exact(value) else ""


def _status_pass(call_result: Any) -> bool:
    return type(call_result) is dict and call_result.get("status") == "PASS"


def _authority_clear(value: Any) -> bool:
    try:
        return not bool(authority_violations(value))
    except Exception:
        return False


def _hash_value(value: Any) -> str:
    if (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return ""


def _normalized_unique_symbols(value: Any) -> list[str] | None:
    if type(value) is not list or not value:
        return None
    symbols: list[str] = []
    for symbol in value:
        if type(symbol) is not str or not symbol or symbol != symbol.strip():
            return None
        symbols.append(symbol)
    if len(set(symbols)) != len(symbols):
        return None
    return sorted(symbols)


def _empty_payload(strategy_id: Any, variant_id: Any, lane: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "admission_state": "COMMON_UNIVERSE_BINDING_BLOCKED",
        "first_blocking_tier": "INPUT_SNAPSHOT",
        "strategy_id": _display_identity(strategy_id),
        "variant_id": _display_identity(variant_id),
        "lane": lane if type(lane) is str and lane in LANES else "",
        "common_universe_status": "NOT_EVALUATED",
        "v1_admission_status": "NOT_EVALUATED",
        "v1_first_blocking_tier": None,
        "evidence_hashes": {
            "source_report_hash": "",
            "report_universe_contract_hash": "",
            "report_tradable_symbols_hash": "",
            "correlation_preregistration_hash": "",
            "correlation_symbols_hash": "",
            "common_universe_binding_hash": "",
            "v1_correlation_admission_hash": "",
        },
        "checks": {
            "input_snapshot_exact": False,
            "input_identity_exact": None,
            "report_universe_contract_exact": None,
            "correlation_preregistration_exact": None,
            "common_universe_exact": None,
            "v1_admission_exact": None,
            "v1_admission_pass": None,
            "evidence_has_no_execution_authority": None,
        },
        "blockers": ["evidence_snapshot_failed"],
        "common_universe_policy": COMMON_UNIVERSE_POLICY,
        "legacy_v1_compatibility_unchanged": True,
        "raw_report_embedded": False,
        "raw_correlation_evidence_embedded": False,
        "raw_symbol_lists_embedded": False,
        "consumer_only": True,
        "manual_review_required": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "automatic_internal_backtest_activation_allowed": False,
        "paper_admission_status": "BLOCKED",
        "research_only": True,
        "permissions": dict(_PERMISSIONS),
    }


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "correlation_admission_v2_hash": strict_canonical_hash(payload),
    }


def build_portfolio_correlation_admission_v2(
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    payload = _empty_payload(strategy_id, variant_id, lane)
    try:
        snapshot = _plain_json_snapshot({
            "report": report_document,
            "correlation_preregistration": correlation_preregistration_document,
            "correlation_matrix": correlation_matrix_document,
            "selection_cells": selection_cells_document,
            "complete_link_gate": complete_link_gate_document,
            "strata_preregistration": strata_preregistration_document,
            "strata_gate": strata_gate_document,
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "lane": lane,
        })
    except Exception:
        return _seal(payload)

    report = snapshot["report"]
    preregistration = snapshot["correlation_preregistration"]
    strategy = snapshot["strategy_id"]
    variant = snapshot["variant_id"]
    selected_lane = snapshot["lane"]
    payload["strategy_id"] = _display_identity(strategy)
    payload["variant_id"] = _display_identity(variant)
    payload["lane"] = (
        selected_lane
        if type(selected_lane) is str and selected_lane in LANES
        else ""
    )

    input_identity_exact = (
        _identity_exact(strategy)
        and _identity_exact(variant)
        and type(selected_lane) is str
        and selected_lane in LANES
    )
    report_universe_contract_exact: bool | None = None
    correlation_preregistration_exact: bool | None = None
    common_universe_exact: bool | None = None
    v1_admission_exact: bool | None = None
    v1_admission_pass: bool | None = None
    v1_candidate: dict[str, Any] | None = None
    report_symbols: list[str] | None = None
    correlation_symbols: list[str] | None = None
    universe_contract: dict[str, Any] | None = None

    if input_identity_exact:
        universe_contract = (
            report.get("universe_contract")
            if type(report) is dict
            and type(report.get("universe_contract")) is dict
            else None
        )
        try:
            report_symbols = _normalized_unique_symbols(
                universe_contract.get("tradable_symbols")
                if type(universe_contract) is dict
                else None
            )
            report_universe_contract_exact = (
                type(universe_contract) is dict
                and report_symbols is not None
                and _status_pass(verify_universe_contract(universe_contract))
                and bool(_hash_value(universe_contract.get("contract_hash")))
            )
        except Exception:
            report_universe_contract_exact = False

    if report_universe_contract_exact is True:
        try:
            correlation_symbols = _normalized_unique_symbols(
                preregistration.get("symbols")
                if type(preregistration) is dict
                else None
            )
            correlation_preregistration_exact = (
                type(preregistration) is dict
                and correlation_symbols is not None
                and _status_pass(
                    verify_correlation_cluster_preregistration(preregistration)
                )
                and bool(_hash_value(preregistration.get("preregistration_hash")))
            )
        except Exception:
            correlation_preregistration_exact = False

    if correlation_preregistration_exact is True:
        common_universe_exact = report_symbols == correlation_symbols

    if common_universe_exact is True:
        v1_arguments = {
            "report_document": report,
            "correlation_preregistration_document": preregistration,
            "correlation_matrix_document": snapshot["correlation_matrix"],
            "selection_cells_document": snapshot["selection_cells"],
            "complete_link_gate_document": snapshot["complete_link_gate"],
            "strata_preregistration_document": snapshot["strata_preregistration"],
            "strata_gate_document": snapshot["strata_gate"],
            "strategy_id": strategy,
            "variant_id": variant,
            "lane": selected_lane,
        }
        try:
            v1_candidate = build_portfolio_correlation_admission_v1(**v1_arguments)
            v1_verification = verify_portfolio_correlation_admission_v1(
                v1_candidate,
                **v1_arguments,
            )
            v1_admission_exact = _status_pass(v1_verification)
            if v1_admission_exact:
                v1_admission_pass = v1_candidate.get("status") == "PASS"
        except Exception:
            v1_candidate = None
            v1_admission_exact = False

    evidence_has_no_execution_authority = _authority_clear({
        "report": report,
        "correlation_preregistration": preregistration,
        "correlation_matrix": snapshot["correlation_matrix"],
        "selection_cells": snapshot["selection_cells"],
        "complete_link_gate": snapshot["complete_link_gate"],
        "strata_preregistration": snapshot["strata_preregistration"],
        "strata_gate": snapshot["strata_gate"],
        "v1_candidate": v1_candidate,
    })
    checks = {
        "input_snapshot_exact": True,
        "input_identity_exact": input_identity_exact,
        "report_universe_contract_exact": report_universe_contract_exact,
        "correlation_preregistration_exact": correlation_preregistration_exact,
        "common_universe_exact": common_universe_exact,
        "v1_admission_exact": v1_admission_exact,
        "v1_admission_pass": v1_admission_pass,
        "evidence_has_no_execution_authority": evidence_has_no_execution_authority,
    }
    blockers: list[str] = []
    first_blocking_tier: str | None = None
    for check_id, tier, blocker in _CHECK_ORDER:
        if checks[check_id] is False:
            blockers.append(blocker)
            if first_blocking_tier is None:
                first_blocking_tier = tier

    passed = not blockers and all(value is True for value in checks.values())
    report_symbols_hash = (
        strict_canonical_hash(report_symbols)
        if report_universe_contract_exact is True
        else ""
    )
    correlation_symbols_hash = (
        strict_canonical_hash(correlation_symbols)
        if correlation_preregistration_exact is True
        else ""
    )
    binding_hash = ""
    if common_universe_exact is not None:
        binding_hash = strict_canonical_hash({
            "schema_version": "portfolio-correlation-common-universe-binding-v1",
            "policy": COMMON_UNIVERSE_POLICY,
            "report_tradable_symbols_hash": report_symbols_hash,
            "correlation_symbols_hash": correlation_symbols_hash,
            "exact_symbol_set_match": common_universe_exact,
        })

    try:
        source_report_hash = strict_canonical_hash(report)
    except Exception:
        source_report_hash = ""
    payload.update({
        "status": "PASS" if passed else "BLOCK",
        "admission_state": (
            "COMMON_UNIVERSE_AND_V1_ADMISSION_VERIFIED_RESEARCH_ONLY"
            if passed
            else "COMMON_UNIVERSE_BINDING_BLOCKED"
        ),
        "first_blocking_tier": first_blocking_tier,
        "common_universe_status": (
            "NOT_EVALUATED"
            if common_universe_exact is None
            else ("PASS" if common_universe_exact else "BLOCK")
        ),
        "v1_admission_status": (
            "NOT_EVALUATED"
            if v1_admission_exact is None
            else (
                "INVALID"
                if v1_admission_exact is False
                else v1_candidate.get("status", "BLOCK")
            )
        ),
        "v1_first_blocking_tier": (
            v1_candidate.get("first_blocking_tier")
            if v1_admission_exact is True and type(v1_candidate) is dict
            else None
        ),
        "evidence_hashes": {
            "source_report_hash": source_report_hash,
            "report_universe_contract_hash": (
                _hash_value(universe_contract.get("contract_hash"))
                if report_universe_contract_exact is True
                and type(universe_contract) is dict
                else ""
            ),
            "report_tradable_symbols_hash": report_symbols_hash,
            "correlation_preregistration_hash": (
                _hash_value(preregistration.get("preregistration_hash"))
                if correlation_preregistration_exact is True
                and type(preregistration) is dict
                else ""
            ),
            "correlation_symbols_hash": correlation_symbols_hash,
            "common_universe_binding_hash": binding_hash,
            "v1_correlation_admission_hash": (
                _hash_value(v1_candidate.get("correlation_admission_hash"))
                if v1_admission_exact is True and type(v1_candidate) is dict
                else ""
            ),
        },
        "checks": checks,
        "blockers": blockers,
    })
    return _seal(payload)


def verify_portfolio_correlation_admission_v2(
    document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        candidate = _plain_json_snapshot(document)
    except Exception:
        candidate = None
        blockers.append("correlation_admission_v2_snapshot_failed")

    expected: dict[str, Any] | None = None
    try:
        expected = build_portfolio_correlation_admission_v2(
            report_document,
            correlation_preregistration_document,
            correlation_matrix_document,
            selection_cells_document,
            complete_link_gate_document,
            strata_preregistration_document,
            strata_gate_document,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        blockers.append("correlation_admission_v2_rebuild_failed")

    exact_rebuild = False
    hash_exact = False
    authority_clear = False
    if type(candidate) is dict:
        try:
            exact_rebuild = (
                type(expected) is dict
                and strict_json_contract_equal(candidate, expected)
            )
        except Exception:
            exact_rebuild = False
        try:
            body = {
                key: value
                for key, value in candidate.items()
                if key != "correlation_admission_v2_hash"
            }
            hash_exact = (
                type(candidate.get("correlation_admission_v2_hash")) is str
                and candidate["correlation_admission_v2_hash"]
                == strict_canonical_hash(body)
            )
        except Exception:
            hash_exact = False
        authority_clear = _authority_clear(candidate)

    if not exact_rebuild:
        blockers.append("correlation_admission_v2_not_exact_rebuild")
    if not hash_exact:
        blockers.append("correlation_admission_v2_hash_mismatch")
    if not authority_clear:
        blockers.append("correlation_admission_v2_has_execution_authority")

    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "candidate_status": (
            candidate.get("status", "BLOCK")
            if type(candidate) is dict
            and candidate.get("status") in {"PASS", "BLOCK"}
            else "BLOCK"
        ),
        "blockers": list(dict.fromkeys(blockers)),
        "exact_rebuild": exact_rebuild,
        "hash_exact": hash_exact,
        "research_only": True,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "COMMON_UNIVERSE_POLICY",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_portfolio_correlation_admission_v2",
    "verify_portfolio_correlation_admission_v2",
]
