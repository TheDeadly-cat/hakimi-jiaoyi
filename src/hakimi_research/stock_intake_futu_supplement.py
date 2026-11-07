"""Pure v2 fixed-window importer declaration over retained Yahoo/Futu bytes.

The provider's coverage and source as-of remain UNKNOWN. Only this explicit
import policy declares an action-free modelling window for descriptive,
IMPORTED_UNVERIFIED research. No source is authenticated and no old check is
upgraded. Review exposes a candidate identity, not a snapshot or persistence.
"""
from copy import deepcopy
import csv
from hashlib import sha256
import io

from . import daily_updates as daily
from . import stock_intake_supplement as original
from .documents import canonical_bytes, digest
from .equity_dataset import build_equity_snapshot
from .futu_rehab_evidence import read_retained_rehab


SCHEMA = 'workbench-stock-futu-supplement-v2'
POLICY_ID = 'FUTU_REPORTED_ACTIONS_FIXED_WINDOW_IMPORT_V2'
LINEAGE_SCHEMA = 'stock-futu-limited-import-lineage-v2'
PERMISSIONS = dict(network_allowed=False, automatic_retry=False, external_execution_allowed=False,
                   paper_allowed=False, live_allowed=False, order_allowed=False)
EXCHANGES = {'US_NASDAQ': 'XNAS', 'US_NYSE': 'XNYS'}


def _require(condition, reason, **details):
    daily._require(condition, 'FUTU_SUPPLEMENT_' + reason, details=details)


