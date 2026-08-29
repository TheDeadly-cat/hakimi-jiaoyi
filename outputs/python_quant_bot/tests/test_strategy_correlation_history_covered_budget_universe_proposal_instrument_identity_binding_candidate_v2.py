from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2
    as identity_binding,
)
from exchange_terminal.services.execution_authority import authority_violations
from tests import (
    test_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1
    as proposal_tests,
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


class StrategyCorrelationHistoryCoveredBudgetUniverseProposalInstrumentIdentityBindingCandidateV2Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        upstream = (
            proposal_tests.StrategyCorrelationHistoryCoveredBudgetUniverseProposalPreflightV1Tests
        )
        upstream.setUpClass()
        cls.projection = upstream.projection
        cls.projection_hash = upstream.projection_hash
        cls.context = upstream.context
        cls.entries = [
            {
                "alias_symbol": "A",
                "budget_symbol": "A",
                "canonical_instrument_id": "US:ISSUER-A:COMMON",
                "venue_id": "XNYS",
            },
            {
                "alias_symbol": "A.N",
                "budget_symbol": "A",
                "canonical_instrument_id": "US:ISSUER-A:COMMON",
                "venue_id": "XNYS",
            },
            {
                "alias_symbol": "A-US",
                "budget_symbol": "A",
                "canonical_instrument_id": "US:ISSUER-A:COMMON",
                "venue_id": "ARCX",
            },
            {
                "alias_symbol": "C",
                "budget_symbol": "C",
                "canonical_instrument_id": "US:ISSUER-C:COMMON",
                "venue_id": "XNYS",
            },
            {
                "alias_symbol": "C.N",
                "budget_symbol": "C",
                "canonical_instrument_id": "US:ISSUER-C:COMMON",
                "venue_id": "XNYS",
            },
        ]
        cls.registry = identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
            cls.entries
        )
        if cls.registry is None:
            raise AssertionError("synthetic identity registry construction failed")
        cls.registry_hash = cls.registry["identity_preregistration_hash"]
        cls.canonical = cls._evaluate("XNYS", "A")
        cls.alias = cls._evaluate("xnys", "a.n")
        cls.nfkc_alias = cls._evaluate("ＸＮＹＳ", "Ａ.Ｎ")
        cls.excluded_alias = cls._evaluate("XNYS", "C.N")
        cls.unknown_alias = cls._evaluate("XNYS", "A-N")
        cls.unknown_venue = cls._evaluate("XNAS", "A")
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _evaluate(cls, venue, symbol, *, registry=None, registry_hash=None):
        return identity_binding.evaluate_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
            cls.registry if registry is None else registry,
            cls.projection,
            venue,
            symbol,
            expected_identity_preregistration_hash=cls.registry_hash
            if registry_hash is None
            else registry_hash,
            expected_projection_preregistration_hash=cls.projection_hash,
            projection_verification_context=cls.context,
        )

    def test_registry_is_exactly_verified_and_collision_free(self):
        self.assertTrue(
            identity_binding.verify_strategy_correlation_instrument_identity_preregistration_v1(
                self.registry,
                expected_identity_preregistration_hash=self.registry_hash,
            )
        )
        self.assertFalse(self.registry["facts"]["collisions_allowed"])
        self.assertTrue(
            self.registry["facts"][
                "canonical_instrument_to_budget_symbol_one_to_one"
            ]
        )
        self.assertEqual(self.registry["facts"]["alias_count"], 5)

        forged_lookup = copy.deepcopy(self.registry)
        forged_lookup["entries"][0]["alias_lookup_key"] = "forged-alias"
        forged_lookup = _reseal(
            forged_lookup,
            "identity_preregistration_hash",
        )
        self.assertFalse(
            identity_binding.verify_strategy_correlation_instrument_identity_preregistration_v1(
                forged_lookup,
                expected_identity_preregistration_hash=forged_lookup[
                    "identity_preregistration_hash"
                ],
            )
        )

    def test_aliases_collapse_to_one_identity_and_one_budget_cluster(self):
        for field in (
            "canonical_instrument_id_sha256",
            "budget_symbol_sha256",
            "source_cluster_id_sha256",
            "source_cluster_members_hash",
        ):
            self.assertEqual(
                self.canonical["proposal"][field],
                self.alias["proposal"][field],
                field,
            )
        self.assertTrue(self.alias["facts"]["canonical_budget_symbol_routed"])
        self.assertTrue(self.alias["facts"]["source_cluster_bound"])
        self.assertEqual(self.alias["status"], self.canonical["status"])
        self.assertEqual(
            self.alias["decision_path"]["permission"], "NOT_AUTHORIZED"
        )

    def test_nfkc_and_casefold_are_cosmetic_only_not_new_tickets(self):
        for field in (
            "canonical_instrument_id_sha256",
            "budget_symbol_sha256",
            "source_cluster_members_hash",
        ):
            self.assertEqual(
                self.nfkc_alias["proposal"][field],
                self.canonical["proposal"][field],
                field,
            )
        self.assertNotEqual(
            self.nfkc_alias["proposal"]["input_symbol_sha256"],
            self.canonical["proposal"]["input_symbol_sha256"],
        )

    def test_excluded_alias_routes_to_existing_history_coverage_block(self):
        self.assertEqual(
            self.excluded_alias["status"], identity_binding.legacy_preflight.EXCLUDED_STATUS
        )
        self.assertTrue(
            self.excluded_alias["facts"]["excluded_universe_member"]
        )
        self.assertIn(
            "PROPOSED_SYMBOL_EXCLUDED_BY_HISTORY_COVERAGE_POLICY",
            self.excluded_alias["blockers"],
        )

    def test_unregistered_alias_and_venue_are_diagnostic_unknown(self):
        for evidence in (self.unknown_alias, self.unknown_venue):
            with self.subTest(evidence=evidence):
                self.assertEqual(evidence["status"], identity_binding.UNKNOWN_STATUS)
                self.assertFalse(evidence["facts"]["alias_preregistered"])
                self.assertIsNone(
                    evidence["proposal"]["canonical_instrument_id_sha256"]
                )
                self.assertIsNone(
                    evidence["proposal"]["source_cluster_members_hash"]
                )
                self.assertEqual(
                    evidence["decision_path"]["permission"], "NOT_AUTHORIZED"
                )
                self.assertIn(
                    "INSTRUMENT_IDENTITY_NOT_PREREGISTERED",
                    evidence["blockers"],
                )

    def test_registry_rejects_alias_and_identity_collisions(self):
        duplicate_alias = copy.deepcopy(self.entries)
        duplicate_alias.append({
            "alias_symbol": "a.n",
            "budget_symbol": "A",
            "canonical_instrument_id": "US:ISSUER-A:COMMON",
            "venue_id": "XNYS",
        })
        self.assertIsNone(
            identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
                duplicate_alias
            )
        )

        split_identity = copy.deepcopy(self.entries)
        split_identity.append({
            "alias_symbol": "B.N",
            "budget_symbol": "B",
            "canonical_instrument_id": "US:ISSUER-A:COMMON",
            "venue_id": "XNYS",
        })
        self.assertIsNone(
            identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
                split_identity
            )
        )

        split_budget = copy.deepcopy(self.entries)
        split_budget.append({
            "alias_symbol": "A2",
            "budget_symbol": "A",
            "canonical_instrument_id": "US:ISSUER-A2:COMMON",
            "venue_id": "XNYS",
        })
        self.assertIsNone(
            identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
                split_budget
            )
        )

    def test_trusted_registry_hash_rejects_validly_rebuilt_replacement(self):
        replacement_entries = copy.deepcopy(self.entries)
        for entry in replacement_entries:
            if entry["budget_symbol"] == "A":
                entry["canonical_instrument_id"] = "US:REPLACEMENT-A:COMMON"
        replacement = identity_binding.build_strategy_correlation_instrument_identity_preregistration_v1(
            replacement_entries
        )
        self.assertIsNotNone(replacement)
        self.assertNotEqual(
            replacement["identity_preregistration_hash"], self.registry_hash
        )
        self.assertFalse(
            identity_binding.verify_strategy_correlation_instrument_identity_preregistration_v1(
                replacement,
                expected_identity_preregistration_hash=self.registry_hash,
            )
        )
        self.assertIsNone(
            self._evaluate(
                "XNYS",
                "A.N",
                registry=replacement,
                registry_hash=self.registry_hash,
            )
        )

    def test_binding_is_exactly_verifiable_and_reseal_cannot_promote(self):
        self.assertTrue(
            identity_binding.verify_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
                self.alias,
                self.registry,
                self.projection,
                "xnys",
                "a.n",
                expected_identity_binding_hash=self.alias["identity_binding_hash"],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        promoted = copy.deepcopy(self.alias)
        promoted["authority"]["proposal_admission_allowed"] = True
        promoted["decision_path"]["permission"] = "AUTHORIZED"
        promoted = _reseal(promoted, "identity_binding_hash")
        self.assertFalse(
            identity_binding.verify_strategy_correlation_history_covered_budget_universe_proposal_instrument_identity_binding_candidate_v2(
                promoted,
                self.registry,
                self.projection,
                "xnys",
                "a.n",
                expected_identity_binding_hash=promoted["identity_binding_hash"],
                expected_identity_preregistration_hash=self.registry_hash,
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_public_binding_redacts_identifiers_and_remains_authority_locked(self):
        rendered = json.dumps(self.alias, ensure_ascii=False, sort_keys=True)
        for raw_identifier in (
            "a.n",
            "XNYS",
            "US:ISSUER-A:COMMON",
        ):
            self.assertNotIn(raw_identifier, rendered)
        self.assertNotIn("READY", rendered)
        self.assertEqual(authority_violations(self.alias), [])
        self.assertFalse(self.alias["registered"])
        self.assertFalse(self.alias["facts"]["proposal_admission_allowed"])
        self.assertTrue(self.alias["authority"]["research_evidence_only"])

    def test_invalid_identity_inputs_fail_closed(self):
        self.assertIsNone(self._evaluate("", "A"))
        self.assertIsNone(self._evaluate("XNYS", "symbol with spaces"))
        self.assertIsNone(self._evaluate("XNYS", "x" * 65))


if __name__ == "__main__":
    unittest.main()
