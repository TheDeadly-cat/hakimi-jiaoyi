"""End-to-end incremental ledger tests with explicitly fictional US daily data."""
import base64
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta, date
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_equity_dataset import fixture, with_csv
from hakimi_research.documents import canonical_bytes, read_document
from hakimi_research.equity_dataset import build_equity_snapshot, save_equity_snapshot
from hakimi_research.trade_cli import create_task
from hakimi_research.task_manager import create_family, read_family, change_state
from hakimi_research.continuous_runtime import (create_continuous_account, advance_continuous_account,
    describe_continuous_account, set_continuous_task_state, lookup_continuous_receipt, reset_continuous_loss)
from hakimi_research import shared_account

LIMITS = dict(max_total_position_pct=1, max_symbol_position_pct=1, min_cash_pct=0, max_daily_loss_pct=.5, max_leverage=1)
OBSERVED = '2024-12-04T00:00:00Z'


def snapshot(*, through='2024-12-03', changes=None, imported=False, symbol='TEST', lag=60):
    raw, manifest = fixture()
    rows = raw.decode().splitlines(); header = rows[0]; output=[]
    for row in rows[1:]:
        parts=row.split(','); day=parts[0]
        if day > through: continue
        # A genuine existing dual-MA crossover at the close preceding score start.
        prices=[100,100.5,99.5,100,10000]
        if day >= '2024-11-08': prices=[104,104.5,103.5,104,10000]
        if changes and day in changes: prices=changes[day]
        output.append(day+','+','.join(map(str,prices)))
    raw=('\n'.join([header,*output])+'\n').encode()
    manifest['calendar']['days']=[r for r in manifest['calendar']['days'] if r['date']<=through]
    manifest['calendar']['coverage_end']=through
    manifest['calendar']['source']['raw_base64']=base64.b64encode(json.dumps(manifest['calendar']['days']).encode()).decode()
    manifest['bar_availability_lag_seconds']=lag
    manifest['as_of']='2024-12-03T23:00:00Z'
    if lag >= 86400:
        manifest['as_of']='2024-12-05T00:00:00Z';manifest['retrieved_at']='2024-12-05T00:00:00Z'
        for key in ['identity','calendar','corporate_actions']:manifest[key]['source']['retrieved_at']='2024-12-05T00:00:00Z'
        manifest['price_source']['retrieved_at']='2024-12-05T00:00:00Z'
    manifest['security']['symbol']=symbol
    manifest['security']['security_id']=('US:XNAS:' if imported else 'SYNTHETIC:DATASET:')+symbol
    manifest['evidence_kind']='IMPORTED_UNVERIFIED' if imported else 'SYNTHETIC_TEST'
    return build_equity_snapshot(raw,with_csv(manifest,raw))


class ContinuousRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace';self.data=snapshot();self.security=self.data.document['security']['security_id']
        self.seed=save_equity_snapshot(self.data,self.workspace/'data')
    def tearDown(self):self.temp.cleanup()
    def task(self,name='active',key='price.dual_ma@1',data=None,managed=False,**kw):
        path=save_equity_snapshot(data,self.workspace/'data') if data else self.seed
        params=dict(target_position_pct=.4) if key=='price.buy_and_hold@1' else dict(fast_window=2,slow_window=4,position_pct=.25,stop_loss_pct=.03,take_profit_pct=.08)
        options=dict(strategy=key,snapshot=path,score_start='2024-11-11',score_end=(data or self.data).document['sessions'][-1]['date'],
            params=params,fee_rate=0,slippage_pct=0,initial_cash=1234)
        options.update(kw)
        if managed:
            family=self.workspace/'tasks'/name;create_family(family,**options);return family
        return create_task(self.workspace/'tasks'/(name+'.json'),**options)
    def account(self,name='account',tasks=None,limits=None):
        account=self.root/name;create_continuous_account(account,tasks or [self.task()],limits=limits or LIMITS);return account
    def advance(self,account,through='2024-12-03',data=None,op='advance',**kw):
        data=data or self.data
        return advance_continuous_account(account,{data.document['security']['security_id']:data.document},through=through,observed_at=OBSERVED,operation_id=op,**kw)
    def view(self,account):return describe_continuous_account(account)

    def test_existing_strategy_real_crossover_and_shared_nav_no_independent_backtest(self):
        account=self.account()
        with patch('hakimi_research.backtest.BacktestEngine.run',side_effect=AssertionError('independent backtest forbidden')):
            receipt=self.advance(account,'2024-11-11')
        decision=receipt['outcome']['sessions'][0]['decisions'][0]
        self.assertEqual(decision['signal']['action'],'BUY')
        self.assertEqual(decision['signal_at'],'2024-11-08T21:01:00Z')
        self.assertEqual(decision['execution_at'],'2024-11-11T14:30:00Z')
        self.assertEqual(Decimal(self.view(account)['cash']),7500) # task risk default caps 25% of shared 10000
        self.assertFalse(self.view(account)['execution_permission']['live_allowed'])
        self.assertEqual(self.view(account)['broker_order_calls'],0)

    def test_batch_and_each_completed_session_have_identical_economic_state(self):
        task=self.task();batch=self.account('batch',[task]);steps=self.account('steps',[task])
        self.advance(batch)
        dates=[s['date'] for s in self.data.document['sessions'] if s['date']>='2024-11-11']
        for i,day in enumerate(dates):self.advance(steps,day,op='step-'+str(i))
        self.assertEqual(self.view(batch)['state'],self.view(steps)['state'])
        self.assertEqual(self.view(steps)['continuous']['last_success_at'],'2024-12-03T21:01:00Z')
        early=next(s for s in self.view(steps)['continuous']['session_results'] if s['session']=='2024-11-29')
        self.assertEqual(early['available_at'],'2024-11-29T18:01:00Z')

    def test_append_snapshot_then_restart_continues_without_duplicate_fills(self):
        seed=snapshot(through='2024-11-11');task=self.task(data=seed);account=self.account(tasks=[task])
        self.advance(account,'2024-11-11',seed)
        first=deepcopy(self.view(account)['state']['intents'])
        later=self.advance(account,op='append');count=len(self.view(account)['continuous']['session_results'])
        self.assertEqual(self.advance(account,op='append'),later)
        duplicate=self.advance(account,op='another-id')
        self.assertEqual(duplicate['outcome']['status'],'NO_NEW_SESSIONS')
        self.assertEqual(len(self.view(account)['continuous']['session_results']),count)
        self.assertEqual({k:self.view(account)['state']['intents'][k] for k in first},first)

    def test_consumed_revision_and_missing_security_are_blocked_without_economic_change(self):
        account=self.account();self.advance(account,'2024-11-11');before=self.view(account)
        changed=snapshot(changes={'2024-11-08':[105,106,104,105,10000]})
        r=self.advance(account,data=changed,op='revision')
        self.assertEqual(r['outcome']['status'],'BLOCKED');self.assertIn('PREFIX_REVISED',r['outcome']['reason'])
        self.assertEqual(self.view(account)['state']['positions'],before['state']['positions'])
        self.assertEqual(self.view(account)['cash'],before['cash'])
        r=advance_continuous_account(account,{},through='2024-12-03',observed_at=OBSERVED,operation_id='missing')
        self.assertIn('DATA_MISSING',r['outcome']['reason'])
        self.assertEqual(self.view(account)['continuous']['last_session'],'2024-11-11')
        self.assertEqual(self.advance(account,op='valid-recovery')['outcome']['status'],'CURRENT')

    def test_future_prices_do_not_change_past_and_stale_coverage_is_explicit(self):
        task=self.task();a=self.account('a',[task]);b=self.account('b',[task])
        future=snapshot(changes={'2024-12-03':[800,900,700,850,10000]})
        self.advance(a,'2024-11-11');self.advance(b,'2024-11-11',future)
        self.assertEqual(self.view(a)['state'],self.view(b)['state'])
        r=self.advance(a,'2024-12-04',op='stale');self.assertIn('STALE_OR_MISSING',r['outcome']['reason'])
        self.assertEqual(self.view(a)['continuous']['last_session'],'2024-11-11')

    def test_pause_keeps_intrabar_stop_and_gap_protection_benchmark_remains_unprotected(self):
        for gap in [False,True]:
            with self.subTest(gap=gap):
                task=self.task('active-'+str(gap));account=self.account('pause-'+str(gap),[task])
                self.advance(account,'2024-11-11');owner=next(iter(self.view(account)['continuous']['task_paused']))
                set_continuous_task_state(account,owner,True,operation_id='pause')
                prices=[90,95,89,92,10000] if gap else [104,120,90,103,10000]
                data=snapshot(changes={'2024-11-12':prices})
                r=self.advance(account,'2024-11-12',data,op='protected')
                exits=[d for d in r['outcome']['sessions'][0]['decisions'] if d['signal']['action']=='EXIT']
                self.assertEqual(len(exits),1);self.assertEqual(exits[0]['basis'],'GAP_OPEN_STOP' if gap else 'INTRABAR_STOP_FIRST')
                self.assertAlmostEqual(exits[0]['reference_price'],90 if gap else 104*.97)
                self.assertTrue(all(Decimal(p['quantity'])==0 for p in self.view(account)['state']['positions'].values()))
        bench=self.task('benchmark','price.buy_and_hold@1');account=self.account('benchmark',[bench]);self.advance(account,'2024-11-11')
        self.advance(account,'2024-11-12',snapshot(changes={'2024-11-12':[90,95,89,92,10000]}),op='drop')
        self.assertTrue(any(Decimal(p['quantity'])>0 for p in self.view(account)['state']['positions'].values()))

    def test_managed_pause_blocks_new_buy_and_existing_family_state_is_honoured(self):
        family=self.task(managed=True);change_state(family,'PAUSED');account=self.account(tasks=[family])
        self.assertTrue(all(self.view(account)['continuous']['task_paused'].values()))
        r=self.advance(account,'2024-11-11',task_files=[family])
        self.assertIn('TASK_PAUSED',r['outcome']['sessions'][0]['decisions'][0]['signal']['reason'])
        self.assertEqual(self.view(account)['cash'],'10000')

    def test_copy_tasks_cannot_double_consume_buy_and_shared_funds_limit_applies(self):
        a=self.task('a');b=self.task('b',initial_cash=99999);account=self.account(tasks=[a,b])
        r=self.advance(account,'2024-11-11');decisions=r['outcome']['sessions'][0]['decisions']
        self.assertEqual([d['decision']['status'] for d in decisions],['RESERVED','DUPLICATE_SIGNAL'])
        other=snapshot(symbol='OTHER')
        c=self.task('c','price.buy_and_hold@1',data=other,params={'target_position_pct':.9})
        d=self.task('d',params=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.08),
            risk=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0))
        account=self.account('competition',[c,d])
        r=advance_continuous_account(account,{self.security:self.data.document,other.document['security']['security_id']:other.document},
            through='2024-11-11',observed_at=OBSERVED,operation_id='competition')
        self.assertEqual(r['outcome']['sessions'][0]['decisions'][1]['decision']['reason'],'INSUFFICIENT_AVAILABLE_FUNDS')
        self.assertEqual(self.view(account)['reserved_cash'],'0')

    def test_imported_unverified_is_not_mislabelled_synthetic_and_legacy_unchanged(self):
        imported=snapshot(imported=True);task=self.task('imported',data=imported);account=self.account(tasks=[task])
        r=self.advance(account,'2024-11-11',imported);self.assertEqual(r['outcome']['status'],'CURRENT')
        self.assertEqual(self.view(account)['evidence_kind'],'IMPORTED_UNVERIFIED')
        self.assertIn('unverified',' '.join(self.view(account)['limitations']))
        old=self.root/'old';shared_account.create_shared_account(old,shared_account.demo_account_config())
        original=(old/'account.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'legacy_account'):self.view(old)
        self.assertEqual((old/'account.json').read_bytes(),original)
        with self.assertRaisesRegex(ValueError,'verified_incremental_ingress'):
            shared_account.transact_shared_account(account,operation_id='manual-mark',kind='MARK',at=self.view(account)['state']['current_at'],payload={'prices':{}})

    def test_commit_response_loss_receipt_lookup_conflicts_and_rollback(self):
        account=self.account();original=shared_account._connection
        @contextmanager
        def lost_response(directory,write=False):
            with original(directory,write=write) as connection:
                yield connection
                if write:raise RuntimeError('simulated_response_lost_after_commit')
        with patch.object(shared_account,'_connection',lost_response):
            with self.assertRaisesRegex(RuntimeError,'response_lost'):self.advance(account,'2024-11-11')
        receipt=lookup_continuous_receipt(account,'advance')
        self.assertEqual(receipt['status'],'COMMITTED')
        self.assertEqual(self.advance(account,'2024-11-11'),receipt['receipt'])
        with self.assertRaisesRegex(ValueError,'operation_id_payload_conflict'):self.advance(account)
        before=self.view(account)['receipt_head']
        with patch.object(shared_account,'_transition',side_effect=RuntimeError('precommit-failure')):
            with self.assertRaisesRegex(RuntimeError,'precommit'):self.advance(account,op='rollback')
        self.assertEqual(lookup_continuous_receipt(account,'rollback')['status'],'NOT_RECORDED')
        self.assertEqual(self.view(account)['receipt_head'],before)

    def test_concurrent_processes_use_one_ledger_cursor_and_restart_verifies(self):
        account=self.account();snapshot_path=self.root/'incoming.json';snapshot_path.write_bytes(canonical_bytes(self.data.document))
        script='''import json,sys
from hakimi_research.continuous_runtime import advance_continuous_account
p=json.load(open(sys.argv[2],encoding="utf-8"))
r=advance_continuous_account(sys.argv[1],{p["security"]["security_id"]:p},through="2024-11-11",observed_at="2024-12-04T00:00:00Z",operation_id=sys.argv[3])
print(r["outcome"]["status"])
'''
        processes=[subprocess.Popen([sys.executable,'-c',script,str(account),str(snapshot_path),'process-'+str(i)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i in range(2)]
        results=[p.communicate(timeout=30) for p in processes]
        self.assertEqual([p.returncode for p in processes],[0,0],results)
        self.assertEqual(sorted(o.strip() for o,e in results),['CURRENT','NO_NEW_SESSIONS'])
        self.assertEqual(len(self.view(account)['continuous']['session_results']),1)
        conn=sqlite3.connect(account/'ledger.sqlite3');raw=conn.execute('SELECT receipt FROM events WHERE seq=1').fetchone()[0]
        value=json.loads(raw);value['state_hash']='0'*64;conn.execute('UPDATE events SET receipt=? WHERE seq=1',(canonical_bytes(value),));conn.commit();conn.close()
        with self.assertRaisesRegex(ValueError,'journal_identity'):self.view(account)

    def test_loss_halt_survives_next_day_and_requires_explicit_later_reset(self):
        task=self.task();limits={**LIMITS,'max_daily_loss_pct':.005};account=self.account(tasks=[task],limits=limits)
        self.advance(account,'2024-11-11')
        data=snapshot(changes={'2024-11-12':[90,95,89,92,10000]})
        self.advance(account,'2024-11-12',data,op='loss');view=self.view(account)
        self.assertTrue(view['state']['loss_halted'])
        with self.assertRaisesRegex(ValueError,'later_completed'):reset_continuous_loss(account,operation_id='early-reset',expected_head=view['receipt_head'])
        self.advance(account,'2024-11-13',data,op='next-day');view=self.view(account)
        self.assertTrue(view['state']['loss_halted'])
        reset_continuous_loss(account,operation_id='reset',expected_head=view['receipt_head'])
        self.assertFalse(self.view(account)['state']['loss_halted'])
        self.assertEqual(self.view(account)['continuous']['status'],'CURRENT')


    def test_single_task_costs_and_protection_match_formal_batch_engine(self):
        from hakimi_research.offline_app import check_task
        from hakimi_research.strategy_registry import run_strategy
        for key in ['price.dual_ma@1','price.buy_and_hold@1']:
            with self.subTest(key=key):
                data=snapshot(changes={'2024-11-12':[104,120,90,103,10000]})
                task=self.task(key.replace('@','-'),key,data=data,initial_cash=10000,fee_rate=.001,slippage_pct=.0005)
                checked=check_task(task)
                expected=run_strategy(key,checked['snapshot'],checked['semantics']['experiment'],None).document['result']
                account=self.account('parity-'+key,[task]);self.advance(account,data=data);view=self.view(account)
                actual=[r['fill'] for r in view['state']['intents'].values() if r['fill']]
                self.assertEqual([f['action'] for f in actual],[f['action'] for f in expected['fills']])
                for a,b in zip(actual,expected['fills']):
                    for field in ['quantity','price','fee','pnl']:self.assertAlmostEqual(a[field],b[field],places=9)
                self.assertAlmostEqual(float(view['cash']),expected['final_cash'],places=8)
                self.assertAlmostEqual(float(view['equity']),expected['final_equity'],places=8)

    def test_two_owners_exit_their_own_slots_during_global_pause(self):
        a=self.task('owner-a',managed=True)
        b=self.task('owner-b',managed=True,params=dict(fast_window=2,slow_window=4,position_pct=.5,stop_loss_pct=.03,take_profit_pct=.08),
            risk=dict(max_position_pct=.6,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0))
        account=self.account(tasks=[a,b]);self.advance(account,'2024-11-11')
        before=self.view(account);self.assertEqual(len(before['state']['positions']),2)
        shared_account.transact_shared_account(account,operation_id='global-pause',kind='PAUSE',at=before['state']['current_at'],payload={'reason':'user pause new buys'})
        data=snapshot(changes={'2024-11-12':[90,95,89,92,10000]})
        r=self.advance(account,'2024-11-12',data,op='exit-both')
        reductions=[d for d in r['outcome']['sessions'][0]['decisions'] if d['signal']['action']=='EXIT']
        self.assertEqual(len(reductions),2);self.assertEqual(len({d['owner'] for d in reductions}),2)
        self.assertTrue(all(d['decision']['settlement']['status']=='SETTLED' for d in reductions))
        self.assertTrue(all(Decimal(p['quantity'])==0 for p in self.view(account)['state']['positions'].values()))
        self.assertTrue(self.view(account)['state']['paused'])

    def test_selected_task_revision_change_stops_new_buys_but_keeps_old_position_protection(self):
        from hakimi_research.task_manager import revise_family
        family=self.task(managed=True);account=self.account(tasks=[family]);self.advance(account,'2024-11-11')
        revise_family(family,params=dict(fast_window=2,slow_window=4,position_pct=.2,stop_loss_pct=.01,take_profit_pct=.04))
        data=snapshot(changes={'2024-11-12':[104,120,90,103,10000]})
        r=self.advance(account,'2024-11-12',data,op='revised-family',task_files=[family])
        exit_row=next(d for d in r['outcome']['sessions'][0]['decisions'] if d['signal']['action']=='EXIT')
        self.assertAlmostEqual(exit_row['reference_price'],104*.97) # original bound 3%, not revised 1%
        view=self.view(account);self.assertTrue(view['continuous']['task_configuration_warnings'])
        owner=next(iter(view['continuous']['task_paused']))
        with self.assertRaisesRegex(ValueError,'restore_bound'):set_continuous_task_state(account,owner,False,operation_id='unsafe-unpause')

    def test_event_schedule_filters_existing_price_buy_and_explains_impact(self):
        from importlib.resources import files
        from hakimi_research.equity_events import _METADATA_FIELDS,build_equity_event
        from hakimi_research.equity_event_context import build_event_context
        template=json.loads(files('hakimi_research').joinpath('resources/trade-demo-event-context.json').read_bytes())['events'][0]
        metadata={k:deepcopy(template[k]) for k in _METADATA_FIELDS|{'schedule'}}
        metadata['security_id']=self.security
        event=build_equity_event(base64.b64decode(template['raw']['content_base64']),metadata)
        context=build_event_context([event],self.security);path=self.workspace/'context.json';path.write_bytes(canonical_bytes(context))
        task=self.task('schedule','event.earnings_schedule@1',event_context=path);account=self.account(tasks=[task])
        r=self.advance(account,'2024-11-11');decision=r['outcome']['sessions'][0]['decisions'][0]
        self.assertEqual(decision['signal']['action'],'HOLD')
        self.assertEqual(decision['research_review']['decision']['input_action'],'BUY')
        self.assertEqual(decision['research_review']['decision']['disposition'],'BLOCK_NEW_BUY')
        self.assertEqual(decision['research_review']['decision']['blocking_event_hashes'],[event['event_hash']])
        self.assertEqual(self.view(account)['cash'],'10000')

    def test_future_receipt_unavailable_bar_lag_revision_and_missing_calendar_are_explicit(self):
        account=self.account()
        r=advance_continuous_account(account,{self.security:self.data.document},through='2024-12-03',
            observed_at='2024-12-03T20:00:00Z',operation_id='future-receipt')
        self.assertIn('FUTURE_RECEIPT',r['outcome']['reason'])
        self.advance(account,'2024-11-11')
        r=self.advance(account,data=snapshot(lag=61),op='lag-changed')
        self.assertIn('DATA_IDENTITY_REVISED',r['outcome']['reason'])
        # A structurally damaged snapshot cannot pass the formal raw-input verifier.
        damaged=deepcopy(self.data.document);damaged['candles'].pop(16)
        r=advance_continuous_account(account,{self.security:damaged},through='2024-12-03',observed_at=OBSERVED,operation_id='missing-row')
        self.assertEqual(r['outcome']['status'],'BLOCKED')
        self.assertEqual(self.view(account)['continuous']['last_session'],'2024-11-11')

    def test_manual_pause_is_not_cleared_by_enabled_family_and_layers_resume_independently(self):
        family=self.task(managed=True);account=self.account(tasks=[family]);owner=next(iter(self.view(account)['continuous']['task_paused']))
        set_continuous_task_state(account,owner,True,operation_id='manual-pause')
        r=self.advance(account,'2024-11-11',task_files=[family])
        self.assertIn('TASK_PAUSED',r['outcome']['sessions'][0]['decisions'][0]['signal']['reason'])
        change_state(family,'PAUSED')
        self.advance(account,'2024-11-12',op='family-pause',task_files=[family])
        set_continuous_task_state(account,owner,False,operation_id='manual-resume')
        self.assertTrue(self.view(account)['continuous']['task_paused'][owner])
        self.assertFalse(self.view(account)['continuous']['manual_task_paused'][owner])
        change_state(family,'ENABLED')
        self.advance(account,'2024-11-13',op='family-resume',task_files=[family])
        self.assertFalse(self.view(account)['continuous']['task_paused'][owner])

    def test_missing_task_state_stops_new_buys_and_keeps_frozen_protection(self):
        task=self.task();account=self.account(tasks=[task]);self.advance(account,'2024-11-11')
        missing=self.workspace/'tasks'/'missing.json'
        data=snapshot(changes={'2024-11-12':[90,95,89,92,10000]})
        r=self.advance(account,'2024-11-12',data,op='missing-task',task_files=[missing])
        self.assertTrue(any(d['signal']['action']=='EXIT' for d in r['outcome']['sessions'][0]['decisions']))
        self.assertTrue(self.view(account)['continuous']['task_configuration_warnings'])

    def test_declared_lag_that_misses_next_open_is_rejected_without_fake_signal_clock(self):
        delayed=snapshot(lag=86400);task=self.task(data=delayed)
        with self.assertRaisesRegex(ValueError,'PRIOR_BAR_UNAVAILABLE'):
            self.account(tasks=[task])
        self.assertFalse((self.root/'account').exists())

    def test_view_projects_current_pause_controls_without_replaying_or_rewriting_sessions(self):
        account=self.account();owner=next(iter(self.view(account)['continuous']['task_paused']))
        before=self.view(account)
        shared_account.transact_shared_account(account,operation_id='global-pause',kind='PAUSE',at=before['state']['current_at'],payload={'reason':'user'})
        paused=self.view(account);self.assertEqual(paused['continuous']['status'],'PAUSED_NEW_ENTRIES')
        shared_account.transact_shared_account(account,operation_id='global-resume',kind='RESUME',at=paused['state']['current_at'],payload={'expected_head':paused['receipt_head']})
        self.assertEqual(self.view(account)['continuous']['status'],'READY')
        self.advance(account,'2024-11-11')
        set_continuous_task_state(account,owner,True,operation_id='owner-pause')
        self.assertEqual(self.view(account)['continuous']['status'],'PAUSED_NEW_ENTRIES')
        set_continuous_task_state(account,owner,False,operation_id='owner-resume')
        current=self.view(account);self.assertEqual(current['continuous']['status'],'CURRENT')
        self.assertIsNone(current['continuous']['stop_reason'])
        state=current['state'];head=current['receipt_head']
        self.assertEqual(self.view(account)['state'],state);self.assertEqual(self.view(account)['receipt_head'],head)
        self.advance(account,'2024-12-04',op='stale')
        set_continuous_task_state(account,owner,True,operation_id='pause-while-stale')
        self.assertEqual(self.view(account)['continuous']['status'],'BLOCKED')


if __name__=='__main__':unittest.main()
