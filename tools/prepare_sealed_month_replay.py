"""Derive a fixed historical month from sealed local Yahoo bytes, without fetching.

This repository-only preparation does not run economics or change old inputs.
Its source receipt is retrospective; it is not historical receipt-time evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import struct

from hakimi_research import daily_updates as updates
from hakimi_research.documents import digest, parse_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.equity_dataset import build_equity_snapshot, verify_equity_snapshot
from hakimi_research.equity_research import EquityExperimentSpec, SPEC_SCHEMA
from hakimi_research.experiment import required_context


DESIGN_SCHEMA = 'fixed-month-replay-design-v1'
AMENDED_DESIGN_SCHEMA = 'fixed-month-replay-design-v2'
MODE = 'HISTORICAL_PREFIX_ISOLATION_REPLAY_NOT_BLIND_NOT_NATURAL_FORWARD'
HISTORICAL_POLICY = {
    'id': 'YAHOO_QUOTE_POST_WINDOW_DIVIDEND_RECONCILIATION_V1',
    'strategy_fields': ['open', 'high', 'low', 'close', 'volume'],
    'adjusted_close_used_for_strategy': False, 'events_used_for_strategy': False,
    'require_no_in_window_actions': True, 'require_no_splits_through_source_acquisition': True,
    'require_all_post_window_adjustments_explained': True, 'max_adjusted_close_error_float32_ulps': 2,
    'require_close_and_adjusted_exact_float32_values': True,
    'verify_entire_context_to_source_latest_complete': True,
    'require_last_event_following_factor_one': True,
    'price_transformation': 'Select original quote OHLCV only; retain the existing explicit 8-decimal CSV convention. Never replace adjusted close, reverse adjust, fill gaps or repair source values.',
    'source_authority': 'IMPORTED_UNVERIFIED; internally reconciled retrospective field basis, not independently authenticated historical point-in-time prices.',
    'reference': 'https://in.help.yahoo.com/kb/adjusted-close-sln28256.html',
}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _clock(value):
    _require(type(value) is str and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value),
        'sealed_replay_exact_utc_time_required')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def _read(path, expected=None):
    raw = updates._read(path)
    if expected is not None:
        _require(sha256(raw).hexdigest() == expected, 'sealed_replay_source_hash_changed:' + Path(path).name)
    return raw


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if type(value) is bytes else updates._json(value))


def _amendment(design):
    _require(design.get('historical_price_policy') == HISTORICAL_POLICY,
             'sealed_replay_historical_policy_changed')
    amendment = design['amends']
    old = parse_document(_read(amendment['original_design_path'], amendment['original_design_sha256']))
    _require(old.get('schema_version') == DESIGN_SCHEMA and old.get('plan_hash') == amendment['original_plan_hash']
             and old['plan_hash'] == digest({k: v for k, v in old.items() if k != 'plan_hash'}),
             'sealed_replay_original_design_invalid')
    _require(_clock(old['recorded_at']) < _clock(design['recorded_at']), 'sealed_replay_amendment_time_invalid')
    metadata = {'schema_version', 'recorded_at', 'amends', 'historical_price_policy', 'execution_policy_notes', 'plan_hash'}
    _require({k: v for k, v in old.items() if k not in metadata} ==
             {k: v for k, v in design.items() if k not in metadata},
             'sealed_replay_amendment_changed_frozen_economic_or_source_fields')
    stopped_path = Path(amendment['stopped_receipt_path'])
    stopped = parse_document(_read(stopped_path, amendment['stopped_receipt_sha256']))
    _require(stopped.get('plan_hash') == old['plan_hash'] and stopped.get('status') == 'STOPPED'
             and stopped.get('economic_runs') == 0 and stopped.get('retained_complete') is True
             and set(stopped['symbols']) == set(design['sources'])
             and all(row.get('status') == 'STOPPED' and row.get('reason') == 'SOURCE_ADJUSTED_RAW_MISMATCH'
                     for row in stopped['symbols'].values()), 'sealed_replay_original_stop_invalid')
    _require(_clock(old['recorded_at']) <= _clock(stopped['prepared_at']) < _clock(design['recorded_at']),
             'sealed_replay_stop_amendment_chronology_invalid')
    for name, expected in stopped['files'].items():
        target = stopped_path.parent / name
        _require(target.resolve().is_relative_to(stopped_path.parent.resolve()), 'sealed_replay_old_evidence_path_invalid')
        _read(target, expected)
    diagnostic = parse_document(_read(amendment['diagnostic_path'], amendment['diagnostic_sha256']))
    _require(diagnostic.get('plan_hash') == old['plan_hash'] and diagnostic.get('economic_runs') == 0
             and set(diagnostic['symbols']) == set(design['sources'])
             and all(diagnostic['symbols'][symbol]['raw_sha256'] == source['raw_sha256']
                     for symbol, source in design['sources'].items()), 'sealed_replay_diagnostic_identity_invalid')


def _design(path):
    raw = _read(path)
    design = parse_document(raw)
    _require(design.get('schema_version') in {DESIGN_SCHEMA, AMENDED_DESIGN_SCHEMA} and design.get('mode') == MODE,
             'sealed_replay_design_schema_or_scope_invalid')
    _require(design.get('plan_hash') == digest({k: v for k, v in design.items() if k != 'plan_hash'}),
             'sealed_replay_design_hash_changed')
    if design['schema_version'] == AMENDED_DESIGN_SCHEMA:
        _amendment(design)
    recorded = _clock(design['recorded_at'])
    _require(recorded <= datetime.now(timezone.utc), 'sealed_replay_design_time_in_future')
    _require(design['cost_multipliers'] == [1, 2, 3] and design['benchmarks'] == ['cash', 'buy_and_hold'],
             'sealed_replay_cost_and_benchmarks_changed')
    _require(design['strategy']['name'] == 'dual_ma', 'sealed_replay_strategy_not_supported')
    _require(type(design['context_sessions']) is int and design['context_sessions'] == required_context(
        design['strategy']['name'], design['strategy']['params']), 'sealed_replay_context_changed')
    first, start, end = (date.fromisoformat(design[k]) for k in ('context_start', 'score_start', 'score_end'))
    _require(first < start <= end and (end - first).days <= 366,
             'sealed_replay_fixed_window_invalid')
    _require(type(design['sources']) is dict and bool(design['sources']), 'sealed_replay_sources_required')
    _require(all(type(symbol) is str and re.fullmatch(r'[A-Z][A-Z0-9.-]{0,10}', symbol)
                 for symbol in design['sources']), 'sealed_replay_symbol_invalid')
    runtime = build_runtime_provenance()
    _require(runtime['source_identity']['content_sha256'] == design['execution_runtime_source_sha256']
             and runtime['environment_verified']['status'] == 'VERIFIED',
             'sealed_replay_execution_identity_changed')
    calendar_raw = _read(design['calendar_path'], design['calendar_sha256'])
    return design, raw, calendar_raw


def _window_reply(raw, source, days, retrieved, calendar):
    """Validate complete source structure/timestamps before excluding its tail.

    Price values outside the fixed window are never interpreted or repaired.
    Selected prices, adjustment basis and every original event remain subject
    to the existing daily-update checks, including outside-window event syntax.
    """
    doc = parse_document(raw, maximum_bytes=updates._MAX)
    chart = doc['chart']
    _require(chart.get('error') is None and type(chart.get('result')) is list and len(chart['result']) == 1,
             'SOURCE_CHART_UNAVAILABLE')
    result = chart['result'][0]
    stamps = result['timestamp']
    quotes = result['indicators']['quote']
    adjusted = result['indicators'].get('adjclose')
    _require(type(stamps) is list and 0 < len(stamps) <= updates._MAX_SOURCE_ROWS,
             'SOURCE_ROW_LIMIT_EXCEEDED')
    _require(type(quotes) is list and len(quotes) == 1 and type(quotes[0]) is dict,
             'SOURCE_ARRAY_SHAPE_INVALID')
    _require(all(type(quotes[0].get(key)) is list and len(quotes[0][key]) == len(stamps)
                 for key in updates._FIELDS), 'SOURCE_ARRAY_LENGTH_MISMATCH')
    _require(type(adjusted) is list and len(adjusted) == 1 and type(adjusted[0]) is dict
             and type(adjusted[0].get('adjclose')) is list and len(adjusted[0]['adjclose']) == len(stamps),
             'SOURCE_ADJUSTMENT_BASIS_UNKNOWN')
    first, last = days[0]['date'], days[-1]['date']
    query_start = source['query_start']
    source_days = updates._days(calendar, date.fromisoformat(query_start), retrieved.astimezone(updates._NY).date())
    source_opens = {row['date']: row['open_utc'] for row in source_days if row['kind'] == 'OPEN'}
    selected, excluded, seen = [], [], set()
    previous = None
    for index, stamp in enumerate(stamps):
        _require(type(stamp) is int and stamp > 0 and (previous is None or stamp > previous),
                 'SOURCE_TIMESTAMP_DUPLICATE_OR_OUT_OF_ORDER')
        previous = stamp
        opened = datetime.fromtimestamp(stamp, timezone.utc)
        day = opened.astimezone(updates._NY).date().isoformat()
        _require(day not in seen, 'SOURCE_DUPLICATE_SESSION')
        seen.add(day)
        _require(day >= query_start and opened <= retrieved, 'SOURCE_ROW_OUTSIDE_REQUEST_OR_FUTURE')
        _require(day in source_opens and opened == _clock(source_opens[day]), 'SOURCE_NON_RTH_DAILY_TIMESTAMP')
        (selected if first <= day <= last else excluded).append(index)
    sliced = deepcopy(doc)
    target = sliced['chart']['result'][0]
    target['timestamp'] = [stamps[i] for i in selected]
    target['indicators']['quote'] = [{key: [quotes[0][key][i] for i in selected] for key in updates._FIELDS}]
    target['indicators']['adjclose'] = [{'adjclose': [adjusted[0]['adjclose'][i] for i in selected]}]
    return updates._json(sliced), len(stamps), len(excluded)


def _float32_ulp(value):
    _require(updates._number(value) and value > 0, 'SOURCE_FLOAT32_VALUE_INVALID')
    try:
        packed = struct.pack('>f', value)
        exact = struct.unpack('>f', packed)[0]
        next_value = struct.unpack('>f', struct.pack('>I', struct.unpack('>I', packed)[0] + 1))[0]
    except (OverflowError, struct.error):
        raise ValueError('SOURCE_FLOAT32_VALUE_INVALID') from None
    _require(exact == value and math.isfinite(next_value), 'SOURCE_VALUE_NOT_EXACT_FINITE_FLOAT32')
    return next_value - exact


def _historical_rows(original, baseline, design, source, retrieved, calendar):
    """Reconcile retrospective adjustments without changing any quote/adj value.

    This is a separately versioned importer policy. The recent-update adapter's
    exact adjusted/close equality guard is not called or modified on this path.
    """
    result = parse_document(original)['chart']['result'][0]
    meta, security = result['meta'], baseline['security']
    exchanges = {'XNAS': {'NMS', 'NGM', 'NCM', 'NASDAQ'}, 'XNYS': {'NYQ', 'NYSE'}}
    _require(meta['symbol'] == security['symbol'] and meta['currency'] == security['currency']
             and meta['exchangeName'] in exchanges[security['exchange']] and meta['instrumentType'] == 'EQUITY'
             and meta['exchangeTimezoneName'] == 'America/New_York', 'SOURCE_SECURITY_IDENTITY_MISMATCH')
    latest = source['latest_completed_session']
    _require(latest == updates._last_complete(calendar, _clock(source.get('checked_at', source['retrieved_at'])))
             and latest >= design['score_end'], 'SOURCE_LATEST_COMPLETED_SESSION_CONFLICT')
    days = updates._days(calendar, date.fromisoformat(design['context_start']), date.fromisoformat(latest))
    opens = [row for row in days if row['kind'] == 'OPEN']
    complete_close = _clock(opens[-1]['close_utc'])
    _require(complete_close.timestamp() + 60 <= retrieved.timestamp(), 'SOURCE_LAST_SESSION_NOT_CONFIRMED_COMPLETE')
    market_time = meta.get('regularMarketTime')
    _require(type(market_time) is int and market_time > 0, 'SOURCE_COMPLETION_CLOCK_MISSING')
    _require(datetime.fromtimestamp(market_time, timezone.utc) <= retrieved, 'SOURCE_COMPLETION_CLOCK_IN_FUTURE')
    _require(market_time >= int(complete_close.timestamp()), 'SOURCE_LAST_SESSION_NOT_CONFIRMED_COMPLETE')
    regular = meta.get('currentTradingPeriod', {}).get('regular')
    _require(type(regular) is dict and type(regular.get('start')) is int and type(regular.get('end')) is int
             and regular['end'] > regular['start'], 'SOURCE_REGULAR_SESSION_CLOCK_MISSING')
    if datetime.fromtimestamp(regular['start'], updates._NY).date().isoformat() == latest:
        _require(regular['start'] == int(_clock(opens[-1]['open_utc']).timestamp())
                 and regular['end'] == int(complete_close.timestamp()), 'SOURCE_REGULAR_SESSION_CLOCK_MISMATCH')
    stamps, quote = result['timestamp'], result['indicators']['quote'][0]
    adjusted = result['indicators']['adjclose'][0]['adjclose']
    date_indices = {datetime.fromtimestamp(stamp, updates._NY).date().isoformat(): index
                    for index, stamp in enumerate(stamps)}
    _require(all(row['date'] in date_indices for row in opens), 'SOURCE_MISSING_COMPLETED_SESSIONS')
    expected = {row['date']: row for row in opens}
    for day in expected:
        index = date_indices[day]
        values = [quote[key][index] for key in updates._FIELDS]
        _require(all(updates._number(value) for value in values) and all(value > 0 for value in values[:4])
                 and type(values[4]) is int and values[4] >= 0, 'SOURCE_MISSING_OR_INVALID_OHLCV')
        opening, high, low, close, _ = values
        _require(high >= max(opening, close) and low <= min(opening, close) and low <= high,
                 'SOURCE_OHLC_GEOMETRY_INVALID')
        _float32_ulp(close)
        _float32_ulp(adjusted[index])
    _require('events' in result and type(result['events']) is dict, 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')
    _require(set(result['events']) <= {'dividends', 'splits', 'capitalGains'}, 'SOURCE_UNKNOWN_CORPORATE_ACTION_KIND')
    all_calendar = updates._days(calendar, date.fromisoformat(source['query_start']), retrieved.astimezone(updates._NY).date())
    trading_dates = [row['date'] for row in all_calendar if row['kind'] == 'OPEN']
    events, dividends = [], []
    for kind, group in result['events'].items():
        _require(type(group) is dict, 'SOURCE_CORPORATE_ACTION_FORMAT_INVALID')
        for key, entry in group.items():
            _require(type(entry) is dict and type(entry.get('date')) is int and entry['date'] > 0,
                     'SOURCE_CORPORATE_ACTION_DATE_UNKNOWN')
            occurred = datetime.fromtimestamp(entry['date'], timezone.utc)
            day = occurred.astimezone(updates._NY).date().isoformat()
            _require(source['query_start'] <= day and occurred <= retrieved and day in trading_dates,
                     'SOURCE_CORPORATE_ACTION_DATE_OUTSIDE_RECEIPT_OR_CALENDAR')
            _require(not design['context_start'] <= day <= design['score_end'], 'CORPORATE_ACTION_IN_WINDOW:' + kind + ':' + day)
            _require(not (day >= design['context_start'] and kind != 'dividends'),
                     'SOURCE_SPLIT_OR_CAPITAL_GAIN_THROUGH_RECEIPT')
            events.append(dict(kind=kind, date=day, event_key=key, event_sha256=digest(entry)))
            if kind == 'dividends':
                amount = entry.get('amount')
                _require(updates._number(amount) and amount > 0, 'SOURCE_ORDINARY_CASH_DIVIDEND_AMOUNT_INVALID')
                if day > design['score_end']:
                    position = trading_dates.index(day)
                    _require(position > 0 and day <= latest and day in date_indices,
                             'SOURCE_DIVIDEND_ADJACENT_SESSION_MISSING')
                    prior = trading_dates[position - 1]
                    _require(prior in date_indices, 'SOURCE_DIVIDEND_ADJACENT_SESSION_MISSING')
                    prior_close = quote['close'][date_indices[prior]]
                    _float32_ulp(prior_close)
                    _require(amount < prior_close, 'SOURCE_ORDINARY_CASH_DIVIDEND_AMOUNT_INVALID')
                    dividends.append(dict(date=day, prior_session=prior, event_sha256=digest(entry),
                                          multiplier=1.0 - amount / prior_close))
    _require(bool(dividends), 'SOURCE_EXPLAINING_POST_WINDOW_DIVIDEND_REQUIRED')
    _require(len({row['date'] for row in dividends}) == len(dividends), 'SOURCE_DUPLICATE_DIVIDEND_DATE')
    dividends.sort(key=lambda row: row['date'])
    factors = []
    for day in expected:
        index = date_indices[day]
        close, adjusted_close = quote['close'][index], adjusted[index]
        factor = math.prod(row['multiplier'] for row in dividends if row['date'] > day)
        ulps = abs(adjusted_close - close * factor) / _float32_ulp(adjusted_close)
        _require(math.isfinite(ulps) and ulps <= 2, 'SOURCE_POST_WINDOW_ADJUSTMENT_UNEXPLAINED:' + day)
        if day >= dividends[-1]['date']:
            _require(factor == 1.0 and adjusted_close == close, 'SOURCE_LAST_EVENT_FOLLOWING_FACTOR_NOT_ONE')
        factors.append(dict(date=day, factor=factor, error_float32_ulps=ulps))
    selected = {day: [float(updates._price(quote[key][date_indices[day]])) for key in updates._FIELDS[:4]]
                     + [quote['volume'][date_indices[day]]] for day in expected if day <= design['score_end']}
    field_map = [dict(date=day, source_index=date_indices[day],
        original_quote_fields_sha256=digest({key: quote[key][date_indices[day]] for key in updates._FIELDS}),
        csv_fields_sha256=digest([day, *(updates._price(value) for value in values[:4]), str(values[4])]))
        for day, values in selected.items()]
    diagnostic = dict(policy=HISTORICAL_POLICY, original_raw_sha256=sha256(original).hexdigest(),
        source_latest_completed_session=latest, reconciled_rows=len(factors),
        selected_rows=len(selected), events=events, post_window_dividends=dividends,
        factor_path=factors, max_error_float32_ulps=max(row['error_float32_ulps'] for row in factors),
        last_event_following_factor_one=True, price_adjustment_applied=False,
        csv_decimal_places=8, original_source_fields_retained_in_original_raw=True,
        adjusted_close_used_for_strategy=False, future_events_used_for_strategy=False,
        diagnostic_not_historical_source_authentication=True,
        selected_field_path='chart.result[0].indicators.quote[0]', field_to_csv_map=field_map)
    return selected, diagnostic


def _prepare_symbol(design, symbol, folder, calendar_raw):
    source = design['sources'][symbol]
    _require(re.fullmatch(r'[A-Z][A-Z0-9.-]{0,10}', symbol), 'sealed_replay_symbol_invalid')
    original = _read(source['raw_source_path'], source['raw_sha256'])
    baseline_raw = _read(source['baseline_snapshot_path'], source['baseline_sha256'])
    check_raw = _read(source['source_check_path'], source['source_check_sha256'])
    # Preserve the source and declarations before parsing market values.
    _write(folder / 'source-original.json', original)
    _write(folder / 'baseline-original.json', baseline_raw)
    _write(folder / 'source-check-original.json', check_raw)
    check = parse_document(check_raw)
    _require(check['symbol'] == symbol and check['raw_sha256'] == source['raw_sha256']
             and check['retrieved_at'] == source['retrieved_at'] and check['source_url'] == source['reference'],
             'sealed_replay_source_receipt_mismatch')
    retrieved = _clock(source['retrieved_at'])
    _require(retrieved <= _clock(design['recorded_at']), 'sealed_replay_source_acquired_after_design')
    baseline = verify_equity_snapshot(parse_document(baseline_raw))
    _require(baseline['security']['symbol'] == symbol, 'sealed_replay_baseline_symbol_mismatch')
    calendar, installed_calendar_raw = updates._calendar_window(
        date.fromisoformat(check['query_start']).year, retrieved.astimezone(updates._NY).year,
        baseline['security']['exchange'])
    _require(installed_calendar_raw == calendar_raw, 'sealed_replay_calendar_identity_changed')
    _require(_clock(calendar['recorded_at']) <= retrieved, 'CALENDAR_NOT_YET_RECORDED')
    days = updates._days(calendar, date.fromisoformat(design['context_start']), date.fromisoformat(design['score_end']))
    dates = [row['date'] for row in days if row['kind'] == 'OPEN']
    context_dates = [value for value in dates if value < design['score_start']]
    score_dates = [value for value in dates if value >= design['score_start']]
    _require(context_dates == design['context_dates'] and len(context_dates) == design['context_sessions']
             and score_dates == design['score_sessions'] and score_dates[0] == design['score_start']
             and score_dates[-1] == design['score_end'], 'sealed_replay_calendar_partition_changed')
    derived, source_count, excluded_count = _window_reply(original, check, days, retrieved, calendar)
    _write(folder / 'source-window-derived.json', derived)
    reconciliation = None
    if design['schema_version'] == AMENDED_DESIGN_SCHEMA:
        rows, reconciliation = _historical_rows(original, baseline, design, check, retrieved, calendar)
        outside = reconciliation['events']
        _write(folder / 'historical-adjustment-reconciliation.json', reconciliation)
    else:
        rows, forming, outside, meta, pre_window = updates._rows(
            derived, baseline, days, design['score_end'], retrieved, check['query_start'], calendar)
        _require(not forming and not pre_window, 'sealed_replay_window_filter_incomplete')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(('session_date', *updates._FIELDS))
    writer.writerows((day, *(updates._price(value) for value in values[:4]), str(values[4]))
                    for day, values in sorted(rows.items()))
    csv_raw = stream.getvalue().encode('utf-8')
    declaration = source['historical_identity_declaration']
    _require(type(declaration) is str and declaration.strip() == declaration and len(declaration) >= 80,
             'sealed_replay_explicit_historical_identity_declaration_required')
    security = deepcopy(baseline['security'])
    security['security_id'] = 'REPLAY:' + symbol + ':' + design['plan_hash'][:20]
    first, last = design['context_start'], design['score_end']
    manifest = dict(schema_version='us-equity-daily-import-v1', security=security,
        identity=dict(stable_within_coverage=True, valid_from=first, valid_through=last,
            selection_basis='New importer declaration recorded ' + design['recorded_at'] + '. ' + declaration,
            source=updates._source('Retrospective metadata supporting a new unverified replay declaration',
                                   source['reference'], original, source['retrieved_at'])),
        calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=last, days=days,
            source=updates._source('Published calendar; retrospective session reconstruction',
                                   calendar['sources'][0], calendar_raw, calendar['recorded_at'])),
        corporate_actions=dict(coverage_start=first, coverage_end=last, coverage_status='DECLARED_COMPLETE',
            actions=[], source=updates._source('Original retained Yahoo dividend/split coverage; not authenticated',
                                               source['reference'], original, source['retrieved_at'])),
        price_source=updates._source('Fixed-window derived CSV; original response and derivation separately retained',
            'urn:sealed-month-replay:' + design['plan_hash'] + ':' + symbol, csv_raw, source['retrieved_at']),
        price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
        completed_bars_only=True, as_of=source['retrieved_at'], retrieved_at=source['retrieved_at'],
        bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
    snapshot = build_equity_snapshot(csv_raw, manifest).document
    _require(snapshot['research_admission']['allowed'], 'sealed_replay_snapshot_not_admitted')
    spec = dict(schema_version=SPEC_SCHEMA, name=symbol + ' fixed historical month replay',
        snapshot_id=snapshot['snapshot_id'], score_start_session=design['score_start'],
        score_end_session=design['score_end'], **{key: deepcopy(design[key]) for key in
        ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy',
         'execution_policy', 'quantity_policy', 'purpose')})
    EquityExperimentSpec.from_document(spec)
    _write(folder / 'prices-derived.csv', csv_raw)
    _write(folder / 'import-manifest.json', manifest)
    _write(folder / 'snapshot.json', snapshot)
    _write(folder / 'spec.json', spec)
    return dict(status='READY', symbol=symbol, snapshot_id=snapshot['snapshot_id'],
        source_rows=source_count, excluded_source_rows=excluded_count, selected_rows=len(rows),
        source_sha256=source['raw_sha256'], derived_source_sha256=sha256(derived).hexdigest(),
        csv_sha256=sha256(csv_raw).hexdigest(), source_retrieved_at=source['retrieved_at'],
        original_security_id=baseline['security']['security_id'], replay_security_id=security['security_id'],
        historical_identity_authenticated=False, original_identity_coverage_reused=False,
        historical_receipt_time_proven=False, blind_holdout_proven=False,
        outside_window_action_count=len(outside), automatic_window_reselection=False,
        historical_price_policy=HISTORICAL_POLICY['id'] if reconciliation is not None else None,
        reconciliation_sha256=digest(reconciliation) if reconciliation is not None else None,
        snapshot_path=str((folder / 'snapshot.json').resolve()), spec_path=str((folder / 'spec.json').resolve()))


def _retained_originals(folder, source):
    """Describe copied evidence, including absent or partially copied originals."""
    result = {}
    for name, key in (('source-original.json', 'raw_sha256'),
                      ('baseline-original.json', 'baseline_sha256'),
                      ('source-check-original.json', 'source_check_sha256')):
        path = folder / name
        expected = source.get(key)
        actual = sha256(_read(path)).hexdigest() if path.is_file() else None
        result[name] = dict(expected_sha256=expected, retained_sha256=actual,
                            matches_design=actual is not None and actual == expected)
    return result


def prepare(design_path, output_dir):
    """Prepare both sealed symbols once; STOP artifacts never trigger reselection."""
    design, design_raw, calendar_raw = _design(design_path)
    updates._regular(Path(output_dir))
    output = Path(output_dir).resolve()
    _require(not output.exists(), 'sealed_replay_output_exists_no_overwrite_or_retry')
    input_paths = [Path(design_path).resolve(), Path(design['calendar_path']).resolve()]
    for source in design['sources'].values():
        input_paths += [Path(source[key]).resolve() for key in
                        ('raw_source_path', 'baseline_snapshot_path', 'source_check_path')]
    _require(all(not p.is_relative_to(output) for p in input_paths), 'sealed_replay_output_contains_source')
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'research-design.json', design_raw)
    _write(output / 'calendar-original.json', calendar_raw)
    results = {}
    for symbol in sorted(design['sources']):
        try:
            result = _prepare_symbol(design, symbol, output / symbol, calendar_raw)
        except (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError) as error:
            # Numeric observations stay in the retained source; stdout only has the reason.
            result = dict(status='STOPPED', symbol=symbol, reason=str(error), automatic_retry=False,
                          automatic_window_reselection=False, economic_runs=0)
        retained = _retained_originals(output / symbol, design['sources'][symbol])
        result.update(retained_files=retained,
                      retained_complete=all(row['matches_design'] for row in retained.values()))
        _write(output / symbol / 'preparation.json', result)
        results[symbol] = result
    retained_files = {symbol + '/' + name: row for symbol, result in results.items()
                      for name, row in result['retained_files'].items()}
    retained_complete = all(row['matches_design'] for row in retained_files.values())
    receipt = dict(schema_version='sealed-month-replay-preparation-v2' if design['schema_version'] == AMENDED_DESIGN_SCHEMA
                   else 'sealed-month-replay-preparation-v1', plan_hash=design['plan_hash'],
        status='READY' if all(row['status'] == 'READY' for row in results.values()) else 'STOPPED',
        mode=MODE, prepared_at=updates._stamp(datetime.now(timezone.utc)), symbols=results,
        retained_files=retained_files, retained_complete=retained_complete,
        original_source_bytes_retained=retained_complete, derived_bytes_are_not_provider_originals=True,
        source_acquisition_not_backdated=True, economic_runs=0, network_requests=0,
        preparer_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        files={p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest()
               for p in sorted(output.rglob('*')) if p.is_file()})
    _write(output / 'preparation.json', receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args(argv)
    result = prepare(args.design, args.output_dir)
    print(json.dumps({key: result[key] for key in ('status', 'plan_hash', 'symbols', 'economic_runs', 'network_requests')},
                     ensure_ascii=False, allow_nan=False))
    return 0 if result['status'] == 'READY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
