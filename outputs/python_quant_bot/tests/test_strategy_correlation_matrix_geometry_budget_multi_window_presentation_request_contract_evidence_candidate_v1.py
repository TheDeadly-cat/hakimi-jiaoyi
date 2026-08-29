from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
import unittest
from unittest.mock import patch

from tests import (
    test_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 as binding_fixture,
)

from exchange_terminal.application import strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1 as evidence
from exchange_terminal.services import strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_adr0334_source_producer_candidate_v1 as producer
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    build_request_scope_evidence_candidate_v1,
    verify_request_scope_evidence_candidate_v1,
)


def _canonical_hash(value):
    return sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


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


def _request_payload(*, non_psd=False):
    fixture = binding_fixture.GeometryBudgetMultiWindowPresentationBindingV9Tests()
    bundle = fixture._bundle(non_psd=non_psd)
    with fixture._boundaries(bundle):
        source_candidate = (
            producer.build_trusted_adr0334_source_producer_candidate_v1(
                request_scope_evidence_candidate=_scope(),
                presentation_binding_evaluation=bundle[
                    "presentation_evaluation"
                ],
                adapter_v7_document=bundle["adapter"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        )
    resolved = source_candidate.take_request_local_context_once().resolve_once()
    return resolved["request_role_values_in_contract_order"]


def _rehash_evaluation(request_payload):
    evaluation = request_payload[
        "geometry_budget_multi_window_presentation_binding_evaluation"
    ]
    evaluation_without_hash = dict(evaluation)
    evaluation_without_hash.pop("evaluation_hash")
    evaluation_hash = _canonical_hash(evaluation_without_hash)
    evaluation["evaluation_hash"] = evaluation_hash
    request_payload[
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
    ] = evaluation_hash


class GeometryBudgetMultiWindowRequestContractEvidenceV1Tests(unittest.TestCase):
    def test_contract_and_field_order_hashes_are_pinned(self):
        self.assertEqual(
            evidence.REQUEST_EVIDENCE_CONTRACT_HASH,
            "0d0046487ff4fab91d2be6e7dc1e2da0d352560aabc16250009809164341725a",
        )
        self.assertEqual(
            evidence.ADR0334_EVALUATION_FIELD_ORDER_HASH,
            "104f7e26f5ca98f8a3a8c6bd6a25e568dee4dcb3c37c743494664e7c7b68a793",
        )
        self.assertEqual(
            evidence.REQUEST_CONTRACT_PAYLOAD_FIELD_ORDER_HASH,
            "6845f7bfb8bfd07f21dad53d3f2d0580c4303a2920aed0d4462fd2cb27799a7e",
        )

    def test_valid_candidate_exactly_verifies(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        self.assertTrue(
            evidence.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                candidate
            )
        )

    def test_candidate_is_deterministic(self):
        request = _request_payload()
        build = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1
        self.assertEqual(build(request), build(request))

    def test_request_payload_and_contract_hashes_are_derived(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        self.assertEqual(
            candidate["request_payload_hash"],
            _canonical_hash(candidate["request_snapshot"]),
        )
        self.assertEqual(
            candidate["request_contract_hash"],
            _canonical_hash(candidate["request_contract_payload"]),
        )
        self.assertTrue(
            candidate["facts"]["request_contract_hash_derived_not_supplied"]
        )

    def test_derived_contract_hash_can_bind_request_scope(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        scope = _scope(candidate["request_contract_hash"])
        self.assertTrue(verify_request_scope_evidence_candidate_v1(scope))
        self.assertEqual(
            scope["evidence"]["request_contract_hash"],
            candidate["request_contract_hash"],
        )

    def test_pass_and_block_requests_have_distinct_contract_hashes(self):
        build = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1
        passing = build(_request_payload())
        blocked = build(_request_payload(non_psd=True))
        self.assertNotEqual(
            passing["request_contract_hash"],
            blocked["request_contract_hash"],
        )
        self.assertEqual(
            blocked["request_snapshot"][
                "geometry_budget_multi_window_presentation_binding_evaluation"
            ]["status"],
            "BLOCK",
        )

    def test_extra_missing_and_reordered_fields_fail_closed(self):
        valid = _request_payload()
        extra = deepcopy(valid)
        extra["unexpected"] = True
        missing = deepcopy(valid)
        missing.pop(evidence.REQUEST_FIELDS[-1])
        reordered = dict(reversed(tuple(valid.items())))
        for request in (extra, missing, reordered):
            with self.subTest(fields=tuple(request)):
                self.assertIsNone(
                    evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                        request
                    )
                )

    def test_wrong_request_schema_fails_closed(self):
        request = _request_payload()
        request["schema_version"] = "wrong"
        self.assertIsNone(
            evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_expected_evaluation_hash_mismatch_fails_closed(self):
        request = _request_payload()
        request[
            "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
        ] = "0" * 64
        self.assertIsNone(
            evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_evaluation_tamper_without_rehash_fails_closed(self):
        request = _request_payload()
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = "TAMPERED"
        self.assertIsNone(
            evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_rehashed_authority_promotion_still_fails_closed(self):
        request = _request_payload()
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["authority"]["paper_authorized"] = True
        _rehash_evaluation(request)
        self.assertIsNone(
            evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_rehashed_semantic_change_is_integrity_only_not_authority(self):
        request = _request_payload()
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = "CALLER_REHASHED_SEMANTIC_CHANGE"
        _rehash_evaluation(request)
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            request
        )
        self.assertIsNotNone(candidate)
        self.assertFalse(candidate["facts"]["adr0334_semantics_reverified"])
        self.assertFalse(
            candidate["authority"]["adr0334_semantic_authority_granted"]
        )

    def test_non_json_cycle_non_finite_and_oversize_fail_closed(self):
        non_json = _request_payload()
        non_json[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = object()
        cyclic = _request_payload()
        cycle = []
        cycle.append(cycle)
        cyclic[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = cycle
        non_finite = _request_payload()
        non_finite[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = math.nan
        oversized = _request_payload()
        oversized[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = "x" * (evidence.MAXIMUM_REQUEST_BYTES + 1)
        _rehash_evaluation(oversized)
        for request in (non_json, cyclic, non_finite, oversized):
            with self.subTest():
                self.assertIsNone(
                    evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                        request
                    )
                )

    def test_input_mutation_does_not_change_snapshot(self):
        request = _request_payload()
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            request
        )
        original = candidate["adr0334_evaluation_hash"]
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ]["reason_code"] = "MUTATED_AFTER_BUILD"
        self.assertEqual(candidate["adr0334_evaluation_hash"], original)

    def test_candidate_and_nested_field_order_tamper_fail_verification(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        reordered = dict(reversed(tuple(candidate.items())))
        self.assertFalse(
            evidence.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                reordered
            )
        )
        nested = deepcopy(candidate)
        nested["request_contract_payload"] = dict(
            reversed(tuple(nested["request_contract_payload"].items()))
        )
        self.assertFalse(
            evidence.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                nested
            )
        )

    def test_candidate_hash_tamper_fails_verification(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        candidate["candidate_hash"] = "0" * 64
        self.assertFalse(
            evidence.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                candidate
            )
        )

    def test_output_is_neutral_and_not_loggable(self):
        candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
            _request_payload()
        )
        rendered = json.dumps(candidate, sort_keys=True)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["registered"])
        self.assertFalse(candidate["facts"]["request_snapshot_logging_allowed"])
        self.assertFalse(candidate["authority"]["paper_authorized"])
        self.assertFalse(candidate["authority"]["live_authorized"])
        self.assertNotIn("READY", rendered)

    def test_builder_performs_no_file_network_or_database_io(self):
        request = _request_payload()
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
            candidate = evidence.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
                request
            )
        self.assertIsNotNone(candidate)


if __name__ == "__main__":
    unittest.main()
