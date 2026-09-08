from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    verify_synthetic_strategy_benchmark_controls_v1,
)
from hakimi_research.deterministic_strategy_research_dossier_v1 import (
    REFERENCE_FILE_NAMES as SOURCE_DOSSIER_REFERENCE_FILE_NAMES,
    REFERENCE_ROOT as SOURCE_DOSSIER_REFERENCE_ROOT,
    build_deterministic_strategy_research_dossier_material_v1,
    verify_deterministic_strategy_research_dossier_reference_v1,
)
from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.distribution_evidence import verify_distribution_evidence
from hakimi_research.experiment_manifest import (
    verify_reproducible_experiment_manifest,
)
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256


CONTRACT_VERSION = "deterministic-strategy-research-dossier-v2"
VERIFIER_VERSION = "deterministic-strategy-research-dossier-verifier-v2"
RECEIPT_VERSION = "deterministic-strategy-research-dossier-receipt-v2"
MANIFEST_VERSION = "deterministic-strategy-research-dossier-manifest-v2"
PROJECTION_VERSION = "deterministic-strategy-benchmark-control-projection-v1"
FROZEN_DISTRIBUTION_PROJECTION_VERSION = (
    "deterministic-strategy-frozen-distribution-metric-projection-v1"
)
FROZEN_COST_STRESS_PROJECTION_VERSION = (
    "deterministic-strategy-frozen-cost-stress-projection-v1"
)
FROZEN_EXPERIMENT_PROVENANCE_PROJECTION_VERSION = (
    "deterministic-strategy-frozen-experiment-provenance-projection-v1"
)
EVIDENCE_GAP_RECONCILIATION_VERSION = (
    "deterministic-strategy-evidence-gap-reconciliation-v1"
)
MATURITY = "SYNTHETIC_NON_CURRENT_BENCHMARK_CONTROL_PROJECTION_ONLY"
STATUS = "BLOCK"
FAMILY_BUNDLE_REFERENCE = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_family_benchmark_v1"
    / "expected_bundle.json"
)
ROBUSTNESS_RECEIPT_REFERENCE = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_robustness_benchmark_v1"
    / "expected_receipt.json"
)
STATISTICAL_V3_RECEIPT_REFERENCE = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_statistical_correction_benchmark_v3"
    / "expected_receipt.json"
)
DISTRIBUTION_METRIC_IDS = (
    "cagr_observation",
    "annualized_volatility",
    "sortino_ratio",
    "calmar_ratio",
    "max_drawdown",
    "max_drawdown_duration_periods",
    "max_drawdown_duration_start",
    "max_drawdown_duration_end",
    "profit_factor",
    "win_rate",
    "payoff_ratio",
    "trade_expectancy",
    "turnover_ratio",
    "fee_load_ratio",
    "market_exposure_ratio",
    "tail_var_95",
    "tail_cvar_95",
    "tail_var_99",
    "tail_cvar_99",
    "period_return_count",
    "closed_trade_count",
)
CONCENTRATION_METRIC_IDS = (
    "top_positive_period_return_share",
    "positive_period_return_hhi",
    "top_positive_month_share",
    "compound_return_without_best_period",
    "compound_return_without_best_month",
    "best_fixed_21_period_window",
    "top_positive_trade_pnl_share",
    "positive_trade_pnl_hhi",
    "pnl_without_best_trade",
)
FROZEN_COST_RUN_IDS = ("frozen_1x", "frozen_2x", "frozen_3x")
FROZEN_COST_ROLES = (
    "FROZEN_COST_1X",
    "FROZEN_COST_2X",
    "FROZEN_COST_3X",
)
FROZEN_FEE_RATES = (
    "0.00050000000000000001",
    "0.001",
    "0.0015",
)
FROZEN_SLIPPAGE_RATES = (
    "0.00020000000000000001",
    "0.00040000000000000002",
    "0.00060000000000000006",
)
FROZEN_PROVENANCE_FIELD_IDS = (
    "experiment_id",
    "git_commit_sha",
    "git_worktree_clean",
    "strategy_name",
    "strategy_version",
    "config_hash",
    "dataset_hash",
    "dependency_lock_name",
    "dependency_lock_hash",
    "dependency_lock_fully_pinned",
    "start_time",
    "end_time",
    "symbol",
    "timeframe",
    "fee_model",
    "slippage_model",
    "random_seed",
    "runtime_version",
    "result_hash",
    "source_run_hash",
    "evaluation_protocol_hash",
    "evaluation_protocol_verified",
    "classification",
    "status",
    "blockers",
)
RESOLVED_STALE_GAP_IDS = (
    "BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED",
    "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED",
    "MULTIPLE_TESTING_NOT_EXECUTED",
    "PARAMETER_STABILITY_NOT_EXECUTED",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED",
    "WALK_FORWARD_NOT_EXECUTED",
)
REQUIRED_RETAINED_GAP_IDS = (
    "FULL_UNIT_PBO_IDENTIFIED_SET_REMAINS",
    "OVERLAPPING_WALK_FORWARD_WINDOWS_NO_INDEPENDENCE_CLAIM",
    "PARTIAL_PBO_IDENTIFIED_SET_REMAINS",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
    "REAL_MARKET_DATA_NOT_USED",
)
REFERENCE_ROOT = (
    REPOSITORY_ROOT / "examples" / "deterministic_strategy_research_dossier_v2"
)
REFERENCE_FILE_NAMES = (
    "expected_receipt.json",
    "expected_report.md",
    "fixture_manifest.json",
)
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"

SOURCE_RELATIVE_PATHS = (
    "outputs/python_quant_bot/exchange_terminal/application/"
    "deterministic_strategy_research_dossier_v2.py",
    "outputs/python_quant_bot/exchange_terminal/application/"
    "synthetic_strategy_benchmark_controls_v1.py",
    "outputs/python_quant_bot/exchange_terminal/application/"
    "synthetic_strategy_report_bundle_v1.py",
    "outputs/python_quant_bot/examples/"
    "build_deterministic_strategy_research_dossier_v2.py",
    "src/hakimi_research/deterministic_strategy_research_dossier_v1.py",
    "src/hakimi_research/synthetic_benchmark_controls.py",
)

BENCHMARK_CONTROL_IDS = (
    "cash",
    "buy_and_hold",
    "simple_ma",
    "simple_breakout",
    "hash_no_skill_median",
    "volatility_matched_buy_and_hold",
)
EXPECTED_STRATEGY_IDS = (
    "bollinger",
    "dual_ma",
    "grid",
    "macd",
    "momentum",
    "rsi",
)
EXPECTED_CONTROL_RUN_IDS = (
    "simple_ma",
    "simple_breakout",
    *tuple(f"hash_no_skill_{index:02d}" for index in range(16)),
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
    "ranking_authorized": False,
}
_V2_GAPS = {
    "BENCHMARK_CONTROL_TO_RECORDED_V14_IDENTITY_ALIGNMENT_NOT_PROVEN",
    "CONTROL_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION",
    "NON_CURRENT_DOSSIER_V2_CANDIDATE",
}


class DeterministicStrategyResearchDossierV2Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise DeterministicStrategyResearchDossierV2Error(message)


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must contain finite native floats")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    raise TypeError(f"{path} must use exact native JSON types")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    _require_exact_json(value)
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = copy.deepcopy(unsigned)
    result[field] = canonical_sha256(unsigned)
    return result


