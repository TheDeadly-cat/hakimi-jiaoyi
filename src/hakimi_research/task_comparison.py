"""Read-only comparisons of verified saved runs with explicit common conditions."""
from pathlib import Path
from .documents import digest
from .offline_app import verify_run, write_new
from .strategy_registry import definition


def _conditions(manifest, report):
    spec, data = report['spec'], report['dataset']
    return dict(dataset=data, score_start=spec['score_start_session'], score_end=spec['score_end_session'],
        score_clock={k: report['scoring_protocol'][k] for k in ['score_start', 'score_end', 'scored_sessions', 'session_clock_hash']},
        initial_cash=spec['initial_cash'], fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'],
        end_policy=spec['end_policy'], quantity_policy=spec['quantity_policy'], purpose=spec['purpose'],
        source_hash=manifest['runtime']['source_identity']['content_sha256'],
        dependencies=manifest['runtime']['environment_verified'])


def compare_runs(directories, *, output=None):
    directories = [Path(p).resolve() for p in directories]
    if len(directories) < 2 or len(set(directories)) != len(directories):
        raise ValueError('comparison_requires_at_least_two_distinct_saved_runs')
    rows, conditions = [], []
    for directory in directories:
        manifest, report, _ = verify_run(directory)
        from .trade_cli import configuration_view
        result, spec = report['result'], report['spec']
        signals = result['signals']
        from .input_workflow import saved_input_outcome
        outcome = saved_input_outcome(report)
        conditions.append(_conditions(manifest, report))
        rows.append(dict(task_id=manifest['task_id'], run_id=manifest['run_id'], report_hash=report['report_hash'],
            strategy=manifest['task']['strategy'], title=definition(manifest['task']['strategy'])['title'],
            task_version=manifest['task'].get('management'), configuration=configuration_view(spec),
            event_context_hash=manifest['task']['event_context_hash'],
            event_rule=definition(manifest['task']['strategy'])['event_rule'],
            warmup=report['scoring_protocol'], initial_cash=spec['initial_cash'],
            net_return=result['total_return'], net_pnl=result['final_equity'] - spec['initial_cash'],
            max_drawdown=result['max_drawdown'], total_fees=result['total_fees'], fills=result['fill_count'],
            buy_intents=sum(row['action'] == 'BUY' for row in signals),
            blocked_new_buys=outcome['blocked_new_buys'], research_input_outcome=outcome,
            realized_pnl=result['realized_pnl'], unrealized_pnl=result['unrealized_pnl'],
            open_position_qty=result['open_position_qty'], risk_semantics=result['risk_semantics'],
            stop_requests=[dict(requested=r['requested_stop_loss_pct'], effective=r['effective_stop_loss_pct']) for r in signals if r['action'] == 'BUY'],
            reasons=list(dict.fromkeys(r['reason'] for r in signals)), limitations=report['limitations']))
    mismatches = [dict(row=i + 1, fields=[k for k in conditions[0] if conditions[0][k] != condition[k]])
        for i, condition in enumerate(conditions[1:], 1) if condition != conditions[0]]
    result = dict(schema_version='hakimi-task-comparison-v1', status='NOT_COMPARABLE' if mismatches else 'COMPARABLE_CONDITIONS',
        mismatches=mismatches, common_conditions=conditions[0] if not mismatches else None,
        per_run_conditions=conditions, rows=rows, new_economic_runs=0, shared_portfolio=False,
        interpretation=['每行使用独立本金；不能相加为共享资金组合。',
            '净收益和费用来自保存的账本；回撤为评分期权益曲线峰值跌幅，均为描述性结果。',
            '费用为比例手续费；固定滑点已进入成交价格，不计为单独手续费。',
            '仓位、止损、事件过滤与退出规则不同会影响成交和收益；条件可比不等于证明某策略更好。',
            '预热要求可不同，评分区间保持原值；不可比时不计算跨行收益差。'])
    result['differences_from_first'] = [] if mismatches else [dict(row=i + 1,
        net_return=row['net_return'] - rows[0]['net_return'], max_drawdown=row['max_drawdown'] - rows[0]['max_drawdown'],
        total_fees=row['total_fees'] - rows[0]['total_fees'], fills=row['fills'] - rows[0]['fills'],
        blocked_new_buys=row['blocked_new_buys'] - rows[0]['blocked_new_buys']) for i, row in enumerate(rows[1:], 1)]
    result['comparison_hash'] = digest(result)
    if output is not None:
        write_new(output, result)
    return result


def print_comparison(view):
    from .trade_cli import print_configuration
    print('结果对照：' + view['status'] + '；新增计算 0；每行独立本金。')
    for i, row in enumerate(view['rows'], 1):
        config = row['configuration']
        print(f"{i} {row['title']}；净收益 {row['net_return']*100:+.4f}%；回撤 {row['max_drawdown']*100:.4f}%；费用 {row['total_fees']:.2f}；成交 {row['fills']}；BUY {row['buy_intents']}；过滤 {row['blocked_new_buys']}")
        print_configuration(config,'  ')
        print('  预热需求 ' + str(row['warmup']['required_context_sessions']))
        print('  原因：' + '；'.join(row['reasons']))
    for mismatch in view['mismatches']:
        print('不可比：第 ' + str(mismatch['row']) + ' 行不同字段 ' + ', '.join(mismatch['fields']))
    for difference in view['differences_from_first']:
        print(f"第 {difference['row']} 行减第 1 行：净收益 {difference['net_return']*100:+.4f} 个百分点；回撤 {difference['max_drawdown']*100:+.4f} 个百分点；费用 {difference['total_fees']:+.2f}；成交 {difference['fills']:+d}；过滤 {difference['blocked_new_buys']:+d}")
    for note in view['interpretation']:
        print(note)
