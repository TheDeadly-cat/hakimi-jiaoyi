"""Receipt-only supervision fixtures; no market requests, task registration or UI."""
from datetime import datetime,timedelta,timezone
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('watch_tested',Path(__file__).resolve().parents[2]/'tools/observation_watch.py')
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
PLANS=['61aa420de8ad2ae886c31d3ee323393e6a21205fbb222841325d30614e2d6b0c',
       '8b371b08d8967198dc9d0f0956e7e0da8c5cc639c7d97a27818522b7a09815d5']


class ObservationWatchTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='hakimi-watch-test-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        self.jobs,self.watch=self.root/'jobs',self.root/'watch'
        self.cutoff=datetime(2026,9,13,1,tzinfo=timezone.utc)
        self.clock=self.cutoff+timedelta(minutes=10)
        clock_patch=patch.object(module.job,'now',side_effect=lambda:self.clock)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.plan=module.build_plan(module.job.stamp(self.cutoff),2,scope='ISOLATED_DRILL')

    def attempt(self, name='first', *, complete=True, valid=True, late=False, duplicate=False, cutoff=None, start_minute=1):
        cutoff=cutoff or self.cutoff
        directory=self.jobs/'attempts'/name
        start=module.job.sealed({'schema_version':'observation-job-start-v2','attempt_id':name,
            'input_cutoff':module.job.stamp(cutoff),'launcher_function_started_at':module.job.stamp(cutoff+timedelta(minutes=start_minute)),
            'launcher_sha256':self.plan['expected_launcher_sha256'],'frozen_wrapper_sha256':module.job.WRAPPER_SHA256,
            'frozen_plan_sha256':module.job.PLAN_SHA256,'order_allowed':False})
        module.job.write_new(directory/'started.json',start)
        if complete:
            signal=cutoff+timedelta(minutes=7 if late else 2)
            records=[{'plan_hash':p,'record_hash':module.job.digest({'cutoff':module.job.stamp(cutoff),'plan':p}),
                      'cutoff':module.job.stamp(cutoff),'signal_available_at':module.job.stamp(signal),
                      'timing_status':'LATE' if late else 'ON_TIME'} for p in PLANS]
            end=module.job.sealed({'schema_version':'observation-job-end-v2','attempt_id':name,'started_receipt_hash':start['receipt_hash'],
                'input_cutoff':module.job.stamp(cutoff),'launcher_record_ended_at':module.job.stamp(max(signal,cutoff+timedelta(minutes=start_minute))+timedelta(seconds=1)),
                'order_allowed':False,'result_valid':valid,
                'health':'DUPLICATE_IN_FLIGHT' if duplicate else 'LATE' if valid and late else 'RESULT_VALID' if valid else 'CHILD_FAILED',
                'child_exit_code':0 if valid else 1,
                'child_execution_bounds':{'outcome':'EXITED','cleanup_confirmed':True,'timeout_seconds':300,'cleanup_seconds':5,'output_limit_bytes_combined':4194304},
                'records':records if valid else []})
            module.job.write_new(directory/'ended.json',end)
        return directory

    def check(self, **kwargs):
        return module.check(self.plan,self.jobs,self.watch,**kwargs)

    def worker(self,path,status='OS_DISPLAY_REPORTED'):
        payload=module.read(path)
        instant=module.job.stamp(module.job.now())
        value={'schema_version':'observation-windows-notification-v1','notification_id':payload['notification_id'],
            'request_file_sha256':module.job.file_hash(path),'status':status,'submitted_at':instant,
            'shown_at':instant if status=='OS_DISPLAY_REPORTED' else None,'clicked_at':None,'ended_at':instant}
        return SimpleNamespace(returncode=0,stdout=json.dumps(value),stderr='',bounds={'outcome':'EXITED','cleanup_confirmed':True})

    def test_plan_requires_prospective_72h_for_declared_window(self):
        with self.assertRaises(ValueError):
            module.build_plan(module.job.stamp(self.cutoff),72)
        future=module.job.stamp(self.cutoff+timedelta(hours=1))
        with self.assertRaises(ValueError):
            module.build_plan(future,2)
        plan=module.build_plan(future,72)
        self.assertFalse(plan['plan_is_scheduler_activation'])
        module.verify_plan(plan)

    def test_completely_absent_job_is_reported_once_and_future_is_not_missing(self):
        first=self.check()['report']
        self.assertEqual(first['rows'][0]['current_status'],'NO_START_RECEIPT')
        self.assertEqual(first['rows'][0]['deadline_status'],'MISSING')
        self.assertEqual(first['rows'][1]['current_status'],'PLANNED')
        self.assertEqual(len(first['changes']),1)
        again=self.check()['report']
        self.assertEqual(again['changes'],[])
        self.assertEqual(again['rows'][0]['first_problem_observed_at'],first['rows'][0]['first_problem_observed_at'])

    def test_exact_timely_boundary_still_pending(self):
        rows,changes=module.evaluate(self.plan,[],None,self.cutoff+timedelta(minutes=5))
        self.assertEqual(rows[0]['deadline_status'],'PENDING')
        self.assertEqual(changes,[])

    def test_unfinished_receipt_is_overdue_without_asserting_process_exit(self):
        self.attempt(complete=False)
        row=self.check()['report']['rows'][0]
        self.assertEqual(row['current_status'],'END_RECEIPT_OVERDUE')
        self.assertEqual(row['unfinished_receipts'],1)
        self.assertNotIn('process_exited',row)

    def test_late_receipt_arrival_recovers_but_preserves_original_missing(self):
        first=self.check()['report']
        self.attempt()
        self.clock+=timedelta(minutes=1)
        recovered=self.check()['report']
        row=recovered['rows'][0]
        self.assertEqual(row['current_status'],'ON_TIME')
        self.assertEqual(row['deadline_status'],'MISSING')
        self.assertTrue(row['original_gap_preserved'])
        self.assertEqual(recovered['changes'],[{'cutoff':module.job.stamp(self.cutoff),'kind':'RECOVERY','status':'ON_TIME'}])
        self.assertEqual(module.job.verify_seal(first),first)

    def test_late_observation_is_never_renamed_on_time(self):
        self.attempt(late=True)
        first=self.check()['report']
        self.assertEqual(first['rows'][0]['deadline_status'],'LATE')
        self.assertEqual(first['changes'][0]['kind'],'LATE')
        self.assertEqual(self.check()['report']['changes'],[])

    def test_later_failed_verification_does_not_erase_valid_deadline_evidence(self):
        self.attempt()
        self.attempt('failed-retry',valid=False,start_minute=8)
        row=self.check()['report']['rows'][0]
        self.assertEqual(row['current_status'],'FAILED')
        self.assertEqual(row['deadline_status'],'ON_TIME')
        self.assertEqual(row['valid_result_receipts'],1)

    def test_duplicate_in_flight_is_not_no_start_or_success(self):
        self.attempt(valid=False,duplicate=True)
        row=self.check()['report']['rows'][0]
        self.assertEqual(row['current_status'],'DUPLICATE_ONLY')
        self.assertEqual(row['deadline_status'],'MISSING')
        self.assertEqual(row['start_receipts'],1)

    def test_source_change_or_removal_fails_without_losing_prior_fingerprints(self):
        directory=self.attempt()
        original=(directory/'ended.json').read_bytes()
        first=self.check()['report']
        (directory/'ended.json').unlink()
        failed=self.check()['report']
        self.assertEqual(failed['status'],'SOURCE_OR_CLOCK_UNVERIFIED')
        self.assertEqual(failed['current_counts'],{})
        self.assertFalse(failed['rows_are_current'])
        self.assertEqual(failed['source_file_sha256'],first['source_file_sha256'])
        (directory/'ended.json').write_bytes(original)
        recovered=self.check()['report']
        self.assertEqual(recovered['status'],'VERIFIED_RECEIPT_SCAN')
        self.assertEqual(recovered['changes'][-1]['status'],'SOURCE_CHECK_RECOVERED')

    def test_clock_high_water_survives_multiple_regressed_checks(self):
        first=self.check()['report']
        self.clock-=timedelta(minutes=2)
        second=self.check()['report']
        self.clock+=timedelta(seconds=30)
        third=self.check()['report']
        self.assertEqual(second['status'],third['status'])
        self.assertEqual(third['status'],'SOURCE_OR_CLOCK_UNVERIFIED')
        self.assertEqual(third['maximum_checked_at'],first['maximum_checked_at'])
        self.assertEqual(third['changes'],[])

    def test_wrong_launcher_cannot_be_accepted(self):
        directory=self.attempt()
        wrong=module.read(directory/'started.json')
        wrong.pop('receipt_hash')
        wrong['launcher_sha256']='0'*64
        (directory/'started.json').write_text(json.dumps(module.job.sealed(wrong)),encoding='utf-8')
        self.assertEqual(self.check()['status'],'SOURCE_OR_CLOCK_UNVERIFIED')

    def test_resealed_different_valid_observation_in_same_cutoff_is_rejected(self):
        self.attempt()
        directory=self.attempt('other',start_minute=3)
        other=module.read(directory/'ended.json')
        other.pop('receipt_hash')
        other['records'][0]['record_hash']='0'*64
        (directory/'ended.json').write_text(json.dumps(module.job.sealed(other)),encoding='utf-8')
        self.assertEqual(self.check()['status'],'SOURCE_OR_CLOCK_UNVERIFIED')

    def test_pending_report_recovers_after_publication_interruption(self):
        with patch.object(module,'ensure_pending',side_effect=OSError('injected-after-report-publication')):
            with self.assertRaises(OSError):
                self.check()
        self.assertEqual(len(list((self.watch/'reports').glob('*.json'))),1)
        self.assertEqual(len(list((self.watch/'pending').glob('*.json'))),0)
        self.check()
        self.assertEqual(len(list((self.watch/'pending').glob('*.json'))),1)

    def test_one_delivery_per_scan_and_delivery_unknown_remains_visible(self):
        self.check()
        self.attempt()
        self.clock+=timedelta(minutes=1)
        self.check()
        calls=[]
        def sender(path):
            calls.append(path)
            return self.worker(path,'DISPLAY_UNCONFIRMED')
        first=self.check(send=True,worker=sender)
        self.assertEqual(len(calls),1)
        self.assertEqual(first['notification_state'],{'pending':1,'unconfirmed':1})
        second=self.check(send=True,worker=self.worker)
        self.assertEqual(second['notification_state'],{'pending':0,'unconfirmed':1})
        with patch.object(module.notify,'execute_worker') as no_call:
            third=self.check(send=True,worker=no_call)
        no_call.assert_not_called()
        self.assertEqual(third['notification_state']['unconfirmed'],1)

    def test_resealed_pending_message_cannot_replace_source_derived_content(self):
        self.check()
        path=next((self.watch/'pending').glob('*.json'))
        payload=module.read(path)
        identity=payload.pop('notification_id')
        payload['body']=payload['body'].removesuffix(' 编号 '+identity[:8])+' arbitrary extra instruction'
        new_identity=module.job.digest(payload)
        payload['notification_id']=new_identity
        payload['body']+=' 编号 '+new_identity[:8]
        path.write_text(json.dumps(payload),encoding='utf-8')
        with self.assertRaises(ValueError):
            self.check(send=True,worker=self.worker)


if __name__=='__main__':
    unittest.main()
