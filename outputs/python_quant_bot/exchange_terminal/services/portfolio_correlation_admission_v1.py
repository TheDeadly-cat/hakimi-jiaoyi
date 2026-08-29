from __future__ import annotations

import math
from typing import Any, Callable

from .execution_authority import authority_violations
from .portfolio_admission import (
    build_internal_backtest_admission,
    verify_internal_backtest_admission,
)
from .strategy_correlation_cluster_complete_link import (
    verify_correlation_cluster_gate_v2,
)
from .strategy_correlation_cluster_gate import (
    verify_correlation_cluster_preregistration,
    verify_correlation_matrix_contract,
)
from .strategy_correlation_preregistered_strata import (
    verify_strategy_correlation_strata_gate,
    verify_strategy_correlation_strata_preregistration,
)
from .strict_canonical_json_hash import (
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "portfolio-correlation-admission-v1"
VERIFICATION_SCHEMA_VERSION = "portfolio-correlation-admission-verification-v1"
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
        "report_strict_canonical",
        "BASE_ADMISSION",
        "source_report_not_strict_canonical",
    ),
    (
        "base_admission_exact",
        "BASE_ADMISSION",
        "base_internal_backtest_admission_failed",
    ),
    (
        "correlation_preregistration_exact",
        "CORRELATION_PREREGISTRATION",
        "correlation_preregistration_verification_failed",
    ),
    (
        "correlation_matrix_exact",
        "CORRELATION_MATRIX",
        "correlation_matrix_verification_failed",
    ),
    (
        "selection_cells_strict_canonical",
        "CORRELATION_MATRIX",
        "selection_cells_not_strict_canonical",
    ),
    (
        "complete_link_gate_exact",
        "COMPLETE_LINK",
        "complete_link_gate_verification_failed",
    ),
    (
        "complete_link_gate_pass",
        "COMPLETE_LINK",
        "complete_link_gate_blocked",
    ),
    (
        "strata_preregistration_exact",
        "STRATA_PREREGISTRATION",
        "strata_preregistration_verification_failed",
    ),
    (
        "strata_gate_exact",
        "STRATA_GATE",
        "strata_gate_verification_failed",
    ),
    (
        "strata_gate_pass",
        "STRATA_GATE",
        "strata_gate_blocked",
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


def _status_pass(call: Callable[[], Any]) -> bool:
    try:
        result = call()
    except Exception:
        return False
    return type(result) is dict and result.get("status") == "PASS"


def _authority_clear(value: Any) -> bool:
    try:
        return not bool(authority_violations(value))
    except Exception:
        return False


def _verified_hash(document: Any, key: str, verified: bool) -> str:
    if not verified or type(document) is not dict:
        return ""
    value = document.get(key)
    if (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return ""


def _empty_payload(strategy_id: Any, variant_id: Any, lane: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCK",
        "admission_state": "CORRELATION_EVIDENCE_BLOCKED",
        "first_blocking_tier": "INPUT_SNAPSHOT",
        "strategy_id": _display_identity(strategy_id),
        "variant_id": _display_identity(variant_id),
        "lane": lane if type(lane) is str and lane in LANES else "",
        "base_admission_status": "NOT_EVALUATED",
        "complete_link_status": "NOT_EVALUATED",
        "strata_preregistration_status": "NOT_EVALUATED",
        "strata_gate_status": "NOT_EVALUATED",
        "evidence_hashes": {
            "source_report_hash": "",
            "base_admission_hash": "",
            "correlation_preregistration_hash": "",
            "correlation_matrix_hash": "",
            "selection_cells_hash": "",
            "complete_link_gate_hash": "",
            "strata_preregistration_hash": "",
            "strata_gate_hash": "",
        },
        "checks": {
            "input_snapshot_exact": False,
            **{check_id: False for check_id, _, _ in _CHECK_ORDER},
        },
        "blockers": ["evidence_snapshot_failed"],
        "independent_vote_policy": (
            "AT_MOST_ONE_VOTE_PER_PREREGISTERED_CLUSTER_WITH_STRATA_GATE"
        ),
        "raw_report_embedded": False,
        "raw_correlation_evidence_embedded": False,
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
        "correlation_admission_hash": strict_canonical_hash(payload),
    }


def build_portfolio_correlation_admission_v1(
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
        })
    except Exception:
        return _seal(payload)

    report = snapshot["report"]
    preregistration = snapshot["correlation_preregistration"]
    matrix = snapshot["correlation_matrix"]
    cells = snapshot["selection_cells"]
    complete_link_gate = snapshot["complete_link_gate"]
    strata_preregistration = snapshot["strata_preregistration"]
    strata_gate = snapshot["strata_gate"]

    payload["checks"]["input_snapshot_exact"] = True
    input_identity_exact = (
        _identity_exact(strategy_id)
        and _identity_exact(variant_id)
        and type(lane) is str
        and lane in LANES
    )

    source_report_hash = ""
    report_strict_canonical = False
    try:
        source_report_hash = strict_canonical_hash(report)
        report_strict_canonical = True
    except Exception:
        pass

    selection_cells_hash = ""
    selection_cells_strict_canonical = False
    try:
        selection_cells_hash = strict_canonical_hash(cells)
        selection_cells_strict_canonical = type(cells) is list
    except Exception:
        pass

    base_admission: dict[str, Any] = {}
    base_admission_exact = False
    if type(report) is dict:
        try:
            base_admission = build_internal_backtest_admission(report)
            base_admission_exact = _status_pass(
                lambda: verify_internal_backtest_admission(base_admission)
            )
        except Exception:
            base_admission = {}

    correlation_preregistration_exact: bool | None = None
    correlation_matrix_exact: bool | None = None
    selection_cells_check: bool | None = None
    complete_link_gate_exact: bool | None = None
    complete_link_gate_pass: bool | None = None
    strata_preregistration_exact: bool | None = None
    strata_gate_exact: bool | None = None
    strata_gate_pass: bool | None = None

    if input_identity_exact and report_strict_canonical and base_admission_exact:
        correlation_preregistration_exact = _status_pass(
            lambda: verify_correlation_cluster_preregistration(preregistration)
        )
    if correlation_preregistration_exact is True:
        expected_symbols = (
            preregistration.get("symbols", [])
            if type(preregistration) is dict
            else []
        )
        correlation_matrix_exact = _status_pass(
            lambda: verify_correlation_matrix_contract(
                matrix,
                expected_symbols=expected_symbols,
            )
        )
    if correlation_matrix_exact is True:
        selection_cells_check = selection_cells_strict_canonical
    if correlation_matrix_exact is True and selection_cells_check is True:
        complete_link_gate_exact = _status_pass(
            lambda: verify_correlation_cluster_gate_v2(
                complete_link_gate,
                preregistration=preregistration,
                correlation_matrix=matrix,
                selection_cells=cells,
                strategy_id=strategy_id,
                variant_id=variant_id,
                lane=lane,
            )
        )
    if complete_link_gate_exact is True:
        complete_link_gate_pass = (
            type(complete_link_gate) is dict
            and complete_link_gate.get("status") == "PASS"
        )
    if complete_link_gate_pass is True:
        strata_preregistration_exact = _status_pass(
            lambda: verify_strategy_correlation_strata_preregistration(
                strata_preregistration,
                source_preregistration=preregistration,
            )
        )
    if strata_preregistration_exact is True:
        strata_gate_exact = _status_pass(
            lambda: verify_strategy_correlation_strata_gate(
                strata_gate,
                registration=strata_preregistration,
                complete_link_gate=complete_link_gate,
                source_preregistration=preregistration,
            )
        )
    if strata_gate_exact is True:
        strata_gate_pass = (
            type(strata_gate) is dict
            and strata_gate.get("status") == "PASS"
        )
    evidence_has_no_execution_authority = _authority_clear({
        "source_report": report,
        "base_admission": base_admission,
        "correlation_preregistration": preregistration,
        "correlation_matrix": matrix,
        "selection_cells": cells,
        "complete_link_gate": complete_link_gate,
        "strata_preregistration": strata_preregistration,
        "strata_gate": strata_gate,
    })

    checks = {
        "input_snapshot_exact": True,
        "input_identity_exact": input_identity_exact,
        "report_strict_canonical": report_strict_canonical,
        "base_admission_exact": base_admission_exact,
        "correlation_preregistration_exact": correlation_preregistration_exact,
        "correlation_matrix_exact": correlation_matrix_exact,
        "selection_cells_strict_canonical": selection_cells_check,
        "complete_link_gate_exact": complete_link_gate_exact,
        "complete_link_gate_pass": complete_link_gate_pass,
        "strata_preregistration_exact": strata_preregistration_exact,
        "strata_gate_exact": strata_gate_exact,
        "strata_gate_pass": strata_gate_pass,
        "evidence_has_no_execution_authority": evidence_has_no_execution_authority,
    }
    blockers: list[str] = []
    first_blocking_tier: str | None = None
    for check_id, tier, blocker in _CHECK_ORDER:
        if checks[check_id] is False:
            blockers.append(blocker)
            if first_blocking_tier is None:
                first_blocking_tier = tier

    passed = not blockers
    payload.update({
        "status": "PASS" if passed else "BLOCK",
        "admission_state": (
            "CORRELATION_AND_PREREGISTERED_STRATA_VERIFIED_RESEARCH_ONLY"
            if passed
            else "CORRELATION_EVIDENCE_BLOCKED"
        ),
        "first_blocking_tier": first_blocking_tier,
        "base_admission_status": (
            base_admission.get("status", "")
            if type(base_admission) is dict
            else ""
        ),
        "complete_link_status": (
            "NOT_EVALUATED"
            if complete_link_gate_exact is None
            else (
                complete_link_gate.get("status", "INVALID")
                if complete_link_gate_exact is True
                and type(complete_link_gate) is dict
                else "INVALID"
            )
        ),
        "strata_preregistration_status": (
            "NOT_EVALUATED"
            if strata_preregistration_exact is None
            else ("PASS" if strata_preregistration_exact else "INVALID")
        ),
        "strata_gate_status": (
            "NOT_EVALUATED"
            if strata_gate_exact is None
            else (
                strata_gate.get("status", "INVALID")
                if strata_gate_exact is True and type(strata_gate) is dict
                else "INVALID"
            )
        ),
        "evidence_hashes": {
            "source_report_hash": source_report_hash if report_strict_canonical else "",
            "base_admission_hash": _verified_hash(
                base_admission,
                "admission_hash",
                base_admission_exact,
            ),
            "correlation_preregistration_hash": _verified_hash(
                preregistration,
                "preregistration_hash",
                correlation_preregistration_exact,
            ),
            "correlation_matrix_hash": _verified_hash(
                matrix,
                "matrix_hash",
                correlation_matrix_exact,
            ),
            "selection_cells_hash": (
                selection_cells_hash if selection_cells_check is True else ""
            ),
            "complete_link_gate_hash": _verified_hash(
                complete_link_gate,
                "gate_hash",
                complete_link_gate_exact,
            ),
            "strata_preregistration_hash": _verified_hash(
                strata_preregistration,
                "registration_hash",
                strata_preregistration_exact,
            ),
            "strata_gate_hash": _verified_hash(
                strata_gate,
                "gate_hash",
                strata_gate_exact,
            ),
        },
        "checks": checks,
        "blockers": blockers,
    })
    return _seal(payload)


def verify_portfolio_correlation_admission_v1(
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
        blockers.append("correlation_admission_snapshot_failed")

    expected: dict[str, Any] | None = None
    try:
        expected = build_portfolio_correlation_admission_v1(
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
        blockers.append("correlation_admission_rebuild_failed")

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
                if key != "correlation_admission_hash"
            }
            hash_exact = (
                type(candidate.get("correlation_admission_hash")) is str
                and candidate["correlation_admission_hash"]
                == strict_canonical_hash(body)
            )
        except Exception:
            hash_exact = False
        authority_clear = _authority_clear(candidate)

    if not exact_rebuild:
        blockers.append("correlation_admission_not_exact_rebuild")
    if not hash_exact:
        blockers.append("correlation_admission_hash_mismatch")
    if not authority_clear:
        blockers.append("correlation_admission_has_execution_authority")

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
    "SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "build_portfolio_correlation_admission_v1",
    "verify_portfolio_correlation_admission_v1",
]
