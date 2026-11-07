"""Metadata-only February eligibility delta after the retained April STOP.

No network, strategy or UI code is used. Rehashes the already identified evidence
instead of repeating the project-wide search or querying 112 databases again.
CSV interpretation is limited to date columns; source interpretation is limited
to symbol, timestamp and event-date metadata, never prices or performance.
"""
from __future__ import annotations
from copy import deepcopy
import csv
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / 'm32-independent-holdout-20261026'
REPO = ROOT.parent / '哈基米v2交易'
AUDIT_SHA = 'cac0cb85c56e3dedba85c40f8498cb828adfb6067ffaf7b79fee888d72614441'
ATTRIBUTION_SHA = '7cfbabb123757d9d094a352e6ac67eb4d5a9146924018df01e6e02098a8dd8a8'
HELPER_SHA = '303e3aed76287c082ac981d751f2497adf183389d87eba0df9f13371ec795492'
PROTOCOL_SHA = '36b00eab50a83a82c405a40897d8f8b1701a45759e50f972db04d52ecb9d6071'
APRIL_COMMIT = 'aa7935214e6e84197f48c1d6fb2908bed3d0851e'
APRIL_STOP_COMMIT = '68a22b4d7b3bd67a8b1e673c0ab7024ee4502b74'
START, SCORE_START, END = date(2026, 1, 14), date(2026, 2, 2), date(2026, 2, 27)
NY = ZoneInfo('America/New_York')


def sha(raw):
    return sha256(raw).hexdigest()


