"""First-use adapters over existing immutable inputs and daily-source guards.

No strategy is run here. A source check retains a review candidate; only an
explicit exact-security confirmation publishes an ordinary equity snapshot.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from importlib.resources import files
import io
from pathlib import Path
import re
from urllib.parse import urlencode

from . import daily_updates as daily
from .documents import digest, parse_document
from .equity_dataset import build_equity_snapshot
from .input_workflow import _retain, inspect_input
from .offline_app import _file_lock, immutable_write, write_new
from .strategy_registry import required_task_context


SCHEMA = 'workbench-stock-intake-v1'
HISTORY_SESSIONS = (20, 60, 120)
_EXCHANGES = {'NMS': 'XNAS', 'NGM': 'XNAS', 'NCM': 'XNAS', 'NASDAQ': 'XNAS', 'NYQ': 'XNYS', 'NYSE': 'XNYS'}
_STATES = {'REVIEW_REQUIRED', 'BLOCKED', 'WAITING_SOURCE_UPDATE', 'CALENDAR_UNAVAILABLE', 'UNKNOWN'}
INTRO_PARAMS = dict(fast_window=5, slow_window=10, position_pct=.25, stop_loss_pct=.03, take_profit_pct=.06)


def first_use_catalog():
    example = dict(title='虚构行情操作示例', strategy='price.dual_ma@1',
        params=dict(INTRO_PARAMS, fast_window=2, slow_window=4), score_start='2024-11-11', score_end='2024-12-03',
        initial_cash=10000, fee_rate=.0008, slippage_pct=.0005)
    intro = dict(title='双均线入门 5/10', strategy='price.dual_ma@1', params=deepcopy(INTRO_PARAMS),
                 initial_cash=10000, fee_rate=.0008, slippage_pct=.0005, score_start=None, score_end=None)
    return dict(examples=[dict(id='dual_ma_intro', title='双均线操作示例', evidence_kind='SYNTHETIC_TEST', suggested_task=example,
        description='固定虚构行情，仅用于体验操作；不会自动运行。')], history_sessions=list(HISTORY_SESSIONS), history_count_kind='TOTAL_COMPLETED_SESSIONS_INCLUDING_CONTEXT',
        real_stock_template=dict(id='dual_ma_5_10_intro', title='双均线入门 5/10', strategy='price.dual_ma@1',
            params=deepcopy(INTRO_PARAMS), suggested_task=intro, initial_cash=10000, fee_rate=.0008, slippage_pct=.0005,
            description='显式入门模板，不改变现有 20/60 默认或旧任务；不代表推荐或有效性证明。'))


def _suggested(snapshot, *, example=False):
    params = dict(INTRO_PARAMS, fast_window=2, slow_window=4) if example else dict(INTRO_PARAMS)
    required = required_task_context('price.dual_ma@1', params)
    sessions = snapshot['sessions']
    return dict(title='虚构行情操作示例' if example else snapshot['security']['symbol'] + ' 双均线入门 5/10',
        strategy='price.dual_ma@1', params=params,
        score_start='2024-11-11' if example else (sessions[required]['date'] if len(sessions) > required else None),
        score_end=sessions[-1]['date'], initial_cash=10000, fee_rate=.0008, slippage_pct=.0005)


def load_example(workspace, example):
    if example != 'dual_ma_intro':
        raise ValueError('first_use_example_not_supported')
    resource = files('hakimi_research').joinpath('resources')
    snapshot = build_equity_snapshot(resource.joinpath('trade-demo.csv').read_bytes(),
                                     resource.joinpath('trade-demo-import.json').read_bytes()).document
    if snapshot['evidence_kind'] != 'SYNTHETIC_TEST':
        raise ValueError('first_use_example_must_be_synthetic')
    retained = _retain(workspace, daily._json(snapshot))
    return dict(retained, example=example, suggested_task=_suggested(snapshot, example=True), new_economic_runs=0)


def _coverage(now, count, exchange):
    year = now.astimezone(daily._NY).year
    supported = daily.calendar_support()['supported_years']
    first_year = max(min(supported), year - 1)
    calendar, raw = daily._calendar_window(first_year, year, exchange)
    daily._require(daily._clock(calendar['recorded_at']) <= now, 'CALENDAR_NOT_YET_RECORDED', 'CALENDAR_UNAVAILABLE')
    latest = daily._last_complete(calendar, now)
    opened = [row for row in daily._days(calendar, date(first_year, 1, 1), date.fromisoformat(latest)) if row['kind'] == 'OPEN']
    daily._require(len(opened) >= count, 'INTAKE_HISTORY_EXCEEDS_AVAILABLE_CALENDAR', 'CALENDAR_UNAVAILABLE')
    first = opened[-count]['date']
    days = daily._days(calendar, date.fromisoformat(first), date.fromisoformat(latest))
    return calendar, raw, days, first, latest


def _security(raw, symbol, intake_id):
    try:
        chart = parse_document(raw, maximum_bytes=daily._MAX)['chart']
        daily._require(chart.get('error') is None and type(chart.get('result')) is list and len(chart['result']) == 1,
                       'SOURCE_CHART_UNAVAILABLE')
        meta = chart['result'][0]['meta']
        daily._require(meta['symbol'] == symbol and meta['currency'] == 'USD'
                       and meta['instrumentType'] == 'EQUITY' and meta['exchangeName'] in _EXCHANGES
                       and meta['exchangeTimezoneName'] == 'America/New_York'
                       and meta.get('dataGranularity') == '1d', 'SOURCE_SECURITY_IDENTITY_MISMATCH')
        name = meta.get('longName') or meta.get('shortName') or symbol
        daily._require(type(name) is str and 0 < len(name) <= 180 and not any(ord(c) < 32 for c in name),
                       'SOURCE_SECURITY_NAME_INVALID')
        exchange = _EXCHANGES[meta['exchangeName']]
        return dict(security_id='IMPORTED:YAHOO:' + exchange + ':' + symbol + ':' + intake_id,
                    symbol=symbol, exchange=exchange, currency='USD', instrument_type='COMMON_STOCK'), name
    except (KeyError, TypeError, IndexError) as exc:
        raise daily._Stop('SOURCE_REQUIRED_FIELDS_INVALID:' + type(exc).__name__) from None


def _review(raw, core, *, retained_calendar=None):
    security, name = _security(raw, core['symbol'], core['intake_id'])
    retrieved = daily._clock(core['retrieved_at'])
    if retained_calendar is None:
        calendar, calendar_raw, days, first, latest = _coverage(retrieved, core['history_sessions'], security['exchange'])
    else:
        calendar_raw = retained_calendar
        calendar = parse_document(calendar_raw)
        exchanges = [calendar['exchange']] if 'years' in calendar else daily._exchanges(calendar)
        daily._require(security['exchange'] in exchanges and daily._clock(calendar['recorded_at']) <= retrieved,
                       'FROZEN_CALENDAR_IDENTITY_INVALID', 'CALENDAR_UNAVAILABLE')
        latest = daily._last_complete(calendar, retrieved)
        opened = [row for row in daily._days(calendar, date(min(daily._calendar_years(calendar)),1,1),
                  date.fromisoformat(latest)) if row['kind']=='OPEN']
        daily._require(len(opened) >= core['history_sessions'], 'FROZEN_CALENDAR_COVERAGE_INVALID')
        first = opened[-core['history_sessions']]['date']
        days = daily._days(calendar,date.fromisoformat(first),date.fromisoformat(latest))
    # The pre-request NYSE calendar only bounds the request. An admitted source
    # must independently pass its actual exchange's installed calendar.
    daily._require(first >= core['query_start'], 'SOURCE_WINDOW_OUTSIDE_REQUEST')
    rows, excluded, outside, meta, prefix = daily._rows(raw, {'security': security}, days, latest,
                                                       retrieved, core['query_start'], calendar)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(('session_date', *daily._FIELDS))
    writer.writerows((day, *(daily._price(v) for v in values[:4]), str(values[4])) for day, values in sorted(rows.items()))
    return dict(security=security, company_name=name, coverage_start=first, coverage_end=latest,
                session_count=len(rows), excluded_forming_sessions=excluded, outside_window_actions=outside,
                excluded_pre_window_sessions=prefix, source_regular_market_time=meta['regularMarketTime']), stream.getvalue().encode(), calendar_raw, days


def check_stock_import(symbol, history_sessions, output_dir, *, now=None, fetcher=None):
    if type(symbol) is not str or re.fullmatch(r'[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?', symbol) is None:
        raise ValueError('stock_symbol_invalid')
    if type(history_sessions) is not int or history_sessions not in HISTORY_SESSIONS:
        raise ValueError('stock_history_sessions_must_be_20_60_or_120')
    directory = Path(output_dir).absolute()
    daily._regular(directory)
    directory.mkdir(parents=True, exist_ok=False)
    checked = daily._stamp(now if now is not None else datetime.now(timezone.utc))
    core = dict(schema_version=SCHEMA, intake_id=directory.name, symbol=symbol, history_sessions=history_sessions,
        checked_at=checked, status='BLOCKED', reason='CHECK_NOT_COMPLETED', can_save=False,
        security=None, company_name=None, coverage_start=None, coverage_end=None, session_count=0,
        retrieved_at=None, source_url=None, raw_sha256=None, query_start=None, artifacts={}, stop_detail=None,
        evidence_kind='IMPORTED_UNVERIFIED', source_truth_verified=False,
        limitations=['来源证券类型和历史身份为导入方声明，未获独立认证。',
                     '只支持美元普通股、完整日线和无公司行为窗口；不会自动缩短区间或调整策略。',
                     '检查不发布行情、不创建任务、不运行回测；确认证券后才保存。'],
        permissions=dict(network_requests=0, economic_runs=0, orders=0))
    try:
        instant = daily._clock(checked)
        _, _, _, first, _ = _coverage(instant, history_sessions, 'XNYS')
        query_start = (date.fromisoformat(first) - timedelta(days=120)).isoformat()
        end = instant.astimezone(daily._NY).date() + timedelta(days=1)
        params = dict(period1=int(datetime.combine(date.fromisoformat(query_start), time(), daily._NY).timestamp()),
            period2=int(datetime.combine(end, time(), daily._NY).timestamp()), interval='1d', events='div,splits', includePrePost='false')
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + symbol + '?' + urlencode(params)
        core.update(query_start=query_start, source_url=url)
        write_new(directory/'request-started.json', dict(symbol=symbol, history_sessions=history_sessions,
                  reference=url, started_at=checked, automatic_retry=False))
        core['artifacts']['request-started.json'] = sha256((directory/'request-started.json').read_bytes()).hexdigest()
        core['permissions']['network_requests'] = 1
        raw = (fetcher or daily._fetch)(url)
        retrieved = daily._stamp(now if now is not None else datetime.now(timezone.utc))
        if type(raw) is bytes:
            immutable_write(directory/'source-original.bin', raw)
            core.update(retrieved_at=retrieved, raw_sha256=sha256(raw).hexdigest())
            core['artifacts']['source-original.bin'] = core['raw_sha256']
        daily._require(type(raw) is bytes and 0 < len(raw) <= daily._MAX, 'SOURCE_RESPONSE_SIZE_INVALID')
        daily._require(daily._clock(retrieved) >= instant, 'RETRIEVAL_CLOCK_MOVED_BACKWARD')
        security, company_name = _security(raw, symbol, core['intake_id'])
        core.update(security=security, company_name=company_name)
        _, calendar_raw, _, first, latest = _coverage(daily._clock(retrieved), history_sessions, security['exchange'])
        immutable_write(directory/'calendar.json', calendar_raw)
        core['artifacts']['calendar.json'] = sha256(calendar_raw).hexdigest()
        core.update(coverage_start=first, coverage_end=latest)
        detail, csv_raw, calendar_raw, _ = _review(raw, core)
        core.update(detail)
        for name, content in (('candidate-prices.csv', csv_raw), ('calendar.json', calendar_raw)):
            immutable_write(directory/name, content)
            core['artifacts'][name] = sha256(content).hexdigest()
        core.update(status='REVIEW_REQUIRED', reason='EXACT_SECURITY_CONFIRMATION_REQUIRED', can_save=True)
    except daily._Stop as exc:
        core.update(status=exc.status, reason=exc.reason, stop_detail=daily._stop_detail(exc.reason, exc.details))
        if exc.received_raw is not None and 'source-original.bin' not in core['artifacts']:
            immutable_write(directory/'source-original.bin', exc.received_raw)
            core.update(retrieved_at=daily._stamp(now if now is not None else datetime.now(timezone.utc)),
                        raw_sha256=sha256(exc.received_raw).hexdigest(), source_response_truncated=exc.truncated)
            core['artifacts']['source-original.bin'] = core['raw_sha256']
    except (ValueError, OSError, KeyError, TypeError) as exc:
        core.update(status='BLOCKED', reason='INPUT_OR_SOURCE_INVALID:' + str(exc)[:240])
    except Exception as exc:
        core.update(status='UNKNOWN', reason='SOURCE_OUTCOME_UNKNOWN:' + type(exc).__name__)
    write_new(directory/'check.json', dict(core, check_hash=digest(core)))
    return read_stock_import(directory)


def read_stock_import(directory):
    directory = Path(directory).absolute()
    checked = parse_document(daily._read(directory/'check.json'))
    core = {k:v for k,v in checked.items() if k != 'check_hash'}
    if (checked.get('schema_version') != SCHEMA or checked.get('check_hash') != digest(core)
            or checked.get('status') not in _STATES or type(checked.get('can_save')) is not bool
            or checked['can_save'] != (checked['status'] == 'REVIEW_REQUIRED')
            or type(checked.get('history_sessions')) is not int or checked['history_sessions'] not in HISTORY_SESSIONS
            or checked.get('intake_id') != directory.name):
        raise ValueError('stock_intake_check_identity_invalid')
    allowed = {'request-started.json', 'source-original.bin', 'candidate-prices.csv', 'calendar.json'}
    if type(checked['artifacts']) is not dict or set(checked['artifacts']) - allowed:
        raise ValueError('stock_intake_artifact_inventory_invalid')
    for name, expected in checked['artifacts'].items():
        path = directory/name
        daily._regular(path)
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('stock_intake_artifact_changed:' + name)
    if checked['raw_sha256'] != checked['artifacts'].get('source-original.bin'):
        raise ValueError('stock_intake_source_identity_invalid')
    if checked['can_save']:
        if set(checked['artifacts']) != allowed:
            raise ValueError('stock_intake_candidate_sources_missing')
        detail, csv_raw, calendar_raw, _ = _review(daily._read(directory/'source-original.bin'), checked,
                                                  retained_calendar=daily._read(directory/'calendar.json'))
        if any(checked[k] != v for k,v in detail.items()) or csv_raw != daily._read(directory/'candidate-prices.csv') or calendar_raw != daily._read(directory/'calendar.json'):
            raise ValueError('stock_intake_candidate_changed')
    result = dict(checked, frozen_input_ref=None, source=dict(name='Yahoo Finance', reference=checked['source_url'],
        retrieved_at=checked['retrieved_at'], raw_sha256=checked['raw_sha256']))
    if (directory/'freeze.json').exists():
        receipt = parse_document(daily._read(directory/'freeze.json'))
        ref = receipt.get('input_ref')
        if (receipt.get('schema_version') != 'workbench-stock-intake-freeze-v1'
                or receipt.get('freeze_hash') != digest({k:v for k,v in receipt.items() if k != 'freeze_hash'})
                or receipt.get('check_hash') != checked['check_hash'] or receipt.get('security') != checked['security']
                or not checked['can_save'] or type(ref) is not str or '\\' in ref or ':' in ref
                or Path(ref).is_absolute() or '..' in Path(ref).parts or not Path(ref).parts or Path(ref).parts[0] != 'data'):
            raise ValueError('stock_intake_freeze_identity_invalid')
        result.update(freeze_receipt=receipt, frozen_input_ref=receipt['input_ref'])
    return result


def save_stock_import(directory, workspace, *, expected_check_hash, confirmed_security):
    directory, workspace = Path(directory).absolute(), Path(workspace).absolute()
    daily._regular(directory); daily._regular(workspace)
    with _file_lock(directory/'.freeze.lock'):
        checked = read_stock_import(directory)
        if checked['check_hash'] != expected_check_hash or type(confirmed_security) is not dict or confirmed_security != checked['security']:
            raise ValueError('stock_intake_exact_security_confirmation_required')
        if not checked['can_save']:
            raise ValueError('stock_intake_not_ready_for_save:' + checked['status'])
        if checked.get('freeze_receipt'):
            receipt = checked['freeze_receipt']
            path = workspace/receipt['input_ref']
            daily._regular(path)
            if not path.resolve().is_relative_to((workspace/'data').resolve()) or sha256(path.read_bytes()).hexdigest() != receipt['input_file_sha256']:
                raise ValueError('stock_intake_saved_input_changed')
            retained = inspect_input(path)
            snapshot = parse_document(path.read_bytes())
            if retained['input_id'] != receipt['snapshot_id'] or snapshot['security'] != checked['security']:
                raise ValueError('stock_intake_saved_input_identity_changed')
        else:
            raw = daily._read(directory/'source-original.bin')
            detail, csv_raw, calendar_raw, days = _review(raw, checked, retained_calendar=daily._read(directory/'calendar.json'))
            first, last, at = detail['coverage_start'], detail['coverage_end'], checked['retrieved_at']
            calendar = parse_document(calendar_raw)
            manifest = dict(schema_version='us-equity-daily-import-v1', security=checked['security'],
                identity=dict(stable_within_coverage=True, valid_from=first, valid_through=last,
                    selection_basis='User confirmed this exact USD common-stock identity for this window. Current Yahoo metadata and historical continuity remain importer declarations, not independent authentication.',
                    source=daily._source('Current Yahoo security metadata; exact identity confirmed by importer', checked['source_url'], raw, at)),
                calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=last, days=days,
                    source=daily._source('Installed published exchange calendar; temporary closures not covered', calendar['sources'][0], calendar_raw, calendar['recorded_at'])),
                corporate_actions=dict(coverage_start=first, coverage_end=last, coverage_status='DECLARED_COMPLETE', actions=[],
                    source=daily._source('Yahoo event coverage retained; completeness not authenticated', checked['source_url'], raw, at)),
                price_source=daily._source('Yahoo raw quote CSV; eight-decimal formatting, no adjustment', checked['source_url'], csv_raw, at),
                price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
                completed_bars_only=True, as_of=at, retrieved_at=at, bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
            snapshot = build_equity_snapshot(csv_raw, manifest).document
            if not snapshot['research_admission']['allowed']:
                raise ValueError('stock_intake_snapshot_not_admitted')
            retained = _retain(workspace, daily._json(snapshot))
            body = dict(schema_version='workbench-stock-intake-freeze-v1', check_hash=checked['check_hash'],
                security=confirmed_security, input_ref=Path(retained['path']).relative_to(workspace.resolve()).as_posix(),
                input_file_sha256=sha256(Path(retained['path']).read_bytes()).hexdigest(), snapshot_id=snapshot['snapshot_id'])
            write_new(directory/'freeze.json', dict(body, freeze_hash=digest(body)))
        return dict(retained, status='STOCK_INPUT_SAVED', check_hash=checked['check_hash'],
                    suggested_task=_suggested(snapshot), new_economic_runs=0)
