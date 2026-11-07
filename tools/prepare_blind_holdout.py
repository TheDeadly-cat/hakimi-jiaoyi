"""Acquire a preregistered project holdout once; never select it from results.

The contract precedes acquisition. Its immutable receipt supplies later source
hashes. This proves the declared local sequence, not global prior ignorance or
historical point-in-time availability. The ordinary installed engine is reused.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time as time_module
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import Request, build_opener

from hakimi_research import daily_updates as updates
from hakimi_research.documents import digest, parse_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.equity_dataset import build_equity_snapshot, verify_equity_snapshot
from hakimi_research.equity_research import EquityExperimentSpec, SPEC_SCHEMA
from hakimi_research.experiment import required_context


_REPLAY_SPEC = importlib.util.spec_from_file_location('_blind_holdout_replay_primitives',
    Path(__file__).with_name('prepare_sealed_month_replay.py'))
replay = importlib.util.module_from_spec(_REPLAY_SPEC)
_REPLAY_SPEC.loader.exec_module(replay)
SCHEMA = 'independent-historical-holdout-design-v1'
MODE = 'PROJECT_HISTORICAL_HOLDOUT_PREACQUISITION'
POLICY = dict(max_requests_per_symbol=2, retry_only_without_successful_response=True,
    same_url_only=True, retry_delay_seconds=3,
    retry_reason_codes=['SOURCE_HTTP_429', 'SOURCE_HTTP_502', 'SOURCE_HTTP_503', 'SOURCE_REQUEST_FAILED_NO_RETRY'])
ECONOMIC_FIELDS = ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy',
    'execution_policy', 'quantity_policy', 'purpose', 'cost_multipliers', 'benchmarks', 'parameter_sources')
_OWN_PATH = 'tools/prepare_blind_holdout.py'
_REPLAY_PATH = 'tools/prepare_sealed_month_replay.py'


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _read(path, expected=None):
    return replay._read(path, expected)


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if type(value) is bytes else updates._json(value))
        stream.flush()
        os.fsync(stream.fileno())


def _relative(repository, name):
    _require(type(name) is str and '\\' not in name and not Path(name).is_absolute()
             and '..' not in Path(name).parts, 'holdout_repository_relative_path_required')
    path = repository / name
    updates._regular(path)
    _require(path.resolve().is_relative_to(repository.resolve()), 'holdout_repository_path_escape')
    return path


def _reference(source, symbol):
    parsed = urlsplit(source['reference'])
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    params = dict(pairs)
    _require(parsed.scheme == 'https' and parsed.netloc == 'query1.finance.yahoo.com'
             and parsed.path == '/v8/finance/chart/' + symbol and not parsed.fragment
             and len(pairs) == len(params) and set(params) == {'period1', 'period2', 'interval', 'events', 'includePrePost'},
             'holdout_fixed_source_url_invalid')
    start = datetime.combine(date.fromisoformat(source['query_start']), time(), updates._NY)
    end = replay._clock(source['query_period2_utc'])
    _require(params == dict(period1=str(int(start.timestamp())), period2=str(int(end.timestamp())),
        interval='1d', events='div,splits', includePrePost='false'), 'holdout_source_url_parameters_changed')
    return end


def check_design_protocol(design_path, expected_sha256=None, *, require_runtime=True):
    """Read-only protocol checks; later report reads do not depend on current HEAD."""
    raw = _read(design_path, expected_sha256)
    design = parse_document(raw)
    _require(design.get('schema_version') == SCHEMA and design.get('mode') == MODE
             and design.get('plan_hash') == digest({k: v for k, v in design.items() if k != 'plan_hash'}),
             'holdout_design_identity_invalid')
    recorded = replay._clock(design['recorded_at'])
    _require(digest(design['acquisition_policy']) == digest(POLICY), 'holdout_acquisition_policy_changed')
    _require(digest(design['historical_price_policy']) == digest(replay.HISTORICAL_POLICY),
             'holdout_historical_price_policy_changed')
    original = parse_document(_read(design['parameter_design']['path'], design['parameter_design']['sha256']))
    _require(original.get('plan_hash') == digest({k: v for k, v in original.items() if k != 'plan_hash'})
             and all(design[key] == original[key] for key in ECONOMIC_FIELDS), 'holdout_frozen_parameters_changed')
    _require(design['strategy']['name'] == 'dual_ma' and design['context_sessions'] == required_context(
        design['strategy']['name'], design['strategy']['params']), 'holdout_required_context_changed')
    context, start, end = (date.fromisoformat(design[key]) for key in ('context_start', 'score_start', 'score_end'))
    _require(context < start <= end and (end-context).days <= 366, 'holdout_window_invalid')
    audit = parse_document(_read(design['exposure_audit']['path'], design['exposure_audit']['sha256']))
    _require(audit.get('status') == 'PASS_PROJECT_SCOPE'
             and audit.get('selected_month') == design['score_start'][:7]
             and audit.get('selected_context_start') == design['context_start']
             and audit.get('selected_score_start') == design['score_start']
             and audit.get('selected_score_end') == design['score_end'], 'holdout_exposure_audit_not_matched')
    _require(type(audit.get('excluded_intervals')) is list, 'holdout_excluded_intervals_required')
    for interval in audit['excluded_intervals']:
        left, right = date.fromisoformat(interval['start']), date.fromisoformat(interval['end'])
        _require(left <= right and (right < context or left > end), 'holdout_window_overlaps_exposed_data')
    addendum = parse_document(_read(design['exposure_addendum']['path'], design['exposure_addendum']['sha256']))
    _require(addendum.get('status') == 'PASS_NO_UNRESOLVED_CANDIDATE_OVERLAP'
             and type(addendum.get('unresolved_candidate_overlap_count')) is int
             and addendum['unresolved_candidate_overlap_count'] == 0
             and all(addendum.get('candidate_' + key) == design[key]
                     for key in ('context_start', 'score_start', 'score_end'))
             and replay._clock(addendum['recorded_at']) <= recorded,
             'holdout_exposure_addendum_not_matched')
    repository = Path(design['repository_path']).resolve()
    _require(type(design['acquisition_output_path']) is str and Path(design['acquisition_output_path']).is_absolute(),
             'holdout_fixed_absolute_output_required')
    updates._regular(Path(design['acquisition_output_path']))
    _relative(repository, design['protocol_repo_path'])
    hashes = design['tool_hashes']
    _require(type(hashes) is dict and {_OWN_PATH, _REPLAY_PATH} <= set(hashes), 'holdout_tool_hashes_required')
    for name, expected in hashes.items():
        _read(_relative(repository, name), expected)
    _require(sha256(Path(__file__).read_bytes()).hexdigest() == hashes[_OWN_PATH]
             and sha256(Path(replay.__file__).read_bytes()).hexdigest() == hashes[_REPLAY_PATH],
             'holdout_executed_tool_identity_changed')
    calendar_raw = _read(design['calendar_path'], design['calendar_sha256'])
    _require(type(design['sources']) is dict and bool(design['sources']), 'holdout_sources_required')
    for symbol, source in design['sources'].items():
        _require(type(symbol) is str and re.fullmatch(r'[A-Z][A-Z0-9.-]{0,10}', symbol)
                 and 'raw_sha256' not in source and 'retrieved_at' not in source,
                 'holdout_preacquisition_source_invalid')
        baseline = verify_equity_snapshot(parse_document(_read(source['baseline_snapshot_path'], source['baseline_sha256'])))
        _require(baseline['security']['symbol'] == symbol, 'holdout_baseline_symbol_mismatch')
        query_start = date.fromisoformat(source['query_start'])
        _require(query_start <= context, 'holdout_query_misses_context')
        calendar, installed_raw = updates._calendar_window(query_start.year, recorded.astimezone(updates._NY).year,
                                                           baseline['security']['exchange'])
        _require(installed_raw == calendar_raw and replay._clock(calendar['recorded_at']) <= recorded,
                 'holdout_calendar_not_frozen_or_available')
        dates = [row['date'] for row in updates._days(calendar, context, end) if row['kind'] == 'OPEN']
        _require(dates == design['context_dates'] + design['score_sessions']
                 and len(design['context_dates']) == design['context_sessions']
                 and design['score_sessions'][0] == design['score_start'] and design['score_sessions'][-1] == design['score_end'],
                 'holdout_calendar_partition_changed')
        latest = updates._last_complete(calendar, recorded)
        _require(source['latest_completed_session'] == latest and latest >= design['score_end'], 'holdout_frozen_source_cutoff_invalid')
        query_end = _reference(source, symbol)
        close = updates._days(calendar, date.fromisoformat(latest), date.fromisoformat(latest))[0]['close_utc']
        _require(query_end > replay._clock(close) and query_end <= datetime.combine(
            recorded.astimezone(updates._NY).date() + timedelta(days=1), time(), updates._NY), 'holdout_query_end_invalid')
        _require(type(source['historical_identity_declaration']) is str and len(source['historical_identity_declaration']) >= 80,
                 'holdout_identity_declaration_required')
    if require_runtime:
        runtime = build_runtime_provenance()
        _require(runtime['source_identity']['content_sha256'] == design['execution_runtime_source_sha256']
                 and runtime['environment_verified']['status'] == 'VERIFIED', 'holdout_execution_runtime_changed')
    return design


def _git_commit(design, design_path, commit):
    repository = Path(design['repository_path'])
    _require(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit), 'holdout_full_commit_required')
    run = lambda *args: subprocess.check_output(['git', *args], cwd=repository)
    _require(run('rev-parse', 'HEAD').decode().strip() == commit, 'holdout_head_must_equal_protocol_commit')
    _require(run('show', commit + ':' + design['protocol_repo_path']) == _read(design_path), 'holdout_protocol_git_blob_mismatch')
    for name, expected in design['tool_hashes'].items():
        _require(sha256(run('show', commit + ':' + name)).hexdigest() == expected, 'holdout_tool_git_blob_mismatch:' + name)
    return datetime.fromtimestamp(int(run('show', '-s', '--format=%ct', commit).decode().strip()), timezone.utc)


class FetchFailure(Exception):
    def __init__(self, reason, *, response_status=None, raw=None, outcome_known=True):
        _require(response_status is None or type(response_status) is int, 'holdout_response_status_type_invalid')
        _require(raw is None or type(raw) is bytes, 'holdout_failure_raw_bytes_required')
        super().__init__(reason)
        self.reason, self.response_status, self.raw, self.outcome_known = reason, response_status, raw, outcome_known


def _fetch(url):
    """Same bounded public transport, with HTTP-200 observation retained on error."""
    parsed = urlsplit(url)
    _require(parsed.scheme == 'https' and parsed.netloc == 'query1.finance.yahoo.com'
             and parsed.path.startswith('/v8/finance/chart/'), 'holdout_source_url_not_allowed')
    status, chunks = None, []
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 HakimiResearch/0.6', 'Accept': 'application/json'})
    try:
        with build_opener(updates._NoRedirect()).open(request, timeout=12) as response:
            status = response.status
            if response.geturl() != url or status != 200:
                raise FetchFailure('SOURCE_RESPONSE_NOT_SUCCESSFUL', response_status=status)
            total = 0
            while total <= updates._MAX:
                chunk = response.read(min(65536, updates._MAX + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
            return b''.join(chunks)
    except HTTPError as error:
        try:
            raw = error.read(updates._MAX + 1)
        except Exception as body_error:
            partial = getattr(body_error, 'partial', None)
            raw = partial[:updates._MAX + 1] if type(partial) is bytes else None
        finally:
            error.close()
        raise FetchFailure('SOURCE_HTTP_' + str(error.code), response_status=error.code, raw=raw) from None
    except (URLError, TimeoutError, OSError):
        raise FetchFailure('SOURCE_REQUEST_FAILED_NO_RETRY' if status is None else 'SOURCE_RESPONSE_BODY_FAILED_NO_RETRY',
                           response_status=status, raw=b''.join(chunks) or None) from None
    except updates._Stop as error:
        raise FetchFailure(error.reason, response_status=status, raw=error.received_raw) from None
    except FetchFailure:
        raise
    except Exception as error:
        partial = getattr(error, 'partial', None)
        if type(partial) is bytes:
            chunks.append(partial)
        raw = b''.join(chunks)[:updates._MAX + 1] or None
        raise FetchFailure('SOURCE_RESPONSE_BODY_FAILED_NO_RETRY' if status is not None else 'SOURCE_UNKNOWN_OUTCOME',
                           response_status=status, raw=raw, outcome_known=status is not None) from None


def _now(clock):
    value = clock() if clock is not None else datetime.now(timezone.utc)
    _require(isinstance(value, datetime) and value.tzinfo is not None, 'holdout_actual_clock_required')
    return value.astimezone(timezone.utc)


def _cutoff(design, source, at):
    calendar = parse_document(_read(design['calendar_path'], design['calendar_sha256']))
    _require(updates._last_complete(calendar, at) == source['latest_completed_session'],
             'holdout_frozen_acquisition_cutoff_expired_no_request_or_reselection')


def _acquire_symbol(design, symbol, directory, commit_time, *, fetcher, clock, sleeper):
    source = design['sources'][symbol]
    attempts = []
    retry_not_before = None
    for number in (1, 2):
        started = _now(clock)
        try:
            _require(started > replay._clock(design['recorded_at']) and started > commit_time,
                     'holdout_request_must_follow_design_and_commit')
            _require(retry_not_before is None or started >= retry_not_before, 'holdout_retry_delay_not_elapsed')
            _cutoff(design, source, started)
        except ValueError as error:
            return dict(status='STOPPED', reference=source['reference'], reason=str(error), attempts=attempts,
                request_started_at=attempts[0]['request_started_at'] if attempts else None,
                retrieved_at=None, raw_path=None, raw_sha256=None)
        attempt_dir = directory / ('attempt-' + str(number))
        entry = dict(number=number, reference=source['reference'], request_started_at=updates._stamp(started), status='REQUEST_STARTED')
        _write(attempt_dir / 'request-started.json', entry)
        failure = None
        try:
            raw = fetcher(source['reference'])
            _require(type(raw) is bytes, 'holdout_fetcher_bytes_required')
            status = 200
        except FetchFailure as error:
            raw, status, failure = error.raw, error.response_status, error
        except Exception as error:
            raw, status = None, None
            failure = FetchFailure('SOURCE_UNKNOWN_OUTCOME:' + type(error).__name__, outcome_known=False)
        try:
            finished = _now(clock)
        except ValueError:
            finished = None
        if raw is not None:
            raw_path = attempt_dir / 'response.bin'
            _write(raw_path, raw)
            entry.update(raw_path=str(raw_path.resolve()), raw_sha256=sha256(raw).hexdigest())
        if finished is None or finished < started or finished <= replay._clock(design['recorded_at']) or finished <= commit_time:
            entry.update(status='UNKNOWN', completed_at=None, response_status=status, reason='SOURCE_RETRIEVAL_CLOCK_INVALID',
                         outcome_known=False, successful_response_received=status == 200)
            _write(attempt_dir / 'result.json', entry)
            attempts.append(entry)
            return dict(status='STOPPED', reference=source['reference'], reason=entry['reason'], attempts=attempts,
                request_started_at=entry['request_started_at'], retrieved_at=None,
                raw_path=entry.get('raw_path'), raw_sha256=entry.get('raw_sha256'))
        entry.update(completed_at=updates._stamp(finished), response_status=status)
        if failure is None:
            entry['status'] = 'ACQUIRED'
        else:
            entry.update(status='FAILED' if failure.outcome_known else 'UNKNOWN', reason=failure.reason,
                outcome_known=failure.outcome_known, successful_response_received=status == 200)
        _write(attempt_dir / 'result.json', entry)
        attempts.append(entry)
        if failure is None:
            return dict(status='ACQUIRED', reference=source['reference'], request_started_at=entry['request_started_at'],
                retrieved_at=entry['completed_at'], raw_path=entry['raw_path'], raw_sha256=entry['raw_sha256'], attempts=attempts)
        retry = (number == 1 and failure.outcome_known and status != 200 and failure.reason in POLICY['retry_reason_codes'])
        if not retry:
            return dict(status='STOPPED', reference=source['reference'], reason=failure.reason, attempts=attempts,
                        request_started_at=attempts[0]['request_started_at'], retrieved_at=None, raw_path=None, raw_sha256=None)
        retry_not_before = finished + timedelta(seconds=POLICY['retry_delay_seconds'])
        sleeper(POLICY['retry_delay_seconds'])
    raise AssertionError('bounded request loop exhausted unexpectedly')


def _prepare_symbol(design, symbol, acquired, folder):
    source = design['sources'][symbol]
    original = _read(acquired['raw_path'], acquired['raw_sha256'])
    baseline_raw = _read(source['baseline_snapshot_path'], source['baseline_sha256'])
    baseline = verify_equity_snapshot(parse_document(baseline_raw))
    retrieved = replay._clock(acquired['retrieved_at'])
    _cutoff(design, source, retrieved)
    calendar_raw = _read(design['calendar_path'], design['calendar_sha256'])
    calendar = parse_document(calendar_raw)
    source_receipt = dict(schema_version='blind-holdout-source-receipt-v1', symbol=symbol,
        raw_sha256=acquired['raw_sha256'], source_url=source['reference'], retrieved_at=acquired['retrieved_at'],
        checked_at=acquired['request_started_at'], query_start=source['query_start'], latest_completed_session=source['latest_completed_session'])
    _write(folder / 'source-original.json', original)
    _write(folder / 'baseline-original.json', baseline_raw)
    _write(folder / 'source-receipt.json', source_receipt)
    days = updates._days(calendar, date.fromisoformat(design['context_start']), date.fromisoformat(design['score_end']))
    derived, source_count, excluded_count = replay._window_reply(original, source_receipt, days, retrieved, calendar)
    _write(folder / 'source-window-derived.json', derived)
    rows, reconciliation = replay._historical_rows(original, baseline, design, source_receipt, retrieved, calendar)
    _write(folder / 'historical-adjustment-reconciliation.json', reconciliation)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(('session_date', *updates._FIELDS))
    writer.writerows((day, *(updates._price(v) for v in values[:4]), str(values[4])) for day, values in sorted(rows.items()))
    csv_raw = stream.getvalue().encode()
    security = deepcopy(baseline['security'])
    security['security_id'] = 'HOLDOUT:' + symbol + ':' + design['plan_hash'][:20]
    first, last, at = design['context_start'], design['score_end'], acquired['retrieved_at']
    manifest = dict(schema_version='us-equity-daily-import-v1', security=security,
        identity=dict(stable_within_coverage=True, valid_from=first, valid_through=last,
            selection_basis='New historical importer declaration under preacquisition protocol ' + design['plan_hash'] + '. ' + source['historical_identity_declaration'],
            source=updates._source('Newly acquired metadata; historical continuity not independently authenticated', source['reference'], original, at)),
        calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=last, days=days,
            source=updates._source('Frozen published calendar; retrospective session reconstruction', calendar['sources'][0], calendar_raw, calendar['recorded_at'])),
        corporate_actions=dict(coverage_start=first, coverage_end=last, coverage_status='DECLARED_COMPLETE', actions=[],
            source=updates._source('Retained original event coverage; not authenticated', source['reference'], original, at)),
        price_source=updates._source('Fixed-window quote CSV; 8 decimal formatting, no economic adjustment',
            'urn:project-holdout:' + design['plan_hash'] + ':' + symbol, csv_raw, at),
        price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE', completed_bars_only=True,
        as_of=at, retrieved_at=at, bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
    snapshot = build_equity_snapshot(csv_raw, manifest).document
    _require(snapshot['research_admission']['allowed'], 'holdout_snapshot_not_admitted')
    spec = dict(schema_version=SPEC_SCHEMA, name=symbol + ' preregistered historical holdout', snapshot_id=snapshot['snapshot_id'],
        score_start_session=design['score_start'], score_end_session=last,
        **{key: deepcopy(design[key]) for key in ECONOMIC_FIELDS if key not in {'cost_multipliers', 'benchmarks', 'parameter_sources'}})
    EquityExperimentSpec.from_document(spec)
    _write(folder / 'prices-derived.csv', csv_raw)
    _write(folder / 'import-manifest.json', manifest)
    _write(folder / 'snapshot.json', snapshot)
    _write(folder / 'spec.json', spec)
    return dict(status='READY', snapshot_path=str((folder / 'snapshot.json').resolve()),
        snapshot_sha256=sha256((folder / 'snapshot.json').read_bytes()).hexdigest(), snapshot_id=snapshot['snapshot_id'],
        spec_path=str((folder / 'spec.json').resolve()), spec_sha256=sha256((folder / 'spec.json').read_bytes()).hexdigest(),
        selected_rows=len(rows), source_rows=source_count, excluded_rows=excluded_count,
        source_receipt_path=str((folder / 'source-receipt.json').resolve()), source_receipt_sha256=sha256((folder / 'source-receipt.json').read_bytes()).hexdigest())


def prepare(design_path, commit, output_dir, *, fetcher=None, clock=None, sleeper=None):
    design = check_design_protocol(design_path)
    commit_time = _git_commit(design, design_path, commit)
    design_sha = sha256(_read(design_path)).hexdigest()
    updates._regular(Path(output_dir))
    output = Path(output_dir).resolve()
    _require(output == Path(design['acquisition_output_path']).resolve(), 'holdout_output_must_equal_frozen_destination')
    _require(not output.exists(), 'holdout_output_exists_no_automatic_retry')
    now = _now(clock)
    _require(now > replay._clock(design['recorded_at']) and now > commit_time, 'holdout_acquisition_must_follow_protocol_commit')
    for source in design['sources'].values():
        _cutoff(design, source, now)
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'design-original.json', _read(design_path))
    start = dict(schema_version='blind-holdout-acquisition-started-v1', plan_hash=design['plan_hash'],
        design_sha256=design_sha, commit=commit, commit_time=updates._stamp(commit_time), started_at=updates._stamp(now), automatic_resume=False)
    _write(output / 'acquisition-started.json', start)
    sources = {}
    for symbol in sorted(design['sources']):
        try:
            sources[symbol] = _acquire_symbol(design, symbol, output / symbol, commit_time,
                fetcher=fetcher or _fetch, clock=clock, sleeper=sleeper or time_module.sleep)
        except Exception as error:
            sources[symbol] = dict(status='UNKNOWN', reference=design['sources'][symbol]['reference'],
                reason=type(error).__name__ + ':' + str(error), automatic_retry=False)
    acquisition = dict(schema_version='blind-holdout-acquisition-v1', plan_hash=design['plan_hash'], design_sha256=design_sha,
        commit=commit, commit_time=updates._stamp(commit_time), started_at=start['started_at'], completed_at=updates._stamp(_now(clock)),
        commit_time_authority='GIT_COMMITTER_TIMESTAMP_NOT_EXTERNAL_TIME_ATTESTATION',
        status='ACQUIRED' if all(x['status'] == 'ACQUIRED' for x in sources.values()) else 'STOPPED', sources=sources)
    acquisition_path = output / 'acquisition.json'
    _write(acquisition_path, acquisition)
    results = {}
    for symbol, acquired in sources.items():
        try:
            _require(acquired['status'] == 'ACQUIRED', 'holdout_source_not_acquired')
            results[symbol] = _prepare_symbol(design, symbol, acquired, output / symbol / 'prepared')
        except Exception as error:
            results[symbol] = dict(status='STOPPED', reason=type(error).__name__ + ':' + str(error),
                                   automatic_retry=False, automatic_window_reselection=False)
        _write(output / symbol / 'preparation.json', results[symbol])
    receipt = dict(schema_version='blind-holdout-preparation-v1', status='READY' if all(r['status'] == 'READY' for r in results.values()) else 'STOPPED',
        plan_hash=design['plan_hash'], design_sha256=design_sha, commit=commit, prepared_at=updates._stamp(_now(clock)),
        acquisition_path=str(acquisition_path), acquisition_sha256=sha256(acquisition_path.read_bytes()).hexdigest(), symbols=results,
        economic_runs=0, no_candidate_price_values_emitted=True, project_scope_only=True, natural_forward_evidence=False,
        files={p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()})
    _write(output / 'preparation.json', receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args(argv)
    receipt = prepare(args.design, args.commit, args.output_dir)
    print(json.dumps({key: receipt[key] for key in ('status', 'plan_hash', 'commit', 'symbols', 'economic_runs')}, ensure_ascii=False))
    return 0 if receipt['status'] == 'READY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
