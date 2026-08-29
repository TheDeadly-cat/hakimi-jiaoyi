from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math
import random
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
    build_strategy_correlation_uncertainty_policy,
    verify_strategy_correlation_uncertainty_audit,
    verify_strategy_correlation_uncertainty_policy,
)
from exchange_terminal.services.strategy_matrix_protocol import canonical_hash


class StrategyCorrelationUncertaintyAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay_verifier = patch(
            "exchange_terminal.services.strategy_correlation_uncertainty_audit."
            "verify_correlation_matrix_replay",
            return_value={"status": "PASS", "blockers": []},
        )
        self.replay_verifier.start()
        self.addCleanup(self.replay_verifier.stop)

    @staticmethod
    def _normal(seed: int) -> list[float]:
        generator = random.Random(seed)
        return [generator.gauss(0.0, 1.0) for _ in range(60)]

    @classmethod
    def _correlated(cls, base: list[float], rho: float, seed: int) -> list[float]:
        noise = cls._normal(seed)
        scale = math.sqrt(1.0 - rho * rho)
        return [rho * left + scale * right for left, right in zip(base, noise, strict=True)]

    @staticmethod
    def _price_rows(signal: list[float]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        price = 100.0
        start = date(2026, 1, 1)
        rows.append({"date": start.isoformat(), "close": price, "complete": True})
        for index, value in enumerate(signal, start=1):
            price *= 1.0 + value * 0.005
            rows.append({
                "date": (start + timedelta(days=index)).isoformat(),
                "close": price,
                "complete": True,
            })
        return rows

    @classmethod
    def _replay(
        cls,
        series: dict[str, list[float]],
        clusters: list[dict[str, object]],
    ) -> dict[str, object]:
        symbols = sorted(series)
        return {
            "schema_version": "strategy-correlation-matrix-replay-v1",
            "status": "PASS",
            "replay_hash": "r" * 64,
            "preregistration": {
                "schema_version": "strategy-correlation-cluster-preregistration-v1",
                "symbols": symbols,
                "clusters": clusters,
                "preregistration_hash": "p" * 64,
            },
            "completed_price_input": {
                "datasets": [
                    {
                        "symbol": symbol,
                        "price_rows": cls._price_rows(series[symbol]),
                    }
                    for symbol in symbols
                ],
            },
        }

    @staticmethod
    def _pair(audit: dict[str, object], left: str, right: str) -> dict[str, object]:
        expected = {left, right}
        return next(
            item
            for item in audit["pairs"]
            if {item["left_symbol"], item["right_symbol"]} == expected
        )

    def test_independent_cross_cluster_pairs_pass_descriptively_only(self) -> None:
        replay = self._replay(
            {"A": self._normal(1), "B": self._normal(2), "C": self._normal(3)},
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
                {"cluster_id": "c", "members": ["C"]},
            ],
        )
        audit = build_strategy_correlation_uncertainty_audit(replay)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["confirmed_high_cross_cluster_count"], 0)
        self.assertEqual(audit["ambiguous_cross_cluster_count"], 0)
        self.assertFalse(audit["current_writer_activation_allowed"])
        self.assertFalse(audit["current_admission_allowed"])
        self.assertFalse(audit["permissions"]["paper_authorized"])
        self.assertFalse(audit["permissions"]["live_order_allowed"])
        self.assertEqual(audit["policy_hash"], audit["policy"]["policy_hash"])
        self.assertEqual(
            verify_strategy_correlation_uncertainty_policy(audit["policy"])["status"],
            "PASS",
        )
        self.assertEqual(verify_strategy_correlation_uncertainty_audit(audit)["status"], "PASS")

    def test_threshold_neighborhood_is_ambiguous_and_blocks_cross_cluster(self) -> None:
        base = self._normal(1)
        replay = self._replay(
            {"A": base, "B": self._correlated(base, 0.76, 3)},
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
            ],
        )
        audit = build_strategy_correlation_uncertainty_audit(replay)
        pair = self._pair(audit, "A", "B")

        self.assertEqual(pair["classification"], "AMBIGUOUS_THRESHOLD")
        self.assertLess(pair["absolute_correlation_interval_lower"], 0.75)
        self.assertGreaterEqual(pair["absolute_correlation_interval_upper"], 0.75)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["first_blocking_tier"], "CROSS_CLUSTER_UNCERTAINTY")

    def test_positive_and_negative_high_cross_cluster_pairs_are_confirmed(self) -> None:
        base = self._normal(1)
        for label, series in (
            ("positive", self._correlated(base, 0.98, 4)),
            ("negative", [-value for value in self._correlated(base, 0.98, 5)]),
        ):
            with self.subTest(label=label):
                audit = build_strategy_correlation_uncertainty_audit(self._replay(
                    {"A": base, "B": series},
                    [
                        {"cluster_id": "a", "members": ["A"]},
                        {"cluster_id": "b", "members": ["B"]},
                    ],
                ))
                pair = self._pair(audit, "A", "B")
                self.assertEqual(pair["classification"], "CONFIRMED_HIGH")
                self.assertGreaterEqual(pair["absolute_correlation_interval_lower"], 0.75)
                self.assertEqual(audit["status"], "BLOCK")

    def test_high_within_cluster_pair_does_not_create_independent_vote_conflict(self) -> None:
        base = self._normal(1)
        audit = build_strategy_correlation_uncertainty_audit(self._replay(
            {
                "A": base,
                "B": self._correlated(base, 0.98, 4),
                "C": self._normal(9),
            },
            [
                {"cluster_id": "ab", "members": ["A", "B"]},
                {"cluster_id": "c", "members": ["C"]},
            ],
        ))
        pair = self._pair(audit, "A", "B")

        self.assertEqual(pair["classification"], "CONFIRMED_HIGH")
        self.assertFalse(pair["cross_cluster"])
        self.assertEqual(audit["confirmed_high_cross_cluster_count"], 0)
        self.assertEqual(audit["status"], "PASS")

    def test_smooth_returns_fail_minimum_effective_sample(self) -> None:
        left = [math.sin(index * 0.05) for index in range(60)]
        right = [value + math.cos(index * 0.07) * 0.001 for index, value in enumerate(left)]
        audit = build_strategy_correlation_uncertainty_audit(self._replay(
            {"A": left, "B": right},
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
            ],
        ))
        pair = self._pair(audit, "A", "B")

        self.assertEqual(pair["classification"], "INSUFFICIENT_EFFECTIVE_SAMPLE")
        self.assertLess(pair["effective_observations"], 12.0)
        self.assertEqual(audit["first_blocking_tier"], "EFFECTIVE_SAMPLE")
        self.assertEqual(audit["status"], "BLOCK")

    def test_coherently_resealed_status_and_counts_cannot_survive_replay(self) -> None:
        base = self._normal(1)
        audit = build_strategy_correlation_uncertainty_audit(self._replay(
            {"A": base, "B": self._correlated(base, 0.76, 3)},
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
            ],
        ))
        forged = deepcopy(audit)
        forged["status"] = "PASS"
        forged["ambiguous_cross_cluster_count"] = 0
        forged["blockers"] = []
        clean = dict(forged)
        clean.pop("audit_hash")
        forged["audit_hash"] = canonical_hash(clean)

        verification = verify_strategy_correlation_uncertainty_audit(forged)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_uncertainty_audit_replay_mismatch",
            verification["blockers"],
        )

    def test_resealed_authority_alias_is_blocked(self) -> None:
        audit = build_strategy_correlation_uncertainty_audit(self._replay(
            {"A": self._normal(1), "B": self._normal(2)},
            [
                {"cluster_id": "a", "members": ["A"]},
                {"cluster_id": "b", "members": ["B"]},
            ],
        ))
        forged = deepcopy(audit)
        forged["permissions"]["can_trade"] = True
        clean = dict(forged)
        clean.pop("audit_hash")
        forged["audit_hash"] = canonical_hash(clean)

        verification = verify_strategy_correlation_uncertainty_audit(forged)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_uncertainty_audit_authority_violation",
            verification["blockers"],
        )

    def test_invalid_matrix_replay_fails_before_price_analysis(self) -> None:
        with patch(
            "exchange_terminal.services.strategy_correlation_uncertainty_audit."
            "verify_correlation_matrix_replay",
            return_value={"status": "BLOCK", "blockers": ["tampered"]},
        ):
            with self.assertRaises(ValueError):
                build_strategy_correlation_uncertainty_audit({})

    def test_resealed_policy_threshold_downgrade_is_blocked(self) -> None:
        policy = build_strategy_correlation_uncertainty_policy()
        forged = deepcopy(policy)
        forged["absolute_pearson_threshold"] = 0.95
        clean = dict(forged)
        clean.pop("policy_hash")
        forged["policy_hash"] = canonical_hash(clean)

        verification = verify_strategy_correlation_uncertainty_policy(forged)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_uncertainty_policy_contract_mismatch",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
