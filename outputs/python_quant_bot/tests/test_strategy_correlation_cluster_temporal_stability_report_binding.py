from copy import deepcopy
import unittest

from tests import test_strategy_correlation_cluster_temporal_stability_protocol as protocol_fixtures
from tests import test_strategy_correlation_cluster_temporal_stability_report_consumer as report_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_binding import (
    assess_strategy_correlation_cluster_temporal_stability_report_binding,
    verify_strategy_correlation_cluster_temporal_stability_report_binding,
)


class StrategyCorrelationClusterTemporalStabilityReportBindingTests(unittest.TestCase):
    BINDING_ID = "temporal-report21-candidate-binding-1"

    def setUp(self):
        self.report_case = (
            report_fixtures.StrategyCorrelationClusterTemporalStabilityReportConsumerTests(
                methodName="test_valid_report21_passes_contract_and_decision"
            )
        )
        self.report_case.setUp()
        self.protocol_case = (
            protocol_fixtures.StrategyCorrelationClusterTemporalStabilityProtocolTests(
                methodName="test_valid_registration_inherits_v7_and_targets_report21"
            )
        )

    def tearDown(self):
        self.report_case.tearDown()

    @staticmethod
    def _identity_hash(report):
        identities = [
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
            }
            for identity in sorted(
                (
                    entry["strategy_id"],
                    entry["variant_id"],
                    entry["lane"],
                )
                for entry in report["entries"]
            )
        ]
        return strict_canonical_hash(identities)

    def _sources(self, *, low_effective_sample=False):
        values = self.report_case._fixture(
            low_effective_sample=low_effective_sample
        )
        extension, report20, report19, registry, stability, temporal = values
        return {
            "protocol_registration": self.protocol_case._registration(),
            "report21_extension": extension,
            "binding_id": self.BINDING_ID,
            "expected_protocol_registration_hash": None,
            "expected_report21_extension_hash": extension["extension_hash"],
            "expected_report_identity_set_hash": self._identity_hash(extension),
            "expected_base_report_hash": report20["base_report_hash"],
            "expected_global_independence_extension_hash": report19[
                "extension_hash"
            ],
            "expected_cluster_stability_extension_hash": report20[
                "extension_hash"
            ],
            "expected_registry_bindings": [registry],
            "expected_stability_bindings": [stability],
            "expected_temporal_stability_bindings": [temporal],
        }

    def _arguments(self, *, low_effective_sample=False, **overrides):
        arguments = self._sources(low_effective_sample=low_effective_sample)
        arguments["expected_protocol_registration_hash"] = arguments[
            "protocol_registration"
        ]["registration_hash"]
        arguments.update(overrides)
        return arguments

    def _assessment(self, **arguments):
        protocol = arguments.pop("protocol_registration")
        report = arguments.pop("report21_extension")
        return assess_strategy_correlation_cluster_temporal_stability_report_binding(
            protocol,
            report,
            **arguments,
        )

    def _verification(self, assessment, arguments):
        return verify_strategy_correlation_cluster_temporal_stability_report_binding(
            assessment,
            **arguments,
        )

    def test_valid_pass_report_is_candidate_bound_but_not_formal(self):
        arguments = self._arguments()
        assessment = self._assessment(**deepcopy(arguments))
        verification = self._verification(assessment, arguments)
        self.assertEqual(assessment["status"], "CANDIDATE_BOUND")
        self.assertEqual(assessment["report21_decision"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["candidate_bound"])
        self.assertFalse(verification["formal_registration_report_binding"])
        self.assertFalse(verification["writer_implemented"])

    def test_valid_block_report_remains_candidate_bound_without_decision_authority(self):
        arguments = self._arguments(low_effective_sample=True)
        assessment = self._assessment(**deepcopy(arguments))
        verification = self._verification(assessment, arguments)
        self.assertEqual(assessment["status"], "CANDIDATE_BOUND")
        self.assertEqual(assessment["report21_decision"], "BLOCK")
        self.assertFalse(assessment["report21_decision_authority"])
        self.assertTrue(verification["candidate_bound"])

    def test_wrong_protocol_registration_hash_blocks_candidate(self):
        arguments = self._arguments(expected_protocol_registration_hash="a" * 64)
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["facts"]["protocol_registration_hash_bound"])

    def test_wrong_report21_extension_hash_blocks_candidate(self):
        arguments = self._arguments(expected_report21_extension_hash="b" * 64)
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["facts"]["report21_extension_hash_bound"])

    def test_wrong_identity_set_hash_blocks_candidate(self):
        arguments = self._arguments(expected_report_identity_set_hash="c" * 64)
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertEqual(assessment["report_identity_count"], 1)
        self.assertFalse(assessment["facts"]["report_identity_set_hash_bound"])

    def test_registration_target_drift_blocks_compatibility(self):
        arguments = self._arguments()
        registration = deepcopy(arguments["protocol_registration"])
        registration["target_report_schema_version"] = 22
        registration = seal_strict_canonical_document(
            registration, "registration_hash"
        )
        arguments["protocol_registration"] = registration
        arguments["expected_protocol_registration_hash"] = registration[
            "registration_hash"
        ]
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(
            assessment["facts"]["protocol_registration_independently_verified"]
        )
        self.assertFalse(assessment["facts"]["target_report_schema_compatible"])

    def test_resealed_temporal_gate_schema_drift_blocks_report_verification(self):
        arguments = self._arguments()
        report = deepcopy(arguments["report21_extension"])
        gate = report["entries"][0]["temporal_stability_gate"]
        gate["schema_version"] = "drifted"
        gate = seal_strict_canonical_document(gate, "gate_hash")
        report["entries"][0]["temporal_stability_gate"] = gate
        report["entries"][0]["temporal_stability_gate_hash"] = gate["gate_hash"]
        report = seal_strict_canonical_document(report, "extension_hash")
        temporal_binding = deepcopy(arguments["expected_temporal_stability_bindings"][0])
        temporal_binding["expected_temporal_stability_gate_hash"] = gate["gate_hash"]
        arguments["report21_extension"] = report
        arguments["expected_report21_extension_hash"] = report["extension_hash"]
        arguments["expected_report_identity_set_hash"] = self._identity_hash(report)
        arguments["expected_temporal_stability_bindings"] = [temporal_binding]
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(
            assessment["facts"]["report21_extension_independently_verified"]
        )
        self.assertFalse(assessment["facts"]["temporal_gate_schema_compatible"])

    def test_missing_external_temporal_binding_blocks_candidate(self):
        arguments = self._arguments(expected_temporal_stability_bindings=[])
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(
            assessment["facts"]["report21_extension_independently_verified"]
        )

    def test_resealed_facts_cannot_override_exact_rebuild(self):
        arguments = self._arguments()
        assessment = self._assessment(**deepcopy(arguments))
        assessment["facts"]["formal_override"] = True
        assessment["formal_registration_report_binding"] = True
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")
        verification = self._verification(assessment, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("report_binding_contract_invalid", verification["blockers"])
        self.assertFalse(verification["formal_registration_report_binding"])

    def test_authority_escalation_is_rejected_after_reseal(self):
        arguments = self._arguments()
        assessment = self._assessment(**deepcopy(arguments))
        assessment["permissions"]["live_order_allowed"] = True
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")
        verification = self._verification(assessment, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])
        self.assertFalse(verification["permissions"]["live_order_allowed"])

    def test_invalid_binding_id_blocks_candidate(self):
        arguments = self._arguments(binding_id=" candidate ")
        assessment = self._assessment(**deepcopy(arguments))
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn("binding_id_invalid", assessment["blockers"])

    def test_assessment_does_not_mutate_or_embed_external_assets(self):
        arguments = self._arguments()
        before = deepcopy(arguments)
        assessment = self._assessment(**deepcopy(arguments))
        self.assertTrue(strict_json_contract_equal(arguments, before))
        self.assertFalse(assessment["external_assets_embedded"])
        self.assertNotIn("protocol_registration", assessment)
        self.assertNotIn("report21_extension", assessment)
        self.assertNotIn("expected_temporal_stability_bindings", assessment)

    def test_output_has_no_writer_or_current_activation(self):
        arguments = self._arguments()
        assessment = self._assessment(**deepcopy(arguments))
        verification = self._verification(assessment, arguments)
        self.assertFalse(assessment["formal_registry_bound"])
        self.assertFalse(assessment["writer_implemented"])
        self.assertFalse(assessment["current_admission_allowed"])
        self.assertFalse(assessment["permissions"]["paper_authorized"])
        self.assertFalse(verification["current_writer_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
