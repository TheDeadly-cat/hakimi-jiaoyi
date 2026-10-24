"""Local presentation adapter over the canonical task/input/ledger APIs.

No vendor kernel, provider, broker, or model is imported here. The workspace is
explicit and all browser supplied references are confined to it. Economic
calculations and their durable recovery remain owned by the existing APIs.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock

from .documents import digest, parse_document, read_document
from .environment import build_runtime_provenance
from .equity_research import PERMISSIONS
from .input_workflow import _retain, list_inputs, import_price_csv
from .offline_app import (describe_run, immutable_write, run_task, verify_run,
                          write_new, _file_lock)
from .research_feedback import build_feedback_markdown
from .task_manager import create_family, describe_task, list_tasks, change_state
from .strategy_registry import strategies, new_task_parameters, required_task_context
from .source_identity import package_content_identity

_LOADED_SOURCE = package_content_identity(Path(__file__).resolve().parent)['content_sha256']


def _regular(path):
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('workspace_symbolic_link_or_junction_not_supported')


def _bytes(value):
    if type(value) is not str or len(value) > 90 * 1024 * 1024:
        raise ValueError('upload_missing_or_too_large')
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('upload_base64_invalid') from exc
    if not result or len(result) > 64 * 1024 * 1024:
        raise ValueError('upload_missing_or_too_large')
    return result


def _delivery_identity(runtime, version, loaded_source):
    """Present existing provenance; a commit alone is not a build-byte identity."""
    source = runtime['source_identity']
    build = source.get('build_receipt')
    verified_build = source.get('status') == 'BUILD_VERIFIED' and type(build) is dict
    git = build.get('git', {}) if verified_build else {}
    commit = git.get('commit') if type(git) is dict else None
    if type(commit) is not str or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
        commit = None
    checkout = source.get('status') == 'CONTENT_HASHED'
    return dict(package_version=None if checkout else version,
        origin='SOURCE_CHECKOUT' if checkout else 'INSTALLED_BUILD' if verified_build else 'UNKNOWN',
        build_commit=commit, build_worktree_status=git.get('status', 'UNKNOWN') if type(git) is dict else 'UNKNOWN',
        source_status=source.get('status', 'UNKNOWN'),
        checkout_git=source.get('git') if checkout else None,
        loaded_source_sha256=loaded_source, disk_source_sha256=source.get('content_sha256'),
        package_location=runtime.get('machine_receipt', {}).get('package_location'),
        environment_status=runtime['environment_verified'].get('status', 'UNKNOWN'),
        dependency_lock_sha256=runtime['environment_verified'].get('lock_sha256'))


def _account_compatibility(saved, runtime, loaded_source, loaded_environment):
    """Read-only projection of the ledger's original code/dependency binding."""
    current = dict(source_sha256=runtime['source_identity'].get('content_sha256'),
        dependencies=runtime['environment_verified'])
    reasons = []
    if type(saved) is not dict or set(saved) != set(current):
        reasons.append('SAVED_RUNTIME_UNKNOWN')
    else:
        if saved['source_sha256'] != current['source_sha256']:
            reasons.append('CODE_CONTENT_CHANGED')
        if saved['dependencies'] != current['dependencies']:
            reasons.append('DEPENDENCIES_CHANGED')
    if current['source_sha256'] != loaded_source or current['dependencies'] != loaded_environment:
        reasons.append('PROCESS_RESTART_REQUIRED')
    return dict(status='READ_ONLY' if reasons else 'CONTINUABLE', can_continue=not reasons,
        reasons=reasons, saved_runtime=saved, current_runtime=current,
        policy='ORIGINAL_CODE_AND_DEPENDENCIES_REQUIRED_NO_POSITION_MIGRATION')


def _project_source_hashes(result):
    rows = result.get('source_manifest')
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        raise ValueError('research_source_manifest_invalid')
    return [row['record_sha256'] for row in rows if row.get('source_kind') == 'project_source']


