"""Pure, separate review of retained prices plus source-backed action coverage.

No source reader is installed here. A service must inject an independently
reviewed, pure SourceReader for a real provider/export format. A renderer may
provide original source bytes, never a reader or a completeness boolean. The
reader must extract the fields below from those bytes; hashes and this module
do not authenticate the provider or prove external truth.

Reader page contract: security (symbol, exchange, currency, instrument_type,
source_security_id as actually declared by that source),
coverage_start/end, date_basis=EFFECTIVE_DATE, coverage_status=COMPLETE,
covered_action_types, as_of, page_id, page_index (1 based), total_pages,
next_page_id (null on final page), total_records, actions. Each action has
action_id, security_id, action_type, effective_date, source_reference, details.
Complete means an explicit source coverage/result declaration, not an empty
list inferred from a missing field or a search with no matches.

The old check remains BLOCKED. This new check can propose a separate ordinary
canonical input, only for action-free windows, with source_truth_verified=false.
No file, network, task, research run, order, or old record is written here.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import io
from typing import Callable

from . import daily_updates as daily
from . import stock_intake as intake
from .documents import digest, parse_document
from .equity_dataset import build_equity_snapshot


SCHEMA = 'workbench-stock-supplement-check-v1'
EVIDENCE_SCHEMA = 'stock-action-source-evidence-v1'
EVIDENCE_TYPE = 'SOURCE_COMPLETE_ACTION_EXPORT'
ARTIFACTS = ('check.json', 'request-started.json', 'source-original.bin', 'calendar.json')
ACTION_TYPES = ('CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'REVERSE_SPLIT',
                'CAPITAL_DISTRIBUTION', 'SPIN_OFF', 'RIGHTS', 'MERGER', 'SECURITY_IDENTITY_CHANGE')
_PAGE_FIELDS = {'security', 'coverage_start', 'coverage_end', 'date_basis', 'coverage_status',
                'covered_action_types', 'as_of', 'page_id', 'page_index', 'total_pages',
                'next_page_id', 'total_records', 'actions'}
_ACTION_FIELDS = {'action_id', 'security_id', 'action_type', 'effective_date', 'source_reference', 'details'}
_MISSING = 'SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN'


@dataclass(frozen=True)
class SourceReader:
    """Trusted integration dependency; never deserialize this from a request.

    parse_page must be pure, strict about its real source schema, and extract
    every completeness/identity/pagination field from the original bytes.
    This repository supplies no production SourceReader and no real acceptance.
    """
    contract_id: str
    parse_page: Callable[[bytes], dict]


def _require(condition, reason):
    daily._require(condition, 'SUPPLEMENT_' + reason)


def _fields(value, fields, label):
    _require(type(value) is dict and set(value) == set(fields), label + '_FIELDS_INVALID')


def _text(value, label, maximum=2048):
    _require(type(value) is str and 0 < len(value) <= maximum and value == value.strip()
             and not any(ord(c) < 32 for c in value), label + '_TEXT_INVALID')
    return value


def _utc(value):
    _text(value, 'TIME', 40)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require(parsed.tzinfo is not None, 'EXPLICIT_TIMEZONE_REQUIRED')
    return parsed.astimezone(timezone.utc)


def _day(value):
    _require(type(value) is str and len(value) == 10 and date.fromisoformat(value).isoformat() == value,
             'DATE_INVALID')
    return value


def _ref(value):
    _text(value, 'SOURCE_REFERENCE')
    _require(value.startswith(('https://', 'urn:')), 'SOURCE_REFERENCE_INVALID')
    return value


def _retained(raw):
    return dict(raw_sha256=sha256(raw).hexdigest(), raw_base64=base64.b64encode(raw).decode('ascii'))


def _original(artifacts):
    _fields(artifacts, ARTIFACTS, 'ORIGINAL_ARTIFACTS')
    _require(all(type(raw) is bytes and 0 < len(raw) <= daily._MAX for raw in artifacts.values()),
             'ORIGINAL_BYTES_REQUIRED')
    checked = parse_document(artifacts['check.json'])
    _require(checked.get('schema_version') == intake.SCHEMA
             and checked.get('check_hash') == digest({k: v for k, v in checked.items() if k != 'check_hash'})
             and checked.get('status') == 'BLOCKED' and checked.get('can_save') is False
             and checked.get('reason') == _MISSING
             and checked.get('stop_detail', {}).get('code') == _MISSING
             and checked.get('evidence_kind') == 'IMPORTED_UNVERIFIED'
             and checked.get('source_truth_verified') is False, 'ORIGINAL_BLOCKED_CHECK_REQUIRED')
    inventory = checked.get('artifacts')
    _fields(inventory, set(ARTIFACTS) - {'check.json'}, 'ORIGINAL_INVENTORY')
    for name, expected in inventory.items():
        _require(sha256(artifacts[name]).hexdigest() == expected, 'ORIGINAL_ARTIFACT_CHANGED:' + name)
    _require(checked.get('raw_sha256') == inventory['source-original.bin'], 'ORIGINAL_RAW_BINDING_CHANGED')
    request = parse_document(artifacts['request-started.json'])
    _require(request == dict(symbol=checked['symbol'], history_sessions=checked['history_sessions'],
             reference=checked['source_url'], started_at=checked['checked_at'], automatic_retry=False),
             'ORIGINAL_REQUEST_BINDING_CHANGED')
    _require(type(checked['history_sessions']) is int and checked['history_sessions'] in intake.HISTORY_SESSIONS,
             'ORIGINAL_HISTORY_INVALID')
    price_at = _utc(checked['retrieved_at'])
    _require(_utc(checked['checked_at']) <= price_at, 'ORIGINAL_TIME_ORDER_INVALID')
    raw = artifacts['source-original.bin']
    security, company = intake._security(raw, checked['symbol'], checked['intake_id'])
    _require(checked['security'] == security and checked['company_name'] == company, 'ORIGINAL_SECURITY_CHANGED')
    fields = daily._quote_fields(raw, {'security': security})
    _require('events' not in fields[0], 'ONLY_ABSENT_EVENT_FIELD_SUPPORTED')
    calendar = parse_document(artifacts['calendar.json'])
    exchanges = [calendar['exchange']] if 'years' in calendar else daily._exchanges(calendar)
    _require(security['exchange'] in exchanges and _utc(calendar['recorded_at']) <= price_at,
             'ORIGINAL_CALENDAR_IDENTITY_INVALID')
    last = daily._last_complete(calendar, price_at)
    opened = [row for row in daily._days(calendar, date(min(daily._calendar_years(calendar)), 1, 1),
                                        date.fromisoformat(last)) if row['kind'] == 'OPEN']
    _require(len(opened) >= checked['history_sessions'], 'ORIGINAL_CALENDAR_COVERAGE_INVALID')
    first = opened[-checked['history_sessions']]['date']
    _require((first, last) == (checked['coverage_start'], checked['coverage_end'])
             and first >= _day(checked['query_start']), 'ORIGINAL_WINDOW_CHANGED')
    days = daily._days(calendar, date.fromisoformat(first), date.fromisoformat(last))
    binding = dict(original_check_hash=checked['check_hash'], original_raw_sha256=checked['raw_sha256'],
                   original_calendar_sha256=inventory['calendar.json'], security=deepcopy(security),
                   coverage_start=first, coverage_end=last)
    return checked, calendar, days, fields, binding


def supplement_template(original_artifacts):
    """A deliberately incomplete form. It cannot pass review without raw evidence."""
    _, _, _, _, binding = _original(original_artifacts)
    return dict(schema_version=EVIDENCE_SCHEMA, evidence_type=EVIDENCE_TYPE, binding=binding,
                source_contract_id=None, source_name=None, source_reference=None,
                retrieved_at=None, pages=[])


def _evidence(evidence, binding, reader, checked_at, last_close):
    _require(isinstance(reader, SourceReader) and callable(reader.parse_page), 'SOURCE_READER_NOT_CONFIGURED')
    _text(reader.contract_id, 'SOURCE_CONTRACT_ID', 180)
    _fields(evidence, {'schema_version', 'evidence_type', 'binding', 'source_contract_id', 'source_name',
                       'source_reference', 'retrieved_at', 'pages'}, 'EVIDENCE')
    _require(evidence['schema_version'] == EVIDENCE_SCHEMA and evidence['evidence_type'] == EVIDENCE_TYPE,
             'SOURCE_EVIDENCE_TYPE_UNSUPPORTED')
    _require(evidence['binding'] == binding, 'EVIDENCE_BINDING_CHANGED')
    _require(evidence['source_contract_id'] == reader.contract_id, 'SOURCE_CONTRACT_MISMATCH')
    _text(evidence['source_name'], 'SOURCE_NAME', 180)
    _ref(evidence['source_reference'])
    obtained = _utc(evidence['retrieved_at'])
    _require(obtained <= checked_at, 'SOURCE_RECEIVED_AFTER_CHECK')
    pages = evidence['pages']
    _require(type(pages) is list and 1 <= len(pages) <= 32, 'ORIGINAL_SOURCE_PAGES_REQUIRED')
    decoded, retained, total_bytes = [], [], 0
    for page in pages:
        _fields(page, {'source_reference', 'raw_base64'}, 'SOURCE_PAGE')
        _ref(page['source_reference'])
        _require(type(page['raw_base64']) is str and len(page['raw_base64']) <= daily._MAX * 2,
                 'SOURCE_PAGE_BYTES_INVALID')
        raw = base64.b64decode(page['raw_base64'], validate=True)
        total_bytes += len(raw)
        _require(0 < len(raw) <= daily._MAX and total_bytes <= daily._MAX, 'SOURCE_PAGE_SIZE_INVALID')
        projection = deepcopy(reader.parse_page(raw))
        _fields(projection, _PAGE_FIELDS, 'SOURCE_PAGE_PROJECTION')
        decoded.append(projection)
        retained.append(dict(source_reference=page['source_reference'], **_retained(raw)))
    seen_pages, seen_actions, outside = set(), set(), []
    total_records, common = None, None
    for index, row in enumerate(decoded):
        source_security = row['security']
        _fields(source_security, {'symbol', 'exchange', 'currency', 'instrument_type', 'source_security_id'},
                'SOURCE_SECURITY')
        _text(source_security['source_security_id'], 'SOURCE_SECURITY_ID', 180)
        _require(all(source_security[key] == binding['security'][key]
                     for key in ('symbol', 'exchange', 'currency', 'instrument_type')), 'SOURCE_SECURITY_MISMATCH')
        first, last = _day(row['coverage_start']), _day(row['coverage_end'])
        _require(first <= binding['coverage_start'] <= binding['coverage_end'] <= last, 'SOURCE_COVERAGE_INCOMPLETE')
        _require(row['coverage_status'] == 'COMPLETE' and row['date_basis'] == 'EFFECTIVE_DATE',
                 'SOURCE_COVERAGE_NOT_EXPLICIT_COMPLETE')
        kinds = row['covered_action_types']
        _require(type(kinds) is list and all(type(kind) is str for kind in kinds)
                 and len(set(kinds)) == len(kinds) and set(kinds) == set(ACTION_TYPES), 'SOURCE_ACTION_TYPES_INCOMPLETE')
        _require(last_close <= _utc(row['as_of']) <= obtained, 'SOURCE_ASOF_OUTSIDE_KNOWN_WINDOW')
        shared = {k: row[k] for k in ('security', 'coverage_start', 'coverage_end', 'coverage_status',
                                    'date_basis', 'covered_action_types', 'as_of')}
        _require(common is None or common == shared, 'SOURCE_PAGE_COVERAGE_CONFLICT')
        common = shared
        page_id = _text(row['page_id'], 'PAGE_ID', 180)
        _require(page_id not in seen_pages, 'SOURCE_DUPLICATE_PAGE')
        seen_pages.add(page_id)
        _require(type(row['page_index']) is int and row['page_index'] == index + 1
                 and type(row['total_pages']) is int and row['total_pages'] == len(decoded),
                 'SOURCE_PAGE_SEQUENCE_INCOMPLETE')
        next_id = decoded[index + 1]['page_id'] if index + 1 < len(decoded) else None
        _require(row['next_page_id'] == next_id, 'SOURCE_PAGINATION_NOT_FINISHED')
        count = row['total_records']
        _require(type(count) is int and 0 <= count <= 10000 and (total_records is None or count == total_records),
                 'SOURCE_TOTAL_RECORDS_INVALID')
        total_records = count
        _require(type(row['actions']) is list and len(row['actions']) <= 10000, 'SOURCE_ACTION_LIST_MISSING')
        for event in row['actions']:
            _fields(event, _ACTION_FIELDS, 'SOURCE_ACTION')
            identity = _text(event['action_id'], 'ACTION_ID', 180)
            _require(identity not in seen_actions, 'SOURCE_DUPLICATE_ACTION')
            seen_actions.add(identity)
            _require(event['security_id'] == source_security['source_security_id'], 'SOURCE_ACTION_SECURITY_MISMATCH')
            _require(event['action_type'] in ACTION_TYPES, 'SOURCE_ACTION_KIND_UNSUPPORTED')
            day = _day(event['effective_date'])
            _require(first <= day <= last, 'SOURCE_ACTION_OUTSIDE_DECLARED_COVERAGE')
            _ref(event['source_reference'])
            _require(type(event['details']) is dict, 'SOURCE_ACTION_DETAILS_REQUIRED')
            if binding['coverage_start'] <= day <= binding['coverage_end']:
                raise daily._Stop('SUPPLEMENT_CORPORATE_ACTION_IN_WINDOW:' + identity,
                                  details=dict(action=deepcopy(event)))
            outside.append(deepcopy(event))
    _require(total_records == len(seen_actions), 'SOURCE_RESULT_COUNT_INCOMPLETE')
    return dict(source_contract_id=reader.contract_id, evidence_type=EVIDENCE_TYPE,
                source_name=evidence['source_name'], source_reference=evidence['source_reference'],
                retrieved_at=evidence['retrieved_at'], source_authenticated=False,
                pages=retained, parsed_pages=decoded), outside


def _evaluate(original_artifacts, evidence, checked_at, source_reader):
    # The original object is never mutated; malformed identities are errors, not
    # a new opinion that can overwrite or repair the old check.
    artifacts = deepcopy(original_artifacts)
    original, calendar, days, fields, binding = _original(artifacts)
    now = _utc(checked_at)
    _require(_utc(original['retrieved_at']) <= now, 'CHECK_BEFORE_PRICE_RECEIPT')
    retained = {name: _retained(raw) for name, raw in artifacts.items()}
    core = dict(schema_version=SCHEMA, binding=binding, original_status=original['status'],
        original_stop_detail=deepcopy(original['stop_detail']), source_event_coverage='UNKNOWN',
        supplemental_coverage='UNKNOWN', status='BLOCKED', reason='SUPPLEMENT_NOT_CHECKED', can_save=False,
        evidence_kind='IMPORTED_UNVERIFIED', source_truth_verified=False, source_authenticated=False,
        times=dict(original_price_retrieved_at=original['retrieved_at'], supplemental_retrieved_at=None,
                   supplement_checked_at=checked_at), retained_originals=retained,
        evidence=deepcopy(evidence), source_projection=None,
        candidate_snapshot_id=None, candidate_csv_sha256=None, session_count=0,
        permissions=dict(network_requests=0, saved_inputs=0, economic_runs=0, orders=0),
        limitations=['来源原件和完整性声明仍未获独立认证。',
                     '补证形成新检查，原 Yahoo 事件覆盖仍未知，原停止记录不改变。',
                     '只支持无公司行为窗口；模块不自带真实来源解析器，来源接入及验收由调用服务负责。'])
    snapshot = None
    try:
        evidence = deepcopy(evidence)
        if type(evidence) is dict and evidence.get('retrieved_at') is not None:
            # Record the claimed receipt separately even if pagination later
            # fails. Validation does not turn this timestamp into authentication.
            _utc(evidence['retrieved_at'])
            core['times']['supplemental_retrieved_at'] = evidence['retrieved_at']
        source, outside = _evidence(evidence, binding, source_reader, now, _utc(days[-1]['close_utc']))
        core.update(supplemental_coverage='DECLARED_COMPLETE', source_projection=source,
                    outside_window_actions=outside)
        rows, excluded, meta, prefix = daily._price_rows(fields, days, binding['coverage_end'],
            _utc(original['retrieved_at']), original['query_start'], calendar)
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('session_date', *daily._FIELDS))
        writer.writerows((day, *(daily._price(v) for v in values[:4]), str(values[4]))
                         for day, values in sorted(rows.items()))
        csv_raw = stream.getvalue().encode('utf-8')
        proof = dict(schema_version='stock-action-supplement-lineage-v1', binding=binding,
                     source_event_coverage='UNKNOWN', supplemental_coverage='DECLARED_COMPLETE',
                     times=core['times'], retained_originals=retained, supplemental_source=source)
        first, last = binding['coverage_start'], binding['coverage_end']
        manifest = dict(schema_version='us-equity-daily-import-v1', security=binding['security'],
            identity=dict(stable_within_coverage=True, valid_from=first, valid_through=last,
                selection_basis='Exact retained security declaration; new supplement review, not authenticated history.',
                source=daily._source('Retained Yahoo security metadata; original receipt time in lineage',
                                     original['source_url'], artifacts['source-original.bin'], original['retrieved_at'])),
            calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=last, days=days,
                source=daily._source('Original retained exchange calendar', calendar['sources'][0],
                                     artifacts['calendar.json'], calendar['recorded_at'])),
            corporate_actions=dict(coverage_start=first, coverage_end=last, coverage_status='DECLARED_COMPLETE', actions=[],
                source=daily._source('Derived supplement coverage bundle; original source bytes and times retained, not authenticated',
                    'urn:hakimi:stock-action-supplement:' + digest(proof), daily._json(proof), checked_at)),
            price_source=daily._source('Derived retained Yahoo OHLCV CSV; new import time, original receipt retained in lineage',
                'urn:hakimi:retained-yahoo:' + original['raw_sha256'], csv_raw, checked_at),
            price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
            completed_bars_only=True, as_of=checked_at, retrieved_at=checked_at,
            bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
        snapshot = build_equity_snapshot(csv_raw, manifest).document
        _require(snapshot['research_admission']['allowed'], 'NEW_SNAPSHOT_NOT_ADMITTED')
        core.update(status='REVIEW_REQUIRED', reason='EXACT_SECURITY_CONFIRMATION_REQUIRED', can_save=True,
            candidate_snapshot_id=snapshot['snapshot_id'], candidate_csv_sha256=sha256(csv_raw).hexdigest(),
            session_count=len(rows), excluded_forming_sessions=excluded, excluded_pre_window_sessions=prefix,
            source_regular_market_time=meta['regularMarketTime'])
    except daily._Stop as error:
        snapshot = None
        core.update(status=error.status, reason=error.reason, stop_details=deepcopy(error.details))
    except (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError) as error:
        snapshot = None
        core.update(status='BLOCKED', reason='SUPPLEMENT_INVALID:' + type(error).__name__)
    return dict(core, check_hash=digest(core)), snapshot


def review_stock_supplement(original_artifacts, evidence, *, checked_at, source_reader=None):
    """Return a new content-bound review; no persistence or old-status transition."""
    return _evaluate(original_artifacts, evidence, checked_at, source_reader)[0]


def build_supplemented_snapshot(original_artifacts, evidence, *, checked_at, expected_check_hash,
                               confirmed_security, source_reader=None):
    """Recompute review and return an in-memory snapshot after exact confirmation.

    Future persistence must retain the check and use the existing current daily
    namespace. This function never saves, adopts, runs, or bypasses old checks.
    """
    checked, snapshot = _evaluate(original_artifacts, evidence, checked_at, source_reader)
    _require(checked['check_hash'] == expected_check_hash, 'CHECK_IDENTITY_CHANGED')
    _require(confirmed_security == checked['binding']['security'], 'EXACT_SECURITY_CONFIRMATION_REQUIRED')
    _require(checked['can_save'] and snapshot is not None, 'NOT_READY_FOR_SAVE')
    return dict(check=checked, snapshot=snapshot)
