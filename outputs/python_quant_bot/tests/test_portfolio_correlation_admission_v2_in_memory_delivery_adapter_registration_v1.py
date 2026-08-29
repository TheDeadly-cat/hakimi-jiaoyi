from __future__ import annotations

import copy
import hashlib
import re
import unittest
from pathlib import Path

from exchange_terminal.services.portfolio_correlation_admission_v2 import (
    build_portfolio_correlation_admission_v2,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_consumer_preregistration_v1 import (
    build_portfolio_correlation_admission_v2_consumer_binding_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1 import (
    ADR0301_SHA256,
    JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
    JAVASCRIPT_ADAPTER_TEST_SHA256,
    PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
    PYTHON_ADAPTER_TEST_SHA256,
    STRICT_CANONICAL_JS_SHA256,
    build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1,
    build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1,
    verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1,
    verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_portfolio_correlation_admission_v1 import FlippingMapping
from tests.test_portfolio_correlation_admission_v2_in_memory_delivery_v1 import (
    PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PortfolioCorrelationAdmissionV2InMemoryDeliveryAdapterRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.delivery = PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests(
            methodName="runTest"
        )
        self.delivery.setUp()
        self.registration = (
            build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1()
        )
        self.binding = self._binding()

    def _binding(
        self,
        *,
        adapter_registration: object | None = None,
        envelope: object | None = None,
        consumer_binding: object | None = None,
        candidate: object | None = None,
        evidence: dict | None = None,
    ) -> dict:
        d = self.delivery
        source = d.evidence if evidence is None else evidence
        return build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1(
            self.registration if adapter_registration is None else adapter_registration,
            d.envelope if envelope is None else envelope,
            d.registration,
            d.binding if consumer_binding is None else consumer_binding,
            d.candidate if candidate is None else candidate,
            **source,
        )

    def _verify(self, document: object) -> bool:
        d = self.delivery
        return verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1(
            document,
            self.registration,
            d.envelope,
            d.registration,
            d.binding,
            d.candidate,
            **d.evidence,
        )

    def test_registration_is_blocked_unbound_and_exact(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "PYTHON_AND_JAVASCRIPT_DELIVERY_ADAPTERS_REGISTERED_UNBOUND",
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(
                self.registration
            )
        )

    def test_registration_pins_all_adr0301_assets_and_dependency(self) -> None:
        python = self.registration["python_contract"]
        javascript = self.registration["javascript_contract"]
        dependencies = self.registration["dependency_manifest"]
        self.assertEqual(python["implementation_sha256"], PYTHON_ADAPTER_IMPLEMENTATION_SHA256)
        self.assertEqual(python["test_sha256"], PYTHON_ADAPTER_TEST_SHA256)
        self.assertEqual(javascript["implementation_sha256"], JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256)
        self.assertEqual(javascript["test_sha256"], JAVASCRIPT_ADAPTER_TEST_SHA256)
        self.assertEqual(dependencies["adr0301_sha256"], ADR0301_SHA256)
        self.assertEqual(dependencies["strict_canonical_javascript_sha256"], STRICT_CANONICAL_JS_SHA256)

    def test_pinned_hashes_match_explicit_current_source_paths(self) -> None:
        paths = {
            PYTHON_ADAPTER_IMPLEMENTATION_SHA256: PROJECT_ROOT / "exchange_terminal/services/portfolio_correlation_admission_v2_in_memory_delivery_v1.py",
            PYTHON_ADAPTER_TEST_SHA256: PROJECT_ROOT / "tests/test_portfolio_correlation_admission_v2_in_memory_delivery_v1.py",
            JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256: PROJECT_ROOT / "exchange_terminal/static/evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js",
            JAVASCRIPT_ADAPTER_TEST_SHA256: PROJECT_ROOT / "exchange_terminal/static/evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.test.js",
            ADR0301_SHA256: PROJECT_ROOT / "docs/adr/0301-portfolio-correlation-admission-v2-in-memory-delivery-v1.md",
            STRICT_CANONICAL_JS_SHA256: PROJECT_ROOT / "exchange_terminal/static/strict_canonical_json_v1.js",
        }
        for expected, path in paths.items():
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_javascript_exports_and_relative_load_order_are_exact(self) -> None:
        contract = self.registration["javascript_contract"]
        self.assertEqual(len(contract["function_exports"]), 5)
        self.assertEqual(
            contract["relative_load_order"],
            [
                "strict_canonical_json_v1.js",
                "evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js",
            ],
        )

    def test_host_plan_remains_fully_empty(self) -> None:
        self.assertTrue(
            all(value is None for value in self.registration["host_plan"].values())
        )

    def test_registration_records_no_adapter_or_presentation_execution(self) -> None:
        facts = self.registration["facts"]
        self.assertFalse(facts["registration_invoked_python_adapter"])
        self.assertFalse(facts["registration_loaded_javascript_adapter"])
        self.assertFalse(facts["adapter_execution_observed"])
        self.assertFalse(facts["presentation_consumer_executed"])
        self.assertFalse(facts["render_called"])
        self.assertFalse(facts["dom_accessed"])
        self.assertFalse(facts["browser_executed"])

    def test_exact_envelope_builds_blocked_hash_only_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "REGISTERED_DUAL_RUNTIME_ADAPTERS_AND_EXACT_ENVELOPE_HASH_BOUND_EXECUTION_UNAUTHORIZED",
        )
        self.assertEqual(
            self.binding["source"]["delivery_envelope_hash"],
            self.delivery.envelope["delivery_envelope_hash"],
        )
        self.assertTrue(self._verify(self.binding))

    def test_exact_common_universe_block_envelope_can_be_integrity_bound(self) -> None:
        evidence, candidate, envelope = self.delivery._block_fixture()
        consumer_binding = build_portfolio_correlation_admission_v2_consumer_binding_v1(
            self.delivery.registration,
            candidate,
            **evidence,
        )
        binding = self._binding(
            envelope=envelope,
            consumer_binding=consumer_binding,
            candidate=candidate,
            evidence=evidence,
        )
        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(binding["status"], "BLOCKED")
        self.assertEqual(
            binding["source"]["candidate_hash"],
            candidate["correlation_admission_v2_hash"],
        )

    def test_binding_contains_hashes_not_envelope_payload_or_symbols(self) -> None:
        self.assertNotIn("delivery_envelope", self.binding)
        self.assertNotIn("presentation_payload", self.binding)
        self.assertNotIn("AAA", repr(self.binding))
        self.assertFalse(self.binding["facts"]["raw_delivery_envelope_embedded"])
        self.assertFalse(self.binding["facts"]["raw_presentation_payload_embedded"])
        self.assertFalse(self.binding["facts"]["raw_source_documents_embedded"])

    def test_tampered_registration_envelope_or_source_returns_unknown(self) -> None:
        registration = copy.deepcopy(self.registration)
        registration["facts"]["adapter_execution_observed"] = True
        envelope = copy.deepcopy(self.delivery.envelope)
        envelope["facts"]["delivery_attempted"] = True
        spliced = copy.deepcopy(self.delivery.evidence)
        spliced["strategy_id"] = "strategy-spliced"
        self.assertEqual(self._binding(adapter_registration=registration)["status"], "UNKNOWN")
        self.assertEqual(self._binding(envelope=envelope)["status"], "UNKNOWN")
        self.assertEqual(self._binding(evidence=spliced)["status"], "UNKNOWN")

    def test_non_native_or_cyclic_input_returns_unknown(self) -> None:
        non_native = self._binding(envelope=FlippingMapping(self.delivery.envelope))
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        cyclic_result = self._binding(adapter_registration=cyclic)
        self.assertEqual(non_native["reason_code"], "INPUT_SNAPSHOT_FAILED")
        self.assertEqual(cyclic_result["reason_code"], "INPUT_SNAPSHOT_FAILED")

    def test_resealed_binding_promotion_fails_exact_verifier(self) -> None:
        promoted = copy.deepcopy(self.binding)
        promoted["facts"]["adapter_execution_observed"] = True
        promoted.pop("adapter_binding_hash")
        promoted = seal_strict_canonical_document(promoted, "adapter_binding_hash")
        self.assertFalse(self._verify(promoted))

    def test_binding_authority_remains_fully_locked(self) -> None:
        authority = self.binding["authority"]
        self.assertFalse(authority["payload_source_registration_allowed"])
        self.assertFalse(authority["presentation_registration_allowed"])
        self.assertFalse(authority["stylesheet_registration_allowed"])
        self.assertFalse(authority["host_asset_write_allowed"])
        self.assertFalse(authority["adapter_execution_allowed"])
        self.assertFalse(authority["presentation_consumer_execution_allowed"])
        self.assertFalse(authority["render_allowed"])
        self.assertFalse(authority["dom_access_allowed"])
        self.assertFalse(authority["browser_execution_allowed"])
        self.assertFalse(authority["current_admission_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_registration_and_binding_have_no_promotional_copy(self) -> None:
        strings: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)
            elif isinstance(value, str):
                strings.append(value)

        collect(self.registration)
        collect(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(strings),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_builders_are_deterministic_and_do_not_mutate_inputs(self) -> None:
        before_registration = copy.deepcopy(self.registration)
        before_envelope = copy.deepcopy(self.delivery.envelope)
        before_evidence = copy.deepcopy(self.delivery.evidence)
        self.assertEqual(self.binding, self._binding())
        self.assertEqual(
            self.registration,
            build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(),
        )
        self.assertEqual(self.registration, before_registration)
        self.assertEqual(self.delivery.envelope, before_envelope)
        self.assertEqual(self.delivery.evidence, before_evidence)


if __name__ == "__main__":
    unittest.main()
