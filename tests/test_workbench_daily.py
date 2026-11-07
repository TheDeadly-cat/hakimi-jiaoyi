"""Workbench integration uses fictional frozen inputs; no network or model calls."""
import base64
import hashlib
from importlib.resources import files
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.documents import read_document
from hakimi_research.task_manager import version_options
from hakimi_research.workbench_service import Workbench


class DailyWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.app = Workbench(self.root)
        self.sequence = 0

    def act(self, action, **fields):
        self.sequence += 1
        return self.app.action(dict(action=action, operation_id='daily-test-' + str(self.sequence), **fields))

    def seed(self):
        source = files('hakimi_research').joinpath('resources')
        return self.act('import_csv',
            csv_base64=base64.b64encode(source.joinpath('trade-demo.csv').read_bytes()).decode(),
            manifest_base64=base64.b64encode(source.joinpath('trade-demo-import.json').read_bytes()).decode())

    def task(self, data, **extra):
        return self.act('create_task', title='FICTIONAL daily workflow', strategy=extra.pop('strategy', 'price.dual_ma@1'),
            snapshot=data['ref'], params=dict(fast_window=2, slow_window=4, position_pct=.25,
            stop_loss_pct=.03, take_profit_pct=.06), score_start='2024-11-11', score_end='2024-11-27',
            initial_cash=10000, fee_rate=.0008, slippage_pct=.0005, **extra)

    @staticmethod
    def hashes(folder):
        return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.rglob('*') if p.is_file()}

    def test_input_update_preserves_frozen_run_parameters_pause_and_rejects_stale_selection(self):
        data = self.seed()
        task = self.task(data)
        run = self.act('run_task', task=task['ref'])
        family = self.app.path(task['ref'])
        before_options = version_options(family)
        original = self.hashes(family / 'versions')
        run_hashes = self.hashes(self.app.path(run['ref']))
        self.act('task_state', task=task['ref'], state='PAUSED')
        changed = self.act('bind_task_input', task=task['ref'], expected_task_id=task['task_id'],
            snapshot=data['ref'], score_end='2024-12-03')
        self.assertEqual(changed['state'], 'PAUSED')
        self.assertEqual(len(changed['revisions']), 2)
        self.assertNotEqual(changed['task_id'], task['task_id'])
        after_options = version_options(family)
        for field in ('params','initial_cash','fee_rate','slippage_pct','risk','score_start'):
            self.assertEqual(before_options[field], after_options[field])
        for name, digest in original.items():
            self.assertEqual(self.hashes(family / 'versions')[name], digest)
        self.assertEqual(self.hashes(self.app.path(run['ref'])), run_hashes)
        with self.assertRaisesRegex(ValueError, 'task_changed_reload'):
            self.act('bind_task_input', task=task['ref'], expected_task_id=task['task_id'],
                snapshot=data['ref'], score_end='2024-12-03')
        repeated = self.act('bind_task_input', task=task['ref'], expected_task_id=changed['task_id'],
            snapshot=data['ref'], score_end='2024-12-03')
        self.assertEqual(repeated['input_update_status'], 'UNCHANGED_NO_NEW_VERSION')
        self.assertEqual(len(repeated['revisions']), 2)
        self.assertEqual(len(self.app.state()['runs']), 1)

    def test_same_validation_is_reused_and_reads_never_recompute(self):
        from hakimi_research import task_validation
        data = self.seed()
        task = self.task(data)
        run = self.act('run_task', task=task['ref'])
        original = self.hashes(self.app.path(run['ref']))
        with patch.object(task_validation, 'create_validation', wraps=task_validation.create_validation) as create:
            first = self.act('validate_run', run=run['ref'])
            second = self.act('validate_run', run=run['ref'])
        self.assertEqual(create.call_count, 1)
        self.assertEqual(first['action_new_economic_runs'], 4)
        self.assertEqual(second['action_new_economic_runs'], 0)
        self.assertTrue(second['reused_saved_validation'])
        self.assertEqual(first['ref'], second['ref'])
        with patch.object(task_validation.EquityExperimentRunner, 'run', side_effect=AssertionError('read must not run')):
            reopened = Workbench(self.root)
            self.assertEqual(reopened.validation_view(first['ref'])['validation_hash'], first['validation_hash'])
            self.assertEqual(reopened.run_view(run['ref'])['diagnostics']['new_economic_runs'], 0)
            self.assertEqual(len(reopened.state()['validations']), 1)
        self.assertEqual(self.hashes(self.app.path(run['ref'])), original)

    def test_stock_check_is_explicit_and_repeated_operation_does_not_fetch_again(self):
        from hakimi_research import daily_updates
        data = self.seed()
        def check(baseline, directory):
            directory.mkdir(parents=True)
            return {'status':'WAITING_SOURCE_UPDATE'}
        view = dict(symbol='TEST', status='WAITING_SOURCE_UPDATE', reason='TEST_ONLY', can_freeze=False)
        with patch.object(daily_updates, 'check_daily_update', side_effect=check) as collect, \
                patch.object(daily_updates, 'read_daily_update', return_value=view):
            self.assertEqual(self.app.state()['daily_updates'], [])
            self.assertEqual(collect.call_count, 0)
            request = dict(action='check_stock_update', operation_id='explicit-data-check', snapshot=data['ref'])
            first = self.app.action(request)
            self.assertEqual(self.app.action(request), first)
            self.assertEqual(collect.call_count, 1)
            self.assertEqual(Workbench(self.root).state()['daily_updates'][0]['status'], 'WAITING_SOURCE_UPDATE')
            self.assertEqual(collect.call_count, 1)
        self.assertEqual(len(self.app.state()['inputs']), 1)
        self.assertEqual(len(self.app.state()['tasks']), 0)

    def test_updated_schedule_version_keeps_exact_accepted_binding(self):
        import test_workbench_research as fixtures
        data = self.seed()
        result, context, source = fixtures.fictional_bundle()
        b64 = lambda raw:base64.b64encode(raw).decode()
        preview = self.act('preview_research', security_id=fixtures.SECURITY,
            result_base64=b64(result), context_base64=b64(context), source_base64=b64(source))
        reviewed = self.act('review_research', research=preview['ref'], decision='ACCEPT_FOR_INPUT_CHECK',
            actor='FICTIONAL_TEST_OPERATOR', reason='Fictional software regression only')
        task = self.task(data, strategy='event.earnings_schedule@1',
            event_context=reviewed['input']['ref'], research=reviewed['ref'])
        original_binding = self.root / 'research-bindings' / (task['task_id'] + '.json')
        before = original_binding.read_bytes()
        changed = self.act('bind_task_input', task=task['ref'], expected_task_id=task['task_id'],
            snapshot=data['ref'], score_end='2024-12-03')
        binding = read_document(self.root / 'research-bindings' / (changed['task_id'] + '.json'))
        self.assertEqual(binding['research'], reviewed['ref'])
        self.assertEqual(binding['assessment_hash'], reviewed['assessment_hash'])
        self.assertEqual(binding['revision'], changed['viewed_revision'])
        self.assertEqual(original_binding.read_bytes(), before)
        self.assertEqual(len(self.app.state()['runs']), 0)

    def test_revision_impact_reads_actual_consumed_prefix_and_preserves_all_records(self):
        import test_daily_updates as fixtures
        from hakimi_research import daily_updates
        from hakimi_research.continuous_runtime import _snapshots
        from hakimi_research.documents import read_document
        prior = fixtures.baseline('2026-10-05', '2026-10-22')
        data = self.act('import_input', content_base64=base64.b64encode(fixtures.encoded(prior)).decode())
        task = self.act('create_task', title='FICTIONAL revision impact', strategy='price.dual_ma@1',
            snapshot=data['ref'], params=dict(fast_window=2, slow_window=4, position_pct=.25,
                stop_loss_pct=.03, take_profit_pct=.06), score_start='2026-10-13', score_end='2026-10-22',
            initial_cash=10000, fee_rate=.0008, slippage_pct=.0005)
        limits = dict(max_total_position_pct=.8, max_symbol_position_pct=.5,
            min_cash_pct=.1, max_daily_loss_pct=.05, max_leverage=1)
        consumed = self.act('create_account', title='FICTIONAL consumed history', tasks=[task['ref']],
            initial_cash=10000, limits=limits)
        seed_only = self.act('create_account', title='FICTIONAL seed only', tasks=[task['ref']],
            initial_cash=10000, limits=limits)
        self.act('advance', account=consumed['ref'], snapshots=[data['ref']], through='2026-10-20',
            observed_at='2026-10-23T21:00:00Z')
        source = fixtures.source_reply('2026-10-05', '2026-10-23')
        source['chart']['result'][0]['indicators']['quote'][0]['high'][10] += 1  # 19 October
        directory = self.root / 'updates/check-revision-impact'
        daily_updates.check_daily_update(self.app.path(data['ref']), directory,
            now=daily_updates._clock('2026-10-23T21:00:00Z'), fetcher=lambda _url:fixtures.encoded(source))
        before = self.hashes(self.root)
        view = self.app.daily_update_view(self.app.ref(directory))
        impact = view['revision_impact']
        self.assertEqual(view['status'], 'REVISION_REVIEW_REQUIRED')
        self.assertEqual(impact['status'], 'CHECKED')
        self.assertEqual([row['ref'] for row in impact['tasks']], [task['ref']])
        accounts = {row['ref']:row for row in impact['accounts']}
        self.assertEqual(accounts[consumed['ref']]['status'], 'INPUT_CONFLICT_REQUIRES_NEW_ACCOUNT')
        self.assertEqual(accounts[consumed['ref']]['changed_row_dates'], ['2026-10-19'])
        self.assertEqual(accounts[consumed['ref']]['last_processed_session'], '2026-10-20')
        self.assertEqual(accounts[seed_only['ref']]['status'], 'RETAINED_PREFIX_UNCHANGED')
        self.assertIsNone(accounts[seed_only['ref']]['last_processed_session'])
        self.assertEqual(accounts[seed_only['ref']]['retained_through'], '2026-10-12')
        self.assertEqual((impact['new_economic_runs'], impact['ledger_writes']), (0, 0))
        self.assertEqual(self.hashes(self.root), before)
        # The informational projection does not weaken the existing ledger gate.
        account = self.app.account_view(consumed['ref'])
        manifest = read_document(self.app.path(consumed['ref']) / 'account.json')
        candidate = read_document(directory / 'candidate-snapshot.json')
        with self.assertRaisesRegex(ValueError, 'DATA_CONSUMED_PREFIX_REVISED_OR_MISSING:.*2026-10-19'):
            _snapshots(account['state'], {candidate['security']['security_id']:candidate},
                manifest['config'], '2026-10-23', '2026-10-23T21:00:00Z')
        self.assertEqual(self.hashes(self.root), before)
        # An unreadable account must remain unknown, never reported unaffected.
        with patch('hakimi_research.continuous_runtime.describe_continuous_account',
                   side_effect=ValueError('FICTIONAL damaged retained ledger')):
            unknown = self.app.daily_update_view(self.app.ref(directory))['revision_impact']
        self.assertEqual(unknown['status'], 'INCOMPLETE')
        self.assertEqual(len(unknown['unresolved']), 2)
        self.assertEqual(unknown['accounts'], [])
        self.assertEqual(self.hashes(self.root), before)

    def test_calendar_policy_comes_from_available_exchange_resources(self):
        from hakimi_research.daily_updates import calendar_support
        support = calendar_support()
        policy = self.app.state()['data_update_policy']
        self.assertEqual(policy['calendar_years'], support['supported_years'])
        self.assertEqual(policy['exchanges'], support['exchanges'])
        self.assertIn(2027, policy['exchanges']['XNYS'])
        self.assertNotIn(2027, policy['exchanges']['XNAS'])


if __name__ == '__main__':
    unittest.main()
