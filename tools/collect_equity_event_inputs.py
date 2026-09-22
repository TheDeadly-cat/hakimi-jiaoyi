"""One fixed AMD quote-only collection: 22 calls, one page each, no retries.

Default is an offline input check. --execute-read-only requires a new private
artifacts directory and runs inside the existing Windows Job boundary. SDK
decoded responses are retained privately; this is not data admission or an
order/account tool. Source identity is frozen before any connection.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SDK_VERSION = '10.7.6708'
TIMEOUT_SECONDS = 600  # existing Job ceiling; within the authorized 20 minutes
OUTPUT_LIMIT = 131072
PLAN_SHA256 = 'd64bc075237fb1ef115276f20b45e3210c61f923e124056aee6e23951d043072'
PREPARED_SHA256 = 'a8e575f5ab0d0008828863f5c31b433dcc50ede8e098a9622a932ec9d4734a5b'
PRE_REPAIR_SOURCE_SHA256 = 'edc45032979e7b2c7c7141c60340accff17da713825ded3674156447c1430fbc'
PRE_CROSSCHECK_SOURCE_SHA256 = 'd14b92a0f7ef19258dd6e8ccff2c601ac49724a519a8f11f186d91ef2df50d8a'
CALENDAR_SHA256 = dict(zip(
    ('2022Q1','2022Q2','2022Q3','2022Q4','2023Q1','2023Q2','2023Q3','2023Q4','2024Q1','2024Q2'),
    ('640271d05168aea5be8eff9632abded884f0d5c9995262a985e1d7f718b120b9',
     '1af65005c028ed041f1e6bc209dcd70b1bcf433f95e3dd988856922d7a301678',
     '5d20bd07f3c45dd6b2af6b764526c1fa6dbd25e44b22a9943002e7bf9d158d2a',
     '7cb11faa5952c7ce55d7c50de05fa11b4bdf0eb45ecfd0450380579d450d81a9',
     '315d707b6d78ffc97cc6bbb682bdda523a6d811552dfce43b0c9b34f8b15c536',
     'ff4c34b3ff158df00b61813251d2fd80edaeceae7909b4955c569e06a5e773ec',
     '9db1e810f6ecf83ea0e3f1c24514bf22aa27e086dbebe07a6ce90ac355745719',
     '520c5c0460e0e429b77b830880f3167babde2a70c24b5d2d73f844425abab4b7',
     '9ad2748dd11c37d2c298b8316f1a4fb177be7d208b14172a7010f200e0be4c39',
     '57a604d9189cda8caef655699ea7b266082b99e304a90b510295222396df0ce0')))


class CollectionStopped(RuntimeError):
    pass


def stamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in
            ('collect_equity_event_inputs.py', 'observation_job.py')}


def read(path):
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise CollectionStopped('INPUT_SIZE_LIMIT')
    return json.loads(raw)


def retained(value):
    """Retain SDK decoded values, including binary page keys and nonfinite data."""
    if isinstance(value, bytes):return {'bytes_base64': base64.b64encode(value).decode('ascii')}
    if isinstance(value, float) and not math.isfinite(value):return {'nonfinite_float': str(value)}
    if isinstance(value, dict):return {str(k): retained(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):return [retained(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):return value
    raise CollectionStopped('UNRECOGNIZED_SDK_VALUE_TYPE')


def write_new(path, value):
    raw = json.dumps(retained(value), ensure_ascii=True, allow_nan=False, indent=2).encode('utf-8')
    if len(raw) > 4 * 1024 * 1024:raise CollectionStopped('PRIVATE_RESPONSE_SIZE_LIMIT')
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def load_inputs():
    plan_path = ROOT / 'docs/research-evidence/equity-events-20260920/plan.json'
    prepared_path = plan_path.with_name('prepared-inputs.json')
    if digest(plan_path) != PLAN_SHA256 or digest(prepared_path) != PREPARED_SHA256:
        raise CollectionStopped('FROZEN_PLAN_OR_PREPARED_INPUT_CHANGED')
    plan, prepared = read(plan_path), read(prepared_path)
    if (prepared['frozen_plan_sha256'] != PLAN_SHA256 or len(prepared['events']) != 10
            or prepared['max_provider_calls'] != 22 or prepared['provider_pages_per_call'] != 1
            or prepared['max_total_K60M_rows'] != 2654 or prepared['max_total_K_DAY_rows'] != 380):
        raise CollectionStopped('FROZEN_BUDGET_MISMATCH')
    calendars, files = {}, {str(plan_path): PLAN_SHA256, str(prepared_path): PREPARED_SHA256}
    for event in prepared['events']:
        quarter = event['fiscal_quarter']
        path = ROOT / 'artifacts/equity-events-20260920/prepared-inputs' / quarter / 'calendar.private.json'
        if digest(path) != CALENDAR_SHA256[quarter]:raise CollectionStopped('FROZEN_CALENDAR_CHANGED')
        files[str(path)] = CALENDAR_SHA256[quarter]
        calendar = read(path)
        sessions = [d for d in calendar['days'] if d['kind'] == 'OPEN']
        if (calendar['timezone'] != 'America/New_York' or len(sessions) != 38
                or sessions[0]['date'] != event['snapshot_start'] or sessions[-1]['date'] != event['score_end']):
            raise CollectionStopped('CALENDAR_WINDOW_MISMATCH')
        calendars[quarter] = sessions
    for document in prepared['calendar_originals']:
        path = ROOT / 'artifacts/equity-events-20260920/public-originals' / document['file']
        if digest(path) != document['sha256']:raise CollectionStopped('CALENDAR_ORIGINAL_CHANGED')
        files[str(path)] = document['sha256']
    return dict(plan=plan, prepared=prepared, calendars=calendars, files=files)


def frozen_requests(inputs):
    result = [dict(label='security', method='get_stock_basicinfo', kwargs=dict(market='US', stock_type='STOCK', code_list=['US.AMD'])),
              dict(label='actions', method='get_rehab', kwargs=dict(code='US.AMD'))]
    for event in inputs['prepared']['events']:
        for kind, count in (('K_DAY', 38), ('K_60M', event['max_K60M_rows'])):
            result.append(dict(label=event['fiscal_quarter']+'-'+kind, quarter=event['fiscal_quarter'],
                method='request_history_kline', kwargs=dict(code='US.AMD', start=event['snapshot_start'],
                end=event['score_end'], ktype=kind, autype='None', max_count=count,
                page_req_key=None, extended_time=False, session='RTH')))
    if len(result) != 22:raise CollectionStopped('REQUEST_BUDGET_CHANGED')
    return result


def decoded_rows(value):
    if type(value) is list:return value  # offline fixtures
    if hasattr(value, 'to_json'):return json.loads(value.to_json(orient='records', double_precision=15))
    raise CollectionStopped('SDK_DATAFRAME_REQUIRED')


def validate_security(rows):
    if (len(rows) != 1 or rows[0].get('code') != 'US.AMD' or rows[0].get('stock_id') != 205816
            or rows[0].get('stock_type') != 'STOCK' or rows[0].get('exchange_type') != 'US_NASDAQ'
            or rows[0].get('lot_size') != 1 or rows[0].get('delisting') is not False):
        raise CollectionStopped('SECURITY_IDENTITY_MISMATCH')


def validate_actions(rows, events):
    """SDK RequestRehab only populates columns selected by companyActFlag.

    DataFrame columns for other action types are null. Preserve those nulls;
    validate the date, mandatory factors and every actually reported action
    group. No field is defaulted to zero or used to prove provider completeness.
    """
    if len(rows) > 1000:raise CollectionStopped('ACTION_RESPONSE_LIMIT')
    factors=('forward_adj_factorA','forward_adj_factorB','backward_adj_factorA','backward_adj_factorB')
    groups=(('split_base','split_ert','split_ratio'),('join_base','join_ert','split_ratio'),
        ('per_cash_div',),('special_dividend',),('bonus_base','bonus_ert','per_share_div_ratio'),
        ('transfer_base','transfer_ert','per_share_trans_ratio'),
        ('allot_base','allot_ert','allotment_ratio','allotment_price'),
        ('add_base','add_ert','stk_spo_ratio','stk_spo_price'),
        ('spin_off_base','spin_off_ert','spin_off_ratio'))
    for action in rows:
        try:
            day=datetime.strptime(action['ex_div_date'],'%Y-%m-%d').date().isoformat()
            if not all(Decimal(str(action[k])).is_finite() for k in factors):raise ValueError('mandatory factors')
            applicable=[]
            for group in groups:
                trigger=group[:2] if group[0] in {'split_base','join_base'} else group
                if any(action.get(k) is not None for k in trigger):
                    if not all(Decimal(str(action[k])).is_finite() for k in group):raise ValueError('partial action group')
                    applicable.append(group)
            if not applicable:raise ValueError('no identified action group')
        except Exception as exc:raise CollectionStopped('ACTION_COVERAGE_UNKNOWN') from exc
        if any(e['snapshot_start'] <= day <= e['score_end'] for e in events):
            raise CollectionStopped('WINDOW_CONTAINS_UNSUPPORTED_CORPORATE_ACTION')


def prior_basis(directory, inputs):
    """Only the specifically identified two-call parser failure can continue."""
    root=Path(directory).resolve()
    names=('summary.json','frozen-inputs.private.json','process.private.json',
        '01-security.started.private.json','01-security.response.private.json',
        '02-actions.started.private.json','02-actions.response.private.json','failure.private.json')
    files={name:digest(root/name) for name in names}
    summary=read(root/'summary.json');frozen=read(root/'frozen-inputs.private.json');process=read(root/'process.private.json')
    if (summary.get('status')!='STOPPED_NO_RETRY' or summary.get('reason')!='ACTION_COVERAGE_UNKNOWN'
            or summary.get('business_method_calls')!=2 or summary.get('business_protocol_query_calls')!=2
            or summary.get('observed_K_DAY_rows')!=0 or summary.get('observed_K60M_rows')!=0
            or summary.get('windows')!=[] or summary.get('account_queries')!=0 or summary.get('order_calls')!=0
            or summary.get('plan_sha256')!=PLAN_SHA256 or summary.get('prepared_inputs_sha256')!=PREPARED_SHA256
            or summary.get('sdk_version')!=SDK_VERSION or process.get('returncode')!=1
            or process['bounds'].get('outcome')!='EXITED' or process['bounds'].get('cleanup_confirmed') is not True
            or frozen.get('source_sha256')!=summary['source_file_sha256']
            or frozen['source_sha256'].get('collect_equity_event_inputs.py')!=PRE_REPAIR_SOURCE_SHA256
            or frozen.get('requests')!=frozen_requests(inputs)
            or frozen.get('files')!=inputs['files']):
        raise CollectionStopped('PRIOR_COLLECTION_NOT_ELIGIBLE_FOR_ONE_CONTINUATION')
    if ({p.name for p in root.glob('??-*.started.private.json')}!=set(names[3:7:2])
            or {p.name for p in root.glob('??-*.response.private.json')}!=set(names[4:7:2])):
        raise CollectionStopped('PRIOR_CALL_INVENTORY_EXCEEDS_TWO')
    responses={}
    for index,label in enumerate(('security','actions')):
        prefix=f'{index+1:02d}-{label}'
        started=read(root/(prefix+'.started.private.json'))
        response=read(root/(prefix+'.response.private.json'))
        if (started.get('request')!=frozen_requests(inputs)[index] or started.get('attempt')!=1
                or response.get('returned_reply',{}).get('ret')!=0
                or response.get('sdk_decoded_protocol_reply',[None])[0]!=0):
            raise CollectionStopped('PRIOR_SUCCESSFUL_QUOTE_RESPONSE_REQUIRED')
        responses[label]=response['returned_reply']['rows']
    validate_security(responses['security']);validate_actions(responses['actions'],inputs['prepared']['events'])
    identity=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    origin=datetime.fromisoformat(summary['checked_at'].replace('Z','+00:00'))
    if origin.tzinfo is None:raise CollectionStopped('PRIOR_COLLECTION_CLOCK_REQUIRED')
    return dict(root=root,files=files,identity=identity,responses=responses,
        deadline=(origin+timedelta(seconds=1200)).isoformat(),original_summary=summary,successful_calls=2)


def crosscheck(daily, rows):
    grouped={}
    for row in rows:grouped.setdefault(row['time_key'][:10],[]).append(row)
    mismatches=volume_differences=0
    for day in daily:
        hours=sorted(grouped[day['time_key'][:10]],key=lambda r:r['time_key'])
        aggregate=dict(open=hours[0]['open'],close=hours[-1]['close'],
            high=max(Decimal(str(r['high'])) for r in hours),low=min(Decimal(str(r['low'])) for r in hours))
        mismatches+=any(Decimal(str(day[k]))!=Decimal(str(aggregate[k])) for k in aggregate)
        volume_differences+=Decimal(str(day['volume']))!=sum(Decimal(str(r['volume'])) for r in hours)
    return dict(daily_RTH_OHLC_mismatch_sessions=mismatches,daily_RTH_volume_difference_sessions=volume_differences)


def window_summary(quarter,daily,hours):
    comparison=crosscheck(daily,hours);matched=comparison['daily_RTH_OHLC_mismatch_sessions']==0
    return dict(fiscal_quarter=quarter,status='RAW_WINDOW_RETAINED_AWAITING_ADMISSION' if matched else 'EXCLUDED_PENDING_CROSSCHECK',
        daily_rows=len(daily),RTH_hour_rows=len(hours),daily_RTH_OHLC_match=matched,**comparison)


def crosscheck_prior_basis(directory,inputs):
    """One explicit remaining-sample continuation, never a retry of Q1/Q2."""
    root=Path(directory).resolve();link=read(root/'continuation.private.json')
    first=prior_basis(link['prior_directory'],inputs)
    claim=first['root'].parent/'collection-continuation-claims'/(first['identity']+'.private.json')
    if (link['prior_basis_sha256']!=first['identity'] or link['prior_file_sha256']!=first['files']
            or link['absolute_deadline']!=first['deadline'] or digest(claim)!=link['claim_sha256']
            or read(claim)['output_directory']!=str(root)):
        raise CollectionStopped('FIRST_CONTINUATION_CHAIN_MISMATCH')
    summary=read(root/'summary.json');frozen=read(root/'frozen-inputs.private.json');process=read(root/'process.private.json')
    if (summary.get('status')!='STOPPED_NO_RETRY' or summary.get('reason')!='DAILY_RTH_OHLC_MISMATCH'
            or summary.get('business_method_calls')!=6 or summary.get('business_protocol_query_calls')!=6
            or summary.get('new_business_method_calls')!=4 or summary.get('observed_K_DAY_rows')!=76
            or summary.get('observed_K60M_rows')!=532 or summary.get('account_queries')!=0 or summary.get('order_calls')!=0
            or summary.get('prior_basis_sha256')!=first['identity'] or summary.get('absolute_collection_deadline')!=first['deadline']
            or summary.get('source_file_sha256',{}).get('collect_equity_event_inputs.py')!=PRE_CROSSCHECK_SOURCE_SHA256
            or frozen.get('source_sha256')!=summary['source_file_sha256'] or frozen.get('files')!=inputs['files']
            or frozen.get('requests')!=frozen_requests(inputs) or process.get('returncode')!=1
            or process['bounds'].get('outcome')!='EXITED' or process['bounds'].get('cleanup_confirmed') is not True):
        raise CollectionStopped('CROSSCHECK_CONTINUATION_NOT_ELIGIBLE')
    names=['summary.json','frozen-inputs.private.json','process.private.json','continuation.private.json','failure.private.json']
    responses=dict(first['responses']);expected_starts=set();expected_responses=set()
    for index,request in enumerate(frozen_requests(inputs)[2:6],3):
        prefix=f'{index:02d}-{request["label"]}';sn=prefix+'.started.private.json';rn=prefix+'.response.private.json'
        names.extend([sn,rn]);expected_starts.add(sn);expected_responses.add(rn)
        started=read(root/sn);response=read(root/rn);returned=response.get('returned_reply',{})
        if (started.get('request')!=request or started.get('attempt')!=1 or returned.get('ret')!=0
                or returned.get('page_req_key') is not None or response.get('sdk_decoded_protocol_reply',[None])[0]!=0):
            raise CollectionStopped('PRIOR_HISTORY_RESPONSE_NOT_SUCCESSFUL_SINGLE_PAGE')
        validate_bars(returned['rows'],inputs['calendars'][request['quarter']],request['kwargs']['ktype'])
        responses[request['label']]=returned['rows']
    if ({p.name for p in root.glob('??-*.started.private.json')}!=expected_starts
            or {p.name for p in root.glob('??-*.response.private.json')}!=expected_responses):
        raise CollectionStopped('CROSSCHECK_PRIOR_CALL_INVENTORY_CHANGED')
    windows=[window_summary(q,responses[q+'-K_DAY'],responses[q+'-K_60M']) for q in ('2022Q1','2022Q2')]
    if not windows[0]['daily_RTH_OHLC_match'] or windows[1]['daily_RTH_OHLC_match']:
        raise CollectionStopped('PRIOR_CROSSCHECK_FAILURE_NOT_REPRODUCED')
    files={str(first['root']/name):sha for name,sha in first['files'].items()}
    files.update({str(root/name):digest(root/name) for name in names});files[str(claim)]=digest(claim)
    identity=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(root=root,files=files,identity=identity,responses=responses,deadline=first['deadline'],
        original_summary=summary,successful_calls=6,carried_windows=windows,
        original_failure='PRESERVED_FIRST_PARSER_FAILURE_AND_SECOND_Q2_OHLC_MISMATCH')


def seconds_remaining(prior):
    return (datetime.fromisoformat(prior['deadline'])-datetime.now(timezone.utc)).total_seconds()


def claim_continuation(prior, output):
    if seconds_remaining(prior)<=0:raise CollectionStopped('ORIGINAL_20_MINUTE_WINDOW_EXPIRED')
    # Sibling ledger: never add, replace or re-sign a file inside the first run.
    ledger=prior['root'].parent/'collection-continuation-claims'
    ledger.mkdir(exist_ok=True)
    path=ledger/(prior['identity']+'.private.json')
    write_new(path,dict(prior_basis_sha256=prior['identity'],prior_directory=str(prior['root']),
        output_directory=str(Path(output).resolve()),claimed_at=stamp(),absolute_deadline=prior['deadline'],
        prior_successful_business_calls=prior['successful_calls'],max_new_history_calls=22-prior['successful_calls'],claim_reusable=False))
    return path


def validate_bars(rows, sessions, kind):
    ny = ZoneInfo('America/New_York')
    expected = []
    for session in sessions:
        if kind == 'K_DAY':expected.append(session['date'])
        else:
            opening = datetime.fromisoformat(session['open_utc'].replace('Z','+00:00'))
            close = datetime.fromisoformat(session['close_utc'].replace('Z','+00:00'))
            end = opening
            while end < close:
                end = min(end+timedelta(hours=1), close)
                expected.append(end.astimezone(ny).strftime('%Y-%m-%d %H:%M:%S'))
    actual = []
    for row in rows:
        if row.get('code') != 'US.AMD':raise CollectionStopped('BAR_SECURITY_IDENTITY_MISMATCH')
        clock = row.get('time_key')
        if type(clock) is not str:raise CollectionStopped('BAR_CLOCK_MISSING')
        if kind == 'K_DAY':
            if clock not in {clock[:10], clock[:10]+' 00:00:00'}:raise CollectionStopped('DAILY_CLOCK_UNEXPECTED')
            actual.append(clock[:10])
        else:actual.append(clock)
        try:
            values = {field: Decimal(str(row[field])) for field in ('open','high','low','close','volume')}
            if (not all(v.is_finite() for v in values.values()) or min(values[k] for k in ('open','high','low','close')) <= 0
                    or values['volume'] < 0 or values['volume'] != values['volume'].to_integral_value()
                    or values['low'] > min(values['open'],values['close'])
                    or values['high'] < max(values['open'],values['close'])):raise ValueError()
        except Exception as exc:raise CollectionStopped('INVALID_ACTUAL_BAR_VALUES') from exc
    if sorted(actual) != sorted(expected) or len(actual) != len(set(actual)):
        raise CollectionStopped('RTH_CLOCK_COVERAGE_MISMATCH')


class SinglePageSDK:
    """Stop SDK-internal short-page pagination before it can send a second page."""
    QUERY_CLASSES = {'get_stock_basicinfo': 'StockBasicInfoQuery', 'get_rehab': 'RequestRehab',
                     'request_history_kline': 'RequestHistoryKlineQuery'}

    def __init__(self, context):
        self.context = context
        self.original = context._get_sync_query_processor
        self.active = None
        self.protocol_calls = 0
        self.blocked_pages = 0
        self.wire_reply = None
        context._get_sync_query_processor = self.processor

    def processor(self, pack, unpack):
        expected = self.QUERY_CLASSES.get(self.active)
        if expected is None or pack.__qualname__.split('.')[0] != expected:
            raise CollectionStopped('QUOTE_METHOD_OUTSIDE_FROZEN_SCOPE')
        processor = self.original(pack, unpack)
        def once(**kwargs):
            if self.protocol_calls != 0:
                self.blocked_pages += 1
                raise CollectionStopped('SDK_AUTOMATIC_PAGINATION_BLOCKED')
            self.protocol_calls += 1
            self.wire_reply = processor(**kwargs)
            if self.active == 'request_history_kline' and self.wire_reply[0] == 0:
                content = self.wire_reply[2]
                if type(content) not in (tuple, list) or len(content) != 3:
                    raise CollectionStopped('UNRECOGNIZED_HISTORY_PAGE_SHAPE')
                if content[1] or content[2] is not None:
                    self.blocked_pages += 1
                    raise CollectionStopped('NEXT_PAGE_REQUIRES_NEW_SCOPE_NO_RETRY')
            return self.wire_reply
        return once

    def query(self, request):
        self.active = request['method'];self.protocol_calls = 0;self.wire_reply = None;self.blocked_pages = 0
        if self.active not in self.QUERY_CLASSES:raise CollectionStopped('QUOTE_METHOD_OUTSIDE_FROZEN_SCOPE')
        try:return getattr(self.context, self.active)(**request['kwargs'])
        finally:self.active = None

    def close(self):self.context.close()


def open_sdk():
    if importlib.metadata.version('futu-api') != SDK_VERSION:raise CollectionStopped('PINNED_SDK_REQUIRED')
    from futu import OpenQuoteContext, SecurityFirm
    expected = ('self','code','start','end','ktype','autype','fields','max_count','page_req_key','extended_time','session')
    if tuple(inspect.signature(OpenQuoteContext.request_history_kline).parameters) != expected:
        raise CollectionStopped('PINNED_SDK_SIGNATURE_MISMATCH')
    context = OpenQuoteContext(host='127.0.0.1', port=11111, is_async_connect=True, security_firm=SecurityFirm.NONE)
    context.set_sync_query_connect_timeout(15)
    if context._query_timeout != 12:
        context.close();raise CollectionStopped('PINNED_SDK_TIMEOUT_MISMATCH')
    return SinglePageSDK(context)


def collect(inputs, output, *, factory=open_sdk, expected_source=None, prior=None):
    """No connection until immutable inputs, caller scope and private receipt exist."""
    output = Path(output)
    requests = frozen_requests(inputs)
    expected_source = expected_source or source_hashes()
    result = dict(status='INCOMPLETE', checked_at=stamp(), plan_sha256=PLAN_SHA256,
        prepared_inputs_sha256=PREPARED_SHA256, sdk_version=SDK_VERSION,
        business_method_calls=0, business_protocol_query_calls=0, blocked_pagination_attempts=0,
        sdk_connection_and_heartbeat_messages_counted=False, max_business_method_calls=22,
        max_wall_seconds=TIMEOUT_SECONDS, authorized_max_wall_seconds=1200,
        observed_K_DAY_rows=0, observed_K60M_rows=0, windows=[],
        account_queries=0, order_calls=0, raw_redistribution_allowed=False,
        data_admission='NOT_PERFORMED', corporate_action_completeness='NOT_INDEPENDENTLY_VERIFIED')
    start = time.monotonic();sdk = None;responses = {}
    if prior:
        used=prior['successful_calls']
        result.update(business_method_calls=used,business_protocol_query_calls=used,
            prior_successful_business_calls=used,new_business_method_calls=0,max_new_history_calls=22-used,
            observed_K_DAY_rows=prior['original_summary']['observed_K_DAY_rows'],
            observed_K60M_rows=prior['original_summary']['observed_K60M_rows'],windows=list(prior.get('carried_windows',[])),
            original_failure=prior.get('original_failure','ACTION_COVERAGE_UNKNOWN_PARSER_REQUIRED_INAPPLICABLE_FIELDS'),
            prior_basis_sha256=prior['identity'],absolute_collection_deadline=prior['deadline'],
            original_source_sha256=prior['original_summary']['source_file_sha256'])
        responses.update(prior['responses'])
    def unchanged():
        if source_hashes() != expected_source or any(digest(p) != h for p,h in inputs['files'].items()):
            raise CollectionStopped('SOURCE_OR_INPUT_CHANGED_NO_FURTHER_REQUEST')
        if time.monotonic()-start >= TIMEOUT_SECONDS:raise CollectionStopped('WALL_TIME_BUDGET_EXHAUSTED')
        if prior:
            if any(digest(prior['root']/p)!=h for p,h in prior['files'].items()):
                raise CollectionStopped('PRIOR_COLLECTION_RECEIPT_CHANGED')
            if seconds_remaining(prior)<=0:raise CollectionStopped('ORIGINAL_20_MINUTE_WINDOW_EXPIRED')
    try:
        unchanged()
        write_new(output/'frozen-inputs.private.json', dict(files=inputs['files'], source_sha256=expected_source,
            requests=requests, checked_at=stamp(), response_representation='SDK_DECODED_NOT_WIRE_BYTES'))
        if prior:
            claim=claim_continuation(prior,output)
            write_new(output/'continuation.private.json',dict(prior_directory=str(prior['root']),
                prior_file_sha256=prior['files'],prior_basis_sha256=prior['identity'],claim_sha256=digest(claim),
                absolute_deadline=prior['deadline'],reused_successful_calls=prior['successful_calls'],max_new_history_calls=22-prior['successful_calls']))
        sdk = factory()
        for number, request in enumerate(requests, 1):
            if prior and number<=prior['successful_calls']:continue
            unchanged()
            prefix = output/f'{number:02d}-{request["label"]}'
            write_new(str(prefix)+'.started.private.json', dict(request=request, started_at=stamp(), attempt=1))
            result['business_method_calls'] += 1
            if prior:result['new_business_method_calls'] += 1
            reply = None
            try:
                reply = sdk.query(request)
            finally:
                result['business_protocol_query_calls'] += sdk.protocol_calls
                result['blocked_pagination_attempts'] += sdk.blocked_pages
                write_new(str(prefix)+'.response.private.json', dict(completed_at=stamp(),
                    sdk_decoded_protocol_reply=sdk.wire_reply,
                    returned_reply=None if reply is None else dict(ret=reply[0],
                        rows=decoded_rows(reply[1]) if reply[0] == 0 else None,
                        error=reply[1] if reply[0] != 0 else None,
                        page_req_key=reply[2] if len(reply) == 3 else None)))
            if type(reply) not in (tuple,list) or len(reply) != (3 if request['method']=='request_history_kline' else 2):
                raise CollectionStopped('UNRECOGNIZED_METHOD_REPLY')
            if type(reply[0]) is not int or reply[0] != 0:raise CollectionStopped('PROVIDER_RETURNED_ERROR_NO_RETRY')
            rows = decoded_rows(reply[1]);responses[request['label']] = rows
            if request['label'] == 'security':
                validate_security(rows)
            elif request['label'] == 'actions':
                validate_actions(rows,inputs['prepared']['events'])
                result['corporate_action_response'] = 'NO_PROVIDER_REPORTED_ACTION_IN_FIXED_WINDOWS'
            else:
                if reply[2] is not None:raise CollectionStopped('NEXT_PAGE_REQUIRES_NEW_SCOPE_NO_RETRY')
                kind = request['kwargs']['ktype'];quarter = request['quarter']
                if len(rows) > request['kwargs']['max_count']:raise CollectionStopped('ROW_BUDGET_EXCEEDED')
                field = 'observed_K_DAY_rows' if kind == 'K_DAY' else 'observed_K60M_rows'
                result[field] += len(rows)
                validate_bars(rows, inputs['calendars'][quarter], kind)
                if kind == 'K_60M':
                    result['windows'].append(window_summary(quarter,responses[quarter+'-K_DAY'],rows))
        unchanged()
        result['status'] = 'FIXED_QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION'
    except Exception as exc:
        result.update(status='STOPPED_NO_RETRY', reason=str(exc) if isinstance(exc,CollectionStopped) else 'UNEXPECTED_ERROR_PRIVATE_DETAILS_RETAINED')
        write_new(output/'failure.private.json', dict(error_type=type(exc).__name__, error=str(exc), checked_at=stamp()))
    finally:
        if sdk is not None:sdk.close()
    result['finished_at'] = stamp()
    result['elapsed_seconds'] = time.monotonic()-start
    result['source_file_sha256'] = expected_source
    write_new(output/'summary.json', result)
    return result


def network_guard():
    listeners = []
    def guard(event,args):
        if event=='socket.bind' and args[1]==('127.0.0.1',0):listeners.append(args[0])
        if event=='socket.connect' and args[1]!=('127.0.0.1',11111):
            owned=False
            for listener in listeners:
                try:owned |= listener.fileno()>=0 and listener.getsockname()==args[1] and bool(listener.getsockopt(socket.SOL_SOCKET,socket.SO_ACCEPTCONN))
                except OSError:pass
            if not owned:raise CollectionStopped('NETWORK_OUTSIDE_OPEND_OR_OWNED_LISTENER')
        if event=='socket.getaddrinfo' and (args[0]!='127.0.0.1' or args[1]!=11111):
            raise CollectionStopped('NETWORK_RESOLUTION_OUTSIDE_FIXED_OPEND')
    sys.addaudithook(guard)


def verify_worker():
    if os.name!='nt':raise CollectionStopped('OWNED_WINDOWS_JOB_REQUIRED')
    try:
        owner=int(os.environ['HAKIMI_OWNED_JOB_PARENT_PID']);handle=int(os.environ['HAKIMI_OWNED_JOB_HANDLE'])
        remaining=float(os.environ['HAKIMI_OWNED_JOB_DEADLINE'])-time.monotonic()
        limit=int(os.environ['HAKIMI_OWNED_JOB_OUTPUT_LIMIT'])
    except (KeyError,ValueError) as exc:raise CollectionStopped('PARENT_OWNED_JOB_ATTESTATION_REQUIRED') from exc
    if owner<=0 or handle<=0 or not 0<remaining<=TIMEOUT_SECONDS or limit!=OUTPUT_LIMIT:
        raise CollectionStopped('PARENT_OWNED_JOB_BOUNDS_INVALID')
    import ctypes as c
    from ctypes import wintypes as w
    api=c.WinDLL('kernel32',use_last_error=True)
    for name,args,ret in (
        ('OpenProcess',[w.DWORD,w.BOOL,w.DWORD],w.HANDLE),('GetCurrentProcess',[],w.HANDLE),
        ('DuplicateHandle',[w.HANDLE,w.HANDLE,w.HANDLE,c.POINTER(w.HANDLE),w.DWORD,w.BOOL,w.DWORD],w.BOOL),
        ('IsProcessInJob',[w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)],w.BOOL),('CloseHandle',[w.HANDLE],w.BOOL)):
        getattr(api,name).argtypes=args;getattr(api,name).restype=ret
    parent=api.OpenProcess(0x0040,False,owner);duplicate=w.HANDLE()
    try:
        if not parent or not api.DuplicateHandle(parent,handle,api.GetCurrentProcess(),c.byref(duplicate),0x0004,False,0):
            raise CollectionStopped('LIVE_PARENT_OWNED_JOB_REQUIRED')
        belongs=w.BOOL()
        if not api.IsProcessInJob(api.GetCurrentProcess(),duplicate,c.byref(belongs)) or not belongs.value:
            raise CollectionStopped('WORKER_NOT_IN_PARENT_JOB')
    finally:
        if duplicate:api.CloseHandle(duplicate)
        if parent:api.CloseHandle(parent)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-read-only',action='store_true')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--continue-from',type=Path,help='Reuse the two successful receipts from the preserved first parser failure, once only.')
    parser.add_argument('--continue-after-crosscheck',type=Path,help='After the preserved six-call Q2 mismatch, request only the eight untouched fixed windows, once.')
    parser.add_argument('--expected-prior-sha256',help='Exact prior basis returned by the offline continuation check.')
    parser.add_argument('--owned-worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--expected-source',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.owned_worker:verify_worker()
    inputs=load_inputs()
    if args.continue_from and args.continue_after_crosscheck:raise CollectionStopped('ONE_EXPLICIT_CONTINUATION_KIND_REQUIRED')
    prior=(crosscheck_prior_basis(args.continue_after_crosscheck,inputs) if args.continue_after_crosscheck else
        prior_basis(args.continue_from,inputs) if args.continue_from else None)
    if prior and args.execute_read_only and args.expected_prior_sha256!=prior['identity']:
        raise CollectionStopped('EXPLICIT_PRIOR_RECEIPT_IDENTITY_REQUIRED')
    if not args.execute_read_only:
        report=dict(status='OFFLINE_INPUTS_VERIFIED_NO_CONNECTION',plan_sha256=PLAN_SHA256,
            prepared_sha256=PREPARED_SHA256,calls=22-prior['successful_calls'] if prior else 22,max_K60M_rows=2654,max_K_DAY_rows=380)
        if prior:report.update(prior_basis_sha256=prior['identity'],absolute_deadline=prior['deadline'],seconds_remaining=seconds_remaining(prior))
        print(json.dumps(report))
        return 0
    if args.output_dir is None:parser.error('--execute-read-only requires --output-dir')
    output=args.output_dir.resolve()
    if not output.is_relative_to(ROOT/'artifacts') or output==ROOT/'artifacts':
        raise CollectionStopped('NEW_WORKSPACE_ARTIFACT_DIRECTORY_REQUIRED')
    if args.owned_worker:
        expected=json.loads(args.expected_source)
        if source_hashes()!=expected:raise CollectionStopped('SOURCE_CHANGED_BEFORE_CONNECTION')
        with (output/'worker-start.private.json').open('x') as stream:
            json.dump(dict(checked_at=stamp(),parent_owned_job_verified=True),stream)
        os.environ['APPDATA']=str(output/'sdk-private-logs')
        network_guard()
        result=collect(inputs,output,expected_source=expected,prior=prior)
        print(json.dumps({k:result[k] for k in ('status','business_method_calls','business_protocol_query_calls','blocked_pagination_attempts','order_calls','account_queries')}))
        return 0 if result['status']=='FIXED_QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION' else 1
    output.mkdir(parents=True,exist_ok=False)
    expected=source_hashes()
    write_new(output/'launch.private.json',dict(checked_at=stamp(),source_sha256=expected))
    spec=importlib.util.spec_from_file_location('equity_collection_job',Path(__file__).with_name('observation_job.py'))
    job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
    argv=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--execute-read-only',
        '--output-dir',str(output),'--owned-worker','--expected-source',json.dumps(expected)]
    timeout=TIMEOUT_SECONDS
    if prior:
        timeout=min(TIMEOUT_SECONDS,seconds_remaining(prior))
        if timeout<=0:raise CollectionStopped('ORIGINAL_20_MINUTE_WINDOW_EXPIRED')
        flag='--continue-after-crosscheck' if args.continue_after_crosscheck else '--continue-from'
        argv.extend([flag,str(prior['root']),'--expected-prior-sha256',prior['identity']])
    result=job.execute(argv,ROOT,timeout_seconds=timeout,output_limit_bytes=OUTPUT_LIMIT,cleanup_seconds=5)
    for name in ('stdout','stderr'):
        (output/(name+'.private.log')).write_text(getattr(result,name),encoding='utf-8')
    write_new(output/'process.private.json',dict(returncode=result.returncode,bounds=result.bounds))
    print(json.dumps(dict(returncode=result.returncode,outcome=result.bounds['outcome'],cleanup_confirmed=result.bounds['cleanup_confirmed'])))
    return result.returncode or (0 if result.bounds['outcome']=='EXITED' and result.bounds['cleanup_confirmed'] else 1)


if __name__=='__main__':raise SystemExit(main())
