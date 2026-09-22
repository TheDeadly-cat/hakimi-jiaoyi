"""Offline event diagnostics using the existing stock engine and its reports.

This tool never fetches data. Full reports contain private market inputs and must
stay local; the returned summary contains only identities and aggregate results.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pandas as pd

from hakimi_research.benchmarks import BUY_AND_HOLD_POLICY
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_event_context import EventSchedulePolicy, RULE_VERSION, schedule_view
from hakimi_research.equity_research import EquityExperimentRunner, EquityExperimentSpec, verify_equity_report
from hakimi_research.equity_schedule_comparison import build_schedule_comparison, run_schedule_comparison


def aligned_benchmark_spec(base):
    """Use A/B score dates, cash, costs and allocation, with one entry."""
    value = copy.deepcopy(EquityExperimentSpec.from_document(base).document)
    if value['schema_version'] != 'us-equity-experiment-spec-v1':
        raise ValueError('diagnostics_require_price_only_base_spec')
    if value['strategy']['name'] != 'dual_ma':
        raise ValueError('diagnostics_require_dual_ma_baseline')
    value['strategy'] = {'name': 'buy_and_hold', 'params': {
        'target_position_pct': value['strategy']['params']['position_pct']}}
    value['execution_policy'] = BUY_AND_HOLD_POLICY
    # The canonical benchmark requires its full-spot admissibility ceiling;
    # the explicit single-entry target still fixes invested capital to 25%.
    value['risk']['max_position_pct'] = 1.0
    value['risk']['min_cash_pct'] = 0.0
    value['name'] += ' / aligned single-entry buy-and-hold'
    return EquityExperimentSpec.from_document(value)


def _position_at_release(report, event):
    """Only claim exact release exposure outside a regular trading session."""
    at = event.get('actual_release_at')
    if at is None:
        return {'status': 'UNKNOWN_RELEASE_CLOCK', 'position_held': None}
    if not event.get('actual_release_source'):
        raise ValueError('diagnostic_release_clock_requires_source')
    stamp = pd.Timestamp(at)
    if stamp.tzinfo is None:
        raise ValueError('diagnostic_release_clock_requires_timezone')
    protocol = report['scoring_protocol']
    if not pd.Timestamp(protocol['score_start']) <= stamp <= pd.Timestamp(protocol['score_end']):
        return {'status': 'OUTSIDE_SCORE_INTERVAL', 'position_held': None}
    if any(pd.Timestamp(row['open_utc']) <= stamp <= pd.Timestamp(row['close_utc'])
           for row in report['dataset']['sessions']):
        return {'status': 'UNKNOWN_INTRADAY_ORDERING', 'position_held': None}
    marks = [row for row in report['result']['equity_curve'] if pd.Timestamp(row['time']) < stamp]
    if not marks or 'position_qty' not in marks[-1]:
        return {'status': 'UNKNOWN_POSITION_MARK', 'position_held': None}
    return {'status': 'MODELLED_OUTSIDE_RTH_RELEASE',
            'position_held': marks[-1]['position_qty'] > 0,
            'basis': 'Last preceding regular-session close; daily model has no outside-RTH fills.'}


def diagnose_pair(a, b, expected_events):
    """Expected events are retrospective denominators, never strategy inputs."""
    comparison = build_schedule_comparison(a, b)
    a, b = verify_equity_report(a), verify_equity_report(b)
    identities = [event['event_id'] for event in expected_events]
    if not identities or len(identities) != len(set(identities)):
        raise ValueError('diagnostic_expected_events_must_be_unique_nonempty')
    first, last = b['spec']['score_start_session'], b['spec']['score_end_session']
    for event in expected_events:
        day = event['scheduled_date']
        if (not isinstance(day, str) or pd.Timestamp(day).strftime('%Y-%m-%d') != day
                or not first <= day <= last):
            raise ValueError('diagnostic_event_date_outside_score')
    sessions = {row['date']: row for row in b['dataset']['sessions']}
    policy = EventSchedulePolicy(b['event_context'], rule=RULE_VERSION,
        security_id=b['dataset']['security']['security_id'], purpose=b['spec']['purpose'])
    event_rows = []
    for event in expected_events:
        day, identity = event['scheduled_date'], event['event_id']
        session = sessions.get(day)
        known = [] if session is None else policy.known_at(session['open_utc'])
        covered = any(row['event_id'] == identity and row['schedule']['status'] == 'ANNOUNCED'
                      and row['schedule']['date'] == day for row in known)
        event_rows.append({'event_id': identity, 'scheduled_date': day,
            'schedule_usable_at_event_session_open': covered,
            'coverage_status': 'USABLE_SCHEDULE' if covered else 'NO_MATCHING_USABLE_SCHEDULE',
            'A_existing_position_at_release': _position_at_release(a, event),
            'B_existing_position_at_release': _position_at_release(b, event)})
    original_buy_a = sum(row['action'] == 'BUY' for row in a['result']['signals'])
    original_buy_b = 0
    date_opportunities = 0
    intervention_opportunities = 0
    blocked = 0
    lag_unavailable = 0
    for row in b['result']['signals']:
        reviews = row['event_filter']
        decision = reviews['decision']
        if decision['input_action'] != 'BUY':
            continue
        original_buy_b += 1
        expected = [event for event in expected_events
                    if event['scheduled_date'] == decision['execution_session']]
        date_opportunities += bool(expected)
        # A protected exit can cancel a queued intent before execution review;
        # such an intent is not a live opportunity for the event filter.
        if row.get('execution_disposition') == 'CANCELLED_OLD_POSITION_OPEN_PROTECTION':
            continue
        matching_known = any(version['event_id'] in {e['event_id'] for e in expected}
            and version['schedule']['status'] == 'ANNOUNCED'
            and version['schedule']['date'] == decision['execution_session']
            for review in reviews.values() for version in review['known_versions'])
        intervention_opportunities += matching_known
        blocked += any(review['disposition'] == 'BLOCK_NEW_BUY' for review in reviews.values())
        # Inspect future availability only to diagnose missed coverage, never
        # feed it back into historical decisions or count it as a real block.
        execution_time = pd.Timestamp(decision['execution_time'])
        lag_unavailable += bool(expected) and not matching_known and any(
            version['event_id'] in {e['event_id'] for e in expected}
            and schedule_view(version)['status'] == 'ANNOUNCED'
            and schedule_view(version)['date'] == decision['execution_session']
            and version['version_public_at'] is not None
            and version['availability']['available_at'] is not None
            and pd.Timestamp(version['version_public_at']) <= execution_time
            < pd.Timestamp(version['availability']['available_at'])
            for version in b['event_context']['events'])
    covered = sum(row['schedule_usable_at_event_session_open'] for row in event_rows)
    return {'A_metrics': comparison['A']['metrics'], 'B_metrics': comparison['B']['metrics'],
        'expected_event_count': len(expected_events), 'usable_event_schedule_count': covered,
        'event_schedule_coverage_ratio': covered / len(expected_events),
        'original_A_buy_intents': original_buy_a, 'original_B_path_buy_intents': original_buy_b,
        'B_buy_intents_on_expected_event_dates': date_opportunities,
        'B_intervenable_buy_intents_with_known_schedule': intervention_opportunities,
        'actual_blocked_B_buy_intents': blocked,
        'B_event_date_buy_intents_unavailable_due_to_declared_lag': lag_unavailable,
        'events': event_rows,
        'limitations': ['Expected event coverage is only for the fixed supplied event list, not all market announcements.',
            'A/B intent counts are path dependent after filtering; differences are not causal foregone profit.',
            'Company, fiscal quarter, market date and industry observations are correlated; no independent sample claim.',
            'Outside-RTH position exposure describes this daily model, not actual broker holdings.']}


def run_diagnostics(snapshot, base_spec, context, expected_events):
    """Two predeclared cost cells, three variants each; no parameter search."""
    original = EquityExperimentSpec.from_document(base_spec).document
    # Validate before computing any returns.
    aligned_benchmark_spec(original)
    reports, cells = {}, []
    for multiplier in (1, 2):
        spec = copy.deepcopy(original)
        spec['fee_rate'] *= multiplier
        spec['slippage_pct'] *= multiplier
        if multiplier != 1:
            spec['name'] += ' / fixed 2x cost stress'
        a, b, _ = run_schedule_comparison(snapshot, EquityExperimentSpec.from_document(spec), context)
        benchmark = EquityExperimentRunner().run(snapshot, aligned_benchmark_spec(spec))
        metrics = diagnose_pair(a.document, b.document, expected_events)
        result = benchmark.document['result']
        cells.append({'cost_multiplier': multiplier, 'fee_rate': spec['fee_rate'],
            'slippage_pct': spec['slippage_pct'], 'diagnostics': metrics,
            'aligned_buy_and_hold': {key: result[key] for key in (
                'total_return', 'max_drawdown', 'total_fees', 'fill_count', 'round_trip_count', 'exposure_ratio')},
            'report_hashes': {'A': a.document['report_hash'], 'B': b.document['report_hash'],
                            'aligned_buy_and_hold': benchmark.document['report_hash']}})
        reports[str(multiplier)] = {'A': a, 'B': b, 'aligned_buy_and_hold': benchmark}
    summary = {'schema_version': 'equity-event-diagnostics-v1',
        'scope': 'DESCRIPTIVE_FIXED_COST_DIAGNOSTICS_NOT_STRATEGY_CONFIRMATION',
        'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'snapshot_id': snapshot.snapshot_id, 'base_spec_hash': digest(original),
        'evidence_kind': snapshot.document['evidence_kind'],
        'runtime_source_identity': reports['1']['A'].document['provenance']['source_identity'],
        'score_start_session': original['score_start_session'], 'score_end_session': original['score_end_session'],
        'initial_cash': original['initial_cash'],
        'target_position_pct': original['strategy']['params']['position_pct'],
        'cells': cells, 'order_allowed': False,
        'benchmark_policy': 'Same period, cash, allocation fraction, fees, slippage and end marking. Canonical buy-and-hold requires max_position_pct=1/min_cash_pct=0, but target allocation remains 25%; one entry, no protective exits.',
        'retention': 'Keep every cost cell, negative/no-trade/zero-block result and all fixed event exclusions.'}
    return {**summary, 'diagnostics_hash': digest(summary)}, reports


def main():
    import argparse
    import json
    import sys
    from hakimi_research.equity_dataset import EquitySnapshot
    from hakimi_research.equity_research import replay_equity_report

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot', 'spec', 'event-context', 'expected-events', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    def offline(event, _arguments):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'}:
            raise RuntimeError('equity_diagnostics_network_denied')
    sys.addaudithook(offline)
    def read(path):
        return json.loads(path.read_text(encoding='utf-8-sig'))
    snapshot = EquitySnapshot(read(args.snapshot))
    # A new directory prevents replacing an earlier experiment or its failures.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    inputs = {'snapshot': args.snapshot, 'spec': args.spec,
              'event_context': args.event_context, 'expected_events': args.expected_events}
    before = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inputs.items()}
    summary, reports = run_diagnostics(snapshot, read(args.spec), read(args.event_context), read(args.expected_events))
    verification = []
    for cost, variants in reports.items():
        for name, report in variants.items():
            report.save(args.output_dir / ('cost-' + cost) / name)
            receipt = replay_equity_report(snapshot, report)
            verification.append({'cost_multiplier': int(cost), 'variant': name,
                                 'report_hash': report.document['report_hash'], **receipt})
    after = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inputs.items()}
    if before != after:
        raise RuntimeError('equity_diagnostics_source_changed_during_run')
    payload = {'summary': summary, 'replays': verification, 'input_file_sha256': before,
               'inputs_unchanged': True, 'network_denied': True}
    with (args.output_dir / 'diagnostics.private.json').open('x', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write('\n')
    print(json.dumps({'diagnostics_hash': summary['diagnostics_hash'],
        'reports_saved': len(verification), 'replays_verified': sum(row['replay_verified'] for row in verification),
        'inputs_unchanged': True, 'order_allowed': False}))
    if not all(row['replay_verified'] for row in verification):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
