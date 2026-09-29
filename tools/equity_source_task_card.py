"""Reuse the existing static card style and fact section for a new source task."""
from copy import deepcopy
from html import escape
from urllib.parse import urlsplit
from tools.equity_research_card import CARD_STYLE
from tools.equity_guidance_card import section

ISSUES={
    'PUBLICATION_TIME_UNKNOWN_DATE_ONLY':'页面只提供公开日期，无法确定精确时刻。',
    'CURRENT_HTML_HISTORICAL_IMMUTABILITY_NOT_PROVEN':'当前网页的历史版本不变性尚未证明。',
    'COVERAGE_IS_DECLARED_REQUIRES_SEMANTIC_REVIEW':'收入口径来自清单声明，仍需语义复核。',
    'KNOWN_MATERIAL_SOURCE_NOT_SELECTED':'已知的重大披露没有全部纳入本次比较。',
    'PRIOR_DISCLOSURE_REQUIRED':'缺少可比较的在先披露。',
    'COVERAGE_NOT_DECLARED':'未声明收入口径，暂不能比较。',
    'LATEST_PRIOR_NOT_UNIQUELY_DETERMINED':'原件数值核对通过，但无法唯一确定最新在先披露；不能判断高于或低于，也不计入数值候选交集。',
}
STOPS={'MISSING_KNOWN_DISCLOSURE':'已知重大披露缺失','MISSING_SOURCE':'原件未具备','MISSING_PRIOR':'在先披露缺失',
       'UNKNOWN_COVERAGE':'收入口径未知','SOURCE_REJECTED':'原件格式、期间或数值核对未通过',
       'AMBIGUOUS_PRIOR_ORDER':'最新在先披露顺序未知'}


def coverage(field):
    labels={'CONSOLIDATED_REPORTED':'公司合并收入','AMD_CONSOLIDATED_REPORTED':'公司合并收入','AMD_EXCLUDING_XILINX':'排除 Xilinx'}
    return '；清单口径：'+labels.get(field['coverage'],field['coverage'] or '未知')+'（待语义复核）'


