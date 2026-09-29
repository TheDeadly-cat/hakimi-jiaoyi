"""Offline, two-event diagnostic with a separate channel-clock witness.

Never backfill issuer public_at or call a channel timestamp the global first
publication. Reuse the fixed price predicate; no strategy, account or order API.
"""
from __future__ import annotations
import argparse
from datetime import timedelta
from html import escape
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from tools.collect_nvda_event_inputs import WINDOWS
from tools.equity_content_protocol import digest, price_confirmation, utc
from tools.equity_research_card import CARD_STYLE
from tools.equity_source_task import verify_packet, require, sha
from hakimi_research.equity_dataset import load_equity_snapshot, verify_equity_snapshot
from hakimi_research.equity_cli import _deny_network
from hakimi_research.reporting import _save_encoded_report

CLOCK = ROOT / 'docs/research-evidence/nvda-event-price-20260930/publication-clock.json'


def read(path):
    raw = Path(path).read_bytes()
    require(len(raw) <= 6 * 1024 * 1024, 'diagnostic_input_budget')
    return json.loads(raw)


def iso(value):
    return value.isoformat().replace('+00:00', 'Z')


def check_clock(row, event, witnesses):
    """Check the retained DOM clock and event binding, not historical truth."""
    require(row['event_id'] == event['event_id'] and row['fiscal_quarter'] == event['fiscal_quarter']
            and row['source_sha256'] == event['actual']['evidence']['source_sha256'], 'clock_event_binding')
    require(event['actual']['public_at'] is None and row['source_public_at'] is None
            and row['global_first_publication_at'] is None, 'original_unknown_clock_must_remain_unknown')
    for name, expected in row['witness_sha256'].items():
        require(Path(name).name == name and sha((witnesses / name).read_bytes()) == expected, 'clock_witness_changed')
    witness = read(witnesses / (row['fiscal_quarter'] + '-wire-browser.private.json'))
    require(witness['url'] == row['channel_url'] and witness['observed_at'] == row['observed_at']
            and witness['representation'] == row['representation'] == 'LIVE_BROWSER_RENDERED_DOM_NOT_HTTP_ORIGINAL'
            and row['expected_heading'] in [x.strip() for x in witness['headings']], 'clock_page_binding')
    require(len(witness['clocks']) == 1, 'ambiguous_channel_clock')
    clock = witness['clocks'][0]
    require(clock['datetime'] == row['channel_publication_at'] and clock['text'].strip() == row['displayed_minute']
            and clock['markup'] == row['dom_time_markup'], 'clock_dom_binding')
    stamp = utc(row['channel_publication_at']); local = stamp.astimezone(ZoneInfo('America/New_York'))
    visible = re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4}) (\d{2}:\d{2}) ET', row['displayed_minute'])
    require(visible is not None and visible.groups() == (local.strftime('%B'), str(local.day), str(local.year), local.strftime('%H:%M')),
            'visible_minute_and_datetime_disagree')
    require(local.date().isoformat() == event['actual']['publication_date'] == row['source_publication_date']
            and stamp <= utc(row['observed_at']), 'channel_clock_date_or_observation_mismatch')
    # Bind the wire's current fiscal-quarter revenue to the same issuer fact.
    content = witness.get('visible_text')
    if content is None:
        excerpt = read(witnesses / (row['fiscal_quarter'] + '-wire-excerpt.private.json'))
        require(excerpt['url'] == row['channel_url'], 'wire_excerpt_url_mismatch')
        content = excerpt['text']
    plain = ' '.join(content.split())
    marker = 'Q' + event['fiscal_quarter'][-1] + ' Fiscal 2024 Summary'
    require(marker in plain, 'wire_fiscal_summary_missing')
    table = plain.split(marker, 1)[1].split('Non-GAAP', 1)[0]
    revenue = re.search(r'\bRevenue\s+\$\s*([\d,]+)', table)
    require(revenue is not None and revenue[1].replace(',', '') == event['actual']['value_million'], 'wire_revenue_binding')
    return stamp


