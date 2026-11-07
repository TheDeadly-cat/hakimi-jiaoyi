"""Pure diagnostics over existing collector bytes, not a source/admission claim.

Input format is the retained started/response JSON written by
tools/collect_nvda_event_inputs.py and tools/collect_equity_event_inputs.py.
sdk_decoded_protocol_reply is an SDK-unpacked return, NOT original protobuf
wire bytes. Missing companyActFlag remains unavailable. This reader neither
imports the Futu SDK nor opens files, sockets, accounts or a research runner.
"""
import base64
from copy import deepcopy
from datetime import date, datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import math
import re
from zoneinfo import ZoneInfo

import pandas as pd

SCHEMA = 'futu-rehab-retained-diagnostic-v2'
KEYS = ('security_request', 'security_response', 'actions_request', 'actions_response')
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 1000
PERMISSIONS = {'network_allowed': False, 'canonical_admission_allowed': False,
               'economic_execution_allowed': False, 'paper_allowed': False,
               'live_allowed': False, 'order_allowed': False, 'automatic_retry': False}
FACTORS = ('forward_adj_factorA', 'forward_adj_factorB', 'backward_adj_factorA', 'backward_adj_factorB')
GROUPS = (
    ('SPLIT_FIELDS', ('split_base', 'split_ert', 'split_ratio')),
    ('REVERSE_SPLIT_FIELDS', ('join_base', 'join_ert', 'split_ratio')),
    ('CASH_DIVIDEND_FIELDS', ('per_cash_div',)),
    ('SPECIAL_DIVIDEND_FIELDS', ('special_dividend',)),
    ('STOCK_DIVIDEND_FIELDS', ('bonus_base', 'bonus_ert', 'per_share_div_ratio')),
    ('TRANSFER_FIELDS', ('transfer_base', 'transfer_ert', 'per_share_trans_ratio')),
    ('RIGHTS_FIELDS', ('allot_base', 'allot_ert', 'allotment_ratio', 'allotment_price')),
    ('ADDITIONAL_ISSUE_FIELDS', ('add_base', 'add_ert', 'stk_spo_ratio', 'stk_spo_price')),
    ('SPIN_OFF_FIELDS', ('spin_off_base', 'spin_off_ert', 'spin_off_ratio')),
)
KNOWN_FIELDS = {'ex_div_date', 'companyActFlag', *FACTORS, *(key for _, group in GROUPS for key in group)}
SDK_COLUMNS = {
    'security': ('code', 'name', 'lot_size', 'stock_type', 'stock_child_type', 'stock_owner',
        'option_type', 'strike_time', 'strike_price', 'suspension', 'listing_date', 'stock_id',
        'delisting', 'index_option_type', 'main_contract', 'last_trade_time', 'exchange_type'),
    'actions': ('ex_div_date', 'split_base', 'split_ert', 'join_base', 'join_ert', 'split_ratio',
        'per_cash_div', 'special_dividend', 'bonus_base', 'bonus_ert', 'per_share_div_ratio',
        'transfer_base', 'transfer_ert', 'per_share_trans_ratio', 'allot_base', 'allot_ert',
        'allotment_ratio', 'allotment_price', 'add_base', 'add_ert', 'stk_spo_ratio', 'stk_spo_price',
        'spin_off_base', 'spin_off_ert', 'spin_off_ratio', *FACTORS),
}


class RetainedEvidenceError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise RetainedEvidenceError(code)


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, 'DUPLICATE_JSON_FIELD')
        result[key] = value
    return result


def _parse(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'RETAINED_BYTES_REQUIRED_OR_TOO_LARGE')
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(RetainedEvidenceError('NONFINITE_JSON')))
    _require(type(value) is dict, 'RETAINED_JSON_OBJECT_REQUIRED')
    return value


def _time(value):
    _require(type(value) is str and len(value) <= 40, 'SOURCE_TIME_REQUIRED')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require(parsed.tzinfo is not None, 'SOURCE_TIMEZONE_REQUIRED')
    return parsed.astimezone(timezone.utc)


def _day(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None,
             'EFFECTIVE_DATE_REQUIRED')
    _require(date.fromisoformat(value).isoformat() == value, 'EFFECTIVE_DATE_INVALID')
    return value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _integer(value):
    return _number(value) and value > 0 and value <= 1000000 and float(value).is_integer()


def _fraction(value):
    return str(value.numerator) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'


def _request(document, method, label):
    _require(type(document.get('attempt')) is int and document['attempt'] == 1, 'SINGLE_RETAINED_ATTEMPT_REQUIRED')
    request = document.get('request')
    _require(type(request) is dict and set(request) == {'label', 'method', 'kwargs'}
             and request.get('method') == method and request.get('label') == label
             and type(request.get('kwargs')) is dict, 'REQUEST_METHOD_OR_LABEL_MISMATCH')
    return request, _time(document.get('started_at'))


