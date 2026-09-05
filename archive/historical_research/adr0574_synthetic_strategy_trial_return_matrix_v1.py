from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    PERIODS_PER_YEAR,
    build_synthetic_strategy_report_bundle_v1,
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 import (
    build_synthetic_strategy_robustness_evidence_with_run_capture_v1,
    plan_synthetic_strategy_robustness_evidence_v1,
    verify_synthetic_strategy_robustness_evidence_v1,
)
from hakimi_research.trial_return_matrix import (
    RETURN_CONVENTION,
    build_strategy_trial_return_matrix,
    canonical_trial_return_matrix_sha256,
    verify_strategy_trial_return_matrix,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-record-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-bundle-receipt-v1"
EVALUATION_ROLE = "SYNTHETIC_ROBUSTNESS_FROZEN_STABILITY"
EVIDENCE_STATE = "OBSERVED"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_TRIAL_RETURN_MATRIX_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "DEFLATED_SHARPE_RATIO_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
]


class SyntheticStrategyTrialReturnMatrixError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyTrialReturnMatrixError(f"{path}: {message}")


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


def plan_synthetic_strategy_trial_return_matrix_v1() -> dict[str, Any]:
    baseline_plan = plan_synthetic_strategy_report_bundle_v1()
    robustness_plan = plan_synthetic_strategy_robustness_evidence_v1()
    strategy_ids = robustness_plan["registered_strategy_ids"]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_required_baseline_run_count": baseline_plan["planned_run_count"],
        "reused_robustness_run_count": robustness_plan["planned_run_count"],
        "planned_run_count": robustness_plan["planned_run_count"],
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "registered_strategy_ids": list(strategy_ids),
        "matrix_policy": {
            "source_phase": "FROZEN_STABILITY",
            "evaluation_role": EVALUATION_ROLE,
            "candidate_scope": "ALL_PREREGISTERED_PARAMETER_TRIALS",
            "selected_trial_policy": "PREREGISTERED_CENTER_DEFAULT_NO_POST_HOC_SELECTION",
            "return_convention": RETURN_CONVENTION,
            "periods_per_year": PERIODS_PER_YEAR,
            "failed_trial_policy": "FAIL_CLOSED_NO_SILENT_DROP",
            "formal_inference_claimed": False,
            "frozen_results_used_for_selection": False,
        },
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def _source_evidence_by_strategy(
    robustness_bundle: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        item["strategy_id"]: item for item in robustness_bundle["strategy_evidence"]
    }