def _evaluate(original_artifacts, artifacts, checked_at):
    # Integrity failure of the original evidence remains an error, as in v1.
    retained_prices = deepcopy(original_artifacts)
    prior, calendar, days, fields, binding = original._original(retained_prices)
    now = original._utc(checked_at)
    price_at = original._utc(prior['retrieved_at'])
    _require(price_at <= now, 'CHECK_BEFORE_PRICE_RECEIPT')
    diagnostic = read_retained_rehab(deepcopy(artifacts), window_start=binding['coverage_start'],
                                    window_end=binding['coverage_end'])
    times = dict(original_price_retrieved_at=prior['retrieved_at'],
                 supplemental_source_times=deepcopy(diagnostic['source_times']),
                 supplemental_retrieved_at=diagnostic['source_times'].get('actions_completed_at'),
                 supplement_checked_at=checked_at, source_asof='UNKNOWN')
    core = dict(schema_version=SCHEMA, policy_id=POLICY_ID, binding=binding,
        original_status=prior['status'], original_stop_detail=deepcopy(prior['stop_detail']),
        status='BLOCKED', can_save=False, reason='FUTU_SUPPLEMENT_NOT_REVIEWED',
        reader_diagnostic=diagnostic, times=times, source_event_coverage='UNKNOWN', source_asof='UNKNOWN',
        supplemental_coverage='UNKNOWN', importer_declaration=None, source_authenticated=False,
        source_truth_verified=False, evidence_kind='IMPORTED_UNVERIFIED',
        research_scope='DESCRIPTIVE_ACTION_FREE_FIXED_WINDOW_ONLY',
        retained_originals={name: original._retained(raw) for name, raw in retained_prices.items()},
        candidate_snapshot_id=None, candidate_csv_sha256=None, session_count=0,
        permissions=deepcopy(PERMISSIONS), network_requests=0, saved_inputs=0, economic_runs=0, orders=0,
        limitations=['来源截止和全部公司行为覆盖仍未知，原件与哈希不构成来源认证。',
            '只有完整响应在固定窗口内未报告事件时才可形成导入建模声明，这不构成供应商完整性保证。',
            '币种仅采用原 Yahoo 证券字段；Futu 未提供时保持未知。',
            '仅供所保存资料的描述性研究，不证明实时可交易、无数据遗漏或策略有效性。',
            '新检查与输入独立保存，原缺 events 的停止记录不改变。'])
    snapshot = None
    try:
        _require(diagnostic['status'] != 'INCOMPLETE', 'RETAINED_EVIDENCE_INCOMPLETE', issues=diagnostic['issues'])
        _require(diagnostic['status'] == 'NO_REPORTED_ACTION_IN_WINDOW', 'ACTION_IN_FIXED_WINDOW')
        security = diagnostic['security']
        _require(security['code'] == 'US.' + binding['security']['symbol']
                 and EXCHANGES.get(security['exchange_type']) == binding['security']['exchange']
                 and security['stock_type'] == 'STOCK', 'EXACT_SECURITY_MISMATCH')
        declared_currency = security['source_fields'].get('currency')
        _require(declared_currency is None or declared_currency == binding['security']['currency'],
                 'EXPLICIT_SOURCE_CURRENCY_CONFLICT')
        source_times = diagnostic['source_times']
        instants = {name: original._utc(value) for name, value in source_times.items()}
        _require(len(instants) == 4 and all(value <= now for value in instants.values()), 'SOURCE_RECEIVED_AFTER_CHECK')
        last_close = original._utc(days[-1]['close_utc'])
        _require(last_close <= instants['actions_started_at']
                 and max(last_close, price_at) <= instants['actions_completed_at'], 'SOURCE_BEFORE_FIXED_WINDOW_OR_PRICES')
        # Current/forming-session actions can already change a historical quote
        # basis. Their being outside the completed window is not sufficient.
        price_horizon = price_at.astimezone(daily._NY).date().isoformat()
        impacting = [row for row in diagnostic['events']
                     if binding['coverage_end'] < row['effective_date'] <= price_horizon]
        _require(not impacting, 'POST_WINDOW_ACTION_MAY_AFFECT_PRICE_BASIS',
                 events=[dict(record_index=row['record_index'], effective_date=row['effective_date']) for row in impacting])
        rows, excluded, meta, prefix = daily._price_rows(fields, days, binding['coverage_end'],
            price_at, prior['query_start'], calendar)
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('session_date', *daily._FIELDS))
        writer.writerows((day, *(daily._price(value) for value in values[:4]), str(values[4]))
                         for day, values in sorted(rows.items()))
        csv_raw = stream.getvalue().encode('utf-8')
        declaration = dict(policy_id=POLICY_ID, declarant='IMPORT_PROCESS_WITH_EXPLICIT_USER_CONFIRMATION',
            coverage_start=binding['coverage_start'], coverage_end=binding['coverage_end'],
            modelling_scope='ACTION_FREE_FIXED_WINDOW_ONLY',
            basis='NO_REPORTED_ACTION_IN_RETAINED_FUTU_RESPONSE',
            source_claim_complete=False, source_event_coverage='UNKNOWN', source_asof='UNKNOWN',
            diagnostic_hash=diagnostic['diagnostic_hash'], explicit_user_confirmation_required=True,
            currency_source='ORIGINAL_YAHOO_META_CURRENCY', futu_currency=security['currency'],
            statement='The import process declares this fixed modelling window from retained observations; neither provider nor reader certifies complete corporate-action coverage.')
        core.update(importer_declaration=declaration, supplemental_coverage='IMPORT_POLICY_DECLARED_FIXED_WINDOW')
        proof = dict(schema_version=LINEAGE_SCHEMA, policy_id=POLICY_ID, binding=binding,
            source_event_coverage='UNKNOWN', source_asof='UNKNOWN', source_authenticated=False,
            times=times, retained_originals=core['retained_originals'], reader_diagnostic=diagnostic,
            importer_declaration=declaration, evidence_kind='IMPORTED_UNVERIFIED',
            research_scope=core['research_scope'], permissions=deepcopy(PERMISSIONS))
        first, last = binding['coverage_start'], binding['coverage_end']
        at = daily._stamp(now)
        manifest = dict(schema_version='us-equity-daily-import-v1', security=binding['security'],
            identity=dict(stable_within_coverage=True, valid_from=first, valid_through=last,
                selection_basis='Exact retained Yahoo identity and matching Futu single-security metadata; bounded importer declaration, not authenticated historical identity.',
                source=daily._source('Original Yahoo security metadata; Futu matching fields retained in policy lineage',
                    prior['source_url'], retained_prices['source-original.bin'], daily._stamp(price_at))),
            calendar=dict(timezone='America/New_York', coverage_start=first, coverage_end=last, days=days,
                source=daily._source('Original retained exchange calendar', calendar['sources'][0],
                    retained_prices['calendar.json'], calendar['recorded_at'])),
            corporate_actions=dict(coverage_start=first, coverage_end=last, coverage_status='DECLARED_COMPLETE', actions=[],
                source=daily._source('V2 IMPORT POLICY declaration only: retained Futu response reports no action in this fixed window; provider completeness UNKNOWN',
                    # Derived lineage has one explicit byte representation.
                    # Original capture bytes remain untouched inside it; input
                    # mapping insertion order must not create another input.
                    'urn:hakimi:futu-fixed-window-import-v2:' + digest(proof), canonical_bytes(proof), at)),
            price_source=daily._source('Derived retained Yahoo OHLCV CSV; raw source and original receipt time retained in v2 lineage',
                'urn:hakimi:retained-yahoo:' + prior['raw_sha256'], csv_raw, at),
            price_basis='RAW_UNADJUSTED', volume_unit='shares', bar_timestamp_semantics='SESSION_DATE',
            completed_bars_only=True, as_of=at, retrieved_at=at,
            bar_availability_lag_seconds=60, evidence_kind='IMPORTED_UNVERIFIED')
        snapshot = build_equity_snapshot(csv_raw, manifest).document
        _require(snapshot['research_admission']['allowed'], 'NEW_SNAPSHOT_NOT_ADMITTED')
        core.update(status='REVIEW_REQUIRED', can_save=True, reason='EXACT_SECURITY_AND_SOURCE_LIMITS_CONFIRMATION_REQUIRED',
            candidate_snapshot_id=snapshot['snapshot_id'], candidate_csv_sha256=sha256(csv_raw).hexdigest(),
            session_count=len(rows), excluded_forming_sessions=excluded, excluded_pre_window_sessions=prefix,
            source_regular_market_time=meta['regularMarketTime'])
    except daily._Stop as error:
        snapshot = None
        core.update(status=error.status, reason=error.reason, stop_details=deepcopy(error.details))
    except (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError) as error:
        snapshot = None
        core.update(status='BLOCKED', reason='FUTU_SUPPLEMENT_INVALID:' + type(error).__name__)
    return dict(core, check_hash=digest(core)), snapshot


def review_futu_supplement(original_artifacts, artifacts, *, checked_at):
    """New content-bound check rebuilt from bytes; never edits the old check."""
    return _evaluate(original_artifacts, artifacts, checked_at)[0]


def build_futu_supplement(original_artifacts, artifacts, *, checked_at, expected_check_hash,
                          confirmed_security, acknowledge_source_limits):
    """Pure explicit confirmation: rebuild the original review and return bytes' projection.

    The calling service records its own user request/receipt; no missing user
    name, SDK version, source timestamp or collection batch is invented here.
    """
    checked, snapshot = _evaluate(original_artifacts, artifacts, checked_at)
    _require(checked['check_hash'] == expected_check_hash, 'CHECK_IDENTITY_CHANGED')
    _require(type(confirmed_security) is dict and confirmed_security == checked['binding']['security'],
             'EXACT_SECURITY_CONFIRMATION_REQUIRED')
    _require(acknowledge_source_limits is True, 'SOURCE_LIMITS_ACKNOWLEDGEMENT_REQUIRED')
    _require(checked['can_save'] and snapshot is not None, 'NOT_READY_FOR_SAVE')
    return dict(check=checked, snapshot=snapshot)
