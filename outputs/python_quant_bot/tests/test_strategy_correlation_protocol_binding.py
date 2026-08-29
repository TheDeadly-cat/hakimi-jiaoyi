from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    assess_strategy_correlation_protocol_binding,
    build_strategy_correlation_protocol_registration,
    build_strategy_correlation_protocol_registration_v2,
    verify_strategy_correlation_protocol_binding_assessment,
    verify_strategy_correlation_protocol_registration,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION,
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
    canonical_hash,
    verify_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    build_strategy_research_protocol_artifact_binding,
    publish_strategy_research_protocol_artifact_no_clobber,
    verify_bound_strategy_research_protocol_artifact,
)
from tests.test_strategy_matrix_protocol import StrategyMatrixProtocolTests


class StrategyCorrelationProtocolBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "equity-tech", "members": ["AAPL", "MSFT"]},
            {"cluster_id": "defensive", "members": ["GLD", "TLT"]},
            {"cluster_id": "crypto", "members": ["BTC-USDT"]},
        ])
        self.registration = build_strategy_correlation_protocol_registration(
            self.preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="a" * 64,
            evaluations=[
                {
                    "strategy_id": "dual_ma",
                    "variant_id": "fixed-v1",
                    "lane": "RAW_EXCESS",
                },
                {
                    "strategy_id": "dual_ma",
                    "variant_id": "fixed-v1",
                    "lane": "RISK_ADJUSTED",
                },
            ],
        )
        self.registration_v2 = build_strategy_correlation_protocol_registration_v2(
            self.preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="a" * 64,
            evaluations=[
                {
                    "strategy_id": "dual_ma",
                    "variant_id": "fixed-v1",
                    "lane": "RAW_EXCESS",
                },
                {
                    "strategy_id": "dual_ma",
                    "variant_id": "fixed-v1",
                    "lane": "RISK_ADJUSTED",
                },
            ],
        )

    def _synthetic_gate(self) -> dict[str, object]:
        return {
            "status": "PASS",
            "schema_version": "strategy-correlation-replayed-gate-v1",
            "strategy_id": "dual_ma",
            "variant_id": "fixed-v1",
            "lane": "RAW_EXCESS",
            "evaluation_hash": "e" * 64,
            "matrix_replay": {
                "preregistration": deepcopy(self.preregistration),
                "completed_price_input": {
                    "cutoff_date": "2026-03-02",
                    "selection_alignment_input_hash": "a" * 64,
                },
            },
        }

    def _synthetic_protocol(self) -> dict[str, object]:
        return {
            "schema_version": "strategy-matrix-protocol-v3",
            "protocol_hash": "p" * 64,
            "batch_spec": {"report_schema_version": 14},
        }

    def test_registration_is_canonical_versioned_and_authority_free(self) -> None:
        verification = verify_strategy_correlation_protocol_registration(self.registration)

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            self.registration["target_protocol_schema_version"],
            "strategy-matrix-protocol-v4",
        )
        self.assertEqual(self.registration["target_report_schema_version"], 15)
        self.assertTrue(self.registration["requires_protocol_upgrade"])
        self.assertTrue(self.registration["requires_new_report_schema"])
        self.assertFalse(self.registration["current_writer_activation_allowed"])
        self.assertFalse(self.registration["current_admission_allowed"])
        self.assertFalse(self.registration["permissions"]["paper_authorized"])
        self.assertFalse(self.registration["permissions"]["live_order_allowed"])
        self.assertEqual(
            [item["lane"] for item in self.registration["evaluations"]],
            ["RAW_EXCESS", "RISK_ADJUSTED"],
        )

    def test_registration_rejects_cutoff_hash_duplicates_and_noncanonical_order(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy_correlation_protocol_registration(
                self.preregistration,
                cutoff_date="2026-3-2",
                selection_alignment_input_hash="not-a-hash",
                evaluations=[
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "fixed-v1",
                        "lane": "RAW_EXCESS",
                    },
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "fixed-v1",
                        "lane": "RAW_EXCESS",
                    },
                ],
            )
        tampered = deepcopy(self.registration)
        tampered["evaluations"] = list(reversed(tampered["evaluations"]))
        clean = dict(tampered)
        clean.pop("registration_hash")
        tampered["registration_hash"] = canonical_hash(clean)
        verification = verify_strategy_correlation_protocol_registration(tampered)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_registration_evaluations_noncanonical",
            verification["blockers"],
        )

    def test_registration_rejects_resealed_authority_alias_and_extra_field(self) -> None:
        tampered = deepcopy(self.registration)
        tampered["permissions"]["can_trade"] = True
        tampered["unregistered_note"] = "retrofit"
        clean = dict(tampered)
        clean.pop("registration_hash")
        tampered["registration_hash"] = canonical_hash(clean)

        verification = verify_strategy_correlation_protocol_registration(tampered)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("strategy_correlation_registration_fields_invalid", verification["blockers"])
        self.assertIn(
            "strategy_correlation_registration_authority_violation",
            verification["blockers"],
        )

    def test_local_chain_match_still_requires_protocol_v4_and_report_schema15(self) -> None:
        gate = self._synthetic_gate()
        protocol = self._synthetic_protocol()
        with (
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_replayed_correlation_cluster_gate",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_strategy_matrix_protocol",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            assessment = assess_strategy_correlation_protocol_binding(
                protocol,
                self.registration,
                gate,
            )
            verification = verify_strategy_correlation_protocol_binding_assessment(
                assessment,
                protocol=protocol,
                registration=self.registration,
                replayed_gate=gate,
            )

        self.assertEqual(assessment["local_chain_status"], "PASS")
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["formal_registry_bound"])
        self.assertFalse(assessment["preregistered_cutoff_bound"])
        self.assertFalse(assessment["current_report_schema_bound"])
        self.assertFalse(assessment["current_writer_activation_allowed"])
        self.assertFalse(assessment["current_admission_allowed"])
        self.assertEqual(
            assessment["next_evidence_required"],
            "CORRELATION_PROTOCOL_REGISTRATION_V2",
        )
        self.assertEqual(verification["status"], "PASS")

    def test_cutoff_or_evaluation_drift_blocks_local_chain(self) -> None:
        gate = self._synthetic_gate()
        gate["matrix_replay"]["completed_price_input"]["cutoff_date"] = "2026-03-03"
        gate["lane"] = "RISK_ADJUSTED-RETROFIT"
        with (
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_replayed_correlation_cluster_gate",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_strategy_matrix_protocol",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            assessment = assess_strategy_correlation_protocol_binding(
                self._synthetic_protocol(),
                self.registration,
                gate,
            )

        self.assertEqual(assessment["local_chain_status"], "BLOCK")
        self.assertIn("local_preregistered_cutoff_mismatch", assessment["blockers"])
        self.assertIn("local_evaluation_not_preregistered", assessment["blockers"])
        self.assertEqual(assessment["next_evidence_required"], "VALID_LOCAL_REPLAY_CHAIN")

    def test_resealed_assessment_cannot_claim_formal_binding(self) -> None:
        gate = self._synthetic_gate()
        protocol = self._synthetic_protocol()
        with (
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_replayed_correlation_cluster_gate",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_strategy_matrix_protocol",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            assessment = assess_strategy_correlation_protocol_binding(
                protocol,
                self.registration,
                gate,
            )
            forged = deepcopy(assessment)
            forged["status"] = "PASS"
            forged["formal_registry_bound"] = True
            forged["current_report_schema_bound"] = True
            clean = dict(forged)
            clean.pop("assessment_hash")
            forged["assessment_hash"] = canonical_hash(clean)
            verification = verify_strategy_correlation_protocol_binding_assessment(
                forged,
                protocol=protocol,
                registration=self.registration,
                replayed_gate=gate,
            )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_binding_assessment_replay_mismatch",
            verification["blockers"],
        )

    def test_protocol_v2_and_v3_reject_coherently_resealed_retrofit(self) -> None:
        fixture = StrategyMatrixProtocolTests("runTest")
        fixture.setUp()
        try:
            protocol_v2 = fixture.protocol()
            self.assertEqual(
                verify_strategy_matrix_protocol(
                    protocol_v2,
                    verify_current_implementation=False,
                )["status"],
                "PASS",
            )
            protocol_artifact = build_strategy_research_protocol_artifact_binding(
                Path(protocol_v2["registry_path"]).parent / "strategy-protocol.json"
            )
            protocol_v3 = build_strategy_matrix_protocol(
                registration_id=protocol_v2["registration_id"],
                research_generation=protocol_v2["research_generation"],
                batch_spec=protocol_v2["batch_spec"],
                implementation_manifest=protocol_v2["implementation_manifest"],
                exposure_audit=protocol_v2["holdout_exposure_audit"],
                registration_clock_attestation=protocol_v2["registration_clock_attestation"],
                expires_at_ms=protocol_v2["expires_at_ms"],
                registry_path=protocol_v2["registry_path"],
                protocol_artifact=protocol_artifact,
            )
            self.assertEqual(
                verify_strategy_matrix_protocol(
                    protocol_v3,
                    verify_current_implementation=False,
                )["status"],
                "PASS",
            )
            for protocol in (protocol_v2, protocol_v3):
                forged = deepcopy(protocol)
                forged["correlation_cluster_protocol_registration"] = deepcopy(
                    self.registration
                )
                forged["correlation_cluster_protocol_registration_hash"] = (
                    self.registration["registration_hash"]
                )
                clean = dict(forged)
                clean.pop("protocol_hash")
                forged["protocol_hash"] = canonical_hash(clean)
                verification = verify_strategy_matrix_protocol(
                    forged,
                    verify_current_implementation=False,
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertIn(
                    "matrix_protocol_pre_v4_has_correlation_registration",
                    verification["blockers"],
                )
        finally:
            fixture.tearDown()

    def test_protocol_v4_binds_registration_and_immutable_artifact_but_not_registry(self) -> None:
        fixture = StrategyMatrixProtocolTests("runTest")
        fixture.setUp()
        try:
            store = StrategyMatrixRegistrationStore(
                db_path=fixture.runtime / "strategy_research_registrations.sqlite3",
                now_ms=lambda: 1_000_000,
                canonical_runtime_root=fixture.runtime,
            )
            protocol_v3 = fixture.schema14_protocol(
                store=store,
                registration_id="correlation-v4-fixture",
            )
            batch_spec = deepcopy(protocol_v3["batch_spec"])
            batch_spec["report_schema_version"] = 15
            batch_spec["selection_symbols"] = list(self.preregistration["symbols"])
            first_variant = batch_spec["variants"][0]
            registration = build_strategy_correlation_protocol_registration_v2(
                self.preregistration,
                cutoff_date="2026-03-02",
                selection_alignment_input_hash="a" * 64,
                evaluations=[{
                    "strategy_id": first_variant["strategy_id"],
                    "variant_id": first_variant["variant_id"],
                    "lane": "RAW_EXCESS",
                }],
            )
            artifact_path = fixture.reports / "correlation-v4-protocol.json"
            artifact_binding = build_strategy_research_protocol_artifact_binding(
                artifact_path
            )
            protocol_v4 = build_strategy_matrix_protocol(
                registration_id=protocol_v3["registration_id"],
                research_generation=protocol_v3["research_generation"],
                batch_spec=batch_spec,
                implementation_manifest=protocol_v3["implementation_manifest"],
                exposure_audit=protocol_v3["holdout_exposure_audit"],
                registration_clock_attestation=protocol_v3["registration_clock_attestation"],
                expires_at_ms=protocol_v3["expires_at_ms"],
                registry_path=protocol_v3["registry_path"],
                protocol_artifact=artifact_binding,
                correlation_cluster_protocol_registration=registration,
            )
            protocol_verification = verify_strategy_matrix_protocol(
                protocol_v4,
                verification_at_ms=1_000_000,
                enforce_not_expired=True,
                verify_current_implementation=False,
            )
            self.assertEqual(protocol_v4["schema_version"], STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION)
            self.assertEqual(protocol_verification["status"], "PASS")
            publish_strategy_research_protocol_artifact_no_clobber(
                artifact_path,
                protocol_v4,
            )
            self.assertEqual(
                verify_bound_strategy_research_protocol_artifact(protocol_v4)["status"],
                "PASS",
            )
            gate = {
                "schema_version": "strategy-correlation-replayed-gate-v1",
                "status": "PASS",
                "strategy_id": first_variant["strategy_id"],
                "variant_id": first_variant["variant_id"],
                "lane": "RAW_EXCESS",
                "evaluation_hash": "e" * 64,
                "matrix_replay": {
                    "preregistration": deepcopy(self.preregistration),
                    "completed_price_input": {
                        "cutoff_date": "2026-03-02",
                        "selection_alignment_input_hash": "a" * 64,
                    },
                },
            }
            uncertainty_audit = {
                "status": "PASS",
                "matrix_replay": gate["matrix_replay"],
                "policy_hash": registration["uncertainty_policy_hash"],
            }
            with (
                patch(
                    "exchange_terminal.services.strategy_correlation_protocol_binding."
                    "verify_replayed_correlation_cluster_gate",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch(
                    "exchange_terminal.services.strategy_correlation_protocol_binding."
                    "verify_strategy_correlation_uncertainty_audit",
                    return_value={"status": "PASS", "blockers": []},
                ),
            ):
                assessment = assess_strategy_correlation_protocol_binding(
                    protocol_v4,
                    registration,
                    gate,
                    uncertainty_audit,
                )
            self.assertEqual(assessment["local_chain_status"], "PASS")
            self.assertEqual(assessment["protocol_status"], "PASS")
            self.assertEqual(assessment["protocol_artifact_status"], "PASS")
            self.assertTrue(assessment["protocol_registration_hash_bound"])
            self.assertTrue(assessment["local_uncertainty_audit_bound"])
            self.assertTrue(assessment["immutable_protocol_artifact_bound"])
            self.assertEqual(assessment["status"], "BLOCK")
            self.assertFalse(assessment["formal_registry_bound"])
            self.assertFalse(assessment["current_report_schema_bound"])
            self.assertFalse(assessment["current_writer_activation_allowed"])
            self.assertFalse(assessment["current_admission_allowed"])
            self.assertEqual(
                assessment["next_evidence_required"],
                "PROTOCOL_V4_REGISTRY_TRANSACTION",
            )
            for gate_status in ("BLOCK", "UNKNOWN"):
                blocked_gate = deepcopy(gate)
                blocked_gate["status"] = gate_status
                with (
                    patch(
                        "exchange_terminal.services.strategy_correlation_protocol_binding."
                        "verify_replayed_correlation_cluster_gate",
                        return_value={"status": "PASS", "blockers": []},
                    ),
                    patch(
                        "exchange_terminal.services.strategy_correlation_protocol_binding."
                        "verify_strategy_correlation_uncertainty_audit",
                        return_value={"status": "PASS", "blockers": []},
                    ),
                ):
                    blocked_assessment = assess_strategy_correlation_protocol_binding(
                        protocol_v4,
                        registration,
                        blocked_gate,
                        uncertainty_audit,
                    )
                with self.subTest(gate_status=gate_status):
                    self.assertEqual(blocked_assessment["local_chain_status"], "PASS")
                    self.assertEqual(
                        blocked_assessment["gate_decision_status"],
                        gate_status,
                    )
                    self.assertEqual(
                        blocked_assessment["local_decision_status"],
                        "BLOCK",
                    )
                    self.assertIn(
                        "local_correlation_gate_decision_block",
                        blocked_assessment["blockers"],
                    )
                    self.assertEqual(
                        blocked_assessment["next_evidence_required"],
                        "CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER",
                    )
                    self.assertFalse(blocked_assessment["formal_registry_bound"])
                    self.assertFalse(
                        blocked_assessment["current_writer_activation_allowed"]
                    )
                    self.assertFalse(blocked_assessment["current_admission_allowed"])
                    self.assertFalse(blocked_assessment["paper_authorized"])
                    self.assertFalse(blocked_assessment["live_order_allowed"])
        finally:
            fixture.tearDown()

    def test_registration_v2_binds_uncertainty_policy_and_rejects_reseal(self) -> None:
        verification = verify_strategy_correlation_protocol_registration(self.registration_v2)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            self.registration_v2["uncertainty_policy_hash"],
            self.registration_v2["uncertainty_policy"]["policy_hash"],
        )
        forged = deepcopy(self.registration_v2)
        forged["uncertainty_policy"]["minimum_effective_observations"] = 4.0
        policy_clean = dict(forged["uncertainty_policy"])
        policy_clean.pop("policy_hash")
        forged["uncertainty_policy"]["policy_hash"] = canonical_hash(policy_clean)
        forged["uncertainty_policy_hash"] = forged["uncertainty_policy"]["policy_hash"]
        clean = dict(forged)
        clean.pop("registration_hash")
        forged["registration_hash"] = canonical_hash(clean)
        verification = verify_strategy_correlation_protocol_registration(forged)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(any("uncertainty_policy" in item for item in verification["blockers"]))

    def test_protocol_v4_rejects_legacy_registration_v1(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy_matrix_protocol(
                registration_id="legacy-registration-v1",
                research_generation="NEW_GENERATION",
                batch_spec={"report_schema_version": 15},
                implementation_manifest={"fingerprint": "f" * 64},
                exposure_audit={},
                registration_clock_attestation={"attested_now_ms": 1_000_000},
                expires_at_ms=2_000_000,
                registry_path=Path.cwd() / "registry.sqlite3",
                protocol_artifact={"schema_version": "placeholder"},
                correlation_cluster_protocol_registration=self.registration,
            )

    def test_assessment_v3_requires_matching_uncertainty_matrix_and_policy(self) -> None:
        gate = self._synthetic_gate()
        audit = {
            "status": "PASS",
            "matrix_replay": {"different": True},
            "policy_hash": "b" * 64,
        }
        with (
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_replayed_correlation_cluster_gate",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_strategy_matrix_protocol",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch(
                "exchange_terminal.services.strategy_correlation_protocol_binding."
                "verify_strategy_correlation_uncertainty_audit",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            assessment = assess_strategy_correlation_protocol_binding(
                self._synthetic_protocol(),
                self.registration_v2,
                gate,
                audit,
            )
        self.assertEqual(assessment["local_chain_status"], "BLOCK")
        self.assertFalse(assessment["local_uncertainty_audit_bound"])
        self.assertIn("local_uncertainty_matrix_replay_mismatch", assessment["blockers"])
        self.assertIn("local_uncertainty_policy_mismatch", assessment["blockers"])
        self.assertEqual(
            assessment["next_evidence_required"],
            "VALID_PREREGISTERED_UNCERTAINTY_AUDIT",
        )

import unittest as _decision_unittest

from exchange_terminal.services.strategy_correlation_protocol_binding import (
    _strategy_correlation_decision_disposition,
)


class StrategyCorrelationDecisionDispositionTests(_decision_unittest.TestCase):
    def test_gate_decision_fails_closed_before_registry(self) -> None:
        for gate_status in ("BLOCK", "UNKNOWN", ""):
            with self.subTest(gate_status=gate_status):
                self.assertEqual(
                    _strategy_correlation_decision_disposition(
                        gate_decision_status=gate_status,
                        uncertainty_decision_status="PASS",
                    ),
                    {
                        "status": "BLOCK",
                        "blocker": "local_correlation_gate_decision_block",
                        "next_evidence_required": (
                            "CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER"
                        ),
                    },
                )

        self.assertEqual(
            _strategy_correlation_decision_disposition(
                gate_decision_status="PASS",
                uncertainty_decision_status="BLOCK",
            ),
            {
                "status": "BLOCK",
                "blocker": "local_uncertainty_decision_block",
                "next_evidence_required": (
                    "RESOLVE_CORRELATION_UNCERTAINTY_OR_REREGISTER"
                ),
            },
        )
        for uncertainty_status in ("PASS", "NOT_REQUIRED"):
            with self.subTest(uncertainty_status=uncertainty_status):
                self.assertEqual(
                    _strategy_correlation_decision_disposition(
                        gate_decision_status="PASS",
                        uncertainty_decision_status=uncertainty_status,
                    ),
                    {
                        "status": "PASS",
                        "blocker": None,
                        "next_evidence_required": None,
                    },
                )

if __name__ == "__main__":
    unittest.main()