def _build_record(
    source_evidence: dict[str, Any],
    robustness_bundle: dict[str, Any],
    run_capture: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    strategy_id = source_evidence["strategy_id"]
    multiple_testing = source_evidence["validation_evidence"]["multiple_testing"]
    trial_ids = multiple_testing["preregistered_trial_ids"]
    candidate_cells = []
    for trial_id in trial_ids:
        prefix = f"{strategy_id}:"
        if type(trial_id) is not str or not trial_id.startswith(prefix):
            _fail("source_evidence.multiple_testing", "trial identity drifted")
        variant_id = trial_id[len(prefix) :]
        run_id = f"{strategy_id}:frozen:{variant_id}:stability"
        captured = run_capture.get(run_id)
        if type(captured) is not dict:
            _fail(f"run_capture.{run_id}", "missing preregistered candidate run")
        candidate_cells.append(
            {
                "trial_id": trial_id,
                "source_observation": deepcopy(captured.get("observation")),
                "source_run": deepcopy(captured.get("run")),
            }
        )
    matrix = build_strategy_trial_return_matrix(
        strategy_id=strategy_id,
        search_family_id=source_evidence["validation_evidence"][
            "formal_search_lineage"
        ]["search_family_id"],
        observation_class=source_evidence["observation_class"],
        source_plan_sha256=robustness_bundle["plan"]["plan_sha256"],
        source_robustness_bundle_sha256=robustness_bundle["bundle_sha256"],
        source_run_ledger_sha256=source_evidence["run_ledger_sha256"],
        preregistered_trial_ids=trial_ids,
        selected_trial_id=multiple_testing["selected_parameter_id"],
        selection_rule=multiple_testing["selection_rule"],
        evaluation_role=EVALUATION_ROLE,
        periods_per_year=PERIODS_PER_YEAR,
        candidate_cells=candidate_cells,
    )
    matrix_receipt = verify_strategy_trial_return_matrix(matrix)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": source_evidence["family_id"],
        "source_strategy_evidence_sha256": source_evidence["record_sha256"],
        "trial_return_matrix": matrix,
        "trial_return_matrix_receipt": matrix_receipt,
        "evidence_state": matrix_receipt["state"],
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(record, "record_sha256")


def build_synthetic_strategy_trial_return_matrix_v1(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyTrialReturnMatrixError(
            "execution requires exact execute=True; inspect the plan first"
        )
    if verify_synthetic_strategy_report_bundle_v1(baseline_bundle).get("status") != "PASS":
        _fail("baseline_bundle", "source did not verify")
    plan = plan_synthetic_strategy_trial_return_matrix_v1()
    robustness_bundle, run_capture = (
        build_synthetic_strategy_robustness_evidence_with_run_capture_v1(
            baseline_bundle, execute=True
        )
    )
    if verify_synthetic_strategy_robustness_evidence_v1(robustness_bundle).get("status") != "PASS":
        _fail("robustness_bundle", "source did not verify")
    if len(run_capture) != plan["reused_robustness_run_count"]:
        _fail("run_capture", "must cover all reused robustness runs")
    evidence_by_strategy = _source_evidence_by_strategy(robustness_bundle)
    records = [
        _build_record(evidence_by_strategy[strategy_id], robustness_bundle, run_capture)
        for strategy_id in plan["registered_strategy_ids"]
    ]
    matrix_source_run_count = sum(
        record["trial_return_matrix"]["trial_count"] for record in records
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_robustness_bundle": deepcopy(robustness_bundle),
        "source_robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "planned_run_count": plan["planned_run_count"],
        "executed_run_count": robustness_bundle["executed_run_count"],
        "additional_backtest_run_count": 0,
        "executed_analysis_count": len(records),
        "matrix_source_run_count": matrix_source_run_count,
        "strategy_records": records,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    _seal(bundle, "bundle_sha256")
    verify_synthetic_strategy_trial_return_matrix_v1(bundle)
    return bundle


def _verify_record(
    record: dict[str, Any], source_evidence: dict[str, Any], bundle: dict[str, Any]
) -> None:
    expected_keys = {
        "schema_version",
        "strategy_id",
        "family_id",
        "source_strategy_evidence_sha256",
        "trial_return_matrix",
        "trial_return_matrix_receipt",
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
    if record["strategy_id"] != source_evidence["strategy_id"]:
        _fail("strategy_record.strategy_id", "source mismatch")
    if record["family_id"] != source_evidence["family_id"]:
        _fail("strategy_record.family_id", "source mismatch")
    if record["source_strategy_evidence_sha256"] != source_evidence["record_sha256"]:
        _fail("strategy_record.source_strategy_evidence_sha256", "source mismatch")
    matrix = record["trial_return_matrix"]
    receipt = verify_strategy_trial_return_matrix(matrix)
    if receipt != record["trial_return_matrix_receipt"]:
        _fail("strategy_record.trial_return_matrix_receipt", "receipt mismatch")
    multiple_testing = source_evidence["validation_evidence"]["multiple_testing"]
    lineage = source_evidence["validation_evidence"]["formal_search_lineage"]
    binding = matrix["source_binding"]
    if matrix["preregistered_trial_ids"] != multiple_testing["preregistered_trial_ids"]:
        _fail("strategy_record.trial_return_matrix", "trial registry mismatch")
    if matrix["selected_trial_id"] != multiple_testing["selected_parameter_id"]:
        _fail("strategy_record.trial_return_matrix", "selected trial mismatch")
    if matrix["selection_rule"] != multiple_testing["selection_rule"]:
        _fail("strategy_record.trial_return_matrix", "selection rule mismatch")
    if matrix["search_family_id"] != lineage["search_family_id"]:
        _fail("strategy_record.trial_return_matrix", "search lineage mismatch")
    if binding["source_plan_sha256"] != bundle["source_robustness_bundle"]["plan"]["plan_sha256"]:
        _fail("strategy_record.trial_return_matrix", "plan binding mismatch")
    if binding["source_robustness_bundle_sha256"] != bundle["source_robustness_bundle_sha256"]:
        _fail("strategy_record.trial_return_matrix", "bundle binding mismatch")
    if binding["source_run_ledger_sha256"] != source_evidence["run_ledger_sha256"]:
        _fail("strategy_record.trial_return_matrix", "ledger binding mismatch")
    source_ledger = {item["run_id"]: item for item in source_evidence["run_ledger"]}
    for row in matrix["candidate_rows"]:
        source_observation = row["source_observation"]
        if source_ledger.get(source_observation["run_id"]) != source_observation:
            _fail("strategy_record.trial_return_matrix", "source observation mismatch")
    if (
        record["evidence_state"] != EVIDENCE_STATE
        or record["status"] != STATUS
        or record["maturity"] != MATURITY
        or record["gaps"] != _gaps()
        or record["authority"] != _authority()
    ):
        _fail("strategy_record", "maturity or authority drifted")


def verify_synthetic_strategy_trial_return_matrix_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    canonical_trial_return_matrix_sha256(bundle)
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_robustness_bundle",
        "source_robustness_bundle_sha256",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "executed_analysis_count",
        "matrix_source_run_count",
        "strategy_records",
        "runtime_mutations",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if type(bundle) is not dict or set(bundle) != expected_keys:
        _fail("bundle", "shape mismatch")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", "schema mismatch")
    if bundle["plan"] != plan_synthetic_strategy_trial_return_matrix_v1():
        _fail("bundle.plan", "must equal deterministic preregistration")
    robustness_bundle = bundle["source_robustness_bundle"]
    if verify_synthetic_strategy_robustness_evidence_v1(robustness_bundle).get("status") != "PASS":
        _fail("bundle.source_robustness_bundle", "source failed verification")
    if bundle["source_robustness_bundle_sha256"] != robustness_bundle["bundle_sha256"]:
        _fail("bundle.source_robustness_bundle_sha256", "source mismatch")
    if (
        type(bundle["planned_run_count"]) is not int
        or bundle["planned_run_count"] != 147
        or type(bundle["executed_run_count"]) is not int
        or bundle["executed_run_count"] != robustness_bundle["executed_run_count"]
        or bundle["additional_backtest_run_count"] != 0
    ):
        _fail("bundle", "run accounting drifted")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    records = bundle["strategy_records"]
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if type(records) is not list or [item.get("strategy_id") for item in records] != strategy_ids:
        _fail("bundle.strategy_records", "membership mismatch")
    source_by_strategy = _source_evidence_by_strategy(robustness_bundle)
    for record in records:
        _verify_record(record, source_by_strategy[record["strategy_id"]], bundle)
    matrix_source_run_count = sum(
        record["trial_return_matrix"]["trial_count"] for record in records
    )
    if bundle["executed_analysis_count"] != len(records):
        _fail("bundle.executed_analysis_count", "analysis count mismatch")
    if bundle["matrix_source_run_count"] != matrix_source_run_count or matrix_source_run_count != 18:
        _fail("bundle.matrix_source_run_count", "candidate source count mismatch")
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
        "trial_count": matrix_source_run_count,
        "observation_count_per_trial": records[0]["trial_return_matrix"][
            "observation_count"
        ],
        "executed_run_count": bundle["executed_run_count"],
        "additional_backtest_run_count": 0,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def render_synthetic_strategy_trial_return_matrix_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_trial_return_matrix_v1(bundle)
    rows = [
        "| Strategy | Trials | Observations per trial | Matrix SHA-256 |",
        "| --- | ---: | ---: | --- |",
    ]
    for record in bundle["strategy_records"]:
        matrix = record["trial_return_matrix"]
        rows.append(
            f"| {record['strategy_id']} | {matrix['trial_count']} | "
            f"{matrix['observation_count']} | `{matrix['matrix_sha256']}` |"
        )
    markdown = "\n".join(
        [
            "# Synthetic Strategy Trial Return Matrix v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Reuses 18 frozen-stability candidate runs from the existing 147-run robustness execution.",
            "- Additional backtest runs for matrix construction: 0",
            "- Frozen observations were not used to select the preregistered center trial.",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['state']}",
            "- This artifact is an input matrix, not a DSR or PBO result.",
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
    if "READY" in markdown:
        _fail("renderer", "neutral token violation")
    return markdown


def build_default_synthetic_strategy_trial_return_matrix_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyTrialReturnMatrixError(
            "execution requires exact execute=True; inspect the baseline and matrix plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
    return build_synthetic_strategy_trial_return_matrix_v1(baseline, execute=True)
