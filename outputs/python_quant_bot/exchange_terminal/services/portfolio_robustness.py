from __future__ import annotations

import hashlib
import json
import math
from typing import Any


PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION = "portfolio-robustness-diagnostic-v3"
PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION = "portfolio-robustness-identity-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _canonical_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or not parsed.is_integer():
        return None
    return int(parsed)


def _diagnostic_rows(value: Any, *, name: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, list):
        return [], [f"{name}_not_list"]
    rows: list[dict[str, Any]] = []
    labels: list[str] = []
    run_hashes: list[str] = []
    issues: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(f"{name}[{index}]_not_object")
            continue
        rows.append(item)
        label = item.get("label")
        run_hash = item.get("run_hash")
        if not _canonical_nonempty_text(label):
            issues.append(f"{name}[{index}]_label_invalid")
        else:
            labels.append(str(label))
        if not _canonical_nonempty_text(run_hash):
            issues.append(f"{name}[{index}]_run_hash_invalid")
        else:
            run_hashes.append(str(run_hash))
    if len(labels) != len(set(labels)):
        issues.append(f"{name}_labels_not_unique")
    if len(run_hashes) != len(set(run_hashes)):
        issues.append(f"{name}_run_hashes_not_unique")
    return rows, issues


def _positive_result(item: dict[str, Any], *, bounded_drawdown: bool = False) -> bool:
    total_return = _finite_number(item.get("total_return_pct"))
    if (
        item.get("ok") is not True
        or item.get("schedule_status") != "PASS"
        or total_return is None
        or total_return <= 0
    ):
        return False
    if not bounded_drawdown:
        return True
    drawdown = _finite_number(item.get("max_drawdown_pct"))
    return drawdown is not None and 0.0 <= drawdown < 15.0


def _derive_robustness_facts(
    *,
    candidate_hash: Any,
    dataset_hash: Any,
    parameter_results: Any,
    ablation_results: Any,
    capital_results: Any,
    candidate_verification: Any,
) -> dict[str, Any]:
    parameter_rows, parameter_issues = _diagnostic_rows(
        parameter_results,
        name="parameter_results",
    )
    ablation_rows, ablation_issues = _diagnostic_rows(
        ablation_results,
        name="ablation_results",
    )
    capital_rows, capital_issues = _diagnostic_rows(
        capital_results,
        name="capital_results",
    )
    contract_issues = [*parameter_issues, *ablation_issues, *capital_issues]
    if len(parameter_rows) != 7:
        contract_issues.append("parameter_results_count_not_7")
    if len(ablation_rows) < 4:
        contract_issues.append("ablation_results_count_below_4")
    capital_labels = {str(item.get("label") or "") for item in capital_rows}
    for required_label in ("CAPITAL_100K", "CAPITAL_1M"):
        if required_label not in capital_labels:
            contract_issues.append(f"capital_results_missing:{required_label}")

    parameter_ok = [
        item for item in parameter_rows
        if _positive_result(item, bounded_drawdown=True)
    ]
    ablation_ok = [item for item in ablation_rows if _positive_result(item)]
    capital_by_label = {str(item.get("label") or ""): item for item in capital_rows}
    negative_ablation_symbols = [
        str(item.get("removed_symbol") or item.get("label") or "")
        for item in ablation_rows
        if not _positive_result(item)
    ]
    baseline_capital = capital_by_label.get("CAPITAL_100K") or {}
    million_capital = capital_by_label.get("CAPITAL_1M") or {}
    checks = {
        "candidate_hash_present": _canonical_nonempty_text(candidate_hash),
        "dataset_hash_present": _canonical_nonempty_text(dataset_hash),
        "candidate_verification_pass": (
            isinstance(candidate_verification, dict)
            and candidate_verification.get("status") == "PASS"
        ),
        "diagnostic_identity_contract_pass": not contract_issues,
        "parameter_neighborhood_positive_at_least_5_of_7": (
            len(parameter_ok) >= 5 and len(parameter_rows) == 7
        ),
        "universe_ablation_positive_at_least_75_pct": (
            len(ablation_rows) >= 4
            and len(ablation_ok) / len(ablation_rows) >= 0.75
        ),
        "baseline_capital_positive": _positive_result(baseline_capital),
        "million_capital_positive_without_partial_fills": (
            _positive_result(million_capital)
            and _nonnegative_integer(million_capital.get("partial_fill_count")) == 0
        ),
        "all_diagnostics_ok": all(
            item.get("ok") is True
            for item in [*parameter_rows, *ablation_rows, *capital_rows]
        ),
        "all_diagnostics_follow_schedule": all(
            item.get("schedule_status") == "PASS"
            for item in [*parameter_rows, *ablation_rows, *capital_rows]
        ),
    }
    return {
        "checks": checks,
        "contract_issues": contract_issues,
        "warnings": [
            f"single_symbol_ablation_non_positive:{symbol}"
            for symbol in negative_ablation_symbols
        ],
        "parameter_summary": {
            "case_count": len(parameter_rows),
            "positive_bounded_count": len(parameter_ok),
        },
        "ablation_summary": {
            "case_count": len(ablation_rows),
            "positive_count": len(ablation_ok),
            "positive_ratio": (
                round(len(ablation_ok) / len(ablation_rows), 6)
                if ablation_rows else 0.0
            ),
        },
        "parameter_rows": parameter_rows,
        "ablation_rows": ablation_rows,
        "capital_rows": capital_rows,
    }


