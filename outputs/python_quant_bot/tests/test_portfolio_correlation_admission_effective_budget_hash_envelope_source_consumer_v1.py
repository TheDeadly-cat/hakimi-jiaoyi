from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1 as preregistration,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 as subject,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1 as adapter_registration,
)
from tests import (
    test_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 as delivery_fixtures,
)


ROOT = Path(__file__).resolve().parents[1]


def _reseal_result(document: dict) -> dict:
    document.pop("consumer_result_hash", None)
    document["consumer_result_hash"] = subject.strict_canonical_hash(document)
    return document


class HashEnvelopeSourceConsumerV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.delivery_case = (
            delivery_fixtures.PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests(
                methodName="test_exact_pass_binding_builds_known_envelope"
            )
        )
        self.delivery_case.setUp()
        self.fixture = self.delivery_case.fixture
        self.adapter_registration = adapter_registration.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_adapter_registration_v1()
        self.consumer_preregistration = preregistration.build_portfolio_correlation_admission_effective_budget_delivery_adapter_consumer_preregistration_v1()

    def arguments(
        self,
        *,
        binding: object | None = None,
        budget: object | None = None,
        inputs: dict | None = None,
        adapter: object | None = None,
        prereg: object | None = None,
    ) -> dict:
        evidence = self.fixture.evidence
        clean_inputs = self.fixture.inputs if inputs is None else inputs
        return {
            "adapter_registration_document": (
                self.adapter_registration if adapter is None else adapter
            ),
            "consumer_preregistration_document": (
                self.consumer_preregistration if prereg is None else prereg
            ),
            "binding_document": (
                self.delivery_case.binding if binding is None else binding
            ),
            "admission_v2_document": self.fixture.admission,
            "effective_budget_v3_document": (
                self.fixture.budget if budget is None else budget
            ),
            "report_document": evidence["report_document"],
            "correlation_preregistration_document": evidence[
                "correlation_preregistration_document"
            ],
            "correlation_matrix_document": evidence[
                "correlation_matrix_document"
            ],
            "selection_cells_document": evidence["selection_cells_document"],
            "complete_link_audit_document": self.fixture.budget_case.audit,
            "complete_link_gate_document": evidence[
                "complete_link_gate_document"
            ],
            "strata_preregistration_document": evidence[
                "strata_preregistration_document"
            ],
            "strata_gate_document": evidence["strata_gate_document"],
            "strategy_id": evidence["strategy_id"],
            "variant_id": evidence["variant_id"],
            "lane": evidence["lane"],
            "equity": clean_inputs["equity"],
            "positions": clean_inputs["positions"],
            "proposed_symbol": clean_inputs["proposed_symbol"],
            "proposed_notional": clean_inputs["proposed_notional"],
            "proposed_direction": clean_inputs["proposed_direction"],
            "max_cluster_gross_pct": clean_inputs["max_cluster_gross_pct"],
            "risk_increasing": clean_inputs["risk_increasing"],
        }

    def build(self, **overrides: object) -> dict:
        return subject.build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
            **self.arguments(**overrides)
        )

    def verify(self, document: object, **overrides: object) -> bool:
        return subject.verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
            document,
            **self.arguments(**overrides),
        )

    def test_exact_gate_builds_deterministic_verified_known_result(self) -> None:
        arguments = self.arguments()
        before = deepcopy(arguments)
        first = subject.build_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1(
            **arguments
        )
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(arguments, before)
        self.assertTrue(self.verify(first))
        self.assertEqual(first["status"], "KNOWN")
        self.assertEqual(
            first["reason_code"],
            "EXACT_CONSUMER_GATE_KNOWN_ENVELOPE_RETURNED",
        )

    def test_exact_result_reuses_the_existing_delivery_envelope(self) -> None:
        result = self.build()
        self.assertEqual(result["envelope"], self.delivery_case.envelope)
        self.assertEqual(
            result["envelope_hash"],
            self.delivery_case.envelope["delivery_envelope_hash"],
        )
        self.assertTrue(result["facts"]["adapter_invoked"])
        self.assertTrue(result["facts"]["envelope_verified"])

    def test_exact_admission_block_remains_known_not_authorized(self) -> None:
        result = self.build(
            binding=self.delivery_case.blocked_binding,
            budget=self.delivery_case.blocked_budget,
            inputs=self.delivery_case.concentrated_inputs,
        )
        self.assertTrue(
            self.verify(
                result,
                binding=self.delivery_case.blocked_binding,
                budget=self.delivery_case.blocked_budget,
                inputs=self.delivery_case.concentrated_inputs,
            )
        )
        self.assertEqual(result["status"], "KNOWN")
        self.assertEqual(result["envelope"], self.delivery_case.blocked_envelope)
        self.assertFalse(result["authority"]["current_admission_allowed"])

    def test_malformed_binding_returns_verified_unknown_envelope(self) -> None:
        malformed = {"schema_version": "not-a-binding"}
        result = self.build(binding=malformed)
        self.assertTrue(self.verify(result, binding=malformed))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "EXACT_CONSUMER_GATE_UNKNOWN_ENVELOPE_RETURNED",
        )
        self.assertIsNotNone(result["envelope"])
        self.assertEqual(result["envelope"]["status"], "UNKNOWN")
        self.assertIn("SOURCE_ENVELOPE_UNKNOWN", result["blockers"])

    def test_drifted_adapter_registration_blocks_before_invocation(self) -> None:
        drifted = deepcopy(self.adapter_registration)
        drifted["registration_id"] = "drifted"
        drifted.pop("adapter_registration_hash")
        drifted["adapter_registration_hash"] = subject.strict_canonical_hash(
            drifted
        )
        with patch.object(subject, "build_delivery_envelope_v1") as builder:
            result = self.build(adapter=drifted)
        builder.assert_not_called()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reason_code"],
            "CONSUMER_GATE_REJECTED_NO_ADAPTER_INVOCATION",
        )
        self.assertFalse(result["facts"]["adapter_invoked"])
        self.assertIsNone(result["envelope"])
        self.assertTrue(self.verify(result, adapter=drifted))
        self.assertFalse(self.verify(result))

    def test_drifted_consumer_preregistration_blocks_before_invocation(self) -> None:
        drifted = deepcopy(self.consumer_preregistration)
        drifted["consumer_contracts"][0]["implementation_binding"] = "host.module"
        drifted["consumer_contracts"][0]["implementation_bound"] = True
        drifted.pop("consumer_preregistration_hash")
        drifted["consumer_preregistration_hash"] = subject.strict_canonical_hash(
            drifted
        )
        with patch.object(subject, "build_delivery_envelope_v1") as builder:
            result = self.build(prereg=drifted)
        builder.assert_not_called()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["gate"]["consumer_preregistration_exact"])
        self.assertIsNone(result["envelope_hash"])
        self.assertTrue(self.verify(result, prereg=drifted))

    def test_non_native_gate_document_blocks_without_adapter_call(self) -> None:
        with patch.object(subject, "build_delivery_envelope_v1") as builder:
            result = self.build(adapter={"value": object()})
        builder.assert_not_called()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["gate"]["adapter_registration_exact"])

    def test_adapter_verification_failure_drops_candidate_envelope(self) -> None:
        with patch.object(
            subject, "verify_delivery_envelope_v1", return_value=False
        ):
            result = self.build()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reason_code"], "ADAPTER_ENVELOPE_VERIFICATION_FAILED"
        )
        self.assertTrue(result["facts"]["adapter_invoked"])
        self.assertFalse(result["facts"]["envelope_verified"])
        self.assertIsNone(result["envelope"])
        self.assertIsNone(result["envelope_hash"])

    def test_gate_contract_hashes_and_identity_are_frozen(self) -> None:
        result = self.build()
        required = result["required_contracts"]
        self.assertEqual(result["consumer_id"], subject.CONSUMER_ID)
        self.assertEqual(
            required["adapter_registration_hash"],
            subject.ADAPTER_REGISTRATION_HASH,
        )
        self.assertEqual(
            required["consumer_preregistration_hash"],
            subject.CONSUMER_PREREGISTRATION_HASH,
        )
        self.assertEqual(
            required["python_consumer_contract_hash"],
            subject.PYTHON_CONSUMER_CONTRACT_HASH,
        )
        self.assertTrue(all(result["gate"].values()))

    def test_result_contains_hashes_not_source_documents(self) -> None:
        result = self.build()
        self.assertFalse(result["facts"]["input_documents_embedded"])
        self.assertEqual(
            sorted(result["source_hashes"]),
            [
                "admission_v2_hash",
                "binding_hash",
                "effective_budget_v3_hash",
                "presentation_payload_hash",
            ],
        )
        for value in result["source_hashes"].values():
            self.assertIsInstance(value, str)
            self.assertEqual(len(value), 64)
        serialized = repr(result).lower()
        for forbidden in (
            "'positions'",
            "'proposed_symbol'",
            "'account_id'",
            "'prices'",
            "'returns'",
            "'bars'",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_transport_and_authority_remain_locked(self) -> None:
        result = self.build()
        self.assertEqual(result["transport"]["mode"], "IN_MEMORY_RETURN_ONLY")
        self.assertIsNone(result["transport"]["payload_source_provider"])
        self.assertIsNone(result["transport"]["route"])
        self.assertIsNone(result["transport"]["endpoint"])
        self.assertFalse(result["transport"]["storage_used"])
        self.assertFalse(result["transport"]["network_used"])
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )

    def test_result_hash_is_exact(self) -> None:
        result = self.build()
        core = dict(result)
        supplied_hash = core.pop("consumer_result_hash")
        self.assertEqual(subject.strict_canonical_hash(core), supplied_hash)

    def test_resealed_envelope_mutation_is_rejected(self) -> None:
        result = self.build()
        result["envelope"]["authority"]["paper_authorized"] = True
        result["envelope"].pop("delivery_envelope_hash")
        result["envelope"]["delivery_envelope_hash"] = subject.strict_canonical_hash(
            result["envelope"]
        )
        self.assertFalse(self.verify(_reseal_result(result)))

    def test_resealed_gate_mutation_is_rejected(self) -> None:
        result = self.build()
        result["gate"]["python_consumer_unbound"] = False
        self.assertFalse(self.verify(_reseal_result(result)))

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        result = self.build()
        result["authority"]["runtime_delivery_allowed"] = True
        self.assertFalse(self.verify(_reseal_result(result)))

    def test_resealed_extra_field_is_rejected(self) -> None:
        result = self.build()
        result["extension"] = {"enabled": False}
        self.assertFalse(self.verify(_reseal_result(result)))

    def test_non_native_and_cyclic_result_are_rejected(self) -> None:
        self.assertFalse(self.verify({"value": object()}))
        self.assertFalse(self.verify({"value": ("tuple",)}))
        cyclic: dict = {}
        cyclic["cycle"] = cyclic
        self.assertFalse(self.verify(cyclic))

    def test_predecessor_source_pins_match_current_files(self) -> None:
        expected = {
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_delivery_"
                "adapter_consumer_preregistration_v1.py"
            ): subject.PREREGISTRATION_IMPLEMENTATION_SHA256,
            (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "delivery_adapter_consumer_preregistration_v1.py"
            ): subject.PREREGISTRATION_TEST_SHA256,
            (
                "docs/adr/0310-portfolio-correlation-admission-effective-"
                "budget-delivery-adapter-consumer-preregistration-v1.md"
            ): subject.PREREGISTRATION_ADR_SHA256,
            (
                "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_in_memory_"
                "delivery_v1.py"
            ): subject.DELIVERY_IMPLEMENTATION_SHA256,
            (
                "tests/test_portfolio_correlation_admission_effective_budget_"
                "in_memory_delivery_v1.py"
            ): subject.DELIVERY_TEST_SHA256,
        }
        for relative_path, expected_hash in expected.items():
            with self.subTest(relative_path=relative_path):
                actual = hashlib.sha256(
                    (ROOT / relative_path).read_bytes()
                ).hexdigest()
                self.assertEqual(actual, expected_hash)

    def test_production_module_has_no_io_host_or_runtime_capability(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
