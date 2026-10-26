"""Synthetic first-use source and persistence checks; no economic execution."""
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import daily_updates as daily
from hakimi_research import stock_intake as intake
from hakimi_research import workbench_service as service
from hakimi_research import workbench_server as server
from test_daily_updates import source_reply, encoded


class StockIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = daily._clock('2026-10-23T21:00:00Z')
        self.sequence = 0
        self.requests = []

    def payload(self, count=20, *, now=None, exchange='XNAS'):
        _, _, _, first, latest = intake._coverage(now or self.now, count, 'XNYS')
        query_start = max((date.fromisoformat(first)-timedelta(days=120)).isoformat(), '2026-01-01')
        payload = source_reply(query_start, latest, exchange=exchange)
        payload['chart']['result'][0]['meta'].update(dataGranularity='1d', longName='Fictional TEST Corporation')
        return payload

    def check(self, payload=None, *, count=20, now=None, fetcher=None):
        self.sequence += 1
        folder = self.root/('check-' + str(self.sequence))
        raw = encoded(payload if payload is not None else self.payload(count, now=now))
        def fetch(url):
            self.requests.append(url)
            self.assertTrue((folder/'request-started.json').is_file())
            return raw
        return folder, intake.check_stock_import('TEST', count, folder, now=now or self.now, fetcher=fetcher or fetch)

    def test_check_confirm_save_and_reopen_use_original_bytes_without_another_request(self):
        folder, review = self.check()
        self.assertEqual(review['status'], 'REVIEW_REQUIRED')
        self.assertEqual(review['session_count'], 20)
        self.assertFalse((self.root/'data').exists())
        self.assertEqual(len(self.requests), 1)
        for change in ({'expected_check_hash':'wrong', 'confirmed_security':review['security']},
                       {'expected_check_hash':review['check_hash'], 'confirmed_security':dict(review['security'], currency='EUR')}):
            with self.assertRaisesRegex(ValueError, 'exact_security_confirmation'):
                intake.save_stock_import(folder, self.root, **change)
        saved = intake.save_stock_import(folder, self.root, expected_check_hash=review['check_hash'], confirmed_security=review['security'])
        raw = Path(saved['path']).read_bytes()
        again = intake.save_stock_import(folder, self.root, expected_check_hash=review['check_hash'], confirmed_security=review['security'])
        self.assertEqual(again['path'], saved['path'])
        self.assertEqual(Path(saved['path']).read_bytes(), raw)
        self.assertEqual(len(self.requests), 1)
        doc = json.loads(raw)
        self.assertEqual(doc['evidence_kind'], 'IMPORTED_UNVERIFIED')
        self.assertEqual(doc['security_identity']['source']['raw_sha256'], review['raw_sha256'])
        self.assertFalse(doc['order_allowed'])
        self.assertEqual(saved['suggested_task']['params']['slow_window'], 10)
        self.assertEqual(saved['suggested_task']['score_start'], doc['sessions'][12]['date'])
        self.assertEqual(intake.read_stock_import(folder)['frozen_input_ref'], Path(saved['path']).relative_to(self.root).as_posix())

    def test_bounded_counts_and_unsupported_inputs_reject_before_fetch(self):
        for symbol, count in (('bad/symbol',20),('TEST',True),('TEST',21),('TEST',1000)):
            with self.subTest(symbol=symbol,count=count), self.assertRaises(ValueError):
                intake.check_stock_import(symbol,count,self.root/'invalid',now=self.now,fetcher=lambda _:self.fail('network'))
        for count in (20,60,120):
            with self.subTest(count=count):
                _, review = self.check(count=count)
                self.assertEqual(review['status'],'REVIEW_REQUIRED')
                self.assertEqual(review['session_count'],count)
        review=intake.check_stock_import('TEST',20,self.root/'unpublished-calendar',now=daily._clock('2028-01-10T22:00:00Z'),
                                         fetcher=lambda _:self.fail('unsupported calendar must stop before network'))
        self.assertEqual(review['status'],'CALENDAR_UNAVAILABLE')
        self.assertEqual(review['permissions']['network_requests'],0)

    def test_source_identity_adjustment_missing_events_and_actions_keep_stop_evidence(self):
        variants=[]
        for field,value in (('symbol','OTHER'),('currency','EUR'),('exchangeName','HKG'),('instrumentType','ETF'),
                            ('exchangeTimezoneName','UTC'),('dataGranularity','1h')):
            p=self.payload();p['chart']['result'][0]['meta'][field]=value;variants.append(p)
        p=self.payload();p['chart']['result'][0].pop('events');variants.append(p)
        p=self.payload();p['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][-1]-=1;variants.append(p)
        p=self.payload();result=p['chart']['result'][0];result['events']={'splits':{'x':{'date':result['timestamp'][-1]}}};variants.append(p)
        for p in variants:
            folder,review=self.check(p)
            self.assertEqual(review['status'],'BLOCKED')
            self.assertFalse(review['can_save'])
            self.assertEqual((folder/'source-original.bin').read_bytes(),encoded(p))
            self.assertFalse((folder/'candidate-prices.csv').exists())
        self.assertFalse((self.root/'data').exists())

    def test_missing_latest_waits_and_missing_history_blocks_without_repair(self):
        for index,status in ((-1,'WAITING_SOURCE_UPDATE'),(-2,'BLOCKED')):
            p=self.payload();r=p['chart']['result'][0]
            r['timestamp'].pop(index)
            for values in r['indicators']['quote'][0].values():values.pop(index)
            r['indicators']['adjclose'][0]['adjclose'].pop(index)
            _,review=self.check(p)
            self.assertEqual(review['status'],status)

    def test_actual_exchange_calendar_not_a_nyse_substitution(self):
        now=daily._clock('2027-01-29T22:00:00Z')
        _,review=self.check(self.payload(now=now,exchange='XNAS'),now=now)
        self.assertEqual(review['status'],'CALENDAR_UNAVAILABLE')
        self.assertIn('EXCHANGE_CALENDAR_NOT_PUBLISHED:XNAS:2027',review['reason'])
        _,review=self.check(self.payload(now=now,exchange='XNYS'),now=now)
        self.assertEqual(review['status'],'REVIEW_REQUIRED')
        self.assertEqual(review['security']['exchange'],'XNYS')

    def test_transport_failure_and_unknown_do_not_retry(self):
        for error,status in ((daily._Stop('SOURCE_HTTP_429',received_raw=b'synthetic rate limit'),'BLOCKED'),
                             (RuntimeError('synthetic unknown'),'UNKNOWN')):
            calls=[]
            def fail(url):
                calls.append(url)
                raise error
            folder,review=self.check(fetcher=fail)
            self.assertEqual(len(calls),1)
            self.assertEqual(review['status'],status)
            self.assertFalse(review['can_save'])
            if status=='BLOCKED':self.assertEqual((folder/'source-original.bin').read_bytes(),b'synthetic rate limit')

    def test_tampered_original_cannot_be_read_or_saved(self):
        folder,review=self.check()
        (folder/'source-original.bin').write_bytes(b'changed synthetic bytes')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            intake.read_stock_import(folder)
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            intake.save_stock_import(folder,self.root,expected_check_hash=review['check_hash'],confirmed_security=review['security'])
        self.assertFalse((self.root/'data').exists())

    def test_saved_candidate_uses_its_retained_calendar_on_read_and_save(self):
        folder,review=self.check()
        with patch.object(intake,'_coverage',side_effect=AssertionError('must retain the original calendar')):
            self.assertEqual(intake.read_stock_import(folder)['check_hash'],review['check_hash'])
            saved=intake.save_stock_import(folder,self.root,expected_check_hash=review['check_hash'],confirmed_security=review['security'])
        self.assertEqual(saved['status'],'STOCK_INPUT_SAVED')

    def test_first_saved_input_enters_existing_next_day_update_contract(self):
        folder,review=self.check()
        saved=intake.save_stock_import(folder,self.root,expected_check_hash=review['check_hash'],confirmed_security=review['security'])
        original=Path(saved['path']).read_bytes()
        first=date.fromisoformat(review['query_start'])
        payload=source_reply(first.isoformat(),'2026-10-26')
        update=daily.check_daily_update(saved['path'],self.root/'next-day',now=daily._clock('2026-10-26T21:00:00Z'),fetcher=lambda _:encoded(payload))
        self.assertEqual(update['status'],'READY')
        self.assertEqual(update['new_dates'],['2026-10-26'])
        self.assertEqual(Path(saved['path']).read_bytes(),original)
        self.assertEqual(update['permissions']['economic_runs'],0)


class FirstUseServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'workspace'
        runtime=service.build_runtime_provenance()
        runtime['source_identity']['content_sha256']=service._LOADED_SOURCE
        self.runtime=patch.object(service,'build_runtime_provenance',return_value=runtime)
        self.runtime.start();self.addCleanup(self.runtime.stop)
        self.no_run=patch.object(service,'run_task',side_effect=AssertionError('economic execution prohibited in first-use fixture'))
        self.no_run.start();self.addCleanup(self.no_run.stop)
        self.app=service.Workbench(self.root)

    def test_example_reuse_and_server_side_progress_survive_reopen(self):
        first=self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='z-first-example',guided=True))
        snapshot=Path(first['path']).read_bytes()
        again=self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='a-later-example',guided=True))
        self.assertEqual(first['ref'],again['ref'])
        progress=service.Workbench(self.root).state()['first_use']['progress']
        self.assertEqual(progress['guide_id'],'a-later-example')
        self.assertEqual(progress['step'],'INPUT_SAVED')
        self.assertEqual(progress['suggested_task']['params']['slow_window'],4)
        self.assertEqual(Path(first['path']).read_bytes(),snapshot)
        self.assertEqual(len(self.app.state()['inputs']),1)
        self.assertEqual(self.app.state()['tasks'],[])
        self.assertEqual(self.app.state()['runs'],[])

    def test_guided_task_binding_preserves_template_and_does_not_run(self):
        saved=self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='load-demo-for-task',guided=True))
        task=self.app.action(dict(action='create_task',operation_id='create-demo-task',guided=True,guide_id=saved['workflow']['guide_id'],
                                 snapshot=saved['ref'],**saved['suggested_task']))
        state=service.Workbench(self.root).state()
        self.assertEqual(state['first_use']['progress']['task_ref'],task['ref'])
        self.assertEqual(state['first_use']['progress']['suggested_task'],saved['suggested_task'])
        self.assertEqual(state['first_use']['progress']['step'],'TASK_CREATED')
        self.assertEqual(state['runs'],[])
        self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='restart-same-guide',guided=True,
                             guide_id=saved['workflow']['guide_id']))
        progress=self.app.state()['first_use']['progress']
        self.assertEqual(progress['step'],'INPUT_SAVED')
        self.assertNotIn('task_ref',progress)
        self.assertNotIn('run_ref',progress)
        self.assertEqual(len(self.app.state()['tasks']),1)

    def test_progress_tampering_is_visible_and_old_untimed_receipts_stay_unchanged(self):
        old=self.root/'operations/legacy-record/result.json'
        service.write_new(old,dict(operation_id='legacy-record',ok=True,status='COMMITTED',result={}))
        original=old.read_bytes()
        self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='new-guided-record',guided=True))
        receipt=self.root/'operations/new-guided-record/result.json'
        value=json.loads(receipt.read_bytes());value['workflow']['snapshot_ref']='data/missing.json'
        receipt.write_bytes(encoded(value))
        progress=self.app.state()['first_use']['progress']
        self.assertEqual(progress['status'],'UNAVAILABLE_REQUIRES_REVIEW')
        self.assertEqual(progress['unknown_legacy_operation_count'],1)
        self.assertEqual(old.read_bytes(),original)

    def test_check_operation_replay_and_unknown_pending_never_fetch_again(self):
        helper=StockIntakeTests();helper.setUp();self.addCleanup(helper.doCleanups)
        original=intake.check_stock_import;calls=[]
        def fake(symbol,count,directory):
            def fetch(url):calls.append(url);return encoded(helper.payload())
            return original(symbol,count,directory,now=helper.now,fetcher=fetch)
        request=dict(action='check_stock_import',operation_id='explicit-check-first',symbol='TEST',history_sessions=20,guided=True)
        with patch.object(intake,'check_stock_import',side_effect=fake):
            first=self.app.action(request)
            self.assertEqual(self.app.action(request),first)
        self.assertEqual(len(calls),1)
        state=service.Workbench(self.root).state()
        self.assertEqual(state['first_use']['progress']['intake_ref'],first['ref'])
        self.assertEqual(state['inputs'],[])
        bad=dict(request,operation_id='pending-not-replayed',guide_id=first['workflow']['guide_id'])
        service.write_new(self.root/'operations'/bad['operation_id']/'request.json',dict(request=bad,request_hash=service.digest(bad)))
        with self.assertRaisesRegex(ValueError,'operation_outcome_unknown'):
            self.app.action(bad)
        self.assertEqual(self.app.state()['first_use']['progress']['pending_operations'][0]['operation_id'],bad['operation_id'])
        saved=self.app.action(dict(action='save_stock_import',operation_id='save-confirmed-stock',guided=True,
            guide_id=first['workflow']['guide_id'],intake=first['ref'],expected_check_hash=first['check_hash'],confirmed_security=first['security']))
        progress=service.Workbench(self.root).state()['first_use']['progress']
        self.assertEqual(progress['snapshot_ref'],saved['ref'])
        self.assertEqual(progress['suggested_task']['params']['slow_window'],10)
        self.assertEqual(progress['intake_ref'],first['ref'])
        self.assertEqual(progress['check_hash'],first['check_hash'])
        self.assertEqual(len(calls),1)

    def test_saving_selected_candidate_rebinds_same_guide_to_its_actual_source(self):
        helper=StockIntakeTests();helper.setUp();self.addCleanup(helper.doCleanups)
        original=intake.check_stock_import
        def fake(symbol,count,directory):
            return original(symbol,count,directory,now=helper.now,fetcher=lambda _:encoded(helper.payload()))
        with patch.object(intake,'check_stock_import',side_effect=fake):
            first=self.app.action(dict(action='check_stock_import',operation_id='check-candidate-a',guided=True,
                symbol='TEST',history_sessions=20))
            selected=self.app.action(dict(action='check_stock_import',operation_id='check-candidate-b',guided=True,
                symbol='TEST',history_sessions=20))
        saved=self.app.action(dict(action='save_stock_import',operation_id='save-selected-candidate-b',guided=True,
            guide_id=first['workflow']['guide_id'],intake=selected['ref'],expected_check_hash=selected['check_hash'],
            confirmed_security=selected['security']))
        progress=service.Workbench(self.root).state()['first_use']['progress']
        self.assertEqual(progress['guide_id'],first['workflow']['guide_id'])
        self.assertEqual(progress['intake_ref'],selected['ref'])
        self.assertEqual(progress['check_hash'],selected['check_hash'])
        self.assertEqual(progress['snapshot_ref'],saved['ref'])
        self.assertEqual(progress['snapshot_id'],saved['input_id'])
        self.assertIsNone(self.app.stock_intake_view(first['ref'])['frozen_input_ref'])
        self.assertEqual(self.app.stock_intake_view(selected['ref'])['frozen_input_ref'],saved['ref'])
        self.assertEqual(self.app.state()['runs'],[])

    def test_startup_identity_is_actual_module_and_interpreter(self):
        class FakeService:
            loaded_source='actual-loaded-source'
            def close(self):pass
        class FakeServer:
            workbench=FakeService();server_port=12345
            def serve_forever(self):raise KeyboardInterrupt
            def server_close(self):pass
        out=io.StringIO()
        with patch.object(server,'create_server',return_value=FakeServer()), patch('sys.stdout',out):
            server.main(['--workspace',str(self.root)])
        value=json.loads(out.getvalue())
        self.assertEqual(value['loaded_source_sha256'],'actual-loaded-source')
        self.assertEqual(value['package_location'],str(Path(server.__file__).resolve().parent))
        self.assertEqual(value['python_executable'],str(Path(server.sys.executable).resolve()))

    def test_disconnected_client_does_not_send_second_response_or_hide_domain_errors(self):
        local=server.create_server(self.root)
        self.addCleanup(local.server_close)
        handler=local.RequestHandlerClass.__new__(local.RequestHandlerClass)
        handler.server=local
        handler.path='/'
        handler.headers={'Host':'127.0.0.1:'+str(local.server_port)}
        handler.wfile=io.BytesIO()
        statuses=[]
        handler._headers=lambda status,*_:statuses.append(status)
        handler.do_GET()
        token=re.search(r'<script nonce="([^"]+)"',handler.wfile.getvalue().decode()).group(1)
        handler.headers['X-Hakimi-Token']=token
        handler.path='/api/state'
        class DisconnectedClient:
            writes=0
            def write(self, raw):
                self.writes+=1
                raise ConnectionAbortedError(10053,'synthetic disconnected client')
        handler.wfile=DisconnectedClient()
        statuses.clear()
        with patch.object(local.workbench,'state',return_value={'saved':'unchanged'}):
            handler.do_GET()
        self.assertEqual(statuses,[200])
        self.assertEqual(handler.wfile.writes,1)
        self.assertTrue(handler.close_connection)
        for error in (ValueError('synthetic invalid input'),OSError('synthetic unreadable saved data')):
            with self.subTest(error=type(error).__name__):
                statuses.clear();handler.wfile=io.BytesIO()
                with patch.object(local.workbench,'state',side_effect=error):
                    handler.do_GET()
                self.assertEqual(statuses,[400])
                self.assertEqual(json.loads(handler.wfile.getvalue())['error'],str(error))

    def test_unknown_source_outcome_does_not_advance_saved_progress(self):
        saved=self.app.action(dict(action='load_example',example='dual_ma_intro',operation_id='prior-demo-input',guided=True))
        helper=StockIntakeTests();helper.setUp();self.addCleanup(helper.doCleanups)
        original=intake.check_stock_import
        def fake(symbol,count,directory):
            def fetch(_):raise RuntimeError('unknown synthetic transport')
            return original(symbol,count,directory,now=helper.now,fetcher=fetch)
        with patch.object(intake,'check_stock_import',side_effect=fake):
            unknown=self.app.action(dict(action='check_stock_import',operation_id='unknown-stock-check',guided=True,
                guide_id=saved['workflow']['guide_id'],symbol='TEST',history_sessions=20))
        self.assertEqual(unknown['status'],'UNKNOWN')
        self.assertNotIn('workflow',unknown)
        progress=self.app.state()['first_use']['progress']
        self.assertEqual(progress['step'],'INPUT_SAVED')
        self.assertEqual(progress['snapshot_ref'],saved['ref'])
        self.assertEqual(progress['pending_operations'][0]['operation_id'],'unknown-stock-check')


if __name__=='__main__':
    unittest.main()
