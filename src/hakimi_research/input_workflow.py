"""One offline input workflow over existing snapshot and research contracts."""
from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path

from .content_tasks import CONTEXT_SCHEMA, build_content_context, verify_content_context, _versions
from .documents import parse_document
from .equity_dataset import SCHEMA as SNAPSHOT_SCHEMA, build_equity_snapshot, verify_equity_snapshot
from .equity_event_context import SCHEMA_VERSION as SCHEDULE_SCHEMA, build_event_context, verify_event_context
from .offline_app import immutable_write

_MAX = 64 * 1024 * 1024


def read_input(path):
    path = Path(path).resolve()
    if not path.is_file() or path.stat().st_size > _MAX:
        raise ValueError('input_file_missing_or_too_large:' + str(path))
    return path.read_bytes()


def _document(raw):
    return parse_document(raw)


def verify_research_context(document):
    if document.get('schema_version') == CONTEXT_SCHEMA:
        return verify_content_context(document)
    return verify_event_context(document)


def snapshot_view(document):
    data = verify_equity_snapshot(document)
    source = data['price_source']
    return dict(kind='PRICE_SNAPSHOT', input_id=data['snapshot_id'], security=data['security'],
        coverage_start=data['sessions'][0]['date'], coverage_end=data['sessions'][-1]['date'],
        sessions=len(data['sessions']), price_basis=data['price_basis'], volume_unit=data['volume_unit'],
        timezone=data['timezone'], as_of=data['as_of'], retrieved_at=data['retrieved_at'],
        bar_availability_lag_seconds=data['bar_availability_lag_seconds'], availability_policy=data['availability_policy'],
        source={k: source[k] for k in ('name', 'reference', 'retrieved_at', 'raw_sha256')},
        security_identity_status=data['security_identity']['stable_within_coverage'],
        calendar_coverage=data['quality']['calendar_coverage'], corporate_actions=data['research_admission']['scope'],
        source_authentication=data['source_authentication'], evidence_kind=data['evidence_kind'],
        status='READY' if data['research_admission']['allowed'] else 'BLOCKED',
        reasons=list(data['research_admission']['block_reasons']))


def context_view(document):
    context = verify_research_context(document)
    content = context['schema_version'] == CONTEXT_SCHEMA
    if content:
        events, bindings, approved = _versions(context)
    else:
        events, bindings, approved = context['events'], {}, set()
    rows = []
    for event in events:
        row = dict(event_id=event['event_id'], version=event['version'], event_hash=event['event_hash'],
            source_url=event['source']['url'], source_kind=event['source']['kind'],
            content_sha256=event['raw']['content_sha256'], first_public_at=event['first_public_at'],
            version_public_at=event['version_public_at'], retrieved_at=event['retrieved_at'],
            availability=dict(event['availability']))
        if content:
            candidate = bindings[event['event_hash']]
            row.update(candidate_hash=candidate['candidate_hash'], original_sha256=candidate['raw_sha256'],
                original_retained=candidate['raw_sha256'] in context['source_bytes']['originals'],
                field_review='APPROVED' if candidate['candidate_hash'] in approved else 'NOT_APPROVED',
                fields=[dict(name=f['name'], status=f['status'], reason=f['reason']) for f in event['facts']])
        else:
            from .equity_event_context import schedule_view
            row['schedule'] = schedule_view(event)
        rows.append(row)
    reasons = ['content_original_source_missing'] if content and any(not r['original_retained'] for r in rows) else []
    return dict(kind='CONTENT_CONTEXT' if content else 'SCHEDULE_CONTEXT', input_id=context['context_hash'],
        security_id=context['security_id'], status='BLOCKED' if reasons else 'READY', reasons=reasons, versions=rows,
        approval_status=('IMPORTED_FIELD_RECEIPT' if approved else 'NOT_APPROVED') if content else 'NOT_APPLICABLE_TO_SCHEDULE',
        authority='INPUT_IDENTITY_ONLY_NOT_PUBLISHER_AUTHENTICATION_OR_EXECUTION_AUTHORITY')


