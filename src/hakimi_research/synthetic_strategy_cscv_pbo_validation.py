from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v1,
    build_synthetic_strategy_trial_return_matrix_v2,
    plan_synthetic_strategy_trial_return_matrix_v1,
    plan_synthetic_strategy_trial_return_matrix_v2,
    verify_synthetic_strategy_trial_return_matrix_v1,
    verify_synthetic_strategy_trial_return_matrix_v2,
)
from hakimi_research.cscv_pbo_diagnostic import (
    build_cscv_pbo_diagnostic,
    cscv_pbo_policy_v1,
    verify_cscv_pbo_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-validation-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-validation-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-validation-record-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-cscv-pbo-validation-receipt-v1"
REFERENCE_PLAN_SCHEMA_VERSION = (
    "synthetic-strategy-cscv-pbo-validation-plan-v2"
)
REFERENCE_BUNDLE_SCHEMA_VERSION = (
    "synthetic-strategy-cscv-pbo-validation-bundle-v2"
)
REFERENCE_RECEIPT_SCHEMA_VERSION = (
    "synthetic-strategy-cscv-pbo-validation-receipt-v2"
)
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_CSCV_PBO_DIAGNOSTIC_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_BASE_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "ODD_THREE_TRIAL_MEDIAN_BOUNDARY_SENSITIVITY",
    "REAL_DATASET_GAP",
    "THREE_TRIAL_RANK_RESOLUTION_LIMIT",
    "TRAILING_OBSERVATION_EXCLUDED_FOR_EQUAL_CSCV_PARTITIONS",
]
_PARTIAL_GAP = "PARTIAL_CSCV_RANK_TIE_GAP"


class SyntheticStrategyCscvPboValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyCscvPboValidationError(f"{path}: {message}")


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _gaps(has_rank_ties: bool) -> list[str]:
    gaps = list(_BASE_GAPS)
    if has_rank_ties:
        gaps.append(_PARTIAL_GAP)
    return gaps


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


def plan_synthetic_strategy_cscv_pbo_validation_v1() -> dict[str, Any]:
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
        "coverage_policy": "ALL_STRATEGIES_RETAINED_OBSERVED_OR_EXPLICIT_GAP",
        "policy": cscv_pbo_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(False),
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def plan_synthetic_strategy_cscv_pbo_validation_v2() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_trial_return_matrix_v2()
    plan = plan_synthetic_strategy_cscv_pbo_validation_v1()
    plan.pop("plan_sha256")
    plan["schema_version"] = REFERENCE_PLAN_SCHEMA_VERSION
    plan["source_matrix_schema_version"] = (
        "synthetic-strategy-trial-return-matrix-bundle-v2"
    )
    plan["source_matrix_plan_sha256"] = source_plan["plan_sha256"]
    plan["source_required_run_count"] = source_plan["planned_run_count"]
    plan["registered_strategy_ids"] = list(
        source_plan["registered_strategy_ids"]
    )
    plan["source_reproducibility_context_required"] = True
    plan["expected_source_dependency_bound_run_count"] = 179
    plan["expected_matrix_dependency_bound_run_count"] = 18
    plan["expected_observed_evidence_count"] = 4
    plan["expected_gap_evidence_count"] = 2
    plan["expected_gap_strategy_ids"] = ["dual_ma", "grid"]
    return _seal(plan, "plan_sha256")


def _build_record(source_record: dict[str, Any]) -> dict[str, Any]:
    matrix = source_record["trial_return_matrix"]
    diagnostic = build_cscv_pbo_diagnostic(matrix)
    receipt = verify_cscv_pbo_diagnostic(diagnostic, matrix)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": source_record["strategy_id"],
        "family_id": source_record["family_id"],
        "source_matrix_record_sha256": source_record["record_sha256"],
        "source_trial_return_matrix_sha256": matrix["record_sha256"],
        "cscv_pbo_diagnostic": diagnostic,
        "cscv_pbo_receipt": receipt,
        "evidence_state": receipt["state"],
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": list(diagnostic["gaps"]),
        "authority": _authority(),
    }
    return _seal(record, "record_sha256")


