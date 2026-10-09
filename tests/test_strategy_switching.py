import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.offline_app import check_task, run_task
from hakimi_research.strategy_registry import definition, new_task_parameters
from hakimi_research.task_manager import create_family, describe_task, read_family, revise_family, version_options, change_state
from hakimi_research.trade_cli import configuration_form, default_risk, initialize_demo, main, wizard


class StrategySwitchingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hakimi-strategy-switch-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / 'workspace'
        initialize_demo(self.workspace)
        self.original = version_options(self.workspace / 'tasks/event.json')
        self.original['params'].pop('take_profit_pct')
        self.family = self.workspace / 'tasks/managed'
        create_family(self.family, **self.original)

    def cli(self, *arguments, expected=0):
        with redirect_stdout(io.StringIO()) as stream:
            result = main(list(map(str, arguments)))
        self.assertEqual(result, expected, stream.getvalue())
        return json.loads(stream.getvalue())

    def target(self, key):
        params = ({'target_position_pct': .3} if key == 'price.buy_and_hold@1' else
            dict(fast_window=2, slow_window=4, position_pct=.2, stop_loss_pct=.02, take_profit_pct=.05))
        risk = default_risk(key)
        if key != 'price.buy_and_hold@1':
            risk.update(max_position_pct=.3, max_single_loss_pct=.025, max_daily_loss_pct=.1, min_cash_pct=.15)
        return params, risk

    def files(self, key):
        params, risk = self.target(key)
        paths = []
        for name, document in [('parameters', params), ('risk', risk)]:
            path = self.root / (key + '-' + name + '.json')
            path.write_text(json.dumps(document), encoding='utf-8')
            paths.extend(['--' + name, str(path)])
        return paths

    def frozen(self, *directories):
        return {path: path.read_bytes() for directory in directories for path in directory.rglob('*') if path.is_file()}

    def assert_frozen(self, before):
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw, str(path))

    def assert_state(self, before):
        after = read_family(self.family)
        for key in ('family_id', 'state', 'revisions', 'selected_revision', 'sequence', 'event_hash'):
            self.assertEqual(after[key], before[key], key)

    def switched(self, key):
        report = run_task(self.family)
        change_state(self.family, 'PAUSED')
        before = read_family(self.family)
        old = self.frozen(self.family, report)
        view = self.cli('task-revise', '--task', self.family, '--strategy', key, *self.files(key))
        self.assertEqual(view['family_id'], before['family_id'])
        self.assertEqual(view['state'], 'PAUSED')
        self.assertEqual(len(view['revisions']), 2)
        self.assertNotEqual(view['selected_revision'], before['selected_revision'])
        checked = check_task(self.family, inspect_only=True)
        self.assertEqual(checked['semantics']['strategy'], key)
        self.assertIsNone(checked['context_path'])
        self.assertIsNone(checked['semantics']['event_context_hash'])
        self.assertIsNone(json.loads(checked['task_path'].read_text(encoding='utf-8'))['event_context'])
        self.assertFalse((checked['task_path'].parent / 'inputs/event-context.json').exists())
        self.assertEqual(checked['semantics']['experiment']['schema_version'], 'us-equity-experiment-spec-v1')
        self.assertEqual(checked['semantics']['experiment']['strategy']['params'], self.target(key)[0])
        self.assertEqual(checked['semantics']['experiment']['risk'], self.target(key)[1])
        for name in ('snapshot', 'score_start', 'score_end', 'initial_cash', 'fee_rate', 'slippage_pct'):
            value = version_options(self.family)[name]
            if name == 'snapshot':
                self.assertEqual(value.read_bytes(), self.original[name].read_bytes())
            else:
                self.assertEqual(value, self.original[name], name)
        self.assert_frozen(old)

    def test_cli_event_to_dual_ma_keeps_same_family_pause_inputs_and_report(self):
        self.switched('price.dual_ma@1')

    def test_cli_event_to_buy_and_hold_keeps_same_family_pause_inputs_and_report(self):
        self.switched('price.buy_and_hold@1')

    def test_explicit_conflicting_event_input_is_rejected_without_a_commit(self):
        change_state(self.family, 'PAUSED')
        before, old = read_family(self.family), self.frozen(self.family)
        for key in ('price.dual_ma@1', 'price.buy_and_hold@1'):
            with self.subTest(target=key):
                result = self.cli('task-revise', '--task', self.family, '--strategy', key, *self.files(key),
                    '--event-context', self.original['event_context'], expected=1)
                self.assertIn('price_strategy_must_not_silently_use_event_inputs', result['error'])
                self.assert_state(before)
                self.assert_frozen(old)

    def test_reverse_switch_requires_event_input_and_accepts_an_explicit_valid_one(self):
        for key in ('price.dual_ma@1', 'price.buy_and_hold@1'):
            with self.subTest(source=key):
                self.family = self.workspace / 'tasks' / key.replace('.', '-').replace('@', '-')
                params, risk = self.target(key)
                create_family(self.family, **dict(self.original, strategy=key, params=params, risk=risk, event_context=None))
                change_state(self.family, 'PAUSED')
                before, old = read_family(self.family), self.frozen(self.family)
                arguments = ('task-revise', '--task', self.family, '--strategy', 'event.earnings_schedule@1',
                    *self.files('event.earnings_schedule@1'))
                rejected = self.cli(*arguments, expected=1)
                self.assertIn('event_strategy_context_required', rejected['error'])
                self.assert_state(before)
                self.assert_frozen(old)
                self.cli(*arguments, '--event-context', self.original['event_context'])
                self.assertEqual(read_family(self.family)['state'], 'PAUSED')
                self.assertEqual(len(read_family(self.family)['revisions']), 2)
                self.assertEqual(version_options(self.family)['event_context'].read_bytes(), self.original['event_context'].read_bytes())
                self.assert_frozen(old)

    def test_same_strategy_cash_only_preserves_event_input_and_implicit_eight_percent(self):
        change_state(self.family, 'PAUSED')
        old = self.frozen(self.family)
        self.cli('task-revise', '--task', self.family, '--strategy', 'event.earnings_schedule@1', '--initial-cash', '12000')
        after = version_options(self.family)
        self.assertEqual(after['params'], self.original['params'])
        self.assertEqual(after['risk'], self.original['risk'])
        self.assertEqual(after['event_context'].read_bytes(), self.original['event_context'].read_bytes())
        self.assertEqual(describe_task(self.family)['configuration']['effective']['take_profit_pct'], .08)
        self.assertEqual(after['initial_cash'], 12000)
        self.assertEqual(read_family(self.family)['state'], 'PAUSED')
        self.assert_frozen(old)

    def test_copy_revise_and_menu_use_the_declared_target_template_when_omitted(self):
        target = 'price.buy_and_hold@1'
        copy = self.workspace / 'tasks/copied'
        copied = self.cli('task-copy', '--from-task', self.family, '--task', copy, '--strategy', target)
        revised = self.cli('task-revise', '--task', self.family, '--strategy', target)
        with patch('builtins.input', side_effect=['2'] + [''] * 6), redirect_stdout(io.StringIO()):
            form = configuration_form(self.original)
        for options in (version_options(copy), version_options(self.family), form):
            self.assertEqual(options['params'], new_task_parameters(definition(target)['engine_strategy']))
            self.assertEqual(options['risk'], default_risk(target))
            self.assertIsNone(options['event_context'])
        self.assertNotEqual(copied['family_id'], revised['family_id'])

    def test_incompatible_target_parameters_or_risk_are_rejected_and_not_discarded(self):
        change_state(self.family, 'PAUSED')
        before, old = read_family(self.family), self.frozen(self.family)
        bad_params = self.root / 'incompatible-parameters.json'
        bad_params.write_text(json.dumps(self.original['params']), encoding='utf-8')
        bad_risk = self.root / 'incompatible-risk.json'
        bad_risk.write_text(json.dumps(self.original['risk']), encoding='utf-8')
        for changes in (['--parameters', bad_params], ['--risk', bad_risk]):
            with self.subTest(changes=changes):
                self.cli('task-revise', '--task', self.family, '--strategy', 'price.buy_and_hold@1', *changes, expected=1)
                self.assert_state(before)
                self.assert_frozen(old)

    def test_menu_version_switches_to_each_price_strategy_preserve_pause_and_history(self):
        for key, number, blanks in [('price.dual_ma@1', '1', 14), ('price.buy_and_hold@1', '2', 6)]:
            with self.subTest(target=key):
                self.family = self.workspace / 'tasks' / ('menu-' + number)
                create_family(self.family, **self.original)
                change_state(self.family, 'PAUSED')
                old = self.frozen(self.family)
                catalog = self.cli('tasks', '--workspace', self.workspace)
                index = next(i for i, row in enumerate(catalog, 1) if row.get('family') == str(self.family.resolve()))
                form = [number] + [''] * blanks
                if key == 'price.dual_ma@1':
                    form[1:3] = ['2', '4']
                answers = ['13', str(index), '2'] + form + ['0']
                with patch('builtins.input', side_effect=answers), redirect_stdout(io.StringIO()):
                    self.assertEqual(wizard(self.workspace), 0)
                view = describe_task(self.family)
                self.assertEqual(view['strategy'], key)
                self.assertEqual(view['state'], 'PAUSED')
                self.assertEqual(len(view['revisions']), 2)
                self.assertIsNone(version_options(self.family)['event_context'])
                self.assert_frozen(old)

    def test_python_revision_uses_the_same_switch_rule(self):
        change_state(self.family, 'PAUSED')
        params, risk = self.target('price.dual_ma@1')
        revise_family(self.family, strategy='price.dual_ma@1', params=params, risk=risk)
        self.assertIsNone(version_options(self.family)['event_context'])
        self.assertEqual(read_family(self.family)['state'], 'PAUSED')


if __name__ == '__main__':
    unittest.main()