def _reply(document, label, view):
    reply = document.get('returned_reply')
    _require(type(reply) is dict and set(reply) == {'ret', 'rows', 'error', 'page_req_key'},
             'RETURNED_REPLY_MISSING_OR_FIELDS_INVALID:' + label)
    view['returned_status'][label] = {key: deepcopy(reply[key]) for key in ('ret', 'error', 'page_req_key') if key in reply}
    unpacked = document.get('sdk_decoded_protocol_reply')
    _require(type(unpacked) is list and len(unpacked) == 3 and type(unpacked[0]) is int
             and type(unpacked[1]) is str, 'SDK_DECODED_REPLY_MISSING_OR_INVALID:' + label)
    view['sdk_unpacked_status'][label] = dict(status='RECORDED', ret=unpacked[0], message=unpacked[1])
    _require(type(reply['ret']) is int and unpacked[0] == reply['ret'], 'SDK_AND_RETURNED_STATUS_CONFLICT:' + label)
    _require(type(reply['ret']) is int and reply['ret'] == 0, 'PROVIDER_RETURNED_ERROR:' + label)
    _require(reply.get('error') is None, 'PROVIDER_STATUS_CONFLICT:' + label)
    _require(reply.get('page_req_key') is None, 'UNEXPECTED_REHAB_OR_SECURITY_PAGINATION:' + label)
    _require(type(reply.get('rows')) is list and len(reply['rows']) <= MAX_ROWS, 'SOURCE_ROWS_MISSING_OR_TOO_LARGE:' + label)
    _require(type(unpacked[2]) is list and len(unpacked[2]) <= MAX_ROWS, 'SDK_DECODED_ROWS_MISSING:' + label)
    view['row_comparison'][label] = _compare_rows(unpacked[2], reply['rows'], label)
    return reply['rows'], _time(document.get('completed_at'))


def _compare_rows(sdk_rows, returned_rows, label):
    """Check the actual collector transform, never just two success codes.

    The collector retains SDK rows before pandas fixed-column construction,
    then uses DataFrame.to_json(records, double_precision=15). Reproduce only
    this documented in-memory transform, including null columns/NaN markers.
    Unknown source fields may not disappear through fixed-column projection.
    """
    _require(all(type(row) is dict for row in sdk_rows + returned_rows), 'SOURCE_ROW_OBJECT_REQUIRED:' + label)
    original, returned = _json(sdk_rows), _json(returned_rows)
    if original == returned:
        method = 'EXACT_RETAINED_ROWS'
    else:
        columns = SDK_COLUMNS[label]
        _require(all(set(row) <= set(columns) for row in sdk_rows + returned_rows),
                 'SDK_TRANSFORM_UNKNOWN_FIELDS:' + label)
        restored = []
        for row in sdk_rows:
            values = {}
            for key, value in row.items():
                if type(value) is dict:
                    _require(set(value) == {'nonfinite_float'} and value['nonfinite_float'] in ('nan', 'inf', '-inf'),
                             'SDK_RETAINED_VALUE_INVALID:' + label)
                    values[key] = float(value['nonfinite_float'])
                else:
                    _require(value is None or type(value) in (str, int, float, bool), 'SDK_RETAINED_VALUE_INVALID:' + label)
                    values[key] = value
            restored.append(values)
        projected = json.loads(pd.DataFrame(restored, columns=columns).to_json(orient='records', double_precision=15))
        _require(_json(projected) == returned, 'SDK_AND_RETURNED_ROWS_CONFLICT:' + label)
        method = 'SDK_FIXED_COLUMNS_PANDAS_RECORDS_PRECISION_15'
    return dict(status='MATCHED', method=method, sdk_rows_sha256=sha256(original).hexdigest(),
                returned_rows_sha256=sha256(returned).hexdigest(), observed_rows=len(returned_rows),
                pandas_version=pd.__version__ if method != 'EXACT_RETAINED_ROWS' else None,
                source_authenticated=False)


