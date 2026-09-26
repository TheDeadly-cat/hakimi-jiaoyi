"""Small static additions to the existing event cards; no separate GUI."""
from html import escape
from tools.equity_guidance_pairs import validate_result

LABELS = {'ABOVE':'精度区间仍高于中点', 'BELOW':'精度区间仍低于中点', 'MISSING_PRIOR':'前序指引缺失',
          'UNCERTAIN_PRECISION':'精度区间跨过或触及零', 'NOT_COMPARABLE':'口径不一致，不能直接比较'}
KINDS = {'COMPANY_GUIDANCE':'公司指引','PRELIMINARY_RESULTS':'初步业绩','FORMAL_RESULTS':'正式财报'}


def summary(data):
    validate_result(data)
    c=data['counts']
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


def section(event, sources, source_link, clock_text):
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
           '<div class="table-wrap"><table><thead><tr><th>字段</th><th>百万美元</th><th>口径／范围</th><th>公开时间（UTC）</th><th>原文</th></tr></thead><tbody>']
    for label,value,basis,f in rows:
        source=sources[f['evidence']['source_id']]
        basis += '；排除 Xilinx' if f['coverage']=='AMD_EXCLUDING_XILINX' else '；公司合并收入'
        approval='沿用已核准字段' if f['approval_status']=='REUSED_APPROVED_FIELD' else '新增字段待核准'
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
    parts += ['<p class="note">完整历史版本链未证实；新增字段未核准。本卡仅展示事实配对，不触发新策略。</p>',
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