def diagnose(event, channel_at, snapshot):
    data = verify_equity_snapshot(snapshot.document)
    quarter, release_date, start, end = next(w for w in WINDOWS if w[0] == event['fiscal_quarter'])
    require(all(data['security'][k] == v for k, v in {'security_id': 'US:COMMON:NASDAQ:NVDA', 'symbol': 'NVDA', 'currency': 'USD'}.items()), 'snapshot_security_mismatch')
    sessions = data['sessions']
    require(data['research_admission']['allowed'] and data['price_basis'] == 'RAW_UNADJUSTED'
            and data['bar_availability_lag_seconds'] == 60 and len(sessions) == 8
            and sessions[0]['date'] == start and sessions[-1]['date'] == end
            and sessions[2]['date'] == release_date, 'frozen_snapshot_window_or_basis_changed')
    channel = utc(channel_at); available = channel + timedelta(seconds=120)
    require(utc(sessions[2]['close_utc']) < channel < utc(sessions[3]['open_utc']), 'channel_clock_not_in_fixed_after_close_window')
    targets = [s for s in sessions if utc(s['open_utc']) >= available]
    require(targets and targets[0]['date'] == sessions[3]['date'], 'first_full_session_missing')
    target = targets[0]; decision_at = iso(utc(target['close_utc']) + timedelta(seconds=60))
    bars = [dict(session=s['date'], close=str(c[4]), completed=True,
                 available_at=iso(utc(s['close_utc']) + timedelta(seconds=60))) for c, s in zip(data['candles'], sessions)]
    decision = price_confirmation(release_at=channel_at, decision_at=decision_at, sessions=sessions, bars=bars)
    return dict(event_id=event['event_id'], fiscal_quarter=quarter, snapshot_id=snapshot.snapshot_id,
                source_public_at=None, global_first_publication_at=None, channel_publication_at=channel_at,
                model_available_at=iso(available), model_time_kind='ASSUMED_120_SECONDS_AFTER_CHANNEL_TIMESTAMP',
                baseline_session=sessions[2]['date'], confirmation_session=target['date'], confirmation_at=decision_at,
                price_condition=decision['action'] == 'BUY', earliest_model_entry_at=decision['execution_at'],
                price_decision=decision, numeric_condition=event['comparison']['positive_condition'],
                numeric_status=event['status'], actual_revenue_million=event['actual']['value_million'],
                prior_guidance_midpoint_million=event['latest_prior']['value_million'],
                human_approved=False, economic_executed=False, order_allowed=False)


def prepare(packet_path, evidence_dir, lineage_path):
    packet = verify_packet(packet_path); clocks = read(CLOCK); lineage = read(lineage_path)
    require(clocks['schema_version'] == 'nvda-channel-clock-evidence-v1' and packet['packet_hash'] == clocks['source_packet_hash'], 'source_packet_binding')
    require(sha(Path(lineage_path).read_bytes()) == clocks['price_lineage_sha256'], 'price_lineage_changed')
    require(clocks['historical_diagnostic_policy'] == dict(reference='CHANNEL_PUBLICATION_KNOWN_PUBLIC_BY',
            collection_delay_seconds=60, processing_delay_seconds=60, price_rule='FIXED_C_PRICE_CONFIRMATION_V1',
            bar_lag_seconds=60, source_public_at_unchanged=True, economic_execution_allowed=False), 'frozen_channel_policy_changed')
    expected = {'2024Q1', '2024Q2'}
    for rows in (packet['events'], clocks['events'], lineage['snapshots']):
        require(len(rows) == 2 and {r['fiscal_quarter'] for r in rows} == expected, 'fixed_two_event_inventory')
    for path, expected_hash in lineage['input_sha256'].items():
        require(sha(Path(path).read_bytes()) == expected_hash, 'retained_price_input_changed')
    rows = []
    for event in packet['events']:
        require(event['source_audit'] == 'PASS' and event['prior_order'] == 'UNIQUE_LATEST', 'source_pair_not_ready')
        clock = next(r for r in clocks['events'] if r['event_id'] == event['event_id'])
        check_clock(clock, event, Path(evidence_dir))
        item = next(r for r in lineage['snapshots'] if r['fiscal_quarter'] == event['fiscal_quarter'])
        snap = load_equity_snapshot(item['snapshot_file'])
        require(snap.snapshot_id == item['snapshot_id'] == clocks['snapshot_ids'][event['fiscal_quarter']], 'snapshot_identity_changed')
        row = diagnose(event, clock['channel_publication_at'], snap)
        row.update(channel_url=clock['channel_url'], daily_RTH_OHLC_mismatch_sessions=item['daily_RTH_OHLC_mismatch_sessions'],
                   daily_RTH_volume_difference_sessions=item['daily_RTH_volume_difference_sessions'])
        rows.append(row)
    result = dict(schema_version='nvda-channel-price-diagnostic-v1', source_packet_hash=packet['packet_hash'],
                  clock_evidence_sha256=sha(CLOCK.read_bytes()), price_lineage_sha256=clocks['price_lineage_sha256'],
                  code_sha256={name: sha((ROOT / name).read_bytes()) for name in ('tools/nvda_event_price_diagnostic.py',
                      'tools/equity_content_protocol.py', 'src/hakimi_research/equity_dataset.py', 'tools/equity_research_card.py')},
                  events=rows, counts=dict(events=2, comparable_sources=2, price_snapshots=2,
                      price_signals=sum(r['price_condition'] for r in rows),
                      price_numeric_intersection=sum(r['price_condition'] and r['numeric_condition'] for r in rows),
                      human_approved_events=0, content_interventions=None, economic_runs=0, new_research_admitted=0),
                  status='READONLY_ENGINEERING_DIAGNOSTIC_NOT_ECONOMIC_RESEARCH',
                  authority=dict(account_queries=False, orders=False, economic_execution=False, human_approval=False),
                  limitations=clocks['limitations'] + lineage['limitations'])
    result['diagnostic_hash'] = digest(result)
    return result


