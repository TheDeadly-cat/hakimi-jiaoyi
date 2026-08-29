from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH,
    KEYWORD_SOURCE_COUNT,
    POSITIONAL_SOURCE_COUNT,
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    RequestLocalSourceContextCandidateV1,
    build_request_local_source_context_candidate_v1,
    build_request_scope_evidence_candidate_v1,
    verify_context_creation_receipt_v1,
    verify_context_consumption_receipt_v1,
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


def _positional_sources():
    return [{"position": index, "value": [index]} for index in range(13)]


def _keyword_sources():
    return [{"keyword_position": index, "value": index} for index in range(10)]


def _context():
    return build_request_local_source_context_candidate_v1(
        request_scope_evidence_candidate=_scope_candidate(),
        positional_sources_in_contract_order=_positional_sources(),
        keyword_sources_in_contract_order=_keyword_sources(),
    )


class RequestScopeEvidenceCandidateV1Tests(unittest.TestCase):
    def test_contract_hash_is_pinned(self):
        self.assertEqual(
            CANDIDATE_CONTRACT_HASH,
            "7fd73f90c797621c2df621cf5163bf9c83ba77d49f3262518c6c0a7cb72c72b1",
        )

    def test_valid_scope_candidate_is_blocked_and_unregistered(self):
        candidate = _scope_candidate()
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["registered"])
        self.assertTrue(candidate["synthetic_only"])

    def test_valid_scope_candidate_verifies(self):
        self.assertTrue(verify_request_scope_evidence_candidate_v1(_scope_candidate()))

    def test_scope_candidate_is_deterministic(self):
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
                scope_resolver_preregistration_hash=SCOPE_RESOLVER_PREREGISTRATION_HASH,
                request_scope_id="A" * 64,
                authentication_receipt_hash="2" * 64,
                csrf_receipt_hash="3" * 64,
                origin_receipt_hash="4" * 64,
                request_contract_hash="5" * 64,
                context_generation_id="6" * 64,
            )
        )

    def test_evidence_order_tamper_fails_verification(self):
        candidate = _scope_candidate()
        candidate["evidence"] = dict(reversed(tuple(candidate["evidence"].items())))
        self.assertFalse(verify_request_scope_evidence_candidate_v1(candidate))

    def test_evidence_value_tamper_fails_verification(self):
        candidate = _scope_candidate()
        candidate["evidence"]["request_scope_id"] = "7" * 64
        self.assertFalse(verify_request_scope_evidence_candidate_v1(candidate))

    def test_extra_top_level_field_fails_verification(self):
        candidate = _scope_candidate()
        candidate["unexpected"] = True
        self.assertFalse(verify_request_scope_evidence_candidate_v1(candidate))

    def test_security_semantics_are_not_claimed(self):
        facts = _scope_candidate()["facts"]
        self.assertFalse(facts["security_receipts_semantically_verified"])
        self.assertFalse(facts["authentication_performed"])


class RequestLocalSourceContextCandidateV1Tests(unittest.TestCase):
    def test_valid_context_has_expected_type(self):
        self.assertIsInstance(_context(), RequestLocalSourceContextCandidateV1)

    def test_wrong_positional_count_fails_closed(self):
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                positional_sources_in_contract_order=_positional_sources()[:-1],
                keyword_sources_in_contract_order=_keyword_sources(),
            )
        )

    def test_wrong_keyword_count_fails_closed(self):
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                positional_sources_in_contract_order=_positional_sources(),
                keyword_sources_in_contract_order=_keyword_sources()[:-1],
            )
        )

    def test_string_sources_fail_closed(self):
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                positional_sources_in_contract_order="x" * POSITIONAL_SOURCE_COUNT,
                keyword_sources_in_contract_order=_keyword_sources(),
            )
        )

    def test_non_json_source_fails_closed(self):
        positional = _positional_sources()
        positional[0] = object()
        self.assertIsNone(
            build_request_local_source_context_candidate_v1(
                request_scope_evidence_candidate=_scope_candidate(),
                positional_sources_in_contract_order=positional,
                keyword_sources_in_contract_order=_keyword_sources(),
            )
        )

    def test_creation_receipt_contains_hashes_not_sources(self):
        receipt = _context().receipt
        self.assertFalse(receipt["source_documents_embedded"])
        self.assertEqual(
            len(receipt["positional_source_hashes_in_contract_order"]), 13
        )
        self.assertEqual(
            len(receipt["keyword_source_hashes_in_contract_order"]), 10
        )
        self.assertNotIn("positional_sources_in_contract_order", receipt)
        self.assertNotIn("keyword_sources_in_contract_order", receipt)

    def test_creation_receipt_exact_rebuild_verifies(self):
        context = _context()
        self.assertTrue(
            verify_context_creation_receipt_v1(context.receipt, _scope_candidate())
        )

    def test_creation_receipt_source_hash_tamper_fails(self):
        context = _context()
        receipt = context.receipt
        receipt["positional_source_hashes_in_contract_order"][0] = "0" * 64
        self.assertFalse(
            verify_context_creation_receipt_v1(receipt, _scope_candidate())
        )

    def test_direct_constructor_bypass_is_rejected(self):
        with self.assertRaises(TypeError):
            RequestLocalSourceContextCandidateV1([], [], {})

    def test_repr_redacts_sources(self):
        representation = repr(_context())
        self.assertIn("source_documents=REDACTED", representation)
        self.assertNotIn("keyword_position", representation)

    def test_input_mutation_does_not_change_snapshot(self):
        positional = _positional_sources()
        context = build_request_local_source_context_candidate_v1(
            request_scope_evidence_candidate=_scope_candidate(),
            positional_sources_in_contract_order=positional,
            keyword_sources_in_contract_order=_keyword_sources(),
        )
        positional[0]["value"].append("mutated")
        resolved = context.resolve_once()
        self.assertEqual(
            resolved["positional_sources_in_contract_order"][0]["value"], [0]
        )

    def test_context_resolves_exactly_once(self):
        context = _context()
        self.assertIsNotNone(context.resolve_once())
        self.assertTrue(context.consumed)
        self.assertIsNone(context.resolve_once())

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

    def test_resolution_returns_contract_order_counts(self):
        resolved = _context().resolve_once()
        self.assertEqual(
            len(resolved["positional_sources_in_contract_order"]),
            POSITIONAL_SOURCE_COUNT,
        )
        self.assertEqual(
            len(resolved["keyword_sources_in_contract_order"]),
            KEYWORD_SOURCE_COUNT,
        )


if __name__ == "__main__":
    unittest.main()
