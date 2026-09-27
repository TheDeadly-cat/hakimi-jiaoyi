"""Small static additions to the existing event cards; no separate GUI."""
from html import escape
from tools.equity_guidance_pairs import validate_result
from tools.equity_content_protocol import digest

LABELS = {'ABOVE':'精度区间仍高于中点', 'BELOW':'精度区间仍低于中点', 'MISSING_PRIOR':'前序指引缺失',
          'UNCERTAIN_PRECISION':'精度区间跨过或触及零', 'NOT_COMPARABLE':'口径不一致，不能直接比较'}
KINDS = {'COMPANY_GUIDANCE':'公司指引','PRELIMINARY_RESULTS':'初步业绩','FORMAL_RESULTS':'正式财报'}


def validate_review(review, pairs, paths):
    """Bind a conditional review to its unchanged inputs, never grant admission."""
    def require(ok, name):
        if not ok:raise ValueError('card_review_'+name)
    require(review.get('schema_version')=='guidance-bounded-review-v1','schema')
    require(review.get('review_hash')==digest({k:v for k,v in review.items() if k!='review_hash'}),'hash')
    require(review['pairing_hash']==pairs['pairing_hash'] and review['path_diagnosis_hash']==paths['diagnosis_hash'],'input_identity')
    require(review['source_catalog']==pairs['source_catalog'],'source_identity')
    require(review['review_kind']=='AGENT_SOURCE_REVIEW_NOT_HUMAN_ATTESTATION','review_kind')
    require(review['bounded_scope']['complete_historical_chain_proven'] is False,'scope')
    require(review['decision']['economic_execution_allowed'] is False,'admission')
    items=review['review_items'];refs={s['source_id']:s['sha256'] for s in pairs['source_catalog']}
    require(len({i['field_id'] for i in items})==len(items),'duplicate_items')
    for item in items:
        require(item['review_status']=='CONDITIONAL_DEVELOPMENT_USE' and item['human_approval_status']=='NOT_APPROVED','item_status')
        require(all(refs.get(r['source_id'])==r['source_sha256'] for r in item['evidence']),'field_source')
    require([e['fiscal_quarter'] for e in review['events']]==[e['fiscal_quarter'] for e in pairs['events']],'cohort')
    candidates=[];accepted=0;comparable_accepted=0;signals=0
    for row,pair,path in zip(review['events'],pairs['events'],paths['events']):
        require(row['fiscal_quarter']==path['fiscal_quarter'],'path_cohort')
        require(row['review_status']=='CONDITIONAL_DEVELOPMENT_USE' and row['human_approval_status']=='NOT_APPROVED','event_status')
        require(row['interval_start_inclusive']==pair['original_guidance']['public_at'] and row['interval_end_inclusive']==pair['actual']['public_at'],'interval')
        require(row['known_material_omission'] is False and row['known_material_source_ids']==[v['source_id'] for v in pair['disclosure_chain']],'material_disclosure')
        require(row['old_price_status']==pair['old_price_status']==path['status'] and row['old_price_condition'] is pair['old_price_condition'] is path['price_condition'],'price_binding')
        require(row['comparison_status']==pair['comparison']['status'],'comparison')
        candidate=path['price_condition'] is True and pair['comparison']['positive_condition'] is True
        require(row['numeric_candidate'] is candidate and row['admitted_for_new_study'] is False,'candidate_not_admission')
        if candidate:candidates.append(row['fiscal_quarter'])
        accepted+=path['status']!='DATA_EXCLUDED'
        comparable_accepted+=path['status']!='DATA_EXCLUDED' and pair['comparison']['status']!='NOT_COMPARABLE'
        signals+=path['price_condition'] is True
    expected=dict(fixed_events=len(pairs['events']),comparable_events=pairs['counts']['dimension_matched'],
        conditional_review_items=len(items),new_human_approved_items=0,events_with_all_new_fields_human_approved=0,
        original_price_accepted=accepted,comparable_price_accepted=comparable_accepted,original_price_signals=signals,
        numeric_candidates=candidates,admitted_for_new_study=0,new_content_interventions=None,new_independent_events=0,new_backtest_reports=0)
    require(review['funnel']==expected,'funnel')