def source_link(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ('nvidianews.nvidia.com','investor.nvidia.com','ir.amd.com') or parsed.username or parsed.password:
        raise ValueError('source_task_card_official_url_required')
    return f'<a href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">公司公告原文</a>'


def clock(value):
    if not value:return '精确时刻未知'
    if len(value)==10:return value+'（仅日期，时刻未知）'
    return value.replace('T',' ').replace('Z',' UTC')


def render(packet,result):
    security=packet['definition']['security'];counts=result['counts'];approved=set(result['human_approved_event_ids'])
    sources={s['source_id']:s for s in packet['sources']}
    synthetic=packet['definition']['evidence_kind']=='SYNTHETIC_FIXTURE'
    link=(lambda _url:'虚构格式夹具，无真实原文链接') if synthetic else source_link
    display=lambda n:'未计算／资料未具备' if n is None else str(n)
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>股票公告研究｜来源与可比性</title><style>'+CARD_STYLE+'table{min-width:680px}</style><main><header>',
        '<small>哈基米 · 离线股票事件研究 / 固定来源任务</small>',
        f'<h1>{escape(security["symbol"])}：同财季资料能否比较？</h1>',
        '<p class="warning">虚构资料示例：数字、网页和声明仅用于工程测试，不是真实来源验收。</p>' if synthetic else '<p class="note">当前官方网页留存资料；历史版本真实性未认证。</p>',
        '<div class="summary"><p>本页核对已导入资料与公司在先披露，不代表分析师预期、交易建议或实时监控。</p>',
        f'<p>事件 {counts["events"]} · 按清单口径可比 {counts["comparable_sources"]} · 本次人工核准事件 {counts["human_approved_events"]} · '
        f'数值高于 {counts["numeric_above"]}。</p><p>行情可用事件：{display(counts["market_available_events"])}；'
        f'价格信号：{display(counts["price_signals"])}；价格与数值交集：{display(counts["price_numeric_intersection"])}。</p>',
        '<p><b>本次止于来源流程验收，不运行收益回测。</b>内容干预：未运行；新研究接纳：0。'
        '机器核对、有限来源审查、人工核准、研究接纳和交易授权分别判断。</p></div>',
        f'<p>样本选择依据：{escape(packet["definition"]["selection"]["basis"])}</p>',
        '<p class="note">本批是已见工程资料，不因换了公司就成为独立验证集。金额为百万美元；末位半单位仅是保守精度假设。</p>',
        '<p><a href="../packet.json">字段、原件摘要与任务清单</a> · <a href="result.json">筛选结果</a></p></header>']
    for row in packet['events']:
        quarter=row['fiscal_quarter'];fiscal_label=quarter[:4]+' 财年第 '+quarter[-1]+' 季度'
        parts.extend([f'<article class="card"><h2>{escape(security["symbol"])} {fiscal_label}</h2>',
            f'<p>机器原件核对：{"通过" if row["source_audit"]=="PASS" else "未完成"}；人工核准：{"已导入本次字段核准声明" if row["event_id"] in approved else "未核准"}；研究接纳与交易授权：未开放。</p>'])
        if row['comparison'] is not None:
            a=deepcopy(row['actual']);g=deepcopy(row['latest_prior']);latest=deepcopy(row['latest_prior'])
            versions=deepcopy(row['prior_disclosures'])+[a]
            for field in [a,g,latest]+versions:field['public_at']=field['public_at'] or field['publication_date']
            event=dict(actual=a,original_guidance=g,latest_prior_disclosure=latest,comparison=row['comparison'],notes=[],
                information_state='BOUNDED_MANIFEST_ONLY',
                extra_evidence=[f['evidence'] for f in row['prior_disclosures'] if f['evidence']['source_id']!=latest['evidence']['source_id']],
                source_chain_gap='仅所列本地版本；清单展示顺序不代表时间顺序，完整历史链未证实。',
                disclosure_chain=[dict(source_id=f['evidence']['source_id'],kind=f['kind'],public_at=f['public_at']) for f in versions])
            label='本次来源字段已获人工核准' if row['event_id'] in approved else '机器核对通过；尚未人工核准'
            parts.append(section(event,sources,link,clock,approval_label=lambda _f:label,review_note='完整历史链未证实；字段核准不授予研究或交易权限。',
                clock_heading='页面公开日期／时间',coverage_label=coverage,guidance_label='本次比较采用的最新在先指引中点',
                timeline_heading='查看已选披露与配对依据'))
        else:
            parts.append(f'<p class="warning">停止该事件的比较：{escape(STOPS.get(row["status"],"资料尚未具备"))}。资料不足不填成零。</p>')
            if row['source_audit']=='PASS':
                parts.append('<div class="table-wrap"><table><thead><tr><th>已核对来源（不表示先后）</th><th>百万美元</th><th>页面公开日期／时间</th><th>原文</th></tr></thead><tbody>')
                for field in [row['actual']]+row['prior_disclosures']:
                    sid=field['evidence']['source_id']
                    parts.append(f'<tr><td>{escape(sid)}</td><td class="numeric">{escape(field["value_million"])}</td>'
                        f'<td>{escape(clock(field["public_at"] or field["publication_date"]))}</td><td>{link(sources[sid]["url"])}</td></tr>')
                parts.append('</tbody></table></div>')
        parts.append(f'<p class="note">披露核查窗口：{escape(clock(row["window_start"]))} 至 {escape(clock(row["window_end"]))}。</p>')
        if row['actual']:
            source=sources[row['actual']['evidence']['source_id']]
            parts.append(f'<p class="note">页面公开：{escape(clock(row["actual"]["public_at"] or row["actual"]["publication_date"]))}；'
                f'实际采集：{escape(clock(source["retrieved_at"]))}；提取完成：{escape(clock(packet["extraction_completed_at"]))}；'
                f'模型可用时间：{escape(clock(row["model_available_at"])) if row["model_available_at"] else "未接纳"}。历史假设与实际接收时间不互换。</p>')
        for issue in row['issues']:
            if issue in ISSUES:parts.append(f'<p class="note">{escape(ISSUES[issue])}</p>')
            else:parts.append(f'<details><summary>查看停止原因的核对代码</summary><code>{escape(issue)}</code></details>')
        parts.append('</article>')
    scope=packet['definition']['source_scope']
    parts.extend(['<footer><p>有限来源范围：'+escape(scope['description'])+'</p>',
        '<p>仍未覆盖：'+escape('；'.join(scope['uncovered_channels']))+'。当前网页未被认证为历史不可变版本。</p>',
        '<p>这是开发分支中的离线流程报告；正式 v0.2.1、r3 预览包与实际部署分别保留。账户、订单、T3、Unknown 排查和新监控继续暂停。</p>',
        f'<p>任务版本 {packet["version"]} · 数据身份 <code>{packet["packet_hash"]}</code><br>报告身份 <code>{result["report_hash"]}</code></p></footer></main></html>'])
    return '\n'.join(parts)
