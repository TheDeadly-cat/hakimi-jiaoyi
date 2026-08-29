from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION,
    TARGET_MATRIX_REPORT_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_multiplicity_protocol_registration,
    verify_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    build_strategy_correlation_multiplicity_family_registration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION,
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
    verify_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    build_strategy_research_protocol_artifact_binding,
)
from tests import test_strategy_matrix_protocol as strategy_matrix_protocol_tests


class StrategyCorrelationMultiplicityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "C1", "members": ["A"]},
            {"cluster_id": "C2", "members": ["B"]},
            {"cluster_id": "C3", "members": ["C", "D", "E"]},
        ])
        self.source_registration = build_strategy_correlation_protocol_registration_v2(
            self.preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="a" * 64,
            evaluations=[{
                "strategy_id": "dual_ma",
                "variant_id": "fixed-v1",
                "lane": "RAW_EXCESS",
            }],
        )
        self.family_registration = (
            build_strategy_correlation_multiplicity_family_registration(
                self.source_registration
            )
        )
        self.registration_v3 = (
            build_strategy_correlation_multiplicity_protocol_registration(
                self.family_registration
            )
        )

    def test_registration_v3_binds_family_policies_and_both_report_targets(self) -> None:
        verification = verify_strategy_correlation_multiplicity_protocol_registration(
            self.registration_v3
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["registration_status"], "PREREGISTERED")
        self.assertEqual(
            self.registration_v3["schema_version"],
            STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(self.registration_v3["target_protocol_schema_version"], TARGET_PROTOCOL_SCHEMA_VERSION)
        self.assertEqual(self.registration_v3["target_report_schema_version"], TARGET_REPORT_SCHEMA_VERSION)
        self.assertEqual(
            self.registration_v3["target_matrix_report_schema_version"],
            TARGET_MATRIX_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.registration_v3["family_definition"]["expected_cross_cluster_family_size"],
            7,
        )
        self.assertTrue(self.registration_v3["source_before_returns_asserted"])
        self.assertFalse(self.registration_v3["formal_registry_bound"])
        self.assertFalse(self.registration_v3["current_admission_allowed"])

    def test_invalid_family_registration_is_sanitized_and_replayable(self) -> None:
        invalid = build_strategy_correlation_multiplicity_protocol_registration({
            "schema_version": "attacker",
            "symbols": ["SECRET"],
        })
        verification = verify_strategy_correlation_multiplicity_protocol_registration(invalid)
        self.assertEqual(invalid["status"], "BLOCK")
        self.assertIsNone(invalid["source_protocol_registration"])
        self.assertIsNone(invalid["family_registration"])
        self.assertNotIn("SECRET", repr(invalid))
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["registration_status"], "BLOCK")

    def test_resealed_target_source_family_and_authority_drift_are_blocked(self) -> None:
        target = deepcopy(self.registration_v3)
        target["target_report_schema_version"] = 15
        source = deepcopy(self.registration_v3)
        source["source_registration_hash"] = "f" * 64
        family = deepcopy(self.registration_v3)
        family["family_definition"]["expected_cross_cluster_family_size"] = 999
        authority = deepcopy(self.registration_v3)
        authority["permissions"]["paper_authorized"] = True
        for document in (target, source, family, authority):
            clean = dict(document)
            clean.pop("registration_hash")
            document["registration_hash"] = canonical_hash(clean)
            with self.subTest(registration_hash=document["registration_hash"]):
                self.assertEqual(
                    verify_strategy_correlation_multiplicity_protocol_registration(document)["status"],
                    "BLOCK",
                )

    def _build_protocol_fixture(self) -> tuple[object, dict, dict, dict]:
        fixture_type = strategy_matrix_protocol_tests.StrategyMatrixProtocolTests
        method = next(name for name in dir(fixture_type) if name.startswith("test_"))
        fixture = fixture_type(method)
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        store = StrategyMatrixRegistrationStore(
            db_path=fixture.runtime / "strategy_research_registrations.sqlite3",
            now_ms=lambda: 1_000_000,
            canonical_runtime_root=fixture.runtime,
        )
        protocol_v3 = fixture.schema14_protocol(
            store=store,
            registration_id="correlation-v5-fixture",
        )
        batch_spec = deepcopy(protocol_v3["batch_spec"])
        batch_spec["selection_symbols"] = list(self.preregistration["symbols"])
        first_variant = batch_spec["variants"][0]
        source_registration = build_strategy_correlation_protocol_registration_v2(
            self.preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="b" * 64,
            evaluations=[{
                "strategy_id": first_variant["strategy_id"],
                "variant_id": first_variant["variant_id"],
                "lane": "RAW_EXCESS",
            }],
        )
        family_registration = build_strategy_correlation_multiplicity_family_registration(
            source_registration
        )
        registration_v3 = build_strategy_correlation_multiplicity_protocol_registration(
            family_registration
        )
        artifact = build_strategy_research_protocol_artifact_binding(
            fixture.reports / "correlation-v5-protocol.json"
        )
        return fixture, protocol_v3, batch_spec, {
            "source": source_registration,
            "registration_v3": registration_v3,
            "artifact": artifact,
        }

    def test_protocol_v5_binds_registration_v3_and_verifies(self) -> None:
        _, base, batch_spec, context = self._build_protocol_fixture()
        batch_spec["report_schema_version"] = TARGET_REPORT_SCHEMA_VERSION
        protocol = build_strategy_matrix_protocol(
            registration_id=base["registration_id"],
            research_generation=base["research_generation"],
            batch_spec=batch_spec,
            implementation_manifest=base["implementation_manifest"],
            exposure_audit=base["holdout_exposure_audit"],
            registration_clock_attestation=base["registration_clock_attestation"],
            expires_at_ms=base["expires_at_ms"],
            registry_path=base["registry_path"],
            protocol_artifact=context["artifact"],
            correlation_multiplicity_protocol_registration=context["registration_v3"],
        )
        verification = verify_strategy_matrix_protocol(
            protocol,
            verification_at_ms=1_000_000,
            enforce_not_expired=True,
            verify_current_implementation=False,
        )
        self.assertEqual(protocol["schema_version"], STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            protocol["correlation_multiplicity_protocol_registration_hash"],
            context["registration_v3"]["registration_hash"],
        )
        self.assertFalse(protocol["paper_authorized"])
        self.assertFalse(protocol["live_order_allowed"])

    def test_protocol_v4_remains_valid_and_rejects_v3_retrofit(self) -> None:
        _, base, batch_spec, context = self._build_protocol_fixture()
        batch_spec["report_schema_version"] = 15
        protocol_v4 = build_strategy_matrix_protocol(
            registration_id=base["registration_id"],
            research_generation=base["research_generation"],
            batch_spec=batch_spec,
            implementation_manifest=base["implementation_manifest"],
            exposure_audit=base["holdout_exposure_audit"],
            registration_clock_attestation=base["registration_clock_attestation"],
            expires_at_ms=base["expires_at_ms"],
            registry_path=base["registry_path"],
            protocol_artifact=context["artifact"],
            correlation_cluster_protocol_registration=context["source"],
        )
        self.assertEqual(protocol_v4["schema_version"], STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION)
        self.assertEqual(
            verify_strategy_matrix_protocol(protocol_v4, verify_current_implementation=False)["status"],
            "PASS",
        )
        forged = deepcopy(protocol_v4)
        forged["correlation_multiplicity_protocol_registration"] = deepcopy(context["registration_v3"])
        forged["correlation_multiplicity_protocol_registration_hash"] = context["registration_v3"]["registration_hash"]
        clean = dict(forged)
        clean.pop("protocol_hash")
        forged["protocol_hash"] = canonical_hash(clean)
        verification = verify_strategy_matrix_protocol(forged, verify_current_implementation=False)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("matrix_protocol_pre_v5_has_multiplicity_registration", verification["blockers"])

    def test_protocol_v5_rejects_wrong_report_conflict_and_coherent_reseal(self) -> None:
        _, base, batch_spec, context = self._build_protocol_fixture()
        batch_spec["report_schema_version"] = 15
        kwargs = {
            "registration_id": base["registration_id"],
            "research_generation": base["research_generation"],
            "batch_spec": batch_spec,
            "implementation_manifest": base["implementation_manifest"],
            "exposure_audit": base["holdout_exposure_audit"],
            "registration_clock_attestation": base["registration_clock_attestation"],
            "expires_at_ms": base["expires_at_ms"],
            "registry_path": Path(base["registry_path"]),
            "protocol_artifact": context["artifact"],
        }
        with self.assertRaises(ValueError):
            build_strategy_matrix_protocol(
                **kwargs,
                correlation_multiplicity_protocol_registration=context["registration_v3"],
            )
        batch_spec["report_schema_version"] = TARGET_REPORT_SCHEMA_VERSION
        with self.assertRaises(ValueError):
            build_strategy_matrix_protocol(
                **kwargs,
                correlation_cluster_protocol_registration=context["source"],
                correlation_multiplicity_protocol_registration=context["registration_v3"],
            )
        protocol = build_strategy_matrix_protocol(
            **kwargs,
            correlation_multiplicity_protocol_registration=context["registration_v3"],
        )
        forged = deepcopy(protocol)
        embedded = forged["correlation_multiplicity_protocol_registration"]
        embedded["target_matrix_report_schema_version"] = 7
        registration_clean = dict(embedded)
        registration_clean.pop("registration_hash")
        embedded["registration_hash"] = canonical_hash(registration_clean)
        forged["correlation_multiplicity_protocol_registration_hash"] = embedded["registration_hash"]
        protocol_clean = dict(forged)
        protocol_clean.pop("protocol_hash")
        forged["protocol_hash"] = canonical_hash(protocol_clean)
        verification = verify_strategy_matrix_protocol(forged, verify_current_implementation=False)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(any("multiplicity_registration" in item for item in verification["blockers"]))
