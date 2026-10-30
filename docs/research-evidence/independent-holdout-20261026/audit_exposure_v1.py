"""Project-scoped exposure inventory: dates/identities only, no price or return output.

Read-only against existing projects. Writes one new audit in this evidence folder.
Candidate prices are neither requested nor inspected; JSON/CSV fields used below
are restricted to symbols, timestamps, schema/provenance and immutable identities.
"""
from __future__ import annotations
import base64
import csv
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from urllib.parse import quote
from zoneinfo import ZoneInfo

BASE = Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022')
REPO = BASE / '哈基米v2交易'
DOCUMENTS = Path(r'C:\Users\Administrator\Documents\哈基米v2交易')
OUTPUT = Path(__file__).resolve().parent
PRUNE = {'.git', 'node_modules', 'venv', '.venv', 'site-packages', '__pycache__', '.pytest_cache', 'build', 'dist'}
SYMBOLS = {'NDAQ', 'KO'}
rows, files, errors, database_rows, opaque = [], {}, [], [], []


def symbol(value):
    if type(value) is not str:
        return None
    value = value.upper().split(':')[-1]
    value = value.removeprefix('US.')
    return value if value in SYMBOLS else None


def stamp(value):
    if type(value) is str:
        match = re.match(r'^(\d{4}-\d{2}-\d{2})', value)
        if match:
            try:
                return date.fromisoformat(match[1]).isoformat()
            except ValueError:
                return None
    return None


def add(kind, sym, first, last, path, identity=None, raw_hash=None, note=None):
    if sym in SYMBOLS and first and last:
        rows.append(dict(kind=kind, symbol=sym, start=first, end=last, file=str(path),
                         identity=identity, payload_sha256=raw_hash, note=note))


def csv_dates(raw, sym, path, raw_hash):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not reader.fieldnames:
            return
        date_keys = [k for k in reader.fieldnames if k.lower() in {'date', 'session_date', 'trading_date', 'timestamp', 'time_key', 'time'}]
        symbol_keys = [k for k in reader.fieldnames if k.lower() in {'symbol', 'stock_code', 'ticker', 'code'}]
        found = {}
        for row in reader:
            current = next((symbol(row[k]) for k in symbol_keys if symbol(row[k])), sym)
            day = next((stamp(row[k]) for k in date_keys if stamp(row[k])), None)
            if current in SYMBOLS and day:
                found.setdefault(current, []).append(day)
        for current, dates in found.items():
            add('retained_csv_date_metadata', current, min(dates), max(dates), path, raw_hash=raw_hash)
    except (UnicodeError, csv.Error):
        return


def chart_metadata(doc, path, raw_hash):
    chart = doc.get('chart') if type(doc) is dict else None
    if type(chart) is not dict or type(chart.get('result')) is not list:
        return
    for result in chart['result']:
        if type(result) is not dict:
            continue
        sym = symbol(result.get('meta', {}).get('symbol'))
        if sym not in SYMBOLS:
            continue
        dates = [datetime.fromtimestamp(v, ZoneInfo('America/New_York')).date().isoformat()
                 for v in result.get('timestamp', []) if type(v) is int and v > 0]
        if dates:
            add('retained_provider_response', sym, min(dates), max(dates), path, raw_hash=raw_hash,
                note='Timestamp metadata only; retained source is conservatively excluded even if not scored.')


