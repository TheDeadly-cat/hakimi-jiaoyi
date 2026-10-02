"""Build private canonical RTH snapshots from the retained six-call collection.

No connection or economics. Daily provider bars are cross-check evidence;
snapshot OHLCV is consistently aggregated from the requested RTH hour bars.
Unexplained provider daily/hour volume differences remain explicit.
"""
from __future__ import annotations
import argparse
import base64
from copy import deepcopy
from datetime import date
from decimal import Decimal
import io
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools import collect_nvda_event_inputs as collection
from hakimi_research.equity_dataset import build_equity_snapshot,save_equity_snapshot,load_equity_snapshot
from hakimi_research.equity_cli import _deny_network


def source(name,reference,raw,at):
    return dict(name=name,reference=reference,raw_base64=base64.b64encode(raw).decode('ascii'),retrieved_at=at)


def build(quarter,inputs,daily,hours,security_raw,actions_raw,calendar_raw,retrieved_at,*,synthetic=False):
    require=collection.require;shared=collection.shared
    q,_,start,end=next(w for w in collection.WINDOWS if w[0]==quarter)
    calendar=deepcopy(inputs['calendars'][q]);sessions=calendar['sessions']
    collection.validate_bars(daily,sessions,'K_DAY');collection.validate_bars(hours,sessions,'K_60M')
    comparison=shared.crosscheck(daily,hours)
    require(comparison['daily_RTH_OHLC_mismatch_sessions']==0,'DAILY_RTH_PRICE_MISMATCH_NO_SNAPSHOT')
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['session_date','open','high','low','close','volume'])
    for s in sessions:
        group=sorted([r for r in hours if r['time_key'][:10]==s['date']],key=lambda r:r['time_key'])
        writer.writerow([s['date'],str(group[0]['open']),str(max(Decimal(str(r['high'])) for r in group)),
            str(min(Decimal(str(r['low'])) for r in group)),str(group[-1]['close']),str(sum(Decimal(str(r['volume'])) for r in group))])
    raw_csv=stream.getvalue().encode('utf-8')
    days=calendar['days']
    for d in days:
        if d['kind']=='OPEN':d['early_close']=False
        else:d['reason']='WEEKEND' if date.fromisoformat(d['date']).weekday()>=5 else 'HOLIDAY'
    manifest=dict(schema_version='us-equity-daily-import-v1',
        security=dict(security_id='SYNTHETIC:NVDA:COMMON' if synthetic else 'US:COMMON:NASDAQ:NVDA',symbol='NVDA',exchange='XNAS',currency='USD',instrument_type='COMMON_STOCK'),
        identity=dict(stable_within_coverage=True,valid_from=start,valid_through=end,
            selection_basis='Two user-selected previously seen NVIDIA fiscal events; bounded importer identity declaration from issuer releases and current Futu metadata, not authenticated historical reference data.',
            source=source('Futu single-symbol stock metadata','https://openapi.futunn.com/futu-api-doc/quote/get-stock-basicinfo.html',security_raw,retrieved_at)),
        calendar=dict(timezone='America/New_York',coverage_start=start,coverage_end=end,days=days,
            source=source('Retained Nasdaq 2023 trading calendar',inputs['plan']['calendar']['source'],calendar_raw,inputs['plan']['calendar']['retrieved_at'])),
        corporate_actions=dict(coverage_start=start,coverage_end=end,coverage_status='DECLARED_COMPLETE',actions=[],
            source=source('Futu get_rehab full response; no reported action in this fixed window','https://openapi.futunn.com/futu-api-doc/quote/get-rehab.html',actions_raw,retrieved_at)),
        price_source=source('Derived Futu RAW RTH K60M session OHLCV; private lineage binds original responses','urn:hakimi:nvda-rth-hour-aggregation:'+q,raw_csv,retrieved_at),
        price_basis='RAW_UNADJUSTED',volume_unit='shares',bar_timestamp_semantics='SESSION_DATE',completed_bars_only=True,
        as_of=retrieved_at,retrieved_at=retrieved_at,bar_availability_lag_seconds=60,
        evidence_kind='SYNTHETIC_TEST' if synthetic else 'IMPORTED_UNVERIFIED')
    return build_equity_snapshot(raw_csv,manifest),comparison


