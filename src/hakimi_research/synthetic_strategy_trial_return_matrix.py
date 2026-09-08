from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hakimi_research.synthetic_strategy_report_bundle import (
    PERIODS_PER_YEAR,
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_robustness_evidence import (
    build_synthetic_strategy_robustness_evidence_with_run_capture_v1,
    build_synthetic_strategy_robustness_evidence_with_run_capture_v2,
    plan_synthetic_strategy_robustness_evidence_v1,
    plan_synthetic_strategy_robustness_evidence_v2,
    verify_synthetic_strategy_robustness_evidence_v1,
    verify_synthetic_strategy_robustness_evidence_v2,
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
REFERENCE_PLAN_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-plan-v2"
REFERENCE_BUNDLE_SCHEMA_VERSION = "synthetic-strategy-trial-return-matrix-bundle-v2"
REFERENCE_RECEIPT_SCHEMA_VERSION = (
    "synthetic-strategy-trial-return-matrix-bundle-receipt-v2"
)
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


def plan_synthetic_strategy_trial_return_matrix_v2() -> dict[str, Any]:
    plan = plan_synthetic_strategy_trial_return_matrix_v1()
    plan.pop("plan_sha256")
    robustness_plan = plan_synthetic_strategy_robustness_evidence_v2()
    plan["schema_version"] = REFERENCE_PLAN_SCHEMA_VERSION
    plan["source_baseline_schema_version"] = (
        "synthetic-strategy-report-bundle-v2"
    )
    plan["source_robustness_schema_version"] = (
        "synthetic-strategy-robustness-evidence-v2"
    )
    plan["source_reproducibility_context_required"] = True
    plan["reused_robustness_run_count"] = robustness_plan[
        "planned_run_count"
    ]
    plan["planned_run_count"] = robustness_plan["planned_run_count"]
    plan["registered_strategy_ids"] = list(
        robustness_plan["registered_strategy_ids"]
    )
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


def _verify_candidate_manifest_bindings(
    records: list[dict[str, Any]],
    *,
    context: dict[str, Any],
    robustness_plan_sha256: str,
) -> int:
    count = 0
    for record in records:
        for row in record["trial_return_matrix"]["candidate_rows"]:
            manifest = row["source_run"]["result"].get(
                "experiment_manifest"
            )
            canonical_trial_return_matrix_sha256(manifest)
            if (
                type(manifest) is not dict
                or manifest.get("dependency_lock_hash")
                != context["dependency_lock_hash"]
                or manifest.get("dependency_lock_name")
                != context["dependency_lock_name"]
                or manifest.get("dependency_lock_fully_pinned") is not True
                or manifest.get("git_commit_sha")
                != context["git_commit_sha"]
                or manifest.get("git_worktree_clean") is not False
                or manifest.get("evaluation_role") != "FROZEN_TEST"
                or manifest.get("evaluation_protocol_hash")
                != robustness_plan_sha256
                or manifest.get("evaluation_protocol_verified") is not True
                or type(manifest.get("blockers")) is not list
                or "git_worktree_not_clean" not in manifest["blockers"]
            ):
                _fail(
                    "strategy_record.trial_return_matrix",
                    "candidate reproducibility manifest mismatch",
                )
            count += 1
    return count


def _build_synthetic_strategy_trial_return_matrix(
    baseline_bundle: dict[str, Any],
    *,
    execute: bool,
    plan: dict[str, Any],
    baseline_verifier: Callable[[dict[str, Any]], dict[str, Any]],
    robustness_builder: Callable[..., tuple[dict[str, Any], dict[str, Any]]],
    robustness_verifier: Callable[[dict[str, Any]], dict[str, Any]],
    bundle_schema_version: str,
    reference_binding: bool,
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyTrialReturnMatrixError(
            "execution requires exact execute=True; inspect the plan first"
        )
    baseline_receipt = baseline_verifier(baseline_bundle)
    if baseline_receipt.get("status") != "PASS":
        _fail("baseline_bundle", "source did not verify")
    plan = deepcopy(plan)
    robustness_bundle, run_capture = robustness_builder(
        baseline_bundle,
        execute=True,
    )
    robustness_receipt = robustness_verifier(robustness_bundle)
    if robustness_receipt.get("status") != "PASS":
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
        "schema_version": bundle_schema_version,
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
    if reference_binding:
        context = baseline_bundle.get("reproducibility_context")
        if (
            type(context) is not dict
            or context
            != robustness_bundle.get("reproducibility_context")
        ):
            _fail(
                "reproducibility_context",
                "baseline and robustness contexts must match",
            )
        matrix_dependency_bound_run_count = (
            _verify_candidate_manifest_bindings(
                records,
                context=context,
                robustness_plan_sha256=robustness_bundle["plan"][
                    "plan_sha256"
                ],
            )
        )
        bundle.update(
            {
                "reproducibility_context": deepcopy(context),
                "source_run_reproducibility_ledger_sha256": (
                    robustness_bundle["run_reproducibility_ledger"][
                        "ledger_sha256"
                    ]
                ),
                "source_dependency_bound_run_count": (
                    baseline_receipt["dependency_bound_run_count"]
                    + robustness_receipt["dependency_bound_run_count"]
                ),
                "source_git_bound_run_count": (
                    baseline_receipt["git_bound_run_count"]
                    + robustness_receipt["git_bound_run_count"]
                ),
                "matrix_dependency_bound_run_count": (
                    matrix_dependency_bound_run_count
                ),
            }
        )
    _seal(bundle, "bundle_sha256")
    if reference_binding:
        verify_synthetic_strategy_trial_return_matrix_v2(bundle)
    else:
        verify_synthetic_strategy_trial_return_matrix_v1(bundle)
    return bundle


def build_synthetic_strategy_trial_return_matrix_v1(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_trial_return_matrix(
        baseline_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_trial_return_matrix_v1(),
        baseline_verifier=verify_synthetic_strategy_report_bundle_v1,
        robustness_builder=(
            build_synthetic_strategy_robustness_evidence_with_run_capture_v1
        ),
        robustness_verifier=(
            verify_synthetic_strategy_robustness_evidence_v1
        ),
        bundle_schema_version=BUNDLE_SCHEMA_VERSION,
        reference_binding=False,
    )


def build_synthetic_strategy_trial_return_matrix_v2(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_trial_return_matrix(
        baseline_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_trial_return_matrix_v2(),
        baseline_verifier=verify_synthetic_strategy_report_bundle_v2,
        robustness_builder=(
            build_synthetic_strategy_robustness_evidence_with_run_capture_v2
        ),
        robustness_verifier=(
            verify_synthetic_strategy_robustness_evidence_v2
        ),
        bundle_schema_version=REFERENCE_BUNDLE_SCHEMA_VERSION,
        reference_binding=True,
    )


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


def verify_synthetic_strategy_trial_return_matrix_v2(
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
    if bundle["plan"] != plan_synthetic_strategy_trial_return_matrix_v2():
        _fail("bundle.plan", "must equal deterministic v2 preregistration")
    robustness_bundle = bundle["source_robustness_bundle"]
    robustness_receipt = (
        verify_synthetic_strategy_robustness_evidence_v2(
            robustness_bundle
        )
    )
    if robustness_receipt.get("status") != "PASS":
        _fail("bundle.source_robustness_bundle", "v2 source failed verification")
    baseline_bundle = robustness_bundle["source_bundle"]
    baseline_receipt = verify_synthetic_strategy_report_bundle_v2(
        baseline_bundle
    )
    if baseline_receipt.get("status") != "PASS":
        _fail("bundle.source_robustness_bundle.source_bundle", "v2 baseline failed")
    if bundle["source_robustness_bundle_sha256"] != robustness_bundle["bundle_sha256"]:
        _fail("bundle.source_robustness_bundle_sha256", "source mismatch")
    if (
        type(bundle["planned_run_count"]) is not int
        or bundle["planned_run_count"] != 147
        or type(bundle["executed_run_count"]) is not int
        or bundle["executed_run_count"]
        != robustness_bundle["executed_run_count"]
        or bundle["additional_backtest_run_count"] != 0
    ):
        _fail("bundle", "v2 run accounting drifted")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    records = bundle["strategy_records"]
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if (
        type(records) is not list
        or [item.get("strategy_id") for item in records] != strategy_ids
    ):
        _fail("bundle.strategy_records", "v2 membership mismatch")
    source_by_strategy = _source_evidence_by_strategy(robustness_bundle)
    for record in records:
        _verify_record(
            record,
            source_by_strategy[record["strategy_id"]],
            bundle,
        )
    matrix_source_run_count = sum(
        record["trial_return_matrix"]["trial_count"] for record in records
    )
    if (
        bundle["executed_analysis_count"] != len(records)
        or bundle["matrix_source_run_count"] != matrix_source_run_count
        or matrix_source_run_count != 18
    ):
        _fail("bundle", "v2 analysis or candidate count mismatch")
    context = bundle["reproducibility_context"]
    if (
        type(context) is not dict
        or context != robustness_bundle["reproducibility_context"]
        or context != baseline_bundle["reproducibility_context"]
    ):
        _fail("bundle.reproducibility_context", "v2 source mismatch")
    if (
        bundle["source_run_reproducibility_ledger_sha256"]
        != robustness_bundle["run_reproducibility_ledger"][
            "ledger_sha256"
        ]
    ):
        _fail(
            "bundle.source_run_reproducibility_ledger_sha256",
            "ledger mismatch",
        )
    expected_dependency_count = (
        baseline_receipt["dependency_bound_run_count"]
        + robustness_receipt["dependency_bound_run_count"]
    )
    expected_git_count = (
        baseline_receipt["git_bound_run_count"]
        + robustness_receipt["git_bound_run_count"]
    )
    matrix_dependency_count = _verify_candidate_manifest_bindings(
        records,
        context=context,
        robustness_plan_sha256=robustness_bundle["plan"]["plan_sha256"],
    )
    if (
        type(bundle["source_dependency_bound_run_count"]) is not int
        or bundle["source_dependency_bound_run_count"]
        != expected_dependency_count
        or expected_dependency_count != 179
        or type(bundle["source_git_bound_run_count"]) is not int
        or bundle["source_git_bound_run_count"] != expected_git_count
        or expected_git_count != 0
        or type(bundle["matrix_dependency_bound_run_count"]) is not int
        or bundle["matrix_dependency_bound_run_count"]
        != matrix_dependency_count
        or matrix_dependency_count != 18
    ):
        _fail("bundle", "v2 reproducibility accounting drifted")
    if (
        bundle["evidence_state"] != EVIDENCE_STATE
        or bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["gaps"] != _gaps()
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "v2 maturity or authority drifted")
    return {
        "schema_version": REFERENCE_RECEIPT_SCHEMA_VERSION,
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
        "source_dependency_bound_run_count": expected_dependency_count,
        "source_git_bound_run_count": expected_git_count,
        "matrix_dependency_bound_run_count": matrix_dependency_count,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def _render_synthetic_strategy_trial_return_matrix_markdown(
    bundle: dict[str, Any],
    *,
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
    title: str,
) -> str:
    receipt = verifier(bundle)
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
            title,
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


def render_synthetic_strategy_trial_return_matrix_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_trial_return_matrix_markdown(
        bundle,
        verifier=verify_synthetic_strategy_trial_return_matrix_v1,
        title="# Synthetic Strategy Trial Return Matrix v1",
    )


def render_synthetic_strategy_trial_return_matrix_markdown_v2(
    bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_trial_return_matrix_markdown(
        bundle,
        verifier=verify_synthetic_strategy_trial_return_matrix_v2,
        title="# Synthetic Strategy Trial Return Matrix v2",
    )


def build_default_synthetic_strategy_trial_return_matrix_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyTrialReturnMatrixError(
            "execution requires exact execute=True; inspect the baseline and matrix plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
    return build_synthetic_strategy_trial_return_matrix_v1(baseline, execute=True)


def build_default_synthetic_strategy_trial_return_matrix_v2(
    *,
    execute: bool = False,
    reproducibility_context: dict[str, Any],
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyTrialReturnMatrixError(
            "execution requires exact execute=True; inspect the v2 source and matrix plans first"
        )
    baseline = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=reproducibility_context,
    )
    return build_synthetic_strategy_trial_return_matrix_v2(
        baseline,
        execute=True,
    )
