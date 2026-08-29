from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_complete_link_projection import (
    build_strategy_correlation_complete_link_migration_public_summary,
    verify_strategy_correlation_complete_link_migration_public_summary,
)
from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    build_strategy_correlation_complete_link_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    build_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    build_strategy_correlation_multiplicity_family_registration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)


class StrategyCorrelationCompleteLinkProjectionTests(unittest.TestCase):
    @staticmethod
    def _registration() -> dict:
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "AB", "members": ["A", "B"]},
                {"cluster_id": "C", "members": ["C"]},
            ]
        )
        source_v2 = build_strategy_correlation_protocol_registration_v2(
            preregistration,
            cutoff_date="2026-01-01",
            selection_alignment_input_hash="a" * 64,
            evaluations=[
                {"strategy_id": "S", "variant_id": "V", "lane": "RAW_EXCESS"}
            ],
        )
        family = build_strategy_correlation_multiplicity_family_registration(source_v2)
        source_v3 = build_strategy_correlation_multiplicity_protocol_registration(family)
        return build_strategy_correlation_complete_link_protocol_registration(source_v3)

    def test_verified_registration_projects_neutral_migration_ledger(self) -> None:
        registration = self._registration()
        summary = build_strategy_correlation_complete_link_migration_public_summary(
            registration
        )
        self.assertEqual(summary["status"], "OBSERVED")
        self.assertEqual(summary["source"], "PROTOCOL_REGISTRATION_V4")
        self.assertEqual(summary["gap"], "FORMAL_REGISTRY_AND_WRITER_PENDING")
        self.assertEqual(summary["maturity"], "CONSUMER_ONLY")
        self.assertEqual(summary["permission"], "RESEARCH_ONLY")
        self.assertEqual(summary["absolute_pearson_threshold"], 0.75)
        self.assertEqual(summary["minimum_pair_overlap"], 40)
        self.assertFalse(summary["formal_registry_bound"])
        self.assertFalse(summary["writer_available"])
        self.assertFalse(summary["current_admission_allowed"])
        self.assertFalse(summary["profitability_proven"])
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])

    def test_invalid_source_projects_unknown_without_policy_claims(self) -> None:
        summary = build_strategy_correlation_complete_link_migration_public_summary({})
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["source"], "UNVERIFIED")
        self.assertEqual(summary["gap"], "SOURCE_UNVERIFIED")
        self.assertEqual(summary["maturity"], "UNKNOWN")
        self.assertIsNone(summary["target_report_schema_version"])
        self.assertIsNone(summary["absolute_pearson_threshold"])
        self.assertIsNone(summary["minimum_pair_overlap"])

    def test_public_summary_contains_no_identity_hash_or_raw_registration(self) -> None:
        summary = build_strategy_correlation_complete_link_migration_public_summary(
            self._registration()
        )
        forbidden_keys = {
            "registration_hash",
            "source_registration_hash",
            "cluster_preregistration_hash",
            "family_registration_hash",
            "strategy_id",
            "variant_id",
            "lane",
            "symbols",
            "preregistration",
            "source_registration",
        }
        forbidden_values = {"A", "B", "C", "S", "V", "RAW_EXCESS"}

        def audit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for item in value.values():
                    audit(item)
            elif isinstance(value, list):
                for item in value:
                    audit(item)
            elif isinstance(value, str):
                self.assertNotIn(value, forbidden_values)

        audit(summary)

    def test_exact_verifier_rejects_authority_tamper(self) -> None:
        registration = self._registration()
        summary = build_strategy_correlation_complete_link_migration_public_summary(
            registration
        )
        tampered = copy.deepcopy(summary)
        tampered["paper_authorized"] = True
        verification = verify_strategy_correlation_complete_link_migration_public_summary(
            tampered,
            source_registration=registration,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_source_tamper_degrades_to_unknown(self) -> None:
        registration = self._registration()
        registration["writer_available"] = True
        summary = build_strategy_correlation_complete_link_migration_public_summary(
            registration
        )
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertFalse(summary["writer_available"])


if __name__ == "__main__":
    unittest.main()
