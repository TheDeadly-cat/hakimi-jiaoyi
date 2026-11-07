"""Portable, fictional saved-run diagnostics and immutable validation matrices."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.documents import digest, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.equity_dataset import build_equity_snapshot
from hakimi_research.offline_app import run_task, verify_run, write_new
from hakimi_research.task_validation import create_validation, read_validation, saved_run_diagnostics
from hakimi_research.trade_cli import create_task
from test_equity_research import stock_inputs


def fixture_snapshot(*, cutoff=None, revise=False):
    raw, manifest = stock_inputs()
    rows = raw.decode().splitlines()
    if revise:
        fields = rows[2].split(',')
        fields[4] = str(float(fields[4]) + .125)
        rows[2] = ','.join(fields)
    if cutoff:
        rows = [rows[0], *(row for row in rows[1:] if row.split(',')[0] <= cutoff)]
        calendar = manifest['calendar']
        calendar['days'] = [row for row in calendar['days'] if row['date'] <= cutoff]
        calendar['coverage_end'] = cutoff
        calendar['source']['raw_base64'] = base64.b64encode(json.dumps(calendar['days']).encode()).decode()
        manifest['corporate_actions']['coverage_end'] = cutoff
    raw = ('\n'.join(rows) + '\n').encode()
    manifest['price_source']['raw_base64'] = base64.b64encode(raw).decode()
    return build_equity_snapshot(raw, manifest)


class TaskValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # A single measured runtime prevents concurrent source editing by a
        # developer from making this focused fixture nondeterministic.
        self.runtime = build_runtime_provenance()
        for module in ('offline_app', 'equity_research', 'task_validation'):
            mock = patch('hakimi_research.' + module + '.build_runtime_provenance',
                         side_effect=lambda: deepcopy(self.runtime))
            mock.start()
            self.addCleanup(mock.stop)

    def seed(self, *, fee=.0008, slip=.0005, cutoff=None, strategy='price.dual_ma@1'):
        snapshot = fixture_snapshot(cutoff=cutoff)
        path = self.root / ('source-' + str(len(list(self.root.glob('source-*')))) + '.json')
        write_new(path, snapshot.document)
        task = self.root / ('task-' + path.stem + '.json')
        params = dict(fast_window=2, slow_window=4, position_pct=.25, stop_loss_pct=.03, take_profit_pct=.06)
        if strategy == 'price.buy_and_hold@1':
            params = dict(target_position_pct=.25)
        create_task(task, snapshot=path, strategy=strategy, params=params,
            score_start='2024-11-11', score_end=cutoff or '2024-12-03', fee_rate=fee, slippage_pct=slip,
            initial_cash=10000, output_dir=self.root / 'runs')
        return run_task(task), snapshot

    def test_diagnostics_are_read_only_and_keep_short_sample_nulls(self):
        run, _ = self.seed()
        before = {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
        with patch('hakimi_research.task_validation.run_strategy', side_effect=AssertionError('no calculation')):
            view = saved_run_diagnostics(run)
        self.assertEqual(view['new_economic_runs'], 0)
        self.assertEqual(view['sample']['evidence_kind'], 'SYNTHETIC_TEST')
        self.assertEqual(view['statistical_status']['annualized_return'], 'SHORT_SAMPLE')
        self.assertIsNone(view['summary']['annualized_return'])
        self.assertIsNone(view['summary']['sharpe_ratio'])
        self.assertEqual(before, {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()})
        # Some retained report generations did not store these optional
        # diagnostics. Reading them must not disable the original result view.
        from hakimi_research.task_validation import _diagnostics
        manifest, report, _ = verify_run(run)
        historical = deepcopy(report)
        for field in ('statistical_status', 'accounting', 'risk_semantics', 'round_trips', 'return_series'):
            historical['result'].pop(field, None)
        historical_view = _diagnostics(manifest, historical)
        self.assertEqual(historical_view['statistical_status']['status'], 'NOT_AVAILABLE')
        self.assertEqual(historical_view['accounting']['status'], 'NOT_AVAILABLE')
        self.assertIsNone(historical_view['sample']['return_observations'])
        with self.assertRaisesRegex(ValueError, 'cannot_modify_original_run'):
            create_validation(run, run / 'validation')

    def test_costs_only_change_cost_fields_and_package_reopens_without_calculation(self):
        run, _ = self.seed()
        before = {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
        output = self.root / 'validation'
        result = create_validation(run, output)
        original = verify_run(run)[1]
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['new_economic_runs'], 4)
        self.assertEqual(result['cost_scenarios'][0]['status'], 'REUSED_SAVED_RESULT')
        self.assertEqual(result['cost_scenarios'][0]['report_hash'], original['report_hash'])
        for factor in (2, 3):
            derived = read_document(output / ('cost-' + str(factor)) / 'report.json')
            expected = deepcopy(original['spec'])
            expected.update(fee_rate=original['spec']['fee_rate'] * factor,
                            slippage_pct=original['spec']['slippage_pct'] * factor)
            self.assertEqual(derived['spec'], expected)
            self.assertEqual(derived['dataset'], original['dataset'])
        cash = result['benchmarks'][0]['summary']
        self.assertEqual(cash['total_return'], 0)
        self.assertEqual(cash['fill_count'], 0)
        self.assertEqual(result['benchmarks'][1]['summary']['fill_count'], 1)
        self.assertEqual(result['followup']['status'], 'NOT_RUN')
        with patch('hakimi_research.task_validation.run_strategy', side_effect=AssertionError('no calculation')):
            self.assertEqual(read_validation(output), result)
        self.assertEqual(before, {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()})
        with self.assertRaisesRegex(ValueError, 'validation_output_exists'):
            create_validation(run, output)

    def test_zero_costs_are_explicitly_unchanged_and_invalid_stress_is_rejected(self):
        run, _ = self.seed(fee=0, slip=0)
        result = create_validation(run, self.root / 'zero')
        self.assertTrue(all(row['changed_from_base'] is False for row in result['cost_scenarios']))
        self.assertTrue(all(row['fee_rate'] == row['slippage_pct'] == 0 for row in result['cost_scenarios']))
        from hakimi_research.task_validation import _cost_spec
        for rate in (1e308, .5):
            with self.assertRaisesRegex(ValueError, 'cost_stress_out_of_range'):
                _cost_spec(dict(fee_rate=rate, slippage_pct=0), 3)

    def test_tampered_bytes_and_resealed_projection_are_rejected(self):
        run, _ = self.seed()
        output = self.root / 'validation'
        create_validation(run, output)
        report = output / 'cost-2/report.json'
        original = report.read_bytes()
        report.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'artifact_missing_or_changed'):
            read_validation(output)
        report.write_bytes(original)
        manifest = read_document(output / 'validation.json')
        manifest['cost_scenarios'][1]['summary']['total_return'] = 999
        manifest['validation_hash'] = digest({k: v for k, v in manifest.items() if k != 'validation_hash'})
        (output / 'validation.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'scenario_identity_conflict'):
            read_validation(output)

    def test_new_runtime_cannot_recalculate_old_run_but_can_read_diagnostics(self):
        run, _ = self.seed()
        changed = deepcopy(self.runtime)
        changed['source_identity']['content_sha256'] = 'a' * 64
        with patch('hakimi_research.task_validation.build_runtime_provenance', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'same_verified_code'):
                create_validation(run, self.root / 'blocked')
            self.assertEqual(saved_run_diagnostics(run)['new_economic_runs'], 0)
        self.assertFalse((self.root / 'blocked').exists())

    def test_later_interval_keeps_parameters_and_rejects_revised_prefix(self):
        run, _ = self.seed(cutoff='2024-11-22')
        following = self.root / 'following.json'
        write_new(following, fixture_snapshot().document)
        output = self.root / 'validation'
        result = create_validation(run, output, followup_snapshot=following,
            followup_start='2024-11-25', followup_end='2024-12-03')
        self.assertEqual(result['new_economic_runs'], 5)
        self.assertEqual(result['followup']['status'], 'COMPLETED')
        self.assertFalse(result['followup']['blind_holdout'])
        spec = read_document(output / 'followup/spec.json')
        original = verify_run(run)[1]['spec']
        for key in original.keys() - {'snapshot_id', 'score_start_session', 'score_end_session'}:
            self.assertEqual(spec[key], original[key])
        revised = self.root / 'revised.json'
        write_new(revised, fixture_snapshot(revise=True).document)
        with self.assertRaisesRegex(ValueError, 'prefix_missing_or_revised'):
            create_validation(run, self.root / 'revised-validation', followup_snapshot=revised,
                followup_start='2024-11-25', followup_end='2024-12-03')
        self.assertFalse((self.root / 'revised-validation').exists())
        with self.assertRaisesRegex(ValueError, 'must_start_after_base_score_end'):
            create_validation(run, self.root / 'overlap', followup_snapshot=following,
                followup_start='2024-11-22', followup_end='2024-12-03')

    def test_failed_scenario_is_retained_and_interrupted_output_is_not_reused(self):
        run, _ = self.seed()
        output = self.root / 'validation'
        from hakimi_research.task_validation import run_strategy as real
        def stop_double(strategy, snapshot, spec, context):
            if spec['fee_rate'] == .0016:
                raise ValueError('fictional_scenario_stopped')
            return real(strategy, snapshot, spec, context)
        with patch('hakimi_research.task_validation.run_strategy', side_effect=stop_double):
            result = create_validation(run, output)
        self.assertEqual(result['status'], 'COMPLETED_WITH_STOPPED_SCENARIOS')
        self.assertEqual(result['new_economic_runs'], 3)
        row = result['cost_scenarios'][1]
        self.assertEqual(row['status'], 'STOPPED')
        self.assertIsNone(row['summary'])
        self.assertEqual(read_validation(output), result)
        interrupted = self.root / 'interrupted'
        with patch('hakimi_research.task_validation.run_strategy', side_effect=OSError('fictional disk stop')):
            with self.assertRaisesRegex(OSError, 'fictional disk stop'):
                create_validation(run, interrupted)
        self.assertTrue((interrupted / 'started.json').is_file())
        self.assertFalse((interrupted / 'validation.json').exists())
        with self.assertRaisesRegex(ValueError, 'validation_output_exists'):
            create_validation(run, interrupted)

    def test_event_costs_retain_exact_context_and_buy_hold_baseline_is_supported(self):
        from hakimi_research.trade_cli import initialize_demo
        workspace = self.root / 'event-workspace'
        initialize_demo(workspace)
        event_run = run_task(workspace / 'tasks/event.json')
        output = self.root / 'event-validation'
        result = create_validation(event_run, output)
        base = verify_run(event_run)[1]
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual((output / 'base/inputs/event-context.json').read_bytes(),
                         (event_run / 'inputs/event-context.json').read_bytes())
        for factor in (2, 3):
            report = read_document(output / ('cost-' + str(factor)) / 'report.json')
            self.assertEqual(report['event_context'], base['event_context'])
            self.assertEqual(report['spec']['event_context_hash'], base['spec']['event_context_hash'])
            self.assertEqual(report['spec']['event_rule'], base['spec']['event_rule'])
        for benchmark in ('cash', 'buy_and_hold'):
            self.assertNotIn('event_context', read_document(output / ('benchmark-' + benchmark) / 'report.json'))
        buy_hold, _ = self.seed(strategy='price.buy_and_hold@1')
        baseline = create_validation(buy_hold, self.root / 'buy-hold-validation')
        self.assertEqual(baseline['status'], 'COMPLETED')
        self.assertEqual(baseline['base']['strategy'], 'price.buy_and_hold@1')


if __name__ == '__main__':
    unittest.main()
