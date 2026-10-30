"""Independent arithmetic anchors, pandas oracle, and Python/JS parity."""
import json
import math
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import pandas as pd

from exchange_terminal.services import indicator_math as formulas
from exchange_terminal.services.strategy_signals import rolling_strategy_signal, _average_true_range, strategy_signal_fingerprint


class IndicatorContractTests(unittest.TestCase):
    def test_known_values_and_full_warmup(self):
        self.assertEqual(formulas.sma([1, 2, 3, 4], 3), [None, None, 2, 3])
        self.assertEqual(formulas.ema([1, 2, 3], 3), [1, 1.5, 2.25])
        self.assertAlmostEqual(formulas.bollinger([1, 2, 3], 3)[-1]["upper"], 2 + 2 * math.sqrt(2 / 3))
        self.assertEqual(formulas.rsi([2] * 5, 3), [None, None, None, 50, 50])
        self.assertEqual(formulas.rsi([1, 2, 3, 4], 3)[-1], 100)
        self.assertEqual(formulas.rsi([4, 3, 2, 1], 3)[-1], 0)
        self.assertAlmostEqual(formulas.rsi([1, 3, 2, 4], 3)[-1], 80)
        rows = [{"high": 11, "low": 9, "close": 10}, {"high": 14, "low": 12, "close": 13},
                {"high": 13, "low": 10, "close": 11}, {"high": 12, "low": 10, "close": 11}]
        self.assertEqual(formulas.atr(rows, 3), [None, None, None, 3])
        self.assertEqual(_average_true_range(rows, 3), 3)
        self.assertEqual(formulas.momentum([2, 3, 4, 5], 3)[-1], 1.5)

    def test_native_formulas_match_independent_pandas_reference(self):
        source = pd.Series([100 + i * .07 + math.sin(i / 3) for i in range(150)])
        values = source.tolist()
        pd.testing.assert_series_equal(pd.Series(formulas.sma(values, 20)), source.rolling(20).mean())
        pd.testing.assert_series_equal(pd.Series(formulas.ema(values, 12)), source.ewm(span=12, adjust=False).mean())
        band = formulas.bollinger(values)
        pd.testing.assert_series_equal(pd.Series([v["upper"] if v else None for v in band]),
                                      source.rolling(20).mean() + 2 * source.rolling(20).std(ddof=0))
        line, signal, hist = formulas.macd(values)
        expected = source.ewm(span=12, adjust=False).mean() - source.ewm(span=26, adjust=False).mean()
        pd.testing.assert_series_equal(pd.Series(line), expected)
        pd.testing.assert_series_equal(pd.Series(signal), expected.ewm(span=9, adjust=False).mean())
        pd.testing.assert_series_equal(pd.Series(hist), expected - expected.ewm(span=9, adjust=False).mean())

    def test_missing_values_do_not_forward_fill_or_seed_fake_signals(self):
        values = [1, 2, None, 4, 5, 6]
        self.assertEqual(formulas.sma(values, 3), [None, None, None, None, None, 5])
        self.assertEqual(formulas.ema(values, 3), [1, 1.5, None, 4, 4.5, 5.25])
        self.assertEqual(formulas.rsi(values, 3), [None] * 6)
        self.assertEqual(formulas.momentum(values, 3), [None] * 6)
        self.assertIsNone(formulas.bollinger(values, 3)[4])
        signal = rolling_strategy_signal("rsi", [10.0] * 40, 10, True)
        self.assertEqual(signal["action"], "HOLD", "flat prices must not produce an overbought exit")
        signal = rolling_strategy_signal("bollinger", [10.0] * 40, 1, False, params={"window": 60})
        self.assertEqual(signal["reason"], "insufficient_history")
        self.assertEqual(formulas.sma([1e308, 1e308], 2), [None, None])
        self.assertEqual(formulas.bollinger([1e308, -1e308], 2), [None, None])

    def test_dependency_only_change_requires_reload_before_claiming_new_identity(self):
        import test_quant_bot_backtest as fixtures
        from quant_bot.backtest import BacktestEngine
        from quant_bot.risk import RiskManager
        config = fixtures.QuantBotBacktestTests().config()
        engine = BacktestEngine(config, fixtures.OneShotStrategy(), RiskManager(config.risk))
        frame = fixtures.price_frame(40)
        before_cli = engine._reproducibility(frame)
        before_native = strategy_signal_fingerprint("macd", {})
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw + b"\n# dependency changed" if path == Path(formulas.__file__) else raw
        with patch.object(Path, "read_bytes", changed):
            # The canonical CLI retains its own formulas and source identity.
            self.assertEqual(engine._reproducibility(frame)["run_hash"], before_cli["run_hash"])
            with self.assertRaisesRegex(ValueError, "restart_required"):
                strategy_signal_fingerprint("macd", {})
            from hashlib import sha256
            with patch.object(formulas, "LOADED_SOURCE_SHA256", sha256(changed(Path(formulas.__file__))).hexdigest()):
                self.assertEqual(engine._reproducibility(frame)["run_hash"], before_cli["run_hash"])
                self.assertNotEqual(strategy_signal_fingerprint("macd", {}), before_native)

    def test_javascript_parity_and_every_prefix_is_causal(self):
        values = [100 + math.sin(i / 2) * 7 + i / 10 for i in range(125)]
        values[31] = None
        rows = [{"high": v + 2, "low": v - 1, "close": v} if v is not None
                else {"high": None, "low": None, "close": None} for v in values]
        expected = {"sma": formulas.sma(values, 7), "ema": formulas.ema(values, 7),
                    "bollinger": formulas.bollinger(values, 7), "macd": formulas.macd(values),
                    "rsi": formulas.rsi(values, 7), "momentum": formulas.momentum(values, 7),
                    "atr": formulas.atr(rows, 7)}
        script = Path(__file__).parents[1] / "exchange_terminal/static/indicator_math.js"
        code = """const fs = require('node:fs'), f = require(process.argv[1]);
const p = JSON.parse(fs.readFileSync(0, 'utf8')), v = p.values;
process.stdout.write(JSON.stringify({sma:f.sma(v,7),ema:f.ema(v,7),bollinger:f.bollinger(v,7),
macd:f.macd(v),rsi:f.rsi(v,7),momentum:f.momentum(v,7),atr:f.atr(p.rows,7)}));"""
        result = subprocess.run(["node", "-e", code, str(script)], input=json.dumps({"values": values, "rows": rows}),
                                capture_output=True, text=True, check=True)
        actual = json.loads(result.stdout)
        def same(a, b):
            if isinstance(a, (list, tuple)):
                self.assertEqual(len(a), len(b))
                for x, y in zip(a, b):
                    same(x, y)
            elif isinstance(a, dict):
                self.assertEqual(set(a), set(b))
                for key in a:
                    same(a[key], b[key])
            elif a is None:
                self.assertIsNone(b)
            else:
                self.assertAlmostEqual(a, b, places=10)
        same(expected, actual)
        for end in range(1, len(values) + 1):
            for name in ("sma", "ema", "bollinger", "rsi", "momentum"):
                same(expected[name][:end], getattr(formulas, name)(values[:end], 7))
            same(expected["atr"][:end], formulas.atr(rows[:end], 7))


if __name__ == "__main__":
    unittest.main()