def render(result):
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>NVIDIA 公告与价格核对</title><style>' + CARD_STYLE + '</style><main><header><small>两事件工程诊断 · 只读</small>',
             '<h1>公告何时公开，价格何时可以确认？</h1><p>沿用 NVIDIA FY2024Q1／Q2 两个既有事件；收益对照尚未运行。</p></header>',
             '<div class="summary">新增时间来自 GlobeNewswire 页面时间标签，精确到秒。它表示该渠道的发布记录；全渠道最早时间与网页历史不变性仍未证实。原公告的空时间字段保留。</div>',
             '<p>规则：渠道时间后加 120 秒，等待首个完整交易日；收盘后再等 60 秒。仅当该日收盘高于公告前最后收盘时，才形成价格候选，最早下一交易日开盘模拟入场。</p>',
             '<div class="counts"><span>来源可比 2</span><span>行情快照 2</span><span>价格信号 ' + str(result['counts']['price_signals']) + '</span><span>数值与价格交集 ' + str(result['counts']['price_numeric_intersection']) + '</span><span>人工核准 0</span><span>收益研究 0</span></div>']
    def local(stamp):
        return utc(stamp).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S') + ' 纽约时间'
    for row in result['events']:
        entry = local(row['earliest_model_entry_at']) if row['earliest_model_entry_at'] else '无价格候选，不模拟入场'
        pairs = [('已列来源营收／在先指引中点', row['actual_revenue_million'] + ' / ' + row['prior_guidance_midpoint_million'] + ' 百万美元'),
                 ('发行渠道时间记录', local(row['channel_publication_at'])), ('历史模型假设可用时间', local(row['model_available_at'])),
                 ('价格确认可用时间', local(row['confirmation_at'])), ('是否形成价格候选', '是' if row['price_condition'] else '否'), ('最早模型入场时刻', entry)]
        parts.append('<article class="card"><h2>FY' + escape(row['fiscal_quarter']) + '</h2><div class="table-wrap"><table><tbody>')
        parts.extend('<tr><th>' + escape(label) + '</th><td>' + escape(value) + '</td></tr>' for label, value in pairs)
        parts.append('</tbody></table></div><p><a target="_blank" rel="noopener noreferrer" href="' + escape(row['channel_url'], quote=True) + '">核对发行渠道页面</a></p><p class="note">以上是信息与价格的时间对齐，不是买入指令。字段尚未经使用者核准。</p></article>')
    parts += ['<p class="warning">16 个交易日的日线与常规时段小时线汇总 OHLC 全部一致；成交量全部存在差异，原因未证实。本快照统一使用常规时段小时线汇总，不作成交量、流动性或成交能力结论。</p>',
              '<p>两个事件均是已见工程样例，不足以支持策略优势结论。保留无信号、亏损和排除结果；不按结果增加或替换样本。</p>',
              '<article class="card"><h2>待核准的有限对照</h2><p>拟比较相同价格规则，与价格规则加“实际营收高于已列在先公司指引”条件。两个事件各用 10,000 美元虚拟初始资金、25% 仓位、3% 止损、6% 止盈；评分至公告后第五个交易日，以市值结算。</p><p>常规成本为每次成交 0.08% 费用与 0.05% 滑点；另保留双倍成本情景。共 8 次离线模拟，两组采用相同评分区间和成本，不追加行情请求。</p><p class="note">这只是待核准方案。当前两个候选未达到原先至少三个候选的研究门槛，门槛不降低；拟议对照仅用于验证工程流程。尚未运行收益、费用或基准比较。</p></article>',
              '<footer>收益、内容干预、费用和基准差异尚未计算；人工首次使用验收尚未完成。<br>核对身份 <code>' + result['diagnostic_hash'] + '</code></footer></main></html>']
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packet', 'clock-evidence-dir', 'lineage', 'output-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args(); sys.addaudithook(_deny_network)
    result = prepare(args.packet, args.clock_evidence_dir, args.lineage)
    dest = args.output_dir / ('diagnostic-' + result['diagnostic_hash'])
    files = {'result.json': (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode(), 'index.html': render(result).encode()}
    for name, raw in files.items():
        path = dest / name
        require(not path.exists() or path.read_bytes() == raw, 'existing_diagnostic_changed')
    for name, raw in files.items():
        _save_encoded_report(raw, dest / name)
    print(json.dumps(dict(status=result['status'], counts=result['counts'], output=str(dest))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
