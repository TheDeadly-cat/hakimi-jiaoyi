"""Actual cold installed-console input/version flows using fictional resources."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess


def verify_input_workflow(command, python, run, *, env, outside):
    command, python, outside = str(command), str(python), Path(outside).resolve()
    transcript = []

    def call(*args):
        result = json.loads(run([command, *map(str, args)], echo=False))
        transcript.append(dict(command=args[0], status=result.get('status', 'COMPLETED')))
        return result

    def document(name, value):
        target = outside/name
        if target.exists():
            raise RuntimeError('input_workflow_fixture_must_be_new')
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return target

    def frozen(directory):
        return {p:sha256(p.read_bytes()).hexdigest() for p in Path(directory).rglob('*') if p.is_file()}

    def unchanged(originals):
        if any(not p.is_file() or sha256(p.read_bytes()).hexdigest()!=h for p,h in originals.items()):
            raise RuntimeError('input_workflow_changed_original_bytes')

    def menu(workspace, answers):
        result = subprocess.run([command,'wizard','--workspace',str(workspace)], cwd=outside, env=env,
            input='\n'.join(map(str, answers))+'\n', capture_output=True, text=True, encoding='utf-8', timeout=180)
        if result.returncode or '操作停止：' in result.stdout or '输入操作停止：' in result.stdout:
            raise RuntimeError('installed_input_menu_failed:'+result.stdout[-2000:]+result.stderr[-1000:])
        transcript.append(dict(command='wizard', status='REAL_COLD_MENU_COMPLETED'))
        return result.stdout

    def reject(code, *arguments, family=None):
        before = call('task-show','--task',family) if family else None
        originals = frozen(family) if family else {}
        result = subprocess.run([command,*map(str, arguments)], cwd=outside, env=env,
            capture_output=True, text=True, encoding='utf-8', timeout=120)
        stopped = json.loads(result.stdout)
        if result.returncode!=1 or stopped.get('status')!='STOPPED' or code not in stopped.get('error',''):
            raise RuntimeError('installed_input_rejection_failed:'+code+':'+str(stopped))
        if family:
            after = call('task-show','--task',family)
            for key in ('family_id','state','selected_revision','event_hash','revisions'):
                if before[key]!=after[key]:raise RuntimeError('rejected_input_binding_committed_state')
            unchanged(originals)
        transcript.append(dict(command=arguments[0], status='STOPPED', expected_reason=code))

    source = outside/'input-source-demo'
    initialized = call('init','--demo','--workspace',source)
    source_originals = frozen(source)
    snapshot_path = next((source/'data').glob('equity_dataset_*.json'))
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    csv = outside/'input-provided.csv';csv.write_bytes(base64.b64decode(snapshot['raw_input']['csv_base64']))
    metadata = outside/'input-provided-metadata.json';metadata.write_bytes(base64.b64decode(snapshot['raw_input']['manifest_base64']))
    user = outside/'input-user-workspace'
    call('init','--workspace',user)
    output = menu(user,['16','2',csv,metadata,'0','0'])
    if '输入已封存：' not in output:raise RuntimeError('actual_menu_did_not_import_csv')
    imported = call('input-import','--workspace',user,'--csv',csv,'--metadata',metadata)
    if imported['input_id']!=snapshot['snapshot_id']:raise RuntimeError('csv_input_identity_changed')
    market = Path(imported['path'])
    existing = call('input-import','--workspace',user,'--file',snapshot_path)
    if Path(existing['path']).read_bytes()!=snapshot_path.read_bytes():raise RuntimeError('existing_snapshot_bytes_not_retained')
    schedule = call('input-import','--workspace',user,'--file',source/'data/event-context.json')
    parameters = document('input-price-parameters.json',dict(fast_window=2,slow_window=4,position_pct=.25,stop_loss_pct=.03,take_profit_pct=.06))
    reject('event_strategy_context_required','input-check','--strategy','event.earnings_schedule@1',
        '--snapshot',market,'--parameters',parameters)
    checked = call('input-check','--strategy','event.earnings_schedule@1','--snapshot',market,
        '--event-context',schedule['path'],'--parameters',parameters)
    if checked['new_economic_runs']!=0:raise RuntimeError('input_check_ran_simulation')
    families = [user/'tasks/event-cli',user/'tasks/event-menu']
    for family in families:
        call('task-create','--managed','--task',family,'--strategy','event.earnings_schedule@1',
            '--snapshot',market,'--event-context',schedule['path'],'--parameters',parameters)
    event_before = call('task-show','--task',families[0])
    old_run = Path(call('run','--task',families[0])['run_directory'])
    originals = frozen(old_run)
    original_versions = {family: frozen(family) for family in families}
    for family in families:call('task-state','--task',family,'--state','PAUSED')
    reject('event_strategy_context_required','task-bind','--task',families[0],'--clear-event-context',family=families[0])

    # Fixture creation alone uses installed APIs; every product action below
    # goes through the real installed console or terminal menu.
    revised_context = outside/'input-revised-schedule.json'
    code = """import json,sys
