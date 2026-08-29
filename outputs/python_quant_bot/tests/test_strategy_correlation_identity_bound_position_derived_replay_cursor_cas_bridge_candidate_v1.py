from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_replay_cursor_cas_binding_v1
    as cas_binding,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
    as batch_identity_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3
    as identity_post_merge,
)
from exchange_terminal.application import (
    strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1
    as subject,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)
from exchange_terminal.services.execution_authority import authority_violations
from tests import (
    test_strategy_correlation_cluster_v9_position_derived_snapshot_replay_cursor_cas_binding_v1
    as cas_fixture_module,
)
from tests import (
    test_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2
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


class DigestAliasStr(str):
    def __new__(cls, value, digest_alias):
        instance = super().__new__(cls, value)
        instance.digest_alias = digest_alias
        return instance

    def encode(self, encoding="utf-8", errors="strict"):
        return self.digest_alias.encode(encoding, errors)

    def __reduce__(self):
        return type(self), (str(self), self.digest_alias)


class DictAlias(dict):
    pass


class StrategyCorrelationIdentityBoundPositionDerivedReplayCursorCasBridgeCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        cas_fixture = (
            cas_fixture_module.V9PositionDerivedSnapshotReplayCursorCasBindingV1Tests
        )
        identity_fixture = (
            identity_fixture_module.StrategyCorrelationHistoryCoveredBudgetUniverseBatchInstrumentIdentityGateCandidateV2Tests
        )
        cas_fixture.setUpClass()
        identity_fixture.setUpClass()
        cls.cas_fixture = cas_fixture
        cls.identity_fixture = identity_fixture
        cls.freshness_context = copy.deepcopy(cas_fixture.source_context)
        cls.freshness_result = cas_fixture.source_result
        cls.attestation = cas_fixture.attestation
        cls.base_cursor = cas_fixture.base_cursor
        cls.request_nonce_hash = cas_fixture.request_nonce_hash
        cls.registry = identity_fixture.registry
        cls.registry_hash = identity_fixture.registry_hash
        source_proposal = cls.freshness_context["proposals"][0]
        cls.identity_proposals = [
            {
                "proposal_id": source_proposal.proposal_id,
                "venue_id": "XNYS",
                "symbol": "A.N",
                "requested_gross_bps": source_proposal.requested_gross_bps,
            }
        ]
        stripped = [
            {
                "proposal_id": cls.identity_proposals[0]["proposal_id"],
                "venue_id": cls.identity_proposals[0]["venue_id"],
                "symbol": cls.identity_proposals[0]["symbol"],
            }
        ]
        cls.batch_identity = batch_identity_gate.evaluate_strategy_correlation_history_covered_budget_universe_batch_instrument_identity_gate_candidate_v2(
            cls.registry,
            cls.freshness_context["projection_preregistration"],
            stripped,
            expected_identity_preregistration_hash=cls.registry_hash,
            expected_projection_preregistration_hash=cls.freshness_context[
                "expected_projection_preregistration_hash"
            ],
            projection_verification_context=cls.freshness_context[
                "projection_verification_context"
            ],
        )
        if cls.batch_identity is None:
            raise AssertionError("identity batch did not build on v9 projection")
        cls.identity_result = cls._build_identity_result(cls.identity_proposals)
        cls.identity_context = cls._identity_context(cls.identity_proposals)
        cls.cas_result = cas_fixture._evaluate()
        cls.bridge = cls._evaluate()
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _build_identity_result(cls, proposals):
        result = identity_post_merge.evaluate_strategy_correlation_history_covered_budget_universe_identity_bound_position_derived_post_merge_cluster_exposure_gate_candidate_v3(
            cls.batch_identity,
            cls.registry,
            cls.freshness_context["projection_preregistration"],
            proposals,
            cls.freshness_context["exposure_policy"],
            cls.freshness_context["adapter_result"].position_claim,
            expected_batch_identity_gate_hash=cls.batch_identity[
                "batch_identity_gate_hash"
            ],
            expected_identity_preregistration_hash=cls.registry_hash,
            expected_position_snapshot_claim_hash=cls.freshness_context[
                "adapter_result"
            ].position_claim.claim_hash,
            expected_projection_preregistration_hash=cls.freshness_context[
                "expected_projection_preregistration_hash"
            ],
            projection_verification_context=cls.freshness_context[
                "projection_verification_context"
            ],
        )
        if result is None:
            raise AssertionError("identity-bound post-merge result did not build")
        return result

    @classmethod
    def _identity_context(cls, proposals):
        return {
            "batch_identity_gate_document": cls.batch_identity,
            "identity_preregistration": cls.registry,
            "projection_preregistration": cls.freshness_context[
                "projection_preregistration"
            ],
            "proposals": proposals,
            "exposure_policy": cls.freshness_context["exposure_policy"],
            "position_snapshot_claim": cls.freshness_context[
                "adapter_result"
            ].position_claim,
            "expected_batch_identity_gate_hash": cls.batch_identity[
                "batch_identity_gate_hash"
            ],
            "expected_identity_preregistration_hash": cls.registry_hash,
            "expected_position_snapshot_claim_hash": cls.freshness_context[
                "adapter_result"
            ].position_claim.claim_hash,
            "expected_projection_preregistration_hash": cls.freshness_context[
                "expected_projection_preregistration_hash"
            ],
            "projection_verification_context": cls.freshness_context[
                "projection_verification_context"
            ],
        }

    @classmethod
    def _evaluate(
        cls,
        *,
        identity_result=None,
        identity_context=None,
        freshness_result=None,
        freshness_context=None,
        cas_result=None,
        observed_cursor=None,
    ):
        identity_result = (
            cls.identity_result if identity_result is None else identity_result
        )
        identity_context = (
            cls.identity_context if identity_context is None else identity_context
        )
        freshness_result = (
            cls.freshness_result if freshness_result is None else freshness_result
        )
        freshness_context = (
            cls.freshness_context if freshness_context is None else freshness_context
        )
        cas_result = cls.cas_result if cas_result is None else cas_result
        observed_cursor = (
            cls.base_cursor if observed_cursor is None else observed_cursor
        )
        return subject.evaluate_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
            identity_result,
            copy.deepcopy(identity_context),
            freshness_result,
            copy.deepcopy(freshness_context),
            cas_result,
            cls.attestation,
            cls.base_cursor,
            observed_cursor,
            expected_identity_bound_post_merge_hash=identity_result[
                "identity_bound_post_merge_hash"
            ],
            expected_freshness_binding_hash=freshness_result.binding_hash,
            expected_replay_cursor_cas_binding_hash=cas_result.binding_hash,
            request_nonce_hash=cls.request_nonce_hash,
            expected_observed_cursor_hash=observed_cursor.cursor_hash,
        )

    def test_alias_identity_amount_snapshot_and_cas_are_cross_bound(self):
        self.assertEqual(
            self.bridge["status"], subject.STATUS_UNCOMMITTED_CANDIDATE
        )
        self.assertEqual(
            self.bridge["source"]["position_derived_post_merge_result_hash"],
            self.cas_result.source_position_derived_result_hash,
        )
        self.assertEqual(
            self.bridge["source"]["derived_incumbent_snapshot_hash"],
            self.cas_result.source_derived_incumbent_snapshot_hash,
        )
        self.assertEqual(
            self.bridge["observations"]["requested_total_gross_bps"], 400
        )
        self.assertTrue(
            self.bridge["facts"][
                "proposal_ids_symbols_amounts_bound_across_contracts"
            ]
        )

    def test_projection_is_reverified_on_v9_context_not_fixture_assumed(self):
        self.assertNotEqual(
            self.freshness_context["expected_projection_preregistration_hash"],
            self.identity_fixture.projection_hash,
        )
        self.assertEqual(
            self.bridge["source"]["batch_identity_gate_hash"],
            self.batch_identity["batch_identity_gate_hash"],
        )
        self.assertEqual(
            self.identity_result["source"]["projection_preregistration_hash"],
            self.freshness_context["expected_projection_preregistration_hash"],
        )

    def test_amount_splice_builds_valid_identity_result_but_fails_cross_binding(self):
        mutated_proposals = copy.deepcopy(self.identity_proposals)
        mutated_proposals[0]["requested_gross_bps"] = 401
        mutated_result = self._build_identity_result(mutated_proposals)
        self.assertNotEqual(
            mutated_result["source"]["position_derived_post_merge_result_hash"],
            self.cas_result.source_position_derived_result_hash,
        )
        self.assertIsNone(
            self._evaluate(
                identity_result=mutated_result,
                identity_context=self._identity_context(mutated_proposals),
            )
        )

    def test_non_native_proposal_identity_cannot_alias_digest_or_mapping(self):
        canonical_id = self.freshness_context["proposals"][0].proposal_id
        spoofed_id = DigestAliasStr("other-proposal-9", canonical_id)
        spoofed_proposals = [dict(self.identity_proposals[0])]
        spoofed_proposals[0]["proposal_id"] = spoofed_id
        self.assertNotEqual(str(spoofed_id), canonical_id)
        self.assertEqual(spoofed_id.encode("utf-8"), canonical_id.encode("utf-8"))
        with self.assertRaisesRegex(
            AssertionError,
            "identity-bound post-merge result did not build",
        ):
            self._build_identity_result(spoofed_proposals)
        self.assertIsNone(
            self._evaluate(
                identity_context=self._identity_context(spoofed_proposals),
            )
        )

        mapping_alias = [DictAlias(self.identity_proposals[0])]
        with self.assertRaisesRegex(
            AssertionError,
            "identity-bound post-merge result did not build",
        ):
            self._build_identity_result(mapping_alias)
        self.assertIsNone(
            self._evaluate(
                identity_context=self._identity_context(mapping_alias),
            )
        )

        canonical_alias_context = copy.deepcopy(self.freshness_context)
        canonical_proposal = canonical_alias_context["proposals"][0]
        canonical_alias_context["proposals"] = (
            replace(
                canonical_proposal,
                proposal_id=DigestAliasStr(canonical_id, canonical_id),
            ),
        )
        self.assertIsNone(
            self._evaluate(freshness_context=canonical_alias_context)
        )

    def test_cas_conflict_remains_unknown_and_uncommitted(self):
        extra_hash = "0" * 64
        if extra_hash in self.base_cursor.consumed_attestation_hashes:
            extra_hash = "1" * 64
        observed = freshness_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.base_cursor.high_water_sequence,
            high_water_attestation_hash=(
                self.base_cursor.high_water_attestation_hash
            ),
            consumed_attestation_hashes=tuple(
                sorted(self.base_cursor.consumed_attestation_hashes + (extra_hash,))
            ),
        )
        cas_result = self.cas_fixture._evaluate(observed_cursor=observed)
        result = self._evaluate(cas_result=cas_result, observed_cursor=observed)
        self.assertEqual(result["status"], subject.STATUS_UNKNOWN)
        self.assertFalse(result["observations"]["returned_cursor_changed"])

    def test_returned_cursor_replay_remains_blocked_not_committed(self):
        replay_cas = self.cas_fixture._evaluate(
            observed_cursor=self.cas_result.returned_cursor
        )
        result = self._evaluate(
            cas_result=replay_cas,
            observed_cursor=self.cas_result.returned_cursor,
        )
        self.assertEqual(result["status"], subject.STATUS_BLOCKED)
        self.assertFalse(result["facts"]["atomic_storage_commit_verified"])

    def test_freshness_or_cas_hash_splice_fails_closed(self):
        freshness_splice = replace(
            self.freshness_result,
            source_position_derived_result_hash="0" * 64,
        )
        self.assertIsNone(
            self._evaluate(freshness_result=freshness_splice)
        )
        cas_splice = replace(
            self.cas_result,
            source_derived_incumbent_snapshot_hash="0" * 64,
        )
        self.assertIsNone(self._evaluate(cas_result=cas_splice))

    def test_provider_commit_persistence_and_permissions_remain_closed(self):
        for field in (
            "observed_cursor_provider_registered",
            "observed_cursor_source_truth_verified",
            "consume_once_verified",
            "atomic_storage_commit_verified",
            "durable_commit_verified",
            "linearizable_read_verified",
            "replay_registry_persistence_verified",
            "cursor_write_performed",
            "current_admission_allowed",
        ):
            self.assertFalse(self.bridge["facts"][field], field)
        self.assertEqual(
            self.bridge["decision_path"]["permission"], "NOT_AUTHORIZED"
        )

    def test_exact_verifier_rejects_resealed_authority_promotion(self):
        self.assertTrue(
            subject.verify_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
                self.bridge,
                self.identity_result,
                copy.deepcopy(self.identity_context),
                self.freshness_result,
                copy.deepcopy(self.freshness_context),
                self.cas_result,
                self.attestation,
                self.base_cursor,
                self.base_cursor,
                expected_identity_bound_cas_bridge_hash=self.bridge[
                    "identity_bound_cas_bridge_hash"
                ],
                expected_identity_bound_post_merge_hash=self.identity_result[
                    "identity_bound_post_merge_hash"
                ],
                expected_freshness_binding_hash=self.freshness_result.binding_hash,
                expected_replay_cursor_cas_binding_hash=self.cas_result.binding_hash,
                request_nonce_hash=self.request_nonce_hash,
                expected_observed_cursor_hash=self.base_cursor.cursor_hash,
            )
        )
        promoted = copy.deepcopy(self.bridge)
        promoted["authority"]["atomic_storage_commit_verified"] = True
        promoted["decision_path"]["permission"] = "AUTHORIZED"
        promoted = _reseal(promoted, "identity_bound_cas_bridge_hash")
        self.assertFalse(
            subject.verify_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1(
                promoted,
                self.identity_result,
                copy.deepcopy(self.identity_context),
                self.freshness_result,
                copy.deepcopy(self.freshness_context),
                self.cas_result,
                self.attestation,
                self.base_cursor,
                self.base_cursor,
                expected_identity_bound_cas_bridge_hash=promoted[
                    "identity_bound_cas_bridge_hash"
                ],
                expected_identity_bound_post_merge_hash=self.identity_result[
                    "identity_bound_post_merge_hash"
                ],
                expected_freshness_binding_hash=self.freshness_result.binding_hash,
                expected_replay_cursor_cas_binding_hash=self.cas_result.binding_hash,
                request_nonce_hash=self.request_nonce_hash,
                expected_observed_cursor_hash=self.base_cursor.cursor_hash,
            )
        )

    def test_public_output_is_redacted_neutral_and_authority_clean(self):
        rendered = json.dumps(self.bridge, ensure_ascii=False, sort_keys=True)
        for raw_identifier in (
            "binding-p-1",
            "A.N",
            "XNYS",
            self.base_cursor.stream_id,
        ):
            self.assertNotIn(raw_identifier, rendered)
        self.assertNotIn("READY", rendered)
        self.assertEqual(authority_violations(self.bridge), [])
        self.assertFalse(self.bridge["registered"])


if __name__ == "__main__":
    unittest.main()
