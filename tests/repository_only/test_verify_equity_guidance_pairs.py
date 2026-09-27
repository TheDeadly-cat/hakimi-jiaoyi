"""Independent-auditor regressions with fictional, complete-schema disclosures.

Economic values follow the reviewer's probes. Required source catalog, period,
clock and event identity are supplied explicitly; no real sources are fetched.
"""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.verify_equity_guidance_pairs import verify

QUARTERS=[f'{y}Q{q}' for y in (2022,2023,2024) for q in range(1,5) if y<2024 or q<3]
WORDS={1:'first',2:'second',3:'third',4:'fourth'}


def seal(data):
    data['pairing_hash']=hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='pairing_hash'},
        sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def compare(a,g):
    if a['coverage']!=g['coverage']:
        return dict(status='NOT_COMPARABLE',mismatched_dimensions=['coverage'],nominal_difference_million=None,
            difference_interval_million=None,nominal_ratio=None,positive_condition=None)
    av,gv=Decimal(a['value_million']),Decimal(g['value_million']);delta=av-gv
    radius=(Decimal(a['display_quantum_million'])+Decimal(g['display_quantum_million']))/2
    lo,hi=delta-radius,delta+radius
    state='ABOVE' if lo>0 else 'BELOW' if hi<0 else 'UNCERTAIN_PRECISION'
    return dict(status=state,mismatched_dimensions=[],nominal_difference_million=str(delta),
        difference_interval_million=[str(lo),str(hi)],nominal_ratio=str(delta/gv),
        positive_condition=True if state=='ABOVE' else False if state=='BELOW' else None)


def fixture(root):
    catalog=[];index=[];events=[]
    def source(id,body,public_day):
        summer=4<=public_day.month<=10
        hour=16 if summer else 15;zone='EDT' if summer else 'EST'
        html=f'<html><body><time datetime="{public_day.isoformat()}T{hour}:00:00" class="date">{zone}</time>{body}</body></html>'
        raw=html.encode();path=root/(id+'.html');path.write_bytes(raw)
        source=dict(source_id=id,sha256=hashlib.sha256(raw).hexdigest(),url='https://ir.amd.com/fictional-test/'+id,
            retrieved_at='2026-01-01T00:00:00Z',published_at=public_day.isoformat()+'T20:00:00Z')
        catalog.append(source);index.append(dict(source,status=200,path=str(path)))
        return source
    for q in QUARTERS:
        year,n=int(q[:4]),int(q[-1]);release=date(year,n*3,25)+timedelta(days=35);before=release-timedelta(days=80)
        body=f'<p>GAAP Quarterly Financial Results</p><table><tr><th></th><th>Q{n} {year}</th><th>Q{n} {year-1}</th></tr>'
        body+='<tr><td>Revenue ($M)</td><td>$6,000</td><td>$4,500</td></tr></table>'
        if q=='2022Q1':body+='<p>First quarter results include partial quarter financial results from Xilinx.</p>'
        actual=source(q+'-actual',body,release)
        gquote='approximately $5.5 billion, plus or minus $300 million'
        body=f'<p>For the {WORDS[n]} quarter of {year}, AMD expects revenue to be {gquote}.</p>'
        if q=='2022Q1':body+='<p>Guidance does not contemplate the addition of Xilinx.</p>'
        guide=source(q+'-guidance',body,before)
        def field(src,value,quantum,quote):
            return dict(value_million=value,display_quantum_million=quantum,security_id='US:COMMON:CUSIP:007903107',
                fiscal_quarter=q,currency='USD',unit='MILLION_USD',basis='REVENUE',coverage='AMD_CONSOLIDATED_REPORTED',
                public_at=src['published_at'],approval_status='ADDITIONAL_REVIEW_REQUIRED',
                evidence=dict(source_id=src['source_id'],source_sha256=src['sha256'],quote=quote,locator='FICTIONAL_TEST'))
        a=field(actual,'6000','1','Revenue ($M) $6,000')
        g=field(guide,'5500','100',gquote)
        g.update(kind='COMPANY_GUIDANCE',business_half_range_million='300',business_range_million=['5200','5800'])
        extra=[]
        if q=='2022Q1':
            g['coverage']='AMD_EXCLUDING_XILINX'
            extra=[dict(source_id=guide['source_id'],source_sha256=guide['sha256'],quote='Guidance does not contemplate the addition of Xilinx'),
                   dict(source_id=actual['source_id'],source_sha256=actual['sha256'],quote='results include partial quarter financial results from')]
        latest=deepcopy(g);chain=[dict(source_id=guide['source_id'],kind='COMPANY_GUIDANCE',public_at=g['public_at'])]
        if q=='2022Q3':
            pquote='Third quarter revenue is expected to be approximately $5.8 billion'
            preliminary=source(q+'-preliminary',f'<p>AMD today announced selected preliminary financial results for the third quarter of 2022.</p><p>{pquote}.</p>',release-timedelta(days=25))
            latest=field(preliminary,'5800','100',pquote)
            latest.update(kind='PRELIMINARY_RESULTS',business_half_range_million=None,business_range_million=None)
            chain.append(dict(source_id=preliminary['source_id'],kind='PRELIMINARY_RESULTS',public_at=latest['public_at']))
        chain.append(dict(source_id=actual['source_id'],kind='FORMAL_RESULTS',public_at=a['public_at']))
        excluded=q in ('2022Q2','2022Q4','2023Q3');signal=q in ('2022Q1','2024Q2')
        events.append(dict(event_id='AMD:'+q+':EARNINGS',fiscal_quarter=q,actual=a,original_guidance=g,
            latest_prior_disclosure=latest,comparison=compare(a,latest),comparison_to_original_guidance=compare(a,g),
            disclosure_chain=chain,extra_evidence=extra,economic_execution_allowed=False,complete_historical_chain_proven=False,
            old_price_status='DATA_EXCLUDED' if excluded else 'ENTERED_STOPPED' if signal else 'NO_PRICE_SIGNAL',
            old_price_condition=None if excluded else signal))
    data=dict(schema_version='same-quarter-guidance-pairs-v1',source_catalog=catalog,events=events,
        counts=dict(events=10,dimension_matched=9,numerically_above=9,numerically_below=0,precision_uncertain=0,
            not_comparable=1,missing_prior=0,early_disclosure=1,retained_price_accepted=7,retained_price_signals=2,
            new_backtest_reports=0,new_independent_events=0,new_content_interventions=None,additional_human_approved_fields=0),
        decision=dict(economic_execution_allowed=False),source_scope=dict(complete_historical_chain_proven=False))
    seal(data);return data,{'sources':index}


class IndependentGuidanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hakimi-guidance-audit-')
        self.root=Path(self.temp.name);self.data,self.index=fixture(self.root)
    def tearDown(self):self.temp.cleanup()
    def audit(self,reseal=True):
        if reseal:seal(self.data)
        p=self.root/'result.json';i=self.root/'index.json'
        p.write_text(json.dumps(self.data),encoding='utf-8');i.write_text(json.dumps(self.index),encoding='utf-8')
        return verify(p,i)
    def recalculate(self,n):
        e=self.data['events'][n];e['comparison']=compare(e['actual'],e['latest_prior_disclosure'])
        e['comparison_to_original_guidance']=compare(e['actual'],e['original_guidance'])
    def rewrite_source(self,id,old,new):
        src=next(s for s in self.index['sources'] if s['source_id']==id);path=Path(src['path'])
        raw=path.read_text().replace(old,new).encode();path.write_bytes(raw)
        h=hashlib.sha256(raw).hexdigest();src['sha256']=h
        next(s for s in self.data['source_catalog'] if s['source_id']==id)['sha256']=h
        for e in self.data['events']:
            refs=[e['actual']['evidence'],e['original_guidance']['evidence'],e['latest_prior_disclosure']['evidence']]+e['extra_evidence']
            for r in refs:
                if r['source_id']==id:r['source_sha256']=h
    def test_normal_complete_schema_source_fixture_passes(self):
        r=self.audit();self.assertTrue(r['passed']);self.assertEqual(r['schema_version'],'guidance-independent-source-audit-v2')
    def test_guidance_numeric_tamper_with_valid_reseal_rejected(self):
        e=self.data['events'][0]
        for key in ('original_guidance','latest_prior_disclosure'):e[key]['value_million']='5000'
        self.recalculate(0)
        with self.assertRaisesRegex(ValueError,'guidance:source-value'):self.audit()
    def test_preliminary_numeric_tamper_with_valid_reseal_rejected(self):
        self.data['events'][2]['latest_prior_disclosure']['value_million']='5500';self.recalculate(2)
        with self.assertRaisesRegex(ValueError,'preliminary:source-value'):self.audit()
    def test_changed_number_and_quote_absent_from_source_rejected(self):
        e=self.data['events'][1]
        for key in ('original_guidance','latest_prior_disclosure'):
            e[key]['value_million']='5000';e[key]['evidence']['quote']='approximately $5.0 billion'
        self.recalculate(1)
        with self.assertRaisesRegex(ValueError,'guidance:source-value'):self.audit()
    def test_quote_from_other_content_cannot_support_selected_fact(self):
        e=self.data['events'][1]
        for key in ('original_guidance','latest_prior_disclosure'):e[key]['evidence']['quote']='For the fourth quarter of 2020'
        with self.assertRaisesRegex(ValueError,'quote-in-selected-fact'):self.audit()
    def test_wrong_actual_value_rejected(self):
        self.data['events'][0]['actual']['value_million']='9000';self.recalculate(0)
        with self.assertRaisesRegex(ValueError,'actual:source-value'):self.audit()
    def test_previous_quarter_value_cannot_replace_current_column(self):
        self.data['events'][1]['actual']['value_million']='4500';self.recalculate(1)
        with self.assertRaisesRegex(ValueError,'actual:source-value'):self.audit()
    def test_current_column_header_is_checked_even_with_rebound_source(self):
        self.rewrite_source('2022Q2-actual','Q2 2022','Q1 2022')
        with self.assertRaisesRegex(ValueError,'current_column_period'):self.audit()
    def test_wrong_guidance_fiscal_period_in_raw_source_rejected(self):
        self.rewrite_source('2022Q2-guidance','second quarter of 2022','first quarter of 2022')
        with self.assertRaisesRegex(ValueError,'guidance_target_period'):self.audit()
    def test_wrong_preliminary_fiscal_period_in_raw_source_rejected(self):
        self.rewrite_source('2022Q3-preliminary','third quarter of 2022','second quarter of 2022')
        with self.assertRaisesRegex(ValueError,'preliminary_target_period'):self.audit()
    def test_raw_guidance_unit_controls_scale(self):
        self.rewrite_source('2022Q2-guidance','$5.5 billion','$5.5 million')
        with self.assertRaisesRegex(ValueError,'guidance:source-value'):self.audit()
    def test_raw_preliminary_unit_controls_scale(self):
        self.rewrite_source('2022Q3-preliminary','$5.8 billion','$5.8 million')
        with self.assertRaisesRegex(ValueError,'preliminary:source-value'):self.audit()
    def test_actual_source_unit_is_not_assumed(self):
        self.rewrite_source('2022Q2-actual','Revenue ($M)','Revenue ($B)')
        with self.assertRaisesRegex(ValueError,'million_table_missing'):self.audit()
    def test_wrong_output_unit_is_rejected(self):
        self.data['events'][1]['actual']['unit']='BILLION_USD'
        with self.assertRaisesRegex(ValueError,'identity'):self.audit()
    def test_changed_guidance_range_is_rejected(self):
        e=self.data['events'][1]
        for key in ('original_guidance','latest_prior_disclosure'):
            e[key]['business_half_range_million']='100';e[key]['business_range_million']=['5400','5600']
        with self.assertRaisesRegex(ValueError,'business-range'):self.audit()
    def test_changed_precision_cannot_force_direction(self):
        e=self.data['events'][1]
        for key in ('original_guidance','latest_prior_disclosure'):e[key]['display_quantum_million']='1'
        self.recalculate(1)
        with self.assertRaisesRegex(ValueError,'source-precision'):self.audit()
    def test_stale_pairing_hash_rejected(self):
        self.data['pairing_hash']='0'*64
        with self.assertRaisesRegex(ValueError,'pairing-hash'):self.audit(reseal=False)
    def test_wrong_schema_rejected(self):
        self.data['schema_version']='something-else'
        with self.assertRaisesRegex(ValueError,'schema'):self.audit()
    def test_empty_quote_is_not_source_binding(self):
        self.data['events'][1]['actual']['evidence']['quote']=''
        with self.assertRaisesRegex(ValueError,'quote-required'):self.audit()
    def test_missing_evidence_identity_rejected(self):
        self.data['events'][1]['actual']['evidence'].pop('source_id')
        with self.assertRaisesRegex(ValueError,'evidence-required'):self.audit()
    def test_missing_source_file_rejected(self):
        self.index['sources'][0]['path']=str(self.root/'does-not-exist.html')
        with self.assertRaisesRegex(ValueError,'source-file-present'):self.audit()
    def test_missing_catalog_source_rejected(self):
        self.data['source_catalog'].pop()
        with self.assertRaisesRegex(ValueError,'catalog-index-coverage'):self.audit()
    def test_duplicate_source_index_rejected(self):
        self.index['sources'].append(deepcopy(self.index['sources'][0]))
        with self.assertRaisesRegex(ValueError,'source-index-unique'):self.audit()
    def test_source_catalog_digest_binding_rejected(self):
        self.data['source_catalog'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'catalog-binding'):self.audit()
    def test_changed_source_bytes_rejected(self):
        p=Path(self.index['sources'][0]['path']);p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'raw-source'):self.audit()
    def test_missing_field_source_reference_rejected(self):
        self.data['events'][1]['actual']['evidence']['source_id']='missing'
        with self.assertRaisesRegex(ValueError,'source-present'):self.audit()
    def test_wrong_event_identity_rejected(self):
        self.data['events'][1]['event_id']='AMD:2022Q1:EARNINGS'
        with self.assertRaisesRegex(ValueError,'event-identity'):self.audit()
    def test_wrong_counts_rejected_even_after_reseal(self):
        self.data['counts']['dimension_matched']=10
        with self.assertRaisesRegex(ValueError,'derived-counts'):self.audit()
    def test_repeated_reports_do_not_create_new_independent_events(self):
        self.data['counts']['new_independent_events']=10
        with self.assertRaisesRegex(ValueError,'derived-counts'):self.audit()
    def test_shifted_source_clock_cannot_be_invented_in_json(self):
        self.data['events'][1]['original_guidance']['public_at']='2022-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'public-clock'):self.audit()
    def test_whole_chain_claim_cannot_be_inferred_from_two_sources(self):
        self.data['events'][1]['complete_historical_chain_proven']=True
        with self.assertRaisesRegex(ValueError,'not-complete-chain'):self.audit()


if __name__=='__main__':unittest.main()
