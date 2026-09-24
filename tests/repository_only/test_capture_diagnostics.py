"""Offline faults: real stage code with substituted sockets/HTTP responses."""
from pathlib import Path
import io
import json
import os
import socket
import ssl
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from capture_diagnostics import CaptureFailure, Trace, TracedHTTPSConnection, get_public_page, traced_connection
import collect_btc_snapshot as collector
import run_forward_cycle
import observation_job

URL="https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1H&limit=300&after=1"


class Response:
    status=200; url=URL
    def __init__(self, raw=b'{}',error=None): self.raw,self.error=raw,error
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,limit):
        if self.error: raise self.error
        return self.raw[:limit]


class CaptureDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.sink=io.StringIO();self.trace=Trace(self.sink)
    def rows(self): return [json.loads(line) for line in self.sink.getvalue().splitlines()]
    def test_dns_fault_is_distinct_and_does_not_expose_raw_message(self):
        with patch('socket.getaddrinfo',side_effect=socket.gaierror('private proxy credentials')):
            with self.assertRaises(CaptureFailure) as error: traced_connection(self.trace,('example.test',443),1)
        self.assertEqual(error.exception.stage,'DNS')
        self.assertNotIn('credentials',self.sink.getvalue())
    def test_connect_timeout_closes_owned_socket(self):
        fake=Mock();fake.connect.side_effect=TimeoutError()
        with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]),patch('socket.socket',return_value=fake):
            with self.assertRaises(CaptureFailure) as error:traced_connection(self.trace,('example.test',443),1)
        self.assertEqual(error.exception.stage,'CONNECT');fake.close.assert_called_once()
    def test_tls_failure_keeps_validation_enabled_and_closes_socket(self):
        connection=TracedHTTPSConnection('example.test',trace=self.trace)
        self.assertTrue(connection._context.check_hostname)
        self.assertEqual(connection._context.verify_mode,ssl.CERT_REQUIRED)
        fake=Mock();connection.sock=fake
        context=Mock();context.wrap_socket.side_effect=ssl.SSLCertVerificationError('private host')
        connection._context=context
        with patch('http.client.HTTPConnection.connect'):
            with self.assertRaises(CaptureFailure) as error:connection.connect()
        self.assertEqual(error.exception.stage,'TLS');fake.close.assert_called_once()
    def test_http_header_fault_is_identified(self):
        connection=TracedHTTPSConnection('example.test',trace=self.trace);connection.sock=Mock()
        with patch('http.client.HTTPSConnection.getresponse',side_effect=TimeoutError()):
            with self.assertRaises(CaptureFailure) as error:connection.getresponse()
        self.assertEqual(error.exception.stage,'HTTP_HEADERS')
    def test_read_timeout_can_retry_only_inside_explicit_attempt_budget(self):
        opener=Mock();opener.open.side_effect=[Response(error=TimeoutError()),Response(b'fresh')]
        self.assertEqual(get_public_page(URL,self.trace,max_attempts=2,opener=opener),b'fresh')
        self.assertEqual(opener.open.call_count,2)
        self.assertTrue(any(row['stage']=='RESPONSE_READ' and row['state']=='FAILED' for row in self.rows()))
    def test_default_does_not_retry_or_use_cache(self):
        opener=Mock();opener.open.return_value=Response(error=TimeoutError())
        with self.assertRaises(CaptureFailure):get_public_page(URL,self.trace,opener=opener)
        self.assertEqual(opener.open.call_count,1)
    def test_transient_tls_timeout_retries_but_certificate_failure_does_not(self):
        opener=Mock();opener.open.side_effect=[CaptureFailure('TLS','TimeoutError'),Response(b'fresh')]
        self.assertEqual(get_public_page(URL,self.trace,max_attempts=2,opener=opener),b'fresh')
        rejected=Mock();rejected.open.side_effect=CaptureFailure('TLS','SSLCertVerificationError')
        with self.assertRaises(CaptureFailure):get_public_page(URL,self.trace,max_attempts=3,opener=rejected)
        self.assertEqual(rejected.open.call_count,1)
    def test_total_deadline_blocks_next_call(self):
        clock=[0];trace=Trace(self.sink,total_seconds=1,clock=lambda:clock[0]);clock[0]=2
        opener=Mock()
        with self.assertRaises(CaptureFailure) as error:get_public_page(URL,trace,opener=opener)
        self.assertEqual(error.exception.stage,'TOTAL_DEADLINE');opener.open.assert_not_called()
    def test_retry_shares_total_request_budget(self):
        trace=Trace(self.sink,max_calls=1);opener=Mock();opener.open.return_value=Response(error=TimeoutError())
        with self.assertRaises(CaptureFailure) as error:get_public_page(URL,trace,max_attempts=3,opener=opener)
        self.assertEqual(error.exception.stage,'REQUEST_BUDGET');self.assertEqual(opener.open.call_count,1)
    def test_account_or_altered_origin_never_reaches_opener(self):
        for bad in ('https://www.okx.com/api/v5/trade/order','https://www.okx.com.evil.test/api/v5/market/history-candles'):
            with self.subTest(url=bad),self.assertRaises(ValueError):get_public_page(bad,self.trace,opener=Mock())
    def test_bad_response_is_logged_and_not_admitted(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(collector,'get_public_page',return_value=b'{"code":"0","data":[]}') as get:
            output=Path(folder)
            with self.assertRaises(CaptureFailure) as error:collector.collect('2024-01-01T00:00:00Z','2024-01-01T01:00:00Z',output)
            self.assertEqual(error.exception.stage,'CONTENT_VALIDATION')
            self.assertFalse((output/'datasets').exists())
            self.assertIn('CONTENT_VALIDATION',(output/'public_capture_trace.jsonl').read_text())
            with self.assertRaises(FileExistsError):collector.collect('2024-01-01T00:00:00Z','2024-01-01T01:00:00Z',output)
            self.assertEqual(get.call_count,1)
    def test_finished_phase_is_not_reported_as_still_started(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'public_capture_trace.jsonl'
            target.write_text('{"stage":"DNS","state":"STARTED"}\n{"stage":"DNS","state":"SUCCEEDED"}\n',encoding='utf-8')
            self.assertEqual(run_forward_cycle._capture_failure_stage(Path(folder)),'DNS:SUCCEEDED')
            with target.open('a') as f:f.write('{"stage":"CONNECT","state":"STARTED"}\n{partial')
            self.assertEqual(run_forward_cycle._capture_failure_stage(Path(folder)),'CONNECT:STARTED')
    @unittest.skipUnless(os.name=='nt','Windows owned-process deadline')
    def test_blocked_dns_leaves_a_phase_receipt_and_owned_process_is_reaped(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'public_capture_trace.jsonl'
            tools_path=str(Path(__file__).resolve().parents[2]/'tools')
            code=('import sys,socket,time;sys.path.insert(0,sys.argv[1]);'
                  'from capture_diagnostics import Trace,traced_connection;'
                  'f=open(sys.argv[2],"x");t=Trace(f);'
                  'socket.getaddrinfo=lambda *a,**k:time.sleep(6);'
                  'traced_connection(t,("synthetic.invalid",443),1)')
            result=observation_job.execute([sys.executable,'-I','-S','-B','-c',code,tools_path,str(target)],root,timeout_seconds=1)
            self.assertEqual(result.bounds['outcome'],'TIMED_OUT')
            self.assertTrue(result.bounds['cleanup_confirmed'])
            self.assertEqual(run_forward_cycle._capture_failure_stage(root),'DNS:STARTED')


if __name__=='__main__':unittest.main()
