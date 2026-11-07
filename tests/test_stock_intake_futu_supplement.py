"""Synthetic retained prices and collector replies; zero real provider calls.

Ordinary-import declarations exercise production admission without representing
these fictional TEST prices, records or missing SDK metadata as real evidence.
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
from hakimi_research import stock_intake_supplement as original
from hakimi_research import stock_intake_futu_supplement as supplement
from hakimi_research import futu_rehab_evidence as reader
from hakimi_research.documents import digest
from hakimi_research.equity_dataset import verify_equity_snapshot
from test_daily_updates import encoded, source_reply
from test_futu_rehab_evidence import fixture as collector_fixture, split


class FutuSupplementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='new-futu-supplement-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = daily._clock('2026-10-23T21:00:00Z')
        self.review_at = '2026-10-24T11:00:00Z'
        self.counter = 0
        blocker = patch('socket.socket.connect', side_effect=AssertionError('No source request'))
        blocker.start(); self.addCleanup(blocker.stop)
        self.prices = self.original()
        self.actions = self.collector()

    def payload(self, now=None, *, include_forming=False):
        instant = now or self.now
        _, _, _, first, last = intake._coverage(instant, 20, 'XNAS')
        raw = source_reply((date.fromisoformat(first) - timedelta(days=120)).isoformat(),
                           instant.astimezone(daily._NY).date().isoformat() if include_forming else last)
        result = raw['chart']['result'][0]
        result['meta'].update(dataGranularity='1d', longName='FICTIONAL TEST source')
        if include_forming:
            result['meta']['regularMarketTime'] = int(instant.timestamp())
        result.pop('events')
        return raw

    def original(self, payload=None, now=None):
        self.counter += 1
        folder = self.root / ('check-' + str(self.counter))
        raw = encoded(payload if payload is not None else self.payload(now))
        checked = intake.check_stock_import('TEST', 20, folder, now=now or self.now, fetcher=lambda _: raw)
        self.assertEqual(checked['reason'], 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')
        return {name: (folder / name).read_bytes() for name in original.ARTIFACTS}

    def collector(self, rows=None):
        values = collector_fixture(rows)
        times = dict(security_request='2026-10-24T10:00:00Z', security_response='2026-10-24T10:00:01Z',
                     actions_request='2026-10-24T10:00:02Z', actions_response='2026-10-24T10:00:03Z')
        for key, raw in values.items():
            doc = json.loads(raw)
            if key.endswith('request'):
                doc['started_at'] = times[key]
                kwargs = doc['request']['kwargs']
                if key == 'security_request': kwargs['code_list'] = ['US.TEST']
                else: kwargs['code'] = 'US.TEST'
            else:
                doc['completed_at'] = times[key]
                if key == 'security_response':
                    doc['returned_reply']['rows'][0]['code'] = 'US.TEST'
                    doc['sdk_decoded_protocol_reply'][2][0]['code'] = 'US.TEST'
            values[key] = encoded(doc)
        return values

    def review(self, artifacts=None, prices=None, at=None):
        return supplement.review_futu_supplement(prices or self.prices,
            self.actions if artifacts is None else artifacts, checked_at=at or self.review_at)

    def build(self, check=None, **updates):
        check = check or self.review()
        args = dict(checked_at=self.review_at, expected_check_hash=check['check_hash'],
            confirmed_security=check['binding']['security'], acknowledge_source_limits=True)
        args.update(updates)
        return supplement.build_futu_supplement(self.prices, self.actions, **args)

    def edit(self, artifacts, key, change):
        result = deepcopy(artifacts); doc = json.loads(result[key]); change(doc); result[key] = encoded(doc)
        return result

    def assert_blocked(self, artifacts=None, prices=None, reason=None, at=None):
        result = self.review(artifacts, prices, at)
        self.assertFalse(result['can_save'])
        self.assertIsNone(result['candidate_snapshot_id'])
        self.assertIsNone(result['candidate_csv_sha256'])
        if reason: self.assertIn(reason, result['reason'])
        return result

    def test_success_has_new_identity_and_never_promotes_source_coverage(self):
        before = deepcopy((self.prices, self.actions))
        checked = self.review()
        self.assertEqual(checked['schema_version'], 'workbench-stock-futu-supplement-v2')
        self.assertEqual(checked['policy_id'], supplement.POLICY_ID)
        self.assertEqual(checked['status'], 'REVIEW_REQUIRED')
        self.assertTrue(checked['can_save'])
        self.assertEqual(checked['source_event_coverage'], 'UNKNOWN')
        self.assertEqual(checked['source_asof'], 'UNKNOWN')
        self.assertFalse(checked['importer_declaration']['source_claim_complete'])
        self.assertIsNone(checked['importer_declaration']['futu_currency'])
        self.assertEqual(checked['importer_declaration']['currency_source'], 'ORIGINAL_YAHOO_META_CURRENCY')
        self.assertEqual(checked['session_count'], 20)
        self.assertNotIn('snapshot', checked)
        self.assertEqual(checked, self.review())
        self.assertEqual((self.prices, self.actions), before)

    def test_canonical_snapshot_verified_and_all_eight_originals_retained(self):
        built = self.build(); checked, snapshot = built['check'], built['snapshot']
        self.assertEqual(verify_equity_snapshot(snapshot), snapshot)
        self.assertEqual(snapshot['snapshot_id'], checked['candidate_snapshot_id'])
        self.assertEqual(snapshot['evidence_kind'], 'IMPORTED_UNVERIFIED')
        self.assertEqual(snapshot['corporate_actions']['coverage_status'], 'DECLARED_COMPLETE')
        self.assertIn('IMPORT POLICY declaration only', snapshot['corporate_actions']['source']['name'])
        proof = json.loads(base64.b64decode(snapshot['corporate_actions']['source']['raw_base64']))
        self.assertEqual(proof['source_event_coverage'], 'UNKNOWN')
        self.assertEqual(proof['source_asof'], 'UNKNOWN')
        self.assertEqual(proof['reader_diagnostic']['status'], 'NO_REPORTED_ACTION_IN_WINDOW')
        for name, raw in self.prices.items():
            self.assertEqual(base64.b64decode(proof['retained_originals'][name]['raw_base64']), raw)
        for name, raw in self.actions.items():
            self.assertEqual(base64.b64decode(proof['reader_diagnostic']['retained_artifacts'][name]['raw_base64']), raw)
        self.assertEqual(proof['times']['original_price_retrieved_at'], '2026-10-23T21:00:00Z')
        self.assertEqual(proof['times']['supplemental_retrieved_at'], '2026-10-24T10:00:03Z')
        self.assertEqual(proof['times']['supplement_checked_at'], self.review_at)
        self.assertFalse(any(checked['permissions'].values()))
        for key in ('paper_allowed', 'live_allowed', 'order_allowed'):
            self.assertFalse(snapshot[key])

    def test_explicit_exact_confirmation_limits_ack_and_rebuild_are_required(self):
        checked = self.review()
        for updates, reason in ((dict(expected_check_hash='0' * 64), 'CHECK_IDENTITY_CHANGED'),
            (dict(confirmed_security=dict(checked['binding']['security'], symbol='OTHER')), 'EXACT_SECURITY_CONFIRMATION'),
            (dict(acknowledge_source_limits=False), 'SOURCE_LIMITS_ACKNOWLEDGEMENT'),
            (dict(acknowledge_source_limits=1), 'SOURCE_LIMITS_ACKNOWLEDGEMENT'),
            (dict(checked_at='2026-10-24T11:00:01Z'), 'CHECK_IDENTITY_CHANGED')):
            with self.subTest(updates=updates), self.assertRaisesRegex(ValueError, reason): self.build(checked, **updates)
        self.actions['actions_response'] += b' '
        with self.assertRaisesRegex(ValueError, 'CHECK_IDENTITY_CHANGED'): self.build(checked)

    def test_only_missing_events_original_is_eligible_and_old_bytes_stay_unchanged(self):
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.build()
        after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(json.loads(self.prices['check.json'])['status'], 'BLOCKED')
        self.assertNotIn('events', json.loads(self.prices['source-original.bin'])['chart']['result'][0])
        changed = deepcopy(self.prices); doc = json.loads(changed['check.json'])
        doc['reason'] = 'OTHER_BLOCKER'; doc['check_hash'] = digest({k:v for k,v in doc.items() if k != 'check_hash'})
        changed['check.json'] = encoded(doc)
        with self.assertRaises(ValueError): self.review(prices=changed)
        for name in ('source-original.bin', 'calendar.json', 'request-started.json'):
            changed = deepcopy(self.prices); changed[name] += b' '
            with self.subTest(name=name), self.assertRaises(ValueError): self.review(prices=changed)

    def test_missing_four_piece_evidence_or_sdk_rows_never_passes_a_checkbox(self):
        self.assert_blocked({}, reason='RETAINED_EVIDENCE_INCOMPLETE')
        for key in self.actions:
            missing = deepcopy(self.actions); missing.pop(key)
            self.assert_blocked(missing, reason='RETAINED_EVIDENCE_INCOMPLETE')
        for field in ('sdk_decoded_protocol_reply',):
            changed = self.edit(self.actions, 'actions_response', lambda doc: doc.pop(field))
            self.assert_blocked(changed, reason='RETAINED_EVIDENCE_INCOMPLETE')
        changed = self.edit(self.actions, 'actions_response', lambda doc: doc['returned_reply'].pop('rows'))
        changed = self.edit(changed, 'actions_response', lambda doc: doc.update(coverage_status='COMPLETE', complete=True))
        self.assert_blocked(changed, reason='RETAINED_EVIDENCE_INCOMPLETE')

    def test_real_success_empty_array_is_observation_not_fabricated_complete(self):
        checked = self.review()
        diag = checked['reader_diagnostic']
        self.assertEqual(diag['paging']['observed_record_count'], 0)
        self.assertEqual(diag['paging']['provider_total'], 'UNAVAILABLE')
        self.assertEqual(diag['paging']['status'], 'NOT_APPLICABLE_TO_PROTOCOL')
        self.assertEqual(diag['collector_identity']['sdk_version'], 'UNKNOWN')
        self.assertEqual(diag['collector_identity']['capture_batch'], 'UNKNOWN')
        self.assertFalse(diag['canonical_admission'])
        self.assertEqual(diag['row_comparison']['actions']['status'], 'MATCHED')

    def test_exact_futu_yahoo_identity_and_optional_currency_conflicts_block(self):
        for updates in (dict(code='US.OTHER'), dict(exchange_type='US_NYSE'), dict(stock_type='ETF'),
                        dict(stock_id=True), dict(lot_size=100), dict(delisting=True), dict(currency='EUR')):
            artifacts = deepcopy(self.actions)
            doc = json.loads(artifacts['security_response'])
            doc['sdk_decoded_protocol_reply'][2][0].update(updates)
            doc['returned_reply']['rows'][0].update(updates)
            artifacts['security_response'] = encoded(doc)
            with self.subTest(updates=updates): self.assert_blocked(artifacts)

    def test_any_window_action_is_blocked_and_outside_action_is_retained(self):
        checked = json.loads(self.prices['check.json'])
        for day in (checked['coverage_start'], checked['coverage_end']):
            self.assert_blocked(self.collector([split(day)]), reason='ACTION_IN_FIXED_WINDOW')
        row = split('2023-05-24')
        reviewed = self.review(self.collector([row]))
        self.assertTrue(reviewed['can_save'])
        self.assertEqual(reviewed['reader_diagnostic']['events'][0]['source_fields'], row)
        self.assertFalse(reviewed['reader_diagnostic']['events'][0]['inside_window'])

    def test_current_forming_day_action_is_not_ignored_as_outside_window(self):
        at = daily._clock('2026-10-23T15:00:00Z')
        prices = self.original(self.payload(at, include_forming=True), now=at)
        self.assertEqual(json.loads(prices['check.json'])['coverage_end'], '2026-10-22')
        self.assert_blocked(self.collector([split('2026-10-23')]), prices,
                            reason='POST_WINDOW_ACTION_MAY_AFFECT_PRICE_BASIS')
        clean = self.review(prices=prices)
        self.assertTrue(clean['can_save'])
        self.assertEqual(clean['excluded_forming_sessions'], ['2026-10-23'])

    def test_source_after_price_capture_does_not_rewrite_old_price_window(self):
        reviewed = self.review(self.collector([split('2026-10-24')]))
        self.assertTrue(reviewed['can_save'])
        self.assertEqual(reviewed['binding']['coverage_end'], '2026-10-23')
        self.assertFalse(reviewed['reader_diagnostic']['events'][0]['inside_window'])

    def test_source_times_cannot_be_after_check_or_before_price_window(self):
        self.assert_blocked(at='2026-10-24T10:00:02Z', reason='SOURCE_RECEIVED_AFTER_CHECK')
        changed = deepcopy(self.actions)
        for key in changed:
            doc = json.loads(changed[key]); field = 'started_at' if key.endswith('request') else 'completed_at'
            doc[field] = doc[field].replace('2026-10-24T10:', '2026-10-23T19:')
            changed[key] = encoded(doc)
        self.assert_blocked(changed, reason='SOURCE_BEFORE_FIXED_WINDOW_OR_PRICES')
        with self.assertRaisesRegex(ValueError, 'CHECK_BEFORE_PRICE_RECEIPT'):
            self.review(at='2026-10-23T20:59:59Z')

    def test_full_price_validation_cannot_be_bypassed_by_action_success(self):
        for kind in ('adjusted', 'geometry', 'volume', 'missing', 'forming_clock'):
            payload = self.payload(); row = payload['chart']['result'][0]
            if kind == 'adjusted': row['indicators']['adjclose'][0]['adjclose'][-1] -= 1
            elif kind == 'geometry': row['indicators']['quote'][0]['high'][-1] = 1
            elif kind == 'volume': row['indicators']['quote'][0]['volume'][-1] = -1
            elif kind == 'forming_clock': row['meta']['regularMarketTime'] = row['timestamp'][-1]
            else:
                row['timestamp'].pop(-2)
                for values in row['indicators']['quote'][0].values(): values.pop(-2)
                row['indicators']['adjclose'][0]['adjclose'].pop(-2)
            with self.subTest(kind=kind): self.assert_blocked(prices=self.original(payload), reason='SOURCE_')

    def test_conflicting_success_rows_and_unknown_actions_keep_diagnostic_evidence(self):
        artifacts = self.collector([split('2023-05-24')])
        artifacts = self.edit(artifacts, 'actions_response',
            lambda doc: doc['sdk_decoded_protocol_reply'][2][0].update(split_base=9))
        blocked = self.assert_blocked(artifacts, reason='RETAINED_EVIDENCE_INCOMPLETE')
        self.assertIn('SDK_AND_RETURNED_ROWS_CONFLICT:actions', blocked['reader_diagnostic']['issues'])
        self.assertEqual(base64.b64decode(blocked['reader_diagnostic']['retained_artifacts']['actions_response']['raw_base64']),
                         artifacts['actions_response'])
        row = split('2023-05-24'); row['unknown_action'] = 10
        self.assert_blocked(self.collector([row]), reason='RETAINED_EVIDENCE_INCOMPLETE')

    def test_review_and_build_do_no_io_and_modified_return_does_not_change_rebuild(self):
        with patch('builtins.open', side_effect=AssertionError('Pure review must not write or read files')), \
                patch.object(Path, 'open', side_effect=AssertionError('Pure review must not open files')):
            checked = self.review(); result = self.build(checked)
        checked['binding']['security']['symbol'] = 'MUTATED'
        result['snapshot']['security']['symbol'] = 'MUTATED'
        fresh = self.review()
        self.assertEqual(fresh['binding']['security']['symbol'], 'TEST')
        self.assertEqual(fresh['check_hash'], self.review()['check_hash'])
        self.assertEqual(fresh['economic_runs'], 0)

    def test_actual_dataframe_collector_representation_can_build_without_source_upgrade(self):
        row = split('2023-05-24'); row.update(split_ert=3.0, split_ratio=1 / 3)
        self.actions = self.collector([row])
        for label in ('security', 'actions'):
            doc = json.loads(self.actions[label + '_response'])
            doc['returned_reply']['rows'] = json.loads(reader.pd.DataFrame(doc['sdk_decoded_protocol_reply'][2],
                columns=reader.SDK_COLUMNS[label]).to_json(orient='records', double_precision=15))
            self.actions[label + '_response'] = encoded(doc)
        built = self.build()
        self.assertEqual(verify_equity_snapshot(built['snapshot']), built['snapshot'])
        self.assertEqual(built['check']['reader_diagnostic']['row_comparison']['actions']['method'],
                         'SDK_FIXED_COLUMNS_PANDAS_RECORDS_PRECISION_15')
        self.assertEqual(built['check']['source_event_coverage'], 'UNKNOWN')
        self.assertEqual(built['check']['reader_diagnostic']['collector_identity']['format'], 'RECOGNIZED_COLLECTOR_FORMAT')

    def test_old_complete_export_policy_is_not_reinterpreted_by_v2(self):
        old = original.review_stock_supplement(self.prices, original.supplement_template(self.prices),
                                               checked_at=self.review_at)
        self.assertFalse(old['can_save'])
        self.assertIn('SOURCE_READER_NOT_CONFIGURED', old['reason'])
        self.assertTrue(self.review()['can_save'])
        self.assertEqual(json.loads(self.prices['check.json'])['status'], 'BLOCKED')

    def test_original_and_source_mapping_order_never_changes_review_or_snapshot_identity(self):
        checked = self.review()
        built = self.build(checked)
        original_reordered = dict(reversed(list(self.prices.items())))
        source_reordered = dict(reversed(list(self.actions.items())))
        for prices, actions in ((original_reordered, self.actions),
                                (self.prices, source_reordered),
                                (original_reordered, source_reordered)):
            with self.subTest(original_keys=list(prices), source_keys=list(actions)):
                result = supplement.review_futu_supplement(prices, actions, checked_at=self.review_at)
                self.assertEqual(result['check_hash'], checked['check_hash'])
                self.assertEqual(result['candidate_snapshot_id'], checked['candidate_snapshot_id'])
                actual = supplement.build_futu_supplement(prices, actions, checked_at=self.review_at,
                    expected_check_hash=checked['check_hash'], confirmed_security=checked['binding']['security'],
                    acknowledge_source_limits=True)
                self.assertEqual(actual, built)
                self.assertEqual(verify_equity_snapshot(actual['snapshot']), actual['snapshot'])
                proof_raw = base64.b64decode(actual['snapshot']['corporate_actions']['source']['raw_base64'])
                self.assertEqual(proof_raw, base64.b64decode(built['snapshot']['corporate_actions']['source']['raw_base64']))
                proof = json.loads(proof_raw)
                for name, raw in self.prices.items():
                    self.assertEqual(base64.b64decode(proof['retained_originals'][name]['raw_base64']), raw)
                for name, raw in self.actions.items():
                    self.assertEqual(base64.b64decode(proof['reader_diagnostic']['retained_artifacts'][name]['raw_base64']), raw)


if __name__ == '__main__':
    unittest.main()
