"""Bounded NVDA quote collection for two previously selected engineering events.

Default is offline. The explicit live switch reuses the existing pinned SDK,
single-page guard, loopback network restriction and owned Windows Job. Raw
provider data stays in a new private artifacts directory. No trading context.
"""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import collect_equity_event_inputs as shared

CODE='US.NVDA'
PLAN=ROOT/'docs/studies/nvda-event-price-20260930.json'
CALENDAR_HASH='3781aa7ec98e429b39c9b1cbdb3677043b8ba622084b8c9d5e10fd7836d9a13b'
WINDOWS=(('2024Q1','2023-05-24','2023-05-22','2023-06-01'),
         ('2024Q2','2023-08-23','2023-08-21','2023-08-30'))
TIMEOUT_SECONDS=180


def require(ok,reason):
    if not ok:raise shared.CollectionStopped(reason)


def identity():
    paths=[PLAN,Path(__file__),ROOT/'tools/collect_equity_event_inputs.py',ROOT/'tools/observation_job.py']
    return {p.relative_to(ROOT).as_posix():shared.digest(p) for p in paths}


def prepare(calendar_path):
    plan=shared.read(PLAN)
    require(plan['schema_version']=='nvda-two-event-input-plan-v1','PLAN_SCHEMA_CHANGED')
    require(tuple(tuple(e[k] for k in ('fiscal_quarter','publication_date','snapshot_start','snapshot_end')) for e in plan['events'])==WINDOWS,'FIXED_EVENT_WINDOWS_CHANGED')
    require(plan['code']==CODE and plan['budget']==dict(business_calls=6,daily_rows=16,hour_rows=112,pages_per_call=1,retries=0,wall_seconds=180),'FIXED_QUOTE_BUDGET_CHANGED')
    require(plan['permissions']==dict(quote_read=True,account_read=False,orders=False,subscriptions=False,economic_execution=False,raw_redistribution=False),'PERMISSION_SCOPE_CHANGED')
    require(plan['calendar']['sha256']==CALENDAR_HASH,'PLAN_CALENDAR_IDENTITY_CHANGED')
    require(shared.digest(calendar_path)==CALENDAR_HASH,'CALENDAR_ORIGINAL_CHANGED')
    ny=ZoneInfo('America/New_York');calendars={}
    # The retained Nasdaq 2023 calendar marks May 29 closed, no early closes
    # in either fixed range. Every civil day is kept, including closed days.
    for quarter,release,start,end in WINDOWS:
        days=[];day=date.fromisoformat(start)
        while day<=date.fromisoformat(end):
            open_day=day.weekday()<5 and day.isoformat()!='2023-05-29'
            row=dict(date=day.isoformat(),kind='OPEN' if open_day else 'CLOSED')
            if open_day:
                for field,clock in [('open_utc','09:30:00'),('close_utc','16:00:00')]:
                    row[field]=datetime.fromisoformat(day.isoformat()+'T'+clock).replace(tzinfo=ny).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            days.append(row);day+=timedelta(days=1)
        sessions=[d for d in days if d['kind']=='OPEN']
        require(len(sessions)==8 and sessions[2]['date']==release,'FIXED_CALENDAR_WINDOW_CHANGED')
        calendars[quarter]=dict(days=days,sessions=sessions)
    return dict(plan=plan,calendar_path=str(Path(calendar_path).resolve()),calendar_sha256=CALENDAR_HASH,calendars=calendars)


def requests():
    result=[dict(label='security',method='get_stock_basicinfo',kwargs=dict(market='US',stock_type='STOCK',code_list=[CODE])),
            dict(label='actions',method='get_rehab',kwargs=dict(code=CODE))]
    for quarter,_,start,end in WINDOWS:
        for kind,count in [('K_DAY',8),('K_60M',56)]:
            result.append(dict(label=quarter+'-'+kind,quarter=quarter,method='request_history_kline',
                kwargs=dict(code=CODE,start=start,end=end,ktype=kind,autype='None',max_count=count,page_req_key=None,extended_time=False,session='RTH')))
    return result


