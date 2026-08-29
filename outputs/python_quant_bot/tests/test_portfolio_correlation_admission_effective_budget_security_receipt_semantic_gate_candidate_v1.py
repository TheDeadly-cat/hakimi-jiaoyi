from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    build_request_scope_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_candidate_v1 import (
    AUTHENTICATION_RECEIPT_FIELDS,
    AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH,
    CSRF_RECEIPT_FIELDS,
    CSRF_RECEIPT_FIELD_ORDER_HASH,
    EXPECTED_PREREGISTRATION_HASH,
    GATE_CONTRACT_HASH,
    ORIGIN_RECEIPT_FIELDS,
    ORIGIN_RECEIPT_FIELD_ORDER_HASH,
    PROVIDER_ROLES,
    build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1,
    build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1,
    verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1,
    verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1,
)


class SecurityReceiptSemanticGateCandidateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        request = {
            "schema_version": "portfolio-correlation-admission-effective-budget-readonly-http-projection-candidate-request-v1",
            "projection_id": "portfolio-correlation-admission-effective-budget-readonly-v1",
        }
        self.request_evidence = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request
        )
        self.scope = build_request_scope_evidence_candidate_v1(
            scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
            request_scope_id="1" * 64,
            authentication_receipt_hash="2" * 64,
            csrf_receipt_hash="3" * 64,
            origin_receipt_hash="4" * 64,
            request_contract_hash=self.request_evidence["request_contract_hash"],
            context_generation_id="6" * 64,
        )
        self.preregistration = build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1()
        self.forged_receipts = {
            "authentication": {
                "authenticated": True,
                "principal": "PRIVATE-PRINCIPAL-SENTINEL",
            },
            "csrf": {
                "verified": True,
                "token": "PRIVATE-CSRF-SENTINEL",
            },
            "origin": {
                "allowed": True,
                "origin": "PRIVATE-ORIGIN-SENTINEL",
            },
        }

    def _evaluate(self, *, preregistration=None, scope=None, receipts=None):
        values = self.forged_receipts if receipts is None else receipts
        return build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
            self.preregistration if preregistration is None else preregistration,
            self.request_evidence,
            self.scope if scope is None else scope,
            authentication_receipt_document=values.get("authentication"),
            csrf_receipt_document=values.get("csrf"),
            origin_receipt_document=values.get("origin"),
        )

    def test_contract_hashes_are_pinned(self):
        self.assertEqual(
            GATE_CONTRACT_HASH,
            "141b844a7e43fc069921aefc99214d4d8cb1ee63f80408f249899d29839bad71",
        )
        self.assertEqual(
            EXPECTED_PREREGISTRATION_HASH,
            "9a0455aba48d9b3361aed84428b101c82352833cb3a32e09960b34afe46ab72f",
        )

    def test_receipt_field_order_hashes_are_pinned(self):
        self.assertEqual(
            AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH,
            "99f62ad29526d6976aed07597e778b5163f60f66549148263cafa3d7b635901b",
        )
        self.assertEqual(
            CSRF_RECEIPT_FIELD_ORDER_HASH,
            "5913900c17d29f5577c260944e9180a7e89429ef2cd569ae2b0da0e8dda78f69",
        )
        self.assertEqual(
            ORIGIN_RECEIPT_FIELD_ORDER_HASH,
            "f60dd627e4568d19703aa8d108460ad1d092791a351a71a9cbcce2c0a5ad3197",
        )

    def test_preregistration_exactly_verifies(self):
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1(
                self.preregistration
            )
        )

    def test_all_provider_slots_are_unregistered(self):
        self.assertEqual(tuple(self.preregistration["providers"]), PROVIDER_ROLES)
        for provider in self.preregistration["providers"].values():
            self.assertFalse(provider["registered"])
            self.assertFalse(provider["semantic_verifier_bound"])
            self.assertIsNone(provider["provider_id"])

    def test_activation_order_is_consumer_first(self):
        order = self.preregistration["activation_order"]
        self.assertLess(
            order.index("VERIFY_RECEIPT_ISSUER_AND_REQUEST_BINDING"),
            order.index("ACTIVATE_INTERNAL_LIFECYCLE_CONSUMER"),
        )
        self.assertLess(
            order.index("ACTIVATE_INTERNAL_LIFECYCLE_CONSUMER"),
            order.index("CONSIDER_HTTP_MOUNT"),
        )

    def test_no_receipts_still_returns_unknown(self):
        evaluation = self._evaluate(
            receipts={"authentication": None, "csrf": None, "origin": None}
        )
        self.assertEqual(evaluation["status"], "UNKNOWN")
        self.assertEqual(
            evaluation["gate_state"], "SECURITY_SEMANTICS_UNAVAILABLE"
        )
        self.assertEqual(evaluation["permission_state"], "UNAUTHORIZED")

    def test_self_reported_success_flags_are_ignored(self):
        evaluation = self._evaluate()
        self.assertFalse(evaluation["facts"]["security_semantics_verified"])
        self.assertFalse(
            evaluation["facts"]["lifecycle_activation_authorized"]
        )
        self.assertTrue(
            evaluation["facts"]["self_reported_authenticated_ignored"]
        )

    def test_forged_receipt_content_is_not_embedded(self):
        rendered = json.dumps(self._evaluate(), sort_keys=True)
        self.assertNotIn("PRIVATE-PRINCIPAL-SENTINEL", rendered)
        self.assertNotIn("PRIVATE-CSRF-SENTINEL", rendered)
        self.assertNotIn("PRIVATE-ORIGIN-SENTINEL", rendered)

    def test_evaluation_exactly_verifies(self):
        evaluation = self._evaluate()
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
                evaluation,
                self.preregistration,
                self.request_evidence,
                self.scope,
                authentication_receipt_document=self.forged_receipts[
                    "authentication"
                ],
                csrf_receipt_document=self.forged_receipts["csrf"],
                origin_receipt_document=self.forged_receipts["origin"],
            )
        )

    def test_evaluation_is_deterministic(self):
        self.assertEqual(self._evaluate(), self._evaluate())

    def test_mismatched_scope_fails_closed(self):
        scope = deepcopy(self.scope)
        scope["evidence"]["request_contract_hash"] = "0" * 64
        self.assertIsNone(self._evaluate(scope=scope))

    def test_tampered_preregistration_fails_closed(self):
        preregistration = deepcopy(self.preregistration)
        preregistration["providers"]["authentication"]["registered"] = True
        self.assertIsNone(self._evaluate(preregistration=preregistration))

    def test_evaluation_tamper_fails_verification(self):
        evaluation = self._evaluate()
        evaluation["facts"]["security_semantics_verified"] = True
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
                evaluation,
                self.preregistration,
                self.request_evidence,
                self.scope,
                authentication_receipt_document=self.forged_receipts[
                    "authentication"
                ],
                csrf_receipt_document=self.forged_receipts["csrf"],
                origin_receipt_document=self.forged_receipts["origin"],
            )
        )

    def test_non_json_receipt_hash_is_null_and_still_unknown(self):
        evaluation = self._evaluate(
            receipts={"authentication": object(), "csrf": None, "origin": None}
        )
        self.assertIsNone(
            evaluation["receipt_document_hashes"]["authentication"]
        )
        self.assertEqual(evaluation["status"], "UNKNOWN")

    def test_receipt_mutation_after_evaluation_is_isolated(self):
        receipts = deepcopy(self.forged_receipts)
        evaluation = self._evaluate(receipts=receipts)
        original_hash = evaluation["receipt_document_hashes"]["authentication"]
        receipts["authentication"]["authenticated"] = False
        self.assertEqual(
            evaluation["receipt_document_hashes"]["authentication"],
            original_hash,
        )

    def test_future_receipt_contracts_share_request_bindings(self):
        for fields in (
            AUTHENTICATION_RECEIPT_FIELDS,
            CSRF_RECEIPT_FIELDS,
            ORIGIN_RECEIPT_FIELDS,
        ):
            self.assertIn("provider_registration_hash", fields)
            self.assertIn("request_scope_id", fields)
            self.assertIn("request_contract_hash", fields)
            self.assertIn("receipt_nonce_hash", fields)

    def test_semantic_success_path_does_not_exist(self):
        self.assertFalse(
            self.preregistration["facts"]["semantic_success_state_enabled"]
        )
        self.assertFalse(
            self._evaluate()["facts"]["semantic_success_state_enabled"]
        )

    def test_authority_remains_neutral_and_locked(self):
        authority = self._evaluate()["authority"]
        for key in (
            "security_semantics_verified",
            "authenticated_request_authorized",
            "lifecycle_activation_authorized",
            "http_registration_authorized",
            "runtime_activation_authorized",
            "paper_authorized",
            "live_authorized",
            "profitability_claimed",
        ):
            self.assertFalse(authority[key])


if __name__ == "__main__":
    unittest.main()
