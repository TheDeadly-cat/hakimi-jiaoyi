"""Append-only task versions and state, separate from frozen economic runs."""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import re
from uuid import uuid4

from .documents import digest, read_document
from .offline_app import _file_lock, write_new, immutable_write, portable_location
from .strategy_registry import reconfigure_task_options

FAMILY_SCHEMA = 'hakimi-task-family-v1'
TASK_SCHEMA = 'hakimi-offline-task-v2'
_VERSION = re.compile(r'r[0-9]{4}-[0-9a-f]{32}')


def _seal(value, key):
    return {**value, key: digest(value)}


def _verified(value, fields, key):
    if type(value) is not dict or set(value) != set(fields) | {key}:
        raise ValueError('managed_task_record_fields_invalid')
    body = {k: v for k, v in value.items() if k != key}
    if value[key] != digest(body):
        raise ValueError('managed_task_record_identity_conflict')
    return value


def _family_for_task(path):
    path = Path(path).resolve()
    if path.is_dir():
        return path
    task = read_document(path)
    if task.get('schema_version') != TASK_SCHEMA:
        return None
    if path.name != 'task.json' or not _VERSION.fullmatch(path.parent.name) or path.parent.parent.name != 'versions':
        raise ValueError('managed_task_location_invalid')
    return path.parent.parent.parent


@contextmanager
def family_lock(family):
    family = Path(family).resolve()
    locks = family.parent / '.task-locks'
    locks.mkdir(parents=True, exist_ok=True)
    with _file_lock(locks / (family.name + '.lock')):
        yield


def _version(family, name, family_id):
    if type(name) is not str or not _VERSION.fullmatch(name):
        raise ValueError('task_version_name_invalid')
    folder = family / 'versions' / name
    if folder.is_symlink():
        raise ValueError('task_version_must_be_regular')
    seal = _verified(read_document(folder / 'version.json'),
        {'schema_version', 'family_id', 'revision', 'number', 'parent_revision', 'files'}, 'version_hash')
    if seal['schema_version'] != 'hakimi-task-version-v1' or seal['family_id'] != family_id or seal['revision'] != name:
        raise ValueError('task_version_identity_conflict')
    if type(seal['number']) is not int or seal['number'] < 1 or type(seal['files']) is not dict:
        raise ValueError('task_version_fields_invalid')
    if set(seal['files']) not in ({'task.json', 'inputs/snapshot.json'}, {'task.json', 'inputs/snapshot.json', 'inputs/event-context.json'}):
        raise ValueError('task_version_input_inventory_invalid')
    for relative, expected in seal['files'].items():
        path = folder / relative
        if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('task_version_input_missing_or_changed:' + relative)
    task = read_document(folder / 'task.json')
    if task.get('management') != {'family_id': family_id, 'revision': name} or task.get('state') != 'ENABLED':
        raise ValueError('task_version_management_conflict')
    if task.get('snapshot') != 'inputs/snapshot.json' or task.get('event_context') != ('inputs/event-context.json' if 'inputs/event-context.json' in seal['files'] else None):
        raise ValueError('task_version_input_path_conflict')
    return seal