def validate_security(rows):
    require(len(rows)==1,'ONE_SECURITY_REQUIRED')
    r=rows[0]
    require(r.get('code')==CODE and r.get('stock_type')=='STOCK' and r.get('exchange_type')=='US_NASDAQ'
            and r.get('lot_size')==1 and r.get('delisting') is False and type(r.get('stock_id')) is int and r['stock_id']>0,'SECURITY_IDENTITY_MISMATCH')


def validate_actions(rows):
    # Pinned get_rehab(code) returns action fields without a code column. Its
    # identity is bound by the immutable single-symbol request and SDK query,
    # not by manufacturing a response field the protocol does not provide.
    shared.validate_actions(rows,[dict(snapshot_start=start,score_end=end) for _,_,start,end in WINDOWS])


def prior_basis(directory,inputs):
    """Resume only the unqueried suffix of the known two-successful-call stop."""
    root=Path(directory).resolve();summary=shared.read(root/'summary.json');frozen=shared.read(root/'frozen-inputs.private.json')
    process=shared.read(root/'process.private.json')
    require(summary['status']=='STOPPED_NO_RETRY' and summary['reason']=='ACTION_SECURITY_IDENTITY_MISMATCH'
        and summary['business_method_calls']==summary['business_protocol_query_calls']==2
        and summary['account_queries']==summary['order_calls']==0 and summary['windows']==[]
        and summary['sdk_version']==shared.SDK_VERSION and process['returncode']==1
        and process['bounds']['cleanup_confirmed'] is True and process['bounds']['outcome']=='EXITED','PRIOR_NOT_ELIGIBLE_FOR_UNQUERIED_SUFFIX')
    require(frozen['inputs']==inputs and frozen['requests']==requests()
        and frozen['source_identity']['docs/studies/nvda-event-price-20260930.json']==shared.digest(PLAN),'PRIOR_INPUT_IDENTITY_CHANGED')
    require({p.name for p in root.glob('*.started.private.json')}=={'01-security.started.private.json','02-actions.started.private.json'},'PRIOR_CALL_INVENTORY_CHANGED')
    responses={}
    for index,label in enumerate(('security','actions'),1):
        prefix=f'{index:02d}-{label}'
        started=shared.read(root/(prefix+'.started.private.json'));response=shared.read(root/(prefix+'.response.private.json'))
        require(started['request']==requests()[index-1] and started['attempt']==1 and response['returned_reply']['ret']==0,'PRIOR_SUCCESSFUL_REPLY_REQUIRED')
        responses[label]=response['returned_reply']['rows']
    validate_security(responses['security']);validate_actions(responses['actions'])
    files={p.name:shared.digest(p) for p in root.iterdir() if p.is_file()}
    key=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return dict(directory=str(root),files=files,identity=key,responses=responses)


def validate_bars(rows,sessions,kind):
    expected=[];ny=ZoneInfo('America/New_York')
    for session in sessions:
        if kind=='K_DAY':expected.append(session['date'])
        else:
            current=datetime.fromisoformat(session['open_utc'].replace('Z','+00:00'))
            close=datetime.fromisoformat(session['close_utc'].replace('Z','+00:00'))
            while current<close:
                current=min(current+timedelta(hours=1),close)
                expected.append(current.astimezone(ny).strftime('%Y-%m-%d %H:%M:%S'))
    observed=[]
    for row in rows:
        require(row.get('code')==CODE,'BAR_SECURITY_IDENTITY_MISMATCH')
        clock=row.get('time_key');require(type(clock) is str,'BAR_CLOCK_MISSING')
        if kind=='K_DAY':
            require(clock in (clock[:10],clock[:10]+' 00:00:00'),'DAILY_CLOCK_UNEXPECTED');observed.append(clock[:10])
        else:observed.append(clock)
        try:
            values={k:Decimal(str(row[k])) for k in ('open','high','low','close','volume')}
            require(all(v.is_finite() for v in values.values()),'NONFINITE_BAR')
            require(min(values[k] for k in ('open','high','low','close'))>0 and values['volume']>=0
                and values['volume']==values['volume'].to_integral_value(),'INVALID_BAR_PRICE_OR_VOLUME')
            require(values['low']<=min(values['open'],values['close'])<=max(values['open'],values['close'])<=values['high'],'INVALID_OHLC_GEOMETRY')
        except (KeyError,ArithmeticError) as exc:raise shared.CollectionStopped('INVALID_BAR_VALUES') from exc
    require(sorted(observed)==sorted(expected) and len(observed)==len(set(observed)),'RTH_CLOCK_COVERAGE_MISMATCH')


