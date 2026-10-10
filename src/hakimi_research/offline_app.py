"""Installed task workflow using existing snapshots, runner, risk and replay."""
from __future__ import annotations
from datetime import datetime, timezone
from contextlib import contextmanager
from html import escape
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .documents import digest, read_document, canonical_bytes
from .equity_dataset import load_equity_snapshot
from .equity_event_context import verify_event_context
from .equity_research import EquityResearchReport, EquityExperimentSpec, inspect_equity_inputs, verify_equity_report, replay_equity_report, PERMISSIONS
from .environment import build_runtime_provenance
from .reporting import _save_encoded_report
from .report_style import CARD_STYLE
from .strategy_registry import (definition, strategy_identity, validate_strategy, run_strategy,
    inspect_task_inputs, verify_task_report, replay_task_report)


def write_new(path, value):
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n'
    immutable_write(path, encoded)


def immutable_write(path, encoded):
    path = Path(path)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != encoded:
            raise ValueError('existing_output_conflict:' + path.name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _save_encoded_report(encoded, path)


def resolve_location(base, value):
    if type(value) is not str or not value.strip():
        raise ValueError('explicit_input_path_required')
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(base) / path
    return path.resolve()


def portable_location(path, base, *, relative_root=None):
    path, base = Path(path).resolve(), Path(base).resolve()
    root = Path(relative_root).resolve() if relative_root is not None else base
    if not path.is_relative_to(root):
        return str(path)
    try:
        return Path(os.path.relpath(path, base)).as_posix()
    except ValueError:
        return str(path)


def resolve_input(task_file, value):
    path = resolve_location(Path(task_file).parent, value)
    if not path.is_file():
        raise ValueError('input_file_missing:' + str(path))
    return path


@contextmanager
def _file_lock(path, *, create=True):
    if Path(path).is_symlink():
        raise ValueError('run_lock_path_is_not_regular')
    handle = Path(path).open('a+b' if create else 'r+b')
    try:
        if handle.seek(0, 2) == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('run_has_an_active_owner:do_not_resume_or_repeat') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _run_name(directory):
    name = Path(directory).name
    prepared = re.fullmatch(r'\.preparing-(run-[0-9a-f]{64})-[0-9a-f]{32}', name)
    return prepared.group(1) if prepared else name


@contextmanager
def run_lock(directory):
    """Claim initialization and calculation with the same OS-held mutex."""
    directory = Path(directory).resolve()
    locks = directory.parent / '.run-locks'
    locks.mkdir(parents=True, exist_ok=True)
    with _file_lock(locks / (_run_name(directory) + '.lock')):
        legacy = directory / '.run.lock'
        if legacy.exists():
            with _file_lock(legacy, create=False):
                yield
        else:
            yield


def check_task(task_file, *, inspect_only=False):
    from .task_manager import resolve_managed_task, TASK_SCHEMA
    task_file = resolve_managed_task(task_file, inspect_only=inspect_only)
    task = read_document(task_file)
    fields = {'schema_version', 'strategy', 'state', 'snapshot', 'event_context', 'experiment', 'output_dir'}
    if task.get('schema_version') == TASK_SCHEMA:
        fields.add('management')
    if set(task) != fields or task['schema_version'] not in {'hakimi-offline-task-v1', TASK_SCHEMA}:
        raise ValueError('offline_task_fields_or_schema_invalid')
    if task['state'] not in {'ENABLED', 'PAUSED'} or (task['state'] != 'ENABLED' and not inspect_only):
        raise ValueError('task_paused:enable_in_configuration_before_running')
    entry = definition(task['strategy'])
    snapshot_path = resolve_input(task_file, task['snapshot'])
    snapshot = load_equity_snapshot(snapshot_path)
    context_path = resolve_input(task_file, task['event_context']) if task['event_context'] is not None else None
    from .input_workflow import verify_research_context
    context = verify_research_context(read_document(context_path)) if context_path else None
    checked_spec = validate_strategy(task['strategy'], task['experiment'], context)
    spec = checked_spec.document
    if task['schema_version'] == TASK_SCHEMA:
        from .trade_cli import validate_configuration
        validate_configuration(spec)
    else:
        # Legacy inputs share numeric admission, but retain their historical
        # clipping policy. Frozen run verification still uses its original spec.
        from .trade_cli import validate_runtime_configuration
        validate_runtime_configuration(spec)
    if spec['snapshot_id'] != snapshot.snapshot_id:
        raise ValueError('task_snapshot_identity_conflict')
    if not snapshot.document['research_admission']['allowed']:
        raise ValueError('data_blocked:' + ','.join(snapshot.document['research_admission']['block_reasons']))
    if context and context['security_id'] != snapshot.document['security']['security_id']:
        raise ValueError('event_context_security_conflict')
    if snapshot.document['research_admission']['synthetic_only'] and spec['purpose'] != 'SYNTHETIC_REGRESSION':
        raise ValueError('synthetic_inputs_cannot_be_market_evidence')
    # Validate the scoring and warmup clocks without running a strategy.
    protocol = inspect_task_inputs(snapshot, checked_spec, event_context=context)
    semantics = dict(schema_version=task['schema_version'], strategy=task['strategy'], state=task['state'],
        strategy_identity=strategy_identity(task['strategy']), experiment=spec,
        event_context_hash=context['context_hash'] if context else None)
    if 'management' in task:
        semantics['management'] = task['management']
    task_id = digest(semantics)
    output = resolve_location(task_file.parent, task['output_dir'])
    return dict(task_id=task_id, semantics=semantics, definition=entry, snapshot=snapshot,
        context=context, snapshot_path=snapshot_path, context_path=context_path,
        task_path=task_file, output=output.resolve(), protocol=protocol)


def _publish_prepared_run(stage, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError('existing_run_directory_not_replaced:' + str(destination))
    stage.rename(destination)


def _prepare_run(context, runtime, run_id, destination):
    stage = destination.parent / ('.preparing-' + destination.name + '-' + uuid4().hex)
    try:
        stage.mkdir(exist_ok=False)
        write_new(stage / 'preparation.json', dict(schema_version='hakimi-run-preparation-v1',
            run_id=run_id, task_id=context['task_id'], state='PREPARING', strategy_started=False))
        inputs = {'snapshot.json': context['snapshot_path'].read_bytes()}
        if context['context_path']:
            inputs['event-context.json'] = context['context_path'].read_bytes()
        for name, content in inputs.items():
            immutable_write(stage / 'inputs' / name, content)
        manifest = dict(schema_version='hakimi-offline-run-inputs-v1', run_id=run_id, task_id=context['task_id'],
            task=context['semantics'], input_sha256={name: __import__('hashlib').sha256(raw).hexdigest() for name, raw in inputs.items()},
            runtime=runtime, execution_permission=dict(PERMISSIONS))
        write_new(stage / 'inputs.json', manifest)
        write_new(stage / 'started.json', dict(started_at=datetime.now(timezone.utc).isoformat(), run_id=run_id))
        # Validate the sealed copies before making this directory a resumable run.
        verify_run_inputs(stage, allow_preparation=True)
        _publish_prepared_run(stage, destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if stage.is_dir():
            try:
                write_new(stage / 'preparation-failure.json', dict(error_type=type(exc).__name__, error=str(exc),
                    strategy_started=False, published=False, automatic_retry=False,
                    next_action='RUN_ORIGINAL_TASK_AGAIN', original_partial_files_retained=True))
            except (OSError, ValueError):
                pass  # Full disks can also prevent diagnostics; partial input bytes remain.
        raise ValueError('run_initialization_not_published:' + str(stage)
            + '; original partial files retained; run the original task again; ' + str(exc)) from exc


def run_task(task_file, *, output_dir=None):
    from .task_manager import execution_guard
    with execution_guard(task_file) as selected:
        return _run_task(selected, output_dir=output_dir)


def _run_task(task_file, *, output_dir=None):
    context = check_task(task_file)
    runtime = build_runtime_provenance()
    if runtime['source_identity']['status'] not in {'CONTENT_HASHED', 'BUILD_VERIFIED'} or runtime['environment_verified']['status'] != 'VERIFIED':
        raise ValueError('runtime_source_or_dependencies_unverified')
    run_id = digest(dict(task_id=context['task_id'], source_hash=runtime['source_identity']['content_sha256'],
        environment=runtime['environment_verified']))
    output = Path(output_dir).expanduser().resolve() if output_dir is not None else context['output']
    destination = output / ('run-' + run_id)
    with run_lock(destination):
        # Recheck only after claiming the run: another owner may have finished it.
        if destination.exists():
            if (destination / 'report.json').is_file():
                recover_report(destination)
                return destination
            if not (destination / 'inputs.json').is_file() or not (destination / 'started.json').is_file():
                raise ValueError('run_initialization_incomplete:' + str(destination)
                    + '; original directory retained; use run --task <original task> --output-dir <new output directory>; do not resume incomplete inputs')
            raise ValueError('interrupted_calculation_no_saved_report:' + str(destination) + '; explicitly use recover --resume-calculation')
        _prepare_run(context, runtime, run_id, destination)
        if (destination / 'report.json').is_file():
            recover_report(destination)
            return destination
        snapshot = load_equity_snapshot(destination / 'inputs/snapshot.json')
        event_context = read_document(destination / 'inputs/event-context.json') if context['context'] else None
        try:
            report = run_strategy(context['semantics']['strategy'], snapshot, context['semantics']['experiment'], event_context)
            write_new(destination / 'report.json', report.document)
            recover_report(destination)
        except Exception as exc:
            write_new(destination / 'failure.json', dict(error_type=type(exc).__name__, error=str(exc),
                saved_report=(destination / 'report.json').is_file(), automatic_retry=False))
            raise
    return destination


def verify_run_inputs(directory, *, allow_preparation=False):
    from hashlib import sha256
    directory = Path(directory).resolve()
    if directory.name.startswith('.preparing-') and not allow_preparation:
        raise ValueError('run_initialization_not_published:partial files retained; run the original task again')
    if not (directory / 'inputs.json').is_file() or not (directory / 'started.json').is_file():
        raise ValueError('run_initialization_incomplete:original directory retained; rerun the original task with --output-dir <new output directory>')
    manifest = read_document(directory / 'inputs.json')
    started = read_document(directory / 'started.json')
    if set(started) != {'run_id', 'started_at'} or started['run_id'] != manifest['run_id']:
        raise ValueError('run_start_record_identity_conflict')
    if manifest['schema_version'] != 'hakimi-offline-run-inputs-v1' or manifest['execution_permission'] != PERMISSIONS:
        raise ValueError('run_manifest_schema_or_permissions_invalid')
    if manifest['task_id'] != digest(manifest['task']):
        raise ValueError('run_task_identity_conflict')
    runtime = manifest['runtime']
    if manifest['run_id'] != digest(dict(task_id=manifest['task_id'], source_hash=runtime['source_identity']['content_sha256'],
            environment=runtime['environment_verified'])):
        raise ValueError('run_identity_conflict')
    if manifest['task']['strategy_identity'] != strategy_identity(manifest['task']['strategy']):
        raise ValueError('registered_strategy_version_changed')
    for name, expected in manifest['input_sha256'].items():
        if name not in {'snapshot.json', 'event-context.json'}:
            raise ValueError('unexpected_run_input_name')
        path = directory / 'inputs' / name
        if not path.is_file() or path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('retained_input_missing_or_changed:' + name)
    snapshot = load_equity_snapshot(directory / 'inputs/snapshot.json')
    context = read_document(directory / 'inputs/event-context.json') if 'event-context.json' in manifest['input_sha256'] else None
    inspect_task_inputs(snapshot, validate_strategy(manifest['task']['strategy'], manifest['task']['experiment'], context), event_context=context)
    return manifest, snapshot, context


def verify_run(directory):
    directory = Path(directory).resolve()
    manifest, snapshot, context = verify_run_inputs(directory)
    report = verify_task_report(read_document(directory / 'report.json'), snapshot)
    runtime = manifest['runtime']
    if (report['provenance']['source_identity']['content_sha256'] != runtime['source_identity']['content_sha256']
            or report['provenance']['environment_verified'] != runtime['environment_verified']):
        raise ValueError('retained_report_runtime_identity_conflict')
    if report['spec'] != manifest['task']['experiment'] or report['dataset']['snapshot_id'] != snapshot.snapshot_id or report.get('event_context') != context:
        raise ValueError('retained_report_does_not_match_frozen_task')
    return manifest, report, snapshot


def resume_calculation(directory):
    """Explicitly recover an interrupted new-app task; frozen old studies cannot enter."""
    directory = Path(directory).resolve()
    with run_lock(directory):
        if (directory / 'report.json').is_file():
            return recover_report(directory), 0
        manifest, snapshot, context = verify_run_inputs(directory)
        current = build_runtime_provenance()
        if (current['source_identity']['status'] not in {'CONTENT_HASHED', 'BUILD_VERIFIED'}
                or current['source_identity']['content_sha256'] != manifest['runtime']['source_identity']['content_sha256']
                or current['environment_verified'] != manifest['runtime']['environment_verified']):
            raise ValueError('resume_requires_same_verified_code_and_dependency_identity')
        attempts = directory / 'resume-attempts'
        attempts.mkdir(exist_ok=True)
        number = len(list(attempts.glob('*.started.json'))) + 1
        write_new(attempts / f'{number:03d}.started.json', dict(run_id=manifest['run_id'],
            started_at=datetime.now(timezone.utc).isoformat(), explicit_resume=True, prior_failure_preserved=True))
        try:
            report = run_strategy(manifest['task']['strategy'], snapshot, manifest['task']['experiment'], context)
            write_new(directory / 'report.json', report.document)
            page = recover_report(directory)
        except Exception as exc:
            write_new(attempts / f'{number:03d}.failure.json', dict(error_type=type(exc).__name__, error=str(exc), automatic_retry=False))
            raise
        write_new(attempts / f'{number:03d}.completed.json', dict(report_hash=report.document['report_hash'], new_economic_runs=1))
        return page, 1


def render_run(manifest, report, directory):
    entry = definition(manifest['task']['strategy'])
    result = report['result']
    signals = result['signals']
    from .input_workflow import saved_input_outcome, context_view
    outcome = saved_input_outcome(report)
    inputs_html = '<p>行情身份 <code>'+report['dataset']['snapshot_id']+'</code>；研究状态 '+escape(outcome['status'])+'。</p><p>'+escape(outcome['explanation'])+'</p>'
    if report.get('event_context') is not None:
        view = context_view(report['event_context'])
        inputs_html += '<p>研究内容身份 <code>'+view['input_id']+'</code>。</p><ul>'
        for row in view['versions']:
            available=row['availability']
            inputs_html += '<li>'+escape(row['event_id'])+' v'+str(row['version'])+'；可用 '+escape(str(available['available_at']))+' / '+escape(available['available_at_kind'])+'；来源 '+escape(row['source_url'])
            if 'field_review' in row:inputs_html += '；字段核准 '+escape(row['field_review'])
            inputs_html += '</li>'
        inputs_html += '</ul>'
    if report.get('input_reviews') is not None:
        inputs_html += '<ul>'
        for row in outcome['reviews']:
            if row['price_action']=='BUY':
                versions=', '.join(v['event_id']+' v'+str(v['version'])+' / '+v['field_review'] for v in row['known_versions'])
                inputs_html += '<li>'+escape(row['decision_at'])+'：价格 '+escape(row['price_action'])+' → '+escape(row['output_action'])+'；'+escape(row['reason'])+'；'+escape(row['applicability'])+'；所用版本 '+escape(versions or '无可用版本')+'</li>'
        inputs_html += '</ul>'
    reasons = list(dict.fromkeys(r['reason'] for r in signals))
    net = result['final_equity'] - report['spec']['initial_cash']
    title = escape(entry['title'])
    detail = ''.join('<li>' + escape(reason) + '</li>' for reason in reasons)
    warnings = ''.join('<li>' + escape(note) + '</li>' for note in report['limitations'])
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        '<title>哈基米交易 · 离线运行结果</title><style>' + CARD_STYLE + '</style><main><header><small>可安装离线量化工具候选</small>'
        '<h1>' + title + '</h1></header><article class="card"><h2>本次运行</h2><p>策略版本 ' + escape(entry['version']) + '；任务状态 ENABLED。</p>'
        '<p>证券 ' + escape(report['dataset']['security']['symbol']) + '；评分区间 ' + escape(report['spec']['score_start_session']) + ' 至 ' + escape(report['spec']['score_end_session']) + '。</p>'
        '<p>数据类型 ' + escape(report['dataset']['evidence_kind']) + '；日线、碎股、比例费用和固定滑点为模型近似。有效杠杆 1；公司行为记账暂不支持。</p>'
        '<p>BUY 意图 ' + str(sum(r['action'] == 'BUY' for r in signals)) + '；成交 ' + str(result['fill_count']) + '；研究过滤阻挡 ' + str(outcome['blocked_new_buys']) + '。</p>'
        '<p><strong>净收益率 ' + f"{result['total_return']*100:+.4f}%" + '；扣费后损益 ' + f'{net:+.2f}' + ' 美元。</strong></p>'
        '<details><summary>费用与期末持仓</summary><p>费用 ' + f"{result['total_fees']:.2f}" + ' 美元；已实现 ' + f"{result['realized_pnl']:+.2f}" + '；未实现 ' + f"{result['unrealized_pnl']:+.2f}" + '；期末持仓 ' + f"{result['open_position_qty']:.4f}" + ' 股。</p></details>'
        '<details><summary>信号与阻挡原因</summary><ul>' + detail + '</ul></details></article>'
        '<article class="card"><h2>输入与规则影响</h2>'+inputs_html+'</article>'
        '<article class="card"><h2>数据与成交模型边界</h2><ul>' + warnings + '</ul></article>'
        '<footer>输出位置：<code>' + escape(str(directory)) + '</code><br>任务身份：<code>' + manifest['task_id'] + '</code><br>报告身份：<code>' + report['report_hash'] + '</code>'
        '<p>研究内核隔离运行；账户、模拟订单和真实订单权限保持关闭。重放或页面恢复使用保留输入，不访问网络。</p></footer></main></html>')


def recover_report(directory):
    directory = Path(directory).resolve()
    manifest, report, _ = verify_run(directory)
    # Location is display-only: migration updates only a derived view, never report identity.
    encoded = render_run(manifest, report, directory).encode()
    path = directory / 'index.html'
    if path.exists() and path.read_bytes() != encoded:
        # A moved run gets a new display filename rather than overwriting the previous view.
        path = directory / ('index-' + digest(dict(output_location=str(directory)))[:12] + '.html')
    immutable_write(path, encoded)
    return path


def describe_run(directory):
    """Read a verified saved result for clients that cannot open a browser."""
    directory = Path(directory).resolve()
    manifest, report, _ = verify_run(directory)
    entry = definition(manifest['task']['strategy'])
    result = report['result']
    signals = result['signals']
    from .input_workflow import saved_input_outcome
    outcome = saved_input_outcome(report)
    return dict(schema_version='hakimi-offline-result-view-v1',
        strategy=dict(key=manifest['task']['strategy'], title=entry['title'], version=entry['version'], state=manifest['task']['state']),
        symbol=report['dataset']['security']['symbol'], data_kind=report['dataset']['evidence_kind'],
        score_start=report['spec']['score_start_session'], score_end=report['spec']['score_end_session'],
        buy_intents=sum(row['action'] == 'BUY' for row in signals), fill_count=result['fill_count'],
        blocked_new_buys=outcome['blocked_new_buys'], research_input_outcome=outcome,
        reasons=list(dict.fromkeys(row['reason'] for row in signals)),
        total_return=result['total_return'], net_pnl=result['final_equity'] - report['spec']['initial_cash'],
        total_fees=result['total_fees'], realized_pnl=result['realized_pnl'], unrealized_pnl=result['unrealized_pnl'],
        open_position_qty=result['open_position_qty'], limitations=report['limitations'], effective_leverage=1,
        output_directory=str(directory), task_id=manifest['task_id'], report_hash=report['report_hash'])


def replay_run(directory):
    directory = Path(directory).resolve()
    _, report, snapshot = verify_run(directory)
    receipt = replay_task_report(snapshot, EquityResearchReport(report))
    write_new(directory / 'replays' / (receipt['receipt_hash'] + '.json'), receipt)
    if not receipt['replay_verified']:
        raise ValueError('replay_failed_original_result_retained')
    return receipt
