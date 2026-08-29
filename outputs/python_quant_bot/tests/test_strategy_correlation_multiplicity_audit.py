from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_multiplicity_audit as audit
from exchange_terminal.services.strategy_matrix_protocol import canonical_hash


class StrategyCorrelationMultiplicityAuditTests(unittest.TestCase):
    def _pairs(
        self,
        count: int,
        *,
        correlation: float = 0.20,
        effective_observations: float = 60.0,
    ) -> list[dict[str, object]]:
        return [{
            "left_symbol": f"A{index}",
            "right_symbol": f"B{index}",
            "left_cluster_id": f"left_{index}",
            "right_cluster_id": f"right_{index}",
            "correlation": correlation,
            "cross_cluster": True,
            "effective_observations": effective_observations,
            "overlap_observations": 60,
        } for index in range(count)]

    def _source(
        self,
        pairs: list[dict[str, object]],
        *,
        status: str = "PASS",
    ) -> dict[str, object]:
        return {
            "schema_version": "strategy-correlation-uncertainty-audit-v2",
            "status": status,
            "audit_hash": "a" * 64,
            "pair_count": len(pairs),
            "cross_cluster_pair_count": len(pairs),
            "pairs": pairs,
            "external_authenticity_proven": False,
            "profitability_proven": False,
            "performance_claim_allowed": False,
            "parameter_selection_allowed": False,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }

    def _build_verified(self, source: dict[str, object]) -> dict[str, object]:
        with patch.object(
            audit,
            "verify_strategy_correlation_uncertainty_audit",
            return_value={"status": "PASS", "blockers": []},
        ):
            return audit.build_strategy_correlation_multiplicity_audit(source)

    def _verify_replayed(
        self,
        document: dict[str, object],
    ) -> dict[str, object]:
        with patch.object(
            audit,
            "verify_strategy_correlation_uncertainty_audit",
            return_value={"status": "PASS", "blockers": []},
        ):
            return audit.verify_strategy_correlation_multiplicity_audit(document)

    def test_familywise_adjustment_turns_single_pair_high_into_ambiguity(self) -> None:
        document = self._build_verified(
            self._source(self._pairs(10, correlation=0.86))
        )
        self.assertEqual(document["family_size"], 10)
        self.assertAlmostEqual(document["adjusted_critical_value"], 2.807033768344)
        self.assertEqual(document["confirmed_high_cross_cluster_count"], 0)
        self.assertEqual(document["ambiguous_cross_cluster_count"], 10)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "AMBIGUOUS")
        self.assertGreater(
            document["pairs"][0]["adjusted_absolute_interval_lower"],
            0.72,
        )
        self.assertLess(
            document["pairs"][0]["adjusted_absolute_interval_lower"],
            0.75,
        )

    def test_one_pair_retains_ordinary_two_sided_95_percent_interval(self) -> None:
        document = self._build_verified(
            self._source(self._pairs(1, correlation=0.86))
        )
        self.assertEqual(document["family_size"], 1)
        self.assertAlmostEqual(document["adjusted_critical_value"], 1.95996398454)
        self.assertEqual(document["confirmed_high_cross_cluster_count"], 1)
        self.assertEqual(document["ambiguous_cross_cluster_count"], 0)
        self.assertEqual(document["status"], "BLOCK")

    def test_low_cross_cluster_family_passes_descriptively_only(self) -> None:
        document = self._build_verified(self._source(self._pairs(7)))
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["confirmed_low_cross_cluster_count"], 7)
        self.assertEqual(document["first_blocking_tier"], "NONE")
        self.assertTrue(document["requires_new_report_schema"])
        for field in (
            "external_authenticity_proven",
            "profitability_proven",
            "performance_claim_allowed",
            "parameter_selection_allowed",
            "current_writer_activation_allowed",
            "current_admission_allowed",
        ):
            self.assertIs(document[field], False)
        self.assertEqual(
            document["permissions"],
            {"paper_authorized": False, "live_order_allowed": False},
        )
        self.assertEqual(self._verify_replayed(document)["status"], "PASS")

    def test_source_block_is_monotonic_even_when_adjusted_pairs_are_low(self) -> None:
        document = self._build_verified(
            self._source(self._pairs(3), status="BLOCK")
        )
        self.assertEqual(document["confirmed_low_cross_cluster_count"], 3)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "SOURCE_AUDIT_BLOCK")

    def test_insufficient_effective_sample_blocks_before_interval_claim(self) -> None:
        document = self._build_verified(
            self._source(self._pairs(2, effective_observations=11.99))
        )
        self.assertEqual(
            document["insufficient_effective_sample_pair_count"],
            2,
        )
        self.assertEqual(document["first_blocking_tier"], "INSUFFICIENT_EFFECTIVE_SAMPLE")
        self.assertIsNone(document["pairs"][0]["adjusted_interval_lower"])
        self.assertEqual(document["status"], "BLOCK")

    def test_invalid_source_is_redacted_into_replayable_block(self) -> None:
        source = self._source(self._pairs(2))
        source["permissions"] = {
            "paper_authorized": True,
            "live_order_allowed": False,
        }
        document = self._build_verified(source)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["source_status"], "INVALID")
        self.assertIsNone(document["source_uncertainty_audit"])
        self.assertEqual(document["pairs"], [])
        self.assertEqual(document["first_blocking_tier"], "SOURCE_INVALID")
        self.assertNotIn("A0", str(document))
        self.assertEqual(
            audit.verify_strategy_correlation_multiplicity_audit(document)["status"],
            "PASS",
        )

    def test_reseal_policy_pair_and_authority_tamper_are_rejected(self) -> None:
        baseline = self._build_verified(self._source(self._pairs(7)))
        cases = []
        policy = deepcopy(baseline)
        policy["policy"]["familywise_confidence_level"] = 0.90
        policy["policy"]["policy_hash"] = canonical_hash({
            key: value
            for key, value in policy["policy"].items()
            if key != "policy_hash"
        })
        policy["policy_hash"] = policy["policy"]["policy_hash"]
        policy["audit_hash"] = canonical_hash({
            key: value for key, value in policy.items() if key != "audit_hash"
        })
        cases.append(policy)
        pair = deepcopy(baseline)
        pair["pairs"][0]["classification"] = "AMBIGUOUS"
        pair["audit_hash"] = canonical_hash({
            key: value for key, value in pair.items() if key != "audit_hash"
        })
        cases.append(pair)
        authority = deepcopy(baseline)
        authority["permissions"]["paper_authorized"] = True
        authority["audit_hash"] = canonical_hash({
            key: value for key, value in authority.items() if key != "audit_hash"
        })
        cases.append(authority)
        extra = deepcopy(baseline)
        extra["current_writer_allowed"] = False
        extra["audit_hash"] = canonical_hash({
            key: value for key, value in extra.items() if key != "audit_hash"
        })
        cases.append(extra)
        for document in cases:
            with self.subTest(document=document):
                verification = self._verify_replayed(document)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertFalse(verification["current_writer_activation_allowed"])
                self.assertFalse(verification["current_admission_allowed"])
                self.assertFalse(verification["paper_authorized"])
                self.assertFalse(verification["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
