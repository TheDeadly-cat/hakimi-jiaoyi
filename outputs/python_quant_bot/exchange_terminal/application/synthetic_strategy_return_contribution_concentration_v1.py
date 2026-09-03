from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (
    build_synthetic_strategy_trial_return_matrix_v1,
    plan_synthetic_strategy_trial_return_matrix_v1,
    verify_synthetic_strategy_trial_return_matrix_v1,
)
from hakimi_research.return_contribution_concentration import (
    FIXED_WINDOW_LENGTH,
    build_return_contribution_concentration_diagnostic,
    return_contribution_concentration_policy_v1,
    verify_return_contribution_concentration_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


PLAN_SCHEMA_VERSION = (
    "synthetic-strategy-return-contribution-concentration-plan-v1"
)
BUNDLE_SCHEMA_VERSION = (
    "synthetic-strategy-return-contribution-concentration-bundle-v1"
)
RECORD_SCHEMA_VERSION = (
    "synthetic-strategy-return-contribution-concentration-record-v1"
)
RECEIPT_SCHEMA_VERSION = (
    "synthetic-strategy-return-contribution-concentration-receipt-v1"
)
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_RETURN_CONTRIBUTION_CONCENTRATION_DIAGNOSTIC_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "CALENDAR_MONTH_SYNTHETIC_ONLY",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "OPEN_POSITION_UNREALISED_PNL_NOT_ATTRIBUTED_TO_CLOSED_TRADES",
    "PARTIAL_POSITIVE_CLOSED_TRADE_CONCENTRATION_GAP",
    "PARTIAL_POSITIVE_PERIOD_RETURN_CONCENTRATION_GAP",
    "REAL_DATASET_GAP",
    "RETURN_CONTRIBUTION_CONCENTRATION_SYNTHETIC_DIAGNOSTIC_ONLY",
    "TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY",
]


class SyntheticStrategyReturnContributionConcentrationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyReturnContributionConcentrationError(
        f"{path}: {message}"
    )


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _gaps() -> list[str]:
    return list(_GAPS)


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    if type(record) is not dict:
        _fail(path, "must be an exact dict")
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        _fail(f"{path}.{field}", "must be a SHA-256")
    payload = {key: value for key, value in record.items() if key != field}
    if canonical_trial_return_matrix_sha256(payload) != digest:
        _fail(f"{path}.{field}", "digest mismatch")


