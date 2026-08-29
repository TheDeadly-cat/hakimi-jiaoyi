from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    KNOWN_REQUEST_CONTRACT_HASH,
    KNOWN_REQUEST_PAYLOAD_HASH,
    PROJECTION_ID,
    PROJECTION_REQUEST_SCHEMA_VERSION,
    REQUEST_EVIDENCE_CONTRACT_HASH,
    build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)


def _request():
    return {
        "schema_version": PROJECTION_REQUEST_SCHEMA_VERSION,
        "projection_id": PROJECTION_ID,
    }


class RequestContractEvidenceCandidateV1Tests(unittest.TestCase):
    def test_contract_and_known_request_hashes_are_pinned(self):
        self.assertEqual(
            REQUEST_EVIDENCE_CONTRACT_HASH,
            "cae0e79f6ad2ceec2444574858ab9d542ebb4912c1e7d463b8a426ba15dc165a",
        )
        self.assertEqual(
            KNOWN_REQUEST_PAYLOAD_HASH,
            "03d52bc29aa187160a9a1ff0a67a5f58835a0b48d787da399dbe950f4bbe24f9",
        )
        self.assertEqual(
            KNOWN_REQUEST_CONTRACT_HASH,
            "7423b83ea15bc410a10ec6964dc906c60368a2147a19e16ebeffdf6a8175b5b4",
        )

    def test_valid_candidate_exactly_verifies(self):
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            _request()
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                candidate
            )
        )

    def test_candidate_is_deterministic(self):
        build = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1
        self.assertEqual(build(_request()), build(_request()))

    def test_request_contract_hash_is_derived(self):
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            _request()
        )
        self.assertEqual(candidate["request_contract_hash"], KNOWN_REQUEST_CONTRACT_HASH)
        self.assertTrue(candidate["facts"]["request_contract_hash_derived_not_supplied"])

    def test_extra_request_field_fails_closed(self):
        request = _request()
        request["source"] = "forbidden"
        self.assertIsNone(
            build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_missing_request_field_fails_closed(self):
        request = _request()
        request.pop("projection_id")
        self.assertIsNone(
            build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_wrong_schema_fails_closed(self):
        request = _request()
        request["schema_version"] = "wrong"
        self.assertIsNone(
            build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_wrong_projection_id_fails_closed(self):
        request = _request()
        request["projection_id"] = "wrong"
        self.assertIsNone(
            build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                request
            )
        )

    def test_non_json_request_fails_closed(self):
        self.assertIsNone(
            build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                {"schema_version": PROJECTION_REQUEST_SCHEMA_VERSION, "projection_id": object()}
            )
        )

    def test_input_mutation_does_not_change_candidate(self):
        request = _request()
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request
        )
        request["projection_id"] = "mutated"
        self.assertEqual(candidate["request_snapshot"]["projection_id"], PROJECTION_ID)

    def test_snapshot_tamper_fails_verification(self):
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            _request()
        )
        candidate["request_snapshot"]["projection_id"] = "tampered"
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                candidate
            )
        )

    def test_hash_tamper_fails_verification(self):
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            _request()
        )
        candidate["request_contract_hash"] = "0" * 64
        self.assertFalse(
            verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
                candidate
            )
        )

    def test_output_is_neutral_and_contains_no_source_input(self):
        candidate = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            _request()
        )
        rendered = json.dumps(candidate, sort_keys=True)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["registered"])
        self.assertNotIn("READY", rendered)
        self.assertNotIn("profitability_claimed\": true", rendered)


if __name__ == "__main__":
    unittest.main()
