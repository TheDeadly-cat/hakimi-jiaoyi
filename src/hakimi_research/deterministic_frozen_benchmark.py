from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from hakimi_research.source_layout import REPOSITORY_ROOT

from hakimi_research.frozen_evaluation import (  # noqa: E402
    AUTHORITY_LOCK,
    STANDARD_REPORT_COVERAGE_GAPS,
    build_frozen_evaluation_protocol,
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_protocol,
    verify_frozen_evaluation_report,
)
from hakimi_research.config import BotConfig  # noqa: E402


DETERMINISTIC_FROZEN_BENCHMARK_VERSION = "deterministic-frozen-benchmark-v14"
DETERMINISTIC_FROZEN_BENCHMARK_VERIFIER_VERSION = (
    "deterministic-frozen-benchmark-verifier-v14"
)
FIXTURE_MANIFEST_VERSION = "deterministic-frozen-benchmark-manifest-v14"
SAMPLE_ID = "synthetic-frozen-oos-cost-stress-v2"
MATURITY = "SYNTHETIC_FIXTURE_ONLY"
REPO_ROOT = REPOSITORY_ROOT
REFERENCE_ROOT = REPO_ROOT / "examples" / "deterministic_frozen_benchmark_v2"
LOCK_PATH = REPO_ROOT / "requirements.research.lock"
REQUIRED_DATA_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
REFERENCE_FILE_NAMES = (
    "config.json",
    "dataset.csv",
    "dataset_governance.json",
    "experiment_context.json",
    "expected_report.json",
    "expected_report.md",
    "fixture_manifest.json",
)
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_frozen_benchmark.py",
    "src/hakimi_research/source_layout.py",
    "src/hakimi_research/frozen_evaluation.py",
    "src/hakimi_research/frozen_experiment_provenance.py",
    "src/hakimi_research/experiment_provenance_consumer_adapter_v1.py",
    "src/hakimi_research/experiment_provenance_binding_v1.py",
    "src/hakimi_research/reporting.py",
    "src/hakimi_research/dataset_governance.py",
    "src/hakimi_research/dataset_calendar_conformance.py",
    "src/hakimi_research/bootstrap_confidence_evidence.py",
    "src/hakimi_research/frozen_statistical_correction.py",
    "src/hakimi_research/trial_return_matrix.py",
    "src/hakimi_research/deflated_sharpe_diagnostic.py",
    "src/hakimi_research/cscv_pbo_diagnostic.py",
    "src/hakimi_research/cscv_pbo_tie_bounds.py",
    "src/hakimi_research/frozen_execution_adversity.py",
    "src/hakimi_research/backtest.py",
    "src/hakimi_research/benchmarks.py",
    "src/hakimi_research/volatility_comparison.py",
    "src/hakimi_research/volatility_target_baseline.py",
    "src/hakimi_research/walk_forward.py",
    "src/hakimi_research/parameter_stability.py",
    "src/hakimi_research/multiple_testing.py",
    "src/hakimi_research/frozen_market_regime.py",
    "src/hakimi_research/distribution_evidence.py",
    "src/hakimi_research/frozen_distribution.py",
    "src/hakimi_research/config.py",
    "src/hakimi_research/execution.py",
    "src/hakimi_research/experiment_manifest.py",
    "src/hakimi_research/indicators.py",
    "src/hakimi_research/models.py",
    "src/hakimi_research/risk.py",
    "src/hakimi_research/strategies/base.py",
    "src/hakimi_research/strategies/templates.py",
)
_CONTEXT_FIELDS = {
    "git_commit_sha",
    "git_worktree_clean",
    "dependency_lock_hash",
    "dependency_lock_fully_pinned",
    "dependency_lock_name",
    "runtime_version",
}
_CLAIMS_LOCK = {
    "real_dataset": False,
    "formal_blind_test": False,
    "natural_forward": False,
    "parameter_selection": False,
    "ranking": False,
    "profitability": False,
    "paper": False,
    "live": False,
    "order": False,
}


