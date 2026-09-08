from __future__ import annotations

from typing import Any

from hakimi_research.bootstrap_confidence_evidence import (
    BLOCK_LENGTH,
    CONFIDENCE_LEVEL,
    INSUFFICIENT_OBSERVATIONS_GAP,
    MINIMUM_OBSERVATION_COUNT,
    REPLICATE_COUNT,
    BootstrapConfidenceEvidenceError,
    _AUTHORITY,
    _canonical_sha256,
    _compound,
    _decimal,
    _fail,
    _interval,
    _normalise_curve,
    _require_sha256,
    _returns_by_time,
    _sample_indices,
)


SCHEMA_VERSION = "paired-moving-block-bootstrap-confidence-evidence-v2"
POLICY_SCHEMA_VERSION = "paired-moving-block-bootstrap-policy-v2"
RECEIPT_SCHEMA_VERSION = "paired-moving-block-bootstrap-confidence-receipt-v2"
SAMPLE_SCHEMA_VERSION = "paired-bootstrap-statistical-sample-v2"
SEED_SCHEMA_VERSION = "paired-bootstrap-seed-material-v2"
SEED_NAMESPACE = "hakimi-paired-moving-block-bootstrap-outcome-v2"


def paired_moving_block_bootstrap_policy_v2() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "method": "PAIRED_MOVING_BLOCK_BOOTSTRAP",
        "block_length": BLOCK_LENGTH,
        "replicate_count": REPLICATE_COUNT,
        "minimum_observation_count": MINIMUM_OBSERVATION_COUNT,
        "confidence_level": CONFIDENCE_LEVEL,
        "lower_quantile": "0.025",
        "upper_quantile": "0.975",
        "quantile_method": "LINEAR_TYPE_7",
        "seed_derivation": "SHA256_STATISTICAL_SAMPLE_IDENTITY_V2",
        "seed_namespace": SEED_NAMESPACE,
        "seed_source_provenance_included": False,
        "seed_statistical_sample_included": True,
        "paired_sampling": True,
        "statistics": [
            "STRATEGY_TOTAL_RETURN",
            "BUY_AND_HOLD_TOTAL_RETURN",
            "STRATEGY_MINUS_BUY_AND_HOLD_TOTAL_RETURN",
        ],
        "formal_inference_claimed": False,
        "performance_selection_used": False,
        "post_observation_policy_tuning": False,
    }


