"""Fictional prices/source replies only; no request to a live provider."""
import base64
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import daily_updates as updates
from hakimi_research.equity_dataset import build_equity_snapshot


def encoded(value):
    return (json.dumps(value, allow_nan=False) + '\n').encode()


def calendar_rows(first, last):
    calendar, _ = updates._calendar_window(date.fromisoformat(first).year, date.fromisoformat(last).year, 'XNYS')
    return updates._days(calendar, date.fromisoformat(first), date.fromisoformat(last))


def source_reply(first='2026-10-19', last='2026-10-23', *, exchange='XNAS'):
    sessions = [row for row in calendar_rows(first, last) if row['kind'] == 'OPEN']
    values = {key: [] for key in updates._FIELDS}
    for i, _ in enumerate(sessions):
        for key, value in zip(updates._FIELDS, [100 + i, 102 + i, 99 + i, 101 + i, 1000 + i]):
            values[key].append(value)
    epoch = lambda value: int(updates._clock(value).timestamp())
    regular = {'start': epoch(sessions[-1]['open_utc']), 'end': epoch(sessions[-1]['close_utc'])}
    return {'chart': {'error': None, 'result': [{'meta': {'symbol': 'TEST', 'currency': 'USD',
        'exchangeName': 'NYQ' if exchange == 'XNYS' else 'NMS', 'instrumentType': 'EQUITY', 'exchangeTimezoneName': 'America/New_York',
        'regularMarketTime': regular['end'], 'currentTradingPeriod': {'regular': regular}},
        'timestamp': [epoch(row['open_utc']) for row in sessions], 'events': {},
        'indicators': {'quote': [values], 'adjclose': [{'adjclose': values['close'][:]}]}}]}}


def baseline(first='2026-10-19', last='2026-10-22', *, exchange='XNAS'):
    days = calendar_rows(first, last)
    sessions = [row for row in days if row['kind'] == 'OPEN']
    raw = ('session_date,open,high,low,close,volume\n' + ''.join(
        f"{row['date']},{100+i},{102+i},{99+i},{101+i},{1000+i}\n" for i, row in enumerate(sessions))).encode()
    retrieved = max('2026-10-22T23:11:00Z', updates._stamp(updates._clock(sessions[-1]['close_utc']) + timedelta(seconds=60)))
    source = lambda kind, content: {'name': 'SYNTHETIC_TEST_' + kind,
        'reference': 'urn:synthetic:daily-update:' + kind, 'retrieved_at': retrieved,
        'raw_base64': base64.b64encode(content).decode()}
    manifest = {'schema_version': 'us-equity-daily-import-v1',
        'security': {'security_id': 'SYNTHETIC:DAILY:TEST', 'symbol': 'TEST', 'exchange': exchange,
                     'currency': 'USD', 'instrument_type': 'COMMON_STOCK'},
        'identity': {'stable_within_coverage': True, 'valid_from': first, 'valid_through': last,
            'selection_basis': 'Fictional input; imported flag exercises the production gate only.',
            'source': source('identity', b'Fictional security identity')},
        'calendar': {'timezone': 'America/New_York', 'coverage_start': first, 'coverage_end': last,
            'days': days, 'source': source('calendar', encoded(days))},
        'corporate_actions': {'coverage_start': first, 'coverage_end': last, 'coverage_status': 'DECLARED_COMPLETE',
            'actions': [], 'source': source('actions', b'Fictional declared empty actions')},
        'price_source': source('prices', raw), 'price_basis': 'RAW_UNADJUSTED', 'volume_unit': 'shares',
        'bar_timestamp_semantics': 'SESSION_DATE', 'completed_bars_only': True, 'as_of': retrieved,
        'retrieved_at': retrieved, 'bar_availability_lag_seconds': 60, 'evidence_kind': 'IMPORTED_UNVERIFIED'}
    return build_equity_snapshot(raw, manifest).document


class DailyUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.serial = 0

    def check(self, payload=None, *, prior=None, now='2026-10-23T21:00:00Z'):
        self.serial += 1
        path = self.root / f'baseline-{self.serial}.json'
        path.write_bytes(encoded(prior or baseline()))
        target = self.root / f'check-{self.serial}'
        self.fetches = []
        raw = encoded(payload if payload is not None else source_reply())
        def fetch(url):
            self.fetches.append(url)
            return raw
        result = updates.check_daily_update(path, target, now=updates._clock(now), fetcher=fetch)
        self.assertEqual(path.read_bytes(), encoded(prior or baseline()))
        return target, result

    def test_append_freeze_is_immutable_idempotent_and_no_update_has_no_candidate(self):
        target, checked = self.check()
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['new_dates'], ['2026-10-23'])
        self.assertEqual(len(self.fetches), 1)
        self.assertTrue(self.fetches[0].startswith('https://query1.finance.yahoo.com/v8/finance/chart/TEST?'))
        self.assertIn('includePrePost=false', self.fetches[0])
        workspace = self.root / 'workspace'
        frozen = updates.freeze_daily_update(target, workspace)
        retained = Path(frozen['path']).read_bytes()
        again = updates.freeze_daily_update(target, workspace)
        self.assertEqual(again, frozen)
        self.assertEqual(len(list(workspace.rglob('*.json'))), 1)
        self.assertEqual(sha256(retained).hexdigest(), checked['candidate_sha256'])
        self.assertTrue(updates.read_daily_update(target)['frozen'])
        other, unchanged = self.check(prior=json.loads(retained), now='2026-10-23T22:00:00Z')
        self.assertEqual(unchanged['status'], 'UNCHANGED')
        self.assertFalse((other / 'candidate-snapshot.json').exists())
        with self.assertRaisesRegex(ValueError, 'not_freezable'):
            updates.freeze_daily_update(other, workspace)

    def test_historical_revision_requires_explicit_acknowledgement(self):
        payload = source_reply()
        payload['chart']['result'][0]['indicators']['quote'][0]['high'][0] += 1
        target, checked = self.check(payload)
        self.assertEqual(checked['status'], 'REVISION_REVIEW_REQUIRED')
        self.assertEqual(checked['revisions'], [dict(date='2026-10-19', field='high', old_value=102.0, new_value=103)])
        workspace = self.root / 'workspace'
        with self.assertRaisesRegex(ValueError, 'require_acknowledgement'):
            updates.freeze_daily_update(target, workspace)
        self.assertFalse(workspace.exists())
        frozen = updates.freeze_daily_update(target, workspace, acknowledge_revisions=True)
        self.assertTrue(frozen['acknowledged_revisions'])
        self.assertEqual(frozen, updates.freeze_daily_update(target, workspace))

    def test_existing_eight_decimal_csv_convention_never_rounds_old_snapshot_values(self):
        def old_high(value):
            document = baseline()
            manifest = json.loads(base64.b64decode(document['raw_input']['manifest_base64']))
            lines = base64.b64decode(document['raw_input']['csv_base64']).decode().splitlines()
            row = lines[1].split(','); row[2] = value; lines[1] = ','.join(row)
            raw = ('\n'.join(lines) + '\n').encode()
            manifest['price_source']['raw_base64'] = base64.b64encode(raw).decode()
            return build_equity_snapshot(raw, manifest).document
        payload = source_reply()
        payload['chart']['result'][0]['indicators']['quote'][0]['high'][0] = 102.123456784
        target, checked = self.check(payload, prior=old_high('102.12345678'))
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['revisions'], [])
        self.assertEqual(checked['normalization_policy'], updates._NORMALIZATION)
        self.assertEqual((target / 'source-yahoo-chart.json').read_bytes(), encoded(payload))
        payload['chart']['result'][0]['indicators']['quote'][0]['high'][0] = 102.123456794
        _, revised = self.check(payload, prior=old_high('102.12345678'))
        self.assertEqual(revised['revisions'][0]['new_value'], 102.12345679)
        payload['chart']['result'][0]['indicators']['quote'][0]['high'][0] = 102.123456784
        _, high_precision = self.check(payload, prior=old_high('102.123456781'))
        self.assertEqual(high_precision['status'], 'REVISION_REVIEW_REQUIRED')
        self.assertEqual(high_precision['revisions'][0]['old_value'], 102.123456781)
        self.assertEqual(high_precision['revisions'][0]['new_value'], 102.12345678)

    def test_received_sources_and_candidates_are_verified_before_read_or_freeze(self):
        for name in ('source-yahoo-chart.json', 'candidate-snapshot.json', 'baseline-snapshot.json'):
            target, _ = self.check()
            with (target / name).open('ab') as stream:
                stream.write(b' ')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'artifact_changed'):
                updates.read_daily_update(target)
            with self.assertRaisesRegex(ValueError, 'artifact_changed'):
                updates.freeze_daily_update(target, self.root / 'workspace')

    def test_missing_latest_waits_but_missing_history_blocks_and_raw_is_retained(self):
        payload = source_reply()
        result = payload['chart']['result'][0]
        for index in (-1, 1):
            modified = deepcopy(payload)
            item = modified['chart']['result'][0]
            item['timestamp'].pop(index)
            item['indicators']['adjclose'][0]['adjclose'].pop(index)
            for values in item['indicators']['quote'][0].values():
                values.pop(index)
            target, checked = self.check(modified)
            self.assertEqual(checked['status'], 'WAITING_SOURCE_UPDATE' if index == -1 else 'BLOCKED')
            self.assertIn('SOURCE_MISSING_COMPLETED_SESSIONS', checked['reason'])
            self.assertEqual((target / 'source-yahoo-chart.json').read_bytes(), encoded(modified))
            self.assertFalse(checked['can_freeze'])

    def test_forming_bar_is_excluded_and_provider_completion_clock_is_required(self):
        payload = source_reply()
        result = payload['chart']['result'][0]
        result['meta']['regularMarketTime'] = int(updates._clock('2026-10-23T15:00:00Z').timestamp())
        for values in result['indicators']['quote'][0].values():
            values[-1] = None
        result['indicators']['adjclose'][0]['adjclose'][-1] = None
        _, checked = self.check(payload, now='2026-10-23T15:00:00Z')
        self.assertEqual(checked['status'], 'UNCHANGED')
        self.assertEqual(checked['latest_completed_session'], '2026-10-22')
        self.assertEqual(checked['excluded_forming_sessions'], ['2026-10-23'])
        payload = source_reply()
        payload['chart']['result'][0]['meta']['regularMarketTime'] -= 1
        _, checked = self.check(payload)
        self.assertEqual(checked['status'], 'WAITING_SOURCE_UPDATE')
        self.assertEqual(checked['reason'], 'SOURCE_LAST_SESSION_NOT_CONFIRMED_COMPLETE')

    def test_leading_source_context_is_bounded_and_never_enters_candidate(self):
        payload = source_reply()
        result = payload['chart']['result'][0]
        result['timestamp'].insert(0, int(updates._clock('2026-10-01T13:30:00Z').timestamp()))
        for values in result['indicators']['quote'][0].values():
            values.insert(0, None)
        result['indicators']['adjclose'][0]['adjclose'].insert(0, None)
        result['events'] = {'dividends': {'earlier': {'date': int(updates._clock('2026-10-01T13:30:00Z').timestamp()), 'amount': 1}}}
        target, checked = self.check(payload)
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['query_start'], '2026-06-21')
        self.assertEqual(checked['coverage_start'], '2026-10-19')
        self.assertEqual(checked['excluded_pre_window_sessions'], ['2026-10-01'])
        candidate = json.loads((target / 'candidate-snapshot.json').read_bytes())
        self.assertEqual(candidate['sessions'][0]['date'], '2026-10-19')
        result['timestamp'][0] = int(updates._clock('2026-06-19T13:30:00Z').timestamp())
        _, blocked = self.check(payload)
        self.assertEqual(blocked['reason'], 'SOURCE_ROW_OUTSIDE_REQUEST_OR_FUTURE')

    def test_duplicates_null_prices_adjustments_and_actions_are_not_repaired(self):
        cases = []
        reply = source_reply(); reply['chart']['result'][0]['timestamp'][1] = reply['chart']['result'][0]['timestamp'][0]
        cases.append((reply, 'SOURCE_TIMESTAMP_DUPLICATE_OR_OUT_OF_ORDER'))
        reply = source_reply(); reply['chart']['result'][0]['indicators']['quote'][0]['open'][0] = None
        cases.append((reply, 'SOURCE_MISSING_OR_INVALID_OHLCV'))
        reply = source_reply(); reply['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][0] -= 1
        cases.append((reply, 'SOURCE_ADJUSTED_RAW_MISMATCH'))
        reply = source_reply(); reply['chart']['result'][0].pop('events')
        cases.append((reply, 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN'))
        reply = source_reply(); reply['chart']['result'][0]['events'] = {'dividends': {'one': {'date': reply['chart']['result'][0]['timestamp'][0], 'amount': .1}}}
        cases.append((reply, 'CORPORATE_ACTION_IN_WINDOW:dividends:2026-10-19'))
        reply = source_reply(); reply['chart']['result'][0]['meta']['symbol'] = 'OTHER'
        cases.append((reply, 'SOURCE_SECURITY_IDENTITY_MISMATCH'))
        for reply, reason in cases:
            with self.subTest(reason=reason):
                _, checked = self.check(reply)
                self.assertEqual(checked['status'], 'BLOCKED')
                self.assertEqual(checked['reason'], reason)
                self.assertFalse(checked['can_freeze'])

    def test_published_holidays_early_close_and_both_dst_offsets(self):
        cal, _ = updates._calendar()
        self.assertEqual(updates._last_complete(cal, updates._clock('2026-11-26T22:00:00Z')), '2026-11-25')
        self.assertEqual(updates._last_complete(cal, updates._clock('2026-11-28T22:00:00Z')), '2026-11-27')
        self.assertEqual(updates._last_complete(cal, updates._clock('2026-11-27T18:00:59Z')), '2026-11-25')
        self.assertEqual(updates._last_complete(cal, updates._clock('2026-11-27T18:01:00Z')), '2026-11-27')
        for day, expected in [('2026-03-06', '2026-03-06T14:30:00Z'), ('2026-03-09', '2026-03-09T13:30:00Z'),
                              ('2026-10-30', '2026-10-30T13:30:00Z'), ('2026-11-02', '2026-11-02T14:30:00Z')]:
            self.assertEqual(calendar_rows(day, day)[0]['open_utc'], expected)
        prior = baseline('2026-11-23', '2026-11-25')
        _, checked = self.check(source_reply('2026-11-23', '2026-11-27'), prior=prior, now='2026-11-27T18:01:00Z')
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['new_dates'], ['2026-11-27'])

    def test_unsupported_year_and_failed_source_do_not_retry(self):
        target, checked = self.check(now='2027-01-05T22:00:00Z')
        self.assertEqual(checked['status'], 'CALENDAR_UNAVAILABLE')
        self.assertEqual(checked['reason'], 'EXCHANGE_CALENDAR_NOT_PUBLISHED:XNAS:2027')
        self.assertEqual(checked['stop_detail']['details']['exchange'], 'XNAS')
        self.assertEqual(self.fetches, [])
        self.assertFalse((target / 'source-yahoo-chart.json').exists())
        path = self.root / 'baseline-for-failure.json'; path.write_bytes(encoded(baseline()))
        with patch.object(updates, '_fetch', side_effect=TimeoutError('test timeout')) as fetch:
            checked = updates.check_daily_update(path, self.root / 'failed', now=updates._clock('2026-10-23T21:00:00Z'))
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(checked['status'], 'BLOCKED')
        self.assertFalse(checked['can_freeze'])
        with patch.object(updates, '_fetch', side_effect=updates._Stop('SOURCE_HTTP_429', received_raw=b'Rate limited')):
            target = self.root / 'http-failed'
            checked = updates.check_daily_update(path, target, now=updates._clock('2026-10-23T21:00:00Z'))
        self.assertEqual(checked['reason'], 'SOURCE_HTTP_429')
        self.assertEqual((target / 'source-yahoo-chart.json').read_bytes(), b'Rate limited')
        self.assertFalse(checked['source_response_truncated'])

    def test_installed_calendar_inventory_preserves_2026_and_scopes_2027_to_nyse(self):
        _, raw = updates._calendar()
        self.assertEqual(sha256(raw).hexdigest(), 'c367399cdb316fecae4e63b95d0d183b4959b61237145b8e01a0f3b1a2561491')
        support = updates.calendar_support()
        self.assertEqual(support['supported_years'], [2026, 2027])
        self.assertEqual(support['exchanges'], {'XNAS': [2026], 'XNYS': [2026, 2027]})
        self.assertEqual(support['max_history_calendar_days'], 366)
        self.assertEqual(support['max_source_rows'], 370)
        cal, _ = updates._calendar(2027)
        self.assertEqual(len(cal['holidays']), 10)
        days = updates._days(cal, date(2027, 1, 1), date(2027, 12, 31))
        self.assertEqual(sum(row['kind'] == 'OPEN' for row in days), 251)
        by_day = {row['date']: row for row in days}
        self.assertEqual(by_day['2027-12-24']['kind'], 'CLOSED')
        self.assertEqual(by_day['2027-07-02']['close_utc'], '2027-07-02T20:00:00Z')
        self.assertEqual(by_day['2027-12-31']['close_utc'], '2027-12-31T21:00:00Z')
        self.assertEqual([row['date'] for row in days if row.get('early_close')], ['2027-11-26'])

    def test_2027_early_close_holidays_and_dst_use_new_york_dates(self):
        cal, _ = updates._calendar(2027)
        for day, opened, closed in [
            ('2027-03-12', '14:30:00Z', '21:00:00Z'), ('2027-03-15', '13:30:00Z', '20:00:00Z'),
            ('2027-11-05', '13:30:00Z', '20:00:00Z'), ('2027-11-08', '14:30:00Z', '21:00:00Z')]:
            row = calendar_rows(day, day)[0]
            self.assertEqual(row['open_utc'], day + 'T' + opened)
            self.assertEqual(row['close_utc'], day + 'T' + closed)
        self.assertEqual(updates._last_complete(cal, updates._clock('2027-11-26T18:00:59Z')), '2027-11-24')
        self.assertEqual(updates._last_complete(cal, updates._clock('2027-11-26T18:01:00Z')), '2027-11-26')
        prior = baseline('2027-11-22', '2027-11-24', exchange='XNYS')
        target, checked = self.check(source_reply('2027-11-22', '2027-11-26', exchange='XNYS'),
                                     prior=prior, now='2027-11-26T18:01:00Z')
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['new_dates'], ['2027-11-26'])
        self.assertEqual(checked['calendar_years'], [2027])
        self.assertEqual(checked['calendar_coverage'][0]['exchanges'], ['XNYS'])
        self.assertEqual(json.loads((target / 'candidate-snapshot.json').read_bytes())['sessions'][-1]['close_utc'],
                         '2027-11-26T18:00:00Z')

    def test_cross_year_append_retains_each_calendar_and_does_not_add_holiday_bars(self):
        prior = baseline('2026-12-28', '2026-12-31', exchange='XNYS')
        payload = source_reply('2026-12-28', '2027-01-04', exchange='XNYS')
        target, checked = self.check(payload, prior=prior, now='2027-01-04T21:01:00Z')
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['new_dates'], ['2027-01-04'])
        self.assertEqual(checked['calendar_years'], [2026, 2027])
        merged = json.loads((target / 'calendar.json').read_bytes())
        for part in merged['components']:
            original = updates._calendar(part['year'])[1]
            self.assertEqual(base64.b64decode(part['raw_base64']), original)
            self.assertEqual(part['sha256'], sha256(original).hexdigest())
        candidate = json.loads((target / 'candidate-snapshot.json').read_bytes())
        self.assertEqual([r['date'] for r in candidate['sessions']],
                         ['2026-12-28', '2026-12-29', '2026-12-30', '2026-12-31', '2027-01-04'])
        self.assertEqual(checked['revisions'], [])
        frozen = updates.freeze_daily_update(target, self.root / 'cross-year')
        self.assertEqual(Path(frozen['path']).read_bytes(), (target / 'candidate-snapshot.json').read_bytes())
        _, holiday = self.check(source_reply('2026-12-28', '2026-12-31', exchange='XNYS'),
                                prior=prior, now='2027-01-01T23:00:00Z')
        self.assertEqual(holiday['status'], 'UNCHANGED')
        self.assertEqual(holiday['latest_completed_session'], '2026-12-31')

    def test_request_crossing_new_york_year_boundary_freezes_actual_calendar_once(self):
        moments = iter(['2027-01-01T04:59:59+00:00', '2027-01-01T05:00:01+00:00'])
        class BoundaryClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls.fromisoformat(next(moments)).astimezone(tz)
        prior = baseline('2026-12-28', '2026-12-30', exchange='XNYS')
        path = self.root / 'midnight-baseline.json'; path.write_bytes(encoded(prior))
        payload = encoded(source_reply('2026-12-28', '2026-12-31', exchange='XNYS'))
        with patch.object(updates, 'datetime', BoundaryClock):
            checked = updates.check_daily_update(path, self.root / 'midnight', fetcher=lambda url: payload)
        self.assertEqual(checked['status'], 'READY')
        self.assertEqual(checked['new_dates'], ['2026-12-31'])
        self.assertEqual(checked['calendar_years'], [2026, 2027])
        self.assertEqual(checked['retrieved_at'], '2027-01-01T05:00:01Z')

    def test_unsupported_calendar_future_availability_and_window_limit_stop_before_fetch(self):
        prior = baseline(exchange='XNYS')
        _, unavailable = self.check(prior=prior, now='2028-01-04T22:00:00Z')
        self.assertEqual(unavailable['reason'], 'PUBLISHED_CALENDAR_YEAR_UNAVAILABLE:2028')
        self.assertEqual(self.fetches, [])
        cal, raw = updates._calendar()
        future = deepcopy(cal); future['recorded_at'] = '2026-10-24T00:00:00Z'
        with patch.object(updates, '_calendar_window', return_value=(future, encoded(future))):
            _, unavailable = self.check()
        self.assertEqual(unavailable['reason'], 'CALENDAR_NOT_YET_RECORDED')
        self.assertEqual(self.fetches, [])
        prior = baseline('2026-01-02', '2026-01-05', exchange='XNYS')
        _, too_long = self.check(prior=prior, now='2027-01-04T22:00:00Z')
        self.assertEqual(too_long['reason'], 'HISTORY_WINDOW_LIMIT_EXCEEDED')
        self.assertEqual(too_long['stop_detail']['details']['maximum'], 366)
        self.assertEqual(self.fetches, [])

    def test_corporate_action_details_are_explicit_and_never_create_a_candidate(self):
        for kind in ('dividends', 'splits', 'capitalGains'):
            reply = source_reply()
            row = reply['chart']['result'][0]
            row['events'] = {kind: {'test': {'date': row['timestamp'][0], 'amount': .1}}}
            # A known event explains the stop even if adjusted prices also differ.
            row['indicators']['adjclose'][0]['adjclose'][0] -= 1
            target, checked = self.check(reply)
            self.assertEqual(checked['status'], 'BLOCKED')
            self.assertFalse(checked['can_freeze'])
            self.assertEqual(checked['stop_detail']['details']['kind'], kind)
            self.assertEqual(checked['stop_detail']['details']['date'], '2026-10-19')
            self.assertFalse((target / 'candidate-snapshot.json').exists())
            self.assertEqual((target / 'source-yahoo-chart.json').read_bytes(), encoded(reply))
        reply = source_reply(); reply['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][0] -= 1
        _, checked = self.check(reply)
        self.assertEqual(checked['stop_detail']['details'], dict(date='2026-10-19', raw_close=101, adjusted_close=100))
        reply = source_reply(); reply['chart']['result'][0].pop('events')
        _, checked = self.check(reply)
        self.assertEqual(checked['stop_detail']['code'], 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')

    def test_original_v1_check_without_new_explanation_fields_remains_readable(self):
        target, _ = self.check()
        checked = json.loads((target / 'check.json').read_bytes())
        for name in ('calendar_years', 'calendar_coverage', 'stop_detail', 'check_hash'):
            checked.pop(name)
        checked['check_hash'] = updates.digest(checked)
        (target / 'check.json').write_bytes(encoded(checked))
        self.assertEqual(updates.read_daily_update(target)['status'], 'READY')


if __name__ == '__main__':
    unittest.main()
