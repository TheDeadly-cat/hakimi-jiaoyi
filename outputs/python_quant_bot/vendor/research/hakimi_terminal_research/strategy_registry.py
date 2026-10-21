"""Versioned application adapters over existing strategies, not another engine."""
from copy import deepcopy
from .documents import digest
from .equity_event_context import RULE_VERSION
from .equity_research import EquityExperimentSpec, EquityExperimentRunner, SPEC_SCHEMA, EVENT_SPEC_SCHEMA

_COMMON = dict(market='US_COMMON_STOCK', timeframe='REGULAR_SESSION_DAILY', status='AVAILABLE_OFFLINE',
    input_requirements=['Verified equity snapshot', 'Stable identity and declared action-free coverage',
        'Completed regular-session bars and sufficient warmup', 'Explicit score window, costs and risk'],
    risk_constraints=['Canonical RiskManager', 'Effective leverage 1', 'No shorting, margin or broker orders'])
_ENTRIES = {
    'price.dual_ma@1': dict(_COMMON, strategy_id='price.dual_ma', version='1', title='双均线价格策略',
        engine_strategy='dual_ma', event_rule=None, signal_rule='Existing fast/slow MA crossover',
        entry_rule='Available prior-session decision; next regular-session open',
        exit_rule='Existing crossover exit and requested stop/take-profit protections',
        parameters=['fast_window', 'slow_window', 'position_pct', 'stop_loss_pct', 'take_profit_pct']),
    'price.buy_and_hold@1': dict(_COMMON, strategy_id='price.buy_and_hold', version='1', title='买入持有基准',
        engine_strategy='buy_and_hold', event_rule=None, signal_rule='Existing one-time benchmark entry',
        entry_rule='Same scoring-session timing as the existing benchmark', exit_rule='Mark to market at end; no forced liquidation',
        parameters=['target_position_pct'],risk_constraints=['Existing full-spot-cash benchmark policy', 'No strategy stop/take-profit', 'No borrowing or orders']),
    'event.earnings_schedule@1': dict(_COMMON, strategy_id='event.earnings_schedule', version='1', title='公告排期过滤＋价格策略',
        engine_strategy='dual_ma', event_rule=RULE_VERSION,
        signal_rule='Existing dual MA; existing announced-schedule policy reviews each BUY',
        entry_rule='Known scheduled earnings date or unknown schedule blocks a new BUY',
        exit_rule='Same price strategy exits and canonical protections',
        parameters=['fast_window', 'slow_window', 'position_pct', 'stop_loss_pct', 'take_profit_pct'],
        extra_input_requirements=['Versioned, point-in-time event context for the same security']),
}

# Additive adapters: existing entries and their identity hashes remain unchanged.
for _key, _title, _rule in [
    ('content.price_confirmation@1', '公告后价格确认基准', 'FIRST_FULL_POST_RELEASE_CLOSE_CONFIRMATION_V1'),
    ('content.reviewed_outlook@1', '已核准下季指引条件＋价格确认', 'REVIEWED_NEXT_QUARTER_OUTLOOK_ABOVE_CURRENT_REVENUE_V1'),
]:
    _ENTRIES[_key] = dict(_COMMON, strategy_id=_key.split('@')[0], version='1', title=_title,
        engine_strategy='equity_post_release_confirmation', event_rule=_rule,
        signal_rule='Existing first full post-release close predicate; optionally existing approved outlook predicate',
        entry_rule='Single confirmation opportunity; next regular-session open',
        exit_rule='Canonical configured stop/take-profit; no retry or re-entry; mark to market at end',
        parameters=['position_pct', 'stop_loss_pct', 'take_profit_pct'],
        extra_input_requirements=['Existing candidate packet, normalized and original source bytes, exact publication clock',
            'Scoped field receipt for content acceptance; missing approval remains UNKNOWN/HOLD'])


def strategies():
    return deepcopy(_ENTRIES)


def definition(strategy_key):
    if strategy_key not in _ENTRIES:
        raise ValueError('unsupported_strategy:' + str(strategy_key))
    return deepcopy(_ENTRIES[strategy_key])


def strategy_identity(strategy_key):
    return digest(definition(strategy_key))


