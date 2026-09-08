from __future__ import annotations

import hashlib
import json
from typing import Any

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
)
from hakimi_research.bootstrap_confidence_evidence import (
    build_bootstrap_confidence_evidence,
    paired_moving_block_bootstrap_policy_v1,
    verify_bootstrap_confidence_evidence,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-record-v1"
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


def build_synthetic_strategy_bootstrap_validation_v1(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBootstrapValidationError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    verify_synthetic_strategy_report_bundle_v1(baseline_bundle)
    plan = plan_synthetic_strategy_bootstrap_validation_v1()
    records = [
        _build_record(baseline_bundle, strategy_id)
        for strategy_id in plan["registered_strategy_ids"]
    ]
    observed_count = sum(
        record["bootstrap_receipt"]["state"] == "OBSERVED" for record in records
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
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
        "gaps": _gaps(),
        "authority": _authority(),
    }
    bundle["bundle_sha256"] = _canonical_sha256(bundle)
    verify_synthetic_strategy_bootstrap_validation_v1(bundle, baseline_bundle)
    return bundle


def verify_synthetic_strategy_bootstrap_validation_v1(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    verify_synthetic_strategy_report_bundle_v1(baseline_bundle)
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


def render_synthetic_strategy_bootstrap_validation_markdown_v1(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
) -> str:
    receipt = verify_synthetic_strategy_bootstrap_validation_v1(
        bundle, baseline_bundle
    )
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
            "# Synthetic Strategy Bootstrap Confidence Validation v1",
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
