"""Repository-only, read-only observation of the existing strategy boundary.

No strategy, engine or saved report is replaced. This is a Python callback
contract check, not a sandbox against malicious reflection/filesystem access,
an independent blind holdout, or proof of historical point-in-time data.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd

from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from hakimi_research.documents import digest, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.offline_app import verify_run
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import DualMovingAverageStrategy, build_strategy
from hakimi_research.strategy_registry import run_strategy

SCHEMA = 'strategy-prefix-observation-v1'
HOLDOUT_SCHEMA = 'independent-historical-holdout-design-v1'
HOLDOUT_MODE = 'PROJECT_HISTORICAL_HOLDOUT_PREACQUISITION'
FIELDS = ('open', 'high', 'low', 'close', 'volume')
LIMITATIONS = [
    'Checks the registered Python strategy callback arguments, not an OS security sandbox.',
    'Does not prevent malicious reflection, module globals, files, network or other side channels.',
    'Historical input may have been revised or viewed before this design; blind holdout is not proven.',
    'A verification replay is one additional calculation; the original product run stays unchanged.',
]


def frame_hash(data):
    rows = [[stamp.isoformat(), *[float(v).hex() for v in row]]
            for stamp, row in zip(data.index, data.loc[:, FIELDS].itertuples(index=False, name=None))]
    return digest(dict(columns=list(FIELDS), rows=rows))


def _blocks(data):
    # Pinned pandas: inspect each actual numeric allocation, not a potentially
    # copied .values projection that could conceal a larger shared backing.
    return [block.values for block in data._mgr.blocks]


def check_visible_frame(visible, full, limit, *, guarded_input=None):
    if (type(visible) is not pd.DataFrame or list(visible.columns) != list(FIELDS)
            or len(visible) != limit or not visible.equals(full.iloc[:limit])
            or visible.attrs):
        raise ValueError('strategy_visible_input_is_not_exact_prefix')
    try:
        visible.iloc[limit]
    except IndexError:
        pass
    else:
        raise ValueError('strategy_future_row_index_was_accessible')
    boundaries = []
    for values in _blocks(visible):
        if not isinstance(values, np.ndarray) or values.dtype.kind not in 'fiu':
            raise ValueError('strategy_numeric_backing_not_supported')
        backing = values
        while isinstance(backing.base, np.ndarray):
            backing = backing.base
        if backing.base is not None or backing.nbytes != values.nbytes:
            raise ValueError('strategy_numeric_backing_extends_beyond_visible_prefix')
        candidates = _blocks(full) + (_blocks(guarded_input) if guarded_input is not None else [])
        if any(np.shares_memory(values, candidate) for candidate in candidates):
            raise ValueError('strategy_prefix_shares_engine_price_storage')
        boundaries.append(dict(visible_elements=int(values.size), backing_elements=int(backing.size),
                               visible_bytes=int(values.nbytes), backing_bytes=int(backing.nbytes)))
    return dict(visible_rows=limit, visible_first=visible.index[0].isoformat(),
                visible_through=visible.index[-1].isoformat(), prefix_sha256=frame_hash(visible),
                numeric_allocations=boundaries, shares_engine_price_storage=False,
                dataframe_attrs_empty=True, future_row_index_rejected=True,
                visible_timestamp_semantics='BAR_OPEN')


class PrefixObserver:
    """Observe the actual unwrapped Dual MA function after its existing guard."""
    def __init__(self, data, first, last):
        self.data, self.first, self.last = data, first, last
        wrapped = DualMovingAverageStrategy.generate_signal
        if not getattr(wrapped, '_research_strategy_guarded', False) or not hasattr(wrapped, '__wrapped__'):
            raise ValueError('registered_strategy_guard_not_observable')
        self.wrapper_code, self.target_code = wrapped.__code__, wrapped.__wrapped__.__code__
        self.rows, self.active = [], {}

    def _profile(self, frame, event, value):
        if frame.f_code is not self.target_code:
            return
        if event == 'call':
            guard = frame.f_back
            if guard is None or guard.f_code is not self.wrapper_code:
                raise ValueError('strategy_called_without_existing_guard')
            visible, portfolio = frame.f_locals['data'], frame.f_locals['portfolio']
            if (guard.f_locals.get('data_snapshot') is not visible
                    or guard.f_locals.get('portfolio_snapshot') is not portfolio
                    or guard.f_locals['portfolio'] is portfolio):
                raise ValueError('strategy_guard_copy_identity_conflict')
            limit = self.first + len(self.rows)
            if limit >= self.last:
                raise ValueError('strategy_unexpected_extra_decision')
            row = check_visible_frame(visible, self.data, limit, guarded_input=guard.f_locals['data'])
            row.update(ordinal=len(self.rows) + 1, portfolio_sha256=digest(asdict(portfolio)),
                       next_execution_open=self.data.index[limit].isoformat())
            self.rows.append(row)
            self.active[id(frame)] = row
        elif event == 'return':
            row = self.active.pop(id(frame), None)
            if row is None or value is None:
                raise ValueError('strategy_callback_did_not_return_signal')
            signal = asdict(value)
            signal['action'] = value.action.value
            row['signal_sha256'] = digest(signal)

    def __enter__(self):
        if sys.getprofile() is not None:
            raise ValueError('existing_profiler_must_not_be_replaced')
        sys.setprofile(self._profile)
        return self

    def __exit__(self, kind, value, traceback):
        sys.setprofile(None)
        if kind is None and (len(self.rows) != self.last - self.first or self.active):
            raise ValueError('strategy_decision_coverage_incomplete')


def _inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('audit_source_symlink_rejected')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return result


def _runtime_key(runtime):
    if (runtime['source_identity'].get('status') not in {'CONTENT_HASHED', 'BUILD_VERIFIED'}
            or runtime['environment_verified'].get('status') != 'VERIFIED'):
        raise ValueError('audit_requires_verified_runtime')
    return dict(source=runtime['source_identity']['content_sha256'],
                environment=runtime['environment_verified'])


def _date(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('audit_timestamp_requires_timezone')
    return parsed


def _referenced_document(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('audit_amendment_reference_must_be_regular')
    raw = path.read_bytes()
    if type(expected) is not str or sha256(raw).hexdigest() != expected:
        raise ValueError('audit_amendment_reference_bytes_changed')
    return json.loads(raw)


def _check_amendment(design):
    policy = design.get('historical_price_policy')
    if (type(policy) is not dict
            or policy.get('id') != 'YAHOO_QUOTE_POST_WINDOW_DIVIDEND_RECONCILIATION_V1'
            or policy.get('strategy_fields') != list(FIELDS)
            or policy.get('adjusted_close_used_for_strategy') is not False
            or policy.get('events_used_for_strategy') is not False
            or type(policy.get('max_adjusted_close_error_float32_ulps')) is not int
            or policy['max_adjusted_close_error_float32_ulps'] != 2
            or any(policy.get(key) is not True for key in (
                'require_no_in_window_actions', 'require_no_splits_through_source_acquisition',
                'require_all_post_window_adjustments_explained', 'require_close_and_adjusted_exact_float32_values',
                'verify_entire_context_to_source_latest_complete', 'require_last_event_following_factor_one'))):
        raise ValueError('audit_historical_price_policy_conflict')
    amendment = design.get('amends')
    if type(amendment) is not dict or not amendment.get('reason'):
        raise ValueError('audit_amendment_requires_original_design_and_stop')
    original = _referenced_document(amendment['original_design_path'], amendment['original_design_sha256'])
    stopped = _referenced_document(amendment['stopped_receipt_path'], amendment['stopped_receipt_sha256'])
    diagnostic = _referenced_document(amendment['diagnostic_path'], amendment['diagnostic_sha256'])
    if (original.get('schema_version') != 'fixed-month-replay-design-v1'
            or original.get('plan_hash') != digest({k: v for k, v in original.items() if k != 'plan_hash'})
            or amendment.get('original_plan_hash') != original['plan_hash']
            or stopped.get('schema_version') != 'sealed-month-replay-preparation-v1'
            or stopped.get('status') != 'STOPPED' or stopped.get('economic_runs') != 0
            or stopped.get('plan_hash') != original['plan_hash']
            or set(stopped.get('symbols', {})) != set(original['sources'])
            or any(row.get('status') != 'STOPPED' or row.get('reason') != 'SOURCE_ADJUSTED_RAW_MISMATCH'
                   for row in stopped['symbols'].values())
            or diagnostic.get('plan_hash') != original['plan_hash']
            or diagnostic.get('read_only') is not True or diagnostic.get('economic_runs') != 0
            or diagnostic.get('new_source_requests') != 0):
        raise ValueError('audit_amendment_original_design_or_stop_identity_conflict')
    allowed = {'schema_version', 'recorded_at', 'execution_policy_notes', 'plan_hash'}
    if (any(design.get(key) != value for key, value in original.items() if key not in allowed)
            or set(design) - set(original) - {'amends', 'historical_price_policy', 'execution_policy_notes'}):
        raise ValueError('audit_amendment_changed_frozen_parameters_dates_or_sources')
    if not (_date(original['recorded_at']) <= _date(stopped['prepared_at']) < _date(design['recorded_at'])):
        raise ValueError('audit_amendment_order_conflict')


def check_design(design, manifest, report, snapshot, current, started):
    if (design.get('schema_version') not in {'fixed-month-replay-design-v1', 'fixed-month-replay-design-v2', HOLDOUT_SCHEMA}
            or design.get('plan_hash') != digest({k: v for k, v in design.items() if k != 'plan_hash'})):
        raise ValueError('audit_design_identity_invalid')
    if design['schema_version'] == 'fixed-month-replay-design-v2':
        _check_amendment(design)
    if design['schema_version'] == HOLDOUT_SCHEMA and design.get('mode') != HOLDOUT_MODE:
        raise ValueError('audit_holdout_mode_conflict')
    if _date(design['recorded_at']) > _date(started['started_at']):
        raise ValueError('audit_design_postdates_formal_run')
    if manifest['task']['strategy'] != 'price.dual_ma@1':
        raise ValueError('audit_only_registered_dual_ma_supported')
    spec = report['spec']
    for key in ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy',
                'execution_policy', 'quantity_policy', 'purpose'):
        if spec[key] != design[key]:
            raise ValueError('audit_frozen_design_spec_conflict:' + key)
    if (spec['score_start_session'] != design['score_start'] or spec['score_end_session'] != design['score_end']
            or design.get('cost_multipliers') != [1, 2, 3] or design.get('benchmarks') != ['cash', 'buy_and_hold']):
        raise ValueError('audit_frozen_design_window_or_matrix_conflict')
    symbol = report['dataset']['security']['symbol']
    if type(design.get('sources')) is not dict or symbol not in design['sources']:
        raise ValueError('audit_frozen_design_symbol_conflict')
    dates = [row['date'] for row in snapshot.document['sessions']]
    first, last = dates.index(design['score_start']), dates.index(design['score_end']) + 1
    if (dates[0] != design['context_start'] or first != design['context_sessions'] or last != len(dates)
            or dates[:first] != design['context_dates'] or dates[first:last] != design['score_sessions']):
        raise ValueError('audit_frozen_design_context_conflict')
    if (_runtime_key(manifest['runtime']) != _runtime_key(current)
            or current['source_identity']['content_sha256'] != design['execution_runtime_source_sha256']):
        raise ValueError('audit_requires_same_frozen_verified_runtime')
    return first, last


def _holdout_protocol_checker():
    """Load only the adjacent, separately frozen repository preparation tool."""
    path = Path(__file__).with_name('prepare_blind_holdout.py')
    spec = importlib.util.spec_from_file_location('prefix_holdout_preparation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_design_protocol


def _bound_file(base, reference, expected):
    path = Path(reference)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    if (not resolved.is_relative_to(base.resolve()) or path.is_symlink() or not path.is_file()
            or any(parent.is_symlink() for parent in path.parents)):
        raise ValueError('audit_holdout_artifact_outside_receipt_directory')
    raw = path.read_bytes()
    if type(expected) is not str or sha256(raw).hexdigest() != expected:
        raise ValueError('audit_holdout_artifact_bytes_changed')
    return resolved, raw


def _git_output(repository, *args):
    return subprocess.check_output(['git', *args], cwd=repository, stderr=subprocess.PIPE)


def _check_holdout_bindings(design, raw, design_path, preparation_path, preparation_sha256,
                            report, snapshot, started):
    if preparation_path is None or not preparation_sha256:
        raise ValueError('audit_holdout_requires_preparation_and_sha256')
    checked = _holdout_protocol_checker()(design_path, expected_sha256=sha256(raw).hexdigest())
    if checked != design:
        raise ValueError('audit_holdout_protocol_validator_identity_conflict')
    preparation_path = Path(preparation_path).resolve()
    fixed_output = Path(design['acquisition_output_path'])
    if not fixed_output.is_absolute() or preparation_path.parent != fixed_output.resolve():
        raise ValueError('audit_holdout_preparation_outside_frozen_destination')
    prep = _referenced_document(preparation_path, preparation_sha256)
    if (prep.get('schema_version') != 'blind-holdout-preparation-v1' or prep.get('status') != 'READY'
            or prep.get('plan_hash') != design['plan_hash'] or prep.get('design_sha256') != sha256(raw).hexdigest()
            or set(prep.get('symbols', {})) != set(design['sources'])
            or any(row.get('status') != 'READY' for row in prep['symbols'].values())):
        raise ValueError('audit_holdout_preparation_identity_conflict')
    acquisition_path = Path(prep['acquisition_path'])
    if not acquisition_path.is_absolute():
        acquisition_path = preparation_path.parent / acquisition_path
    acquisition_path = acquisition_path.resolve()
    if acquisition_path.parent != preparation_path.parent:
        raise ValueError('audit_holdout_acquisition_outside_preparation_directory')
    acquisition = _referenced_document(acquisition_path, prep['acquisition_sha256'])
    commit = prep.get('commit')
    if (type(commit) is not str or not re.fullmatch(r'[0-9a-f]{40}', commit)
            or acquisition.get('schema_version') != 'blind-holdout-acquisition-v1'
            or acquisition.get('status') != 'ACQUIRED' or acquisition.get('commit') != commit
            or acquisition.get('plan_hash') != design['plan_hash']
            or acquisition.get('design_sha256') != sha256(raw).hexdigest()
            or set(acquisition.get('sources', {})) != set(design['sources'])):
        raise ValueError('audit_holdout_acquisition_identity_conflict')
    repository = Path(design['repository_path']).resolve()
    protocol_relative = Path(design['protocol_repo_path'])
    if protocol_relative.is_absolute() or '..' in protocol_relative.parts:
        raise ValueError('audit_holdout_protocol_repository_path_invalid')
    if _git_output(repository, 'show', commit + ':' + protocol_relative.as_posix()) != raw:
        raise ValueError('audit_holdout_preacquisition_commit_bytes_conflict')
    commit_at = _date(_git_output(repository, 'show', '-s', '--format=%cI', commit).decode().strip())
    if commit_at != _date(acquisition['commit_time']):
        raise ValueError('audit_holdout_commit_time_conflict')
    frozen_at = _date(design['recorded_at'])
    prepared_at = _date(prep['prepared_at'])
    if not (frozen_at <= commit_at < _date(acquisition['started_at'])
            <= _date(acquisition['completed_at']) <= prepared_at < _date(started['started_at'])):
        raise ValueError('audit_holdout_preparation_chronology_conflict')
    if type(prep.get('files')) is not dict or not prep['files']:
        raise ValueError('audit_holdout_preparation_inventory_missing')
    inventory = {}
    for reference, expected in prep['files'].items():
        path, _ = _bound_file(preparation_path.parent, reference, expected)
        inventory[path] = expected
    if inventory.get(acquisition_path) != prep['acquisition_sha256']:
        raise ValueError('audit_holdout_acquisition_missing_from_inventory')
    sources = {}
    for symbol, source in acquisition['sources'].items():
        if source.get('status') != 'ACQUIRED' or source.get('reference') != design['sources'][symbol]['reference']:
            raise ValueError('audit_holdout_source_identity_conflict')
        requested_at, retrieved_at = _date(source['request_started_at']), _date(source['retrieved_at'])
        if not (commit_at < _date(acquisition['started_at']) <= requested_at <= retrieved_at
                <= _date(acquisition['completed_at'])):
            raise ValueError('audit_holdout_source_predates_commitment')
        _bound_file(acquisition_path.parent, source['raw_path'], source['raw_sha256'])
        attempts = source.get('attempts')
        policy = design['acquisition_policy']
        maximum = policy['max_requests_per_symbol']
        if (type(maximum) is not int or type(attempts) is not list or not 1 <= len(attempts) <= maximum
                or attempts[-1].get('status') != 'ACQUIRED'):
            raise ValueError('audit_holdout_source_attempt_history_missing')
        previous = _date(acquisition['started_at'])
        for ordinal, attempt in enumerate(attempts, 1):
            begin, end = _date(attempt['request_started_at']), _date(attempt['completed_at'])
            earliest = previous + (timedelta(seconds=policy['retry_delay_seconds']) if ordinal > 1 else timedelta())
            if (attempt.get('number') != ordinal or attempt.get('reference') != source['reference']
                    or not (earliest <= begin <= end <= retrieved_at)):
                raise ValueError('audit_holdout_source_attempt_chronology_conflict')
            if ordinal < len(attempts) and (attempt.get('status') != 'FAILED'
                    or attempt.get('outcome_known') is not True or attempt.get('successful_response_received') is not False
                    or attempt.get('reason') not in policy['retry_reason_codes'] or attempt.get('response_status') == 200):
                raise ValueError('audit_holdout_retry_after_disallowed_or_successful_response')
            previous = end
            if 'raw_path' in attempt or 'raw_sha256' in attempt:
                _bound_file(acquisition_path.parent, attempt['raw_path'], attempt['raw_sha256'])
        last = attempts[-1]
        if (last['request_started_at'] != source['request_started_at'] or last['completed_at'] != source['retrieved_at']
                or last.get('raw_sha256') != source['raw_sha256'] or last.get('raw_path') != source['raw_path']
                or last.get('response_status') != 200):
            raise ValueError('audit_holdout_selected_source_attempt_conflict')
        sources[symbol] = dict(request_started_at=source['request_started_at'], retrieved_at=source['retrieved_at'],
                               raw_sha256=source['raw_sha256'], attempts=len(attempts))
    symbol = report['dataset']['security']['symbol']
    prepared = prep['symbols'][symbol]
    if prepared.get('status') != 'READY' or prepared.get('snapshot_id') != snapshot.snapshot_id:
        raise ValueError('audit_holdout_prepared_snapshot_identity_conflict')
    snapshot_path, snapshot_raw = _bound_file(preparation_path.parent, prepared['snapshot_path'], prepared['snapshot_sha256'])
    spec_path, spec_raw = _bound_file(preparation_path.parent, prepared['spec_path'], prepared['spec_sha256'])
    if (inventory.get(snapshot_path) != prepared['snapshot_sha256'] or inventory.get(spec_path) != prepared['spec_sha256']
            or json.loads(snapshot_raw) != snapshot.document):
        raise ValueError('audit_holdout_saved_snapshot_differs_from_preparation')
    prepared_spec = json.loads(spec_raw)
    for key in ('snapshot_id', 'strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy',
                'execution_policy', 'quantity_policy', 'purpose', 'score_start_session', 'score_end_session'):
        if prepared_spec[key] != report['spec'][key]:
            raise ValueError('audit_holdout_prepared_spec_conflict:' + key)
    for recorded_source in (snapshot.document['security_identity']['source'], snapshot.document['corporate_actions']['source']):
        if (recorded_source['raw_sha256'] != sources[symbol]['raw_sha256']
                or recorded_source['retrieved_at'] != sources[symbol]['retrieved_at']
                or recorded_source['reference'] != design['sources'][symbol]['reference']):
            raise ValueError('audit_holdout_snapshot_source_binding_conflict')
    return dict(scope='PROJECT_HISTORICAL_HOLDOUT_PREACQUISITION',
        exposure_audit_sha256=design['exposure_audit']['sha256'], parameter_design_sha256=design['parameter_design']['sha256'],
        exposure_addendum_sha256=design['exposure_addendum']['sha256'],
        project_exposure_audit_verified=True, frozen_parameter_source_verified=True,
        protocol_commit=commit, protocol_committed_at=acquisition['commit_time'],
        preacquisition_commitment_verified=True, preparation_sha256=preparation_sha256,
        acquisition_sha256=prep['acquisition_sha256'], prepared_at=prep['prepared_at'],
        prepared_snapshot_matches_formal_run=True, frozen_economics_match_preparation=True, sources=sources,
        chronological_oos=False, historical_point_in_time_source=False,
        global_unseen_data_proven=False, callback_observer_alone_proves_blind_holdout=False)


def _write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        stream.write('\n')


def verify_saved_run(run_dir, *, design_path, design_sha256, output_path,
                     preparation_path=None, preparation_sha256=None):
    root, design_path, output = Path(run_dir).resolve(), Path(design_path).resolve(), Path(output_path).resolve()
    if output.is_relative_to(root) or output == design_path:
        raise ValueError('audit_output_cannot_modify_run_or_design')
    started_path = output.with_name(output.name + '.started.json')
    if output.exists() or started_path.exists():
        raise ValueError('audit_destination_exists_no_automatic_recalculation')
    raw = design_path.read_bytes()
    if sha256(raw).hexdigest() != design_sha256:
        raise ValueError('audit_design_bytes_changed')
    design = json.loads(raw)
    before = _inventory(root)
    manifest, report, snapshot = verify_run(root)
    current = build_runtime_provenance()
    started = read_document(root / 'started.json')
    first, last = check_design(design, manifest, report, snapshot, current, started)
    blinding_evidence = None
    if design['schema_version'] == HOLDOUT_SCHEMA:
        blinding_evidence = _check_holdout_bindings(design, raw, design_path, preparation_path,
            preparation_sha256, report, snapshot, started)
    data = snapshot.frame()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_new(started_path, dict(schema_version=SCHEMA, run_id=manifest['run_id'],
        started_at=datetime.now(timezone.utc).isoformat(), design_sha256=design_sha256,
        intended_additional_validation_calculations=1, automatic_retry=False))
    try:
        with PrefixObserver(data, first, last) as observer:
            recalculated = run_strategy(manifest['task']['strategy'], snapshot, report['spec'],
                                        report.get('event_context')).document
        for row in observer.rows:
            session = snapshot.document['sessions'][row['visible_rows'] - 1]
            available = _date(session['close_utc']) + timedelta(seconds=snapshot.document['bar_availability_lag_seconds'])
            if available >= _date(row['next_execution_open']):
                raise ValueError('audit_decision_not_available_before_execution_open')
            row['visible_last_session_close'] = session['close_utc']
            row['decision_available_at'] = available.isoformat()
        if recalculated['result'] != report['result']:
            raise ValueError('audit_observed_economic_result_differs_from_formal_report')
        if (recalculated['spec'] != report['spec'] or recalculated['dataset'] != report['dataset']
                or _runtime_key(current) != _runtime_key(build_runtime_provenance())
                or _runtime_key(current) != _runtime_key(recalculated['provenance'])):
            raise ValueError('audit_runtime_or_input_changed_during_verification')
        if before != _inventory(root) or design_path.read_bytes() != raw:
            raise ValueError('audit_original_artifacts_changed')
        if blinding_evidence is not None and blinding_evidence != _check_holdout_bindings(
                design, raw, design_path, preparation_path, preparation_sha256, report, snapshot, started):
            raise ValueError('audit_holdout_bindings_changed_during_verification')
        result = dict(schema_version=SCHEMA, status='PASS', recorded_at=datetime.now(timezone.utc).isoformat(),
            run_id=manifest['run_id'], report_hash=report['report_hash'], snapshot_id=snapshot.snapshot_id,
            design_sha256=design_sha256, plan_hash=design['plan_hash'],
            runtime=_runtime_key(current), original_file_sha256=before,
            original_files_unchanged=True, economic_result_exact_match=True,
            economic_result_sha256=digest(report['result']), additional_validation_calculations=1,
            new_product_runs=0, blind_holdout_proven=False, os_sandbox=False,
            trace=observer.rows, trace_sha256=digest(observer.rows), limitations=LIMITATIONS)
        if blinding_evidence is not None:
            result['blinding_evidence'] = blinding_evidence
        _write_new(output, result)
        return result
    except BaseException as exc:
        _write_new(output.with_name(output.name + '.failed.json'), dict(schema_version=SCHEMA,
            status='FAILED_VERIFICATION_RETAINED', error_type=type(exc).__name__, error=str(exc),
            automatic_retry=False, original_files_unchanged=before == _inventory(root)))
        raise


def synthetic_check():
    """One baseline and one deliberately different future; no market input."""
    index = pd.bdate_range('2024-01-02', periods=48, tz='UTC')
    close = np.array([100 + ((i // 6) % 2 * 2 - 1) * (i % 6) for i in range(48)], dtype=float)
    data = pd.DataFrame(dict(open=close, high=close + 1, low=close - 1, close=close, volume=10000), index=index)
    first, cut, last = 12, 29, len(data)
    params = dict(fast_window=5, slow_window=10, position_pct=.25, stop_loss_pct=.03, take_profit_pct=.06)
    config = BotConfig(market='stock', symbol='SYNTHETIC', timeframe='1d', initial_cash=10000,
        strategy=StrategyConfig(name='dual_ma', params=params),
        risk=RiskConfig(max_position_pct=.25, max_single_loss_pct=.03, max_daily_loss_pct=1., min_cash_pct=0., max_leverage=1.),
        execution=ExecutionConfig(fee_rate=.0008, slippage_pct=.0005))
    def execute(frame):
        engine = BacktestEngine(config, build_strategy('dual_ma', params), RiskManager(config.risk))
        with PrefixObserver(frame, first, last) as observer:
            result = engine.run(frame, score_start=first, score_end=last).to_dict()
        return result, observer.rows
    original, trace = execute(data)
    changed = data.copy(deep=True)
    changed.loc[changed.index[cut]:, list(FIELDS[:4])] *= 4
    changed.loc[changed.index[cut]:, 'volume'] *= 3
    perturbed, other_trace = execute(changed)
    cutoff = index[cut]
    def prefix(rows):
        return [r for r in rows if pd.Timestamp(r.get('time', r.get('fill_time'))) < cutoff]
    comparisons = {key: prefix(original[key]) == prefix(perturbed[key]) for key in ('signals', 'fills', 'equity_curve')}
    # A decision at the previous close can execute on the altered bar. The
    # prefix comparison excludes that future fill/equity, not its past signal.
    trace_same = [r for r in trace if r['visible_rows'] <= cut] == [r for r in other_trace if r['visible_rows'] <= cut]
    if not all(comparisons.values()) or not trace_same:
        raise ValueError('synthetic_future_perturbation_changed_past')
    if not prefix(original['fills']):
        raise ValueError('synthetic_probe_requires_actual_fills')
    if original['fills'] == perturbed['fills'] and original['equity_curve'] == perturbed['equity_curve']:
        raise ValueError('synthetic_future_perturbation_must_change_future_economics')
    return dict(schema_version=SCHEMA, status='PASS', evidence_kind='SYNTHETIC_REGRESSION',
        baseline_and_perturbed_calculations=2, past_prefix_equal=comparisons,
        past_callback_trace_equal=trace_same, baseline_fill_count=len(original['fills']),
        compared_past_fill_count=len(prefix(original['fills'])), future_economics_changed=True,
        future_changed_from=cutoff.isoformat(), trace=trace, trace_sha256=digest(trace), limitations=LIMITATIONS)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic', action='store_true')
    mode.add_argument('--run', type=Path)
    parser.add_argument('--design', type=Path)
    parser.add_argument('--design-sha256')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--preparation-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.synthetic:
        if args.output.exists():
            raise ValueError('audit_destination_exists')
        result = synthetic_check()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _write_new(args.output, result)
    else:
        if not args.design or not args.design_sha256:
            parser.error('--run requires --design and --design-sha256')
        result = verify_saved_run(args.run, design_path=args.design, design_sha256=args.design_sha256, output_path=args.output,
            preparation_path=args.preparation, preparation_sha256=args.preparation_sha256)
    print(json.dumps({k: result[k] for k in ('schema_version', 'status')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
