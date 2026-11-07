"""Pure synthetic receipt comparisons: no model, server or workspace writes."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.services.terminal_ai_evidence import (
    SCHEMA, ai_evidence_binding, compare_ai_strategy, validate_ai_evidence,
)


class AiStrategyBindingTests(unittest.TestCase):
    def setUp(self):
        self.params = {"fast_window": 5, "slow_window": 20, "min_cash_pct": 10.0}
        self.context = {"engine_id": "terminal.causal-long-only-signals-v7", "strategy_id": "dual_ma",
                        "strategy_params": deepcopy(self.params)}
        self.data = {"id": "synthetic-input", "symbol": "SYNTHETIC", "bar": "1d", "meta": {"session": "regular"},
                     "rows": [{"ts_ms": 1000 + i * 1000, "open": 10, "high": 11, "low": 9,
                               "close": 10, "volume": 100} for i in range(30)]}
        rows = [{"ts": row["ts_ms"], **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}}
                for row in self.data["rows"]]
        self.evidence = {"schema_version": SCHEMA, "symbol": "SYNTHETIC", "bar": "1Dutc", "session": "regular",
                         "question": "Synthetic reference", "generated_at": 100000,
                         "input_identity": {"rows_sha256": sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                                            "row_count": 30, "first_ts": 1000, "last_ts": 30000,
                                            "source": "unverified-fixture", "price_basis": "RAW"},
                         "providers": [{"provider": "openai", "model": "synthetic-only", "content": "Synthetic text"}]}

    def binding(self, evidence=None, **changes):
        current = {**self.context, **changes}
        return ai_evidence_binding(evidence or self.evidence, self.data, current["strategy_id"],
                                   current["strategy_params"], current["engine_id"])

    def test_exact_explicit_rules_do_not_authenticate_source_or_model(self):
        self.evidence["strategy_context"] = deepcopy(self.context)
        self.assertEqual(validate_ai_evidence(self.evidence, self.data), self.evidence)
        binding = self.binding()
        self.assertEqual(binding["status"], "SAME_NUMERIC_ROWS")
        self.assertEqual(binding["strategy_binding"]["status"], "MATCH")
        self.assertFalse(binding["source_authenticated"])
        self.assertFalse(binding["model_receipt_authenticated"])
        self.assertFalse(binding["parameter_selection_allowed"])
        self.assertFalse(binding["order_allowed"])

    def test_edited_parameter_changes_only_the_rule_match(self):
        self.evidence["strategy_context"] = deepcopy(self.context)
        before = json.dumps(self.evidence, sort_keys=True)
        binding = self.binding(strategy_params={**self.params, "fast_window": 6})
        self.assertEqual(binding["status"], "SAME_NUMERIC_ROWS")
        self.assertEqual(binding["strategy_binding"]["status"], "MISMATCH")
        self.assertEqual(binding["strategy_binding"]["differing_parameters"], ["fast_window"])
        self.assertEqual(json.dumps(self.evidence, sort_keys=True), before)

    def test_same_rule_on_different_data_is_not_the_same_snapshot(self):
        self.evidence["strategy_context"] = deepcopy(self.context)
        self.evidence["input_identity"]["rows_sha256"] = "0" * 64
        binding = self.binding()
        self.assertEqual(binding["status"], "DIFFERENT_SNAPSHOT")
        self.assertEqual(binding["strategy_binding"]["status"], "MATCH")

    def test_legacy_receipt_stays_unchanged_and_rule_identity_is_unknown(self):
        before = json.dumps(self.evidence, sort_keys=True)
        old = validate_ai_evidence(self.evidence, self.data)
        binding = self.binding(old)
        self.assertEqual(binding["strategy_binding"]["status"], "UNKNOWN")
        self.assertIsNone(binding["strategy_binding"]["analysis_context"])
        self.assertEqual(len(binding["strategy_binding"]["missing_fields"]), 3)
        self.assertEqual(json.dumps(old, sort_keys=True), before)
        self.assertNotIn("strategy_context", old)

    def test_partial_receipt_and_missing_parameter_never_get_task_defaults(self):
        for context in ({}, {"strategy_id": "dual_ma"}, {**self.context, "strategy_params": {"fast_window": 5}}):
            with self.subTest(context=context):
                receipt = {**self.evidence, "strategy_context": deepcopy(context)}
                self.assertEqual(validate_ai_evidence(receipt, self.data)["strategy_context"], context)
                binding = self.binding(receipt)["strategy_binding"]
                self.assertEqual(binding["status"], "UNKNOWN")
                self.assertTrue(binding["missing_fields"])
                self.assertEqual(binding["analysis_context"], context)

    def test_engine_and_strategy_identity_are_required_even_with_equal_numbers(self):
        self.evidence["strategy_context"] = deepcopy(self.context)
        for changes in ({"engine_id": "terminal.causal-long-only-signals-v6"}, {"strategy_id": "momentum"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.binding(**changes)["strategy_binding"]["status"], "MISMATCH")
        unknown = ai_evidence_binding(self.evidence, self.data)["strategy_binding"]
        self.assertEqual(unknown["status"], "UNKNOWN")

    def test_context_rejects_authority_unbounded_and_nonfinite_fields(self):
        contexts = [{**self.context, "order_allowed": True}, {**self.context, "engine_id": ""},
                    {**self.context, "strategy_params": {"bad": float("nan")}},
                    {**self.context, "strategy_params": {"bad": 10 ** 400}},
                    {**self.context, "strategy_params": {"bad": {"nested": True}}},
                    {**self.context, "strategy_params": {"__proto__": "bad"}}]
        for context in contexts:
            with self.subTest(context=context), self.assertRaises(ValueError):
                validate_ai_evidence({**self.evidence, "strategy_context": context}, self.data)

    def test_boolean_is_not_a_numeric_match_and_returned_context_is_detached(self):
        receipt = {"strategy_context": {**self.context, "strategy_params": {"flag": True}}}
        binding = compare_ai_strategy(receipt, "dual_ma", {"flag": 1}, self.context["engine_id"])
        self.assertEqual(binding["status"], "MISMATCH")
        binding["analysis_context"]["strategy_params"]["flag"] = False
        self.assertTrue(receipt["strategy_context"]["strategy_params"]["flag"])


if __name__ == "__main__":
    unittest.main()