def _event(row, index, first, last):
    _require(type(row) is dict, 'ACTION_ROW_OBJECT_REQUIRED')
    result = dict(record_index=index, source_fields=deepcopy(row), effective_date=None,
        inside_window=None, reported_field_groups=[], split_interpretations=[], issues=[],
        company_action_flags={'status': 'UNAVAILABLE', 'value': None, 'scope': 'RETURNED_SDK_ROW'},
        distribution_conditions='NOT_ESTABLISHED', accounting_eligible=False)
    try:
        day = _day(row.get('ex_div_date'))
        result.update(effective_date=day, inside_window=first <= day <= last)
        _require(not set(row) - KNOWN_FIELDS, 'UNRECOGNIZED_ACTION_FIELDS')
        _require(all(_number(row.get(key)) for key in FACTORS), 'ACTION_FACTORS_MISSING_OR_INVALID')
        if 'companyActFlag' in row:
            _require(type(row['companyActFlag']) is int and 0 <= row['companyActFlag'] < 2**63, 'COMPANY_ACTION_FLAG_INVALID')
            result['company_action_flags'] = dict(status='RECORDED', value=row['companyActFlag'],
                location='EXPLICIT_RETURNED_ROW_FIELD', interpretation='PRESERVED_NOT_INFERRED_OR_DECODED')
        for kind, group in GROUPS:
            trigger = group[:2] if kind in ('SPLIT_FIELDS', 'REVERSE_SPLIT_FIELDS') else group
            if not any(row.get(key) is not None for key in trigger):
                continue
            result['reported_field_groups'].append(kind)
            _require(all(_number(row.get(key)) for key in group), 'PARTIAL_OR_INVALID_ACTION_GROUP:' + kind)
            if kind in ('SPLIT_FIELDS', 'REVERSE_SPLIT_FIELDS'):
                base, ert = row[group[0]], row[group[1]]
                _require(_integer(base) and _integer(ert), 'SPLIT_RATIO_NOT_POSITIVE_INTEGERS')
                quantity = Fraction(int(ert), int(base))
                result['split_interpretations'].append(dict(
                    fields=group[:2], original_base=base, original_ert=ert,
                    new_shares_per_old_share=_fraction(quantity),
                    unit_cost_multiplier=_fraction(1 / quantity),
                    derivation=group[1] + ' / ' + group[0], source_split_ratio=row['split_ratio'],
                    kind='FORWARD_SPLIT' if quantity > 1 else 'REVERSE_SPLIT' if quantity < 1 else 'UNCHANGED_RATIO',
                    accounting_applied=False))
                _require(math.isclose(row['split_ratio'], int(base) / int(ert), rel_tol=1e-12, abs_tol=0),
                         'SOURCE_DISPLAY_RATIO_CONFLICT')
        _require(bool(result['reported_field_groups']), 'NO_RECOGNIZED_ACTION_FIELDS')
        _require(len(result['split_interpretations']) <= 1, 'SIMULTANEOUS_SPLIT_AND_JOIN_FIELDS')
    except (RetainedEvidenceError, ValueError, TypeError, OverflowError) as error:
        result['issues'].append(str(error))
    return result


