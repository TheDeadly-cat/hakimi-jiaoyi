from __future__ import annotations

import hashlib
import json
from typing import Any

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    verify_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 import (
    plan_synthetic_strategy_robustness_evidence_v1,
    verify_synthetic_strategy_robustness_evidence_v1,
)
from hakimi_research.market_regime_evidence import (
    build_market_regime_evidence,
    market_regime_policy_v1,
    verify_market_regime_evidence,
)
from hakimi_research.validation_evidence import (
    build_validation_evidence,
    verify_validation_evidence,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-market-regime-validation-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-market-regime-validation-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-market-regime-validation-record-v1"
STATUS = "GAP"
MATURITY = "SYNTHETIC_MARKET_REGIME_PARTIAL"
OBSERVATION_CLASS = "SYNTHETIC_OBSERVATION_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "HIGH_VOLATILITY_REGIME_COVERAGE_GAP",
    "REAL_DATASET_GAP",
]


class SyntheticStrategyMarketRegimeValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyMarketRegimeValidationError(f"{path}: {message}")


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


def plan_synthetic_strategy_market_regime_validation_v1() -> dict[str, Any]:
    strategy_ids = plan_synthetic_strategy_robustness_evidence_v1()[
        "registered_strategy_ids"
    ]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_required_run_count": 179,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "registered_strategy_ids": strategy_ids,
        "policy": market_regime_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "authority": _authority(),
        "gaps": _gaps(),
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def _find_strategy_report(
    baseline_bundle: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    matches = [
        item
        for item in baseline_bundle["strategy_reports"]
        if item["strategy_id"] == strategy_id
    ]
    if len(matches) != 1:
        _fail("baseline_bundle.strategy_reports", f"expected one {strategy_id} report")
    return matches[0]


def _find_robustness_record(
    robustness_bundle: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    matches = [
        item
        for item in robustness_bundle["strategy_evidence"]
        if item["strategy_id"] == strategy_id
    ]
    if len(matches) != 1:
        _fail("robustness_bundle.strategy_evidence", f"expected one {strategy_id} record")
    return matches[0]


def _source_inputs(
    baseline_bundle: dict[str, Any], strategy_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    strategy_report = _find_strategy_report(baseline_bundle, strategy_id)
    strategy_run = strategy_report["runs"]["frozen_1x"]
    benchmark_run = baseline_bundle["benchmarks"]["buy_and_hold"]
    frozen_start, frozen_end = baseline_bundle["fixture"]["partition_protocol"][
        "frozen_slice"
    ]
    market_records = baseline_bundle["fixture"]["records"][frozen_start:frozen_end]
    return strategy_report, strategy_run, benchmark_run, market_records


def _build_record(
    baseline_bundle: dict[str, Any],
    robustness_bundle: dict[str, Any],
    strategy_id: str,
) -> dict[str, Any]:
    strategy_report, strategy_run, benchmark_run, market_records = _source_inputs(
        baseline_bundle, strategy_id
    )
    source_record = _find_robustness_record(robustness_bundle, strategy_id)
    regime_evidence = build_market_regime_evidence(
        market_records,
        strategy_run["result"]["equity_curve"],
        benchmark_run["result"]["equity_curve"],
        dataset_sha256=strategy_run["dataset_sha256"],
        strategy_result_sha256=strategy_run["result_sha256"],
        benchmark_result_sha256=benchmark_run["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    regime_receipt = verify_market_regime_evidence(
        regime_evidence,
        market_records,
        strategy_run["result"]["equity_curve"],
        benchmark_run["result"]["equity_curve"],
        dataset_sha256=strategy_run["dataset_sha256"],
        strategy_result_sha256=strategy_run["result_sha256"],
        benchmark_result_sha256=benchmark_run["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )

    source_validation = source_record["validation_evidence"]
    source_report = strategy_report
    if _canonical_sha256(source_report) != source_validation["source_report_sha256"]:
        _fail(
            "source_report_sha256",
            "full strategy report must match the robustness validation source",
        )
    multiple_testing_input = dict(source_validation["multiple_testing"])
    multiple_testing_input.pop("ledger_sha256", None)
    validation_evidence = build_validation_evidence(
        source_report,
        experiment_id=f"{source_validation['experiment_id']}-market-regime-v1",
        formal_search_lineage=source_validation["formal_search_lineage"],
        distribution_evidence=source_validation["distribution_evidence"],
        walk_forward=source_validation["walk_forward"],
        parameter_stability=source_validation["parameter_stability"],
        multiple_testing=multiple_testing_input,
        market_regimes=regime_evidence["consumer_view"],
    )
    validation_receipt = verify_validation_evidence(validation_evidence, source_report)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": source_record["family_id"],
        "source_strategy_report_sha256": strategy_report["report_sha256"],
        "source_robustness_record_sha256": source_record["record_sha256"],
        "market_regime_evidence": regime_evidence,
        "market_regime_receipt": regime_receipt,
        "validation_evidence": validation_evidence,
        "validation_receipt": validation_receipt,
        "status": STATUS,
        "observation_class": OBSERVATION_CLASS,
        "authority": _authority(),
    }
    record["record_sha256"] = _canonical_sha256(record)
    return record


def build_synthetic_strategy_market_regime_validation_v1(
    baseline_bundle: dict[str, Any],
    robustness_bundle: dict[str, Any],
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyMarketRegimeValidationError(
            "analysis requires exact execute=True; inspect the plan first"
        )
    verify_synthetic_strategy_report_bundle_v1(baseline_bundle)
    verify_synthetic_strategy_robustness_evidence_v1(robustness_bundle)
    if robustness_bundle["source_bundle"] != baseline_bundle:
        _fail("robustness_bundle.source_bundle", "must equal the verified baseline bundle")

    plan = plan_synthetic_strategy_market_regime_validation_v1()
    records = [
        _build_record(baseline_bundle, robustness_bundle, strategy_id)
        for strategy_id in plan["registered_strategy_ids"]
    ]
    observed_slice_count = sum(
        record["market_regime_receipt"]["observed_count"] for record in records
    )
    gap_slice_count = sum(
        record["market_regime_receipt"]["gap_count"] for record in records
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_baseline_bundle_sha256": baseline_bundle["bundle_sha256"],
        "source_robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "executed_analysis_count": len(records),
        "observed_slice_count": observed_slice_count,
        "gap_slice_count": gap_slice_count,
        "strategy_records": records,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    bundle["bundle_sha256"] = _canonical_sha256(bundle)
    verify_synthetic_strategy_market_regime_validation_v1(
        bundle, baseline_bundle, robustness_bundle
    )
    return bundle


def verify_synthetic_strategy_market_regime_validation_v1(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
    robustness_bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    verify_synthetic_strategy_report_bundle_v1(baseline_bundle)
    verify_synthetic_strategy_robustness_evidence_v1(robustness_bundle)
    expected_keys = {
        "schema_version",
        "status",
        "maturity",
        "plan",
        "source_baseline_bundle_sha256",
        "source_robustness_bundle_sha256",
        "planned_run_count",
        "executed_run_count",
        "executed_analysis_count",
        "observed_slice_count",
        "gap_slice_count",
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
        _fail("bundle", "must retain GAP state and partial synthetic maturity")
    if bundle["plan"] != plan_synthetic_strategy_market_regime_validation_v1():
        _fail("bundle.plan", "must equal the deterministic preregistered plan")
    if bundle["source_baseline_bundle_sha256"] != baseline_bundle["bundle_sha256"]:
        _fail("bundle.source_baseline_bundle_sha256", "must bind the baseline bundle")
    if (
        bundle["source_robustness_bundle_sha256"]
        != robustness_bundle["bundle_sha256"]
    ):
        _fail("bundle.source_robustness_bundle_sha256", "must bind robustness")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    if bundle["authority"] != _authority() or bundle["gaps"] != _gaps():
        _fail("bundle", "must retain authority and gap contracts")
    if bundle["planned_run_count"] != 0 or bundle["executed_run_count"] != 0:
        _fail("bundle", "market-regime analysis must add zero backtest runs")

    records = bundle["strategy_records"]
    if type(records) is not list:
        _fail("bundle.strategy_records", "must be an exact list")
    strategy_ids = bundle["plan"]["registered_strategy_ids"]
    if [record.get("strategy_id") for record in records] != strategy_ids:
        _fail("bundle.strategy_records", "must cover each registered strategy in order")
    for index, record in enumerate(records):
        expected = _build_record(
            baseline_bundle, robustness_bundle, strategy_ids[index]
        )
        if record != expected:
            _fail(
                f"bundle.strategy_records[{index}]",
                "must match source-bound market-regime validation",
            )
    observed_slice_count = sum(
        record["market_regime_receipt"]["observed_count"] for record in records
    )
    gap_slice_count = sum(
        record["market_regime_receipt"]["gap_count"] for record in records
    )
    if bundle["executed_analysis_count"] != len(strategy_ids):
        _fail("bundle.executed_analysis_count", "must cover all strategies")
    if bundle["observed_slice_count"] != observed_slice_count:
        _fail("bundle.observed_slice_count", "must match verified records")
    if bundle["gap_slice_count"] != gap_slice_count:
        _fail("bundle.gap_slice_count", "must match verified records")
    without_hash = dict(bundle)
    bundle_sha256 = without_hash.pop("bundle_sha256")
    if type(bundle_sha256) is not str or bundle_sha256 != _canonical_sha256(without_hash):
        _fail("bundle.bundle_sha256", "must match the canonical bundle digest")
    return {
        "schema_version": "synthetic-strategy-market-regime-validation-receipt-v1",
        "state": STATUS,
        "bundle_sha256": bundle_sha256,
        "strategy_count": len(strategy_ids),
        "observed_slice_count": observed_slice_count,
        "gap_slice_count": gap_slice_count,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "runtime_mutations": False,
        "maturity": MATURITY,
        "authority": _authority(),
        "gaps": _gaps(),
    }


def render_synthetic_strategy_market_regime_validation_markdown_v1(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
    robustness_bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_market_regime_validation_v1(
        bundle, baseline_bundle, robustness_bundle
    )
    rows = []
    for record in bundle["strategy_records"]:
        states = {
            item["regime_id"]: item["status"]
            for item in record["market_regime_evidence"]["observations"]
        }
        rows.append(
            "| "
            + " | ".join(
                [
                    record["strategy_id"],
                    states["BULL"],
                    states["BEAR"],
                    states["RANGE"],
                    states["HIGH_VOLATILITY"],
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# Synthetic Strategy Market-Regime Validation v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Fixed 20-bar causal policy with one-bar label lag",
            "- Additional backtest runs: 0",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            "- Status: GAP",
            "",
            "## PERMISSION",
            "- Research-only synthetic evidence",
            "- Profitability proof: false",
            "- Blind-test completion: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            "| Strategy | BULL | BEAR | RANGE | HIGH_VOLATILITY |",
            "| --- | --- | --- | --- | --- |",
            *rows,
            "",
            f"Bundle SHA-256: `{receipt['bundle_sha256']}`",
        ]
    )
