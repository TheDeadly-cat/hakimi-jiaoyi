from __future__ import annotations

import copy
from typing import Any

from hakimi_research.synthetic_strategy_baseline_lineage_proof import (
    _default_reference_context,
    build_synthetic_strategy_baseline_lineage_proof_v1,
    verify_synthetic_strategy_baseline_lineage_proof_v1,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
)
from hakimi_research.synthetic_strategy_robustness_evidence import (
    build_synthetic_strategy_robustness_evidence_v1,
    build_synthetic_strategy_robustness_evidence_v2,
    verify_synthetic_strategy_robustness_evidence_v1,
    verify_synthetic_strategy_robustness_evidence_v2,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-robustness-lineage-proof-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-robustness-lineage-proof-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-robustness-lineage-proof-receipt-v1"
MATURITY = "SYNTHETIC_ROBUSTNESS_OUTCOME_LINEAGE_ONLY"
STATUS = "BLOCK"
STATE = "OBSERVED_WITH_GAPS"
LEGACY_BASELINE_RUN_COUNT = 32
LEGACY_ROBUSTNESS_RUN_COUNT = 147
CANONICAL_BASELINE_RUN_COUNT = 32
CANONICAL_ROBUSTNESS_RUN_COUNT = 147
SOURCE_EXECUTED_RUN_COUNT = 358
ALIGNED_OUTCOME_PAIR_COUNT = 147

_REMOVED_PROVENANCE_KEYS = {
    "experiment_manifest",
    "reproducibility",
    "reproducibility_context",
    "run_reproducibility_ledger",
    "source_reproducibility_context_required",
    "source_schema_version",
    "schema_version",
    "completed_evidence",
    "gaps",
    "bundle_sha256",
    "source_bundle_sha256",
    "plan_sha256",
    "run_sha256",
    "result_sha256",
    "report_sha256",
    "binding_sha256",
    "evidence_sha256",
    "source_report_sha256",
    "source_result_sha256",
    "record_sha256",
    "run_ledger_sha256",
    "diagnostics_sha256",
    "artifact_sha256",
    "ledger_sha256",
    "source_run_sha256",
    "lineage_sha256",
    "producer_report_sha256",
    "selected_result_sha256",
    "benchmark_result_sha256",
    "strategy_result_sha256",
}
_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "LEGACY_ROBUSTNESS_RUN_MANIFESTS_UNBOUND",
    "MANIFEST_PROVENANCE_DIFFERS_BY_VERSION",
    "OVERLAPPING_RUN_ACCOUNTING_NOT_ADDITIVE",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "STATISTICAL_LEDGER_ALIGNMENT_NOT_PROVEN",
]
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyRobustnessLineageProofError(ValueError):
    pass


def _outcome_projection(value: Any) -> Any:
    value_type = type(value)
    if value_type is dict:
        return {
            key: _outcome_projection(item)
            for key, item in value.items()
            if key not in _REMOVED_PROVENANCE_KEYS
        }
    if value_type is list:
        return [_outcome_projection(item) for item in value]
    if value is None or value_type in (str, int, float, bool):
        return copy.deepcopy(value)
    raise TypeError("robustness projection requires exact native JSON values")


def _compact_records(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *bundle["benchmark_ledger"],
        *[
            record
            for evidence in bundle["strategy_evidence"]
            for record in evidence["run_ledger"]
        ],
    ]


def plan_synthetic_strategy_robustness_lineage_proof_v1() -> dict[str, Any]:
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "legacy_baseline_run_count": LEGACY_BASELINE_RUN_COUNT,
        "legacy_robustness_run_count": LEGACY_ROBUSTNESS_RUN_COUNT,
        "canonical_baseline_run_count": CANONICAL_BASELINE_RUN_COUNT,
        "canonical_robustness_run_count": CANONICAL_ROBUSTNESS_RUN_COUNT,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "outcome_projection_removed_key_names": sorted(
            _REMOVED_PROVENANCE_KEYS
        ),
        "run_id_retained_and_compared": True,
        "phase_retained_and_compared": True,
        "parameter_id_retained_and_compared": True,
        "dataset_hash_retained_and_compared": True,
        "compact_outcomes_retained_and_compared": True,
        "baseline_outcome_alignment_proven": False,
        "robustness_outcome_alignment_proven": False,
        "robustness_bundle_identity_equal": False,
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
    legacy_v1_bundle: dict[str, Any],
    canonical_v2_bundle: dict[str, Any],
) -> None:
    if type(legacy_v1_bundle) is not dict:
        raise TypeError("legacy_v1_bundle must be an exact native dict")
    if type(canonical_v2_bundle) is not dict:
        raise TypeError("canonical_v2_bundle must be an exact native dict")
    legacy_receipt = verify_synthetic_strategy_robustness_evidence_v1(
        legacy_v1_bundle
    )
    canonical_receipt = verify_synthetic_strategy_robustness_evidence_v2(
        canonical_v2_bundle
    )
    if legacy_receipt.get("status") != "PASS":
        raise SyntheticStrategyRobustnessLineageProofError(
            "legacy robustness verification failed"
        )
    if canonical_receipt.get("status") != "PASS":
        raise SyntheticStrategyRobustnessLineageProofError(
            "canonical robustness verification failed"
        )
    if legacy_receipt.get("verified_run_count") != LEGACY_ROBUSTNESS_RUN_COUNT:
        raise SyntheticStrategyRobustnessLineageProofError(
            "legacy robustness run count drifted"
        )
    if canonical_receipt.get("verified_run_count") != CANONICAL_ROBUSTNESS_RUN_COUNT:
        raise SyntheticStrategyRobustnessLineageProofError(
            "canonical robustness run count drifted"
        )


