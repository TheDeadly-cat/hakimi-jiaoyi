"""Synthetic Git/protocol/HTTP receipts only; no new market data or strategy run."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.client import IncompleteRead
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from urllib.parse import urlencode
from urllib.error import HTTPError
from unittest.mock import patch

from hakimi_research.documents import digest
from hakimi_research import daily_updates as updates


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


blind = load('blind_holdout_under_test', ROOT / 'tools/prepare_blind_holdout.py')
fixtures = load('sealed_holdout_fixtures', ROOT / 'tests/repository_only/test_sealed_month_replay.py')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True) + '\n').encode()


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 23, 0, 0, 2, tzinfo=timezone.utc)
        self.sleeps = []

    def __call__(self):
        self.value += timedelta(milliseconds=1)
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += timedelta(seconds=seconds)


class BlindHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.prices = fixtures.SealedMonthReplayV2Tests('test_v2_reconciles_entire_history_and_keeps_original_quote_fields')
        self.prices.setUp()
        self.addCleanup(self.prices.doCleanups)
        f = self.prices.fixture
        self.root = f.root
        self.repo = self.root / 'repository'
        self.repo.mkdir()
        self.clock = Clock()
        self.calls = []
        self.output = self.root / 'heldout-once'
        parameter = deepcopy(f.design)
        parameter.update(schema_version='fixed-month-replay-design-v2', parameter_sources={})
        parameter.pop('plan_hash', None)
        parameter['plan_hash'] = digest(parameter)
        self.parameter = self.root / 'parameter-design.json'
        self.parameter.write_bytes(encoded(parameter))
        audit = dict(status='PASS_PROJECT_SCOPE', excluded_intervals=[dict(start='2026-09-16', end='2026-10-22')],
            selected_month='2026-08', selected_context_start='2026-07-16', selected_score_start='2026-08-03', selected_score_end='2026-08-31')
        self.audit = self.root / 'exposure.json'
        self.audit.write_bytes(encoded(audit))
        self.addendum = self.root / 'anonymous-attribution.json'
        self.addendum.write_bytes(encoded(dict(status='PASS_NO_UNRESOLVED_CANDIDATE_OVERLAP',
            unresolved_candidate_overlap_count=0, candidate_context_start='2026-07-16',
            candidate_score_start='2026-08-03', candidate_score_end='2026-08-31', recorded_at='2026-10-22T23:59:59Z')))
        self.design = {key: deepcopy(parameter[key]) for key in blind.ECONOMIC_FIELDS}
        self.design.update(schema_version=blind.SCHEMA, mode=blind.MODE, recorded_at='2026-10-23T00:00:00Z',
            context_start='2026-07-16', context_sessions=12, context_dates=f.design['context_dates'],
            score_start='2026-08-03', score_end='2026-08-31', score_sessions=f.design['score_sessions'],
            calendar_path=str(f.calendar_path), calendar_sha256=sha256(f.calendar_path.read_bytes()).hexdigest(),
            repository_path=str(self.repo), protocol_repo_path='protocol.json', acquisition_output_path=str(self.output),
            historical_price_policy=deepcopy(blind.replay.HISTORICAL_POLICY), acquisition_policy=deepcopy(blind.POLICY),
            parameter_design=dict(path=str(self.parameter), sha256=sha256(self.parameter.read_bytes()).hexdigest()),
            exposure_audit=dict(path=str(self.audit), sha256=sha256(self.audit.read_bytes()).hexdigest()),
            exposure_addendum=dict(path=str(self.addendum), sha256=sha256(self.addendum.read_bytes()).hexdigest()),
            execution_runtime_source_sha256='synthetic-runtime', tool_hashes={})
        for name in (blind._OWN_PATH, blind._REPLAY_PATH):
            target = self.repo / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            self.design['tool_hashes'][name] = sha256(target.read_bytes()).hexdigest()
        period1 = int(datetime(2026, 7, 16, tzinfo=updates._NY).timestamp())
        period2 = int(datetime(2026, 10, 23, tzinfo=updates._NY).timestamp())
        reference = 'https://query1.finance.yahoo.com/v8/finance/chart/TEST?' + urlencode(dict(
            period1=period1, period2=period2, interval='1d', events='div,splits', includePrePost='false'))
        self.design['sources'] = {'TEST': dict(baseline_snapshot_path=str(f.baseline_path),
            baseline_sha256=sha256(f.baseline_path.read_bytes()).hexdigest(), query_start='2026-07-16',
            query_period2_utc='2026-10-23T04:00:00Z', latest_completed_session='2026-10-22', reference=reference,
            historical_identity_declaration=f.design['sources']['TEST']['historical_identity_declaration'])}
        self.payload = deepcopy(f.payload)
        result = self.payload['chart']['result'][0]
        start_index = result['timestamp'].index(int(updates._clock('2026-07-16T13:30:00Z').timestamp()))
        result['timestamp'] = result['timestamp'][start_index:]
        for key in updates._FIELDS:
            result['indicators']['quote'][0][key] = result['indicators']['quote'][0][key][start_index:]
        result['indicators']['adjclose'][0]['adjclose'] = result['indicators']['adjclose'][0]['adjclose'][start_index:]
        self.raw = encoded(self.payload)
        runtime = dict(source_identity=dict(content_sha256='synthetic-runtime'), environment_verified=dict(status='VERIFIED'))
        self.runtime_patch = patch.object(blind, 'build_runtime_provenance', return_value=runtime)
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.git('init', '--quiet')
        self.git('config', 'core.autocrlf', 'false')
        self.plan = self.root / 'protocol-original.json'
        self.seal()

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_DATE='2026-10-23T00:00:01Z', GIT_COMMITTER_DATE='2026-10-23T00:00:01Z')
        return subprocess.check_output(['git', '-c', 'user.name=Synthetic Test', '-c', 'user.email=synthetic@example.invalid',
                                       *args], cwd=self.repo, env=env, stderr=subprocess.STDOUT)

    def seal(self):
        self.design.pop('plan_hash', None)
        self.design['plan_hash'] = digest(self.design)
        raw = encoded(self.design)
        self.plan.write_bytes(raw)
        (self.repo / 'protocol.json').write_bytes(raw)
        self.git('add', '--', '.')
        self.git('commit', '--quiet', '--allow-empty', '-m', 'Synthetic sealed protocol')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()

    def fetch(self, url):
        self.calls.append(url)
        path = self.output / 'TEST/attempt-1/request-started.json'
        self.assertTrue(path.is_file(), 'request must be durable before any fetch')
        return self.raw

    def prepare(self, fetcher=None, **options):
        return blind.prepare(self.plan, self.commit, options.pop('output_dir', self.output),
                             fetcher=fetcher or self.fetch, clock=self.clock, sleeper=self.clock.sleep, **options)

    def test_committed_design_precedes_single_acquisition_and_preparation(self):
        before = self.plan.read_bytes()
        receipt = self.prepare()
        self.assertEqual(receipt['status'], 'READY')
        self.assertEqual(receipt['economic_runs'], 0)
        self.assertEqual(self.plan.read_bytes(), before)
        self.assertEqual(self.calls, [self.design['sources']['TEST']['reference']])
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        source = acquisition['sources']['TEST']
        self.assertEqual(source['status'], 'ACQUIRED')
        self.assertEqual(source['retrieved_at'], source['attempts'][-1]['completed_at'])
        self.assertGreater(source['retrieved_at'], acquisition['commit_time'])
        self.assertGreater(source['retrieved_at'], self.design['recorded_at'])
        self.assertEqual(Path(source['raw_path']).read_bytes(), self.raw)
        self.assertEqual(source['raw_sha256'], sha256(self.raw).hexdigest())
        self.assertEqual(receipt['acquisition_sha256'], sha256(Path(receipt['acquisition_path']).read_bytes()).hexdigest())
        self.assertEqual(receipt['symbols']['TEST']['selected_rows'], 33)

    def test_same_protocol_cannot_use_a_different_destination_or_run_twice(self):
        with self.assertRaisesRegex(ValueError, 'output_must_equal_frozen_destination'):
            self.prepare(output_dir=self.root / 'alternate')
        self.assertEqual(self.calls, [])
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'output_exists'):
            self.prepare()
        self.assertEqual(len(self.calls), 1)

    def test_uncommitted_protocol_change_and_different_head_never_fetch(self):
        self.design['acquisition_output_path'] = str(self.root / 'new-destination')
        self.design['plan_hash'] = digest({k:v for k,v in self.design.items() if k!='plan_hash'})
        self.plan.write_bytes(encoded(self.design))
        with self.assertRaisesRegex(ValueError, 'protocol_git_blob_mismatch'):
            self.prepare()
        self.assertEqual(self.calls, [])
        self.seal()
        old_commit = self.commit
        self.git('commit', '--allow-empty', '--quiet', '-m', 'A different current HEAD')
        with self.assertRaisesRegex(ValueError, 'head_must_equal_protocol_commit'):
            blind.prepare(self.plan, old_commit, self.output, fetcher=self.fetch, clock=self.clock)
        self.assertEqual(self.calls, [])

    def test_overlapping_exposure_audit_stops_before_fetch(self):
        audit = json.loads(self.audit.read_text())
        audit['excluded_intervals'].append(dict(start='2026-07-20', end='2026-07-21'))
        self.audit.write_bytes(encoded(audit))
        self.design['exposure_audit']['sha256'] = sha256(self.audit.read_bytes()).hexdigest()
        self.seal()
        with self.assertRaisesRegex(ValueError, 'overlaps_exposed_data'):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_explicit_429_has_one_same_url_delayed_retry_and_retains_error_body(self):
        def fetch(url):
            self.calls.append(url)
            if len(self.calls)==1:
                raise blind.FetchFailure('SOURCE_HTTP_429', response_status=429, raw=b'synthetic rate limit')
            return self.raw
        receipt = self.prepare(fetch)
        self.assertEqual(receipt['status'], 'READY')
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        attempts = acquisition['sources']['TEST']['attempts']
        self.assertEqual(self.calls, [self.design['sources']['TEST']['reference']]*2)
        self.assertEqual(self.clock.sleeps, [3])
        self.assertEqual(attempts[0]['status'], 'FAILED')
        self.assertEqual(Path(attempts[0]['raw_path']).read_bytes(), b'synthetic rate limit')
        elapsed = updates._clock(attempts[1]['request_started_at']) - updates._clock(attempts[0]['completed_at'])
        self.assertGreaterEqual(elapsed.total_seconds(), 3)

    def test_addendum_rejects_unresolved_boolean_wrong_date_and_future_evidence(self):
        original = json.loads(self.addendum.read_text())
        for change in ({'unresolved_candidate_overlap_count': 1}, {'unresolved_candidate_overlap_count': False},
                       {'candidate_context_start': '2026-07-17'}, {'recorded_at': '2026-10-23T00:00:01Z'},
                       {'status': 'UNKNOWN'}):
            with self.subTest(change=change):
                self.addendum.write_bytes(encoded({**original, **change}))
                self.design['exposure_addendum']['sha256'] = sha256(self.addendum.read_bytes()).hexdigest()
                self.seal()
                with self.assertRaisesRegex(ValueError, 'exposure_addendum_not_matched'):
                    self.prepare()
                self.assertEqual(self.calls, [])

    def test_http200_quality_failure_never_retries_or_reselects(self):
        def fetch(url):
            self.calls.append(url)
            return b'{"chart": "invalid synthetic response"}'
        receipt = self.prepare(fetch)
        self.assertEqual(receipt['status'], 'STOPPED')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.clock.sleeps, [])
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        self.assertEqual(acquisition['sources']['TEST']['attempts'][0]['response_status'], 200)
        self.assertFalse((self.output/'TEST/prepared/snapshot.json').exists())

    def test_known_body_failure_after_http200_does_not_retry_and_keeps_partial_bytes(self):
        def fetch(url):
            self.calls.append(url)
            raise blind.FetchFailure('SOURCE_REQUEST_FAILED_NO_RETRY', response_status=200, raw=b'partial synthetic response')
        receipt = self.prepare(fetch)
        self.assertEqual(receipt['status'], 'STOPPED')
        self.assertEqual(len(self.calls), 1)
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        attempt = acquisition['sources']['TEST']['attempts'][0]
        self.assertTrue(attempt['successful_response_received'])
        self.assertEqual(Path(attempt['raw_path']).read_bytes(), b'partial synthetic response')

    def test_unknown_outcome_never_retries(self):
        def fetch(url):
            self.calls.append(url)
            raise RuntimeError('synthetic unknown transport outcome')
        receipt = self.prepare(fetch)
        self.assertEqual(receipt['status'], 'STOPPED')
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        self.assertEqual(acquisition['sources']['TEST']['attempts'][0]['status'], 'UNKNOWN')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.clock.sleeps, [])

    def test_transport_incomplete_http200_retains_partial_bytes_without_retry(self):
        case = self
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                return False
            def geturl(self):
                return case.design['sources']['TEST']['reference']
            def read(self, size):
                raise IncompleteRead(partial=b'partial synthetic HTTP200', expected=100)
        class Opener:
            def open(self, request, timeout):
                case.calls.append(request.full_url)
                case.assertTrue((case.output/'TEST/attempt-1/request-started.json').is_file())
                return Response()
        with patch.object(blind, 'build_opener', return_value=Opener()):
            receipt = self.prepare(blind._fetch)
        self.assertEqual(receipt['status'], 'STOPPED')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.clock.sleeps, [])
        acquisition = json.loads(Path(receipt['acquisition_path']).read_text())
        attempt = acquisition['sources']['TEST']['attempts'][0]
        self.assertEqual(attempt['response_status'], 200)
        self.assertTrue(attempt['successful_response_received'])
        self.assertEqual(Path(attempt['raw_path']).read_bytes(), b'partial synthetic HTTP200')

    def test_transport_retains_http_error_status_and_partial_body(self):
        url = self.design['sources']['TEST']['reference']
        error = HTTPError(url, 429, 'Synthetic rate limit', {}, None)
        error.read = lambda size: (_ for _ in ()).throw(IncompleteRead(partial=b'partial 429', expected=10))
        class Opener:
            def open(self, request, timeout):
                raise error
        with patch.object(blind, 'build_opener', return_value=Opener()):
            with self.assertRaises(blind.FetchFailure) as caught:
                blind._fetch(url)
        self.assertEqual(caught.exception.response_status, 429)
        self.assertEqual(caught.exception.raw, b'partial 429')
        self.assertEqual(caught.exception.reason, 'SOURCE_HTTP_429')

    def test_changed_code_fails_before_fetch(self):
        (self.repo / blind._OWN_PATH).write_bytes((self.repo / blind._OWN_PATH).read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'source_hash_changed'):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_stale_cutoff_fails_before_any_price_request(self):
        self.clock.value = datetime(2026, 10, 23, 21, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, 'frozen_acquisition_cutoff_expired'):
            self.prepare()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
