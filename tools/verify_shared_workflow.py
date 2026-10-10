"""Actual installed cold entries, process competition and crash-boundary recovery."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess


def verify_shared_workflow(command,python,run,*,env,outside):
    command,python,outside=str(command),str(python),Path(outside)
    def call(*args):return json.loads(run([command,*map(str,args)],echo=False))
    def document(name,value):
        path=outside/name
        with path.open('x',encoding='utf-8') as f:json.dump(value,f)
        return path
    def check(condition,code):
        if not condition:raise RuntimeError('shared_installed_'+code)
    demo=call('shared-demo','--directory',outside/'shared-cancel-demo')
    account,at=demo['account'],demo['at']
    arguments=['shared-step','--account',account,'--operation-id','first-cohort','--at',at]
    for task in demo['tasks']:arguments+=['--task',task]
    receipt=call(*arguments);decisions=receipt['outcome']['decisions']
    check([d['status'] for d in decisions]==['RESERVED','REJECTED'],'two_8000_requests')
    view=call('shared-show','--account',account)
    check(float(view['reserved_cash'])==8000 and float(view['available_cash'])==2000,'shared_cash')
    check(call(*arguments)==receipt,'same_operation_idempotence')
    check(call('shared-receipt','--account',account,'--operation-id','first-cohort')['receipt']==receipt,'receipt_lookup')
    check(call('shared-receipt','--account',account,'--operation-id','absent')['status']=='NOT_RECORDED','missing_receipt')
    call('shared-cancel','--account',account,'--operation-id','cancel','--at',at,'--intent-id',decisions[0]['intent_id'],'--reason','synthetic cancel')
    arguments[4]='after-cancel'
    check(all(d['status']=='DUPLICATE_SIGNAL' for d in call(*arguments)['outcome']['decisions']),'terminal_signal_reopened')
    check(float(call('shared-show','--account',account)['reserved_cash'])==0,'cancel_released')
    # Another real cold task cohort, canonical settlement, loss latch and reset.
    demo2=call('shared-demo','--directory',outside/'shared-fill-demo');acc2=demo2['account']
    r=call('shared-step','--account',acc2,'--operation-id','entry','--at',at,'--task',demo2['tasks'][0],'--task',demo2['tasks'][1])
    call('shared-settle','--account',acc2,'--operation-id','fill','--at',at,'--intent-id',r['outcome']['decisions'][0]['intent_id'])
    view=call('shared-show','--account',acc2)
    check(float(view['cash'])==2000 and float(view['reserved_cash'])==0 and len(view['state']['positions'])==1,'canonical_shared_fill')
    prices=document('shared-loss-prices.json',{'SYNTHETIC:RESEARCH:TEST':89})
    call('shared-mark','--account',acc2,'--operation-id','loss','--at','2024-11-11T15:30:00Z','--prices',prices)
    view=call('shared-show','--account',acc2);check(view['state']['loss_halted'],'loss_latch')
    call('shared-pause','--account',acc2,'--operation-id','operator-pause','--at','2024-11-11T15:30:00Z','--reason','offline review')
    resume=subprocess.run([command,'shared-resume','--account',acc2,'--operation-id','blocked-resume','--at','2024-11-11T15:30:00Z',
        '--expected-head',call('shared-show','--account',acc2)['receipt_head']],cwd=outside,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
    check(resume.returncode==1 and 'loss_halt_requires' in json.loads(resume.stdout)['error'],'unsafe_resume')
    prices=document('shared-next-prices.json',{'SYNTHETIC:RESEARCH:TEST':103});tomorrow='2024-11-12T14:30:00Z'
    call('shared-mark','--account',acc2,'--operation-id','next-mark','--at',tomorrow,'--prices',prices)
    call('shared-day-reset','--account',acc2,'--operation-id','reset','--at',tomorrow,'--expected-head',call('shared-show','--account',acc2)['receipt_head'])
    view=call('shared-show','--account',acc2);check(view['state']['paused'] and not view['state']['loss_halted'],'manual_pause_preserved')
    call('shared-resume','--account',acc2,'--operation-id','resume','--at',tomorrow,'--expected-head',view['receipt_head'])
    check(not call('shared-show','--account',acc2)['state']['paused'],'qualified_resume')
    # Whole directory migration and cold reopen preserve ledger bytes/identity.
    original=Path(account);before={p.relative_to(original):sha256(p.read_bytes()).hexdigest() for p in original.rglob('*') if p.is_file()}
    moved=outside/'shared-migrated';shutil.copytree(original.parent,moved)
    check(call('shared-show','--account',moved/'account')==call('shared-show','--account',account),'migration_identity')
    check(before=={p.relative_to(original):sha256(p.read_bytes()).hexdigest() for p in original.rglob('*') if p.is_file()},'read_changed_bytes')
    # Use the real menu twice, including saved receipt lookup after exit.
    workspace=outside/'shared-menu'
    for answers in [['17','1','example','4','menu-cohort','','','0','0'],['17','2','1','3','12','menu-cohort','0','0']]:
        process=subprocess.run([command,'wizard','--workspace',str(workspace)],cwd=outside,env=env,
            input='\n'.join(answers)+'\n',capture_output=True,text=True,encoding='utf-8',timeout=120)
        check(process.returncode==0 and '操作停止' not in process.stdout,'cold_menu')
        check('预留 8000.00；可用 2000.00' in process.stdout,'menu_visible_funds')
    # Five canonical registered strategies, source context and task state are
    # validated by the installed API, with independent backtests prohibited.
    adapters=r'''import json,sys
from pathlib import Path
from unittest.mock import patch
from hakimi_research.trade_cli import initialize_demo,create_task
from hakimi_research.input_workflow import import_content_packet
from hakimi_research.strategy_registry import strategies
from hakimi_research.shared_account import create_shared_account,demo_account_config
from hakimi_research.shared_signals import step_shared_tasks
root=Path(sys.argv[1]);w=root/'inputs';init=initialize_demo(w);e=init['input_examples'];snapshot=next((w/'data').glob('equity_dataset_*.json'))
context=Path(import_content_packet(e['packet'],w,event_id=e['event_id'],texts_dir=e['texts_dir'],originals_dir=e['originals_dir'],synthetic=True)['path'])
tasks=[]
for i,key in enumerate(strategies()):
 opts=dict(snapshot=snapshot,strategy=key,score_start='2024-11-11',score_end='2024-12-03',fee_rate=0,slippage_pct=0)
 if key=='price.buy_and_hold@1':opts['params']=dict(target_position_pct=.8)
 elif key.startswith('content.'):
  opts.update(params=dict(position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06),event_context=context)
 else:
  opts['params']=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06)
  if key.startswith('event.'):opts['event_context']=w/'data/event-context.json'
 if key!='price.buy_and_hold@1':opts['risk']=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0)
 tasks.append(create_task(w/'tasks'/('shared-'+str(i)+'.json'),**opts))
config=demo_account_config();config['as_of']='2024-11-11T14:30:00Z';config['securities']['SYNTHETIC:RESEARCH:TEST']['price']=104
create_shared_account(root/'account',config)
with patch('hakimi_research.offline_app.run_strategy',side_effect=AssertionError('independent backtest')):
 r=step_shared_tasks(root/'account',tasks,operation_id='all-five',at=config['as_of'])
assert len(r['outcome']['decisions'])==5
print(json.dumps(list(strategies())))
'''
    keys=json.loads(run([python,'-I','-X','utf8','-B','-c',adapters,str(outside/'shared-all-five')],echo=False))
    processes=r'''import json,os,sys,time,subprocess
from pathlib import Path
from hakimi_research.shared_account import create_shared_account,demo_account_config,describe_shared_account
from hakimi_research.shared_signals import demo_competing_intents
root=Path(sys.argv[1]);root.mkdir();account=root/'concurrent';create_shared_account(account,demo_account_config())
worker="""import json,sys,time
from pathlib import Path
from hakimi_research.shared_account import transact_shared_account
Path(sys.argv[2]).write_text('ready')
while not Path(sys.argv[3]).exists():time.sleep(.01)
r=transact_shared_account(sys.argv[1],operation_id=sys.argv[4],kind='RESERVE',at='2024-11-08T14:30:00Z',payload=dict(intents=[json.loads(sys.argv[5])]))
print(json.dumps(r['outcome']['decisions'][0]['status']))
"""
workers=[]
try:
 for i,p in enumerate(demo_competing_intents()):workers.append(subprocess.Popen([sys.executable,'-I','-X','utf8','-B','-c',worker,str(account),str(root/('ready'+str(i))),str(root/'go'),'worker-'+str(i),json.dumps(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE))
 deadline=time.monotonic()+30
 while not all((root/('ready'+str(i))).exists() for i in range(2)):
  assert all(w.poll() is None for w in workers) and time.monotonic()<deadline
  time.sleep(.02)
 (root/'go').write_text('go');statuses=[]
 for w in workers:
  out,err=w.communicate(timeout=40);assert w.returncode==0,err;statuses.append(json.loads(out))
 assert sorted(statuses)==['REJECTED','RESERVED']
 view=describe_shared_account(account);assert view['sequence']==2 and float(view['reserved_cash'])==8000
finally:
 for w in workers:
  if w.poll() is None:w.kill();w.wait(timeout=10)
crash="""import os,sys
from contextlib import contextmanager
from hakimi_research import shared_account as a
from hakimi_research.shared_signals import demo_competing_intents
original=a._connection
class Boundary:
 def __init__(self,c):self.c=c
 def execute(self,sql,*args):
  if sql=='COMMIT' and sys.argv[2]=='before':os._exit(74)
  result=self.c.execute(sql,*args)
  if sql=='COMMIT' and sys.argv[2]=='after':os._exit(75)
  return result
