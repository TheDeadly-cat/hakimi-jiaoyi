from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_independent_ticket_consumer_v3
    as consumer_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_market_data_envelope_binding_adapter_v5
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_return_panel_lineage_adapter_v4
    as lineage_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as source_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class MultiWindowMarketDataEnvelopeBindingAdapterV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = [("short", 20), ("anchor", 60), ("long", 120)]
        self.clusters = [
            {"cluster_id": "tech", "members": ["A", "B"]},
            {"cluster_id": "rates", "members": ["C"]},
        ]
        self.payloads = self._payloads()
        self.panel = subject.derive_common_return_panel_from_market_data_envelopes_v5(
            self.payloads
        )
        self.source_bindings = subject.market_data_envelope_source_bindings_v5(
            self.payloads
        )
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
        self.consumer_preregistration = consumer_v3.build_multi_window_independent_ticket_consumer_preregistration_v3(
            self.bindings
        )
        self.lineage_preregistration = lineage_v4.build_multi_window_return_panel_lineage_preregistration_v4(
            self.consumer_preregistration,
            self.source_preregistrations,
            expected_panel_hash=self.panel["panel_hash"],
            timeframe="1d",
            cutoff_date=self.panel["cutoff_date"],
        )
        self.matrices = lineage_v4.derive_multi_window_matrices_from_return_panel_v4(
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel,
        )
        self.window_inputs = self._window_inputs()
        self.consumer_document = self._consumer(self.window_inputs)
        self.lineage_document = self._lineage(
            self.consumer_document,
            self.window_inputs,
        )
        self.binding_preregistration = subject.build_market_data_envelope_binding_preregistration_v5(
            self.source_bindings,
            expected_panel_hash=self.panel["panel_hash"],
            expected_lineage_preregistration_v4_hash=self.lineage_preregistration[
                "lineage_preregistration_v4_hash"
            ],
        )
        self.expected_binding_hash = self.binding_preregistration[
            "binding_preregistration_v5_hash"
        ]

    @staticmethod
    def _return_sequences(count=130):
        a_pattern = (-0.010, -0.005, 0.005, 0.010)
        c_pattern = (0.010, -0.010, -0.010, 0.010)
        return {
            "A": [a_pattern[index % 4] for index in range(count)],
            "B": [a_pattern[index % 4] * 0.9 for index in range(count)],
            "C": [c_pattern[index % 4] for index in range(count)],
        }

    def _payloads(self, *, source_prefix="unverified_primary_feed"):
        returns = self._return_sequences()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        payloads = {}
        for symbol in ("A", "B", "C"):
            provider = f"{source_prefix}_{symbol.lower()}"
            closes = [100.0]
            for value in returns[symbol]:
                closes.append(closes[-1] * (1.0 + value))
            rows = [
                {
                    "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                    "close": close,
                    "complete": True,
                    "source": provider,
                }
                for index, close in enumerate(closes)
            ]
            payload = {
                "ok": True,
                "symbol": symbol,
                "source": provider,
                "rows": rows,
            }
            payloads[symbol] = attach_market_data_envelope(
                payload,
                symbol=symbol,
                timeframe="1D",
            )
        return payloads

    @staticmethod
    def _cells(statuses=None):
        statuses = statuses or {"A": "PASS", "B": "PASS", "C": "PASS"}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "envelope-v5",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in statuses.items()
        ]

    def _window_inputs(self, *, long_statuses=None):
        inputs = {}
        for window_id, _ in self.specs:
            source = self.source_preregistrations[window_id]
            matrix = self.matrices[window_id]
            cells = self._cells(long_statuses if window_id == "long" else None)
            gate = source_v2.evaluate_correlation_cluster_window_independent_ticket_gate_v2(
                source,
                matrix,
                cells,
                expected_preregistration_v2_hash=source[
                    "preregistration_v2_hash"
                ],
                strategy_id="trend",
                variant_id="envelope-v5",
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
            variant_id="envelope-v5",
            lane="RAW_EXCESS",
        )

    def _lineage(self, consumer, inputs):
        return lineage_v4.evaluate_multi_window_return_panel_lineage_adapter_v4(
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.panel,
            consumer,
            inputs,
            expected_lineage_preregistration_v4_hash=self.lineage_preregistration[
                "lineage_preregistration_v4_hash"
            ],
            strategy_id="trend",
            variant_id="envelope-v5",
            lane="RAW_EXCESS",
        )

    def evaluate(
        self,
        *,
        payloads=None,
        binding_preregistration=None,
        lineage_document=None,
        consumer_document=None,
        window_inputs=None,
        expected_binding_hash=None,
    ):
        return subject.evaluate_market_data_envelope_binding_adapter_v5(
            self.binding_preregistration
            if binding_preregistration is None
            else binding_preregistration,
            self.payloads if payloads is None else payloads,
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.lineage_document if lineage_document is None else lineage_document,
            self.consumer_document if consumer_document is None else consumer_document,
            self.window_inputs if window_inputs is None else window_inputs,
            expected_binding_preregistration_v5_hash=(
                self.expected_binding_hash
                if expected_binding_hash is None
                else expected_binding_hash
            ),
            strategy_id="trend",
            variant_id="envelope-v5",
            lane="RAW_EXCESS",
        )

    def test_canonical_envelopes_derive_and_bind_exact_lineage(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(document["facts"]["market_data_envelopes_exactly_verified"])
        self.assertTrue(document["facts"]["close_grid_exactly_aligned"])
        self.assertTrue(document["facts"]["return_panel_derived_from_envelopes"])
        self.assertTrue(document["facts"]["provider_identity_structurally_bound"])
        self.assertFalse(document["facts"]["provider_identity_authenticated"])
        self.assertEqual(document["summary"]["common_close_row_count"], 131)
        self.assertEqual(document["summary"]["derived_return_row_count"], 130)
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_lineage_consumer_block_is_preserved(self):
        inputs = self._window_inputs(
            long_statuses={"A": "PASS", "B": "PASS", "C": "BLOCK"}
        )
        consumer = self._consumer(inputs)
        lineage = self._lineage(consumer, inputs)
        document = self.evaluate(
            lineage_document=lineage,
            consumer_document=consumer,
            window_inputs=inputs,
        )
        self.assertEqual(lineage["status"], "BLOCK")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "RETURN_PANEL_LINEAGE")

    def test_missing_fixture_synthetic_fallback_and_incomplete_envelopes_are_unknown(self):
        missing = copy.deepcopy(self.payloads)
        missing["A"].pop("market_data_envelope")
        fixture = self._payloads(source_prefix="fixture_cache")
        synthetic = self._payloads(source_prefix="synthetic_fallback")
        incomplete = copy.deepcopy(self.payloads)
        incomplete["B"]["rows"][-1]["complete"] = False
        cases = {
            "missing_envelope": missing,
            "fixture_marker": fixture,
            "synthetic_fallback_marker": synthetic,
            "incomplete_row": incomplete,
        }
        for kind, payloads in cases.items():
            with self.subTest(kind=kind):
                document = self.evaluate(payloads=payloads)
                self.assertEqual(document["status"], "UNKNOWN")
                self.assertEqual(document["source_summaries"], [])

    def test_payload_row_tamper_without_envelope_update_is_unknown(self):
        payloads = copy.deepcopy(self.payloads)
        payloads["A"]["rows"][-1]["close"] *= 1.1
        document = self.evaluate(payloads=payloads)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("market_data_envelope_source_invalid", document["blockers"])

    def test_coherent_source_reseal_cannot_reuse_old_binding_or_lineage(self):
        payloads = copy.deepcopy(self.payloads)
        raw = {
            key: value
            for key, value in payloads["A"].items()
            if key != "market_data_envelope"
        }
        raw["rows"][-1]["close"] *= 1.01
        payloads["A"] = attach_market_data_envelope(raw, symbol="A", timeframe="1D")
        document = self.evaluate(payloads=payloads)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("market_data_envelope_binding_mismatch", document["blockers"])

    def test_misaligned_timestamp_grid_is_unknown(self):
        payloads = copy.deepcopy(self.payloads)
        raw = {
            key: value
            for key, value in payloads["C"].items()
            if key != "market_data_envelope"
        }
        raw["rows"][-1]["ts_ms"] += 86_400_000
        payloads["C"] = attach_market_data_envelope(raw, symbol="C", timeframe="1D")
        document = self.evaluate(payloads=payloads)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("market_data_envelope_source_invalid", document["blockers"])

    def test_wrong_binding_pin_and_resealed_provider_drift_are_unknown(self):
        wrong_pin = self.evaluate(expected_binding_hash="0" * 64)
        binding = copy.deepcopy(self.binding_preregistration)
        binding.pop("binding_preregistration_v5_hash")
        binding["source_bindings"][0]["provider"] = "other_provider"
        binding = seal_strict_canonical_document(
            binding,
            "binding_preregistration_v5_hash",
        )
        drift = self.evaluate(
            binding_preregistration=binding,
            expected_binding_hash=binding["binding_preregistration_v5_hash"],
        )
        for document in (wrong_pin, drift):
            self.assertEqual(document["status"], "UNKNOWN")
            self.assertEqual(document["source_summaries"], [])

    def test_boolean_synthetic_count_and_unknown_provider_alias_are_rejected(self):
        boolean_count = copy.deepcopy(self.source_bindings)
        boolean_count[0]["synthetic_rows"] = False
        unknown_provider = copy.deepcopy(self.source_bindings)
        unknown_provider[0]["provider"] = " UNKNOWN "
        for bindings in (boolean_count, unknown_provider):
            with self.subTest(provider=bindings[0]["provider"]):
                with self.assertRaises(subject.MarketDataEnvelopeBindingContractError):
                    subject.build_market_data_envelope_binding_preregistration_v5(
                        bindings,
                        expected_panel_hash=self.panel["panel_hash"],
                        expected_lineage_preregistration_v4_hash=(
                            self.lineage_preregistration[
                                "lineage_preregistration_v4_hash"
                            ]
                        ),
                    )

        payloads = copy.deepcopy(self.payloads)
        raw = {
            key: value
            for key, value in payloads["A"].items()
            if key != "market_data_envelope"
        }
        raw["source"] = "UNKNOWN"
        for row in raw["rows"]:
            row["source"] = "UNKNOWN"
        payloads["A"] = attach_market_data_envelope(
            raw,
            symbol="A",
            timeframe="1D",
        )
        with self.assertRaises(subject.MarketDataEnvelopeBindingContractError):
            subject.derive_common_return_panel_from_market_data_envelopes_v5(
                payloads
            )

    def test_exact_adapter_verifier_rejects_resealed_count_and_authority(self):
        document = self.evaluate()
        valid = subject.verify_market_data_envelope_binding_adapter_v5(
            document,
            self.binding_preregistration,
            self.payloads,
            self.lineage_preregistration,
            self.consumer_preregistration,
            self.source_preregistrations,
            self.lineage_document,
            self.consumer_document,
            self.window_inputs,
            expected_binding_preregistration_v5_hash=self.expected_binding_hash,
            strategy_id="trend",
            variant_id="envelope-v5",
            lane="RAW_EXCESS",
        )
        variants = []
        for mutate in (
            lambda item: item["summary"].__setitem__("source_symbol_count", 99),
            lambda item: item["authority"].__setitem__("paper_authorized", True),
        ):
            changed = copy.deepcopy(document)
            changed.pop("adapter_v5_hash")
            mutate(changed)
            variants.append(seal_strict_canonical_document(changed, "adapter_v5_hash"))
        self.assertEqual(valid["status"], "PASS")
        for changed in variants:
            receipt = subject.verify_market_data_envelope_binding_adapter_v5(
                changed,
                self.binding_preregistration,
                self.payloads,
                self.lineage_preregistration,
                self.consumer_preregistration,
                self.source_preregistrations,
                self.lineage_document,
                self.consumer_document,
                self.window_inputs,
                expected_binding_preregistration_v5_hash=self.expected_binding_hash,
                strategy_id="trend",
                variant_id="envelope-v5",
                lane="RAW_EXCESS",
            )
            self.assertEqual(receipt["status"], "BLOCK")

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        before = copy.deepcopy(
            (
                self.binding_preregistration,
                self.payloads,
                self.lineage_document,
                self.consumer_document,
                self.window_inputs,
            )
        )
        document = self.evaluate()
        after = (
            self.binding_preregistration,
            self.payloads,
            self.lineage_document,
            self.consumer_document,
            self.window_inputs,
        )
        self.assertEqual(after, before)
        self.assertNotIn("rows", document)
        self.assertNotIn("market_data_envelope", document)
        self.assertFalse(document["facts"]["raw_rows_embedded"])
        self.assertFalse(document["facts"]["provider_identity_authenticated"])


if __name__ == "__main__":
    unittest.main()
