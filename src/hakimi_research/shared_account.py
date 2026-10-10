"""Synthetic shared cash admission and durable reservations; no broker adapter.

One SQLite transaction owns the account decision, reservation and receipt.
The journal is the authority: restart verifies its chain and pure transitions.
Canonical risk/models/execution are used on detached, in-memory portfolios.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Context, Decimal, ROUND_CEILING, localcontext
from functools import wraps
import json
import math
from pathlib import Path
import re
import sqlite3
from tempfile import mkdtemp

from .config import RiskConfig
from .documents import canonical_bytes, digest, parse_document
from .environment import build_runtime_provenance
from .equity_research import PERMISSIONS
from .execution import ResearchExecutionSimulator
from .models import Action, Order, Portfolio, Signal
from .offline_app import _file_lock
from .risk import RiskManager, daily_loss_allowed
from .strategy_registry import definition

ACCOUNT_SCHEMA = 'synthetic-shared-account-v2'
RECEIPT_SCHEMA = 'synthetic-shared-account-receipt-v2'
LEGACY_ACCOUNT_SCHEMA = 'synthetic-shared-account-v1'
LEGACY_RECEIPT_SCHEMA = 'synthetic-shared-account-receipt-v1'
COMPETITION = 'COMMITTED_RECEIPT_FIFO_ALL_OR_NOTHING'
ZERO = '0' * 64


def _precision(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext(Context(prec=34)):
            return function(*args, **kwargs)
    return wrapped


def _number(value, *, positive=False, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value <= 0):
        raise ValueError('shared_finite_nonnegative_native_number_required')
    if maximum is not None and value > maximum:
        raise ValueError('shared_numeric_limit_exceeded')
    return float(value)


def _key(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_.:@-]{1,128}', value):
        raise ValueError('shared_identifier_invalid')
    return value


def _clock(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError('shared_exact_utc_clock_required')
    datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    return value


def _d(value):
    return Decimal(str(value))


def _money(value):
    return str(_d(value))


def _slot(owner, security):
    return digest(dict(owner=owner, security_id=security))


def _signal(document):
    fields = {'action', 'confidence', 'size_pct', 'reason', 'stop_loss_pct', 'take_profit_pct', 'metadata'}
    if type(document) is not dict or set(document) != fields:
        raise ValueError('shared_signal_fields_invalid')
    return Signal(Action(document['action']), **{k: v for k, v in document.items() if k != 'action'})


def signal_document(signal):
    if type(signal) is not Signal:
        raise ValueError('shared_exact_canonical_signal_required')
    return dict(action=signal.action.value, confidence=signal.confidence, size_pct=signal.size_pct,
        reason=signal.reason, stop_loss_pct=signal.stop_loss_pct, take_profit_pct=signal.take_profit_pct,
        metadata=deepcopy(signal.metadata))


def opportunity_identity(proposal):
    source=proposal['source']
    if source.get('kind')=='FIXED_SYNTHETIC_SIGNAL':
        if set(source)!={'kind','evidence_kind','signal_key'}:raise ValueError('shared_fixed_signal_source_fields_invalid')
        _key(source['signal_key'])
        return digest(dict(owner=proposal['owner'],strategy=proposal['strategy'],security_id=proposal['security_id'],
            action=proposal['signal']['action'],signal_key=source['signal_key'],
            signal_at=proposal['signal_at'],execution_at=proposal['execution_at']))
    if source.get('kind')=='REGISTERED_TASK_SIGNAL':return digest(source['opportunity_inputs'])
    raise ValueError('shared_signal_source_kind_unsupported')


def _symbol_aliases(config):
    symbols = [row['symbol'].upper() for row in config['securities'].values()]
    return len(symbols) != len(set(symbols))


def validate_account_config(config, *, allow_historical_symbol_aliases=False):
    fields = {'schema_version', 'evidence_kind', 'currency', 'initial_cash', 'initial_positions',
        'securities', 'as_of', 'limits', 'competition'}
    if (type(config) is not dict or set(config) != fields or type(config['schema_version']) is not str
            or config['schema_version'] not in {ACCOUNT_SCHEMA,LEGACY_ACCOUNT_SCHEMA}):
        raise ValueError('shared_account_config_fields_invalid')
    if config['evidence_kind'] != 'SYNTHETIC_TEST' or config['currency'] != 'USD' or config['competition'] != COMPETITION:
        raise ValueError('shared_only_synthetic_usd_fifo_accounts_supported')
    _number(config['initial_cash']); _clock(config['as_of'])
    limits = config['limits']
    if type(limits) is not dict or set(limits) != {'max_total_position_pct', 'max_symbol_position_pct',
            'min_cash_pct', 'max_daily_loss_pct', 'max_leverage'}:
        raise ValueError('shared_explicit_global_limits_required')
    for key in ['max_total_position_pct', 'max_symbol_position_pct', 'max_daily_loss_pct']:
        _number(limits[key], positive=True, maximum=1)
    _number(limits['min_cash_pct'], maximum=1)
    if type(limits['max_leverage']) not in (int, float) or limits['max_leverage'] != 1:
        raise ValueError('shared_cash_only_leverage_one_required')
    if type(config['securities']) is not dict or not config['securities']:
        raise ValueError('shared_explicit_synthetic_security_marks_required')
    for security, row in config['securities'].items():
        _key(security)
        if not security.startswith('SYNTHETIC:'):
            raise ValueError('shared_explicit_synthetic_security_identity_required')
        if type(row) is not dict or set(row) != {'symbol', 'price'}:
            raise ValueError('shared_security_fields_invalid')
        _key(row['symbol']); _number(row['price'], positive=True)
    if not allow_historical_symbol_aliases and _symbol_aliases(config):
        raise ValueError('shared_duplicate_symbol_aliases_not_allowed')
    if type(config['initial_positions']) is not list:
        raise ValueError('shared_initial_positions_list_required')
    slots = set()
    for row in config['initial_positions']:
        if type(row) is not dict or set(row) != {'owner', 'security_id', 'quantity', 'avg_entry_price', 'entry_fees', 'realized_pnl'}:
            raise ValueError('shared_initial_position_fields_invalid')
        owner, security = _key(row['owner']), _key(row['security_id'])
        if security not in config['securities'] or _slot(owner, security) in slots:
            raise ValueError('shared_initial_position_security_or_duplicate_invalid')
        slots.add(_slot(owner, security)); _number(row['quantity'], positive=True)
        _number(row['avg_entry_price'], positive=True); _number(row['entry_fees'])
        if type(row['realized_pnl']) not in (int, float) or not math.isfinite(row['realized_pnl']):
            raise ValueError('shared_initial_realized_pnl_invalid')
    return parse_document(canonical_bytes(config))


def demo_account_config():
    """Explicit demonstration parameters, never a trading recommendation."""
    return dict(schema_version=ACCOUNT_SCHEMA, evidence_kind='SYNTHETIC_TEST', currency='USD',
        initial_cash=10000, initial_positions=[], as_of='2024-11-08T14:30:00Z',
        securities={'SYNTHETIC:RESEARCH:TEST': dict(symbol='TEST', price=101)}, competition=COMPETITION,
        limits=dict(max_total_position_pct=1, max_symbol_position_pct=1, min_cash_pct=0,
            max_daily_loss_pct=0.05, max_leverage=1))


def _equity(state):
    return _d(state['cash']) + sum((_d(p['quantity']) * _d(state['marks'][p['security_id']])
        for p in state['positions'].values()), Decimal(0))


def _reserved(state, *, omit=None):
    return sum((_d(row['reserved_cash']) for key, row in state['intents'].items()
        if row['status'] == 'RESERVED' and key != omit), Decimal(0))


def _exposure(state, *, security=None, omit=None):
    value = sum((_d(p['quantity']) * _d(state['marks'][p['security_id']])
        for p in state['positions'].values() if security is None or p['security_id'] == security), Decimal(0))
    for key, row in state['intents'].items():
        if key != omit and row['status'] == 'RESERVED' and row['action'] == 'BUY' and (security is None or row['security_id'] == security):
            value += _d(row['quantity']) * _d(state['marks'][row['security_id']])
    return value


def _initial(config):
    state = dict(cash=_money(config['initial_cash']), positions={}, marks={k: _money(v['price']) for k, v in config['securities'].items()},
        marks_at=config['as_of'], current_at=config['as_of'], day=config['as_of'][:10], day_start_equity='0',
        intents={}, opportunities={}, paused=False, pause_reason=None, loss_halted=False)
    for row in config['initial_positions']:
        state['positions'][_slot(row['owner'], row['security_id'])] = {
            **row, **{k: _money(row[k]) for k in ['quantity', 'avg_entry_price', 'entry_fees', 'realized_pnl']}}
    state['day_start_equity'] = str(_equity(state))
    return state


def _loss_allowed(state, config):
    return daily_loss_allowed(float(_equity(state)),float(state['day_start_equity']),config['limits']['max_daily_loss_pct'])


def _buy_block(state, config, row, *, omit=None):
    if state['paused']: return 'GLOBAL_PAUSED'
    if state['loss_halted'] or not _loss_allowed(state, config): return 'GLOBAL_DAILY_LOSS_HALTED'
    cash, nav = _d(state['cash']), _equity(state)
    debit = _d(row['reserved_cash']); limits = config['limits']
    if cash - _reserved(state, omit=omit) - debit < 0: return 'INSUFFICIENT_AVAILABLE_FUNDS'
    # Fees and slippage reduce projected NAV before exposure/floor admission.
    mark_value = _d(row['quantity']) * _d(state['marks'][row['security_id']])
    pending_cost=sum((max(Decimal(0),_d(r['estimated_debit'])-_d(r['quantity'])*_d(state['marks'][r['security_id']]))
        for key,r in state['intents'].items() if key!=omit and r['status']=='RESERVED' and r['action']=='BUY'),Decimal(0))
    projected_nav = nav - pending_cost - max(Decimal(0),_d(row['estimated_debit']) - mark_value)
    if projected_nav <= 0: return 'PROJECTED_EQUITY_NOT_POSITIVE'
    if not daily_loss_allowed(float(projected_nav),float(state['day_start_equity']),limits['max_daily_loss_pct']):return 'PROJECTED_GLOBAL_DAILY_LOSS_LIMIT'
    if cash - _reserved(state, omit=omit) - debit < projected_nav * _d(limits['min_cash_pct']): return 'GLOBAL_CASH_FLOOR'
    if _exposure(state, omit=omit) + mark_value > projected_nav * _d(limits['max_total_position_pct']): return 'GLOBAL_TOTAL_POSITION_LIMIT'
    if _exposure(state, security=row['security_id'], omit=omit) + mark_value > projected_nav * _d(limits['max_symbol_position_pct']): return 'GLOBAL_SECURITY_POSITION_LIMIT'
    return None


def _proposal(value, config):
    fields = {'owner', 'strategy', 'security_id', 'signal', 'signal_at', 'execution_at', 'risk',
        'fee_rate', 'slippage_pct', 'source', 'opportunity_id'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('shared_intent_proposal_fields_invalid')
    _key(value['owner']); _key(value['strategy']); definition(value['strategy']); _key(value['security_id'])
    if value['security_id'] not in config['securities']:
        raise ValueError('shared_security_not_in_synthetic_account')
    signal = _signal(value['signal']); _clock(value['signal_at']); _clock(value['execution_at'])
    if value['signal_at'] >= value['execution_at']:
        raise ValueError('shared_signal_must_precede_execution')
    if type(value['source']) is not dict or value['source'].get('evidence_kind') != 'SYNTHETIC_TEST':
        raise ValueError('shared_synthetic_signal_source_required')
    if type(value['opportunity_id']) is not str or value['opportunity_id']!=opportunity_identity(value):
        raise ValueError('shared_opportunity_identity_invalid')
    if type(value['risk']) is not dict or set(value['risk'])!={'max_position_pct','max_single_loss_pct','max_daily_loss_pct','max_leverage','min_cash_pct'}:
        raise ValueError('shared_strategy_risk_fields_invalid')
    risk = RiskManager(RiskConfig(**value['risk']))
    if risk.config.max_leverage != 1:
        raise ValueError('shared_strategy_leverage_one_required')
    _number(value['fee_rate'], maximum=1); _number(value['slippage_pct'], maximum=1)
    ResearchExecutionSimulator(value['fee_rate'], value['slippage_pct'])
    return signal, risk


def _reserve_one(state, config, proposal):
    signal, risk = _proposal(proposal, config)
    if proposal['execution_at'] != state['marks_at']:
        raise ValueError('shared_intent_requires_current_exact_mark_clock')
    identity = digest(proposal)
    if identity in state['intents']:
        return dict(status='ALREADY_RECORDED', intent_id=identity, original_status=state['intents'][identity]['status'])
    if proposal['opportunity_id'] in state['opportunities']:
        return dict(status='DUPLICATE_SIGNAL', intent_id=identity, original_intent=state['opportunities'][proposal['opportunity_id']])
    owner, security = proposal['owner'], proposal['security_id']; price = float(state['marks'][security])
    position = state['positions'].get(_slot(owner, security), {})
    own_quantity = float(position.get('quantity', 0))
    security_quantity = sum((_d(p['quantity']) for p in state['positions'].values() if p['security_id'] == security), Decimal(0))
    # Canonical sizing sees total account NAV, not an independent task bankroll.
    if signal.action == Action.BUY:
        portfolio = Portfolio(cash=float(_equity(state) - security_quantity * _d(price)), position_qty=float(security_quantity))
    else:
        portfolio = Portfolio(cash=float(state['cash']), position_qty=own_quantity,
            avg_entry_price=float(position.get('avg_entry_price', 0)), entry_fees=float(position.get('entry_fees', 0)),
            realized_pnl=float(position.get('realized_pnl', 0)))
    risk.reset_day(float(state['day_start_equity']))
    order = risk.signal_to_order(config['securities'][security]['symbol'], signal, portfolio, price,
        fee_rate=proposal['fee_rate'], slippage_pct=proposal['slippage_pct'])
    row = dict(proposal=deepcopy(proposal), owner=owner, security_id=security, action=signal.action.value,
        quantity='0', reserved_cash='0', estimated_debit='0', status='REJECTED', reason='STRATEGY_RISK_NO_EXECUTABLE_INTENT', fill=None)
    if signal.action == Action.HOLD:
        row.update(status='HOLD', reason=signal.reason)
    elif order is not None:
        row.update(action=order.action.value, quantity=_money(order.quantity), reference_price=_money(price))
        if order.action == Action.BUY:
            notional = order.quantity * (price * (1 + proposal['slippage_pct']))
            debit = notional + notional * proposal['fee_rate']
            row.update(estimated_debit=_money(debit), reserved_cash=str(_d(debit).quantize(Decimal('0.01'), rounding=ROUND_CEILING)))
            reason = _buy_block(state, config, row)
        else:
            locked = sum(_d(r['quantity']) for r in state['intents'].values() if r['status'] == 'RESERVED'
                and r['action'] == 'SELL' and r['owner'] == owner and r['security_id'] == security)
            reason = 'INSUFFICIENT_UNRESERVED_OWNED_QUANTITY' if _d(row['quantity']) > _d(own_quantity) - locked else None
        row.update(status='REJECTED' if reason else 'RESERVED', reason=reason or 'GLOBAL_LIMITS_AND_FUNDS_ALLOWED')
        if reason: row['reserved_cash'] = '0'
    state['intents'][identity] = row; state['opportunities'][proposal['opportunity_id']] = identity
    return dict(status=row['status'], reason=row['reason'], intent_id=identity,
        requested_quantity=row['quantity'], reserved_cash=row['reserved_cash'])


def _invariants(state):
    if not math.isfinite(float(_equity(state))) or float(_equity(state)) <= 0:
        raise ValueError('shared_finite_positive_derived_equity_required')
    if _d(state['cash']) < 0 or _reserved(state) > _d(state['cash']):
        raise ValueError('shared_cash_or_reservation_invariant_broken')
    for position in state['positions'].values():
        if _d(position['quantity']) < 0 or _d(position['entry_fees']) < 0:
            raise ValueError('shared_position_invariant_broken')
    for row in state['intents'].values():
        if row['status'] != 'RESERVED' and _d(row['reserved_cash']) != 0:
            raise ValueError('shared_terminal_intent_must_release_reservation')


@_precision
def _transition(previous, request, config, head):
    if type(request) is not dict or set(request) != {'kind','at','payload'} or type(request['kind']) is not str or type(request['payload']) is not dict:
        raise ValueError('shared_request_fields_invalid')
    state = deepcopy(previous); kind = request['kind']; at = _clock(request['at'])
    if at < state['current_at']:
        raise ValueError('shared_clock_cannot_move_backwards')
    if config['schema_version']==ACCOUNT_SCHEMA and kind!='MARK' and at!=state['current_at']:
        raise ValueError('shared_operation_requires_current_account_clock_use_mark_to_advance')
    if at[:10] != state['day'] and kind in {'RESERVE','TASK_STEP','RESUME'}:
        raise ValueError('shared_new_day_requires_explicit_baseline_reset')
    payload = request['payload']; state['current_at'] = at
    if kind in {'RESERVE', 'TASK_STEP'}:
        if kind == 'TASK_STEP':
            if set(payload) != {'tasks'}: raise ValueError('shared_task_step_fields_invalid')
            from .shared_signals import task_proposals
            proposals = task_proposals(payload['tasks'], state, config, at)
        else:
            if set(payload) != {'intents'}: raise ValueError('shared_reserve_fields_invalid')
            proposals = payload['intents']
            if type(proposals) is not list or any(type(p) is not dict or type(p.get('source')) is not dict
                    or p['source'].get('kind')!='FIXED_SYNTHETIC_SIGNAL' for p in proposals):
                raise ValueError('shared_fixed_ingress_cannot_impersonate_registered_tasks')
        if type(proposals) is not list or not proposals:
            raise ValueError('shared_nonempty_intent_batch_required')
        outcome = dict(status='INTENTS_JUDGED', decisions=[_reserve_one(state, config, p) for p in proposals])
    elif kind == 'MARK':
        if set(payload) != {'prices'} or type(payload['prices']) is not dict or set(payload['prices']) != set(state['marks']):
            raise ValueError('shared_complete_security_mark_set_required')
        for value in payload['prices'].values(): _number(value, positive=True)
        if at == state['marks_at'] and any(_d(payload['prices'][k]) != _d(state['marks'][k]) for k in state['marks']):
            raise ValueError('shared_same_clock_mark_conflict')
        state.update(marks={k: _money(v) for k, v in payload['prices'].items()}, marks_at=at)
        if not _loss_allowed(state, config): state['loss_halted'] = True
        outcome = dict(status='MARKS_RECORDED', loss_halted=state['loss_halted'])
    elif kind == 'PAUSE':
        if set(payload) != {'reason'} or type(payload['reason']) is not str or not payload['reason'].strip():
            raise ValueError('shared_pause_reason_required')
        state.update(paused=True, pause_reason=payload['reason']); outcome = dict(status='GLOBAL_PAUSED')
    elif kind in {'RESUME', 'DAY_RESET'}:
        if set(payload) != {'expected_head'} or payload['expected_head'] != head:
            raise ValueError('shared_resume_or_reset_requires_current_receipt_head')
        active = any(r['status'] == 'RESERVED' for r in state['intents'].values())
        if active: raise ValueError('shared_resume_or_reset_requires_no_outstanding_reservations')
        if at != state['marks_at']: raise ValueError('shared_resume_or_reset_requires_current_exact_marks')
        if kind == 'DAY_RESET':
            if at[:10] <= state['day']: raise ValueError('shared_day_reset_requires_later_utc_day')
            state.update(day=at[:10], day_start_equity=str(_equity(state)), loss_halted=False)
            outcome = dict(status='DAY_BASELINE_RESET', manual_pause_preserved=state['paused'])
        else:
            limits=config['limits'];nav=_equity(state)
            if state['loss_halted'] or not _loss_allowed(state, config): raise ValueError('shared_loss_halt_requires_explicit_new_day_baseline')
            if (_exposure(state) > nav*_d(limits['max_total_position_pct'])
                    or any(_exposure(state,security=s)>nav*_d(limits['max_symbol_position_pct']) for s in state['marks'])
                    or _d(state['cash'])<nav*_d(limits['min_cash_pct'])):
                raise ValueError('shared_resume_global_limits_not_satisfied')
            state.update(paused=False, pause_reason=None);outcome=dict(status='GLOBAL_RESUMED')
    elif kind in {'CANCEL', 'REJECT', 'SETTLE'}:
        fields = {'intent_id'} if kind == 'SETTLE' else {'intent_id','reason'}
        if set(payload) != fields: raise ValueError('shared_lifecycle_payload_fields_invalid')
        identity=_key(payload['intent_id']);row=state['intents'].get(identity)
        if row is None: outcome=dict(status='INTENT_NOT_FOUND',intent_id=identity)
        elif row['status']!='RESERVED': outcome=dict(status='ALREADY_TERMINAL',intent_id=identity,original_status=row['status'])
        elif kind!='SETTLE':
            if type(payload['reason']) is not str or not payload['reason'].strip():raise ValueError('shared_release_reason_required')
            row.update(status='CANCELLED' if kind=='CANCEL' else 'REJECTED',reason=payload['reason'],reserved_cash='0')
            outcome=dict(status=row['status'],intent_id=identity)
        else:
            proposal=row['proposal'];security=row['security_id'];owner=row['owner']
            reason = 'STALE_MARK_OR_EXECUTION_CLOCK' if at!=proposal['execution_at'] or at!=state['marks_at'] or _d(state['marks'][security])!=_d(row['reference_price']) else None
            if reason is None and row['action']=='BUY':reason=_buy_block(state,config,row,omit=identity)
            if reason:
                row.update(status='REJECTED',reason=reason,reserved_cash='0');outcome=dict(status='REJECTED',reason=reason,intent_id=identity)
            else:
                slot=_slot(owner,security);p=state['positions'].get(slot,{})
                other_reserved=_reserved(state,omit=identity)
                portfolio=Portfolio(cash=float(_d(state['cash'])-other_reserved),position_qty=float(p.get('quantity',0)),
                    avg_entry_price=float(p.get('avg_entry_price',0)),entry_fees=float(p.get('entry_fees',0)),realized_pnl=float(p.get('realized_pnl',0)))
                order=Order(config['securities'][security]['symbol'],Action(row['action']),float(row['quantity']),float(row['reference_price']),proposal['signal']['reason'])
                fill=ResearchExecutionSimulator(proposal['fee_rate'],proposal['slippage_pct']).submit_order(order,portfolio)
                if fill.quantity!=order.quantity:
                    # The simulated portfolio is detached. A partial canonical
                    # fill never becomes a partial shared-account settlement.
                    row.update(status='REJECTED',reason='CANONICAL_FULL_FILL_NOT_AVAILABLE',reserved_cash='0')
                    outcome=dict(status='REJECTED',reason=row['reason'],intent_id=identity)
                else:
                    # Preserve the canonical float cost calculation; Decimal only
                    # combines account-wide cash deltas and conservative reserves.
                    delta=_d(fill.quantity*fill.price+fill.fee if row['action']=='BUY' else fill.quantity*fill.price-fill.fee)
                    state['cash']=str(_d(state['cash'])-delta if row['action']=='BUY' else _d(state['cash'])+delta)
                    state['positions'][slot]=dict(owner=owner,security_id=security,quantity=_money(portfolio.position_qty),
                        avg_entry_price=_money(portfolio.avg_entry_price),entry_fees=_money(portfolio.entry_fees),realized_pnl=_money(portfolio.realized_pnl))
                    row.update(status='SETTLED',reserved_cash='0',fill=dict(symbol=fill.symbol,action=fill.action.value,
                        quantity=fill.quantity,price=fill.price,fee=fill.fee,pnl=fill.pnl),reason='CANONICAL_SYNTHETIC_FILL')
                    if not _loss_allowed(state,config):state['loss_halted']=True
                    outcome=dict(status='SETTLED',intent_id=identity,fill=deepcopy(row['fill']))
    else: raise ValueError('shared_operation_kind_unsupported')
    _invariants(state)
    return outcome,state


def _manifest(directory):
    directory=Path(directory).resolve();path=directory/'account.json'
    if path.is_symlink() or not path.is_file():raise ValueError('shared_account_manifest_missing_or_not_regular')
    value=parse_document(path.read_bytes())
    if set(value)!={'config','runtime','account_id'} or value['account_id']!=digest({k:v for k,v in value.items() if k!='account_id'}):
        raise ValueError('shared_account_manifest_identity_invalid')
    # Historical journals keep their original per-ID admission semantics.
    # Reading cannot silently invalidate or rewrite previously committed bytes.
    validate_account_config(value['config'], allow_historical_symbol_aliases=True)
    return value


@contextmanager
def _connection(directory, *, write=False):
    path=Path(directory).resolve()/'ledger.sqlite3'
    if path.is_symlink() or not path.is_file():raise ValueError('shared_account_ledger_missing_or_not_regular')
    conn=sqlite3.connect(path.as_uri()+'?mode=rw' if write else path.as_uri()+'?mode=ro',uri=True,timeout=20,isolation_level=None)
    try:
        conn.execute('PRAGMA synchronous=FULL')
        conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        yield conn
    except sqlite3.Error as exc:
        raise ValueError('shared_sqlite_operation_stopped:'+type(exc).__name__) from exc
    finally:conn.close()


def _restore(conn,manifest):
    state=_initial(manifest['config']);head=ZERO;receipts=[]
    for sequence,operation_id,raw in conn.execute('SELECT seq, operation_id, receipt FROM events ORDER BY seq'):
        value=parse_document(raw)
        fields={'schema_version','account_id','sequence','operation_id','previous_receipt','request','outcome','state_hash','receipt_hash'}
        expected_schema=RECEIPT_SCHEMA if manifest['config']['schema_version']==ACCOUNT_SCHEMA else LEGACY_RECEIPT_SCHEMA
        if (set(value)!=fields or value['schema_version']!=expected_schema or value['account_id']!=manifest['account_id']
                or sequence!=len(receipts)+1 or value['sequence']!=sequence or operation_id!=value['operation_id']
                or value['previous_receipt']!=head or value['receipt_hash']!=digest({k:v for k,v in value.items() if k!='receipt_hash'})):
            raise ValueError('shared_journal_identity_or_sequence_invalid')
        outcome,state=_transition(state,value['request'],manifest['config'],head)
        if outcome!=value['outcome'] or digest(state)!=value['state_hash']:
            raise ValueError('shared_journal_transition_or_state_invalid')
        receipts.append(value);head=value['receipt_hash']
    return state,head,receipts


@_precision
def create_shared_account(directory,config):
    directory=Path(directory).resolve();config=validate_account_config(config)
    if config['schema_version']!=ACCOUNT_SCHEMA:raise ValueError('shared_new_account_requires_current_version_config')
    if directory.exists():raise ValueError('shared_new_account_directory_required')
    _invariants(_initial(config))
    runtime=build_runtime_provenance()
    if runtime['source_identity']['status'] not in {'CONTENT_HASHED','BUILD_VERIFIED'} or runtime['environment_verified']['status']!='VERIFIED':
        raise ValueError('shared_initialization_requires_verified_code_and_dependencies')
    binding=dict(source_sha256=runtime['source_identity']['content_sha256'],dependencies=runtime['environment_verified'])
    core=dict(config=config,runtime=binding);manifest={**core,'account_id':digest(core)}
    directory.parent.mkdir(parents=True,exist_ok=True)
    # Cooperating initializers share an OS mutex before publishing. A failed
    # staging directory is retained for inspection; an existing target is never
    # used as an empty account or overwritten.
    lock=directory.parent/('.shared-init-'+digest(str(directory))+'.lock')
    with _file_lock(lock):
        if directory.exists():raise ValueError('shared_new_account_directory_required')
        stage=Path(mkdtemp(prefix='.preparing-shared-',dir=directory.parent))
        (stage/'account.json').write_bytes(canonical_bytes(manifest))
        conn=sqlite3.connect(stage/'ledger.sqlite3')
        try:
            conn.execute('PRAGMA synchronous=FULL');conn.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE, receipt BLOB NOT NULL)');conn.commit()
        finally:conn.close()
        if directory.exists():raise ValueError('shared_new_account_directory_required')
        stage.rename(directory)
    return describe_shared_account(directory)


@_precision
def transact_shared_account(directory, *, operation_id, kind, at, payload):
    _key(operation_id);_clock(at)
    request=dict(kind=kind,at=at,payload=parse_document(canonical_bytes(payload)))
    manifest=_manifest(directory)
    if manifest['config']['schema_version']!=ACCOUNT_SCHEMA:
        raise ValueError('shared_legacy_v1_account_is_read_only_original_bytes_retained')
    validate_account_config(manifest['config'])
    runtime=build_runtime_provenance()
    if manifest['runtime']!=dict(source_sha256=runtime['source_identity']['content_sha256'],dependencies=runtime['environment_verified']):
        raise ValueError('shared_mutation_requires_original_code_and_dependencies')
    with _connection(directory,write=True) as conn:
        state,head,receipts=_restore(conn,manifest)
        old=next((r for r in receipts if r['operation_id']==operation_id),None)
        if old is not None:
            if old['request']!=request:raise ValueError('shared_operation_id_payload_conflict')
            return old
        outcome,next_state=_transition(state,request,manifest['config'],head)
        core=dict(schema_version=RECEIPT_SCHEMA,account_id=manifest['account_id'],sequence=len(receipts)+1,
            operation_id=operation_id,previous_receipt=head,request=request,outcome=outcome,state_hash=digest(next_state))
        receipt={**core,'receipt_hash':digest(core)}
        conn.execute('INSERT INTO events (seq, operation_id, receipt) VALUES (?, ?, ?)',(receipt['sequence'],operation_id,canonical_bytes(receipt)))
        conn.execute('COMMIT')
        return receipt


@_precision
def describe_shared_account(directory):
    manifest=_manifest(directory)
    with _connection(directory) as conn:state,head,receipts=_restore(conn,manifest)
    legacy=manifest['config']['schema_version']==LEGACY_ACCOUNT_SCHEMA
    return dict(schema_version='synthetic-shared-account-view-v2',account_id=manifest['account_id'],evidence_kind='SYNTHETIC_TEST',currency='USD',
        account_schema_version=manifest['config']['schema_version'],legacy_read_only=legacy,
        symbol_aliases_read_only=_symbol_aliases(manifest['config']),
        clock_policy='LEGACY_V1_REPLAY_ONLY' if legacy else 'ONLY_EXPLICIT_MARK_ADVANCES_CLOCK',
        competition=COMPETITION,limits=deepcopy(manifest['config']['limits']),state=state,sequence=len(receipts),receipt_head=head,
        cash=state['cash'],reserved_cash=str(_reserved(state)),available_cash=str(_d(state['cash'])-_reserved(state)),
        equity=str(_equity(state)),total_position_value=str(_equity(state)-_d(state['cash'])),projected_total_position_value=str(_exposure(state)),
        history=receipts,execution_permission=dict(PERMISSIONS),external_account_connected=False,broker_order_calls=0,
        limitations=['Synthetic local account only. No broker, paper/live authority, background monitoring or profitability claim.',
            'FIFO means the committed receipt sequence; concurrent scheduling may choose a different winner.',
            'All-or-nothing admission; no automatic reduction, retry or reinvestment of a rejected intent.',
            'Journal verification recomputes detached canonical synthetic transitions, never republishes or resubmits them.',
            'Spot long-only USD, fractional shares and canonical fixed cost/price approximations.'])
