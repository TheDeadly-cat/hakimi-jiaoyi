"""Pair retained AMD disclosures; no market reads, strategy, or approvals.

Outputs distinguish a numerical comparison from information novelty, source-chain
coverage and human approval. A successful extraction never opens an execution gate.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.equity_content_protocol import digest, utc, validate_approval
from tools.prepare_announcement_review import PlainText

COHORT = [f'{year}Q{quarter}' for year in (2022, 2023, 2024)
          for quarter in range(1, 5) if year < 2024 or quarter < 3]
SECURITY = 'US:COMMON:CUSIP:007903107'
FULL_SCOPE = 'AMD_CONSOLIDATED_REPORTED'
QWORDS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4}


def plain(raw):
    parser = PlainText(); parser.feed(raw)
    return '\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip())


def decimal(value):
    if not isinstance(value, str):
        raise ValueError('pair_decimal_string_required')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('pair_finite_decimal_required')
    return result


def interval_comparison(actual, prior):
    """Conservative decimal-display bounds, separate from business guidance range.

    Half of each last displayed unit is a declared reconstruction assumption,
    not a probabilistic interval or the publisher's economic forecast range.
    Equality/touching zero is uncertain. Future users must not silently exchange
    the nominal-midpoint condition for a guidance-upper-bound condition.
    """
    if prior is None:
        return {'status':'MISSING_PRIOR', 'mismatched_dimensions':[],
                'nominal_difference_million':None, 'difference_interval_million':None,
                'nominal_ratio':None, 'positive_condition':None}
    keys = ('security_id', 'fiscal_quarter', 'currency', 'unit', 'basis', 'coverage')
    mismatches = [key for key in keys if actual[key] != prior[key]]
    if mismatches:
        return {'status': 'NOT_COMPARABLE', 'mismatched_dimensions': mismatches,
                'nominal_difference_million': None, 'difference_interval_million': None,
                'nominal_ratio': None, 'positive_condition': None}
    a, p = decimal(actual['value_million']), decimal(prior['value_million'])
    aq, pq = decimal(actual['display_quantum_million']), decimal(prior['display_quantum_million'])
    if min(a, p, aq, pq) <= 0:
        raise ValueError('pair_positive_values_and_precision_required')
    gap = a - p; radius = (aq + pq) / 2
    lower, upper = gap - radius, gap + radius
    status = 'ABOVE' if lower > 0 else 'BELOW' if upper < 0 else 'UNCERTAIN_PRECISION'
    return {'status': status, 'mismatched_dimensions': [],
            'nominal_difference_million': str(gap),
            'difference_interval_million': [str(lower), str(upper)],
            'nominal_ratio': str(gap / p),
            'positive_condition': True if status == 'ABOVE' else False if status == 'BELOW' else None}


def evidence(source, text, quote, locator):
    start = text.index(quote)
    return {'source_id': source['source_id'], 'source_sha256': source['sha256'],
            'plain_text_start': start, 'plain_text_end': start + len(quote),
            'quote': quote, 'locator': locator}


def publication(raw):
    match = re.search(r'<time datetime="([0-9T:-]+)" class="date">\s*([^<]+)</time>', raw)
    if not match:
        return None
    local = datetime.fromisoformat(match[1]).replace(tzinfo=ZoneInfo('America/New_York'))
    if local.tzname() not in match[2]:
        raise ValueError('pair_publication_timezone_mismatch')
    return local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def fact(value, quantum, quarter, source, text, quote, locator, *, approval='ADDITIONAL_REVIEW_REQUIRED', coverage=FULL_SCOPE):
    return {'value_million': value, 'display_quantum_million': quantum,
            'security_id': SECURITY, 'fiscal_quarter': quarter, 'currency': 'USD',
            'unit': 'MILLION_USD', 'basis': 'REVENUE', 'coverage': coverage,
            'approval_status': approval, 'public_at': source['published_at'],
            'evidence': evidence(source, text, quote, locator)}


def exact_actual(source, text, quarter):
    match = re.search(r'GAAP Quarterly Financial Results(?P<header>.*?)Revenue\s*\(\$M\)\s*\$\s*([\d,]+)', text, re.S)
    if not match:
        raise ValueError('pair_actual_revenue_table_missing')
    first_period = re.search(r'Q([1-4])\s+(20\d\d)', match['header'])
    if not first_period or first_period[2] + 'Q' + first_period[1] != quarter:
        raise ValueError('pair_actual_column_period_mismatch')
    token = match[2]
    quote = text[match.start():match.end()].split('Revenue', 1)[1]
    quote = 'Revenue' + quote
    return fact(token.replace(',', ''), '1', quarter, source, text, quote,
                'First Revenue ($M) value in GAAP Quarterly Financial Results; current-quarter column')


def extract_guidance(source, text, quarter, approval):
    matches = list(re.finditer(r'For the ([a-z]+) quarter of (20\d\d), AMD expects revenue to be approximately \$(\d+(?:\.\d+)?) billion, plus or minus \$(\d+(?:\.\d+)?) million', text))
    matches = [m for m in matches if m[2] + 'Q' + str(QWORDS.get(m[1], 0)) == quarter]
    if len(matches) != 1:
        raise ValueError('pair_target_quarter_guidance_missing_or_ambiguous')
    match = matches[0]
    value = decimal(match[3]); quantum = Decimal(10) ** value.as_tuple().exponent * 1000
    quote = f'approximately ${match[3]} billion, plus or minus ${match[4]} million'
    result = fact(str(value * 1000), str(quantum), quarter, source, text, quote,
                  'Current Outlook; explicitly named target fiscal quarter', approval=approval)
    half = decimal(match[4])
    result.update(kind='COMPANY_GUIDANCE', business_half_range_million=str(half),
                  business_range_million=[str(value * 1000 - half), str(value * 1000 + half)])
    return result


def load_sources(index_path):
    index_raw = index_path.read_bytes()
    sources, texts, raw_hashes = {}, {}, {}
    for row in json.loads(index_raw)['sources']:
        id = row['source_id']
        if id in sources:
            raise ValueError('pair_duplicate_source')
        parsed = urlsplit(row['url'])
        if parsed.scheme != 'https' or parsed.hostname != 'ir.amd.com' or parsed.username or parsed.password:
            raise ValueError('pair_official_source_required')
        if row['status'] != 200:
            continue
        path = Path(row['path']); raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('pair_source_changed:' + id)
        html = raw.decode('utf-8'); text = plain(html)
        sources[id] = {'source_id': id, 'url': row['url'], 'sha256': row['sha256'],
                       'retrieved_at': row['retrieved_at'], 'published_at': publication(html),
                       'retained': row['retained'], 'plain_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                       'historical_immutability': 'NOT_PROVEN_CURRENT_HTML'}
        texts[id] = text; raw_hashes[str(path)] = row['sha256']
    return sources, texts, raw_hashes


def validate_result(result):
    if result.get('pairing_hash') != digest({k: v for k, v in result.items() if k != 'pairing_hash'}):
        raise ValueError('pair_result_identity_changed')
    if [e['fiscal_quarter'] for e in result['events']] != COHORT:
        raise ValueError('pair_fixed_cohort_required')
    if result['decision']['economic_execution_allowed'] is not False:
        raise ValueError('pair_diagnostic_only')
    for event in result['events']:
        if event['economic_execution_allowed'] is not False:
            raise ValueError('pair_diagnostic_only')
        if interval_comparison(event['actual'], event['latest_prior_disclosure']) != event['comparison']:
            raise ValueError('pair_comparison_inconsistent')
        if event['latest_prior_disclosure'] is not None and utc(event['latest_prior_disclosure']['public_at']) >= utc(event['actual']['public_at']):
            raise ValueError('pair_prior_disclosure_not_prior')
    counts=Counter(e['comparison']['status'] for e in result['events'])
    expected={'events':10,'dimension_matched':counts['ABOVE']+counts['BELOW']+counts['UNCERTAIN_PRECISION'],
              'numerically_above':counts['ABOVE'],'numerically_below':counts['BELOW'],
              'precision_uncertain':counts['UNCERTAIN_PRECISION'],'not_comparable':counts['NOT_COMPARABLE'],
              'missing_prior':counts['MISSING_PRIOR']}
    if any(result['counts'].get(k)!=v for k,v in expected.items()):
        raise ValueError('pair_counts_inconsistent')
    return result


def build(index_path, candidate_path, approval_path, path_result_path):
    sources, texts, before = load_sources(index_path)
    packet_raw, approval_raw, path_raw = candidate_path.read_bytes(), approval_path.read_bytes(), path_result_path.read_bytes()
    packet, approval, paths = json.loads(packet_raw), json.loads(approval_raw), json.loads(path_raw)
    approved = validate_approval(packet, approval)
    if [row['fiscal_quarter'] for row in packet['events']] != COHORT or len(approved) != 10:
        raise ValueError('pair_original_approved_cohort_required')
    if paths['diagnosis_hash'] != digest({k:v for k,v in paths.items() if k!='diagnosis_hash'}):
        raise ValueError('pair_old_path_identity_changed')
    old_paths = {row['fiscal_quarter']: row for row in paths['events']}
    if sorted(old_paths) != sorted(COHORT):
        raise ValueError('pair_old_path_cohort_mismatch')
    events = []
    for i, quarter in enumerate(COHORT):
        original = packet['events'][i]
        source, text = sources[quarter], texts[quarter]
        if source['sha256'] != original['raw_sha256'] or source['published_at'] != original['first_public_at']:
            raise ValueError('pair_approved_source_or_clock_changed')
        actual = exact_actual(source, text, quarter)
        prev_id = COHORT[i-1] if i else '2021Q4'
        status = 'REUSED_APPROVED_FIELD' if i else 'ADDITIONAL_REVIEW_REQUIRED'
        guidance = extract_guidance(sources[prev_id], texts[prev_id], quarter, status) if prev_id in sources else None
        if i:
            previous = {f['name']:f for f in packet['events'][i-1]['facts']}
            for name, value in [('next_revenue_guidance_midpoint', guidance['value_million']),
                                ('next_revenue_guidance_half_range', guidance['business_half_range_million'])]:
                old = previous[name]
                if decimal(old['value']) * decimal(old['scale']) / 1000000 != decimal(value) or old['fiscal_period'] != quarter:
                    raise ValueError('pair_existing_guidance_changed')
            guidance['original_candidate_hash'] = packet['events'][i-1]['candidate_hash']
        latest = dict(guidance) if guidance else None
        chain = [{'source_id': prev_id, 'kind': 'COMPANY_GUIDANCE', 'public_at': guidance['public_at']}] if guidance else []
        notes = []
        extra_evidence = []
        early = 'NOT_FOUND_IN_BOUNDED_FINANCIAL_ARCHIVE'
        if quarter == '2022Q1' and guidance:
            guidance['coverage'] = latest['coverage'] = 'AMD_EXCLUDING_XILINX'
            quote = 'Guidance does not contemplate the addition of Xilinx'
            extra_evidence.append(evidence(sources['2021Q4-slides'], texts['2021Q4-slides'], quote, 'Financial Outlook slide 20'))
            quote = 'results include partial quarter financial results from'
            extra_evidence.append(evidence(source, text, quote, 'Opening acquisition scope note'))
            notes.append('前序指引排除 Xilinx，正式 GAAP 总营收包含 Xilinx；直接比较口径不一致。原文另有剔除 Xilinx 的补充表，但本轮不替换已定义的总营收口径。')
        if quarter == '2022Q3':
            prelim_id = '2022Q3-preliminary'; ps, pt = sources[prelim_id], texts[prelim_id]
            quote = 'Third quarter revenue is expected to be approximately $5.6 billion'
            latest = fact('5600', '100', quarter, ps, pt, quote, 'Preliminary selected financial results; total revenue')
            latest.update(kind='PRELIMINARY_RESULTS', business_half_range_million=None, business_range_million=None)
            # The original range belongs to the old guidance, never to the preliminary number.
            chain.append({'source_id': prelim_id, 'kind': 'PRELIMINARY_RESULTS', 'public_at': latest['public_at']})
            early = 'PRELIMINARY_RESULTS_BEFORE_FORMAL_RELEASE'
            notes.append('10 月 6 日已公布约 56 亿美元；11 月 1 日正式结果不能再把此前下修当成新的信息。初步结果不是原经营指引范围。')
        chain.append({'source_id': quarter, 'kind': 'FORMAL_RESULTS', 'public_at': actual['public_at']})
        if any(utc(a['public_at']) >= utc(b['public_at']) for a,b in zip(chain, chain[1:])):
            raise ValueError('pair_disclosure_chain_not_chronological')
        price = old_paths[quarter]
        if price['candidate_hash'] != original['candidate_hash']:
            raise ValueError('pair_old_price_candidate_mismatch')
        if guidance is None:
            notes.append('缺少可核验的前序指引原件，事件继续保留；不以另一财季或零替代。')
        event = {'event_id': original['event_id'], 'fiscal_quarter': quarter,
                 'actual': actual, 'approved_headline_actual': next(f for f in original['facts'] if f['name']=='actual_revenue'),
                 'original_candidate_hash': original['candidate_hash'],
                 'original_guidance': guidance, 'latest_prior_disclosure': latest,
                 'comparison': interval_comparison(actual, latest),
                 'comparison_to_original_guidance': interval_comparison(actual, guidance),
                 'disclosure_chain': chain, 'information_state': early,
                 'revision_chain_status': 'LATEST_IN_REVIEWED_OFFICIAL_FINANCIAL_ARCHIVE_ONLY',
                 'complete_historical_chain_proven': False,
                 'source_chain_gap': '财务新闻分类归档与已留存原件覆盖，未证明所有电话会、其他分类披露或历史页面版本均已纳入。',
                 'extra_evidence': extra_evidence, 'notes': notes,
                 'old_price_status': price['status'], 'old_price_condition': price.get('price_condition'),
                 'old_legal_entry_at': next((c['C_path']['entry_at'] for c in price['cost_cases'] if c['C_path']['status']=='RECORDED_ENTRY'), None),
                 'new_content_intervention': None, 'economic_execution_allowed': False,
                 'research_gate': 'HOLD_ADDITIONAL_FIELDS_AND_SOURCE_CHAIN_REVIEW'}
        events.append(event)
    after_changed = [p for p,h in before.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    for path, raw in [(candidate_path,packet_raw),(approval_path,approval_raw),(path_result_path,path_raw)]:
        if path.read_bytes()!=raw:after_changed.append(str(path))
    if after_changed:raise ValueError('pair_input_changed_during_read')
    counts = Counter(row['comparison']['status'] for row in events)
    result = {'schema_version':'same-quarter-guidance-pairs-v1', 'created_at':datetime.now(timezone.utc).isoformat(),
              'purpose':'SEEN_DEVELOPMENT_SOURCE_PAIRING_NOT_NEW_ECONOMIC_STUDY',
              'source_catalog': list(sources.values()),
              'inputs':{'original_packet_hash':packet['packet_hash'],
                        'original_approval_sha256':hashlib.sha256(approval_raw).hexdigest(),
                        'original_path_diagnosis_hash':paths['diagnosis_hash']},
              'precision_policy':{'unit':'MILLION_USD','method':'HALF_LAST_DISPLAYED_UNIT_CONSERVATIVE_RECONSTRUCTION',
                                  'actual_table_quantum':'1','guidance_midpoint_quantum':'100',
                                  'zero_touch_or_cross':'UNCERTAIN','business_range_used_as_rounding_error':False,
                                  'meaning':'列示精度的保守重建假设；不是统计置信区间，亦非公司经营指引区间。'},
              'source_scope':{'financial_archive_ids':['financial-archive-2','financial-archive-3'],
                              'additional_scope_documents':['2021Q4-slides','2022Q1-slides','2022-analyst-day'],
                              'historical_originals_unchanged':True,'complete_historical_chain_proven':False},
              'counts':{'events':10,'dimension_matched':counts['ABOVE']+counts['BELOW']+counts['UNCERTAIN_PRECISION'],
                        'numerically_above':counts['ABOVE'],'numerically_below':counts['BELOW'],
                        'precision_uncertain':counts['UNCERTAIN_PRECISION'],'not_comparable':counts['NOT_COMPARABLE'],
                        'missing_prior':counts['MISSING_PRIOR'],
                        'early_disclosure':sum(e['information_state']=='PRELIMINARY_RESULTS_BEFORE_FORMAL_RELEASE' for e in events),
                        'retained_price_accepted':sum(e['old_price_status']!='DATA_EXCLUDED' for e in events),
                        'retained_price_signals':sum(e['old_price_condition'] is True for e in events),
                        'new_content_interventions':None,'new_backtest_reports':0,'new_independent_events':0,
                        'additional_human_approved_fields':0},
              'decision':{'status':'DO_NOT_START_NEW_FIXED_STUDY_YET',
                          'meaning':'同财季比较有明确含义，配对表可用；新增精确值与修订链尚未核准，不启动新内容研究。',
                          'blockers':['ADDITIONAL_FIELD_REVIEW_REQUIRED','COMPLETE_PRIOR_DISCLOSURE_CHAIN_NOT_PROVEN'],
                          'old_sample_role':'ALREADY_SEEN_DEVELOPMENT_ONLY',
                          'economic_execution_allowed':False,'account_allowed':False,'monitor_start_allowed':False},
              'events':events}
    result['pairing_hash']=digest(result)
    return validate_result(result)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('source-index','candidates','approval','path-result','output'):
        parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args()
    result=build(args.source_index,args.candidates,args.approval,args.path_result)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'pairing_hash':result['pairing_hash'],'counts':result['counts']}))
