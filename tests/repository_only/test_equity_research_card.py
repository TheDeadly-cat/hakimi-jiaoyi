"""Static report contracts; no browser, external source or research execution."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.equity_content_protocol import digest
from tools.equity_research_card import render,pct


def fixture():
    events=[]
    for i in range(10):
        events.append({'fiscal_quarter':f'{2022+i//4}Q{i%4+1}','status':'DATA_EXCLUDED' if i<3 else 'NO_PRICE_SIGNAL',
            'first_public_at':'2024-01-01T00:00:00Z','model_event_available_at':'2024-01-01T00:02:00Z',
            'candidate_hash':'fixture','cost_cases':[],'facts':[],'source_url':'https://ir.amd.com/fictional-test',
            'actual_retrieved_at':'2026-01-01T00:00:00Z','actual_extraction_completed_at':'2026-01-01T00:01:00Z',
            'price_condition':False,'confirmation_close_change':'-.1','content_condition':True,'content_changed_decision':False})
    result={'events':events,'protocol_hash':'fixture'};result['diagnosis_hash']=digest(result)
    return result,{'version':'SYNTHETIC_FIXTURE','build_id':'fixture-not-a-release'}


class ResearchCardTests(unittest.TestCase):
    def test_complete_coverage_missing_not_zero_and_readonly_contract(self):
        html=render(*fixture())
        self.assertEqual(html.count('<article '),10)
        self.assertIn('资料不足',html);self.assertIn('这不等于零收益',html)
        self.assertIn('内容条件否决：<b>0</b>',html)
        for forbidden in ('<script','<form','<input','<iframe','src="https://'):
            self.assertNotIn(forbidden,html)
        self.assertIn('Content-Security-Policy',html);self.assertIn('原包未修改',html)
        self.assertNotIn('收盘价都低于入场参考价',html)
        self.assertEqual(pct(None),'未计算');self.assertEqual(pct(0),'0%')
    def test_untrusted_text_is_escaped_and_script_urls_are_rejected(self):
        result,preview=fixture();result['events'][0]['candidate_hash']='<script>unsafe</script>'
        result['diagnosis_hash']=digest({k:v for k,v in result.items() if k!='diagnosis_hash'})
        html=render(result,preview);self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        result['events'][0]['source_url']='javascript:alert(1)'
        result['diagnosis_hash']=digest({k:v for k,v in result.items() if k!='diagnosis_hash'})
        with self.assertRaisesRegex(ValueError,'official'):render(result,preview)
    def test_changed_result_cannot_be_rendered_under_old_identity(self):
        result,preview=fixture();result['events'].pop()
        with self.assertRaisesRegex(ValueError,'identity'):render(result,preview)


if __name__=='__main__':unittest.main()
