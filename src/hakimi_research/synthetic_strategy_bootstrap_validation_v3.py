from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from hakimi_research.bootstrap_confidence_evidence_v2 import (
    build_bootstrap_confidence_evidence_v2,
    paired_moving_block_bootstrap_policy_v2,
    verify_bootstrap_confidence_evidence_v2,
)
from hakimi_research.synthetic_strategy_bootstrap_validation import (
    MATURITY,
    OBSERVATION_CLASS,
    STATUS,
    SyntheticStrategyBootstrapValidationError,
    _authority,
    _canonical_sha256,
    _fail,
    _find_strategy_report,
    _render_synthetic_strategy_bootstrap_validation_markdown,
    _verify_baseline,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v2,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-plan-v3"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-bundle-v3"
RECORD_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-record-v3"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-bootstrap-validation-receipt-v3"
_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "STATISTICAL_REFERENCE_V3_CONSUMER_NOT_ACTIVATED",
    "SYNTHETIC_FIXED_169_OBSERVATION_BOOTSTRAP_ONLY",
]


def _require_exact_json(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "dict keys must be exact strings")
            _require_exact_json(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, f"{path}[{index}]")
        return
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float and math.isfinite(value):
        return
    _fail(path, "must contain exact finite native JSON values")


def plan_synthetic_strategy_bootstrap_validation_v3() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_report_bundle_v1()
    strategy_ids = source_plan["registered_strategy_ids"]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "accepted_source_baseline_schema_versions": [
            "synthetic-strategy-report-bundle-v1",
            "synthetic-strategy-report-bundle-v2",
        ],
        "source_required_run_count": source_plan["planned_run_count"],
        "planned_run_count": 0,
        "executed_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "registered_strategy_ids": strategy_ids,
        "policy": paired_moving_block_bootstrap_policy_v2(),
        "seed_identity_scope": "STATISTICAL_SAMPLE_ONLY",
        "source_provenance_binding_required": True,
        "source_provenance_affects_seed": False,
        "expected_paired_observation_count_per_strategy": 169,
        "expected_replicate_count": 1000,
        "expected_interval_count_per_strategy": 3,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(_GAPS),
        "authority": _authority(),
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def _source_verification_v3(
    baseline_bundle: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(baseline_bundle) is not dict:
        _fail("baseline_bundle", "must be an exact dict")
    _require_exact_json(baseline_bundle, "baseline_bundle")
    source_schema = baseline_bundle.get("schema_version")
    if source_schema == "synthetic-strategy-report-bundle-v1":
        receipt = _verify_baseline(
            baseline_bundle,
            verify_synthetic_strategy_report_bundle_v1,
        )
        binding = {
            "source_schema_version": source_schema,
            "source_bundle_sha256": baseline_bundle["bundle_sha256"],
            "source_verifier_contract": (
                "synthetic-strategy-report-bundle-verifier-v1"
            ),
            "source_verifier_receipt_sha256": _canonical_sha256(receipt),
            "source_reproducibility_context_sha256": None,
            "source_dependency_bound_run_count": None,
            "source_git_bound_run_count": None,
            "source_provenance_bound": True,
            "canonical_reproducibility_context_bound": False,
        }
        return receipt, binding
    if source_schema == "synthetic-strategy-report-bundle-v2":
        receipt = _verify_baseline(
            baseline_bundle,
            verify_synthetic_strategy_report_bundle_v2,
        )
        binding = {
            "source_schema_version": source_schema,
            "source_bundle_sha256": baseline_bundle["bundle_sha256"],
            "source_verifier_contract": (
                "synthetic-strategy-report-bundle-verifier-v2"
            ),
            "source_verifier_receipt_sha256": _canonical_sha256(receipt),
            "source_reproducibility_context_sha256": _canonical_sha256(
                baseline_bundle["reproducibility_context"]
            ),
            "source_dependency_bound_run_count": receipt[
                "dependency_bound_run_count"
            ],
            "source_git_bound_run_count": receipt["git_bound_run_count"],
            "source_provenance_bound": True,
            "canonical_reproducibility_context_bound": True,
        }
        return receipt, binding
    _fail(
        "baseline_bundle.schema_version",
        "must be an accepted exact report bundle schema",
    )


def _build_record_v3(
    baseline_bundle: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    report = _find_strategy_report(baseline_bundle, strategy_id)
    run = report["runs"]["frozen_1x"]
    benchmark = baseline_bundle["benchmarks"]["buy_and_hold"]
    evidence = build_bootstrap_confidence_evidence_v2(
        run["result"]["equity_curve"],
        benchmark["result"]["equity_curve"],
        strategy_id=strategy_id,
        dataset_sha256=run["dataset_sha256"],
        strategy_result_sha256=run["result_sha256"],
        benchmark_result_sha256=benchmark["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    receipt = verify_bootstrap_confidence_evidence_v2(
        evidence,
        run["result"]["equity_curve"],
        benchmark["result"]["equity_curve"],
        strategy_id=strategy_id,
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
        "statistical_sample_sha256": evidence["statistical_sample_sha256"],
        "bootstrap_evidence": evidence,
        "bootstrap_receipt": receipt,
        "evidence_state": receipt["state"],
        "status": STATUS,
        "maturity": MATURITY,
        "observation_class": OBSERVATION_CLASS,
        "source_provenance_bound": True,
        "source_provenance_affects_seed": False,
        "authority": _authority(),
    }
    record["record_sha256"] = _canonical_sha256(record)
    return record


def _compose_synthetic_strategy_bootstrap_validation_v3(
    baseline_bundle: dict[str, Any],
) -> dict[str, Any]:
    _, source_binding = _source_verification_v3(baseline_bundle)
    plan = plan_synthetic_strategy_bootstrap_validation_v3()
    records = [
        _build_record_v3(baseline_bundle, strategy_id)
        for strategy_id in plan["registered_strategy_ids"]
    ]
    paired_counts = {
        record["bootstrap_receipt"]["paired_observation_count"]
        for record in records
    }
    replicate_counts = {
        record["bootstrap_receipt"]["replicate_count"] for record in records
    }
    interval_counts = {
        record["bootstrap_receipt"]["interval_count"] for record in records
    }
    sample_hashes = {
        record["statistical_sample_sha256"] for record in records
    }
    if (
        paired_counts != {169}
        or replicate_counts != {1000}
        or interval_counts != {3}
        or len(sample_hashes) != 6
    ):
        _fail("strategy_records", "v3 Bootstrap coverage or sample identity drifted")
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": "OBSERVED",
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_provenance_binding": source_binding,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "executed_analysis_count": 6,
        "observed_evidence_count": 6,
        "gap_evidence_count": 0,
        "paired_observation_count_per_strategy": 169,
        "replicate_count": 1000,
        "interval_count_per_strategy": 3,
        "seed_identity_scope": "STATISTICAL_SAMPLE_ONLY",
        "source_provenance_affects_seed": False,
        "strategy_records": records,
        "runtime_mutations": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(_GAPS),
        "authority": _authority(),
    }
    bundle = deepcopy(payload)
    bundle["bundle_sha256"] = _canonical_sha256(payload)
    return bundle


def build_synthetic_strategy_bootstrap_validation_v3(
    baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBootstrapValidationError(
            "v3 analysis requires exact execute=True; inspect the v3 plan first"
        )
    bundle = _compose_synthetic_strategy_bootstrap_validation_v3(baseline_bundle)
    verify_synthetic_strategy_bootstrap_validation_v3(bundle, baseline_bundle)
    return bundle


def verify_synthetic_strategy_bootstrap_validation_v3(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    _require_exact_json(bundle, "bundle")
    expected = _compose_synthetic_strategy_bootstrap_validation_v3(baseline_bundle)
    if bundle != expected:
        _fail("bundle", "must match deterministic v3 source and sample evidence")
    source_binding = bundle["source_provenance_binding"]
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": "OBSERVED",
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": bundle["plan"]["plan_sha256"],
        "source_schema_version": source_binding["source_schema_version"],
        "source_bundle_sha256": source_binding["source_bundle_sha256"],
        "strategy_count": 6,
        "observed_evidence_count": 6,
        "gap_evidence_count": 0,
        "planned_run_count": 0,
        "executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "paired_observation_count_per_strategy": 169,
        "replicate_count": 1000,
        "interval_count_per_strategy": 3,
        "seed_identity_scope": "STATISTICAL_SAMPLE_ONLY",
        "source_provenance_bound": True,
        "source_provenance_affects_seed": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "gaps": list(_GAPS),
        "authority": _authority(),
    }


def replay_synthetic_strategy_bootstrap_validation_v3(
    bundle: dict[str, Any], baseline_bundle: dict[str, Any]
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_bootstrap_validation_v3(
        bundle, baseline_bundle
    )
    replayed = build_synthetic_strategy_bootstrap_validation_v3(
        baseline_bundle, execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic v3 analysis mismatch")
    result = dict(receipt)
    result["replay_status"] = "EXACT_MATCH"
    result["replayed_analysis_count"] = 6
    return result


def render_synthetic_strategy_bootstrap_validation_markdown_v3(
    bundle: dict[str, Any],
    baseline_bundle: dict[str, Any],
) -> str:
    return _render_synthetic_strategy_bootstrap_validation_markdown(
        bundle,
        baseline_bundle,
        verifier=verify_synthetic_strategy_bootstrap_validation_v3,
        title="# Synthetic Strategy Bootstrap Confidence Validation v3",
    )


def build_default_synthetic_strategy_bootstrap_validation_v3(
    *,
    execute: bool = False,
    reproducibility_context: dict[str, Any],
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBootstrapValidationError(
            "execution requires exact execute=True; inspect the v3 source plan first"
        )
    baseline = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=reproducibility_context,
    )
    return build_synthetic_strategy_bootstrap_validation_v3(
        baseline,
        execute=True,
    )
