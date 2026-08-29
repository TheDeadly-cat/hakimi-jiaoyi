from __future__ import annotations

import copy
from datetime import date, timedelta
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_independent_ticket_consumer_v3
    as consumer_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_return_panel_lineage_adapter_v4
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as source_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class MultiWindowReturnPanelLineageAdapterV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = [("short", 20), ("anchor", 60), ("long", 120)]
        self.clusters = [
            {"cluster_id": "tech", "members": ["A", "B"]},
            {"cluster_id": "rates", "members": ["C"]},
        ]
        self.source_preregistrations = {}
        self.bindings = []
        for window_id, lookback in self.specs:
            source = source_v2.build_correlation_cluster_window_source_preregistration_v2(
                window_id=window_id,
                lookback_observations=lookback,
                clusters=self.clusters,
            )
            self.source_preregistrations[window_id] = source
            self.bindings.append(
                {
                    "window_id": window_id,
                    "lookback_observations": lookback,
                    "source_preregistration_v2_hash": source[
                        "preregistration_v2_hash"
                    ],
                }
            )
        self.consumer_preregistration = (
            consumer_v3.build_multi_window_independent_ticket_consumer_preregistration_v3(
                self.bindings
            )
        )
        self.panel = self._panel()
        self.lineage_preregistration = (
            subject.build_multi_window_return_panel_lineage_preregistration_v4(
                self.consumer_preregistration,
                self.source_preregistrations,
                expected_panel_hash=self.panel["panel_hash"],
                timeframe="1d",
                cutoff_date=self.panel["cutoff_date"],
            )
        )
        self.expected_lineage_hash = self.lineage_preregistration[
            "lineage_preregistration_v4_hash"
        ]
        self.matrices = subject.derive_multi_window_matrices_from_return_panel_v4(
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel,
        )
        self.window_inputs = self._window_inputs()
        self.consumer_document = self._consumer(self.window_inputs)

    @staticmethod
    def _rows(count=130, *, constant_a=False):
        start = date(2026, 1, 1)
        a_pattern = (-0.010, -0.005, 0.005, 0.010)
        c_pattern = (0.010, -0.010, -0.010, 0.010)
        rows = []
        for index in range(count):
            a_value = 0.0 if constant_a else a_pattern[index % 4]
            rows.append(
                {
                    "date": (start + timedelta(days=index)).isoformat(),
                    "returns": {
                        "A": a_value,
                        "B": a_value * 0.9,
                        "C": c_pattern[index % 4],
                    },
                }
            )
        return rows

    def _panel(self, rows=None):
        rows = self._rows() if rows is None else rows
        return subject.build_common_return_panel_v1(
            symbols=["A", "B", "C"],
            rows=rows,
            timeframe="1d",
            cutoff_date=rows[-1]["date"],
        )

    @staticmethod
    def _cells(statuses=None):
        statuses = statuses or {"A": "PASS", "B": "PASS", "C": "PASS"}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "lineage-v4",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in statuses.items()
        ]

    def _window_inputs(self, *, long_statuses=None, matrices=None):
        matrices = self.matrices if matrices is None else matrices
        inputs = {}
        for window_id, _ in self.specs:
            source = self.source_preregistrations[window_id]
            cells = self._cells(long_statuses if window_id == "long" else None)
            matrix = matrices[window_id]
            gate = source_v2.evaluate_correlation_cluster_window_independent_ticket_gate_v2(
                source,
                matrix,
                cells,
                expected_preregistration_v2_hash=source[
                    "preregistration_v2_hash"
                ],
                strategy_id="trend",
                variant_id="lineage-v4",
                lane="RAW_EXCESS",
            )
            inputs[window_id] = {
                "source_preregistration": source,
                "matrix": matrix,
                "selection_cells": cells,
                "gate": gate,
            }
        return inputs

    def _consumer(self, inputs):
        return consumer_v3.evaluate_multi_window_independent_ticket_consumer_v3(
            self.consumer_preregistration,
            inputs,
            expected_consumer_preregistration_v3_hash=(
                self.consumer_preregistration[
                    "consumer_preregistration_v3_hash"
                ]
            ),
            strategy_id="trend",
            variant_id="lineage-v4",
            lane="RAW_EXCESS",
        )

    def evaluate(
        self,
        *,
        panel=None,
        lineage_preregistration=None,
        consumer_document=None,
        window_inputs=None,
        expected_lineage_hash=None,
    ):
        return subject.evaluate_multi_window_return_panel_lineage_adapter_v4(
            self.lineage_preregistration
            if lineage_preregistration is None
            else lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel if panel is None else panel,
            self.consumer_document
            if consumer_document is None
            else consumer_document,
            self.window_inputs if window_inputs is None else window_inputs,
            expected_lineage_preregistration_v4_hash=(
                self.expected_lineage_hash
                if expected_lineage_hash is None
                else expected_lineage_hash
            ),
            strategy_id="trend",
            variant_id="lineage-v4",
            lane="RAW_EXCESS",
        )

    def test_raw_common_panel_recomputes_three_exact_matrices(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(document["facts"]["raw_return_rows_recomputed"])
        self.assertTrue(document["facts"]["common_observation_membership_exact"])
        self.assertTrue(document["facts"]["all_window_matrices_exactly_derived"])
        self.assertEqual(document["summary"]["panel_row_count"], 130)
        self.assertEqual(document["summary"]["verified_window_matrix_count"], 3)
        self.assertEqual(
            document["summary"][
                "conservative_effective_independent_ticket_count"
            ],
            2,
        )
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_exact_consumer_block_is_preserved_after_lineage_passes(self):
        inputs = self._window_inputs(
            long_statuses={"A": "PASS", "B": "PASS", "C": "BLOCK"}
        )
        consumer = self._consumer(inputs)
        document = self.evaluate(
            consumer_document=consumer,
            window_inputs=inputs,
        )
        self.assertEqual(consumer["status"], "BLOCK")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "CONSUMER")
        self.assertTrue(document["facts"]["raw_return_rows_recomputed"])

    def test_resealed_raw_return_change_cannot_reuse_old_matrices(self):
        rows = copy.deepcopy(self.panel["rows"])
        rows[-1]["returns"]["A"] += 0.001
        changed_panel = self._panel(rows)
        changed_lineage = (
            subject.build_multi_window_return_panel_lineage_preregistration_v4(
                self.consumer_preregistration,
                self.source_preregistrations,
                expected_panel_hash=changed_panel["panel_hash"],
                timeframe="1d",
                cutoff_date=changed_panel["cutoff_date"],
            )
        )
        document = self.evaluate(
            panel=changed_panel,
            lineage_preregistration=changed_lineage,
            expected_lineage_hash=changed_lineage[
                "lineage_preregistration_v4_hash"
            ],
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn(
            "return_panel_window_matrix_mismatch:short",
            document["blockers"],
        )

    def test_resealed_matrix_correlation_tamper_is_unknown(self):
        inputs = copy.deepcopy(self.window_inputs)
        matrix = copy.deepcopy(inputs["long"]["matrix"])
        matrix.pop("matrix_v2_hash")
        matrix["pairs"][0]["pearson_correlation"] = 0.50
        matrix = seal_strict_canonical_document(matrix, "matrix_v2_hash")
        inputs["long"]["matrix"] = matrix
        document = self.evaluate(window_inputs=inputs)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn(
            "return_panel_window_matrix_mismatch:long",
            document["blockers"],
        )

    def test_missing_common_member_and_future_cutoff_rows_are_rejected(self):
        missing = self._rows()
        missing[0]["returns"].pop("C")
        future = self._rows()
        for rows, cutoff in (
            (missing, missing[-1]["date"]),
            (future, future[-2]["date"]),
        ):
            with self.subTest(cutoff=cutoff):
                with self.assertRaises(
                    subject.MultiWindowReturnPanelLineageContractError
                ):
                    subject.build_common_return_panel_v1(
                        symbols=["A", "B", "C"],
                        rows=rows,
                        timeframe="1d",
                        cutoff_date=cutoff,
                    )

    def test_zero_variance_panel_cannot_derive_pearson_matrix(self):
        panel = self._panel(self._rows(constant_a=True))
        lineage = subject.build_multi_window_return_panel_lineage_preregistration_v4(
            self.consumer_preregistration,
            self.source_preregistrations,
            expected_panel_hash=panel["panel_hash"],
            timeframe="1d",
            cutoff_date=panel["cutoff_date"],
        )
        with self.assertRaisesRegex(
            subject.MultiWindowReturnPanelLineageContractError,
            "variance must be positive",
        ):
            subject.derive_multi_window_matrices_from_return_panel_v4(
                lineage,
                self.consumer_preregistration,
                self.source_preregistrations,
                panel,
            )

    def test_wrong_lineage_pin_and_spliced_source_are_unknown(self):
        wrong_pin = self.evaluate(expected_lineage_hash="0" * 64)
        sources = copy.deepcopy(self.source_preregistrations)
        sources["long"] = copy.deepcopy(sources["anchor"])
        spliced = subject.evaluate_multi_window_return_panel_lineage_adapter_v4(
            self.lineage_preregistration,
            self.consumer_preregistration,
            sources,
            self.panel,
            self.consumer_document,
            self.window_inputs,
            expected_lineage_preregistration_v4_hash=self.expected_lineage_hash,
            strategy_id="trend",
            variant_id="lineage-v4",
            lane="RAW_EXCESS",
        )
        for document in (wrong_pin, spliced):
            self.assertEqual(document["status"], "UNKNOWN")
            self.assertEqual(document["window_lineage_summaries"], [])
            self.assertIsNone(document["summary"])

    def test_exact_adapter_verifier_rejects_resealed_count_and_authority(self):
        document = self.evaluate()
        valid = subject.verify_multi_window_return_panel_lineage_adapter_v4(
            document,
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel,
            self.consumer_document,
            self.window_inputs,
            expected_lineage_preregistration_v4_hash=self.expected_lineage_hash,
            strategy_id="trend",
            variant_id="lineage-v4",
            lane="RAW_EXCESS",
        )
        variants = []
        for mutate in (
            lambda item: item["summary"].__setitem__("panel_row_count", 999),
            lambda item: item["authority"].__setitem__("paper_authorized", True),
        ):
            changed = copy.deepcopy(document)
            changed.pop("adapter_v4_hash")
            mutate(changed)
            variants.append(seal_strict_canonical_document(changed, "adapter_v4_hash"))
        self.assertEqual(valid["status"], "PASS")
        for changed in variants:
            receipt = subject.verify_multi_window_return_panel_lineage_adapter_v4(
                changed,
                self.lineage_preregistration,
                self.consumer_preregistration,
                self.source_preregistrations,
                self.panel,
                self.consumer_document,
                self.window_inputs,
                expected_lineage_preregistration_v4_hash=self.expected_lineage_hash,
                strategy_id="trend",
                variant_id="lineage-v4",
                lane="RAW_EXCESS",
            )
            self.assertEqual(receipt["status"], "BLOCK")

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        before = copy.deepcopy(
            (
                self.lineage_preregistration,
                self.consumer_preregistration,
                self.source_preregistrations,
                self.panel,
                self.consumer_document,
                self.window_inputs,
            )
        )
        document = self.evaluate()
        after = (
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel,
            self.consumer_document,
            self.window_inputs,
        )
        self.assertEqual(after, before)
        self.assertNotIn("rows", document)
        self.assertNotIn("matrix", document)
        self.assertNotIn("selection_cells", document)
        self.assertTrue(document["facts"]["raw_return_rows_recomputed"])
        self.assertFalse(document["facts"]["raw_rows_embedded"])
        self.assertFalse(document["facts"]["source_documents_embedded"])


if __name__ == "__main__":
    unittest.main()
