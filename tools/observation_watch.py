"""Independent one-shot receipt supervision. Does not start an observer or a task."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import uuid

_SPEC = importlib.util.spec_from_file_location('watch_notification',Path(__file__).with_name('observation_notify.py'))
notify = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(notify)
job = notify.job
HOUR = timedelta(hours=1)
GOOD = {'ON_TIME','LATE'}
PROBLEMS = {'NO_START_RECEIPT','DUPLICATE_ONLY','NO_VALID_RESULT','END_RECEIPT_OVERDUE','FAILED'}
MAX_ATTEMPTS = 4096
MAX_SOURCE_BYTES = 16 * 1024 * 1024


def read_hashed(path, limit=1024*1024):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit+1)
    if len(raw)>limit:
        raise ValueError('watch_document_limit')
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result:
                raise ValueError('duplicate_JSON_key')
            result[key] = value
        return result
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_JSON')))
    return value,hashlib.sha256(raw).hexdigest(),len(raw)


def read(path, limit=1024*1024):
    return read_hashed(path,limit)[0]


def tools_identity():
    return {name:job.file_hash(Path(__file__).with_name(name)) for name in
            ('observation_job.py','observation_notify.py','show_observation_notification.ps1','observation_watch.py')}


def build_plan(start_cutoff, hours, *, scope='DECLARED_WINDOW', launcher_sha256=None):
    start = job.timestamp(start_cutoff)
    selected = job.now()
    if (scope not in {'DECLARED_WINDOW','ISOLATED_DRILL'} or type(hours) is not int or not 1<=hours<=72
            or start.minute or start.second or start.microsecond
            or scope=='DECLARED_WINDOW' and (hours!=72 or start<=selected)):
        raise ValueError('future_72h_window_or_explicit_isolated_drill_required')
    tools = tools_identity()
    launcher = launcher_sha256 or tools['observation_job.py']
    if not re.fullmatch('[a-f0-9]{64}',launcher) or scope=='DECLARED_WINDOW' and launcher!=tools['observation_job.py']:
        raise ValueError('invalid_expected_launcher_identity')
    return job.sealed({'schema_version':'observation-watch-plan-v1','scope':scope,
        'selected_at':job.stamp(selected),'start_cutoff':job.stamp(start),
        'end_cutoff_exclusive':job.stamp(start+hours*HOUR),'planned_hours':hours,
        'timely_seconds':300,'scheduled_minute':1,'unfinished_after_seconds':335,
        'expected_launcher_sha256':launcher,'frozen_plan_sha256':job.PLAN_SHA256,
        'frozen_wrapper_sha256':job.WRAPPER_SHA256,'tools_sha256':tools,
        'plan_is_scheduler_activation':False,'order_allowed':False})


def verify_plan(plan):
    job.verify_seal(plan)
    start,end = job.timestamp(plan['start_cutoff']),job.timestamp(plan['end_cutoff_exclusive'])
    if (plan.get('schema_version')!='observation-watch-plan-v1'
            or plan.get('scope') not in {'DECLARED_WINDOW','ISOLATED_DRILL'}
            or type(plan.get('planned_hours')) is not int or not 1<=plan['planned_hours']<=72
            or start.minute or start.second or start.microsecond
            or end-start!=plan['planned_hours']*HOUR
            or plan.get('timely_seconds')!=300 or plan.get('scheduled_minute')!=1
            or plan.get('unfinished_after_seconds')!=335
            or plan.get('tools_sha256')!=tools_identity()
            or plan.get('frozen_plan_sha256')!=job.PLAN_SHA256 or plan.get('frozen_wrapper_sha256')!=job.WRAPPER_SHA256
            or plan.get('plan_is_scheduler_activation') is not False or plan.get('order_allowed') is not False
            or not re.fullmatch('[a-f0-9]{64}',plan.get('expected_launcher_sha256',''))):
        raise ValueError('watch_plan_or_tools_changed')
    if plan['scope']=='DECLARED_WINDOW' and (plan['planned_hours']!=72
            or job.timestamp(plan['selected_at'])>=start
            or plan['expected_launcher_sha256']!=plan['tools_sha256']['observation_job.py']):
        raise ValueError('declared_window_identity_or_selection_invalid')
    return plan


def inventory(job_root, plan):
    """Read complete atomically published receipts; never lock out the producer."""
    first,last = job.timestamp(plan['start_cutoff']),job.timestamp(plan['end_cutoff_exclusive'])
    sources, attempts, total = {}, [], 0
    paths = []
    for path in (job_root/'attempts').glob('*/started.json'):
        if len(paths)>=MAX_ATTEMPTS:
            raise ValueError('watch_attempt_limit')
        paths.append(path)
    for start_path in sorted(paths):
        if not start_path.resolve().is_relative_to(job_root):
            raise ValueError('source_path_outside_job_root')
        start,start_sha,size=read_hashed(start_path,65536)
        total += size
        if total>MAX_SOURCE_BYTES:
            raise ValueError('watch_source_byte_limit')
        cutoff = job.timestamp(start['input_cutoff'])
        if not first<=cutoff<last:
            continue
        job.verify_seal(start)
        started = job.timestamp(start['launcher_function_started_at'])
        if (start.get('schema_version')!='observation-job-start-v2'
                or start.get('attempt_id')!=start_path.parent.name
                or start.get('launcher_sha256')!=plan['expected_launcher_sha256']
                or start.get('frozen_wrapper_sha256')!=plan['frozen_wrapper_sha256']
                or start.get('frozen_plan_sha256')!=plan['frozen_plan_sha256']
                or start.get('order_allowed') is not False
                or not cutoff<=started<cutoff+HOUR or job.stamp(cutoff)!=start['input_cutoff']):
            raise ValueError('unaccepted_launcher_start')
        sources[start_path.relative_to(job_root).as_posix()] = start_sha
        end_path = start_path.with_name('ended.json')
        end = None
        if end_path.exists():
            if not end_path.resolve().is_relative_to(job_root):
                raise ValueError('source_path_outside_job_root')
            end,end_sha,size=read_hashed(end_path,65536)
            total += size
            if total>MAX_SOURCE_BYTES:
                raise ValueError('watch_source_byte_limit')
            job.verify_seal(end)
            ended = job.timestamp(end['launcher_record_ended_at'])
            if (end.get('schema_version')!='observation-job-end-v2'
                    or end.get('attempt_id')!=start['attempt_id']
                    or end.get('started_receipt_hash')!=start['receipt_hash']
                    or end.get('input_cutoff')!=start['input_cutoff'] or end.get('order_allowed') is not False
                    or ended<started or type(end.get('result_valid')) is not bool):
                raise ValueError('unaccepted_launcher_end')
            valid_health = {'RESULT_VALID','LATE','DUPLICATE_VERIFY'}
            if (end.get('health') not in valid_health|notify.FAILED_HEALTH|{'DUPLICATE_IN_FLIGHT'}
                    or end['result_valid'] != (end['health'] in valid_health)):
                raise ValueError('launcher_health_disagrees_with_result')
            if end['result_valid']:
                bounds = end.get('child_execution_bounds',{})
                records = end.get('records',[])
                allowed = {'61aa420de8ad2ae886c31d3ee323393e6a21205fbb222841325d30614e2d6b0c',
                           '8b371b08d8967198dc9d0f0956e7e0da8c5cc639c7d97a27818522b7a09815d5'}
                if (bounds.get('outcome')!='EXITED' or bounds.get('cleanup_confirmed') is not True
                        or type(end.get('child_exit_code')) is not int or end['child_exit_code']!=0
                        or bounds.get('timeout_seconds')!=300 or bounds.get('cleanup_seconds')!=5
                        or bounds.get('output_limit_bytes_combined')!=4194304 or len(records)!=2
                        or {r.get('plan_hash') for r in records}!=allowed):
                    raise ValueError('valid_result_evidence_incomplete')
                for record in records:
                    signal = job.timestamp(record['signal_available_at'])
                    timely = 'ON_TIME' if signal<=cutoff+timedelta(seconds=300) else 'LATE'
                    if (record.get('cutoff')!=start['input_cutoff'] or not cutoff<=signal<=ended
                            or record.get('timing_status')!=timely
                            or not re.fullmatch('[a-f0-9]{64}',record.get('record_hash',''))):
                        raise ValueError('observation_clock_or_identity_invalid')
                expected_health='LATE' if any(record['timing_status']=='LATE' for record in records) else 'RESULT_VALID'
                if end['health'] not in {'DUPLICATE_VERIFY',expected_health}:
                    raise ValueError('launcher_health_and_observation_timing_disagree')
            sources[end_path.relative_to(job_root).as_posix()] = end_sha
        attempts.append({'start':start,'end':end})
    valid_by_cutoff={}
    for item in attempts:
        if item['end'] and item['end']['result_valid']:
            cutoff=item['start']['input_cutoff']
            signature=job.digest(sorted(item['end']['records'],key=lambda record:record['plan_hash']))
            if cutoff in valid_by_cutoff and valid_by_cutoff[cutoff]!=signature:
                raise ValueError('same_cutoff_valid_observation_identity_changed')
            valid_by_cutoff[cutoff]=signature
    return attempts,sources


def evaluate(plan, attempts, previous, as_of):
    """Fixture-callable domain calculation; CLI always supplies an actual clock."""
    prior = {row['cutoff']:row for row in previous.get('rows',[])} if previous else {}
    rows,changes = [],[]
    for offset in range(plan['planned_hours']):
        cutoff = job.timestamp(plan['start_cutoff'])+offset*HOUR
        text = job.stamp(cutoff)
        deadline = cutoff+timedelta(seconds=plan['timely_seconds'])
        old = prior.get(text,{})
        related = sorted([a for a in attempts if a['start']['input_cutoff']==text],
                         key=lambda a:(a['start']['launcher_function_started_at'],a['start']['attempt_id']))
        real = [a for a in related if not a['end'] or a['end']['health']!='DUPLICATE_IN_FLIGHT']
        latest = real[-1] if real else None
        valid=[a for a in real if a['end'] and a['end']['result_valid']]
        observation_status=('LATE' if any(r['timing_status']=='LATE' for a in valid for r in a['end']['records']) else 'ON_TIME') if valid else None
        if cutoff>as_of:
            status = 'PLANNED'
        elif latest is None:
            status = ('DUPLICATE_ONLY' if related else 'NO_START_RECEIPT') if as_of>deadline else 'PENDING'
        elif latest['end'] is None:
            age = as_of-job.timestamp(latest['start']['launcher_function_started_at'])
            status = ('END_RECEIPT_OVERDUE' if age>timedelta(seconds=plan['unfinished_after_seconds'])
                      else 'VERIFICATION_PENDING' if valid else 'NO_VALID_RESULT' if as_of>deadline else 'START_WITHOUT_END')
        elif not latest['end']['result_valid']:
            status = 'FAILED'
        else:
            status = 'LATE' if any(r['timing_status']=='LATE' for r in latest['end']['records']) else 'ON_TIME'
        row = {'cutoff':text,'deadline':job.stamp(deadline),'current_status':status,
               'start_receipts':len(related),'end_receipts':sum(a['end'] is not None for a in related),
               'unfinished_receipts':sum(a['end'] is None for a in related),
               'valid_result_receipts':len(valid),
               'latest_end_hash':latest['end']['receipt_hash'] if latest and latest['end'] else None,
               'deadline_status':old.get('deadline_status','PENDING'),
               'first_problem_observed_at':old.get('first_problem_observed_at'),
               'problem_open':old.get('problem_open',False)}
        if row['deadline_status']=='PENDING' and as_of>deadline:
            row['deadline_status'] = observation_status or ('FAILED' if status=='FAILED' else 'MISSING')
        if status in PROBLEMS:
            if not row['first_problem_observed_at']:
                row['first_problem_observed_at'] = job.stamp(as_of)
            if not row['problem_open'] or status in {'END_RECEIPT_OVERDUE','FAILED'} and old.get('current_status')!=status:
                changes.append({'cutoff':text,'kind':'PROBLEM','status':status})
            row['problem_open'] = True
        elif status in GOOD:
            if row['problem_open']:
                changes.append({'cutoff':text,'kind':'RECOVERY','status':status})
            elif status=='LATE' and old.get('current_status')!='LATE':
                changes.append({'cutoff':text,'kind':'LATE','status':status})
            row['problem_open'] = False
        row['original_gap_preserved'] = row['deadline_status'] in {'MISSING','FAILED'}
        rows.append(row)
    return rows,changes


def event_payload(report, plan):
    changes = report['changes']
    if not changes:
        return None
    counts = Counter(change['kind'] for change in changes)
    slot_counts=Counter(change['kind'] for change in changes if change.get('cutoff'))
    if report['status']!='VERIFIED_RECEIPT_SCAN':
        message = '巡检未能确认观察记录，请检查本地巡检报告。'
    else:
        details=[text for count,text in
            [(slot_counts['PROBLEM'],str(slot_counts['PROBLEM'])+'个周期需核对'),
             (slot_counts['RECOVERY'],str(slot_counts['RECOVERY'])+'个周期已恢复'),
             (slot_counts['LATE'],str(slot_counts['LATE'])+'个周期迟到')] if count]
        if any(change['status']=='SOURCE_CHECK_RECOVERED' for change in changes):
            details.append('巡检来源核对已恢复')
        if any(change['kind']=='WINDOW_ELAPSED' for change in changes):
            details.append('声明窗口已结束，等待验收')
        message = '本次扫描：'+'，'.join(details)+'。历史缺口保留。'
    prefix = '隔离演练，' if plan['scope']=='ISOLATED_DRILL' else ''
    core = {'schema_version':'observation-notification-payload-v1',
            'source_watch_report_hash':report['receipt_hash'],'source_watch_plan_hash':plan['receipt_hash'],
            'evidence_origin':'INDEPENDENT_RECEIPT_SCAN','input_cutoff':changes[-1].get('cutoff'),
            'drill':plan['scope']=='ISOLATED_DRILL','title':('演练：' if prefix else '')+'哈基米观察巡检',
            'body':prefix+job.timestamp(report['checked_at']).strftime('%m-%d %H:%M UTC：')+message,
            'icon':'Warning' if counts['PROBLEM'] or report['status']!='VERIFIED_RECEIPT_SCAN' else 'Info',
            'order_allowed':False}
    identity = job.digest(core)
    return {**core,'notification_id':identity,'body':core['body']+' 编号 '+identity[:8]}


def previous_report(root):
    paths = []
    for path in (root/'reports').glob('*.json'):
        if len(paths)>=10000 or not re.fullmatch(r'\d{8}_[a-f0-9]{32}\.json',path.name):
            raise ValueError('watch_report_inventory_invalid')
        paths.append(path)
    if not paths:
        return None
    path = max(paths)
    value = job.verify_seal(read(path))
    if value.get('schema_version')!='observation-watch-report-v1' or value.get('sequence')!=int(path.name[:8]):
        raise ValueError('watch_previous_report_invalid')
    return value


def ensure_pending(root, report, plan):
    payload = event_payload(report,plan)
    if payload is None:
        return
    path = root/'pending'/(f"{report['sequence']:08d}_"+report['receipt_hash']+'.json')
    if path.exists():
        if read(path)!=payload:
            raise ValueError('watch_pending_event_changed')
    else:
        job.write_new(path,payload)


def pending_paths(root):
    paths=[]
    for path in (root/'pending').glob('*.json'):
        if len(paths)>=10000 or not re.fullmatch(r'\d{8}_[a-f0-9]{64}\.json',path.name):
            raise ValueError('watch_notification_queue_invalid')
        paths.append(path)
    return sorted(paths)


def read_pending(root,path,plan):
    candidates=list((root/'reports').glob(path.name[:8]+'_*.json'))
    if len(candidates)!=1:
        raise ValueError('pending_notification_source_report_ambiguous')
    report=job.verify_seal(read(candidates[0]))
    payload=notify.validate_payload(read(path))
    if (report.get('plan_hash')!=plan['receipt_hash'] or report['receipt_hash']!=path.stem[9:]
            or payload!=event_payload(report,plan)):
        raise ValueError('pending_notification_source_binding_invalid')
    return payload


def deliver_pending(root, plan, *, send, worker=notify.execute_worker):
    results,calls = [],0
    if not send:
        return results
    def limited(path):
        nonlocal calls
        if calls>=1:
            raise ValueError('one_native_delivery_per_scan')
        calls+=1
        return worker(path)
    for path in pending_paths(root):
        payload = read_pending(root,path,plan)
        marker = root/'delivery'/(payload['notification_id']+'.json')
        if marker.exists():
            saved = job.verify_seal(read(marker))
            if saved.get('notification_id')!=payload['notification_id']:
                raise ValueError('watch_delivery_marker_mismatch')
            continue
        result = notify.dispatch(payload,root/'outbox',send=True,worker=limited)
        results.append({'notification_id':payload['notification_id'],'result':result})
        if result['status'] not in notify.KNOWN_UNSHOWN|{'DEFERRED_RETRY_BACKOFF','DUPLICATE_IN_FLIGHT'}:
            job.write_new(marker,job.sealed({'notification_id':payload['notification_id'],
                'saved_at':job.stamp(job.now()),'result':result}))
        if calls:
            break
    return results


def delivery_state(root,plan):
    pending,unconfirmed=0,0
    for path in pending_paths(root):
        payload=read_pending(root,path,plan)
        marker=root/'delivery'/(payload['notification_id']+'.json')
        if not marker.exists():
            pending+=1
        else:
            saved=job.verify_seal(read(marker))
            if saved.get('notification_id')!=payload['notification_id']:
                raise ValueError('watch_delivery_marker_mismatch')
            unconfirmed+=saved.get('result',{}).get('delivery_confirmed') is not True
    return {'pending':pending,'unconfirmed':unconfirmed}


def check(plan, job_root, watch_root, *, send=False, worker=notify.execute_worker):
    verify_plan(plan)
    job_root,root = Path(job_root).resolve(),Path(watch_root).resolve()
    if root==job_root or root.is_relative_to(job_root) or job_root.is_relative_to(root):
        raise ValueError('watch_and_producer_roots_must_be_separate')
    with job.job_lock(root/'watch.lock') as acquired:
        if not acquired:
            return {'status':'DUPLICATE_WATCH_IN_FLIGHT'}
        bound = root/'plan.json'
        if bound.exists():
            if read(bound)!=plan:
                raise ValueError('watch_root_bound_to_other_plan')
        else:
            job.write_new(bound,plan)
        previous = previous_report(root)
        if previous and previous.get('plan_hash')!=plan['receipt_hash']:
            raise ValueError('previous_watch_plan_changed')
        if previous:
            ensure_pending(root,previous,plan)  # recover a crash after report publication
        source_root_hash = job.digest({'resolved_job_root':str(job_root)})
        if previous and previous.get('source_root_hash')!=source_root_hash:
            raise ValueError('watch_source_root_changed')
        prior_sources = previous.get('source_file_sha256',{}) if previous else {}
        report = {'schema_version':'observation-watch-report-v1','sequence':previous['sequence']+1 if previous else 1,
            'plan_hash':plan['receipt_hash'],'source_root_hash':source_root_hash,
            'previous_report_hash':previous['receipt_hash'] if previous else None,
            'scope':plan['scope'],'status':'VERIFIED_RECEIPT_SCAN','source_file_sha256':prior_sources,
            'rows':previous.get('rows',[]) if previous else [],'changes':[],
            'evidence_boundary':'PINNED_LAUNCHER_RECEIPTS_NOT_PROCESS_LIVENESS_OR_MARKET_REPLAY',
            'scheduler_activation_verified':False,'order_allowed':False}
        try:
            attempts,sources = inventory(job_root,plan)
            as_of = job.now()
            high_water=job.timestamp(previous.get('maximum_checked_at',previous['checked_at'])) if previous else job.timestamp(plan['selected_at'])
            if as_of<high_water:
                raise ValueError('watch_clock_regressed')
            if any(sources.get(path)!=sha for path,sha in prior_sources.items()):
                raise ValueError('previous_source_bytes_changed_or_removed')
            if any(job.timestamp(a['start']['launcher_function_started_at'])>as_of
                   or a['end'] and job.timestamp(a['end']['launcher_record_ended_at'])>as_of for a in attempts):
                raise ValueError('source_receipt_clock_in_future')
            rows,changes = evaluate(plan,attempts,previous,as_of)
            if previous and previous['status']!='VERIFIED_RECEIPT_SCAN':
                changes.append({'kind':'RECOVERY','status':'SOURCE_CHECK_RECOVERED'})
            report.update(checked_at=job.stamp(as_of),source_file_sha256=sources,rows=rows,changes=changes)
        except (ValueError,KeyError,TypeError,OSError) as exc:
            report.update(status='SOURCE_OR_CLOCK_UNVERIFIED',checked_at=job.stamp(job.now()),error_type=type(exc).__name__)
            if not previous or previous['status']!='SOURCE_OR_CLOCK_UNVERIFIED':
                report['changes']=[{'kind':'PROBLEM','status':'SOURCE_OR_CLOCK_UNVERIFIED'}]
        report['rows_are_current']=report['status']=='VERIFIED_RECEIPT_SCAN'
        report['current_counts']=dict(Counter(row['current_status'] for row in report['rows'])) if report['rows_are_current'] else {}
        report['rows_last_verified_at']=report['checked_at'] if report['rows_are_current'] else previous.get('rows_last_verified_at') if previous else None
        report['deadline_counts']=dict(Counter(row['deadline_status'] for row in report['rows']))
        report['maximum_checked_at']=max(report['checked_at'],previous.get('maximum_checked_at',previous['checked_at']) if previous else report['checked_at'])
        report['window_elapsed']=bool(previous and previous.get('window_elapsed')) or timestamp_at_end(plan,report['checked_at'])
        if report['window_elapsed'] and not (previous and previous.get('window_elapsed')):
            report['changes'].append({'kind':'WINDOW_ELAPSED','status':'WINDOW_ENDED_REVIEW_REQUIRED'})
        report=job.sealed(report)
        report_path=root/'reports'/(f"{report['sequence']:08d}_"+uuid.uuid4().hex+'.json')
        job.write_new(report_path,report)
        ensure_pending(root,report,plan)
        delivery=deliver_pending(root,plan,send=send,worker=worker)
        return {'status':report['status'],'report':report,'delivery':delivery,
                'notification_state':delivery_state(root,plan),'notification_send_requested':bool(send)}


def timestamp_at_end(plan,value):
    return job.timestamp(value)>=job.timestamp(plan['end_cutoff_exclusive'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    make=sub.add_parser('plan')
    make.add_argument('--start',required=True)
    make.add_argument('--hours',type=int,default=72)
    make.add_argument('--scope',choices=('DECLARED_WINDOW','ISOLATED_DRILL'),default='DECLARED_WINDOW')
    make.add_argument('--launcher-sha256')
    make.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('check')
    run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--job-root',type=Path,required=True)
    run.add_argument('--watch-root',type=Path,required=True)
    run.add_argument('--send',action='store_true')
    args=parser.parse_args()
    if args.command=='plan':
        plan=build_plan(args.start,args.hours,scope=args.scope,launcher_sha256=args.launcher_sha256)
        job.write_new(args.output,plan)
        print(json.dumps(plan,ensure_ascii=True))
        return 0
    result=check(read(args.plan),args.job_root,args.watch_root,send=args.send)
    if 'report' in result:
        report=result['report']
        compact={key:report[key] for key in ('status','checked_at','receipt_hash','current_counts','deadline_counts')}
        compact.update(changes=len(report['changes']),delivery=[item['result']['status'] for item in result['delivery']],
                       notification_send_requested=bool(args.send),notification_state=result['notification_state'])
    else:
        compact=result
    print(json.dumps(compact,ensure_ascii=True,allow_nan=False))
    if result['status']!='VERIFIED_RECEIPT_SCAN':
        return 1
    return 1 if args.send and (result['notification_state']['pending'] or result['notification_state']['unconfirmed']) else 0


if __name__=='__main__':
    raise SystemExit(main())
