from __future__ import annotations

import unittest

from exchange_terminal.services.strategy_research import (
    build_legacy_parameter_stability_snapshot_v1,
    build_parameter_stability_snapshot,
)


class StrategyPracticalityTests(unittest.TestCase):
    @staticmethod
    def frozen_variants() -> list[dict[str, object]]:
        return [
            {
                "strategy_id": "dual_ma",
                "variant_label": label,
                "variant_id": f"dual_ma:{label}:frozen",
                "params": {"position": index},
                "param_hash": f"hash-{label}",
            }
            for index, label in enumerate(("fast", "balanced", "slow"), start=1)
        ]

    @classmethod
    def rankings(
        cls,
        scores: tuple[float, float, float],
        eligible: tuple[bool, bool, bool] = (True, True, True),
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for variant, score, is_eligible in zip(cls.frozen_variants(), scores, eligible):
            rows.append({
                **variant,
                "adjusted_score": score,
                "status": "PASS" if is_eligible else "BLOCK",
                "eligible_for_test": is_eligible,
            })
        return rows

    def test_adjacent_eligible_validation_variants_form_a_plateau(self) -> None:
        snapshot = build_parameter_stability_snapshot(
            self.rankings((10.0, 9.0, 0.0)),
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["schema_version"], "strategy-parameter-plateau-v2")
        self.assertEqual(snapshot["status"], "PASS")
        self.assertTrue(snapshot["descriptive_only"])
        self.assertFalse(snapshot["parameter_selection_allowed"])
        strategy = snapshot["strategies"][0]
        self.assertEqual(strategy["adjacent_near_best_variant_ids"], ["dual_ma:balanced:frozen"])
        self.assertEqual(strategy["connected_plateau_ids"], [
            "dual_ma:fast:frozen",
            "dual_ma:balanced:frozen",
        ])
        self.assertEqual(strategy["plateau_width"], 2)

    def test_non_adjacent_high_endpoints_are_not_a_plateau(self) -> None:
        snapshot = build_parameter_stability_snapshot(
            self.rankings((10.0, 0.0, 9.0)),
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["status"], "REVIEW")
        self.assertTrue(snapshot["strategies"][0]["peak_only"])
        self.assertIn(
            "parameter_stability_peak_without_adjacent_plateau",
            snapshot["blockers"],
        )

    def test_ineligible_neighbor_cannot_make_a_plateau_pass(self) -> None:
        snapshot = build_parameter_stability_snapshot(
            self.rankings((10.0, 9.0, 0.0), (True, False, True)),
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["status"], "REVIEW")
        self.assertEqual(snapshot["strategies"][0]["near_best_scored_variant_count"], 2)
        self.assertEqual(snapshot["strategies"][0]["near_best_eligible_variant_count"], 1)
        self.assertEqual(snapshot["strategies"][0]["adjacent_near_best_variant_count"], 0)

    def test_highest_scored_ineligible_variant_is_exposed(self) -> None:
        snapshot = build_parameter_stability_snapshot(
            self.rankings((10.0, 9.0, 8.0), (False, True, True)),
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["status"], "REVIEW")
        self.assertEqual(snapshot["strategies"][0]["best_variant_id"], "dual_ma:fast:frozen")
        self.assertFalse(snapshot["strategies"][0]["best_variant_eligible"])
        self.assertIn("parameter_stability_best_variant_ineligible", snapshot["blockers"])

    def test_frozen_topology_and_ranking_must_cover_each_other(self) -> None:
        snapshot = build_parameter_stability_snapshot(
            self.rankings((10.0, 9.0, 8.0))[:-1],
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["status"], "BLOCK")
        self.assertIn("parameter_stability_ranking_coverage_missing", snapshot["blockers"])

    def test_frozen_variant_label_is_part_of_topology_identity(self) -> None:
        rankings = self.rankings((10.0, 9.0, 8.0))
        rankings[1]["variant_label"] = "renamed-after-freeze"
        snapshot = build_parameter_stability_snapshot(
            rankings,
            frozen_variants=self.frozen_variants(),
        )

        self.assertEqual(snapshot["status"], "BLOCK")
        self.assertIn("parameter_stability_ranking_identity_mismatch", snapshot["blockers"])
        self.assertIn(
            "dual_ma:balanced:frozen:variant_label",
            snapshot["strategies"][0]["identity_mismatches"],
        )

    def test_v1_builder_remains_available_only_for_historical_verification(self) -> None:
        snapshot = build_legacy_parameter_stability_snapshot_v1([
            {"strategy_id": "dual_ma", "variant_id": "fast", "adjusted_score": 10.0, "eligible_for_test": True},
            {"strategy_id": "dual_ma", "variant_id": "balanced", "adjusted_score": 9.0, "eligible_for_test": True},
            {"strategy_id": "dual_ma", "variant_id": "slow", "adjusted_score": 8.0, "eligible_for_test": True},
        ])

        self.assertEqual(snapshot["schema_version"], "strategy-parameter-plateau-v1")
        self.assertEqual(snapshot["status"], "PASS")
        self.assertFalse(snapshot["parameter_selection_allowed"])


if __name__ == "__main__":
    unittest.main()
