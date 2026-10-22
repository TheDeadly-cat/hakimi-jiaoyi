"""Fictional, offline workbench acceptance tests; no real human or issuer approval.

The reserved example.invalid source and SYNTHETIC_TEST prices exercise the
explicit acceptance path. They are never market evidence or trading authority.
"""
import base64
from importlib.resources import files
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from hakimi_research.documents import read_document
from hakimi_research.equity_event_context import build_event_context
from hakimi_research.equity_events import build_equity_event
from hakimi_research.workbench_service import Workbench


FIXTURE = Path(__file__).parent / 'fixtures/collaboration_schedule_result_synthetic.json'
SECURITY = 'SYNTHETIC:RESEARCH:TEST'
SOURCE = b'Fictional TESTCO issuer: Q4 results on 2024-11-19 before the market opens.\n'
PARAMS = dict(fast_window=2, slow_window=4, position_pct=.25,
              stop_loss_pct=.03, take_profit_pct=.06)


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _studio_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def fictional_bundle():
    """Return a sealed test result/context/source with an overtly fake issuer."""
    event = build_equity_event(SOURCE, {
        'event_id': 'FICTIONAL:TESTCO:2024Q4:SCHEDULE', 'security_id': SECURITY,
        'event_kind': 'EARNINGS_SCHEDULE', 'version': 1, 'prior_version_hash': None,
        # COMPANY_IR exercises the acceptance path; .invalid and the explicit
        # fictional text make this impossible to mistake for issuer evidence.
        'source': {'url': 'https://issuer.example.invalid/fictional/earnings',
                   'kind': 'COMPANY_IR', 'document_type': 'PRESS_RELEASE',
                   'disclosure_items': [], 'official_source_status': 'DECLARED_UNVERIFIED'},
        'first_public_at': '2024-10-22T14:00:00Z',
        'version_public_at': '2024-10-22T14:00:00Z',
        'publication_clock': {'status': 'ATTESTED',
                              'verification_method': 'FICTIONAL_UNIT_TEST_CLOCK',
                              'evidence': 'Fictional time, asserted only inside this test.'},
        'retrieved_at': '2024-10-22T14:01:00Z',
        'timing': {'mode': 'OBSERVED', 'received_at': '2024-10-22T14:01:00Z',
                   'extraction_completed_at': '2024-10-22T14:02:00Z',
                   'collection_delay_seconds': None, 'processing_delay_seconds': None},
        'scheduled_release_at': None,
        'schedule': {'status': 'ANNOUNCED', 'date': '2024-11-19',
                     'time_precision': 'BEFORE_MARKET_OPEN',
                     'timezone': 'America/New_York',
                     'evidence': [{'quote': SOURCE.decode().strip()}], 'reason': None},
        'facts': [], 'uncertainties': ['Entirely fictional test input.'],
    })
    context = _encoded(build_event_context([event], SECURITY))
    result = json.loads(FIXTURE.read_text(encoding='utf-8'))
    context_sha = hashlib.sha256(context).hexdigest()
    source_sha = hashlib.sha256(SOURCE).hexdigest()
    result['domain_context']['payload_sha256'] = context_sha
    for row in result['source_manifest']:
        if row['source_kind'] == 'domain_context':
            row['record_sha256'] = context_sha
        elif row['source_kind'] == 'project_source':
            row['record_sha256'] = source_sha
    body = {key: value for key, value in result.items() if key not in {'result_id', 'result_sha256'}}
    result['result_id'] = 'result_' + _studio_hash(body)[:32]
    result['result_sha256'] = _studio_hash({key: value for key, value in result.items()
                                           if key != 'result_sha256'})
    return _encoded(result), context, SOURCE


class WorkbenchResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.app = Workbench(self.root)
        self.counter = 0
        self.result_raw, self.context_raw, self.source_raw = fictional_bundle()

    def act(self, action, **fields):
        self.counter += 1
        return self.app.action(dict(action=action,
                                    operation_id=f'fictional-operation-{self.counter}', **fields))

    @staticmethod
    def b64(raw):
        return base64.b64encode(raw).decode('ascii')

    def prices(self):
        resource = files('hakimi_research').joinpath('resources')
        return self.act('import_csv',
            csv_base64=self.b64(resource.joinpath('trade-demo.csv').read_bytes()),
            manifest_base64=self.b64(resource.joinpath('trade-demo-import.json').read_bytes()))

    def preview(self, *, result_raw=None, context_raw=None, source_raw=None):
        return self.act('preview_research', security_id=SECURITY,
            result_base64=self.b64(result_raw if result_raw is not None else self.result_raw),
            context_base64=self.b64(context_raw if context_raw is not None else self.context_raw),
            source_base64=self.b64(source_raw if source_raw is not None else self.source_raw))

    def approve_for_test(self):
        preview = self.preview()
        self.assertEqual(preview['status'], 'REJECTED')
        self.assertEqual(preview['reasons'], ['MANUAL_CONFIRMATION_REQUIRED'])
        self.assertTrue(preview['original_source_retained'])
        reviewed = self.act('review_research', research=preview['ref'],
            decision='ACCEPT_FOR_INPUT_CHECK', actor='FICTIONAL_TEST_OPERATOR',
            reason='Fictional regression test of explicit local acceptance only')
        self.assertEqual(reviewed['status'], 'READY_FOR_EXPLICIT_INPUT_CHECK')
        self.assertFalse(reviewed['human_identity_authenticated'])
        self.assertFalse(reviewed['order_allowed'])
        return preview, reviewed

    def create_schedule_task(self, prices, context_ref, *, research=None):
        options = dict(title='FICTIONAL schedule test', strategy='event.earnings_schedule@1',
            snapshot=prices['ref'], event_context=context_ref, params=PARAMS,
            score_start='2024-11-11', score_end='2024-12-03', initial_cash=10000,
            fee_rate=.0008, slippage_pct=.0005)
        if research is not None:
            options['research'] = research
        return self.act('create_task', **options)

    def test_explicit_review_create_run_export_retains_original_source_and_version(self):
        prices = self.prices()
        _, reviewed = self.approve_for_test()
        task = self.create_schedule_task(prices, reviewed['input']['ref'], research=reviewed['ref'])
        run = self.act('run_task', task=task['ref'])
        exported = self.act('export_research_result', research=reviewed['ref'], run=run['ref'])
        folder = self.app.path(exported['ref'], 'exports')
        self.assertEqual(exported['status'], 'FROZEN_RESEARCH_RETURN_READY')
        self.assertEqual((folder / 'project-source.raw').read_bytes(), self.source_raw)
        self.assertEqual((folder / 'collaboration-result.json').read_bytes(), self.result_raw)
        self.assertEqual((folder / 'event-context.json').read_bytes(), self.context_raw)
        project_source = next(row for row in read_document(folder / 'collaboration-result.json')
                              ['source_manifest'] if row['source_kind'] == 'project_source')
        self.assertEqual(project_source['record_sha256'], hashlib.sha256(self.source_raw).hexdigest())
        self.assertEqual(read_document(folder / 'human-confirmation.json')['actor'], 'FICTIONAL_TEST_OPERATOR')
        binding = read_document(folder / 'task-input-binding.json')
        self.assertEqual(binding['task_id'], task['task_id'])
        self.assertEqual(binding['research'], reviewed['ref'])
        self.assertEqual(binding['assessment_hash'], reviewed['assessment_hash'])
        self.assertEqual(binding['revision'], task['viewed_revision'])
        self.assertEqual(run['inputs']['management']['revision'], task['viewed_revision'])
        self.assertEqual(run['inputs']['event_context_hash'], reviewed['context_hash'])
        self.assertFalse(read_document(self.app.path(run['ref'], 'runs') / 'inputs.json')
                         ['execution_permission']['order_allowed'])

    def test_previous_run_cannot_be_retroactively_claimed_by_later_review(self):
        prices = self.prices()
        direct = self.act('import_input', content_base64=self.b64(self.context_raw))
        old_task = self.create_schedule_task(prices, direct['ref'])
        old_run = self.act('run_task', task=old_task['ref'])
        _, reviewed = self.approve_for_test()
        with self.assertRaisesRegex(ValueError, 'saved_result_predates_this_research_binding'):
            self.act('export_research_result', research=reviewed['ref'], run=old_run['ref'])
        bound = self.act('bind_research', research=reviewed['ref'], task=old_task['ref'])
        self.assertNotEqual(bound['viewed_revision'], old_task['viewed_revision'])
        self.assertNotEqual(bound['task_id'], old_task['task_id'])
        new_run = self.act('run_task', task=old_task['ref'])
        self.assertNotEqual(new_run['ref'], old_run['ref'])
        exported = self.act('export_research_result', research=reviewed['ref'], run=new_run['ref'])
        self.assertEqual(exported['status'], 'FROZEN_RESEARCH_RETURN_READY')
        self.assertEqual(read_document(self.app.path(exported['ref'], 'exports') / 'task-input-binding.json')['task_id'],
                         bound['task_id'])

    def test_changed_confirmation_context_result_or_source_is_rejected(self):
        prices = self.prices()
        for name in ('confirmation.json', 'event-context.json', 'collaboration-result.json',
                     'project-source.raw'):
            with self.subTest(name=name):
                _, reviewed = self.approve_for_test()
                path = self.app.path(reviewed['ref'], 'research-imports') / name
                path.write_bytes(path.read_bytes() + b' ')
                reason = ('research_original_source_hash_mismatch' if name == 'project-source.raw'
                          else 'research_confirmation_or_retained_bytes_changed')
                with self.assertRaisesRegex(ValueError, reason):
                    self.create_schedule_task(prices, reviewed['input']['ref'], research=reviewed['ref'])
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])

    def test_malformed_source_manifest_has_durable_stopped_result_not_unknown_retry(self):
        malformed = json.loads(self.result_raw)
        malformed['source_manifest'] = [1]
        request = dict(action='preview_research', operation_id='malformed-source-123',
            security_id=SECURITY, result_base64=self.b64(_encoded(malformed)),
            context_base64=self.b64(self.context_raw), source_base64=self.b64(self.source_raw))
        with self.assertRaisesRegex(ValueError, 'research_source_manifest_invalid'):
            self.app.action(request)
        receipt = read_document(self.root / 'operations/malformed-source-123/result.json')
        self.assertEqual(receipt['status'], 'STOPPED')
        self.assertFalse(receipt['automatic_retry'])
        with self.assertRaisesRegex(ValueError, 'research_source_manifest_invalid'):
            self.app.action(request)
        self.assertFalse((self.root / 'operations/malformed-source-123/request.json').is_symlink())
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