def read_family(family):
    family = Path(family).resolve()
    header = _verified(read_document(family / 'family.json'), {'schema_version', 'family_id', 'title'}, 'family_hash')
    if header['schema_version'] != FAMILY_SCHEMA:
        raise ValueError('task_family_schema_invalid')
    records = sorted((family / 'journal').glob('*.json'))
    if not records:
        raise ValueError('task_family_has_no_committed_state')
    previous, revisions, state, selected = None, [], None, None
    for sequence, path in enumerate(records, 1):
        if path.name != f'{sequence:06d}.json' or path.is_symlink():
            raise ValueError('task_journal_gap_or_invalid_name')
        event = _verified(read_document(path), {'schema_version', 'family_id', 'sequence', 'previous_hash',
            'action', 'revision', 'version_hash', 'state'}, 'event_hash')
        if (event['schema_version'] != 'hakimi-task-event-v1' or event['family_id'] != header['family_id']
                or type(event['sequence']) is not int or event['sequence'] != sequence or event['previous_hash'] != previous):
            raise ValueError('task_journal_chain_conflict')
        seal = _version(family, event['revision'], header['family_id'])
        if event['version_hash'] != seal['version_hash'] or event['state'] not in {'ENABLED', 'PAUSED'}:
            raise ValueError('task_state_version_binding_invalid')
        action = event['action']
        if action in {'CREATE', 'REVISE'}:
            if ((sequence == 1) != (action == 'CREATE') or event['revision'] in revisions
                    or seal['number'] != len(revisions) + 1 or seal['parent_revision'] != selected
                    or (sequence > 1 and event['state'] != state)):
                raise ValueError('task_revision_history_conflict')
            revisions.append(event['revision'])
        elif action == 'SELECT':
            if event['revision'] not in revisions or event['state'] != state:
                raise ValueError('task_selection_history_conflict')
        elif action == 'STATE':
            if event['revision'] != selected:
                raise ValueError('task_state_cannot_change_configuration')
        else:
            raise ValueError('task_history_action_invalid')
        previous, selected, state = event['event_hash'], event['revision'], event['state']
    orphans = sorted(p.name for p in (family / 'versions').iterdir() if p.is_dir() and p.name not in revisions)
    return dict(family=str(family), family_id=header['family_id'], title=header['title'], state=state,
        selected_revision=selected, revisions=revisions, sequence=len(records), event_hash=previous,
        uncommitted_versions_retained=orphans)


def resolve_managed_task(path, *, inspect_only=False):
    family = _family_for_task(path)
    if family is None:
        return Path(path).resolve()
    view = read_family(family)
    selected = family / 'versions' / view['selected_revision'] / 'task.json'
    requested = selected if Path(path).is_dir() else Path(path).resolve()
    if requested.parent.name not in view['revisions']:
        raise ValueError('task_version_not_committed')
    if not inspect_only:
        if view['state'] != 'ENABLED':
            raise ValueError('task_paused:enable_task_family_before_running')
        if requested != selected:
            raise ValueError('historical_task_not_selected:select_configuration_before_running')
    return requested


@contextmanager
def execution_guard(path):
    """Keep pause/select/revise serialized with the complete run admission."""
    family = _family_for_task(path)
    if family is None:
        yield Path(path)
    else:
        with family_lock(family):
            yield resolve_managed_task(path)


def _commit(family, view, action, revision, state):
    seal = _version(family, revision, view['family_id'])
    event = _seal(dict(schema_version='hakimi-task-event-v1', family_id=view['family_id'],
        sequence=view['sequence'] + 1, previous_hash=view['event_hash'], action=action,
        revision=revision, version_hash=seal['version_hash'], state=state), 'event_hash')
    write_new(family / 'journal' / f"{event['sequence']:06d}.json", event)


def _prepare_version(family, workspace, family_id, number, parent_revision, options):
    from .trade_cli import build_task_document
    from .offline_app import check_task
    name = f'r{number:04d}-' + uuid4().hex
    if number > 9999:
        raise ValueError('task_version_limit_reached')
    destination = family / 'versions' / name
    stage = family / 'versions' / ('.preparing-' + name)
    stage.mkdir(parents=True, exist_ok=False)
    # Validate requested inputs/configuration before any version is committed.
    options = dict(options)
    snapshot = Path(options.pop('snapshot')).resolve()
    context = options.pop('event_context', None)
    output = options.pop('output_dir', None)
    if output is not None and Path(output).resolve() != (workspace / 'runs').resolve():
        raise ValueError('managed_task_output_is_workspace_runs:legacy_run_supports_explicit_external_output')
    task = build_task_document(stage / 'task.json', snapshot=snapshot, event_context=context, **options)
    immutable_write(stage / 'inputs/snapshot.json', snapshot.read_bytes())
    if context is not None:
        immutable_write(stage / 'inputs/event-context.json', Path(context).read_bytes())
    task.update(snapshot='inputs/snapshot.json', event_context='inputs/event-context.json' if context is not None else None,
        output_dir=portable_location(workspace / 'runs', destination, relative_root=workspace))
    # Check the copies with the established v1 validator before adding management.
    write_new(stage / 'task.json', task)
    check_task(stage / 'task.json')
    # This generated validation file is unpublished; successful versions expose
    # only the management-bound task, never an executable legacy duplicate.
    (stage / 'task.json').unlink()
    task.update(schema_version=TASK_SCHEMA, management={'family_id': family_id, 'revision': name})
    write_new(stage / 'task.json', task)
    names = ['task.json', 'inputs/snapshot.json'] + (['inputs/event-context.json'] if context is not None else [])
    seal = _seal(dict(schema_version='hakimi-task-version-v1', family_id=family_id, revision=name,
        number=number, parent_revision=parent_revision,
        files={n: sha256((stage / n).read_bytes()).hexdigest() for n in names}), 'version_hash')
    write_new(stage / 'version.json', seal)
    stage.rename(destination)
    return name


