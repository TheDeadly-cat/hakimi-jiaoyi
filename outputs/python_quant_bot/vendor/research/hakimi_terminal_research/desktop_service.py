"""JSON views and explicit local actions over the existing offline APIs.

The HTTP host owns authentication, request limits and its serial job queue.
Reads never initialize a workspace or run a strategy. Client IDs address only
inventoried workspace files, never client-supplied filesystem paths.
"""
from __future__ import annotations

import base64
import csv
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from importlib import metadata
import io
import json
from pathlib import Path
import re
import stat
import tempfile
import tomllib
from zoneinfo import ZoneInfo

from . import input_workflow, offline_app, task_manager, trade_cli
from .documents import canonical_bytes, read_document
from .equity_research import PERMISSIONS
from .strategy_registry import strategies, new_task_parameters, required_task_context
from .task_comparison import compare_runs
from .run_presentation import task_presentation
from .strategy_guidance import guidance_for

_MAX_UPLOAD = 16 * 1024 * 1024
_HEADER = ['session_date', 'open', 'high', 'low', 'close', 'volume']
_OPTIONS = {'strategy', 'snapshot_id', 'research_input_id', 'params', 'risk',
            'score_start', 'score_end', 'initial_cash', 'fee_rate', 'slippage_pct'}
_LABELS = dict(fast_window='快均线周期', slow_window='慢均线周期', position_pct='目标仓位比例',
    target_position_pct='基准仓位比例', stop_loss_pct='止损价格距离', take_profit_pct='止盈价格距离',
    max_position_pct='最大仓位比例', max_single_loss_pct='最大止损价格距离',
    max_daily_loss_pct='日亏损阻止新买入阈值', max_leverage='杠杆', min_cash_pct='最低现金比例')


def _fields(payload, allowed, required=()):
    if type(payload) is not dict or set(payload) - set(allowed) or set(required) - set(payload):
        raise ValueError('desktop_action_fields_invalid')
    # Reject non-native and non-finite input before dispatch, including nested values.
    canonical_bytes(payload)


