from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import unittest
from unittest.mock import patch

from hakimi_research.validation_evidence import (
    FORMAL_SEARCH_LINEAGE_PRODUCER_ID,
    VALIDATION_EVIDENCE_VERSION,
    ValidationEvidenceError,
    build_validation_evidence,
    render_verified_research_markdown,
    verify_validation_evidence,
)
from hakimi_research.distribution_evidence import build_distribution_evidence


EXPERIMENT_CONTEXT = {
    "git_commit_sha": "a" * 40,
    "git_worktree_clean": True,
    "dependency_lock_hash": "b" * 64,
    "dependency_lock_fully_pinned": True,
    "dependency_lock_name": "requirements.research.lock",
    "random_seed": 17,
    "runtime_version": "python-test",
}


BASE_MARKDOWN = """# Frozen Evaluation Report

- WALK_FORWARD_NOT_BOUND_TO_ADR0509
- PARAMETER_STABILITY_NOT_BOUND_TO_ADR0509
- MULTIPLE_TESTING_LINEAGE_NOT_BOUND_TO_ADR0509
- MARKET_REGIME_SLICES_NOT_BOUND_TO_ADR0509
- TAIL_AND_DISTRIBUTION_METRICS_NOT_AVAILABLE
"""
def _synthetic_backtest_result() -> dict[str, object]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    equity = 10_000.0
    curve = []
    for index in range(420):
        if index and index % 19 == 0:
            equity -= 18.0
        elif index % 7 == 0:
            equity += 8.0
        else:
            equity += 1.5
        curve.append({"time": (start + timedelta(days=index)).isoformat(), "equity": round(equity, 2)})
    fills = [
        {"action": "BUY", "quantity": 10.0, "price": 100.0, "pnl": 0.0, "fill_time": curve[10]["time"]},
        {"action": "SELL", "quantity": 10.0, "price": 105.0, "pnl": 48.0, "fill_time": curve[30]["time"]},
        {"action": "BUY", "quantity": 8.0, "price": 103.0, "pnl": 0.0, "fill_time": curve[50]["time"]},
        {"action": "SELL", "quantity": 8.0, "price": 100.0, "pnl": -26.0, "fill_time": curve[80]["time"]},
        {"action": "BUY", "quantity": 6.0, "price": 101.0, "pnl": 0.0, "fill_time": curve[100]["time"]},
        {"action": "SELL", "quantity": 6.0, "price": 104.0, "pnl": 16.0, "fill_time": curve[130]["time"]},
    ]
    return {
        "annualized_return": 0.05,
        "equity_curve": curve,
        "fills": fills,
    }


REPORT = {
    "report_version": "synthetic-v1",
    "observations": [0.1, -0.2],
    "authority": False,
    "backtest_result": _synthetic_backtest_result(),
}
PROTOCOL = {"protocol_version": "synthetic-protocol-v1"}
DATA = {"dataset_hash": "synthetic"}
CONFIG = {"config_hash": "synthetic"}


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _period(start: int, end: int) -> dict[str, int]:
    return {"start_index": start, "end_index": end}


def _window(
    window_id: str,
    offset: int,
    parameter_id: str,
    *,
    status: str = "OBSERVED",
) -> dict[str, object]:
    observed = status == "OBSERVED"
    return {
        "window_id": window_id,
        "train": _period(offset, offset + 9),
        "validation": _period(offset + 12, offset + 19),
        "frozen_test": _period(offset + 21, offset + 29),
        "purge_bars": 2,
        "embargo_bars": 1,
        "selected_parameter_id": parameter_id,
        "status": status,
        "strategy_total_return": "0.04" if observed else None,
        "benchmark_total_return": "0.02" if observed else None,
        "strategy_result_sha256": _hash(f"{window_id}-strategy") if observed else None,
        "benchmark_result_sha256": _hash(f"{window_id}-benchmark") if observed else None,
        "failure_code": None if observed else "SYNTHETIC_WINDOW_FAILURE",
    }


def _neighbor(parameter_id: str, metric: str, *, status: str = "OBSERVED") -> dict[str, object]:
    observed = status == "OBSERVED"
    return {
        "parameter_id": parameter_id,
        "distance_fraction": "0.10",
        "status": status,
        "frozen_excess_return": metric if observed else None,
        "result_sha256": _hash(f"neighbor-{parameter_id}") if observed else None,
        "failure_code": None if observed else "SYNTHETIC_NEIGHBOR_FAILURE",
    }


