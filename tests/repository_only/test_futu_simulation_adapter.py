"""Transport/SQLite contracts only; fixtures are not official paper evidence."""
from datetime import datetime, timedelta, timezone
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('futu_adapter_tested',Path(__file__).resolve().parents[2]/'tools/futu_simulation_adapter.py')
futu=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(futu)


class Context:
    def __init__(self):
        self.account={'acc_id':123,'trd_env':'SIMULATE','acc_status':'ACTIVE','sim_acc_type':'STOCK_AND_OPTION','trdmarket_auth':['US']}
        self.orders=[];self.cash='1000';self.display_currency='USD';self.positions=[];self.sent=[];self.cancelled=[];self.callback=None;self.lose=False;self.changed=False;self.read_count=0
    def get_acc_list(self):return 0,[self.account]
    def _bound(self,kwargs):
        assert kwargs['trd_env']=='SIMULATE' and kwargs['acc_id']==123 and 'acc_index' not in kwargs
    def order_list_query(self,**kwargs):self._bound(kwargs);return 0,list(self.orders)
    def history_order_list_query(self,**kwargs):self._bound(kwargs);return 0,list(self.orders)
    def accinfo_query(self,**kwargs):
        self._bound(kwargs);self.read_count+=1
        return 0,[{'currency':self.display_currency,'us_cash':str(int(self.cash)+self.read_count) if self.changed else self.cash,'power':'999999'}]
    def position_list_query(self,**kwargs):self._bound(kwargs);return 0,self.positions
    def acctradinginfo_query(self,**kwargs):self._bound(kwargs);return 0,[dict(max_cash_buy=1,max_position_sell=0,max_cash_and_margin_buy=1000,max_sell_short=1000)]
    def place_order(self,**kwargs):
        self._bound(kwargs);self.sent.append(kwargs)
        row=dict(order_id='987',code=kwargs['code'],trd_side=kwargs['trd_side'],order_type=kwargs['order_type'],order_status='SUBMITTED',
            qty=kwargs['qty'],price=kwargs['price'],dealt_qty=0,dealt_avg_price=0,remark=kwargs['remark'],updated_time='2026-09-13 12:00:00',time_in_force='DAY')
        self.orders=[row]
        if self.callback:self.callback({**row,'trd_env':'SIMULATE','acc_id':123})
        if self.lose:raise TimeoutError('fixture response lost after acceptance')
        return 0,[row]
    def modify_order(self,**kwargs):self._bound(kwargs);self.cancelled.append(kwargs);return 0,[{'order_id':kwargs['order_id']}]
    def close(self):pass


class Quote:
    def __init__(self):self.state='AFTERNOON';self.stock_id=205816
    def get_stock_basicinfo(self,**kwargs):return 0,[dict(code='US.AMD',stock_id=self.stock_id,exchange_type='US_NASDAQ',stock_type='STOCK',lot_size=1)]
    def get_market_snapshot(self,**kwargs):return 0,[dict(code='US.AMD',equity_valid=True,price_spread=0.01,suspension=False)]
    def get_market_state(self,**kwargs):return 0,[dict(code='US.AMD',market_state=self.state)]
    def close(self):pass


class FutuSimulationContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hakimi-futu-contract-');self.root=Path(self.tmp.name)
        self.profile=dict(schema_version='futu-simulation-binding-v1',account_id='123',market='US',symbol='US.AMD',host='127.0.0.1',port=11111,history_start=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        self.ctx=Context();self.quote=Quote();self.adapter=futu.FutuAdapter(self.ctx,self.profile,quote_context=self.quote,_lease_root=self.root/'leases')
        self.path=self.root/'official.sqlite'
        self.store=futu.SimulationStore.create_bound(self.path,profile=self.profile,cash='1000',holdings={},max_order_notional='100',fee_reserve='3',anchor=self.adapter.stable_reads())
        self.store.prepare('one',symbol='US.AMD',side='BUY',quantity_value=1,limit_price='10')
        payload=json.loads(self.store._row('one')['payload'])
        self.authorization=dict(mode=futu.MODE,account_id='123',intent_id='one',payload_sha256=futu.core.fingerprint(payload),
            expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat().replace('+00:00','Z'),exclusive_account_control=True,operations=['SUBMIT_ONCE','CANCEL_OWN_ORDER'])
    def tearDown(self):
        self.adapter.close();self.store.close();self.tmp.cleanup()
    def submit(self,**kwargs):return self.adapter.submit_once(self.store,'one',authorization=self.authorization,**kwargs)
    def statement(self,qty=0,notional='0',fee='0'):
        return dict(source_kind='OWNER_PROVIDED_SIMULATION_STATEMENT',source_sha256=hashlib.sha256(b'contract fixture only').hexdigest(),operator_verified=True,order_id='987',cumulative_quantity=qty,cumulative_notional=notional,cumulative_fee=fee)

    def test_readonly_preflight_never_calls_order_transport(self):
        result=self.adapter.stable_reads()
        self.assertEqual(result['scope'],'REPEATED_SCOPED_READS_NOT_ATOMIC')
        self.assertEqual(result['value']['cash'],'1000')
        self.assertEqual(self.ctx.sent,[])
    def test_real_and_wrong_accounts_are_rejected(self):
        for change in ({'trd_env':'REAL'},{'acc_id':124},{'trdmarket_auth':['HK']},{'acc_status':'DISABLED'}):
            with self.subTest(change=change):
                ctx=Context();ctx.account.update(change)
                with self.assertRaises(futu.Error):futu.FutuAdapter(ctx,self.profile,_lease_root=self.root/'leases')
                self.assertEqual(ctx.sent,[])
    def test_binding_rejects_remote_default_and_unsupported_market(self):
        for change in ({'account_id':'0'},{'account_id':123},{'port':True},{'host':'localhost'},{'market':'HK'},{'symbol':'US.AAPL'}):
            with self.subTest(change=change),self.assertRaises(futu.Error):futu.binding({**self.profile,**change})
    def test_no_authorization_never_claims_or_sends(self):
        with self.assertRaises(futu.Error):self.adapter.submit_once(self.store,'one',authorization={})
        self.assertEqual(self.store._row('one')['state'],'PREPARED');self.assertEqual(self.ctx.sent,[])
    def test_expired_changed_payload_or_nonexclusive_authorization_rejected(self):
        for change in ({'expires_at':'2020-01-01T00:00:00Z'},{'payload_sha256':'b'*64},{'exclusive_account_control':False},{'account_id':'124'}):
            with self.subTest(change=change),self.assertRaises(futu.Error):self.adapter.submit_once(self.store,'one',authorization={**self.authorization,**change})
        self.assertEqual(self.ctx.sent,[])
    def test_submit_uses_explicit_simulation_account_limit_day_rth_no_adjustment(self):
        self.assertEqual(self.submit(),'ORDER_RECORDED_ACCOUNTING_UNKNOWN')
        sent=self.ctx.sent[0]
        self.assertEqual({k:sent[k] for k in ('trd_env','acc_id','order_type','time_in_force','session','adjust_limit','fill_outside_rth')},
            dict(trd_env='SIMULATE',acc_id=123,order_type='NORMAL',time_in_force='DAY',session='RTH',adjust_limit=0,fill_outside_rth=False))
        self.assertNotIn('acc_index',sent)
    def test_callback_before_sync_response_keeps_fee_unknown(self):
        self.ctx.callback=self.adapter.callbacks.put
        self.submit()
        kinds=[r[0] for r in self.store.db.execute('SELECT kind FROM events ORDER BY sequence')]
        self.assertLess(kinds.index('SUBMISSION_MAY_REACH_VENUE'),kinds.index('FUTU_ORDER_RAW'))
        self.assertLess(kinds.index('FUTU_ORDER_RAW'),kinds.index('FUTU_SYNC_RESPONSE'))
        result=self.store.inspect();self.assertIsNone(result['cash']);self.assertEqual(result['accounting_pending_order_ids'],['987'])
        with self.assertRaisesRegex(futu.Error,'evidence_unknown'):self.adapter.reconcile(self.store)
    def test_response_lost_restart_queries_identity_without_resubmission(self):
        self.ctx.lose=True;self.assertEqual(self.submit(),'SUBMIT_UNKNOWN_NO_RESEND')
        self.store.close();self.store=futu.SimulationStore(self.path)
        self.assertEqual(self.submit(),'ALREADY_ATTEMPTED_NO_SEND')
        with self.assertRaisesRegex(futu.Error,'evidence_unknown'):self.adapter.reconcile(self.store)
        self.assertEqual(self.store._row('one')['broker_id'],'987');self.assertEqual(len(self.ctx.sent),1)
    def test_discarded_sync_response_is_labelled_fault_injection(self):
        self.assertEqual(self.submit(discard_sync_response=True),'SUBMIT_UNKNOWN_NO_RESEND')
        record=json.loads(self.store.db.execute("SELECT payload FROM events WHERE kind='FUTU_SYNC_RESPONSE'").fetchone()[0])
        self.assertTrue(record['discarded_for_fault_test']);self.assertEqual(len(self.ctx.sent),1)
    def test_missing_fees_are_not_automatically_filled_with_zero(self):
        self.submit()
        with self.assertRaises(futu.Error):self.store.admit_statement('987',statement=self.statement()|{'cumulative_fee':None},source_bytes=b'contract fixture only')
        self.assertEqual(self.store.accounting_pending(),['987'])
        self.assertEqual(self.store._row('one')['state'],'SUBMIT_UNKNOWN')
    def test_statement_and_terminal_query_use_existing_ledger_and_reconcile(self):
        self.submit();self.adapter.cancel(self.store,'one',authorization=self.authorization)
        self.assertEqual(self.store._row('one')['cancel_state'],'ACK_RECEIVED')
        self.ctx.orders[0].update(order_status='CANCELLED_ALL',updated_time='2026-09-13 12:00:01')
        with self.assertRaises(futu.Error):self.adapter.reconcile(self.store)
        self.store.admit_statement('987',statement=self.statement(),source_bytes=b'contract fixture only')
        result=self.adapter.reconcile(self.store)
        self.assertFalse(result['atomic_snapshot_claimed']);self.assertEqual(result['state']['orders'][0]['state'],'CANCELLED')
        self.assertEqual(result['state']['orders'][0]['cancel_state'],'CONFIRMED')
    def test_fill_and_fee_statement_preserve_exact_core_accounting(self):
        self.submit();self.ctx.orders[0].update(order_status='FILLED_ALL',dealt_qty=1,dealt_avg_price=9.5,updated_time='2026-09-13 12:00:01')
        with self.assertRaises(futu.Error):self.adapter.reconcile(self.store)
        self.store.admit_statement('987',statement=self.statement(1,'9.5','2'),source_bytes=b'contract fixture only')
        self.ctx.cash='988.5';self.ctx.positions=[dict(acc_id=123,currency='USD',position_side='LONG',code='US.AMD',qty=1)]
        self.assertEqual(self.adapter.reconcile(self.store)['state']['cash'],'988.5')
    def test_conflicting_binding_persists_stop_after_rollback(self):
        self.submit();self.ctx.orders[0]['code']='US.AAPL'
        with self.assertRaises(futu.Error):self.store.observe_order(self.ctx.orders[0],origin='FIXTURE')
        self.store.close();self.store=futu.SimulationStore(self.path)
        self.assertEqual(self.store.inspect()['stop_reason'],'futu_order_evidence_conflict')
    def test_changed_scans_and_foreign_order_fail_closed(self):
        self.ctx.changed=True
        with self.assertRaises(futu.Error):self.submit()
        self.assertEqual(self.ctx.sent,[])
    def test_account_lease_blocks_second_adapter(self):
        other=futu.FutuAdapter(Context(),self.profile,_lease_root=self.root/'leases')
        try:
            self.adapter.acquire_authority()
            with self.assertRaises(futu.Error):other.acquire_authority()
        finally:other.close()
    def test_local_simulator_cannot_adopt_official_database_or_command(self):
        with self.assertRaises(futu.Error):futu.core.ExecutionStore(self.path)
        with self.assertRaises(futu.Error):futu.core.submit_once(self.store,self.ctx,'one')
    def test_first_cycle_does_not_expand_symbol_quantity_or_price_rules(self):
        for kwargs in (dict(symbol='US.AAPL',quantity_value=1,limit_price='10'),dict(symbol='US.AMD',quantity_value=2,limit_price='10'),dict(symbol='US.AMD',quantity_value=True,limit_price='10'),dict(symbol='US.AMD',quantity_value=1,limit_price='10.001')):
            with self.subTest(kwargs=kwargs),self.assertRaises(futu.Error):self.store.prepare('other',side='BUY',**kwargs)
    def test_instrument_identity_change_or_closed_market_prevents_send(self):
        self.quote.stock_id=9
        with self.assertRaises(futu.Error):self.submit()
        self.quote.stock_id=205816;self.quote.state='CLOSED'
        with self.assertRaises(futu.Error):self.submit()
        self.assertEqual(self.ctx.sent,[])
    def test_starting_other_holdings_do_not_invent_tradable_tick_rules(self):
        self.ctx.positions=[dict(acc_id=123,currency='USD',position_side='LONG',code='US.MSFT',qty=2)]
        store=futu.SimulationStore.create_bound(self.root/'anchor.sqlite',profile=self.profile,cash='1000',holdings={'US.MSFT':2},max_order_notional='100',fee_reserve='3',anchor=self.adapter.stable_reads())
        try:
            self.assertEqual(store.config['symbols'],{'US.AMD':'0.01'})
            self.assertEqual(store.inspect()['positions'],{'US.MSFT':2})
            with self.assertRaises(futu.Error):store.prepare('bad',symbol='US.MSFT',side='SELL',quantity_value=1,limit_price='10')
        finally:store.close()
    def test_native_usd_cash_does_not_depend_on_display_currency(self):
        self.ctx.display_currency='N/A'
        self.assertEqual(self.adapter.stable_reads()['value']['cash'],'1000')
        self.ctx.cash='N/A'
        with self.assertRaises(futu.Error):
            self.adapter.stable_reads()
    def test_margin_capacity_does_not_substitute_for_cash_capacity(self):
        self.ctx.acctradinginfo_query=lambda **kwargs:(0,[dict(max_cash_buy=0,max_cash_and_margin_buy=1000)])
        with self.assertRaisesRegex(futu.Error,'cash_only'):self.submit()
        self.assertEqual(self.ctx.sent,[])
        self.assertEqual(self.store._row('one')['state'],'PREPARED')
    def test_cancel_own_order_does_not_require_an_open_quote_market(self):
        self.submit();self.quote.state='AFTER_HOURS_END'
        self.assertEqual(self.adapter.cancel(self.store,'one',authorization=self.authorization),'CANCEL_ACK_NOT_TERMINAL')
        self.assertEqual(len(self.ctx.cancelled),1)
    def test_anchor_is_bound_to_account_cash_positions_and_empty_orders(self):
        anchor=self.adapter.stable_reads();anchor['binding_sha256']='c'*64
        with self.assertRaises(futu.Error):futu.SimulationStore.create_bound(self.root/'bad.sqlite',profile=self.profile,cash='1000',holdings={},max_order_notional='100',fee_reserve='3',anchor=anchor)
        self.assertFalse((self.root/'bad.sqlite').exists())
    def test_statement_digest_requires_actual_retained_original_bytes(self):
        self.submit()
        with self.assertRaises(futu.Error):self.store.admit_statement('987',statement=self.statement(),source_bytes=b'different fixture')
        self.assertEqual(self.store.accounting_pending(),['987'])
    def test_stale_callback_does_not_replace_later_cumulative_observation(self):
        self.submit();new={**self.ctx.orders[0],'order_status':'FILLED_ALL','dealt_qty':1,'dealt_avg_price':9.5,'updated_time':'2026-09-13 12:00:01'}
        self.store.observe_order(new,origin='FIXTURE')
        self.assertEqual(self.store.observe_order(self.ctx.orders[0],origin='FIXTURE'),'STALE_RETAINED')
        value=json.loads(self.store.db.execute('SELECT projection FROM futu_orders').fetchone()[0]);self.assertEqual(value['dealt_qty'],1)
    def test_closed_authority_cannot_be_recreated_by_copying_database(self):
        copy_path=self.root/'copied.sqlite'
        target=futu.core.sqlite3.connect(copy_path)
        self.store.db.backup(target);target.close()
        self.submit();self.adapter.close()
        copied=futu.SimulationStore(copy_path)
        other=futu.FutuAdapter(Context(),self.profile,quote_context=Quote(),_lease_root=self.root/'leases')
        try:
            with self.assertRaisesRegex(futu.Error,'different_database'):other.submit_once(copied,'one',authorization=self.authorization)
            self.assertEqual(other.context.sent,[])
        finally:other.close();copied.close()


if __name__=='__main__':unittest.main()