def collect(inputs,output,expected,*,factory=shared.open_sdk,prior=None):
    output=Path(output);calls=requests();sdk=None;responses={}
    summary=dict(status='INCOMPLETE',started_at=shared.stamp(),source_identity=expected,sdk_version=shared.SDK_VERSION,
        business_method_calls=0,business_protocol_query_calls=0,blocked_pagination_attempts=0,
        connection_and_heartbeat_messages_counted=False,account_queries=0,order_calls=0,
        windows=[],data_admission='NOT_PERFORMED',economic_runs=0,raw_redistribution_allowed=False)
    if prior:
        responses.update(prior['responses'])
        summary.update(business_method_calls=2,business_protocol_query_calls=2,reused_successful_calls=2,new_business_method_calls=0,
            prior_identity=prior['identity'],original_failure='ACTION_SECURITY_IDENTITY_MISMATCH',continuation_scope='FOUR_UNQUERIED_PRICE_REQUESTS_ONLY')
    def unchanged():
        require(identity()==expected and shared.digest(inputs['calendar_path'])==CALENDAR_HASH,'FROZEN_INPUT_CHANGED_NO_FURTHER_REQUEST')
        if prior:require(all(shared.digest(Path(prior['directory'])/name)==h for name,h in prior['files'].items()),'PRIOR_RECEIPT_CHANGED')
    try:
        unchanged()
        shared.write_new(output/'frozen-inputs.private.json',dict(inputs=inputs,requests=calls,source_identity=expected,
            response_representation='SDK_DECODED_NOT_WIRE_BYTES'))
        if prior:
            claims=Path(prior['directory']).parent/'continuation-claims';claims.mkdir(exist_ok=True)
            claim=dict(prior_identity=prior['identity'],output=str(output.resolve()),claimed_at=shared.stamp(),
                new_call_budget=4,total_call_budget=6,phase_wall_seconds=TIMEOUT_SECONDS,price_retries=0)
            shared.write_new(claims/(prior['identity']+'.private.json'),claim)
            shared.write_new(output/'continuation.private.json',dict(**claim,prior_directory=prior['directory'],prior_files=prior['files']))
        sdk=factory()
        for index,request in enumerate(calls,1):
            if prior and index<=2:continue
            unchanged();prefix=output/f'{index:02d}-{request["label"]}'
            shared.write_new(str(prefix)+'.started.private.json',dict(request=request,started_at=shared.stamp(),attempt=1))
            summary['business_method_calls']+=1;reply=None
            if prior:summary['new_business_method_calls']+=1
            try:reply=sdk.query(request)
            finally:
                summary['business_protocol_query_calls']+=sdk.protocol_calls
                summary['blocked_pagination_attempts']+=sdk.blocked_pages
                shared.write_new(str(prefix)+'.response.private.json',dict(completed_at=shared.stamp(),sdk_decoded_protocol_reply=sdk.wire_reply,
                    returned_reply=reply if reply is None else dict(ret=reply[0],rows=shared.decoded_rows(reply[1]) if reply[0]==0 else None,
                        error=reply[1] if reply[0]!=0 else None,page_req_key=reply[2] if len(reply)==3 else None)))
            require(type(reply) in (tuple,list) and len(reply)==(3 if request['method']=='request_history_kline' else 2),'UNRECOGNIZED_METHOD_REPLY')
            require(type(reply[0]) is int and reply[0]==0,'PROVIDER_RETURNED_ERROR_NO_RETRY')
            rows=shared.decoded_rows(reply[1]);responses[request['label']]=rows
            if request['label']=='security':validate_security(rows)
            elif request['label']=='actions':
                validate_actions(rows)
            else:
                require(reply[2] is None,'NEXT_PAGE_REQUIRES_NEW_SCOPE_NO_RETRY')
                require(len(rows)<=request['kwargs']['max_count'],'ROW_BUDGET_EXCEEDED')
                quarter=request['quarter'];kind=request['kwargs']['ktype']
                validate_bars(rows,inputs['calendars'][quarter]['sessions'],kind)
                if kind=='K_60M':summary['windows'].append(shared.window_summary(quarter,responses[quarter+'-K_DAY'],rows))
        unchanged();summary['status']='QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION'
    except Exception as exc:
        summary.update(status='STOPPED_NO_RETRY',reason=str(exc) if isinstance(exc,shared.CollectionStopped) else 'UNEXPECTED_ERROR_PRIVATE_DETAILS_RETAINED')
        shared.write_new(output/'failure.private.json',dict(error_type=type(exc).__name__,error=str(exc)))
    finally:
        if sdk is not None:
            try:sdk.close()
            except Exception:
                summary.update(status='STOPPED_NO_RETRY',reason='CONNECTION_CLEANUP_FAILED')
    summary['finished_at']=shared.stamp();shared.write_new(output/'summary.json',summary)
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calendar-original',required=True,type=Path)
    parser.add_argument('--execute-read-only',action='store_true')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--continue-from',type=Path,help='Use the two successful metadata replies of the preserved parser stop; never query them again.')
    parser.add_argument('--expected-prior-identity')
    parser.add_argument('--owned-worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--expected-source',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.owned_worker:shared.verify_worker()
    inputs=prepare(args.calendar_original)
    prior=prior_basis(args.continue_from,inputs) if args.continue_from else None
    if not args.execute_read_only:
        print(json.dumps(dict(status='OFFLINE_READY_NO_CONNECTION',identity=identity(),requests=requests()[2:] if prior else requests(),budget=inputs['plan']['budget'],
            prior_identity=prior['identity'] if prior else None,new_call_budget=4 if prior else 6,phase_wall_seconds=TIMEOUT_SECONDS)));return 0
    require(args.output_dir is not None,'NEW_OUTPUT_DIRECTORY_REQUIRED');output=args.output_dir.resolve()
    require(output.is_relative_to(ROOT/'artifacts') and output!=ROOT/'artifacts','PRIVATE_ARTIFACT_DIRECTORY_REQUIRED')
    if prior:require(args.expected_prior_identity==prior['identity'],'EXACT_PRIOR_IDENTITY_REQUIRED')
    if args.owned_worker:
        expected=json.loads(args.expected_source);require(identity()==expected,'SOURCE_CHANGED_BEFORE_CONNECTION')
        shared.network_guard()
        result=collect(inputs,output,expected,prior=prior)
        return 0 if result['status']=='QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION' else 1
    output.mkdir(parents=True,exist_ok=False)
    from tools.observation_job import execute
    arguments=[sys.executable,'-B',str(Path(__file__).resolve()),'--calendar-original',str(args.calendar_original.resolve()),
        '--execute-read-only','--output-dir',str(output),'--owned-worker','--expected-source',json.dumps(identity())]
    if prior:arguments+=['--continue-from',prior['directory'],'--expected-prior-identity',prior['identity']]
    result=execute(arguments,
        ROOT,timeout_seconds=TIMEOUT_SECONDS,output_limit_bytes=shared.OUTPUT_LIMIT)
    for name in ('stdout','stderr'):(output/(name+'.private.log')).write_text(getattr(result,name),encoding='utf-8')
    shared.write_new(output/'process.private.json',dict(returncode=result.returncode,bounds=result.bounds))
    print(json.dumps(dict(returncode=result.returncode,outcome=result.bounds['outcome'],cleanup_confirmed=result.bounds['cleanup_confirmed'])))
    return result.returncode or (0 if result.bounds['outcome']=='EXITED' and result.bounds['cleanup_confirmed'] else 1)


if __name__=='__main__':raise SystemExit(main())
