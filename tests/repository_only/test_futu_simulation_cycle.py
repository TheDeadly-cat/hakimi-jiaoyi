"""One-cycle driver contracts; contexts and statements are synthetic fixtures."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


cycle=load('cycle_tested',Path(__file__).resolve().parents[2]/'tools/futu_simulation_cycle.py')
fixture=load('cycle_transport_fixtures',Path(__file__).with_name('test_futu_simulation_adapter.py'))


class OneOfficialCycleDriverContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hakimi-cycle-contract-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.database=self.root/'cycle.sqlite'
        self.context=fixture.Context();self.quote=fixture.Quote();self.factory_calls=0
        self.profile=dict(schema_version='futu-simulation-binding-v1',account_id='123',market='US',symbol='US.AMD',
            host='127.0.0.1',port=11111,history_start=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        self.authorization=dict(mode=cycle.adapter_module.MODE,account_id='123',intent_id=cycle.INTENT,
            payload_sha256=cycle.core.fingerprint(cycle.PAYLOAD),exclusive_account_control=True,
            operations=['SUBMIT_ONCE','CANCEL_OWN_ORDER'],expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat())

    def factory(self,profile):
        self.factory_calls+=1
        return cycle.adapter_module.FutuAdapter(self.context,profile,quote_context=self.quote,_lease_root=self.root/'lease')

    def phase(self,phase,**kwargs):
        return cycle.run_phase(phase,self.database,_sdk_factory=self.factory,**kwargs)

    def prepare(self):return self.phase('prepare',profile=self.profile)

    def test_prepare_freezes_actual_read_anchor_without_sending_or_authorizing(self):
        receipt=self.prepare()
        self.assertEqual(receipt['status'],'PREPARED_AWAITING_SEPARATE_AUTHORIZATION')
        self.assertEqual(receipt['proposal']['payload'],cycle.PAYLOAD)
        self.assertEqual(receipt['order_dispatch_attempts'],0)
        self.assertEqual(self.context.sent,[])
        self.assertFalse(receipt['official_cycle_complete'])
        self.assertNotIn('authorization',receipt)

    def test_unauthorized_submit_fails_before_sdk_connection_or_claim(self):
        self.prepare();before=self.factory_calls
        with self.assertRaisesRegex(cycle.Error,'separate_official_simulation_order_authorization'):
            self.phase('submit')
        self.assertEqual(before,self.factory_calls)
        store=cycle.adapter_module.SimulationStore(self.database)
        try:self.assertIsNone(store._row(cycle.INTENT)['claim_id'])
        finally:store.close()

    def test_lost_response_reopen_query_and_duplicate_probe_never_resend(self):
        self.prepare();self.context.lose=True
        submitted=self.phase('submit',authorization=self.authorization)
        self.assertEqual(submitted['status'],'SUBMIT_UNKNOWN_NO_RESEND')
        self.assertEqual(submitted['order_dispatch_attempts'],1)
        recovered=self.phase('recover')
        self.assertEqual(recovered['error'],'futu_fee_or_gross_notional_evidence_unknown')
        self.assertEqual(recovered['state']['orders'][0]['broker_id'],'987')
        self.assertEqual(recovered['order_dispatch_attempts'],0)
        before=self.factory_calls
        duplicate=self.phase('duplicate-probe')
        self.assertEqual(duplicate['status'],'DUPLICATE_DURABLE_CLAIM_REFUSED_NO_TRANSPORT')
        self.assertEqual(self.factory_calls,before)
        self.assertEqual(len(self.context.sent),1)
        again=self.phase('submit',authorization=self.authorization)
        self.assertEqual(again['status'],'ALREADY_ATTEMPTED_NO_SEND')
        self.assertEqual(again['order_dispatch_attempts'],0)

    def test_cancel_retains_exact_ack_and_never_claims_terminal_accounting(self):
        self.prepare();self.phase('submit',authorization=self.authorization)
        self.phase('recover')
        cancelled=self.phase('cancel',authorization=self.authorization)
        self.assertEqual(cancelled['status'],'CANCEL_ACK_NOT_TERMINAL')
        self.assertEqual(cancelled['cancel_dispatch_attempts'],1)
        self.assertFalse(cancelled['official_cycle_complete'])
        store=cycle.adapter_module.SimulationStore(self.database)
        try:
            raw=json.loads(store.db.execute("SELECT payload FROM events WHERE kind='FUTU_CANCEL_SYNC_RESPONSE'").fetchone()[0])
            self.assertEqual(raw['rows'],[dict(order_id='987',trd_env='SIMULATE')])
        finally:store.close()
        second=self.phase('cancel',authorization=self.authorization)
        self.assertEqual(second['cancel_dispatch_attempts'],0)

    def test_changed_source_stops_before_opening_sdk(self):
        self.prepare();before=self.factory_calls
        changed=cycle.source_hashes()|{'futu_simulation_cycle.py':'0'*64}
        with mock.patch.object(cycle,'source_hashes',return_value=changed):
            receipt=self.phase('submit',authorization=self.authorization)
        self.assertEqual(receipt['error'],'cycle_source_or_frozen_terms_changed')
        self.assertEqual(before,self.factory_calls)
        self.assertEqual(self.context.sent,[])

    def test_reprepare_does_not_replace_existing_database(self):
        self.prepare()
        before=self.database.read_bytes()
        receipt=self.prepare()
        self.assertEqual(receipt['error'],'cycle_database_already_exists')
        self.assertEqual(before,self.database.read_bytes())


if __name__=='__main__':unittest.main()