def inspect_json(doc, path, raw_hash):
    if type(doc) is not dict:
        return
    chart_metadata(doc, path, raw_hash)
    security = doc.get('security', {})
    sym = symbol(security.get('symbol')) if type(security) is dict else None
    if sym:
        sessions = doc.get('sessions', [])
        dates = [stamp(r.get('date')) for r in sessions if type(r) is dict]
        dates = [x for x in dates if x]
        if dates:
            add('retained_snapshot_context', sym, min(dates), max(dates), path,
                identity=doc.get('snapshot_id'), raw_hash=raw_hash, note=doc.get('evidence_kind'))
    task = doc.get('task', doc)
    if type(task) is dict and type(task.get('experiment')) is dict:
        snap = path.parent / 'inputs/snapshot.json'
        if snap.is_file():
            data = json.loads(snap.read_bytes())
            current = symbol(data.get('security', {}).get('symbol'))
            spec = task['experiment']
            add('saved_run_score' if doc.get('run_id') else 'saved_task_score', current,
                stamp(spec.get('score_start_session')), stamp(spec.get('score_end_session')), path,
                identity=doc.get('run_id', spec.get('snapshot_id')), raw_hash=raw_hash,
                note=task.get('strategy'))
    if type(doc.get('schema_version')) is str and doc['schema_version'].startswith('fixed-month-replay-design-'):
        for current in doc.get('sources', {}):
            add('frozen_design_score', current, stamp(doc.get('score_start')), stamp(doc.get('score_end')),
                path, identity=doc.get('plan_hash'), raw_hash=raw_hash)
    if type(doc.get('policy')) is dict and doc['policy'].get('id') == 'YAHOO_QUOTE_POST_WINDOW_DIVIDEND_RECONCILIATION_V1':
        current = symbol(path.parent.name)
        dates = [stamp(r.get('date')) for r in doc.get('factor_path', []) if type(r) is dict]
        dates = [x for x in dates if x]
        if dates:
            add('numeric_source_reconciliation', current, min(dates), max(dates), path,
                raw_hash=raw_hash, note='Dates from recorded factor audit; no ratio/price/return inspected here.')
    # Inspect embedded retained source bytes only for timestamps/header dates.
    def embedded(node, inherited=sym):
        if type(node) is dict:
            current = symbol(node.get('symbol')) or inherited
            content = node.get('raw_base64')
            if type(content) is str:
                try:
                    raw = base64.b64decode(content, validate=True)
                    h = sha256(raw).hexdigest()
                    if raw.lstrip().startswith(b'{'):
                        value = json.loads(raw)
                        chart_metadata(value, path, h)
                    else:
                        csv_dates(raw, current, path, h)
                except (ValueError, UnicodeError):
                    pass
            for key, value in node.items():
                if key not in {'candles', 'timestamp', 'quote', 'adjclose', 'result', 'raw_base64'}:
                    embedded(value, current)
        elif type(node) is list:
            for value in node:
                if type(value) in (dict, list):
                    embedded(value, inherited)
    embedded(doc)


def scan_files():
    names = {'inputs.json', 'task.json', 'check.json', 'report.json', 'validation.json',
             'snapshot.json', 'source-yahoo-chart.json', 'historical-adjustment-reconciliation.json'}
    parsed = 0
    for root in (BASE, DOCUMENTS):
        for folder, dirs, names_here in os.walk(root):
            dirs[:] = [name for name in dirs if name not in PRUNE
                       and not (Path(folder) / name).is_symlink()
                       and not (Path(folder) / name).is_junction()
                       and (Path(folder) / name).resolve() != OUTPUT]
            for name in names_here:
                path = Path(folder) / name
                if path.is_symlink():
                    continue
                relevant_json = path.suffix.lower() == '.json' and (name in names or 'design' in name
                    or 'yahoo' in name.lower() or name.startswith('task-') or name.startswith('source-'))
                if not relevant_json:
                    if path.suffix.lower() in {'.csv', '.parquet', '.feather', '.xlsx'}:
                        matched = next((s for s in SYMBOLS if re.search(r'(^|[^A-Za-z])' + s + r'([^A-Za-z]|$)', str(path), re.I)), None)
                        if matched and path.suffix.lower() == '.csv':
                            raw = path.read_bytes(); h = sha256(raw).hexdigest()
                            files[str(path)] = dict(sha256=h, bytes=len(raw), reader='date_and_symbol_columns_only')
                            csv_dates(raw, matched, path, h)
                        elif matched:
                            opaque.append(str(path))
                    continue
                try:
                    raw = path.read_bytes()
                    if len(raw) > 64 * 1024 * 1024:
                        errors.append(dict(path=str(path), reason='metadata_file_over_64MiB_not_parsed'))
                        continue
                    doc = json.loads(raw)
                    before = len(rows)
                    inspect_json(doc, path, sha256(raw).hexdigest())
                    parsed += 1
                    if len(rows) != before:
                        files[str(path)] = dict(sha256=sha256(raw).hexdigest(), bytes=len(raw), reader='identity_dates_only')
                except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
                    errors.append(dict(path=str(path), reason=type(exc).__name__))
    return parsed


