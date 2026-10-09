"""Cold-process menu/CLI regression for the exact installed repair candidate."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify_configuration_workflow(command, workspace, run, *, env, outside):
    command,workspace,outside=str(command),Path(workspace).resolve(),Path(outside).resolve()
    if not workspace.is_relative_to(outside):raise ValueError('configuration_trial_must_be_in_acceptance_directory')
    def call(*args):
        return json.loads(run([command,*map(str,args)],echo=False))
    def index(task):
        catalog=call('tasks','--workspace',workspace)
        return next(i for i,row in enumerate(catalog,1) if Path(row.get('family',row['task_file'])).resolve()==task.resolve())
    def menu(inputs,name):
        completed=subprocess.run([command,'wizard','--workspace',str(workspace)],input='\n'.join(inputs)+'\n',
            cwd=outside,env=env,text=True,encoding='utf-8',capture_output=True,timeout=120)
        (outside/(name+'.txt')).write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode or '操作停止：' in completed.stdout:raise RuntimeError('installed_configuration_menu_failed:'+name)
    rows=[]
    snapshot=next((workspace/'data').glob('equity_dataset_*.json'))
    for label,key,event in [('price','price.dual_ma@1',False),('event','event.earnings_schedule@1',True)]:
        params=dict(fast_window=2,slow_window=4,position_pct=.25,stop_loss_pct=.03)
        parameters=outside/('partial-'+label+'-parameters.json');parameters.write_text(json.dumps(params),encoding='utf-8')
        legacy=workspace/'tasks'/('partial-'+label+'.json')
        args=['task-create','--task',legacy,'--snapshot',snapshot,'--strategy',key,'--parameters',parameters,
            '--score-start','2024-11-11','--score-end','2024-12-03']
        if event:args+=['--event-context',workspace/'data/event-context.json']
        call(*args)
        old=call('task-show','--task',legacy)
        if old['configuration']['effective']['take_profit_pct']!=.08:raise RuntimeError('installed_old_effective_default_not_eight')
        legacy_bytes=sha256(legacy.read_bytes()).hexdigest()
        family=workspace/'tasks'/('preserved-'+label)
        menu(['13',str(index(legacy)),'3']+['']*(16 if event else 15)+[family.name,'0'],'copy-partial-'+label)
        copied=call('task-show','--task',family)
        if copied['configuration']['requested']['strategy']['params']!=params or copied['configuration']['effective']['take_profit_pct']!=.08:
            raise RuntimeError('installed_blank_copy_changed_existing_rules')
        folder=Path(call('run','--task',family)['run_directory'])
        report_bytes=sha256((folder/'report.json').read_bytes()).hexdigest()
        first_task=Path(copied['task_file']);first_bytes=sha256(first_task.read_bytes()).hexdigest()
        cash=['']*(16 if event else 15);cash[10]='12000'
        number=str(index(family))
        menu(['13',number,'2']+['']*(16 if event else 15)+['13',number,'2']+cash+['0'],'edit-partial-'+label)
        edited=call('task-show','--task',family)
        if (len(edited['revisions'])!=3 or edited['configuration']['effective']['initial_cash']!=12000
                or edited['configuration']['requested']['strategy']['params']!=params or edited['configuration']['effective']['take_profit_pct']!=.08):
            raise RuntimeError('installed_blank_or_cash_edit_changed_existing_rules')
        call('task-state','--task',family,'--state','PAUSED')
        before=call('task-show','--task',family)
        rejections=[]
        for field,value in [('stop_loss_pct',0),('take_profit_pct',0),('take_profit_pct',1.1),('position_pct',-.1),('max_daily_loss_pct',0)]:
            name='risk' if field.startswith('max_') else 'parameters'
            config=deepcopy(before['configuration']['requested']['risk'] if name=='risk' else params);config[field]=value
            bad=outside/('bad-'+label+'-'+str(len(rejections))+'.json');bad.write_text(json.dumps(config),encoding='utf-8')
            completed=subprocess.run([command,'task-revise','--task',str(family),'--'+name,str(bad)],cwd=outside,env=env,
                text=True,encoding='utf-8',capture_output=True,timeout=60)
            stopped=json.loads(completed.stdout)
            if completed.returncode!=1 or stopped['status']!='STOPPED':raise RuntimeError('installed_numeric_configuration_not_rejected')
            after=call('task-show','--task',family)
            if after['event_hash']!=before['event_hash'] or after['selected_revision']!=before['selected_revision'] or after['state']!='PAUSED':
                raise RuntimeError('installed_failed_configuration_changed_state')
            rejections.append(dict(field=field,value=value,status='STOPPED',error=stopped['error'],committed_state_unchanged=True))
        if (sha256(legacy.read_bytes()).hexdigest()!=legacy_bytes or sha256(first_task.read_bytes()).hexdigest()!=first_bytes
                or sha256((folder/'report.json').read_bytes()).hexdigest()!=report_bytes):
            raise RuntimeError('installed_configuration_edit_changed_frozen_bytes')
        rows.append(dict(strategy=key,omitted_take_profit_preserved=True,before_effective_take_profit=.08,after_effective_take_profit=.08,
            committed_revisions=3,blank_copy_and_edit_passed=True,cash_only_edit_passed=True,first_task_and_report_bytes_unchanged=True,
            rejections=rejections,menu_transcript_sha256={name:sha256((outside/(name+'-'+label+'.txt')).read_bytes()).hexdigest()
                for name in ['copy-partial','edit-partial']}))
    return dict(schema_version='configuration-consistency-installed-workflow-v1',status='PASS',data_kind='SYNTHETIC_TEST',
        same_candidate=True,rows=rows,provider_calls=0,order_calls=0,backtest_used_to_validate_invalid_configurations=False)
