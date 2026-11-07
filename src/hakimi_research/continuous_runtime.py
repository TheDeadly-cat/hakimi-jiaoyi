"""Incremental, offline US daily research over the canonical shared ledger.

No provider, broker, background worker or execution authority lives here. A
completed session is one deterministic economic step. Requests and their exact
snapshots are committed atomically by shared_account, including blocked attempts.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .config import RiskConfig
from .documents import digest
from .equity_dataset import EquitySnapshot, verify_equity_snapshot
from .equity_event_context import EventSchedulePolicy
from .models import Action, Portfolio, Signal
from .offline_app import check_task
from .risk import RiskManager
from .shared_account import (CONTINUOUS_SCHEMA, COMPETITION, _clock, _d, _equity,
    _invariants, _key, _loss_allowed, _money, _reserve_one, _reserved, _slot,
    _transition, create_shared_account, describe_shared_account,
    signal_document, transact_shared_account)
from .strategies.templates import build_strategy
from .strategy_registry import definition, effective_parameters, strategy_identity
from .task_manager import _family_for_task, family_lock, read_family

SCHEMA = 'continuous-research-policy-v1'
SUPPORTED = {'price.dual_ma@1', 'price.buy_and_hold@1', 'event.earnings_schedule@1'}


def _date(value):
    if type(value) is not str or date.fromisoformat(value).isoformat() != value:
        raise ValueError('continuous_exact_session_date_required')
    return value


def _available(data, session):
    value = datetime.fromisoformat(session['close_utc'].replace('Z', '+00:00'))
    return (value + timedelta(seconds=data['bar_availability_lag_seconds'])).strftime('%Y-%m-%dT%H:%M:%SZ')


def _check_available_clocks(data):
    # Match the formal equity session engine: next-open execution needs the
    # previous completed bar before that open, including early-close/DST gaps.
    for prior, current in zip(data['sessions'], data['sessions'][1:]):
        if _available(data, prior) >= current['open_utc']:
            raise ValueError('DATA_PRIOR_BAR_UNAVAILABLE_BEFORE_NEXT_OPEN')


def _binding(context):
    semantics = deepcopy(context['semantics'])
    owner = ('family:' + semantics['management']['family_id'] if 'management' in semantics else context['task_id'])
    return dict(owner=owner, task_id=context['task_id'], semantics=semantics,
        snapshot=deepcopy(context['snapshot'].document), context=deepcopy(context['context']))


def _verify_binding(binding):
    if type(binding) is not dict or set(binding) != {'owner', 'task_id', 'semantics', 'snapshot', 'context'}:
        raise ValueError('continuous_task_binding_invalid')
    semantics = binding['semantics']; key = semantics['strategy']
    if key not in SUPPORTED or binding['task_id'] != digest(semantics) or semantics['strategy_identity'] != strategy_identity(key):
        raise ValueError('continuous_task_identity_or_strategy_not_supported')
    expected = 'family:' + semantics['management']['family_id'] if 'management' in semantics else binding['task_id']
    if binding['owner'] != expected:
        raise ValueError('continuous_task_owner_conflict')
    data = verify_equity_snapshot(binding['snapshot'])
    _check_available_clocks(data)
    from .strategy_registry import inspect_task_inputs, validate_strategy
    spec = semantics['experiment']
    checked = validate_strategy(key, spec, binding['context'])
    inspect_task_inputs(EquitySnapshot(data), checked, event_context=binding['context'])
    if spec['snapshot_id'] != data['snapshot_id'] or not data['research_admission']['allowed']:
        raise ValueError('continuous_task_input_not_admitted')
    return data


def validate_continuous_config(config):
    policy = config['continuous']
    if type(policy) is not dict or set(policy) != {'schema_version', 'start_session', 'tasks', 'pause_policy', 'clock_policy', 'initial_task_paused'}:
        raise ValueError('continuous_config_fields_invalid')
    if policy['schema_version'] != SCHEMA or policy['pause_policy'] != 'STOP_NEW_BUYS_KEEP_PROTECTION' or policy['clock_policy'] != 'COMPLETED_SESSION_OFFLINE_REPLAY':
        raise ValueError('continuous_policy_not_supported')
    start = _date(policy['start_session']); tasks = policy['tasks']
    if type(tasks) is not list or not tasks or len(tasks) > 32:
        raise ValueError('continuous_one_to_32_tasks_required')
    if config['initial_positions']:
        raise ValueError('continuous_new_account_no_legacy_position_migration')
    owners = set(); securities = set(); clocks = set()
    for binding in tasks:
        data = _verify_binding(binding); owner = binding['owner']
        if owner in owners: raise ValueError('continuous_duplicate_task_owner')
        owners.add(owner); security = data['security']['security_id']; securities.add(security)
        if data['evidence_kind'] != config['evidence_kind']:
            raise ValueError('continuous_mixed_evidence_not_supported')
        index = next((i for i, row in enumerate(data['sessions']) if row['date'] == start), None)
        if index is None or index < 1 or binding['semantics']['experiment']['score_start_session'] != start:
            raise ValueError('continuous_common_task_score_start_required')
        prior = data['sessions'][index - 1]
        clocks.add(_available(data, prior))
        if config['securities'].get(security) != dict(symbol=data['security']['symbol'], price=data['candles'][index-1][4]):
            raise ValueError('continuous_initial_marks_binding_conflict')
        if _available(data, prior) >= data['sessions'][index]['open_utc']:
            raise ValueError('continuous_seed_bar_not_available_before_open')
    if (type(policy['initial_task_paused']) is not dict or set(policy['initial_task_paused']) != owners
            or any(type(v) is not bool for v in policy['initial_task_paused'].values())):
        raise ValueError('continuous_initial_task_states_invalid')
    if securities != set(config['securities']) or len(clocks) != 1 or config['as_of'] not in clocks:
        raise ValueError('continuous_common_seed_clock_required')


def _prefix(data, through):
    return dict(rows={s['date']: digest(dict(session=s, candle=c)) for s, c in zip(data['sessions'], data['candles']) if s['date'] <= through},
        calendar={row['date']: digest(row) for row in data['calendar']['days'] if row['date'] <= through},
        security=data['security'], price_basis=data['price_basis'], lag=data['bar_availability_lag_seconds'],
        evidence_kind=data['evidence_kind'])


def initial_continuous_state(config):
    policy = config['continuous']; start = policy['start_session']; inputs = {}
    for task in policy['tasks']:
        data = task['snapshot']; index = next(i for i, s in enumerate(data['sessions']) if s['date'] == start)
        inputs[data['security']['security_id']] = _prefix(data, data['sessions'][index-1]['date'])
    return dict(schema_version='continuous-research-state-v1', last_session=None,
        last_success_at=None, last_observed_at=None, status='READY', stop_reason=None,
        inputs=inputs, task_paused=deepcopy(policy['initial_task_paused']),
        manual_task_paused={owner:False for owner in policy['initial_task_paused']},
        family_task_paused=deepcopy(policy['initial_task_paused']),
        protection={}, session_results=[], loss_halt_session=None, task_configuration_warnings={})


def create_continuous_account(directory, task_files, *, initial_cash=10000, limits, start_session=None):
    with ExitStack() as stack:
        families = sorted({str(f) for path in task_files if (f := _family_for_task(path)) is not None})
        for family in families: stack.enter_context(family_lock(family))
        tasks = []; initial_paused = {}
        for path in task_files:
            binding = _binding(check_task(path, inspect_only=True))
            family = _family_for_task(path)
            initial_paused[binding['owner']] = (read_family(family)['state'] if family else binding['semantics']['state']) == 'PAUSED'
            tasks.append(binding)
        if not tasks: raise ValueError('continuous_tasks_required')
        start = start_session or tasks[0]['semantics']['experiment']['score_start_session']
        securities = {}; clocks = []
        for task in tasks:
            data = _verify_binding(task)
            index = next((i for i, s in enumerate(data['sessions']) if s['date'] == start), None)
            if index is None or index < 1: raise ValueError('continuous_seed_session_missing')
            security = data['security']['security_id']
            row = dict(symbol=data['security']['symbol'], price=data['candles'][index-1][4])
            if security in securities and securities[security] != row: raise ValueError('continuous_shared_security_price_conflict')
            securities[security] = row; clocks.append(_available(data, data['sessions'][index-1]))
        config = dict(schema_version=CONTINUOUS_SCHEMA, evidence_kind=tasks[0]['snapshot']['evidence_kind'], currency='USD',
            initial_cash=initial_cash, initial_positions=[], securities=securities, as_of=clocks[0], limits=limits,
            competition=COMPETITION, continuous=dict(schema_version=SCHEMA, start_session=start, tasks=tasks,
                pause_policy='STOP_NEW_BUYS_KEEP_PROTECTION', clock_policy='COMPLETED_SESSION_OFFLINE_REPLAY', initial_task_paused=initial_paused))
        create_shared_account(directory, config)
        return describe_continuous_account(directory)


def _snapshots(previous, snapshots, config, through, observed):
    if type(snapshots) is not dict or set(snapshots) != set(config['securities']):
        raise ValueError('DATA_MISSING:complete_security_snapshot_set_required')
    data = {}
    for security, raw in snapshots.items():
        value = verify_equity_snapshot(raw)
        _check_available_clocks(value)
        if value['security']['security_id'] != security or not value['research_admission']['allowed']:
            raise ValueError('DATA_NOT_ADMITTED:' + security)
        if datetime.fromisoformat(value['retrieved_at'].replace('Z', '+00:00')) > datetime.fromisoformat(observed.replace('Z', '+00:00')):
            raise ValueError('DATA_FUTURE_RECEIPT:' + security)
        old = previous['continuous']['inputs'][security]
        new = _prefix(value, through)
        for key in ['security', 'price_basis', 'lag', 'evidence_kind']:
            if old[key] != new[key]: raise ValueError('DATA_IDENTITY_REVISED:' + security + ':' + key)
        for key in ['rows', 'calendar']:
            for day, identity in old[key].items():
                if new[key].get(day) != identity:
                    raise ValueError('DATA_CONSUMED_PREFIX_REVISED_OR_MISSING:' + security + ':' + day)
        if through > value['calendar']['coverage_end']:
            raise ValueError('DATA_STALE_OR_MISSING_COVERAGE:' + security)
        data[security] = value
    # A shared clock never manufactures prices for a missing member.
    schedules = [tuple((s['date'], s['open_utc'], s['close_utc']) for s in value['sessions']
        if config['continuous']['start_session'] <= s['date'] <= through) for value in data.values()]
    if any(s != schedules[0] for s in schedules[1:]):
        raise ValueError('DATA_CALENDAR_ALIGNMENT_MISSING')
    for value in data.values():
        for session in value['sessions']:
            if session['date'] <= through and _available(value, session) > observed:
                raise ValueError('DATA_NOT_YET_AVAILABLE:' + session['date'])
    return data


def _portfolio(state, owner, security):
    p = state['positions'].get(_slot(owner, security), {})
    return Portfolio(cash=float(_d(state['cash']) - _reserved(state)), position_qty=float(p.get('quantity', 0)),
        avg_entry_price=float(p.get('avg_entry_price', 0)), entry_fees=float(p.get('entry_fees', 0)),
        realized_pnl=float(p.get('realized_pnl', 0)))


def _proposal(task, signal, signal_at, execution_at, state, config, basis, reviews):
    semantics = task['semantics']; spec = semantics['experiment']; security = task['snapshot']['security']['security_id']
    identity = dict(strategy_identity=semantics['strategy_identity'], parameters=effective_parameters(definition(semantics['strategy'])['engine_strategy'], spec['strategy']['params']),
        security_id=security, signal_at=signal_at, execution_at=execution_at, action=signal.action.value)
    if signal.action in {Action.SELL, Action.EXIT}:
        identity = dict(schema_version='continuous-owned-reduction-v1', owner=task['owner'], security_id=security,
            signal_at=signal_at, execution_at=execution_at, phase=basis)
    return dict(owner=task['owner'], strategy=semantics['strategy'], security_id=security,
        signal=signal_document(signal), signal_at=signal_at, execution_at=execution_at,
        risk=deepcopy(spec['risk']), fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'],
        source=dict(kind='CONTINUOUS_REGISTERED_SIGNAL', evidence_kind=config['evidence_kind'],
            task_id=task['task_id'], opportunity_inputs=identity, basis=basis, research_review=reviews), opportunity_id=digest(identity))


def _execute(state, config, task, signal, signal_at, at, price, basis, reviews=None):
    """Detached canonical admission/settlement; price basis is sealed in receipt."""
    security = task['snapshot']['security']['security_id']; prior_mark = state['marks'][security]
    state['marks'][security] = _money(price)
    proposal = _proposal(task, signal, signal_at, at, state, config, basis, reviews or {})
    judged = _reserve_one(state, config, proposal)
    if judged['status'] == 'RESERVED':
        settled, next_state = _transition(state, dict(kind='SETTLE', at=at, payload=dict(intent_id=judged['intent_id'])), config, 'internal-continuous-phase')
        state.clear(); state.update(next_state)
        judged = {**judged, 'settlement': settled}
        if settled['status'] == 'SETTLED' and signal.action == Action.BUY and task['semantics']['strategy'] != 'price.buy_and_hold@1':
            stop = RiskManager(RiskConfig(**task['semantics']['experiment']['risk'])).effective_stop_loss(signal.stop_loss_pct)
            state['continuous']['protection'][task['owner']] = dict(stop_loss_pct=stop, take_profit_pct=signal.take_profit_pct)
    state['marks'][security] = prior_mark
    return dict(owner=task['owner'], security_id=security, basis=basis, signal=signal_document(signal),
        signal_at=signal_at, execution_at=at, reference_price=price, decision=judged, research_review=reviews or {})


def _protection(state, task, candle, opening_only=False):
    security = task['snapshot']['security']['security_id']; p = _portfolio(state, task['owner'], security)
    rule = state['continuous']['protection'].get(task['owner'])
    if p.position_qty <= 0 or not rule: return None
    opening, high, low = candle[1:4]
    stop = p.avg_entry_price * (1 - rule['stop_loss_pct']) if rule['stop_loss_pct'] else 0
    target = p.avg_entry_price * (1 + rule['take_profit_pct']) if rule['take_profit_pct'] else 0
    if stop and opening <= stop: return opening, 'GAP_OPEN_STOP'
    if target and opening >= target: return target, 'OPEN_TARGET'
    if opening_only: return None
    if stop and low <= stop: return stop, 'INTRABAR_STOP_FIRST' if target and high >= target else 'INTRABAR_STOP'
    if target and high >= target: return target, 'INTRABAR_TARGET'
    return None


def _day(state, config, data, day):
    tasks = config['continuous']['tasks']; records = []; first = next(iter(data.values()))
    session = next(s for s in first['sessions'] if s['date'] == day); opening = session['open_utc']; closing = session['close_utc']
    previous_close_equity = _equity(state)
    state.update(current_at=opening, marks_at=opening, day=day, day_start_equity=str(previous_close_equity))
    indices = {security: next(i for i, s in enumerate(value['sessions']) if s['date'] == day) for security, value in data.items()}
    state['marks'] = {security: _money(value['candles'][indices[security]][1]) for security, value in data.items()}
    if not _loss_allowed(state, config): state['loss_halted'] = True
    # All existing-position opening protections precede all new entries.
    protected = set()
    for task in tasks:
        security = task['snapshot']['security']['security_id']; i = indices[security]; value = data[security]
        protection = _protection(state, task, value['candles'][i], opening_only=True)
        if protection:
            price, basis = protection; signal_at = _available(value, value['sessions'][i-1])
            records.append(_execute(state, config, task, Signal.exit(basis), signal_at, opening, price, basis))
            protected.add(task['owner'])
    for task in tasks:
        if task['owner'] in protected: continue
        semantics = task['semantics']; key = semantics['strategy']; spec = semantics['experiment']
        security = task['snapshot']['security']['security_id']; value = data[security]; i = indices[security]
        signal_at = _available(value, value['sessions'][i-1]); reviews = {}
        if signal_at >= opening:
            raise ValueError('DATA_PRIOR_BAR_UNAVAILABLE_BEFORE_NEXT_OPEN')
        if key == 'price.buy_and_hold@1' and day != config['continuous']['start_session']:
            signal = Signal.hold('BENCHMARK_SINGLE_INITIAL_OPPORTUNITY')
        else:
            model = build_strategy(definition(key)['engine_strategy'], spec['strategy']['params'])
            signal = model.generate_signal(EquitySnapshot(value).frame().iloc[:i], _portfolio(state, task['owner'], security))
            if definition(key)['event_rule']:
                policy = EventSchedulePolicy(task['context'], rule=definition(key)['event_rule'], security_id=security, purpose=spec['purpose'])
                signal, reviews['decision'] = policy.review(signal, as_of=signal_at, execution_time=opening, execution_session=day, stage='DECISION')
                signal, reviews['execution'] = policy.review(signal, as_of=opening, execution_time=opening, execution_session=day, stage='EXECUTION')
        if state['continuous']['task_paused'][task['owner']] and signal.action == Action.BUY:
            signal = Signal.hold('TASK_PAUSED_STOP_NEW_BUYS_KEEP_PROTECTION')
        records.append(_execute(state, config, task, signal, signal_at, opening, value['candles'][i][1], 'NEXT_SESSION_OPEN', reviews))
    # Intraday order is unknowable from daily OHLC: stop wins if both hit.
    state.update(current_at=closing, marks_at=closing)
    for task in tasks:
        if task['owner'] in protected: continue
        security = task['snapshot']['security']['security_id']; candle = data[security]['candles'][indices[security]]
        protection = _protection(state, task, candle)
        if protection:
            price, basis = protection
            records.append(_execute(state, config, task, Signal.exit(basis), opening, closing, price, basis))
    state['marks'] = {security: _money(value['candles'][indices[security]][4]) for security, value in data.items()}
    if not _loss_allowed(state, config): state['loss_halted'] = True
    if state['loss_halted'] and state['continuous']['loss_halt_session'] is None:
        state['continuous']['loss_halt_session'] = day
    available = max(_available(value, value['sessions'][indices[security]]) for security, value in data.items())
    state.update(current_at=available, marks_at=available)
    state['continuous'].update(last_session=day, last_success_at=available)
    result = dict(session=day, available_at=available, decisions=records, equity=str(_equity(state)),
        cash=state['cash'], positions=deepcopy(state['positions']), loss_halted=state['loss_halted'])
    state['continuous']['session_results'].append(result)
    _invariants(state)
    return result


def continuous_transition(previous, request, config, head):
    state = deepcopy(previous); runtime = state['continuous']; kind = request['kind']; payload = request['payload']; observed = _clock(request['at'])
    if kind == 'CONTINUOUS_TASK_STATE':
        if set(payload) != {'owner', 'paused'} or payload['owner'] not in runtime['task_paused'] or type(payload['paused']) is not bool:
            raise ValueError('continuous_task_pause_fields_invalid')
        if observed != state['current_at']: raise ValueError('continuous_control_requires_current_clock')
        if not payload['paused'] and payload['owner'] in runtime['task_configuration_warnings']:
            raise ValueError('continuous_restore_bound_task_configuration_before_unpause')
        runtime['manual_task_paused'][payload['owner']] = payload['paused']
        _effective_pauses(runtime)
        return dict(status='TASK_STATE_RECORDED', pause_policy='STOP_NEW_BUYS_KEEP_PROTECTION'), state
    if kind == 'CONTINUOUS_RESET_LOSS':
        if set(payload) != {'expected_head'} or payload['expected_head'] != head or observed != state['current_at']:
            raise ValueError('continuous_reset_requires_current_head_and_clock')
        halted = runtime['loss_halt_session']
        if not halted or not runtime['last_session'] or runtime['last_session'] <= halted:
            raise ValueError('continuous_loss_reset_requires_later_completed_session')
        state.update(loss_halted=False, day_start_equity=str(_equity(state)))
        runtime['loss_halt_session'] = None
        return dict(status='LOSS_RESET', manual_pause_preserved=state['paused']), state
    if kind != 'CONTINUOUS_ADVANCE' or set(payload) != {'snapshots', 'through', 'task_states', 'task_configuration_warnings'}:
        raise ValueError('continuous_request_fields_invalid')
    through = _date(payload['through'])
    if runtime['last_observed_at'] and observed < runtime['last_observed_at']:
        raise ValueError('continuous_observation_clock_cannot_move_backwards')
    if runtime['last_session'] and through < runtime['last_session']:
        raise ValueError('continuous_cursor_cannot_move_backwards')
    states = payload['task_states']
    if type(states) is not dict or any(owner not in runtime['task_paused'] or type(paused) is not bool for owner, paused in states.items()):
        raise ValueError('continuous_task_states_invalid')
    warnings = payload['task_configuration_warnings']
    if type(warnings) is not dict or any(owner not in states or states[owner] is not True
            or reason not in {'BOUND_TASK_REVISION_CHANGED_STOP_NEW_BUYS_KEEP_OLD_PROTECTION', 'TASK_STATE_UNAVAILABLE_STOP_NEW_BUYS_KEEP_PROTECTION'} for owner, reason in warnings.items()):
        raise ValueError('continuous_task_configuration_warning_invalid')
    try:
        data = _snapshots(state, payload['snapshots'], config, through, observed)
    except ValueError as exc:
        runtime.update(status='BLOCKED', stop_reason=str(exc), last_observed_at=observed)
        return dict(status='BLOCKED', reason=str(exc), protection_status='NOT_COMPUTABLE_FOR_MISSING_OR_REVISED_DATA',
            last_success_at=runtime['last_success_at'], processed_sessions=[]), state
    runtime['family_task_paused'].update(states)
    for owner in states: runtime['task_configuration_warnings'].pop(owner, None)
    runtime['task_configuration_warnings'].update(warnings)
    _effective_pauses(runtime)
    sessions = [s['date'] for s in next(iter(data.values()))['sessions'] if config['continuous']['start_session'] <= s['date'] <= through
        and (runtime['last_session'] is None or s['date'] > runtime['last_session'])]
    results = [_day(state, config, data, day) for day in sessions]
    runtime = state['continuous']
    runtime['inputs'] = {security: _prefix(value, through) for security, value in data.items()}
    status = 'LOSS_HALTED' if state['loss_halted'] else 'PAUSED_NEW_ENTRIES' if state['paused'] or all(runtime['task_paused'].values()) else 'CURRENT'
    runtime.update(last_observed_at=observed, status=status, stop_reason='GLOBAL_DAILY_LOSS_HALTED' if state['loss_halted'] else None)
    return dict(status=status if results else 'NO_NEW_SESSIONS', processed_sessions=[r['session'] for r in results],
        sessions=results, last_success_at=runtime['last_success_at']), state


def _effective_pauses(runtime):
    runtime['task_paused'] = {owner: runtime['manual_task_paused'][owner] or runtime['family_task_paused'][owner]
        or owner in runtime['task_configuration_warnings'] for owner in runtime['task_paused']}


def task_control_snapshot(directory, task_files):
    """Read under the caller's family locks; missing state is reduce-only."""
    from .shared_account import _manifest
    registered = {t['owner']:t for t in _manifest(directory)['config']['continuous']['tasks']}
    unavailable = ({owner:True for owner in registered},
        {owner:'TASK_STATE_UNAVAILABLE_STOP_NEW_BUYS_KEEP_PROTECTION' for owner in registered})
    if task_files is None: return unavailable
    states = {}; warnings = {}
    try:
        for path in task_files:
            binding = _binding(check_task(path, inspect_only=True)); owner = binding['owner']
            if owner not in registered: return unavailable
            family = _family_for_task(path)
            states[owner] = (read_family(family)['state'] if family else binding['semantics']['state']) == 'PAUSED'
            if binding['task_id'] != registered[owner]['task_id']:
                states[owner] = True
                warnings[owner] = 'BOUND_TASK_REVISION_CHANGED_STOP_NEW_BUYS_KEEP_OLD_PROTECTION'
        if set(states) != set(registered): return unavailable
    except (ValueError, OSError):
        return unavailable
    return states, warnings


