"""Frozen-tool/config tests. Registration and provider calls are never exercised."""
from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('bundle_tested',Path(__file__).resolve().parents[2]/'tools/observation_bundle.py')
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ObservationBundleTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows task preparation uses PowerShell')
    def test_powershell_json_dates_keep_utc_through_com_string_boundary(self):
        script=Path(__file__).resolve().parents[2]/'tools/prepare_observation_task.ps1'
        command=r'''$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($args[0],[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'parse failure'}
$fn=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Convert-UtcTaskBoundary'},$true)
. ([scriptblock]::Create($fn.Extent.Text))
$parsed='{"first":"2026-09-13T01:00:30Z","end":"2026-09-16T01:10:00Z"}' | ConvertFrom-Json
@((Convert-UtcTaskBoundary $parsed.first),(Convert-UtcTaskBoundary $parsed.end),(Convert-UtcTaskBoundary ([DateTimeOffset]'2026-09-13T09:00:30+08:00'))) | ConvertTo-Json -Compress
'''
        found=[]
        for name in ('powershell.exe','pwsh.exe'):
            executable=shutil.which(name)
            if executable:
                found.append(name)
                with self.subTest(shell=name):
                    # A file avoids command-string interpolation of the path.
                    with tempfile.TemporaryDirectory(prefix='hakimi-task-time-') as directory:
                        probe=Path(directory)/'probe.ps1'
                        probe.write_text(command,encoding='utf-8-sig')
                        result=subprocess.run([executable,'-NoProfile','-NonInteractive','-File',str(probe),str(script)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(json.loads(result.stdout),['2026-09-13T01:00:30Z','2026-09-16T01:10:00Z','2026-09-13T01:00:30Z'])
        self.assertTrue(found,'Windows PowerShell must be available')

    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='hakimi-control-bundle-test-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        self.bundle=self.root/'bundle'
        self.runtime=self.root/'runtime'
        (self.runtime/'venv/Scripts').mkdir(parents=True)
        (self.runtime/'venv/Scripts/pythonw.exe').write_bytes(b'NOT_AN_EXECUTABLE_TEST_FIXTURE')
        self.clock=module.now()
        self.start=(self.clock+timedelta(hours=2)).replace(minute=0,second=0,microsecond=0)
        clock=patch.object(module,'now',side_effect=lambda:self.clock)
        clock.start()
        self.addCleanup(clock.stop)
        self.preflight={'verification':{'fixture':True},'execution_bounds':{'fixture':True}}

    def create(self):
        with patch.object(module,'source_commit',return_value='1'*40),patch.object(module,'runtime_preflight',return_value=self.preflight):
            return module.create(self.bundle,self.runtime,module.stamp(self.start))

    def test_bundle_keeps_exact_tools_and_separate_state_directories(self):
        manifest=self.create()
        loaded,watch=module.verify_bundle(self.bundle,manifest['receipt_hash'])
        self.assertEqual(loaded,manifest)
        self.assertEqual(set(loaded['tool_sha256']),set(module.FILES))
        self.assertEqual(loaded['runtime_preflight'],self.preflight)
        self.assertEqual(module.timestamp(loaded['end_cutoff_exclusive'])-self.start,timedelta(hours=72))
        self.assertFalse(Path(loaded['job_root']).is_relative_to(Path(loaded['watch_root'])))
        self.assertFalse(loaded['scheduler_activated'])
        self.assertFalse((self.bundle/'job-receipts').exists())
        self.assertFalse((self.bundle/'watch-receipts').exists())

    def test_preview_has_two_expiring_windowless_roles_and_pinned_manifest(self):
        manifest=self.create()
        value=module.preview(self.bundle)
        observe,watch=value['tasks']
        self.assertEqual([item['task_name'] for item in value['tasks']],['HakimiReadOnlyObservation','HakimiObservationWatch'])
        self.assertEqual((observe['interval_seconds'],watch['interval_seconds']),(3600,60))
        self.assertEqual((observe['execution_limit_seconds'],watch['execution_limit_seconds']),(600,50))
        self.assertTrue(all(item['execute'].endswith('pythonw.exe') for item in value['tasks']))
        self.assertTrue(all(manifest['receipt_hash'] in item['arguments'] for item in value['tasks']))
        self.assertEqual(module.timestamp(watch['end_utc_exclusive'])-module.timestamp(observe['end_utc_exclusive']),timedelta(minutes=10))
        self.clock=self.start-timedelta(seconds=30)
        self.assertFalse(module.preview(self.bundle)['current_registration_window_valid'])

    def test_existing_destination_and_runtime_overlap_are_rejected_without_preflight(self):
        self.bundle.mkdir()
        with patch.object(module,'runtime_preflight') as runtime:
            with self.assertRaises(ValueError):
                module.create(self.bundle,self.runtime,module.stamp(self.start))
        runtime.assert_not_called()
        with self.assertRaises(ValueError):
            module.create(self.runtime/'new-controls',self.runtime,module.stamp(self.start))

    def test_tampered_tool_is_rejected_before_module_import(self):
        manifest=self.create()
        (self.bundle/'tools/observation_watch.py').write_text('raise RuntimeError("must not execute")',encoding='utf-8')
        with patch.object(module,'load') as loader:
            with self.assertRaises(ValueError):
                module.verify_bundle(self.bundle,manifest['receipt_hash'])
        loader.assert_not_called()

    def test_modified_plan_or_resealed_registered_manifest_is_rejected(self):
        manifest=self.create()
        changed=dict(manifest)
        changed.pop('receipt_hash')
        changed['created_at']='2000-01-01T00:00:00Z'
        (self.bundle/'bundle.json').write_text(json.dumps(module.seal(changed)),encoding='utf-8')
        with self.assertRaises(ValueError):
            module.verify_bundle(self.bundle,manifest['receipt_hash'])
        (self.bundle/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
        (self.bundle/'watch-plan.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):
            module.verify_bundle(self.bundle,manifest['receipt_hash'])

    def test_observation_does_not_start_before_or_after_declared_window(self):
        manifest=self.create()
        loaded,watch=module.verify_bundle(self.bundle,manifest['receipt_hash'])
        with patch.object(module,'verify_bundle',return_value=(loaded,watch)),patch.object(watch.job,'execute') as execute:
            before=module.run_role(self.bundle,manifest['receipt_hash'],'observe')
            self.clock=module.timestamp(manifest['end_cutoff_exclusive'])
            after=module.run_role(self.bundle,manifest['receipt_hash'],'observe')
        self.assertEqual(before['status'],after['status'])
        self.assertEqual(before['status'],'OUTSIDE_DECLARED_RUN_WINDOW')
        execute.assert_not_called()

    def test_watch_child_boundary_failure_is_not_preflight_or_success(self):
        manifest=self.create()
        loaded,watch=module.verify_bundle(self.bundle,manifest['receipt_hash'])
        value=SimpleNamespace(returncode=1,stdout='',stderr='',bounds={'outcome':'TIMED_OUT','cleanup_confirmed':True})
        with patch.object(module,'verify_bundle',return_value=(loaded,watch)),patch.object(watch.job,'execute',return_value=value) as execute:
            result=module.run_role(self.bundle,manifest['receipt_hash'],'watch')
        self.assertEqual(result['status'],'CHILD_EXECUTION_BOUNDARY_FAILED')
        self.assertEqual(execute.call_args.kwargs['timeout_seconds'],40)
        self.assertEqual(execute.call_args.kwargs['cleanup_seconds'],5)

    def test_exit_zero_without_a_bound_watch_report_is_invalid(self):
        manifest=self.create()
        loaded,watch=module.verify_bundle(self.bundle,manifest['receipt_hash'])
        value=SimpleNamespace(returncode=0,stdout='{}',stderr='',bounds={'outcome':'EXITED','cleanup_confirmed':True})
        with patch.object(module,'verify_bundle',return_value=(loaded,watch)),patch.object(watch.job,'execute',return_value=value):
            result=module.run_role(self.bundle,manifest['receipt_hash'],'watch')
        self.assertEqual(result['status'],'CHILD_RESULT_INVALID')
        self.assertEqual(result['error_stage'],'VALIDATE')

    def test_observer_receives_declared_window_arguments(self):
        manifest=self.create()
        loaded,watch=module.verify_bundle(self.bundle,manifest['receipt_hash'])
        self.clock=self.start+timedelta(minutes=2)
        value=SimpleNamespace(returncode=1,stdout='',stderr='',bounds={'outcome':'TIMED_OUT','cleanup_confirmed':True})
        with patch.object(module,'verify_bundle',return_value=(loaded,watch)),patch.object(watch.job,'execute',return_value=value) as execute:
            module.run_role(self.bundle,manifest['receipt_hash'],'observe')
        arguments=execute.call_args.args[0]
        self.assertEqual(arguments[arguments.index('--window-start')+1],manifest['start_cutoff'])
        self.assertEqual(arguments[arguments.index('--window-end')+1],manifest['end_cutoff_exclusive'])


if __name__=='__main__':
    unittest.main()
