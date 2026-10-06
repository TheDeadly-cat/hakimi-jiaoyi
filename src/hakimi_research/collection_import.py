"""Import complete or legitimately resumed local quotes into a movable bundle.

The raw receipts are private inputs. This module has no provider or account API.
Content identities use relative paths; the source receipt's old paths are never
used as locations and the source receipts are copied byte for byte.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path, PurePosixPath
import tempfile
from zoneinfo import ZoneInfo

from .documents import digest, read_document
from .equity_dataset import load_equity_snapshot, save_equity_snapshot
from .futu_quote_contract import WINDOWS, requests, require, validate_security, validate_actions
from .futu_snapshot_aggregation import build

SCHEMA = 'hakimi-portable-quote-bundle-v1'
PLAN_BYTES = files('hakimi_research').joinpath('resources/nvda-collection-plan.json').read_bytes()
PLAN = json.loads(PLAN_BYTES)
PLAN_SHA = hashlib.sha256(PLAN_BYTES).hexdigest()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path, *, allow_empty=False):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'INPUT_FILE_MISSING_OR_NOT_REGULAR:' + path.name)
    with path.open('rb') as handle:
        raw = handle.read(16 * 1024 * 1024 + 1)
    require((allow_empty or len(raw) > 0) and len(raw) <= 16 * 1024 * 1024, 'INPUT_SIZE_LIMIT:' + path.name)
    return raw


def calendars():
    ny = ZoneInfo('America/New_York')
    result = {}
    for quarter, release, first, last in WINDOWS:
        days = []
        day = date.fromisoformat(first)
        while day <= date.fromisoformat(last):
            opened = day.weekday() < 5 and day.isoformat() != '2023-05-29'
            row = dict(date=day.isoformat(), kind='OPEN' if opened else 'CLOSED')
            if opened:
                for key, time in [('open_utc', '09:30:00'), ('close_utc', '16:00:00')]:
                    row[key] = datetime.fromisoformat(day.isoformat() + 'T' + time).replace(tzinfo=ny).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            days.append(row)
            day += timedelta(days=1)
        result[quarter] = dict(days=days, sessions=[d for d in days if d['kind'] == 'OPEN'])
    return result


def _completion(summary, process, *, resumed):
    require(summary.get('status') == 'QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION'
        and summary.get('business_method_calls') == summary.get('business_protocol_query_calls') == 6
        and summary.get('account_queries') == summary.get('order_calls') == 0
        and summary.get('sdk_version') == '10.7.6708', 'COLLECTION_COMPLETION_NOT_PROVEN')
    require(process.get('returncode') == 0 and process.get('bounds', {}).get('outcome') == 'EXITED'
        and process['bounds'].get('cleanup_confirmed') is True, 'COLLECTION_PROCESS_NOT_CLEANLY_EXITED')
    if resumed:
        require(summary.get('new_business_method_calls') == 4 and summary.get('reused_successful_calls') == 2,
            'CONTINUATION_CALL_SCOPE_CHANGED')
    else:
        require(not summary.get('reused_successful_calls') and not summary.get('prior_identity'),
            'NORMAL_IMPORT_CANNOT_HIDE_CONTINUATION')


def import_collection(*, calendar_original, output_dir, collection=None, first=None, continuation=None, synthetic=False):
    require((collection is not None and first is None and continuation is None)
        or (collection is None and first is not None and continuation is not None), 'SELECT_COMPLETE_COLLECTION_OR_FIRST_AND_CONTINUATION')
    roots = {'collection': Path(collection)} if collection is not None else {'first': Path(first), 'continuation': Path(continuation)}
    raw = {}
    locations = {}
    def retain(role, name):
        key = 'inputs/' + role + '/' + name
        if key not in raw:
            raw[key] = read_bytes(roots[role] / name)
            locations[key] = roots[role] / name
        return json.loads(raw[key])
    calendar_raw = read_bytes(calendar_original)
    calendar_hash = sha(calendar_raw)
    require(synthetic or calendar_hash == PLAN['calendar']['sha256'], 'CALENDAR_ORIGINAL_CHANGED')
    expected_calendars = calendars()
    for role in roots:
        frozen = retain(role, 'frozen-inputs.private.json')
        inputs = frozen['inputs']
        require(inputs['plan'] == PLAN and inputs['calendar_sha256'] == calendar_hash
            and inputs['calendars'] == expected_calendars and frozen['requests'] == requests(), 'COLLECTION_INPUT_CONTRACT_CHANGED')
        require(frozen['source_identity'].get('docs/studies/nvda-event-price-20260930.json') == PLAN_SHA,
            'COLLECTION_PLAN_IDENTITY_CHANGED')
        require(not synthetic or frozen.get('evidence_kind') == 'SYNTHETIC_TEST', 'SYNTHETIC_RECEIPT_LABEL_REQUIRED')
    resumed = first is not None
    completed_role = 'continuation' if resumed else 'collection'
    _completion(retain(completed_role, 'summary.json'), retain(completed_role, 'process.private.json'), resumed=resumed)
    if resumed:
        summary, process = retain('first', 'summary.json'), retain('first', 'process.private.json')
        require(summary.get('status') == 'STOPPED_NO_RETRY' and summary.get('reason') == 'ACTION_SECURITY_IDENTITY_MISMATCH'
            and summary.get('business_method_calls') == summary.get('business_protocol_query_calls') == 2
            and summary.get('account_queries') == summary.get('order_calls') == 0
            and summary.get('windows') == [] and summary.get('sdk_version') == '10.7.6708'
            and process.get('returncode') == 1 and process['bounds'].get('outcome') == 'EXITED'
            and process['bounds'].get('cleanup_confirmed') is True, 'PRIOR_NOT_ELIGIBLE_FOR_UNQUERIED_SUFFIX')
        link = retain('continuation', 'continuation.private.json')
        prior_files = link['prior_files']
        require(set(prior_files) == {p.name for p in roots['first'].iterdir() if p.is_file()}, 'PRIOR_FILE_INVENTORY_CHANGED')
        for name, expected in prior_files.items():
            require(PurePosixPath(name).name == name and '/' not in name and '\\' not in name, 'UNSAFE_PRIOR_FILE_NAME')
            content = read_bytes(roots['first'] / name, allow_empty=True)
            require(sha(content) == expected, 'PRIOR_RECEIPT_CHANGED:' + name)
            raw['inputs/first/' + name] = content
            locations['inputs/first/' + name] = roots['first'] / name
        prior_identity = sha(json.dumps(prior_files, sort_keys=True).encode())
        require(link['prior_identity'] == prior_identity and retain('continuation', 'summary.json')['prior_identity'] == prior_identity,
            'CONTINUATION_BINDING_CHANGED')
    replies = {}
    for index, request in enumerate(requests(), 1):
        role = 'first' if resumed and index <= 2 else completed_role
        prefix = f'{index:02d}-{request["label"]}'
        started = retain(role, prefix + '.started.private.json')
        response = retain(role, prefix + '.response.private.json')
        reply = response['returned_reply']
        require(started['request'] == request and started['attempt'] == 1
            and type(reply['ret']) is int and reply['ret'] == 0 and reply.get('page_req_key') is None, 'REQUEST_OR_SUCCESSFUL_REPLY_CHANGED')
        replies[request['label']] = response
    for role, directory in roots.items():
        expected_indices = range(1, 3) if role == 'first' else range(3, 7) if role == 'continuation' else range(1, 7)
        expected_started = {f'{i:02d}-{requests()[i-1]["label"]}.started.private.json' for i in expected_indices}
        require({p.name for p in directory.glob('*.started.private.json')} == expected_started, 'CALL_INVENTORY_CHANGED')
    validate_security(replies['security']['returned_reply']['rows'])
    validate_actions(replies['actions']['returned_reply']['rows'], [dict(snapshot_start=start, score_end=end) for _, _, start, end in WINDOWS])
    raw['inputs/calendar.original'] = calendar_raw
    locations['inputs/calendar.original'] = Path(calendar_original)
    snapshots = []
    for quarter, _, _, _ in WINDOWS:
        hours = replies[quarter + '-K_60M']
        snapshot, comparison = build(quarter, dict(calendars=expected_calendars, plan=PLAN),
            replies[quarter + '-K_DAY']['returned_reply']['rows'], hours['returned_reply']['rows'],
            raw['inputs/' + ('first' if resumed else 'collection') + '/01-security.response.private.json'],
            raw['inputs/' + ('first' if resumed else 'collection') + '/02-actions.response.private.json'],
            calendar_raw, hours['completed_at'], synthetic=synthetic)
        require(snapshot.document['research_admission']['allowed'] is True, 'CANONICAL_SNAPSHOT_IMPORT_REJECTED')
        snapshots.append((quarter, snapshot, comparison))
    require(all(read_bytes(path, allow_empty=True) == raw[name] for name, path in locations.items()), 'INPUT_CHANGED_DURING_IMPORT')
    # Locations do not enter the bundle identity. All retained bytes do.
    core = dict(schema_version=SCHEMA, import_mode='HISTORICAL_CONTINUATION' if resumed else 'COMPLETE_COLLECTION',
        evidence_kind='SYNTHETIC_TEST' if synthetic else 'IMPORTED_UNVERIFIED',
        inputs_sha256={name: sha(content) for name, content in sorted(raw.items())},
        snapshots=[dict(fiscal_quarter=q, snapshot_id=s.snapshot_id,
            path=f'snapshots/{q}/equity_dataset_{s.snapshot_id}.json', **comparison) for q, s, comparison in snapshots],
        permissions=dict(provider_calls=0, account_queries=0, orders=0, economic_runs=0),
        limitations=['Fixed two-window NVDA importer; generic supported equities use CSV metadata import.',
            'Provider identity and action completeness remain bounded declarations.',
            'Daily/hour volume differences remain unexplained and do not prove liquidity.'])
    bundle_id = digest(core)
    manifest = {**core, 'bundle_id': bundle_id}
    output = Path(output_dir).resolve()
    destination = output / ('quote-bundle-' + bundle_id)
    if destination.exists():
        require(verify_bundle(destination) == manifest, 'EXISTING_BUNDLE_CONFLICT')
        return destination
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.quote-import-', dir=output) as temp:
        stage = Path(temp) / 'bundle'
        stage.mkdir()
        for name, content in raw.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for quarter, snapshot, _ in snapshots:
            saved = save_equity_snapshot(snapshot, stage / 'snapshots' / quarter)
            require(saved.name == Path(next(r['path'] for r in core['snapshots'] if r['fiscal_quarter'] == quarter)).name,
                'SNAPSHOT_FILENAME_CONTRACT_CHANGED')
        (stage / 'bundle.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        verify_bundle(stage)
        # Atomic publication of a fully checked directory, no existing result overwrite.
        stage.rename(destination)
    return destination


def relative_file(root, name):
    part = PurePosixPath(name)
    require(type(name) is str and not part.is_absolute() and not any(p in {'..', '.', ''} for p in part.parts)
        and '\\' not in name and ':' not in name, 'BUNDLE_PATH_INVALID')
    path = root.joinpath(*part.parts)
    require(path.resolve().is_relative_to(root.resolve()) and not any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)),
        'BUNDLE_PATH_ESCAPE')
    return path


def verify_bundle(directory):
    root = Path(directory).resolve()
    manifest = read_document(relative_file(root, 'bundle.json'))
    require(manifest.get('schema_version') == SCHEMA and manifest.get('bundle_id') == digest({k: v for k, v in manifest.items() if k != 'bundle_id'}),
        'BUNDLE_IDENTITY_CHANGED')
    require(manifest['permissions'] == dict(provider_calls=0, account_queries=0, orders=0, economic_runs=0), 'BUNDLE_PERMISSION_CONFLICT')
    for name, expected in manifest['inputs_sha256'].items():
        require(sha(read_bytes(relative_file(root, name), allow_empty=True)) == expected, 'BUNDLE_INPUT_CHANGED:' + name)
    for row in manifest['snapshots']:
        snapshot = load_equity_snapshot(relative_file(root, row['path']))
        require(snapshot.snapshot_id == row['snapshot_id'] and snapshot.document['evidence_kind'] == manifest['evidence_kind'],
            'BUNDLE_SNAPSHOT_IDENTITY_CONFLICT')
    expected_files = {'bundle.json', *manifest['inputs_sha256'], *(r['path'] for r in manifest['snapshots'])}
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == expected_files,
        'BUNDLE_FILE_INVENTORY_CONFLICT')
    return manifest