def task_family_locks(stack, task_files):
    families = set()
    for path in task_files or []:
        try:
            family = _family_for_task(path)
            if family is not None: families.add(str(family))
        except (ValueError, OSError):
            continue
    for family in sorted(families): stack.enter_context(family_lock(family))


def advance_continuous_account(directory, snapshots, *, through, observed_at, operation_id, task_files=None):
    with ExitStack() as stack:
        task_family_locks(stack, task_files)
        # A manual replay with no external family synchronization preserves the
        # account's already committed controls. A watcher always supplies a read.
        states, warnings = task_control_snapshot(directory, task_files) if task_files is not None else ({}, {})
        return transact_shared_account(directory, operation_id=operation_id, kind='CONTINUOUS_ADVANCE', at=observed_at,
            payload=dict(snapshots=snapshots, through=through, task_states=states, task_configuration_warnings=warnings))


def set_continuous_task_state(directory, owner, paused, *, operation_id):
    view = describe_continuous_account(directory)
    return transact_shared_account(directory, operation_id=operation_id, kind='CONTINUOUS_TASK_STATE',
        at=view['state']['current_at'], payload=dict(owner=owner, paused=paused))


def reset_continuous_loss(directory, *, operation_id, expected_head):
    view = describe_continuous_account(directory)
    return transact_shared_account(directory, operation_id=operation_id, kind='CONTINUOUS_RESET_LOSS',
        at=view['state']['current_at'], payload=dict(expected_head=expected_head))