def _verify_record_pairs(
    legacy_records: list[dict[str, Any]],
    canonical_records: list[dict[str, Any]],
) -> None:
    if len(legacy_records) != ALIGNED_OUTCOME_PAIR_COUNT:
        raise SyntheticStrategyRobustnessLineageProofError(
            "legacy compact record count drifted"
        )
    if len(canonical_records) != ALIGNED_OUTCOME_PAIR_COUNT:
        raise SyntheticStrategyRobustnessLineageProofError(
            "canonical compact record count drifted"
        )
    identity_fields = ("run_id", "phase", "window_id", "parameter_id")
    outcome_fields = (
        "status",
        "failure_code",
        "dataset_sha256",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "trade_count",
    )
    for index, (legacy, canonical) in enumerate(
        zip(legacy_records, canonical_records)
    ):
        if any(legacy[field] != canonical[field] for field in identity_fields):
            raise SyntheticStrategyRobustnessLineageProofError(
                f"compact record identity mismatch at index {index}"
            )
        if any(legacy[field] != canonical[field] for field in outcome_fields):
            raise SyntheticStrategyRobustnessLineageProofError(
                f"compact record outcome mismatch at index {index}"
            )


def _compose_bundle(
    legacy_v1_bundle: dict[str, Any],
    canonical_v2_bundle: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    baseline_proof = build_synthetic_strategy_baseline_lineage_proof_v1(
        legacy_v1_bundle["source_bundle"],
        canonical_v2_bundle["source_bundle"],
        execute=True,
    )
    baseline_receipt = verify_synthetic_strategy_baseline_lineage_proof_v1(
        baseline_proof
    )
    if baseline_receipt["baseline_outcome_alignment_proven"] is not True:
        raise SyntheticStrategyRobustnessLineageProofError(
            "baseline outcome alignment prerequisite failed"
        )
    legacy_records = _compact_records(legacy_v1_bundle)
    canonical_records = _compact_records(canonical_v2_bundle)
    _verify_record_pairs(legacy_records, canonical_records)
    legacy_projection = _outcome_projection(legacy_v1_bundle)
    canonical_projection = _outcome_projection(canonical_v2_bundle)
    if legacy_projection != canonical_projection:
        raise SyntheticStrategyRobustnessLineageProofError(
            "robustness outcome projection mismatch"
        )
    if legacy_v1_bundle["bundle_sha256"] == canonical_v2_bundle[
        "bundle_sha256"
    ]:
        raise SyntheticStrategyRobustnessLineageProofError(
            "versioned robustness identities must remain distinct"
        )
    ledger = canonical_v2_bundle.get("run_reproducibility_ledger")
    if (
        type(ledger) is not dict
        or ledger.get("run_count") != CANONICAL_ROBUSTNESS_RUN_COUNT
        or type(ledger.get("records")) is not list
        or len(ledger["records"]) != CANONICAL_ROBUSTNESS_RUN_COUNT
        or ledger.get("evaluation_role_counts")
        != {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39}
    ):
        raise SyntheticStrategyRobustnessLineageProofError(
            "canonical reproducibility ledger boundary drifted"
        )
    if "run_reproducibility_ledger" in legacy_v1_bundle:
        raise SyntheticStrategyRobustnessLineageProofError(
            "legacy robustness unexpectedly contains a reproducibility ledger"
        )
    outcome_projection_sha256 = canonical_sha256(legacy_projection)
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "plan": copy.deepcopy(plan),
        "legacy_v1_robustness_bundle": copy.deepcopy(legacy_v1_bundle),
        "canonical_v2_robustness_bundle": copy.deepcopy(canonical_v2_bundle),
        "bindings": {
            "baseline_lineage_proof_bundle_sha256": baseline_proof[
                "bundle_sha256"
            ],
            "legacy_v1_robustness_bundle_sha256": legacy_v1_bundle[
                "bundle_sha256"
            ],
            "canonical_v2_robustness_bundle_sha256": canonical_v2_bundle[
                "bundle_sha256"
            ],
            "robustness_outcome_projection_sha256": (
                outcome_projection_sha256
            ),
            "canonical_run_reproducibility_ledger_sha256": ledger[
                "ledger_sha256"
            ],
        },
        "legacy_baseline_run_count": LEGACY_BASELINE_RUN_COUNT,
        "legacy_robustness_run_count": LEGACY_ROBUSTNESS_RUN_COUNT,
        "canonical_baseline_run_count": CANONICAL_BASELINE_RUN_COUNT,
        "canonical_robustness_run_count": CANONICAL_ROBUSTNESS_RUN_COUNT,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "run_ids_equal": True,
        "phases_equal": True,
        "parameter_ids_equal": True,
        "dataset_hashes_equal": True,
        "compact_outcomes_equal": True,
        "baseline_outcome_alignment_proven": True,
        "robustness_outcome_alignment_proven": True,
        "robustness_bundle_identity_equal": False,
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


def build_synthetic_strategy_robustness_lineage_proof_v1(
    legacy_v1_bundle: dict[str, Any] | None = None,
    canonical_v2_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if legacy_v1_bundle is not None or canonical_v2_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt sources")
        return plan_synthetic_strategy_robustness_lineage_proof_v1()
    if legacy_v1_bundle is None or canonical_v2_bundle is None:
        raise ValueError("execute=True requires both prebuilt robustness sources")
    _verify_sources(legacy_v1_bundle, canonical_v2_bundle)
    return _compose_bundle(
        legacy_v1_bundle,
        canonical_v2_bundle,
        plan_synthetic_strategy_robustness_lineage_proof_v1(),
    )


def build_default_synthetic_strategy_robustness_lineage_proof_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        return plan_synthetic_strategy_robustness_lineage_proof_v1()
    legacy_source = build_synthetic_strategy_report_bundle_v1(execute=True)
    canonical_source = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_default_reference_context(),
    )
    legacy = build_synthetic_strategy_robustness_evidence_v1(
        legacy_source,
        execute=True,
    )
    canonical = build_synthetic_strategy_robustness_evidence_v2(
        canonical_source,
        execute=True,
    )
    return build_synthetic_strategy_robustness_lineage_proof_v1(
        legacy,
        canonical,
        execute=True,
    )


def verify_synthetic_strategy_robustness_lineage_proof_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise TypeError("bundle must be an exact native dict")
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise SyntheticStrategyRobustnessLineageProofError(
            "unexpected robustness lineage proof schema"
        )
    plan = bundle.get("plan")
    if plan != plan_synthetic_strategy_robustness_lineage_proof_v1():
        raise SyntheticStrategyRobustnessLineageProofError(
            "robustness lineage proof plan mismatch"
        )
    legacy = bundle.get("legacy_v1_robustness_bundle")
    canonical = bundle.get("canonical_v2_robustness_bundle")
    if type(legacy) is not dict or type(canonical) is not dict:
        raise TypeError("lineage proof must embed exact robustness sources")
    _verify_sources(legacy, canonical)
    expected = _compose_bundle(legacy, canonical, plan)
    if bundle != expected:
        raise SyntheticStrategyRobustnessLineageProofError(
            "robustness lineage proof verification failed"
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": plan["plan_sha256"],
        **copy.deepcopy(bundle["bindings"]),
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "baseline_outcome_alignment_proven": True,
        "robustness_outcome_alignment_proven": True,
        "robustness_bundle_identity_equal": False,
        "canonical_reproducibility_ledger_verified": True,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "state": STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }


def render_synthetic_strategy_robustness_lineage_proof_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_robustness_lineage_proof_v1(bundle)
    lines = [
        "# Synthetic Strategy Robustness Lineage Proof v1",
        "",
        "## SOURCE",
        (
            "- Legacy robustness bundle: `"
            f"{receipt['legacy_v1_robustness_bundle_sha256']}`"
        ),
        (
            "- Canonical robustness bundle: `"
            f"{receipt['canonical_v2_robustness_bundle_sha256']}`"
        ),
        (
            "- Robustness outcome projection: `"
            f"{receipt['robustness_outcome_projection_sha256']}`"
        ),
        f"- Aligned outcome pairs: {receipt['aligned_outcome_pair_count']}",
        "- Source runs: 179 legacy + 179 canonical; comparison backtests: 0",
        "",
        "## GAP",
        *[f"- {gap}" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Baseline outcome alignment proven: TRUE",
        "- Robustness outcome alignment proven: TRUE",
        "- Robustness bundle identity equal: FALSE",
        "- Canonical reproducibility ledger verified: TRUE",
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
        raise SyntheticStrategyRobustnessLineageProofError(
            "neutral renderer token violation"
        )
    return markdown
