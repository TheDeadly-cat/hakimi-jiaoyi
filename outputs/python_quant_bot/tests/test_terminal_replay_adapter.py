"""Fresh fictional import -> genuine native save/run -> trusted replay only.

The ordinary-import metadata is explicitly a QA declaration. It is neither
authenticated market evidence nor use of any existing user's result.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_continuous_replay as replay
from exchange_terminal.services import terminal_replay_service as trusted
from tests import test_terminal_research as fixture
from hakimi_research.input_workflow import _retain


def inventory(root):
    return {str(p.resolve().relative_to(root.resolve())):(sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file() and 'historical-replay' not in p.parts}


class TrustedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixtures=fixture.TerminalResearchTests();self.fixtures.setUp()
        self.addCleanup(self.fixtures.doCleanups)
        # Production QuantWorkspace resolves its trusted workspace before
        # constructing either service; reproduce that entry contract under 8.3 TEMP.
        self.fixtures.root=self.fixtures.root.resolve()
        self.fixtures.core.workspace=self.fixtures.core.workspace.resolve()
        self.service=self.fixtures.service
        self.service.workspace=self.fixtures.core.workspace
        self.service.fingerprint=trusted.signals.strategy_signal_fingerprint
        self.guard_state={'schema_version':'hakimi-runtime-build-v1','status':'PASS','restart_required':False}
        self.now=datetime(2026,10,30,tzinfo=timezone.utc)
        self.adapter=trusted.TrustedReplayAdapter(self.service,runtime_guard=lambda:deepcopy(self.guard_state),clock=lambda:self.now)
        self.settings=dict(account_id='replay-fresh-0001',initial_cash='10000',unit_quantity=1,fee_rate='0.0005',
                           slippage_bps='2',limits=deepcopy(replay.DEFAULT_LIMITS))
        self.connections=[];self.addCleanup(self.close_all)
        self.network=patch('socket.socket.connect',side_effect=AssertionError('No network')).start()
        self.addCleanup(patch.stopall)

    def close_all(self):
        for c in self.connections:
            try:c.close()
            except Exception:pass

    def native_chain(self, *, namespace='daily_reference', strategy_id='dual_ma',params=None):
        snapshot=fixture.build_core_import_qa_fixture()
        raw=(json.dumps(snapshot,indent=3)+'\n').encode()
        if namespace=='daily_reference':
            retained=_retain(self.service.workspace/'daily',raw)
            relative=Path(retained['path']).resolve().relative_to((self.service.workspace/'daily').resolve()).as_posix()
            canonical_id='canon-'+sha256(relative.encode()).hexdigest()[:32]
            saved_input=self.service.mutate('terminal_import_daily_input',{'input_id':canonical_id})
        else:
            # Frozen core service is only used to verify/read this new fixture.
            from exchange_terminal.services.quant_workspace import _load_kernel
            core=_load_kernel().service(self.service.workspace.resolve())
            self.service.core=core
            source=core.workspace/'data'/'fresh-qa.json';source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(raw)
            saved_input=self.service.mutate('terminal_import_core_input',{'input_id':core._id(source)})
        task=self.service.mutate('terminal_save_task',dict(name='新建虚构QA原生报告',strategy_id=strategy_id,
            strategy_params=params or {'fast_window':10,'slow_window':40},input_id=saved_input['id'],
            risk={'position_pct':25,'take_profit_pct':0,'stop_loss_pct':8,'leverage':1},
            costs={'fee_rate':.0005,'slippage_bps':2}))
        def actual(**kw):
            return fixture.run_causal_long_only_backtest(rows=kw['market_payload']['rows'],symbol=kw['symbol'],source=kw['market_payload']['source'],
                signal_fn=fixture.build_strategy_signal_fn(kw['strategy_id'],kw['strategy_params']),
                startup_candles=fixture.strategy_startup_candles_for_params(kw['strategy_id'],kw['strategy_params']),
                position_pct=kw['position_pct'],take_profit_pct=kw['take_profit_pct'],stop_loss_pct=kw['stop_loss_pct'],
                leverage=kw['leverage'],fee_rate=kw['fee_rate'],slippage_bps=kw['slippage_bps'],market='stock',timeframe='1D')
        self.fixtures.runner.side_effect=actual
        previous_runs=self.fixtures.runner.call_count
        report=self.service.mutate('terminal_run_task',{'task_id':task['id']})
        self.assertEqual(report['status'],'COMPLETED',report.get('error'))
        self.assertEqual(self.fixtures.runner.call_count,previous_runs+1)
        self.fixtures.runner.side_effect=AssertionError('Replay and readback must not run research again')
        self.fixtures.reader.side_effect=AssertionError('Saved replay must not fetch market cache')
        return {'kind':'terminal_run','id':report['id']},saved_input,snapshot

    def confirmation(self, preview):
        return dict(admission_id=preview['admission_id'],model_id=replay.MODEL,
                    whole_share_next_open_is_different=True,no_intrabar_stop_or_take_profit=True)

    def create(self, reference):
        preview=self.adapter.preview(reference,self.settings)
        account=self.adapter.create_new(reference,self.settings,self.confirmation(preview));self.connections.append(account)
        return preview,account

    def test_real_daily_native_report_seed_next_open_and_readback_keep_research_bytes(self):
        reference,saved,snapshot=self.native_chain()
        before=inventory(self.service.workspace)
        preview,account=self.create(reference)
        self.assertEqual(preview['input_binding']['source_namespace'],'daily_reference')
        self.assertFalse(preview['model']['native_execution_equivalent'])
        self.assertEqual(preview['session_count'],len(snapshot['sessions']))
        seed=account.seed_close('fresh-seed-0001',expected_head=account.snapshot()['head'],seed_count=80)
        step=account.advance_next('fresh-step-0001',expected_head=seed['head'])
        self.assertEqual(step['outcome']['fill']['execution_at'],trusted.stamp(snapshot['sessions'][80]['open_utc']))
        self.assertEqual(step['outcome']['signal']['signal_at'],trusted.stamp(snapshot['sessions'][80]['close_utc']))
        self.assertEqual(account.snapshot()['state']['event_at'],trusted.stamp(snapshot['sessions'][80]['close_utc']))
        self.assertTrue(all(e['recorded_at'].startswith('2026-10-30') for e in account.history()['items']))
        self.assertEqual(account.advance_next('fresh-step-0001',expected_head=seed['head']),step)
        account.close()
        inspected=self.adapter.inspect(self.settings['account_id'])
        self.assertEqual(inspected['snapshot']['phase'],'RECOVERY_REQUIRED')
        reopened=self.adapter.open_for_steps(self.settings['account_id']);self.connections.append(reopened)
        with self.assertRaisesRegex(replay.ReplayError,'reconciliation'):
            reopened.advance_next('fresh-no-auto-0001',expected_head=step['head'])
        checked=reopened.reconcile('fresh-check-0001',expected_head=step['head'])
        resumed=reopened.resume('fresh-resume-0001',expected_head=checked['head'])
        self.assertEqual(resumed['outcome']['computed_steps'],0)
        self.assertEqual(reopened.snapshot()['state']['cursor'],80)
        self.assertEqual(inventory(self.service.workspace),before)
        self.assertEqual(self.fixtures.runner.call_count,1);self.network.assert_not_called()

    def test_real_core_original_is_native_report_reference_not_core_strategy(self):
        reference,_,_=self.native_chain(namespace='core_reference')
        preview,account=self.create(reference)
        self.assertEqual(preview['input_binding']['source_namespace'],'core_reference')
        self.assertEqual(account.snapshot()['phase'],'SEED_REQUIRED')
        with self.assertRaisesRegex(trusted.AdmissionError,'completed_native'):
            self.adapter.preview({'kind':'core_run','id':'a'*24},self.settings)

    def test_confirmation_and_settings_are_exact_without_new_store(self):
        reference,_,_=self.native_chain()
        preview=self.adapter.preview(reference,self.settings)
        for confirmation in ({},dict(self.confirmation(preview),no_intrabar_stop_or_take_profit=1)):
            with self.assertRaisesRegex(trusted.AdmissionError,'explicit_exact'):
                self.adapter.create_new(reference,self.settings,confirmation)
        changed=dict(self.settings,unit_quantity=2)
        with self.assertRaisesRegex(trusted.AdmissionError,'explicit_exact'):
            self.adapter.create_new(reference,changed,self.confirmation(preview))
        self.assertFalse((self.service.workspace/'historical-replay').exists())

    def test_runtime_and_real_source_identity_changes_block_calculation_but_allow_read(self):
        reference,_,_=self.native_chain();_,account=self.create(reference)
        before=account.snapshot();self.guard_state.update(status='RESTART_REQUIRED',restart_required=True)
        with self.assertRaisesRegex(trusted.AdmissionError,'restart_required'):
            account.seed_close('source-block-0001',expected_head=before['head'],seed_count=80)
        self.assertEqual(account.snapshot(),before)
        self.assertEqual(account.history()['items'][0]['kind'],'CREATED')
        self.guard_state.update(status='PASS',restart_required=False)
        original=trusted._engine_source_identity()
        with patch.object(trusted,'_engine_source_identity',return_value=dict(original,extra='f'*64)):
            with self.assertRaisesRegex(trusted.AdmissionError,'binding_changed'):
                account.seed_close('source-block-0002',expected_head=before['head'],seed_count=80)
        self.assertEqual(account.snapshot(),before)

    def test_tampered_retained_original_is_rejected_before_new_account(self):
        reference,saved,_=self.native_chain()
        path=self.service.workspace/saved['daily_reference']['original_bytes_path']
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.adapter.preview(reference,self.settings)
        self.assertFalse((self.service.workspace/'historical-replay').exists())

    def test_native_cache_without_original_calendar_is_explicitly_unsupported(self):
        task=self.fixtures.task();report=self.fixtures.run_task(task)
        self.assertEqual(report['status'],'COMPLETED')
        with self.assertRaisesRegex(trusted.AdmissionError,'canonical_original_required'):
            self.adapter.preview({'kind':'terminal_run','id':report['id']},self.settings)


if __name__=='__main__':unittest.main()
