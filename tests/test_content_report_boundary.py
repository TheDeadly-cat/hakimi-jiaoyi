"""Full synthetic report/menu regressions, including self-consistent bad copies."""
import copy
from contextlib import ExitStack, redirect_stdout
from hashlib import sha256
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from hakimi_research import content_tasks, offline_app
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.equity_research import verify_equity_report
from hakimi_research.input_workflow import import_content_packet
from hakimi_research.offline_app import run_task, verify_run, recover_report, describe_run, check_task
from hakimi_research.strategy_registry import definition
from hakimi_research.task_comparison import compare_runs
from hakimi_research.task_manager import create_family, version_options
from hakimi_research.trade_cli import initialize_demo, create_task, wizard


class ContentReportBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='hakimi-content-report-boundary-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workspace = self.root/'workspace'
        examples = initialize_demo(self.workspace)['input_examples']
        self.snapshot = version_options(self.workspace/'tasks/price.json')['snapshot']
        self.context = Path(import_content_packet(examples['packet'],self.workspace,event_id=examples['event_id'],
            texts_dir=examples['texts_dir'],originals_dir=examples['originals_dir'],synthetic=True)['path'])

    def run_content(self, name='normal', strategy='content.price_confirmation@1', **options):
        family = self.workspace/'tasks'/name
        create_family(family,strategy=strategy,snapshot=self.snapshot,event_context=self.context,
            score_start='2024-11-04',**dict({'score_end':'2024-12-03'},**options))
        run = run_task(family)
        _, report, snapshot = verify_run(run)
        return run,report,snapshot

    def seal_bad_copy(self, report, change):
        bad = copy.deepcopy(report)
        change(bad['result'])
        bad['result_hash'] = digest(dict(snapshot_id=bad['dataset']['snapshot_id'],spec=bad['spec'],result=bad['result']))
        bad['report_hash'] = digest({k:v for k,v in bad.items() if k!='report_hash'})
        return bad

    def no_engine(self):
        stack = ExitStack()
        for module,name in [(offline_app,'run_strategy'),(content_tasks,'run_content_task')]:
            stack.enter_context(patch.object(module,name,side_effect=AssertionError('reading must not run economics')))
        stack.enter_context(patch.object(content_tasks._SessionEngine,'run',side_effect=AssertionError('reading must not run engine')))
        return stack

    def test_normal_protection_and_legal_unfilled_opportunity_are_readonly(self):
        cases=[self.run_content(),self.run_content('zero-allocation',params=dict(position_pct=0,stop_loss_pct=.03,take_profit_pct=.06)),
            self.run_content('blocked',strategy='content.reviewed_outlook@1'),
            self.run_content('mark-to-market',score_end='2024-11-08')]
        self.assertTrue(any(f['action']=='SELL' and f['fill_basis']=='INTRABAR_STOP' for f in cases[0][1]['result']['fills']))
        self.assertEqual(cases[1][1]['result']['fill_count'],0)
        self.assertTrue(any(s['action']=='BUY' for s in cases[1][1]['result']['signals']))
        self.assertEqual(cases[2][1]['result']['fill_count'],0)
        self.assertEqual(cases[3][1]['result']['fill_count'],1)
        self.assertGreater(cases[3][1]['result']['open_position_qty'],0)
        with self.no_engine():
            for run,report,snapshot in cases:
                original=(run/'report.json').read_bytes()
                self.assertEqual(content_tasks.verify_content_report(report,snapshot),report)
                describe_run(run);recover_report(run)
                self.assertEqual((run/'report.json').read_bytes(),original)
            self.assertEqual(compare_runs([cases[0][0],cases[2][0]])['new_economic_runs'],0)

    def test_rehashed_bad_security_session_signal_and_basis_stop_view_recover_compare(self):
        run,report,snapshot=self.run_content()
        frozen=(run/'report.json').read_bytes()
        for field,value in [('symbol','OTHER'),('fill_time','2024-11-09T14:30:00Z'),
                ('signal_time','2024-11-09T14:30:00Z'),('fill_basis','UNSUPPORTED')]:
            with self.subTest(field=field):
                bad=self.seal_bad_copy(report,lambda r:r['fills'][0].update({field:value}))
                duplicate=self.root/field/run.name;duplicate.parent.mkdir();shutil.copytree(run,duplicate)
                (duplicate/'report.json').write_bytes(canonical_bytes(bad))
                before={p:sha256(p.read_bytes()).hexdigest() for p in duplicate.rglob('*') if p.is_file()}
                with self.no_engine():
                    for operation in [lambda:content_tasks.verify_content_report(bad,snapshot),lambda:describe_run(duplicate),
                            lambda:recover_report(duplicate),lambda:compare_runs([run,duplicate],output=self.root/'not-written.json')]:
                        with self.assertRaisesRegex(ValueError,'equity_fill_before_signal_or_outside_session'):operation()
                self.assertFalse((self.root/'not-written.json').exists())
                self.assertEqual(before,{p:sha256(p.read_bytes()).hexdigest() for p in duplicate.rglob('*') if p.is_file()})
        self.assertEqual((run/'report.json').read_bytes(),frozen)

    def test_session_valid_wrong_opportunity_and_protective_buy_basis_are_rejected(self):
        _,report,snapshot=self.run_content()
        sessions=report['dataset']['sessions'];index=next(i for i,s in enumerate(sessions) if s['date']=='2024-11-11')
        def later(result):
            result['fills'][0].update(fill_time=sessions[index]['open_utc'],
                signal_time=str(pd.Timestamp(sessions[index-1]['close_utc'])+pd.Timedelta(seconds=60)))
        for change in [later,lambda r:r['fills'][0].update(fill_basis='INTRABAR_TARGET')]:
            bad=self.seal_bad_copy(report,change)
            with self.no_engine(),self.assertRaisesRegex(ValueError,'content_report_buy_not_bound_to_plan'):
                content_tasks.verify_content_report(bad,snapshot)

    def test_filtered_duplicate_and_reentry_buys_cannot_use_a_rehashed_report(self):
        _,report,snapshot=self.run_content()
        _,blocked,_=self.run_content('blocked',strategy='content.reviewed_outlook@1')
        def inject(result):result['fills']=[copy.deepcopy(report['result']['fills'][0])];result['fill_count']=1
        bad=self.seal_bad_copy(blocked,inject)
        with self.no_engine(),self.assertRaisesRegex(ValueError,'content_report_buy_not_bound_to_plan'):
            content_tasks.verify_content_report(bad,snapshot)
        def duplicate(result):result['fills'].insert(1,copy.deepcopy(result['fills'][0]));result['fill_count']+=1
        sessions=report['dataset']['sessions'];index=next(i for i,s in enumerate(sessions) if s['date']=='2024-11-18')
        def reentry(result):
            new=copy.deepcopy(result['fills'][0]);new.update(fill_time=sessions[index]['open_utc'],
                signal_time=str(pd.Timestamp(sessions[index-1]['close_utc'])+pd.Timedelta(seconds=60)))
            result['fills'].append(new);result['fill_count']+=1
        for change in [duplicate,reentry]:
            with self.no_engine(),self.assertRaisesRegex(ValueError,'content_report_buy_not_bound_to_plan'):
                content_tasks.verify_content_report(self.seal_bad_copy(report,change),snapshot)

    def test_protective_exit_clock_action_and_entry_order_are_checked(self):
        _,report,snapshot=self.run_content()
        for change,reason in [(lambda r:r['fills'][1].update(signal_time='2024-12-03T21:01:00Z'),'content_report_exit_not_protective'),
                (lambda r:r['fills'][1].update(action='HOLD'),'content_report_fill_action_invalid'),
                (lambda r:r['fills'].reverse(),'content_report_exit_not_protective'),
                (lambda r:r.update(fill_count=999),'content_report_fill_count_mismatch')]:
            with self.no_engine(),self.assertRaisesRegex(ValueError,reason):
                content_tasks.verify_content_report(self.seal_bad_copy(report,change),snapshot)

    def test_signals_must_match_the_plan_even_when_no_fill_is_added(self):
        _,report,snapshot=self.run_content('blocked',strategy='content.reviewed_outlook@1')
        bad=self.seal_bad_copy(report,lambda r:r['signals'][0].update(action='BUY'))
        with self.no_engine(),self.assertRaisesRegex(ValueError,'content_report_signal_not_bound_to_plan'):
            content_tasks.verify_content_report(bad,snapshot)

    def test_legacy_menu_uses_registry_parameters_for_all_five_strategies(self):
        keys=['price.dual_ma@1','price.buy_and_hold@1','event.earnings_schedule@1',
            'content.price_confirmation@1','content.reviewed_outlook@1']
        for number,key in enumerate(keys,1):
            with self.subTest(strategy=key):
                entry=definition(key)
                params=['2','4','','',''] if number in {1,3} else [''] if number==2 else ['','','']
                answers=['10','1',str(number),*params,*(['']*4 if number!=2 else []),*(['']*5)]
                if entry['event_rule']:answers.append(str(self.workspace/'data/event-context.json') if number==3 else str(self.context))
                name='legacy-'+str(number);answers.extend([name,'0'])
                with patch('builtins.input',side_effect=answers),redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(wizard(self.workspace),0)
                self.assertNotIn('操作停止：',output.getvalue())
                task=check_task(self.workspace/'tasks'/(name+'.json'))
                self.assertEqual(task['semantics']['strategy'],key)
                self.assertEqual(set(task['semantics']['experiment']['strategy']['params']),set(entry['parameters']))

    def test_unknown_content_parameters_remain_rejected_before_task_publication(self):
        task=self.root/'invalid.json'
        with self.assertRaisesRegex(ValueError,'content_task_strategy_parameters_invalid'):
            create_task(task,strategy='content.price_confirmation@1',snapshot=self.snapshot,event_context=self.context,
                params=dict(position_pct=.25,stop_loss_pct=.03,take_profit_pct=.06,fast_window=2,slow_window=4))
        self.assertFalse(task.exists())

    def test_shared_fill_checks_preserve_price_report_rejections(self):
        run=run_task(self.workspace/'tasks/price.json');_,report,_=verify_run(run)
        self.assertEqual(verify_equity_report(report),report)
        for field,value in [('symbol','OTHER'),('fill_time','2024-11-09T14:30:00Z'),
                ('signal_time','2024-12-31T00:00:00Z'),('fill_basis','UNSUPPORTED')]:
            with self.assertRaisesRegex(ValueError,'equity_fill_before_signal_or_outside_session'):
                verify_equity_report(self.seal_bad_copy(report,lambda r:r['fills'][0].update({field:value})))
