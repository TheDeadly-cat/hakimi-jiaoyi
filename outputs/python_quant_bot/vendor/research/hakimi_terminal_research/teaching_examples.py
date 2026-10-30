"""Explicit, additive preparation of the existing fictional teaching fixtures.

No strategy runs here. Ordinary input admission and managed-task creation remain
authoritative. Partial publications and conflicting user changes are retained;
this function never repairs, revises, enables, or retries a task automatically.
"""
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import stat
import tempfile

from .documents import canonical_bytes, read_document
from .equity_dataset import build_equity_snapshot
from .equity_event_context import verify_event_context
from . import input_workflow, task_manager
from .offline_app import _file_lock
from .trade_cli import build_task_document, initialize_empty


_TASKS = (
    ('教学-双均线', 'price.dual_ma@1', False),
    ('教学-公告排期', 'event.earnings_schedule@1', True),
)
_PARAMS = dict(fast_window=2, slow_window=4, position_pct=0.25,
               stop_loss_pct=0.03, take_profit_pct=0.06)


def _regular(path):
    """Reject links/reparse points without following them; missing is explicit."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError('teaching_example_reparse_path_not_supported:' + str(path))
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise ValueError('teaching_example_path_not_regular:' + str(path))
    return info


def _guard_path(workspace, path):
    path = Path(path).absolute()
    if not path.is_relative_to(workspace):
        raise ValueError('teaching_example_path_outside_workspace')
    current = workspace
    _regular(current)
    for part in path.relative_to(workspace).parts:
        if part in {'.', '..'}:
            raise ValueError('teaching_example_path_outside_workspace')
        current /= part
        _regular(current)
    return path


def _guard_tree(workspace, directory):
    _guard_path(workspace, directory)
    if directory.is_dir():
        # Visit without following a directory link. A suspicious child stops the
        # operation before the task reader can resolve or write through it.
        for child in directory.iterdir():
            info = _regular(child)
            if info is not None and stat.S_ISDIR(info.st_mode):
                _guard_tree(workspace, child)


def _workspace(workspace):
    workspace = Path(workspace).expanduser().absolute()
    # Resolve only after checking the supplied root and its existing parents.
    for path in reversed((workspace, *workspace.parents)):
        _regular(path)
    workspace = workspace.resolve()
    info = _regular(workspace)
    if info is not None:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError('teaching_example_workspace_not_directory')
        marker = _guard_path(workspace, workspace / 'workspace.json')
        if not marker.is_file() or read_document(marker).get('schema_version') != 'hakimi-offline-workspace-v1':
            raise ValueError('teaching_example_workspace_not_initialized:现有目录保持不变，请选择有效工作区')
    for name in ('data', 'tasks', 'tasks/.task-locks', '.teaching-examples.lock'):
        _guard_path(workspace, workspace / name)
    locks = [workspace / '.teaching-examples.lock'] + [
        workspace / 'tasks/.task-locks' / (name + '.lock') for name, _, _ in _TASKS]
    for lock in locks:
        _guard_path(workspace, lock)
        if _regular(lock) is not None and (not lock.is_file() or lock.read_bytes() != b'0'):
            raise ValueError('teaching_example_control_conflict:现有控制文件保持不变:' + str(lock))
    return workspace


def _existing(workspace, family, expected, snapshot_id, context_hash):
    """Reuse only unchanged teaching configuration, preserving the current state."""
    _guard_path(workspace, family)
    tasks = family.parent
    if tasks.is_dir() and any(tasks.glob('.creating-' + family.name + '-*')):
        raise ValueError('teaching_example_unfinished_creation_retained:' + family.name
                         + ':发现未完成的创建目录，已保留；请先核对，不自动重建')
    legacy = family.with_suffix('.json')
    if _regular(legacy) is not None:
        raise ValueError('teaching_example_name_conflict:' + family.name + ':同名旧任务已保留')
    if _regular(family) is None:
        return None
    _guard_tree(workspace, family)
    try:
        view = task_manager.describe_task(family)
        task = read_document(view['task_file'])
        same = (view['title'] == family.name and len(view['revisions']) == 1
                and not view['uncommitted_versions_retained']
                and view['strategy'] == expected['strategy']
                and canonical_bytes(task['experiment']) == canonical_bytes(expected['experiment'])
                and view['inputs']['snapshot']['input_id'] == snapshot_id
                and (view['inputs']['research']['input_id'] if view['inputs']['research'] else None) == context_hash)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise ValueError('teaching_example_name_conflict:' + family.name
                         + ':现有任务无法确认与教学配置一致，原件已保留') from error
    if not same:
        raise ValueError('teaching_example_name_conflict:' + family.name
                         + ':同名任务已有不同配置、修订或未完成版本，原件已保留；请直接管理现有任务')
    return view


def _id(workspace, path):
    return sha256(Path(path).relative_to(workspace).as_posix().encode()).hexdigest()[:24]


def prepare_teaching_examples(workspace):
    """Append fictional inputs and two tasks only after an explicit user action.

    Returns task paths, economic task IDs and the same opaque path IDs used by
    the desktop inventory. Repeating a completed preparation reuses verified
    configuration and never re-enables paused tasks. A conflicting or unfinished
    task causes a clear failure without cleanup or an alternative task name.
    """
    workspace = _workspace(workspace)
    resources = files('hakimi_terminal_research').joinpath('resources')
    snapshot = build_equity_snapshot(resources.joinpath('trade-demo.csv').read_bytes(),
                                    resources.joinpath('trade-demo-import.json').read_bytes())
    context_raw = resources.joinpath('trade-demo-event-context.json').read_bytes()
    context = verify_event_context(json.loads(context_raw))
    if (snapshot.document['evidence_kind'] != 'SYNTHETIC_TEST'
            or len(snapshot.document['sessions']) != 22
            or context['security_id'] != snapshot.document['security']['security_id']
            or any(event['source']['kind'] != 'SYNTHETIC_FIXTURE' for event in context['events'])):
        raise ValueError('teaching_example_fixture_identity_conflict')
    snapshot_raw = (json.dumps(snapshot.document, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    # Only generated copies of bundled fixtures live in this temporary folder.
    # Task publication stages always stay in the workspace and are never cleaned.
    with tempfile.TemporaryDirectory(prefix='hakimi-teaching-input-') as temporary:
        snapshot_file, context_file = Path(temporary) / 'snapshot.json', Path(temporary) / 'event-context.json'
        snapshot_file.write_bytes(snapshot_raw)
        context_file.write_bytes(context_raw)
        plans = []
        for name, strategy, event in _TASKS:
            options = dict(strategy=strategy, snapshot=snapshot_file,
                           event_context=context_file if event else None, params=dict(_PARAMS))
            family = workspace / 'tasks' / name
            expected = build_task_document(family / '.teaching-preview/task.json', **options)
            plans.append((family, options, expected, context['context_hash'] if event else None))
        # Preflight every collision before adding even an input or lock file.
        for family, _, expected, context_hash in plans:
            _existing(workspace, family, expected, snapshot.snapshot_id, context_hash)
        destinations = [
            workspace / 'data/snapshots' / snapshot.snapshot_id / (sha256(snapshot_raw).hexdigest() + '.json'),
            workspace / 'data/research' / context['context_hash'] / (sha256(context_raw).hexdigest() + '.json'),
        ]
        for path in destinations:
            _guard_path(workspace, path)
        if not workspace.exists():
            initialize_empty(workspace)
        lock = _guard_path(workspace, workspace / '.teaching-examples.lock')
        with _file_lock(lock):
            # Recheck under the preparation lock; task APIs retain their own locks.
            existing = [_existing(workspace, family, expected, snapshot.snapshot_id, context_hash)
                        for family, _, expected, context_hash in plans]
            for path in destinations:
                _guard_path(workspace, path)
            inputs = [input_workflow.import_input(path, workspace) for path in (snapshot_file, context_file)]
            rows = []
            for (family, options, _, _), prior in zip(plans, existing):
                if prior is None:
                    bound = dict(options, snapshot=Path(inputs[0]['path']),
                                 event_context=Path(inputs[1]['path']) if options['event_context'] else None)
                    task_manager.create_family(family, title=family.name, **bound)
                    view = task_manager.describe_task(family)
                    disposition = 'CREATED'
                else:
                    view, disposition = prior, 'REUSED_UNCHANGED'
                rows.append(dict(view, id=_id(workspace, family), name=family.name,
                                 path=str(family), disposition=disposition))
    return dict(status='TEACHING_EXAMPLES_PREPARED', evidence_kind='SYNTHETIC_TEST',
                new_economic_runs=0, tasks=rows,
                inputs=[dict(view, id=_id(workspace, view['path'])) for view in inputs],
                message='已准备22日虚构教学行情与均线2/4教学任务；未运行回测，未修改普通20/60默认值。暂停的已有教学任务保持暂停。')
