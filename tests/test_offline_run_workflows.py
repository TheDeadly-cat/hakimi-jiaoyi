"""Actual process interleavings, preparation faults and reopened menu history."""
from contextlib import contextmanager, redirect_stdout
import io
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import offline_app as app
from hakimi_research.trade_cli import initialize_demo, wizard, create_task
from hakimi_research.documents import digest
from hakimi_research.environment import build_runtime_provenance


def paused_original(task, ready, release, results, count, boundary):
    """Spawn-safe worker exercising the installed package's real run path."""
    original_writer = app._save_encoded_report
    original_lock = app.run_lock
    original_strategy = app.run_strategy
    def strategy(*args, **kwargs):
        with count.get_lock():count.value += 1
        return original_strategy(*args, **kwargs)
    def writer(encoded, path):
        result = original_writer(encoded, path)
        if boundary == 'START_RECORD' and Path(path).name == 'started.json':
            manifest = json.loads((Path(path).parent/'inputs.json').read_bytes())
            ready.send(str(Path(path).parent.parent/('run-'+manifest['run_id'])) if Path(path).parent.name.startswith('.preparing-') else str(Path(path).parent))
            if not release.wait(40):raise RuntimeError('test_original_release_timeout')
        return result
    @contextmanager
    def lock(directory):
        if boundary == 'BEFORE_CLAIM':
            ready.send(str(directory))
            if not release.wait(40):raise RuntimeError('test_original_release_timeout')
        with original_lock(directory):yield
    try:
        with patch.object(app,'_save_encoded_report',side_effect=writer),patch.object(app,'run_lock',side_effect=lock),patch.object(app,'run_strategy',side_effect=strategy):
            result=app.run_task(task)
        results.send(('OK',str(result)))
    except BaseException as exc:
        results.send(('ERROR',type(exc).__name__,str(exc)))
    finally:
        ready.close();results.close()


class OfflineRunWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.workspace=self.root/'workspace';initialize_demo(self.workspace)
        self.task=self.workspace/'tasks/price.json'

    def child(self,boundary):
        ctx=multiprocessing.get_context('spawn')
        ready_parent,ready_child=ctx.Pipe(duplex=False)
        result_parent,result_child=ctx.Pipe(duplex=False)
        release=ctx.Event();count=ctx.Value('i',0)
        process=ctx.Process(target=paused_original,args=(str(self.task),ready_child,release,result_child,count,boundary))
        process.start();ready_child.close();result_child.close()
        def cleanup():
            if process.is_alive():release.set()
            process.join(12)
            if process.is_alive():process.terminate();process.join(5)
            ready_parent.close();result_parent.close()
        self.addCleanup(cleanup)
        self.assertTrue(ready_parent.poll(25),'original did not reach test boundary')
        directory=Path(ready_parent.recv())
        self.assertTrue(process.is_alive())
        return process,release,count,result_parent,directory

    def test_live_original_after_start_record_rejects_other_process_recovery(self):
        process,release,count,result,directory=self.child('START_RECORD')
        try:
            self.assertEqual(count.value,0)
            with self.assertRaisesRegex(ValueError,'active_owner'):app.resume_calculation(directory)
            self.assertEqual(count.value,0)
        finally:release.set()
        process.join(15);self.assertFalse(process.is_alive())
        self.assertTrue(result.poll(2));self.assertEqual(result.recv()[0],'OK')
        self.assertEqual(count.value,1)
        original=(directory/'report.json').read_bytes()
        with patch.object(app,'run_strategy',side_effect=AssertionError('saved calculation must not repeat')):
            self.assertEqual(app.resume_calculation(directory)[1],0)
        self.assertEqual((directory/'report.json').read_bytes(),original)

    def test_original_rechecks_saved_result_after_claiming_mutex(self):
        process,release,count,result,directory=self.child('BEFORE_CLAIM')
        original_strategy=app.run_strategy
        def strategy(*args,**kwargs):
            with count.get_lock():count.value+=1
            return original_strategy(*args,**kwargs)
        try:
            with patch.object(app,'run_strategy',side_effect=strategy):self.assertEqual(app.run_task(self.task),directory)
            self.assertEqual(count.value,1)
        finally:release.set()
        process.join(15);self.assertFalse(process.is_alive())
        self.assertTrue(result.poll(2));self.assertEqual(result.recv()[0],'OK')
        self.assertEqual(count.value,1)

    def test_process_exit_during_preparation_retains_partial_files_and_allows_task_retry(self):
        process,release,count,result,directory=self.child('START_RECORD')
        process.terminate();process.join(10);self.assertFalse(process.is_alive())
        self.assertEqual(count.value,0)
        self.assertFalse(directory.exists())
        stages=list(directory.parent.glob('.preparing-run-*'));self.assertEqual(len(stages),1)
        retained={p.relative_to(stages[0]).as_posix():p.read_bytes() for p in stages[0].rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'initialization_not_published'):app.resume_calculation(stages[0])
        saved=app.run_task(self.task);self.assertTrue((saved/'report.json').is_file())
        for name,raw in retained.items():self.assertEqual((stages[0]/name).read_bytes(),raw)

    def test_four_preparation_fault_boundaries_have_consistent_retry_and_recovery(self):
        original_writer=app._save_encoded_report
        original_mkdir=Path.mkdir
        for boundary in ['DIRECTORY','snapshot.json','inputs.json','started.json']:
            with self.subTest(boundary=boundary):
                output=self.root/('fault-'+boundary.replace('.','-'))
                fired=False
                def mkdir(path,*args,**kwargs):
                    nonlocal fired
                    if boundary=='DIRECTORY' and path.name.startswith('.preparing-') and not fired:
                        fired=True;raise OSError('fictional directory creation failure')
                    return original_mkdir(path,*args,**kwargs)
                def writer(encoded,path):
                    nonlocal fired
                    if Path(path).name==boundary and not fired:
                        fired=True;raise OSError('fictional preparation write failure')
                    return original_writer(encoded,path)
                with patch.object(Path,'mkdir',new=mkdir),patch.object(app,'_save_encoded_report',side_effect=writer),patch.object(app,'run_strategy',side_effect=AssertionError('preparation must not calculate')):
                    with self.assertRaisesRegex(ValueError,'initialization_not_published'):app.run_task(self.task,output_dir=output)
                self.assertTrue(fired);self.assertFalse(list(output.glob('run-*')))
                retained={p:p.read_bytes() for stage in output.glob('.preparing-*') for p in stage.rglob('*') if p.is_file()}
                for stage in output.glob('.preparing-*'):
                    with self.assertRaisesRegex(ValueError,'initialization_not_published'):app.resume_calculation(stage)
                saved=app.run_task(self.task,output_dir=output)
                self.assertTrue(app.replay_run(saved)['replay_verified'])
                for path,raw in retained.items():self.assertEqual(path.read_bytes(),raw)

    def test_legacy_incomplete_directory_is_retained_and_explicit_new_location_works(self):
        context=app.check_task(self.task);runtime=build_runtime_provenance()
        identity=digest(dict(task_id=context['task_id'],source_hash=runtime['source_identity']['content_sha256'],environment=runtime['environment_verified']))
        directory=context['output']/('run-'+identity);directory.mkdir(parents=True)
        partial=directory/'partial-original';partial.write_bytes(b'original partial data')
        with self.assertRaisesRegex(ValueError,'initialization_incomplete'):app.run_task(self.task)
        with self.assertRaisesRegex(ValueError,'initialization_incomplete'):app.resume_calculation(directory)
        saved=app.run_task(self.task,output_dir=self.root/'explicit-retry-output')
        self.assertTrue((saved/'report.json').is_file());self.assertEqual(partial.read_bytes(),b'original partial data')
        self.assertFalse((directory/'report.json').exists())

    def test_external_output_menu_survives_exit_reopen_view_replay_and_history(self):
        from hakimi_research.trade_cli import recent_runs
        task=json.loads(self.task.read_bytes());task['output_dir']=str(self.root/'external-results')
        self.task.write_text(json.dumps(task),encoding='utf-8')
        with patch('builtins.input',side_effect=['3','2','0']),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(self.workspace),0)
        self.assertIn('运行完成',output.getvalue());self.assertNotIn('操作停止',output.getvalue())
        records=list(self.workspace.glob('last-run-*.json'));self.assertEqual(len(records),1)
        record=json.loads(records[0].read_bytes());self.assertEqual(record['location_kind'],'ABSOLUTE')
        directory=Path(record['run_directory']);original=(directory/'report.json').read_bytes()
        with patch('builtins.input',side_effect=['4','5','8','1','12','1','0']),redirect_stdout(io.StringIO()) as reopened:
            self.assertEqual(wizard(self.workspace),0)
        self.assertIn('净收益率 -1.0253%',reopened.getvalue());self.assertIn('重放通过',reopened.getvalue())
        self.assertIn('新增离线计算 0 次',reopened.getvalue());self.assertNotIn('操作停止',reopened.getvalue())
        self.assertEqual((directory/'report.json').read_bytes(),original)
        self.assertEqual(recent_runs(self.workspace)[0],[directory])

    def test_missing_history_is_diagnosed_and_legacy_relative_history_still_loads(self):
        from hakimi_research.trade_cli import remember_run,recent_runs
        directory=app.run_task(self.task)
        (self.workspace/'last-run-legacy.json').write_text(json.dumps(dict(run_directory=directory.relative_to(self.workspace).as_posix())),encoding='utf-8')
        remember_run(self.workspace,self.root/'missing-run')
        candidates,warnings=recent_runs(self.workspace)
        self.assertEqual(candidates,[directory]);self.assertTrue(any('directory_missing' in item for item in warnings))
        (self.workspace/'last-run-escape.json').write_text(json.dumps(dict(schema_version='hakimi-recent-run-v1',run_directory='../elsewhere',location_kind='WORKSPACE_RELATIVE',recorded_at='2026-10-09')),encoding='utf-8')
        self.assertTrue(any('escapes_workspace' in item for item in recent_runs(self.workspace)[1]))

    def test_interrupted_external_calculation_is_found_without_a_recent_marker(self):
        task=json.loads(self.task.read_bytes());task['output_dir']=str(self.root/'external-interruption')
        self.task.write_text(json.dumps(task),encoding='utf-8')
        with patch.object(app,'run_strategy',side_effect=OSError('fictional interrupted external calculation')):
            with self.assertRaises(OSError):app.run_task(self.task)
        self.assertFalse(list(self.workspace.glob('last-run-*.json')))
        with patch('builtins.input',side_effect=['8','1','4','5','0']),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(self.workspace),0)
        self.assertIn('新增离线计算 1 次',output.getvalue());self.assertIn('重放通过',output.getvalue())
        self.assertNotIn('操作停止',output.getvalue())


if __name__=='__main__':unittest.main()
