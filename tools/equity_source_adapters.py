"""Small explicit disclosure-format adapters, with separate numeric audit paths.

Unsupported issuers or ambiguous source formats stop. Importing a current HTML
page does not authenticate its historical publication or its coverage semantics.
"""
from datetime import datetime, timezone
from decimal import Decimal
import json
import re
from urllib.parse import urlsplit

from tools.verify_equity_guidance_pairs import Rows
from tools.prepare_announcement_review import PlainText

WORDS={'first':1,'second':2,'third':3,'fourth':4}
ISSUERS={
    'nvidia-earnings-html-v1':('NVDA','NVIDIA Corporation',('nvidianews.nvidia.com','investor.nvidia.com'),'NVIDIA'),
    'amd-earnings-html-v1':('AMD','Advanced Micro Devices, Inc.',('ir.amd.com',),'AMD'),
}


def require(ok,reason):
    if not ok:raise ValueError('disclosure_adapter:'+reason)


def normalize(raw):
    parser=PlainText();parser.feed(raw.decode('utf-8'))
    return ' '.join(' '.join(parser.parts).split())


def publication(raw):
    """Preserve source date precision; never invent an intraday timestamp."""
    html=raw.decode('utf-8');values=[]
    # Actual Newsroom releases expose an article date, while their sidebar has
    # newer related-story dates. Only the article's own date is authoritative.
    article_dates=re.findall(r'<div\b[^>]*class=[\"\'][^\"\']*\barticle-date\b[^\"\']*[\"\'][^>]*>\s*([^<]+)\s*</div>',html,re.I)
    if article_dates:
        require(len(article_dates)==1,'publication_missing_or_ambiguous')
        try:day=datetime.strptime(' '.join(article_dates[0].split()),'%B %d, %Y').date().isoformat()
        except ValueError:raise ValueError('disclosure_adapter:unsupported_article_date') from None
        return dict(publication_date=day,public_at=None,publication_precision='SOURCE_DATE_ONLY',historical_immutability='NOT_PROVEN')
    for value in re.findall(r'<time\b[^>]*datetime=[\"\']([^\"\']+)',html,re.I):values.append(value)
    for script in re.findall(r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>',html,re.I|re.S):
        try:obj=json.loads(script)
        except (ValueError,TypeError):continue
        def walk(item):
            if isinstance(item,dict):
                if 'datePublished' in item:values.append(item['datePublished'])
                for child in item.values():walk(child)
            elif isinstance(item,list):
                for child in item:walk(child)
        walk(obj)
    dates=set();clocks=set()
    for value in values:
        if not isinstance(value,str):continue
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):dates.add(value);continue
        try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:continue
        dates.add(d.date().isoformat())
        if d.tzinfo is not None:clocks.add(d.astimezone(timezone.utc).isoformat().replace('+00:00','Z'))
    require(len(dates)==1 and len(clocks)<=1,'publication_missing_or_ambiguous')
    return dict(publication_date=next(iter(dates)),public_at=next(iter(clocks)) if clocks else None,
                publication_precision='SOURCE_TIMESTAMP' if clocks else 'SOURCE_DATE_ONLY',historical_immutability='NOT_PROVEN')


def context(security,source):
    require(security['adapter'] in ISSUERS,'unsupported_adapter')
    symbol,name,domains,marker=ISSUERS[security['adapter']]
    require(security['symbol']==symbol and security['name']==name,'adapter_issuer_mismatch')
    url=urlsplit(source['url'])
    require(url.scheme=='https' and url.hostname in domains and not url.username and not url.password and not url.fragment,'official_source_url_required')
    raw=source['raw'];text=normalize(raw)
    require(marker in text and 'Financial Results' in text,'issuer_document_not_supported')
    return raw,text


def scalar(token,unit):
    value=Decimal(token.replace(',',''));scale=Decimal(1000) if unit.lower()=='billion' else Decimal(1)
    require(value.is_finite() and value>0,'positive_amount_required')
    return value*scale,Decimal(10)**value.as_tuple().exponent*scale


def fact(security,source,quarter,kind,value,quantum,quote,locator,clock):
    text=normalize(source['raw']);start=text.find(quote)
    require(start>=0,'quote_not_in_original')
    return dict(value_million=str(value),display_quantum_million=str(quantum),
        security_id=security['security_id'],fiscal_quarter=quarter,currency=security['currency'],unit='MILLION_USD',
        basis='REVENUE',coverage=source['coverage'],coverage_status='DECLARED_UNREVIEWED',kind=kind,
        business_half_range_million=None,business_range_million=None,approval_status='ADDITIONAL_REVIEW_REQUIRED',
        evidence=dict(source_id=source['source_id'],source_sha256=source['sha256'],quote=quote,
                      plain_text_start=start,plain_text_end=start+len(quote),locator=locator),**clock)


