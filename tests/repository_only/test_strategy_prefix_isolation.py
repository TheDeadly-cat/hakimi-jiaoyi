"""Synthetic callback-boundary and immutable verification-tool regressions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
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

    def holdout_seed(self, root):
        """Fictional prices and a real temporary Git commitment; no market source."""
        moment = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        stamp = lambda seconds: (moment + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')
        source_raw = b'{"kind":"synthetic-only holdout source"}'
        raw, declaration = FIXTURE.stock_inputs()
        source = dict(name='SYNTHETIC_HOLDOUT', reference='https://example.test/holdout/TEST',
                      retrieved_at=stamp(182), raw_base64=base64.b64encode(source_raw).decode())
        declaration['identity']['source'] = deepcopy(source)
        declaration['corporate_actions']['source'] = deepcopy(source)
        declaration['price_source']['retrieved_at'] = stamp(182)
        declaration['retrieved_at'] = stamp(182)
        snapshot = build_equity_snapshot(raw, declaration)
        prepared_root = root / 'prepared'
        prepared_root.mkdir()
        snapshot_path = prepared_root / 'snapshot.json'
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
        design = dict(schema_version=AUDIT.HOLDOUT_SCHEMA, mode=AUDIT.HOLDOUT_MODE, recorded_at=stamp(0),
            score_start=spec['score_start_session'], score_end=spec['score_end_session'],
            score_sessions=dates[first:], context_dates=dates[:first], context_start=dates[0], context_sessions=first,
            **{key: spec[key] for key in ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk',
                'end_policy', 'execution_policy', 'quantity_policy', 'purpose')},
            cost_multipliers=[1, 2, 3], benchmarks=['cash', 'buy_and_hold'],
            sources={'TEST': {'reference': source['reference']}}, repository_path=str(root), protocol_repo_path='design.json',
            acquisition_output_path=str(prepared_root),
            acquisition_policy=dict(max_requests_per_symbol=2, retry_delay_seconds=3, same_url_only=True,
                retry_only_without_successful_response=True,
                retry_reason_codes=['SOURCE_HTTP_429', 'SOURCE_HTTP_502', 'SOURCE_HTTP_503', 'SOURCE_REQUEST_FAILED_NO_RETRY']),
            exposure_audit={'sha256': 'a' * 64}, parameter_design={'sha256': 'b' * 64},
            exposure_addendum={'path': str(root / 'synthetic-attribution.json'), 'sha256': 'c' * 64},
            execution_runtime_source_sha256=manifest['runtime']['source_identity']['content_sha256'])
        design['plan_hash'] = digest(design)
        path = root / 'design.json'
        write_new(path, design)
        subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
        subprocess.run(['git', 'add', '--', 'design.json'], cwd=root, check=True, capture_output=True)
        environment = {**os.environ, 'GIT_AUTHOR_DATE': stamp(60), 'GIT_COMMITTER_DATE': stamp(60)}
        subprocess.run(['git', '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'synthetic pre-acquisition commitment'], cwd=root, env=environment,
                       check=True, capture_output=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        acquired_root = prepared_root
        (acquired_root / 'source.json').write_bytes(source_raw)
        acquired_source = dict(status='ACQUIRED', reference=source['reference'], request_started_at=stamp(181),
            retrieved_at=stamp(182), raw_path='source.json', raw_sha256=sha256(source_raw).hexdigest(),
            attempts=[dict(number=1, status='ACQUIRED', request_started_at=stamp(181), completed_at=stamp(182),
                           reference=source['reference'], response_status=200,
                           raw_path='source.json', raw_sha256=sha256(source_raw).hexdigest())])
        acquisition = dict(schema_version='blind-holdout-acquisition-v1', status='ACQUIRED',
            plan_hash=design['plan_hash'], design_sha256=sha256(path.read_bytes()).hexdigest(), commit=commit,
            commit_time=stamp(60), started_at=stamp(180), completed_at=stamp(183), sources={'TEST': acquired_source})
        acquisition_path = acquired_root / 'acquisition.json'
        write_new(acquisition_path, acquisition)
        spec_path = prepared_root / 'spec.json'
        write_new(spec_path, spec)
        snapshot_sha, spec_sha = sha256(snapshot_path.read_bytes()).hexdigest(), sha256(spec_path.read_bytes()).hexdigest()
        prep = dict(schema_version='blind-holdout-preparation-v1', status='READY', plan_hash=design['plan_hash'],
            design_sha256=sha256(path.read_bytes()).hexdigest(), commit=commit, prepared_at=stamp(240),
            acquisition_path=str(acquisition_path), acquisition_sha256=sha256(acquisition_path.read_bytes()).hexdigest(),
            symbols={'TEST': dict(status='READY', snapshot_path=str(snapshot_path), snapshot_sha256=snapshot_sha,
                                 snapshot_id=snapshot.snapshot_id, spec_path=str(spec_path), spec_sha256=spec_sha)},
            files={'snapshot.json': snapshot_sha, 'spec.json': spec_sha,
                   'acquisition.json': sha256(acquisition_path.read_bytes()).hexdigest()})
        prep_path = prepared_root / 'preparation.json'
        write_new(prep_path, prep)
        return run, path, design, prep_path, prep, acquisition_path, acquisition

    def test_holdout_receipts_bind_real_commit_source_snapshot_and_preserve_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, design, prep_path, prep, _, _ = self.holdout_seed(root)
            before = AUDIT._inventory(run)
            # The companion tool owns protocol-selection validation. This test
            # exercises the observer's independent commit/receipt/run bindings.
            with patch.object(AUDIT, '_holdout_protocol_checker', return_value=lambda *a, **k: design):
                result = AUDIT.verify_saved_run(run, design_path=path, design_sha256=sha256(path.read_bytes()).hexdigest(),
                    output_path=root / 'verified-holdout.json', preparation_path=prep_path,
                    preparation_sha256=sha256(prep_path.read_bytes()).hexdigest())
            self.assertEqual(AUDIT._inventory(run), before)
            self.assertTrue(result['economic_result_exact_match'])
            self.assertFalse(result['blind_holdout_proven'])
            self.assertEqual(result['blinding_evidence']['protocol_commit'], prep['commit'])
            self.assertTrue(result['blinding_evidence']['preacquisition_commitment_verified'])
            self.assertEqual(result['blinding_evidence']['exposure_addendum_sha256'], 'c' * 64)
            self.assertFalse(result['blinding_evidence']['chronological_oos'])
            self.assertFalse(result['blinding_evidence']['global_unseen_data_proven'])
            self.assertEqual(result['additional_validation_calculations'], 1)

    def test_holdout_requires_preparation_before_any_recalculation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, design, prep_path, *_ = self.holdout_seed(root)
            with patch.object(AUDIT, 'run_strategy', side_effect=AssertionError('must not calculate')):
                with self.assertRaisesRegex(ValueError, 'requires_preparation'):
                    self.audit(run, path, root / 'missing.json')
                with patch.object(AUDIT, '_holdout_protocol_checker', return_value=lambda *a, **k: design):
                    with self.assertRaisesRegex(ValueError, 'reference_bytes_changed'):
                        AUDIT.verify_saved_run(run, design_path=path, design_sha256=sha256(path.read_bytes()).hexdigest(),
                            output_path=root / 'wrong-hash.json', preparation_path=prep_path, preparation_sha256='0' * 64)
            self.assertFalse((root / 'missing.json.started.json').exists())
            self.assertFalse((root / 'wrong-hash.json.started.json').exists())

    def test_holdout_rejects_postdated_commit_wrong_source_and_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, design, prep_path, prep, acquisition_path, acquisition = self.holdout_seed(root)
            _, report, snapshot = verify_run(run)
            started = read_document(run / 'started.json')
            def check(current_prep, current_acquisition):
                acquisition_path.write_text(json.dumps(current_acquisition), encoding='utf-8')
                current_prep['acquisition_sha256'] = sha256(acquisition_path.read_bytes()).hexdigest()
                current_prep['files']['acquisition.json'] = current_prep['acquisition_sha256']
                prep_path.write_text(json.dumps(current_prep), encoding='utf-8')
                return AUDIT._check_holdout_bindings(design, path.read_bytes(), path, prep_path,
                    sha256(prep_path.read_bytes()).hexdigest(), report, snapshot, started)
            with patch.object(AUDIT, '_holdout_protocol_checker', return_value=lambda *a, **k: design):
                for label in ('commit-time', 'retrieved-before-commit', 'reference', 'snapshot-id', 'prepared-after-run',
                              'attempt-history', 'inventory', 'retry-response-200', 'retry-unknown', 'retry-reason',
                              'retry-too-soon', 'excess-attempts', 'retry-valid'):
                    changed_prep, changed_acquisition = deepcopy(prep), deepcopy(acquisition)
                    if label == 'commit-time':
                        changed_acquisition['commit_time'] = changed_acquisition['completed_at']
                    elif label == 'retrieved-before-commit':
                        changed_acquisition['sources']['TEST']['request_started_at'] = design['recorded_at']
                    elif label == 'reference':
                        changed_acquisition['sources']['TEST']['reference'] = 'https://example.test/OTHER'
                    elif label == 'snapshot-id':
                        changed_prep['symbols']['TEST']['snapshot_id'] = 'f' * 64
                    elif label == 'prepared-after-run':
                        changed_prep['prepared_at'] = '2100-01-01T00:00:00Z'
                    elif label == 'attempt-history':
                        changed_acquisition['sources']['TEST']['attempts'] = []
                    elif label == 'inventory':
                        changed_prep['files'] = {'spec.json': prep['files']['spec.json']}
                    else:
                        source = changed_acquisition['sources']['TEST']
                        last = source['attempts'][0]
                        begin = AUDIT._date(last['request_started_at'])
                        first = dict(number=1, status='FAILED', reason='SOURCE_HTTP_429', response_status=429,
                            outcome_known=True, successful_response_received=False, reference=source['reference'],
                            request_started_at=changed_acquisition['started_at'],
                            completed_at=changed_acquisition['started_at'])
                        # Move the initial request so a valid three-second retry
                        # interval fits inside the fictional acquisition clock.
                        changed_acquisition['started_at'] = (begin - timedelta(seconds=5)).isoformat()
                        first['request_started_at'] = first['completed_at'] = changed_acquisition['started_at']
                        last['number'] = 2
                        source['attempts'] = [first, last]
                        if label == 'retry-response-200':
                            first['response_status'] = 200
                        elif label == 'retry-unknown':
                            first['outcome_known'] = False
                        elif label == 'retry-reason':
                            first['reason'] = 'SOURCE_ALREADY_RECEIVED_BUT_BAD_PRICES'
                        elif label == 'retry-too-soon':
                            first['completed_at'] = (begin - timedelta(seconds=2)).isoformat()
                        elif label == 'excess-attempts':
                            source['attempts'].insert(1, deepcopy(first))
                    if label == 'retry-valid':
                        self.assertEqual(check(changed_prep, changed_acquisition)['sources']['TEST']['attempts'], 2)
                        continue
                    with self.subTest(label=label), self.assertRaises(ValueError):
                        check(changed_prep, changed_acquisition)

    def test_holdout_rejects_uncommitted_protocol_and_mutated_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, path, design, prep_path, prep, acquisition_path, acquisition = self.holdout_seed(root)
            _, report, snapshot = verify_run(run)
            started = read_document(run / 'started.json')
            with patch.object(AUDIT, '_holdout_protocol_checker', return_value=lambda *a, **k: design):
                (acquisition_path.parent / 'source.json').write_bytes(b'changed source')
                with self.assertRaisesRegex(ValueError, 'artifact_bytes_changed'):
                    AUDIT._check_holdout_bindings(design, path.read_bytes(), path, prep_path,
                        sha256(prep_path.read_bytes()).hexdigest(), report, snapshot, started)
                altered_raw = path.read_bytes() + b' '
                changed_prep, changed_acquisition = deepcopy(prep), deepcopy(acquisition)
                changed_prep['design_sha256'] = changed_acquisition['design_sha256'] = sha256(altered_raw).hexdigest()
                acquisition_path.write_text(json.dumps(changed_acquisition), encoding='utf-8')
                changed_prep['acquisition_sha256'] = sha256(acquisition_path.read_bytes()).hexdigest()
                changed_prep['files']['acquisition.json'] = changed_prep['acquisition_sha256']
                prep_path.write_text(json.dumps(changed_prep), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'preacquisition_commit_bytes_conflict'):
                    AUDIT._check_holdout_bindings(design, altered_raw, path, prep_path,
                        sha256(prep_path.read_bytes()).hexdigest(), report, snapshot, started)


if __name__ == '__main__':
    unittest.main()
