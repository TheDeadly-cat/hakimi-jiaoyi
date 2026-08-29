from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    EXTENSION_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_report_extension,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strategy_correlation_strata_global_independence import (
    evaluate_strategy_correlation_strata_global_independence_gate,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    verify_strategy_correlation_strata_report_extension,
)


class StrategyCorrelationGlobalIndependenceReportConsumerTests(unittest.TestCase):
    BASE_REPORT_HASH = "b" * 64
    CLASSIFICATION_SOURCE_HASH = "a" * 64

    @staticmethod
    def _seal(document, field):
        document.pop(field, None)
        document[field] = strict_canonical_hash(document)
        return document

    @staticmethod
    def _dimensions(*, cycle):
        if not cycle:
            return [
                {
                    "dimension_id": "asset-family",
                    "strata": [
                        {"stratum_id": "family-a", "cluster_ids": ["cluster-aaa"]},
                        {"stratum_id": "family-b", "cluster_ids": ["cluster-bbb"]},
                        {"stratum_id": "family-c", "cluster_ids": ["cluster-ccc"]},
                    ],
                }
            ]
        return [
            {
                "dimension_id": "dimension-ab",
                "strata": [
                    {
                        "stratum_id": "ab",
                        "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                    },
                    {"stratum_id": "c-only", "cluster_ids": ["cluster-ccc"]},
                ],
            },
            {
                "dimension_id": "dimension-ac",
                "strata": [
                    {
                        "stratum_id": "ac",
                        "cluster_ids": ["cluster-aaa", "cluster-ccc"],
                    },
                    {"stratum_id": "b-only", "cluster_ids": ["cluster-bbb"]},
                ],
            },
            {
                "dimension_id": "dimension-bc",
                "strata": [
                    {
                        "stratum_id": "bc",
                        "cluster_ids": ["cluster-bbb", "cluster-ccc"],
                    },
                    {"stratum_id": "a-only", "cluster_ids": ["cluster-aaa"]},
                ],
            },
        ]

    def _fixture(self, *, cycle=False):
        identities = [
            ("cluster-aaa", "AAA"),
            ("cluster-bbb", "BBB"),
            ("cluster-ccc", "CCC"),
        ]
        source_preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": cluster_id, "members": [symbol]}
                for cluster_id, symbol in identities
            ]
        )
        correlation_matrix = build_correlation_matrix_contract(
            [symbol for _, symbol in identities],
            {
                ("AAA", "BBB"): 0.1,
                ("AAA", "CCC"): 0.1,
                ("BBB", "CCC"): 0.1,
            },
        )
        selection_cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "lane": "RAW_EXCESS",
                "symbol": symbol,
                "gate_status": "PASS",
            }
            for _, symbol in identities
        ]
        complete_link_gate = evaluate_correlation_cluster_gate_v2(
            source_preregistration,
            correlation_matrix,
            selection_cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        base_complete_link_extension = self._seal(
            {
                "schema_version": "strategy-research-complete-link-extension-v1",
                "base_report_schema_version": 16,
                "target_report_schema_version": 17,
                "target_protocol_schema_version": "strategy-matrix-protocol-v6",
                "base_report_hash": self.BASE_REPORT_HASH,
                "entries": [
                    {
                        "strategy_id": "S",
                        "variant_id": "V",
                        "lane": "RAW_EXCESS",
                        "preregistration": source_preregistration,
                        "correlation_matrix": correlation_matrix,
                        "selection_cells": selection_cells,
                        "gate_v2": complete_link_gate,
                    }
                ],
                "decision": "PASS",
                "decision_blockers": [],
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

        dimensions = self._dimensions(cycle=cycle)
        strata_registration = build_strategy_correlation_strata_preregistration(
            source_preregistration,
            dimensions,
        )
        strata_gate = evaluate_strategy_correlation_strata_gate(
            strata_registration,
            complete_link_gate,
            source_preregistration=source_preregistration,
        )
        registry_asset = build_strategy_correlation_strata_registry_asset(
            source_preregistration,
            dimensions,
            registry_id="candidate-report19",
            classification_source="external-synthetic-classification",
            classification_source_version="v1",
            classification_source_hash=self.CLASSIFICATION_SOURCE_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        expected_binding = {
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
            "selection_cutoff_date": "2026-08-02",
            "expected_registry_asset_hash": registry_asset["registry_asset_hash"],
            "expected_classification_source_hash": self.CLASSIFICATION_SOURCE_HASH,
        }
        registry_binding = assess_strategy_correlation_strata_registry_binding(
            registry_asset,
            strata_registration,
            source_preregistration,
            selection_cutoff_date=expected_binding["selection_cutoff_date"],
            expected_registry_asset_hash=expected_binding[
                "expected_registry_asset_hash"
            ],
            expected_classification_source_hash=expected_binding[
                "expected_classification_source_hash"
            ],
        )
        base_strata_extension = self._seal(
            {
                "schema_version": "strategy-research-preregistered-strata-extension-v1",
                "base_report_schema_version": 17,
                "target_report_schema_version": 18,
                "base_protocol_schema_version": "strategy-matrix-protocol-v6",
                "target_protocol_schema_version": "strategy-matrix-protocol-v7",
                "base_report_hash": self.BASE_REPORT_HASH,
                "base_complete_link_extension": base_complete_link_extension,
                "base_complete_link_extension_hash": base_complete_link_extension[
                    "extension_hash"
                ],
                "entries": [
                    {
                        "strategy_id": "S",
                        "variant_id": "V",
                        "lane": "RAW_EXCESS",
                        "source_preregistration": source_preregistration,
                        "strata_registration": strata_registration,
                        "complete_link_gate": complete_link_gate,
                        "strata_gate": strata_gate,
                        "registry_asset": registry_asset,
                        "registry_binding": registry_binding,
                    }
                ],
                "registry_binding_required": True,
                "consumer_only": True,
                "decision": "PASS",
                "decision_blockers": [],
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
        return base_strata_extension, expected_binding

    def _extension(self, base_strata_extension):
        entries = []
        decision_blockers = []
        if base_strata_extension["decision"] != "PASS":
            decision_blockers.append("strata_extension_blocked")
        for base_entry in base_strata_extension["entries"]:
            global_gate = evaluate_strategy_correlation_strata_global_independence_gate(
                base_entry["strata_registration"],
                base_entry["complete_link_gate"],
                base_entry["strata_gate"],
                source_preregistration=base_entry["source_preregistration"],
            )
            identity = (
                base_entry["strategy_id"],
                base_entry["variant_id"],
                base_entry["lane"],
            )
            if global_gate["status"] != "PASS":
                decision_blockers.append(
                    "global_independence_gate_blocked:" + ":".join(identity)
                )
            entries.append(
                {
                    "strategy_id": identity[0],
                    "variant_id": identity[1],
                    "lane": identity[2],
                    "source_preregistration": base_entry["source_preregistration"],
                    "strata_registration": base_entry["strata_registration"],
                    "complete_link_gate": base_entry["complete_link_gate"],
                    "strata_gate": base_entry["strata_gate"],
                    "global_independence_gate": global_gate,
                }
            )
        return self._seal(
            {
                "schema_version": EXTENSION_SCHEMA_VERSION,
                "base_report_schema_version": 18,
                "target_report_schema_version": 19,
                "base_protocol_schema_version": "strategy-matrix-protocol-v7",
                "target_protocol_schema_version": "strategy-matrix-protocol-v8",
                "base_report_hash": base_strata_extension["base_report_hash"],
                "base_strata_extension": base_strata_extension,
                "base_strata_extension_hash": base_strata_extension["extension_hash"],
                "entries": entries,
                "registry_binding_required": True,
                "global_independence_required": True,
                "consumer_only": True,
                "decision": "PASS" if not decision_blockers else "BLOCK",
                "decision_blockers": decision_blockers,
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

    def _verify(self, document, expected_binding):
        return verify_strategy_correlation_global_independence_report_extension(
            document,
            expected_base_report_hash=self.BASE_REPORT_HASH,
            expected_registry_bindings=[expected_binding],
        )

    def test_independent_singletons_pass_contract_and_decision(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["permissions"]["paper_authorized"])
        self.assertFalse(verification["permissions"]["live_order_allowed"])

    def test_three_dimension_cycle_passes_report18_but_blocks_report19(self):
        base_extension, expected_binding = self._fixture(cycle=True)
        report18 = verify_strategy_correlation_strata_report_extension(
            base_extension,
            expected_base_report_hash=self.BASE_REPORT_HASH,
            expected_registry_bindings=[expected_binding],
        )
        document = self._extension(base_extension)
        gate = document["entries"][0]["global_independence_gate"]

        verification = self._verify(document, expected_binding)

        self.assertEqual(report18["status"], "PASS")
        self.assertEqual(report18["decision"], "PASS")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["global_independence_audit"]["registered_independent_capacity"],
            1,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(
            verification["blockers"],
            ["global_independence_gate_blocked:S:V:RAW_EXCESS"],
        )

    def test_resealed_search_evidence_tamper_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        gate = document["entries"][0]["global_independence_gate"]
        audit = gate["global_independence_audit"]
        audit["search_node_count"] += 1
        self._seal(audit, "audit_hash")
        self._seal(gate, "gate_hash")
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_gate_invalid:S:V:RAW_EXCESS",
            verification["blockers"],
        )

    def test_nested_authority_escalation_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        gate = document["entries"][0]["global_independence_gate"]
        gate["permissions"]["paper_authorized"] = True
        self._seal(gate, "gate_hash")
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])

    def test_consumer_only_integer_alias_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        document["consumer_only"] = 1
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("consumer_only_mismatch", verification["blockers"])

    def test_global_required_integer_alias_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        document["global_independence_required"] = 1
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_required_mismatch",
            verification["blockers"],
        )

    def test_report_schema_float_alias_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        document["target_report_schema_version"] = 19.0
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "target_report_schema_version_mismatch",
            verification["blockers"],
        )

    def test_external_registry_hash_mismatch_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        mismatched_binding = deepcopy(expected_binding)
        mismatched_binding["expected_registry_asset_hash"] = "c" * 64

        verification = self._verify(document, mismatched_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("base_strata_extension_invalid", verification["blockers"])

    def test_resealed_decision_upgrade_is_rejected(self):
        base_extension, expected_binding = self._fixture(cycle=True)
        document = self._extension(base_extension)
        document["decision"] = "PASS"
        document["decision_blockers"] = []
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("decision_mismatch", verification["blockers"])
        self.assertIn("decision_blockers_mismatch", verification["blockers"])

    def test_entry_identity_drift_is_rejected(self):
        base_extension, expected_binding = self._fixture()
        document = self._extension(base_extension)
        document["entries"][0]["strategy_id"] = "DRIFTED"
        self._seal(document, "extension_hash")

        verification = self._verify(document, expected_binding)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "entry_identity_mismatch:DRIFTED:V:RAW_EXCESS",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
