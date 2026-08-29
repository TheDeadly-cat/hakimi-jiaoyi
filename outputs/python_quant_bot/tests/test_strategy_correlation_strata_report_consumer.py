import copy
from pathlib import Path
import subprocess
import sys
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    BASE_REPORT_SCHEMA_VERSION as COMPLETE_LINK_BASE_REPORT_SCHEMA,
    EXTENSION_SCHEMA_VERSION as COMPLETE_LINK_EXTENSION_SCHEMA,
    TARGET_PROTOCOL_SCHEMA_VERSION as COMPLETE_LINK_TARGET_PROTOCOL,
    TARGET_REPORT_SCHEMA_VERSION as COMPLETE_LINK_TARGET_REPORT,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationStrataReportConsumerTests(unittest.TestCase):
    BASE_HASH = "b" * 64
    SOURCE_HASH = "a" * 64

    @staticmethod
    def _hash(document, field):
        return strict_canonical_hash(
            {key: value for key, value in document.items() if key != field}
        )

    def _base_extension(self, *, base_blocked=False):
        symbols = ["AAA", "BBB"]
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-aaa", "members": ["AAA"]},
                {"cluster_id": "cluster-bbb", "members": ["BBB"]},
            ]
        )
        matrix = build_correlation_matrix_contract(
            symbols,
            {("AAA", "BBB"): 0.10},
        )
        cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": (
                    "BLOCK"
                    if base_blocked and symbol == "BBB"
                    else "PASS"
                ),
            }
            for symbol in symbols
        ]
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        decision_blockers = (
            []
            if gate["status"] == "PASS"
            else ["complete_link_gate_blocked:S:V:RAW_EXCESS"]
        )
        extension = {
            "schema_version": COMPLETE_LINK_EXTENSION_SCHEMA,
            "base_report_schema_version": COMPLETE_LINK_BASE_REPORT_SCHEMA,
            "target_report_schema_version": COMPLETE_LINK_TARGET_REPORT,
            "target_protocol_schema_version": COMPLETE_LINK_TARGET_PROTOCOL,
            "base_report_hash": self.BASE_HASH,
            "entries": [
                {
                    "strategy_id": "S",
                    "variant_id": "V",
                    "lane": "RAW_EXCESS",
                    "preregistration": preregistration,
                    "correlation_matrix": matrix,
                    "selection_cells": cells,
                    "gate_v2": gate,
                }
            ],
            "decision": gate["status"],
            "decision_blockers": decision_blockers,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        extension["extension_hash"] = self._hash(
            extension,
            "extension_hash",
        )
        return preregistration, gate, extension

    def _fixture(
        self,
        *,
        shared_stratum=False,
        base_blocked=False,
        expected_source_hash=None,
    ):
        preregistration, gate, base_extension = self._base_extension(
            base_blocked=base_blocked
        )
        strata = (
            [
                {
                    "stratum_id": "shared",
                    "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                }
            ]
            if shared_stratum
            else [
                {
                    "stratum_id": "family-a",
                    "cluster_ids": ["cluster-aaa"],
                },
                {
                    "stratum_id": "family-b",
                    "cluster_ids": ["cluster-bbb"],
                },
            ]
        )
        dimensions = [{"dimension_id": "asset-family", "strata": strata}]
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            dimensions,
        )
        strata_gate = evaluate_strategy_correlation_strata_gate(
            registration,
            gate,
            source_preregistration=preregistration,
        )
        asset = build_strategy_correlation_strata_registry_asset(
            preregistration,
            dimensions,
            registry_id="candidate-1",
            classification_source="external-source",
            classification_source_version="v1",
            classification_source_hash=self.SOURCE_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        bound_source_hash = expected_source_hash or self.SOURCE_HASH
        binding = assess_strategy_correlation_strata_registry_binding(
            asset,
            registration,
            preregistration,
            selection_cutoff_date="2026-08-02",
            expected_registry_asset_hash=asset["registry_asset_hash"],
            expected_classification_source_hash=bound_source_hash,
        )
        expected_binding = {
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
            "selection_cutoff_date": "2026-08-02",
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_classification_source_hash": bound_source_hash,
        }
        entry = {
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
            "source_preregistration": preregistration,
            "strata_registration": registration,
            "complete_link_gate": gate,
            "strata_gate": strata_gate,
            "registry_asset": asset,
            "registry_binding": binding,
        }
        decision_blockers = []
        if base_extension["decision"] != "PASS":
            decision_blockers.append("complete_link_extension_blocked")
        if strata_gate["status"] != "PASS":
            decision_blockers.append(
                "strata_gate_blocked:S:V:RAW_EXCESS"
            )
        if binding["status"] != "BOUND":
            decision_blockers.append(
                "strata_registry_binding_blocked:S:V:RAW_EXCESS"
            )
        document = {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": self.BASE_HASH,
            "base_complete_link_extension": base_extension,
            "base_complete_link_extension_hash": base_extension[
                "extension_hash"
            ],
            "entries": [entry],
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "registry_binding_required": True,
            "consumer_only": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        document["extension_hash"] = self._hash(
            document,
            "extension_hash",
        )
        return document, expected_binding

    def _verify(self, document, expected_binding):
        return verify_strategy_correlation_strata_report_extension(
            document,
            expected_base_report_hash=self.BASE_HASH,
            expected_registry_bindings=[expected_binding],
        )

    def test_consumer_accepts_bound_pass_without_enabling_writer(self):
        document, expected = self._fixture()
        verification = self._verify(document, expected)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["permissions"]["paper_authorized"])
        self.assertFalse(verification["permissions"]["live_order_allowed"])

    def test_strata_block_is_valid_contract_evidence(self):
        document, expected = self._fixture(shared_stratum=True)
        verification = self._verify(document, expected)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertIn(
            "strata_gate_blocked:S:V:RAW_EXCESS",
            document["decision_blockers"],
        )

    def test_registry_binding_block_is_valid_contract_evidence(self):
        document, expected = self._fixture(expected_source_hash="c" * 64)
        verification = self._verify(document, expected)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertIn(
            "strata_registry_binding_blocked:S:V:RAW_EXCESS",
            document["decision_blockers"],
        )

    def test_base_complete_link_block_is_preserved(self):
        document, expected = self._fixture(base_blocked=True)
        verification = self._verify(document, expected)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertIn(
            "complete_link_extension_blocked",
            document["decision_blockers"],
        )

    def test_resealed_nested_complete_link_gate_is_rejected(self):
        document, expected = self._fixture()
        tampered = copy.deepcopy(document)
        base_gate = tampered["base_complete_link_extension"]["entries"][0][
            "gate_v2"
        ]
        base_gate["status"] = "BLOCK"
        base_gate["gate_hash"] = self._hash(base_gate, "gate_hash")
        tampered["entries"][0]["complete_link_gate"] = copy.deepcopy(
            base_gate
        )
        base_extension = tampered["base_complete_link_extension"]
        base_extension["extension_hash"] = self._hash(
            base_extension,
            "extension_hash",
        )
        tampered["base_complete_link_extension_hash"] = base_extension[
            "extension_hash"
        ]
        tampered["extension_hash"] = self._hash(
            tampered,
            "extension_hash",
        )
        self.assertEqual(
            self._verify(tampered, expected)["status"],
            "BLOCK",
        )

    def test_resealed_nested_authority_escalation_is_rejected(self):
        document, expected = self._fixture()
        tampered = copy.deepcopy(document)
        asset = tampered["entries"][0]["registry_asset"]
        asset["formal_registry_activation_allowed"] = True
        asset["registry_asset_hash"] = self._hash(
            asset,
            "registry_asset_hash",
        )
        tampered["extension_hash"] = self._hash(
            tampered,
            "extension_hash",
        )
        verification = self._verify(tampered, expected)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strata_report_extension_authority_invalid",
            verification["blockers"],
        )

    def test_external_expected_hash_cannot_be_replaced_by_document(self):
        document, expected = self._fixture()
        hostile_expected = dict(expected)
        hostile_expected["expected_classification_source_hash"] = "d" * 64
        verification = self._verify(document, hostile_expected)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                blocker.startswith(
                    "strata_report_registry_binding_invalid:"
                )
                for blocker in verification["blockers"]
            )
        )

    def test_package_and_script_style_imports_are_supported(self):
        project_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import services."
                    "strategy_correlation_complete_link_report_consumer; "
                    "import services."
                    "strategy_correlation_strata_report_consumer"
                ),
            ],
            cwd=project_root / "exchange_terminal",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