def inspect_input(path):
    raw = read_input(path)
    value = _document(raw)
    if value.get('schema_version') == SNAPSHOT_SCHEMA:
        view = snapshot_view(value)
    elif value.get('schema_version') in {SCHEDULE_SCHEMA, CONTEXT_SCHEMA}:
        view = context_view(value)
    else:
        raise ValueError('unsupported_input_schema:' + str(value.get('schema_version')))
    return dict(view, path=str(Path(path).resolve()), file_sha256=sha256(raw).hexdigest())


def list_inputs(workspace):
    directory = Path(workspace).resolve() / 'data'
    items = []
    for path in sorted(directory.rglob('*.json')) if directory.is_dir() else []:
        try:
            value = _document(read_input(path))
            if value.get('schema_version') not in {SNAPSHOT_SCHEMA, SCHEDULE_SCHEMA, CONTEXT_SCHEMA}:
                continue  # Source manifests remain in the established source workflow.
            items.append(inspect_input(path))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            items.append(dict(kind='INVALID_INPUT', status='STOPPED', path=str(path), reasons=[str(exc)]))
    return dict(status='OFFLINE_INPUT_INVENTORY', items=items, registry='EXISTING_WORKSPACE_FILES_NO_SECOND_DATA_REGISTRY', new_economic_runs=0)


def _retain(workspace, raw):
    value = _document(raw)
    if value.get('schema_version') == SNAPSHOT_SCHEMA:
        view = snapshot_view(value)
        kind = 'snapshots'
    else:
        view = context_view(value)
        kind = 'research'
    path = Path(workspace).resolve() / 'data' / kind / view['input_id'] / (sha256(raw).hexdigest() + '.json')
    immutable_write(path, raw)
    retained = inspect_input(path)
    return dict(retained, status='OFFLINE_INPUT_RETAINED', admission_status=retained['status'], original_bytes_retained=True)


def import_input(path, workspace):
    return _retain(workspace, read_input(path))