class Workbench:
    def __init__(self, workspace):
        root = Path(workspace).expanduser().absolute()
        _regular(root)
        self.root = root.resolve()
        self.lock = RLock()
        self.loaded_source = _LOADED_SOURCE
        self.loaded_environment = build_runtime_provenance()['environment_verified']
        for name in ('data', 'tasks', 'runs', 'continuous', 'operations', 'watches', 'research-imports', 'research-bindings', 'exports', 'updates', 'validations'):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def path(self, ref, area=None):
        if type(ref) is not str or not ref or '\\' in ref or ':' in ref:
            raise ValueError('workspace_reference_invalid')
        relative = Path(ref)
        if relative.is_absolute() or '..' in relative.parts or (area and relative.parts[0] != area):
            raise ValueError('workspace_reference_outside_allowed_area')
        path = self.root / relative
        _regular(path)
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('workspace_reference_outside_workspace')
        return path

    def ref(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def _item(self, path, reader):
        _regular(path)
        try:
            return dict(reader(path), ref=self.ref(path))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            return dict(ref=self.ref(path), status='STOPPED', error=str(exc))

    def run_view(self, ref):
        from .task_validation import saved_run_diagnostics
        path = self.path(ref, 'runs')
        manifest, report, _ = verify_run(path)
        result = report['result']
        return dict(ref=ref, view=describe_run(path),
            summary={key: result.get(key) for key in ('total_return', 'max_drawdown', 'final_equity',
                'total_fees', 'fill_count', 'realized_pnl', 'unrealized_pnl', 'open_position_qty')},
            signals=result['signals'], fills=result['fills'], equity_curve=result['equity_curve'],
            runtime=manifest['runtime'], inputs=manifest['task'], diagnostics=saved_run_diagnostics(path))

    def daily_update_view(self, ref):
        from .daily_updates import read_daily_update
        result = read_daily_update(self.path(ref, 'updates'))
        receipt = result.get('freeze_receipt') or {}
        if receipt:
            frozen = self.path(receipt['input_ref'], 'data')
            if hashlib.sha256(frozen.read_bytes()).hexdigest() != receipt['input_file_sha256']:
                raise ValueError('daily_update_frozen_input_missing_or_changed')
        return dict(result, ref=ref, frozen_input_ref=receipt.get('input_ref'))

    def validation_view(self, ref):
        from .task_validation import read_validation
        return dict(read_validation(self.path(ref, 'validations')), ref=ref)

    def account_view(self, ref, *, runtime=None):
        from .continuous_runtime import describe_continuous_account
        path = self.path(ref, 'continuous')
        result = describe_continuous_account(path)
        connection = read_document(path / 'workbench-binding.json')
        manifest = read_document(path / 'account.json')
        compatibility = _account_compatibility(manifest.get('runtime'), runtime or build_runtime_provenance(),
            self.loaded_source, self.loaded_environment)
        return dict(result, ref=ref, title=connection['title'], task_refs=connection['tasks'],
            compatibility=compatibility)

    def watch_view(self, ref):
        from .continuous_watch import describe_watch
        path = self.path(ref, 'watches')
        return dict(describe_watch(path), ref=ref, account=read_document(path / 'workbench-binding.json')['account'])

    def _research_bundle(self, ref):
        from hashlib import sha256
        from .collaboration_schedule_adapter import assess_schedule_import
        folder = self.path(ref, 'research-imports')
        for name in ('collaboration-result.json', 'event-context.json', 'confirmation.json',
                     'assessment.json', 'project-source.raw'):
            _regular(folder / name)
        saved = read_document(folder / 'assessment.json')
        result_raw = (folder / 'collaboration-result.json').read_bytes()
        assessment = assess_schedule_import(result_raw, (folder / 'event-context.json').read_bytes(),
            (folder / 'confirmation.json').read_bytes(), expected_security_id=saved['security_id'])
        if assessment != saved or assessment['status'] != 'READY_FOR_EXPLICIT_INPUT_CHECK':
            raise ValueError('research_confirmation_or_retained_bytes_changed')
        sources = _project_source_hashes(parse_document(result_raw))
        if sources != [sha256((folder / 'project-source.raw').read_bytes()).hexdigest()]:
            raise ValueError('research_original_source_hash_mismatch')
        return folder, assessment

    def _bind_receipt(self, task, research, assessment):
        view = describe_task(task)
        body = dict(schema_version='workbench-research-binding-v1', task_id=view['task_id'],
            family_id=view.get('family_id'), revision=view.get('viewed_revision'),
            research=research, assessment_hash=assessment['assessment_hash'], context_hash=assessment['context_hash'])
        record = dict(body, binding_hash=digest(body))
        write_new(self.root / 'research-bindings' / (view['task_id'] + '.json'), record)
        return record

    def close(self):
        from .continuous_watch import stop_watch
        for path in (self.root / 'watches').iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                stop_watch(path)

    def state(self):
        with self.lock:
            runtime = build_runtime_provenance()
            inputs = [item for item in list_inputs(self.root)['items']
                      if not Path(item['path']).is_relative_to(self.root / 'data' / 'watch-inbox')]
            for item in inputs:
                item['ref'] = self.ref(item['path'])
            tasks = [self._item(p, describe_task) for p in list_tasks(self.root)]
            runs = [self._item(p, describe_run) for p in sorted((self.root / 'runs').glob('run-*')) if p.is_dir()]
            accounts = [self._item(p, lambda q: self.account_view(self.ref(q), runtime=runtime))
                        for p in sorted((self.root / 'continuous').iterdir())
                        if p.is_dir() and not p.name.startswith('.')]
            # State summaries exclude the complete immutable snapshots/ledger.
            accounts = [{k: v for k, v in a.items() if k not in {'history', 'state'}} for a in accounts]
            operations = [read_document(p) for p in sorted((self.root / 'operations').glob('*/result.json'))]
            pending = [dict(operation_id=p.parent.name, status='UNKNOWN_REQUIRES_REVIEW',
                request_hash=read_document(p)['request_hash'])
                for p in sorted((self.root / 'operations').glob('*/request.json'))
                if not (p.parent / 'result.json').exists()]
            restart_required = (runtime['source_identity'].get('content_sha256') != self.loaded_source
                                or runtime['environment_verified'] != self.loaded_environment)
            try:
                version = metadata.version('hakimi-research')
            except metadata.PackageNotFoundError:
                version = 'source-checkout'
            catalog = strategies()
            for key, entry in catalog.items():
                entry['defaults'] = new_task_parameters(entry['engine_strategy'])
                entry['required_context_sessions'] = required_task_context(key, entry['defaults'])
                entry['continuous_supported'] = key in {'price.dual_ma@1', 'price.buy_and_hold@1', 'event.earnings_schedule@1'}
            watches = [self._item(p, lambda q: self.watch_view(self.ref(q)))
                       for p in sorted((self.root / 'watches').iterdir())
                       if p.is_dir() and not p.name.startswith('.')]
            research = [dict(read_document(p), ref=self.ref(p.parent))
                        for p in sorted((self.root / 'research-imports').glob('*/assessment.json'))]
            updates = [self._item(p, lambda q: self.daily_update_view(self.ref(q)))
                       for p in sorted((self.root / 'updates').glob('check-*')) if p.is_dir()]
            validations = [self._item(p, lambda q: self.validation_view(self.ref(q)))
                           for p in sorted((self.root / 'validations').glob('validation-*')) if p.is_dir()]
            validation_summaries = [{k:v for k,v in row.items()
                if k in {'ref','base','symbol','status','validation_hash','error'}} for row in validations]
            return dict(engine=dict(name='hakimi_research', version=version,
                delivery=_delivery_identity(runtime, version, self.loaded_source),
                source_identity=runtime['source_identity'], environment=runtime['environment_verified'],
                permissions=dict(PERMISSIONS), new_task_default=True), workspace=str(self.root),
                inputs=inputs, tasks=tasks, runs=runs, accounts=accounts, strategies=catalog,
                operations=operations[-20:] + pending, watches=watches, research_imports=research,
                daily_updates=updates[-50:], validations=validation_summaries,
                data_update_policy=dict(calendar_years=[2026], source='Yahoo Finance', max_symbols=1,
                    network='EXPLICIT_CHECK_ONLY', existing_snapshot_required=True),
                server_time=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                runtime_guard=dict(restart_required=restart_required, loaded_source_sha256=self.loaded_source),
                mode='LOCAL_RESEARCH_ONLY', source_collection='EXPLICIT_FILE_IMPORT_OR_PUBLIC_DAILY_CHECK',
                legacy_policy='Historical engines and results retain their own original identities and entry points.')

    def action(self, request):
        if type(request) is not dict:
            raise ValueError('action_object_required')
        action = request.get('action')
        if action == 'task_context':
            from .equity_dataset import verify_equity_snapshot
            from .strategy_registry import definition
            strategy = request['strategy']
            entry = definition(strategy)
            params = request.get('params') or new_task_parameters(entry['engine_strategy'])
            required = required_task_context(strategy, params)
            data = verify_equity_snapshot(read_document(self.path(request['snapshot'], 'data')))
            sessions = data['sessions']
            return dict(required_context_sessions=required, sessions=len(sessions),
                suggested_score_start=sessions[required]['date'] if len(sessions) > required else None,
                coverage_end=sessions[-1]['date'], admission='FULL_TASK_VALIDATION_REQUIRED_BEFORE_RUN')
        if action == 'compare':
            from .task_comparison import compare_runs
            return compare_runs([self.path(p, 'runs') for p in request['runs']])
        op = request.get('operation_id')
        if type(op) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', op):
            raise ValueError('explicit_operation_id_required')
        folder = self.root / 'operations' / op
        fingerprint = digest(request)
        with self.lock, _file_lock(self.root / '.workbench.lock'):
            _regular(folder)
            if (folder / 'request.json').exists():
                saved = read_document(folder / 'request.json')
                if saved['request_hash'] != fingerprint:
                    raise ValueError('operation_id_payload_conflict')
                if (folder / 'result.json').exists():
                    result = read_document(folder / 'result.json')
                    if not result['ok']:
                        raise ValueError(result['error'])
                    return result['result']
                raise ValueError('operation_outcome_unknown:inspect_saved_artifacts_before_retry')
            runtime = build_runtime_provenance()
            if action != 'stop_watch' and (runtime['source_identity'].get('content_sha256') != self.loaded_source
                    or runtime['environment_verified'] != self.loaded_environment):
                raise ValueError('workbench_restart_required_source_or_dependencies_changed')
            write_new(folder / 'request.json', dict(request_hash=fingerprint, request=request))
            try:
                result = self._dispatch(request)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                write_new(folder / 'result.json', dict(operation_id=op, ok=False,
                    status='STOPPED', error=str(exc), automatic_retry=False))
                raise
            write_new(folder / 'result.json', dict(operation_id=op, ok=True, status='COMMITTED', result=result))
            return result

    def _dispatch(self, r):
        action, op = r['action'], r['operation_id']
        if action == 'import_input':
            result = _retain(self.root, _bytes(r['content_base64']))
            return dict(result, ref=self.ref(result['path']))
        if action == 'import_csv':
            stage = self.root / 'operations' / op
            immutable_write(stage / 'prices.csv', _bytes(r['csv_base64']))
            immutable_write(stage / 'metadata.json', _bytes(r['manifest_base64']))
            result = import_price_csv(stage / 'prices.csv', stage / 'metadata.json', self.root)
            return dict(result, ref=self.ref(result['path']))
        if action == 'check_stock_update':
            from .daily_updates import check_daily_update
            directory = self.root / 'updates' / ('check-' + op)
            check_daily_update(self.path(r['snapshot'], 'data'), directory)
            return self.daily_update_view(self.ref(directory))
        if action == 'freeze_stock_update':
            from .daily_updates import freeze_daily_update
            acknowledged = r.get('acknowledge_revisions', False)
            if type(acknowledged) is not bool:
                raise ValueError('revision_acknowledgment_exact_bool_required')
            result = freeze_daily_update(self.path(r['update'], 'updates'), self.root,
                acknowledge_revisions=acknowledged)
            return dict(result, ref=self.ref(result['path']))
        if action == 'validate_run':
            from .task_validation import create_validation
            options = {}
            if r.get('followup_snapshot'):
                options = dict(followup_snapshot=self.path(r['followup_snapshot'], 'data'),
                    followup_start=r.get('followup_start'), followup_end=r.get('followup_end'))
            elif r.get('followup_start') or r.get('followup_end'):
                raise ValueError('followup_snapshot_required_for_dates')
            run = self.path(r['run'], 'runs')
            manifest, report, _ = verify_run(run)
            key = digest(dict(method='hakimi-task-validation-v1', run_id=manifest['run_id'],
                report_hash=report['report_hash'], followup_sha256=hashlib.sha256(
                    options['followup_snapshot'].read_bytes()).hexdigest() if options else None,
                followup_start=options.get('followup_start'), followup_end=options.get('followup_end')))
            directory = self.root / 'validations' / ('validation-' + key)
            _regular(directory)
            reused = directory.exists()
            if not reused:
                create_validation(run, directory, **options)
            result = self.validation_view(self.ref(directory))
            return dict(result, reused_saved_validation=reused,
                action_new_economic_runs=0 if reused else result['new_economic_runs'])
        if action == 'bind_task_input':
            from .equity_dataset import verify_equity_snapshot
            from .task_manager import revise_family, version_options
            family = self.path(r['task'], 'tasks')
            if not family.is_dir():
                raise ValueError('managed_task_required_for_input_version_update')
            expected = r.get('expected_task_id')
            before = describe_task(family)
            if not expected or expected != before['task_id']:
                raise ValueError('task_changed_reload_before_updating_inputs')
            options = version_options(family)
            snapshot = self.path(r['snapshot'], 'data')
            previous = verify_equity_snapshot(read_document(options['snapshot']))
            updated = verify_equity_snapshot(read_document(snapshot))
            if previous['security'] != updated['security']:
                raise ValueError('input_update_requires_same_security')
            if type(r.get('score_end')) is not str or r['score_end'] < options['score_end']:
                raise ValueError('input_update_requires_explicit_non_decreasing_score_end')
            if previous['snapshot_id'] == updated['snapshot_id'] and r['score_end'] == options['score_end']:
                return dict(before, ref=r['task'], input_update_status='UNCHANGED_NO_NEW_VERSION')
            old_binding = self.root / 'research-bindings' / (expected + '.json')
            approved, research_ref = None, None
            if old_binding.exists():
                _regular(old_binding)
                binding = read_document(old_binding)
                if (binding.get('task_id') != expected or binding.get('binding_hash') !=
                        digest({k:v for k,v in binding.items() if k != 'binding_hash'})):
                    raise ValueError('research_binding_identity_changed')
                research_ref = binding['research']
                _, approved = self._research_bundle(research_ref)
                if (options['strategy'] != 'event.earnings_schedule@1' or not options['event_context'] or
                        read_document(options['event_context'])['context_hash'] != approved['context_hash']):
                    raise ValueError('research_binding_context_mismatch')
            revised = revise_family(family, expected_task_id=expected, snapshot=snapshot, score_end=r['score_end'])
            version = family / 'versions' / revised['selected_revision'] / 'task.json'
            if approved is not None:
                self._bind_receipt(version, research_ref, approved)
            return dict(describe_task(version), ref=r['task'], input_update_status='NEW_IMMUTABLE_VERSION')
        if action == 'create_task':
            options = {k: r[k] for k in ('strategy', 'params', 'score_start', 'score_end',
                        'initial_cash', 'fee_rate', 'slippage_pct', 'risk') if k in r and r[k] is not None}
            options['snapshot'] = self.path(r['snapshot'], 'data')
            if r.get('event_context'):
                options['event_context'] = self.path(r['event_context'], 'data')
            approved = None
            if r.get('research'):
                _, approved = self._research_bundle(r['research'])
                if (r['strategy'] != 'event.earnings_schedule@1' or not options.get('event_context')
                        or read_document(options['event_context'])['context_hash'] != approved['context_hash']):
                    raise ValueError('explicit_schedule_task_and_confirmed_input_must_match')
            family = self.root / 'tasks' / ('task-' + op)
            create_family(family, title=r.get('title'), **options)
            if approved is not None:
                self._bind_receipt(family, r['research'], approved)
            return dict(describe_task(family), ref=self.ref(family))
        if action == 'run_task':
            directory = run_task(self.path(r['task'], 'tasks'), output_dir=self.root / 'runs')
            return self.run_view(self.ref(directory))
        if action == 'task_state':
            family = self.path(r['task'], 'tasks')
            change_state(family, r['state'])
            return dict(describe_task(family), ref=self.ref(family))
        if action == 'create_account':
            from .continuous_runtime import create_continuous_account
            paths = [self.path(ref, 'tasks') for ref in r['tasks']]
            directory = self.root / 'continuous' / ('account-' + op)
            create_continuous_account(directory, paths, initial_cash=r.get('initial_cash', 10000), limits=r['limits'])
            write_new(directory / 'workbench-binding.json', dict(title=r.get('title') or '连续日线研究', tasks=r['tasks']))
            return self.account_view(self.ref(directory))
        if action == 'advance':
            from .continuous_runtime import advance_continuous_account
            directory = self.path(r['account'], 'continuous')
            snapshots = {}
            for ref in r['snapshots']:
                value = read_document(self.path(ref, 'data'))
                security = value['security']['security_id']
                if security in snapshots:
                    raise ValueError('one_snapshot_per_security_required')
                snapshots[security] = value
            binding = read_document(directory / 'workbench-binding.json')
            observed = r.get('observed_at') or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', observed):
                raise ValueError('observation_exact_utc_seconds_required')
            if datetime.fromisoformat(observed.replace('Z', '+00:00')) > datetime.now(timezone.utc):
                raise ValueError('future_observation_time_not_allowed')
            receipt = advance_continuous_account(directory, snapshots, through=r['through'],
                observed_at=observed, operation_id=op,
                task_files=[self.path(ref, 'tasks') for ref in binding['tasks']])
            return dict(receipt=receipt, account=self.account_view(r['account']))
        if action == 'pause_account':
            from .shared_account import transact_shared_account
            directory = self.path(r['account'], 'continuous')
            view = self.account_view(r['account'])
            if type(r['paused']) is not bool:
                raise ValueError('paused_exact_bool_required')
            receipt = transact_shared_account(directory, operation_id=op, kind='PAUSE' if r['paused'] else 'RESUME',
                at=view['state']['current_at'], payload=dict(reason='USER_STOP_NEW_BUYS_KEEP_PROTECTION')
                if r['paused'] else dict(expected_head=view['receipt_head']))
            return dict(receipt=receipt, account=self.account_view(r['account']))
        if action == 'account_task_state':
            from .continuous_runtime import set_continuous_task_state
            directory = self.path(r['account'], 'continuous')
            receipt = set_continuous_task_state(directory, r['owner'], r['paused'], operation_id=op)
            return dict(receipt=receipt, account=self.account_view(r['account']))
        if action == 'reset_loss':
            from .continuous_runtime import reset_continuous_loss
            directory = self.path(r['account'], 'continuous')
            receipt = reset_continuous_loss(directory, operation_id=op, expected_head=r['expected_head'])
            return dict(receipt=receipt, account=self.account_view(r['account']))
        if action == 'discard_watch_pending':
            from .continuous_watch import discard_uncommitted_pending
            directory = self.path(r['watch'], 'watches')
            view = self.watch_view(r['watch'])
            if view['monitoring'] or view['status'] != 'PENDING_REVIEW_REQUIRED':
                raise ValueError('stop_observation_and_review_pending_request_before_discard')
            discard_uncommitted_pending(directory, expected_operation_id=r['expected_operation_id'], reason=r['reason'])
            return self.watch_view(r['watch'])
        if action == 'recover_watch_pending':
            from .continuous_watch import recover_watch_pending
            directory = self.path(r['watch'], 'watches')
            recover_watch_pending(directory, expected_operation_id=r['expected_operation_id'])
            return self.watch_view(r['watch'])
        if action == 'configure_watch':
            from .continuous_watch import configure_watch
            from .equity_dataset import verify_equity_snapshot
            directory = self.root / 'watches' / ('watch-' + op)
            inbox = self.root / 'data' / 'watch-inbox' / op
            mapping = {}
            for ref in r['snapshots']:
                raw = self.path(ref, 'data').read_bytes()
                document = verify_equity_snapshot(parse_document(raw))
                security = document['security']['security_id']
                if security in mapping:
                    raise ValueError('one_snapshot_per_security_required')
                target = inbox / (digest(security) + '.json')
                immutable_write(target, raw)
                mapping[security] = str(target)
            account_dir = self.path(r['account'], 'continuous')
            binding = read_document(account_dir / 'workbench-binding.json')
            configure_watch(directory, account_dir, mapping,
                interval_seconds=r.get('interval_seconds', 5), max_data_age_seconds=r.get('max_data_age_seconds', 345600),
                task_files=[self.path(ref, 'tasks') for ref in binding['tasks']])
            write_new(directory / 'workbench-binding.json', dict(account=r['account'], inputs=mapping))
            return self.watch_view(self.ref(directory))
        if action in {'start_watch', 'stop_watch'}:
            from .continuous_watch import start_watch, stop_watch
            directory = self.path(r['watch'], 'watches')
            (start_watch if action == 'start_watch' else stop_watch)(directory)
            return self.watch_view(r['watch'])
        if action == 'update_watch_input':
            from .equity_dataset import verify_equity_snapshot
            directory = self.path(r['watch'], 'watches')
            mapping = read_document(directory / 'workbench-binding.json')['inputs']
            raw = self.path(r['snapshot'], 'data').read_bytes()
            document = verify_equity_snapshot(parse_document(raw))
            security = document['security']['security_id']
            if security not in mapping:
                raise ValueError('snapshot_security_not_in_watch')
            target = self.path(self.ref(mapping[security]), 'data')
            temporary = target.with_name(target.name + '.' + op + '.pending')
            immutable_write(temporary, raw)
            os.replace(temporary, target)
            return dict(status='WATCH_INPUT_UPDATED', security_id=security, snapshot_id=document['snapshot_id'],
                original_frozen_input_retained=True)
        if action == 'preview_research':
            from hashlib import sha256
            from .collaboration_schedule_adapter import assess_schedule_import
            result_raw = _bytes(r['result_base64'])
            context_raw = _bytes(r['context_base64']) if r.get('context_base64') else None
            assessment = assess_schedule_import(result_raw, context_raw, None, expected_security_id=r['security_id'])
            folder = self.root / 'research-imports' / ('research-' + op)
            immutable_write(folder / 'collaboration-result.json', result_raw)
            if context_raw is not None:
                immutable_write(folder / 'event-context.json', context_raw)
            if r.get('source_base64'):
                source_raw = _bytes(r['source_base64'])
                result = parse_document(result_raw)
                hashes = _project_source_hashes(result)
                if hashes != [sha256(source_raw).hexdigest()]:
                    raise ValueError('research_original_source_hash_mismatch')
                immutable_write(folder / 'project-source.raw', source_raw)
            write_new(folder / 'assessment.json', assessment)
            return dict(assessment, ref=self.ref(folder), original_source_retained=(folder / 'project-source.raw').exists())
        if action == 'review_research':
            from hashlib import sha256
            from .collaboration_schedule_adapter import assess_schedule_import, CONFIRMATION_VERSION
            folder = self.path(r['research'], 'research-imports')
            result_raw = (folder / 'collaboration-result.json').read_bytes()
            context_raw = (folder / 'event-context.json').read_bytes()
            result = parse_document(result_raw)
            source_path = folder / 'project-source.raw'
            if r['decision'] == 'ACCEPT_FOR_INPUT_CHECK':
                if not source_path.is_file():
                    raise ValueError('research_original_source_bytes_required_before_acceptance')
                sources = _project_source_hashes(result)
                if sources != [sha256(source_path.read_bytes()).hexdigest()]:
                    raise ValueError('research_original_source_hash_mismatch')
            previous = read_document(folder / 'assessment.json')
            confirmation = dict(version=CONFIRMATION_VERSION, decision=r['decision'], actor=r['actor'],
                reason=r['reason'], confirmed_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                result_sha256=result['result_sha256'], context_file_sha256=sha256(context_raw).hexdigest(),
                security_id=previous['security_id'])
            from .documents import canonical_bytes
            assessment = assess_schedule_import(result_raw, context_raw, canonical_bytes(confirmation),
                expected_security_id=previous['security_id'])
            # Every review is a new immutable record; prior refusal is retained.
            reviewed = self.root / 'research-imports' / ('review-' + op)
            immutable_write(reviewed / 'collaboration-result.json', result_raw)
            immutable_write(reviewed / 'event-context.json', context_raw)
            if source_path.is_file():
                immutable_write(reviewed / 'project-source.raw', source_path.read_bytes())
            immutable_write(reviewed / 'confirmation.json', canonical_bytes(confirmation))
            write_new(reviewed / 'assessment.json', assessment)
            response = dict(assessment, ref=self.ref(reviewed))
            if assessment['status'] == 'READY_FOR_EXPLICIT_INPUT_CHECK':
                retained = _retain(self.root, context_raw)
                response['input'] = dict(retained, ref=self.ref(retained['path']))
            return response
        if action == 'bind_research':
            from .input_workflow import bind_inputs
            folder, assessment = self._research_bundle(r['research'])
            task = self.path(r['task'], 'tasks')
            if describe_task(task)['strategy'] != 'event.earnings_schedule@1':
                raise ValueError('explicit_schedule_task_required_parameters_never_automatically_changed')
            retained = _retain(self.root, (folder / 'event-context.json').read_bytes())
            result = bind_inputs(task, event_context=retained['path'])
            binding = self._bind_receipt(task, r['research'], assessment)
            return dict(result, ref=self.ref(task), research_binding=binding)
        if action == 'export_research_result':
            folder, assessment = self._research_bundle(r['research'])
            run = self.path(r['run'], 'runs')
            manifest, report, _ = verify_run(run)
            if (assessment['status'] != 'READY_FOR_EXPLICIT_INPUT_CHECK'
                    or manifest['task']['event_context_hash'] != assessment['context_hash']):
                raise ValueError('saved_result_not_bound_to_confirmed_research_input')
            binding_path = self.root / 'research-bindings' / (manifest['task_id'] + '.json')
            _regular(binding_path)
            if not binding_path.is_file():
                raise ValueError('saved_result_predates_this_research_binding_create_bound_version_and_run')
            binding = read_document(binding_path)
            if (binding.get('binding_hash') != digest({k: v for k, v in binding.items() if k != 'binding_hash'})
                    or binding.get('task_id') != manifest['task_id'] or binding.get('research') != r['research']
                    or binding.get('assessment_hash') != assessment['assessment_hash']):
                raise ValueError('saved_result_research_approval_binding_mismatch')
            target = self.root / 'exports' / ('research-return-' + op)
            # Return native contracts and frozen evidence, not a new protocol.
            sources = ((run / 'report.json', 'quant-report.json'),
                    (folder / 'collaboration-result.json', 'collaboration-result.json'),
                    (folder / 'event-context.json', 'event-context.json'),
                    (folder / 'assessment.json', 'input-assessment.json'),
                    (folder / 'confirmation.json', 'human-confirmation.json'),
                    (folder / 'project-source.raw', 'project-source.raw'))
            exported_bytes = {name: source.read_bytes() for source, name in sources}
            view = describe_run(run)
            exported_bytes['result-view.json'] = (json.dumps(view, ensure_ascii=False, indent=2,
                allow_nan=False).encode('utf-8') + b'\n')
            exported_bytes['task-input-binding.json'] = binding_path.read_bytes()
            feedback = build_feedback_markdown(manifest, report, assessment,
                read_document(folder / 'confirmation.json'), binding, exported_bytes)
            feedback_sha256 = hashlib.sha256(feedback).hexdigest()
            feedback_filename = 'research-feedback-' + feedback_sha256 + '.md'
            for name, raw in exported_bytes.items():
                immutable_write(target / name, raw)
            immutable_write(target / feedback_filename, feedback)
            return dict(status='FROZEN_RESEARCH_RETURN_READY', directory=str(target), ref=self.ref(target),
                research_input_outcome=view['research_input_outcome'], report_hash=report['report_hash'],
                feedback_filename=feedback_filename, feedback_sha256=feedback_sha256,
                feedback_ref=self.ref(target / feedback_filename),
                feedback_bytes=len(feedback), feedback_characters=len(feedback.decode('utf-8')),
                feedback_material_import_ready=(len(feedback) <= 2_000_000
                    and len(feedback.decode('utf-8')) <= 50_000),
                delivery_status='LOCAL_EXPORT_ONLY_NOT_RECEIVED', external_database_modified=False)
        raise ValueError('unsupported_workbench_action')
