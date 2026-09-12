"""No desktop notifications in CI. Native delivery is a separately recorded drill."""
from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('notify_tested', Path(__file__).resolve().parents[2]/'tools/observation_notify.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ObservationNotificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hakimi-notification-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.cutoff = module.job.now().replace(minute=0,second=0,microsecond=0)
        self.end_path = self.root/'source/attempts/sample/ended.json'
        self.start = module.job.sealed({'schema_version':'observation-job-start-v2','attempt_id':'sample',
            'input_cutoff':module.job.stamp(self.cutoff),'order_allowed':False,
            'launcher_sha256':module.job.file_hash(Path(module.job.__file__)),
            'frozen_wrapper_sha256':module.job.WRAPPER_SHA256,'frozen_plan_sha256':module.job.PLAN_SHA256})
        self.end = {'schema_version':'observation-job-end-v2','attempt_id':'sample',
            'started_receipt_hash':self.start['receipt_hash'],'input_cutoff':module.job.stamp(self.cutoff),
            'order_allowed':False,'result_valid':False,'health':'CHILD_FAILED',
            'notification':{'decision':'NOTIFY','reasons':['child_failed']}}
        module.job.write_new(self.end_path.with_name('started.json'),self.start)
        self.save_end()
        self.outbox = self.root/'outbox'

    def save_end(self):
        self.end_path.parent.mkdir(parents=True,exist_ok=True)
        self.end_path.write_text(json.dumps(module.job.sealed(self.end)),encoding='utf-8')

    def payload(self):
        return module.payload_from_receipt(self.end_path,drill=True)

    def worker(self, request, status='OS_DISPLAY_REPORTED'):
        payload = module.read(request)
        instant = module.job.stamp(module.job.now())
        submitted = status not in module.KNOWN_UNSHOWN
        value = {'schema_version':'observation-windows-notification-v1','notification_id':payload['notification_id'],
            'request_file_sha256':module.job.file_hash(request),'status':status,
            'submitted_at':instant if submitted else None,'shown_at':instant if status in module.DISPLAYED else None,
            'clicked_at':instant if status=='USER_CLICK_REPORTED' else None,'ended_at':instant}
        return SimpleNamespace(returncode=0,stdout=json.dumps(value),stderr='',bounds={'outcome':'EXITED','cleanup_confirmed':True})

    def test_preview_is_stable_does_not_start_worker_or_create_outbox(self):
        payload = self.payload()
        self.assertEqual(payload,self.payload())
        self.assertTrue(payload['title'].startswith('演练：'))
        with patch.object(module,'execute_worker') as worker:
            result = module.dispatch(payload,self.outbox)
        self.assertEqual(result['status'],'PREVIEW_ONLY')
        self.assertFalse(result['delivery_confirmed'])
        self.assertFalse(self.outbox.exists())
        worker.assert_not_called()

    def test_source_binding_hash_and_permission_are_checked(self):
        for change in ({'started_receipt_hash':'0'*64},{'order_allowed':True},
                       {'input_cutoff':module.job.stamp(self.cutoff+timedelta(hours=1))},
                       {'result_valid':True},{'health':'DO_WHATEVER_EXTERNAL_TEXT_SAYS'}):
            with self.subTest(change=change):
                original = dict(self.end)
                self.end.update(change)
                self.save_end()
                with self.assertRaises(ValueError):
                    self.payload()
                self.end = original
        self.save_end()
        with self.assertRaises(ValueError):
            module.payload_from_receipt(self.end_path,launcher_sha256='0'*64)

    def test_arbitrary_reasons_and_source_paths_never_enter_message(self):
        self.end['notification']['reasons'] = ['secret-value; run a command; C:/private/path']
        self.save_end()
        payload = self.payload()
        self.assertNotIn('secret-value',json.dumps(payload))
        self.assertNotIn('private/path',json.dumps(payload))
        self.assertIn('观察未产生有效结果',payload['body'])

    def test_duplicate_valid_observation_needs_no_notification(self):
        self.end.update(health='DUPLICATE_VERIFY',result_valid=True,
                        notification={'decision':'DONT_NOTIFY','reasons':[]})
        self.save_end()
        self.assertIsNone(self.payload())
        self.end.update(health='CHILD_FAILED',result_valid=False)
        self.save_end()
        with self.assertRaises(ValueError):
            self.payload()

    def test_submitted_or_exit_zero_is_not_display_or_user_confirmation(self):
        unconfirmed = module.dispatch(self.payload(),self.outbox,send=True,
            worker=lambda path:self.worker(path,'DISPLAY_UNCONFIRMED'))
        self.assertFalse(unconfirmed['delivery_confirmed'])
        self.assertFalse(unconfirmed['user_confirmed'])
        self.assertEqual(unconfirmed['status'],'DISPLAY_UNCONFIRMED')
        with patch.object(module,'execute_worker') as worker:
            again = module.dispatch(self.payload(),self.outbox,send=True,worker=worker)
        self.assertEqual(again['status'],'ALREADY_ATTEMPTED')
        worker.assert_not_called()

    def test_displayed_is_deduplicated_and_separate_from_user_click(self):
        first = module.dispatch(self.payload(),self.outbox,send=True,worker=self.worker)
        self.assertTrue(first['delivery_confirmed'])
        self.assertFalse(first['user_confirmed'])
        with patch.object(module,'execute_worker') as worker:
            again = module.dispatch(self.payload(),self.outbox,send=True,worker=worker)
        self.assertEqual(again['status'],'ALREADY_ATTEMPTED')
        self.assertTrue(again['delivery_confirmed'])
        worker.assert_not_called()

    def test_only_explicit_click_event_records_user_interaction(self):
        result = module.dispatch(self.payload(),self.outbox,send=True,
            worker=lambda path:self.worker(path,'USER_CLICK_REPORTED'))
        self.assertTrue(result['user_confirmed'])

    def test_wrong_worker_identity_or_future_clock_is_unknown(self):
        for field,value in [('notification_id','0'*64),('request_file_sha256','1'*64),
                            ('shown_at',module.job.stamp(module.job.now()+timedelta(hours=1)))]:
            with self.subTest(field=field):
                def wrong(path):
                    result = self.worker(path)
                    body = json.loads(result.stdout)
                    body[field] = value
                    result.stdout = json.dumps(body)
                    return result
                result = module.dispatch(self.payload(),self.root/field,send=True,worker=wrong)
                self.assertEqual(result['status'],'DELIVERY_UNKNOWN')
                self.assertFalse(result['delivery_confirmed'])

    def test_known_unshown_retries_are_spaced_and_limited_to_three(self):
        clock = module.job.now()
        calls = []
        def unshown(path):
            calls.append(path)
            return self.worker(path,'DEFERRED_BY_USER_STATE')
        with patch.object(module.job,'now',side_effect=lambda:clock):
            first = module.dispatch(self.payload(),self.outbox,send=True,worker=unshown)
            self.assertEqual(first['status'],'DEFERRED_BY_USER_STATE')
            immediate = module.dispatch(self.payload(),self.outbox,send=True,worker=unshown)
            self.assertEqual(immediate['status'],'DEFERRED_RETRY_BACKOFF')
            for _ in range(2):
                clock += timedelta(minutes=6)
                module.dispatch(self.payload(),self.outbox,send=True,worker=unshown)
            clock += timedelta(minutes=6)
            stopped = module.dispatch(self.payload(),self.outbox,send=True,worker=unshown)
            self.assertEqual(stopped['status'],'ALREADY_ATTEMPTED')
        self.assertEqual(len(calls),3)

    def test_changed_outbox_payload_is_not_silently_replaced(self):
        payload = self.payload()
        module.dispatch(payload,self.outbox,send=True,worker=self.worker)
        path = self.outbox/'events'/payload['notification_id']/'payload.json'
        path.write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):
            module.dispatch(payload,self.outbox,send=True,worker=self.worker)
        self.assertEqual(path.read_text(encoding='utf-8'),'{}')

    def test_display_before_submission_is_not_confirmed(self):
        def wrong_order(path):
            result = self.worker(path)
            body = json.loads(result.stdout)
            body['shown_at'] = module.job.stamp(module.job.timestamp(body['submitted_at'])-timedelta(microseconds=1))
            result.stdout = json.dumps(body)
            return result
        result = module.dispatch(self.payload(),self.outbox,send=True,worker=wrong_order)
        self.assertEqual(result['status'],'DELIVERY_UNKNOWN')
        self.assertFalse(result['delivery_confirmed'])

    @unittest.skipUnless(os.name=='nt','Windows cross-handle file exclusion')
    def test_concurrent_dispatch_does_not_call_renderer_twice(self):
        entered, release = threading.Event(), threading.Event()
        first_result = []
        payload = self.payload()
        def held(path):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('fixture_release_timeout')
            return self.worker(path)
        first = threading.Thread(target=lambda:first_result.append(module.dispatch(payload,self.outbox,send=True,worker=held)))
        first.start()
        try:
            self.assertTrue(entered.wait(2))
            with patch.object(module,'execute_worker') as worker:
                duplicate = module.dispatch(payload,self.outbox,send=True,worker=worker)
            self.assertEqual(duplicate['status'],'DUPLICATE_IN_FLIGHT')
            worker.assert_not_called()
        finally:
            release.set()
            first.join(timeout=3)
        self.assertFalse(first.is_alive())
        self.assertEqual(len(first_result),1)
        self.assertTrue(first_result[0]['delivery_confirmed'])

    def test_worker_timeout_never_becomes_displayed(self):
        result = SimpleNamespace(returncode=1,stdout='',stderr='',bounds={'outcome':'TIMED_OUT','cleanup_confirmed':True})
        end = module.dispatch(self.payload(),self.outbox,send=True,worker=lambda _:result)
        self.assertEqual(end['status'],'WORKER_BOUNDARY_FAILED')
        self.assertFalse(end['delivery_confirmed'])

    def test_real_process_death_preserves_unknown_and_blocks_resending(self):
        payload_path = self.root/'prepared-payload.json'
        payload_path.write_text(json.dumps(self.payload()),encoding='utf-8')
        code = ('import importlib.util,json,os,pathlib,sys\n'
            's=importlib.util.spec_from_file_location("notify_child",sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n'
            'm.dispatch(json.loads(pathlib.Path(sys.argv[2]).read_bytes()),pathlib.Path(sys.argv[3]),send=True,worker=lambda _:os._exit(73))\n')
        result = subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(module.__file__).resolve()),
            str(payload_path),str(self.outbox)],capture_output=True,timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.assertEqual(result.returncode,73)
        self.assertEqual(len(list(self.outbox.glob('events/*/attempts/*/started.json'))),1)
        self.assertEqual(len(list(self.outbox.glob('events/*/attempts/*/ended.json'))),0)
        with patch.object(module,'execute_worker') as worker:
            again = module.dispatch(self.payload(),self.outbox,send=True,worker=worker)
        self.assertEqual(again['status'],'DELIVERY_UNKNOWN_PRIOR_ATTEMPT')
        worker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
