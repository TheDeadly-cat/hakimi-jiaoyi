"""Immutable, non-economic CSV form templates; never an input admission receipt."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from .documents import digest, read_document
from .offline_app import write_new

SCHEMA = 'hakimi-csv-import-template-v1'
DIRECTORY = 'import-templates'
COLUMNS = frozenset({'session_date', 'open', 'high', 'low', 'close', 'volume'})
REUSABLE_FIELDS = frozenset({'symbol', 'exchange', 'security_id', 'source_name', 'source_reference', 'lag_seconds'})
_BODY_FIELDS = frozenset({'schema_version', 'name', 'column_mapping', 'fields'})
_ID = re.compile(r'[0-9a-f]{64}')


def _text(value, label, maximum=2048, *, exact_edges=True):
    if (type(value) is not str or not value.strip() or len(value) > maximum
            or (exact_edges and value != value.strip()) or any(ord(character) < 32 for character in value)):
        raise ValueError('csv_template_text_invalid:' + label)


def _body(payload):
    if type(payload) is not dict or set(payload) != {'name', 'column_mapping', 'fields'}:
        raise ValueError('csv_template_fields_invalid')
    _text(payload['name'], 'name', 80)
    mapping, fields = payload['column_mapping'], payload['fields']
    if type(mapping) is not dict or set(mapping) != COLUMNS:
        raise ValueError('csv_template_column_mapping_fields_invalid')
    for key, value in mapping.items():
        _text(value, key, 180, exact_edges=False)
    if len(set(mapping.values())) != len(COLUMNS):
        raise ValueError('csv_template_column_mapping_must_be_distinct')
    if type(fields) is not dict or set(fields) - REUSABLE_FIELDS:
        raise ValueError('csv_template_nonreusable_fields_forbidden')
    for key, value in fields.items():
        if key == 'lag_seconds':
            if type(value) is not int or not 1 <= value <= 7 * 86400:
                raise ValueError('csv_template_lag_seconds_invalid')
        else:
            _text(value, key, 180 if key in {'symbol', 'exchange', 'security_id'} else 2048)
    if 'symbol' in fields and re.fullmatch(r'[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?', fields['symbol']) is None:
        raise ValueError('csv_template_symbol_invalid')
    if 'exchange' in fields and fields['exchange'] not in {'XNAS', 'XNYS'}:
        raise ValueError('csv_template_exchange_invalid')
    if 'source_reference' in fields and not fields['source_reference'].startswith(('https://', 'urn:')):
        raise ValueError('csv_template_source_reference_invalid')
    # New detached dictionaries: callers cannot mutate a retained template view.
    return dict(schema_version=SCHEMA, name=payload['name'], column_mapping=dict(mapping), fields=dict(fields))


def validate_template(payload):
    """Validate and detach a save request without reading or writing anything."""
    body = _body(payload)
    return {key: body[key] for key in ('name', 'column_mapping', 'fields')}


def _verified(record, identity):
    if (type(record) is not dict or set(record) != _BODY_FIELDS | {'id', 'created_at'}
            or record.get('schema_version') != SCHEMA or record.get('id') != identity):
        raise ValueError('csv_template_record_invalid')
    body = _body({key: record[key] for key in ('name', 'column_mapping', 'fields')})
    if digest(body) != identity:
        raise ValueError('csv_template_identity_mismatch')
    timestamp = record['created_at']
    if type(timestamp) is not str:
        raise ValueError('csv_template_created_at_invalid')
    try:
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('csv_template_created_at_invalid') from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError('csv_template_created_at_invalid')
    return dict(body, id=identity, created_at=timestamp)


def _view(record):
    return dict(record, status='FORM_VALUES_ONLY', admission_status='NOT_EVALUATED',
        new_economic_runs=0,
        note='仅填入可复用资料。请重新检查当前 CSV；本次时间、交易日历和全部核对声明需重新填写。')


def _folder(workspace, safe_path):
    return safe_path(Path(workspace) / DIRECTORY)


def read_template(workspace, identity, *, safe_path):
    if type(identity) is not str or _ID.fullmatch(identity) is None:
        raise ValueError('csv_template_id_invalid')
    path = safe_path(_folder(workspace, safe_path) / (identity + '.json'))
    return _view(_verified(read_document(path), identity))


def list_templates(workspace, *, safe_path):
    directory = _folder(workspace, safe_path)
    if not directory.exists():
        return dict(items=[], warnings=[])
    if not directory.is_dir():
        raise ValueError('csv_template_directory_invalid')
    items, warnings = [], []
    for path in sorted(directory.glob('*.json')):
        try:
            items.append(read_template(workspace, path.stem, safe_path=safe_path))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            warnings.append(dict(name=path.name, error=str(exc)))
    items.sort(key=lambda row: (row['created_at'], row['id']), reverse=True)
    return dict(items=items, warnings=warnings)


def save_template(workspace, payload, *, safe_path):
    body = _body(payload)
    identity = digest(body)
    header = safe_path(Path(workspace) / 'workspace.json')
    if not header.is_file() or read_document(header).get('schema_version') != 'hakimi-offline-workspace-v1':
        raise ValueError('csv_template_workspace_not_initialized')
    path = safe_path(_folder(workspace, safe_path) / (identity + '.json'))
    if path.exists():
        return read_template(workspace, identity, safe_path=safe_path)
    record = dict(body, id=identity, created_at=datetime.now(timezone.utc).isoformat())
    try:
        write_new(path, record)
    except FileExistsError:
        return read_template(workspace, identity, safe_path=safe_path)
    except ValueError as exc:
        # Another same-content save may have published first. Its original
        # creation time wins; validate it rather than replacing either record.
        if not str(exc).startswith('existing_output_conflict:'):
            raise
        return read_template(workspace, identity, safe_path=safe_path)
    return _view(record)