def extract(security,source,quarter,kind):
    if security['adapter']=='amd-earnings-html-v1':return extract_amd(security,source,quarter,kind)
    raw,text=context(security,source);clock=publication(raw)
    if kind=='ACTUAL':
        parser=Rows();parser.feed(raw.decode('utf-8'));found=[]
        for table in parser.tables:
            for index,row in enumerate(table['rows']):
                if not row or row[0].strip().lower()!='revenue':continue
                inside=' '.join(' '.join(r) for r in table['rows'][:index])
                before=table['before']+' '+inside
                markers=re.findall(r'\b(?:Non[- ]GAAP|GAAP)\b',inside,re.I) or re.findall(r'\b(?:Non[- ]GAAP|GAAP)\b',table['before'],re.I)
                if not markers or markers[-1].upper()!='GAAP':continue
                headers=re.findall(r'Q([1-4])\s+FY\s*(20\d\d|\d\d)\b',inside)
                if not headers:continue  # Annual/income statements are not the quarterly summary.
                require(re.search(r'\$\s*in millions',before,re.I) is not None,'actual_amount_unit_unsupported')
                year=headers[0][1];year='20'+year if len(year)==2 else year
                require(year+'Q'+headers[0][0]==quarter,'actual_current_period_mismatch')
                quote=' '.join(row)
                match=re.match(r'Revenue\s+\$\s*([\d,]+)(?:\s|$)',quote,re.I)
                require(match is not None,'actual_current_amount_missing')
                normalized=re.search(r'Revenue\s+\$\s*'+re.escape(match[1]),text,re.I)
                require(normalized is not None,'actual_quote_missing')
                found.append((Decimal(match[1].replace(',','')),normalized[0]))
        require(len(found)==1,'actual_table_missing_or_ambiguous')
        value,quote=found[0]
        return fact(security,source,quarter,'FORMAL_RESULTS',value,Decimal(1),quote,'GAAP table; first current fiscal-quarter Revenue column',clock)
    pattern=(r'NVIDIA[’\']s outlook for the (first|second|third|fourth) quarter of fiscal (20\d\d) is as follows:.*?'
             r'Revenue is expected to be \$([\d,]+(?:\.\d+)?) (billion|million), plus or minus ([\d.]+)%')
    matches=[m for m in re.finditer(pattern,text,re.I) if m[2]+'Q'+str(WORDS[m[1].lower()])==quarter]
    require(len(matches)==1,'guidance_target_missing_or_ambiguous')
    match=matches[0];value,quantum=scalar(match[3],match[4]);percent=Decimal(match[5])
    require(0<percent<100,'guidance_percentage_invalid')
    quote=match[0][match[0].find('Revenue'):]
    result=fact(security,source,quarter,'COMPANY_GUIDANCE',value,quantum,quote,'Outlook; named target fiscal quarter; percentage business range',clock)
    half=value*percent/100
    result.update(business_half_range_million=str(half),business_range_million=[str(value-half),str(value+half)],business_range_percent=str(percent))
    return result