def read_retained_rehab(artifacts, *, window_start, window_end):
    """Inspect four original collector byte strings. Never grant admission.

    The request binds action rows to their actual code; no code/currency/flag,
    source coverage range, page count, total or COMPLETE value is fabricated.
    A successful empty returned list is observed zero rows, not coverage proof.
    """
    view = dict(schema_version=SCHEMA, status='INCOMPLETE',
        window={'start': window_start, 'end': window_end, 'basis': 'CALLER_FIXED_EFFECTIVE_DATE_WINDOW'},
        security=None, returned_status={}, sdk_unpacked_status={key: {'status': 'UNAVAILABLE'} for key in ('security', 'actions')},
        row_comparison={}, source_asof='UNKNOWN',
        collector_identity=dict(format='UNRECOGNIZED_OR_INCOMPLETE', sdk_version='UNKNOWN',
                                capture_batch='UNKNOWN', authenticated=False),
        requests={}, source_times={}, events=[], issues=[],
        paging={'status': 'NOT_APPLICABLE_TO_PROTOCOL', 'provider_total': 'UNAVAILABLE',
                'observed_record_count': None},
        coverage={'provider_claim': 'UNAVAILABLE', 'source_event_coverage': 'UNKNOWN',
                  'no_reported_action_in_window': None, 'independent_completeness_verified': False},
        source_format='COLLECTOR_RETAINED_SDK_UNPACKED_REPLY_NOT_PROTOBUF_WIRE',
        retained_artifacts={}, source_authenticated=False, canonical_admission=False,
        permissions=deepcopy(PERMISSIONS), new_economic_runs=0, provider_calls=0,
        limitations=['只说明本次保存的供应商响应中报告了什么，不证明全部公司行为完整。',
                     '缺少公司行为标志、币种或来源覆盖范围时保持未记录，不补零或补 COMPLETE。',
                     '拆合股比例仅作原字段解释，不调整旧行情、持仓、现金或研究结果。'])
    try:
        _require(type(artifacts) is dict and set(artifacts) == set(KEYS), 'EXACT_FOUR_COLLECTOR_ARTIFACTS_REQUIRED')
        _require(all(type(raw) is bytes for raw in artifacts.values()) and sum(len(raw) for raw in artifacts.values()) <= 8 * 1024 * 1024,
                 'RETAINED_TOTAL_BYTES_INVALID')
        for key, raw in artifacts.items():
            _require(0 < len(raw) <= MAX_BYTES, 'RETAINED_BYTES_REQUIRED_OR_TOO_LARGE')
            view['retained_artifacts'][key] = dict(sha256=sha256(raw).hexdigest(), byte_count=len(raw),
                                                   raw_base64=base64.b64encode(raw).decode('ascii'))
        docs = {key: _parse(raw) for key, raw in artifacts.items()}
        for label in ('security', 'actions'):
            returned = docs[label + '_response'].get('returned_reply')
            if type(returned) is dict:
                view['returned_status'][label] = {key: deepcopy(returned[key]) for key in ('ret', 'error', 'page_req_key') if key in returned}
        first, last = _day(window_start), _day(window_end)
        _require(first <= last and (date.fromisoformat(last) - date.fromisoformat(first)).days <= 366,
                 'BOUNDED_FIXED_WINDOW_REQUIRED')
        security_request, security_start = _request(docs['security_request'], 'get_stock_basicinfo', 'security')
        action_request, action_start = _request(docs['actions_request'], 'get_rehab', 'actions')
        view['requests'] = dict(security=deepcopy(security_request), actions=deepcopy(action_request))
        kwargs = action_request['kwargs']
        _require(set(kwargs) == {'code'} and type(kwargs['code']) is str
                 and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,19}', kwargs['code']) is not None, 'EXPLICIT_US_SECURITY_CODE_REQUIRED')
        code = kwargs['code']
        _require(security_request['kwargs'] == dict(market='US', stock_type='STOCK', code_list=[code]),
                 'SECURITY_REQUEST_BINDING_MISMATCH')
        securities, security_end = _reply(docs['security_response'], 'security', view)
        rows, action_end = _reply(docs['actions_response'], 'actions', view)
        view['collector_identity']['format'] = 'RECOGNIZED_COLLECTOR_FORMAT'
        view['source_times'] = dict(security_started_at=docs['security_request']['started_at'],
            security_completed_at=docs['security_response']['completed_at'],
            actions_started_at=docs['actions_request']['started_at'], actions_completed_at=docs['actions_response']['completed_at'])
        _require(security_start <= security_end <= action_start <= action_end, 'SOURCE_CLOCK_ORDER_INVALID')
        _require(date.fromisoformat(last) <= action_end.astimezone(ZoneInfo('America/New_York')).date(),
                 'WINDOW_AFTER_RETAINED_RESPONSE')
        _require(len(securities) == 1 and type(securities[0]) is dict, 'ONE_RETAINED_SECURITY_REQUIRED')
        security = securities[0]
        _require(security.get('code') == code and security.get('stock_type') == 'STOCK'
                 and security.get('exchange_type') in {'US_NASDAQ', 'US_NYSE'}
                 and type(security.get('stock_id')) is int and security['stock_id'] > 0
                 and _number(security.get('lot_size')) and security['lot_size'] == 1
                 and security.get('delisting') is False, 'RETAINED_SECURITY_IDENTITY_MISMATCH')
        currency = security.get('currency')
        view['security'] = dict(code=code, stock_id=security['stock_id'], exchange_type=security['exchange_type'],
            stock_type=security['stock_type'], source_fields=deepcopy(security),
            currency=currency if type(currency) is str and re.fullmatch(r'[A-Z]{3}', currency) else None,
            binding_status='MATCHED_RETAINED_SINGLE_SECURITY_REQUEST_NOT_EXTERNAL_AUTHENTICATION')
        view['paging']['observed_record_count'] = len(rows)
        fingerprints = set()
        for index, row in enumerate(rows):
            event = _event(row, index, first, last)
            fingerprint = sha256(_json(row)).hexdigest()
            if fingerprint in fingerprints:
                event['issues'].append('DUPLICATE_REPORTED_ACTION_ROW')
            fingerprints.add(fingerprint)
            view['events'].append(event)
            view['issues'].extend(f'ROW_{index}:' + issue for issue in event['issues'])
        present = any(event['inside_window'] is True for event in view['events'])
        if not view['issues']:
            view['status'] = 'ACTION_PRESENT' if present else 'NO_REPORTED_ACTION_IN_WINDOW'
            view['coverage']['no_reported_action_in_window'] = not present
        view['reported_in_window_count'] = sum(event['inside_window'] is True for event in view['events'])
    except (RetainedEvidenceError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        view['issues'].append(str(error))
    view['display'] = {
        'NO_REPORTED_ACTION_IN_WINDOW': '保存的 Futu 响应在此窗口未报告公司行为；完整性仍未知。',
        'ACTION_PRESENT': '保存的 Futu 响应报告了窗口内公司行为；尚未执行核算。',
        'INCOMPLETE': '保留证据不完整或相互矛盾，不能据此判断该窗口。',
    }[view['status']]
    return {**view, 'diagnostic_hash': sha256(_json(view)).hexdigest()}
