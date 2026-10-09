"""Fictional witnesses and prices; no provider or network access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).parent))
from tools.nvda_event_price_diagnostic import check_clock, diagnose
from tools.prepare_nvda_price_snapshots import build
import test_prepare_nvda_price_snapshots as snapshot_fixtures


class ClockWitnessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        self.event = dict(event_id='NVDA:2024Q1:EARNINGS', fiscal_quarter='2024Q1',
                          actual=dict(public_at=None, publication_date='2023-05-24', value_million='1234', evidence=dict(source_sha256='a' * 64)))
        self.witness = dict(url='https://www.globenewswire.com/fictional-test', observed_at='2026-09-30T00:00:00Z',
                            representation='LIVE_BROWSER_RENDERED_DOM_NOT_HTTP_ORIGINAL', headings=['Fictional test heading'],
                            clocks=[dict(datetime='2023-05-24T20:20:30Z', text='May 24, 2023 16:20 ET', markup='<time>fictional</time>')],
                            visible_text='Q1 Fiscal 2024 Summary GAAP Revenue $ 1,234 Non-GAAP')
        self.row = dict(event_id=self.event['event_id'], fiscal_quarter='2024Q1', source_sha256='a' * 64,
                        source_public_at=None, global_first_publication_at=None, source_publication_date='2023-05-24',
                        channel_url=self.witness['url'], observed_at=self.witness['observed_at'], representation=self.witness['representation'],
                        expected_heading='Fictional test heading', channel_publication_at='2023-05-24T20:20:30Z',
                        displayed_minute='May 24, 2023 16:20 ET', dom_time_markup='<time>fictional</time>')
        self.write()
    def write(self):
        path = self.root / '2024Q1-wire-browser.private.json'
        path.write_text(json.dumps(self.witness), encoding='utf-8')
        self.row['witness_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}
    def test_seconds_preserved_and_original_fact_not_backfilled(self):
        before = deepcopy(self.event)
        stamp = check_clock(self.row, self.event, self.root)
        self.assertEqual(stamp.second, 30); self.assertEqual(self.event, before)
    def test_rounded_display_cannot_override_seconds(self):
        self.row['channel_publication_at'] = '2023-05-24T20:20:00Z'
        with self.assertRaisesRegex(ValueError, 'clock_dom_binding'): check_clock(self.row, self.event, self.root)
    def test_clock_minute_conflict_rejected(self):
        self.row['displayed_minute'] = self.witness['clocks'][0]['text'] = 'May 24, 2023 17:20 ET'; self.write()
        with self.assertRaisesRegex(ValueError, 'visible_minute'): check_clock(self.row, self.event, self.root)
    def test_wrong_revenue_or_changed_witness_rejected(self):
        self.witness['visible_text'] = 'Q1 Fiscal 2024 Summary GAAP Revenue $ 9,999 Non-GAAP'; self.write()
        with self.assertRaisesRegex(ValueError, 'wire_revenue_binding'): check_clock(self.row, self.event, self.root)
        (self.root / '2024Q1-wire-browser.private.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'clock_witness_changed'): check_clock(self.row, self.event, self.root)
    def test_global_first_claim_rejected(self):
        self.row['global_first_publication_at'] = self.row['channel_publication_at']
        with self.assertRaisesRegex(ValueError, 'unknown_clock'): check_clock(self.row, self.event, self.root)


class PriceAlignmentTests(unittest.TestCase):
    def setUp(self):
        fixture = snapshot_fixtures.NvdaSnapshotTests(); fixture.setUp()
        self.inputs, self.daily, self.hours = fixture.inputs, fixture.daily, fixture.hours
        self.event = dict(event_id='NVDA:2024Q1:EARNINGS', fiscal_quarter='2024Q1', status='ABOVE',
                          comparison={'positive_condition': True}, actual={'value_million': '1234'}, latest_prior={'value_million': '1000'})
    def snapshot(self, *, synthetic=False):
        return build('2024Q1', self.inputs, self.daily, self.hours, b'fictional identity', b'fictional actions', b'fictional calendar',
                     '2026-09-30T00:00:00Z', synthetic=synthetic)[0]
    def rising_day(self, day):
        for row in self.daily + self.hours:
            if row['time_key'].startswith(day): row['close'] = 11
    def test_signal_only_after_first_full_session_and_next_open(self):
        self.rising_day('2023-05-25')
        row = diagnose(self.event, '2023-05-24T20:20:30Z', self.snapshot())
        self.assertEqual(row['model_available_at'], '2023-05-24T20:22:30Z')
        self.assertEqual(row['confirmation_at'], '2023-05-25T20:01:00Z')
        self.assertEqual(row['earliest_model_entry_at'], '2023-05-26T13:30:00Z')
        self.assertTrue(row['price_condition']); self.assertFalse(row['order_allowed']); self.assertFalse(row['human_approved'])
    def test_later_rise_does_not_replace_first_full_session_failure(self):
        self.rising_day('2023-05-26')
        row = diagnose(self.event, '2023-05-24T20:20:30Z', self.snapshot())
        self.assertFalse(row['price_condition']); self.assertIsNone(row['earliest_model_entry_at'])
    def test_wrong_security_rejected(self):
        with self.assertRaisesRegex(ValueError, 'snapshot_security_mismatch'):
            diagnose(self.event, '2023-05-24T20:20:30Z', self.snapshot(synthetic=True))
    def test_clock_on_wrong_day_not_silently_used(self):
        with self.assertRaisesRegex(ValueError, 'fixed_after_close_window'):
            diagnose(self.event, '2023-05-25T21:00:00Z', self.snapshot())


if __name__ == '__main__': unittest.main()
