from copy import deepcopy
import unittest
from unittest.mock import patch
from exchange_terminal.services import terminal_continuous_replay as replay
from tests import test_terminal_continuous_replay as fixtures


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReplayTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_event_limit_preserves_all_rows_and_pause_reconcile_exit_and_bounded_pages(self):
        limits=dict(replay.DEFAULT_LIMITS,max_events=5,history_page_limit=2)
        account=self.fixture.create(limits=limits);seed=self.fixture.seed(account)
        account.advance_next('capacity-step-0001',expected_head=seed['head'])
        self.assertEqual(account.snapshot()['phase'],'CAPACITY_PAUSED')
        before=account.snapshot()
        with self.assertRaisesRegex(replay.ReplayError,'capacity_reached'):
            account.advance_next('capacity-step-0002',expected_head=before['head'])
        self.assertEqual(account.snapshot(),before)
        paused=account.pause('capacity-pause-0001',expected_head=before['head'],reason='stop at limit')
        checked=account.reconcile('capacity-check-0001',expected_head=paused['head'])
        self.assertEqual(account.snapshot()['capacity']['events'],7)
        with self.assertRaisesRegex(replay.ReplayError,'capacity_reached'):
            account.resume('capacity-resume-0001',expected_head=checked['head'])
        items=[];cursor=0
        while True:
            page=account.history(after_sequence=cursor,expected_head=checked['head'])
            self.assertLessEqual(len(page['items']),2);items+=page['items'];cursor=page['next_after']
            if not page['has_more']:break
        self.assertEqual([e['sequence'] for e in items],list(range(1,8)))
        with self.assertRaisesRegex(replay.ReplayError,'bounded_history'):account.history(limit=3)
        with self.assertRaisesRegex(replay.ReplayError,'head_changed'):account.history(expected_head=seed['head'])

    def test_interrupted_step_at_capacity_can_reconcile_without_any_fill(self):
        account=self.fixture.create(limits=dict(replay.DEFAULT_LIMITS,max_events=5))
        seed=self.fixture.seed(account)
        account._fault=lambda phase:(_ for _ in ()).throw(fixtures.Crash()) if phase=='after_intent' else None
        with self.assertRaises(fixtures.Crash):account.advance_next('capacity-crash-0001',expected_head=seed['head'])
        head=account.snapshot()['head'];account.close();account=self.fixture.reopen()
        checked=account.reconcile('capacity-recover-0001',expected_head=head)
        self.assertEqual(account.snapshot()['state']['quantity'],0)
        self.assertEqual(account.receipt('capacity-crash-0001')['outcome']['status'],'ABANDONED_NOT_APPLIED_AFTER_RECONCILIATION')
        account.pause('capacity-stop-0001',expected_head=checked['head'],reason='keep preserved')

    def test_input_version_limit_rejects_new_bytes_preserving_old_and_stop(self):
        account=self.fixture.create(limits=dict(replay.DEFAULT_LIMITS,max_input_versions=1))
        seed=self.fixture.seed(account);new=deepcopy(self.fixture.dataset);new['bars'][-1]['close']='134'
        before=account.snapshot()
        with self.assertRaisesRegex(replay.ReplayError,'input_capacity'):
            account.adopt_input('capacity-adopt-0001',expected_head=seed['head'],dataset=new)
        self.assertEqual(account.snapshot(),before)
        self.assertEqual(account.db.execute('SELECT COUNT(*) FROM datasets').fetchone()[0],1)
        account.pause('input-cap-stop-0001',expected_head=seed['head'],reason='input version limit')

    def test_implementation_change_blocks_step_before_intent_but_reads_and_pause_work(self):
        account=self.fixture.create();before=account.snapshot()
        with patch.object(replay,'LOADED_IMPLEMENTATION_SHA256','f'*64):
            with self.assertRaisesRegex(replay.ReplayError,'implementation_changed'):
                self.fixture.seed(account)
            self.assertFalse(account.snapshot()['implementation_compatible'])
            account.pause('model-stop-0001',expected_head=before['head'],reason='source changed')
        self.assertEqual(len(self.fixture.calls),0)


if __name__=='__main__':unittest.main()
