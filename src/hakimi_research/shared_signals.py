"""Existing task signals over fixed synthetic inputs and one account view."""
from contextlib import ExitStack
from copy import deepcopy
import pandas as pd

from .config import RiskConfig
from .content_tasks import ContentSignalAdapter, content_plan
from .documents import digest
from .equity_dataset import EquitySnapshot, verify_equity_snapshot
from .equity_event_context import EventSchedulePolicy
from .models import Portfolio, Signal
from .offline_app import check_task
from .risk import RiskManager
from .shared_account import _d, _equity, _reserved, _slot, signal_document, transact_shared_account
from .strategies.templates import build_strategy
from .strategy_registry import definition, effective_parameters, inspect_task_inputs, strategy_identity, validate_strategy
from .task_manager import _family_for_task, family_lock


def fixed_signal_proposal(*, owner, strategy, security_id, signal, signal_at, execution_at,
        risk, fee_rate=0, slippage_pct=0, signal_key='fixed-input'):
    value=dict(owner=owner,strategy=strategy,security_id=security_id,signal=signal_document(signal),
        signal_at=signal_at,execution_at=execution_at,risk=deepcopy(risk),fee_rate=fee_rate,slippage_pct=slippage_pct,
        source=dict(kind='FIXED_SYNTHETIC_SIGNAL',evidence_kind='SYNTHETIC_TEST',signal_key=signal_key))
    from .shared_account import opportunity_identity
    return {**value,'opportunity_id':opportunity_identity(value)}


def demo_competing_intents():
    risk=dict(max_position_pct=1,max_single_loss_pct=0.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0)
    return [fixed_signal_proposal(owner=owner,strategy='price.buy_and_hold@1',security_id='SYNTHETIC:RESEARCH:TEST',
        signal=Signal.buy('SYNTHETIC two strategies each request 80 percent',0.8),
        signal_at='2024-11-07T21:01:00Z',execution_at='2024-11-08T14:30:00Z',risk=risk)
        for owner in ['synthetic-strategy-a','synthetic-strategy-b']]


def _pack(context):
    value=dict(schema_version='shared-fixed-task-input-v1',task_id=context['task_id'],
        semantics=deepcopy(context['semantics']),snapshot=deepcopy(context['snapshot'].document),
        context=deepcopy(context['context']))
    return {**value,'binding_hash':digest(value)}


def _check_binding(value):
    fields={'schema_version','task_id','semantics','snapshot','context','binding_hash'}
    if (type(value) is not dict or set(value)!=fields or value['schema_version']!='shared-fixed-task-input-v1'
            or value['binding_hash']!=digest({k:v for k,v in value.items() if k!='binding_hash'})
            or value['task_id']!=digest(value['semantics'])):
        raise ValueError('shared_task_binding_identity_invalid')
    semantics=value['semantics'];key=semantics['strategy']
    if semantics['state']!='ENABLED' or semantics['strategy_identity']!=strategy_identity(key):
        raise ValueError('shared_task_disabled_or_registered_identity_changed')
    data=verify_equity_snapshot(value['snapshot']);spec=semantics['experiment']
    if data['evidence_kind']!='SYNTHETIC_TEST' or spec['purpose']!='SYNTHETIC_REGRESSION':
        raise ValueError('shared_task_step_only_fixed_synthetic_inputs_supported')
    if value['context'] is not None:
        context=value['context']
        synthetic=(context.get('evidence_kind')=='SYNTHETIC_TEST' if context.get('schema_version')=='equity-content-context-v1'
            else bool(context.get('events')) and all(e['source']['kind']=='SYNTHETIC_FIXTURE' for e in context['events']))
        if not synthetic:raise ValueError('shared_task_step_real_research_context_not_supported')
    checked=validate_strategy(key,spec,value['context'])
    inspect_task_inputs(EquitySnapshot(data),checked,event_context=value['context'])
    if spec['snapshot_id']!=data['snapshot_id'] or semantics['event_context_hash']!=(value['context']['context_hash'] if value['context'] else None):
        raise ValueError('shared_task_input_binding_conflict')
    return semantics,data,spec


