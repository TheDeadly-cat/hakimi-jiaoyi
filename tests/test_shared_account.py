"""One account, real process contention and durable crash outcomes."""
from copy import deepcopy
import base64
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from importlib.resources import files
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from hakimi_research.documents import canonical_bytes,digest,parse_document
from hakimi_research.models import Signal
from hakimi_research.shared_account import create_shared_account,demo_account_config,describe_shared_account,transact_shared_account,opportunity_identity
from hakimi_research.shared_signals import demo_competing_intents,fixed_signal_proposal

AT='2024-11-08T14:30:00Z'
SECURITY='SYNTHETIC:RESEARCH:TEST'


class SharedAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.account=self.root/'account'
        self.config=demo_account_config();self.inputs=demo_competing_intents()
    def tearDown(self):self.temp.cleanup()
    def init(self,config=None):return create_shared_account(self.account,config or self.config)
    def transact(self,op,kind,payload,at=AT):return transact_shared_account(self.account,operation_id=op,kind=kind,at=at,payload=payload)
    def reserve(self,op='reserve',inputs=None):return self.transact(op,'RESERVE',dict(intents=inputs or self.inputs))
    def view(self):return describe_shared_account(self.account)
    def first(self,r):return r['outcome']['decisions'][0]['intent_id']
    def reidentify(self,p):p['opportunity_id']=opportunity_identity(p);return p

    def test_two_8000_requests_share_one_10000_balance_and_reopen(self):
        self.init();r=self.reserve();d=r['outcome']['decisions']
        self.assertEqual([v['status'] for v in d],['RESERVED','REJECTED'])
        self.assertEqual(d[1]['reason'],'INSUFFICIENT_AVAILABLE_FUNDS')
        self.assertEqual(Decimal(self.view()['reserved_cash']),8000);self.assertEqual(Decimal(self.view()['available_cash']),2000)
        self.assertEqual(self.reserve(),r);self.assertEqual(self.view()['sequence'],1)
        with self.assertRaisesRegex(ValueError,'operation_id_payload_conflict'):self.reserve(inputs=[self.inputs[1]])
        self.assertEqual(self.view()['sequence'],1)
        self.assertEqual(Decimal(d[0]['requested_quantity']),Decimal(d[1]['requested_quantity']))

    def test_cancel_reject_and_repeat_do_not_leak_or_reopen_funds(self):
        self.init();identity=self.first(self.reserve());self.transact('cancel','CANCEL',dict(intent_id=identity,reason='synthetic cancel'))
        self.assertEqual(Decimal(self.view()['reserved_cash']),0)
        d=self.reserve('repeat')['outcome']['decisions'];self.assertEqual([v['status'] for v in d],['ALREADY_RECORDED']*2)
        self.assertEqual(d[0]['original_status'],'CANCELLED');self.assertEqual(Decimal(self.view()['available_cash']),10000)
        fresh=deepcopy(self.inputs[0]);fresh['source']['signal_key']='new-explicit-opportunity';self.reidentify(fresh)
        identity=self.first(self.reserve('fresh',[fresh]));self.transact('reject','REJECT',dict(intent_id=identity,reason='synthetic reject'))
        self.assertEqual(Decimal(self.view()['reserved_cash']),0)
        self.assertEqual(self.transact('late-fill','SETTLE',dict(intent_id=identity))['outcome']['status'],'ALREADY_TERMINAL')

    def test_changed_payload_of_same_signal_cannot_reserve_twice(self):
        self.init();self.reserve(inputs=[self.inputs[0]])
        p=deepcopy(self.inputs[0]);p['signal']['reason']='another caller text'
        d=self.reserve('other-operation',[p])['outcome']['decisions'][0]
        self.assertEqual(d['status'],'DUPLICATE_SIGNAL');self.assertEqual(Decimal(self.view()['reserved_cash']),8000)

    def test_future_reserve_clock_cannot_burn_a_valid_execution_opportunity(self):
        self.init();later='2024-11-08T15:30:00Z'
        with self.assertRaisesRegex(ValueError,'requires_current_account_clock'):
            self.transact('wrong-clock','RESERVE',dict(intents=[self.inputs[0]]),at=later)
        self.assertEqual(self.view()['sequence'],0);self.assertEqual(self.view()['state']['current_at'],AT)
        identity=self.first(self.reserve(inputs=[self.inputs[0]]))
        self.assertEqual(self.transact('valid-fill','SETTLE',dict(intent_id=identity))['outcome']['status'],'SETTLED')

    def test_unknown_lifecycle_operations_do_not_poison_another_reservation_clock(self):
        self.init();identity=self.first(self.reserve(inputs=[self.inputs[0]]));later='2024-11-08T15:30:00Z'
        for kind in ['CANCEL','REJECT','SETTLE']:
            payload=dict(intent_id='unknown')
            if kind!='SETTLE':payload['reason']='synthetic unknown'
            before=self.view()
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'requires_current_account_clock'):
                self.transact('wrong-'+kind,kind,payload,at=later)
            self.assertEqual(self.view(),before)
            self.assertEqual(self.transact('current-'+kind,kind,payload)['outcome']['status'],'INTENT_NOT_FOUND')
            self.assertEqual(self.view()['state']['current_at'],AT)
        self.assertEqual(self.transact('valid-fill','SETTLE',dict(intent_id=identity))['outcome']['status'],'SETTLED')

    def test_terminal_no_op_wrong_clock_cannot_expire_a_second_reservation(self):
        self.init();inputs=deepcopy(self.inputs)
        for p in inputs:p['signal']['size_pct']=.4
        r=self.reserve(inputs=inputs);one,two=[d['intent_id'] for d in r['outcome']['decisions']]
        self.transact('cancel-one','CANCEL',dict(intent_id=one,reason='synthetic release'))
        for kind in ['CANCEL','REJECT','SETTLE']:
            payload=dict(intent_id=one)
            if kind!='SETTLE':payload['reason']='repeat'
            before=self.view()
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'requires_current_account_clock'):
                self.transact('late-'+kind,kind,payload,at='2024-11-08T15:30:00Z')
            self.assertEqual(self.view(),before)
        self.assertEqual(self.transact('fill-two','SETTLE',dict(intent_id=two))['outcome']['status'],'SETTLED')

    def test_original_installed_v1_bytes_are_read_only_without_resigning(self):
        fixture=json.loads(files('hakimi_research').joinpath('resources/shared-account-v1.json').read_bytes())
        self.account.mkdir()
        for name,proof in fixture['files'].items():
            raw=base64.b64decode(proof['base64']);self.assertEqual(sha256(raw).hexdigest(),proof['sha256'])
            (self.account/name).write_bytes(raw)
        view=self.view();self.assertTrue(view['legacy_read_only']);self.assertEqual(view['clock_policy'],'LEGACY_V1_REPLAY_ONLY')
        self.assertEqual(view['sequence'],1);self.assertEqual(Decimal(view['reserved_cash']),8000)
        with self.assertRaisesRegex(ValueError,'legacy_v1_account_is_read_only'):
            self.transact('new-write','PAUSE',dict(reason='blocked'))
        for name,proof in fixture['files'].items():self.assertEqual(sha256((self.account/name).read_bytes()).hexdigest(),proof['sha256'])

    def test_existing_directory_and_invalid_payloads_leave_account_unchanged(self):
        self.account.mkdir();(self.account/'original').write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError,'new_account_directory'):self.init()
        self.assertEqual((self.account/'original').read_bytes(),b'preserve')
        other=self.root/'other';create_shared_account(other,self.config)
        for payload in [dict(intents=[None]),dict(intents=[dict(source=[])])]:
            with self.assertRaises(ValueError):transact_shared_account(other,operation_id='bad',kind='RESERVE',at=AT,payload=payload)
            self.assertEqual(describe_shared_account(other)['sequence'],0)

    def test_canonical_fee_and_slippage_fill_preserves_shared_funds(self):
        self.init();p=deepcopy(self.inputs[0]);p.update(fee_rate=.02,slippage_pct=.01)
        r=self.reserve(inputs=[p]);row=r['outcome']['decisions'][0]
        self.assertEqual(row['status'],'RESERVED')
        cash=Decimal(self.view()['cash']);reserved=Decimal(self.view()['reserved_cash'])
        r=self.transact('cost-fill','SETTLE',dict(intent_id=row['intent_id']))
        self.assertEqual(r['outcome']['status'],'SETTLED')
        fill=r['outcome']['fill'];debit=Decimal(str(fill['quantity']*fill['price']+fill['fee']))
        self.assertLessEqual(debit,reserved);self.assertEqual(Decimal(self.view()['cash']),cash-debit)
        self.assertEqual(Decimal(self.view()['reserved_cash']),0)

    def test_global_total_symbol_and_cash_floor_cannot_be_bypassed(self):
        cases=[('GLOBAL_TOTAL_POSITION_LIMIT',dict(max_total_position_pct=.7)),
            ('GLOBAL_SECURITY_POSITION_LIMIT',dict(max_symbol_position_pct=.7)),('GLOBAL_CASH_FLOOR',dict(min_cash_pct=.3))]
        for reason,limits in cases:
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as path:
                config=deepcopy(self.config);config['limits'].update(limits);account=Path(path)/'account';create_shared_account(account,config)
                r=transact_shared_account(account,operation_id='r',kind='RESERVE',at=AT,payload=dict(intents=[self.inputs[0]]))
                self.assertEqual(r['outcome']['decisions'][0]['reason'],reason)
                self.assertEqual(Decimal(describe_shared_account(account)['reserved_cash']),0)

    def test_pending_costs_are_included_before_global_exposure_approval(self):
        config=deepcopy(self.config);config['limits']['max_total_position_pct']=.97
        config['securities']['SYNTHETIC:OTHER']=dict(symbol='OTHER',price=100);self.init(config)
        a,b=deepcopy(self.inputs)
        for p in [a,b]:p['signal']['size_pct']=.48;p['fee_rate']=.02
        b['security_id']='SYNTHETIC:OTHER'
        d=self.reserve(inputs=[self.reidentify(a),self.reidentify(b)])['outcome']['decisions']
        self.assertEqual(d[0]['status'],'RESERVED');self.assertEqual(d[1]['reason'],'GLOBAL_TOTAL_POSITION_LIMIT')

    def test_pause_rechecks_old_reservation_and_resume_requires_current_head(self):
        self.init();identity=self.first(self.reserve(inputs=[self.inputs[0]]));self.transact('pause','PAUSE',dict(reason='global stop'))
        self.assertEqual(self.reserve('second',[self.inputs[1]])['outcome']['decisions'][0]['reason'],'GLOBAL_PAUSED')
        self.assertEqual(self.transact('fill','SETTLE',dict(intent_id=identity))['outcome']['reason'],'GLOBAL_PAUSED')
        self.assertEqual(Decimal(self.view()['cash']),10000);self.assertEqual(Decimal(self.view()['reserved_cash']),0)
        with self.assertRaisesRegex(ValueError,'current_receipt_head'):self.transact('stale','RESUME',dict(expected_head='0'*64))
        self.transact('resume','RESUME',dict(expected_head=self.view()['receipt_head']));self.assertFalse(self.view()['state']['paused'])

    def test_canonical_settlement_is_idempotent_and_sells_cannot_steal(self):
        self.init();identity=self.first(self.reserve(inputs=[self.inputs[0]]));r=self.transact('fill','SETTLE',dict(intent_id=identity))
        self.assertEqual(r['outcome']['status'],'SETTLED');self.assertEqual(Decimal(self.view()['cash']),2000)
        self.assertEqual(self.transact('fill','SETTLE',dict(intent_id=identity)),r)
        self.assertEqual(self.transact('other-fill-op','SETTLE',dict(intent_id=identity))['outcome']['status'],'ALREADY_TERMINAL')
        sell=fixed_signal_proposal(owner=self.inputs[1]['owner'],strategy='price.dual_ma@1',security_id=SECURITY,
            signal=Signal.exit('reduce'),signal_at=self.inputs[0]['signal_at'],execution_at=AT,risk=self.inputs[0]['risk'])
        self.assertEqual(self.reserve('wrong-owner',[sell])['outcome']['decisions'][0]['status'],'REJECTED')
        sell['owner']=self.inputs[0]['owner'];self.reidentify(sell);sid=self.first(self.reserve('owned-sell',[sell]))
        self.transact('pause','PAUSE',dict(reason='stop new risk'))
        self.assertEqual(self.transact('sell-fill','SETTLE',dict(intent_id=sid))['outcome']['status'],'SETTLED')
        self.assertEqual(Decimal(self.view()['cash']),10000);self.assertTrue(self.view()['state']['paused'])

    def test_pending_sells_lock_owned_quantity_without_double_release(self):
        self.init();identity=self.first(self.reserve(inputs=[self.inputs[0]]));self.transact('fill','SETTLE',dict(intent_id=identity))
        sell=fixed_signal_proposal(owner=self.inputs[0]['owner'],strategy='price.dual_ma@1',security_id=SECURITY,
            signal=Signal.exit('sell'),signal_at=self.inputs[0]['signal_at'],execution_at=AT,risk=self.inputs[0]['risk'])
        second=deepcopy(sell);second['source']['signal_key']='second-sell';self.reidentify(second)
        d=self.reserve('two-sells',[sell,second])['outcome']['decisions'];self.assertEqual([v['status'] for v in d],['RESERVED','REJECTED'])
        self.transact('cancel-sell','CANCEL',dict(intent_id=d[0]['intent_id'],reason='cancel'))
        self.assertEqual(sum(float(p['quantity']) for p in self.view()['state']['positions'].values()),.8*10000/101)

    def test_loss_halt_new_day_reset_and_manual_resume_conditions(self):
        config=deepcopy(self.config);config['initial_cash']=9000;config['securities'][SECURITY]['price']=100
        config['initial_positions']=[dict(owner='seed',security_id=SECURITY,quantity=10,avg_entry_price=100,entry_fees=0,realized_pnl=0)]
        self.init(config);later='2024-11-08T15:30:00Z';self.transact('loss','MARK',dict(prices={SECURITY:50}),at=later)
        self.assertTrue(self.view()['state']['loss_halted']);self.transact('pause','PAUSE',dict(reason='review loss'),at=later)
        with self.assertRaisesRegex(ValueError,'explicit_new_day'):self.transact('resume-fails','RESUME',dict(expected_head=self.view()['receipt_head']),at=later)
        tomorrow='2024-11-11T14:30:00Z';self.transact('marks-next-day','MARK',dict(prices={SECURITY:50}),at=tomorrow)
        self.transact('baseline','DAY_RESET',dict(expected_head=self.view()['receipt_head']),at=tomorrow)
        self.assertTrue(self.view()['state']['paused']);self.assertFalse(self.view()['state']['loss_halted'])
        self.transact('resume','RESUME',dict(expected_head=self.view()['receipt_head']),at=tomorrow);self.assertFalse(self.view()['state']['paused'])

    def test_stale_buy_releases_funds_and_new_day_baseline_waits_for_reservations(self):
        self.init();identity=self.first(self.reserve(inputs=[self.inputs[0]]));tomorrow='2024-11-11T14:30:00Z'
        self.transact('new-marks','MARK',dict(prices={SECURITY:104}),at=tomorrow)
        with self.assertRaisesRegex(ValueError,'no_outstanding'):self.transact('blocked','DAY_RESET',dict(expected_head=self.view()['receipt_head']),at=tomorrow)
        self.assertEqual(self.transact('stale-fill','SETTLE',dict(intent_id=identity),at=tomorrow)['outcome']['reason'],'STALE_MARK_OR_EXECUTION_CLOCK')
        self.transact('baseline','DAY_RESET',dict(expected_head=self.view()['receipt_head']),at=tomorrow)
        self.assertEqual(Decimal(self.view()['reserved_cash']),0)

    def test_read_reopen_preserves_bytes_and_decimal_context(self):
        self.init();self.reserve();before={p.name:sha256(p.read_bytes()).hexdigest() for p in self.account.iterdir() if p.is_file()}
        with localcontext() as c:
            c.prec=2;self.assertEqual(Decimal(self.view()['available_cash']),2000)
        self.assertEqual(before,{p.name:sha256(p.read_bytes()).hexdigest() for p in self.account.iterdir() if p.is_file()})

    def test_real_label_impersonation_and_rehashed_transition_are_rejected(self):
        config=deepcopy(self.config);config['evidence_kind']='REAL_ACCOUNT'
        with self.assertRaisesRegex(ValueError,'only_synthetic'):self.init(config)
        self.assertFalse(self.account.exists());self.init();self.reserve()
        bad=deepcopy(self.inputs[0]);bad['source']['kind']='REGISTERED_TASK_SIGNAL'
        with self.assertRaisesRegex(ValueError,'cannot_impersonate'):self.reserve('bad',[bad])
        self.assertEqual(self.view()['sequence'],1)
        with sqlite3.connect(self.account/'ledger.sqlite3') as c:
            r=parse_document(c.execute('SELECT receipt FROM events WHERE seq=1').fetchone()[0]);r['outcome']['decisions'][1]['status']='RESERVED'
            r['receipt_hash']=digest({k:v for k,v in r.items() if k!='receipt_hash'});c.execute('UPDATE events SET receipt=? WHERE seq=1',(canonical_bytes(r),))
        c.close()
        with self.assertRaisesRegex(ValueError,'transition_or_state'):self.view()
        with self.assertRaisesRegex(ValueError,'transition_or_state'):self.reserve('after-corruption')

    def test_real_two_process_contention_has_only_one_8000_reservation(self):
        self.init();code="""import json,sys,time
from pathlib import Path
from hakimi_research.shared_account import transact_shared_account
account,ready,go,output=map(Path,sys.argv[1:5]);ready.write_text('ready');deadline=time.monotonic()+30
while not go.exists():
 if time.monotonic()>deadline:raise RuntimeError('barrier expired')
 time.sleep(.01)
r=transact_shared_account(account,operation_id=sys.argv[5],kind='RESERVE',at='2024-11-08T14:30:00Z',payload=dict(intents=[json.loads(sys.argv[6])]))
output.write_text(json.dumps(r))
""";workers=[];go=self.root/'go'
        try:
            for i,p in enumerate(self.inputs):
                workers.append(subprocess.Popen([sys.executable,'-X','utf8','-B','-c',code,str(self.account),str(self.root/f'ready{i}'),str(go),str(self.root/f'out{i}'),f'process-{i}',json.dumps(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE))
            deadline=time.monotonic()+25
            while not all((self.root/f'ready{i}').exists() for i in range(2)):
                self.assertTrue(all(w.poll() is None for w in workers));self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            go.write_bytes(b'go')
            for w in workers:
                stdout,stderr=w.communicate(timeout=30);self.assertEqual(w.returncode,0,stderr)
            statuses=[json.loads((self.root/f'out{i}').read_bytes())['outcome']['decisions'][0]['status'] for i in range(2)]
            self.assertEqual(sorted(statuses),['REJECTED','RESERVED']);self.assertEqual(self.view()['sequence'],2)
            self.assertEqual(Decimal(self.view()['reserved_cash']),8000)
        finally:
            for w in workers:
                if w.poll() is None:w.kill();w.wait(timeout=10)

    def test_crash_before_or_after_commit_is_resolved_from_the_journal(self):
        code="""import json,os,sys
from contextlib import contextmanager
from hakimi_research import shared_account as a
original=a._connection
class Boundary:
 def __init__(self,c):self.c=c
 def execute(self,sql,*args):
  if sql=='COMMIT' and sys.argv[2]=='before':os._exit(74)
  result=self.c.execute(sql,*args)
  if sql=='COMMIT' and sys.argv[2]=='after':os._exit(75)
  return result
@contextmanager
def hooked(*args,**kwargs):
 with original(*args,**kwargs) as c:yield Boundary(c)
a._connection=hooked
a.transact_shared_account(sys.argv[1],operation_id='crash-operation',kind='RESERVE',at='2024-11-08T14:30:00Z',payload=dict(intents=[json.loads(sys.argv[3])]))
"""
        for boundary in ['before','after']:
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as path:
                account=Path(path)/'account';create_shared_account(account,self.config)
                r=subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(account),boundary,json.dumps(self.inputs[0])],capture_output=True,timeout=30)
                self.assertEqual(r.returncode,74 if boundary=='before' else 75,r.stderr)
                view=describe_shared_account(account);self.assertEqual(view['sequence'],0 if boundary=='before' else 1)
                self.assertEqual(Decimal(view['reserved_cash']),0 if boundary=='before' else 8000)
                self.assertEqual(len([v for v in view['history'] if v['operation_id']=='crash-operation']),0 if boundary=='before' else 1)


if __name__=='__main__':unittest.main()
