"""Offline Futu receipt validation extracted from the existing bounded collector.

No SDK, connection, credentials or order methods are imported here.
"""
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

CODE='US.NVDA'
WINDOWS=(('2024Q1','2023-05-24','2023-05-22','2023-06-01'),('2024Q2','2023-08-23','2023-08-21','2023-08-30'))
class CollectionStopped(ValueError): pass
def require(ok, reason):
    if not ok: raise CollectionStopped(reason)

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
