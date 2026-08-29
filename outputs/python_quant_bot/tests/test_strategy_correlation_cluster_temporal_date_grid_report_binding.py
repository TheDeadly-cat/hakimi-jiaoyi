from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import unittest
from unittest.mock import patch

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    evaluate_strategy_correlation_cluster_temporal_date_grid_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_binding import (
    assess_strategy_correlation_cluster_temporal_date_grid_report_binding,
    verify_strategy_correlation_cluster_temporal_date_grid_report_binding,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    evaluate_strategy_correlation_cluster_temporal_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_binding import (
    assess_strategy_correlation_cluster_temporal_stability_report_binding,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from tests.test_strategy_correlation_cluster_temporal_stability_report_binding import (
    StrategyCorrelationClusterTemporalStabilityReportBindingTests,
)


class StrategyCorrelationClusterTemporalDateGridReportBindingTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source_case = (
            StrategyCorrelationClusterTemporalStabilityReportBindingTests(
                methodName="test_valid_pass_report_is_candidate_bound_but_not_formal"
            )
        )
        self.source_case.setUp()
        self.addCleanup(self.source_case.tearDown)

    @staticmethod
    def _date_grid_gate(arguments):
        report = arguments["report21_extension"]
        report_entry = report["entries"][0]
        report20 = report["base_cluster_stability_extension"]
        stability_entry = report20["entries"][0]
        source_entry = report20["base_global_independence_extension"]["entries"][0]
        temporal_binding = arguments["expected_temporal_stability_bindings"][0]
        return evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
            temporal_binding["source_uncertainty_audit"],
            report_entry["temporal_stability_gate"],
            full_window_stability_gate=stability_entry["stability_gate"],
            complete_link_gate=source_entry["complete_link_gate"],
            preregistration=source_entry["source_preregistration"],
            correlation_matrix=temporal_binding["correlation_matrix"],
            selection_cells=temporal_binding["selection_cells"],
            strategy_id=report_entry["strategy_id"],
            variant_id=report_entry["variant_id"],
            lane=report_entry["lane"],
        )

    def _date_grid_binding(self, arguments):
        entry = arguments["report21_extension"]["entries"][0]
        gate = self._date_grid_gate(arguments)
        return {
            "strategy_id": entry["strategy_id"],
            "variant_id": entry["variant_id"],
            "lane": entry["lane"],
            "expected_temporal_date_grid_gate_hash": gate["gate_hash"],
        }

    def _assessment(self, arguments, date_grid_bindings):
        values = deepcopy(arguments)
        protocol = values.pop("protocol_registration")
        report = values.pop("report21_extension")
        return assess_strategy_correlation_cluster_temporal_date_grid_report_binding(
            protocol,
            report,
            expected_temporal_date_grid_bindings=deepcopy(date_grid_bindings),
            **values,
        )

    def _verification(self, document, arguments, date_grid_bindings):
        return verify_strategy_correlation_cluster_temporal_date_grid_report_binding(
            document,
            expected_temporal_date_grid_bindings=deepcopy(date_grid_bindings),
            **deepcopy(arguments),
        )

    def _misaligned_arguments(self):
        report20_case = self.source_case.report_case.report20_case
        preregistration, aligned_source, _ = report20_case._source_inputs()
        replay = deepcopy(aligned_source["matrix_replay"])
        for dataset in replay["completed_price_input"]["datasets"]:
            if dataset["symbol"] == "BBB":
                for row in dataset["price_rows"]:
                    row["date"] = (
                        date.fromisoformat(row["date"]) - timedelta(days=20)
                    ).isoformat()
        source = build_strategy_correlation_uncertainty_audit(replay)
        correlations = {
            (item["left_symbol"], item["right_symbol"]): item["correlation"]
            for item in source["pairs"]
        }
        overlaps = {
            (item["left_symbol"], item["right_symbol"]): item[
                "overlap_observations"
            ]
            for item in source["pairs"]
        }
        matrix = build_correlation_matrix_contract(
            preregistration["symbols"],
            correlations,
            overlap_observations=overlaps,
        )
        with patch.object(
            report20_case,
            "_source_inputs",
            return_value=(preregistration, source, matrix),
        ):
            report20, report19, registry_binding, stability_binding = (
                report20_case._fixture()
            )

        stability_entry = report20["entries"][0]
        source_entry = report20["base_global_independence_extension"]["entries"][0]
        identity = {
            "strategy_id": stability_entry["strategy_id"],
            "variant_id": stability_entry["variant_id"],
            "lane": stability_entry["lane"],
        }
        temporal_gate = evaluate_strategy_correlation_cluster_temporal_stability_gate(
            source,
            stability_entry["stability_gate"],
            complete_link_gate=source_entry["complete_link_gate"],
            preregistration=source_entry["source_preregistration"],
            correlation_matrix=matrix,
            selection_cells=stability_binding["selection_cells"],
            **identity,
        )
        temporal_binding = {
            **identity,
            "source_uncertainty_audit": source,
            "correlation_matrix": matrix,
            "selection_cells": stability_binding["selection_cells"],
            "expected_temporal_stability_gate_hash": temporal_gate["gate_hash"],
        }
        report21 = seal_strict_canonical_document(
            {
                "schema_version": EXTENSION_SCHEMA_VERSION,
                "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
                "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
                "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
                "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
                "base_report_hash": report20["base_report_hash"],
                "base_cluster_stability_extension": report20,
                "base_cluster_stability_extension_hash": report20[
                    "extension_hash"
                ],
                "registry_bindings_required": True,
                "stability_bindings_required": True,
                "temporal_stability_gate_required": True,
                "external_temporal_stability_bindings_required": True,
                "entries": [
                    {
                        **identity,
                        "temporal_stability_gate": temporal_gate,
                        "temporal_stability_gate_hash": temporal_gate[
                            "gate_hash"
                        ],
                    }
                ],
                "decision": "PASS",
                "decision_blockers": [],
                "consumer_only": True,
                "requires_new_report_schema": True,
                "writer_available": False,
                "current_admission_allowed": False,
                "current_writer_activation_allowed": False,
                "permissions": {
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            },
            "extension_hash",
        )
        protocol = self.source_case.protocol_case._registration()
        arguments = {
            "protocol_registration": protocol,
            "report21_extension": report21,
            "binding_id": "temporal-date-grid-report21-misaligned-proof",
            "expected_protocol_registration_hash": protocol["registration_hash"],
            "expected_report21_extension_hash": report21["extension_hash"],
            "expected_report_identity_set_hash": self.source_case._identity_hash(
                report21
            ),
            "expected_base_report_hash": report20["base_report_hash"],
            "expected_global_independence_extension_hash": report19[
                "extension_hash"
            ],
            "expected_cluster_stability_extension_hash": report20[
                "extension_hash"
            ],
            "expected_registry_bindings": [registry_binding],
            "expected_stability_bindings": [stability_binding],
            "expected_temporal_stability_bindings": [temporal_binding],
        }
        return arguments, replay

    def test_aligned_report21_is_candidate_bound_with_date_grid_pass(self):
        arguments = self.source_case._arguments()
        bindings = [self._date_grid_binding(arguments)]
        assessment = self._assessment(arguments, bindings)
        verification = self._verification(assessment, arguments, bindings)
        self.assertEqual(assessment["status"], "CANDIDATE_BOUND")
        self.assertEqual(assessment["report21_decision"], "PASS")
        self.assertEqual(assessment["date_grid_decision"], "PASS")
        self.assertEqual(assessment["temporal_date_grid_gate_count"], 1)
        self.assertEqual(assessment["temporal_date_grid_gate_pass_count"], 1)
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["candidate_bound"])
        self.assertFalse(
            assessment["protocol_date_grid_policy_preregistered"]
        )
        self.assertTrue(assessment["requires_report_schema_upgrade"])

    def test_misaligned_old_candidate_is_blocked_by_date_grid_binding(self):
        arguments, replay = self._misaligned_arguments()
        source_values = deepcopy(arguments)
        protocol = source_values.pop("protocol_registration")
        report = source_values.pop("report21_extension")
        source_assessment = (
            assess_strategy_correlation_cluster_temporal_stability_report_binding(
                protocol,
                report,
                **source_values,
            )
        )
        bindings = [self._date_grid_binding(arguments)]
        assessment = self._assessment(arguments, bindings)
        datasets = {
            item["symbol"]: item
            for item in replay["completed_price_input"]["datasets"]
        }
        aaa_dates = {
            row["date"] for row in datasets["AAA"]["price_rows"][1:]
        }
        bbb_dates = {
            row["date"] for row in datasets["BBB"]["price_rows"][1:]
        }
        self.assertEqual(len(aaa_dates & bbb_dates), 40)
        self.assertEqual(source_assessment["status"], "CANDIDATE_BOUND")
        self.assertEqual(source_assessment["report21_decision"], "PASS")
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertEqual(assessment["date_grid_decision"], "BLOCK")
        self.assertFalse(
            assessment["facts"][
                "report21_pass_requires_all_date_grid_pass"
            ]
        )

    def test_missing_or_wrong_date_grid_binding_blocks_candidate(self):
        arguments = self.source_case._arguments()
        valid = self._date_grid_binding(arguments)
        missing = self._assessment(arguments, [])
        wrong = deepcopy(valid)
        wrong["expected_temporal_date_grid_gate_hash"] = "f" * 64
        mismatched = self._assessment(arguments, [wrong])
        self.assertEqual(missing["status"], "BLOCK")
        self.assertFalse(missing["facts"]["date_grid_binding_set_exact"])
        self.assertEqual(mismatched["status"], "BLOCK")
        self.assertFalse(mismatched["facts"]["date_grid_gate_hashes_bound"])

    def test_coherently_resealed_facts_cannot_override_rebuild(self):
        arguments = self.source_case._arguments()
        bindings = [self._date_grid_binding(arguments)]
        assessment = self._assessment(arguments, bindings)
        assessment["facts"]["formal_override"] = True
        assessment["formal_registration_report_binding"] = True
        assessment = seal_strict_canonical_document(
            assessment,
            "assessment_hash",
        )
        verification = self._verification(assessment, arguments, bindings)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["formal_registration_report_binding"])

    def test_authority_and_native_aliases_fail_closed(self):
        arguments = self.source_case._arguments()
        bindings = [self._date_grid_binding(arguments)]
        assessment = self._assessment(arguments, bindings)
        authority = deepcopy(assessment)
        authority["permissions"]["live_order_allowed"] = True
        authority = seal_strict_canonical_document(authority, "assessment_hash")
        alias = deepcopy(assessment)
        alias["report_identity_count"] = 1.0
        alias = seal_strict_canonical_document(alias, "assessment_hash")
        authority_verification = self._verification(
            authority,
            arguments,
            bindings,
        )
        alias_verification = self._verification(alias, arguments, bindings)
        self.assertEqual(authority_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation",
            authority_verification["blockers"],
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertIs(
            alias_verification["permissions"]["live_order_allowed"],
            False,
        )

    def test_assessment_does_not_embed_external_assets(self):
        arguments = self.source_case._arguments()
        bindings = [self._date_grid_binding(arguments)]
        assessment = self._assessment(arguments, bindings)
        self.assertFalse(assessment["external_assets_embedded"])
        self.assertNotIn("protocol_registration", assessment)
        self.assertNotIn("report21_extension", assessment)
        self.assertNotIn("expected_temporal_stability_bindings", assessment)
        self.assertNotIn("expected_temporal_date_grid_bindings", assessment)

    def test_exports_have_no_writer_report_builder_or_current_switch(self):
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_report_binding as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("build_report22", exports)
        self.assertNotIn("write_report21", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
