from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.benchmarks import (  # noqa: E402
    FIXED_BASELINE_MATRIX_VERSION,
    build_fixed_benchmark,
    fixed_benchmark_specs,
)
from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.models import Portfolio  # noqa: E402
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


EXPECTED_IDS = [
    "CASH",
    "ENGINE_BUY_AND_HOLD",
    "FIXED_DUAL_MA",
    "FIXED_BREAKOUT",
    "HASH_NO_SKILL",
]


class StringAlias(str):
    pass


class IntAlias(int):
    pass


class FixedBaselineMatrixV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = synthetic_frame()
        cls.config = config()
        cls.protocol = protocol(cls.frame, cls.config)
        cls.report = build_frozen_evaluation_report(
            cls.protocol,
            cls.frame,
            cls.config,
            experiment_context=context(),
        )

    def test_specs_are_fresh_preregistered_exact_native_values(self) -> None:
        first = fixed_benchmark_specs(17)
        second = fixed_benchmark_specs(17)
        self.assertEqual([item["benchmark_id"] for item in first], EXPECTED_IDS)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        first[-1]["params"]["random_seed"] = 99
        self.assertEqual(second[-1]["params"]["random_seed"], 17)

    def test_factory_identity_and_params_match_specs(self) -> None:
        for spec in fixed_benchmark_specs(17):
            strategy = build_fixed_benchmark(spec["benchmark_id"], 17)
            self.assertEqual(strategy.name, spec["strategy_name"])
            self.assertEqual(strategy.version, spec["version"])
            self.assertEqual(strategy.params, spec["params"])

    def test_factory_rejects_aliases_unknown_ids_and_invalid_seeds(self) -> None:
        for benchmark_id in (None, 1, "", "UNKNOWN", StringAlias("CASH")):
            with self.assertRaises(ValueError):
                build_fixed_benchmark(benchmark_id, 17)  # type: ignore[arg-type]
        for random_seed in (None, True, -1, 2_147_483_648, IntAlias(17)):
            with self.assertRaises(ValueError):
                fixed_benchmark_specs(random_seed)  # type: ignore[arg-type]

    def test_signal_generation_is_repeatable_and_seed_bound(self) -> None:
        portfolio = Portfolio(cash=10_000.0)
        frame = self.frame.iloc[:30]
        for benchmark_id in EXPECTED_IDS:
            first = build_fixed_benchmark(benchmark_id, 17).generate_signal(frame, portfolio)
            second = build_fixed_benchmark(benchmark_id, 17).generate_signal(frame, portfolio)
            self.assertEqual(first, second)
        seed_17 = build_fixed_benchmark("HASH_NO_SKILL", 17)
        seed_18 = build_fixed_benchmark("HASH_NO_SKILL", 18)
        actions_17 = [
            seed_17.generate_signal(self.frame.iloc[:end], portfolio).action.value
            for end in range(1, len(self.frame) + 1)
        ]
        actions_18 = [
            seed_18.generate_signal(self.frame.iloc[:end], portfolio).action.value
            for end in range(1, len(self.frame) + 1)
        ]
        self.assertNotEqual(actions_17, actions_18)

    def test_protocol_binds_complete_versioned_specs(self) -> None:
        self.assertEqual(
            [item["benchmark_id"] for item in self.protocol["benchmarks"]],
            EXPECTED_IDS,
        )
        for spec in self.protocol["benchmarks"]:
            self.assertEqual(spec["matrix_version"], FIXED_BASELINE_MATRIX_VERSION)
            core = {key: value for key, value in spec.items() if key != "spec_hash"}
            self.assertEqual(spec["spec_hash"], canonical_payload_hash(core))

    def test_report_binds_full_role_cost_baseline_matrix(self) -> None:
        expected = {
            (role, benchmark_id, scenario_id)
            for role in ("VALIDATION", "FROZEN_TEST")
            for benchmark_id in EXPECTED_IDS
            for scenario_id in ("BASE", "DOUBLE_COST", "TRIPLE_COST")
        }
        observed = {
            (item["role"], item["benchmark_id"], item["scenario_id"])
            for item in self.report["benchmark_runs"]
        }
        self.assertEqual(observed, expected)
        self.assertEqual(len(self.report["benchmark_runs"]), 30)
        specs = {
            item["benchmark_id"]: item
            for item in self.protocol["benchmarks"]
        }
        for record in self.report["benchmark_runs"]:
            spec = specs[record["benchmark_id"]]
            self.assertEqual(record["benchmark_spec_hash"], spec["spec_hash"])
            self.assertEqual(record["benchmark_params"], spec["params"])
            self.assertEqual(
                record["result"]["reproducibility"]["param_hash"],
                canonical_payload_hash(spec["params"]),
            )
        self.assertTrue(all(value is False for value in self.report["authority"].values()))

    def test_spec_and_matrix_tampering_fail_closed(self) -> None:
        tampered = deepcopy(self.report)
        tampered["benchmark_runs"][0]["benchmark_params"] = {"forged": True}
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                tampered,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )
        incomplete = deepcopy(self.report)
        incomplete["benchmark_runs"].pop()
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                incomplete,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )
        malformed_fields = (
            ("result", []),
            ("experiment_manifest", []),
            ("benchmark_params", []),
            ("role", []),
            ("benchmark_id", []),
            ("scenario_id", []),
        )
        for field, value in malformed_fields:
            malformed = deepcopy(self.report)
            malformed["benchmark_runs"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    verify_frozen_evaluation_report(
                        malformed,
                        self.protocol,
                        self.frame,
                        self.config,
                        experiment_context=context(),
                    )

    def test_markdown_exposes_benchmark_and_cost_identity_neutrally(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("| Role | Benchmark | Cost scenario |", rendered)
        for benchmark_id in EXPECTED_IDS:
            self.assertIn(f"| {benchmark_id} |", rendered)
        self.assertNotIn(
            "VOLATILITY_MATCHED_EXECUTION_BASELINE_NOT_AVAILABLE",
            rendered,
        )
        self.assertIn(
            "Prior-window volatility-target research-simulator benchmark",
            rendered,
        )
        self.assertNotIn("READY", rendered)

    def test_deterministic_source_envelope_includes_baseline_producer(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/benchmarks.py"', source)


if __name__ == "__main__":
    unittest.main()
