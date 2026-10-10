"""Existing registered rules feed the same synthetic account admission."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.documents import read_document
from hakimi_research.input_workflow import import_content_packet
from hakimi_research.shared_account import create_shared_account,demo_account_config,describe_shared_account,transact_shared_account
from hakimi_research.shared_signals import step_shared_tasks
from hakimi_research.strategy_registry import strategies
from hakimi_research.trade_cli import create_task,initialize_demo

AT='2024-11-11T14:30:00Z'
SECURITY='SYNTHETIC:RESEARCH:TEST'


class SharedSignalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.workspace=self.root/'workspace'
        examples=initialize_demo(self.workspace)['input_examples'];self.snapshot=next((self.workspace/'data').glob('equity_dataset_*.json'))
        self.context=Path(import_content_packet(examples['packet'],self.workspace,event_id=examples['event_id'],
            texts_dir=examples['texts_dir'],originals_dir=examples['originals_dir'],synthetic=True)['path'])
        self.account=self.root/'account';self.config=demo_account_config();self.config['as_of']=AT
        self.config['securities'][SECURITY]['price']=104
    def tearDown(self):self.temp.cleanup()
    def init(self):return create_shared_account(self.account,self.config)
    def task(self,name,key,**changes):
        options=dict(strategy=key,snapshot=self.snapshot,score_start='2024-11-11',score_end='2024-12-03',fee_rate=0,slippage_pct=0,initial_cash=1234)
        if key=='price.buy_and_hold@1':options['params']=dict(target_position_pct=.8)
        elif key.startswith('content.'):
            options.update(params=dict(position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06),event_context=self.context)
        else:
            options['params']=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06)
            if key.startswith('event.'):options['event_context']=self.workspace/'data/event-context.json'
        if key!='price.buy_and_hold@1':options['risk']=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0)
        options.update(changes)
        return create_task(self.workspace/'tasks'/(name+'.json'),**options)

    def test_real_price_and_benchmark_requests_use_account_nav_and_shared_cash(self):
        a=self.task('benchmark','price.buy_and_hold@1');b=self.task('active','price.dual_ma@1');self.init()
        with patch('hakimi_research.offline_app.run_strategy',side_effect=AssertionError('independent backtest called')):
            receipt=step_shared_tasks(self.account,[a,b],operation_id='cohort',at=AT)
        d=receipt['outcome']['decisions'];self.assertEqual([r['status'] for r in d],['RESERVED','REJECTED'])
        self.assertEqual(d[1]['reason'],'INSUFFICIENT_AVAILABLE_FUNDS')
        self.assertEqual(Decimal(d[0]['reserved_cash']),8000);self.assertEqual(Decimal(describe_shared_account(self.account)['available_cash']),2000)
        intent=describe_shared_account(self.account)['state']['intents'][d[0]['intent_id']]
        self.assertFalse(intent['proposal']['source']['independent_task_capital_applied'])
        self.assertIn('single score-start entry attempt',intent['proposal']['signal']['reason'])

    def test_all_five_registered_adapters_feed_one_account_without_independent_runs(self):
        tasks=[self.task(str(i),k) for i,k in enumerate(strategies())];self.init()
        before={p:sha256(p.read_bytes()).hexdigest() for p in self.workspace.rglob('*') if p.is_file()}
        with patch('hakimi_research.backtest.BacktestEngine.run',side_effect=AssertionError('backtest called')):
            r=step_shared_tasks(self.account,tasks,operation_id='all-five',at=AT)
        self.assertEqual(len(r['outcome']['decisions']),5)
        self.assertEqual([t['semantics']['strategy'] for t in r['request']['payload']['tasks']],list(strategies()))
        self.assertLessEqual(Decimal(describe_shared_account(self.account)['reserved_cash']),10000)
        self.assertEqual(before,{p:sha256(p.read_bytes()).hexdigest() for p in self.workspace.rglob('*') if p.is_file()})
        self.assertFalse((self.workspace/'runs').exists())

    def test_task_copy_or_independent_capital_edit_cannot_repeat_same_signal(self):
        a=self.task('original','price.buy_and_hold@1');b=self.task('copy','price.buy_and_hold@1',initial_cash=99999);self.init()
        r=step_shared_tasks(self.account,[a,b],operation_id='copies',at=AT)
        self.assertEqual([d['status'] for d in r['outcome']['decisions']],['RESERVED','DUPLICATE_SIGNAL'])
        self.assertEqual(Decimal(describe_shared_account(self.account)['reserved_cash']),8000)

    def managed_pair(self,key='price.dual_ma@1'):
        from hakimi_research.task_manager import create_family,read_family
        families=[self.workspace/'tasks'/name for name in ['owner-a','owner-b']]
        options=dict(strategy=key,snapshot=self.snapshot,score_start='2024-11-11',score_end='2024-12-03',fee_rate=0,slippage_pct=0)
        if key=='price.buy_and_hold@1':options['params']=dict(target_position_pct=.8)
        else:
            options['params']=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06)
            options['risk']=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0)
        for index,family in enumerate(families):create_family(family,initial_cash=[1234,99999][index],**options)
        return families,['family:'+read_family(f)['family_id'] for f in families]

    def owned_config(self,owners):
        config=deepcopy(self.config)
        config['initial_positions']=[dict(owner=owner,security_id=SECURITY,quantity=quantity,
            avg_entry_price=90,entry_fees=0,realized_pnl=0) for owner,quantity in zip(owners,[10,20])]
        return config

    def test_registered_owner_exits_reserve_and_settle_both_slots_under_all_guards(self):
        families,owners=self.managed_pair()
        for order in [[0,1],[1,0]]:
            for guard in ['normal','paused','loss']:
                with self.subTest(order=order,guard=guard):
                    account=self.root/('account-'+str(order[0])+'-'+guard);config=self.owned_config(owners)
                    if guard=='loss':
                        config['as_of']='2024-11-11T14:00:00Z';config['securities'][SECURITY]['price']=120
                        config['limits']['max_daily_loss_pct']=.01
                    create_shared_account(account,config)
                    if guard=='paused':transact_shared_account(account,operation_id='pause',kind='PAUSE',at=AT,payload=dict(reason='synthetic'))
                    if guard=='loss':
                        transact_shared_account(account,operation_id='loss',kind='MARK',at=AT,payload=dict(prices={SECURITY:104}))
                        self.assertTrue(describe_shared_account(account)['state']['loss_halted'])
                    receipt=step_shared_tasks(account,[families[i] for i in order],operation_id='exit',at=AT)
                    decisions=receipt['outcome']['decisions']
                    self.assertEqual([d['status'] for d in decisions],['RESERVED','RESERVED'])
                    self.assertEqual([Decimal(d['requested_quantity']) for d in decisions],[[10,20][i] for i in order])
                    view=describe_shared_account(account)
                    self.assertEqual(Decimal(view['cash']),10000);self.assertEqual(Decimal(view['available_cash']),10000)
                    self.assertEqual(Decimal(view['reserved_cash']),0)
                    self.assertEqual(len(view['state']['opportunities']),2)
                    for number,d in enumerate(decisions):
                        r=transact_shared_account(account,operation_id='fill-'+str(number),kind='SETTLE',at=AT,payload=dict(intent_id=d['intent_id']))
                        self.assertEqual(r['outcome']['status'],'SETTLED')
                        positions={p['owner']:Decimal(p['quantity']) for p in describe_shared_account(account)['state']['positions'].values()}
                        self.assertEqual(positions[owners[order[number]]],0)
                        if number==0:self.assertEqual(positions[owners[order[1]]],[10,20][order[1]])
                    self.assertEqual(Decimal(describe_shared_account(account)['cash']),13120)
                    self.assertEqual(transact_shared_account(account,operation_id='fill-again',kind='SETTLE',at=AT,
                        payload=dict(intent_id=decisions[0]['intent_id']))['outcome']['status'],'ALREADY_TERMINAL')
                    self.assertEqual(Decimal(describe_shared_account(account)['cash']),13120)

    def test_owner_exit_cancel_and_task_revision_cannot_reopen_same_clock(self):
        from hakimi_research.task_manager import revise_family,read_family
        families,owners=self.managed_pair();self.config=self.owned_config(owners);self.init()
        receipt=step_shared_tasks(self.account,[families[0]],operation_id='exit',at=AT)
        self.assertEqual(step_shared_tasks(self.account,[families[0]],operation_id='exit',at=AT),receipt)
        self.assertEqual(step_shared_tasks(self.account,[families[0]],operation_id='other-op',at=AT)['outcome']['decisions'][0]['status'],'DUPLICATE_SIGNAL')
        transact_shared_account(self.account,operation_id='cancel',kind='CANCEL',at=AT,
            payload=dict(intent_id=receipt['outcome']['decisions'][0]['intent_id'],reason='synthetic review'))
        original_family=read_family(families[0])['family_id']
        revise_family(families[0],initial_cash=77777,params=dict(fast_window=2,slow_window=4,position_pct=.7,stop_loss_pct=.02,take_profit_pct=.05))
        self.assertEqual(read_family(families[0])['family_id'],original_family)
        self.assertEqual(step_shared_tasks(self.account,[families[0]],operation_id='changed-version',at=AT)['outcome']['decisions'][0]['status'],'DUPLICATE_SIGNAL')
        before=describe_shared_account(self.account)
        with self.assertRaisesRegex(ValueError,'operation_id_payload_conflict'):
            step_shared_tasks(self.account,[families[0]],operation_id='exit',at=AT)
        self.assertEqual(describe_shared_account(self.account),before)
        self.assertEqual({p['owner']:Decimal(p['quantity']) for p in before['state']['positions'].values()},dict(zip(owners,[10,20])))
        self.assertEqual(sum(r['status']=='RESERVED' for r in before['state']['intents'].values()),0)
        second=step_shared_tasks(self.account,[families[1]],operation_id='other-owner',at=AT)['outcome']['decisions'][0]
        self.assertEqual(second['status'],'RESERVED');self.assertEqual(Decimal(second['requested_quantity']),20)

    def test_managed_buy_copies_still_share_one_global_opportunity(self):
        families,_=self.managed_pair('price.buy_and_hold@1');self.init()
        r=step_shared_tasks(self.account,families,operation_id='copied-buy',at=AT)
        self.assertEqual([d['status'] for d in r['outcome']['decisions']],['RESERVED','DUPLICATE_SIGNAL'])
        self.assertEqual(Decimal(describe_shared_account(self.account)['reserved_cash']),8000)

    def test_managed_version_changes_preserve_owned_position_and_pause_guard(self):
        from hakimi_research.task_manager import create_family,revise_family,change_state,read_family
        family=self.workspace/'tasks/managed'
        create_family(family,strategy='price.buy_and_hold@1',snapshot=self.snapshot,params=dict(target_position_pct=.8),
            score_start='2024-11-11',score_end='2024-12-03',fee_rate=0,slippage_pct=0)
        self.init();r=step_shared_tasks(self.account,[family],operation_id='managed-entry',at=AT)
        intent=r['outcome']['decisions'][0]['intent_id']
        transact_shared_account(self.account,operation_id='fill',kind='SETTLE',at=AT,payload=dict(intent_id=intent))
        before=describe_shared_account(self.account)
        owner='family:'+read_family(family)['family_id']
        self.assertEqual(list(before['state']['positions'].values())[0]['owner'],owner)
        revise_family(family,initial_cash=99999,params=dict(target_position_pct=.7))
        r=step_shared_tasks(self.account,[family],operation_id='new-version',at=AT)
        self.assertEqual(r['outcome']['decisions'][0]['status'],'HOLD')
        self.assertEqual(describe_shared_account(self.account)['cash'],before['cash'])
        change_state(family,'PAUSED')
        with self.assertRaisesRegex(ValueError,'task_paused'):step_shared_tasks(self.account,[family],operation_id='paused',at=AT)

    def test_task_pause_and_wrong_mark_are_rejected_before_account_publication(self):
        task=self.task('benchmark','price.buy_and_hold@1');self.init()
        value=read_document(task);value['state']='PAUSED'
        from hakimi_research.documents import canonical_bytes
        task.write_bytes(canonical_bytes(value))
        with self.assertRaisesRegex(ValueError,'task_paused'):step_shared_tasks(self.account,[task],operation_id='paused',at=AT)
        self.assertEqual(describe_shared_account(self.account)['sequence'],0)
        value['state']='ENABLED';task.write_bytes(canonical_bytes(value))
        transact_shared_account(self.account,operation_id='later-mark',kind='MARK',at='2024-11-11T15:30:00Z',payload=dict(prices={SECURITY:104}))
        with self.assertRaisesRegex(ValueError,'clock_cannot_move'):step_shared_tasks(self.account,[task],operation_id='stale',at=AT)
        self.assertEqual(describe_shared_account(self.account)['sequence'],1)

    def test_benchmark_rejection_is_not_retried_at_next_session(self):
        task=self.task('benchmark','price.buy_and_hold@1');self.config['limits']['max_total_position_pct']=.5;self.init()
        r=step_shared_tasks(self.account,[task],operation_id='initial',at=AT)
        self.assertEqual(r['outcome']['decisions'][0]['status'],'REJECTED')
        tomorrow='2024-11-12T14:30:00Z'
        from hakimi_research.equity_dataset import EquitySnapshot
        snapshot=read_document(self.snapshot)
        index=next(i for i,s in enumerate(snapshot['sessions']) if s['open_utc']==tomorrow)
        price=float(EquitySnapshot(snapshot).frame().iloc[index]['open'])
        transact_shared_account(self.account,operation_id='next-mark',kind='MARK',at=tomorrow,payload=dict(prices={SECURITY:price}))
        head=describe_shared_account(self.account)['receipt_head'];transact_shared_account(self.account,operation_id='next-day',kind='DAY_RESET',at=tomorrow,payload=dict(expected_head=head))
        r=step_shared_tasks(self.account,[task],operation_id='next-signal',at=tomorrow)
        self.assertEqual(r['outcome']['decisions'][0]['status'],'HOLD');self.assertEqual(Decimal(describe_shared_account(self.account)['reserved_cash']),0)

    def test_content_unknown_and_outside_opportunity_are_hold_with_saved_reason(self):
        tasks=[self.task('content-c','content.price_confirmation@1'),self.task('content-d','content.reviewed_outlook@1')];self.init()
        r=step_shared_tasks(self.account,tasks,operation_id='content',at=AT)
        self.assertEqual([d['status'] for d in r['outcome']['decisions']],['HOLD','HOLD'])
        view=describe_shared_account(self.account)
        for d in r['outcome']['decisions']:
            self.assertIn('research_review',view['state']['intents'][d['intent_id']]['proposal']['source'])


if __name__=='__main__':unittest.main()
