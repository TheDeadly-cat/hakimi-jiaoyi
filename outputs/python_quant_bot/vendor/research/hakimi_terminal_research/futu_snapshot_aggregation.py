"""Existing RTH aggregation adapter; canonical snapshot validation stays shared."""
import base64,csv,io
from copy import deepcopy
from datetime import date
from decimal import Decimal
from . import futu_quote_contract as contract
from .equity_dataset import build_equity_snapshot

def source(name,reference,raw,at):
    return dict(name=name,reference=reference,raw_base64=base64.b64encode(raw).decode('ascii'),retrieved_at=at)

def build(quarter,inputs,daily,hours,security_raw,actions_raw,calendar_raw,retrieved_at,*,synthetic=False):
    require=contract.require;shared=contract
    q,_,start,end=next(w for w in contract.WINDOWS if w[0]==quarter)
    calendar=deepcopy(inputs['calendars'][q]);sessions=calendar['sessions']
    contract.validate_bars(daily,sessions,'K_DAY');contract.validate_bars(hours,sessions,'K_60M')
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
