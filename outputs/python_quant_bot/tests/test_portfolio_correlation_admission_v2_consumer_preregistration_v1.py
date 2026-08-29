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
    ADR0299_SHA256,
    V1_IMPLEMENTATION_SHA256,
    V2_CONTRACT_TEST_SHA256,
    V2_IMPLEMENTATION_SHA256,
    build_portfolio_correlation_admission_v2_consumer_binding_v1,
    build_portfolio_correlation_admission_v2_consumer_preregistration_v1,
    verify_portfolio_correlation_admission_v2_consumer_binding_v1,
    verify_portfolio_correlation_admission_v2_consumer_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_portfolio_correlation_admission_v1 import FlippingMapping
from tests.test_portfolio_correlation_admission_v2 import (
    PortfolioCorrelationAdmissionV2Tests,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PortfolioCorrelationAdmissionV2ConsumerPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = PortfolioCorrelationAdmissionV2Tests(methodName="runTest")
        self.evidence = self.fixture._evidence()
        self.candidate = build_portfolio_correlation_admission_v2(**self.evidence)
        self.registration = (
            build_portfolio_correlation_admission_v2_consumer_preregistration_v1()
        )
        self.binding = self._binding()

    def _binding(
        self,
        *,
        registration: object | None = None,
        candidate: object | None = None,
        evidence: dict | None = None,
    ) -> dict:
        source = self.evidence if evidence is None else evidence
        return build_portfolio_correlation_admission_v2_consumer_binding_v1(
            self.registration if registration is None else registration,
            self.candidate if candidate is None else candidate,
            **source,
        )

    def _verify(self, document: object) -> bool:
        return verify_portfolio_correlation_admission_v2_consumer_binding_v1(
            document,
            self.registration,
            self.candidate,
            **self.evidence,
        )

    def test_registration_is_blocked_unbound_and_exact(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "V2_CONSUMER_PREREGISTERED_UNBOUND",
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_v2_consumer_preregistration_v1(
                self.registration
            )
        )

    def test_registration_pins_exact_v1_v2_and_adr0299_sources(self) -> None:
        producer = self.registration["producer_contract"]
        predecessor = self.registration["predecessor_contract"]
        self.assertEqual(producer["implementation_sha256"], V2_IMPLEMENTATION_SHA256)
        self.assertEqual(producer["test_sha256"], V2_CONTRACT_TEST_SHA256)
        self.assertEqual(producer["adr_sha256"], ADR0299_SHA256)
        self.assertEqual(predecessor["implementation_sha256"], V1_IMPLEMENTATION_SHA256)
        self.assertTrue(predecessor["compatibility_unchanged"])

    def test_pinned_source_hashes_match_current_explicit_source_paths(self) -> None:
        paths = {
            V1_IMPLEMENTATION_SHA256: PROJECT_ROOT / "exchange_terminal/services/portfolio_correlation_admission_v1.py",
            V2_IMPLEMENTATION_SHA256: PROJECT_ROOT / "exchange_terminal/services/portfolio_correlation_admission_v2.py",
            V2_CONTRACT_TEST_SHA256: PROJECT_ROOT / "tests/test_portfolio_correlation_admission_v2.py",
            ADR0299_SHA256: PROJECT_ROOT / "docs/adr/0299-portfolio-correlation-common-universe-binding-v2.md",
        }
        for expected, path in paths.items():
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_registration_leaves_all_consumers_and_host_bindings_absent(self) -> None:
        contract = self.registration["consumer_contract"]
        self.assertIsNone(contract["delivery_adapter"])
        self.assertIsNone(contract["presentation_consumer"])
        self.assertIsNone(contract["application_importer"])
        self.assertIsNone(contract["html_mount"])
        self.assertIsNone(contract["route"])

    def test_exact_pass_candidate_builds_hash_only_blocked_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "EXACT_V2_RESEARCH_PASS_BOUND_CONSUMER_UNACTIVATED",
        )
        self.assertEqual(
            self.binding["source"]["candidate_hash"],
            self.candidate["correlation_admission_v2_hash"],
        )
        self.assertTrue(self.binding["facts"]["v2_candidate_exactly_verified"])
        self.assertTrue(self.binding["facts"]["v2_candidate_research_pass"])

    def test_exact_cross_universe_block_is_bound_without_v1_evaluation(self) -> None:
        evidence = self.fixture._replace_universe(
            self.fixture._evidence(),
            ["CCC", "DDD"],
            selection_basis="CONSUMER_PREREGISTRATION_BLOCK_FIXTURE",
        )
        candidate = build_portfolio_correlation_admission_v2(**evidence)
        binding = self._binding(candidate=candidate, evidence=evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["v1_admission_status"], "NOT_EVALUATED")
        self.assertEqual(binding["status"], "BLOCKED")
        self.assertEqual(
            binding["binding_state"],
            "EXACT_V2_BLOCK_BOUND_CONSUMER_UNACTIVATED",
        )
        self.assertTrue(binding["facts"]["v2_block_candidate_bound"])
        self.assertEqual(binding["source"]["v1_candidate_hash"], "")

    def test_tampered_registration_returns_unknown(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["facts"]["presentation_consumer_registered"] = True
        tampered.pop("consumer_preregistration_hash")
        tampered = seal_strict_canonical_document(
            tampered,
            "consumer_preregistration_hash",
        )
        result = self._binding(registration=tampered)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "CONSUMER_PREREGISTRATION_NOT_EXACT",
        )

    def test_tampered_candidate_returns_unknown_even_when_resealed(self) -> None:
        promoted = copy.deepcopy(self.candidate)
        promoted["permissions"]["paper_authorized"] = True
        promoted.pop("correlation_admission_v2_hash")
        promoted = seal_strict_canonical_document(
            promoted,
            "correlation_admission_v2_hash",
        )
        result = self._binding(candidate=promoted)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "V2_CANDIDATE_NOT_EXACT")

    def test_source_context_splice_returns_unknown(self) -> None:
        spliced = copy.deepcopy(self.evidence)
        spliced["strategy_id"] = "strategy-spliced"
        result = self._binding(evidence=spliced)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "V2_CANDIDATE_NOT_EXACT")

    def test_non_native_or_cyclic_input_returns_unknown(self) -> None:
        non_native = self._binding(candidate=FlippingMapping(self.candidate))
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        cyclic_result = self._binding(registration=cyclic)
        self.assertEqual(non_native["reason_code"], "INPUT_SNAPSHOT_FAILED")
        self.assertEqual(cyclic_result["reason_code"], "INPUT_SNAPSHOT_FAILED")

    def test_binding_exact_verifier_rejects_resealed_promotion(self) -> None:
        promoted = copy.deepcopy(self.binding)
        promoted["facts"]["consumer_executed"] = True
        promoted.pop("consumer_binding_hash")
        promoted = seal_strict_canonical_document(promoted, "consumer_binding_hash")
        self.assertFalse(self._verify(promoted))

    def test_binding_contains_hashes_not_raw_candidate_or_symbols(self) -> None:
        serialized = repr(self.binding)
        self.assertNotIn("AAA", serialized)
        self.assertNotIn("report_document", self.binding)
        self.assertNotIn("candidate_document", self.binding)
        self.assertFalse(self.binding["facts"]["raw_candidate_embedded"])
        self.assertFalse(self.binding["facts"]["raw_source_documents_embedded"])
        self.assertFalse(self.binding["facts"]["raw_symbol_lists_embedded"])

    def test_binding_authority_and_runtime_facts_remain_locked(self) -> None:
        self.assertFalse(self.binding["authority"]["consumer_execution_allowed"])
        self.assertFalse(self.binding["authority"]["current_admission_allowed"])
        self.assertFalse(self.binding["authority"]["paper_authorized"])
        self.assertFalse(self.binding["authority"]["live_order_allowed"])
        self.assertFalse(self.binding["facts"]["delivery_adapter_registered"])
        self.assertFalse(self.binding["facts"]["presentation_consumer_registered"])
        self.assertFalse(self.binding["facts"]["current_activated"])

    def test_registration_and_binding_have_no_promotional_copy(self) -> None:
        values: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)
            elif isinstance(value, str):
                values.append(value)

        collect(self.registration)
        collect(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_builders_are_deterministic_and_do_not_mutate_inputs(self) -> None:
        before_registration = copy.deepcopy(self.registration)
        before_candidate = copy.deepcopy(self.candidate)
        before_evidence = copy.deepcopy(self.evidence)
        self.assertEqual(self.binding, self._binding())
        self.assertEqual(
            self.registration,
            build_portfolio_correlation_admission_v2_consumer_preregistration_v1(),
        )
        self.assertEqual(self.registration, before_registration)
        self.assertEqual(self.candidate, before_candidate)
        self.assertEqual(self.evidence, before_evidence)


if __name__ == "__main__":
    unittest.main()
