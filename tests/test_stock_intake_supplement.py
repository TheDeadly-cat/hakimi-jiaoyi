"""Contract fixtures only: no real provider or real completeness acceptance.

QA_READER parses the fictional source format below; it is deliberately defined
only in this test file, never registered as a production source reader.
"""
import base64
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import daily_updates as daily
from hakimi_research import stock_intake as intake
from hakimi_research import stock_intake_supplement as supplement
from hakimi_research.documents import digest
from hakimi_research.equity_dataset import verify_equity_snapshot
from test_daily_updates import encoded, source_reply


def qa_page_reader(raw):
    doc = json.loads(raw)
    if set(doc) != {'fixture_kind', 'source_page'} or doc['fixture_kind'] != 'SYNTHETIC_SOURCE_CONTRACT_ONLY':
        raise ValueError('not_a_qa_source_page')
    return doc['source_page']


QA_READER = supplement.SourceReader('qa-fixture-only-v1', qa_page_reader)


class StockIntakeSupplementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='supplement-contract-qa-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = daily._clock('2026-10-23T21:00:00Z')
        self.source_at = '2026-10-24T10:00:00Z'
        self.review_at = '2026-10-24T11:00:00Z'
        self.counter = 0
        self.network = patch('socket.socket.connect', side_effect=AssertionError('No network in contract fixtures'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.artifacts = self.original()

    def payload(self, now=None):
        instant = now or self.now
        _, _, _, first, last = intake._coverage(instant, 20, 'XNAS')
        raw = source_reply((date.fromisoformat(first) - timedelta(days=120)).isoformat(), last)
        result = raw['chart']['result'][0]
        result['meta'].update(dataGranularity='1d', longName='Fictional TEST Corporation')
        result.pop('events')
        return raw

    def original(self, payload=None, now=None):
        self.counter += 1
        folder = self.root / ('check-' + str(self.counter))
        raw = encoded(payload if payload is not None else self.payload(now))
        checked = intake.check_stock_import('TEST', 20, folder, now=now or self.now, fetcher=lambda _: raw)
        self.assertEqual(checked['reason'], 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')
        self.assertFalse(checked['can_save'])
        return {name: (folder / name).read_bytes() for name in supplement.ARTIFACTS}

    def evidence(self, artifacts=None):
        artifacts = artifacts or self.artifacts
        original = json.loads(artifacts['check.json'])
        form = supplement.supplement_template(artifacts)
        form.update(source_contract_id=QA_READER.contract_id, source_name='Fictional coverage export, QA ONLY',
                    source_reference='urn:qa:complete-action-source', retrieved_at=self.source_at)
        security = {k: original['security'][k] for k in ('symbol', 'exchange', 'currency', 'instrument_type')}
        security['source_security_id'] = 'QA:SOURCE:TEST'
        row = dict(security=security, coverage_start=original['query_start'], coverage_end=original['coverage_end'],
                   date_basis='EFFECTIVE_DATE', coverage_status='COMPLETE',
                   covered_action_types=list(supplement.ACTION_TYPES), as_of=self.source_at,
                   page_id='p1', page_index=1, total_pages=1, next_page_id=None, total_records=0, actions=[])
        self.set_pages(form, [row])
        return form

    def set_pages(self, evidence, rows):
        evidence['pages'] = [dict(source_reference='urn:qa:page:' + str(i), raw_base64=base64.b64encode(
            encoded(dict(fixture_kind='SYNTHETIC_SOURCE_CONTRACT_ONLY', source_page=row))).decode())
            for i, row in enumerate(rows)]

    def page(self, evidence, index=0):
        return qa_page_reader(base64.b64decode(evidence['pages'][index]['raw_base64']))

    def review(self, evidence=None, artifacts=None, **kwargs):
        return supplement.review_stock_supplement(artifacts or self.artifacts,
            evidence if evidence is not None else self.evidence(artifacts),
            checked_at=kwargs.pop('checked_at', self.review_at), source_reader=kwargs.pop('source_reader', QA_READER), **kwargs)

    def assert_blocked(self, evidence, reason, artifacts=None, **kwargs):
        result = self.review(evidence, artifacts, **kwargs)
        self.assertFalse(result['can_save'])
        self.assertIn(reason, result['reason'])
        self.assertIsNone(result['candidate_snapshot_id'])
        return result

    def test_default_reader_and_unfilled_template_never_make_a_source_claim(self):
        before = deepcopy(self.artifacts)
        template = supplement.supplement_template(self.artifacts)
        self.assertEqual(template['pages'], [])
        self.assertIsNone(template['source_contract_id'])
        self.assert_blocked(template, 'SOURCE_READER_NOT_CONFIGURED', source_reader=None)
        self.assert_blocked(self.evidence(), 'SOURCE_READER_NOT_CONFIGURED', source_reader=None)
        self.assertEqual(self.artifacts, before)
        self.assertFalse((self.root / 'data').exists())

    def test_complete_source_is_a_new_unverified_review_and_old_bytes_stay_blocked(self):
        originals = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        evidence = self.evidence()
        unchanged = deepcopy(evidence)
        reviewed = self.review(evidence)
        self.assertEqual(reviewed['status'], 'REVIEW_REQUIRED')
        self.assertTrue(reviewed['can_save'])
        self.assertEqual(reviewed['source_event_coverage'], 'UNKNOWN')
        self.assertEqual(reviewed['supplemental_coverage'], 'DECLARED_COMPLETE')
        self.assertFalse(reviewed['source_truth_verified'])
        self.assertFalse(reviewed['source_authenticated'])
        self.assertEqual(reviewed['evidence_kind'], 'IMPORTED_UNVERIFIED')
        self.assertEqual(reviewed['session_count'], 20)
        self.assertTrue(all(value == 0 for value in reviewed['permissions'].values()))
        self.assertEqual(json.loads(self.artifacts['check.json'])['status'], 'BLOCKED')
        self.assertEqual(evidence, unchanged)
        self.assertEqual({str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}, originals)

    def test_snapshot_reuses_canonical_verifier_and_retains_three_times_and_all_originals(self):
        evidence = self.evidence()
        check = self.review(evidence)
        built = supplement.build_supplemented_snapshot(self.artifacts, evidence, checked_at=self.review_at,
            expected_check_hash=check['check_hash'], confirmed_security=check['binding']['security'], source_reader=QA_READER)
        snapshot = built['snapshot']
        self.assertEqual(verify_equity_snapshot(snapshot), snapshot)
        self.assertEqual(snapshot['snapshot_id'], check['candidate_snapshot_id'])
        self.assertEqual(snapshot['schema_version'], 'us-equity-daily-snapshot-v1')
        self.assertEqual(snapshot['retrieved_at'], self.review_at)
        self.assertEqual(snapshot['price_source']['retrieved_at'], self.review_at)
        self.assertEqual(snapshot['corporate_actions']['source']['retrieved_at'], self.review_at)
        self.assertIn('Derived retained Yahoo', snapshot['price_source']['name'])
        proof = json.loads(base64.b64decode(snapshot['corporate_actions']['source']['raw_base64']))
        self.assertEqual(proof['source_event_coverage'], 'UNKNOWN')
        self.assertEqual(proof['times'], dict(original_price_retrieved_at='2026-10-23T21:00:00Z',
                         supplemental_retrieved_at=self.source_at, supplement_checked_at=self.review_at))
        for name, raw in self.artifacts.items():
            self.assertEqual(base64.b64decode(proof['retained_originals'][name]['raw_base64']), raw)
        self.assertNotIn('events', json.loads(base64.b64decode(proof['retained_originals']['source-original.bin']['raw_base64']))['chart']['result'][0])
        self.assertFalse(snapshot['order_allowed'])
        self.assertFalse(snapshot['research_admission']['source_truth_verified'])

    def test_original_artifact_hashes_check_hash_request_security_and_range_are_bound(self):
        for name in supplement.ARTIFACTS:
            changed = deepcopy(self.artifacts)
            changed[name] += b' '
            if name == 'check.json':
                # Encoding alone is retained; the original check's content hash
                # is still valid. Changing a field without its hash is not.
                doc = json.loads(changed[name]); doc['symbol'] = 'OTHER'; changed[name] = encoded(doc)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.review(artifacts=changed)
        for field, value in (('security', {}), ('coverage_start', '2026-01-01'), ('history_sessions', True)):
            changed = deepcopy(self.artifacts)
            doc = json.loads(changed['check.json']); doc[field] = value
            doc['check_hash'] = digest({k: v for k, v in doc.items() if k != 'check_hash'})
            changed['check.json'] = encoded(doc)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.review(artifacts=changed)

    def test_supplement_binding_must_match_every_original_identity(self):
        base = self.evidence()
        for key in base['binding']:
            changed = deepcopy(base); changed['binding'][key] = 'changed'
            with self.subTest(key=key):
                self.assert_blocked(changed, 'EVIDENCE_BINDING_CHANGED')

    def test_source_security_range_type_and_explicit_coverage_are_required(self):
        for field, value, reason in (
            ('coverage_start', '2026-10-23', 'SOURCE_COVERAGE_INCOMPLETE'),
            ('coverage_end', '2026-10-22', 'SOURCE_COVERAGE_INCOMPLETE'),
            ('coverage_status', 'UNKNOWN', 'SOURCE_COVERAGE_NOT_EXPLICIT_COMPLETE'),
            ('date_basis', 'ANNOUNCEMENT_DATE', 'SOURCE_COVERAGE_NOT_EXPLICIT_COMPLETE'),
            ('covered_action_types', ['SPLIT'], 'SOURCE_ACTION_TYPES_INCOMPLETE')):
            evidence = self.evidence(); row = self.page(evidence); row[field] = value; self.set_pages(evidence, [row])
            with self.subTest(field=field): self.assert_blocked(evidence, reason)
        for key, value in (('symbol', 'OTHER'), ('currency', 'HKD'), ('exchange', 'XNYS'), ('instrument_type', 'ETF')):
            evidence = self.evidence(); row = self.page(evidence); row['security'][key] = value; self.set_pages(evidence, [row])
            with self.subTest(key=key): self.assert_blocked(evidence, 'SOURCE_SECURITY_MISMATCH')

    def test_user_checkbox_empty_list_missing_raw_fields_and_unknown_contract_cannot_substitute(self):
        evidence = self.evidence(); evidence['complete'] = True
        self.assert_blocked(evidence, 'EVIDENCE_FIELDS_INVALID')
        evidence = self.evidence(); evidence['pages'] = []
        self.assert_blocked(evidence, 'ORIGINAL_SOURCE_PAGES_REQUIRED')
        evidence = self.evidence(); evidence['source_contract_id'] = 'not-reviewed'
        self.assert_blocked(evidence, 'SOURCE_CONTRACT_MISMATCH')
        evidence = self.evidence(); evidence['evidence_type'] = 'USER_ASSERTION'
        self.assert_blocked(evidence, 'SOURCE_EVIDENCE_TYPE_UNSUPPORTED')
        for missing in ('coverage_status', 'actions', 'total_records', 'next_page_id'):
            evidence = self.evidence(); row = self.page(evidence); row.pop(missing); self.set_pages(evidence, [row])
            with self.subTest(missing=missing): self.assert_blocked(evidence, 'SOURCE_PAGE_PROJECTION_FIELDS_INVALID')

    def test_pagination_and_explicit_zero_count_are_checked_not_assumed(self):
        for field, value, reason in (
            ('total_pages', 2, 'SOURCE_PAGE_SEQUENCE_INCOMPLETE'),
            ('page_index', True, 'SOURCE_PAGE_SEQUENCE_INCOMPLETE'),
            ('next_page_id', 'missing', 'SOURCE_PAGINATION_NOT_FINISHED'),
            ('total_records', 1, 'SOURCE_RESULT_COUNT_INCOMPLETE'),
            ('total_records', False, 'SOURCE_TOTAL_RECORDS_INVALID')):
            evidence = self.evidence(); row = self.page(evidence); row[field] = value; self.set_pages(evidence, [row])
            with self.subTest(field=field): self.assert_blocked(evidence, reason)

    def event(self, evidence, day):
        return dict(action_id='qa-event-1', security_id='QA:SOURCE:TEST', action_type='SPLIT',
                    effective_date=day, source_reference='urn:qa:event-1', details={'numerator': 2, 'denominator': 1})

    def test_complete_two_page_source_preserves_outside_events_and_rejects_duplicates(self):
        evidence = self.evidence(); row1 = self.page(evidence); row2 = deepcopy(row1)
        row1.update(total_pages=2, next_page_id='p2', total_records=1,
                    actions=[self.event(evidence, row1['coverage_start'])])
        row2.update(page_id='p2', page_index=2, total_pages=2, total_records=1)
        self.set_pages(evidence, [row1, row2])
        result = self.review(evidence)
        self.assertTrue(result['can_save'])
        self.assertEqual(len(result['outside_window_actions']), 1)
        self.assertEqual(len(result['source_projection']['pages']), 2)
        row2['actions'] = deepcopy(row1['actions']); row1['total_records'] = row2['total_records'] = 2
        self.set_pages(evidence, [row1, row2])
        self.assert_blocked(evidence, 'SOURCE_DUPLICATE_ACTION')
        row2['actions'] = []; row2['page_id'] = row1['page_id']; row1['next_page_id'] = row2['page_id']
        self.set_pages(evidence, [row1, row2])
        self.assert_blocked(evidence, 'SOURCE_DUPLICATE_PAGE')

    def test_in_window_actions_remain_blocked_and_no_action_accounting_is_invented(self):
        for kind in supplement.ACTION_TYPES:
            evidence = self.evidence(); row = self.page(evidence)
            event = self.event(evidence, evidence['binding']['coverage_start']); event['action_type'] = kind
            row.update(total_records=1, actions=[event]); self.set_pages(evidence, [row])
            with self.subTest(kind=kind):
                result = self.assert_blocked(evidence, 'CORPORATE_ACTION_IN_WINDOW:qa-event-1')
                self.assertEqual(result['stop_details']['action'], event)

    def test_three_clocks_do_not_backdate_new_evidence_or_extend_the_price_window(self):
        evidence = self.evidence(); evidence['retrieved_at'] = '2026-10-25T10:00:00Z'
        self.assert_blocked(evidence, 'SOURCE_RECEIVED_AFTER_CHECK')
        evidence = self.evidence(); row = self.page(evidence); row['as_of'] = '2026-10-22T20:00:00Z'; self.set_pages(evidence, [row])
        self.assert_blocked(evidence, 'SOURCE_ASOF_OUTSIDE_KNOWN_WINDOW')
        evidence = self.evidence(); row = self.page(evidence); row['as_of'] = '2026-10-24T10:01:00Z'; self.set_pages(evidence, [row])
        self.assert_blocked(evidence, 'SOURCE_ASOF_OUTSIDE_KNOWN_WINDOW')
        with self.assertRaisesRegex(ValueError, 'CHECK_BEFORE_PRICE_RECEIPT'):
            self.review(checked_at='2026-10-22T20:00:00Z')
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_TIMEZONE_REQUIRED'):
            self.review(checked_at='2026-10-24T11:00:00')
        later = self.review(checked_at='2026-10-28T23:00:00Z')
        self.assertEqual(later['binding']['coverage_end'], '2026-10-23')
        self.assertEqual(later['session_count'], 20)

    def test_complete_evidence_still_runs_all_ohlcv_and_completion_checks(self):
        cases = []
        raw = self.payload(); raw['chart']['result'][0]['indicators']['quote'][0]['low'][-1] = 100000; cases.append((raw, 'SOURCE_OHLC_GEOMETRY_INVALID'))
        raw = self.payload(); raw['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][-1] -= 1; cases.append((raw, 'SOURCE_ADJUSTED_RAW_MISMATCH'))
        raw = self.payload(); raw['chart']['result'][0]['indicators']['quote'][0]['volume'][-1] = 1.5; cases.append((raw, 'SOURCE_MISSING_OR_INVALID_OHLCV'))
        raw = self.payload(); raw['chart']['result'][0]['meta']['regularMarketTime'] += 7200; cases.append((raw, 'SOURCE_COMPLETION_CLOCK_IN_FUTURE'))
        raw = self.payload(); raw['chart']['result'][0]['timestamp'][-1] -= 1; cases.append((raw, 'SOURCE_NON_RTH_DAILY_TIMESTAMP'))
        raw = self.payload(); r = raw['chart']['result'][0]; r['timestamp'].pop(-1)
        for values in r['indicators']['quote'][0].values(): values.pop(-1)
        r['indicators']['adjclose'][0]['adjclose'].pop(-1); cases.append((raw, 'SOURCE_MISSING_COMPLETED_SESSIONS'))
        for payload, reason in cases:
            with self.subTest(reason=reason):
                artifacts = self.original(payload)
                self.assert_blocked(self.evidence(artifacts), reason, artifacts=artifacts)

    def test_old_wrapper_missing_event_rejection_has_priority_and_unchanged_success_values(self):
        checked, calendar, days, fields, binding = supplement._original(self.artifacts)
        args = ({'security': binding['security']}, days, binding['coverage_end'], self.now, checked['query_start'], calendar)
        with self.assertRaisesRegex(ValueError, 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN'):
            daily._rows(self.artifacts['source-original.bin'], *args)
        # A separate synthetic source explicitly contains events. Never patch
        # the native retained original to obtain a passing response.
        fixture = self.payload(); fixture['chart']['result'][0]['events'] = {}
        prior = daily._rows(encoded(fixture), *args)
        rows, excluded, meta, prefix = daily._price_rows(fields, days, binding['coverage_end'], self.now, checked['query_start'], calendar)
        self.assertEqual(prior, (rows, excluded, [], meta, prefix))

    def test_forming_bar_is_excluded_using_original_receipt_not_new_review_clock(self):
        now = daily._clock('2026-10-23T15:00:00Z')
        fixture = self.payload(now)
        result = fixture['chart']['result'][0]
        calendar, _, _, _, _ = intake._coverage(now, 20, 'XNAS')
        today = daily._days(calendar, date(2026, 10, 23), date(2026, 10, 23))[0]
        result['timestamp'].append(int(daily._clock(today['open_utc']).timestamp()))
        for values in result['indicators']['quote'][0].values(): values.append(None)
        result['indicators']['adjclose'][0]['adjclose'].append(None)
        result['meta']['regularMarketTime'] = int(now.timestamp())
        result['meta']['currentTradingPeriod']['regular'] = {
            'start': int(daily._clock(today['open_utc']).timestamp()),
            'end': int(daily._clock(today['close_utc']).timestamp())}
        artifacts = self.original(fixture, now)
        result = self.review(self.evidence(artifacts), artifacts=artifacts)
        self.assertTrue(result['can_save'])
        self.assertEqual(result['binding']['coverage_end'], '2026-10-22')
        self.assertEqual(result['session_count'], 20)
        self.assertEqual(result['excluded_forming_sessions'], ['2026-10-23'])

    def test_unknown_action_and_page_conflicting_coverage_cannot_be_ignored(self):
        evidence = self.evidence(); row1 = self.page(evidence); row2 = deepcopy(row1)
        row1.update(total_pages=2, next_page_id='p2')
        row2.update(page_id='p2', page_index=2, total_pages=2, as_of='2026-10-24T09:00:00Z')
        self.set_pages(evidence, [row1, row2])
        self.assert_blocked(evidence, 'SOURCE_PAGE_COVERAGE_CONFLICT')
        evidence = self.evidence(); row = self.page(evidence)
        event = self.event(evidence, row['coverage_start']); event['action_type'] = 'UNRECOGNIZED_DISTRIBUTION'
        row.update(actions=[event], total_records=1); self.set_pages(evidence, [row])
        self.assert_blocked(evidence, 'SOURCE_ACTION_KIND_UNSUPPORTED')

    def test_exact_confirmation_and_recomputed_source_bytes_bind_build(self):
        evidence = self.evidence(); check = self.review(evidence)
        args = dict(checked_at=self.review_at, expected_check_hash=check['check_hash'],
                    confirmed_security=check['binding']['security'], source_reader=QA_READER)
        with self.assertRaisesRegex(ValueError, 'EXACT_SECURITY_CONFIRMATION_REQUIRED'):
            supplement.build_supplemented_snapshot(self.artifacts, evidence, **dict(args, confirmed_security={}))
        changed = deepcopy(evidence); changed['pages'][0]['raw_base64'] = base64.b64encode(
            base64.b64decode(changed['pages'][0]['raw_base64']) + b' ').decode()
        with self.assertRaisesRegex(ValueError, 'CHECK_IDENTITY_CHANGED'):
            supplement.build_supplemented_snapshot(self.artifacts, changed, **args)
        self.assertFalse((self.root / 'data').exists())


if __name__ == '__main__':
    unittest.main()