class DeterministicFrozenBenchmarkError(RuntimeError):
    pass


def _fail(code: str) -> None:
    raise DeterministicFrozenBenchmarkError(code)


def _require_native_json(value: Any, *, path: str = "root") -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"deterministic_benchmark_nonfinite:{path}")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_native_json(item, path=f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(f"deterministic_benchmark_key_type:{path}")
            _require_native_json(item, path=f"{path}.{key}")
        return
    _fail(f"deterministic_benchmark_native_json_required:{path}")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        _fail(f"deterministic_benchmark_file_missing:{path.name}")
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    _require_native_json(value)
    rendered = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )
    return (rendered + "\n").encode("utf-8")


def _resolve_reference_root(reference_root: str | None) -> Path:
    if reference_root is None:
        return REFERENCE_ROOT
    if type(reference_root) is not str or not reference_root:
        _fail("deterministic_benchmark_reference_root_exact_str_required")
    return Path(reference_root).resolve()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DeterministicFrozenBenchmarkError(
            f"deterministic_benchmark_{label}_read_failed:{type(exc).__name__}"
        ) from exc
    _require_native_json(value, path=label)
    if type(value) is not dict:
        _fail(f"deterministic_benchmark_{label}_exact_dict_required")
    return value


def _load_frame(root: Path) -> pd.DataFrame:
    path = root / "dataset.csv"
    raw = path.read_bytes()
    if b"\r" in raw:
        _fail("deterministic_benchmark_dataset_lf_required")
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        raise DeterministicFrozenBenchmarkError(
            f"deterministic_benchmark_dataset_read_failed:{type(exc).__name__}"
        ) from exc
    if list(frame.columns) != list(REQUIRED_DATA_COLUMNS):
        _fail("deterministic_benchmark_dataset_columns_invalid")
    if len(frame) != 128:
        _fail("deterministic_benchmark_dataset_row_count_invalid")
    try:
        timestamps = pd.to_datetime(frame.pop("timestamp"), utc=True, errors="raise")
        for column in REQUIRED_DATA_COLUMNS[1:]:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
    except Exception as exc:
        raise DeterministicFrozenBenchmarkError(
            f"deterministic_benchmark_dataset_value_invalid:{type(exc).__name__}"
        ) from exc
    frame.index = pd.DatetimeIndex(timestamps)
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        _fail("deterministic_benchmark_dataset_timestamp_order_invalid")
    return frame


def _load_config(root: Path) -> BotConfig:
    path = root / "config.json"
    raw = _read_json(path, label="config")
    try:
        config = BotConfig.from_file(path)
    except Exception as exc:
        raise DeterministicFrozenBenchmarkError(
            f"deterministic_benchmark_config_invalid:{type(exc).__name__}"
        ) from exc
    checks = (
        raw.get("mode") == "backtest",
        raw.get("market") == "synthetic",
        raw.get("symbol") == "SYNTH-001",
        raw.get("timeframe") == "1d",
        raw.get("data", {}).get("provider") == "csv",
        raw.get("data", {}).get("use_cache") is False,
        raw.get("data", {}).get("history_limit") == 128,
        raw.get("execution", {}).get("broker") == "research_simulator",
        raw.get("execution", {}).get("exchange") == "disabled",
        raw.get("execution", {}).get("live_trading_enabled") is False,
    )
    if not all(checks):
        _fail("deterministic_benchmark_config_research_lock_invalid")
    return config


