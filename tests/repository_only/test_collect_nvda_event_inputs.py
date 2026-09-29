"""Fictional quote replies only; never opens a broker connection."""
from copy import deepcopy
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools import collect_nvda_event_inputs as tool


def bars(sessions,kind):
    rows=[]
    for s in sessions:
        clocks=[s['date']+' 00:00:00']
        if kind=='K_60M':
            clocks=[];current=datetime.fromisoformat(s['open_utc'].replace('Z','+00:00'));end=datetime.fromisoformat(s['close_utc'].replace('Z','+00:00'))
            while current<end:
                current=min(current+timedelta(hours=1),end)
                clocks.append(current.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S'))
        for clock in clocks:rows.append(dict(code='US.NVDA',time_key=clock,open=10,high=11,low=9,close=10,volume=700 if kind=='K_DAY' else 100))
    return rows


class FakeSDK:
    def __init__(self,inputs,edit=None):self.inputs=inputs;self.edit=edit;self.seen=[];self.protocol_calls=0;self.blocked_pages=0;self.wire_reply=None;self.closed=False
    def query(self,request):
        self.seen.append(deepcopy(request));self.protocol_calls=1;self.blocked_pages=0
        if request['label']=='security':reply=[0,[dict(code='US.NVDA',stock_type='STOCK',exchange_type='US_NASDAQ',lot_size=1,delisting=False,stock_id=1234)]]
        elif request['label']=='actions':reply=[0,[]]
        else:reply=[0,bars(self.inputs['calendars'][request['quarter']]['sessions'],request['kwargs']['ktype']),None]
        if self.edit:self.edit(request,reply)
        self.wire_reply=deepcopy(reply);return reply
    def close(self):self.closed=True


class NvdaQuoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.calendar=self.root/'fictional-calendar';self.calendar.write_bytes(b'FICTIONAL TEST CALENDAR')
        h=hashlib.sha256(self.calendar.read_bytes()).hexdigest()
        m=json.loads(tool.PLAN.read_bytes());m['calendar']['sha256']=h;self.plan=self.root/'plan.json';self.plan.write_text(json.dumps(m),encoding='utf-8')
        self.enterContext(patch.object(tool,'PLAN',self.plan));self.enterContext(patch.object(tool,'CALENDAR_HASH',h))
        self.enterContext(patch.object(tool,'identity',return_value={'fictional_identity':'test'}))
        self.inputs=tool.prepare(self.calendar)
    def collect(self,edit=None):
        self.sdk=FakeSDK(self.inputs,edit);self.output=self.root/'output';self.output.mkdir()
        return tool.collect(self.inputs,self.output,tool.identity(),factory=lambda:self.sdk)

    def test_exact_six_call_budget_and_no_account_method(self):
        result=self.collect();self.assertEqual(result['status'],'QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION')
        self.assertEqual(result['business_method_calls'],6);self.assertEqual(result['business_protocol_query_calls'],6)
        self.assertEqual({r['method'] for r in self.sdk.seen},{'get_stock_basicinfo','get_rehab','request_history_kline'})
        self.assertEqual(result['account_queries'],0);self.assertEqual(result['order_calls'],0);self.assertTrue(self.sdk.closed)
        self.assertEqual(result['data_admission'],'NOT_PERFORMED');self.assertEqual(len(result['windows']),2)
        self.assertTrue(all(w['daily_RTH_OHLC_match'] for w in result['windows']))
        self.assertEqual(len(list(self.output.glob('*.response.private.json'))),6)

    def test_holiday_and_two_before_five_after_are_frozen(self):
        for quarter,event,_,_ in tool.WINDOWS:
            sessions=self.inputs['calendars'][quarter]['sessions'];self.assertEqual(len(sessions),8)
            self.assertEqual(sessions[2]['date'],event);self.assertEqual(len(sessions[3:]),5)
        may={d['date']:d for d in self.inputs['calendars']['2024Q1']['days']}
        self.assertEqual(may['2023-05-29']['kind'],'CLOSED');self.assertEqual(may['2023-05-25']['open_utc'],'2023-05-25T13:30:00Z')

    def test_changed_calendar_fails_before_connection(self):
        self.calendar.write_bytes(b'CHANGED')
        result=self.collect();self.assertEqual(result['business_method_calls'],0);self.assertEqual(self.sdk.seen,[])
        self.assertEqual(result['reason'],'FROZEN_INPUT_CHANGED_NO_FURTHER_REQUEST')

    def test_expanded_scope_fails_offline(self):
        m=json.loads(self.plan.read_bytes());m['budget']['business_calls']=7;self.plan.write_text(json.dumps(m))
        with self.assertRaisesRegex(tool.shared.CollectionStopped,'FIXED_QUOTE_BUDGET'):tool.prepare(self.calendar)

    def test_wrong_symbol_stops_after_metadata_without_retry(self):
        def edit(r,reply):
            if r['label']=='security':reply[1][0]['code']='US.OTHER'
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],1);self.assertEqual(result['reason'],'SECURITY_IDENTITY_MISMATCH')

    def test_provider_error_stops_once_and_keeps_reply(self):
        def edit(r,reply):
            if r['label']=='2024Q1-K_60M':reply[:]=[-1,'FICTIONAL_PERMISSION_ERROR',None]
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],4);self.assertEqual(result['reason'],'PROVIDER_RETURNED_ERROR_NO_RETRY')
        self.assertTrue(self.sdk.closed);self.assertIn('FICTIONAL_PERMISSION_ERROR',(self.output/'04-2024Q1-K_60M.response.private.json').read_text())

    def test_next_page_key_does_not_trigger_continuation(self):
        def edit(r,reply):
            if r['label']=='2024Q1-K_DAY':reply[2]=b'next'
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],3);self.assertEqual(result['reason'],'NEXT_PAGE_REQUIRES_NEW_SCOPE_NO_RETRY')

    def test_missing_or_duplicate_bar_stops_before_other_window(self):
        def edit(r,reply):
            if r['label']=='2024Q1-K_DAY':reply[1][-1]=reply[1][0]
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],3);self.assertEqual(result['reason'],'RTH_CLOCK_COVERAGE_MISMATCH')

    def test_nonfinite_price_is_retained_and_rejected(self):
        def edit(r,reply):
            if r['label']=='2024Q1-K_DAY':reply[1][0]['close']=float('nan')
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],3);self.assertEqual(result['reason'],'NONFINITE_BAR')
        self.assertIn('nonfinite_float',(self.output/'03-2024Q1-K_DAY.response.private.json').read_text())

    def test_mismatch_is_visible_without_replacing_window_or_admitting_data(self):
        def edit(r,reply):
            if r['label']=='2024Q1-K_DAY':reply[1][0]['close']=11
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],6)
        self.assertEqual(result['windows'][0]['status'],'EXCLUDED_PENDING_CROSSCHECK');self.assertEqual(result['data_admission'],'NOT_PERFORMED')

    def test_corporate_action_inside_window_stops_collection(self):
        def edit(r,reply):
            if r['label']=='actions':reply[1]=[dict(ex_div_date='2023-05-25',per_cash_div=0.04,forward_adj_factorA=1,forward_adj_factorB=0,backward_adj_factorA=1,backward_adj_factorB=0)]
        result=self.collect(edit);self.assertEqual(result['business_method_calls'],2);self.assertEqual(result['reason'],'WINDOW_CONTAINS_UNSUPPORTED_CORPORATE_ACTION')

    def test_action_response_without_code_column_matches_pinned_sdk_contract(self):
        def edit(r,reply):
            if r['label']=='actions':reply[1]=[dict(ex_div_date='2023-06-08',per_cash_div=0.04,forward_adj_factorA=1,forward_adj_factorB=0,backward_adj_factorA=1,backward_adj_factorB=0)]
        self.assertEqual(self.collect(edit)['business_method_calls'],6)

    def test_continuation_reuses_metadata_and_cannot_be_claimed_twice(self):
        old=self.root/'prior';old.mkdir();f=old/'summary.json';f.write_bytes(b'fictional prior receipt')
        prior=dict(directory=str(old),files={'summary.json':hashlib.sha256(f.read_bytes()).hexdigest()},identity='fictional-prior',responses={'security':[],'actions':[]})
        sdk=FakeSDK(self.inputs);out=self.root/'continuation';out.mkdir()
        result=tool.collect(self.inputs,out,tool.identity(),factory=lambda:sdk,prior=prior)
        self.assertEqual(result['business_method_calls'],6);self.assertEqual(result['new_business_method_calls'],4)
        self.assertEqual(len(sdk.seen),4);self.assertTrue(all(r['method']=='request_history_kline' for r in sdk.seen))
        other=self.root/'second-continuation';other.mkdir();second=FakeSDK(self.inputs)
        failure=tool.collect(self.inputs,other,tool.identity(),factory=lambda:second,prior=prior)
        self.assertEqual(failure['status'],'STOPPED_NO_RETRY');self.assertEqual(second.seen,[])


if __name__=='__main__':unittest.main()
