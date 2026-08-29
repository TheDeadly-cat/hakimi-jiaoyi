from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
)
from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    build_strategy_correlation_complete_link_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_complete_link_registry_binding import (
    assess_strategy_correlation_complete_link_registry_binding,
    verify_strategy_correlation_complete_link_registry_binding,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    build_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_registration import (
    build_strategy_correlation_multiplicity_family_registration,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    build_strategy_correlation_protocol_registration_v2,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_registry_anchor,
    build_strategy_research_search_lineage_v2,
)


class StrategyCorrelationCompleteLinkRegistryBindingTests(unittest.TestCase):
    REGISTRATION_ID = "complete-link-v6-001"
    RUNTIME_ROOT = "C:/isolated-runtime"
    REGISTRY_PATH = "C:/isolated-runtime/registry.json"
    REGISTRY_ASSET_HASH = "d" * 64

    @staticmethod
    def _hash(value: object) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def _registration(cls) -> dict:
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "AB", "members": ["A", "B"]},
                {"cluster_id": "C", "members": ["C"]},
            ]
        )
        source_v2 = build_strategy_correlation_protocol_registration_v2(
            preregistration,
            cutoff_date="2026-01-01",
            selection_alignment_input_hash="a" * 64,
            evaluations=[
                {"strategy_id": "S", "variant_id": "V", "lane": "RAW_EXCESS"}
            ],
        )
        family = build_strategy_correlation_multiplicity_family_registration(
            source_v2
        )
        source_v3 = build_strategy_correlation_multiplicity_protocol_registration(
            family
        )
        return build_strategy_correlation_complete_link_protocol_registration(
            source_v3
        )

    @classmethod
    def _sources(cls) -> tuple[dict, dict, dict]:
        registration = cls._registration()
        lineage = build_strategy_research_search_lineage_v2(
            search_family_id="complete-link-v6",
            prior_registrations=[],
            current_trial_count=1,
        )
        anchor = build_strategy_research_registry_anchor(
            registration_id=cls.REGISTRATION_ID,
            protocol_hash=registration["registration_hash"],
            registered_event_hash="b" * 64,
            registry_audit_tail_event_hash="c" * 64,
            active_runtime_root=cls.RUNTIME_ROOT,
            canonical_registry_path=cls.REGISTRY_PATH,
            search_lineage=lineage,
        )
        return registration, lineage, anchor

    @classmethod
    def _assess(cls, registration: dict, lineage: dict, anchor: dict) -> dict:
        return assess_strategy_correlation_complete_link_registry_binding(
            registration,
            anchor,
            lineage,
            expected_registration_id=cls.REGISTRATION_ID,
            expected_active_runtime_root=cls.RUNTIME_ROOT,
            expected_canonical_registry_path=cls.REGISTRY_PATH,
            expected_registry_asset_hash=cls.REGISTRY_ASSET_HASH,
        )

    def test_binding_verifies_anchor_and_external_fingerprint_without_writer(self) -> None:
        registration, lineage, anchor = self._sources()
        assessment = self._assess(registration, lineage, anchor)
        verification = verify_strategy_correlation_complete_link_registry_binding(
            assessment,
            registration=registration,
            registry_anchor=anchor,
            search_lineage=lineage,
            expected_registration_id=self.REGISTRATION_ID,
            expected_active_runtime_root=self.RUNTIME_ROOT,
            expected_canonical_registry_path=self.REGISTRY_PATH,
            expected_registry_asset_hash=self.REGISTRY_ASSET_HASH,
        )

        self.assertEqual(assessment["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(assessment["registry_anchor_contract_verified"])
        self.assertTrue(assessment["registry_asset_fingerprint_bound"])
        self.assertFalse(assessment["external_registry_asset_read_performed_by_assessor"])
        self.assertFalse(assessment["writer_available"])
        self.assertFalse(assessment["writer_activation_allowed"])
        self.assertFalse(assessment["current_admission_allowed"])
        self.assertFalse(assessment["permissions"]["paper_authorized"])
        self.assertFalse(assessment["permissions"]["live_order_allowed"])

    def test_protocol_hash_mismatch_blocks_anchor_binding(self) -> None:
        registration, lineage, anchor = self._sources()
        tampered_anchor = copy.deepcopy(anchor)
        tampered_anchor["protocol_hash"] = "e" * 64

        assessment = self._assess(registration, lineage, tampered_anchor)
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn("strategy_registry_anchor_invalid", assessment["blockers"])

    def test_runtime_or_registry_path_drift_blocks_binding(self) -> None:
        registration, lineage, anchor = self._sources()
        for field, value in (
            ("active_runtime_root", "C:/other-runtime"),
            ("canonical_registry_path", "C:/other-runtime/registry.json"),
        ):
            tampered_anchor = copy.deepcopy(anchor)
            tampered_anchor[field] = value
            with self.subTest(field=field):
                assessment = self._assess(registration, lineage, tampered_anchor)
                self.assertEqual(assessment["status"], "BLOCK")

    def test_lineage_drift_blocks_binding(self) -> None:
        registration, lineage, anchor = self._sources()
        tampered_lineage = copy.deepcopy(lineage)
        tampered_lineage["current_trial_count"] = 2

        assessment = self._assess(registration, tampered_lineage, anchor)
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn("strategy_search_lineage_v2_invalid", assessment["blockers"])

    def test_expected_registry_asset_hash_drift_breaks_exact_verification(self) -> None:
        registration, lineage, anchor = self._sources()
        assessment = self._assess(registration, lineage, anchor)

        verification = verify_strategy_correlation_complete_link_registry_binding(
            assessment,
            registration=registration,
            registry_anchor=anchor,
            search_lineage=lineage,
            expected_registration_id=self.REGISTRATION_ID,
            expected_active_runtime_root=self.RUNTIME_ROOT,
            expected_canonical_registry_path=self.REGISTRY_PATH,
            expected_registry_asset_hash="e" * 64,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_authority_alias_is_rejected(self) -> None:
        registration, lineage, anchor = self._sources()
        assessment = self._assess(registration, lineage, anchor)
        tampered = copy.deepcopy(assessment)
        tampered["paper"] = True
        payload = {
            key: value for key, value in tampered.items() if key != "assessment_hash"
        }
        tampered["assessment_hash"] = self._hash(payload)

        verification = verify_strategy_correlation_complete_link_registry_binding(
            tampered,
            registration=registration,
            registry_anchor=anchor,
            search_lineage=lineage,
            expected_registration_id=self.REGISTRATION_ID,
            expected_active_runtime_root=self.RUNTIME_ROOT,
            expected_canonical_registry_path=self.REGISTRY_PATH,
            expected_registry_asset_hash=self.REGISTRY_ASSET_HASH,
        )
        self.assertEqual(verification["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
