from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 as subject,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as predecessor,
)


ROOT = Path(__file__).resolve().parents[1]


def _reseal(document: dict) -> dict:
    document.pop("consumer_preregistration_hash", None)
    document["consumer_preregistration_hash"] = subject.strict_canonical_hash(document)
    return document


class DeliveryAdapterConsumerPreregistrationV1Tests(unittest.TestCase):
    def build(self) -> dict:
        return subject.build_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1()

    def verify(self, document: object) -> bool:
        return subject.verify_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1(
            document
        )

    def test_exact_document_is_deterministic_and_verifies(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))
        core = dict(first)
        supplied_hash = core.pop("consumer_preregistration_hash")
        self.assertEqual(subject.strict_canonical_hash(core), supplied_hash)

    def test_identity_and_state_are_frozen(self) -> None:
        document = self.build()
        self.assertEqual(document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(document["preregistration_id"], subject.PREREGISTRATION_ID)
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(
            document["registration_state"],
            "DUAL_RUNTIME_CONSUMERS_PREREGISTERED_HOST_UNBOUND",
        )

    def test_predecessor_identity_source_and_subcontract_hashes_are_exact(self) -> None:
        contract = self.build()["predecessor_contract"]
        self.assertEqual(
            contract["registration_hash"], subject.PREDECESSOR_REGISTRATION_HASH
        )
        self.assertEqual(
            contract["asset_manifest_hash"],
            subject.PREDECESSOR_ASSET_MANIFEST_HASH,
        )
        self.assertEqual(
            contract["python_contract_hash"], subject.PYTHON_CONTRACT_HASH
        )
        self.assertEqual(
            contract["javascript_contract_hash"], subject.JAVASCRIPT_CONTRACT_HASH
        )
        self.assertEqual(
            contract["presentation_contract_hash"],
            subject.PRESENTATION_CONTRACT_HASH,
        )
        self.assertEqual(
            contract["transport_contract_hash"], subject.TRANSPORT_CONTRACT_HASH
        )
        self.assertEqual(
            contract["authority_hash"], subject.PREDECESSOR_AUTHORITY_HASH
        )
        self.assertEqual(
            contract["host_plan_hash"], subject.PREDECESSOR_HOST_PLAN_HASH
        )

    def test_consumer_order_and_ids_are_frozen(self) -> None:
        consumers = self.build()["consumer_contracts"]
        self.assertEqual(
            [consumer["consumer_id"] for consumer in consumers],
            [subject.PYTHON_CONSUMER_ID, subject.JAVASCRIPT_CONSUMER_ID],
        )
        self.assertEqual([consumer["runtime"] for consumer in consumers], [
            "PYTHON",
            "JAVASCRIPT",
        ])

    def test_python_consumer_is_hash_only_and_unbound(self) -> None:
        consumer = self.build()["consumer_contracts"][0]
        self.assertEqual(consumer["role"], "HASH_ONLY_IN_MEMORY_ENVELOPE_SOURCE")
        self.assertEqual(
            consumer["required_contract_hash"], subject.PYTHON_CONTRACT_HASH
        )
        self.assertEqual(
            consumer["required_transport_contract_hash"],
            subject.TRANSPORT_CONTRACT_HASH,
        )
        self.assertEqual(
            consumer["output_boundary"], "HASH_ONLY_IN_MEMORY_ENVELOPE_ONLY"
        )
        self.assertIsNone(consumer["implementation_binding"])
        self.assertIsNone(consumer["payload_source_provider"])
        self.assertIsNone(consumer["host_slot"])
        self.assertTrue(consumer["contract_preregistered"])
        self.assertFalse(consumer["implementation_bound"])
        self.assertFalse(consumer["execution_allowed"])
        self.assertFalse(consumer["route_allowed"])
        self.assertFalse(consumer["writer_allowed"])

    def test_javascript_consumer_is_unmounted_and_neutral(self) -> None:
        document = self.build()
        consumer = document["consumer_contracts"][1]
        predecessor_document = predecessor.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
        self.assertEqual(
            consumer["required_contract_hash"], subject.JAVASCRIPT_CONTRACT_HASH
        )
        self.assertEqual(
            consumer["required_presentation_contract_hash"],
            subject.PRESENTATION_CONTRACT_HASH,
        )
        self.assertEqual(
            consumer["required_stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(
            consumer["required_relative_load_order"],
            predecessor_document["javascript_contract"]["relative_load_order"],
        )
        self.assertIsNone(consumer["module_binding"])
        self.assertIsNone(consumer["html_script_binding"])
        self.assertIsNone(consumer["stylesheet_link_binding"])
        self.assertIsNone(consumer["mount_slot"])
        self.assertFalse(consumer["browser_execution_allowed"])
        self.assertFalse(consumer["dom_mount_allowed"])
        self.assertFalse(consumer["runtime_asset_loading_allowed"])

    def test_activation_order_is_consumer_first_and_current_last(self) -> None:
        order = self.build()["activation_order"]
        self.assertEqual(order[0], "VERIFY_EXACT_ADR0309_ADAPTER_REGISTRATION")
        self.assertEqual(order[1], "VERIFY_ADR0310_CONSUMER_PREREGISTRATION")
        self.assertLess(
            order.index("IMPLEMENT_PYTHON_HASH_ONLY_SOURCE_IN_SEPARATE_VERSION"),
            order.index("DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION"),
        )
        self.assertLess(
            order.index(
                "IMPLEMENT_JAVASCRIPT_INSPECTION_CONSUMER_IN_SEPARATE_VERSION"
            ),
            order.index("DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION"),
        )
        self.assertEqual(
            order[-1], "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION"
        )

    def test_host_plan_is_entirely_unbound(self) -> None:
        host_plan = self.build()["host_plan"]
        self.assertTrue(host_plan)
        self.assertTrue(all(value is None for value in host_plan.values()))

    def test_authority_is_entirely_false(self) -> None:
        authority = self.build()["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_facts_and_blockers_reject_activation_claims(self) -> None:
        document = self.build()
        facts = document["facts"]
        self.assertTrue(facts["consumer_contracts_preregistered"])
        self.assertFalse(facts["python_consumer_implemented"])
        self.assertFalse(facts["javascript_consumer_implemented"])
        self.assertFalse(facts["host_bindings_declared"])
        self.assertFalse(facts["runtime_mutations_performed"])
        self.assertFalse(facts["profitability_proven"])
        self.assertIn("CURRENT_ACTIVATION_NOT_AUTHORIZED", document["blockers"])
        self.assertIn(
            "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED", document["blockers"]
        )

    def test_resealed_predecessor_builder_drift_fails_closed(self) -> None:
        drifted = predecessor.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
        drifted["registration_id"] = "drifted"
        drifted.pop("adapter_registration_hash")
        drifted["adapter_registration_hash"] = predecessor.strict_canonical_hash(
            drifted
        )
        with patch.object(
            subject,
            "build_adapter_registration_v1",
            return_value=drifted,
        ):
            with self.assertRaises(ValueError):
                self.build()

    def test_resealed_predecessor_reference_drift_is_rejected(self) -> None:
        document = self.build()
        document["predecessor_contract"]["registration_hash"] = "0" * 64
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_subcontract_hash_drift_is_rejected(self) -> None:
        document = self.build()
        document["predecessor_contract"]["javascript_contract_hash"] = "1" * 64
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_consumer_binding_injection_is_rejected(self) -> None:
        document = self.build()
        consumer = document["consumer_contracts"][0]
        consumer["implementation_binding"] = "exchange_terminal.server"
        consumer["implementation_bound"] = True
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_consumer_reordering_is_rejected(self) -> None:
        document = self.build()
        document["consumer_contracts"].reverse()
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_host_plan_injection_is_rejected(self) -> None:
        document = self.build()
        document["host_plan"]["route"] = "/api/correlation"
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        document = self.build()
        document["authority"]["consumer_execution_allowed"] = True
        self.assertFalse(self.verify(_reseal(document)))

    def test_resealed_extra_field_is_rejected(self) -> None:
        document = self.build()
        document["extension"] = {"enabled": False}
        self.assertFalse(self.verify(_reseal(document)))

    def test_non_native_and_cyclic_documents_are_rejected(self) -> None:
        self.assertFalse(self.verify({"value": object()}))
        self.assertFalse(self.verify({"value": ("tuple",)}))
        cyclic: dict = {}
        cyclic["cycle"] = cyclic
        self.assertFalse(self.verify(cyclic))

    def test_predecessor_source_files_match_declared_hashes(self) -> None:
        expected = {
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_in_memory_"
                "delivery_adapter_registration_v1.py"
            ): subject.PREDECESSOR_IMPLEMENTATION_SHA256,
            (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_adapter_registration_v1.py"
            ): subject.PREDECESSOR_TEST_SHA256,
            (
                "docs/adr/0309-portfolio-correlation-admission-effective-"
                "budget-in-memory-delivery-adapter-registration-v1.md"
            ): subject.PREDECESSOR_ADR_SHA256,
        }
        for relative_path, expected_hash in expected.items():
            with self.subTest(relative_path=relative_path):
                actual_hash = hashlib.sha256(
                    (ROOT / relative_path).read_bytes()
                ).hexdigest()
                self.assertEqual(actual_hash, expected_hash)

    def test_production_module_has_no_host_or_io_capability(self) -> None:
        source = Path(subject.__file__).read_text(encoding="utf-8")
        forbidden = (
            "import requests",
            "from requests",
            "import socket",
            "from socket",
            "urllib.",
            "subprocess.",
            "open(",
            "Path(",
            "os.environ",
            "sqlite3",
            "http.client",
            "flask",
            "fastapi",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        canonical = subject.strict_canonical_hash(self.build())
        self.assertEqual(len(canonical), 64)


if __name__ == "__main__":
    unittest.main()
