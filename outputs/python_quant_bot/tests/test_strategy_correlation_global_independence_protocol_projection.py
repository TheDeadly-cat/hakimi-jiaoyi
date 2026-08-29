from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_global_independence_protocol as protocol_fixtures

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_global_independence_protocol_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_global_independence_protocol_migration_public_summary,
    verify_strategy_correlation_global_independence_protocol_migration_public_summary,
)


class StrategyCorrelationGlobalIndependenceProtocolProjectionTests(unittest.TestCase):
    @staticmethod
    def _seal(document, field):
        document.pop(field, None)
        document[field] = strict_canonical_hash(document)
        return document

    def _protocol(self):
        fixture = protocol_fixtures.StrategyCorrelationGlobalIndependenceProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    @staticmethod
    def _field_names(value):
        names = set()
        if isinstance(value, dict):
            names.update(value)
            for child in value.values():
                names.update(
                    StrategyCorrelationGlobalIndependenceProtocolProjectionTests._field_names(
                        child
                    )
                )
        elif isinstance(value, list):
            for child in value:
                names.update(
                    StrategyCorrelationGlobalIndependenceProtocolProjectionTests._field_names(
                        child
                    )
                )
        return names

    def test_verified_protocol_projects_neutral_migration_state(self):
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                self._protocol()
            )
        )

        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["protocol_target"], "PROTOCOL_V8")
        self.assertEqual(summary["source"]["report_target"], "REPORT19")
        self.assertEqual(summary["gap"]["formal_registry_status"], "NOT_SUPPLIED")
        self.assertEqual(summary["maturity"]["status"], "PROTOCOL_PREREGISTERED")
        self.assertEqual(summary["maturity"]["writer_prerequisite_count"], 7)
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_invalid_protocol_projects_unknown(self):
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                {}
            )
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")
        self.assertEqual(summary["maturity"]["status"], "UNKNOWN")
        self.assertIsNone(summary["maturity"]["writer_prerequisite_count"])

    def test_resealed_protocol_drift_projects_unknown(self):
        protocol = self._protocol()
        protocol["schema19_consumer_available"] = False
        self._seal(protocol, "registration_hash")

        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                protocol
            )
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")

    def test_tampered_summary_is_rejected(self):
        protocol = self._protocol()
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                protocol
            )
        )
        summary["maturity"]["writer"] = "IMPLEMENTED"

        verification = (
            verify_strategy_correlation_global_independence_protocol_migration_public_summary(
                summary,
                source_protocol_registration=protocol,
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("public_summary_contract_invalid", verification["blockers"])

    def test_permission_integer_alias_is_rejected(self):
        protocol = self._protocol()
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                protocol
            )
        )
        summary["permission"]["paper_authorized"] = 0

        verification = (
            verify_strategy_correlation_global_independence_protocol_migration_public_summary(
                summary,
                source_protocol_registration=protocol,
            )
        )

        self.assertEqual(verification["status"], "BLOCK")

    def test_authority_escalation_is_rejected(self):
        protocol = self._protocol()
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                protocol
            )
        )
        summary["permission"]["live_order_allowed"] = True

        verification = (
            verify_strategy_correlation_global_independence_protocol_migration_public_summary(
                summary,
                source_protocol_registration=protocol,
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])

    def test_public_summary_redacts_hashes_and_identities(self):
        summary = (
            build_strategy_correlation_global_independence_protocol_migration_public_summary(
                self._protocol()
            )
        )
        serialized = json.dumps(summary, sort_keys=True)
        field_names = self._field_names(summary)

        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(
            {
                "registration_hash",
                "policy_hash",
                "registry_id",
                "cluster_id",
                "symbol",
                "selection_cutoff_date",
            }.isdisjoint(field_names)
        )
        self.assertTrue(all(value is False for value in summary["redaction"].values()))


if __name__ == "__main__":
    unittest.main()
