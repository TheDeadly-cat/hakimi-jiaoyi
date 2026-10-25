"""Synthetic callback-boundary and immutable verification-tool regressions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('prefix_audit_tool', ROOT / 'tools/verify_strategy_prefix_isolation.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
FIXTURE_SPEC = importlib.util.spec_from_file_location('equity_prefix_fixture', ROOT / 'tests/test_equity_research.py')
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)

from hakimi_research.documents import digest, read_document
from hakimi_research.equity_dataset import build_equity_snapshot
from hakimi_research.models import Portfolio
from hakimi_research.offline_app import run_task, verify_run, write_new
from hakimi_research.strategies.templates import DualMovingAverageStrategy, build_strategy
from hakimi_research.trade_cli import create_task


class PrefixIsolationTests(unittest.TestCase):
    def test_future_perturbation_keeps_past_nonempty_economics_and_callbacks(self):
        result = AUDIT.synthetic_check()
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(all(result['past_prefix_equal'].values()))
        self.assertTrue(result['past_callback_trace_equal'])
        self.assertGreater(result['compared_past_fill_count'], 0)
        self.assertTrue(result['future_economics_changed'])
        self.assertEqual(result['baseline_and_perturbed_calculations'], 2)
        self.assertEqual([r['visible_rows'] for r in result['trace']], list(range(12, 48)))
        for row in result['trace']:
            self.assertNotIn('prices', row)
            self.assertEqual(len(row['prefix_sha256']), 64)
            self.assertLess(pd.Timestamp(row['visible_through']), pd.Timestamp(row['next_execution_open']))
            self.assertTrue(all(b['visible_bytes'] == b['backing_bytes'] for b in row['numeric_allocations']))

    def frame(self):
        values = np.arange(150, dtype=float).reshape(30, 5) + 100
        return pd.DataFrame(values, columns=AUDIT.FIELDS, index=pd.date_range('2024-01-01', periods=30, tz='UTC'))

    def test_shared_future_backing_and_changed_prefix_are_detected(self):
        data = self.frame()
        with self.assertRaisesRegex(ValueError, 'backing_extends|shares_engine'):
            AUDIT.check_visible_frame(data.iloc[:12], data, 12)
        copied = data.iloc[:12].copy(deep=True)
        self.assertEqual(AUDIT.check_visible_frame(copied, data, 12)['visible_rows'], 12)
        copied.iloc[0, 3] += 1
        with self.assertRaisesRegex(ValueError, 'exact_prefix'):
            AUDIT.check_visible_frame(copied, data, 12)

    def test_guard_bypass_is_rejected_and_profiler_is_restored(self):
        data = self.frame()
        strategy = build_strategy('dual_ma', dict(fast_window=5, slow_window=10))
        with self.assertRaisesRegex(ValueError, 'without_existing_guard'):
            with AUDIT.PrefixObserver(data, 12, 30):
                DualMovingAverageStrategy.generate_signal.__wrapped__(strategy, data.iloc[:12].copy(), Portfolio(cash=10000))
        self.assertIsNone(sys.getprofile())

    def test_no_callback_or_metadata_side_channel_cannot_pass(self):
        data = self.frame()
        with self.assertRaisesRegex(ValueError, 'coverage_incomplete'):
            with AUDIT.PrefixObserver(data, 12, 30):
                pass
        visible = data.iloc[:12].copy(deep=True)
        visible.attrs['future'] = 'hidden data'
        with self.assertRaisesRegex(ValueError, 'exact_prefix'):
            AUDIT.check_visible_frame(visible, data, 12)

    def seed(self, root):
        frozen_at = datetime.now(timezone.utc).isoformat()
        snapshot = build_equity_snapshot(*FIXTURE.stock_inputs())
        snapshot_path = root / 'snapshot.json'
        write_new(snapshot_path, snapshot.document)
        task = root / 'task.json'
        create_task(task, snapshot=snapshot_path, strategy='price.dual_ma@1',
            params=dict(fast_window=2, slow_window=4, position_pct=.25, stop_loss_pct=.03, take_profit_pct=.06),
            score_start='2024-11-11', score_end='2024-12-03', initial_cash=10000,
            fee_rate=.0008, slippage_pct=.0005, output_dir=root / 'runs')
        run = run_task(task)
        manifest, report, _ = verify_run(run)
        spec, dates = report['spec'], [r['date'] for r in snapshot.document['sessions']]
        first = dates.index(spec['score_start_session'])
        design = dict(schema_version='fixed-month-replay-design-v1', recorded_at=frozen_at,
            score_start=spec['score_start_session'], score_end=spec['score_end_session'],
            score_sessions=dates[first:], context_dates=dates[:first], context_start=dates[0], context_sessions=first,
            **{key: spec[key] for key in ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk',
                'end_policy', 'execution_policy', 'quantity_policy', 'purpose')},
            cost_multipliers=[1, 2, 3], benchmarks=['cash', 'buy_and_hold'], sources={'TEST': {'synthetic': True}},
            execution_runtime_source_sha256=manifest['runtime']['source_identity']['content_sha256'])
        design['plan_hash'] = digest(design)
        path = root / 'design.json'
        write_new(path, design)
        return run, path, design

    def audit(self, run, design, output):
        return AUDIT.verify_saved_run(run, design_path=design,
            design_sha256=sha256(design.read_bytes()).hexdigest(), output_path=output)

    def test_saved_run_verification_preserves_files_counts_replay_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, design, _ = self.seed(root)
            before = AUDIT._inventory(run)
            result = self.audit(run, design, root / 'verified.json')
            self.assertTrue(result['economic_result_exact_match'])
            self.assertEqual(result['additional_validation_calculations'], 1)
            self.assertEqual(result['new_product_runs'], 0)
            self.assertEqual(AUDIT._inventory(run), before)
            self.assertFalse(result['blind_holdout_proven'])
            self.assertFalse(result['os_sandbox'])
            self.assertEqual(len(result['trace']), 16)
            for row in result['trace']:
                self.assertTrue(row['future_row_index_rejected'])
                self.assertLess(AUDIT._date(row['decision_available_at']), AUDIT._date(row['next_execution_open']))
            with patch.object(AUDIT, 'run_strategy', side_effect=AssertionError('must not calculate')):
                with self.assertRaisesRegex(ValueError, 'no_automatic_recalculation'):
                    self.audit(run, design, root / 'verified.json')

    def test_changed_or_postdated_design_and_runtime_drift_stop_before_calculation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, design = self.seed(root)
            manifest, report, snapshot = verify_run(run)
            current = AUDIT.build_runtime_provenance()
            started = read_document(run / 'started.json')
            for key, value in [('fee_rate', .123), ('score_end', '2024-12-02'),
                               ('recorded_at', '2100-01-01T00:00:00Z'),
                               ('execution_runtime_source_sha256', 'a' * 64)]:
                changed = deepcopy(design)
                changed[key] = value
                changed['plan_hash'] = digest({k: v for k, v in changed.items() if k != 'plan_hash'})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    AUDIT.check_design(changed, manifest, report, snapshot, current, started)
            with patch.object(AUDIT, 'run_strategy', side_effect=AssertionError('must not calculate')):
                with self.assertRaisesRegex(ValueError, 'bytes_changed'):
                    AUDIT.verify_saved_run(run, design_path=path, design_sha256='0' * 64,
                                           output_path=root / 'blocked.json')
            self.assertFalse((root / 'blocked.json.started.json').exists())

    def test_comparison_failure_retains_start_failure_and_protects_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, design, _ = self.seed(root)
            before = AUDIT._inventory(run)
            real = AUDIT.run_strategy
            def changed(*args, **kwargs):
                result = real(*args, **kwargs)
                result.document['result']['total_fees'] += 1
                return result
            with patch.object(AUDIT, 'run_strategy', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'economic_result_differs'):
                    self.audit(run, design, root / 'failed.json')
            self.assertFalse((root / 'failed.json').exists())
            self.assertTrue((root / 'failed.json.started.json').is_file())
            self.assertTrue((root / 'failed.json.failed.json').is_file())
            self.assertEqual(AUDIT._inventory(run), before)

    def amended(self, root, path, original):
        moment = AUDIT._date(original['recorded_at'])
        stopped = root / 'stopped.json'
        diagnostic = root / 'diagnostic.json'
        write_new(stopped, dict(schema_version='sealed-month-replay-preparation-v1', status='STOPPED',
            prepared_at=(moment + timedelta(microseconds=1)).isoformat(), plan_hash=original['plan_hash'], economic_runs=0,
            symbols={'TEST': dict(status='STOPPED', reason='SOURCE_ADJUSTED_RAW_MISMATCH')}))
        write_new(diagnostic, dict(plan_hash=original['plan_hash'], read_only=True, economic_runs=0, new_source_requests=0))
        design = deepcopy(original)
        design.update(schema_version='fixed-month-replay-design-v2',
            recorded_at=(moment + timedelta(microseconds=2)).isoformat(),
            historical_price_policy=dict(id='YAHOO_QUOTE_POST_WINDOW_DIVIDEND_RECONCILIATION_V1',
                strategy_fields=list(AUDIT.FIELDS), adjusted_close_used_for_strategy=False, events_used_for_strategy=False,
                max_adjusted_close_error_float32_ulps=2, require_no_in_window_actions=True,
                require_no_splits_through_source_acquisition=True, require_all_post_window_adjustments_explained=True,
                require_close_and_adjusted_exact_float32_values=True, verify_entire_context_to_source_latest_complete=True,
                require_last_event_following_factor_one=True),
            amends=dict(original_design_path=str(path), original_design_sha256=sha256(path.read_bytes()).hexdigest(),
                original_plan_hash=original['plan_hash'], stopped_receipt_path=str(stopped),
                stopped_receipt_sha256=sha256(stopped.read_bytes()).hexdigest(), diagnostic_path=str(diagnostic),
                diagnostic_sha256=sha256(diagnostic.read_bytes()).hexdigest(), reason='SYNTHETIC source-only diagnosis'))
        design['plan_hash'] = digest({k: v for k, v in design.items() if k != 'plan_hash'})
        return design

    def test_v2_accepts_preserved_v1_stop_and_exact_fixed_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, original = self.seed(root)
            design = self.amended(root, path, original)
            manifest, report, snapshot = verify_run(run)
            self.assertEqual(AUDIT.check_design(design, manifest, report, snapshot,
                AUDIT.build_runtime_provenance(), read_document(run / 'started.json')), (6, 22))
            self.assertEqual(read_document(path), original)

    def test_v2_rejects_changed_policy_weak_tolerance_and_reselected_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, path, original = self.seed(root)
            design = self.amended(root, path, original)
            for key, value in [('adjusted_close_used_for_strategy', True), ('events_used_for_strategy', 0),
                               ('max_adjusted_close_error_float32_ulps', 3),
                               ('verify_entire_context_to_source_latest_complete', False)]:
                changed = deepcopy(design)
                changed['historical_price_policy'][key] = value
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'price_policy_conflict'):
                    AUDIT._check_amendment(changed)
            for key, value in [('fee_rate', .003), ('score_start', '2024-11-12'), ('sources', {'OTHER': {}})]:
                changed = deepcopy(design)
                changed[key] = value
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'changed_frozen'):
                    AUDIT._check_amendment(changed)

    def test_v2_requires_actual_unchanged_stop_bytes_and_original_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, path, original = self.seed(root)
            design = self.amended(root, path, original)
            changed = deepcopy(design)
            changed['amends']['original_plan_hash'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'identity_conflict'):
                AUDIT._check_amendment(changed)
            stopped = Path(design['amends']['stopped_receipt_path'])
            stopped.write_bytes(stopped.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'reference_bytes_changed'):
                AUDIT._check_amendment(design)


if __name__ == '__main__':
    unittest.main()
