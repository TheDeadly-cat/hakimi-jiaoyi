"""Synthetic execution and authorization checks; never load actual Futu prices."""
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from test_equity_research import stock_inputs
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_dataset import build_equity_snapshot
from scripts.reconcile_research_ledger import reconcile
from tools.equity_content_protocol import price_confirmation
from tools import nvda_economic_study as study


def fixture(*, numeric=True, price=True, loss=False):
    raw, manifest = stock_inputs()
    lines = raw.decode().splitlines()
    if not price:
        fields = lines[2].split(','); fields[4] = '101'; lines[2] = ','.join(fields)
    if loss:
        lines[3] = '2024-11-05,102,104,90,95,10000'
    raw = ('\n'.join(lines) + '\n').encode()
    import base64
    manifest['price_source']['raw_base64'] = base64.b64encode(raw).decode()
    snapshot = build_equity_snapshot(raw, manifest)
    bars = [dict(session=s['date'], close=str(c[4]), completed=True,
        available_at=s['close_utc'].replace(':00:00Z', ':01:00Z')) for c, s in zip(snapshot.document['candles'], snapshot.document['sessions'])]
    decision = price_confirmation(release_at='2024-11-01T20:15:00Z', decision_at='2024-11-04T21:01:00Z',
                                  sessions=snapshot.document['sessions'], bars=bars)
    row = dict(event_id='SYNTHETIC:EARNINGS', price_condition=decision['action'] == 'BUY', numeric_condition=numeric,
               earliest_model_entry_at=decision['execution_at'], confirmation_at='2024-11-04T21:01:00Z',
               model_available_at='2024-11-01T20:17:00Z', source_public_at=None)
    return snapshot, row


def run(snapshot, row, variant='PRICE_PLUS_CONTENT', *, cost='NORMAL'):
    multiplier = 1 if cost == 'NORMAL' else 2
    return study._engine_cell(snapshot, row, variant=variant,
        cost=dict(name=cost, fee_rate='0.0008' if multiplier == 1 else '0.0016',
                  slippage_pct='0.0005' if multiplier == 1 else '0.0010'),
        score_start='2024-11-05', score_end='2024-11-08', purpose='SYNTHETIC_REGRESSION', authorization_hash=None)


