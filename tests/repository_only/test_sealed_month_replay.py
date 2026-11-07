"""Sealed historical preparation on fictional prices; no provider/network access."""
import base64
from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import daily_updates as updates
from hakimi_research.documents import digest
from hakimi_research.equity_dataset import build_equity_snapshot, load_equity_snapshot


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('sealed_month_preparer', ROOT / 'tools/prepare_sealed_month_replay.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


def encode(value):
    return (json.dumps(value, allow_nan=False) + '\n').encode()


def source_reply(calendar):
    sessions = [row for row in updates._days(calendar, date(2026, 5, 19), date(2026, 10, 22))
                if row['kind'] == 'OPEN']
    values = {key: [] for key in updates._FIELDS}
    for index, _ in enumerate(sessions):
        for key, value in zip(updates._FIELDS, [100 + index, 102 + index, 99 + index, 101 + index, 1000 + index]):
            values[key].append(value)
    epoch = lambda value: int(updates._clock(value).timestamp())
    regular = dict(start=epoch(sessions[-1]['open_utc']), end=epoch(sessions[-1]['close_utc']))
    return dict(chart=dict(error=None, result=[dict(meta=dict(symbol='TEST', currency='USD', exchangeName='NYQ',
        instrumentType='EQUITY', exchangeTimezoneName='America/New_York', regularMarketTime=regular['end'],
        currentTradingPeriod=dict(regular=regular)), timestamp=[epoch(row['open_utc']) for row in sessions],
        events={}, indicators=dict(quote=[values], adjclose=[dict(adjclose=values['close'][:])]))]))


class SealedMonthReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hakimi-sealed-month-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calendar, calendar_raw = updates._calendar(2026)
        self.calendar_path = self.root / 'calendar.json'
        self.calendar_path.write_bytes(calendar_raw)
        self.raw_path, self.baseline_path, self.check_path = (self.root / name for name in
            ('source-original.json', 'baseline.json', 'source-check.json'))
        self.retrieved = '2026-10-22T23:33:58Z'
        self.reference = 'https://query1.finance.yahoo.com/v8/finance/chart/TEST?interval=1d&events=div,splits'
        days = updates._days(self.calendar, date(2026, 9, 16), date(2026, 10, 22))
        sessions = [row for row in days if row['kind'] == 'OPEN']
        csv = ('session_date,open,high,low,close,volume\n' + ''.join(
            row['date'] + ',100,102,99,101,1000\n' for row in sessions)).encode()
        source = lambda name, raw: dict(name='SYNTHETIC ' + name, reference='urn:synthetic:' + name,
            retrieved_at=self.retrieved, raw_base64=base64.b64encode(raw).decode())
        manifest = dict(schema_version='us-equity-daily-import-v1', security=dict(security_id='SYNTHETIC:TEST',
            symbol='TEST', exchange='XNYS', currency='USD', instrument_type='COMMON_STOCK'),
            identity=dict(stable_within_coverage=True, valid_from='2026-09-16', valid_through='2026-10-22',
                selection_basis='Fictional existing identity declaration; never a real security.', source=source('identity', b'fiction')),
            calendar=dict(timezone='America/New_York', coverage_start='2026-09-16', coverage_end='2026-10-22',
                days=days, source=source('calendar', calendar_raw)),
            corporate_actions=dict(coverage_start='2026-09-16', coverage_end='2026-10-22', coverage_status='DECLARED_COMPLETE',
                actions=[], source=source('actions', b'fiction')),
            price_source=source('prices', csv), price_basis='RAW_UNADJUSTED', volume_unit='shares',
            bar_timestamp_semantics='SESSION_DATE', completed_bars_only=True, as_of=self.retrieved,
            retrieved_at=self.retrieved, bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
        self.baseline_path.write_bytes(encode(build_equity_snapshot(csv, manifest).document))
        period = updates._days(self.calendar, date(2026, 7, 16), date(2026, 8, 31))
        dates = [row['date'] for row in period if row['kind'] == 'OPEN']
        self.design = dict(schema_version=prepare.DESIGN_SCHEMA, recorded_at='2026-10-24T01:00:00Z', mode=prepare.MODE,
            score_start='2026-08-03', score_end='2026-08-31', score_sessions=[d for d in dates if d >= '2026-08-03'],
            context_start='2026-07-16', context_sessions=12, context_dates=[d for d in dates if d < '2026-08-03'],
            strategy=dict(name='dual_ma', params=dict(fast_window=5, slow_window=10, position_pct=.25,
                stop_loss_pct=.03, take_profit_pct=.06)), initial_cash=10000, fee_rate=.0008, slippage_pct=.0005,
            risk=dict(max_daily_loss_pct=1.0, max_leverage=1.0, max_position_pct=.25, max_single_loss_pct=.03, min_cash_pct=0),
            end_policy='MARK_TO_MARKET', execution_policy='STANDARD_STRATEGY_RISK',
            quantity_policy='FRACTIONAL_SHARES_RESEARCH_APPROXIMATION', purpose='DESCRIPTIVE_DEVELOPMENT',
            cost_multipliers=[1, 2, 3], benchmarks=['cash', 'buy_and_hold'], calendar_path=str(self.calendar_path),
            calendar_sha256=sha256(calendar_raw).hexdigest(), execution_runtime_source_sha256='synthetic-runtime',
            sources={'TEST': dict(raw_source_path=str(self.raw_path), baseline_snapshot_path=str(self.baseline_path),
                baseline_sha256=sha256(self.baseline_path.read_bytes()).hexdigest(), retrieved_at=self.retrieved,
                reference=self.reference, source_check_path=str(self.check_path),
                historical_identity_declaration='SYNTHETIC new importer historical declaration; continuity is not independently authenticated; '
                                                'this does not extend the old identity assertion or backdate source acquisition.')})
        self.payload = source_reply(self.calendar)
        self.plan_path = self.root / 'design.json'
        self.output = self.root / 'prepared'
        runtime = dict(source_identity=dict(content_sha256='synthetic-runtime'), environment_verified=dict(status='VERIFIED'))
        self.patch = patch.object(prepare, 'build_runtime_provenance', return_value=runtime)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.seal()

    def seal(self):
        raw = encode(self.payload)
        self.raw_path.write_bytes(raw)
        check = dict(symbol='TEST', raw_sha256=sha256(raw).hexdigest(), retrieved_at=self.retrieved,
            source_url=self.reference, query_start='2026-05-19', latest_completed_session='2026-10-22')
        self.check_path.write_bytes(encode(check))
        self.design['sources']['TEST'].update(raw_sha256=sha256(raw).hexdigest(),
            source_check_sha256=sha256(self.check_path.read_bytes()).hexdigest())
        self.write_design()

    def write_design(self):
        self.design.pop('plan_hash', None)
        self.design['plan_hash'] = digest(self.design)
        self.plan_path.write_bytes(encode(self.design))

    def run_prepare(self):
        before = {p: p.read_bytes() for p in (self.raw_path, self.baseline_path, self.check_path, self.plan_path)}
        value = prepare.prepare(self.plan_path, self.output)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        return value

    def assert_stopped(self, fragment):
        result = self.run_prepare()
        self.assertEqual(result['status'], 'STOPPED')
        self.assertIn(fragment, result['symbols']['TEST']['reason'])
        self.assertFalse((self.output / 'TEST/snapshot.json').exists())
        self.assertEqual(result['economic_runs'], 0)
        self.assertEqual(result['network_requests'], 0)
        return result

    def test_fixed_window_preserves_original_receipt_and_creates_separate_identity(self):
        result = self.run_prepare()
        self.assertEqual(result['status'], 'READY')
        row = result['symbols']['TEST']
        self.assertTrue(result['original_source_bytes_retained'])
        self.assertTrue(result['retained_complete'])
        self.assertTrue(row['retained_complete'])
        self.assertEqual(len(result['retained_files']), 3)
        self.assertTrue(all(item['matches_design'] and item['expected_sha256'] == item['retained_sha256']
                            for item in result['retained_files'].values()))
        self.assertEqual((row['selected_rows'], row['source_rows']), (33, 109))
        snapshot = load_equity_snapshot(row['snapshot_path']).document
        self.assertEqual(snapshot['retrieved_at'], self.retrieved)
        self.assertEqual(snapshot['sessions'][0]['date'], '2026-07-16')
        self.assertEqual(snapshot['sessions'][-1]['date'], '2026-08-31')
        self.assertEqual(snapshot['security_identity']['valid_from'], '2026-07-16')
        self.assertNotEqual(snapshot['security']['security_id'], 'SYNTHETIC:TEST')
        self.assertIn(self.design['recorded_at'], snapshot['security_identity']['selection_basis'])
        self.assertFalse(snapshot['research_admission']['source_truth_verified'])
        self.assertFalse(row['historical_receipt_time_proven'])
        self.assertEqual((self.output / 'TEST/source-original.json').read_bytes(), self.raw_path.read_bytes())
        self.assertNotEqual(row['derived_source_sha256'], row['source_sha256'])
        spec = json.loads((self.output / 'TEST/spec.json').read_text())
        for key in ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy'):
            self.assertEqual(spec[key], self.design[key])

    def test_changed_design_is_rejected_before_output(self):
        self.design['fee_rate'] = .001
        self.plan_path.write_bytes(encode(self.design))
        with self.assertRaisesRegex(ValueError, 'design_hash_changed'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_changed_source_is_stopped_and_not_resealed(self):
        self.raw_path.write_bytes(self.raw_path.read_bytes() + b' ')
        result = self.assert_stopped('source_hash_changed')
        self.assertFalse((self.output / 'TEST/source-original.json').exists())
        self.assertFalse(result['original_source_bytes_retained'])
        self.assertFalse(result['retained_complete'])
        self.assertFalse(result['symbols']['TEST']['retained_complete'])
        self.assertEqual(len(result['retained_files']), 3)
        self.assertTrue(all(item['retained_sha256'] is None and item['matches_design'] is False
                            for item in result['retained_files'].values()))

    def test_existing_output_is_not_retried_or_overwritten(self):
        self.run_prepare()
        before = {str(p): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'output_exists'):
            self.run_prepare()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_actions_in_warmup_or_scoring_stop_without_reselecting(self):
        self.payload['chart']['result'][0]['events'] = {'dividends': {'one': {'date': int(updates._clock('2026-07-20T13:30:00Z').timestamp()), 'amount': 1}}}
        self.seal()
        self.assert_stopped('CORPORATE_ACTION_IN_WINDOW')

    def test_adjusted_raw_disagreement_is_not_repaired(self):
        result = self.payload['chart']['result'][0]
        index = result['timestamp'].index(int(updates._clock('2026-08-03T13:30:00Z').timestamp()))
        result['indicators']['adjclose'][0]['adjclose'][index] -= 1
        self.seal()
        receipt = self.assert_stopped('SOURCE_ADJUSTED_RAW_MISMATCH')
        self.assertTrue(receipt['retained_complete'])
        self.assertTrue(receipt['original_source_bytes_retained'])

    def test_missing_event_coverage_stops(self):
        del self.payload['chart']['result'][0]['events']
        self.seal()
        self.assert_stopped('SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')

    def test_missing_fixed_session_is_not_filled_or_shrunk(self):
        result = self.payload['chart']['result'][0]
        index = result['timestamp'].index(int(updates._clock('2026-08-03T13:30:00Z').timestamp()))
        result['timestamp'].pop(index)
        for values in result['indicators']['quote'][0].values():
            values.pop(index)
        result['indicators']['adjclose'][0]['adjclose'].pop(index)
        self.seal()
        self.assert_stopped('SOURCE_MISSING_COMPLETED_SESSIONS:2026-08-03')

    def test_source_completion_clock_must_cover_fixed_last_session(self):
        self.payload['chart']['result'][0]['meta']['regularMarketTime'] = int(updates._clock('2026-08-31T19:59:59Z').timestamp())
        self.seal()
        self.assert_stopped('SOURCE_LAST_SESSION_NOT_CONFIRMED_COMPLETE')

    def test_future_tail_timestamp_cannot_be_hidden_by_window_filter(self):
        self.payload['chart']['result'][0]['timestamp'][-1] = int(updates._clock('2026-10-23T13:30:00Z').timestamp())
        self.seal()
        self.assert_stopped('SOURCE_ROW_OUTSIDE_REQUEST_OR_FUTURE')

    def test_bad_array_shape_outside_window_is_not_hidden(self):
        self.payload['chart']['result'][0]['indicators']['quote'][0]['close'].pop()
        self.seal()
        self.assert_stopped('SOURCE_ARRAY_LENGTH_MISMATCH')

    def test_changed_partition_is_rejected_despite_valid_design_hash(self):
        self.design['context_start'] = '2026-07-17'
        self.write_design()
        self.assert_stopped('calendar_partition_changed')

    def test_wrong_symbol_metadata_stops(self):
        self.payload['chart']['result'][0]['meta']['symbol'] = 'DIFFERENT'
        self.seal()
        self.assert_stopped('SOURCE_SECURITY_IDENTITY_MISMATCH')

    def test_traversal_symbol_is_rejected_before_output(self):
        self.design['sources']['../outside'] = self.design['sources'].pop('TEST')
        self.write_design()
        with self.assertRaisesRegex(ValueError, 'symbol_invalid'):
            self.run_prepare()
        self.assertFalse(self.output.exists())


class SealedMonthReplayV2Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = SealedMonthReplayTests('test_fixed_window_preserves_original_receipt_and_creates_separate_identity')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        result = self.fixture.payload['chart']['result'][0]
        for key in updates._FIELDS[:4]:
            result['indicators']['quote'][0][key] = [struct.unpack('>f', struct.pack('>f', value + .1))[0]
                for value in result['indicators']['quote'][0][key]]
        stamp = int(updates._clock('2026-09-15T13:30:00Z').timestamp())
        event_index = result['timestamp'].index(stamp)
        result['events'] = {'dividends': {str(stamp): dict(date=stamp, amount=1.0)}}
        factor = 1.0 - 1.0 / result['indicators']['quote'][0]['close'][event_index - 1]
        result['indicators']['adjclose'][0]['adjclose'] = [
            struct.unpack('>f', struct.pack('>f', close * (factor if i < event_index else 1.0)))[0]
            for i, close in enumerate(result['indicators']['quote'][0]['close'])]

    def seal_v2(self):
        f = self.fixture
        f.seal()
        old_design_path, old_output = f.plan_path, f.output
        stopped = f.run_prepare()
        self.assertEqual(stopped['symbols']['TEST']['reason'], 'SOURCE_ADJUSTED_RAW_MISMATCH')
        diagnostic_path = f.root / 'diagnostic.json'
        diagnostic_path.write_bytes(encode(dict(plan_hash=f.design['plan_hash'], economic_runs=0,
            symbols={'TEST': {'raw_sha256': f.design['sources']['TEST']['raw_sha256']}})))
        f.design.update(schema_version=prepare.AMENDED_DESIGN_SCHEMA, recorded_at=updates._stamp(datetime.now(timezone.utc)),
            historical_price_policy=deepcopy(prepare.HISTORICAL_POLICY), amends=dict(
                original_design_path=str(old_design_path), original_design_sha256=sha256(old_design_path.read_bytes()).hexdigest(),
                original_plan_hash=f.design['plan_hash'], stopped_receipt_path=str(old_output / 'preparation.json'),
                stopped_receipt_sha256=sha256((old_output / 'preparation.json').read_bytes()).hexdigest(),
                diagnostic_path=str(diagnostic_path), diagnostic_sha256=sha256(diagnostic_path.read_bytes()).hexdigest()))
        f.plan_path = f.root / 'design-v2.json'
        f.output = f.root / 'prepared-v2'
        f.write_design()

    def test_v2_reconciles_entire_history_and_keeps_original_quote_fields(self):
        self.seal_v2()
        f = self.fixture
        original = f.raw_path.read_bytes()
        result = f.run_prepare()
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['schema_version'], 'sealed-month-replay-preparation-v2')
        self.assertEqual((f.output / 'TEST/source-original.json').read_bytes(), original)
        reconciliation = json.loads((f.output / 'TEST/historical-adjustment-reconciliation.json').read_text())
        self.assertGreater(reconciliation['reconciled_rows'], 33)
        self.assertEqual(reconciliation['factor_path'][0]['date'], '2026-07-16')
        self.assertEqual(reconciliation['factor_path'][-1]['date'], '2026-10-22')
        self.assertEqual(reconciliation['factor_path'][-1]['factor'], 1.0)
        self.assertLessEqual(reconciliation['max_error_float32_ulps'], 2)
        self.assertEqual(len(reconciliation['field_to_csv_map']), 33)
        self.assertFalse(reconciliation['price_adjustment_applied'])
        self.assertEqual(reconciliation['csv_decimal_places'], 8)
        self.assertFalse(reconciliation['adjusted_close_used_for_strategy'])
        snapshot = load_equity_snapshot(f.output / 'TEST/snapshot.json').document
        raw = json.loads(original)['chart']['result'][0]
        formatting_changed_binary_value = False
        for session, candle in zip(snapshot['sessions'], snapshot['candles']):
            index = raw['timestamp'].index(int(updates._clock(session['open_utc']).timestamp()))
            original_values = [raw['indicators']['quote'][0][key][index] for key in updates._FIELDS]
            self.assertEqual(candle[1:], [float(updates._price(value)) for value in original_values[:4]] + original_values[4:])
            formatting_changed_binary_value |= candle[1:] != original_values
        self.assertTrue(formatting_changed_binary_value)
        self.assertEqual(json.loads((f.root / 'prepared/preparation.json').read_text())['status'], 'STOPPED')

    def test_v2_cannot_change_frozen_dates_or_parameters(self):
        self.seal_v2()
        f = self.fixture
        f.design['fee_rate'] = .0009
        f.write_design()
        with self.assertRaisesRegex(ValueError, 'changed_frozen_economic_or_source_fields'):
            f.run_prepare()
        self.assertFalse(f.output.exists())

    def test_v2_ulp_budget_is_exact_not_configurable(self):
        self.seal_v2()
        f = self.fixture
        f.design['historical_price_policy']['max_adjusted_close_error_float32_ulps'] = 3
        f.write_design()
        with self.assertRaisesRegex(ValueError, 'historical_policy_changed'):
            f.run_prepare()
        self.assertFalse(f.output.exists())

    def test_v2_recorded_time_must_follow_the_actual_stop_receipt(self):
        self.seal_v2()
        f = self.fixture
        f.design['recorded_at'] = '2026-10-24T01:00:01Z'
        f.write_design()
        with self.assertRaisesRegex(ValueError, 'stop_amendment_chronology_invalid'):
            f.run_prepare()
        self.assertFalse(f.output.exists())

    def test_v2_checks_source_days_after_scoring_window(self):
        result = self.fixture.payload['chart']['result'][0]
        index = result['timestamp'].index(int(updates._clock('2026-09-10T13:30:00Z').timestamp()))
        value = result['indicators']['adjclose'][0]['adjclose'][index]
        result['indicators']['adjclose'][0]['adjclose'][index] = value + prepare._float32_ulp(value) * 4
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_POST_WINDOW_ADJUSTMENT_UNEXPLAINED:2026-09-10')

    def test_v2_requires_exact_factor_one_after_last_event(self):
        result = self.fixture.payload['chart']['result'][0]
        value = result['indicators']['adjclose'][0]['adjclose'][-1]
        result['indicators']['adjclose'][0]['adjclose'][-1] += prepare._float32_ulp(value)
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_LAST_EVENT_FOLLOWING_FACTOR_NOT_ONE')

    def test_v2_rejects_post_window_split(self):
        stamp = int(updates._clock('2026-09-16T13:30:00Z').timestamp())
        self.fixture.payload['chart']['result'][0]['events']['splits'] = {str(stamp): dict(date=stamp, numerator=2, denominator=1)}
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_SPLIT_OR_CAPITAL_GAIN_THROUGH_RECEIPT')

    def test_v2_requires_full_source_continuity_through_receipt(self):
        result = self.fixture.payload['chart']['result'][0]
        index = result['timestamp'].index(int(updates._clock('2026-09-14T13:30:00Z').timestamp()))
        result['timestamp'].pop(index)
        for values in result['indicators']['quote'][0].values():
            values.pop(index)
        result['indicators']['adjclose'][0]['adjclose'].pop(index)
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_MISSING_COMPLETED_SESSIONS')

    def test_v2_rejects_unsupported_source_precision(self):
        result = self.fixture.payload['chart']['result'][0]
        index = result['timestamp'].index(int(updates._clock('2026-09-10T13:30:00Z').timestamp()))
        result['indicators']['quote'][0]['close'][index] += 1e-10
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_VALUE_NOT_EXACT_FINITE_FLOAT32')

    def test_v2_rejects_nonordinary_dividend_amount(self):
        entry = next(iter(self.fixture.payload['chart']['result'][0]['events']['dividends'].values()))
        entry['amount'] = 0
        self.seal_v2()
        self.fixture.assert_stopped('SOURCE_ORDINARY_CASH_DIVIDEND_AMOUNT_INVALID')

    def test_v2_policy_itself_rejects_unknown_event_kinds(self):
        f = self.fixture
        stamp = int(updates._clock('2026-09-16T13:30:00Z').timestamp())
        f.payload['chart']['result'][0]['events']['unknownAdjustment'] = {str(stamp): dict(date=stamp)}
        f.seal()
        with self.assertRaisesRegex(ValueError, 'SOURCE_UNKNOWN_CORPORATE_ACTION_KIND'):
            prepare._historical_rows(f.raw_path.read_bytes(), json.loads(f.baseline_path.read_text()),
                f.design, json.loads(f.check_path.read_text()), updates._clock(f.retrieved), f.calendar)

    def test_v2_policy_itself_rejects_action_inside_fixed_window(self):
        f = self.fixture
        stamp = int(updates._clock('2026-08-04T13:30:00Z').timestamp())
        f.payload['chart']['result'][0]['events']['dividends'][str(stamp)] = dict(date=stamp, amount=1)
        f.seal()
        with self.assertRaisesRegex(ValueError, 'CORPORATE_ACTION_IN_WINDOW'):
            prepare._historical_rows(f.raw_path.read_bytes(), json.loads(f.baseline_path.read_text()),
                f.design, json.loads(f.check_path.read_text()), updates._clock(f.retrieved), f.calendar)

    def test_v2_rechecks_original_stop_attachments(self):
        self.seal_v2()
        f = self.fixture
        path = f.root / 'prepared/TEST/source-original.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'source_hash_changed'):
            f.run_prepare()
        self.assertFalse(f.output.exists())


if __name__ == '__main__':
    unittest.main()
