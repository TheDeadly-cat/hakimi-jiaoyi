from __future__ import annotations

import copy
from typing import Any, Callable

from hakimi_research.synthetic_strategy_baseline_lineage_proof import (
    _default_reference_context,
)
from hakimi_research.synthetic_strategy_bootstrap_validation import (
    build_synthetic_strategy_bootstrap_validation_v1,
    build_synthetic_strategy_bootstrap_validation_v2,
    verify_synthetic_strategy_bootstrap_validation_v1,
    verify_synthetic_strategy_bootstrap_validation_v2,
)
from hakimi_research.synthetic_strategy_bootstrap_validation_v3 import (
    build_synthetic_strategy_bootstrap_validation_v3,
    verify_synthetic_strategy_bootstrap_validation_v3,
)
from hakimi_research.synthetic_strategy_cscv_pbo_tie_bounds import (
    build_synthetic_strategy_cscv_pbo_tie_bounds_v1,
    build_synthetic_strategy_cscv_pbo_tie_bounds_v2,
)
from hakimi_research.synthetic_strategy_cscv_pbo_validation import (
    build_synthetic_strategy_cscv_pbo_validation_v1,
    build_synthetic_strategy_cscv_pbo_validation_v2,
)
from hakimi_research.synthetic_strategy_deflated_sharpe_validation import (
    build_synthetic_strategy_deflated_sharpe_validation_v1,
    build_synthetic_strategy_deflated_sharpe_validation_v2,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
)
from hakimi_research.synthetic_strategy_robustness_lineage_proof import (
    build_synthetic_strategy_robustness_lineage_proof_v1,
    verify_synthetic_strategy_robustness_lineage_proof_v1,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v1,
    build_synthetic_strategy_trial_return_matrix_v2,
    verify_synthetic_strategy_trial_return_matrix_v1,
    verify_synthetic_strategy_trial_return_matrix_v2,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-statistical-applicability-proof-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-statistical-applicability-proof-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-statistical-applicability-proof-receipt-v1"
MATURITY = "SYNTHETIC_PARTIAL_STATISTICAL_APPLICABILITY_ONLY"
STATUS = "BLOCK"
STATE = "OBSERVED_WITH_GAPS"
SOURCE_EXECUTED_RUN_COUNT = 358
STATISTICAL_ADDITIONAL_BACKTEST_RUN_COUNT = 0
MATRIX_CANDIDATE_COUNT = 18
BOOTSTRAP_STRATEGY_COUNT = 6
BOOTSTRAP_INTERVAL_VALUE_COUNT = 54
BOOTSTRAP_DIFFERING_INTERVAL_VALUE_COUNT = 53
BOOTSTRAP_EQUAL_INTERVAL_VALUE_COUNT = 1
BOOTSTRAP_DIFFERING_SEED_COUNT = 6
CANONICAL_RETAINED_SPLIT_BOUND_COUNT = 420
OUTCOME_PLAN_SCHEMA_VERSION = (
    "synthetic-strategy-statistical-applicability-proof-plan-v2"
)
OUTCOME_BUNDLE_SCHEMA_VERSION = (
    "synthetic-strategy-statistical-applicability-proof-bundle-v2"
)
OUTCOME_RECEIPT_SCHEMA_VERSION = (
    "synthetic-strategy-statistical-applicability-proof-receipt-v2"
)
OUTCOME_MATURITY = "SYNTHETIC_FULL_STATISTICAL_NUMERICAL_APPLICABILITY_ONLY"
OUTCOME_BOOTSTRAP_DIFFERING_INTERVAL_VALUE_COUNT = 0
OUTCOME_BOOTSTRAP_EQUAL_INTERVAL_VALUE_COUNT = 54
OUTCOME_BOOTSTRAP_DIFFERING_SEED_COUNT = 0

_DROP_EXACT = {
    "plan",
    "source_robustness_bundle",
    "source_matrix_bundle",
    "source_cscv_bundle",
    "experiment_manifest",
    "candidate_source_run_sha256s",
    "candidate_row_sha256s",
    "retained_split_bound_count",
    "reproducibility_context",
    "source_run_reproducibility_ledger_sha256",
    "source_dependency_bound_run_count",
    "source_git_bound_run_count",
    "matrix_dependency_bound_run_count",
    "source_reproducibility_context_required",
    "source_matrix_schema_version",
    "source_cscv_schema_version",
    "source_robustness_schema_version",
    "source_baseline_schema_version",
    "formal_inference_claimed",
    "decision_threshold",
    "schema_version",
}
_GAPS = [
    "BOOTSTRAP_SOURCE_BOUND_SEED_NUMERICAL_MISMATCH",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "FULL_STATISTICAL_REFERENCE_APPLICABILITY_NOT_PROVEN",
    "OVERLAPPING_RUN_ACCOUNTING_NOT_ADDITIVE",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "STATISTICAL_LEDGER_ALIGNMENT_NOT_PROVEN",
]
_OUTCOME_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "OVERLAPPING_RUN_ACCOUNTING_NOT_ADDITIVE",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "STATISTICAL_LEDGER_ALIGNMENT_NOT_PROVEN",
    "STATISTICAL_REFERENCE_V3_CONSUMER_NOT_ACTIVATED",
]
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyStatisticalApplicabilityProofError(ValueError):
    pass


