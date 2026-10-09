import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import offline_app, task_manager
from hakimi_research.documents import read_document
from hakimi_research.offline_app import check_task, run_task, replay_run, recover_report, verify_run
from hakimi_research.trade_cli import initialize_demo, main, wizard
from hakimi_research.task_manager import (create_family, revise_family, read_family, change_state,
    select_version, describe_task, version_options, family_lock)
from hakimi_research.task_comparison import compare_runs


class ManagedStrategyTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hakimi-m2-tasks-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.workspace=self.root/'workspace'
        initialize_demo(self.workspace)
        self.options=version_options(self.workspace/'tasks/price.json')
        self.family=self.workspace/'tasks/managed'

    def create(self):
        return create_family(self.family,**self.options)

    def cli(self, arguments, expected=0):
        with redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(arguments),expected,stream.getvalue())
        return json.loads(stream.getvalue())

    def test_versions_pause_selection_and_direct_file_admission_preserve_frozen_run(self):
        self.create();first=check_task(self.family);folder=run_task(self.family)
        report=(folder/'report.json').read_bytes();old_task=first['task_path'].read_bytes()
        revised=revise_family(self.family,initial_cash=12000)
        self.assertNotEqual(check_task(self.family)['task_id'],first['task_id'])
        self.assertEqual(len(revised['revisions']),2)
        with self.assertRaisesRegex(ValueError,'historical_task_not_selected'):run_task(first['task_path'])
        change_state(self.family,'PAUSED')
        with self.assertRaisesRegex(ValueError,'task_paused'):run_task(self.family)
        selected=Path(describe_task(self.family)['task_file'])
        with self.assertRaisesRegex(ValueError,'task_paused'):run_task(selected)
        self.assertEqual(describe_task(self.family)['configuration']['effective']['initial_cash'],12000)
        select_version(self.family,1)
        self.assertEqual(read_family(self.family)['state'],'PAUSED')
        change_state(self.family,'ENABLED')
        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('old report must not recalculate')):
            self.assertEqual(run_task(self.family),folder)
        self.assertEqual(first['task_path'].read_bytes(),old_task)
        self.assertEqual((folder/'report.json').read_bytes(),report)
        self.assertEqual(check_task(self.family)['task_id'],first['task_id'])

    def test_requested_risk_and_costs_match_effective_stops_and_saved_accounting(self):
        params=dict(self.options['params'],position_pct=.15,stop_loss_pct=.02)
        risk=dict(self.options['risk'],max_position_pct=.2,max_single_loss_pct=.025,max_daily_loss_pct=.1,min_cash_pct=.1)
        create_family(self.family,**dict(self.options,params=params,risk=risk,fee_rate=.001,slippage_pct=.002))
        view=describe_task(self.family)['configuration']
        self.assertEqual(view['requested']['risk'],risk)
        self.assertEqual(view['effective']['stop_loss_pct'],.02)
        result=verify_run(run_task(self.family))[1]['result']
        buys=[r for r in result['signals'] if r['action']=='BUY']
        self.assertTrue(buys)
        self.assertTrue(all(r['effective_stop_loss_pct']==.02 for r in buys))
        self.assertEqual(result['risk_semantics']['daily_loss']['threshold_pct'],.1)
        self.assertGreater(result['total_fees'],0)

    def test_conflicts_and_unsupported_fields_do_not_publish_or_move_old_selection(self):
        self.create();before=read_family(self.family)
        cases=[dict(risk=dict(self.options['risk'],max_leverage=2)),
            dict(params=dict(self.options['params'],position_pct=.5)),
            dict(params=dict(self.options['params'],stop_loss_pct=.04)),
            dict(risk=dict(self.options['risk'],unrecognized_control=.1)),
            dict(params=dict(self.options['params'],unknown_rule=True)),
            dict(params=dict(self.options['params'],slow_window=12)),
            dict(initial_cash=float('nan')),dict(score_start='2024-11-01')]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):revise_family(self.family,**changes)
            self.assertEqual(read_family(self.family)['event_hash'],before['event_hash'])
        self.assertEqual(len(read_family(self.family)['revisions']),1)

    def test_benchmark_rejects_inactive_risk_configuration_and_exposes_exit_differences(self):
        options=dict(self.options,strategy='price.buy_and_hold@1',params={'target_position_pct':.3},risk=None)
        create_family(self.family,**options)
        view=describe_task(self.family)['configuration']
        self.assertIsNone(view['effective']['stop_loss_pct'])
        self.assertIsNone(view['effective']['max_daily_loss_pct'])
        with self.assertRaisesRegex(ValueError,'benchmark_has_no_active_risk_controls'):
            revise_family(self.family,risk=dict(self.options['risk'],max_position_pct=1,max_daily_loss_pct=.05))

    def test_state_commit_failure_retains_old_selection_and_uncommitted_revision(self):
        self.create();before=read_family(self.family)
        original=task_manager.write_new
        def fail_commit(path,value):
            if Path(path).parent.name=='journal':raise OSError('fictional state write failure')
            return original(path,value)
        with patch.object(task_manager,'write_new',side_effect=fail_commit):
            with self.assertRaisesRegex(OSError,'fictional'):revise_family(self.family,initial_cash=15000)
            with self.assertRaisesRegex(OSError,'fictional'):change_state(self.family,'PAUSED')
        after=read_family(self.family)
        self.assertEqual(after['event_hash'],before['event_hash'])
        self.assertEqual(after['state'],'ENABLED')
        self.assertEqual(len(after['uncommitted_versions_retained']),1)
        orphan=Path(after['family'])/'versions'/after['uncommitted_versions_retained'][0]/'task.json'
        with self.assertRaisesRegex(ValueError,'not_committed'):run_task(orphan)
        self.assertEqual(check_task(self.family)['semantics']['experiment']['initial_cash'],10000)

    def test_journal_gap_and_sealed_input_change_fail_closed(self):
        self.create();change_state(self.family,'PAUSED')
        (self.family/'journal/000001.json').rename(self.family/'retained-first-event.json')
        with self.assertRaisesRegex(ValueError,'journal_gap'):describe_task(self.family)
        (self.family/'retained-first-event.json').rename(self.family/'journal/000001.json')
        change_state(self.family,'ENABLED')
        snapshot=check_task(self.family)['snapshot_path']
        snapshot.write_bytes(snapshot.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'input_missing_or_changed'):run_task(self.family)

    def test_family_lock_prevents_state_change_and_execution_by_another_owner(self):
        self.create()
        with family_lock(self.family):
            with self.assertRaisesRegex(ValueError,'active_owner'):change_state(self.family,'PAUSED')
            with self.assertRaisesRegex(ValueError,'active_owner'):run_task(self.family)
        self.assertEqual(read_family(self.family)['state'],'ENABLED')

    def test_common_comparison_has_exact_score_and_no_recompute_or_portfolio_sum(self):
        self.create();active=run_task(self.family)
        event=run_task(self.workspace/'tasks/event.json')
        benchmark=self.workspace/'tasks/benchmark'
        create_family(benchmark,**dict(self.options,strategy='price.buy_and_hold@1',params={'target_position_pct':.25},risk=None))
        held=run_task(benchmark)
        raw=[(p/'report.json').read_bytes() for p in [active,event,held]]
        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('compare must not run')):
            view=compare_runs([active,event,held],output=self.workspace/'comparison.json')
        self.assertEqual(view['status'],'COMPARABLE_CONDITIONS')
        self.assertEqual(view['new_economic_runs'],0);self.assertFalse(view['shared_portfolio'])
        self.assertEqual([r['warmup']['required_context_sessions'] for r in view['rows']],[6,6,1])
        self.assertEqual(len(view['differences_from_first']),2)
        self.assertGreater(view['rows'][0]['max_drawdown'],0)
        self.assertFalse(view['rows'][2]['risk_semantics']['protective_exits_enabled'])
        self.assertEqual([read_document(p/'report.json')['spec']['score_start_session'] for p in [active,event,held]],['2024-11-11']*3)
        self.assertEqual([(p/'report.json').read_bytes() for p in [active,event,held]],raw)

    def test_different_cash_costs_or_scores_are_explicitly_incomparable(self):
        self.create();first=run_task(self.family)
        for changes,field in [(dict(initial_cash=11000),'initial_cash'),(dict(fee_rate=.002),'fee_rate'),
                (dict(slippage_pct=.002),'slippage_pct'),(dict(score_start='2024-11-12'),'score_start')]:
            with self.subTest(field=field):
                revise_family(self.family,**dict(self.options,**changes))
                view=compare_runs([first,run_task(self.family)])
                self.assertEqual(view['status'],'NOT_COMPARABLE')
                self.assertIn(field,view['mismatches'][0]['fields'])
                self.assertEqual(view['differences_from_first'],[])

    def test_workspace_move_retains_all_versions_state_reports_and_replay(self):
        self.create();first=run_task(self.family);report=(first/'report.json').read_bytes()
        revise_family(self.family,initial_cash=12500);change_state(self.family,'PAUSED')
        identity=describe_task(self.family)['task_id']
        moved=self.root/'moved';shutil.move(str(self.workspace),moved)
        family=moved/'tasks/managed';folder=moved/'runs'/first.name
        self.assertFalse(self.workspace.exists())
        self.assertEqual(describe_task(family)['task_id'],identity)
        self.assertEqual(read_family(family)['state'],'PAUSED')
        self.assertEqual((folder/'report.json').read_bytes(),report)
        self.assertTrue(replay_run(folder)['replay_verified'])
        self.assertTrue(recover_report(folder).is_file())
        change_state(family,'ENABLED');select_version(family,1)
        self.assertEqual(run_task(family),folder)

    def test_normal_commands_copy_revise_and_reopen_history(self):
        self.cli(['task-copy','--from-task',str(self.workspace/'tasks/price.json'),'--task',str(self.family)])
        before=self.cli(['task-show','--task',str(self.family)])
        self.cli(['task-revise','--task',str(self.family),'--initial-cash','12345'])
        self.cli(['task-state','--task',str(self.family),'--state','PAUSED'])
        self.cli(['run','--task',str(self.family)],1)
        self.cli(['task-select','--task',str(self.family),'--version','1'])
        after=self.cli(['task-show','--task',str(self.family)])
        self.assertEqual(before['task_id'],after['task_id']);self.assertEqual(after['state'],'PAUSED')
        self.assertEqual(len(after['revisions']),2)

    def test_wizard_creates_configured_managed_task_runs_and_pauses_it(self):
        # Choose supplied data and edit all supported fields via the menu.
        inputs=['15','1','1','2','4','.15','.02','.06','.2','.025','.1','.1','12000','.001','.002',
            '2024-11-11','2024-12-03','normal-managed','2','2','3','2','13','2','4','0']
        # Sorted legacy event.json precedes normal-managed, then price.json.
        with patch('builtins.input',side_effect=inputs),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(self.workspace),0)
        family=self.workspace/'tasks/normal-managed'
        self.assertEqual(describe_task(family)['state'],'PAUSED')
        self.assertEqual(describe_task(family)['configuration']['effective']['initial_cash'],12000)
        self.assertIn('运行完成',output.getvalue())
        self.assertIn('生效配置',output.getvalue())


if __name__=='__main__':unittest.main()