def prepare(first,continuation,calendar_path,output):
    shared=collection.shared;require=collection.require;first=Path(first);continuation=Path(continuation);output=Path(output)
    inputs=collection.prepare(calendar_path);prior=collection.prior_basis(first,inputs)
    link=shared.read(continuation/'continuation.private.json');summary=shared.read(continuation/'summary.json');process=shared.read(continuation/'process.private.json')
    require(link['prior_identity']==prior['identity'] and link['prior_files']==prior['files'],'CONTINUATION_BINDING_CHANGED')
    require(summary['status']=='QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION' and summary['business_method_calls']==summary['business_protocol_query_calls']==6
        and summary['new_business_method_calls']==4 and summary['reused_successful_calls']==2 and summary['account_queries']==summary['order_calls']==0
        and process['returncode']==0 and process['bounds']['outcome']=='EXITED' and process['bounds']['cleanup_confirmed'] is True,'COLLECTION_COMPLETION_NOT_PROVEN')
    response_files=[first/'01-security.response.private.json',first/'02-actions.response.private.json']
    prices={}
    for i,request in enumerate(collection.requests()[2:],3):
        prefix=f'{i:02d}-{request["label"]}'
        started=shared.read(continuation/(prefix+'.started.private.json'));path=continuation/(prefix+'.response.private.json');response=shared.read(path)
        require(started['request']==request and started['attempt']==1 and response['returned_reply']['ret']==0 and response['returned_reply']['page_req_key'] is None,'PRICE_REQUEST_OR_REPLY_CHANGED')
        prices[request['label']]=response;response_files.append(path)
    input_hashes={str(p.resolve()):shared.digest(p) for p in response_files+[Path(calendar_path)]}
    output.mkdir(parents=True,exist_ok=False);results=[]
    for q,_,start,end in collection.WINDOWS:
        daily=prices[q+'-K_DAY']['returned_reply']['rows'];hours=prices[q+'-K_60M']['returned_reply']['rows']
        snap,comparison=build(q,inputs,daily,hours,response_files[0].read_bytes(),response_files[1].read_bytes(),
            Path(calendar_path).read_bytes(),prices[q+'-K_60M']['completed_at'])
        p=save_equity_snapshot(snap,output/q);verified=load_equity_snapshot(p)
        require(verified.snapshot_id==snap.snapshot_id and verified.document['research_admission']['allowed'],'CANONICAL_SNAPSHOT_IMPORT_REJECTED')
        results.append(dict(fiscal_quarter=q,snapshot_id=snap.snapshot_id,snapshot_file=str(p.resolve()),sessions=8,
            start=start,end=end,**comparison,volume_basis='SUM_OF_SEVEN_DECLARED_RTH_HOUR_BARS',
            daily_volume_difference_reason='UNVERIFIED_DO_NOT_ASSUME_EXTENDED_HOURS',
            canonical_importer_contract='PASS_UNDER_BOUNDED_DECLARATIONS',external_truth_verified=False,economic_execution_allowed=False))
    require(all(shared.digest(p)==h for p,h in input_hashes.items()),'INPUT_CHANGED_DURING_IMPORT')
    receipt=dict(schema_version='nvda-rth-snapshot-preparation-v1',input_sha256=input_hashes,source_sha256=shared.digest(__file__),
        plan_sha256=shared.digest(collection.PLAN),snapshots=results,provider_calls=0,account_queries=0,economic_runs=0,
        limitations=['Provider historical identity and action completeness are bounded importer declarations','Daily and RTH hour volume differ; no volume-based signal or liquidity evidence','Publication-clock binding and human semantic approval remain separate'])
    shared.write_new(output/'lineage.private.json',receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('first','continuation','calendar-original','output-dir'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args();sys.addaudithook(_deny_network)
    # Network calls are neither required nor implemented by this offline import.
    data=prepare(args.first,args.continuation,args.calendar_original,args.output_dir)
    print(json.dumps(dict(status='PRIVATE_SNAPSHOTS_PREPARED',snapshots=[{'fiscal_quarter':r['fiscal_quarter'],'snapshot_id':r['snapshot_id']} for r in data['snapshots']],economic_runs=0)))
    return 0


if __name__=='__main__':raise SystemExit(main())
