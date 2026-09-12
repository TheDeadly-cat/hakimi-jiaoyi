"""One bounded local notification for a verified launcher receipt; no scheduler."""
from __future__ import annotations

import argparse
from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid

_SPEC = importlib.util.spec_from_file_location('notification_launcher_helpers', Path(__file__).with_name('observation_job.py'))
job = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(job)

DISPLAYED = {'OS_DISPLAY_REPORTED', 'USER_CLICK_REPORTED'}
KNOWN_UNSHOWN = {'DEFERRED_BY_USER_STATE', 'USER_STATE_UNAVAILABLE'}
WORKER_STATES = DISPLAYED | KNOWN_UNSHOWN | {'DISPLAY_UNCONFIRMED', 'WORKER_ERROR'}
FAILED_HEALTH = {'FAILED_PREFLIGHT', 'CHILD_FAILED', 'CHILD_TERMINATED', 'CHILD_START_OR_WAIT_FAILED',
    'EXIT_ZERO_RESULT_INVALID', 'CHILD_TIMED_OUT', 'CHILD_OUTPUT_LIMIT', 'CHILD_LEFTOVER_DESCENDANTS',
    'CHILD_CLEANUP_NOT_CONFIRMED', 'CHILD_OUTPUT_READ_FAILED', 'CHILD_OUTPUT_ENCODING_INVALID'}


def read(path):
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError('notification_receipt_too_large')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_JSON_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_JSON')))


def payload_from_receipt(path, *, drill=False, launcher_sha256=None):
    path = Path(path).resolve()
    if path.name != 'ended.json':
        raise ValueError('ended_launcher_receipt_required')
    start = job.verify_seal(read(path.with_name('started.json')))
    end = job.verify_seal(read(path))
    expected = launcher_sha256 or job.file_hash(Path(job.__file__))
    cutoff = job.timestamp(end['input_cutoff'])
    if (start.get('schema_version') != 'observation-job-start-v2'
            or end.get('schema_version') != 'observation-job-end-v2'
            or start.get('attempt_id') != end.get('attempt_id')
            or end.get('started_receipt_hash') != start['receipt_hash']
            or start.get('input_cutoff') != end['input_cutoff']
            or job.stamp(cutoff) != end['input_cutoff'] or cutoff.minute or cutoff.second or cutoff.microsecond
            or start.get('launcher_sha256') != expected
            or start.get('frozen_wrapper_sha256') != job.WRAPPER_SHA256
            or start.get('frozen_plan_sha256') != job.PLAN_SHA256
            or start.get('order_allowed') is not False or end.get('order_allowed') is not False
            or type(end.get('result_valid')) is not bool):
        raise ValueError('notification_source_identity_or_binding_invalid')
    health = end.get('health')
    valid_health = {'RESULT_VALID','LATE','DUPLICATE_VERIFY'}
    if health not in FAILED_HEALTH | valid_health | {'DUPLICATE_IN_FLIGHT'}:
        raise ValueError('unknown_launcher_health')
    if end['result_valid'] != (health in valid_health):
        raise ValueError('health_and_result_valid_disagree')
    notification = end.get('notification', {})
    if notification.get('decision') not in {'NOTIFY','DONT_NOTIFY'}:
        raise ValueError('unknown_notification_decision')
    if ((health in FAILED_HEALTH or health == 'LATE') and notification['decision'] != 'NOTIFY'
            or health == 'DUPLICATE_IN_FLIGHT' and notification['decision'] != 'DONT_NOTIFY'):
        raise ValueError('health_and_notification_decision_disagree')
    if notification['decision'] == 'DONT_NOTIFY':
        return None
    reasons = notification.get('reasons', [])
    if type(reasons) is not list or any(type(reason) is not str for reason in reasons):
        raise ValueError('invalid_notification_reasons')
    if health in FAILED_HEALTH:
        message, icon = '观察未产生有效结果，请检查本地运行记录。', 'Warning'
    elif health == 'LATE':
        message, icon = '观察已完成，但超过准时期限。', 'Warning'
    elif 'recovered_after_failed_result' in reasons:
        message, icon = '观察已从先前失败中恢复，结果验证通过。', 'Info'
    elif 'new_missing_strategy_hours_including_outside_frozen_window' in reasons:
        message, icon = '发现缺少的观察记录，请核对本地覆盖报告。', 'Warning'
    elif 'prior_start_without_end' in reasons:
        message, icon = '发现先前任务没有结束回执，需核对运行状态。', 'Warning'
    else:
        raise ValueError('unsupported_notification_reason')
    core = {'schema_version':'observation-notification-payload-v1',
            'source_receipt_hash':end['receipt_hash'], 'source_started_hash':start['receipt_hash'],
            'source_launcher_sha256':expected, 'input_cutoff':end['input_cutoff'], 'drill':bool(drill),
            'title':('演练：' if drill else '') + '哈基米研究观察',
            'body':('隔离演练，' if drill else '') + cutoff.strftime('%m-%d %H:%M UTC：') + message,
            'icon':icon, 'order_allowed':False}
    identity = job.digest(core)
    # A short code binds the visible trial to this exact payload, not a prior pop-up.
    return {**core, 'notification_id':identity, 'body':core['body'] + ' 编号 ' + identity[:8]}