def _regime(regime_id: str, *, status: str = "OBSERVED") -> dict[str, object]:
    observed = status == "OBSERVED"
    return {
        "regime_id": regime_id,
        "status": status,
        "strategy_total_return": "0.03" if observed else None,
        "benchmark_total_return": "0.01" if observed else None,
        "observation_sha256": _hash(f"regime-{regime_id}") if observed else None,
        "gap_code": None if observed else "SYNTHETIC_REGIME_GAP",
    }


def _formal_search_lineage() -> dict[str, object]:
    return {
        "producer_id": FORMAL_SEARCH_LINEAGE_PRODUCER_ID,
        "producer_schema_version": "synthetic-search-lineage-v2",
        "artifact_sha256": _hash("formal-search-lineage-artifact"),
        "lineage_sha256": _hash("formal-search-lineage-payload"),
        "search_family_id": "synthetic-search-family-v1",
        "current_trial_count": 3,
        "cumulative_trial_count": 3,
        "prior_registration_count": 0,
    }


def _distribution_evidence() -> dict[str, object]:
    return build_distribution_evidence(
        REPORT,
        source_result_path=["backtest_result"],
        periods_per_year=252,
    )


def _components() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    walk_forward = {"windows": [_window("window-2", 10, "parameter-2"), _window("window-1", 0, "parameter-1")]}
    parameter_stability = {
        "selected_parameter_id": "parameter-1",
        "selected_frozen_excess_return": "0.04",
        "selected_result_sha256": _hash("selected-parameter-1"),
        "max_abs_degradation": "0.02",
        "minimum_neighbor_count": 2,
        "minimum_stable_neighbor_count": 2,
        "neighbors": [_neighbor("parameter-3", "0.039"), _neighbor("parameter-2", "0.03")],
    }
    multiple_testing = {
        "preregistered_trial_ids": ["parameter-3", "parameter-1", "parameter-2"],
        "trial_outcomes": [
            {"trial_id": "parameter-3", "status": "FAILED", "result_sha256": None, "failure_code": "SYNTHETIC_TRIAL_FAILURE", "decision_status": None, "decision_blockers": []},
            {"trial_id": "parameter-2", "status": "OBSERVED", "result_sha256": _hash("trial-2"), "failure_code": None, "decision_status": "BLOCK", "decision_blockers": ["SYNTHETIC_SCORE_BLOCK"]},
            {"trial_id": "parameter-1", "status": "OBSERVED", "result_sha256": _hash("trial-1"), "failure_code": None, "decision_status": "PASS", "decision_blockers": []},
        ],
        "selected_parameter_id": "parameter-1",
        "selection_rule": "preregistered validation score, then lexical identifier",
        "producer_report_sha256": _hash("synthetic-trial-producer-report"),
    }
    market_regimes = {
        "slices": [
            _regime("HIGH_VOLATILITY"),
            _regime("RANGE"),
            _regime("BEAR"),
            _regime("BULL"),
        ]
    }
    return walk_forward, parameter_stability, multiple_testing, market_regimes


def _build(
    *,
    report: dict[str, object] | None = None,
    mutate=None,
) -> dict[str, object]:
    components = list(_components())
    if mutate is not None:
        mutate(*components)
    return build_validation_evidence(
        REPORT if report is None else report,
        experiment_id="synthetic-experiment-v1",
        formal_search_lineage=_formal_search_lineage(),
        distribution_evidence=_distribution_evidence(),
        walk_forward=components[0],
        parameter_stability=components[1],
        multiple_testing=components[2],
        market_regimes=components[3],
    )


