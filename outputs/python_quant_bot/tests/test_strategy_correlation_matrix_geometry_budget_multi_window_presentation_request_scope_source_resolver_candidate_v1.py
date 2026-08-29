from __future__ import annotations

from copy import deepcopy
import math
import unittest

from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH,
    MAX_CANONICAL_CONTEXT_BYTES,
    REQUEST_ROLES,
    REQUEST_SOURCE_COUNT,
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    VERIFICATION_CONTEXT_ROLES,
    VERIFICATION_CONTEXT_SOURCE_COUNT,
    RequestLocalSourceContextCandidateV1,
    build_request_local_source_context_candidate_v1,
    build_request_scope_evidence_candidate_v1,
    verify_context_consumption_receipt_v1,
    verify_context_creation_receipt_v1,
    verify_request_scope_evidence_candidate_v1,
)


def _scope_candidate():
    return build_request_scope_evidence_candidate_v1(
        scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
        request_scope_id="1" * 64,
        authentication_receipt_hash="2" * 64,
        csrf_receipt_hash="3" * 64,
        origin_receipt_hash="4" * 64,
        request_contract_hash="5" * 64,
        context_generation_id="6" * 64,
    )


def _request_sources():
    return {
        "schema_version": "synthetic-request-v9",
        "geometry_budget_multi_window_presentation_binding_evaluation": {
            "status": "BLOCKED",
            "values": [1],
        },
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash": (
            "a" * 64
        ),
    }


def _context_sources():
    return {
        "presentation_binding_evaluation": {"kind": "synthetic-presentation"},
        "adapter_v7_document": {"kind": "synthetic-adapter"},
        "expected_evaluation_hash": "b" * 64,
        "expected_presentation_binding_evaluation_hash": "c" * 64,
        "expected_adapter_v7_hash": "d" * 64,
        "presentation_binding_verification_context": {
            "kind": "synthetic-presentation-context"
        },
        "adapter_v7_verification_context": {
            "kind": "synthetic-adapter-context"
        },
    }


def _context():
    return build_request_local_source_context_candidate_v1(
        request_scope_evidence_candidate=_scope_candidate(),
        request_role_values_in_contract_order=_request_sources(),
        verification_context_values_in_contract_order=_context_sources(),
    )


class RequestScopeEvidenceCandidateV1Tests(unittest.TestCase):
    def test_contract_hash_is_pinned(self):
        self.assertEqual(
            CANDIDATE_CONTRACT_HASH,
            "dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f",
        )

    def test_predecessor_role_counts_and_order_are_pinned(self):
        self.assertEqual(REQUEST_SOURCE_COUNT, 3)
        self.assertEqual(VERIFICATION_CONTEXT_SOURCE_COUNT, 7)
        self.assertEqual(
            REQUEST_ROLES,
            (
                "schema_version",
                "geometry_budget_multi_window_presentation_binding_evaluation",
                "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash",
            ),
        )
        self.assertEqual(len(VERIFICATION_CONTEXT_ROLES), 7)

    def test_valid_scope_candidate_is_blocked_and_unregistered(self):
        candidate = _scope_candidate()
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["registered"])
        self.assertTrue(candidate["synthetic_only"])

    def test_valid_scope_candidate_verifies_and_is_deterministic(self):
        self.assertTrue(verify_request_scope_evidence_candidate_v1(_scope_candidate()))
        self.assertEqual(_scope_candidate(), _scope_candidate())

    def test_wrong_preregistration_hash_fails_closed(self):
        self.assertIsNone(
            build_request_scope_evidence_candidate_v1(
                scope_resolver_preregistration_hash="0" * 64,
                request_scope_id="1" * 64,
                authentication_receipt_hash="2" * 64,
                csrf_receipt_hash="3" * 64,
                origin_receipt_hash="4" * 64,
                request_contract_hash="5" * 64,
                context_generation_id="6" * 64,
            )
        )

    def test_noncanonical_hash_shape_fails_closed(self):
        self.assertIsNone(
            build_request_scope_evidence_candidate_v1(
                scope_resolver_preregistration_hash=(
                    SCOPE_RESOLVER_PREREGISTRATION_HASH
                ),
                request_scope_id="A" * 64,
                authentication_receipt_hash="2" * 64,
                csrf_receipt_hash="3" * 64,
                origin_receipt_hash="4" * 64,
                request_contract_hash="5" * 64,
                context_generation_id="6" * 64,
            )
        )

    def test_scope_field_order_tamper_fails_verification(self):
        candidate = _scope_candidate()
        candidate["evidence"] = dict(reversed(tuple(candidate["evidence"].items())))
        self.assertFalse(verify_request_scope_evidence_candidate_v1(candidate))

    def test_scope_value_and_extra_field_tamper_fail_verification(self):
        value_tampered = _scope_candidate()
        value_tampered["evidence"]["method"] = "GET"
        self.assertFalse(verify_request_scope_evidence_candidate_v1(value_tampered))
        field_tampered = _scope_candidate()
        field_tampered["unexpected"] = True
        self.assertFalse(verify_request_scope_evidence_candidate_v1(field_tampered))

    def test_security_and_trading_semantics_are_not_claimed(self):
        candidate = _scope_candidate()
        self.assertFalse(candidate["facts"]["security_receipts_semantically_verified"])
        self.assertFalse(candidate["facts"]["authentication_performed"])
        self.assertFalse(candidate["facts"]["profitability_proven"])
        self.assertFalse(candidate["authority"]["paper_authorized"])
        self.assertFalse(candidate["authority"]["live_order_allowed"])


