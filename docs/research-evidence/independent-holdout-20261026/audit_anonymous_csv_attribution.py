"""Finite attribution of the 18 anonymous CSV groups; no price interpretation.

Reads metadata, retained bytes for hashes, CSV date/source columns and ledger
identity fields only. Does not request data, import strategy code or run economics.
"""
from __future__ import annotations
import base64
import csv
import io
import json
import sqlite3
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / 'exposure-audit-v2.json'
AUDIT_SHA = 'cac0cb85c56e3dedba85c40f8498cb828adfb6067ffaf7b79fee888d72614441'
DOCUMENTS = Path(r'C:\Users\Administrator\Documents\哈基米v2交易')
START, SCORE_START, END = date(2026, 3, 16), date(2026, 4, 1), date(2026, 4, 30)
TARGETS = {'NDAQ', 'KO', 'US.NDAQ', 'US.KO'}


def digest(raw):
    return sha256(raw).hexdigest()


def evidence(path, fields):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=digest(raw), bytes=len(raw), identity_fields=fields)


def embedded_matches(document, wanted):
    matches = []
    def walk(value, pointer=''):
        if isinstance(value, dict):
            if isinstance(value.get('raw_base64'), str):
                raw = base64.b64decode(value['raw_base64'], validate=True)
                if digest(raw) == wanted:
                    matches.append((raw, pointer + '/raw_base64'))
            for key, child in value.items():
                if key not in {'raw_base64', 'candles', 'quote', 'adjclose'}:
                    walk(child, pointer + '/' + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, pointer + '/' + str(index))
    walk(document)
    return matches


def metadata_identity(document):
    identity = document.get('identity', document.get('security_identity', {}))
    return dict(schema_version=document.get('schema_version'), security=document.get('security'),
        evidence_kind=document.get('evidence_kind'), selection_basis=identity.get('selection_basis'),
        valid_from=identity.get('valid_from'), valid_through=identity.get('valid_through'),
        price_source_reference=document.get('price_source', {}).get('reference'))