def plan_synthetic_strategy_return_contribution_concentration_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_trial_return_matrix_v1()
    strategy_ids = source_plan["registered_strategy_ids"]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_matrix_plan_sha256": source_plan["plan_sha256"],
        "source_required_run_count": source_plan["planned_run_count"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "registered_strategy_ids": list(strategy_ids),
        "expected_observation_count_per_strategy": 169,
        "fixed_window_length": FIXED_WINDOW_LENGTH,
        "expected_fixed_window_candidate_count": 149,
        "policy": return_contribution_concentration_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def _build_record(source_record: dict[str, Any]) -> dict[str, Any]:
    matrix = source_record["trial_return_matrix"]
    diagnostic = build_return_contribution_concentration_diagnostic(matrix)
    receipt = verify_return_contribution_concentration_diagnostic(
        diagnostic, matrix
    )
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": source_record["strategy_id"],
        "family_id": source_record["family_id"],
        "source_matrix_record_sha256": source_record["record_sha256"],
        "source_trial_return_matrix_sha256": matrix["record_sha256"],
        "return_contribution_diagnostic": diagnostic,
        "return_contribution_receipt": receipt,
        "period_concentration_state": diagnostic[
            "positive_period_return_concentration"
        ]["state"],
        "calendar_month_sensitivity_state": "OBSERVED",
        "fixed_window_sensitivity_state": "OBSERVED",
        "closed_trade_sensitivity_state": diagnostic[
            "closed_trade_evidence_state"
        ],
        "positive_closed_trade_concentration_state": diagnostic[
            "positive_closed_trade_pnl_concentration"
        ]["state"],
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(record, "record_sha256")


def build_synthetic_strategy_return_contribution_concentration_v1(
    matrix_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyReturnContributionConcentrationError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    try:
        verify_synthetic_strategy_trial_return_matrix_v1(matrix_bundle)
    except Exception as exc:
        _fail("matrix_bundle", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_return_contribution_concentration_v1()
    source_records = {
        record["strategy_id"]: record
        for record in matrix_bundle["strategy_records"]
    }
    records = [
        _build_record(source_records[strategy_id])
        for strategy_id in plan["registered_strategy_ids"]
    ]
    positive_trade_observed = sum(
        record["positive_closed_trade_concentration_state"] == "OBSERVED"
        for record in records
    )
    closed_trade_observed = sum(
        record["closed_trade_sensitivity_state"] == "OBSERVED"
        for record in records
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_matrix_bundle": deepcopy(matrix_bundle),
        "source_matrix_bundle_sha256": matrix_bundle["bundle_sha256"],
        "source_reused_run_count": matrix_bundle["executed_run_count"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "executed_analysis_count": len(records),
        "observed_period_concentration_count": sum(
            record["period_concentration_state"] == "OBSERVED"
            for record in records
        ),
        "gap_period_concentration_count": sum(
            record["period_concentration_state"] == "GAP"
            for record in records
        ),
        "observed_calendar_month_sensitivity_count": len(records),
        "observed_fixed_window_sensitivity_count": len(records),
        "observed_closed_trade_sensitivity_count": closed_trade_observed,
        "gap_closed_trade_sensitivity_count": len(records)
        - closed_trade_observed,
        "observed_positive_closed_trade_concentration_count": positive_trade_observed,
        "gap_positive_closed_trade_concentration_count": len(records)
        - positive_trade_observed,
        "strategy_records": records,
        "runtime_mutations": False,
        "computed_diagnostics": [
            "BEST_SINGLE_PERIOD_REMOVAL",
            "BEST_UTC_CALENDAR_MONTH_REMOVAL",
            "BEST_CONTIGUOUS_21_PERIOD_WINDOW_REMOVAL",
            "POSITIVE_PERIOD_RETURN_HHI",
            "BEST_CLOSED_SELL_FILL_PNL_REMOVAL",
            "POSITIVE_CLOSED_TRADE_PNL_HHI_WHEN_AVAILABLE",
        ],
        "gaps": _gaps(),
        "authority": _authority(),
    }
    _seal(bundle, "bundle_sha256")
    verify_synthetic_strategy_return_contribution_concentration_v1(bundle)
    return bundle


def _verify_record(
    record: dict[str, Any], source_record: dict[str, Any]
) -> None:
    expected_keys = {
        "schema_version",
        "strategy_id",
        "family_id",
        "source_matrix_record_sha256",
        "source_trial_return_matrix_sha256",
        "return_contribution_diagnostic",
        "return_contribution_receipt",
        "period_concentration_state",
        "calendar_month_sensitivity_state",
        "fixed_window_sensitivity_state",
        "closed_trade_sensitivity_state",
        "positive_closed_trade_concentration_state",
        "evidence_state",
        "status",
        "maturity",
        "gaps",
        "authority",
        "record_sha256",
    }
    if type(record) is not dict or set(record) != expected_keys:
        _fail("strategy_record", "shape mismatch")
    _verify_seal(record, "record_sha256", "strategy_record")
    if record["schema_version"] != RECORD_SCHEMA_VERSION:
        _fail("strategy_record.schema_version", "schema mismatch")
    if record["strategy_id"] != source_record["strategy_id"]:
        _fail("strategy_record.strategy_id", "source mismatch")
    if record["family_id"] != source_record["family_id"]:
        _fail("strategy_record.family_id", "source mismatch")
    if record["source_matrix_record_sha256"] != source_record["record_sha256"]:
        _fail("strategy_record.source_matrix_record_sha256", "source mismatch")
    matrix = source_record["trial_return_matrix"]
    if record["source_trial_return_matrix_sha256"] != matrix["record_sha256"]:
        _fail("strategy_record.source_trial_return_matrix_sha256", "source mismatch")
    try:
        receipt = verify_return_contribution_concentration_diagnostic(
            record["return_contribution_diagnostic"], matrix
        )
    except Exception as exc:
        _fail(
            "strategy_record.return_contribution_diagnostic",
            f"verification failed:{type(exc).__name__}:{exc}",
        )
    if receipt != record["return_contribution_receipt"]:
        _fail("strategy_record.return_contribution_receipt", "receipt mismatch")
    diagnostic = record["return_contribution_diagnostic"]
    expected_states = {
        "period_concentration_state": diagnostic[
            "positive_period_return_concentration"
        ]["state"],
        "calendar_month_sensitivity_state": "OBSERVED",
        "fixed_window_sensitivity_state": "OBSERVED",
        "closed_trade_sensitivity_state": diagnostic[
            "closed_trade_evidence_state"
        ],
        "positive_closed_trade_concentration_state": diagnostic[
            "positive_closed_trade_pnl_concentration"
        ]["state"],
    }
    for field, expected in expected_states.items():
        if record[field] != expected:
            _fail(f"strategy_record.{field}", "diagnostic projection mismatch")
    if (
        record["evidence_state"] != EVIDENCE_STATE
        or record["status"] != STATUS
        or record["maturity"] != MATURITY
        or record["gaps"] != _gaps()
        or record["authority"] != _authority()
    ):
        _fail("strategy_record", "maturity or authority drifted")


def verify_synthetic_strategy_return_contribution_concentration_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    canonical_trial_return_matrix_sha256(bundle)
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_matrix_bundle",
        "source_matrix_bundle_sha256",
        "source_reused_run_count",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "executed_analysis_count",
        "observed_period_concentration_count",
        "gap_period_concentration_count",
        "observed_calendar_month_sensitivity_count",
        "observed_fixed_window_sensitivity_count",
        "observed_closed_trade_sensitivity_count",
        "gap_closed_trade_sensitivity_count",
        "observed_positive_closed_trade_concentration_count",
        "gap_positive_closed_trade_concentration_count",
        "strategy_records",
        "runtime_mutations",
        "computed_diagnostics",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if type(bundle) is not dict or set(bundle) != expected_keys:
        _fail("bundle", "shape mismatch")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", "schema mismatch")
    if bundle["plan"] != plan_synthetic_strategy_return_contribution_concentration_v1():
        _fail("bundle.plan", "must equal deterministic preregistration")
    source = bundle["source_matrix_bundle"]
    try:
        verify_synthetic_strategy_trial_return_matrix_v1(source)
    except Exception as exc:
        _fail(
            "bundle.source_matrix_bundle",
            f"verification failed:{type(exc).__name__}:{exc}",
        )
    if bundle["source_matrix_bundle_sha256"] != source["bundle_sha256"]:
        _fail("bundle.source_matrix_bundle_sha256", "source mismatch")
    if (
        type(bundle["source_reused_run_count"]) is not int
        or bundle["source_reused_run_count"] != 147
        or type(bundle["planned_run_count"]) is not int
        or bundle["planned_run_count"] != 0
        or type(bundle["executed_run_count"]) is not int
        or bundle["executed_run_count"] != 0
        or bundle["additional_backtest_run_count"] != 0
    ):
        _fail("bundle", "run accounting drifted")
    records = bundle["strategy_records"]
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if type(records) is not list or [record.get("strategy_id") for record in records] != strategy_ids:
        _fail("bundle.strategy_records", "membership mismatch")
    source_records = {
        record["strategy_id"]: record for record in source["strategy_records"]
    }
    for record in records:
        _verify_record(record, source_records[record["strategy_id"]])
    count_fields = {
        "observed_period_concentration_count": sum(
            record["period_concentration_state"] == "OBSERVED"
            for record in records
        ),
        "gap_period_concentration_count": sum(
            record["period_concentration_state"] == "GAP"
            for record in records
        ),
        "observed_calendar_month_sensitivity_count": sum(
            record["calendar_month_sensitivity_state"] == "OBSERVED"
            for record in records
        ),
        "observed_fixed_window_sensitivity_count": sum(
            record["fixed_window_sensitivity_state"] == "OBSERVED"
            for record in records
        ),
        "observed_closed_trade_sensitivity_count": sum(
            record["closed_trade_sensitivity_state"] == "OBSERVED"
            for record in records
        ),
        "gap_closed_trade_sensitivity_count": sum(
            record["closed_trade_sensitivity_state"] == "GAP"
            for record in records
        ),
        "observed_positive_closed_trade_concentration_count": sum(
            record["positive_closed_trade_concentration_state"] == "OBSERVED"
            for record in records
        ),
        "gap_positive_closed_trade_concentration_count": sum(
            record["positive_closed_trade_concentration_state"] == "GAP"
            for record in records
        ),
    }
    for field, expected in count_fields.items():
        if type(bundle[field]) is not int or bundle[field] != expected:
            _fail(f"bundle.{field}", "projection count mismatch")
    if bundle["executed_analysis_count"] != len(records) or len(records) != 6:
        _fail("bundle.executed_analysis_count", "analysis count mismatch")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    if bundle["computed_diagnostics"] != [
        "BEST_SINGLE_PERIOD_REMOVAL",
        "BEST_UTC_CALENDAR_MONTH_REMOVAL",
        "BEST_CONTIGUOUS_21_PERIOD_WINDOW_REMOVAL",
        "POSITIVE_PERIOD_RETURN_HHI",
        "BEST_CLOSED_SELL_FILL_PNL_REMOVAL",
        "POSITIVE_CLOSED_TRADE_PNL_HHI_WHEN_AVAILABLE",
    ]:
        _fail("bundle.computed_diagnostics", "diagnostic set mismatch")
    if (
        bundle["evidence_state"] != EVIDENCE_STATE
        or bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["gaps"] != _gaps()
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "maturity or authority drifted")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "strategy_count": len(records),
        "executed_analysis_count": len(records),
        "source_reused_run_count": 147,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        **count_fields,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def replay_synthetic_strategy_return_contribution_concentration_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_return_contribution_concentration_v1(
        bundle
    )
    replayed = build_synthetic_strategy_return_contribution_concentration_v1(
        bundle["source_matrix_bundle"], execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic analysis mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_analysis_count"] = len(bundle["strategy_records"])
    return output


def render_synthetic_strategy_return_contribution_concentration_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_return_contribution_concentration_v1(
        bundle
    )
    rows = [
        "| Strategy | Periods | UTC months | Closed sells | Positive trade HHI state |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for record in bundle["strategy_records"]:
        diagnostic = record["return_contribution_diagnostic"]
        rows.append(
            f"| {record['strategy_id']} | {diagnostic['observation_count']} | "
            f"{diagnostic['calendar_month_count']} | {diagnostic['closed_trade_count']} | "
            f"{record['positive_closed_trade_concentration_state']} |"
        )
    markdown = "\n".join(
        [
            "# Synthetic Strategy Return Contribution Concentration v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Consumes the verified selected-center Frozen return matrix and its bound fill ledger.",
            "- Additional backtest runs: 0",
            "- Six strategy analyses reuse the existing 147-run robustness source.",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['state']}",
            "- Best-period, best-UTC-month, best-21-period-window, and best-closed-trade removal are descriptive synthetic sensitivities.",
            "- Calendar months are synthetic UTC groups; closed trades are realised SELL-fill PnL under the current simplified execution model.",
            "- No decision threshold or formal inference is attached.",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Formal inference authority: false",
            "- Profitability proof: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            *rows,
            "",
            f"Bundle SHA-256: `{receipt['bundle_sha256']}`",
        ]
    )
    for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
        if forbidden in markdown:
            _fail("renderer", f"neutral token violation:{forbidden}")
    return markdown


def build_default_synthetic_strategy_return_contribution_concentration_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyReturnContributionConcentrationError(
            "execution requires exact execute=True; inspect all source plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
    matrix_bundle = build_synthetic_strategy_trial_return_matrix_v1(
        baseline, execute=True
    )
    return build_synthetic_strategy_return_contribution_concentration_v1(
        matrix_bundle, execute=True
    )
