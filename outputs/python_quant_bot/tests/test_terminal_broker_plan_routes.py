"""Real authenticated routing and new TEMP stores, with fictional trusted inputs.

The immediate job stub is the existing handler fixture; durable job scheduling
has its own tests. No server, SDK, market source or research runner is started.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from unittest.mock import Mock
import unittest

from exchange_terminal.services.terminal_broker_candidate_service import BrokerCandidateService
from exchange_terminal.services.terminal_broker_package_loader import BrokerRuntimeLoad
from exchange_terminal.services.terminal_broker_plan_service import BrokerPlanService, PERMISSIONS, SCHEMA
from exchange_terminal.services import terminal_broker_execution_plan as plan
from tests import test_terminal_broker_integration as route_fixture
from tests import test_terminal_broker_execution_plan as fixture


class BrokerPlanRouteTests(unittest.TestCase):
    setUp = route_fixture.BrokerIntegrationTests.setUp
    request = route_fixture.BrokerIntegrationTests.request
    read = route_fixture.BrokerIntegrationTests.read
    inventory = route_fixture.BrokerIntegrationTests.inventory

    def install_preparation(self, resolver=None):
        candidates = BrokerCandidateService(self.shell.workspace / 'broker-candidates-v2',
            research_resolver=lambda _: deepcopy(fixture.RESOLUTION), clock=lambda: fixture.NOW)
        self.service._broker_service = candidates
        saved = candidates.save({'mode': fixture.SIM, 'request_id': 'route-plan-candidate-001',
            'config': fixture.config(), 'research_reference': fixture.REF})
        intent = candidates.prepare_intent({'mode': fixture.SIM, 'request_id': 'route-plan-intent-0001',
                                           'config_id': saved['config_id']})['intent']
        self.loader = Mock(side_effect=lambda mode: BrokerRuntimeLoad('PACKAGED_IDENTITY_MATCHED', mode,
            plan.verify_runtime_identity(**fixture.runtime_inputs(mode))))
        service = BrokerPlanService(self.shell.workspace, candidates=candidates,
            research_resolver=resolver or (lambda _: deepcopy(fixture.RESOLUTION)),
            runtime_loader=self.loader, clock=lambda: fixture.NOW)
        self.service._broker_plan_service = service
        return {'mode': fixture.SIM, 'request_id': 'route-plan-prepare-001', 'config_id': saved['config_id'],
                'intent_id': intent['id'], 'expected_control_revision': 0, 'bounds': fixture.bounds()}

    def test_actual_get_whitelist_and_default_repository_loader_are_lazy(self):
        before = self.inventory()
        cases = [
            ('terminal_broker_plan_capabilities', {'mode': fixture.SIM}),
            ('terminal_broker_plans', {'mode': fixture.SIM}),
            ('terminal_broker_plan', {'mode': fixture.SIM, 'plan_id': 'f' * 64}),
            ('terminal_broker_plan_receipt', {'mode': fixture.SIM, 'request_id': 'route-never-started-001'}),
        ]
        for resource, identity in cases:
            with self.subTest(resource=resource):
                status, response = self.read(resource, identity)
                self.assertEqual(status, 200, response)
                self.assertEqual(response['data']['schema_version'], SCHEMA)
                self.assertEqual(response['data']['permissions'], PERMISSIONS)
        self.assertEqual(self.read(cases[0][0], cases[0][1])[1]['data']['status'], 'NOT_PACKAGED')
        self.assertEqual(self.inventory(), before)
        self.jobs.submit.assert_not_called()
        self.runner.assert_not_called()
        self.network.assert_not_called()

    def test_actual_post_get_and_read_only_recovery_keep_one_original_plan(self):
        payload = self.install_preparation()
        status, response = self.request('actions/terminal_broker_prepare_plan',
                                       {'payload': payload, 'request_id': 'outer-plan-job-001'})
        self.assertEqual(status, 202, response)
        result = response['data']['result']
        self.assertEqual(result['status'], 'PLAN_SAVED')
        self.assertEqual(result['receipt']['payload'], payload)
        self.assertEqual(result['permissions'], PERMISSIONS)
        identity = result['result']['plan_id']
        self.loader.side_effect = AssertionError('Saved reads must not check current package or recompute')
        before = self.inventory()
        status, detail = self.read('terminal_broker_plan', {'mode': fixture.SIM, 'plan_id': identity})
        self.assertEqual(status, 200, detail)
        self.assertEqual(detail['data']['plan']['research_eligibility']['offline_only'], True)
        status, receipt = self.read('terminal_broker_plan_receipt',
                                    {'mode': fixture.SIM, 'request_id': payload['request_id']})
        self.assertEqual(status, 200, receipt)
        self.assertEqual(receipt['data']['receipt'], result['receipt'])
        self.assertFalse(receipt['data']['retry_allowed'])
        listed = self.read('terminal_broker_plans', {'mode': fixture.SIM})[1]['data']
        self.assertEqual([row['plan_id'] for row in listed['items']], [identity])
        self.assertEqual([row['request_id'] for row in listed['requests']], [payload['request_id']])
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.loader.call_count, 1)
        self.runner.assert_not_called()
        self.network.assert_not_called()

    def test_direct_stop_during_slow_plan_preparation_blocks_final_publication(self):
        entered, release = Event(), Event()
        def resolve(_):
            entered.set()
            if not release.wait(3):
                raise AssertionError('fixture resolver release missing')
            return deepcopy(fixture.RESOLUTION)
        payload = self.install_preparation(resolve)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(self.request, 'actions/terminal_broker_prepare_plan',
                                      {'payload': payload, 'request_id': 'outer-plan-job-stop-1'})
            self.assertTrue(entered.wait(3))
            try:
                status, stopped = self.request('broker-candidate/stop', {
                    'mode': fixture.SIM, 'request_id': 'direct-stop-during-plan-1', 'reason': 'Explicit fixture stop'})
                self.assertEqual(status, 200, stopped)
                self.assertEqual(stopped['data']['status'], 'STOPPED')
                self.assertFalse(stopped['data']['broker_orders_cancelled'])
            finally:
                release.set()
            status, response = pending.result(timeout=5)
        self.assertEqual(status, 202, response)
        result = response['data']['result']
        self.assertEqual(result['status'], 'PLAN_NOT_CREATED')
        self.assertIsNone(result['result']['plan_id'])
        self.assertIn('control', result['result']['reason'])
        listed = self.read('terminal_broker_plans', {'mode': fixture.SIM})[1]['data']
        self.assertEqual(listed['items'], [])
        self.assertEqual(len(listed['requests']), 1)
        self.assertEqual(listed['requests'][0]['state'], 'REFUSED')
        self.network.assert_not_called()

    def test_authentication_read_only_and_client_runtime_fields_reject_before_store_write(self):
        payload = {'mode': fixture.SIM, 'request_id': 'denied-plan-request-001', 'config_id': 'a' * 64,
                   'intent_id': 'b' * 64, 'expected_control_revision': 0, 'bounds': fixture.bounds()}
        request = {'payload': payload, 'request_id': 'denied-outer-plan-job'}
        for options in ({'token': False}, {'origin': False}, {'content_type': 'text/plain'}):
            with self.subTest(options=options):
                self.assertIn(self.request('actions/terminal_broker_prepare_plan', request, **options)[0], {400, 403})
                self.assertEqual(self.inventory(), {})
        self.shell.read_only = True
        self.assertEqual(self.request('actions/terminal_broker_prepare_plan', request)[0], 423)
        self.shell.read_only = False
        for extra in ({'runtime_identity': {}}, {'manifest_path': 'C:/outside'}, {'submit_allowed': True}):
            with self.subTest(extra=extra):
                status, response = self.request('actions/terminal_broker_prepare_plan',
                    {'payload': {**payload, **extra}, 'request_id': 'denied-forged-plan-job'})
                self.assertEqual(status, 400, response)
                self.assertEqual(self.inventory(), {})
        self.runner.assert_not_called()
        self.network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
