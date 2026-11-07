"""Only new fictional daily sequences. No provider, broker, server or old runs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
from types import ModuleType
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_continuous_replay import HistoricalReplay, ReplayError, MODEL, digest, encoded


class Crash(BaseException):
    pass


def data(count=34, start=100):
    bars = []
    first = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for i in range(count):
        opening = first + timedelta(days=i, hours=14, minutes=30)
        closing = first + timedelta(days=i, hours=21)
        bars.append(dict(date=opening.date().isoformat(), open_at=int(opening.timestamp()*1000),
            close_at=int(closing.timestamp()*1000), open=str(start+i-1), high=str(start+i+1),
            low=str(start+i-2), close=str(start+i), volume="1000", complete=True))
    return dict(security_id="SYNTHETIC:TEST", price_basis="RAW_UNADJUSTED", calendar_id="EXPLICIT_SYNTHETIC_SESSIONS",
                observed_at=bars[-1]["close_at"]+1000, corporate_actions=[], evidence_kind="SYNTHETIC_TEST", bars=bars)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-new-replay-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.path = self.root / "historical-replay" / "new-account.sqlite"
        self.now = datetime(2026, 10, 30, 1, tzinfo=timezone.utc)
        self.binding = {"strategy_id":"fixture-rule", "params":{"threshold":100}, "source_sha256":"a"*64}
        self.binding_hash = digest(self.binding)
        self.calls = []
        self.dataset = data()
        self.accounts = []
        self.addCleanup(self.close_all)
        network = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        network.start(); self.addCleanup(network.stop)

    def close_all(self):
        for account in self.accounts:
            try: account.close()
            except sqlite3.ProgrammingError: pass

    def signal(self, prefix, position):
        self.calls.append((deepcopy(prefix), deepcopy(position)))
        close = float(prefix[-1]["close"])
        action = "EXIT" if position["has_position"] and close < 100 else "BUY" if not position["has_position"] and close >= 100 else "HOLD"
        return dict(action=action, reason="fictional-threshold")

    def create(self, **values):
        options = dict(account_id="new-replay-0001", initial_cash="1000", unit_quantity=1, fee_rate="0", slippage_bps="0",
            strategy_binding=self.binding, dataset=self.dataset, signal_fn=self.signal,
            source_guard=lambda:self.binding_hash, clock=lambda:self.now)
        options.update(values)
        account = HistoricalReplay.create(self.path, **options)
        self.accounts.append(account)
        return account

    def reopen(self):
        account = HistoricalReplay(self.path, signal_fn=self.signal, source_guard=lambda:self.binding_hash, clock=lambda:self.now)
        self.accounts.append(account)
        return account

    def seed(self, account, count=30):
        return account.seed_close("request-seed-0001", expected_head=account.snapshot()["head"], seed_count=count)

    def test_seed_only_signals_then_next_open_fills_before_new_close_signal(self):
        self.dataset["bars"][30].update(open="150", high="151", low="0.5", close="1")
        self.dataset["bars"][31].update(open="120", high="121", low="118", close="119")
        account = self.create()
        self.assertEqual(account.snapshot()["phase"], "SEED_REQUIRED")
        self.assertEqual(self.calls, [])
        seed = self.seed(account)
        self.assertEqual(seed["outcome"]["status"], "SEED_SIGNAL_ONLY")
        self.assertIsNone(seed["outcome"]["fill"])
        self.assertEqual(account.snapshot()["state"]["quantity"], 0)
        first = account.advance_next("request-step-0001", expected_head=seed["head"])
        self.assertEqual(first["outcome"]["fill"]["fill_price"], "150.00000000")
        self.assertEqual(first["outcome"]["signal"]["value"]["action"], "EXIT")
        self.assertEqual(account.snapshot()["state"]["quantity"], 1)
        second = account.advance_next("request-step-0002", expected_head=first["head"])
        self.assertEqual(second["outcome"]["fill"]["fill_price"], "120.00000000")
        self.assertEqual(account.snapshot()["state"]["cash"], "970.00000000")
        self.assertEqual(account.snapshot()["state"]["quantity"], 0)
        self.assertEqual([len(prefix) for prefix,_ in self.calls], [30,31,32])
        self.assertTrue(self.calls[1][1]["has_position"])
        self.assertTrue(all(row["date"] <= prefix[-1]["date"] for prefix,_ in self.calls for row in prefix))

    def test_historical_event_clock_is_never_replaced_with_real_recording_time(self):
        account = self.create(); seed = self.seed(account)
        step = account.advance_next("request-clock-0001", expected_head=seed["head"])
        fill = step["outcome"]["fill"]
        self.assertEqual(fill["signal_at"], self.dataset["bars"][29]["close_at"])
        self.assertEqual(fill["execution_at"], self.dataset["bars"][30]["open_at"])
        self.assertEqual(account.snapshot()["state"]["event_at"], self.dataset["bars"][30]["close_at"])
        self.assertTrue(all(event["recorded_at"].startswith("2026-10-30") for event in account.history()["items"]))
        self.assertLess(fill["execution_at"], int(datetime(2021,1,1,tzinfo=timezone.utc).timestamp()*1000))
        self.assertNotIn('quote_max_age_ms', encoded(account.config))

    def test_duplicate_request_and_stale_head_cannot_advance_twice(self):
        account = self.create(); seed = self.seed(account)
        step = account.advance_next("request-once-0001", expected_head=seed["head"])
        before, calls = self.path.read_bytes(), len(self.calls)
        self.assertEqual(account.advance_next("request-once-0001", expected_head=seed["head"]), step)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaisesRegex(ReplayError, "request_id_conflict"):
            account.advance_next("request-once-0001", expected_head=step["head"])
        with self.assertRaisesRegex(ReplayError, "expected_head_changed"):
            account.advance_next("request-other-0001", expected_head=seed["head"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_response_lost_after_commit_reopens_with_receipt_and_no_recalculation(self):
        account = self.create(); seed = self.seed(account)
        with patch.object(account, '_fault', side_effect=lambda phase: (_ for _ in ()).throw(Crash()) if phase=='after_commit' else None):
            with self.assertRaises(Crash): account.advance_next("request-lost-0001", expected_head=seed["head"])
        calls = len(self.calls)
        saved = account.receipt("request-lost-0001")
        account.close(); reopened = self.reopen()
        self.assertEqual(reopened.snapshot()["phase"], "RECOVERY_REQUIRED")
        self.assertEqual(reopened.receipt("request-lost-0001"), saved)
        recovered = reopened.reconcile("request-reconcile-0001", expected_head=saved["head"])
        self.assertEqual(recovered["outcome"]["abandoned_request_ids"], [])
        self.assertEqual(reopened.snapshot()["phase"], "PAUSED")
        resumed = reopened.resume("request-resume-0001", expected_head=recovered["head"])
        self.assertEqual(resumed["outcome"]["computed_steps"], 0)
        self.assertEqual(reopened.advance_next("request-lost-0001", expected_head=seed["head"]), saved)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(reopened.snapshot()["state"]["cursor"], 30)

    def test_crash_after_intent_requires_reconcile_and_resume_without_fabricated_fill(self):
        account = self.create(); seed = self.seed(account)
        with patch.object(account, '_fault', side_effect=lambda phase: (_ for _ in ()).throw(Crash()) if phase=='after_intent' else None):
            with self.assertRaises(Crash): account.advance_next("request-pending-0001", expected_head=seed["head"])
        self.assertEqual(len(self.calls), 1)
        account.close(); reopened = self.reopen()
        state = reopened.snapshot()
        self.assertEqual((state["state"]["cursor"],state["state"]["quantity"]), (29,0))
        with self.assertRaisesRegex(ReplayError, "reconciliation_no_replay"):
            reopened.advance_next("request-pending-0001", expected_head=seed["head"])
        recovered = reopened.reconcile("request-reconcile-0001", expected_head=state["head"])
        self.assertEqual(reopened.receipt("request-pending-0001")["outcome"]["status"], "ABANDONED_NOT_APPLIED_AFTER_RECONCILIATION")
        self.assertEqual(len(self.calls), 1)
        with self.assertRaisesRegex(ReplayError, "paused"):
            reopened.advance_next("request-still-paused", expected_head=recovered["head"])
        resumed = reopened.resume("request-resume-0001", expected_head=recovered["head"])
        step = reopened.advance_next("request-new-step-0001", expected_head=resumed["head"])
        self.assertEqual(step["outcome"]["index"], 30)
        self.assertEqual(reopened.snapshot()["state"]["quantity"], 1)

    def test_crash_after_calculation_does_not_publish_partial_accounting(self):
        account = self.create(); seed = self.seed(account)
        with patch.object(account, '_fault', side_effect=lambda phase: (_ for _ in ()).throw(Crash()) if phase=='after_calculation' else None):
            with self.assertRaises(Crash): account.advance_next("request-calculated-0001", expected_head=seed["head"])
        self.assertEqual(account.snapshot()["state"]["cash"], "1000.00000000")
        self.assertEqual(account.snapshot()["state"]["quantity"], 0)
        calls = len(self.calls)
        account.reconcile("request-reconcile-0001", expected_head=account.snapshot()["head"])
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(account.snapshot()["phase"], "PAUSED")

    def test_pause_during_signal_calculation_prevents_atomic_step_commit(self):
        account = self.create(); seed = self.seed(account)
        entered, release = threading.Event(), threading.Event()
        def blocked(prefix, position):
            entered.set()
            if not release.wait(3): raise RuntimeError('fixture release missing')
            return self.signal(prefix,position)
        account.signal_fn = blocked
        with ThreadPoolExecutor(max_workers=2) as pool:
            stepping = pool.submit(account.advance_next,"request-inflight-0001",expected_head=seed["head"])
            try:
                self.assertTrue(entered.wait(1))
                current = account.snapshot()
                self.assertEqual(current["phase"], "PROCESSING")
                paused = pool.submit(account.pause,"request-pause-0001",expected_head=current["head"],reason="explicit pause").result(timeout=1)
                self.assertFalse(paused["outcome"]["broker_orders_cancelled"])
            finally:
                release.set()
            with self.assertRaisesRegex(ReplayError,"reconciliation_required"): stepping.result(timeout=2)
        self.assertEqual(account.snapshot()["state"]["quantity"], 0)
        self.assertEqual(account.snapshot()["phase"], "ERROR_RECONCILIATION_REQUIRED")

    def test_consumed_prefix_revision_rejected_future_tail_explicitly_adoptable(self):
        account = self.create(); seed = self.seed(account)
        revised = deepcopy(self.dataset); revised['bars'][0].update(close='700',high='701')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ReplayError,"consumed_prefix_revision"):
            account.adopt_input("request-revise-0001",expected_head=seed['head'],dataset=revised)
        self.assertEqual(self.path.read_bytes(),before)
        tail=deepcopy(self.dataset);tail['bars'][31].update(open='170',high='171')
        adopted=account.adopt_input("request-tail-0001",expected_head=seed['head'],dataset=tail)
        self.assertEqual(adopted['outcome']['protected_prefix_rows'],30)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(account.snapshot()['state']['cash'],'1000.00000000')
        self.assertEqual(account.history()["items"][2]['state_after']['pending_signal'],seed['outcome']['signal'])

    def test_waiting_data_append_has_no_automatic_step(self):
        self.dataset=data(30);account=self.create();seed=self.seed(account)
        self.assertEqual(account.snapshot()['phase'],'WAITING_DATA')
        with self.assertRaisesRegex(ReplayError,'waiting_for_next_complete'):
            account.advance_next('request-no-data-0001',expected_head=seed['head'])
        adopted=account.adopt_input('request-append-0001',expected_head=seed['head'],dataset=data(31))
        self.assertEqual(account.snapshot()['phase'],'READY_FOR_EXPLICIT_STEP')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(account.snapshot()['state']['quantity'],0)
        self.assertEqual(adopted['outcome']['status'],'INPUT_VERSION_ADOPTED_NO_STEP')

    def test_source_change_blocks_new_step_but_saved_reads_remain_available(self):
        account=self.create();seed=self.seed(account)
        self.binding_hash='f'*64
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ReplayError,'signal_source_changed'):
            account.advance_next('request-drift-0001',expected_head=seed['head'])
        account.history();account.snapshot();self.assertEqual(account.receipt('request-seed-0001'),seed)
        self.assertEqual(self.path.read_bytes(),before)

    def test_incomplete_or_unobserved_bars_and_manual_account_database_are_rejected(self):
        for alter in ('incomplete','future','duplicate','action'):
            trial=deepcopy(self.dataset)
            if alter=='incomplete':trial['bars'][-1]['complete']=False
            elif alter=='future':trial['observed_at']=trial['bars'][-1]['close_at']-1
            elif alter=='duplicate':trial['bars'][-1]['date']=trial['bars'][-2]['date']
            else:trial['corporate_actions']=[{'split':'2:1'}]
            with self.subTest(alter=alter),self.assertRaises(ReplayError): self.create(dataset=trial)
            self.assertFalse(self.path.exists())
        self.path.parent.mkdir();db=sqlite3.connect(self.path);db.execute('PRAGMA application_id=1213154609');db.close()
        with self.assertRaisesRegex(ReplayError,'foreign_account'):self.reopen()

    def test_declared_fees_and_slippage_are_accounted_with_no_fractional_or_short_fill(self):
        account=self.create(fee_rate='0.01',slippage_bps='100');seed=self.seed(account)
        step=account.advance_next('request-costs-0001',expected_head=seed['head'])
        fill=step['outcome']['fill']
        self.assertEqual((fill['quantity'],fill['fill_price'],fill['fee']),(1,'130.29000000','1.30290000'))
        self.assertEqual(account.snapshot()['state']['cash'],'868.40710000')
        self.assertEqual(fill['model'],MODEL)
        self.assertTrue(all(value is False for value in account.snapshot()['permissions'].values()))

    def test_event_corruption_is_rejected_without_repair_or_strategy_rerun(self):
        account=self.create();self.seed(account);calls=len(self.calls)
        account.db.execute("UPDATE events SET hash=? WHERE sequence=2",('f'*64,))
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ReplayError,'event_chain_changed'):account.snapshot()
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual(len(self.calls),calls)

    def test_real_original_dual_ma_signal_on_new_fictional_sequence(self):
        from exchange_terminal.services import strategy_signals
        source=Path(strategy_signals.__file__).resolve().parent
        source_hashes={name:sha256((source/name).read_bytes()).hexdigest() for name in ('strategy_signals.py','indicator_math.py')}
        package=ModuleType('replay_original_services');package.__path__=[str(source)]
        with patch.dict(sys.modules,{'replay_original_services':package}):
            original=importlib.import_module('replay_original_services.strategy_signals')
        params={'fast_window':2,'slow_window':3}
        binding={'strategy_id':'dual_ma','params':params,'source_hashes':source_hashes,
                 'fingerprint':original.strategy_signal_fingerprint('dual_ma',params)}
        native=original.build_strategy_signal_fn('dual_ma',params)
        seen=[]
        def guard():
            if any(sha256((source/name).read_bytes()).hexdigest()!=h for name,h in source_hashes.items()):
                raise ReplayError('actual_signal_source_changed')
            original.indicator_math.assert_loaded_source_current()
            return digest(binding)
        def signal(prefix,position):
            seen.append((len(prefix),position['has_position']))
            return native([float(bar['close']) for bar in prefix],float(prefix[-1]['close']),position['has_position'],
                          float(position['entry_price'] or 0),0.0)
        self.dataset['bars'][30].update(open='150',high='151',low='0.5',close='1')
        self.dataset['bars'][31].update(open='120',high='121',low='118',close='119')
        account=self.create(strategy_binding=binding,signal_fn=signal,source_guard=guard)
        seed=self.seed(account)
        self.assertEqual(seed['outcome']['signal']['value'],{'action':'BUY','reason':'fast_ma_above_slow_ma'})
        first=account.advance_next('request-actual-0001',expected_head=seed['head'])
        self.assertEqual(first['outcome']['signal']['value'],{'action':'EXIT','reason':'fast_ma_below_slow_ma'})
        second=account.advance_next('request-actual-0002',expected_head=first['head'])
        self.assertEqual(second['outcome']['fill']['action'],'EXIT')
        self.assertEqual(seen,[(30,False),(31,True),(32,False)])
        self.assertEqual(account.snapshot()['state']['cash'],'970.00000000')
        self.assertEqual({name:sha256((source/name).read_bytes()).hexdigest() for name in source_hashes},source_hashes)


if __name__=='__main__':unittest.main()
