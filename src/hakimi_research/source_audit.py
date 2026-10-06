"""Independent source-table and decimal-interval audit; standard library only.

Does not import the pairing implementation or read prices, broker state or URLs.
The source index points to retained local originals and must remain private.
"""
from html.parser import HTMLParser
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import re


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.current=None; self.cells=None; self.all_text=[]
        self.tables=[];self.table_stack=[];self.ignored=0;self.clock=None;self.clocks=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('head','script','style'):self.ignored+=1
        if self.ignored:return
        if tag=='table':self.table_stack.append({'before':self.text[-500:],'rows':[]})
        if tag=='time':self.clock={'datetime':dict(attrs).get('datetime'),'text':[]}
        if tag=='tr':self.current=[]
        if tag in ('th','td') and self.current is not None:self.cells=[]
    def handle_data(self,text):
        if self.ignored:return
        self.all_text.append(text)
        if self.cells is not None:self.cells.append(text)
        if self.clock is not None:self.clock['text'].append(text)
    def handle_endtag(self,tag):
        if tag in ('head','script','style'):self.ignored-=1;return
        if self.ignored:return
        if tag in ('th','td') and self.cells is not None:
            self.current.append(' '.join(''.join(self.cells).split()));self.cells=None
        if tag=='tr' and self.current is not None:
            if self.table_stack:self.table_stack[-1]['rows'].append(self.current)
            self.rows.append(self.current);self.current=None
        if tag=='table' and self.table_stack:self.tables.append(self.table_stack.pop())
        if tag=='time' and self.clock is not None:self.clocks.append(self.clock);self.clock=None

    @property
    def text(self):return ' '.join(' '.join(self.all_text).split())


COHORT=[f'{y}Q{q}' for y in (2022,2023,2024) for q in range(1,5) if y<2024 or q<3]
QUARTERS={'first':1,'second':2,'third':3,'fourth':4}
IDENTITY={'security_id':'US:COMMON:CUSIP:007903107','currency':'USD','unit':'MILLION_USD','basis':'REVENUE'}


def require(condition,name):
    if not condition:raise ValueError('guidance_audit_failed:'+name)


def seal_hash(data):
    return hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='pairing_hash'},
        sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def number(value):
    require(type(value) is str,'decimal_string_required')
    n=Decimal(value);require(n.is_finite(),'finite_number_required');return n


def stamp(value):
    require(type(value) is str,'timestamp_required')
    value=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(value.tzinfo is not None,'timestamp_zone_required')
    return value.astimezone(timezone.utc)


def source_clock(parser):
    clocks=[]
    for row in parser.clocks:
        label=' '.join(row['text']); match=re.search(r'\b(EST|EDT)\b',label)
        if row['datetime'] and match:
            local=datetime.fromisoformat(row['datetime'])
            require(local.tzinfo is None,'source_clock_unexpected_offset')
            clocks.append(local.replace(tzinfo=timezone(timedelta(hours=-5 if match[1]=='EST' else -4))).astimezone(timezone.utc))
    require(len(set(clocks))==1,'source_publication_clock_missing_or_ambiguous')
    return clocks[0]


def money(token,unit):
    # Derive the scale and displayed precision from the SOURCE, never JSON.
    scale={'million':Decimal(1),'billion':Decimal(1000)}[unit.lower()]
    value=Decimal(token.replace(',',''))
    return value*scale,Decimal(10)**value.as_tuple().exponent*scale


def same_quote(quote,text):
    normalize=lambda s:re.sub(r'\$\s+', '$',' '.join(s.split()))
    return normalize(quote) in normalize(text)


def actual_source(parser,quarter):
    for table in parser.tables:
        for i,row in enumerate(table['rows']):
            if not row or not re.fullmatch(r'Revenue\s*\(\$M\)',row[0]):continue
            context=table['before']+' '+' '.join(' '.join(r) for r in table['rows'][:i])
            headings=re.findall(r'(?:Non[- ]?GAAP(?:\([^)]*\))?|GAAP) Quarterly Financial Results',context,re.I)
            require(headings and headings[-1].lower()=='gaap quarterly financial results','actual_gaap_table_required')
            headers=[r for r in table['rows'][:i] if any(re.fullmatch(r'Q[1-4]\s+20\d\d|20\d\dQ[1-4]',c) for c in r)]
            require(bool(headers),'actual_period_header_missing')
            periods=[c for c in headers[-1] if re.fullmatch(r'Q[1-4]\s+20\d\d|20\d\dQ[1-4]',c)]
            first=periods[0];first=first if first.startswith('20') else first[-4:]+'Q'+first[1]
            require(first==quarter,'actual_current_column_period_mismatch')
            joined=' '.join(row)
            match=re.match(r'Revenue\s*\(\$M\)\s*\$\s*([\d,]+)(?:\s|$)',joined)
            require(match is not None,'actual_current_column_money_missing')
            return {'value':Decimal(match[1].replace(',','')),'quantum':Decimal(1),'text':joined}
    raise ValueError('guidance_audit_failed:actual_million_table_missing')