def reference(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    actual = sha(raw)
    if expected is not None and actual != expected:
        raise ValueError('REFERENCE_HASH_CHANGED:' + str(path))
    return dict(path=str(path), sha256=actual, bytes=len(raw))


def document(path, expected=None):
    ref = reference(path, expected)
    return json.loads(Path(path).read_bytes()), ref


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert ROOT.name == 'm32-independent-holdout-feb-20261026'
    assert not (ROOT / 'exposure-audit.json').exists()
    assert not (ROOT / 'anonymous-csv-attribution.json').exists()
    audit, audit_ref = document(PRIOR / 'exposure-audit-v2.json', AUDIT_SHA)
    attributed, attributed_ref = document(PRIOR / 'anonymous-csv-attribution.json', ATTRIBUTION_SHA)
    protocol, protocol_ref = document(PRIOR / 'protocol.json', PROTOCOL_SHA)
    preparation, preparation_ref = document(PRIOR / 'prepared-r1/preparation.json')
    acquisition, acquisition_ref = document(PRIOR / 'prepared-r1/acquisition.json')
    stopped, stopped_ref = document(PRIOR / 'stop-evidence.json')
    authorization, authorization_ref = document(ROOT / 'preservation-before.json')
    assert 'Separate February holdout approved' in authorization['user_authorization']
    assert audit['status'] == 'PASS_PROJECT_SCOPE'
    assert attributed['status'] == 'PASS_NO_UNRESOLVED_CANDIDATE_OVERLAP'
    assert attributed['audit_sha256'] == AUDIT_SHA
    assert preparation['status'] == 'STOPPED' and preparation['economic_runs'] == 0
    assert stopped['formal_runs'] == stopped['cost_runs'] == stopped['observer_recalculations'] == 0
    assert preparation_ref['sha256'] == stopped['preparation_sha256']
    assert acquisition_ref['sha256'] == stopped['acquisition_sha256'] == preparation['acquisition_sha256']
    assert protocol['plan_hash'] == preparation['plan_hash'] == acquisition['plan_hash'] == stopped['plan_hash']
    assert preparation['design_sha256'] == acquisition['design_sha256'] == PROTOCOL_SHA
    git = lambda *args: subprocess.check_output(['git', *args], cwd=REPO)
    assert git('show', APRIL_COMMIT + ':' + protocol['protocol_repo_path']) == (PRIOR/'protocol.json').read_bytes()
    assert git('show', APRIL_STOP_COMMIT + ':docs/research-evidence/independent-holdout-20261026/stop-evidence.json') == (PRIOR/'stop-evidence.json').read_bytes()
    head = git('rev-parse', 'HEAD').decode().strip()
    git('merge-base', '--is-ancestor', APRIL_STOP_COMMIT, head)
    changed_paths = git('diff', '--name-only', audit['git']['head'] + '..' + head).decode().splitlines()
    allowed = ('docs/research-evidence/independent-holdout-20261026/',
        'docs/research-evidence/independent-holdout-feb-20261026/')
    allowed_files = {'README.md', 'CURRENT_STATUS.md', 'tools/prepare_blind_holdout.py',
        'tools/verify_strategy_prefix_isolation.py', 'tests/repository_only/test_blind_holdout.py',
        'tests/repository_only/test_strategy_prefix_isolation.py'}
    git_drift = [p for p in changed_paths if p not in allowed_files and not p.startswith(allowed)]
    issues = [dict(code='UNEXPECTED_GIT_CHANGE_SINCE_BASE_AUDIT', path=p) for p in git_drift]
    revalidated = []
    def verify(path, expected, category):
        path = Path(path)
        try:
            actual = reference(path)
            passed = actual['sha256'] == expected
            entry = dict(**actual, expected_sha256=expected, category=category, status='MATCH' if passed else 'CHANGED')
        except OSError as error:
            passed = False
            entry = dict(path=str(path), expected_sha256=expected, category=category,
                status='UNREADABLE', error_type=type(error).__name__)
        revalidated.append(entry)
        if not passed:
            issues.append(dict(code='BOUND_EVIDENCE_DRIFT', **entry))
    for path, metadata in audit['matched_file_metadata'].items():
        verify(path, metadata['sha256'], 'prior_identified_file')
    for metadata in audit['database_audit']['files']:
        verify(metadata['path'], metadata['sha256'], 'prior_database_bytes_no_sql')
    identity_refs = {item['path']: item['sha256'] for record in attributed['records'] for item in record['evidence']}
    for path, expected in identity_refs.items():
        verify(path, expected, 'prior_anonymous_identity_evidence')
    # Reuse the exact old parser only for dates and matching embedded CSV bytes.
    helper_path = PRIOR / 'audit_anonymous_csv_attribution.py'
    helper_ref = reference(helper_path, HELPER_SHA)
    spec = importlib.util.spec_from_file_location('retained_anonymous_metadata_helpers', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    records = []
    assert len(attributed['records']) == 18
    for old in attributed['records']:
        record = deepcopy(old)
        path = Path(old['representative_path'])
        container = path.read_bytes()
        assert sha(container) == old['representative_container_sha256']
        raw = container
        if path.suffix.lower() == '.json':
            matches = helper.embedded_matches(json.loads(container), old['sha256'])
            assert matches
            raw = matches[0][0]
        assert sha(raw) == old['sha256']
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), strict=True)
        columns = [key for key in reader.fieldnames if key.lower() in {'date', 'session_date', 'trading_date', 'timestamp', 'time_key', 'time'}]
        dates, errors, rows_count = [], [], 0
        assert len(columns) == 1
        for number, row in enumerate(reader, start=2):
            rows_count += 1
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('MALFORMED_ROW_WIDTH')
                dates.append(helper.calendar_date(row[columns[0]]))
            except (ValueError, OverflowError, OSError) as error:
                errors.append(dict(row=number, code=type(error).__name__))
        assert rows_count == old['date_check']['rows']
        overlap = sum(START <= day <= END for day in dates)
        identity = old['attribution'] or {}
        known_other = identity.get('kind') in {'SYNTHETIC_FIXTURE', 'SYNTHETIC_CONFIGURED_DATASET',
            'SYNTHETIC_COLUMN_MAPPING_SOURCE', 'OTHER_INSTRUMENT'}
        unresolved = bool(errors or not dates or (overlap and not known_other))
        record['date_check'] = dict(columns=columns, rows=rows_count, valid_date_rows=len(dates),
            start=min(dates).isoformat() if dates else None, end=max(dates).isoformat() if dates else None,
            candidate_context_and_score_overlap_rows=overlap, issues=errors,
            timestamp_policy=old['date_check']['timestamp_policy'])
        record['status'] = 'UNRESOLVED_CANDIDATE_OVERLAP' if unresolved else (
            'RESOLVED_OTHER_OR_SYNTHETIC' if known_other else 'NO_CANDIDATE_DATE_OVERLAP')
        record['unresolved_candidate_overlap'] = unresolved
        record['prior_attribution_sha256'] = ATTRIBUTION_SHA
        records.append(record)
    sources = []
    assert set(acquisition['sources']) == {'NDAQ', 'KO'}
    for symbol, source in acquisition['sources'].items():
        raw_ref = reference(source['raw_path'], source['raw_sha256'])
        result = json.loads(Path(source['raw_path']).read_bytes())['chart']['result'][0]
        assert result['meta']['symbol'] == symbol
        dates = [datetime.fromtimestamp(stamp, NY).date().isoformat() for stamp in result['timestamp']]
        assert len(dates) == len(set(dates)) == 155 and dates == sorted(dates)
        assert dates[0] == '2026-03-16' and dates[-1] == '2026-10-23'
        event_dates = []
        for kind, group in result['events'].items():
            for event in group.values():
                event_dates.append(dict(kind=kind, date=datetime.fromtimestamp(event['date'], NY).date().isoformat()))
        assert len(source['attempts']) == 1 and source['attempts'][0]['response_status'] == 200
        assert source['retrieved_at'] == stopped['sources'][symbol]['retrieved_at']
        sources.append(dict(symbol=symbol, **raw_ref, actual_retrieved_at=source['retrieved_at'],
            first_session=dates[0], last_session=dates[-1], source_rows=len(dates),
            session_dates_sha256=sha('\n'.join(dates).encode()), event_dates=event_dates,
            scope='Timestamp and event-date metadata only; no price/volume/adjustment/performance values inspected.'))
    assert preparation['symbols']['NDAQ']['status'] == 'STOPPED'
    assert preparation['symbols']['KO']['status'] == 'READY'
    prior_intervals = audit['excluded_intervals']
    first = min([x['start'] for x in prior_intervals] + [x['first_session'] for x in sources])
    last = max([x['end'] for x in prior_intervals] + [x['last_session'] for x in sources])
    assert (first, last) == ('2026-03-16', '2026-10-23')
    calendar_path = REPO / 'src/hakimi_research/resources/us-equity-calendar-2026.json'
    calendar, calendar_ref = document(calendar_path, audit['calendar_sha256'])
    holidays = set(calendar['holidays'])
    def open_day(day):
        return day.weekday() < 5 and day.isoformat() not in holidays
    previous_month_end = date.fromisoformat(first).replace(day=1) - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    score = [previous_month_start + timedelta(days=i) for i in range((previous_month_end-previous_month_start).days+1)
        if open_day(previous_month_start + timedelta(days=i))]
    context, cursor = [], score[0] - timedelta(days=1)
    while len(context) < 12:
        if open_day(cursor):
            context.append(cursor)
        cursor -= timedelta(days=1)
    context.sort()
    assert (context[0], score[0], score[-1], len(score)) == (START, SCORE_START, END, 19)
    prior_overlap = [dict(kind=g['kind'], symbol=g['symbol'], start=g['start'], end=g['end'])
        for g in audit['exposure_groups'] if g['start'] <= END.isoformat() and g['end'] >= START.isoformat()]
    if prior_overlap:
        issues.append(dict(code='KNOWN_EXPOSURE_OVERLAPS_CANDIDATE', records=prior_overlap))
    unknown = sum(bool(record['unresolved_candidate_overlap']) for record in records)
    if unknown:
        issues.append(dict(code='ANONYMOUS_CANDIDATE_OVERLAP', groups=unknown))
    # Recheck the frozen April preparation manifest, without interpreting its data.
    for name, expected in preparation['files'].items():
        verify(PRIOR/'prepared-r1'/name, expected, 'retained_april_preparation')
    assert reference(PRIOR/'protocol.json')['sha256'] == PROTOCOL_SHA
    assert reference(PRIOR/'exposure-audit-v2.json')['sha256'] == AUDIT_SHA
    assert reference(PRIOR/'anonymous-csv-attribution.json')['sha256'] == ATTRIBUTION_SHA
    stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    script_ref = reference(__file__)
    checks_path = ROOT / 'eligibility-reference-revalidation.json'
    checks = dict(schema_version='holdout-reference-revalidation-v1', recorded_at=stamp,
        status='PASS' if not issues else 'NEEDS_SCOPE_REVIEW', files=revalidated,
        database_queries=0, full_project_search_repeated=False, issues=issues)
    write_new(checks_path, checks)
    checks_ref = reference(checks_path)
    common = dict(recorded_at=stamp, new_source_requests=0, economic_runs=0,
        candidate_selection_changed_from_user_authorized_round=False,
        prior_april_stop_preserved=True, separate_user_authorized_round=True,
        authorization_reference=authorization_ref, prior_audit=audit_ref, prior_attribution=attributed_ref,
        revalidation=checks_ref, script=script_ref)
    addendum = dict(schema_version='anonymous-csv-attribution-v1', **common,
        status='PASS_NO_UNRESOLVED_CANDIDATE_OVERLAP' if not issues and unknown == 0 else 'NEEDS_SCOPE_REVIEW',
        candidate_context_start=START.isoformat(), candidate_score_start=SCORE_START.isoformat(),
        candidate_score_end=END.isoformat(), unresolved_candidate_overlap_count=unknown,
        groups_checked=len(records), records=records, price_values_interpreted=False,
        return_values_interpreted=False, parser_reference=helper_ref,
        limitations=attributed['limitations'] + ['February candidate dates rechecked against the same 18 content groups; identities reused only after evidence-byte revalidation.'])
    write_new(ROOT/'anonymous-csv-attribution.json', addendum)
    addendum_ref = reference(ROOT/'anonymous-csv-attribution.json')
    result = dict(schema_version='project-scoped-holdout-exposure-delta-v1', **common,
        status='PASS_PROJECT_SCOPE' if not issues else 'NEEDS_SCOPE_REVIEW',
        excluded_intervals=[dict(start=first, end=last, symbols=['KO', 'NDAQ'],
            reason='Union of prior retained sources and the preserved April first-acquisition originals, including all unscored dates.')],
        selected_month='2026-02', selected_context_start=START.isoformat(),
        selected_score_start=SCORE_START.isoformat(), selected_score_end=END.isoformat(),
        selected_context_dates=[d.isoformat() for d in context], selected_score_dates=[d.isoformat() for d in score],
        calendar_path=str(calendar_path), calendar_sha256=calendar_ref['sha256'],
        selection_rule='Latest complete calendar month wholly before the earliest retained NDAQ/KO source; fixed 12-session context. February is a new explicitly authorized round after April source STOP, not an automatic retry or performance-based replacement.',
        prior_project_scope_reused=True, prior_exposure_group_count=len(audit['exposure_groups']),
        identified_files_rehashed=len(audit['matched_file_metadata']), database_files_rehashed=len(audit['database_audit']['files']),
        database_queries_repeated=0, anonymous_identity_evidence_files_rehashed=len(identity_refs),
        added_april_sources=sources, retained_april_protocol=protocol_ref,
        retained_april_preparation=preparation_ref, retained_april_acquisition=acquisition_ref,
        retained_april_stop=stopped_ref, anonymous_addendum=addendum_ref,
        git=dict(baseline_head=audit['git']['head'], checked_head=head, changed_paths_since_baseline=changed_paths,
            april_protocol_commit=APRIL_COMMIT, april_stop_commit=APRIL_STOP_COMMIT, fetched=False),
        unreadable_or_unclassified_relevant_metadata=issues,
        opaque_symbol_named_data=deepcopy(audit['opaque_symbol_named_data']),
        candidate_actual_ndaq_ko_development_or_tuning_exposure_identified=False if not issues else None,
        qualifications='No identified NDAQ/KO real-data use in January 14 through February 27 within the audited project scope; not proof of global ignorance or statistical independence.',
        limitations=deepcopy(audit['limitations']) + [
            'This is an incremental audit of already bound evidence plus the two April raw acquisitions; it does not repeat the 2175-file discovery or 112-database query audit.',
            'Existing source prices after March 16 are excluded conservatively whether scored or not; they do not establish point-in-time historical truth.',
            'No new candidate prices or performance were obtained for this eligibility delta. All old parameters and source guards must be separately frozen unchanged before acquisition.',
            'If new unbound evidence or material drift appears, this project-scoped eligibility conclusion must be revisited before execution.'])
    write_new(ROOT/'exposure-audit.json', result)
    print(json.dumps(dict(status=result['status'], addendum_status=addendum['status'],
        identified_files_rehashed=result['identified_files_rehashed'], database_files_rehashed=result['database_files_rehashed'],
        anonymous_identity_evidence_files_rehashed=len(identity_refs), unresolved_candidate_overlap_count=unknown,
        anonymous_groups_with_date_overlap=sum(r['date_check']['candidate_context_and_score_overlap_rows'] > 0 for r in records),
        excluded_start=first, excluded_end=last, context_sessions=len(context), score_sessions=len(score),
        audit_sha256=reference(ROOT/'exposure-audit.json')['sha256'], addendum_sha256=addendum_ref['sha256'],
        revalidation_sha256=checks_ref['sha256'], script_sha256=script_ref['sha256'])))


if __name__ == '__main__':
    main()
