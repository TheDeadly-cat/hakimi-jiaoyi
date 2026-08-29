from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tests import (
    test_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 as binding_fixture,
)

from exchange_terminal.application import strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1 as request_evidence
from exchange_terminal.services import strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_candidate_v1 as gate
from exchange_terminal.services import strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_adr0334_source_producer_candidate_v1 as producer
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    build_request_scope_evidence_candidate_v1,
)


def _scope(request_contract_hash="5" * 64):
    return build_request_scope_evidence_candidate_v1(
        scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
        request_scope_id="1" * 64,
        authentication_receipt_hash="2" * 64,
        csrf_receipt_hash="3" * 64,
        origin_receipt_hash="4" * 64,
        request_contract_hash=request_contract_hash,
        context_generation_id="6" * 64,
    )


def _build_source(fixture, bundle, scope):
    with fixture._boundaries(bundle):
        return producer.build_trusted_adr0334_source_producer_candidate_v1(
            request_scope_evidence_candidate=scope,
            presentation_binding_evaluation=bundle["presentation_evaluation"],
            adapter_v7_document=bundle["adapter"],
            presentation_binding_verification_context=bundle[
                "presentation_context"
            ],
            adapter_v7_verification_context=bundle["adapter_context"],
        )


def _chain(*, non_psd=False):
    fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
    bundle = fixture._bundle(non_psd=non_psd)
    bootstrap = _build_source(fixture, bundle, _scope())
    request_payload = (
        bootstrap.take_request_local_context_once()
        .resolve_once()["request_role_values_in_contract_order"]
    )
    evidence = request_evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
        request_payload
    )
    scope = _scope(evidence["request_contract_hash"])
    source = _build_source(fixture, bundle, scope)
    source_receipt = source.receipt
    context = source.take_request_local_context_once()
    return {
        "fixture": fixture,
        "bundle": bundle,
        "request_evidence": evidence,
        "scope": scope,
        "source_receipt": source_receipt,
        "context_receipt": context.receipt,
    }


def _forged_receipts(scope):
    evidence = scope["evidence"]
    return {
        "authentication": {
            "authenticated": True,
            "principal": "PRIVATE-PRINCIPAL-SENTINEL",
            "receipt_hash": evidence["authentication_receipt_hash"],
        },
        "csrf": {
            "verified": True,
            "token": "PRIVATE-CSRF-SENTINEL",
            "receipt_hash": evidence["csrf_receipt_hash"],
        },
        "origin": {
            "allowed": True,
            "origin": "PRIVATE-ORIGIN-SENTINEL",
            "receipt_hash": evidence["origin_receipt_hash"],
        },
    }


def _evaluate(chain, *, preregistration=None, receipts=None):
    preregistration = (
        gate.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1()
        if preregistration is None
        else preregistration
    )
    receipts = _forged_receipts(chain["scope"]) if receipts is None else receipts
    return gate.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
        preregistration,
        chain["request_evidence"],
        chain["scope"],
        chain["source_receipt"],
        chain["context_receipt"],
        authentication_receipt_document=receipts.get("authentication"),
        csrf_receipt_document=receipts.get("csrf"),
        origin_receipt_document=receipts.get("origin"),
    )


