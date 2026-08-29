from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_multiplicity_registration as registration,
)
from exchange_terminal.services.strategy_correlation_multiplicity_audit import (
    build_strategy_correlation_multiplicity_policy,
)
from exchange_terminal.services.canonical_json_hash import canonical_hash


class StrategyCorrelationMultiplicityRegistrationTests(unittest.TestCase):
    def _source_registration(
        self,
        cluster_sizes: tuple[int, ...] = (1, 1, 3),
    ) -> dict[str, object]:
        symbols = []
        clusters = []
        cursor = 0
        for cluster_index, size in enumerate(cluster_sizes):
            members = [f"S{cursor + offset}" for offset in range(size)]
            cursor += size
            symbols.extend(members)
            clusters.append({
                "cluster_id": f"cluster_{cluster_index}",
                "members": members,
            })
        return {
            "schema_version": "strategy-correlation-protocol-registration-v2",
            "registration_hash": "a" * 64,
            "preregistration": {
                "schema_version": "strategy-correlation-cluster-preregistration-v1",
                "preregistration_hash": "b" * 64,
                "symbols": symbols,
                "clusters": clusters,
            },
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }

    def _build_verified(self, source: dict[str, object]) -> dict[str, object]:
        with patch.object(
            registration,
            "verify_strategy_correlation_protocol_registration",
            return_value={"status": "PASS", "blockers": []},
        ):
            return (
                registration
                .build_strategy_correlation_multiplicity_family_registration(source)
            )

    def _verify_registration(
        self,
        document: dict[str, object],
    ) -> dict[str, object]:
        with patch.object(
            registration,
            "verify_strategy_correlation_protocol_registration",
            return_value={"status": "PASS", "blockers": []},
        ):
            return (
                registration
                .verify_strategy_correlation_multiplicity_family_registration(
                    document
                )
            )

    def _audit(
        self,
        family_registration: dict[str, object],
        *,
        status: str = "PASS",
    ) -> dict[str, object]:
        source_registration = family_registration["source_protocol_registration"]
        expected = family_registration["family_definition"][
            "expected_cross_cluster_family_size"
        ]
        return {
            "schema_version": "strategy-correlation-multiplicity-audit-v1",
            "status": status,
            "family_size": expected,
            "policy": deepcopy(family_registration["multiplicity_policy"]),
            "policy_hash": family_registration["multiplicity_policy_hash"],
            "source_uncertainty_audit": {
                "matrix_replay": {
                    "preregistration": deepcopy(
                        source_registration["preregistration"]
                    ),
                },
            },
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }

    def _assess(
        self,
        family_registration: dict[str, object],
        multiplicity_audit: dict[str, object],
    ) -> dict[str, object]:
        with (
            patch.object(
                registration,
                "verify_strategy_correlation_protocol_registration",
                return_value={"status": "PASS", "blockers": []},
            ),
            patch.object(
                registration,
                "verify_strategy_correlation_multiplicity_audit",
                return_value={"status": "PASS", "blockers": []},
            ),
        ):
            return registration.assess_strategy_correlation_multiplicity_binding(
                family_registration,
                multiplicity_audit,
            )

    def test_family_size_is_derived_from_partition_before_returns(self) -> None:
        document = self._build_verified(self._source_registration((1, 1, 3)))
        family = document["family_definition"]
        self.assertEqual(document["status"], "PREREGISTERED")
        self.assertEqual(family["cluster_sizes"], [1, 1, 3])
        self.assertEqual(family["symbol_count"], 5)
        self.assertEqual(family["total_pair_count"], 10)
        self.assertEqual(family["within_cluster_pair_count"], 3)
        self.assertEqual(family["expected_cross_cluster_family_size"], 7)
        self.assertEqual(document["input_scope"], "PREREGISTRATION_ONLY")
        self.assertTrue(document["source_before_returns_asserted"])
        self.assertEqual(self._verify_registration(document)["status"], "PASS")

    def test_different_partition_derives_different_registered_family(self) -> None:
        document = self._build_verified(self._source_registration((1, 2, 2)))
        family = document["family_definition"]
        self.assertEqual(family["cluster_sizes"], [1, 2, 2])
        self.assertEqual(family["within_cluster_pair_count"], 2)
        self.assertEqual(family["expected_cross_cluster_family_size"], 8)

    def test_invalid_partition_is_sanitized_without_identity_echo(self) -> None:
        source = self._source_registration()
        source["preregistration"]["clusters"][1]["members"][0] = "S0"
        document = self._build_verified(source)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIsNone(document["source_protocol_registration"])
        self.assertIsNone(document["family_definition"])
        self.assertNotIn("S0", str(document))
        with patch.object(
            registration,
            "verify_strategy_correlation_protocol_registration",
            return_value={"status": "BLOCK", "blockers": ["invalid"]},
        ):
            verification = (
                registration
                .verify_strategy_correlation_multiplicity_family_registration(
                    document
                )
            )
        self.assertEqual(verification["status"], "PASS")

    def test_resealed_family_policy_source_and_authority_tamper_are_blocked(self) -> None:
        baseline = self._build_verified(self._source_registration())
        cases = []
        family = deepcopy(baseline)
        family["family_definition"]["expected_cross_cluster_family_size"] = 8
        cases.append(family)
        policy = deepcopy(baseline)
        policy["multiplicity_policy"]["familywise_confidence_level"] = 0.90
        policy["multiplicity_policy"]["policy_hash"] = canonical_hash({
            key: value
            for key, value in policy["multiplicity_policy"].items()
            if key != "policy_hash"
        })
        policy["multiplicity_policy_hash"] = policy["multiplicity_policy"]["policy_hash"]
        cases.append(policy)
        source = deepcopy(baseline)
        source["source_registration_hash"] = "c" * 64
        cases.append(source)
        authority = deepcopy(baseline)
        authority["permissions"]["paper_authorized"] = True
        cases.append(authority)
        for document in cases:
            document["family_registration_hash"] = canonical_hash({
                key: value
                for key, value in document.items()
                if key != "family_registration_hash"
            })
            with self.subTest(document=document):
                self.assertEqual(
                    self._verify_registration(document)["status"],
                    "BLOCK",
                )

    def test_local_binding_passes_but_requires_new_consumers(self) -> None:
        family_registration = self._build_verified(self._source_registration())
        multiplicity_audit = self._audit(family_registration)
        assessment = self._assess(family_registration, multiplicity_audit)
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertEqual(assessment["local_chain_status"], "PASS")
        self.assertEqual(assessment["local_decision_status"], "PASS")
        self.assertTrue(assessment["preregistration_bound"])
        self.assertTrue(assessment["family_size_bound"])
        self.assertTrue(assessment["policy_bound"])
        self.assertEqual(assessment["expected_family_size"], 7)
        self.assertEqual(assessment["observed_family_size"], 7)
        self.assertEqual(
            assessment["next_evidence_required"],
            "NEW_PROTOCOL_AND_REPORT_CONSUMER",
        )
        self.assertIn(
            "multiplicity_new_protocol_and_report_consumer_required",
            assessment["blockers"],
        )
        for field in (
            "formal_protocol_bound",
            "current_report_schema_bound",
            "current_writer_activation_allowed",
            "current_admission_allowed",
            "parameter_selection_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertIs(assessment[field], False)

    def test_binding_rejects_partition_family_and_policy_drift(self) -> None:
        family_registration = self._build_verified(self._source_registration())
        baseline_audit = self._audit(family_registration)
        cases = []
        partition = deepcopy(baseline_audit)
        partition["source_uncertainty_audit"]["matrix_replay"][
            "preregistration"
        ]["preregistration_hash"] = "d" * 64
        cases.append((
            partition,
            "MATCH_PREREGISTERED_CLUSTER_PARTITION",
            "multiplicity_preregistration_mismatch",
        ))
        family = deepcopy(baseline_audit)
        family["family_size"] = 8
        cases.append((
            family,
            "MATCH_PREREGISTERED_FAMILY_SIZE",
            "multiplicity_family_size_mismatch",
        ))
        policy = deepcopy(baseline_audit)
        policy["policy_hash"] = "e" * 64
        cases.append((
            policy,
            "MATCH_PREREGISTERED_MULTIPLICITY_POLICY",
            "multiplicity_policy_mismatch",
        ))
        for document, next_evidence, blocker in cases:
            with self.subTest(next_evidence=next_evidence):
                assessment = self._assess(family_registration, document)
                self.assertEqual(assessment["local_chain_status"], "BLOCK")
                self.assertEqual(
                    assessment["next_evidence_required"],
                    next_evidence,
                )
                self.assertIn(blocker, assessment["blockers"])

    def test_audit_block_is_monotonic_and_cannot_reach_consumer_step(self) -> None:
        family_registration = self._build_verified(self._source_registration())
        multiplicity_audit = self._audit(family_registration, status="BLOCK")
        assessment = self._assess(family_registration, multiplicity_audit)
        self.assertEqual(assessment["local_chain_status"], "PASS")
        self.assertEqual(assessment["local_decision_status"], "BLOCK")
        self.assertEqual(
            assessment["next_evidence_required"],
            "RESOLVE_MULTIPLICITY_BLOCK_OR_REREGISTER",
        )
        self.assertIn("multiplicity_audit_decision_block", assessment["blockers"])

    def test_binding_assessment_reseal_and_authority_tamper_are_blocked(self) -> None:
        family_registration = self._build_verified(self._source_registration())
        multiplicity_audit = self._audit(family_registration)
        baseline = self._assess(family_registration, multiplicity_audit)
        cases = []
        resealed = deepcopy(baseline)
        resealed["next_evidence_required"] = "CURRENT_WRITER"
        resealed["assessment_hash"] = canonical_hash({
            key: value
            for key, value in resealed.items()
            if key != "assessment_hash"
        })
        cases.append(resealed)
        authority = deepcopy(baseline)
        authority["paper_authorized"] = True
        authority["assessment_hash"] = canonical_hash({
            key: value
            for key, value in authority.items()
            if key != "assessment_hash"
        })
        cases.append(authority)
        for document in cases:
            with (
                patch.object(
                    registration,
                    "verify_strategy_correlation_protocol_registration",
                    return_value={"status": "PASS", "blockers": []},
                ),
                patch.object(
                    registration,
                    "verify_strategy_correlation_multiplicity_audit",
                    return_value={"status": "PASS", "blockers": []},
                ),
            ):
                verification = (
                    registration
                    .verify_strategy_correlation_multiplicity_binding_assessment(
                        document,
                        family_registration=family_registration,
                        multiplicity_audit=multiplicity_audit,
                    )
                )
            self.assertEqual(verification["status"], "BLOCK")
            self.assertFalse(verification["current_writer_activation_allowed"])
            self.assertFalse(verification["current_admission_allowed"])
            self.assertFalse(verification["paper_authorized"])
            self.assertFalse(verification["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