from pathlib import Path
from hakimi_research.equity_events import build_equity_event
from hakimi_research.equity_event_context import build_event_context
old=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['events'][0]
metadata={k:v for k,v in old.items() if k not in {'schema_version','raw','event_hash','availability','authority'}}
text='Fictional schedule ANNOUNCED 2024-11-12 after market close.'
metadata.update(version=2,prior_version_hash=old['event_hash'],version_public_at='2024-11-07T13:00:00Z')
metadata['schedule']=dict(metadata['schedule'],date='2024-11-12',evidence=[dict(quote=text)])
new=build_equity_event(text.encode(),metadata)
value=build_event_context([old,new],old['security_id'])
Path(sys.argv[2]).write_text(json.dumps(value,indent=2)+'\\n',encoding='utf-8')
"""
    run([python,'-c',code,schedule['path'],str(revised_context)],echo=False)
    revised = call('input-import','--workspace',user,'--file',revised_context)
    updated = call('task-bind','--task',families[0],'--event-context',revised['path'])
    if updated['state']!='PAUSED' or len(updated['revisions'])!=2 or updated['family_id']!=event_before['family_id']:
        raise RuntimeError('installed_input_binding_changed_family_or_pause')
    unchanged(original_versions[families[0]])
    catalog = call('inputs','--workspace',user)['items']
    research = [r for r in catalog if r['kind']=='SCHEDULE_CONTEXT' and r['status']=='READY']
    research_number = next(i for i,r in enumerate(research,1) if r['path']==revised['path'])
    menu(user,['16','7','2','2',research_number,'SAVE','0','0'])
    menu_view = call('task-show','--task',families[1])
    if menu_view['state']!='PAUSED' or len(menu_view['revisions'])!=2 or menu_view['inputs']['research']['input_id']!=revised['input_id']:
        raise RuntimeError('installed_menu_research_binding_failed')
    unchanged(original_versions[families[1]])
    call('task-state','--task',families[0],'--state','ENABLED')
    new_run = Path(call('run','--task',families[0])['run_directory'])
    compared = call('compare','--run-dir',old_run,'--run-dir',new_run)
    if compared['status']!='COMPARABLE_CONDITIONS' or compared['new_economic_runs']!=0:
        raise RuntimeError('input_revision_comparison_conditions_changed')
    if compared['rows'][0]['blocked_new_buys']!=1 or compared['rows'][1]['blocked_new_buys']!=0:
        raise RuntimeError('installed_schedule_version_not_applied_point_in_time')
    unchanged(originals)

    examples = initialized['input_examples']
    content_arguments = ['--workspace',user,'--packet',examples['packet'],'--event-id',examples['event_id'],
        '--texts-dir',examples['texts_dir'],'--originals-dir',examples['originals_dir'],'--synthetic']
    unknown = call('content-import',*content_arguments)
    if unknown['approval_status']!='NOT_APPROVED':raise RuntimeError('content_import_invented_field_approval')
    content_active, content_price = user/'tasks/content-active', user/'tasks/content-price'
    for family,key in [(content_active,'content.reviewed_outlook@1'),(content_price,'content.price_confirmation@1')]:
        call('input-check','--strategy',key,'--snapshot',market,'--event-context',unknown['path'],
            '--score-start','2024-11-04','--score-end','2024-12-03')
        call('task-create','--managed','--task',family,'--strategy',key,'--snapshot',market,
            '--event-context',unknown['path'],'--score-start','2024-11-04','--score-end','2024-12-03')
    unknown_run = Path(call('run','--task',content_active)['run_directory'])
    baseline_run = Path(call('run','--task',content_price)['run_directory'])
    unknown_view = call('report','--run-dir',unknown_run)['result_view']
    if unknown_view['fill_count']!=0 or unknown_view['blocked_new_buys']!=1:
        raise RuntimeError('unapproved_content_did_not_hold_price_intent')
    frozen_unknown = frozen(unknown_run)
    packet = json.loads(Path(examples['packet']).read_text(encoding='utf-8'))
    # This is an explicit fictional contract fixture, never a claimed human act.
    approval = document('input-synthetic-field-receipt.json',dict(schema_version='human-field-review-v1',
        packet_hash=packet['packet_hash'], decision='APPROVED_LISTED_FIELDS', reviewer_kind='HUMAN_ATTESTATION',
        reviewer='SYNTHETIC_FIXTURE_ONLY',source_user_confirmation='Fictional fixture only; no actual human approval claimed',
        reviewed_at='2024-12-06T00:00:00Z',approved_candidate_hashes=[packet['events'][0]['candidate_hash']],
        approved_fields=['actual_revenue','diluted_eps','non_gaap_diluted_eps',
            'next_revenue_guidance_midpoint','next_revenue_guidance_half_range','first_public_at']))
    accepted = call('content-import',*content_arguments,'--approval',approval)
    call('task-state','--task',content_active,'--state','PAUSED')
    active_originals = frozen(content_active)
    active_before = call('task-show','--task',content_active)
    revised_active = call('task-bind','--task',content_active,'--event-context',accepted['path'])
    if revised_active['state']!='PAUSED' or len(revised_active['revisions'])!=2 or revised_active['family_id']!=active_before['family_id']:
        raise RuntimeError('content_input_binding_changed_family_or_pause')
    unchanged(active_originals)
    reject('task_paused','run','--task',content_active,family=content_active)
    call('task-state','--task',content_active,'--state','ENABLED')
    accepted_run = Path(call('run','--task',content_active)['run_directory'])
    accepted_view = call('report','--run-dir',accepted_run)['result_view']
    if accepted_view['fill_count']<1 or accepted_view['research_input_outcome']['status']!='NO_CONTENT_INTERVENTION':
        raise RuntimeError('existing_approved_content_predicate_not_applied')
    price_report = json.loads((baseline_run/'report.json').read_text(encoding='utf-8'))
    accepted_report = json.loads((accepted_run/'report.json').read_text(encoding='utf-8'))
    if price_report['result']!=accepted_report['result']:
        raise RuntimeError('content_no_intervention_differs_from_identical_price_baseline')
    content_comparison = call('compare','--run-dir',baseline_run,'--run-dir',accepted_run)
    if content_comparison['status']!='COMPARABLE_CONDITIONS' or content_comparison['new_economic_runs']!=0:
        raise RuntimeError('content_comparison_not_readonly_or_conditions_changed')
    unchanged(frozen_unknown)
    menu(user,['16','1','0','0'])  # Exit/reopen inventory after real revision commits.

    retained = frozen(user)
    migrated = outside/'input-migrated-workspace'
    if not user.is_relative_to(outside) or not migrated.is_relative_to(outside) or user==outside or migrated.exists():
        raise RuntimeError('synthetic_migration_target_invalid')
    shutil.copytree(user,migrated)
    migrated_family = migrated/content_active.relative_to(user)
    migrated_run = migrated/accepted_run.relative_to(user)
    migrated_view = call('task-show','--task',migrated_family)
    if migrated_view['task_id']!=revised_active['task_id'] or not Path(migrated_view['inputs']['snapshot']['path']).is_relative_to(migrated):
        raise RuntimeError('migrated_task_input_identity_or_location_changed')
    if not Path(migrated_view['inputs']['research']['path']).is_relative_to(migrated):
        raise RuntimeError('migrated_research_input_not_portable')
    # Pause/state events do not change a committed task identity.
    report_bytes = (migrated_run/'report.json').read_bytes()
    viewed = call('report','--run-dir',migrated_run)
    recovered = call('recover','--run-dir',migrated_run)
    replayed = call('replay','--run-dir',migrated_run)
    if not replayed['replay_verified'] or viewed['new_economic_runs']!=0 or recovered['new_economic_runs']!=0:
        raise RuntimeError('migrated_content_replay_or_readonly_view_failed')
    if (migrated_run/'report.json').read_bytes()!=report_bytes:raise RuntimeError('migration_rewrote_original_report')
    menu(migrated,['16','1','0','0'])
    unchanged(retained);unchanged(source_originals)
    return dict(schema_version='installed-offline-input-workflow-v1',status='PASS',operator='AGENT',
        data_kind='SYNTHETIC_TEST',human_review_claimed=False,fixture_review='SYNTHETIC_CONTRACT_RECEIPT_ONLY',
        actual_installed_cold_console=True,actual_menu_csv_import=True,actual_menu_research_binding=True,
        snapshot_original_bytes_preserved=True,research_packet_original_bytes_preserved=True,
        missing_context_rejected=True,paused_task_rejected=True,rejections_keep_committed_state=True,
        input_checks_new_economic_runs=0,comparison_new_economic_runs=0,
        task_version_binding=True,pause_preserved=True,old_reports_unchanged=True,
        schedule_version_changes_filter=True,unapproved_content_holds=True,
        approved_fixture_content_no_intervention_matches_price_result=True,
        exit_reopen=True,workspace_migration=True,migrated_replay_verified=True,migrated_view_new_economic_runs=0,
        checkout_data_used=False,source_modified=False,provider_calls=0,account_calls=0,order_calls=0,
        transcript=transcript)
