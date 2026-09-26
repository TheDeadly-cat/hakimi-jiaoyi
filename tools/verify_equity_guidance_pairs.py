"""Independent source-table and decimal-interval audit; standard library only.

Does not import the pairing implementation or read prices, broker state or URLs.
The source index points to retained local originals and must remain private.
"""
from html.parser import HTMLParser
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import argparse
import hashlib
import json
import re


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.current=None; self.cells=None; self.all_text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.current=[]
        if tag in ('th','td') and self.current is not None:self.cells=[]
    def handle_data(self,text):
        self.all_text.append(text)
        if self.cells is not None:self.cells.append(text)
    def handle_endtag(self,tag):
        if tag in ('th','td') and self.cells is not None:
            self.current.append(' '.join(''.join(self.cells).split()));self.cells=None
        if tag=='tr' and self.current is not None:
            self.rows.append(self.current);self.current=None


def verify(result_path,index_path):
    raw=result_path.read_bytes(); data=json.loads(raw)
    index=json.loads(index_path.read_bytes());sources={s['source_id']:s for s in index['sources'] if s['status']==200}
    checks=[];parsed={}
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
        if not passed:raise ValueError('guidance_audit_failed:'+name)
    for id,s in sources.items():
        raw_source=Path(s['path']).read_bytes()
        check('raw-source:'+id,hashlib.sha256(raw_source).hexdigest()==s['sha256'])
        p=Rows();p.feed(raw_source.decode('utf-8'));parsed[id]=p
    check('fixed-coverage',[e['fiscal_quarter'] for e in data['events']]==['2022Q1','2022Q2','2022Q3','2022Q4','2023Q1','2023Q2','2023Q3','2023Q4','2024Q1','2024Q2'])
    for event in data['events']:
        q=event['fiscal_quarter'];a=event['actual'];g=event['latest_prior_disclosure']
        parser=parsed[a['evidence']['source_id']]
        revenue=next(row for row in parser.rows if row and re.fullmatch(r'Revenue\s*\(\$M\)',row[0]))
        value=re.search(r'[\d,]+',' '.join(revenue[1:]))[0].replace(',','')
        check(q+':current-table-revenue',Decimal(value)==Decimal(a['value_million']))
        references=[a['evidence']]+([event['original_guidance']['evidence']] if event['original_guidance'] else [])
        if g and g['kind']=='PRELIMINARY_RESULTS':references.append(g['evidence'])
        references+=event['extra_evidence']
        for n,ref in enumerate(references):
            source=sources[ref['source_id']]
            check(f'{q}:reference-hash:{n}',ref['source_sha256']==source['sha256'])
            quote=' '.join(ref['quote'].split())
            text=' '.join(''.join(parsed[ref['source_id']].all_text).split())
            check(f'{q}:quote:{n}',quote in text)
        if g is None:
            check(q+':missing',event['comparison']['status']=='MISSING_PRIOR');continue
        check(q+':prior-clock',g['public_at']<a['public_at'])
        if a['coverage']!=g['coverage']:
            check(q+':scope-mismatch',event['comparison']['status']=='NOT_COMPARABLE' and event['comparison']['nominal_ratio'] is None)
            continue
        av,pv=Decimal(a['value_million']),Decimal(g['value_million'])
        al,ah=av-Decimal(a['display_quantum_million'])/2,av+Decimal(a['display_quantum_million'])/2
        pl,ph=pv-Decimal(g['display_quantum_million'])/2,pv+Decimal(g['display_quantum_million'])/2
        interval=[al-ph,ah-pl]
        check(q+':interval-subtraction',[Decimal(x) for x in event['comparison']['difference_interval_million']]==interval)
        sign='ABOVE' if min(interval)>0 else 'BELOW' if max(interval)<0 else 'UNCERTAIN_PRECISION'
        check(q+':sign',event['comparison']['status']==sign)
        recorded=Decimal(event['comparison']['nominal_ratio'])
        exact=(Fraction(av)-Fraction(pv))/Fraction(pv)
        half_last_unit=Fraction(Decimal(1).scaleb(recorded.as_tuple().exponent))/2
        check(q+':nominal-ratio',abs(Fraction(recorded)-exact)<=half_last_unit)
    q3=data['events'][2]
    check('2022Q3-three-stage-chain',[r['kind'] for r in q3['disclosure_chain']]==['COMPANY_GUIDANCE','PRELIMINARY_RESULTS','FORMAL_RESULTS'])
    check('2022Q3-no-reused-business-range',q3['latest_prior_disclosure']['business_range_million'] is None)
    check('no-new-economic-execution',data['counts']['new_backtest_reports']==0 and all(e['economic_execution_allowed'] is False for e in data['events']))
    check('not-run-is-not-zero-intervention',data['counts']['new_content_interventions'] is None)
    check('no-extra-approved-fields',data['counts']['additional_human_approved_fields']==0)
    for id,s in sources.items():
        check('source-unchanged-after:'+id,hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256'])
    return {'schema_version':'guidance-independent-source-audit-v1','pairing_hash':data['pairing_hash'],
            'data_sha256':hashlib.sha256(raw).hexdigest(),'source_count':len(sources),
            'check_count':len(checks),'passed':all(c['passed'] for c in checks),
            'checks':checks,'network_calls':0,'economic_experiments':0,
            'ratio_check':'EXACT_RATIONAL_WITH_HALF_LAST_RECORDED_DECIMAL_UNIT',
            'limitations':['SOURCE_CHAIN_COMPLETENESS_NOT_PROVEN','NOT_HUMAN_FIELD_APPROVAL']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('result','source-index','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=verify(a.result,a.source_index)
    with a.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='checks'}))
