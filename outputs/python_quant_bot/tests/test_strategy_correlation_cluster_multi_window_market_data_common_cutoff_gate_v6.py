from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.application.market_data_envelope import (
    attach_market_data_envelope,
)
from exchange_terminal.services.strategy_correlation_cluster_multi_window_market_data_common_cutoff_gate_v6 import (
    CUTOFF_SEMANTICS,
    GATE_SCHEMA_VERSION,
    GATE_VERIFICATION_SCHEMA_VERSION,
    MarketDataCommonCutoffContractError,
    PREREGISTRATION_SCHEMA_VERSION,
    REQUIRED_WINDOW_LENGTHS,
    STATIC_FINGERPRINT,
    build_market_data_common_cutoff_preregistration_v6,
    evaluate_market_data_common_cutoff_gate_v6,
    verify_market_data_common_cutoff_gate_v6,
    verify_market_data_common_cutoff_preregistration_v6,
)
from exchange_terminal.services.strategy_correlation_cluster_multi_window_market_data_envelope_binding_adapter_v5 import (
    build_market_data_envelope_binding_preregistration_v5,
    derive_common_return_panel_from_market_data_envelopes_v5,
    market_data_envelope_source_bindings_v5,
)
from exchange_terminal.services.strategy_correlation_cluster_multi_window_return_panel_lineage_adapter_v4 import (
    build_multi_window_return_panel_lineage_preregistration_v4,
    derive_multi_window_matrices_from_return_panel_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_multi_window_market_data_envelope_binding_adapter_v5 import (
    MultiWindowMarketDataEnvelopeBindingAdapterV5Tests,
)


class MultiWindowMarketDataCommonCutoffGateV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v5_case = MultiWindowMarketDataEnvelopeBindingAdapterV5Tests(
            methodName="runTest"
        )
        self.v5_case.setUp()
        self.adapter_v5_document = self.v5_case.evaluate()
        self.adapter_v5_context = self._context(self.v5_case)
        self.source_bindings = market_data_envelope_source_bindings_v5(
            self.v5_case.payloads
        )
        self.provider_bindings = [
            {"symbol": item["symbol"], "provider": item["provider"]}
            for item in self.source_bindings
        ]
        self.cutoff_ts_ms = self.v5_case.payloads["A"]["rows"][-1]["ts_ms"]
        self.preregistration = self.build_preregistration()
        self.expected_preregistration_hash = self.preregistration[
            "common_cutoff_preregistration_v6_hash"
        ]

    @staticmethod
    def _context(case):
        return {
            "binding_preregistration": case.binding_preregistration,
            "market_data_payloads": case.payloads,
            "lineage_preregistration": case.lineage_preregistration,
            "consumer_preregistration": case.consumer_preregistration,
            "source_preregistrations": case.source_preregistrations,
            "lineage_adapter_document": case.lineage_document,
            "consumer_document": case.consumer_document,
            "window_inputs": case.window_inputs,
            "expected_binding_preregistration_v5_hash": case.expected_binding_hash,
            "strategy_id": "trend",
            "variant_id": "envelope-v5",
            "lane": "RAW_EXCESS",
        }

    def build_preregistration(self, **overrides):
        values = {
            "expected_symbols": sorted(self.v5_case.payloads),
            "expected_provider_bindings": self.provider_bindings,
            "expected_timeframe": self.v5_case.payloads["A"][
                "market_data_envelope"
            ]["timeframe"],
            "expected_observation_cutoff_ts_ms": self.cutoff_ts_ms,
            "expected_close_row_count": 131,
            "expected_return_row_count": 130,
            "required_window_lengths": list(REQUIRED_WINDOW_LENGTHS),
        }
        values.update(copy.deepcopy(overrides))
        return build_market_data_common_cutoff_preregistration_v6(**values)

    def evaluate(self, **overrides):
        values = {
            "preregistration": self.preregistration,
            "adapter_v5_document": self.adapter_v5_document,
            "adapter_v5_context": self.adapter_v5_context,
            "expected_common_cutoff_preregistration_v6_hash": (
                self.expected_preregistration_hash
            ),
        }
        values.update(overrides)
        return evaluate_market_data_common_cutoff_gate_v6(**values)

    def _coherently_shifted_v5_chain(self, shift_ms: int):
        case = MultiWindowMarketDataEnvelopeBindingAdapterV5Tests(
            methodName="runTest"
        )
        case.setUp()
        shifted_payloads = {}
        for symbol, payload in case.payloads.items():
            base = copy.deepcopy(payload)
            base.pop("market_data_envelope")
            for row in base["rows"]:
                row["ts_ms"] += shift_ms
            shifted_payloads[symbol] = attach_market_data_envelope(
                base,
                symbol=symbol,
                timeframe=payload["market_data_envelope"]["timeframe"],
            )

        panel = derive_common_return_panel_from_market_data_envelopes_v5(
            shifted_payloads
        )
        lineage_preregistration = (
            build_multi_window_return_panel_lineage_preregistration_v4(
                case.consumer_preregistration,
                case.source_preregistrations,
                expected_panel_hash=panel["panel_hash"],
                timeframe=panel["timeframe"],
                cutoff_date=panel["cutoff_date"],
            )
        )
        case.panel = panel
        case.lineage_preregistration = lineage_preregistration
        case.matrices = derive_multi_window_matrices_from_return_panel_v4(
            lineage_preregistration,
            case.consumer_preregistration,
            case.source_preregistrations,
            panel,
        )
        window_inputs = case._window_inputs()
        consumer = case._consumer(window_inputs)
        lineage = case._lineage(consumer, window_inputs)
        source_bindings = market_data_envelope_source_bindings_v5(
            shifted_payloads
        )
        binding_preregistration = (
            build_market_data_envelope_binding_preregistration_v5(
                source_bindings,
                expected_panel_hash=panel["panel_hash"],
                expected_lineage_preregistration_v4_hash=(
                    lineage_preregistration[
                        "lineage_preregistration_v4_hash"
                    ]
                ),
            )
        )
        case.payloads = shifted_payloads
        case.binding_preregistration = binding_preregistration
        case.expected_binding_hash = binding_preregistration[
            "binding_preregistration_v5_hash"
        ]
        case.window_inputs = window_inputs
        case.consumer_document = consumer
        case.lineage_document = lineage
        document = case.evaluate()
        return document, self._context(case)

    def test_exact_common_cutoff_gate_passes_without_authority(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_COMMON_NATIVE_CUTOFF_BOUND_RESEARCH_GATE_V6",
        )
        self.assertEqual(
            document["cutoff"]["expected_observation_cutoff_ts_ms"],
            self.cutoff_ts_ms,
        )
        self.assertEqual(
            document["cutoff"]["observed_common_cutoff_ts_ms"],
            self.cutoff_ts_ms,
        )
        self.assertEqual(document["cutoff"]["close_row_count"], 131)
        self.assertEqual(document["cutoff"]["return_row_count"], 130)
        self.assertEqual(len(document["datasets"]), 3)
        self.assertTrue(document["facts"]["common_timestamp_grid_recomputed"])
        self.assertTrue(
            document["facts"]["common_native_cutoff_matches_preregistration"]
        )
        self.assertFalse(document["facts"]["freshness_evaluated"])
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_gap_proof_shifted_v5_passes_but_old_cutoff_is_unknown(self):
        shifted_document, shifted_context = self._coherently_shifted_v5_chain(
            10 * 365 * 24 * 60 * 60 * 1000
        )
        self.assertEqual(shifted_document["status"], "PASS")
        result = self.evaluate(
            adapter_v5_document=shifted_document,
            adapter_v5_context=shifted_context,
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("common_native_cutoff_exact", result["blockers"])
        self.assertNotEqual(
            result["cutoff"]["observed_common_cutoff_ts_ms"],
            self.cutoff_ts_ms,
        )

    def test_one_millisecond_cutoff_drift_is_unknown(self):
        preregistration = self.build_preregistration(
            expected_observation_cutoff_ts_ms=self.cutoff_ts_ms + 1
        )
        result = self.evaluate(
            preregistration=preregistration,
            expected_common_cutoff_preregistration_v6_hash=preregistration[
                "common_cutoff_preregistration_v6_hash"
            ],
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("common_native_cutoff_exact", result["blockers"])

    def test_preregistered_provider_drift_is_unknown(self):
        bindings = copy.deepcopy(self.provider_bindings)
        bindings[0]["provider"] = "different_fixture_provider"
        preregistration = self.build_preregistration(
            expected_provider_bindings=bindings
        )
        result = self.evaluate(
            preregistration=preregistration,
            expected_common_cutoff_preregistration_v6_hash=preregistration[
                "common_cutoff_preregistration_v6_hash"
            ],
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("provider_binding_exact", result["blockers"])

    def test_preregistration_rejects_boolean_counts_and_unknown_provider(self):
        invalid_values = [
            {"expected_observation_cutoff_ts_ms": False},
            {"expected_close_row_count": True},
            {"expected_return_row_count": False},
            {"expected_return_row_count": 129},
            {"required_window_lengths": [20, 60]},
            {"expected_timeframe": "1d"},
        ]
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(
                MarketDataCommonCutoffContractError
            ):
                self.build_preregistration(**overrides)

        bindings = copy.deepcopy(self.provider_bindings)
        bindings[0]["provider"] = " UNKNOWN "
        with self.assertRaises(MarketDataCommonCutoffContractError):
            self.build_preregistration(expected_provider_bindings=bindings)

    def test_preregistration_rejects_symbol_order_and_provider_shape(self):
        with self.assertRaises(MarketDataCommonCutoffContractError):
            self.build_preregistration(expected_symbols=["B", "A", "C"])
        bindings = copy.deepcopy(self.provider_bindings)
        bindings[0]["extra"] = True
        with self.assertRaises(MarketDataCommonCutoffContractError):
            self.build_preregistration(expected_provider_bindings=bindings)

    def test_payload_or_adapter_tamper_is_unknown(self):
        context = copy.deepcopy(self.adapter_v5_context)
        context["market_data_payloads"]["A"]["rows"][-1]["complete"] = False
        result = self.evaluate(adapter_v5_context=context)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("adapter_v5_exact", result["blockers"])

        adapter = copy.deepcopy(self.adapter_v5_document)
        adapter["authority"]["current_admission_allowed"] = True
        result = self.evaluate(adapter_v5_document=adapter)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("adapter_v5_exact", result["blockers"])

    def test_preregistration_verifier_requires_exact_hash_and_rebuild(self):
        verification = verify_market_data_common_cutoff_preregistration_v6(
            self.preregistration,
            expected_common_cutoff_preregistration_v6_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        tampered = copy.deepcopy(self.preregistration)
        tampered["facts"]["freshness_policy_defined"] = True
        tampered = seal_strict_canonical_document(
            tampered,
            "common_cutoff_preregistration_v6_hash",
        )
        verification = verify_market_data_common_cutoff_preregistration_v6(
            tampered,
            expected_common_cutoff_preregistration_v6_hash=tampered[
                "common_cutoff_preregistration_v6_hash"
            ],
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_gate_verifier_rejects_resealed_cutoff_and_authority_tamper(self):
        document = self.evaluate()
        verification = verify_market_data_common_cutoff_gate_v6(
            document,
            self.preregistration,
            self.adapter_v5_document,
            self.adapter_v5_context,
            expected_common_cutoff_preregistration_v6_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        variants = []
        cutoff = copy.deepcopy(document)
        cutoff["cutoff"]["observed_common_cutoff_ts_ms"] += 1
        variants.append(cutoff)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for variant in variants:
            with self.subTest(variant=variant):
                resealed = seal_strict_canonical_document(
                    variant,
                    "common_cutoff_gate_v6_hash",
                )
                verification = verify_market_data_common_cutoff_gate_v6(
                    resealed,
                    self.preregistration,
                    self.adapter_v5_document,
                    self.adapter_v5_context,
                    expected_common_cutoff_preregistration_v6_hash=(
                        self.expected_preregistration_hash
                    ),
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["gate_decision"], "UNKNOWN")

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        preregistration = copy.deepcopy(self.preregistration)
        adapter = copy.deepcopy(self.adapter_v5_document)
        context = copy.deepcopy(self.adapter_v5_context)
        document = self.evaluate()
        self.assertEqual(preregistration, self.preregistration)
        self.assertEqual(adapter, self.adapter_v5_document)
        self.assertEqual(context, self.adapter_v5_context)
        encoded = json.dumps(document, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            '"rows":',
            '"market_data_payloads":',
            '"window_inputs":',
            '"consumer_document":',
            '"market_data_envelope":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(document["facts"]["raw_rows_embedded"])

    def test_claims_remain_calibrated_and_authority_locked(self):
        document = self.evaluate()
        self.assertEqual(document["cutoff"]["cutoff_semantics"], CUTOFF_SEMANTICS)
        self.assertFalse(document["facts"]["freshness_policy_defined"])
        self.assertFalse(
            document["facts"]["external_preregistration_time_authenticated"]
        )
        self.assertFalse(document["facts"]["provider_identity_authenticated"])
        self.assertFalse(
            document["facts"]["provider_dataset_content_attested"]
        )
        for key, value in document["authority"].items():
            if key == "descriptive_only":
                self.assertTrue(value)
            else:
                self.assertFalse(value)

    def test_schema_fingerprint_and_window_policy_are_locked(self):
        document = self.evaluate()
        verification = verify_market_data_common_cutoff_gate_v6(
            document,
            self.preregistration,
            self.adapter_v5_document,
            self.adapter_v5_context,
            expected_common_cutoff_preregistration_v6_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(
            self.preregistration["schema_version"],
            PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["schema_version"], GATE_SCHEMA_VERSION)
        self.assertEqual(
            verification["schema_version"],
            GATE_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            document["cutoff"]["required_window_lengths"],
            [20, 60, 120],
        )


if __name__ == "__main__":
    unittest.main()