class GeometryBudgetMultiWindowSecurityReceiptSemanticGateV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chain = _chain()
        cls.preregistration = gate.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1()
        cls.receipts = _forged_receipts(cls.chain["scope"])

    def test_contract_and_preregistration_hashes_are_pinned(self):
        self.assertEqual(
            gate.GATE_CONTRACT_HASH,
            "f1da8347793aee5d57462ab2c46a38cce3dcd6889c78bb975a65a0b0c0a3e645",
        )
        self.assertEqual(
            gate.EXPECTED_PREREGISTRATION_HASH,
            "580e8b14d316c47b80c660bc7ad2236351e5daaa80f1246ee45fd4501c6be372",
        )

    def test_receipt_field_order_hashes_are_pinned(self):
        self.assertEqual(
            gate.AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH,
            "00049f40df5bde5a1afba4805565c538c63f3446c2a7d63a76ad3ba53548280d",
        )
        self.assertEqual(
            gate.CSRF_RECEIPT_FIELD_ORDER_HASH,
            "898a56fa990a2844792422652fe9e02bcff96ce5bc8d69474d1c5b750281895e",
        )
        self.assertEqual(
            gate.ORIGIN_RECEIPT_FIELD_ORDER_HASH,
            "26e641bad6a0adb8bb8ba2f1d075bfdb955b4b2eb61a57cb24932ca9f2477191",
        )

    def test_preregistration_exactly_verifies(self):
        self.assertTrue(
            gate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1(
                self.preregistration
            )
        )

    def test_all_provider_slots_are_unregistered_and_unbound(self):
        self.assertEqual(tuple(self.preregistration["providers"]), gate.PROVIDER_ROLES)
        for provider_state in self.preregistration["providers"].values():
            self.assertFalse(provider_state["registered"])
            self.assertFalse(provider_state["semantic_verifier_bound"])
            self.assertFalse(provider_state["receipt_issuer_trust_bound"])
            self.assertIsNone(provider_state["provider_id"])

    def test_activation_order_is_consumer_first(self):
        order = self.preregistration["activation_order"]
        self.assertLess(
            order.index(
                "VERIFY_RECEIPT_SCHEMA_SEAL_REQUEST_SCOPE_EVALUATION_AND_SOURCE_BINDINGS"
            ),
            order.index("REGISTER_AUTHENTICATED_REQUEST_LIFECYCLE_OWNER"),
        )
        self.assertLess(
            order.index("REGISTER_AUTHENTICATED_REQUEST_LIFECYCLE_OWNER"),
            order.index("BIND_HANDLER_BY_SEPARATE_DECISION"),
        )

    def test_valid_cross_bound_chain_is_still_unknown_and_unauthorized(self):
        evaluation = _evaluate(self.chain)
        self.assertEqual(evaluation["status"], "UNKNOWN")
        self.assertEqual(
            evaluation["gate_state"],
            "SECURITY_SEMANTICS_UNAVAILABLE",
        )
        self.assertEqual(evaluation["permission_state"], "UNAUTHORIZED")
        self.assertTrue(
            evaluation["facts"]["all_nonsecurity_cross_bindings_verified"]
        )

    def test_no_receipt_documents_is_still_unknown(self):
        evaluation = _evaluate(
            self.chain,
            receipts={"authentication": None, "csrf": None, "origin": None},
        )
        self.assertEqual(evaluation["status"], "UNKNOWN")
        self.assertFalse(evaluation["facts"]["security_semantics_verified"])

    def test_forged_success_flags_and_matching_hashes_are_ignored(self):
        evaluation = _evaluate(self.chain)
        self.assertTrue(
            all(evaluation["self_reported_hash_matches_scope"].values())
        )
        self.assertFalse(
            evaluation["facts"]["self_reported_receipt_hash_match_authoritative"]
        )
        self.assertFalse(evaluation["facts"]["security_semantics_verified"])
        self.assertFalse(
            evaluation["facts"]["authenticated_request_authorized"]
        )

    def test_private_receipt_content_is_not_embedded(self):
        rendered = json.dumps(_evaluate(self.chain), sort_keys=True)
        self.assertNotIn("PRIVATE-PRINCIPAL-SENTINEL", rendered)
        self.assertNotIn("PRIVATE-CSRF-SENTINEL", rendered)
        self.assertNotIn("PRIVATE-ORIGIN-SENTINEL", rendered)

    def test_evaluation_exactly_verifies_and_is_deterministic(self):
        evaluation = _evaluate(self.chain)
        self.assertEqual(evaluation, _evaluate(self.chain))
        self.assertTrue(
            gate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
                evaluation,
                self.preregistration,
                self.chain["request_evidence"],
                self.chain["scope"],
                self.chain["source_receipt"],
                self.chain["context_receipt"],
                authentication_receipt_document=self.receipts["authentication"],
                csrf_receipt_document=self.receipts["csrf"],
                origin_receipt_document=self.receipts["origin"],
            )
        )

    def test_scope_request_contract_mismatch_fails_closed(self):
        mismatched_scope = deepcopy(self.chain["scope"])
        mismatched_scope["evidence"]["request_contract_hash"] = "0" * 64
        chain = dict(self.chain)
        chain["scope"] = mismatched_scope
        self.assertIsNone(_evaluate(chain))

    def test_request_and_source_evaluation_hash_mismatch_fails_closed(self):
        alternate = _chain(non_psd=True)
        chain = dict(self.chain)
        chain["source_receipt"] = alternate["source_receipt"]
        chain["context_receipt"] = alternate["context_receipt"]
        self.assertIsNone(_evaluate(chain))

    def test_tampered_context_and_source_receipts_fail_closed(self):
        context_tampered = dict(self.chain)
        context_tampered["context_receipt"] = deepcopy(
            self.chain["context_receipt"]
        )
        context_tampered["context_receipt"]["context_hash"] = "0" * 64
        source_tampered = dict(self.chain)
        source_tampered["source_receipt"] = deepcopy(
            self.chain["source_receipt"]
        )
        source_tampered["source_receipt"]["production_receipt_hash"] = "0" * 64
        self.assertIsNone(_evaluate(context_tampered))
        self.assertIsNone(_evaluate(source_tampered))

    def test_tampered_preregistration_fails_closed(self):
        preregistration = deepcopy(self.preregistration)
        preregistration["providers"]["authentication"]["registered"] = True
        self.assertIsNone(_evaluate(self.chain, preregistration=preregistration))

    def test_non_json_receipt_hash_is_null_and_still_unknown(self):
        evaluation = _evaluate(
            self.chain,
            receipts={"authentication": object(), "csrf": None, "origin": None},
        )
        self.assertIsNone(evaluation["receipt_document_hashes"]["authentication"])
        self.assertEqual(evaluation["status"], "UNKNOWN")

    def test_receipt_mutation_after_evaluation_is_isolated(self):
        receipts = deepcopy(self.receipts)
        evaluation = _evaluate(self.chain, receipts=receipts)
        original_hash = evaluation["receipt_document_hashes"]["authentication"]
        receipts["authentication"]["authenticated"] = False
        self.assertEqual(
            evaluation["receipt_document_hashes"]["authentication"],
            original_hash,
        )

    def test_evaluation_and_nested_order_tamper_fail_verification(self):
        evaluation = _evaluate(self.chain)
        reordered = dict(reversed(tuple(evaluation.items())))
        self.assertFalse(
            gate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
                reordered,
                self.preregistration,
                self.chain["request_evidence"],
                self.chain["scope"],
                self.chain["source_receipt"],
                self.chain["context_receipt"],
                authentication_receipt_document=self.receipts["authentication"],
                csrf_receipt_document=self.receipts["csrf"],
                origin_receipt_document=self.receipts["origin"],
            )
        )
        nested = deepcopy(evaluation)
        nested["scope_receipt_hashes"] = dict(
            reversed(tuple(nested["scope_receipt_hashes"].items()))
        )
        self.assertFalse(
            gate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
                nested,
                self.preregistration,
                self.chain["request_evidence"],
                self.chain["scope"],
                self.chain["source_receipt"],
                self.chain["context_receipt"],
                authentication_receipt_document=self.receipts["authentication"],
                csrf_receipt_document=self.receipts["csrf"],
                origin_receipt_document=self.receipts["origin"],
            )
        )

    def test_evaluation_authority_tamper_fails_verification(self):
        evaluation = _evaluate(self.chain)
        evaluation["authority"]["paper_authorized"] = True
        self.assertFalse(
            gate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
                evaluation,
                self.preregistration,
                self.chain["request_evidence"],
                self.chain["scope"],
                self.chain["source_receipt"],
                self.chain["context_receipt"],
                authentication_receipt_document=self.receipts["authentication"],
                csrf_receipt_document=self.receipts["csrf"],
                origin_receipt_document=self.receipts["origin"],
            )
        )

    def test_semantic_success_path_does_not_exist(self):
        evaluation = _evaluate(self.chain)
        self.assertFalse(
            self.preregistration["facts"]["semantic_success_state_enabled"]
        )
        self.assertFalse(evaluation["facts"]["semantic_success_state_enabled"])
        self.assertFalse(evaluation["authority"]["security_semantics_verified"])

    def test_builder_performs_no_file_network_or_database_io(self):
        with patch(
            "builtins.open",
            side_effect=AssertionError("filesystem access"),
        ), patch(
            "socket.socket",
            side_effect=AssertionError("network access"),
        ), patch(
            "sqlite3.connect",
            side_effect=AssertionError("database access"),
        ):
            evaluation = _evaluate(self.chain)
        self.assertIsNotNone(evaluation)


if __name__ == "__main__":
    unittest.main()
