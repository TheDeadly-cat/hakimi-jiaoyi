from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_audit as uncertainty_module
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_cluster_gate_v1
    as cluster_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class StrategyCorrelationUncertaintyMultiWindowObservationOverlapGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        replay_verifier = patch.object(
            uncertainty_module,
            "verify_correlation_matrix_replay",
            return_value={"status": "PASS", "blockers": []},
        )
        replay_verifier.start()
        self.addCleanup(replay_verifier.stop)

    @staticmethod
    def _clusters() -> list[dict[str, object]]:
        return [
            {"cluster_id": "a", "members": ["A"]},
            {"cluster_id": "b", "members": ["B"]},
        ]

    def _low_audit(self, left_seed: int, right_seed: int) -> dict[str, object]:
        series = {
            "A": cluster_fixtures.FixtureCase._normal(left_seed),
            "B": cluster_fixtures.FixtureCase._normal(right_seed),
        }
        replay = cluster_fixtures.FixtureCase._replay(series, self._clusters())
        return uncertainty_module.build_strategy_correlation_uncertainty_audit(
            replay
        )

    def _high_audit(self, seed: int) -> dict[str, object]:
        base = cluster_fixtures.FixtureCase._normal(seed)
        series = {
            "A": base,
            "B": cluster_fixtures.FixtureCase._correlated(
                base,
                0.98,
                seed + 100,
            ),
        }
        replay = cluster_fixtures.FixtureCase._replay(series, self._clusters())
        return uncertainty_module.build_strategy_correlation_uncertainty_audit(
            replay
        )

    @staticmethod
    def _range_ids(start: int, count: int) -> list[str]:
        return [f"obs-{index:06d}" for index in range(start, start + count)]

    @staticmethod
    def _audit_count(audit: dict[str, object]) -> int:
        pairs = audit["pairs"]
        return int(pairs[0]["overlap_observations"])

    def _upstream(
        self,
        audits: list[dict[str, object]],
    ) -> dict[str, object]:
        windows = [f"window-{index:02d}" for index in range(1, len(audits) + 1)]
        preregistration = cluster_gate.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            ["A", "B"],
            self._clusters(),
            windows,
        )
        self.assertIsNotNone(preregistration)
        inputs = [
            {"window_id": window_id, "uncertainty_audit": audit}
            for window_id, audit in zip(windows, audits, strict=True)
        ]
        hashes = [str(audit["audit_hash"]) for audit in audits]
        gate = cluster_gate.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            preregistration,
            inputs,
            expected_preregistration_hash=preregistration["preregistration_hash"],
            expected_window_audit_hashes=hashes,
        )
        self.assertIsNotNone(gate)
        return {
            "windows": windows,
            "preregistration": preregistration,
            "inputs": inputs,
            "hashes": hashes,
            "gate": gate,
        }

    def _context(
        self,
        audits: list[dict[str, object]],
        observation_sets: list[list[str]],
    ) -> dict[str, object]:
        upstream = self._upstream(audits)
        preregistration = subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_preregistration_v1(
            upstream["preregistration"],
            study_identity_hash=_hash("study-identity"),
            observation_identifier_scheme_hash=_hash(
                "ascending-synthetic-observation-id-v1"
            ),
            registration_sequence=1,
        )
        self.assertIsNotNone(preregistration)
        rows = []
        for index, (window_id, audit, observation_ids) in enumerate(
            zip(
                upstream["windows"],
                audits,
                observation_sets,
                strict=True,
            ),
            start=1,
        ):
            rows.append(
                {
                    "common_observation_membership_gate_v2_hash": _hash(
                        f"membership-gate-{index}"
                    ),
                    "common_observation_membership_hash": strict_canonical_hash(
                        observation_ids
                    ),
                    "common_price_date_grid_hash": _hash(
                        f"price-date-grid-{index}"
                    ),
                    "common_sample_count": len(observation_ids),
                    "date_grid_audit_hash": _hash(f"date-grid-audit-{index}"),
                    "observation_ids": list(observation_ids),
                    "uncertainty_audit_hash": audit["audit_hash"],
                    "window_id": window_id,
                }
            )
        evidence = subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
            preregistration,
            rows,
            evidence_sequence=2,
        )
        self.assertIsNotNone(evidence)
        return {
            **upstream,
            "overlap_preregistration": preregistration,
            "evidence": evidence,
        }

    def _evaluate(self, context: dict[str, object]) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
            context["overlap_preregistration"],
            context["evidence"],
            context["gate"],
            context["preregistration"],
            context["inputs"],
            expected_preregistration_hash=context["overlap_preregistration"][
                "preregistration_hash"
            ],
            expected_evidence_hash=context["evidence"]["evidence_hash"],
            expected_multi_window_gate_hash=context["gate"]["gate_hash"],
            expected_multi_window_preregistration_hash=context[
                "preregistration"
            ]["preregistration_hash"],
            expected_window_audit_hashes=context["hashes"],
        )
        self.assertIsInstance(result, dict)
        return result

    def _two_low_audits(self) -> list[dict[str, object]]:
        return [self._low_audit(1, 2), self._low_audit(3, 4)]

    def test_disjoint_memberships_pass_research_veto(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )

        gate = self._evaluate(context)

        self.assertEqual(context["gate"]["status"], "PASS")
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["gate_blockers"], [])
        self.assertEqual(
            gate["summary"][
                "maximum_observed_pairwise_jaccard_overlap_bps_ceiling"
            ],
            0,
        )

    def test_distinct_audit_hashes_with_duplicate_membership_are_blocked(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        observation_ids = self._range_ids(0, count)
        context = self._context(
            audits,
            [observation_ids, list(observation_ids)],
        )

        gate = self._evaluate(context)

        self.assertEqual(context["gate"]["status"], "PASS")
        self.assertEqual(len(set(context["hashes"])), 2)
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["reason_code"], "BLOCK_PSEUDO_MULTI_WINDOW_EVIDENCE")
        self.assertTrue(gate["facts"]["pseudo_multi_window_evidence_present"])
        self.assertEqual(gate["summary"]["exact_duplicate_pair_count"], 1)

    def test_high_pairwise_jaccard_overlap_blocks_with_ceiling_rounding(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        shift = max(1, count // 4)
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(shift, count)],
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "BLOCK")
        pair = gate["pairwise_overlap_assessments"][0]
        self.assertGreater(
            pair["jaccard_overlap_bps_ceiling"],
            subject.MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS,
        )
        self.assertTrue(pair["overlap_exceeds_maximum"])
        self.assertEqual(subject._overlap_bps_ceiling(1, 3), 3334)

    def test_three_window_union_coverage_blocks_zero_unique_contribution(self) -> None:
        audits = [
            self._low_audit(1, 2),
            self._low_audit(3, 4),
            self._low_audit(5, 6),
        ]
        count = self._audit_count(audits[0])
        half = count // 2
        context = self._context(
            audits,
            [
                self._range_ids(0, count),
                self._range_ids(half, count),
                self._range_ids(count, count),
            ],
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "BLOCK")
        middle = gate["window_assessments"][1]
        self.assertEqual(middle["unique_observation_count"], 0)
        self.assertTrue(middle["unique_contribution_below_minimum"])
        self.assertTrue(
            all(
                pair["jaccard_overlap_bps_ceiling"]
                <= subject.MAXIMUM_PAIRWISE_JACCARD_OVERLAP_BPS
                for pair in gate["pairwise_overlap_assessments"]
            )
        )

    def test_observation_count_must_match_each_verified_uncertainty_audit(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count - 1), self._range_ids(count, count)],
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["WINDOW_MEMBERSHIP_TO_AUDIT_BINDING_FAILED"],
        )

    def test_reordered_window_evidence_cannot_be_built(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        rows = list(reversed(context["evidence"]["window_observations"]))

        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
                context["overlap_preregistration"],
                rows,
                evidence_sequence=3,
            )
        )

    def test_duplicate_or_unsorted_observation_ids_cannot_be_built(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        rows = deepcopy(context["evidence"]["window_observations"])
        rows[0]["observation_ids"] = ["obs-000002", "obs-000001"]
        rows[0]["common_sample_count"] = 2
        rows[0]["common_observation_membership_hash"] = strict_canonical_hash(
            rows[0]["observation_ids"]
        )
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
                context["overlap_preregistration"],
                rows,
                evidence_sequence=3,
            )
        )
        rows[0]["observation_ids"] = ["obs-000001", "obs-000001"]
        rows[0]["common_observation_membership_hash"] = strict_canonical_hash(
            rows[0]["observation_ids"]
        )
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
                context["overlap_preregistration"],
                rows,
                evidence_sequence=3,
            )
        )

    def test_resealed_membership_tamper_fails_closed_unknown(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        forged = deepcopy(context["evidence"])
        forged["window_observations"][0]["observation_ids"][0] = "obs-999999"
        unsigned = deepcopy(forged)
        unsigned.pop("evidence_hash")
        forged = seal_strict_canonical_document(unsigned, "evidence_hash")
        context["evidence"] = forged

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["OVERLAP_PREREGISTRATION_OR_EVIDENCE_INVALID"],
        )

    def test_uncertainty_audit_hash_splice_fails_closed_unknown(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        forged = deepcopy(context["evidence"])
        forged["window_observations"][0]["uncertainty_audit_hash"] = _hash(
            "spliced-audit"
        )
        unsigned = deepcopy(forged)
        unsigned.pop("evidence_hash")
        forged = seal_strict_canonical_document(unsigned, "evidence_hash")
        context["evidence"] = forged
        context["evidence"]["evidence_hash"] = forged["evidence_hash"]

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["WINDOW_MEMBERSHIP_TO_AUDIT_BINDING_FAILED"],
        )

    def test_upstream_cluster_gate_block_is_preserved(self) -> None:
        audits = [self._low_audit(1, 2), self._high_audit(3)]
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )

        gate = self._evaluate(context)

        self.assertEqual(context["gate"]["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertIn(
            "UPSTREAM_MULTI_WINDOW_CLUSTER_GATE_BLOCKED",
            gate["gate_blockers"],
        )

    def test_reused_source_receipt_hash_blocks(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        rows = deepcopy(context["evidence"]["window_observations"])
        rows[1]["date_grid_audit_hash"] = rows[0]["date_grid_audit_hash"]
        evidence = subject.build_strategy_correlation_uncertainty_multi_window_observation_overlap_evidence_v1(
            context["overlap_preregistration"],
            rows,
            evidence_sequence=3,
        )
        self.assertIsNotNone(evidence)
        context["evidence"] = evidence

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "BLOCK")
        self.assertIn("DATE_GRID_AUDIT_HASH_REUSED", gate["gate_blockers"])

    def test_forged_upstream_gate_fails_exact_rebuild(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        forged = deepcopy(context["gate"])
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")
        context["gate"] = forged

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0345_GATE_EXACT_REBUILD_FAILED"],
        )

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )
        gate = self._evaluate(context)
        verification_arguments = {
            "expected_gate_hash": gate["gate_hash"],
            "expected_preregistration_hash": context["overlap_preregistration"][
                "preregistration_hash"
            ],
            "expected_evidence_hash": context["evidence"]["evidence_hash"],
            "expected_multi_window_gate_hash": context["gate"]["gate_hash"],
            "expected_multi_window_preregistration_hash": context[
                "preregistration"
            ]["preregistration_hash"],
            "expected_window_audit_hashes": context["hashes"],
        }
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
                gate,
                context["overlap_preregistration"],
                context["evidence"],
                context["gate"],
                context["preregistration"],
                context["inputs"],
                **verification_arguments,
            )
        )
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")
        verification_arguments["expected_gate_hash"] = forged["gate_hash"]
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
                forged,
                context["overlap_preregistration"],
                context["evidence"],
                context["gate"],
                context["preregistration"],
                context["inputs"],
                **verification_arguments,
            )
        )

    def test_gate_output_excludes_raw_ids_and_preserves_all_authority_locks(self) -> None:
        audits = self._two_low_audits()
        count = self._audit_count(audits[0])
        context = self._context(
            audits,
            [self._range_ids(0, count), self._range_ids(count, count)],
        )

        gate = self._evaluate(context)
        serialized = json.dumps(gate, sort_keys=True)

        self.assertNotIn('"observation_ids":', serialized)
        self.assertNotIn(
            context["evidence"]["window_observations"][0]["observation_ids"][0],
            serialized,
        )
        self.assertNotIn('"uncertainty_audit":', serialized)
        self.assertFalse(gate["facts"]["independence_units_claimed"])
        self.assertFalse(gate["facts"]["membership_issuer_exactly_verified"])
        self.assertTrue(
            all(
                value is False
                for key, value in gate["authority"].items()
                if key != "research_evidence_only"
            )
        )

    def test_upstream_source_pin_matches_reviewed_adr0345_implementation(self) -> None:
        source_path = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "services"
            / "strategy_correlation_uncertainty_multi_window_cluster_gate_v1.py"
        )
        self.assertEqual(
            sha256(source_path.read_bytes()).hexdigest(),
            subject.MULTI_WINDOW_GATE_V1_IMPLEMENTATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