def _outcome_projection(value: Any) -> Any:
    value_type = type(value)
    if value_type is dict:
        return {
            key: _outcome_projection(item)
            for key, item in value.items()
            if key not in _DROP_EXACT
            and not (key.endswith("_sha256") and key != "dataset_sha256")
        }
    if value_type is list:
        return [_outcome_projection(item) for item in value]
    if value is None or value_type in (str, int, float, bool):
        return copy.deepcopy(value)
    raise TypeError("statistical projection requires exact native JSON values")


def _bootstrap_interval_values(bundle: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for record in bundle["strategy_records"]:
        for interval in record["bootstrap_evidence"]["intervals"]:
            for field in ("lower_bound", "median", "upper_bound"):
                value = interval[field]
                if type(value) is not str:
                    raise SyntheticStrategyStatisticalApplicabilityProofError(
                        "Bootstrap interval values must be exact strings"
                    )
                values.append(value)
    return values


def _bootstrap_seed_values(bundle: dict[str, Any]) -> list[str]:
    values = [
        record["bootstrap_evidence"]["seed_material_sha256"]
        for record in bundle["strategy_records"]
    ]
    if any(type(value) is not str or len(value) != 64 for value in values):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "Bootstrap seed material must contain exact SHA-256 strings"
        )
    return values


def _build_analysis_stages(
    legacy_matrix: dict[str, Any],
    canonical_matrix: dict[str, Any],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    legacy_dsr = build_synthetic_strategy_deflated_sharpe_validation_v1(
        legacy_matrix,
        execute=True,
    )
    canonical_dsr = build_synthetic_strategy_deflated_sharpe_validation_v2(
        canonical_matrix,
        execute=True,
    )
    legacy_pbo = build_synthetic_strategy_cscv_pbo_validation_v1(
        legacy_matrix,
        execute=True,
    )
    canonical_pbo = build_synthetic_strategy_cscv_pbo_validation_v2(
        canonical_matrix,
        execute=True,
    )
    legacy_tie = build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
        legacy_pbo,
        execute=True,
    )
    canonical_tie = build_synthetic_strategy_cscv_pbo_tie_bounds_v2(
        canonical_pbo,
        execute=True,
    )
    return {
        "dsr": (legacy_dsr, canonical_dsr),
        "pbo": (legacy_pbo, canonical_pbo),
        "tie": (legacy_tie, canonical_tie),
    }


def plan_synthetic_strategy_statistical_applicability_proof_v1() -> (
    dict[str, Any]
):
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "comparison_stage_ids": ["matrix", "dsr", "pbo", "tie", "bootstrap"],
        "projection_removed_key_names": sorted(_DROP_EXACT),
        "matrix_outcome_applicability_proven": False,
        "dsr_numerical_applicability_proven": False,
        "pbo_numerical_applicability_proven": False,
        "tie_bounds_numerical_applicability_proven": False,
        "bootstrap_numerical_applicability_proven": False,
        "full_statistical_reference_applicability_proven": False,
        "canonical_reproducibility_ledger_verified": False,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "state": "PLANNED",
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    result = copy.deepcopy(payload)
    result["plan_sha256"] = canonical_sha256(payload)
    return result


def _verify_sources(
    legacy_matrix: dict[str, Any],
    canonical_matrix: dict[str, Any],
    legacy_bootstrap: dict[str, Any],
    canonical_bootstrap: dict[str, Any],
) -> dict[str, Any]:
    if any(
        type(value) is not dict
        for value in (
            legacy_matrix,
            canonical_matrix,
            legacy_bootstrap,
            canonical_bootstrap,
        )
    ):
        raise TypeError("all statistical applicability sources must be exact dicts")
    legacy_matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v1(
        legacy_matrix
    )
    canonical_matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v2(
        canonical_matrix
    )
    if (
        legacy_matrix_receipt.get("state") != "OBSERVED"
        or canonical_matrix_receipt.get("state") != "OBSERVED"
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "matrix sources did not retain observed state"
        )
    legacy_robustness = legacy_matrix["source_robustness_bundle"]
    canonical_robustness = canonical_matrix["source_robustness_bundle"]
    robustness_proof = build_synthetic_strategy_robustness_lineage_proof_v1(
        legacy_robustness,
        canonical_robustness,
        execute=True,
    )
    robustness_receipt = verify_synthetic_strategy_robustness_lineage_proof_v1(
        robustness_proof
    )
    if robustness_receipt["robustness_outcome_alignment_proven"] is not True:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "robustness applicability prerequisite failed"
        )
    legacy_baseline = legacy_robustness["source_bundle"]
    canonical_baseline = canonical_robustness["source_bundle"]
    verify_synthetic_strategy_bootstrap_validation_v1(
        legacy_bootstrap,
        legacy_baseline,
    )
    verify_synthetic_strategy_bootstrap_validation_v2(
        canonical_bootstrap,
        canonical_baseline,
    )
    return robustness_proof


