from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from exchange_terminal.services.strategy_hypothesis_preregistration import (
    MECHANISM_FAILURE_METRICS_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
    load_strategy_hypothesis_preregistration,
    verify_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_research import canonical_hash


def draft(
    *,
    strategy_ids: list[str] | None = None,
    generation: str = "TEST_GENERATION",
) -> dict[str, object]:
    return {
        "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
        "hypothesis_id": "test-mechanism-v1",
        "research_generation": generation,
        "strategy_ids": strategy_ids or ["dual_ma"],
        "mechanism_family": "trend persistence with causal confirmation",
        "hypothesis_statement": (
            "A completed-bar trend persistence state should retain positive "
            "benchmark excess after configured costs."
        ),
        "novelty_statement": (
            "This mechanism does not reuse pullback or squeeze entries and "
            "does not retune either falsified strategy family."
        ),
        "mechanism_specific_failure_conditions": [
            "Retire the hypothesis if causal confirmation does not improve fresh excess returns."
        ],
    }


def draft_v2() -> dict[str, object]:
    source = draft()
    source["schema_version"] = (
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
    )
    source["hypothesis_id"] = "test-mechanism-v2"
    source["mechanism_specific_failure_conditions"] = [{
        "condition_id": "validation_excess_lost",
        "evidence_stage": "DEVELOPMENT_SELECTION",
        "metric": "median_validation_excess_return_pct",
        "operator": "LTE",
        "threshold": 0.0,
        "required_action": "BLOCK_RESEARCH",
    }]
    return source


def draft_v3() -> dict[str, object]:
    source = draft_v2()
    source["schema_version"] = (
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
    )
    source["hypothesis_id"] = "test-mechanism-v3"
    source["search_family_id"] = "causal-trend-global-search"
    return source


class StrategyHypothesisPreregistrationTests(unittest.TestCase):
    def test_v3_binds_search_family_without_changing_v2_contract(self) -> None:
        legacy = build_strategy_hypothesis_preregistration(draft_v2())
        sealed = build_strategy_hypothesis_preregistration(draft_v3())

        self.assertNotIn("search_family_id", legacy)
        self.assertEqual(
            sealed["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
        )
        self.assertEqual(
            sealed["search_family_id"],
            "causal-trend-global-search",
        )
        self.assertEqual(
            verify_strategy_hypothesis_preregistration(
                sealed,
                expected_strategy_ids=["dual_ma"],
                expected_research_generation="TEST_GENERATION",
                expected_schema_version=(
                    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                ),
            )["status"],
            "PASS",
        )

        missing = draft_v3()
        missing.pop("search_family_id")
        with self.assertRaisesRegex(ValueError, "strategy_search_family_id"):
            build_strategy_hypothesis_preregistration(missing)
        legacy_with_family = draft_v2()
        legacy_with_family["search_family_id"] = "renamed-family"
        with self.assertRaisesRegex(
            ValueError,
            "legacy_strategy_hypothesis_has_search_family",
        ):
            build_strategy_hypothesis_preregistration(legacy_with_family)

    def test_v2_seals_only_machine_readable_development_conditions(self) -> None:
        sealed = build_strategy_hypothesis_preregistration(draft_v2())

        self.assertEqual(
            sealed["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
        )
        condition = sealed["failure_contract"][
            "mechanism_specific_conditions"
        ][0]
        self.assertEqual(
            set(condition),
            {
                "condition_id",
                "evidence_stage",
                "metric",
                "operator",
                "threshold",
                "required_action",
            },
        )
        self.assertIn(condition["metric"], MECHANISM_FAILURE_METRICS_V2)
        self.assertEqual(
            verify_strategy_hypothesis_preregistration(
                sealed,
                expected_strategy_ids=["dual_ma"],
                expected_research_generation="TEST_GENERATION",
                expected_schema_version=(
                    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
                ),
            )["status"],
            "PASS",
        )
        legacy_binding = verify_strategy_hypothesis_preregistration(
            sealed,
            expected_schema_version=(
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION
            ),
        )
        self.assertIn(
            "strategy_hypothesis_schema_binding_mismatch",
            legacy_binding["blockers"],
        )

    def test_v2_rejects_missing_duplicate_or_unbounded_predicates(self) -> None:
        cases: list[tuple[str, object, str]] = []
        missing = draft_v2()
        missing["mechanism_specific_failure_conditions"] = []
        cases.append(("missing", missing, "mechanism_conditions_invalid"))
        duplicate = draft_v2()
        duplicate["mechanism_specific_failure_conditions"] = [
            *duplicate["mechanism_specific_failure_conditions"],
            deepcopy(duplicate["mechanism_specific_failure_conditions"][0]),
        ]
        cases.append(("duplicate", duplicate, "condition_id_duplicate"))
        for field, value, error in (
            ("metric", "self_reported_profit", "mechanism_metric_invalid"),
            ("operator", "EVAL", "mechanism_operator_invalid"),
            ("threshold", float("nan"), "mechanism_threshold_invalid"),
            ("evidence_stage", "NATURAL_FORWARD_MATURITY", "evidence_stage_invalid"),
            ("required_action", "ALLOW_PAPER", "required_action_invalid"),
        ):
            invalid = draft_v2()
            invalid["mechanism_specific_failure_conditions"][0][field] = value
            cases.append((field, invalid, error))
        for name, source, error in cases:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, error):
                build_strategy_hypothesis_preregistration(source)

    def test_builder_is_deterministic_and_freezes_robustness_and_authority(self) -> None:
        source = draft()
        before = deepcopy(source)

        first = build_strategy_hypothesis_preregistration(source)
        second = build_strategy_hypothesis_preregistration(source)

        self.assertEqual(source, before)
        self.assertEqual(first, second)
        self.assertEqual(
            first["parameter_robustness_contract"]["topology_basis"],
            "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
        )
        self.assertFalse(
            first["parameter_robustness_contract"]["numeric_parameter_distance_claimed"]
        )
        self.assertFalse(
            first["cost_and_time_contract"]["walk_forward_optimization_claim_allowed"]
        )
        self.assertEqual(
            first["holdout_and_forward_contract"]["minimum_natural_forward_outcomes"],
            60,
        )
        self.assertEqual(
            first["holdout_and_forward_contract"]["minimum_executed_rebalances"],
            8,
        )
        self.assertFalse(first["paper_authorized"])
        self.assertFalse(first["live_order_allowed"])
        self.assertEqual(
            verify_strategy_hypothesis_preregistration(
                first,
                expected_strategy_ids=["dual_ma"],
                expected_research_generation="TEST_GENERATION",
            )["status"],
            "PASS",
        )

    def test_falsified_ids_and_unknown_or_weak_drafts_fail_closed(self) -> None:
        for strategy_id in ("trend_pullback", "squeeze_breakout"):
            with self.subTest(strategy_id=strategy_id), self.assertRaisesRegex(
                ValueError,
                "reuses_falsified_strategy_id",
            ):
                build_strategy_hypothesis_preregistration(
                    draft(strategy_ids=[strategy_id])
                )
        unknown = draft()
        unknown["paper_ready"] = False
        with self.assertRaisesRegex(ValueError, "unknown_fields"):
            build_strategy_hypothesis_preregistration(unknown)
        weak = draft()
        weak["novelty_statement"] = "different"
        with self.assertRaisesRegex(ValueError, "field_length_invalid"):
            build_strategy_hypothesis_preregistration(weak)

    def test_verifier_recomputes_semantics_even_after_outer_hash_is_resealed(self) -> None:
        sealed = build_strategy_hypothesis_preregistration(draft())
        tampered = deepcopy(sealed)
        tampered["cost_and_time_contract"]["stressed_return_must_remain_positive"] = False
        content = dict(tampered)
        content.pop("hypothesis_hash")
        tampered["hypothesis_hash"] = canonical_hash(content)

        verification = verify_strategy_hypothesis_preregistration(tampered)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_hypothesis_semantic_or_hash_mismatch",
            verification["blockers"],
        )
        wrong_binding = verify_strategy_hypothesis_preregistration(
            sealed,
            expected_strategy_ids=["macd"],
            expected_research_generation="OTHER",
        )
        self.assertIn(
            "strategy_hypothesis_strategy_binding_mismatch",
            wrong_binding["blockers"],
        )
        self.assertIn(
            "strategy_hypothesis_generation_binding_mismatch",
            wrong_binding["blockers"],
        )

    def test_loader_allows_only_small_project_json_outside_protected_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "docs" / "hypothesis.json"
            source.parent.mkdir()
            source.write_text(json.dumps(draft()), encoding="utf-8")

            loaded = load_strategy_hypothesis_preregistration(
                source,
                project_root=root,
            )
            self.assertEqual(loaded["hypothesis_id"], "test-mechanism-v1")

            protected = root / "runtime" / "hypothesis.json"
            protected.parent.mkdir()
            protected.write_text(json.dumps(draft()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "runtime_path_forbidden"):
                load_strategy_hypothesis_preregistration(
                    protected,
                    project_root=root,
                )

            outside = root.parent / "outside-hypothesis.json"
            with self.assertRaisesRegex(ValueError, "path_outside_project"):
                load_strategy_hypothesis_preregistration(
                    outside,
                    project_root=root,
                )


if __name__ == "__main__":
    unittest.main()
