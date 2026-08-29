from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    build_strategy_correlation_multiplicity_family_registration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_CLAIM_VERSION_V2,
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    build_strategy_research_protocol_artifact_binding,
    publish_strategy_research_protocol_artifact_no_clobber,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
)
from tests import test_strategy_correlation_multiplicity_protocol as protocol_tests


class StrategyCorrelationMultiplicityRegistryTests(unittest.TestCase):
    def _fixture(self):
        source_case = protocol_tests.StrategyCorrelationMultiplicityProtocolTests(
            "test_protocol_v5_binds_registration_v3_and_verifies"
        )
        source_case.setUp()
        fixture, base, batch_spec, context = source_case._build_protocol_fixture()
        self.addCleanup(source_case.doCleanups)
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
        artifact_path = fixture.reports / "correlation-v5-protocol.json"
        publish_strategy_research_protocol_artifact_no_clobber(
            artifact_path,
            protocol,
        )
        store = StrategyMatrixRegistrationStore(
            db_path=base["registry_path"],
            now_ms=lambda: 1_000_000,
            canonical_runtime_root=fixture.runtime,
        )
        return source_case, fixture, base, context, protocol, store

    def test_v5_register_claim_complete_and_audit_share_existing_state_machine(self) -> None:
        _, _, base, _, protocol, store = self._fixture()
        registration = store.register(protocol)
        claim = store.claim(
            base["registration_id"],
            clock_attestation=base["registration_clock_attestation"],
            exposure_audit=base["holdout_exposure_audit"],
        )
        completion = store.complete(
            base["registration_id"],
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            clock_attestation=base["registration_clock_attestation"],
        )
        audit = store.audit()
        state = store.get(base["registration_id"])

        self.assertEqual(registration["status"], "REGISTERED")
        self.assertEqual(claim["status"], "CLAIMED")
        self.assertEqual(claim["claim"]["schema_version"], STRATEGY_MATRIX_CLAIM_VERSION_V2)
        self.assertIn("search_lineage_registry_anchor", claim["claim"])
        self.assertEqual(completion["status"], "COMPLETED")
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["event_count"], 3)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertFalse(claim["paper_authorized"])
        self.assertFalse(completion["live_order_allowed"])

    def test_v5_claim_and_completion_remain_single_use(self) -> None:
        _, _, base, _, protocol, store = self._fixture()
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        self.assertEqual(
            store.claim(
                base["registration_id"],
                clock_attestation=base["registration_clock_attestation"],
                exposure_audit=base["holdout_exposure_audit"],
            )["status"],
            "CLAIMED",
        )
        second_claim = store.claim(
            base["registration_id"],
            clock_attestation=base["registration_clock_attestation"],
            exposure_audit=base["holdout_exposure_audit"],
        )
        self.assertEqual(second_claim["status"], "BLOCK")
        self.assertTrue(any("already_consumed" in item for item in second_claim["blockers"]))
        self.assertEqual(
            store.complete(
                base["registration_id"],
                result_hash="d" * 64,
                dataset_manifest_hash="e" * 64,
                clock_attestation=base["registration_clock_attestation"],
            )["status"],
            "COMPLETED",
        )
        second_completion = store.complete(
            base["registration_id"],
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            clock_attestation=base["registration_clock_attestation"],
        )
        self.assertEqual(second_completion["status"], "BLOCK")
        self.assertIn("matrix_registration_not_running", second_completion["blockers"])
        self.assertEqual(store.audit()["status"], "PASS")

    def test_v4_remains_dormant_at_registry_boundary(self) -> None:
        _, fixture, base, context, _, store = self._fixture()
        batch_spec = deepcopy(base["batch_spec"])
        batch_spec["report_schema_version"] = 15
        artifact_path = fixture.reports / "correlation-v4-registry-block.json"
        protocol_v4 = build_strategy_matrix_protocol(
            registration_id="correlation-v4-registry-block",
            research_generation=base["research_generation"],
            batch_spec=batch_spec,
            implementation_manifest=base["implementation_manifest"],
            exposure_audit=base["holdout_exposure_audit"],
            registration_clock_attestation=base["registration_clock_attestation"],
            expires_at_ms=base["expires_at_ms"],
            registry_path=base["registry_path"],
            protocol_artifact=build_strategy_research_protocol_artifact_binding(
                artifact_path
            ),
            correlation_cluster_protocol_registration=context["source"],
        )
        publish_strategy_research_protocol_artifact_no_clobber(
            artifact_path,
            protocol_v4,
        )
        registration = store.register(protocol_v4)
        self.assertEqual(registration["status"], "BLOCK")
        self.assertIn("matrix_protocol_artifact:matrix_protocol_artifact_binding_required", registration["blockers"])
        self.assertEqual(store.audit()["event_count"], 0)

    def test_resealed_v3_target_drift_blocks_before_registry_event(self) -> None:
        _, fixture, base, _, protocol, store = self._fixture()
        forged = deepcopy(protocol)
        registration = forged["correlation_multiplicity_protocol_registration"]
        registration["target_matrix_report_schema_version"] = 7
        registration_clean = dict(registration)
        registration_clean.pop("registration_hash")
        registration["registration_hash"] = canonical_hash(registration_clean)
        forged["correlation_multiplicity_protocol_registration_hash"] = registration[
            "registration_hash"
        ]
        protocol_clean = dict(forged)
        protocol_clean.pop("protocol_hash")
        forged["protocol_hash"] = canonical_hash(protocol_clean)
        artifact_path = fixture.reports / "correlation-v5-forged.json"
        forged["protocol_artifact"] = build_strategy_research_protocol_artifact_binding(
            artifact_path
        )
        protocol_clean = dict(forged)
        protocol_clean.pop("protocol_hash")
        forged["protocol_hash"] = canonical_hash(protocol_clean)
        publish_strategy_research_protocol_artifact_no_clobber(
            artifact_path,
            forged,
        )
        registration_result = store.register(forged)
        self.assertEqual(registration_result["status"], "BLOCK")
        self.assertEqual(store.audit()["event_count"], 0)

    def test_second_v5_registration_replays_schema16_lineage(self) -> None:
        _, fixture, base, context, protocol, store = self._fixture()
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        second_base = fixture.schema14_protocol(
            store=store,
            registration_id="correlation-v5-second",
        )
        second_batch = deepcopy(second_base["batch_spec"])
        self.assertEqual(
            second_batch["search_lineage"]["schema_version"],
            STRATEGY_RESEARCH_SEARCH_LINEAGE_SCHEMA_VERSION_V2,
        )
        second_batch["report_schema_version"] = TARGET_REPORT_SCHEMA_VERSION
        source_preregistration = context["source"]["preregistration"]
        second_batch["selection_symbols"] = list(
            source_preregistration["symbols"]
        )
        variant = second_batch["variants"][0]
        source = build_strategy_correlation_protocol_registration_v2(
            source_preregistration,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="c" * 64,
            evaluations=[{
                "strategy_id": variant["strategy_id"],
                "variant_id": variant["variant_id"],
                "lane": "RAW_EXCESS",
            }],
        )
        family = build_strategy_correlation_multiplicity_family_registration(source)
        registration_v3 = build_strategy_correlation_multiplicity_protocol_registration(
            family
        )
        artifact_path = (
            fixture.reports / "correlation-v5-second-multiplicity.json"
        )
        second_protocol = build_strategy_matrix_protocol(
            registration_id=second_base["registration_id"],
            research_generation=second_base["research_generation"],
            batch_spec=second_batch,
            implementation_manifest=second_base["implementation_manifest"],
            exposure_audit=second_base["holdout_exposure_audit"],
            registration_clock_attestation=second_base["registration_clock_attestation"],
            expires_at_ms=second_base["expires_at_ms"],
            registry_path=second_base["registry_path"],
            protocol_artifact=build_strategy_research_protocol_artifact_binding(
                artifact_path
            ),
            correlation_multiplicity_protocol_registration=registration_v3,
        )
        publish_strategy_research_protocol_artifact_no_clobber(
            artifact_path,
            second_protocol,
        )
        second_registration = store.register(second_protocol)
        self.assertEqual(second_registration["status"], "REGISTERED")
        self.assertEqual(store.audit()["status"], "PASS")
        self.assertEqual(store.audit()["event_count"], 2)
