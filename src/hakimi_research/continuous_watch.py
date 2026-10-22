"""Explicit local-file observation for continuous research; never a data feed.

The shared account remains the only economic ledger. This module stores source
mapping, diagnostic status and a durable pending request for receipt recovery.
It never connects to a provider, places orders, or resumes observation on import.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
from threading import Event, RLock, Thread
from tempfile import NamedTemporaryFile

from .continuous_runtime import (_available, describe_continuous_account,
    lookup_continuous_receipt, task_control_snapshot, task_family_locks)
from .documents import canonical_bytes, digest, read_document
from .equity_dataset import verify_equity_snapshot
from .offline_app import _file_lock, write_new
from .shared_account import _clock, _manifest, transact_shared_account

WATCH_SCHEMA = 'continuous-local-watch-v1'
_ACTIVE = {}
_ACTIVE_LOCK = RLock()


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _atomic(path, document):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(prefix='.watch-state-', suffix='.tmp', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(canonical_bytes(document)); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load(directory):
    path = Path(directory).resolve() / 'watch.json'
    if path.is_symlink(): raise ValueError('watch_configuration_must_be_regular')
    document = read_document(path)
    body = {k: v for k, v in document.items() if k != 'watch_id'}
    if (set(body) != {'schema_version', 'account_dir', 'account_id', 'inputs', 'interval_seconds', 'max_data_age_seconds', 'task_files'}
            or body['schema_version'] != WATCH_SCHEMA or digest(body) != document.get('watch_id')):
        raise ValueError('watch_configuration_identity_invalid')
    return document


def configure_watch(directory, account_dir, inputs, *, interval_seconds=5, max_data_age_seconds=345600, task_files=None):
    directory = Path(directory).resolve(); account_dir = Path(account_dir).resolve()
    view = describe_continuous_account(account_dir)
    if type(inputs) is not dict or set(inputs) != set(view['state']['marks']):
        raise ValueError('watch_explicit_complete_security_path_mapping_required')
    if type(interval_seconds) not in (int, float) or not 1 <= interval_seconds <= 3600:
        raise ValueError('watch_interval_must_be_1_to_3600_seconds')
    if type(max_data_age_seconds) is not int or not 60 <= max_data_age_seconds <= 30*86400:
        raise ValueError('watch_max_age_must_be_60_seconds_to_30_days')
    if directory.exists(): raise ValueError('watch_new_directory_required')
    normalized = {}
    for security, location in inputs.items():
        original = Path(location).absolute()
        if original.is_symlink() or not original.is_file():
            raise ValueError('watch_initial_snapshot_path_must_be_regular_file:' + security)
        normalized[security] = str(original.resolve())
    if len(set(normalized.values())) != len(normalized):
        raise ValueError('watch_each_security_requires_distinct_file')
    body = dict(schema_version=WATCH_SCHEMA, account_dir=str(account_dir), account_id=view['account_id'],
        inputs=normalized, interval_seconds=interval_seconds, max_data_age_seconds=max_data_age_seconds,
        task_files=[str(Path(p).resolve()) for p in task_files] if task_files is not None else None)
    directory.mkdir(parents=True, exist_ok=False)
    write_new(directory/'watch.json', {**body, 'watch_id':digest(body)})
    _atomic(directory/'status.json', dict(status='STOPPED', reason='Explicit start required; restart never starts observation.',
        last_poll_at=None, last_success_at=view['continuous']['last_success_at'], pending_operation_id=None))
    return describe_watch(directory)


class LocalInputWatcher:
    def __init__(self, directory, *, clock=None):
        self.directory = Path(directory).resolve(); self.config = _load(self.directory)
        self.clock = clock or _now; self._stop = Event(); self._thread = None; self._seen = {}; self._lock = RLock()

    def _status(self, status, reason, now, **extra):
        previous = read_document(self.directory/'status.json')
        document = {**previous, 'status':status, 'reason':reason, 'last_poll_at':now, **extra}
        _atomic(self.directory/'status.json', document)
        return self.describe()

    def describe(self):
        result = read_document(self.directory/'status.json')
        alive = bool(self._thread and self._thread.is_alive())
        return {**result, 'watch_id':self.config['watch_id'], 'monitoring':alive,
            'observation_state':'STOPPING' if alive and self._stop.is_set() else 'RUNNING' if alive else 'STOPPED',
            'inputs':deepcopy(self.config['inputs']), 'account_dir':self.config['account_dir'], 'account_id':self.config['account_id'],
            'task_files':deepcopy(self.config['task_files']), 'interval_seconds':self.config['interval_seconds'],
            'max_data_age_seconds':self.config['max_data_age_seconds'], 'network_requests':0,
            'execution_authority':'RESEARCH_ONLY_NO_BROKER_OR_ORDERS'}

    def _pending(self):
        pointer = self.directory/'pending.json'
        if not pointer.exists(): return None
        value = read_document(pointer)
        if value == {'operation_id':None}: return None
        if type(value) is not dict or set(value) != {'operation_id'}:
            raise ValueError('watch_pending_pointer_invalid')
        operation_id=value['operation_id']
        if type(operation_id) is not str or not operation_id.startswith('watch-') or len(operation_id)!=70 or any(c not in '0123456789abcdef' for c in operation_id[6:]):
            raise ValueError('watch_pending_operation_identity_invalid')
        document=read_document(self.directory/'requests'/(operation_id+'.json'))
        if (type(document) is not dict or set(document) != {'account_id','request','source_hashes','operation_id','receipt_head_at_observation'}
                or document['account_id'] != self.config['account_id'] or document['operation_id'] != operation_id
                or operation_id != 'watch-'+digest({k:v for k,v in document.items() if k!='operation_id'})):
            raise ValueError('watch_pending_request_identity_invalid')
        return document

    def _resolve(self, pending, now):
        lookup = lookup_continuous_receipt(self.config['account_dir'], pending['operation_id'])
        receipt = lookup['receipt']
        if receipt is not None and receipt['request'] != pending['request']:
            raise ValueError('watch_committed_receipt_request_conflict')
        if receipt is None:
            runtime=describe_continuous_account(self.config['account_dir'])['continuous']
            if ((runtime['last_observed_at'] and pending['request']['at'] < runtime['last_observed_at'])
                    or (runtime['last_session'] and pending['request']['payload']['through'] < runtime['last_session'])):
                return self._status('PENDING_REVIEW_REQUIRED','Account has advanced beyond this uncommitted request; inspect it before any retry.',now,
                    pending_operation_id=pending['operation_id'])
            last_available=min(_available(value,value['sessions'][-1]) for value in pending['request']['payload']['snapshots'].values())
            age=(datetime.fromisoformat(now.replace('Z','+00:00'))-datetime.fromisoformat(last_available.replace('Z','+00:00'))).total_seconds()
            if age<0 or age>self.config['max_data_age_seconds']:
                return self._status('PENDING_REVIEW_REQUIRED','Uncommitted pending input is no longer within the declared availability/age window; explicit review required.',now,
                    pending_operation_id=pending['operation_id'])
            states,warnings=task_control_snapshot(self.config['account_dir'],self.config['task_files'])
            payload=pending['request']['payload']
            if states != payload['task_states'] or warnings != payload['task_configuration_warnings']:
                return self._status('PENDING_REVIEW_REQUIRED','Uncommitted pending request has older task controls; explicit discard or restore controls required.',now,
                    pending_operation_id=pending['operation_id'])
            request=pending['request']
            receipt=transact_shared_account(self.config['account_dir'], operation_id=pending['operation_id'], **request)
        view=describe_continuous_account(self.config['account_dir'])
        outcome=receipt['outcome']; blocked=outcome['status']=='BLOCKED'
        result=self._status('INPUT_REJECTED' if blocked else 'CURRENT',outcome.get('reason'),now,
            pending_operation_id=None, receipt_hash=receipt['receipt_hash'],
            last_success_at=view['continuous']['last_success_at'], latest_common_session=pending['request']['payload']['through'],
            last_source_hashes=pending['source_hashes'], account_status=view['continuous']['status'],
            last_controls_hash=digest(dict(states=pending['request']['payload']['task_states'],warnings=pending['request']['payload']['task_configuration_warnings'])))
        # Clearing only follows a durable, verified receipt and published status.
        _atomic(self.directory/'pending.json',{'operation_id':None})
        return result

    def poll_once(self, *, now=None):
        now=_clock(now or self.clock())
        with self._lock, _file_lock(self.directory/'.watch.lock'), ExitStack() as stack:
            try:
                task_family_locks(stack,self.config['task_files'])
                if _load(self.directory)!=self.config: raise ValueError('watch_configuration_changed_restart_required')
                view=describe_continuous_account(self.config['account_dir'])
                if view['account_id']!=self.config['account_id']: raise ValueError('watch_account_identity_changed')
                pending=self._pending()
                if pending is not None:
                    try:return self._resolve(pending,now)
                    except Exception as exc:
                        return self._status('SUBMISSION_UNKNOWN','Read the durable receipt before retry: '+str(exc),now,pending_operation_id=pending['operation_id'])
                data={};hashes={};unstable=[]
                for security,location in self.config['inputs'].items():
                    path=Path(location)
                    if path.is_symlink() or not path.is_file():
                        return self._status('INPUT_MISSING','Snapshot missing; protection cannot be computed: '+security,now)
                    before=path.stat()
                    if before.st_size>32*1024*1024:raise ValueError('watch_snapshot_size_limit')
                    raw=path.read_bytes();after=path.stat()
                    fingerprint=(after.st_size,after.st_mtime_ns,sha256(raw).hexdigest())
                    if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or self._seen.get(security)!=fingerprint:
                        unstable.append(security)
                    self._seen[security]=fingerprint;hashes[security]=fingerprint[2]
                    from .documents import parse_document
                    value=verify_equity_snapshot(parse_document(raw))
                    if value['security']['security_id']!=security:raise ValueError('watch_snapshot_security_mismatch:'+security)
                    if datetime.fromisoformat(value['retrieved_at'].replace('Z','+00:00'))>datetime.fromisoformat(now.replace('Z','+00:00')):
                        return self._status('INPUT_NOT_YET_AVAILABLE','Snapshot receipt is in the future: '+security,now)
                    data[security]=value
                if unstable:return self._status('WAITING_STABLE_INPUT','Need two unchanged reads: '+','.join(unstable),now)
                latest=min(value['sessions'][-1]['date'] for value in data.values())
                if view['continuous']['last_session'] and latest<view['continuous']['last_session']:
                    return self._status('INPUT_REJECTED','Incoming snapshot ends before the committed cursor; no automatic rewind.',now,latest_common_session=latest)
                if view['continuous']['last_observed_at'] and now<view['continuous']['last_observed_at']:
                    return self._status('INPUT_NOT_YET_AVAILABLE','Observer clock precedes the last committed observation; no clock rewind.',now)
                last_available=min(_available(value,value['sessions'][-1]) for value in data.values())
                age=(datetime.fromisoformat(now.replace('Z','+00:00'))-datetime.fromisoformat(last_available.replace('Z','+00:00'))).total_seconds()
                if age<0:return self._status('INPUT_NOT_YET_AVAILABLE','Last bar is not yet available.',now)
                if age>self.config['max_data_age_seconds']:
                    return self._status('INPUT_STALE','Data exceeds the explicitly configured age limit; no automatic backfill trades or protection claim.',now,
                        latest_common_session=latest,data_age_seconds=age)
                previous=read_document(self.directory/'status.json')
                states,warnings=task_control_snapshot(self.config['account_dir'],self.config['task_files'])
                controls=digest(dict(states=states,warnings=warnings))
                if hashes==previous.get('last_source_hashes') and controls==previous.get('last_controls_hash'):
                    return self._status(previous['status'] if previous['status']=='INPUT_REJECTED' else 'CURRENT',previous.get('reason') if previous['status']=='INPUT_REJECTED' else None,now,
                        account_status=view['continuous']['status'],last_success_at=view['continuous']['last_success_at'],data_age_seconds=age)
                request=dict(kind='CONTINUOUS_ADVANCE',at=now,payload=dict(snapshots=data,through=latest,task_states=states,task_configuration_warnings=warnings))
                body=dict(account_id=self.config['account_id'],request=request,source_hashes=hashes,receipt_head_at_observation=view['receipt_head'])
                pending={**body,'operation_id':'watch-'+digest(body)}
                write_new(self.directory/'requests'/(pending['operation_id']+'.json'),pending)
                _atomic(self.directory/'pending.json',dict(operation_id=pending['operation_id']))
                try:return self._resolve(pending,now)
                except Exception as exc:
                    return self._status('SUBMISSION_UNKNOWN','Read the durable receipt before retry: '+str(exc),now,pending_operation_id=pending['operation_id'])
            except Exception as exc:
                return self._status('INPUT_ERROR',str(exc),now)

    def _run(self):
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self.config['interval_seconds'])

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():return self.describe()
            self._stop.clear();self._thread=Thread(target=self._run,name='hakimi-local-research-watch',daemon=True);self._thread.start()
            return self.describe()

    def stop(self):
        self._stop.set()
        thread=self._thread
        if thread:thread.join(timeout=3)
        return self.describe()


def start_watch(directory):
    key=str(Path(directory).resolve())
    with _ACTIVE_LOCK:
        watcher=_ACTIVE.get(key)
        if watcher is None:watcher=LocalInputWatcher(directory);_ACTIVE[key]=watcher
        watcher.start();return watcher


def stop_watch(directory):
    key=str(Path(directory).resolve())
    with _ACTIVE_LOCK:
        watcher=_ACTIVE.get(key)
    return watcher.stop() if watcher else describe_watch(directory)


def describe_watch(directory):
    key=str(Path(directory).resolve())
    with _ACTIVE_LOCK:
        watcher=_ACTIVE.get(key)
    return watcher.describe() if watcher else LocalInputWatcher(directory).describe()


def discard_uncommitted_pending(directory, *, expected_operation_id, reason):
    """Explicit user recovery; a committed/unknown receipt is never discarded."""
    watcher=LocalInputWatcher(directory)
    if type(reason) is not str or not reason.strip():raise ValueError('watch_pending_discard_reason_required')
    with _file_lock(watcher.directory/'.watch.lock'):
        pending=watcher._pending()
        if pending is None or pending['operation_id']!=expected_operation_id:
            raise ValueError('watch_expected_pending_identity_required')
        lookup=lookup_continuous_receipt(watcher.config['account_dir'],expected_operation_id)
        if lookup['status']!='NOT_RECORDED':raise ValueError('watch_committed_request_must_be_resolved_not_discarded')
        # Keep both original request and the user's disposition as local evidence.
        write_new(watcher.directory/'dispositions'/(expected_operation_id+'.json'),
            dict(operation_id=expected_operation_id,status='USER_DISCARDED_NOT_RECORDED',reason=reason,at=_now()))
        _atomic(watcher.directory/'pending.json',{'operation_id':None})
        return watcher._status('STOPPED','Uncommitted request explicitly discarded; source may be reconsidered on next explicit observation.',_now(),pending_operation_id=None)