def _load_dataset_governance(root: Path) -> dict[str, Any]:
    governance = _read_json(
        root / "dataset_governance.json",
        label="dataset_governance",
    )
    source = governance.get("source")
    population = governance.get("population")
    if (
        type(source) is not dict
        or source.get("source_manifest_sha256") != _sha256_file(root / "dataset.csv")
        or type(population) is not dict
        or population.get("universe_snapshot_sha256")
        != _sha256_bytes(
            json.dumps(
                ["SYNTH-001"],
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    ):
        _fail("deterministic_benchmark_dataset_governance_binding_invalid")
    return governance


def _load_context(root: Path) -> dict[str, Any]:
    context = _read_json(root / "experiment_context.json", label="experiment_context")
    if set(context) != _CONTEXT_FIELDS:
        _fail("deterministic_benchmark_context_fields_invalid")
    if (
        type(context["git_commit_sha"]) is not str
        or context["git_commit_sha"] != "0" * 40
        or context["git_worktree_clean"] is not False
        or type(context["dependency_lock_hash"]) is not str
        or len(context["dependency_lock_hash"]) != 64
        or context["dependency_lock_fully_pinned"] is not True
        or context["dependency_lock_name"] != "requirements.research.lock"
        or context["runtime_version"] != "python-3.14"
    ):
        _fail("deterministic_benchmark_context_identity_invalid")
    if context["dependency_lock_hash"] != _sha256_file(LOCK_PATH):
        _fail("deterministic_benchmark_dependency_lock_hash_mismatch")
    return context


def build_deterministic_frozen_benchmark_reference_material(
    *,
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _resolve_reference_root(reference_root)
    frame = _load_frame(root)
    config = _load_config(root)
    dataset_governance = _load_dataset_governance(root)
    context = _load_context(root)
    protocol = build_frozen_evaluation_protocol(
        frame,
        config,
        dataset_governance=dataset_governance,
        experiment_context=context,
        train_rows=40,
        purge_rows=4,
        validation_rows=40,
        embargo_rows=4,
        frozen_test_rows=40,
        random_seed=17,
    )
    verify_frozen_evaluation_protocol(
        protocol,
        frame,
        config,
        experiment_context=context,
    )
    report = build_frozen_evaluation_report(
        protocol,
        frame,
        config,
        experiment_context=context,
    )
    verify_frozen_evaluation_report(
        report,
        protocol,
        frame,
        config,
        experiment_context=context,
    )
    report_json = _canonical_json_bytes(report, pretty=True)
    report_markdown = render_frozen_evaluation_markdown(
        report,
        protocol,
        frame,
        config,
        experiment_context=context,
    ).encode("utf-8")
    source_hashes = {
        relative: _sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_RELATIVE_PATHS
    }
    input_hashes = {
        name: _sha256_file(root / name)
        for name in (
            "config.json",
            "dataset.csv",
            "dataset_governance.json",
            "experiment_context.json",
        )
    }
    manifest_core: dict[str, Any] = {
        "contract_version": FIXTURE_MANIFEST_VERSION,
        "sample_id": SAMPLE_ID,
        "maturity": MATURITY,
        "quality_status": report["quality_gate"]["status"],
        "git_provenance": "UNBOUND_SOURCE_HASH_ENVELOPE",
        "runtime_contract": "python-3.14",
        "dependency_lock": {
            "name": "requirements.research.lock",
            "sha256": _sha256_file(LOCK_PATH),
            "fully_pinned": True,
        },
        "source_files": source_hashes,
        "input_files": input_hashes,
        "data_rows": len(frame),
        "dataset_hash": protocol["dataset"]["dataset_hash"],
        "dataset_governance_schema": protocol["dataset"]["governance"]["schema_version"],
        "dataset_governance_hash": protocol["dataset"]["governance"]["governance_hash"],
        "dataset_calendar_conformance_schema": protocol["dataset"]["calendar_conformance"]["schema_version"],
        "dataset_calendar_conformance_hash": protocol["dataset"]["calendar_conformance"]["conformance_hash"],
        "partition_rows": {
            item["name"]: item["row_count"]
            for item in protocol["partition_plan"]["windows"]
        },
        "cost_scenarios": [
            {
                "scenario_id": item["scenario_id"],
                "multiplier": item["multiplier"],
            }
            for item in protocol["cost_scenarios"]
        ],
        "execution_adversity_policy_hash": protocol["execution_adversity"][
            "policy_hash"
        ],
        "execution_adversity_scenarios": [
            item["scenario_id"]
            for item in protocol["execution_adversity"]["scenarios"]
        ],
        "execution_adversity_run_count": len(report["execution_adversity_runs"]),
        "execution_adversity_observed_run_count": sum(
            record["observation_status"] == "OBSERVED"
            for record in report["execution_adversity_runs"]
        ),
        "liquidity_capacity_run_count": len(report["liquidity_capacity_runs"]),
        "liquidity_capacity_partial_fill_count": sum(
            record["liquidity_capacity_summary"]["partial_fill_count"]
            for record in report["liquidity_capacity_runs"]
        ),
        "liquidity_rejection_evidence_count": len(
            report["liquidity_rejection_evidence"]
        ),
        "liquidity_rejection_observed_count": sum(
            record["decision"]["status"] == "REJECTED"
            for record in report["liquidity_rejection_evidence"]
        ),
        "volatility_matched_comparison_record_count": len(
            report["volatility_matched_comparisons"]
        ),
        "volatility_matched_comparison_gap_count": sum(
            record["comparison_status"] == "GAP"
            for record in report["volatility_matched_comparisons"]
        ),
        "bootstrap_confidence_record_count": len(
            report["bootstrap_confidence_evidence"]
        ),
        "bootstrap_confidence_observed_count": sum(
            record["evidence"]["evidence_state"] == "OBSERVED"
            for record in report["bootstrap_confidence_evidence"]
        ),
        "bootstrap_confidence_gap_count": sum(
            record["evidence"]["evidence_state"] == "GAP"
            for record in report["bootstrap_confidence_evidence"]
        ),
        "bootstrap_confidence_minimum_observation_count": report[
            "bootstrap_confidence_evidence"
        ][0]["evidence"]["policy"]["minimum_observation_count"],
        "bootstrap_confidence_paired_observation_counts": [
            record["evidence"]["sample_summary"]["paired_observation_count"]
            for record in report["bootstrap_confidence_evidence"]
        ],
        "return_concentration_record_count": len(
            report["tail_distribution_analysis"]
        ),
        "return_concentration_fixed_window_gap_count": sum(
            record["distribution_evidence"]["concentration"][
                "best_fixed_21_period_window"
            ]["state"]
            == "GAP"
            for record in report["tail_distribution_analysis"]
        ),
        "return_concentration_positive_period_hhi_observed_count": sum(
            record["distribution_evidence"]["concentration"][
                "positive_period_return_hhi"
            ]
            is not None
            for record in report["tail_distribution_analysis"]
        ),
        "statistical_correction_record_count": len(
            report["statistical_correction_evidence"]
        ),
        "statistical_correction_trial_counts": [
            record["trial_matrix"]["trial_count"]
            for record in report["statistical_correction_evidence"]
        ],
        "statistical_correction_observation_counts": [
            record["trial_matrix"]["observation_count"]
            for record in report["statistical_correction_evidence"]
        ],
        "statistical_correction_dsr_gap_count": sum(
            record["deflated_sharpe"]["state"] == "GAP"
            for record in report["statistical_correction_evidence"]
        ),
        "statistical_correction_pbo_gap_count": sum(
            record["cscv_pbo"]["state"] == "GAP"
            for record in report["statistical_correction_evidence"]
        ),
        "statistical_correction_additional_backtest_run_count": sum(
            record["additional_backtest_run_count"]
            for record in report["statistical_correction_evidence"]
        ),
        "benchmarks": [item["benchmark_id"] for item in protocol["benchmarks"]],
        "comparison_methods": [
            item["comparison_id"] for item in protocol["comparison_methods"]
        ],
        "execution_baseline_methods": [
            item["benchmark_id"] for item in protocol["execution_baseline_methods"]
        ],
        "walk_forward_method": protocol["walk_forward"]["method"]["method_version"],
        "parameter_stability_method": protocol["parameter_stability"]["method"]["method_version"],
        "multiple_testing_policy": protocol["multiple_testing_policy"]["policy_version"],
        "market_regime_policy": protocol["market_regime_policy"]["policy_version"],
        "tail_distribution_policy": protocol["tail_distribution_policy"]["policy_version"],
        "protocol_id": protocol["protocol_id"],
        "protocol_hash": protocol["protocol_hash"],
        "report_id": report["report_id"],
        "report_hash": report["report_hash"],
        "expected_report_sha256": _sha256_bytes(report_json),
        "expected_markdown_sha256": _sha256_bytes(report_markdown),
        "coverage_gaps": list(STANDARD_REPORT_COVERAGE_GAPS),
        "quality_blockers": list(report["quality_gate"]["blockers"]),
        "authority": dict(AUTHORITY_LOCK),
        "claims": dict(_CLAIMS_LOCK),
    }
    manifest = dict(manifest_core)
    manifest["manifest_sha256"] = _sha256_bytes(_canonical_json_bytes(manifest_core))
    return {
        "protocol": protocol,
        "report": report,
        "manifest": manifest,
        "files": {
            "expected_report.json": report_json.decode("utf-8"),
            "expected_report.md": report_markdown.decode("utf-8"),
            "fixture_manifest.json": _canonical_json_bytes(
                manifest,
                pretty=True,
            ).decode("utf-8"),
        },
    }


def verify_deterministic_frozen_benchmark_reference(
    *,
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _resolve_reference_root(reference_root)
    material = build_deterministic_frozen_benchmark_reference_material(
        reference_root=str(root),
    )
    report = material["report"]
    manifest = material["manifest"]
    expected_report_bytes = (root / "expected_report.json").read_bytes()
    expected_markdown_bytes = (root / "expected_report.md").read_bytes()
    expected_manifest_bytes = (root / "fixture_manifest.json").read_bytes()
    expected_report = _read_json(root / "expected_report.json", label="expected_report")
    expected_manifest = _read_json(
        root / "fixture_manifest.json",
        label="fixture_manifest",
    )
    manifest_core = {
        key: value
        for key, value in expected_manifest.items()
        if key != "manifest_sha256"
    }
    checks = {
        "reference_file_set": all((root / name).is_file() for name in REFERENCE_FILE_NAMES),
        "lf_only": all(b"\r" not in (root / name).read_bytes() for name in REFERENCE_FILE_NAMES),
        "manifest_exact": expected_manifest == manifest,
        "manifest_bytes_canonical": expected_manifest_bytes
        == material["files"]["fixture_manifest.json"].encode("utf-8"),
        "manifest_self_hash": expected_manifest.get("manifest_sha256")
        == _sha256_bytes(_canonical_json_bytes(manifest_core)),
        "report_exact": expected_report == report,
        "report_bytes_canonical": expected_report_bytes
        == material["files"]["expected_report.json"].encode("utf-8"),
        "markdown_exact": expected_markdown_bytes
        == material["files"]["expected_report.md"].encode("utf-8"),
        "quality_blocked": report["quality_gate"]["status"] == "BLOCK",
        "dataset_governance_bound": report["dataset_governance_hash"]
        == manifest["dataset_governance_hash"]
        == material["protocol"]["dataset"]["governance"]["governance_hash"],
        "dataset_calendar_conformance_bound": report[
            "dataset_calendar_conformance_hash"
        ]
        == manifest["dataset_calendar_conformance_hash"]
        == material["protocol"]["dataset"]["calendar_conformance"]["conformance_hash"]
        and material["protocol"]["dataset"]["calendar_conformance"]["status"]
        == "PASS",
        "execution_adversity_bound": manifest["execution_adversity_policy_hash"]
        == material["protocol"]["execution_adversity"]["policy_hash"]
        and manifest["execution_adversity_run_count"]
        == len(report["execution_adversity_runs"])
        == 6
        and manifest["execution_adversity_observed_run_count"] == 0
        and report["quality_gate"]["execution_adversity_matrix_complete"] is True
        and report["quality_gate"]["execution_adversity_observation_complete"]
        is False
        and "EXECUTION_ADVERSITY_TARGET_SOURCE_ACTIVITY_INSUFFICIENT"
        in report["quality_gate"]["blockers"],
        "liquidity_capacity_bound": manifest["liquidity_capacity_run_count"]
        == len(report["liquidity_capacity_runs"])
        == 2
        and manifest["liquidity_capacity_partial_fill_count"] >= 2
        and report["quality_gate"]["liquidity_capacity_matrix_complete"] is True
        and report["quality_gate"]["liquidity_capacity_partial_fill_observed"]
        is True,
        "liquidity_rejection_bound": manifest[
            "liquidity_rejection_evidence_count"
        ]
        == len(report["liquidity_rejection_evidence"])
        == 2
        and manifest["liquidity_rejection_observed_count"] == 2
        and report["quality_gate"][
            "liquidity_rejection_probe_matrix_complete"
        ]
        is True
        and report["quality_gate"]["liquidity_rejection_observed"] is True
        and all(
            record["portfolio_mutated"] is False
            and all(value is False for value in record["authority"].values())
            for record in report["liquidity_rejection_evidence"]
        ),
        "volatility_matched_comparison_bound": manifest[
            "volatility_matched_comparison_record_count"
        ]
        == len(report["volatility_matched_comparisons"])
        == 6
        and manifest["volatility_matched_comparison_gap_count"] == 6
        and report["quality_gate"][
            "volatility_matched_comparison_matrix_complete"
        ]
        is True
        and report["quality_gate"][
            "volatility_matched_comparison_observation_complete"
        ]
        is False
        and "VOLATILITY_MATCHED_COMPARISON_OBSERVATION_INCOMPLETE"
        in report["quality_gate"]["blockers"],
        "bootstrap_confidence_bound": manifest["bootstrap_confidence_record_count"]
        == len(report["bootstrap_confidence_evidence"])
        == 2
        and manifest["bootstrap_confidence_observed_count"] == 0
        and manifest["bootstrap_confidence_gap_count"] == 2
        and manifest["bootstrap_confidence_minimum_observation_count"] == 60
        and manifest["bootstrap_confidence_paired_observation_counts"] == [9, 9]
        and report["quality_gate"]["bootstrap_confidence_matrix_complete"] is True
        and report["quality_gate"]["bootstrap_confidence_observation_complete"]
        is False
        and "BOOTSTRAP_CONFIDENCE_INSUFFICIENT_PAIRED_OBSERVATIONS"
        in report["quality_gate"]["blockers"],
        "return_concentration_bound": manifest["return_concentration_record_count"]
        == len(report["tail_distribution_analysis"])
        == 6
        and manifest["return_concentration_fixed_window_gap_count"] == 6
        and report["quality_gate"][
            "return_contribution_concentration_matrix_complete"
        ]
        is True,
        "statistical_corrections_bound": manifest[
            "statistical_correction_record_count"
        ]
        == len(report["statistical_correction_evidence"])
        == 2
        and manifest["statistical_correction_trial_counts"] == [21, 21]
        and manifest["statistical_correction_observation_counts"] == [9, 9]
        and manifest["statistical_correction_dsr_gap_count"] == 2
        and manifest["statistical_correction_pbo_gap_count"] == 2
        and manifest["statistical_correction_additional_backtest_run_count"] == 0
        and report["quality_gate"]["statistical_correction_matrix_complete"] is True
        and report["quality_gate"]["statistical_correction_estimable"] is False
        and "FROZEN_STATISTICAL_CORRECTIONS_UNESTIMABLE"
        in report["quality_gate"]["blockers"],
        "not_formal_blind": report["quality_gate"]["frozen_test_is_blind"] is False,
        "not_natural_forward": report["quality_gate"]["natural_forward_evidence"] is False,
        "authority_locked": report["authority"] == AUTHORITY_LOCK
        and all(value is False for value in report["authority"].values()),
        "claims_locked": expected_manifest.get("claims") == _CLAIMS_LOCK
        and all(value is False for value in expected_manifest.get("claims", {}).values()),
    }
    if not all(checks.values()):
        failed = ",".join(name for name, passed in checks.items() if not passed)
        _fail(f"deterministic_benchmark_reference_verification_failed:{failed}")
    return {
        "contract_version": DETERMINISTIC_FROZEN_BENCHMARK_VERIFIER_VERSION,
        "status": "PASS",
        "sample_id": SAMPLE_ID,
        "maturity": MATURITY,
        "quality_status": "BLOCK",
        "data_rows": manifest["data_rows"],
        "protocol_id": manifest["protocol_id"],
        "protocol_hash": manifest["protocol_hash"],
        "report_id": manifest["report_id"],
        "report_hash": manifest["report_hash"],
        "manifest_sha256": manifest["manifest_sha256"],
        "dataset_governance_hash": manifest["dataset_governance_hash"],
        "dataset_calendar_conformance_hash": manifest[
            "dataset_calendar_conformance_hash"
        ],
        "execution_adversity_run_count": manifest[
            "execution_adversity_run_count"
        ],
        "execution_adversity_observed_run_count": manifest[
            "execution_adversity_observed_run_count"
        ],
        "liquidity_capacity_run_count": manifest[
            "liquidity_capacity_run_count"
        ],
        "liquidity_capacity_partial_fill_count": manifest[
            "liquidity_capacity_partial_fill_count"
        ],
        "liquidity_rejection_evidence_count": manifest[
            "liquidity_rejection_evidence_count"
        ],
        "liquidity_rejection_observed_count": manifest[
            "liquidity_rejection_observed_count"
        ],
        "volatility_matched_comparison_record_count": manifest[
            "volatility_matched_comparison_record_count"
        ],
        "volatility_matched_comparison_gap_count": manifest[
            "volatility_matched_comparison_gap_count"
        ],
        "bootstrap_confidence_record_count": manifest[
            "bootstrap_confidence_record_count"
        ],
        "bootstrap_confidence_observed_count": manifest[
            "bootstrap_confidence_observed_count"
        ],
        "bootstrap_confidence_gap_count": manifest[
            "bootstrap_confidence_gap_count"
        ],
        "bootstrap_confidence_minimum_observation_count": manifest[
            "bootstrap_confidence_minimum_observation_count"
        ],
        "bootstrap_confidence_paired_observation_counts": manifest[
            "bootstrap_confidence_paired_observation_counts"
        ],
        "return_concentration_record_count": manifest[
            "return_concentration_record_count"
        ],
        "return_concentration_fixed_window_gap_count": manifest[
            "return_concentration_fixed_window_gap_count"
        ],
        "return_concentration_positive_period_hhi_observed_count": manifest[
            "return_concentration_positive_period_hhi_observed_count"
        ],
        "statistical_correction_record_count": manifest[
            "statistical_correction_record_count"
        ],
        "statistical_correction_trial_counts": manifest[
            "statistical_correction_trial_counts"
        ],
        "statistical_correction_observation_counts": manifest[
            "statistical_correction_observation_counts"
        ],
        "statistical_correction_dsr_gap_count": manifest[
            "statistical_correction_dsr_gap_count"
        ],
        "statistical_correction_pbo_gap_count": manifest[
            "statistical_correction_pbo_gap_count"
        ],
        "statistical_correction_additional_backtest_run_count": manifest[
            "statistical_correction_additional_backtest_run_count"
        ],
        "checks": checks,
        "authority": dict(AUTHORITY_LOCK),
        "claims": dict(_CLAIMS_LOCK),
    }