def build_bootstrap_confidence_evidence_v2(
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    strategy_id: str,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    strategy_curve = _normalise_curve(strategy_equity_curve, "strategy_equity_curve")
    benchmark_curve = _normalise_curve(benchmark_equity_curve, "benchmark_equity_curve")
    if type(strategy_id) is not str or not strategy_id:
        _fail("strategy_id", "must be a non-empty exact str")
    dataset_digest = _require_sha256(dataset_sha256, "dataset_sha256")
    strategy_digest = _require_sha256(
        strategy_result_sha256, "strategy_result_sha256"
    )
    benchmark_digest = _require_sha256(
        benchmark_result_sha256, "benchmark_result_sha256"
    )
    if type(observation_class) is not str or not observation_class:
        _fail("observation_class", "must be a non-empty exact str")

    strategy_returns_by_time = _returns_by_time(strategy_curve)
    benchmark_returns_by_time = _returns_by_time(benchmark_curve)
    common_times = sorted(set(strategy_returns_by_time) & set(benchmark_returns_by_time))
    strategy_returns = [strategy_returns_by_time[time] for time in common_times]
    benchmark_returns = [benchmark_returns_by_time[time] for time in common_times]
    policy = paired_moving_block_bootstrap_policy_v2()
    policy_sha256 = _canonical_sha256(policy)
    statistical_sample = {
        "schema_version": SAMPLE_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "observation_class": observation_class,
        "paired_observation_count": len(common_times),
        "common_times": common_times,
        "strategy_return_hex": [value.hex() for value in strategy_returns],
        "benchmark_return_hex": [value.hex() for value in benchmark_returns],
    }
    statistical_sample_sha256 = _canonical_sha256(statistical_sample)
    source_binding = {
        "dataset_sha256": dataset_digest,
        "strategy_result_sha256": strategy_digest,
        "benchmark_result_sha256": benchmark_digest,
        "strategy_equity_curve_sha256": _canonical_sha256(strategy_curve),
        "benchmark_equity_curve_sha256": _canonical_sha256(benchmark_curve),
        "common_observation_times_sha256": _canonical_sha256(common_times),
        "paired_observation_count": len(common_times),
        "start_time": common_times[0] if common_times else None,
        "end_time": common_times[-1] if common_times else None,
    }
    sample_summary = {
        "paired_observation_count": len(common_times),
        "strategy_total_return": _decimal(_compound(strategy_returns))
        if strategy_returns
        else None,
        "benchmark_total_return": _decimal(_compound(benchmark_returns))
        if benchmark_returns
        else None,
        "strategy_minus_benchmark_total_return": (
            _decimal(_compound(strategy_returns) - _compound(benchmark_returns))
            if strategy_returns
            else None
        ),
    }

    gaps: list[str] = []
    intervals: list[dict[str, Any]] = []
    replicate_count = 0
    seed_identity: dict[str, Any] | None = None
    seed_material_sha256: str | None = None
    if len(common_times) < MINIMUM_OBSERVATION_COUNT:
        gaps.append(INSUFFICIENT_OBSERVATIONS_GAP)
        evidence_state = "GAP"
    else:
        evidence_state = "OBSERVED"
        seed_identity = {
            "schema_version": SEED_SCHEMA_VERSION,
            "namespace": SEED_NAMESPACE,
            "strategy_id": strategy_id,
            "observation_class": observation_class,
            "policy_sha256": policy_sha256,
            "statistical_sample_sha256": statistical_sample_sha256,
            "source_provenance_included": False,
        }
        seed_material_sha256 = _canonical_sha256(seed_identity)
        strategy_distribution: list[float] = []
        benchmark_distribution: list[float] = []
        difference_distribution: list[float] = []
        for replicate_index in range(REPLICATE_COUNT):
            indices = _sample_indices(
                len(common_times), seed_material_sha256, replicate_index
            )
            sampled_strategy = [strategy_returns[index] for index in indices]
            sampled_benchmark = [benchmark_returns[index] for index in indices]
            strategy_total = _compound(sampled_strategy)
            benchmark_total = _compound(sampled_benchmark)
            strategy_distribution.append(strategy_total)
            benchmark_distribution.append(benchmark_total)
            difference_distribution.append(round(strategy_total - benchmark_total, 12))
        replicate_count = REPLICATE_COUNT
        strategy_point = _compound(strategy_returns)
        benchmark_point = _compound(benchmark_returns)
        intervals = [
            _interval("STRATEGY_TOTAL_RETURN", strategy_point, strategy_distribution),
            _interval(
                "BUY_AND_HOLD_TOTAL_RETURN",
                benchmark_point,
                benchmark_distribution,
            ),
            _interval(
                "STRATEGY_MINUS_BUY_AND_HOLD_TOTAL_RETURN",
                round(strategy_point - benchmark_point, 12),
                difference_distribution,
            ),
        ]

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "observation_class": observation_class,
        "evidence_state": evidence_state,
        "policy": policy,
        "policy_sha256": policy_sha256,
        "statistical_sample_sha256": statistical_sample_sha256,
        "seed_identity": seed_identity,
        "seed_material_sha256": seed_material_sha256,
        "source_binding": source_binding,
        "replicate_count": replicate_count,
        "sample_summary": sample_summary,
        "intervals": intervals,
        "gaps": gaps,
        "authority": dict(_AUTHORITY),
    }
    evidence["evidence_sha256"] = _canonical_sha256(evidence)
    return evidence


def verify_bootstrap_confidence_evidence_v2(
    evidence: dict[str, Any],
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    strategy_id: str,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    if type(evidence) is not dict:
        _fail("evidence", "must be an exact dict")
    expected = build_bootstrap_confidence_evidence_v2(
        strategy_equity_curve,
        benchmark_equity_curve,
        strategy_id=strategy_id,
        dataset_sha256=dataset_sha256,
        strategy_result_sha256=strategy_result_sha256,
        benchmark_result_sha256=benchmark_result_sha256,
        observation_class=observation_class,
    )
    if evidence != expected:
        _fail(
            "evidence",
            "must match deterministic sample-identity and source-bound evidence",
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": evidence["evidence_state"],
        "evidence_sha256": evidence["evidence_sha256"],
        "statistical_sample_sha256": evidence["statistical_sample_sha256"],
        "seed_material_sha256": evidence["seed_material_sha256"],
        "source_binding_sha256": _canonical_sha256(evidence["source_binding"]),
        "paired_observation_count": evidence["source_binding"][
            "paired_observation_count"
        ],
        "replicate_count": evidence["replicate_count"],
        "interval_count": len(evidence["intervals"]),
        "policy_sha256": evidence["policy_sha256"],
        "seed_source_provenance_included": False,
        "gaps": list(evidence["gaps"]),
        "authority": dict(_AUTHORITY),
    }
