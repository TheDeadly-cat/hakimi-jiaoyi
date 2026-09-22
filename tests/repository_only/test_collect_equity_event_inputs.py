"""Quote collection bounds using synthetic bars only; never import/connect SDK."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SPEC=importlib.util.spec_from_file_location('bounded_quote_collector',Path(__file__).resolve().parents[2]/'tools/collect_equity_event_inputs.py')
collector=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(collector)


def bars(sessions,kind):
    result=[]
    for session in sessions:
        clocks=[session['date']+' 00:00:00']
        if kind=='K_60M':
            start=datetime.fromisoformat(session['open_utc'].replace('Z','+00:00'))
            end=datetime.fromisoformat(session['close_utc'].replace('Z','+00:00'));clocks=[]
            while start<end:
                start=min(start+timedelta(hours=1),end)
                clocks.append(start.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S'))
        for clock in clocks:
            result.append(dict(code='US.AMD',time_key=clock,open=10,high=12,low=9,close=11,volume=70 if kind=='K_DAY' else 10))
    return result


def fixture_inputs():
    """Synthetic calendars: tests do not need private operational files."""
    prepared=collector.read(collector.ROOT/'docs/research-evidence/equity-events-20260920/prepared-inputs.json')
    calendars={};ny=ZoneInfo('America/New_York')
    for event in prepared['events']:
        first=datetime.fromisoformat(event['snapshot_start'])
        sessions=[]
        for i in range(38):
            day=first+timedelta(days=i)
            close_hour=13 if event['max_K60M_rows']==263 and i==5 else 16
            opening=day.replace(hour=9,minute=30,tzinfo=ny).astimezone(timezone.utc)
            close=day.replace(hour=close_hour,tzinfo=ny).astimezone(timezone.utc)
            sessions.append(dict(date=day.date().isoformat(),open_utc=opening.isoformat(),close_utc=close.isoformat()))
        calendars[event['fiscal_quarter']]=sessions
    return dict(prepared=prepared,calendars=calendars,files={})


class FakeSDK:
    def __init__(self,inputs):self.inputs=inputs;self.calls=[];self.protocol_calls=0;self.blocked_pages=0;self.wire_reply=None;self.closed=False;self.error_at=None;self.page_at=None;self.mutate=None
    def query(self,request):
        self.calls.append(request);self.protocol_calls=1
        if self.mutate:self.mutate()
        if len(self.calls)==self.error_at:
            self.wire_reply=(-1,'synthetic quota failure; no retries',None)
            return (-1,'synthetic quota failure; no retries',None) if request['method']=='request_history_kline' else (-1,'synthetic failure')
        if request['label']=='security':rows=[dict(code='US.AMD',stock_id=205816,stock_type='STOCK',exchange_type='US_NASDAQ',lot_size=1,delisting=False)]
        elif request['label']=='actions':rows=[]
        else:rows=bars(self.inputs['calendars'][request['quarter']],request['kwargs']['ktype'])
        self.wire_reply=(0,'',rows)
        if request['method']=='request_history_kline':return 0,rows,b'page' if len(self.calls)==self.page_at else None
        return 0,rows
    def close(self):self.closed=True


class QuoteCollectionContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hakimi-quote-fixture-');self.addCleanup(self.tmp.cleanup)
        self.output=Path(self.tmp.name);self.inputs=fixture_inputs();self.sdk=FakeSDK(self.inputs)
    def run_collection(self):return collector.collect(self.inputs,self.output,factory=lambda:self.sdk)

    def test_frozen_inputs_and_exact_quote_only_request_budget(self):
        requests=collector.frozen_requests(self.inputs)
        self.assertEqual(len(requests),22)
        self.assertEqual({r['method'] for r in requests},{'get_stock_basicinfo','get_rehab','request_history_kline'})
        history=requests[2:]
        self.assertEqual(sum(r['kwargs']['max_count'] for r in history if r['kwargs']['ktype']=='K_DAY'),380)
        self.assertEqual(sum(r['kwargs']['max_count'] for r in history if r['kwargs']['ktype']=='K_60M'),2654)
        for r in history:
            self.assertEqual(r['kwargs']['code'],'US.AMD');self.assertEqual(r['kwargs']['session'],'RTH')
            self.assertEqual(r['kwargs']['autype'],'None');self.assertFalse(r['kwargs']['extended_time'])
            self.assertIsNone(r['kwargs']['page_req_key'])

    def test_all_fixed_windows_finish_with_private_raw_and_no_admission(self):
        result=self.run_collection()
        self.assertEqual(result['status'],'FIXED_QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION')
        self.assertEqual(result['business_method_calls'],22);self.assertEqual(result['business_protocol_query_calls'],22)
        self.assertFalse(result['sdk_connection_and_heartbeat_messages_counted'])
        self.assertEqual(result['observed_K_DAY_rows'],380);self.assertEqual(result['observed_K60M_rows'],2654)
        self.assertEqual(len(result['windows']),10);self.assertTrue(self.sdk.closed)
        self.assertEqual(result['account_queries'],0);self.assertEqual(result['order_calls'],0)
        self.assertEqual(result['data_admission'],'NOT_PERFORMED')
        self.assertEqual(len(list(self.output.glob('*.response.private.json'))),22)
        self.assertNotIn('returned_reply',result);self.assertNotIn(str(self.output),json.dumps(result))

    def test_quota_failure_retained_and_no_retry_or_next_event(self):
        self.sdk.error_at=3;result=self.run_collection()
        self.assertEqual(result['reason'],'PROVIDER_RETURNED_ERROR_NO_RETRY')
        self.assertEqual(len(self.sdk.calls),3);self.assertEqual(result['windows'],[])
        raw=json.loads((self.output/'03-2022Q1-K_DAY.response.private.json').read_text())
        self.assertEqual(raw['returned_reply']['ret'],-1)
        self.assertIn('quota',raw['returned_reply']['error'])

    def test_page_key_stops_without_following_or_retry(self):
        self.sdk.page_at=3;result=self.run_collection()
        self.assertEqual(result['reason'],'NEXT_PAGE_REQUIRES_NEW_SCOPE_NO_RETRY')
        self.assertEqual(len(self.sdk.calls),3)
        raw=json.loads((self.output/'03-2022Q1-K_DAY.response.private.json').read_text())
        self.assertEqual(raw['returned_reply']['page_req_key'],{'bytes_base64':'cGFnZQ=='})

    def test_first_unknown_exception_is_private_and_stops(self):
        self.sdk.query=mock.Mock(side_effect=TimeoutError('synthetic local private detail'))
        result=self.run_collection()
        self.assertEqual(result['status'],'STOPPED_NO_RETRY');self.assertEqual(result['business_method_calls'],1)
        self.assertNotIn('synthetic local private detail',json.dumps(result))
        self.assertIn('synthetic local private detail',(self.output/'failure.private.json').read_text())

    def test_source_change_after_one_request_blocks_next(self):
        source=collector.source_hashes();changed=[False]
        self.sdk.mutate=lambda:changed.__setitem__(0,True)
        with mock.patch.object(collector,'source_hashes',side_effect=lambda:source|{'changed':'yes'} if changed[0] else source):
            result=collector.collect(self.inputs,self.output,factory=lambda:self.sdk,expected_source=source)
        self.assertEqual(result['reason'],'SOURCE_OR_INPUT_CHANGED_NO_FURTHER_REQUEST')
        self.assertEqual(len(self.sdk.calls),1)

    def test_frozen_plan_hash_change_fails_without_connection(self):
        with mock.patch.object(collector,'PLAN_SHA256','0'*64),self.assertRaisesRegex(collector.CollectionStopped,'FROZEN_PLAN'):
            collector.load_inputs()

    def test_missing_and_outside_RTH_bars_are_rejected_without_filling(self):
        sessions=self.inputs['calendars']['2023Q2'];rows=bars(sessions,'K_60M')
        self.assertEqual(len(rows),263);collector.validate_bars(rows,sessions,'K_60M')
        with self.assertRaisesRegex(collector.CollectionStopped,'COVERAGE'):collector.validate_bars(rows[:-1],sessions,'K_60M')
        bad=[dict(r) for r in rows];bad[0]['time_key']='2023-06-29 09:00:00'
        with self.assertRaisesRegex(collector.CollectionStopped,'COVERAGE'):collector.validate_bars(bad,sessions,'K_60M')

    def test_nonfinite_and_wrong_security_bars_fail(self):
        sessions=self.inputs['calendars']['2022Q1'];rows=bars(sessions,'K_DAY')
        rows[0]['open']=float('nan')
        with self.assertRaisesRegex(collector.CollectionStopped,'VALUES'):collector.validate_bars(rows,sessions,'K_DAY')
        rows[0]['code']='US.AAPL'
        with self.assertRaisesRegex(collector.CollectionStopped,'IDENTITY'):collector.validate_bars(rows,sessions,'K_DAY')

    def action(self):
        return dict(ex_div_date='2000-08-22',forward_adj_factorA=0.5,forward_adj_factorB=0,
            backward_adj_factorA=2,backward_adj_factorB=0,split_base=2,split_ert=1,split_ratio=2,
            join_base=None,join_ert=None,per_cash_div=None,special_dividend=None)

    def test_inapplicable_null_action_fields_are_preserved_not_filled(self):
        row=self.action();before=json.dumps(row,sort_keys=True)
        collector.validate_actions([row],self.inputs['prepared']['events'])
        self.assertEqual(json.dumps(row,sort_keys=True),before)
        self.assertIsNone(row['per_cash_div'])

    def test_missing_mandatory_factor_partial_action_or_window_action_still_stop(self):
        for update in ({'forward_adj_factorA':None},{'split_ert':None},{'per_cash_div':'unknown'}):
            with self.subTest(update=update),self.assertRaisesRegex(collector.CollectionStopped,'ACTION_COVERAGE_UNKNOWN'):
                collector.validate_actions([self.action()|update],self.inputs['prepared']['events'])
        with self.assertRaisesRegex(collector.CollectionStopped,'WINDOW_CONTAINS'):
            collector.validate_actions([self.action()|{'ex_div_date':'2022-05-03'}],self.inputs['prepared']['events'])

    def prior(self):
        first=self.output/'first';first.mkdir()
        hashes={'collect_equity_event_inputs.py':collector.PRE_REPAIR_SOURCE_SHA256,'observation_job.py':collector.source_hashes()['observation_job.py']}
        summary=dict(status='STOPPED_NO_RETRY',reason='ACTION_COVERAGE_UNKNOWN',checked_at=collector.stamp(),
            business_method_calls=2,business_protocol_query_calls=2,observed_K_DAY_rows=0,observed_K60M_rows=0,
            windows=[],account_queries=0,order_calls=0,plan_sha256=collector.PLAN_SHA256,
            prepared_inputs_sha256=collector.PREPARED_SHA256,sdk_version=collector.SDK_VERSION,source_file_sha256=hashes)
        collector.write_new(first/'summary.json',summary)
        collector.write_new(first/'frozen-inputs.private.json',dict(files={},source_sha256=hashes,requests=collector.frozen_requests(self.inputs)))
        collector.write_new(first/'process.private.json',dict(returncode=1,bounds=dict(outcome='EXITED',cleanup_confirmed=True)))
        collector.write_new(first/'failure.private.json',dict(error='ACTION_COVERAGE_UNKNOWN'))
        for index,request in enumerate(collector.frozen_requests(self.inputs)[:2],1):
            rows=self.sdk.query(request)[1] if index==1 else [self.action()]
            prefix=first/f'{index:02d}-{request["label"]}'
            collector.write_new(str(prefix)+'.started.private.json',dict(request=request,attempt=1))
            collector.write_new(str(prefix)+'.response.private.json',dict(returned_reply=dict(ret=0,rows=rows),sdk_decoded_protocol_reply=[0,'',rows]))
        self.sdk.calls=[]
        return collector.prior_basis(first,self.inputs)

    def test_continuation_reuses_first_two_calls_and_once_only_ledger(self):
        prior=self.prior();out=self.output/'continuation';out.mkdir()
        before={p.name:collector.digest(p) for p in prior['root'].iterdir()}
        result=collector.collect(self.inputs,out,factory=lambda:self.sdk,prior=prior)
        self.assertEqual(result['status'],'FIXED_QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION')
        self.assertEqual(result['business_method_calls'],22);self.assertEqual(result['new_business_method_calls'],20)
        self.assertEqual(len(self.sdk.calls),20)
        self.assertEqual({r['method'] for r in self.sdk.calls},{'request_history_kline'})
        self.assertEqual(before,{p.name:collector.digest(p) for p in prior['root'].iterdir()})
        second=self.output/'second';second.mkdir();factory=mock.Mock()
        duplicate=collector.collect(self.inputs,second,factory=factory,prior=prior)
        self.assertEqual(duplicate['status'],'STOPPED_NO_RETRY');factory.assert_not_called()

    def test_prior_hash_change_and_expired_original_window_stop_before_sdk(self):
        prior=self.prior();out=self.output/'continuation';out.mkdir();factory=mock.Mock()
        with mock.patch.object(collector,'seconds_remaining',return_value=-1):
            result=collector.collect(self.inputs,out,factory=factory,prior=prior)
        self.assertEqual(result['reason'],'ORIGINAL_20_MINUTE_WINDOW_EXPIRED');factory.assert_not_called()
        self.assertFalse((self.output/'collection-continuation-claims').exists())
        (prior['root']/'failure.private.json').write_text('{"changed":true}')
        other=self.output/'changed';other.mkdir()
        result=collector.collect(self.inputs,other,factory=factory,prior=prior)
        self.assertEqual(result['reason'],'PRIOR_COLLECTION_RECEIPT_CHANGED');factory.assert_not_called()

    def test_ohlc_mismatch_retains_excluded_window_and_next_fixed_events(self):
        query=self.sdk.query
        def mismatch(request):
            reply=query(request)
            if request['label']=='2022Q2-K_DAY':reply[1][0]['open']=10.25
            return reply
        self.sdk.query=mismatch
        result=self.run_collection()
        self.assertEqual(result['business_method_calls'],22)
        self.assertEqual(len(result['windows']),10)
        self.assertEqual(result['windows'][1]['status'],'EXCLUDED_PENDING_CROSSCHECK')
        self.assertEqual(result['windows'][1]['daily_RTH_OHLC_mismatch_sessions'],1)
        self.assertEqual(result['windows'][2]['fiscal_quarter'],'2022Q3')
        raw=json.loads((self.output/'05-2022Q2-K_DAY.response.private.json').read_text())
        self.assertEqual(raw['returned_reply']['rows'][0]['open'],10.25)

    def test_six_prior_calls_leave_only_sixteen_never_repeat_q1_q2(self):
        prior=self.prior();prior['successful_calls']=6
        prior['original_summary'].update(observed_K_DAY_rows=76,observed_K60M_rows=532)
        prior['carried_windows']=[dict(fiscal_quarter='2022Q1',status='RAW_WINDOW_RETAINED_AWAITING_ADMISSION'),
            dict(fiscal_quarter='2022Q2',status='EXCLUDED_PENDING_CROSSCHECK')]
        out=self.output/'remaining';out.mkdir()
        result=collector.collect(self.inputs,out,factory=lambda:self.sdk,prior=prior)
        self.assertEqual(result['business_method_calls'],22);self.assertEqual(result['new_business_method_calls'],16)
        self.assertEqual(len(self.sdk.calls),16)
        self.assertEqual(self.sdk.calls[0]['label'],'2022Q3-K_DAY')
        self.assertEqual(result['observed_K_DAY_rows'],380);self.assertEqual(result['observed_K60M_rows'],2654)
        self.assertEqual(result['windows'][1]['status'],'EXCLUDED_PENDING_CROSSCHECK')

    def test_sdk_short_page_is_blocked_before_internal_second_request(self):
        class RequestHistoryKlineQuery:
            @staticmethod
            def pack_req():pass
            @staticmethod
            def unpack_rsp():pass
        # Real SDK functions have class-qualified names at module level.
        RequestHistoryKlineQuery.pack_req.__qualname__='RequestHistoryKlineQuery.pack_req'
        class Context:
            def __init__(self):self.sent=0
            def _get_sync_query_processor(self,pack,unpack):
                def query(**kwargs):self.sent+=1;return 0,'',([{'time_key':'synthetic first page'}],True,b'next')
                return query
            def request_history_kline(self,**kwargs):
                for _ in range(2):
                    self._get_sync_query_processor(RequestHistoryKlineQuery.pack_req,RequestHistoryKlineQuery.unpack_rsp)()
            def close(self):pass
        context=Context();sdk=collector.SinglePageSDK(context)
        with self.assertRaisesRegex(collector.CollectionStopped,'NEXT_PAGE'):
            sdk.query(dict(method='request_history_kline',kwargs={}))
        self.assertEqual(context.sent,1);self.assertEqual(sdk.protocol_calls,1)
        self.assertEqual(sdk.wire_reply[2][2],b'next')

    @unittest.skipUnless(os.name=='nt','Windows worker attestation')
    def test_direct_worker_cannot_start_sdk_or_write_artifacts(self):
        env={k:v for k,v in os.environ.items() if not k.startswith('HAKIMI_OWNED_JOB_')}
        result=subprocess.run([sys.executable,'-B',collector.__file__,'--owned-worker','--execute-read-only',
            '--output-dir',str(self.output)],env=env,capture_output=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'PARENT_OWNED_JOB_ATTESTATION_REQUIRED',result.stderr)
        self.assertEqual(list(self.output.iterdir()),[])


if __name__=='__main__':unittest.main()