def _upload(value):
    if type(value) is not str or len(value) > ((_MAX_UPLOAD + 2) // 3) * 4:
        raise ValueError('desktop_upload_size_invalid')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('desktop_upload_base64_invalid') from exc
    if not raw or len(raw) > _MAX_UPLOAD:
        raise ValueError('desktop_upload_size_invalid')
    return raw


def _raw_rows(raw):
    try:
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise ValueError('equity_csv_encoding_or_structure_invalid') from exc
    if (not rows or len(rows) < 2 or not rows[0] or any(not column.strip() for column in rows[0])
            or len(rows[0]) != len(set(rows[0]))):
        raise ValueError('desktop_csv_header_missing_or_duplicate')
    if any(len(row) != len(rows[0]) for row in rows[1:]):
        raise ValueError('equity_csv_row_width_invalid')
    return rows


def _proposed_mapping(columns):
    aliases = dict(session_date={'session_date', 'date', '日期', '交易日期'}, open={'open', '开盘', '开盘价'},
        high={'high', '最高', '最高价'}, low={'low', '最低', '最低价'}, close={'close', '收盘', '收盘价'},
        volume={'volume', 'vol', '成交量'})
    result = {}
    for key, choices in aliases.items():
        matches = [name for name in columns if name.strip().casefold() in choices]
        if len(matches) == 1:
            result[key] = matches[0]
    return result


def _normalize_csv(raw, mapping):
    rows = _raw_rows(raw)
    if (type(mapping) is not dict or set(mapping) != set(_HEADER)
            or any(type(value) is not str for value in mapping.values())
            or len(set(mapping.values())) != 6 or not set(mapping.values()) <= set(rows[0])):
        raise ValueError('desktop_csv_six_distinct_column_mappings_required')
    indices = [rows[0].index(mapping[key]) for key in _HEADER]
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(_HEADER)
    writer.writerows([[row[index] for index in indices] for row in rows[1:]])
    return output.getvalue().encode('utf-8')


def _csv_rows(raw):
    rows = _raw_rows(raw)
    if rows[0] != _HEADER:
        raise ValueError('desktop_csv_column_mapping_confirmation_required')
    dates = [date.fromisoformat(row[0]) for row in rows[1:]]
    if dates != sorted(set(dates)) or any(d.isoformat() != row[0] for d, row in zip(dates, rows[1:])):
        raise ValueError('equity_csv_session_missing_extra_duplicate_or_out_of_order')
    if (dates[-1] - dates[0]).days > 3660:
        raise ValueError('equity_calendar_range_invalid')
    return rows[1:], dates


def _preview(raw, column_mapping=None):
    raw_rows = _raw_rows(raw)
    mapping = _proposed_mapping(raw_rows[0]) if column_mapping is None else column_mapping
    if column_mapping is not None:
        _normalize_csv(raw, mapping)
    common = dict(status='CSV_PREVIEW_NOT_ADMITTED', columns=raw_rows[0], required_columns=_HEADER,
        row_count=len(raw_rows) - 1, proposed_mapping=mapping,
        sample_rows=[dict(zip(raw_rows[0], row)) for row in raw_rows[1:6]],
        original_csv_sha256=sha256(raw).hexdigest(), new_economic_runs=0)
    if len(mapping) != 6:
        return dict(common, mapping_complete=False, coverage_start=None, coverage_end=None, session_dates=[],
                    missing_weekdays=[], required_confirmations=['请为日期、开高低收、成交量选择六个不同的列。'])
    normalized = _normalize_csv(raw, mapping)
    rows, dates = _csv_rows(normalized)
    observed = set(dates)
    missing = [dates[0] + timedelta(days=n) for n in range((dates[-1] - dates[0]).days + 1)
               if dates[0] + timedelta(days=n) not in observed and (dates[0] + timedelta(days=n)).weekday() < 5]
    return dict(common, mapping_complete=True,
        coverage_start=dates[0].isoformat(), coverage_end=dates[-1].isoformat(),
        session_dates=[d.isoformat() for d in dates], missing_weekdays=[d.isoformat() for d in missing],
        timezone='America/New_York',
        defaults=dict(exchange='XNAS', lag_seconds=60, identity_stable=False, action_free_confirmed=False,
            calendar_confirmed=False, completed_bars_only=False, raw_unadjusted=False, shares_volume=False),
        required_confirmations=['仅支持美股普通股、美元、未复权日线、成交量单位股。',
            '日期缺口不能自动认定为休市；请逐日确认休市原因，并列出提前收盘日期。',
            '证券身份及公司行为覆盖未确认时保留为阻挡；来源声明不等于外部认证。',
            '常规纽约时间开盘 09:30、收盘 16:00；提前收盘 13:00。请核对所选窗口。'])


def _form_metadata(raw, form, conversion=None):
    required = {'symbol', 'exchange', 'security_id', 'source_name', 'source_reference', 'retrieved_at', 'as_of',
        'lag_seconds', 'identity_stable', 'identity_note', 'action_free_confirmed', 'actions_note',
        'calendar_confirmed', 'calendar_note', 'closed_dates', 'early_close_dates',
        'completed_bars_only', 'raw_unadjusted', 'shares_volume'}
    _fields(form, required, required)
    for key in ('identity_stable', 'action_free_confirmed', 'calendar_confirmed',
                'completed_bars_only', 'raw_unadjusted', 'shares_volume'):
        if type(form[key]) is not bool:
            raise ValueError('desktop_import_confirmation_requires_boolean:' + key)
    if not all(form[key] for key in ('calendar_confirmed', 'completed_bars_only', 'raw_unadjusted', 'shares_volume')):
        raise ValueError('desktop_import_calendar_and_price_declarations_required')
    for key in ('identity_note', 'actions_note', 'calendar_note'):
        if type(form[key]) is not str or not form[key].strip():
            raise ValueError('desktop_import_declaration_note_required:' + key)
    view = _preview(raw)
    closed, early = form['closed_dates'], form['early_close_dates']
    if (type(closed) is not dict or set(closed) != set(view['missing_weekdays'])
            or any(reason not in {'HOLIDAY', 'EXCHANGE_CLOSURE'} for reason in closed.values())):
        raise ValueError('desktop_import_missing_weekdays_require_explicit_closure')
    if (type(early) is not list or any(type(day) is not str for day in early)
            or len(set(early)) != len(early) or not set(early) <= set(view['session_dates'])):
        raise ValueError('desktop_import_early_close_dates_invalid')
    first, last = date.fromisoformat(view['coverage_start']), date.fromisoformat(view['coverage_end'])
    ny = ZoneInfo('America/New_York')
    def utc(day, hour, minute=0):
        return datetime.combine(day, time(hour, minute), ny).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    days = []
    for number in range((last - first).days + 1):
        day = first + timedelta(days=number)
        if day.weekday() >= 5:
            days.append(dict(date=day.isoformat(), kind='CLOSED', reason='WEEKEND'))
        elif day.isoformat() in closed:
            days.append(dict(date=day.isoformat(), kind='CLOSED', reason=closed[day.isoformat()]))
        else:
            short = day.isoformat() in early
            days.append(dict(date=day.isoformat(), kind='OPEN', open_utc=utc(day, 9, 30),
                             close_utc=utc(day, 13 if short else 16), early_close=short))
    declaration = canonical_bytes(dict(kind='USER_LOCAL_IMPORT_DECLARATION_NOT_EXTERNAL_VERIFICATION', form=form,
                                       csv_conversion=conversion))
    declaration_source = dict(name='用户本地导入声明', reference='urn:hakimi:local-declaration:' + sha256(declaration).hexdigest(),
        retrieved_at=form['retrieved_at'], raw_base64=base64.b64encode(declaration).decode('ascii'))
    return dict(schema_version='us-equity-daily-import-v1',
        security=dict(security_id=form['security_id'], symbol=form['symbol'], exchange=form['exchange'],
                      currency='USD', instrument_type='COMMON_STOCK'),
        identity=dict(stable_within_coverage=form['identity_stable'], valid_from=first.isoformat(),
            valid_through=last.isoformat(), selection_basis=form['identity_note'], source=declaration_source),
        calendar=dict(timezone='America/New_York', coverage_start=first.isoformat(), coverage_end=last.isoformat(),
                      source=declaration_source, days=days),
        corporate_actions=dict(coverage_start=first.isoformat(), coverage_end=last.isoformat(),
            coverage_status='DECLARED_COMPLETE' if form['action_free_confirmed'] else 'UNKNOWN',
            source=declaration_source, actions=[]),
        price_source=dict(name=form['source_name'], reference=form['source_reference'], retrieved_at=form['retrieved_at'],
                          raw_base64=base64.b64encode(raw).decode('ascii')),
        price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
        completed_bars_only=True, as_of=form['as_of'], retrieved_at=form['retrieved_at'],
        bar_availability_lag_seconds=form['lag_seconds'], evidence_kind='IMPORTED_UNVERIFIED')


class DesktopService:
    def __init__(self, workspace):
        # Workspace choice belongs to the trusted launcher, not an HTTP payload.
        self.workspace = Path(workspace).expanduser().resolve()

    def _safe(self, path):
        path = Path(path).absolute()
        if not path.is_relative_to(self.workspace):
            raise ValueError('desktop_path_outside_workspace')
        current = self.workspace
        try:
            root_info = current.lstat()
        except FileNotFoundError:
            root_info = None
        if root_info is not None and (stat.S_ISLNK(root_info.st_mode)
                or getattr(root_info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError('desktop_reparse_path_not_supported')
        for part in path.relative_to(self.workspace).parts:
            if part in {'.', '..'}:
                raise ValueError('desktop_path_outside_workspace')
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('desktop_reparse_path_not_supported')
        if not path.resolve().is_relative_to(self.workspace):
            raise ValueError('desktop_path_outside_workspace')
        return path

    def _id(self, path):
        return sha256(self._safe(path).relative_to(self.workspace).as_posix().encode()).hexdigest()[:24]

    def _paths(self, resource):
        root = self._safe(self.workspace / {'tasks': 'tasks', 'inputs': 'data', 'runs': 'runs'}[resource])
        if not root.exists():
            return []
        if resource == 'tasks':
            return task_manager.list_tasks(self.workspace)
        if resource == 'runs':
            return sorted(root.glob('run-*'), key=lambda p: p.name, reverse=True)
        return sorted(root.rglob('*.json'))

    def _lookup(self, resource, identity):
        if type(identity) is not str or re.fullmatch(r'[0-9a-f]{24}', identity) is None:
            raise ValueError('desktop_unknown_' + resource + '_id')
        for path in self._paths(resource):
            try:
                if self._id(path) == identity:
                    return self._safe(path)
            except ValueError:
                continue
        raise ValueError('desktop_unknown_' + resource + '_id')

    def _guard_tree(self, directory):
        self._safe(directory)
        for path in directory.rglob('*'):
            self._safe(path)

    def _guard_task(self, path):
        self._safe(path)
        if path.is_dir():
            self._guard_tree(path)
        selected = task_manager.resolve_managed_task(path, inspect_only=True)
        self._safe(selected)
        document = read_document(selected)
        for key in ('snapshot', 'event_context'):
            reference = document.get(key)
            if reference:
                target = Path(reference)
                # Normalize ordinary .. in managed portable input references only
                # after checking the lexical path's existing prefix for links.
                candidate = selected.parent / target
                resolved = candidate.resolve()
                self._safe(resolved)
                for prefix in [candidate, *candidate.parents]:
                    if prefix == self.workspace or not prefix.is_relative_to(self.workspace):
                        break
                    if prefix.is_symlink() or (prefix.exists() and getattr(prefix.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                        raise ValueError('desktop_reparse_path_not_supported')
        return path

    def _task(self, path):
        view = task_manager.describe_task(self._guard_task(path))
        available = self._inventory('inputs')['items']
        selections = {}
        for key, field in [('snapshot', 'snapshot_id'), ('research', 'research_input_id')]:
            bound = view['inputs'][key]
            selection = next((row['id'] for row in available
                if bound is not None and row['input_id'] == bound['input_id'] and row['kind'] == bound['kind']), None)
            selections[field] = selection
            if bound is not None:
                bound['id'] = selection
                bound['retained_in_task'] = path.is_dir()
        return dict(view, id=self._id(path), name=path.stem if path.is_file() else path.name,
                    title=view.get('title', path.stem), label=view.get('title', path.stem),
                    legacy_task=view.get('legacy_task', False), **selections)

    def _input(self, path):
        view = input_workflow.inspect_input(self._safe(path))
        return dict(view, id=self._id(path), label=view.get('security', {}).get('symbol', path.stem))

    def _run(self, path, detail=False):
        self._guard_tree(path)
        summary = offline_app.describe_run(path)
        identity = self._id(path)
        manifest, report, snapshot = offline_app.verify_run(path)
        presentation = task_presentation(manifest, path)
        try:
            started = datetime.fromisoformat(read_document(path / 'started.json')['started_at'])
            started_at = started.astimezone(timezone.utc).isoformat() if started.tzinfo is not None else None
        except (TypeError, ValueError):
            started_at = None
        summary = dict(summary, **presentation, id=identity, run_id=path.name.removeprefix('run-'), label=summary['strategy']['title'],
                       max_drawdown=report['result']['max_drawdown'], started_at=started_at)
        if not detail:
            return summary
        result = report['result']
        peak = None
        curve = []
        for point in result['equity_curve']:
            peak = point['equity'] if peak is None else max(peak, point['equity'])
            curve.append(dict(point, drawdown=(peak - point['equity']) / peak if peak else 0))
        candles = [dict(time=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5])
                   for row in snapshot.document['candles']]
        return dict(id=identity, summary=summary, configuration=trade_cli.configuration_view(report['spec']),
            equity_curve=curve, candles=candles, fills=result['fills'], signals=result['signals'],
            research_input_outcome=summary['research_input_outcome'], limitations=report['limitations'],
            identities=dict(run_id=manifest['run_id'], task_id=manifest['task_id'], report_hash=report['report_hash']),
            new_economic_runs=0)

    def _inventory(self, resource):
        items, warnings = [], []
        for path in self._paths(resource):
            try:
                view = {'tasks': self._task, 'inputs': self._input, 'runs': self._run}[resource](path)
                items.append(view)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                if resource == 'inputs' and str(exc).startswith('unsupported_input_schema:'):
                    continue
                warnings.append(dict(name=path.name, error=str(exc)))
        if resource == 'runs':
            items.sort(key=lambda row: row['started_at'] or '', reverse=True)
        return dict(items=items, warnings=warnings)

    def read(self, resource, identity=None):
        if resource == 'csv_templates':
            from .csv_templates import list_templates, read_template
            return (list_templates(self.workspace, safe_path=self._safe) if identity is None
                    else read_template(self.workspace, identity, safe_path=self._safe))
        if resource in {'tasks', 'inputs', 'runs'}:
            if identity is None:
                return self._inventory(resource)
            path = self._lookup(resource, identity)
            return self._run(path, detail=True) if resource == 'runs' else {'tasks': self._task, 'inputs': self._input}[resource](path)
        if identity is not None:
            raise ValueError('desktop_unexpected_identity')
        if resource == 'strategies':
            items = []
            for key, entry in strategies().items():
                params, risk = new_task_parameters(entry['engine_strategy']), trade_cli.default_risk(key)
                def field(name, value):
                    result = dict(key=name, label=_LABELS[name], type='integer' if type(value) is int else 'number', minimum=0)
                    if name.endswith('window'):
                        result['minimum'] = 1
                    elif name == 'max_leverage':
                        result.update(minimum=1, maximum=1)
                    else:
                        result['maximum'] = 1
                    return result
                items.append(dict(entry, key=key, params=params, risk=risk, guidance=guidance_for(key),
                    required_context_sessions=required_task_context(key, params),
                    warmup_note='按现有规则校验预热与评分区间；不会自动更改策略参数。',
                    parameter_fields=[field(name, value) for name, value in params.items()],
                    risk_fields=[field(name, value) for name, value in risk.items()]))
            return dict(items=items, warnings=[])
        if resource == 'status':
            groups = {key: self._inventory(key) for key in ('tasks', 'inputs', 'runs')}
            header = self._safe(self.workspace / 'workspace.json')
            initialized = header.is_file()
            if initialized and read_document(header).get('schema_version') != 'hakimi-offline-workspace-v1':
                raise ValueError('desktop_workspace_schema_invalid')
            from .environment import build_runtime_provenance
            provenance = build_runtime_provenance()
            project = Path(__file__).resolve().parents[2] / 'pyproject.toml'
            if Path(__file__).resolve().parent.parent.name == 'src' and project.is_file():
                version = tomllib.loads(project.read_text(encoding='utf-8'))['project']['version']
            else:
                try:
                    version = metadata.version('hakimi-research')
                except metadata.PackageNotFoundError:
                    version = 'UNKNOWN'
            return dict(workspace=str(self.workspace), workspace_name=self.workspace.name, version=version,
                source_status=provenance['source_identity']['status'],
                source_sha256=provenance['source_identity']['content_sha256'],
                initialized=initialized,
                counts={key: len(view['items']) for key, view in groups.items()},
                **{key: view['items'] for key, view in groups.items()},
                warnings=[warning for group in groups.values() for warning in group['warnings']],
                execution_permission=dict(PERMISSIONS))
        raise ValueError('desktop_unknown_resource')

    def _options(self, payload):
        _fields(payload, _OPTIONS)
        options = {key: value for key, value in payload.items() if key not in {'snapshot_id', 'research_input_id'}}
        for client, api, kind in [('snapshot_id', 'snapshot', 'PRICE_SNAPSHOT'),
                                  ('research_input_id', 'event_context', None)]:
            if client in payload:
                identity = payload[client]
                if client == 'research_input_id' and identity is None:
                    options[api] = None
                    continue
                path = self._lookup('inputs', identity)
                view = self._input(path)
                if (kind and view['kind'] != kind) or (not kind and view['kind'] == 'PRICE_SNAPSHOT'):
                    raise ValueError('desktop_input_kind_mismatch')
                options[api] = path
        return options

    def _new_family(self, name):
        if (type(name) is not str or re.fullmatch(r'[\w-]{1,64}', name) is None
                or re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', name, re.IGNORECASE)):
            raise ValueError('desktop_task_name_invalid')
        return self._safe(self.workspace / 'tasks' / name)

    def mutate(self, action, payload):
        if action == 'prepare_teaching_examples':
            _fields(payload, ())
            self._safe(self.workspace)
            from .teaching_examples import prepare_teaching_examples
            return prepare_teaching_examples(self.workspace)
        if action == 'initialize_demo':
            _fields(payload, ())
            self._safe(self.workspace)
            trade_cli.initialize_demo(self.workspace)
            return self.read('status')
        if action == 'preview_csv':
            _fields(payload, {'csv_name', 'csv_base64', 'column_mapping'}, {'csv_base64'})
            return _preview(_upload(payload['csv_base64']), payload.get('column_mapping'))
        if self.workspace.exists():
            header = self._safe(self.workspace / 'workspace.json')
            if not header.is_file() or read_document(header).get('schema_version') != 'hakimi-offline-workspace-v1':
                raise ValueError('desktop_workspace_not_initialized')
            # Never let an existing junction redirect an admitted action's write.
            for directory in ('data', 'tasks', '.task-locks', 'runs'):
                path = self._safe(self.workspace / directory)
                if path.is_dir():
                    self._guard_tree(path)
        if action == 'save_csv_template':
            from .csv_templates import save_template
            return save_template(self.workspace, payload, safe_path=self._safe)
        if action in {'import_csv', 'import_document'}:
            allowed = {'csv_name', 'csv_base64', 'column_mapping', 'metadata_name', 'metadata_base64', 'metadata_form', 'save_template'} if action == 'import_csv' else {'filename', 'document_base64'}
            _fields(payload, allowed, {'csv_base64'} if action == 'import_csv' else {'document_base64'})
            template_request = None
            if 'save_template' in payload:
                from .csv_templates import save_template, validate_template
                form = payload.get('metadata_form')
                if type(form) is not dict or 'metadata_base64' in payload or 'column_mapping' not in payload:
                    raise ValueError('desktop_csv_template_requires_metadata_form_and_mapping')
                template_request = validate_template(payload['save_template'])
                if template_request['column_mapping'] != payload['column_mapping']:
                    raise ValueError('desktop_csv_template_mapping_mismatch')
                for key, value in template_request['fields'].items():
                    if key not in form or type(form[key]) is not type(value) or form[key] != value:
                        raise ValueError('desktop_csv_template_metadata_mismatch:' + key)
            # Temporary upload names are fixed: client filenames are display-only.
            with tempfile.TemporaryDirectory(prefix='hakimi-desktop-upload-') as temporary:
                upload = Path(temporary) / 'upload'
                raw = _upload(payload['csv_base64' if action == 'import_csv' else 'document_base64'])
                if action == 'import_csv':
                    if ('metadata_base64' in payload) == ('metadata_form' in payload):
                        raise ValueError('desktop_import_exactly_one_metadata_source_required')
                    conversion = None
                    if 'column_mapping' in payload:
                        if 'metadata_base64' in payload:
                            raise ValueError('desktop_csv_conversion_requires_explicit_metadata_form')
                        normalized = _normalize_csv(raw, payload['column_mapping'])
                        conversion = dict(schema_version='hakimi-local-csv-column-conversion-v1',
                            original_csv_base64=base64.b64encode(raw).decode('ascii'),
                            original_csv_sha256=sha256(raw).hexdigest(), normalized_csv_sha256=sha256(normalized).hexdigest(),
                            column_mapping=payload['column_mapping'], operation='SELECT_AND_REORDER_COLUMNS_ONLY',
                            price_values_changed=False)
                        raw = normalized
                    # A proposal is never implicit permission to normalize input.
                    _csv_rows(raw)
                    upload.write_bytes(raw)
                    metadata = Path(temporary) / 'metadata.json'
                    metadata.write_bytes(_upload(payload['metadata_base64']) if 'metadata_base64' in payload
                                         else canonical_bytes(_form_metadata(raw, payload['metadata_form'], conversion)))
                    view = input_workflow.import_price_csv(upload, metadata, self.workspace)
                    if conversion is not None:
                        record = {key: value for key, value in conversion.items() if key != 'original_csv_base64'}
                        directory = self._safe(self.workspace / 'data/csv-imports' / conversion['original_csv_sha256']
                                               / sha256(canonical_bytes(record)).hexdigest())
                        originals = dict(original=directory / 'original.csv', normalized=directory / 'normalized.csv',
                                         conversion=directory / 'conversion.json')
                        for name, content in [('original', base64.b64decode(conversion['original_csv_base64'], validate=True)),
                                              ('normalized', raw), ('conversion', canonical_bytes(record))]:
                            offline_app.immutable_write(self._safe(originals[name]), content)
                        view = dict(view, csv_conversion=dict(record, retained_files={key: str(path) for key, path in originals.items()}))
                else:
                    upload.write_bytes(raw)
                    view = input_workflow.import_input(upload, self.workspace)
            result = dict(view, id=self._id(Path(view['path'])), label=view.get('security', {}).get('symbol', '研究输入'))
            if template_request is not None:
                # The durable import job owns this follow-up, independently of
                # the originating browser dialog. Never replay an uncertain save.
                try:
                    saved = save_template(self.workspace, template_request, safe_path=self._safe)
                    result['template_save'] = dict(status='SAVED', template=saved)
                except Exception as exc:
                    result['template_save'] = dict(status='UNKNOWN', automatic_retry=False,
                        message='行情已封存；模板保存结果尚未确认，请核对模板与操作记录，不要重复提交。' + str(exc))
            return result
        if action == 'create_task':
            _fields(payload, _OPTIONS | {'name', 'title'}, {'name', 'strategy', 'snapshot_id'})
            path = self._new_family(payload['name'])
            options = self._options({key: value for key, value in payload.items() if key in _OPTIONS})
            task_manager.create_family(path, title=payload.get('title'), **options)
            return self._task(path)
        if action == 'copy_task':
            _fields(payload, {'task_id', 'name', 'title'}, {'task_id', 'name'})
            source = self._guard_task(self._lookup('tasks', payload['task_id']))
            path = self._new_family(payload['name'])
            task_manager.create_family(path, title=payload.get('title'), **task_manager.version_options(source))
            return self._task(path)
        if action in {'revise_task', 'set_task_state', 'run_task', 'check_task'}:
            key = 'changes' if action == 'revise_task' else 'state' if action == 'set_task_state' else None
            required = {'task_id'} | ({key} if key else set())
            _fields(payload, required, required)
            path = self._guard_task(self._lookup('tasks', payload['task_id']))
            if action in {'revise_task', 'set_task_state'} and not path.is_dir():
                raise ValueError('desktop_legacy_task_copy_before_edit')
            if action == 'revise_task':
                task_manager.revise_family(path, **self._options(payload['changes']))
            elif action == 'set_task_state':
                task_manager.change_state(path, payload['state'])
            elif action == 'check_task':
                view = self._task(path)
                return dict(view, status='INPUTS_APPLICABLE_NO_SIMULATION', new_economic_runs=0,
                            can_run=view['state'] == 'ENABLED')
            else:
                output = self._safe(self.workspace / 'runs')
                directory = offline_app.run_task(path, output_dir=output)
                result = self._run(directory, detail=True)
                # Existing run_task may compute or reuse a verified saved run.
                # Only reads/comparisons claim zero new economic calculations.
                result.pop('new_economic_runs')
                return dict(result, operation='RUN_REQUEST_COMPLETED')
            return self._task(path)
        if action == 'compare':
            _fields(payload, {'run_ids'}, {'run_ids'})
            if type(payload['run_ids']) is not list:
                raise ValueError('desktop_compare_run_ids_required')
            paths = [self._lookup('runs', identity) for identity in payload['run_ids']]
            for path in paths:
                self._guard_tree(path)
            return compare_runs(paths)
        raise ValueError('desktop_unknown_action')
