from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
    as batch_identity_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2
    as identity_binding,
)
from exchange_terminal.services.execution_authority import authority_violations
from tests import (
    test_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2
    as identity_fixture_module,
)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(document, hash_field):
    mutated = copy.deepcopy(document)
    mutated.pop(hash_field, None)
    mutated[hash_field] = _digest(mutated)
    return mutated


def proposal(proposal_id, venue_id, symbol):
    return {
        "proposal_id": proposal_id,
        "venue_id": venue_id,
        "symbol": symbol,
    }


class StrategyCorrelationHistoryCoveredBudgetUniverseBatchInstrumentIdentityGateCandidateV2Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        upstream = (
            identity_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseProposalInstrumentIdentityBindingCandidateV2Tests
        )
        upstream.setUpClass()
        cls.projection = upstream.projection
        cls.projection_hash = upstream.projection_hash
        cls.context = upstream.context
        cls.entries = copy.deepcopy(upstream.entries) + [
            {
                "alias_symbol": "B",
                "budget_symbol": "B",
                "canonical_instrument_id": "US:ISSUER-B:COMMON",
                "venue_id": "XNYS",
            },
            {
                "alias_symbol": "B.N",
                "budget_symbol": "B",
                "canonical_instrument_id": "US:ISSUER-B:COMMON",
                "venue_id": "XNYS",
            },
        ]
        cls.registry = identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
            cls.entries
        )
        if cls.registry is None:
            raise AssertionError("expanded identity registry construction failed")
        cls.registry_hash = cls.registry["identity_preregistration_hash"]
        cls.unique_proposals = [
            proposal("p-a", "XNYS", "A"),
            proposal("p-b", "XNYS", "B.N"),
        ]
        cls.duplicate_alias_proposals = [
            proposal("p-a", "XNYS", "A"),
            proposal("p-a-alias", "xnys", "a.n"),
        ]
        cls.cross_venue_duplicate_proposals = [
            proposal("p-a", "XNYS", "A"),
            proposal("p-a-alt", "ARCX", "A-US"),
        ]
        cls.nfkc_duplicate_proposals = [
            proposal("p-a", "XNYS", "A"),
            proposal("p-a-nfkc", "ＸＮＹＳ", "Ａ.Ｎ"),
        ]
        cls.unknown_proposals = [
            proposal("p-a", "XNYS", "A"),
            proposal("p-unknown", "XNYS", "A-N"),
        ]
        cls.excluded_duplicate_proposals = [
            proposal("p-c", "XNYS", "C"),
            proposal("p-c-alias", "XNYS", "C.N"),
        ]
        cls.unique = cls._evaluate(cls.unique_proposals)
        cls.duplicate_alias = cls._evaluate(cls.duplicate_alias_proposals)
        cls.cross_venue_duplicate = cls._evaluate(
            cls.cross_venue_duplicate_proposals
        )
        cls.nfkc_duplicate = cls._evaluate(cls.nfkc_duplicate_proposals)
        cls.unknown = cls._evaluate(cls.unknown_proposals)
        cls.excluded_duplicate = cls._evaluate(cls.excluded_duplicate_proposals)
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _evaluate(
        cls,
        proposals,
        *,
        registry=None,
        registry_hash=None,
    ):
        return batch_identity_gate.evaluate_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
            cls.registry if registry is None else registry,
            cls.projection,
            proposals,
            expected_identity_preregistration_hash=cls.registry_hash
            if registry_hash is None
            else registry_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_unique_identities_compose_exact_batch_v1_cluster_counts(self):
        self.assertEqual(
            self.unique["status"], batch_preflight.PROJECTED_IMMATURE_STATUS
        )
        summary = self.unique["ticket_summary"]
        self.assertEqual(summary["proposal_occurrence_count"], 2)
        self.assertEqual(summary["unique_canonical_instrument_count"], 2)
        self.assertEqual(
            summary["duplicate_canonical_instrument_occurrence_count"], 0
        )
        self.assertEqual(summary["source_unique_projected_symbol_count"], 2)
        self.assertEqual(summary["source_effective_projected_ticket_count"], 2)
        self.assertTrue(
            self.unique["facts"]["source_batch_preflight_exactly_verified"]
        )

    def test_alias_duplicate_is_one_ticket_and_explicitly_blocked(self):
        self.assertEqual(
            self.duplicate_alias["status"], batch_identity_gate.DUPLICATE_STATUS
        )
        summary = self.duplicate_alias["ticket_summary"]
        self.assertEqual(summary["proposal_occurrence_count"], 2)
        self.assertEqual(summary["unique_canonical_instrument_count"], 1)
        self.assertEqual(
            summary["duplicate_canonical_instrument_occurrence_count"], 1
        )
        self.assertEqual(summary["source_unique_projected_symbol_count"], 1)
        self.assertEqual(summary["source_effective_projected_ticket_count"], 1)
        self.assertIn(
            "BATCH_DUPLICATE_CANONICAL_INSTRUMENT",
            self.duplicate_alias["blockers"],
        )

    def test_cross_venue_and_nfkc_aliases_cannot_create_new_tickets(self):
        expected_identity = self.duplicate_alias["evidence"][
            "unique_canonical_instrument_hashes"
        ]
        for evidence in (
            self.cross_venue_duplicate,
            self.nfkc_duplicate,
        ):
            with self.subTest(evidence=evidence):
                self.assertEqual(evidence["status"], batch_identity_gate.DUPLICATE_STATUS)
                self.assertEqual(
                    evidence["evidence"]["unique_canonical_instrument_hashes"],
                    expected_identity,
                )
                self.assertEqual(
                    evidence["ticket_summary"][
                        "unique_canonical_instrument_count"
                    ],
                    1,
                )

    def test_unknown_identity_prevents_batch_v1_derivation(self):
        self.assertEqual(
            self.unknown["status"], batch_identity_gate.UNKNOWN_IDENTITY_STATUS
        )
        self.assertEqual(
            self.unknown["ticket_summary"]["unknown_identity_occurrence_count"],
            1,
        )
        self.assertIsNone(self.unknown["source"]["source_batch_preflight_hash"])
        self.assertFalse(
            self.unknown["facts"]["source_batch_preflight_exactly_verified"]
        )
        self.assertIn(
            "CANONICAL_TICKET_DERIVATION_INCOMPLETE",
            self.unknown["blockers"],
        )

    def test_history_exclusion_precedes_duplicate_identity_status(self):
        self.assertEqual(
            self.excluded_duplicate["status"], batch_preflight.EXCLUDED_STATUS
        )
        self.assertEqual(
            self.excluded_duplicate["ticket_summary"][
                "duplicate_canonical_instrument_occurrence_count"
            ],
            1,
        )
        self.assertIn(
            "BATCH_CONTAINS_HISTORY_COVERAGE_EXCLUDED_SYMBOL",
            self.excluded_duplicate["blockers"],
        )

    def test_registry_identity_outside_projection_inherits_batch_unknown(self):
        entries = copy.deepcopy(self.entries) + [
            {
                "alias_symbol": "Z.N",
                "budget_symbol": "Z",
                "canonical_instrument_id": "US:ISSUER-Z:COMMON",
                "venue_id": "XNYS",
            }
        ]
        registry = identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
            entries
        )
        self.assertIsNotNone(registry)
        evidence = self._evaluate(
            [proposal("p-z", "XNYS", "Z.N")],
            registry=registry,
            registry_hash=registry["identity_preregistration_hash"],
        )
        self.assertEqual(evidence["status"], batch_preflight.UNKNOWN_STATUS)
        self.assertIsNotNone(evidence["source"]["source_batch_preflight_hash"])

    def test_proposal_ids_are_unique_order_bound_and_size_limited(self):
        duplicate_id = [
            proposal("same", "XNYS", "A"),
            proposal("same", "XNYS", "B"),
        ]
        self.assertIsNone(self._evaluate(duplicate_id))
        oversized = [
            proposal(f"p-{index}", "XNYS", "A")
            for index in range(batch_identity_gate.MAX_PROPOSAL_OCCURRENCES + 1)
        ]
        self.assertIsNone(self._evaluate(oversized))

        reordered = list(reversed(self.unique_proposals))
        self.assertFalse(
            batch_identity_gate.verify_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
                self.unique,
                self.registry,
                self.projection,
                reordered,
                expected_batch_identity_gate_hash=self.unique[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_trusted_registry_hash_rejects_replacement(self):
        replacement_entries = copy.deepcopy(self.entries)
        for entry in replacement_entries:
            if entry["budget_symbol"] == "A":
                entry["canonical_instrument_id"] = "US:REPLACEMENT-A:COMMON"
        replacement = identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
            replacement_entries
        )
        self.assertIsNotNone(replacement)
        self.assertIsNone(
            self._evaluate(
                self.unique_proposals,
                registry=replacement,
                registry_hash=self.registry_hash,
            )
        )

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        self.assertTrue(
            batch_identity_gate.verify_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
                self.duplicate_alias,
                self.registry,
                self.projection,
                self.duplicate_alias_proposals,
                expected_batch_identity_gate_hash=self.duplicate_alias[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        promoted = copy.deepcopy(self.duplicate_alias)
        promoted["authority"]["batch_admission_allowed"] = True
        promoted["decision_path"]["permission"] = "AUTHORIZED"
        promoted = _reseal(promoted, "batch_identity_gate_hash")
        self.assertFalse(
            batch_identity_gate.verify_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
                promoted,
                self.registry,
                self.projection,
                self.duplicate_alias_proposals,
                expected_batch_identity_gate_hash=promoted[
                    "batch_identity_gate_hash"
                ],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_public_output_is_redacted_neutral_and_authority_clean(self):
        rendered = json.dumps(self.duplicate_alias, ensure_ascii=False, sort_keys=True)
        for raw_identifier in (
            "p-a-alias",
            "a.n",
            "XNYS",
            "US:ISSUER-A:COMMON",
        ):
            self.assertNotIn(raw_identifier, rendered)
        self.assertNotIn("READY", rendered)
        self.assertEqual(
            self.duplicate_alias["decision_path"]["permission"],
            "NOT_AUTHORIZED",
        )
        self.assertEqual(authority_violations(self.duplicate_alias), [])
        self.assertFalse(self.duplicate_alias["registered"])
        self.assertFalse(
            self.duplicate_alias["facts"]["batch_admission_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
