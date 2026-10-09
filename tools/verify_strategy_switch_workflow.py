"""Cold console-process strategy revision regression against an installed wheel."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify_strategy_switch_workflow(command, workspace, run, *, env, outside):
    command, workspace, outside = str(command), Path(workspace).resolve(), Path(outside).resolve()
    if not workspace.is_relative_to(outside):
        raise ValueError('strategy_switch_trial_must_be_inside_acceptance_directory')
    transcript = []

    def call(*args):
        value = json.loads(run([command, *map(str, args)], echo=False))
        transcript.append(dict(command=args[0], status=value.get('status', 'COMPLETED')))
        return value

    def frozen(*directories):
        return {path: sha256(path.read_bytes()).hexdigest()
            for directory in directories for path in directory.rglob('*') if path.is_file()}

    def unchanged(files):
        if any(not p.is_file() or sha256(p.read_bytes()).hexdigest() != digest for p, digest in files.items()):
            raise RuntimeError('installed_strategy_switch_changed_original_bytes')

    def reject(family, error, *args):
        before = call('task-show', '--task', family)
        original = frozen(family, workspace / 'runs')
        result = subprocess.run([command, 'task-revise', '--task', str(family), *map(str, args)],
            cwd=outside, env=env, text=True, encoding='utf-8', capture_output=True, timeout=120)
        stopped = json.loads(result.stdout)
        if result.returncode != 1 or stopped['status'] != 'STOPPED' or error not in stopped['error']:
            raise RuntimeError('installed_strategy_switch_rejection_failed:expected=' + error
                + ',observed=' + str(stopped.get('error')) + ',exit=' + str(result.returncode))
        after = call('task-show', '--task', family)
        if any(after[name] != before[name] for name in ('family_id', 'state', 'selected_revision', 'event_hash', 'revisions')):
            raise RuntimeError('installed_rejected_strategy_switch_committed_state')
        unchanged(original)
        transcript.append(dict(command='task-revise', status='STOPPED', error=stopped['error']))
        return dict(status='STOPPED', error=stopped['error'], committed_state_and_original_bytes_unchanged=True)

    def document(label, value):
        path = outside / ('strategy-switch-' + label + '.json')
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    event_key = 'event.earnings_schedule@1'
    source = workspace / 'tasks/event.json'
    source_view = call('task-show', '--task', source)
    original_params = dict(source_view['configuration']['requested']['strategy']['params'])
    original_params.pop('take_profit_pct', None)
    partial_params = document('partial-event-parameters', original_params)
    seed = workspace / 'tasks/switch-origin'
    call('task-copy', '--from-task', source, '--task', seed, '--parameters', partial_params)
    seed_view = call('task-show', '--task', seed)
    event_input = Path(seed_view['task_file']).parent / 'inputs/event-context.json'
    source_files = frozen(seed, workspace / 'data')
    active_params = dict(fast_window=2, slow_window=4, position_pct=.2, stop_loss_pct=.02, take_profit_pct=.05)
    active_risk = dict(max_position_pct=.3, max_single_loss_pct=.025, max_daily_loss_pct=.1, min_cash_pct=.15, max_leverage=1)
    benchmark_params = dict(target_position_pct=.3)
    benchmark_risk = dict(max_position_pct=1, max_single_loss_pct=.03, max_daily_loss_pct=1, min_cash_pct=0, max_leverage=1)
    targets = [('dual-ma', 'price.dual_ma@1', active_params, active_risk),
        ('buy-and-hold', 'price.buy_and_hold@1', benchmark_params, benchmark_risk)]
    active_files = ['--parameters', document('active-parameters', active_params),
        '--risk', document('active-risk', active_risk)]
    rows = []
    for label, key, params, risk in targets:
        options = ['--parameters', document(label + '-parameters', params), '--risk', document(label + '-risk', risk)]
        family = workspace / 'tasks' / ('switch-to-' + label)
        call('task-copy', '--from-task', seed, '--task', family)
        report = Path(call('run', '--task', family)['run_directory'])
        call('task-state', '--task', family, '--state', 'PAUSED')
        before = call('task-show', '--task', family)
        original = frozen(family, report)
        conflict = reject(family, 'price_strategy_must_not_silently_use_event_inputs',
            '--strategy', key, *options, '--event-context', event_input)
        revised = call('task-revise', '--task', family, '--strategy', key, *options)
        task = json.loads(Path(revised['task_file']).read_text(encoding='utf-8'))
        seal = json.loads(Path(revised['task_file']).with_name('version.json').read_text(encoding='utf-8'))
        if (revised['family_id'] != before['family_id'] or revised['state'] != 'PAUSED'
                or len(revised['revisions']) != 2 or seal['parent_revision'] != before['selected_revision']
                or task['event_context'] is not None or 'inputs/event-context.json' in seal['files']
                or task['experiment']['schema_version'] != 'us-equity-experiment-spec-v1'
                or task['experiment']['strategy']['params'] != params or task['experiment']['risk'] != risk):
            raise RuntimeError('installed_event_to_price_revision_failed:' + key)
        for field in ('initial_cash', 'fee_rate', 'slippage_pct', 'score_start_session', 'score_end_session'):
            if revised['configuration']['requested'][field] != before['configuration']['requested'][field]:
                raise RuntimeError('installed_strategy_switch_changed_shared_configuration:' + field)
        old_snapshot = Path(before['task_file']).parent / 'inputs/snapshot.json'
        new_snapshot = Path(revised['task_file']).parent / 'inputs/snapshot.json'
        if old_snapshot.read_bytes() != new_snapshot.read_bytes():
            raise RuntimeError('installed_strategy_switch_changed_snapshot')
        unchanged(original)
        reverse = reject(family, 'event_strategy_context_required', '--strategy', event_key, *active_files)
        restored = call('task-revise', '--task', family, '--strategy', event_key, *active_files, '--event-context', event_input)
        if restored['state'] != 'PAUSED' or len(restored['revisions']) != 3:
            raise RuntimeError('installed_reverse_strategy_switch_changed_pause_or_history')
        restored_context = Path(restored['task_file']).parent / 'inputs/event-context.json'
        if restored_context.read_bytes() != event_input.read_bytes():
            raise RuntimeError('installed_reverse_strategy_switch_did_not_bind_explicit_event')
        copied = workspace / 'tasks' / ('switch-copy-' + label)
        copy_view = call('task-copy', '--from-task', seed, '--task', copied, '--strategy', key, *options)
        if (copy_view['configuration']['requested']['strategy']['params'] != params
                or copy_view['configuration']['requested']['risk'] != risk
                or json.loads(Path(copy_view['task_file']).read_text(encoding='utf-8'))['event_context'] is not None):
            raise RuntimeError('installed_copy_and_revision_switch_rules_differ')
        unchanged(original)
        rows.append(dict(target=key, explicit_legal_target_parameters_and_risk=True,
            requested_target_parameters=params, requested_target_risk=risk,
            same_family_revision_passed=True, event_input_cleared=True, explicit_conflict=conflict,
            reverse_missing_event=reverse, explicit_reverse_event_passed=True, copy_control_passed=True,
            paused_state_preserved=True, parent_revision_bound=True, shared_configuration_and_snapshot_preserved=True,
            original_files_verified=len(original), original_task_inputs_and_report_bytes_unchanged=True))

    call('task-state', '--task', seed, '--state', 'PAUSED')
    before = call('task-show', '--task', seed)
    cash = call('task-revise', '--task', seed, '--strategy', event_key, '--initial-cash', '12000')
    if (cash['state'] != 'PAUSED' or cash['configuration']['requested']['strategy']['params'] != original_params
            or cash['configuration']['requested']['risk'] != before['configuration']['requested']['risk']
            or cash['configuration']['effective']['take_profit_pct'] != .08
            or cash['configuration']['effective']['initial_cash'] != 12000):
        raise RuntimeError('installed_same_strategy_cash_edit_changed_original_rules')
    if (Path(cash['task_file']).parent / 'inputs/event-context.json').read_bytes() != event_input.read_bytes():
        raise RuntimeError('installed_same_strategy_cash_edit_changed_event_input')
    incompatible_params = reject(seed, 'unsupported_application_strategy_parameter',
        '--strategy', 'price.buy_and_hold@1', '--parameters', partial_params)
    incompatible_risk = reject(seed, 'benchmark_has_no_active_risk_controls',
        '--strategy', 'price.buy_and_hold@1', '--risk', document('incompatible-risk', active_risk))

    default_family = workspace / 'tasks/switch-default-benchmark'
    default_view = call('task-copy', '--from-task', seed, '--task', default_family, '--strategy', 'price.buy_and_hold@1')
    defaults_revised = call('task-revise', '--task', seed, '--strategy', 'price.buy_and_hold@1')
    for value in (default_view, defaults_revised):
        if (value['configuration']['requested']['strategy']['params'] != dict(target_position_pct=.25)
                or value['configuration']['requested']['risk'] != benchmark_risk):
            raise RuntimeError('installed_strategy_switch_default_template_mismatch')

    menu_rows = []
    for label, key, number, blanks in [('dual-ma', 'price.dual_ma@1', '1', 14),
            ('buy-and-hold', 'price.buy_and_hold@1', '2', 6)]:
        family = workspace / 'tasks' / ('menu-switch-' + label)
        call('task-copy', '--from-task', source, '--task', family)
        call('task-state', '--task', family, '--state', 'PAUSED')
        original = frozen(family)
        catalog = json.loads(run([command, 'tasks', '--workspace', str(workspace)], echo=False))
        index = next(i for i, row in enumerate(catalog, 1) if row.get('family') == str(family))
        form = [number] + [''] * blanks
        if key == 'price.dual_ma@1':
            form[1:3] = ['2', '4']
        answers = ['13', str(index), '2'] + form + ['0']
        completed = subprocess.run([command, 'wizard', '--workspace', str(workspace)], cwd=outside, env=env,
            input='\n'.join(answers) + '\n', text=True, encoding='utf-8', capture_output=True, timeout=120)
        (outside / ('strategy-switch-menu-' + label + '.txt')).write_text(completed.stdout + completed.stderr, encoding='utf-8')
        if completed.returncode or '操作停止：' in completed.stdout or '切换策略：' not in completed.stdout:
            raise RuntimeError('installed_strategy_switch_menu_failed:' + key)
        after = call('task-show', '--task', family)
        if after['strategy'] != key or after['state'] != 'PAUSED' or len(after['revisions']) != 2:
            raise RuntimeError('installed_strategy_switch_menu_changed_state_or_wrong_strategy')
        if json.loads(Path(after['task_file']).read_text(encoding='utf-8'))['event_context'] is not None:
            raise RuntimeError('installed_strategy_switch_menu_kept_stale_event')
        unchanged(original)
        menu_rows.append(dict(target=key, status='PASS', paused_state_and_original_version_preserved=True,
            transcript_sha256=sha256(completed.stdout.encode('utf-8')).hexdigest()))
    unchanged(source_files)
    return dict(schema_version='strategy-switch-installed-workflow-v1', status='PASS', data_kind='SYNTHETIC_TEST',
        operator='AGENT', normal_installed_console_entry=True, rows=rows, menu_rows=menu_rows,
        same_strategy_cash_only_retains_implicit_eight_percent=True, declared_default_template_controls_passed=True,
        incompatible_explicit_parameters=incompatible_params, incompatible_explicit_risk=incompatible_risk,
        source_files_and_old_versions_preserved=True, transcript=transcript, provider_calls=0, order_calls=0)