def _stage_binding(
    legacy: dict[str, Any], canonical: dict[str, Any]
) -> dict[str, Any]:
    legacy_projection = _outcome_projection(legacy)
    canonical_projection = _outcome_projection(canonical)
    if legacy_projection != canonical_projection:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "statistical stage outcome projection mismatch"
        )
    return {
        "legacy_bundle_sha256": legacy["bundle_sha256"],
        "canonical_bundle_sha256": canonical["bundle_sha256"],
        "outcome_projection_sha256": canonical_sha256(legacy_projection),
    }


def _compose_bundle(
    legacy_matrix: dict[str, Any],
    canonical_matrix: dict[str, Any],
    legacy_bootstrap: dict[str, Any],
    canonical_bootstrap: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    robustness_proof = _verify_sources(
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
    )
    stages = _build_analysis_stages(legacy_matrix, canonical_matrix)
    stage_bindings = {
        "matrix": _stage_binding(legacy_matrix, canonical_matrix),
        **{
            name: _stage_binding(legacy, canonical)
            for name, (legacy, canonical) in stages.items()
        },
    }
    canonical_tie = stages["tie"][1]
    if canonical_tie["retained_split_bound_count"] != (
        CANONICAL_RETAINED_SPLIT_BOUND_COUNT
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "canonical tie retained-split count drifted"
        )
    legacy_interval_values = _bootstrap_interval_values(legacy_bootstrap)
    canonical_interval_values = _bootstrap_interval_values(canonical_bootstrap)
    if len(legacy_interval_values) != BOOTSTRAP_INTERVAL_VALUE_COUNT:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "legacy Bootstrap interval count drifted"
        )
    if len(canonical_interval_values) != BOOTSTRAP_INTERVAL_VALUE_COUNT:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "canonical Bootstrap interval count drifted"
        )
    differing_interval_count = sum(
        legacy != canonical
        for legacy, canonical in zip(
            legacy_interval_values,
            canonical_interval_values,
        )
    )
    equal_interval_count = BOOTSTRAP_INTERVAL_VALUE_COUNT - differing_interval_count
    if (
        differing_interval_count != BOOTSTRAP_DIFFERING_INTERVAL_VALUE_COUNT
        or equal_interval_count != BOOTSTRAP_EQUAL_INTERVAL_VALUE_COUNT
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "Bootstrap numerical mismatch coverage drifted"
        )
    legacy_seeds = _bootstrap_seed_values(legacy_bootstrap)
    canonical_seeds = _bootstrap_seed_values(canonical_bootstrap)
    differing_seed_count = sum(
        legacy != canonical
        for legacy, canonical in zip(legacy_seeds, canonical_seeds)
    )
    if differing_seed_count != BOOTSTRAP_DIFFERING_SEED_COUNT:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "Bootstrap seed mismatch coverage drifted"
        )
    bootstrap_binding = {
        "legacy_bundle_sha256": legacy_bootstrap["bundle_sha256"],
        "canonical_bundle_sha256": canonical_bootstrap["bundle_sha256"],
        "legacy_interval_values_sha256": canonical_sha256(
            legacy_interval_values
        ),
        "canonical_interval_values_sha256": canonical_sha256(
            canonical_interval_values
        ),
        "legacy_seed_material_sha256": canonical_sha256(legacy_seeds),
        "canonical_seed_material_sha256": canonical_sha256(canonical_seeds),
    }
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "plan": copy.deepcopy(plan),
        "legacy_matrix_bundle": copy.deepcopy(legacy_matrix),
        "canonical_matrix_bundle": copy.deepcopy(canonical_matrix),
        "legacy_bootstrap_bundle": copy.deepcopy(legacy_bootstrap),
        "canonical_bootstrap_bundle": copy.deepcopy(canonical_bootstrap),
        "bindings": {
            "robustness_lineage_proof_bundle_sha256": robustness_proof[
                "bundle_sha256"
            ],
            "canonical_run_reproducibility_ledger_sha256": canonical_matrix[
                "source_run_reproducibility_ledger_sha256"
            ],
            "stages": stage_bindings,
            "bootstrap": bootstrap_binding,
        },
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "canonical_retained_split_bound_count": (
            CANONICAL_RETAINED_SPLIT_BOUND_COUNT
        ),
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "bootstrap_differing_interval_value_count": differing_interval_count,
        "bootstrap_equal_interval_value_count": equal_interval_count,
        "bootstrap_differing_seed_count": differing_seed_count,
        "matrix_outcome_applicability_proven": True,
        "dsr_numerical_applicability_proven": True,
        "pbo_numerical_applicability_proven": True,
        "tie_bounds_numerical_applicability_proven": True,
        "bootstrap_numerical_applicability_proven": False,
        "full_statistical_reference_applicability_proven": False,
        "canonical_reproducibility_ledger_verified": True,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "state": STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    result = copy.deepcopy(payload)
    result["bundle_sha256"] = canonical_sha256(payload)
    return result


