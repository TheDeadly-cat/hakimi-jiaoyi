"""Installed menu-10 and rehashed-report rejection using only fictional inputs."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify_content_boundary_workflow(command, python, run, *, env, outside):
    command, python, outside = str(command), str(python), Path(outside).resolve()
    workspace=outside/'content-boundary-workspace'
    initialized=json.loads(run([command,'init','--demo','--workspace',str(workspace)],echo=False))
    examples=initialized['input_examples']
    context=json.loads(run([command,'content-import','--workspace',str(workspace),'--packet',examples['packet'],
        '--event-id',examples['event_id'],'--texts-dir',examples['texts_dir'],'--originals-dir',examples['originals_dir'],
        '--synthetic'],echo=False))['path']
    keys=['price.dual_ma@1','price.buy_and_hold@1','event.earnings_schedule@1',
        'content.price_confirmation@1','content.reviewed_outlook@1']
    menu_tasks=[];runs=[]
    for number,key in enumerate(keys,1):
        params=['2','4','','',''] if number in {1,3} else [''] if number==2 else ['','','']
        answers=['10','1',str(number),*params,*(['']*4 if number!=2 else []),*(['']*5)]
        if number in {3,4,5}:answers.append(str(workspace/'data/event-context.json') if number==3 else context)
        name='legacy-'+str(number);answers.extend([name,'0'])
        proc=subprocess.run([command,'wizard','--workspace',str(workspace)],cwd=outside,env=env,
            input='\n'.join(answers)+'\n',text=True,encoding='utf-8',capture_output=True,timeout=180)
        if proc.returncode or '操作停止：' in proc.stdout or '任务已保存：' not in proc.stdout:
            raise RuntimeError('installed_legacy_menu_creation_failed:'+key+':'+proc.stdout[-1000:])
        task=workspace/'tasks'/(name+'.json')
        checked=json.loads(run([command,'check','--task',str(task)],echo=False))
        if checked['configuration']['requested']['strategy']['params'].keys()!=set(
                ['fast_window','slow_window','position_pct','stop_loss_pct','take_profit_pct'] if number in {1,3}
                else ['target_position_pct'] if number==2 else ['position_pct','stop_loss_pct','take_profit_pct']):
            raise RuntimeError('installed_legacy_parameters_differ_from_registry')
        executed=json.loads(run([command,'run','--task',str(task)],echo=False))
        directory=Path(executed['run_directory']);runs.append(directory)
        viewed=json.loads(run([command,'report','--run-dir',str(directory)],echo=False))
        if viewed['new_economic_runs']!=0:raise RuntimeError('report_view_repeated_economics')
        menu_tasks.append(dict(strategy=key,configuration_checked=True,run_view_checked=True))
    normal,blocked=runs[3],runs[4]
    original=(normal/'report.json').read_bytes();report=json.loads(original)
    blocked_original=(blocked/'report.json').read_bytes();blocked_report=json.loads(blocked_original)
    if not any(f['action']=='SELL' and f['fill_basis']=='INTRABAR_STOP' for f in report['result']['fills']):
        raise RuntimeError('protective_exit_fixture_not_exercised')
    if blocked_report['result']['fill_count']!=0:raise RuntimeError('unknown_content_fixture_not_blocked')
    zero=outside/'content-zero-parameters.json';zero.write_bytes(b'{"position_pct":0,"stop_loss_pct":0.03,"take_profit_pct":0.06}')
    snapshot=next((workspace/'data').glob('equity_dataset_*.json'))
    task=workspace/'tasks/zero.json'
    run([command,'task-create','--task',str(task),'--strategy',keys[3],'--snapshot',str(snapshot),
        '--event-context',context,'--parameters',str(zero)],echo=False)
    zero_run=Path(json.loads(run([command,'run','--task',str(task)],echo=False))['run_directory'])
    zero_view=json.loads(run([command,'report','--run-dir',str(zero_run)],echo=False))
    if zero_view['result_view']['fill_count']!=0 or zero_view['new_economic_runs']!=0:
        raise RuntimeError('legal_zero_allocation_not_readable')
    # Only fixture construction uses installed APIs. Reads below are actual CLI processes.
    code="""import copy,json,shutil,sys
