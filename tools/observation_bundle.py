"""Freeze a local 72h observation trial and run its fixed roles; no registration."""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

FILES=('observation_job.py','observation_notify.py','show_observation_notification.ps1',
       'observation_watch.py','observation_bundle.py','prepare_observation_task.ps1')

def now():
    return datetime.now(timezone.utc)

def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def timestamp(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone_required')
    return parsed.astimezone(timezone.utc)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')).hexdigest()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def seal(value):
    return dict(value,receipt_hash=digest(value))

def read(path):
    with Path(path).open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('bundle_document_limit')
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:
                raise ValueError('duplicate_key')
            value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_JSON')))

def verified(value):
    if value.get('receipt_hash')!=digest({key:item for key,item in value.items() if key!='receipt_hash'}):
        raise ValueError('bundle_document_digest_invalid')
    return value

def write_new(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.pending-',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,indent=2).encode('ascii')+b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def source_commit(source):
    paths=['tools/'+name for name in FILES]
    options={'cwd':source.parent,'capture_output':True,'text':True,'encoding':'utf-8','timeout':10}
    for argv in (['git','ls-files','--error-unmatch',*paths],['git','diff','--exit-code','HEAD','--',*paths]):
        if subprocess.run(argv,**options).returncode:
            raise ValueError('bundle_tools_must_match_committed_source')
    result=subprocess.run(['git','rev-parse','HEAD'],**options)
    if result.returncode:
        raise ValueError('source_commit_unavailable')
    return result.stdout.strip()

def runtime_preflight(runtime,job):
    job.verify_deployment(runtime)
    code=('import importlib.util,json,pathlib,sys; r=pathlib.Path(sys.argv[1]).resolve(); '
          's=importlib.util.spec_from_file_location("frozen_preflight",r/"tools/forward_reliability.py"); '
          'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
          'p=m.load_plan(r/"forward/reliability-plan-20260906.json"); '
          'print(json.dumps(m.verify_runtime(r,p),sort_keys=True))')
    result=job.execute([str(runtime/'venv/Scripts/python.exe'),'-I','-B','-c',code,str(runtime)],runtime,
                       timeout_seconds=30,output_limit_bytes=16384,cleanup_seconds=5)
    if result.returncode or result.bounds['outcome']!='EXITED' or not result.bounds['cleanup_confirmed']:
        raise ValueError('installed_runtime_preflight_failed')
    return {'verification':json.loads(result.stdout),'execution_bounds':result.bounds,'checked_at':stamp(now())}

def create(destination,runtime,start_cutoff):
    source=Path(__file__).resolve().parent
    root,runtime=Path(destination).resolve(),Path(runtime).resolve()
    if root.exists():
        raise ValueError('new_bundle_directory_required')
    if root==runtime or root.is_relative_to(runtime) or runtime.is_relative_to(root):
        raise ValueError('bundle_must_be_separate_from_frozen_runtime')
    if str(root).startswith('\\\\') or str(runtime).startswith('\\\\'):
        raise ValueError('local_paths_required')
    start=timestamp(start_cutoff)
    if start<now()+timedelta(minutes=10) or start.minute or start.second or start.microsecond:
        raise ValueError('future_whole_hour_with_ten_minute_preparation_margin_required')
    commit=source_commit(source)
    hashes={name:file_hash(source/name) for name in FILES}
    if any((source/name).is_symlink() for name in FILES):
        raise ValueError('regular_bundle_tools_required')
    job=load('bundle_source_job',source/'observation_job.py')
    preflight=runtime_preflight(runtime,job)
    root.mkdir(parents=True,exist_ok=False)
    (root/'tools').mkdir()
    for name in FILES:
        shutil.copy2(source/name,root/'tools'/name)
        if file_hash(root/'tools'/name)!=hashes[name] or file_hash(source/name)!=hashes[name]:
            raise ValueError('tool_bytes_changed_during_bundle_copy')
    watch=load('bundle_copied_watch',root/'tools/observation_watch.py')
    plan=watch.build_plan(stamp(start),72)
    write_new(root/'watch-plan.json',plan)
    end=timestamp(plan['end_cutoff_exclusive'])
    value=seal({'schema_version':'observation-control-bundle-v1','created_at':stamp(now()),
        'source_commit':commit,'source_bytes_policy':'EXACT_LOCAL_CHECKOUT_BYTES_WITH_COMMITTED_TOOL_CONTENT',
        'bundle_root':str(root),'runtime_root':str(runtime),
        'job_root':str(root/'job-receipts'),'watch_root':str(root/'watch-receipts'),
        'tool_sha256':hashes,'watch_plan_file_sha256':file_hash(root/'watch-plan.json'),
        'watch_plan_hash':plan['receipt_hash'],'start_cutoff':stamp(start),'end_cutoff_exclusive':stamp(end),
        'watch_end_exclusive':stamp(end+timedelta(minutes=10)),
        'end_policy':'STOP_TRIAL_OBSERVATION_AT_END; ALLOW_10_MINUTES_FOR_FINAL_WATCH_AND_NOTIFICATION_DRAIN',
        'runtime_preflight':preflight,'scheduler_activated':False,'old_heartbeat_changed':False,
        'observer_execution_limit_seconds':600,'watch_execution_limit_seconds':50,
        'observer_interval_seconds':3600,'watch_interval_seconds':60,
        'logon_type':'INTERACTIVE_CURRENT_USER','order_allowed':False})
    write_new(root/'bundle.json',value)
    return value

def verify_bundle(root,expected_hash=None):
    root=Path(root).resolve()
    manifest=verified(read(root/'bundle.json'))
    if expected_hash and manifest['receipt_hash']!=expected_hash:
        raise ValueError('registered_bundle_identity_changed')
    if (manifest.get('schema_version')!='observation-control-bundle-v1'
            or manifest.get('bundle_root')!=str(root)
            or manifest.get('job_root')!=str(root/'job-receipts') or manifest.get('watch_root')!=str(root/'watch-receipts')
            or set(manifest.get('tool_sha256',{}))!=set(FILES)
            or manifest.get('scheduler_activated') is not False or manifest.get('order_allowed') is not False
            or manifest.get('observer_interval_seconds')!=3600 or manifest.get('watch_interval_seconds')!=60
            or manifest.get('observer_execution_limit_seconds')!=600 or manifest.get('watch_execution_limit_seconds')!=50):
        raise ValueError('bundle_contract_invalid')
    for name,sha in manifest['tool_sha256'].items():
        target=root/'tools'/name
        if target.is_symlink() or file_hash(target)!=sha:
            raise ValueError('frozen_control_tool_changed')
    if file_hash(root/'watch-plan.json')!=manifest['watch_plan_file_sha256']:
        raise ValueError('watch_plan_bytes_changed')
    watch=load('bundle_checked_watch',root/'tools/observation_watch.py')
    plan=watch.verify_plan(read(root/'watch-plan.json'))
    if (plan['receipt_hash']!=manifest['watch_plan_hash'] or plan['scope']!='DECLARED_WINDOW'
            or plan['start_cutoff']!=manifest['start_cutoff'] or plan['end_cutoff_exclusive']!=manifest['end_cutoff_exclusive']
            or timestamp(manifest['watch_end_exclusive'])!=timestamp(manifest['end_cutoff_exclusive'])+timedelta(minutes=10)):
        raise ValueError('bundle_window_binding_invalid')
    return manifest,watch

def preview(root):
    root=Path(root).resolve()
    manifest,_=verify_bundle(root)
    pythonw=Path(manifest['runtime_root'])/'venv/Scripts/pythonw.exe'
    if not pythonw.is_file():
        raise ValueError('fixed_windowless_python_missing')
    tasks=[]
    for role,name,offset,interval,limit,end in (
        ('observe','HakimiReadOnlyObservation',60,3600,600,manifest['end_cutoff_exclusive']),
        ('watch','HakimiObservationWatch',30,60,50,manifest['watch_end_exclusive'])):
        argv=['-I','-B',str(root/'tools/observation_bundle.py'),'run','--bundle-root',str(root),
              '--bundle-sha256',manifest['receipt_hash'],'--role',role]
        tasks.append({'role':role,'task_name':name,'execute':str(pythonw),'arguments':subprocess.list2cmdline(argv),
            'working_directory':str(root),'first_utc':stamp(timestamp(manifest['start_cutoff'])+timedelta(seconds=offset)),
            'end_utc_exclusive':end,'interval_seconds':interval,'execution_limit_seconds':limit,
            'multiple_instances':'IgnoreNew','logon_type':'Interactive','run_level':'Limited'})
    return {'status':'NOT_ACTIVATED','bundle_hash':manifest['receipt_hash'],'source_commit':manifest['source_commit'],
        'start_cutoff':manifest['start_cutoff'],'end_cutoff_exclusive':manifest['end_cutoff_exclusive'],
        'watch_end_exclusive':manifest['watch_end_exclusive'],'end_policy':manifest['end_policy'],
        'current_registration_window_valid':now()+timedelta(minutes=2)<timestamp(manifest['start_cutoff']),
        'activation_requires_explicit_maintainer_approval_and_old_heartbeat_pause':True,'tasks':tasks}

def run_role(root,expected_hash,role):
    root=Path(root).resolve()
    start=now()
    attempt=start.strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid.uuid4().hex
    location=root/'runner-attempts'/attempt
    initial=seal({'schema_version':'observation-bundle-run-start-v1','started_at':stamp(start),
        'role':role,'bundle_hash':expected_hash,'attempt_id':attempt,'order_allowed':False})
    write_new(location/'started.json',initial)
    end={'schema_version':'observation-bundle-run-end-v1','attempt_id':attempt,
        'started_receipt_hash':initial['receipt_hash'],'role':role,'status':'FAILED_PREFLIGHT','order_allowed':False,
        'result_scope':'PROCESS_RESULT_NOT_WINDOW_ACCEPTANCE'}
    stage='PREFLIGHT'
    try:
        manifest,watch=verify_bundle(root,expected_hash)
        if role not in {'observe','watch'}:
            raise ValueError('unknown_fixed_role')
        first=timestamp(manifest['start_cutoff'])
        last=timestamp(manifest['end_cutoff_exclusive'] if role=='observe' else manifest['watch_end_exclusive'])
        if now()>=last or role=='observe' and now()<first:
            end['status']='OUTSIDE_DECLARED_RUN_WINDOW'
        else:
            runtime=Path(manifest['runtime_root'])
            argv=[str(runtime/'venv/Scripts/python.exe'),'-I','-B']
            if role=='observe':
                argv += [str(root/'tools/observation_job.py'),'--runtime-root',str(runtime),'--job-root',manifest['job_root'],
                         '--window-start',manifest['start_cutoff'],'--window-end',manifest['end_cutoff_exclusive']]
                timeout,output=340,1024*1024
            else:
                argv += [str(root/'tools/observation_watch.py'),'check','--plan',str(root/'watch-plan.json'),
                         '--job-root',manifest['job_root'],'--watch-root',manifest['watch_root'],'--send']
                timeout,output=40,16384
            stage='EXECUTE'
            result=watch.job.execute(argv,root,timeout_seconds=timeout,output_limit_bytes=output,cleanup_seconds=5)
            end.update(child_exit_code=result.returncode,execution_bounds=result.bounds,
                stdout_sha256=hashlib.sha256(result.stdout.encode('utf-8')).hexdigest(),
                stderr_sha256=hashlib.sha256(result.stderr.encode('utf-8')).hexdigest())
            if result.bounds['outcome']!='EXITED' or not result.bounds['cleanup_confirmed']:
                end['status']='CHILD_EXECUTION_BOUNDARY_FAILED'
            else:
                stage='VALIDATE'
                value=json.loads(result.stdout)
                if role=='observe':
                    watch.job.verify_seal(value)
                    identifier=value.get('attempt_id','')
                    if not re.fullmatch(r'\d{8}T\d{12}Z_[a-f0-9]{32}',identifier):
                        raise ValueError('child_attempt_identity_invalid')
                    path=Path(manifest['job_root'])/'attempts'/identifier/'ended.json'
                    if (read(path)!=value or value.get('schema_version')!='observation-job-end-v2'
                            or value.get('order_allowed') is not False
                            or not start<=timestamp(value['launcher_record_ended_at'])<=now()):
                        raise ValueError('child_observation_receipt_binding_invalid')
                else:
                    report=watch.previous_report(Path(manifest['watch_root']))
                    if (not report or report['receipt_hash']!=value.get('receipt_hash')
                            or report['plan_hash']!=manifest['watch_plan_hash']
                            or report['status']!=value.get('status')
                            or not start<=timestamp(report['checked_at'])<=now()):
                        raise ValueError('child_watch_receipt_binding_invalid')
                end['child_summary']=value
                end['status']='COMPLETED' if result.returncode==0 else 'CHILD_REPORTED_FAILURE'
    except Exception as exc:
        end['error_type']=type(exc).__name__
        end['error_stage']=stage
        end['status']='FAILED_PREFLIGHT' if stage=='PREFLIGHT' else 'CHILD_START_OR_WAIT_FAILED' if stage=='EXECUTE' else 'CHILD_RESULT_INVALID'
    end['ended_at']=stamp(now())
    end=seal(end)
    write_new(location/'ended.json',end)
    return end

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('create')
    build.add_argument('--output',type=Path,required=True)
    build.add_argument('--runtime-root',type=Path,required=True)
    build.add_argument('--start',required=True)
    show=sub.add_parser('preview')
    show.add_argument('--bundle-root',type=Path,required=True)
    run=sub.add_parser('run')
    run.add_argument('--bundle-root',type=Path,required=True)
    run.add_argument('--bundle-sha256',required=True)
    run.add_argument('--role',choices=('observe','watch'),required=True)
    args=parser.parse_args()
    if args.command=='create':
        result=create(args.output,args.runtime_root,args.start)
    elif args.command=='preview':
        result=preview(args.bundle_root)
    else:
        result=run_role(args.bundle_root,args.bundle_sha256,args.role)
    if sys.stdout is not None:
        print(json.dumps(result,ensure_ascii=True,allow_nan=False))
    return 0 if args.command!='run' or result['status'] in {'COMPLETED','OUTSIDE_DECLARED_RUN_WINDOW'} else 1

if __name__=='__main__':
    raise SystemExit(main())