def effective_parameters(engine_strategy, params):
    """Interpret existing v1 adapters without changing their engine fallbacks.

    Blank edits retain omitted fields. This detached projection is shared by
    the form, configuration view and input admission, never a rewritten spec.
    """
    defaults = {'dual_ma': dict(fast_window=20, slow_window=60, position_pct=0.25,
        stop_loss_pct=0.03, take_profit_pct=0.08), 'buy_and_hold': dict(target_position_pct=0.25),
        'equity_post_release_confirmation': dict(position_pct=0.25, stop_loss_pct=0.03, take_profit_pct=0.06)}
    if engine_strategy not in defaults:
        raise ValueError('unsupported_application_engine_strategy:' + str(engine_strategy))
    return {**defaults[engine_strategy], **deepcopy(params)}


def new_task_parameters(engine_strategy):
    """New-task template; its 6% target is not an existing-rule default."""
    params = effective_parameters(engine_strategy, {})
    if engine_strategy == 'dual_ma':
        params['take_profit_pct'] = 0.06
    return params


def reconfigure_task_options(original, changes):
    """Preserve same-strategy omissions; switch to the target's new-task defaults.

    Only inherited strategy parameters, risk and event input are replaced on a
    strategy change. Explicit overrides remain subject to ordinary validation;
    shared snapshot, score, capital and costs are retained.
    """
    options = dict(original)
    if 'strategy' in changes and changes['strategy'] != original.get('strategy'):
        definition(changes['strategy'])
        options.update(params=None, risk=None, event_context=None)
    options.update(changes)
    return options


def validate_strategy(strategy_key, spec, event_context):
    entry = definition(strategy_key)
    if entry['engine_strategy'] == 'equity_post_release_confirmation':
        from .content_tasks import CONTEXT_SCHEMA, ContentTaskSpec, verify_content_context
        if type(event_context) is not dict or event_context.get('schema_version') != CONTEXT_SCHEMA:
            raise ValueError('research_input_not_applicable:content_rule_requires_content_context')
        checked = ContentTaskSpec.from_document(spec)
        context = verify_content_context(event_context)
        if checked.document['event_rule'] != entry['event_rule'] or checked.document['event_context_hash'] != context['context_hash']:
            raise ValueError('content_task_registered_rule_or_context_mismatch')
        return checked
    checked = EquityExperimentSpec.from_document(spec)
    doc = checked.document
    if doc['strategy']['name'] != entry['engine_strategy']:
        raise ValueError('strategy_configuration_does_not_match_registered_adapter')
    if set(doc['strategy']['params']) - set(entry['parameters']):
        raise ValueError('unsupported_application_strategy_parameter')
    if entry['event_rule'] is None:
        if doc['schema_version'] != SPEC_SCHEMA or event_context is not None:
            raise ValueError('price_strategy_must_not_silently_use_event_inputs')
    elif doc['schema_version'] != EVENT_SPEC_SCHEMA or doc['event_rule'] != entry['event_rule'] or event_context is None:
        raise ValueError('registered_event_strategy_requires_bound_event_context')
    elif event_context.get('schema_version') != 'equity-event-context-v1':
        raise ValueError('research_input_not_applicable:schedule_rule_requires_schedule_context')
    return checked


def run_strategy(strategy_key, snapshot, spec, event_context=None):
    checked = validate_strategy(strategy_key, spec, event_context)
    if definition(strategy_key)['engine_strategy'] == 'equity_post_release_confirmation':
        from .content_tasks import run_content_task
        return run_content_task(snapshot, checked, event_context)
    return EquityExperimentRunner().run(snapshot, checked, event_context=event_context)


def required_task_context(strategy_key, params):
    from .experiment import required_context
    entry = definition(strategy_key)
    return 1 if entry['engine_strategy'] == 'equity_post_release_confirmation' else required_context(entry['engine_strategy'], params)


def inspect_task_inputs(snapshot, spec, *, event_context=None):
    from .content_tasks import SPEC_SCHEMA, inspect_content_inputs
    if spec.document['schema_version'] == SPEC_SCHEMA:
        return inspect_content_inputs(snapshot, spec, event_context)
    from .equity_research import inspect_equity_inputs
    return inspect_equity_inputs(snapshot, spec, event_context=event_context)


def verify_task_report(document, snapshot):
    from .content_tasks import REPORT_SCHEMA, verify_content_report
    if document.get('schema_version') == REPORT_SCHEMA:
        return verify_content_report(document, snapshot)
    from .equity_research import verify_equity_report
    return verify_equity_report(document)


def replay_task_report(snapshot, report):
    from .content_tasks import REPORT_SCHEMA, replay_content_report
    if report.document.get('schema_version') == REPORT_SCHEMA:
        return replay_content_report(snapshot, report)
    from .equity_research import replay_equity_report
    return replay_equity_report(snapshot, report)
