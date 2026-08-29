from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tests import (
    test_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_candidate_v1 as gate_fixture,
)

from exchange_terminal.application import strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_owner_candidate_v1 as lifecycle
from exchange_terminal.services import strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_candidate_v1 as gate


def _owner_inputs(*, no_receipts=False):
    chain = gate_fixture._chain()
    preregistration = gate.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1()
    if no_receipts:
        receipts = {"authentication": None, "csrf": None, "origin": None}
    else:
        receipts = gate_fixture._forged_receipts(chain["scope"])
    evaluation = gate_fixture._evaluate(
        chain,
        preregistration=preregistration,
        receipts=receipts,
    )
    return {
        "security_gate_preregistration_document": preregistration,
        "security_gate_evaluation": evaluation,
        "request_contract_evidence_candidate": chain["request_evidence"],
        "request_scope_evidence_candidate": chain["scope"],
        "source_production_receipt": chain["source_receipt"],
        "request_local_context_creation_receipt": chain["context_receipt"],
        "authentication_receipt_document": receipts["authentication"],
        "csrf_receipt_document": receipts["csrf"],
        "origin_receipt_document": receipts["origin"],
    }


def _owner(inputs=None):
    inputs = _owner_inputs() if inputs is None else inputs
    return lifecycle.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_owner_candidate_v1(
        **inputs
    )


class GeometryBudgetMultiWindowRequestLifecycleOwnerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = _owner_inputs()

    def test_contract_hash_is_pinned(self):
        self.assertEqual(
            lifecycle.LIFECYCLE_OWNER_CONTRACT_HASH,
            "73833a5ada7b94b52bbf7ec86130f033dab0ca582288b946a4d7a67498efd202",
        )

    def test_valid_unknown_gate_builds_blocked_owner(self):
        owner = _owner(self.inputs)
        self.assertIsInstance(owner, lifecycle.RequestLifecycleOwnerCandidateV1)
        self.assertFalse(owner.attempted)
        self.assertFalse(owner.closed)
        self.assertEqual(owner.creation_receipt["status"], "BLOCKED")
        self.assertFalse(
            owner.creation_receipt["facts"]["authenticated_claim_possible"]
        )

    def test_creation_receipt_exactly_verifies(self):
        owner = _owner(self.inputs)
        self.assertTrue(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1(
                owner.creation_receipt,
                **self.inputs,
            )
        )

    def test_direct_constructor_is_rejected(self):
        with self.assertRaises(TypeError):
            lifecycle.RequestLifecycleOwnerCandidateV1({})

    def test_first_claim_closes_with_terminal_rejection(self):
        owner = _owner(self.inputs)
        result = owner.claim_once()
        self.assertTrue(owner.attempted)
        self.assertTrue(owner.closed)
        self.assertEqual(
            result["claim_receipt"]["claim_outcome"],
            "CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE",
        )
        self.assertFalse(result["claim_receipt"]["authenticated_claim_created"])

    def test_claim_receipt_and_result_exactly_verify(self):
        owner = _owner(self.inputs)
        result = owner.claim_once()
        self.assertTrue(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1(
                result["claim_receipt"],
                result["creation_receipt"],
            )
        )
        self.assertTrue(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_result_candidate_v1(
                result,
                **self.inputs,
            )
        )

    def test_sequential_retry_returns_none(self):
        owner = _owner(self.inputs)
        self.assertIsNotNone(owner.claim_once())
        self.assertIsNone(owner.claim_once())

    def test_eight_concurrent_claims_produce_one_result(self):
        owner = _owner(self.inputs)
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: owner.claim_once(), range(8)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertTrue(owner.closed)
        self.assertEqual(owner.claim_receipt["claim_attempt_count"], 1)

    def test_tampered_gate_evaluation_cannot_create_owner(self):
        inputs = deepcopy(self.inputs)
        inputs["security_gate_evaluation"]["facts"][
            "security_semantics_verified"
        ] = True
        self.assertIsNone(_owner(inputs))

    def test_mismatched_scope_cannot_create_owner(self):
        inputs = deepcopy(self.inputs)
        inputs["request_scope_evidence_candidate"]["evidence"][
            "request_contract_hash"
        ] = "0" * 64
        self.assertIsNone(_owner(inputs))

    def test_receipt_document_mutation_cannot_create_owner(self):
        inputs = deepcopy(self.inputs)
        inputs["authentication_receipt_document"]["authenticated"] = False
        self.assertIsNone(_owner(inputs))

    def test_no_receipt_documents_still_builds_rejecting_owner(self):
        inputs = _owner_inputs(no_receipts=True)
        owner = _owner(inputs)
        result = owner.claim_once()
        self.assertEqual(
            result["claim_receipt"]["claim_outcome"],
            "CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE",
        )

    def test_creation_receipt_tamper_and_order_fail_verification(self):
        owner = _owner(self.inputs)
        tampered = owner.creation_receipt
        tampered["maximum_claim_attempt_count"] = 2
        self.assertFalse(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1(
                tampered,
                **self.inputs,
            )
        )
        reordered = dict(reversed(tuple(owner.creation_receipt.items())))
        self.assertFalse(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1(
                reordered,
                **self.inputs,
            )
        )

    def test_claim_receipt_tamper_and_order_fail_verification(self):
        result = _owner(self.inputs).claim_once()
        tampered = deepcopy(result["claim_receipt"])
        tampered["authenticated_claim_created"] = True
        self.assertFalse(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1(
                tampered,
                result["creation_receipt"],
            )
        )
        reordered = dict(reversed(tuple(result["claim_receipt"].items())))
        self.assertFalse(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1(
                reordered,
                result["creation_receipt"],
            )
        )

    def test_result_tamper_fails_verification(self):
        result = _owner(self.inputs).claim_once()
        result["authority"]["paper_authorized"] = True
        self.assertFalse(
            lifecycle.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_result_candidate_v1(
                result,
                **self.inputs,
            )
        )

    def test_receipts_result_and_repr_do_not_echo_private_sentinels(self):
        owner = _owner(self.inputs)
        result = owner.claim_once()
        rendered = json.dumps(result, sort_keys=True)
        for sentinel in (
            "PRIVATE-PRINCIPAL-SENTINEL",
            "PRIVATE-CSRF-SENTINEL",
            "PRIVATE-ORIGIN-SENTINEL",
        ):
            self.assertNotIn(sentinel, rendered)
            self.assertNotIn(sentinel, repr(owner))

    def test_claim_never_touches_context_provider_or_handler(self):
        result = _owner(self.inputs).claim_once()
        receipt = result["claim_receipt"]
        self.assertFalse(receipt["context_consumption_attempted"])
        self.assertFalse(receipt["provider_invocation_attempted"])
        self.assertFalse(receipt["handler_invocation_attempted"])

    def test_durable_and_cross_process_claims_are_not_made(self):
        creation = _owner(self.inputs).creation_receipt
        self.assertFalse(creation["facts"]["durable_idempotency_provided"])
        self.assertFalse(creation["facts"]["cross_process_exclusion_provided"])

    def test_authority_remains_neutral_and_locked(self):
        result = _owner(self.inputs).claim_once()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["registered"])
        for key in (
            "authenticated_request_claimed",
            "lifecycle_activation_authorized",
            "provider_binding_authorized",
            "handler_binding_authorized",
            "current_admission_allowed",
            "paper_authorized",
            "live_authorized",
            "writer_allowed",
            "profitability_claimed",
        ):
            self.assertFalse(result["authority"][key])

    def test_builder_and_claim_perform_no_file_network_or_database_io(self):
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
            owner = _owner(self.inputs)
            result = owner.claim_once()
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
