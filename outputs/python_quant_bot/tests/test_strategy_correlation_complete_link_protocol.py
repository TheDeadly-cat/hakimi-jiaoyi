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
    verify_strategy_correlation_complete_link_protocol_registration,
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


class StrategyCorrelationCompleteLinkProtocolTests(unittest.TestCase):
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
    def _source_registration(cls) -> dict:
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
        return build_strategy_correlation_multiplicity_protocol_registration(family)

    @classmethod
    def _reseal_policy_and_registration(cls, document: dict) -> dict:
        policy = document["complete_link_policy"]
        policy_payload = {
            key: value for key, value in policy.items() if key != "policy_hash"
        }
        policy["policy_hash"] = cls._hash(policy_payload)
        document["complete_link_policy_hash"] = policy["policy_hash"]
        payload = {
            key: value for key, value in document.items() if key != "registration_hash"
        }
        document["registration_hash"] = cls._hash(payload)
        return document

    def test_registration_binds_protocol_v6_without_writer_authority(self) -> None:
        registration = build_strategy_correlation_complete_link_protocol_registration(
            self._source_registration()
        )
        verification = verify_strategy_correlation_complete_link_protocol_registration(
            registration
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            registration["schema_version"],
            "strategy-correlation-protocol-registration-v4",
        )
        self.assertEqual(
            registration["target_protocol_schema_version"],
            "strategy-matrix-protocol-v6",
        )
        self.assertEqual(registration["target_report_schema_version"], 17)
        self.assertTrue(registration["schema17_consumer_available"])
        self.assertFalse(registration["formal_registry_bound"])
        self.assertFalse(registration["writer_available"])
        self.assertFalse(registration["current_admission_allowed"])
        self.assertFalse(registration["current_writer_activation_allowed"])
        self.assertFalse(registration["permissions"]["paper_authorized"])
        self.assertFalse(registration["permissions"]["live_order_allowed"])

    def test_policy_freezes_complete_link_threshold_and_migration_prerequisites(self) -> None:
        registration = build_strategy_correlation_complete_link_protocol_registration(
            self._source_registration()
        )
        policy = registration["complete_link_policy"]

        self.assertEqual(policy["absolute_pearson_threshold"], 0.75)
        self.assertEqual(policy["minimum_pair_overlap"], 40)
        self.assertEqual(
            policy["topology_rule"],
            "ALL_INTERNAL_PAIRS_MEET_ABSOLUTE_PEARSON_THRESHOLD",
        )
        self.assertEqual(
            policy["writer_activation_prerequisites"],
            [
                "INDEPENDENT_SCHEMA16_VERIFICATION",
                "BASE_REPORT_HASH_BINDING",
                "COMPLETE_LINK_GATE_V2_REBUILD",
                "PROTOCOL_V6_FORMAL_REGISTRY",
                "SCHEMA17_SOLE_WRITER_MIGRATION_TESTS",
            ],
        )

    def test_coherently_resealed_threshold_tamper_is_rejected(self) -> None:
        registration = build_strategy_correlation_complete_link_protocol_registration(
            self._source_registration()
        )
        tampered = copy.deepcopy(registration)
        tampered["complete_link_policy"]["absolute_pearson_threshold"] = 0.70
        tampered = self._reseal_policy_and_registration(tampered)

        verification = verify_strategy_correlation_complete_link_protocol_registration(
            tampered
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_source_hash_drift_is_rejected(self) -> None:
        registration = build_strategy_correlation_complete_link_protocol_registration(
            self._source_registration()
        )
        tampered = copy.deepcopy(registration)
        tampered["source_registration_hash"] = "b" * 64
        tampered = self._reseal_policy_and_registration(tampered)

        verification = verify_strategy_correlation_complete_link_protocol_registration(
            tampered
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_authority_alias_is_rejected_even_when_resealed(self) -> None:
        registration = build_strategy_correlation_complete_link_protocol_registration(
            self._source_registration()
        )
        tampered = copy.deepcopy(registration)
        tampered["live"] = True
        tampered = self._reseal_policy_and_registration(tampered)

        verification = verify_strategy_correlation_complete_link_protocol_registration(
            tampered
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_legacy_v2_source_cannot_skip_multiplicity_registration(self) -> None:
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
        with self.assertRaisesRegex(
            ValueError,
            "complete_link_source_protocol_registration_invalid",
        ):
            build_strategy_correlation_complete_link_protocol_registration(source_v2)


if __name__ == "__main__":
    unittest.main()
