"""Synthetic timing, comparability and display-precision contracts."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.equity_guidance_pairs import (COHORT, interval_comparison, exact_actual,
    extract_guidance, validate_result, digest)
from tools.equity_research_card import render
# CI discovers this directory as top-level modules. Do not rely on a namespace
# package named tests: installed dependencies may provide a concrete tests package.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_equity_research_card import fixture as path_fixture


def fields(value='5500', quantum='1'):
    return dict(value_million=value,display_quantum_million=quantum,
                security_id='fixture',fiscal_quarter='2024Q1',currency='USD',unit='MILLION_USD',
                basis='REVENUE',coverage='fixture',public_at='2024-05-01T00:00:00Z',
                approval_status='ADDITIONAL_REVIEW_REQUIRED',evidence=dict(source_id='fixture',quote='numeric fixture',locator='fixture'))


def paired_fixture():
    paths, preview=path_fixture();events=[]
    for quarter in COHORT:
        a=fields();a['fiscal_quarter']=quarter
        g=fields('5300','100');g.update(fiscal_quarter=quarter,public_at='2024-01-01T00:00:00Z',kind='COMPANY_GUIDANCE',business_range_million=['5000','5600'])
        events.append(dict(fiscal_quarter=quarter,actual=a,original_guidance=g,latest_prior_disclosure=g,
            comparison=interval_comparison(a,g),economic_execution_allowed=False,information_state='NOT_FOUND_IN_BOUNDED_FINANCIAL_ARCHIVE',
            disclosure_chain=[],notes=[],source_chain_gap='fixture gap',extra_evidence=[]))
    data=dict(inputs=dict(original_path_diagnosis_hash=paths['diagnosis_hash']),events=events,
        decision=dict(economic_execution_allowed=False),
        source_catalog=[dict(source_id='fixture',url='https://ir.amd.com/fictional-test',retrieved_at='2026-01-01T00:00:00Z')],
        counts=dict(events=10,dimension_matched=10,numerically_above=10,numerically_below=0,precision_uncertain=0,not_comparable=0,missing_prior=0,early_disclosure=0,retained_price_signals=0))
    seal(data);return paths,preview,data


def seal(data):data['pairing_hash']=digest({k:v for k,v in data.items() if k!='pairing_hash'})


class GuidancePairsTests(unittest.TestCase):
    def test_guidance_business_range_is_not_rounding_error_or_new_threshold(self):
        a=fields('5550');g=fields('5400','100');g['business_range_million']=['5100','5700']
        c=interval_comparison(a,g)
        self.assertEqual(c['status'],'ABOVE');self.assertEqual(c['difference_interval_million'],['99.5','200.5'])
    def test_positive_nominal_can_be_uncertain_due_to_precision(self):
        c=interval_comparison(fields('6550'),fields('6500','100'))
        self.assertEqual(c['status'],'UNCERTAIN_PRECISION');self.assertIsNone(c['positive_condition'])
        self.assertEqual(c['difference_interval_million'],['-0.5','100.5'])
    def test_zero_touch_and_zero_gap_are_not_directional(self):
        for value in ('5450.5','5400'):
            with self.subTest(value=value):self.assertIsNone(interval_comparison(fields(value),fields('5400','100'))['positive_condition'])
    def test_clear_negative_remains_negative(self):
        self.assertFalse(interval_comparison(fields('5565'),fields('6700','100'))['positive_condition'])
    def test_all_matching_dimensions_are_required(self):
        for key in ('security_id','fiscal_quarter','currency','unit','basis','coverage'):
            with self.subTest(key=key):
                a=fields();g=fields();g[key]='different'
                c=interval_comparison(a,g);self.assertEqual(c['status'],'NOT_COMPARABLE');self.assertIsNone(c['nominal_ratio'])
    def test_missing_prior_is_missing_not_zero(self):
        c=interval_comparison(fields(),None)
        self.assertEqual(c['status'],'MISSING_PRIOR');self.assertIsNone(c['nominal_difference_million'])
    def test_invalid_numbers_rejected(self):
        for value in ('NaN','Infinity','0','-1'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):interval_comparison(fields(value),fields())
    def test_financial_table_selects_current_period_and_rejects_wrong_period(self):
        text='GAAP Quarterly Financial Results\nQ1 2024\nQ1 2023\nRevenue ($M)\n$\n5,473\n$5,353'
        source=dict(source_id='fixture',sha256='fixture',published_at='2024-05-01T00:00:00Z')
        f=exact_actual(source,text,'2024Q1');self.assertEqual(f['value_million'],'5473')
        self.assertEqual(text[f['evidence']['plain_text_start']:f['evidence']['plain_text_end']],f['evidence']['quote'])
        with self.assertRaisesRegex(ValueError,'period'):exact_actual(source,text,'2023Q1')
    def test_guidance_target_period_not_nearest_number(self):
        text='For the second quarter of 2024, AMD expects revenue to be approximately $5.7 billion, plus or minus $300 million'
        source=dict(source_id='fixture',sha256='fixture',published_at='2024-05-01T00:00:00Z')
        f=extract_guidance(source,text,'2024Q2','REUSED_APPROVED_FIELD')
        self.assertEqual(f['business_range_million'],['5400.0','6000.0'])
        self.assertEqual(f['display_quantum_million'],'100.0')
        with self.assertRaisesRegex(ValueError,'target'):extract_guidance(source,text,'2024Q1','X')
    def test_future_disclosure_rejected_even_after_rehash(self):
        _,_,data=paired_fixture();data['events'][0]['latest_prior_disclosure']['public_at']='2024-05-01T00:00:00Z';seal(data)
        with self.assertRaisesRegex(ValueError,'not_prior'):validate_result(data)
    def test_duplicate_cohort_and_false_counts_rejected(self):
        _,_,data=paired_fixture();data['events'][0]['fiscal_quarter']=COHORT[1];seal(data)
        with self.assertRaisesRegex(ValueError,'cohort'):validate_result(data)
        _,_,data=paired_fixture();data['counts']['dimension_matched']=11;seal(data)
        with self.assertRaisesRegex(ValueError,'counts'):validate_result(data)
    def test_study_gate_does_not_open_from_positive_comparisons(self):
        _,_,data=paired_fixture();validate_result(data)
        data['decision']['economic_execution_allowed']=True;seal(data)
        with self.assertRaisesRegex(ValueError,'diagnostic'):validate_result(data)
    def test_new_cards_preserve_historical_context_and_no_active_surface(self):
        paths,preview,data=paired_fixture();html=render(paths,preview,data)
        self.assertEqual(html.count('class="guidance-pair"'),10)
        self.assertIn('新内容干预：未运行',html);self.assertIn('历史 C/D 与价格路径（旧内容条件）',html)
        self.assertIn('新增字段待核准',html);self.assertIn('这不等于零收益',html)
        for tag in ('<script','<form','<input','<iframe'):self.assertNotIn(tag,html)
    def test_changed_source_text_is_escaped_and_url_checked(self):
        paths,preview,data=paired_fixture();data['events'][0]['notes']=['<script>bad()</script>'];seal(data)
        self.assertIn('&lt;script&gt;',render(paths,preview,data))
        data['source_catalog'][0]['url']='https://evil.example';seal(data)
        with self.assertRaisesRegex(ValueError,'official'):render(paths,preview,data)
    def test_old_path_identity_cannot_be_mixed(self):
        paths,preview,data=paired_fixture();data['inputs']['original_path_diagnosis_hash']='different';seal(data)
        with self.assertRaisesRegex(ValueError,'identity'):render(paths,preview,data)
    def test_missing_prior_still_keeps_ten_cards(self):
        paths,preview,data=paired_fixture();row=data['events'][0]
        row['original_guidance']=row['latest_prior_disclosure']=None
        row['comparison']=interval_comparison(row['actual'],None)
        data['counts'].update(dimension_matched=9,numerically_above=9,missing_prior=1);seal(data)
        html=render(paths,preview,data)
        self.assertEqual(html.count('class="guidance-pair"'),10);self.assertIn('前序指引缺失',html)


if __name__=='__main__':unittest.main()