from pathlib import Path
import pandas as pd
from hakimi_research.documents import canonical_bytes,digest
normal,blocked,target=map(Path,sys.argv[1:]);base=json.loads((normal/'report.json').read_bytes())
cases=[]
for field,value in [('symbol','OTHER'),('fill_time','2024-11-09T14:30:00Z'),('signal_time','2024-11-09T14:30:00Z'),('fill_basis','UNSUPPORTED')]:
    cases.append((field,normal,lambda r,f=field,v=value:r['fills'][0].update({f:v}),'equity_fill_before_signal_or_outside_session'))
def later(r):
    sessions=base['dataset']['sessions'];i=next(i for i,s in enumerate(sessions) if s['date']=='2024-11-11')
    r['fills'][0].update(fill_time=sessions[i]['open_utc'],signal_time=str(pd.Timestamp(sessions[i-1]['close_utc'])+pd.Timedelta(seconds=60)))
def duplicate(r):r['fills'].insert(1,copy.deepcopy(r['fills'][0]));r['fill_count']+=1
def inject(r):r['fills']=[copy.deepcopy(base['result']['fills'][0])];r['fill_count']=1
cases.extend([('wrong-opportunity',normal,later,'content_report_buy_not_bound_to_plan'),('duplicate',normal,duplicate,'content_report_buy_not_bound_to_plan'),('filtered',blocked,inject,'content_report_buy_not_bound_to_plan')])
rows=[]
for name,source,change,reason in cases:
    path=target/name/source.name;path.parent.mkdir(parents=True);shutil.copytree(source,path)
    bad=json.loads((path/'report.json').read_bytes());change(bad['result'])
    bad['result_hash']=digest(dict(snapshot_id=bad['dataset']['snapshot_id'],spec=bad['spec'],result=bad['result']))
    bad['report_hash']=digest({k:v for k,v in bad.items() if k!='report_hash'})
    (path/'report.json').write_bytes(canonical_bytes(bad));rows.append(dict(name=name,path=str(path),reason=reason))
print(json.dumps(rows))
"""
    bad_cases=json.loads(run([python,'-I','-X','utf8','-B','-c',code,str(normal),str(blocked),str(outside/'content-bad-copies')],echo=False))
    rejections=[]
    for case in bad_cases:
        directory=Path(case['path'])
        before={p:sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}
        for verb,arguments in [('report',['--run-dir',directory]),('recover',['--run-dir',directory]),
                ('compare',['--run-dir',normal,'--run-dir',directory])]:
            proc=subprocess.run([command,verb,*map(str,arguments)],cwd=outside,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
            value=json.loads(proc.stdout)
            if proc.returncode!=1 or value.get('status')!='STOPPED' or case['reason'] not in value.get('error',''):
                raise RuntimeError('installed_bad_content_report_not_rejected:'+case['name']+':'+verb)
            rejections.append(dict(case=case['name'],command=verb,status='STOPPED',reason=case['reason']))
        if before!={p:sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}:
            raise RuntimeError('rejected_read_modified_copy')
    if (normal/'report.json').read_bytes()!=original or (blocked/'report.json').read_bytes()!=blocked_original:
        raise RuntimeError('negative_cases_modified_original_reports')
    # Forbid engines explicitly during installed API reads too; inputs/planners are real.
    readonly="""from pathlib import Path
from unittest.mock import patch
import sys
from hakimi_research import offline_app,content_tasks
from hakimi_research.task_comparison import compare_runs
with patch.object(offline_app,'run_strategy',side_effect=AssertionError('read ran economics')), patch.object(content_tasks,'run_content_task',side_effect=AssertionError('read ran content')), patch.object(content_tasks._SessionEngine,'run',side_effect=AssertionError('read ran engine')):
    for p in map(Path,sys.argv[1:]):offline_app.describe_run(p);offline_app.recover_report(p)
    assert compare_runs(list(map(Path,sys.argv[1:3])))['new_economic_runs']==0
"""
    run([python,'-I','-X','utf8','-B','-c',readonly,str(normal),str(blocked),str(zero_run)],echo=False)
    return dict(schema_version='installed-content-boundary-workflow-v1',status='PASS',operator='AGENT',data_kind='SYNTHETIC_TEST',
        actual_cold_legacy_menu=True,menu_tasks=menu_tasks,rehashed_bad_copy_rejections=rejections,
        normal_content_readable=True,legal_zero_fill_readable=True,blocked_content_readable=True,protective_exit_readable=True,
        reads_forbid_engines=True,original_reports_unchanged=True,rejected_copies_unchanged=True,
        view_recovery_compare_new_economic_runs=0,checkout_data_used=False,historical_reports_modified=False,
        provider_calls=0,account_calls=0,order_calls=0)
