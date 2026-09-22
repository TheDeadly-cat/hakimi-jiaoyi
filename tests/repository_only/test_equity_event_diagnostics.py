"""Bounded fictional tests; no market, account, web or model access."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from test_equity_research import stock_snapshot, spec_document
from test_equity_schedule_filter import schedule, schedule_metadata, context
from hakimi_research.documents import canonical_bytes
from hakimi_research.equity_events import build_equity_event
from hakimi_research.equity_research import EquityExperimentSpec
from hakimi_research.equity_schedule_comparison import run_schedule_comparison

module_spec = importlib.util.spec_from_file_location('equity_event_diagnostics', ROOT / 'tools/equity_event_diagnostics.py')
diagnostics = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(diagnostics)


def pair(events):
    snapshot = stock_snapshot()
    spec = EquityExperimentSpec.from_document(spec_document(snapshot, 'buy_and_hold', fee=.0008, slip=.0005))
    a, b, _ = run_schedule_comparison(snapshot, spec, context(events))
    return a.document, b.document


def expected(day='2024-11-04'):
    return [{'event_id': 'SYNTHETIC:SCHEDULE:Q3', 'scheduled_date': day,
             'actual_release_at': None, 'actual_release_source': None}]


class EventDiagnosticsTests(unittest.TestCase):
    def test_count_original_buy_opportunity_block_and_keep_no_trade(self):
        a, b = pair([schedule()])
        result = diagnostics.diagnose_pair(a, b, expected())
        self.assertEqual(result['original_A_buy_intents'], 1)
        self.assertEqual(result['original_B_path_buy_intents'], 1)
        self.assertEqual(result['B_intervenable_buy_intents_with_known_schedule'], 1)
        self.assertEqual(result['actual_blocked_B_buy_intents'], 1)
        self.assertEqual(result['B_metrics']['outcome'], 'NO_TRADE')

    def test_missing_event_remains_in_coverage_denominator(self):
        a, b = pair([schedule()])
        missing = {'event_id': 'SYNTHETIC:MISSING', 'scheduled_date': '2024-11-05'}
        result = diagnostics.diagnose_pair(a, b, [*expected(), missing])
        self.assertEqual(result['expected_event_count'], 2)
        self.assertEqual(result['event_schedule_coverage_ratio'], .5)
        self.assertEqual(result['events'][1]['coverage_status'], 'NO_MATCHING_USABLE_SCHEDULE')

    def test_lag_miss_does_not_become_a_historical_block(self):
        raw, metadata = schedule_metadata(public='2024-11-04T14:29:59Z')
        metadata['timing']['collection_delay_seconds'] = 60
        metadata['timing']['processing_delay_seconds'] = 60
        a, b = pair([build_equity_event(raw, metadata)])
        result = diagnostics.diagnose_pair(a, b, expected())
        self.assertEqual(result['event_schedule_coverage_ratio'], 0)
        self.assertEqual(result['actual_blocked_B_buy_intents'], 0)
        self.assertEqual(result['B_event_date_buy_intents_unavailable_due_to_declared_lag'], 1)
        # B retains policy audit metadata even when economics are unchanged.
        for key in ['fills', 'equity_curve', 'total_return', 'total_fees']:
            self.assertEqual(canonical_bytes(a['result'][key]), canonical_bytes(b['result'][key]))

    def test_release_crossing_is_unknown_without_clock_and_known_outside_rth(self):
        a, b = pair([schedule('2024-11-05')])
        event = expected('2024-11-05')
        no_clock = diagnostics.diagnose_pair(a, b, event)['events'][0]
        self.assertIsNone(no_clock['A_existing_position_at_release']['position_held'])
        event[0].update(actual_release_at='2024-11-05T21:15:00Z', actual_release_source='urn:synthetic:release')
        known = diagnostics.diagnose_pair(a, b, event)['events'][0]
        self.assertTrue(known['A_existing_position_at_release']['position_held'])
        self.assertTrue(known['B_existing_position_at_release']['position_held'])
        event[0]['actual_release_at'] = '2024-11-05T15:00:00Z'
        intraday = diagnostics.diagnose_pair(a, b, event)['events'][0]
        self.assertEqual(intraday['A_existing_position_at_release']['status'], 'UNKNOWN_INTRADAY_ORDERING')

    def test_duplicate_and_outside_events_cannot_inflate_denominator(self):
        a, b = pair([schedule()])
        for events in [expected() * 2, expected('2099-01-01')]:
            with self.subTest(events=events), self.assertRaises(ValueError):
                diagnostics.diagnose_pair(a, b, events)

    def test_aligned_benchmark_keeps_dates_cash_cost_allocation_without_mutation(self):
        snapshot = stock_snapshot()
        base = spec_document(snapshot)
        base['strategy'] = {'name': 'dual_ma', 'params': {'fast_window': 5, 'slow_window': 10, 'position_pct': .25}}
        base['score_start_session'] = snapshot.document['sessions'][12]['date']
        before = canonical_bytes(base)
        aligned = diagnostics.aligned_benchmark_spec(base).document
        for key in ['score_start_session', 'score_end_session', 'initial_cash', 'fee_rate', 'slippage_pct', 'end_policy']:
            self.assertEqual(aligned[key], base[key])
        self.assertEqual(aligned['strategy']['params']['target_position_pct'], .25)
        self.assertEqual(before, canonical_bytes(base))

    def test_fixed_two_cost_cells_keep_no_crossover_and_replay_identically(self):
        snapshot = stock_snapshot()
        base = spec_document(snapshot, fee=.0008, slip=.0005)
        base['strategy'] = {'name': 'dual_ma', 'params': {'fast_window': 5, 'slow_window': 10, 'position_pct': .25}}
        base['score_start_session'] = snapshot.document['sessions'][12]['date']
        archive = context([schedule('2024-11-22')])
        first, reports = diagnostics.run_diagnostics(snapshot, base, archive, expected('2024-11-22'))
        second, _ = diagnostics.run_diagnostics(snapshot, base, archive, expected('2024-11-22'))
        self.assertEqual([cell['cost_multiplier'] for cell in first['cells']], [1, 2])
        for cell in first['cells']:
            self.assertEqual(cell['diagnostics']['A_metrics']['outcome'], 'NO_TRADE')
            self.assertEqual(cell['diagnostics']['actual_blocked_B_buy_intents'], 0)
            self.assertEqual(cell['fee_rate'], .0008 * cell['cost_multiplier'])
            self.assertEqual(cell['slippage_pct'], .0005 * cell['cost_multiplier'])
        # Reports include captured provenance timestamps, whereas economic
        # result identity is deterministic for identical inputs.
        for cost, variants in reports.items():
            self.assertEqual(set(variants), {'A', 'B', 'aligned_buy_and_hold'})
        for before, after in zip(first['cells'], second['cells']):
            self.assertEqual(before['diagnostics'], after['diagnostics'])
            self.assertEqual(before['aligned_buy_and_hold'], after['aligned_buy_and_hold'])


if __name__ == '__main__':
    unittest.main()
