from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tests import (
    test_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 as binding_fixture,
)

from exchange_terminal.services import strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_adr0334_source_producer_candidate_v1 as producer
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    REQUEST_ROLES,
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    VERIFICATION_CONTEXT_ROLES,
    build_request_scope_evidence_candidate_v1,
    verify_context_consumption_receipt_v1,
)


def _scope_candidate(request_scope_id: str = "1" * 64):
    return build_request_scope_evidence_candidate_v1(
        scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
        request_scope_id=request_scope_id,
        authentication_receipt_hash="2" * 64,
        csrf_receipt_hash="3" * 64,
        origin_receipt_hash="4" * 64,
        request_contract_hash="5" * 64,
        context_generation_id="6" * 64,
    )


def _build_candidate(*, bundle=None, scope=None):
    fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
    if bundle is None:
        bundle = fixture._bundle()
    if scope is None:
        scope = _scope_candidate()
    with fixture._boundaries(bundle):
        candidate = producer.build_trusted_adr0334_source_producer_candidate_v1(
            request_scope_evidence_candidate=scope,
            presentation_binding_evaluation=bundle["presentation_evaluation"],
            adapter_v7_document=bundle["adapter"],
            presentation_binding_verification_context=bundle[
                "presentation_context"
            ],
            adapter_v7_verification_context=bundle["adapter_context"],
        )
    return candidate, bundle