class ValidationEvidenceReportV1Tests(unittest.TestCase):
    def test_build_is_deterministic_and_normalizes_record_order(self) -> None:
        first = _build()
        second = _build()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], VALIDATION_EVIDENCE_VERSION)
        self.assertEqual(first["formal_search_lineage"]["current_trial_count"], 3)
        self.assertEqual([item["window_id"] for item in first["walk_forward"]["windows"]], ["window-1", "window-2"])
        self.assertEqual(first["multiple_testing"]["preregistered_trial_ids"], ["parameter-1", "parameter-2", "parameter-3"])
        self.assertEqual([item["regime_id"] for item in first["market_regimes"]["slices"]], ["BULL", "BEAR", "RANGE", "HIGH_VOLATILITY"])

    def test_verify_reports_bound_observations_and_preserved_failed_trial(self) -> None:
        summary = verify_validation_evidence(_build(), REPORT)
        self.assertEqual(summary["walk_forward"]["state"], "OBSERVED")
        self.assertEqual(summary["parameter_stability"]["state"], "OBSERVED")
        self.assertEqual(summary["multiple_testing"]["failed_count"], 1)
        self.assertEqual(summary["market_regimes"]["state"], "OBSERVED")
        self.assertEqual(summary["permission"], "RESEARCH_ONLY")

    def test_renderer_composes_verified_base_and_neutral_evidence_sections(self) -> None:
        evidence = _build()
        with patch("hakimi_research.validation_evidence.render_frozen_evaluation_markdown", return_value=BASE_MARKDOWN) as base_renderer:
            rendered = render_verified_research_markdown(
                REPORT,
                PROTOCOL,
                DATA,
                CONFIG,
                evidence,
                experiment_context=EXPERIMENT_CONTEXT,
            )
        base_renderer.assert_called_once_with(
            REPORT,
            PROTOCOL,
            DATA,
            CONFIG,
            experiment_context=EXPERIMENT_CONTEXT,
        )
        self.assertIn("WALK_FORWARD_BOUND_BY_VALIDATION_EVIDENCE_V1", rendered)
        self.assertNotIn("WALK_FORWARD_NOT_BOUND_TO_ADR0509", rendered)
        self.assertIn("SYNTHETIC_TRIAL_FAILURE", rendered)
        self.assertIn("SYNTHETIC_SCORE_BLOCK", rendered)
        self.assertIn("TAIL_AND_DISTRIBUTION_METRICS_BOUND_BY_DISTRIBUTION_EVIDENCE_V1", rendered)
        self.assertNotIn("TAIL_AND_DISTRIBUTION_METRICS_NOT_AVAILABLE", rendered)
        self.assertIn("## Tail and Distribution", rendered)
        self.assertIn("paper_authorized: false", rendered)
        self.assertIn("live_authorized: false", rendered)
        self.assertNotIn("READY", rendered)

    def test_source_report_mutation_breaks_identity_binding(self) -> None:
        evidence = _build()
        changed = copy.deepcopy(REPORT)
        changed["observations"][0] = 0.2
        with self.assertRaisesRegex(ValidationEvidenceError, "source_report_sha256"):
            verify_validation_evidence(evidence, changed)

    def test_evidence_mutation_breaks_evidence_digest(self) -> None:
        evidence = _build()
        evidence["walk_forward"]["windows"][0]["strategy_total_return"] = "0.05"
        with self.assertRaisesRegex(ValidationEvidenceError, "evidence_sha256"):
            verify_validation_evidence(evidence, REPORT)

    def test_exact_str_subclass_is_rejected_before_identity_methods(self) -> None:
        class EvilStr(str):
            def encode(self, *args, **kwargs):
                raise AssertionError("subclass encode must not run")

        walk, stability, multiplicity, regimes = _components()
        with self.assertRaisesRegex(ValidationEvidenceError, "experiment_id"):
            build_validation_evidence(
                REPORT,
                experiment_id=EvilStr("synthetic-experiment-v1"),
                formal_search_lineage=_formal_search_lineage(),
                distribution_evidence=_distribution_evidence(),
                walk_forward=walk,
                parameter_stability=stability,
                multiple_testing=multiplicity,
                market_regimes=regimes,
            )

    def test_nested_list_subclass_is_rejected(self) -> None:
        class EvilList(list):
            pass

        walk, stability, multiplicity, regimes = _components()
        walk["windows"] = EvilList(walk["windows"])
        with self.assertRaisesRegex(ValidationEvidenceError, "unsupported non-native type"):
            build_validation_evidence(
                REPORT,
                experiment_id="synthetic-experiment-v1",
                formal_search_lineage=_formal_search_lineage(),
                distribution_evidence=_distribution_evidence(),
                walk_forward=walk,
                parameter_stability=stability,
                multiple_testing=multiplicity,
                market_regimes=regimes,
            )

    def test_report_dict_subclass_is_rejected(self) -> None:
        class EvilDict(dict):
            pass

        with self.assertRaisesRegex(ValidationEvidenceError, "unsupported non-native type"):
            _build(report=EvilDict(REPORT))

    def test_nonfinite_report_float_is_rejected(self) -> None:
        report = copy.deepcopy(REPORT)
        report["observations"][0] = float("nan")
        with self.assertRaisesRegex(ValidationEvidenceError, "finite"):
            _build(report=report)

    def test_purge_boundary_violation_is_rejected(self) -> None:
        def mutate(walk, *_):
            walk["windows"][1]["purge_bars"] = 3

        with self.assertRaisesRegex(ValidationEvidenceError, "purge_bars"):
            _build(mutate=mutate)

    def test_embargo_boundary_violation_is_rejected(self) -> None:
        def mutate(walk, *_):
            walk["windows"][1]["embargo_bars"] = 2

        with self.assertRaisesRegex(ValidationEvidenceError, "embargo_bars"):
            _build(mutate=mutate)

    def test_duplicate_window_identifier_is_rejected(self) -> None:
        def mutate(walk, *_):
            walk["windows"][0]["window_id"] = "window-1"

        with self.assertRaisesRegex(ValidationEvidenceError, "window_id values must be unique"):
            _build(mutate=mutate)

    def test_missing_trial_outcome_is_rejected(self) -> None:
        def mutate(_walk, _stability, multiplicity, _regimes):
            multiplicity["trial_outcomes"].pop()

        with self.assertRaisesRegex(ValidationEvidenceError, "account for every preregistered trial"):
            _build(mutate=mutate)

    def test_failed_trial_cannot_be_selected(self) -> None:
        def mutate(_walk, stability, multiplicity, _regimes):
            multiplicity["selected_parameter_id"] = "parameter-3"
            stability["selected_parameter_id"] = "parameter-3"

        with self.assertRaisesRegex(ValidationEvidenceError, "OBSERVED preregistered trial"):
            _build(mutate=mutate)

    def test_stability_shortfall_is_rendered_as_gap_not_erased(self) -> None:
        def mutate(_walk, stability, _multiplicity, _regimes):
            stability["max_abs_degradation"] = "0.001"

        evidence = _build(mutate=mutate)
        summary = verify_validation_evidence(evidence, REPORT)
        self.assertEqual(summary["parameter_stability"]["state"], "GAP")
        self.assertIn("PARAMETER_STABILITY_OUTCOME_GAP", summary["gaps"])

    def test_failed_window_and_missing_regime_remain_visible(self) -> None:
        def mutate(walk, _stability, _multiplicity, regimes):
            walk["windows"][0] = _window("window-2", 10, "parameter-2", status="FAILED")
            regimes["slices"][0] = _regime("HIGH_VOLATILITY", status="GAP")

        evidence = _build(mutate=mutate)
        summary = verify_validation_evidence(evidence, REPORT)
        self.assertEqual(summary["walk_forward"]["state"], "GAP")
        self.assertEqual(summary["market_regimes"]["state"], "GAP")
        with patch("hakimi_research.validation_evidence.render_frozen_evaluation_markdown", return_value=BASE_MARKDOWN):
            rendered = render_verified_research_markdown(
                REPORT,
                PROTOCOL,
                DATA,
                CONFIG,
                evidence,
                experiment_context=EXPERIMENT_CONTEXT,
            )
        self.assertIn("SYNTHETIC_WINDOW_FAILURE", rendered)
        self.assertIn("SYNTHETIC_REGIME_GAP", rendered)
        self.assertIn("UNKNOWN", rendered)

    def test_true_authority_is_rejected_even_before_digest_check(self) -> None:
        evidence = _build()
        evidence["authority"]["paper_authorized"] = True
        with self.assertRaisesRegex(ValidationEvidenceError, "must be exact false"):
            verify_validation_evidence(evidence, REPORT)

    def test_renderer_fails_closed_when_base_coverage_contract_drifts(self) -> None:
        evidence = _build()
        with patch("hakimi_research.validation_evidence.render_frozen_evaluation_markdown", return_value="# drifted base"):
            with self.assertRaisesRegex(ValidationEvidenceError, "missing expected ADR0509 coverage marker"):
                render_verified_research_markdown(
                    REPORT,
                    PROTOCOL,
                    DATA,
                    CONFIG,
                    evidence,
                    experiment_context=EXPERIMENT_CONTEXT,
                )


if __name__ == "__main__":
    unittest.main()