class NvdaEconomicTests(unittest.TestCase):
    def test_same_engine_next_open_replay_and_independent_decimal_ledger(self):
        snapshot, row = fixture(); report = run(snapshot, row)
        buys = [f for f in report['result']['fills'] if f['action'] == 'BUY']
        self.assertEqual(len(buys), 1); self.assertEqual(buys[0]['fill_time'], '2024-11-05 14:30:00+00:00')
        self.assertTrue(study.check_replay(report, run(snapshot, row))['replay_verified'])
        self.assertEqual(reconcile(report, snapshot.document)['status'], 'PASS')
        self.assertFalse(report['execution_permission']['order_allowed'])
    def test_content_veto_and_disabled_content_equality(self):
        snapshot, row = fixture(numeric=False)
        c, disabled, d = (run(snapshot, row, v) for v in ('PRICE_ONLY', 'CONTENT_DISABLED', 'PRICE_PLUS_CONTENT'))
        self.assertEqual(canonical_bytes(c['result']), canonical_bytes(disabled['result']))
        self.assertGreater(c['result']['fill_count'], 0); self.assertEqual(d['result']['fill_count'], 0)
        self.assertEqual(reconcile(d, snapshot.document)['status'], 'PASS')
    def test_positive_content_preserves_same_economic_path_in_both_costs(self):
        snapshot, row = fixture()
        for cost in ('NORMAL', 'DOUBLE'):
            c, d = run(snapshot, row, 'PRICE_ONLY', cost=cost), run(snapshot, row, cost=cost)
            self.assertEqual(canonical_bytes(c['result']), canonical_bytes(d['result']))
            self.assertEqual(c['spec']['score_start_session'], d['spec']['score_start_session'])
    def test_no_price_signal_is_retained_despite_later_rising_prices(self):
        snapshot, row = fixture(price=False)
        self.assertFalse(row['price_condition'])
        report = run(snapshot, row)
        self.assertEqual(report['result']['fill_count'], 0)
        self.assertEqual(report['result']['final_equity'], 10000)
        self.assertEqual(reconcile(report, snapshot.document)['status'], 'PASS')
    def test_loss_and_fee_accounting_remain_in_result(self):
        snapshot, row = fixture(loss=True); report = run(snapshot, row)
        self.assertLess(report['result']['total_return'], 0); self.assertEqual(report['result']['round_trip_count'], 1)
        self.assertGreater(report['result']['total_fees'], 0)
        self.assertEqual(reconcile(report, snapshot.document)['status'], 'PASS')
        self.assertLess(float(study.metrics(report)['net_pnl']), 0)
    def test_mark_to_market_is_not_a_forced_closing_trade(self):
        snapshot, row = fixture(); report = run(snapshot, row)
        self.assertGreater(report['result']['open_position_qty'], 0)
        self.assertEqual(report['result']['round_trip_count'], 0)
        self.assertEqual(report['result']['realized_pnl'], 0)
        self.assertNotEqual(report['result']['unrealized_pnl'], 0)
    def test_missing_approval_blocks_before_diagnostic_or_engine(self):
        args = Namespace(approval=None, execute_approved=True)
        with patch.object(study.diagnostic, 'prepare') as prepare, patch.object(study, '_SessionEngine') as engine:
            with self.assertRaisesRegex(ValueError, 'human_field_and_scope_approval_required'): study.prepare(args)
        prepare.assert_not_called(); engine.assert_not_called()
    def test_wrong_approval_kind_or_scope_is_not_human_authority(self):
        proposal = study.read_document(study.PROPOSAL); clocks = study.read_document(study.diagnostic.CLOCK)
        receipt = dict(schema_version='nvda-field-economic-approval-v1', proposal_sha256=study.PROPOSAL_SHA256,
            **{k: proposal[k] for k in ('source_packet_hash', 'diagnostic_hash', 'clock_evidence_sha256', 'snapshot_ids')},
            approved_event_ids=study.EVENT_IDS, approved_fields=study.FIELDS, decision='APPROVE_LISTED_FIELDS_AND_EIGHT_OFFLINE_CELLS',
            reviewer_kind='SYNTHETIC_TEST_NOT_A_HUMAN', reviewer='FICTIONAL', source_user_confirmation='FICTIONAL', reviewed_at='2026-10-02T00:00:00Z')
        with self.assertRaisesRegex(ValueError, 'human_approval_kind_or_scope'): study.check_approval(receipt, proposal, clocks)
        receipt['reviewer_kind'] = 'HUMAN_ATTESTATION'; receipt['approved_event_ids'] = ['WRONG:EVENT']
        with self.assertRaisesRegex(ValueError, 'approval_field_scope'): study.check_approval(receipt, proposal, clocks)
    def test_real_label_cannot_use_synthetic_execution_path(self):
        raw, manifest = stock_inputs(); manifest['evidence_kind'] = 'IMPORTED_UNVERIFIED'
        snapshot = build_equity_snapshot(raw, manifest); _, row = fixture()
        with self.assertRaisesRegex(ValueError, 'real_input_requires_approved_context'): run(snapshot, row)
    def test_early_information_and_shifted_entry_rejected(self):
        snapshot, row = fixture(); row['model_available_at'] = '2024-11-04T15:00:00Z'
        with self.assertRaisesRegex(ValueError, 'information_not_available'): run(snapshot, row)
        _, row = fixture(); row['earliest_model_entry_at'] = '2024-11-06T14:30:00Z'
        with self.assertRaisesRegex(ValueError, 'entry_must_equal'): run(snapshot, row)
    def test_tampered_report_does_not_replay(self):
        snapshot, row = fixture(); report = run(snapshot, row); altered = deepcopy(report)
        altered['result']['final_equity'] += 1
        with self.assertRaisesRegex(ValueError, 'report_hash_changed'): study.check_replay(altered, report)