class RequestLocalSourceContextCandidateV1Tests(unittest.TestCase):
    def test_valid_context_has_expected_type(self):
        self.assertIsInstance(_context(), RequestLocalSourceContextCandidateV1)

    def test_request_role_order_is_exact(self):
        reversed_sources = dict(reversed(tuple(_request_sources().items())))
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                request_role_values_in_contract_order=reversed_sources,
                verification_context_values_in_contract_order=_context_sources(),
            )
        )

    def test_missing_or_extra_verification_role_fails_closed(self):
        missing = _context_sources()
        missing.pop("adapter_v7_verification_context")
        extra = _context_sources()
        extra["unexpected"] = True
        for values in (missing, extra):
            with self.subTest(keys=tuple(values)):
                self.assertIsNone(
                    build_request_local_source_context_candidate_v1(
                        request_scope_evidence_candidate=_scope_candidate(),
                        request_role_values_in_contract_order=_request_sources(),
                        verification_context_values_in_contract_order=values,
                    )
                )

    def test_non_mapping_sources_fail_closed(self):
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                request_role_values_in_contract_order="not-a-role-map",
                verification_context_values_in_contract_order=_context_sources(),
            )
        )

    def test_non_json_and_non_finite_sources_fail_closed(self):
        non_json = _request_sources()
        non_json["schema_version"] = object()
        non_finite = _context_sources()
        non_finite["expected_evaluation_hash"] = math.nan
        for request_values, context_values in (
            (non_json, _context_sources()),
            (_request_sources(), non_finite),
        ):
            with self.subTest():
                self.assertIsNone(
                    build_request_local_source_context_candidate_v1(
                        request_scope_evidence_candidate=_scope_candidate(),
                        request_role_values_in_contract_order=request_values,
                        verification_context_values_in_contract_order=context_values,
                    )
                )

    def test_cyclic_source_fails_closed(self):
        request_values = _request_sources()
        cycle = []
        cycle.append(cycle)
        request_values["schema_version"] = cycle
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                request_role_values_in_contract_order=request_values,
                verification_context_values_in_contract_order=_context_sources(),
            )
        )

    def test_context_size_limit_fails_closed(self):
        request_values = _request_sources()
        request_values["schema_version"] = "x" * (MAX_CANONICAL_CONTEXT_BYTES + 1)
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                request_role_values_in_contract_order=request_values,
                verification_context_values_in_contract_order=_context_sources(),
            )
        )

    def test_creation_receipt_contains_hashes_not_sources(self):
        receipt = _context().receipt
        self.assertFalse(receipt["source_documents_embedded"])
        self.assertFalse(receipt["source_role_meaning_reverified"])
        self.assertFalse(receipt["receipt_authenticated"])
        self.assertEqual(
            tuple(receipt["request_source_hashes_by_role"]),
            REQUEST_ROLES,
        )
        self.assertEqual(
            tuple(receipt["verification_context_source_hashes_by_role"]),
            VERIFICATION_CONTEXT_ROLES,
        )
        self.assertNotIn("request_role_values_in_contract_order", receipt)
        self.assertNotIn("verification_context_values_in_contract_order", receipt)

    def test_creation_receipt_exact_rebuild_verifies(self):
        context = _context()
        self.assertTrue(
            verify_context_creation_receipt_v1(context.receipt, _scope_candidate())
        )

    def test_creation_receipt_field_order_and_source_hash_tamper_fail(self):
        context = _context()
        order_tampered = dict(reversed(tuple(context.receipt.items())))
        self.assertFalse(
            verify_context_creation_receipt_v1(order_tampered, _scope_candidate())
        )
        hash_tampered = context.receipt
        first_role = REQUEST_ROLES[0]
        hash_tampered["request_source_hashes_by_role"][first_role] = "0" * 64
        self.assertFalse(
            verify_context_creation_receipt_v1(hash_tampered, _scope_candidate())
        )

    def test_creation_receipt_role_hash_order_tamper_fails(self):
        receipt = _context().receipt
        receipt["verification_context_source_hashes_by_role"] = dict(
            reversed(
                tuple(receipt["verification_context_source_hashes_by_role"].items())
            )
        )
        self.assertFalse(
            verify_context_creation_receipt_v1(receipt, _scope_candidate())
        )

    def test_direct_constructor_bypass_is_rejected(self):
        with self.assertRaises(TypeError):
            RequestLocalSourceContextCandidateV1({}, {}, {}, {})

    def test_repr_redacts_source_documents(self):
        representation = repr(_context())
        self.assertIn("source_documents=REDACTED", representation)
        self.assertNotIn("synthetic-adapter", representation)

    def test_input_mutation_does_not_change_snapshot(self):
        request_values = _request_sources()
        context = build_request_local_source_context_candidate_v1(
            request_scope_evidence_candidate=_scope_candidate(),
            request_role_values_in_contract_order=request_values,
            verification_context_values_in_contract_order=_context_sources(),
        )
        request_values[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["values"].append("mutated")
        resolved = context.resolve_once()
        self.assertEqual(
            resolved["request_role_values_in_contract_order"][
                "geometry_budget_multi_window_presentation_binding_evaluation"
            ]["values"],
            [1],
        )

    def test_context_resolves_exactly_once_and_discards(self):
        context = _context()
        resolved = context.resolve_once()
        self.assertIsNotNone(resolved)
        self.assertTrue(context.consumed)
        self.assertTrue(
            resolved["consumption_receipt"]["discarded_after_resolution"]
        )
        self.assertIsNone(context.resolve_once())

    def test_resolution_field_and_role_order_are_exact(self):
        resolved = _context().resolve_once()
        self.assertEqual(
            tuple(resolved),
            (
                "schema_version",
                "candidate_contract_hash",
                "provider_output_schema_version",
                "provider_output_shape_hash",
                "request_role_hash",
                "verification_context_role_hash",
                "request_scope_id",
                "context_generation_id",
                "request_role_values_in_contract_order",
                "verification_context_values_in_contract_order",
                "consumption_receipt",
            ),
        )
        self.assertEqual(
            tuple(resolved["request_role_values_in_contract_order"]),
            REQUEST_ROLES,
        )
        self.assertEqual(
            tuple(resolved["verification_context_values_in_contract_order"]),
            VERIFICATION_CONTEXT_ROLES,
        )

    def test_consumption_receipt_verifies(self):
        context = _context()
        creation_receipt = context.receipt
        resolved = context.resolve_once()
        self.assertTrue(
            verify_context_consumption_receipt_v1(
                resolved["consumption_receipt"],
                creation_receipt,
                _scope_candidate(),
            )
        )

    def test_consumption_receipt_tamper_fails(self):
        context = _context()
        creation_receipt = context.receipt
        resolved = context.resolve_once()
        tampered = deepcopy(resolved["consumption_receipt"])
        tampered["resolution_count"] = 2
        self.assertFalse(
            verify_context_consumption_receipt_v1(
                tampered,
                creation_receipt,
                _scope_candidate(),
            )
        )

    def test_forged_creation_receipt_cannot_validate_consumption(self):
        context = _context()
        creation_receipt = context.receipt
        resolved = context.resolve_once()
        forged_creation = deepcopy(creation_receipt)
        forged_creation["context_hash"] = "0" * 64
        self.assertFalse(
            verify_context_consumption_receipt_v1(
                resolved["consumption_receipt"],
                forged_creation,
                _scope_candidate(),
            )
        )


if __name__ == "__main__":
    unittest.main()