def summary(data, review=None):
    validate_result(data)
    c=data['counts']
    if review is not None:
        f=review['funnel']
        return (f'<div class="summary guidance-summary"><p>固定 {f["fixed_events"]} 个历史事件，{f["comparable_events"]} 个口径可比。'
                f'新增 {f["conditional_review_items"]} 个审阅项已完成原件核查，可有条件用于历史开发；新增人工核准为 0。</p>'
                f'<p>原行情接纳 {f["original_price_accepted"]} 个，其中口径也可比的有 {f["comparable_price_accepted"]} 个；'
                f'原价格信号 {f["original_price_signals"]} 个，叠加本次数值条件仅余 <b>{len(f["numeric_candidates"])} 个数值候选：'
                f'{escape("、".join(f["numeric_candidates"]) or "无")}</b>。获准参与新研究的为 0。</p>'
                '<p><b>本批开发诊断结案，不启动新收益研究。</b>单个已见候选不足以支持扩展研究；'
                '新内容干预：未运行，不能记为零次或零收益。</p></div>'
                '<p class="note">独立审计已从原 HTML 核对实际营收、指引和初步值。有限披露核查已结束并保留缺口；'
                '它不证明完整历史链，也不等于人工核准。数值高于公司在先披露，不是高于分析师预期。</p>'
                '<p class="note">单位为百万美元。实际值 ±0.5、在先数值 ±50 是保守列示精度假设，'
                '不是公司经营范围或统计置信区间。</p>'
                '<p><a href="guidance-review.json">查看新增字段结论、来源范围与筛选明细</a> · '
                '<a href="guidance-pairs.json">查看原配对数据</a></p>')
    return (f'<div class="summary guidance-summary"><p>十个历史事件全部保留。按所查原件，{c["dimension_matched"]} 个期间与口径匹配，'
            f'{c["not_comparable"]} 个口径不同；保守处理列示精度后，{c["numerically_above"]} 个高于最后已知数值，'
            f'{c["precision_uncertain"]} 个方向不确定。{c["early_disclosure"]} 个存在提前公布的初步业绩。</p>'
            '<p><b>结论：目前先完成事实配对，不启动新回测。</b>新增精确字段尚待核准，完整历史修订链也未证实。'
            '数值高于中点不等于存在新的可交易信息。</p></div>'
            '<p class="note">单位统一为百万美元。正式营收列示至 1 百万美元，指引或初步数值列示至 100 百万美元；'
            '本表保守采用各自末位单位的一半作精度边界。这不是公司指引范围或统计置信区间。</p>'
            f'<p class="note">覆盖 {c["events"]} 个事件 · 口径匹配 {c["dimension_matched"]} 个 · 原价格信号 '
            f'{c["retained_price_signals"]} 个 · 新内容干预：未运行 · 新独立样本：0。'
            '<a href="guidance-pairs.json">下载本次配对数据与逐字段依据</a></p>')