def describe_continuous_account(directory):
    view = describe_shared_account(directory)
    if view['account_schema_version'] != CONTINUOUS_SCHEMA:
        raise ValueError('continuous_legacy_account_requires_separate_new_account_no_migration')
    view.update(schema_version='continuous-research-view-v1', engine='hakimi_research',
        continuous=deepcopy(view['state']['continuous']), clock_policy='COMPLETED_SESSION_OFFLINE_REPLAY',
        opportunity_policy='GLOBAL_BUY_OWNER_REDUCTION_PHASE',
        limitations=['Completed-daily-bar research with no market connection or broker/paper/live execution; local-file observation is separately started.',
            'Imported prices remain unverified; replay uses close plus declared lag, not proof of historical receipt.',
            'Action-free US common-stock/USD windows only. Daily OHLC uses stop-first ambiguity and fixed costs.',
            'Pause stops new buys; existing positions still receive protection when complete valid data is supplied.',
            'Loss halt persists across sessions/restarts; explicit reset requires a later completed session.',
            'Task configuration is frozen; changes require a separate account, without migrating old positions.'])
    # Control receipts change the authoritative flags without rerunning a price
    # session. Project their current meaning without rewriting journal state.
    runtime = view['continuous']; state = view['state']
    if runtime['status'] != 'BLOCKED':
        if state['loss_halted']:
            runtime.update(status='LOSS_HALTED', stop_reason='GLOBAL_DAILY_LOSS_HALTED')
        elif state['paused'] or all(runtime['task_paused'].values()):
            runtime.update(status='PAUSED_NEW_ENTRIES', stop_reason='STOP_NEW_BUYS_KEEP_PROTECTION')
        else:
            runtime.update(status='CURRENT' if runtime['last_session'] else 'READY', stop_reason=None)
    return view


def lookup_continuous_receipt(directory, operation_id):
    _key(operation_id)
    view = describe_continuous_account(directory)
    receipt = next((r for r in view['history'] if r['operation_id'] == operation_id), None)
    return dict(status='COMMITTED' if receipt else 'NOT_RECORDED', operation_id=operation_id, receipt=receipt,
        recovery_policy='Inspect the durable receipt before retrying an unknown submission; never allocate a new ID automatically.')
