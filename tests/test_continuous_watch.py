"""Local observation and interrupted-submission recovery, without network I/O."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_continuous_runtime as fixtures
from hakimi_research.documents import canonical_bytes,read_document
from hakimi_research.continuous_runtime import describe_continuous_account,set_continuous_task_state
from hakimi_research.continuous_watch import (configure_watch,LocalInputWatcher,describe_watch,
    discard_uncommitted_pending,recover_watch_pending,start_watch,stop_watch)
from hakimi_research.task_manager import change_state
from hakimi_research import continuous_watch as watch_module


class ContinuousWatchTests(unittest.TestCase):
    def setUp(self):
        self.factory=fixtures.ContinuousRuntimeTests();self.factory.setUp()
        self.addCleanup(self.factory.tearDown)
        self.root=self.factory.root;self.task=self.factory.task(managed=True)
        self.account=self.factory.account(tasks=[self.task]);self.input=self.root/'inbox'/'TEST.json';self.input.parent.mkdir()
        self.input.write_bytes(canonical_bytes(self.factory.data.document))
        self.watch_dir=self.root/'watch'
        configure_watch(self.watch_dir,self.account,{self.factory.security:self.input},interval_seconds=1,
            max_data_age_seconds=30*86400,task_files=[self.task])
        self.watcher=LocalInputWatcher(self.watch_dir,clock=lambda:fixtures.OBSERVED)
        self.addCleanup(self.watcher.stop)
    def ready(self):
        self.assertEqual(self.watcher.poll_once()['status'],'WAITING_STABLE_INPUT')
        return self.watcher.poll_once()
    def view(self):return describe_continuous_account(self.account)

    def test_configure_and_restart_never_start_threads_stable_reads_advance_once(self):
        self.assertFalse(describe_watch(self.watch_dir)['monitoring'])
        self.assertEqual(self.ready()['status'],'CURRENT')
        self.assertEqual(self.view()['continuous']['last_session'],'2024-12-03')
        sequence=self.view()['sequence']
        self.assertEqual(self.watcher.poll_once()['status'],'CURRENT')
        self.assertEqual(self.view()['sequence'],sequence)
        restarted=LocalInputWatcher(self.watch_dir,clock=lambda:fixtures.OBSERVED)
        self.assertEqual(restarted.describe()['observation_state'],'STOPPED')
        self.assertEqual(restarted.poll_once()['status'],'WAITING_STABLE_INPUT')
        self.assertEqual(restarted.poll_once()['status'],'CURRENT')
        self.assertEqual(self.view()['sequence'],sequence)

    def test_missing_stale_and_wrong_security_do_not_create_fake_protection(self):
        self.input.rename(self.root/'saved-input.json')
        state=self.watcher.poll_once();self.assertEqual(state['status'],'INPUT_MISSING');self.assertIn('protection cannot',state['reason'])
        self.assertEqual(self.view()['sequence'],0)
        self.input.write_bytes(canonical_bytes(self.factory.data.document));self.watcher.poll_once()
        state=self.watcher.poll_once(now='2025-02-01T00:00:00Z');self.assertEqual(state['status'],'INPUT_STALE')
        self.assertEqual(self.view()['sequence'],0)
        self.input.write_bytes(canonical_bytes(fixtures.snapshot(symbol='OTHER').document))
        self.assertEqual(self.watcher.poll_once()['status'],'INPUT_ERROR')
        self.assertEqual(self.view()['sequence'],0)

    def test_prefix_revision_is_rejected_and_later_valid_file_can_resume(self):
        self.ready();before=self.view()
        revised=fixtures.snapshot(changes={'2024-11-08':[105,106,104,105,10000]})
        self.input.write_bytes(canonical_bytes(revised.document));self.watcher.poll_once()
        self.assertEqual(self.watcher.poll_once()['status'],'INPUT_REJECTED')
        self.assertEqual(self.view()['state']['positions'],before['state']['positions'])
        self.assertEqual(self.watcher.poll_once()['status'],'INPUT_REJECTED')
        self.input.write_bytes(canonical_bytes(self.factory.data.document));self.watcher.poll_once()
        self.assertEqual(self.watcher.poll_once()['status'],'CURRENT')

    def test_response_loss_reopens_pending_receipt_without_resubmission(self):
        self.watcher.poll_once();original=watch_module.transact_shared_account
        def commit_then_lose(*args,**kwargs):
            original(*args,**kwargs);raise RuntimeError('response lost after durable commit')
        with patch.object(watch_module,'transact_shared_account',commit_then_lose):
            state=self.watcher.poll_once()
        self.assertEqual(state['status'],'SUBMISSION_UNKNOWN')
        pending=read_document(self.watch_dir/'pending.json');self.assertIsNotNone(pending)
        sequence=self.view()['sequence']
        reopened=LocalInputWatcher(self.watch_dir,clock=lambda:fixtures.OBSERVED)
        with patch.object(watch_module,'transact_shared_account',side_effect=AssertionError('must look up committed receipt')):
            self.assertEqual(reopened.poll_once()['status'],'CURRENT')
        self.assertEqual(self.view()['sequence'],sequence)
        self.assertIsNone(read_document(self.watch_dir/'pending.json')['operation_id'])

    def test_explicit_recovery_uses_committed_receipt_and_stays_stopped(self):
        self.watcher.poll_once();original=watch_module.transact_shared_account
        def commit_then_lose(*args,**kwargs):
            original(*args,**kwargs);raise RuntimeError('response lost after durable commit')
        with patch.object(watch_module,'transact_shared_account',commit_then_lose):
            self.assertEqual(self.watcher.poll_once()['status'],'SUBMISSION_UNKNOWN')
        pending=read_document(self.watch_dir/'pending.json')['operation_id']
        committed=self.view()['history'][0]
        owner=next(iter(self.view()['continuous']['task_paused']))
        set_continuous_task_state(self.account,owner,True,operation_id='later-manual-control')
        sequence=self.view()['sequence']
        with patch.object(watch_module,'transact_shared_account',side_effect=AssertionError('receipt must be reused')):
            recovered=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now=fixtures.OBSERVED)
        self.assertEqual(recovered['status'],'CURRENT')
        self.assertEqual(recovered['receipt_hash'],committed['receipt_hash'])
        self.assertFalse(recovered['pending_present'])
        self.assertFalse(recovered['monitoring'])
        self.assertEqual(self.view()['sequence'],sequence)
        self.assertIsNone(read_document(self.watch_dir/'pending.json')['operation_id'])

    def test_crash_after_pending_pointer_is_visible_and_explicitly_resumes_same_request(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=KeyboardInterrupt('process stopped')):
            with self.assertRaises(KeyboardInterrupt):self.watcher.poll_once()
        pending=read_document(self.watch_dir/'pending.json')['operation_id']
        reopened=describe_watch(self.watch_dir)
        self.assertTrue(reopened['pending_present'])
        self.assertEqual(reopened['pending_operation_id'],pending)
        self.assertEqual(reopened['status'],'SUBMISSION_UNKNOWN')
        self.assertFalse(reopened['monitoring'])
        with self.assertRaisesRegex(ValueError,'explicit_recovery'):
            start_watch(self.watch_dir)
        with patch.object(watch_module,'transact_shared_account',wraps=watch_module.transact_shared_account) as submit:
            result=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now=fixtures.OBSERVED)
        self.assertEqual(submit.call_count,1)
        self.assertEqual(submit.call_args.kwargs['operation_id'],pending)
        self.assertEqual(result['status'],'CURRENT')
        self.assertFalse(result['monitoring'])
        self.assertEqual(self.view()['history'][0]['operation_id'],pending)

    def test_explicit_recovery_keeps_expired_or_changed_control_pending_for_review(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):
            self.assertEqual(self.watcher.poll_once()['status'],'SUBMISSION_UNKNOWN')
        pending=read_document(self.watch_dir/'pending.json')['operation_id']
        with patch.object(watch_module,'transact_shared_account',side_effect=AssertionError('stale must not submit')):
            stale=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now='2025-02-01T00:00:00Z')
        self.assertEqual(stale['status'],'PENDING_REVIEW_REQUIRED')
        self.assertTrue(stale['pending_present'])
        owner=next(iter(self.view()['continuous']['task_paused']))
        set_continuous_task_state(self.account,owner,True,operation_id='manual-control-change')
        with patch.object(watch_module,'transact_shared_account',wraps=watch_module.transact_shared_account) as guarded:
            changed=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now=fixtures.OBSERVED)
        self.assertEqual(guarded.call_count,1)
        self.assertEqual(changed['status'],'PENDING_REVIEW_REQUIRED')
        self.assertIn('receipt head changed',changed['reason'])
        self.assertEqual(self.view()['sequence'],1)
        self.assertEqual(read_document(self.watch_dir/'pending.json')['operation_id'],pending)

    def test_control_receipt_inserted_after_precheck_is_rejected_in_write_transaction(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):
            self.watcher.poll_once()
        pending=read_document(self.watch_dir/'pending.json')['operation_id']
        owner=next(iter(self.view()['continuous']['task_paused']))
        original=watch_module.transact_shared_account
        def interleave_control(*args,**kwargs):
            set_continuous_task_state(self.account,owner,True,operation_id='interleaved-manual-control')
            return original(*args,**kwargs)
        with patch.object(watch_module,'transact_shared_account',interleave_control):
            result=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now=fixtures.OBSERVED)
        self.assertEqual(result['status'],'PENDING_REVIEW_REQUIRED')
        self.assertIn('receipt head changed',result['reason'])
        self.assertEqual([r['operation_id'] for r in self.view()['history']],['interleaved-manual-control'])
        self.assertEqual(read_document(self.watch_dir/'pending.json')['operation_id'],pending)
        self.assertFalse(result['monitoring'])

    def test_corrupt_pending_pointer_remains_visible_but_has_no_recoverable_id(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):
            self.watcher.poll_once()
        pending=read_document(self.watch_dir/'pending.json')['operation_id']
        self.watch_dir.joinpath('pending.json').write_bytes(b'{broken')
        view=describe_watch(self.watch_dir)
        self.assertTrue(view['pending_present'])
        self.assertIsNone(view['pending_operation_id'])
        self.assertEqual(view['status'],'SUBMISSION_UNKNOWN')
        with self.assertRaisesRegex(ValueError,'explicit_recovery'):
            start_watch(self.watch_dir)
        with patch.object(watch_module,'transact_shared_account',side_effect=AssertionError('corrupt pointer must not submit')):
            recovered=recover_watch_pending(self.watch_dir,expected_operation_id=pending,now=fixtures.OBSERVED)
        self.assertEqual(recovered['status'],'SUBMISSION_UNKNOWN')
        self.assertIsNone(recovered['pending_operation_id'])
        self.assertEqual(self.view()['sequence'],0)

    def test_explicit_recovery_rejects_running_observation(self):
        start_watch(self.watch_dir)
        self.addCleanup(stop_watch,self.watch_dir)
        with self.assertRaisesRegex(ValueError,'stop_observation_before_pending_recovery'):
            recover_watch_pending(self.watch_dir,expected_operation_id='watch-'+'0'*64,now=fixtures.OBSERVED)

    def test_precommit_failure_retries_only_exact_durable_request(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):
            self.assertEqual(self.watcher.poll_once()['status'],'SUBMISSION_UNKNOWN')
        pending=read_document(self.watch_dir/'pending.json');request=read_document(self.watch_dir/'requests'/(pending['operation_id']+'.json'))
        self.assertEqual(self.view()['sequence'],0)
        reopened=LocalInputWatcher(self.watch_dir,clock=lambda:'2024-12-04T00:05:00Z')
        self.assertEqual(reopened.poll_once()['status'],'CURRENT')
        self.assertEqual(self.view()['history'][0]['operation_id'],pending['operation_id'])
        self.assertEqual(self.view()['history'][0]['request'],request['request'])

    def test_family_pause_after_uncommitted_request_requires_explicit_review(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):self.watcher.poll_once()
        pending=read_document(self.watch_dir/'pending.json');change_state(self.task,'PAUSED')
        reopened=LocalInputWatcher(self.watch_dir,clock=lambda:fixtures.OBSERVED)
        self.assertEqual(reopened.poll_once()['status'],'PENDING_REVIEW_REQUIRED')
        self.assertEqual(self.view()['sequence'],0)
        discard_uncommitted_pending(self.watch_dir,expected_operation_id=pending['operation_id'],reason='User selects current paused controls')
        self.assertEqual(reopened.poll_once()['status'],'WAITING_STABLE_INPUT')
        self.assertEqual(reopened.poll_once()['status'],'CURRENT')
        self.assertEqual(self.view()['cash'],'10000')
        self.assertTrue(all(self.view()['continuous']['task_paused'].values()))

    def test_watcher_honours_family_and_account_pause_without_unpausing_either(self):
        owner=next(iter(self.view()['continuous']['task_paused']))
        set_continuous_task_state(self.account,owner,True,operation_id='manual-pause')
        self.ready();self.assertEqual(self.view()['cash'],'10000')
        self.assertTrue(self.view()['continuous']['manual_task_paused'][owner])
        self.assertFalse(self.view()['continuous']['family_task_paused'][owner])
        change_state(self.task,'PAUSED');self.watcher.poll_once()
        set_continuous_task_state(self.account,owner,False,operation_id='manual-resume')
        self.assertTrue(self.view()['continuous']['task_paused'][owner])
        self.assertEqual(self.watcher.describe()['execution_authority'],'RESEARCH_ONLY_NO_BROKER_OR_ORDERS')

    def test_real_background_thread_observes_append_and_stop_does_not_change_account(self):
        seed=fixtures.snapshot(through='2024-11-11');self.input.write_bytes(canonical_bytes(seed.document))
        self.watcher.start()
        def wait_for(day):
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if self.view()['continuous']['last_session']==day:return
                time.sleep(.1)
            self.fail('watch did not process input: '+str(self.watcher.describe()))
        wait_for('2024-11-11')
        self.input.write_bytes(canonical_bytes(self.factory.data.document));wait_for('2024-12-03')
        stopped=self.watcher.stop();self.assertEqual(stopped['observation_state'],'STOPPED')
        before=self.view()['receipt_head'];time.sleep(.1)
        self.assertEqual(self.view()['receipt_head'],before)
        self.assertFalse(self.view()['state']['paused'])

    def test_expired_uncommitted_pending_never_automatically_replays_old_opportunity(self):
        self.watcher.poll_once()
        with patch.object(watch_module,'transact_shared_account',side_effect=RuntimeError('before commit')):self.watcher.poll_once()
        reopened=LocalInputWatcher(self.watch_dir,clock=lambda:'2025-02-01T00:00:00Z')
        with patch.object(watch_module,'transact_shared_account',side_effect=AssertionError('expired pending must not submit')):
            result=reopened.poll_once()
        self.assertEqual(result['status'],'PENDING_REVIEW_REQUIRED')
        self.assertIn('age window',result['reason'])
        self.assertEqual(self.view()['sequence'],0)

    def test_status_binds_exact_account_and_declared_input_paths(self):
        result=describe_watch(self.watch_dir)
        self.assertEqual(result['account_dir'],str(self.account.resolve()))
        self.assertEqual(result['account_id'],self.view()['account_id'])
        self.assertEqual(result['inputs'],{self.factory.security:str(self.input.resolve())})
        self.assertEqual(result['task_files'],[str(self.task.resolve())])

    def test_older_snapshot_after_progress_does_not_create_unknown_pending_or_rewind(self):
        self.ready();before=self.view()['receipt_head']
        self.input.write_bytes(canonical_bytes(fixtures.snapshot(through='2024-11-11').document))
        self.watcher.poll_once();result=self.watcher.poll_once()
        self.assertEqual(result['status'],'INPUT_REJECTED')
        self.assertIn('committed cursor',result['reason'])
        self.assertIsNone(read_document(self.watch_dir/'pending.json')['operation_id'])
        self.assertEqual(self.view()['receipt_head'],before)


if __name__=='__main__':unittest.main()