def calendar_date(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('DATE_EMPTY')
    text = text.strip()
    if text.isdecimal() and len(text) == 13:
        return datetime.fromtimestamp(int(text) / 1000, timezone.utc).date()
    if len(text) == 10:
        return date.fromisoformat(text)
    return datetime.fromisoformat(text.replace('Z', '+00:00')).date()


def ledger_identity(rows):
    symbols, types, invalid = set(), set(), 0
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {'symbol', 'ticker', 'stock_code', 'instid'} and isinstance(child, str):
                    symbols.add(child)
                elif isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for row in rows:
        types.add(row['type'])
        try:
            walk(json.loads(row['payload']))
        except (ValueError, TypeError):
            invalid += 1
    return dict(kind='TERMINAL_ACTIVITY_LEDGER', identity_columns=['time', 'type', 'payload'],
        payload_symbol_fields=sorted(symbols), activity_types=sorted(types), invalid_payload_count=invalid,
        target_symbol_matches=sorted(TARGETS.intersection(symbols)),
        limitation='Activity timestamps are not necessarily embedded market-data dates; symbol metadata was also checked.')


def main():
    audit_raw = AUDIT.read_bytes()
    assert digest(audit_raw) == AUDIT_SHA
    audit = json.loads(audit_raw)
    assert (audit['selected_context_start'], audit['selected_score_start'], audit['selected_score_end']) == (
        START.isoformat(), SCORE_START.isoformat(), END.isoformat())
    groups = [r for r in audit['csv_audit']['records'] if r['status'] == 'UNCLASSIFIED_NO_SYMBOL_METADATA']
    assert len(groups) == 18
    records = []
    for group in groups:
        wanted = group['sha256']
        locations = [Path(value) for value in group['locations']]
        representative = next((p for p in locations if p.suffix.lower() == '.csv'), locations[0])
        raw = representative.read_bytes()
        references = []
        if representative.suffix.lower() == '.json':
            document = json.loads(raw)
            matches = embedded_matches(document, wanted)
            assert matches
            references.append(evidence(representative, dict(**metadata_identity(document),
                matching_embedded_sha256=wanted, matching_json_pointers=[x[1] for x in matches])))
            raw = matches[0][0]
        assert digest(raw) == wanted
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), strict=True)
        header = reader.fieldnames
        assert header and len(set(header)) == len(header)
        rows = list(reader)
        columns = [key for key in header if key.lower() in {'date', 'session_date', 'trading_date', 'timestamp', 'time_key', 'time'}]
        dates, errors = [], []
        if len(columns) != 1:
            errors.append(dict(code='DATE_COLUMN_NOT_UNIQUE'))
        else:
            for index, row in enumerate(rows, start=2):
                if None in row or any(value is None for value in row.values()):
                    errors.append(dict(code='MALFORMED_ROW_WIDTH', row=index))
                    continue
                try:
                    dates.append(calendar_date(row[columns[0]]))
                except (ValueError, OverflowError, OSError):
                    errors.append(dict(code='INVALID_DATE', row=index))
        overlap = sum(START <= day <= END for day in dates)
        attribution = None
        if header == ['time', 'type', 'payload']:
            attribution = ledger_identity(rows)
            references.append(evidence(representative, attribution))
        elif representative.name == 'btc_daily_prices.csv':
            database = representative.with_suffix('.sqlite')
            wal = Path(str(database) + '-wal')
            wal_bytes = wal.stat().st_size if wal.exists() else 0
            assert wal_bytes == 0, 'BTC database has live WAL; no immutable attribution allowed'
            database_sha = digest(database.read_bytes())
            connection = sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True)
            try:
                db_rows = connection.execute('SELECT symbol, source, trading_date FROM btc_daily_prices ORDER BY trading_date').fetchall()
                identities = connection.execute('SELECT symbol, market, source FROM symbols').fetchall()
            finally:
                connection.close()
            assert digest(database.read_bytes()) == database_sha
            csv_meta = sorted((row['date'], row['source']) for row in rows)
            assert csv_meta == sorted((row[2], row[1]) for row in db_rows)
            assert {row[0] for row in db_rows} == {'BTC-USDT'}
            assert identities == [('BTC-USDT', 'crypto', 'okx')]
            attribution = dict(kind='OTHER_INSTRUMENT', symbol='BTC-USDT', market='crypto', source='okx',
                evidence_basis='Companion database all-row date/source equality, one symbol, matching documented CSV row count/range and symbol-filtered export code.',
                no_price_equality_claim=True)
            references.append(evidence(database, dict(symbols=identities, rows=len(db_rows),
                date_source_columns_exactly_match_csv=True, wal_bytes=wal_bytes,
                queried_columns=['symbol', 'source', 'trading_date'], read_mode='ro&immutable=1')))
            docs = DOCUMENTS / 'outputs/python_quant_bot/docs/btc_daily_database.md'
            references.append(evidence(docs, dict(relevant_lines=[18,19,20,21],
                documented_symbol='BTC-USDT', documented_source='OKX', documented_rows=3079,
                documented_start='2018-01-11', documented_end='2026-06-16')))
            generator = DOCUMENTS / 'outputs/python_quant_bot/build_btc_daily_database.py'
            references.append(evidence(generator, dict(default_symbol='BTC-USDT', default_symbol_line=17,
                export_function='export_csv', symbol_predicate_lines=[184,189,191], csv_header_line=195)))
        elif representative.name == 'BTC-USDT_1h.csv':
            attribution = dict(kind='OTHER_INSTRUMENT_FILENAME', symbol='BTC-USDT', timeframe='1h',
                evidence_basis='Existing cache filename plus all CSV dates outside candidate interval; no price authentication claimed.')
            references.append(evidence(representative, dict(filename=representative.name)))
        elif representative.name == 'original.csv' and (representative.parent / 'conversion.json').exists():
            conversion_path = representative.parent / 'conversion.json'
            conversion = json.loads(conversion_path.read_bytes())
            assert conversion['original_csv_sha256'] == wanted
            assert conversion['normalized_csv_sha256'] == '26d27fcc06b6171301c5907bbec84e587f21f2370866287230223eea1caac3b9'
            attribution = dict(kind='SYNTHETIC_COLUMN_MAPPING_SOURCE', normalized_group_sha256=conversion['normalized_csv_sha256'],
                evidence_basis='Saved conversion receipt links original bytes to separately attributed TEST fixture; candidate dates also do not overlap.')
            references.append(evidence(conversion_path, conversion))
        else:
            candidates = []
            if representative.suffix.lower() == '.json':
                candidates.append(representative)
            for name in ['metadata.json', 'input-provided-metadata.json', 'synthetic_daily.manifest.json']:
                candidate = representative.parent / name
                if candidate.exists():
                    candidates.append(candidate)
            # Prefer an unmodified accepted snapshot over deliberately bad copies.
            candidates.extend(p for p in locations if p.suffix.lower() == '.json' and 'bad-copies' not in str(p))
            for candidate in dict.fromkeys(candidates):
                doc = json.loads(candidate.read_bytes())
                if not embedded_matches(doc, wanted):
                    continue
                security = doc.get('security', {})
                if str(security.get('security_id', '')).startswith('SYNTHETIC:'):
                    attribution = dict(kind='SYNTHETIC_FIXTURE', symbol=security.get('symbol'),
                        security_id=security['security_id'], evidence_kind=doc.get('evidence_kind'))
                    references.append(evidence(candidate, dict(**metadata_identity(doc), matching_embedded_sha256=wanted)))
                    break
            if attribution is None and (representative.parent / 'config.json').exists():
                config_path = representative.parent / 'config.json'
                config = json.loads(config_path.read_bytes())
                if config.get('symbol') == 'SYNTH-001':
                    attribution = dict(kind='SYNTHETIC_CONFIGURED_DATASET', symbol=config['symbol'])
                    references.append(evidence(config_path, dict(symbol=config['symbol'], data=config.get('data'))))
        date_pass = bool(dates) and not errors
        resolved_other = attribution is not None and attribution['kind'] in {
            'SYNTHETIC_FIXTURE', 'SYNTHETIC_CONFIGURED_DATASET', 'SYNTHETIC_COLUMN_MAPPING_SOURCE', 'OTHER_INSTRUMENT'}
        resolved_ledger = attribution is not None and attribution['kind'] == 'TERMINAL_ACTIVITY_LEDGER' and not attribution['target_symbol_matches'] and not attribution['invalid_payload_count']
        unresolved = not date_pass or (overlap > 0 and not (resolved_other or resolved_ledger))
        records.append(dict(sha256=wanted, bytes=len(raw), locations=group['locations'],
            representative_path=str(representative), representative_container_sha256=digest(representative.read_bytes()),
            attribution=attribution, evidence=references,
            date_check=dict(columns=columns, rows=len(rows), valid_date_rows=len(dates),
                start=min(dates).isoformat() if dates else None, end=max(dates).isoformat() if dates else None,
                candidate_context_and_score_overlap_rows=overlap, issues=errors,
                timestamp_policy='Epoch milliseconds converted in UTC; ISO date prefix retained for named calendar-date data.'),
            status='UNRESOLVED_CANDIDATE_OVERLAP' if unresolved else ('RESOLVED_OTHER_OR_SYNTHETIC' if resolved_other else 'NO_CANDIDATE_DATE_OVERLAP'),
            unresolved_candidate_overlap=unresolved))
    unresolved_count = sum(record['unresolved_candidate_overlap'] for record in records)
    assert digest(AUDIT.read_bytes()) == AUDIT_SHA
    result = dict(schema_version='anonymous-csv-attribution-v1', recorded_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        status='PASS_NO_UNRESOLVED_CANDIDATE_OVERLAP' if unresolved_count == 0 else 'NEEDS_SCOPE_REVIEW',
        audit_path=str(AUDIT), audit_sha256=AUDIT_SHA, candidate_context_start=START.isoformat(),
        candidate_score_start=SCORE_START.isoformat(), candidate_score_end=END.isoformat(),
        unresolved_candidate_overlap_count=unresolved_count, groups_checked=len(records),
        candidate_selection_changed=False, new_source_requests=0, economic_runs=0,
        price_values_interpreted=False, return_values_interpreted=False,
        records=records, script_sha256=digest(Path(__file__).read_bytes()),
        limitations=['Finite supplement to the 18 exact content groups in exposure-audit-v2; no expansion of global audit scope.',
            'Metadata attribution is not external source authentication or proof of statistical independence.',
            'Stored bytes are hashed and mechanically parsed to isolate metadata; OHLCV and performance values are neither evaluated nor emitted.',
            'The BTC companion check compares dates/source/identity, not price values; symbol attribution also relies on the existing documentation and symbol-filtered export implementation.'])
    destination = ROOT / 'anonymous-csv-attribution.json'
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], groups=len(records), unresolved_candidate_overlap_count=unresolved_count,
        groups_with_date_overlap=sum(record['date_check']['candidate_context_and_score_overlap_rows'] > 0 for record in records),
        candidate_selection_changed=False, sha256=digest(destination.read_bytes()))))


if __name__ == '__main__':
    main()