def scan_databases():
    root = DOCUMENTS / 'outputs/python_quant_bot/runtime'
    chosen = {'stock_candles_cache.sqlite', 'stock_corporate_actions.sqlite',
              'stock_candles_cache_pre_yahoo_volume_v2_20260802T001759Z.sqlite', 'strategy_pipeline.sqlite3',
              'portfolio_experiments.sqlite3', 'portfolio_forward_performance.sqlite', 'portfolio_shadow.sqlite',
              'paper_ledger.sqlite3', 'exchange_terminal_ledger.sqlite3', 'research_bridge.sqlite3'}
    q = lambda value: '"' + value.replace('"', '""') + '"'
    databases, symbol_tables, json_columns, wal = [], 0, 0, []
    for path in root.rglob('*'):
        if not path.is_file() or path.name not in chosen:
            continue
        if path.with_name(path.name + '-wal').exists():
            wal.append(str(path))
        db = sqlite3.connect('file:' + quote(path.as_posix(), safe='/:') + '?mode=ro&immutable=1', uri=True)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            cols = [r[1] for r in db.execute('PRAGMA table_info(' + q(table) + ')')]
            for col in cols:
                if col.lower() in {'symbol', 'ticker', 'stock_code', 'code'}:
                    symbol_tables += 1
                    count = db.execute('SELECT count(*) FROM ' + q(table) + ' WHERE upper(cast(' + q(col)
                        + ' as text)) IN (?,?,?,?)', ('NDAQ', 'KO', 'US.NDAQ', 'US.KO')).fetchone()[0]
                    if count:
                        database_rows.append(dict(database=str(path), table=table, column=col, matches=count))
                if col.endswith('_json'):
                    json_columns += 1
                    # Prefilter text, then inspect only the symbol keys. No
                    # numerical field, historical return or price is selected.
                    sql = ('SELECT count(*) FROM ' + q(table) + ' e WHERE json_valid(e.' + q(col) + ') AND EXISTS('
                           'SELECT 1 FROM json_tree(CASE WHEN json_valid(e.' + q(col) + ') THEN e.' + q(col) + " ELSE '{}' END) j WHERE lower(cast(j.key as text)) "
                           "IN ('symbol','ticker','stock_code','code') AND upper(cast(j.value as text)) IN (?,?,?,?))")
                    count = db.execute(sql, ('NDAQ', 'KO', 'US.NDAQ', 'US.KO')).fetchone()[0]
                    if count:
                        database_rows.append(dict(database=str(path), table=table, column=col, matches=count,
                                                  note='Symbol inside JSON; date range requires follow-up metadata extraction.'))
        db.close()
        databases.append(dict(path=str(path), bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest()))
    return dict(files=databases, count=len(databases), symbol_columns_checked=symbol_tables,
                json_columns_checked=json_columns, matching_records=database_rows, wal_sidecars_not_read=wal,
                access='SQLite mode=ro&immutable=1; no WAL present if listed array is empty.')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True, encoding='utf-8').strip()


