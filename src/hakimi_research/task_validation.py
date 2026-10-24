"""Explicit, immutable diagnostics around saved equity runs; no new engine.

Reading saved diagnostics never calculates a strategy. Cost scenarios and
benchmarks require an explicit request and retain their own complete reports.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import math
from pathlib import Path

from .benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from .documents import digest, read_document
from .environment import build_runtime_provenance
from .equity_dataset import load_equity_snapshot
from .equity_research import EquityExperimentRunner, EquityExperimentSpec, PERMISSIONS, SPEC_SCHEMA
from .offline_app import immutable_write, verify_run, write_new
from .strategy_registry import inspect_task_inputs, run_strategy, validate_strategy, verify_task_report

SCHEMA = 'hakimi-task-validation-v1'
SUPPORTED = {'price.dual_ma@1', 'price.buy_and_hold@1', 'event.earnings_schedule@1'}
NOTES = [
    '每格使用独立本金，不能相加为共享资金组合；结果为固定参数的描述性研究。',
    '成本格仅将比例手续费与固定滑点同时乘以倍数；滑点已进入成交价格，不能加回费用推测零成本收益。',
    '现金基准始终持有现金；100%买入持有基准只在评分开始尝试一次，无策略止损、止盈或排期过滤。',
    '基准与策略的仓位和退出规则不同；条件对照不证明策略更好。',
    '后续区间从独立本金和空仓开始，保留历史预热；它不是原持仓的连续运行、盲测或参数优化。',
    '来源、交易日及无公司行动声明未经独立认证；短样本和未运行状态不能解释为验证通过。',
]


def _runtime_key(runtime):
    return dict(source_hash=runtime['source_identity']['content_sha256'],
                environment=runtime['environment_verified'])


def _require_runtime(original, current):
    if (current['source_identity'].get('status') not in {'CONTENT_HASHED', 'BUILD_VERIFIED'}
            or current['environment_verified'].get('status') != 'VERIFIED'
            or _runtime_key(original) != _runtime_key(current)):
        raise ValueError('validation_requires_same_verified_code_and_dependency_identity')


def _summary(report):
    result = report['result']
    return dict(report_hash=report['report_hash'],
        **{key: result.get(key) for key in ('total_return', 'max_drawdown', 'final_equity',
            'total_fees', 'fill_count', 'round_trip_count', 'realized_pnl', 'unrealized_pnl',
            'open_position_qty', 'annualized_return', 'sharpe_ratio', 'win_rate')},
        statistical_status=_saved_mapping(result, 'statistical_status'),
        scored_sessions=report.get('scoring_protocol', {}).get('scored_sessions'))


def _saved_mapping(container, key):
    value = container.get(key)
    return deepcopy(value) if type(value) is dict else dict(status='NOT_AVAILABLE',
        reason='FIELD_NOT_RECORDED_IN_SAVED_REPORT', field=key)


def _diagnostics(manifest, report):
    result = report['result']
    protocol = report.get('scoring_protocol', {})
    from .input_workflow import saved_input_outcome
    try:
        outcome = saved_input_outcome(report)
    except (KeyError, TypeError, ValueError):
        outcome = dict(status='NOT_AVAILABLE', reason='INPUT_OUTCOME_NOT_RECORDED_IN_SAVED_REPORT')
    return dict(status='SAVED_DESCRIPTIVE_DIAGNOSTICS', run_id=manifest['run_id'],
        report_hash=report['report_hash'], new_economic_runs=0,
        sample=dict(scored_sessions=protocol.get('scored_sessions'),
            required_context_sessions=protocol.get('required_context_sessions'),
            available_context_sessions=protocol.get('available_context_sessions'),
            return_observations=len(result['return_series']) if type(result.get('return_series')) is list else None,
            completed_round_trips=len(result['round_trips']) if type(result.get('round_trips')) is list else None,
            fill_count=result.get('fill_count'), evidence_kind=report.get('dataset', {}).get('evidence_kind')),
        accounting=_saved_mapping(result, 'accounting'), statistical_status=_saved_mapping(result, 'statistical_status'),
        risk_semantics=_saved_mapping(result, 'risk_semantics'), summary=_summary(report),
        research_input_outcome=outcome, limitations=deepcopy(report.get('limitations', [])))


def saved_run_diagnostics(run_dir):
    """Project only verified, saved quantities; historical runtimes remain readable."""
    manifest, report, _ = verify_run(run_dir)
    return _diagnostics(manifest, report)


def _base(manifest, report):
    return dict(run_id=manifest['run_id'], task_id=manifest['task_id'], report_hash=report['report_hash'],
        strategy=manifest['task']['strategy'], spec=deepcopy(report['spec']),
        symbol=report['dataset']['security']['symbol'], security=deepcopy(report['dataset']['security']),
        snapshot_id=report['dataset']['snapshot_id'], runtime=_runtime_key(manifest['runtime']))


def _cost_spec(spec, multiplier):
    changed = deepcopy(spec)
    for key in ('fee_rate', 'slippage_pct'):
        value = changed[key] * multiplier
        if not math.isfinite(value) or not 0 <= value < 1:
            raise ValueError('validation_cost_stress_out_of_range:' + key)
        changed[key] = value
    return changed


def _benchmark_spec(spec, kind):
    changed = deepcopy(spec)
    changed.update(schema_version=SPEC_SCHEMA, strategy=dict(name=kind,
        params={'target_position_pct': 1.0} if kind == 'buy_and_hold' else {}),
        execution_policy=BUY_AND_HOLD_POLICY if kind == 'buy_and_hold' else STANDARD_RISK_POLICY)
    changed.pop('event_context_hash', None)
    changed.pop('event_rule', None)
    if kind == 'buy_and_hold':
        changed['risk'].update(max_position_pct=1.0, min_cash_pct=0.0)
    return changed


def _followup_spec(base_snapshot, new_snapshot, spec, start, end):
    old, new = base_snapshot.document, new_snapshot.document
    for key in ('security', 'price_basis', 'volume_unit', 'quote_unit', 'bar_availability_lag_seconds', 'evidence_kind'):
        if old[key] != new[key]:
            raise ValueError('validation_followup_input_semantics_changed:' + key)
    if type(start) is not str or type(end) is not str or start <= spec['score_end_session']:
        raise ValueError('validation_followup_must_start_after_base_score_end')
    if not new['research_admission']['allowed']:
        raise ValueError('validation_followup_data_not_admitted')
    new_rows = {row['date']: (row, candle) for row, candle in zip(new['sessions'], new['candles'])}
    # All source rows already visible to the baseline are fixed, including
    # unused tail rows. This does not claim the later interval was unseen.
    for row, candle in zip(old['sessions'], old['candles']):
        if new_rows.get(row['date']) != (row, candle):
            raise ValueError('validation_followup_prefix_missing_or_revised:' + row['date'])
    new_days = {row['date']: row for row in new['calendar']['days']}
    if any(new_days.get(row['date']) != row for row in old['calendar']['days']):
        raise ValueError('validation_followup_calendar_prefix_missing_or_revised')
    if new['as_of'] < old['as_of'] or new['retrieved_at'] < old['retrieved_at']:
        raise ValueError('validation_followup_receipt_precedes_baseline')
    changed = deepcopy(spec)
    changed.update(snapshot_id=new_snapshot.snapshot_id, score_start_session=start, score_end_session=end)
    return changed


def _cell(root, name, spec, snapshot, context, strategy):
    folder = root / name
    write_new(folder / 'spec.json', spec)
    result = dict(status='STOPPED', reason=None, spec_hash=digest(spec),
                  report_hash=None, summary=None, artifact=name + '/report.json')
    try:
        if strategy is None:
            report = EquityExperimentRunner().run(snapshot, EquityExperimentSpec.from_document(spec)).document
        else:
            report = run_strategy(strategy, snapshot, spec, context).document
        write_new(folder / 'report.json', report)
        result.update(status='COMPLETED', report_hash=report['report_hash'], summary=_summary(report))
    except (ValueError, ArithmeticError) as exc:
        # No retry and no optimistic success. Preserve all other matrix rows.
        result.update(reason=str(exc), artifact=None)
        write_new(folder / 'stopped.json', dict(reason=str(exc), automatic_retry=False))
    return result


def create_validation(run_dir, output_dir, *, followup_snapshot=None, followup_start=None, followup_end=None):
    """Create once. A partly written destination is retained and never resumed here."""
    run_dir, output = Path(run_dir).resolve(), Path(output_dir)
    if output.is_symlink() or output.resolve().is_relative_to(run_dir):
        raise ValueError('validation_output_cannot_modify_original_run')
    manifest, report, snapshot = verify_run(run_dir)
    original_identity = _base(manifest, report)
    runtime = build_runtime_provenance()
    _require_runtime(manifest['runtime'], runtime)
    strategy = manifest['task']['strategy']
    if strategy not in SUPPORTED:
        raise ValueError('validation_strategy_not_supported_saved_diagnostics_remain_available')
    supplied = (followup_snapshot is not None, followup_start is not None, followup_end is not None)
    if any(supplied) and not all(supplied):
        raise ValueError('validation_followup_requires_snapshot_start_and_end')
    spec = report['spec']
    # Reject invalid stress rates before any trajectory starts, including zero
    # and finite but economically unsupported extreme fee configurations.
    costs = [(factor, _cost_spec(spec, factor)) for factor in (2, 3)]
    for _, candidate in costs:
        EquityExperimentSpec.from_document(candidate)
    context = report.get('event_context')
    following, following_spec = None, None
    if all(supplied):
        following = load_equity_snapshot(followup_snapshot)
        following_spec = _followup_spec(snapshot, following, spec, followup_start, followup_end)
        checked = validate_strategy(strategy, following_spec, context)
        inspect_task_inputs(following, checked, event_context=context)
    if output.is_symlink() or output.exists():
        raise ValueError('validation_output_exists_original_artifacts_retained')
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / 'started.json', dict(schema_version=SCHEMA,
        started_at=datetime.now(timezone.utc).isoformat(), base_run_id=manifest['run_id'], automatic_retry=False))
    base_files = ['inputs.json', 'started.json', 'report.json', *('inputs/' + name for name in manifest['input_sha256'])]
    for name in base_files:
        source = run_dir / name
        if source.is_symlink():
            raise ValueError('validation_source_must_be_regular')
        immutable_write(output / 'base' / name, source.read_bytes())
    # Validate the frozen copies, then use only those copies for new calculations.
    manifest, report, snapshot = verify_run(output / 'base')
    if _base(manifest, report) != original_identity:
        raise ValueError('validation_base_changed_while_freezing')
    context = report.get('event_context')
    cost_rows = [dict(status='REUSED_SAVED_RESULT', reason=None, multiplier=1,
        fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'], changed_from_base=False,
        spec_hash=report['spec_hash'], report_hash=report['report_hash'], summary=_summary(report),
        artifact='base/report.json')]
    for factor, candidate in costs:
        row = _cell(output, 'cost-' + str(factor), candidate, snapshot, context, strategy)
        row.update(multiplier=factor, fee_rate=candidate['fee_rate'], slippage_pct=candidate['slippage_pct'],
            changed_from_base=any(candidate[key] != spec[key] for key in ('fee_rate', 'slippage_pct')))
        cost_rows.append(row)
    benchmarks = []
    for kind, title in [('cash', '现金基准'), ('buy_and_hold', '100%买入持有基准')]:
        row = _cell(output, 'benchmark-' + kind, _benchmark_spec(spec, kind), snapshot, None, None)
        row.update(benchmark=kind, title=title)
        benchmarks.append(row)
    followup = dict(status='NOT_RUN', reason='NO_EXPLICIT_FOLLOWUP_INTERVAL', summary=None,
        report_hash=None, artifact=None, method='FIXED_PARAMETERS_LATER_INTERVAL_DESCRIPTIVE_ONLY',
        blind_holdout=False, parameter_selection=False)
    if following is not None:
        immutable_write(output / 'followup' / 'snapshot.json', Path(followup_snapshot).read_bytes())
        frozen = load_equity_snapshot(output / 'followup' / 'snapshot.json')
        # Recheck the sealed bytes; an input changing during the copy is rejected.
        if frozen.document != following.document:
            raise ValueError('validation_followup_changed_while_freezing')
        followup.update(_cell(output, 'followup', following_spec, frozen, context, strategy))
        followup.update(score_start=followup_start, score_end=followup_end, snapshot_id=frozen.snapshot_id)
    rows = [*cost_rows, *benchmarks, followup]
    core = dict(schema_version=SCHEMA,
        status='COMPLETED_WITH_STOPPED_SCENARIOS' if any(row['status'] == 'STOPPED' for row in rows) else 'COMPLETED',
        base=_base(manifest, report), diagnostics=_diagnostics(manifest, report),
        cost_scenarios=cost_rows, benchmarks=benchmarks, followup=followup,
        new_economic_runs=sum(row['status'] == 'COMPLETED' for row in rows),
        permissions=dict(PERMISSIONS), interpretation=list(NOTES))
    _require_runtime(manifest['runtime'], build_runtime_provenance())
    core['files'] = {p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file()}
    write_new(output / 'validation.json', {**core, 'validation_hash': digest(core)})
    return read_validation(output)


def _check_cell(root, name, row, expected_spec, snapshot, context, runtime):
    if read_document(root / name / 'spec.json') != expected_spec or row['spec_hash'] != digest(expected_spec):
        raise ValueError('validation_derived_spec_changed:' + name)
    if row['status'] == 'STOPPED':
        stopped = read_document(root / name / 'stopped.json')
        if (not row['reason'] or stopped != dict(reason=row['reason'], automatic_retry=False)
                or row['summary'] is not None or row['report_hash'] is not None or row['artifact'] is not None
                or (root / name / 'report.json').exists()):
            raise ValueError('validation_stopped_scenario_invalid:' + name)
        return
    if row['status'] != 'COMPLETED' or row['reason'] is not None or row['artifact'] != name + '/report.json':
        raise ValueError('validation_scenario_status_invalid:' + name)
    report = verify_task_report(read_document(root / name / 'report.json'), snapshot)
    _require_runtime(runtime, report['provenance'])
    from .equity_research import _projection
    if (report['spec'] != expected_spec or report['dataset'] != _projection(snapshot.document)
            or report.get('event_context') != context or row['summary'] != _summary(report)
            or row['report_hash'] != report['report_hash']):
        raise ValueError('validation_scenario_identity_conflict:' + name)


def read_validation(output_dir):
    """Read and verify the complete frozen package without economic calculations."""
    root = Path(output_dir)
    if root.is_symlink():
        raise ValueError('validation_directory_must_be_regular')
    value = read_document(root / 'validation.json')
    if (value.get('schema_version') != SCHEMA or value.get('permissions') != PERMISSIONS
            or value.get('validation_hash') != digest({k: v for k, v in value.items() if k != 'validation_hash'})):
        raise ValueError('validation_manifest_identity_conflict')
    inventory = value['files']
    observed = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('validation_artifact_must_be_regular')
        if path.is_file() and path != root / 'validation.json':
            relative = path.relative_to(root).as_posix()
            observed.add(relative)
            if inventory.get(relative) != sha256(path.read_bytes()).hexdigest():
                raise ValueError('validation_artifact_missing_or_changed:' + relative)
    if observed != set(inventory):
        raise ValueError('validation_artifact_inventory_conflict')
    manifest, report, snapshot = verify_run(root / 'base')
    if value['base'] != _base(manifest, report) or value['diagnostics'] != _diagnostics(manifest, report):
        raise ValueError('validation_base_projection_conflict')
    strategy, spec, runtime = manifest['task']['strategy'], report['spec'], manifest['runtime']
    if strategy not in SUPPORTED or value['interpretation'] != NOTES:
        raise ValueError('validation_contract_changed')
    context = report.get('event_context')
    cost_rows = value['cost_scenarios']
    if [row.get('multiplier') for row in cost_rows] != [1, 2, 3]:
        raise ValueError('validation_cost_matrix_invalid')
    for row in cost_rows:
        factor = row['multiplier']
        candidate = _cost_spec(spec, factor)
        if (row['fee_rate'] != candidate['fee_rate'] or row['slippage_pct'] != candidate['slippage_pct']
                or row['changed_from_base'] != any(candidate[key] != spec[key] for key in ('fee_rate', 'slippage_pct'))):
            raise ValueError('validation_cost_projection_conflict')
        if factor == 1:
            expected = dict(status='REUSED_SAVED_RESULT', reason=None, multiplier=1,
                fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'], changed_from_base=False,
                spec_hash=report['spec_hash'], report_hash=report['report_hash'], summary=_summary(report), artifact='base/report.json')
            if row != expected:
                raise ValueError('validation_base_cost_row_changed')
        else:
            _check_cell(root, 'cost-' + str(factor), row, candidate, snapshot, context, runtime)
    benchmarks = value['benchmarks']
    if [row.get('benchmark') for row in benchmarks] != ['cash', 'buy_and_hold']:
        raise ValueError('validation_benchmark_matrix_invalid')
    for row in benchmarks:
        kind = row['benchmark']
        _check_cell(root, 'benchmark-' + kind, row, _benchmark_spec(spec, kind), snapshot, None, runtime)
    following = value['followup']
    if (following['method'] != 'FIXED_PARAMETERS_LATER_INTERVAL_DESCRIPTIVE_ONLY'
            or following['blind_holdout'] is not False or following['parameter_selection'] is not False):
        raise ValueError('validation_followup_authority_invalid')
    if following['status'] == 'NOT_RUN':
        if (following != dict(status='NOT_RUN', reason='NO_EXPLICIT_FOLLOWUP_INTERVAL', summary=None,
                report_hash=None, artifact=None, method='FIXED_PARAMETERS_LATER_INTERVAL_DESCRIPTIVE_ONLY',
                blind_holdout=False, parameter_selection=False) or (root / 'followup').exists()):
            raise ValueError('validation_followup_not_run_invalid')
    else:
        frozen = load_equity_snapshot(root / 'followup' / 'snapshot.json')
        candidate = _followup_spec(snapshot, frozen, spec, following['score_start'], following['score_end'])
        if following['snapshot_id'] != frozen.snapshot_id:
            raise ValueError('validation_followup_snapshot_identity_conflict')
        _check_cell(root, 'followup', following, candidate, frozen, context, runtime)
    rows = [*cost_rows, *benchmarks, following]
    expected_status = 'COMPLETED_WITH_STOPPED_SCENARIOS' if any(row['status'] == 'STOPPED' for row in rows) else 'COMPLETED'
    if value['status'] != expected_status or value['new_economic_runs'] != sum(row['status'] == 'COMPLETED' for row in rows):
        raise ValueError('validation_completion_projection_conflict')
    return value