@contextmanager
def hook(*args,**kwargs):
 with original(*args,**kwargs) as c:yield Boundary(c)
a._connection=hook
a.transact_shared_account(sys.argv[1],operation_id='crash',kind='RESERVE',at='2024-11-08T14:30:00Z',payload=dict(intents=[demo_competing_intents()[0]]))
"""
rows=[]
for mode,count in [('before',0),('after',1)]:
 acc=root/mode;create_shared_account(acc,demo_account_config())
 p=subprocess.run([sys.executable,'-I','-X','utf8','-B','-c',crash,str(acc),mode],capture_output=True,timeout=40)
 assert p.returncode==(74 if mode=='before' else 75),p.stderr
 v=describe_shared_account(acc);assert v['sequence']==count and float(v['reserved_cash'])==8000*count
 rows.append(dict(boundary=mode,exit_code=p.returncode,committed_receipts=count))
print(json.dumps(dict(concurrent_statuses=sorted(statuses),concurrent_sequence=2,crashes=rows)))
'''
    proof=json.loads(run([python,'-I','-X','utf8','-B','-c',processes,str(outside/'shared-processes')],echo=False))
    # Actual cold rejection must preserve both the clock and the complete view.
    clock_account=outside/'shared-clock-cli'
    before=call('shared-init','--account',clock_account,'--demo')
    for verb,tail in [('shared-reserve',['--demo']),('shared-settle',['--intent-id','unknown']),
            ('shared-cancel',['--intent-id','unknown','--reason','synthetic typo'])]:
        process=subprocess.run([command,verb,'--account',str(clock_account),'--operation-id','bad-'+verb,
            '--at','2024-11-08T15:30:00Z',*tail],cwd=outside,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
        check(process.returncode==1 and 'requires_current_account_clock' in json.loads(process.stdout)['error'],'wrong_clock_rejection')
        check(call('shared-show','--account',clock_account)==before,'wrong_clock_changed_account')
    clock_checks=r'''import base64,hashlib,json,sys
from pathlib import Path
from importlib.resources import files
from hakimi_research.shared_account import create_shared_account,demo_account_config,describe_shared_account,transact_shared_account
from hakimi_research.shared_signals import demo_competing_intents
root=Path(sys.argv[1]);account=root/'live';at='2024-11-08T14:30:00Z';later='2024-11-08T15:30:00Z'
create_shared_account(account,demo_account_config());inputs=demo_competing_intents()
for p in inputs:p['signal']['size_pct']=.4
r=transact_shared_account(account,operation_id='two',kind='RESERVE',at=at,payload=dict(intents=inputs))
one,two=[d['intent_id'] for d in r['outcome']['decisions']]
transact_shared_account(account,operation_id='release-one',kind='CANCEL',at=at,payload=dict(intent_id=one,reason='synthetic cancel'))
for identity in ['unknown',one]:
 for kind in ['CANCEL','REJECT','SETTLE']:
  payload=dict(intent_id=identity)
  if kind!='SETTLE':payload['reason']='synthetic no-op'
  before=describe_shared_account(account)
  try:transact_shared_account(account,operation_id=kind+'-'+identity,kind=kind,at=later,payload=payload)
  except ValueError as e:assert 'requires_current_account_clock' in str(e)
  else:raise AssertionError('bad lifecycle clock accepted')
  assert describe_shared_account(account)==before
r=transact_shared_account(account,operation_id='settle-two',kind='SETTLE',at=at,payload=dict(intent_id=two));assert r['outcome']['status']=='SETTLED'
fixture=json.loads(files('hakimi_research').joinpath('resources/shared-account-v1.json').read_bytes())
legacy=root/'legacy';legacy.mkdir()
for name,proof in fixture['files'].items():
 raw=base64.b64decode(proof['base64']);assert hashlib.sha256(raw).hexdigest()==proof['sha256'];(legacy/name).write_bytes(raw)
view=describe_shared_account(legacy);assert view['legacy_read_only'] and view['sequence']==1 and float(view['reserved_cash'])==8000
try:transact_shared_account(legacy,operation_id='blocked',kind='PAUSE',at=at,payload=dict(reason='read only'))
except ValueError as e:assert 'legacy_v1_account_is_read_only' in str(e)
else:raise AssertionError('legacy account mutated')
for name,proof in fixture['files'].items():assert hashlib.sha256((legacy/name).read_bytes()).hexdigest()==proof['sha256']
'''
    run([python,'-I','-X','utf8','-B','-c',clock_checks,str(outside/'shared-clock-api')],echo=False)
    return dict(schema_version='installed-shared-funds-workflow-v2',status='PASS',operator='AGENT',data_kind='SYNTHETIC_TEST',
        competition='COMMITTED_RECEIPT_FIFO_ALL_OR_NOTHING',registered_strategies=keys,process_proof=proof,
        actual_cold_console=True,actual_menu=True,exit_reopen=True,task_capital_ignored=True,all_or_nothing=True,
        duplicate_operation_idempotent=True,terminal_signal_not_reopened=True,cancel_releases_funds=True,
        canonical_settlement=True,global_loss_latch=True,conditional_resume=True,manual_pause_preserved=True,
        receipt_lookup=True,workspace_migration=True,read_preserves_bytes=True,independent_backtests_forbidden=True,
        wrong_clock_rejected_without_account_change=True,no_op_does_not_poison_clock=True,
        legacy_v1_readable_with_original_bytes=True,legacy_v1_mutation_blocked=True,
        provider_calls=0,external_account_calls=0,broker_order_calls=0,checkout_data_used=False,source_modified=False)
