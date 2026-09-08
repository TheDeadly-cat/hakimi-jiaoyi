"""Exercise the legacy UI's config producer against the installed canonical reader."""
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from hakimi_research.config import BotConfig


ROOT = Path(__file__).resolve().parents[2]


class Sidebar:
    def header(self, *_args): pass
    def info(self, *_args): pass
    def caption(self, *_args): pass
    def selectbox(self, _label, options, index=0): return options[index]
    def text_input(self, _label, value): return value
    def number_input(self, _label, **kwargs): return kwargs['value']
    def slider(self, _label, _minimum, _maximum, value, _step): return value
    def toggle(self, _label, *, value): return value


class DashboardConfigCompatibility(unittest.TestCase):
    def test_default_and_archived_execution_values_load_with_execution_disabled(self):
        # Compile only the real producer: importing the whole Streamlit app would
        # initialize UI/provider code outside this config compatibility contract.
        path = ROOT / 'outputs/python_quant_bot/dashboard_app.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'build_config_from_ui')
        namespace = {'Any': object, 'st': SimpleNamespace(sidebar=Sidebar()),
                     'STRATEGY_REGISTRY': {'dual_ma': object()},
                     'strategy_params_form': lambda _name, params: params}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        for broker, exchange in [('research_simulator', 'disabled'), ('paper', 'okx')]:
            with self.subTest(broker=broker), tempfile.TemporaryDirectory() as folder:
                raw = json.loads((ROOT / 'outputs/python_quant_bot/config.example.json').read_text(encoding='utf-8'))
                raw['execution'].update(broker=broker, exchange=exchange, live_trading_enabled=True)
                produced = namespace['build_config_from_ui'](raw)
                config_path = Path(folder) / 'config.json'
                config_path.write_text(json.dumps(produced), encoding='utf-8')
                config = BotConfig.from_file(config_path)
                self.assertEqual(config.execution.broker, 'research_simulator')
                self.assertEqual(config.execution.exchange, 'disabled')
                self.assertIs(config.execution.live_trading_enabled, False)
                self.assertEqual(config.mode, 'backtest')


if __name__ == '__main__':
    unittest.main()
