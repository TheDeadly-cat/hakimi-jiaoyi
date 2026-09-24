"""Render a static read-only research supplement beside an unchanged r3 preview."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
from html import escape
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.equity_content_protocol import digest
from tools.supervised_preview import verify_bundle

STATUS = {"DATA_EXCLUDED": "资料不足 · 原排除保留", "NO_PRICE_SIGNAL": "没有价格信号",
          "CONTENT_VETO": "内容条件否决", "ENTERED_STOPPED": "入场后止损", "ENTERED_MARKED": "入场后按市值记录"}
NAMES = {"actual_revenue": "当季营收（公告首段）", "diluted_eps": "GAAP 每股收益",
         "non_gaap_diluted_eps": "非 GAAP 每股收益", "next_revenue_guidance_midpoint": "下一财季营收指引中点",
         "next_revenue_guidance_half_range": "下一财季指引半范围"}


def pct(value):
    if value is None:
        return "未计算"
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("card_nonfinite_metric")
    return f"{number * 100:+.4f}%" if number else "0%"


def fact_value(fact):
    value = Decimal(fact["value"]) * Decimal(fact["scale"])
    return f"{value / Decimal(1000000000):f} 十亿美元" if fact["unit"] == "CURRENCY" else f"{value:f} 美元/股"


def clock_text(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).strftime('%Y-%m-%d %H:%M UTC')


def source_link(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "ir.amd.com" or parsed.username or parsed.password:
        raise ValueError("card_official_announcement_url_required")
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">AMD 公告原文</a>'


def render(result, preview):
    if result["diagnosis_hash"] != digest({k: v for k, v in result.items() if k != "diagnosis_hash"}):
        raise ValueError("card_diagnosis_identity_changed")
    counts = Counter(e["status"] for e in result["events"])
    if sum(counts.values()) != 10:
        raise ValueError("card_fixed_coverage_required")
    normal = [c for e in result['events'] for c in e['cost_cases']
              if c['cost_multiplier']==1 and c['C_path']['status']=='RECORDED_ENTRY']
    endpoints = [h['values'] for c in normal for h in c['C_path']['horizons']]
    complete = bool(normal) and len(endpoints)==3*len(normal) and all(v is not None for v in endpoints)
    all_down = complete and all(Decimal(v['close_price_change']) < 0 for v in endpoints)
    stop_better = complete and all(Decimal(h['values']['retained_entry_mark_return']) < Decimal(str(c['C_return']))
                                  for c in normal for h in c['C_path']['horizons'])
    headline = (f'入场后第 1、3、5 日，{len(normal)} 个事件的收盘价都低于入场参考价' if all_down
                else 'AMD 公告后的信号、退出与固定后续路径')
    finding = ('各固定终点的价格变化均为负。' if all_down else '各固定终点逐项列示，缺失保持未计算。')
    if stop_better:
        finding += '原止损损失小于这些终点的留仓市值估算损失，本批没有支持“仅因止损太紧而错失后续收盘回升”的证据。'
    else:
        finding += '请分别比较原退出路径与终点估值；后者不代表可执行的另一策略。'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>AMD 事件研究｜信号、退出与后续路径</title><style>',
        'body{margin:0;background:#f4f5f3;color:#182725;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1100px;margin:auto;padding:44px 24px 64px}h1{font-size:30px;line-height:1.35;margin:12px 0 20px}h2{font-size:23px;margin:0}h3{font-size:17px;margin-top:24px}p{max-width:88ch}a{color:#16675c}small,.muted{color:#586b66}header{margin-bottom:28px}.summary{padding:22px 26px;background:#e5eee9;border-left:4px solid #438571}.counts{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}.counts span{padding:8px 14px;border:1px solid #c9d6cf;border-radius:5px;background:white}.card{padding:25px 28px;margin:22px 0;background:white;border:1px solid #d7dfd9;border-radius:9px}.card-head{display:flex;align-items:center;justify-content:space-between;gap:18px}.badge{font-size:14px;color:#56665f;background:#eef1ed;padding:4px 12px;border-radius:14px}.timeline{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:15px 0}.timeline div{border-top:2px solid #d0ded6;padding-top:9px;font-size:14px}.timeline b{display:block}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th{text-align:left;background:#eef3f0;white-space:nowrap}td,th{padding:10px 12px;border-bottom:1px solid #e2e8e3}td.numeric{white-space:nowrap}details{border-top:1px solid #e4e8e5;margin-top:20px;padding-top:12px}summary{cursor:pointer;color:#315e52;font-weight:600}code{overflow-wrap:anywhere;font-size:12px}.note{font-size:14px;color:#5c6e65}.warning{background:#fbf3e3;padding:12px 16px;border-radius:5px}footer{margin-top:30px;border-top:1px solid #c9d6cf;padding-top:20px;font-size:13px;color:#607068}@media(max-width:680px){main{padding:24px 14px}h1{font-size:25px}.card{padding:18px 16px}.card-head{align-items:flex-start;flex-direction:column;gap:8px}.timeline{grid-template-columns:1fr}td,th{padding:8px}.summary{padding:16px}}@media print{body{background:white}main{padding:0}.card{break-inside:avoid}details{display:block}summary{display:none}}',
        'table{min-width:680px}</style><main><header><small>哈基米 · 股票事件研究 / 固定开发诊断 · 2026-09-25</small>',
        f'<h1>{escape(headline)}</h1>',
        f'<div class="summary"><p>原十个 AMD 财报窗口中，{10-counts["DATA_EXCLUDED"]} 个可计算，{len(normal)} 个产生合法入场；内容否决 {counts["CONTENT_VETO"]} 个事件。{escape(finding)}</p><p>这是已见开发事件的路径解释，不是取消止损后的新回测，也不能证明信号普遍无效。{counts["DATA_EXCLUDED"]} 个存在行情分歧的事件仍排除。</p></div></header>',
        '<div class="counts">' + ''.join(f'<span>{escape(STATUS[k])}：<b>{counts[k]}</b></span>' for k in ("ENTERED_STOPPED", "NO_PRICE_SIGNAL", "CONTENT_VETO", "DATA_EXCLUDED")) + '</div>',
        '<p class="note">下列百分比含义分开：价格变化相对合法入场的常规开盘；市值估算使用原模拟入场后的数量和现金，包含入场成本但没有虚构出场费用。原策略回报是已有报告结果。入场日计为第 1 个交易日。窄屏可横向滚动表格查看完整列。</p>']
    for index, event in enumerate(result["events"]):
        event_id = f'event-{event["fiscal_quarter"]}'
        parts += [f'<article class="card" id="{escape(event_id)}" data-source-event="/events/{index}">',
            f'<div class="card-head"><h2>AMD {escape(event["fiscal_quarter"])}</h2><span class="badge">{escape(STATUS[event["status"]])}</span></div>',
            '<div class="timeline">', f'<div><b>公告公开（页面标记）</b>{escape(clock_text(event["first_public_at"]))}</div>',
            f'<div><b>模型信息可用</b>{escape(clock_text(event["model_event_available_at"]))}<br>公开后 120 秒假设</div>',
            f'<div><b>首个完整交易日确认</b>{escape(event.get("confirmation_session", "原行情未接纳"))}<br>{escape(clock_text(event["confirmation_available_at"]) if event.get("confirmation_available_at") else "未计算")}</div></div>']
        if event["status"] == "DATA_EXCLUDED":
            parts.append('<p class="warning">原日线与常规时段聚合存在差异，资料不足以按旧规约接纳。价格条件、入场与后续收益未计算；这不等于零收益。</p>')
        else:
            parts.append(f'<p>价格确认：<b>{"成立" if event["price_condition"] else "不成立"}</b>（公告前收盘至确认收盘 {pct(event["confirmation_close_change"])}）；内容条件：<b>{"成立" if event["content_condition"] else "不成立"}</b>。内容是否改变决定：<b>{"是" if event["content_changed_decision"] else "否"}</b>。</p>')
            parts.append('<p class="note">这段确认涨跌发生在策略合法入场之前，不能当作本系统可获得的入场后收益。</p>')
            if event["status"] == "NO_PRICE_SIGNAL":
                parts.append('<p>没有产生 C 的合法买入，D 也没有入场。保留覆盖记录，后续路径表不制造一笔假想交易。</p>')
            for case in event["cost_cases"]:
                path = case["C_path"]
                parts.append(f'<h3>{"正常成本" if case["cost_multiplier"] == 1 else "两倍成本"} · 费率 {pct(case["fee_rate"]).lstrip("+")} / 单边滑点 {pct(case["slippage_pct"]).lstrip("+")}</h3>')
                disabled = pct(case["C_return"]) if case["disabled_D_byte_identical_C"] else '未验证'
                parts.append(f'<p>C 原回报 <b>{pct(case["C_return"])}</b> · D 原回报 <b>{pct(case["D_return"])}</b> · 关闭内容条件后的 D：<b>{disabled}</b>（已有逐字节检查）</p>')
                if path["status"] != "RECORDED_ENTRY":
                    continue
                exit_name={'INTRABAR_STOP':'盘中止损','GAP_OPEN':'开盘跳空保护','OPEN_AT_END':'期末未平仓'}.get(path['exit_basis'],path['exit_basis'])
                parts.append(f'<p class="note">合法入场 {escape(clock_text(path["entry_at"]))}；退出日 {escape(path["exit_session"] or "未平仓")}，依据 {escape(exit_name)}。入场费 {Decimal(path["entry_fee"]):.4f} 美元、出场费 {Decimal(path["exit_fee"]):.4f} 美元（展示至四位小数）。日线不提供精确盘中时刻；零收盘敞口不代表盘中没有仓位。</p>')
                parts.append('<div class="table-wrap"><table><thead><tr><th>固定终点</th><th>入场后价格变化</th><th>保留入场仓位的市值估算</th><th>期间价格范围（低至高）</th></tr></thead><tbody>')
                for horizon in path["horizons"]:
                    values = horizon["values"]
                    if values is None:
                        parts.append(f'<tr><td>第 {horizon["sessions"]} 个交易日</td><td colspan="3">资料缺失或超出原评分窗口，不缩短期限</td></tr>'); continue
                    title = escape(json.dumps(horizon["source_rows"], ensure_ascii=False), quote=True)
                    parts.append(f'<tr data-source-rows="{title}"><td>第 {horizon["sessions"]} 日<br>{escape(horizon["close_session"])}</td><td class="numeric">{pct(values["close_price_change"])}</td><td class="numeric">{pct(values["retained_entry_mark_return"])}</td><td class="numeric">{pct(values["full_horizon_low_change"])} 至 {pct(values["full_horizon_high_change"])}</td></tr>')
                parts.append('</tbody></table></div><p class="note">最高／最低价先后未知，不能把最高价当成止损后可成交的机会。同日止损之后的剩余路径未知；严格退出后的范围仅统计之后完整交易日，详见数据文件。</p>')
        parts += ['<details><summary>查看已核准字段、精度与依据</summary>', f'<p>{source_link(event["source_url"])} · <a href="path-results.json">结果与逐项计算指针</a></p>',
            '<div class="table-wrap"><table><thead><tr><th>字段</th><th>数值</th><th>目标财季</th><th>口径／精度</th></tr></thead><tbody>']
        for fact in event["facts"]:
            precision = '首段四舍五入' if fact['precision']=='SOURCE_ROUNDED_HEADLINE_BILLION' else '保留原列示精度'
            basis={'GAAP':'GAAP','NON_GAAP':'非 GAAP','REVENUE_OUTLOOK':'公司营收指引'}.get(fact['basis'],fact['basis'])
            parts.append(f'<tr><td>{escape(NAMES[fact["name"]])}</td><td>{escape(fact_value(fact))}</td><td>{escape(fact["fiscal_period"])}</td><td>{escape(basis)} · {precision}</td></tr>')
        parts += ['</tbody></table></div>', f'<p class="note">实际取回：{escape(event["actual_retrieved_at"])}；提取完成：{escape(event["actual_extraction_completed_at"])}。字段于 2026 年核准，当前 HTML 的历史不可变性未证明。没有完整此前指引修订链或分析师一致预期。</p>',
            f'<p>候选字段摘要 <code>{escape(event["candidate_hash"])}</code></p>']
        for case in event['cost_cases']:
            parts.append(f'<p>{case["cost_multiplier"]} 倍成本报告：C <code>{escape(case["report_hashes"]["C"])}</code>；D <code>{escape(case["report_hashes"]["D"])}</code></p>')
        parts.append('</details></article>')
    parts += [f'<footer>本页是既有 r3 只读预览的独立静态补充。原预览版本 {escape(str(preview["version"]))}，构建 <code>{escape(preview["build_id"])}</code> 已核对，原包未修改。此补充不表示旧 wheel 已携带新工具；v0.2.1、旧 O1 和 T3 状态保持原边界。<p>本页不自动联网、连接账户、写入研究事实或启动监控。没有实时状态承诺。</p><p>诊断摘要 <code>{result["diagnosis_hash"]}</code><br>规约摘要 <code>{result["protocol_hash"]}</code></p></footer></main></html>']
    return '\n'.join(parts)


def build(result_path, preview_root, output):
    if output.resolve().is_relative_to(preview_root.resolve()):
        raise ValueError("card_output_must_not_modify_preview_bundle")
    preview = verify_bundle(preview_root)
    if preview['kind'] != 'research':
        raise ValueError('card_research_preview_required')
    raw = result_path.read_bytes(); result = json.loads(raw)
    html = render(result, preview)
    output.mkdir(parents=True, exist_ok=False)
    (output/'index.html').write_text(html,encoding='utf-8',newline='\n')
    (output/'path-results.json').write_bytes(raw)
    verify_bundle(preview_root)
    receipt = {'schema_version':'readonly-event-card-v1','diagnosis_hash':result['diagnosis_hash'],
        'html_sha256':hashlib.sha256((output/'index.html').read_bytes()).hexdigest(),
        'data_sha256':hashlib.sha256(raw).hexdigest(),'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'preview_build_id':preview['build_id'],'preview_integrity':'VERIFIED_BEFORE_AND_AFTER',
        'old_preview_replaced':False,'auto_network_requests':False,'order_allowed':False}
    (output/'render-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('result','preview-root','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.result,args.preview_root,args.output),indent=2))