def validate_payload(value):
    if type(value) is not dict or value.get('schema_version') != 'observation-notification-payload-v1':
        raise ValueError('invalid_payload')
    identity = value.get('notification_id')
    if type(identity) is not str or not re.fullmatch('[a-f0-9]{64}', identity):
        raise ValueError('invalid_notification_identity')
    suffix = ' 编号 ' + identity[:8]
    if not value.get('body','').endswith(suffix):
        raise ValueError('payload_display_binding_missing')
    core = {key:item for key,item in value.items() if key != 'notification_id'}
    core['body'] = core['body'][:-len(suffix)]
    if job.digest(core) != identity or value.get('order_allowed') is not False:
        raise ValueError('payload_identity_changed')
    if len(value['title']) > 48 or len(value['body']) > 200:
        raise ValueError('notification_text_too_long')
    return value


def execute_worker(request_path):
    if os.name != 'nt':
        raise OSError('windows_notification_required')
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = Path(__file__).with_name('show_observation_notification.ps1')
    return job.execute([str(powershell),'-NoLogo','-NoProfile','-NonInteractive','-STA','-WindowStyle','Hidden',
                        '-File',str(script),'-RequestPath',str(request_path)], request_path.parent,
                       timeout_seconds=25, output_limit_bytes=16384, cleanup_seconds=3)


