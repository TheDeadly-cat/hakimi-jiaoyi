from copy import deepcopy
import unittest

from tests import test_strategy_correlation_strata_protocol as protocol_v7_fixtures

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_global_independence_protocol import (
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    build_strategy_correlation_global_independence_protocol_registration,
    verify_strategy_correlation_global_independence_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_strata_protocol import (
    build_strategy_correlation_strata_protocol_registration,
)


class StrategyCorrelationGlobalIndependenceProtocolTests(unittest.TestCase):
    @staticmethod
    def _seal(document, field):
        document.pop(field, None)
        document[field] = strict_canonical_hash(document)
        return document

    def _source_v6(self):
        fixture = protocol_v7_fixtures.StrategyCorrelationStrataProtocolTests(
            methodName="runTest"
        )
        return fixture._source_v6()[-1]

    def _source_v7(self):
        return build_strategy_correlation_strata_protocol_registration(
            self._source_v6()
        )

    def _registration(self):
        return build_strategy_correlation_global_independence_protocol_registration(
            self._source_v7()
        )

    def test_valid_registration_freezes_exact_protocol_v8_policy(self):
        document = self._registration()

        verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                document
            )
        )
        policy = document["global_independence_policy"]

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(document["schema_version"], REGISTRATION_SCHEMA_VERSION)
        self.assertEqual(policy["schema_version"], POLICY_SCHEMA_VERSION)
        self.assertEqual(
            policy["conflict_rule"],
            "ANY_SHARED_PARENT_STRATUM_ACROSS_REGISTERED_DIMENSIONS",
        )
        self.assertEqual(policy["independence_algorithm"], "EXACT_MAXIMUM_INDEPENDENT_SET")
        self.assertFalse(policy["approximation_allowed"])
        self.assertEqual(policy["exact_search_cluster_limit"], 24)
        self.assertEqual(policy["exact_search_node_limit"], 250000)
        self.assertEqual(policy["minimum_global_independent_votes"], 2)
        self.assertEqual(policy["required_global_independent_fraction"], 0.6)
        self.assertEqual(document["target_protocol_schema_version"], "strategy-matrix-protocol-v8")
        self.assertEqual(document["target_report_schema_version"], 19)
        self.assertFalse(document["formal_registry_bound"])
        self.assertFalse(document["writer_available"])
        self.assertFalse(document["current_admission_allowed"])
        self.assertFalse(document["permissions"]["paper_authorized"])
        self.assertFalse(document["permissions"]["live_order_allowed"])

    def test_protocol_v6_source_cannot_skip_registration_v5(self):
        with self.assertRaisesRegex(
            ValueError, "source_protocol_v7_registration_invalid"
        ):
            build_strategy_correlation_global_independence_protocol_registration(
                self._source_v6()
            )

    def test_resealed_source_v7_semantic_drift_is_rejected(self):
        source = self._source_v7()
        source["schema18_consumer_available"] = False
        self._seal(source, "registration_hash")

        with self.assertRaisesRegex(
            ValueError, "source_protocol_v7_registration_invalid"
        ):
            build_strategy_correlation_global_independence_protocol_registration(
                source
            )

    def test_resealed_policy_limit_drift_is_rejected(self):
        document = self._registration()
        policy = document["global_independence_policy"]
        policy["exact_search_node_limit"] = 249999
        self._seal(policy, "policy_hash")
        document["global_independence_policy_hash"] = policy["policy_hash"]
        self._seal(document, "registration_hash")

        verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                document
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_protocol_registration_contract_invalid",
            verification["blockers"],
        )

    def test_resealed_report_schema_float_alias_is_rejected(self):
        document = self._registration()
        document["target_report_schema_version"] = 19.0
        self._seal(document, "registration_hash")

        verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                document
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_protocol_registration_contract_invalid",
            verification["blockers"],
        )

    def test_nested_authority_escalation_is_rejected(self):
        document = self._registration()
        policy = document["global_independence_policy"]
        policy["permissions"]["paper_authorized"] = True
        self._seal(policy, "policy_hash")
        document["global_independence_policy_hash"] = policy["policy_hash"]
        self._seal(document, "registration_hash")

        verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                document
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])

    def test_resealed_source_hash_drift_is_rejected(self):
        document = self._registration()
        document["source_registration_hash"] = "0" * 64
        self._seal(document, "registration_hash")

        verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                document
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_protocol_registration_contract_invalid",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
