from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.backtest import (  # noqa: E402
    BacktestEngine,
    build_backtest_reproducibility,
)
from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.risk import RiskManager  # noqa: E402
from hakimi_research.strategies.templates import build_strategy  # noqa: E402
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    synthetic_frame,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_REPRODUCIBILITY_HASH = (
    "a33c9a8baba1ccc0c41dc9fcb77fbc3f75419a8e9ef814249f32ed0d4a0f2e07"
)


def _build(
    frame,
    value,
    experiment_context,
    max_volume_participation_rate=None,
):
    strategy = build_strategy(value.strategy.name, value.strategy.params)
    expected = build_backtest_reproducibility(
        frame,
        value,
        strategy,
        experiment_context=experiment_context,
        max_volume_participation_rate=max_volume_participation_rate,
    )
    engine = BacktestEngine(
        config=value,
        strategy=strategy,
        risk_manager=RiskManager(value.risk),
        experiment_context=experiment_context,
        max_volume_participation_rate=max_volume_participation_rate,
    )
    return expected, engine._reproducibility(frame)


class BacktestReproducibilityBuilderV1Tests(unittest.TestCase):
    def test_score_start_accounting_versions_identity_without_overwriting_v1_evidence(self) -> None:
        expected, delegated = _build(synthetic_frame(), config(), context())

        self.assertEqual(expected, delegated)
        self.assertNotEqual(
            canonical_payload_hash(expected),
            BASELINE_REPRODUCIBILITY_HASH,
        )
        self.assertEqual(expected["scoring"]["metric_semantics_version"], "research-accounting-score-start-v2")
        self.assertEqual(expected["execution_model"], "signal-close-next-open-ohlc-v5")
        repeated, _ = _build(synthetic_frame(), config(), context())
        self.assertEqual(expected, repeated)

    def test_all_identity_inputs_are_rebuilt_without_running_backtest(self) -> None:
        base_frame = synthetic_frame()
        base_config = config()
        base_context = context()
        variants = [("base", base_frame, base_config, base_context, None)]

        changed_data = base_frame.copy()
        changed_data.iloc[-1, changed_data.columns.get_loc("close")] += 0.125
        variants.append((
            "data",
            changed_data,
            deepcopy(base_config),
            deepcopy(base_context),
            None,
        ))

        changed_fee = deepcopy(base_config)
        changed_fee.execution.fee_rate += 0.0005
        variants.append((
            "fee",
            base_frame,
            changed_fee,
            deepcopy(base_context),
            None,
        ))

        changed_params = deepcopy(base_config)
        changed_params.strategy.params = {
            **changed_params.strategy.params,
            "fast": 9,
        }
        variants.append((
            "params",
            base_frame,
            changed_params,
            deepcopy(base_context),
            None,
        ))

        changed_seed = deepcopy(base_context)
        changed_seed["random_seed"] = 1
        variants.append((
            "seed",
            base_frame,
            deepcopy(base_config),
            changed_seed,
            None,
        ))
        variants.append((
            "liquidity_cap",
            base_frame,
            deepcopy(base_config),
            deepcopy(base_context),
            0.125,
        ))

        observed = []
        for name, frame, value, experiment_context, cap in variants:
            with self.subTest(name=name):
                expected, delegated = _build(
                    frame,
                    value,
                    experiment_context,
                    cap,
                )
                self.assertEqual(expected, delegated)
                observed.append(expected["run_hash"])

        self.assertEqual(len(set(observed)), len(variants))

    def test_current_consumers_do_not_bypass_public_builder(self) -> None:
        source = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "backtest.py"
        ).read_text(encoding="utf-8")

        self.assertIn("return build_backtest_reproducibility(", source)
        self.assertEqual(source.count("canonical_rows = ["), 1)


if __name__ == "__main__":
    unittest.main()
