from __future__ import annotations

import inspect
import re
from collections.abc import Iterator, Mapping
from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock, patch

from exchange_terminal.interfaces.http import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as subject,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as provider_binding,
)
from tests import (
    test_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 as source_consumer_tests,
)


_DEFAULT = object()


class SecondReadFlipMapping(Mapping[str, object]):
    def __init__(self, base: dict[str, object], key: str, forged: object) -> None:
        self._base = base
        self._key = key
        self._forged = forged
        self.reads = 0

    def __iter__(self) -> Iterator[str]:
        return iter(self._base)

    def __len__(self) -> int:
        return len(self._base)

    def __getitem__(self, key: str) -> object:
        if key == self._key:
            self.reads += 1
            if self.reads > 1:
                return self._forged
        return self._base[key]


class ReadonlyHttpProjectionCandidateV1Tests(TestCase):
    def setUp(self) -> None:
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "projection_id": subject.PROJECTION_ID,
        }
        self.binding = (
            provider_binding.build_portfolio_correlation_admission_effective_budget_python_provider_binding_v1()
        )
        case = source_consumer_tests.HashEnvelopeSourceConsumerV1Tests(
            methodName="runTest"
        )
        case.setUp()
        fixture = case.fixture
        evidence = fixture.evidence
        self.positional = [
            case.adapter_registration,
            case.consumer_preregistration,
            fixture.binding,
            fixture.admission,
            fixture.budget,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            fixture.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
        ]
        self.keyword = {
            "strategy_id": evidence["strategy_id"],
            "variant_id": evidence["variant_id"],
            "lane": evidence["lane"],
            **fixture.inputs,
        }

    def _build(
        self,
        *,
        request: object = _DEFAULT,
        binding: object = _DEFAULT,
        positional: object = _DEFAULT,
        keyword: object = _DEFAULT,
    ) -> dict:
        return subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
            self.request if request is _DEFAULT else request,
            provider_binding_document=(
                self.binding if binding is _DEFAULT else binding
            ),
            internal_provider_positional=(
                self.positional if positional is _DEFAULT else positional
            ),
            internal_provider_keyword=(
                self.keyword if keyword is _DEFAULT else keyword
            ),
        )

    def test_known_provider_result_projects_hash_only_presentation(self) -> None:
        response = self._build()
        self.assertEqual(response["state"], "KNOWN")
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertTrue(response["facts"]["provider_result_verified"])
        self.assertTrue(response["facts"]["result_available"])
        payload = response["payload"]
        self.assertEqual(
            payload["provider_result_hash"],
            "4271f49558382127bb0e1e737ca080686c305907e60e0b5514aded14a98e7b96",
        )
        self.assertTrue(payload["presentation"]["facts"]["hash_only_projection"])
        self.assertEqual(
            [tier["tier"] for tier in payload["presentation"]["tiers"]],
            [
                "INPUT_SNAPSHOT",
                "ADMISSION_V2_EXACT",
                "EFFECTIVE_BUDGET_V3_EXACT",
                "CROSS_SOURCE_BINDING",
                "ADMISSION_V2_DECISION",
                "EFFECTIVE_BUDGET_V3_DECISION",
                "PERMISSION",
            ],
        )

    def test_malformed_binding_source_projects_verified_unknown(self) -> None:
        positional = deepcopy(self.positional)
        positional[2] = []
        response = self._build(positional=positional)
        self.assertEqual(response["state"], "UNKNOWN")
        self.assertEqual(response["reason_code"], "SOURCE_PROVIDER_UNKNOWN")
        self.assertTrue(response["facts"]["provider_result_verified"])
        self.assertTrue(response["facts"]["source_unknown"])
        self.assertIsNone(response["payload"])

    def test_drifted_adapter_projects_verified_blocked(self) -> None:
        positional = deepcopy(self.positional)
        positional[0]["facts"]["javascript_adapter_registered"] = False
        response = self._build(positional=positional)
        self.assertEqual(response["state"], "BLOCKED")
        self.assertEqual(response["reason_code"], "SOURCE_PROVIDER_BLOCKED")
        self.assertTrue(response["facts"]["provider_result_verified"])
        self.assertTrue(response["facts"]["source_blocked"])
        self.assertIsNone(response["payload"])

    def test_request_contract_is_exact_and_contains_no_source_input(self) -> None:
        cases = [
            None,
            {},
            {**self.request, "unexpected": True},
            {**self.request, "schema_version": "wrong"},
            {**self.request, "projection_id": "wrong"},
        ]
        for request in cases:
            with self.subTest(request=request):
                with patch.object(
                    subject.provider_binding,
                    "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
                ) as resolver:
                    response = self._build(request=request)
                resolver.assert_not_called()
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertEqual(response["reason_code"], "REQUEST_CONTRACT_INVALID")

    def test_internal_context_shape_is_exact_and_fails_before_invocation(self) -> None:
        cases = [
            None,
            [],
            self.positional[:-1],
            {"not": "a list"},
        ]
        for positional in cases:
            with self.subTest(positional=positional), patch.object(
                subject.provider_binding,
                "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
                return_value=Mock(),
            ) as resolver:
                response = self._build(positional=positional)
                resolver.return_value.assert_not_called()
                self.assertEqual(
                    response["reason_code"], "INTERNAL_PROVIDER_CONTEXT_INVALID"
                )
        keyword = {**self.keyword, "unexpected": True}
        response = self._build(keyword=keyword)
        self.assertEqual(response["reason_code"], "INTERNAL_PROVIDER_CONTEXT_INVALID")

    def test_tampered_provider_binding_fails_before_provider_invocation(self) -> None:
        tampered = deepcopy(self.binding)
        tampered["authority"]["external_request_invocation_allowed"] = True
        with patch.object(subject, "_verify_provider_result") as verifier:
            response = self._build(binding=tampered)
        verifier.assert_not_called()
        self.assertEqual(response["reason_code"], "PROVIDER_BINDING_UNVERIFIED")

    def test_provider_exception_fails_closed_without_payload(self) -> None:
        with patch.object(
            subject.provider_binding,
            "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
            return_value=Mock(side_effect=ValueError("synthetic failure")),
        ):
            response = self._build()
        self.assertEqual(response["reason_code"], "PROVIDER_INVOCATION_ERROR")
        self.assertIsNone(response["payload"])

    def test_provider_verification_false_fails_closed(self) -> None:
        with patch.object(subject, "_verify_provider_result", return_value=False):
            response = self._build()
        self.assertEqual(response["reason_code"], "PROVIDER_RESULT_UNVERIFIED")
        self.assertIsNone(response["payload"])

    def test_forged_provider_authority_is_rejected_after_true_verifier(self) -> None:
        real_provider = provider_binding.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
            self.binding
        )
        forged = real_provider(*self.positional, **self.keyword)
        forged["authority"]["paper_authorized"] = True
        with patch.object(
            subject.provider_binding,
            "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
            return_value=Mock(return_value=forged),
        ), patch.object(subject, "_verify_provider_result", return_value=True):
            response = self._build()
        self.assertEqual(response["reason_code"], "PROVIDER_RESULT_UNVERIFIED")
        self.assertIsNone(response["payload"])

    def test_request_and_internal_context_values_are_not_echoed(self) -> None:
        response = self._build()
        response_strings: list[str] = []

        def collect_strings(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect_strings(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_strings(nested)
            elif isinstance(value, str):
                response_strings.append(value)

        collect_strings(response)
        for raw_value in (
            self.keyword["proposed_symbol"],
            self.keyword["strategy_id"],
            self.keyword["variant_id"],
        ):
            self.assertNotIn(raw_value, response_strings)
        self.assertFalse(response["lineage"]["request_document_embedded"])
        self.assertFalse(response["lineage"]["internal_provider_context_embedded"])
        self.assertFalse(response["lineage"]["source_documents_embedded"])

    def test_transport_is_unregistered_and_side_effect_free(self) -> None:
        transport = self._build()["transport"]
        self.assertFalse(transport["registered"])
        self.assertFalse(transport["externally_callable"])
        self.assertIsNone(transport["method"])
        self.assertIsNone(transport["route"])
        self.assertIsNone(transport["endpoint"])
        self.assertEqual(transport["input_source"], "INTERNAL_PROVIDER_RESULT_ONLY")
        for field in (
            "runtime_reads",
            "runtime_mutations",
            "database_reads",
            "database_writes",
            "cache_reads",
            "cache_writes",
            "network_used",
            "request_body_logging_allowed",
        ):
            self.assertFalse(transport[field], field)

    def test_authority_remains_descriptive_and_fully_locked(self) -> None:
        authority = self._build()["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_response_is_deterministic_and_exactly_verifiable(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
                first,
                self.request,
                provider_binding_document=self.binding,
                internal_provider_positional=self.positional,
                internal_provider_keyword=self.keyword,
            )
        )

    def test_response_transport_or_authority_tamper_is_rejected(self) -> None:
        for mutate in (
            lambda value: value["transport"].update({"registered": True}),
            lambda value: value["authority"].update(
                {"http_projection_binding_allowed": True}
            ),
            lambda value: value.update({"current": True}),
        ):
            with self.subTest(mutate=mutate):
                tampered = deepcopy(self._build())
                mutate(tampered)
                self.assertFalse(
                    subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
                        tampered,
                        self.request,
                        provider_binding_document=self.binding,
                        internal_provider_positional=self.positional,
                        internal_provider_keyword=self.keyword,
                    )
                )

    def test_builder_invokes_resolved_provider_exactly_once(self) -> None:
        provider = Mock(
            wraps=provider_binding.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
                self.binding
            )
        )
        with patch.object(
            subject.provider_binding,
            "resolve_portfolio_correlation_admission_effective_budget_python_provider_v1",
            return_value=provider,
        ):
            response = self._build()
        provider.assert_called_once()
        self.assertEqual(response["state"], "KNOWN")

    def test_single_snapshot_blocks_second_read_request_swap(self) -> None:
        wrapped = SecondReadFlipMapping(
            self.request,
            "projection_id",
            "forged",
        )
        response = self._build(request=wrapped)
        self.assertEqual(response["state"], "KNOWN")
        self.assertEqual(wrapped.reads, 1)

    def test_inputs_are_not_mutated(self) -> None:
        before_request = deepcopy(self.request)
        before_binding = deepcopy(self.binding)
        before_positional = deepcopy(self.positional)
        before_keyword = deepcopy(self.keyword)
        self._build()
        self.assertEqual(self.request, before_request)
        self.assertEqual(self.binding, before_binding)
        self.assertEqual(self.positional, before_positional)
        self.assertEqual(self.keyword, before_keyword)

    def test_cyclic_inputs_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        response = self._build(request=cyclic)
        self.assertEqual(response["reason_code"], "REQUEST_CONTRACT_INVALID")
        response = self._build(positional=[cyclic] * 13)
        self.assertEqual(response["reason_code"], "INTERNAL_PROVIDER_CONTEXT_INVALID")

    def test_public_api_exposes_no_route_runtime_database_cache_or_secret(self) -> None:
        for function in (
            subject.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
            subject.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "route",
                        "endpoint",
                        "runtime",
                        "database",
                        "cache",
                        "private_key",
                        "authentication_token",
                    }
                )
            )

    def test_response_values_have_no_ready_or_profitability_promotion(self) -> None:
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

        collect(self._build())
        self.assertIsNone(
            re.search(r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate", " ".join(values), re.IGNORECASE)
        )