def guidance_source(parser,quarter):
    pattern=(r'For the (first|second|third|fourth) quarter of (20\d\d),\s*AMD expects revenue to be '
             r'approximately \$([\d,]+(?:\.\d+)?) (billion|million),\s*plus or minus '
             r'\$([\d,]+(?:\.\d+)?) (billion|million)')
    found=[m for m in re.finditer(pattern,parser.text,re.I) if m[2]+'Q'+str(QUARTERS[m[1].lower()])==quarter]
    require(len(found)==1,'guidance_target_period_missing_or_ambiguous')
    m=found[0];value,quantum=money(m[3],m[4]);half,_=money(m[5],m[6])
    return {'value':value,'quantum':quantum,'half':half,'range':[value-half,value+half],'text':m[0]}


def preliminary_source(parser,quarter):
    periods={(m[2]+'Q'+str(QUARTERS[m[1].lower()])) for m in re.finditer(
        r'selected preliminary financial results for the (first|second|third|fourth) quarter of (20\d\d)',parser.text,re.I)}
    require(periods=={quarter},'preliminary_target_period_missing_or_ambiguous')
    found=[m for m in re.finditer(r'(First|Second|Third|Fourth) quarter revenue is expected to be approximately '
        r'\$([\d,]+(?:\.\d+)?) (billion|million)',parser.text,re.I) if QUARTERS[m[1].lower()]==int(quarter[-1])]
    require(len(found)==1,'preliminary_revenue_missing_or_ambiguous')
    value,quantum=money(found[0][2],found[0][3])
    return {'value':value,'quantum':quantum,'text':found[0][0]}


