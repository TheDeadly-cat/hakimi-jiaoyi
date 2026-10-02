"""Approval-bound offline NVIDIA comparison using the existing engine and ledger.

Default: verify inputs and show preparation status. Execution requires a scoped
human receipt and an explicit switch. No provider, account or order interface.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from html import escape
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.equity_cli import _deny_network
from hakimi_research.equity_dataset import EquitySnapshot, load_equity_snapshot, verify_equity_snapshot
from hakimi_research.equity_research import PERMISSIONS, _SessionEngine, _projection
from hakimi_research.risk import RiskManager
from hakimi_research.reporting import _save_encoded_report
from scripts.reconcile_research_ledger import reconcile
from tools.equity_content_protocol import utc
from tools.equity_content_study import ContentSignalAdapter, FIXED_RISK
from tools import nvda_event_price_diagnostic as diagnostic
from tools.equity_research_card import CARD_STYLE

PROPOSAL = ROOT / 'docs/research-evidence/nvda-event-price-20260930/economic-proposal.json'
PROPOSAL_SHA256 = '00e06ae243d7f9f8b8319362c01ef614e7ec49ca0f07787d604de33e4a02acc9'
REPORT_SCHEMA = 'us-equity-channel-content-report-v1'
EVENT_IDS = ['NVDA:2024Q1:EARNINGS', 'NVDA:2024Q2:EARNINGS']
FIELDS = ['actual_revenue_million', 'latest_listed_prior_guidance_midpoint_million',
          'channel_publication_at', 'channel_clock_meaning', 'bounded_economic_scope']


def claim_path():
    return ROOT / 'artifacts/nvda-price-20260930/economic-claims' / (PROPOSAL_SHA256 + '.private.json')


def require(condition, reason):
    if not condition:
        raise ValueError('nvda_economics:' + reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def tool_identity():
    names = ['tools/nvda_economic_study.py', 'tools/nvda_event_price_diagnostic.py',
             'tools/equity_content_study.py', 'tools/equity_content_protocol.py',
             'scripts/reconcile_research_ledger.py']
    return {name: sha(ROOT / name) for name in names}


def check_approval(receipt, proposal, clocks):
    require(receipt is not None, 'human_field_and_scope_approval_required')
    require(set(receipt) == {'schema_version', 'proposal_sha256', 'source_packet_hash', 'diagnostic_hash',
            'clock_evidence_sha256', 'snapshot_ids', 'approved_event_ids', 'approved_fields', 'decision',
            'reviewer_kind', 'reviewer', 'source_user_confirmation', 'reviewed_at'}, 'approval_shape')
    require(receipt['schema_version'] == 'nvda-field-economic-approval-v1'
            and receipt['decision'] == 'APPROVE_LISTED_FIELDS_AND_EIGHT_OFFLINE_CELLS'
            and receipt['reviewer_kind'] == 'HUMAN_ATTESTATION', 'human_approval_kind_or_scope')
    require(receipt['proposal_sha256'] == PROPOSAL_SHA256 and all(receipt[k] == proposal[k] for k in
            ('source_packet_hash', 'diagnostic_hash', 'clock_evidence_sha256', 'snapshot_ids')), 'approval_input_binding')
    require(receipt['approved_event_ids'] == EVENT_IDS and receipt['approved_fields'] == FIELDS, 'approval_field_scope')
    require(all(type(receipt[k]) is str and receipt[k].strip() for k in ('reviewer', 'source_user_confirmation')), 'human_attestation_required')
    require(utc(receipt['reviewed_at']) >= max(utc(r['observed_at']) for r in clocks['events']), 'approval_before_clock_evidence')
    return digest(receipt)


def prepare(args):
    require(sha(PROPOSAL) == PROPOSAL_SHA256, 'frozen_proposal_changed')
    proposal = read_document(PROPOSAL); clocks = read_document(diagnostic.CLOCK)
    approval = read_document(args.approval) if args.approval else None
    approval_hash = check_approval(approval, proposal, clocks) if approval is not None or args.execute_approved else None
    # Rechecks original source packet, private DOM witnesses and quote hashes.
    result = diagnostic.prepare(args.packet, args.clock_evidence_dir, args.lineage)
    require(result['diagnostic_hash'] == proposal['diagnostic_hash']
            and sha(diagnostic.CLOCK) == proposal['clock_evidence_sha256'], 'diagnostic_or_clock_identity_changed')
    lineage = read_document(args.lineage)
    snapshots = {r['fiscal_quarter']: load_equity_snapshot(r['snapshot_file']) for r in lineage['snapshots']}
    require({q: s.snapshot_id for q, s in snapshots.items()} == proposal['snapshot_ids'], 'snapshot_set_changed')
    files = [PROPOSAL, diagnostic.CLOCK, args.packet, args.lineage]
    if args.approval: files.append(args.approval)
    files += [Path(r['snapshot_file']) for r in lineage['snapshots']]
    packet = read_document(args.packet)
    files += [args.packet.parent / 'manifest.private.json']
    files += [args.packet.parent / s['retained_path'] for s in packet['sources']]
    files += [args.clock_evidence_dir / name for e in clocks['events'] for name in e['witness_sha256']]
    files += [Path(path) for path in lineage['input_sha256']]
    inputs = {str(p.resolve()): sha(p) for p in files}
    return dict(proposal=proposal, clocks=clocks, approval=approval, approval_hash=approval_hash,
                diagnostic=result, snapshots=snapshots, input_sha256=inputs, tool_identity=tool_identity())


def _engine_cell(snapshot, row, *, variant, cost, score_start, score_end, purpose, authorization_hash):
    """Small signal-plan adapter; all fills, risk and bookkeeping stay canonical."""
    data = verify_equity_snapshot(snapshot.document)
    require(variant in {'PRICE_ONLY', 'PRICE_PLUS_CONTENT', 'CONTENT_DISABLED'}, 'variant')
    synthetic = data['evidence_kind'] == 'SYNTHETIC_TEST'
    require((synthetic and purpose == 'SYNTHETIC_REGRESSION') or (not synthetic and purpose == 'DESCRIPTIVE_DEVELOPMENT'
            and type(authorization_hash) is str and len(authorization_hash) == 64), 'real_input_requires_approved_context')
    require(data['research_admission']['allowed'] and data['bar_availability_lag_seconds'] == 60, 'snapshot_not_eligible')
    require(type(row['price_condition']) is bool and type(row['numeric_condition']) is bool, 'conditions_must_be_boolean')
    require(cost in ({'name': 'NORMAL', 'fee_rate': '0.0008', 'slippage_pct': '0.0005'},
                     {'name': 'DOUBLE', 'fee_rate': '0.0016', 'slippage_pct': '0.0010'}), 'fixed_cost_scenario')
    sessions = data['sessions']; dates = [s['date'] for s in sessions]
    first, end = dates.index(score_start), dates.index(score_end) + 1
    require(1 <= first < end, 'score_context')
    eligible = row['price_condition'] and (variant != 'PRICE_PLUS_CONTENT' or row['numeric_condition'])
    entry = row['earliest_model_entry_at'] if eligible else None
    confirmation_open = None
    if entry is not None:
        require(entry == sessions[first]['open_utc'], 'entry_must_equal_fixed_score_start')
        confirmation = sessions[first - 1]
        require(pd.Timestamp(row['confirmation_at']) == pd.Timestamp(confirmation['close_utc']) + pd.Timedelta(seconds=60), 'confirmation_clock_changed')
        require(utc(row['model_available_at']) <= utc(confirmation['open_utc']), 'information_not_available_for_full_session')
        confirmation_open = str(pd.Timestamp(confirmation['open_utc']))
    plan = dict(confirmation_bar_open=confirmation_open, execution_at=entry)
    params = dict(confirmation_bar_open=confirmation_open, decision_plan_hash=digest(plan),
                  protocol_hash=PROPOSAL_SHA256, position_pct=0.25, stop_loss_pct=0.03, take_profit_pct=0.06)
    strategy = ContentSignalAdapter(params)
    config = BotConfig(market='stock', symbol=data['security']['symbol'], timeframe='1d', initial_cash=10000,
        strategy=StrategyConfig(name=strategy.name, params=params), risk=RiskConfig(**FIXED_RISK),
        execution=ExecutionConfig(fee_rate=float(cost['fee_rate']), slippage_pct=float(cost['slippage_pct'])))
    result = _SessionEngine(config, strategy, RiskManager(config.risk), sessions=sessions, lag=60,
                            benchmark_policy='STANDARD_STRATEGY_RISK').run(EquitySnapshot(data).frame(), score_start=first, score_end=end).to_dict()
    result.pop('experiment_manifest', None)
    buys = [f for f in result['fills'] if f['action'] == 'BUY']
    require(len(buys) <= 1 and all(entry is not None and pd.Timestamp(f['fill_time']) == pd.Timestamp(entry) for f in buys), 'unexpected_entry')
    spec = dict(schema_version='us-equity-channel-content-spec-v1', snapshot_id=snapshot.snapshot_id,
        score_start_session=score_start, score_end_session=score_end, initial_cash=10000,
        fee_rate=float(cost['fee_rate']), slippage_pct=float(cost['slippage_pct']), risk=dict(FIXED_RISK),
        end_policy='MARK_TO_MARKET', quantity_policy='FRACTIONAL_SHARES_RESEARCH_APPROXIMATION',
        execution_policy='STANDARD_STRATEGY_RISK', purpose=purpose, variant=variant, event_id=row['event_id'],
        protocol_hash=PROPOSAL_SHA256, strategy=dict(name=strategy.name, params=params))
    core = dict(schema_version=REPORT_SCHEMA, spec=spec, spec_hash=digest(spec), dataset=_projection(data),
        decision=plan, diagnostic_row=row, result=result, result_hash=digest(result), authorization_hash=authorization_hash,
        provenance=build_runtime_provenance(), tool_identity=tool_identity(), execution_permission=dict(PERMISSIONS),
        limitations=['Seen engineering inputs, not strategy admission or unseen validation.',
            'Channel known-public-by reconstruction; source public_at and global first publication remain unknown.',
            '120-second information delay and 60-second bar delay are model assumptions.',
            'Daily OHLC exits, fractional shares, fixed slippage and mark-to-market are approximations.',
            'PRICE_ONLY is the common comparison baseline; no third buy-and-hold run or portfolio aggregation.'])
    return {**core, 'report_hash': digest(core)}


def run_cell(context, quarter, cost, variant):
    require(variant in {'PRICE_ONLY', 'PRICE_PLUS_CONTENT'}, 'approved_variants_only')
    approved = check_approval(context['approval'], context['proposal'], context['clocks'])
    require(approved == context['approval_hash'], 'approval_changed')
    require(sha(PROPOSAL) == PROPOSAL_SHA256 and read_document(PROPOSAL) == context['proposal'], 'proposal_changed')
    require(digest({k: v for k, v in context['diagnostic'].items() if k != 'diagnostic_hash'})
            == context['proposal']['diagnostic_hash'], 'diagnostic_changed')
    require(context['tool_identity'] == tool_identity(), 'execution_code_changed')
    row = next(r for r in context['diagnostic']['events'] if r['fiscal_quarter'] == quarter)
    window = next(r for r in context['proposal']['score_windows'] if r['fiscal_quarter'] == quarter)
    require(context['snapshots'][quarter].snapshot_id == context['proposal']['snapshot_ids'][quarter] == row['snapshot_id'], 'cell_snapshot_binding')
    return _engine_cell(context['snapshots'][quarter], row, variant=variant, cost=cost,
        score_start=window['start_session'], score_end=window['end_session'], purpose='DESCRIPTIVE_DEVELOPMENT', authorization_hash=approved)


def check_replay(original, repeated):
    for report in (original, repeated):
        require(report['report_hash'] == digest({k: v for k, v in report.items() if k != 'report_hash'}), 'report_hash_changed')
    omit = {'provenance', 'report_hash'}
    same = canonical_bytes({k: v for k, v in original.items() if k not in omit}) == canonical_bytes({k: v for k, v in repeated.items() if k not in omit})
    before, after = original['provenance'], repeated['provenance']
    source = before['source_identity']['content_sha256'] == after['source_identity']['content_sha256'] and all(
        p['source_identity']['status'] in {'CONTENT_HASHED', 'BUILD_VERIFIED'} for p in (before, after))
    environment = before['environment_verified'] == after['environment_verified'] and after['environment_verified']['status'] == 'VERIFIED'
    return dict(report_hash=original['report_hash'], result_and_inputs_match=same, source_matches=source,
                environment_verified=environment, replay_verified=same and source and environment, order_allowed=False)


def metrics(report):
    result = report['result']; net = Decimal(str(result['final_equity'])) - Decimal('10000')
    keys = ('total_return', 'final_equity', 'total_fees', 'max_drawdown', 'realized_pnl', 'unrealized_pnl',
            'open_position_qty', 'fill_count', 'round_trip_count', 'ambiguous_intrabar_count')
    return {**{k: result[k] for k in keys}, 'net_pnl': str(net),
            'before_fees_pnl_on_same_fills_including_slippage': str(net + Decimal(str(result['total_fees'])))}


def execute(context, output):
    # Receipt validation precedes creating an execution directory or claim.
    check_approval(context['approval'], context['proposal'], context['clocks'])
    output = Path(output).resolve()
    require(output.is_relative_to(ROOT / 'artifacts') and output != ROOT / 'artifacts', 'private_new_output_required')
    require(not output.exists(), 'output_already_exists_no_repeat')
    require(context['proposal']['budget'] == dict(real_economic_cells=8, replays=8, independent_ledger_checks=8,
            new_provider_calls=0, account_queries=0, orders=0, tuning=0), 'fixed_budget_changed')
    expected_tools = context['tool_identity']
    expected_runtime = build_runtime_provenance()
    require(expected_runtime['source_identity']['status'] in {'CONTENT_HASHED', 'BUILD_VERIFIED'}
            and expected_runtime['environment_verified']['status'] == 'VERIFIED', 'runtime_source_or_dependencies_unverified')
    def unchanged():
        require(expected_tools == tool_identity() and all(sha(p) == h for p, h in context['input_sha256'].items()), 'frozen_input_changed')
        runtime = build_runtime_provenance()
        require(all(runtime[k] == expected_runtime[k] for k in ('source_identity', 'environment_verified')), 'runtime_changed_during_study')
    unchanged()
    claim = claim_path()
    require(not claim.exists(), 'eight_cell_budget_already_claimed_no_repeat')
    write_new(claim, dict(output=str(output), started_at=stamp(), proposal_sha256=PROPOSAL_SHA256,
                         approval_hash=context['approval_hash'], budget=context['proposal']['budget']))
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / 'inputs-before.private.json', context['input_sha256'])
    write_new(output / 'input-diagnostic.private.json', context['diagnostic'])
    summary = dict(schema_version='nvda-eight-cell-study-v1', status='INCOMPLETE', started_at=stamp(),
        proposal_sha256=PROPOSAL_SHA256, approval_hash=context['approval_hash'], diagnostic_hash=context['diagnostic']['diagnostic_hash'],
        economic_cells_started=0, replay_cells_started=0, ledger_checks_completed=0, cells=[],
        events=[dict(event_id=e, status='NOT_STARTED') for e in EVENT_IDS], external_requests=0, account_queries=0, broker_order_calls=0,
        execution_permission=dict(PERMISSIONS), human_first_use='NOT_ACCEPTED', research_admitted=False)
    try:
        for event in context['diagnostic']['events']:
            quarter = event['fiscal_quarter']; status = next(r for r in summary['events'] if r['event_id'] == event['event_id'])
            status['status'] = 'IN_PROGRESS'
            for cost in context['proposal']['cost_scenarios']:
                pair = {}
                for variant in ('PRICE_ONLY', 'PRICE_PLUS_CONTENT'):
                    unchanged(); folder = output / quarter / cost['name'] / variant
                    write_new(folder / 'started.private.json', dict(started_at=stamp(), variant=variant))
                    summary['economic_cells_started'] += 1
                    report = run_cell(context, quarter, cost, variant)
                    write_new(folder / 'report.private.json', report)
                    summary['replay_cells_started'] += 1
                    replay = check_replay(report, run_cell(context, quarter, cost, variant))
                    write_new(folder / 'replay.private.json', replay)
                    ledger = reconcile(report, context['snapshots'][quarter].document)
                    write_new(folder / 'ledger.private.json', ledger); summary['ledger_checks_completed'] += 1
                    require(replay['replay_verified'] and ledger['status'] == 'PASS', 'replay_or_ledger_failed')
                    pair[variant] = report
                c, d = pair['PRICE_ONLY'], pair['PRICE_PLUS_CONTENT']
                changed = c['decision'] != d['decision']
                if not changed: require(canonical_bytes(c['result']) == canonical_bytes(d['result']), 'same_decision_unequal_result')
                summary['cells'].append(dict(fiscal_quarter=quarter, cost=cost['name'],
                    score_start=c['spec']['score_start_session'], score_end=c['spec']['score_end_session'],
                    report_hashes={k: r['report_hash'] for k, r in pair.items()}, metrics={k: metrics(r) for k, r in pair.items()},
                    exit_bases={k: [f['fill_basis'] for f in r['result']['fills'] if f['action'] == 'SELL'] for k, r in pair.items()},
                    content_changed_entry=changed, content_minus_price_return=d['result']['total_return'] - c['result']['total_return'],
                    common_baseline='PRICE_ONLY_SAME_WINDOW_CAPITAL_COST_AND_EXIT_RULE'))
            status['status'] = 'COMPLETED_PRICE_SIGNAL' if event['price_condition'] else 'COMPLETED_NO_PRICE_SIGNAL'
        unchanged()
        require(summary['economic_cells_started'] == summary['replay_cells_started'] == summary['ledger_checks_completed'] == 8, 'budget_or_coverage_mismatch')
        summary.update(status='COMPLETED_ENGINEERING_ONLY', counts={**context['diagnostic']['counts'], 'human_approved_events': 2,
            'economic_runs': 8, 'content_interventions': len({r['fiscal_quarter'] for r in summary['cells'] if r['content_changed_entry']})})
    except Exception as exc:
        for event in summary['events']:
            if event['status'] == 'IN_PROGRESS': event['status'] = 'STOPPED_WITH_RETAINED_PARTIAL_CELLS'
        summary.update(status='STOPPED_PRESERVED_NO_AUTOMATIC_RETRY', error_type=type(exc).__name__, error=str(exc))
    summary['finished_at'] = stamp(); summary['tool_identity'] = expected_tools; summary['study_hash'] = digest(summary)
    write_new(output / 'study.private.json', summary)
    rebuild_report(output)
    return summary


def render(summary, source_diagnostic, *, synthetic=False):
    """Reuse the existing static card styling; show incomplete cells explicitly."""
    complete = summary['status'] == 'COMPLETED_ENGINEERING_ONLY'
    state = '两事件离线工程对照完成' if complete else '执行停止 · 已有结果保留'
    if synthetic: state = '虚构数据演示 · 不是真实 NVIDIA 收益'
    page_title = '虚构数据对照演示' if synthetic else 'NVIDIA 有限对照'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>' + page_title + '</title><style>' + CARD_STYLE + '</style><main><header><small>固定两事件 · 历史模拟 · 无账户操作</small><h1>' + state + '</h1></header>',
        '<p class="summary">基准是“仅价格规则”，对照组再加入“实际营收高于已列在先公司指引”条件。各事件独立使用相同资金、评分区间、成本与退出规则；两档成本不增加独立事件数。</p>',
        '<p>渠道时间加 120 秒为假设的信息可用时间；首个完整交易日收盘后加 60 秒确认，最早随后开盘模拟入场。原公告时刻仍为空，全渠道首次公开时间未认证。</p>']
    def pct(value): return f'{float(value) * 100:+.4f}%'
    def safe(value): return escape(str(value))
    def money(value): return f'{float(value):,.2f}'
    def local_clock(value): return utc(value).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')
    cells = {(c['fiscal_quarter'], c['cost']): c for c in summary['cells']}
    for event in source_diagnostic['events']:
        q = event['fiscal_quarter']
        parts.append('<article class="card"><h2>FY' + escape(q) + '</h2><p>实际营收 / 已列在先指引中点：' +
            escape(event['actual_revenue_million'] + ' / ' + event['prior_guidance_midpoint_million']) + ' 百万美元。</p><p>渠道时间：' +
            local_clock(event['channel_publication_at']) + '；价格确认：' + local_clock(event['confirmation_at']) + '（纽约时间）。</p>')
        parts.append('<div class="table-wrap"><table><thead><tr><th>成本情景</th><th>仅价格净收益率</th><th>加内容净收益率</th><th>差额（百分点）</th><th>内容改变入场意图</th></tr></thead><tbody>')
        for name, label in (('NORMAL', '常规'), ('DOUBLE', '双倍')):
            cell = cells.get((q, name))
            if cell is None:
                parts.append('<tr><td>' + label + '</td><td colspan="4">未完成，不能填成零收益</td></tr>'); continue
            c, d = cell['metrics']['PRICE_ONLY'], cell['metrics']['PRICE_PLUS_CONTENT']
            parts.append('<tr><td>' + label + '</td><td>' + pct(c['total_return']) + '</td><td>' + pct(d['total_return']) + '</td><td>' +
                f'{float(cell["content_minus_price_return"]) * 100:+.4f}' + '</td><td>' + ('是' if cell['content_changed_entry'] else '否') + '</td></tr>')
        parts.append('</tbody></table></div>')
        for name, label in (('NORMAL', '常规'), ('DOUBLE', '双倍')):
            cell = cells.get((q, name))
            if cell is None: continue
            parts.append('<details><summary>' + label + '成本：费用与期末持仓</summary><p>评分区间 ' + escape(cell['score_start'] + ' 至 ' + cell['score_end']) + '</p>')
            for variant, title in (('PRICE_ONLY', '仅价格'), ('PRICE_PLUS_CONTENT', '价格加内容')):
                m = cell['metrics'][variant]
                parts.append('<p>' + title + '：扣费后损益 ' + money(m['net_pnl']) + ' 美元；费用 ' + money(m['total_fees']) +
                    '；相同成交路径扣费前损益 ' + money(m['before_fees_pnl_on_same_fills_including_slippage']) +
                    '（仍包含模拟滑点）。已实现 ' + money(m['realized_pnl']) + '；未实现 ' + money(m['unrealized_pnl']) +
                    '；期末持仓 ' + f'{float(m["open_position_qty"]):.4f}' + ' 股。按市值结算，不强制平仓。</p>')
            parts.append('</details>')
        parts.append('</article>')
    parts += ['<p class="warning">已见两事件只用于工程验证。原至少三个候选门槛未达，未授予策略研究接纳；成交量差异原因未证实。亏损、无信号、停止和零内容干预均保留。</p>',
              '<footer>实际启动模拟 ' + safe(summary['economic_cells_started']) + ' 次；重放 ' + safe(summary['replay_cells_started']) +
              ' 次；独立账本核对 ' + safe(summary['ledger_checks_completed']) + ' 次。非开发者首次使用尚未验收。<br>结果身份 <code>' + safe(summary['study_hash']) + '</code></footer></main></html>']
    return '\n'.join(parts)


def rebuild_report(directory):
    directory = Path(directory)
    summary = read_document(directory / 'study.private.json')
    source_diagnostic = read_document(directory / 'input-diagnostic.private.json')
    require(summary['study_hash'] == digest({k: v for k, v in summary.items() if k != 'study_hash'}), 'study_identity_changed')
    require(source_diagnostic['diagnostic_hash'] == summary['diagnostic_hash']
            == digest({k: v for k, v in source_diagnostic.items() if k != 'diagnostic_hash'}), 'report_input_binding')
    require(summary['tool_identity'] == tool_identity(), 'retained_renderer_code_changed')
    encoded = render(summary, source_diagnostic).encode('utf-8')
    output = directory / 'index.html'
    require(not output.exists() or output.read_bytes() == encoded, 'existing_report_changed')
    _save_encoded_report(encoded, output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packet', 'clock-evidence-dir', 'lineage'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--execute-approved', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--report-study', type=Path, help='Rebuild a retained study page offline without running any simulation.')
    args = parser.parse_args(argv); sys.addaudithook(_deny_network)
    if args.report_study is not None:
        require(not args.execute_approved and all(getattr(args, k) is None for k in
                ('packet', 'clock_evidence_dir', 'lineage', 'approval', 'output')), 'report_mode_has_no_execution_inputs')
        print(json.dumps(dict(status='RETAINED_REPORT_RENDERED', output=str(rebuild_report(args.report_study)), economic_runs=0)))
        return 0
    require(all(getattr(args, k) is not None for k in ('packet', 'clock_evidence_dir', 'lineage')), 'input_paths_required')
    context = prepare(args)
    if not args.execute_approved:
        status = 'READY_FOR_APPROVED_OFFLINE_RUN' if context['approval_hash'] else 'PENDING_HUMAN_FIELD_AND_SCOPE_APPROVAL'
        if claim_path().exists(): status = 'EXECUTION_ALREADY_CLAIMED_NO_AUTOMATIC_REPEAT'
        print(json.dumps(dict(status=status,
                              diagnostic_hash=context['diagnostic']['diagnostic_hash'], economic_runs=0, provider_calls=0)))
        return 0
    require(args.output is not None, 'new_output_required')
    summary = execute(context, args.output)
    print(json.dumps({k: summary[k] for k in ('status', 'study_hash', 'economic_cells_started', 'replay_cells_started', 'ledger_checks_completed')}))
    return 0 if summary['status'] == 'COMPLETED_ENGINEERING_ONLY' else 1


if __name__ == '__main__': raise SystemExit(main())