def build_synthetic_strategy_statistical_applicability_proof_v1(
    legacy_matrix: dict[str, Any] | None = None,
    canonical_matrix: dict[str, Any] | None = None,
    legacy_bootstrap: dict[str, Any] | None = None,
    canonical_bootstrap: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    sources = (
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
    )
    if execute is False:
        if any(source is not None for source in sources):
            raise ValueError("plan-only mode does not accept prebuilt sources")
        return plan_synthetic_strategy_statistical_applicability_proof_v1()
    if any(source is None for source in sources):
        raise ValueError("execute=True requires all four prebuilt sources")
    return _compose_bundle(
        legacy_matrix,  # type: ignore[arg-type]
        canonical_matrix,  # type: ignore[arg-type]
        legacy_bootstrap,  # type: ignore[arg-type]
        canonical_bootstrap,  # type: ignore[arg-type]
        plan_synthetic_strategy_statistical_applicability_proof_v1(),
    )


def build_default_synthetic_strategy_statistical_applicability_proof_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        return plan_synthetic_strategy_statistical_applicability_proof_v1()
    legacy_source = build_synthetic_strategy_report_bundle_v1(execute=True)
    canonical_source = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_default_reference_context(),
    )
    legacy_matrix = build_synthetic_strategy_trial_return_matrix_v1(
        legacy_source,
        execute=True,
    )
    canonical_matrix = build_synthetic_strategy_trial_return_matrix_v2(
        canonical_source,
        execute=True,
    )
    legacy_bootstrap = build_synthetic_strategy_bootstrap_validation_v1(
        legacy_source,
        execute=True,
    )
    canonical_bootstrap = build_synthetic_strategy_bootstrap_validation_v2(
        canonical_source,
        execute=True,
    )
    return build_synthetic_strategy_statistical_applicability_proof_v1(
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
        execute=True,
    )


def _verify_declared_boundary(bundle: dict[str, Any]) -> None:
    expected = {
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "canonical_retained_split_bound_count": CANONICAL_RETAINED_SPLIT_BOUND_COUNT,
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "bootstrap_differing_interval_value_count": BOOTSTRAP_DIFFERING_INTERVAL_VALUE_COUNT,
        "bootstrap_equal_interval_value_count": BOOTSTRAP_EQUAL_INTERVAL_VALUE_COUNT,
        "bootstrap_differing_seed_count": BOOTSTRAP_DIFFERING_SEED_COUNT,
        "matrix_outcome_applicability_proven": True,
        "dsr_numerical_applicability_proven": True,
        "pbo_numerical_applicability_proven": True,
        "tie_bounds_numerical_applicability_proven": True,
        "bootstrap_numerical_applicability_proven": False,
        "full_statistical_reference_applicability_proven": False,
        "canonical_reproducibility_ledger_verified": True,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "state": STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _GAPS,
        "authority": _AUTHORITY,
        "runtime_mutations": False,
    }
    for field, value in expected.items():
        if bundle.get(field) != value:
            raise SyntheticStrategyStatisticalApplicabilityProofError(
                f"declared applicability boundary drifted: {field}"
            )