def dispatch(payload, outbox, *, send=False, worker=execute_worker):
    validate_payload(payload)
    if not send:
        return {'status':'PREVIEW_ONLY', 'payload':payload, 'delivery_confirmed':False}
    outbox = Path(outbox).resolve()
    directory = outbox / 'events' / payload['notification_id']
    with job.job_lock(outbox / 'notification.lock') as acquired:
        if not acquired:
            return {'status':'DUPLICATE_IN_FLIGHT','delivery_confirmed':False}
        request = directory / 'payload.json'
        if request.exists():
            if read(request) != payload:
                raise ValueError('notification_outbox_identity_conflict')
        else:
            job.write_new(request, payload)
        attempts = []
        for path in sorted((directory / 'attempts').glob('*/started.json')):
            if len(attempts) >= 3:
                raise ValueError('notification_attempt_limit')
            start = job.verify_seal(read(path))
            end_path = path.with_name('ended.json')
            if not end_path.exists():
                return {'status':'DELIVERY_UNKNOWN_PRIOR_ATTEMPT','delivery_confirmed':False,
                        'notification_id':payload['notification_id']}
            end = job.verify_seal(read(end_path))
            if (end.get('started_receipt_hash') != start['receipt_hash']
                    or start.get('notification_id') != payload['notification_id']):
                raise ValueError('delivery_attempt_binding_invalid')
            attempts.append((start,end))
        if attempts:
            previous = attempts[-1][1]
            if previous['status'] not in KNOWN_UNSHOWN or len(attempts) >= 3:
                return {'status':'ALREADY_ATTEMPTED','previous_status':previous['status'],
                        'delivery_confirmed':previous['status'] in DISPLAYED,
                        'notification_id':payload['notification_id']}
            if job.now() < job.timestamp(previous['ended_at']) + timedelta(minutes=5):
                return {'status':'DEFERRED_RETRY_BACKOFF','delivery_confirmed':False,
                        'notification_id':payload['notification_id']}
        current = job.now()
        attempt_id = current.strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid.uuid4().hex
        attempt_dir = directory / 'attempts' / attempt_id
        start = job.sealed({'schema_version':'observation-notification-start-v1', 'attempt_id':attempt_id,
            'notification_id':payload['notification_id'], 'started_at':job.stamp(current),
            'request_file_sha256':job.file_hash(request),
            'dispatcher_sha256':job.file_hash(Path(__file__)),
            'renderer_sha256':job.file_hash(Path(__file__).with_name('show_observation_notification.ps1'))})
        job.write_new(attempt_dir/'started.json', start)
        end = {'schema_version':'observation-notification-end-v1','attempt_id':attempt_id,
               'started_receipt_hash':start['receipt_hash'], 'notification_id':payload['notification_id'],
               'status':'DELIVERY_UNKNOWN', 'delivery_confirmed':False, 'user_confirmed':False}
        try:
            result = worker(request)
            end.update(worker_exit_code=result.returncode, execution_bounds=result.bounds)
            if job.file_hash(Path(__file__).with_name('show_observation_notification.ps1')) != start['renderer_sha256']:
                raise ValueError('notification_renderer_changed_during_attempt')
            if result.bounds['outcome'] != 'EXITED' or not result.bounds['cleanup_confirmed']:
                end['status'] = 'WORKER_BOUNDARY_FAILED'
            elif result.returncode:
                end['status'] = 'WORKER_FAILED'
            else:
                value = json.loads(result.stdout)
                if (value.get('schema_version') != 'observation-windows-notification-v1'
                        or value.get('notification_id') != payload['notification_id']
                        or value.get('request_file_sha256') != start['request_file_sha256']
                        or value.get('status') not in WORKER_STATES
                        or job.file_hash(request) != start['request_file_sha256']):
                    raise ValueError('worker_result_binding_invalid')
                if value['status'] in DISPLAYED and (value.get('shown_at') is None or value.get('submitted_at') is None):
                    raise ValueError('display_event_missing')
                if value['status'] == 'USER_CLICK_REPORTED' and value.get('clicked_at') is None:
                    raise ValueError('click_event_missing')
                if value['status'] in KNOWN_UNSHOWN and value.get('submitted_at') is not None:
                    raise ValueError('unshown_status_after_submission')
                for field in ('shown_at','clicked_at','closed_at','submitted_at','ended_at'):
                    if value.get(field) is not None and not current <= job.timestamp(value[field]) <= job.now():
                        raise ValueError('worker_event_clock_outside_attempt')
                ended_at = job.timestamp(value['ended_at'])
                submitted_at = job.timestamp(value['submitted_at']) if value.get('submitted_at') else None
                shown_at = job.timestamp(value['shown_at']) if value.get('shown_at') else None
                if submitted_at and submitted_at > ended_at:
                    raise ValueError('notification_submission_after_end')
                if shown_at and (submitted_at is None or not submitted_at <= shown_at <= ended_at):
                    raise ValueError('notification_display_clock_invalid')
                for field in ('clicked_at','closed_at'):
                    if value.get(field) is not None and (submitted_at is None or not (shown_at or submitted_at) <= job.timestamp(value[field]) <= ended_at):
                        raise ValueError('notification_interaction_clock_invalid')
                end.update(status=value['status'], delivery_confirmed=value['status'] in DISPLAYED,
                           user_confirmed=value['status']=='USER_CLICK_REPORTED', worker_observation=value)
        except Exception as exc:
            end['error_type'] = type(exc).__name__
        end['ended_at'] = job.stamp(job.now())
        end = job.sealed(end)
        job.write_new(attempt_dir/'ended.json',end)
        return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--outbox-root',type=Path,required=True)
    parser.add_argument('--launcher-sha256')
    parser.add_argument('--drill',action='store_true')
    parser.add_argument('--send',action='store_true',help='Show one Windows notification; default is preview only')
    args = parser.parse_args()
    payload = payload_from_receipt(args.receipt, drill=args.drill, launcher_sha256=args.launcher_sha256)
    result = dispatch(payload,args.outbox_root,send=args.send) if payload else {'status':'NO_NOTIFICATION_REQUIRED','delivery_confirmed':False}
    print(json.dumps(result,ensure_ascii=True,allow_nan=False))
    return 0 if result.get('delivery_confirmed') or result['status'] in {'PREVIEW_ONLY','NO_NOTIFICATION_REQUIRED','DUPLICATE_IN_FLIGHT','DEFERRED_RETRY_BACKOFF'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
