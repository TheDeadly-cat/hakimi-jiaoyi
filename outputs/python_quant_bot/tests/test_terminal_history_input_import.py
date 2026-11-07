"""Fresh fictional saved inputs; never copies a user's historical workspace."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from exchange_terminal.services.terminal_history_input_import import TerminalHistoryInputImport, ACTION
from exchange_terminal.services.terminal_workspace_history import TerminalWorkspaceHistory
from hakimi_research.documents import digest
from hakimi_research import workbench_service


def hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()} if root.exists() else {}


class HistoryInputImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file = Path(__file__).with_name('test_terminal_daily_bridge.py')
        spec = importlib.util.spec_from_file_location('history_copy_fixture', file)
        cls.fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.fixture)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fresh-history-copy-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root/'source'
        self.target = self.root/'target'
        self.raw, self.snapshot, _ = self.fixture.fixture()
        self.original = self.source/'data'/'retained.json'
        self.original.parent.mkdir(parents=True)
        self.original.write_bytes(self.raw)
        self.history = TerminalWorkspaceHistory(local_app_data=self.root/'unused-local',
            extra_roots=(self.source,), known_original_root=self.root/'unused-original', current_workspace=self.target)
        self.daily = TerminalDailyResearch(self.target)
        self.copy = TerminalHistoryInputImport(self.daily, self.history)
        self.workspace = self.history.list_workspaces()['items'][0]['id']
        self.input = self.history.list_records(self.workspace, 'inputs')['items'][0]
        self.old = hashes(self.source)
        self.addCleanup(patch.stopall)
        patch('socket.socket.connect', side_effect=AssertionError('No external calls')).start()
        patch('exchange_terminal.services.backtest_engine.run_causal_long_only_backtest', side_effect=AssertionError('No research run')).start()
        self.addCleanup(lambda: self.daily._writer.close() if self.daily._writer is not None else None)

    def payload(self, operation='history-copy-fixture-operation'):
        return dict(operation_id=operation, workspace_id=self.workspace, input_id=self.input['id'],
            expected_file_sha256=self.input['file_sha256'], expected_snapshot_id=self.input['snapshot_id'],
            confirmed_security=deepcopy(self.input['security']), acknowledge_source_limits=True)

    def test_read_inventory_detail_and_absent_receipts_are_lazy_and_read_only(self):
        before = hashes(self.root)
        self.assertEqual(self.history.read_detail(self.workspace, 'inputs', self.input['id'])['snapshot_id'], self.snapshot['snapshot_id'])
        self.assertEqual(self.copy.read()['items'], [])
        self.assertEqual(self.copy.read(self.payload()['operation_id'])['status'], 'NOT_RECORDED')
        self.assertIsNone(self.daily._writer)
        self.assertFalse(self.target.exists())
        self.assertEqual(hashes(self.root), before)

    def test_explicit_copy_reuses_canonical_receipts_and_exact_bytes_without_running(self):
        payload = self.payload()
        result = self.copy.mutate(payload)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['request_hash'], digest(dict(action=ACTION, payload=payload)))
        self.assertEqual(result['saved_input_verification'], 'VERIFIED_CURRENT_TARGET')
        raw, snapshot = self.daily.verified_input(result['saved_input_id'])
        self.assertEqual(raw, self.raw)
        self.assertEqual(snapshot, self.snapshot)
        self.assertEqual(hashes(self.source), self.old)
        self.assertEqual(result['source']['source_truth_verified'], False)
        self.assertEqual(result['permissions'], dict(research_only=True,paper_allowed=False,live_allowed=False,order_allowed=False))
        self.assertEqual(result['new_economic_runs'], 0)
        request = json.loads((self.daily.root/'operations'/payload['operation_id']/'request.json').read_bytes())
        self.assertEqual(request['request_hash'], digest(request['request']))
        self.assertEqual(request['request']['history_origin']['payload'], payload)
        before = hashes(self.root)
        self.assertEqual(self.copy.mutate(payload), result)
        self.assertEqual(self.copy.read()['items'][0], result)
        self.assertEqual(hashes(self.root), before)
        self.assertEqual(list((self.daily.root/'tasks').iterdir()), [])
        self.assertEqual(list((self.daily.root/'runs').iterdir()), [])

    def test_duplicate_bytes_with_new_explicit_operation_do_not_create_another_input(self):
        first = self.copy.mutate(self.payload())
        second = self.copy.mutate(self.payload('history-copy-second-explicit'))
        self.assertEqual(first['saved_input_id'], second['saved_input_id'])
        self.assertEqual(len(self.daily.read('terminal_daily_inputs')['items']), 1)
        self.assertEqual(hashes(self.source), self.old)

    def test_source_hash_security_and_explicit_confirmation_are_required_before_writer(self):
        for change in (lambda p:p.update(expected_file_sha256='f'*64), lambda p:p.update(expected_snapshot_id='f'*64),
                       lambda p:p['confirmed_security'].update(symbol='OTHER'), lambda p:p.update(acknowledge_source_limits=1),
                       lambda p:p.update(path=str(self.original)), lambda p:p.update(input_id='../outside'),
                       lambda p:p.update(operation_id='not-a-history-operation')):
            with self.subTest(change=change):
                payload=self.payload();change(payload)
                with self.assertRaises(ValueError): self.copy.mutate(payload)
                self.assertIsNone(self.daily._writer)
                self.assertFalse(self.target.exists())
        self.assertEqual(hashes(self.source), self.old)

    def test_changed_source_and_hardlinked_source_are_not_copied(self):
        self.original.write_bytes(b'changed source')
        with self.assertRaises(ValueError): self.copy.mutate(self.payload())
        self.assertFalse(self.target.exists())
        self.original.write_bytes(self.raw)
        import os
        os.link(self.original, self.root/'source-alias')
        with self.assertRaisesRegex(ValueError,'regular_bounded'): self.copy.mutate(self.payload())
        self.assertFalse(self.target.exists())

    def test_destination_collision_is_rejected_without_overwriting_or_claiming(self):
        target=self.copy._destination(self.raw,self.snapshot)
        target.parent.mkdir(parents=True)
        target.write_bytes(b'pre-existing conflict')
        before=hashes(self.root)
        with self.assertRaisesRegex(ValueError,'destination_collision'):self.copy.mutate(self.payload())
        self.assertEqual(hashes(self.root),before)
        self.assertEqual(self.copy.read(self.payload()['operation_id'])['status'],'NOT_RECORDED')

    def test_pending_copy_never_retries_even_when_input_write_succeeded(self):
        original=workbench_service.write_new
        def lose_result(path,value):
            if Path(path).name=='result.json':raise OSError('fixture lost before completion record')
            return original(path,value)
        with patch.object(workbench_service,'write_new',side_effect=lose_result):
            with self.assertRaises(OSError):self.copy.mutate(self.payload())
        before=hashes(self.root)
        with patch.object(workbench_service,'_retain',side_effect=AssertionError('No retry')):
            self.assertEqual(self.copy.read(self.payload()['operation_id'])['status'],'PENDING')
            with self.assertRaisesRegex(ValueError,'query_only'):self.copy.mutate(self.payload())
        self.assertEqual(hashes(self.root),before)
        self.assertEqual(len(self.daily.read('terminal_daily_inputs')['items']),1)

    def test_lost_success_reply_recovers_from_receipt_without_recopied_source(self):
        writer=self.daily._ensure_writer();original=writer.action
        def lost(request):
            original(request);raise OSError('fixture lost reply')
        with patch.object(writer,'action',side_effect=lost):
            with self.assertRaises(OSError):self.copy.mutate(self.payload())
        self.original.unlink()
        before=hashes(self.root)
        with patch.object(writer,'action',side_effect=AssertionError('No replay')):
            result=self.copy.read(self.payload()['operation_id'])
            self.assertEqual(result['status'],'COMPLETED')
            self.assertFalse(result['current_source_rechecked'])
            self.assertEqual(result['saved_input_verification'],'VERIFIED_CURRENT_TARGET')
            self.assertEqual(self.copy.mutate(self.payload()),result)
        self.assertEqual(hashes(self.root),before)

    def test_copy_fact_is_not_revoked_when_target_read_later_fails(self):
        result=self.copy.mutate(self.payload())
        path=self.daily._lookup('inputs',result['saved_input_id']);path.write_bytes(b'changed target')
        before=hashes(self.root)
        receipt=self.copy.read(self.payload()['operation_id'])
        self.assertEqual(receipt['status'],'COMPLETED')
        self.assertEqual(receipt['saved_input_id'],result['saved_input_id'])
        self.assertIsNone(receipt['saved_input'])
        self.assertEqual(receipt['saved_input_verification'],'UNAVAILABLE')
        self.assertIn('saved_input_read_error',receipt)
        self.assertEqual(hashes(self.root),before)

    def test_same_operation_different_payload_and_tampered_origin_fail_closed(self):
        self.copy.mutate(self.payload())
        changed=self.payload();changed['confirmed_security']['symbol']='OTHER'
        before=hashes(self.root)
        with self.assertRaisesRegex(ValueError,'payload_conflict'):self.copy.mutate(changed)
        self.assertEqual(hashes(self.root),before)
        path=self.daily.root/'operations'/self.payload()['operation_id']/'request.json'
        record=json.loads(path.read_bytes());record['request']['history_origin']['source']['sessions']+=1
        path.write_text(json.dumps(record),encoding='utf-8')
        before=hashes(self.root)
        with self.assertRaisesRegex(ValueError,'request_changed'):self.copy.read(self.payload()['operation_id'])
        self.assertEqual(hashes(self.root),before)

    def test_two_processes_claim_same_operation_once(self):
        payload=self.root/'copy-payload.json';payload.write_text(json.dumps(self.payload()),encoding='utf-8')
        signal=self.root/'start'
        script=r'''
import json,pathlib,socket,sys,time
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No network'))
from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from exchange_terminal.services.terminal_history_input_import import TerminalHistoryInputImport
from exchange_terminal.services.terminal_workspace_history import TerminalWorkspaceHistory
from hakimi_research import workbench_service
root,payload,marker,signal=map(pathlib.Path,sys.argv[1:]);source=root/'source';target=root/'target'
history=TerminalWorkspaceHistory(local_app_data=root/'unused-local',extra_roots=(source,),known_original_root=root/'unused-original',current_workspace=target)
daily=TerminalDailyResearch(target);helper=TerminalHistoryInputImport(daily,history);original=workbench_service._retain
def retain(*args):
    marker.write_text('one actual retain');time.sleep(.2);return original(*args)
workbench_service._retain=retain;marker.with_suffix('.ready').write_text('ready')
deadline=time.monotonic()+20
while not signal.exists():
    if time.monotonic()>deadline:raise TimeoutError('start signal absent')
    time.sleep(.01)
try:
    value=helper.mutate(json.loads(payload.read_bytes()));print(json.dumps({'status':value['status'],'id':value['saved_input_id']}))
except ValueError as error:print(json.dumps({'status':'PENDING_OR_CONFLICT','reason':str(error)}))
finally:
    if daily._writer is not None:daily._writer.close()
'''
        processes=[]
        try:
            for index in range(2):
                processes.append(subprocess.Popen([sys.executable,'-B','-c',script,str(self.root),str(payload),str(self.root/f'retained-{index}'),str(signal)],
                    cwd=Path(__file__).resolve().parents[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8'))
            deadline=time.monotonic()+20
            while len(list(self.root.glob('retained-*.ready')))<2:
                for process in processes:
                    if process.poll() is not None:
                        stdout,stderr=process.communicate();self.fail(f'child stopped before ready: {stdout} {stderr}')
                self.assertLess(time.monotonic(),deadline)
                time.sleep(.01)
            signal.write_text('go')
            values=[]
            for process in processes:
                stdout,stderr=process.communicate(timeout=30);self.assertEqual(process.returncode,0,stderr);values.append(json.loads(stdout))
            self.assertGreaterEqual(sum(row['status']=='COMPLETED' for row in values),1,values)
            self.assertEqual(len([p for p in self.root.glob('retained-*') if p.suffix!='.ready']),1)
            self.assertEqual(self.copy.read(self.payload()['operation_id'])['status'],'COMPLETED')
            self.assertEqual(len(self.daily.read('terminal_daily_inputs')['items']),1)
            self.assertEqual(hashes(self.source),self.old)
        finally:
            for process in processes:
                if process.poll() is None:process.kill()
                process.communicate(timeout=10)
                if process.stdout:process.stdout.close()
                if process.stderr:process.stderr.close()
if __name__ == '__main__':
    unittest.main()