class SyntheticStudyLifecycleTests(unittest.TestCase):
    """Synthetic orchestration only; mock authority is never a human receipt."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        self.enterContext(patch.object(study, 'ROOT', self.root))
        self.enterContext(patch.object(study, 'EVENT_IDS', ['SYNTHETIC:Q1', 'SYNTHETIC:Q2']))
        self.enterContext(patch.object(study, 'check_approval', return_value='SYNTHETIC_TEST_AUTHORITY_STUB'))
        self.enterContext(patch.object(study, 'tool_identity', return_value={'fixture': 'SYNTHETIC_TEST_ONLY'}))
        snapshot, row = fixture(); self.rows = []
        for q in ('Q1', 'Q2'):
            self.rows.append(dict(row, event_id='SYNTHETIC:' + q, fiscal_quarter=q, actual_revenue_million='1000',
                prior_guidance_midpoint_million='900', channel_publication_at='2024-11-01T20:15:00Z'))
        diag = dict(events=self.rows, counts=dict(events=2, comparable_sources=2, price_signals=2, new_research_admitted=0))
        diag['diagnostic_hash'] = digest(diag)
        self.context = dict(approval=None, approval_hash='SYNTHETIC_TEST_AUTHORITY_STUB',
            proposal=study.read_document(study.PROPOSAL), clocks={}, diagnostic=diag, snapshots={'Q1': snapshot, 'Q2': snapshot},
            input_sha256={}, tool_identity={'fixture': 'SYNTHETIC_TEST_ONLY'})
        def synthetic_cell(context, q, cost, variant):
            return run(snapshot, next(r for r in self.rows if r['fiscal_quarter'] == q), variant, cost=cost['name'])
        self.cell = self.enterContext(patch.object(study, 'run_cell', side_effect=synthetic_cell))
        self.output = self.root / 'artifacts/study'
    def test_eight_cells_eight_replays_and_claim_prevents_another_run(self):
        result = study.execute(self.context, self.output)
        self.assertEqual(result['status'], 'COMPLETED_ENGINEERING_ONLY')
        self.assertEqual(self.cell.call_count, 16)
        self.assertEqual(result['ledger_checks_completed'], 8)
        self.assertEqual(len(list(self.output.rglob('report.private.json'))), 8)
        self.assertEqual(result['counts']['content_interventions'], 0)
        self.assertTrue((self.output / 'index.html').exists())
        with self.assertRaisesRegex(ValueError, 'budget_already_claimed'):
            study.execute(self.context, self.root / 'artifacts/second-attempt')
        self.assertEqual(self.cell.call_count, 16)
    def test_failed_ledger_preserves_first_reports_and_stops_remaining_cells(self):
        real_ledger = study.reconcile; count = 0
        def fail_second(report, snapshot):
            nonlocal count
            count += 1; result = real_ledger(report, snapshot)
            if count == 2: result['status'] = 'FAIL'
            return result
        with patch.object(study, 'reconcile', side_effect=fail_second):
            result = study.execute(self.context, self.output)
        self.assertEqual(result['status'], 'STOPPED_PRESERVED_NO_AUTOMATIC_RETRY')
        self.assertEqual(result['economic_cells_started'], 2); self.assertEqual(self.cell.call_count, 4)
        self.assertEqual(result['events'][0]['status'], 'STOPPED_WITH_RETAINED_PARTIAL_CELLS')
        self.assertEqual(result['events'][1]['status'], 'NOT_STARTED')
        self.assertEqual(len(list(self.output.rglob('report.private.json'))), 2)
        self.assertIn('未完成，不能填成零收益', (self.output / 'index.html').read_text(encoding='utf-8'))
    def test_interrupted_page_rebuild_does_not_repeat_simulation(self):
        with patch.object(study, '_save_encoded_report', side_effect=OSError('FICTIONAL_PAGE_INTERRUPTION')):
            with self.assertRaisesRegex(OSError, 'FICTIONAL_PAGE_INTERRUPTION'): study.execute(self.context, self.output)
        self.assertTrue((self.output / 'study.private.json').exists()); self.assertEqual(self.cell.call_count, 16)
        path = study.rebuild_report(self.output)
        self.assertTrue(path.exists()); self.assertEqual(self.cell.call_count, 16)
        path.write_text('conflicting fictional evidence', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'existing_report_changed'): study.rebuild_report(self.output)


if __name__ == '__main__': unittest.main()
