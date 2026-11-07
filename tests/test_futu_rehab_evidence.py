"""Synthetic collector-format fixtures; no real provider acceptance or calls."""
import ast
import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from hakimi_research import futu_rehab_evidence as reader


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def fixture(rows=None):
    security = dict(code='US.QATEST', name='Fictional QA security', stock_type='STOCK', exchange_type='US_NASDAQ',
                    lot_size=1, delisting=False, stock_id=123456)
    def request(label, method, kwargs, at):
        return dict(request=dict(label=label, method=method, kwargs=kwargs), started_at=at, attempt=1,
                    fixture_notice='SYNTHETIC_CONTRACT_FIXTURE_NOT_MARKET_DATA')
    def response(rows, at):
        return dict(completed_at=at, sdk_decoded_protocol_reply=[0, '', deepcopy(rows)],
                    returned_reply=dict(ret=0, rows=rows, error=None, page_req_key=None),
                    fixture_notice='SYNTHETIC_CONTRACT_FIXTURE_NOT_MARKET_DATA')
    return dict(security_request=encoded(request('security', 'get_stock_basicinfo',
        dict(market='US', stock_type='STOCK', code_list=['US.QATEST']), '2026-09-30T12:00:00Z')),
        security_response=encoded(response([security], '2026-09-30T12:00:01Z')),
        actions_request=encoded(request('actions', 'get_rehab', dict(code='US.QATEST'), '2026-09-30T12:00:02Z')),
        actions_response=encoded(response(deepcopy(rows or []), '2026-09-30T12:00:03Z')))


def split(day='2023-05-24', **updates):
    return dict(ex_div_date=day, split_base=1.0, split_ert=5.0, split_ratio=.2,
        join_base=None, join_ert=None, per_cash_div=None, special_dividend=None,
        forward_adj_factorA=.2, forward_adj_factorB=0.0, backward_adj_factorA=5.0, backward_adj_factorB=0.0, **updates)


