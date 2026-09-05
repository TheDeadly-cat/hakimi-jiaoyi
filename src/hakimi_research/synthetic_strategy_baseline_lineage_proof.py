from __future__ import annotations

import copy
import hashlib
from typing import Any

from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.synthetic_strategy_report_bundle import (
    _v1_projection_from_v2,
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
    verify_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v2,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-baseline-lineage-proof-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-baseline-lineage-proof-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-baseline-lineage-proof-receipt-v1"
MATURITY = "SYNTHETIC_BASELINE_OUTCOME_LINEAGE_ONLY"
STATUS = "BLOCK"
STATE = "OBSERVED_WITH_GAPS"
LEGACY_SOURCE_RUN_COUNT = 32
CANONICAL_SOURCE_RUN_COUNT = 32
SOURCE_EXECUTED_RUN_COUNT = 64
ALIGNED_OUTCOME_PAIR_COUNT = 32
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"

_DERIVED_PROVENANCE_KEYS = {
    "bundle_sha256",
    "run_sha256",
    "result_sha256",
    "report_sha256",
    "binding_sha256",
    "evidence_sha256",
    "source_report_sha256",
    "source_result_sha256",
}
_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "MANIFEST_PROVENANCE_DIFFERS_BY_VERSION",
    "OVERLAPPING_RUN_ACCOUNTING_NOT_ADDITIVE",
    "REAL_DATASET_GAP",
    "ROBUSTNESS_LINEAGE_ALIGNMENT_NOT_PROVEN",
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


class SyntheticStrategyBaselineLineageProofError(ValueError):
    pass


def _default_reference_context() -> dict[str, Any]:
    lock_hash = hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest()
    return {
        "schema_version": "synthetic-strategy-reference-context-v1",
        "git_commit_sha": "0" * 40,
        "git_worktree_clean": False,
        "dependency_lock_hash": lock_hash,
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "runtime_version": "python-3.14",
    }


def _outcome_projection(value: Any) -> Any:
    value_type = type(value)
    if value_type is dict:
        return {
            key: _outcome_projection(item)
            for key, item in value.items()
            if key != "experiment_manifest"
            and key not in _DERIVED_PROVENANCE_KEYS
        }
    if value_type is list:
        return [_outcome_projection(item) for item in value]
    if value is None or value_type in (str, int, float, bool):
        return copy.deepcopy(value)
    raise TypeError("outcome projection requires exact native JSON values")


def _all_runs(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    runs = [
        *bundle["benchmarks"].values(),
        *[
            run
            for report in bundle["strategy_reports"]
            for run in report["runs"].values()
        ],
    ]
    return sorted(runs, key=lambda run: run["run_id"])


def _run_dataset_hash(run: dict[str, Any]) -> str:
    try:
        value = run["result"]["experiment_manifest"]["dataset_hash"]
    except (KeyError, TypeError) as exc:
        raise SyntheticStrategyBaselineLineageProofError(
            "run dataset hash path missing"
        ) from exc
    if type(value) is not str or len(value) != 64:
        raise SyntheticStrategyBaselineLineageProofError(
            "run dataset hash must be an exact SHA-256 string"
        )
    return value


def plan_synthetic_strategy_baseline_lineage_proof_v1() -> dict[str, Any]:
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "legacy_source_schema_version": "synthetic-strategy-report-bundle-v1",
        "canonical_source_schema_version": "synthetic-strategy-report-bundle-v2",
        "legacy_source_run_count": LEGACY_SOURCE_RUN_COUNT,
        "canonical_source_run_count": CANONICAL_SOURCE_RUN_COUNT,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "outcome_projection_removed_key_names": sorted(
            _DERIVED_PROVENANCE_KEYS | {"experiment_manifest"}
        ),
        "dataset_hash_retained_and_compared": True,
        "run_id_retained_and_compared": True,
        "baseline_outcome_alignment_proven": False,
        "baseline_bundle_identity_equal": False,
        "robustness_alignment_proven": False,
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(legacy_v1_bundle) is not dict:
        raise TypeError("legacy_v1_bundle must be an exact native dict")
    if type(canonical_v2_bundle) is not dict:
        raise TypeError("canonical_v2_bundle must be an exact native dict")
    legacy_receipt = verify_synthetic_strategy_report_bundle_v1(
        legacy_v1_bundle
    )
    canonical_receipt = verify_synthetic_strategy_report_bundle_v2(
        canonical_v2_bundle
    )
    if legacy_receipt.get("status") != "PASS":
        raise SyntheticStrategyBaselineLineageProofError(
            "legacy v1 source verification failed"
        )
    if canonical_receipt.get("status") != "PASS":
        raise SyntheticStrategyBaselineLineageProofError(
            "canonical v2 source verification failed"
        )
    if legacy_receipt.get("verified_run_count") != LEGACY_SOURCE_RUN_COUNT:
        raise SyntheticStrategyBaselineLineageProofError(
            "legacy source run count drifted"
        )
    if canonical_receipt.get("verified_run_count") != CANONICAL_SOURCE_RUN_COUNT:
        raise SyntheticStrategyBaselineLineageProofError(
            "canonical source run count drifted"
        )
    return legacy_receipt, canonical_receipt


def _compose_bundle(
    legacy_v1_bundle: dict[str, Any],
    canonical_v2_bundle: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    canonical_v1_projection = _v1_projection_from_v2(canonical_v2_bundle)
    legacy_runs = _all_runs(legacy_v1_bundle)
    canonical_runs = _all_runs(canonical_v1_projection)
    if len(legacy_runs) != ALIGNED_OUTCOME_PAIR_COUNT:
        raise SyntheticStrategyBaselineLineageProofError(
            "legacy outcome run count drifted"
        )
    if len(canonical_runs) != ALIGNED_OUTCOME_PAIR_COUNT:
        raise SyntheticStrategyBaselineLineageProofError(
            "canonical outcome run count drifted"
        )
    legacy_run_ids = [run.get("run_id") for run in legacy_runs]
    canonical_run_ids = [run.get("run_id") for run in canonical_runs]
    if any(type(value) is not str for value in legacy_run_ids):
        raise SyntheticStrategyBaselineLineageProofError(
            "legacy run IDs must be exact strings"
        )
    if legacy_run_ids != canonical_run_ids:
        raise SyntheticStrategyBaselineLineageProofError("run ID alignment failed")
    legacy_dataset_hashes = [_run_dataset_hash(run) for run in legacy_runs]
    canonical_dataset_hashes = [
        _run_dataset_hash(run) for run in canonical_runs
    ]
    if legacy_dataset_hashes != canonical_dataset_hashes:
        raise SyntheticStrategyBaselineLineageProofError(
            "dataset hash alignment failed"
        )
    legacy_projection = _outcome_projection(legacy_v1_bundle)
    canonical_projection = _outcome_projection(canonical_v1_projection)
    if legacy_projection != canonical_projection:
        raise SyntheticStrategyBaselineLineageProofError(
            "baseline outcome projection mismatch"
        )
    if legacy_v1_bundle["bundle_sha256"] == canonical_v2_bundle[
        "bundle_sha256"
    ]:
        raise SyntheticStrategyBaselineLineageProofError(
            "versioned source bundle identities must remain distinct"
        )
    outcome_projection_sha256 = canonical_sha256(legacy_projection)
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "plan": copy.deepcopy(plan),
        "legacy_v1_bundle": copy.deepcopy(legacy_v1_bundle),
        "canonical_v2_bundle": copy.deepcopy(canonical_v2_bundle),
        "bindings": {
            "legacy_v1_bundle_sha256": legacy_v1_bundle["bundle_sha256"],
            "canonical_v2_bundle_sha256": canonical_v2_bundle[
                "bundle_sha256"
            ],
            "canonical_v1_projection_bundle_sha256": (
                canonical_v1_projection["bundle_sha256"]
            ),
            "outcome_projection_sha256": outcome_projection_sha256,
            "fixture_protocol_sha256": legacy_v1_bundle["fixture"][
                "partition_protocol"
            ]["protocol_sha256"],
        },
        "legacy_source_run_count": LEGACY_SOURCE_RUN_COUNT,
        "canonical_source_run_count": CANONICAL_SOURCE_RUN_COUNT,
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "run_ids_equal": True,
        "dataset_hashes_equal": True,
        "baseline_outcome_alignment_proven": True,
        "baseline_bundle_identity_equal": False,
        "robustness_alignment_proven": False,
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


def build_synthetic_strategy_baseline_lineage_proof_v1(
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
        return plan_synthetic_strategy_baseline_lineage_proof_v1()
    if legacy_v1_bundle is None or canonical_v2_bundle is None:
        raise ValueError("execute=True requires both prebuilt lineage sources")
    _verify_sources(legacy_v1_bundle, canonical_v2_bundle)
    return _compose_bundle(
        legacy_v1_bundle,
        canonical_v2_bundle,
        plan_synthetic_strategy_baseline_lineage_proof_v1(),
    )


def build_default_synthetic_strategy_baseline_lineage_proof_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        return plan_synthetic_strategy_baseline_lineage_proof_v1()
    legacy = build_synthetic_strategy_report_bundle_v1(execute=True)
    canonical = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_default_reference_context(),
    )
    return build_synthetic_strategy_baseline_lineage_proof_v1(
        legacy,
        canonical,
        execute=True,
    )


def verify_synthetic_strategy_baseline_lineage_proof_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise TypeError("bundle must be an exact native dict")
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise SyntheticStrategyBaselineLineageProofError(
            "unexpected baseline lineage proof schema"
        )
    plan = bundle.get("plan")
    if plan != plan_synthetic_strategy_baseline_lineage_proof_v1():
        raise SyntheticStrategyBaselineLineageProofError(
            "baseline lineage proof plan mismatch"
        )
    legacy = bundle.get("legacy_v1_bundle")
    canonical = bundle.get("canonical_v2_bundle")
    if type(legacy) is not dict or type(canonical) is not dict:
        raise TypeError("lineage proof must embed exact native source bundles")
    _verify_sources(legacy, canonical)
    expected = _compose_bundle(legacy, canonical, plan)
    if bundle != expected:
        raise SyntheticStrategyBaselineLineageProofError(
            "baseline lineage proof verification failed"
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "legacy_v1_bundle_sha256": bundle["bindings"][
            "legacy_v1_bundle_sha256"
        ],
        "canonical_v2_bundle_sha256": bundle["bindings"][
            "canonical_v2_bundle_sha256"
        ],
        "canonical_v1_projection_bundle_sha256": bundle["bindings"][
            "canonical_v1_projection_bundle_sha256"
        ],
        "outcome_projection_sha256": bundle["bindings"][
            "outcome_projection_sha256"
        ],
        "fixture_protocol_sha256": bundle["bindings"][
            "fixture_protocol_sha256"
        ],
        "source_executed_run_count": SOURCE_EXECUTED_RUN_COUNT,
        "aligned_outcome_pair_count": ALIGNED_OUTCOME_PAIR_COUNT,
        "comparison_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "baseline_outcome_alignment_proven": True,
        "baseline_bundle_identity_equal": False,
        "robustness_alignment_proven": False,
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


def render_synthetic_strategy_baseline_lineage_proof_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_baseline_lineage_proof_v1(bundle)
    lines = [
        "# Synthetic Strategy Baseline Lineage Proof v1",
        "",
        "## SOURCE",
        f"- Legacy v1 bundle: `{receipt['legacy_v1_bundle_sha256']}`",
        f"- Canonical v2 bundle: `{receipt['canonical_v2_bundle_sha256']}`",
        f"- Outcome projection: `{receipt['outcome_projection_sha256']}`",
        f"- Aligned outcome pairs: {receipt['aligned_outcome_pair_count']}",
        "- Source runs: 32 legacy + 32 canonical; comparison backtests: 0",
        "",
        "## GAP",
        *[f"- {gap}" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Baseline outcome alignment proven: TRUE",
        "- Baseline bundle identity equal: FALSE",
        "- Robustness alignment proven: FALSE",
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
        raise SyntheticStrategyBaselineLineageProofError(
            "neutral renderer token violation"
        )
    return markdown