def _require_denied_authority(value: Any, label: str) -> None:
    if type(value) is not dict or not value:
        _fail(f"{label} authority missing")
    if any(type(item) is not bool or item is not False for item in value.values()):
        _fail(f"{label} authority escalation")


def _control_projection(bundle: dict[str, Any]) -> dict[str, Any]:
    _require_exact_json(bundle, path="$.benchmark_controls_bundle")
    receipt = verify_synthetic_strategy_benchmark_controls_v1(bundle)
    _require_exact_json(receipt, path="$.benchmark_controls_receipt")
    if receipt.get("status") != STATUS or receipt.get("state") != "OBSERVED_WITH_GAPS":
        _fail("benchmark-control receipt maturity drifted")
    if receipt.get("runtime_mutations") is not False:
        _fail("benchmark-control runtime mutations must remain false")
    _require_denied_authority(receipt.get("authority"), "benchmark control")

    control_runs = bundle.get("control_runs")
    if type(control_runs) is not list:
        _fail("control runs missing")
    control_identities = [
        {
            "control_id": item.get("control_id"),
            "control_kind": item.get("control_kind"),
        }
        for item in control_runs
    ]
    if tuple(item["control_id"] for item in control_identities) != EXPECTED_CONTROL_RUN_IDS:
        _fail("control run identity or order drifted")

    distribution = bundle.get("no_skill_distribution")
    if type(distribution) is not dict or distribution.get("path_count") != 16:
        _fail("no-skill distribution missing")
    summary = distribution.get("summary")
    if type(summary) is not dict or set(summary) != {
        "maximum",
        "median_type7",
        "minimum",
        "q25_type7",
        "q75_type7",
        "summary_sha256",
    }:
        _fail("no-skill summary shape drifted")

    comparisons = bundle.get("strategy_control_comparisons")
    if type(comparisons) is not list:
        _fail("strategy control comparisons missing")
    if tuple(item.get("strategy_id") for item in comparisons) != EXPECTED_STRATEGY_IDS:
        _fail("strategy control comparison membership drifted")
    comparison_rows = []
    for item in comparisons:
        controls = item.get("control_total_returns")
        deltas = item.get("strategy_minus_control_return_deltas")
        if type(controls) is not dict or tuple(controls) != BENCHMARK_CONTROL_IDS:
            _fail("control return identity or order drifted")
        if type(deltas) is not dict or tuple(deltas) != BENCHMARK_CONTROL_IDS:
            _fail("control delta identity or order drifted")
        if item.get("ranking_performed") is not False:
            _fail("strategy control comparison ranking escalation")
        _require_denied_authority(item.get("authority"), "strategy comparison")
        comparison_rows.append(
            {
                "strategy_id": item["strategy_id"],
                "strategy_frozen_total_return": item["strategy_frozen_total_return"],
                "control_total_returns": copy.deepcopy(controls),
                "strategy_minus_control_return_deltas": copy.deepcopy(deltas),
                "comparison_sha256": item["comparison_sha256"],
            }
        )

    projections = bundle.get("volatility_matched_projections")
    if type(projections) is not list:
        _fail("volatility-matched projections missing")
    if tuple(item.get("strategy_id") for item in projections) != EXPECTED_STRATEGY_IDS:
        _fail("volatility projection membership drifted")
    projection_rows = []
    for item in projections:
        if item.get("executable_claim") is not False:
            _fail("volatility projection executable-claim escalation")
        _require_denied_authority(item.get("authority"), "volatility projection")
        projection_rows.append(
            {
                "strategy_id": item["strategy_id"],
                "strategy_annualised_sample_volatility": item[
                    "strategy_annualised_sample_volatility"
                ],
                "projected_annualised_sample_volatility": item[
                    "projected_annualised_sample_volatility"
                ],
                "scaling_multiplier": item["scaling_multiplier"],
                "volatility_matched_buy_and_hold_compounded_return": item[
                    "volatility_matched_buy_and_hold_compounded_return"
                ],
                "projection_sha256": item["projection_sha256"],
                "executable_claim": False,
            }
        )

    core = {
        "schema_version": PROJECTION_VERSION,
        "source_control_receipt": copy.deepcopy(receipt),
        "source_control_bundle_sha256": receipt["bundle_sha256"],
        "source_control_plan_sha256": bundle["plan"]["plan_sha256"],
        "source_baseline_bundle_sha256": bundle[
            "source_baseline_bundle_sha256"
        ],
        "benchmark_control_ids": list(BENCHMARK_CONTROL_IDS),
        "control_run_identities": control_identities,
        "no_skill_distribution": {
            "path_count": distribution["path_count"],
            "summary": copy.deepcopy(summary),
            "distribution_sha256": distribution["distribution_sha256"],
        },
        "strategy_control_comparisons": comparison_rows,
        "volatility_matched_projections": projection_rows,
        "source_reused_run_count": receipt["source_reused_run_count"],
        "additional_backtest_run_count": receipt[
            "additional_backtest_run_count"
        ],
        "control_rebuild_performed": True,
        "control_to_recorded_v14_identity_alignment_proven": False,
        "equal_volatility_projection_executable": False,
        "candidate_only": True,
        "current_activation": False,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(core, "projection_sha256")


def _frozen_distribution_metric_projection(
    source_v1: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_json(source_v1, path="$.source_dossier_v1")
    source_receipt = source_v1["receipt"]
    family_bytes = FAMILY_BUNDLE_REFERENCE.read_bytes()
    family_file_sha256 = _sha256_bytes(family_bytes)
    if family_file_sha256 != source_receipt["component_file_sha256"][
        "family_bundle_json"
    ]:
        _fail("Frozen distribution source family bundle identity drifted")
    family_bundle = json.loads(family_bytes.decode("utf-8"))
    _require_exact_json(family_bundle, path="$.family_bundle")
    reports = family_bundle.get("strategy_reports")
    if type(reports) is not list:
        _fail("Frozen distribution source strategy_reports must be a native list")
    if [report.get("strategy_id") for report in reports] != list(
        EXPECTED_STRATEGY_IDS
    ):
        _fail("Frozen distribution source strategy order drifted")

    strategy_metrics: list[dict[str, Any]] = []
    for report in reports:
        strategy_id = report["strategy_id"]
        frozen = report.get("frozen_distribution")
        if type(frozen) is not dict:
            _fail(f"{strategy_id} Frozen distribution binding is missing")
        source_report = frozen.get("source_report")
        evidence = frozen.get("evidence")
        if type(source_report) is not dict or type(evidence) is not dict:
            _fail(f"{strategy_id} Frozen distribution source/evidence is missing")
        verify_distribution_evidence(evidence, source_report)
        source_sha256 = canonical_sha256(source_report)
        if source_sha256 != frozen.get("source_report_sha256"):
            _fail(f"{strategy_id} Frozen distribution source hash drifted")
        if source_sha256 != evidence.get("source_report_sha256"):
            _fail(f"{strategy_id} Frozen distribution evidence binding drifted")
        if source_report.get("strategy_id") != strategy_id:
            _fail(f"{strategy_id} Frozen distribution strategy binding drifted")
        if source_report.get("evaluation_role") != "FROZEN_COST_1X":
            _fail(f"{strategy_id} Frozen distribution role drifted")

        metrics = evidence.get("metrics")
        concentration = evidence.get("concentration")
        if type(metrics) is not dict or set(metrics) != set(DISTRIBUTION_METRIC_IDS):
            _fail(f"{strategy_id} Frozen distribution metric inventory drifted")
        if type(concentration) is not dict or set(concentration) != set(
            CONCENTRATION_METRIC_IDS
        ):
            _fail(f"{strategy_id} Frozen concentration inventory drifted")
        result = source_report.get("result")
        if type(result) is not dict:
            _fail(f"{strategy_id} Frozen result is missing")
        for metric_id in ("total_return", "sharpe_ratio"):
            value = result.get(metric_id)
            if type(value) not in (int, float) or not math.isfinite(float(value)):
                _fail(f"{strategy_id} Frozen {metric_id} is not finite")

        strategy_metrics.append(
            {
                "strategy_id": strategy_id,
                "evaluation_role": source_report["evaluation_role"],
                "fixture_id": source_report["fixture_id"],
                "source_report_sha256": source_sha256,
                "distribution_evidence_sha256": evidence["evidence_sha256"],
                "distribution_status": evidence["status"],
                "distribution_gaps": copy.deepcopy(evidence["gaps"]),
                "total_return": result["total_return"],
                "sharpe_ratio": result["sharpe_ratio"],
                "metrics": {
                    metric_id: copy.deepcopy(metrics[metric_id])
                    for metric_id in DISTRIBUTION_METRIC_IDS
                },
                "monthly_returns": copy.deepcopy(evidence["monthly_returns"]),
                "monthly_summary": copy.deepcopy(evidence["monthly_summary"]),
                "yearly_returns": copy.deepcopy(evidence["yearly_returns"]),
                "yearly_summary": copy.deepcopy(evidence["yearly_summary"]),
                "concentration": {
                    metric_id: copy.deepcopy(concentration[metric_id])
                    for metric_id in CONCENTRATION_METRIC_IDS
                },
            }
        )

    return _seal(
        {
            "schema_version": FROZEN_DISTRIBUTION_PROJECTION_VERSION,
            "source_family_bundle_file_sha256": family_file_sha256,
            "strategy_ids": list(EXPECTED_STRATEGY_IDS),
            "strategy_count": len(strategy_metrics),
            "distribution_metric_ids": list(DISTRIBUTION_METRIC_IDS),
            "concentration_metric_ids": list(CONCENTRATION_METRIC_IDS),
            "strategy_metrics": strategy_metrics,
        },
        "projection_sha256",
    )


def _frozen_cost_stress_projection(
    source_v1: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_json(source_v1, path="$.source_dossier_v1")
    source_receipt = source_v1["receipt"]
    family_bytes = FAMILY_BUNDLE_REFERENCE.read_bytes()
    family_file_sha256 = _sha256_bytes(family_bytes)
    if family_file_sha256 != source_receipt["component_file_sha256"][
        "family_bundle_json"
    ]:
        _fail("Frozen cost-stress source family bundle identity drifted")
    family_bundle = json.loads(family_bytes.decode("utf-8"))
    _require_exact_json(family_bundle, path="$.family_bundle")
    reports = family_bundle.get("strategy_reports")
    if type(reports) is not list:
        _fail("Frozen cost-stress strategy_reports must be a native list")
    if [report.get("strategy_id") for report in reports] != list(
        EXPECTED_STRATEGY_IDS
    ):
        _fail("Frozen cost-stress strategy order drifted")

    run_rows: list[dict[str, Any]] = []
    strategy_observations: list[dict[str, Any]] = []
    for report in reports:
        strategy_id = report["strategy_id"]
        runs = report.get("runs")
        if type(runs) is not dict:
            _fail(f"{strategy_id} Frozen cost-stress runs are missing")
        strategy_rows: list[dict[str, Any]] = []
        for index, run_id in enumerate(FROZEN_COST_RUN_IDS):
            run = runs.get(run_id)
            if type(run) is not dict:
                _fail(f"{strategy_id} {run_id} is missing")
            if run.get("evaluation_role") != FROZEN_COST_ROLES[index]:
                _fail(f"{strategy_id} {run_id} outer role drifted")
            result = run.get("result")
            if type(result) is not dict:
                _fail(f"{strategy_id} {run_id} result is missing")
            result_sha256 = canonical_sha256(result)
            if result_sha256 != run.get("result_sha256"):
                _fail(f"{strategy_id} {run_id} result identity drifted")
            manifest = result.get("experiment_manifest")
            if type(manifest) is not dict:
                _fail(f"{strategy_id} {run_id} experiment manifest is missing")
            if manifest.get("evaluation_role") != "FROZEN_TEST":
                _fail(f"{strategy_id} {run_id} manifest role drifted")
            if manifest.get("research_only") is not True:
                _fail(f"{strategy_id} {run_id} research-only flag drifted")
            for denied_field in (
                "live_order_allowed",
                "order_entry_allowed",
                "paper_authorized",
                "result_is_profitability_proof",
            ):
                if manifest.get(denied_field) is not False:
                    _fail(f"{strategy_id} {run_id} {denied_field} escalated")
            fee_model = manifest.get("fee_model")
            slippage_model = manifest.get("slippage_model")
            if type(fee_model) is not dict or type(slippage_model) is not dict:
                _fail(f"{strategy_id} {run_id} cost model is missing")
            if fee_model != {
                "kind": "proportional",
                "rate": FROZEN_FEE_RATES[index],
            }:
                _fail(f"{strategy_id} {run_id} fee model drifted")
            if slippage_model != {
                "kind": "proportional",
                "rate": FROZEN_SLIPPAGE_RATES[index],
            }:
                _fail(f"{strategy_id} {run_id} slippage model drifted")
            for identity_field in (
                "manifest_hash",
                "source_run_hash",
                "result_hash",
            ):
                value = manifest.get(identity_field)
                if type(value) is not str or len(value) != 64:
                    _fail(f"{strategy_id} {run_id} {identity_field} drifted")
            for metric_id in (
                "total_return",
                "sharpe_ratio",
                "max_drawdown",
                "total_fees",
            ):
                value = result.get(metric_id)
                if type(value) not in (int, float) or not math.isfinite(float(value)):
                    _fail(f"{strategy_id} {run_id} {metric_id} is not finite")

            strategy_rows.append(
                {
                    "strategy_id": strategy_id,
                    "run_id": run_id,
                    "cost_role": run["evaluation_role"],
                    "manifest_evaluation_role": manifest["evaluation_role"],
                    "reproducibility_classification": manifest["classification"],
                    "fee_model": copy.deepcopy(fee_model),
                    "slippage_model": copy.deepcopy(slippage_model),
                    "result_sha256": result_sha256,
                    "manifest_sha256": manifest["manifest_hash"],
                    "source_run_sha256": manifest["source_run_hash"],
                    "manifest_result_sha256": manifest["result_hash"],
                    "total_return": result["total_return"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "max_drawdown": result["max_drawdown"],
                    "total_fees": result["total_fees"],
                }
            )

        baseline = strategy_rows[0]
        for row in strategy_rows:
            row["total_return_delta_from_1x"] = round(
                float(row["total_return"]) - float(baseline["total_return"]), 12
            )
            row["sharpe_ratio_delta_from_1x"] = round(
                float(row["sharpe_ratio"]) - float(baseline["sharpe_ratio"]), 12
            )
            row["max_drawdown_delta_from_1x"] = round(
                float(row["max_drawdown"]) - float(baseline["max_drawdown"]), 12
            )
            row["total_fees_delta_from_1x"] = round(
                float(row["total_fees"]) - float(baseline["total_fees"]), 12
            )
        fees = [float(row["total_fees"]) for row in strategy_rows]
        returns = [float(row["total_return"]) for row in strategy_rows]
        drawdowns = [float(row["max_drawdown"]) for row in strategy_rows]
        strategy_observations.append(
            {
                "strategy_id": strategy_id,
                "fees_non_decreasing_observation": fees == sorted(fees),
                "returns_non_increasing_observation": returns
                == sorted(returns, reverse=True),
                "drawdowns_non_decreasing_observation": drawdowns
                == sorted(drawdowns),
            }
        )
        run_rows.extend(strategy_rows)

    return _seal(
        {
            "schema_version": FROZEN_COST_STRESS_PROJECTION_VERSION,
            "source_family_bundle_file_sha256": family_file_sha256,
            "strategy_ids": list(EXPECTED_STRATEGY_IDS),
            "run_ids": list(FROZEN_COST_RUN_IDS),
            "cost_roles": list(FROZEN_COST_ROLES),
            "manifest_evaluation_role": "FROZEN_TEST",
            "expected_fee_rates": list(FROZEN_FEE_RATES),
            "expected_slippage_rates": list(FROZEN_SLIPPAGE_RATES),
            "strategy_count": len(EXPECTED_STRATEGY_IDS),
            "run_count": len(run_rows),
            "run_rows": run_rows,
            "strategy_observations": strategy_observations,
            "observations_are_profitability_proof": False,
        },
        "projection_sha256",
    )


def _frozen_experiment_provenance_projection(
    source_v1: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_json(source_v1, path="$.source_dossier_v1")
    source_receipt = source_v1["receipt"]
    family_bytes = FAMILY_BUNDLE_REFERENCE.read_bytes()
    family_file_sha256 = _sha256_bytes(family_bytes)
    if family_file_sha256 != source_receipt["component_file_sha256"][
        "family_bundle_json"
    ]:
        _fail("Frozen provenance source family bundle identity drifted")
    family_bundle = json.loads(family_bytes.decode("utf-8"))
    _require_exact_json(family_bundle, path="$.family_bundle")
    reports = family_bundle.get("strategy_reports")
    if type(reports) is not list:
        _fail("Frozen provenance strategy_reports must be a native list")
    if [report.get("strategy_id") for report in reports] != list(
        EXPECTED_STRATEGY_IDS
    ):
        _fail("Frozen provenance strategy order drifted")

    rows: list[dict[str, Any]] = []
    blocker_counts: dict[str, int] = {}
    for report in reports:
        strategy_id = report["strategy_id"]
        runs = report.get("runs")
        if type(runs) is not dict:
            _fail(f"{strategy_id} Frozen provenance runs are missing")
        for index, run_id in enumerate(FROZEN_COST_RUN_IDS):
            run = runs.get(run_id)
            if type(run) is not dict:
                _fail(f"{strategy_id} {run_id} provenance run is missing")
            if run.get("evaluation_role") != FROZEN_COST_ROLES[index]:
                _fail(f"{strategy_id} {run_id} provenance role drifted")
            result = run.get("result")
            if type(result) is not dict:
                _fail(f"{strategy_id} {run_id} provenance result is missing")
            result_sha256 = canonical_sha256(result)
            if result_sha256 != run.get("result_sha256"):
                _fail(f"{strategy_id} {run_id} provenance result identity drifted")
            manifest = result.get("experiment_manifest")
            if type(manifest) is not dict:
                _fail(f"{strategy_id} {run_id} provenance manifest is missing")
            missing_fields = [
                field_id
                for field_id in FROZEN_PROVENANCE_FIELD_IDS
                if field_id not in manifest
            ]
            if missing_fields:
                _fail(
                    f"{strategy_id} {run_id} provenance fields are missing: "
                    + ",".join(missing_fields)
                )
            result_payload = copy.deepcopy(result)
            result_payload.pop("experiment_manifest")
            if not verify_reproducible_experiment_manifest(
                manifest, result_payload
            ):
                _fail(f"{strategy_id} {run_id} provenance manifest verification failed")
            if manifest.get("evaluation_role") != "FROZEN_TEST":
                _fail(f"{strategy_id} {run_id} provenance manifest role drifted")
            if manifest.get("classification") != "REPRODUCIBILITY_INCOMPLETE":
                _fail(f"{strategy_id} {run_id} provenance classification drifted")
            if manifest.get("status") != STATUS:
                _fail(f"{strategy_id} {run_id} provenance status drifted")
            if manifest.get("blockers") != ["git_worktree_not_clean"]:
                _fail(f"{strategy_id} {run_id} provenance blockers drifted")
            if manifest.get("git_commit_sha") != "0" * 40:
                _fail(f"{strategy_id} {run_id} provenance Git sentinel drifted")
            if manifest.get("git_worktree_clean") is not False:
                _fail(f"{strategy_id} {run_id} provenance worktree state drifted")
            if manifest.get("dependency_lock_fully_pinned") is not True:
                _fail(f"{strategy_id} {run_id} dependency lock state drifted")
            if manifest.get("evaluation_protocol_verified") is not True:
                _fail(f"{strategy_id} {run_id} evaluation protocol state drifted")
            for blocker in manifest["blockers"]:
                blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "run_id": run_id,
                    "cost_role": run["evaluation_role"],
                    "source_result_sha256": result_sha256,
                    "manifest_sha256": manifest["manifest_hash"],
                    "provenance": {
                        field_id: copy.deepcopy(manifest[field_id])
                        for field_id in FROZEN_PROVENANCE_FIELD_IDS
                    },
                }
            )

    return _seal(
        {
            "schema_version": FROZEN_EXPERIMENT_PROVENANCE_PROJECTION_VERSION,
            "source_family_bundle_file_sha256": family_file_sha256,
            "strategy_ids": list(EXPECTED_STRATEGY_IDS),
            "run_ids": list(FROZEN_COST_RUN_IDS),
            "field_ids": list(FROZEN_PROVENANCE_FIELD_IDS),
            "strategy_count": len(EXPECTED_STRATEGY_IDS),
            "run_count": len(rows),
            "native_manifest_verification_count": len(rows),
            "rows": rows,
            "unique_experiment_id_count": len(
                {row["provenance"]["experiment_id"] for row in rows}
            ),
            "unique_manifest_sha256_count": len(
                {row["manifest_sha256"] for row in rows}
            ),
            "unique_result_sha256_count": len(
                {row["provenance"]["result_hash"] for row in rows}
            ),
            "unique_source_run_sha256_count": len(
                {row["provenance"]["source_run_hash"] for row in rows}
            ),
            "unique_dataset_sha256_count": len(
                {row["provenance"]["dataset_hash"] for row in rows}
            ),
            "unique_config_sha256_count": len(
                {row["provenance"]["config_hash"] for row in rows}
            ),
            "blocker_counts": dict(sorted(blocker_counts.items())),
            "reproducibility_complete": False,
            "provenance_is_profitability_proof": False,
        },
        "projection_sha256",
    )


def _load_bound_component_receipt(
    source_receipt: dict[str, Any],
    *,
    reference_path: Path,
    source_file_key: str,
    label: str,
) -> tuple[dict[str, Any], str]:
    receipt_bytes = reference_path.read_bytes()
    receipt_file_sha256 = _sha256_bytes(receipt_bytes)
    if receipt_file_sha256 != source_receipt["component_file_sha256"].get(
        source_file_key
    ):
        _fail(f"{label} receipt file identity drifted")
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    _require_exact_json(receipt, path=f"$.{label}_receipt")
    receipt_core = copy.deepcopy(receipt)
    claimed_sha256 = receipt_core.pop("receipt_sha256", None)
    if type(claimed_sha256) is not str:
        _fail(f"{label} receipt identity is missing")
    if canonical_sha256(receipt_core) != claimed_sha256:
        _fail(f"{label} receipt self-identity drifted")
    return receipt, receipt_file_sha256


def _evidence_gap_reconciliation(
    source_v1: dict[str, Any],
    control_projection: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_json(source_v1, path="$.source_dossier_v1")
    _require_exact_json(control_projection, path="$.control_projection")
    source_receipt = source_v1["receipt"]
    inherited_gaps = sorted(
        set(source_receipt["gaps"])
        | set(control_projection["source_control_receipt"]["gaps"])
        | _V2_GAPS
    )
    robustness, robustness_file_sha256 = _load_bound_component_receipt(
        source_receipt,
        reference_path=ROBUSTNESS_RECEIPT_REFERENCE,
        source_file_key="robustness_receipt_json",
        label="robustness_v1",
    )
    statistical, statistical_file_sha256 = _load_bound_component_receipt(
        source_receipt,
        reference_path=STATISTICAL_V3_RECEIPT_REFERENCE,
        source_file_key="statistical_v3_receipt_json",
        label="statistical_v3",
    )
    if robustness.get("status") != STATUS or robustness.get("runtime_mutations") is not False:
        _fail("robustness-v1 reconciliation source state drifted")
    if statistical.get("status") != STATUS or statistical.get("runtime_mutations") is not False:
        _fail("statistical-v3 reconciliation source state drifted")

    completed = set(robustness.get("completed_evidence", []))
    statistical_remaining = set(statistical.get("remaining_gaps", []))
    resolution_checks = {
        "BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED": (
            statistical.get("bootstrap_observed_evidence_count") == 6
            and statistical.get("bootstrap_gap_evidence_count") == 0
            and statistical.get("bootstrap_interval_count_per_strategy") == 3
        ),
        "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED": (
            statistical.get("deflated_sharpe_diagnostic_count") == 6
            and "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED"
            not in statistical_remaining
        ),
        "MULTIPLE_TESTING_NOT_EXECUTED": (
            {
                "MULTIPLE_TESTING_LEDGER_COMPLETE",
                "BONFERRONI_AND_BH_DIAGNOSTICS_COMPUTED",
            }
            <= completed
        ),
        "PARAMETER_STABILITY_NOT_EXECUTED": (
            "PARAMETER_STABILITY_EXECUTED" in completed
        ),
        "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED": (
            statistical.get("cscv_pbo_observed_evidence_count", 0)
            + statistical.get("cscv_pbo_gap_evidence_count", 0)
            == len(EXPECTED_STRATEGY_IDS)
            and "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED"
            not in statistical_remaining
        ),
        "WALK_FORWARD_NOT_EXECUTED": "WALK_FORWARD_EXECUTED" in completed,
    }
    if set(resolution_checks) != set(RESOLVED_STALE_GAP_IDS):
        _fail("resolved stale-gap inventory drifted")
    if not all(resolution_checks.values()):
        _fail("one or more stale-gap resolution checks failed")
    if not set(RESOLVED_STALE_GAP_IDS) <= set(inherited_gaps):
        _fail("one or more resolved stale gaps are absent from inherited gaps")
    retained_gaps = sorted(set(inherited_gaps) - set(RESOLVED_STALE_GAP_IDS))
    if not set(REQUIRED_RETAINED_GAP_IDS) <= set(retained_gaps):
        _fail("required unresolved evidence gaps were removed")

    return _seal(
        {
            "schema_version": EVIDENCE_GAP_RECONCILIATION_VERSION,
            "robustness_receipt_file_sha256": robustness_file_sha256,
            "robustness_receipt_sha256": robustness["receipt_sha256"],
            "statistical_v3_receipt_file_sha256": statistical_file_sha256,
            "statistical_v3_receipt_sha256": statistical["receipt_sha256"],
            "component_receipt_identity_verified": True,
            "component_reference_rebuild_performed": False,
            "resolution_checks": resolution_checks,
            "resolved_stale_gap_ids": list(RESOLVED_STALE_GAP_IDS),
            "resolved_stale_gap_count": len(RESOLVED_STALE_GAP_IDS),
            "inherited_gap_ids": inherited_gaps,
            "inherited_gap_count": len(inherited_gaps),
            "retained_gap_ids": retained_gaps,
            "retained_gap_count": len(retained_gaps),
            "required_retained_gap_ids": list(REQUIRED_RETAINED_GAP_IDS),
            "robustness_summary": {
                "schema_version": robustness["schema_version"],
                "maturity": robustness["maturity"],
                "executed_run_count": robustness["robustness_executed_run_count"],
                "total_executed_run_count": robustness["total_executed_run_count"],
                "completed_evidence": copy.deepcopy(
                    robustness["completed_evidence"]
                ),
                "remaining_gaps": copy.deepcopy(robustness["gaps"]),
            },
            "statistical_v3_summary": {
                "schema_version": statistical["schema_version"],
                "maturity": statistical["maturity"],
                "bootstrap_observed_evidence_count": statistical[
                    "bootstrap_observed_evidence_count"
                ],
                "bootstrap_gap_evidence_count": statistical[
                    "bootstrap_gap_evidence_count"
                ],
                "bootstrap_replicate_count": statistical[
                    "bootstrap_replicate_count"
                ],
                "deflated_sharpe_diagnostic_count": statistical[
                    "deflated_sharpe_diagnostic_count"
                ],
                "cscv_pbo_observed_evidence_count": statistical[
                    "cscv_pbo_observed_evidence_count"
                ],
                "cscv_pbo_gap_evidence_count": statistical[
                    "cscv_pbo_gap_evidence_count"
                ],
                "remaining_gaps": copy.deepcopy(statistical["remaining_gaps"]),
            },
            "reconciliation_is_profitability_proof": False,
            "reconciliation_is_formal_inference": False,
            "status": STATUS,
            "runtime_mutations": False,
        },
        "projection_sha256",
    )


def _build_receipt(
    source_v1: dict[str, Any],
    projection: dict[str, Any],
    frozen_distribution_projection: dict[str, Any],
    frozen_cost_stress_projection: dict[str, Any],
    frozen_experiment_provenance_projection: dict[str, Any],
    evidence_gap_reconciliation: dict[str, Any],
) -> dict[str, Any]:
    source_receipt = source_v1["receipt"]
    source_manifest = source_v1["manifest"]
    gaps = list(evidence_gap_reconciliation["retained_gap_ids"])
    payload = {
        "schema_version": RECEIPT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "data_source": "PURE_SYNTHETIC_REFERENCE_ARTIFACTS",
        "source_dossier_v1_receipt_sha256": source_receipt["receipt_sha256"],
        "source_dossier_v1_manifest_sha256": source_manifest["manifest_sha256"],
        "source_dossier_v1_full_report_alignment_proven": source_receipt[
            "full_report_alignment_proven"
        ],
        "benchmark_control_projection": copy.deepcopy(projection),
        "frozen_distribution_metric_projection": copy.deepcopy(
            frozen_distribution_projection
        ),
        "frozen_cost_stress_projection": copy.deepcopy(
            frozen_cost_stress_projection
        ),
        "frozen_experiment_provenance_projection": copy.deepcopy(
            frozen_experiment_provenance_projection
        ),
        "evidence_gap_reconciliation": copy.deepcopy(
            evidence_gap_reconciliation
        ),
        "benchmark_control_ids": list(BENCHMARK_CONTROL_IDS),
        "registered_strategy_ids": list(EXPECTED_STRATEGY_IDS),
        "benchmark_control_to_recorded_v14_identity_alignment_proven": False,
        "full_report_alignment_proven": False,
        "control_rebuild_required_for_semantic_revalidation": True,
        "formal_frozen_blind_test_complete": False,
        "formal_inference_claimed": False,
        "profitability_proven": False,
        "ranking_performed": False,
        "decision_threshold": None,
        "candidate_only": True,
        "current_activation": False,
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": gaps,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "receipt_sha256")


def _table_header(prefix: str) -> list[str]:
    return [
        f"| {prefix} | Cash | Buy and hold | Simple MA | Simple breakout | "
        "No-skill median | Volatility-matched buy and hold |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]


def _render_report(receipt: dict[str, Any]) -> str:
    projection = receipt["benchmark_control_projection"]
    total_rows = _table_header("Strategy Frozen total return")
    delta_rows = _table_header("Strategy minus control")
    for item in projection["strategy_control_comparisons"]:
        controls = item["control_total_returns"]
        deltas = item["strategy_minus_control_return_deltas"]
        strategy = item["strategy_id"]
        total_rows.append(
            f"| {strategy}: {item['strategy_frozen_total_return']} | "
            + " | ".join(controls[key] for key in BENCHMARK_CONTROL_IDS)
            + " |"
        )
        delta_rows.append(
            f"| {strategy} | "
            + " | ".join(deltas[key] for key in BENCHMARK_CONTROL_IDS)
            + " |"
        )
    no_skill = projection["no_skill_distribution"]
    summary = no_skill["summary"]
    lines = [
        "# Deterministic Synthetic Strategy Research Dossier v2 Candidate",
        "",
        "All observations are from fixed synthetic fixtures. They are not profitability evidence, formal inference, ranking permission, or trading authority.",
        "",
        "## SOURCE",
        f"- Source dossier v1: `{receipt['source_dossier_v1_receipt_sha256']}`",
        f"- Benchmark-control bundle: `{projection['source_control_bundle_sha256']}`",
        f"- Benchmark-control plan: `{projection['source_control_plan_sha256']}`",
        f"- Shared baseline bundle: `{projection['source_baseline_bundle_sha256']}`",
        "- Source runs reused: 32; additional synthetic control runs: 18.",
        "- Candidate only: true; current activation: false.",
        "",
        "### Synthetic control total-return observations",
        *total_rows,
        "",
        "### Synthetic strategy-minus-control return deltas",
        *delta_rows,
        "",
        "### Hash no-skill synthetic distribution",
        f"- Paths: {no_skill['path_count']}",
        f"- Minimum: {summary['minimum']}",
        f"- Q25 Type-7: {summary['q25_type7']}",
        f"- Median Type-7: {summary['median_type7']}",
        f"- Q75 Type-7: {summary['q75_type7']}",
        f"- Maximum: {summary['maximum']}",
        "",
        "## GAP",
        *[f"- `{gap}`" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- Status: `{receipt['status']}`",
        f"- Maturity: `{receipt['maturity']}`",
        "- The volatility-matched result is an ex-post synthetic projection, not an executable baseline.",
        "- Exact control identity alignment to the recorded v14 report is not proven without a full rebuild.",
        "- Dossier v1 remains current and byte-identical.",
        "",
        "## PERMISSION",
        "- Profitability proven: `false`",
        "- Formal inference authorized: `false`",
        "- Ranking authorized: `false`",
        "- Paper authorized: `false`",
        "- Live authorized: `false`",
        "- Order entry authorized: `false`",
    ]
    markdown = "\n".join(lines) + "\n"
    for forbidden in ("READY", "Profitability proven: `true`"):
        if forbidden in markdown:
            _fail("dossier v2 renderer contains an authority-escalating token")
    return (
        markdown.rstrip()
        + "\n\n"
        + _render_frozen_distribution_metrics(
            receipt["frozen_distribution_metric_projection"]
        ).rstrip()
        + "\n\n"
        + _render_frozen_cost_stress(
            receipt["frozen_cost_stress_projection"]
        ).rstrip()
        + "\n\n"
        + _render_frozen_experiment_provenance(
            receipt["frozen_experiment_provenance_projection"]
        ).rstrip()
        + "\n\n"
        + _render_evidence_gap_reconciliation(
            receipt["evidence_gap_reconciliation"]
        )
    )


def _display_metric(value: Any) -> str:
    if value is None:
        return "undefined"
    if type(value) is float:
        return format(value, ".12g")
    if type(value) in (int, str):
        return str(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _render_frozen_distribution_metrics(projection: dict[str, Any]) -> str:
    lines = [
        "## Frozen distribution metrics and Sharpe",
        "",
        "This is a non-current synthetic projection of existing Frozen evidence. Undefined statistics remain undefined; no value is zero-filled.",
        "",
        "| Strategy | Total return | CAGR | Annualized volatility | Sharpe | Sortino | Calmar | Max drawdown | Drawdown duration |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in projection["strategy_metrics"]:
        metrics = item["metrics"]
        lines.append(
            "| "
            + " | ".join(
                _display_metric(value)
                for value in (
                    item["strategy_id"],
                    item["total_return"],
                    metrics["cagr_observation"],
                    metrics["annualized_volatility"],
                    item["sharpe_ratio"],
                    metrics["sortino_ratio"],
                    metrics["calmar_ratio"],
                    metrics["max_drawdown"],
                    metrics["max_drawdown_duration_periods"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| Strategy | Profit factor | Win rate | Payoff ratio | Trade expectancy | Turnover | Fee load | Market exposure |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in projection["strategy_metrics"]:
        metrics = item["metrics"]
        lines.append(
            "| "
            + " | ".join(
                _display_metric(value)
                for value in (
                    item["strategy_id"],
                    metrics["profit_factor"],
                    metrics["win_rate"],
                    metrics["payoff_ratio"],
                    metrics["trade_expectancy"],
                    metrics["turnover_ratio"],
                    metrics["fee_load_ratio"],
                    metrics["market_exposure_ratio"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| Strategy | VaR 95 | CVaR 95 | VaR 99 | CVaR 99 | Periods | Closed trades | Evidence state |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in projection["strategy_metrics"]:
        metrics = item["metrics"]
        lines.append(
            "| "
            + " | ".join(
                _display_metric(value)
                for value in (
                    item["strategy_id"],
                    metrics["tail_var_95"],
                    metrics["tail_cvar_95"],
                    metrics["tail_var_99"],
                    metrics["tail_cvar_99"],
                    metrics["period_return_count"],
                    metrics["closed_trade_count"],
                    item["distribution_status"],
                )
            )
            + " |"
        )
    lines.extend(["", "### Distribution buckets and concentration", ""])
    for item in projection["strategy_metrics"]:
        compact = lambda value: json.dumps(
            value, sort_keys=True, separators=(",", ":")
        )
        lines.extend(
            [
                f"- `{item['strategy_id']}` monthly returns: `{compact(item['monthly_returns'])}`",
                f"- `{item['strategy_id']}` monthly summary: `{compact(item['monthly_summary'])}`",
                f"- `{item['strategy_id']}` yearly returns: `{compact(item['yearly_returns'])}`",
                f"- `{item['strategy_id']}` yearly summary: `{compact(item['yearly_summary'])}`",
                f"- `{item['strategy_id']}` concentration: `{compact(item['concentration'])}`",
                f"- `{item['strategy_id']}` gaps: `{compact(item['distribution_gaps'])}`",
            ]
        )
    return "\n".join(lines) + "\n"


def _render_frozen_cost_stress(projection: dict[str, Any]) -> str:
    lines = [
        "## Frozen cost-stress observations",
        "",
        "These are non-current synthetic observations from existing Frozen runs. Cost-role labels and embedded FROZEN_TEST experiment roles are preserved separately.",
        "",
        "| Strategy | Cost role | Manifest role | Fee rate | Slippage rate | Total return | Delta vs 1x | Sharpe | Delta vs 1x | Max drawdown | Delta vs 1x | Total fees | Delta vs 1x |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in projection["run_rows"]:
        lines.append(
            "| "
            + " | ".join(
                _display_metric(value)
                for value in (
                    row["strategy_id"],
                    row["cost_role"],
                    row["manifest_evaluation_role"],
                    row["fee_model"]["rate"],
                    row["slippage_model"]["rate"],
                    row["total_return"],
                    row["total_return_delta_from_1x"],
                    row["sharpe_ratio"],
                    row["sharpe_ratio_delta_from_1x"],
                    row["max_drawdown"],
                    row["max_drawdown_delta_from_1x"],
                    row["total_fees"],
                    row["total_fees_delta_from_1x"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| Strategy | Fees non-decreasing | Returns non-increasing | Drawdowns non-decreasing |",
            "| --- | --- | --- | --- |",
        ]
    )
    for observation in projection["strategy_observations"]:
        lines.append(
            "| "
            + " | ".join(
                _display_metric(value)
                for value in (
                    observation["strategy_id"],
                    observation["fees_non_decreasing_observation"],
                    observation["returns_non_increasing_observation"],
                    observation["drawdowns_non_decreasing_observation"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "These observations do not prove profitability, formal inference, ranking authority, paper authority, live authority, or order-entry authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_frozen_experiment_provenance(projection: dict[str, Any]) -> str:
    lines = [
        "## Frozen experiment provenance",
        "",
        f"- Native manifest verification: `{projection['native_manifest_verification_count']}/{projection['run_count']}`",
        f"- Reproducibility complete: `{_display_metric(projection['reproducibility_complete'])}`",
        f"- Blocker counts: `{json.dumps(projection['blocker_counts'], sort_keys=True, separators=(',', ':'))}`",
        "",
        "Each entry below is projected from an identity-bound manifest after native verification against the result payload with the embedded manifest removed.",
    ]
    for row in projection["rows"]:
        provenance = row["provenance"]
        lines.extend(
            [
                "",
                f"### `{row['strategy_id']}` / `{row['run_id']}`",
                f"- experiment_id: `{provenance['experiment_id']}`",
                f"- strategy_name: `{provenance['strategy_name']}`; strategy_version: `{provenance['strategy_version']}`",
                f"- git_commit_sha: `{provenance['git_commit_sha']}`; git_worktree_clean: `{_display_metric(provenance['git_worktree_clean'])}`",
                f"- config_hash: `{provenance['config_hash']}`; dataset_hash: `{provenance['dataset_hash']}`",
                f"- dependency_lock_name: `{provenance['dependency_lock_name']}`; dependency_lock_hash: `{provenance['dependency_lock_hash']}`; dependency_lock_fully_pinned: `{_display_metric(provenance['dependency_lock_fully_pinned'])}`",
                f"- evaluation_protocol_hash: `{provenance['evaluation_protocol_hash']}`; evaluation_protocol_verified: `{_display_metric(provenance['evaluation_protocol_verified'])}`",
                f"- window: `{provenance['start_time']}` to `{provenance['end_time']}`; symbol/timeframe: `{provenance['symbol']}` / `{provenance['timeframe']}`",
                f"- random_seed: `{provenance['random_seed']}`; runtime_version: `{provenance['runtime_version']}`",
                f"- fee_model: `{json.dumps(provenance['fee_model'], sort_keys=True, separators=(',', ':'))}`; slippage_model: `{json.dumps(provenance['slippage_model'], sort_keys=True, separators=(',', ':'))}`",
                f"- result_hash: `{provenance['result_hash']}`; source_run_hash: `{provenance['source_run_hash']}`; manifest_hash: `{row['manifest_sha256']}`",
                f"- classification/status: `{provenance['classification']}` / `{provenance['status']}`; blockers: `{json.dumps(provenance['blockers'], separators=(',', ':'))}`",
            ]
        )
    lines.extend(
        [
            "",
            "This provenance projection does not prove reproducibility, profitability, formal inference, ranking authority, paper authority, live authority, or order-entry authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_evidence_gap_reconciliation(projection: dict[str, Any]) -> str:
    robustness = projection["robustness_summary"]
    statistical = projection["statistical_v3_summary"]
    lines = [
        "## Evidence gap reconciliation",
        "",
        f"- Inherited GAP count: `{projection['inherited_gap_count']}`",
        f"- Resolved stale GAP count: `{projection['resolved_stale_gap_count']}`",
        f"- Retained GAP count: `{projection['retained_gap_count']}`",
        f"- Robustness receipt: `{projection['robustness_receipt_sha256']}`",
        f"- Statistical-v3 receipt: `{projection['statistical_v3_receipt_sha256']}`",
        "",
        "### Resolved stale GAP identifiers",
        *[f"- `{gap}`" for gap in projection["resolved_stale_gap_ids"]],
        "",
        "### Existing robustness evidence",
        f"- Robustness runs: `{robustness['executed_run_count']}`; total source plus robustness runs: `{robustness['total_executed_run_count']}`",
        *[f"- `{item}`" for item in robustness["completed_evidence"]],
        "",
        "### Existing statistical-v3 evidence",
        f"- Bootstrap observed/gap evidence: `{statistical['bootstrap_observed_evidence_count']}/{statistical['bootstrap_gap_evidence_count']}`; replicates: `{statistical['bootstrap_replicate_count']}`",
        f"- Deflated Sharpe diagnostics: `{statistical['deflated_sharpe_diagnostic_count']}`",
        f"- CSCV PBO observed/gap evidence: `{statistical['cscv_pbo_observed_evidence_count']}/{statistical['cscv_pbo_gap_evidence_count']}`",
        "",
        "Only stale NOT_EXECUTED/NOT_ESTIMATED labels with exact bound replacement evidence are removed. Partial PBO identification, overlapping-window dependence, real-data, formal-blind-test and authority gaps remain.",
        "This reconciliation does not prove profitability or authorize formal inference, ranking, paper, live, or order entry.",
    ]
    return "\n".join(lines) + "\n"


def build_deterministic_strategy_research_dossier_material_v2(
    benchmark_controls_bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(benchmark_controls_bundle) is not dict:
        raise TypeError("benchmark_controls_bundle must be an exact native dict")
    _require_exact_json(benchmark_controls_bundle)
    verify_deterministic_strategy_research_dossier_reference_v1()
    source_v1 = build_deterministic_strategy_research_dossier_material_v1()
    projection = _control_projection(benchmark_controls_bundle)
    frozen_distribution_projection = _frozen_distribution_metric_projection(source_v1)
    frozen_cost_stress_projection = _frozen_cost_stress_projection(source_v1)
    frozen_experiment_provenance_projection = (
        _frozen_experiment_provenance_projection(source_v1)
    )
    evidence_gap_reconciliation = _evidence_gap_reconciliation(
        source_v1, projection
    )
    receipt = _build_receipt(
        source_v1,
        projection,
        frozen_distribution_projection,
        frozen_cost_stress_projection,
        frozen_experiment_provenance_projection,
        evidence_gap_reconciliation,
    )
    receipt_bytes = _json_bytes(receipt)
    report_bytes = _render_report(receipt).encode("utf-8")
    source_files = {
        path: _sha256_bytes((REPOSITORY_ROOT / path).read_bytes())
        for path in SOURCE_RELATIVE_PATHS
    }
    source_v1_files = {
        name: _sha256_bytes((SOURCE_DOSSIER_REFERENCE_ROOT / name).read_bytes())
        for name in SOURCE_DOSSIER_REFERENCE_FILE_NAMES
    }
    manifest_core = {
        "contract_version": MANIFEST_VERSION,
        "receipt_schema_version": receipt["schema_version"],
        "receipt_sha256": receipt["receipt_sha256"],
        "source_dossier_v1_receipt_sha256": receipt[
            "source_dossier_v1_receipt_sha256"
        ],
        "benchmark_control_bundle_sha256": projection[
            "source_control_bundle_sha256"
        ],
        "benchmark_control_projection_sha256": projection["projection_sha256"],
        "frozen_distribution_metric_projection_sha256": (
            frozen_distribution_projection["projection_sha256"]
        ),
        "frozen_cost_stress_projection_sha256": frozen_cost_stress_projection[
            "projection_sha256"
        ],
        "frozen_experiment_provenance_projection_sha256": (
            frozen_experiment_provenance_projection["projection_sha256"]
        ),
        "evidence_gap_reconciliation_sha256": evidence_gap_reconciliation[
            "projection_sha256"
        ],
        "source_files": source_files,
        "source_file_count": len(source_files),
        "source_dossier_v1_reference_files": source_v1_files,
        "source_dossier_v1_reference_file_count": len(source_v1_files),
        "dependency_lock": {
            "name": LOCK_PATH.name,
            "sha256": _sha256_bytes(LOCK_PATH.read_bytes()),
            "fully_pinned": True,
        },
        "expected_receipt_file_sha256": _sha256_bytes(receipt_bytes),
        "expected_report_file_sha256": _sha256_bytes(report_bytes),
        "control_rebuild_required_for_semantic_revalidation": True,
        "benchmark_control_to_recorded_v14_identity_alignment_proven": False,
        "candidate_only": True,
        "current_activation": False,
        "status": STATUS,
        "maturity": MATURITY,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    manifest = _seal(manifest_core, "manifest_sha256")
    return {
        "receipt": receipt,
        "manifest": manifest,
        "files": {
            "expected_receipt.json": receipt_bytes.decode("utf-8"),
            "expected_report.md": report_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(manifest).decode("utf-8"),
        },
    }


def verify_deterministic_strategy_research_dossier_material_v2(
    material: dict[str, Any],
    benchmark_controls_bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(material) is not dict:
        raise TypeError("material must be an exact native dict")
    _require_exact_json(material)
    if set(material) != {"receipt", "manifest", "files"}:
        _fail("dossier v2 material shape mismatch")
    expected = build_deterministic_strategy_research_dossier_material_v2(
        benchmark_controls_bundle
    )
    if material != expected:
        _fail("dossier v2 material does not match deterministic sources")
    return {
        "status": "PASS",
        "contract_version": CONTRACT_VERSION,
        "receipt_sha256": material["receipt"]["receipt_sha256"],
        "manifest_sha256": material["manifest"]["manifest_sha256"],
        "candidate_only": True,
        "current_activation": False,
        "control_rebuild_required_for_semantic_revalidation": True,
        "runtime_mutations": False,
        "authority": copy.deepcopy(_AUTHORITY),
    }


def verify_deterministic_strategy_research_dossier_reference_v2(
    benchmark_controls_bundle: dict[str, Any],
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = REFERENCE_ROOT if reference_root is None else Path(reference_root)
    expected = build_deterministic_strategy_research_dossier_material_v2(
        benchmark_controls_bundle
    )
    verify_deterministic_strategy_research_dossier_material_v2(
        expected, benchmark_controls_bundle
    )
    if not root.is_dir():
        _fail("dossier v2 reference root missing")
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    checks = {
        "reference_file_set": actual_names == set(REFERENCE_FILE_NAMES),
        "lf_only": all(
            b"\r" not in (root / name).read_bytes()
            for name in REFERENCE_FILE_NAMES
            if (root / name).is_file()
        ),
        "expected_bytes_exact": all(
            (root / name).is_file()
            and (root / name).read_bytes()
            == expected["files"][name].encode("utf-8")
            for name in REFERENCE_FILE_NAMES
        ),
    }
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        _fail(f"dossier v2 reference verification failed:{failed}")
    return {
        "status": "PASS",
        "contract_version": VERIFIER_VERSION,
        "receipt_sha256": expected["receipt"]["receipt_sha256"],
        "manifest_sha256": expected["manifest"]["manifest_sha256"],
        "checks": checks,
        "candidate_only": True,
        "current_activation": False,
        "runtime_mutations": False,
        "authority": copy.deepcopy(_AUTHORITY),
    }


__all__ = [
    "BENCHMARK_CONTROL_IDS",
    "CONTRACT_VERSION",
    "EXPECTED_CONTROL_RUN_IDS",
    "EXPECTED_STRATEGY_IDS",
    "REFERENCE_FILE_NAMES",
    "REFERENCE_ROOT",
    "build_deterministic_strategy_research_dossier_material_v2",
    "verify_deterministic_strategy_research_dossier_material_v2",
    "verify_deterministic_strategy_research_dossier_reference_v2",
]
