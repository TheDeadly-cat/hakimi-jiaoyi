from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch
from exchange_terminal.services import terminal_continuous_replay as replay
from exchange_terminal.services import terminal_replay_service as trusted
from tests import test_terminal_replay_adapter as fixtures


class APITests(unittest.TestCase):
    setUp=fixtures.TrustedAdapterTests.setUp
    close_all=fixtures.TrustedAdapterTests.close_all
    native_chain=fixtures.TrustedAdapterTests.native_chain
    confirmation=fixtures.TrustedAdapterTests.confirmation

    def prepare(self):
        reference,_,_=self.native_chain()
        api=trusted.ReplayAPI(self.adapter);self.addCleanup(api.close)
        preview=api.read('preview',dict(reference=reference,settings=self.settings))
        body=dict(request_id='api-create-0001',reference=reference,settings=self.settings,confirmation=self.confirmation(preview))
        result=api.mutate('create',body)
        return api,preview,body,result

    def test_creation_receipt_unknown_readback_and_reopen_no_autoresume_or_recreate(self):
        api,preview,body,result=self.prepare();account_id=self.settings['account_id']
        before=self.adapter._path(account_id).read_bytes()
        self.assertEqual(api.read('creation_receipt',dict(account_id=account_id,request_id=body['request_id'])),result)
        self.assertEqual(api.mutate('create',body),result)
        with self.assertRaisesRegex(trusted.AdmissionError,'conflict'):
            api.mutate('create',dict(body,settings=dict(self.settings,unit_quantity=2)))
        self.assertEqual(api.read('status',dict(account_id=account_id))['phase'],'SEED_REQUIRED')
        self.assertEqual(self.adapter._path(account_id).read_bytes(),before)
        api.close();fresh=trusted.ReplayAPI(self.adapter);self.addCleanup(fresh.close)
        self.assertEqual(fresh.read('creation_receipt',dict(account_id=account_id,request_id=body['request_id'])),result)
        status=fresh.read('status',dict(account_id=account_id));self.assertEqual(status['phase'],'RECOVERY_REQUIRED')
        with self.assertRaisesRegex(replay.ReplayError,'reconciliation'):
            fresh.mutate('seed',dict(account_id=account_id,request_id='api-reopen-seed',expected_head=status['head'],seed_count=preview['seed_selection']['recommended_count']))
        checked=fresh.mutate('reconcile',dict(account_id=account_id,request_id='api-reopen-check',expected_head=status['head']))
        resumed=fresh.mutate('resume',dict(account_id=account_id,request_id='api-reopen-resume',expected_head=checked['head']))
        self.assertEqual(resumed['outcome']['computed_steps'],0)
        self.assertIsNone(fresh.read('status',dict(account_id=account_id))['state']['cursor'])

    def test_source_change_and_unavailable_resolver_cannot_remove_pause_reconcile_and_reads(self):
        api,_,_,created=self.prepare();account_id=self.settings['account_id'];api.close()
        fresh=trusted.ReplayAPI(self.adapter);self.addCleanup(fresh.close)
        self.guard_state.update(status='RESTART_REQUIRED',restart_required=True)
        with (patch.object(self.service,'read',side_effect=AssertionError('Unavailable saved-report resolver')),
              patch.object(self.service,'_input',side_effect=AssertionError('No input admission during stop'))):
            before=fresh.read('status',{'account_id':account_id})
            paused=fresh.mutate('pause',dict(account_id=account_id,request_id='api-source-stop',expected_head=before['head'],reason='source changed'))
            checked=fresh.mutate('reconcile',dict(account_id=account_id,request_id='api-source-check',expected_head=paused['head']))
            self.assertEqual(fresh.read('receipt',dict(account_id=account_id,request_id='api-source-stop')),paused)
            self.assertEqual(len(fresh.read('history',dict(account_id=account_id,limit=10))['items']),3)
            with self.assertRaisesRegex(trusted.AdmissionError,'restart_required'):
                fresh.mutate('resume',dict(account_id=account_id,request_id='api-source-resume',expected_head=checked['head']))
        self.assertEqual(fresh.read('status',dict(account_id=account_id))['state']['quantity'],0)

    def test_direct_pause_can_bind_original_head_and_pending_request_while_signal_blocks(self):
        api,preview,_,created=self.prepare();account_id=self.settings['account_id']
        seed=api.mutate('seed',dict(account_id=account_id,request_id='api-seed-0001',expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count']))
        entered,release=threading.Event(),threading.Event()
        original=trusted.signals.build_strategy_signal_fn
        def factory(*args,**kwargs):
            fn=original(*args,**kwargs)
            def blocked(*a,**k):entered.set();release.wait(5);return fn(*a,**k)
            return blocked
        body=dict(account_id=account_id,request_id='api-step-blocked',expected_head=seed['head'])
        with patch.object(trusted.signals,'build_strategy_signal_fn',side_effect=factory),ThreadPoolExecutor(max_workers=1) as pool:
            job=pool.submit(api.mutate,'step',body)
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(api.read('status',dict(account_id=account_id))['phase'],'PROCESSING')
                paused=api.mutate('pause',dict(account_id=account_id,request_id='api-stop-inflight',expected_head=seed['head'],
                    in_flight_request_id=body['request_id'],reason='user paused during calculation'))
                self.assertEqual(paused['outcome']['status'],'PAUSED')
            finally:release.set()
            with self.assertRaisesRegex(replay.ReplayError,'head_or_pause'):job.result(5)
        status=api.read('status',dict(account_id=account_id))
        self.assertEqual(status['state']['cursor'],preview['seed_selection']['recommended_count']-1)
        self.assertEqual(status['state']['quantity'],0)
        self.assertEqual(status['phase'],'ERROR_RECONCILIATION_REQUIRED')
        receipt=api.read('receipt',dict(account_id=account_id,request_id=body['request_id']))
        self.assertEqual(receipt['status'],'PENDING')
        self.assertFalse(receipt['automatic_next_step'])

    def test_all_nine_actual_native_strategies_bind_and_compute_seed_from_verified_saved_input(self):
        from tests.test_terminal_strategy_candidates import spec
        self.fixtures.catalog=[{'id':name,'name':name,'params':spec(name)['params'],
            'capability':{'new_research_allowed':True,'backtest_supported':True}} for name in trusted.CATALOG_ORDER]
        for index,name in enumerate(trusted.CATALOG_ORDER):
            with self.subTest(strategy=name):
                reference,_,_=self.native_chain(strategy_id=name,params=spec(name)['params'])
                settings=dict(self.settings,account_id='nine-rule-'+str(index))
                preview=self.adapter.preview(reference,settings)
                session=self.adapter.create_new(reference,settings,self.confirmation(preview));self.connections.append(session)
                seed=session.seed_close('nine-rule-seed-'+str(index),expected_head=session.snapshot()['head'],seed_count=preview['seed_selection']['recommended_count'])
                step=session.advance_next('nine-rule-step-'+str(index),expected_head=seed['head'])
                self.assertIn(step['outcome']['signal']['value']['action'],{'BUY','EXIT','HOLD'})
                self.assertEqual(preview['research_binding']['strategy_id'],name)
        self.assertEqual(self.fixtures.runner.call_count,9);self.network.assert_not_called()

    def test_actual_verified_input_tail_adoption_preserves_consumed_prefix_and_never_steps(self):
        import base64,json
        from hashlib import sha256
        from decimal import Decimal
        from pathlib import Path
        from hakimi_research.equity_dataset import build_equity_snapshot
        from hakimi_research.input_workflow import _retain
        reference,_,snapshot=self.native_chain()
        api=trusted.ReplayAPI(self.adapter);self.addCleanup(api.close)
        preview=api.read('preview',dict(reference=reference,settings=self.settings))
        created=api.mutate('create',dict(request_id='adopt-create-0001',reference=reference,settings=self.settings,confirmation=self.confirmation(preview)))
        account_id=self.settings['account_id']
        seed=api.mutate('seed',dict(account_id=account_id,request_id='adopt-seed-0001',expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count']))
        def save_amended(row_index):
            csv=base64.b64decode(snapshot['raw_input']['csv_base64']).decode().splitlines()
            columns=csv[row_index+1].split(',');columns[4]=str(Decimal(columns[4])+Decimal('.01'));csv[row_index+1]=','.join(columns)
            manifest=json.loads(base64.b64decode(snapshot['raw_input']['manifest_base64']))
            manifest['price_source']['raw_base64']=base64.b64encode(('\n'.join(csv)+'\n').encode()).decode()
            revised=build_equity_snapshot(('\n'.join(csv)+'\n').encode(),manifest).document
            raw=json.dumps(revised,indent=2).encode();retained=_retain(self.service.workspace/'daily',raw)
            relative=Path(retained['path']).resolve().relative_to((self.service.workspace/'daily').resolve()).as_posix()
            identity='canon-'+sha256(relative.encode()).hexdigest()[:32]
            return self.service.mutate('terminal_import_daily_input',{'input_id':identity})['id']
        future=save_amended(len(snapshot['candles'])-1)
        before=api.read('status',dict(account_id=account_id))
        adoption=dict(account_id=account_id,request_id='adopt-tail-0001',expected_head=seed['head'],input_id=future)
        adopted=api.mutate('adopt',adoption)
        self.assertEqual(adopted['request_hash'],replay.digest(adoption))
        self.assertEqual(adopted['request_action'],'adopt')
        self.assertEqual(api.read('receipt',dict(account_id=account_id,request_id=adoption['request_id'])),adopted)
        stored=json.loads(api._sessions[account_id].ledger.db.execute('SELECT payload FROM requests WHERE id=?',(adoption['request_id'],)).fetchone()[0])
        self.assertEqual(stored['_api']['payload']['input_id'],future)
        self.assertNotEqual(stored['input_id'],future)
        after=api.read('status',dict(account_id=account_id))
        self.assertEqual(before['state']['cursor'],after['state']['cursor'])
        self.assertEqual(before['state']['cash'],after['state']['cash'])
        self.assertEqual(adopted['outcome']['status'],'INPUT_VERSION_ADOPTED_NO_STEP')
        consumed=save_amended(0)
        with self.assertRaisesRegex(replay.ReplayError,'consumed_prefix_revision'):
            api.mutate('adopt',dict(account_id=account_id,request_id='adopt-past-0001',expected_head=adopted['head'],input_id=consumed))
        self.assertEqual(api.read('status',dict(account_id=account_id)),after)
        self.assertEqual(self.fixtures.runner.call_count,1)

    def test_source_guard_rechecks_after_actual_signal_and_before_commit(self):
        reference,_,_=self.native_chain()
        original=trusted.signals.build_strategy_signal_fn
        for phase in ('after_signal','before_commit'):
            self.guard_state.update(status='PASS',restart_required=False)
            settings=dict(self.settings,account_id='source-phase-'+phase)
            preview=self.adapter.preview(reference,settings)
            session=self.adapter.create_new(reference,settings,self.confirmation(preview));self.connections.append(session)
            if phase=='after_signal':
                def factory(*args,**kwargs):
                    fn=original(*args,**kwargs)
                    def changed(*a,**k):
                        answer=fn(*a,**k);self.guard_state.update(status='RESTART_REQUIRED',restart_required=True);return answer
                    return changed
                with patch.object(trusted.signals,'build_strategy_signal_fn',side_effect=factory):self.adapter.activate(session)
            else:
                def fault(at):
                    if at=='after_calculation':self.guard_state.update(status='RESTART_REQUIRED',restart_required=True)
                session.ledger._fault=fault
            with self.assertRaisesRegex(trusted.AdmissionError,'restart_required'):
                session.seed_close('phase-seed-'+phase,expected_head=session.snapshot()['head'],seed_count=preview['seed_selection']['recommended_count'])
            state=session.snapshot()
            self.assertIsNone(state['state']['cursor']);self.assertEqual(state['state']['quantity'],0)
            self.assertEqual(state['phase'],'ERROR_RECONCILIATION_REQUIRED')
            stopped=session.pause('phase-stop-'+phase,expected_head=state['head'],reason='blocked source change')
            session.reconcile('phase-check-'+phase,expected_head=stopped['head'])
        self.assertEqual(self.fixtures.runner.call_count,1)

    def test_saved_display_summary_survives_reopen_and_unavailable_current_resolver_read_only(self):
        reference,_,_=self.native_chain()
        self.settings['display_name']='  我的长期日线练习  '
        api=trusted.ReplayAPI(self.adapter);self.addCleanup(api.close)
        preview=api.read('preview',dict(reference=reference,settings=self.settings))
        self.assertEqual(preview['settings']['display_name'],'我的长期日线练习')
        created=api.mutate('create',dict(request_id='name-create-0001',reference=reference,settings=self.settings,confirmation=self.confirmation(preview)))
        account_id=self.settings['account_id']
        summary=api.read('status',dict(account_id=account_id))['display_summary']
        self.assertEqual(summary['display_name'],'我的长期日线练习')
        self.assertEqual(summary['symbol'],'QADEMO')
        self.assertEqual(summary['strategy_id'],'dual_ma')
        self.assertEqual(summary['reference'],reference)
        self.assertEqual(summary['task_version'],1)
        self.assertEqual(summary['unit_quantity'],1)
        self.assertEqual(summary['initial_cash'],'10000')
        self.assertEqual(summary['fee_rate'],'0.0005')
        self.assertEqual(summary['slippage_bps'],'2')
        self.assertEqual(summary['created_at'],self.now.isoformat())
        self.assertEqual(summary['model'],preview['model'])
        api.close();fresh=trusted.ReplayAPI(self.adapter);self.addCleanup(fresh.close)
        path=self.adapter._path(account_id);before=(path.read_bytes(),path.stat().st_mtime_ns)
        with (patch.object(self.service,'read',side_effect=AssertionError('No current research resolver')),
              patch.object(self.service,'_input',side_effect=AssertionError('No input re-admission')),
              patch.object(self.adapter,'runtime_guard',side_effect=AssertionError('No current code guard for saved display'))):
            reopened=fresh.read('status',dict(account_id=account_id))
            accounts=fresh.read('accounts',{})
            self.assertEqual(reopened['display_summary'],summary)
            self.assertEqual(accounts['items'][0]['display_summary'],summary)
            self.assertEqual(reopened['phase'],'RECOVERY_REQUIRED')
            self.assertEqual(reopened['head'],created['head'])
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)

    def test_display_name_validation_default_and_confirmation_binding(self):
        reference,_,_=self.native_chain()
        preview=self.adapter.preview(reference,self.settings)
        self.assertEqual(preview['settings']['display_name'],'QADEMO · dual_ma')
        self.assertNotIn(self.settings['account_id'],preview['settings']['display_name'])
        changed=dict(self.settings,display_name='换个练习名称')
        with self.assertRaisesRegex(trusted.AdmissionError,'explicit_exact'):
            self.adapter.create_new(reference,changed,self.confirmation(preview))
        for name in ('',' '*4,'X'*65,'line\nbreak','hidden\x00control','zero\u200bwidth',42):
            with self.subTest(name=repr(name)),self.assertRaisesRegex(trusted.AdmissionError,'printable_replay_display_name'):
                self.adapter.preview(reference,dict(self.settings,display_name=name))
        self.assertFalse((self.service.workspace/'historical-replay').exists())

    def test_corrupt_idle_store_can_close_handle_without_repair_or_business_event(self):
        import sqlite3
        api,_,_,_=self.prepare();account_id=self.settings['account_id']
        session=api._sessions[account_id]
        session.ledger.db.execute('UPDATE events SET hash=? WHERE sequence=1',('f'*64,))
        path=self.adapter._path(account_id);before=(path.read_bytes(),path.stat().st_mtime_ns)
        with self.assertRaisesRegex(replay.ReplayError,'event_chain_changed'):
            api.read('status',dict(account_id=account_id))
        with patch.object(session,'snapshot',side_effect=AssertionError('Close must not inspect corrupt ledger')):
            api.close_session(account_id)
        self.assertNotIn(account_id,api._sessions)
        with self.assertRaises(sqlite3.ProgrammingError):session.ledger.db.execute('SELECT 1')
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)

    def test_close_rejects_active_calculation_then_releases_idle_handle_without_new_event(self):
        api,preview,_,created=self.prepare();account_id=self.settings['account_id']
        entered,release=threading.Event(),threading.Event()
        original=trusted.signals.build_strategy_signal_fn
        def factory(*args,**kwargs):
            fn=original(*args,**kwargs)
            def blocked(*a,**k):entered.set();release.wait(5);return fn(*a,**k)
            return blocked
        with patch.object(trusted.signals,'build_strategy_signal_fn',side_effect=factory),ThreadPoolExecutor(max_workers=1) as pool:
            job=pool.submit(api.mutate,'seed',dict(account_id=account_id,request_id='close-active-seed',
                expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count']))
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(replay.ReplayError,'operation_still_processing'):
                    api.close_session(account_id)
                self.assertIn(account_id,api._sessions)
            finally:release.set()
            saved=job.result(5)
        path=self.adapter._path(account_id);before=(path.read_bytes(),path.stat().st_mtime_ns)
        api.close_session(account_id)
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)
        reopened=api.read('status',dict(account_id=account_id))
        self.assertEqual(reopened['phase'],'RECOVERY_REQUIRED')
        self.assertEqual(reopened['head'],saved['head'])
        self.assertEqual(reopened['capacity']['events'],3)

    def test_late_pause_has_exact_typed_refusal_without_row_and_missing_receipt_stays_missing(self):
        api,preview,_,created=self.prepare();account_id=self.settings['account_id']
        seed=api.mutate('seed',dict(account_id=account_id,request_id='race-seed-0001',expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count']))
        step_body=dict(account_id=account_id,request_id='race-step-0001',expected_head=seed['head'])
        applied=api.mutate('step',step_body)
        body=dict(account_id=account_id,request_id='race-pause-0001',expected_head=seed['head'],
                  in_flight_request_id=step_body['request_id'],reason='暂停这次处理')
        path=self.adapter._path(account_id);before=(path.read_bytes(),path.stat().st_mtime_ns)
        refused=api.mutate('pause',body)
        self.assertEqual(refused,dict(status='REFUSED_NOT_APPLIED',reason='expected_head_changed',automatic_retry=False,
            automatic_next_step=False,account_id=account_id,request_id=body['request_id'],request_action='pause',request_hash=replay.digest(body)))
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)
        with self.assertRaisesRegex(replay.ReplayError,'request_not_found'):
            api.read('receipt',dict(account_id=account_id,request_id=body['request_id']))
        self.assertEqual(api.read('receipt',dict(account_id=account_id,request_id=step_body['request_id'])),applied)
        stale_step=api.mutate('step',dict(account_id=account_id,request_id='race-stale-step',expected_head=seed['head']))
        self.assertEqual(stale_step['status'],'REFUSED_NOT_APPLIED')
        self.assertEqual(api.read('status',dict(account_id=account_id))['head'],applied['head'])

    def test_existing_success_conflict_and_pending_are_never_typed_as_not_applied(self):
        api,preview,_,created=self.prepare();account_id=self.settings['account_id']
        body=dict(account_id=account_id,request_id='identity-seed-0001',expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count'])
        applied=api.mutate('seed',body)
        self.assertEqual(api.mutate('seed',body),applied)
        with self.assertRaisesRegex(replay.ReplayError,'request_id_conflict') as conflict:
            api.mutate('seed',dict(body,seed_count=body['seed_count']+1))
        self.assertNotIsInstance(conflict.exception,replay.ReplayRefusedNotApplied)
        session=api._sessions[account_id]
        session.ledger._fault=lambda phase:(_ for _ in ()).throw(ValueError('intent retained')) if phase=='after_intent' else None
        next_body=dict(account_id=account_id,request_id='identity-step-0001',expected_head=applied['head'])
        with self.assertRaisesRegex(ValueError,'intent retained') as failed:api.mutate('step',next_body)
        self.assertNotIsInstance(failed.exception,replay.ReplayRefusedNotApplied)
        with self.assertRaisesRegex(replay.ReplayError,'pending_intent') as pending:api.mutate('step',next_body)
        self.assertNotIsInstance(pending.exception,replay.ReplayRefusedNotApplied)
        receipt=api.read('receipt',dict(account_id=account_id,request_id=next_body['request_id']))
        self.assertEqual(receipt['status'],'PENDING');self.assertEqual(receipt['request_hash'],replay.digest(next_body))

    def test_commit_then_error_is_unknown_with_queryable_original_metadata_and_no_post_ack_read(self):
        reference,_,_=self.native_chain();api=trusted.ReplayAPI(self.adapter);self.addCleanup(api.close)
        preview=api.read('preview',dict(reference=reference,settings=self.settings))
        creation=dict(request_id='ack-create-0001',reference=reference,settings=self.settings,confirmation=self.confirmation(preview))
        with patch.object(api,'read',side_effect=AssertionError('No post-create acknowledgement read')):
            created=api.mutate('create',creation)
        self.assertEqual(created['request_hash'],replay.digest(creation));self.assertEqual(created['request_action'],'create')
        account_id=self.settings['account_id'];session=api._sessions[account_id]
        body=dict(account_id=account_id,request_id='ack-seed-0001',expected_head=created['head'],seed_count=preview['seed_selection']['recommended_count'])
        with patch.object(api,'read',side_effect=AssertionError('No post-mutation acknowledgement read')):
            acknowledged=api.mutate('seed',body)
        self.assertEqual(acknowledged['request_hash'],replay.digest(body))
        session.ledger._fault=lambda phase:(_ for _ in ()).throw(ValueError('response lost after committed step')) if phase=='after_commit' else None
        step_body=dict(account_id=account_id,request_id='ack-step-0001',expected_head=acknowledged['head'])
        with self.assertRaisesRegex(ValueError,'response lost') as unknown:api.mutate('step',step_body)
        self.assertNotIsInstance(unknown.exception,replay.ReplayRefusedNotApplied)
        queried=api.read('receipt',dict(account_id=account_id,request_id=step_body['request_id']))
        self.assertEqual(queried['outcome']['status'],'ONE_BAR_APPLIED')
        self.assertEqual(queried['request_hash'],replay.digest(step_body));self.assertEqual(queried['request_action'],'step')

    def test_api_metadata_and_new_control_hash_are_checked_against_immutable_event_chain(self):
        import json
        api,_,creation,created=self.prepare();account_id=self.settings['account_id']
        body=dict(account_id=account_id,request_id='chain-pause-0001',expected_head=created['head'],reason='original reason')
        paused=api.mutate('pause',body);session=api._sessions[account_id]
        self.assertEqual(api.read('receipt',dict(account_id=account_id,request_id=body['request_id'])),paused)
        row=session.ledger.db.execute('SELECT * FROM requests WHERE id=?',(body['request_id'],)).fetchone()
        bad_receipt=json.loads(row['receipt']);bad_receipt['request_id']='forged-request-identity'
        session.ledger.db.execute('UPDATE requests SET receipt=? WHERE id=?',(replay.encoded(bad_receipt),body['request_id']))
        with self.assertRaisesRegex(replay.ReplayError,'request_receipt_changed'):
            api.read('receipt',dict(account_id=account_id,request_id=body['request_id']))
        session.ledger.db.execute('UPDATE requests SET receipt=? WHERE id=?',(row['receipt'],body['request_id']))
        payload=json.loads(row['payload']);payload['reason']='changed reason';payload['_api']['payload']['reason']='changed reason'
        payload['_api']['hash']=replay.digest(payload['_api']['payload'])
        forged_hash=replay.digest(dict(action=row['action'],payload=payload))
        session.ledger.db.execute('UPDATE requests SET payload=?,hash=? WHERE id=?',(replay.encoded(payload),forged_hash,body['request_id']))
        path=self.adapter._path(account_id);before=path.read_bytes()
        with self.assertRaisesRegex(replay.ReplayError,'control_request_hash_changed'):
            api.read('receipt',dict(account_id=account_id,request_id=body['request_id']))
        self.assertEqual(path.read_bytes(),before)
        # The INTENT branch must bind the same full API metadata as controls.
        second_settings=dict(self.settings,account_id='chain-seed-second')
        preview=api.read('preview',dict(reference=creation['reference'],settings=second_settings))
        new=api.mutate('create',dict(request_id='chain-create-0002',reference=creation['reference'],settings=second_settings,confirmation=self.confirmation(preview)))
        seed_body=dict(account_id=second_settings['account_id'],request_id='chain-seed-0002',expected_head=new['head'],seed_count=preview['seed_selection']['recommended_count'])
        api.mutate('seed',seed_body);second=api._sessions[second_settings['account_id']]
        seed_row=second.ledger.db.execute('SELECT * FROM requests WHERE id=?',(seed_body['request_id'],)).fetchone()
        seed_payload=json.loads(seed_row['payload']);seed_payload['seed_count']+=1;seed_payload['_api']['payload']['seed_count']+=1
        seed_payload['_api']['hash']=replay.digest(seed_payload['_api']['payload'])
        second.ledger.db.execute('UPDATE requests SET payload=?,hash=? WHERE id=?',
            (replay.encoded(seed_payload),replay.digest(dict(action=seed_row['action'],payload=seed_payload)),seed_body['request_id']))
        with self.assertRaisesRegex(replay.ReplayError,'request_intent_binding_changed'):
            api.read('receipt',dict(account_id=second_settings['account_id'],request_id=seed_body['request_id']))

    def test_client_internal_api_injection_is_rejected_and_legacy_receipt_bytes_are_not_rewritten(self):
        api,_,_,created=self.prepare();account_id=self.settings['account_id']
        with self.assertRaisesRegex(trusted.AdmissionError,'fields_invalid'):
            api.mutate('pause',dict(account_id=account_id,request_id='inject-pause-0001',expected_head=created['head'],reason='x',_api={}))
        session=api._sessions[account_id];append=session.ledger._append
        def old_event(kind,payload,state):return append(kind,{key:value for key,value in payload.items() if key!='request_hash'},state)
        with patch.object(session.ledger,'_append',side_effect=old_event):
            session.pause('legacy-pause-0001',expected_head=created['head'],reason='saved old-format control')
        raw=session.ledger.db.execute('SELECT receipt FROM requests WHERE id=?',('legacy-pause-0001',)).fetchone()[0]
        path=self.adapter._path(account_id);before=(path.read_bytes(),path.stat().st_mtime_ns)
        read=api.read('receipt',dict(account_id=account_id,request_id='legacy-pause-0001'))
        self.assertEqual(read['request_metadata_status'],'UNAVAILABLE_LEGACY_PAYLOAD')
        self.assertNotIn('request_hash',read)
        self.assertEqual(session.ledger.db.execute('SELECT receipt FROM requests WHERE id=?',('legacy-pause-0001',)).fetchone()[0],raw)
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)

    def test_unseeded_adoption_of_short_verified_input_projects_missing_rows_without_resolver(self):
        import base64,json
        from hashlib import sha256
        from pathlib import Path
        from hakimi_research.equity_dataset import build_equity_snapshot
        from hakimi_research.input_workflow import _retain
        reference,_,snapshot=self.native_chain();api=trusted.ReplayAPI(self.adapter);self.addCleanup(api.close)
        preview=api.read('preview',dict(reference=reference,settings=self.settings))
        created=api.mutate('create',dict(request_id='short-create-0001',reference=reference,settings=self.settings,confirmation=self.confirmation(preview)))
        csv=base64.b64decode(snapshot['raw_input']['csv_base64']).decode().splitlines()[:11]
        raw_csv=('\n'.join(csv)+'\n').encode();manifest=json.loads(base64.b64decode(snapshot['raw_input']['manifest_base64']))
        manifest['price_source']['raw_base64']=base64.b64encode(raw_csv).decode()
        last_date=csv[-1].split(',')[0]
        manifest['calendar']['coverage_end']=last_date
        manifest['calendar']['days']=[day for day in manifest['calendar']['days'] if day['date']<=last_date]
        manifest['calendar']['source']['raw_base64']=base64.b64encode(json.dumps(manifest['calendar']['days']).encode()).decode()
        short=build_equity_snapshot(raw_csv,manifest).document
        retained=_retain(self.service.workspace/'daily',json.dumps(short,indent=2).encode())
        relative=Path(retained['path']).resolve().relative_to((self.service.workspace/'daily').resolve()).as_posix()
        native=self.service.mutate('terminal_import_daily_input',dict(input_id='canon-'+sha256(relative.encode()).hexdigest()[:32]))
        account_id=self.settings['account_id']
        adopted=api.mutate('adopt',dict(account_id=account_id,request_id='short-adopt-0001',expected_head=created['head'],input_id=native['id']))
        before=self.adapter._path(account_id).read_bytes()
        with (patch.object(self.adapter,'runtime_guard',side_effect=AssertionError('Saved projection must not run current guard')),
              patch.object(self.service,'read',side_effect=AssertionError('No research resolver for saved projection'))):
            status=api.read('status',dict(account_id=account_id))
        selection=status['seed_selection']
        self.assertFalse(selection['data_sufficient']);self.assertEqual(selection['available_rows'],10)
        self.assertEqual(selection['missing_rows'],selection['minimum_count']-10)
        for field in ('recommended_count','recommended_session','next_session'):self.assertIsNone(selection[field])
        self.assertEqual(status['head'],adopted['head']);self.assertIsNone(status['state']['cursor'])
        self.assertEqual(self.adapter._path(account_id).read_bytes(),before)


if __name__=='__main__':unittest.main()