def main():
    destination = OUTPUT / 'exposure-audit.json'
    if destination.exists():
        raise ValueError('Audit already exists; preserve it.')
    parsed = scan_files()
    db = scan_databases()
    grouped = {}
    for row in rows:
        key = (row['kind'], row['symbol'], row['start'], row['end'], row.get('identity'), row.get('payload_sha256'))
        item = grouped.setdefault(key, {k: v for k, v in row.items() if k != 'file'})
        item.setdefault('locations', []).append(row['file'])
    provider_rows = [r for r in rows if r['kind'] == 'retained_provider_response']
    first = min(date.fromisoformat(r['start']) for r in provider_rows)
    last = max(date.fromisoformat(r['end']) for r in provider_rows)
    # Latest whole calendar month whose entire warmup and score precede the
    # earliest retained source; selection uses dates, not returns/events.
    month_end = first.replace(day=1) - timedelta(days=1)
    month_start = month_end.replace(day=1)
    calendar_path = REPO / 'src/hakimi_research/resources/us-equity-calendar-2026.json'
    calendar = json.loads(calendar_path.read_bytes())
    holidays = set(calendar['holidays'])
    def open_days(a, b):
        return [a + timedelta(days=i) for i in range((b-a).days+1)
                if (a + timedelta(days=i)).weekday() < 5 and (a + timedelta(days=i)).isoformat() not in holidays]
    score = open_days(month_start, month_end)
    preceding = open_days(date(month_start.year, 1, 1), month_start-timedelta(days=1))[-12:]
    assert len(preceding) == 12 and score[-1] < first and preceding[0] >= date(2026, 1, 1)
    refs = git('for-each-ref', '--format=%(refname) %(objectname)').splitlines()
    history = git('log', '--all', '--format=%H %cs %s', '-G', r'NDAQ|(^|[^A-Za-z])KO([^A-Za-z]|$)', '--',
                  'docs', 'configs', 'examples', 'tests', 'tools', 'outputs/python_quant_bot').splitlines()
    unresolved = bool(errors or opaque or database_rows or db['wal_sidecars_not_read'])
    result = dict(schema_version='project-scoped-holdout-exposure-audit-v1',
        status='NEEDS_SCOPE_REVIEW' if unresolved else 'PASS_PROJECT_SCOPE', recorded_at=datetime.now(timezone.utc).isoformat(),
        read_only=True, new_source_requests=0, economic_runs=0,
        audit_roots=[str(BASE), str(DOCUMENTS)], excluded_new_delivery_root=str(OUTPUT),
        parser_scope='Known task/run/snapshot/source/check/design JSON plus symbol-named CSV; only identities and dates emitted.',
        pruned_directories=sorted(PRUNE), parsed_metadata_files=parsed,
        evidence_deduplication='Unique content/identity/range groups; repeated workspace copies are locations, not new exposures.',
        exposure_groups=list(grouped.values()), matched_file_metadata=files,
        excluded_intervals=[dict(start=first.isoformat(), end=last.isoformat(), symbols=sorted(SYMBOLS),
            reason='Entire already-retained source interval conservatively excluded, including unscored prices.')],
        selection_rule='Within the verified 2026 calendar choose the latest complete calendar month whose full fixed 12-session context and scoring interval predate the earliest retained NDAQ/KO source.',
        selected_month=month_start.strftime('%Y-%m'), selected_context_start=preceding[0].isoformat(),
        selected_score_start=score[0].isoformat(), selected_score_end=score[-1].isoformat(),
        selected_context_dates=[d.isoformat() for d in preceding], selected_score_dates=[d.isoformat() for d in score],
        calendar_sha256=sha256(calendar_path.read_bytes()).hexdigest(),
        database_audit=db, unreadable_or_unclassified_relevant_metadata=errors, opaque_symbol_named_data=opaque,
        git=dict(head=git('rev-parse','HEAD'), visible_ref_count=len(refs), visible_commit_count=int(git('rev-list','--all','--count')),
                 refs=refs, symbol_change_commits=history, fetched=False),
        limitations=[
            'Project-scope absence of identified use is not global unviewed-data or statistical-independence proof.',
            'Cannot audit deleted/unreachable Git objects, external chats/accounts/files, human memory or model pretraining.',
            'Anonymous price files without symbol metadata and unlisted proprietary/binary stores are not certified.',
            'Only locally visible Git refs/history are covered; no remote fetch was performed.',
            'Known synthetic strategy tests are development evidence, not independent real-market observations.',
            'Data intake/quality reconciliation used future-to-window source metadata in the prior retrospective study; all retained source dates are excluded here.',
        ], script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('status','parsed_metadata_files','excluded_intervals','selected_month',
        'selected_context_start','selected_score_start','selected_score_end')},ensure_ascii=False))
    print(json.dumps({'groups':len(grouped),'errors':len(errors),'opaque':len(opaque),'database_matches':len(database_rows),
        'database_files':db['count'],'database_json_columns':db['json_columns_checked']},ensure_ascii=False))


if __name__ == '__main__':
    main()
