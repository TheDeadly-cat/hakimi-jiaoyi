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
    discard_uncommitted_pending)
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