def import_price_csv(csv, metadata, workspace):
    snapshot = build_equity_snapshot(read_input(csv), read_input(metadata))
    encoded = (json.dumps(snapshot.document, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    return _retain(workspace, encoded)


def import_schedule_events(paths, workspace):
    events = [_document(read_input(p)) for p in paths]
    securities = {e['security_id'] for e in events}
    if len(securities) != 1:
        raise ValueError('event_context_requires_one_security')
    context = build_event_context(events, next(iter(securities)))
    return _retain(workspace, (json.dumps(context, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _matching_sources(directory, wanted, suffixes):
    found = {}
    if directory is None:
        return found
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError('content_source_directory_missing')
    candidates = [p for p in sorted(directory.iterdir()) if p.is_file() and p.suffix.lower() in suffixes]
    if len(candidates) > 128:
        raise ValueError('content_source_directory_file_limit')
    for path in candidates:
        raw = read_input(path)
        key = sha256(raw).hexdigest()
        if key in wanted:
            found[key] = raw
    return found


def import_content_packet(packet, workspace, *, event_id, texts_dir, originals_dir=None, approval=None, synthetic=False):
    packet_raw = read_input(packet)
    from .content_tasks import _packet
    value = _packet(packet_raw)
    selected = [r for r in value.get('events', []) if r.get('event_id') == event_id]
    texts = _matching_sources(texts_dir, {r['plain_text_sha256'] for r in selected}, {'.txt'})
    originals = _matching_sources(originals_dir, {r['raw_sha256'] for r in selected}, {'.txt', '.html', '.htm'})
    context = build_content_context(packet_raw, event_id=event_id, texts=texts, originals=originals,
        approval_raw=read_input(approval) if approval is not None else None, synthetic=synthetic)
    return _retain(workspace, (json.dumps(context, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def check_inputs(options, *, location):
    """Use ordinary task admission without creating a task or running an engine."""
    from .trade_cli import build_task_document, configuration_view
    from .strategy_registry import definition
    task = build_task_document(location, **options)
    snapshot = inspect_input(options['snapshot'])
    context = inspect_input(options['event_context']) if options.get('event_context') is not None else None
    return dict(status='INPUTS_APPLICABLE_NO_SIMULATION', strategy=options['strategy'], snapshot=snapshot,
        research=context, event_rule=definition(options['strategy'])['event_rule'],
        configuration=configuration_view(task['experiment']), new_economic_runs=0,
        note='历史窗口按保存的评分区间检查；不按今天日期把历史行情误判为实时过期数据。')


def bind_inputs(family, **changes):
    from .task_manager import revise_family, version_options, describe_task
    if not changes or set(changes) - {'snapshot', 'event_context'}:
        raise ValueError('task_bind_requires_explicit_input_changes')
    options = dict(version_options(family), **changes)
    check_inputs(options, location=Path(family) / '.input-preview/task.json')
    revise_family(family, **changes)
    return dict(status='INPUTS_BOUND_TO_NEW_TASK_VERSION', **describe_task(family))


def bound_input_view(checked):
    return dict(snapshot=inspect_input(checked['snapshot_path']),
        research=inspect_input(checked['context_path']) if checked['context_path'] is not None else None,
        event_rule=checked['definition']['event_rule'], input_change_policy='NEW_IMMUTABLE_TASK_VERSION_OLD_RUNS_KEEP_FROZEN_INPUTS')


def saved_input_outcome(report):
    if report.get('schema_version') == 'us-equity-content-task-report-v1':
        rows = report['input_reviews']
        scored = {s['date'] for s in report['dataset']['sessions']
            if report['spec']['score_start_session'] <= s['date'] <= report['spec']['score_end_session']}
        included = [r for r in rows if r['price_execution_at'] is not None and r['price_execution_at'][:10] in scored]
        blocked = sum(r['disposition'] == 'BLOCK_NEW_BUY' for r in included)
        visible = [dict(r, in_score_window=r['price_execution_at'] is not None and r['price_execution_at'][:10] in scored,
            applicability='PRICE_OPPORTUNITY_OUTSIDE_SCORE_WINDOW' if r['price_execution_at'] is not None
                and r['price_execution_at'][:10] not in scored else 'IN_SCORE_WINDOW' if r['price_execution_at'] is not None else 'NO_PRICE_BUY') for r in rows]
        return dict(status='CONTENT_FILTER_CHANGED_PRICE_INTENT' if blocked else 'NO_CONTENT_INTERVENTION',
            rule=report['spec']['event_rule'], blocked_new_buys=blocked, reviews=visible,
            explanation='价格确认、内容拒绝及其可用版本分开显示；没有干预不表示内容证明策略有效。')
    if report.get('event_context') is None:
        return dict(status='NOT_APPLICABLE', rule=None, blocked_new_buys=0, reviews=[],
            explanation='价格策略没有绑定或使用研究输入。')
    reviews = [r.get('event_filter', {}) for r in report['result']['signals']]
    blocked = sum(any(v.get('disposition') == 'BLOCK_NEW_BUY' for v in r.values()) for r in reviews)
    return dict(status='SCHEDULE_FILTER_CHANGED_PRICE_INTENT' if blocked else 'NO_SCHEDULE_INTERVENTION',
        rule=report['spec']['event_rule'], blocked_new_buys=blocked, reviews=reviews,
        explanation='排期规则只取消新 BUY；未知或尚不可用版本不会被当作已知公告内容。')


def print_input(view):
    if view['kind'] == 'PRICE_SNAPSHOT':
        print(f"行情 {view['security']['symbol']} / {view['security']['security_id']}；{view['coverage_start']} 至 {view['coverage_end']}；{view['sessions']} 个完整交易日；{view['status']}")
        print('  来源 '+view['source']['name']+'；价格口径 '+view['price_basis']+'；内容 '+view['input_id'])
    elif view['kind'] in {'SCHEDULE_CONTEXT', 'CONTENT_CONTEXT'}:
        print('研究 '+view['security_id']+'；'+view['kind']+'；内容 '+view['input_id'])
        for row in view['versions']:
            available = row['availability']
            print(f"  {row['event_id']} v{row['version']}；可用 {available['available_at']} / {available['available_at_kind']}；来源 {row['source_url']}")
            if 'field_review' in row:
                print('  字段核准 '+row['field_review']+'；原件 '+('已保留' if row['original_retained'] else '缺失'))
    else:
        print('输入不可用：'+view.get('path', ''))
    for reason in view.get('reasons', []):
        print('  停止原因：'+reason)
    if 'file_sha256' in view:
        print('  文件身份 '+view['file_sha256']+'；位置 '+view['path'])
