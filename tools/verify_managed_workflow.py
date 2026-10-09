"""Actual console-process lifecycle against the one installed candidate."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify_managed_workflow(command, workspace, run, *, env, outside):
    command, workspace, outside = str(command), Path(workspace), Path(outside).resolve()
    if not workspace.resolve().is_relative_to(outside):
        raise ValueError('managed_trial_workspace_must_be_inside_acceptance_directory')
    transcript = []
    def call(*args):
        result = json.loads(run([command, *map(str,args)], echo=False))
        transcript.append(dict(command=args[0],status=result.get('status','COMPLETED') if isinstance(result,dict) else 'COMPLETED'))
        return result
    family=workspace/'tasks/active-managed'
    call('task-copy','--from-task',workspace/'tasks/price.json','--task',family)
    first=call('task-show','--task',family)
    event=workspace/'tasks/event-managed'
    call('task-copy','--from-task',workspace/'tasks/event.json','--task',event)
    benchmark=workspace/'tasks/benchmark-managed'
    params=outside/'benchmark-parameters.json'
    params.write_text(json.dumps({'target_position_pct':.25}),encoding='utf-8')
    call('task-copy','--from-task',family,'--task',benchmark,'--strategy','price.buy_and_hold@1','--parameters',params)
    folders=[Path(call('run','--task',task)['run_directory']) for task in [family,event,benchmark]]
    hashes=[sha256((folder/'report.json').read_bytes()).hexdigest() for folder in folders]
    view=call('compare',*[part for folder in folders for part in ['--run-dir',folder]],'--output',workspace/'comparison.json')
    if view['status']!='COMPARABLE_CONDITIONS' or view['new_economic_runs']!=0 or view['shared_portfolio']:
        raise RuntimeError('installed_common_comparison_failed')
    call('task-revise','--task',family,'--initial-cash','12000')
    second_folder=Path(call('run','--task',family)['run_directory'])
    conflict=call('compare','--run-dir',folders[0],'--run-dir',second_folder)
    if conflict['status']!='NOT_COMPARABLE' or 'initial_cash' not in conflict['mismatches'][0]['fields']:
        raise RuntimeError('installed_comparison_cash_mismatch_not_explained')
    call('task-state','--task',family,'--state','PAUSED')
    stopped=subprocess.run([command,'run','--task',str(family)],cwd=outside,env=env,text=True,encoding='utf-8',capture_output=True,timeout=60)
    paused=json.loads(stopped.stdout)
    if stopped.returncode!=1 or paused['status']!='STOPPED' or 'task_paused' not in paused['error']:
        raise RuntimeError('installed_paused_task_not_rejected')
    call('task-select','--task',family,'--version','1')
    call('task-state','--task',family,'--state','ENABLED')
    reopened=call('task-show','--task',family)
    if reopened['task_id']!=first['task_id'] or len(reopened['revisions'])!=2:
        raise RuntimeError('installed_reopen_version_identity_lost')
    reused=call('run','--task',family)
    if Path(reused['run_directory'])!=folders[0] or sha256((folders[0]/'report.json').read_bytes()).hexdigest()!=hashes[0]:
        raise RuntimeError('installed_historical_selection_changed_frozen_result')
    moved=outside/'migrated-user-workspace'
    if moved.exists():raise RuntimeError('migration_destination_exists')
    workspace.rename(moved)
    if workspace.exists():raise RuntimeError('migration_old_workspace_still_present')
    migrated=call('task-show','--task',moved/'tasks/active-managed')
    if migrated['task_id']!=first['task_id']:raise RuntimeError('installed_migration_task_identity_changed')
    for folder, expected in zip(folders,hashes):
        target=moved/'runs'/folder.name
        replay=call('replay','--run-dir',target)
        if not replay['replay_verified']:raise RuntimeError('installed_managed_replay_failed')
        recover=call('recover','--run-dir',target)
        if recover['new_economic_runs']!=0 or sha256((target/'report.json').read_bytes()).hexdigest()!=expected:
            raise RuntimeError('installed_managed_recovery_changed_saved_result')
    return dict(schema_version='managed-task-installed-workflow-v1',status='PASS',data_kind='SYNTHETIC_TEST',
        scenarios=['CREATE_AND_COPY','REVISE_NEW_VERSION','RUN_THREE_REGISTERED_STRATEGIES','COMMON_COMPARISON',
            'INCOMPARABLE_CASH_REJECTED','PAUSED_EXECUTION_REJECTED','SELECT_HISTORICAL_CONFIGURATION',
            'COLD_PROCESS_REOPEN','WORKSPACE_MOVED_OLD_PATH_ABSENT','THREE_REPORT_REPLAYS','SAVED_REPORT_RECOVERY_ZERO_CALCULATIONS'],
        task_ids=[row['task_id'] for row in view['rows']],report_hashes=[row['report_hash'] for row in view['rows']],
        comparison_hash=view['comparison_hash'],comparison_status=view['status'],
        transcript=transcript,shared_portfolio=False,provider_calls=0,order_calls=0,checkout_data_used=False)
