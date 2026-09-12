"""Offline launcher fault tests: every observer child is replaced by a local fake."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
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
        with patch.dict(os.environ, {'PYTHONPATH': 'bad_path', 'PYTHONHOME': 'bad_home'}), patch.object(module, '_run_owned_windows') as run:
            module.execute(['fake-python', 'fake-script'], self.root)
        options = run.call_args.kwargs
        self.assertNotIn('PYTHONPATH', options['environment'])
        self.assertNotIn('PYTHONHOME', options['environment'])
        self.assertEqual(options['environment']['PYTHONUTF8'], '1')
        self.assertEqual(options['timeout_seconds'], 300)
        self.assertEqual(options['output_limit_bytes'], 4 * 1024 * 1024)

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

    @unittest.skipUnless(os.name == 'nt', 'Windows owned-job executor')
    def test_real_timeout_releases_launcher_lock_and_next_cycle_recovers(self):
        real_execute = module.execute
        def timeout_child(argv, root):
            return real_execute([sys.executable, '-I', '-S', '-B', '-c', 'import time; time.sleep(6)'],
                                root, timeout_seconds=0.3)
        failed, _ = self.run_job(timeout_child)
        self.assertEqual(failed['health'], 'CHILD_TIMED_OUT')
        self.assertFalse(failed['result_valid'])
        self.assertTrue(failed['child_execution_bounds']['cleanup_confirmed'])
        self.assertEqual(failed['notification']['decision'], 'NOTIFY')
        self.cutoff += timedelta(hours=1)
        self.clock += timedelta(hours=1)
        recovered, _ = self.run_job()
        self.assertTrue(recovered['result_valid'])
        self.assertIn('recovered_after_failed_result', recovered['notification']['reasons'])

    @unittest.skipUnless(os.name == 'nt', 'Windows owned-job executor')
    def test_real_connection_refusal_is_failed_and_retains_cleanup_evidence(self):
        real_execute = module.execute
        # Keep ownership of a loopback port without listening; no broker/provider
        # address is contacted and another process cannot take the fixture port.
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            port = reserved.getsockname()[1]
            code = 'import socket,sys; socket.create_connection(("127.0.0.1",int(sys.argv[1])),timeout=0.2)'
            def offline_child(argv, root):
                return real_execute([sys.executable, '-I', '-S', '-B', '-c', code, str(port)], root, timeout_seconds=2)
            failed, _ = self.run_job(offline_child)
        self.assertEqual(failed['health'], 'CHILD_FAILED')
        self.assertFalse(failed['result_valid'])
        self.assertTrue(failed['child_execution_bounds']['cleanup_confirmed'])
        self.assertEqual(failed['notification']['decision'], 'NOTIFY')

    @unittest.skipUnless(os.name == 'nt', 'Windows cross-process lock')
    def test_duplicate_from_a_second_process_never_starts_a_second_observer(self):
        ready = self.root / 'lock-holder-ready.txt'
        code = ('import importlib.util,pathlib,sys,time\n'
                'spec=importlib.util.spec_from_file_location("lock_holder",sys.argv[1])\n'
                'module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n'
                'with module.job_lock(pathlib.Path(sys.argv[2])) as acquired:\n'
                ' assert acquired\n'
                ' pathlib.Path(sys.argv[3]).write_text("ready")\n'
                ' time.sleep(6)\n')
        holder = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', code,
                                   str(Path(module.__file__).resolve()), str(self.jobs/'launcher.lock'), str(ready)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 3
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(ready.exists())
            duplicate, execute = self.run_job()
            self.assertEqual(duplicate['health'], 'DUPLICATE_IN_FLIGHT')
            execute.assert_not_called()
        finally:
            holder.kill()
            holder.wait(timeout=3)
        with module.job_lock(self.jobs/'launcher.lock') as acquired:
            self.assertTrue(acquired)


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object behavior')
class OwnedChildProcessTests(unittest.TestCase):
    """Real local finite child processes; no frozen deployment or network calls."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='hakimi-owned-process-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def execute(self, code, *arguments, **options):
        return module.execute([sys.executable, '-X', 'utf8', '-I', '-S', '-B', '-c', code, *map(str, arguments)],
                              self.root, **options)

    def assert_pid_exited(self, pid):
        # Inspect a child-published PID only for liveness; never terminate by PID.
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.WaitForSingleObject.restype = wintypes.DWORD
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle.restype = wintypes.BOOL
        handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE, no terminate right
        if not handle:
            self.assertEqual(ctypes.get_last_error(), 87)  # no such running process
            return
        try:
            self.assertEqual(api.WaitForSingleObject(handle, 2000), 0, 'owned descendant is still running')
        finally:
            api.CloseHandle(handle)

    def test_normal_completion_preserves_output_and_exit_status(self):
        result = self.execute('import os; os.write(1,b"ok\\n"); os.write(2,b"diagnostic\\n"); raise SystemExit(7)')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, 'ok\n', 'diagnostic\n'))
        self.assertEqual(result.bounds['outcome'], 'EXITED')
        self.assertTrue(result.bounds['cleanup_confirmed'])

    def test_hang_is_bounded_and_output_limit_is_combined_while_streaming(self):
        started = time.monotonic()
        result = self.execute('import time; time.sleep(6)', timeout_seconds=0.3)
        self.assertEqual(result.bounds['outcome'], 'TIMED_OUT')
        self.assertTrue(result.bounds['cleanup_confirmed'])
        self.assertLess(time.monotonic() - started, 3)
        code = 'import os\nfor _ in range(200):\n os.write(1,b"x"*512); os.write(2,b"y"*512)'
        result = self.execute(code, output_limit_bytes=1024, timeout_seconds=2)
        self.assertEqual(result.bounds['outcome'], 'OUTPUT_LIMIT')
        self.assertLessEqual(sum(result.bounds['bytes_retained'].values()), 1024)
        self.assertGreater(sum(result.bounds['bytes_seen'].values()), 1024)
        self.assertTrue(result.bounds['output_truncated'])
        self.assertTrue(result.bounds['cleanup_confirmed'])

    def test_descendants_are_reaped_even_when_their_parent_exits_zero(self):
        child = 'import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(6)'
        for close_output in (False, True):
            with self.subTest(close_output=close_output):
                marker = self.root / ('descendant-' + str(close_output) + '.txt')
                code = ('import pathlib,subprocess,sys,time\n'
                        'options = {"stdout":subprocess.DEVNULL,"stderr":subprocess.DEVNULL} if sys.argv[3]=="True" else {}\n'
                        'subprocess.Popen([sys.executable,"-I","-S","-B","-c",sys.argv[2],sys.argv[1]],**options)\n'
                        'deadline=time.monotonic()+3\n'
                        'while not pathlib.Path(sys.argv[1]).exists() and time.monotonic()<deadline: time.sleep(0.01)\n')
                result = self.execute(code, marker, child, close_output, timeout_seconds=4)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.bounds['outcome'], 'LEFTOVER_DESCENDANTS')
                self.assertTrue(result.bounds['cleanup_confirmed'])
                self.assert_pid_exited(int(marker.read_text()))

    def test_failed_job_assignment_never_starts_the_observer(self):
        marker = self.root / 'must-not-start.txt'
        with patch.object(module._WindowsJob, 'assign', side_effect=OSError('injected assignment failure')):
            with self.assertRaises(OSError):
                self.execute('import pathlib,sys; pathlib.Path(sys.argv[1]).touch()', marker)
        self.assertFalse(marker.exists())

    def test_timeout_does_not_terminate_an_unrelated_process(self):
        other = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', 'import time; time.sleep(6)'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            result = self.execute('import time; time.sleep(6)', timeout_seconds=0.3)
            self.assertTrue(result.bounds['cleanup_confirmed'])
            self.assertIsNone(other.poll())
        finally:
            other.kill()  # this test's own Popen handle, outside the executor job
            other.wait(timeout=3)

    def test_abrupt_launcher_exit_releases_descendant_lock(self):
        lock, ready = self.root / 'child.lock', self.root / 'child-ready.txt'
        child = ('import msvcrt,os,pathlib,sys,time\n'
                 'stream=open(sys.argv[1],"w+b"); stream.write(b"0"); stream.flush(); stream.seek(0)\n'
                 'msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)\n'
                 'pathlib.Path(sys.argv[2]).write_text(str(os.getpid()))\n'
                 'time.sleep(6)\n')
        driver = ('import importlib.util,pathlib,sys\n'
                  'spec=importlib.util.spec_from_file_location("owned_driver",sys.argv[1])\n'
                  'module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n'
                  'module.execute([sys.executable,"-I","-S","-B","-c",sys.argv[2],sys.argv[3],sys.argv[4]],pathlib.Path(sys.argv[3]).parent)\n')
        launcher = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', driver,
                                     str(Path(module.__file__).resolve()), child, str(lock), str(ready)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 3
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(ready.exists(), 'fixture never acquired its lock')
            launcher.kill()  # stable handle for the launcher created by this test
            launcher.wait(timeout=3)
            self.assert_pid_exited(int(ready.read_text()))
            with module.job_lock(lock) as acquired:
                self.assertTrue(acquired, 'descendant lock survived launcher termination')
        finally:
            if launcher.poll() is None:
                launcher.kill()
                launcher.wait(timeout=3)

    def test_invalid_utf8_and_invalid_bounds_cannot_be_accepted(self):
        result = self.execute('import os; os.write(1,b"\\xff")')
        self.assertEqual(result.bounds['outcome'], 'OUTPUT_ENCODING_INVALID')
        for options in ({'timeout_seconds':float('inf')}, {'timeout_seconds':True},
                        {'output_limit_bytes':0}, {'cleanup_seconds':-1}):
            with self.subTest(options=options), patch.object(module, '_run_owned_windows') as run:
                with self.assertRaises(ValueError):
                    self.execute('print("not run")', **options)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
