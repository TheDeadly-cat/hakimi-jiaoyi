from __future__ import annotations

import copy
import re
import unittest

from exchange_terminal.services.portfolio_correlation_admission_v2 import (
    build_portfolio_correlation_admission_v2,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_consumer_preregistration_v1 import (
    build_portfolio_correlation_admission_v2_consumer_binding_v1,
    build_portfolio_correlation_admission_v2_consumer_preregistration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_in_memory_delivery_v1 import (
    CONSUMER_PREREGISTRATION_HASH,
    PAYLOAD_SCHEMA_VERSION,
    build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1,
    verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_portfolio_correlation_admission_v1 import FlippingMapping
from tests.test_portfolio_correlation_admission_v2 import (
    PortfolioCorrelationAdmissionV2Tests,
)


class PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = PortfolioCorrelationAdmissionV2Tests(methodName="runTest")
        self.evidence = self.fixture._evidence()
        self.candidate = build_portfolio_correlation_admission_v2(**self.evidence)
        self.registration = (
            build_portfolio_correlation_admission_v2_consumer_preregistration_v1()
        )
        self.binding = build_portfolio_correlation_admission_v2_consumer_binding_v1(
            self.registration,
            self.candidate,
            **self.evidence,
        )
        self.envelope = self._envelope()

    def _envelope(
        self,
        *,
        registration: object | None = None,
        binding: object | None = None,
        candidate: object | None = None,
        evidence: dict | None = None,
    ) -> dict:
        source = self.evidence if evidence is None else evidence
        return build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
            self.registration if registration is None else registration,
            self.binding if binding is None else binding,
            self.candidate if candidate is None else candidate,
            **source,
        )

    def _verify(self, document: object) -> bool:
        return verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
            document,
            self.registration,
            self.binding,
            self.candidate,
            **self.evidence,
        )

    def _block_fixture(self) -> tuple[dict, dict, dict]:
        evidence = self.fixture._replace_universe(
            self.fixture._evidence(),
            ["CCC", "DDD"],
            selection_basis="IN_MEMORY_DELIVERY_BLOCK_FIXTURE",
        )
        candidate = build_portfolio_correlation_admission_v2(**evidence)
        binding = build_portfolio_correlation_admission_v2_consumer_binding_v1(
            self.registration,
            candidate,
            **evidence,
        )
        envelope = self._envelope(
            binding=binding,
            candidate=candidate,
            evidence=evidence,
        )
        return evidence, candidate, envelope

    def test_exact_chain_builds_blocked_endpoint_free_envelope(self) -> None:
        self.assertEqual(self.envelope["status"], "BLOCKED")
        self.assertEqual(
            self.envelope["delivery_state"],
            "EXACT_V2_PRESENTATION_PAYLOAD_ENVELOPED_IN_MEMORY_CONSUMER_UNBOUND",
        )
        self.assertTrue(self._verify(self.envelope))

    def test_transport_is_in_memory_no_store_and_endpoint_free(self) -> None:
        transport = self.envelope["transport"]
        self.assertEqual(transport["mode"], "IN_MEMORY_JSON_DOCUMENT")
        self.assertEqual(transport["cache_policy"], "NO_STORE")
        self.assertIsNone(transport["endpoint"])
        self.assertIsNone(transport["route"])
        self.assertFalse(transport["wire_bytes_built"])
        self.assertFalse(transport["network_transport_used"])
        self.assertFalse(transport["persistent_storage_used"])

    def test_pass_payload_is_bounded_hash_only_projection(self) -> None:
        payload = self.envelope["presentation_payload"]
        self.assertEqual(payload["schema_version"], PAYLOAD_SCHEMA_VERSION)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["candidate_hash"], self.candidate["correlation_admission_v2_hash"])
        self.assertNotIn("strategy_id", payload)
        self.assertNotIn("variant_id", payload)
        self.assertNotIn("evidence_hashes", payload)
        self.assertFalse(payload["facts"]["raw_v2_candidate_embedded"])
        self.assertNotIn("AAA", repr(payload))

    def test_exact_common_universe_block_is_delivered_without_v1_hash(self) -> None:
        _, candidate, envelope = self._block_fixture()
        payload = envelope["presentation_payload"]
        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(payload["status"], "BLOCK")
        self.assertEqual(payload["first_blocking_tier"], "COMMON_UNIVERSE")
        self.assertEqual(payload["v1_admission_status"], "NOT_EVALUATED")
        self.assertEqual(envelope["status"], "BLOCKED")

    def test_envelope_pins_exact_registration_binding_and_candidate_hashes(self) -> None:
        provenance = self.envelope["provenance"]
        self.assertEqual(
            provenance["consumer_preregistration_hash"],
            CONSUMER_PREREGISTRATION_HASH,
        )
        self.assertEqual(
            provenance["consumer_binding_hash"],
            self.binding["consumer_binding_hash"],
        )
        self.assertEqual(
            provenance["candidate_hash"],
            self.candidate["correlation_admission_v2_hash"],
        )

    def test_tampered_registration_binding_or_candidate_returns_unknown(self) -> None:
        registration = copy.deepcopy(self.registration)
        registration["facts"]["delivery_adapter_registered"] = True
        binding = copy.deepcopy(self.binding)
        binding["facts"]["consumer_executed"] = True
        candidate = copy.deepcopy(self.candidate)
        candidate["permissions"]["paper_authorized"] = True
        self.assertEqual(self._envelope(registration=registration)["status"], "UNKNOWN")
        self.assertEqual(self._envelope(binding=binding)["status"], "UNKNOWN")
        self.assertEqual(self._envelope(candidate=candidate)["status"], "UNKNOWN")

    def test_source_context_splice_returns_unknown_without_payload(self) -> None:
        spliced = copy.deepcopy(self.evidence)
        spliced["lane"] = "RISK_ADJUSTED"
        result = self._envelope(evidence=spliced)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["presentation_payload"])

    def test_non_native_or_cyclic_input_returns_unknown(self) -> None:
        non_native = self._envelope(candidate=FlippingMapping(self.candidate))
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        cyclic_result = self._envelope(binding=cyclic)
        self.assertEqual(non_native["reason_code"], "INPUT_SNAPSHOT_FAILED")
        self.assertEqual(cyclic_result["reason_code"], "INPUT_SNAPSHOT_FAILED")

    def test_unknown_envelope_contains_no_payload_or_verified_facts(self) -> None:
        result = self._envelope(binding={})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["presentation_payload"])
        self.assertFalse(result["facts"]["consumer_binding_exactly_verified"])
        self.assertFalse(result["facts"]["bounded_presentation_payload_embedded"])

    def test_resealed_envelope_promotion_fails_exact_verifier(self) -> None:
        promoted = copy.deepcopy(self.envelope)
        promoted["facts"]["delivery_attempted"] = True
        promoted.pop("delivery_envelope_hash")
        promoted = seal_strict_canonical_document(promoted, "delivery_envelope_hash")
        self.assertFalse(self._verify(promoted))

    def test_delivery_render_and_permission_authority_remains_locked(self) -> None:
        facts = self.envelope["facts"]
        authority = self.envelope["authority"]
        self.assertFalse(facts["delivery_attempted"])
        self.assertFalse(facts["payload_extracted"])
        self.assertFalse(facts["presentation_consumer_executed"])
        self.assertFalse(facts["render_called"])
        self.assertFalse(facts["dom_accessed"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["ui_mounted"])
        self.assertFalse(authority["wire_transport_allowed"])
        self.assertFalse(authority["presentation_consumer_execution_allowed"])
        self.assertFalse(authority["current_admission_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_envelope_has_no_promotional_copy(self) -> None:
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

        collect(self.envelope)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(strings),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.envelope["facts"]["profitability_proven"])

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        before_registration = copy.deepcopy(self.registration)
        before_binding = copy.deepcopy(self.binding)
        before_candidate = copy.deepcopy(self.candidate)
        before_evidence = copy.deepcopy(self.evidence)
        self.assertEqual(self.envelope, self._envelope())
        self.assertEqual(self.registration, before_registration)
        self.assertEqual(self.binding, before_binding)
        self.assertEqual(self.candidate, before_candidate)
        self.assertEqual(self.evidence, before_evidence)


if __name__ == "__main__":
    unittest.main()