def verify_synthetic_strategy_statistical_applicability_proof_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise TypeError("bundle must be an exact native dict")
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "unexpected statistical applicability proof schema"
        )
    plan = bundle.get("plan")
    if plan != plan_synthetic_strategy_statistical_applicability_proof_v1():
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "statistical applicability proof plan mismatch"
        )
    _verify_declared_boundary(bundle)
    sources = (
        bundle.get("legacy_matrix_bundle"),
        bundle.get("canonical_matrix_bundle"),
        bundle.get("legacy_bootstrap_bundle"),
        bundle.get("canonical_bootstrap_bundle"),
    )
    if any(type(source) is not dict for source in sources):
        raise TypeError("proof must embed all exact native source bundles")
    expected = _compose_bundle(
        sources[0],  # type: ignore[arg-type]
        sources[1],  # type: ignore[arg-type]
        sources[2],  # type: ignore[arg-type]
        sources[3],  # type: ignore[arg-type]
        plan,
    )
    if bundle != expected:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "statistical applicability proof verification failed"
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "bindings": copy.deepcopy(bundle["bindings"]),
        **{
            key: copy.deepcopy(bundle[key])
            for key in (
                "source_executed_run_count",
                "statistical_additional_backtest_run_count",
                "matrix_candidate_count",
                "canonical_retained_split_bound_count",
                "bootstrap_strategy_count",
                "bootstrap_interval_value_count",
                "bootstrap_differing_interval_value_count",
                "bootstrap_equal_interval_value_count",
                "bootstrap_differing_seed_count",
                "matrix_outcome_applicability_proven",
                "dsr_numerical_applicability_proven",
                "pbo_numerical_applicability_proven",
                "tie_bounds_numerical_applicability_proven",
                "bootstrap_numerical_applicability_proven",
                "full_statistical_reference_applicability_proven",
                "canonical_reproducibility_ledger_verified",
                "statistical_ledger_alignment_proven",
                "full_report_alignment_proven",
                "run_accounting_additive",
                "formal_inference_claimed",
                "decision_threshold",
                "state",
                "maturity",
                "status",
                "gaps",
                "authority",
                "runtime_mutations",
            )
        },
    }


