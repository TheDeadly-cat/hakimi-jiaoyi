from __future__ import annotations

import copy
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_independent_ticket_consumer_v3
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as source_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class MultiWindowIndependentTicketConsumerV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = [
            ("short", 20),
            ("anchor", 60),
            ("long", 120),
        ]
        self.clusters = [
            {"cluster_id": "tech", "members": ["A", "B"]},
            {"cluster_id": "rates", "members": ["C"]},
        ]
        self.correlations = {
            ("A", "B"): 0.90,
            ("A", "C"): 0.10,
            ("B", "C"): 0.10,
        }
        self.bindings = []
        self.inputs = {}
        for window_id, lookback in self.specs:
            binding, item = self._window(window_id, lookback)
            self.bindings.append(binding)
            self.inputs[window_id] = item
        self.preregistration = (
            subject.build_multi_window_independent_ticket_consumer_preregistration_v3(
                self.bindings
            )
        )
        self.expected_hash = self.preregistration[
            "consumer_preregistration_v3_hash"
        ]

    @staticmethod
    def _cells(statuses=None):
        statuses = statuses or {"A": "PASS", "B": "PASS", "C": "PASS"}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "fixed-v3",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in statuses.items()
        ]

    def _window(
        self,
        window_id,
        lookback,
        *,
        clusters=None,
        correlations=None,
        statuses=None,
        pseudo_status=None,
    ):
        preregistration = (
            source_v2.build_correlation_cluster_window_source_preregistration_v2(
                window_id=window_id,
                lookback_observations=lookback,
                clusters=self.clusters if clusters is None else clusters,
            )
        )
        matrix = source_v2.build_correlation_cluster_window_matrix_v2(
            preregistration,
            self.correlations if correlations is None else correlations,
            overlap_observations=lookback,
        )
        cells = self._cells(statuses)
        if pseudo_status is not None:
            cells[0]["gate_status"] = pseudo_status
        gate = source_v2.evaluate_correlation_cluster_window_independent_ticket_gate_v2(
            preregistration,
            matrix,
            cells,
            expected_preregistration_v2_hash=preregistration[
                "preregistration_v2_hash"
            ],
            strategy_id="trend",
            variant_id="fixed-v3",
            lane="RAW_EXCESS",
        )
        return (
            {
                "window_id": window_id,
                "lookback_observations": lookback,
                "source_preregistration_v2_hash": preregistration[
                    "preregistration_v2_hash"
                ],
            },
            {
                "source_preregistration": preregistration,
                "matrix": matrix,
                "selection_cells": cells,
                "gate": gate,
            },
        )

    def evaluate(self, *, inputs=None, preregistration=None, expected_hash=None):
        return subject.evaluate_multi_window_independent_ticket_consumer_v3(
            self.preregistration if preregistration is None else preregistration,
            self.inputs if inputs is None else inputs,
            expected_consumer_preregistration_v3_hash=(
                self.expected_hash if expected_hash is None else expected_hash
            ),
            strategy_id="trend",
            variant_id="fixed-v3",
            lane="RAW_EXCESS",
        )

    def test_three_real_exact_source_v2_windows_pass_without_mock(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["summary"]["verified_window_count"], 3)
        self.assertEqual(document["summary"]["unique_matrix_hash_count"], 3)
        self.assertEqual(document["summary"]["unique_partition_count"], 1)
        self.assertEqual(
            document["summary"][
                "conservative_effective_independent_ticket_count"
            ],
            2,
        )
        self.assertEqual(
            document["summary"]["maximum_raw_passing_symbol_ticket_count"],
            3,
        )
        self.assertTrue(document["facts"]["all_windows_exactly_verified"])
        self.assertFalse(document["facts"]["mock_verifier_used"])
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_one_exact_window_cluster_vote_block_blocks_consumer(self):
        inputs = copy.deepcopy(self.inputs)
        _, inputs["long"] = self._window(
            "long",
            120,
            statuses={"A": "PASS", "B": "PASS", "C": "BLOCK"},
        )
        document = self.evaluate(inputs=inputs)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "WINDOW_GATES")
        self.assertIn("window_gate_blocked:long", document["blockers"])
        self.assertEqual(
            document["summary"][
                "conservative_effective_independent_ticket_count"
            ],
            1,
        )

    def test_exact_partition_drift_blocks_before_window_gate_promotion(self):
        inputs = copy.deepcopy(self.inputs)
        drift_clusters = [
            {"cluster_id": "ac", "members": ["A", "C"]},
            {"cluster_id": "b", "members": ["B"]},
        ]
        drift_correlations = {
            ("A", "B"): 0.10,
            ("A", "C"): 0.90,
            ("B", "C"): 0.10,
        }
        binding, inputs["long"] = self._window(
            "long",
            120,
            clusters=drift_clusters,
            correlations=drift_correlations,
        )
        bindings = copy.deepcopy(self.bindings)
        bindings[-1] = binding
        preregistration = (
            subject.build_multi_window_independent_ticket_consumer_preregistration_v3(
                bindings
            )
        )
        document = self.evaluate(
            inputs=inputs,
            preregistration=preregistration,
            expected_hash=preregistration["consumer_preregistration_v3_hash"],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"],
            "BLOCK_MULTI_WINDOW_CLUSTER_PARTITION_DRIFT",
        )
        self.assertEqual(document["summary"]["unique_partition_count"], 2)

    def test_missing_extra_and_spliced_window_inputs_are_unknown(self):
        missing = copy.deepcopy(self.inputs)
        missing.pop("long")
        extra = copy.deepcopy(self.inputs)
        extra["extra"] = copy.deepcopy(self.inputs["long"])
        spliced = copy.deepcopy(self.inputs)
        spliced["long"] = copy.deepcopy(self.inputs["anchor"])
        for inputs in (missing, extra, spliced):
            with self.subTest(keys=sorted(inputs)):
                document = self.evaluate(inputs=inputs)
                self.assertEqual(document["status"], "UNKNOWN")
                self.assertEqual(document["window_summaries"], [])
                self.assertEqual(document["first_blocking_tier"], "SOURCE")

    def test_resealed_blocked_window_promotion_is_unknown(self):
        inputs = copy.deepcopy(self.inputs)
        _, blocked = self._window(
            "long",
            120,
            statuses={"A": "PASS", "B": "PASS", "C": "BLOCK"},
        )
        promoted = copy.deepcopy(blocked["gate"])
        promoted.pop("gate_v2_hash")
        promoted["status"] = "PASS"
        promoted["effective_independent_ticket_count"] = 2
        promoted = seal_strict_canonical_document(promoted, "gate_v2_hash")
        blocked["gate"] = promoted
        inputs["long"] = blocked
        document = self.evaluate(inputs=inputs)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("window_source_unverified:long", document["blockers"])

    def test_nested_unhashable_pseudo_status_is_unknown(self):
        inputs = copy.deepcopy(self.inputs)
        _, inputs["long"] = self._window(
            "long",
            120,
            pseudo_status={},
        )
        document = self.evaluate(inputs=inputs)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("window_source_unverified:long", document["blockers"])

    def test_preregistration_rejects_count_order_boolean_and_duplicate_hash(self):
        cases = [
            self.bindings[:2],
            [self.bindings[1], self.bindings[0], self.bindings[2]],
            [
                self.bindings[0],
                {**self.bindings[1], "lookback_observations": True},
                self.bindings[2],
            ],
            [
                self.bindings[0],
                {
                    **self.bindings[1],
                    "source_preregistration_v2_hash": self.bindings[0][
                        "source_preregistration_v2_hash"
                    ],
                },
                self.bindings[2],
            ],
        ]
        for bindings in cases:
            with self.subTest(bindings=bindings):
                with self.assertRaises(
                    subject.MultiWindowIndependentTicketConsumerContractError
                ):
                    subject.build_multi_window_independent_ticket_consumer_preregistration_v3(
                        bindings
                    )

    def test_wrong_consumer_pin_and_non_native_inputs_fail_closed(self):
        wrong_pin = self.evaluate(expected_hash="0" * 64)
        non_native = subject.evaluate_multi_window_independent_ticket_consumer_v3(
            None,
            None,
            expected_consumer_preregistration_v3_hash=None,
            strategy_id="trend",
            variant_id="fixed-v3",
            lane="RAW_EXCESS",
        )
        for document in (wrong_pin, non_native):
            self.assertEqual(document["status"], "UNKNOWN")
            self.assertEqual(document["window_summaries"], [])
            self.assertFalse(document["authority"]["paper_authorized"])
            self.assertFalse(document["authority"]["live_order_allowed"])

    def test_exact_consumer_verifier_rejects_resealed_count_and_authority(self):
        document = self.evaluate()
        valid = subject.verify_multi_window_independent_ticket_consumer_v3(
            document,
            self.preregistration,
            self.inputs,
            expected_consumer_preregistration_v3_hash=self.expected_hash,
            strategy_id="trend",
            variant_id="fixed-v3",
            lane="RAW_EXCESS",
        )
        variants = []
        for mutate in (
            lambda item: item["summary"].__setitem__(
                "conservative_effective_independent_ticket_count", 99
            ),
            lambda item: item["authority"].__setitem__("paper_authorized", True),
        ):
            changed = copy.deepcopy(document)
            changed.pop("consumer_v3_hash")
            mutate(changed)
            variants.append(
                seal_strict_canonical_document(changed, "consumer_v3_hash")
            )
        self.assertEqual(valid["status"], "PASS")
        for changed in variants:
            receipt = subject.verify_multi_window_independent_ticket_consumer_v3(
                changed,
                self.preregistration,
                self.inputs,
                expected_consumer_preregistration_v3_hash=self.expected_hash,
                strategy_id="trend",
                variant_id="fixed-v3",
                lane="RAW_EXCESS",
            )
            self.assertEqual(receipt["status"], "BLOCK")

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        preregistration_before = copy.deepcopy(self.preregistration)
        inputs_before = copy.deepcopy(self.inputs)
        document = self.evaluate()
        self.assertEqual(self.preregistration, preregistration_before)
        self.assertEqual(self.inputs, inputs_before)
        self.assertNotIn("matrix", document)
        self.assertNotIn("selection_cells", document)
        self.assertFalse(document["facts"]["source_documents_embedded"])
        self.assertFalse(document["facts"]["current_activated"])


if __name__ == "__main__":
    unittest.main()