def section(event, sources, source_link, clock_text, review=None, approval_label=None, review_note=None,
            clock_heading='公开时间（UTC）', coverage_label=None):
    a, g, latest = event['actual'], event['original_guidance'], event['latest_prior_disclosure']
    result=event['comparison']
    latest_name=KINDS[latest['kind']] if latest else '缺失，未计算'
    rows=[('正式财报实际营收',a['value_million'],'财务表，百万美元',a)]
    if g:
        business=' 至 '.join(g['business_range_million'])
        rows.append(('原公司指引中点',g['value_million'],f'经营范围 {business}',g))
    if latest and latest['kind']=='PRELIMINARY_RESULTS':
        rows.append(('此前最后已知数值',latest['value_million'],'初步业绩，无新经营范围',latest))
    parts=['<section class="guidance-pair"><h3>同财季事实配对</h3>',
           f'<p><b>{escape(LABELS[result["status"]])}</b>；比较基准：{escape(latest_name)}。</p>',
           f'<div class="table-wrap"><table><thead><tr><th>字段</th><th>百万美元</th><th>口径／范围</th><th>{escape(clock_heading)}</th><th>原文</th></tr></thead><tbody>']
    for label,value,basis,f in rows:
        source=sources[f['evidence']['source_id']]
        basis += coverage_label(f) if coverage_label is not None else '；排除 Xilinx' if f['coverage']=='AMD_EXCLUDING_XILINX' else '；公司合并收入'
        approval='沿用已核准字段' if f['approval_status']=='REUSED_APPROVED_FIELD' else '新增字段待核准'
        if review is not None and f['approval_status']!='REUSED_APPROVED_FIELD':
            approval='有条件用于历史开发；未获人工核准'
        if approval_label is not None:approval=approval_label(f)
        parts.append(f'<tr><td>{escape(label)}<br><small>{approval}</small></td><td class="numeric">{escape(value)}</td>'
                     f'<td>{escape(basis)}</td><td>{escape(clock_text(f["public_at"]))}</td><td>{source_link(source["url"])}</td></tr>')
    parts.append('</tbody></table></div>')
    if result['difference_interval_million'] is not None:
        lo,hi=result['difference_interval_million']
        parts.append(f'<p>名义差额：{escape(result["nominal_difference_million"])} 百万美元；精度差额区间 '
                     f'{escape(lo)} 至 {escape(hi)} 百万美元。此处比较中点，未改为比较指引上界。</p>')
    for note in event['notes']:
        parts.append(f'<p class="warning">{escape(note)}</p>')
    if event['information_state']=='NOT_FOUND_IN_BOUNDED_FINANCIAL_ARCHIVE':
        parts.append('<p class="note">所查财务新闻归档内未发现另一次初步业绩；这不证明从未通过其他渠道提前披露。</p>')
    if review is not None:
        candidate='仅数值候选，未获准参与新研究' if review['numeric_candidate'] else '不进入数值候选交集'
        parts.append(f'<p><b>审核结论：有条件用于历史开发；{candidate}。</b></p>'
                     f'<p class="note">有限核查区间：{escape(clock_text(review["interval_start_inclusive"]))} 至 '
                     f'{escape(clock_text(review["interval_end_inclusive"]))}。已知重大披露已纳入；'
                     '排期公告只查标题，电话会、其他类别和历史修订等仍有缺口。新增字段未获人工核准。</p>')
    parts += [(f'<p class="note">{escape(review_note)}</p>' if review_note is not None else '<p class="note">完整历史版本链未证实。本卡仅展示事实配对，不触发新策略。</p>' if review is not None else '<p class="note">完整历史版本链未证实；新增字段未核准。本卡仅展示事实配对，不触发新策略。</p>'),
              '<details><summary>查看版本时间线与配对依据</summary>']
    for version in event['disclosure_chain']:
        source=sources[version['source_id']]
        parts.append(f'<p>{escape(clock_text(version["public_at"]))} · {KINDS[version["kind"]]} · {source_link(source["url"])}</p>')
    parts.append(f'<p>{escape(event["source_chain_gap"])}</p>')
    refs=[a['evidence']]+([g['evidence']] if g else [])+([latest['evidence']] if latest and latest['kind']=='PRELIMINARY_RESULTS' else [])+event['extra_evidence']
    for ref in refs:
        source=sources[ref['source_id']]
        parts.append(f'<p>{source_link(source["url"])}：<q>{escape(ref["quote"])}</q><br>'
                     f'<small>{escape(ref["locator"])}；实际取回 {escape(source["retrieved_at"])}；'
                     f'公开时间以页面标记为准，当前网页历史不变性未证明。</small></p>')
    parts.append('</details></section>')
    return '\n'.join(parts)
