"""Normal canonical workspace flow and local HTTP boundary regression checks."""
import base64
from importlib.resources import files
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.workbench_service import Workbench
from hakimi_research.workbench_server import create_server


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.app = Workbench(self.root)
        self.sequence = 0

    def act(self, action, **params):
        self.sequence += 1
        return self.app.action(dict(action=action, operation_id='operation-' + str(self.sequence), **params))

    def seed(self):
        resource = files('hakimi_research').joinpath('resources')
        return self.act('import_csv',
            csv_base64=base64.b64encode(resource.joinpath('trade-demo.csv').read_bytes()).decode(),
            manifest_base64=base64.b64encode(resource.joinpath('trade-demo-import.json').read_bytes()).decode())

    def task(self, data, strategy='price.dual_ma@1'):
        params = dict(fast_window=2, slow_window=4, position_pct=.25, stop_loss_pct=.03, take_profit_pct=.06)
        if strategy == 'price.buy_and_hold@1':
            params = dict(target_position_pct=.25)
        return self.act('create_task', title='软件演练', strategy=strategy, snapshot=data['ref'], params=params,
            score_start='2024-11-11', score_end='2024-12-03', initial_cash=10000, fee_rate=.0008, slippage_pct=.0005)

    def test_import_create_run_compare_close_reopen_uses_saved_canonical_results(self):
        data = self.seed()
        first = self.task(data)
        second = self.task(data, 'price.buy_and_hold@1')
        a = self.act('run_task', task=first['ref'])
        b = self.act('run_task', task=second['ref'])
        comparison = self.act('compare', runs=[a['ref'], b['ref']])
        self.assertEqual(comparison['status'], 'COMPARABLE_CONDITIONS')
        self.assertIn('max_drawdown', a['summary'])
        self.assertTrue(a['signals'])
        self.assertEqual(a['view']['data_kind'], 'SYNTHETIC_TEST')
        reopened = Workbench(self.root)
        self.assertEqual(reopened.run_view(a['ref']), a)
        state = reopened.state()
        self.assertEqual(state['engine']['name'], 'hakimi_research')
        self.assertFalse(state['engine']['permissions']['order_allowed'])
        self.assertEqual(len(state['tasks']), 2)
        self.assertEqual(len(state['runs']), 2)

    def test_operation_retry_returns_original_without_duplicate_task_and_conflict_stops(self):
        data = self.seed()
        request = dict(action='create_task', operation_id='once-task-123', title='一次',
            strategy='price.buy_and_hold@1', snapshot=data['ref'])
        result = self.app.action(request)
        self.assertEqual(self.app.action(request), result)
        self.assertEqual(len(list((self.root / 'tasks').glob('task-*'))), 1)
        with self.assertRaisesRegex(ValueError, 'operation_id_payload_conflict'):
            self.app.action(dict(request, title='另一个任务'))

    def test_pending_operation_never_automatically_reexecutes(self):
        from hakimi_research.documents import digest
        from hakimi_research.offline_app import write_new
        request = dict(action='create_task', operation_id='unknown-1234')
        write_new(self.root / 'operations/unknown-1234/request.json', dict(request_hash=digest(request), request=request))
        with self.assertRaisesRegex(ValueError, 'operation_outcome_unknown'):
            self.app.action(request)
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])

    def test_reopened_workbench_recovers_only_original_watch_receipt_without_starting(self):
        from hakimi_research.documents import read_document
        from hakimi_research.continuous_watch import LocalInputWatcher
        from hakimi_research import continuous_watch as watch_module
        data = self.seed()
        task = self.task(data)
        account = self.act('create_account', title='恢复演练', tasks=[task['ref']], initial_cash=10000,
            limits=dict(max_total_position_pct=.8, max_symbol_position_pct=.5,
                        min_cash_pct=.1, max_daily_loss_pct=.05, max_leverage=1))
        watch = self.act('configure_watch', account=account['ref'], snapshots=[data['ref']],
            interval_seconds=1, max_data_age_seconds=30*86400)
        directory = self.app.path(watch['ref'], 'watches')
        local = LocalInputWatcher(directory, clock=lambda:'2024-12-04T00:00:00Z')
        self.assertEqual(local.poll_once()['status'], 'WAITING_STABLE_INPUT')
        original = watch_module.transact_shared_account
        def commit_then_lose(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('response lost after durable commit')
        with patch.object(watch_module, 'transact_shared_account', commit_then_lose):
            self.assertEqual(local.poll_once()['status'], 'SUBMISSION_UNKNOWN')
        pending = read_document(directory/'pending.json')['operation_id']
        sequence = self.app.account_view(account['ref'])['sequence']
        reopened = Workbench(self.root)
        state = reopened.state()
        self.assertEqual(state['watches'][0]['pending_operation_id'], pending)
        self.assertFalse(state['watches'][0]['monitoring'])
        request = dict(action='recover_watch_pending', operation_id='recover-watch-original-123',
            watch=watch['ref'], expected_operation_id=pending)
        with patch.object(watch_module, 'transact_shared_account', side_effect=AssertionError('must reuse receipt')):
            recovered = reopened.action(request)
        self.assertEqual(recovered['status'], 'CURRENT')
        self.assertFalse(recovered['pending_present'])
        self.assertFalse(recovered['monitoring'])
        self.assertEqual(reopened.action(request), recovered)
        self.assertEqual(reopened.account_view(account['ref'])['sequence'], sequence)
        with self.assertRaisesRegex(ValueError, 'watch_pending_request_required'):
            reopened.action(dict(request, operation_id='recover-watch-absent-123'))
        self.assertEqual(reopened.account_view(account['ref'])['sequence'], sequence)

    def test_loaded_process_rejects_mutation_after_disk_identity_changes(self):
        from hakimi_research.environment import build_runtime_provenance
        runtime = build_runtime_provenance()
        runtime['source_identity']['content_sha256'] = 'f' * 64
        with patch('hakimi_research.workbench_service.build_runtime_provenance', return_value=runtime):
            with self.assertRaisesRegex(ValueError, 'workbench_restart_required'):
                self.act('import_input', content_base64=base64.b64encode(b'{}').decode())
        self.assertEqual(list((self.root / 'operations').glob('*/request.json')), [])

    def test_delivery_identity_uses_verified_build_commit_not_current_git(self):
        from copy import deepcopy
        from hakimi_research.environment import build_runtime_provenance
        from hakimi_research.workbench_service import _delivery_identity
        runtime = deepcopy(build_runtime_provenance())
        source = runtime['source_identity']
        source.update(status='BUILD_VERIFIED', git=dict(commit='b' * 40, status='CLEAN'),
            build_receipt=dict(git=dict(commit='a' * 40, status='DIRTY')))
        identity = _delivery_identity(runtime, 'test-package', self.app.loaded_source)
        self.assertEqual(identity['build_commit'], 'a' * 40)
        self.assertEqual(identity['build_worktree_status'], 'DIRTY')
        self.assertEqual(identity['origin'], 'INSTALLED_BUILD')
        self.assertEqual(identity['loaded_source_sha256'], self.app.loaded_source)
        self.assertEqual(identity['package_version'], 'test-package')
        source['status'] = 'BUILD_MISMATCH'
        self.assertIsNone(_delivery_identity(runtime, 'test-package', self.app.loaded_source)['build_commit'])
        source['status'] = 'CONTENT_HASHED'
        identity = _delivery_identity(runtime, 'unrelated-installed-package', self.app.loaded_source)
        self.assertEqual(identity['origin'], 'SOURCE_CHECKOUT')
        self.assertIsNone(identity['package_version'])
        self.assertIsNone(identity['build_commit'])
        self.assertEqual(identity['checkout_git']['commit'], 'b' * 40)

    def test_account_compatibility_is_read_only_and_ignores_git_only_changes(self):
        from copy import deepcopy
        import hashlib
        from hakimi_research.environment import build_runtime_provenance
        data = self.seed()
        task = self.task(data)
        account = self.act('create_account', title='身份核对', tasks=[task['ref']], initial_cash=10000,
            limits=dict(max_total_position_pct=.8, max_symbol_position_pct=.5,
                        min_cash_pct=.1, max_daily_loss_pct=.05, max_leverage=1))
        hashes = lambda: {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in self.root.rglob('*') if p.is_file()}
        before = hashes()
        original = self.app.account_view(account['ref'])
        self.assertTrue(original['compatibility']['can_continue'])
        runtime = deepcopy(build_runtime_provenance())
        runtime['source_identity']['git'] = dict(commit='b' * 40, status='DIRTY')
        with patch('hakimi_research.workbench_service.build_runtime_provenance', return_value=runtime):
            self.assertTrue(self.app.account_view(account['ref'])['compatibility']['can_continue'])
        runtime['source_identity']['content_sha256'] = 'f' * 64
        with patch('hakimi_research.workbench_service.build_runtime_provenance', return_value=runtime):
            changed = self.app.account_view(account['ref'])
            self.assertEqual(changed['compatibility']['status'], 'READ_ONLY')
            self.assertIn('CODE_CONTENT_CHANGED', changed['compatibility']['reasons'])
            self.assertFalse(changed['compatibility']['can_continue'])
            self.assertFalse(self.app.state()['accounts'][0]['compatibility']['can_continue'])
        self.assertEqual(changed['history'], original['history'])
        self.assertEqual(changed['state'], original['state'])
        self.assertEqual(hashes(), before)

    def test_missing_account_binding_and_changed_dependencies_do_not_claim_continuation(self):
        from copy import deepcopy
        from hakimi_research.environment import build_runtime_provenance
        from hakimi_research.workbench_service import _account_compatibility
        runtime = build_runtime_provenance()
        missing = _account_compatibility(None, runtime, self.app.loaded_source, self.app.loaded_environment)
        self.assertFalse(missing['can_continue'])
        self.assertEqual(missing['reasons'], ['SAVED_RUNTIME_UNKNOWN'])
        saved = dict(source_sha256=self.app.loaded_source, dependencies=deepcopy(self.app.loaded_environment))
        saved['dependencies']['python_version'] = 'different'
        changed = _account_compatibility(saved, runtime, self.app.loaded_source, self.app.loaded_environment)
        self.assertFalse(changed['can_continue'])
        self.assertEqual(changed['reasons'], ['DEPENDENCIES_CHANGED'])

    def test_task_context_uses_current_parameters_without_creating_task(self):
        data = self.seed()
        default = self.app.action(dict(action='task_context', strategy='price.dual_ma@1', snapshot=data['ref']))
        changed = self.app.action(dict(action='task_context', strategy='price.dual_ma@1', snapshot=data['ref'],
            params=dict(fast_window=5, slow_window=10)))
        self.assertEqual(default['required_context_sessions'], 62)
        self.assertEqual(changed['required_context_sessions'], 12)
        self.assertIsNotNone(changed['suggested_score_start'])
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])

    def test_workspace_reference_cannot_escape_or_access_wrong_area(self):
        for ref in ('../outside.json', '/etc/passwd', 'C:/outside.json', 'data\\other.json', 'runs/../data/a'):
            with self.assertRaises(ValueError):
                self.app.path(ref, 'data')
        with self.assertRaises(ValueError):
            self.app.path('operations/secret/request.json', 'data')

    def test_global_pause_keeps_continuous_protection_semantics_and_reopens(self):
        data = self.seed()
        task = self.task(data)
        account = self.act('create_account', title='连续演练', tasks=[task['ref']], initial_cash=10000,
            limits=dict(max_total_position_pct=.8, max_symbol_position_pct=.5,
                        min_cash_pct=.1, max_daily_loss_pct=.05, max_leverage=1))
        paused = self.act('pause_account', account=account['ref'], paused=True)
        self.assertTrue(paused['account']['state']['paused'])
        advanced = self.act('advance', account=account['ref'], snapshots=[data['ref']],
            through='2024-12-03', observed_at='2024-12-04T00:00:00Z')
        self.assertEqual(advanced['account']['continuous']['status'], 'PAUSED_NEW_ENTRIES')
        self.assertEqual(Workbench(self.root).account_view(account['ref'])['receipt_head'],
                         advanced['account']['receipt_head'])
        resumed = self.act('pause_account', account=account['ref'], paused=False)
        self.assertFalse(resumed['account']['state']['paused'])

    def test_real_adapter_preview_requires_confirmation_and_keeps_refusal(self):
        fixture = Path(__file__).parent / 'fixtures/collaboration_schedule_result_synthetic.json'
        response = self.act('preview_research', result_base64=base64.b64encode(fixture.read_bytes()).decode(),
            security_id='SYNTHETIC:TEST')
        self.assertEqual(response['status'], 'REJECTED')
        self.assertIn('MANUAL_CONFIRMATION_REQUIRED', response['reasons'])
        self.assertTrue(self.app.path(response['ref']).joinpath('assessment.json').is_file())
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])

    def test_http_rejects_missing_token_cross_origin_and_untrusted_host(self):
        server = create_server(self.root)
        self.addCleanup(server.server_close)
        handler = server.RequestHandlerClass.__new__(server.RequestHandlerClass)
        handler.server = server
        handler.path = '/'
        host = '127.0.0.1:' + str(server.server_port)
        handler.headers = {'Host': host}
        handler.wfile = io.BytesIO()
        statuses = []
        handler._headers = lambda status, *_: statuses.append(status)
        handler.do_GET()
        html = handler.wfile.getvalue().decode()
        self.assertEqual(statuses, [200])
        token = re.search(r'<script nonce="([^"]+)"', html).group(1)
        for headers in ({}, {'X-Hakimi-Token': token, 'Origin': 'https://attacker.example'},
                        {'X-Hakimi-Token': token, 'Host': 'attacker.example'}):
            handler.headers = dict({'Host': host}, **headers)
            with self.assertRaises(ValueError):
                handler._boundary(api=True)
        handler.path = '/api/state'
        handler.headers = {'Host': host, 'X-Hakimi-Token': token}
        handler.wfile = io.BytesIO()
        handler.do_GET()
        result = json.loads(handler.wfile.getvalue())
        self.assertEqual(statuses[-1], 200)
        self.assertEqual(result['mode'], 'LOCAL_RESEARCH_ONLY')


if __name__ == '__main__':
    unittest.main()