def render_synthetic_strategy_statistical_applicability_proof_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_statistical_applicability_proof_v1(
        bundle
    )
    stages = receipt["bindings"]["stages"]
    lines = [
        "# Synthetic Strategy Statistical Applicability Proof v1",
        "",
        "## SOURCE",
        f"- Matrix outcome projection: `{stages['matrix']['outcome_projection_sha256']}`",
        f"- DSR outcome projection: `{stages['dsr']['outcome_projection_sha256']}`",
        f"- PBO outcome projection: `{stages['pbo']['outcome_projection_sha256']}`",
        f"- Tie-bounds outcome projection: `{stages['tie']['outcome_projection_sha256']}`",
        "- Source runs: 179 legacy + 179 canonical; statistical backtests: 0",
        "",
        "## GAP",
        *[f"- {gap}" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Matrix outcome applicability proven: TRUE",
        "- DSR numerical applicability proven: TRUE",
        "- PBO numerical applicability proven: TRUE",
        "- Tie-bounds numerical applicability proven: TRUE",
        "- Bootstrap numerical applicability proven: FALSE",
        "- Full statistical reference applicability proven: FALSE",
        "- Statistical ledger alignment proven: FALSE",
        "- Full report alignment proven: FALSE",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    markdown = "\n".join(lines) + "\n"
    if "READY" in markdown or "Profitability proven: TRUE" in markdown:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "neutral renderer token violation"
        )
    return markdown


def plan_synthetic_strategy_statistical_applicability_proof_v2() -> (
    dict[str, Any]
):
    payload = {
        "schema_version": OUTCOME_PLAN_SCHEMA_VERSION,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "bootstrap_seed_policy_version": (
            "paired-moving-block-bootstrap-policy-v2"
        ),
        "comparison_stage_ids": ["matrix", "dsr", "pbo", "tie", "bootstrap"],
        "projection_removed_key_names": sorted(_DROP_EXACT),
        "matrix_outcome_applicability_proven": False,
        "dsr_numerical_applicability_proven": False,
        "pbo_numerical_applicability_proven": False,
        "tie_bounds_numerical_applicability_proven": False,
        "bootstrap_numerical_applicability_proven": False,
        "full_statistical_numerical_applicability_proven": False,
        "full_statistical_reference_applicability_proven": False,
        "bootstrap_seed_identity_policy_proven": False,
        "bootstrap_source_provenance_binding_preserved": False,
        "canonical_reproducibility_ledger_verified": False,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "state": "PLANNED",
        "maturity": OUTCOME_MATURITY,
        "status": STATUS,
        "gaps": list(_OUTCOME_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    result = copy.deepcopy(payload)
    result["plan_sha256"] = canonical_sha256(payload)
    return result


def _bootstrap_v3_projection(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": record["strategy_id"],
            "family_id": record["family_id"],
            "statistical_sample_sha256": record[
                "statistical_sample_sha256"
            ],
            "policy_sha256": record["bootstrap_evidence"]["policy_sha256"],
            "seed_material_sha256": record["bootstrap_evidence"][
                "seed_material_sha256"
            ],
            "sample_summary": copy.deepcopy(
                record["bootstrap_evidence"]["sample_summary"]
            ),
            "intervals": copy.deepcopy(
                record["bootstrap_evidence"]["intervals"]
            ),
        }
        for record in bundle["strategy_records"]
    ]


def _verify_sources_v2(
    legacy_matrix: dict[str, Any],
    canonical_matrix: dict[str, Any],
    legacy_bootstrap: dict[str, Any],
    canonical_bootstrap: dict[str, Any],
) -> dict[str, Any]:
    if any(
        type(value) is not dict
        for value in (
            legacy_matrix,
            canonical_matrix,
            legacy_bootstrap,
            canonical_bootstrap,
        )
    ):
        raise TypeError("all v2 applicability sources must be exact dicts")
    legacy_matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v1(
        legacy_matrix
    )
    canonical_matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v2(
        canonical_matrix
    )
    if (
        legacy_matrix_receipt.get("state") != "OBSERVED"
        or canonical_matrix_receipt.get("state") != "OBSERVED"
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v2 matrix sources did not retain observed state"
        )
    legacy_robustness = legacy_matrix["source_robustness_bundle"]
    canonical_robustness = canonical_matrix["source_robustness_bundle"]
    robustness_proof = build_synthetic_strategy_robustness_lineage_proof_v1(
        legacy_robustness,
        canonical_robustness,
        execute=True,
    )
    robustness_receipt = verify_synthetic_strategy_robustness_lineage_proof_v1(
        robustness_proof
    )
    if robustness_receipt["robustness_outcome_alignment_proven"] is not True:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v2 robustness applicability prerequisite failed"
        )
    legacy_baseline = legacy_robustness["source_bundle"]
    canonical_baseline = canonical_robustness["source_bundle"]
    verify_synthetic_strategy_bootstrap_validation_v3(
        legacy_bootstrap, legacy_baseline
    )
    verify_synthetic_strategy_bootstrap_validation_v3(
        canonical_bootstrap, canonical_baseline
    )
    return robustness_proof


def _compose_bundle_v2(
    legacy_matrix: dict[str, Any],
    canonical_matrix: dict[str, Any],
    legacy_bootstrap: dict[str, Any],
    canonical_bootstrap: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    robustness_proof = _verify_sources_v2(
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
    )
    stages = _build_analysis_stages(legacy_matrix, canonical_matrix)
    stage_bindings = {
        "matrix": _stage_binding(legacy_matrix, canonical_matrix),
        **{
            name: _stage_binding(legacy, canonical)
            for name, (legacy, canonical) in stages.items()
        },
    }
    canonical_tie = stages["tie"][1]
    if canonical_tie["retained_split_bound_count"] != (
        CANONICAL_RETAINED_SPLIT_BOUND_COUNT
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v2 canonical tie retained-split count drifted"
        )
    legacy_projection = _bootstrap_v3_projection(legacy_bootstrap)
    canonical_projection = _bootstrap_v3_projection(canonical_bootstrap)
    if legacy_projection != canonical_projection:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v3 Bootstrap statistical outcome projection mismatch"
        )
    if legacy_bootstrap["bundle_sha256"] == canonical_bootstrap["bundle_sha256"]:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v3 Bootstrap source provenance identities must remain distinct"
        )
    legacy_interval_values = _bootstrap_interval_values(legacy_bootstrap)
    canonical_interval_values = _bootstrap_interval_values(canonical_bootstrap)
    if (
        len(legacy_interval_values) != BOOTSTRAP_INTERVAL_VALUE_COUNT
        or len(canonical_interval_values) != BOOTSTRAP_INTERVAL_VALUE_COUNT
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v3 Bootstrap interval coverage drifted"
        )
    differing_interval_count = sum(
        legacy != canonical
        for legacy, canonical in zip(
            legacy_interval_values, canonical_interval_values
        )
    )
    legacy_seeds = _bootstrap_seed_values(legacy_bootstrap)
    canonical_seeds = _bootstrap_seed_values(canonical_bootstrap)
    differing_seed_count = sum(
        legacy != canonical
        for legacy, canonical in zip(legacy_seeds, canonical_seeds)
    )
    if (
        differing_interval_count
        != OUTCOME_BOOTSTRAP_DIFFERING_INTERVAL_VALUE_COUNT
        or differing_seed_count != OUTCOME_BOOTSTRAP_DIFFERING_SEED_COUNT
    ):
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v3 Bootstrap seed or interval equality drifted"
        )
    bootstrap_binding = {
        "legacy_bundle_sha256": legacy_bootstrap["bundle_sha256"],
        "canonical_bundle_sha256": canonical_bootstrap["bundle_sha256"],
        "statistical_outcome_projection_sha256": canonical_sha256(
            legacy_projection
        ),
        "interval_values_sha256": canonical_sha256(legacy_interval_values),
        "seed_material_sha256": canonical_sha256(legacy_seeds),
        "source_bundle_identity_distinct": True,
        "source_provenance_affects_seed": False,
    }
    payload = {
        "schema_version": OUTCOME_BUNDLE_SCHEMA_VERSION,
        "plan": copy.deepcopy(plan),
        "legacy_matrix_bundle": copy.deepcopy(legacy_matrix),
        "canonical_matrix_bundle": copy.deepcopy(canonical_matrix),
        "legacy_bootstrap_bundle": copy.deepcopy(legacy_bootstrap),
        "canonical_bootstrap_bundle": copy.deepcopy(canonical_bootstrap),
        "bindings": {
            "robustness_lineage_proof_bundle_sha256": robustness_proof[
                "bundle_sha256"
            ],
            "canonical_run_reproducibility_ledger_sha256": canonical_matrix[
                "source_run_reproducibility_ledger_sha256"
            ],
            "stages": stage_bindings,
            "bootstrap": bootstrap_binding,
        },
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "canonical_retained_split_bound_count": (
            CANONICAL_RETAINED_SPLIT_BOUND_COUNT
        ),
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "bootstrap_differing_interval_value_count": differing_interval_count,
        "bootstrap_equal_interval_value_count": (
            BOOTSTRAP_INTERVAL_VALUE_COUNT - differing_interval_count
        ),
        "bootstrap_differing_seed_count": differing_seed_count,
        "matrix_outcome_applicability_proven": True,
        "dsr_numerical_applicability_proven": True,
        "pbo_numerical_applicability_proven": True,
        "tie_bounds_numerical_applicability_proven": True,
        "bootstrap_numerical_applicability_proven": True,
        "full_statistical_numerical_applicability_proven": True,
        "full_statistical_reference_applicability_proven": False,
        "bootstrap_seed_identity_policy_proven": True,
        "bootstrap_source_provenance_binding_preserved": True,
        "canonical_reproducibility_ledger_verified": True,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "state": STATE,
        "maturity": OUTCOME_MATURITY,
        "status": STATUS,
        "gaps": list(_OUTCOME_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    result = copy.deepcopy(payload)
    result["bundle_sha256"] = canonical_sha256(payload)
    return result


def build_synthetic_strategy_statistical_applicability_proof_v2(
    legacy_matrix: dict[str, Any] | None = None,
    canonical_matrix: dict[str, Any] | None = None,
    legacy_bootstrap: dict[str, Any] | None = None,
    canonical_bootstrap: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    sources = (
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
    )
    if execute is False:
        if any(source is not None for source in sources):
            raise ValueError("plan-only mode does not accept prebuilt sources")
        return plan_synthetic_strategy_statistical_applicability_proof_v2()
    if any(source is None for source in sources):
        raise ValueError("execute=True requires all four prebuilt sources")
    return _compose_bundle_v2(
        legacy_matrix,  # type: ignore[arg-type]
        canonical_matrix,  # type: ignore[arg-type]
        legacy_bootstrap,  # type: ignore[arg-type]
        canonical_bootstrap,  # type: ignore[arg-type]
        plan_synthetic_strategy_statistical_applicability_proof_v2(),
    )


def build_default_synthetic_strategy_statistical_applicability_proof_v2(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        return plan_synthetic_strategy_statistical_applicability_proof_v2()
    legacy_source = build_synthetic_strategy_report_bundle_v1(execute=True)
    canonical_source = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_default_reference_context(),
    )
    legacy_matrix = build_synthetic_strategy_trial_return_matrix_v1(
        legacy_source, execute=True
    )
    canonical_matrix = build_synthetic_strategy_trial_return_matrix_v2(
        canonical_source, execute=True
    )
    legacy_bootstrap = build_synthetic_strategy_bootstrap_validation_v3(
        legacy_source, execute=True
    )
    canonical_bootstrap = build_synthetic_strategy_bootstrap_validation_v3(
        canonical_source, execute=True
    )
    return build_synthetic_strategy_statistical_applicability_proof_v2(
        legacy_matrix,
        canonical_matrix,
        legacy_bootstrap,
        canonical_bootstrap,
        execute=True,
    )


def _verify_declared_boundary_v2(bundle: dict[str, Any]) -> None:
    expected = {
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "statistical_additional_backtest_run_count": 0,
        "matrix_candidate_count": MATRIX_CANDIDATE_COUNT,
        "canonical_retained_split_bound_count": CANONICAL_RETAINED_SPLIT_BOUND_COUNT,
        "bootstrap_strategy_count": BOOTSTRAP_STRATEGY_COUNT,
        "bootstrap_interval_value_count": BOOTSTRAP_INTERVAL_VALUE_COUNT,
        "bootstrap_differing_interval_value_count": 0,
        "bootstrap_equal_interval_value_count": 54,
        "bootstrap_differing_seed_count": 0,
        "matrix_outcome_applicability_proven": True,
        "dsr_numerical_applicability_proven": True,
        "pbo_numerical_applicability_proven": True,
        "tie_bounds_numerical_applicability_proven": True,
        "bootstrap_numerical_applicability_proven": True,
        "full_statistical_numerical_applicability_proven": True,
        "full_statistical_reference_applicability_proven": False,
        "bootstrap_seed_identity_policy_proven": True,
        "bootstrap_source_provenance_binding_preserved": True,
        "canonical_reproducibility_ledger_verified": True,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "state": STATE,
        "maturity": OUTCOME_MATURITY,
        "status": STATUS,
        "gaps": _OUTCOME_GAPS,
        "authority": _AUTHORITY,
        "runtime_mutations": False,
    }
    for field, value in expected.items():
        if bundle.get(field) != value:
            raise SyntheticStrategyStatisticalApplicabilityProofError(
                f"declared v2 applicability boundary drifted: {field}"
            )


def verify_synthetic_strategy_statistical_applicability_proof_v2(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise TypeError("bundle must be an exact native dict")
    if bundle.get("schema_version") != OUTCOME_BUNDLE_SCHEMA_VERSION:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "unexpected v2 statistical applicability proof schema"
        )
    plan = bundle.get("plan")
    if plan != plan_synthetic_strategy_statistical_applicability_proof_v2():
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v2 statistical applicability proof plan mismatch"
        )
    _verify_declared_boundary_v2(bundle)
    sources = (
        bundle.get("legacy_matrix_bundle"),
        bundle.get("canonical_matrix_bundle"),
        bundle.get("legacy_bootstrap_bundle"),
        bundle.get("canonical_bootstrap_bundle"),
    )
    if any(type(source) is not dict for source in sources):
        raise TypeError("v2 proof must embed all exact native source bundles")
    expected = _compose_bundle_v2(
        sources[0],  # type: ignore[arg-type]
        sources[1],  # type: ignore[arg-type]
        sources[2],  # type: ignore[arg-type]
        sources[3],  # type: ignore[arg-type]
        plan,
    )
    if bundle != expected:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "v2 statistical applicability proof verification failed"
        )
    fields = (
        "source_executed_run_count",
        "statistical_additional_backtest_run_count",
        "matrix_candidate_count",
        "canonical_retained_split_bound_count",
        "bootstrap_strategy_count",
        "bootstrap_interval_value_count",
        "bootstrap_differing_interval_value_count",
        "bootstrap_equal_interval_value_count",
        "bootstrap_differing_seed_count",
        "matrix_outcome_applicability_proven",
        "dsr_numerical_applicability_proven",
        "pbo_numerical_applicability_proven",
        "tie_bounds_numerical_applicability_proven",
        "bootstrap_numerical_applicability_proven",
        "full_statistical_numerical_applicability_proven",
        "full_statistical_reference_applicability_proven",
        "bootstrap_seed_identity_policy_proven",
        "bootstrap_source_provenance_binding_preserved",
        "canonical_reproducibility_ledger_verified",
        "statistical_ledger_alignment_proven",
        "full_report_alignment_proven",
        "run_accounting_additive",
        "formal_inference_claimed",
        "decision_threshold",
        "state",
        "maturity",
        "status",
        "gaps",
        "authority",
        "runtime_mutations",
    )
    return {
        "schema_version": OUTCOME_RECEIPT_SCHEMA_VERSION,
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "bindings": copy.deepcopy(bundle["bindings"]),
        **{key: copy.deepcopy(bundle[key]) for key in fields},
    }


def render_synthetic_strategy_statistical_applicability_proof_markdown_v2(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_statistical_applicability_proof_v2(
        bundle
    )
    lines = [
        "# Synthetic Strategy Statistical Applicability Proof v2",
        "",
        "## SOURCE",
        "- PURE_SYNTHETIC_IN_MEMORY",
        "- Source runs: 179 legacy + 179 canonical; statistical backtests: 0",
        "- Bootstrap seed identity: preregistered policy + exact paired return sample",
        "- Source provenance remains bound to each distinct evidence bundle",
        "",
        "## GAP",
        *[f"- {gap}" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Matrix outcome applicability proven: TRUE",
        "- DSR numerical applicability proven: TRUE",
        "- PBO numerical applicability proven: TRUE",
        "- Tie-bounds numerical applicability proven: TRUE",
        "- Bootstrap numerical applicability proven: TRUE",
        "- Full statistical numerical applicability proven: TRUE",
        "- Full statistical reference applicability proven: FALSE",
        "- Statistical ledger alignment proven: FALSE",
        "- Full report alignment proven: FALSE",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    markdown = "\n".join(lines) + "\n"
    if "READY" in markdown or "Profitability proven: TRUE" in markdown:
        raise SyntheticStrategyStatisticalApplicabilityProofError(
            "neutral v2 renderer token violation"
        )
    return markdown