def task_proposals(bindings,state,config,at):
    if type(bindings) is not list or not bindings:
        raise ValueError('shared_nonempty_fixed_tasks_required')
    proposals=[];seen=[]
    for binding in bindings:
        semantics,data,spec=_check_binding(binding);key=semantics['strategy'];entry=definition(key)
        security=data['security']['security_id'];sessions=data['sessions']
        management=semantics.get('management')
        owner='family:'+management['family_id'] if management else binding['task_id']
        if security not in config['securities'] or config['securities'][security]['symbol']!=data['security']['symbol']:
            raise ValueError('shared_task_security_not_bound_to_account')
        index=next((i for i,s in enumerate(sessions) if s['open_utc']==at),None)
        if index is None or index<1 or not spec['score_start_session']<=sessions[index]['date']<=spec['score_end_session']:
            raise ValueError('shared_task_execution_outside_fixed_score_sessions')
        frame=EquitySnapshot(data).frame();price=float(frame.iloc[index]['open'])
        if at!=state['marks_at'] or _d(price)!=_d(state['marks'][security]):
            raise ValueError('shared_task_quote_differs_from_current_account_mark')
        signal_at=(pd.Timestamp(sessions[index-1]['close_utc'])+pd.Timedelta(seconds=data['bar_availability_lag_seconds'])).isoformat().replace('+00:00','Z')
        if pd.Timestamp(signal_at)>=pd.Timestamp(at):raise ValueError('shared_task_prior_bar_not_available')
        position=state['positions'].get(_slot(owner,security),{})
        portfolio=Portfolio(cash=float(_d(state['cash'])-_reserved(state)),position_qty=float(position.get('quantity',0)),
            avg_entry_price=float(position.get('avg_entry_price',0)),entry_fees=float(position.get('entry_fees',0)),realized_pnl=float(position.get('realized_pnl',0)))
        params=spec['strategy']['params'];reviews={}
        if entry['engine_strategy']=='buy_and_hold':
            if sessions[index]['date']!=spec['score_start_session'] or portfolio.position_qty>0:
                signal=Signal.hold('SHARED_BENCHMARK_SINGLE_FIRST_SESSION_OPPORTUNITY')
            else:
                signal=build_strategy('buy_and_hold',params).generate_signal(frame.iloc[:index],portfolio)
        elif entry['engine_strategy']=='equity_post_release_confirmation':
            plan,input_reviews=content_plan(data,binding['context'],enabled=entry['event_rule']=='REVIEWED_NEXT_QUARTER_OUTLOOK_ABOVE_CURRENT_REVENUE_V1')
            scored={s['open_utc'] for s in sessions if spec['score_start_session']<=s['date']<=spec['score_end_session']}
            allowed=next((r for r in plan if r['action']=='BUY' and r['execution_at'] in scored),None)
            confirmation=None
            if allowed:
                pindex=next(i for i,r in enumerate(plan) if r['decision_at']==allowed['decision_at'])
                confirmation=str(pd.Timestamp(sessions[pindex]['open_utc']))
            model=ContentSignalAdapter(dict(params,confirmation_bar_open=confirmation,decision_plan_hash=digest(plan)))
            signal=model.generate_signal(frame.iloc[:index],portfolio)
            reviews=dict(decision=next((r for r in plan if r['execution_at']==at),None),input_reviews=input_reviews)
        else:
            signal=build_strategy(entry['engine_strategy'],params).generate_signal(frame.iloc[:index],portfolio)
            if entry['event_rule']:
                policy=EventSchedulePolicy(binding['context'],rule=entry['event_rule'],
                    security_id=security,purpose=spec['purpose'])
                signal,decision=policy.review(signal,as_of=signal_at,execution_time=at,
                    execution_session=sessions[index]['date'],stage='DECISION')
                signal,execution=policy.review(signal,as_of=at,execution_time=at,
                    execution_session=sessions[index]['date'],stage='EXECUTION')
                reviews=dict(decision=decision,execution=execution)
        # Existing canonical open-price protection remains reduce-only. Full
        # daily-OHLC/incremental protection orchestration is a later package.
        if entry['engine_strategy']!='buy_and_hold' and portfolio.position_qty>0:
            protective=RiskManager(RiskConfig(**spec['risk'])).enforce_stop_rules(data['security']['symbol'],portfolio,
                price,params.get('stop_loss_pct',0.03),params.get('take_profit_pct',0.08))
            if protective is not None:signal=Signal.exit(protective.reason)
        # Copies, task bankroll edits and later snapshot/context versions cannot
        # turn the same rule/clock signal into another account opportunity.
        opportunity_inputs=dict(strategy_identity=semantics['strategy_identity'],
            parameters=effective_parameters(entry['engine_strategy'],params),signal_at=signal_at,execution_at=at,
            security_id=security,action=signal.action.value,signal_size_pct=signal.size_pct,
            stop_loss_pct=signal.stop_loss_pct,take_profit_pct=signal.take_profit_pct)
        proposal=dict(owner=owner,strategy=key,security_id=security,signal=signal_document(signal),signal_at=signal_at,execution_at=at,
            risk=deepcopy(spec['risk']),fee_rate=spec['fee_rate'],slippage_pct=spec['slippage_pct'],
            source=dict(kind='REGISTERED_TASK_SIGNAL',evidence_kind='SYNTHETIC_TEST',binding_hash=binding['binding_hash'],
                account_state_hash=digest(state),independent_task_capital_applied=False,opportunity_inputs=opportunity_inputs,research_review=reviews),
            opportunity_id=digest(opportunity_inputs))
        proposals.append(proposal);seen.append(key)
    return proposals


def step_shared_tasks(directory,task_files,*,operation_id,at):
    # Same family mutex as task edit/run; hold it through account publication.
    with ExitStack() as stack:
        families=sorted({str(f) for path in task_files if (f:=_family_for_task(path)) is not None})
        for family in families:stack.enter_context(family_lock(family))
        bindings=[_pack(check_task(path)) for path in task_files]
        return transact_shared_account(directory,operation_id=operation_id,kind='TASK_STEP',at=at,payload=dict(tasks=bindings))