def verify(result_path,index_path):
    raw=result_path.read_bytes(); data=json.loads(raw)
    index_raw=index_path.read_bytes();index=json.loads(index_raw)
    checks=[];parsed={}
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
        if not passed:raise ValueError('guidance_audit_failed:'+name)
    check('schema',data.get('schema_version')=='same-quarter-guidance-pairs-v1')
    check('pairing-hash',data.get('pairing_hash')==seal_hash(data))
    check('source-catalog-required',type(data.get('source_catalog')) is list)
    check('source-index-unique',len({s['source_id'] for s in index['sources']})==len(index['sources']))
    sources={s['source_id']:s for s in index['sources'] if s['status']==200}
    catalog={s['source_id']:s for s in data['source_catalog']}
    check('source-catalog-unique',len(catalog)==len(data['source_catalog']))
    check('source-catalog-index-coverage',set(sources)==set(catalog))
    for id,s in sources.items():
        url=urlsplit(s['url'])
        check('official-source:'+id,url.scheme=='https' and url.hostname=='ir.amd.com' and not url.username and not url.password)
        check('catalog-binding:'+id,all(catalog[id][k]==s[k] for k in ('sha256','url','retrieved_at')))
        check('source-file-present:'+id,Path(s['path']).is_file())
        raw_source=Path(s['path']).read_bytes()
        check('raw-source:'+id,hashlib.sha256(raw_source).hexdigest()==s['sha256'])
        p=Rows();p.feed(raw_source.decode('utf-8'));parsed[id]=p
    check('fixed-coverage',[e['fiscal_quarter'] for e in data['events']]==COHORT)

    def bound_fact(field,quarter,kind):
        check(quarter+':'+kind+':fact-required',type(field) is dict)
        ref=field.get('evidence')
        check(quarter+':'+kind+':evidence-required',type(ref) is dict and all(k in ref for k in ('source_id','source_sha256','quote')))
        check(quarter+':'+kind+':quote-required',type(ref['quote']) is str and bool(ref['quote'].strip()))
        id=ref['source_id']
        check(quarter+':'+kind+':source-present',id in sources)
        check(quarter+':'+kind+':identity',all(field.get(k)==v for k,v in IDENTITY.items()) and field['fiscal_quarter']==quarter)
        check(quarter+':'+kind+':reference-hash',ref['source_sha256']==sources[id]['sha256'])
        parser=parsed[id]
        extracted=(actual_source if kind=='actual' else guidance_source if kind=='guidance' else preliminary_source)(parser,quarter)
        check(quarter+':'+kind+':source-value',number(field['value_million'])==extracted['value'])
        check(quarter+':'+kind+':source-precision',number(field['display_quantum_million'])==extracted['quantum'])
        check(quarter+':'+kind+':quote-in-selected-fact',same_quote(ref['quote'],extracted['text']))
        clock=source_clock(parser)
        check(quarter+':'+kind+':public-clock',stamp(field['public_at'])==clock==stamp(catalog[id]['published_at']))
        if kind=='guidance':
            check(quarter+':guidance:amount-type',field['kind']=='COMPANY_GUIDANCE')
            check(quarter+':guidance:business-range',number(field['business_half_range_million'])==extracted['half'] and
                  [number(n) for n in field['business_range_million']]==extracted['range'])
        elif kind=='preliminary':
            check(quarter+':preliminary:amount-type',field['kind']=='PRELIMINARY_RESULTS' and field['business_half_range_million'] is None and field['business_range_million'] is None)
        return extracted

    def comparison(event,a,p,prior,label):
        q=event['fiscal_quarter'];result=event[label]
        mismatch=[k for k in (*IDENTITY,'fiscal_quarter','coverage') if event['actual'][k]!=prior[k]]
        check(q+':'+label+':dimensions',result['mismatched_dimensions']==mismatch)
        if mismatch:
            check(q+':'+label+':incomparable',result['status']=='NOT_COMPARABLE' and all(result[k] is None for k in
                ('nominal_difference_million','difference_interval_million','nominal_ratio','positive_condition')))
            return
        # Both values and precision below came independently from original HTML.
        av,pv=a['value'],p['value'];radius=(a['quantum']+p['quantum'])/2
        interval=[av-pv-radius,av-pv+radius]
        check(q+':'+label+':gap',number(result['nominal_difference_million'])==av-pv)
        check(q+':'+label+':interval',[number(x) for x in result['difference_interval_million']]==interval)
        sign='ABOVE' if min(interval)>0 else 'BELOW' if max(interval)<0 else 'UNCERTAIN_PRECISION'
        check(q+':'+label+':direction',result['status']==sign and result['positive_condition'] is (True if sign=='ABOVE' else False if sign=='BELOW' else None))
        recorded=number(result['nominal_ratio']);exact=(Fraction(av)-Fraction(pv))/Fraction(pv)
        check(q+':'+label+':ratio',abs(Fraction(recorded)-exact)<=Fraction(Decimal(1).scaleb(recorded.as_tuple().exponent))/2)

    for event in data['events']:
        q=event['fiscal_quarter'];a=event['actual'];g=event['latest_prior_disclosure']
        check(q+':event-identity',event['event_id']=='AMD:'+q+':EARNINGS')
        actual=bound_fact(a,q,'actual');original=bound_fact(event['original_guidance'],q,'guidance')
        check(q+':latest-required',type(g) is dict)
        if g['kind']=='PRELIMINARY_RESULTS':latest=bound_fact(g,q,'preliminary')
        else:
            check(q+':latest-guidance-binding',g==event['original_guidance']);latest=original
        expected_coverage='AMD_EXCLUDING_XILINX' if q=='2022Q1' else 'AMD_CONSOLIDATED_REPORTED'
        check(q+':source-scope',a['coverage']=='AMD_CONSOLIDATED_REPORTED' and event['original_guidance']['coverage']==expected_coverage and g['coverage']==expected_coverage)
        references=event['extra_evidence']
        for n,ref in enumerate(references):
            check(f'{q}:extra-source:{n}',ref['source_id'] in sources)
            source=sources[ref['source_id']]
            check(f'{q}:reference-hash:{n}',ref['source_sha256']==source['sha256'])
            check(f'{q}:quote:{n}',same_quote(ref['quote'],parsed[ref['source_id']].text))
        if q=='2022Q1':
            check(q+':xilinx-scope-evidence',any('Guidance does not contemplate the addition of Xilinx' in r['quote'] for r in references) and
                any('results include partial quarter financial results from' in r['quote'] for r in references))
        chain=[{'source_id':event['original_guidance']['evidence']['source_id'],'kind':'COMPANY_GUIDANCE','public_at':event['original_guidance']['public_at']}]
        if g['kind']=='PRELIMINARY_RESULTS':chain.append({'source_id':g['evidence']['source_id'],'kind':'PRELIMINARY_RESULTS','public_at':g['public_at']})
        chain.append({'source_id':a['evidence']['source_id'],'kind':'FORMAL_RESULTS','public_at':a['public_at']})
        check(q+':chain-bound-to-facts',event['disclosure_chain']==chain)
        check(q+':chain-order',all(stamp(x['public_at'])<stamp(y['public_at']) for x,y in zip(chain,chain[1:])))
        check(q+':bounded-source-not-complete-chain',event['complete_historical_chain_proven'] is False)
        check(q+':retained-price-metadata',event['old_price_status'] in ('DATA_EXCLUDED','NO_PRICE_SIGNAL','CONTENT_VETO','ENTERED_STOPPED','ENTERED_MARKED') and
            (event['old_price_condition'] is None if event['old_price_status']=='DATA_EXCLUDED' else type(event['old_price_condition']) is bool))
        comparison(event,actual,latest,g,'comparison')
        comparison(event,actual,original,event['original_guidance'],'comparison_to_original_guidance')
    q3=data['events'][2]
    check('2022Q3-three-stage-chain',[r['kind'] for r in q3['disclosure_chain']]==['COMPANY_GUIDANCE','PRELIMINARY_RESULTS','FORMAL_RESULTS'])
    check('2022Q3-no-reused-business-range',q3['latest_prior_disclosure']['business_range_million'] is None)
    states=[e['comparison']['status'] for e in data['events']]
    expected_counts={'events':10,'dimension_matched':sum(s!='NOT_COMPARABLE' for s in states),
        'numerically_above':states.count('ABOVE'),'numerically_below':states.count('BELOW'),
        'precision_uncertain':states.count('UNCERTAIN_PRECISION'),'not_comparable':states.count('NOT_COMPARABLE'),'missing_prior':0,
        'early_disclosure':sum(e['latest_prior_disclosure']['kind']=='PRELIMINARY_RESULTS' for e in data['events']),
        'retained_price_accepted':sum(e['old_price_status']!='DATA_EXCLUDED' for e in data['events']),
        'retained_price_signals':sum(e['old_price_condition'] is True for e in data['events']),
        'new_independent_events':0,'new_backtest_reports':0,'additional_human_approved_fields':0}
    check('derived-counts',all(type(data['counts'].get(k)) is int and data['counts'][k]==v for k,v in expected_counts.items()))
    check('no-new-economic-execution',data['counts']['new_backtest_reports']==0 and all(e['economic_execution_allowed'] is False for e in data['events']))
    check('not-run-is-not-zero-intervention',data['counts']['new_content_interventions'] is None)
    check('no-extra-approved-fields',data['counts']['additional_human_approved_fields']==0)
    check('no-study-admission',data['decision']['economic_execution_allowed'] is False)
    check('source-scope-not-global-proof',data['source_scope']['complete_historical_chain_proven'] is False)
    for id,s in sources.items():
        check('source-unchanged-after:'+id,hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256'])
    check('input-result-unchanged',result_path.read_bytes()==raw)
    check('input-index-unchanged',index_path.read_bytes()==index_raw)
    return {'schema_version':'guidance-independent-source-audit-v2','pairing_hash':data['pairing_hash'],
            'data_sha256':hashlib.sha256(raw).hexdigest(),'source_count':len(sources),
            'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'economic_fields_independently_parsed':['actual_current_quarter_revenue','original_guidance_midpoint_and_range','latest_preliminary_revenue','source_amount_units_and_precision','source_target_quarter','source_publication_clock'],
            'check_count':len(checks),'passed':all(c['passed'] for c in checks),
            'checks':checks,'network_calls':0,'economic_experiments':0,
            'ratio_check':'EXACT_RATIONAL_WITH_HALF_LAST_RECORDED_DECIMAL_UNIT',
            'limitations':['SOURCE_CHAIN_COMPLETENESS_NOT_PROVEN','NOT_HUMAN_FIELD_APPROVAL','HASH_IS_CONTENT_IDENTITY_NOT_AUTHENTICATION','RETAINED_PRICE_COUNTS_INTERNAL_CONSISTENCY_ONLY']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('result','source-index','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=verify(a.result,a.source_index)
    with a.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='checks'}))
