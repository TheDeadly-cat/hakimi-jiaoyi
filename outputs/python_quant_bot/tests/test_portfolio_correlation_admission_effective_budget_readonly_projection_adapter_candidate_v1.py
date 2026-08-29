from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1 import (
    ADAPTER_CONTRACT_HASH,
    PROJECTION_CALLABLE_IDENTITY_HASH,
    build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.application.ports.portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 import (
    build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    build_request_local_source_context_candidate_v1,
    build_request_scope_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1 import (
    KEYWORD_ROLES,
)
from tests import test_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1 as projection_fixture_module


class ReadonlyProjectionAdapterCandidateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = projection_fixture_module.ReadonlyHttpProjectionCandidateV1Tests(
            methodName="test_known_provider_result_projects_hash_only_presentation"
        )
        fixture.setUp()
        self.request = deepcopy(fixture.request)
        self.binding = deepcopy(fixture.binding)
        self.positional = deepcopy(fixture.positional)
        self.keyword = deepcopy(fixture.keyword)
        self.request_evidence = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            self.request
        )
        self.scope = self._build_scope("1")

    def _build_scope(self, seed: str, request_contract_hash=None):
        return build_request_scope_evidence_candidate_v1(
            scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
            request_scope_id=seed * 64,
            authentication_receipt_hash="2" * 64,
            csrf_receipt_hash="3" * 64,
            origin_receipt_hash="4" * 64,
            request_contract_hash=(
                self.request_evidence["request_contract_hash"]
                if request_contract_hash is None
                else request_contract_hash
            ),
            context_generation_id="6" * 64,
        )

    def _build_context(self, *, positional=None, keyword=None, scope=None):
        positional_values = self.positional if positional is None else positional
        keyword_mapping = self.keyword if keyword is None else keyword
        keyword_values = [keyword_mapping[role] for role in KEYWORD_ROLES]
        return build_request_local_source_context_candidate_v1(
            request_scope_evidence_candidate=self.scope if scope is None else scope,
            positional_sources_in_contract_order=positional_values,
            keyword_sources_in_contract_order=keyword_values,
        )

    def _build_adapter(
        self,
        *,
        context=None,
        scope=None,
        binding=None,
        request_evidence=None,
    ):
        return build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
            self.request_evidence if request_evidence is None else request_evidence,
            provider_binding_document=self.binding if binding is None else binding,
            request_scope_evidence_candidate=self.scope if scope is None else scope,
            request_local_source_context_candidate=(
                self._build_context() if context is None else context
            ),
        )

    def _verify_adapter(
        self,
        document,
        *,
        request_evidence=None,
        binding=None,
        scope=None,
        positional=None,
        keyword=None,
    ):
        return verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
            document,
            self.request_evidence if request_evidence is None else request_evidence,
            provider_binding_document=self.binding if binding is None else binding,
            request_scope_evidence_candidate=self.scope if scope is None else scope,
            internal_provider_positional=(
                self.positional if positional is None else positional
            ),
            internal_provider_keyword=self.keyword if keyword is None else keyword,
        )

    @staticmethod
    def _reseal(document, field):
        result = deepcopy(document)
        result.pop(field, None)
        encoded = json.dumps(
            result,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        result[field] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return result

    def test_contract_hashes_are_pinned(self):
        self.assertEqual(
            ADAPTER_CONTRACT_HASH,
            "c6e04132f9e773dfdf77fdbd4ef3255d102b6c0000918b6b3631f204f485215b",
        )
        self.assertEqual(
            PROJECTION_CALLABLE_IDENTITY_HASH,
            "aeaa931f01a2aa1f67643ff59b5f2927a418bd6576d6586244dc46abab95781f",
        )

    def test_real_known_projection_is_reproduced_exactly(self):
        adapter = self._build_adapter()
        expected = build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
            self.request,
            provider_binding_document=self.binding,
            internal_provider_positional=self.positional,
            internal_provider_keyword=self.keyword,
        )
        self.assertEqual(adapter["projection_response"], expected)
        self.assertEqual(
            adapter["projection_response_hash"],
            "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1",
        )

    def test_real_projection_response_verifier_accepts_adapter_output(self):
        adapter = self._build_adapter()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
                adapter["projection_response"],
                self.request,
                provider_binding_document=self.binding,
                internal_provider_positional=self.positional,
                internal_provider_keyword=self.keyword,
            )
        )

    def test_source_bearing_semantic_verifier_accepts_real_output(self):
        adapter = self._build_adapter()
        self.assertTrue(self._verify_adapter(adapter))

    def test_consistency_verifier_is_explicitly_non_authoritative(self):
        adapter = self._build_adapter()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
                adapter,
                self.request_evidence,
                provider_binding_document=self.binding,
                request_scope_evidence_candidate=self.scope,
            )
        )
        self.assertEqual(
            adapter["evidence_verification_level"],
            "CONSISTENCY_ONLY_WITHOUT_EPHEMERAL_SOURCES",
        )
        self.assertFalse(
            adapter["facts"][
                "consistency_verifier_proves_projection_provenance"
            ]
        )

    def test_context_is_consumed_exactly_once(self):
        context = self._build_context()
        self.assertIsNotNone(self._build_adapter(context=context))
        self.assertTrue(context.consumed)
        self.assertIsNone(self._build_adapter(context=context))

    def test_invalid_binding_fails_before_context_consumption(self):
        context = self._build_context()
        binding = deepcopy(self.binding)
        binding["provider_binding_hash"] = "0" * 64
        self.assertIsNone(self._build_adapter(context=context, binding=binding))
        self.assertFalse(context.consumed)

    def test_wrong_scope_fails_before_context_consumption(self):
        context = self._build_context()
        other_scope = self._build_scope("7")
        self.assertIsNone(
            self._build_adapter(context=context, scope=other_scope)
        )
        self.assertFalse(context.consumed)

    def test_non_context_object_fails_closed(self):
        self.assertIsNone(self._build_adapter(context={}))

    def test_adapter_tamper_fails_verification(self):
        adapter = self._build_adapter()
        adapter["facts"]["real_projection_callable_invoked_once"] = False
        self.assertFalse(self._verify_adapter(adapter))

    def test_projection_response_tamper_fails_verification(self):
        adapter = self._build_adapter()
        adapter["projection_response"]["state"] = "READY"
        self.assertFalse(self._verify_adapter(adapter))

    def test_creation_receipt_tamper_fails_verification(self):
        adapter = self._build_adapter()
        adapter["context_creation_receipt"]["context_hash"] = "0" * 64
        self.assertFalse(self._verify_adapter(adapter))

    def test_consumption_receipt_tamper_fails_verification(self):
        adapter = self._build_adapter()
        adapter["context_consumption_receipt"]["resolution_count"] = 2
        self.assertFalse(self._verify_adapter(adapter))

    def test_request_swap_fails_verification(self):
        adapter = self._build_adapter()
        request_evidence = deepcopy(self.request_evidence)
        request_evidence["request_snapshot"]["projection_id"] = "different"
        self.assertFalse(
            self._verify_adapter(
                adapter,
                request_evidence=request_evidence,
            )
        )

    def test_scope_with_caller_supplied_wrong_request_hash_fails_before_consumption(self):
        wrong_scope = self._build_scope("8", request_contract_hash="5" * 64)
        context = self._build_context(scope=wrong_scope)
        self.assertIsNone(
            self._build_adapter(context=context, scope=wrong_scope)
        )
        self.assertFalse(context.consumed)

    def test_scope_swap_fails_verification(self):
        adapter = self._build_adapter()
        self.assertFalse(
            self._verify_adapter(adapter, scope=self._build_scope("7"))
        )

    def test_source_mismatch_fails_semantic_verification(self):
        adapter = self._build_adapter()
        positional = deepcopy(self.positional)
        positional[0]["schema_version"] = "source-mismatch"
        self.assertFalse(
            self._verify_adapter(adapter, positional=positional)
        )

    def test_fully_resealed_projection_forgery_is_semantically_rejected(self):
        adapter = self._build_adapter()
        forged = deepcopy(adapter)
        forged["projection_response"]["state"] = "FORGED_SELF_CONSISTENT_STATE"
        forged["projection_response"] = self._reseal(
            forged["projection_response"],
            "response_hash",
        )
        forged["projection_response_hash"] = forged["projection_response"][
            "response_hash"
        ]
        forged = self._reseal(forged, "adapter_hash")
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
                forged,
                self.request_evidence,
                provider_binding_document=self.binding,
                request_scope_evidence_candidate=self.scope,
            )
        )
        self.assertFalse(self._verify_adapter(forged))

    def test_keyword_role_swap_cannot_reproduce_known_response(self):
        keyword = deepcopy(self.keyword)
        keyword["strategy_id"], keyword["variant_id"] = (
            keyword["variant_id"],
            keyword["strategy_id"],
        )
        adapter = self._build_adapter(context=self._build_context(keyword=keyword))
        self.assertNotEqual(
            adapter["projection_response_hash"],
            "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1",
        )

    def test_positional_role_swap_cannot_reproduce_known_response(self):
        positional = deepcopy(self.positional)
        positional[0], positional[1] = positional[1], positional[0]
        adapter = self._build_adapter(
            context=self._build_context(positional=positional)
        )
        self.assertNotEqual(
            adapter["projection_response_hash"],
            "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1",
        )

    def test_input_mutation_after_context_creation_isolated(self):
        positional = deepcopy(self.positional)
        context = self._build_context(positional=positional)
        positional[0]["schema_version"] = "mutated"
        adapter = self._build_adapter(context=context)
        self.assertEqual(
            adapter["projection_response_hash"],
            "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1",
        )

    def test_output_contains_no_source_sentinel(self):
        positional = deepcopy(self.positional)
        positional[0] = {**positional[0], "private_sentinel": "DO-NOT-ECHO"}
        adapter = self._build_adapter(
            context=self._build_context(positional=positional)
        )
        self.assertNotIn("DO-NOT-ECHO", json.dumps(adapter, sort_keys=True))

    def test_authority_is_neutral_and_locked(self):
        adapter = self._build_adapter()
        self.assertEqual(adapter["status"], "BLOCKED")
        self.assertFalse(adapter["registered"])
        self.assertTrue(adapter["synthetic_only"])
        for key in (
            "http_registration_authorized",
            "runtime_activation_authorized",
            "paper_authorized",
            "live_authorized",
            "profitability_claimed",
        ):
            self.assertFalse(adapter["authority"][key])

    def test_adapter_requires_ephemeral_sources_for_semantic_verification(self):
        facts = self._build_adapter()["facts"]
        self.assertTrue(facts["source_bearing_semantic_verifier_available"])
        self.assertFalse(facts["consistency_verifier_proves_projection_provenance"])
        self.assertTrue(facts["request_contract_derived_from_exact_snapshot"])
        self.assertTrue(facts["request_contract_hash_matched_scope"])


if __name__ == "__main__":
    unittest.main()
