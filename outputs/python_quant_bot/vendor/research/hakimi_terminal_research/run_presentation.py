"""Frozen run labels and configuration differences, without executing strategies."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re

from .documents import read_document


PRESENTATION_FILE = 'task-presentation.json'
PRESENTATION_SCHEMA = 'hakimi-run-presentation-v1'
RUN_SCHEMA = 'hakimi-offline-run-inputs-v2'
_REVISION = re.compile(r'r([0-9]{4})-[0-9a-f]{32}')


def capture_task_presentation(context):
    """Capture a name only during preparation under the caller's execution guard."""
    management = context['semantics'].get('management')
    if management is not None:
        from .task_manager import read_family
        task_path = Path(context['task_path'])
        family = read_family(task_path.parent.parent.parent)
        if (family['family_id'] != management['family_id']
                or management['revision'] not in family['revisions']
                or task_path.parent.name != management['revision']):
            raise ValueError('run_presentation_family_binding_invalid')
        name, origin = family['title'], 'MANAGED_TASK_TITLE'
    else:
        name, origin = Path(context['task_path']).stem, 'LEGACY_TASK_FILE_NAME'
    return dict(schema_version=PRESENTATION_SCHEMA, task_id=context['task_id'],
                management=deepcopy(management), task_display_name=name, name_origin=origin)


def retained_presentation(manifest, directory):
    """Read only the hash-bound snapshot; an unbound file is never a name source."""
    expected = manifest['input_sha256'].get(PRESENTATION_FILE)
    if expected is None:
        if manifest['schema_version'] == RUN_SCHEMA:
            raise ValueError('run_presentation_binding_missing')
        return None
    path = Path(directory) / 'inputs' / PRESENTATION_FILE
    if not path.is_file() or path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('retained_input_missing_or_changed:' + PRESENTATION_FILE)
    value = read_document(path)
    management = manifest['task'].get('management')
    expected_origin = 'MANAGED_TASK_TITLE' if management is not None else 'LEGACY_TASK_FILE_NAME'
    if (set(value) != {'schema_version', 'task_id', 'management', 'task_display_name', 'name_origin'}
            or value['schema_version'] != PRESENTATION_SCHEMA
            or value['task_id'] != manifest['task_id']
            or value['management'] != management
            or value['name_origin'] != expected_origin
            or type(value['task_display_name']) is not str or not value['task_display_name'].strip()):
        raise ValueError('run_presentation_snapshot_invalid')
    return value


def task_presentation(manifest, directory):
    """Project a verified run's saved name/version, never its current task family."""
    value = retained_presentation(manifest, directory)
    management = manifest['task'].get('management')
    management = management if isinstance(management, dict) else {}
    revision = management.get('revision')
    matched = _REVISION.fullmatch(revision) if isinstance(revision, str) else None
    number = int(matched.group(1)) if matched and int(matched.group(1)) > 0 else None
    return dict(task_display_name=value['task_display_name'] if value else '历史任务（名称未保存）',
                task_display_name_status='RETAINED' if value else 'NOT_RETAINED',
                task_display_name_origin=value['name_origin'] if value else None,
                task_family_id=management.get('family_id'), task_revision=revision if matched else None,
                task_version_number=number, task_version_label=f'版本 {number}' if number else '版本未知')


def configuration_differences(left, right):
    """Expose requested/effective values; missing fields differ from explicit null."""
    def flatten(value, prefix):
        if isinstance(value, dict):
            result = {}
            for key in sorted(value):
                result.update(flatten(value[key], prefix + '.' + key))
            return result
        return {prefix: value}

    def values(configuration):
        result = {}
        for field in ('requested', 'effective', 'risk_policy', 'exit_rule'):
            if field in configuration:
                result.update(flatten(configuration[field], field))
        return result

    first, second = values(left), values(right)
    return [dict(path=path, left_present=path in first, right_present=path in second,
                 left=deepcopy(first.get(path)), right=deepcopy(second.get(path)))
            for path in sorted(first.keys() | second.keys())
            if path not in first or path not in second or first[path] != second[path]]
