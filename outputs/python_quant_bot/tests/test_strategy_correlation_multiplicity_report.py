from __future__ import annotations

from copy import deepcopy
import sys
import unittest

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strategy_correlation_multiplicity_audit import (
    build_strategy_correlation_multiplicity_audit,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    assess_strategy_correlation_multiplicity_binding,
    build_strategy_correlation_multiplicity_family_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_report import (
    build_strategy_correlation_multiplicity_report_evidence,
    verify_strategy_correlation_multiplicity_report_evidence,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_replayed_correlation_cluster_gate,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    build_strategy_research_protocol_artifact_binding,
)
from tests import test_strategy_correlation_return_replay as replay_tests
from tests import test_strategy_matrix_protocol as protocol_tests


class StrategyCorrelationMultiplicityReportTests(unittest.TestCase):
    def _chain(self, *, gate_pass: bool) -> dict:
        captures: dict[str, list[dict]] = {}
        tracked = {
            "build_correlation_completed_price_input",
            "build_correlation_matrix_replay",
        }

        def trace(frame, event, arg):
            if event == "return" and frame.f_code.co_name in tracked and isinstance(arg, dict):
                captures.setdefault(frame.f_code.co_name, []).append(arg)
            return trace

        replay_case = replay_tests.StrategyCorrelationReturnReplayTests(
            "test_price_replay_recomputes_matrix_and_collapses_symbol_majority"
        )
        replay_result = unittest.TestResult()
        sys.settrace(trace)
        try:
            replay_case.run(replay_result)
        finally:
            sys.settrace(None)
        self.assertTrue(replay_result.wasSuccessful())
        completed = captures["build_correlation_completed_price_input"][0]
        matrix = captures["build_correlation_matrix_replay"][0]

        fixture_type = protocol_tests.StrategyMatrixProtocolTests
        fixture_method = next(name for name in dir(fixture_type) if name.startswith("test_"))
        fixture = fixture_type(fixture_method)
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        store = StrategyMatrixRegistrationStore(
            db_path=fixture.runtime / "strategy_research_registrations.sqlite3",
            now_ms=lambda: 1_000_000,
            canonical_runtime_root=fixture.runtime,
        )
        base = fixture.schema14_protocol(
            store=store,
            registration_id="multiplicity-report-fixture",
        )
        batch_spec = deepcopy(base["batch_spec"])
        batch_spec["report_schema_version"] = TARGET_REPORT_SCHEMA_VERSION
        batch_spec["selection_symbols"] = list(matrix["preregistration"]["symbols"])
        variant = batch_spec["variants"][0]
        cells = [{
            "symbol": symbol,
            "strategy_id": variant["strategy_id"],
            "variant_id": variant["variant_id"],
            "lane": "RAW_EXCESS",
            "gate_status": "PASS" if gate_pass else "BLOCK",
        } for symbol in matrix["preregistration"]["symbols"]]
        gate = build_replayed_correlation_cluster_gate(
            matrix,
            cells,
            strategy_id=variant["strategy_id"],
            variant_id=variant["variant_id"],
            lane="RAW_EXCESS",
        )
        source = build_strategy_correlation_protocol_registration_v2(
            matrix["preregistration"],
            cutoff_date=completed["cutoff_date"],
            selection_alignment_input_hash=completed["selection_alignment_input_hash"],
            evaluations=[{
                "strategy_id": variant["strategy_id"],
                "variant_id": variant["variant_id"],
                "lane": "RAW_EXCESS",
            }],
        )
        uncertainty = build_strategy_correlation_uncertainty_audit(matrix)
        multiplicity = build_strategy_correlation_multiplicity_audit(uncertainty)
        family = build_strategy_correlation_multiplicity_family_registration(source)
        family_assessment = assess_strategy_correlation_multiplicity_binding(
            family,
            multiplicity,
        )
        registration_v3 = build_strategy_correlation_multiplicity_protocol_registration(
            family
        )
        protocol = build_strategy_matrix_protocol(
            registration_id=base["registration_id"],
            research_generation=base["research_generation"],
            batch_spec=batch_spec,
            implementation_manifest=base["implementation_manifest"],
            exposure_audit=base["holdout_exposure_audit"],
            registration_clock_attestation=base["registration_clock_attestation"],
            expires_at_ms=base["expires_at_ms"],
            registry_path=base["registry_path"],
            protocol_artifact=build_strategy_research_protocol_artifact_binding(
                fixture.reports / "multiplicity-report-protocol.json"
            ),
            correlation_multiplicity_protocol_registration=registration_v3,
        )
        return {
            "protocol": protocol,
            "gate": gate,
            "uncertainty": uncertainty,
            "multiplicity": multiplicity,
            "assessment": family_assessment,
        }

    def _evidence(self, chain: dict) -> dict:
        return build_strategy_correlation_multiplicity_report_evidence(
            chain["protocol"],
            chain["gate"],
            chain["uncertainty"],
            chain["multiplicity"],
            chain["assessment"],
        )

    def test_positive_chain_is_valid_but_still_requires_schema8_envelope(self) -> None:
        chain = self._chain(gate_pass=True)
        evidence = self._evidence(chain)
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            evidence,
            protocol=chain["protocol"],
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["decision_status"], "PASS")
        self.assertEqual(evidence["expected_family_size"], 7)
        self.assertEqual(evidence["observed_family_size"], 7)
        self.assertEqual(evidence["required_matrix_report_schema_version"], 8)
        self.assertEqual(evidence["next_evidence_required"], "MATRIX_REPORT_SCHEMA_8_ENVELOPE")
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(evidence["formal_registry_bound"])
        self.assertFalse(evidence["current_admission_allowed"])

    def test_gate_block_is_monotonic_while_artifact_verification_passes(self) -> None:
        chain = self._chain(gate_pass=False)
        evidence = self._evidence(chain)
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            evidence,
            protocol=chain["protocol"],
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["decision_status"], "BLOCK")
        self.assertEqual(evidence["next_evidence_required"], "CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER")
        self.assertIn("correlation_gate_decision_block", evidence["blockers"])
        self.assertEqual(verification["status"], "PASS")

    def test_invalid_chain_is_sanitized_without_symbol_or_pair_echo(self) -> None:
        chain = self._chain(gate_pass=True)
        chain["uncertainty"]["matrix_replay"] = {"symbols": ["SECRET_SYMBOL"]}
        evidence = self._evidence(chain)
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            evidence,
            protocol=chain["protocol"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIsNone(evidence["replayed_gate"])
        self.assertIsNone(evidence["uncertainty_audit"])
        self.assertNotIn("SECRET_SYMBOL", repr(evidence))
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["evidence_status"], "BLOCK")

    def test_resealed_summary_or_embedded_evidence_drift_is_blocked(self) -> None:
        chain = self._chain(gate_pass=True)
        evidence = self._evidence(chain)
        summary_forged = deepcopy(evidence)
        summary_forged["expected_family_size"] = 999
        embedded_forged = deepcopy(evidence)
        embedded_forged["multiplicity_audit"]["family_size"] = 999
        for forged in (summary_forged, embedded_forged):
            clean = dict(forged)
            clean.pop("evidence_hash")
            forged["evidence_hash"] = canonical_hash(clean)
            verification = verify_strategy_correlation_multiplicity_report_evidence(
                forged,
                protocol=chain["protocol"],
            )
            self.assertEqual(verification["status"], "BLOCK")

    def test_authority_reseal_is_blocked(self) -> None:
        chain = self._chain(gate_pass=True)
        forged = self._evidence(chain)
        forged["permissions"]["paper_authorized"] = True
        clean = dict(forged)
        clean.pop("evidence_hash")
        forged["evidence_hash"] = canonical_hash(clean)
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            forged,
            protocol=chain["protocol"],
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(any("authority" in item for item in verification["blockers"]))
