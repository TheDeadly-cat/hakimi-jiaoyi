from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate import (
    GATE_SCHEMA,
    PRECOMMIT_SCHEMA,
    PRECOMMIT_STATIC_FINGERPRINT,
    PROTOCOL_ID,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_report_consumer as g1_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = g1_fixtures.StrategyCorrelationCrossLagFactorCalibrationReportConsumerTests(
            methodName="test_match_source_is_observed_without_attestation"
        )
        case.setUp()
        self.case = case
        self.registration = case.registration
        self.observations = case.observations
        self.replay = case.replay
        self.report = case._consume()
        self.declaration = self._declaration(self.report)

    def _declaration(self, report, **overrides):
        summary = report["calibration_summary"]
        document = {
            "schema_version": PRECOMMIT_SCHEMA,
            "static_fingerprint": PRECOMMIT_STATIC_FINGERPRINT,
            "protocol_id": PROTOCOL_ID,
            "future_evaluation_id": "EVAL-2025-02-A",
            "source_report_hash": report["verification_hash"],
            "source_replay_hash": report["source_replay_hash"],
            "source_registration_hash": report["source_registration_hash"],
            "source_calibration_observations_hash": report[
                "source_calibration_observations_hash"
            ],
            "registered_beta_ledger_hash": report[
                "source_registered_beta_ledger_hash"
            ],
            "replayed_beta_ledger_hash": report[
                "source_replayed_beta_ledger_hash"
            ],
            "calibration_cutoff_date": summary["calibration_cutoff_date"],
            "selection_cutoff_date": summary["selection_cutoff_date"],
            "precommit_declared_at_utc": "2025-01-15T00:00:00Z",
            "evaluation_not_before_date": summary["selection_cutoff_date"],
            "external_time_anchor_reference_hash": "a" * 64,
        }
        document.update(overrides)
        return seal_strict_canonical_document(document, "declaration_hash")

    def _evaluate(
        self,
        declaration=...,
        *,
        report=...,
        replay=...,
        registration=None,
        observations=None,
        expected_declaration_hash=None,
        expected_report_hash=None,
        expected_replay_hash=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
    ):
        declaration = self.declaration if declaration is ... else declaration
        report = self.report if report is ... else report
        replay = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_declaration_hash is None:
            expected_declaration_hash = (
                "" if declaration is None else declaration["declaration_hash"]
            )
        if expected_report_hash is None:
            expected_report_hash = report["verification_hash"]
        if expected_replay_hash is None:
            expected_replay_hash = replay["receipt_hash"]
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _verify(self, gate, declaration=..., **kwargs):
        declaration = self.declaration if declaration is ... else declaration
        report = kwargs.pop("report", self.report)
        replay = kwargs.pop("replay", self.replay)
        registration = kwargs.pop("registration", self.registration)
        observations = kwargs.pop("observations", self.observations)
        expected_declaration_hash = kwargs.pop(
            "expected_declaration_hash",
            "" if declaration is None else declaration["declaration_hash"],
        )
        expected_report_hash = kwargs.pop(
            "expected_report_hash", report["verification_hash"]
        )
        expected_replay_hash = kwargs.pop(
            "expected_replay_hash", replay["receipt_hash"]
        )
        expected_registration_hash = kwargs.pop(
            "expected_registration_hash", registration["registration_hash"]
        )
        expected_observations_hash = kwargs.pop(
            "expected_observations_hash",
            observations["calibration_observations_hash"],
        )
        self.assertFalse(kwargs)
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
            gate,
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _block_context(self):
        registration, replay = self.case._block_source()
        report = self.case._consume(replay, registration=registration)
        declaration = self._declaration(report)
        return registration, replay, report, declaration

    def test_match_is_bound_local_only(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["source_state"], "OBSERVED")
        self.assertEqual(gate["gate_decision"], "BOUND_LOCAL_ONLY")
        self.assertTrue(gate["facts"]["hash_chain_bound"])
        self.assertFalse(gate["facts"]["external_time_anchor_verified"])
        self.assertTrue(self._verify(gate))

    def test_block_replay_remains_blocked(self) -> None:
        registration, replay, report, declaration = self._block_context()
        gate = self._evaluate(
            declaration,
            report=report,
            replay=replay,
            registration=registration,
        )
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertIn("REGISTERED_BETA_REPLAY_MISMATCH", gate["blockers"])
        self.assertIn("FUTURE_EVALUATION_PRECOMMIT_BLOCKED", gate["blockers"])
        self.assertTrue(
            self._verify(
                gate,
                declaration,
                report=report,
                replay=replay,
                registration=registration,
            )
        )

    def test_missing_declaration_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["gate_decision"], "UNKNOWN")
        self.assertEqual(gate["blockers"], ["PRECOMMIT_DECLARATION_MISSING"])
        self.assertTrue(self._verify(gate, None))

    def test_unsupported_declaration_has_fixed_unknown_closure(self) -> None:
        declaration = {
            "schema_version": "candidate-v0",
            "static_fingerprint": "candidate-0",
        }
        gate = self._evaluate(
            declaration, expected_declaration_hash="a" * 64
        )
        self.assertEqual(gate["source_state"], "UNSUPPORTED")
        self.assertEqual(gate["blockers"], ["PRECOMMIT_DECLARATION_UNSUPPORTED"])

    def test_expected_declaration_hash_is_bound(self) -> None:
        gate = self._evaluate(expected_declaration_hash="0" * 64)
        self.assertEqual(gate["source_state"], "INVALID")

    def test_broken_declaration_hash_is_invalid(self) -> None:
        declaration = deepcopy(self.declaration)
        declaration["declaration_hash"] = "0" * 64
        gate = self._evaluate(
            declaration, expected_declaration_hash="0" * 64
        )
        self.assertEqual(gate["source_state"], "INVALID")

    def test_every_source_hash_binding_is_required(self) -> None:
        for field in (
            "source_report_hash",
            "source_replay_hash",
            "source_registration_hash",
            "source_calibration_observations_hash",
        ):
            declaration = self._declaration(self.report, **{field: "0" * 64})
            gate = self._evaluate(declaration)
            self.assertEqual(gate["source_state"], "INVALID", field)

    def test_both_beta_ledger_hashes_are_bound(self) -> None:
        for field in ("registered_beta_ledger_hash", "replayed_beta_ledger_hash"):
            declaration = self._declaration(self.report, **{field: "0" * 64})
            gate = self._evaluate(declaration)
            self.assertEqual(gate["source_state"], "INVALID", field)

    def test_cutoff_dates_are_bound_to_report(self) -> None:
        for field, value in (
            ("calibration_cutoff_date", "2025-01-02"),
            ("selection_cutoff_date", "2025-02-02"),
        ):
            declaration = self._declaration(self.report, **{field: value})
            gate = self._evaluate(declaration)
            self.assertEqual(gate["source_state"], "INVALID", field)

    def test_precommit_date_must_be_between_cutoffs(self) -> None:
        for timestamp in (
            "2025-01-01T00:00:00Z",
            "2025-02-01T00:00:00Z",
            "2025-01-15T00:00:00+00:00",
        ):
            declaration = self._declaration(
                self.report, precommit_declared_at_utc=timestamp
            )
            gate = self._evaluate(declaration)
            self.assertEqual(gate["source_state"], "INVALID", timestamp)

    def test_evaluation_not_before_selection_cutoff(self) -> None:
        declaration = self._declaration(
            self.report, evaluation_not_before_date="2025-01-31"
        )
        self.assertEqual(self._evaluate(declaration)["source_state"], "INVALID")

    def test_evaluation_id_and_protocol_are_strict(self) -> None:
        for overrides in (
            {"future_evaluation_id": "short"},
            {"future_evaluation_id": "EVAL 2025 02 A"},
            {"protocol_id": "FUTURE_FACTOR_RESIDUALIZATION_EVALUATION_V3"},
        ):
            declaration = self._declaration(self.report, **overrides)
            self.assertEqual(
                self._evaluate(declaration)["source_state"], "INVALID"
            )

    def test_external_anchor_is_hash_bound_but_never_verified(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["external_time_anchor_reference_hash"],
            self.declaration["external_time_anchor_reference_hash"],
        )
        self.assertFalse(gate["facts"]["external_time_anchor_verified"])
        self.assertIn(
            "EXTERNAL_PRECOMMIT_TIME_ANCHOR_UNVERIFIED", gate["blockers"]
        )

    def test_source_context_substitution_is_invalid(self) -> None:
        observations = self.case.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )
        registration = self.case.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        self.assertEqual(
            self._evaluate(registration=registration)["source_state"], "INVALID"
        )

    def test_coherently_resealed_report_tamper_is_invalid(self) -> None:
        report = deepcopy(self.report)
        report["gap_state"] = "CALIBRATION_REPLAY_MISMATCH"
        report = seal_strict_canonical_document(report, "verification_hash")
        declaration = self._declaration(report)
        gate = self._evaluate(declaration, report=report)
        self.assertEqual(gate["source_state"], "INVALID")

    def test_projection_is_aggregate_only(self) -> None:
        gate = self._evaluate()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(gate)
        self.assertTrue(
            {
                "rows",
                "identity_order",
                "beta_by_identity",
                "factor_id",
                "factor_source_hash",
                "returns_by_identity",
                "factor_return",
            }.isdisjoint(keys)
        )
        self.assertNotIn("COMMON-FACTOR-1", json.dumps(gate, sort_keys=True))

    def test_authority_is_permanently_locked(self) -> None:
        for gate in (self._evaluate(), self._evaluate(None)):
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["future_evaluation_allowed"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_inputs_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._evaluate(DictSubclass(self.declaration))["source_state"],
            "INVALID",
        )
        declaration = deepcopy(self.declaration)
        declaration["future_evaluation_id"] = float("nan")
        self.assertEqual(
            self._evaluate(
                declaration,
                expected_declaration_hash=self.declaration["declaration_hash"],
            )["source_state"],
            "INVALID",
        )

    def test_resealed_gate_tamper_is_rejected(self) -> None:
        gate = self._evaluate()
        for field, value in (
            ("gate_decision", "ADMIT"),
            ("source_state", "READY"),
        ):
            tampered = deepcopy(gate)
            tampered[field] = value
            tampered = seal_strict_canonical_document(tampered, "gate_hash")
            self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("pathlib.Path.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._evaluate()
            second = self._evaluate()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_and_fingerprints_are_exact(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            PRECOMMIT_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-declaration-candidate-v1",
        )
        self.assertEqual(
            PRECOMMIT_STATIC_FINGERPRINT,
            "20260824-cross-lag-factor-calibration-precommit-declaration-1",
        )
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260824-cross-lag-factor-calibration-precommit-gate-1",
        )
        self.assertEqual(gate["protocol_id"], PROTOCOL_ID)


if __name__ == "__main__":
    unittest.main()
