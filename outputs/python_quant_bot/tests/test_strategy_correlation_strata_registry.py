import copy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    build_strategy_correlation_strata_registry_asset,
    verify_strategy_correlation_strata_registry_asset,
    verify_strategy_correlation_strata_registry_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationStrataRegistryTests(unittest.TestCase):
    SOURCE_HASH = "a" * 64

    def _source(self):
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-aaa", "members": ["AAA"]},
                {"cluster_id": "cluster-bbb", "members": ["BBB"]},
            ]
        )
        dimensions = [
            {
                "dimension_id": "sector",
                "strata": [
                    {
                        "stratum_id": "sector-a",
                        "cluster_ids": ["cluster-aaa"],
                    },
                    {
                        "stratum_id": "sector-b",
                        "cluster_ids": ["cluster-bbb"],
                    },
                ],
            }
        ]
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            dimensions,
        )
        asset = build_strategy_correlation_strata_registry_asset(
            preregistration,
            dimensions,
            registry_id="strata-registry-candidate-1",
            classification_source="external-classification-snapshot",
            classification_source_version="2026-07-31",
            classification_source_hash=self.SOURCE_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        return preregistration, dimensions, registration, asset

    def _assessment(self, preregistration, registration, asset, **overrides):
        values = {
            "selection_cutoff_date": "2026-08-02",
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_classification_source_hash": self.SOURCE_HASH,
        }
        values.update(overrides)
        return assess_strategy_correlation_strata_registry_binding(
            asset,
            registration,
            preregistration,
            **values,
        )

    def test_registry_asset_is_canonical_and_exactly_rebuildable(self):
        preregistration, _, _, asset = self._source()
        self.assertEqual(asset["status"], "FROZEN_CANDIDATE")
        self.assertFalse(asset["methodology"]["selection_returns_used"])
        self.assertFalse(asset["methodology"]["post_selection_edits_allowed"])
        self.assertEqual(
            verify_strategy_correlation_strata_registry_asset(
                asset,
                source_preregistration=preregistration,
            )["status"],
            "PASS",
        )

    def test_registry_builder_rejects_invalid_provenance_and_timing(self):
        preregistration, dimensions, _, _ = self._source()
        cases = [
            {"classification_source_hash": "not-a-hash"},
            {
                "effective_date": "2026-08-02",
                "frozen_at": "2026-08-01T00:00:00Z",
            },
            {"frozen_at": "2026-08-01T00:00:00+00:00"},
        ]
        base = {
            "registry_id": "candidate",
            "classification_source": "external-source",
            "classification_source_version": "v1",
            "classification_source_hash": self.SOURCE_HASH,
            "effective_date": "2026-07-31",
            "frozen_at": "2026-08-01T00:00:00Z",
        }
        for override in cases:
            with self.subTest(override=override):
                values = dict(base)
                values.update(override)
                with self.assertRaises(ValueError):
                    build_strategy_correlation_strata_registry_asset(
                        preregistration,
                        dimensions,
                        **values,
                    )

    def test_binding_requires_all_frozen_provenance_facts(self):
        preregistration, _, registration, asset = self._source()
        assessment = self._assessment(
            preregistration,
            registration,
            asset,
        )
        self.assertEqual(assessment["status"], "BOUND")
        self.assertTrue(all(assessment["facts"].values()))
        self.assertFalse(assessment["formal_registry_activation_allowed"])
        self.assertFalse(assessment["permissions"]["paper_authorized"])
        self.assertFalse(assessment["permissions"]["live_order_allowed"])

    def test_resealed_source_hash_is_caught_by_external_expectation(self):
        preregistration, _, registration, asset = self._source()
        tampered = copy.deepcopy(asset)
        tampered["classification_source"]["content_hash"] = "b" * 64
        tampered["registry_asset_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered.items()
                if key != "registry_asset_hash"
            }
        )
        self.assertEqual(
            verify_strategy_correlation_strata_registry_asset(
                tampered,
                source_preregistration=preregistration,
            )["status"],
            "PASS",
        )
        assessment = self._assessment(
            preregistration,
            registration,
            tampered,
            expected_registry_asset_hash=tampered["registry_asset_hash"],
        )
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn(
            "classification_source_hash_binding_invalid",
            assessment["blockers"],
        )

    def test_registry_must_be_effective_and_frozen_before_selection(self):
        preregistration, _, registration, asset = self._source()
        assessment = self._assessment(
            preregistration,
            registration,
            asset,
            selection_cutoff_date="2026-08-01",
        )
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn(
            "registry_not_frozen_before_selection",
            assessment["blockers"],
        )

    def test_registry_dimensions_must_exactly_match_registration(self):
        preregistration, _, registration, _ = self._source()
        different_dimensions = [
            {
                "dimension_id": "sector",
                "strata": [
                    {
                        "stratum_id": "shared",
                        "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                    }
                ],
            }
        ]
        different_asset = build_strategy_correlation_strata_registry_asset(
            preregistration,
            different_dimensions,
            registry_id="different",
            classification_source="external-source",
            classification_source_version="v1",
            classification_source_hash=self.SOURCE_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        assessment = self._assessment(
            preregistration,
            registration,
            different_asset,
            expected_registry_asset_hash=different_asset[
                "registry_asset_hash"
            ],
        )
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn(
            "strata_dimensions_binding_invalid",
            assessment["blockers"],
        )

    def test_resealed_authority_and_assessment_tampering_are_blocked(self):
        preregistration, _, registration, asset = self._source()
        tampered_asset = copy.deepcopy(asset)
        tampered_asset["formal_registry_activation_allowed"] = True
        tampered_asset["registry_asset_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered_asset.items()
                if key != "registry_asset_hash"
            }
        )
        self.assertEqual(
            verify_strategy_correlation_strata_registry_asset(
                tampered_asset,
                source_preregistration=preregistration,
            )["status"],
            "BLOCK",
        )
        assessment = self._assessment(
            preregistration,
            registration,
            asset,
        )
        self.assertEqual(
            verify_strategy_correlation_strata_registry_binding(
                assessment,
                registry_asset=asset,
                registration=registration,
                source_preregistration=preregistration,
                selection_cutoff_date="2026-08-02",
                expected_registry_asset_hash=asset["registry_asset_hash"],
                expected_classification_source_hash=self.SOURCE_HASH,
            )["status"],
            "PASS",
        )
        tampered_assessment = copy.deepcopy(assessment)
        tampered_assessment["formal_registry_activation_allowed"] = True
        tampered_assessment["assessment_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered_assessment.items()
                if key != "assessment_hash"
            }
        )
        self.assertEqual(
            verify_strategy_correlation_strata_registry_binding(
                tampered_assessment,
                registry_asset=asset,
                registration=registration,
                source_preregistration=preregistration,
                selection_cutoff_date="2026-08-02",
                expected_registry_asset_hash=asset["registry_asset_hash"],
                expected_classification_source_hash=self.SOURCE_HASH,
            )["status"],
            "BLOCK",
        )


if __name__ == "__main__":
    unittest.main()
