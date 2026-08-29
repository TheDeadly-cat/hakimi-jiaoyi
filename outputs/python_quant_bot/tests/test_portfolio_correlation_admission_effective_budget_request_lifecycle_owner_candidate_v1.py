from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import unittest

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1 import (
    verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_lifecycle_owner_candidate_v1 import (
    LIFECYCLE_OWNER_CONTRACT_HASH,
    RequestLifecycleOwnerCandidateV1,
    build_portfolio_correlation_admission_effective_budget_request_lifecycle_owner_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_request_lifecycle_creation_receipt_v1,
    verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1,
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


class ExplodingConsumedContext:
    @property
    def consumed(self):
        raise RuntimeError("consumed property must not be observed")


class RequestLifecycleOwnerCandidateV1Tests(unittest.TestCase):
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
        self.scope = self._scope("1", self.request_evidence["request_contract_hash"])

    def _scope(self, seed, request_contract_hash):
        return build_request_scope_evidence_candidate_v1(
            scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
            request_scope_id=seed * 64,
            authentication_receipt_hash="2" * 64,
            csrf_receipt_hash="3" * 64,
            origin_receipt_hash="4" * 64,
            request_contract_hash=request_contract_hash,
            context_generation_id="6" * 64,
        )

    def _owner(self, *, request_evidence=None, scope=None):
        return build_portfolio_correlation_admission_effective_budget_request_lifecycle_owner_candidate_v1(
            request_contract_evidence_candidate=(
                self.request_evidence
                if request_evidence is None
                else request_evidence
            ),
            request_scope_evidence_candidate=self.scope if scope is None else scope,
        )

    def _context(self, *, positional=None, keyword=None, scope=None):
        positional_values = self.positional if positional is None else positional
        keyword_mapping = self.keyword if keyword is None else keyword
        return build_request_local_source_context_candidate_v1(
            request_scope_evidence_candidate=self.scope if scope is None else scope,
            positional_sources_in_contract_order=positional_values,
            keyword_sources_in_contract_order=[
                keyword_mapping[role] for role in KEYWORD_ROLES
            ],
        )

    def _execute(self, *, owner=None, context=None, binding=None):
        owner_value = self._owner() if owner is None else owner
        context_value = self._context() if context is None else context
        result = owner_value.execute_once(
            provider_binding_document=self.binding if binding is None else binding,
            request_local_source_context_candidate=context_value,
        )
        return owner_value, context_value, result

    def test_contract_hash_is_pinned(self):
        self.assertEqual(
            LIFECYCLE_OWNER_CONTRACT_HASH,
            "f9e349c876a243a966429b98645a23e6d41e093ab58102980e760748c16cf42d",
        )

    def test_creation_receipt_exactly_verifies(self):
        owner = self._owner()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_creation_receipt_v1(
                owner.creation_receipt,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
            )
        )

    def test_direct_constructor_is_rejected(self):
        with self.assertRaises(TypeError):
            RequestLifecycleOwnerCandidateV1({}, {}, {})

    def test_valid_execution_reproduces_known_projection(self):
        owner, context, result = self._execute()
        self.assertTrue(owner.closed)
        self.assertTrue(context.consumed)
        self.assertEqual(
            result["adapter_candidate"]["projection_response_hash"],
            "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1",
        )
        self.assertEqual(
            result["execution_receipt"]["execution_outcome"],
            "ADAPTER_ACCEPTED",
        )

    def test_valid_execution_result_exactly_verifies(self):
        owner, context, result = self._execute()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
                result,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
                provider_binding_document=self.binding,
                context_consumed_observed=context.consumed,
            )
        )

    def test_adapter_semantic_provenance_remains_independently_verifiable(self):
        _, _, result = self._execute()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
                result["adapter_candidate"],
                self.request_evidence,
                provider_binding_document=self.binding,
                request_scope_evidence_candidate=self.scope,
                internal_provider_positional=self.positional,
                internal_provider_keyword=self.keyword,
            )
        )

    def test_owner_allows_only_one_attempt(self):
        owner, _, result = self._execute()
        self.assertIsNotNone(result)
        self.assertTrue(owner.attempted)
        self.assertIsNone(
            owner.execute_once(
                provider_binding_document=self.binding,
                request_local_source_context_candidate=self._context(),
            )
        )

    def test_concurrent_calls_claim_exactly_one_attempt(self):
        owner = self._owner()
        contexts = [self._context() for _ in range(8)]

        def execute(source_context):
            return owner.execute_once(
                provider_binding_document=self.binding,
                request_local_source_context_candidate=source_context,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(execute, contexts))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(sum(source.consumed for source in contexts), 1)
        self.assertTrue(owner.closed)

    def test_exploding_consumed_property_is_not_observed(self):
        owner = self._owner()
        result = owner.execute_once(
            provider_binding_document=self.binding,
            request_local_source_context_candidate=ExplodingConsumedContext(),
        )
        self.assertTrue(owner.closed)
        self.assertIsNone(result["adapter_candidate"])
        self.assertFalse(
            result["execution_receipt"]["context_consumed_observed"]
        )

    def test_invalid_binding_closes_without_consuming_context(self):
        binding = deepcopy(self.binding)
        binding["provider_binding_hash"] = "0" * 64
        owner, context, result = self._execute(binding=binding)
        self.assertTrue(owner.closed)
        self.assertFalse(context.consumed)
        self.assertIsNone(result["adapter_candidate"])
        self.assertEqual(
            result["execution_receipt"]["execution_outcome"],
            "ADAPTER_REJECTED",
        )

    def test_invalid_attempt_cannot_retry_with_valid_binding(self):
        binding = deepcopy(self.binding)
        binding["provider_binding_hash"] = "0" * 64
        owner, _, _ = self._execute(binding=binding)
        self.assertIsNone(
            owner.execute_once(
                provider_binding_document=self.binding,
                request_local_source_context_candidate=self._context(),
            )
        )

    def test_rejected_result_exactly_verifies(self):
        binding = deepcopy(self.binding)
        binding["provider_binding_hash"] = "0" * 64
        _, context, result = self._execute(binding=binding)
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
                result,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
                provider_binding_document=binding,
                context_consumed_observed=context.consumed,
            )
        )

    def test_mismatched_scope_cannot_create_owner(self):
        scope = self._scope("7", "5" * 64)
        self.assertIsNone(self._owner(scope=scope))

    def test_tampered_request_evidence_cannot_create_owner(self):
        evidence = deepcopy(self.request_evidence)
        evidence["request_contract_hash"] = "0" * 64
        self.assertIsNone(self._owner(request_evidence=evidence))

    def test_owner_snapshots_request_evidence(self):
        evidence = deepcopy(self.request_evidence)
        owner = self._owner(request_evidence=evidence)
        evidence["request_contract_hash"] = "0" * 64
        _, _, result = self._execute(owner=owner)
        self.assertIsNotNone(result["adapter_candidate"])

    def test_result_tamper_fails_verification(self):
        _, context, result = self._execute()
        result["execution_receipt"]["adapter_attempt_count"] = 2
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
                result,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
                provider_binding_document=self.binding,
                context_consumed_observed=context.consumed,
            )
        )

    def test_adapter_tamper_fails_result_verification(self):
        _, context, result = self._execute()
        result["adapter_candidate"]["status"] = "READY"
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
                result,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
                provider_binding_document=self.binding,
                context_consumed_observed=context.consumed,
            )
        )

    def test_context_observation_mismatch_fails_verification(self):
        _, context, result = self._execute()
        self.assertTrue(context.consumed)
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
                result,
                request_contract_evidence_candidate=self.request_evidence,
                request_scope_evidence_candidate=self.scope,
                provider_binding_document=self.binding,
                context_consumed_observed=False,
            )
        )

    def test_second_owner_cannot_reuse_consumed_context(self):
        context = self._context()
        first_owner, _, first = self._execute(context=context)
        second_owner, _, second = self._execute(
            owner=self._owner(),
            context=context,
        )
        self.assertIsNotNone(first["adapter_candidate"])
        self.assertIsNone(second["adapter_candidate"])
        self.assertTrue(first_owner.closed)
        self.assertTrue(second_owner.closed)

    def test_receipts_and_repr_do_not_echo_source_sentinel(self):
        positional = deepcopy(self.positional)
        positional[0]["private_sentinel"] = "DO-NOT-ECHO-LIFECYCLE"
        owner, _, result = self._execute(context=self._context(positional=positional))
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn("DO-NOT-ECHO-LIFECYCLE", rendered)
        self.assertNotIn("DO-NOT-ECHO-LIFECYCLE", repr(owner))

    def test_security_receipts_remain_semantically_unverified(self):
        owner = self._owner()
        facts = owner.creation_receipt["facts"]
        self.assertTrue(facts["security_receipts_hash_bound"])
        self.assertFalse(facts["security_receipt_semantics_verified"])

    def test_authority_remains_neutral_and_locked(self):
        _, _, result = self._execute()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["registered"])
        for key in (
            "authenticated_request_claimed",
            "http_registration_authorized",
            "runtime_activation_authorized",
            "paper_authorized",
            "live_authorized",
            "profitability_claimed",
        ):
            self.assertFalse(result["authority"][key])


if __name__ == "__main__":
    unittest.main()
