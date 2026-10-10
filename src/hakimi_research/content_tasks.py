"""Portable inputs and an installed adapter for the existing C/D predicates.

Candidate packets, field receipts and source bytes keep their original formats.
This envelope binds them to a task; it does not extract or approve new facts.
The adapter feeds a fixed signal plan to the canonical session engine.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
import re

import pandas as pd

from . import content_protocol as protocol
from .benchmarks import STANDARD_RISK_POLICY
from .config import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from .documents import canonical_bytes, digest, parse_document
from .environment import build_runtime_provenance
from .equity_dataset import EquitySnapshot, verify_equity_snapshot
from .equity_events import build_equity_event, event_snapshot_eligibility, select_event_versions
from .equity_research import PERMISSIONS, _SessionEngine, _projection, _verify_equity_fills
from .models import Signal
from .risk import RiskManager
from .strategies.base import StrategyBase

CONTEXT_SCHEMA = 'equity-content-context-v1'
SPEC_SCHEMA = 'us-equity-content-task-spec-v1'
REPORT_SCHEMA = 'us-equity-content-task-report-v1'
PRICE_RULE = 'FIRST_FULL_POST_RELEASE_CLOSE_CONFIRMATION_V1'
CONTENT_RULE = 'REVIEWED_NEXT_QUARTER_OUTLOOK_ABOVE_CURRENT_REVENUE_V1'
ENGINE_STRATEGY = 'equity_post_release_confirmation'
PARAMETERS = {'position_pct', 'stop_loss_pct', 'take_profit_pct'}
_HEX = re.compile(r'[0-9a-f]{64}')
_LIMIT = 8 * 1024 * 1024


def _decode(value):
    if type(value) is not str:
        raise ValueError('content_source_base64_required')
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise ValueError('content_source_base64_invalid') from exc
    if not raw or len(raw) > _LIMIT:
        raise ValueError('content_source_size_invalid')
    return raw


def _packet(raw):
    # Original review files can have a UTF-8 BOM; its bytes remain in the seal.
    return parse_document(raw.removeprefix(b'\xef\xbb\xbf'), maximum_bytes=_LIMIT)


def build_content_context(packet_raw, *, event_id, texts, approval_raw=None,
                          originals=None, synthetic=False):
    if type(synthetic) is not bool or type(event_id) is not str or not event_id.strip():
        raise ValueError('content_event_id_and_explicit_evidence_kind_required')
    packet = _packet(packet_raw)
    approval = _packet(approval_raw) if approval_raw is not None else None
    protocol.validate_approval(packet, approval)
    candidates = [r for r in packet.get('events', []) if r.get('event_id') == event_id]
    if not candidates:
        raise ValueError('content_event_missing')
    securities = {r['security_id'] for r in candidates}
    if len(securities) != 1:
        raise ValueError('content_event_security_conflict')
    originals = originals or {}
    sources = {}
    for field, supplied in [('normalized', texts), ('originals', originals)]:
        if type(supplied) is not dict:
            raise ValueError('content_source_inventory_required')
        sources[field] = {}
        for key, raw in supplied.items():
            if type(key) is not str or not _HEX.fullmatch(key) or type(raw) is not bytes or not raw or len(raw) > _LIMIT:
                raise ValueError('content_source_identity_or_size_invalid')
            if sha256(raw).hexdigest() != key:
                raise ValueError('content_source_bytes_changed')
            sources[field][key] = base64.b64encode(raw).decode('ascii')
    wanted = {r['plain_text_sha256'] for r in candidates}
    if set(sources['normalized']) != wanted:
        raise ValueError('content_normalized_sources_missing_or_unselected')
    wanted_raw = {r['raw_sha256'] for r in candidates}
    if set(sources['originals']) - wanted_raw:
        raise ValueError('content_original_sources_unselected')
    # Plain-text fictional originals may be byte-identical to normalized text.
    # This retains their actual bytes; it never invents missing HTML.
    for key in wanted_raw & wanted:
        sources['originals'].setdefault(key, sources['normalized'][key])
    core = dict(schema_version=CONTEXT_SCHEMA, event_id=event_id,
        security_id=next(iter(securities)), packet=packet, approval=approval,
        source_bytes=sources,
        original_inputs=dict(packet_base64=base64.b64encode(packet_raw).decode('ascii'),
            packet_sha256=sha256(packet_raw).hexdigest(),
            approval_base64=base64.b64encode(approval_raw).decode('ascii') if approval_raw is not None else None,
            approval_sha256=sha256(approval_raw).hexdigest() if approval_raw is not None else None),
        evidence_kind='SYNTHETIC_TEST' if synthetic else 'IMPORTED_UNVERIFIED',
        scope='EXISTING_PRICE_CONFIRMATION_AND_NEXT_QUARTER_OUTLOOK_NOT_CONSENSUS',
        execution_permission=dict(PERMISSIONS))
    context = {**core, 'context_hash': digest(core)}
    _versions(context)
    return context


def verify_content_context(document):
    value = parse_document(canonical_bytes(document))
    raw = value['original_inputs']
    expected = build_content_context(_decode(raw['packet_base64']), event_id=value['event_id'],
        approval_raw=_decode(raw['approval_base64']) if raw['approval_base64'] is not None else None,
        texts={k: _decode(v) for k, v in value['source_bytes']['normalized'].items()},
        originals={k: _decode(v) for k, v in value['source_bytes']['originals'].items()},
        synthetic=value['evidence_kind'] == 'SYNTHETIC_TEST')
    if canonical_bytes(value) != canonical_bytes(expected):
        raise ValueError('content_context_binding_invalid')
    return expected


def _versions(context):
    """Project the two existing predicate inputs to the canonical event contract."""
    approved = protocol.validate_approval(context['packet'], context['approval'])
    candidates = sorted((r for r in context['packet']['events'] if r.get('event_id') == context['event_id']),
        key=lambda r: r['version'])
    previous = None
    events, bindings = [], {}
    for candidate in candidates:
        if candidate['candidate_hash'] != protocol.digest({k: v for k, v in candidate.items() if k != 'candidate_hash'}):
            raise ValueError('content_candidate_identity_changed')
        if candidate['prior_version_hash'] != previous:
            raise ValueError('content_candidate_lineage_mismatch')
        if not candidate.get('first_public_at'):
            raise ValueError('content_publication_time_unknown')
        text = _decode(context['source_bytes']['normalized'][candidate['plain_text_sha256']]).decode('utf-8')
        used = []
        for name in ('actual_revenue', 'next_revenue_guidance_midpoint'):
            matches = [f for f in candidate['facts'] if f['name'] == name]
            if len(matches) != 1:
                raise ValueError('content_unique_required_fact_missing')
            fact = matches[0]
            if fact['status'] == 'MISSING':
                used.append(dict(name=name, status='MISSING', value=None, value_text=None, scale=None,
                    currency=None, unit=None, fiscal_period=None, basis=None, evidence=[], reason=fact['reason']))
                continue
            evidence = fact['evidence']
            eligible = candidate['candidate_hash'] in approved and fact['status'] in {'KNOWN', 'UNCERTAIN'} \
                and fact.get('reason') in {None, 'PENDING_HUMAN_SEMANTIC_REVIEW'}
            used.append(dict(name=name, status='KNOWN' if eligible else 'UNCERTAIN', value=fact['value'],
                value_text=fact['value'], scale=fact['scale'], currency=fact['currency'], unit=fact['unit'],
                fiscal_period=fact['fiscal_period'], basis='GAAP' if name == 'actual_revenue' else 'NOT_APPLICABLE',
                evidence=[dict(start=evidence['plain_text_start'], end=evidence['plain_text_end'], quote=evidence['quote'])],
                reason=None if eligible else 'NOT_APPROVED_OR_UNCERTAIN'))
        event = build_equity_event(text.encode('utf-8'), dict(event_id=candidate['event_id'],
            security_id=candidate['security_id'], event_kind='EARNINGS', version=candidate['version'],
            prior_version_hash=events[-1]['event_hash'] if events else None,
            source=dict(url=candidate['source_url'],
                kind='SYNTHETIC_FIXTURE' if context['evidence_kind'] == 'SYNTHETIC_TEST' else 'COMPANY_IR',
                document_type='EARNINGS_RELEASE_NORMALIZED_TEXT', disclosure_items=[], official_source_status='DECLARED_UNVERIFIED'),
            first_public_at=candidate['first_public_at'],
            version_public_at=candidate.get('version_public_at', candidate['first_public_at']),
            publication_clock=dict(status='ATTESTED', verification_method='RETAINED_PACKET_DECLARED_PUBLICATION_CLOCK',
                evidence='candidate_sha256=' + candidate['candidate_hash']), retrieved_at=candidate['retrieved_at'],
            timing=dict(mode='HISTORICAL_RECONSTRUCTION', received_at=None,
                extraction_completed_at=candidate['extraction_completed_at'], collection_delay_seconds=60, processing_delay_seconds=60),
            scheduled_release_at=None, facts=used,
            uncertainties=['Current retained sources are not authenticated immutable historical content.',
                '60+60 seconds is the existing 120-second model assumption, not measured latency.',
                'Only the two predicate inputs are projected; the full candidate packet remains sealed.']))
        events.append(event)
        bindings[event['event_hash']] = candidate
        previous = candidate['candidate_hash']
    select_event_versions(events, '9999-01-01T00:00:00Z')
    return events, bindings, approved


@dataclass(frozen=True)
class ContentTaskSpec:
    document: dict

    @classmethod
    def from_document(cls, document):
        value = parse_document(canonical_bytes(document))
        fields = {'schema_version', 'name', 'snapshot_id', 'score_start_session', 'score_end_session', 'strategy',
            'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy', 'purpose', 'quantity_policy',
            'execution_policy', 'event_context_hash', 'event_rule'}
        if set(value) != fields or value['schema_version'] != SPEC_SCHEMA:
            raise ValueError('content_task_spec_fields_invalid')
        if type(value['name']) is not str or not value['name'].strip():
            raise ValueError('content_task_name_required')
        if any(type(value[k]) is not str or not _HEX.fullmatch(value[k]) for k in ('snapshot_id','event_context_hash')):
            raise ValueError('content_task_input_identity_invalid')
        if value['event_rule'] not in {PRICE_RULE, CONTENT_RULE}:
            raise ValueError('content_task_existing_rule_required')
        if value['purpose'] not in {'SYNTHETIC_REGRESSION', 'DESCRIPTIVE_DEVELOPMENT'}:
            raise ValueError('content_task_purpose_invalid')
        if value['end_policy'] != 'MARK_TO_MARKET' or value['quantity_policy'] != 'FRACTIONAL_SHARES_RESEARCH_APPROXIMATION' \
                or value['execution_policy'] != STANDARD_RISK_POLICY:
            raise ValueError('content_task_execution_policy_invalid')
        for key in ('score_start_session', 'score_end_session'):
            if type(value[key]) is not str or pd.Timestamp(value[key]).strftime('%Y-%m-%d') != value[key]:
                raise ValueError('content_task_score_session_required')
        if value['score_start_session'] > value['score_end_session']:
            raise ValueError('content_task_score_range_invalid')
        strategy = value['strategy']
        if set(strategy) != {'name', 'params'} or strategy['name'] != ENGINE_STRATEGY or set(strategy['params']) != PARAMETERS:
            raise ValueError('content_task_strategy_parameters_invalid')
        params = strategy['params']
        Signal.buy('configuration validation only', params['position_pct'],
            stop_loss_pct=params['stop_loss_pct'], take_profit_pct=params['take_profit_pct'])
        config = _config(value, 'TEST')
        if config.risk.max_leverage != 1:
            raise ValueError('spot_mvp_requires_leverage_one')
        return cls(value)


def _config(spec, symbol, params=None):
    return BotConfig(market='stock', symbol=symbol, timeframe='1d', initial_cash=spec['initial_cash'],
        strategy=StrategyConfig(name=ENGINE_STRATEGY, params=params or spec['strategy']['params']),
        risk=RiskConfig(**spec['risk']), execution=ExecutionConfig(fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct']))


def content_plan(data, context, *, enabled):
    events, bindings, approved = _versions(context)
    if not any(protocol.utc(s['close_utc']) <= protocol.utc(events[0]['first_public_at']) for s in data['sessions']):
        raise ValueError('content_pre_release_price_baseline_missing')
    alignment = event_snapshot_eligibility(events[0], data)
    if alignment['status'] != 'READY':
        raise ValueError('content_calendar_not_ready:' + alignment['reason'])
    rows, decisions, bars = [], [], []
    for candle, session in zip(data['candles'], data['sessions']):
        at = (protocol.utc(session['close_utc']) + timedelta(seconds=data['bar_availability_lag_seconds'])).isoformat().replace('+00:00', 'Z')
        bars.append(dict(session=session['date'], close=str(candle[4]), available_at=at, completed=True))
        price = protocol.price_confirmation(release_at=events[0]['first_public_at'], decision_at=at, sessions=data['sessions'], bars=bars)
        known = select_event_versions(events, at)
        versions = [bindings[e['event_hash']] for e in known]
        result = protocol.content_condition(price, versions=versions, decision_at=at, approved_hashes=approved, enabled=enabled)
        decisions.append(dict(decision_at=at, **result))
        blocked = price['action'] == 'BUY' and result['action'] != 'BUY'
        rows.append(dict(decision_at=at, price_action=price['action'], output_action=result['action'],
            execution_at=result['execution_at'], price_execution_at=price['execution_at'], reason=result['reason'],
            disposition='BLOCK_NEW_BUY' if blocked else 'NO_PRICE_BUY' if price['action'] != 'BUY'
                else 'ALLOW_REVIEWED_CONTENT_BUY' if enabled else 'CONTENT_RULE_DISABLED_PRICE_BASELINE',
            known_versions=[dict(event_id=e['event_id'], version=e['version'], event_hash=e['event_hash'],
                candidate_hash=bindings[e['event_hash']]['candidate_hash'], available_at=e['availability']['available_at'],
                available_at_kind=e['availability']['available_at_kind'],
                field_review='APPROVED' if bindings[e['event_hash']]['candidate_hash'] in approved else 'NOT_APPROVED') for e in known]))
    if sum(r['action'] == 'BUY' for r in decisions) > 1:
        raise ValueError('content_more_than_one_entry_intent')
    return decisions, rows


def inspect_content_inputs(snapshot, spec, context):
    data = verify_equity_snapshot(snapshot.document)
    value = ContentTaskSpec.from_document(spec.document if hasattr(spec, 'document') else spec).document
    context = verify_content_context(context)
    if value['snapshot_id'] != data['snapshot_id'] or value['event_context_hash'] != context['context_hash']:
        raise ValueError('content_task_input_identity_conflict')
    if context['security_id'] != data['security']['security_id']:
        raise ValueError('event_context_security_conflict')
    if not data['research_admission']['allowed']:
        raise ValueError('data_blocked:' + ','.join(data['research_admission']['block_reasons']))
    if (data['research_admission']['synthetic_only'] or context['evidence_kind'] == 'SYNTHETIC_TEST') and value['purpose'] != 'SYNTHETIC_REGRESSION':
        raise ValueError('synthetic_inputs_cannot_be_market_evidence')
    if data['bar_availability_lag_seconds'] != 60:
        raise ValueError('content_existing_60_second_bar_assumption_required')
    selected = [r for r in context['packet']['events'] if r.get('event_id') == context['event_id']]
    if any(r['raw_sha256'] not in context['source_bytes']['originals'] for r in selected):
        raise ValueError('content_original_source_missing')
    dates = [s['date'] for s in data['sessions']]
    try:
        first, last = dates.index(value['score_start_session']), dates.index(value['score_end_session']) + 1
    except ValueError as exc:
        raise ValueError('equity_score_session_not_in_snapshot') from exc
    if first < 1 or last <= first:
        raise ValueError('equity_insufficient_context_sessions')
    content_plan(data, context, enabled=value['event_rule'] == CONTENT_RULE)
    return dict(score_start=data['sessions'][first]['open_utc'], score_end=data['sessions'][last - 1]['close_utc'],
        available_context_sessions=first, required_context_sessions=1, scored_sessions=last - first, warmup_trading=False,
        annualization='252_REGULAR_SESSIONS_PER_YEAR_DESCRIPTIVE_ASSUMPTION',
        bar_availability_lag_seconds=60, session_clock_hash=digest(dict(sessions=data['sessions'], bar_availability_lag_seconds=60)),
        company_actions='DECLARED_ACTION_FREE_WINDOW_ONLY', parameter_selection=False, confirmation_evaluation=False)


class ContentSignalAdapter(StrategyBase):
    def __init__(self, params):
        super().__init__(params, name=ENGINE_STRATEGY, version='v1')

    def generate_signal(self, data, portfolio):
        if str(data.index[-1]) == self.get('confirmation_bar_open', None):
            return Signal.buy('FIRST_POST_RELEASE_CLOSE_ABOVE_PRE_RELEASE_CLOSE', self.get('position_pct', None),
                stop_loss_pct=self.get('stop_loss_pct', None), take_profit_pct=self.get('take_profit_pct', None))
        return Signal.hold('NO_AVAILABLE_PRICE_CONFIRMATION')


@dataclass(frozen=True)
class ContentTaskReport:
    document: dict


def run_content_task(snapshot, spec, context):
    value = ContentTaskSpec.from_document(spec.document if hasattr(spec, 'document') else spec).document
    clock = inspect_content_inputs(snapshot, value, context)
    data = verify_equity_snapshot(snapshot.document)
    context = verify_content_context(context)
    plan, reviews = content_plan(data, context, enabled=value['event_rule'] == CONTENT_RULE)
    dates = [s['date'] for s in data['sessions']]
    first, last = dates.index(value['score_start_session']), dates.index(value['score_end_session']) + 1
    opens = {s['open_utc'] for s in data['sessions'][first:last]}
    entry = next((r for r in plan if r['action'] == 'BUY' and r['execution_at'] in opens), None)
    confirmation = None
    if entry:
        index = next(i for i, r in enumerate(plan) if r['decision_at'] == entry['decision_at'])
        confirmation = str(pd.Timestamp(data['sessions'][index]['open_utc']))
    params = dict(value['strategy']['params'], confirmation_bar_open=confirmation, decision_plan_hash=digest(plan))
    config = _config(value, data['security']['symbol'], params)
    result = _SessionEngine(config, ContentSignalAdapter(params), RiskManager(config.risk),
        sessions=data['sessions'], lag=60, benchmark_policy=STANDARD_RISK_POLICY).run(
            EquitySnapshot(data).frame(), score_start=first, score_end=last).to_dict()
    result.pop('experiment_manifest', None)
    buys = [f for f in result['fills'] if f['action'] == 'BUY']
    if len(buys) > 1 or any(entry is None or pd.Timestamp(f['fill_time']) != pd.Timestamp(entry['execution_at']) for f in buys):
        raise ValueError('content_entry_execution_mismatch')
    core = dict(schema_version=REPORT_SCHEMA, spec=value, spec_hash=digest(value), dataset=_projection(data),
        scoring_protocol=clock, result=result, result_hash=digest(dict(snapshot_id=data['snapshot_id'], spec=value, result=result)),
        event_context=context, decision_plan=plan, input_reviews=reviews,
        provenance=build_runtime_provenance(), execution_permission=dict(PERMISSIONS),
        limitations=['Imported source, calendar and company-action declarations are not independently authenticated.',
            'This is the existing first full post-release close predicate and reviewed next-quarter outlook predicate; it is not analyst-consensus surprise.',
            '120-second information and 60-second completed-bar availability are model assumptions.',
            'Daily OHLC exits, fractional shares, fixed costs and mark-to-market are research approximations.',
            'One entry opportunity; no retry after rejection or protective exit. No strategy admission or profitability claim.'])
    return ContentTaskReport({**core, 'report_hash': digest(core)})


def verify_content_report(document, snapshot):
    value = parse_document(canonical_bytes(document))
    fields = {'schema_version', 'spec', 'spec_hash', 'dataset', 'scoring_protocol', 'result', 'result_hash',
        'event_context', 'decision_plan', 'input_reviews', 'provenance', 'execution_permission', 'limitations', 'report_hash'}
    if set(value) != fields or value['schema_version'] != REPORT_SCHEMA or value['report_hash'] != digest({k: v for k, v in value.items() if k != 'report_hash'}):
        raise ValueError('content_report_schema_or_identity_invalid')
    data = verify_equity_snapshot(snapshot.document)
    spec = ContentTaskSpec.from_document(value['spec'])
    clock = inspect_content_inputs(snapshot, spec, value['event_context'])
    plan, reviews = content_plan(data, value['event_context'], enabled=spec.document['event_rule'] == CONTENT_RULE)
    if value['spec_hash'] != digest(spec.document) or value['dataset'] != _projection(data) or value['scoring_protocol'] != clock \
            or value['decision_plan'] != plan or value['input_reviews'] != reviews or value['execution_permission'] != PERMISSIONS:
        raise ValueError('content_report_inputs_or_plan_changed')
    if value['result_hash'] != digest(dict(snapshot_id=data['snapshot_id'], spec=spec.document, result=value['result'])):
        raise ValueError('content_report_result_hash_mismatch')
    dates = [s['date'] for s in data['sessions']]
    first, last = dates.index(spec.document['score_start_session']), dates.index(spec.document['score_end_session']) + 1
    marks = value['result']['equity_curve']
    if len(marks) != last - first + 1 or pd.Timestamp(marks[0]['time']) != pd.Timestamp(data['sessions'][first]['open_utc']):
        raise ValueError('content_report_mark_count_or_initial_clock_invalid')
    if any(pd.Timestamp(m['time']) != pd.Timestamp(s['close_utc']) for m, s in zip(marks[1:], data['sessions'][first:last])):
        raise ValueError('content_report_mark_not_regular_close')
    expected = [pd.Timestamp(s['close_utc']) + pd.Timedelta(seconds=60) for s in data['sessions'][first - 1:last - 1]]
    if [pd.Timestamp(r['time']) for r in value['result']['signals']] != expected:
        raise ValueError('content_report_signal_availability_mismatch')
    _verify_equity_fills(value['result'], data, first, last, expected)
    _verify_content_execution(value['result'], plan, data['sessions'][first:last])
    return value


def _verify_content_execution(result, plan, sessions):
    """Bind saved intents/fills to the one admitted opportunity, without replay."""
    opens = {pd.Timestamp(s['open_utc']) for s in sessions}
    entry = next((r for r in plan if r['action'] == 'BUY' and pd.Timestamp(r['execution_at']) in opens), None)
    decision = pd.Timestamp(entry['decision_at']) if entry is not None else None
    execution = pd.Timestamp(entry['execution_at']) if entry is not None else None
    for signal in result['signals']:
        expected = 'BUY' if decision is not None and pd.Timestamp(signal['time']) == decision else 'HOLD'
        if signal['action'] != expected:
            raise ValueError('content_report_signal_not_bound_to_plan')
    if type(result['fill_count']) is not int or result['fill_count'] != len(result['fills']):
        raise ValueError('content_report_fill_count_mismatch')
    bought = exited = False
    previous = None
    for fill in result['fills']:
        at, signal_at = pd.Timestamp(fill['fill_time']), pd.Timestamp(fill['signal_time'])
        if previous is not None and at < previous:
            raise ValueError('content_report_fill_order_invalid')
        previous = at
        if fill['action'] == 'BUY':
            if bought or entry is None or at != execution or signal_at != decision or fill['fill_basis'] != 'NEXT_BAR_OPEN':
                raise ValueError('content_report_buy_not_bound_to_plan')
            bought = True
        elif fill['action'] == 'SELL':
            if (not bought or exited or signal_at != at
                    or fill['fill_basis'] not in {'GAP_OPEN', 'OPEN_TARGET', 'INTRABAR_STOP', 'INTRABAR_TARGET'}):
                raise ValueError('content_report_exit_not_protective_or_without_entry')
            exited = True
        else:
            raise ValueError('content_report_fill_action_invalid')


def replay_content_report(snapshot, report):
    original = verify_content_report(report.document, snapshot)
    repeated = run_content_task(snapshot, original['spec'], original['event_context']).document
    before, after = original['provenance'], repeated['provenance']
    matches = original['result_hash'] == repeated['result_hash']
    source = before['source_identity']['content_sha256'] == after['source_identity']['content_sha256'] \
        and before['source_identity']['status'] in {'CONTENT_HASHED', 'BUILD_VERIFIED'} \
        and after['source_identity']['status'] in {'CONTENT_HASHED', 'BUILD_VERIFIED'}
    environment = before['environment_verified'] == after['environment_verified'] and after['environment_verified']['status'] == 'VERIFIED'
    core = dict(schema_version='us-equity-content-task-replay-v1', original_report_hash=original['report_hash'],
        snapshot_id=snapshot.snapshot_id, original_result_hash=original['result_hash'], replayed_result_hash=repeated['result_hash'],
        result_matches=matches, source_matches=source, environment_verified=environment,
        replay_verified=matches and source and environment, execution_permission=dict(PERMISSIONS), replay_provenance=after)
    return {**core, 'receipt_hash': digest(core)}
