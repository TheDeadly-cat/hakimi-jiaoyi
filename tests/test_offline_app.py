"""Installed entry, bound tasks, interrupted publication and movable workspaces."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.trade_cli import initialize_demo, main, wizard
from hakimi_research.offline_app import check_task, run_task, replay_run, recover_report, verify_run, resume_calculation, run_lock, describe_run
from hakimi_research.source_task import prepare, verify_packet, report as source_report
from hakimi_research.strategy_registry import run_strategy
from hakimi_research.equity_research import EquityExperimentRunner, EquityExperimentSpec


class OfflineAppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.workspace=self.root/'workspace'
        initialize_demo(self.workspace)

    def task(self,name='price'):
        return self.workspace/'tasks'/(name+'.json')

    def test_two_registered_adapters_use_existing_results_and_replay(self):
        results={}
        for name in ['price','event']:
            ctx=check_task(self.task(name))
            direct=EquityExperimentRunner().run(ctx['snapshot'],EquityExperimentSpec.from_document(ctx['semantics']['experiment']),event_context=ctx['context'])
            folder=run_task(self.task(name))
            _,saved,_=verify_run(folder)
            self.assertEqual(saved['result_hash'],direct.document['result_hash'])
            self.assertEqual(saved['result'],direct.document['result'])
            self.assertTrue(replay_run(folder)['replay_verified'])
            self.assertEqual(run_task(self.task(name)),folder)
            self.assertFalse(saved['execution_permission']['order_allowed'])
            self.assertIn('费用与期末持仓',(folder/'index.html').read_text(encoding='utf-8'))
            results[name]=saved['result']
        self.assertGreater(results['price']['fill_count'],0)
        self.assertEqual(results['event']['fill_count'],0)
        self.assertTrue(any(v.get('disposition')=='BLOCK_NEW_BUY' for row in results['event']['signals'] for v in row.get('event_filter',{}).values()))

    def test_moving_workspace_keeps_task_and_report_identity(self):
        before=check_task(self.task())['task_id']
        folder=run_task(self.task());original=(folder/'report.json').read_bytes()
        moved=self.root/'other-computer'/'moved-workspace'
        shutil.copytree(self.workspace,moved)
        moved_run=moved/'runs'/folder.name
        self.assertTrue(self.workspace.resolve().is_relative_to(self.root))
        shutil.rmtree(self.workspace)
        self.assertEqual(check_task(moved/'tasks/price.json')['task_id'],before)
        self.assertEqual((moved_run/'report.json').read_bytes(),original)
        self.assertTrue(replay_run(moved_run)['replay_verified'])
        page=recover_report(moved_run)
        self.assertIn(str(moved_run),page.read_text(encoding='utf-8'))
        self.assertEqual((moved_run/'report.json').read_bytes(),original)

    def test_interrupted_html_recovers_saved_result_without_running_engine(self):
        from hakimi_research import offline_app
        original=offline_app._save_encoded_report
        def interrupt(encoded,path):
            if Path(path).name=='index.html':raise OSError('fictional report-write interruption')
            return original(encoded,path)
        with patch.object(offline_app,'_save_encoded_report',side_effect=interrupt):
            with self.assertRaisesRegex(OSError,'interruption'):run_task(self.task())
        folder=next((self.workspace/'runs').glob('run-*'));raw=(folder/'report.json').read_bytes()
        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('engine must not repeat')):
            self.assertTrue(recover_report(folder).is_file())
            self.assertEqual(run_task(self.task()),folder)
        self.assertEqual((folder/'report.json').read_bytes(),raw)
        self.assertTrue((folder/'failure.json').is_file())

    def test_missing_or_corrupt_input_paused_task_and_wrong_strategy_stop(self):
        for change,error in [({'state':'PAUSED'},'task_paused'),({'strategy':'price.dual_ma@999'},'unsupported_strategy'),
            ({'snapshot':'missing-file.json'},'input_file_missing')]:
            with self.subTest(change=change):
                task=json.loads(self.task().read_bytes());task.update(change)
                path=self.workspace/'tasks'/'bad.json';path.write_text(json.dumps(task),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,error):run_task(path)
        self.assertFalse((self.workspace/'runs').exists())
        folder=run_task(self.task());p=folder/'inputs/snapshot.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'retained_input_missing_or_changed'):recover_report(folder)

    def test_explicit_calculation_resume_preserves_failure_and_refuses_live_owner(self):
        from hakimi_research import offline_app
        with patch.object(offline_app,'run_strategy',side_effect=OSError('fictional interrupted calculation')):
            with self.assertRaisesRegex(OSError,'interrupted calculation'):run_task(self.task())
        folder=next((self.workspace/'runs').glob('run-*'));failure=(folder/'failure.json').read_bytes()
        self.assertFalse((folder/'report.json').exists())
        with run_lock(folder):
            with self.assertRaisesRegex(ValueError,'active_owner'):resume_calculation(folder)
        with patch.object(offline_app,'run_strategy',wraps=run_strategy) as runner:
            page,runs=resume_calculation(folder)
            self.assertEqual(runs,1);self.assertEqual(runner.call_count,1);self.assertTrue(page.is_file())
        self.assertEqual((folder/'failure.json').read_bytes(),failure)
        self.assertTrue((folder/'resume-attempts/001.completed.json').is_file())
        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('must not repeat saved computation')):
            self.assertEqual(resume_calculation(folder)[1],0)


    def test_new_parameters_new_identity_but_location_is_not_a_new_strategy(self):
        original=check_task(self.task())['task_id']
        task=json.loads(self.task().read_bytes());task['experiment']['fee_rate']=0.0016
        path=self.workspace/'tasks'/'new-cost.json';path.write_text(json.dumps(task),encoding='utf-8')
        self.assertNotEqual(check_task(path)['task_id'],original)
        task['experiment']['fee_rate']=0.0008;task['output_dir']='../../another-output'
        path.write_text(json.dumps(task),encoding='utf-8')
        self.assertEqual(check_task(path)['task_id'],original)

    def test_installed_source_workflow_runs_and_retained_packet_moves(self):
        packet=prepare(self.workspace/'data/source-manifest.json')
        self.assertEqual(verify_packet(packet)['events'][0]['status'],'ABOVE')
        page=source_report(packet)
        self.assertTrue((page/'index.html').is_file())
        original=packet.read_bytes()
        moved=self.root/'moved-source-task';shutil.copytree(packet.parent,moved)
        self.assertEqual(verify_packet(moved/'packet.json')['packet_hash'],verify_packet(packet)['packet_hash'])
        self.assertEqual((moved/'packet.json').read_bytes(),original)
        (moved/'originals'/next((moved/'originals').iterdir()).name).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'retained_source_changed'):verify_packet(moved/'packet.json')

    def test_cli_checks_and_terminal_menu_are_real_entry_paths(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['check','--task',str(self.task())]),0)
            self.assertEqual(main(['source','verify','--packet',str(prepare(self.workspace/'data/source-manifest.json'))]),0)
            self.assertEqual(main(['check','--task',str(self.root/'absent.json')]),1)
        self.assertIn('INPUTS_CHECKED_NO_SIMULATION',output.getvalue())
        with patch('builtins.input',side_effect=['2','1','3','1','5','6','0']),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(self.workspace),0)
        self.assertIn('输入检查通过',output.getvalue());self.assertIn('运行完成',output.getvalue());self.assertIn('重放通过',output.getvalue())

    def test_normal_menu_import_and_configuration_do_not_require_a_demo(self):
        from importlib.resources import files
        resources=files('hakimi_research').joinpath('resources')
        csv=self.root/'provided.csv';metadata=self.root/'provided.json'
        csv.write_bytes(resources.joinpath('trade-demo.csv').read_bytes())
        metadata.write_bytes(resources.joinpath('trade-demo-import.json').read_bytes())
        empty=self.root/'normal-user'
        inputs=['9',str(csv),str(metadata),'10','1','2',*(['']*6),'baseline','2','1','3','1','0']
        with patch('builtins.input',side_effect=inputs),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(empty),0)
        self.assertTrue((empty/'tasks/baseline.json').is_file())
        self.assertFalse((empty/'tasks/price.json').exists())
        self.assertIn('运行完成',output.getvalue())


    def test_saved_result_is_readable_without_a_browser_or_new_calculation(self):
        from hakimi_research import offline_app
        folder=run_task(self.task());original=(folder/'report.json').read_bytes()
        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('view must not calculate')):
            with patch('hakimi_research.trade_cli.request_browser_view',side_effect=AssertionError('view must not launch a browser')):
                with patch('builtins.input',side_effect=['4','0']),redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(wizard(self.workspace),0)
                with redirect_stdout(io.StringIO()) as json_output:
                    self.assertEqual(main(['report','--run-dir',str(folder)]),0)
        text=output.getvalue()
        for expected in ['双均线价格策略','策略版本 1','2024-11-11','2024-12-03','SYNTHETIC_TEST',
            'BUY 意图 1；成交 2','净收益率 -1.0253%','扣费后损益 -102.53','费用 3.92','期末持仓 0.0000',
            'fast MA crossed above slow MA',str(folder)]:self.assertIn(expected,text)
        result=json.loads(json_output.getvalue())
        self.assertEqual(result['new_economic_runs'],0)
        self.assertEqual(result['result_view']['report_hash'],verify_run(folder)[1]['report_hash'])
        self.assertEqual((folder/'report.json').read_bytes(),original)
        corrupt=json.loads(original);corrupt['result']['total_fees']=0
        (folder/'report.json').write_text(json.dumps(corrupt),encoding='utf-8')
        with self.assertRaises(ValueError):describe_run(folder)

    def test_optional_browser_failure_and_timeout_preserve_access_to_saved_results(self):
        import subprocess
        from types import SimpleNamespace
        folder=run_task(self.task());original=(folder/'report.json').read_bytes()
        for behavior,message in [(dict(return_value=SimpleNamespace(returncode=1)),'浏览器未能打开'),
            (dict(side_effect=subprocess.TimeoutExpired('fictional browser request',5)),'浏览器打开请求未完成')]:
            with self.subTest(message=message):
                with patch('subprocess.run',**behavior) as dispatch,patch('builtins.input',side_effect=['11','0']),redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(wizard(self.workspace),0)
                self.assertIn(message,output.getvalue())
                self.assertIn('净收益率 -1.0253%',output.getvalue())
                self.assertEqual(dispatch.call_count,1)
                self.assertEqual(dispatch.call_args.kwargs['timeout'],5)
                self.assertEqual((folder/'report.json').read_bytes(),original)


if __name__=='__main__':unittest.main()
