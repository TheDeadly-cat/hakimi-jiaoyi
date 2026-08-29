from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope import (
    ENVELOPE_SCHEMA,
    GATE_SCHEMA,
    GATE_STATIC_FINGERPRINT,
    PRESENTATION_STATUS,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2 as h1_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = h1_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV2Tests(
            methodName="test_complete_context_is_bound_for_both_verifiers"
        )
        case.setUp()
        self.case = case
        self.precommit_gate_v1 = case.precommit_gate_v1
        self.stability_gate = case.stability_gate
        self.declaration = case.declaration
        self.report = case.report
        self.replay = case.replay
        self.registration = case.registration
        self.observations = case.observations
        self.gate = case._evaluate()

    def _build(
        self,
        gate=...,
        *,
        precommit_gate_v1=...,
        stability_gate=...,
        declaration=...,
        report=...,
        replay=...,
        registration=...,
        observations=...,
        expected_gate_hash=None,
        expected_precommit_gate_v1_hash=None,
        expected_stability_gate_hash=None,
        expected_declaration_hash=None,
        expected_report_hash=None,
        expected_replay_hash=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
    ):
        gate = self.gate if gate is ... else gate
        precommit_gate_v1 = (
            self.precommit_gate_v1
            if precommit_gate_v1 is ...
            else precommit_gate_v1
        )
        stability_gate = (
            self.stability_gate if stability_gate is ... else stability_gate
        )
        declaration = self.declaration if declaration is ... else declaration
        report = self.report if report is ... else report
        replay = self.replay if replay is ... else replay
        registration = self.registration if registration is ... else registration
        observations = self.observations if observations is ... else observations

        if expected_gate_hash is None:
            expected_gate_hash = "" if gate is None else gate["gate_hash"]
        if expected_precommit_gate_v1_hash is None:
            expected_precommit_gate_v1_hash = (
                ""
                if precommit_gate_v1 is None
                else precommit_gate_v1["gate_hash"]
            )
        if expected_stability_gate_hash is None:
            expected_stability_gate_hash = (
                "" if stability_gate is None else stability_gate["gate_hash"]
            )
        if expected_declaration_hash is None:
            expected_declaration_hash = (
                "" if declaration is None else declaration["declaration_hash"]
            )
        if expected_report_hash is None:
            expected_report_hash = (
                "" if report is None else report["verification_hash"]
            )
        if expected_replay_hash is None:
            expected_replay_hash = "" if replay is None else replay["receipt_hash"]
        if expected_registration_hash is None:
            expected_registration_hash = (
                "" if registration is None else registration["registration_hash"]
            )
        if expected_observations_hash is None:
            expected_observations_hash = (
                ""
                if observations is None
                else observations["calibration_observations_hash"]
            )
        return build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope(
            gate,
            precommit_gate_v1,
            stability_gate,
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_gate_hash=expected_gate_hash,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_stability_gate_hash=expected_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _verify(self, envelope, **overrides):
        gate = overrides.pop("gate", self.gate)
        precommit_gate_v1 = overrides.pop(
            "precommit_gate_v1", self.precommit_gate_v1
        )
        stability_gate = overrides.pop("stability_gate", self.stability_gate)
        declaration = overrides.pop("declaration", self.declaration)
        report = overrides.pop("report", self.report)
        replay = overrides.pop("replay", self.replay)
        registration = overrides.pop("registration", self.registration)
        observations = overrides.pop("observations", self.observations)
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope(
            envelope,
            gate,
            precommit_gate_v1,
            stability_gate,
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_gate_hash=overrides.pop(
                "expected_gate_hash", "" if gate is None else gate["gate_hash"]
            ),
            expected_precommit_gate_v1_hash=overrides.pop(
                "expected_precommit_gate_v1_hash",
                "" if precommit_gate_v1 is None else precommit_gate_v1["gate_hash"],
            ),
            expected_stability_gate_hash=overrides.pop(
                "expected_stability_gate_hash",
                "" if stability_gate is None else stability_gate["gate_hash"],
            ),
            expected_declaration_hash=overrides.pop(
                "expected_declaration_hash",
                "" if declaration is None else declaration["declaration_hash"],
            ),
            expected_report_hash=overrides.pop(
                "expected_report_hash",
                "" if report is None else report["verification_hash"],
            ),
            expected_replay_hash=overrides.pop(
                "expected_replay_hash",
                "" if replay is None else replay["receipt_hash"],
            ),
            expected_registration_hash=overrides.pop(
                "expected_registration_hash",
                "" if registration is None else registration["registration_hash"],
            ),
            expected_calibration_observations_hash=overrides.pop(
                "expected_observations_hash",
                ""
                if observations is None
                else observations["calibration_observations_hash"],
            ),
        )

    def _context_envelope(self, context):
        gate = self.case._evaluate(**context)
        return self._build(
            gate,
            precommit_gate_v1=context["precommit_gate_v1"],
            stability_gate=context["stability_gate"],
            declaration=context["declaration"],
            report=context["report"],
            replay=context["replay"],
            registration=context["registration"],
            observations=context["observations"],
        )

    def test_stability_guarded_gate_is_verified_and_copied(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "OBSERVED")
        self.assertEqual(
            envelope["gate"]["gate_decision"],
            "BOUND_LOCAL_ONLY_STABILITY_GUARDED",
        )
        self.assertEqual(envelope["source_gate_hash"], self.gate["gate_hash"])
        self.assertTrue(self._verify(envelope))

    def test_h0_block_remains_block(self) -> None:
        envelope = self._context_envelope(self.case._drift_context())
        self.assertEqual(envelope["gate"]["gate_decision"], "BLOCK")
        self.assertEqual(envelope["gate"]["gate_reason"], "BETA_STABILITY_GATE_BLOCKED")

    def test_g3_source_block_remains_block(self) -> None:
        envelope = self._context_envelope(self.case._source_block_context())
        self.assertEqual(envelope["gate"]["gate_decision"], "BLOCK")
        self.assertEqual(envelope["gate"]["gate_reason"], "SOURCE_PRECOMMIT_GATE_BLOCKED")

    def test_verified_missing_source_gate_remains_distinct_unknown(self) -> None:
        gate = self.case._evaluate(precommit_gate_v1=None)
        envelope = self._build(gate, precommit_gate_v1=None)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "MISSING")
        self.assertEqual(envelope["gate"]["gate_decision"], "UNKNOWN")

    def test_not_supplied_gate_is_closed_without_source_upgrade(self) -> None:
        envelope = self._build(None)
        self.assertEqual(envelope["source_state"], "NOT_SUPPLIED")
        self.assertEqual(envelope["verification_state"], "UNKNOWN")
        self.assertIsNone(envelope["gate"])

    def test_unsupported_gate_is_distinct(self) -> None:
        gate = deepcopy(self.gate)
        gate["schema_version"] = "unsupported-gate-v99"
        gate = seal_strict_canonical_document(gate, "gate_hash")
        envelope = self._build(gate)
        self.assertEqual(envelope["source_state"], "UNSUPPORTED")

    def test_expected_gate_hash_substitution_is_invalid(self) -> None:
        envelope = self._build(expected_gate_hash="0" * 64)
        self.assertEqual(envelope["source_state"], "INVALID")

    def test_complete_context_substitution_is_invalid(self) -> None:
        observations = self.case.fixture._observations(count=39)
        self.assertEqual(
            self._build(observations=observations)["source_state"], "INVALID"
        )
        registration = self.case.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        self.assertEqual(
            self._build(registration=registration)["source_state"], "INVALID"
        )

    def test_coherently_resealed_gate_tamper_is_invalid(self) -> None:
        gate = deepcopy(self.gate)
        gate["maximum_observed_normalized_beta_drift"] = "2"
        gate = seal_strict_canonical_document(gate, "gate_hash")
        self.assertEqual(self._build(gate)["source_state"], "INVALID")

    def test_envelope_tamper_fails_exact_verification(self) -> None:
        envelope = self._build()
        envelope["envelope_reason"] = "H1_PRECOMMIT_GATE_INVALID"
        self.assertFalse(self._verify(envelope))

    def test_source_mutation_cannot_change_embedded_copy(self) -> None:
        envelope = self._build()
        self.gate["blockers"].append("MUTATED_AFTER_BUILD")
        self.assertNotIn("MUTATED_AFTER_BUILD", envelope["gate"]["blockers"])

    def test_projection_is_aggregate_only(self) -> None:
        def collect_keys(value):
            keys = set()
            if type(value) is dict:
                for key, nested in value.items():
                    keys.add(key)
                    keys.update(collect_keys(nested))
            elif type(value) is list:
                for nested in value:
                    keys.update(collect_keys(nested))
            return keys

        keys = collect_keys(self._build())
        for forbidden in (
            "beta_by_identity",
            "factor_return",
            "identity_order",
            "returns_by_identity",
            "rows",
        ):
            self.assertNotIn(forbidden, keys)

    def test_authority_is_locked_and_non_proof(self) -> None:
        envelope = self._build()
        self.assertFalse(strict_research_authority_invalid(envelope["authority"]))
        self.assertFalse(envelope["authority"]["beta_temporal_stability_proven"])
        self.assertFalse(envelope["authority"]["paper_authorized"])
        self.assertFalse(envelope["authority"]["live_order_allowed"])

    def test_nonnative_and_nonfinite_gate_inputs_close_invalid(self) -> None:
        class MappingSubclass(dict):
            pass

        self.assertEqual(self._build(MappingSubclass(self.gate))["source_state"], "INVALID")
        gate = deepcopy(self.gate)
        gate["fold_count"] = float("nan")
        self.assertEqual(self._build(gate)["source_state"], "INVALID")

    def test_deterministic_build_uses_no_external_state(self) -> None:
        with (
            patch("builtins.open", side_effect=AssertionError("external read")),
            patch("socket.create_connection", side_effect=AssertionError("network")),
            patch("time.time", side_effect=AssertionError("clock")),
        ):
            first = self._build()
            second = self._build()
        self.assertEqual(first, second)

    def test_schema_fingerprint_and_status_are_exact(self) -> None:
        self.assertEqual(
            ENVELOPE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260827-cross-lag-factor-calibration-precommit-presentation-envelope-1",
        )
        self.assertEqual(PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE")
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v2",
        )
        self.assertEqual(
            GATE_STATIC_FINGERPRINT,
            "20260826-cross-lag-factor-calibration-precommit-gate-2",
        )
