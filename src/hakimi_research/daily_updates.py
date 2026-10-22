"""Explicit, bounded public daily-price checks over existing equity snapshots.

Only this opt-in adapter makes a public HTTPS request. It neither updates a task
nor advances an account. Each check retains the returned bytes and a new fixed
snapshot; freezing reuses the ordinary immutable input store. Provider claims
remain IMPORTED_UNVERIFIED, including identity and corporate-action coverage.
OHLC uses the existing public-import CSV convention of eight decimal places.
Original full-precision response bytes remain retained; old snapshot values are
compared exactly with new normalized CSV values, without rounding the old data.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import csv
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from importlib.resources import files
import io
import json
import math
from pathlib import Path
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from .documents import digest, parse_document
from .equity_dataset import build_equity_snapshot, verify_equity_snapshot
from .input_workflow import _retain, inspect_input
from .offline_app import _file_lock, immutable_write, write_new

SCHEMA = 'workbench-daily-update-v1'
_MAX = 4 * 1024 * 1024
_NY = ZoneInfo('America/New_York')
_FIELDS = ('open', 'high', 'low', 'close', 'volume')
_STATES = {'READY', 'REVISION_REVIEW_REQUIRED', 'UNCHANGED', 'WAITING_SOURCE_UPDATE',
           'BLOCKED', 'CALENDAR_UNAVAILABLE'}
_NORMALIZATION = 'RAW_UNADJUSTED_OHLC_8_DECIMAL_CSV_V1_VOLUME_EXACT_INTEGER'


class _Stop(ValueError):
    def __init__(self, reason, status='BLOCKED', *, received_raw=None, truncated=False):
        self.reason, self.status = reason, status
        self.received_raw, self.truncated = received_raw, truncated
        super().__init__(reason)


def _require(condition, reason, status='BLOCKED'):
    if not condition:
        raise _Stop(reason, status)


def _stamp(value):
    _require(isinstance(value, datetime) and value.tzinfo is not None, 'UTC_CLOCK_REQUIRED')
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _clock(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def _regular(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('daily_update_link_not_supported')


def _read(path, maximum=64 * 1024 * 1024):
    path = Path(path)
    _regular(path)
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    if not raw or len(raw) > maximum:
        raise ValueError('daily_update_file_size_invalid:' + path.name)
    return raw


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _calendar():
    raw = files('hakimi_research').joinpath('resources/us-equity-calendar-2026.json').read_bytes()
    return parse_document(raw), raw


def _days(calendar, first, last):
    rows = []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        name = day.isoformat()
        if day.weekday() >= 5 or name in calendar['holidays']:
            rows.append(dict(date=name, kind='CLOSED', reason='WEEKEND' if day.weekday() >= 5 else 'HOLIDAY'))
        else:
            close = calendar['early_closes'].get(name, calendar['regular_close'])
            def at(clock):
                return _stamp(datetime.combine(day, time.fromisoformat(clock), _NY))
            rows.append(dict(date=name, kind='OPEN', open_utc=at(calendar['regular_open']),
                close_utc=at(close), early_close=name in calendar['early_closes']))
    return rows


def _last_complete(calendar, now):
    today = now.astimezone(_NY).date()
    first = date(calendar['year'], 1, 1)
    days = _days(calendar, first, today)
    completed = [row for row in days if row['kind'] == 'OPEN'
                 and _clock(row['close_utc']) + timedelta(seconds=60) <= now]
    _require(bool(completed), 'NO_COMPLETED_SESSION_IN_SUPPORTED_YEAR', 'CALENDAR_UNAVAILABLE')
    return completed[-1]['date']


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise _Stop('SOURCE_REDIRECT_REFUSED')


def _fetch(url):
    parsed = urlsplit(url)
    _require(parsed.scheme == 'https' and parsed.netloc == 'query1.finance.yahoo.com'
             and parsed.path.startswith('/v8/finance/chart/'), 'SOURCE_URL_NOT_ALLOWED')
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 HakimiResearch/0.6', 'Accept': 'application/json'})
    try:
        with build_opener(_NoRedirect()).open(request, timeout=12) as response:
            _require(response.geturl() == url and response.status == 200, 'SOURCE_RESPONSE_NOT_SUCCESSFUL')
            raw = response.read(_MAX + 1)
    except HTTPError as exc:
        try:
            raw = exc.read(_MAX + 1)
        except (OSError, TimeoutError):
            raw = None
        raise _Stop('SOURCE_HTTP_' + str(exc.code), received_raw=raw[:_MAX] if raw else None,
                    truncated=bool(raw and len(raw) > _MAX)) from None
    except (URLError, TimeoutError, OSError):
        raise _Stop('SOURCE_REQUEST_FAILED_NO_RETRY') from None
    if not raw or len(raw) > _MAX:
        raise _Stop('SOURCE_RESPONSE_SIZE_INVALID', received_raw=raw[:_MAX] if raw else None,
                    truncated=bool(raw and len(raw) > _MAX))
    return raw


def _source(name, reference, raw, retrieved):
    return dict(name=name, reference=reference, retrieved_at=retrieved,
                raw_base64=base64.b64encode(raw).decode('ascii'))


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _price(value):
    return f'{value:.8f}'.rstrip('0').rstrip('.')


def _rows(raw, baseline, days, latest, retrieved, query_start):
    try:
        doc = parse_document(raw, maximum_bytes=_MAX)
        chart = doc['chart']
        _require(chart.get('error') is None and type(chart.get('result')) is list
                 and len(chart['result']) == 1, 'SOURCE_CHART_UNAVAILABLE')
        result = chart['result'][0]
        meta = result['meta']
        security = baseline['security']
        exchanges = {'XNAS': {'NMS', 'NGM', 'NCM', 'NASDAQ'}, 'XNYS': {'NYQ', 'NYSE'}}
        _require(meta['symbol'] == security['symbol'] and meta['currency'] == security['currency']
                 and meta['exchangeName'] in exchanges[security['exchange']]
                 and meta['instrumentType'] == 'EQUITY'
                 and meta['exchangeTimezoneName'] == 'America/New_York', 'SOURCE_SECURITY_IDENTITY_MISMATCH')
        stamps = result['timestamp']
        quotes = result['indicators']['quote']
        _require(type(stamps) is list and 0 < len(stamps) <= 370 and type(quotes) is list
                 and len(quotes) == 1 and type(quotes[0]) is dict, 'SOURCE_ARRAY_SHAPE_INVALID')
        quote = quotes[0]
        _require(all(type(quote.get(key)) is list and len(quote[key]) == len(stamps) for key in _FIELDS),
                 'SOURCE_ARRAY_LENGTH_MISMATCH')
        adjusted = result['indicators']['adjclose']
        _require(type(adjusted) is list and len(adjusted) == 1
                 and type(adjusted[0].get('adjclose')) is list and len(adjusted[0]['adjclose']) == len(stamps),
                 'SOURCE_ADJUSTMENT_BASIS_UNKNOWN')
        adjusted = adjusted[0]['adjclose']
        expected = {row['date']: row for row in days if row['kind'] == 'OPEN'}
        observed, seen, excluded, pre_window = {}, set(), [], []
        previous = None
        for index, value in enumerate(stamps):
            _require(type(value) is int and value > 0 and (previous is None or value > previous),
                     'SOURCE_TIMESTAMP_DUPLICATE_OR_OUT_OF_ORDER')
            previous = value
            opened = datetime.fromtimestamp(value, timezone.utc)
            day = opened.astimezone(_NY).date().isoformat()
            _require(day not in seen, 'SOURCE_DUPLICATE_SESSION')
            seen.add(day)
            _require(day >= query_start and opened <= retrieved, 'SOURCE_ROW_OUTSIDE_REQUEST_OR_FUTURE')
            if day < days[0]['date']:
                pre_window.append(day)
                continue  # Bounded leading history is source context, never candidate prices.
            if day > latest:
                _require(day == retrieved.astimezone(_NY).date().isoformat(), 'SOURCE_UNEXPECTED_FUTURE_SESSION')
                calendar, _ = _calendar()
                forming = _days(calendar, date.fromisoformat(day), date.fromisoformat(day))[0]
                _require(forming['kind'] == 'OPEN' and opened == _clock(forming['open_utc']),
                         'SOURCE_NON_RTH_FORMING_SESSION')
                excluded.append(day)
                continue  # Forming prices (including null cells) never enter the snapshot.
            _require(day in expected, 'SOURCE_BAR_ON_CLOSED_DATE')
            _require(opened == _clock(expected[day]['open_utc']), 'SOURCE_NON_RTH_DAILY_TIMESTAMP')
            values = [quote[key][index] for key in _FIELDS]
            _require(all(_number(value) for value in values) and all(value > 0 for value in values[:4])
                     and type(values[4]) is int and values[4] >= 0, 'SOURCE_MISSING_OR_INVALID_OHLCV')
            o, h, l, c, _ = values
            _require(h >= max(o, c) and l <= min(o, c) and l <= h, 'SOURCE_OHLC_GEOMETRY_INVALID')
            _require(_number(adjusted[index]) and adjusted[index] == c, 'SOURCE_ADJUSTED_RAW_MISMATCH')
            observed[day] = [float(_price(value)) for value in values[:4]] + [values[4]]
        missing = sorted(set(expected) - set(observed))
        if missing:
            status = 'WAITING_SOURCE_UPDATE' if missing == [latest] else 'BLOCKED'
            raise _Stop('SOURCE_MISSING_COMPLETED_SESSIONS:' + ','.join(missing), status)
        market_time = meta.get('regularMarketTime')
        _require(type(market_time) is int and market_time > 0, 'SOURCE_COMPLETION_CLOCK_MISSING')
        _require(datetime.fromtimestamp(market_time, timezone.utc) <= retrieved, 'SOURCE_COMPLETION_CLOCK_IN_FUTURE')
        _require(market_time >= int(_clock(expected[latest]['close_utc']).timestamp()),
                 'SOURCE_LAST_SESSION_NOT_CONFIRMED_COMPLETE', 'WAITING_SOURCE_UPDATE')
        regular = meta.get('currentTradingPeriod', {}).get('regular')
        _require(type(regular) is dict and type(regular.get('start')) is int and type(regular.get('end')) is int
                 and regular['end'] > regular['start'], 'SOURCE_REGULAR_SESSION_CLOCK_MISSING')
        period_day = datetime.fromtimestamp(regular['start'], _NY).date().isoformat()
        if period_day == latest:
            _require(regular['start'] == int(_clock(expected[latest]['open_utc']).timestamp())
                     and regular['end'] == int(_clock(expected[latest]['close_utc']).timestamp()),
                     'SOURCE_REGULAR_SESSION_CLOCK_MISMATCH')
        _require('events' in result and type(result['events']) is dict, 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN')
        events = result['events']
        _require(set(events) <= {'dividends', 'splits', 'capitalGains'}, 'SOURCE_UNKNOWN_CORPORATE_ACTION_KIND')
        outside_actions = []
        for kind, group in events.items():
            _require(type(group) is dict, 'SOURCE_CORPORATE_ACTION_FORMAT_INVALID')
            for entry in group.values():
                _require(type(entry) is dict and type(entry.get('date')) is int and entry['date'] > 0,
                         'SOURCE_CORPORATE_ACTION_DATE_UNKNOWN')
                action_day = datetime.fromtimestamp(entry['date'], _NY).date().isoformat()
                _require(not days[0]['date'] <= action_day <= latest,
                         'CORPORATE_ACTION_IN_WINDOW:' + kind + ':' + action_day)
                outside_actions.append(dict(kind=kind, date=action_day))
        return observed, excluded, outside_actions, meta, pre_window
    except (KeyError, TypeError, IndexError, OverflowError, OSError) as exc:
        raise _Stop('SOURCE_REQUIRED_FIELDS_INVALID:' + type(exc).__name__) from None


def _candidate(raw, baseline, calendar, calendar_raw, latest, retrieved, url, query_start):
    first = baseline['calendar']['coverage_start']
    days = _days(calendar, date.fromisoformat(first), date.fromisoformat(latest))
    rows, excluded, outside, meta, pre_window = _rows(raw, baseline, days, latest, _clock(retrieved), query_start)
    old = {s['date']: c[1:] for s, c in zip(baseline['sessions'], baseline['candles'])}
    _require(set(old) <= set(rows), 'SOURCE_HISTORICAL_SESSIONS_REMOVED')
    revisions = []
    for day in sorted(set(rows) & set(old)):
        for key, before, after in zip(_FIELDS, old[day], rows[day]):
            if before != after:
                revisions.append(dict(date=day, field=key, old_value=before, new_value=after))
    new_calendar = {row['date']: row for row in days}
    for row in baseline['calendar']['days']:
        if row['date'] in new_calendar and row != new_calendar[row['date']]:
            revisions.append(dict(date=row['date'], field='calendar', old_value=row, new_value=new_calendar[row['date']]))
    new_dates = sorted(set(rows) - set(old))
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('session_date', *_FIELDS))
    writer.writerows((day, *(_price(value) for value in values[:4]), str(values[4]))
                     for day, values in sorted(rows.items()))
    csv_raw = output.getvalue().encode('utf-8')
    identity = deepcopy(baseline['security_identity'])
    identity.pop('security_id')
    identity['source'].pop('raw_sha256')
    identity['source'].pop('truth_status')
    identity['valid_through'] = latest
    identity['selection_basis'] = ('Existing declared common-stock identity; Yahoo symbol, currency, exchange and EQUITY '
        'metadata agree at retrieval. Continued identity is a caller declaration, not independent authentication.')
    manifest = dict(schema_version='us-equity-daily-import-v1', security=baseline['security'], identity=identity,
        calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=latest,
            source=_source('Published NYSE/Nasdaq 2026 schedule; temporary closures not covered',
                calendar['sources'][0], calendar_raw, calendar['recorded_at']), days=days),
        corporate_actions=dict(coverage_start=first, coverage_end=latest, coverage_status='DECLARED_COMPLETE',
            source=_source('Requested Yahoo dividend/split/capital-gain events; completeness is declared, not authenticated',
                url, raw, retrieved), actions=[]),
        price_source=_source('Yahoo chart raw quote OHLCV; source response retained with update check', url, csv_raw, retrieved),
        price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
        completed_bars_only=True, as_of=retrieved, retrieved_at=retrieved, bar_availability_lag_seconds=60,
        evidence_kind='IMPORTED_UNVERIFIED')
    snapshot = build_equity_snapshot(csv_raw, manifest)
    _require(snapshot.document['research_admission']['allowed'], 'UPDATED_SNAPSHOT_NOT_ADMITTED')
    return snapshot.document, new_dates, revisions, dict(excluded_forming_sessions=excluded,
        excluded_pre_window_sessions=pre_window, outside_window_actions=outside,
        source_regular_market_time=meta['regularMarketTime'])


def check_daily_update(baseline_file, output_dir, *, now=None, fetcher=None):
    """Check one imported stock once; callers choose an unused output directory."""
    directory = Path(output_dir).absolute()
    _regular(directory)
    directory.mkdir(parents=True, exist_ok=False)
    checked = _stamp(now if now is not None else datetime.now(timezone.utc))
    core = dict(schema_version=SCHEMA, symbol='', status='BLOCKED', reason='CHECK_NOT_COMPLETED',
        baseline_snapshot_id='', baseline_start=None, baseline_end=None,
        latest_completed_session=None, new_dates=[], revisions=[],
        candidate_snapshot_id=None, can_freeze=False, candidate_sha256=None, source_url=None,
        retrieved_at=None, raw_sha256=None, checked_at=checked, query_start=None, coverage_start=None,
        evidence_kind='IMPORTED_UNVERIFIED',
        normalization_policy=_NORMALIZATION,
        source_truth_verified=False, permissions=dict(account_queries=0, orders=0, economic_runs=0),
        artifacts={}, source_policy='One explicit Yahoo request; no retries, fallback, task binding, or account advance.')
    try:
        baseline_raw = _read(baseline_file)
        immutable_write(directory / 'baseline-snapshot.json', baseline_raw)
        core['artifacts']['baseline-snapshot.json'] = sha256(baseline_raw).hexdigest()
        baseline = verify_equity_snapshot(parse_document(baseline_raw))
        core.update(symbol=baseline['security']['symbol'], baseline_snapshot_id=baseline['snapshot_id'],
                    baseline_start=baseline['calendar']['coverage_start'], baseline_end=baseline['calendar']['coverage_end'])
        _require(baseline['evidence_kind'] == 'IMPORTED_UNVERIFIED' and baseline['research_admission']['allowed'],
                 'IMPORTED_ADMITTED_BASELINE_REQUIRED')
        _require(baseline['bar_availability_lag_seconds'] == 60, 'BASELINE_60_SECOND_LAG_REQUIRED')
        calendar, calendar_raw = _calendar()
        immutable_write(directory / 'calendar.json', calendar_raw)
        core['artifacts']['calendar.json'] = sha256(calendar_raw).hexdigest()
        instant = _clock(checked)
        first = date.fromisoformat(baseline['calendar']['coverage_start'])
        query_start = (first - timedelta(days=120)).isoformat()
        core.update(query_start=query_start, coverage_start=first.isoformat())
        _require(first.year == calendar['year'] == instant.astimezone(_NY).year
                 and date.fromisoformat(baseline['calendar']['coverage_end']).year == calendar['year'],
                 'ONLY_PUBLISHED_2026_CALENDAR_SUPPORTED', 'CALENDAR_UNAVAILABLE')
        _require(_clock(calendar['recorded_at']) <= instant, 'CALENDAR_NOT_YET_RECORDED', 'CALENDAR_UNAVAILABLE')
        latest = _last_complete(calendar, instant)
        core['latest_completed_session'] = latest
        _require(baseline['sessions'][-1]['date'] <= latest and _clock(baseline['retrieved_at']) <= instant,
                 'BASELINE_AFTER_CHECK_TIME')
        end = instant.astimezone(_NY).date() + timedelta(days=1)
        params = dict(period1=int(datetime.combine(date.fromisoformat(query_start), time(), _NY).timestamp()),
            period2=int(datetime.combine(end, time(), _NY).timestamp()), interval='1d',
            events='div,splits', includePrePost='false')
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + baseline['security']['symbol'] + '?' + urlencode(params)
        core['source_url'] = url
        raw = (fetcher or _fetch)(url)
        _require(type(raw) is bytes and bool(raw) and len(raw) <= _MAX, 'SOURCE_RESPONSE_SIZE_INVALID')
        retrieved = _stamp(now if now is not None else datetime.now(timezone.utc))
        _require(_clock(retrieved) >= instant, 'RETRIEVAL_CLOCK_MOVED_BACKWARD')
        immutable_write(directory / 'source-yahoo-chart.json', raw)
        core.update(retrieved_at=retrieved, raw_sha256=sha256(raw).hexdigest())
        core['artifacts']['source-yahoo-chart.json'] = core['raw_sha256']
        _require(_clock(retrieved).astimezone(_NY).year == calendar['year'],
                 'ONLY_PUBLISHED_2026_CALENDAR_SUPPORTED', 'CALENDAR_UNAVAILABLE')
        latest = _last_complete(calendar, _clock(retrieved))
        core['latest_completed_session'] = latest
        candidate, new_dates, revisions, detail = _candidate(raw, baseline, calendar, calendar_raw,
                                                          latest, retrieved, url, query_start)
        core.update(new_dates=new_dates, revisions=revisions, **detail)
        if not new_dates and not revisions:
            core.update(status='UNCHANGED', reason='NO_NEW_OR_REVISED_COMPLETED_BARS')
        else:
            encoded = _json(candidate)
            immutable_write(directory / 'candidate-snapshot.json', encoded)
            core['artifacts']['candidate-snapshot.json'] = sha256(encoded).hexdigest()
            core.update(status='REVISION_REVIEW_REQUIRED' if revisions else 'READY',
                reason='HISTORICAL_VALUES_REVISED_REQUIRES_ACKNOWLEDGEMENT' if revisions else 'NEW_COMPLETED_DAILY_BARS',
                candidate_snapshot_id=candidate['snapshot_id'], candidate_sha256=sha256(encoded).hexdigest(), can_freeze=True)
    except _Stop as exc:
        core.update(status=exc.status, reason=exc.reason)
        if exc.received_raw:
            immutable_write(directory / 'source-yahoo-chart.json', exc.received_raw)
            core.update(retrieved_at=_stamp(now if now is not None else datetime.now(timezone.utc)),
                raw_sha256=sha256(exc.received_raw).hexdigest(), source_response_truncated=exc.truncated)
            core['artifacts']['source-yahoo-chart.json'] = core['raw_sha256']
    except (ValueError, OSError, KeyError, TypeError) as exc:
        core.update(status='BLOCKED', reason='INPUT_OR_SOURCE_INVALID:' + str(exc)[:240])
    write_new(directory / 'check.json', {**core, 'check_hash': digest(core)})
    return read_daily_update(directory)


def _freeze_receipt(directory, checked):
    receipt = parse_document(_read(directory / 'freeze.json'))
    core = {key: value for key, value in receipt.items() if key != 'freeze_hash'}
    if (receipt.get('schema_version') != 'workbench-daily-freeze-v1' or receipt.get('freeze_hash') != digest(core)
            or receipt.get('check_hash') != checked['check_hash']
            or receipt.get('candidate_snapshot_id') != checked['candidate_snapshot_id']
            or receipt.get('input_file_sha256') != checked['candidate_sha256']
            or type(receipt.get('acknowledged_revisions')) is not bool
            or (checked['revisions'] and receipt['acknowledged_revisions'] is not True)):
        raise ValueError('daily_freeze_receipt_identity_invalid')
    expected = 'data/snapshots/' + checked['candidate_snapshot_id'] + '/' + checked['candidate_sha256'] + '.json'
    if receipt.get('input_ref') != expected:
        raise ValueError('daily_freeze_input_reference_invalid')
    return receipt


def read_daily_update(directory):
    directory = Path(directory).absolute()
    checked = parse_document(_read(directory / 'check.json'))
    core = {key: value for key, value in checked.items() if key != 'check_hash'}
    if (checked.get('schema_version') != SCHEMA or checked.get('check_hash') != digest(core)
            or checked.get('status') not in _STATES or type(checked.get('can_freeze')) is not bool
            or checked['can_freeze'] != (checked['status'] in {'READY', 'REVISION_REVIEW_REQUIRED'})):
        raise ValueError('daily_update_check_identity_invalid')
    allowed = {'baseline-snapshot.json', 'calendar.json', 'source-yahoo-chart.json', 'candidate-snapshot.json'}
    if type(checked.get('artifacts')) is not dict or set(checked['artifacts']) - allowed:
        raise ValueError('daily_update_artifact_inventory_invalid')
    for name, expected in checked['artifacts'].items():
        if sha256(_read(directory / name)).hexdigest() != expected:
            raise ValueError('daily_update_artifact_changed:' + name)
    if checked['raw_sha256'] != checked['artifacts'].get('source-yahoo-chart.json'):
        raise ValueError('daily_update_source_identity_invalid')
    if not checked['can_freeze'] and (checked['candidate_snapshot_id'] is not None
            or checked['candidate_sha256'] is not None or 'candidate-snapshot.json' in checked['artifacts']):
        raise ValueError('daily_update_unavailable_candidate_invalid')
    if checked['can_freeze']:
        if set(checked['artifacts']) != allowed or checked['raw_sha256'] != checked['artifacts']['source-yahoo-chart.json']:
            raise ValueError('daily_update_candidate_sources_missing')
        candidate = verify_equity_snapshot(parse_document(_read(directory / 'candidate-snapshot.json')))
        baseline = verify_equity_snapshot(parse_document(_read(directory / 'baseline-snapshot.json')))
        if (candidate['snapshot_id'] != checked['candidate_snapshot_id']
                or candidate['security'] != baseline['security']
                or baseline['snapshot_id'] != checked['baseline_snapshot_id']
                or candidate['sessions'][-1]['date'] != checked['latest_completed_session']
                or candidate['retrieved_at'] != checked['retrieved_at']
                or checked['candidate_sha256'] != checked['artifacts']['candidate-snapshot.json']):
            raise ValueError('daily_update_candidate_identity_invalid')
    result = dict(checked, frozen=False)
    if (directory / 'freeze.json').exists():
        if not checked['can_freeze']:
            raise ValueError('daily_update_unavailable_candidate_cannot_be_frozen')
        result.update(frozen=True, freeze_receipt=_freeze_receipt(directory, checked))
    return result


def freeze_daily_update(directory, workspace, *, acknowledge_revisions=False):
    """Explicitly retain this exact candidate once; old inputs remain untouched."""
    if type(acknowledge_revisions) is not bool:
        raise ValueError('daily_update_acknowledgement_must_be_boolean')
    directory, workspace = Path(directory).absolute(), Path(workspace).absolute()
    _regular(directory); _regular(workspace)
    with _file_lock(directory / '.freeze.lock'):
        checked = read_daily_update(directory)
        if not checked['can_freeze']:
            raise ValueError('daily_update_not_freezable:' + checked['status'])
        if not checked['frozen'] and checked['revisions'] and not acknowledge_revisions:
            raise ValueError('daily_update_historical_revisions_require_acknowledgement')
        if checked['frozen']:
            receipt = checked['freeze_receipt']
            path = workspace / receipt['input_ref']
            if sha256(_read(path)).hexdigest() != receipt['input_file_sha256']:
                raise ValueError('daily_update_frozen_input_changed')
            retained = inspect_input(path)
        else:
            raw = _read(directory / 'candidate-snapshot.json')
            retained = _retain(workspace, raw)
            core = dict(schema_version='workbench-daily-freeze-v1', check_hash=checked['check_hash'],
                candidate_snapshot_id=checked['candidate_snapshot_id'], acknowledged_revisions=acknowledge_revisions,
                input_ref=Path(retained['path']).relative_to(workspace.resolve()).as_posix(),
                input_file_sha256=sha256(raw).hexdigest())
            receipt = {**core, 'freeze_hash': digest(core)}
            write_new(directory / 'freeze.json', receipt)
        return dict(retained, status='DAILY_UPDATE_FROZEN', admission_status='READY', original_bytes_retained=True,
            check_hash=checked['check_hash'], acknowledged_revisions=receipt['acknowledged_revisions'],
            freeze_hash=receipt['freeze_hash'])
