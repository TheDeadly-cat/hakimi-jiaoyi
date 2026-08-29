from __future__ import annotations

import copy
import unittest
from pathlib import Path

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v6 as budget_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v5 as v5_tests


class StrategyCorrelationClusterEffectiveBetBudgetV6Tests(unittest.TestCase):
    def assert_authority_locked(self, authority) -> None:
        self.assertTrue(authority["descriptive_only"])
        self.assertFalse(
            any(
                value
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def setUp(self) -> None:
        self.base = v5_tests.StrategyCorrelationClusterEffectiveBetBudgetV5Tests(
            methodName="test_signed_high_equity_snapshot_passes_local_binding"
        )
        self.base.setUp()
        self.bundle = self.base.high_equity_bundle
        self.observed_at = self.bundle["claim"]["snapshot"]["observed_at_unix_ms"]
        self.policy_kwargs = {
            "provider_preregistration_kwargs": self.base.provider_kwargs,
            "maximum_snapshot_age_ms": 1_000,
            "maximum_future_skew_ms": 10,
        }
        self.policy = budget_v6.build_portfolio_snapshot_admission_policy_v1(
            self.base.provider,
            **self.policy_kwargs,
        )
        self.previous_state, self.previous_state_kwargs = self.build_state(
            revision=11,
            claim_hash=self.base.low_equity_bundle["claim"]["snapshot_claim_hash"],
            sequence=7,
            observed_at=self.base.low_equity_bundle["claim"]["snapshot"][
                "observed_at_unix_ms"
            ],
        )
        self.transition, self.transition_kwargs = self.build_transition(
            self.previous_state,
            self.previous_state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at + 500,
        )

    def build_state(
        self,
        *,
        revision: int,
        claim_hash: str,
        sequence: int,
        observed_at: int,
    ):
        kwargs = {
            "expected_policy_hash": self.policy["policy_hash"],
            "policy_build_kwargs": self.policy_kwargs,
            "state_revision": revision,
            "last_snapshot_claim_hash": claim_hash,
            "last_snapshot_sequence": sequence,
            "last_observed_at_unix_ms": observed_at,
        }
        state = budget_v6.build_portfolio_snapshot_admission_state_v1(
            self.policy,
            self.base.provider,
            **kwargs,
        )
        return state, kwargs

    def build_transition(
        self,
        state,
        state_kwargs,
        bundle,
        *,
        evaluated_at: int,
    ):
        kwargs = {
            "expected_previous_state_hash": state["state_hash"],
            "previous_state_build_kwargs": state_kwargs,
            "expected_snapshot_evidence_hash": bundle["evidence"][
                "snapshot_evidence_hash"
            ],
            "snapshot_evaluation_kwargs": bundle["evaluation_kwargs"],
            "evaluated_at_unix_ms": evaluated_at,
        }
        transition = budget_v6.evaluate_portfolio_snapshot_admission_transition_v1(
            state,
            self.policy,
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
            self.base.provider,
            **kwargs,
        )
        return transition, kwargs

    def evaluate_v6(
        self,
        *,
        transition=None,
        transition_kwargs=None,
        previous_state=None,
        bundle=None,
        **overrides,
    ):
        transition = self.transition if transition is None else transition
        transition_kwargs = (
            self.transition_kwargs
            if transition_kwargs is None
            else transition_kwargs
        )
        previous_state = (
            self.previous_state if previous_state is None else previous_state
        )
        bundle = self.bundle if bundle is None else bundle
        kwargs = dict(self.base.increase_kwargs)
        kwargs.update(
            {
                "expected_transition_hash": transition["transition_hash"],
                "transition_evaluation_kwargs": transition_kwargs,
                "expected_current_state_hash": transition.get("next_state_hash")
                or ("0" * 64),
                "expected_snapshot_evidence_hash": bundle["evidence"][
                    "snapshot_evidence_hash"
                ],
                "snapshot_evaluation_kwargs": bundle["evaluation_kwargs"],
                "evaluated_at_unix_ms": self.observed_at + 500,
            }
        )
        kwargs.update(overrides)
        return budget_v6.evaluate_strategy_correlation_cluster_effective_bet_budget_v6(
            transition,
            previous_state,
            self.policy,
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
            self.base.provider,
            self.base.preregistration,
            self.base.matrix,
            self.base.audit,
            **kwargs,
        )

    def test_v5_reaccepts_same_snapshot_without_continuity_or_freshness(self):
        first = self.base.evaluate_v5(self.bundle)
        replay = self.base.evaluate_v5(self.bundle)
        self.assertEqual("PASS", first["status"])
        self.assertEqual(first, replay)
        self.assertFalse(first["facts"]["snapshot_sequence_continuity_verified"])
        self.assertFalse(first["facts"]["snapshot_freshness_verified"])
        self.assertFalse(first["facts"]["runtime_assets_accessed"])

    def test_policy_is_exact_preregistered_and_authority_locked(self):
        self.assertEqual("PREREGISTERED", self.policy["status"])
        self.assertTrue(
            budget_v6.verify_portfolio_snapshot_admission_policy_v1(
                self.policy,
                self.base.provider,
                expected_policy_hash=self.policy["policy_hash"],
                **self.policy_kwargs,
            )
        )
        self.assertEqual(
            "EXACT_PREVIOUS_PLUS_ONE",
            self.policy["continuity_policy"]["sequence_rule"],
        )
        self.assert_authority_locked(self.policy["authority"])

    def test_previous_state_is_exact_candidate_and_authority_locked(self):
        self.assertEqual("CANDIDATE", self.previous_state["status"])
        self.assertTrue(
            budget_v6.verify_portfolio_snapshot_admission_state_v1(
                self.previous_state,
                self.policy,
                self.base.provider,
                expected_state_hash=self.previous_state["state_hash"],
                **self.previous_state_kwargs,
            )
        )
        self.assertEqual(7, self.previous_state["state"]["last_snapshot_sequence"])
        self.assert_authority_locked(self.previous_state["authority"])

    def test_transition_advances_exact_sequence_and_emits_next_state(self):
        self.assertEqual("PASS", self.transition["status"])
        self.assertEqual(8, self.transition["next_state_candidate"]["state"]["last_snapshot_sequence"])
        self.assertEqual(12, self.transition["next_state_candidate"]["state"]["state_revision"])
        self.assertTrue(
            self.transition["facts"][
                "snapshot_sequence_transition_arithmetic_verified"
            ]
        )
        self.assertFalse(
            self.transition["facts"]["snapshot_sequence_continuity_verified"]
        )
        self.assert_authority_locked(self.transition["authority"])

    def test_v6_binds_current_head_snapshot_and_v5_budget(self):
        result = self.evaluate_v6()
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertTrue(result["facts"]["expected_current_head_matches"])
        self.assertTrue(
            result["facts"]["snapshot_freshness_window_arithmetic_verified"]
        )
        self.assertFalse(result["facts"]["snapshot_freshness_verified"])
        self.assertFalse(result["facts"]["caller_equity_input_accepted"])
        self.assertFalse(result["facts"]["caller_positions_input_accepted"])
        self.assertTrue(
            result["facts"]["predecessor_admission_authority_preserved_blocked"]
        )
        self.assert_authority_locked(result["authority"])

    def test_advanced_head_rejects_old_transition_replay(self):
        second_bundle = self.base.build_snapshot_bundle(
            equity=10_000,
            positions=self.base.positions,
            sequence=9,
            label="advanced-head",
        )
        current_state = self.transition["next_state_candidate"]
        current_state_kwargs = {
            "expected_policy_hash": self.policy["policy_hash"],
            "policy_build_kwargs": self.policy_kwargs,
            "state_revision": 12,
            "last_snapshot_claim_hash": self.bundle["claim"]["snapshot_claim_hash"],
            "last_snapshot_sequence": 8,
            "last_observed_at_unix_ms": self.observed_at,
        }
        second_observed_at = second_bundle["claim"]["snapshot"]["observed_at_unix_ms"]
        second_transition, _ = self.build_transition(
            current_state,
            current_state_kwargs,
            second_bundle,
            evaluated_at=second_observed_at + 10,
        )
        result = self.evaluate_v6(
            expected_current_state_hash=second_transition["next_state_hash"]
        )
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("EXPECTED_CURRENT_HEAD_MATCHES", result["blockers"])
        self.assertFalse(result["facts"]["expected_current_head_matches"])

    def test_repeated_read_of_current_head_is_deterministic_within_window(self):
        first = self.evaluate_v6()
        second = self.evaluate_v6()
        self.assertEqual("PASS", first["status"])
        self.assertEqual(first, second)

    def test_stale_snapshot_blocks_transition(self):
        transition, _ = self.build_transition(
            self.previous_state,
            self.previous_state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at + 1_001,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_NOT_TOO_OLD", transition["blockers"])
        self.assertIsNone(transition["next_state_hash"])

    def test_snapshot_that_ages_after_transition_blocks_v6(self):
        result = self.evaluate_v6(evaluated_at_unix_ms=self.observed_at + 1_001)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("CURRENT_SNAPSHOT_NOT_TOO_OLD", result["blockers"])

    def test_snapshot_age_boundary_passes(self):
        result = self.evaluate_v6(evaluated_at_unix_ms=self.observed_at + 1_000)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1_000, result["snapshot_summary"]["clock_delta_ms"])

    def test_future_skew_boundary_passes_with_monotonic_evaluation_time(self):
        transition, transition_kwargs = self.build_transition(
            self.previous_state,
            self.previous_state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at - 10,
        )
        result = self.evaluate_v6(
            transition=transition,
            transition_kwargs=transition_kwargs,
            evaluated_at_unix_ms=self.observed_at - 10,
        )
        self.assertEqual("PASS", transition["status"])
        self.assertEqual("PASS", result["status"])

    def test_future_skew_beyond_boundary_blocks_transition(self):
        transition, _ = self.build_transition(
            self.previous_state,
            self.previous_state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at - 11,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_NOT_TOO_FAR_FUTURE", transition["blockers"])

    def test_skipped_sequence_blocks_transition(self):
        state, state_kwargs = self.build_state(
            revision=11,
            claim_hash=self.base.low_equity_bundle["claim"]["snapshot_claim_hash"],
            sequence=6,
            observed_at=self.observed_at - 2,
        )
        transition, _ = self.build_transition(
            state,
            state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_SEQUENCE_INCREMENT_EXACT", transition["blockers"])

    def test_duplicate_sequence_blocks_transition(self):
        state, state_kwargs = self.build_state(
            revision=11,
            claim_hash=self.base.low_equity_bundle["claim"]["snapshot_claim_hash"],
            sequence=8,
            observed_at=self.observed_at - 1,
        )
        transition, _ = self.build_transition(
            state,
            state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_SEQUENCE_INCREMENT_EXACT", transition["blockers"])

    def test_nonmonotonic_observed_time_blocks_transition(self):
        state, state_kwargs = self.build_state(
            revision=11,
            claim_hash=self.base.low_equity_bundle["claim"]["snapshot_claim_hash"],
            sequence=7,
            observed_at=self.observed_at,
        )
        transition, _ = self.build_transition(
            state,
            state_kwargs,
            self.bundle,
            evaluated_at=self.observed_at,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_OBSERVED_TIME_MONOTONIC", transition["blockers"])

    def test_consumer_clock_rollback_before_transition_blocks_v6(self):
        result = self.evaluate_v6(evaluated_at_unix_ms=self.observed_at + 499)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("EVALUATION_TIME_NOT_BEFORE_TRANSITION", result["blockers"])

    def test_valid_transition_does_not_promote_blocked_v5_budget(self):
        low_bundle = self.base.build_snapshot_bundle(
            equity=5_000,
            positions=self.base.positions,
            sequence=8,
            label="low-equity-current",
        )
        low_observed_at = low_bundle["claim"]["snapshot"]["observed_at_unix_ms"]
        transition, transition_kwargs = self.build_transition(
            self.previous_state,
            self.previous_state_kwargs,
            low_bundle,
            evaluated_at=low_observed_at + 500,
        )
        result = self.evaluate_v6(
            transition=transition,
            transition_kwargs=transition_kwargs,
            bundle=low_bundle,
            evaluated_at_unix_ms=low_observed_at + 500,
        )
        self.assertEqual("PASS", transition["status"])
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("V5_EFFECTIVE_BUDGET_PASS", result["blockers"])

    def test_tampered_signature_evidence_blocks_transition(self):
        tampered = copy.deepcopy(self.bundle["evidence"])
        tampered["status"] = "BLOCKED"
        transition = budget_v6.evaluate_portfolio_snapshot_admission_transition_v1(
            self.previous_state,
            self.policy,
            tampered,
            self.bundle["signed"],
            self.bundle["claim"],
            self.base.provider,
            **self.transition_kwargs,
        )
        self.assertEqual("BLOCKED", transition["status"])
        self.assertIn("SNAPSHOT_SIGNATURE_EVIDENCE_EXACT", transition["blockers"])

    def test_provider_preregistration_drift_rejects_policy(self):
        provider = copy.deepcopy(self.base.provider)
        provider["status"] = "PASS"
        with self.assertRaises(ValueError):
            budget_v6.build_portfolio_snapshot_admission_policy_v1(
                provider,
                **self.policy_kwargs,
            )

    def test_resealed_policy_promotion_fails_stale_expected_hash(self):
        tampered = copy.deepcopy(self.policy)
        del tampered["policy_hash"]
        tampered["status"] = "PASS"
        tampered = seal_strict_canonical_document(tampered, "policy_hash")
        self.assertFalse(
            budget_v6.verify_portfolio_snapshot_admission_policy_v1(
                tampered,
                self.base.provider,
                expected_policy_hash=self.policy["policy_hash"],
                **self.policy_kwargs,
            )
        )

    def test_resealed_state_promotion_fails_stale_expected_hash(self):
        tampered = copy.deepcopy(self.previous_state)
        del tampered["state_hash"]
        tampered["status"] = "PASS"
        tampered = seal_strict_canonical_document(tampered, "state_hash")
        self.assertFalse(
            budget_v6.verify_portfolio_snapshot_admission_state_v1(
                tampered,
                self.policy,
                self.base.provider,
                expected_state_hash=self.previous_state["state_hash"],
                **self.previous_state_kwargs,
            )
        )

    def test_resealed_transition_promotion_fails_stale_expected_hash(self):
        tampered = copy.deepcopy(self.transition)
        del tampered["transition_hash"]
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "transition_hash")
        self.assertFalse(
            budget_v6.verify_portfolio_snapshot_admission_transition_v1(
                tampered,
                self.previous_state,
                self.policy,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.bundle["claim"],
                self.base.provider,
                expected_transition_hash=self.transition["transition_hash"],
                **self.transition_kwargs,
            )
        )

    def test_v6_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v6()
        kwargs = dict(self.base.increase_kwargs)
        kwargs.update(
            {
                "expected_transition_hash": self.transition["transition_hash"],
                "transition_evaluation_kwargs": self.transition_kwargs,
                "expected_current_state_hash": self.transition["next_state_hash"],
                "expected_snapshot_evidence_hash": self.bundle["evidence"][
                    "snapshot_evidence_hash"
                ],
                "snapshot_evaluation_kwargs": self.bundle["evaluation_kwargs"],
                "evaluated_at_unix_ms": self.observed_at + 500,
            }
        )
        self.assertTrue(
            budget_v6.verify_strategy_correlation_cluster_effective_bet_budget_v6(
                result,
                self.transition,
                self.previous_state,
                self.policy,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.bundle["claim"],
                self.base.provider,
                self.base.preregistration,
                self.base.matrix,
                self.base.audit,
                expected_budget_v6_hash=result["budget_v6_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        del tampered["budget_v6_hash"]
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v6_hash")
        self.assertFalse(
            budget_v6.verify_strategy_correlation_cluster_effective_bet_budget_v6(
                tampered,
                self.transition,
                self.previous_state,
                self.policy,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.bundle["claim"],
                self.base.provider,
                self.base.preregistration,
                self.base.matrix,
                self.base.audit,
                expected_budget_v6_hash=result["budget_v6_hash"],
                **kwargs,
            )
        )

    def test_boolean_numeric_aliases_are_rejected(self):
        with self.assertRaises(ValueError):
            budget_v6.build_portfolio_snapshot_admission_policy_v1(
                self.base.provider,
                **{**self.policy_kwargs, "maximum_snapshot_age_ms": True},
            )
        with self.assertRaises(ValueError):
            budget_v6.build_portfolio_snapshot_admission_state_v1(
                self.policy,
                self.base.provider,
                **{**self.previous_state_kwargs, "state_revision": True},
            )
        with self.assertRaises(ValueError):
            budget_v6.evaluate_portfolio_snapshot_admission_transition_v1(
                self.previous_state,
                self.policy,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.bundle["claim"],
                self.base.provider,
                **{**self.transition_kwargs, "evaluated_at_unix_ms": True},
            )
        with self.assertRaises(ValueError):
            self.evaluate_v6(evaluated_at_unix_ms=True)

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        inputs_before = copy.deepcopy(
            {
                "transition": self.transition,
                "state": self.previous_state,
                "policy": self.policy,
                "evidence": self.bundle["evidence"],
                "signed": self.bundle["signed"],
                "claim": self.bundle["claim"],
            }
        )
        first = self.evaluate_v6()
        second = self.evaluate_v6()
        self.assertEqual(first, second)
        self.assertEqual(inputs_before["transition"], self.transition)
        self.assertEqual(inputs_before["state"], self.previous_state)
        self.assertEqual(inputs_before["policy"], self.policy)
        self.assertEqual(inputs_before["evidence"], self.bundle["evidence"])
        self.assertEqual(inputs_before["signed"], self.bundle["signed"])
        self.assertEqual(inputs_before["claim"], self.bundle["claim"])

        def keys(value):
            if isinstance(value, dict):
                found = set(value)
                for child in value.values():
                    found.update(keys(child))
                return found
            if isinstance(value, list):
                found = set()
                for child in value:
                    found.update(keys(child))
                return found
            return set()

        output_keys = keys(first)
        self.assertNotIn("positions", output_keys)
        self.assertNotIn("public_key_spki_base64", output_keys)
        self.assertNotIn("signature_base64", output_keys)
        self.assertNotIn("signature", output_keys)

    def test_production_has_no_private_key_clock_io_network_or_runtime_access(self):
        source = Path(budget_v6.__file__).read_text(encoding="utf-8")
        forbidden = (
            "Ed25519PrivateKey",
            "private_key",
            "time.time",
            "datetime.now",
            "Path(",
            "open(",
            "requests.",
            "urllib.",
            "sqlite3",
            ".env",
            "runtime/",
            "runtime\\\\",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
