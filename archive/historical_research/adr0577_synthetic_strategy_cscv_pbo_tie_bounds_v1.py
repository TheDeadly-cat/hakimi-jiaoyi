from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (
    plan_synthetic_strategy_cscv_pbo_validation_v1,
    verify_synthetic_strategy_cscv_pbo_validation_v1,
)
from hakimi_research.cscv_pbo_tie_bounds import (
    CscvPboTieBoundsError,
    build_cscv_pbo_tie_bounds,
    cscv_pbo_tie_bounds_policy_v1,
    verify_cscv_pbo_tie_bounds,
)
from hakimi_research.trial_return_matrix import (
    TrialReturnMatrixError,
    canonical_trial_return_matrix_sha256,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-tie-bounds-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-tie-bounds-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-tie-bounds-record-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-tie-bounds-receipt-v1"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_CSCV_PBO_TIE_BOUNDS_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_SOURCE_PARTIAL_GAP = "PARTIAL_CSCV_RANK_TIE_GAP"
_BOUNDS_GAPS = [
    "TIE_AWARE_PBO_IDENTIFIED_SET_SYNTHETIC_ONLY",
    "PARTIAL_PBO_IDENTIFIED_SET_REMAINS",
    "FULL_UNIT_PBO_IDENTIFIED_SET_REMAINS",
]


class SyntheticStrategyCscvPboTieBoundsError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyCscvPboTieBoundsError(f"{path}: {message}")


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _require_canonical(value: Any, path: str) -> None:
    try:
        canonical_trial_return_matrix_sha256(value)
    except TrialReturnMatrixError as exc:
        _fail(path, str(exc))


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    if type(record) is not dict:
        _fail(path, "must be an exact dict")
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        _fail(f"{path}.{field}", "must be a SHA-256")
    payload = {key: value for key, value in record.items() if key != field}
    try:
        observed_digest = canonical_trial_return_matrix_sha256(payload)
    except TrialReturnMatrixError as exc:
        _fail(path, str(exc))
    if observed_digest != digest:
        _fail(f"{path}.{field}", "digest mismatch")


def _gaps() -> list[str]:
    source_gaps = plan_synthetic_strategy_cscv_pbo_validation_v1()["gaps"]
    return [
        *[gap for gap in source_gaps if gap != _SOURCE_PARTIAL_GAP],
        *_BOUNDS_GAPS,
    ]


def plan_synthetic_strategy_cscv_pbo_tie_bounds_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_cscv_pbo_validation_v1()
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_cscv_plan_sha256": source_plan["plan_sha256"],
        "source_required_run_count": source_plan["source_required_run_count"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_analysis_count": len(source_plan["registered_strategy_ids"]),
        "executed_analysis_count": 0,
        "registered_strategy_ids": list(source_plan["registered_strategy_ids"]),
        "coverage_policy": "ALL_STRATEGIES_RETAINED_WITH_POINT_OR_INTERVAL_IDENTIFIED_PBO",
        "source_partial_rank_tie_gap_must_be_replaced": True,
        "policy": cscv_pbo_tie_bounds_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def _build_record(source_record: dict[str, Any]) -> dict[str, Any]:
    source_diagnostic = source_record["cscv_pbo_diagnostic"]
    bounds = build_cscv_pbo_tie_bounds(source_diagnostic)
    receipt = verify_cscv_pbo_tie_bounds(bounds, source_diagnostic)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": source_record["strategy_id"],
        "family_id": source_record["family_id"],
        "source_cscv_record_sha256": source_record["record_sha256"],
        "source_cscv_diagnostic_sha256": source_diagnostic[
            "diagnostic_sha256"
        ],
        "tie_bounds_diagnostic": bounds,
        "tie_bounds_receipt": receipt,
        "evidence_state": receipt["state"],
        "bound_quality": receipt["bound_quality"],
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": list(bounds["gaps"]),
        "authority": _authority(),
    }
    return _seal(record, "record_sha256")


def build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
    source_cscv_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyCscvPboTieBoundsError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    try:
        verify_synthetic_strategy_cscv_pbo_validation_v1(source_cscv_bundle)
    except Exception as exc:
        _fail("source_cscv_bundle", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_cscv_pbo_tie_bounds_v1()
    source_records = {
        record["strategy_id"]: record
        for record in source_cscv_bundle["strategy_records"]
    }
    records = [
        _build_record(source_records[strategy_id])
        for strategy_id in plan["registered_strategy_ids"]
    ]
    point_count = sum(record["bound_quality"] == "POINT_IDENTIFIED" for record in records)
    partial_count = sum(
        record["bound_quality"] == "PARTIAL_IDENTIFIED_SET"
        for record in records
    )
    full_count = sum(
        record["bound_quality"] == "FULL_UNIT_INTERVAL" for record in records
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": "OBSERVED_WITH_GAPS",
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_cscv_bundle": deepcopy(source_cscv_bundle),
        "source_cscv_bundle_sha256": source_cscv_bundle["bundle_sha256"],
        "source_matrix_bundle_sha256": source_cscv_bundle[
            "source_matrix_bundle_sha256"
        ],
        "source_reused_run_count": source_cscv_bundle[
            "source_reused_run_count"
        ],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "executed_analysis_count": len(records),
        "point_identified_evidence_count": point_count,
        "partial_interval_evidence_count": partial_count,
        "full_unit_interval_evidence_count": full_count,
        "strategy_records": records,
        "runtime_mutations": False,
        "computed_diagnostics": [
            "TIE_AWARE_PBO_BOUNDS_FOR_ALL_STRATEGIES",
            "NO_ARBITRARY_TIE_BREAK",
            "NO_INTERVAL_MIDPOINT_POINT_SUBSTITUTION",
        ],
        "gaps": _gaps(),
        "authority": _authority(),
    }
    _seal(bundle, "bundle_sha256")
    verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(bundle)
    return bundle


def _verify_record(record: dict[str, Any], source_record: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "strategy_id",
        "family_id",
        "source_cscv_record_sha256",
        "source_cscv_diagnostic_sha256",
        "tie_bounds_diagnostic",
        "tie_bounds_receipt",
        "evidence_state",
        "bound_quality",
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
    if record["source_cscv_record_sha256"] != source_record["record_sha256"]:
        _fail("strategy_record.source_cscv_record_sha256", "source mismatch")
    source_diagnostic = source_record["cscv_pbo_diagnostic"]
    if (
        record["source_cscv_diagnostic_sha256"]
        != source_diagnostic["diagnostic_sha256"]
    ):
        _fail("strategy_record.source_cscv_diagnostic_sha256", "source mismatch")
    try:
        receipt = verify_cscv_pbo_tie_bounds(
            record["tie_bounds_diagnostic"], source_diagnostic
        )
    except CscvPboTieBoundsError as exc:
        _fail("strategy_record.tie_bounds_diagnostic", str(exc))
    if receipt != record["tie_bounds_receipt"]:
        _fail("strategy_record.tie_bounds_receipt", "receipt mismatch")
    if (
        record["evidence_state"] != receipt["state"]
        or record["bound_quality"] != receipt["bound_quality"]
        or record["status"] != STATUS
        or record["maturity"] != MATURITY
        or record["gaps"] != record["tie_bounds_diagnostic"]["gaps"]
        or record["authority"] != _authority()
    ):
        _fail("strategy_record", "evidence or authority drifted")


def verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    _require_canonical(bundle, "bundle")
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_cscv_bundle",
        "source_cscv_bundle_sha256",
        "source_matrix_bundle_sha256",
        "source_reused_run_count",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "executed_analysis_count",
        "point_identified_evidence_count",
        "partial_interval_evidence_count",
        "full_unit_interval_evidence_count",
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
    if bundle["plan"] != plan_synthetic_strategy_cscv_pbo_tie_bounds_v1():
        _fail("bundle.plan", "must equal deterministic preregistration")
    source = bundle["source_cscv_bundle"]
    try:
        verify_synthetic_strategy_cscv_pbo_validation_v1(source)
    except Exception as exc:
        _fail("bundle.source_cscv_bundle", f"verification failed:{type(exc).__name__}:{exc}")
    if bundle["source_cscv_bundle_sha256"] != source["bundle_sha256"]:
        _fail("bundle.source_cscv_bundle_sha256", "source mismatch")
    if (
        bundle["source_matrix_bundle_sha256"]
        != source["source_matrix_bundle_sha256"]
    ):
        _fail("bundle.source_matrix_bundle_sha256", "source mismatch")
    if (
        bundle["source_reused_run_count"] != 147
        or bundle["planned_run_count"] != 0
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
    point_count = sum(record["bound_quality"] == "POINT_IDENTIFIED" for record in records)
    partial_count = sum(
        record["bound_quality"] == "PARTIAL_IDENTIFIED_SET"
        for record in records
    )
    full_count = sum(
        record["bound_quality"] == "FULL_UNIT_INTERVAL" for record in records
    )
    if (
        len(records) != 6
        or bundle["executed_analysis_count"] != 6
        or bundle["point_identified_evidence_count"] != point_count
        or bundle["partial_interval_evidence_count"] != partial_count
        or bundle["full_unit_interval_evidence_count"] != full_count
    ):
        _fail("bundle", "analysis coverage drifted")
    if (
        bundle["evidence_state"] != "OBSERVED_WITH_GAPS"
        or bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["runtime_mutations"] is not False
        or bundle["gaps"] != _gaps()
        or _SOURCE_PARTIAL_GAP in bundle["gaps"]
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "maturity, gap, or authority drifted")
    if bundle["computed_diagnostics"] != [
        "TIE_AWARE_PBO_BOUNDS_FOR_ALL_STRATEGIES",
        "NO_ARBITRARY_TIE_BREAK",
        "NO_INTERVAL_MIDPOINT_POINT_SUBSTITUTION",
    ]:
        _fail("bundle.computed_diagnostics", "diagnostic set mismatch")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": "OBSERVED_WITH_GAPS",
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "strategy_count": len(records),
        "point_identified_evidence_count": point_count,
        "partial_interval_evidence_count": partial_count,
        "full_unit_interval_evidence_count": full_count,
        "executed_analysis_count": len(records),
        "source_reused_run_count": 147,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def replay_synthetic_strategy_cscv_pbo_tie_bounds_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(bundle)
    replayed = build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
        bundle["source_cscv_bundle"], execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic analysis mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_analysis_count"] = len(bundle["strategy_records"])
    return output


def render_synthetic_strategy_cscv_pbo_tie_bounds_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(bundle)
    rows = [
        "| Strategy | Bound quality | PBO lower | PBO upper |",
        "| --- | --- | ---: | ---: |",
    ]
    for record in bundle["strategy_records"]:
        diagnostic = record["tie_bounds_diagnostic"]
        rows.append(
            f"| {record['strategy_id']} | {record['bound_quality']} | "
            f"{diagnostic['pbo_nonpositive_logit_lower_bound']} | "
            f"{diagnostic['pbo_nonpositive_logit_upper_bound']} |"
        )
    markdown = "\n".join(
        [
            "# Synthetic Strategy CSCV/PBO Tie Bounds v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Reuses all 147 source runs and all 70 CSCV splits per strategy.",
            "- Additional backtest runs: 0",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            "- IS maximizer ties and OOS rank ties are retained as identified sets.",
            "- No arbitrary tie-break or interval-midpoint PBO is reported.",
            "- Full-unit bounds remain explicitly uninformative.",
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