def create_family(family, *, title=None, **options):
    family = Path(family).resolve()
    if not re.fullmatch(r'[\w-]{1,64}', family.name) or family.parent.name != 'tasks':
        raise ValueError('managed_task_must_be_named_directory_under_workspace_tasks')
    if title is not None and (type(title) is not str or not title.strip()):
        raise ValueError('task_title_required')
    workspace = family.parent.parent
    with family_lock(family):
        if family.exists():
            raise ValueError('task_family_exists:revise_or_copy_instead')
        stage = family.parent / ('.creating-' + family.name + '-' + uuid4().hex)
        stage.mkdir()
        header = _seal(dict(schema_version=FAMILY_SCHEMA, family_id=uuid4().hex, title=title or family.name), 'family_hash')
        write_new(stage / 'family.json', header)
        revision = _prepare_version(stage, workspace, header['family_id'], 1, None, options)
        _commit(stage, dict(family_id=header['family_id'], sequence=0, event_hash=None), 'CREATE', revision, 'ENABLED')
        read_family(stage)
        stage.rename(family)
    return read_family(family)


def version_options(path):
    from .offline_app import check_task
    selected = resolve_managed_task(path, inspect_only=True)
    context = check_task(selected, inspect_only=True)
    spec = context['semantics']['experiment']
    return dict(strategy=context['semantics']['strategy'], snapshot=context['snapshot_path'],
        event_context=context['context_path'], params=spec['strategy']['params'],
        score_start=spec['score_start_session'], score_end=spec['score_end_session'],
        initial_cash=spec['initial_cash'], fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'], risk=spec['risk'])


def revise_family(family, **changes):
    family = Path(family).resolve()
    with family_lock(family):
        view = read_family(family)
        options = version_options(family)
        if set(changes) - set(options):
            raise ValueError('unsupported_task_change:' + ','.join(sorted(set(changes) - set(options))))
        options = reconfigure_task_options(options, changes)
        revision = _prepare_version(family, family.parent.parent, view['family_id'], len(view['revisions']) + 1,
            view['selected_revision'], options)
        _commit(family, view, 'REVISE', revision, view['state'])
    return read_family(family)


def change_state(family, state):
    if state not in {'ENABLED', 'PAUSED'}:
        raise ValueError('task_state_invalid')
    family = Path(family).resolve()
    with family_lock(family):
        view = read_family(family)
        if state != view['state']:
            _commit(family, view, 'STATE', view['selected_revision'], state)
    return read_family(family)


def select_version(family, number):
    family = Path(family).resolve()
    with family_lock(family):
        view = read_family(family)
        if type(number) is not int or not 1 <= number <= len(view['revisions']):
            raise ValueError('task_version_number_out_of_range')
        _commit(family, view, 'SELECT', view['revisions'][number - 1], view['state'])
    return read_family(family)


def list_tasks(workspace):
    directory = Path(workspace) / 'tasks'
    if not directory.is_dir():
        return []
    return sorted([p for p in directory.iterdir() if (p.is_file() and p.suffix == '.json')
        or (p.is_dir() and not p.name.startswith('.') and (p / 'family.json').is_file())])


def describe_task(path):
    from .offline_app import check_task
    from .trade_cli import configuration_view
    checked = check_task(path, inspect_only=True)
    family = _family_for_task(path)
    view = read_family(family) if family else dict(state=checked['semantics']['state'], revisions=[], legacy_task=True)
    from .input_workflow import bound_input_view
    return dict(**view, task_id=checked['task_id'], strategy=checked['semantics']['strategy'], inputs=bound_input_view(checked),
        viewed_revision=checked['semantics'].get('management',{}).get('revision'),
        configuration=configuration_view(checked['semantics']['experiment']), scoring=checked['protocol'],
        task_file=str(checked['task_path']))
