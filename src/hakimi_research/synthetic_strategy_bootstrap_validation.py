from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Callable

from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.bootstrap_confidence_evidence import (
    build_bootstrap_confidence_evidence,
    paired_moving_block_bootstrap_policy_v1,
    verify_bootstrap_confidence_evidence,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-record-v1"
REFERENCE_PLAN_SCHEMA_VERSION = (
    "synthetic-strategy-bootstrap-validation-plan-v2"
)
REFERENCE_BUNDLE_SCHEMA_VERSION = (
    "synthetic-strategy-bootstrap-validation-bundle-v2"
)
REFERENCE_RECEIPT_SCHEMA_VERSION = (
    "synthetic-strategy-bootstrap-validation-receipt-v2"
)
EVIDENCE_STATE = "OBSERVED"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_BOOTSTRAP_CONFIDENCE_ONLY"
OBSERVATION_CLASS = "SYNTHETIC_OBSERVATION_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "DEFLATED_SHARPE_RATIO_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
]
_REFERENCE_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "SYNTHETIC_FIXED_169_OBSERVATION_BOOTSTRAP_ONLY",
]


class SyntheticStrategyBootstrapValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyBootstrapValidationError(f"{path}: {message}")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _gaps() -> list[str]:
    return list(_GAPS)