class FutuRehabRetainedReaderTests(unittest.TestCase):
    def read(self, artifacts=None, **options):
        return reader.read_retained_rehab(artifacts or fixture(), window_start=options.get('start', '2023-05-22'),
                                         window_end=options.get('end', '2023-06-01'))

    def edit(self, source, key, change):
        value = deepcopy(source)
        doc = json.loads(value[key]); change(doc); value[key] = encoded(doc)
        return value

    def test_success_empty_rows_are_observed_zero_not_a_complete_source_claim(self):
        source = fixture(); before = deepcopy(source)
        result = self.read(source)
        self.assertEqual(result['status'], 'NO_REPORTED_ACTION_IN_WINDOW')
        self.assertEqual(result['paging'], dict(status='NOT_APPLICABLE_TO_PROTOCOL', provider_total='UNAVAILABLE', observed_record_count=0))
        self.assertEqual(result['coverage']['provider_claim'], 'UNAVAILABLE')
        self.assertEqual(result['coverage']['source_event_coverage'], 'UNKNOWN')
        self.assertFalse(result['coverage']['independent_completeness_verified'])
        self.assertIsNone(result['security']['currency'])
        self.assertEqual(source, before)
        self.assertFalse(result['canonical_admission'])
        self.assertTrue(all(value is False for value in result['permissions'].values()))
        self.assertEqual(result['provider_calls'], 0)

    def test_original_bytes_status_and_fields_are_exactly_retained(self):
        source = fixture([split()]); result = self.read(source)
        for key, raw in source.items():
            retained = result['retained_artifacts'][key]
            self.assertEqual(base64.b64decode(retained['raw_base64']), raw)
            self.assertEqual(retained['sha256'], sha256(raw).hexdigest())
            self.assertEqual(retained['byte_count'], len(raw))
        self.assertEqual(result['returned_status']['actions']['ret'], 0)
        self.assertEqual(result['sdk_unpacked_status']['actions'], {'status': 'RECORDED', 'ret': 0, 'message': ''})
        self.assertEqual(result['events'][0]['source_fields'], split())
        self.assertEqual(result['source_times']['actions_completed_at'], '2026-09-30T12:00:03Z')
        self.assertEqual(result['diagnostic_hash'], self.read(source)['diagnostic_hash'])

    def test_futu_forward_and_reverse_ratio_direction_without_accounting(self):
        forward = self.read(fixture([split()]))
        self.assertEqual(forward['status'], 'ACTION_PRESENT')
        interpretation = forward['events'][0]['split_interpretations'][0]
        self.assertEqual(interpretation['new_shares_per_old_share'], '5')
        self.assertEqual(interpretation['unit_cost_multiplier'], '1/5')
        self.assertEqual(interpretation['derivation'], 'split_ert / split_base')
        reverse = split(); reverse.update(split_base=None, split_ert=None, join_base=50.0, join_ert=1.0, split_ratio=50.0)
        result = self.read(fixture([reverse])); interpretation = result['events'][0]['split_interpretations'][0]
        self.assertEqual(interpretation['new_shares_per_old_share'], '1/50')
        self.assertEqual(interpretation['unit_cost_multiplier'], '50')
        self.assertFalse(result['events'][0]['accounting_eligible'])
        self.assertEqual(result['events'][0]['distribution_conditions'], 'NOT_ESTABLISHED')
        self.assertFalse(interpretation['accounting_applied'])

    def test_flag_absence_is_not_manufactured_from_nonnull_columns(self):
        missing = self.read(fixture([split()]))['events'][0]
        self.assertEqual(missing['company_action_flags'], dict(status='UNAVAILABLE', value=None, scope='RETURNED_SDK_ROW'))
        recorded = self.read(fixture([split(companyActFlag=129)]))['events'][0]
        self.assertEqual(recorded['company_action_flags']['value'], 129)
        self.assertEqual(recorded['source_fields']['companyActFlag'], 129)
        self.assertEqual(recorded['company_action_flags']['interpretation'], 'PRESERVED_NOT_INFERRED_OR_DECODED')

    def test_actions_outside_the_fixed_window_are_retained_not_removed(self):
        row = split('2024-06-10'); result = self.read(fixture([row]))
        self.assertEqual(result['status'], 'NO_REPORTED_ACTION_IN_WINDOW')
        self.assertEqual(result['paging']['observed_record_count'], 1)
        self.assertEqual(result['events'][0]['source_fields'], row)
        self.assertFalse(result['events'][0]['inside_window'])

    def test_missing_rows_cannot_be_replaced_by_checkbox_or_complete_field(self):
        source = self.edit(fixture(), 'actions_response', lambda d: d['returned_reply'].pop('rows'))
        result = self.read(source)
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertIsNone(result['coverage']['no_reported_action_in_window'])
        source = self.edit(source, 'actions_response', lambda d: d.update(complete=True, total_records=0, coverage_status='COMPLETE'))
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')

    def test_request_code_stock_id_exchange_and_single_security_are_bound(self):
        modifications = [
            ('actions_request', lambda d: d['request']['kwargs'].update(code='US.OTHER')),
            ('security_request', lambda d: d['request']['kwargs'].update(code_list=['US.QATEST', 'US.OTHER'])),
            ('security_response', lambda d: d['returned_reply']['rows'][0].update(code='US.OTHER')),
            ('security_response', lambda d: d['returned_reply']['rows'][0].update(stock_id=True)),
            ('security_response', lambda d: d['returned_reply']['rows'][0].update(exchange_type='HK_MAINBOARD')),
            ('security_response', lambda d: d['returned_reply']['rows'][0].update(stock_type='ETF')),
            ('actions_request', lambda d: d['request'].update(method='place_order')),
        ]
        for key, mutate in modifications:
            with self.subTest(key=key):
                result = self.read(self.edit(fixture(), key, mutate))
                self.assertEqual(result['status'], 'INCOMPLETE')
                self.assertFalse(result['canonical_admission'])

    def test_failed_status_clock_and_unexpected_pagination_remain_incomplete(self):
        modifications = [
            ('actions_response', lambda d: d['returned_reply'].update(ret=-1, error='FICTIONAL_SOURCE_ERROR')),
            ('actions_response', lambda d: d['returned_reply'].update(ret=False)),
            ('actions_response', lambda d: d['returned_reply'].update(page_req_key='unexpected-page')),
            ('actions_response', lambda d: d.update(completed_at='2026-09-30T11:59:00Z')),
            ('actions_request', lambda d: d.update(started_at='2026-09-30T12:00:02')),
            ('actions_request', lambda d: d.update(attempt=2)),
            ('actions_response', lambda d: d.update(sdk_decoded_protocol_reply=[-1,'contradiction',[]])),
        ]
        for key, mutate in modifications:
            with self.subTest(key=key):
                self.assertEqual(self.read(self.edit(fixture(), key, mutate))['status'], 'INCOMPLETE')

    def test_malformed_partial_unknown_and_duplicate_event_rows_do_not_get_negative_conclusion(self):
        rows = []
        bad = split(); bad.pop('split_ert'); rows.append([bad])
        bad = split(); bad['ex_div_date'] = '2023-02-30'; rows.append([bad])
        bad = split(); bad['mystery_distribution'] = 1; rows.append([bad])
        bad = split(); bad['split_ratio'] = 5; rows.append([bad])
        bad = split(); bad['split_ert'] = 2.5; rows.append([bad])
        bad = split(); bad['companyActFlag'] = True; rows.append([bad])
        rows.append([split(), split()])
        rows.append(['not-a-row'])
        for values in rows:
            with self.subTest(values=values):
                result = self.read(fixture(values))
                self.assertEqual(result['status'], 'INCOMPLETE')
                self.assertIsNone(result['coverage']['no_reported_action_in_window'])

    def test_nonterminating_display_ratio_does_not_change_exact_integer_quantity_ratio(self):
        row = split(); row.update(split_base=3.0, split_ert=1.0, split_ratio=3.0)
        result = self.read(fixture([row]))
        self.assertEqual(result['events'][0]['split_interpretations'][0]['new_shares_per_old_share'], '1/3')
        row.update(split_base=1.0, split_ert=3.0, split_ratio=0.333333333333333)
        result = self.read(fixture([row]))
        self.assertEqual(result['status'], 'ACTION_PRESENT')
        self.assertEqual(result['events'][0]['split_interpretations'][0]['new_shares_per_old_share'], '3')

    def test_finite_json_byte_identity_and_window_boundaries(self):
        source = fixture(); source['actions_response'] = b'{"a":1,"a":2}'
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')
        source['actions_response'] = b'{"x":NaN}'
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')
        self.assertEqual(self.read(start='2023-06-02', end='2023-06-01')['status'], 'INCOMPLETE')
        self.assertEqual(self.read(start='2027-05-22', end='2027-06-01')['status'], 'INCOMPLETE')
        self.assertEqual(self.read(start='2020-01-01', end='2023-06-01')['status'], 'INCOMPLETE')
        source = fixture(); source['actions_response'] = 'a file path is not accepted'
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')

    def test_no_external_or_filesystem_execution_dependency(self):
        tree = ast.parse(Path(reader.__file__).read_text(encoding='utf-8'))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names}
        self.assertFalse(imports & {'futu','socket','requests','urllib','subprocess','pathlib','os'})
        with patch('socket.socket.connect', side_effect=AssertionError('no external calls')):
            result = self.read(fixture([split()]))
        self.assertEqual(result['new_economic_runs'], 0)

    def test_sdk_decoded_rows_are_required_and_conflicts_cannot_hide_behind_success(self):
        for label in ('security', 'actions'):
            for change in (lambda doc: doc.pop('sdk_decoded_protocol_reply'),
                           lambda doc: doc.update(sdk_decoded_protocol_reply=None),
                           lambda doc: doc['sdk_decoded_protocol_reply'].__setitem__(2, None)):
                result = self.read(self.edit(fixture(), label + '_response', change))
                self.assertEqual(result['status'], 'INCOMPLETE')
        source = self.edit(fixture([split()]), 'actions_response',
                           lambda doc: doc['sdk_decoded_protocol_reply'][2][0].update(split_ert=7.0))
        result = self.read(source)
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertTrue(any('ROWS_CONFLICT' in item for item in result['issues']))
        source = self.edit(fixture(), 'security_response',
                           lambda doc: doc['sdk_decoded_protocol_reply'][2][0].update(stock_id=98765))
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')

    def test_real_collector_dataframe_null_columns_and_decimal_format_are_reproduced(self):
        # Source SDK is never imported. This is the actual collector's pandas
        # transform applied to explicitly fictional protocol-shaped rows.
        row = split(); row.update(split_ert=3.0, split_ratio=1 / 3)
        source = fixture([row])
        for label in ('security', 'actions'):
            doc = json.loads(source[label + '_response'])
            raw_rows = doc['sdk_decoded_protocol_reply'][2]
            projected = json.loads(reader.pd.DataFrame(raw_rows, columns=reader.SDK_COLUMNS[label]).to_json(
                orient='records', double_precision=15))
            doc['returned_reply']['rows'] = projected
            source[label + '_response'] = encoded(doc)
        result = self.read(source)
        self.assertEqual(result['status'], 'ACTION_PRESENT')
        self.assertEqual(result['row_comparison']['actions']['method'], 'SDK_FIXED_COLUMNS_PANDAS_RECORDS_PRECISION_15')
        self.assertNotEqual(result['row_comparison']['actions']['sdk_rows_sha256'],
                            result['row_comparison']['actions']['returned_rows_sha256'])
        self.assertEqual(result['collector_identity']['sdk_version'], 'UNKNOWN')
        self.assertEqual(result['collector_identity']['capture_batch'], 'UNKNOWN')
        self.assertEqual(result['source_asof'], 'UNKNOWN')

    def test_collector_nonfinite_markers_become_null_only_via_known_transform(self):
        source = fixture()
        doc = json.loads(source['security_response'])
        sdk_rows = doc['sdk_decoded_protocol_reply'][2]
        sdk_rows[0]['strike_price'] = {'nonfinite_float': 'nan'}
        transformed = deepcopy(sdk_rows); transformed[0]['strike_price'] = float('nan')
        doc['returned_reply']['rows'] = json.loads(reader.pd.DataFrame(transformed,
            columns=reader.SDK_COLUMNS['security']).to_json(orient='records', double_precision=15))
        source['security_response'] = encoded(doc)
        self.assertEqual(self.read(source)['status'], 'NO_REPORTED_ACTION_IN_WINDOW')
        doc['sdk_decoded_protocol_reply'][2][0]['unknown_nonnull_field'] = 'must not disappear'
        source['security_response'] = encoded(doc)
        self.assertEqual(self.read(source)['status'], 'INCOMPLETE')

    def test_row_counts_presence_order_and_boolean_are_exact(self):
        for change in (lambda doc: doc['sdk_decoded_protocol_reply'][2].append(split()),
                       lambda doc: doc['sdk_decoded_protocol_reply'][2][0].update(split_base=True),
                       lambda doc: doc['sdk_decoded_protocol_reply'][2][0].pop('split_base')):
            source = self.edit(fixture([split()]), 'actions_response', change)
            self.assertEqual(self.read(source)['status'], 'INCOMPLETE')
        for field in ('error', 'page_req_key'):
            source = self.edit(fixture(), 'actions_response', lambda doc: doc['returned_reply'].pop(field))
            self.assertEqual(self.read(source)['status'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
