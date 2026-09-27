"""Hand-computed paths with holidays/weekends absent; no engine or provider."""
import copy
from decimal import Decimal
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.equity_path_diagnostics import paths


def fixture():
    days=['2024-05-03','2024-05-06','2024-05-07','2024-05-08','2024-05-09']
    sessions=[{'date':d,'open_utc':d+'T13:30:00Z','close_utc':d+'T20:00:00Z'} for d in days]
    candles=[[s['open_utc'],100,high,low,close,1000] for s,(high,low,close) in zip(sessions,
        [(104,96,99),(110,95,106),(120,100,115),(110,90,101),(100,85,90)])]
    snapshot={'snapshot_id':'fixture','sessions':sessions,'candles':candles}
    buy={'action':'BUY','fill_time':sessions[0]['open_utc'],'signal_time':'2024-05-02T20:01:00Z',
         'quantity':25,'cash_after':7498,'fee':2}
    sell={'action':'SELL','fill_time':sessions[0]['open_utc'],'fee':1.94,'fill_basis':'INTRABAR_STOP'}
    report={'report_hash':'fixture-report','spec':{'initial_cash':10000,'score_start_session':days[0],'score_end_session':days[-1]},
            'result':{'fills':[buy,sell],'total_return':-.007894,'realized_pnl':-78.94,'exposure_ratio':0}}
    return snapshot,report


class PathDiagnosticTests(unittest.TestCase):
    def test_exact_trading_day_horizons_and_entry_cost_valuation(self):
        result=paths(*fixture());rows=result['horizons']
        self.assertEqual([r['close_session'] for r in rows],['2024-05-03','2024-05-07','2024-05-09'])
        self.assertEqual([Decimal(r['values']['close_price_change']) for r in rows],[Decimal('-.01'),Decimal('.15'),Decimal('-.10')])
        self.assertEqual(Decimal(rows[1]['values']['retained_entry_mark_return']),Decimal('.0373'))
        self.assertEqual(result['entry_fee'],'2');self.assertEqual(result['exit_fee'],'1.94')
    def test_same_day_high_is_not_called_a_post_stop_opportunity(self):
        result=paths(*fixture());first=result['horizons'][0]
        self.assertIsNone(first['values']['post_exit_full_session_high_change'])
        self.assertEqual(first['intrabar_extrema_order'],'UNKNOWN')
        self.assertEqual(first['post_exit_same_day_remainder'],'UNKNOWN')
        self.assertEqual(Decimal(result['horizons'][1]['values']['post_exit_full_session_low_change']),Decimal('-.05'))
        self.assertTrue(result['intraday_exposure_not_zero']);self.assertIsNone(result['holding_time_exact'])
    def test_missing_tail_and_original_score_end_are_not_shortened(self):
        snapshot,report=fixture();snapshot['sessions'].pop();snapshot['candles'].pop()
        self.assertIsNone(paths(snapshot,report)['horizons'][2]['values'])
        snapshot,report=fixture();report['spec']['score_end_session']='2024-05-06'
        self.assertEqual([r['status'] for r in paths(snapshot,report)['horizons']],
            ['OBSERVED_RETAINED_PATH','MISSING_OR_OUTSIDE_ORIGINAL_SCORE','MISSING_OR_OUTSIDE_ORIGINAL_SCORE'])
    def test_no_entry_stays_missing_not_a_zero_return_trade(self):
        snapshot,report=fixture();report['result']['fills']=[]
        self.assertTrue(all(r['values'] is None and r['status']=='NO_ENTRY' for r in paths(snapshot,report)['horizons']))
    def test_later_extrema_do_not_change_earlier_horizon(self):
        snapshot,report=fixture();before=paths(snapshot,report)['horizons'][0]
        snapshot['candles'][-1][2]=10000;snapshot['candles'][-1][3]=1
        self.assertEqual(before,paths(snapshot,report)['horizons'][0])
    def test_invalid_entry_or_duplicate_intent_is_rejected(self):
        snapshot,report=fixture();report['result']['fills'][0]['signal_time']=report['result']['fills'][0]['fill_time']
        with self.assertRaises(ValueError):paths(snapshot,report)
        snapshot,report=fixture();report['result']['fills'].append(copy.deepcopy(report['result']['fills'][0]))
        with self.assertRaises(ValueError):paths(snapshot,report)


if __name__=='__main__':unittest.main()
