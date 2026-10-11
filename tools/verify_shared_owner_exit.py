"""Installed registered-owner reductions, independent processes and old journals."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify_owner_exits(command, python, run, *, env, outside):
    command, python, outside = str(command), str(python), Path(outside)
    def check(condition, code):
        if not condition:
            raise RuntimeError('shared_owner_exit_' + code)
    def call(*args):
        return json.loads(run([command, *map(str, args)], echo=False))
    def step(account, tasks, operation):
        args = ['shared-step', '--account', account, '--operation-id', operation, '--at', at]
        for task in tasks:
            args += ['--task', task]
        return call(*args)
    def lifecycle(account, intent, kind, operation):
        args = ['shared-' + kind, '--account', account, '--operation-id', operation, '--at', at, '--intent-id', intent]
        if kind == 'cancel':
            args += ['--reason', 'synthetic review']
        return call(*args)
    setup = r'''import base64,hashlib,json,sys
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from hakimi_research.shared_account import demo_account_config
from hakimi_research.task_manager import create_family,read_family
from hakimi_research.trade_cli import initialize_demo
root=Path(sys.argv[1]);root.mkdir();w=root/'inputs';initialize_demo(w)
snapshot=next((w/'data').glob('equity_dataset_*.json'));tasks=[];owners=[];buys=[]
common=dict(snapshot=snapshot,score_start='2024-11-11',score_end='2024-12-03',fee_rate=0,slippage_pct=0)
for i in range(2):
 family=w/'tasks'/('owner-'+str(i));create_family(family,strategy='price.dual_ma@1',
  params=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06),
  risk=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0),**common)
 tasks.append(str(family));owners.append('family:'+read_family(family)['family_id'])
 buy=w/'tasks'/('buy-'+str(i));create_family(buy,strategy='price.buy_and_hold@1',
  initial_cash=[1234,99999][i],params=dict(target_position_pct=.8),**common);buys.append(str(buy))
base=demo_account_config();base['as_of']='2024-11-11T14:30:00Z';base['securities']['SYNTHETIC:RESEARCH:TEST']['price']=104
configs={}
for mode in ['normal','loss','buy']:
 config=deepcopy(base)
 if mode!='buy':config['initial_positions']=[dict(owner=o,security_id='SYNTHETIC:RESEARCH:TEST',quantity=q,
  avg_entry_price=90,entry_fees=0,realized_pnl=0) for o,q in zip(owners,[10,20])]
 if mode=='loss':
  config['as_of']='2024-11-11T14:00:00Z';config['securities']['SYNTHETIC:RESEARCH:TEST']['price']=120
  config['limits']['max_daily_loss_pct']=.01
 path=root/(mode+'.json');path.write_text(json.dumps(config),encoding='utf-8');configs[mode]=str(path)
fixture=json.loads(files('hakimi_research').joinpath('resources/shared-account-v2-task-exit.json').read_bytes())
legacy=root/'original-v2-task-exit';legacy.mkdir()
for name,proof in fixture['files'].items():
 raw=base64.b64decode(proof['base64']);assert hashlib.sha256(raw).hexdigest()==proof['sha256'];(legacy/name).write_bytes(raw)
print(json.dumps(dict(tasks=tasks,owners=owners,buys=buys,configs=configs,at=base['as_of'],
 legacy=dict(account=str(legacy),expected=fixture['expected'],hashes={n:p['sha256'] for n,p in fixture['files'].items()}))))
'''
    info = json.loads(run([python, '-I', '-X', 'utf8', '-B', '-c', setup, str(outside/'shared-owner-exit')], echo=False))
    tasks, at, owners = info['tasks'], info['at'], info['owners']
    security = 'SYNTHETIC:RESEARCH:TEST'
    prices = outside/'shared-owner-exit'/'prices.json'
    prices.write_text(json.dumps({security:104}), encoding='utf-8')
    for first in [0, 1]:
        for mode in ['normal', 'paused', 'loss']:
            account = outside/'shared-owner-exit'/('account-' + str(first) + '-' + mode)
            call('shared-init', '--account', account, '--config', info['configs']['loss' if mode=='loss' else 'normal'])
            if mode == 'paused':
                call('shared-pause', '--account', account, '--operation-id', 'pause', '--at', at, '--reason', 'synthetic')
            if mode == 'loss':
                call('shared-mark', '--account', account, '--operation-id', 'loss', '--at', at, '--prices', prices)
                check(call('shared-show', '--account', account)['state']['loss_halted'], 'loss_guard_missing')
            order = [first, 1-first]
            receipt = step(account, [tasks[i] for i in order], 'exit')
            decisions = receipt['outcome']['decisions']
            check([d['status'] for d in decisions]==['RESERVED','RESERVED'], 'different_owners_collided')
            check([float(d['requested_quantity']) for d in decisions]==[[10,20][i] for i in order], 'owned_quantities')
            check(step(account, [tasks[i] for i in order], 'exit')==receipt, 'same_operation_changed')
            view = call('shared-show', '--account', account, '--journal')
            check(float(view['cash'])==10000 and float(view['available_cash'])==10000 and float(view['reserved_cash'])==0, 'pending_sell_cash')
            check(len(view['state']['opportunities'])==2, 'opportunity_slots')
            for n, d in enumerate(decisions):
                check(lifecycle(account, d['intent_id'], 'settle', 'fill-'+str(n))['outcome']['status']=='SETTLED', 'fill')
                positions = {p['owner']:float(p['quantity']) for p in call('shared-show','--account',account)['state']['positions'].values()}
                check(positions[owners[order[n]]]==0, 'own_fill')
                if n == 0:
                    check(positions[owners[order[1]]]==[10,20][order[1]], 'other_position_changed')
            check(float(call('shared-show','--account',account)['cash'])==13120, 'final_cash')
            check(lifecycle(account,decisions[0]['intent_id'],'settle','repeat-fill')['outcome']['status']=='ALREADY_TERMINAL', 'repeat_fill')
    account = outside/'shared-owner-exit'/'cancel-revision'
    call('shared-init','--account',account,'--config',info['configs']['normal'])
    first = step(account, tasks, 'exit')['outcome']['decisions']
    check(all(d['status']=='RESERVED' for d in first), 'cancel_setup')
    check(all(d['status']=='DUPLICATE_SIGNAL' for d in step(account,tasks,'changed-operation')['outcome']['decisions']), 'new_id_reopened')
    lifecycle(account,first[0]['intent_id'],'cancel','cancel')
    revise = r'''import sys
from hakimi_research.task_manager import revise_family
revise_family(sys.argv[1],initial_cash=77777,params=dict(fast_window=2,slow_window=4,position_pct=.7,stop_loss_pct=.02,take_profit_pct=.05))
'''
    run([python,'-I','-X','utf8','-B','-c',revise,tasks[0]],echo=False)
    check(step(account,[tasks[0]],'revised-exit')['outcome']['decisions'][0]['status']=='DUPLICATE_SIGNAL', 'revision_reopened')
    view = call('shared-show','--account',account,'--journal')
    check(sum(r['status']=='RESERVED' for r in view['state']['intents'].values())==1, 'cancel_changed_other_lock')
    check(lifecycle(account,first[1]['intent_id'],'settle','other-fill')['outcome']['status']=='SETTLED', 'other_fill')
    view = call('shared-show','--account',account)
    check({p['owner']:float(p['quantity']) for p in view['state']['positions'].values()}==dict(zip(owners,[10,0])), 'cancel_position')
    # Two independent console processes enter the same SQLite account.
    account = outside/'shared-owner-exit'/'concurrent'
    call('shared-init','--account',account,'--config',info['configs']['normal'])
    workers = []
    try:
        for i, task in enumerate(tasks):
            workers.append(subprocess.Popen([command,'shared-step','--account',str(account),'--operation-id','worker-'+str(i),
                '--at',at,'--task',task],cwd=outside,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
        for worker in workers:
            out, err = worker.communicate(timeout=90)
            check(worker.returncode==0, 'concurrent_console_exit_'+str(worker.returncode))
            d = json.loads(out)['outcome']['decisions'][0]
            check(d['status']=='RESERVED', 'concurrent_owner_collided')
        view = call('shared-show','--account',account,'--journal')
        check(view['sequence']==2 and sum(float(r['quantity']) for r in view['state']['intents'].values())==30, 'concurrent_quantities')
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill(); worker.wait(timeout=10)
    account = outside/'shared-owner-exit'/'buy-copies'
    call('shared-init','--account',account,'--config',info['configs']['buy'])
    decisions = step(account,info['buys'],'buy')['outcome']['decisions']
    check([d['status'] for d in decisions]==['RESERVED','DUPLICATE_SIGNAL'], 'buy_dedup_weakened')
    lifecycle(account,decisions[0]['intent_id'],'cancel','cancel-buy')
    check(all(d['status']=='DUPLICATE_SIGNAL' for d in step(account,info['buys'],'again')['outcome']['decisions']), 'buy_cancel_reopened')
    legacy = info['legacy']
    view = call('shared-show','--account',legacy['account'],'--journal')
    check(view['legacy_read_only'] and view['opportunity_policy']=='LEGACY_RULE_CLOCK_V1'
        and view['clock_policy']=='ONLY_EXPLICIT_MARK_ADVANCES_CLOCK', 'old_semantics')
    check(view['sequence']==legacy['expected']['sequence'] and view['receipt_head']==legacy['expected']['receipt_head'], 'old_head')
    check([d['status'] for d in view['history'][0]['outcome']['decisions']]==['RESERVED','DUPLICATE_SIGNAL'], 'old_task_replay')
    result = subprocess.run([command,'shared-pause','--account',legacy['account'],'--operation-id','blocked','--at',at,
        '--reason','read only'],cwd=outside,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
    check(result.returncode==1 and 'legacy_v2_account_is_read_only' in json.loads(result.stdout)['error'], 'old_write_allowed')
    check(call('shared-show','--account',legacy['account'],'--journal')==view, 'old_read_changed')
    check(all(sha256((Path(legacy['account'])/n).read_bytes()).hexdigest()==h for n,h in legacy['hashes'].items()), 'old_bytes_changed')
    return dict(registered_owner_exit_both_orders=True,paused_and_loss_halted_owner_exits=True,
        owner_only_settlement=True,pending_sell_does_not_credit_cash=True,
        owner_exit_new_operation_and_revision_not_reopened=True,owner_exit_cancel_not_reopened=True,
        concurrent_registered_owner_exits=True,managed_buy_copy_dedup_preserved=True,
        legacy_v2_task_step_readable_with_original_bytes=True,legacy_v2_mutation_blocked=True)
