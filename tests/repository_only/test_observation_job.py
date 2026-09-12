"""Offline launcher fault tests: every observer child is replaced by a local fake."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('observation_job_tested', Path(__file__).resolve().parents[2] / 'tools/observation_job.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ObservationJobTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'frozen'
        self.root.mkdir()
        self.jobs = Path(temp.name) / 'job-receipts'
        self.cutoff = datetime(2026, 9, 9, 5, tzinfo=timezone.utc)
        self.clock = self.cutoff + timedelta(minutes=2)
        self.plan = {'plans': [{'plan_hash': 'a' * 64}, {'plan_hash': 'b' * 64}]}
        self.missing = []
        for context in (patch.object(module, 'now', side_effect=lambda: self.clock),
                        patch.object(module, 'verify_deployment', return_value=self.plan)):
            context.start()
            self.addCleanup(context.stop)

    def child(self, argv, root, *, duplicate=False, old=False):
        self.assertTrue(list(self.jobs.glob('attempts/*/started.json')), 'Launcher start receipt must exist before child launch')
        cutoff = self.cutoff - timedelta(hours=1) if old else self.cutoff
        records = [{'plan_hash': p['plan_hash'], 'record_hash': ('c' if i == 0 else 'd') * 64,
                    'cutoff': module.stamp(cutoff), 'signal_available_at': module.stamp(cutoff + timedelta(minutes=2)),
                    'timing_status': 'ON_TIME', 'backfill': False} for i, p in enumerate(self.plan['plans'])]
        result = module.sealed({'status': 'RECORDED_AND_REPLAYED', 'input_cutoff': module.stamp(cutoff),
                                'plan_hash': module.PLAN_SHA256, 'observations': 2, 'replays_verified': 2,
                                'exit_code': 0, 'order_allowed': False, 'automatic_backfill': False,
                                'original_bytes_preserved': True, 'classification': 'DUPLICATE_VERIFY' if duplicate else 'FIRST_ATTEMPT',
                                'runtime_verification': {'source_sha256': module.SOURCE_SHA256, 'environment_sha256': module.ENVIRONMENT_SHA256,
                                                         'source_status': 'BUILD_VERIFIED', 'environment_status': 'VERIFIED'}, 'records': records})
        path = self.root / 'forward/cycles' / cutoff.strftime('%Y%m%dT%H0000Z') / 'forward_cycle_fixed.json'
        if not path.exists():
            module.write_new(path, {'status': 'RECORDED_AND_REPLAYED', 'cutoff': module.stamp(cutoff), 'observations': 2,
                                    'replays_verified': 2, 'order_allowed': False, 'automatic_backfill': False, 'prior_absences': self.missing})
        return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr='')

    def run_job(self, child=None, **kwargs):
        with patch.object(module, 'execute', side_effect=child or self.child) as execute:
            result = module.run(self.root, self.jobs, **kwargs)
        return result, execute

    def test_os_process_clock_does_not_invent_scheduler_event(self):
        result, execute = self.run_job()
        self.assertEqual(result['health'], 'RESULT_VALID')
        argv = execute.call_args.args[0]
        self.assertEqual(argv[argv.index('--trigger-kind') + 1], 'MANUAL')
        self.assertNotIn('--trigger-at', argv)
        start = module.read_json(next(self.jobs.glob('attempts/*/started.json')))
        self.assertEqual(start['trigger_evidence'], 'PROCESS_START_ONLY')
        self.assertIsNone(start['scheduler_event_at'])
        self.assertEqual(result['notification']['delivery_status'], 'NOT_SENT_BY_THIS_TOOL')

    def test_actual_scheduler_event_is_preserved_and_future_event_rejected(self):
        event = module.stamp(self.cutoff + timedelta(minutes=1))
        result, execute = self.run_job(scheduler_event_at=event)
        argv = execute.call_args.args[0]
        self.assertEqual(argv[argv.index('--trigger-at') + 1], event)
        self.assertTrue(result['result_valid'])
        invalid, blocked = self.run_job(scheduler_event_at=module.stamp(self.clock + timedelta(seconds=1)))
        self.assertEqual(invalid['health'], 'FAILED_PREFLIGHT')
        blocked.assert_not_called()
        with self.assertRaises(ValueError):
            module.run(self.root, self.jobs, scheduler_event_at='not-a-clock-private-input')
        self.assertNotIn('not-a-clock-private-input', ''.join(p.read_text() for p in self.jobs.glob('attempts/*/*.json')))

    def test_clean_child_environment_and_windowless_launch(self):
        with patch.dict(os.environ, {'PYTHONPATH': 'bad_path', 'PYTHONHOME': 'bad_home'}), patch.object(module.subprocess, 'run') as run:
            module.execute(['fake-python', 'fake-script'], self.root)
        options = run.call_args.kwargs
        self.assertNotIn('PYTHONPATH', options['env'])
        self.assertNotIn('PYTHONHOME', options['env'])
        self.assertEqual(options['env']['PYTHONUTF8'], '1')
        if os.name == 'nt':
            self.assertEqual(options['creationflags'], subprocess.CREATE_NO_WINDOW)

    def test_exit_zero_expired_result_does_not_report_health(self):
        result, _ = self.run_job(lambda argv, root: self.child(argv, root, old=True))
        self.assertEqual(result['health'], 'EXIT_ZERO_RESULT_INVALID')
        self.assertFalse(result['result_valid'])
        self.assertEqual(result['notification']['decision'], 'NOTIFY')

    def test_offline_connect_failure_is_not_success_and_error_text_is_sanitized(self):
        result, _ = self.run_job(lambda *_: SimpleNamespace(returncode=1, stdout='', stderr='secret-key-and-private-path'))
        self.assertEqual(result['health'], 'CHILD_FAILED')
        self.assertFalse(result['result_valid'])
        self.assertNotIn('secret-key', json.dumps(result))
        self.assertEqual(result['child_exit_code'], 1)

    def test_terminated_child_retains_exit_status(self):
        result, _ = self.run_job(lambda *_: SimpleNamespace(returncode=-15, stdout='', stderr=''))
        self.assertEqual(result['health'], 'CHILD_TERMINATED')
        self.assertEqual(result['child_exit_code'], -15)

    def test_child_start_failure_has_ended_launcher_receipt(self):
        result, _ = self.run_job(lambda *_: (_ for _ in ()).throw(OSError('private failure')))
        self.assertEqual(result['health'], 'CHILD_START_OR_WAIT_FAILED')
        self.assertEqual(len(list(self.jobs.glob('attempts/*/ended.json'))), 1)
        self.assertIsNone(result['child_exit_code'])
        self.assertNotIn('private failure', json.dumps(result))

    def test_duplicate_cutoff_preserves_driver_bytes_and_does_not_repeat_notification(self):
        first, _ = self.run_job()
        path = next(self.root.glob('forward/cycles/*/forward_cycle_fixed.json'))
        original = path.read_bytes()
        second, _ = self.run_job(lambda argv, root: self.child(argv, root, duplicate=True))
        self.assertEqual(second['health'], 'DUPLICATE_VERIFY')
        self.assertEqual(second['notification']['decision'], 'DONT_NOTIFY')
        self.assertEqual(original, path.read_bytes())
        self.assertNotEqual(first['attempt_id'], second['attempt_id'])
        self.assertEqual(len(list(self.jobs.glob('attempts/*/started.json'))), 2)

    def test_frozen_lock_duplicate_has_no_valid_result_claim(self):
        value = module.sealed({'status': 'DUPLICATE_IN_FLIGHT', 'input_cutoff': module.stamp(self.cutoff),
                               'plan_hash': module.PLAN_SHA256, 'order_allowed': False})
        result, _ = self.run_job(lambda *_: SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr=''))
        self.assertEqual(result['health'], 'DUPLICATE_IN_FLIGHT')
        self.assertFalse(result['result_valid'])
        self.assertEqual(result['notification']['decision'], 'DONT_NOTIFY')

    def test_outside_window_new_missing_is_computed_and_not_repeated(self):
        self.missing = [{'cutoff': '2026-09-09T00:00:00Z', 'missing_plan_hashes': ['a' * 64, 'b' * 64]}]
        first, _ = self.run_job()
        self.assertEqual(len(first['new_missing_strategy_hours']), 2)
        self.assertIn('new_missing_strategy_hours_including_outside_frozen_window', first['notification']['reasons'])
        second, _ = self.run_job(lambda argv, root: self.child(argv, root, duplicate=True))
        self.assertEqual(second['new_missing_strategy_hours'], [])
        self.assertEqual(second['notification']['decision'], 'DONT_NOTIFY')

    def test_prior_start_without_end_is_not_reported_as_past_success(self):
        module.write_new(self.jobs / 'attempts/prior/started.json', module.sealed({'attempt_id': 'prior', 'input_cutoff': module.stamp(self.cutoff - timedelta(hours=1))}))
        result, _ = self.run_job()
        self.assertEqual(result['prior_unfinished_attempts'], ['prior'])
        self.assertIn('prior_start_without_end', result['notification']['reasons'])
        again, _ = self.run_job(lambda argv, root: self.child(argv, root, duplicate=True))
        self.assertEqual(again['prior_unfinished_attempts'], ['prior'])
        self.assertEqual(again['new_unfinished_attempts'], [])
        self.assertNotIn('prior_start_without_end', again['notification']['reasons'])

    def test_two_launchers_share_exclusion_lock(self):
        entered, release = threading.Event(), threading.Event()
        results = []
        def slow(argv, root):
            entered.set()
            self.assertTrue(release.wait(5))
            return self.child(argv, root)
        with patch.object(module, 'execute', side_effect=slow) as execute:
            thread = threading.Thread(target=lambda: results.append(module.run(self.root, self.jobs)))
            thread.start()
            self.assertTrue(entered.wait(5))
            duplicate = module.run(self.root, self.jobs)
            release.set()
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(duplicate['health'], 'DUPLICATE_IN_FLIGHT')
        self.assertEqual(execute.call_count, 1)
        self.assertTrue(results[0]['result_valid'])

    def test_changed_pinned_deployment_blocks_before_child(self):
        with patch.object(module, 'verify_deployment', side_effect=ValueError('changed')):
            result, execute = self.run_job()
        self.assertEqual(result['health'], 'FAILED_PREFLIGHT')
        execute.assert_not_called()

    def test_forged_receipt_and_late_hour_start_fail_closed(self):
        def tampered(argv, root):
            child = self.child(argv, root)
            value = json.loads(child.stdout)
            value['observations'] = 99
            child.stdout = json.dumps(value)
            return child
        result, _ = self.run_job(tampered)
        self.assertEqual(result['health'], 'EXIT_ZERO_RESULT_INVALID')
        self.clock = self.cutoff + timedelta(minutes=55)
        result, execute = self.run_job()
        self.assertEqual(result['health'], 'FAILED_PREFLIGHT')
        execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
