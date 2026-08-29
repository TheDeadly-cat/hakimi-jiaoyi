import copy
import unittest

from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    build_strategy_correlation_complete_link_protocol_registration,
    verify_strategy_correlation_complete_link_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_strata_protocol import (
    EXTENSION_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_strata_protocol_registration,
    verify_strategy_correlation_strata_protocol_registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from tests import test_strategy_correlation_multiplicity_protocol


class StrategyCorrelationStrataProtocolTests(unittest.TestCase):
    @staticmethod
    def _hash(document, field):
        return strict_canonical_hash(
            {key: value for key, value in document.items() if key != field}
        )

    def _source_v6(self):
        fixture = (
            test_strategy_correlation_multiplicity_protocol
            .StrategyCorrelationMultiplicityProtocolTests(
            methodName="test_protocol_v5_binds_registration_v3_and_verifies"
            )
        )
        fixture.setUp()
        matrix_case, _, _, container = fixture._build_protocol_fixture()
        try:
            source_v3 = container["registration_v3"]
            source_v6 = (
                build_strategy_correlation_complete_link_protocol_registration(
                    source_v3
                )
            )
        finally:
            matrix_case.tearDown()
        self.assertEqual(
            verify_strategy_correlation_complete_link_protocol_registration(
                source_v6
            )["status"],
            "PASS",
        )
        return source_v3, source_v6

    def test_registration_targets_report18_protocol_v7_without_authority(self):
        _, source = self._source_v6()
        registration = (
            build_strategy_correlation_strata_protocol_registration(source)
        )
        self.assertEqual(
            registration["schema_version"],
            REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_protocol_schema_version"],
            TARGET_PROTOCOL_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_report_schema_version"],
            TARGET_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_extension_schema_version"],
            EXTENSION_SCHEMA_VERSION,
        )
        self.assertFalse(registration["formal_registry_bound"])
        self.assertFalse(registration["writer_available"])
        self.assertFalse(registration["current_admission_allowed"])
        self.assertFalse(registration["permissions"]["paper_authorized"])
        self.assertFalse(registration["permissions"]["live_order_allowed"])
        self.assertEqual(
            verify_strategy_correlation_strata_protocol_registration(
                registration
            )["status"],
            "PASS",
        )

    def test_policy_freezes_registry_and_report18_prerequisites(self):
        _, source = self._source_v6()
        registration = (
            build_strategy_correlation_strata_protocol_registration(source)
        )
        policy = registration["strata_policy"]
        self.assertTrue(policy["report17_extension_verification_required"])
        self.assertTrue(policy["strata_gate_rebuild_required"])
        self.assertTrue(policy["registry_asset_verification_required"])
        self.assertTrue(policy["registry_binding_bound_required"])
        self.assertTrue(policy["external_registry_asset_hash_required"])
        self.assertTrue(
            policy["external_classification_source_hash_required"]
        )
        self.assertTrue(policy["selection_cutoff_binding_required"])
        self.assertTrue(policy["real_registry_asset_required"])
        self.assertIn(
            "SCHEMA18_SOLE_WRITER_MIGRATION_TESTS",
            policy["writer_activation_prerequisites"],
        )

    def test_protocol_v5_source_cannot_skip_protocol_v6(self):
        source_v3, _ = self._source_v6()
        with self.assertRaisesRegex(
            ValueError,
            "source_protocol_v6_registration_invalid",
        ):
            build_strategy_correlation_strata_protocol_registration(
                source_v3
            )

    def test_resealed_source_protocol_drift_is_rejected(self):
        _, source = self._source_v6()
        tampered_source = copy.deepcopy(source)
        tampered_source["target_report_schema_version"] = 18
        tampered_source["registration_hash"] = self._hash(
            tampered_source,
            "registration_hash",
        )
        with self.assertRaisesRegex(
            ValueError,
            "source_protocol_v6_registration_invalid",
        ):
            build_strategy_correlation_strata_protocol_registration(
                tampered_source
            )

    def test_coherently_resealed_policy_tamper_is_rejected(self):
        _, source = self._source_v6()
        registration = (
            build_strategy_correlation_strata_protocol_registration(source)
        )
        tampered = copy.deepcopy(registration)
        tampered["strata_policy"]["real_registry_asset_required"] = False
        tampered["strata_policy"]["policy_hash"] = self._hash(
            tampered["strata_policy"],
            "policy_hash",
        )
        tampered["strata_policy_hash"] = tampered["strata_policy"][
            "policy_hash"
        ]
        tampered["registration_hash"] = self._hash(
            tampered,
            "registration_hash",
        )
        self.assertEqual(
            verify_strategy_correlation_strata_protocol_registration(
                tampered
            )["status"],
            "BLOCK",
        )

    def test_resealed_authority_escalation_is_rejected(self):
        _, source = self._source_v6()
        registration = (
            build_strategy_correlation_strata_protocol_registration(source)
        )
        tampered = copy.deepcopy(registration)
        tampered["formal_registry_activation_allowed"] = True
        tampered["registration_hash"] = self._hash(
            tampered,
            "registration_hash",
        )
        verification = (
            verify_strategy_correlation_strata_protocol_registration(
                tampered
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strata_protocol_registration_authority_invalid",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
