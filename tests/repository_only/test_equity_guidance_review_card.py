"""Retained public evidence only; no private originals, broker or new research."""
from pathlib import Path
from hashlib import sha256
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.equity_content_protocol import digest
from tools.equity_research_card import render


class GuidanceReviewCardTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'docs/research-evidence/equity-guidance-20260927'
        load=lambda p:json.loads(p.read_bytes())
        self.paths=load(folder/'report/path-results.json')
        self.pairs=load(folder/'report/guidance-pairs.json')
        self.review=load(folder/'audit-repair/bounded-review.json')
        receipt=load(folder/'report/render-receipt.json')
        self.preview=dict(version='0.3.0.dev1',build_id=receipt['preview_build_id'])
        self.old_html=(folder/'report/index.html').read_bytes()

    def seal(self):
        self.review['review_hash']=digest({k:v for k,v in self.review.items() if k!='review_hash'})

    def render(self):return render(self.paths,self.preview,self.pairs,self.review)

    def test_real_evidence_displays_one_candidate_without_granting_human_approval(self):
        html=self.render()
        self.assertEqual(html.count('class="guidance-pair"'),10)
        self.assertIn('1 个数值候选：2024Q2',html)
        self.assertIn('新增人工核准为 0',html)
        self.assertIn('口径也可比的有 6 个',html)
        self.assertIn('新内容干预：未运行',html)
        self.assertIn('本批开发诊断结案',html)
        for tag in ('<script','<form','<input','<iframe'):self.assertNotIn(tag,html)

    def test_without_review_sidecar_previous_report_remains_byte_identical(self):
        self.assertEqual(render(self.paths,self.preview,self.pairs).encode(),self.old_html)
        self.assertEqual(sha256(render(self.paths,self.preview).encode()).hexdigest(),
                         '599811b2c0e575dd5e20978d1959b060a34cbcd00a5f38d91d53aec67653668b')

    def test_unsealed_review_change_is_rejected(self):
        self.review['funnel']['admitted_for_new_study']=1
        with self.assertRaisesRegex(ValueError,'review_hash'):self.render()

    def test_review_cannot_be_rebound_to_other_pairing(self):
        self.review['pairing_hash']='other';self.seal()
        with self.assertRaisesRegex(ValueError,'input_identity'):self.render()

    def test_known_preliminary_omission_stops_display_of_reviewed_event(self):
        self.review['events'][2]['known_material_source_ids'].remove('2022Q3-preliminary');self.seal()
        with self.assertRaisesRegex(ValueError,'material_disclosure'):self.render()

    def test_price_signal_cannot_be_changed_to_create_more_candidates(self):
        self.review['events'][1]['old_price_condition']=True;self.seal()
        with self.assertRaisesRegex(ValueError,'price_binding'):self.render()

    def test_development_review_cannot_be_relabelled_human_approval(self):
        self.review['review_items'][0]['human_approval_status']='APPROVED';self.seal()
        with self.assertRaisesRegex(ValueError,'item_status'):self.render()

    def test_unknown_intervention_cannot_be_changed_to_zero(self):
        self.review['funnel']['new_content_interventions']=0;self.seal()
        with self.assertRaisesRegex(ValueError,'funnel'):self.render()

    def test_field_evidence_cannot_point_to_a_different_source_identity(self):
        self.review['review_items'][0]['evidence'][0]['source_sha256']='other';self.seal()
        with self.assertRaisesRegex(ValueError,'field_source'):self.render()


if __name__=='__main__':unittest.main()