def _build_synthetic_strategy_cscv_pbo_validation(
    matrix_bundle: dict[str, Any],
    *,
    execute: bool,
    plan: dict[str, Any],
    matrix_verifier: Callable[[dict[str, Any]], dict[str, Any]],
    bundle_schema_version: str,
    reference_binding: bool,
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyCscvPboValidationError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    try:
        matrix_verifier(matrix_bundle)
    except Exception as exc:
        _fail("matrix_bundle", f"verification failed:{type(exc).__name__}:{exc}")
    plan = deepcopy(plan)
    source_records = {
        record["strategy_id"]: record for record in matrix_bundle["strategy_records"]
    }
    records = [
        _build_record(source_records[strategy_id])
        for strategy_id in plan["registered_strategy_ids"]
    ]
    observed_count = sum(record["evidence_state"] == "OBSERVED" for record in records)
    gap_count = len(records) - observed_count
    bundle = {
        "schema_version": bundle_schema_version,
        "evidence_state": "OBSERVED" if gap_count == 0 else "GAP",
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
        "observed_evidence_count": observed_count,
        "gap_evidence_count": gap_count,
        "strategy_records": records,
        "runtime_mutations": False,
        "computed_diagnostics": ["CSCV_PBO_DIAGNOSTIC_ATTEMPTED_FOR_ALL_STRATEGIES"],
        "gaps": _gaps(gap_count > 0),
        "authority": _authority(),
    }
    if reference_binding:
        context = matrix_bundle.get("reproducibility_context")
        if type(context) is not dict:
            _fail(
                "matrix_bundle.reproducibility_context",
                "exact context is required",
            )
        bundle.update(
            {
                "reproducibility_context": deepcopy(context),
                "source_run_reproducibility_ledger_sha256": matrix_bundle[
                    "source_run_reproducibility_ledger_sha256"
                ],
                "source_dependency_bound_run_count": matrix_bundle[
                    "source_dependency_bound_run_count"
                ],
                "source_git_bound_run_count": matrix_bundle[
                    "source_git_bound_run_count"
                ],
                "matrix_dependency_bound_run_count": matrix_bundle[
                    "matrix_dependency_bound_run_count"
                ],
            }
        )
    _seal(bundle, "bundle_sha256")
    if reference_binding:
        verify_synthetic_strategy_cscv_pbo_validation_v2(bundle)
    else:
        verify_synthetic_strategy_cscv_pbo_validation_v1(bundle)
    return bundle


def build_synthetic_strategy_cscv_pbo_validation_v1(
    matrix_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_cscv_pbo_validation(
        matrix_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_cscv_pbo_validation_v1(),
        matrix_verifier=verify_synthetic_strategy_trial_return_matrix_v1,
        bundle_schema_version=BUNDLE_SCHEMA_VERSION,
        reference_binding=False,
    )


def build_synthetic_strategy_cscv_pbo_validation_v2(
    matrix_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_cscv_pbo_validation(
        matrix_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_cscv_pbo_validation_v2(),
        matrix_verifier=verify_synthetic_strategy_trial_return_matrix_v2,
        bundle_schema_version=REFERENCE_BUNDLE_SCHEMA_VERSION,
        reference_binding=True,
    )


def _verify_record(record: dict[str, Any], source_record: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "strategy_id",
        "family_id",
        "source_matrix_record_sha256",
        "source_trial_return_matrix_sha256",
        "cscv_pbo_diagnostic",
        "cscv_pbo_receipt",
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
    receipt = verify_cscv_pbo_diagnostic(record["cscv_pbo_diagnostic"], matrix)
    if receipt != record["cscv_pbo_receipt"]:
        _fail("strategy_record.cscv_pbo_receipt", "receipt mismatch")
    if record["evidence_state"] != receipt["state"]:
        _fail("strategy_record.evidence_state", "receipt mismatch")
    if (
        record["status"] != STATUS
        or record["maturity"] != MATURITY
        or record["gaps"] != record["cscv_pbo_diagnostic"]["gaps"]
        or record["authority"] != _authority()
    ):
        _fail("strategy_record", "maturity or authority drifted")


def verify_synthetic_strategy_cscv_pbo_validation_v1(
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
        "observed_evidence_count",
        "gap_evidence_count",
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
    if bundle["plan"] != plan_synthetic_strategy_cscv_pbo_validation_v1():
        _fail("bundle.plan", "must equal deterministic preregistration")
    source = bundle["source_matrix_bundle"]
    try:
        verify_synthetic_strategy_trial_return_matrix_v1(source)
    except Exception as exc:
        _fail("bundle.source_matrix_bundle", f"verification failed:{type(exc).__name__}:{exc}")
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
    observed_count = sum(record["evidence_state"] == "OBSERVED" for record in records)
    gap_count = len(records) - observed_count
    if bundle["observed_evidence_count"] != observed_count:
        _fail("bundle.observed_evidence_count", "coverage mismatch")
    if bundle["gap_evidence_count"] != gap_count:
        _fail("bundle.gap_evidence_count", "coverage mismatch")
    if bundle["executed_analysis_count"] != len(records) or len(records) != 6:
        _fail("bundle.executed_analysis_count", "analysis count mismatch")
    expected_state = "OBSERVED" if gap_count == 0 else "GAP"
    if bundle["evidence_state"] != expected_state:
        _fail("bundle.evidence_state", "coverage mismatch")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    if bundle["computed_diagnostics"] != ["CSCV_PBO_DIAGNOSTIC_ATTEMPTED_FOR_ALL_STRATEGIES"]:
        _fail("bundle.computed_diagnostics", "diagnostic set mismatch")
    if (
        bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["gaps"] != _gaps(gap_count > 0)
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "maturity or authority drifted")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": expected_state,
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "strategy_count": len(records),
        "observed_evidence_count": observed_count,
        "gap_evidence_count": gap_count,
        "executed_analysis_count": len(records),
        "source_reused_run_count": 147,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": _gaps(gap_count > 0),
        "authority": _authority(),
    }


def verify_synthetic_strategy_cscv_pbo_validation_v2(
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
        "observed_evidence_count",
        "gap_evidence_count",
        "strategy_records",
        "runtime_mutations",
        "computed_diagnostics",
        "gaps",
        "authority",
        "reproducibility_context",
        "source_run_reproducibility_ledger_sha256",
        "source_dependency_bound_run_count",
        "source_git_bound_run_count",
        "matrix_dependency_bound_run_count",
        "bundle_sha256",
    }
    if type(bundle) is not dict or set(bundle) != expected_keys:
        _fail("bundle", "v2 shape mismatch")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    if bundle["schema_version"] != REFERENCE_BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", "v2 schema mismatch")
    if bundle["plan"] != plan_synthetic_strategy_cscv_pbo_validation_v2():
        _fail("bundle.plan", "must equal deterministic v2 preregistration")
    source = bundle["source_matrix_bundle"]
    try:
        source_receipt = verify_synthetic_strategy_trial_return_matrix_v2(
            source
        )
    except Exception as exc:
        _fail(
            "bundle.source_matrix_bundle",
            f"v2 verification failed:{type(exc).__name__}:{exc}",
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
        _fail("bundle", "v2 run accounting drifted")
    records = bundle["strategy_records"]
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if (
        type(records) is not list
        or [record.get("strategy_id") for record in records] != strategy_ids
    ):
        _fail("bundle.strategy_records", "v2 membership mismatch")
    source_records = {
        record["strategy_id"]: record
        for record in source["strategy_records"]
    }
    for record in records:
        _verify_record(record, source_records[record["strategy_id"]])
    observed_count = sum(
        record["evidence_state"] == "OBSERVED" for record in records
    )
    gap_count = len(records) - observed_count
    gap_strategy_ids = [
        record["strategy_id"]
        for record in records
        if record["evidence_state"] == "GAP"
    ]
    if (
        bundle["observed_evidence_count"] != observed_count
        or bundle["gap_evidence_count"] != gap_count
        or observed_count
        != bundle["plan"]["expected_observed_evidence_count"]
        or gap_count != bundle["plan"]["expected_gap_evidence_count"]
        or gap_strategy_ids != bundle["plan"]["expected_gap_strategy_ids"]
    ):
        _fail("bundle", "v2 coverage or tie membership drifted")
    if bundle["executed_analysis_count"] != len(records) or len(records) != 6:
        _fail("bundle.executed_analysis_count", "v2 analysis count mismatch")
    if bundle["evidence_state"] != "GAP":
        _fail("bundle.evidence_state", "v2 tie gaps must remain GAP")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    if bundle["computed_diagnostics"] != [
        "CSCV_PBO_DIAGNOSTIC_ATTEMPTED_FOR_ALL_STRATEGIES"
    ]:
        _fail("bundle.computed_diagnostics", "v2 diagnostic set mismatch")
    if (
        type(bundle["reproducibility_context"]) is not dict
        or bundle["reproducibility_context"]
        != source["reproducibility_context"]
        or bundle["source_run_reproducibility_ledger_sha256"]
        != source["source_run_reproducibility_ledger_sha256"]
        or type(bundle["source_dependency_bound_run_count"]) is not int
        or bundle["source_dependency_bound_run_count"]
        != source_receipt["source_dependency_bound_run_count"]
        or bundle["source_dependency_bound_run_count"] != 179
        or type(bundle["source_git_bound_run_count"]) is not int
        or bundle["source_git_bound_run_count"]
        != source_receipt["source_git_bound_run_count"]
        or bundle["source_git_bound_run_count"] != 0
        or type(bundle["matrix_dependency_bound_run_count"]) is not int
        or bundle["matrix_dependency_bound_run_count"]
        != source_receipt["matrix_dependency_bound_run_count"]
        or bundle["matrix_dependency_bound_run_count"] != 18
    ):
        _fail("bundle", "v2 source provenance drifted")
    if (
        bundle["plan"]["policy"]["formal_inference_claimed"] is not False
        or bundle["plan"]["policy"]["decision_threshold"] is not None
        or bundle["plan"]["policy"]["performance_tie_policy"]
        != "GAP_NO_ARBITRARY_RANK_NO_SPLIT_DROP"
    ):
        _fail("bundle.plan.policy", "v2 inference or tie-policy escalation")
    if (
        bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["gaps"] != _gaps(True)
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "v2 maturity or authority drifted")
    return {
        "schema_version": REFERENCE_RECEIPT_SCHEMA_VERSION,
        "state": "GAP",
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "strategy_count": len(records),
        "observed_evidence_count": observed_count,
        "gap_evidence_count": gap_count,
        "gap_strategy_ids": gap_strategy_ids,
        "executed_analysis_count": len(records),
        "source_reused_run_count": 147,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_dependency_bound_run_count": bundle[
            "source_dependency_bound_run_count"
        ],
        "source_git_bound_run_count": bundle[
            "source_git_bound_run_count"
        ],
        "matrix_dependency_bound_run_count": bundle[
            "matrix_dependency_bound_run_count"
        ],
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": _gaps(True),
        "authority": _authority(),
    }


def replay_synthetic_strategy_cscv_pbo_validation_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_cscv_pbo_validation_v1(bundle)
    replayed = build_synthetic_strategy_cscv_pbo_validation_v1(
        bundle["source_matrix_bundle"], execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic analysis mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_analysis_count"] = len(bundle["strategy_records"])
    return output


def replay_synthetic_strategy_cscv_pbo_validation_v2(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_cscv_pbo_validation_v2(bundle)
    replayed = build_synthetic_strategy_cscv_pbo_validation_v2(
        bundle["source_matrix_bundle"],
        execute=True,
    )
    if replayed != bundle:
        _fail("replay", "deterministic v2 analysis mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_analysis_count"] = len(bundle["strategy_records"])
    return output


def _render_synthetic_strategy_cscv_pbo_validation_markdown(
    bundle: dict[str, Any],
    *,
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
    title: str,
) -> str:
    receipt = verifier(bundle)
    rows = [
        "| Strategy | State | CSCV splits | Gap splits | Nonpositive-logit rate |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for record in bundle["strategy_records"]:
        diagnostic = record["cscv_pbo_diagnostic"]
        rate = diagnostic["pbo_nonpositive_logit_rate"]
        rows.append(
            f"| {record['strategy_id']} | {record['evidence_state']} | "
            f"{diagnostic['combination_count']} | {diagnostic['gap_split_count']} | "
            f"{rate if rate is not None else 'GAP'} |"
        )
    markdown = "\n".join(
        [
            title,
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Eight equal chronological partitions and all 70 symmetric combinations.",
            "- One trailing observation is explicitly retained as excluded evidence.",
            "- Additional backtest runs: 0",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['state']}",
            "- Rank ties remain GAP and are never resolved by an arbitrary lexical vote.",
            "- Rates are descriptive synthetic diagnostics without a decision threshold.",
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


def render_synthetic_strategy_cscv_pbo_validation_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_cscv_pbo_validation_markdown(
        bundle,
        verifier=verify_synthetic_strategy_cscv_pbo_validation_v1,
        title="# Synthetic Strategy CSCV/PBO Diagnostic v1",
    )


def render_synthetic_strategy_cscv_pbo_validation_markdown_v2(
    bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_cscv_pbo_validation_markdown(
        bundle,
        verifier=verify_synthetic_strategy_cscv_pbo_validation_v2,
        title="# Synthetic Strategy CSCV/PBO Diagnostic v2",
    )


def build_default_synthetic_strategy_cscv_pbo_validation_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyCscvPboValidationError(
            "execution requires exact execute=True; inspect all source plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
    matrix_bundle = build_synthetic_strategy_trial_return_matrix_v1(
        baseline, execute=True
    )
    return build_synthetic_strategy_cscv_pbo_validation_v1(
        matrix_bundle, execute=True
    )


def build_default_synthetic_strategy_cscv_pbo_validation_v2(
    *,
    execute: bool = False,
    reproducibility_context: dict[str, Any],
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyCscvPboValidationError(
            "execution requires exact execute=True; inspect all v2 source plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=reproducibility_context,
    )
    matrix_bundle = build_synthetic_strategy_trial_return_matrix_v2(
        baseline,
        execute=True,
    )
    return build_synthetic_strategy_cscv_pbo_validation_v2(
        matrix_bundle,
        execute=True,
    )
