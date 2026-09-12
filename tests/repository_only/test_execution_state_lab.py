"""Real SQLite/crash boundaries against a separate durable local simulated venue."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

SCRIPT = Path(__file__).resolve().parents[2] / 'tools/execution_state_lab.py'
SPEC = importlib.util.spec_from_file_location('execution_state_lab_tested', SCRIPT)
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class ExecutionStateLabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hakimi-execution-lab-test-')
        self.root = Path(self.temp.name).resolve()
        self.path, self.remote = self.root/'client.sqlite', self.root/'venue.sqlite'
        self.store = lab.ExecutionStore.create(self.path, cash='1000', holdings={}, symbols={'TEST':'0.01'})
        self.venue = lab.SimulatedVenue.create(self.remote, cash='1000', holdings={})

    def tearDown(self):
        self.store.close()
        self.venue.close()
        self.temp.cleanup()

    def prepare(self, key='intent-1', *, side='BUY', qty=10, price='10'):
        return self.store.prepare(key, symbol='TEST', side=side, quantity_value=qty, limit_price=price)

    def send(self, key='intent-1', *, lose=False):
        self.prepare(key)
        lab.reconcile(self.store, self.venue)
        return lab.submit_once(self.store, self.venue, key, lose_response=lose)

    def row(self):
        return self.store.inspect()['orders'][0]

    def update(self, qty, value, fee, state):
        return self.venue.update(self.row()['broker_id'], filled=qty, notional=value, fee=fee, state=state)

    def count(self):
        return self.venue.db.execute('SELECT COUNT(*) FROM venue_orders').fetchone()[0]

    def test_lost_response_restart_and_duplicate_do_not_repeat_submission(self):
        self.assertEqual(self.send(lose=True), 'UNKNOWN_RECONCILE_BEFORE_NEW_RISK')
        self.assertEqual(self.row()['state'], 'SUBMIT_UNKNOWN')
        self.store.close()
        self.store = lab.ExecutionStore(self.path)
        self.assertEqual(lab.submit_once(self.store, self.venue, 'intent-1'), 'ALREADY_ATTEMPTED_NO_SEND')
        self.assertEqual(self.count(), 1)
        lab.reconcile(self.store, self.venue)
        self.assertEqual(self.row()['state'], 'WORKING')
        self.assertIsNotNone(self.row()['broker_id'])

    def test_process_crash_after_venue_commit_before_ack_is_recoverable(self):
        self.prepare()
        code = '''import importlib.util,os,pathlib,sys
spec=importlib.util.spec_from_file_location("crash_lab",sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
store=module.ExecutionStore(sys.argv[2]);venue=module.SimulatedVenue(sys.argv[3])
module.reconcile(store,venue)
command=store.claim_submit("intent-1")
venue.submit(command)
os._exit(73)
'''
        child = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-B', '-c', code,
                                str(SCRIPT), str(self.path), str(self.remote)], capture_output=True, timeout=15)
        self.assertEqual(child.returncode, 73, child.stderr)
        self.store.close()
        self.store = lab.ExecutionStore(self.path)
        self.assertEqual(self.row()['state'], 'SUBMIT_UNKNOWN')
        self.assertEqual(lab.submit_once(self.store, self.venue, 'intent-1'), 'ALREADY_ATTEMPTED_NO_SEND')
        lab.reconcile(self.store, self.venue)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.row()['state'], 'WORKING')

    def test_crash_before_send_cannot_treat_absence_as_rejection(self):
        self.prepare()
        lab.reconcile(self.store, self.venue)
        command = self.store.claim_submit('intent-1')
        with self.assertRaisesRegex(lab.StateError, 'absence_does_not_prove'):
            lab.reconcile(self.store, self.venue)
        self.assertEqual(self.row()['state'], 'SUBMIT_UNKNOWN')
        self.assertIsNone(self.store.claim_submit('intent-1'))
        self.assertEqual(self.count(), 0)
        self.store.reject_submit('intent-1', command['claim_id'], 'LAB_DEFINITIVE_REJECTION')
        lab.reconcile(self.store, self.venue)
        self.assertIsNotNone(self.store.inspect()['stop_reason'])
        self.store.resume_new_risk('operator_checked_lab_rejection')
        self.assertIsNone(self.store.inspect()['stop_reason'])

    def test_cumulative_fills_only_book_deltas_and_duplicate_is_idempotent(self):
        self.send()
        partial = self.update(3, '29', '0.30', 'PARTIAL')
        self.store.ingest(partial)
        self.assertEqual(self.store.inspect()['cash'], '970.7')
        revision = self.store.inspect()['revision']
        self.assertEqual(self.store.ingest(partial), 'DUPLICATE')
        self.assertEqual(self.store.inspect()['revision'], revision)
        self.store.ingest(self.update(10, '98', '0.80', 'FILLED'))
        lab.reconcile(self.store, self.venue)
        state = self.store.inspect()
        self.assertEqual((state['cash'], state['positions']), ('901.2', {'TEST':10}))
        deltas = [json.loads(row[0]) for row in self.store.db.execute("SELECT payload FROM events WHERE kind='OBSERVATION_APPLIED'")]
        self.assertEqual(sum(row['delta_quantity'] for row in deltas), 10)
        self.assertEqual(sum(Decimal(row['delta_notional']) for row in deltas), Decimal('98'))
        self.assertEqual(sum(Decimal(row['delta_fee']) for row in deltas), Decimal('0.80'))

    def test_cancel_ack_does_not_release_reservation_and_fill_can_win(self):
        self.send()
        command = self.store.begin_cancel('intent-1')
        self.assertIsNone(self.store.begin_cancel('intent-1'))
        self.store.cancel_response('intent-1', command['cancel_id'], True)
        self.assertEqual(self.row()['state'], 'WORKING')
        self.assertEqual(self.store.inspect()['reserved_cash'], '101')
        self.store.ingest(self.update(10, '99', '1', 'FILLED'))
        self.store.cancel_response('intent-1', command['cancel_id'], True)
        self.assertEqual(self.row()['cancel_state'], 'SUPERSEDED_BY_FILL')
        self.assertEqual(self.store.inspect()['reserved_cash'], '0')
        self.assertEqual(self.row()['state'], 'FILLED')

    def test_late_partial_does_not_reopen_cancelled_but_fresh_open_snapshot_stops(self):
        self.send()
        partial = self.update(3, '29', '0.3', 'PARTIAL')
        self.store.ingest(partial)
        self.store.ingest(self.update(3, '29', '0.3', 'CANCELLED'))
        late = dict(partial, evidence_id=uuid.uuid4().hex)
        self.store.ingest(late)
        self.assertEqual(self.row()['state'], 'CANCELLED')
        self.assertEqual(self.store.inspect()['positions'], {'TEST':3})
        self.update(3, '29', '0.3', 'PARTIAL')
        with self.assertRaisesRegex(lab.StateError, 'terminal_order_reported_open'):
            lab.reconcile(self.store, self.venue)
        self.assertEqual(self.row()['state'], 'CANCELLED')
        self.assertIsNotNone(self.store.inspect()['stop_reason'])

    def test_stale_quantity_is_ignored_but_changed_notional_at_same_quantity_stops(self):
        self.send()
        old = self.update(2, '19', '0.2', 'PARTIAL')
        self.store.ingest(self.update(4, '39', '0.4', 'PARTIAL'))
        self.assertEqual(self.store.ingest(old), 'STALE')
        self.assertEqual(self.row()['filled'], 4)
        conflict = self.update(4, '38', '0.4', 'PARTIAL')
        with self.assertRaisesRegex(lab.StateError, 'cumulative_value_conflict'):
            self.store.ingest(conflict)
        self.assertEqual(self.row()['notional'], '39')
        fault = json.loads(self.store.db.execute("SELECT payload FROM events WHERE kind='RISK_STOP' ORDER BY sequence DESC LIMIT 1").fetchone()[0])
        self.assertEqual(fault['rejected_evidence_sha256'], lab.fingerprint(conflict))

    def test_same_evidence_id_with_different_payload_is_rejected(self):
        self.send()
        first = self.update(2, '19', '0.2', 'PARTIAL')
        self.store.ingest(first)
        with self.assertRaisesRegex(lab.StateError, 'observation_id_conflict'):
            self.store.ingest(dict(first, cumulative_fee='0.3'))
        self.assertEqual(self.row()['fee'], '0.2')

    def test_reconciliation_batch_rolls_back_on_balance_mismatch_then_recovers(self):
        self.send(lose=True)
        order_id = self.venue.db.execute('SELECT order_id FROM venue_orders').fetchone()[0]
        self.venue.update(order_id, filled=3, notional='29', fee='0.3', state='PARTIAL')
        snapshot = self.venue.snapshot(self.store.begin_reconcile())
        snapshot['cash'] = '999'
        with self.assertRaisesRegex(lab.StateError, 'reconciliation_mismatch'):
            self.store.complete_reconcile(snapshot)
        self.assertEqual((self.row()['filled'], self.row()['state']), (0, 'SUBMIT_UNKNOWN'))
        lab.reconcile(self.store, self.venue)
        self.assertEqual(self.row()['filled'], 3)
        self.assertIsNotNone(self.store.inspect()['stop_reason'])

    def test_simulator_does_not_hide_duplicate_client_submissions(self):
        self.prepare()
        lab.reconcile(self.store, self.venue)
        command = self.store.claim_submit('intent-1')
        self.venue.submit(command)
        self.venue.submit(command)
        self.assertEqual(self.count(), 2)
        with self.assertRaisesRegex(lab.StateError, 'ambiguous_snapshot_order_identity'):
            lab.reconcile(self.store, self.venue)
        self.assertEqual(self.row()['state'], 'SUBMIT_UNKNOWN')

    def test_unmanaged_order_or_changed_order_terms_halt_new_risk(self):
        self.send()
        obs = self.venue.snapshot('test')['orders'][0]
        for bad in (dict(obs, client_id='unknown', evidence_id=uuid.uuid4().hex),
                    dict(obs, quantity=11, evidence_id=uuid.uuid4().hex),
                    dict(obs, broker_order_id='LABO-another', evidence_id=uuid.uuid4().hex)):
            with self.subTest(bad=bad), self.assertRaises(lab.StateError):
                self.store.ingest(bad)
        self.assertEqual(self.row()['filled'], 0)
        self.assertIsNotNone(self.store.inspect()['stop_reason'])

    def test_unfilled_reservations_prevent_overcommit_and_release_on_terminal(self):
        self.prepare('first', qty=90)
        lab.reconcile(self.store, self.venue)
        lab.submit_once(self.store, self.venue, 'first')
        self.prepare('second', qty=10)
        lab.reconcile(self.store, self.venue)
        with self.assertRaisesRegex(lab.StateError, 'cash_reservation_exceeded'):
            self.store.claim_submit('second')
        first_id = self.store.inspect()['orders'][0]['broker_id']
        self.store.ingest(self.venue.update(first_id, filled=0, notional='0', fee='0', state='CANCELLED'))
        lab.reconcile(self.store, self.venue)
        self.assertIsNotNone(self.store.claim_submit('second'))

    def test_restart_and_stale_query_require_fresh_reconciliation(self):
        self.prepare()
        old = self.venue.snapshot(self.store.begin_reconcile())
        fresh = self.venue.snapshot(self.store.begin_reconcile())
        with self.assertRaisesRegex(lab.StateError, 'stale_or_unsolicited'):
            self.store.complete_reconcile(old)
        self.store.complete_reconcile(fresh)
        self.store.close()
        self.store = lab.ExecutionStore(self.path)
        with self.assertRaisesRegex(lab.StateError, 'fresh_reconciliation_required'):
            self.store.claim_submit('intent-1')
        lab.reconcile(self.store, self.venue)
        self.assertIsNotNone(self.store.claim_submit('intent-1'))

    def test_persistent_stop_blocks_buys_but_allows_reconciled_reduce_only_sell(self):
        self.send()
        self.store.ingest(self.update(10, '99', '1', 'FILLED'))
        self.store.stop('operator_stop')
        self.prepare('new-buy', qty=1)
        lab.reconcile(self.store, self.venue)
        with self.assertRaisesRegex(lab.StateError, 'new_risk_stopped'):
            self.store.claim_submit('new-buy')
        self.prepare('sell-too-many', side='SELL', qty=11)
        lab.reconcile(self.store, self.venue)
        with self.assertRaisesRegex(lab.StateError, 'reduce_only_sell_exceeded'):
            self.store.claim_submit('sell-too-many')
        self.prepare('reduce-position', side='SELL', qty=5)
        lab.reconcile(self.store, self.venue)
        self.assertIsNotNone(self.store.claim_submit('reduce-position'))
        self.assertEqual(self.store.inspect()['stop_reason'], 'operator_stop')

    def test_malformed_native_types_and_limit_breach_preserve_previous_state(self):
        self.send()
        good = self.venue.snapshot('test')['orders'][0]
        variants = [dict(good, state=[]), dict(good, quantity=True), dict(good, cumulative_fee=0.0),
                    dict(good, evidence_id=uuid.uuid4().hex, state='PARTIAL', cumulative_quantity=1, cumulative_notional='11')]
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(lab.StateError):
                self.store.ingest(bad)
        self.assertEqual(self.row()['filled'], 0)
        self.assertIsNotNone(self.store.inspect()['stop_reason'])

    def test_concurrent_intent_creation_deduplicates_and_conflicts_remain_rejected(self):
        def prepare():
            store = lab.ExecutionStore(self.path)
            try:
                return store.prepare('same-intent', symbol='TEST', side='BUY', quantity_value=1, limit_price='10.00')
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: prepare(), range(4)))
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(len(self.store.inspect()['orders']), 1)
        with self.assertRaisesRegex(lab.StateError, 'intent_id_conflict'):
            self.prepare('same-intent', qty=2)

    def test_foreign_database_is_not_mutated_and_quantity_precision_is_explicit(self):
        other = self.root/'unrelated.sqlite'
        db = sqlite3.connect(other)
        try:
            db.execute('CREATE TABLE unrelated(x)')
            db.commit()
        finally:
            db.close()
        before = hashlib.sha256(other.read_bytes()).hexdigest()
        with self.assertRaisesRegex(lab.StateError, 'foreign_database_refused'):
            lab.ExecutionStore(other)
        self.assertEqual(hashlib.sha256(other.read_bytes()).hexdigest(), before)
        for options in ({'qty':True}, {'qty':1.5}, {'price':'10.001'}, {'price':'NaN'}):
            with self.subTest(options=options), self.assertRaises(lab.StateError):
                self.prepare(**options)
        self.assertEqual(self.store.inspect()['orders'], [])

    def test_non_simulator_transport_is_refused_before_claim(self):
        self.prepare()
        lab.reconcile(self.store, self.venue)
        with self.assertRaisesRegex(lab.StateError, 'local_simulator_required'):
            lab.submit_once(self.store, object(), 'intent-1')
        self.assertEqual(self.row()['state'], 'PREPARED')

    def test_cancel_unknown_survives_restart_and_cannot_be_reissued(self):
        self.send()
        command = self.store.begin_cancel('intent-1')
        self.store.close()
        self.store = lab.ExecutionStore(self.path)
        self.assertIsNone(self.store.begin_cancel('intent-1'))
        self.assertEqual(self.row()['cancel_id'], command['cancel_id'])
        with self.assertRaisesRegex(lab.StateError, 'unresolved_external_outcome'):
            lab.reconcile(self.store, self.venue)
        self.store.cancel_response('intent-1', command['cancel_id'], False)
        lab.reconcile(self.store, self.venue)
        retry = self.store.begin_cancel('intent-1')
        self.assertNotEqual(retry['cancel_id'], command['cancel_id'])
        self.assertEqual(retry['broker_order_id'], command['broker_order_id'])

    def test_late_fee_is_booked_once_and_overspend_halts_without_hiding_fill(self):
        self.send()
        self.store.ingest(self.update(10, '99', '0.50', 'FILLED'))
        later = self.update(10, '99', '1', 'FILLED')
        self.store.ingest(later)
        self.store.ingest(later)
        self.assertEqual(self.store.inspect()['cash'], '900')
        overspend = self.update(10, '99', '1000', 'FILLED')
        with self.assertRaisesRegex(lab.StateError, 'negative_lab_balance'):
            self.store.ingest(overspend)
        state = self.store.inspect()
        self.assertEqual(state['cash'], '-99')
        self.assertEqual(state['positions'], {'TEST':10})
        self.assertEqual(state['stop_reason'], 'negative_lab_balance')

    def test_expired_and_definitively_rejected_orders_are_terminal(self):
        self.send()
        self.store.ingest(self.update(0, '0', '0', 'EXPIRED'))
        self.assertIsNone(self.store.claim_submit('intent-1'))
        self.assertEqual(self.store.inspect()['reserved_cash'], '0')
        self.prepare('rejected')
        lab.reconcile(self.store, self.venue)
        command = self.store.claim_submit('rejected')
        self.store.reject_submit('rejected', command['claim_id'], 'LAB_SERVER_REJECTED')
        self.assertIsNone(self.store.claim_submit('rejected'))
        lab.reconcile(self.store, self.venue)

    def test_partial_snapshot_cannot_authorize_and_callback_obsoletes_query(self):
        self.send()
        snapshot = self.venue.snapshot(self.store.begin_reconcile())
        snapshot['scope'] = 'OPEN_ORDERS_ONLY'
        with self.assertRaisesRegex(lab.StateError, 'complete_scoped_snapshot_required'):
            self.store.complete_reconcile(snapshot)
        old = self.venue.snapshot(self.store.begin_reconcile())
        self.store.ingest(self.update(2, '19', '0.2', 'PARTIAL'))
        with self.assertRaisesRegex(lab.StateError, 'stale_or_unsolicited'):
            self.store.complete_reconcile(old)
        self.assertEqual(self.row()['filled'], 2)
        lab.reconcile(self.store, self.venue)

    def test_crash_during_initialization_does_not_leave_an_admitted_half_store(self):
        broken = self.root/'interrupted-create.sqlite'
        code = '''import importlib.util,os,sys
spec=importlib.util.spec_from_file_location("create_crash_lab",sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
connect=module.sqlite3.connect
def traced(*args,**kwargs):
 db=connect(*args,**kwargs)
 def crash(sql):
  if sql == "PRAGMA user_version=1": os._exit(74)
 db.set_trace_callback(crash)
 return db
module.sqlite3.connect=traced
module.ExecutionStore.create(sys.argv[2],cash="1000",holdings={},symbols={"TEST":"0.01"})
'''
        child = subprocess.run([sys.executable,'-I','-B','-c',code,str(SCRIPT),str(broken)],capture_output=True,timeout=15)
        self.assertEqual(child.returncode,74,child.stderr)
        with self.assertRaisesRegex(lab.StateError,'foreign_database_refused'):
            lab.ExecutionStore(broken)
        with self.assertRaises(FileExistsError):
            lab.ExecutionStore.create(broken,cash='1000',holdings={},symbols={'TEST':'0.01'})

    def test_reconciliation_and_dispatch_expire_without_sending(self):
        self.prepare()
        snapshot = self.venue.snapshot(self.store.begin_reconcile())
        later = lab.time.monotonic() + 6
        with patch.object(lab.time,'monotonic',return_value=later):
            with self.assertRaisesRegex(lab.StateError,'stale_or_unsolicited'):
                self.store.complete_reconcile(snapshot)
        lab.reconcile(self.store,self.venue)
        later = lab.time.monotonic() + 6
        with patch.object(lab.time,'monotonic',return_value=later):
            with self.assertRaisesRegex(lab.StateError,'fresh_reconciliation_required'):
                lab.submit_once(self.store,self.venue,'intent-1')
        self.assertEqual(self.row()['state'],'PREPARED')
        self.assertEqual(self.count(),0)

    def test_sell_partial_fills_reserve_remaining_shares_and_book_proceeds_once(self):
        self.send()
        self.store.ingest(self.update(10,'99','1','FILLED'))
        self.store.stop('operator_stop')
        self.prepare('reduce',side='SELL',qty=5)
        lab.reconcile(self.store,self.venue)
        self.assertEqual(lab.submit_once(self.store,self.venue,'reduce'),'ACKNOWLEDGED')
        order = next(row for row in self.store.inspect()['orders'] if row['intent_id']=='reduce')
        part = self.venue.update(order['broker_id'],filled=2,notional='21',fee='0.2',state='PARTIAL')
        self.store.ingest(part)
        self.store.ingest(part)
        state = self.store.inspect()
        self.assertEqual((state['cash'],state['positions']),('920.8',{'TEST':8}))
        self.assertEqual(state['reserved_sell_quantities'],{'TEST':3})
        self.prepare('oversell',side='SELL',qty=6)
        lab.reconcile(self.store,self.venue)
        with self.assertRaisesRegex(lab.StateError,'reduce_only_sell_exceeded'):
            self.store.claim_submit('oversell')
        self.store.ingest(self.venue.update(order['broker_id'],filled=5,notional='52',fee='0.5',state='FILLED'))
        lab.reconcile(self.store,self.venue)
        state = self.store.inspect()
        self.assertEqual((state['cash'],state['positions']),('951.5',{'TEST':5}))
        self.assertEqual(state['reserved_sell_quantities'],{})
        self.assertEqual(state['stop_reason'],'operator_stop')


if __name__ == '__main__':
    unittest.main()