class TrustedAdr0334SourceProducerCandidateV1Tests(unittest.TestCase):
    def test_contract_hash_is_pinned(self):
        self.assertEqual(
            producer.CANDIDATE_CONTRACT_HASH,
            "f6148d309a3343324347019811055f449d7621046afd460e5a79d3b622da9389",
        )

    def test_valid_candidate_is_blocked_unregistered_and_synthetic(self):
        candidate, _ = _build_candidate()
        self.assertIsInstance(
            candidate,
            producer.TrustedAdr0334SourceProducerCandidateV1,
        )
        receipt = candidate.receipt
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertFalse(receipt["registered"])
        self.assertTrue(receipt["synthetic_only"])

    def test_candidate_is_deterministic(self):
        first, _ = _build_candidate()
        second, _ = _build_candidate()
        self.assertEqual(first.receipt, second.receipt)

    def test_receipt_records_exact_verification_without_security_claims(self):
        candidate, _ = _build_candidate()
        receipt = candidate.receipt
        self.assertTrue(receipt["facts"]["adr0334_exact_verifier_passed"])
        self.assertTrue(
            receipt["facts"]["expected_hashes_derived_from_source_documents"]
        )
        self.assertFalse(
            receipt["facts"]["security_receipts_semantically_verified"]
        )
        self.assertFalse(
            receipt["facts"]["source_provenance_cryptographically_authenticated"]
        )
        self.assertFalse(receipt["authority"]["current_admission_allowed"])
        self.assertFalse(receipt["authority"]["paper_authorized"])
        self.assertFalse(receipt["authority"]["live_order_allowed"])

    def test_receipt_excludes_source_documents(self):
        candidate, bundle = _build_candidate()
        receipt_text = json.dumps(candidate.receipt, sort_keys=True)
        self.assertFalse(candidate.receipt["source_documents_embedded"])
        self.assertNotIn(bundle["adapter"]["decision"], receipt_text)
        self.assertNotIn("presentation_binding_evaluation", candidate.receipt)
        self.assertIn("source_documents=REDACTED", repr(candidate))

    def test_production_receipt_exact_rebuild_verifies(self):
        scope = _scope_candidate()
        candidate, _ = _build_candidate(scope=scope)
        receipt = candidate.receipt
        context = candidate.take_request_local_context_once()
        self.assertTrue(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                receipt,
                scope,
                context.receipt,
            )
        )

    def test_receipt_field_order_and_hash_tamper_fail(self):
        scope = _scope_candidate()
        candidate, _ = _build_candidate(scope=scope)
        context = candidate.take_request_local_context_once()
        reordered = dict(reversed(tuple(candidate.receipt.items())))
        self.assertFalse(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                reordered,
                scope,
                context.receipt,
            )
        )
        tampered = candidate.receipt
        tampered["adr0334_evaluation_hash"] = "0" * 64
        self.assertFalse(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                tampered,
                scope,
                context.receipt,
            )
        )

    def test_nested_verification_authority_tamper_fails(self):
        scope = _scope_candidate()
        candidate, _ = _build_candidate(scope=scope)
        context = candidate.take_request_local_context_once()
        tampered = candidate.receipt
        tampered["adr0334_verification_receipt"]["paper_authorized"] = True
        self.assertFalse(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                tampered,
                scope,
                context.receipt,
            )
        )

    def test_receipt_from_another_scope_fails(self):
        candidate, _ = _build_candidate()
        context = candidate.take_request_local_context_once()
        self.assertFalse(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                candidate.receipt,
                _scope_candidate("7" * 64),
                context.receipt,
            )
        )

    def test_tampered_context_creation_receipt_fails(self):
        scope = _scope_candidate()
        candidate, _ = _build_candidate(scope=scope)
        context = candidate.take_request_local_context_once()
        creation_receipt = context.receipt
        creation_receipt["context_hash"] = "0" * 64
        self.assertFalse(
            producer.verify_trusted_adr0334_source_production_receipt_v1(
                candidate.receipt,
                scope,
                creation_receipt,
            )
        )

    def test_context_handoff_is_exactly_once(self):
        candidate, _ = _build_candidate()
        self.assertFalse(candidate.consumed)
        self.assertIsNotNone(candidate.take_request_local_context_once())
        self.assertTrue(candidate.consumed)
        self.assertIsNone(candidate.take_request_local_context_once())

    def test_downstream_context_resolves_exact_roles_once(self):
        candidate, _ = _build_candidate()
        context = candidate.take_request_local_context_once()
        creation_receipt = context.receipt
        resolved = context.resolve_once()
        self.assertEqual(
            tuple(resolved["request_role_values_in_contract_order"]),
            REQUEST_ROLES,
        )
        self.assertEqual(
            tuple(resolved["verification_context_values_in_contract_order"]),
            VERIFICATION_CONTEXT_ROLES,
        )
        self.assertTrue(
            verify_context_consumption_receipt_v1(
                resolved["consumption_receipt"],
                creation_receipt,
                _scope_candidate(),
            )
        )
        self.assertIsNone(context.resolve_once())

    def test_expected_hashes_are_derived_and_cross_bound(self):
        candidate, bundle = _build_candidate()
        resolved = candidate.take_request_local_context_once().resolve_once()
        request_values = resolved["request_role_values_in_contract_order"]
        context_values = resolved[
            "verification_context_values_in_contract_order"
        ]
        evaluation = request_values[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]
        self.assertEqual(
            request_values[
                "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
            ],
            evaluation["evaluation_hash"],
        )
        self.assertEqual(
            context_values["expected_evaluation_hash"],
            evaluation["evaluation_hash"],
        )
        self.assertEqual(
            context_values["expected_presentation_binding_evaluation_hash"],
            bundle["presentation_evaluation"]["evaluation_hash"],
        )
        self.assertEqual(
            context_values["expected_adapter_v7_hash"],
            bundle["adapter"]["adapter_v7_hash"],
        )

    def test_input_mutation_does_not_change_resolved_snapshot(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        original_decision = bundle["adapter"]["decision"]
        candidate, _ = _build_candidate(bundle=bundle)
        bundle["adapter"]["decision"] = "MUTATED_AFTER_BUILD"
        resolved = candidate.take_request_local_context_once().resolve_once()
        self.assertEqual(
            resolved["verification_context_values_in_contract_order"][
                "adapter_v7_document"
            ]["decision"],
            original_decision,
        )

    def test_neutral_block_evaluation_is_preserved_not_promoted(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle(non_psd=True)
        candidate, _ = _build_candidate(bundle=bundle)
        resolved = candidate.take_request_local_context_once().resolve_once()
        evaluation = resolved["request_role_values_in_contract_order"][
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]
        self.assertEqual(evaluation["status"], "BLOCK")
        self.assertFalse(evaluation["authority"]["paper_authorized"])
        self.assertFalse(evaluation["authority"]["live_order_allowed"])

    def test_invalid_scope_rejects_before_adr0334(self):
        invalid_scope = _scope_candidate()
        invalid_scope["unexpected"] = True
        with patch.object(
            producer,
            "evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
        ) as evaluator:
            result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=invalid_scope,
                presentation_binding_evaluation={},
                adapter_v7_document={},
                presentation_binding_verification_context={},
                adapter_v7_verification_context={},
            )
        self.assertIsNone(result)
        evaluator.assert_not_called()

    def test_missing_derived_hash_rejects_before_adr0334(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        presentation = deepcopy(bundle["presentation_evaluation"])
        presentation.pop("evaluation_hash")
        with patch.object(
            producer,
            "evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
        ) as evaluator:
            result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                presentation_binding_evaluation=presentation,
                adapter_v7_document=bundle["adapter"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        self.assertIsNone(result)
        evaluator.assert_not_called()

    def test_non_json_cyclic_and_oversized_inputs_fail_closed(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        non_json = deepcopy(bundle["presentation_context"])
        non_json["probe"] = object()
        cycle = deepcopy(bundle["presentation_context"])
        cycle["probe"] = cycle
        oversized = deepcopy(bundle["presentation_context"])
        oversized["probe"] = "x" * (producer.MAX_SOURCE_INPUT_BYTES + 1)
        for context in (non_json, cycle, oversized):
            with self.subTest(kind=type(context.get("probe")).__name__):
                result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                    request_scope_evidence_candidate=_scope_candidate(),
                    presentation_binding_evaluation=bundle[
                        "presentation_evaluation"
                    ],
                    adapter_v7_document=bundle["adapter"],
                    presentation_binding_verification_context=context,
                    adapter_v7_verification_context=bundle["adapter_context"],
                )
                self.assertIsNone(result)

    def test_adr0334_evaluation_exception_and_non_document_fail_closed(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        for replacement in (RuntimeError("synthetic"), "not-a-document"):
            with self.subTest(replacement=type(replacement).__name__):
                if isinstance(replacement, Exception):
                    patcher = patch.object(
                        producer,
                        "evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
                        side_effect=replacement,
                    )
                else:
                    patcher = patch.object(
                        producer,
                        "evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
                        return_value=replacement,
                    )
                with patcher:
                    result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                        request_scope_evidence_candidate=_scope_candidate(),
                        presentation_binding_evaluation=bundle[
                            "presentation_evaluation"
                        ],
                        adapter_v7_document=bundle["adapter"],
                        presentation_binding_verification_context=bundle[
                            "presentation_context"
                        ],
                        adapter_v7_verification_context=bundle[
                            "adapter_context"
                        ],
                    )
                self.assertIsNone(result)

    def test_adr0334_verifier_block_fails_closed(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        with fixture._boundaries(bundle), patch.object(
            producer,
            "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
            return_value={
                "schema_version": producer.ADR0334_VERIFICATION_SCHEMA_VERSION,
                "status": "BLOCK",
                "evaluation_hash": "0" * 64,
                "current_admission_allowed": False,
                "writer_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        ):
            result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                presentation_binding_evaluation=bundle["presentation_evaluation"],
                adapter_v7_document=bundle["adapter"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        self.assertIsNone(result)

    def test_source_resolver_rejection_fails_closed(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        with fixture._boundaries(bundle), patch.object(
            producer,
            "build_request_local_source_context_candidate_v1",
            return_value=None,
        ):
            result = producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                presentation_binding_evaluation=bundle["presentation_evaluation"],
                adapter_v7_document=bundle["adapter"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        self.assertIsNone(result)

    def test_direct_constructor_bypass_is_rejected(self):
        with self.assertRaises(TypeError):
            producer.TrustedAdr0334SourceProducerCandidateV1(None, {})

    def test_candidate_path_performs_no_file_network_or_database_io(self):
        fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
        bundle = fixture._bundle()
        with fixture._boundaries(bundle), patch(
            "builtins.open",
            side_effect=AssertionError("filesystem access"),
        ), patch(
            "socket.socket",
            side_effect=AssertionError("network access"),
        ), patch(
            "sqlite3.connect",
            side_effect=AssertionError("database access"),
        ):
            candidate = producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                presentation_binding_evaluation=bundle["presentation_evaluation"],
                adapter_v7_document=bundle["adapter"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
            resolved = candidate.take_request_local_context_once().resolve_once()
        self.assertIsNotNone(resolved)


if __name__ == "__main__":
    unittest.main()
