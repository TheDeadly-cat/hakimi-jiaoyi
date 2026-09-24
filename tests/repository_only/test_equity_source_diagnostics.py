from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from equity_source_diagnostics import inspect_window, slots


def fixture(early=False):
    session={'date':'2024-07-03','kind':'OPEN','open_utc':'2024-07-03T13:30:00Z',
             'close_utc':'2024-07-03T17:00:00Z' if early else '2024-07-03T20:00:00Z','early_close':early}
    hour=[{'time_key':label,'open':10,'high':11,'low':9,'close':10,'volume':10} for label in slots(session)]
    daily=[{'time_key':'2024-07-03 00:00:00','open':10,'high':11,'low':8.9,'close':10,'volume':100}]
    return daily,hour,{'days':[session]}


class SourceDiagnosticsTests(unittest.TestCase):
    def test_mismatch_remains_excluded_and_raw_input_is_unchanged(self):
        values=fixture();before=copy.deepcopy(values);result=inspect_window(*values)
        self.assertEqual(result['differences'][0]['daily_minus_RTH'],'-0.1')
        self.assertEqual(result['differences'][0]['decision'],'KEEP_ORIGINAL_EVENT_EXCLUDED')
        self.assertEqual(values,before)
    def test_missing_tail_is_not_reported_as_complete(self):
        daily,hour,calendar=fixture()
        with self.assertRaisesRegex(ValueError,'grid'):inspect_window(daily,hour[:-1],calendar)
    def test_early_close_four_labels_retains_final_half_hour(self):
        result=inspect_window(*fixture(True))
        self.assertEqual(result['hourly_rows'],4)
        self.assertEqual(result['differences'][0]['last_partial_bar_label'],'2024-07-03 13:00:00')
    def test_duplicate_or_reordered_bar_rejected(self):
        daily,hour,calendar=fixture()
        with self.assertRaises(ValueError):inspect_window(daily,hour+[hour[-1]],calendar)
        with self.assertRaises(ValueError):inspect_window(daily,list(reversed(hour)),calendar)


if __name__=='__main__':unittest.main()
