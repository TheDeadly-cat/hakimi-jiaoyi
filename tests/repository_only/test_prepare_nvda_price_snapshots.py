"""Canonical offline snapshot checks with fictional prices and sources."""
from datetime import date,timedelta
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
from tools.prepare_nvda_price_snapshots import build
from test_collect_nvda_event_inputs import bars


class NvdaSnapshotTests(unittest.TestCase):
    def setUp(self):
        days=[];d=date(2023,5,22)
        while d<=date(2023,6,1):
            row={'date':d.isoformat(),'kind':'OPEN' if d.weekday()<5 and d.isoformat()!='2023-05-29' else 'CLOSED'}
            if row['kind']=='OPEN':row.update(open_utc=d.isoformat()+'T13:30:00Z',close_utc=d.isoformat()+'T20:00:00Z')
            days.append(row);d+=timedelta(days=1)
        self.inputs={'calendars':{'2024Q1':{'days':days,'sessions':[d for d in days if d['kind']=='OPEN']}},
            'plan':{'calendar':{'source':'urn:fictional-calendar','retrieved_at':'2026-09-20T00:00:00Z'}}}
        self.daily=bars(self.inputs['calendars']['2024Q1']['sessions'],'K_DAY')
        self.hours=bars(self.inputs['calendars']['2024Q1']['sessions'],'K_60M')
    def run_build(self,at='2026-09-30T00:00:00Z'):
        return build('2024Q1',self.inputs,self.daily,self.hours,b'fictional identity',b'fictional actions',b'fictional calendar',at,synthetic=True)
    def test_rth_volume_stays_separate_from_larger_daily_volume(self):
        for r in self.daily:r['volume']=800
        snap,comparison=self.run_build()
        self.assertEqual(len(snap.document['candles']),8)
        self.assertTrue(all(r[-1]==700 for r in snap.document['candles']))
        self.assertEqual(comparison['daily_RTH_volume_difference_sessions'],8)
        self.assertEqual(snap.document['evidence_kind'],'SYNTHETIC_TEST')
        self.assertFalse(snap.document['order_allowed'])
    def test_price_mismatch_is_rejected_before_snapshot(self):
        self.daily[0]['close']=11
        with self.assertRaisesRegex(RuntimeError,'DAILY_RTH_PRICE_MISMATCH'):self.run_build()
    def test_missing_hour_cannot_be_aggregated_as_a_full_session(self):
        self.hours.pop()
        with self.assertRaisesRegex(RuntimeError,'RTH_CLOCK_COVERAGE_MISMATCH'):self.run_build()
    def test_calendar_future_bar_is_not_marked_completed(self):
        self.inputs['plan']['calendar']['retrieved_at']='2023-05-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'not_complete_and_available'):self.run_build('2023-05-31T00:00:00Z')


if __name__=='__main__':unittest.main()
