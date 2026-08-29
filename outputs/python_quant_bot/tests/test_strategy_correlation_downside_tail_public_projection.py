from __future__ import annotations

import copy
import json
import re
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_downside_tail_gate import (
    build_strategy_correlation_downside_tail_registration,
    evaluate_strategy_correlation_downside_tail_gate,
)
from exchange_terminal.services.strategy_correlation_downside_tail_protocol import (
    assess_strategy_correlation_downside_tail_protocol_binding,
    build_strategy_correlation_downside_tail_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_downside_tail_public_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_downside_tail_public_summary,
    verify_strategy_correlation_downside_tail_public_summary,
)
from exchange_terminal.services.strategy_correlation_downside_tail_report_consumer import (
    consume_strategy_correlation_downside_tail_evaluation,
)


class StrategyCorrelationDownsideTailPublicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.registration = build_strategy_correlation_downside_tail_registration(
            registration_id="downside-tail-public-1",
            stratum_by_identity={"A": "S1", "B": "S2"},
        )
        self.protocol = build_strategy_correlation_downside_tail_protocol_registration(
            self.registration
        )

    def _observations(self, *, joint=False, count=60, prefix="obs"):
        rows = []
        for index in range(count):
            left_tail = index < 12
            right_tail = index < 12 if joint else 12 <= index < 24
            rows.append(
                {
                    "observation_id": f"{prefix}-{index:03d}",
                    "returns": {
                        "A": -1.0 if left_tail else (0.0 if index % 2 == 0 else 2.0),
                        "B": -1.0 if right_tail else (2.0 if index % 2 == 0 else 0.0),
                    },
                }
            )
        return rows

    def _inputs(self, *, joint=False, count=60, prefix="obs"):
        evaluation = evaluate_strategy_correlation_downside_tail_gate(
            self.registration,
            self._observations(joint=joint, count=count, prefix=prefix),
            expected_registration_hash=self.registration["registration_hash"],
        )
        receipt = consume_strategy_correlation_downside_tail_evaluation(
            evaluation,
            registration=self.registration,
            expected_registration_hash=self.registration["registration_hash"],
            expected_evaluation_hash=evaluation["evaluation_hash"],
        )
        assessment = assess_strategy_correlation_downside_tail_protocol_binding(
            self.protocol,
            evaluation,
            receipt,
            source_registration=self.registration,
            expected_protocol_hash=self.protocol["protocol_hash"],
            expected_registration_hash=self.registration["registration_hash"],
            expected_evaluation_hash=evaluation["evaluation_hash"],
        )
        return {
            "binding_assessment": assessment,
            "protocol_registration": self.protocol,
            "evaluation": evaluation,
            "consumer_receipt": receipt,
            "source_registration": self.registration,
            "expected_protocol_hash": self.protocol["protocol_hash"],
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_evaluation_hash": evaluation["evaluation_hash"],
        }

    def test_not_supplied_is_distinct_from_unknown(self):
        absent = build_strategy_correlation_downside_tail_public_summary()
        invalid = build_strategy_correlation_downside_tail_public_summary({})

        self.assertEqual(absent["source"]["state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["source"]["state"], "UNKNOWN")
        self.assertNotEqual(absent, invalid)

    def test_observed_pass_is_public_candidate_only(self):
        summary = build_strategy_correlation_downside_tail_public_summary(**self._inputs())

        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(summary["source"]["state"], "OBSERVED")
        self.assertEqual(summary["gap"]["gate_decision"], "PASS")
        self.assertEqual(summary["gap"]["binding_status"], "CANDIDATE_BOUND")
        self.assertEqual(summary["maturity"]["state"], "CANDIDATE_BOUND_NOT_FORMAL")
        self.assertFalse(summary["permission"]["count_as_independent_allowed"])

    def test_observed_block_remains_visible(self):
        summary = build_strategy_correlation_downside_tail_public_summary(
            **self._inputs(joint=True)
        )

        self.assertEqual(summary["source"]["state"], "OBSERVED")
        self.assertEqual(summary["gap"]["gate_decision"], "BLOCK")
        self.assertEqual(summary["source"]["coupled_pair_count"], 1)
        self.assertEqual(summary["gap"]["binding_status"], "CANDIDATE_BOUND")

    def test_valid_unknown_source_is_candidate_blocked(self):
        summary = build_strategy_correlation_downside_tail_public_summary(
            **self._inputs(count=59)
        )

        self.assertEqual(summary["source"]["state"], "UNKNOWN")
        self.assertEqual(summary["gap"]["gate_decision"], "BLOCK")
        self.assertEqual(summary["gap"]["binding_status"], "CANDIDATE_BLOCKED")
        self.assertEqual(summary["maturity"]["state"], "CANDIDATE_BLOCKED_NOT_FORMAL")

    def test_wrong_expected_protocol_hash_projects_unknown(self):
        inputs = self._inputs()
        inputs["expected_protocol_hash"] = "0" * 64
        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)

        self.assertEqual(summary["source"]["state"], "UNKNOWN")
        self.assertEqual(summary["gap"]["binding_status"], "UNKNOWN")

    def test_resealed_assessment_decision_tamper_projects_unknown(self):
        inputs = self._inputs()
        tampered = copy.deepcopy(inputs["binding_assessment"])
        tampered["gate_decision"] = "BLOCK"
        tampered.pop("assessment_hash")
        inputs["binding_assessment"] = seal_strict_canonical_document(
            tampered,
            "assessment_hash",
        )

        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)
        self.assertEqual(summary["source"]["state"], "UNKNOWN")

    def test_exact_public_summary_verifies(self):
        inputs = self._inputs(joint=True)
        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)
        verification = verify_strategy_correlation_downside_tail_public_summary(
            summary,
            **inputs,
        )

        self.assertEqual(verification["verification_status"], "PASS")
        self.assertEqual(verification["public_state"], "OBSERVED")
        self.assertEqual(verification["gate_decision"], "BLOCK")

    def test_tampered_summary_does_not_verify(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)
        summary["gap"]["binding_status"] = "FORMAL"

        verification = verify_strategy_correlation_downside_tail_public_summary(
            summary,
            **inputs,
        )
        self.assertEqual(verification["verification_status"], "BLOCK")
        self.assertEqual(verification["public_state"], "UNKNOWN")

    def test_numeric_permission_alias_does_not_verify(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)
        summary["permission"]["paper_authorized"] = 0

        verification = verify_strategy_correlation_downside_tail_public_summary(
            summary,
            **inputs,
        )
        self.assertEqual(verification["verification_status"], "BLOCK")

    def test_public_summary_redacts_hashes_identities_and_tail_details(self):
        inputs = self._inputs(joint=True, prefix="PRIVATE-OBSERVATION")
        summary = build_strategy_correlation_downside_tail_public_summary(**inputs)
        encoded = json.dumps(summary, sort_keys=True)

        private_hashes = set(re.findall(r"[0-9a-f]{64}", json.dumps(inputs)))
        self.assertTrue(private_hashes)
        self.assertTrue(all(value not in encoded for value in private_hashes))
        self.assertNotIn("PRIVATE-OBSERVATION", encoded)
        self.assertNotIn('"returns"', encoded)
        self.assertNotIn('"left_identity"', encoded)
        self.assertNotIn('"stratum_by_identity"', encoded)
        self.assertNotIn('"raw_p_value"', encoded)

    def test_untrusted_input_text_is_not_reflected(self):
        summary = build_strategy_correlation_downside_tail_public_summary(
            {"secret": "DO-NOT-REFLECT"}
        )
        self.assertNotIn("DO-NOT-REFLECT", json.dumps(summary, sort_keys=True))

    def test_every_authority_and_redaction_flag_stays_closed(self):
        summary = build_strategy_correlation_downside_tail_public_summary(**self._inputs())
        self.assertTrue(summary["permission"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in summary["permission"].items()
                if key != "descriptive_only"
            )
        )
        self.assertTrue(all(value is False for value in summary["redaction"].values()))

    def test_projection_is_deterministic(self):
        inputs = self._inputs(joint=True)
        self.assertEqual(
            build_strategy_correlation_downside_tail_public_summary(**inputs),
            build_strategy_correlation_downside_tail_public_summary(
                **copy.deepcopy(inputs)
            ),
        )


if __name__ == "__main__":
    unittest.main()
