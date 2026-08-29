from __future__ import annotations

import unittest

from exchange_terminal.domain.contracts import build_candle_decision_id


class CandleDecisionIdDelimiterLockV1Tests(unittest.TestCase):
    @staticmethod
    def _build(**overrides) -> str:
        values = {
            "strategy": "alpha",
            "symbol": "BTC-USDT",
            "timeframe": "1D",
            "candle_close_time": "2026-08-25T00:00:00Z",
            "action": "BUY",
            "strategy_version": "v1",
        }
        values.update(overrides)
        return build_candle_decision_id(**values)

    def test_existing_canonical_id_bytes_are_unchanged(self) -> None:
        self.assertEqual(
            self._build(),
            "strategy:alpha|symbol:btc-usdt|timeframe:1d|candle:2026-08-25T00:00:00Z|action:BUY|version:v1",
        )

    def test_previously_colliding_delimiter_inputs_are_both_rejected(self) -> None:
        adversarial = (
            {"strategy": "alpha|symbol:beta", "symbol": "gamma"},
            {"strategy": "alpha", "symbol": "beta|symbol:gamma"},
        )
        for overrides in adversarial:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "candle_decision_id_"):
                    self._build(**overrides)

    def test_pipe_is_rejected_in_every_component(self) -> None:
        fields = (
            "strategy",
            "symbol",
            "timeframe",
            "candle_close_time",
            "action",
            "strategy_version",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, f"candle_decision_id_{field}_invalid"):
                    self._build(**{field: "left|right"})

    def test_controls_outer_candle_whitespace_and_non_strings_are_rejected(self) -> None:
        invalid = (
            {"strategy": "alpha\nforged"},
            {"symbol": "btc\x00usdt"},
            {"timeframe": "1D\x7f"},
            {"candle_close_time": " 2026-08-25T00:00:00Z"},
            {"action": "BUY\rSELL"},
            {"strategy_version": "v1\u2028v2"},
            {"strategy": 1},
            {"candle_close_time": 1_800_000_000},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "candle_decision_id_"):
                    self._build(**overrides)

    def test_component_lengths_are_bounded(self) -> None:
        invalid = (
            {"strategy": "a" * 129},
            {"symbol": "s" * 129},
            {"timeframe": "t" * 129},
            {"candle_close_time": "c" * 257},
            {"action": "a" * 129},
            {"strategy_version": "v" * 129},
        )
        for overrides in invalid:
            with self.subTest(field=next(iter(overrides))):
                with self.assertRaisesRegex(ValueError, "_too_long"):
                    self._build(**overrides)

    def test_legacy_case_trim_and_empty_fallback_normalization_remains_stable(self) -> None:
        self.assertEqual(
            self._build(
                strategy=" Alpha ",
                symbol=" BTC-USDT ",
                timeframe=" 1D ",
                action=" buy ",
                strategy_version=" v2 ",
            ),
            "strategy:alpha|symbol:btc-usdt|timeframe:1d|candle:2026-08-25T00:00:00Z|action:BUY|version:v2",
        )
        self.assertEqual(
            self._build(
                strategy="",
                symbol="",
                timeframe="",
                action="",
                strategy_version=None,
            ),
            "strategy:legacy|symbol:unknown|timeframe:unknown|candle:2026-08-25T00:00:00Z|action:NONE|version:v1",
        )


if __name__ == "__main__":
    unittest.main()
