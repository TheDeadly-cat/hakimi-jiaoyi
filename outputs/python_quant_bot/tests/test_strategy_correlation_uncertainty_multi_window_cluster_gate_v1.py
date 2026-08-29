from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_audit as uncertainty_module
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as subject,
)
from tests import test_strategy_correlation_uncertainty_audit as uncertainty_fixtures


FixtureCase = SimpleNamespace(
    _normal=(
        uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests._normal
    ),
    _correlated=(
        uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests._correlated
    ),
    _replay=(
        uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests._replay
    ),
)


def _canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


class StrategyCorrelationUncertaintyMultiWindowClusterGateV1Tests(
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
    def _singleton_clusters(symbols: list[str]) -> list[dict[str, object]]:
        return [
            {"cluster_id": symbol.lower(), "members": [symbol]}
            for symbol in symbols
        ]

    @staticmethod
    def _audit(
        series: dict[str, list[float]],
        clusters: list[dict[str, object]],
    ) -> dict[str, object]:
        return build_strategy_correlation_uncertainty_audit(
            FixtureCase._replay(series, clusters)
        )

    def _low_audit(
        self,
        clusters: list[dict[str, object]],
        seeds: tuple[int, ...],
    ) -> dict[str, object]:
        symbols = sorted(
            member
            for cluster in clusters
            for member in cluster["members"]
        )
        return self._audit(
            {
                symbol: FixtureCase._normal(seed)
                for symbol, seed in zip(symbols, seeds, strict=True)
            },
            clusters,
        )

    def _context(
        self,
        symbols: list[str],
        clusters: list[dict[str, object]],
        audits: list[dict[str, object]],
        windows: list[str] | None = None,
    ) -> tuple[dict[str, object], list[dict[str, object]], list[str]]:
        window_ids = windows or ["short", "long"]
        preregistration = subject.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            symbols,
            clusters,
            window_ids,
        )
        self.assertIsNotNone(preregistration)
        inputs = [
            {"window_id": window_id, "uncertainty_audit": audit}
            for window_id, audit in zip(window_ids, audits, strict=True)
        ]
        hashes = [str(audit["audit_hash"]) for audit in audits]
        return preregistration, inputs, hashes

    def _evaluate(
        self,
        context: tuple[dict[str, object], list[dict[str, object]], list[str]],
    ) -> dict[str, object]:
        preregistration, inputs, hashes = context
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            preregistration,
            inputs,
            expected_preregistration_hash=preregistration["preregistration_hash"],
            expected_window_audit_hashes=hashes,
        )
        self.assertIsNotNone(result)
        return result

    def test_every_window_confirmed_low_preserves_separate_clusters(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        audits = [
            self._low_audit(clusters, (1, 2)),
            self._low_audit(clusters, (3, 4)),
        ]

        gate = self._evaluate(self._context(symbols, clusters, audits))

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["dependence_edge_count"], 0)
        self.assertEqual(gate["cross_cluster_dependence_edge_count"], 0)
        self.assertEqual(gate["derived_conservative_component_count"], 2)
        self.assertEqual(
            gate["pair_assessments"][0]["conservative_state"],
            "CONFIRMED_LOW_ALL_WINDOWS",
        )
        self.assertTrue(gate["facts"]["all_windows_exactly_verified"])

    def test_one_confirmed_high_window_blocks_separate_clusters(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        base = FixtureCase._normal(1)
        audits = [
            self._low_audit(clusters, (2, 3)),
            self._audit(
                {"A": base, "B": FixtureCase._correlated(base, 0.98, 4)},
                clusters,
            ),
        ]

        gate = self._evaluate(self._context(symbols, clusters, audits))

        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["dependence_edge_count"], 1)
        self.assertEqual(gate["cross_cluster_dependence_edge_count"], 1)
        self.assertEqual(
            gate["pair_assessments"][0]["conservative_state"],
            "CONFIRMED_DEPENDENCE_EDGE",
        )

    def test_ambiguous_window_is_a_dependence_edge(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        base = FixtureCase._normal(1)
        ambiguous = self._audit(
            {"A": base, "B": FixtureCase._correlated(base, 0.76, 3)},
            clusters,
        )
        gate = self._evaluate(
            self._context(
                symbols,
                clusters,
                [self._low_audit(clusters, (8, 9)), ambiguous],
            )
        )

        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["pair_assessments"][0]["conservative_state"],
            "AMBIGUOUS_DEPENDENCE_EDGE",
        )

    def test_insufficient_effective_sample_is_a_dependence_edge(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        left = [math.sin(index * 0.05) for index in range(60)]
        right = [
            value + math.cos(index * 0.07) * 0.001
            for index, value in enumerate(left)
        ]
        insufficient = self._audit({"A": left, "B": right}, clusters)
        gate = self._evaluate(
            self._context(
                symbols,
                clusters,
                [self._low_audit(clusters, (12, 13)), insufficient],
            )
        )

        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["pair_assessments"][0]["conservative_state"],
            "INSUFFICIENT_SAMPLE_DEPENDENCE_EDGE",
        )

    def test_dependence_inside_one_preregistered_cluster_passes_grouping_gate(self) -> None:
        symbols = ["A", "B"]
        clusters = [{"cluster_id": "ab", "members": ["A", "B"]}]
        base_one = FixtureCase._normal(1)
        base_two = FixtureCase._normal(2)
        audits = [
            self._audit(
                {"A": base_one, "B": FixtureCase._correlated(base_one, 0.98, 4)},
                clusters,
            ),
            self._audit(
                {"A": base_two, "B": FixtureCase._correlated(base_two, 0.98, 5)},
                clusters,
            ),
        ]

        gate = self._evaluate(self._context(symbols, clusters, audits))

        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["dependence_edge_count"], 1)
        self.assertEqual(gate["cross_cluster_dependence_edge_count"], 0)
        self.assertEqual(
            gate["derived_conservative_components"][0]["members"],
            ["A", "B"],
        )

    def test_cross_window_bridge_forms_one_transitive_component(self) -> None:
        symbols = ["A", "B", "C"]
        clusters = self._singleton_clusters(symbols)
        first_base = FixtureCase._normal(1)
        second_base = FixtureCase._normal(11)
        first = self._audit(
            {
                "A": first_base,
                "B": FixtureCase._correlated(first_base, 0.98, 4),
                "C": FixtureCase._normal(9),
            },
            clusters,
        )
        second = self._audit(
            {
                "A": FixtureCase._normal(10),
                "B": second_base,
                "C": FixtureCase._correlated(second_base, 0.98, 12),
            },
            clusters,
        )

        gate = self._evaluate(
            self._context(symbols, clusters, [first, second])
        )

        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["derived_conservative_component_count"], 1)
        self.assertEqual(
            gate["derived_conservative_components"][0]["members"],
            ["A", "B", "C"],
        )
        self.assertTrue(
            gate["derived_conservative_components"][0][
                "crosses_preregistered_clusters"
            ]
        )

    def test_missing_reordered_and_reused_windows_fail_closed(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        audits = [
            self._low_audit(clusters, (1, 2)),
            self._low_audit(clusters, (3, 4)),
        ]
        preregistration, inputs, hashes = self._context(symbols, clusters, audits)

        missing = subject.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            preregistration,
            inputs[:1],
            expected_preregistration_hash=preregistration["preregistration_hash"],
            expected_window_audit_hashes=hashes[:1],
        )
        self.assertEqual(missing["status"], "UNKNOWN")

        reordered = subject.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            preregistration,
            list(reversed(inputs)),
            expected_preregistration_hash=preregistration["preregistration_hash"],
            expected_window_audit_hashes=list(reversed(hashes)),
        )
        self.assertEqual(reordered["status"], "UNKNOWN")

        reused = subject.evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            preregistration,
            [inputs[0], {"window_id": "long", "uncertainty_audit": audits[0]}],
            expected_preregistration_hash=preregistration["preregistration_hash"],
            expected_window_audit_hashes=[hashes[0], hashes[0]],
        )
        self.assertEqual(reused["status"], "UNKNOWN")

    def test_tampered_resealed_audit_cannot_change_pair_classification(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        audits = [
            self._low_audit(clusters, (1, 2)),
            self._low_audit(clusters, (3, 4)),
        ]
        forged = deepcopy(audits[1])
        forged["pairs"][0]["classification"] = "CONFIRMED_HIGH"
        forged_unsigned = dict(forged)
        forged_unsigned.pop("audit_hash")
        forged["audit_hash"] = _canonical_hash(forged_unsigned)
        context = self._context(symbols, clusters, [audits[0], forged])

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(gate["reason_code"], "WINDOW_AUDIT_VERIFICATION_FAILED")

    def test_audit_partition_must_match_preregistered_partition(self) -> None:
        symbols = ["A", "B"]
        audit_clusters = self._singleton_clusters(symbols)
        gate_clusters = [{"cluster_id": "ab", "members": ["A", "B"]}]
        audits = [
            self._low_audit(audit_clusters, (1, 2)),
            self._low_audit(audit_clusters, (3, 4)),
        ]

        gate = self._evaluate(self._context(symbols, gate_clusters, audits))

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(gate["reason_code"], "WINDOW_AUDIT_VERIFICATION_FAILED")

    def test_preregistration_rejects_noncanonical_or_incomplete_partitions(self) -> None:
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                ["B", "A"],
                self._singleton_clusters(["A", "B"]),
                ["short", "long"],
            )
        )
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                ["A", "B"],
                [{"cluster_id": "a", "members": ["A"]}],
                ["short", "long"],
            )
        )
        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                ["A", "B"],
                self._singleton_clusters(["A", "B"]),
                ["short", "short"],
            )
        )

    def test_gate_verifier_rebuilds_and_rejects_resealed_authority_promotion(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        audits = [
            self._low_audit(clusters, (1, 2)),
            self._low_audit(clusters, (3, 4)),
        ]
        preregistration, inputs, hashes = self._context(symbols, clusters, audits)
        gate = self._evaluate((preregistration, inputs, hashes))
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
                gate,
                preregistration,
                inputs,
                expected_gate_hash=gate["gate_hash"],
                expected_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
                expected_window_audit_hashes=hashes,
            )
        )
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = dict(forged)
        unsigned.pop("gate_hash")
        forged["gate_hash"] = _canonical_hash(unsigned)
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
                forged,
                preregistration,
                inputs,
                expected_gate_hash=forged["gate_hash"],
                expected_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
                expected_window_audit_hashes=hashes,
            )
        )

    def test_output_is_hash_bounded_and_all_authority_stays_false(self) -> None:
        symbols = ["A", "B"]
        clusters = self._singleton_clusters(symbols)
        audits = [
            self._low_audit(clusters, (1, 2)),
            self._low_audit(clusters, (3, 4)),
        ]
        gate = self._evaluate(self._context(symbols, clusters, audits))
        serialized = json.dumps(gate, sort_keys=True)

        self.assertNotIn("completed_price_input", serialized)
        self.assertNotIn("price_rows", serialized)
        self.assertNotIn("matrix_replay", serialized)
        self.assertFalse(gate["facts"]["raw_uncertainty_audits_embedded"])
        self.assertFalse(gate["facts"]["raw_price_or_return_series_embedded"])
        self.assertTrue(
            all(
                value is False
                for key, value in gate["authority"].items()
                if key != "research_evidence_only"
            )
        )

    def test_upstream_source_pin_matches_reviewed_implementation(self) -> None:
        source_path = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "services"
            / "strategy_correlation_uncertainty_audit.py"
        )
        self.assertEqual(
            sha256(source_path.read_bytes()).hexdigest(),
            subject.UNCERTAINTY_AUDIT_SOURCE_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