def plan_synthetic_strategy_bootstrap_validation_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_report_bundle_v1()
    strategy_ids = source_plan["registered_strategy_ids"]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_required_run_count": source_plan["planned_run_count"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "registered_strategy_ids": strategy_ids,
        "policy": paired_moving_block_bootstrap_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def plan_synthetic_strategy_bootstrap_validation_v2() -> dict[str, Any]:
    plan = plan_synthetic_strategy_bootstrap_validation_v1()
    plan.pop("plan_sha256")
    plan["schema_version"] = REFERENCE_PLAN_SCHEMA_VERSION
    plan["source_baseline_schema_version"] = (
        "synthetic-strategy-report-bundle-v2"
    )
    plan["source_reproducibility_context_required"] = True
    plan["expected_source_dependency_bound_run_count"] = 32
    plan["expected_paired_observation_count_per_strategy"] = 169
    plan["expected_replicate_count"] = 1000
    plan["expected_interval_count_per_strategy"] = 3
    plan["formal_inference_claimed"] = False
    plan["decision_threshold"] = None
    plan["gaps"] = list(_REFERENCE_GAPS)
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def _verify_baseline(
    baseline_bundle: dict[str, Any],
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    receipt = verifier(baseline_bundle)
    if receipt.get("status") != "PASS":
        _fail("baseline_bundle", "source verifier did not return PASS")
    return receipt


def _find_strategy_report(
    baseline_bundle: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    matches = [
        report
        for report in baseline_bundle["strategy_reports"]
        if report["strategy_id"] == strategy_id
    ]
    if len(matches) != 1:
        _fail("baseline_bundle.strategy_reports", f"expected one {strategy_id} report")
    return matches[0]


def _build_record(
    baseline_bundle: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    report = _find_strategy_report(baseline_bundle, strategy_id)
    run = report["runs"]["frozen_1x"]
    benchmark = baseline_bundle["benchmarks"]["buy_and_hold"]
    evidence = build_bootstrap_confidence_evidence(
        run["result"]["equity_curve"],
        benchmark["result"]["equity_curve"],
        dataset_sha256=run["dataset_sha256"],
        strategy_result_sha256=run["result_sha256"],
        benchmark_result_sha256=benchmark["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    receipt = verify_bootstrap_confidence_evidence(
        evidence,
        run["result"]["equity_curve"],
        benchmark["result"]["equity_curve"],
        dataset_sha256=run["dataset_sha256"],
        strategy_result_sha256=run["result_sha256"],
        benchmark_result_sha256=benchmark["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": report["family_id"],
        "source_strategy_report_sha256": report["report_sha256"],
        "source_strategy_result_sha256": run["result_sha256"],
        "source_benchmark_result_sha256": benchmark["result_sha256"],
        "bootstrap_evidence": evidence,
        "bootstrap_receipt": receipt,
        "evidence_state": receipt["state"],
        "status": STATUS,
        "maturity": MATURITY,
        "observation_class": OBSERVATION_CLASS,
        "authority": _authority(),
    }
    record["record_sha256"] = _canonical_sha256(record)
    return record


def _build_synthetic_strategy_bootstrap_validation(
    baseline_bundle: dict[str, Any],
    *,
    execute: bool,
    plan: dict[str, Any],
    source_verifier: Callable[[dict[str, Any]], dict[str, Any]],
    bundle_schema_version: str,
    gaps: list[str],
    reference_binding: bool,
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBootstrapValidationError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    source_receipt = _verify_baseline(baseline_bundle, source_verifier)
    plan = deepcopy(plan)
    records = [
        _build_record(baseline_bundle, strategy_id)
        for strategy_id in plan["registered_strategy_ids"]
    ]
    observed_count = sum(
        record["bootstrap_receipt"]["state"] == "OBSERVED" for record in records
    )
    bundle = {
        "schema_version": bundle_schema_version,
        "evidence_state": "OBSERVED" if observed_count == len(records) else "GAP",
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_baseline_bundle_sha256": baseline_bundle["bundle_sha256"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "executed_analysis_count": len(records),
        "observed_evidence_count": observed_count,
        "gap_evidence_count": len(records) - observed_count,
        "strategy_records": records,
        "runtime_mutations": False,
        "gaps": list(gaps),
        "authority": _authority(),
    }
    if reference_binding:
        paired_counts = {
            record["bootstrap_receipt"]["paired_observation_count"]
            for record in records
        }
        replicate_counts = {
            record["bootstrap_receipt"]["replicate_count"]
            for record in records
        }
        interval_counts = {
            record["bootstrap_receipt"]["interval_count"]
            for record in records
        }
        if (
            paired_counts != {169}
            or replicate_counts != {1000}
            or interval_counts != {3}
        ):
            _fail("strategy_records", "v2 Bootstrap coverage drifted")
        bundle.update(
            {
                "reproducibility_context": deepcopy(
                    baseline_bundle["reproducibility_context"]
                ),
                "source_dependency_bound_run_count": source_receipt[
                    "dependency_bound_run_count"
                ],
                "source_git_bound_run_count": source_receipt[
                    "git_bound_run_count"
                ],
                "paired_observation_count_per_strategy": 169,
                "replicate_count": 1000,
                "interval_count_per_strategy": 3,
                "additional_backtest_run_count": 0,
                "formal_inference_claimed": False,
                "decision_threshold": None,
            }
        )
    bundle["bundle_sha256"] = _canonical_sha256(bundle)
    if reference_binding:
        verify_synthetic_strategy_bootstrap_validation_v2(
            bundle,
            baseline_bundle,
        )
    else:
        verify_synthetic_strategy_bootstrap_validation_v1(
            bundle,
            baseline_bundle,
        )
    return bundle


def build_synthetic_strategy_bootstrap_validation_v1(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_bootstrap_validation(
        baseline_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_bootstrap_validation_v1(),
        source_verifier=verify_synthetic_strategy_report_bundle_v1,
        bundle_schema_version=BUNDLE_SCHEMA_VERSION,
        gaps=_gaps(),
        reference_binding=False,
    )


def build_synthetic_strategy_bootstrap_validation_v2(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_bootstrap_validation(
        baseline_bundle,
        execute=execute,
        plan=plan_synthetic_strategy_bootstrap_validation_v2(),
        source_verifier=verify_synthetic_strategy_report_bundle_v2,
        bundle_schema_version=REFERENCE_BUNDLE_SCHEMA_VERSION,
        gaps=list(_REFERENCE_GAPS),
        reference_binding=True,
    )


def verify_synthetic_strategy_bootstrap_validation_v1(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    _verify_baseline(
        baseline_bundle,
        verify_synthetic_strategy_report_bundle_v1,
    )
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_baseline_bundle_sha256",
        "planned_run_count",
        "executed_run_count",
        "executed_analysis_count",
        "observed_evidence_count",
        "gap_evidence_count",
        "strategy_records",
        "runtime_mutations",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if set(bundle) != expected_keys:
        _fail("bundle", f"must contain exactly {sorted(expected_keys)}")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", f"must equal {BUNDLE_SCHEMA_VERSION}")
    if bundle["status"] != STATUS or bundle["maturity"] != MATURITY:
        _fail("bundle", "must retain BLOCK and synthetic-bootstrap maturity")
    if bundle["plan"] != plan_synthetic_strategy_bootstrap_validation_v1():
        _fail("bundle.plan", "must equal the deterministic preregistered plan")
    if bundle["source_baseline_bundle_sha256"] != baseline_bundle["bundle_sha256"]:
        _fail("bundle.source_baseline_bundle_sha256", "must bind baseline")
    if bundle["planned_run_count"] != 0 or bundle["executed_run_count"] != 0:
        _fail("bundle", "bootstrap analysis must add zero backtest runs")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    if bundle["gaps"] != _gaps() or bundle["authority"] != _authority():
        _fail("bundle", "must retain gaps and all-false authority")
    records = bundle["strategy_records"]
    if type(records) is not list:
        _fail("bundle.strategy_records", "must be an exact list")
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if [record.get("strategy_id") for record in records] != strategy_ids:
        _fail("bundle.strategy_records", "must cover registered strategies in order")
    for index, strategy_id in enumerate(strategy_ids):
        if records[index] != _build_record(baseline_bundle, strategy_id):
            _fail(
                f"bundle.strategy_records[{index}]",
                "must match deterministic source-bound evidence",
            )
    observed_count = sum(
        record["bootstrap_receipt"]["state"] == "OBSERVED" for record in records
    )
    expected_state = "OBSERVED" if observed_count == len(records) else "GAP"
    if bundle["evidence_state"] != expected_state:
        _fail("bundle.evidence_state", "must match verified evidence coverage")
    if bundle["executed_analysis_count"] != len(records):
        _fail("bundle.executed_analysis_count", "must match all records")
    if bundle["observed_evidence_count"] != observed_count:
        _fail("bundle.observed_evidence_count", "must match verified records")
    if bundle["gap_evidence_count"] != len(records) - observed_count:
        _fail("bundle.gap_evidence_count", "must match verified records")
    without_hash = dict(bundle)
    bundle_sha256 = without_hash.pop("bundle_sha256")
    if type(bundle_sha256) is not str or bundle_sha256 != _canonical_sha256(without_hash):
        _fail("bundle.bundle_sha256", "must match the canonical bundle digest")
    return {
        "schema_version": "synthetic-strategy-bootstrap-validation-receipt-v1",
        "state": bundle["evidence_state"],
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle_sha256,
        "strategy_count": len(records),
        "observed_evidence_count": observed_count,
        "gap_evidence_count": len(records) - observed_count,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def verify_synthetic_strategy_bootstrap_validation_v2(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
) -> dict[str, Any]:
    canonical_sha256(bundle)
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    source_receipt = _verify_baseline(
        baseline_bundle,
        verify_synthetic_strategy_report_bundle_v2,
    )
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_baseline_bundle_sha256",
        "planned_run_count",
        "executed_run_count",
        "executed_analysis_count",
        "observed_evidence_count",
        "gap_evidence_count",
        "strategy_records",
        "runtime_mutations",
        "gaps",
        "authority",
        "reproducibility_context",
        "source_dependency_bound_run_count",
        "source_git_bound_run_count",
        "paired_observation_count_per_strategy",
        "replicate_count",
        "interval_count_per_strategy",
        "additional_backtest_run_count",
        "formal_inference_claimed",
        "decision_threshold",
        "bundle_sha256",
    }
    if set(bundle) != expected_keys:
        _fail("bundle", "v2 shape mismatch")
    if bundle["schema_version"] != REFERENCE_BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", "v2 schema mismatch")
    if bundle["status"] != STATUS or bundle["maturity"] != MATURITY:
        _fail("bundle", "must retain BLOCK and synthetic-bootstrap maturity")
    if bundle["plan"] != plan_synthetic_strategy_bootstrap_validation_v2():
        _fail("bundle.plan", "must equal deterministic v2 plan")
    if bundle["source_baseline_bundle_sha256"] != baseline_bundle["bundle_sha256"]:
        _fail("bundle.source_baseline_bundle_sha256", "source mismatch")
    if (
        bundle["planned_run_count"] != 0
        or bundle["executed_run_count"] != 0
        or bundle["additional_backtest_run_count"] != 0
        or bundle["runtime_mutations"] is not False
    ):
        _fail("bundle", "v2 Bootstrap must add zero backtest runs")
    if (
        bundle["gaps"] != list(_REFERENCE_GAPS)
        or bundle["authority"] != _authority()
        or bundle["formal_inference_claimed"] is not False
        or bundle["decision_threshold"] is not None
    ):
        _fail("bundle", "v2 gap, authority, or inference drifted")
    if (
        type(bundle["reproducibility_context"]) is not dict
        or bundle["reproducibility_context"]
        != baseline_bundle["reproducibility_context"]
        or type(bundle["source_dependency_bound_run_count"]) is not int
        or bundle["source_dependency_bound_run_count"]
        != source_receipt["dependency_bound_run_count"]
        or bundle["source_dependency_bound_run_count"] != 32
        or type(bundle["source_git_bound_run_count"]) is not int
        or bundle["source_git_bound_run_count"]
        != source_receipt["git_bound_run_count"]
        or bundle["source_git_bound_run_count"] != 0
        or bundle["paired_observation_count_per_strategy"] != 169
        or bundle["replicate_count"] != 1000
        or bundle["interval_count_per_strategy"] != 3
    ):
        _fail("bundle", "v2 source provenance or coverage drifted")
    records = bundle["strategy_records"]
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if (
        type(records) is not list
        or [record.get("strategy_id") for record in records] != strategy_ids
    ):
        _fail("bundle.strategy_records", "v2 membership mismatch")
    for index, strategy_id in enumerate(strategy_ids):
        if records[index] != _build_record(baseline_bundle, strategy_id):
            _fail(
                f"bundle.strategy_records[{index}]",
                "must match deterministic v2 source-bound evidence",
            )
    observed_count = sum(
        record["bootstrap_receipt"]["state"] == "OBSERVED"
        for record in records
    )
    if (
        observed_count != 6
        or bundle["evidence_state"] != "OBSERVED"
        or bundle["executed_analysis_count"] != 6
        or bundle["observed_evidence_count"] != 6
        or bundle["gap_evidence_count"] != 0
        or {
            record["bootstrap_receipt"]["paired_observation_count"]
            for record in records
        }
        != {169}
        or {
            record["bootstrap_receipt"]["replicate_count"]
            for record in records
        }
        != {1000}
        or {
            record["bootstrap_receipt"]["interval_count"]
            for record in records
        }
        != {3}
    ):
        _fail("bundle", "v2 Bootstrap evidence coverage drifted")
    without_hash = dict(bundle)
    bundle_sha256 = without_hash.pop("bundle_sha256")
    if (
        type(bundle_sha256) is not str
        or bundle_sha256 != _canonical_sha256(without_hash)
    ):
        _fail("bundle.bundle_sha256", "v2 digest mismatch")
    return {
        "schema_version": REFERENCE_RECEIPT_SCHEMA_VERSION,
        "state": "OBSERVED",
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle_sha256,
        "strategy_count": 6,
        "observed_evidence_count": 6,
        "gap_evidence_count": 0,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_dependency_bound_run_count": 32,
        "source_git_bound_run_count": 0,
        "paired_observation_count_per_strategy": 169,
        "replicate_count": 1000,
        "interval_count_per_strategy": 3,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": list(_REFERENCE_GAPS),
        "authority": _authority(),
    }


def replay_synthetic_strategy_bootstrap_validation_v2(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_bootstrap_validation_v2(
        bundle,
        baseline_bundle,
    )
    replayed = build_synthetic_strategy_bootstrap_validation_v2(
        baseline_bundle,
        execute=True,
    )
    if replayed != bundle:
        _fail("replay", "deterministic v2 analysis mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_analysis_count"] = 6
    return output


def _render_synthetic_strategy_bootstrap_validation_markdown(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
    ,
    *,
    verifier: Callable[
        [dict[str, Any], dict[str, Any]],
        dict[str, Any],
    ],
    title: str,
) -> str:
    receipt = verifier(bundle, baseline_bundle)
    rows = []
    for record in bundle["strategy_records"]:
        intervals = {
            item["metric_id"]: item
            for item in record["bootstrap_evidence"]["intervals"]
        }
        strategy_interval = intervals["STRATEGY_TOTAL_RETURN"]
        difference_interval = intervals[
            "STRATEGY_MINUS_BUY_AND_HOLD_TOTAL_RETURN"
        ]
        rows.append(
            "| "
            + " | ".join(
                [
                    record["strategy_id"],
                    str(record["bootstrap_receipt"]["paired_observation_count"]),
                    f"[{strategy_interval['lower_bound']}, {strategy_interval['upper_bound']}]",
                    f"[{difference_interval['lower_bound']}, {difference_interval['upper_bound']}]",
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            title,
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Paired 5-bar moving blocks, 1000 SHA-256-derived replicates",
            "- Additional backtest runs: 0",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['state']}",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Formal inference authority: false",
            "- Profitability proof: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            "| Strategy | Paired observations | Strategy return 95% interval | Strategy-minus-benchmark 95% interval |",
            "| --- | ---: | --- | --- |",
            *rows,
            "",
            f"Bundle SHA-256: `{receipt['bundle_sha256']}`",
        ]
    )


def render_synthetic_strategy_bootstrap_validation_markdown_v1(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_bootstrap_validation_markdown(
        bundle,
        baseline_bundle,
        verifier=verify_synthetic_strategy_bootstrap_validation_v1,
        title="# Synthetic Strategy Bootstrap Confidence Validation v1",
    )


def render_synthetic_strategy_bootstrap_validation_markdown_v2(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_bootstrap_validation_markdown(
        bundle,
        baseline_bundle,
        verifier=verify_synthetic_strategy_bootstrap_validation_v2,
        title="# Synthetic Strategy Bootstrap Confidence Validation v2",
    )


def build_default_synthetic_strategy_bootstrap_validation_v2(
    *,
    execute: bool = False,
    reproducibility_context: dict[str, Any],
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBootstrapValidationError(
            "execution requires exact execute=True; inspect the v2 source plan first"
        )
    baseline = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=reproducibility_context,
    )
    return build_synthetic_strategy_bootstrap_validation_v2(
        baseline,
        execute=True,
    )