def audit_fact(security,source,quarter,kind,field):
    """Re-extract source numbers without using extract() or JSON value matching."""
    if security['adapter']=='amd-earnings-html-v1':return audit_amd(security,source,quarter,kind,field)
    raw,text=context(security,source)
    require(field['evidence']['source_sha256']==source['sha256'] and field['evidence']['source_id']==source['source_id'],'audit_source_binding')
    require(field['security_id']==security['security_id'] and field['fiscal_quarter']==quarter and field['currency']==security['currency'] and field['unit']=='MILLION_USD' and field['basis']=='REVENUE','audit_dimensions')
    if kind=='ACTUAL':
        # Different path: contiguous GAAP summary text with the current header,
        # rather than selecting the producer's table row or trusting its quote.
        pattern=r'(?<!Non-)(?<!Non )\bGAAP\b\s*\(\$ in millions[^)]*\)\s*Q([1-4])\s+FY\s*(20\d\d|\d\d)\b.*?Revenue\s+\$\s*([\d,]+)'
        rows=list(re.finditer(pattern,text,re.I))
        require(len(rows)==1,'audit_gaap_summary_missing_or_ambiguous')
        match=rows[0];year='20'+match[2] if len(match[2])==2 else match[2]
        require(year+'Q'+match[1]==quarter,'audit_actual_period')
        value=Decimal(match[3].replace(',',''));quantum=Decimal(1);half=None
        require(field['kind']=='FORMAL_RESULTS','audit_actual_kind')
    else:
        heading=re.compile(r'NVIDIA[’\']s outlook for the ([a-z]+) quarter of fiscal (20\d\d) is as follows:',re.I)
        sections=[]
        for match in heading.finditer(text):
            if match[2]+'Q'+str(WORDS.get(match[1].lower(),0))==quarter:sections.append(text[match.end():match.end()+450])
        require(len(sections)==1,'audit_guidance_period')
        amounts=list(re.finditer(r'Revenue is expected to be \$([\d,]+(?:\.\d+)?) (million|billion), plus or minus ([\d.]+)%',sections[0],re.I))
        require(len(amounts)==1,'audit_guidance_ambiguous')
        match=amounts[0];literal=Decimal(match[1].replace(',',''));scale=Decimal({'million':1,'billion':1000}[match[2].lower()])
        value=literal*scale;quantum=Decimal(10)**literal.as_tuple().exponent*scale;half=value*Decimal(match[3])/100
        require(field['kind']=='COMPANY_GUIDANCE' and Decimal(field['business_half_range_million'])==half and [Decimal(n) for n in field['business_range_million']]==[value-half,value+half],'audit_business_range')
    require(Decimal(field['value_million'])==value,'audit_source_value')
    require(Decimal(field['display_quantum_million'])==quantum,'audit_source_precision')
    ref=field['evidence'];require(ref['quote'] and text[ref['plain_text_start']:ref['plain_text_end']]==ref['quote'],'audit_quote_binding')
    clock=publication(raw)
    require(all(field[k]==v for k,v in clock.items()),'audit_clock_binding')
    return True


def extract_amd(security,source,quarter,kind):
    """Reuse the existing AMD extractor, without its fixed ten-event cohort."""
    from tools.equity_guidance_pairs import plain,exact_actual,extract_guidance,publication as amd_clock
    raw,normalized=context(security,source);text=plain(raw.decode());at=amd_clock(raw.decode())
    require(at is not None,'amd_publication_missing')
    clock=dict(public_at=at,publication_date=at[:10],publication_precision='SOURCE_TIMESTAMP',historical_immutability='NOT_PROVEN')
    metadata=dict(source_id=source['source_id'],sha256=source['sha256'],published_at=at)
    parsed=exact_actual(metadata,text,quarter) if kind=='ACTUAL' else extract_guidance(metadata,text,quarter,'ADDITIONAL_REVIEW_REQUIRED')
    quote=(' '.join(parsed['evidence']['quote'].split()) if kind!='ACTUAL' else re.search(r'Revenue\s*\(\$M\)\s*\$\s*[\d,]+',normalized)[0])
    result=fact(security,source,quarter,'FORMAL_RESULTS' if kind=='ACTUAL' else 'COMPANY_GUIDANCE',
        Decimal(parsed['value_million']),Decimal(parsed['display_quantum_million']),quote,parsed['evidence']['locator'],clock)
    if kind!='ACTUAL':result.update({k:parsed[k] for k in ('business_half_range_million','business_range_million')})
    return result


def audit_amd(security,source,quarter,kind,field):
    from tools.verify_equity_guidance_pairs import actual_source,guidance_source,source_clock
    raw,text=context(security,source);parser=Rows();parser.feed(raw.decode())
    parsed=(actual_source if kind=='ACTUAL' else guidance_source)(parser,quarter)
    require(Decimal(field['value_million'])==parsed['value'],'audit_source_value')
    require(Decimal(field['display_quantum_million'])==parsed['quantum'],'audit_source_precision')
    require(field['kind']==('FORMAL_RESULTS' if kind=='ACTUAL' else 'COMPANY_GUIDANCE'),'audit_amount_kind')
    require(field['security_id']==security['security_id'] and field['fiscal_quarter']==quarter and field['currency']=='USD' and field['unit']=='MILLION_USD' and field['basis']=='REVENUE','audit_dimensions')
    if kind!='ACTUAL':
        require(Decimal(field['business_half_range_million'])==parsed['half'] and [Decimal(x) for x in field['business_range_million']]==parsed['range'],'audit_business_range')
    ref=field['evidence'];require(ref['source_id']==source['source_id'] and ref['source_sha256']==source['sha256'],'audit_source_binding')
    require(ref['quote'] and text[ref['plain_text_start']:ref['plain_text_end']]==ref['quote'],'audit_quote_binding')
    require(field['public_at']==source_clock(parser).isoformat().replace('+00:00','Z'),'audit_clock_binding')
    return True