def fixed_parameter_stress_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": "BASELINE", "overrides": {}},
        {"label": "LOOKBACK_105", "overrides": {"lookback": 105}},
        {"label": "LOOKBACK_147", "overrides": {"lookback": 147}},
        {"label": "SKIP_RECENT_3", "overrides": {"skip_recent": 3}},
        {"label": "SKIP_RECENT_10", "overrides": {"skip_recent": 10}},
        {"label": "TARGET_VOL_12", "overrides": {"target_portfolio_volatility_pct": 12.0}},
        {"label": "TARGET_VOL_18", "overrides": {"target_portfolio_volatility_pct": 18.0}},
    ]


def compact_backtest_result(label: str, report: dict[str, Any], **metadata: Any) -> dict[str, Any]:
    return {
        "label": str(label),
        **metadata,
        "ok": report.get("ok") is True,
        "total_return_pct": report.get("total_return_pct"),
        "max_drawdown_pct": report.get("max_drawdown_pct"),
        "sharpe": report.get("sharpe"),
        "annualized_turnover_multiple": report.get("annualized_turnover_multiple"),
        "order_event_count": report.get("order_event_count"),
        "partial_fill_count": report.get("partial_fill_count"),
        "liquidity_block_count": report.get("liquidity_block_count"),
        "gap_block_count": report.get("gap_block_count"),
        "schedule_status": str((report.get("schedule_contract") or {}).get("status") or "BLOCK"),
        "run_hash": str(report.get("run_hash") or ""),
    }


def build_robustness_assessment(
    *,
    candidate_hash: str,
    dataset_hash: str,
    parameter_results: list[dict[str, Any]],
    ablation_results: list[dict[str, Any]],
    capital_results: list[dict[str, Any]],
    created_at: str = "",
    candidate_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    facts = _derive_robustness_facts(
        candidate_hash=candidate_hash,
        dataset_hash=dataset_hash,
        parameter_results=parameter_results,
        ablation_results=ablation_results,
        capital_results=capital_results,
        candidate_verification=candidate_verification,
    )
    checks = facts["checks"]
    payload = {
        "schema_version": PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION,
        "identity_contract_version": PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION,
        "status": "ROBUSTNESS_PASS" if all(checks.values()) else "ROBUSTNESS_BLOCK",
        "candidate_hash": str(candidate_hash or ""),
        "dataset_hash": str(dataset_hash or ""),
        "created_at": str(created_at or ""),
        "candidate_verification": (
            dict(candidate_verification)
            if isinstance(candidate_verification, dict)
            else {}
        ),
        "checks": checks,
        "contract_issues": facts["contract_issues"],
        "warnings": facts["warnings"],
        "parameter_summary": facts["parameter_summary"],
        "ablation_summary": facts["ablation_summary"],
        "parameter_results": facts["parameter_rows"],
        "ablation_results": facts["ablation_rows"],
        "capital_results": facts["capital_rows"],
        "diagnostic_only": True,
        "parameter_selection_allowed": False,
        "manual_review_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["robustness_hash"] = _canonical_hash(payload)
    return payload


def verify_robustness_report(report: dict[str, Any], *, candidate_hash: str) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "schema_version": PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION,
            "identity_contract_version": PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION,
            "status": "BLOCK",
            "blockers": ["robustness_report_object_required"],
            "expected_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    payload = dict(report or {})
    expected_hash = str(payload.pop("robustness_hash", "") or "")
    blockers: list[str] = []
    if str(report.get("schema_version") or "") != PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION:
        blockers.append("robustness_schema_invalid")
    if (
        str(report.get("identity_contract_version") or "")
        != PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION
    ):
        blockers.append("robustness_identity_contract_version_invalid")
    if str(report.get("status") or "") != "ROBUSTNESS_PASS":
        blockers.append("robustness_status_not_passed")
    if str(report.get("candidate_hash") or "") != str(candidate_hash or ""):
        blockers.append("robustness_candidate_hash_mismatch")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("robustness_hash_mismatch")
    if report.get("paper_authorized") is not False or report.get("live_order_allowed") is not False:
        blockers.append("robustness_report_has_execution_authority")
    if (
        report.get("diagnostic_only") is not True
        or report.get("parameter_selection_allowed") is not False
        or report.get("manual_review_required") is not True
    ):
        blockers.append("robustness_diagnostic_authority_invalid")
    facts = _derive_robustness_facts(
        candidate_hash=report.get("candidate_hash"),
        dataset_hash=report.get("dataset_hash"),
        parameter_results=report.get("parameter_results"),
        ablation_results=report.get("ablation_results"),
        capital_results=report.get("capital_results"),
        candidate_verification=report.get("candidate_verification"),
    )
    if report.get("checks") != facts["checks"]:
        blockers.append("robustness_checks_mismatch")
    if report.get("contract_issues") != facts["contract_issues"]:
        blockers.append("robustness_contract_issues_mismatch")
    if report.get("warnings") != facts["warnings"]:
        blockers.append("robustness_warnings_mismatch")
    if report.get("parameter_summary") != facts["parameter_summary"]:
        blockers.append("robustness_parameter_summary_mismatch")
    if report.get("ablation_summary") != facts["ablation_summary"]:
        blockers.append("robustness_ablation_summary_mismatch")
    if not all(facts["checks"].values()):
        blockers.append("robustness_derived_checks_not_passed")
    return {
        "schema_version": PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION,
        "identity_contract_version": PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "expected_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
