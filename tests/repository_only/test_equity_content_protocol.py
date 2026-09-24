from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from equity_content_protocol import content_condition, price_confirmation, digest, validate_approval
from prepare_announcement_review import extract


def inputs():
    sessions=[{'date':f'2024-05-0{day}','open_utc':f'2024-05-0{day}T13:30:00Z','close_utc':f'2024-05-0{day}T20:00:00Z'} for day in (1,2,3)]
    bars=[{'session':f'2024-05-0{day}','close':str(value),'available_at':f'2024-05-0{day}T20:01:00Z','completed':True} for day,value in ((1,100),(2,101),(3,110))]
    return dict(release_at='2024-05-01T20:15:00Z',decision_at='2024-05-02T20:01:00Z',sessions=sessions,bars=bars)


def version(actual='5.5',guidance='5.7',**changes):
    facts=[{'name':'actual_revenue','status':'UNCERTAIN','value':actual,'scale':'1000000000','currency':'USD','unit':'CURRENCY','fiscal_period':'2024Q1','basis':'GAAP','reason':'PENDING_HUMAN_SEMANTIC_REVIEW'},
           {'name':'next_revenue_guidance_midpoint','status':'UNCERTAIN','value':guidance,'scale':'1000000000','currency':'USD','unit':'CURRENCY','fiscal_period':'2024Q2','basis':'REVENUE_OUTLOOK','reason':'PENDING_HUMAN_SEMANTIC_REVIEW'}]
    row={'event_id':'SYNTHETIC:2024Q1','fiscal_quarter':'2024Q1','first_public_at':'2024-05-01T20:15:00Z','version':1,'facts':facts,**changes}
    row['candidate_hash']=digest(row);return row


class ContentProtocolTests(unittest.TestCase):
    def test_only_first_complete_post_release_close_can_confirm(self):
        data=inputs();c=price_confirmation(**data)
        self.assertEqual(c['action'],'BUY');self.assertEqual(c['execution_at'],'2024-05-03T13:30:00Z')
        data['decision_at']='2024-05-02T19:59:00Z'
        self.assertEqual(price_confirmation(**data)['action'],'HOLD')
    def test_negative_first_bar_does_not_search_a_later_winner(self):
        data=inputs();data['bars'][1]['close']='99';data['decision_at']='2024-05-03T20:01:00Z'
        self.assertEqual(price_confirmation(**data)['action'],'HOLD')
    def test_disabled_D_is_exactly_C_even_with_unknown_facts(self):
        c=price_confirmation(**inputs())
        self.assertEqual(content_condition(c,versions=[],decision_at=inputs()['decision_at'],approved_hashes=set(),enabled=False),c)
    def test_unapproved_content_never_creates_direction(self):
        c=price_confirmation(**inputs());v=version()
        self.assertEqual(content_condition(c,versions=[v],decision_at=inputs()['decision_at'],approved_hashes=set())['action'],'HOLD')
    def test_reviewed_condition_preserves_C_entry_and_risk_permission(self):
        c=price_confirmation(**inputs());v=version()
        self.assertEqual(content_condition(c,versions=[v],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash']}),c)
        self.assertFalse(c['order_allowed'])
    def test_future_announcement_or_revision_does_not_change_past(self):
        c=price_confirmation(**inputs());v=version();future=version(guidance='1',version=2,version_public_at='2024-06-01T20:15:00Z')
        a=content_condition(c,versions=[v],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash']})
        b=content_condition(c,versions=[v,future],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash'],future['candidate_hash']})
        self.assertEqual(a,b)
    def test_latest_unapproved_revision_does_not_fall_back_to_old_good_fact(self):
        c=price_confirmation(**inputs());v=version();later=version(guidance='1',version=2,version_public_at='2024-05-02T15:00:00Z')
        result=content_condition(c,versions=[v,later],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash']})
        self.assertEqual(result['action'],'HOLD')
    def test_currency_period_and_basis_mismatch_cannot_trigger(self):
        c=price_confirmation(**inputs())
        for key,value in [('currency','CNY'),('fiscal_period','2024Q3'),('basis','NON_GAAP')]:
            v=version();v['facts'][1][key]=value;v['candidate_hash']=digest({k:x for k,x in v.items() if k!='candidate_hash'})
            self.assertEqual(content_condition(c,versions=[v],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash']})['action'],'HOLD')
    def test_tampering_breaks_review_binding(self):
        c=price_confirmation(**inputs());v=version();v['facts'][0]['value']='1'
        with self.assertRaisesRegex(ValueError,'identity'):content_condition(c,versions=[v],decision_at=inputs()['decision_at'],approved_hashes={v['candidate_hash']})
    def test_incomplete_or_early_available_bar_is_rejected(self):
        data=inputs();data['bars'][1]['completed']=False
        self.assertEqual(price_confirmation(**data)['action'],'HOLD')
        data['bars'][1]['available_at']='2024-05-02T19:00:00Z'
        with self.assertRaises(ValueError):price_confirmation(**data)
    def test_semantic_loss_sign_and_guidance_quarter_remain_separate(self):
        raw='<time datetime="2023-05-02T16:15:00" class="date">May 02, 2023 4:15 pm EDT</time><p>AMD today announced revenue for the first quarter of 2023 of $5.4 billion, diluted loss per share of $0.09. On a non-GAAP basis diluted earnings per share of $0.60.</p><p>For the second quarter of 2023, AMD expects revenue to be approximately $5.3 billion, plus or minus $300 million.</p>'
        row,_=extract(raw,'2023Q1');facts={f['name']:f for f in row['facts']}
        self.assertEqual(facts['diluted_eps']['value'],'-0.09');self.assertEqual(facts['non_gaap_diluted_eps']['value'],'0.60')
        self.assertEqual(facts['next_revenue_guidance_midpoint']['fiscal_period'],'2023Q2')
        self.assertEqual(row['human_review']['status'],'PENDING')
    def test_packet_requires_separate_specific_human_receipt(self):
        packet={'events':[version()]};packet['packet_hash']=digest(packet)
        self.assertEqual(validate_approval(packet,None),set())
        with self.assertRaises(ValueError):validate_approval(packet,{'decision':'APPROVED_LISTED_FIELDS'})


if __name__=='__main__':unittest.main()
